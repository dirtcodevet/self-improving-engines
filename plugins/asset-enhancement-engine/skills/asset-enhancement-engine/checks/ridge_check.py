"""RIDGE CHECK (rock1 R2; domain-neutral): does a render show the same ridges and flat faces as the photo?

Compares two traced facet structures in the SAME pixel frame (photo camera):
  photo side  : facets JSON {"ridges":[{"id","polyline":[[x,y],..]}], "faces":[{"id","polygon","reads_planar"}]}
  render side : a facets JSON, OR a render image traced here with engine/tools/facet_trace.py
  (optional)  : the render's position pass (H x W x 3 world xyz, .npy) for face planarity.

Verdicts per ridge / face:
  MISSING : a photo ridge less than min_cover of whose length has a render ridge within match_r px
  EXTRA   : a render ridge less than min_cover of whose length has a photo ridge within match_r px
  MOVED   : a matched photo ridge whose median distance to the render ridges is > tol px (R2: 4 px)
  BENT    : a photo face that reads planar whose render points deviate from their best plane by more than
            planar_tol (R2: 1 %) of the face size (residual p1..p99 range / 3-D extent of the face)
PASS only when there is none of these.

usage:
  python ridge_check.py <photo_facets.json> <render_facets.json | render.png> [--pos pos.npy] [--out report.json]
  python ridge_check.py --prove [out_dir]      planted failures on every side (A22) + tracer validation (A23)
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

TOL, MATCH_R, MIN_COVER, PLANAR_TOL, MIN_LEN, ERODE = 4.0, 12.0, 0.5, 0.01, 20.0, 6
CLAY = (0.04, 0.02)   # render side of R2: a flat-shaded clay pass (grain 4 %, mottling 2 %), not the textured beauty


def sample(poly, step=1.0):
    p = np.asarray(poly, np.float64)
    if len(p) < 2:
        return p
    out = [p[0]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(int(np.ceil(np.hypot(*(b - a)) / step)), 1)
        out += [a + (b - a) * t for t in np.arange(1, n + 1) / n]
    return np.array(out)


def length(poly):
    p = np.asarray(poly, np.float64)
    return float(np.sum(np.hypot(*np.diff(p, axis=0).T))) if len(p) > 1 else 0.0


def dist_field(ridges, shape):
    """distance (px) from every pixel to the nearest ridge, ridges rasterised at 4x sub-pixel then measured at 1x"""
    canvas = np.full(shape, 255, np.uint8)
    for r in ridges:
        cv2.polylines(canvas, [np.int32(np.round(np.asarray(r["polyline"]) * 16 - 8))], False, 0, 1, cv2.LINE_8,
                      shift=4)
    return cv2.distanceTransform(canvas, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)


def at(D, pts):
    """bilinear read of a distance field at sub-pixel points (pixel centres at integer + 0.5)"""
    x = np.clip(pts[:, 0] - 0.5, 0, D.shape[1] - 1.001); y = np.clip(pts[:, 1] - 0.5, 0, D.shape[0] - 1.001)
    x0, y0 = x.astype(int), y.astype(int); fx, fy = x - x0, y - y0
    return (D[y0, x0] * (1 - fx) * (1 - fy) + D[y0, x0 + 1] * fx * (1 - fy) + D[y0 + 1, x0] * (1 - fx) * fy
            + D[y0 + 1, x0 + 1] * fx * fy)


def face_bend(poly, pos, erode=ERODE):
    m = np.zeros(pos.shape[:2], np.uint8)
    cv2.fillPoly(m, [np.int32(np.round(poly))], 1)
    m = cv2.erode(m, np.ones((2 * erode + 1,) * 2, np.uint8)) > 0
    P = pos[m]
    P = P[np.isfinite(P).all(1)]
    if len(P) < 30:
        return None
    c = P.mean(0)
    _, s, vt = np.linalg.svd(P - c, full_matrices=False)
    r = (P - c) @ vt[2]
    uv = (P - c) @ vt[:2].T
    size = float(np.hypot(np.ptp(uv[:, 0]), np.ptp(uv[:, 1])))
    rng = float(np.percentile(r, 99) - np.percentile(r, 1))
    return rng / max(size, 1e-12)


def compare(photo, render, shape, pos=None, tol=TOL, match_r=MATCH_R, min_cover=MIN_COVER, planar_tol=PLANAR_TOL,
            min_len=MIN_LEN):
    pr = [r for r in photo["ridges"] if length(r["polyline"]) >= min_len]
    rr = [r for r in render["ridges"] if length(r["polyline"]) >= min_len]
    Dr, Dp = dist_field(rr, shape), dist_field(pr, shape)
    rep = dict(ridges=[], extra=[], faces=[], fails=[])
    for r in pr:
        d = at(Dr, sample(r["polyline"]))
        cov = float(np.mean(d <= match_r))
        med = float(np.median(d[d <= match_r])) if cov > 0 else None
        p90 = float(np.percentile(d[d <= match_r], 90)) if cov > 0 else None
        st = "MISSING" if cov < min_cover else ("MOVED" if med > tol else "ok")
        rep["ridges"].append(dict(id=r["id"], cover=round(cov, 3), median_px=None if med is None else round(med, 2),
                                  p90_px=None if p90 is None else round(p90, 2), status=st))
        if st != "ok":
            rep["fails"].append(f"ridge {r['id']} {st}" + (f" (median {med:.1f} px > {tol})" if st == "MOVED" else
                                                           f" (cover {cov:.2f})"))
    for r in rr:
        d = at(Dp, sample(r["polyline"]))
        cov = float(np.mean(d <= match_r))
        if cov < min_cover:
            rep["extra"].append(dict(id=r.get("id"), cover=round(cov, 3), length_px=round(length(r["polyline"]), 1)))
            rep["fails"].append(f"render ridge {r.get('id')} EXTRA (cover {cov:.2f}, {length(r['polyline']):.0f} px)")
    if pos is not None:
        for f in photo.get("faces", []):
            if not f.get("planar_for_R2", f.get("reads_planar", True)):
                continue
            b = face_bend(f["polygon"], pos)
            st = "n/a" if b is None else ("BENT" if b > planar_tol else "ok")
            rep["faces"].append(dict(id=f["id"], bend=None if b is None else round(b, 4), status=st))
            if st == "BENT":
                rep["fails"].append(f"face {f['id']} BENT ({b * 100:.2f} % > {planar_tol * 100:.0f} %)")
    rep["verdict"] = "PASS" if not rep["fails"] else "FAIL"
    rep["params"] = dict(tol=tol, match_r=match_r, min_cover=min_cover, planar_tol=planar_tol, min_len=min_len)
    return rep


# ---------------------------------------------------------------- synthetic faceted scenes (for the proof only)
def scene(seed, lines=None, H=600, W=700, tex_seed=None, bend=None, gain=1.0, tex=(0.16, 0.05)):
    """a faceted object: convex silhouette cut by straight fracture lines; each cell is a flat face (own plane,
    own shade) with grain + mottling texture. Returns image, mask, ground-truth ridges, position map, lines."""
    rng = np.random.default_rng(seed)
    cx, cy, R = W / 2, H / 2, min(H, W) * 0.42
    ang = np.sort(rng.uniform(0, 2 * np.pi, 9))
    sil = np.c_[cx + R * np.cos(ang) * rng.uniform(0.8, 1.0, 9), cy + R * np.sin(ang) * rng.uniform(0.75, 0.95, 9)]
    sil = cv2.convexHull(np.float32(sil))[:, 0, :]
    mask = np.zeros((H, W), np.uint8); cv2.fillPoly(mask, [np.int32(np.round(sil))], 1)
    if lines is None:
        lines = []                                               # fracture directions spread ~45 deg apart
        th0 = rng.uniform(0, np.pi)                               # (no sliver faces thinner than a few px)
        for k in range(4):
            th = th0 + k * np.pi / 4 + rng.uniform(-0.12, 0.12); n = np.array([np.cos(th), np.sin(th)])
            lines.append([float(n[0]), float(n[1]), float(n @ [cx, cy] + rng.uniform(-0.35, 0.35) * R)])
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    code = np.zeros((H, W), np.int64)
    for k, (a, b, c) in enumerate(lines):
        code |= ((a * xx + b * yy - c) > 0).astype(np.int64) << k
    ids, cell = np.unique(code, return_inverse=True); cell = cell.reshape(H, W) + 1
    cell[mask == 0] = 0
    srng = np.random.default_rng(seed + 7)
    # shades: adjacent faces at least 0.08 apart (a ridge between two faces under one light shows as a step)
    adj = set()
    for a_, b_ in ((cell[:, :-1], cell[:, 1:]), (cell[:-1, :], cell[1:, :])):
        sel = (a_ != b_) & (a_ > 0) & (b_ > 0)
        adj |= set(zip(a_[sel].tolist(), b_[sel].tolist()))
    levels = np.linspace(0.28, 0.78, 11); shade = {}
    for c in range(1, len(ids) + 1):
        nb = [shade[o] for (p_, o) in adj if p_ == c and o in shade] + [shade[p_] for (p_, o) in adj if o == c and p_ in shade]
        cand = [l for l in srng.permutation(levels) if all(abs(l - v) >= 0.08 for v in nb)]
        shade[c] = float(cand[0] if cand else srng.choice(levels))
    # each face its own plane z = p x + q y + r ; a bend adds a parabolic bulge with sagitta bend[1] * face size
    pos = np.full((H, W, 3), np.nan, np.float32)
    for c in range(1, len(ids) + 1):
        m = cell == c
        if not m.any():
            continue
        p, q = srng.uniform(-0.8, 0.8, 2); r = srng.uniform(-50, 50)
        z = p * xx[m] + q * yy[m] + r
        if bend is not None and bend[0] == c:
            u = xx[m] - xx[m].mean(); h = np.ptp(u) / 2 + 1e-9
            size = np.hypot(np.ptp(xx[m]), np.ptp(yy[m]))
            z = z + bend[1] * size * (1 - (u / h) ** 2)
        pos[m] = np.c_[xx[m], yy[m], z]
    trng = np.random.default_rng(1000 + (seed if tex_seed is None else tex_seed))
    grain = cv2.GaussianBlur(trng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 1.3); grain /= grain.std()
    mott = cv2.GaussianBlur(trng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 12); mott /= mott.std()
    base = np.vectorize(lambda c: shade.get(c, 1.0))(cell).astype(np.float32) * gain
    I = base * (1 + tex[0] * grain + tex[1] * mott)
    I = np.where(mask > 0, I, 0.98 + 0.01 * trng.normal(0, 1, (H, W)))
    img = cv2.cvtColor(np.clip(I * 255, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    # ground-truth ridges: each fracture line clipped to the silhouette (cells on both sides are different faces)
    gt = []
    for k, (a, b, c) in enumerate(lines):
        t = np.linspace(-2000, 2000, 16001); n = np.array([a, b]); d = np.array([-b, a])
        pts = (n * c)[None] + t[:, None] * d[None]
        ok = np.array([cv2.pointPolygonTest(np.float32(sil), (float(x), float(y)), True) > 0 for x, y in pts])
        if ok.sum() > 2:
            seg = pts[ok]; gt.append(dict(id=k + 1, polyline=[seg[0].tolist(), seg[-1].tolist()]))
    return img, mask.astype(bool), gt, pos, lines, cell


def gt_facets(gt, cell):
    faces = []
    for c in range(1, cell.max() + 1):
        m = (cell == c).astype(np.uint8)
        if m.sum() < 50:
            continue
        cnt = max(cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0], key=cv2.contourArea)
        faces.append(dict(id=c, polygon=cnt[:, 0, :].tolist(), reads_planar=True))
    return dict(ridges=gt, faces=faces)


def prove(out_dir):
    import facet_trace as ft
    os.makedirs(out_dir, exist_ok=True)
    P = dict(grain=3, merge=6.0, min_area=0.01, edge_k=2.5)
    results = []

    def trace(img, mask):
        res, lab, _ = ft.trace(img, mask, **P)
        return res

    # A23: tracer accuracy on held-out scenes (seeds chosen before the fit, never used to set P)
    val = []
    for s in (101, 102, 103, 104, 105):
        img, mask, gt, pos, lines, cell = scene(s, tex=CLAY)
        tr = trace(img, mask)
        rep = compare(dict(ridges=_inner(gt, mask), faces=[]), tr, mask.shape)
        meds = [r["median_px"] for r in rep["ridges"] if r["median_px"] is not None]
        val.append(dict(seed=s, verdict=rep["verdict"], medians=meds, fails=rep["fails"]))
    allm = [m for v in val for m in v["medians"]]
    validation = dict(seeds=[101, 102, 103, 104, 105], ridge_median_px_median=round(float(np.median(allm)), 2),
                      ridge_median_px_max=round(float(np.max(allm)), 2), per_seed=val,
                      all_pass=all(v["verdict"] == "PASS" for v in val))

    # planted failures, end to end (photo traced, render traced) on scene seeds 11..13
    cases = []
    for s in (11, 12, 13):
        img, mask, gt, pos, lines, cell = scene(s)
        # photo side = a careful trace (picker-traced polylines, as facets.json is): ground truth + 1 px jitter
        jr = np.random.default_rng(s + 900)
        photo = gt_facets([dict(id=r["id"], polyline=(np.asarray(r["polyline"]) + jr.normal(0, 1.0, (2, 2))).tolist())
                           for r in _inner(gt, mask)], cell)
        k = 1 + (s % len(lines))                                   # which fracture line to tamper with
        a, b, c = lines[k - 1]

        def run(name, expect, lines2=None, bend=None, tex=None):
            im2, m2, gt2, pos2, _, cell2 = scene(s, lines=lines2 if lines2 is not None else lines, tex_seed=tex,
                                                 bend=bend, gain=0.93, tex=CLAY)
            rend = trace(im2, m2)
            rep = compare(photo, rend, mask.shape, pos=pos2)
            ok = rep["verdict"] == expect
            cases.append(dict(scene=s, case=name, expect=expect, got=rep["verdict"], correct=ok, fails=rep["fails"][:6]))
            return rep, im2, rend
        run("same geometry, new texture + 7 % darker", "PASS", tex=s + 50)
        run("ridge moved 2 px (inside 4 px tol)", "PASS", lines2=_shift(lines, k, 2.0), tex=s + 51)
        rep6, im6, rend6 = run("ridge moved 6 px", "FAIL", lines2=_shift(lines, k, 6.0), tex=s + 52)
        run("ridge missing", "FAIL", lines2=[l for i, l in enumerate(lines) if i != k - 1], tex=s + 53)
        extra = [[float(np.cos(0.3 + s)), float(np.sin(0.3 + s)), 0.0]]
        extra[0][2] = extra[0][0] * 350 + extra[0][1] * 300 + 30
        run("extra ridge", "FAIL", lines2=lines + extra, tex=s + 54)
        big = max(range(1, cell.max() + 1), key=lambda f: (cell == f).sum())
        run("face bent 3 %", "FAIL", bend=(big, 0.03), tex=s + 55)
        run("face bent 0.5 % (inside 1 % tol)", "PASS", bend=(big, 0.005), tex=s + 56)
        if s == 11:
            ov = ft.overlay(im6, rend6)
            for r in photo["ridges"]:
                cv2.polylines(ov, [np.int32(np.round(np.asarray(r["polyline"])))], False, (0, 200, 0), 1)
            cv2.imwrite(os.path.join(out_dir, "ridge_check_prove_moved6.png"), ov)
    report = dict(tracer_params=P, validation_A23=validation, planted=cases,
                  all_planted_correct=all(c["correct"] for c in cases))
    json.dump(report, open(os.path.join(out_dir, "ridge_check_proof.json"), "w"), indent=1)
    for c in cases:
        print(f"scene {c['scene']}  {c['case']:<42} expect {c['expect']}  got {c['got']}  {'OK' if c['correct'] else 'WRONG'}"
              f"  {'; '.join(c['fails'][:2])}")
    print("A23 tracer validation (held-out seeds):", json.dumps({k: v for k, v in validation.items() if k != 'per_seed'}))
    print("ALL PLANTED CORRECT:", report["all_planted_correct"])
    return report


def _shift(lines, k, d):
    out = [list(l) for l in lines]; out[k - 1][2] += d; return out


def _inner(ridges, mask, margin=6):
    """ground-truth ridges minus the strip along the silhouette (the tracer leaves that strip to R1)"""
    D = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
    out = []
    for r in ridges:
        p = sample(r["polyline"], 1.0)
        keep = at(D, p) > margin
        if keep.sum() > 2:
            q = p[keep]; out.append(dict(id=r["id"], polyline=[q[0].tolist(), q[-1].tolist()]))
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--prove":
        prove(a[1] if len(a) > 1 else ".")
        sys.exit(0)
    photo = json.load(open(a[0]))
    W, H = photo["size"]
    pos = np.load(a[a.index("--pos") + 1]) if "--pos" in a else None
    if a[1].lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr")):
        import facet_trace as ft
        render, _, _ = ft.trace(cv2.imread(a[1]), **photo.get("params", {}))
    else:
        render = json.load(open(a[1]))
    rep = compare(photo, render, (H, W), pos=pos)
    if "--out" in a:
        json.dump(rep, open(a[a.index("--out") + 1], "w"), indent=1)
    print(rep["verdict"], *rep["fails"], sep="\n  ")
