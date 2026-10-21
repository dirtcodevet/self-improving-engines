"""FACET TRACE: the face/ridge structure of a piecewise-flat object in one image (photo OR render).
Domain-neutral: any object made of near-flat facets seen against a plain background - broken stone, cut gems,
crystals, low-poly renders, folded card, carved wood, architecture.

Cues (how a ridge shows in an image under one light):
  1. shading discontinuity - two faces meeting at an angle get different brightness (a STEP in smoothed luminance);
  2. region uniformity     - inside one flat face the smoothed luminance is near constant;
  3. edges                 - the step lies on a gradient-magnitude maximum (watershed line).
Texture (grain, noise) is removed first with a median filter sized to the grain, which keeps steps sharp.

Method:
  mask -> grain-suppressed luminance Ls -> SLIC over-segmentation of Ls -> greedy merge of adjacent superpixels whose
  mean Ls differ by < merge_dL (region uniformity) -> small regions folded into their most similar neighbour ->
  merged regions eroded and re-grown by watershed on |grad Ls| (boundaries snap to the step, cue 3) ->
  ridges = shared boundaries between two faces (silhouette excluded), ordered and simplified to polylines.

usage: python facet_trace.py <image> <out.json> [overlay.png] [--mask m.png] [--grain 4] [--merge 4.0] [--min_area 0.004]
out.json: {"image", "size":[W,H], "params", "faces":[{"id","polygon":[[x,y],..],"area_px","mean_L","reads_planar",...}],
           "ridges":[{"id","faces":[a,b],"polyline":[[x,y],..],"length_px","step_L"}]}
Built for rock1 R2 (2026-10-18). Reuses nothing from the cat engine's line tools for the trace itself
(line_map.py works at 1-2.5 px, the grain scale here); line_map is used as an independent cue in validation.
"""
import json
import sys

import cv2
import numpy as np
from scipy import ndimage as ndi
from skimage import segmentation, morphology

DEFAULTS = dict(grain=4, merge=4.0, min_area=0.004, n_seg=900, erode=5, sil_margin=6, min_ridge=20, simplify=1.5, edge_k=2.5)


def object_mask(img, thr=205):
    """subject vs a light plain background (studio white). Largest component, holes filled."""
    L = cv2.medianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0], 7)
    m = (L < thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return m.astype(bool)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return ndi.binary_fill_holes(lab == k)


def smooth_lum(img, grain):
    """luminance (0..100) with texture below ~2*grain px removed; median keeps facet steps sharp"""
    L = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0]
    k = 2 * int(grain) + 1
    Ls = cv2.medianBlur(cv2.medianBlur(L, k), k)
    return cv2.GaussianBlur(Ls.astype(np.float32) * 100 / 255, (0, 0), 1.0)


def grad_mag(Ls, s=1.5):
    g = cv2.GaussianBlur(Ls, (0, 0), s)
    return np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)) / 8


def merge_regions(lab, Ls, thr, min_area_px):
    """greedy region merge on mean luminance (union of the most similar adjacent pair first)."""
    lab = lab.copy()
    while True:
        ids = np.unique(lab[lab > 0])
        if len(ids) < 2:
            return lab
        mean = ndi.mean(Ls, lab, ids); area = ndi.sum(np.ones_like(Ls), lab, ids)
        M = dict(zip(ids, mean)); A = dict(zip(ids, area))
        pairs = set()
        for a, b in ((lab[:, :-1], lab[:, 1:]), (lab[:-1, :], lab[1:, :])):
            sel = (a != b) & (a > 0) & (b > 0)
            pairs |= set(zip(np.minimum(a[sel], b[sel]).tolist(), np.maximum(a[sel], b[sel]).tolist()))
        if not pairs:
            return lab
        # phase 1: merge pairs more similar than thr (region uniformity); phase 2 (only once phase 1 is done):
        # regions still smaller than min_area fold into their most similar neighbour
        cand = sorted((abs(M[a] - M[b]), a, b) for a, b in pairs)
        small = []
        if cand[0][0] >= thr:
            small = sorted((abs(M[a] - M[b]), a, b) for a, b in pairs if min(A[a], A[b]) < min_area_px)
            if not small:
                return lab
            cand = small
        # merge a whole batch of disjoint pairs per pass (speed); each region at most once per pass
        used = set(); remap = {}
        for d, a, b in cand:
            if not small and d >= thr:
                break
            if small and min(A[a], A[b]) >= min_area_px:
                continue
            if a in used or b in used:
                continue
            used |= {a, b}; remap[b if A[b] < A[a] else a] = a if A[b] < A[a] else b
        lut = np.arange(lab.max() + 1)
        for s, t in remap.items():
            lut[s] = t
        lab = lut[lab]


def merge_weak_boundaries(lab, G, mask, k):
    inner = cv2.erode(mask.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    sums = {}
    for a, b in ((lab[:, :-1], lab[:, 1:]), (lab[:-1, :], lab[1:, :])):
        sel = (a != b) & (a > 0) & (b > 0)
        g = G[:a.shape[0], :a.shape[1]][sel]; ok = inner[:a.shape[0], :a.shape[1]][sel]
        for p, q, gg, o in zip(np.minimum(a[sel], b[sel]).tolist(), np.maximum(a[sel], b[sel]).tolist(), g, ok):
            if o:
                s = sums.setdefault((p, q), [0.0, 0]); s[0] += gg; s[1] += 1
    # texture level: median gradient over pixels away from any boundary
    bd = segmentation.find_boundaries(lab, mode="thick")
    interior = inner & ~cv2.dilate(bd.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    tex = float(np.median(G[interior])) if interior.any() else float(np.median(G[mask]))
    parent = {}

    def root(x):
        while parent.get(x, x) != x:
            x = parent.get(x, x)
        return x
    for (p, q), (s, n) in sums.items():
        if n >= 5 and s / n < k * tex:
            rp, rq = root(p), root(q)
            if rp != rq:
                parent[max(rp, rq)] = min(rp, rq)
    lut = np.arange(lab.max() + 1)
    for x in range(1, lab.max() + 1):
        lut[x] = root(x)
    return lut[lab]


def order_chain(pts):
    """order a thin set of pixels (a ridge between two faces) into one path: longest geodesic path of the skeleton"""
    if len(pts) < 2:
        return pts
    x0, y0 = pts.min(0); img = np.zeros(tuple((pts.max(0) - pts.min(0) + 3)[::-1]), bool)
    img[pts[:, 1] - y0 + 1, pts[:, 0] - x0 + 1] = True
    sk = morphology.skeletonize(img)
    ys, xs = np.nonzero(sk)
    if len(xs) < 2:
        return pts
    idx = {(x, y): i for i, (x, y) in enumerate(zip(xs, ys))}
    nb = [[idx[(x + dx, y + dy)] for dx in (-1, 0, 1) for dy in (-1, 0, 1)
           if (dx or dy) and (x + dx, y + dy) in idx] for x, y in zip(xs, ys)]

    def bfs(s):
        dist = [-1] * len(xs); prev = [-1] * len(xs); dist[s] = 0; q = [s]
        for u in q:
            for v in nb[u]:
                if dist[v] < 0:
                    dist[v] = dist[u] + 1; prev[v] = u; q.append(v)
        far = int(np.argmax(dist)); return far, prev
    a, _ = bfs(0); b, prev = bfs(a)
    path = [b]
    while path[-1] != a:
        path.append(prev[path[-1]])
    return np.array([(xs[i] + x0 - 1, ys[i] + y0 - 1) for i in path])


def ridges_from_labels(lab, mask, sil_margin, min_len, eps):
    """boundary between faces a and b, as pixel-edge midpoints, minus the strip along the silhouette"""
    inner = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5) > sil_margin
    out = []
    H, W = lab.shape
    bnd = {}
    for (a, b, ya, xa) in ((lab[:, :-1], lab[:, 1:], 0, 1), (lab[:-1, :], lab[1:, :], 1, 0)):
        sel = (a != b) & (a > 0) & (b > 0)
        yy, xx = np.nonzero(sel)
        for y, x, p, q in zip(yy, xx, a[sel], b[sel]):
            if not inner[y, x]:
                continue
            bnd.setdefault((min(p, q), max(p, q)), []).append((x, y))
    for (p, q), pts in bnd.items():
        pts = np.array(pts)
        # a pair can share several separate stretches: split into connected pieces (8-conn, 3 px gap allowed)
        canvas = np.zeros((H, W), np.uint8); canvas[pts[:, 1], pts[:, 0]] = 1
        n, cc = cv2.connectedComponents(cv2.dilate(canvas, np.ones((3, 3), np.uint8)))
        for k in range(1, n):
            sub = pts[cc[pts[:, 1], pts[:, 0]] == k]
            if len(sub) < min_len:
                continue
            path = order_chain(sub).astype(np.float32) + 0.5          # pixel-edge midpoint
            poly = cv2.approxPolyDP(path.reshape(-1, 1, 2), eps, False)[:, 0, :]
            length = float(np.sum(np.hypot(*np.diff(poly, axis=0).T)))
            if length >= min_len:
                out.append(dict(faces=[int(p), int(q)], polyline=np.round(poly, 1).tolist(), length_px=round(length, 1)))
    return out


def trace(img, mask=None, **kw):
    P = {**DEFAULTS, **{k: v for k, v in kw.items() if v is not None}}
    if mask is None:
        mask = object_mask(img)
    mask = mask.astype(bool)
    Ls = smooth_lum(img, P["grain"])
    G = grad_mag(Ls)
    sp = segmentation.slic(Ls, n_segments=P["n_seg"], compactness=0.3, channel_axis=None, mask=mask,
                           start_label=1, enforce_connectivity=True)
    min_area_px = P["min_area"] * mask.sum()
    lab = merge_regions(sp, Ls, P["merge"], min_area_px)
    # snap: erode each region, re-grow by watershed on the gradient magnitude (boundary -> step location)
    markers = np.zeros_like(lab)
    ker = np.ones((2 * P["erode"] + 1,) * 2, np.uint8)
    for r in np.unique(lab[lab > 0]):
        er = cv2.erode((lab == r).astype(np.uint8), ker) > 0
        markers[er] = r
    lab = segmentation.watershed(G, markers, mask=mask)
    # edge cue: a ridge is a SHARP step. A boundary whose mean |grad| is not clearly above the texture's own
    # gradient inside the faces is mottling, not a ridge -> merge across it, then snap again.
    for _ in range(2):
        lab = merge_weak_boundaries(lab, G, mask, P["edge_k"])
        markers = np.zeros_like(lab)
        for r in np.unique(lab[lab > 0]):
            markers[cv2.erode((lab == r).astype(np.uint8), ker) > 0] = r
        lab = segmentation.watershed(G, markers, mask=mask)
    # relabel 1..n by area (largest first)
    ids, cnt = np.unique(lab[lab > 0], return_counts=True)
    order = ids[np.argsort(-cnt)]
    lut = np.zeros(lab.max() + 1, int); lut[order] = np.arange(1, len(order) + 1)
    lab = lut[lab]
    faces = []
    yy, xx = np.mgrid[0:lab.shape[0], 0:lab.shape[1]]
    for f in range(1, lab.max() + 1):
        m = lab == f
        cs = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]
        c = max(cs, key=cv2.contourArea)
        poly = cv2.approxPolyDP(c, P["simplify"], True)[:, 0, :]
        # shading over the face: plane fit L = a + b x + c y; a face that 'reads planar' has a small shading ramp
        A = np.c_[np.ones(m.sum()), xx[m], yy[m]]
        coef, *_ = np.linalg.lstsq(A, Ls[m], rcond=None)
        diam = float(np.hypot(*(np.ptp(xx[m]), np.ptp(yy[m]))))
        ramp = float(np.hypot(coef[1], coef[2]) * diam)               # L units across the face
        resid = float(np.std(Ls[m] - A @ coef))
        faces.append(dict(id=f, polygon=poly.tolist(), area_px=int(m.sum()), centroid=[round(float(xx[m].mean()), 1),
                          round(float(yy[m].mean()), 1)], mean_L=round(float(Ls[m].mean()), 2),
                          shading_ramp_L=round(ramp, 2), shading_resid_L=round(resid, 2),
                          reads_planar=bool(ramp < 12 and resid < 4)))
    ridges = ridges_from_labels(lab, mask, P["sil_margin"], P["min_ridge"], P["simplify"])
    M = {f["id"]: f["mean_L"] for f in faces}
    for i, r in enumerate(ridges):
        r["id"] = i + 1
        r["step_L"] = round(abs(M[r["faces"][0]] - M[r["faces"][1]]), 2)
    return dict(size=[img.shape[1], img.shape[0]], params=P, faces=faces, ridges=ridges), lab, mask


def overlay(img, res, lab=None):
    ov = (cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR) * 0.55 + 100).astype(np.uint8)
    rng = np.random.default_rng(3)
    if lab is not None:
        col = rng.integers(60, 255, (lab.max() + 1, 3)); col[0] = 0
        tint = col[lab].astype(np.float32)
        ov = np.where(lab[..., None] > 0, (ov * 0.6 + tint * 0.4), ov).astype(np.uint8)
    for f in res["faces"]:
        cv2.polylines(ov, [np.int32(f["polygon"])], True, (90, 90, 90), 1, cv2.LINE_AA)
        cx, cy = map(int, f["centroid"])
        cv2.putText(ov, f"F{f['id']}", (cx - 12, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(ov, f"F{f['id']}", (cx - 12, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (255, 255, 255) if f["reads_planar"] else (0, 200, 255), 1, cv2.LINE_AA)
    for r in res["ridges"]:
        p = np.float32(r["polyline"])
        cv2.polylines(ov, [np.int32(np.round(p * 4))], False, (0, 0, 255), 2, cv2.LINE_AA, shift=2)
        m = p[len(p) // 2]
        cv2.putText(ov, f"R{r['id']}", (int(m[0]) + 4, int(m[1]) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 160), 1,
                    cv2.LINE_AA)
    return ov


if __name__ == "__main__":
    args = sys.argv[1:]
    opt = {}
    for k in ("--mask", "--grain", "--merge", "--min_area"):
        if k in args:
            i = args.index(k); opt[k[2:]] = args[i + 1]; del args[i:i + 2]
    img = cv2.imread(args[0])
    mask = cv2.imread(opt.pop("mask"), 0) > 127 if "mask" in opt else None
    kw = {k: float(v) for k, v in opt.items()}
    if "grain" in kw:
        kw["grain"] = int(kw["grain"])
    res, lab, mask = trace(img, mask, **kw)
    res["image"] = args[0]
    json.dump(res, open(args[1], "w"), indent=1)
    print(f"{len(res['faces'])} faces, {len(res['ridges'])} ridges -> {args[1]}")
    if len(args) > 2:
        cv2.imwrite(args[2], overlay(img, res, lab))
