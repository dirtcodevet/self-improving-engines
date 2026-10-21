# Blender-side: add EEVEE-specific Material Outputs next to the Cycles ones (Principled Hair and a transmissive
# cornea render dark/opaque in EEVEE). Cycles keeps its physical shaders; EEVEE gets cheap look-alikes.
import bpy


def eevee_out(mat, build):
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.bl_idname == "ShaderNodeOutputMaterial":
            if n.target == 'EEVEE' or n.label == "EEVEE":
                nt.nodes.remove(n)
            else:
                n.target = 'CYCLES'
    o = nt.nodes.new("ShaderNodeOutputMaterial"); o.target = 'EEVEE'; o.label = "EEVEE"; o.location = (700, -400)
    sh = build(nt)
    nt.links.new(sh.outputs[0], o.inputs["Surface"])


def fur(nt):
    src = [n for n in nt.nodes if n.bl_idname == "ShaderNodeMix" and n.blend_type == 'MULTIPLY' and n.location.x < -150][0]
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.location = (300, -400)
    b.inputs["Roughness"].default_value = 0.55
    b.inputs["Sheen Weight"].default_value = 0.6
    b.inputs["Sheen Roughness"].default_value = 0.4
    gm = nt.nodes.new("ShaderNodeGamma"); gm.location = (100, -400); gm.inputs["Gamma"].default_value = 0.55  # undo darkening meant for multiple scattering
    nt.links.new(src.outputs[2], gm.inputs["Color"]); nt.links.new(gm.outputs[0], b.inputs["Base Color"])
    return b


def cornea(nt):
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); tr.location = (100, -350)
    gl = nt.nodes.new("ShaderNodeBsdfGlossy"); gl.location = (100, -500); gl.inputs["Roughness"].default_value = 0.02
    fr = nt.nodes.new("ShaderNodeFresnel"); fr.location = (-100, -300); fr.inputs["IOR"].default_value = 1.376
    mx = nt.nodes.new("ShaderNodeMixShader"); mx.location = (300, -400)
    nt.links.new(fr.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2])
    return mx


def whisker(nt):
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.location = (300, -400)
    b.inputs["Base Color"].default_value = (0.85, 0.84, 0.82, 1); b.inputs["Roughness"].default_value = 0.3
    return b


eevee_out(bpy.data.materials["M_Fur"], fur)
eevee_out(bpy.data.materials["M_Cornea"], cornea)
if "M_Whisker" in bpy.data.materials:
    eevee_out(bpy.data.materials["M_Whisker"], whisker)
cm = bpy.data.materials["M_Cornea"]
if hasattr(cm, "surface_render_method"):
    cm.surface_render_method = 'BLENDED'
print("eevee outputs added")
