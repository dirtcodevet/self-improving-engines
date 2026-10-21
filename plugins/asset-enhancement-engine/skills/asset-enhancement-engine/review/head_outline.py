"""Head OUTLINE from the photo camera: photo mask vs model mask (project_mask.py or the Blender probe).
Per side: the outline from the widest cheek point (below the eyes) up to the ear base - its bulge relative to the
chord (+ convex / - concave: the person's "indent above the cheeks"; anatomy: temporalis fills the temporal fossa,
so this line is straight or convex, never concave). Plus head width at the eyes and cheeks, ear-base gap, dome.
usage: python head_outline.py <case_dir> <model_mask.png> [overlay.png]
"""
import json
import os
import sys

import cv2
import numpy as np

P = None


def measure(case, mpath):
    """{'photo': {...}, 'model': {...}} side metrics for the photo mask and a model mask"""
    global P
    P = json.load(open(os.path.join(case, "ref_points.json")))["points"]
    ph = load(os.path.join(case, "ref_mask.png"))
    md = load(mpath, ph.shape)
    out = {}
    for name, m in (("photo", ph), ("model", md)):
        l, r, ey, cx = outline(m)
        out[name] = {"R": side_metrics(l, ey, -1), "L": side_metrics(r, ey, +1),
                     "width_eyes": float(r[ey] - l[ey]) if ey in l else float("nan")}
    return out, ph, md


def load(p, shape=None):
    m = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    m = (m[..., -1] if m.ndim == 3 else m) > 127
    if shape is not None and m.shape != shape:
        m = cv2.resize(m.astype(np.uint8), (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    return m


def outline(m):
    """OUTER outline per row: leftmost / rightmost mask pixel within +-250 px of the face centre (ear outer edges
    above, cheeks below)"""
    eR, eL = np.array(P["eye.R"]), np.array(P["eye.L"])
    ey = int((eR[1] + eL[1]) / 2)
    cx = (eR[0] + eL[0]) / 2
    left, right = {}, {}
    for y in range(int(min(P["ear_tip.R"][1], P["ear_tip.L"][1])), int(P["chin"][1]) + 40):
        xs = np.nonzero(m[y, int(cx - 250): int(cx + 250)])[0]
        if len(xs):
            left[y], right[y] = int(xs.min() + cx - 250), int(xs.max() + cx - 250)
    return left, right, ey, cx


def side_metrics(side, ey, sign):
    ys = np.array(sorted(side)); xs = np.array([side[y] for y in ys], float)
    # widest cheek point: extreme x between eye level and eye level + 90 px
    sel = (ys > ey - 10) & (ys < ey + 55)   # cheekbone band only (v1 +90 px reached the shoulder outline on the side where the body shows)
    if not sel.any():
        return None
    yc = ys[sel][np.argmax(sign * xs[sel])]
    # ear base: the most inward point of the OUTER outline between the ear tip and the cheek (the notch where the
    # ear's outer edge meets the side of the head)
    tip_y = min(P["ear_tip.R"][1], P["ear_tip.L"][1])
    sel2 = (ys > tip_y + 30) & (ys < yc - 20)
    yb = ys[sel2][np.argmin(sign * xs[sel2])]
    seg = (ys >= yb) & (ys <= yc)
    py, px = ys[seg], xs[seg]
    p0, p1 = np.array([side[yb], yb], float), np.array([side[yc], yc], float)
    d = p1 - p0; n = np.array([d[1], -d[0]]) / np.linalg.norm(d)
    if n[0] * sign < 0:
        n = -n                                  # n points OUTWARD (away from the face centre)
    off = (np.stack([px, py], 1) - p0) @ n      # + = outline bulges outward of the chord = convex
    return {"cheek_y": int(yc), "ear_base_y": int(yb), "bulge_max": float(off.max()), "bulge_min": float(off.min()),
            "chord_px": float(np.linalg.norm(d)), "cheek_x": float(side[yc]), "ear_base_x": float(side[yb])}




if __name__ == "__main__":
    case, mpath = sys.argv[1], sys.argv[2]
    out, ph, md = measure(case, mpath)
    print(f"{'':10s} {'photo':>28s} {'model':>28s}")
    for s in "RL":
        a, b = out["photo"][s], out["model"][s]
        print(f"side {s}: cheek->ear-base bulge min/max px   {a['bulge_min']:6.1f}/{a['bulge_max']:5.1f}           "
              f"{b['bulge_min']:6.1f}/{b['bulge_max']:5.1f}")
        print(f"        cheek x / ear-base x               {a['cheek_x']:6.0f}/{a['ear_base_x']:5.0f}           {b['cheek_x']:6.0f}/{b['ear_base_x']:5.0f}")
        print(f"        cheek y / ear-base y               {a['cheek_y']:6.0f}/{a['ear_base_y']:5.0f}           {b['cheek_y']:6.0f}/{b['ear_base_y']:5.0f}")
    print(f"head width at the eyes px                {out['photo']['width_eyes']:6.0f}                        {out['model']['width_eyes']:6.0f}")
    if len(sys.argv) > 3:
        img = cv2.imread(os.path.join(case, "ref.jpg"))
        for m, col in ((ph, (60, 220, 60)), (md, (40, 40, 255))):
            cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(img, cs, -1, col, 2)
        cv2.imwrite(sys.argv[3], cv2.resize(img[60:520, 480:940], None, fx=2, fy=2))
