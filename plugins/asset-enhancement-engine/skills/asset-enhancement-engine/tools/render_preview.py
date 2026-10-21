# Blender-side: Cycles preview render through the scene camera. Restores settings afterwards.
# Globals: OUT (png). Optional: SAMPLES (64), PCT (50), BORDER (x0,y0,x1,y1 in 0..1, y up) for a crop,
# SIDE_BY_SIDE (path of the reference photo -> writes OUT_cmp.png with photo | render), DENOISE (True; False for
# review renders: OIDN smears sub-pixel hair strands - v37: ear texture -61 % denoised vs -44 % raw at 1024 spp).
import bpy, os

sc = bpy.context.scene
r = sc.render
cy = sc.cycles
SAMPLES = globals().get("SAMPLES", 64)
PCT = globals().get("PCT", 50)
BORDER = globals().get("BORDER", None)
DENOISE = globals().get("DENOISE", True)
saved = (r.engine, cy.samples, r.resolution_percentage, r.filepath, r.use_border, r.use_crop_to_border,
         r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y, r.film_transparent, cy.use_denoising)
try:
    r.engine = 'CYCLES'
    cy.samples = SAMPLES
    cy.use_denoising = DENOISE
    cy.max_bounces, cy.transparent_max_bounces = 12, 16
    r.resolution_percentage = PCT
    r.film_transparent = False
    if BORDER:
        r.use_border, r.use_crop_to_border = True, True
        r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y = BORDER
    else:
        r.use_border = False
    r.filepath = OUT
    bpy.ops.render.render(write_still=True)
finally:
    (r.engine, cy.samples, r.resolution_percentage, r.filepath, r.use_border, r.use_crop_to_border,
     r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y, r.film_transparent, cy.use_denoising) = saved
print("render", OUT)
