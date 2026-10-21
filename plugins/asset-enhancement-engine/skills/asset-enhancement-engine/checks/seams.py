"""Whole-body seam/fairness scan: tight CONCAVE creases (indents, grooves) and tight CONVEX ridges (shelves, juts)
anywhere on the skin, grouped into clusters and attributed to the primitives that meet there (SDF owner map).
v28 review (person): ridge/shelf on the chest, indented neck-body junction, lines/bulges where legs and tail meet
the body, a pointy jut on top of the tail base, an indent above the cheeks - none caught: checks.coherence only
looks at the mid-trunk (excludes head, tail, below elbows) = exactly where the junctions are.
usage: python seams.py <mesh_prefix> [--colors out.ply]
"""
import json
import os
import sys

import numpy as np
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks as C  # noqa: E402


def calib(e, iters):
    from skimage.measure import marching_cubes
    R0, vox = 0.02, e * 1.15
    g = np.arange(-R0 - 4 * vox, R0 + 4 * vox, vox)
    X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
    sv, sf, _, _ = marching_cubes(np.sqrt(X ** 2 + Y ** 2 + Z ** 2) - R0, 0.0, spacing=(vox,) * 3)
    sv += g[0]
    d = ((sv - C.laplacian_smooth(sv, sf, iters)) * C.vertex_normals(sv, sf)).sum(1)
    return float(np.median(d) * R0)


def scan(m, iters=8, r_crease=0.007, r_ridge=0.004):
    v, f, L = m["v"], m["f"], m["L"]
    e = float(np.median(np.linalg.norm(v[f[:, 0]] - v[f[:, 1]], axis=1)))
    c = calib(e, iters)
    disp = ((v - C.laplacian_smooth(v, f, iters)) * C.vertex_normals(v, f)).sum(1)
    radius = c / np.where(np.abs(disp) > 1e-9, disp, 1e-9)          # signed: + convex, - concave
    # engineered face detail and paws/toes/ears are SUPPOSED to be tight - scanned separately (body = the rest)
    head = np.linalg.norm(v - np.array(L["head"]), axis=1) < 0.075
    paws = v[:, 2] < 0.03
    crease = (radius < 0) & (-radius < r_crease) & ~paws
    ridge = (radius > 0) & (radius < r_ridge) & ~paws & ~head
    return v, radius, head, crease, ridge


def clusters(v, sel, owner, parts, min_n=25):
    idx = np.nonzero(sel)[0]
    if len(idx) == 0:
        return []
    tr = cKDTree(v[idx])
    _, lab = connected_components(tr.sparse_distance_matrix(tr, 0.003).tocsr() > 0, directed=False)
    out = []
    for c_ in np.unique(lab):
        s = idx[lab == c_]
        if len(s) < min_n:
            continue
        own = {}
        if owner is not None:
            for o in owner[s]:
                own[parts[o] if 0 <= o < len(parts) else "?"] = own.get(parts[o] if 0 <= o < len(parts) else "?", 0) + 1
        out.append((len(s), v[s].mean(0), sorted(own.items(), key=lambda t: -t[1])[:3], s))
    return sorted(out, key=lambda t: -t[0])


if __name__ == "__main__":
    pre = sys.argv[1]
    m = C.load(pre)
    owner = np.load(pre + "_owner.npy") if os.path.exists(pre + "_owner.npy") else None
    parts = json.load(open(pre + "_parts.json")) if os.path.exists(pre + "_parts.json") else []
    v, radius, head, crease, ridge = scan(m)
    for name, sel in (("CREASE (concave, r < 7 mm)", crease & ~head), ("RIDGE (convex, r < 4 mm, body)", ridge),
                      ("HEAD creases (concave, r < 7 mm)", crease & head)):
        cl = clusters(v, sel, owner, parts)
        print(f"== {name}: {len(cl)} clusters")
        for n, cen, own, s in cl[:12]:
            print(f"   n={n:5d} at {np.round(cen, 3)}  tightest r {np.abs(radius[s]).min()*1000:4.1f} mm  parts {own}")
    if "--colors" in sys.argv:
        out = sys.argv[sys.argv.index("--colors") + 1]
        # blue = concave crease, red = convex ridge, grey = fine; intensity by tightness
        col = np.full((len(v), 3), 200, np.uint8)
        t = np.clip(1 - (-radius) / 0.012, 0, 1) * (radius < 0)
        col[t > 0] = (np.array([200, 200, 200]) * (1 - t[t > 0, None]) + np.array([30, 80, 255]) * t[t > 0, None]).astype(np.uint8)
        t2 = np.clip(1 - radius / 0.008, 0, 1) * (radius > 0) * ~head
        col[t2 > 0] = (np.array([200, 200, 200]) * (1 - t2[t2 > 0, None]) + np.array([255, 40, 30]) * t2[t2 > 0, None]).astype(np.uint8)
        f = m["f"]
        with open(out, "wb") as fh:
            fh.write((f"ply\nformat binary_little_endian 1.0\nelement vertex {len(v)}\nproperty float x\nproperty float y\n"
                      f"property float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\n"
                      f"element face {len(f)}\nproperty list uchar int vertex_indices\nend_header\n").encode())
            vd = np.zeros(len(v), dtype=[("p", "<f4", 3), ("c", "u1", 3)]); vd["p"] = v; vd["c"] = col; fh.write(vd.tobytes())
            fd = np.zeros(len(f), dtype=[("n", "u1"), ("i", "<i4", 3)]); fd["n"] = 3; fd["i"] = f; fh.write(fd.tobytes())
        print("colours ->", out)
