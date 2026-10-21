"""CLAY PAIRS: two (or more) skins rendered with the same camera and the same raking light, laid side by side with
labels, and close crops of the same pixels of each (build 13a3's a3_shots.py and a3_bl_rake.py, used again by 13a4;
moved here in build A1, 2026-10-21). For fixed front / side / top views of PLY files use clay_sheet.py instead.

  render(spec, meshes, out_dir, log=None)  run clay_rake_bl.py in background Blender: spec = {"samples", "views": [...]}
                                           (see clay_rake_bl.py), meshes = {tag: mesh.npz}; renders out_dir/<tag>/<view>.png
  pair(a_png, b_png, out_png, title, lab_a, lab_b)   the two side by side under a title, each labelled
  project_box(view, P)                     the pixel box of points P in a perspective view (Blender's camera: 36 mm
                                           sensor fitted to the larger side), for a crop round a changed region
  crop_pair(view, P, tags, out_dir, name, title, margin=0.06)  the same crop of each tag's render, then their pair
CLI: python engine/review/clay_pairs.py SPEC.json OUT_DIR A=mesh_a.npz B=mesh_b.npz   (renders, then one pair per view)
Proof: engine/review/test_clay_pairs.py (a planted 0.3 mm bump on a sphere shows in the pair, inside its box only).
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"


def font(sz):
    from PIL import ImageFont
    try:
        return ImageFont.truetype("arial.ttf", sz)
    except Exception:
        return ImageFont.load_default()


def render(spec, meshes, out_dir, log=None, timeout=7200):
    out_dir = os.path.abspath(out_dir); os.makedirs(out_dir, exist_ok=True)
    vp = os.path.join(out_dir, "views.json")
    with open(vp, "w") as fh:
        json.dump(spec, fh, indent=1)
    cmd = [BLENDER, "-b", "--factory-startup", "--python", os.path.join(HERE, "clay_rake_bl.py"), "--", vp, out_dir] + \
          ["%s=%s" % (k, os.path.abspath(v)) for k, v in meshes.items()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    with open(log or os.path.join(out_dir, "blender_log.txt"), "w") as fh:
        fh.write(r.stdout[-20000:] + r.stderr[-5000:])
    if r.returncode != 0 or "Traceback" in r.stdout + r.stderr:
        raise RuntimeError("clay render failed:\n" + r.stdout[-3000:] + r.stderr[-3000:])
    return vp


def project_box(v, P):
    loc = np.array(v["loc"], float); tgt = np.array(v["target"], float); fwd = (tgt - loc) / np.linalg.norm(tgt - loc)
    up = np.array([0, 0, 1.0]); up_t = up - fwd * (up @ fwd); up_t /= np.linalg.norm(up_t); right = np.cross(fwd, up_t)
    W, H = v["resolution"]; f = v.get("lens", 85.0) / 36.0 * max(W, H)
    Q = P - loc; z = Q @ fwd
    x = W / 2 + f * (Q @ right) / z; y = H / 2 - f * (Q @ up_t) / z
    return x.min(), y.min(), x.max(), y.max()


def pair(a, b, out, title, lab_a="before", lab_b="after"):
    from PIL import Image, ImageDraw
    A = Image.open(a).convert("RGB"); B = Image.open(b).convert("RGB")
    h = max(A.size[1], B.size[1]); W = A.size[0] + B.size[0] + 12
    im = Image.new("RGB", (W, h + 44), (20, 20, 20)); im.paste(A, (0, 44)); im.paste(B, (A.size[0] + 12, 44))
    d = ImageDraw.Draw(im); d.text((10, 8), title, fill=(255, 255, 255), font=font(24))
    for x0, t in ((8, lab_a), (A.size[0] + 20, lab_b)):
        d.rectangle([x0 - 4, 48, x0 + 70, 80], fill=(0, 0, 0)); d.text((x0, 50), t, fill=(255, 255, 255), font=font(26))
    im.save(out)


def crop_pair(v, P, tags, out_dir, name, title, margin=0.06):
    from PIL import Image
    x0, y0, x1, y1 = project_box(v, P)
    W, H = v["resolution"]; m = margin * max(x1 - x0, y1 - y0)
    box = tuple(int(round(t)) for t in (max(0, x0 - m), max(0, y0 - m), min(W, x1 + m), min(H, y1 + m)))
    for tag in tags:
        Image.open(os.path.join(out_dir, tag, v["name"] + ".png")).crop(box).save(os.path.join(out_dir, tag, "_crop_%s.png" % name))
    pair(os.path.join(out_dir, tags[0], "_crop_%s.png" % name), os.path.join(out_dir, tags[1], "_crop_%s.png" % name),
         os.path.join(out_dir, name + "_close.png"), title, tags[0], tags[1])
    return box


if __name__ == "__main__":
    a = sys.argv[1:]
    spec = json.load(open(a[0])); out = os.path.abspath(a[1]); meshes = dict(x.split("=", 1) for x in a[2:])
    render(spec, meshes, out)
    tags = list(meshes)
    if len(tags) >= 2:
        for v in spec["views"]:
            pair(os.path.join(out, tags[0], v["name"] + ".png"), os.path.join(out, tags[1], v["name"] + ".png"),
                 os.path.join(out, v["name"] + ".png"), "%s - %s (left), %s (right)" % (v["name"], tags[0], tags[1]), tags[0], tags[1])
    print("pairs in", out)
