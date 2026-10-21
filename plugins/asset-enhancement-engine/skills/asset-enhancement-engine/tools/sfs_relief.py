"""SFS RELIEF (domain-neutral, orthographic cameras): front relief from the photo's shading, added to ONE closed skin
as a displacement along the view axis that fades to zero at the occluding contour.

Why it exists (woman2, 2026-10-19): a front photo of a smooth subject measures its outline (x, z) directly, but the
relief INSIDE the outline (clavicles, ribs, abdominal wall, the real breast form) shows only as shading. The cat engine
filled such relief from a 3-D reference (Tripo) or from priors; with no reference and the brief "front form from
shading", the relief has to come from the photo's shading itself (G3 rank 4: indirect cue). This is a linearised
shape-from-shading on the low-pass luminance with the light fitted by engine/tools/shading_albedo.fit:

  residual    R = lowpass(photo Y_lin) - lowpass(a + b . n)      on the fit pixels (areolae / navel / edge band out)
  model       a displacement d (mm, + = toward the camera) changes the normal by -(grad d)/q (q = 1/|n . view|), so
              the shading by  dS = -(b_x d_x + b_z d_z) |n_y|  (first order; world x right, z up, view +y)
  solve       min |W (dS - R)|^2 + LAM |lap d|^2 + MU |d|^2, d = 0 outside the facing region, on a grid DOWN x coarser
              than the photo (sparse LSQR); d clipped to +-CLIP mm. What it cannot see: relief along the direction
              perpendicular to the light's image-plane component (only the Laplacian term shapes it), and albedo
              changes the low-pass keeps (they turn into false relief) - both are reported, not hidden.
  apply       v_y -= d(projected vertex) * w(facing), w = smoothstep(n.view over [W_LO, W_HI]), so the silhouette and
              the turn through the contour are untouched.

API: solve(fitres, cam, lam, mu, down) -> d_img (H, W) mm ; apply(v, f, cam, d_img, vn) -> v'
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix, diags, vstack
from scipy.sparse.linalg import lsqr

import shading_albedo as SA

CLIP = 12.0          # mm: relief, not re-shaping; larger form errors belong to the form layer
W_LO, W_HI = 0.20, 0.50


def _grad_ops(idx, shape):
    """forward differences on the masked grid (only pairs where both ends are unknowns)"""
    H, W = shape
    rows, cols, vals = [], [], []
    ops = []
    for dy, dx in ((0, 1), (1, 0)):
        a = idx[: H - dy, : W - dx]; b = idx[dy:, dx:]
        ok = (a >= 0) & (b >= 0)
        n = int(ok.sum()); r = np.arange(n)
        G = coo_matrix((np.r_[-np.ones(n), np.ones(n)], (np.r_[r, r], np.r_[a[ok], b[ok]])), shape=(n, int(idx.max()) + 1)).tocsr()
        ops.append((G, ok))
    return ops


def solve(fr, cam, b_world, lam=30.0, mu=1e-4, down=3, s_mm_per_px=None):
    rast, N, use = fr["rast"], fr["N"], fr["use"]
    lin_Y = None
    # residual on the full grid, low-passed
    S = fr["S"]
    Y = SA.srgb_to_lin(fr["rgb"]) @ np.array([0.2126, 0.7152, 0.0722])
    R = SA.lowpass(Y, use) - SA.lowpass(S, use)
    facing = np.where(rast["mask"], -(N @ cam.forward), 0.0)
    region = rast["mask"] & (facing > W_LO)
    # coarse grid
    Hc, Wc = (np.array(R.shape) + down - 1) // down
    def coarse(a, fn=np.mean):
        pad = np.zeros((Hc * down, Wc * down), a.dtype); pad[: a.shape[0], : a.shape[1]] = a
        return fn(fn(pad.reshape(Hc, down, Wc, down), axis=3), axis=1)
    Rc = coarse(np.where(use, R, 0.0)); Uc = coarse(use.astype(float)); Rc = np.where(Uc > 0, Rc / np.maximum(Uc, 1e-9), 0)
    regc = coarse(region.astype(float)) > 0.5
    nyc = coarse(np.abs(N[..., 1]) * region) / np.maximum(coarse(region.astype(float)), 1e-9)
    idx = np.full(regc.shape, -1, np.int64); idx[regc] = np.arange(regc.sum())
    n = int(regc.sum())
    step = down * s_mm_per_px                          # mm per coarse cell
    # one data row per interior cell (all 4 neighbours in the region), central differences:
    #   -b_x |n_y| d_x - b_z |n_y| d_z = R ,  d_x = (d[j+1] - d[j-1]) / 2step ,  d_z = -(d[i+1] - d[i-1]) / 2step
    bx, bz = b_world[0], b_world[2]
    ii, jj = np.nonzero(regc)
    Hc_, Wc_ = regc.shape
    inn = (ii > 0) & (ii < Hc_ - 1) & (jj > 0) & (jj < Wc_ - 1)
    ii, jj = ii[inn], jj[inn]
    nb = [idx[ii, jj + 1], idx[ii, jj - 1], idx[ii + 1, jj], idx[ii - 1, jj]]
    ok = np.all(np.stack(nb) >= 0, axis=0)
    ii, jj = ii[ok], jj[ok]; nb = [q[ok] for q in nb]
    ny = nyc[ii, jj]; m = len(ii); r = np.arange(m)
    cx_ = -bx * ny / (2 * step); cz_ = bz * ny / (2 * step)
    Ad = coo_matrix((np.r_[cx_, -cx_, cz_, -cz_], (np.r_[r, r, r, r], np.r_[nb[0], nb[1], nb[2], nb[3]])), shape=(m, n)).tocsr()
    rd = Rc[ii, jj]
    # Laplacian (5-point) for smoothness
    rows, cols, vals = [], [], []
    ii, jj = np.nonzero(regc)
    for (di, dj) in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        i2, j2 = ii + di, jj + dj
        ok = (i2 >= 0) & (i2 < regc.shape[0]) & (j2 >= 0) & (j2 < regc.shape[1])
        nb = np.full(len(ii), -1); nb[ok] = idx[i2[ok], j2[ok]]
        k = idx[ii, jj]
        rows += [k]; cols += [k]; vals += [np.full(len(k), -1.0)]
        has = nb >= 0
        rows += [k[has]]; cols += [nb[has]]; vals += [np.ones(has.sum())]
        # neighbours outside the region are d = 0 (Dirichlet): only the -1 term stays
    L = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr() / step ** 2
    A = vstack([Ad, np.sqrt(lam) * L, np.sqrt(mu) * diags(np.ones(n))]).tocsr()
    rhs = np.r_[rd, np.zeros(n), np.zeros(n)]
    sol = lsqr(A, rhs, atol=1e-8, btol=1e-8, iter_lim=4000)[0]
    dc = np.zeros(regc.shape); dc[regc] = np.clip(sol, -CLIP, CLIP)
    d = ndi.zoom(dc, down, order=1)[: R.shape[0], : R.shape[1]]
    d = ndi.gaussian_filter(d, down)                   # undo the coarse-grid blockiness
    d *= region
    return d, dict(unknowns=n, step_mm=step, lam=lam, mu=mu, down=down, d_min=float(dc.min()), d_max=float(dc.max()),
                   d_rms=float(np.sqrt((dc[regc] ** 2).mean())))


def apply(v, f, cam, d_img, vn):
    v = np.asarray(v, float).copy()
    uvz = cam.project(v); H, W = d_img.shape
    col = np.clip(uvz[:, 0] - 0.5, 0, W - 1.001); row = np.clip(uvz[:, 1] - 0.5, 0, H - 1.001)
    d = ndi.map_coordinates(d_img, [row, col], order=1)
    facing = -(vn @ cam.forward)
    w = np.clip((facing - W_LO) / (W_HI - W_LO), 0, 1); w = w * w * (3 - 2 * w)
    # front-visible only: vertices on the far side face away (w = 0) already
    v -= (d * w / 1000.0)[:, None] * cam.forward[None, :]     # + d = toward the camera (metres)
    return v, dict(moved=int((np.abs(d * w) > 0.05).sum()), max_mm=float(np.abs(d * w).max()))
