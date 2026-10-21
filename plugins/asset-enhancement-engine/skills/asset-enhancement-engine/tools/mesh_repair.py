"""MESH REPAIR at the root: a crumpled patch refilled, two sheets that pass through each other made to touch (build K1,
2026-10-21: the base body's own mesh faults - eye-socket floors, toe roots, lips, finger roots, thumbs, an ear, nose
spots). Vertex moves only: connectivity, UVs and every per-vertex array stay valid. numpy / scipy only.

  F = local_faults(V, T, vmask, margin=0.01, deg=90)
        the K1 instruments (engine/checks/mesh_faults.py) over the triangles touching `vmask`, crossings tested against
        every triangle within `margin` of it: folds past deg, past 150, worst, inside-out faces, crossing pairs, area
  X = refill(V, B, T, free)
        the root fix where a sculpt folded the skin: the displacement of V over a sound base surface B (same faces; e.g.
        the base body's cage subdivided without its sculpt) is replaced on the free vertices by the smoothest field
        joining the displacement round them, so the skin there follows the base's form plus the sculpt's displacement
        as it runs in from round the fault (cotangent weights of B)
  w = winding(P, V, T) / turned(V, T, ids)
        generalized winding number of points (1 inside, 0 outside, 2 inside two overlapping parts); turned() reads it
        just inside each vertex: ~0 a pleat turned inside out, ~2 the vertex lies inside another part
  X, rep = unfold(V, T, free, detail="keep")
        a crumpled patch (edges folded back on themselves, faces turned inside out, the patch passing through itself)
        replaced by the smoothest patch joining the skin round it: surface_fairing.fill with UNIFORM (umbrella) weights -
        cotangent weights read off crumpled triangles are meaningless - and the skin's own fine relief carried back
        (gated, so the crumple itself is not copied; detail=None: the smooth fill alone)
  X, rep = separate(V, T, region, clearance=4e-5, ease_m=0.004, iters=10, W=None)
        two parts that pass through each other made to touch at their mid-surface: a vertex lies inside the other part
        when the winding number just inside it reads ~2; it goes back along its own inward normal by half its depth (the
        distance to the first face it meets that way, two rings round it excluded) plus half the clearance, the other
        part's vertices likewise, so they meet with `clearance` between them; the push eases out to nothing over
        `ease_m` round the contact (bi-Laplacian fill of the push, cotangent weights of W, default V) and the step
        repeats on the moved skin until no pair crosses. No sheet labels are needed
  m = dilate(T, mask, rings);  t, f = ray_first_hit(O, D, V, Tk, tmax)
Proof: engine/tools/test_mesh_repair.py (winding numbers of two overlapping spheres; a planted pleat on a sculpted
sphere refilled over the sphere; a crumpled disc on a sheet unfolded; the two spheres separated to touch; json beside it).
Found on the base body (build K1): a sculpt's faults sit on a sound subdivision surface, so refill() fixes them at the
root; separate() only where two parts press through each other; unfold() where the base surface itself is crumpled.
"""
import os
import sys

import numpy as np
from scipy import sparse

_H = os.path.dirname(os.path.abspath(__file__))
for _p in (_H, os.path.normpath(os.path.join(_H, "..", "checks"))):
    if _p not in sys.path:
        sys.path.append(_p)
import mesh_geom as MG  # noqa: E402
import mesh_faults as MF  # noqa: E402
import surface_fairing as SF  # noqa: E402


def _sub(V, T, vmask, margin):
    vm = np.asarray(vmask, bool)
    lo = V[vm].min(0) - margin; hi = V[vm].max(0) + margin
    P = V[T]
    near = ((P.max(1) >= lo) & (P.min(1) <= hi)).all(1)
    return np.nonzero(near)[0]


def local_faults(V, T, vmask, margin=0.01, deg=90.0, pairs_out=False):
    V = np.asarray(V, float); T = np.asarray(T, np.int64); vm = np.asarray(vmask, bool)
    sub = _sub(V, T, vm, margin); Ts = T[sub]
    tm = vm[Ts].any(1)
    F = MF.folds(V, Ts)
    em = vm[F["e"]].any(1)
    fold = em & (F["ang"] > deg)
    inv = MF.inverted(V, Ts, F) & tm
    P = MF.crossings(V, Ts, tri_sel=tm)
    _, ar = MF.normals(V, Ts)
    u = np.unique(P.ravel()) if len(P) else np.zeros(0, np.int64)
    out = dict(folds=int(fold.sum()), over_150=int((F["ang"][em] > 150).sum()),
               worst_deg=round(float(F["ang"][em].max()), 2) if em.any() else None,
               inverted_faces=int(inv.sum()), crossing_pairs=int(len(P)), crossing_area_mm2=round(float(ar[u].sum() * 1e6), 4))
    if pairs_out:
        out["_pairs"] = sub[P] if len(P) else np.zeros((0, 2), np.int64)
        out["_fold_edges"] = F["e"][fold]
        out["_inverted_tris"] = sub[inv]
    return out


def refill(V, B, T, free, A=None):
    """the displacement of V over a sound base surface B with the same faces (e.g. a sculpt over its unsculpted
    subdivision surface) replaced on the free vertices by the smoothest field joining the displacement round them
    (bi-Laplacian, cotangent weights of B, which are meaningful where V's are not): X = B + filled(V - B). Outside
    `free` X == V exactly."""
    V = np.asarray(V, float); B = np.asarray(B, float); free = np.asarray(free, bool)
    if A is None:
        A = SF.tri_adjacency(T, len(V))
    D = V - B
    Dn = D.copy()
    for c in range(3):
        Dn[:, c] = SF.scalar_fill(B, T, free, D[:, c], A=A)
    X = V.copy(); X[free] = B[free] + Dn[free]
    return X


def unfold(V, T, free, detail="keep"):
    X, rep = SF.fill(np.asarray(V, float), np.asarray(T, np.int64), np.asarray(free, bool), weights="uniform", detail=detail)
    rep.pop("gate", None)
    return X, rep


def solid_angles(P, A, B, C):
    """(len(P),) summed signed solid angle of triangles (A, B, C) seen from each point (Van Oosterom & Strackee 1983)"""
    out = np.zeros(len(P))
    step = max(1, 4_000_000 // max(len(A), 1))
    for s0 in range(0, len(P), step):
        p = P[s0:s0 + step, None, :]
        a = A[None] - p; b = B[None] - p; c = C[None] - p
        la = np.linalg.norm(a, axis=2); lb = np.linalg.norm(b, axis=2); lc = np.linalg.norm(c, axis=2)
        num = (a * np.cross(b, c)).sum(2)
        den = la * lb * lc + (a * b).sum(2) * lc + (b * c).sum(2) * la + (c * a).sum(2) * lb
        out[s0:s0 + step] = (2 * np.arctan2(num, den)).sum(1)
    return out


def winding(P, V, T, near_r=0.03):
    """generalized winding number of points P (all near one another) for the closed surface (V, T): 1 inside, 0 outside,
    2 inside two overlapping parts. Triangles within near_r of the points' centre are summed per point; the rest once,
    at the centre (their solid angle changes little over a few mm)"""
    P = np.asarray(P, float); V = np.asarray(V, float)
    c = P.mean(0); rad = np.linalg.norm(P - c, axis=1).max()
    tc = V[T].mean(1)
    near = np.linalg.norm(tc - c, axis=1) < near_r + rad
    Tn, Tf = T[near], T[~near]
    w = solid_angles(P, V[Tn[:, 0]], V[Tn[:, 1]], V[Tn[:, 2]])
    wf = 0.0
    for s0 in range(0, len(Tf), 1_000_000):
        t = Tf[s0:s0 + 1_000_000]
        wf += solid_angles(c[None], V[t[:, 0]], V[t[:, 1]], V[t[:, 2]])[0]
    return (w + wf) / (4 * np.pi)


def turned(V, T, ids, eps=2e-5, near_r=0.015):
    """winding number just inside each vertex in ids (v - eps * normal): ~1 sound, ~0 the surface there is turned
    inside out (a pleat folded back on itself), ~2 the vertex lies inside another part of the body (two parts passing
    through each other)"""
    N = MG.vertex_normals(V, T)
    return winding(V[ids] - eps * N[ids], V, T, near_r=near_r)


def dilate(T, mask, rings, n=None):
    A = SF.tri_adjacency(T, len(mask) if n is None else n)
    m = np.asarray(mask, bool).copy()
    for _ in range(rings):
        m |= (A @ m.astype(float)) > 0
    return m


def ray_first_hit(O, D, V, Tk, tmax):
    """first hit of each ray (O + t D, 0 < t < tmax) on triangles Tk: (t, face index into Tk, or -1)"""
    best_t = np.full(len(O), np.inf); best_f = -np.ones(len(O), np.int64)
    A = V[Tk[:, 0]]; e1 = V[Tk[:, 1]] - A; e2 = V[Tk[:, 2]] - A
    step = max(1, 2_000_000 // max(len(Tk), 1))
    for s0 in range(0, len(O), step):
        o = O[s0:s0 + step, None, :]; d = D[s0:s0 + step, None, :]
        h = np.cross(d, e2[None]); det = (e1[None] * h).sum(2)
        ok = np.abs(det) > 1e-20
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        sv = o - A[None]; u = (sv * h).sum(2) * inv
        q = np.cross(sv, e1[None]); w = (d * q).sum(2) * inv; t = (e2[None] * q).sum(2) * inv
        hit = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 1e-9) & (t < tmax)
        t = np.where(hit, t, np.inf)
        j = np.argmin(t, 1); tt = t[np.arange(len(j)), j]
        best_t[s0:s0 + step] = tt; best_f[s0:s0 + step] = np.where(np.isfinite(tt), j, -1)
    return best_t, best_f


def separate(V, T, region, clearance=4e-5, ease_m=0.004, iters=10, margin=0.01, dmax=0.004, near_m=0.003,
             W=None, log=None):
    """two parts of the surface that pass through each other made to touch (see the module docstring). A vertex is
    inside another part when the winding number just inside it is ~2 (turned()); its depth is the distance along its
    inward normal to the first face it meets (the other part's surface, which it exits there), two rings round it
    excluded. W: positions to read the easing's cotangent weights from (a clean surface with the same faces, e.g. the
    unsculpted base), default V."""
    V = np.asarray(V, float).copy(); T = np.asarray(T, np.int64); region = np.asarray(region, bool)
    W = V if W is None else np.asarray(W, float)
    X0 = V.copy(); rep = {"iters": []}
    A = SF.tri_adjacency(T, len(V))
    I = sparse.identity(len(V), format="csr")
    A1 = ((A + I) > 0).astype(np.float32)
    A2 = (A1 @ A1).tocsr()
    sub = _sub(V, T, region, margin); Ts = T[sub]
    from scipy.spatial import cKDTree
    for it in range(iters):
        lf = local_faults(V, T, region, margin=margin, pairs_out=True)
        P = lf["_pairs"]
        if not len(P):
            break
        dk, _ = cKDTree(V[T[np.unique(P.ravel())]].mean(1)).query(V, distance_upper_bound=near_m)
        cand = np.nonzero(np.isfinite(dk) & region)[0]
        Nv = MG.vertex_normals(V, T)
        w = winding(V[cand] - 2e-5 * Nv[cand], V, T, near_r=0.015)
        cand = cand[w > 1.5]
        if not len(cand):
            rep["iters"].append({"pairs": int(len(P)), "inside": 0}); break
        tt, ff = ray_first_hit(V[cand], -Nv[cand], V, Ts, dmax)
        # skip faces next to the vertex: take the first hit beyond its two rings
        fv = Ts[np.maximum(ff, 0)]
        adj = np.zeros(len(cand), bool)
        for j in range(3):
            adj |= np.asarray(A2[cand, fv[:, j]]).ravel() > 0
        if adj.any():
            keep = np.ones(len(Ts), bool)
            for k in np.nonzero(adj)[0]:
                ring = np.nonzero(np.asarray(A2[cand[k]].todense()).ravel() > 0)[0]
                bad = np.isin(Ts, ring).any(1)
                t2, f2 = ray_first_hit(V[cand[[k]]], -Nv[cand[[k]]], V, Ts[~bad], dmax)
                tt[k] = t2[0]; ff[k] = -1 if f2[0] < 0 else np.nonzero(~bad)[0][f2[0]]
        ok = ff >= 0
        m = cand[ok]
        push = np.zeros((len(V), 3)); hit = np.zeros(len(V), bool)
        amt = (tt[ok] + clearance) * 0.5 + 1e-6
        push[m] = -Nv[m] * amt[:, None]; hit[m] = True
        if not hit.any():
            rep["iters"].append({"pairs": int(len(P)), "inside": int(len(cand)), "pushed": 0}); break
        d, _ = cKDTree(V[hit]).query(V, distance_upper_bound=ease_m)
        free = np.isfinite(d) & ~hit
        out = push.copy()
        if free.any():
            for c in range(3):
                out[:, c] = SF.scalar_fill(W, T, free, push[:, c], A=A)
        V = V + out
        rep["iters"].append({"pairs": int(len(P)), "inside": int(len(cand)), "pushed": int(hit.sum()), "eased": int(free.sum()),
                             "push_mm_max": round(float(np.linalg.norm(push, axis=1).max() * 1e3), 4)})
    rep["after"] = local_faults(V, T, region, margin=margin)
    mv = np.linalg.norm(V - X0, axis=1)
    rep["move_mm"] = {"max": float(mv.max() * 1e3), "moved": int((mv > 0).sum())}
    return V, rep
