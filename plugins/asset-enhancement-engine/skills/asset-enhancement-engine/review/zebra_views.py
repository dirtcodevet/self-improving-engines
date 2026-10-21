# Blender-side: ZEBRA (reflection-line) review renders of the clay skin at REST pose. Stripes = the reflection
# vector's height through a black/white band pattern: they run smooth where the surface is fair, and kink (G1) or
# bunch/bend abruptly (G2: curvature jump) at bad seams - the "lines" a person sees at the neck, legs, tail.
# Globals: OUT (png), VIEWS_PY, optional CENTER/SIZE/VIEWS (passed to views.py), FREQ (stripes, default 16), PREFIX.
import bpy, math
PREFIX = globals().get("PREFIX", "Cat")
sc = bpy.context.scene
vl = bpy.context.view_layer
rig = bpy.data.objects.get(f"{PREFIX}_Rig")
mat = bpy.data.materials.get("_Zebra") or bpy.data.materials.new("_Zebra")
mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
tc = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = globals().get("FREQ", 16) * 2 * math.pi
sn = nt.nodes.new("ShaderNodeMath"); sn.operation = 'SINE'
gt = nt.nodes.new("ShaderNodeMath"); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.0
em = nt.nodes.new("ShaderNodeEmission")
out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(tc.outputs["Reflection"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], mul.inputs[0])
nt.links.new(mul.outputs[0], sn.inputs[0]); nt.links.new(sn.outputs[0], gt.inputs[0])
nt.links.new(gt.outputs[0], em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs["Surface"])
_z_saved = (vl.material_override, rig.data.pose_position if rig else None)
_z_vis = {o.name: o.hide_render for o in bpy.data.objects}
try:
    vl.material_override = mat
    if rig:
        rig.data.pose_position = 'REST'
    for o in bpy.data.objects:
        if o.type == 'CURVES' or "Whisk" in o.name or o.name in (f"{PREFIX}_Body", f"{PREFIX}_SkinRef", f"{PREFIX}_FurEnvelope") \
                or o.name.startswith(f"{PREFIX}_Acc_"):
            o.hide_render = True
    ENGINE = 'BLENDER_EEVEE'
    exec(open(VIEWS_PY).read())
finally:
    vl.material_override = _z_saved[0]
    if rig:
        rig.data.pose_position = _z_saved[1]
    for n, h in _z_vis.items():
        if n in bpy.data.objects:
            bpy.data.objects[n].hide_render = h
print("zebra", OUT)
