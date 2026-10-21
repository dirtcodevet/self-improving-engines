# Blender-side: turn the raw SDF skin (<PREFIX>_Body, marching-cubes triangles) into a production mesh
# <PREFIX>_Skin: Laplacian de-stair -> QuadriFlow quads -> shrinkwrap back onto the smoothed hi-res
# surface -> subdivision (live). The raw body stays (hidden) for probes/regression.
# Optional globals: PREFIX, TARGET_FACES (default 60000), SMOOTH_ITERS (default 6).
import bpy, time

PREFIX = globals().get("PREFIX", "Cat")
TARGET = globals().get("TARGET_FACES", 300000)
SMOOTH_ITERS = globals().get("SMOOTH_ITERS", 6)
t0 = time.time()
src = bpy.data.objects[f"{PREFIX}_Body"]
coll = src.users_collection[0]

# 1) smoothed hi-res reference (shrinkwrap target)
ref_name = f"{PREFIX}_SkinRef"
old = bpy.data.objects.get(ref_name)
if old:
    bpy.data.objects.remove(old, do_unlink=True)
import os
_lm = src["landmarks_file"]; _pre = _lm[:-len("_landmarks.json")]
if os.path.exists(_pre + "_hr.ply") and os.path.exists(_pre + "_lr.ply"):
    # two-resolution meshing: union the fine head box + the cut coarse body (both closed) via the voxel remesh below
    parts = []
    for suf in ("_lr", "_hr"):
        before = set(bpy.data.objects)
        bpy.ops.wm.ply_import(filepath=_pre + suf + ".ply")
        parts += [o for o in bpy.data.objects if o not in before]
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    with bpy.context.temp_override(active_object=parts[0], object=parts[0], selected_objects=parts, selected_editable_objects=parts):
        bpy.ops.object.join()
    ref = parts[0]
    for c in list(ref.users_collection):
        c.objects.unlink(ref)
    coll.objects.link(ref)
    ref.name = ref_name
    print("two-resolution parts joined:", len(ref.data.polygons), "faces")
else:
    ref = src.copy()
    ref.data = src.data.copy()
    ref.name = ref_name
    coll.objects.link(ref)
m = ref.modifiers.new("destair", 'LAPLACIANSMOOTH')
m.iterations, m.lambda_factor, m.lambda_border = SMOOTH_ITERS, 0.6, 0.0
m.use_volume_preserve, m.use_normalized = True, True
with bpy.context.temp_override(object=ref, active_object=ref, selected_objects=[ref]):
    bpy.ops.object.modifier_apply(modifier=m.name)
# marching-cubes output can carry a few non-manifold ambiguities; QuadriFlow refuses those.
# A fine voxel remesh guarantees a closed manifold with consistent normals.
two_res = os.path.exists(_pre + "_hr.ply")
ref.data.remesh_voxel_size = globals().get("VOXEL", 0.00045 if two_res else 0.0006)   # keep the hires head detail
ref.data.use_remesh_fix_poles = True
with bpy.context.temp_override(object=ref, active_object=ref, selected_objects=[ref]):
    bpy.ops.object.voxel_remesh()
print("voxel remesh:", len(ref.data.polygons), "faces")

# 2) production skin. MODE "decimate" (default): fine voxel remesh -> collapse decimation. Robust for
# thin parts (ears, lips, lid margins) - QuadriFlow collapsed an ear at 58k AND at 117k faces (fidelity
# check: 37 mm error at the ear tip) and would seal a 1.8 mm mouth slit. MODE "quadriflow" kept for bodies
# without thin parts.
MODE = globals().get("MODE", "decimate")
skin_name = f"{PREFIX}_Skin"
old = bpy.data.objects.get(skin_name)
old_mats = list(old.data.materials) if old else []
old_mods = []
if old:
    bpy.data.objects.remove(old, do_unlink=True)
skin = ref.copy()
skin.data = ref.data.copy()
skin.name = skin_name
coll.objects.link(skin)
for o in bpy.context.view_layer.objects:
    o.select_set(False)
bpy.context.view_layer.objects.active = skin
skin.select_set(True)
from mathutils import Matrix
if MODE == "quadriflow":
    skin.data.transform(Matrix.Scale(100.0, 4))  # QuadriFlow rejects sub-mm edges in metres
    with bpy.context.temp_override(object=skin, active_object=skin, selected_objects=[skin], selected_editable_objects=[skin]):
        res = bpy.ops.object.quadriflow_remesh(mode='FACES', target_faces=TARGET, seed=7)
    skin.data.transform(Matrix.Scale(0.01, 4))
    if res != {'FINISHED'}:
        raise RuntimeError(f"QuadriFlow failed: {res}")
else:
    dm = skin.modifiers.new("decimate", 'DECIMATE')
    dm.decimate_type, dm.ratio = 'COLLAPSE', min(1.0, TARGET / max(len(skin.data.polygons), 1))
    with bpy.context.temp_override(object=skin, active_object=skin, selected_objects=[skin]):
        bpy.ops.object.modifier_apply(modifier=dm.name)
print(MODE, "faces", len(skin.data.polygons), f"{time.time()-t0:.1f}s")

# 3) shrinkwrap back onto the de-staired hi-res surface, then live subdivision
sw = skin.modifiers.new("fit", 'SHRINKWRAP')
sw.target, sw.wrap_method, sw.wrap_mode = ref, 'NEAREST_SURFACEPOINT', 'ON_SURFACE'
with bpy.context.temp_override(object=skin, active_object=skin, selected_objects=[skin]):
    bpy.ops.object.modifier_apply(modifier=sw.name)
for p in skin.data.polygons:
    p.use_smooth = True
if MODE == "quadriflow":
    sd = skin.modifiers.new("subd", 'SUBSURF')
    sd.levels, sd.render_levels, sd.quality = 1, 2, 3
for mt in old_mats:
    skin.data.materials.append(mt)
if not skin.data.materials and src.data.materials:
    skin.data.materials.append(src.data.materials[0])

skin.hide_set(False)
skin.hide_render = False  # copies inherit hide flags from earlier runs - always reset explicitly
ref.hide_set(True)
ref.hide_render = True
src.hide_set(True)
src.hide_render = True
skin["landmarks_file"] = src["landmarks_file"]

# FIDELITY CHECK: every hi-res surface point must lie close to the quad skin (catches thin parts -
# ears - that QuadriFlow collapses; v9 at 58k faces lost the right ear).
from mathutils.bvhtree import BVHTree
import numpy as np
dg = bpy.context.evaluated_depsgraph_get()
bvh = BVHTree.FromObject(skin, dg)  # evaluated = with subdivision
co = np.empty(len(ref.data.vertices) * 3, np.float32)
ref.data.vertices.foreach_get("co", co)
co = co.reshape(-1, 3)[::7]
d = np.array([(bvh.find_nearest(tuple(p))[3] or 0.0) for p in co])
worst = co[int(np.argmax(d))]
LIMIT = globals().get("FIDELITY_MM", 1.5)
skin["fidelity_p99_mm"] = float(np.percentile(d, 99) * 1000)
skin["fidelity_max_mm"] = float(d.max() * 1000)
print(f"fidelity: p99 {np.percentile(d, 99)*1000:.2f} mm  max {d.max()*1000:.2f} mm at {np.round(worst, 3)}  "
      f"-> {'PASS' if d.max()*1000 <= LIMIT else 'FAIL'} (limit {LIMIT} mm)")
print("production skin ready:", len(skin.data.vertices), "verts", len(skin.data.polygons), "faces",
      f"total {time.time()-t0:.1f}s")
