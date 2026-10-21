"""BLENDER-SIDE (background): pose skinned bodies through a list of arm elevations under several deformation variants
and export what a numpy study needs to say where and why each body creases, collapses or passes through itself.
Created 2026-10-20 (woman2 build 12: what makes each body deform well or badly, mesh against mesh, rig against rig).

Usage:  blender -b --factory-startup --python pose_study_bl.py -- SPEC.json
Reads the SPEC's blend (a copy; never saved), appends only the objects it names, and writes into SPEC["out"]:
  rest_<variant>.npz   once per variant: v (bind shape, world m, float32), f (triangles), W (n x groups, float32),
                       groups, bones (deform bones: name, rest head / tail world), thick / clear (rays, below), pairs
  <variant>_<pose>.npz v (posed, world, float32), n (vertex normals), thick, clear, pairs (self-intersecting triangle
                       pairs, Blender's BVH overlap; pairs sharing a vertex are not counted), heads / tails (posed deform
                       bones), keys (shape-key values the drivers gave), arm (measured upper-arm angle from vertical,
                       L / R, deg), girdle (our rig: clavicle / scapula rotation, deg; Rigify: shoulder rotation)
  thick: inward ray along -normal to the first surface (local solid thickness, m); clear: outward ray along +normal
  (clearance to another part of the body, m); NaN where no hit within 0.4 m or outside the SPEC's ray zone.
SPEC:
  {"blend": path, "out": dir, "append": [names],
   "variants": [{"name", "mesh", "rig", "mode": "ours" | "rigify" | "quick" (root, head, clavicle SC -> shoulder joint,
                 upper arm, forearm: cases/woman2/build12/bl_quick_rig.py), "rhythm": bool (rigify / quick: the shoulder control turned
                 by our rig's clavicle elevation for the same total), "dqs": bool, "keys": bool (shape keys on),
                 "mute_mods": [modifier names], "multires": level,
                 "weights_from": {"mesh": source object (same topology), "map": {group: [source groups]}} (optional:
                 the variant's mesh is a copy of "mesh" carrying the mapped weights),
                 "poses": [total abduction from vertical, deg], "ray_zone": {"centres": [[x,y,z]], "radius": m}}]}
Our rig's rule (rig.json shoulder_rhythm): g = T - rest - max(0, (T - 30) / 3) (g = 0 for T <= rest); its drivers turn
the scapula and clavicle. Rigify: FK controls; the arm angle is corrected by measuring DEF-upper_arm until within 0.05 deg.
"""
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

SPEC = json.load(open(sys.argv[sys.argv.index("--") + 1]))
OUT = SPEC["out"]
REST = {"L": 5.93, "R": 5.95}                      # rig.json joints rest_abduction_deg (v12 and build 08 share them)
KCLAV = {"L": 0.66014, "R": 0.67554}               # rig.json clavicle drivers
vl = bpy.context.view_layer

with bpy.data.libraries.load(SPEC["blend"], link=False) as (src, dst):
    dst.objects = [n for n in SPEC["append"] if n in src.objects]
    missing = [n for n in SPEC["append"] if n not in src.objects]
assert not missing, missing
for ob in dst.objects:
    bpy.context.scene.collection.objects.link(ob)
vl.update()


def gh_for(s, total):
    return 0.0 if total <= REST[s] else total - REST[s] - max(0.0, (total - 30.0) / 3.0)


def clav_elev(s, total):
    g = gh_for(s, total); st = max(0.0, (g - (30.0 - REST[s])) / 2.0)
    return math.degrees(math.asin(min(1.0, KCLAV[s] * math.sin(math.radians(st))))), st


def arm_angle(rig, bone):
    out = []
    for s in "LR":
        d = (rig.matrix_world.to_3x3() @ rig.pose.bones[bone + "." + s].matrix.to_3x3()).col[1]
        out.append(math.degrees(math.atan2(abs(d.x), -d.z)))
    return out


def deform_bones(rig):
    return [b.name for b in rig.data.bones if b.use_deform]


def reset(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = pb.rotation_mode
        pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)


def pose_ours(rig, total):
    for s, sg in (("L", 1), ("R", -1)):
        rig.pose.bones["upper_arm." + s].rotation_euler = (0, 0, -sg * math.radians(gh_for(s, total)))
        rig.pose.bones["forearm." + s].rotation_euler = (0, 0, 0)
    vl.update(); vl.update()
    gird = {}
    for s in "LR":
        gird[s] = {"clavicle_deg": round(math.degrees(rig.pose.bones["clavicle." + s].rotation_euler[2]), 3),
                   "scapula_deg": round(math.degrees(rig.pose.bones["scapula." + s].rotation_euler[2]), 3),
                   "gh_deg": round(gh_for(s, total), 3)}
    return gird


RIGIFY = dict(shoulder="shoulder.", fk="upper_arm_fk.", measure="DEF-upper_arm", tail="DEF-shoulder.",
              reset=("upper_arm_fk.", "forearm_fk.", "hand_fk.", "shoulder."), ikfk="upper_arm_parent.")
QUICK = dict(shoulder="clavicle.", fk="upper_arm.", measure="upper_arm", tail="clavicle.",      # bl_quick_rig.py's rig
             reset=("upper_arm.", "forearm.", "clavicle."), ikfk=None)


def pose_rigify(rig, total, rhythm, ikfk, B_=RIGIFY):
    """FK arms to `total` from vertical in the frontal plane; with rhythm, the shoulder control first raises the
    shoulder's outer end by our clavicle elevation (sign checked on the bone's tail). B_ names the bones (Rigify or the
    quick rig)."""
    gird = {}
    for s, sg in (("L", 1), ("R", -1)):
        if B_["ikfk"]:
            rig.pose.bones[B_["ikfk"] + s]["IK_FK"] = ikfk
        for n in B_["reset"]:
            pb = rig.pose.bones[n + s]; pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = (1, 0, 0, 0)
    vl.update()
    for s, sg in (("L", 1), ("R", -1)):
        E, st = clav_elev(s, total) if rhythm else (0.0, 0.0)
        pb = rig.pose.bones[B_["shoulder"] + s]; B = rig.data.bones[B_["shoulder"] + s].matrix_local.to_3x3()
        t0 = (rig.matrix_world @ rig.pose.bones[B_["tail"] + s].tail).z
        for sign in (1, -1):
            Rc = Matrix.Rotation(sign * math.radians(E), 3, "Y")
            pb.rotation_quaternion = (B.inverted() @ Rc @ B).to_quaternion(); vl.update()
            if E == 0 or (rig.matrix_world @ rig.pose.bones[B_["tail"] + s].tail).z > t0:
                break
        dz = (rig.matrix_world @ rig.pose.bones[B_["tail"] + s].tail).z - t0
        gird[s] = {"shoulder_elev_deg": round(E, 3), "scapulothoracic_deg": round(st, 3), "gh_rise_mm": round(dz * 1000, 2)}
    for it in range(8):
        ang = arm_angle(rig, B_["measure"])
        err = [total - a for a in ang]
        if max(abs(e) for e in err) < 0.05:
            break
        for (s, sg), e in zip((("L", 1), ("R", -1)), err):
            pb = rig.pose.bones[B_["fk"] + s]
            M = pb.matrix.copy(); head = M.translation.copy()
            R = Matrix.Rotation(-sg * math.radians(e), 4, "Y")
            pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ M
            vl.update()
    vl.update(); vl.update()
    return gird


def mesh_arrays(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg); me = oe.to_mesh()
    n = len(me.vertices)
    v = np.empty(n * 3, np.float64); me.vertices.foreach_get("co", v); v = v.reshape(-1, 3)
    nn = np.empty(n * 3, np.float64); me.vertices.foreach_get("normal", nn); nn = nn.reshape(-1, 3)
    M = np.array(ob.matrix_world); v = v @ M[:3, :3].T + M[:3, 3]
    nn = nn @ np.linalg.inv(M[:3, :3]); nn /= np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-30)
    me.calc_loop_triangles()
    nt = len(me.loop_triangles); tri = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get("vertices", tri)
    oe.to_mesh_clear()
    return v, nn, tri.reshape(-1, 3)


def eval_weights(ob, names):
    """weights of the evaluated mesh (multires interpolates them), armature off"""
    arm = [m for m in ob.modifiers if m.type == "ARMATURE"]
    for m in arm:
        m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get(); oe = ob.evaluated_get(dg); me = oe.to_mesh()
    col = {g.index: names.index(g.name) for g in ob.vertex_groups if g.name in names}
    W = np.zeros((len(me.vertices), len(names)), np.float32)
    for v in me.vertices:
        for g in v.groups:
            j = col.get(g.group)
            if j is not None:
                W[v.index, j] = g.weight
    oe.to_mesh_clear()
    for m in arm:
        m.show_viewport = True
    return W


def rays(v, nn, f, zone):
    bvh = BVHTree.FromPolygons([tuple(p) for p in v], [tuple(t) for t in f], all_triangles=True)
    pairs = np.array(bvh.overlap(bvh), np.int32).reshape(-1, 2)
    thick = np.full(len(v), np.nan, np.float32); clear = np.full(len(v), np.nan, np.float32)
    if zone:
        c = np.array(zone["centres"]); r = zone["radius"]
        idx = np.where((((v[:, None, :] - c[None]) ** 2).sum(2) < r * r).any(1))[0]
        for i in idx:
            p = Vector(v[i]); d = Vector(nn[i])
            for arr, dd in ((thick, -d), (clear, d)):
                o = p + dd * 2e-5; tot = 2e-5
                for _ in range(4):
                    hit = bvh.ray_cast(o, dd, 0.4)
                    if hit[0] is None:
                        break
                    if hit[3] > 3e-4:
                        arr[i] = tot + hit[3]; break
                    o = hit[0] + dd * 1e-4; tot += hit[3] + 1e-4
    return pairs, thick, clear


def bone_ends(rig, names):
    M = rig.matrix_world
    return (np.array([tuple(M @ rig.pose.bones[k].head) for k in names], np.float32),
            np.array([tuple(M @ rig.pose.bones[k].tail) for k in names], np.float32))


log = {}
for var in SPEC["variants"]:
    name = var["name"]; rig = bpy.data.objects[var["rig"]]; ob = bpy.data.objects[var["mesh"]]
    if var.get("weights_from"):
        wf = var["weights_from"]; srcob = bpy.data.objects[wf["mesh"]]
        me = ob.data.copy(); ob2 = bpy.data.objects.new(name + "_mesh", me); bpy.context.scene.collection.objects.link(ob2)
        ob2.parent = ob.parent; ob2.matrix_parent_inverse = ob.matrix_parent_inverse.copy(); ob2.matrix_basis = ob.matrix_basis.copy()
        m2 = ob2.modifiers.new("Armature", "ARMATURE"); m2.object = rig      # the skin alone: no micro relief
        if me.shape_keys:
            ob2.shape_key_clear()
        keep = set(wf["map"])
        for g in list(ob2.vertex_groups):
            if g.name in keep:
                ob2.vertex_groups.remove(g)
        sgroups = sorted({s for l in wf["map"].values() for s in l})
        Ws = eval_weights(srcob, sgroups)
        for gname, srcs in wf["map"].items():
            w = Ws[:, [sgroups.index(s) for s in srcs]].sum(1) if srcs else np.zeros(len(Ws), np.float32)
            g = ob2.vertex_groups.new(name=gname)
            for i in np.where(w > 0)[0]:
                g.add([int(i)], float(min(1.0, w[i])), "REPLACE")
        ob = ob2
    for m in ob.modifiers:
        if m.name in var.get("mute_mods", []):
            m.show_viewport = False
        if m.type == "MULTIRES" and var.get("multires") is not None:
            m.levels = var["multires"]
        if m.type == "ARMATURE":
            m.use_deform_preserve_volume = bool(var.get("dqs", False))
    if ob.data.shape_keys:
        for k in ob.data.shape_keys.key_blocks[1:]:
            k.mute = not var.get("keys", True)
    defs = deform_bones(rig)
    ikfk = 1.0
    if var["mode"] == "rigify":
        print("IK_FK in file", {s: rig.pose.bones["upper_arm_parent." + s].get("IK_FK") for s in "LR"},
              "FK_limb_follow", {s: rig.pose.bones["upper_arm_parent." + s].get("FK_limb_follow") for s in "LR"})
        ikfk = float(var.get("ikfk", 1.0))
    # rest (every pose bone at identity)
    reset(rig); vl.update(); vl.update()
    v, nn, f = mesh_arrays(ob)
    groups = [g.name for g in ob.vertex_groups if g.name in defs]
    W = eval_weights(ob, groups)
    pairs, thick, clear = rays(v, nn, f, var.get("ray_zone"))
    h, t = bone_ends(rig, defs)
    np.savez_compressed(f"{OUT}/rest_{name}.npz", v=v.astype(np.float32), n=nn.astype(np.float32), f=f, W=W,
                        groups=np.array(groups), bones=np.array(defs), heads=h, tails=t, thick=thick, clear=clear, pairs=pairs)
    log[name] = {"verts": len(v), "tris": len(f), "rest_pairs": len(pairs),
                 "unweighted": int((W.sum(1) <= 1e-6).sum()), "poses": {}}
    for T in var["poses"]:
        reset(rig); vl.update()
        if var["mode"] == "ours":
            gird = pose_ours(rig, T)
        else:
            gird = pose_rigify(rig, T, var.get("rhythm", False), ikfk, QUICK if var["mode"] == "quick" else RIGIFY)
        ang = arm_angle(rig, "DEF-upper_arm" if var["mode"] == "rigify" else "upper_arm")
        v, nn, _ = mesh_arrays(ob)
        pairs, thick, clear = rays(v, nn, f, var.get("ray_zone"))
        h, t = bone_ends(rig, defs)
        keys = {k.name: round(k.value, 4) for k in ob.data.shape_keys.key_blocks[1:]} if ob.data.shape_keys else {}
        np.savez_compressed(f"{OUT}/{name}_{int(T)}.npz", v=v.astype(np.float32), n=nn.astype(np.float32), thick=thick,
                            clear=clear, pairs=pairs, heads=h, tails=t, bones=np.array(defs),
                            arm=np.array(ang), girdle=json.dumps(gird), keys=json.dumps(keys))
        log[name]["poses"][str(T)] = {"arm_deg": [round(a, 2) for a in ang], "pairs": len(pairs), "girdle": gird,
                                      "keys_on": {k: x for k, x in keys.items() if x > 0 and not ob.data.shape_keys.key_blocks[k].mute}}
        print("POSED", name, T, log[name]["poses"][str(T)], flush=True)
    reset(rig); vl.update()
json.dump(log, open(f"{OUT}/log_{SPEC.get('tag', 'run')}.json", "w"), indent=1)
print("DONE", json.dumps(log)[:4000])
