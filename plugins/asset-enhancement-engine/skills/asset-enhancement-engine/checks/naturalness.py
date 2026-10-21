"""Reference-relative naturalness: where does OUR surface bend much more sharply than a natural cat surface at the
same place? Curvature (signed, umbrella-displacement calibrated on spheres) at a given smoothing scale on our fur
envelope and on the aligned 3D reference; excess = |k_ours| - |k_ref| for the same sign; clusters of large excess,
attributed to the SDF parts that meet there. Absolute thresholds cannot do this: an armpit is tight and natural, a
chest shelf can be broad and wrong (v28 review).
usage: python naturalness.py <mesh_prefix> <reference.ply> [iters=30] [--colors out.ply]
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks as C  # noqa: E402
from seams import calib, clusters  # noqa: E402


def signed_k(v, f, iters):
    e = float(np.median(np.linalg.norm(v[f[:, 0]] - v[f[:, 1]], axis=1)))
    c = calib(e, iters)
    disp = ((v - C.laplacian_smooth(v, f, iters)) * C.vertex_normals(v, f)).sum(1)
    return disp / c                                   # 1/m, + convex, - concave


if __name__ == "__main__":
    pre, refp = sys.argv[1], sys.argv[2]
    iters = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 30
    vo, fo = C.read_ply(pre + "_env.ply")
    vr, fr = C.read_ply(refp)
    L = json.load(open(pre + "_landmarks.json"))["landmarks"]
    ko, kr = signed_k(vo, fo, iters), signed_k(vr, fr, iters)
    d, j = cKDTree(vr).query(vo)
    kref = kr[j]
    near = d < float(os.environ.get("NEAR_MM", "15")) / 1000   # judged where the reference is near (junctions drift away: 6 mm judged only 52%)
    excess_cc = np.where(near & (ko < 0), (-ko) - np.maximum(-kref, 0), 0)    # extra concavity (dents, grooves)
    excess_cv = np.where(near & (ko > 0), ko - np.maximum(kref, 0), 0)        # extra convexity (ridges, juts)
    owner = np.load(pre + "_env_owner.npy") if os.path.exists(pre + "_env_owner.npy") else None
    parts = json.load(open(pre + "_parts.json")) if os.path.exists(pre + "_parts.json") else []
    head = np.linalg.norm(vo - np.array(L["head"]), axis=1) < 0.075
    print(f"scale iters={iters}; reference within 6 mm on {near.mean()*100:.0f}% of our envelope")
    for name, ex in (("EXTRA CONCAVITY (dents/grooves)", excess_cc), ("EXTRA CONVEXITY (ridges/juts/bulges)", excess_cv)):
        thr = 1 / float(os.environ.get("R_MM", "25")) * 1000   # extra bend beyond the reference
        cl = clusters(vo, ex > thr, owner, parts, min_n=20)
        print(f"== {name}: {len(cl)} clusters (excess curvature > 1/12mm)")
        for n, cen, own, s in cl[:14]:
            print(f"   n={n:5d} at {np.round(cen, 3)} {'HEAD' if head[s].mean() > 0.5 else '    '}  "
                  f"ours r {1/max(np.abs(ko[s]).max(),1e-9)*1000:5.1f} mm vs ref r {1/max(np.abs(kref[s]).max(),1e-9)*1000:5.1f} mm  parts {own}")
    if "--colors" in sys.argv:
        out = sys.argv[sys.argv.index("--colors") + 1]
        col = np.full((len(vo), 3), 205, np.uint8)
        t = np.clip(excess_cc / (1 / 0.005), 0, 1); col[t > 0] = (205 * (1 - t[t > 0, None]) + np.array([30, 80, 255]) * t[t > 0, None]).astype(np.uint8)
        t2 = np.clip(excess_cv / (1 / 0.005), 0, 1); col[t2 > 0] = (205 * (1 - t2[t2 > 0, None]) + np.array([255, 40, 30]) * t2[t2 > 0, None]).astype(np.uint8)
        col[~near] = (150, 205, 150)                   # reference far away: no verdict (green-grey)
        with open(out, "wb") as fh:
            fh.write((f"ply\nformat binary_little_endian 1.0\nelement vertex {len(vo)}\nproperty float x\nproperty float y\n"
                      f"property float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\n"
                      f"element face {len(fo)}\nproperty list uchar int vertex_indices\nend_header\n").encode())
            vd = np.zeros(len(vo), dtype=[("p", "<f4", 3), ("c", "u1", 3)]); vd["p"] = vo; vd["c"] = col; fh.write(vd.tobytes())
            fd = np.zeros(len(fo), dtype=[("n", "u1"), ("i", "<i4", 3)]); fd["n"] = 3; fd["i"] = fo; fh.write(fd.tobytes())
        print("colours ->", out)
