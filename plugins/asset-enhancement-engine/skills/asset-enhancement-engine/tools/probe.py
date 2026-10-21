# Blender-side probe: render the model's silhouette (alpha) through the scene camera and
# project the model's landmarks to photo pixels. Expects OUT (path prefix). Optional PREFIX.
# Writes OUT_mask.png and OUT_points.json. Restores every render setting it touches.
import bpy, json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PREFIX = globals().get("PREFIX", "Cat")
sc = bpy.context.scene
r = sc.render
vs = sc.view_settings
saved = (r.engine, r.film_transparent, r.resolution_percentage, r.filepath, r.image_settings.color_mode,
         sc.display.shading.light, sc.display.shading.color_type, sc.display.render_aa, vs.view_transform, vs.look,
         r.dither_intensity)
rig_ = bpy.data.objects.get(f"{PREFIX}_Rig")
pose_saved = rig_.data.pose_position if rig_ else None
if rig_:   # score the model at REST: an active animation posed the head at frame 1 (eyes read 12 px off)
    rig_.data.pose_position = 'REST'
    bpy.context.view_layer.update()
hidden = []
env = bpy.data.objects.get(f"{PREFIX}_FurEnvelope")
body_ = bpy.data.objects.get(f"{PREFIX}_Body")
swap = env is not None
# save EXACT prior render visibility of every Cat object and restore it afterwards. v1 restored the raw body
# to render=True, so a hidden rest-pose copy of the head rendered inside every later image (ghost head on posing).
cat_objs = [o for o in bpy.data.collections[PREFIX].all_objects if o is not None]  # stale None entries seen after deletions
vis_saved = {o.name: o.hide_render for o in cat_objs}
skin_ = bpy.data.objects.get(f"{PREFIX}_Skin")
try:
    if swap:  # silhouette of a furry subject = fur envelope, not skin
        for o in cat_objs:
            o.hide_render = o is not env
    # every state change happens INSIDE the try: v1 hid collections before it, crashed, and left the Studio
    # (lights) hidden -> every later Cycles render came out black
    for c in bpy.data.collections:
        if c.name != PREFIX and not c.hide_render:
            c.hide_render = True
            hidden.append(c)
    r.engine = 'BLENDER_WORKBENCH'
    r.film_transparent = True
    r.resolution_percentage = 50
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGBA'
    sc.display.shading.light = 'FLAT'
    # one render = mask (alpha) + part-ID colours (exact: no AA, no dither, Raw view transform)
    sc.display.shading.color_type = 'VERTEX' if swap else 'SINGLE'
    sc.display.render_aa = 'OFF'
    vs.view_transform, vs.look = 'Raw', 'None'
    r.dither_intensity = 0.0
    r.filepath = OUT + "_mask.png"
    bpy.ops.render.render(write_still=True)
finally:
    (r.engine, r.film_transparent, r.resolution_percentage, r.filepath, r.image_settings.color_mode,
     sc.display.shading.light, sc.display.shading.color_type, sc.display.render_aa, vs.view_transform, vs.look,
     r.dither_intensity) = saved
    for c in hidden:
        c.hide_render = False
    for nm, hr in vis_saved.items():
        bpy.data.objects[nm].hide_render = hr

body = bpy.data.objects[f"{PREFIX}_Body"]
L = json.load(open(body["landmarks_file"]))["landmarks"]
mw = body.matrix_world
W, H = r.resolution_x, r.resolution_y


def px(p):
    v = world_to_camera_view(sc, sc.camera, Vector(p))
    return [v.x * W, (1 - v.y) * H]


pts = {}
for side in "RL":
    eye = bpy.data.objects.get(f"{PREFIX}_Eye.{side}")
    if eye:  # pupil = front of the eyeball along its gaze (-Y local)
        front = eye.matrix_world @ Vector((0, -1, 0))
        pts[f"eye.{side}"] = px(front)
for k in ("nose", "chin", "ear_tip.R", "ear_tip.L"):
    if k in L:
        pts[k] = px(mw @ Vector(L[k]))
for k in ("fpaw.R", "fpaw.L", "hpaw.R", "hpaw.L"):
    if k in L:
        p = L[k]
        pts[k] = px(mw @ Vector((p[0], p[1] - 0.014, 0.0)))
if "tail" in L:
    pts["tail_tip"] = px(mw @ Vector(L["tail"][-1]))
json.dump({"image_size": [W, H], "points": pts}, open(OUT + "_points.json", "w"), indent=1)
print("probe written", OUT)
if rig_:
    rig_.data.pose_position = pose_saved
