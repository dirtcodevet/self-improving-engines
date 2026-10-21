# Blender-side procedural groom for a quadruped: hair curves on <PREFIX>_Skin, in TWO LAYERS.
# Reads skin point attributes fur_len, fur_dens, coat (+ UVs) and the landmarks (nose, head, tail, paws); optional
# per-zone attributes written by the case coat script: zone, hair_lift (deg), hair_clump (0..1), hair_rscale.
# Layers (real coats: long sparse guard hairs carry the colour and the visible texture over a dense, short, crimped,
# paler undercoat that gives volume):
#   guard  N_GUARD strands, full fur_len, root lift / clumping / thickness from the zone attributes
#   under  N_UNDER strands, UNDER_LEN x fur_len, erect and wavy, thin, hardly clumped, colour mixed toward white
#   furn   N_FURN strands on the ear FURNISHINGS only (zone 12): long, fanned up and out, tufted, in the zone's hair
#          colour (attribute hair_tint: rgb + weight; a hair colour distinct from the skin under it)
# Comb field: face hair flows out from the nose, body hair back and down the flanks, legs down, tail toward its tip,
# ear backs and rims toward the tips, ear furnishings up and outward, eye surround radially away from the eyes.
# Creates <PREFIX>_Fur (Curves, both layers, curve attribute 'layer' 0/1) attached to the skin (surface +
# surface_uv_coordinate) so it follows the rig.
# Globals: N_GUARD (320000), N_UNDER (300000), UNDER_LEN (0.45), K (points/strand, 5), ROOT_R/TIP_R (m), SEED,
# VIEW_FRACTION, CLUMP (guard clumping when the skin has no hair_clump attribute).
import bpy, json, time, os, importlib
import numpy as np
from mathutils.kdtree import KDTree
import hair_tracts as HT
importlib.reload(HT)

t0 = time.time()
PREFIX = globals().get("PREFIX", "Cat")
N_GUARD = int(globals().get("N_GUARD", 320000))
N_UNDER = int(globals().get("N_UNDER", 300000))
# furnishing defaults from the v37 ear lab (engine/review/ear_lab.sh, variants a-n scored with compare_regions):
# long, lying low in the cup, swept ~45 deg up-and-out, in thin tufts, clipped to the pinna outline
N_FURN = int(globals().get("N_FURN", 26000))
FURN_LEN, FURN_R, FURN_CLUMP = globals().get("FURN_LEN", 1.0), globals().get("FURN_R", 1.3), globals().get("FURN_CLUMP", 0.95)
FURN_LIFT = globals().get("FURN_LIFT", (6, 14))    # root lift range (deg); the tip lies at half of it
FURN_OUT = globals().get("FURN_OUT", 1.0)          # comb inside the ear: tip-ward + FURN_OUT x outward
FURN_DIV = int(globals().get("FURN_DIV", 60))      # strands per tuft
UNDER_LEN = globals().get("UNDER_LEN", 0.45)
K = int(globals().get("K", 5))
ROOT_R = globals().get("ROOT_R", 0.000045)
TIP_R = globals().get("TIP_R", 0.000008)
SEED = globals().get("SEED", 11)
VIEW_FRACTION = globals().get("VIEW_FRACTION", 0.25)
CLUMP = globals().get("CLUMP", 0.55)
rng = np.random.default_rng(SEED)
# trial E3 (engine/flags.json): strands follow the skin's hair GROWTH FIELD (hair_field.py: tract prior turned toward
# the photo's measured fur direction) instead of the tract prior alone. Off -> identical to the pre-E3 groom.
_fl = os.path.join(os.path.dirname(os.path.dirname(HT.__file__)), "flags.json")
_flags = json.load(open(_fl)) if os.path.exists(_fl) else {}
USE_HAIR_FIELD = globals().get("USE_HAIR_FIELD", _flags.get("E3_hair_growth_field", False))

skin = bpy.data.objects[f"{PREFIX}_Skin"]
me = skin.data
J = json.load(open(skin["landmarks_file"]))
L = J["landmarks"]

# ---- UV map (needed so strands stay attached under deformation)
if not me.uv_layers:
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = skin
    skin.select_set(True)
    with bpy.context.temp_override(object=skin, active_object=skin, selected_objects=[skin], selected_editable_objects=[skin]):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.002)
        bpy.ops.object.mode_set(mode='OBJECT')
    print("uv unwrapped", f"{time.time()-t0:.1f}s")

me.calc_loop_triangles()
nt = len(me.loop_triangles)
tv = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get("vertices", tv); tv = tv.reshape(-1, 3)
tl = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get("loops", tl); tl = tl.reshape(-1, 3)
nv = len(me.vertices)
co = np.empty(nv * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3).astype(np.float64)
vn = np.empty(nv * 3, np.float32); me.vertices.foreach_get("normal", vn); vn = vn.reshape(-1, 3).astype(np.float64)


def pattr(name, default=None):
    if name not in me.attributes:
        return np.full(nv, default, np.float32)
    buf = np.empty(nv, np.float32)
    me.attributes[name].data.foreach_get("value", buf)
    return buf


flen, fden = pattr("fur_len"), pattr("fur_dens")
zone_v = pattr("zone", 0.0)
lift_v, clump_v, rsc_v = pattr("hair_lift", 34.0), pattr("hair_clump", CLUMP), pattr("hair_rscale", 1.0)
coat = np.empty(nv * 4, np.float32); me.color_attributes["coat"].data.foreach_get("color", coat); coat = coat.reshape(-1, 4)
uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers.active.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
hdir = None
if USE_HAIR_FIELD:
    assert "hair_dir" in me.attributes, "E3 on but the skin has no hair_dir (run hair_field.py after coat)"
    hdir = np.empty(nv * 3, np.float32); me.attributes["hair_dir"].data.foreach_get("vector", hdir); hdir = hdir.reshape(-1, 3)
tint = np.zeros((nv, 4), np.float32)
if "hair_tint" in me.color_attributes:
    me.color_attributes["hair_tint"].data.foreach_get("color", tint.ravel())
A, B, C = co[tv[:, 0]], co[tv[:, 1]], co[tv[:, 2]]
area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
# undercoat: barely any on the ear interior skin and under the furnishings (pink skin shows through in the photo)
under_w = np.ones(nv)
under_w[np.isin(np.round(zone_v), (6, 12))] = 0.25


def roots(n, vweight):
    """Sample n roots by area x per-vertex weight; return per-strand interpolated attributes."""
    w = area * vweight[tv].mean(1)
    tri = rng.choice(nt, size=n, p=w / w.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s1 = np.sqrt(r1)
    bc = np.stack([1 - s1, s1 * (1 - r2), s1 * r2], 1)
    vt = tv[tri]
    Nn = (bc[:, :, None] * vn[vt]).sum(1); Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
    lerp = lambda a: (bc * a[vt]).sum(1)
    return dict(P=(bc[:, :, None] * co[vt]).sum(1), Nn=Nn, len=lerp(flen), lift=lerp(lift_v), clump=lerp(clump_v),
                rsc=lerp(rsc_v), zone=np.round(zone_v[vt[np.arange(n), bc.argmax(1)]]),
                col=(bc[:, :, None] * coat[vt]).sum(1), UV=(bc[:, :, None] * uv[tl[tri]]).sum(1),
                tint=(bc[:, :, None] * tint[vt]).sum(1),
                hdir=(bc[:, :, None] * hdir[vt]).sum(1) if hdir is not None else None)


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


def ss(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


Hc, nose = np.array(L["head"]), np.array(L["nose"])
Rh = np.array(L["head_R"])


def comb_field(P, Nn, zone, hd=None):
    N = len(P)
    if hd is not None:                                               # E3: the growth field at each root
        comb = hd - (hd * Nn).sum(1, keepdims=True) * Nn
    else:
        comb = HT.tract_field(P, Nn, zone, L, furn_out=FURN_OUT)
    # per-strand jitter (same random draws in both modes)
    comb = unit(comb + 0.25 * unit(rng.normal(size=(N, 3))) * 0.6)
    return unit(comb - (comb * Nn).sum(1, keepdims=True) * Nn)


def grow(R, lenr, lift0_deg, lift1_deg, wob_s, clump_s, clump_div=18):
    """Strands lift off the skin at lift0, lie down to lift1 toward the tip, then clump toward nearby guides."""
    N = len(lenr)
    comb = comb_field(R["P"], R["Nn"], R["zone"], R.get("hdir"))
    lift0, lift1 = np.radians(lift0_deg), np.radians(lift1_deg)
    pts = np.zeros((N, K, 3))
    pts[:, 0] = R["P"] - R["Nn"] * 0.0002
    seglen = (lenr / (K - 1))[:, None]
    wob = rng.normal(size=(N, 3)) * wob_s
    for k in range(1, K):
        f = (k - 1) / max(K - 2, 1)
        th = lift0 * (1 - f) + lift1 * f
        sgn = 1 if k % 2 else -1                                     # alternate the wobble: crimp, not a bend
        d = unit(np.cos(th)[:, None] * comb + np.sin(th)[:, None] * R["Nn"] + wob * (f if wob_s < 0.2 else sgn))
        pts[:, k] = pts[:, k - 1] + d * seglen
    if np.max(clump_s) > 0:
        ng_ = max(N // clump_div, 1)                                # strands per tuft ~ clump_div
        gidx = rng.choice(N, ng_, replace=False)
        kd = KDTree(ng_)
        for i, gi in enumerate(gidx):
            kd.insert(R["P"][gi], i)
        kd.balance()
        near = np.array([kd.find(tuple(p))[1] for p in R["P"]])
        gp = pts[gidx[near]]
        gp = gp - gp[:, :1] + pts[:, :1]                             # guide shape re-rooted at this strand
        f = (np.linspace(0, 1, K) ** 1.3)[None, :, None] * clump_s[:, None, None]
        pts = pts * (1 - f) + gp * f
    return pts


def ear_clip(pts, zone, P):
    """Ear-interior strands end inside their own pinna: shrink each strand (about its root) to its last point inside
    the outline (outer edge 0.9 x the pinna half-width of sdf_core.pinna, below 95 % of the height). Lab v37 i-m:
    furnishings swept up-and-out piled up as a white fringe outside the outer edge whatever length rule coat used."""
    sel = np.isin(zone, (6, 12))
    if not sel.any() or "ear_w" not in L:
        return pts
    wb = L["ear_w"]
    for sd in "RL":
        eb, et = np.array(L[f"ear_base.{sd}"]), np.array(L[f"ear_tip.{sd}"])
        if f"ear_u.{sd}" not in L:
            continue
        ax = unit(et - eb); Hh = np.linalg.norm(et - eb)
        eu = np.array(L[f"ear_u.{sd}"]); eu = unit(eu - (eu @ ax) * ax)
        near = sel & (np.linalg.norm(P - eb, axis=1) < 1.3 * Hh) & ((P - eb) @ ax > -0.003)
        if not near.any():
            continue
        q = pts[near] - eb
        t = (q @ ax) / Hh; lat = q @ eu
        tc = np.clip(t, 0, 1)
        hw_out = wb / 2 * (1 - tc) + 0.12 * wb * 4 * tc * (1 - tc)
        bad = (lat > 0.9 * hw_out) | (t > 0.95)
        bad[:, 0] = False
        first = np.where(bad.any(1), bad.argmax(1), K)
        f = np.clip((first - 1) / (K - 1), 0.12, 1.0)
        root = pts[near][:, :1]
        pts[near] = root + (pts[near] - root) * f[:, None, None]
    return pts


# ---- guard layer: zone-driven lift / clumping / thickness
G = roots(N_GUARD, fden)
g_len = G["len"] * rng.uniform(0.80, 1.2, N_GUARD)
g_lift0 = np.clip(G["lift"] + rng.uniform(-6, 6, N_GUARD), 3, 75)
g_lift1 = rng.uniform(4, 14, N_GUARD) * np.clip(G["lift"] / 34.0, 0.3, 1.6)
g_lift1 = np.where(G["zone"] == 12, g_lift0 * 0.5, g_lift1)        # furnishings stay fanned out to the tip
g_pts = grow(G, g_len, g_lift0, g_lift1, 0.12, G["clump"] * rng.uniform(0.6, 1.0, N_GUARD))
g_pts = ear_clip(g_pts, G["zone"], G["P"])
g_rad = np.linspace(ROOT_R, TIP_R, K)[None, :] * (G["rsc"] * rng.uniform(0.85, 1.15, N_GUARD))[:, None]
print(f"guard layer {N_GUARD}  {time.time()-t0:.1f}s")
# ---- undercoat: dense, short, erect, crimped, thin, paler
U = roots(N_UNDER, fden * under_w)
u_len = np.maximum(U["len"] * UNDER_LEN * rng.uniform(0.8, 1.1, N_UNDER), 0.0006)
u_pts = grow(U, u_len, rng.uniform(35, 55, N_UNDER), rng.uniform(15, 30, N_UNDER), 0.35,
             0.12 * rng.uniform(0.5, 1.0, N_UNDER))
u_rad = np.linspace(ROOT_R, TIP_R, K)[None, :] * 0.55 * np.ones((N_UNDER, 1))
U["col"][:, :3] = U["col"][:, :3] * 0.7 + 0.3 * np.array([0.86, 0.85, 0.87])
print(f"undercoat {N_UNDER}  {time.time()-t0:.1f}s")

# ---- ear furnishings: their own hair type (long, fanned, tufted, pale) - the person's "different types of hair"
furn_w = fden * (np.round(zone_v) == 12)
if N_FURN > 0 and furn_w.sum() > 0:
    F = roots(N_FURN, furn_w)
    f_len = F["len"] * FURN_LEN * rng.uniform(0.85, 1.15, N_FURN)
    f_l0 = rng.uniform(*FURN_LIFT, N_FURN)
    f_pts = grow(F, f_len, f_l0, f_l0 * 0.5, 0.10, FURN_CLUMP * rng.uniform(0.8, 1.0, N_FURN), FURN_DIV)
    f_pts = ear_clip(f_pts, F["zone"], F["P"])
    f_len = np.linalg.norm(np.diff(f_pts, axis=1), axis=2).sum(1)
    f_rad = np.linspace(ROOT_R, TIP_R, K)[None, :] * FURN_R * np.ones((N_FURN, 1))
    F["tint"][:, 3] = 1.0
    print(f"furnishings {N_FURN}  len {f_len.mean()*1000:.1f} mm  {time.time()-t0:.1f}s")
else:
    F = dict(col=np.zeros((0, 4)), UV=np.zeros((0, 2)), tint=np.zeros((0, 4)), zone=np.zeros(0))
    f_pts, f_rad, f_len = np.zeros((0, K, 3)), np.zeros((0, K)), np.zeros(0)
nF = len(f_len)

pts = np.concatenate([g_pts, u_pts, f_pts]); rad = np.concatenate([g_rad, u_rad, f_rad])
col = np.concatenate([G["col"], U["col"], F["col"]]); UV = np.concatenate([G["UV"], U["UV"], F["UV"]])
layer = np.concatenate([np.zeros(N_GUARD), np.ones(N_UNDER), np.full(nF, 2.0)])
lenr = np.concatenate([g_len, u_len, f_len])
tw = np.concatenate([G["tint"], U["tint"] * [1, 1, 1, 0.5], F["tint"]])   # undercoat takes half the hair colour
N = len(pts)

# colour from where the strand is SEEN: fur lies downstream of its root, so a pattern painted on the skin
# would appear shifted (face markings vanished under white strands rooted nearer the nose). Sample the coat
# at the surface under the root and under the tip; interpolate along the strand.
kdv = KDTree(nv)
for i, p_ in enumerate(co):
    kdv.insert(p_, i)
kdv.balance()
tip_idx = np.array([kdv.find(tuple(p_))[1] for p_ in pts[:, -1]])
col_tip = coat[tip_idx].copy()
col_tip[N_GUARD:N_GUARD + N_UNDER, :3] = col_tip[N_GUARD:N_GUARD + N_UNDER, :3] * 0.7 + 0.3 * np.array([0.86, 0.85, 0.87])
ramp = np.linspace(0, 1, K)[None, :, None] ** 0.7
pcol = col[:, None, :] * (1 - ramp) + col_tip[:, None, :] * ramp
w_ = np.clip(tw[:, 3], 0, 1)[:, None, None]                       # zone hair colour over the skin-sampled colour
pcol[:, :, :3] = pcol[:, :, :3] * (1 - w_) + tw[:, None, :3] * w_

# ---- build the Curves object
name = f"{PREFIX}_Fur"
old = bpy.data.objects.get(name)
if old:
    od = old.data
    bpy.data.objects.remove(old, do_unlink=True)
    bpy.data.hair_curves.remove(od)
cd = bpy.data.hair_curves.new(name)
cd.add_curves([K] * N)
cd.attributes["position"].data.foreach_set("vector", pts.astype(np.float32).ravel())
ra = cd.attributes.get("radius") or cd.attributes.new("radius", 'FLOAT', 'POINT')
ra.data.foreach_set("value", rad.astype(np.float32).ravel())
ca = cd.attributes.new("coat", 'FLOAT_COLOR', 'POINT')
ca.data.foreach_set("color", pcol.astype(np.float32).ravel())
la = cd.attributes.new("layer", 'FLOAT', 'CURVE')
la.data.foreach_set("value", layer.astype(np.float32))
su = cd.attributes.get("surface_uv_coordinate") or cd.attributes.new("surface_uv_coordinate", 'FLOAT2', 'CURVE')
su.data.foreach_set("vector", UV.astype(np.float32).ravel())
cd.materials.append(bpy.data.materials["M_Fur"])
ob = bpy.data.objects.new(name, cd)
skin.users_collection[0].objects.link(ob)
cd.surface = skin
cd.surface_uv_map = me.uv_layers.active.name

# viewport thinning (render keeps all strands)
# always rebuild generated datablocks: a failed earlier run left this group half-built (no links) and
# reusing it silently deleted every strand
old_ng = bpy.data.node_groups.get("FurViewportThin")
if old_ng is not None:
    bpy.data.node_groups.remove(old_ng)
if True:
    ng = bpy.data.node_groups.new("FurViewportThin", 'GeometryNodeTree')
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    fr = ng.interface.new_socket("Fraction", in_out='INPUT', socket_type='NodeSocketFloat')
    fr.default_value, fr.min_value, fr.max_value = 0.25, 0.0, 1.0
    gi, go = ng.nodes.new("NodeGroupInput"), ng.nodes.new("NodeGroupOutput")
    isv = ng.nodes.new("GeometryNodeIsViewport")
    rnd = ng.nodes.new("FunctionNodeRandomValue")
    cmp = ng.nodes.new("FunctionNodeCompare"); cmp.data_type = 'FLOAT'; cmp.operation = 'GREATER_THAN'
    band = ng.nodes.new("FunctionNodeBooleanMath"); band.operation = 'AND'
    dele = ng.nodes.new("GeometryNodeDeleteGeometry"); dele.domain = 'CURVE'
    rnd.data_type = 'FLOAT'
    # Blender 5 nodes expose type-dependent sockets: pick by enabled + type, never by index
    sock = lambda col, typ: [x for x in col if x.enabled and x.type == typ]
    ng.links.new(sock(rnd.outputs, 'VALUE')[0], sock(cmp.inputs, 'VALUE')[0])
    ng.links.new(gi.outputs["Fraction"], sock(cmp.inputs, 'VALUE')[1])
    ng.links.new(isv.outputs[0], band.inputs[0]); ng.links.new(cmp.outputs[0], band.inputs[1])
    ng.links.new(gi.outputs["Geometry"], dele.inputs["Geometry"]); ng.links.new(band.outputs[0], dele.inputs["Selection"])
    ng.links.new(dele.outputs[0], go.inputs["Geometry"])
md = ob.modifiers.new("viewport_thin", 'NODES')
md.node_group = ng
dg = bpy.context.evaluated_depsgraph_get()
ev_n = len(ob.evaluated_get(dg).data.curves)
assert ev_n > 0.1 * N * VIEW_FRACTION, f"viewport thinning produced {ev_n} curves"
for it in ng.interface.items_tree:  # Blender 5: modifier inputs are not ID props -> set the socket default
    if getattr(it, "name", "") == "Fraction":
        it.default_value = VIEW_FRACTION
zs = np.concatenate([G["zone"], U["zone"], F["zone"]])
zl = {int(k_): f"{(zs == k_).sum()}" for k_ in np.unique(zs)}
print(f"groom: {N_GUARD} guard + {N_UNDER} under + {nF} furnishings x {K} pts  guard len {g_len.mean()*1000:.1f} mm  "
      f"under {u_len.mean()*1000:.1f} mm  strands per zone {zl}  {time.time()-t0:.1f}s")
