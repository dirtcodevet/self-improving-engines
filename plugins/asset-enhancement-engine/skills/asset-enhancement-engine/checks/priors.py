"""PRIORS check: every dimension the photo cannot measure must sit inside its anatomical prior (engine/priors.json).
Measured on the fur envelope (<prefix>_env.ply) in the head frame from the landmarks; the temple outline through
the photo camera (review/project_mask + head_outline). usage: python priors.py <case_dir> <mesh_prefix>
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "review"))
import checks as C  # noqa: E402

PRI = json.load(open(os.path.join(HERE, "..", "priors.json")))


def head_measures(pre):
    v, f = C.read_ply(pre + "_env.ply")
    J = json.load(open(pre + "_landmarks.json")); L = J["landmarks"]
    R = np.array(L["head_R"]); fwd = R @ np.array([0, -1.0, 0]); up = R @ np.array([0, 0, 1.0]); lat = R @ np.array([1.0, 0, 0])
    apex = [np.array(L[f"eye.{s}"]) + np.array(L[f"eye_dir.{s}"]) * L["eye_r"] for s in "RL"]
    o = (apex[0] + apex[1]) / 2
    E = abs((apex[1] - apex[0]) @ lat)
    p = np.stack([(v - o) @ lat, (v - o) @ fwd, (v - o) @ up], 1)
    near = (np.abs(p[:, 0]) < 1.6 * E) & (p[:, 1] > -2.2 * E) & (p[:, 2] > -2.5 * E) & (p[:, 2] < 2.6 * E)
    q = p[near]; mid = q[np.abs(q[:, 0]) < 0.06 * E]
    nose = mid[np.argmax(mid[:, 1])]
    band = q[(q[:, 2] < 0.0) & (q[:, 2] > -0.9 * E) & (q[:, 1] > -0.9 * E)]
    W = band[:, 0].max() - band[:, 0].min()
    top = mid[(mid[:, 1] < 0.2 * E) & (mid[:, 1] > -1.0 * E)][:, 2].max()
    fs = []
    for z in np.linspace(0.1 * E, top - 0.05 * E, 8):
        b = mid[np.abs(mid[:, 2] - z) < 0.03 * E]
        if len(b):
            fs.append((b[:, 1].max(), z))
    fs = np.array(fs); k = np.polyfit(fs[:, 1], fs[:, 0], 1)[0]
    ch = mid[(mid[:, 1] > 0.0) & (mid[:, 2] < nose[2] - 0.1 * E)]
    lowfront = ch[ch[:, 1] > ch[:, 1].max() - 0.25 * E]; chin = lowfront[np.argmin(lowfront[:, 2])]
    return {"muzzle_projection_over_width": float(nose[1] / W), "forehead_slope_deg": float(np.degrees(np.arctan2(1.0, -k))),
            "chin_behind_nose_over_width": float((nose[1] - chin[1]) / W), "_W_head_mm": float(W * 1000), "_E_mm": float(E * 1000),
            "_nose_ahead_mm": float(nose[1] * 1000)}


def temple(case, pre):
    import cv2
    import project_mask as PM
    import head_outline as HO
    v, f = C.read_ply(pre + "_env.ply")
    cam = json.load(open(os.path.join(case, "camera_frozen.json")))
    m = PM.mask(v, f, cam)
    tmp = pre + "_envmask_tmp.png"; cv2.imwrite(tmp, m)
    out, _, _ = HO.measure(case, tmp)
    os.remove(tmp)
    return {"temple_bulge_min_px": float(min(out["model"]["R"]["bulge_min"], out["model"]["L"]["bulge_min"]))}


if __name__ == "__main__":
    case, pre = sys.argv[1], sys.argv[2]
    m = head_measures(pre); m.update(temple(case, pre))
    allok = True
    for k, spec in PRI["head"].items():
        if k not in m:
            print(f"  ---- {k:32s} not measured yet"); continue
        lo, hi = spec["range"]; ok = lo <= m[k] <= hi; allok &= ok
        print(f"  {'PASS' if ok else 'FAIL'} {k:32s} {m[k]:8.3f}  prior [{lo}, {hi}] target {spec['target']}")
    print("  (head width", round(m["_W_head_mm"], 1), "mm, E", round(m["_E_mm"], 1), "mm, nose ahead of the corneas", round(m["_nose_ahead_mm"], 1), "mm)")
    sys.exit(0 if allok else 1)
