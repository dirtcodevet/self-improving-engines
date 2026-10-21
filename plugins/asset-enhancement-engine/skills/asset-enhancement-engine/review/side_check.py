"""SECOND-ANGLE CHECK of a fitted frame (every 3-D fit is checked from an angle the fit did not see): the frame's
joints in a TRUE SIDE view (projected on the subject's sagittal plane, near side solid, far side thin), drawn over a
real side reference scaled withers-to-withers with the ground lines aligned and the trunk midpoints aligned.
Prints each picked reference point next to the frame's matching value in units of withers height.

The reference is another animal (and may be mid-stride): compare PROPORTIONS and joint HEIGHTS, not limb angles.
usage: python side_check.py <frame.json> <side_proportions.json> <gridded_side_image> <out.png> [near_side=L]
"""
import json
import sys

import cv2
import numpy as np


def main(fj, sj, img_path, out, near="L"):
    F = json.load(open(fj)); J = {k: np.array(v) * 1000 for k, v in F["joints"].items()}
    S = json.load(open(sj)); P = S["points"]
    img = cv2.imread(img_path)
    ground = P["ground_front"]; wh_ref = ground - P["withers"][1]; wh = J["withers"][2]
    k = wh_ref / wh                                                  # reference units per mm
    mid_ref = (P["point_of_shoulder"][0] + P["point_of_buttock"][0]) / 2
    mid = (J["shoulder_c"][1] + J["hip_c"][1]) / 2
    to = lambda p: (int(round(mid_ref + (p[1] - mid) * k)), int(round(ground - p[2] * k)))   # +y (backward) = image right
    far = "R" if near == "L" else "L"
    chains = [["scapula_top.{s}", "shoulder.{s}", "elbow.{s}", "wrist.{s}", "mcp.{s}", "fpaw.{s}"],
              ["hip.{s}", "knee.{s}", "hock.{s}", "mtp.{s}", "hpaw.{s}"], ["hock.{s}", "calcaneus.{s}"]]
    ov = img.copy()
    for sd, col, th in ((far, (160, 160, 255), 2), (near, (0, 0, 255), 4)):
        for ch in chains:
            pts = [to(J[c.format(s=sd)]) for c in ch if c.format(s=sd) in J]
            for a, b in zip(pts, pts[1:]): cv2.line(ov, a, b, col, th)
            for p in pts: cv2.circle(ov, p, th + 2, col, -1)
    sp = [to(J[k_]) for k_ in ("withers", "spine_mid", "sacrum")]
    for a, b in zip(sp, sp[1:]): cv2.line(ov, a, b, (0, 200, 0), 4)
    cv2.line(ov, to(J["sacrum"]), to(J["hip_c"]), (0, 200, 0), 2)
    for name, xy in P.items():
        if isinstance(xy, list):
            cv2.drawMarker(ov, tuple(int(v) for v in xy), (255, 255, 0), cv2.MARKER_CROSS, 22, 3)
            cv2.putText(ov, name, (int(xy[0]) + 8, int(xy[1]) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    cv2.line(ov, (0, ground), (img.shape[1], ground), (255, 255, 0), 1)
    cv2.putText(ov, "frame (near side red, far pink, spine green) vs reference points (cyan); scaled withers-to-withers",
                (10, img.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imwrite(out, ov)
    # heights in units of withers height: reference (skin landmarks) vs frame (joints) - definitions differ, flagged
    rows = [("shoulder joint / point of shoulder", (ground - P["point_of_shoulder"][1]) / wh_ref, J[f"shoulder.{near}"][2] / wh),
            ("elbow", (ground - P["elbow"][1]) / wh_ref, J[f"elbow.{near}"][2] / wh),
            ("hock (ref: hock point; frame: calcaneus tip)", (P["ground_hind_near"] - P["hock"][1]) / wh_ref, J[f"calcaneus.{near}"][2] / wh),
            ("hip joint / point of buttock", (ground - P["point_of_buttock"][1]) / wh_ref, J[f"hip.{near}"][2] / wh),
            ("croup / sacrum", (ground - P["croup_y"]) / wh_ref, J["sacrum"][2] / wh)]
    print(f"{'landmark (height / withers)':48s} {'ref':>6s} {'frame':>6s}")
    for n, r, f in rows:
        print(f"{n:48s} {r:6.3f} {f:6.3f}")
    print("knee height / withers (no reference point):", round(J[f"knee.{near}"][2] / wh, 3),
          "; femur from vertical (deg):", round(float(np.degrees(np.arctan2(J[f"hip.{near}"][1] - J[f"knee.{near}"][1], J[f"hip.{near}"][2] - J[f"knee.{near}"][2]))), 1))
    print("trunk pitch: shoulder joints", round(J["shoulder_c"][2]), "mm vs hip joints", round(J["hip_c"][2]), "mm above ground")


if __name__ == "__main__":
    main(*sys.argv[1:6])
