"""L1 FRAME ACCEPTANCE (layered-build.md). Each check names its evidence and confidence (engine-grounding G2).
A3: before use, these checks must FAIL on a known-bad frame (the v37r frame whose trunk sat mid-body).
A5: the person's critique of that frame ("the spine stops mid-back, the hips sit mid-body") is encoded as the
tail-emergence and side-proportion checks.

usage: python frame_checks.py <case_dir> <mesh_ver> <frame.json>    -> prints PASS/FAIL per check, exit 1 on a FAIL
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "review"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from project_mask import project  # noqa: E402
import frame as FR  # noqa: E402


def run(case, mv, fj):
    F = json.load(open(fj)); J = {k: np.array(v) for k, v in F["joints"].items()}; P = F["pose"]
    cam = json.load(open(os.path.join(case, "mesh", f"{mv}_camera.json")))
    M = json.load(open(os.path.join(case, "frame", "landmarks_measured.json")))["points"]
    S = json.load(open(os.path.join(case, "frame", "side_proportions.json")))["ratios"]
    proj = lambda p: project(np.atleast_2d(p), cam, 1728, 1152)[0][0]
    res = []
    # 1. paws (measured; horizontal pixel only - the vertical one encodes depth at a 4 deg camera, lesson J3)
    worst = max(abs(proj(J[k])[0] - M[k]["xy"][0]) for k in ("fpaw.R", "fpaw.L", "hpaw.R", "hpaw.L"))
    res.append(("paws_horizontal_px", worst <= 6, f"{worst:.1f} <= 6", "measured"))
    # 2. tail emergence (measured: tail pigment) - the person's "spine stops mid-back" critique
    fp = FR.axes(P["yaw"], P["pitch"])[3]
    tail_root = J["sacrum"] - fp * 0.025 * P["s"]
    tr = proj(tail_root); te = np.array(M["tail_emergence"]["xy"])
    ok_t = abs(tr[0] - te[0]) <= 30 and tr[1] <= te[1] + 5          # occluded root: at or above the emergence point
    res.append(("tail_root_vs_emergence", ok_t, f"dx {tr[0]-te[0]:+.0f} (|.|<=30), dy {tr[1]-te[1]:+.0f} (<= +5: at or above)", "measured (occlusion-aware)"))
    # 3. side proportion: trunk (shoulder-hip joints) / withers height (sourced 1.23 joint-to-joint; picked 1.34)
    trunk = float(np.linalg.norm(J["shoulder_c"] - J["hip_c"])); wh = float(J["withers"][2])
    r = trunk / wh
    res.append(("trunk_over_withers", 1.05 <= r <= 1.45, f"{r:.2f} in [1.05, 1.45] (Day&Jayne {320/259.8:.2f}, side ref {S['trunk_over_withers']})", "sourced + picked"))
    # 4. elbow height / withers height (picked on one side reference, slim breed: loose band, flagged)
    eh = float((J["elbow.R"][2] + J["elbow.L"][2]) / 2) / wh
    res.append(("elbow_over_withers", 0.30 <= eh <= 0.58, f"{eh:.2f} in [0.30, 0.58] (side ref {S['elbow_over_withers']})", "picked (flagged)"))
    # 5. the dorsal line: the spine lies below the photo's dorsal outline (soft tissue band unsourced: loose, flagged)
    gaps = []
    D = json.load(open(os.path.join(case, "frame", "landmarks_measured.json")))["dorsal_line"]["xy"]
    sp = [proj(J["withers"] + (J["sacrum"] - J["withers"]) * t) for t in np.linspace(0, 1, 30)]
    for x, y in D:
        near = min(sp, key=lambda q: abs(q[0] - x))
        if abs(near[0] - x) < 15:
            gaps.append(near[1] - y)
    ok = len(gaps) >= 5 and min(gaps) >= 10 and max(gaps) <= 120
    res.append(("spine_under_dorsal_line_px", ok, f"{len(gaps)} cols, gap {min(gaps) if gaps else 'n/a':.0f}..{max(gaps) if gaps else 'n/a':.0f} in [10, 120]" if gaps else "spine not under the dorsal line", "measured outline, unsourced band (flagged)"))
    # 6. proportions within the template's anatomical spread (one size factor; by construction) + size in range
    T = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "packs", "felid", "frame_template.json")))
    lo, hi = T["size_factor_range"]
    res.append(("size_factor_in_range", lo + 0.005 <= P["s"] <= hi - 0.005, f"{P['s']:.3f} strictly inside [{lo}, {hi}] (a pinned bound = a modelling conflict)", "sourced"))
    fails = 0
    for name, ok, detail, ev in res:
        print(f"  {'PASS' if ok else 'FAIL'} {name:28s} {detail}   [{ev}]")
        fails += not ok
    return fails


if __name__ == "__main__":
    sys.exit(1 if run(*sys.argv[1:4]) else 0)
