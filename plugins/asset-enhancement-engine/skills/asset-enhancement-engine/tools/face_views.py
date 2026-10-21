# Blender-side: face close-ups that FOLLOW THE POSED HEAD at the current frame (the head turns during the idle),
# via views.py. Directions are head-local (face front = local -y), carried by the head bone's pose delta.
# Globals: OUT (png), VIEWS_PY (path to views.py), FRAME (optional), CLAY (True = hide fur/whiskers: skin + teeth +
# tongue only), SIZE (default 0.05), LANDMARK (default 'mouth_front'), PREFIX.
import bpy, json
import numpy as np
from mathutils import Matrix, Vector

PREFIX = globals().get("PREFIX", "Cat")
sc = bpy.context.scene
rig = bpy.data.objects[f"{PREFIX}_Rig"]
skin = bpy.data.objects[f"{PREFIX}_Skin"]
_fv_frame0 = sc.frame_current
_fv_vis = {o.name: o.hide_render for o in bpy.data.objects}
try:
    if "FRAME" in globals():
        sc.frame_set(int(FRAME))
    J = json.load(open(skin["landmarks_file"]))
    L = J["landmarks"]
    R = np.array(L["head_R"])
    hb = rig.pose.bones["head"]
    D = (rig.matrix_world @ hb.matrix) @ (rig.matrix_world @ hb.bone.matrix_local).inverted()   # rest -> posed (world)
    D3 = np.array(D.to_3x3())
    c = D @ Vector(L[globals().get("LANDMARK", "mouth_front")])
    dirs = {"front": (0, -1, 0.05), "q34_L": (0.6, -0.8, 0.1), "side_L": (1, -0.05, 0), "below": (0, -0.75, -0.65),
            "q34_R": (-0.6, -0.8, 0.1)}
    VIEWS = {k: (tuple(D3 @ (R @ np.array(d, float))), True) for k, d in dirs.items()}
    if globals().get("CLAY", True):
        for o in bpy.data.objects:
            if o.name in (f"{PREFIX}_Fur", f"{PREFIX}_Body", f"{PREFIX}_SkinRef", f"{PREFIX}_FurEnvelope") or "Whisk" in o.name:
                o.hide_render = True
    CENTER = tuple(c); SIZE = globals().get("SIZE", 0.05)
    exec(open(VIEWS_PY).read())
finally:
    for n, h in _fv_vis.items():
        if n in bpy.data.objects:
            bpy.data.objects[n].hide_render = h
    sc.frame_set(_fv_frame0)
print("face views", OUT)
