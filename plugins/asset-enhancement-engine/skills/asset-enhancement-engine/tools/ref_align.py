"""Align a generated 3D reference mesh (arbitrary frame/scale) to the case's world frame so that, seen through
the case camera, its silhouette matches the photo mask. Grounded: after every transform the lowest point is
put on z=0. Search: yaw grid, then Nelder-Mead over (yaw, pitch, roll, log-scale, tx, ty).
Writes <out.json> with a 4x4 matrix (reference-local -> world) and the aligned IoU.

usage: python ref_align.py <ref.ply> <camera.json> <mask.png> <out.json> [target_height_m]
"""
import json, sys
import cv2
import numpy as np
from PIL import Image
from scipy.optimize import minimize

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "..", "checks"))
from checks import read_ply  # noqa: E402

ref_p, cam_p, mask_p, out_p = sys.argv[1:5]
target_h = float(sys.argv[5]) if len(sys.argv) > 5 else 0.33
v, f = read_ply(ref_p)
v = v - v.mean(0)
cam = json.load(open(cam_p))
mask_full = np.asarray(Image.open(mask_p).convert("L")) > 127
H0, W0 = mask_full.shape
S = 0.4
W, H = int(W0 * S), int(H0 * S)
mask = cv2.resize(mask_full.astype(np.uint8), (W, H), interpolation=cv2.INTER_AREA) > 0
fpx = cam["lens"] / cam["sensor_width"] * W
C = np.array(cam["location"]); Mb = np.array(cam["rot_matrix"])
sub = f[:: max(len(f) // 60000, 1)]


def R(yaw, pitch, roll):
    cy, sy, cp, sp, cr, sr = np.cos(yaw), np.sin(yaw), np.cos(pitch), np.sin(pitch), np.cos(roll), np.sin(roll)
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Ry = np.array([[cr, 0, sr], [0, 1, 0], [-sr, 0, cr]])
    return Rz @ Rx @ Ry


def place(x, base_scale):
    yaw, pitch, roll, ls, tx, ty = x
    M = R(yaw, pitch, roll) * (base_scale * np.exp(ls))
    w = v @ M.T
    w[:, 0] += tx; w[:, 1] += ty; w[:, 2] -= w[:, 2].min()
    return w, M


def silhouette(w):
    pc = (w - C) @ Mb
    z = -pc[:, 2]
    ok = z > 1e-3
    u = fpx * pc[:, 0] / np.maximum(z, 1e-3) + W / 2
    vv = H / 2 - fpx * pc[:, 1] / np.maximum(z, 1e-3)
    img = np.zeros((H, W), np.uint8)
    tri = np.stack([u, vv], 1)[sub].astype(np.int32)
    tri = tri[ok[sub].all(1)]
    for t in tri:   # per-triangle: cv2.fillPoly(list) uses even-odd -> overlapping tris punch holes
        cv2.fillConvexPoly(img, t, 1)
    return img > 0


def iou(x, base_scale):
    s = silhouette(place(x, base_scale)[0])
    return (s & mask).sum() / max((s | mask).sum(), 1)


ext = v.max(0) - v.min(0)
best = None
for up_axis in range(3):          # which local axis is "up" is unknown: try each as world Z
    perm = [a for a in range(3) if a != up_axis] + [up_axis]
    vv_ = v[:, perm]
    for flip in (1, -1):
        vv2 = vv_ * np.array([1, flip, flip])
        base = target_h / (vv2[:, 2].max() - vv2[:, 2].min())
        v_backup = v
        v = vv2
        for yaw in np.radians(np.arange(0, 360, 15)):
            x0 = np.array([yaw, 0, 0, 0, 0.0, 0.0])
            sc = iou(x0, base)
            if best is None or sc > best[0]:
                best = (sc, x0, base, perm, flip)
        v = v_backup
sc, x0, base, perm, flip = best
v = v[:, perm] * np.array([1, flip, flip])
print(f"coarse: IoU {sc:.3f} yaw {np.degrees(x0[0]):.0f} up_axis perm {perm} flip {flip}")
res = minimize(lambda x: -iou(x, base), x0, method="Nelder-Mead",
               options=dict(initial_simplex=np.array([x0] + [x0 + d for d in np.diag([0.2, 0.08, 0.08, 0.15, 0.03, 0.03])]),
                            maxiter=600, xatol=1e-4, fatol=1e-4))
x = res.x
w, M = place(x, base)
full = np.eye(4)
P = np.zeros((3, 3)); P[np.arange(3), perm] = 1; P = np.diag([1, flip, flip]) @ P
full[:3, :3] = M @ P
cen = __import__("checks").read_ply(ref_p)[0].mean(0)
full[:3, 3] = -full[:3, :3] @ cen + np.array([x[4], x[5], 0])
full[2, 3] -= (read_ply(ref_p)[0] @ full[:3, :3].T + full[:3, 3])[:, 2].min()
fin = iou(x, base)
json.dump({"matrix": full.tolist(), "iou": float(fin), "yaw_deg": float(np.degrees(x[0])), "scale": float(base * np.exp(x[3]))},
          open(out_p, "w"), indent=1)
print(f"aligned: IoU {fin:.4f}  yaw {np.degrees(x[0]):.1f}  pitch {np.degrees(x[1]):.1f}  roll {np.degrees(x[2]):.1f}  "
      f"scale {base*np.exp(x[3]):.4f}  height {np.ptp((read_ply(ref_p)[0] @ full[:3,:3].T)[:,2]):.3f} m")
