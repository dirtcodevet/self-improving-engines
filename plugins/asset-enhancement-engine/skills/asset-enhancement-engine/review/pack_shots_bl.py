"""(background Blender) LABELLED SHOTS OF A PACK'S MESH, clay or the pack's own skin material, from any list of cameras.
Made in build 13a (cases/woman2/build13/bl_shots.py), moved here in build A1 (2026-10-21). For a raking-light pair of
two skins use clay_pairs.py; for fixed front / side / top views of PLY files, clay_sheet.py.
    blender -b --factory-startup --python pack_shots_bl.py -- MESH.npz VIEWS.json OUT_DIR [PACK_DIR]

MESH.npz: v, poly_sizes, poly_verts, uv (corners); optional per-vertex attributes (skin_colour (n,4), skin_roughness,
skin_sss_scale, breast, areola, nipple, relief_uv_L, nac_uv, nac_map) read by the pack's skin material
(materials.json, engine/tools/build_base_torso.py's graph builder).
VIEWS.json: {"resolution": [w, h], "samples", "views": [{"name", "mode": "clay"|"colour", "ortho": bool, "loc": [x,y,z],
"target": [x,y,z], "ortho_scale" | "lens", "resolution"?}]}. Lights: a key from the camera's upper left, a fill from its
right, a rim from behind. OUT_DIR is made absolute (a relative path in -b lands under Blender's own folder).
"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
mesh_path, views_path, out_dir = a[0], a[1], os.path.abspath(a[2])
pack_dir = a[3] if len(a) > 3 else None
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "engine", "tools"))
import build_base_torso as BB  # noqa: E402

os.makedirs(out_dir, exist_ok=True)
Z = np.load(mesh_path)
VW = json.load(open(views_path))
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
me = BB._make_mesh("Body", Z["v"].astype(np.float32), Z["poly_verts"], Z["poly_sizes"])
if "uv" in Z.files:
    BB._add_uv(me, Z["uv"], "UVMap")
for k in ("skin_roughness", "skin_sss_scale", "nac_map"):
    if k in Z.files:
        at = me.attributes.new(k, "FLOAT", "POINT"); at.data.foreach_set("value", Z[k].astype(np.float32))
for k in ("breast", "areola", "nipple", "tubercle", "vein"):
    if k in Z.files:
        at = me.attributes.new("zone_%s.001" % k, "FLOAT", "POINT"); at.data.foreach_set("value", Z[k].astype(np.float32))
for k in ("relief_uv_L", "nac_uv"):
    if k in Z.files:
        at = me.attributes.new(k, "FLOAT2", "POINT"); at.data.foreach_set("vector", Z[k].astype(np.float32).ravel())
if "skin_colour" in Z.files:
    ca = me.color_attributes.new("skin_colour", "FLOAT_COLOR", "POINT"); ca.data.foreach_set("color", Z["skin_colour"].astype(np.float32).ravel())
ob = bpy.data.objects.new("Body", me)
bpy.context.scene.collection.objects.link(ob)

clay = bpy.data.materials.new("Clay"); clay.use_nodes = True
bs = clay.node_tree.nodes["Principled BSDF"]
bs.inputs["Base Color"].default_value = (0.62, 0.60, 0.58, 1.0); bs.inputs["Roughness"].default_value = 0.55
colour = None
if pack_dir and os.path.exists(os.path.join(pack_dir, "materials.json")):
    spec = json.load(open(os.path.join(pack_dir, "materials.json")))["skin"]
    colour = BB._graph_material("Skin", spec, pack_dir)

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = int(VW.get("samples", 48)); sc.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "CUDA"; prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    sc.cycles.device = "GPU"
except Exception:
    sc.cycles.device = "CPU"
sc.render.resolution_x, sc.render.resolution_y = VW.get("resolution", [1200, 1500])
sc.render.film_transparent = False
sc.view_settings.view_transform = "AgX"
world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.18, 0.18, 0.19, 1); world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6


def light(name, loc, energy, size):
    ld = bpy.data.lights.new(name, "AREA"); ld.energy = energy; ld.size = size
    lo = bpy.data.objects.new(name, ld); sc.collection.objects.link(lo); lo.location = loc
    d = Vector((0, 0, -0.4)) - Vector(loc); lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return lo


cam_d = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
lights = []
for v in VW["views"]:
    for lo in lights:
        bpy.data.objects.remove(lo, do_unlink=True)
    loc = Vector(v["loc"]); tgt = Vector(v["target"]); fwd = (tgt - loc).normalized()
    side = fwd.cross(Vector((0, 0, 1))).normalized()
    # key from the camera's upper left, fill from its right, rim from behind
    lights = [light("Key", tuple(loc + 1.2 * (-side) + Vector((0, 0, 1.0)) - 0.2 * fwd), 220.0, 1.5),
              light("Fill", tuple(loc + 1.4 * side + Vector((0, 0, 0.2))), 80.0, 2.0),
              light("Rim", tuple(tgt - 1.5 * fwd + Vector((0, 0, 1.2))), 150.0, 1.5)]
    cam.location = loc; cam.rotation_euler = fwd.to_track_quat("-Z", "Y").to_euler()
    if v.get("ortho", False):
        cam_d.type = "ORTHO"; cam_d.ortho_scale = v["ortho_scale"]
    else:
        cam_d.type = "PERSP"; cam_d.lens = v.get("lens", 85.0)
    cam_d.clip_start = 0.005; cam_d.clip_end = 20
    ob.data.materials.clear()
    ob.data.materials.append(colour if (v["mode"] == "colour" and colour is not None) else clay)
    if "resolution" in v:
        sc.render.resolution_x, sc.render.resolution_y = v["resolution"]
    else:
        sc.render.resolution_x, sc.render.resolution_y = VW.get("resolution", [1200, 1500])
    sc.render.filepath = os.path.join(out_dir, v["name"] + ".png")
    bpy.ops.render.render(write_still=True)
    print("shot", v["name"], flush=True)
