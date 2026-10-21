"""SURFACE ANALYSIS by numbers (the person, 2026-10-19: "Everything we're building is mathematically quantifiable ... let
math carry the day"). Measures one region of a mesh directly from its vertices, in the region's own frame:

  - mean curvature H at every vertex (cotangent Laplacian), in 1/m;
  - flat spots: where H drops well below its own neighbourhood (H / H smoothed over ~20 mm), with area and place;
  - dents and bulges: signed distance (mm) from a smoothed copy of the surface, band-passed so the region's overall
    convexity cancels (smoothed at ~10 mm minus smoothed at ~30 mm);
  - meridian profiles: H along lines running out from a centre point (e.g. the nipple) at chosen angles;
  - fine texture: RMS of the surface's high-frequency relief (vs a lightly smoothed copy) and the vertex spacing, which
    bounds the finest relief the mesh itself can hold.

usage: python surface_analysis.py <skin.npz> <region_key> <side:+x|-x|all> <centre_key> <out_prefix>
  skin.npz holds v, f and per-vertex weights (region_key, centre_key) as in engine/packs/human/base_female_torso/v2.
Frame: x = subject's left, y = back, z = up (metres). Angles in the output: 0 = lateral (toward the arm), 90 = up,
180 = medial, 270 = down, seen from the front.
"""
import json
import sys

import numpy as np
from scipy import sparse


import os as _os_mg, sys as _sys_mg  # noqa: E402  (build A1: the engine's one closest point, normals, cotangent Laplacian)
_MG_DIR = _os_mg.path.normpath(_os_mg.path.join(_os_mg.path.dirname(_os_mg.path.abspath(__file__)), '.'))
if _MG_DIR not in _sys_mg.path:
    _sys_mg.path.append(_MG_DIR)
import mesh_geom as _MG  # noqa: E402


def cot_laplacian(V, F):
    return _MG.cot_laplacian(V, F, clamp=False)


def vertex_normals(V, F):
    return _MG.vertex_normals(V, F, eps=1e-20)


def umbrella(V, F):
    n = len(V); e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    A = sparse.coo_matrix((np.ones(len(e) * 2), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    deg = np.asarray(A.sum(1)).ravel()
    return sparse.diags(1 / np.maximum(deg, 1)) @ A


def smooth(X, M, iters):
    for _ in range(iters):
        X = 0.5 * X + 0.5 * (M @ X)
    return X


def main():
    path, key, side, ckey, out = sys.argv[1:6]
    z = np.load(path); V, F = z["v"].astype(np.float64), z["f"]
    cen = z[ckey] > 0.5
    cen &= (V[:, 0] > 0) if side == "+x" else (V[:, 0] < 0) if side == "-x" else True
    N = vertex_normals(V, F)
    side_m = (V[:, 0] > 0) if side == "+x" else (V[:, 0] < 0) if side == "-x" else np.ones(len(V), bool)
    if N[(z[key] > 0.5) & side_m, 1].mean() > 0: N = -N       # outward = toward the front for a front region
    tip0 = V[cen][np.argmin(V[cen][:, 1])]
    arm = z["arm_limb"] > 0.5 if "arm_limb" in z.files else np.zeros(len(V), bool)
    sel = side_m & (N[:, 1] < -0.15) & ~arm & (np.hypot(V[:, 0] - tip0[0], V[:, 2] - tip0[2]) < 0.105)
    L, area = cot_laplacian(V, F)
    Hn = -(L @ V) / (2 * np.maximum(area, 1e-20))[:, None]
    H = np.einsum("ij,ij->i", Hn, N)                          # > 0 convex (bulging out)
    M = umbrella(V, F)
    edge = np.linalg.norm(V[F[:, 0]] - V[F[:, 1]], axis=1).mean()
    it = lambda mm: max(1, int((mm / 1000 / edge) ** 2))      # diffusion iterations for a smoothing radius in mm
    H = smooth(H.copy(), M, it(5))                             # 5 mm: read curvature above mesh noise
    Hs = smooth(H.copy(), M, it(20))
    ratio = H / np.where(np.abs(Hs) > 1e-6, Hs, np.nan)
    S10, S30 = smooth(V.copy(), M, it(10)), smooth(V.copy(), M, it(30))
    band = np.einsum("ij,ij->i", (S10 - S30), N) * 1000       # mm; bulge (+) / dent or flat (-) at 1-3 cm scale
    S2 = smooth(V.copy(), M, max(2, it(1.5)))
    fine = np.einsum("ij,ij->i", (V - S2), N) * 1000          # mm; fine relief
    # frame: axis = mean outward normal of the region, origin at the centre point's most forward vertex
    axis = N[sel].mean(0); axis /= np.linalg.norm(axis)
    tip = V[cen][np.argmax(V[cen] @ axis)]
    lat = np.array([1.0 if side != "-x" else -1.0, 0, 0]); lat -= axis * (lat @ axis); lat /= np.linalg.norm(lat)
    up = np.cross(axis, lat); up *= np.sign(up[2]) if up[2] != 0 else 1
    d = V[sel] - tip; u, v = d @ lat, d @ up; r = np.hypot(u, v); th = np.degrees(np.arctan2(v, u)) % 360
    h = d @ axis                                                # height along the region's axis
    fit_m = (r > 0.022) & (r < 0.100)                           # outside the nipple-areola complex
    U, W_ = u / 0.1, v / 0.1
    A = np.stack([U ** i * W_ ** j for i in range(7) for j in range(7 - i)], 1)
    coef, *_ = np.linalg.lstsq(A[fit_m], h[fit_m], rcond=None)
    band_sel = (h - A @ coef) * 1000                            # mm vs a smooth 6th-order dome (about 2 cm smoothing scale)
    band[sel] = band_sel
    Hsel, Rsel, Bsel = H[sel], ratio[sel], band[sel]
    a = area[sel]
    flat = (Rsel < 0.5) & (r > 0.022) & (r < 0.100)            # outside the nipple-areola complex
    out_j = {"region": key, "side": side, "vertices": int(sel.sum()), "mean_edge_mm": round(edge * 1000, 3),
             "H_median_per_m": round(float(np.median(Hsel)), 2),
             "flat_spots": {"area_cm2": round(float(a[flat].sum() * 1e4), 2),
                            "share_of_region_pct": round(float(a[flat].sum() / a.sum() * 100), 2)},
             "band_mm": {k_: round(float(f_(Bsel[fit_m])), 3) for k_, f_ in (("min", np.min), ("p1", lambda x: np.percentile(x, 1)),
                         ("p99", lambda x: np.percentile(x, 99)), ("max", np.max), ("rms", lambda x: np.sqrt(np.mean(x ** 2))))},
             "fine_relief_rms_mm": round(float(np.sqrt(np.mean(fine[sel] ** 2))), 4),
             "by_direction": {}}
    for name, c in (("lateral", 0), ("up", 90), ("medial", 180), ("down", 270)):
        m = (np.abs(((th - c + 180) % 360) - 180) < 22.5) & fit_m
        if m.sum() < 10: continue
        out_j["by_direction"][name] = {
            "H_median_per_m": round(float(np.median(Hsel[m])), 2),
            "flat_area_cm2": round(float(a[m & flat].sum() * 1e4), 2),
            "band_min_mm": round(float(Bsel[m].min()), 3),
            "where_band_min": {"r_mm": round(float(r[m][np.argmin(Bsel[m])] * 1000), 1),
                               "angle_deg": round(float(th[m][np.argmin(Bsel[m])]), 1)}}
    json.dump(out_j, open(out + ".json", "w"), indent=1)
    plot(u, v, Hsel, Rsel, Bsel, r, th, out_j, out + ".png")
    print(json.dumps(out_j, indent=1))


def plot(u, v, H, R, B, r, th, j, path):
    keep = r > 0.022; u, v, H, R, B, r, th = u[keep], v[keep], H[keep], R[keep], B[keep], r[keep], th[keep]
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 4, figsize=(22, 5.6))
    kw = dict(s=1.2, rasterized=True)
    for k, (val, lim, cmap, title) in enumerate(((H, (np.percentile(H, 2), np.percentile(H, 98)), "viridis", "mean curvature H (1/m): dark = flatter"),
                                                  (np.clip(R, 0, 1.5), (0, 1.5), "RdYlGn", "H / its 2 cm neighbourhood: red = flat spot"),
                                                  (B, (-1.0, 1.0), "RdBu_r", "vs smooth dome, mm: blue = flat/dented, red = bulging"))):
        sc = ax[k].scatter(u * 1000, v * 1000, c=val, vmin=lim[0], vmax=lim[1], cmap=cmap, **kw)
        ax[k].set_aspect("equal"); ax[k].set_title(title, fontsize=10); plt.colorbar(sc, ax=ax[k], fraction=0.046)
        ax[k].set_xlabel("mm (from the nipple; arm side on the RIGHT, as seen from the front)")
    for name, c, col in (("lateral (arm side)", 0, "tab:red"), ("up", 90, "tab:blue"), ("medial", 180, "tab:green"), ("down", 270, "tab:orange")):
        m = (np.abs(((th - c + 180) % 360) - 180) < 8)
        o = np.argsort(r[m]); rr, hh = r[m][o] * 1000, H[m][o]
        if len(rr) > 30:
            k = 15; hh = np.convolve(hh, np.ones(k) / k, mode="same")
            ax[3].plot(rr, hh, color=col, label=name)
    ax[3].set_xlabel("distance from the nipple (mm)"); ax[3].set_ylabel("H (1/m)"); ax[3].legend(); ax[3].set_title("curvature along four meridians", fontsize=10)
    fig.suptitle(f"{j['side']} breast: flat spots {j['flat_spots']['area_cm2']} cm2 ({j['flat_spots']['share_of_region_pct']} %), "
                 f"vs smooth dome min {j['band_mm']['min']} / max {j['band_mm']['max']} mm (RMS {j['band_mm']['rms']}), fine relief RMS {j['fine_relief_rms_mm']} mm, vertex spacing {j['mean_edge_mm']} mm", fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=90)


if __name__ == "__main__":
    main()
