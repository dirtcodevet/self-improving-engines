# Blender-side: the hair GROWTH DIRECTION at every skin point (person, 2026-10-17: every hair "comes from a surface on
# the cat, and grows in its own specified way"). Start from the anatomical tract prior (hair_tracts.py); where the
# frozen camera sees the skin clearly, turn it toward the fur direction measured on the photo (photo_flow.py: hair-scale
# detail only, orientation mod 180 - the sign comes from the prior); then smooth over the surface so measured and
# unseen regions join without seams. Groom reads it when engine/flags.json E3_hair_growth_field is true.
# Writes POINT attributes hair_dir (FLOAT_VECTOR, unit tangent) and hair_dir_w (photo weight 0..1).
# Globals: FLOW (photo_flow.npz), PREFIX, PHOTO_W (0.85), COH_MIN (0.30), COH_FULL (0.70), SMOOTH_IT (30),
# FUR_MIN (0.2), FURN_OUT (1.0, as groom), TURN_DEG (35: neighbours turned further than this barely smooth each other).
import bpy, json, time, importlib
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import hair_tracts as HT
importlib.reload(HT)

t0 = time.time()
PREFIX = globals().get("PREFIX", "Cat")
PHOTO_W = globals().get("PHOTO_W", 0.85)
COH_MIN, COH_FULL = globals().get("COH_MIN", 0.30), globals().get("COH_FULL", 0.70)
SMOOTH_IT = int(globals().get("SMOOTH_IT", 30))
FUR_MIN = globals().get("FUR_MIN", 0.2)
MAX_DEV = globals().get("MAX_DEV", 50.0)
FURN_OUT = globals().get("FURN_OUT", 1.0)
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
    get = lambda k, d: (lambda a: (me.attributes[k].data.foreach_get("value", a), a)[1])(np.empty(n, np.float32)) \
        if k in me.attributes else np.full(n, d, np.float32)
    zone, fden = np.round(get("zone", 0.0)), get("fur_dens", 1.0)
    L = json.load(open(skin["landmarks_file"]))["landmarks"]
    mw = np.array(skin.matrix_world)
    assert np.allclose(mw, np.eye(4), atol=1e-6), "hair_field expects the skin at identity transform"
    import os
    _tf = os.path.join(os.path.dirname(os.path.dirname(skin["landmarks_file"])), "hair_tracts.json")
    TRACTS = json.load(open(_tf)) if (os.path.exists(_tf) and globals().get("USE_TRACTS", True)) else None
    prior = HT.unit(HT.tract_field(co, nr, zone, L, furn_out=FURN_OUT, tracts=TRACTS))
    print("hair field: face prior =", "fitted source/sink tracts (" + _tf + ")" if TRACTS else "single radial source")

    # ---- photo fur orientation at each visible vertex
    F = np.load(FLOW)
    ang, coh = F["angle_deg"].astype(np.float32), F["coherence"].astype(np.float32)
    w_out = F["outline_w"].astype(np.float32) if "outline_w" in F else np.ones_like(coh)
    w_wh = F["whisker_w"].astype(np.float32) if "whisker_w" in F else np.ones_like(coh)
    H, W = ang.shape
    cam = sc.camera
    dg = bpy.context.evaluated_depsgraph_get()
    Pm = np.array(cam.calc_matrix_camera(dg, x=W, y=H, scale_x=sc.render.pixel_aspect_x, scale_y=sc.render.pixel_aspect_y))
    Vm = np.array(cam.matrix_world.inverted())
    M = Pm @ Vm

    def proj(p):
        h = np.c_[p, np.ones(len(p))] @ M.T
        ndc = h[:, :2] / h[:, 3:4]
        return np.stack([(ndc[:, 0] + 1) / 2 * W, (1 - (ndc[:, 1] + 1) / 2) * H], 1)   # x right, y down

    cpos = np.array(cam.matrix_world.translation)
    to_cam = cpos - co
    dist = np.linalg.norm(to_cam, axis=1)
    facing = (nr * to_cam).sum(1) / dist
    cand = np.where((facing > 0.25) & (fden > FUR_MIN))[0]
    bvh = BVHTree.FromObject(skin, dg)
    vis = np.zeros(n, bool)
    for i in cand:
        d_ = to_cam[i] / dist[i]
        if bvh.ray_cast(Vector(co[i] + d_ * 0.0006), Vector(d_), dist[i])[0] is None:
            vis[i] = True
    idx = np.where(vis)[0]
    uv = proj(co[idx])
    inside = (uv[:, 0] >= 0) & (uv[:, 0] < W - 1) & (uv[:, 1] >= 0) & (uv[:, 1] < H - 1)
    idx, uv = idx[inside], uv[inside]
    xi, yi = uv[:, 0].astype(int), uv[:, 1].astype(int)
    phi = np.radians(ang[yi, xi]); c_px = coh[yi, xi] * w_out[yi, xi]
    ear_ = np.isin(zone[idx], (6, 7, 8, 12))
    c_px = c_px * np.where(ear_, 1.0, w_wh[yi, xi])                 # ear hairs are ridges too, and they ARE fur
    # tangent basis and the image-space Jacobian of a small step along each basis vector
    nv_ = nr[idx]
    a_ = np.where(np.abs(nv_[:, :1]) < 0.9, np.array([[1.0, 0, 0]]), np.array([[0, 1.0, 0]]))
    t1 = HT.unit(np.cross(nv_, a_)); t2 = np.cross(nv_, t1)
    eps = 0.001
    J1 = (proj(co[idx] + eps * t1) - uv) / eps
    J2 = (proj(co[idx] + eps * t2) - uv) / eps
    u = np.stack([np.cos(phi), np.sin(phi)], 1)
    det = J1[:, 0] * J2[:, 1] - J2[:, 0] * J1[:, 1]
    ok = np.abs(det) > 1e-9
    a1 = np.where(ok, (u[:, 0] * J2[:, 1] - J2[:, 0] * u[:, 1]) / np.where(ok, det, 1), 0)
    a2 = np.where(ok, (J1[:, 0] * u[:, 1] - u[:, 0] * J1[:, 1]) / np.where(ok, det, 1), 0)
    tdir = HT.unit(a1[:, None] * t1 + a2[:, None] * t2)
    flip = (tdir * prior[idx]).sum(1) < 0                             # orientation only: the prior gives the sign
    tdir[flip] *= -1
    # structure first (person: "the direction is guided by the structures of the cat"): a measurement may turn the
    # anatomical direction, but one that disagrees by more than MAX_DEV is set aside as doubtful (flagged in hair_dir_w)
    dev = np.degrees(np.arccos(np.clip((tdir * prior[idx]).sum(1), -1, 1)))
    w_agree = HT.ss(MAX_DEV + 15, MAX_DEV - 15, dev)
    w = np.zeros(n)
    w[idx] = PHOTO_W * HT.ss(COH_MIN, COH_FULL, c_px) * HT.ss(0.25, 0.6, facing[idx]) * ok * w_agree
    doubt = int(((HT.ss(COH_MIN, COH_FULL, c_px) > 0.5) & (w_agree < 0.5)).sum())
    if globals().get("EXPORT"):                                    # trusted measurements for fitting the tract model
        wm = PHOTO_W * HT.ss(COH_MIN, COH_FULL, c_px) * HT.ss(0.25, 0.6, facing[idx]) * ok
        np.savez(EXPORT, P=co[idx], N=nr[idx], T=tdir, w=wm, zone=zone[idx], head=np.array(L["head"]),
                 head_R=np.array(L["head_R"]), eyeR=np.array(L["eye.R"]), eyeL=np.array(L["eye.L"]))
    # the PERSON's marked directions (engine-grounding G12; the human supplies facts the input does not hold): where
    # the photo is unreliable - the outer cheeks, where fur turns down toward the jaw - their strokes are measurements
    # with the highest trust, spread a few pixels around each stroke; the turn-preserving smoothing carries them on
    n_marked = 0
    if globals().get("MARKS"):
        segs = json.load(open(MARKS))["segments"]
        mxy = np.array([[s_["x"], s_["y"]] for s_ in segs]); mang = np.radians([s_["angle_deg"] for s_ in segs])
        dd = np.hypot(uv[:, None, 0] - mxy[None, :, 0], uv[:, None, 1] - mxy[None, :, 1])
        jm, dmin = dd.argmin(1), dd.min(1)
        MARK_R, MARK_W = globals().get("MARK_R", 7.0), globals().get("MARK_W", 0.95)
        near = dmin < MARK_R
        um = np.stack([np.cos(mang[jm]), np.sin(mang[jm])], 1)
        b1 = np.where(ok, (um[:, 0] * J2[:, 1] - J2[:, 0] * um[:, 1]) / np.where(ok, det, 1), 0)
        b2 = np.where(ok, (J1[:, 0] * um[:, 1] - um[:, 0] * J1[:, 1]) / np.where(ok, det, 1), 0)
        tm = HT.unit(b1[:, None] * t1 + b2[:, None] * t2)
        tm[(tm * prior[idx]).sum(1) < 0] *= -1
        wm_ = MARK_W * HT.ss(MARK_R, 0.4 * MARK_R, dmin) * near * ok
        take = wm_ > w[idx]
        tdir = np.where(take[:, None], tm, tdir)
        w[idx] = np.where(take, wm_, w[idx])
        n_marked = int(take.sum())
        print(f"hair field: person's marks {len(segs)} -> {n_marked} skin points take their direction")
    meas = prior.copy(); meas[idx] = tdir
    d0 = HT.unit(prior * (1 - w)[:, None] + meas * w[:, None])

    # ---- smooth over the surface: measured points stay near their measurement, the rest follow their neighbours.
    # Direction-preserving: a neighbour pointing a very different way gets little say (weight exp(-(angle/TURN)^2)),
    # so real direction changes - turns, partings, whorls - survive instead of being averaged away (person: the
    # gaps in the photo's flow "are important because they differ from the surrounding fur on direction").
    ev = np.empty(len(me.edges) * 2, np.int32); me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
    deg = np.bincount(ev[:, 0], minlength=n) + np.bincount(ev[:, 1], minlength=n)
    d = d0.copy()
    TURN = np.radians(globals().get("TURN_DEG", 35.0))
    for _ in range(SMOOTH_IT):
        cosang = np.clip((d[ev[:, 0]] * d[ev[:, 1]]).sum(1), -1, 1)
        we_ = np.exp(-(np.arccos(cosang) / TURN) ** 2)
        acc = np.stack([np.bincount(ev[:, 0], weights=we_ * d[ev[:, 1], k], minlength=n)
                        + np.bincount(ev[:, 1], weights=we_ * d[ev[:, 0], k], minlength=n) for k in range(3)], 1)
        wsum = np.bincount(ev[:, 0], weights=we_, minlength=n) + np.bincount(ev[:, 1], weights=we_, minlength=n)
        avg = np.where(wsum[:, None] > 1e-6, acc / np.maximum(wsum, 1e-6)[:, None], d)
        d = HT.unit(d0 * (0.6 * w)[:, None] + avg * (1 - 0.6 * w)[:, None])
        d = HT.unit(d - (d * nr).sum(1, keepdims=True) * nr)
    for name, typ, arr, comp in (("hair_dir", 'FLOAT_VECTOR', d, "vector"), ("hair_dir_w", 'FLOAT', w, "value")):
        if name in me.attributes:
            me.attributes.remove(me.attributes[name])
        me.attributes.new(name, typ, 'POINT').data.foreach_set(comp, np.asarray(arr, np.float32).ravel())
    turn = np.degrees(np.arccos(np.clip((d * prior).sum(1), -1, 1)))
    strong = w > 0.4
    zs = {int(z_): f"{np.median(turn[strong & (zone == z_)]):.0f}" for z_ in np.unique(zone[strong])}
    print(f"hair field: clear measurements set aside as disagreeing with the structure prior: {doubt}")
    print(f"hair field: visible {vis.sum()}  photo-weighted (>0.4) {strong.sum()}  median turn from the prior "
          f"{np.median(turn[strong]):.0f} deg; by zone {zs}  {time.time() - t0:.1f}s")
finally:
    if rig:
        rig.data.pose_position = pose_saved
