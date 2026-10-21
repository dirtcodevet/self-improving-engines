# CLAY SHEET in a BACKGROUND Blender (never touches the person's live scene): one or more PLY meshes rendered as
# colourless clay (Workbench studio light, cavity on), orthographic front / side / top / three-quarter, one PNG per
# view + a sheet. Model frame: x = subject's left, y = backward (front = -y), z = up.
# usage: blender -b --factory-startup --python clay_sheet.py -- <out_prefix> <mesh.ply> [more.ply ...] [--size 0.12]
#        [--views front,side,top,three_quarter,front_low] [--res 700]
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]; plys = []; size = None; views = ["front", "side", "top", "three_quarter"]; res = 700
i = 1
while i < len(argv):
    if argv[i] == "--size": size = float(argv[i + 1]); i += 2
    elif argv[i] == "--views": views = argv[i + 1].split(","); i += 2
    elif argv[i] == "--res": res = int(argv[i + 1]); i += 2
    else: plys.append(argv[i]); i += 1

sc = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
objs = []
for p in plys:
    before = set(bpy.data.objects)
    bpy.ops.wm.ply_import(filepath=p)
    for o in set(bpy.data.objects) - before:
        for f in o.data.polygons: f.use_smooth = True
        objs.append(o)
lo = Vector((min(min((o.matrix_world @ v.co)[a] for v in o.data.vertices) for o in objs) for a in range(3)))
hi = Vector((max(max((o.matrix_world @ v.co)[a] for v in o.data.vertices) for o in objs) for a in range(3)))
c = (lo + hi) / 2; ext = max(hi - lo)
size = size or ext * 1.25
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "SINGLE"; sh.single_color = (0.82, 0.80, 0.76)
sh.show_cavity = True; sh.cavity_type = "BOTH"; sh.show_shadows = True
sc.display.shadow_shift = 0.1
sc.render.resolution_x = sc.render.resolution_y = res
sc.render.film_transparent = False
sc.world = sc.world or bpy.data.worlds.new("W")
cam = bpy.data.cameras.new("C"); cam.type = "ORTHO"; cam.ortho_scale = size; cam.clip_start = 0.001; cam.clip_end = 10
co = bpy.data.objects.new("C", cam); sc.collection.objects.link(co); sc.camera = co
DIRS = {"front": (0, -1, 0), "side": (1, 0, 0), "top": (0, 0, 1), "three_quarter": (0.75, -1, 0.45),
        "front_low": (0, -1, -0.25), "side_right": (-1, 0, 0), "back": (0, 1, 0)}
for v in views:
    d = Vector(DIRS[v]).normalized()
    co.location = c + d * 2.0
    up = Vector((0, -1, 0)) if v == "top" else Vector((0, 0, 1))
    co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    if v == "top":
        co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        import math
        co.rotation_euler = (0, 0, math.pi)                        # look down, front (-y) at the top of the image
    sc.render.filepath = f"{out}_{v}.png"
    bpy.ops.render.render(write_still=True)
print("clay sheet:", out, views, "size", round(size, 4))
