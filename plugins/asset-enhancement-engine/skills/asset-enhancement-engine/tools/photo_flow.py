"""Fur direction measured on the reference photo, per pixel (runs outside Blender).

Hair-scale detail only: a difference-of-gaussians band (sigma 0.8 - 2.5 px) removes marking stripes and broad
shading, which dominated the old whole-gradient flow measure (v37b check: photo fine-scale flow agrees with fur,
render raw flow on cheek.R was a low-coherence artefact). TWO tensor scales, per pixel the clearer one: where fur
TURNS (the cheek, where the flow from the eye bends down and back - the person's circled gaps, 2026-10-17) the coarse
scale mixes the directions into "no direction"; the fine scale reads the turn. Structure tensor (sigma ~3 px) -> the orientation across
which brightness changes most; fur runs perpendicular to it. Orientation only (mod 180 deg): the sign comes from the
anatomical hair tracts (hair_tracts.py) when it is mapped onto the skin (hair_field.py).

usage: python photo_flow.py <photo> <mask.png> <out.npz> [debug.png]
out: angle_deg (H, W) fur orientation in image coords (x right, y down), coherence (H, W) 0..1 (0 outside the mask)
"""
import sys

import cv2
import numpy as np


def flow(img, mask=None, s_fine=0.8, s_coarse=2.5, s_tensor=3.0):
    L = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32) * 100 / 255
    band = cv2.GaussianBlur(L, (0, 0), s_fine) - cv2.GaussianBlur(L, (0, 0), s_coarse)
    gx, gy = cv2.Sobel(band, cv2.CV_32F, 1, 0), cv2.Sobel(band, cv2.CV_32F, 0, 1)
    jxx, jyy, jxy = (cv2.GaussianBlur(t, (0, 0), s_tensor) for t in (gx * gx, gy * gy, gx * gy))
    lam = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2)
    coh = lam / np.maximum(jxx + jyy, 1e-6)
    ang = (0.5 * np.degrees(np.arctan2(2 * jxy, jxx - jyy)) + 90.0) % 180.0   # fur runs across the gradient
    if mask is not None:
        coh = np.where(mask, coh, 0.0)
    return ang.astype(np.float32), coh.astype(np.float32)


def flow_multiscale(img, mask=None, scales=(1.5, 3.0)):
    """per pixel the tensor scale with the higher coherence; returns angle, coherence, chosen scale"""
    best = None
    for s in scales:
        a, c = flow(img, mask, s_tensor=s)
        if best is None:
            best = [a, c, np.full(a.shape, s, np.float32)]
        else:
            take = c > best[1]
            best[0] = np.where(take, a, best[0]); best[1] = np.where(take, c, best[1]); best[2] = np.where(take, s, best[2])
    return best


def trust_maps(img, mask, outline_px=10.0):
    """logic checks on the measurement (person, 2026-10-17: "add additional reference and logic checks"):
    - outline: the cat/background edge reads as fur running ALONG the outline (the false vertical strokes on the cheeks)
      -> no trust within outline_px of the mask edge, ramping in over the next outline_px;
    - whiskers: thin, bright, long, straight lines (Hessian ridge at sigma 1.2, coherent at sigma 6) are not fur.
    Returns (outline_weight, whisker_weight), both 0..1 (1 = trust)."""
    dist = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
    w_out = np.clip((dist - outline_px) / outline_px, 0, 1)
    L = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32) * 100 / 255
    Lg = cv2.GaussianBlur(L, (0, 0), 1.2)
    Lxx, Lyy, Lxy = cv2.Sobel(Lg, cv2.CV_32F, 2, 0), cv2.Sobel(Lg, cv2.CV_32F, 0, 2), cv2.Sobel(Lg, cv2.CV_32F, 1, 1)
    ridge = np.maximum(-((Lxx + Lyy) / 2 - np.sqrt(((Lxx - Lyy) / 2) ** 2 + Lxy ** 2)), 0)
    gx, gy = cv2.Sobel(Lg, cv2.CV_32F, 1, 0), cv2.Sobel(Lg, cv2.CV_32F, 0, 1)
    j = [cv2.GaussianBlur(t, (0, 0), 6) for t in (gx * gx, gy * gy, gx * gy)]
    coh6 = np.sqrt((j[0] - j[1]) ** 2 + 4 * j[2] ** 2) / np.maximum(j[0] + j[1], 1e-6)
    thr = np.percentile(ridge[mask], 97)
    whisk = cv2.dilate(((ridge > thr) & (coh6 > 0.55)).astype(np.uint8), np.ones((3, 3), np.uint8))
    return w_out.astype(np.float32), (1 - cv2.GaussianBlur(whisk.astype(np.float32), (0, 0), 1.5)).astype(np.float32)


if __name__ == "__main__":
    photo, maskp, out = sys.argv[1:4]
    img = cv2.imread(photo)
    mask = cv2.imread(maskp, 0) > 127
    ang, coh, scl = flow_multiscale(img, mask)
    w_out, w_whisk = trust_maps(img, mask)
    np.savez_compressed(out, angle_deg=ang.astype(np.float16), coherence=coh.astype(np.float16), scale=scl.astype(np.float16),
                        outline_w=w_out.astype(np.float16), whisker_w=w_whisk.astype(np.float16))
    print(f"photo flow: {img.shape[1]}x{img.shape[0]}  coherence mean (in mask) {coh[mask].mean():.2f}  "
          f"> 0.4: {(coh[mask] > 0.4).mean() * 100:.0f} %  -> {out}")
    if len(sys.argv) > 4:                        # debug: short strokes along the measured fur direction
        dbg = (img * 0.6).astype(np.uint8)
        for y in range(8, img.shape[0], 12):
            for x in range(8, img.shape[1], 12):
                c = coh[y, x] * w_out[y, x] * w_whisk[y, x]
                if c < 0.25:
                    continue
                a = np.radians(ang[y, x]); dx, dy = 5 * np.cos(a), 5 * np.sin(a)
                col = (0, int(255 * min(c / 0.7, 1)), 255)
                cv2.line(dbg, (int(x - dx), int(y - dy)), (int(x + dx), int(y + dy)), col, 1, cv2.LINE_AA)
        cv2.imwrite(sys.argv[4], dbg)
