"""Multi-view shape coherence vs a 3D reference (measuring stick): orthographic silhouettes from 5 views +
trunk profile curves. Model = fur envelope (+ part owners for attribution); reference = aligned mesh in the
same world frame. Lower weight on the side the photo never saw (the reference hallucinated it).

usage: python multiview.py <model_prefix> <ref_aligned.ply> [out_png]
  model_prefix -> <prefix>_env.ply, <prefix>_env_owner.npy, <prefix>_parts.json, <prefix>_landmarks.json
Gate (provisional, ratchet): weighted mean IoU >= 0.85, every seen view IoU >= 0.80,
topline/underline/width mean |diff| <= 4 mm, extra profile bumps <= 1.
"""
import json, os, sys
from collections import Counter
import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter1d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import read_ply  # noqa: E402

PX = 2000.0  # pixels per metre (0.5 mm px)
VIEWS = {  # name: (u axis, v axis (up in image), weight)  - orthographic projections
    "side_L": ((0, -1, 0), (0, 0, 1), 1.0),     # looking from +X (the cat's left, the side the photo shows)
    "side_R": ((0, 1, 0), (0, 0, 1), 0.4),      # unseen in the photo
    "top": ((1, 0, 0), (0, -1, 0), 0.8),
    "back": ((-1, 0, 0), (0, 0, 1), 0.6),
    "front": ((1, 0, 0), (0, 0, 1), 1.0),
}


def raster(v, f, U, Vax, lo, shape, owner=None):
    u = (v @ np.array(U) - lo[0]) * PX
    w = (lo[1] - v @ np.array(Vax)) * PX
    pts = np.stack([u, w], 1)[f].astype(np.int32)
    img = np.zeros(shape, np.int32) - 1
    # per-triangle fill: cv2.fillPoly(list) uses even-odd, so overlapping triangles punch holes
    lab = np.zeros(shape, np.int32)
    own = owner[f[:, 0]] + 1 if owner is not None else np.ones(len(f), np.int32)
    for t, o in zip(pts, own.tolist()):
        cv2.fillConvexPoly(lab, t, int(o))
    return lab > 0, (lab - 1 if owner is not None else None)


def profiles(v, ys, xlim=0.03):
    top, bot, wid = [], [], []
    for y in ys:
        sl = v[np.abs(v[:, 1] - y) < 0.004]
        mid = sl[np.abs(sl[:, 0]) < 0.006]
        if len(mid) < 4:
            top.append(np.nan); bot.append(np.nan); wid.append(np.nan); continue
        t, b = mid[:, 2].max(), mid[mid[:, 2] > 0.05, 2].min() if (mid[:, 2] > 0.05).any() else np.nan
        top.append(t); bot.append(b)
        band = sl[(sl[:, 2] > b + 0.3 * (t - b)) & (sl[:, 2] < t)] if not np.isnan(b) else sl[:0]
        wid.append(np.abs(band[:, 0]).max() if len(band) else np.nan)
    return np.array(top), np.array(bot), np.array(wid)


def bumps(curve):
    c = gaussian_filter1d(np.nan_to_num(curve, nan=np.nanmean(curve)), 1.5)
    k = np.diff(c, 2)
    k[np.abs(k) < 2e-5] = 0
    s = np.sign(k[k != 0])
    return int((np.diff(s) != 0).sum())


def plant_mv(mv, mf, L, name):
    v = mv.copy()
    H = np.array(L["head"])
    if name == "head_forward":      # v16 posture: head 30 mm forward, 20 mm lower
        w = np.clip(1 - (np.linalg.norm(v - H, axis=1) - 0.05) / 0.03, 0, 1)
        v += w[:, None] * np.array([0, -0.03, -0.02])
    elif name == "chest_ball":      # v16 chest: a ball in front of the trunk
        c = np.array([0.0, -0.10, 0.15]); d = np.linalg.norm(v - c, axis=1)
        v += (v - c) / np.maximum(d, 1e-9)[:, None] * (0.012 * np.clip(1 - d / 0.05, 0, 1) ** 2)[:, None]
    elif name == "hip_bulge":      # anchored ON the haunch surface (v1 fixture sat 6 mm inside -> only 5.6 mm push)
        for s_ in (-1, 1):
            band = (np.abs(v[:, 1] - 0.09) < 0.004) & (np.abs(v[:, 2] - 0.16) < 0.006) & (s_ * v[:, 0] > 0)
            p0 = v[band][np.argmax(s_ * v[band][:, 0])]
            nrm = np.array([s_, 0.0, 0.0])
            d = np.linalg.norm(v - p0, axis=1)
            v += nrm[None, :] * (0.010 * np.clip(1 - d / 0.03, 0, 1) ** 2)[:, None]
    elif name == "torso_stretch":
        sel = v[:, 1] > 0.0
        v[sel, 1] *= 1.35
    return v


def surface_dev(mv, rv, rf, exclude_head=None, exclude_tail_y=0.15):
    """signed distance model->reference surface (outward +), binned in 2 cm cells over trunk+legs; returns the
    worst cell's 90th percentile outward and inward deviation - catches LOCAL bulges/dents that barely move a
    silhouette or a station-averaged profile (multiview v1 missed a 12 mm chest ball and a 10 mm hip bulge)."""
    from scipy.spatial import cKDTree
    rng = np.random.default_rng(1)
    A, B, C = rv[rf[:, 0]], rv[rf[:, 1]], rv[rf[:, 2]]
    fn = np.cross(B - A, C - A); ar = np.linalg.norm(fn, axis=1); fn = fn / np.maximum(ar, 1e-12)[:, None]
    k = rng.choice(len(rf), 300000, p=ar / ar.sum())
    r1, r2 = rng.random(len(k)), rng.random(len(k)); s1 = np.sqrt(r1)
    S = (1 - s1)[:, None] * A[k] + (s1 * (1 - r2))[:, None] * B[k] + (s1 * r2)[:, None] * C[k]
    N = fn[k]
    sel = mv[:, 1] < exclude_tail_y
    if exclude_head is not None:   # whole head incl. ears (head pose differs by design; ears dominated v1)
        sel &= (np.linalg.norm(mv - exclude_head, axis=1) > 0.085) & ~((mv[:, 2] > 0.26) & (mv[:, 1] < -0.04))
    pts = mv[sel][:: max(sel.sum() // 120000, 1)]
    _, idx = cKDTree(S).query(pts)
    sd = ((pts - S[idx]) * N[idx]).sum(1) * 1000
    cell = np.floor(pts / 0.02).astype(int)
    keys, inv = np.unique(cell, axis=0, return_inverse=True)
    worst_out, worst_in, where_out, where_in = 0.0, 0.0, None, None
    cells = {}
    for ci in range(len(keys)):
        m = inv == ci
        if m.sum() < 30:
            continue
        o, i_ = np.percentile(sd[m], 90), -np.percentile(sd[m], 10)
        cells[tuple(keys[ci])] = (float(o), float(i_), float(np.median(sd[m])))
        if o > worst_out:
            worst_out, where_out = o, (keys[ci] * 0.02 + 0.01).round(3).tolist()
        if i_ > worst_in:
            worst_in, where_in = i_, (keys[ci] * 0.02 + 0.01).round(3).tolist()
    return {"bulge_cell_p90_mm": round(float(worst_out), 1), "bulge_at": where_out,
            "dent_cell_p90_mm": round(float(worst_in), 1), "dent_at": where_in, "_cells": cells}


def score(mv, mf, own, names, rv, rf, out_png=None, quiet=False, head=None):
    allv = np.vstack([mv, rv])
    tiles, rows, wsum, isum, ok = [], {}, 0.0, 0.0, True
    for name, (U, Vax, wt) in VIEWS.items():
        uu, vv = allv @ np.array(U), allv @ np.array(Vax)
        lo = (uu.min() - 0.01, vv.max() + 0.01)
        shape = (int((vv.max() - vv.min() + 0.02) * PX) + 2, int((uu.max() - uu.min() + 0.02) * PX) + 2)
        ms, lab = raster(mv, mf, U, Vax, lo, shape, own)
        rs, _ = raster(rv, rf, U, Vax, lo, shape)
        iou = (ms & rs).sum() / max((ms | rs).sum(), 1)
        cm = ms & ~cv2.erode(ms.astype(np.uint8), np.ones((3, 3))).astype(bool)
        cr = rs & ~cv2.erode(rs.astype(np.uint8), np.ones((3, 3))).astype(bool)
        d = np.concatenate([distance_transform_edt(~cr)[cm], distance_transform_edt(~cm)[cr]]) / PX * 1000
        row = {"iou": round(float(iou), 4), "contour_p95_mm": round(float(np.percentile(d, 95)), 1), "weight": wt}
        if lab is not None and names:
            ex = Counter(names[i] if 0 <= i < len(names) else "?" for i in lab[ms & ~rs])
            _, (iy, ix) = distance_transform_edt(~ms, return_indices=True)
            mi = Counter(names[i] if 0 <= i < len(names) else "?" for i in lab[iy, ix][rs & ~ms])
            row["excess_mm2"] = {k: round(c / PX ** 2 * 1e6) for k, c in ex.most_common(4)}
            row["missing_mm2"] = {k: round(c / PX ** 2 * 1e6) for k, c in mi.most_common(4)}
        rows[name] = row
        wsum += wt; isum += wt * iou
        if wt >= 0.8:
            ok &= iou >= 0.80
        if out_png:
            t = np.zeros(shape + (3,), np.uint8) + 40
            t[ms & rs] = (235, 235, 235); t[rs & ~ms] = (60, 60, 230); t[ms & ~rs] = (240, 110, 70)
            tiles.append(cv2.resize(t, (int(t.shape[1] * 400 / t.shape[0]), 400)))
    wiou = isum / wsum
    ok &= wiou >= 0.85
    # trunk profiles along the body axis
    ys = np.linspace(-0.11, 0.12, 47)
    mt, mb, mw = profiles(mv, ys)
    rt, rb, rw = profiles(rv, ys)
    prof = {}
    for nm, a, b in (("topline", mt, rt), ("underline", mb, rb), ("half_width", mw, rw)):
        good = ~np.isnan(a) & ~np.isnan(b)
        prof[nm + "_mae_mm"] = round(float(np.abs(a[good] - b[good]).mean() * 1000), 2) if good.any() else None
        prof[nm + "_extra_bumps"] = bumps(a) - bumps(b)
        ok &= (prof[nm + "_mae_mm"] or 99) <= 4.0 and prof[nm + "_extra_bumps"] <= 1
    if out_png and tiles:
        cv2.imwrite(out_png, cv2.hconcat(tiles))
    dev = surface_dev(mv, rv, rf, exclude_head=head)
    ok &= dev["bulge_cell_p90_mm"] <= 8.0 and dev["dent_cell_p90_mm"] <= 8.0
    return {"views": rows, "weighted_iou": round(wiou, 4), "profiles": prof, "surface": dev, "PASS": bool(ok)}


def main():
    pre, ref_p = sys.argv[1], sys.argv[2]
    surf = "_env" if "--env" in sys.argv else ""   # default: skin (a generated reference is ~skin level)
    mv, mf = read_ply(pre + surf + ".ply")
    own = np.load(pre + surf + "_owner.npy").astype(int) if os.path.exists(pre + surf + "_owner.npy") else None
    names = json.load(open(pre + "_parts.json")) if os.path.exists(pre + "_parts.json") else []
    rv, rf = read_ply(ref_p)
    out_png = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else None
    if "--prove" in sys.argv:
        # regression-style proof: each planted defect must move the metrics past tolerance vs the unplanted build
        L = json.load(open(pre + "_landmarks.json"))["landmarks"]
        hd = np.array(L["head"])
        base = score(mv, mf, None, [], rv, rf, head=hd)
        print("  baseline surface:", {k: v for k, v in base["surface"].items() if not k.startswith("_")})
        def worse(r):
            dv = max(base["views"][k]["iou"] - r["views"][k]["iou"] for k in base["views"])
            dp = max((r["profiles"][k] or 0) - (base["profiles"][k] or 0) for k in base["profiles"] if k.endswith("_mae_mm"))
            bc, rc = base["surface"]["_cells"], r["surface"]["_cells"]
            ds = max([max(rc[c][0] - bc[c][0], rc[c][1] - bc[c][1], abs(rc[c][2] - bc[c][2])) for c in rc if c in bc] or [0])
            return dv, max(dp, ds)
        allc = True
        for d in ("head_forward", "chest_ball", "hip_bulge", "torso_stretch"):
            r = score(plant_mv(mv, mf, L, d), mf, None, [], rv, rf, head=hd)
            dv, dp = worse(r)
            caught = dv >= 0.02 or dp >= 3.0
            allc &= caught
            print(f"  planted {d:14s} worst view IoU drop {dv:.3f}  worst profile/surface rise {dp:.1f} mm -> {'CAUGHT' if caught else 'MISSED'}")
        print("MULTIVIEW PROOF:", "OK" if allc else "FAILED", "(tolerance: view IoU -0.02, or profile/surface cell +3 mm)")
        return
    hd = np.array(json.load(open(pre + "_landmarks.json"))["landmarks"]["head"]) if os.path.exists(pre + "_landmarks.json") else None
    res = score(mv, mf, own, names, rv, rf, out_png, head=hd)
    res["surface"].pop("_cells", None)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
