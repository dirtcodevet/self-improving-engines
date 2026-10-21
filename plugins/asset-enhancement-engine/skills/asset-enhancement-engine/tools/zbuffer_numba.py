"""Z-BUFFER (numba): the per-pixel front face id, depth and first-exit depth of a triangle mesh through a camera.

Why it exists (woman2, 2026-10-19): engine/checks/object_checks.rasterize is the proven measuring instrument, but it
loops over triangles in Python (fine for the rock's few thousand facets, minutes for a 0.5-1.5 M triangle body). This is
the same definition, compiled: the same Camera (object_checks.Camera: R, t, fx, fy, cx, cy, ortho), the same pixel-centre
convention (pixel (col,row) centre at (col + 0.5, row + 0.5)), the same front/back-facing rule and barycentric inside
test (w >= 0), the same depth interpolation (linear for ortho, perspective-correct otherwise). Proof: `prove()`
compares it with object_checks.rasterize on a planted mesh (identical face ids except at exact ties, depths to 1e-9).

  rasterize(v, f, cam) -> dict(face, zfront, zexit, mask)   (same keys as object_checks.rasterize)
"""
import os
import sys

import numpy as np
from numba import njit, prange

HERE = os.path.dirname(os.path.abspath(__file__))


@njit(cache=True)
def _raster(T, front, W, H, ortho, zf, ze, fid):
    for i in range(T.shape[0]):
        u0, v0, z0 = T[i, 0, 0], T[i, 0, 1], T[i, 0, 2]
        u1, v1, z1 = T[i, 1, 0], T[i, 1, 1], T[i, 1, 2]
        u2, v2, z2 = T[i, 2, 0], T[i, 2, 1], T[i, 2, 2]
        A = (u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)
        if abs(A) < 1e-12:
            continue
        x0 = max(int(np.floor(min(u0, min(u1, u2)) - 0.5)), 0)
        x1 = min(int(np.ceil(max(u0, max(u1, u2)) - 0.5)), W - 1)
        y0 = max(int(np.floor(min(v0, min(v1, v2)) - 0.5)), 0)
        y1 = min(int(np.ceil(max(v0, max(v1, v2)) - 0.5)), H - 1)
        for py_i in range(y0, y1 + 1):
            py = py_i + 0.5
            for px_i in range(x0, x1 + 1):
                px = px_i + 0.5
                w0 = ((u1 - px) * (v2 - py) - (u2 - px) * (v1 - py)) / A
                w1 = ((u2 - px) * (v0 - py) - (u0 - px) * (v2 - py)) / A
                w2 = 1.0 - w0 - w1
                if w0 < 0 or w1 < 0 or w2 < 0:
                    continue
                if ortho:
                    z = w0 * z0 + w1 * z1 + w2 * z2
                else:
                    z = 1.0 / (w0 / z0 + w1 / z1 + w2 / z2)
                if front[i]:
                    if z < zf[py_i, px_i]:
                        zf[py_i, px_i] = z
                        fid[py_i, px_i] = i
                else:
                    if z < ze[py_i, px_i]:
                        ze[py_i, px_i] = z


def rasterize(v, f, cam):
    v = np.asarray(v, float); f = np.asarray(f, np.int64)
    uvz = cam.project(v); Xc = cam.to_cam(v)
    nc = np.cross(Xc[f[:, 1]] - Xc[f[:, 0]], Xc[f[:, 2]] - Xc[f[:, 0]])
    front = (nc[:, 2] < 0) if cam.ortho else (np.einsum("ij,ij->i", nc, Xc[f[:, 0]]) < 0)
    H, W = cam.H, cam.W
    zf = np.full((H, W), np.inf); ze = np.full((H, W), np.inf); fid = np.full((H, W), -1, np.int64)
    _raster(uvz[f].astype(np.float64), front, W, H, bool(cam.ortho), zf, ze, fid)
    return dict(face=fid, zfront=zf, zexit=ze, mask=fid >= 0, front_facing=front)


def prove():
    """planted mesh: two overlapping tilted boxes, perspective and ortho; must equal object_checks.rasterize"""
    sys.path.insert(0, os.path.join(HERE, "..", "checks"))
    import types
    sys.modules.setdefault("twosided", types.SimpleNamespace(MeshDist=None, area_samples=None))
    import object_checks as OC
    rng = np.random.default_rng(0)
    V, F = [], []
    for k in range(2):
        c = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], float) - 0.5
        R = np.linalg.qr(rng.normal(size=(3, 3)))[0]
        V.append(c @ R.T * 0.3 + rng.normal(size=3) * 0.05)
        q = np.array([[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]) + 8 * k
        for a, b, cc, d in q:
            F += [[a, b, cc], [a, cc, d]]
    V = np.vstack(V); F = np.array(F)
    out = {}
    for ortho in (False, True):
        cam = OC.Camera.look_at([0.2, -2.0, 0.3], [0, 0, 0], 400 if ortho else 900, 160, 120, ortho=ortho)
        a, b = OC.rasterize(V, F, cam), rasterize(V, F, cam)
        same = (a["face"] == b["face"]).mean()
        dz = np.nanmax(np.abs(np.where(np.isfinite(a["zfront"]), a["zfront"] - b["zfront"], 0)))
        out["ortho" if ortho else "persp"] = dict(face_agree=float(same), max_dz=float(dz), mask_px=int(a["mask"].sum()))
    out["pass"] = all(o["face_agree"] > 0.999 and o["max_dz"] < 1e-9 for o in out.values() if isinstance(o, dict))
    return out


if __name__ == "__main__":
    print(prove())
