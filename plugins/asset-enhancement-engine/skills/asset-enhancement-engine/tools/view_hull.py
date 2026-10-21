"""VIEW HULL: a volume from the silhouettes of ONE reference object photographed from several sides (domain-neutral:
a skull, a hoof, a stump, a product). Each view = the object's mask in one photo plus which model axes the image's
right and down directions show. The hull is the intersection of the extruded masks (signed distance = the max of the
2-D signed distances): never smaller than the object, exact on every silhouette, blind to concavities no silhouette
shows (those are carved separately from picked features).

G5 agreement: views that share an axis must agree on its extent. The spec gives one sourced length; every other
scale is implied by the views, and the report shows the two independent scales of the third view and their spread.

spec (JSON):
  image, length_mm, segment {warm_min, value_min},
  views {name: {bbox [x,y,w,h], right "+x|-x|+y|-y|+z|-z", down "...", keep_holes [[x,y],...], level "pca"|null}}
  The view that does not show the length axis is scaled from the others.
ROUNDED mode (spec "loft": {"side": view, "top": view, "q_up", "q_dn"}): three silhouettes cannot describe a rounded
cross-section (every slice of a hull is a box clipped by the front outline). The loft runs superelliptic sections
through the per-station extents - top/bottom from the side view, half-width from the top view's CENTRAL run (the run
through the midline, so bars beside it such as zygomatic arches are excluded) - and is clipped by the hull (every
silhouette stays exact); the hull's parts OUTSIDE the central run (the bars) are added back.
usage: python view_hull.py <spec.json> <out_prefix> [voxel_mm=0.5]
writes <out>.npz (sdf grid, mm), <out>.ply (metres, model frame), <out>_report.json, <out>_views.png
"""
import json
import sys

import cv2
import numpy as np
from scipy import ndimage

AX = {"x": 0, "y": 1, "z": 2}


def view_mask(img, v, seg):
    x, y, w, h = v["bbox"]
    c = img[y:y + h, x:x + w].astype(int)
    fg = ((c[..., 2] - c[..., 0] > seg["warm_min"]) & (c.max(2) > seg["value_min"])).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg, 8)
    m = (lab == 1 + np.argmax(st[1:, 4])).astype(np.uint8)
    # fill every hole except those picked as SEE-THROUGH openings (the rest are highlights on the object)
    inv = 1 - m; n2, lab2 = cv2.connectedComponents(inv, connectivity=4)
    border = set(np.unique(np.r_[lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]]))
    keep = {lab2[py - y, px - x] for px, py in v.get("keep_holes", [])}
    for j in range(1, n2):
        if j not in border and j not in keep:
            m[lab2 == j] = 1
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    if v.get("close_px"):                                            # bright bone read as background at the edge
        k = int(v["close_px"]); m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    if v.get("level") == "pca":                                      # rotate so the long axis is horizontal
        ys, xs = np.nonzero(m); P = np.c_[xs, ys].astype(float); P -= P.mean(0)
        ev, evec = np.linalg.eigh(P.T @ P); d = evec[:, -1]
        ang = np.degrees(np.arctan2(d[1], d[0]))
        ang = ang - 180 if ang > 90 else ang + 180 if ang < -90 else ang
        R = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
        m = (cv2.warpAffine(m, R, (w, h), flags=cv2.INTER_NEAREST) > 0).astype(np.uint8)
        v["_rot_deg"] = float(ang)
    return m


def img_to_model(d, k, coord):
    """image coordinate along the view's `k` direction ("right"/"down") -> model coordinate on the axis it shows"""
    a, sg = d["ax"][k]; e0, e1 = d["ext"][k]
    return a, (coord - (e0 + e1) / 2) * sg * d["scale_mm_per_px"]


def loft_round(F, V, spec, g, P, la, step=1.0):
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sdf_core import loft_y, smin
    side, top = V[spec["side"]], V[spec["top"]]
    # side view: per column -> length coordinate; top/bottom of the mask -> up axis
    kL = "right" if side["ax"]["right"][0] == la else "down"; kU = "down" if kL == "right" else "right"
    m = side["m"] if kL == "right" else side["m"].T
    prof = {}
    for c in range(m.shape[1]):
        rows = np.nonzero(m[:, c])[0]
        if len(rows) < 2: continue
        _, yv = img_to_model(side, kL, c)
        a_u, z0 = img_to_model(side, kU, rows.min()); _, z1 = img_to_model(side, kU, rows.max())
        prof[round(yv / step) * step] = (max(z0, z1), min(z0, z1))
    # top view: per column -> length; the run through the midline row -> half-width (bars beside it excluded)
    kL2 = "right" if top["ax"]["right"][0] == la else "down"; kW = "down" if kL2 == "right" else "right"
    mt = top["m"] if kL2 == "right" else top["m"].T
    e0, e1 = top["ext"][kW]; mid_row = int(round((e0 + e1) / 2))
    wid = {}
    for c in range(mt.shape[1]):
        col = mt[:, c]
        if not col[mid_row]: continue
        lo_ = mid_row
        while lo_ > 0 and col[lo_ - 1]: lo_ -= 1
        hi_ = mid_row
        while hi_ < len(col) - 1 and col[hi_ + 1]: hi_ += 1
        _, yv = img_to_model(top, kL2, c)
        _, x0 = img_to_model(top, kW, lo_); _, x1 = img_to_model(top, kW, hi_)
        wid[round(yv / step) * step] = abs(x1 - x0) / 2
    ys = sorted(set(prof) & set(wid))
    ys = [y for y in ys if prof[y][0] - prof[y][1] > 2 * step]
    st = np.array(ys); T = np.array([prof[y][0] for y in ys]); B = np.array([prof[y][1] for y in ys])
    W = np.array([wid[y] for y in ys])
    # light smoothing of the picked-free profiles (pixel noise), ends kept
    from scipy.ndimage import uniform_filter1d
    T, B, W = (uniform_filter1d(a_, 3, mode="nearest") for a_ in (T, B, W))
    M = B + spec.get("mid_frac", 0.5) * (T - B)
    pr = loft_y(st / 1000, T / 1000, B / 1000, M / 1000, W / 1000, q_up=spec.get("q_up", 2.3), q_dn=spec.get("q_dn", 2.0), name="view_loft")
    X, Y, Z = (q / 1000 for q in P)
    D = pr.fn(X, Y, Z) * 1000
    # bars beside the central run: hull outside the central half-width (interpolated over the length axis)
    hw = np.interp(P[la], st, W, left=0, right=0)
    bars = np.maximum(F, hw + 0.5 - np.abs(P[0]))
    Fr = np.maximum(D, F)                                            # rounded, never outside any silhouette
    Fr = smin(Fr, bars, spec.get("bar_blend_mm", 1.5)).astype(np.float32)
    return Fr, dict(stations=len(st), y_range_mm=[float(st[0]), float(st[-1])], max_half_width_mm=float(W.max()),
                    q_up=spec.get("q_up", 2.3), q_dn=spec.get("q_dn", 2.0), mid_frac=spec.get("mid_frac", 0.5))


def axis_of(s):
    return AX[s[1]], (1.0 if s[0] == "+" else -1.0)


def load_views(S):
    """masks, axis mappings and per-view scales (mm/px) of a spec; also the cross-view agreement (G5)"""
    img = cv2.imread(S["image"]); seg = S.get("segment", dict(warm_min=6, value_min=60))
    L = float(S["length_mm"]); la = AX[S.get("length_axis", "y")]
    V = {}
    for name, v in S["views"].items():
        m = view_mask(img, v, seg)
        ys, xs = np.nonzero(m)
        ext = {"right": (xs.min(), xs.max()), "down": (ys.min(), ys.max())}
        V[name] = dict(v=v, m=m, ext=ext, ax={"right": axis_of(v["right"]), "down": axis_of(v["down"])})
    # 1. scales: views showing the length axis get it from the sourced length
    scale = {}; extent_mm = {}
    for name, d in V.items():
        for k in ("right", "down"):
            if d["ax"][k][0] == la:
                scale[name] = L / (d["ext"][k][1] - d["ext"][k][0] + 1)
    for name, d in V.items():
        if name in scale:
            for k in ("right", "down"):
                a = d["ax"][k][0]
                extent_mm.setdefault(a, []).append((name, (d["ext"][k][1] - d["ext"][k][0] + 1) * scale[name]))
    implied = {}
    for name, d in V.items():
        if name in scale:
            continue
        est = []
        for k in ("right", "down"):
            a = d["ax"][k][0]
            for src, mm in extent_mm.get(a, []):
                est.append((src, "xyz"[a], mm / (d["ext"][k][1] - d["ext"][k][0] + 1)))
        implied[name] = est
        scale[name] = float(np.mean([e[2] for e in est]))
    # 2. per-axis extent (mm): mean over the views that show it -> the model box, centred at 0
    box = np.zeros(3)
    for name, d in V.items():
        for k in ("right", "down"):
            pass
    ext_all = {a: [] for a in range(3)}
    for name, d in V.items():
        for k in ("right", "down"):
            ext_all[d["ax"][k][0]].append((d["ext"][k][1] - d["ext"][k][0] + 1) * scale[name])
    box = np.array([np.mean(ext_all[a]) for a in range(3)])
    for name, d in V.items():
        d["scale_mm_per_px"] = scale[name]
    return V, scale, implied, ext_all, box, la


def pick_to_model(d, xy):
    """a point picked in FULL-image coordinates of view d (no PCA-levelled views) -> {axis: model mm}"""
    assert d["v"].get("level") is None, "picks on a levelled view need the rotation"
    u = xy[0] - d["v"]["bbox"][0]; w = xy[1] - d["v"]["bbox"][1]
    out = {}
    for k, c in (("right", u), ("down", w)):
        a, sg = d["ax"][k]; e0, e1 = d["ext"][k]
        out[a] = (c - (e0 + e1) / 2) * sg * d["scale_mm_per_px"]
    return out


def main(spec_path, out, vox=0.5):
    S = json.load(open(spec_path))
    V, scale, implied, ext_all, box, la = load_views(S)
    # 3. the signed-distance field: max over views of each view's 2-D signed distance (mm)
    pad = 3.0
    lo = -box / 2 - pad; n = np.ceil((box + 2 * pad) / vox).astype(int) + 1
    g = [lo[a] + np.arange(n[a]) * vox for a in range(3)]
    X, Y, Z = np.meshgrid(*g, indexing="ij"); P = (X, Y, Z)
    F = np.full(X.shape, -1e9, np.float32)
    for name, d in V.items():
        m = d["m"]
        sd = (cv2.distanceTransform(1 - m, cv2.DIST_L2, 5) - cv2.distanceTransform(m, cv2.DIST_L2, 5)) * scale[name]
        cols = []
        for k in ("right", "down"):
            a, sg = d["ax"][k]
            e0, e1 = d["ext"][k]
            c_img = (e0 + e1) / 2
            cols.append(c_img + sg * P[a] / scale[name])              # model -> image coordinate
        u, w = cols                                                    # u = column (right), w = row (down)
        val = ndimage.map_coordinates(sd, [w.ravel(), u.ravel()], order=1, mode="constant", cval=50.0).reshape(X.shape)
        F = np.maximum(F, val.astype(np.float32))
        d["scale_mm_per_px"] = scale[name]
    loft_rep = None
    if S.get("loft"):
        F, loft_rep = loft_round(F, V, S["loft"], g, P, la)
    from skimage import measure
    verts, faces, _, _ = measure.marching_cubes(F, 0.0, spacing=(vox, vox, vox))
    verts += lo
    np.savez_compressed(out + ".npz", F=F, lo=lo, vox=vox)
    sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
    from sdf_core import write_ply
    write_ply(out + ".ply", verts / 1000.0, faces)
    rep = dict(box_mm=box.round(2).tolist(), scale_mm_per_px={k: round(v, 5) for k, v in scale.items()},
               implied_scales={k: [(s, a, round(x, 5)) for s, a, x in v] for k, v in implied.items()},
               agreement={k: round(float((max(x[2] for x in v) - min(x[2] for x in v)) / np.mean([x[2] for x in v])), 4) for k, v in implied.items()},
               extents_mm={"xyz"[a]: [round(x, 2) for x in ext_all[a]] for a in range(3)},
               level_rot_deg={k: d["v"].get("_rot_deg") for k, d in V.items()}, verts=len(verts), faces=len(faces), loft=loft_rep)
    json.dump(rep, open(out + "_report.json", "w"), indent=1)
    tiles = []
    for name, d in V.items():
        t = cv2.cvtColor(d["m"] * 255, cv2.COLOR_GRAY2BGR); s = 360 / max(t.shape[:2])
        t = cv2.resize(t, None, fx=s, fy=s); cv2.putText(t, name, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        tiles.append(np.pad(t, ((0, 360 - t.shape[0]), (0, 360 - t.shape[1]), (0, 0)), constant_values=60))
    cv2.imwrite(out + "_views.png", np.hstack(tiles))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.5)
