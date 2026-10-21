# Blender-side check of the OPEN mouth at the widest jaw frame (meow), seen face-on (following the posed head):
# orthographic rays on a 0.25 mm grid over the mouth; the first hit decides each ray: tooth, tongue, mouth
# interior (skin hit behind the lip front), or outer skin. Reports
#   taper     = opening width at 75% of its height / width at 25% (rectangle ~1.0; a cat's meow tapers, < 0.85)
#   tongue    = tongue share of the opening        teeth = tooth share   canines_up = rays on each upper canine
#   interior_lum = mean RENDERED luminance (Cycles, scene look, fur on) over the opening, 0..1 display values
# v28: the person's round-1 "mouth looks like a square" held for the open mouth (v27d: rectangle, teeth specks,
# near-black interior). Gate (provisional, person to confirm): taper < 0.85, tongue > 0.08, each upper canine
# >= 10 rays, interior_lum > 0.35. Globals: PREFIX, FRAME (default: frame of the widest jaw), OUT_JSON (optional).
import bpy, json, math, sys, importlib
import numpy as np
if globals().get("TOOLS") and TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
import mouth_geom as MG
importlib.reload(MG)
from mathutils import Vector
from mathutils.bvhtree import BVHTree

PREFIX = globals().get("PREFIX", "Cat")
sc = bpy.context.scene
rig = bpy.data.objects[f"{PREFIX}_Rig"]
skin = bpy.data.objects[f"{PREFIX}_Skin"]
_mo_f0 = sc.frame_current
try:
    fr = globals().get("FRAME")
    if fr is None:
        best = (sc.frame_start, 0.0)
        for f in range(sc.frame_start, sc.frame_end + 1):
            sc.frame_set(f)
            a = rig.pose.bones["jaw"].rotation_euler.x
            if a < best[1]:
                best = (f, a)
        fr = best[0]
    sc.frame_set(int(fr))
    dg = bpy.context.evaluated_depsgraph_get()
    J = json.load(open(skin["landmarks_file"]))
    L = J["landmarks"]
    R = np.array(L["head_R"])
    hb = rig.pose.bones["head"]
    D = (rig.matrix_world @ hb.matrix) @ (rig.matrix_world @ hb.bone.matrix_local).inverted()
    D3 = np.array(D.to_3x3())
    fwd = D3 @ (R @ np.array([0, -1.0, 0]))       # face front (world)
    up = D3 @ (R @ np.array([0, 0, 1.0]))
    right = np.cross(up, fwd)                     # right x up = fwd (camera X, Y, Z=fwd: a proper rotation)
    c = np.array(D @ Vector(L["mouth_front"]))
    objs = {"skin": skin}
    for o in bpy.data.objects:
        if o.name.startswith(f"{PREFIX}_Acc_Teeth"):
            objs[o.name] = o
        if o.name.startswith(f"{PREFIX}_Acc_Tongue"):
            objs["tongue"] = o
    bvh = {k: BVHTree.FromObject(o, dg) for k, o in objs.items()}
    # oral-cavity skin = the slit's own walls at REST (the mouth definition), by vertex index (topology is stable)
    hs = J["params"]["head_scale"]
    n_ = len(skin.data.vertices)
    co = np.empty(n_ * 3, np.float32); skin.data.vertices.foreach_get("co", co)
    hl = ((co.reshape(-1, 3).astype(np.float64) - np.array(L["head"])) @ R) / hs
    zm_, e_, h_ = MG.zm_e_h(hl[:, 0], hl[:, 1], MG.from_landmarks(L, hs))
    oral = (e_ < 1.0) & (np.abs(hl[:, 2] - zm_) < h_ + 0.0004)
    me = skin.evaluated_get(dg).data
    step, half = 0.00025, 0.018
    c = c - up * 0.012                              # grid centre: below the lip front (the jaw drops)
    us = np.arange(-half, half + 1e-9, step)
    vs = np.arange(-half, half + 1e-9, step)
    cls = np.zeros((len(vs), len(us)), np.int8)   # 0 outer skin/none, 1 interior, 2 tongue, 3 tooth
    can = {"R": 0, "L": 0}
    can_pos = {s: np.array(D @ Vector(L[f"canine_up.{s}"])) for s in "RL"}
    for i, v in enumerate(vs):
        for j, u in enumerate(us):
            o = c + right * u + up * v + fwd * 0.05
            hits = []
            for k, b in bvh.items():
                h = b.ray_cast(Vector(o), Vector(-fwd), 0.2)
                if h[0] is not None:
                    hits.append((h[3], k, h))
            if not hits:
                continue
            d, k, h = min(hits)
            p = np.array(h[0])
            if k == "tongue":
                cls[i, j] = 2
            elif k.startswith(f"{PREFIX}_Acc_Teeth"):
                cls[i, j] = 3
                if "_up" in k:            # upper canine = upper-tooth hit within 2.5 mm (sideways, face-on) of its landmark
                    for s_ in "RL":
                        if abs((p - can_pos[s_]) @ right) < 0.0025:
                            can[s_] += 1
            else:                                 # interior = a hit on the oral-cavity walls
                if oral[list(me.polygons[h[2]].vertices)].mean() > 0.5:
                    cls[i, j] = 1
    # rendered luminance over the opening: orthographic Cycles render aligned with the ray grid (fur on)
    cam_d = bpy.data.cameras.new("_mo_cam"); cam = bpy.data.objects.new("_mo_cam", cam_d); sc.collection.objects.link(cam)
    r_ = sc.render
    saved = (sc.camera, r_.engine, r_.resolution_x, r_.resolution_y, r_.resolution_percentage, r_.filepath, r_.use_border,
             sc.cycles.samples, r_.image_settings.file_format)
    import os, tempfile
    tmp = os.path.join(tempfile.gettempdir(), "_mouth_open_check.png")
    try:
        cam_d.type = 'ORTHO'; cam_d.ortho_scale = 2 * half + step; cam_d.clip_start = 0.001; cam_d.clip_end = 1.0
        cam.location = Vector(c + fwd * 0.08)
        m3 = np.stack([right, up, -fwd * -1], 1)    # camera looks along -Z: columns x=right, y=up, z=-(view dir)=fwd
        from mathutils import Matrix
        cam.rotation_euler = Matrix(m3.tolist()).to_euler()
        sc.camera = cam
        r_.engine = 'CYCLES'; sc.cycles.samples = 48; r_.resolution_x = len(us); r_.resolution_y = len(vs)
        r_.resolution_percentage = 100; r_.use_border = False; r_.filepath = tmp; r_.image_settings.file_format = 'PNG'
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(tmp)
        px = np.array(img.pixels[:], np.float32).reshape(len(vs), len(us), 4)[:, :, :3]   # row 0 = bottom = vs[0]
        bpy.data.images.remove(img)
    finally:
        (sc.camera, r_.engine, r_.resolution_x, r_.resolution_y, r_.resolution_percentage, r_.filepath, r_.use_border,
         sc.cycles.samples, r_.image_settings.file_format) = saved
        bpy.data.objects.remove(cam, do_unlink=True); bpy.data.cameras.remove(cam_d)
    lum = list(px[cls > 0].mean(1))
    if "DEBUG_PNG" in globals():                      # render | class mask side by side (rows flipped to image order)
        import numpy as _np
        m = _np.zeros_like(px); m[cls == 1] = (0.8, 0.2, 0.2); m[cls == 2] = (1.0, 0.6, 0.7); m[cls == 3] = (1, 1, 1)
        sheet = _np.concatenate([px, m], 1)
        im2 = bpy.data.images.new("_mo_dbg", sheet.shape[1], sheet.shape[0])
        im2.pixels.foreach_set(_np.concatenate([sheet, _np.ones(sheet.shape[:2] + (1,), _np.float32)], 2).ravel())
        im2.filepath_raw = DEBUG_PNG; im2.file_format = 'PNG'; im2.save(); bpy.data.images.remove(im2)
    open_ = cls > 0
    rows = np.nonzero(open_.any(1))[0]
    out = {"frame": int(fr), "jaw_deg": round(math.degrees(rig.pose.bones["jaw"].rotation_euler.x), 1)}
    if len(rows) > 4:
        h_ = rows.max() - rows.min()
        def width(fr_):
            r = rows.max() - int(fr_ * h_)          # rows run bottom (low v) -> top; 25% from the top
            cols = np.nonzero(open_[r])[0]
            return (cols.max() - cols.min() + 1) * step if len(cols) else 0.0
        w25, w75 = width(0.25), width(0.75)
        n = int(open_.sum())
        out.update({"opening_mm2": round(n * step * step * 1e6, 1), "width_top_mm": round(w25 * 1000, 1),
                    "width_low_mm": round(w75 * 1000, 1), "taper": round(w75 / max(w25, 1e-9), 3),
                    "tongue": round(float((cls == 2).sum()) / n, 3), "teeth": round(float((cls == 3).sum()) / n, 3),
                    "canines_up": can, "interior_lum": round(float(np.mean(lum)) if lum else 0.0, 3)})
        ok = (out["taper"] < 0.85 and out["tongue"] > 0.08 and min(can.values()) >= 10 and out["interior_lum"] > 0.35)
        out["PASS"] = bool(ok)
    else:
        out["PASS"] = False
        out["note"] = "no opening found"
    print(json.dumps(out))
    if "OUT_JSON" in globals():
        json.dump(out, open(OUT_JSON, "w"), indent=1)
finally:
    sc.frame_set(_mo_f0)
