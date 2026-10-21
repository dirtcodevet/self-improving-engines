"""SLICE LOFT (domain-neutral): one closed surface from a stack of horizontal sections plus 3-D feature volumes.

Why it exists (woman2, 2026-10-19): the cat engine lofts along a body axis (`loft_y`, `loft_curve`) and blends parts
in `sdf_core`, both written around the felid spec. An upright subject photographed from the front is measured ROW BY
ROW: under an orthographic camera every image row IS a horizontal slice, so the photo hands over the x-extent of every
part in every slice directly (torso run, arm runs), and only the depth (y) has to come from priors. This tool turns
such per-slice section polygons into one signed-distance volume, unions them per slice with a per-slice blend radius
(wide where parts should merge, zero where the photo shows a gap, so no webbing), adds analytic 3-D feature volumes
(union / smooth union / smooth subtraction), caps the stack with planes, and meshes it once (J1 lofted sections,
layered-build.md "the skin is computed once from the union").

  slice field   for each slice z: each polygon -> exact unsigned distance (KD-tree over the polygon resampled at
                <= RESAMPLE_FRAC of the voxel) with the sign from an exact point-in-polygon test; parts combined by
                polynomial smooth-min with the slice's k (k = 0 -> hard min).
  features      callables f(X, Y, z) -> signed distance (mm) on the slice grid, each with an op and its k(z).
  caps          planes z <= z_top, z >= z_bot by a smooth max (k_cap) so the cut is flat and clean.
  mesh          skimage marching cubes at level 0; the largest component kept (every other component reported);
                orientation forced outward (signed volume > 0).

Units: mm in, mm out. Memory: one float32 volume (nx*ny*nz*4 bytes) plus marching-cubes working space.

Python API: build(slices_fn, grid, features=(), caps=None) -> dict(v, f, info)
  slices_fn(z) -> list of dict(poly=(n,2) array [x, y] closed CCW or CW, k=float)   (k: blend with the previous union)
  grid = dict(x=(x0, x1), y=(y0, y1), z=(z0, z1), h=voxel_mm)
"""
import time

import numpy as np
from matplotlib.path import Path
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

RESAMPLE_FRAC = 0.25   # polygon resampled at <= 1/4 voxel: the nearest-sample distance then over-reads the true
                       # point-to-segment distance by < h^2/(8*R) and by at most h/8 at a sample midpoint (exact enough
                       # for the zero crossing, which is what marching cubes interpolates)


def smin(a, b, k):
    """polynomial smooth minimum (k in mm); k <= 0 -> min"""
    if np.all(np.asarray(k) <= 0):
        return np.minimum(a, b)
    k = np.maximum(np.asarray(k, float), 1e-9)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def resample_closed(poly, step):
    P = np.asarray(poly, float)
    if np.allclose(P[0], P[-1]):
        P = P[:-1]
    Q = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    out = []
    for i in range(len(P)):
        n = max(1, int(np.ceil(seg[i] / step)))
        t = np.arange(n)[:, None] / n
        out.append(Q[i] + t * (Q[i + 1] - Q[i]))
    return np.vstack(out)


def poly_sdf(poly, XY, h):
    """signed distance (negative inside) of points XY (m,2) to a closed polygon"""
    S = resample_closed(poly, RESAMPLE_FRAC * h)
    d, _ = cKDTree(S).query(XY, workers=-1)
    inside = Path(np.vstack([poly, poly[:1]])).contains_points(XY)
    return np.where(inside, -d, d)


def taubin(v, f, iters=6, lam=0.5, mu=-0.53):
    """Taubin lambda|mu smoothing with the uniform Laplacian: removes marching-cubes terracing without the shrinkage
    of plain Laplacian smoothing (Taubin 1995). Boundary-free closed meshes only."""
    from scipy.sparse import coo_matrix, diags
    n = len(v)
    E = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]
    A = coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(n, n)).tocsr()
    A = ((A + A.T) > 0).astype(float)
    deg = np.asarray(A.sum(1)).ravel(); Dinv = diags(1 / np.maximum(deg, 1))
    W = Dinv @ A
    v = v.copy()
    for _ in range(iters):
        v = v + lam * (W @ v - v)
        v = v + mu * (W @ v - v)
    return v


def build(slices_fn, grid, features=(), caps=None, smooth_sigma_vox=0.0, quiet=False, taubin_iters=0):
    from skimage import measure
    t0 = time.time()
    h = float(grid["h"])
    xs = np.arange(grid["x"][0], grid["x"][1] + h / 2, h)
    ys = np.arange(grid["y"][0], grid["y"][1] + h / 2, h)
    zs = np.arange(grid["z"][0], grid["z"][1] + h / 2, h)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    XY = np.c_[X.ravel(), Y.ravel()]
    vol = np.empty((len(xs), len(ys), len(zs)), np.float32)
    far = 4.0 * h
    for k, z in enumerate(zs):
        parts = slices_fn(z)
        F = None
        for p in parts:
            if p["poly"] is None or len(p["poly"]) < 3:
                continue
            d = poly_sdf(np.asarray(p["poly"], float), XY, h).reshape(X.shape)
            F = d if F is None else smin(F, d, p.get("k", 0.0))
        if F is None:
            F = np.full(X.shape, 1e3)
        for feat in features:
            g = feat["fn"](X, Y, z)
            if g is None:
                continue
            kk = feat.get("k", 0.0)
            kk = kk(z) if callable(kk) else kk
            if feat["op"] == "union":
                F = smin(F, g, kk)
            elif feat["op"] == "subtract":
                F = smax(F, -g, kk)
            elif feat["op"] == "intersect":
                F = smax(F, g, kk)
        if caps:
            kc = caps.get("k", 0.0)
            F = smax(F, np.full(X.shape, z - caps["z_top"]), kc)
            F = smax(F, np.full(X.shape, caps["z_bot"] - z), kc)
        vol[:, :, k] = F
        if not quiet and k % 50 == 0:
            print(f"  slice {k}/{len(zs)} z={z:.1f} ({time.time() - t0:.0f} s)", flush=True)
    vol[0], vol[-1], vol[:, 0], vol[:, -1], vol[:, :, 0], vol[:, :, -1] = far, far, far, far, far, far   # closed by construction
    if smooth_sigma_vox > 0:
        vol = ndi.gaussian_filter(vol, smooth_sigma_vox).astype(np.float32)
    v, f, n, _ = measure.marching_cubes(vol, 0.0, spacing=(h, h, h))
    v += np.array([xs[0], ys[0], zs[0]])
    del vol
    # components
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    E = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]
    A = coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(len(v), len(v)))
    nc, lab = connected_components(A, directed=False)
    sizes = np.bincount(lab[f[:, 0]], minlength=nc)
    keep = int(np.argmax(sizes))
    dropped = sorted([int(s) for i, s in enumerate(sizes) if i != keep and s > 0], reverse=True)
    fm = f[lab[f[:, 0]] == keep]
    used = np.unique(fm); remap = np.full(len(v), -1, np.int64); remap[used] = np.arange(len(used))
    v, f = v[used], remap[fm]
    if taubin_iters:
        v = taubin(v, f, taubin_iters)
    T = v[f]; vol6 = np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])).sum()
    if vol6 < 0:
        f = f[:, ::-1].copy()
    info = dict(h_mm=h, grid_shape=[len(xs), len(ys), len(zs)], verts=int(len(v)), faces=int(len(f)),
                components=int(nc), dropped_component_faces=dropped[:10], volume_cm3=float(abs(vol6) / 6 / 1000),
                seconds=round(time.time() - t0, 1))
    return dict(v=v, f=f.astype(np.int64), info=info)
