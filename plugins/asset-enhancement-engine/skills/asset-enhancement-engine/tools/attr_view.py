# Blender-side debug: render the skin's colour attribute flat & unlit through the scene camera (Workbench),
# fur hidden. Shows exactly where a painted pattern landed. Globals: OUT, ATTR (default 'coat'), BORDER.
import bpy
PREFIX = globals().get("PREFIX", "Cat")
sc = bpy.context.scene; r = sc.render; sh = sc.display.shading; vs = sc.view_settings
skin = bpy.data.objects[f"{PREFIX}_Skin"]
me = skin.data
ATTR = globals().get("ATTR", "coat")
me.color_attributes.active_color = me.color_attributes[ATTR]
hide = [o for o in bpy.data.objects if o.type == 'CURVES' and not o.hide_render]
for o in hide:
    o.hide_render = True
saved = (r.engine, sh.light, sh.color_type, vs.view_transform, vs.look, r.resolution_percentage, r.filepath,
         r.use_border, r.use_crop_to_border, r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y)
try:
    r.engine = 'BLENDER_WORKBENCH'; sh.light = 'FLAT'; sh.color_type = 'VERTEX'
    vs.view_transform, vs.look = 'Standard', 'None'
    r.resolution_percentage = 100
    B = globals().get("BORDER")
    if B:
        r.use_border = r.use_crop_to_border = True
        r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y = B
    r.filepath = OUT
    bpy.ops.render.render(write_still=True)
finally:
    (r.engine, sh.light, sh.color_type, vs.view_transform, vs.look, r.resolution_percentage, r.filepath,
     r.use_border, r.use_crop_to_border, r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y) = saved
    for o in hide:
        o.hide_render = False
print("attr view", OUT)
