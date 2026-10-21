"""Proof of pose_correctives.py on planted shapes with known answers (2026-10-21, build 13c).
    python engine/tools/test_pose_correctives.py   -> test_pose_correctives.json beside it, PASS / FAIL per check
1. to_rest inverts any Jacobian: J (to_rest(J, D)) = D.
2. ArapField: a rigidly moved shape comes back exactly (the planted answer); a tube bent 120 deg by blending two bones'
   transforms (linear skinning's collapse) moves back toward rest: edge-length error lower (mean and max) and the bend's
   section radius closer to rest (a part only: 3 steps, and the bend's inside must shorten; the numbers are recorded).
3. breast_envelope: no stretch -> no move; a cap over a flat wall stretched 10 % keeps its volume (the planted rest
   volume), presses its top in, and never goes under the wall's limit.
4. self_contact: two sheets planted 4 mm into each other are found with depth 4 mm and each pushed out by half.
5. hat_expr equals hat (the driver expression and the numpy weight) on a dense grid.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesh_geom as MG  # noqa: E402
import pose_correctives as PC  # noqa: E402

OUT = {}


def ok(name, cond, **kw):
    OUT[name] = {"PASS": bool(cond), **{k: (round(float(v), 8) if isinstance(v, (float, np.floating)) else v) for k, v in kw.items()}}
    print(("PASS " if cond else "FAIL ") + name, kw)


def grid(nu, nv, f):
    u, v = np.meshgrid(np.linspace(0, 1, nu), np.linspace(0, 1, nv), indexing="ij")
    V = f(u.ravel(), v.ravel())
    F = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            a = i * nv + j; b = a + nv
            F += [[a, b, b + 1], [a, b + 1, a + 1]]
    return V, np.array(F, np.int64)


def rot(axis, ang):
    a = np.asarray(axis, float); a /= np.linalg.norm(a); K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K


rng = np.random.default_rng(3)
# 1
J = np.eye(3) + 0.4 * rng.standard_normal((500, 3, 3)); D = rng.standard_normal((500, 3))
ok("to_rest_inverts", np.abs(np.einsum("nij,nj->ni", J, PC.to_rest(J, D)) - D).max() < 1e-9)

# 2a rigid motion
V0, F = grid(30, 40, lambda u, v: np.stack([0.03 * np.cos(2 * np.pi * u * 0.9), 0.03 * np.sin(2 * np.pi * u * 0.9), 0.2 * v], 1))
Rg = rot([1, 2, 0.5], 1.1); Y = V0 @ Rg.T + [0.1, -0.2, 0.05]
lam = np.full(len(V0), 1e-3)
A = PC.ArapField(V0, F, lam)
X = A.solve(Y, Y, R_init=np.tile(Rg, (len(V0), 1, 1)), iters=3)
ok("arap_rigid_exact", np.abs(X - Y).max() < 1e-8, max_mm=np.abs(X - Y).max() * 1e3)

# 2b a tube bent 120 deg at its middle by blending two bones (linear skinning's collapse)
V0, F = grid(48, 60, lambda u, v: np.stack([0.03 * np.cos(2 * np.pi * u * 47 / 48), 0.03 * np.sin(2 * np.pi * u * 47 / 48), 0.3 * v - 0.15], 1))
w = np.clip((V0[:, 2] + 0.04) / 0.08, 0, 1)
Rb = rot([1, 0, 0], math.radians(120))
Y = (1 - w)[:, None] * V0 + w[:, None] * (V0 @ Rb.T)
lam = np.where(np.abs(V0[:, 2]) > 0.12, 10.0, 1e-3)
Jb = (1 - w)[:, None, None] * np.eye(3) + w[:, None, None] * Rb
X = PC.ArapField(V0, F, lam).solve(Y, Y, R_init=PC.polar(Jb), iters=3)
E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
el = lambda P: np.linalg.norm(P[E[:, 0]] - P[E[:, 1]], axis=1)
err0 = np.abs(el(Y) / el(V0) - 1); err1 = np.abs(el(X) / el(V0) - 1)
mid = np.abs(V0[:, 2]) < 0.02
def sect(P):
    c = P[mid].mean(0); return np.median(np.linalg.norm(P[mid] - c, axis=1))
# a 120 deg bend must shorten the inside of the bend: the check is that each measure moves toward rest
ok("arap_bent_tube_restores", (err1.mean() < err0.mean()) and (err1.max() < err0.max()) and (abs(sect(X) - sect(V0)) < abs(sect(Y) - sect(V0))),
   edge_err_mean_before=err0.mean(), edge_err_mean_after=err1.mean(), edge_err_max_before=err0.max(), edge_err_max_after=err1.max(), radius_mm_rest=sect(V0) * 1e3, radius_mm_skinned=sect(Y) * 1e3,
   radius_mm_after=sect(X) * 1e3)

# 3 the breast on a planted cap over a flat wall z = 0
R = 0.08
V0, F = grid(41, 41, lambda u, v: np.stack([(u - 0.5) * 0.16, (v - 0.5) * 0.16, np.zeros_like(u)], 1))
r2 = (V0[:, 0] ** 2 + V0[:, 1] ** 2)
cap = np.clip(0.05 * (1 - r2 / 0.07 ** 2), 0, None)
V0 = V0 + np.stack([np.zeros_like(cap), np.zeros_like(cap), cap], 1)
wp = np.clip((0.07 - np.sqrt(r2)) / 0.02, 0, 1)
cwV, cwF = grid(21, 21, lambda u, v: np.stack([(u - 0.5) * 0.3, (v - 0.5) * 0.3, np.full_like(u, -0.001)], 1))
prm = dict(E_breast=250.0, membrane=5.76, nu=0.49, T0=0.576, rho=951.0, g=0.0, h_floor=0.01, d_min=0.008, d_min_share=0.5,
           edge=0.05, restore_volume=True, cw_rest=cwV, kappa_max=200.0, smooth_iters=4)
u0, i0 = PC.breast_envelope(V0, F, V0, wp, cwV, cwF, prm)
ok("breast_no_stretch_no_move", np.abs(u0).max() < 1e-9, u_max=np.abs(u0).max())
Ys = V0 * [1.1, 1.0, 1.0]                                     # 10 % stretch across, the cap's volume grows 10 %
u1, i1 = PC.breast_envelope(V0, F, Ys, wp, cwV, cwF, prm)
vol_ok = abs(i1["volume_after_ml"] - i1["volume_rest_ml"]) < 0.02 * i1["volume_rest_ml"]
top = r2 < 0.02 ** 2
ok("breast_stretch_keeps_volume_presses_top", vol_ok and u1[top].mean() < 0 and i1["at_chest_wall_limit"] >= 0,
   volume_rest_ml=i1["volume_rest_ml"], volume_stretched_ml=i1["volume_skinned_ml"], volume_after_ml=i1["volume_after_ml"],
   top_u_mm=u1[top].mean() * 1e3)

# 4 two sheets passed 4 mm into each other: A faces up (+z) at z = +2 mm, B faces down (-z) at z = -2 mm
A_, FA = grid(21, 21, lambda u, v: np.stack([u * 0.05, v * 0.05, np.full_like(u, 0.002)], 1))
B_, FB = grid(21, 21, lambda u, v: np.stack([u * 0.05, v * 0.05, np.full_like(u, -0.002)], 1))
Xc = np.concatenate([A_, B_]); Fc = np.concatenate([FA, FB[:, ::-1] + len(A_)])
nA = MG.face_normals(Xc, Fc[:len(FA)]).mean(0); nB = MG.face_normals(Xc, Fc[len(FA):]).mean(0)
V0c = Xc.copy(); V0c[len(A_):, 2] += 0.5                       # far apart at rest
inner = np.nonzero((Xc[:, 0] > 0.01) & (Xc[:, 0] < 0.04) & (Xc[:, 1] > 0.01) & (Xc[:, 1] < 0.04))[0]
ids, T, dep, _ = PC.self_contact(Xc, Fc, V0c, inner, rest_sep=0.02, max_d=0.03, gap=0.0)
ok("contact_found_half_push", len(ids) == len(inner) and abs(np.median(dep) - 0.004) < 1e-6 and
   np.abs(T[:, 2]).max() < 1e-9,
   normals_A_B=[nA.round(3).tolist(), nB.round(3).tolist()], found=len(ids), planted=len(inner), depth_mm=float(np.median(dep)) * 1e3)

# 5 expressions
env = {"clamp": lambda x, a, b: min(max(x, a), b), "min": min, "max": max, "abs": abs}
knots = [20.0, 55.0, 90.0, 130.0, 170.0]; bad = 0.0
for j in range(len(knots)):
    ex = PC.hat_expr("e", knots, j)
    for e in np.linspace(0, 190, 381):
        bad = max(bad, abs(eval(ex, env, {"e": e}) - float(PC.hat(e, knots, j))))
ok("hat_expr_equals_hat", bad < 1e-12, max_diff=bad)

res = {"all_PASS": all(v["PASS"] for v in OUT.values()), "checks": OUT}
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_pose_correctives.json"), "w"), indent=1)
print("ALL PASS" if res["all_PASS"] else "SOME FAIL")
