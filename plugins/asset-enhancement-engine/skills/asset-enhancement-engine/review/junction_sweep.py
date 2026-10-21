"""Junction experiment: does a wider blend (or another change) make THIS junction fair, and at what shape cost?
Evaluates only a box around the junction (all primitives, at the build voxel), scales the blend radius k of the
named primitive(s) by each multiplier, and reports the seam strength there (p95 of |grad H|, the fairness.py metric,
over 10 mm around the junction point) and how far the surface moved vs x1 (shape cost).
usage: python junction_sweep.py <case_dir> <x,y,z> <half_size> <prim_prefix[,prefix2]> [mults=1,1.5,2,3] [vox=0.0008]
"""
import importlib.util
import os
import sys

import numpy as np
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools")); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "checks"))
import sdf_core as S  # noqa: E402
import fairness as F  # noqa: E402

case = sys.argv[1]
c = np.array([float(t) for t in sys.argv[2].split(",")])
hsz = float(sys.argv[3])
prefixes = tuple(sys.argv[4].split(","))
mults = [float(t) for t in (sys.argv[5] if len(sys.argv) > 5 else "1,1.5,2,3").split(",")]
vox = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0008


def build():
    mod = importlib.util.spec_from_file_location("case_spec", os.path.join(case, "spec.py"))
    spec = importlib.util.module_from_spec(mod); mod.loader.exec_module(spec)
    return spec.build(spec.P)


import io, contextlib  # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    prims0, L = build()
k0 = {p.name: p.k for p in prims0 if p.name.startswith(prefixes)}
print(f"junction at {c} box {2*hsz*1000:.0f} mm; primitives {k0}")
ref = None
for m in mults:
    prims = [p for p in prims0]
    for p in prims:
        if p.name in k0:
            p.k = k0[p.name] * m
    lo, hi = c - hsz, c + hsz
    Fld, _ = S.evaluate(prims, lo, hi, vox)
    Fld[0, :, :] = Fld[-1, :, :] = Fld[:, 0, :] = Fld[:, -1, :] = Fld[:, :, -1] = vox
    v, f, _, _ = marching_cubes(Fld, 0.0, spacing=(vox,) * 3, gradient_direction="ascent", allow_degenerate=False)
    v += lo
    inner = np.all(np.abs(v - c) < hsz - 3 * vox, axis=1)       # ignore the box walls
    H = F.curvature(v, f)
    G = F.grad_mag(v, f, H)
    tr = cKDTree(v)
    _, i0 = tr.query(np.where(inner[:, None], v, 1e9).min(0) * 0 + c) if False else tr.query(c)
    nb = [i for i in tr.query_ball_point(v[i0], 0.010) if inner[i]]
    seam = float(np.percentile(G[nb], 95)) if nb else float("nan")
    moved = ""
    if ref is None:
        ref = (v[inner], cKDTree(v[inner]))
    else:
        d, _ = ref[1].query(v[inner])
        moved = f"surface moved p95 {np.percentile(d, 95)*1000:4.1f} mm, max {d.max()*1000:4.1f} mm"
    print(f"  k x{m:<4} seam |gradH| p95 {seam:9.0f}  {moved}")
    for p in prims:
        if p.name in k0:
            p.k = k0[p.name]
