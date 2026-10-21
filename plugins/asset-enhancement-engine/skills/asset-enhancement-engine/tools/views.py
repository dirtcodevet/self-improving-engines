# Blender-side: orthographic/perspective turnaround contact sheet of the model (Workbench, studio
# light, cavity). Single-view silhouette fitting can hide nonsense in other views - always look.
# Expects OUT (png path). Optional PREFIX. Renders side, front, top, back-3/4 and hero-3/4.
import bpy, math, os
from mathutils import Vector

PREFIX = globals().get("PREFIX", "Cat")
sc = bpy.context.scene
r = sc.render
body = bpy.data.objects[f"{PREFIX}_Body"]
bb = [body.matrix_world @ Vector(c) for c in body.bound_box]
lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
ctr = Vector(globals()["CENTER"]) if "CENTER" in globals() else (lo + hi) / 2
size = globals().get("SIZE", max(hi - lo))

cam_d = bpy.data.cameras.new("_views_cam")
cam = bpy.data.objects.new("_views_cam", cam_d)
sc.collection.objects.link(cam)
vs = sc.view_settings
saved = (sc.camera, r.engine, r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.film_transparent,
         sc.display.shading.light, sc.display.shading.color_type, sc.display.shading.show_cavity,
         vs.view_transform, vs.look, vs.exposure, r.use_border)
vs.view_transform, vs.look, vs.exposure, r.use_border = 'Standard', 'None', 0.0, False  # clay views ignore the look grade
hidden = [c for c in bpy.data.collections if c.name != PREFIX and not c.hide_render]
views = globals().get("VIEWS") or {   # VIEWS = {name: ((dx,dy,dz), ortho)} overrides (part_lab: head-local views)
    "side_L": ((1, 0, 0), True), "front": ((0, -1, 0), True), "top": ((0, 0, 1), True),
    "back34": ((0.7, 0.7, 0.35), False), "hero34": ((0.75, -0.75, 0.3), False),
}
tiles = []
try:
    for c in hidden:   # inside the try so a failure always restores (see probe.py)
        c.hide_render = True
    sc.camera = cam
    r.engine = globals().get('ENGINE', 'BLENDER_WORKBENCH')   # zebra_views: EEVEE with a stripe material override
    r.resolution_x = r.resolution_y = 520
    r.resolution_percentage = 100
    r.film_transparent = False
    sh = sc.display.shading
    sh.light, sh.color_type, sh.show_cavity = 'STUDIO', globals().get('SHADE_COLOR', 'SINGLE'), True   # VERTEX: review heat maps
    sh.single_color = (0.85, 0.82, 0.8)
    for name, (d, ortho) in views.items():
        d = Vector(d).normalized()
        cam.location = ctr + d * size * 3
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y' if abs(d.z) < 0.99 else 'Y').to_euler()
        if abs(d.z) > 0.99:
            cam.rotation_euler = (0, 0, 0)
        cam_d.type = 'ORTHO' if ortho else 'PERSP'
        cam_d.ortho_scale = size * 1.15
        cam_d.lens = 85
        cam_d.clip_end = 100
        cam_d.clip_start = min(0.1, size * 0.2)   # close-ups (part_lab) sit nearer than the 0.1 m default
        p = os.path.splitext(OUT)[0] + f"_{name}.png"
        r.filepath = p
        bpy.ops.render.render(write_still=True)
        tiles.append(p)
finally:
    (sc.camera, r.engine, r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.film_transparent,
     sc.display.shading.light, sc.display.shading.color_type, sc.display.shading.show_cavity,
     vs.view_transform, vs.look, vs.exposure, r.use_border) = saved
    for c in hidden:
        c.hide_render = False
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(cam_d)

# stitch
imgs = [bpy.data.images.load(p) for p in tiles]
import numpy as np
w, h = imgs[0].size
sheet = np.zeros((h, w * len(imgs), 4), np.float32)
for i, im in enumerate(imgs):
    px = np.array(im.pixels[:], np.float32).reshape(h, w, 4)
    sheet[:, i * w:(i + 1) * w] = px
    bpy.data.images.remove(im)
out = bpy.data.images.new("_sheet", w * len(tiles), h, alpha=True)
out.pixels.foreach_set(sheet.ravel())
out.filepath_raw = OUT
out.file_format = 'PNG'
out.save()
bpy.data.images.remove(out)
import time as _time
for p in tiles:      # OneDrive can lock a just-written file for a moment: retry, never fail the review on cleanup
    for _k in range(5):
        try:
            os.remove(p); break
        except OSError:
            _time.sleep(0.4)
print("views sheet", OUT)
