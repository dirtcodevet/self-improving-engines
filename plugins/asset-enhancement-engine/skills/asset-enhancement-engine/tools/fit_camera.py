"""Solve the reference camera from 2D points the BUILDER marked on the photo and the model's
3D landmarks (cv2.solvePnP + focal sweep). Prints per-point residuals - large residuals say
which part of the model is mis-proportioned, not that the camera is wrong.

usage: python fit_camera.py <model_landmarks.json> <ref_points.json> <out_camera.json> [pts,...]
"""
import json
import sys

import cv2
import numpy as np

lm_path, ref_path, out_path = sys.argv[1:4]
use = sys.argv[4].split(",") if len(sys.argv) > 4 else ["fpaw.R", "fpaw.L", "hpaw.R", "hpaw.L", "eye.R", "eye.L", "nose", "chin"]

L = json.load(open(lm_path))["landmarks"]
ref = json.load(open(ref_path))
W, H = ref["image_size"]
pts2d = ref["points"]


def model_point(name):
    if name.startswith("eye."):
        c, d = np.array(L[name]), np.array(L["eye_dir." + name[4:]])
        return c + d / np.linalg.norm(d) * L["eye_r"]  # cornea front = pupil in the photo
    if name.startswith("fpaw.") or name.startswith("hpaw."):
        p = np.array(L[name], float)
        return np.array([p[0], p[1] - 0.014, 0.0])  # toe front at ground contact
    if name == "tail_tip":
        return np.array(L["tail"][-1])
    return np.array(L[name], float)


names = [n for n in use if n in pts2d]
X = np.array([model_point(n) for n in names], np.float64)
x = np.array([pts2d[n] for n in names], np.float64)

best = None
for lens in np.arange(24, 401, 4):
    f = lens / 36.0 * W
    K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]])
    ok, rvec, tvec = cv2.solvePnP(X, x, K, None, flags=cv2.SOLVEPNP_SQPNP)
    if not ok:
        continue
    rvec, tvec = cv2.solvePnPRefineLM(X, x, K, None, rvec, tvec)
    proj, _ = cv2.projectPoints(X, rvec, tvec, K, None)
    err = np.linalg.norm(proj.reshape(-1, 2) - x, axis=1)
    rms = float(np.sqrt((err ** 2).mean()))
    Rm = cv2.Rodrigues(rvec)[0]
    C = (-Rm.T @ tvec).ravel()
    if C[2] < 0.005:  # camera under the floor is not a solution
        continue
    if best is None or rms < best[0]:
        best = (rms, lens, Rm, C, err)

rms, lens, Rm, C, err = best
# OpenCV cam axes (x right, y down, z fwd) -> Blender cam (x right, y up, -z fwd)
Mb = np.stack([Rm.T[:, 0], -Rm.T[:, 1], -Rm.T[:, 2]], axis=1)
json.dump({"lens": float(lens), "sensor_width": 36.0, "location": C.tolist(), "rot_matrix": Mb.tolist(),
           "rms_px": rms, "residuals_px": dict(zip(names, err.round(1).tolist()))}, open(out_path, "w"), indent=1)
print(f"lens {lens:.1f}mm  cam at {C.round(3)}  height {C[2]:.3f}m  rms {rms:.1f}px")
for n, e in zip(names, err):
    print(f"  {n:10s} {e:6.1f}px")
