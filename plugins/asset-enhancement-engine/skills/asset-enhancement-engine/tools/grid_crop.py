"""GRID CROP for picking (engine-grounding G4: code proposes, a picker picks): a crop of an image with a labelled
grid in ORIGINAL image coordinates, so picked points need no conversion.
usage: python grid_crop.py <image> <out.png> x y w h [step=50] [scale=1.0]
"""
import sys

import cv2

im = cv2.imread(sys.argv[1]); out = sys.argv[2]
x, y, w, h = (int(v) for v in sys.argv[3:7]); step = int(sys.argv[7]) if len(sys.argv) > 7 else 50
s = float(sys.argv[8]) if len(sys.argv) > 8 else 1.0
c = cv2.resize(im[y:y + h, x:x + w], None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
g0x = (x + step - 1) // step * step; g0y = (y + step - 1) // step * step
for gx in range(g0x, x + w, step):
    X = int((gx - x) * s); major = gx % (2 * step) == 0
    cv2.line(c, (X, 0), (X, c.shape[0]), (0, 0, 255) if major else (0, 160, 255), 1)
    if major: cv2.putText(c, str(gx), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 220), 1)
for gy in range(g0y, y + h, step):
    Y = int((gy - y) * s); major = gy % (2 * step) == 0
    cv2.line(c, (0, Y), (c.shape[1], Y), (0, 0, 255) if major else (0, 160, 255), 1)
    if major: cv2.putText(c, str(gy), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 220), 1)
cv2.imwrite(out, c)
