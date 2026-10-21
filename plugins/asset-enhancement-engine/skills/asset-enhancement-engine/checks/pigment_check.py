"""C7 PIGMENT CHECK (Phase 2, checksB 2026-10-18): a render of the model from the FROZEN camera (same frame and size
as cases/<case>/ref.jpg) against the photo.
1. REGION COLOUR: the regions of review/compare_regions.py (boxes placed from ref_points.json by the inter-ocular
   distance, polygons from review/photo_features.json; boxes clipped to ref_mask.png) - copied, not imported, because
   compare_regions.py runs on import and scores CIE76. Per region: mean CIELAB (D65, skimage) of each image and the
   CIEDE2000 difference of the means. PASS dE00 <= 3.0. Reason: dE00 ~1 is a just-noticeable difference for
   side-by-side patches and 2-3 is visible only on close comparison; 3.0 leaves room for fur sheen / render noise but
   a 5-unit shift (the planted failure) must fail with margin.
2. MARKING-EDGE CRISPNESS: the colour-point boundary is found ON THE PHOTO in a PIGMENT coordinate, a*b* projected on
   the axis body colour -> marking colour (photo_markings.json MARK_RGB): shading moves L* and hardly this (cat1:
   markings 16.5 units out, the darkest-20 % shading 2.6). Smoothed (sigma 1.5 px), Otsu split of the cat mask (eroded
   6 px: no silhouette edges) into marked / unmarked, boundary pixels kept where the gradient is in the top 30 % and away (10 px) from the eyes, nose, mouth and inner
   ears (features, not markings). At up to 400 boundary samples a 25-px L* profile is read ACROSS the edge (gradient
   direction) of the pigment coordinate, averaged over 5 lines along the edge (fur noise), on BOTH images at the same
   pixels. Width = 10-90 % rise between the profile's own plateaus (3 end samples each side). Profiles whose photo
   contrast < 30 % of the body-to-marking distance are dropped; a render profile with < 50 % of the photo's contrast counts as width 25 (edge missing).
   Result: the EXTRA BLUR of ours over the photo, sigma_x = sqrt(max(w_ours^2 - w_photo^2, 0)) / 2.563 px
   (a Gaussian of sigma s has a 10-90 % width of 2.563 s, and widths add in quadrature).
   PASS sigma_x <= 1.5 px. Reason: 1.5 px at ~0.27 mm/px = 0.4 mm, inside the +-0.5 mm position tolerance and
   above the ~0.5-1 px softening of render resampling; the planted 3 px blur must fail.
usage: python pigment_check.py <case_dir> <render.png> [out.json]
"""
import json
import os
import sys

import cv2
import numpy as np
from scipy.ndimage import map_coordinates
from skimage.color import deltaE_ciede2000, rgb2lab

DE_MARK, SIG_MARK = 3.0, 1.5


def load_case(case):
    """points, features, photo, mask, and the MARKING AXIS: body colour (median a*b* of the brightest 30 % of the mask)
    -> marking colour (photo_markings.json MARK_RGB, measured on the photo's stripes)"""
    P = json.load(open(os.path.join(case, "ref_points.json")))["points"]
    F = json.load(open(os.path.join(case, "review", "photo_features.json")))["features"]
    photo = cv2.imread(os.path.join(case, "ref.jpg")); mask = cv2.imread(os.path.join(case, "ref_mask.png"), 0) > 127
    return P, F, photo, mask


def marking_axis(case, photo, mask):
    M = json.load(open(os.path.join(case, "photo_markings.json"))); A = lab(photo)
    body = np.median(A[mask & (A[..., 0] > np.percentile(A[..., 0][mask], 70))][:, 1:], 0)
    mk = rgb2lab(np.array([[M["MARK_RGB"]]], float))[0, 0, 1:]; d = mk - body
    return body, d / np.linalg.norm(d), float(np.linalg.norm(d))


def mark_index(img, axis):
    """pigment coordinate: a*b* projected on body -> marking (shading moves L*, hardly this)"""
    body, d, _ = axis; A = lab(img); return (A[..., 1] - body[0]) * d[0] + (A[..., 2] - body[1]) * d[1]


def regions(P, F, mask, scale=1.0):
    """compare_regions.py's layout (boxes x scale), as boolean masks"""
    eR, eL, nose, chin = (np.array(P[k], float) for k in ("eye.R", "eye.L", "nose", "chin")); iod = eL[0] - eR[0]
    H, W = mask.shape

    def box(cx, cy, w, h):
        w, h = w * scale, h * scale; return int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2)
    B = {"forehead": box((eR[0] + eL[0]) / 2, eR[1] - 0.75 * iod, 1.1 * iod, 0.55 * iod),
         "cheek.R": box(eR[0] - 0.25 * iod, eR[1] + 0.55 * iod, 0.45 * iod, 0.4 * iod),
         "cheek.L": box(eL[0] + 0.25 * iod, eL[1] + 0.55 * iod, 0.45 * iod, 0.4 * iod),
         "muzzle.R": box(nose[0] - 0.3 * iod, nose[1] + 0.25 * iod, 0.3 * iod, 0.3 * iod),
         "muzzle.L": box(nose[0] + 0.3 * iod, nose[1] + 0.25 * iod, 0.3 * iod, 0.3 * iod),
         "chin": box(chin[0], chin[1] + 0.2 * iod, 0.4 * iod, 0.25 * iod),
         "chest": box(nose[0] + 0.1 * iod, chin[1] + 1.6 * iod, 1.2 * iod, 0.9 * iod),
         "leg.fR": box(P["fpaw.R"][0], P["fpaw.R"][1] - 1.2 * iod, 0.35 * iod, 0.8 * iod),
         "leg.fL": box(P["fpaw.L"][0], P["fpaw.L"][1] - 1.2 * iod, 0.35 * iod, 0.8 * iod)}
    out = {}
    for k, (x0, y0, x1, y1) in B.items():
        s = np.zeros((H, W), bool); s[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)] = True; s &= mask
        if s.sum() >= 30: out[k] = s
    for k in ("nose", "ear_in.R", "ear_in.L"):
        if F.get(k):
            m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.array(F[k], np.int32)], 1)
            if m.sum() >= 30: out["nose_leather" if k == "nose" else k] = m > 0
    return out


def lab(img_bgr):
    return rgb2lab(img_bgr[..., ::-1].astype(np.float64) / 255.0)


def region_colour(photo, render, R, mark=DE_MARK):
    A, B = lab(photo), lab(render); rows = {}
    for k, s in R.items():
        a, b = A[s].mean(0), B[s].mean(0); dE = float(deltaE_ciede2000(a[None], b[None])[0])
        rows[k] = {"photo_lab": np.round(a, 2).tolist(), "model_lab": np.round(b, 2).tolist(), "dE00": round(dE, 3), "status": "PASS" if dE <= mark else "FAIL"}
    return rows


def edge_samples(photo, mask, F, axis, strength_pct=70, nmax=400, erode=6, feat_pad=10):
    L = mark_index(photo, axis); Ls = cv2.GaussianBlur(L, (0, 0), 1.5)
    m = cv2.erode(mask.astype(np.uint8), np.ones((2 * erode + 1, 2 * erode + 1), np.uint8)) > 0
    feat = np.zeros(mask.shape, np.uint8)
    for k in ("eye.R", "eye.L", "iris.R", "iris.L", "nose", "nostril.R", "nostril.L", "mouth", "ear_in.R", "ear_in.L"):
        if F.get(k): cv2.fillPoly(feat, [np.array(F[k], np.int32)], 1)
    feat = cv2.dilate(feat, np.ones((2 * feat_pad + 1, 2 * feat_pad + 1), np.uint8)) > 0
    sc = 255.0 / max(axis[2] * 1.5, 1e-9); v = Ls[m]; thr, _ = cv2.threshold(np.clip(v * sc, 0, 255).astype(np.uint8).reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = (Ls * sc > thr) & m                               # the MARKED side
    bnd = (cv2.dilate(dark.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) & ~dark & m & ~feat
    gx, gy = cv2.Sobel(Ls, cv2.CV_64F, 1, 0, ksize=3) / 8, cv2.Sobel(Ls, cv2.CV_64F, 0, 1, ksize=3) / 8; g = np.hypot(gx, gy)
    ys, xs = np.nonzero(bnd)
    if len(ys) == 0:
        return np.zeros((0, 2)), np.zeros((0, 2)), bnd
    keep = g[ys, xs] >= np.percentile(g[ys, xs], strength_pct); ys, xs = ys[keep], xs[keep]
    step = max(1, len(ys) // nmax); o = np.lexsort((xs, ys))[::step]; ys, xs = ys[o], xs[o]
    nrm = np.c_[gx[ys, xs], gy[ys, xs]]; nrm /= np.maximum(np.linalg.norm(nrm, axis=1), 1e-9)[:, None]
    return np.c_[xs, ys].astype(float), nrm, bnd


def profiles(Limg, pts, nrm, half=12, lines=5):
    s = np.arange(-half, half + 1, dtype=float); tg = np.c_[-nrm[:, 1], nrm[:, 0]]; acc = 0
    for l in np.arange(lines) - lines // 2:
        X = pts[:, None, 0] + s[None] * nrm[:, None, 0] + l * tg[:, None, 0]; Y = pts[:, None, 1] + s[None] * nrm[:, None, 1] + l * tg[:, None, 1]
        acc = acc + map_coordinates(Limg, [Y, X], order=1, mode="nearest")
    return acc / lines


def width_10_90(p):
    lo, hi = p[:3].mean(), p[-3:].mean(); c = hi - lo
    if abs(c) < 1e-9:
        return np.nan, 0.0
    q = (p - lo) / c; n = len(q); mid = n // 2
    i10 = next((i for i in range(mid, 0, -1) if q[i - 1] <= 0.1 < q[i] or q[i] <= 0.1), None)
    i90 = next((i for i in range(mid, n - 1) if q[i] < 0.9 <= q[i + 1] or q[i] >= 0.9), None)
    if i10 is None or i90 is None:
        return np.nan, abs(c)

    def cross(i, lev):                                   # linear position where q crosses lev between i and i+1
        a, b = q[i], q[i + 1]; return i + (lev - a) / (b - a) if b != a else i
    x10 = cross(i10 - 1, 0.1) if q[i10] > 0.1 else float(i10)
    x90 = cross(i90, 0.9) if q[i90] < 0.9 else float(i90)
    return max(x90 - x10, 0.0), abs(c)


def crispness(photo, render, pts, nrm, axis, half=12, mark=SIG_MARK, cfrac=0.3):
    Lp, Lr = mark_index(photo, axis), mark_index(render, axis); cmin = cfrac * axis[2]
    Pp, Pr = profiles(Lp, pts, nrm, half), profiles(Lr, pts, nrm, half); wp, wr = [], []
    for a, b in zip(Pp, Pr):
        w1, c1 = width_10_90(a)
        if not np.isfinite(w1) or c1 < cmin:
            continue
        w2, c2 = width_10_90(b)
        if c2 < 0.5 * c1 or not np.isfinite(w2):
            w2 = 2.0 * half + 1
        wp.append(w1); wr.append(w2)
    if not wp:
        return {"status": "FAIL", "why": "no marking edges found on the photo", "n": 0}
    mp, mr = float(np.median(wp)), float(np.median(wr)); sx = float(np.sqrt(max(mr ** 2 - mp ** 2, 0.0)) / 2.563)
    return {"n": len(wp), "photo_width_px": round(mp, 2), "model_width_px": round(mr, 2), "extra_blur_sigma_px": round(sx, 3),
            "mark_px": mark, "status": "PASS" if sx <= mark else "FAIL"}


def check(case, render, region_scale=1.0, de_mark=DE_MARK, sig_mark=SIG_MARK, half=12, strength_pct=70, photo=None):
    P, F, ph, mask = load_case(case)
    if photo is not None:
        ph = photo
    if render.shape != ph.shape:
        raise SystemExit(f"render {render.shape} is not the frozen-camera frame {ph.shape}")
    R = regions(P, F, mask, region_scale); col = region_colour(ph, render, R, de_mark); ax = marking_axis(case, ph, mask)
    pts, nrm, _ = edge_samples(ph, mask, F, ax, strength_pct); cr = crispness(ph, render, pts, nrm, ax, half, sig_mark)
    ok = all(r["status"] == "PASS" for r in col.values()) and cr["status"] == "PASS"
    return {"status": "PASS" if ok else "FAIL", "regions": col, "crispness": cr}


def main(argv):
    case, rp = argv[0], argv[1]; res = check(case, cv2.imread(rp))
    for k, r in res["regions"].items():
        print(f"{r['status']}  {k:13s} dE00 {r['dE00']:5.2f}   photo {r['photo_lab']}  model {r['model_lab']}")
    c = res["crispness"]; print(f"{c['status']}  marking edges: {c}")
    print(res["status"])
    if len(argv) > 2:
        json.dump(res, open(argv[2], "w"), indent=1)
    return res["status"] != "PASS"


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1:]) else 0)
