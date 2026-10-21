"""(background Blender) CLAY SHOTS LIT SO FINE RELIEF SHOWS: one low, raking key light, the same camera and light for
every mesh, so two skins render side by side as a fair pair. Made in build 13a3 (cases/woman2/build13/a3_bl_rake.py),
moved here in build A1 (2026-10-21); engine/review/clay_pairs.py runs it and lays the pairs out.
    blender -b --factory-startup --python clay_rake_bl.py -- VIEWS.json OUT_DIR TAG=MESH.npz [TAG=MESH.npz ...]

MESH.npz: v and either poly_sizes + poly_verts (any polygons) or f (triangles).
VIEWS.json: {"resolution", "samples", "views": [{"name", "loc", "target", "lens" | "ortho"+"ortho_scale", "resolution"?,
"rake_from"?, "rake_elev"?}]}. Each view is rendered once per mesh, OUT_DIR/<TAG>/<name>.png. Light: a sun with a 1 deg
disc that grazes the skin facing the camera - it comes from above the view (or its side: "rake_from", degrees, 0 top,
90 right, -90 left), "rake_elev" (12 deg) off the plane at right angles to the view axis, so a surface facing the
camera is lit at 78 deg incidence and a relief of slope s changes the light by ~ s / tan(12 deg), 4.7x what it would be
under head-on light; a dim even world (0.25) keeps the shadowed side readable. Clay (0.62, 0.60, 0.58), roughness 0.55.
Cycles, denoised (GPU when CUDA is there, else CPU). Output paths are made absolute (a relative path in -b lands under
Blender's own folder).
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
views_path, out_dir = a[0], os.path.abspath(a[1])
meshes = [x.split("=", 1) for x in a[2:]]
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "engine", "tools"))
import build_base_torso as BB  # noqa: E402

VW = json.load(open(views_path))
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
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
sc.view_settings.view_transform = "AgX"
world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.18, 0.18, 0.19, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.25
clay = bpy.data.materials.new("Clay"); clay.use_nodes = True
bs = clay.node_tree.nodes["Principled BSDF"]
bs.inputs["Base Color"].default_value = (0.62, 0.60, 0.58, 1.0); bs.inputs["Roughness"].default_value = 0.55
sun_d = bpy.data.lights.new("Rake", "SUN"); sun_d.energy = 4.5; sun_d.angle = math.radians(1.0)
sun = bpy.data.objects.new("Rake", sun_d); sc.collection.objects.link(sun)
cam_d = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam

objs = {}
for tag, path in meshes:
    Z = np.load(path)
    if "poly_verts" in Z.files:
        pv, ps = Z["poly_verts"], Z["poly_sizes"]
    else:
        pv, ps = Z["f"].astype(np.int64).ravel(), np.full(len(Z["f"]), 3)
    me = BB._make_mesh("Body_" + tag, Z["v"].astype(np.float32), pv, ps)
    ob = bpy.data.objects.new("Body_" + tag, me); sc.collection.objects.link(ob)
    ob.data.materials.append(clay)
    objs[tag] = ob

for v in VW["views"]:
    loc = Vector(v["loc"]); tgt = Vector(v["target"]); fwd = (tgt - loc).normalized()
    up = Vector((0, 0, 1)); up_t = (up - fwd * up.dot(fwd)).normalized(); right = fwd.cross(up_t).normalized()
    # the light comes from the image's top (rake_from 0), right (90) or left (-90), across the view, tilted 12 deg
    # into the surface that faces the camera
    az = math.radians(v.get("rake_from", 0.0)); src = up_t * math.cos(az) + right * math.sin(az)
    el = math.radians(v.get("rake_elev", 12.0))
    ld = (-src * math.cos(el) + fwd * math.sin(el)).normalized()
    sun.rotation_euler = ld.to_track_quat("-Z", "Y").to_euler()
    cam.location = loc; cam.rotation_euler = fwd.to_track_quat("-Z", "Y").to_euler()
    if v.get("ortho", False):
        cam_d.type = "ORTHO"; cam_d.ortho_scale = v["ortho_scale"]
    else:
        cam_d.type = "PERSP"; cam_d.lens = v.get("lens", 85.0)
    cam_d.clip_start = 0.005; cam_d.clip_end = 20
    sc.render.resolution_x, sc.render.resolution_y = v.get("resolution", VW.get("resolution", [1200, 1200]))
    for tag, ob in objs.items():
        for t2, o2 in objs.items():
            o2.hide_render = t2 != tag
        os.makedirs(os.path.join(out_dir, tag), exist_ok=True)
        sc.render.filepath = os.path.join(out_dir, tag, v["name"] + ".png")
        bpy.ops.render.render(write_still=True)
        print("shot", tag, v["name"], flush=True)
