# Blender-side: apply a named test pose to <PREFIX>_Rig, measure deformation quality on the skin, optionally
# render head/body views, then (unless KEEP) restore the rest pose.
# Pose spec: POSE = {bone: (rx, ry, rz) degrees}. Metrics: max/p99 edge-length strain (stretch/squash) and
# fur strands still attached (root distance to deformed skin).
import bpy, math, json
import numpy as np

PREFIX = globals().get("PREFIX", "Cat")
POSE = globals().get("POSE", {})
rig = bpy.data.objects[f"{PREFIX}_Rig"]
skin = bpy.data.objects[f"{PREFIX}_Skin"]
for pb in rig.pose.bones:
    pb.rotation_euler = (0, 0, 0)
    pb.location = (0, 0, 0)
for b, (rx, ry, rz) in POSE.items():
    rig.pose.bones[b].rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
me0 = skin.data
ev = skin.evaluated_get(dg).data
n = len(me0.vertices)
a = np.empty(n * 3, np.float32); me0.vertices.foreach_get("co", a); a = a.reshape(-1, 3)
b = np.empty(n * 3, np.float32); ev.vertices.foreach_get("co", b); b = b.reshape(-1, 3)
e = np.empty(len(me0.edges) * 2, np.int32); me0.edges.foreach_get("vertices", e); e = e.reshape(-1, 2)
l0 = np.linalg.norm(a[e[:, 0]] - a[e[:, 1]], axis=1)
l1 = np.linalg.norm(b[e[:, 0]] - b[e[:, 1]], axis=1)
strain = np.abs(np.log(np.maximum(l1, 1e-9) / np.maximum(l0, 1e-9)))
moved = np.linalg.norm(b - a, axis=1)
res = {"pose": list(POSE.keys()), "strain_p99": float(np.percentile(strain, 99)), "strain_max": float(strain.max()),
       "worst_edge_at": b[e[int(np.argmax(strain)), 0]].round(4).tolist(), "max_move_mm": float(moved.max() * 1000)}
fur = bpy.data.objects.get(f"{PREFIX}_Fur")
if fur:
    fe = fur.evaluated_get(dg).data
    m = len(fe.curves)
    if m:
        from mathutils.bvhtree import BVHTree
        bvh = BVHTree.FromObject(skin, dg)
        pos = np.empty(len(fe.points) * 3, np.float32); fe.attributes["position"].data.foreach_get("vector", pos)
        pos = pos.reshape(-1, 3)
        off = np.empty(m, np.int32); fe.curves.foreach_get("first_point_index", off)
        roots = pos[off][:: max(m // 3000, 1)]
        mw = fur.matrix_world
        d = [bvh.find_nearest(mw @ __import__("mathutils").Vector(p))[3] for p in roots]
        res["fur_root_gap_p99_mm"] = float(np.percentile(d, 99) * 1000)
print(json.dumps(res))
if "OUT" in globals():
    exec(open(globals()["VIEWS"]).read())
if not globals().get("KEEP", False):
    for pb in rig.pose.bones:
        pb.rotation_euler = (0, 0, 0)
