"""Segment the cat from the seamless grey studio background -> binary silhouette mask.

Pass 1 (seed): background = 2nd-order polynomial fitted to border pixels; pixels clearly
brighter (white fur) or more saturated (lavender/pink) than bg become sure-foreground seeds.
Pass 2: OpenCV GrabCut inside a rectangle, seeded with pass-1, resolves shadowed white fur
that is the same grey as the backdrop (pass 1 alone misses it).

usage: python ref_mask.py ref.jpg out_mask.png x0 y0 x1 y1
"""
import sys
import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

src, out = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = map(int, sys.argv[3:7])
rgb = np.asarray(Image.open(src).convert("RGB"))
im = rgb.astype(np.float32)
H, W, _ = im.shape
yy, xx = np.mgrid[0:H, 0:W]
xn, yn = xx / W, yy / H

band = np.zeros((H, W), bool)
band[:60, :] = True
band[:, :120] = True
band[:, -120:] = True
A = np.stack([np.ones_like(xn), xn, yn, xn * xn, yn * yn, xn * yn], -1)
bg = np.zeros_like(im)
for c in range(3):
    coef, *_ = np.linalg.lstsq(A[band], im[..., c][band], rcond=None)
    bg[..., c] = A @ coef

lum, bglum = im.mean(-1), bg.mean(-1)
sat = im.max(-1) - im.min(-1)
bgsat = bg.max(-1) - bg.min(-1)
seed = ((lum - bglum) > 14) | ((sat - bgsat) > 18)
seed = ndi.binary_opening(seed, iterations=3)

gc = np.full((H, W), cv2.GC_BGD, np.uint8)
gc[y0:y1, x0:x1] = cv2.GC_PR_BGD
# probable fg: dilated seed region
gc[ndi.binary_dilation(seed, iterations=12) & (gc == cv2.GC_PR_BGD)] = cv2.GC_PR_FGD
gc[ndi.binary_erosion(seed, iterations=4)] = cv2.GC_FGD
bgdModel = np.zeros((1, 65), np.float64)
fgdModel = np.zeros((1, 65), np.float64)
cv2.grabCut(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), gc, None, bgdModel, fgdModel, 8, cv2.GC_INIT_WITH_MASK)
fg = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)

fg = ndi.binary_opening(fg, iterations=2)
lab, n = ndi.label(fg)
sizes = ndi.sum(fg, lab, range(1, n + 1))
fg = lab == (np.argmax(sizes) + 1)
# fill only small holes (fur speckle); big enclosed areas are bg between the legs
holes = ndi.binary_fill_holes(fg) & ~fg
hl, hn = ndi.label(holes)
if hn:
    hs = ndi.sum(holes, hl, range(1, hn + 1))
    small = np.isin(hl, np.nonzero(hs < 2500)[0] + 1)
    fg |= small

Image.fromarray((fg * 255).astype(np.uint8)).save(out)
ys, xs = np.nonzero(fg)
print(f"size {W}x{H}  fg_px={fg.sum()}  bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]")
