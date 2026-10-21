"""Phase 2 skin and fur-tip checks (criteria C2, C3, C8 of engine/log/PHASE2_ROUND0.md).

C2 skin_integrity(v, f)        the skin is ONE closed, manifold, consistently oriented surface with NO self-intersection
                               (clefts and between the toes included). Topology by edge / corner-fan counting; the
                               self-intersection by an exact triangle-triangle test over a uniform spatial grid (each
                               candidate pair is tested in exactly one cell), in bounded chunks: ~2-3 M faces in minutes
                               and well under 3 GB.
C3 skin_vs_envelope(...)       the TRUE distance from the skin to the fur envelope (twosided.MeshDist, exact point ->
                               triangle) equals the region's coat depth within +-0.5 mm. Why 0.5 mm: the Phase 1
                               precision rule (person, LOG #79) gives every reference position at +-0.5 mm, so a skin
                               cannot be held tighter to the envelope than the envelope's own numbers. Reported per
                               region as AREA over the tolerance (mm2 and fraction), not a mean; patches over the 0.2 mm
                               watch level are listed with place and peak so sub-tolerance defects are still SEEN.
C8 fur_tips_vs_envelope(...)   strand tip points against the envelope, SIGNED (+ = the tip stands out of the envelope),
                               per region; a region fails where more than MAX_TIP_FRAC of its tips stand out or fall
                               short by more than that region's coat-depth spread.

All lengths are metres (the meshes are z-up metres); reports give mm. The envelope distance always comes from
tripo_rebuild/twosided.MeshDist (proven in Phase 1); it is not reimplemented here.
Proofs on planted failures: skin_checks_prove.py (same folder).
"""
import os
import sys
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = os.path.dirname(os.path.abspath(__file__))
TRIPO = os.path.normpath(os.path.join(HERE, "..", "..", "tripo_rebuild"))
if TRIPO not in sys.path:
    sys.path.insert(0, TRIPO)
from twosided import MeshDist, area_samples  # noqa: E402

# ---- pass marks (each with its reason)
TOL_C3 = 0.0005      # +-0.5 mm: the Phase 1 precision rule (LOG #79) - reference positions are known to +-0.5 mm
WATCH_C3 = 0.0002    # 0.2 mm: listed, not failed - twice the 0.1 mm floor at which Phase 1's area metrics (twosided.
                     # prove_small) resolve a 0.3 mm bump, so a sub-tolerance bump/dent is still reported with its place
MAX_AREA_C3 = 0.5    # mm2 of a region over TOL_C3 that fails it: >= 4 samples at the default 8 /mm2 (one stray sample
                     # cannot fail a region) and ~ a 0.8 mm-wide patch, smaller than any feature Phase 1 measured.
                     # An AREA, not a fraction, because a 3 mm hole is 0.02 % of the body and a fraction would pass it.
MAX_TIP_FRAC = 0.10  # C8: tips may stray past the spread (stray guard hairs) but not more than 1 in 10 per region; a
                     # coat whose tips scatter normally inside a 2-sigma band leaves ~5 % outside, so 10 % is 2x that.


def _ms(t0):
    return f"{time.time() - t0:6.1f} s"


# =====================================================================  C2: integrity
def _edges(f):
    """directed edges of every face corner: (a, b) and the corner index of a and of b"""
    F = len(f)
    a = np.concatenate([f[:, 0], f[:, 1], f[:, 2]]); b = np.concatenate([f[:, 1], f[:, 2], f[:, 0]])
    r3 = np.arange(F, dtype=np.int32) * 3
    ca = np.concatenate([r3, r3 + 1, r3 + 2])
    cb = np.concatenate([r3 + 1, r3 + 2, r3])
    return a, b, ca, cb


def topology(f, nv):
    """open / non-manifold edges, non-manifold (pinched) vertices, orientation flips, shells - on face-referenced
    vertices only. Returns a dict of counts plus up to 20 example vertex ids per defect."""
    a, b, ca, cb = _edges(f)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    key = lo.astype(np.int64) * nv + hi
    o = np.argsort(key, kind="stable"); ks = key[o]
    first = np.r_[True, ks[1:] != ks[:-1]]; start = np.flatnonzero(first); cnt = np.diff(np.r_[start, len(ks)])
    open_e = start[cnt == 1]; nonman_e = start[cnt > 2]
    # manifold edges: the two uses must run in opposite directions (consistent orientation)
    two = start[cnt == 2]; i1, i2 = o[two], o[two + 1]
    flipped = int((a[i1] == a[i2]).sum())
    # corner fans: join the corners of the shared edge's two faces at each end vertex
    cu1 = np.where(a[i1] == lo[i1], ca[i1], cb[i1]); cw1 = np.where(a[i1] == lo[i1], cb[i1], ca[i1])
    cu2 = np.where(a[i2] == lo[i2], ca[i2], cb[i2]); cw2 = np.where(a[i2] == lo[i2], cb[i2], ca[i2])
    nc = 3 * len(f)
    g = coo_matrix((np.ones(2 * len(two), np.int8), (np.r_[cu1, cw1], np.r_[cu2, cw2])), shape=(nc, nc))
    _, comp = connected_components(g, directed=False)
    cv = f.reshape(-1)                                                   # vertex of each corner
    pair = np.unique(cv.astype(np.int64) * nc + comp)                    # distinct (vertex, fan) pairs
    fans = np.bincount((pair // nc).astype(np.int64), minlength=nv)
    pinched = np.flatnonzero(fans > 1)
    # shells: connected components of the edge graph of the referenced vertices
    used = np.unique(f)
    ge = coo_matrix((np.ones(len(a), np.int8), (a, b)), shape=(nv, nv))
    _, vl = connected_components(ge, directed=False)
    shells = len(np.unique(vl[used])); sizes = np.bincount(np.unique(vl[used], return_inverse=True)[1].ravel())
    rep = (f[:, 0] == f[:, 1]) | (f[:, 1] == f[:, 2]) | (f[:, 2] == f[:, 0])
    return dict(open_edges=int(len(open_e)), nonmanifold_edges=int(len(nonman_e)), pinched_vertices=int(len(pinched)),
                orientation_flips=flipped, shells=int(shells), shell_faces_sizes=sorted((sizes).tolist(), reverse=True)[:5],
                repeated_index_faces=int(rep.sum()),
                ex_open=np.unique(np.r_[a[o[open_e]], b[o[open_e]]])[:20].tolist(),
                ex_nonman=np.unique(np.r_[a[o[nonman_e]], b[o[nonman_e]]])[:20].tolist(), ex_pinched=pinched[:20].tolist())


def _cross(x, y):
    return np.stack([x[:, 1] * y[:, 2] - x[:, 2] * y[:, 1], x[:, 2] * y[:, 0] - x[:, 0] * y[:, 2], x[:, 0] * y[:, 1] - x[:, 1] * y[:, 0]], 1)


def _dot(x, y):
    return np.einsum("ij,ij->i", x, y)


def _seg_tri(P0, P1, A, B, C):
    """closed segment P0P1 meets closed triangle ABC (Moller-Trumbore); segments parallel to the plane -> False"""
    e1, e2, d = B - A, C - A, P1 - P0
    h = _cross(d, e2); a = _dot(e1, h)
    scale = np.linalg.norm(d, axis=1) * np.linalg.norm(e1, axis=1) * np.linalg.norm(e2, axis=1)
    ok = np.abs(a) > 1e-12 * scale; a = np.where(ok, a, 1.0)
    s = P0 - A; u = _dot(s, h) / a; q = _cross(s, e1); w = _dot(d, q) / a; t = _dot(e2, q) / a
    return ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t >= 0) & (t <= 1)


def _orient2(p, q, r):
    return (q[:, 0] - p[:, 0]) * (r[:, 1] - p[:, 1]) - (q[:, 1] - p[:, 1]) * (r[:, 0] - p[:, 0])


def _in_tri2(p, A, B, C):
    o1, o2, o3 = _orient2(A, B, p), _orient2(B, C, p), _orient2(C, A, p)
    return ((o1 > 0) & (o2 > 0) & (o3 > 0)) | ((o1 < 0) & (o2 < 0) & (o3 < 0))


def _coplanar_overlap(TA, TB, nA):
    """2D overlap of coplanar triangles (projected along A's dominant normal axis): a proper edge crossing, or a
    vertex / centroid strictly inside the other. Shared boundaries alone do not count."""
    ax = np.argmax(np.abs(nA), axis=1); keep = np.array([[1, 2], [0, 2], [0, 1]])[ax]
    kk = np.repeat(keep[:, None, :], 3, axis=1)
    A2 = np.take_along_axis(TA, kk, axis=2); B2 = np.take_along_axis(TB, kk, axis=2)
    hit = np.zeros(len(TA), bool)
    for i in range(3):
        p, q = A2[:, i], A2[:, (i + 1) % 3]
        for j in range(3):
            s, t = B2[:, j], B2[:, (j + 1) % 3]
            d1, d2, d3, d4 = _orient2(p, q, s), _orient2(p, q, t), _orient2(s, t, p), _orient2(s, t, q)
            hit |= (d1 * d2 < 0) & (d3 * d4 < 0)
        hit |= _in_tri2(A2[:, i], B2[:, 0], B2[:, 1], B2[:, 2]) | _in_tri2(B2[:, i], A2[:, 0], A2[:, 1], A2[:, 2])
    hit |= _in_tri2(A2.mean(1), B2[:, 0], B2[:, 1], B2[:, 2]) | _in_tri2(B2.mean(1), A2[:, 0], A2[:, 1], A2[:, 2])
    return hit


def _tri_tri(v, f, ia, ib, fn):
    """exact intersection of face pairs (ia, ib) that share at most ONE vertex (edge-neighbours are never passed).
    Returns a bool per pair."""
    FA, FB = f[ia], f[ib]; TA, TB = v[FA], v[FB]; nA, nB = fn[ia], fn[ib]
    eps = 1e-13                                                          # m: ~1e4 x the float64 rounding at 0.3 m
    dB = np.einsum("pkj,pj->pk", TB - TA[:, :1], nA)                     # B's vertices against A's plane
    dA = np.einsum("pkj,pj->pk", TA - TB[:, :1], nB)
    shA = (FA[:, :, None] == FB[:, None, :])                             # shared-vertex matrix (p, i_A, j_B)
    sharedA = shA.any(2); sharedB = shA.any(1); one = sharedA.any(1)
    dB = np.where(sharedB, 0.0, dB); dA = np.where(sharedA, 0.0, dA)     # a shared vertex lies ON both planes
    cop = (np.abs(dB) <= eps).all(1)
    sep = ((dB >= -eps).all(1) | (dB <= eps).all(1)) | ((dA >= -eps).all(1) | (dA <= eps).all(1))
    hit = np.zeros(len(ia), bool)
    m = ~cop & ~sep
    if m.any():
        idx = np.flatnonzero(m); h = np.zeros(len(idx), bool)
        tA, tB, sA, sB = TA[idx], TB[idx], sharedA[idx], sharedB[idx]
        for i in range(3):                                               # A's edges against B, B's edges against A
            j = (i + 1) % 3
            useA = ~(sA[:, i] | sA[:, j])                                # with one shared vertex only the opposite edge
            useA = useA | ~one[idx]                                      # is tested (the others meet B at that vertex)
            h |= useA & _seg_tri(tA[:, i], tA[:, j], tB[:, 0], tB[:, 1], tB[:, 2])
            useB = ~(sB[:, i] | sB[:, j]) | ~one[idx]
            h |= useB & _seg_tri(tB[:, i], tB[:, j], tA[:, 0], tA[:, 1], tA[:, 2])
        hit[idx] = h
    if cop.any():
        idx = np.flatnonzero(cop); hit[idx] = _coplanar_overlap(TA[idx], TB[idx], nA[idx])
    return hit


def self_intersections(v, f, cell=None, pair_chunk=1_500_000, quiet=True):
    """every pair of NON-adjacent faces (sharing no edge) whose triangles meet. Uniform grid: each face goes into every
    cell its box touches; a pair is tested only in the cell holding the low corner of the two boxes' overlap, so each
    pair is tested once without a global unique. Returns (pairs (k,2) int, info dict)."""
    t0 = time.time()
    f = np.ascontiguousarray(f); F = len(f)
    T = v[f]; blo = T.min(1); bhi = T.max(1)
    fn = _cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ln = np.linalg.norm(fn, axis=1); degenerate = int((ln < 1e-18).sum())          # area < 5e-7 mm2
    fn = fn / np.maximum(ln, 1e-30)[:, None]
    del T
    ext = (bhi - blo).max(1)
    if cell is None:
        cell = float(max(1.5 * np.median(ext), 1e-6))
    org = blo.min(0) - 1e-9
    g0 = np.floor((blo - org) / cell).astype(np.int64); g1 = np.floor((bhi - org) / cell).astype(np.int64)
    dims = g1.max(0) + 1
    span = g1 - g0 + 1; ncell = span.prod(1)
    g0 = g0.astype(np.int32); span = span.astype(np.int32); ncell = ncell.astype(np.int32)
    tri = np.repeat(np.arange(F, dtype=np.int32), ncell)
    k = (np.arange(len(tri), dtype=np.int64) - np.repeat(np.cumsum(ncell, dtype=np.int64) - ncell, ncell)).astype(np.int32)
    sx, sy = span[tri, 0], span[tri, 1]
    key = (g0[tri, 0] + k % sx).astype(np.int64) * dims[1]
    key += g0[tri, 1] + (k // sx) % sy; key *= dims[2]; key += g0[tri, 2] + k // (sx * sy)
    del k, sx, sy
    o = np.argsort(key, kind="stable"); key = key[o]; tri = tri[o]; del o
    first = np.r_[True, key[1:] != key[:-1]]; start = np.flatnonzero(first); cnt = np.diff(np.r_[start, len(key)])
    npairs = (np.repeat((start + cnt).astype(np.int64), cnt) - np.arange(len(key)) - 1).astype(np.int32)   # partners after each entry in its cell
    del first, start, cnt
    cum = np.cumsum(npairs, dtype=np.int64); total = int(cum[-1]) if len(cum) else 0
    if not quiet:
        print(f"    selfint: {F} faces, cell {cell * 1000:.3f} mm, {len(key)} grid entries, {total / 1e6:.1f} M candidate pairs ({_ms(t0)})", flush=True)
    blo32 = (blo - 1e-9).astype(np.float32); bhi32 = (bhi + 1e-9).astype(np.float32)    # conservative boxes
    found = []; tested = 0; p0 = 0; n = len(key)
    while p0 < n:
        p1 = int(np.searchsorted(cum, (cum[p0 - 1] if p0 else 0) + pair_chunk, side="right"))
        p1 = min(max(p1, p0 + 1), n)
        cntp = npairs[p0:p1]; pa = np.repeat(np.arange(p0, p1), cntp)
        if len(pa):
            off = np.arange(len(pa)) - np.repeat(np.cumsum(cntp) - cntp, cntp); pb = pa + 1 + off
            a, b = tri[pa], tri[pb]
            ok = np.all(blo32[a] <= bhi32[b], 1) & np.all(blo32[b] <= bhi32[a], 1)
            a, b, pk = a[ok], b[ok], key[pa[ok]]
            # test the pair only in the cell holding the low corner of the boxes' overlap (once per pair)
            cc = np.floor((np.maximum(blo[a], blo[b]) - org) / cell).astype(np.int64)
            own = ((cc[:, 0] * dims[1] + cc[:, 1]) * dims[2] + cc[:, 2]) == pk
            a, b = a[own], b[own]
            sh = (f[a][:, :, None] == f[b][:, None, :]).sum((1, 2))
            a, b = a[sh <= 1], b[sh <= 1]                                # edge-neighbours share an edge: never tested
            tested += len(a)
            if len(a):
                hit = _tri_tri(v, f, a, b, fn)
                if hit.any():
                    found.append(np.c_[a[hit], b[hit]])
        p0 = p1
    pairs = np.vstack(found) if found else np.zeros((0, 2), np.int64)
    pairs = np.unique(np.sort(pairs, 1), axis=0)
    info = dict(faces=F, cell_mm=cell * 1000, candidate_pairs=total, exact_tests=tested, degenerate_faces=degenerate, seconds=time.time() - t0)
    if not quiet:
        print(f"    selfint: {tested / 1e6:.1f} M exact tests, {len(pairs)} intersecting pairs ({_ms(t0)})", flush=True)
    return pairs, info


def _sites(P, h=0.002):
    """group points into sites: connected 2 mm grid cells (26-neighbour). Returns list of (centre_mm, count)."""
    if len(P) == 0:
        return []
    g = np.floor(P / h).astype(np.int64); u, inv = np.unique(g, axis=0, return_inverse=True); inv = inv.ravel()
    lut = {tuple(c): i for i, c in enumerate(u)}; rows, cols = [], []
    for i, c in enumerate(u):
        for d in np.ndindex(3, 3, 3):
            j = lut.get((c[0] + d[0] - 1, c[1] + d[1] - 1, c[2] + d[2] - 1))
            if j is not None:
                rows.append(i); cols.append(j)
    _, lab = connected_components(coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(u), len(u))), directed=False)
    pl = lab[inv]; out = []
    for s in np.unique(pl):
        m = pl == s; out.append((np.round(P[m].mean(0) * 1000, 1).tolist(), int(m.sum())))
    return sorted(out, key=lambda r: -r[1])


def skin_integrity(v, f, check_self_intersection=True, cell=None, quiet=True):
    """C2. PASS = closed (0 open edges), manifold (every edge in exactly 2 faces, every vertex one fan), consistently
    oriented, ONE shell, no repeated-index face and NO self-intersecting pair of non-adjacent faces. Only
    face-referenced vertices are considered (Tripo-style arrays keep unreferenced ones)."""
    t0 = time.time(); f = np.asarray(f, np.int64)
    used = np.unique(f); remap = np.full(len(v), -1, np.int64); remap[used] = np.arange(len(used))
    f = remap[f].astype(np.int32); v = np.asarray(v, np.float64)[used]
    top = topology(f, len(v))
    if not quiet:
        print(f"    topology ({_ms(t0)}): open {top['open_edges']}, non-manifold edges {top['nonmanifold_edges']}, pinched vertices "
              f"{top['pinched_vertices']}, flips {top['orientation_flips']}, shells {top['shells']} {top['shell_faces_sizes']}", flush=True)
    T = v[f]; vol = float(np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])).sum() / 6.0); del T
    res = dict(top, faces=len(f), vertices=len(v), signed_volume_cm3=vol * 1e6)
    for k in ("ex_open", "ex_nonman", "ex_pinched"):
        res[k] = (v[res[k]] * 1000).round(2).tolist()[:5]                # example positions, mm
    ok = (top["open_edges"] == 0 and top["nonmanifold_edges"] == 0 and top["pinched_vertices"] == 0 and top["orientation_flips"] == 0
          and top["shells"] == 1 and top["repeated_index_faces"] == 0 and vol > 0)
    if check_self_intersection:
        pairs, info = self_intersections(v, f, cell=cell, quiet=quiet)
        res.update(selfint_pairs=int(len(pairs)), selfint_info=info,
                   selfint_sites=_sites(v[f[pairs.ravel()]].mean(1)) if len(pairs) else [])
        ok &= len(pairs) == 0
    res["pass"] = bool(ok); res["seconds"] = time.time() - t0
    return res


# =====================================================================  C3: skin vs envelope
def skin_vs_envelope(skin_v, skin_f, env_v, env_f, depth_fn, region_fn=None, region_names=None, tol=TOL_C3, watch=WATCH_C3,
                     max_area_mm2=MAX_AREA_C3, per_mm2=8.0, env_md=None, seed=0, samples=None):
    """C3. Area samples on the skin -> exact SIGNED distance to the envelope (twosided.MeshDist; + = outside it).
    inset = -signed distance (how far INSIDE the envelope the skin lies); err = inset - depth_fn(points).
    depth_fn(P (n,3) m) -> wanted depth (m) per point (0 on furless areas: they sit ON the envelope).
    region_fn(P) -> int label per point (index into region_names); None = one region.
    A region FAILS when its area with |err| > tol exceeds max_area_mm2. Patches with |err| > watch are listed."""
    P = area_samples(skin_v, skin_f, per_mm2, seed) if samples is None else samples
    md = env_md if env_md is not None else MeshDist(env_v, env_f)
    _, sd = md(P)
    err = -sd - depth_fn(P)
    lab = np.zeros(len(P), np.int64) if region_fn is None else np.asarray(region_fn(P)).astype(np.int64)
    over, wat = np.abs(err) > tol, np.abs(err) > watch
    rows = {}
    for r in np.unique(lab):
        m = lab == r; nm = region_names[r] if region_names is not None else str(int(r)); e = err[m] * 1000
        a_over = float(over[m].sum() / per_mm2)
        rows[nm] = dict(area_mm2=float(m.sum() / per_mm2), area_over_tol_mm2=a_over, frac_over_tol=float(over[m].mean()),
                        area_over_watch_mm2=float(wat[m].sum() / per_mm2), median_err_mm=float(np.median(e)),
                        p1_mm=float(np.percentile(e, 1)), p99_mm=float(np.percentile(e, 99)), max_abs_mm=float(np.abs(e).max()),
                        passed=bool(a_over <= max_area_mm2))
    sites = []
    if wat.any():
        Q = P[wat]; E = err[wat]
        for s_cen, cnt in _sites(Q):                                    # every patch, largest first
            near = np.linalg.norm(Q - np.array(s_cen) / 1000, axis=1) < 0.004
            pk = E[near][np.argmax(np.abs(E[near]))] if near.any() else 0.0
            sites.append(dict(centre_mm=s_cen, area_mm2=cnt / per_mm2, peak_err_mm=float(pk * 1000)))
    return dict(passed=bool(all(r["passed"] for r in rows.values())), tol_mm=tol * 1000, watch_mm=watch * 1000,
                max_area_mm2=max_area_mm2, per_mm2=per_mm2, regions=rows, watch_sites=sites), (P, err, lab)


# =====================================================================  C8: fur tips vs envelope
def fur_tips_vs_envelope(tips, env_v, env_f, depth_spread_fn, region_fn=None, region_names=None, max_frac=MAX_TIP_FRAC, env_md=None):
    """C8. Signed distance of each strand TIP to the envelope (+ = stands out). depth_spread_fn(P) -> the region's
    coat-depth spread (m, > 0) per tip. A region FAILS when more than max_frac of its tips stand out by more than the
    spread, or more than max_frac fall short by more than it."""
    md = env_md if env_md is not None else MeshDist(env_v, env_f)
    _, sd = md(tips); s = np.asarray(depth_spread_fn(tips), float) * np.ones(len(tips))
    lab = np.zeros(len(tips), np.int64) if region_fn is None else np.asarray(region_fn(tips)).astype(np.int64)
    rows = {}
    for r in np.unique(lab):
        m = lab == r; nm = region_names[r] if region_names is not None else str(int(r))
        fo, fs = float((sd[m] > s[m]).mean()), float((sd[m] < -s[m]).mean())
        rows[nm] = dict(n=int(m.sum()), median_mm=float(np.median(sd[m]) * 1000), p5_mm=float(np.percentile(sd[m], 5) * 1000),
                        p95_mm=float(np.percentile(sd[m], 95) * 1000), spread_mm=float(np.median(s[m]) * 1000),
                        frac_out=fo, frac_short=fs, passed=bool(fo <= max_frac and fs <= max_frac))
    return dict(passed=bool(all(r["passed"] for r in rows.values())), max_frac=max_frac, regions=rows), sd
