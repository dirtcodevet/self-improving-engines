"""(background Blender) rays, nearest points and self-overlaps on a triangle mesh, by Blender's BVH. Made in build 13a
(cases/woman2/build13/bl_rays.py), moved here in build A1; call it from system Python with engine/tools/bvh.py rays().
    blender -b --factory-startup --python bl_bvh.py -- IN.npz OUT.npz

IN.npz:  V (n,3) float, F (m,3) int (triangles); optional
         O (k,3) ray origins, D (k,3) unit directions, maxd (scalar, m), min_hit (scalar, m: hits nearer than this are the
           ray's own surface and are stepped over, as engine/tools/pose_study_bl.py rays() does: 0.3 mm);
         Q (j,3) query points for nearest-surface lookup;  overlap (bool scalar): self-overlapping triangle pairs.
         P, PN, P0 (k,3) skin points, their outward normals and rest places, V0 (n,3) the rest skin, rest_sep, maxd_in
           (build 13c: inside test, below);
OUT.npz: dist (k,) first hit beyond min_hit along each ray (NaN: none within maxd), hit_face (k,);
         cross_out (k,) surface crossings along +PN (odd: inside), depth_in (k,), depth_face (k,);
         near_d (j,), near_p (j,3), near_n (j,3) face normal of the nearest point, near_face (j,);  pairs (p,2).
"""
import sys

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
Z = dict(np.load(a[0], allow_pickle=False))
V = Z["V"].astype(float); F = Z["F"].astype(np.int64)
bvh = BVHTree.FromPolygons(V.tolist(), F.tolist(), all_triangles=True)
out = {}
if "O" in Z:
    O, D = Z["O"].astype(float), Z["D"].astype(float)
    maxd = float(Z.get("maxd", 0.4)); mh = float(Z.get("min_hit", 3e-4))
    dist = np.full(len(O), np.nan); hf = np.full(len(O), -1, np.int64)
    for i in range(len(O)):
        d = Vector(D[i]); o = Vector(O[i]) + d * 2e-5; tot = 2e-5
        for _ in range(6):
            hit = bvh.ray_cast(o, d, maxd - tot)
            if hit[0] is None:
                break
            if tot + hit[3] > mh:
                dist[i] = tot + hit[3]; hf[i] = hit[2]; break
            o = hit[0] + d * 1e-4; tot += hit[3] + 1e-4
    out["dist"] = dist; out["hit_face"] = hf
if "Q" in Z:
    Q = Z["Q"].astype(float)
    nd = np.full(len(Q), np.nan); npnt = np.full((len(Q), 3), np.nan); nn = np.full((len(Q), 3), np.nan); nf = np.full(len(Q), -1, np.int64)
    for i in range(len(Q)):
        r = bvh.find_nearest(Vector(Q[i]))
        if r[0] is not None:
            npnt[i] = r[0]; nn[i] = r[1]; nf[i] = r[2]; nd[i] = r[3]
    out.update(near_d=nd, near_p=npnt, near_n=nn, near_face=nf)
if "P" in Z:
    # build 13c: is a skin point inside the body (skin passed through skin)? Odd count of surface crossings along its
    # outward normal = inside another part's volume (the skin must be closed). Depth: along the inward normal, the first
    # face it EXITS (face normal along the ray) that was at least rest_sep from the point at rest.
    P, PN, P0 = Z["P"].astype(float), Z["PN"].astype(float), Z["P0"].astype(float)
    V0 = Z["V0"].astype(float); C0 = V0[F].mean(1); FN = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    FN /= np.maximum(np.linalg.norm(FN, axis=1, keepdims=True), 1e-30)
    rs = float(Z.get("rest_sep", 0.012)); md = float(Z.get("maxd_in", 0.05)); eps = 2e-4
    cnt = np.zeros(len(P), np.int64); dep = np.full(len(P), np.nan); dfa = np.full(len(P), -1, np.int64)
    for i in range(len(P)):
        d = Vector(PN[i]); o = Vector(P[i]) + d * eps; n_ = 0
        for _ in range(40):
            hit = bvh.ray_cast(o, d, 3.0)
            if hit[0] is None:
                break
            n_ += 1; o = hit[0] + d * 1e-5
        cnt[i] = n_
        d = -Vector(PN[i]); o = Vector(P[i]) + d * eps; tot = eps
        for _ in range(20):
            hit = bvh.ray_cast(o, d, md - tot)
            if hit[0] is None:
                break
            f = hit[2]; tot += hit[3]
            if np.dot(FN[f], -PN[i]) > 0 and np.linalg.norm(C0[f] - P0[i]) > rs:
                dep[i] = tot; dfa[i] = f; break
            o = hit[0] + d * 1e-5; tot += 1e-5
    out.update(cross_out=cnt, depth_in=dep, depth_face=dfa)
if bool(Z.get("overlap", False)):
    out["pairs"] = np.array(bvh.overlap(bvh), np.int64).reshape(-1, 2)
np.savez_compressed(a[1], **out)
print("bl_rays done", {k: v.shape for k, v in out.items()})
