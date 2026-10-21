"""BACKDROP MASK (domain-neutral): mask of a SMOOTH, coloured subject on a plain, near-neutral studio backdrop, plus the
split of each image row into its foreground RUNS (left to right), with an independent edge validation.

Why it exists (woman2, 2026-10-19): the engine's two mask tools did not fit a smooth subject cut by the frame.
`ref_mask.py` fits its backdrop on fixed border bands (top 60 rows, 120 columns each side), and a subject cut by the
top and bottom of the frame puts skin into those bands; `studio_photo_fit.py` separates object from sweep by TEXTURE
energy (rock grain), and skin has none. This tool separates by COLOUR DISTANCE from a fitted backdrop instead.

  backdrop   per channel, a 2nd-order polynomial in (u, v) fitted to near-neutral pixels (chroma <= NEUTRAL_CHROMA, i.e.
             pixels the subject cannot own when the subject is coloured); iterated once with residual rejection.
  mask       CIE76 dE between the pixel and the fitted backdrop at that pixel (Lab, both) >= DE_FG -> sure foreground
             seeds; dE <= DE_BG -> sure background; GrabCut decides the band between; holes filled; components smaller
             than MIN_COMP_FRAC of the largest dropped.
  runs       for every row, the [start, end] columns of each foreground run longer than MIN_RUN px (left to right).
  validate   independent 1-D step-edge crossings (half level between the backdrop and the subject medians, from the
             OUTSIDE) on scanlines chosen by the caller BEFORE the mask is seen, against the mask boundary: median and p95
             of |crossing - mask edge| in px (studio_photo_checks H4's definition, reused as a method).

Settings are stated with their reasons below; none is tuned on a held-out answer.

usage: python backdrop_mask.py <photo> <out_dir> [--scanlines rows.json]
  writes <out_dir>/mask.png, runs.json, mask_report.json
"""
import argparse
import json
import os

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

NEUTRAL_CHROMA = 6.0   # Lab chroma; a grey backdrop sits at 0-3 (JPEG/PNG noise), coloured subjects at >= 15 (skin 20-35)
DE_FG = 20.0           # dE from the backdrop that only the subject reaches (backdrop residual dE is ~1-3)
DE_BG = 6.0            # dE below which a pixel is backdrop for GrabCut (3x the backdrop residual)
MIN_COMP_FRAC = 0.01   # specks: components under 1 % of the largest are noise
MIN_RUN = 4            # px; a run shorter than this is a mask speck, not a part
GC_ITERS = 4


def srgb_to_lab(rgb):
    """rgb in [0,1] (..., 3) -> CIE Lab (D65)"""
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def fit_backdrop(rgb):
    H, W, _ = rgb.shape
    lab = srgb_to_lab(rgb)
    chroma = np.hypot(lab[..., 1], lab[..., 2])
    cand = chroma <= NEUTRAL_CHROMA
    yy, xx = np.mgrid[0:H, 0:W]
    xn, yn = xx / W, yy / H
    A = np.stack([np.ones_like(xn), xn, yn, xn * xn, yn * yn, xn * yn], -1)
    bg = np.zeros_like(rgb)
    keep = cand.copy()
    for it in range(2):
        for c in range(3):
            coef, *_ = np.linalg.lstsq(A[keep], rgb[..., c][keep], rcond=None)
            bg[..., c] = A @ coef
        res = np.abs(rgb - bg).max(-1)
        thr = max(3 * np.median(res[keep]), 2 / 255)
        keep = cand & (res <= thr)
    return bg, keep, lab, chroma


def make_mask(rgb):
    bg, used, lab, chroma = fit_backdrop(rgb)
    de = np.linalg.norm(lab - srgb_to_lab(bg), axis=-1)
    gc = np.full(de.shape, cv2.GC_PR_BGD, np.uint8)
    gc[de >= DE_FG] = cv2.GC_FGD
    gc[(de >= DE_BG) & (de < DE_FG)] = cv2.GC_PR_FGD
    gc[de < DE_BG] = cv2.GC_BGD
    img8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)[..., ::-1].copy()
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(img8, gc, None, bgd, fgd, GC_ITERS, cv2.GC_INIT_WITH_MASK)
    m = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)
    m = ndi.binary_fill_holes(m)
    lab_c, n = ndi.label(m)
    if n > 1:
        sizes = ndi.sum(m, lab_c, range(1, n + 1))
        m = np.isin(lab_c, 1 + np.flatnonzero(sizes >= MIN_COMP_FRAC * sizes.max()))
    resid = float(np.median(de[used]))
    return m, de, dict(backdrop_pixels=int(used.sum()), backdrop_median_dE=round(resid, 3),
                       seed_fg=int((de >= DE_FG).sum()), band=int(((de >= DE_BG) & (de < DE_FG)).sum()))


def row_runs(m, min_run=MIN_RUN):
    out = []
    for r in range(m.shape[0]):
        row = m[r].astype(np.int8)
        d = np.diff(np.r_[0, row, 0])
        s, e = np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1
        out.append([[int(a), int(b)] for a, b in zip(s, e) if b - a + 1 >= min_run])
    return out


def step_crossings(lum, m, rows, side_win=12, inner=(6, 18)):
    """For each pre-chosen row: walking in from each image side, the sub-pixel column where the luminance profile
    crosses the half level between the outside plateau and the inside median; compared with the mask's first/last
    foreground column. Uses the photo only (not the mask) to find the crossing; the mask only names which run."""
    errs = []
    for r in rows:
        prof = lum[r]
        cols = np.flatnonzero(m[r])
        if len(cols) == 0:
            continue
        for side in (0, 1):
            edge = cols[0] if side == 0 else cols[-1]
            p = prof if side == 0 else prof[::-1]
            e = edge if side == 0 else len(prof) - 1 - edge
            lo0, lo1 = max(0, e - side_win - 8), max(1, e - 8)
            hi0, hi1 = e + inner[0], e + inner[1]
            if lo1 - lo0 < 3 or hi1 >= len(p):
                continue
            out_m, in_m = np.median(p[lo0:lo1]), np.median(p[hi0:hi1])
            if abs(out_m - in_m) < 0.04:
                continue
            lev = 0.5 * (out_m + in_m)
            sgn = np.sign(out_m - in_m)
            x = None
            for i in range(lo0, hi1):
                if sgn * (p[i] - lev) >= 0 > sgn * (p[i + 1] - lev):
                    x = i + (p[i] - lev) / (p[i] - p[i + 1])
                    break
            if x is None:
                continue
            # mask edge as a boundary position: first fg pixel's left side = e - 0.5 + 0.5 (pixel centre convention)
            errs.append(dict(row=int(r), side="left" if side == 0 else "right", crossing=float(x), mask_edge=float(e - 0.5),
                             err_px=float(abs(x - (e - 0.5)))))
    d = np.array([q["err_px"] for q in errs]) if errs else np.array([np.inf])
    return dict(n=len(errs), median_px=float(np.median(d)), p95_px=float(np.percentile(d, 95)), max_px=float(d.max()),
                worst=sorted(errs, key=lambda q: -q["err_px"])[:5])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo"); ap.add_argument("out_dir"); ap.add_argument("--scanlines", default=None)
    a = ap.parse_args()
    rgb = np.asarray(Image.open(a.photo).convert("RGB")).astype(np.float64) / 255.0
    m, de, info = make_mask(rgb)
    os.makedirs(a.out_dir, exist_ok=True)
    Image.fromarray((m * 255).astype(np.uint8)).save(os.path.join(a.out_dir, "mask.png"))
    runs = row_runs(m)
    json.dump(runs, open(os.path.join(a.out_dir, "runs.json"), "w"))
    rep = dict(tool="engine/tools/backdrop_mask.py", settings=dict(NEUTRAL_CHROMA=NEUTRAL_CHROMA, DE_FG=DE_FG, DE_BG=DE_BG,
               MIN_COMP_FRAC=MIN_COMP_FRAC, MIN_RUN=MIN_RUN), info=info, fg_px=int(m.sum()))
    if a.scanlines:
        sl = json.load(open(a.scanlines)); rows = sl["rows"] if "rows" in sl else sl["mask_scanlines"]["rows"]
        lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
        rep["edge_validation"] = step_crossings(lum, m, rows)
    json.dump(rep, open(os.path.join(a.out_dir, "mask_report.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1)[:1500])


if __name__ == "__main__":
    main()
