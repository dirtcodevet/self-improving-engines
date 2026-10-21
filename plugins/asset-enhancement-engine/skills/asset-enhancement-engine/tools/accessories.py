# Blender-side accessories for a felid built by this engine: teeth, tongue (skinned to tongue bones),
# retractable claws, whiskers (muzzle / brow / cheek). Everything is generated from landmarks, rooted on the
# rest-pose skin and parented to the right bones of <PREFIX>_Rig. Rebuilds from scratch every run.
import bpy, bmesh, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

PREFIX = globals().get("PREFIX", "Cat")
rig = bpy.data.objects[f"{PREFIX}_Rig"]
skin = bpy.data.objects[f"{PREFIX}_Skin"]
coll = skin.users_collection[0]
J = json.load(open(skin["landmarks_file"]))
L, P = J["landmarks"], J["params"]
Rm = Matrix(L["head_R"]); H0 = Vector(L["head"]); hs = P["head_scale"]
W = lambda p: H0 + Rm @ (hs * Vector(p))
UP, FWD, RIGHT = Rm @ Vector((0, 0, 1)), Rm @ Vector((0, -1, 0)), Rm @ Vector((1, 0, 0))
for pb in rig.pose.bones:  # build at rest
    pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
bpy.context.view_layer.update()
skin_rest = BVHTree.FromPolygons([v.co.copy() for v in skin.data.vertices], [p.vertices[:] for p in skin.data.polygons])

for o in list(bpy.data.objects):
    if o.name.startswith(f"{PREFIX}_Acc_"):
        d = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if d is not None and d.users == 0:
            (bpy.data.hair_curves if isinstance(d, bpy.types.Curves) else bpy.data.meshes).remove(d)


def parent_bone(obj, bname):
    pb = rig.pose.bones[bname]
    pmat = rig.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))
    mw = obj.matrix_world.copy()
    obj.parent, obj.parent_type, obj.parent_bone = rig, 'BONE', bname
    obj.matrix_parent_inverse = pmat.inverted()
    obj.matrix_basis = mw


def mesh_obj(name, bm, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(bpy.data.materials[mat])
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def tusk(bm, base, axis, back, length, r0, curve=0.25, segs=10, ring=10):
    """Curved cone (tooth/claw): from base along axis, bending toward `back` by `curve` (fraction of length)."""
    axis, back = axis.normalized(), back.normalized()
    side = axis.cross(back).normalized()
    back = side.cross(axis).normalized()
    rings = []
    for i in range(segs + 1):
        t = i / segs
        c = base + axis * (length * t) + back * (curve * length * t * t)
        tang = (axis + back * (2 * curve * t)).normalized()
        s2 = tang.cross(back).normalized(); b2 = s2.cross(tang).normalized()
        r = r0 * (1 - t) ** 0.85 + 0.00005
        rings.append([bm.verts.new(c + (s2 * math.cos(a) + b2 * math.sin(a) * 0.8) * r)
                      for a in np.linspace(0, 2 * math.pi, ring, endpoint=False)])
    for i in range(segs):
        for j in range(ring):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % ring], rings[i + 1][(j + 1) % ring], rings[i + 1][j]))
    bm.faces.new(list(reversed(rings[0])))
    tip = bm.verts.new(rings[-1][0].co * 0 + sum((v.co for v in rings[-1]), Vector()) / ring)
    for j in range(ring):
        bm.faces.new((rings[-1][j], rings[-1][(j + 1) % ring], tip))


# ---------------------------------------------------------------- teeth
# v28: seated on the GUM LINES of the mouth definition (cavity roof / floor), not on fixed landmark heights: the
# v18-v27 canines started 2 mm inside the jaw and showed ~0.6 mm below the roof (specks in the meow), incisors
# not at all. Crowns fit inside the closed gap (rest = closed), so the closed mouth stays sealed.
import sys as _sys, importlib as _il
if globals().get("TOOLS") and TOOLS not in _sys.path:
    _sys.path.insert(0, TOOLS)
import mouth_geom as MG
_il.reload(MG)
_G = MG.from_landmarks(L, hs)
_Ri = Rm.inverted()


def seat(p, jaw, embed, visible):
    """(base, length) for a tooth at world point p: its root `embed` m inside the gum, crown `visible` m"""
    l = _Ri @ (p - H0) / hs
    zm, e, h = MG.zm_e_h(np.array([l.x]), np.array([l.y]), _G)
    gum = float(zm[0] + h[0]) if jaw == "up" else float(zm[0] - h[0])
    zb = gum + (embed if jaw == "up" else -embed) * 1.0 / hs
    return W((l.x, l.y, zb)), embed + visible


TOOTH = {"up": dict(canine=(0.0015, 0.0042, 0.0014), incisor=(0.0004, 0.0014, 0.0005), premolar=(0.0006, 0.0012, 0.0011)),
         "lo": dict(canine=(0.0012, 0.0036, 0.0012), incisor=(0.0004, 0.0012, 0.00045), premolar=(0.0006, 0.0010, 0.0010))}
for jaw, bname in (("up", "head"), ("lo", "jaw")):
    bm = bmesh.new()
    sgn = -1 if jaw == "up" else 1
    T = TOOTH[jaw]
    for side, s in (("R", -1), ("L", 1)):
        c = Vector(L[f"canine_{jaw}.{side}"])
        base, ln = seat(c, jaw, T["canine"][0], T["canine"][1])
        tusk(bm, base, UP * sgn, -FWD, ln, T["canine"][2], curve=0.18)
        for k in range(3):  # incisors in an arc between the canines
            f = (k + 0.5) / 3
            ic = Vector(L[f"incisor_{jaw}"]) + RIGHT * (s * 0.0042 * f * hs) + FWD * (-0.0008 * f)
            base, ln = seat(ic, jaw, T["incisor"][0], T["incisor"][1])
            tusk(bm, base, UP * sgn, -FWD, ln, T["incisor"][2], curve=0.05, segs=3, ring=6)
        for k in range(2):  # premolars along the jaw
            pm = c + RIGHT * (s * 0.0012) + (-FWD) * (0.004 + 0.0045 * k)
            base, ln = seat(pm, jaw, T["premolar"][0], T["premolar"][1])
            tusk(bm, base, UP * sgn, -FWD, ln, T["premolar"][2], curve=0.05, segs=4, ring=8)
    ob = mesh_obj(f"{PREFIX}_Acc_Teeth_{jaw}", bm, "M_Teeth")
    parent_bone(ob, bname)

# ---------------------------------------------------------------- tongue (skinned)
tg = [Vector(p) for p in L["tongue"]]
tip = tg[2] + FWD * 0.004
path = [tg[0], tg[1], tg[2], tip]
bm = bmesh.new()
U, Vn = 24, 16
ring_rows = []
seglen = [(path[i + 1] - path[i]).length for i in range(3)]
tot = sum(seglen)
for i in range(U + 1):
    u = i / U
    d = u * tot
    k = 0
    while k < 2 and d > seglen[k]:
        d -= seglen[k]; k += 1
    c = path[k].lerp(path[k + 1], min(d / seglen[k], 1.0))
    w = 0.0072 * (1 - 0.55 * u ** 3) * (0.75 + 0.25 * math.sin(math.pi * min(u * 1.6, 1)))   # v28: wider (fills the jaw)
    th = 0.0020 * (1 - 0.5 * u ** 2)
    if u > 0.97:
        w *= 0.6; th *= 0.6
    row = []
    for j in range(Vn):
        a = 2 * math.pi * j / Vn
        x, z = math.cos(a) * w, math.sin(a) * th
        if z > 0:
            z -= 0.0006 * math.exp(-(x / (0.25 * w)) ** 2)  # median groove on the top
        row.append(bm.verts.new(c + RIGHT * x + UP * (z - 0.0008)))
    ring_rows.append(row)
for i in range(U):
    for j in range(Vn):
        bm.faces.new((ring_rows[i][j], ring_rows[i][(j + 1) % Vn], ring_rows[i + 1][(j + 1) % Vn], ring_rows[i + 1][j]))
bm.faces.new(list(reversed(ring_rows[0]))); bm.faces.new(ring_rows[-1])
tongue = mesh_obj(f"{PREFIX}_Acc_Tongue", bm, "M_Tongue")
for nm in ("tongue1", "tongue2", "tongue3"):
    tongue.vertex_groups.new(name=nm)
for v in tongue.data.vertices:
    rel = (v.co - tg[0]).dot(FWD.normalized()) / max((tip - tg[0]).dot(FWD.normalized()), 1e-6)
    w1 = max(0.0, 1 - abs(rel - 0.0) / 0.45); w2 = max(0.0, 1 - abs(rel - 0.5) / 0.45); w3 = max(0.0, 1 - abs(rel - 1.0) / 0.45)
    s_ = w1 + w2 + w3 or 1
    for nm, w in (("tongue1", w1), ("tongue2", w2), ("tongue3", w3)):
        if w > 0:
            tongue.vertex_groups[nm].add([v.index], w / s_, 'REPLACE')
tongue.parent = rig
tongue.matrix_parent_inverse = rig.matrix_world.inverted()
am = tongue.modifiers.new("rig", 'ARMATURE'); am.object = rig

# ---------------------------------------------------------------- claws (retracted; tips just show)
for key, bfmt in (("toes_f", "fingers.{}"), ("toes_h", "toes.{}")):
    for side in "RL":
        bm = bmesh.new()
        for t in L[key]:
            t = Vector(t)
            if (t.x < 0) != (side == "R"):
                continue
            tusk(bm, t + Vector((0, 0.0042, 0.0012)), Vector((0, -1, -0.55)), Vector((0, 0, -1)), 0.0058, 0.0007, curve=0.35)
        ob = mesh_obj(f"{PREFIX}_Acc_Claws_{key[-1]}.{side}", bm, "M_Claw")
        parent_bone(ob, bfmt.format(side))

# ---------------------------------------------------------------- whiskers
wm = bpy.data.materials.get("M_Whisker") or bpy.data.materials.new("M_Whisker")
wm.use_nodes = True
nt = wm.node_tree
for nd in list(nt.nodes):
    nt.nodes.remove(nd)
hb = nt.nodes.new("ShaderNodeBsdfHairPrincipled"); hb.parametrization = 'COLOR'
hb.inputs["Color"].default_value = (0.82, 0.80, 0.78, 1); hb.inputs["Roughness"].default_value = 0.18
hb.inputs["Radial Roughness"].default_value = 0.2
o_ = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(hb.outputs[0], o_.inputs["Surface"])
rng = np.random.default_rng(5)


def snap(p):
    loc, nrm, _, _ = skin_rest.find_nearest(p)
    return (loc, nrm) if loc is not None else (p, UP)


def whisker_set(name, roots_dirs, bone_name, K=8):
    strands = []
    for root, d0, length, droop, r0 in roots_dirs:
        root, nrm = snap(root)
        pts = []
        dirv = d0.normalized()
        for k in range(K):
            t = k / (K - 1)
            pts.append(root - nrm * 0.0008 + dirv * length * t - UP * droop * length * t * t)
        strands.append((pts, r0))
    cd = bpy.data.hair_curves.new(name)
    cd.add_curves([K] * len(strands))
    cd.attributes["position"].data.foreach_set("vector", np.array([[p[:] for p in s[0]] for s in strands], np.float32).ravel())
    ra = cd.attributes.get("radius") or cd.attributes.new("radius", 'FLOAT', 'POINT')
    ra.data.foreach_set("value", np.concatenate([np.linspace(s[1], 0.000015, K) for s in strands]).astype(np.float32))
    cd.materials.append(wm)
    ob = bpy.data.objects.new(name, cd)
    coll.objects.link(ob)
    parent_bone(ob, bone_name)
    return ob


for side, s in (("R", -1), ("L", 1)):
    wp = Vector(L[f"whiskerpad.{side}"])
    out = (RIGHT * s * 0.85 + FWD * 0.45).normalized()
    rd = []
    for row in range(4):
        for col in range(3):
            root = wp + UP * ((1.5 - row) * 0.0022) + (-FWD) * (col * 0.0026) + RIGHT * (s * (0.002 - col * 0.0004))
            d = (out + UP * (0.18 - 0.14 * row) + FWD * (0.10 - 0.08 * col) + Vector(rng.normal(0, 0.05, 3))).normalized()
            length = (0.062 - 0.006 * row - 0.004 * col) * rng.uniform(0.9, 1.08)
            rd.append((root, d, length, 0.10 + 0.04 * row, 0.00019))  # v19: thicker roots (whiskers barely read)
    whisker_set(f"{PREFIX}_Acc_Whiskers.{side}", rd, f"whisker.{side}")
    br = Vector(L[f"brow.{side}"])
    rd = []
    for k in range(4):
        root = br + RIGHT * (s * 0.0025 * k) + UP * (0.0006 * k)
        d = (UP * 0.9 + RIGHT * s * (0.35 + 0.15 * k) + FWD * 0.25).normalized()
        rd.append((root, d, (0.030 - 0.003 * k) * rng.uniform(0.9, 1.1), -0.05, 0.00008))
    for k in range(2):  # cheek (genal) whiskers behind the mouth corner
        root = W((s * 0.022, -0.010, -0.016 - 0.004 * k))
        d = (RIGHT * s + (-FWD) * 0.2 - UP * 0.15).normalized()
        rd.append((root, d, 0.028 * rng.uniform(0.9, 1.1), 0.08, 0.00008))
    whisker_set(f"{PREFIX}_Acc_BrowWhiskers.{side}", rd, "head")
print("accessories:", sorted(o.name for o in bpy.data.objects if o.name.startswith(f"{PREFIX}_Acc_")))
