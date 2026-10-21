# Blender-side: ORTHOGRAPHIC head render along a given head frame (face-on / profile / below), transparent
# background, Workbench (TEXTURE or SINGLE), for outline + feature comparison between OUR model and a reference
# (normalised by eye spacing afterwards). Writes OUT (RGBA png) and OUT.json (pixels-per-metre + projected points).
# Globals: OBJS (object names to show), CENTER, FWD (face-front dir, world), UP (world), SIZE (ortho width m),
# RES (px), SHADE ('TEXTURE' | 'SINGLE'), POINTS (optional {name: world xyz} to project), OUT.
import bpy, json
import numpy as np
from mathutils import Vector, Matrix
sc = bpy.context.scene; r = sc.render; sh = sc.display.shading
fwd = Vector(FWD).normalized(); up = (Vector(UP) - Vector(UP).dot(fwd) * fwd).normalized(); right = up.cross(fwd)
cam_d = bpy.data.cameras.new("_ho_cam"); cam = bpy.data.objects.new("_ho_cam", cam_d); sc.collection.objects.link(cam)
cam_d.type = 'ORTHO'; cam_d.ortho_scale = SIZE; cam_d.clip_start = 0.001; cam_d.clip_end = 10
cam.matrix_world = Matrix.Translation(Vector(CENTER) + fwd * 2.0) @ Matrix((right, up, fwd)).transposed().to_4x4()
vs = sc.view_settings
saved = (sc.camera, r.engine, r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.film_transparent,
         sh.light, sh.color_type, sh.show_cavity, vs.view_transform, vs.look, r.use_border)
vis = {o.name: (o.hide_render, o.hide_viewport) for o in bpy.data.objects}
try:
    for o in bpy.data.objects:
        show = o.name in OBJS
        o.hide_render = not show
        if show:
            o.hide_viewport = False
    sc.camera = cam
    r.engine = 'BLENDER_WORKBENCH'; r.resolution_x = r.resolution_y = RES; r.resolution_percentage = 100
    r.film_transparent = True; r.use_border = False
    sh.light, sh.color_type, sh.show_cavity = 'STUDIO', SHADE, True
    sh.single_color = (0.85, 0.82, 0.8)
    vs.view_transform, vs.look = 'Standard', 'None'
    r.filepath = OUT
    bpy.ops.render.render(write_still=True)
finally:
    (sc.camera, r.engine, r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.film_transparent,
     sh.light, sh.color_type, sh.show_cavity, vs.view_transform, vs.look, r.use_border) = saved
    for n, (hr, hv) in vis.items():
        if n in bpy.data.objects:
            bpy.data.objects[n].hide_render, bpy.data.objects[n].hide_viewport = hr, hv
    bpy.data.objects.remove(cam, do_unlink=True); bpy.data.cameras.remove(cam_d)
ppm = RES / SIZE
pts = {}
for k, p in (globals().get("POINTS") or {}).items():
    d = Vector(p) - Vector(CENTER)
    pts[k] = [RES / 2 + d.dot(right) * ppm, RES / 2 - d.dot(up) * ppm]
json.dump({"ppm": ppm, "points": pts, "res": RES}, open(OUT + ".json", "w"))
print("head_ortho", OUT)
