"""PROOF of surface_fairing.fill()'s detail (2026-10-21, woman2 build 13a3; A10 / A22, planted).
    python engine/tools/test_fill_detail.py [--out engine/tools/test_fill_detail.json]

A skin-like test surface: a quad grid of 2.5 mm (the woman2 skin's mean edge) bent round a cylinder of 120 mm radius
(a torso side's curvature), carrying a fine relief made of 2,500 Gaussian bumps (sigma 4 mm, heights +-0.04 mm; a
seeded random field), measured with relief() at 10 mm. The free set is a disc of 65 mm radius in the middle.
Planted cases (each against the same surface without the plant, the answer key):
  dent    a wrong shape at a larger scale than the relief: a dent 4 mm deep, 50 mm radius, (1 - (r/R)^2)^3 profile.
          The fill must take it out and keep the relief: inside / around within the around's own spread (its four
          sectors' p75 over the whole around's), where the smooth fill (detail=None, the 13a2 failure) falls far below.
  crease  the dent plus a crease the fill is there to remove: a groove 1 mm deep, 2 mm wide, 60 mm long through the
          disc. The gate must not copy it: the largest edge turn inside within the clean surface's own largest edge
          turn, and the inside's relief not above the around's spread.
  rough   the over-rough side (A22): the source's relief tripled (detail_from = a copy of the input whose relief is x3).
          The gate must catch it (the share gated large) - the tool never makes a patch rougher than the skin round it
          from a source that is.
Each case also records the smooth fill's numbers. Pass marks come from the clean surface's own readings (its sector
spread, its own largest edge turn); no number is picked.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import surface_fairing as SF  # noqa: E402

E = 0.0025; NG = 121; RC = 0.12; RFREE = 0.065


def surface(seed=7):
    u = (np.arange(NG) - NG // 2) * E
    U, W = np.meshgrid(u, u, indexing="ij")
    rng = np.random.default_rng(seed)
    c = rng.uniform(-0.16, 0.16, (2500, 2)); a = rng.choice([-1.0, 1.0], 2500) * rng.uniform(0.02, 0.04, 2500)
    det = np.zeros_like(U)
    for k in range(len(c)):
        det += a[k] * 1e-3 * np.exp(-((U - c[k, 0]) ** 2 + (W - c[k, 1]) ** 2) / (2 * 0.004 ** 2))
    return U, W, det


def embed(U, W, h):
    """the (u, w) grid bent round a cylinder of radius RC about the u axis, h along the outward normal"""
    th = W / RC
    return np.stack([U, (RC + h) * np.sin(th), (RC + h) * np.cos(th) - RC], -1).reshape(-1, 3)


def faces():
    i = np.arange(NG - 1)[:, None] * NG + np.arange(NG - 1)[None, :]
    i = i.ravel()
    return np.r_[np.c_[i, i + NG, i + NG + 1], np.c_[i, i + NG + 1, i + 1]].astype(np.int64)


def edge_turn_max(V, F, sel):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); fn /= np.linalg.norm(fn, axis=1, keepdims=True)
    e = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1); f = np.tile(np.arange(len(F)), 3)
    o = np.lexsort((e[:, 1], e[:, 0])); e, f = e[o], f[o]
    same = np.all(e[1:] == e[:-1], axis=1); a, b = f[:-1][same], f[1:][same]; ee = e[:-1][same]
    ang = np.degrees(np.arccos(np.clip((fn[a] * fn[b]).sum(1), -1, 1)))
    m = sel[ee[:, 0]] & sel[ee[:, 1]]
    return float(ang[m].max())


def sector_spread(V, F, around, A, k=4):
    ids = np.nonzero(around)[0]
    h = SF.relief(V, F, ids, 0.010, A=A)
    ang = np.arctan2(V[ids, 1], V[ids, 0]); sec = np.floor((ang + np.pi) / (2 * np.pi / k)).astype(int).clip(0, k - 1)
    whole = np.nanpercentile(np.abs(h), 75)
    r = [float(np.nanpercentile(np.abs(h[sec == j]), 75) / whole) for j in range(k)]
    return min(r), max(r)


def main(out_path=None):
    U, W, det = surface(); F = faces(); n = NG * NG
    r = np.hypot(U, W).ravel(); free = r < RFREE
    clean = embed(U, W, det)
    A = SF.tri_adjacency(F, n)
    d_out = SF.ring_distance(A, free, 12); d_in = SF.ring_distance(A, ~free, 3)
    around = (~free) & (d_out >= 5) & (d_out <= 12); core = free & (d_in >= 3)
    lo, hi = sector_spread(clean, F, around, A)
    turn_clean = edge_turn_max(clean, F, core)
    Rd = 0.050; dent = np.where(r < Rd, -0.004 * (1 - (r / Rd) ** 2) ** 3, 0.0).reshape(U.shape)
    groove = np.where((np.abs(W) < 0.030), -0.001 * np.exp(-(U ** 2) / (2 * 0.001 ** 2)), 0.0)
    res = {"surface": {"vertices": n, "edge_mm": E * 1e3, "cylinder_radius_mm": RC * 1e3, "free_vertices": int(free.sum()),
                       "core_vertices": int(core.sum()), "around_vertices": int(around.sum()),
                       "around_sector_spread": [round(lo, 3), round(hi, 3)], "clean_core_edge_turn_max_deg": round(turn_clean, 3)}}
    ok_all = True
    for case in ("dent", "crease", "rough"):
        h = det + dent + (groove if case == "crease" else 0.0)
        V = embed(U, W, h)
        kw = {}
        if case == "rough":
            kw["detail_from"] = embed(U, W, 3 * det + dent)
        out_s, _ = SF.fill(V, F, free, detail=None)
        out, rep = SF.fill(V, F, free, **kw)
        g = rep.pop("gate"); d = rep["detail"]
        rp = d["relief_p75_mm"]
        ratio, ratio_s = d["inside_over_around"], rp["inside_smooth_fill"] / rp["around"]
        # shape: the output against the clean surface, along the clean normal, inside the free set
        Nc = SF.vertex_normals(clean, F)
        dev = np.einsum("ij,ij->i", out - clean, Nc)[free] * 1e3; dev_s = np.einsum("ij,ij->i", out_s - clean, Nc)[free] * 1e3
        dev_in = np.einsum("ij,ij->i", V - clean, Nc)[free] * 1e3
        row = {"inside_over_around": round(ratio, 3), "smooth_fill_inside_over_around": round(ratio_s, 3),
               "relief_p75_mm": {k: round(v, 5) for k, v in rp.items()}, "gate": d["gate"],
               "shape_vs_clean_mm_max_abs": {"input": round(float(np.abs(dev_in).max()), 3), "smooth_fill": round(float(np.abs(dev_s).max()), 3),
                                             "out": round(float(np.abs(dev).max()), 3)},
               "core_edge_turn_max_deg": {"input": round(edge_turn_max(V, F, core), 2), "smooth_fill": round(edge_turn_max(out_s, F, core), 2),
                                          "out": round(edge_turn_max(out, F, core), 2)}}
        if case == "dent":
            row["pass"] = bool(lo <= ratio <= hi and not (lo <= ratio_s <= hi))
        elif case == "crease":
            row["pass"] = bool(row["core_edge_turn_max_deg"]["out"] <= turn_clean and ratio <= hi)
        else:
            row["pass"] = bool(d["gate"]["gated_share_of_free"] > 0.5 and ratio <= hi)
        ok_all &= row["pass"]
        res[case] = row
    res["all_pass"] = bool(ok_all)
    print(json.dumps(res, indent=1))
    if out_path:
        json.dump(res, open(out_path, "w"), indent=1)
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[a.index("--out") + 1] if "--out" in a else None)
