"""QUAD RELAYOUT: slide a quad mesh's vertices over its OWN surface so that chosen vertices (poles) go to new places and
chosen edge loops lie along given curves, the connectivity unchanged and the form kept (every moved vertex lands on
the old surface). Built in woman2 build 13b (2026-10-21) for the shoulder topology: poles out of the armpit and from
under the breast, a loop along the deltoid's border and the axillary folds, a breast's loops laid as the other's mirror.

  R = relayout(V, Q, free, points=None, chains=None, iters=40, pins=None)
      V (n, 3), Q (m, 4) quads; free (n,) bool: the vertices that may move (their quads, plus one ring of held
      vertices round them, make the patch: a disc, or a disc with held islands in it).
      points: {vertex: target 3-D point} (projected onto the old patch surface first)
      chains: [(vertex chain (k,), polyline (p, 3))]: the chain's vertices are spread along the polyline (projected
              onto the patch) at the arc-length fractions they have now; its two ends go to the polyline's ends
      Method: the patch is laid flat by a least-squares conformal map (quad_grid.lscm_uv) of its old triangles; the move
      is a smooth displacement of that flat layout, the bi-Laplacian (cotangent) interpolation of the targets' moves
      with the held ring still (a pole's one-ring moves with it: rigid_ring); each new flat point is located in an old
      flat triangle and lifted to the old 3-D triangle at the same barycentric place. The strain a move leaves is about
      its length over the patch radius: size the free set to the move (quality() before and after).
      Returns dict: V (new positions), tri (n,) old triangle index for each moved vertex (-1 = not moved), bary (n, 3),
      Tpatch (the old triangles the indices refer to, global vertex ids), flips (new flat triangles turned over),
      param_flips (old flat triangles turned over by the conformal map: must be 0), outside (moved points that fell
      outside every old triangle and were clamped: should be 0), target_err_mm (largest distance of a target vertex
      from its target after lifting)
  R = relayout_surface(V, Q, free, points=None, chains=None, steps=12)
      the same job without a flat layout (a deep curved patch, e.g. an armpit, scales a conformal map so unevenly that
      a move set in the flat layout lands far off: measured in build 13b): the targets' 3-D moves are interpolated over
      the patch by the bi-Laplacian of the mesh itself (cotangent, lumped mass) with the held ring still, and every
      moved vertex walks there in `steps` steps, put back on the old surface (closest point on the old patch faces)
      after each. Returns the same keys (tri / bary of the final place on the old faces)
  A = resample(R, arr)            a per-vertex array (n, ...) read at the moved vertices' new places (barycentric on the
                                  old triangles; bool / integer arrays take the nearest corner's value)
  UV = resample_corners(R, Q, UVc)  per-corner (m, 4, 2) uvs read at the moved vertices' new places; the patch must hold
                                  no uv seam (refused otherwise)
  Vn = relax(V, Q, free, iters=40, lam=0.5)
                                  tangential relaxation: each free vertex moves toward its edge neighbours' mean and is
                                  put back on the OLD surface (closest point on the old faces round the patch), so skewed
                                  or collapsed quads open up and the form stays; the others hold
  quality(V, Q, faces)            quad corner angles (deg: p1 / p50 / p99 of the smallest and largest corner) and the edge
                                  length ratio within each quad (p50 / p99), to compare a patch before and after
Proof: engine/tools/test_quad_relayout.py (a planted cylinder; json beside it).
"""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu
from scipy.spatial import cKDTree

try:
    from . import quad_grid as QG  # noqa
except ImportError:
    import quad_grid as QG  # noqa
try:
    from . import mesh_geom as MG  # noqa
except ImportError:
    import mesh_geom as MG  # noqa


def _tri_area2(U, T):
    a = U[T[:, 1]] - U[T[:, 0]]; b = U[T[:, 2]] - U[T[:, 0]]
    return a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]


def _cot_weights(U, T):
    """2-D cotangent Laplacian (positive semi-definite, off-diagonal -w) over triangles T of layout U"""
    n = len(U)
    I, J, W = [], [], []
    for k in range(3):
        i, j, l = T[:, k], T[:, (k + 1) % 3], T[:, (k + 2) % 3]
        a = U[i] - U[l]; b = U[j] - U[l]
        cr = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
        cot = (a * b).sum(1) / np.maximum(np.abs(cr), 1e-30)
        w = 0.5 * cot
        I += [i, j]; J += [j, i]; W += [w, w]
    I = np.concatenate(I); J = np.concatenate(J); W = np.concatenate(W)
    Wm = sparse.coo_matrix((W, (I, J)), shape=(n, n)).tocsr()
    Lm = sparse.diags(np.asarray(Wm.sum(1)).ravel()) - Wm
    return Lm.tocsc()


def _locate(U_old, T, P, k=24):
    """for each 2-D point, an old triangle that holds it and the barycentrics (clamped to the nearest when none does)"""
    C = U_old[T].mean(1)
    tree = cKDTree(C)
    kk = min(k, len(T))
    _, idx = tree.query(P, k=kk)
    idx = np.atleast_2d(idx)
    A = U_old[T[idx, 0]]; B = U_old[T[idx, 1]]; Cc = U_old[T[idx, 2]]
    v0 = B - A; v1 = Cc - A; v2 = P[:, None, :] - A
    d00 = (v0 * v0).sum(2); d01 = (v0 * v1).sum(2); d11 = (v1 * v1).sum(2); d20 = (v2 * v0).sum(2); d21 = (v2 * v1).sum(2)
    den = d00 * d11 - d01 * d01
    den = np.where(np.abs(den) < 1e-30, 1e-30, den)
    b1 = (d11 * d20 - d01 * d21) / den; b2 = (d00 * d21 - d01 * d20) / den; b0 = 1 - b1 - b2
    mn = np.minimum(np.minimum(b0, b1), b2)
    best = np.argmax(mn, axis=1)
    r = np.arange(len(P))
    tri = idx[r, best]; bary = np.stack([b0[r, best], b1[r, best], b2[r, best]], 1)
    outside = mn[r, best] < -1e-7
    bary = np.clip(bary, 0, None); bary /= bary.sum(1, keepdims=True)
    return tri, bary, outside


def relayout(V, Q, free, points=None, chains=None, pins=None, rigid_ring=True):
    V = np.asarray(V, float); Q = np.asarray(Q, np.int64); free = np.asarray(free, bool)
    n = len(V)
    pf = free[Q].any(1)
    patch_faces = np.nonzero(pf)[0]
    pv = np.unique(Q[patch_faces])
    held = pv[~free[pv]]
    # the patch's boundary vertices (a disc, or a disc with held islands inside: each is a hole of the flat layout)
    Fp = Q[patch_faces]; ea = Fp.ravel(); eb = np.roll(Fp, -1, 1).ravel()
    key = np.minimum(ea, eb) * (n + 1) + np.maximum(ea, eb)
    uk, cnt = np.unique(key, return_counts=True)
    bnd_v = np.unique(np.r_[ea[np.isin(key, uk[cnt == 1])], eb[np.isin(key, uk[cnt == 1])]])
    loc = -np.ones(n, np.int64); loc[pv] = np.arange(len(pv))
    Tg = QG.quad_tris(Q[patch_faces])                            # global ids
    T = loc[Tg]
    # flat layout of the old patch
    if pins is None:
        b0 = int(bnd_v[0]); b1 = int(bnd_v[np.argmax(np.linalg.norm(V[bnd_v] - V[b0], axis=1))])
        pins = {int(b0): np.array([0.0, 0.0]), int(b1): np.array([np.linalg.norm(V[b1] - V[b0]), 0.0])}
    U = QG.lscm_uv(V, Tg, pv, pins)
    ar_old = _tri_area2(U, T)
    sgn = np.sign(np.median(ar_old))
    if sgn < 0:
        U[:, 1] *= -1; ar_old = -ar_old
    param_flips = int((ar_old <= 0).sum())
    # targets in the flat layout: a 3-D point -> the old patch triangle nearest it -> its barycentric place in 2-D
    MP = MG.MeshProj(V, Tg)
    fixed = {int(v): U[loc[v]] for v in held}
    tgt3 = {}

    def flat_of(P3):
        X, d, f = MP.project(np.atleast_2d(P3))
        tri = Tg[f]
        _, bary = MG.closest_on_triangles(X, V[tri[:, 0]], V[tri[:, 1]], V[tri[:, 2]], bary=True)
        return (U[loc[tri]] * bary[:, :, None]).sum(1), X

    if points:
        ids = np.array(list(points.keys()), np.int64); P3 = np.array([points[k] for k in ids.tolist()])
        uu, X = flat_of(P3)
        for v, u, x in zip(ids.tolist(), uu, X):
            fixed[v] = u; tgt3[v] = x
    for chain, poly in (chains or []):
        chain = np.asarray(chain, np.int64); poly = np.asarray(poly, float)
        seg = np.linalg.norm(np.diff(V[chain], axis=0), axis=1); fr = np.r_[0, np.cumsum(seg)] / max(seg.sum(), 1e-12)
        ps = np.linalg.norm(np.diff(poly, axis=0), axis=1); pc = np.r_[0, np.cumsum(ps)] / max(ps.sum(), 1e-12)
        P3 = np.stack([np.interp(fr, pc, poly[:, d]) for d in range(3)], 1)
        uu, X = flat_of(P3)
        for v, u, x in zip(chain.tolist(), uu, X):
            if free[v]:
                fixed[v] = u; tgt3[v] = x
    # the move as a smooth displacement of the flat layout: bi-Laplacian (cotangent L, lumped mass M: L M^-1 L D = 0)
    # with D = 0 on the held vertices and D = target - now on the targets, so a moved point drags its surroundings
    # with a falloff spread over the patch (a membrane / ARAP solve pins a point with a log singularity: tested)
    Lm = _cot_weights(U, T)
    nl = len(pv)
    area = np.zeros(nl)
    np.add.at(area, T.ravel(), np.repeat(np.abs(_tri_area2(U, T)) / 6.0, 3))
    K = (Lm @ sparse.diags(1.0 / np.maximum(area, 1e-30)) @ Lm).tocsc()
    isf = np.zeros(nl, bool)
    fid = np.array([loc[k] for k in fixed.keys()], np.int64); isf[fid] = True
    D = np.zeros((nl, 2)); D[fid] = np.array(list(fixed.values())) - U[fid]
    if rigid_ring and points:
        # each pole's one-ring moves with it (its star keeps its shape)
        A1 = QG.ring_neighbours(Q[patch_faces], n)
        for v in points:
            for w in A1[v].indices:
                if free[w] and int(w) not in fixed:
                    isf[loc[w]] = True; D[loc[w]] = D[loc[v]]
    fr_ = np.nonzero(~isf)[0]
    Kff = splu(K[fr_][:, fr_].tocsc()); Kfc = K[fr_][:, isf]
    D[fr_] = np.stack([Kff.solve(-(Kfc @ D[isf][:, d])) for d in range(2)], 1)
    Xn = U + D
    flips = int((_tri_area2(Xn, T) <= 0).sum())
    # lift: the moved vertices' new flat places located in the old flat triangles
    mv = np.nonzero(free[pv])[0]
    tri_l, bary, outside = _locate(U, T, Xn[mv])
    Vn = V.copy()
    Vn[pv[mv]] = (V[Tg[tri_l]] * bary[:, :, None]).sum(1)
    tri = -np.ones(n, np.int64); tri[pv[mv]] = tri_l
    B = np.zeros((n, 3)); B[pv[mv]] = bary
    terr = max([float(np.linalg.norm(Vn[v] - x)) for v, x in tgt3.items()] or [0.0]) * 1e3
    return {"V": Vn, "tri": tri, "bary": B, "Tpatch": Tg, "flips": flips, "param_flips": param_flips,
            "outside": int(outside.sum()), "target_err_mm": round(terr, 4), "moved": int(free.sum()),
            "patch_faces": patch_faces, "U_old": U, "U_new": Xn, "patch_vertices": pv}


def resample(R, arr):
    arr = np.asarray(arr)
    out = arr.copy()
    m = R["tri"] >= 0
    tri = R["Tpatch"][R["tri"][m]]; b = R["bary"][m]
    if arr.dtype.kind in "biu":
        out[m] = arr[tri[np.arange(len(tri)), b.argmax(1)]]
    else:
        out[m] = (arr[tri].astype(float) * (b.reshape(b.shape + (1,) * (arr.ndim - 1)))).sum(1).astype(arr.dtype)
    return out


def resample_corners(R, Q, UVc):
    """per-corner uvs at the moved vertices' new places. The patch must hold no uv seam (every vertex of the patch
    one uv): checked, and refused otherwise, so a caller picks a seam-free patch"""
    Q = np.asarray(Q, np.int64); UVc = np.asarray(UVc, float).reshape(len(Q), 4, 2)
    pf = R["patch_faces"]; pv = R["patch_vertices"]
    fv = Q[pf].ravel(); uv = UVc[pf].reshape(-1, 2)
    o = np.argsort(fv, kind="stable"); fs = fv[o]; us = uv[o]
    st = np.r_[0, np.nonzero(np.diff(fs))[0] + 1]
    spread = np.abs(np.maximum.reduceat(us, st, 0) - np.minimum.reduceat(us, st, 0)).max(1)
    if (spread > 1e-6).any():
        raise ValueError("resample_corners: the patch holds a uv seam at %d vertices" % int((spread > 1e-6).sum()))
    vuv = np.zeros((int(Q.max()) + 1, 2)); vuv[fs[st]] = us[st]
    new = resample(R, vuv)
    out = UVc.copy()
    moved = R["tri"] >= 0
    m = moved[Q[pf]]
    sub = out[pf]; sub[m] = new[Q[pf][m]]; out[pf] = sub
    return out


def quality(V, Q, faces=None):
    Q = np.asarray(Q, np.int64)
    q = Q if faces is None else Q[faces]
    P = V[q]
    ang = []
    for c in range(4):
        a = P[:, (c - 1) % 4] - P[:, c]; b = P[:, (c + 1) % 4] - P[:, c]
        ang.append(np.degrees(np.arccos(np.clip((a * b).sum(1) / np.maximum(np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-30), -1, 1))))
    ang = np.stack(ang, 1)
    el = np.stack([np.linalg.norm(P[:, (c + 1) % 4] - P[:, c], axis=1) for c in range(4)], 1)
    ratio = el.max(1) / np.maximum(el.min(1), 1e-30)
    r = lambda x: [round(float(v), 2) for v in x]
    return {"quads": int(len(q)), "min_corner_deg_p1_p50": r(np.percentile(ang.min(1), [1, 50])), "min_corner_deg_min": round(float(ang.min()), 2),
            "max_corner_deg_p50_p99": r(np.percentile(ang.max(1), [50, 99])), "max_corner_deg_max": round(float(ang.max()), 2),
            "edge_ratio_p50_p99_max": r(np.percentile(ratio, [50, 99, 100]))}


def relax(V, Q, free, iters=40, lam=0.5):
    V = np.asarray(V, float); Q = np.asarray(Q, np.int64); free = np.asarray(free, bool)
    pf = free[Q].any(1)
    pv = np.unique(Q[pf])
    near = np.isin(Q, pv).any(1)
    Tg = QG.quad_tris(Q[near])
    MP = MG.MeshProj(V, Tg)
    A = QG.ring_neighbours(Q[pf], len(V))
    deg = np.asarray(A.sum(1)).ravel()
    X = V.copy()
    idx = np.nonzero(free)[0]
    Asub = A[idx]
    for _ in range(iters):
        avg = (Asub @ X) / np.maximum(deg[idx], 1)[:, None]
        Y = X[idx] + lam * (avg - X[idx])
        X[idx] = MP.project(Y)[0]
    return X


def relayout_surface(V, Q, free, points=None, chains=None, steps=12, rigid_ring=True):
    V = np.asarray(V, float); Q = np.asarray(Q, np.int64); free = np.asarray(free, bool)
    n = len(V)
    pf = free[Q].any(1)
    patch_faces = np.nonzero(pf)[0]
    pv = np.unique(Q[patch_faces])
    loc = -np.ones(n, np.int64); loc[pv] = np.arange(len(pv))
    near = np.isin(Q, pv).any(1)
    Tg = QG.quad_tris(Q[near])
    MP = MG.MeshProj(V, Tg)
    tgt = {}
    if points:
        ids = np.array(list(points.keys()), np.int64); P3 = np.array([points[k] for k in ids.tolist()])
        X, _, _ = MP.project(P3)
        tgt.update({int(v): x for v, x in zip(ids.tolist(), X)})
    for chain, poly in (chains or []):
        chain = np.asarray(chain, np.int64); poly = np.asarray(poly, float)
        seg = np.linalg.norm(np.diff(V[chain], axis=0), axis=1); fr = np.r_[0, np.cumsum(seg)] / max(seg.sum(), 1e-12)
        ps = np.linalg.norm(np.diff(poly, axis=0), axis=1); pc = np.r_[0, np.cumsum(ps)] / max(ps.sum(), 1e-12)
        P3 = np.stack([np.interp(fr, pc, poly[:, d]) for d in range(3)], 1)
        X, _, _ = MP.project(P3)
        for v, x in zip(chain.tolist(), X):
            if free[v]:
                tgt[int(v)] = x
    Tl = loc[QG.quad_tris(Q[patch_faces])]
    Lm, area = MG.cot_laplacian(V[pv], Tl)
    Lm = -Lm.tocsc() if (Lm.diagonal() < 0).all() else Lm.tocsc()          # positive semi-definite
    K = (Lm @ sparse.diags(1.0 / np.maximum(np.asarray(area).ravel(), 1e-30)) @ Lm).tocsc()
    nl = len(pv)
    isf = ~free[pv]
    ring = {}
    if rigid_ring and points:
        A1 = QG.ring_neighbours(Q[patch_faces], n)
        for v in points:
            for w in A1[v].indices:
                if free[w] and int(w) not in tgt:
                    ring[int(w)] = int(v); isf[loc[w]] = True
    for v in tgt:
        isf[loc[v]] = True
    fr_ = np.nonzero(~isf)[0]
    Kff = splu(K[fr_][:, fr_].tocsc()) if len(fr_) else None
    Kfc = K[fr_][:, isf]
    mv = np.nonzero(free[pv])[0]
    Xall = V[pv].copy()
    for rnd in range(3):                                   # walk, then walk the remaining error again
        D = np.zeros((nl, 3))
        for v, x in tgt.items():
            D[loc[v]] = x - Xall[loc[v]]
        for w, v in ring.items():
            D[loc[w]] = D[loc[v]]
        if Kff is not None:
            D[fr_] = np.stack([Kff.solve(-(Kfc @ D[isf][:, d])) for d in range(3)], 1)
        st = steps if rnd == 0 else max(2, steps // 4)
        X = Xall[mv]
        for k in range(st):
            X, _, _ = MP.project(X + D[mv] / st)
        Xall[mv] = X
    X = Xall[mv]
    Xf, dist, f = MP.project(X)
    tri = -np.ones(n, np.int64); B = np.zeros((n, 3))
    tt = Tg[f]
    _, bary = MG.closest_on_triangles(Xf, V[tt[:, 0]], V[tt[:, 1]], V[tt[:, 2]], bary=True)
    tri[pv[mv]] = f; B[pv[mv]] = bary
    Vn = V.copy(); Vn[pv[mv]] = Xf
    # turned-over faces: a moved face whose normal turned more than 90 deg from the old one
    T2 = QG.quad_tris(Q[patch_faces])
    n0 = MG.face_normals(V, T2); n1 = MG.face_normals(Vn, T2)
    flips = int(((n0 * n1).sum(1) < 0).sum())
    terr = max([float(np.linalg.norm(Vn[v] - x)) for v, x in tgt.items() if free[v]] or [0.0]) * 1e3
    return {"V": Vn, "tri": tri, "bary": B, "Tpatch": Tg, "flips": flips, "param_flips": 0, "outside": 0,
            "target_err_mm": round(terr, 4), "moved": int(free.sum()), "patch_faces": patch_faces, "patch_vertices": pv}
