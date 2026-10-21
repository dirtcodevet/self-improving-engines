# Blender-side: show the placed L1 SKULL (skull_place.py output) in the person's viewport next to the frame: cranium
# bone-coloured, mandible a little warmer so the JAW LINE between them reads; collection "Skull" (rebuilt each run);
# the viewport aimed at the head. Globals: SKULL (out prefix of skull_place.py), AIM (True: aim at the head)
import bpy
from mathutils import Vector

col = bpy.data.collections.get("Skull")
if col:
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:
    col = bpy.data.collections.new("Skull"); bpy.context.scene.collection.children.link(col)
COL = {"cranium": (0.93, 0.89, 0.80), "mandible": (0.95, 0.80, 0.62)}
objs = []
for part, rgb in COL.items():
    before = set(bpy.data.objects)
    bpy.ops.wm.ply_import(filepath=f"{SKULL}_{part}.ply")
    for o in set(bpy.data.objects) - before:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o); o.name = f"Skull_{part.capitalize()}"
        for f in o.data.polygons: f.use_smooth = True
        m = bpy.data.materials.get(f"Skull_{part}") or bpy.data.materials.new(f"Skull_{part}")
        m.diffuse_color = (*rgb, 1.0); o.data.materials.append(m); o.color = (*rgb, 1.0)
        objs.append(o)
if globals().get("AIM", True):
    pts = [o.matrix_world @ v.co for o in objs for i, v in enumerate(o.data.vertices) if i % 50 == 0]
    c = sum(pts, Vector()) / len(pts)
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                sp = area.spaces.active
                sp.shading.type = "SOLID"; sp.shading.color_type = "OBJECT"
                sp.shading.show_xray = True; sp.shading.xray_alpha = 0.5
                r3 = sp.region_3d; r3.view_location = c; r3.view_distance = 0.30
                r3.view_rotation = Vector((-0.55, -0.80, 0.25)).to_track_quat("Z", "Y")
print("skull shown:", [o.name for o in objs])
