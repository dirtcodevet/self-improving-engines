# Blender-side: compare hair directions with directions a PERSON marked on the photo (engine-grounding G12: a person's
# marks are hints, checked against what the data shows). For each marked segment, the visible skin point under it;
# its structure prior (hair_tracts), its photo measurement (photo_flow.npz) and its final growth field (hair_dir)
# are projected through the frozen camera and compared with the mark (orientation, mod 180).
# Globals: MARKS (json: segments x, y, angle_deg in photo pixels), FLOW (photo_flow.npz), PREFIX, OUT_JSON (optional).
import bpy, json, importlib
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import hair_tracts as HT
importlib.reload(HT)

PREFIX = globals().get("PREFIX", "Cat")
sc = bpy.context.scene
skin = bpy.data.objects[f"{PREFIX}_Skin"]
rig = bpy.data.objects.get(f"{PREFIX}_Rig")
pp = rig.data.pose_position if rig else None
try:
    if rig:
        rig.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    me = skin.data; n = len(me.vertices)
    co = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3).astype(float)
    nr = np.empty(n * 3, np.float32); me.vertices.foreach_get("normal", nr); nr = nr.reshape(-1, 3).astype(float)
    zone = np.empty(n, np.float32); me.attributes["zone"].data.foreach_get("value", zone); zone = np.round(zone)
    hd = np.empty(n * 3, np.float32); me.attributes["hair_dir"].data.foreach_get("vector", hd); hd = hd.reshape(-1, 3).astype(float)
    L = json.load(open(skin["landmarks_file"]))["landmarks"]
    import os
    _tf = os.path.join(os.path.dirname(os.path.dirname(skin["landmarks_file"])), "hair_tracts.json")
    TRACTS = json.load(open(_tf)) if (os.path.exists(_tf) and globals().get("USE_TRACTS", True)) else None
    F = np.load(FLOW); ang = F["angle_deg"].astype(float); H, W = ang.shape
    trust = F["coherence"].astype(float) * (F["outline_w"].astype(float) if "outline_w" in F else 1.0)
    cam = sc.camera; dg = bpy.context.evaluated_depsgraph_get()
    M = np.array(cam.calc_matrix_camera(dg, x=W, y=H)) @ np.array(cam.matrix_world.inverted())

    def proj(p):
        h = np.c_[p, np.ones(len(p))] @ M.T; ndc = h[:, :2] / h[:, 3:4]
        return np.stack([(ndc[:, 0] + 1) / 2 * W, (1 - (ndc[:, 1] + 1) / 2) * H], 1)

    uv = proj(co)
    cpos = np.array(cam.matrix_world.translation)
    bvh = BVHTree.FromObject(skin, dg)
    marks = json.load(open(MARKS))["segments"]
    adiff = lambda a, b: abs(((a - b) + 90) % 180 - 90)
    rows = []
    for m in marks:
        near = np.where(np.hypot(uv[:, 0] - m["x"], uv[:, 1] - m["y"]) < 3.0)[0]
        near = near[np.argsort(np.linalg.norm(co[near] - cpos, axis=1))]
        vi = None
        for i in near[:40]:
            d_ = (cpos - co[i]) / np.linalg.norm(cpos - co[i])
            if (nr[i] @ d_) > 0.05 and bvh.ray_cast(Vector(co[i] + d_ * 0.0006), Vector(d_), np.linalg.norm(cpos - co[i]))[0] is None:
                vi = i; break
        if vi is None:
            continue
        pr = HT.unit(HT.tract_field(co[vi:vi + 1], nr[vi:vi + 1], zone[vi:vi + 1], L, tracts=TRACTS))[0]
        a_of = lambda v: float(np.degrees(np.arctan2(*(proj(co[vi:vi + 1] + 0.001 * v)[0] - uv[vi])[::-1])) % 180)
        xi, yi = int(m["x"]), int(m["y"])
        rows.append(dict(x=m["x"], y=m["y"], mark=m["angle_deg"], prior=a_of(pr), photo=float(ang[yi, xi]),
                         trust=float(trust[yi, xi]), field=a_of(hd[vi]), zone=int(zone[vi])))
    for r in rows:
        r["err_prior"], r["err_photo"], r["err_field"] = (adiff(r[k], r["mark"]) for k in ("prior", "photo", "field"))
    med = {k: float(np.median([r[k] for r in rows])) for k in ("err_prior", "err_photo", "err_field")}
    print(f"marks checked {len(rows)}/{len(marks)}  median error vs the person's marks: structure prior {med['err_prior']:.0f} deg, "
          f"photo measurement {med['err_photo']:.0f} deg, growth field {med['err_field']:.0f} deg")
    for r in rows:
        print(f"  ({r['x']:.0f},{r['y']:.0f}) mark {r['mark']:4.0f}  prior {r['prior']:4.0f}  photo {r['photo']:4.0f} (trust {r['trust']:.2f})  field {r['field']:4.0f}  zone {r['zone']}")
    if globals().get("OUT_JSON"):
        json.dump(dict(median=med, rows=rows), open(OUT_JSON, "w"), indent=1)
finally:
    if rig:
        rig.data.pose_position = pp
