"""PROPOSE landmark candidates from a subject's silhouette (engine-grounding G4: code proposes, a picker picks, code
checks). Domain-neutral: works on any mask. Proposes
  - corners: curvature extrema along the outline (convex = bony points such as a heel or an elbow; concave = folds),
  - the dorsal line: the top edge of the silhouette per column,
  - appendage roots: where a thin appendage (tail) widens into the body (medial-axis width jump).
Writes <out>.json (numbered candidates with pixel coordinates and kind) and <out>.png (numbered overlay to pick from).
usage: python outline_candidates.py <image> <mask.png> <out_prefix> [min_y_frac=0.0]
"""
import json
import sys

import cv2
import numpy as np


def corners(cnt, win=18, min_turn=35.0, sep=25):
    p = cnt[:, 0, :].astype(float); n = len(p)
    a = p[(np.arange(n) - win) % n]; b = p[(np.arange(n) + win) % n]
    v1, v2 = p - a, b - p
    ang = np.degrees(np.arctan2(v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0], (v1 * v2).sum(1)))   # signed turning
    out = []
    order = np.argsort(-np.abs(ang))
    for i in order:
        if abs(ang[i]) < min_turn: break
        if all(np.hypot(*(p[i] - q["xy"])) > sep for q in out):
            out.append(dict(xy=p[i], turn=float(ang[i])))
    return out


def outline_path(cnt, a, b, upper=True):
    """the OUTLINE between two picked points, walked along the contour (not the top pixel per column: a column top
    picks up whatever occludes the line there - on cat1 the ear tip became 'dorsal line', R4c). Of the two arcs
    between a and b, returns the upper (smaller mean y) or the lower one, ordered from a to b."""
    p = cnt[:, 0, :]; n = len(p)
    ia = int(np.argmin(np.hypot(*(p - np.asarray(a)).T))); ib = int(np.argmin(np.hypot(*(p - np.asarray(b)).T)))
    arc1 = p[[(ia + k) % n for k in range((ib - ia) % n + 1)]]
    arc2 = p[[(ia - k) % n for k in range((ia - ib) % n + 1)]]
    pick = min if upper else max
    return pick((arc1, arc2), key=lambda q: q[:, 1].mean())


def appendage_roots(mask, min_len=60):
    """thin parts of the mask: medial axis via distance transform; a root is where the local half-width jumps"""
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    thin = (dist > 0) & (dist < np.percentile(dist[dist > 0], 60))
    sk = cv2.ximgproc.thinning(mask * 255) if hasattr(cv2, "ximgproc") else None
    if sk is None:
        return []
    ys, xs = np.where(sk > 0)
    w = dist[ys, xs]
    roots = []
    for y, x, ww in zip(ys, xs, w):
        nb = dist[max(y - 12, 0):y + 13, max(x - 12, 0):x + 13]
        if ww < 14 and nb.max() > 2.2 * ww:
            roots.append((x, y, float(ww), float(nb.max())))
    return roots


if __name__ == "__main__":
    img = cv2.imread(sys.argv[1]); mask = (cv2.imread(sys.argv[2], 0) > 127).astype(np.uint8)
    out = sys.argv[3]; min_y = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    H, W = mask.shape
    cnt = max(cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0], key=cv2.contourArea)
    cand = [c for c in corners(cnt) if c["xy"][1] >= min_y * H]
    top = {}
    for x in range(W):
        ys = np.where(mask[:, x])[0]
        if len(ys): top[x] = int(ys.min())
    roots = appendage_roots(mask)
    ov = (img * 0.5).astype(np.uint8)
    cv2.drawContours(ov, [cnt], -1, (200, 200, 200), 1)
    for x, y in top.items():
        if x % 4 == 0: cv2.circle(ov, (x, y), 1, (0, 255, 0), -1)
    rec = []
    for i, c in enumerate(cand):
        x, y = int(c["xy"][0]), int(c["xy"][1]); col = (0, 200, 255) if c["turn"] > 0 else (255, 120, 0)
        cv2.circle(ov, (x, y), 5, col, 2); cv2.putText(ov, str(i), (x + 6, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
        rec.append(dict(id=i, x=x, y=y, kind="corner", turn_deg=round(c["turn"], 1)))
    for j, (x, y, w, nbmax) in enumerate(roots[:200:5]):
        cv2.drawMarker(ov, (int(x), int(y)), (255, 0, 255), cv2.MARKER_TILTED_CROSS, 8, 1)
        rec.append(dict(id=f"r{j}", x=int(x), y=int(y), kind="appendage_root", half_width=w, body_half_width=nbmax))
    cv2.imwrite(out + ".png", ov)
    json.dump(dict(image=sys.argv[1], candidates=rec, dorsal_top={str(k): v for k, v in top.items()}), open(out + ".json", "w"))
    print(f"{len(cand)} corners, {len(roots)} appendage-root points -> {out}.png")
