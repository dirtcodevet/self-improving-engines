# Blender-side: deformation coherence across an animation. For sampled frames: skin edge strain (p99/max),
# biggest-strain location, fur-root attachment gap, eyeball-vs-lid penetration count, ground penetration.
# Globals: FRAMES (list), optional OUT_DIR + VIEWS (renders a clay views sheet per frame).
import bpy, json
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

PREFIX = globals().get("PREFIX", "Cat")
FRAMES = globals().get("FRAMES", [1, 40, 62, 84, 130, 165])
sc = bpy.context.scene
skin = bpy.data.objects[f"{PREFIX}_Skin"]
me0 = skin.data
n = len(me0.vertices)
a = np.empty(n * 3, np.float32); me0.vertices.foreach_get("co", a); a = a.reshape(-1, 3)
e = np.empty(len(me0.edges) * 2, np.int32); me0.edges.foreach_get("vertices", e); e = e.reshape(-1, 2)
l0 = np.linalg.norm(a[e[:, 0]] - a[e[:, 1]], axis=1)
rows = []
for f in FRAMES:
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = skin.evaluated_get(dg).data
    b = np.empty(n * 3, np.float32); ev.vertices.foreach_get("co", b); b = b.reshape(-1, 3)
    l1 = np.linalg.norm(b[e[:, 0]] - b[e[:, 1]], axis=1)
    strain = np.abs(np.log(np.maximum(l1, 1e-9) / np.maximum(l0, 1e-9)))
    row = {"frame": f, "strain_p99": round(float(np.percentile(strain, 99)), 3), "strain_max": round(float(strain.max()), 2),
           "worst_at": b[e[int(np.argmax(strain)), 0]].round(3).tolist(),
           "below_ground_mm": round(float(-min(b[:, 2].min(), 0) * 1000), 2)}
    # eyeballs: count skin verts that ended up INSIDE an eyeball (lid sliding through the eye)
    pen = 0
    for side in "RL":
        eye = bpy.data.objects.get(f"{PREFIX}_Eye.{side}")
        if eye:
            c = np.array(eye.matrix_world.translation); r = eye.matrix_world.to_scale()[0]
            pen += int((np.linalg.norm(b - c, axis=1) < r * 0.97).sum())
    row["skin_inside_eyeballs"] = pen
    # closed-mouth frames: teeth/tongue must stay inside the skin (v18 canines poked through the closed lips)
    jaw_pb = bpy.data.objects[f"{PREFIX}_Rig"].pose.bones.get("jaw")
    import math as _m   # v27: closed angle is a parameter (rest = closed, 0.5 deg); v22-v26 tested x > 0
    if jaw_pb is not None and jaw_pb.rotation_euler.x >= _m.radians(float(globals().get("CLOSED_JAW", 0.5)) - 0.25):
        bvh_s = BVHTree.FromObject(skin, dg)
        out_ = 0
        for o in bpy.data.objects:
            if o.name.startswith(f"{PREFIX}_Acc_Teeth") or o.name.startswith(f"{PREFIX}_Acc_Tongue"):
                me_ = o.evaluated_get(dg).to_mesh()
                cv = np.empty(len(me_.vertices) * 3, np.float32); me_.vertices.foreach_get("co", cv)
                # EXPOSED = a ray from the part outward (away from the head centre, +/- 25 deg) escapes without
                # hitting skin. (v1 used "outside by surface normal": the oral cavity is outside the solid too,
                # so properly hidden teeth counted.)
                hc = Vector(json.load(open(skin["landmarks_file"]))["landmarks"]["head"])
                for c3 in cv.reshape(-1, 3)[::3]:   # bpy collections do not support stepped slices
                    p = o.matrix_world @ Vector(c3)
                    d0 = (p - hc).normalized()
                    side = d0.orthogonal().normalized()
                    for dv in (d0, (d0 + side * 0.45).normalized(), (d0 - side * 0.45).normalized()):
                        hit = bvh_s.ray_cast(p + dv * 0.0002, dv, 0.15)
                        if hit[0] is None:
                            out_ += 1
                            break
                o.evaluated_get(dg).to_mesh_clear()
        row["mouth_parts_exposed"] = out_
    fur = bpy.data.objects.get(f"{PREFIX}_Fur")
    if fur:
        fe = fur.evaluated_get(dg).data
        if len(fe.curves):
            bvh = BVHTree.FromObject(skin, dg)
            pos = np.empty(len(fe.points) * 3, np.float32); fe.attributes["position"].data.foreach_get("vector", pos)
            off = np.empty(len(fe.curves), np.int32); fe.curves.foreach_get("first_point_index", off)
            roots = pos.reshape(-1, 3)[off][:: max(len(off) // 2000, 1)]
            d = [bvh.find_nearest(fur.matrix_world @ Vector(p))[3] for p in roots]
            row["fur_gap_p99_mm"] = round(float(np.percentile(d, 99) * 1000), 2)
    rows.append(row)
    if "OUT_DIR" in globals():
        OUT = f"{OUT_DIR}\\anim_f{f:03d}.png"
        exec(open(VIEWS).read())
sc.frame_set(1)
print(json.dumps(rows, indent=0))
