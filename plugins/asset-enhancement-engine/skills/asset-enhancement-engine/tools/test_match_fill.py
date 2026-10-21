"""Proof of surface_fairing.match_fill / scalar_fill / closest_on_mesh (2026-10-21, woman2 build 13a4). Planted:
  1. closest_on_mesh against brute force on a random convex hull (skinny triangles: the hard case), points 2 % off it
  2. scalar_fill: a field held as a smooth quadratic round a disc and free inside comes back as that quadratic (a thin
     plate reproduces it: its bi-Laplacian is 0), and nothing outside the free set changes
  3. match_fill: a 2 mm-spaced grid surface = the target (a gentle dome with seeded fine relief, standing in for the
     other side mirrored) + a smooth offset (a tilt and a 3 mm shift: the two sides' global difference) + a planted
     mound 4 mm high, 30 mm across (the bulge). match_fill over the mound's region (+ a border) must give target +
     offset there, read at each vertex's own place (the mound gone: under 0.2 mm, 5 % of it; what it leaves adds under
     1 micron of relief over the target's), the target's own fine relief carried in (with no mound, only the offset:
     correlation with the target's relief where each vertex landed > 0.8), and not move anything outside the free set.
    python engine/tools/test_match_fill.py   (writes test_match_fill.json beside it)"""
import json
import os
import sys

import numpy as np
from scipy.spatial import ConvexHull

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import surface_fairing as SF  # noqa: E402


def grid(n, st):
    k = (np.arange(n) - (n - 1) / 2) * st; X, Y = np.meshgrid(k, k)
    idx = np.arange(n * n).reshape(n, n)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel()
    return X.ravel(), Y.ravel(), np.r_[np.c_[a, b, d], np.c_[a, d, c]]


def run():
    out = {}
    rng = np.random.default_rng(1)
    P = rng.normal(size=(3000, 3)); P /= np.linalg.norm(P, axis=1, keepdims=True); F = ConvexHull(P).simplices
    Q = rng.normal(size=(500, 3)); Q = Q / np.linalg.norm(Q, axis=1, keepdims=True) * 1.02
    X, d = SF.closest_on_mesh(Q, P, F)
    best = np.full(len(Q), np.inf)
    for f in F:
        q = SF._closest_tri_vec(Q, np.repeat(P[f[0]][None], len(Q), 0), np.repeat(P[f[1]][None], len(Q), 0), np.repeat(P[f[2]][None], len(Q), 0))
        best = np.minimum(best, np.linalg.norm(q - Q, axis=1))
    out["1_closest_on_mesh"] = {"points": len(Q), "worse_than_brute_force": int(((d - best) > 1e-9).sum()), "max_excess": float((d - best).max()),
                                "pass": bool(((d - best) > 1e-9).sum() == 0)}
    # 2. scalar_fill reproduces a quadratic
    x, y, Fg = grid(81, 0.002); V = np.c_[x, y, np.zeros_like(x)]
    f = 3.0 * x * x - 2.0 * x * y + 1.5 * y * y + 0.2 * x
    free = np.hypot(x, y) < 0.04
    g = SF.scalar_fill(V, Fg, free, np.where(free, 0.0, f))
    out["2_scalar_fill"] = {"free": int(free.sum()), "max_error_inside": float(np.abs(g - f)[free].max()), "value_scale": float(np.abs(f[free]).max()),
                            "changed_outside": float(np.abs(g - np.where(free, 0.0, f))[~free].max())}
    out["2_scalar_fill"]["pass"] = bool(out["2_scalar_fill"]["max_error_inside"] < 1e-3 * out["2_scalar_fill"]["value_scale"] and out["2_scalar_fill"]["changed_outside"] == 0.0)
    # 3. match_fill removes a planted mound and carries the target's form and fine relief
    x, y, Fg = grid(121, 0.002)
    r = np.hypot(x, y)
    fine = np.zeros_like(x)
    for _ in range(600):
        cx, cy = rng.uniform(-0.12, 0.12, 2); s = rng.uniform(0.0015, 0.003); a = rng.uniform(-3e-5, 3e-5)
        fine += a * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * s * s))
    target_z = 0.03 * np.exp(-(r / 0.08) ** 2) + fine
    offset = 0.003 + 0.02 * x + 0.01 * y
    mound = 0.004 * np.exp(-(np.hypot(x - 0.03, y + 0.01) / 0.012) ** 2)
    Vt = np.c_[x, y, target_z]; Vs = np.c_[x, y, target_z + offset + mound]
    region = np.hypot(x - 0.03, y + 0.01) < 0.035
    Vn, rep = SF.match_fill(Vs, Fg, region, Vt, Fg)
    # the result against target + offset at each result vertex's own place (x, y): vertices move along their normals,
    # so they also slide along the surface (up to ~1 mm on the mound's slope) and are compared where they landed
    from scipy.interpolate import griddata
    want = griddata(np.c_[x, y], target_z + offset, Vn[region, :2], method="cubic")
    err = Vn[region, 2] - want
    core = np.hypot(x - 0.03, y + 0.01) < 0.025
    ids = np.nonzero(core)[0]
    rr = SF.relief(Vn, Fg, ids, 0.006)
    rt_grid = SF.relief(Vt, Fg, np.arange(len(x)), 0.006)
    ok = np.isfinite(rt_grid)
    rt = griddata(np.c_[x, y][ok], rt_grid[ok], Vn[ids, :2], method="linear")
    out["3_match_fill"] = {"mound_mm": 4.0, "error_vs_target_plus_offset_mm_p50_max": [float(np.median(np.abs(err)) * 1e3), float(np.abs(err).max() * 1e3)],
                           "mound_left_mm_max": float(np.abs(err).max() * 1e3), "relief_corr_with_target_where_landed": float(np.corrcoef(rr, rt)[0, 1]),
                           "relief_p75_ratio": float(np.percentile(np.abs(rr), 75) / np.percentile(np.abs(rt), 75)),
                           "moved_outside_free_mm": float(np.abs(Vn - Vs)[~region].max() * 1e3), "report": rep}
    # the same with no mound (only the two sides' offset): the target's fine relief must come across where it landed
    Vs0 = np.c_[x, y, target_z + offset]
    Vn0, _ = SF.match_fill(Vs0, Fg, region, Vt, Fg)
    rr0 = SF.relief(Vn0, Fg, ids, 0.006); rt0 = griddata(np.c_[x, y][ok], rt_grid[ok], Vn0[ids, :2], method="linear")
    out["3_match_fill"]["no_mound_relief_corr_where_landed"] = float(np.corrcoef(rr0, rt0)[0, 1])
    out["3_match_fill"]["relief_excess_over_target_um"] = float((np.percentile(np.abs(rr), 75) - np.percentile(np.abs(rt), 75)) * 1e6)
    out["3_match_fill"]["pass"] = bool(out["3_match_fill"]["mound_left_mm_max"] < 0.2 and out["3_match_fill"]["no_mound_relief_corr_where_landed"] > 0.8
                                       and out["3_match_fill"]["relief_excess_over_target_um"] < 1.0 and out["3_match_fill"]["moved_outside_free_mm"] == 0.0)
    out["all_pass"] = all(v["pass"] for v in out.values() if isinstance(v, dict) and "pass" in v)
    return out


if __name__ == "__main__":
    o = run()
    json.dump(o, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_match_fill.json"), "w"), indent=1)
    print(json.dumps(o, indent=1))
