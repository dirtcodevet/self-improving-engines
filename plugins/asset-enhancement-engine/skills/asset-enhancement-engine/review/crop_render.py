# Blender-side: border-render pixel boxes of the frozen camera view (full-resolution pixel coords, top-left origin)
# at the REST pose and restore every setting it touches. Globals: BOXES {name: [x0, y0, x1, y1]}, OUT_DIR,
# SAMPLES (64), SCALE (1; 2 = double resolution for viewing - boxes stay in full-resolution pixel coords), DENOISE (None = keep the scene's setting; the OIDN denoiser smears sub-pixel hair strands).
# Writes OUT_DIR/<name>.png at 100 % scale.
import bpy, os

sc = bpy.context.scene; r = sc.render; cy = sc.cycles
rig = bpy.data.objects.get("Cat_Rig")
saved = (r.use_border, r.use_crop_to_border, r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y,
         cy.samples, r.filepath, r.resolution_percentage, rig.data.pose_position if rig else None, cy.use_denoising)
try:
    if rig:
        rig.data.pose_position = 'REST'
    W, H = r.resolution_x, r.resolution_y
    r.resolution_percentage = int(round(100 * globals().get("SCALE", 1)))
    r.use_border = True; r.use_crop_to_border = True
    cy.samples = globals().get("SAMPLES", 64)
    if globals().get("DENOISE") is not None:
        cy.use_denoising = DENOISE
    for name, (x0, y0, x1, y1) in BOXES.items():
        r.border_min_x, r.border_max_x = x0 / W, x1 / W
        r.border_min_y, r.border_max_y = 1 - y1 / H, 1 - y0 / H
        r.filepath = os.path.join(OUT_DIR, f"{name}.png")
        bpy.ops.render.render(write_still=True)
finally:
    (r.use_border, r.use_crop_to_border, r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y,
     cy.samples, r.filepath, r.resolution_percentage, pp, cy.use_denoising) = saved
    if rig:
        rig.data.pose_position = pp
print("crop renders ->", OUT_DIR, list(BOXES))
