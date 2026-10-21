"""SHADING FIT + DE-LIT ALBEDO (domain-neutral): one directional light fitted to a photo from a mesh's normals, the
render-vs-photo shading agreement, and per-vertex colour with that shading divided out.

Why it exists (woman2, 2026-10-19): the engine's `light_match.py` matches luminance DISTRIBUTIONS by Blender renders
(no per-pixel agreement, no albedo), `object_checks.shading_consistency` scores per FACET medians (a rock's planar
faces), and the cat's pigment chain projected photo colour with its shading still in it. A smooth subject needs a
per-pixel shading model to (a) say whether the form explains the photo's shading (T3) and (b) take the shading OUT of
the colour, so no shadow is painted on (E5, T7).

  normals     per pixel: the front face from engine/tools/zbuffer_numba (same camera convention as object_checks),
              vertex normals interpolated barycentrically (smooth shading, as Blender renders it).
  light       in LINEAR light, photo luminance Y = a + b . n on skin pixels (minus excluded regions, a band at the
              silhouette and the frame cuts) by least squares: ambient a, light vector b (direction b/|b|). One light.
  agreement   Pearson r between the low-pass (Gaussian sigma LP_SIGMA px, normalised convolution inside the mask) photo
              luminance and the low-pass fitted shading, on the same pixels.
  albedo      linear photo / relative shading (S / median S), back to sRGB; per vertex sampled where the vertex is
              visible and faces the camera (n.v >= VIS_LO), blended over [VIS_LO, VIS_HI] into the front's skin
              statistics (median albedo + its linear trend with height) for the unseen side.
  bake test   Pearson r between low-pass albedo luminance and low-pass shading on the front: a photo with its
              shading still in it correlates strongly (+), an over-divided one strongly (-); a de-lit one near 0.

API: fit(v, f, cam, rgb, mask, exclude=None) -> dict ; vertex_colours(v, f, cam, fitres, ...) -> (n,3) sRGB
"""
import numpy as np
from scipy import ndimage as ndi

import zbuffer_numba as ZB

LP_SIGMA = 6.0      # px: removes skin texture and pores, keeps form shading (woman2: ~3.3 mm at 0.55 mm/px)
EDGE_BAND = 6       # px at the silhouette left out of the fit: grazing normals and backdrop bleed
VIS_LO, VIS_HI = 0.25, 0.50
REL_MIN = 0.0       # (off) a floor on the relative shading divided out; 0.6 was tried on woman2 rli: a soft studio light wraps further round the outline
                    # than one Lambert light, and dividing by the Lambert falloff there turned the rims white (woman2 rlh)
INNER_BAND = 25     # px: the bake test is also reported away from the outline, where one Lambert light is a fair model
DEPTH_TOL = 0.0015  # m: a vertex is visible when within 1.5 mm of the z-buffer front at its pixel


import os as _os_mg, sys as _sys_mg  # noqa: E402  (build A1: the engine's one closest point, normals, cotangent Laplacian)
_MG_DIR = _os_mg.path.normpath(_os_mg.path.join(_os_mg.path.dirname(_os_mg.path.abspath(__file__)), '.'))
if _MG_DIR not in _sys_mg.path:
    _sys_mg.path.append(_MG_DIR)
import mesh_geom as _MG  # noqa: E402


def srgb_to_lin(c):
    c = np.asarray(c, float); return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, float), 0, 1); return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def vertex_normals(v, f):
    return _MG.vertex_normals(v, f, eps=1e-12)


def pixel_normals(v, f, cam, rast, vn):
    fid = rast["face"]; m = fid >= 0
    rows, cols = np.nonzero(m); F = f[fid[m]]
    uv = cam.project(v)[:, :2]
    P = np.c_[cols + 0.5, rows + 0.5]
    a, b, c = uv[F[:, 0]], uv[F[:, 1]], uv[F[:, 2]]
    A = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
    w0 = ((b[:, 0] - P[:, 0]) * (c[:, 1] - P[:, 1]) - (c[:, 0] - P[:, 0]) * (b[:, 1] - P[:, 1])) / A
    w1 = ((c[:, 0] - P[:, 0]) * (a[:, 1] - P[:, 1]) - (a[:, 0] - P[:, 0]) * (c[:, 1] - P[:, 1])) / A
    w2 = 1 - w0 - w1
    n = w0[:, None] * vn[F[:, 0]] + w1[:, None] * vn[F[:, 1]] + w2[:, None] * vn[F[:, 2]]
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    N = np.zeros(m.shape + (3,)); N[m] = n
    return N, m


def lowpass(img, m, sigma=LP_SIGMA):
    w = ndi.gaussian_filter(m.astype(float), sigma)
    if img.ndim == 3:
        return np.stack([ndi.gaussian_filter(img[..., c] * m, sigma) for c in range(img.shape[2])], -1) / np.maximum(w, 1e-6)[..., None]
    return ndi.gaussian_filter(img * m, sigma) / np.maximum(w, 1e-6)


def pearson(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def fit(v, f, cam, rgb, mask, exclude=None, cut_rows=3):
    """rgb sRGB [0,1] (H,W,3); mask = photo subject mask; exclude = pixels left out (areolae, navel, ...)"""
    v = np.asarray(v, float); f = np.asarray(f, np.int64)
    rast = ZB.rasterize(v, f, cam)
    vn = vertex_normals(v, f)
    N, mm = pixel_normals(v, f, cam, rast, vn)
    lin = srgb_to_lin(rgb); Y = lin @ np.array([0.2126, 0.7152, 0.0722])
    use = mm & mask & ~ndi.binary_dilation(~(mm & mask), iterations=EDGE_BAND)
    use[:cut_rows] = False; use[-cut_rows:] = False
    if exclude is not None:
        use &= ~exclude
    A = np.c_[np.ones(use.sum()), N[use]]
    coef, *_ = np.linalg.lstsq(A, Y[use], rcond=None)
    S = np.where(mm, coef[0] + N @ coef[1:], 0.0)
    S = np.maximum(S, 0.05 * np.median(S[use]))
    Yl, Sl = lowpass(Y, use), lowpass(S, use)
    r = pearson(Yl[use], Sl[use])
    rel = np.maximum(S / np.median(S[use]), REL_MIN)
    alb = lin / rel[..., None]
    alb_l = lowpass(alb @ np.array([0.2126, 0.7152, 0.0722]), use)
    bake_r = pearson(alb_l[use], Sl[use])
    inner = use & ~ndi.binary_dilation(~use, iterations=INNER_BAND)
    bake_inner = pearson(alb_l[inner], Sl[inner])
    plant_photo = pearson(lowpass(Y, use)[use], Sl[use])
    plant_over = pearson(lowpass((lin / rel[..., None] ** 2) @ np.array([0.2126, 0.7152, 0.0722]), use)[use], Sl[use])
    l = coef[1:] / np.linalg.norm(coef[1:])          # world axes (the normals are world normals)
    return dict(rast=rast, N=N, S=S, rel=rel, use=use, albedo_lin=alb, vn=vn, photo_mask=mask, rgb=rgb, coef=coef,
                report=dict(ambient=float(coef[0]), light_vec=coef[1:].tolist(), light_dir_cam=l.tolist(),
                            fit_pixels=int(use.sum()), shading_corr_lowpass=round(r, 4), bake_corr_albedo_vs_shading=round(bake_r, 4),
                            bake_corr_interior=round(bake_inner, 4), interior_band_px=INNER_BAND,
                            bake_plant_photo_itself=round(plant_photo, 4), bake_plant_over_divided=round(plant_over, 4),
                            fit_rmse=float(np.sqrt(np.mean((Y[use] - S[use]) ** 2)))))


def vertex_colours(v, f, cam, fr, front_stats_exclude=None):
    """per-vertex sRGB: de-lit photo where seen, the front's skin statistics where unseen, blended by facing"""
    v = np.asarray(v, float); vn = fr["vn"]; rast = fr["rast"]
    uvz = cam.project(v); H, W = rast["mask"].shape
    col = np.clip(np.floor(uvz[:, 0]).astype(int), 0, W - 1); row = np.clip(np.floor(uvz[:, 1]).astype(int), 0, H - 1)
    zf = rast["zfront"][row, col]
    view = cam.forward                                     # camera looks along +forward; facing = n . (-forward)
    facing = -(vn @ view)
    seen_px = rast["mask"] & fr["photo_mask"]          # visibility: the model's front AND the photo's subject (not the fit set:
    vis = (np.abs(uvz[:, 2] - zf) < DEPTH_TOL) & (facing > VIS_LO) & seen_px[row, col]   # excluded pixels still carry colour)
    alb = fr["albedo_lin"]
    stat_m = fr["use"].copy()
    if front_stats_exclude is not None:
        stat_m &= ~front_stats_exclude
    rows_s, cols_s = np.nonzero(stat_m)
    vals = alb[stat_m]
    # front skin statistics: median + linear trend with image row (height)
    Z = np.c_[np.ones(len(rows_s)), rows_s / H]
    trend = np.stack([np.linalg.lstsq(Z, vals[:, c], rcond=None)[0] for c in range(3)], 1)
    back = np.c_[np.ones(len(v)), np.clip(row / H, 0, 1)] @ trend
    w = np.clip((facing - VIS_LO) / (VIS_HI - VIS_LO), 0, 1); w = w * w * (3 - 2 * w); w = np.where(vis, w, 0.0)
    front = alb[row, col]
    out = w[:, None] * front + (1 - w[:, None]) * back
    return lin_to_srgb(out), dict(seen_vertices=int(vis.sum()), trend=trend.tolist(), w=w)
