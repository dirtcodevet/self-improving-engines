"""Calibrate studio light balance to the reference photo by luminance DISTRIBUTION matching (not eyeballing).
Stats: subject p10/p50/p90 inside each image's own subject mask + backdrop mean. Coordinate search over
light energies / world / exposure via low-res Cycles renders in the live Blender. Writes best to <out.json>.
usage: python light_match.py <ref.jpg> <ref_mask.png> <probe_mask.png> <out.json> [iters=2]
(probe_mask = the model silhouette at the camera, from probe.py)
"""
import json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image

ref_p, refm_p, modm_p, out_p = sys.argv[1:5]
iters = int(sys.argv[5]) if len(sys.argv) > 5 else 2
HERE = os.path.dirname(os.path.abspath(__file__))
BM = os.path.join(HERE, "bmcp.py")
W, H = 432, 288


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def stats(img, mask):
    L = lum(img)
    sub = L[mask]
    bgm = ~np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(__import__("PIL.ImageFilter").ImageFilter.MaxFilter(15))) > 0
    bg = L[bgm & (np.arange(L.shape[0])[:, None] < L.shape[0] * 0.75)]
    return np.array([np.percentile(sub, 10), np.percentile(sub, 50), np.percentile(sub, 90), bg.mean()])


ref = np.asarray(Image.open(ref_p).convert("RGB").resize((W, H))).astype(float)
refm = np.asarray(Image.open(refm_p).convert("L").resize((W, H))) > 127
modm = np.asarray(Image.open(modm_p).convert("RGBA").resize((W, H)))[..., 3] > 127
target = stats(ref, refm)
print("target p10/p50/p90/bg", target.round(1))
tmp = tempfile.mkdtemp()


def render(cfg):
    out = os.path.join(tmp, "lm.png")
    code = f"""
import bpy
sc=bpy.context.scene
for n,k in (('Key','key'),('Fill','fill'),('Rim','rim'),('Top','top'),('BG','bg')):
    o=bpy.data.objects.get(n)
    if o and k in {cfg}: o.data.energy={cfg}[k]
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value={cfg}['world']
sc.view_settings.exposure={cfg}['exposure']
fm=bpy.data.materials['M_Fur'].node_tree.nodes
g=[n for n in fm if n.bl_idname=='ShaderNodeGamma']
if g: g[0].inputs['Gamma'].default_value={cfg}.get('fur_gamma',1.8)
st=bpy.data.materials.get('M_Studio')
if st: st.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*[{cfg}.get('backdrop',0.62)]*3,1)
r=sc.render; cy=sc.cycles; sv=(r.resolution_percentage,cy.samples,r.filepath,r.use_border)
r.resolution_percentage=25; cy.samples=24; r.use_border=False; r.filepath=r'{out}'
bpy.ops.render.render(write_still=True)
r.resolution_percentage,cy.samples,r.filepath,r.use_border=sv
"""
    subprocess.run([sys.executable, BM, "code", code], check=True, capture_output=True)
    return np.asarray(Image.open(out).convert("RGB").resize((W, H))).astype(float)


def loss(cfg):
    s = stats(render(cfg), modm)
    wts = np.array([1.5, 1.0, 1.0, 0.7])
    return float((wts * (s - target) ** 2).sum()), s


cfg = json.load(open(out_p)) if os.path.exists(out_p) else dict(key=260, fill=22, rim=150, top=25, world=0.25, exposure=-0.45)
best, bs = loss(cfg)
print("start", round(best, 1), bs.round(1), cfg)
cfg.setdefault("fur_gamma", 1.8); cfg.setdefault("backdrop", 0.62); cfg.setdefault("bg", 300.0)
steps = dict(bg=0.6, world=0.6, exposure=0.35, fur_gamma=0.35, key=0.35, fill=0.6, rim=0.5, top=0.6, backdrop=0.2)
for it in range(iters):
    for k, st in steps.items():
        for sgn in (+1, -1):
            c2 = dict(cfg)
            c2[k] = cfg[k] + sgn * st if k == "exposure" else cfg[k] * (1 + st) ** sgn
            if k == "backdrop":
                c2[k] = min(c2[k], 0.95)
            l2, s2 = loss(c2)
            if l2 < best:
                best, bs, cfg = l2, s2, c2
                print(f"  {k}{'+' if sgn > 0 else '-'} -> {best:.1f} {bs.round(1)}")
                break
    steps = {k: v * 0.5 for k, v in steps.items()}
json.dump(cfg, open(out_p, "w"), indent=1)
print("best", round(best, 1), "stats", bs.round(1), "target", target.round(1))
print(json.dumps(cfg))
