"""SKIN MICRO-RELIEF FROM CITED NUMBERS (2026-10-19), a texture for the target-driven loop (core.py).

Why: skin texture used to be guessed noise. This module builds the height field from the numbers in
engine/packs/human/references/skin_microrelief_breast.md (plateau area, furrow depth/width, two line families,
follicle density) and measures the result with profilometer-style descriptors (Ra, Rz, Rt, plateau density,
furrow depth, anisotropy), so the loop can fit the texture's parameters to cited targets instead of by eye.

The model (a periodic square tile, x = columns = "around the nipple", y = rows, heights in micrometres, plateau top = 0):
  1. seeds on a jittered sheared-hexagonal lattice, periodic on the tile; its size is picked so the MEAN PLATEAU AREA of
     the finished network (after thinning merges triangles) is p["plateau_mm2"]; jitter = sd / spacing;
  2. primary furrows = Delaunay edges of the seeds (young skin, triangular plateaus): V groove, depth d1, full width
     width_um; edges kept by orientation (family 1 = 0 deg = x axis, family 2 = family2_deg) with strength "anisotropy";
  3. secondary furrows = shallower V grooves (d2) on a second Delaunay network at half the spacing, thinned half as hard;
  4. follicle openings = round pits (parabolic bowl) at a share of the primary junctions, density follicles_per_cm2;
  5. grooves and pits are unioned (deepest wins); the V is area-averaged per pixel so Ra does not depend on the grid;
  6. optional extra keys (defaults in START_PARAMS): family_sigma_deg, family2_weight, sec_anisotropy.
API: generate, stats, relief_stats (descriptor), FieldParams (handle), save_tile, render_grooves, lattice_info.
"""
import json
import math
import struct
import zlib
from functools import lru_cache

import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import Delaunay, cKDTree

# Young adult, light end (reference table in skin_microrelief_breast.md, section 0). Rows without a cited number are
# marked: jitter (0.2-0.3 cited), anisotropy/family weights/sigma (engineering defaults), follicle depth/radius
# (assumption: optical Ra sees only the pore mouth, the 100-300 um histology depth is not part of the surface profile).
START_PARAMS = {
    "plateau_mm2": 0.17,        # R3 via R4: 5.8 per mm2
    "jitter": 0.25,             # sigma / spacing, 0.2-0.3
    "d1_um": 30.0,              # R1, R10, R11
    "width_um": 50.0,           # assumption (40-60)
    "family2_deg": 65.0,        # 60-70 deg to family 1
    "anisotropy": 0.5,          # 0 = all directions equal, 1 = only the two families
    "d2_um": 10.0,              # R10
    "follicles_per_cm2": 22.0,  # R15, 17-28
    "follicle_depth_um": 40.0,  # assumption
    "follicle_radius_um": 25.0,  # assumption (mouth diameter 30-80 um)
    "family_sigma_deg": 18.0,   # angular width of a family (edges of a jittered network scatter about +-15 deg)
    "family2_weight": 0.8,      # family 2 is the weaker one (R1: principal axis plus second axis)
    "sec_anisotropy": 0.5,      # secondary furrows follow the families half as strongly
}


def _full(p):
    q = dict(START_PARAMS)
    q.update({k: float(v) for k, v in (p or {}).items() if k in START_PARAMS})
    return q


# --------------------------------------------------------------------------------------- network (periodic Delaunay)

def _keep_prob(theta, aniso, phi, sigma, w2):
    """probability that an edge of orientation theta (deg, [0,180)) is kept as a furrow"""
    theta = np.asarray(theta, dtype=float)
    d1 = np.minimum(theta, 180.0 - theta)
    d2 = np.abs(theta - phi)
    d2 = np.minimum(d2, 180.0 - d2)
    w = np.maximum(np.exp(-0.5 * (d1 / sigma) ** 2), w2 * np.exp(-0.5 * (d2 / sigma) ** 2))
    return (1.0 - aniso) + aniso * w


def _build(L, nx, ny, k, jitter, seed, stream, prob_fn, want_faces):
    """Delaunay network of a periodic jittered lattice: nx seeds per row, ny rows, each row shifted k*s/ny against the
    last (k=ny/2 would be the hexagonal lattice with an exact half shift; tan(phi) = nx/k). Returns kept edges and
    the number of plateau regions left after the dropped edges have merged their two triangles (dual components)."""
    N = nx * ny
    k = int(k) % ny
    s, hh = L / nx, L / ny
    jj, ii = np.meshgrid(np.arange(ny), np.arange(nx), indexing="ij")
    pts = np.stack([(ii * s + jj * (k * s / ny)).ravel(), (jj * hh).ravel()], 1)
    rng = np.random.default_rng([int(seed), int(stream), nx, ny, k])
    unit = math.sqrt(s * hh)
    pts = pts + np.clip(rng.standard_normal((N, 2)), -2.5, 2.5) * (jitter * unit) \
        + rng.standard_normal((N, 2)) * (1e-4 * unit)          # tiny noise breaks Delaunay ties of the exact lattice
    pts = np.mod(pts, L)
    shifts = np.array([(ox - 1, oy - 1) for oy in range(3) for ox in range(3)], float) * L   # cell 4 = the tile
    ext = (pts[None] + shifts[:, None, :]).reshape(-1, 2)
    tri = Delaunay(ext)
    S = tri.simplices
    cent = ext[S].mean(1)
    cidx = np.nonzero(np.all((cent >= 0) & (cent < L), axis=1))[0]   # one image of each physical triangle
    T = len(cidx)
    St = S[cidx]
    va, vb = St[:, [1, 2, 0]], St[:, [2, 0, 1]]                      # edge e = opposite vertex e (as tri.neighbors)
    ia, ib = va % N, vb % N
    ca, cb = va // N, vb // N
    swap = ((ia * 3 + ca % 3) * 3 + ca // 3) > ((ib * 3 + cb % 3) * 3 + cb // 3)
    i1, i2 = np.where(swap, ib, ia), np.where(swap, ia, ib)
    dx = np.where(swap, ca % 3 - cb % 3, cb % 3 - ca % 3)
    dy = np.where(swap, ca // 3 - cb // 3, cb // 3 - ca // 3)
    keys = (((i1.astype(np.int64) * N + i2) * 5 + (dx + 2)) * 5 + (dy + 2)).ravel()   # same for every periodic image
    _, first, inv = np.unique(keys, return_index=True, return_inverse=True)
    E = len(first)
    ga, gb = va.ravel()[first], vb.ravel()[first]
    pa, pb = ext[ga], ext[gb]
    vec = pb - pa
    theta = np.degrees(np.arctan2(vec[:, 1], vec[:, 0])) % 180.0
    u = np.random.default_rng([int(seed), int(stream) + 101, nx, ny, k]).random(E)
    keep = u < prob_fn(theta)
    net = {"nx": nx, "ny": ny, "k": k, "N": N, "T": T, "E": E, "pts": pts, "keep": keep,
           "segs": np.concatenate([pa[keep], pb[keep]], 1),
           "deg": np.bincount(np.r_[(ga % N)[keep], (gb % N)[keep]], minlength=N), "F": None}
    if want_faces:
        nb = tri.neighbors[cidx]
        valid = nb >= 0
        cn = np.mod(cent[np.where(valid, nb, 0)], L).reshape(-1, 2)
        cn = np.minimum(cn, L * (1.0 - 1e-12))
        dist, nid = cKDTree(cent[cidx], boxsize=L).query(cn)
        nid = nid.reshape(T, 3)
        if T == 2 * N and dist.max() < 1e-6 * L:
            rr, cc = np.nonzero(~keep[inv.reshape(T, 3)] & valid)
            g = coo_matrix((np.ones(len(rr)), (rr, nid[rr, cc])), shape=(T, T))
            net["F"] = int(connected_components(g, directed=False)[0])
        else:   # should not happen; fall back to Euler's count (every kept edge beyond V closes a plateau)
            net["F"] = max(1, int(keep.sum()) - N)
    return net


@lru_cache(maxsize=24)
def _primary_network(L, A, phi, jitter, aniso, sigma, w2, seed):
    """pick (nx, ny, k) so that the finished network has about L^2 / A plateau regions with edge directions 0 and phi"""
    phi = float(np.clip(phi, 20.0, 160.0))
    prob_fn = lambda th: _keep_prob(th, aniso, phi, sigma, w2)
    sinp = math.sin(math.radians(phi))
    N0 = L * L / (2.0 * A)                       # seeds if every Delaunay triangle is a plateau
    nx_lo = max(3, int(math.floor(math.sqrt(N0 * sinp) * 0.85)))
    nx_hi = max(nx_lo + 2, int(math.ceil(math.sqrt(6.0 * N0 * sinp) * 1.15)))   # strong thinning needs many seeds
    p0 = float(prob_fn(np.zeros(1))[0])
    cands = []
    for nx in range(nx_lo, nx_hi + 1):
        s = L / nx
        ny_ref = nx / sinp
        for ny in range(max(3, int(ny_ref * 0.75)), int(ny_ref * 1.35) + 2):
            if nx * ny > 20000:
                continue
            ks = np.arange(ny)
            hh = L / ny
            c = ks * s / ny
            cr = c - s * np.round(c / s)
            tx = np.where(cr >= 0, cr - s, cr + s)
            ang_b, ang_t = np.degrees(np.arctan2(hh, cr)), np.degrees(np.arctan2(hh, tx))
            lens = np.stack([np.full(ny, s), np.hypot(cr, hh), np.hypot(tx, hh)])
            shape = np.log(lens.max(0) / lens.min(0))
            err = np.minimum(np.abs(ang_b - phi), np.abs(ang_t - phi))
            f_est = np.maximum(p0 + prob_fn(ang_b) + prob_fn(ang_t) - 1.0, 0.4) * nx * ny
            for kk in np.argsort(0.3 * shape + 0.3 * err / 10.0)[:2]:
                cands.append((nx, ny, int(kk), float(f_est[kk]), float(shape[kk]), float(err[kk])))

    def cost(c, f, r=1.0):
        return abs(math.log(f * r * A / (L * L))) + 0.3 * c[4] + 0.3 * c[5] / 10.0

    built, ratios, best = set(), [], None

    def run(c):
        nonlocal best
        net = _build(L, c[0], c[1], c[2], jitter, seed, 1, prob_fn, True)
        net["cost"] = cost(c, net["F"])
        net["lattice_err_deg"], net["lattice_shape"] = c[5], c[4]
        built.add(c[:3])
        ratios.append(math.log(net["F"] / c[3]))
        if best is None or net["cost"] < best["cost"]:
            best = net

    # the closed-form count ignores dangling edges and is biased: build a few lattices exactly, learn the bias
    # (median of exact / closed-form), re-rank all lattices with it and build the best unbuilt ones; three rounds
    r = 1.0
    for n_build in (4, 5, 4):
        todo = [c for c in sorted(cands, key=lambda c: cost(c, c[3], r)) if c[:3] not in built][:n_build]
        for c in todo:
            run(c)
        r = math.exp(float(np.median(ratios)))
    return best


@lru_cache(maxsize=24)
def _secondary_network(L, nx, ny, k, jitter, aniso, phi, sigma, w2, seed):
    phi = float(np.clip(phi, 20.0, 160.0))
    return _build(L, 2 * nx, 2 * ny, 2 * k, jitter, seed, 2, lambda th: _keep_prob(th, aniso, phi, sigma, w2), False)


def lattice_info(p, size_mm, seed=0):
    """realised lattice of generate(p, size_mm, ., seed): sizes, plateau count and area after thinning"""
    q = _full(p)
    L = float(size_mm)
    n = _primary_network(L, q["plateau_mm2"], q["family2_deg"], q["jitter"], q["anisotropy"], q["family_sigma_deg"],
                         q["family2_weight"], int(seed))
    return {"nx": n["nx"], "ny": n["ny"], "k": n["k"], "seeds": n["N"], "edges": n["E"], "edges_kept": int(n["keep"].sum()),
            "plateaus": n["F"], "plateau_mm2_realised": L * L / n["F"], "plateau_density_expected": n["F"] / (L * L),
            "lattice_angle_err_deg": n["lattice_err_deg"], "lattice_shape_ln": n["lattice_shape"]}


# ------------------------------------------------------------------------------------------------------ rasterisation

def _G(x, hw):
    x = np.clip(x, -hw, hw)
    return np.where(x < 0, (x + hw) ** 2, 2.0 * hw * hw - (hw - x) ** 2) / (2.0 * hw)


def _vprof(d, hw):
    """unit V groove (half width hw, pixels) averaged over a one-pixel box at distance d from its centre line"""
    return _G(d + 0.5, hw) - _G(d - 0.5, hw)


def _stamp_seg(C, x0, y0, x1, y1, hw, depth, m):
    W = C.shape[0]
    xa, xb = max(int(math.floor(min(x0, x1) - m)), 0), min(int(math.ceil(max(x0, x1) + m)), W)
    ya, yb = max(int(math.floor(min(y0, y1) - m)), 0), min(int(math.ceil(max(y0, y1) + m)), W)
    if xb <= xa or yb <= ya:
        return
    X = np.arange(xa, xb, dtype=np.float32) + np.float32(0.5)
    Y = (np.arange(ya, yb, dtype=np.float32) + np.float32(0.5))[:, None]
    dx, dy = x1 - x0, y1 - y0
    l2 = dx * dx + dy * dy
    t = np.clip(((X - x0) * dx + (Y - y0) * dy) / max(l2, 1e-12), 0.0, 1.0)
    ex, ey = X - (x0 + t * dx), Y - (y0 + t * dy)
    sub = C[ya:yb, xa:xb]
    np.maximum(sub, depth * _vprof(np.sqrt(ex * ex + ey * ey), hw), out=sub)


def _stamp_pit(C, cx, cy, R, depth):
    W = C.shape[0]
    m = R + 1.0
    xa, xb = max(int(math.floor(cx - m)), 0), min(int(math.ceil(cx + m)), W)
    ya, yb = max(int(math.floor(cy - m)), 0), min(int(math.ceil(cy + m)), W)
    if xb <= xa or yb <= ya:
        return
    X = np.arange(xa, xb, dtype=np.float32) + np.float32(0.5)
    Y = (np.arange(ya, yb, dtype=np.float32) + np.float32(0.5))[:, None]
    r2 = ((X - cx) ** 2 + (Y - cy) ** 2) / (R * R)
    sub = C[ya:yb, xa:xb]
    np.maximum(sub, depth * np.maximum(0.0, 1.0 - r2), out=sub)


def _fold(C, P, px):
    """add the periodic images stored in the halo of width P back into the tile (union = maximum)"""
    A = C[P:P + px, :].copy()
    np.maximum(A[px - P:, :], C[:P, :], out=A[px - P:, :])
    np.maximum(A[:P, :], C[P + px:, :], out=A[:P, :])
    B = A[:, P:P + px].copy()
    np.maximum(B[:, px - P:], A[:, :P], out=B[:, px - P:])
    np.maximum(B[:, :P], A[:, P + px:], out=B[:, :P])
    return B


def _raster(px, groups):
    """groups: ("seg", (n,4) px coords, depth_um, half_width_px) or ("pit", (n,2) px coords, depth_um, radius_px)
    -> depth field (positive down) of a periodic tile, float32"""
    reach = max([g[3] for g in groups] + [1.0]) + 1.0
    P = int(math.ceil(reach)) + 2
    P = min(P, px)
    Wc = px + 2 * P
    C = np.zeros((Wc, Wc), np.float32)
    for kind, arr, depth, size in groups:
        arr = np.asarray(arr, float)
        if arr.size == 0 or depth <= 0:
            continue
        m = size + 1.0
        arr = arr.copy()
        if kind == "seg":                                   # wrap each segment's start into the tile (keeps the segment whole)
            w = np.floor(arr[:, 0] / px) * px, np.floor(arr[:, 1] / px) * px
            arr[:, [0, 2]] -= w[0][:, None]
            arr[:, [1, 3]] -= w[1][:, None]
            lo, hi = arr.reshape(-1, 2, 2).min(1), arr.reshape(-1, 2, 2).max(1)
            lo, hi = lo.min(0), hi.max(0)
        else:
            arr = np.mod(arr, px)
            lo = hi = None
        # shifts by whole tile periods whose image can reach the canvas (halo included)
        rng_ = [range(int(math.floor((-P - m - (hi[i] if hi is not None else px)) / px)) + 1,
                      int(math.ceil((px + P + m - (lo[i] if lo is not None else 0.0)) / px))) for i in (0, 1)]
        for kx in rng_[0]:
            for ky in rng_[1]:
                sx, sy = kx * px, ky * px
                if kind == "seg":
                    x0, y0, x1, y1 = (arr[:, 0] + sx + P), (arr[:, 1] + sy + P), (arr[:, 2] + sx + P), (arr[:, 3] + sy + P)
                    ok = (np.maximum(x0, x1) + m > 0) & (np.minimum(x0, x1) - m < Wc) &                          (np.maximum(y0, y1) + m > 0) & (np.minimum(y0, y1) - m < Wc)
                    for i in np.nonzero(ok)[0]:
                        _stamp_seg(C, float(x0[i]), float(y0[i]), float(x1[i]), float(y1[i]), float(size), float(depth), m)
                else:
                    cx, cy = arr[:, 0] + sx + P, arr[:, 1] + sy + P
                    ok = (cx + m > 0) & (cx - m < Wc) & (cy + m > 0) & (cy - m < Wc)
                    for i in np.nonzero(ok)[0]:
                        _stamp_pit(C, float(cx[i]), float(cy[i]), float(size), float(depth))
    return _fold(C, P, px)


def render_grooves(segments_mm, size_mm, px, depth_um, width_um):
    """periodic tile with V grooves along the given segments (n,4: x0,y0,x1,y1 in mm, may leave [0,size) and wrap);
    heights in um, <= 0"""
    L = float(size_mm)
    delta = L * 1000.0 / px
    seg = np.asarray(segments_mm, float).reshape(-1, 4) * (px / L)
    return -_raster(px, [("seg", seg, float(depth_um), width_um / delta / 2.0)]).astype(np.float32)


def generate(p, size_mm, px, seed=0):
    """micro-relief height field, float32 micrometres, shape (px, px), periodic in both axes, plateau tops = 0"""
    q = _full(p)
    L, px, seed = float(size_mm), int(px), int(seed)
    ppm = px / L                                   # pixels per mm
    delta = L * 1000.0 / px                        # um per pixel
    net = _primary_network(L, q["plateau_mm2"], q["family2_deg"], q["jitter"], q["anisotropy"], q["family_sigma_deg"],
                           q["family2_weight"], seed)
    hw = q["width_um"] / delta / 2.0
    groups = []
    if q["d2_um"] > 0:
        n2 = _secondary_network(L, net["nx"], net["ny"], net["k"], q["jitter"], q["anisotropy"] * q["sec_anisotropy"],
                                q["family2_deg"], q["family_sigma_deg"], q["family2_weight"], seed)
        groups.append(("seg", n2["segs"] * ppm, q["d2_um"], hw))
    if q["d1_um"] > 0:
        groups.append(("seg", net["segs"] * ppm, q["d1_um"], hw))
    n_fol = int(round(q["follicles_per_cm2"] * L * L / 100.0))
    cand = np.nonzero(net["deg"] >= 3)[0]
    if n_fol > 0 and len(cand) and q["follicle_depth_um"] > 0:
        pick = np.random.default_rng([seed, 7]).choice(cand, size=min(n_fol, len(cand)), replace=False)
        groups.append(("pit", net["pts"][pick] * ppm, q["follicle_depth_um"], max(q["follicle_radius_um"] / delta, 0.75)))
    return -_raster(px, groups).astype(np.float32)


# ---------------------------------------------------------------------------------------------------------- statistics

def _profile_stats(P):
    """P (n, m): n parallel profiles. Ra, Rq about each profile's mean; Rz = mean of 5 peak-to-valley over 5 equal
    sampling lengths; Rt = peak-to-valley of the whole profile; all averaged over the n profiles"""
    z = P - P.mean(1, keepdims=True)
    m = P.shape[1] // 5
    seg = P[:, :5 * m].reshape(P.shape[0], 5, m)
    return (float(np.abs(z).mean()), float(np.sqrt((z * z).mean(1)).mean()),
            float((seg.max(2) - seg.min(2)).mean()), float((P.max(1) - P.min(1)).mean()))


def _label_periodic(free):
    """4-connected regions of a boolean mask on a torus -> (labels, areas)"""
    lab, n = ndimage.label(free)
    if n == 0:
        return lab, np.zeros(0, int)
    pairs = np.concatenate([np.stack([lab[0, :], lab[-1, :]], 1), np.stack([lab[:, 0], lab[:, -1]], 1)])
    pairs = pairs[(pairs[:, 0] > 0) & (pairs[:, 1] > 0)]
    g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n + 1, n + 1))
    _, comp = connected_components(g, directed=False)
    lab = comp[lab]
    lab[~free] = -1
    ids = np.unique(lab[free])
    areas = np.bincount(np.searchsorted(ids, lab[free]), minlength=len(ids))
    return lab, areas


def stats(h, size_mm):
    """profilometer-style numbers of a height field h (micrometres; rows = y, columns = x, square pixels, x spans size_mm).
    Ra/Rq/Rz/Rt: profiles in both directions, averaged (ra_x_um / ra_y_um separately). primary_depth_um: median of the
    deepest 10 % of groove crossings. plateau_density_per_mm2: periodic regions left by the furrow mask (deeper than
    0.5 x primary depth), so secondary grooves deeper than half the primary ones also count as boundaries.
    anisotropy_index: 0..1 from the gradient structure tensor; dominant_deg: strongest furrow direction (0 = x axis, mod 180;
    with two similar families it can sit on either); tensor_deg: the tensor's mean direction."""
    h = np.asarray(h, dtype=np.float64)
    ny, nx = h.shape
    pitch = size_mm * 1000.0 / nx                                  # um per pixel
    px_ = h[::max(1, ny // 1024), :]                               # profiles along x
    py_ = h.T[::max(1, nx // 1024), :]                             # profiles along y
    sx, sy = _profile_stats(px_), _profile_stats(py_)
    out = {"ra_um": 0.5 * (sx[0] + sy[0]), "rq_um": 0.5 * (sx[1] + sy[1]), "rz_um": 0.5 * (sx[2] + sy[2]),
           "rt_um": 0.5 * (sx[3] + sy[3]), "ra_x_um": sx[0], "ra_y_um": sy[0]}
    # groove crossings: local depth maxima on every profile; the primary depth is the median of the deepest 10 %
    ref = float(np.percentile(h, 90))
    peaks = []
    for P in (px_, py_):
        D = ref - P
        c = D[:, 1:-1]
        pk = (c > D[:, :-2]) & (c >= D[:, 2:]) & (c > 1.0)
        peaks.append(c[pk])
    peaks = np.concatenate(peaks)
    if peaks.size >= 10:
        pd = float(np.median(peaks[peaks >= np.quantile(peaks, 0.9)]))
    else:
        pd = float(np.median(peaks)) if peaks.size else 0.0
    out["primary_depth_um"] = pd
    # plateau regions: parts of the tile that the furrow mask (deeper than 0.5 x primary depth) leaves connected
    dens = 0.0
    if pd > 1.0:
        _, areas = _label_periodic((ref - h) <= 0.5 * pd)
        if areas.size:
            areas = areas[areas >= max(4.0, 0.1 * np.median(areas))]
            dens = float(areas.size) / (ny * nx * pitch * pitch * 1e-6)
    out["plateau_density_per_mm2"] = dens
    # structure tensor of the height gradient (orientation of the furrow flanks)
    gy, gx = np.gradient(h, pitch)
    gx, gy = gx[1:-1, 1:-1], gy[1:-1, 1:-1]
    jxx, jyy, jxy = float((gx * gx).mean()), float((gy * gy).mean()), float((gx * gy).mean())
    tr = jxx + jyy
    if tr < 1e-12:
        out.update(anisotropy_index=0.0, dominant_deg=0.0, tensor_deg=0.0)
        return out
    out["anisotropy_index"] = math.sqrt((jxx - jyy) ** 2 + 4.0 * jxy ** 2) / tr
    out["tensor_deg"] = (math.degrees(0.5 * math.atan2(2.0 * jxy, jxx - jyy)) + 90.0) % 180.0
    wgt = (gx * gx + gy * gy).ravel()
    ang = (np.degrees(np.arctan2(gy, gx)).ravel() + 90.0) % 180.0            # furrow direction (perpendicular to slope)
    hist = np.bincount(np.minimum(ang.astype(int), 179), weights=wgt, minlength=180)
    hist = ndimage.gaussian_filter1d(hist, 4.0, mode="wrap")
    out["dominant_deg"] = float(np.argmax(hist) + 0.5)                            # the strongest family
    return out


# ----------------------------------------------------------------------------------------------------- loop interface

def relief_stats(state, size_mm=8.0, px=512, seed=0):
    """descriptor for core.measure: stats of generate(state["relief"]) with the prefix "relief_" """
    s = stats(generate(state["relief"], size_mm, px, seed), size_mm)
    return {"relief_" + k: v for k, v in s.items()}


DEFAULT_BOUNDS = {"plateau_mm2": (0.05, 0.45), "jitter": (0.0, 0.45), "d1_um": (8.0, 90.0), "width_um": (15.0, 130.0),
                  "family2_deg": (35.0, 145.0), "anisotropy": (0.0, 1.0), "d2_um": (0.0, 35.0),
                  "follicles_per_cm2": (0.0, 60.0), "follicle_depth_um": (5.0, 120.0), "follicle_radius_um": (8.0, 80.0),
                  "family_sigma_deg": (6.0, 40.0), "family2_weight": (0.2, 1.0), "sec_anisotropy": (0.0, 1.0)}
DEFAULT_SCALE = {"plateau_mm2": 0.1, "jitter": 0.2, "d1_um": 20.0, "width_um": 30.0, "family2_deg": 20.0, "anisotropy": 0.5,
                 "d2_um": 10.0, "follicles_per_cm2": 20.0, "follicle_depth_um": 30.0, "follicle_radius_um": 20.0,
                 "family_sigma_deg": 10.0, "family2_weight": 0.4, "sec_anisotropy": 0.5}


class FieldParams:
    """loop handle over chosen keys of state["relief"]. bounds / scale: dict key -> value, or a pair / array in key order,
    or None for the defaults above. apply() returns a copy of the state with those keys replaced."""

    def __init__(self, keys, state, bounds=None, scale=None, name="relief_params", field="relief"):
        self.keys, self.field, self.name = list(keys), field, name
        self.n = len(self.keys)
        base = _full(state.get(field, {}))
        self.x0 = np.array([float(state[field].get(k, base[k])) for k in self.keys])
        if bounds is None:
            lo = np.array([DEFAULT_BOUNDS[k][0] for k in self.keys]); hi = np.array([DEFAULT_BOUNDS[k][1] for k in self.keys])
        elif isinstance(bounds, dict):
            lo = np.array([bounds[k][0] for k in self.keys], float); hi = np.array([bounds[k][1] for k in self.keys], float)
        else:
            lo, hi = np.broadcast_to(np.asarray(bounds[0], float), (self.n,)).copy(), np.broadcast_to(np.asarray(bounds[1], float), (self.n,)).copy()
        self.bounds = (lo, hi)
        if scale is None:
            self.scale = np.array([DEFAULT_SCALE[k] for k in self.keys])
        elif isinstance(scale, dict):
            self.scale = np.array([scale[k] for k in self.keys], float)
        else:
            self.scale = np.broadcast_to(np.asarray(scale, float), (self.n,)).copy()

    def apply(self, state, params):
        new = dict(state)
        r = dict(state.get(self.field, {}))
        for k, v in zip(self.keys, np.asarray(params, float).ravel()):
            r[k] = float(v)
        new[self.field] = r
        return new


# --------------------------------------------------------------------------------------------------------------- output

def _write_png16(path, a16):
    h, w = a16.shape
    raw = np.concatenate([np.zeros((h, 1), np.uint8), np.ascontiguousarray(a16.astype(">u2")).view(np.uint8).reshape(h, 2 * w)], 1)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16, 0, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw.tobytes(), 6)) + chunk(b"IEND", b""))


def save_tile(h, path_png, path_json, size_mm, params=None, seed=None):
    """16-bit grayscale PNG (0 = deepest, 65535 = highest) + JSON that maps it back to micrometres:
    height_um = height_min_um + value / 65535 * (height_max_um - height_min_um)"""
    h = np.asarray(h, dtype=np.float64)
    lo, hi = float(h.min()), float(h.max())
    span = hi - lo if hi > lo else 1.0
    a16 = np.rint((h - lo) / span * 65535.0).astype(np.uint16)
    try:
        import imageio.v3 as iio
        iio.imwrite(path_png, a16)
    except Exception:
        _write_png16(path_png, a16)
    meta = {"size_mm": float(size_mm), "px": int(h.shape[1]), "rows": int(h.shape[0]), "um_per_px": size_mm * 1000.0 / h.shape[1],
            "height_min_um": lo, "height_max_um": hi, "tileable": True, "x_axis": "columns (around the nipple)",
            "encoding": "height_um = height_min_um + value / 65535 * (height_max_um - height_min_um); 0 = deepest",
            "params": _full(params) if params is not None else None, "seed": seed}
    with open(path_json, "w") as f:
        json.dump(meta, f, indent=1)
    return meta
