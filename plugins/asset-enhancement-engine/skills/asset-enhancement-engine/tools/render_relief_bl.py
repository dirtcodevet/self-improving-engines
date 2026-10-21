"""RENDER RELIEF (2026-10-19, woman2 issue 03): the render stack's own micro displacement as it is realised on a pack's
mesh near given points - run in a BACKGROUND Blender (never the live one). The pack's micro_detail.json layer (render-only
Skin_micro_subdiv + Skin_micro_detail: Voronoi pores along the normal, weighted by pores_strength) shows only where the
mesh is dense enough to hold it, so a mesh change (the NAC patches rebuilt coarser) changes what renders there; this
reads what renders.
    blender -b --factory-startup --python engine/tools/render_relief_bl.py -- <pack> <out.npz> <x,y,z;x,y,z> [radius_m]
Builds the pack with build_base_torso.py, keeps the skin within radius of the points (so the subdivision stays small; the
pores use object coordinates, so cutting does not move them), sets the micro layer's render settings in the viewport,
and writes p0 (positions without the displacement, subdivided as rendered), d (displacement along the evaluated normal,
m) and tri (triangles)."""
import bpy, bmesh, json, os, sys, time
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "engine", "tools"))
import build_base_torso as BT  # noqa: E402

a = sys.argv[sys.argv.index("--") + 1:]
V, OUT = os.path.abspath(a[0]), a[1]
pts = np.array([[float(x) for x in p.split(",")] for p in a[2].split(";")]); rad = float(a[3]) if len(a) > 3 else 0.028
assert bpy.app.background
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
sc = json.load(open(os.path.join(V, "scene.json"))); BT._build_v2(V, sc, (0, 0, 0), None, False, lambda *x: None, time.time())
ob = bpy.data.objects[sc["objects"]["torso"]]; me = ob.data
co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
far = np.ones(len(co), bool)
for p in pts: far &= np.linalg.norm(co - p, axis=1) > rad
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.verts[i] for i in np.where(far)[0]], context="VERTS"); bm.to_mesh(me); bm.free()
sub, dis = ob.modifiers["Skin_micro_subdiv"], ob.modifiers["Skin_micro_detail"]
sub.levels = sub.render_levels; sub.show_viewport = sub.show_render


def ev():
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); e = ob.evaluated_get(dg); m = e.to_mesh()
    x = np.zeros(len(m.vertices) * 3); m.vertices.foreach_get("co", x); n = np.zeros(len(m.vertices) * 3); m.vertices.foreach_get("normal", n)
    m.calc_loop_triangles(); t = np.zeros(len(m.loop_triangles) * 3, np.int64); m.loop_triangles.foreach_get("vertices", t)
    e.to_mesh_clear(); return x.reshape(-1, 3), n.reshape(-1, 3), t.reshape(-1, 3)


dis.show_viewport = False; P0, N0, T = ev()
dis.show_viewport = dis.show_render; P1, _, T1 = ev()
assert len(P0) == len(P1)          # same vertices; quads may triangulate differently once displaced (T from the undisplaced)
d = ((P1 - P0) * N0).sum(1)
np.savez_compressed(OUT, p0=P0, d=d, tri=T, subdiv_levels=sub.render_levels, displace_on=bool(dis.show_render))
print("RENDER_RELIEF", json.dumps({"vertices": len(P0), "levels": sub.render_levels, "displace": bool(dis.show_render),
                                   "d_abs_max_um": float(np.abs(d).max() * 1e6)}))
