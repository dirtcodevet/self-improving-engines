"""Proof of engine/tools/mesh_repair.py (build K1, 2026-10-21), answers known without the tool:
  winding:  two 10 mm spheres overlapping by 2 mm: a point inside one reads 1, inside both 2, outside 0
  refill:   a sphere (the sound base) with a smooth displacement field (the "sculpt") and, in one cap, a planted pleat
            (a tangential shear that folds the skin back on itself): before, folds / inside-out faces present; after
            refill() on the cap + 1 mm: none, nothing outside the free set moved, and inside the free set the result is
            the base plus a displacement within the range of the sculpt round it
  unfold:   a flat sheet with a crumpled disc (random 0.6 mm jitter at 0.2 mm spacing): after unfold(): no folds or
            crossings, nothing outside the free set moved
  separate: the two overlapping spheres (each its own closed shell): after separate(): no crossing pair, the smallest
            gap between the shells within [0, 0.1] mm, and they still touch (gap under 0.1 mm), the far side unmoved
    python engine/tools/test_mesh_repair.py     -> test_mesh_repair.json beside this file
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mesh_repair as MR  # noqa: E402
import mesh_geom as MG  # noqa: E402


def sphere(c, R, nt=48, nphi=96):
    th = np.linspace(0, np.pi, nt + 1)[1:-1]; ph = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    P = [np.array(c) + R * np.c_[np.sin(t) * np.cos(ph), np.sin(t) * np.sin(ph), np.full(nphi, np.cos(t))] for t in th]
    V = np.concatenate(P + [np.array([c]) + [0, 0, R], np.array([c]) - [0, 0, R]])
    top, bot = len(V) - 2, len(V) - 1
    T = []
    for i in range(nt - 2):
        for j in range(nphi):
            a = i * nphi + j; b = i * nphi + (j + 1) % nphi
            T += [[a, a + nphi, b + nphi], [a, b + nphi, b]]
    for j in range(nphi):
        T.append([top, j, (j + 1) % nphi])
        a = (nt - 2) * nphi + j; b = (nt - 2) * nphi + (j + 1) % nphi
        T.append([bot, b, a])
    T = np.array(T, np.int64)
    n = MG.face_normals(V, T); out = ((V[T].mean(1) - np.array(c)) * n).sum(1) < 0
    T[out] = T[out][:, ::-1]
    return V, T


def main():
    out = {}; ok = True
    R = 0.010
    # winding
    V1, T1 = sphere([0, 0, 0], R); V2, T2 = sphere([0.018, 0, 0], R)
    V = np.r_[V1, V2]; T = np.r_[T1, T2 + len(V1)]
    w = MR.winding(np.array([[-0.005, 0, 0], [0.009, 0, 0], [0.023, 0, 0], [0.0, 0.02, 0.0]]), V, T, near_r=0.05)
    out["winding"] = {"inside_one_both_other_outside": [round(float(x), 4) for x in w]}
    ok &= bool(np.allclose(w, [1, 2, 1, 0], atol=0.02))
    # separate
    region = np.ones(len(V), bool)
    f0 = MR.local_faults(V, T, region)
    X, rep = MR.separate(V, T, region, ease_m=0.004)
    f1 = rep["after"]
    a = np.arange(len(V1)); b = np.arange(len(V1), len(V))
    Pa, da = MG.closest_on_mesh(X[a], X[b], T2)
    gap = float(np.min(np.where(np.linalg.norm(X[a] - np.array([0.009, 0, 0]), axis=1) < 0.006, da, np.inf)))
    far = np.r_[a[V1[:, 0] < -0.005], b[V2[:, 0] > 0.023]]
    out["separate"] = {"before": f0, "after": f1, "smallest_gap_mm": round(gap * 1e3, 4), "far_side_max_move_mm": float(np.abs(X[far] - V[far]).max() * 1e3),
                       "iters": rep["iters"]}
    ok &= f0["crossing_pairs"] > 0 and f1["crossing_pairs"] == 0 and 0 <= gap <= 1e-4 and out["separate"]["far_side_max_move_mm"] == 0.0
    # refill: base sphere B, sculpt = smooth bumps; a pleat in one cap
    B, TB = sphere([0, 0, 0], R)
    Nb = B / np.linalg.norm(B, axis=1)[:, None]
    sculpt = 3e-4 * np.sin(B[:, 0] * 400) * np.cos(B[:, 1] * 300)
    Vs = B + sculpt[:, None] * Nb
    cap = Vs[:, 2] > 0.0085
    shear = np.zeros_like(B)
    th = np.arctan2(B[:, 1], B[:, 0])
    rho = np.linalg.norm(B[:, :2], axis=1)
    shear[cap, 0] = 2.5e-3 * np.sin(np.pi * (B[cap, 2] - 0.0085) / 0.0015) * np.cos(th[cap] * 3)
    Vp = Vs + shear
    reg = np.linalg.norm(B - [0, 0, R], axis=1) < 0.008
    b0 = MR.local_faults(Vp, TB, reg)
    free = MR.dilate(TB, cap, 3)
    Xr = MR.refill(Vp, B, TB, free)
    b1 = MR.local_faults(Xr, TB, reg)
    Dn = np.linalg.norm(Xr - B, axis=1)
    out["refill"] = {"before": b0, "after": b1, "outside_free_max_move": float(np.abs(Xr[~free] - Vp[~free]).max()),
                     "free": int(free.sum()), "displacement_inside_mm_max": float(Dn[free].max() * 1e3),
                     "sculpt_round_mm_max": float(np.abs(sculpt[~free & (np.linalg.norm(B - [0, 0, R], axis=1) < 0.011)]).max() * 1e3)}
    ok &= (b0["folds"] + b0["inverted_faces"]) > 0 and b1["folds"] == 0 and b1["inverted_faces"] == 0 and b1["crossing_pairs"] == 0 \
        and out["refill"]["outside_free_max_move"] == 0.0 and out["refill"]["displacement_inside_mm_max"] <= out["refill"]["sculpt_round_mm_max"] * 1.05
    # unfold: a crumpled disc on a flat sheet
    n = 60; h = 2e-4
    xs, ys = np.meshgrid(np.arange(n + 1) * h, np.arange(n + 1) * h, indexing="ij")
    Vf = np.c_[xs.ravel(), ys.ravel(), np.zeros(xs.size)]
    idx = lambda i, j: i * (n + 1) + j  # noqa: E731
    Tf = np.array([t for i in range(n) for j in range(n) for t in ([idx(i, j), idx(i + 1, j), idx(i + 1, j + 1)], [idx(i, j), idx(i + 1, j + 1), idx(i, j + 1)])], np.int64)
    disc = np.linalg.norm(Vf[:, :2] - n * h / 2, axis=1) < 1.5e-3
    rng = np.random.default_rng(7)
    Vc = Vf.copy(); Vc[disc] += rng.normal(0, 6e-4, (disc.sum(), 3))
    whole = np.ones(len(Vf), bool)
    u0 = MR.local_faults(Vc, Tf, whole)
    freeu = MR.dilate(Tf, disc, 2)
    Xu, _ = MR.unfold(Vc, Tf, freeu, detail=None)
    u1 = MR.local_faults(Xu, Tf, whole)
    out["unfold"] = {"before": u0, "after": u1, "outside_free_max_move": float(np.abs(Xu[~freeu] - Vc[~freeu]).max())}
    ok &= u0["folds"] > 0 and u1["folds"] == 0 and u1["crossing_pairs"] == 0 and u1["inverted_faces"] == 0 and out["unfold"]["outside_free_max_move"] == 0.0
    out["pass"] = bool(ok)
    with open(os.path.join(HERE, "test_mesh_repair.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(json.dumps({k: (v if k != "separate" else {kk: vv for kk, vv in v.items() if kk != "iters"}) for k, v in out.items()}, indent=1, default=str))
    print("PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
