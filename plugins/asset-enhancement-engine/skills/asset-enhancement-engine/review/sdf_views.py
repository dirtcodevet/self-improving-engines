"""Shaded ORTHOGRAPHIC clay views of a signed-distance grid (.npz with F, lo, vox) - no Blender needed: front, side,
top, three-quarter. For checking a layer's volume (e.g. a skull hull) before it goes into the scene.
usage: python sdf_views.py <grid.npz> <out.png> [size_px=360]
"""
import sys

import cv2
import numpy as np
from scipy import ndimage


def render(F, vox, view, size):
    # view: rotation applied to the grid (ndimage.rotate) then look down -y (front), +x (side), -z (top)
    G = F
    if view == "three_quarter":
        G = ndimage.rotate(G, 35, axes=(0, 1), reshape=True, order=1, mode="constant", cval=10.0)
        G = ndimage.rotate(G, -20, axes=(1, 2), reshape=True, order=1, mode="constant", cval=10.0)
        look = 1
    else:
        look = {"front": 1, "side": 0, "top": 2}[view]
    inside = G < 0
    hit = inside.any(look)
    first = np.argmax(inside, axis=look).astype(float)                # nearest surface along the look axis
    depth = np.where(hit, first, np.nan)
    gy, gx = np.gradient(np.nan_to_num(depth, nan=np.nanmax(depth) if hit.any() else 0))
    n = np.dstack([-gx, -gy, np.ones_like(gx) * 1.0]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    light = np.array([-0.4, -0.5, 0.75]); light /= np.linalg.norm(light)
    shade = np.clip(n @ light, 0, 1) * 0.75 + 0.25
    img = np.where(hit, shade * 230, 40).astype(np.uint8)
    if view == "side":
        img = img.T                                                  # rows = z, cols = y
    elif view in ("front", "three_quarter"):
        img = img.T
    else:
        img = img.T
    img = img[::-1] if view != "top" else img                        # z up
    s = size / max(img.shape)
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)


def main(npz, out, size=360):
    D = np.load(npz); F = D["F"]; vox = float(D["vox"])
    tiles = []
    for v in ("front", "side", "top", "three_quarter"):
        t = render(F, vox, v, size)
        t = cv2.cvtColor(t, cv2.COLOR_GRAY2BGR)
        t = np.pad(t, ((0, size - t.shape[0]), (0, size - t.shape[1]), (0, 0)), constant_values=40)
        cv2.putText(t, v, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 1); tiles.append(t)
    cv2.imwrite(out, np.hstack(tiles))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 360)
