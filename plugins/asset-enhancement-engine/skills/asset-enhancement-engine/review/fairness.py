"""Seam FAIRNESS: where does curvature JUMP along the surface? (CAD 'G2' test; zebra stripes show the same thing.)
Every body part is a primitive joined to its neighbour by a polynomial smooth-min, which is tangent-continuous but
NOT curvature-continuous: the curvature changes abruptly at the edges of the blend band -> the 'lines' the person
saw where the neck, legs and tail meet the body, the chest shelf, the indent above the cheeks (v27d review).
Metric: mean curvature H (calibrated umbrella displacement, small scale) -> its surface gradient |grad H| per vertex
(1-ring finite differences, lightly averaged). The natural baseline is the 3D reference (Rodin, a smooth natural cat
surface): bands above its p99 are flagged, clustered and attributed to the SDF parts meeting there (owner map).
usage: python fairness.py <mesh_prefix> <reference.ply> [--colors out.ply] [--json out.json]
"""
import json
import os
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "checks"))
import checks as C  # noqa: E402
from seams import calib  # noqa: E402

SIGMA = 0.0025     # physical smoothing scale (m); iterations follow from the edge length (diffusion ~ 0.5 e^2 / iter)


def curvature(v, f, sigma=SIGMA):
    e = float(np.median(np.linalg.norm(v[f[:, 0]] - v[f[:, 1]], axis=1)))
    iters = max(2, int(round(2 * sigma ** 2 / e ** 2)))
    c = calib(e, iters)
    return ((v - C.laplacian_smooth(v, f, iters)) * C.vertex_normals(v, f)).sum(1) / c        # 1/m


def grad_mag(v, f, H, r=0.003, step=2):
    """|grad H| at a PHYSICAL scale: for every `step`-th vertex, the largest |dH|/d over neighbours 1.5..r away
    (per-edge differences were dominated by marching-cubes noise); spread back to all vertices by nearest sample"""
    idx = np.arange(0, len(v), step)
    tr = cKDTree(v)
    g = np.zeros(len(idx))
    for k, i in enumerate(idx):
        nb = tr.query_ball_point(v[i], r)
        if len(nb) < 4:
            continue
        nb = np.array(nb); d = np.linalg.norm(v[nb] - v[i], axis=1); m = d > 0.5 * r
        if m.any():
            g[k] = np.max(np.abs(H[nb[m]] - H[i]) / d[m])
    _, j = cKDTree(v[idx]).query(v)
    return g[j]                                                                                # 1/m^2


def run(pre, refp):
    v, f = C.read_ply(pre + ".ply")
    L = json.load(open(pre + "_landmarks.json"))["landmarks"]
    G = grad_mag(v, f, curvature(v, f))
    owner = np.load(pre + "_owner.npy") if os.path.exists(pre + "_owner.npy") else None
    parts = json.load(open(pre + "_parts.json")) if os.path.exists(pre + "_parts.json") else []
    # natural baseline WITHIN this mesh (same voxel noise everywhere): the mid-flank, one primitive, no seam within
    # 12 mm. (The 3D reference is too coarse - 4 mm edges - to set a 3 mm-scale baseline.)
    trunk_id = parts.index("trunk") if "trunk" in parts else -1
    clean = (owner == trunk_id) if owner is not None else np.ones(len(v), bool)
    other = np.nonzero(owner != trunk_id)[0] if owner is not None else np.array([], int)
    if len(other):
        dd, _ = cKDTree(v[other]).query(v)
        clean &= dd > 0.012
    clean &= (np.abs(v[:, 1]) < 0.08) & (v[:, 2] > 0.13)
    base = float(np.percentile(G[clean], 95))
    head = np.linalg.norm(v - np.array(L["head"]), axis=1) < 0.075
    # only the ENGINEERED details are exempt (eyelid apertures, nostrils/leather, mouth slit) - tight radii. v1 exempted
    # everything within 45 mm of the nose and hid the whisker-pad -> cheek transition (person: "transitions too sharply")
    face = np.zeros(len(v), bool)
    for k, r in (("eye.R", 0.0125), ("eye.L", 0.0125), ("nose", 0.0085), ("mouth_front", 0.0)):
        if k in L and r > 0:
            face |= np.linalg.norm(v - np.array(L[k]), axis=1) < r
    if "mouth" in L:
        sys.path.insert(0, os.path.join(HERE, "..", "tools"))
        import mouth_geom as MG
        R_, H0_, hs_ = np.array(L["head_R"]), np.array(L["head"]), json.load(open(pre + "_landmarks.json"))["params"]["head_scale"]
        hl = ((v - H0_) @ R_) / hs_
        zm, e, h = MG.zm_e_h(hl[:, 0], hl[:, 1], MG.from_landmarks(L, hs_))
        face |= (e < 1.05) & (np.abs(hl[:, 2] - zm) < h + 0.0025)          # the slit and its lip margins
    ears = np.zeros(len(v), bool)
    for s in "RL":
        if f"ear_tip.{s}" in L:
            ears |= np.linalg.norm(v - np.array(L[f"ear_tip.{s}"]), axis=1) < 0.035
    paws = v[:, 2] < 0.03
    judged = ~face & ~ears & ~paws
    hot = judged & (G > 3.0 * base)
    idx = np.nonzero(hot)[0]
    found = []
    if len(idx):
        tr = cKDTree(v[idx])
        _, lab = connected_components(tr.sparse_distance_matrix(tr, 0.003).tocsr() > 0, directed=False)
        for c_ in np.unique(lab):
            s = idx[lab == c_]
            if len(s) < 30:
                continue
            # parts meeting here: owners within 4 mm of the band
            near = cKDTree(v).query_ball_point(v[s].mean(0), 0.012)
            own = {}
            if owner is not None:
                for o in owner[near]:
                    nm = parts[o] if 0 <= o < len(parts) else "?"
                    own[nm] = own.get(nm, 0) + 1
            found.append({"n": int(len(s)), "at": np.round(v[s].mean(0), 3).tolist(),
                          "peak_x_base": round(float(G[s].max() / base), 1),
                          "parts": [k for k, _ in sorted(own.items(), key=lambda t: -t[1])[:3]], "idx": s})
    found.sort(key=lambda d: -d["n"] * d["peak_x_base"])
    return v, f, G, base, judged, found


if __name__ == "__main__":
    pre, refp = sys.argv[1], sys.argv[2]
    v, f, G, base, judged, found = run(pre, refp)
    print(f"baseline (seam-free mid-flank p95 |grad H|) {base:.0f} 1/m^2; judged {judged.mean()*100:.0f}% of the skin; "
          f"flagged bands (> 3x baseline): {len(found)}")
    for d in found[:20]:
        print(f"   n={d['n']:5d} at {d['at']}  peak {d['peak_x_base']:5.1f}x  parts {d['parts']}")
    if "--json" in sys.argv:
        json.dump({"baseline": base, "bands": [{k: v_ for k, v_ in d.items() if k != "idx"} for d in found]},
                  open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
    if "--colors" in sys.argv:
        out = sys.argv[sys.argv.index("--colors") + 1]
        t = np.clip((G / base - 1.0) / 4.0, 0, 1) * judged
        col = (np.array([205, 205, 205]) * (1 - t[:, None]) + np.array([255, 120, 0]) * t[:, None]).astype(np.uint8)
        col[~judged] = (170, 200, 170)
        with open(out, "wb") as fh:
            fh.write((f"ply\nformat binary_little_endian 1.0\nelement vertex {len(v)}\nproperty float x\nproperty float y\n"
                      f"property float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\n"
                      f"element face {len(f)}\nproperty list uchar int vertex_indices\nend_header\n").encode())
            vd = np.zeros(len(v), dtype=[("p", "<f4", 3), ("c", "u1", 3)]); vd["p"] = v; vd["c"] = col; fh.write(vd.tobytes())
            fd = np.zeros(len(f), dtype=[("n", "u1"), ("i", "<i4", 3)]); fd["n"] = 3; fd["i"] = f; fh.write(fd.tobytes())
        print("colours ->", out)
