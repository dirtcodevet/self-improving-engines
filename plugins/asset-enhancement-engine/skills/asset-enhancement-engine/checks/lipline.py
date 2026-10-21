"""Lip-line check: the closed mouth's two margins must be smooth curves - no cusps, notches or sawtooth.
v19-v26 lips read "jagged/notched" (person: "mouth looks like a straight line or square"; clay close-ups): the
lip line had a cusp at the midline (|x| in the droop term) and the lower lip was the sliced bottom of the upper-lip
lobes. Measured on the head mesh (_hr.ply when present): for 0.5 mm bins across the mouth, the upper margin =
lowest frontal point of the upper lip, the lower margin = highest frontal point of the lower lip. A local
quadratic fit (+-1.2 mm) gives the curvature radius and the high-frequency residual of each margin.
The philtrum cleft (|x| < 1.2 mm on the UPPER margin) is anatomy, not a defect, and is excluded there only.

usage: python lipline.py <mesh_prefix> [--plant cusp]     (also used by checks.py)
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import mouth_geom as MG  # noqa: E402

R_MIN_MM = 2.0      # tightest allowed bend of a lip margin (designed lobes: ~5 mm; the v26 midline cusp: < 1 mm)
HF_MAX_MM = 0.20    # sawtooth / notch residual allowed around the local quadratic


def margins(v, L, P, bin_w=0.0005):
    R = np.array(L["head_R"]); H0 = np.array(L["head"]); hs = P["head_scale"]
    hl = ((v - H0) @ R) / hs
    x, y, z = hl.T
    G = MG.from_landmarks(L, hs)
    zm, e, _ = MG.zm_e_h(x, y, G)
    near = (np.abs(z - zm) < 0.004) & (e < 1.05)
    xs = np.arange(-0.6 * G["a"], 0.6 * G["a"] + 1e-9, bin_w)
    up, lo = np.full(len(xs), np.nan), np.full(len(xs), np.nan)
    for i, xb in enumerate(xs):
        s = near & (np.abs(x - xb) < bin_w / 2)
        for side, out in ((z > zm, up), (z < zm, lo)):
            q = s & side
            if q.sum() < 4:
                continue
            q &= y < y[q].min() + 0.0025                       # frontal skin + the first 2.5 mm of the slit face
            zz = np.sort(z[q])
            out[i] = np.mean(zz[:3]) if out is up else np.mean(zz[-3:])   # robust edge: mean of 3 extreme points
    return xs, up, lo


def smoothness(xs, zs, skip_mid=0.0, half=0.0012):
    ok = ~np.isnan(zs)
    rmin, hf, at = np.inf, 0.0, None
    for i in np.nonzero(ok)[0]:
        if abs(xs[i]) < skip_mid:
            continue
        w = ok & (np.abs(xs - xs[i]) <= half)
        if abs(xs[i]) >= skip_mid > 0:
            w &= np.abs(xs) >= skip_mid
        if w.sum() < 5:
            continue
        c = np.polyfit(xs[w] - xs[i], zs[w], 2)
        k = abs(2 * c[0]) / (1 + c[1] ** 2) ** 1.5
        r = 1.0 / max(k, 1e-9)
        res = float(np.abs(zs[w] - np.polyval(c, xs[w] - xs[i])).max())
        if r < rmin:
            rmin, at = r, xs[i]
        hf = max(hf, res)
    return float(rmin * 1000), float(hf * 1000), (None if at is None else round(float(at) * 1000, 1))


def check_lipline(v, L, P):
    xs, up, lo = margins(v, L, P)
    ru, hu, au = smoothness(xs, up, skip_mid=0.0012)
    rl, hl_, al = smoothness(xs, lo)
    cover = float(np.mean(~np.isnan(up)) + np.mean(~np.isnan(lo))) / 2
    ok = min(ru, rl) >= R_MIN_MM and max(hu, hl_) <= HF_MAX_MM and cover > 0.8
    return bool(ok), {"upper_rmin_mm": round(float(ru), 2), "upper_at_mm": au, "upper_hf_mm": round(float(hu), 3),
                      "lower_rmin_mm": round(float(rl), 2), "lower_at_mm": al, "lower_hf_mm": round(float(hl_), 3),
                      "coverage": round(cover, 2)}


def plant_cusp(v, L, P, height=0.0008, width=0.0012):
    """the v26 defect: a tent-shaped peak on the lower lip margin at the midline"""
    R = np.array(L["head_R"]); H0 = np.array(L["head"]); hs = P["head_scale"]
    hl = ((v - H0) @ R) / hs
    G = MG.from_landmarks(L, hs)
    zm, e, h = MG.zm_e_h(hl[:, 0], hl[:, 1], G)
    band = (hl[:, 2] < zm) & (hl[:, 2] > zm - 0.004) & (e < 1.05)
    tent = np.clip(1 - np.abs(hl[:, 0]) / width, 0, 1) * height * band
    hl2 = hl.copy(); hl2[:, 2] += tent
    return (hl2 * hs) @ R.T + H0


def read_ply_v(path):
    with open(path, "rb") as f:
        h = b""
        while not h.endswith(b"end_header\n"):
            h += f.readline()
        nv = int(h.split(b"element vertex ")[1].split()[0])
        return np.frombuffer(f.read(nv * 12), "<f4").reshape(-1, 3).astype(np.float64)


def load_head(prefix, ply=None):
    J = json.load(open(prefix + "_landmarks.json"))
    p = ply or (prefix + "_hr.ply" if os.path.exists(prefix + "_hr.ply") else prefix + ".ply")
    return read_ply_v(p), J["landmarks"], J["params"]


if __name__ == "__main__":
    ply = sys.argv[sys.argv.index("--ply") + 1] if "--ply" in sys.argv else None
    v, L, P = load_head(sys.argv[1], ply)
    if "--plant" in sys.argv:
        v = plant_cusp(v, L, P)
    ok, out = check_lipline(v, L, P)
    print(f"  {'PASS' if ok else 'FAIL'} lipline      {out}")
