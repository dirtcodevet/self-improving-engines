"""MOUND RESIZE by computation (2026-10-21, woman2 build 13a4): a mound on a wall (a breast on its chest wall, any
bump on a surface it rests on) made smaller or larger by its height above the wall, along the wall's own axis.

THE MECHANISM. A mound's size is its height above the surface it rests on, over its footprint (the cup reference's
R6: volume = skin minus chest wall over the outline). Given the wall as a height grid in the mound's own frame (rows
e1, e2, a; origin o; a = the wall's mean outward normal; `wall[row = v, col = u]`, the engine's chest_wall.Side
convention), each vertex's height above the wall is h = q_a - wall(q_u, q_v). The mound is resized by moving every
vertex ALONG a by

        delta = (c - 1) * Hs * m * ramp(Hs)

  Hs    the SMOOTH part of h: h averaged over the surface within `smooth_mm` (weights (1 - d^2/r^2)^2, neighbours along
        the edges). What is finer than that - the skin's fine relief, small marks - is h - Hs and is not scaled: it
        rides on the moved surface unchanged, so a resized mound keeps its own detail.
  c     the size factor (volume over a fixed footprint scales by c exactly, for the column part of the mound).
  m     the footprint weight: 1 on the footprint grid mask, falling smoothly (smoothstep, blurred over 2 mm: a distance
        off a pixel mask steps by a pixel) to exactly 0 at `band_mm` outside it, so nothing outside the footprint and its
        band moves (the A28 item 9 diff reads exactly 0 there).
        band_mode="fill" (woman2 13a4): instead of that taper, the move in the band is the smoothest field (bi-Laplacian,
        scalar_fill) joining the mound's own move at the footprint's edge to nothing at band_mm. Where the skin round the
        mound stands off the wall (a body's side beside a breast, Hs 3-8 mm there) a fixed taper bends the move by
        (1 - c) Hs over its width (~2 mm over 15 mm: ~50 /m added along two lines); the fill spreads it with the least
        bending. It overshoots a little past an edge where the mound meets its wall steeply (outward 0.3 mm on 13a4's
        upper chest, 0.16 mm on the planted mound).
  ramp  smoothstep(Hs / ramp_mm): no move where the skin lies on or below the wall (a fold bottom, the chest round the
        mound): a fold tethered to the wall stays where it is. ramp_mm = 0: a plain cut at Hs = 0 (the move is then
        (c - 1) max(Hs, 0), continuous; where the mound meets its wall at an angle the move's own slope only scales that
        angle by c). A ramp over a few mm bends the move where the skin approaches the wall - on a mound whose border
        meets the wall at an angle (an upper breast pole) it adds a crease of its own there (woman2 13a4: ramp 4 mm made
        relief() at 10 mm along the upper outline 1.5-2x the pole's).
A CAP (a feature on the mound that must keep its own size and detail - a nipple-areola; `cap` mask): its heights are
left out of the smooth part, and the mound under it is the smoothest surface joining the mound round it (scalar_fill);
the cap then rides on the resized mound with all of its own relief (its height above that mound) unchanged - it follows
the mound's gentle flattening under it (its outline and tilt) and is never squashed. Preferred to `rigid` (below): a cap
held rigid while the mound round it flattens stands proud of it and its ring shows as an edge in raking light (woman2
13a4, cases/woman2/build13/work13a4/z_breast_*_side_clay.png: 13a3 left, the rigid cap right).
A RIGID set (a cap that must keep its own size and detail - a nipple-areola) moves as one body by the mean delta of its
boundary ring; round it (within `rigid_blend_mm`, Euclidean distance to the set) the delta is the smoothest field
joining that value to the mound's own (a bi-Laplacian fill of the scalar, cotangent weights: scalar_fill), so the cap is
translated exactly, never squashed, and the ring takes the cap's difference with the least added curvature.

WHY IT CANNOT FOLD. Every move is along the one axis a and, within one column (u, v), the new height above the wall is
W + Hs * (1 + (c - 1) m ramp) + detail: monotone in the old height for 0 < c, smooth m. So the order of the layers a
column crosses (a lower pole overhanging its fold: front skin, underside, fold) is kept, and no face turns over unless
the delta field itself is rough at the scale of a face (smooth_mm >> an edge). The report counts faces whose normal
turned more than 90 deg (must be 0).

    V_new, rep, aux = resize(V, F, frame, footprint, c, sel=None, cap=None, rigid=None, smooth_mm=6.0, band_mm=15.0,
                             ramp_mm=4.0, rigid_blend_mm=10.0, band_mode="taper", cap_fill_first=False)
      cap_fill_first  (13a5) fill the cap's place before the smooth mean (default off: 13a4's resize, which replays)
      frame     dict(o, R, step, n, wall) - wall: (n, n) heights (m), NaN off the wall
      footprint (n, n) bool grid mask
      c         scalar, or (n_vertices,) per-vertex factor (e.g. a factor that differs by region; must be smooth)
      sel       vertex mask the tool may move (default: every vertex whose column is on the grid); the arm of a body, the
                other mound's half, are left out by the caller
    rim_concavity(V, F, frame, thetas_deg, r_range_mm, smooth_mm=4.0)
      the junction descriptor: on each ray from the frame origin (angle theta from e1, in the u-v plane), the skin's
      front height profile in the frame (rasterised on the grid by the caller: a height map `skin`), its curvature along
      the ray (1/m, positive = concave), and the peak concavity within r_range: a crease where a mound meets its wall
      reads as a sharp peak (radius under ~25 mm, > 40 /m: the chest-wall instrument's own fold threshold).
Proof: engine/tools/test_mound_resize.py (planted mound with a cap and fine relief on a curved wall; json beside it).

A SIMILAR RESIZE (2026-10-21, woman2 build 13a5): `resize` keeps the footprint, so a smaller mound comes out flatter for
its size (woman2 13a4: apex over the raised area's radius 0.66 -> 0.50 at 0.75 of the volume). `resize_similar` keeps
the mound's proportions instead: the mound of size factor s is the similarity of the old one about a centre point on the
wall, h'(c + s (p - c)) = s h(p) in the wall's own coordinates (u, v along the wall, h above it), so apex over radius,
the upper share and every profile scaled by its own height and length stay as they were, and the volume over the
footprint scales by s^3. Two steps, each a real mechanism:
  1 the height: `resize` with factor k (k = s for a plain similarity; k = s / c_before when undoing an earlier
    footprint-keeping resize by c_before), its cap and band fill as above, the cap's place filled before the smooth mean
    (cap_fill_first: a mean with the cap left out is one-sided next to it and reads low by the dome's slope);
  2 the footprint: every vertex of a column slides along the wall by the lateral field w(u, v) and keeps its height above
    the wall (its a changes by W(p + w) - W(p)), so all layers of a column (front skin, the underside of an overhanging
    pole, its fold) move together and keep their order. w is the soft fit (similar_field, fit_len_mm) to the similarity's
    own move (s - 1)(p - c), asked for where the mound stands over core_h_mm, easing out within cap_ring_mm of the cap
    and within relax_mm of held cells; held: the cap (one constant: it keeps its size), 0 past the band, on the caller's
    held cells and off the wall. The similarity's move is affine (no bending), so it is kept exactly wherever nothing
    fixed is near; the skin round the mound takes up the change in footprint with the least bending, and the fold under
    the mound moves with it. Where held cells meet the mound (a midline it reaches) the mound stays where it meets them,
    lowered by k. The map p -> p + w(p) must stay one-to-one: its least Jacobian determinant is reported (must be > 0);
  3 the cap and the ring round it (within cap_ring_mm, easing out over seat_fade_mm), where the slide is not the
    similarity's: each vertex seen from the front takes the similar mound's smooth height where it now stands (a local
    quadric of the smooth height round its own first place, evaluated at its pre-image) plus its own relief (the cap's
    shape, the fine relief), so the cap keeps its size and rides on the similar mound; where the slide is the
    similarity's that change is 0.
  Measured on the planted dome (test_mound_similar.json): the similar form within 0.056 mm p99 where the move is asked
  for, 0.09 mm where it is filled, 0.013 mm on the cap; a strip held across the dome's foot: 0.0 mm, the far side within
  0.09 mm p99.
    V_new, rep, aux = resize_similar(V, F, frame, footprint, s, k, centre_uv, sel=None, cap=None, held_grid=None,
                                     smooth_mm=6.0, band_mm=40.0, core_h_mm=1.0, cap_ring_mm=20.0, fit_len_mm=4.0,
                                     relax_mm=30.0, seat_fade_mm=20.0, top_tol_mm=2.0, depth_mm=(-60.0, -30.0))
      centre_uv  the similarity's centre in the frame (m): a cap's own centre keeps the cap where it is
      held_grid  (n, n) bool: cells whose skin must not slide (a midline strip shared with the other side)
      depth_mm   skin deeper than the first value below the wall (the far side of the body in the same columns) never
                 slides; between the two values the slide eases in
      aux        "w" the field (n, n, 2), "footprint" the new footprint (the old one carried by the map), "core", "held"
Proof: engine/tools/test_mound_similar.py (a planted mound with a cap and fine relief on a curved wall made 0.9 x as
large: its form against the analytic similarity; an overhanging lip shrunk with its fold; json beside it).
"""
import numpy as np
from scipy import ndimage, sparse
from scipy.spatial import cKDTree


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def _adjacency(F, n):
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    A = sparse.coo_matrix((np.ones(len(e) * 2), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    return A


def _ring_rows(A, ids, rings):
    S = sparse.csr_matrix((np.ones(len(ids)), (np.arange(len(ids)), ids)), shape=(len(ids), A.shape[0]))
    X = S.copy()
    for _ in range(rings):
        X = X + X @ A
        X.data[:] = 1.0
    return X.tocsr()


def surface_mean(V, F, ids, h, radius, A=None, chunk=4000):
    """weighted mean of h (NaN ignored) over each id's surface neighbourhood within radius, weights (1 - d^2/r^2)^2,
    neighbours along the edges (a second sheet nearby never counts)"""
    n = len(V)
    if A is None:
        A = _adjacency(F, n)
    Fl = F[np.isin(F, ids).any(1)]
    el = np.linalg.norm(V[Fl[:, 0]] - V[Fl[:, 1]], axis=1)
    # rings: enough edge steps to reach the whole ball along the graph (a path along the edges runs up to ~1.5 x the
    # straight distance on a triangulated grid); a truncated ball is lopsided and makes the mean jump between vertices
    rings = int(min(40, np.ceil(1.5 * radius / max(np.percentile(el, 5), 1e-6)) + 1))
    out = np.full(len(ids), np.nan); hv = np.nan_to_num(h); ok = np.isfinite(h).astype(float)
    for c0 in range(0, len(ids), chunk):
        c = ids[c0:c0 + chunk]
        X = _ring_rows(A, c, rings).tocoo()
        d2 = ((V[c[X.row]] - V[X.col]) ** 2).sum(1); m = d2 <= radius * radius
        r, cl, w = X.row[m], X.col[m], (1 - d2[m] / radius ** 2) ** 2 * ok[X.col[m]]
        out[c0:c0 + len(c)] = np.bincount(r, w * hv[cl], len(c)) / np.maximum(np.bincount(r, w, len(c)), 1e-30)
    return out


def heights(V, frame, ids=None):
    """height above the wall along a, and the frame coordinates (u, v, a) of each vertex (NaN off the grid)"""
    o, R, st, n, W = np.asarray(frame["o"], float), np.asarray(frame["R"], float), float(frame["step"]), int(frame["n"]), frame["wall"]
    P = V if ids is None else V[ids]
    q = (P - o) @ R.T
    x = q[:, 0] / st + (n - 1) / 2; y = q[:, 1] / st + (n - 1) / 2
    w = ndimage.map_coordinates(W, [y, x], order=1, mode="constant", cval=np.nan)
    return q[:, 2] - w, q


def footprint_weight(frame, footprint, band_mm, q, blur_mm=2.0):
    """1 on the footprint, smoothstep to 0 at band_mm outside it, read at the frame points q (bilinear); blurred over
    blur_mm (a distance read off a pixel mask steps by a pixel, and the step would print into the moves as a vertex-
    scale ripple along the outline - woman2 13a4) with the smoothstep ending 3 x blur_mm early, so the weight is still
    exactly 0 past band_mm. Also returns each point's distance outside the footprint (mm, 0 inside)."""
    st = float(frame["step"]); n = int(frame["n"])
    dist = ndimage.distance_transform_edt(~footprint) * st * 1e3
    inner = max(band_mm - 3 * blur_mm, 0.5 * band_mm)
    g = 1.0 - smoothstep(dist / max(inner, 1e-9))
    if blur_mm > 0:
        g = ndimage.gaussian_filter(g, blur_mm * 1e-3 / st)
    g = np.where(dist <= band_mm, g, 0.0)
    x = q[:, 0] / st + (n - 1) / 2; y = q[:, 1] / st + (n - 1) / 2
    w = ndimage.map_coordinates(g, [y, x], order=1, mode="constant", cval=0.0)
    dv = ndimage.map_coordinates(dist, [y, x], order=1, mode="constant", cval=1e9)
    return w, dv


def resize(V, F, frame, footprint, c, sel=None, rigid=None, smooth_mm=6.0, band_mm=15.0, ramp_mm=4.0, rigid_blend_mm=10.0, cap=None,
           band_mode="taper", cap_fill_first=False):
    V = np.asarray(V, float); F = np.asarray(F, np.int64); n = len(V)
    a = np.asarray(frame["R"], float)[2]
    h_all, q_all = heights(V, frame)
    on = np.isfinite(h_all) if sel is None else (np.asarray(sel, bool) & np.isfinite(h_all))
    m_all = np.zeros(n); dist_all = np.full(n, 1e9)
    m_all[on], dist_all[on] = footprint_weight(frame, footprint, band_mm, q_all[on])
    move = on & ((m_all > 0) if band_mode != "fill" else (dist_all <= band_mm))
    # the smooth height over the moved set and a margin of smooth_mm (so the average at its edge sees its neighbours)
    A = _adjacency(F, n)
    zone = move.copy()
    reach = int(np.ceil(smooth_mm / 1.0)) + 2
    for _ in range(reach):
        zone |= (A @ zone.astype(float)) > 0
    zone &= np.isfinite(h_all)
    zid = np.nonzero(zone)[0]
    hz = np.full(n, np.nan); hz[zid] = h_all[zid]
    if cap is not None and np.asarray(cap, bool).any():
        hz[np.asarray(cap, bool)] = np.nan                 # the cap's own heights never enter the smooth mound
        if cap_fill_first:
            # (13a5) the cap's place filled first with the smoothest surface joining the mound round it, so the smooth
            # mean next to the cap is not one-sided: excluded heights left it biased by the dome's slope x the missing
            # side's offset (woman2 13c, 1-2 mm outside the areola: 0.26 mm low p50, 0.54 p5; 0.1 mm at 3-4 mm), and every
            # later step printed that bias as a ring round the cap
            cz = np.asarray(cap, bool) & zone
            hz = scalar_fill(V, F, cz, np.where(np.isfinite(hz), hz, 0.0))
            hz[~zone] = np.nan
    Hs = np.full(n, np.nan); mid = np.nonzero(move)[0]
    Hs[mid] = surface_mean(V, F, mid, hz, smooth_mm * 1e-3, A=A)
    if cap is not None and np.asarray(cap, bool).any():
        cp = np.asarray(cap, bool) & move
        Hs = np.where(np.isfinite(Hs), Hs, 0.0)
        Hs = scalar_fill(V, F, cp, Hs, A=A)                 # the mound under the cap: the smoothest surface joining it
    cv = np.full(n, float(c)) if np.ndim(c) == 0 else np.asarray(c, float)
    delta = np.zeros(n)
    ramp = (Hs[mid] > 0).astype(float) if ramp_mm <= 0 else smoothstep(Hs[mid] / (ramp_mm * 1e-3))
    if band_mode == "fill":
        # inside the footprint the move is the mound's own; in the band outside it the smoothest field joining that
        # move to nothing at band_mm (scalar_fill, C1 with both) - where the skin round a mound stands off its wall
        # (a body's side beside a breast) the change is spread with the least bending instead of a fixed taper
        inside = np.zeros(n, bool); inside[mid] = dist_all[mid] <= 0.5            # on the footprint (its pixels, 1 mm)
        delta[mid] = np.where(inside[mid], (cv[mid] - 1.0) * Hs[mid] * ramp, 0.0)
        delta = scalar_fill(V, F, move & ~inside, delta, A=A)
    else:
        delta[mid] = (cv[mid] - 1.0) * Hs[mid] * m_all[mid] * ramp
    rep = {"moved": int((np.abs(delta) > 0).sum()), "smooth_mm": smooth_mm, "band_mm": band_mm, "ramp_mm": ramp_mm, "band_mode": band_mode}
    if rigid is not None and np.asarray(rigid, bool).any():
        rg = np.asarray(rigid, bool)
        ring = rg & ((A @ (~rg).astype(float)) > 0)
        d_anchor = float(np.mean(delta[ring])) if ring.any() else float(np.mean(delta[rg]))
        tree = cKDTree(V[rg]); dd, _ = tree.query(V, distance_upper_bound=rigid_blend_mm * 1e-3)
        blend = np.isfinite(dd) & ~rg
        fixed_val = delta.copy(); fixed_val[rg] = d_anchor
        delta = scalar_fill(V, F, blend, fixed_val, A=A)
        rep["rigid"] = {"vertices": int(rg.sum()), "move_mm": d_anchor * 1e3, "blend_mm": rigid_blend_mm, "blend_vertices": int(blend.sum())}
    Vn = V + delta[:, None] * a[None]
    # soundness: faces turned over
    def fnorm(X):
        nn = np.cross(X[F[:, 1]] - X[F[:, 0]], X[F[:, 2]] - X[F[:, 0]]); return nn / np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-30)
    touched = (np.abs(delta) > 0)[F].any(1)
    flips = int(((fnorm(V)[touched] * fnorm(Vn)[touched]).sum(1) < 0).sum())
    rep.update({"delta_mm": {"min": float(delta.min() * 1e3), "max": float(delta.max() * 1e3)}, "faces_turned_over": flips})
    return Vn, rep, {"delta": delta, "Hs": Hs, "h": h_all, "m": m_all}


def scalar_fill(V, F, free, values, A=None):
    """values on the free vertices replaced by the smoothest field joining the rest (surface_fairing.scalar_fill: the
    bi-Laplacian, cotangent weights of V, rows two rings past the free set so the field meets the held values with
    their slope)"""
    import surface_fairing as SF
    return SF.scalar_fill(V, F, free, values, A=A)


def soften_band(h, band, step, smooth_len_mm=3.0, pre_sigma_mm=3.0, eps=1e-6):
    """a junction softened on a height grid: inside `band` (weights 0..1, smooth) the heights are replaced by the thin
    plate that follows the heights round it - the smoothing spline argmin sum w (T - Hs)^2 + l^4 |grad^2 T|^2 with
    w = 1 - (1 - eps) band, l = smooth_len_mm (small: outside the band T follows Hs) - where Hs is h smoothed at
    pre_sigma_mm (NaN-aware), so the correction (T - Hs) x band is smooth and the fine relief (h - Hs) rides on it.
    A concave corner (a crease where a mound meets its wall) is filled with the least bending the band allows: the
    join's radius grows with the band's width. Returns the correction grid (0 outside the band, NaN off the data)."""
    ok = np.isfinite(h)
    s = pre_sigma_mm * 1e-3 / step
    num = ndimage.gaussian_filter(np.where(ok, h, 0.0), s); den = ndimage.gaussian_filter(ok.astype(float), s)
    Hs = np.where(ok, num / np.maximum(den, 1e-9), np.nan)
    n_r, n_c = h.shape
    def d(n, k):
        c = {1: [-1, 1], 2: [1, -2, 1]}[k]
        return sparse.diags([np.full(n - k, float(x)) for x in c], list(range(k + 1)), shape=(n - k, n)) / step ** k
    I_r, I_c = sparse.identity(n_r), sparse.identity(n_c)
    Duu = sparse.kron(I_r, d(n_c, 2)); Dvv = sparse.kron(d(n_r, 2), I_c); Duv = sparse.kron(d(n_r, 1), d(n_c, 1))
    K = (Duu.T @ Duu + Dvv.T @ Dvv + 2 * Duv.T @ Duv).tocsc()
    w = np.where(ok, 1.0 - (1.0 - eps) * np.clip(band, 0, 1), 0.0).ravel()
    lam = (smooth_len_mm * 1e-3) ** 4
    from scipy.sparse.linalg import splu
    T = splu((sparse.diags(w) + lam * K).tocsc()).solve(w * np.nan_to_num(Hs).ravel()).reshape(h.shape)
    return np.where(ok, (T - Hs) * np.clip(band, 0, 1), np.nan), Hs, T


def profile_concavity(skin, frame, thetas_deg, r_mm, smooth_mm=4.0):
    """curvature (1/m, + = concave seen from outside the mound, i.e. the profile bending away from the axis) of the
    front height map `skin` (n, n, heights along a; NaN off the skin) along rays from the frame origin.
    Returns (thetas, r_mm, K) with K[i, j] at theta i, radius r_mm[j]"""
    st = float(frame["step"]); n = int(frame["n"]); c0 = (n - 1) / 2
    r = np.asarray(r_mm, float) * 1e-3; dr = (r[1] - r[0])
    K = np.full((len(thetas_deg), len(r)), np.nan)
    for i, t in enumerate(np.radians(thetas_deg)):
        prof = ndimage.map_coordinates(skin, [r * np.sin(t) / st + c0, r * np.cos(t) / st + c0], order=1, cval=np.nan)
        ok = np.isfinite(prof)
        if ok.sum() < 10:
            continue
        j1 = np.nonzero(~ok)[0]; jend = j1[0] if len(j1) else len(r)
        p = ndimage.gaussian_filter1d(prof[:jend], smooth_mm * 1e-3 / dr)
        d1 = np.gradient(p, dr); k = np.gradient(d1, dr) / (1 + d1 ** 2) ** 1.5
        K[i, :jend] = k
    return np.asarray(thetas_deg, float), np.asarray(r_mm, float), K


def rim_concavity(skin, frame, thetas_deg, r_lo_mm, r_hi_mm, smooth_mm=4.0, dr_mm=0.5):
    """per ray: the peak concavity (1/m) within [r_lo, r_hi] (arrays or scalars, mm) and where it is (mm)"""
    r = np.arange(0, 150, dr_mm)
    th, r, K = profile_concavity(skin, frame, thetas_deg, r, smooth_mm)
    lo = np.broadcast_to(np.asarray(r_lo_mm, float), th.shape); hi = np.broadcast_to(np.asarray(r_hi_mm, float), th.shape)
    peak = np.full(len(th), np.nan); at = np.full(len(th), np.nan)
    for i in range(len(th)):
        m = (r >= lo[i]) & (r <= hi[i]) & np.isfinite(K[i])
        if m.any():
            j = np.nonzero(m)[0][np.argmax(K[i, m])]; peak[i] = K[i, j]; at[i] = r[j]
    return peak, at


# ------------------------------------------------------------------------------------------------ the similar resize
def _grid_thin_plate(n_r, n_c):
    """the thin-plate energy matrix of an (n_r, n_c) grid (unit spacing; natural edges): sum |d2/du2|^2 + |d2/dv2|^2 +
    2 |d2/dudv|^2 over the grid, as soften_band builds it"""
    def d(n, k):
        c = {1: [-1, 1], 2: [1, -2, 1]}[k]
        return sparse.diags([np.full(n - k, float(x)) for x in c], list(range(k + 1)), shape=(n - k, n))
    I_r, I_c = sparse.identity(n_r), sparse.identity(n_c)
    Duu = sparse.kron(I_r, d(n_c, 2)); Dvv = sparse.kron(d(n_r, 2), I_c); Duv = sparse.kron(d(n_r, 1), d(n_c, 1))
    return (Duu.T @ Duu + Dvv.T @ Dvv + 2 * Duv.T @ Duv).tocsr()


def similar_field(frame, centre_uv, s, core, zero, held=None, held_value=(0.0, 0.0), weight=None, fit_len_mm=8.0):
    """the lateral field (n, n, 2) (m; [..., 0] along u, [..., 1] along v; grids [row = v, col = u]) of a similarity of
    factor s about centre_uv. 0 on `zero` and `held_value` on `held` (fixed). Hard: (s - 1)(p - c) fixed on `core`, the
    smoothest field (the grid's thin-plate energy) on the rest. Soft (`weight` given, a grid 0..1; `core` unused): the
    field minimising sum weight |w - (s - 1)(p - c)|^2 + (fit_len_mm / step)^4 x thin-plate energy - the similarity's
    move is affine (no bending energy), so it is kept exactly wherever no fixed cell is within a few fit_len_mm, and it
    bends away from it towards the fixed cells over that length with no edge of its own.
    Returns (w, least det of the map's Jacobian, J det grid)"""
    from scipy.sparse.linalg import splu
    st = float(frame["step"]); n = int(frame["n"]); c0 = (n - 1) / 2
    kk = (np.arange(n) - c0) * st; U, Vv = np.meshgrid(kk, kk)
    tgt = np.stack([(s - 1.0) * (U - centre_uv[0]), (s - 1.0) * (Vv - centre_uv[1])], -1)
    soft = weight is not None
    val = np.zeros((n, n, 2)); fixed = np.asarray(zero, bool).copy()
    if not soft:
        fixed |= np.asarray(core, bool); val[core] = tgt[core]
    if held is not None:
        held = np.asarray(held, bool) & ~np.asarray(zero, bool)
        fixed = fixed | held; val[held] = np.asarray(held_value, float)
    K = _grid_thin_plate(n, n)
    if soft:
        lam = (fit_len_mm * 1e-3 / st) ** 4
        wt = np.clip(np.asarray(weight, float), 0, 1).ravel()
        K = (sparse.diags(wt) + lam * K).tocsr()
    f = ~fixed.ravel()
    w = val.copy()
    if f.any():
        Kff = K[f][:, f].tocsc(); Kfc = K[f][:, ~f]
        lu = splu(Kff)
        for comp in (0, 1):
            x = val[..., comp].ravel().copy()
            rhs = -(Kfc @ x[~f])
            if soft:
                rhs = rhs + (wt * tgt[..., comp].ravel())[f]
            x[f] = lu.solve(rhs)
            w[..., comp] = x.reshape(n, n)
    du_dv, du_du = np.gradient(w[..., 0], st); dv_dv, dv_du = np.gradient(w[..., 1], st)
    det = (1 + du_du) * (1 + dv_dv) - du_dv * dv_du
    return w, float(det.min()), det


def warp_lateral(V, frame, w, sel=None, depth_mm=(-60.0, -30.0)):
    """every selected vertex slides along the wall by the field w at its column and keeps its height above the wall (so
    every layer of a column moves alike and keeps its order); skin deeper than depth_mm[0] below the wall never moves,
    the slide eases in up to depth_mm[1]. Returns (V_new, moved mask)"""
    V = np.asarray(V, float)
    o, R, st, n, W = np.asarray(frame["o"], float), np.asarray(frame["R"], float), float(frame["step"]), int(frame["n"]), frame["wall"]
    c0 = (n - 1) / 2
    h, q = heights(V, frame)
    on = np.isfinite(h) if sel is None else (np.asarray(sel, bool) & np.isfinite(h))
    g = np.zeros(len(V))
    g[on] = smoothstep((h[on] * 1e3 - depth_mm[0]) / (depth_mm[1] - depth_mm[0]))
    x = q[:, 0] / st + c0; y = q[:, 1] / st + c0
    du = ndimage.map_coordinates(w[..., 0], [y, x], order=1, mode="constant", cval=0.0) * g
    dv = ndimage.map_coordinates(w[..., 1], [y, x], order=1, mode="constant", cval=0.0) * g
    mv = (g > 0) & ((du != 0) | (dv != 0))
    u1 = q[:, 0] + du; v1 = q[:, 1] + dv
    W0 = ndimage.map_coordinates(W, [y, x], order=1, mode="constant", cval=np.nan)
    W1 = ndimage.map_coordinates(W, [v1 / st + c0, u1 / st + c0], order=1, mode="constant", cval=np.nan)
    mv &= np.isfinite(W0) & np.isfinite(W1)
    qn = q.copy()
    qn[mv, 0] = u1[mv]; qn[mv, 1] = v1[mv]; qn[mv, 2] = q[mv, 2] + (W1[mv] - W0[mv])
    Vn = V.copy(); Vn[mv] = o + qn[mv] @ R
    return Vn, mv


def _raster(frame, q, ok):
    st = float(frame["step"]); n = int(frame["n"]); c0 = (n - 1) / 2
    m = np.zeros((n, n), bool)
    c = np.round(q[ok, 0] / st + c0).astype(int); r = np.round(q[ok, 1] / st + c0).astype(int)
    k = (c >= 0) & (c < n) & (r >= 0) & (r < n)
    m[r[k], c[k]] = True
    return m


def carry_mask(frame, w, mask, iters=6):
    """a grid mask carried by the map p -> p + w(p): the new mask at p is the old one at the map's inverse (fixed-point)"""
    st = float(frame["step"]); n = int(frame["n"])
    rr, cc = np.mgrid[0:n, 0:n].astype(float)
    x, y = cc.copy(), rr.copy()
    for _ in range(iters):
        x_new = cc - ndimage.map_coordinates(w[..., 0], [y, x], order=1, mode="nearest") / st
        y_new = rr - ndimage.map_coordinates(w[..., 1], [y, x], order=1, mode="nearest") / st
        x, y = x_new, y_new
    return ndimage.map_coordinates(np.asarray(mask, float), [y, x], order=1, mode="constant", cval=0.0) >= 0.5


def _quadric_eval(P, f, B, Q, k=48, chunk=20000):
    """f (given at 2-D points P) at the points Q by a weighted quadric fitted round B (each query's base point, near Q):
    its k nearest P, weights (1 - d^2 / R^2)^2 with R just past the k-th; smooth in Q, no triangulation"""
    from scipy.spatial import cKDTree
    tree = cKDTree(P); out = np.full(len(Q), np.nan)
    for i0 in range(0, len(Q), chunk):
        b = B[i0:i0 + chunk]; qq = Q[i0:i0 + chunk]
        d, j = tree.query(b, k=min(k, len(P)))
        R = d[:, -1:] * 1.05 + 1e-12
        w = (1 - (d / R) ** 2) ** 2
        x = (P[j, 0] - b[:, None, 0]) * 1e3; y = (P[j, 1] - b[:, None, 1]) * 1e3          # mm: a well-scaled system
        G = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], -1)
        GW = G * w[..., None]
        A = np.einsum("mki,mkj->mij", GW, G) + 1e-9 * np.eye(6)
        rhs = np.einsum("mki,mk->mi", GW, f[j])
        a = np.linalg.solve(A, rhs[..., None])[..., 0]
        dx = (qq[:, 0] - b[:, 0]) * 1e3; dy = (qq[:, 1] - b[:, 1]) * 1e3
        out[i0:i0 + chunk] = (a * np.stack([np.ones_like(dx), dx, dy, dx * dx, dx * dy, dy * dy], -1)).sum(1)
    return out


def _top_layer(frame, q, h, ok, tol):
    """vertices on the skin seen from the front along the axis: within tol of the highest skin in their column (3 x 3 cells)"""
    st = float(frame["step"]); n = int(frame["n"]); c0 = (n - 1) / 2
    c = np.round(q[:, 0] / st + c0).astype(int); r = np.round(q[:, 1] / st + c0).astype(int)
    inn = ok & (c >= 0) & (c < n) & (r >= 0) & (r < n)
    top = np.full((n, n), -np.inf)
    np.maximum.at(top, (r[inn], c[inn]), h[inn])
    top = ndimage.maximum_filter(top, size=3)
    out = np.zeros(len(q), bool)
    out[inn] = h[inn] >= top[r[inn], c[inn]] - tol
    return out


def resize_similar(V, F, frame, footprint, s, k, centre_uv, sel=None, cap=None, held_grid=None, smooth_mm=6.0, band_mm=40.0,
                   core_h_mm=1.0, cap_ring_mm=20.0, fit_len_mm=4.0, relax_mm=30.0, seat_fade_mm=20.0, top_tol_mm=2.0,
                   depth_mm=(-60.0, -30.0)):
    """the mound made s x as large with its proportions kept (module docstring, A SIMILAR RESIZE)"""
    V = np.asarray(V, float); F = np.asarray(F, np.int64); n = int(frame["n"]); st = float(frame["step"]); c0 = (n - 1) / 2
    cuv = np.asarray(centre_uv, float)
    sel = np.isfinite(heights(V, frame)[0]) if sel is None else np.asarray(sel, bool)
    # 1 the height
    V1, rep1, aux1 = resize(V, F, frame, footprint, k, sel=sel, cap=cap, smooth_mm=smooth_mm, band_mm=band_mm, ramp_mm=0.0, band_mode="fill",
                            cap_fill_first=True)
    Hs1 = aux1["Hs"] + aux1["delta"]
    h1, q1 = heights(V1, frame)
    # 2 the footprint. The mound (its smooth height over core_h_mm, on the footprint) asks for the similarity's move, fully
    # where it is clear of the cap's ring and of held / zero cells (relax_mm), easing to nothing towards them; the cap
    # is held (it moves as one); 0 past the band and on held cells; the field is the soft fit (similar_field, fit_len_mm)
    core = _raster(frame, q1, sel & np.isfinite(Hs1) & (Hs1 > core_h_mm * 1e-3))
    core = ndimage.binary_fill_holes(ndimage.binary_closing(core, iterations=2)) & footprint
    held = np.zeros((n, n), bool); held_value = np.zeros(2)
    if cap is not None and np.asarray(cap, bool).any():
        cp = np.asarray(cap, bool) & sel
        held = ndimage.binary_fill_holes(ndimage.binary_dilation(_raster(frame, q1, cp), iterations=2))
        held_value = (s - 1.0) * (q1[cp, :2].mean(0) - cuv)
    dist_out = ndimage.distance_transform_edt(~footprint) * st * 1e3
    zero = (dist_out > band_mm) | ~np.isfinite(frame["wall"])
    if held_grid is not None:
        zero |= np.asarray(held_grid, bool)
    d_zero = ndimage.distance_transform_edt(~zero) * st * 1e3
    d_held = ndimage.distance_transform_edt(~held) * st * 1e3 if held.any() else np.full((n, n), 1e9)
    weight = ndimage.gaussian_filter(core.astype(float), 2.0) * smoothstep(d_zero / relax_mm) * smoothstep((d_held - 0.25 * cap_ring_mm) / (0.75 * cap_ring_mm))
    w, det_min, det = similar_field(frame, cuv, s, core, zero, held=held if held.any() else None, held_value=held_value,
                                    weight=weight, fit_len_mm=fit_len_mm)
    V2, mv = warp_lateral(V1, frame, w, sel=sel, depth_mm=depth_mm)
    # 3 the cap and the ring round it, where the slide is not the similarity's (the cap keeps its size): each vertex of the
    # skin seen from the front takes the similar mound's smooth height where it now stands, h = Hs1(c + (p' - c) / s), plus
    # its own relief (h1 - Hs1: the cap's shape, the fine relief), fully within cap_ring_mm of the cap, easing out over
    # seat_fade_mm beyond, where the slide is the similarity's and the change is 0. Elsewhere (the mound towards held cells:
    # it stays where it meets them, lowered by k) the form is the slid one; one smooth field, no second form blended in
    seat = {"vertices": 0}
    from scipy.interpolate import LinearNDInterpolator
    samp = lambda G: ndimage.map_coordinates(G, [q1[:, 1] / st + c0, q1[:, 0] / st + c0], order=1, cval=0.0)
    top = _top_layer(frame, q1, h1, sel & np.isfinite(h1) & np.isfinite(Hs1), top_tol_mm * 1e-3) & (Hs1 > 0)
    b = (1.0 - smoothstep((samp(d_held) - cap_ring_mm) / seat_fade_mm)) if held.any() else np.zeros(len(V))
    zone = top & (b > 0)
    src = top & (samp(d_held) <= cap_ring_mm + seat_fade_mm + 15.0)
    if zone.any():
        h2, q2 = heights(V2, frame)
        pre = cuv + (q2[zone, :2] - cuv) / s
        # the smooth height at the pre-image by a local quadric of Hs1 round each vertex's own first place (its 48 nearest
        # source vertices): a piecewise-linear interpolant over the projected vertices printed the mesh's packed rings
        # round the cap into the skin (relief() at 5 mm 1.4-1.9 x round the areola, woman2 13a5)
        Hm = _quadric_eval(q1[src, :2], Hs1[src], q1[zone, :2], pre)
        ok = np.isfinite(Hm)
        ids = np.nonzero(zone)[0][ok]
        dh = b[ids] * ((Hm[ok] + (h1[ids] - Hs1[ids])) - h2[ids])
        a = np.asarray(frame["R"], float)[2]
        V2 = V2.copy(); V2[ids] += dh[:, None] * a[None]
        seat = {"vertices": int(len(ids)), "outside_data": int((~ok).sum()), "dh_mm_p1_p99": [float(np.percentile(dh, 1) * 1e3), float(np.percentile(dh, 99) * 1e3)],
                "dh_mm_min_max": [float(dh.min() * 1e3), float(dh.max() * 1e3)]}

    def fnorm(X):
        nn = np.cross(X[F[:, 1]] - X[F[:, 0]], X[F[:, 2]] - X[F[:, 0]])
        return nn / np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-30)
    moved = np.linalg.norm(V2 - V, axis=1) > 0
    touched = moved[F].any(1)
    flips = int(((fnorm(V)[touched] * fnorm(V2)[touched]).sum(1) < 0).sum())
    wl = np.linalg.norm(w, axis=-1) * 1e3
    kk = (np.arange(n) - c0) * st; U, Vv = np.meshgrid(kk, kk)
    dev = np.hypot(w[..., 0] - (s - 1) * (U - cuv[0]), w[..., 1] - (s - 1) * (Vv - cuv[1])) * 1e3
    rep = {"s": float(s), "k": float(k), "centre_uv_mm": [float(x * 1e3) for x in centre_uv], "height_step": rep1,
           "lateral": {"core_cells": int(core.sum()), "held_cells": int(held.sum()), "held_value_mm": (held_value * 1e3).tolist(),
                       "field_mm_max": float(wl.max()), "jacobian_det_min": det_min, "vertices_slid": int(mv.sum()),
                       "off_similarity_mm_on_core_p50_p95_max": [float(x) for x in np.percentile(dev[core], [50, 95, 100])]},
           "seat": seat,
           "settings": {"smooth_mm": smooth_mm, "band_mm": band_mm, "core_h_mm": core_h_mm, "cap_ring_mm": cap_ring_mm, "fit_len_mm": fit_len_mm,
                        "relax_mm": relax_mm, "seat_fade_mm": seat_fade_mm, "top_tol_mm": top_tol_mm, "depth_mm": list(depth_mm)},
           "moved": int(moved.sum()), "faces_turned_over": flips}
    return V2, rep, {"w": w, "det": det, "core": core, "held": held, "zero": zero, "footprint": carry_mask(frame, w, footprint),
                     "V_height": V1, "aux_height": aux1, "slid": mv, "seat_weight": b, "seated": zone, "weight": weight, "off_similarity_mm": dev}
