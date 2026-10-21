"""POSE SAMPLES (background Blender only): a format-3 pack posed by its own controls at named poses, exported with each
vertex's skinning Jacobian, so a corrective computed on the posed skin can be stored as a rest-space shape key exactly.
Created 2026-10-21 (woman2 build 13c: corrective shapes by computation).

Why: shape keys are added BEFORE the armature, and the posed result of rest + d is linear in d for a fixed pose (linear
skinning A_v d, dual quaternion R_v d, the mix of the two by its vertex group). Blender's dual-quaternion blend is not
re-implemented here: the Jacobian is read off Blender itself by three unit shape keys (d = h along x, y, z on the
chosen vertices), so J_v = d(posed)/d(rest) is the as-built deformation, mix and drivers included, to float precision.
A posed fix D then goes into the rest space as J_v^-1 D (engine/tools/pose_correctives.py, to_rest).

Usage:  blender -b --factory-startup --python engine/tools/pose_samples_bl.py -- SPEC.json
SPEC: {"build_pack": pack dir, "root": engine checkout, "out": dir (absolute),
       "poses": {name: {"rot": {bone: [x, y, z] rad}, "props": {bone: {prop: value}}}},
       "jac_idx": .npy of vertex indices (optional; no Jacobian without it), "h": offset m (default 0.01),
       "mute_mods": [modifier names] (default the micro-detail layer), "keys": true (the pack's own shape keys on)}
Writes OUT/<name>.npz: v (posed skin, world, float64), cw (posed chest wall), J (len(idx), 3, 3) with J[:, :, k] =
d posed / d rest_k, keys (json of shape-key values the drivers gave), girdle (json: e, p, a per side).
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np

SPEC = json.load(open(sys.argv[sys.argv.index("--") + 1]))
OUT = SPEC["out"]
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_base_torso as BBT  # noqa: E402

t0 = time.time()
info = BBT.build(pack=SPEC["build_pack"], root=SPEC.get("root"))
sc = json.load(open(os.path.join(SPEC["build_pack"], "scene.json")))
P = sc["prefix"]
ob = bpy.data.objects[sc["objects"]["body"]]
rig = bpy.data.objects[sc["objects"]["rig"]]
cw = bpy.data.objects.get(sc["objects"].get("chest_wall", ""))
vl = bpy.context.view_layer
for m in ob.modifiers:
    if m.name in SPEC.get("mute_mods", ["Skin_micro_subdiv", "Skin_micro_detail"]):
        m.show_viewport = False
use_keys = SPEC.get("keys", True)
me = ob.data
if me.shape_keys:
    for k in me.shape_keys.key_blocks[1:]:
        k.mute = not use_keys
n = len(me.vertices)
base = np.empty(n * 3, np.float32)
me.vertices.foreach_get("co", base)
base = base.reshape(-1, 3)
idx = np.load(SPEC["jac_idx"]) if SPEC.get("jac_idx") else None
h = float(SPEC.get("h", 0.01))
jk = []
if idx is not None:
    if not me.shape_keys:
        ob.shape_key_add(name="Basis", from_mix=False)
    for a in range(3):
        k = ob.shape_key_add(name="_jac%d" % a, from_mix=False)
        co = base.copy()
        co[idx, a] += h
        k.data.foreach_set("co", co.ravel())
        k.value = 0.0
        jk.append(k)
print("SAMPLES built", json.dumps(info)[:300], "jac verts", 0 if idx is None else len(idx), flush=True)


def evaluated(o):
    dg = bpy.context.evaluated_depsgraph_get()
    oe = o.evaluated_get(dg)
    m = oe.to_mesh()
    v = np.empty(len(m.vertices) * 3, np.float64)
    m.vertices.foreach_get("co", v)
    oe.to_mesh_clear()
    M = np.array(o.matrix_world)
    return v.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]


def reset():
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
        for k in ("shrug", "pinch", "round", "tilt", "roll_amount", "roll_phase"):
            if k in pb.keys():
                pb[k] = 0.0


def pose(Pz):
    for bn, rot in Pz.get("rot", {}).items():
        rig.pose.bones[bn].rotation_euler = rot
    for bn, props in Pz.get("props", {}).items():
        for k, v in props.items():
            rig.pose.bones[bn][k] = float(v)
    vl.update(); vl.update()
    g = {}
    for s in "LR":
        sb = rig.pose.bones.get("shoulder." + s)
        if sb is not None:
            g[s] = {k: round(float(sb[k]), 4) for k in ("e", "p", "a", "shs", "pit", "rot", "tit") if k in sb.keys()}
    return g


log = {}
for name, Pz in SPEC["poses"].items():
    t1 = time.time()
    reset(); vl.update()
    g = pose(Pz)
    v = evaluated(ob)
    out = {"v": v, "girdle": json.dumps(g)}
    if cw is not None:
        out["cw"] = evaluated(cw)
    if me.shape_keys:
        out["keys"] = json.dumps({k.name: round(k.value, 5) for k in me.shape_keys.key_blocks[1:] if not k.name.startswith("_jac")})
    if idx is not None:
        J = np.empty((len(idx), 3, 3), np.float64)
        for a, k in enumerate(jk):
            k.value = 1.0
            vl.update()
            J[:, :, a] = (evaluated(ob)[idx] - v[idx]) / h
            k.value = 0.0
        vl.update()
        out["J"] = J.astype(np.float32)
    np.savez(os.path.join(OUT, name + ".npz"), **out)
    log[name] = {"girdle": g, "s": round(time.time() - t1, 1)}
    print("SAMPLE", name, log[name], flush=True)
json.dump({"build": info, "poses": log, "seconds": round(time.time() - t0, 1)}, open(os.path.join(OUT, "log.json"), "w"), indent=1)
print("DONE", round(time.time() - t0, 1))
