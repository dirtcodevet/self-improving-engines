"""BLENDER-SIDE: export a skinned mesh's evaluated (posed) vertex positions and the armature's deform matrices for
one pose, so posed-space measurements and fixes can be computed in numpy and turned back into rest-space corrective
offsets (engine/tools/posed_correctives.py). Created 2026-10-19 (woman2 v5, armpit cup).

Run through bmcp with these globals set before the file: MESH (object name), RIG (armature object name),
ROT (dict bone name -> (x, y, z) Euler radians; bones not listed are set to zero rotation), OUT (npz path).
Writes: v (posed, world), n (posed normals), M (bones x 4 x 4 deform matrices: pose.matrix @ bone.matrix_local^-1,
world = armature object matrix assumed identity, asserted), bones (names). Restores the rig to its rest rotations in a
finally block (the engine rule: a probe restores every state it touches).
"""
import bpy
import numpy as np
from mathutils import Matrix

ob, rig = bpy.data.objects[MESH], bpy.data.objects[RIG]
assert rig.matrix_world == Matrix.Identity(4) and ob.matrix_world == Matrix.Identity(4), "world matrices must be identity"
saved = {b.name: tuple(b.rotation_euler) for b in rig.pose.bones}
try:
    for b in rig.pose.bones:
        b.rotation_euler = ROT.get(b.name, (0.0, 0.0, 0.0))
    vl = bpy.context.view_layer
    vl.update(); vl.update()                          # the girdle drivers, then the skin
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    n = len(me.vertices)
    v = np.empty(n * 3, np.float64); me.vertices.foreach_get("co", v)
    nn = np.empty(n * 3, np.float64); me.vertices.foreach_get("normal", nn)
    ob.evaluated_get(dg).to_mesh_clear()
    names = [b.name for b in rig.pose.bones]
    M = np.array([np.array(rig.pose.bones[k].matrix @ rig.data.bones[k].matrix_local.inverted()) for k in names])
    np.savez(OUT, v=v.reshape(-1, 3), n=nn.reshape(-1, 3), M=M, bones=np.array(names))
    print("exported", n, "verts ->", OUT)
finally:
    for b in rig.pose.bones:
        b.rotation_euler = saved[b.name]
    bpy.context.view_layer.update(); bpy.context.view_layer.update()
