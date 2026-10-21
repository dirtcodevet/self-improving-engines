"""Photo vs render close-ups of the ears and the temple strip (eye -> ear), same camera, side by side.

Crop boxes come from the model's landmarks projected through the frozen camera (ear tip, ear base, eye), so the
same anatomy is framed in both images. Rows: right ear + temple, left ear + temple; columns: photo | render.
usage:
  python ear_crops.py <photo> <render_same_camera> <landmarks.json> <camera.json> <out.png> [scale]   full render
  python ear_crops.py boxes <photo> <landmarks.json> <camera.json> <out_boxes.json>                  for a lab loop
  python ear_crops.py compose <photo> <boxes.json> <crop_dir> <out.png> [scale]   crop_dir/ear_<side>.png per box
The lab loop (engine/review/ear_lab.sh) border-renders only the boxes: seconds instead of a full build.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from project_mask import project  # noqa: E402


def boxes(photo, lm, camf):
    W, H = Image.open(photo).size
    L = json.load(open(lm))["landmarks"]
    cam = json.load(open(camf))
    out = {}
    for sd in ("R", "L"):
        pts = np.array([L[f"ear_tip.{sd}"], L[f"ear_base.{sd}"], L[f"eye.{sd}"]], float)
        uv = project(pts, cam, W, H)[0]
        x0, y0 = uv.min(0); x1, y1 = uv.max(0)
        m = 0.25 * max(x1 - x0, y1 - y0)
        out[sd] = [int(round(v)) for v in (max(x0 - m, 0), max(y0 - m, 0), min(x1 + m, W), min(y1 + m, H))]
    return out, (W, H)


def sheet(photo, crops, bx, out, scale=2.5):
    P = Image.open(photo).convert("RGB")
    rows = []
    for sd in ("R", "L"):
        box = tuple(bx[sd])
        size = (int((box[2] - box[0]) * scale), int((box[3] - box[1]) * scale))
        row = Image.new("RGB", (2 * size[0] + 12, size[1] + 28), (255, 255, 255))
        for i, (im, lab) in enumerate(((P.crop(box), "photo"), (crops[sd], "render"))):
            row.paste(im.convert("RGB").resize(size, Image.LANCZOS), (i * (size[0] + 12), 28))
            ImageDraw.Draw(row).text((i * (size[0] + 12) + 6, 6), f"{lab}  ear.{sd} + temple", fill=(0, 0, 0))
        rows.append(row)
    Wt = max(r.size[0] for r in rows)
    s = Image.new("RGB", (Wt, sum(r.size[1] for r in rows) + 12 * (len(rows) - 1)), (255, 255, 255))
    y = 0
    for r in rows:
        s.paste(r, (0, y)); y += r.size[1] + 12
    s.save(out)
    print("ear crops ->", out, s.size)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "boxes":
        bx, (W, H) = boxes(a[1], a[2], a[3])
        json.dump(dict(boxes=bx, W=W, H=H), open(a[4], "w"))
        print(json.dumps(bx))
    elif a[0] == "compose":
        bx = json.load(open(a[2]))["boxes"]
        crops = {sd: Image.open(os.path.join(a[3], f"ear_{sd}.png")) for sd in ("R", "L")}
        sheet(a[1], crops, bx, a[4], float(a[5]) if len(a) > 5 else 2.5)
    else:
        bx, _ = boxes(a[0], a[2], a[3])
        R = Image.open(a[1])
        sheet(a[0], {sd: R.crop(tuple(b)) for sd, b in bx.items()}, bx, a[4], float(a[5]) if len(a) > 5 else 2.5)
