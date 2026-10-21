"""MESH FAULTS of a whole skin: edges folded past a limit, inside-out faces, pairs of triangles passing through each
other, grouped into clusters (numpy / scipy only, no Blender; peak memory about 1 GB on a 1.4 M-triangle body).

The K1 map's instruments (woman2, 2026-10-21, `cases/woman2/K1_measure_2026-10-21.md`; proven there on a planted grid
and a planted copy of the skin) brought into the engine by build K1 (2026-10-21) with their proof
(`engine/checks/test_mesh_faults.py`, json beside it), unchanged in what they read.

  T, own = tris(sizes, flat)        fan triangles (0,1,2), (0,2,3) per quad and the owning polygon (mesh_geom.quads_tris:
                                    each quad's own diagonal counts as an edge too)
  F = folds(V, T)                   every interior edge: faces a, b, the angle between their normals (deg), its sense
                                    (+1 valley: the faces close towards each other on the outside; -1 ridge), whether the
                                    two faces are wound consistently
  inv = inverted(V, T, F=None)      per triangle: its normal points against the sum of its edge neighbours' normals
                                    (a face turned inside out against all round it)
  P = crossings(V, T)               (k, 2) triangle pairs that pass through each other and share no vertex: candidates
                                    from centroids within the two circumradii (KD-tree per z slab, size classes), then
                                    the six edge-through-triangle tests (Moller-Trumbore, t in [0, 1])
  C = clusters(V, T, fe, P, ...)    fold edges and crossing triangles within `join_m` (4.2 mm) of each other joined into
                                    one cluster; per cluster its counts, worst angle, inside-out faces, area, centre
  R = measure(V, T, deg=90)         the whole skin: counts (folds past deg and past 150, inside-out faces, crossing
                                    pairs, their area in cm2), the clusters, and the raw arrays
  r = in_region(R, vmask)           the same counts for the elements touching the vertices in `vmask` (a place and the
                                    border round it): used for "each place before and after"
"""
import os
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

_T = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
if _T not in sys.path:
    sys.path.append(_T)
import mesh_geom as MG  # noqa: E402


def tris(sizes, flat):
    return MG.quads_tris(sizes, flat)


def normals(V, T):
    n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    a = np.linalg.norm(n, axis=1)
    return n / np.maximum(a, 1e-30)[:, None], 0.5 * a


def folds(V, T):
    nf = len(T)
    E = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]])
    opp = np.concatenate([T[:, 2], T[:, 0], T[:, 1]])
    fid = np.tile(np.arange(nf), 3)
    k = np.minimum(E[:, 0], E[:, 1]) * np.int64(len(V)) + np.maximum(E[:, 0], E[:, 1])
    o = np.argsort(k, kind="stable"); ks = k[o]
    same = np.nonzero(ks[1:] == ks[:-1])[0]
    i, j = o[same], o[same + 1]
    a, b = fid[i], fid[j]; e = E[i]
    n, _ = normals(V, T)
    ang = np.degrees(np.arccos(np.clip((n[a] * n[b]).sum(1), -1, 1)))
    s = (n[a] * (V[opp[j]] - V[e[:, 0]])).sum(1)
    sense = np.sign(s).astype(np.int8)
    consistent = E[i, 0] == E[j, 1]
    return dict(e=e, a=a, b=b, ang=ang, sense=sense, consistent=consistent, opp_a=opp[i], opp_b=opp[j])


def inverted(V, T, F=None):
    if F is None:
        F = folds(V, T)
    n, _ = normals(V, T)
    s = np.zeros((len(T), 3))
    np.add.at(s, F["a"], n[F["b"]]); np.add.at(s, F["b"], n[F["a"]])
    return (n * s).sum(1) < 0


def _mt_hits(V, T, p):
    hit = np.zeros(len(p), bool)
    for a_, b_ in ((0, 1), (1, 0)):
        A = V[T[p[:, a_]]]; B = V[T[p[:, b_]]]
        e1 = B[:, 1] - B[:, 0]; e2 = B[:, 2] - B[:, 0]
        for k in range(3):
            o = A[:, k]; d = A[:, (k + 1) % 3] - o
            h = np.cross(d, e2); det = (e1 * h).sum(1)
            ok = np.abs(det) > 1e-18
            inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
            sv = o - B[:, 0]
            u = (sv * h).sum(1) * inv
            qv = np.cross(sv, e1)
            w = (d * qv).sum(1) * inv
            t = (e2 * qv).sum(1) * inv
            hit |= ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t >= 0) & (t <= 1)
    return hit


def _test(V, T, c, r, lo, hi, pr, chunk):
    if not len(pr):
        return pr
    out = []
    for s in range(0, len(pr), chunk):
        p = pr[s:s + chunk]
        p = p[np.linalg.norm(c[p[:, 0]] - c[p[:, 1]], axis=1) <= r[p[:, 0]] + r[p[:, 1]]]
        p = p[~(T[p[:, 0]][:, :, None] == T[p[:, 1]][:, None, :]).any((1, 2))]
        p = p[((lo[p[:, 0]] <= hi[p[:, 1]]) & (lo[p[:, 1]] <= hi[p[:, 0]])).all(1)]
        out.append(p[_mt_hits(V, T, p)])
    return np.concatenate(out)


def crossings(V, T, slab=0.01, piece=6000, chunk=400_000, log=None, tri_sel=None):
    """tri_sel (optional bool per triangle): only pairs with at least one triangle in it (the other may be anywhere)"""
    V = np.asarray(V, float)
    P = V[T]
    c = P.mean(1); r = np.linalg.norm(P - c[:, None], axis=2).max(1)
    lo = P.min(1); hi = P.max(1); del P
    bounds = [1.2e-3, 2.4e-3, 4.8e-3, 9.6e-3]
    cls = np.digitize(r, bounds)
    ks = [k for k in range(len(bounds) + 1) if (cls == k).any()]
    rmax = {k: float(r[cls == k].max()) for k in ks}
    members = {k: np.nonzero(cls == k)[0] for k in ks}
    z = c[:, 2]
    found = []; most = 0
    for z0 in np.arange(z.min(), z.max() + slab, slab):
        z1 = z0 + slab
        for ka in ks:
            A = members[ka]; core = A[(z[A] >= z0) & (z[A] < z1)]
            if not len(core):
                continue
            core = core[np.argsort(c[core, 0])]
            for kb in ks:
                if kb < ka:
                    continue
                Rr = rmax[ka] + rmax[kb]
                B = members[kb]; ring = B[(z[B] >= z0 - Rr) & (z[B] < z1 + Rr)]
                if not len(ring):
                    continue
                tb = cKDTree(c[ring])
                for s in range(0, len(core), piece):
                    cp = core[s:s + piece]
                    M = cKDTree(c[cp]).sparse_distance_matrix(tb, Rr, output_type="ndarray")
                    if not len(M):
                        continue
                    pr = np.c_[cp[M["i"]], ring[M["j"]]]; del M
                    if ka == kb:
                        zi, zj = z[pr[:, 0]], z[pr[:, 1]]
                        pr = pr[(zi < zj) | ((zi == zj) & (pr[:, 0] < pr[:, 1]))]
                    if tri_sel is not None:
                        pr = pr[tri_sel[pr[:, 0]] | tri_sel[pr[:, 1]]]
                    most = max(most, len(pr))
                    found.append(_test(V, T, c, r, lo, hi, pr, chunk))
                del tb
    pr = np.concatenate(found) if found else np.zeros((0, 2), np.int64)
    pr = np.unique(np.sort(pr, 1), axis=0) if len(pr) else pr.reshape(0, 2)
    if log is not None:
        log.update(dict(radius_classes_mm=[b * 1e3 for b in bounds], largest_candidate_batch=int(most), slab_m=slab))
    return pr


def clusters(V, T, fe, fang, fsense, fa, fb, P, inv, join_m=0.0042, cell_m=0.002):
    n, ar = normals(V, T)
    ct = np.unique(P.ravel()) if len(P) else np.zeros(0, np.int64)
    pts = np.r_[(V[fe[:, 0]] + V[fe[:, 1]]) / 2, V[T[ct]].mean(1)] if (len(fe) + len(ct)) else np.zeros((0, 3))
    if not len(pts):
        return [], np.zeros(0, int), ct
    cell = np.floor(pts / cell_m).astype(np.int64)
    uc, ix = np.unique(cell, axis=0, return_inverse=True); ix = ix.ravel()
    pr = cKDTree((uc + 0.5) * cell_m).query_pairs(join_m, output_type="ndarray")
    A = coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(len(uc), len(uc)))
    nc, lab_c = connected_components(A, directed=False)
    lab = lab_c[ix]
    tri_lab = np.full(len(T), -1); tri_lab[ct] = lab[len(fe):]
    out = []
    for c in range(nc):
        m = lab == c; mf = m[:len(fe)]; mc = m[len(fe):]
        tris_c = ct[mc]
        pairs_c = int((tri_lab[P[:, 0]] == c).sum()) if len(P) else 0
        faces_c = np.unique(np.r_[fa[mf], fb[mf], tris_c])
        p = pts[m]
        out.append(dict(id=int(c), centre_m=p.mean(0).round(5).tolist(), lo_m=p.min(0).round(5).tolist(), hi_m=p.max(0).round(5).tolist(),
                        fold_edges=int(mf.sum()), over_150=int((fang[mf] > 150).sum()),
                        worst_deg=round(float(fang[mf].max()), 2) if mf.any() else None,
                        valley=int((fsense[mf] > 0).sum()), ridge=int((fsense[mf] < 0).sum()),
                        inverted_faces=int(inv[faces_c].sum()), crossing_pairs=pairs_c, crossing_tris=int(mc.sum()),
                        crossing_area_mm2=round(float(ar[tris_c].sum() * 1e6), 3)))
    out.sort(key=lambda d: -(d["fold_edges"] + d["crossing_pairs"]))
    return out, lab, ct


def measure(V, T, deg=90.0, with_clusters=True, log=None):
    V = np.asarray(V, float); T = np.asarray(T, np.int64)
    F = folds(V, T)
    inv = inverted(V, T, F)
    P = crossings(V, T, log=log)
    _, ar = normals(V, T)
    sel = F["ang"] > deg
    u = np.unique(P.ravel()) if len(P) else np.zeros(0, np.int64)
    R = dict(folds_over_deg=int(sel.sum()), deg=deg, folds_over_150=int((F["ang"] > 150).sum()),
             max_deg=round(float(F["ang"].max()), 2), inverted_faces=int(inv.sum()), crossing_pairs=int(len(P)),
             crossing_area_cm2=round(float(ar[u].sum() * 1e4), 4), crossing_tris=int(len(u)),
             inconsistent_edges=int((~F["consistent"]).sum()))
    raw = dict(fe=F["e"][sel], fa=F["a"][sel], fb=F["b"][sel], fang=F["ang"][sel], fsense=F["sense"][sel], pairs=P, inv=inv, area=ar)
    if with_clusters:
        C, lab, ct = clusters(V, T, raw["fe"], raw["fang"], raw["fsense"], raw["fa"], raw["fb"], P, inv)
        raw["label"] = lab; raw["crossing_tri_ids"] = ct     # elements: fold edges first, then crossing triangles
        R["clusters"] = len(C)
        R["inverted_in_clusters"] = int(sum(d["inverted_faces"] for d in C))
        return dict(summary=R, clusters=C, raw=raw)
    return dict(summary=R, clusters=None, raw=raw)


def in_region(M, T, vmask, deg=None):
    """counts of measure()'s elements touching the vertices in vmask (a fold edge with an end in it, a crossing pair
    with a triangle touching it, an inside-out face touching it); deg: count only folds past it (default: measure's)"""
    raw = M["raw"]; T = np.asarray(T)
    tm = vmask[T].any(1)
    fe = raw["fe"]; fang = raw["fang"]
    fm = vmask[fe].any(1)
    if deg is not None:
        fm &= fang > deg
    P = raw["pairs"]
    pm = (tm[P[:, 0]] | tm[P[:, 1]]) if len(P) else np.zeros(0, bool)
    u = np.unique(P[pm].ravel()) if pm.any() else np.zeros(0, np.int64)
    return dict(folds=int(fm.sum()), over_150=int((fang[fm] > 150).sum()),
                worst_deg=round(float(fang[fm].max()), 2) if fm.any() else None,
                inverted_faces=int((raw["inv"] & tm).sum()), crossing_pairs=int(pm.sum()),
                crossing_area_mm2=round(float(raw["area"][u].sum() * 1e6), 3))
