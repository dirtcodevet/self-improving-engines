"""Compare traced features: photo vs model (both traced by trace_photo.py from the same camera/frame/resolution).
Shape descriptors per feature, photo value, model value, difference, verdict vs a tolerance; plus a green (photo)
/ red (model) contour overlay on the photo. Every line of the table is a finding the reviewer can act on.
usage: python compare_features.py <case_dir> <model_features_name> [out_prefix]
"""
import json
import os
import sys

import cv2
import numpy as np

case, mname = sys.argv[1], sys.argv[2]
outp = sys.argv[3] if len(sys.argv) > 3 else os.path.join(case, "review", mname + "_vs_photo")
A = json.load(open(os.path.join(case, "review", "photo_features.json")))["features"]
B = json.load(open(os.path.join(case, "review", mname + ".json")))["features"]


def shape(pts):
    a = np.array(pts, float)
    if len(a) < 5:
        return None
    m = cv2.moments(a.astype(np.float32))
    area = abs(cv2.contourArea(a.astype(np.float32)))
    per = cv2.arcLength(a.astype(np.float32), True)
    cx, cy = (m["m10"] / m["m00"], m["m01"] / m["m00"]) if m["m00"] else a.mean(0)
    w, h = np.ptp(a[:, 0]) + 1, np.ptp(a[:, 1]) + 1
    c = np.cov((a - a.mean(0)).T); ev, evec = np.linalg.eigh(c)
    ang = np.degrees(np.arctan2(evec[1, 1], evec[0, 1]))
    ang = (ang + 90) % 180 - 90
    return {"cx": cx, "cy": cy, "w": w, "h": h, "area": area, "aspect": w / h, "tilt_deg": ang,
            "circularity": 4 * np.pi * area / max(per * per, 1e-9)}


def iou(pa, pb, H=1152, W=1728):
    ma, mb = np.zeros((H, W), np.uint8), np.zeros((H, W), np.uint8)
    cv2.fillPoly(ma, [np.array(pa, np.int32)], 1); cv2.fillPoly(mb, [np.array(pb, np.int32)], 1)
    return float((ma & mb).sum() / max((ma | mb).sum(), 1))


def mouth_desc(pts):
    a = np.array(pts, float)
    if len(a) < 5:
        return None
    xl, xr = a[:, 0].min(), a[:, 0].max()
    cx = np.median(a[:, 0])
    stem = a[np.abs(a[:, 0] - cx) < 3]
    top = stem[:, 1].min() if len(stem) else a[:, 1].min()
    junction_y = stem[:, 1].max() if len(stem) else a[:, 1].mean()
    left = a[a[:, 0] < cx - 4]; right = a[a[:, 0] > cx + 4]

    def branch(pp):
        if len(pp) < 3:
            return np.nan
        k = np.polyfit(pp[:, 0], pp[:, 1], 1)[0]
        return np.degrees(np.arctan(abs(k)))
    return {"width": xr - xl, "philtrum": junction_y - top, "droop_L_deg": branch(left), "droop_R_deg": branch(right),
            "corner_drop": float(np.mean([a[a[:, 0] == xl][:, 1].mean(), a[a[:, 0] == xr][:, 1].mean()]) - junction_y)}


def head_desc(pts):
    a = np.array(pts, float)
    if len(a) < 20:
        return None
    n = len(a); mid = a[int(0.3 * n): int(0.7 * n)]
    ys = mid[:, 1]
    # dome: how far the middle rises above the ear-base valleys (ear bases = lowest points of the outline in the
    # 15-40 % and 60-85 % stretches); flatness = residual of a parabola over the middle third
    lb = a[int(0.12 * n): int(0.45 * n)]; rb = a[int(0.55 * n): int(0.88 * n)]
    yl, yr = lb[:, 1].max(), rb[:, 1].max()
    dome = (yl + yr) / 2 - ys.min()
    k = np.polyfit(mid[:, 0], mid[:, 1], 2)[0]
    return {"ear_base_gap": float(rb[np.argmax(rb[:, 1]), 0] - lb[np.argmax(lb[:, 1]), 0]), "dome_height": float(dome),
            "dome_curv_x1000": float(k * 1000)}


rows = []


def add(feat, key, pa, pb, tol, unit="", rel=True):
    if pa is None or pb is None:
        rows.append((feat, key, pa, pb, None, "missing"))
        return
    d = (pb - pa) / abs(pa) if rel and abs(pa) > 1e-9 else pb - pa
    ok = abs(d) <= tol
    rows.append((feat, key, pa, pb, d, "ok" if ok else "OFF"))


for f in ("eye.R", "eye.L", "iris.R", "iris.L", "pupil.R", "pupil.L", "nose", "nostril.R", "nostril.L", "ear_in.R", "ear_in.L"):
    sa = shape(A.get(f, [])) if A.get(f) else None
    sb = shape(B.get(f, [])) if B.get(f) else None
    if sa is None or sb is None:
        rows.append((f, "trace", None if sa is None else "ok", None if sb is None else "ok", None, "missing"))
        continue
    add(f, "width px", sa["w"], sb["w"], 0.12)
    add(f, "height px", sa["h"], sb["h"], 0.12)
    add(f, "aspect w/h", sa["aspect"], sb["aspect"], 0.12)
    add(f, "centre x px", sa["cx"], sb["cx"], 6, rel=False)
    add(f, "centre y px", sa["cy"], sb["cy"], 6, rel=False)
    if f.startswith(("eye", "nose")) and max(sa["aspect"], 1 / sa["aspect"]) > 1.15 and max(sb["aspect"], 1 / sb["aspect"]) > 1.15:
        add(f, "tilt deg", sa["tilt_deg"], sb["tilt_deg"], 6, rel=False)   # tilt is undefined for near-round shapes
        add(f, "circularity", sa["circularity"], sb["circularity"], 0.1)
    rows.append((f, "overlap IoU", None, round(iou(A[f], B[f]), 3), None, "ok" if iou(A[f], B[f]) > 0.7 else "OFF"))
ma, mb = mouth_desc(A.get("mouth", [])), mouth_desc(B.get("mouth", []))
if ma and mb:
    for k, tol, rel in (("width", 0.12, True), ("philtrum", 0.2, True), ("droop_L_deg", 6, False), ("droop_R_deg", 6, False),
                        ("corner_drop", 4, False)):
        add("mouth", k, ma[k], mb[k], tol, rel=rel)
ha, hb = head_desc(A.get("head_top", [])), head_desc(B.get("head_top", []))
if ha and hb:
    for k, tol, rel in (("ear_base_gap", 0.08, True), ("dome_height", 0.2, True), ("dome_curv_x1000", 0.3, True)):
        add("head_top", k, ha[k], hb[k], tol, rel=rel)

off = [r for r in rows if r[5] != "ok"]
lines = [f"{'feature':10s} {'measure':16s} {'photo':>9s} {'model':>9s} {'diff':>8s}  verdict"]
for f, k, pa, pb, d, v in rows:
    fmt = lambda x: (f"{x:9.2f}" if isinstance(x, (float, np.floating)) else f"{str(x):>9s}")
    ds = "" if d is None else (f"{d*100:+7.0f}%" if abs(d) < 5 and k not in ("centre x px", "centre y px", "tilt deg", "droop_L_deg", "droop_R_deg", "corner_drop") else f"{d:+8.1f}")
    lines.append(f"{f:10s} {k:16s} {fmt(pa)} {fmt(pb)} {ds:>8s}  {v}")
txt = "\n".join(lines) + f"\n\n{len(off)} of {len(rows)} measurements OFF or missing"
open(outp + ".txt", "w").write(txt)
print(txt)
# overlay: photo with green (photo) and red (model) contours, face crop x2.5
img = cv2.imread(os.path.join(case, "ref.jpg"))
for feats, col in ((A, (60, 220, 60)), (B, (40, 40, 255))):
    for k, pts in feats.items():
        if not pts or k.startswith("iris_circle"):
            continue
        a = np.array(pts, np.int32)
        if k in ("mouth", "head_top"):
            for p_ in a:
                cv2.circle(img, tuple(int(t) for t in p_), 1, col, -1)
        else:
            cv2.polylines(img, [a], True, col, 1, cv2.LINE_AA)
crop = cv2.resize(img[100:470, 540:880], None, fx=2.5, fy=2.5, interpolation=cv2.INTER_NEAREST)
cv2.imwrite(outp + ".png", crop)
