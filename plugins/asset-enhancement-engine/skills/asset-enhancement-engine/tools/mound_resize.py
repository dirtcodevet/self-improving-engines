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
                             ramp_mm=4.0, rigid_blend_mm=10.0, band_mode="taper")
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
           band_mode="taper"):
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
