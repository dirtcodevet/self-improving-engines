"""Side-by-side photo | render (full frame) and optional crop pair. usage: compare.py ref.jpg render.png out.png [crop_render.png x0 y0 x1 y1(0..1, y up)]"""
import sys
from PIL import Image
ref, ren, out = sys.argv[1:4]
a = Image.open(ref).convert('RGB').resize((864, 576)); b = Image.open(ren).convert('RGB').resize((864, 576))
c = Image.new('RGB', (1728, 576)); c.paste(a, (0, 0)); c.paste(b, (864, 0)); c.crop((220, 30, 1528, 560)).save(out)
if len(sys.argv) > 4:
    crop, x0, y0, x1, y1 = sys.argv[4], *map(float, sys.argv[5:9])
    r = Image.open(ref).convert('RGB'); W, H = r.size
    ra = r.crop((int(x0 * W), int((1 - y1) * H), int(x1 * W), int((1 - y0) * H)))
    rb = Image.open(crop).convert('RGB').resize(ra.size)
    c = Image.new('RGB', (ra.width * 2, ra.height)); c.paste(ra, (0, 0)); c.paste(rb, (ra.width, 0))
    c.save(out.replace('.png', '_crop.png'))
