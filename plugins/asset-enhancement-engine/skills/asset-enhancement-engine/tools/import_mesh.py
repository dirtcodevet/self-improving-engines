# Blender-side: load a generated creature mesh (PLY + landmarks JSON) into the live scene.
# Swaps mesh data in place so modifiers/materials/children survive between iterations.
# Expects globals: MESH (path prefix, no extension). Optional: PREFIX (default "Cat"), COLL.
import bpy, json
from mathutils import Vector

PREFIX = globals().get("PREFIX", "Cat")
COLL = globals().get("COLL", PREFIX)
ply = MESH + ".ply"
lm = json.load(open(MESH + "_landmarks.json"))["landmarks"]
coll = bpy.data.collections.get(COLL) or bpy.data.collections.new(COLL)
if coll.name not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(coll)

before = set(bpy.data.objects)
bpy.ops.wm.ply_import(filepath=ply)
new = [o for o in bpy.data.objects if o not in before][0]
new_mesh = new.data
bpy.data.objects.remove(new, do_unlink=True)

body = bpy.data.objects.get(f"{PREFIX}_Body")
if body is None:
    body = bpy.data.objects.new(f"{PREFIX}_Body", new_mesh)
    coll.objects.link(body)
else:
    old = body.data
    old_mats = list(old.materials)
    body.data = new_mesh
    for m in old_mats:
        new_mesh.materials.append(m)
    if old.users == 0:
        bpy.data.meshes.remove(old)
new_mesh.name = f"{PREFIX}_Body_Mesh"
for p in new_mesh.polygons:
    p.use_smooth = True
if not new_mesh.materials:
    mat = bpy.data.materials.get("M_Clay") or bpy.data.materials.new("M_Clay")
    if not mat.use_nodes:
        mat.use_nodes = True
        b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.82, 0.80, 0.78, 1)
        b.inputs["Roughness"].default_value = 0.55
    new_mesh.materials.append(mat)

# eyeballs: local -Y of the sphere is the gaze direction
for side in "RL":
    if f"eye.{side}" not in lm:
        continue
    name = f"{PREFIX}_Eye.{side}"
    eye = bpy.data.objects.get(name)
    if eye is None:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0)
        eye = bpy.context.active_object
        eye.name = name
        for c in eye.users_collection:
            c.objects.unlink(eye)
        coll.objects.link(eye)
        for p in eye.data.polygons:
            p.use_smooth = True
        em = bpy.data.materials.get("M_Eye") or bpy.data.materials.new("M_Eye")
        if not em.use_nodes:
            em.use_nodes = True
            bb = em.node_tree.nodes["Principled BSDF"]
            bb.inputs["Base Color"].default_value = (0.25, 0.45, 0.8, 1)
            bb.inputs["Roughness"].default_value = 0.05
        eye.data.materials.append(em)
    r = lm["eye_r"]
    # an earlier rig may have bone-parented the eye: clear it, else location is read in bone space (v17b: 12 px)
    eye.parent = None
    eye.matrix_parent_inverse.identity()
    eye.scale = (r, r, r)
    eye.location = Vector(lm[f"eye.{side}"])
    eye.rotation_euler = Vector(lm[f"eye_dir.{side}"]).to_track_quat('-Y', 'Z').to_euler()

# fur envelope (skin offset by fur depth): used by the probe for silhouette scoring only
import os
env_name = f"{PREFIX}_FurEnvelope"
env = bpy.data.objects.get(env_name)
if os.path.exists(MESH + "_env.ply"):
    before = set(bpy.data.objects)
    bpy.ops.wm.ply_import(filepath=MESH + "_env.ply")
    tmp = [o for o in bpy.data.objects if o not in before][0]
    em_ = tmp.data
    bpy.data.objects.remove(tmp, do_unlink=True)
    if env is None:
        env = bpy.data.objects.new(env_name, em_)
        coll.objects.link(env)
    else:
        old = env.data
        env.data = em_
        if old.users == 0:
            bpy.data.meshes.remove(old)
    # part-ID colours (flat per face) for the probe's attribution pass: code = owner+1 in a 16x16 grid
    own_path = MESH + "_env_owner.npy"
    if os.path.exists(own_path):
        import numpy as np
        me = env.data
        code = np.load(own_path).astype(np.int32) + 1
        lv = np.empty(len(me.loops), np.int32)
        me.loops.foreach_get("vertex_index", lv)
        ls = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get("loop_start", ls)
        fcode = code[lv[ls]]
        lcode = np.repeat(fcode, 3)
        rgba = np.ones((len(lcode), 4), np.float32)
        rgba[:, 0] = ((lcode % 16) * 16 + 8) / 255.0
        rgba[:, 1] = ((lcode // 16) * 16 + 8) / 255.0
        rgba[:, 2] = 0.0
        for ca in list(me.color_attributes):
            me.color_attributes.remove(ca)
        ca = me.color_attributes.new("part_id", 'FLOAT_COLOR', 'CORNER')
        ca.data.foreach_set("color", rgba.ravel())
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = 0
    env.display_type = 'WIRE'
    env.hide_set(True)
    env.hide_render = True
elif env is not None:
    bpy.data.objects.remove(env, do_unlink=True)

body["landmarks_file"] = MESH + "_landmarks.json"
print("loaded", ply, "verts", len(new_mesh.vertices), "faces", len(new_mesh.polygons))
