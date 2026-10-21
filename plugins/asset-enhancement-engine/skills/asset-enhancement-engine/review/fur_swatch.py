# FUR SWATCH TEST (run in a separate background Blender; never touches the cat scene):
#   blender -b --factory-startup --python fur_swatch.py -- <ours|blender> <out_dir> [density_scale]
# One patch of skin at REAL scale (a gently curved 8 x 8 cm "flank"), the same camera, light, hair material and
# render settings for both grooms, so only the groom differs (engine-grounding: tools are chosen by result):
#   ours    - our generator, upgraded: guard / awn / down layers at real density, locks with gaps, 3-D strands
#   blender - the same guide strands, with Blender's procedural hair tools making the detail (Interpolate, Clump,
#             Frizz, Noise, Set Profile from datafiles/assets/nodes/procedural_hair_node_assets.blend)
# Renders: close.png (macro, ~0.02 mm/px, like fur close-up photos) and review.png (~0.25 mm/px, the cat's review
# camera scale). Values are a white short-haired flank; refine from engine/references/cat-hair-streams.md.
import bpy, bmesh, sys, os, json, time
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["ours", "."]
MODE, OUT = argv[0], argv[1]
DS = float(argv[2]) if len(argv) > 2 else 1.0
PRESET = argv[3] if len(argv) > 3 else "v1"
FAST = "fast" in argv                         # exploration: half resolution, 96 samples
os.makedirs(OUT, exist_ok=True)
t0 = time.time()
rng = np.random.default_rng(7)
R_CYL, HALF = 0.07, 0.04                       # patch: cylinder radius 7 cm, 8 x 8 cm
LAYERS = [  # name, length m, density per cm2, root radius m, lift root/tip deg, lock strength, crimp m
    ("guard", 0.018, 400 * DS, 0.000035, (22, 8), 0.85, 0.0),
    ("awn", 0.014, 1500 * DS, 0.000022, (25, 10), 0.75, 0.00008),
    ("down", 0.009, 3000 * DS, 0.000013, (40, 25), 0.30, 0.00025),
]
K = 8
if PRESET == "v3":   # v2 + locks that PART (bigger, tighter at the tips), a thinner under-layer so the partings show depth
    LAYERS = [
        ("guard", 0.022, 300 * DS, 0.000038, (36, 14), 0.55, 0.0),
        ("awn", 0.015, 1500 * DS, 0.000022, (30, 12), 0.97, 0.00004),
        ("down", 0.007, 1800 * DS, 0.000012, (45, 30), 0.40, 0.00025),
    ]
if PRESET == "v2":   # structure of real coats: stiff guard hairs stand above a dense under-layer; locks part and
    LAYERS = [       # deviate from the main lie; down stays hidden and crimped
        ("guard", 0.022, 400 * DS, 0.000038, (38, 16), 0.35, 0.0),
        ("awn", 0.014, 1500 * DS, 0.000022, (28, 12), 0.92, 0.00006),
        ("down", 0.008, 3000 * DS, 0.000012, (45, 30), 0.30, 0.00025),
    ]
LOCK_DEV = 0.30 if PRESET in ("v2", "v3") else 0.0     # per-lock direction deviation (radians-ish, tangent offset)
LOCK_MM2 = {"v2": 7.0, "v3": 10.0}.get(PRESET, 4.0)      # area per lock

# ---- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons["cycles"].preferences
for dt in ("OPTIX", "CUDA", "HIP", "ONEAPI"):
    try:
        prefs.compute_device_type = dt; prefs.get_devices()
        if any(d.type == dt for d in prefs.devices):
            for d in prefs.devices: d.use = True
            sc.cycles.device = 'GPU'; break
    except Exception:
        pass
sc.cycles.samples = 256; sc.cycles.use_denoising = False
sc.cycles_curves.shape = 'THICK'; sc.cycles_curves.subdivisions = 3
sc.render.film_transparent = False
world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.32, 0.32, 0.33, 1); world.node_tree.nodes["Background"].inputs[1].default_value = 0.25

# ---- the skin patch (grid with UVs, bent onto a cylinder along X)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=160, y_subdivisions=160, size=2 * HALF)
patch = bpy.context.active_object; patch.name = "Swatch"
for v in patch.data.vertices:
    x, y = v.co.x, v.co.y; a = y / R_CYL
    v.co = Vector((x, R_CYL * np.sin(a), R_CYL * np.cos(a) - R_CYL))
patch.data.update()
skin = bpy.data.materials.new("Skin"); skin.use_nodes = True
b = skin.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.82, 0.72, 0.72, 1); b.inputs["Roughness"].default_value = 0.55
patch.data.materials.append(skin)
for p in patch.data.polygons: p.use_smooth = True

hairmat = bpy.data.materials.new("Fur"); hairmat.use_nodes = True
nt = hairmat.node_tree; [nt.nodes.remove(n) for n in list(nt.nodes)]
hb = nt.nodes.new("ShaderNodeBsdfHairPrincipled"); hb.parametrization = 'MELANIN'
hb.inputs["Melanin"].default_value = 0.04; hb.inputs["Melanin Redness"].default_value = 0.3
hb.inputs["Roughness"].default_value = 0.28; hb.inputs["Radial Roughness"].default_value = 0.3; hb.inputs["Coat"].default_value = 0.12
hb.inputs["Random Color"].default_value = 0.08; hb.inputs["Random Roughness"].default_value = 0.15
o = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(hb.outputs[0], o.inputs["Surface"])

# ---- lights and cameras (identical for both modes)
def area(name, loc, size, energy):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = energy
    ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob); ob.location = loc
    ob.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return ob
if PRESET in ("v2", "v3"):   # a smaller, lower key gives the fur depth (shadow in the partings); soft fill keeps it readable
    area("Key", (-0.30, -0.20, 0.22), 0.08, 9); area("Fill", (0.35, -0.10, 0.25), 0.4, 3); area("Rim", (0.05, 0.35, 0.20), 0.2, 6)
else:
    area("Key", (-0.25, -0.30, 0.45), 0.25, 14); area("Fill", (0.35, -0.10, 0.25), 0.4, 4); area("Rim", (0.05, 0.35, 0.20), 0.2, 6)
cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 100; cam_d.sensor_width = 36
cam_d.clip_start = 0.001                                     # the default 0.1 m clipped the macro camera (8 cm away)
cam = bpy.data.objects.new("Cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
view_dir = Vector((0.0, -0.55, 0.83)).normalized()            # oblique, across the lie of the hair

def place(field_w):
    d = field_w * cam_d.lens / cam_d.sensor_width
    cam.location = view_dir * d + Vector((0, 0, 0.004))
    cam.rotation_euler = (-view_dir).to_track_quat('-Z', 'Y').to_euler()

# ---- roots and guide-free strand building (shared helpers)
me = patch.data; me.calc_loop_triangles()
nt_ = len(me.loop_triangles)
tv = np.empty(nt_ * 3, np.int32); me.loop_triangles.foreach_get("vertices", tv); tv = tv.reshape(-1, 3)
tl = np.empty(nt_ * 3, np.int32); me.loop_triangles.foreach_get("loops", tl); tl = tl.reshape(-1, 3)
co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3).astype(float)
vn = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("normal", vn); vn = vn.reshape(-1, 3).astype(float)
uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers.active.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
A_ = co[tv[:, 0]]; area_t = 0.5 * np.linalg.norm(np.cross(co[tv[:, 1]] - A_, co[tv[:, 2]] - A_), axis=1)
unit = lambda v: v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)

def roots(n):
    tri = rng.choice(nt_, size=n, p=area_t / area_t.sum())
    r1, r2 = rng.random(n), rng.random(n); s1 = np.sqrt(r1)
    bc = np.stack([1 - s1, s1 * (1 - r2), s1 * r2], 1)
    P = (bc[:, :, None] * co[tv[tri]]).sum(1); N = unit((bc[:, :, None] * vn[tv[tri]]).sum(1))
    UV = (bc[:, :, None] * uv[tl[tri]]).sum(1)
    return P, N, UV

def strands(P, N, length, lift, crimp, wob=0.10):
    n = len(P)
    comb = np.array([1.0, 0, 0])[None] + 0.12 * rng.normal(size=(n, 3))      # the hair lies along +X (head -> tail)
    comb = unit(comb - (comb * N).sum(1, keepdims=True) * N)
    side = unit(np.cross(N, comb))
    L = length * rng.uniform(0.8, 1.15, n)
    l0, l1 = np.radians(rng.normal(lift[0], 4, n)), np.radians(rng.normal(lift[1], 3, n))
    pts = np.zeros((n, K, 3)); pts[:, 0] = P - N * 0.0002
    w = rng.normal(size=(n, 3)) * wob; ph = rng.uniform(0, 6.28, n)
    for k in range(1, K):
        f = (k - 1) / (K - 2); th = l0 * (1 - f) + l1 * f
        d = unit(np.cos(th)[:, None] * comb + np.sin(th)[:, None] * N + w * f)
        pts[:, k] = pts[:, k - 1] + d * (L / (K - 1))[:, None]
        if crimp:
            pts[:, k] += side * (crimp * np.sin(ph + 2.4 * k))[:, None]
    return pts, L

def make_curves(name, pts, rad_root, UV=None, attach=True):
    n = len(pts)
    cd = bpy.data.hair_curves.new(name); cd.add_curves([K] * n)
    cd.attributes["position"].data.foreach_set("vector", pts.astype(np.float32).ravel())
    ra = cd.attributes.get("radius") or cd.attributes.new("radius", 'FLOAT', 'POINT')
    ra.data.foreach_set("value", np.tile(np.linspace(rad_root, rad_root * 0.25, K), n).astype(np.float32))
    if UV is not None:
        su = cd.attributes.get("surface_uv_coordinate") or cd.attributes.new("surface_uv_coordinate", 'FLOAT2', 'CURVE')
        su.data.foreach_set("vector", UV.astype(np.float32).ravel())
    cd.materials.append(hairmat)
    ob = bpy.data.objects.new(name, cd); sc.collection.objects.link(ob)
    if attach:
        cd.surface = patch; cd.surface_uv_map = me.uv_layers.active.name
    return ob

area_cm2 = (2 * HALF * 100) ** 2
stats = {}
if MODE == "ours":
    for name, length, dens, rr, lift, lock, crimp in LAYERS:
        n = int(area_cm2 * dens)
        P, N, UV = roots(n)
        pts, L = strands(P, N, length, lift, crimp)
        # LOCKS: hairs gather toward a lock centre's strand (lock spacing ~2 mm), tips most, leaving gaps between
        nl = max(int(area_cm2 * 100 / LOCK_MM2), 1)                         # one lock per LOCK_MM2 mm2
        li = rng.choice(n, nl, replace=False)
        from mathutils.kdtree import KDTree
        kd = KDTree(nl)
        for i, j in enumerate(li): kd.insert(P[j], i)
        kd.balance()
        near = np.array([kd.find(tuple(p))[1] for p in P])
        gp = pts[li[near]]; gp = gp - gp[:, :1] + pts[:, :1]
        if LOCK_DEV > 0:                                               # each lock lies at its own small angle
            dev = rng.normal(0, LOCK_DEV, nl)[near]
            sidev = unit(np.cross(N, np.array([1.0, 0, 0])[None]))
            gp = gp + (gp - gp[:, :1]) * 0 + sidev[:, None, :] * (np.linspace(0, 1, K)[None, :, None] * (L * dev)[:, None, None])
        f = (np.linspace(0, 1, K) ** 1.2)[None, :, None] * (lock * rng.uniform(0.7, 1.0, n))[:, None, None]
        pts = pts * (1 - f) + gp * f
        make_curves(f"fur_{name}", pts, rr, UV)
        stats[name] = n
else:
    # the same guide structure (one guide per ~2 mm2 per layer), Blender's tools make the strands
    lib = r'C:\Program Files\Blender Foundation\Blender 5.2\5.2\datafiles\assets\nodes\procedural_hair_node_assets.blend'
    with bpy.data.libraries.load(lib) as (src, dst):
        dst.node_groups = [g for g in src.node_groups if g in ("Interpolate Hair Curves", "Clump Hair Curves",
                           "Frizz Hair Curves", "Hair Curves Noise", "Set Hair Curve Profile")]
    G = {g.name: g for g in dst.node_groups}
    for name, length, dens, rr, lift, lock, crimp in LAYERS:
        ng_ = int(area_cm2 * 100 / 2.0)
        P, N, UV = roots(ng_)
        pts, L = strands(P, N, length, lift, 0.0, wob=0.05)
        ob = make_curves(f"guides_{name}", pts, rr, UV)
        tree = bpy.data.node_groups.new(f"groom_{name}", 'GeometryNodeTree')
        tree.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        tree.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
        gi, go = tree.nodes.new("NodeGroupInput"), tree.nodes.new("NodeGroupOutput")
        def grp(gname, **vals):
            nd = tree.nodes.new("GeometryNodeGroup"); nd.node_tree = G[gname]
            for k_, v_ in vals.items():
                nd.inputs[k_].default_value = v_
            return nd
        interp = grp("Interpolate Hair Curves", **{"Density": dens * 1e4, "Interpolation Guides": 4, "Viewport Amount": 1.0})
        clump = grp("Clump Hair Curves", **{"Factor": lock, "Distance Threshold": {"v2": 0.0016, "v3": 0.0024}.get(PRESET, 0.0012), "Tip Spread": 0.0002 if PRESET != "v3" else 0.00008})
        frizz = grp("Frizz Hair Curves", **{"Factor": 1.0, "Distance": 0.00004 + crimp})
        noise = grp("Hair Curves Noise", **({"Factor": 1.0, "Distance": 0.0015, "Scale": 60.0} if PRESET == "v2" else
                                            {"Factor": 1.0, "Distance": 0.0012, "Scale": 35.0} if PRESET == "v3" else
                                            {"Factor": 1.0, "Distance": 0.0002, "Scale": 300.0}))
        prof = grp("Set Hair Curve Profile", **{"Replace Radius": True, "Radius": rr})
        chain = [gi, interp, clump, frizz, noise, prof, go]
        for a_, b_ in zip(chain[:-1], chain[1:]):
            tree.links.new(a_.outputs[0], b_.inputs[0])
        md = ob.modifiers.new("groom", 'NODES'); md.node_group = tree
        dg = bpy.context.evaluated_depsgraph_get()
        stats[name] = len(ob.evaluated_get(dg).data.curves)
print("strands", stats, f"{time.time() - t0:.0f}s")

# ---- renders
if FAST:
    sc.cycles.samples = 96
SUPER = 2 if PRESET == "v3" else 1                 # supersample the review view: render 2x, average down (removes noise)
for tag, field, res in (("close", 0.030, (1600, 1067)), ("review", 0.060, (240, 160))):
    place(field); sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 50 if (FAST and tag == "close") else 100
    if tag == "review" and SUPER > 1:
        sc.render.resolution_percentage = 100 * SUPER
    sc.render.filepath = os.path.join(OUT, f"{tag}.png")
    bpy.ops.render.render(write_still=True)
    if tag == "review" and SUPER > 1:
        im = bpy.data.images.load(sc.render.filepath); im.scale(*res); im.save()
    print("rendered", tag, f"{time.time() - t0:.0f}s")
json.dump(dict(mode=MODE, density_scale=DS, strands=stats, seconds=round(time.time() - t0)), open(os.path.join(OUT, "info.json"), "w"))
