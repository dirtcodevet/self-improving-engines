# Report helper: stack images vertically (same width) with a label bar above each.
# usage: python stack.py <out.png> <label1> <img1> [<label2> <img2> ...]
import sys
import cv2
import numpy as np

out, args = sys.argv[1], sys.argv[2:]
pairs = list(zip(args[0::2], args[1::2]))
imgs = [cv2.imread(p) for _, p in pairs]
W = max(im.shape[1] for im in imgs)
rows = []
for (label, _), im in zip(pairs, imgs):
    im = cv2.resize(im, (W, int(im.shape[0] * W / im.shape[1])), interpolation=cv2.INTER_AREA)
    bar = np.full((44, W, 3), 32, np.uint8)
    cv2.putText(bar, label, (14, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (235, 235, 235), 2, cv2.LINE_AA)
    rows += [bar, im]
cv2.imwrite(out, np.vstack(rows))
print("stacked", out, W)
