"""Score fur images against reference close-ups of real fur with SCALE-TOLERANT measures (the references' magnification
is unknown): how deep the gaps between locks go (dark-gap depth), sharpness relative to contrast, how orderly the
hair runs (structure-tensor coherence), and how detail falls off from coarse to fine (radial power-spectrum slope).
Each measure is compared to the references' range; the score is the mean |z| against the references (lower =
closer). A3 self-test first: a blurred copy of a reference must score worse than the reference itself.

usage: python fur_swatch_score.py <reference images dir> <candidate image> [<candidate image> ...]
"""
import glob
import os
import sys

import cv2
import numpy as np


def measures(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32) * 100 / 255
    h, w = g.shape
    c = g[h // 8: -h // 8, w // 8: -w // 8]                     # central crop: no frame edges
    med = np.median(c)
    gap = (med - np.percentile(c, 5)) / max(med, 1e-6)          # dark-gap depth between locks
    gx, gy = cv2.Sobel(c, cv2.CV_32F, 1, 0), cv2.Sobel(c, cv2.CV_32F, 0, 1)
    sharp = np.hypot(gx, gy).mean() / max(c.std(), 1e-6)
    j = [cv2.GaussianBlur(t, (0, 0), 4) for t in (gx * gx, gy * gy, gx * gy)]
    coh = float(np.median(np.sqrt((j[0] - j[1]) ** 2 + 4 * j[2] ** 2) / np.maximum(j[0] + j[1], 1e-6)))
    s = min(c.shape); cc = c[:s, :s] - c[:s, :s].mean()
    F = np.abs(np.fft.fftshift(np.fft.fft2(cc * np.outer(np.hanning(s), np.hanning(s))))) ** 2
    yy, xx = np.indices(F.shape); r = np.hypot(yy - s / 2, xx - s / 2).astype(int)
    prof = np.bincount(r.ravel(), F.ravel()) / np.maximum(np.bincount(r.ravel()), 1)
    k = np.arange(4, s // 3)
    slope = float(np.polyfit(np.log(k), np.log(prof[k] + 1e-9), 1)[0])
    return dict(gap=float(gap), sharp=float(sharp), coherence=coh, slope=slope)


def score(m, ref):
    return float(np.mean([abs(m[k] - ref[k][0]) / max(ref[k][1], 1e-6) for k in ref]))


if __name__ == "__main__":
    refs = sorted(glob.glob(os.path.join(sys.argv[1], "*.jpg")) + glob.glob(os.path.join(sys.argv[1], "*.png")))
    R = [measures(cv2.imread(f)) for f in refs]
    ref = {k: (np.mean([r[k] for r in R]), np.std([r[k] for r in R]) + 0.05 * abs(np.mean([r[k] for r in R])) + 1e-3) for k in R[0]}
    print(f"references: {len(R)}  " + "  ".join(f"{k} {v[0]:.3f}+-{v[1]:.3f}" for k, v in ref.items()))
    one = cv2.imread(refs[0])                                        # A3: the measure must tell sharp from blurred
    s_ref, s_blur = score(measures(one), ref), score(measures(cv2.GaussianBlur(one, (0, 0), 3)), ref)
    print(f"self-test: reference {s_ref:.2f}  blurred copy {s_blur:.2f}  -> {'OK' if s_blur > s_ref else 'FAILED: measure cannot see blur'}")
    for f in sys.argv[2:]:
        m = measures(cv2.imread(f))
        print(f"{os.path.relpath(f):55s} score {score(m, ref):5.2f}   " + "  ".join(f"{k} {v:.3f}" for k, v in m.items()))
