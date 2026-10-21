"""SURFACE FAIRING by math (2026-10-19). Replaces a band of a surface with the smoothest surface that joins its
surroundings: minimise the squared umbrella Laplacian of the positions over the band, with every vertex outside the
band held fixed (a bi-Laplacian fill), then keep only each vertex's move along its normal (no sliding). Creases that
are real anatomy inside the band (strong concave curvature) can be held fixed. A clearance check against a protected
set (e.g. the arm) scales a vertex's move down wherever it would come closer than a minimum gap.

Why it exists: surface_analysis.py found a flat band then a bump on the outer curve of both breasts (curvature ~+20/m
falling to ~0 at 65-75 mm from the nipple, then ~+12/m at 85 mm) - "mild flattening" the person saw by eye. Fixing it
is a solve, not a sculpt.

usage (as a module): fair(V, F, band_mask, fixed_mask=None, protect_pts=None, min_gap=0.0005, no_outward=None) -> V_new, report
no_outward (2026-10-19, woman2 v5): a vertex mask whose moves may only go inward (along -normal). For two surfaces
pressed together: rounding a corner beside the contact cuts it back, and nothing beside the other surface moves toward it.

fill(V, F, free, weights="cotan") -> V_new, report   (2026-10-21, woman2 build 13a2)
  The free vertices solved as the smoothest surface joining the held rest, all three coordinates: minimise
  sum_i |(L x)_i|^2 / A_i with L the COTANGENT Laplacian of the input surface (weights >= 0) and A_i its lumped vertex
  area; rows reach two rings past the free set, so the fill meets the held skin in position and tangent plane. Solved on
  the faces within 3 rings of the free set only (seconds on a 686k-vertex body). Why cotangent: the operator is the
  surface's own geometry (the discrete mean-curvature normal), so the fill minimises curvature, not a connectivity-
  weighted average; fair()'s uniform (umbrella) weights also re-space vertices by connectivity. Measured on woman2
  build 13a2 (support loops 2.4-3.0 mm from the base loop): the median gaps moved 0.06-0.77 mm with cotangent weights
  (the right side's within 0.15 mm) and 0.03-0.61 mm with uniform ones (narrowed) - a small difference on that mesh.
  Use for a region whose shape is wrong (a step, a ridge, a crease) but whose surroundings are right; a large free set
  is filled as a thin plate, so its own form comes from its border alone. weights="umbrella" gives fair()'s operator on the same rows.

fill(V, F, free, weights="cotan", detail="keep", detail_from=None, detail_radius=0.010, gate=True) -> V_new, report
  DETAIL (2026-10-21, woman2 build 13a3). A thin plate has no fine relief: on woman2 13a2 the filled patches read
  0.24x the skin round them (relief() p75) and the person saw them as blurry. fill() now keeps detail by default:
  the patch is the smooth fill above plus a fine relief carried along the fill's normals (multiresolution editing: a
  smooth base and its detail; Kobbelt et al. 1998, Botsch & Sorkine 2008). The relief is READ with relief() - each
  vertex's height above the quadric best fitting the surface within detail_radius (10 mm: the band the orchestrator's
  10-pass averaging reads) - and the detail is TAKEN with relief() at EXTRACT x detail_radius (20 mm), so the band read
  is carried whole (planted, no gate: inside/around 0.44 taken at r, 0.84 at 1.5 r, 1.00 at 2 r). The source:
    detail_from=None    the input's own detail at each free vertex (right when the input's patch is good skin with a
                        wrong shape at a larger scale than the relief: a dent, a step, a bulge);
    an (n, 3) surface   another surface with the input's vertex order (e.g. the body before a defect was made);
    an (n,) array       heights in metres per vertex, taken by the caller (relief() at 2 r) from wherever the body's
                        own skin is.
  The gate (default on) never copies a place whose relief is an outlier against the held skin round the patch (5-12
  rings out): local RMS of the source's relief within detail_radius, modified z-score above 3.5 (Iglewicz & Hoaglin
  1993) - a crease or fold the fill is there to remove does not come back; that place and a radius round it get no
  detail, easing in over another radius. The report gives relief() p75 inside (the free set >= 3 rings in) and around
  for the input, the smooth fill and the output, and the gate's level and share. detail=None gives the fill as it was.
  Limit (measured on woman2 13a, build 13a3): when the input's patch is itself the deformation its own relief is 2.9x
  the surroundings'. The gate closes over most of it (54 % of the free set an outlier, 79 % gated): K2's crease stays
  out (2.3 deg, as the smooth fill), but the patch keeps only 0.37x the surroundings' relief. Without the gate the
  input's relief came back whole with pieces of the crease (seen in raking light). There, give detail_from - the
  body's own skin from before the defect.
  Proof: engine/tools/test_fill_detail.py (planted on a skin-like test surface; its json beside it).
"""
# ---- FUNCTION INDEX (engine/tools/func_index.py; grep 'def <name>' to jump) ----
#   umbrella_L(V, F)
#   vertex_normals(V, F)
#   dn_min(D, N, B)  - the most inward normal component of the moves, mm (report only)
#   fair(V, F, band, fixed, protect_pts, min_gap, no_o...)
#   cot_laplacian(V, F, clamp)  - cotangent Laplacian (off-diagonal +cot/2, diagonal minus the row sum) and lumped (o...
#   tri_adjacency(F, n)
#   ring_distance(A, seed, max_rings)  - edge-rings from the seed vertices (0 on them), max_rings + 1 beyond max_rings
#   ring_rows(A, ids, rings)  - sparse (len(ids), n) 0/1: for each id the vertices within `rings` edge-rings of it, i...
#   relief(V, F, ids, radius, N, A, chunk, max_rings)  - FINE RELIEF (2026-10-21, woman2 build 13a3): each vertex's h...
#   local_rms(A, V, ids, h, radius)  - RMS of the per-vertex values h over each id's surface neighbourhood within rad...
#   local_min_mean(A, V, ids, g, radius)  - minimum and weighted mean of g over each id's surface neighbourhood withi...
#   fill(V, F, free, weights, detail, detail_from, det...)  - the bi-Laplacian fill of the free vertices, positions i...
#   scalar_fill(V, F, free, values, A)  - (2026-10-21, build 13a4) a per-vertex scalar on the free vertices replaced ...
#   closest_on_mesh(P, Vt, Ft, k)  - closest point of each P on the triangles round its k nearest vertices of (Vt, Ft...
#   match_fill(V, F, free, target_V, target_F, iters)  - (2026-10-21, build 13a4) the free vertices take the FORM of ...
#   (+ 3 private helpers: grep '^def _')
# ---- END FUNCTION INDEX ----
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve, splu
from scipy.spatial import cKDTree


import os as _os_mg, sys as _sys_mg  # noqa: E402  (build A1: the engine's one closest point, normals, cotangent Laplacian)
_MG_DIR = _os_mg.path.normpath(_os_mg.path.join(_os_mg.path.dirname(_os_mg.path.abspath(__file__)), '.'))
if _MG_DIR not in _sys_mg.path:
    _sys_mg.path.append(_MG_DIR)
import mesh_geom as _MG  # noqa: E402


def umbrella_L(V, F):
    n = len(V); e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    A = sparse.coo_matrix((np.ones(len(e) * 2), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    deg = np.asarray(A.sum(1)).ravel()
    return sparse.eye(n) - sparse.diags(1 / np.maximum(deg, 1)) @ A


def vertex_normals(V, F):
    return _MG.vertex_normals(V, F, eps=1e-20)


def dn_min(D, N, B):
    """the most inward normal component of the moves, mm (report only)"""
    return np.einsum("ij,ij->i", D[B], N[B]).min() * 1000


def fair(V, F, band, fixed=None, protect_pts=None, min_gap=0.0005, no_outward=None, normal_only=True):
    band = band.copy()
    if fixed is not None: band &= ~fixed
    L = umbrella_L(V, F)
    Q = (L.T @ L).tocsr()
    B = np.where(band)[0]; R = np.where(~band)[0]
    QBB = Q[B][:, B].tocsc(); QBR = Q[B][:, R]
    Vn = V.copy()
    for k in range(3):
        Vn[B, k] = spsolve(QBB, -(QBR @ V[R, k]))
    N = vertex_normals(V, F)
    d = np.einsum("ij,ij->i", Vn - V, N)                      # normal-only move
    if not normal_only:
        # the full solved position (2026-10-19, woman2 v5): at a sharp corner, normal-only moves of neighbours along
        # diverging normals fold the surface; the solved positions themselves don't. no_outward clips the normal part.
        D = Vn - V
        if no_outward is not None:
            dn = np.einsum("ij,ij->i", D, N); D[no_outward] -= (np.maximum(dn[no_outward], 0.0))[:, None] * N[no_outward]
        out = V.copy(); out[B] += D[B]
        return out, {"band_vertices": int(len(B)), "move_mm": {"min": float(-np.linalg.norm(D[B], axis=1).max() * 1000) if False else float(dn_min(D, N, B)),
                     "max": float(np.linalg.norm(D[B], axis=1).max() * 1000), "rms": float(np.sqrt(np.mean(np.sum(D[B] ** 2, 1))) * 1000)},
                     "mode": "full positions"}
    move = np.zeros(len(V)); move[B] = d[B]
    if no_outward is not None:
        move[no_outward] = np.minimum(move[no_outward], 0.0)
    rep = {"band_vertices": int(len(B)), "move_mm": {"min": float(move[B].min() * 1000), "max": float(move[B].max() * 1000),
                                                     "rms": float(np.sqrt(np.mean(move[B] ** 2)) * 1000)}}
    if protect_pts is not None and len(protect_pts):
        tree = cKDTree(protect_pts)
        before, _ = tree.query(V[B])
        after, _ = tree.query(V[B] + move[B, None] * N[B])
        bad = (after < min_gap) & (after < before)
        # scale a vertex's move so it keeps at least min_gap (or its old clearance, if that was already smaller)
        for _ in range(8):
            if not bad.any(): break
            move[B[bad]] *= 0.5
            after, _ = tree.query(V[B] + move[B, None] * N[B])
            bad = (after < min_gap) & (after < before)
        rep["clearance_mm"] = {"before_min": float(before.min() * 1000), "after_min": float(after.min() * 1000),
                               "scaled_vertices": int(((after < before) & (before < min_gap * 4)).sum())}
    return V + move[:, None] * N, rep


def cot_laplacian(V, F, clamp=True):
    """cotangent Laplacian (off-diagonal +cot/2, diagonal minus the row sum) and lumped (one-third) vertex areas;
    clamp=True sets an obtuse triangle's negative cotangent to 0, so L stays an M-matrix (mesh_geom.cot_laplacian)"""
    return _MG.cot_laplacian(V, F, clamp)


def tri_adjacency(F, n):
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    A = sparse.coo_matrix((np.ones(len(e) * 2), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    return A


def ring_distance(A, seed, max_rings):
    """edge-rings from the seed vertices (0 on them), max_rings + 1 beyond max_rings"""
    d = np.full(A.shape[0], max_rings + 1, np.int32); cur = np.asarray(seed, bool).copy(); d[cur] = 0
    for k in range(1, max_rings + 1):
        new = ((A @ cur.astype(float)) > 0) & ~cur
        d[new] = k; cur |= new
    return d


def ring_rows(A, ids, rings):
    """sparse (len(ids), n) 0/1: for each id the vertices within `rings` edge-rings of it, itself included"""
    n = A.shape[0]; S = (A + sparse.identity(n, format="csr")).tocsr(); S.data[:] = 1.0
    X = sparse.csr_matrix((np.ones(len(ids)), (np.arange(len(ids)), ids)), shape=(len(ids), n))
    for _ in range(rings):
        X = (X @ S).tocsr(); X.data[:] = 1.0
    return X


def relief(V, F, ids=None, radius=0.010, N=None, A=None, chunk=2500, max_rings=16):
    """FINE RELIEF (2026-10-21, woman2 build 13a3): each vertex's height along its normal above the quadric that best fits
    the skin round it within `radius` (weights (1 - d^2/r^2)^2, the vertex itself left out; neighbours found along the
    surface's edges, so a second sheet nearby - an arm beside the side - never counts). A quadric takes the surface's own
    curvature exactly, and a fit is independent of how the vertices are spaced, so neither reads as relief; what is left is
    the surface's form finer than ~2 x radius. Returns metres per id (NaN where fewer than 10 neighbours).
    max_rings (2026-10-21, build 13a4): the neighbourhood is gathered over at most this many edge rings (16 as before);
    a radius past ~16 x the shortest edges needs more, or the ball is cut short and lopsided."""
    V = np.asarray(V, float); F = np.asarray(F, np.int64); n = len(V)
    ids = np.arange(n) if ids is None else np.asarray(ids, np.int64)
    if N is None:
        N = vertex_normals(V, F)
    if A is None:
        A = tri_adjacency(F, n)
    Fl = F[np.isin(F, ids).any(1)]
    el = np.linalg.norm(V[Fl[:, 0]] - V[Fl[:, 1]], axis=1)
    rings = int(min(max_rings, np.ceil(radius / max(np.percentile(el, 5), 1e-6))))
    out = np.full(len(ids), np.nan); r2 = radius * radius
    for c0 in range(0, len(ids), chunk):
        c = ids[c0:c0 + chunk]
        X = ring_rows(A, c, rings)
        cnt = np.diff(X.indptr); K = int(cnt.max())
        idx = np.full((len(c), K), -1, np.int64)
        rows = np.repeat(np.arange(len(c)), cnt); pos = np.arange(len(X.indices)) - np.repeat(X.indptr[:-1], cnt)
        idx[rows, pos] = X.indices
        P = V[idx] - V[c][:, None, :]
        nz = N[c]; hlp = np.where(np.abs(nz[:, :1]) < 0.9, [[1.0, 0, 0]], [[0, 1.0, 0]])
        a = np.cross(nz, hlp); a /= np.linalg.norm(a, axis=1, keepdims=True); b = np.cross(nz, a)
        x = np.einsum("nkj,nj->nk", P, a) / radius; y = np.einsum("nkj,nj->nk", P, b) / radius; z = np.einsum("nkj,nj->nk", P, nz)
        d2 = (P * P).sum(2)
        w = np.where((idx >= 0) & (idx != c[:, None]) & (d2 <= r2), (1 - d2 / r2) ** 2, 0.0)
        G = np.stack([x * x, x * y, y * y, x, y, np.ones_like(x)], -1)
        M = np.einsum("nki,nk,nkj->nij", G, w, G); rhs = np.einsum("nki,nk,nk->ni", G, w, z)
        M += np.eye(6)[None] * 1e-9 * np.trace(M, axis1=1, axis2=2)[:, None, None]
        ok = (w > 0).sum(1) >= 10
        coef = np.linalg.solve(M[ok], rhs[ok][..., None])[..., 0]
        o = np.full(len(c), np.nan); o[ok] = -coef[:, 5]; out[c0:c0 + chunk] = o
    return out


def _neighbourhoods(A, V, ids, radius, chunk=4000):
    """per chunk of ids: (chunk ids, rows, cols, weights (1 - d^2/r^2)^2 within radius), neighbours along the edges"""
    nb = A[ids].tocoo()
    e = np.linalg.norm(V[ids[nb.row]] - V[nb.col], axis=1)
    rings = int(min(16, np.ceil(radius / max(np.percentile(e, 5), 1e-6))))
    for c0 in range(0, len(ids), chunk):
        c = ids[c0:c0 + chunk]
        X = ring_rows(A, c, rings).tocoo()
        d2 = ((V[c[X.row]] - V[X.col]) ** 2).sum(1); m = d2 <= radius * radius
        yield c0, c, X.row[m], X.col[m], (1 - d2[m] / radius ** 2) ** 2


def local_rms(A, V, ids, h, radius):
    """RMS of the per-vertex values h over each id's surface neighbourhood within radius (NaN ignored)"""
    out = np.full(len(ids), np.nan); hv = np.nan_to_num(h); ok = np.isfinite(h).astype(float)
    for c0, c, r, cl, w in _neighbourhoods(A, V, ids, radius):
        w = w * ok[cl]
        out[c0:c0 + len(c)] = np.sqrt(np.bincount(r, w * hv[cl] ** 2, len(c)) / np.maximum(np.bincount(r, w, len(c)), 1e-30))
    return out


def local_min_mean(A, V, ids, g, radius):
    """minimum and weighted mean of g over each id's surface neighbourhood within radius"""
    mn = np.ones(len(ids)); mean = np.zeros(len(ids))
    for c0, c, r, cl, w in _neighbourhoods(A, V, ids, radius):
        m = np.full(len(c), np.inf); np.minimum.at(m, r, g[cl]); mn[c0:c0 + len(c)] = m
        mean[c0:c0 + len(c)] = np.bincount(r, w * g[cl], len(c)) / np.maximum(np.bincount(r, w, len(c)), 1e-30)
    return mn, mean


GATE_Z = 3.5   # Iglewicz & Hoaglin (1993): a modified z-score above 3.5 marks an outlier
EXTRACT = 2.0   # the detail is taken at twice the radius it is read at: relief() at r passes the band of relief()
                # at 2r almost whole (planted: read/source 1.00 at 2r, 0.44 at r, 0.84 at 1.5r; test_fill_detail.py)


def fill(V, F, free, weights="cotan", detail="keep", detail_from=None, detail_radius=0.010, gate=True, around_rings=(5, 12)):
    """the bi-Laplacian fill of the free vertices, positions in full; then (detail="keep", the default since 2026-10-21)
    the fine relief carried onto the filled patch - see DETAIL in the module docstring. detail=None: the smooth fill
    alone (fill() as it was before 2026-10-21). detail_from: None (the input's own detail), an (n, 3) surface with the
    input's vertex order (its detail), or an (n,) array of detail heights in metres (NaN = none), read by the caller at
    EXTRACT x detail_radius. Returns (V_new, report); the report's "gate" is the per-vertex weight the detail was carried
    with (pop it before saving the report as json)."""
    V = np.asarray(V, float); F = np.asarray(F, np.int64); free = np.asarray(free, bool); n = len(V)
    X, rep = _fill_smooth(V, F, free, weights)
    if not detail:
        rep["detail"] = None
        return X, rep
    A = tri_adjacency(F, n); re = EXTRACT * detail_radius
    d_out = ring_distance(A, free, around_rings[1] + 16)
    d_in = ring_distance(A, ~free, 3)
    core = free & (d_in >= 3)
    around = (~free) & (d_out >= around_rings[0]) & (d_out <= around_rings[1])
    fid, aid = np.nonzero(free)[0], np.nonzero(around)[0]
    zone = np.nonzero(d_out <= around_rings[1] + 16)[0]
    D_in = np.full(n, np.nan); D_in[zone] = relief(V, F, zone, re, A=A)          # the input's own detail
    if detail_from is None:
        D, src_kind = D_in, "the input's own detail"
    else:
        dfm = np.asarray(detail_from, float)
        if dfm.ndim == 2:
            D = np.full(n, np.nan); near = np.nonzero(d_out <= 16)[0]; D[near] = relief(dfm, F, near, re, A=A)
            src_kind = "the detail of detail_from (a surface with the input's vertex order)"
        else:
            D, src_kind = dfm.copy(), "detail_from heights"
    g = np.zeros(n); g[fid] = 1.0; z_stats = None
    if gate:
        L_ar = local_rms(A, V, aid, D_in, detail_radius); L_fr = local_rms(A, V, fid, D, detail_radius)
        la = L_ar[np.isfinite(L_ar)]; med = np.median(la); mad = np.median(np.abs(la - med))
        z = 0.6745 * (np.nan_to_num(L_fr, nan=0.0) - med) / max(mad, 1e-12)
        graw = np.ones(n); graw[fid] = (z <= GATE_Z).astype(float)
        # an outlier place and a whole radius round it are not copied; the weight then eases in over another radius
        gmin, _ = local_min_mean(A, V, fid, graw, detail_radius)
        g2 = np.ones(n); g2[fid] = gmin
        _, gm = local_min_mean(A, V, fid, g2, detail_radius)
        g = np.zeros(n); g[fid] = gm
        z_stats = {"around_local_rms_median_mm": float(med * 1e3), "gate_level_mm": float((med + GATE_Z * mad / 0.6745) * 1e3),
                   "outlier_share_of_free": float((graw[fid] == 0).mean()), "gated_share_of_free": float((g[fid] < 0.5).mean())}
    Nx = vertex_normals(X, F)
    add = np.zeros(n); add[fid] = g[fid] * np.nan_to_num(D[fid])
    out = X.copy(); out[fid] += add[fid, None] * Nx[fid]

    def p75(Vv, m):
        return float(np.nanpercentile(np.abs(relief(Vv, F, np.nonzero(m)[0], detail_radius, A=A)), 75) * 1e3)
    rp = {"around": p75(V, around), "inside_input": p75(V, core), "inside_smooth_fill": p75(X, core), "inside_out": p75(out, core)}
    rep["detail"] = {"source": src_kind, "read_radius_mm": detail_radius * 1e3, "extract_radius_mm": re * 1e3, "gate": z_stats,
                     "added_mm_p75_max": [float(np.percentile(np.abs(add[fid]), 75) * 1e3), float(np.abs(add[fid]).max() * 1e3)],
                     "relief_p75_mm": rp, "inside_over_around": rp["inside_out"] / max(rp["around"], 1e-12),
                     "core_vertices": int(core.sum()), "around_vertices": int(around.sum())}
    rep["gate"] = g
    return out, rep


def _fill_smooth(V, F, free, weights="cotan"):
    """the bi-Laplacian fill of the free vertices, positions in full (fill() before 2026-10-21)"""
    V = np.asarray(V, float); F = np.asarray(F, np.int64); free = np.asarray(free, bool); n = len(V)
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    A = sparse.coo_matrix((np.ones(len(e) * 2), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n)).tocsr()
    near = free.copy()
    for _ in range(3):
        near |= (A @ near.astype(float)) > 0
    Fl = F[near[F].all(1)]
    ids = np.unique(Fl); loc = -np.ones(n, np.int64); loc[ids] = np.arange(len(ids))
    Vl = V[ids]; Fl = loc[Fl]
    if weights == "cotan":
        Lm, area = cot_laplacian(Vl, Fl)
        Minv = sparse.diags(1.0 / np.maximum(area, 1e-12)).tocsr()
    else:
        Lm = -umbrella_L(Vl, Fl).tocsr(); Minv = sparse.identity(len(Vl), format="csr")
    rows_m = near & ~((A @ (~near).astype(float)) > 0)          # the whole one-ring inside the local mesh
    rows = np.nonzero(rows_m[ids])[0]
    Lr = Lm[rows]; Q = (Lr.T @ Minv[rows][:, rows] @ Lr).tocsr()
    fl = np.nonzero(free[ids])[0]; hl = np.nonzero(~free[ids])[0]
    lu = splu(Q[fl][:, fl].tocsc()); Qfh = Q[fl][:, hl]
    X = Vl.copy()
    for k in range(3):
        X[fl, k] = lu.solve(-(Qfh @ Vl[hl, k]))
    out = V.copy(); out[ids[fl]] = X[fl]
    d = np.linalg.norm(out - V, axis=1)
    return out, {"free": int(len(fl)), "local_vertices": int(len(ids)), "rows": int(len(rows)), "weights": weights,
                 "move_mm": {"max": float(d.max() * 1e3), "rms_free": float(np.sqrt(np.mean(d[free] ** 2)) * 1e3)}}


def scalar_fill(V, F, free, values, A=None):
    """(2026-10-21, build 13a4) a per-vertex scalar on the free vertices replaced by the smoothest field joining the
    held values round them: the bi-Laplacian of fill() (cotangent weights of V, rows two rings past the free set, so the
    field meets the held values with their slope) applied to one value per vertex instead of the positions"""
    from scipy.sparse.linalg import splu as _splu
    n = len(V); free = np.asarray(free, bool); values = np.asarray(values, float)
    if A is None:
        A = tri_adjacency(F, n)
    near = free.copy()
    for _ in range(3):
        near |= (A @ near.astype(float)) > 0
    Fl = F[near[F].all(1)]
    ids = np.unique(Fl); loc = -np.ones(n, np.int64); loc[ids] = np.arange(len(ids)); Fl = loc[Fl]
    Lm, area = cot_laplacian(V[ids], Fl)
    Minv = sparse.diags(1.0 / np.maximum(area, 1e-12)).tocsr()
    rows_m = near & ~((A @ (~near).astype(float)) > 0)
    rows = np.nonzero(rows_m[ids])[0]
    Lr = Lm[rows]; Q = (Lr.T @ Minv[rows][:, rows] @ Lr).tocsr()
    fl = np.nonzero(free[ids])[0]; hl = np.nonzero(~free[ids])[0]
    x = _splu(Q[fl][:, fl].tocsc()).solve(-(Q[fl][:, hl] @ values[ids[hl]]))
    out = values.copy(); out[ids[fl]] = x
    return out


def closest_on_mesh(P, Vt, Ft, k=4):
    """closest point of each P on the triangles round its k nearest vertices of (Vt, Ft) (vectorised; on a regular
    mesh the closest triangle touches one of them - checked against brute force in test_match_fill.py). Since build
    A1 the engine's one implementation: mesh_geom.closest_on_mesh"""
    return _MG.closest_on_mesh(P, Vt, Ft, k)


def _closest_tri_vec(p, a, b, c):
    """Ericson's closest point on a triangle, vectorised (mesh_geom.closest_on_triangles)"""
    return _MG.closest_on_triangles(p, a, b, c)


def match_fill(V, F, free, target_V, target_F, iters=3):
    """(2026-10-21, build 13a4) the free vertices take the FORM of a target surface - e.g. the body's other side mirrored,
    where a person said that side is right - plus the smooth offset between the two surfaces carried in from the held
    skin round them: per vertex the offset d to the target along the vertex's normal is read on the free set and the
    held skin round it, d is replaced on the free set by its bi-Laplacian fill (scalar_fill) phi, and each free vertex
    moves along its normal by phi - d (repeated `iters` times on the moved skin). Whatever the target has at every
    scale - its curvature, its 1-4 cm form, its fine relief - comes across; the global difference between the two
    sides (one sits lower, further out) is kept as the smooth phi, so nothing outside the free set moves and the seam
    is as smooth as the offset. Returns (V_new, report)."""
    V = np.asarray(V, float); F = np.asarray(F, np.int64); free = np.asarray(free, bool); n = len(V)
    A = tri_adjacency(F, n)
    zone = free.copy()
    for _ in range(6):
        zone |= (A @ zone.astype(float)) > 0
    zid = np.nonzero(zone)[0]
    N = vertex_normals(V, F)
    X = V.copy(); rep = {"iters": []}
    for it in range(iters):
        Q, dist = closest_on_mesh(X[zid], target_V, target_F)
        d = np.zeros(n); d[zid] = ((X[zid] - Q) * N[zid]).sum(1)
        phi = scalar_fill(V, F, free, d, A=A)
        step = np.zeros(n); step[free] = (phi - d)[free]
        X[free] += step[free, None] * N[free]
        rep["iters"].append({"move_mm_max": float(np.abs(step).max() * 1e3), "gap_to_target_mm_p99": float(np.percentile(dist, 99) * 1e3)})
    mv = np.linalg.norm(X - V, axis=1)
    rep["move_mm"] = {"max": float(mv.max() * 1e3), "rms_free": float(np.sqrt(np.mean(mv[free] ** 2)) * 1e3)}
    return X, rep
