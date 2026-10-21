"""SELF-TEST of the frame fit on a KNOWN pose (skill A3, J5): build a frame with a known anatomical pose, render its
silhouette and landmarks through the case camera into a synthetic case folder, run the same frame_fit, and report how
well the known joints are recovered. If the fit cannot recover a pose it was handed, the METHOD is broken - tuning it
on the real photo would only chase that error.

usage: python frame_fit_selftest.py <case_dir> <mesh_ver> <work_dir>
"""
import json
import os
import shutil
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "tools"))
from project_mask import project  # noqa: E402
import frame as FR  # noqa: E402
import frame_fit  # noqa: E402

W, H = 1728, 1152


def main(case, mv, work):
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(os.path.join(work, "mesh")); os.makedirs(os.path.join(work, "frame"))
    shutil.copy(os.path.join(case, "mesh", f"{mv}_camera.json"), os.path.join(work, "mesh", f"{mv}_camera.json"))
    cam = json.load(open(os.path.join(case, "mesh", f"{mv}_camera.json")))
    L = json.load(open(os.path.join(case, "mesh", f"{mv}_landmarks.json")))
    T, B = FR.load_template(os.path.join(HERE, "..", "packs", "felid", "frame_template.json"))
    real = json.load(open(os.path.join(case, "frame", "frame.json")))["pose"]
    # the KNOWN pose: anatomical standing prior, adult size, placed where the cat stands
    P = dict(s=1.0, trunk=0.32, scap=frame_fit.SCAP_PRIOR, pelvis=0.052, hip_c=np.array(real["hip_c"]), yaw=real["yaw"], pitch=0.0,
             w_shoulder=0.055, w_hip=0.060)
    for sd in "RL":
        P[f"fore.{sd}"] = dict(frame_fit.PRIOR["fore"]); P[f"hind.{sd}"] = dict(frame_fit.PRIOR["hind"])
    P["hip_c"] = P["hip_c"].copy(); P["hip_c"][2] = 0.0
    # a known pose must STAND: tilt the trunk until the fore and hind paws are at the same height (the prior angles
    # alone left the forepaws 42 mm in the air - the first self-test was invalid)
    for _ in range(60):
        Jt = FR.build(P, B)
        dz = (Jt["fpaw.R"][2] + Jt["fpaw.L"][2]) / 2 - (Jt["hpaw.R"][2] + Jt["hpaw.L"][2]) / 2
        P["pitch"] -= dz / max(P["trunk"], 1e-3)
    J = FR.build(P, B)
    J0 = FR.build(P, B)
    lift = -min(J0[k][2] for k in ("fpaw.R", "fpaw.L", "hpaw.R", "hpaw.L")) + 0.006       # put the paws on the ground
    P["hip_c"][2] += lift; J = FR.build(P, B)
    proj = lambda p: project(np.atleast_2d(p), cam, W, H)[0]
    # synthetic silhouette: thick capsules (trunk ~ soft tissue, limbs thinner), drawn in the image
    mask = np.zeros((H, W), np.uint8)
    rad = lambda a, b: 0.050 if ("sacrum" in a or "withers" in b or "spine" in a) else (0.030 if a.startswith(("hip.R", "shoulder.R")) and b.endswith("L") else 0.016)
    for a, b, A, Bp in FR.segments(J):
        r = rad(a, b)
        for t in np.linspace(0, 1, 25):
            c = A + (Bp - A) * t
            u = proj(c)[0]; u2 = proj(c + np.array([0, 0, r]))[0]
            cv2.circle(mask, (int(u[0]), int(u[1])), max(int(np.linalg.norm(u2 - u)), 2), 255, -1)
    cv2.imwrite(os.path.join(work, "ref_mask.png"), mask)
    cv2.imwrite(os.path.join(work, "ref.jpg"), cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))
    paws = {k: proj(J[k])[0].tolist() for k in ("fpaw.R", "fpaw.L", "hpaw.R", "hpaw.L")}
    json.dump(dict(points=paws), open(os.path.join(work, "ref_points.json"), "w"))
    fp = FR.axes(P["yaw"], P["pitch"])[3]
    tail_px = proj(J["sacrum"] - fp * 0.025 * P["s"])[0]
    top = [[int(x), int(np.where(mask[:, x])[0].min())] for x in range(0, W, 10) if mask[:, x].any()]
    sx = sorted([proj(J["withers"])[0][0], proj(J["sacrum"])[0][0]])
    dorsal = [p for p in top if sx[0] <= p[0] <= sx[1]]
    json.dump(dict(points=dict(tail_emergence=dict(xy=tail_px.tolist()), **{k: dict(xy=v) for k, v in paws.items()}),
                   dorsal_line=dict(xy=dorsal)), open(os.path.join(work, "frame", "landmarks_measured.json"), "w"))
    wh = J["withers"][2]
    side = dict(ratios=dict(trunk_over_withers=float(np.linalg.norm(J["shoulder_c"] - J["hip_c"]) / wh),
                            croup_above_hip_over_withers=float(P["pelvis"] / wh),
                            shoulder_joint_over_withers=float((J["shoulder.R"][2] + J["shoulder.L"][2]) / 2 / wh)))
    json.dump(side, open(os.path.join(work, "frame", "side_proportions.json"), "w"))
    # the "reference" landmarks = the truth (a perfect reference) for init and paw depth
    Lt = dict(L); Lt["landmarks"] = dict(L["landmarks"])
    for k in ("fpaw.R", "fpaw.L", "hpaw.R", "hpaw.L", "shoulder.R", "shoulder.L", "hip.R", "hip.L"):
        Lt["landmarks"][k] = J[k].tolist()
    Lt["landmarks"]["tail"] = [(J["sacrum"] - fp * 0.025).tolist()] + L["landmarks"]["tail"][1:]
    json.dump(Lt, open(os.path.join(work, "mesh", f"{mv}_landmarks.json"), "w"))
    frame_fit.main(work, mv, os.path.join(work, "fit"))
    F = json.load(open(os.path.join(work, "fit", "frame.json")))
    err = {k: float(np.linalg.norm(np.array(F["joints"][k]) - J[k]) * 1000) for k in J}
    worst = sorted(err.items(), key=lambda kv: -kv[1])[:8]
    print("SELFTEST truth paw heights mm", [round(J[k][2] * 1000, 1) for k in ("fpaw.R", "fpaw.L", "hpaw.R", "hpaw.L")], "pitch deg", round(np.degrees(P["pitch"]), 1))
    print("SELFTEST recovered size", round(F["pose"]["s"], 3), "(true 1.0); trunk", round(F["report"]["trunk_mm"]), "(true 320)")
    print("SELFTEST joint error mm: median", round(float(np.median(list(err.values()))), 1), "worst", [(k, round(v)) for k, v in worst])
    print("SELFTEST pinned at bounds:", F["report"]["pinned_at_bounds"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
