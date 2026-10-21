"""SECTION CURVATURE (2026-10-19): curvature along the REAL surface curve, cut by planes through a feature's axis.
Why: projecting a region onto its front plane (surface_analysis.py) breaks down where the surface turns away (the side
of the breast), exactly where the flat band the person saw sits. A plane through the nipple axis cuts the actual skin
curve from the nipple round onto the side; its curvature along arc length shows flats and bumps without projection
artefacts (J14: measure a feature in its own frame; the cross-section is the tool that matched the person's eye).

profiles(V, F, centre, axis, ref_dir, angles_deg, inner) -> {angle: (arc_mm, curvature_per_m)}
  centre: a point on the feature (nipple tip); axis: the feature's outward axis; ref_dir: 0 deg direction in the plane
  perpendicular to the axis (e.g. toward the arm); inner: a point inside the body on the axis (the cut's origin).
"""
import numpy as np


def slice_points(V, F, origin, normal):
    s = (V - origin) @ normal
    sf = s[F]; cross = (sf.min(1) < 0) & (sf.max(1) > 0)
    T = F[cross]; st = s[T]; pts = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        m = (st[:, a] < 0) != (st[:, b] < 0)
        va, vb = V[T[m, a]], V[T[m, b]]; sa, sb = st[m, a], st[m, b]
        pts.append(va + (vb - va) * (sa / (sa - sb))[:, None])
    return np.concatenate(pts)


def profile(V, F, tip, axis, direction, inner, max_arc=0.14, step_deg=0.25, return_points=False, phi_max=120, exact=False,
            smooth_n=21):
    """Outer surface curve in the plane spanned by axis and direction, from the axis outward toward `direction`.
    return_points (2026-10-19, issue 01): also the smoothed curve's 3-D points at the returned samples, so a caller can
    say WHERE along the skin a reading sits (areola edge, fold) from the mesh's own zones. phi_max: how far round from
    the axis the cut reaches (deg about `inner`). exact (issue 01): each bin's outermost point is kept at its OWN angle;
    the default places it at the bin's centre angle, which moves it by up to step/2 round `inner` (0.2 mm at 100 mm) and,
    where the skin runs oblique to the ray (the lower pole into the fold), turns that into a radial jitter that reads as
    curvature noise of +-10-20 /m after the 10 mm smoothing. smooth_n: the box smoothing in 0.5 mm samples (21 = 10 mm)."""
    pn = np.cross(axis, direction); pn /= np.linalg.norm(pn)
    P = slice_points(V, F, tip, pn)
    e1, e2 = axis, direction                                       # in-plane frame about `inner`
    q = P - inner; x, y = q @ e1, q @ e2
    phi = np.degrees(np.arctan2(y, x)); rho = np.hypot(x, y)
    keep = (phi >= -2) & (phi <= phi_max)                          # from the axis round toward the side (and a bit behind)
    phi, rho = phi[keep], rho[keep]
    bins = np.arange(0, phi_max, step_deg)
    xs, ys = [], []
    for b0 in bins:
        m = (phi >= b0) & (phi < b0 + step_deg)
        if not m.any(): continue
        k = np.argmax(rho[m])                                      # outermost skin point at this angle
        r = rho[m][k]; t = np.radians(phi[m][k] if exact else b0 + step_deg / 2)
        xs.append(r * np.cos(t)); ys.append(r * np.sin(t))
    C = np.stack([xs, ys], 1)
    ds = np.linalg.norm(np.diff(C, axis=0), axis=1); s = np.r_[0, np.cumsum(ds)]
    keep = s <= max_arc; C, s = C[keep], s[keep]
    # resample at 0.5 mm, smooth over 4 mm, curvature from first and second derivatives
    si = np.arange(0, s[-1], 0.0005); xi = np.interp(si, s, C[:, 0]); yi = np.interp(si, s, C[:, 1])
    k = smooth_n; ker = np.ones(k) / k                             # 10 mm smoothing: read form, not sampling jitter
    xi = np.convolve(xi, ker, mode="same"); yi = np.convolve(yi, ker, mode="same")
    dx, dy = np.gradient(xi, si), np.gradient(yi, si); ddx, ddy = np.gradient(dx, si), np.gradient(dy, si)
    kap = (dx * ddy - dy * ddx) / np.maximum((dx ** 2 + dy ** 2) ** 1.5, 1e-12)
    trim = slice(k, len(si) - k)
    if return_points:
        P3 = inner + np.outer(xi[trim], e1) + np.outer(yi[trim], e2)
        return si[trim] * 1000, kap[trim], P3
    return si[trim] * 1000, kap[trim]                              # + = convex (bulging out), per metre (CCW about `inner`)
