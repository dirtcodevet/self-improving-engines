# Blender-side: show the L1 FRAME in the person's viewport (frame.json from frame_fit.py): bones as clay capsules
# (right side warm, left side cool, spine green) in a "Frame" collection, the current model as a see-through
# wireframe with its fur hidden, and the viewport aimed at the cat. Rebuilds the collection each run.
# Globals: FRAME (frame.json path), PREFIX ("Cat"), GHOST (True: show the old skin as wire, hide fur)
import bpy, bmesh, json
import numpy as np
from mathutils import Vector

PREFIX = globals().get("PREFIX", "Cat")
D = json.load(open(FRAME)); J = {k: Vector(v) for k, v in D["joints"].items()}
s = D["pose"]["s"]
col = bpy.data.collections.get("Frame")
if col:
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:
    col = bpy.data.collections.new("Frame"); bpy.context.scene.collection.children.link(col)


def mat(name, rgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0); return m


MR, ML, MS = mat("FrameR", (0.95, 0.75, 0.30)), mat("FrameL", (0.35, 0.60, 0.95)), mat("FrameSpine", (0.40, 0.85, 0.45))
RAD = {"humerus": 0.0045, "radius": 0.0035, "femur": 0.0050, "tibia": 0.0040, "scapula": 0.0030}


def capsule(name, a, b, r, m):
    bm = bmesh.new()
    d = b - a; L = d.length
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r, radius2=r * 0.85, depth=L)
    for p in (a, b):
        sp = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r * 1.25)
        bmesh.ops.translate(bm, verts=sp["verts"], vec=Vector((0, 0, (L / 2 if p is b else -L / 2))))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    ob.location = (a + b) / 2
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = d.to_track_quat('Z', 'Y')
    ob.data.materials.append(m); ob.color = (*m.diffuse_color[:3], 1)
    return ob


pairs = []
for sd in "RL":
    pairs += [(f"shoulder.{sd}", f"elbow.{sd}", 0.0045), (f"elbow.{sd}", f"wrist.{sd}", 0.0035), (f"wrist.{sd}", f"mcp.{sd}", 0.0025),
              (f"mcp.{sd}", f"fpaw.{sd}", 0.0025), (f"shoulder.{sd}", f"scapula_top.{sd}", 0.0035), (f"hip.{sd}", f"knee.{sd}", 0.0050),
              (f"knee.{sd}", f"hock.{sd}", 0.0040), (f"hock.{sd}", f"mtp.{sd}", 0.0028), (f"mtp.{sd}", f"hpaw.{sd}", 0.0025),
              (f"hock.{sd}", f"calcaneus.{sd}", 0.0028)]
pairs += [("sacrum", "spine_mid", 0.006), ("spine_mid", "withers", 0.006), ("hip.R", "hip.L", 0.004), ("shoulder.R", "shoulder.L", 0.003)]
for a, b, r in pairs:
    if a in J and b in J:
        m = MS if not (a.endswith(".R") or a.endswith(".L")) or (a[:-2] == b[:-2] == "hip") or a.startswith("shoulder.R") and b.startswith("shoulder.L") else (MR if a.endswith(".R") else ML)
        capsule(f"Frame_{a}-{b}", J[a], J[b], r * s, m)
if globals().get("GHOST", True):
    for o in bpy.data.objects:                                   # clutter that hid the frame (v1 viewport check)
        if (o.name in (f"{PREFIX}_Fur", f"{PREFIX}_Rig", f"{PREFIX}_Body", f"{PREFIX}_SkinRef", f"{PREFIX}_FurEnvelope",
                       "Ref3D_Body", "Studio_Sweep") or o.name.startswith(f"{PREFIX}_Acc_")):
            o.hide_set(True)
    sk = bpy.data.objects.get(f"{PREFIX}_Skin")
    if sk:                                                       # a dense wireframe draws as a black blob: light grey + X-ray
        sk.display_type = 'SOLID'; sk.color = (0.80, 0.80, 0.82, 1.0)
# aim every 3-D viewport at the frame, solid shading with object colours
centre = sum((J[k] for k in J), Vector()) / len(J)
for win in bpy.context.window_manager.windows:
    for area in win.screen.areas:
        if area.type == 'VIEW_3D':
            sp = area.spaces.active
            sp.shading.type = 'SOLID'; sp.shading.color_type = 'OBJECT'
            sp.shading.show_xray = True; sp.shading.xray_alpha = 0.35
            r3 = sp.region_3d
            r3.view_location = centre; r3.view_distance = 0.75
            r3.view_rotation = Vector((-0.35, -0.85, 0.35)).to_track_quat('Z', 'Y')
            r3.view_perspective = 'PERSP'
print("frame shown:", len(col.objects), "pieces; size factor", round(s, 3))
