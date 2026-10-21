# Blender-side: lips that actually meet. Adds shape key 'lips_seal' to <PREFIX>_Skin moving the upper and lower lip
# margins (vertices within ~1.5 mm of the mouth separation, inside the slit outline) onto the separation surface,
# and drives it from the jaw bone: sealed at the resting closed angle, released as the jaw opens.
# (Painting/fur could not hide the dark gap: it is geometry - the person's "make real anatomical structures".)
# Globals: PREFIX, CLOSED_DEG (default 4.5), OPEN_DEG (seal fully off by this opening, default -2.0).
import bpy, json, math
import numpy as np

PREFIX = globals().get("PREFIX", "Cat")
CLOSED = math.radians(globals().get("CLOSED_DEG", 4.5))
OPEN = math.radians(globals().get("OPEN_DEG", -2.0))
skin = bpy.data.objects[f"{PREFIX}_Skin"]
rig = bpy.data.objects[f"{PREFIX}_Rig"]
me = skin.data
J = json.load(open(skin["landmarks_file"]))
L, P = J["landmarks"], J["params"]
R = np.array(L["head_R"]); H0 = np.array(L["head"]); hs = P["head_scale"]
n = len(me.vertices)
co = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3).astype(np.float64)
hl = ((co - H0) @ R) / hs
x, y, z = hl.T
import importlib, mouth_geom as MG; importlib.reload(MG)     # the ONE mouth definition (= slit_cavity)
G = MG.from_landmarks(L, hs)
zm, e, _h = MG.zm_e_h(x, y, G)
dz = z - zm
gap = G["gap_edge"]            # lip-zone half gap (the thin part where the slab exits the skin)
# v23: smooth 3 mm falloff - moving only a 1.6 mm margin band tore the lip edges (jagged) and left gaps
FALL = 0.003
band = (e < 1.15) & (np.abs(dz) < gap + FALL) & (np.abs(dz) > 0.00005) & (y < 0.0)
t_ = np.clip((np.abs(dz) - gap) / FALL, 0, 1)
w = (1 - t_ * t_ * (3 - 2 * t_)) * np.clip((1.15 - e) / 0.15, 0, 1)
move_local = np.zeros_like(hl)
move_local[:, 2] = -np.sign(dz) * (gap - 0.00008) * w * band     # every vertex in the band shifts by the gap x falloff
move_world = (move_local * hs) @ R.T

if not me.shape_keys:
    skin.shape_key_add(name="Basis", from_mix=False)
kb = me.shape_keys.key_blocks.get("lips_seal") or skin.shape_key_add(name="lips_seal", from_mix=False)
kb.data.foreach_set("co", (co + move_world).astype(np.float32).ravel())
kb.slider_min, kb.slider_max = 0.0, 1.0
try:
    kb.driver_remove("value")
except Exception:
    pass
fc = kb.driver_add("value")
drv = fc.driver
drv.type = 'SCRIPTED'
var = drv.variables.new()
var.name, var.type = "jaw", 'TRANSFORMS'
t = var.targets[0]
t.id, t.bone_target, t.transform_type, t.transform_space = rig, "jaw", 'ROT_X', 'LOCAL_SPACE'
drv.expression = f"max(0.0, min(1.0, (jaw - ({OPEN:.5f})) / ({CLOSED - OPEN:.5f})))"
print(f"lip seal: {int(band.sum())} lip-margin verts, max move {np.abs(move_world).max()*1000:.2f} mm, driver '{drv.expression}'")
