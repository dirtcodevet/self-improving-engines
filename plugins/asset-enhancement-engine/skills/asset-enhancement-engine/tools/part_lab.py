# Fast unit loop for ONE region of a case spec (mouth, nose, eyelids, chest...): evaluates every primitive but
# only inside a small box, at a fine voxel, and meshes it - seconds instead of a 25-minute build. Use it when a
# local artefact survives fixes (METHOD.md candidate rule: unit-test the primitive, don't keep editing data).
# Usage: python part_lab.py <case_dir> <landmark|x,y,z> <half_size_m> <vox_m> <out_prefix> [open_deg]
# open_deg: also writes <out_prefix>_open.ply with the lower jaw rotated about L["jaw_hinge"] using the rig's own
# weights (mouth_geom.jaw_weight) - preview the meow shape without rigging.
# Writes <out_prefix>.ply and <out_prefix>_frame.json (head frame + head-local view directions for lab_view.py).
import importlib.util
import json
import os
import sys

import numpy as np
from skimage.measure import marching_cubes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdf_core as S  # noqa: E402

case, where, hsz, vox, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
spec_path = os.path.join(case, "spec.py")
mod = importlib.util.spec_from_file_location("case_spec", spec_path)
spec = importlib.util.module_from_spec(mod)
mod.loader.exec_module(spec)
prims, L = spec.build(spec.P)
c = np.array(L[where], float) if where in L else np.array([float(t) for t in where.split(",")])
lo, hi = c - hsz, c + hsz
F, owner = S.evaluate(prims, lo, hi, vox)
F[0, :, :] = F[-1, :, :] = F[:, 0, :] = F[:, -1, :] = F[:, :, -1] = vox     # close the box
v, f, _, _ = marching_cubes(F, 0.0, spacing=(vox,) * 3, gradient_direction="ascent", allow_degenerate=False)
v += lo
S.write_ply(out + ".ply", v, f)
R = np.array(L["head_R"])
if len(sys.argv) > 6:
    import mouth_geom as MG
    H0, hs = np.array(L["head"]), spec.P["head_scale"]
    hl = ((v - H0) @ R) / hs
    hinge = ((np.array(L["jaw_hinge"]) - H0) @ R) / hs
    vo = (MG.open_jaw(hl, MG.from_landmarks(L, hs), hinge, float(sys.argv[6])) * hs) @ R.T + H0
    S.write_ply(out + "_open.ply", vo, f)
    print(f"open-jaw preview {float(sys.argv[6]):.0f} deg -> {out}_open.ply")
views = {   # head-local directions -> world (face front is local -y, up +z, cat's left +x)
    "front": (R @ np.array([0, -1, 0.05])).tolist(),
    "q34_L": (R @ np.array([0.6, -0.8, 0.1])).tolist(),
    "side_L": (R @ np.array([1, -0.05, 0])).tolist(),
    "below": (R @ np.array([0, -0.75, -0.65])).tolist(),
    "q34_R_up": (R @ np.array([-0.6, -0.75, 0.3])).tolist(),
}
json.dump({"center": c.tolist(), "size": 2 * hsz, "views": views}, open(out + "_frame.json", "w"))
if len(sys.argv) > 6:
    json.dump({"center": (c + R @ np.array([0, 0, -0.008])).tolist(), "size": 2 * hsz, "views": views}, open(out + "_open_frame.json", "w"))
print(f"part lab {where}: box {2*hsz*1000:.0f} mm @ {vox*1000:.2f} mm -> {len(f)} faces  {out}.ply")
