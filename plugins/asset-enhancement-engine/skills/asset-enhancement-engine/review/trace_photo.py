"""Precise FEATURE TRACES on the reference photo (builder side; seeded only by the builder's own points
cases/<case>/ref_points.json and its mask - never the eval answer key).
Each feature is traced from its own visual cue, as a closed contour or polyline in photo pixels:
  iris.R/L    blue region around the eye point (HSV), pupil.R/L dark core inside it
  eye.R/L     palpebral opening = the iris + the dark lid margin around it (almond outline)
  nose        pink nose leather (HSV) below the eyes; nostril.R/L = darker slits inside/at its sides
  mouth       dark thin ridge (black-hat) between nose and chin -> skeleton polyline
  head_top    the head's upper outline from the mask between the ears
  ear_in.R/L  pink inner ear
Writes <case>/review/photo_features.json and an overlay PNG to verify every trace by eye.
usage: python trace_photo.py <case_dir> [image] [mask] [out_name]
  default: the reference photo -> review/photo_features.json. The SAME tracer runs on a render from the frozen
  camera (same frame/resolution) so photo and model are measured by one algorithm.
"""
import json
import os
import sys

import cv2
import numpy as np

case = sys.argv[1]
IMG = sys.argv[2] if len(sys.argv) > 2 else os.path.join(case, "ref.jpg")
MASK = sys.argv[3] if len(sys.argv) > 3 else os.path.join(case, "ref_mask.png")
NAME = sys.argv[4] if len(sys.argv) > 4 else "photo_features"
img = cv2.imread(IMG)
H, W = img.shape[:2]
P = json.load(open(os.path.join(case, "ref_points.json")))["points"]
mask = cv2.imread(MASK, cv2.IMREAD_UNCHANGED)
mask = (mask[..., -1] if mask.ndim == 3 else mask) > 127
if mask.shape != (H, W):
    mask = cv2.resize(mask.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
Lc, Ac, Bc = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
out = {"image_size": [W, H], "features": {}}


def biggest(m, seed=None):
    n, lab_, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    if n <= 1:
        return np.zeros_like(m)
    if seed is not None:
        k = lab_[int(seed[1]), int(seed[0])]
        if k > 0:
            return lab_ == k
        d = [np.hypot(*(np.argwhere(lab_ == i).mean(0)[::-1] - seed)) for i in range(1, n)]
        return lab_ == (1 + int(np.argmin(d)))
    return lab_ == (1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])))


def contour(m):
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return max(cs, key=cv2.contourArea)[:, 0, :].tolist() if cs else []


def win(c, rx, ry):
    x0, y0 = int(max(c[0] - rx, 0)), int(max(c[1] - ry, 0))
    return x0, y0, int(min(c[0] + rx, W)), int(min(c[1] + ry, H))


# ---- eyes: iris (blue: Lab b strongly negative), pupil (dark core), opening (iris + dark lid margin)
for s in "RL":
    c = np.array(P[f"eye.{s}"], float)
    x0, y0, x1, y1 = win(c, 60, 45)
    sub_b, sub_L = Bc[y0:y1, x0:x1], Lc[y0:y1, x0:x1]
    iris = biggest(sub_b < -14, c - (x0, y0))
    iris = cv2.morphologyEx(iris.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0
    # iris as a CIRCLE (Hough on the blurred lightness: the blue disc against the dark rim); the opening = pixels
    # inside 1.2 R that are not fur (dark rim or bluish), filled. v1/v2: colour blobs leaked into the periocular
    # stripes or lost the upper iris (pupil + highlight break the blue region)
    from scipy.ndimage import binary_fill_holes
    # circle from the FILLED blue disc (pupil/highlight holes filled): centroid + equivalent radius
    sub_a = Ac[y0:y1, x0:x1]   # iris = BLUE (b << 0, a <= 0); lavender markings are violet (a > 0) - v4 leaked into them
    blue = biggest(cv2.morphologyEx(((sub_b < -8) & (sub_a < 3)).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0, c - (x0, y0))
    blue = binary_fill_holes(cv2.morphologyEx(blue.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) > 0)
    hull = cv2.convexHull(np.argwhere(blue)[:, ::-1].astype(np.int32)) if blue.sum() > 50 else None
    if hull is not None:
        hm = np.zeros(blue.shape, np.uint8); cv2.fillConvexPoly(hm, hull, 1)
        (icx, icy), ir = cv2.minEnclosingCircle(hull)
        ir = float(np.sqrt(hm.sum() / np.pi))                  # equivalent radius of the convex blue disc
        icy, icx = np.argwhere(hm > 0).mean(0)
    else:
        icx, icy, ir = c[0] - x0, c[1] - y0, 23.0
    yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0]
    dist = np.hypot(xx - icx, yy - icy)
    fur_L = np.percentile(sub_L[(dist > 1.4 * ir) & (dist < 2.0 * ir)], 70)
    ell = ((xx - icx) / (1.32 * ir)) ** 2 + ((yy - icy) / (1.10 * ir)) ** 2 < 1   # canthi reach sideways, lids hug the iris
    cand_m = ell & ((sub_L < fur_L - 30) | ((sub_b < -8) & (sub_a < 3)))
    opening = biggest(cv2.morphologyEx(cand_m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0, (icx, icy))
    opening = binary_fill_holes(cv2.morphologyEx(opening.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0)
    iris = opening & (dist < ir * 1.02) & ((sub_b < -4) | (sub_L < np.percentile(sub_L[opening], 30)))
    thr = np.percentile(sub_L[iris], 12)
    pupil = biggest(iris & (sub_L <= thr) & (dist < 0.8 * ir), (icx, icy))
    pupil = binary_fill_holes(cv2.morphologyEx(pupil.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0)
    out["features"][f"iris_circle.{s}"] = [float(icx + x0), float(icy + y0), float(ir)]
    for name, m in ((f"iris.{s}", iris), (f"pupil.{s}", pupil), (f"eye.{s}", opening)):
        ct = contour(m)
        out["features"][name] = [[x + x0, y + y0] for x, y in ct]

# ---- nose leather: pink (Lab a high, L mid-high) below and between the eyes
c = np.array(P["nose"], float)
x0, y0, x1, y1 = win(c, 45, 35)
sub_a, sub_L = Ac[y0:y1, x0:x1], Lc[y0:y1, x0:x1]
pink = (sub_a > 9) & (sub_L > 80)
nose = biggest(cv2.morphologyEx(pink.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0, c - (x0, y0))
from scipy.ndimage import binary_fill_holes
nose = binary_fill_holes(cv2.morphologyEx(nose.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0)
# cut the thin pinkish philtrum stem off the leather (v2 leaked down to the lip line): opening wider than the stem
wid = nose.sum(1)                                   # leather = wide top narrowing to a point; the stem stays narrow
if wid.max() > 0:
    r0 = int(np.argmax(wid))
    below = np.nonzero(wid[r0:] < 0.12 * wid.max())[0]
    if len(below):
        nose[r0 + below[0]:] = False
out["features"]["nose"] = [[x + x0, y + y0] for x, y in contour(nose)]
# nostrils: darkest pink-to-dark pixels within the dilated leather, left/right halves
nd = cv2.dilate(nose.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
dk = nd & (sub_L < np.percentile(sub_L[nose], 12))
cx = np.argwhere(nose).mean(0)[1] if nose.any() else (x1 - x0) / 2
for s, side in (("R", lambda xx: xx < cx), ("L", lambda xx: xx >= cx)):
    m = dk.copy(); xs = np.arange(m.shape[1])[None, :].repeat(m.shape[0], 0); m &= side(xs)
    out["features"][f"nostril.{s}"] = [[x + x0, y + y0] for x, y in contour(biggest(m))] if m.any() else []

# ---- mouth line: dark thin ridge between the nose and the chin (black-hat), skeletonised
cN, cC = np.array(P["nose"], float), np.array(P["chin"], float)
x0, y0, x1, y1 = int(cN[0] - 55), int(cN[1] + 2), int(cN[0] + 55), int(cC[1] + 8)
g = Lc[y0:y1, x0:x1]
bh = cv2.morphologyEx(cv2.GaussianBlur(g, (3, 3), 0), cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
ridge = bh > max(np.percentile(bh, 92), 5)
ridge = cv2.morphologyEx(ridge.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
# keep ridge components that start below the leather and are long (the inverted Y: philtrum + two lip branches)
n_, lab_, st_, _ = cv2.connectedComponentsWithStats(ridge.astype(np.uint8), 8)
keep = np.zeros_like(ridge)
for i in range(1, n_):
    if st_[i, cv2.CC_STAT_AREA] >= 25 and st_[i, cv2.CC_STAT_WIDTH] + st_[i, cv2.CC_STAT_HEIGHT] >= 18:
        keep |= lab_ == i
from skimage.morphology import skeletonize
sk = skeletonize(keep)
pts = np.argwhere(sk)
out["features"]["mouth"] = [[int(x + x0), int(y + y0)] for y, x in pts[np.argsort(pts[:, 1])]] if len(pts) else []
# the leather ends where the philtrum (top of the mouth trace, near the midline) begins
if len(pts) and out["features"]["nose"]:
    mid = pts[np.abs(pts[:, 1] + x0 - cN[0]) < 6]
    if len(mid):
        y_cut = int(mid[:, 0].min() + y0)
        nm = np.array(out["features"]["nose"])
        poly = np.zeros((H, W), np.uint8); cv2.fillPoly(poly, [nm.astype(np.int32)], 1)
        poly[y_cut:] = 0
        out["features"]["nose"] = contour(poly > 0)

# ---- head top: the mask's upper outline between the ear bases (columns between the ear tips)
eR, eL = np.array(P["ear_tip.R"]), np.array(P["ear_tip.L"])
cols = np.arange(int(eR[0]), int(eL[0]) + 1)
top = []
for xx in cols:
    ys = np.nonzero(mask[: int(P["eye.R"][1]), xx])[0]
    if len(ys):
        top.append([int(xx), int(ys.min())])
out["features"]["head_top"] = top

# ---- inner ears: pink inside the mask near each ear tip
for s in "RL":
    c = np.array(P[f"ear_tip.{s}"], float) + (0, 70)
    x0, y0, x1, y1 = win(c, 75, 85)
    sub_a, sub_L = Ac[y0:y1, x0:x1], Lc[y0:y1, x0:x1]
    m = (sub_a > 9) & (sub_L > 120) & mask[y0:y1, x0:x1]
    m = biggest(cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0, c - (x0, y0))
    out["features"][f"ear_in.{s}"] = [[x + x0, y + y0] for x, y in contour(m)]

os.makedirs(os.path.join(case, "review"), exist_ok=True)
json.dump(out, open(os.path.join(case, "review", NAME + ".json"), "w"))
# overlay (face crop, 3x) to verify traces by eye
ov = img.copy()
colors = {"iris": (255, 160, 0), "pupil": (0, 255, 255), "eye": (0, 0, 255), "nose": (255, 0, 255), "nostril": (0, 255, 0),
          "mouth": (0, 140, 255), "head_top": (255, 255, 0), "ear_in": (180, 0, 255)}
for k, pts in out["features"].items():
    if not pts or k.startswith("iris_circle"):
        continue
    a = np.array(pts, np.int32)
    col = colors[k.split(".")[0]]
    if k in ("mouth", "head_top"):
        for p_ in a:
            cv2.circle(ov, tuple(int(t) for t in p_), 1, col, -1)
    else:
        cv2.polylines(ov, [a], True, col, 1, cv2.LINE_AA)
x0, y0, x1, y1 = 540, 100, 880, 470
crop = cv2.resize(ov[y0:y1, x0:x1], None, fx=2.5, fy=2.5, interpolation=cv2.INTER_NEAREST)
cv2.imwrite(os.path.join(case, "review", NAME + "_overlay.png"), crop)
print({k: len(v) for k, v in out["features"].items()})
