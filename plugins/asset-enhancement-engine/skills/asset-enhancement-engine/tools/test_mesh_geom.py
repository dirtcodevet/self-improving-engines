"""Proof of mesh_geom.py on planted answers (A10). python engine/tools/test_mesh_geom.py  -> test_mesh_geom.json beside it.
  closest point   random points round random triangles (every Voronoi region hit) against a brute-force answer (the
                  triangle sampled on a 400 x 400 barycentric grid, then refined): distance never larger than the brute
                  force, the point on the triangle, the barycentrics reproduce it
  meshes          a UV sphere R = 0.1 m: vertex normals within 1 deg of radial; mean curvature 1/R (median within 1 %);
                  the Laplacian kills constants; clamp leaves no negative weight; closest_on_mesh and MeshProj equal
                  a brute force over every triangle for points off the sphere
  folds           two planes meeting at a planted 37 deg turn: dihedral_edges reads 37 deg on the hinge, 0 elsewhere
  polyline        poly_dist to a unit square: known distances"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mesh_geom as MG  # noqa: E402


def sphere(R=0.1, nu=96, nv=48):
    th = np.linspace(0, 2 * np.pi, nu, endpoint=False); ph = np.linspace(0, np.pi, nv + 1)[1:-1]
    TH, PH = np.meshgrid(th, ph, indexing="ij")
    V = np.c_[np.cos(TH).ravel() * np.sin(PH).ravel(), np.sin(TH).ravel() * np.sin(PH).ravel(), np.cos(PH).ravel()] * R
    V = np.vstack([V, [[0, 0, R], [0, 0, -R]]]); top, bot = len(V) - 2, len(V) - 1
    idx = np.arange(nu * (nv - 1)).reshape(nu, nv - 1); F = []
    for i in range(nu):
        j = (i + 1) % nu
        for k in range(nv - 2):
            F += [[idx[i, k], idx[j, k], idx[j, k + 1]], [idx[i, k], idx[j, k + 1], idx[i, k + 1]]]
        F += [[top, idx[j, 0], idx[i, 0]], [bot, idx[i, -1], idx[j, -1]]]
    return V, np.array(F, np.int64)[:, [0, 2, 1]]           # outward


def brute_tri(p, a, b, c, n=400):
    u, v = np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, n)); m = u + v <= 1
    Q = a + u[m, None] * (b - a) + v[m, None] * (c - a)
    return np.linalg.norm(Q - p, axis=1).min()


def main():
    rng = np.random.default_rng(7); out = {}; ok = True
    # closest point
    worst = 0.0; on_tri = 0.0; bary_err = 0.0; regions = set()
    for t in range(300):
        a, b, c = rng.normal(size=(3, 3)); p = (a + b + c) / 3 + rng.normal(size=3) * 1.5
        X, W = MG.closest_on_triangles(p[None], a[None], b[None], c[None], bary=True)
        d = np.linalg.norm(X[0] - p); bf = brute_tri(p, a, b, c)
        worst = max(worst, d - bf)                                     # never farther than the sampled answer
        bary_err = max(bary_err, float(np.abs(W[0] @ np.stack([a, b, c]) - X[0]).max()))
        on_tri = max(on_tri, float(-W[0].min()))
        regions.add(tuple(np.round(W[0] > 1e-9).astype(int)))
    out["closest_point"] = {"triangles": 300, "max_excess_over_brute_force": worst, "bary_reproduces_point_max": bary_err,
                            "most_negative_bary": -on_tri, "regions_hit": len(regions)}
    ok &= worst <= 1e-12 and bary_err < 1e-12 and on_tri < 1e-12 and len(regions) == 7
    # sphere
    R = 0.1; V, F = sphere(R)
    N = MG.vertex_normals(V, F); ang = np.degrees(np.arccos(np.clip((N * V / R).sum(1), -1, 1)))
    H, A = MG.mean_curvature(V, F)
    Lm, _ = MG.cot_laplacian(V, F); Lc, _ = MG.cot_laplacian(V, F, clamp=True)
    off = Lc - __import__("scipy").sparse.diags(Lc.diagonal())
    P = rng.normal(size=(400, 3)); P = P / np.linalg.norm(P, axis=1, keepdims=True) * R * rng.uniform(0.7, 1.3, (400, 1))
    X1, d1 = MG.closest_on_mesh(P, V, F, k=6); X2, d2, _ = MG.MeshProj(V, F, k=16).project(P)
    T = V[F]; dbf = np.array([np.linalg.norm(MG.closest_on_triangles(p[None], T[:, 0], T[:, 1], T[:, 2]) - p, axis=1).min() for p in P])
    out["sphere"] = {"normals_max_deg_from_radial": float(ang.max()), "H_median_x_R": float(np.median(H) * R),
                     "H_p5_p95_x_R": [float(x) for x in np.percentile(H * R, [5, 95])], "area_sum_vs_4piR2": float(A.sum() / (4 * np.pi * R * R)),
                     "laplacian_on_constant_max": float(np.abs(Lm @ np.ones(len(V))).max()), "clamped_negative_weights": int((off.data < 0).sum()),
                     "closest_on_mesh_vs_brute_max_m": float(np.abs(d1 - dbf).max()), "meshproj_vs_brute_max_m": float(np.abs(d2 - dbf).max())}
    s = out["sphere"]
    ok &= s["normals_max_deg_from_radial"] < 1 and abs(s["H_median_x_R"] - 1) < 0.01 and s["laplacian_on_constant_max"] < 1e-12
    ok &= s["clamped_negative_weights"] == 0 and s["closest_on_mesh_vs_brute_max_m"] < 1e-12 and s["meshproj_vs_brute_max_m"] < 1e-12
    # a planted fold: a strip folded 37 deg along x = 0
    x = np.linspace(-1, 1, 21); y = np.linspace(0, 1, 6); Xg, Yg = np.meshgrid(x, y, indexing="ij")
    tilt = np.radians(37.0); Z = np.where(Xg > 0, Xg * np.tan(tilt), 0.0)
    Vf = np.c_[Xg.ravel(), Yg.ravel(), Z.ravel()]; id_ = np.arange(len(Vf)).reshape(21, 6); Ff = []
    for i in range(20):
        for j in range(5):
            Ff += [[id_[i, j], id_[i + 1, j], id_[i + 1, j + 1]], [id_[i, j], id_[i + 1, j + 1], id_[i, j + 1]]]
    e, an = MG.dihedral_edges(Vf, np.array(Ff)); hinge = (np.abs(Vf[e[:, 0], 0]) < 1e-9) & (np.abs(Vf[e[:, 1], 0]) < 1e-9)
    out["fold"] = {"hinge_deg": [float(an[hinge].min()), float(an[hinge].max())], "elsewhere_max_deg": float(an[~hinge].max())}
    ok &= abs(an[hinge].min() - 37) < 1e-9 and abs(an[hinge].max() - 37) < 1e-9 and an[~hinge].max() < 1e-6
    # polyline
    sq = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], float)
    pd = MG.poly_dist(np.array([[0.5, 0.5, 0], [2, 0.5, 0], [0.5, 0.5, 3]]), sq)
    out["poly_dist"] = pd.tolist(); ok &= np.allclose(pd, [0.5, 1.0, np.hypot(0.5, 3)])
    out["PASS"] = bool(ok)
    json.dump(out, open(os.path.join(HERE, "test_mesh_geom.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
