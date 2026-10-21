"""Domain-neutral checks for a solid object rebuilt from one photo (any rigid object: rock, stone, carving, prop).

Written for cases/rock1 (criteria R1, R3, R4, R5, R6 and the person's two decisions in cases/rock1/ROUND0.md), but
nothing here knows what the object is. Everything is plain numpy/scipy so a check can run outside Blender; the only
Blender code is the two bpy_* collectors at the bottom, which run inside Blender and hand plain data to the checks.

Conventions: world is z-up metres; the ground is z = ground_z. Camera space is OpenCV style (x right, y down, z
forward); pixel (col, row) has its centre at (col + 0.5, row + 0.5). Images are float arrays in [0, 1].

  Camera / rasterize / lambert_render  the measuring instrument: a z-buffer through a pinhole (or orthographic)
                        camera, giving the front face id, the entry depth and the FIRST EXIT depth per pixel.
  R1 silhouette_match   mask IoU >= 0.97 and symmetric contour-distance p95 <= 3 px.
  R3 shading_consistency per-face median luminance, render vs photo: Pearson r >= 0.9, the same brightness order on
                        every pair of faces that the photo separates clearly, and every face's out-of-fold residual
                        (2-fold affine fit, folds fixed by label parity BEFORE the fit - A23) <= 8 % of the range.
  R4 colour_match       CIE76 dE of each region's mean L*a*b* <= 5.
  R4 grain_match        scale-normalised LoG "size spectrum": the peak scale within +-20 %, the grain amplitude at the
                        photo's peak within [0.67, 1.5] x, and a real interior peak on both.
  R5 solid_integrity    engine/checks/skin_checks.skin_integrity (reused, A16): closed, manifold, oriented, 1 shell,
                        no self-intersection.
  R5 ground_contact     lowest point within +-1 mm of the ground (floating / sinking), and the visible near-ground
                        band lands on the photo's contact-shadow mask (precision >= 0.9, recall >= 0.8).
  R6 thickness_check    inward-normal ray thickness of every surface sample; thin = < 15 % of the visible depth;
                        fails when thin samples exceed 1 % of the surface area.
  R6 mirror_similarity  best improper isometry (reflection + ICP) from the unseen back onto the visible front; the
                        back fails as a mirror copy when > 50 % of the back that overlaps the mirrored front lies on it
                        within 0.5 % of the size AND with normals within 10 deg.
  D  no_armature        no armature object, armature modifier, armature parent or armature constraint.
  D  horizontal_extent  largest horizontal extent (max Feret diameter of the xy projection) = target +- 5 %.

Proofs on planted failures on every side: object_checks_prove.py (same folder) -> cases/rock1/checks_proven.json.
"""
import os
import sys

import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull, cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ---- pass marks, each with its reason
IOU_MIN = 0.97          # R1, ROUND0.md
CONTOUR_P95_MAX = 3.0   # R1, ROUND0.md, px
CORR_MIN = 0.90         # R3, ROUND0.md
RESID_MAX = 0.08        # R3: a 10 deg tilt changes n.l by 0.17 sin(theta); for faces lit at 30-80 deg that is 0.087-0.17 of
                        # the [0, 1] range, so 0.08 of the face-luminance range sits just under the smallest planted change.
                        # Faces lit within 30 deg of their normal cannot show a tilt in shading (cos is flat there): R1/R2 own that.
ORDER_MARGIN = 0.05     # R3: a pair counts for the brightness order only when the photo separates the two faces by > 5 % of
                        # the range (about 3x the per-face mean noise of a grainy face of 200 px); closer pairs are ties.
MIN_FACE_PX = 200       # R3/R4: a face/region needs >= 200 px for its mean to be stable (grain std 0.1 -> s.e. < 0.02).
DE_MAX = 5.0            # R4, ROUND0.md (CIE76)
GRAIN_SIZE_TOL = 0.20   # R4, ROUND0.md
GRAIN_AMP = (0.67, 1.5) # R4 (estimate, flagged): ROUND0 sets no amplitude; +-50 % contrast is where grain visibly changes
                        # character. It exists so "grain removed" and "grain exaggerated" cannot pass on size alone.
GROUND_TOL = 0.001      # R5: +-1 mm. The planted 3 mm lift/sink must fail with margin, and 1 mm is ~1.5 px at 0.7 m over
                        # ~1100 px: the photo cannot place the contact tighter than that.
CONTACT_BAND = 0.005    # R5: surface within 5 mm of the ground is what darkens the contact shadow (occlusion band).
CONTACT_NEAR_PX = 4     # R5: contact pixels may sit up to 4 px from the shadow mask (the mask edge is soft by ~2-3 px).
CONTACT_PREC, CONTACT_REC = 0.90, 0.80
THIN_FRAC = 0.15        # R6, ROUND0.md: no sliver thinner than 15 % of the visible depth
THIN_AREA_MAX = 0.01    # R6: thin samples may cover <= 1 % of the surface (acute fracture edges leave a legitimately thin
                        # strip; 1 % of a 0.7 m rock is ~ a 9 x 9 cm patch, the smallest sliver that reads in a turnaround).
MIRROR_EPS = 0.005      # R6: 0.5 % of the size (3.5 mm on 0.7 m): a copied surface lands far closer; independent facets do not
MIRROR_ANG = 10.0       # R6: deg. A copy roughened by 1 mm on 2.5 cm triangles has ~4.5 deg rms normal noise (2 sigma = 9 deg),
                        # while facets of an independent back differ from the mirrored front by more (proof: score <= 0.01)
MIRROR_MAX = 0.50       # R6: more than half of the back reproducing the mirrored front is a copy, not a continuation
EXTENT_TARGET, EXTENT_TOL = 0.70, 0.05   # the person's decision 2026-10-18 (NOTES.md)


# =====================================================================  camera and z-buffer
class Camera:
    """x_cam = R @ x_world + t. Perspective: u = fx X/Z + cx. Orthographic: u = fx X + cx (fx = px per metre)."""

    def __init__(self, R, t, fx, fy, cx, cy, W, H, ortho=False):
        self.R = np.asarray(R, float); self.t = np.asarray(t, float)
        self.fx, self.fy, self.cx, self.cy, self.W, self.H, self.ortho = float(fx), float(fy), float(cx), float(cy), int(W), int(H), bool(ortho)

    @classmethod
    def look_at(cls, eye, target, fx, W, H, up=(0, 0, 1), ortho=False):
        eye = np.asarray(eye, float); fwd = np.asarray(target, float) - eye; fwd /= np.linalg.norm(fwd)
        r = np.cross(fwd, up); r /= np.linalg.norm(r); d = np.cross(fwd, r)
        R = np.stack([r, d, fwd]); t = -R @ eye
        return cls(R, t, fx, fx, W / 2.0, H / 2.0, W, H, ortho)

    @property
    def eye(self):
        return -self.R.T @ self.t

    @property
    def forward(self):
        return self.R[2]

    def to_cam(self, P):
        return np.asarray(P, float) @ self.R.T + self.t

    def project(self, P):
        X = self.to_cam(P)
        if self.ortho:
            return np.c_[self.fx * X[:, 0] + self.cx, self.fy * X[:, 1] + self.cy, X[:, 2]]
        return np.c_[self.fx * X[:, 0] / X[:, 2] + self.cx, self.fy * X[:, 1] / X[:, 2] + self.cy, X[:, 2]]


def face_normals(v, f):
    n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-30)


def rasterize(v, f, cam):
    """z-buffer at pixel centres. Returns dict: face (front-most front-facing triangle id, -1 = none), zfront (its
    depth), zexit (depth of the nearest BACK-facing triangle = first exit for a closed outward mesh), mask."""
    v = np.asarray(v, float); f = np.asarray(f, np.int64)
    W, H = cam.W, cam.H
    uvz = cam.project(v); Xc = cam.to_cam(v)
    nc = np.cross(Xc[f[:, 1]] - Xc[f[:, 0]], Xc[f[:, 2]] - Xc[f[:, 0]])
    front = (nc[:, 2] < 0) if cam.ortho else (np.einsum("ij,ij->i", nc, Xc[f[:, 0]]) < 0)
    zf = np.full((H, W), np.inf); ze = np.full((H, W), np.inf); fid = np.full((H, W), -1, np.int64)
    T = uvz[f]
    lo = np.floor(T[:, :, :2].min(1) - 0.5).astype(int); hi = np.ceil(T[:, :, :2].max(1) - 0.5).astype(int)
    for i in range(len(f)):
        x0, y0 = max(lo[i, 0], 0), max(lo[i, 1], 0); x1, y1 = min(hi[i, 0], W - 1), min(hi[i, 1], H - 1)
        if x1 < x0 or y1 < y0:
            continue
        (u0, v0, z0), (u1, v1, z1), (u2, v2, z2) = T[i]
        A = (u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)
        if abs(A) < 1e-12:
            continue
        px = np.arange(x0, x1 + 1) + 0.5; py = (np.arange(y0, y1 + 1) + 0.5)[:, None]
        w0 = ((u1 - px) * (v2 - py) - (u2 - px) * (v1 - py)) / A
        w1 = ((u2 - px) * (v0 - py) - (u0 - px) * (v2 - py)) / A
        w2 = 1.0 - w0 - w1
        ins = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not ins.any():
            continue
        z = (w0 * z0 + w1 * z1 + w2 * z2) if cam.ortho else 1.0 / (w0 / z0 + w1 / z1 + w2 / z2)
        if front[i]:
            sub = zf[y0:y1 + 1, x0:x1 + 1]; upd = ins & (z < sub)
            sub[upd] = z[upd]; fid[y0:y1 + 1, x0:x1 + 1][upd] = i
        else:
            sub = ze[y0:y1 + 1, x0:x1 + 1]; upd = ins & (z < sub); sub[upd] = z[upd]
    return dict(face=fid, zfront=zf, zexit=ze, mask=fid >= 0, front_facing=front)


def lambert_render(v, f, rast, light, albedo=None, ambient=0.15, kd=0.85, bg=1.0):
    """flat Lambert image under ONE directional light (unit vector TOWARDS the light). albedo: None, (H,W) or (H,W,3)."""
    n = face_normals(np.asarray(v, float), np.asarray(f, np.int64))
    s = ambient + kd * np.clip(n @ (np.asarray(light, float) / np.linalg.norm(light)), 0, None)
    fid = rast["face"]; m = fid >= 0
    sh = np.where(m, s[np.maximum(fid, 0)], 0.0)
    if albedo is None:
        albedo = 1.0
    albedo = np.asarray(albedo, float)
    if albedo.ndim == 3:
        img = sh[..., None] * albedo; img[~m] = bg
    else:
        img = sh * albedo; img = np.where(m, img, bg)
    return img


def luminance(rgb):
    rgb = np.asarray(rgb, float)
    return rgb if rgb.ndim == 2 else rgb @ np.array([0.2126, 0.7152, 0.0722])


# =====================================================================  R1 silhouette
def _contour(m):
    return m & ~ndimage.binary_erosion(m, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool), border_value=0)


def silhouette_match(model_mask, photo_mask, iou_min=IOU_MIN, p95_max=CONTOUR_P95_MAX):
    a = np.asarray(model_mask, bool); b = np.asarray(photo_mask, bool)
    inter = (a & b).sum(); union = (a | b).sum(); iou = float(inter / union) if union else 0.0
    ca, cb = _contour(a), _contour(b)
    if not ca.any() or not cb.any():
        return dict(iou=iou, contour_p95_px=float("inf"), pass_iou=False, pass_contour=False, **{"pass": False})
    da = ndimage.distance_transform_edt(~cb)[ca]; db = ndimage.distance_transform_edt(~ca)[cb]
    d = np.r_[da, db]; p95 = float(np.percentile(d, 95))
    ok_i, ok_c = iou >= iou_min, p95 <= p95_max
    return {"iou": round(iou, 5), "contour_p95_px": round(p95, 3), "contour_max_px": round(float(d.max()), 2),
            "p95_model_to_photo": round(float(np.percentile(da, 95)), 3), "p95_photo_to_model": round(float(np.percentile(db, 95)), 3),
            "model_px": int(a.sum()), "photo_px": int(b.sum()), "pass_iou": bool(ok_i), "pass_contour": bool(ok_c), "pass": bool(ok_i and ok_c)}


# =====================================================================  R3 shading
def shading_consistency(label_map, render_lum, photo_lum, min_px=MIN_FACE_PX, corr_min=CORR_MIN, resid_max=RESID_MAX,
                        order_margin=ORDER_MARGIN, erode_px=2):
    """label_map: (H,W) int, the MODEL's face label per pixel (-1 = background). Per face: render vs photo
    luminance over the same pixels, as the MEDIAN over the face eroded by erode_px. Median, not mean: when a model face
    is tilted its region grows into the photo's neighbouring faces, and a mean then follows the render (proof v1: a
    -10 deg tilt grew the face 24 % and passed); the median holds while under half the region is a neighbour. Affine render->photo fitted 2-fold (folds = label parity, fixed before the fit);
    each face's residual is predicted from the OTHER fold's fit."""
    lab = np.asarray(label_map)
    if erode_px > 0:                                                   # drop each face's border pixels (raster edges)
        inner = ndimage.minimum_filter(lab, 2 * erode_px + 1) == ndimage.maximum_filter(lab, 2 * erode_px + 1)
        lab = np.where(inner, lab, -1)
    ok = lab >= 0
    ids, cnt = np.unique(lab[ok], return_counts=True); ids = ids[cnt >= min_px]; cnt = cnt[cnt >= min_px]
    if len(ids) < 4:
        return {"pass": False, "reason": f"only {len(ids)} faces with >= {min_px} px"}
    r = np.asarray(ndimage.median(render_lum, lab, ids)); p = np.asarray(ndimage.median(photo_lum, lab, ids))
    corr = float(np.corrcoef(r, p)[0, 1]) if r.std() > 0 and p.std() > 0 else 0.0
    rng = float(np.percentile(p, 95) - np.percentile(p, 5)) or 1e-6
    pred = np.zeros_like(p); slopes = []
    fold = ids % 2
    for k in (0, 1):
        tr, te = fold != k, fold == k
        if tr.sum() < 2:
            tr = np.ones_like(tr)
        Am = np.c_[np.ones(tr.sum()), r[tr]]; coef = np.linalg.lstsq(Am, p[tr], rcond=None)[0]
        slopes.append(float(coef[1])); pred[te] = coef[0] + coef[1] * r[te]
    resid = np.abs(p - pred) / rng
    dp = p[:, None] - p[None, :]; dr = r[:, None] - r[None, :]
    sep = np.triu(np.abs(dp) > order_margin * rng, 1)
    disc = sep & (np.sign(dp) != np.sign(dr))
    worst = int(np.argmax(resid))
    ok_c, ok_s, ok_r, ok_o = corr >= corr_min, min(slopes) > 0, float(resid.max()) <= resid_max, int(disc.sum()) == 0
    di = np.argwhere(disc)[:10]
    return {"faces": int(len(ids)), "corr": round(corr, 4), "fold_slopes": [round(s, 4) for s in slopes],
            "resid_max": round(float(resid.max()), 4), "resid_worst_face": int(ids[worst]),
            "order_pairs_checked": int(sep.sum()), "order_discordant": int(disc.sum()),
            "discordant_examples": [[int(ids[i]), int(ids[j])] for i, j in di],
            "pass_corr": bool(ok_c and ok_s), "pass_resid": bool(ok_r), "pass_order": bool(ok_o), "pass": bool(ok_c and ok_s and ok_r and ok_o)}


# =====================================================================  R4 colour and grain
_M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
_WHITE = np.array([0.95047, 1.0, 1.08883])


def srgb_to_lab(rgb):
    c = np.clip(np.asarray(rgb, float), 0, 1)
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    t = (c @ _M.T) / _WHITE
    d = 6 / 29; ft = np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4 / 29)
    return np.stack([116 * ft[..., 1] - 16, 500 * (ft[..., 0] - ft[..., 1]), 200 * (ft[..., 1] - ft[..., 2])], -1)


def lab_to_srgb(lab):
    lab = np.asarray(lab, float); fy = (lab[..., 0] + 16) / 116; fx = fy + lab[..., 1] / 500; fz = fy - lab[..., 2] / 200
    d = 6 / 29; ft = np.stack([fx, fy, fz], -1)
    t = np.where(ft > d, ft ** 3, 3 * d * d * (ft - 4 / 29)) * _WHITE
    c = t @ np.linalg.inv(_M).T
    c = np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055)
    return np.clip(c, 0, 1)


def colour_match(render_rgb, photo_rgb, region_map, min_px=MIN_FACE_PX, de_max=DE_MAX):
    """CIE76 dE between each region's mean L*a*b* in the render and in the photo (same pixels)."""
    lab = np.asarray(region_map); ok = lab >= 0
    ids, cnt = np.unique(lab[ok], return_counts=True); ids = ids[cnt >= min_px]; cnt = cnt[cnt >= min_px]
    if len(ids) == 0:
        return {"pass": False, "reason": "no region"}
    Lr, Lp = srgb_to_lab(render_rgb), srgb_to_lab(photo_rgb)
    mr = np.stack([ndimage.mean(Lr[..., k], lab, ids) for k in range(3)], 1)
    mp = np.stack([ndimage.mean(Lp[..., k], lab, ids) for k in range(3)], 1)
    de = np.linalg.norm(mr - mp, axis=1); w = int(np.argmax(de))
    return {"regions": int(len(ids)), "dE_max": round(float(de.max()), 3), "dE_mean_area_weighted": round(float((de * cnt).sum() / cnt.sum()), 3),
            "worst_region": int(ids[w]), "worst_dLab": np.round(mr[w] - mp[w], 2).tolist(), "pass": bool(de.max() <= de_max)}


SIGMAS = np.geomspace(0.6, 12.0, 28)


def grain_spectrum(lum, mask, label_map=None, sigmas=SIGMAS, margin=3.0, min_valid=500):
    """scale-normalised LoG energy E(sigma) = mean (sigma^2 LoG_sigma * I)^2 over pixels further than margin*sigma
    from the mask edge and from any label change (so shading steps at face edges never count). A blob of radius rho
    peaks at sigma = rho / sqrt(2). Returns sigmas, E, peak sigma (log-parabolic, interior maxima only) or None."""
    m = np.asarray(mask, bool)
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        return dict(sigmas=sigmas.tolist(), E=[], peak=None)
    pad = int(np.ceil(margin * sigmas.max())) + 4
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, m.shape[0]); x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, m.shape[1])
    I = np.asarray(lum, float)[y0:y1, x0:x1]; mm = m[y0:y1, x0:x1]
    bnd = ~mm
    if label_map is not None:
        L = np.asarray(label_map)[y0:y1, x0:x1]
        bnd = bnd | (L != np.roll(L, 1, 0)) | (L != np.roll(L, 1, 1))
    dist = ndimage.distance_transform_edt(~bnd)
    I = np.where(mm, I, I[mm].mean())
    E = []
    for s in sigmas:
        val = dist > margin * s
        if val.sum() < min_valid:
            E.append(np.nan); continue
        r = ndimage.gaussian_laplace(I, s) * s * s
        E.append(float(np.mean(r[val] ** 2)))
    E = np.asarray(E); ls = np.log(sigmas); peak = None
    good = np.isfinite(E)
    cand = [i for i in range(1, len(E) - 1) if good[i - 1] and good[i] and good[i + 1] and E[i] > E[i - 1] and E[i] >= E[i + 1]]
    if cand:
        i = max(cand, key=lambda k: E[k])
        y = np.log(E[i - 1:i + 2]); den = y[0] - 2 * y[1] + y[2]
        off = 0.5 * (y[0] - y[2]) / den if den != 0 else 0.0
        peak = float(np.exp(ls[i] + np.clip(off, -1, 1) * (ls[1] - ls[0])))
    return dict(sigmas=np.round(sigmas, 4).tolist(), E=[None if not np.isfinite(e) else float(e) for e in E], peak=peak)


def grain_match(render_lum, photo_lum, mask, label_map=None, size_tol=GRAIN_SIZE_TOL, amp=GRAIN_AMP):
    """both spectra on the SAME pixels (the photo's mask and labels). PASS = both have an interior peak, the peak
    scales agree within size_tol, and the render's grain amplitude at the photo's peak is within amp x the photo's."""
    sp = grain_spectrum(photo_lum, mask, label_map); sr = grain_spectrum(render_lum, mask, label_map)
    out = {"photo_peak_sigma_px": sp["peak"], "render_peak_sigma_px": sr["peak"]}
    if sp["peak"] is None:
        out.update({"pass": False, "reason": "no grain peak in the photo"}); return out
    Ep = np.array([np.nan if e is None else e for e in sp["E"]]); Er = np.array([np.nan if e is None else e for e in sr["E"]])
    ls = np.log(SIGMAS); g = np.isfinite(Ep) & np.isfinite(Er)
    a = float(np.sqrt(np.interp(np.log(sp["peak"]), ls[g], Er[g]) / np.interp(np.log(sp["peak"]), ls[g], Ep[g])))
    ratio = (sr["peak"] / sp["peak"]) if sr["peak"] else None
    ok_s = ratio is not None and abs(ratio - 1) <= size_tol; ok_a = amp[0] <= a <= amp[1]
    out.update({"size_ratio": None if ratio is None else round(ratio, 4), "amplitude_ratio": round(a, 4),
                "pass_size": bool(ok_s), "pass_amplitude": bool(ok_a), "pass": bool(ok_s and ok_a)})
    return out


# =====================================================================  R5 solid and ground
def solid_integrity(v, f, check_self_intersection=True):
    """reuses engine/checks/skin_checks.skin_integrity (A16), unchanged"""
    from skin_checks import skin_integrity
    r = skin_integrity(np.asarray(v, float), np.asarray(f, np.int64), check_self_intersection=check_self_intersection, quiet=True)
    keys = ("open_edges", "nonmanifold_edges", "pinched_vertices", "orientation_flips", "shells", "repeated_index_faces",
            "signed_volume_cm3", "selfint_pairs", "pass")
    return {k: r.get(k) for k in keys}


def surface_samples(v, f, n, seed=0):
    """area-weighted random points: P (n,3), face index, outward unit normal"""
    rng = np.random.default_rng(seed); v = np.asarray(v, float); f = np.asarray(f, np.int64)
    a = 0.5 * np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1)
    fi = rng.choice(len(f), n, p=a / a.sum())
    r1, r2 = rng.random(n), rng.random(n); s = np.sqrt(r1)
    P = (1 - s)[:, None] * v[f[fi, 0]] + (s * (1 - r2))[:, None] * v[f[fi, 1]] + (s * r2)[:, None] * v[f[fi, 2]]
    return P, fi, face_normals(v, f)[fi], float(a.sum())


def visible_samples(v, f, cam, P, fi, rast=None, tol_frac=1e-3):
    """a sample is visible when its face is front-facing and it is the front-most surface at its pixel"""
    if rast is None:
        rast = rasterize(v, f, cam)
    uvz = cam.project(P); c = np.floor(uvz[:, 0]).astype(int); r = np.floor(uvz[:, 1]).astype(int)
    inn = (c >= 0) & (c < cam.W) & (r >= 0) & (r < cam.H)
    z = np.full(len(P), np.inf); z[inn] = rast["zfront"][r[inn], c[inn]]
    tol = tol_frac * float(np.median(uvz[:, 2]))
    return inn & rast["front_facing"][fi] & (uvz[:, 2] <= z + tol)


def ground_contact(v, f, cam, shadow_mask, ground_z=0.0, tol=GROUND_TOL, band=CONTACT_BAND, near_px=CONTACT_NEAR_PX,
                   min_prec=CONTACT_PREC, min_rec=CONTACT_REC, n=20000, seed=0):
    """floating / sinking from the lowest point; WHERE from the visible near-ground band against the photo's contact-
    shadow mask (H,W bool, the shadow core next to the object). n samples go on the triangles that reach into the
    band only (proof v1 sampled the whole surface: 72 contact points, recall 0.78 on the truth)."""
    v = np.asarray(v, float); f = np.asarray(f, np.int64)
    lift = float(v[np.unique(f), 2].min() - ground_z)
    top = ground_z + max(lift, 0) + band
    low = np.flatnonzero(v[f].min(1)[:, 2] <= top)                    # triangles reaching into the band
    P, fl, N, _ = surface_samples(v, f[low], n, seed); fi = low[fl]
    near = P[:, 2] <= top
    rast = rasterize(v, f, cam); vis = visible_samples(v, f, cam, P, fi, rast)
    sel = near & vis; uv = cam.project(P[sel])[:, :2]
    sm = np.asarray(shadow_mask, bool)
    res = {"lift_mm": round(lift * 1000, 3), "floating": bool(lift > tol), "sinking": bool(lift < -tol), "contact_points": int(sel.sum())}
    if sel.sum() < 10 or not sm.any():
        res.update({"precision": 0.0, "recall": 0.0, "pass_place": False})
    else:
        c = np.clip(np.floor(uv).astype(int), 0, [cam.W - 1, cam.H - 1])
        dsh = ndimage.distance_transform_edt(~sm)
        prec = float((dsh[c[:, 1], c[:, 0]] <= near_px).mean())
        cm = np.zeros_like(sm); cm[c[:, 1], c[:, 0]] = True
        rec = float((ndimage.distance_transform_edt(~cm)[sm] <= near_px).mean())
        res.update({"precision": round(prec, 4), "recall": round(rec, 4), "pass_place": bool(prec >= min_prec and rec >= min_rec)})
    res["pass_height"] = bool(not res["floating"] and not res["sinking"])
    res["pass"] = bool(res["pass_height"] and res["pass_place"])
    return res


# =====================================================================  R6 thickness and mirror
def ray_first_hit(v, f, O, D, skip=None, tmin=1e-7, chunk=1_500_000):
    """distance along unit D from O to the first triangle (Moller-Trumbore, brute force in chunks; ~2e7 tests/s).
    skip: per-ray triangle id to ignore (the ray's own face). inf = no hit."""
    v = np.asarray(v, float); f = np.asarray(f, np.int64)
    A = v[f[:, 0]]; E1 = v[f[:, 1]] - A; E2 = v[f[:, 2]] - A
    out = np.full(len(O), np.inf); per = max(1, chunk // len(f))
    for s in range(0, len(O), per):
        o = O[s:s + per, None, :]; d = D[s:s + per, None, :]
        h = np.cross(d, E2[None]); a = np.einsum("ijk,jk->ij", h, E1)
        ok = np.abs(a) > 1e-14; a = np.where(ok, a, 1.0)
        sv = o - A[None]; u = np.einsum("ijk,ijk->ij", sv, h) / a
        q = np.cross(sv, E1[None]); w = np.einsum("ijk,ijk->ij", d, q) / a
        t = np.einsum("ijk,jk->ij", q, E2) / a
        hit = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > tmin)
        if skip is not None:
            hit[np.arange(hit.shape[0]), skip[s:s + per]] = False
        out[s:s + per] = np.where(hit, t, np.inf).min(1)
    return out


def thickness_check(v, f, cam, n=8000, seed=0, thin_frac=THIN_FRAC, area_max=THIN_AREA_MAX):
    """inward-normal ray thickness of each surface sample (the thickness MAP: per sample, also per face min).
    Reference = the visible depth: p99 - p1 of the camera depth of the samples the photo camera sees."""
    v = np.asarray(v, float); f = np.asarray(f, np.int64)
    P, fi, N, area = surface_samples(v, f, n, seed)
    L = float(np.ptp(v, 0).max())
    t = ray_first_hit(v, f, P - 1e-7 * L * N, -N, skip=fi)
    vis = visible_samples(v, f, cam, P, fi)
    z = cam.project(P[vis])[:, 2]; dvis = float(np.percentile(z, 99) - np.percentile(z, 1))
    thin = t < thin_frac * dvis
    per_face = np.full(len(f), np.nan); np.fmin.at(per_face, fi, np.where(np.isfinite(t), t, np.nan))
    return {"visible_depth_m": round(dvis, 4), "thin_limit_m": round(thin_frac * dvis, 4),
            "thin_frac_all": round(float(thin.mean()), 4), "thin_frac_back": round(float(thin[~vis].mean()) if (~vis).any() else 0.0, 4),
            "thin_frac_front": round(float(thin[vis].mean()) if vis.any() else 0.0, 4),
            "thickness_p1_m": round(float(np.percentile(t[np.isfinite(t)], 1)), 4), "no_hit": int((~np.isfinite(t)).sum()),
            "thin_sites": [[round(x, 3) for x in p] for p in P[thin][:5].tolist()],
            "pass": bool(thin.mean() <= area_max)}, dict(P=P, t=t, vis=vis, per_face=per_face)


def _kabsch(X, Y):
    mx, my = X.mean(0), Y.mean(0); U, _, Vt = np.linalg.svd((X - mx).T @ (Y - my))
    d = np.sign(np.linalg.det(Vt.T @ U.T)); Rk = Vt.T @ np.diag([1, 1, d]) @ U.T
    return Rk, my - Rk @ mx


def mirror_similarity(v, f, cam, n=20000, seed=0, eps=MIRROR_EPS, ang=MIRROR_ANG, max_score=MIRROR_MAX, iters=25):
    """is the unseen back a mirror copy of the visible front? Starts: reflection across planes normal to the camera
    axis, its horizontal part and the camera's right axis, each with 0/90/180/270 deg turns about that normal; each is
    refined by trimmed ICP (improper isometry), then polished point-to-plane on the pairs whose normals agree (proof v2:
    plain ICP left an exact copy ~3 mm off, scoring 0.59). Score = of the back samples that land on the front (within 3 sample
    spacings), the fraction that lie ON it (point-to-plane < eps*size) with matching normals (< ang deg); the
    denominator is at least 20 % of the back. Best score over starts (yaw -14..14 deg about z for the horizontal axis).
    Proof v1 scored over ALL back samples: an exact mirror copy scored only 0.35 because the unseen underside has no
    visible counterpart."""
    v = np.asarray(v, float); f = np.asarray(f, np.int64)
    P, fi, N, area = surface_samples(v, f, n, seed)
    vis = visible_samples(v, f, cam, P, fi)
    Pv, Nv, Pb, Nb = P[vis], N[vis], P[~vis], N[~vis]
    if len(Pb) < 50 or len(Pv) < 50:
        return {"pass": True, "score": 0.0, "note": "too few back or front samples"}
    L = float(np.ptp(v, 0).max()); sp = np.sqrt(area / n); tree = cKDTree(Pv); c = P.mean(0)
    fw = cam.forward; fh = fw.copy(); fh[2] = 0; fh = fh / max(np.linalg.norm(fh), 1e-12)
    best = (-1.0, None)
    starts = [fw, cam.R[0]]
    for yaw in (-14, -7, 0, 7, 14):
        y = np.radians(yaw); starts.append(np.array([[np.cos(y), -np.sin(y), 0], [np.sin(y), np.cos(y), 0], [0, 0, 1]]) @ fh)
    for a in starts:
        a = a / np.linalg.norm(a); M = np.eye(3) - 2 * np.outer(a, a)
        for phi in (0, 90, 180, 270):
            th = np.radians(phi); K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
            Rphi = np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K
            A = Rphi @ M; t = c - A @ c
            for _ in range(iters):
                q = Pb @ A.T + t; d, j = tree.query(q)
                keep = d < 0.05 * L
                if keep.sum() < 20:
                    break
                Rk, tk = _kabsch(q[keep], Pv[j[keep]]); A = Rk @ A; t = Rk @ t + tk
                if np.linalg.norm(Rk - np.eye(3)) < 1e-7 and np.linalg.norm(tk) < 1e-9:
                    break
            for _ in range(12):                                        # point-to-plane polish on normal-agreeing pairs
                q = Pb @ A.T + t; m = Nb @ A.T; d, j = tree.query(q)
                inl = (d < 3 * sp) & (np.einsum("ij,ij->i", m, Nv[j]) > np.cos(np.radians(ang)))
                if inl.sum() < 20:
                    break
                qi, pj, nj = q[inl], Pv[j[inl]], Nv[j[inl]]
                Rk, tk = _kabsch(qi, qi - np.einsum("ij,ij->i", qi - pj, nj)[:, None] * nj); A = Rk @ A; t = Rk @ t + tk
            q = Pb @ A.T + t; m = Nb @ A.T; d, j = tree.query(q)
            pd = np.abs(np.einsum("ij,ij->i", q - Pv[j], Nv[j])); cosn = np.einsum("ij,ij->i", m, Nv[j])
            over = d < 3 * sp                                          # back samples that land on the front at all
            match = over & (pd < eps * L) & (cosn > np.cos(np.radians(ang)))
            s = float(match.sum() / max(over.sum(), 0.2 * len(Pb)))
            if s > best[0]:
                best = (s, dict(axis=np.round(a, 3).tolist(), turn_deg=phi, det=round(float(np.linalg.det(A)), 3)))
    return {"score": round(best[0], 4), "best_start": best[1], "back_samples": int(len(Pb)), "front_samples": int(len(Pv)),
            "pass": bool(best[0] <= max_score)}


# =====================================================================  decisions
def no_armature(inventory):
    """inventory: list of {name, type, modifiers: [type], parent_type, constraints: [type]} for EVERY object of the asset"""
    bad = []
    for o in inventory:
        if str(o.get("type", "")).upper() == "ARMATURE":
            bad.append((o["name"], "armature object"))
        if any(str(m).upper() == "ARMATURE" for m in o.get("modifiers", [])):
            bad.append((o["name"], "armature modifier"))
        if str(o.get("parent_type") or "").upper() == "ARMATURE":
            bad.append((o["name"], "parented to an armature"))
        if any(str(c).upper() == "ARMATURE" for c in o.get("constraints", [])):
            bad.append((o["name"], "armature constraint"))
    return {"objects": len(inventory), "rigging": bad, "pass": bool(len(inventory) > 0 and not bad)}


def horizontal_extent(v, target=EXTENT_TARGET, tol=EXTENT_TOL):
    """largest horizontal extent = max Feret diameter of the xy projection (not the axis-aligned box)"""
    xy = np.asarray(v, float)[:, :2]; h = xy[ConvexHull(xy).vertices]
    D = np.linalg.norm(h[:, None] - h[None], axis=2); i, j = np.unravel_index(np.argmax(D), D.shape)
    ext = float(D[i, j]); d = h[j] - h[i]
    return {"extent_m": round(ext, 5), "target_m": target, "rel_err": round(ext / target - 1, 5),
            "direction_deg": round(float(np.degrees(np.arctan2(d[1], d[0]))) % 180, 2),
            "bbox_x_m": round(float(np.ptp(xy[:, 0])), 5), "bbox_y_m": round(float(np.ptp(xy[:, 1])), 5),
            "pass": bool(abs(ext / target - 1) <= tol)}


# =====================================================================  Blender-side collectors (run inside Blender)
def bpy_inventory(collection_name):
    """every object in the collection and its child collections, as plain data for no_armature()"""
    import bpy
    col = bpy.data.collections[collection_name]
    out = []
    for o in col.all_objects:
        out.append({"name": o.name, "type": o.type, "modifiers": [m.type for m in o.modifiers],
                    "parent_type": o.parent.type if o.parent else None, "constraints": [c.type for c in o.constraints]})
    return out


def bpy_world_mesh(collection_name):
    """evaluated (modifiers applied) world-space triangles of every mesh in the collection, merged: (v, f)"""
    import bpy
    dg = bpy.context.evaluated_depsgraph_get(); V, F, off = [], [], 0
    for o in bpy.data.collections[collection_name].all_objects:
        if o.type != "MESH":
            continue
        e = o.evaluated_get(dg); me = e.to_mesh(); me.calc_loop_triangles()
        mw = np.array(o.matrix_world)
        co = np.array([x.co for x in me.vertices], float); co = co @ mw[:3, :3].T + mw[:3, 3]
        tri = np.array([t.vertices for t in me.loop_triangles], np.int64)
        V.append(co); F.append(tri + off); off += len(co); e.to_mesh_clear()
    return (np.vstack(V), np.vstack(F)) if V else (np.zeros((0, 3)), np.zeros((0, 3), np.int64))
