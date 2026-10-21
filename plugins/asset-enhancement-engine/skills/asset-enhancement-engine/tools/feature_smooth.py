# Blender-side: local, non-shrinking (Taubin) smoothing of ENGINEERED feature edges on <PREFIX>_Skin - lip margins,
# nostrils, eyelid margins - which staircase at voxel scale (v23 lips looked torn). Runs right after production_mesh,
# before coat/groom/rig, so nothing rooted on the skin moves afterwards. numpy + Blender only (no scipy in Blender).
# Globals: PREFIX, ITERS (default 10).
import bpy, json
import numpy as np

PREFIX = globals().get("PREFIX", "Cat")
ITERS = int(globals().get("ITERS", 10))
skin = bpy.data.objects[f"{PREFIX}_Skin"]
me = skin.data
J = json.load(open(skin["landmarks_file"]))
L, P = J["landmarks"], J["params"]
n = len(me.vertices)
co = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3).astype(np.float64)
R = np.array(L["head_R"]); H0 = np.array(L["head"]); hs = P["head_scale"]
hl = ((co - H0) @ R) / hs
x, y, z = hl.T


def ss(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


w = np.zeros(n)
if "mouth" in L:
    import importlib, mouth_geom as MG; importlib.reload(MG)     # the ONE mouth definition (= slit_cavity)
    zm, e, _h = MG.zm_e_h(x, y, MG.from_landmarks(L, hs))
    w = np.maximum(w, ss(0.0045, 0.0015, np.abs(z - zm)) * ss(1.25, 1.05, e))
if "rhinarium" in L:
    for c_, r_ in L["rhinarium"]:
        d = np.linalg.norm((hl - np.array(c_)) / (np.array(r_) * 1.6), axis=1)
        w = np.maximum(w, 0.7 * ss(1.0, 0.6, d))
er = L["eye_r"]
for side in "RL":
    if f"eye.{side}" in L:
        de = np.linalg.norm(co - np.array(L[f"eye.{side}"]), axis=1)
        w = np.maximum(w, 0.6 * ss(er + 0.0035, er + 0.0012, de) * (de > er - 0.0005))
sel = w > 0.02
e2 = np.empty(len(me.edges) * 2, np.int32); me.edges.foreach_get("vertices", e2); e2 = e2.reshape(-1, 2)
keep = sel[e2[:, 0]] | sel[e2[:, 1]]
a_, b_ = e2[keep, 0], e2[keep, 1]
deg = np.zeros(n); np.add.at(deg, a_, 1); np.add.at(deg, b_, 1)
for it in range(ITERS * 2):
    lam = 0.5 if it % 2 == 0 else -0.53            # Taubin: smooth, then inflate -> no shrinkage
    acc = np.zeros_like(co)
    np.add.at(acc, a_, co[b_]); np.add.at(acc, b_, co[a_])
    lap = np.where(deg[:, None] > 0, acc / np.maximum(deg, 1)[:, None] - co, 0)
    co = co + (lam * w)[:, None] * lap
me.vertices.foreach_set("co", co.astype(np.float32).ravel())
me.update()
print(f"feature smooth: {int(sel.sum())} verts (lips/nostrils/lid margins), {ITERS} Taubin passes")
