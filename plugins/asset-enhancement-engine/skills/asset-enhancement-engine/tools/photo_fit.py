"""Photo constraints for a case spec in a frozen camera:
 1) ground-contact landmarks (paws) -> exact 3D positions: camera ray through the photo pixel hits z=0.
 2) head pose (centre xyz, yaw, pitch, scale) fitted to eye/nose/chin/ear-tip pixels with a soft prior that
    keeps the centre near a 3D reference's head (depth along the camera ray is otherwise unconstrained).
usage: python photo_fit.py <case_dir> [prior_weight_px_per_mm=3]
Prints the fitted values to paste into the spec (case facts stay in the case)."""
import importlib.util, json, os, sys
import numpy as np
from scipy.optimize import minimize

case = sys.argv[1]
wprior = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
cam = json.load(open(os.path.join(case, "camera_frozen.json")))
pts = json.load(open(os.path.join(case, "ref_points.json")))
Wimg, Himg = pts["image_size"]
f = cam["lens"] / cam["sensor_width"] * Wimg
C = np.array(cam["location"]); Mb = np.array(cam["rot_matrix"])


def project(X):
    pc = (np.atleast_2d(X) - C) @ Mb
    z = -pc[:, 2]
    return np.stack([f * pc[:, 0] / z + Wimg / 2, Himg / 2 - f * pc[:, 1] / z], 1)


def ground_hit(px):
    d_cam = np.array([(px[0] - Wimg / 2) / f, -(px[1] - Himg / 2) / f, -1.0])
    d = Mb @ d_cam
    t = -C[2] / d[2]
    return C + t * d


print("paw toe-front ground points (landmark = toe front; paw centre is ~14 mm behind):")
for k in ("fpaw.R", "fpaw.L", "hpaw.R", "hpaw.L"):
    g = ground_hit(pts["points"][k])
    print(f"  {k}: {np.round(g, 4).tolist()}")

spec_p = os.path.join(case, "spec.py")
spec_m = importlib.util.spec_from_file_location("casespec", spec_p)
S = importlib.util.module_from_spec(spec_m); sys.argv_save = sys.argv; spec_m.loader.exec_module(S)
P0 = dict(S.P)
names = ["eye.R", "eye.L", "nose", "chin", "ear_tip.R", "ear_tip.L"]
target = np.array([pts["points"][n] for n in names])
prior_c = np.array(P0["head_center"])


def lm(x):
    P = dict(P0, head_center=tuple(x[:3]), head_yaw_deg=x[3], head_pitch_deg=x[4], head_scale=x[5])
    _, L = S.build(P)
    out = []
    for n in names:
        if n.startswith("eye."):
            out.append(np.array(L[n]) + np.array(L["eye_dir." + n[4:]]) * L["eye_r"])
        else:
            out.append(np.array(L[n]))
    return np.array(out)


def cost(x):
    e = np.linalg.norm(project(lm(x)) - target, axis=1)
    return (e ** 2).sum() + (wprior * 1000 * np.linalg.norm(x[:3] - prior_c)) ** 2 * 0.05


x0 = np.array([*P0["head_center"], P0["head_yaw_deg"], P0["head_pitch_deg"], P0["head_scale"]])
r = minimize(cost, x0, method="Nelder-Mead", options=dict(maxiter=4000, xatol=1e-6, fatol=1e-3))
e = np.linalg.norm(project(lm(r.x)) - target, axis=1)
print("head fit: centre", np.round(r.x[:3], 4).tolist(), "yaw", round(r.x[3], 2), "pitch", round(r.x[4], 2), "scale", round(r.x[5], 4))
print("  moved from reference head by", round(np.linalg.norm(r.x[:3] - prior_c) * 1000, 1), "mm")
print("  residuals px:", dict(zip(names, np.round(e, 1).tolist())))

# 3) paws: slide each paw on the floor so its toe-front projects onto the photo pixel, with a prior to the
#    reference's paw (a low camera makes pure ray-plane hits useless: ~2 cm depth per pixel).
meas = json.load(open(os.path.join(case, "anatomy_measured.json")))
key = {"fpaw.R": "f.R", "fpaw.L": "f.L", "hpaw.R": "h.R", "hpaw.L": "h.L"}
print("paw centres fitted on the floor (prior = reference paw, 1 px per mm):")
for k, mk in key.items():
    pr = np.array(meas["legs"][mk]["paw_xy"])
    tgt = np.array(pts["points"][k])

    def pc_(xy):
        return np.linalg.norm(project(np.array([xy[0], xy[1] - 0.014, 0.0]))[0] - tgt) ** 2 + (1000 * np.linalg.norm(xy - pr)) ** 2 * 1.0

    rr = minimize(pc_, pr, method="Nelder-Mead", options=dict(xatol=1e-6, fatol=1e-4, maxiter=2000))
    res_px = np.linalg.norm(project(np.array([rr.x[0], rr.x[1] - 0.014, 0.0]))[0] - tgt)
    print(f"  {k}: centre {np.round(rr.x, 4).tolist()}  moved {np.linalg.norm(rr.x - pr)*1000:.1f} mm  residual {res_px:.1f} px")
