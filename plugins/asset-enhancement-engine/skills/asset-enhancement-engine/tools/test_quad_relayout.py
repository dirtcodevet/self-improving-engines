"""Proof of quad_relayout.py on a planted surface (build 13b). python engine/tools/test_quad_relayout.py -> json beside it.
A quad grid on a cylinder (radius 50 mm, 2.5 mm quads, a curved surface with a known form):
  1. a vertex (standing in for a pole) is sent 20 mm round the cylinder: it lands on its target (< 0.01 mm), every moved
     vertex lies on the old piecewise-linear surface (distance to the analytic cylinder within the old facets' own
     chord error), no flat triangle turns over, the patch's quads keep corner angles >= 45 deg;
  2. a grid line is laid onto a planted helix arc (a curve crossing the grid at 15 deg): every chain vertex within
     0.01 mm of the arc;
  1b. the same move by relayout_surface (no flat layout): the same four checks;
  3. a planted attribute linear in (angle, height) is read at the new places within the interpolation error of the
     old facets (< 1e-4 of its range); the uv corners resample the same way; outside the free set nothing moves.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import quad_relayout as QR  # noqa: E402


def cylinder(r=0.05, h=0.0025, nt=126, nz=60):
    th = np.arange(nt) * 2 * np.pi / nt * 0.5           # half a cylinder (an open sheet), 2.5 mm quads
    z = np.arange(nz) * h
    TH, Z = np.meshgrid(th, z, indexing="ij")
    V = np.c_[r * np.cos(TH.ravel()), r * np.sin(TH.ravel()), Z.ravel()]
    vid = lambda i, j: i * nz + j
    Q = np.array([[vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)] for i in range(nt - 1) for j in range(nz - 1)], np.int64)
    return V, Q, TH.ravel(), Z.ravel()


def main():
    out = {}; ok = True
    r = 0.05
    V, Q, TH, Z = cylinder()
    cen = np.array([r * np.cos(0.8), r * np.sin(0.8), 0.075])
    d = np.linalg.norm(V - cen, axis=1)
    free = d < 0.045
    pole = int(np.argmin(d))
    th_t = TH[pole] + 0.020 / r
    tgt = np.array([r * np.cos(th_t), r * np.sin(th_t), Z[pole]])
    R = QR.relayout(V, Q, free, points={pole: tgt})
    Vn = R["V"]
    rad_err = np.abs(np.linalg.norm(Vn[:, :2], axis=1) - r) * 1e3
    chord = r * (1 - np.cos(np.pi / 126 / 2)) * 1e3                     # the old facets' largest sag below the cylinder
    qa = QR.quality(Vn, Q, R["patch_faces"]); q0 = QR.quality(V, Q, R["patch_faces"])
    out["pole_move"] = {"target_err_mm": R["target_err_mm"], "flips": R["flips"], "param_flips": R["param_flips"], "outside": R["outside"],
                        "radius_err_mm_max": round(float(rad_err.max()), 5), "chord_mm": round(chord, 5),
                        "moved_outside_free_mm": round(float(np.abs(Vn[~free] - V[~free]).max() * 1e3), 9),
                        "quality_before": q0, "quality_after": qa}
    ok &= R["target_err_mm"] < 0.01 and R["flips"] == 0 and R["param_flips"] == 0 and rad_err.max() <= chord + 1e-6
    ok &= float(np.abs(Vn[~free] - V[~free]).max()) == 0.0 and qa["min_corner_deg_min"] >= 45
    # the same move by the surface walk (no flat layout)
    Rs = QR.relayout_surface(V, Q, free, points={pole: tgt})
    Vs = Rs["V"]; rad_s = np.abs(np.linalg.norm(Vs[:, :2], axis=1) - r) * 1e3
    qs = QR.quality(Vs, Q, Rs["patch_faces"])
    out["pole_move_surface_walk"] = {"target_err_mm": Rs["target_err_mm"], "flips": Rs["flips"], "radius_err_mm_max": round(float(rad_s.max()), 5),
                                     "moved_outside_free_mm": round(float(np.abs(Vs[~free] - V[~free]).max() * 1e3), 9), "quality_after": qs}
    ok &= Rs["target_err_mm"] < 0.01 and Rs["flips"] == 0 and rad_s.max() <= chord + 1e-6 and qs["min_corner_deg_min"] >= 45
    ok &= float(np.abs(Vs[~free] - V[~free]).max()) == 0.0
    # a grid line onto a helix arc crossing the grid at 15 deg
    j0 = 30
    line = np.array([i * 60 + j0 for i in range(20, 50)])
    s = np.linspace(0, 1, 200)
    th_a = TH[line[0]] + s * (TH[line[-1]] - TH[line[0]])
    z_a = Z[line[0]] + s * np.tan(np.radians(15)) * r * (TH[line[-1]] - TH[line[0]])
    arc = np.c_[r * np.cos(th_a), r * np.sin(th_a), z_a]
    free2 = np.zeros(len(V), bool)
    th_mid = (TH[line[0]] + TH[line[-1]]) / 2
    free2[(np.abs(TH - th_mid) < 0.8) & (np.abs(Z - Z[line[0]] - 0.006) < 0.05)] = True
    R2 = QR.relayout(V, Q, free2, chains=[(line, arc)])
    Vn2 = R2["V"]
    from scipy.spatial import cKDTree
    dch = cKDTree(np.r_[arc]).query(Vn2[line[1:-1]])[0] * 1e3
    out["chain_on_curve"] = {"max_mm_to_arc_samples": round(float(dch.max()), 4), "target_err_mm": R2["target_err_mm"], "flips": R2["flips"],
                             "quality_after": QR.quality(Vn2, Q, R2["patch_faces"])}
    ok &= R2["target_err_mm"] < 0.01 and R2["flips"] == 0
    # attributes: linear in (angle, height)
    f = 3.0 * TH + 40.0 * Z
    fn = QR.resample(R, f)
    th_new = np.arctan2(Vn[:, 1], Vn[:, 0])
    err = np.abs(fn - (3.0 * th_new + 40.0 * Vn[:, 2]))[free]
    rng = f.max() - f.min()
    UVc = np.stack([TH[Q], Z[Q]], 2)
    UVn = QR.resample_corners(R, Q, UVc)
    uv_err = max(float(np.abs(UVn[k, c] - [th_new[v], Vn[v, 2]]).max()) for k in R["patch_faces"][:2000] for c, v in enumerate(Q[k]) if free[v])
    out["attributes"] = {"linear_err_over_range": float(err.max() / rng), "uv_err": uv_err}
    ok &= err.max() / rng < 1e-4 and uv_err < 1e-4
    out["PASS"] = bool(ok)
    json.dump(out, open(os.path.join(HERE, "test_quad_relayout.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
