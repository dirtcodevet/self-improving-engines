# Blender-side: capture the coat MARKINGS from the reference photo instead of inventing them.
# For skin vertices visible to the frozen camera (ray-tested, facing it), sample the photo (blurred) and convert
# colour to a marking strength with a hue test that separates tint from shading: markings are purple
# ((R+B)/2 - G large) while shadows on white fur are neutral grey. Unseen head vertices take the value of their
# mirror image (head-local x -> -x); unseen tail vertices take the value at the same arc length along the tail.
# Then: coat = mix(white, marking colour, strength) wherever the fur region allows (not nose/lips/inner ears).
# Globals: PHOTO (path), MARK_RGB (sRGB 0..1 marking colour), PREFIX. Reads/writes <PREFIX>_Skin 'coat'.
import bpy, json
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view

PREFIX = globals().get("PREFIX", "Cat")
MARK = np.array(globals().get("MARK_RGB", (0.66, 0.56, 0.68))) ** 2.2
DARK = np.array(globals().get("MARK_DARK_RGB", (0.52, 0.42, 0.56))) ** 2.2
# optional per-region palette for the tail (v27c): the tail rings are greyer and darker than the face markings
# (photo, strong-marking pixels: median sRGB 0.60/0.52/0.58); with the face palette they rendered washed out
TMARK = np.array(globals().get("TAIL_MARK_RGB", globals().get("MARK_RGB", (0.66, 0.56, 0.68)))) ** 2.2
TDARK = np.array(globals().get("TAIL_DARK_RGB", globals().get("MARK_DARK_RGB", (0.52, 0.42, 0.56)))) ** 2.2
sc = bpy.context.scene
skin = bpy.data.objects[f"{PREFIX}_Skin"]
rig = bpy.data.objects.get(f"{PREFIX}_Rig")
pose_saved = rig.data.pose_position if rig else None
try:
    if rig:
        rig.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    me = skin.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3).astype(np.float64)
    nr = np.empty(n * 3, np.float32); me.vertices.foreach_get("normal", nr); nr = nr.reshape(-1, 3).astype(np.float64)
    J = json.load(open(skin["landmarks_file"]))
    L, Pm = J["landmarks"], J["params"]
    # photo, lightly blurred (fur noise)
    img = bpy.data.images.load(PHOTO, check_existing=True)
    W, H = img.size
    px = np.array(img.pixels[:], np.float32).reshape(H, W, 4)[::-1, :, :3]    # top row first
    # Blender's bundled Python has no scipy: separable box blur (x2 ~ gaussian) in numpy
    def _box(a, r=2):
        k = 2 * r + 1
        c = np.cumsum(np.pad(a, ((r + 1, r), (0, 0), (0, 0)), mode="edge"), axis=0)
        a = (c[k:] - c[:-k]) / k
        c = np.cumsum(np.pad(a, ((0, 0), (r + 1, r), (0, 0)), mode="edge"), axis=1)
        return (c[:, k:] - c[:, :-k]) / k
    px = _box(px.astype(np.float64), r=1)   # v22: lighter blur (stripes read blobby at r=2 x2)
    cam = sc.camera
    cpos = np.array(cam.matrix_world.translation)
    bvh = BVHTree.FromObject(skin, bpy.context.evaluated_depsgraph_get())
    vis = np.zeros(n, bool)
    uv = np.zeros((n, 2))
    for i in range(n):
        p = co[i]
        to_cam = cpos - p
        dist = np.linalg.norm(to_cam)
        if np.dot(nr[i], to_cam / dist) < 0.25:
            continue
        hit = bvh.ray_cast(Vector(p + to_cam / dist * 0.0006), Vector(to_cam / dist), dist)
        if hit[0] is not None:
            continue
        v = world_to_camera_view(sc, cam, Vector(p))
        uv[i] = (v.x * (W - 1), (1 - v.y) * (H - 1))
        vis[i] = 0 <= uv[i, 0] < W and 0 <= uv[i, 1] < H
    xi, yi = uv[vis, 0].astype(int), uv[vis, 1].astype(int)
    rgb = px[yi, xi] * 255.0
    hue = (rgb[:, 0] + rgb[:, 2]) / 2 - rgb[:, 1]
    lum = rgb.mean(1)
    m_vis = np.clip((hue - 5.0) / 17.0, 0, 1) * np.clip((246 - lum) / 70.0, 0.25, 1.0)
    # v37: PINK is not a marking. Lilac marks have R ~ B (photo forehead stripes R-B 1..5); bare pink skin has R >> B
    # (nose leather 46-50, philtrum 25-28) but scores HIGHER on the purple hue test -> painted lilac under the nose
    m_vis *= np.clip(1 - (rgb[:, 0] - rgb[:, 2] - 12.0) / 16.0, 0, 1)
    m = np.full(n, np.nan)
    m[vis] = m_vis
    # mirror fill for the head
    R = np.array(L["head_R"]); H0 = np.array(L["head"]); hs = Pm["head_scale"]
    hl = ((co - H0) @ R) / hs
    head = (np.linalg.norm(hl - np.array([0, -0.005, 0.0]), axis=1) < 0.075) & (hl[:, 2] > -0.06)
    from mathutils.kdtree import KDTree   # no scipy inside Blender
    hv = head & vis
    hv_idx = np.nonzero(hv)[0]
    kd = KDTree(len(hv_idx))
    for ii, vi in enumerate(hv_idx):
        kd.insert(hl[vi], ii)
    kd.balance()
    need = head & ~vis
    fill = np.full(int(need.sum()), np.nan)
    for ii, q in enumerate(hl[need] * np.array([-1, 1, 1])):
        _, jj, dd = kd.find(q)
        if dd < 0.004:
            fill[ii] = m[hv_idx[jj]]
    m[np.nonzero(need)[0]] = fill
    # tail: by arc length along the tail polyline
    T = np.array(L["tail"])
    seg = np.diff(T, axis=0); sl = np.linalg.norm(seg, axis=1); cum = np.concatenate([[0], np.cumsum(sl)])
    best = np.full(n, 9.0); s_ = np.zeros(n)
    for k in range(len(seg)):
        t = np.clip(((co - T[k]) @ seg[k]) / (sl[k] ** 2), 0, 1)
        dd = np.linalg.norm(co - (T[k] + t[:, None] * seg[k]), axis=1)
        b = dd < best
        best = np.where(b, dd, best); s_ = np.where(b, cum[k] + t * sl[k], s_)
    tail = (best < 0.016) & (co[:, 1] > 0.12)
    tv = tail & vis
    if tv.sum() > 50:
        bins = np.linspace(0, cum[-1], 60)
        idx = np.digitize(s_[tv], bins)
        prof = np.array([np.nanmedian(m[tv][idx == b]) if (idx == b).any() else np.nan for b in range(len(bins) + 1)])
        good = ~np.isnan(prof)
        prof = np.interp(np.arange(len(prof)), np.nonzero(good)[0], prof[good])
        ti = np.nonzero(tail & ~vis)[0]
        m[ti] = prof[np.digitize(s_[ti], bins)]
        # v27d: normalise the tail's contrast by its own p90. The photo's tail is softer/in shade, so its strengths
        # peak at ~0.65 (face ~1.0); through the white/palette blend the darkest ring rendered sRGB 0.76 vs the
        # photo's 0.60 - rings washed out. Ring centres now reach the measured ring colour (TAIL_DARK_RGB).
        p90 = float(np.nanpercentile(m[tv], 90))
        tail_only = tail & ~head
        m[tail_only] = np.clip(m[tail_only] / max(p90, 0.3), 0, 1)
        print(f"tail: visible {int(tv.sum())}/{int(tail.sum())}  visible m p50/p90 {np.nanpercentile(m[tv], 50):.2f}/"
              f"{p90:.2f} (normalised by p90)  profile min/max {np.nanmin(prof):.2f}/{np.nanmax(prof):.2f}")
    # apply where fur colour is free (not nose / lips / mouth / inner ear / pads): use the existing fur density map
    fden = np.empty(n, np.float32); me.attributes["fur_dens"].data.foreach_get("value", fden)
    region = (head | tail) & (fden > 0.5) & ~np.isnan(m)
    if "zone" in me.attributes:   # v37: never inside the ears (the photo's grey-pink ear interior passed the hue test)
        zn = np.empty(n, np.float32); me.attributes["zone"].data.foreach_get("value", zn)
        region &= ~np.isin(np.round(zn), (6, 7, 8, 12))
    coat = np.empty(n * 4, np.float32); me.color_attributes["coat"].data.foreach_get("color", coat); coat = coat.reshape(-1, 4)
    base = coat[:, :3].copy()
    white = np.array((0.95, 0.94, 0.93)) ** 2.2
    mm = np.clip(m[region], 0, 1)[:, None]
    is_tail = (tail & ~head)[region][:, None]
    mk_, dk_ = np.where(is_tail, TMARK, MARK), np.where(is_tail, TDARK, DARK)
    tgt = white * (1 - mm) + (mk_ * (1 - mm) + dk_ * mm) * mm     # stronger = darker
    coat[region, :3] = tgt
    me.color_attributes["coat"].data.foreach_set("color", coat.ravel())
    print(f"photo markings: visible {int(vis.sum())}  head mirrored {int(np.isfinite(fill).sum())}  tail {int(tail.sum())}  "
          f"applied {int(region.sum())}  strong(>0.5) {int((m[region] > 0.5).sum())}")
finally:
    if rig:
        rig.data.pose_position = pose_saved
