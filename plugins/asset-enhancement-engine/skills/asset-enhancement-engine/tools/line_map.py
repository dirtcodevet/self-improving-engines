"""LINE MAP: thin structures in an image - bright lines (whiskers, hairs, highlights on rims) and dark lines (mouth
line, nostrils, eyelid rims, cracks) - with their direction and how long / straight they run. Domain-neutral: the
same map reads leaf veins, fabric threads, roads in aerial photos, cracks, handwriting strokes, wiring.

Method: Hessian of the luminance at several scales (scale-normalised by sigma^2); a bright line has a strongly
negative curvature across it, a dark line a strongly positive one. The line runs along the eigenvector of the
smaller-magnitude curvature. "Straightness" = structure-tensor coherence at a larger scale (long straight lines
such as whiskers score high; tangles and texture score low).

usage: python line_map.py <image> <out.npz> [debug.png] [mask.png]
out: bright, dark (strength 0..1, robust-normalised), angle_deg (line direction, x right y down, mod 180),
     straight (0..1), scale (sigma of the strongest response)
First noticed by the person in the photo-flow work (2026-10-17): the bright-ridge map showed nose, nostrils,
mouth, eyes, whiskers and ear hairs in fine detail.
"""
import sys

import cv2
import numpy as np


def hessian(L, s):
    g = cv2.GaussianBlur(L, (0, 0), s)
    xx, yy, xy = cv2.Sobel(g, cv2.CV_32F, 2, 0), cv2.Sobel(g, cv2.CV_32F, 0, 2), cv2.Sobel(g, cv2.CV_32F, 1, 1)
    tr, d = (xx + yy) / 2, np.sqrt(((xx - yy) / 2) ** 2 + xy ** 2)
    l1, l2 = tr - d, tr + d                                       # l1 <= l2
    # eigenvector of the larger-magnitude curvature points ACROSS the line; the line runs perpendicular to it
    across = 0.5 * np.arctan2(2 * xy, xx - yy)                    # direction of the l2 eigenvector
    return l1 * s * s, l2 * s * s, across


def line_map(img, scales=(1.0, 1.5, 2.5), mask=None):
    L = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32) * 100 / 255
    bright = np.zeros(L.shape, np.float32); dark = np.zeros_like(bright)
    ang = np.zeros_like(bright); scl = np.zeros_like(bright)
    for s in scales:
        l1, l2, across = hessian(L, s)
        b, d = np.maximum(-l1, 0), np.maximum(l2, 0)
        # line direction: for a bright line the across-direction is l1's eigenvector (perpendicular to l2's)
        a_b = np.degrees(across) % 180                            # l2 eigvec = along a bright line
        a_d = (np.degrees(across) + 90) % 180                     # l1 eigvec = along a dark line
        take = np.maximum(b, d) > np.maximum(bright, dark)
        ang = np.where(take, np.where(b >= d, a_b, a_d), ang)
        scl = np.where(take, s, scl)
        bright, dark = np.maximum(bright, b), np.maximum(dark, d)
    sel = mask if mask is not None else np.ones(L.shape, bool)
    for a in (bright, dark):
        a /= max(np.percentile(a[sel], 99.5), 1e-6)
        np.clip(a, 0, 1, out=a)
    g = cv2.GaussianBlur(L, (0, 0), 1.2)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    j = [cv2.GaussianBlur(t, (0, 0), 6) for t in (gx * gx, gy * gy, gx * gy)]
    straight = np.sqrt((j[0] - j[1]) ** 2 + 4 * j[2] ** 2) / np.maximum(j[0] + j[1], 1e-6)
    return bright, dark, ang.astype(np.float32), straight.astype(np.float32), scl


def debug_image(img, bright, dark):
    base = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR).astype(np.float32) * 0.35
    out = base.copy()
    out[..., 0] += 255 * bright; out[..., 1] += 255 * bright                     # bright lines: cyan
    out[..., 2] += 255 * dark; out[..., 0] += 255 * dark                         # dark lines: magenta
    return np.clip(out, 0, 255).astype(np.uint8)


if __name__ == "__main__":
    img = cv2.imread(sys.argv[1])
    mask = cv2.imread(sys.argv[4], 0) > 127 if len(sys.argv) > 4 else None
    bright, dark, ang, straight, scl = line_map(img, mask=mask)
    np.savez_compressed(sys.argv[2], bright=bright.astype(np.float16), dark=dark.astype(np.float16),
                        angle_deg=ang.astype(np.float16), straight=straight.astype(np.float16), scale=scl.astype(np.float16))
    print(f"line map: {img.shape[1]}x{img.shape[0]}  bright > 0.5: {(bright > 0.5).mean() * 100:.1f} %  "
          f"dark > 0.5: {(dark > 0.5).mean() * 100:.1f} %  -> {sys.argv[2]}")
    if len(sys.argv) > 3:
        cv2.imwrite(sys.argv[3], debug_image(img, bright, dark))
