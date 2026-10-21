# Blender-side generic shaders for a furred creature. Reads attributes written by the case coat script:
#   coat (colour), rough. Eye colours come from globals IRIS_IN / IRIS_OUT (linear RGB) if given.
# Creates/updates: M_Skin, M_Eye, M_Cornea, M_Teeth, M_Tongue, M_Claw, M_Fur. Assigns skin + eyes + corneas.
import bpy, math
from mathutils import Vector

PREFIX = globals().get("PREFIX", "Cat")
IRIS_IN = globals().get("IRIS_IN", (0.10, 0.28, 0.75))
IRIS_OUT = globals().get("IRIS_OUT", (0.30, 0.55, 0.92))
# v33: iris extent and pupil shape are case parameters measured on the photo (trace_photo/compare_features):
# iris radius as a fraction of the eyeball radius; pupil half-width / half-height (object units, a vertical oval)
IRIS_R = globals().get("IRIS_R", 0.93)
PUPIL_W, PUPIL_H = globals().get("PUPIL_W", 0.288), globals().get("PUPIL_H", 0.36)


def fresh(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_fake_user = True  # checkpoint's orphan purge deleted not-yet-assigned materials (teeth/tongue/claw)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    return m, nt


def node(nt, typ, loc, **inputs):
    nd = nt.nodes.new(typ)
    nd.location = loc
    for k, v in inputs.items():
        nd.inputs[k].default_value = v
    return nd


def out(nt, shader, loc=(600, 0)):
    o = node(nt, "ShaderNodeOutputMaterial", loc)
    nt.links.new(shader.outputs[0], o.inputs["Surface"])
    return o


# ---------------- skin (under the fur; visible on nose, lids, lips, pads, ear insides, mouth)
m, nt = fresh("M_Skin")
attr = node(nt, "ShaderNodeAttribute", (-600, 100)); attr.attribute_name = "coat"; attr.attribute_type = 'GEOMETRY'
ra = node(nt, "ShaderNodeAttribute", (-600, -150)); ra.attribute_name = "rough"; ra.attribute_type = 'GEOMETRY'
bs = node(nt, "ShaderNodeBsdfPrincipled", (0, 0))
bs.inputs["Subsurface Weight"].default_value = 0.25
bs.inputs["Subsurface Radius"].default_value = (0.004, 0.0015, 0.001)
bs.inputs["Subsurface Scale"].default_value = 1.0
nt.links.new(attr.outputs["Color"], bs.inputs["Base Color"])
nt.links.new(ra.outputs["Fac"], bs.inputs["Roughness"])
# v28: oral cavity glow = coat x 'oral' attribute (coat.py) x ORAL_GLOW - stand-in for the bounce/SSS light inside a
# real mouth (the meow interior rendered near-black: interior luminance 0.14; 0.9 -> ~0.35 with the calibrated look)
oa = node(nt, "ShaderNodeAttribute", (-600, 300)); oa.attribute_name = "oral"; oa.attribute_type = 'GEOMETRY'
omx = node(nt, "ShaderNodeMixRGB", (-300, 300)); omx.blend_type = 'MULTIPLY'; omx.inputs[0].default_value = 1.0
nt.links.new(attr.outputs["Color"], omx.inputs[1]); nt.links.new(oa.outputs["Fac"], omx.inputs[2])
nt.links.new(omx.outputs[0], bs.inputs["Emission Color"])
bs.inputs["Emission Strength"].default_value = globals().get("ORAL_GLOW", 0.9)
nz = node(nt, "ShaderNodeTexNoise", (-600, -400), Scale=900.0, Detail=4.0)
bump = node(nt, "ShaderNodeBump", (-250, -400), Strength=0.15, Distance=0.0002)
nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
out(nt, bs)

# ---------------- eye: iris / pupil / sclera from object coords (gaze = local -Y)
m, nt = fresh("M_Eye")
tc = node(nt, "ShaderNodeTexCoord", (-1400, 0))
sep = node(nt, "ShaderNodeSeparateXYZ", (-1200, 0))
nt.links.new(tc.outputs["Object"], sep.inputs[0])
# radial distance from the gaze axis in the x-z plane; pupil is a slightly vertical oval
mx = node(nt, "ShaderNodeMath", (-1000, 120)); mx.operation = 'MULTIPLY'; mx.inputs[1].default_value = PUPIL_H / PUPIL_W
nt.links.new(sep.outputs["X"], mx.inputs[0])
cmb = node(nt, "ShaderNodeCombineXYZ", (-850, 60))
nt.links.new(mx.outputs[0], cmb.inputs["X"]); nt.links.new(sep.outputs["Z"], cmb.inputs["Y"])
rp = node(nt, "ShaderNodeVectorMath", (-700, 60)); rp.operation = 'LENGTH'
nt.links.new(cmb.outputs[0], rp.inputs[0])
cmb2 = node(nt, "ShaderNodeCombineXYZ", (-850, -120))
nt.links.new(sep.outputs["X"], cmb2.inputs["X"]); nt.links.new(sep.outputs["Z"], cmb2.inputs["Y"])
r = node(nt, "ShaderNodeVectorMath", (-700, -120)); r.operation = 'LENGTH'
nt.links.new(cmb2.outputs[0], r.inputs[0])
front = node(nt, "ShaderNodeMath", (-700, -300)); front.operation = 'LESS_THAN'; front.inputs[1].default_value = 0.0
nt.links.new(sep.outputs["Y"], front.inputs[0])
# iris fibres: radial noise
ang = node(nt, "ShaderNodeMath", (-850, -480)); ang.operation = 'ARCTAN2'
nt.links.new(sep.outputs["Z"], ang.inputs[0]); nt.links.new(sep.outputs["X"], ang.inputs[1])
fib_v = node(nt, "ShaderNodeCombineXYZ", (-700, -480))
nt.links.new(ang.outputs[0], fib_v.inputs["X"]); nt.links.new(r.outputs[1], fib_v.inputs["Y"])
fib = node(nt, "ShaderNodeTexNoise", (-520, -480), Scale=14.0, Detail=6.0, Roughness=0.7)
nt.links.new(fib_v.outputs[0], fib.inputs["Vector"])
iris_ramp = node(nt, "ShaderNodeValToRGB", (-300, -200))
cr = iris_ramp.color_ramp
_s = IRIS_R / 0.93
cr.elements[0].position, cr.elements[0].color = 0.30 * _s, (*IRIS_IN, 1)
cr.elements[1].position, cr.elements[1].color = 0.80 * _s, (*IRIS_OUT, 1)
e3 = cr.elements.new(0.90 * _s); e3.color = (IRIS_IN[0] * 0.35, IRIS_IN[1] * 0.35, IRIS_IN[2] * 0.45, 1)  # limbal ring
nt.links.new(r.outputs[1], iris_ramp.inputs["Fac"])
fibmix = node(nt, "ShaderNodeMix", (-80, -250)); fibmix.data_type = 'RGBA'; fibmix.blend_type = 'OVERLAY'
fibmix.inputs["Factor"].default_value = 0.55
nt.links.new(iris_ramp.outputs["Color"], fibmix.inputs[6]); nt.links.new(fib.outputs["Color"], fibmix.inputs[7])
# pupil + sclera masks
pup = node(nt, "ShaderNodeMath", (-450, 150)); pup.operation = 'LESS_THAN'; pup.inputs[1].default_value = PUPIL_H
nt.links.new(rp.outputs[1], pup.inputs[0])
irs = node(nt, "ShaderNodeMath", (-450, 0)); irs.operation = 'LESS_THAN'; irs.inputs[1].default_value = IRIS_R
nt.links.new(r.outputs[1], irs.inputs[0])
irs2 = node(nt, "ShaderNodeMath", (-300, 0)); irs2.operation = 'MULTIPLY'
nt.links.new(irs.outputs[0], irs2.inputs[0]); nt.links.new(front.outputs[0], irs2.inputs[1])
c_scl = node(nt, "ShaderNodeMix", (100, 0)); c_scl.data_type = 'RGBA'
c_scl.inputs[6].default_value = (0.75, 0.72, 0.70, 1)
nt.links.new(irs2.outputs[0], c_scl.inputs["Factor"]); nt.links.new(fibmix.outputs[2], c_scl.inputs[7])
pup2 = node(nt, "ShaderNodeMath", (-300, 150)); pup2.operation = 'MULTIPLY'
nt.links.new(pup.outputs[0], pup2.inputs[0]); nt.links.new(front.outputs[0], pup2.inputs[1])
c_pup = node(nt, "ShaderNodeMix", (280, 0)); c_pup.data_type = 'RGBA'
c_pup.inputs[7].default_value = (0.004, 0.004, 0.006, 1)
nt.links.new(pup2.outputs[0], c_pup.inputs["Factor"]); nt.links.new(c_scl.outputs[2], c_pup.inputs[6])
bs = node(nt, "ShaderNodeBsdfPrincipled", (450, 0), Roughness=0.35)
nt.links.new(c_pup.outputs[2], bs.inputs["Base Color"])
out(nt, bs, (700, 0))

# ---------------- cornea: clear dome over the eye (catchlights + refraction depth)
m, nt = fresh("M_Cornea")
bs = node(nt, "ShaderNodeBsdfPrincipled", (0, 0), Roughness=0.0, IOR=1.376)
bs.inputs["Transmission Weight"].default_value = 1.0
bs.inputs["Base Color"].default_value = (1, 1, 1, 1)
out(nt, bs)
m.surface_render_method = 'BLENDED' if hasattr(m, "surface_render_method") else None

# ---------------- teeth / tongue / claws
m, nt = fresh("M_Teeth")
bs = node(nt, "ShaderNodeBsdfPrincipled", (0, 0), Roughness=0.25)
bs.inputs["Base Color"].default_value = (0.86, 0.83, 0.74, 1)
bs.inputs["Subsurface Weight"].default_value = 0.2
out(nt, bs)
m, nt = fresh("M_Tongue")
bs = node(nt, "ShaderNodeBsdfPrincipled", (0, 0), Roughness=0.45)
bs.inputs["Base Color"].default_value = (0.80, 0.33, 0.38, 1)   # v28: cat-tongue pink (linear); was 0.70/0.22/0.28
bs.inputs["Emission Color"].default_value = (0.80, 0.33, 0.38, 1)  # v28: same stand-in as the oral glow (M_Skin)
bs.inputs["Emission Strength"].default_value = 0.35
bs.inputs["Subsurface Weight"].default_value = 0.3
bs.inputs["Subsurface Radius"].default_value = (0.003, 0.001, 0.001)
nz = node(nt, "ShaderNodeTexNoise", (-500, -200), Scale=2500.0, Detail=2.0)
bump = node(nt, "ShaderNodeBump", (-250, -200), Strength=0.4, Distance=0.0003)
nt.links.new(nz.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
out(nt, bs)
m, nt = fresh("M_Claw")
bs = node(nt, "ShaderNodeBsdfPrincipled", (0, 0), Roughness=0.3)
bs.inputs["Base Color"].default_value = (0.80, 0.76, 0.68, 1)
bs.inputs["Transmission Weight"].default_value = 0.25
out(nt, bs)

# ---------------- fur: Principled Hair (Chiang), direct colouring from the strand's 'coat' attribute
m, nt = fresh("M_Fur")
attr = node(nt, "ShaderNodeAttribute", (-500, 0)); attr.attribute_name = "coat"; attr.attribute_type = 'GEOMETRY'
hi = node(nt, "ShaderNodeHairInfo", (-500, -250))
jit = node(nt, "ShaderNodeMix", (-250, 0)); jit.data_type = 'RGBA'; jit.blend_type = 'MULTIPLY'
jit.inputs["Factor"].default_value = 0.12
rnd = node(nt, "ShaderNodeValToRGB", (-400, -400))
rnd.color_ramp.elements[0].color = (0.85, 0.85, 0.88, 1); rnd.color_ramp.elements[1].color = (1, 1, 1, 1)
nt.links.new(hi.outputs["Random"], rnd.inputs["Fac"])
# multiple scattering through layers of hair washes colour out: gamma>1 keeps white white, saturates tints
gm = node(nt, "ShaderNodeGamma", (-350, 150)); gm.inputs["Gamma"].default_value = 1.8
nt.links.new(attr.outputs["Color"], gm.inputs["Color"])
# whiteness (absorption) is set separately from tint saturation: a calibrated FUR_GAMMA used directly as a
# gamma turned lavender into neon purple. Equivalent white albedo: 0.89^(FUR_GAMMA-1.8) as a flat multiply.
kw = 0.89 ** max(globals().get("FUR_GAMMA", 1.8) - 1.8, 0.0)
wm = node(nt, "ShaderNodeMix", (-200, 150)); wm.data_type = 'RGBA'; wm.blend_type = 'MULTIPLY'
wm.inputs["Factor"].default_value = 1.0; wm.inputs[7].default_value = (kw, kw, kw, 1)
nt.links.new(gm.outputs["Color"], wm.inputs[6])
nt.links.new(wm.outputs[2], jit.inputs[6]); nt.links.new(rnd.outputs["Color"], jit.inputs[7])
hb = nt.nodes.new("ShaderNodeBsdfHairPrincipled"); hb.location = (0, 0)
hb.parametrization = 'COLOR'
hb.inputs["Roughness"].default_value = 0.32
hb.inputs["Radial Roughness"].default_value = 0.35
hb.inputs["Coat"].default_value = 0.05
hb.inputs["Random Roughness"].default_value = 0.15
nt.links.new(jit.outputs[2], hb.inputs["Color"])
out(nt, hb)

# ---------------- assign
skin = bpy.data.objects.get(f"{PREFIX}_Skin")
if skin:
    skin.data.materials.clear(); skin.data.materials.append(bpy.data.materials["M_Skin"])
coll = skin.users_collection[0] if skin else bpy.context.scene.collection
for side in "RL":
    eye = bpy.data.objects.get(f"{PREFIX}_Eye.{side}")
    if not eye:
        continue
    eye.data.materials.clear(); eye.data.materials.append(bpy.data.materials["M_Eye"])
    cn = bpy.data.objects.get(f"{PREFIX}_Cornea.{side}")
    if cn is None:
        me = bpy.data.meshes.new(f"{PREFIX}_Cornea.{side}")
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=1.0)
        for v in bm.verts:  # bulge the front cap (local -Y) into a corneal dome
            if v.co.y < -0.55:
                v.co.y -= 0.10 * ((-v.co.y - 0.55) / 0.45) ** 1.5
        bm.to_mesh(me); bm.free()
        for p in me.polygons:
            p.use_smooth = True
        cn = bpy.data.objects.new(f"{PREFIX}_Cornea.{side}", me)
        coll.objects.link(cn)
        cn.parent = eye
    cn.scale = (1.03, 1.03, 1.03)
    cn.location = (0, 0, 0)
    cn.data.materials.clear(); cn.data.materials.append(bpy.data.materials["M_Cornea"])
print("materials ready:", [m.name for m in bpy.data.materials if m.name.startswith("M_")])
