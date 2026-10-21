# Blender-side quadruped rig from landmarks: <PREFIX>_Rig armature bound to <PREFIX>_Skin.
# Body weights: bone heat on a decimated proxy, transferred to the full skin (robust + fast at 220k verts).
# Face weights: procedural in head-local space (jaw below the mouth plane, lids on spheres around the eyes,
# ears along the ear axis, whisker pads, nose). Eyes/corneas parent to eye bones; fur deforms with the skin.
import bpy, json, math, time
import numpy as np
from mathutils import Vector, Matrix

t0 = time.time()
PREFIX = globals().get("PREFIX", "Cat")
skin = bpy.data.objects[f"{PREFIX}_Skin"]
coll = skin.users_collection[0]
J = json.load(open(skin["landmarks_file"]))
L, P = J["landmarks"], J["params"]
Rm = Matrix(L["head_R"])
H0 = Vector(L["head"])
hs = P["head_scale"]
W = lambda p: H0 + Rm @ (hs * Vector(p))
UP = Rm @ Vector((0, 0, 1))
FWD = Rm @ Vector((0, -1, 0))
V = Vector

# ---------------------------------------------------------------- clean previous rig
for o in list(bpy.data.objects):
    if o.name == f"{PREFIX}_Rig" or o.name == f"{PREFIX}_WeightProxy":
        d = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if d and d.users == 0:
            (bpy.data.armatures if isinstance(d, bpy.types.Armature) else bpy.data.meshes).remove(d)
for m in list(skin.modifiers):
    if m.type == 'ARMATURE':
        skin.modifiers.remove(m)
skin.vertex_groups.clear()
for o in bpy.context.view_layer.objects:
    o.select_set(False)
bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode != 'OBJECT' else None

arm = bpy.data.armatures.new(f"{PREFIX}_Rig")
rig = bpy.data.objects.new(f"{PREFIX}_Rig", arm)
coll.objects.link(rig)
arm.display_type = 'OCTAHEDRAL'
rig.show_in_front = True
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.edit_bones
FACE = set()


def bone(name, head, tail, parent=None, connect=False, deform=True, roll_up=None, face=False):
    b = eb.new(name)
    b.head, b.tail = V(head), V(tail)
    b.use_deform = deform
    if parent:
        b.parent = eb[parent]
        b.use_connect = connect
    b.align_roll(V(roll_up) if roll_up is not None else V((0, 0, 1)) if abs((b.tail - b.head).normalized().z) < 0.95 else V((0, -1, 0)))
    if face:
        FACE.add(name)
    return b


def resample(pts, n):
    pts = np.array(pts, float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    s = np.linspace(0, cum[-1], n + 1)
    return [tuple(np.array([np.interp(x, cum, pts[:, k]) for k in range(3)])) for x in s]


# ---------------------------------------------------------------- torso / neck / head
sp = [V(p) for p in L["spine"]]                 # rear (tail base) -> front (withers)
bone("root", (0, 0, 0), (0, 0.08, 0), deform=False)
bone("torso", sp[1] + V((0, 0, -0.03)), sp[1] + V((0, -0.05, -0.03)), "root", deform=False)
bone("pelvis", sp[1], sp[0], "torso")
bone("spine1", sp[1], sp[2], "torso")
bone("spine2", sp[2], sp[3], "spine1", True)
bone("spine3", sp[3], sp[4], "spine2", True)
occ = W((0, 0.022, -0.010))
nmid = (sp[4] + occ) / 2 + V((0, -0.005, 0.01))
bone("neck1", sp[4], nmid, "spine3", True)
bone("neck2", nmid, occ, "neck1", True)
bone("head", occ, W((0, -0.032, 0.004)), "neck2", True, roll_up=UP)
# ---------------------------------------------------------------- tail
tp = resample(L["tail"], 8)
prev = "pelvis"
for i in range(8):
    bone(f"tail{i+1}", tp[i], tp[i + 1], prev, connect=i > 0)
    prev = f"tail{i+1}"
# ---------------------------------------------------------------- legs
for side, s in (("R", -1), ("L", 1)):
    sh, el, wr, fp = (V(L[f"{k}.{side}"]) for k in ("shoulder", "elbow", "wrist", "fpaw"))
    bone(f"scapula.{side}", V((s * 0.018, -0.055, 0.218)), sh, "spine3")
    bone(f"upperarm.{side}", sh, el, f"scapula.{side}", True)
    bone(f"forearm.{side}", el, wr, f"upperarm.{side}", True)
    bone(f"hand.{side}", wr, fp, f"forearm.{side}", True)
    bone(f"fingers.{side}", fp, fp + V((0, -0.016, -0.004)), f"hand.{side}", True)
    bone(f"hand_ik.{side}", wr, wr + V((0, -0.02, 0)), "root", deform=False)
    bone(f"elbow_pole.{side}", el + V((0, 0.10, 0)), el + V((0, 0.11, 0)), "root", deform=False)
    hp, kn, hk, hpw = (V(L[f"{k}.{side}"]) for k in ("hip", "knee", "hock", "hpaw"))
    bone(f"thigh.{side}", hp, kn, "pelvis")
    bone(f"shin.{side}", kn, hk, f"thigh.{side}", True)
    bone(f"foot.{side}", hk, hpw, f"shin.{side}", True)
    bone(f"toes.{side}", hpw, hpw + V((0, -0.015, -0.004)), f"foot.{side}", True)
    bone(f"foot_ik.{side}", hk, hk + V((0, 0.02, 0)), "root", deform=False)
    bone(f"knee_pole.{side}", kn + V((0, -0.12, 0)), kn + V((0, -0.13, 0)), "root", deform=False)
# ---------------------------------------------------------------- face
bone("jaw", V(L["jaw_hinge"]), W((0, -0.031, -0.037)), "head", roll_up=UP, face=True)
bone("nose", W((0, -0.032, -0.012)), V(L["nose"]), "head", roll_up=UP, face=True)
er = L["eye_r"]
for side, s in (("R", -1), ("L", 1)):
    c, g = V(L[f"eye.{side}"]), V(L[f"eye_dir.{side}"]).normalized()
    bone(f"eye.{side}", c, c + g * 0.014, "head", deform=False, roll_up=UP)
    bone(f"lid_up.{side}", c, c + g * 0.012 + UP * 0.003, "head", roll_up=UP, face=True)
    bone(f"lid_lo.{side}", c, c + g * 0.012 - UP * 0.003, "head", roll_up=UP, face=True)
    eb_, et_ = V(L[f"ear_base.{side}"]), V(L[f"ear_tip.{side}"])
    mid = eb_ + (et_ - eb_) * 0.5
    bone(f"ear.{side}", eb_, mid, "head", roll_up=FWD, face=True)
    bone(f"ear_tip.{side}", mid, et_, f"ear.{side}", True, roll_up=FWD, face=True)
    wp = V(L[f"whiskerpad.{side}"])
    bone(f"whisker.{side}", wp, wp + FWD * 0.008 + Rm @ V((s * 0.004, 0, 0)), "head", roll_up=UP, face=True)
tg = [V(p) for p in L["tongue"]]
bone("tongue1", tg[0], tg[1], "jaw", roll_up=UP, face=True)
bone("tongue2", tg[1], tg[2], "tongue1", True, roll_up=UP, face=True)
bone("tongue3", tg[2], tg[2] + FWD * 0.008, "tongue2", True, roll_up=UP, face=True)


# ---------------------------------------------------------------- IK with rest-preserving pole angles
def pole_angle(base, ik_bone, pole):
    pn = (ik_bone.tail - base.head).cross(pole - base.head)
    proj = pn.cross(base.tail - base.head)
    a = base.x_axis.angle(proj)
    if base.x_axis.cross(proj).angle(base.tail - base.head) < 1:
        a = -a
    return a


poles = {}
for side in "RL":
    poles[f"forearm.{side}"] = (f"hand_ik.{side}", f"elbow_pole.{side}", pole_angle(eb[f"upperarm.{side}"], eb[f"forearm.{side}"], eb[f"elbow_pole.{side}"].head))
    poles[f"shin.{side}"] = (f"foot_ik.{side}", f"knee_pole.{side}", pole_angle(eb[f"thigh.{side}"], eb[f"shin.{side}"], eb[f"knee_pole.{side}"].head))
for side in "RL":  # hands/feet follow their IK controls once the chain is solved
    eb[f"hand.{side}"].use_inherit_rotation = True
bpy.ops.object.mode_set(mode='POSE')
pb = rig.pose.bones
for b, (tgt, pole, ang) in poles.items():
    c = pb[b].constraints.new('IK')
    c.target, c.subtarget, c.pole_target, c.pole_subtarget = rig, tgt, rig, pole
    c.pole_angle, c.chain_count = ang, 2
for side in "RL":
    pb[f"ear.{side}"].rotation_mode = pb[f"ear_tip.{side}"].rotation_mode = 'XYZ'
for p_ in pb:
    p_.rotation_mode = 'XYZ'
bpy.ops.object.mode_set(mode='OBJECT')
print("armature:", len(arm.bones), "bones", f"{time.time()-t0:.1f}s")

# ---------------------------------------------------------------- body weights: bone heat on a proxy
# re-runnable: a previous build's lips_seal shape key blocks every modifier_apply (v27b "from look" rebuild died
# here). lip_seal.py runs after the rig and re-creates it.
if skin.data.shape_keys:
    skin.shape_key_clear()
proxy = skin.copy()
proxy.data = skin.data.copy()
proxy.name = f"{PREFIX}_WeightProxy"
coll.objects.link(proxy)
proxy.modifiers.clear()
dm = proxy.modifiers.new("dec", 'DECIMATE')
dm.ratio = 26000 / len(proxy.data.polygons)
with bpy.context.temp_override(object=proxy, active_object=proxy, selected_objects=[proxy]):
    bpy.ops.object.modifier_apply(modifier=dm.name)
for b in arm.bones:
    if b.name in FACE:
        b.use_deform = False
for o in bpy.context.view_layer.objects:
    o.select_set(False)
proxy.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
for b in arm.bones:
    if b.name in FACE:
        b.use_deform = True
print("bone heat on proxy:", len(proxy.vertex_groups), "groups", f"{time.time()-t0:.1f}s")
# transfer to the full skin
dt = skin.modifiers.new("wt", 'DATA_TRANSFER')
dt.object = proxy
dt.use_vert_data = True
dt.data_types_verts = {'VGROUP_WEIGHTS'}
dt.vert_mapping = 'POLYINTERP_NEAREST'
dt.layers_vgroup_select_src = 'ALL'
dt.layers_vgroup_select_dst = 'NAME'
with bpy.context.temp_override(object=skin, active_object=skin, selected_objects=[skin]):
    bpy.ops.object.datalayout_transfer(modifier=dt.name)
    bpy.ops.object.modifier_apply(modifier=dt.name)
bpy.data.objects.remove(proxy, do_unlink=True)

# ---------------------------------------------------------------- read weights into a matrix
me = skin.data
n = len(me.vertices)
gnames = [g.name for g in skin.vertex_groups]
Wt = np.zeros((n, len(gnames)), np.float32)
for v in me.vertices:
    for ge in v.groups:
        Wt[v.index, ge.group] = ge.weight
co = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3).astype(np.float64)
R_ = np.array(L["head_R"])
hl = ((co - np.array(L["head"])) @ R_) / hs
x, y, z = hl.T


def ss(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


face_w = {}
import importlib, mouth_geom as MG; importlib.reload(MG)     # the ONE mouth definition (= slit_cavity)
zm, e_m, _h = MG.zm_e_h(x, y, MG.from_landmarks(L, hs))
head_zone = np.linalg.norm(hl - np.array([0, -0.005, 0.0]), axis=1) < 0.075
# jaw weights: mouth_geom.jaw_weight (sharp along the lips, soft vertical falloff behind the corners)
face_w["jaw"] = MG.jaw_weight(hl, MG.from_landmarks(L, hs))     # shared with part_lab's open-jaw preview
for side, s in (("R", -1), ("L", 1)):
    c = np.array(L[f"eye.{side}"]); gz = np.array(L[f"eye_dir.{side}"]); up = np.array(UP)
    rel = co - c
    d = np.linalg.norm(rel, axis=1)
    fwd = rel @ gz
    v = rel @ up
    # lids = only the band of skin lying on the eyeball from the lid margin ~35 deg up (or down) the globe.
    # (v1 took everything within 5 mm of the eyeball sphere -> the whole brow rotated on a blink)
    theta = np.degrees(np.arccos(np.clip(fwd / np.maximum(d, 1e-9), -1, 1)))     # angle from the gaze axis
    th_edge = np.degrees(np.arcsin(min(0.0072 * hs / er, 0.99)))                   # aperture half-height angle
    band = ss(th_edge - 6, th_edge + 2, theta) * ss(th_edge + 50, th_edge + 30, theta)
    shell = ss(er + 0.0042, er + 0.0018, d) * band
    face_w[f"lid_up.{side}"] = shell * ss(0.0005, 0.0030, v)
    face_w[f"lid_lo.{side}"] = shell * ss(-0.0005, -0.0030, v)
    eb_, et_ = np.array(L[f"ear_base.{side}"]), np.array(L[f"ear_tip.{side}"])
    ax = (et_ - eb_) / np.linalg.norm(et_ - eb_)
    r2 = co - eb_
    t = r2 @ ax / np.linalg.norm(et_ - eb_)
    rad = np.linalg.norm(r2 - np.outer(r2 @ ax, ax), axis=1)
    inear = ss(0.030 * (1.05 - 0.8 * np.clip(t, 0, 1)) + 0.006, 0.022 * (1.05 - 0.8 * np.clip(t, 0, 1)), rad)
    face_w[f"ear.{side}"] = inear * ss(0.02, 0.28, t) * (1 - ss(0.45, 0.70, t))
    face_w[f"ear_tip.{side}"] = inear * ss(0.45, 0.70, t)
    wp = np.array(L[f"whiskerpad.{side}"])
    face_w[f"whisker.{side}"] = 0.85 * np.exp(-0.5 * (np.linalg.norm(co - wp, axis=1) / 0.0055) ** 2) * (1 - face_w["jaw"])
face_w["nose"] = 0.9 * np.exp(-0.5 * (np.linalg.norm(co - np.array(L["nose"]), axis=1) / 0.0045) ** 2)
F = np.stack(list(face_w.values()), 1)
tot = F.sum(1)
over = tot > 1
F[over] /= tot[over, None]
tot = np.minimum(tot, 1)
# face bones take their share out of the existing (bone-heat) weights, mostly 'head'
Wt *= (1 - tot)[:, None]
for name, col in zip(face_w.keys(), F.T):
    if name not in gnames:
        skin.vertex_groups.new(name=name)
        gnames.append(name)
        Wt = np.concatenate([Wt, np.zeros((n, 1), np.float32)], 1)
    Wt[:, gnames.index(name)] = col
# normalise + write back (bucketed for speed)
s_ = Wt.sum(1, keepdims=True)
Wt = np.where(s_ > 1e-6, Wt / np.maximum(s_, 1e-6), Wt)
for gi, gname in enumerate(gnames):
    vg = skin.vertex_groups[gname]
    w = Wt[:, gi]
    vg.remove(list(range(n)))
    q = np.round(w * 100).astype(int)
    for lvl in np.unique(q[q > 0]):
        vg.add(np.nonzero(q == lvl)[0].tolist(), float(lvl) / 100, 'REPLACE')
print("face weights:", {k: int((v > 0.5).sum()) for k, v in face_w.items()}, f"{time.time()-t0:.1f}s")

# ---------------------------------------------------------------- bind skin, eyes, fur
skin.parent = rig
skin.matrix_parent_inverse = rig.matrix_world.inverted()
am = skin.modifiers.new("rig", 'ARMATURE')
am.object = rig
am.use_deform_preserve_volume = True
while skin.modifiers.find("rig") > 0:
    bpy.ops.object.modifier_move_up({"object": skin}, modifier="rig") if False else skin.modifiers.move(skin.modifiers.find("rig"), 0)
# eyes: rebuild the rest matrix from landmarks (never trust a possibly mis-parented current transform) and
# parent with an explicit bone-tail inverse. v1 set matrix_world before the new armature's pose was evaluated
# -> eyes collapsed to the origin.
bpy.context.view_layer.update()
for side in "RL":
    eye = bpy.data.objects.get(f"{PREFIX}_Eye.{side}")
    if eye:
        r_ = L["eye_r"]
        mw = Matrix.LocRotScale(V(L[f"eye.{side}"]), V(L[f"eye_dir.{side}"]).to_track_quat('-Y', 'Z'), V((r_, r_, r_)))
        pbe = rig.pose.bones[f"eye.{side}"]
        pmat = rig.matrix_world @ pbe.matrix @ Matrix.Translation((0, pbe.bone.length, 0))
        eye.parent, eye.parent_type, eye.parent_bone = rig, 'BONE', f"eye.{side}"
        eye.matrix_parent_inverse = pmat.inverted()
        eye.matrix_basis = mw
skin.add_rest_position_attribute = True
fur = bpy.data.objects.get(f"{PREFIX}_Fur")
if fur:
    ng = bpy.data.node_groups.get("FurSurfaceDeform")
    if ng:
        bpy.data.node_groups.remove(ng)
    ng = bpy.data.node_groups.new("FurSurfaceDeform", 'GeometryNodeTree')
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    gi, go = ng.nodes.new("NodeGroupInput"), ng.nodes.new("NodeGroupOutput")
    dn = ng.nodes.new("GeometryNodeDeformCurvesOnSurface")
    ng.links.new(gi.outputs[0], dn.inputs[0]); ng.links.new(dn.outputs[0], go.inputs[0])
    for m in list(fur.modifiers):
        if m.name == "surface_deform":
            fur.modifiers.remove(m)
    md = fur.modifiers.new("surface_deform", 'NODES')
    md.node_group = ng
    fur.modifiers.move(fur.modifiers.find("surface_deform"), 0)
    fur.parent = rig
    fur.matrix_parent_inverse = rig.matrix_world.inverted()
bpy.context.view_layer.objects.active = rig
print(f"rig ready {time.time()-t0:.1f}s")
