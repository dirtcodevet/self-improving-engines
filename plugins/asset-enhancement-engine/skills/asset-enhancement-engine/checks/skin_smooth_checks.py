"""skin_smooth_checks (C3b, Phase 2 Stage 2): is the skin SMOOTH under the fur? Kept from the skin-fix round's scratch
tools (%TEMP%/p2_skin-fix/vchecks.py), made general for the skin-v2 build. Three measures, each proven on a planted failure
(A10) every time it runs:

  rings  (V1)  coat depth d along SKIN paths: 12 azimuths about each leg centre (partition.leg_centre), z 4-150 mm, the
               path's radius smoothed over 5 mm; d' and d'' by central differences over +-2 mm. Pass |d''| <= 0.02 per mm
               and |d'| <= 0.15. The upper part of every path (z 120-150) runs onto the trunk, so the trunk's ventral /
               flank blend is read there too ('trunk' = z > 115 mm part of the same paths).
               PLANT: d + a 1.0 mm cubic-smoothstep step over 10 mm at z = 60 mm (the v1 ring mechanism) must FAIL.
  relief (V2)  groove-band relief on the skin: r = (V - smooth60(V)) . n, minus its smooth240 (wavelengths ~1.4-6 mm),
               RMS by depth class. PLANT: a 0.05 mm-amplitude sinusoid of 1.9 mm (Tripo's fur grooves) and 5 mm
               wavelength on a 10 mm patch of the back must be recovered (added RMS ~0.035 mm).
  eyes   (V3)  the step at the bare eye: skin-to-Tripo distance (signed, + = skin inside) on skin vertices binned by 2-D
               distance to the eye mask's margin (coat_field.MASKS['eyes'] r) from -1 to 12 mm; step = the largest
               change between neighbouring 1 mm bins of the median inset. Goggle eyes = a step of ~2 mm at the margin.
               PLANT: the measured profile + 1.5 mm outside the margin must give a step >= 1.5 mm.

usage: python skin_smooth_checks.py <skin.npz> [--ref <skin_ref.npz>] [--out json]
"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.normpath(os.path.join(HERE, "..", "..", "tripo_rebuild")); FEL = os.path.normpath(os.path.join(HERE, "..", "packs", "felid"))
sys.path.insert(0, TR); sys.path.insert(0, FEL)
import coat_field as CF  # noqa: E402
import partition as PT  # noqa: E402

D2_MARK, D1_MARK = 0.02, 0.15
EYE_STEP_MARK = 0.5     # mm between neighbouring 1 mm bins (C3 tolerance)


def ss(t):
    t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)


# ------------------------------------------------------------------------------------------------ rings (V1)
def leg_paths(P, k, nth=12, zs=np.arange(0.004, 0.150, 0.001)):
    cx, cy = PT.leg_centre(k, P[:, 2]); dx, dy = P[:, 0] - cx, P[:, 1] - cy; r = np.hypot(dx, dy); th = np.arctan2(dy, dx)
    m = r < 0.030; ib = np.floor((th + np.pi) / (2 * np.pi) * nth).astype(int) % nth; iz = np.round((P[:, 2] - zs[0]) / 0.001).astype(int)
    ok = m & (iz >= 0) & (iz < len(zs)); key = ib[ok] * len(zs) + iz[ok]
    s = np.bincount(key, r[ok], nth * len(zs)); c = np.bincount(key, None, nth * len(zs))
    R = (s / np.maximum(c, 1)).reshape(nth, len(zs)); R[c.reshape(nth, len(zs)) < 2] = np.nan
    return zs, R


def path_points(V, k, nth=12):
    zs, Rs = leg_paths(V, k, nth); out = []
    for t in range(nth):
        r = Rs[t]
        if np.isnan(r).mean() > 0.3:
            continue
        r = np.interp(zs, zs[~np.isnan(r)], r[~np.isnan(r)]); r = np.convolve(np.pad(r, 2, mode="edge"), np.ones(5) / 5, "valid")
        th = -np.pi + (t + 0.5) * 2 * np.pi / nth; cx, cy = PT.leg_centre(k, zs)
        out.append(np.c_[cx + r * np.cos(th), cy + r * np.sin(th), zs])
    return zs, out


def derivs(d, zs, zlo=0.0, zhi=1.0, h=2):
    d1 = (d[:, 2 * h:] - d[:, :-2 * h]) / (2 * h); d2 = (d[:, 2 * h:] - 2 * d[:, h:-h] + d[:, :-2 * h]) / h ** 2
    zz = zs[h:-h]; m = (zz >= zlo) & (zz <= zhi); d1, d2, zz = d1[:, m], d2[:, m], zz[m]
    j = np.unravel_index(np.abs(d2).argmax(), d2.shape)[1]
    return dict(max_abs_d1=round(float(np.abs(d1).max()), 4), max_abs_d2_per_mm=round(float(np.abs(d2).max()), 4), z_at_max_d2_mm=round(float(zz[j] * 1000), 1))


def rings(V, depth_fn=CF.depth_mm, plant=False):
    res = {}
    for k in PT.LEGS:
        zs, paths = path_points(V, k)
        d = np.array([depth_fn(P) for P in paths])
        if plant:
            d = d + 1.0 * ss((zs[None, :] - 0.055) / 0.010)
        leg, trunk = derivs(d, zs, 0, 0.115), derivs(d, zs, 0.115, 1.0)
        res[k] = dict(leg_z_le_115=leg, trunk_z_gt_115=trunk,
                      passes=bool(max(leg["max_abs_d2_per_mm"], trunk["max_abs_d2_per_mm"]) <= D2_MARK and max(leg["max_abs_d1"], trunk["max_abs_d1"]) <= D1_MARK))
    return res


# ------------------------------------------------------------------------------------------------ relief (V2)
def relief_ops(V, F):
    from scipy.sparse import coo_matrix, diags
    nv = len(V); I = np.r_[F[:, 0], F[:, 1], F[:, 2], F[:, 1], F[:, 2], F[:, 0]]; J = np.r_[F[:, 1], F[:, 2], F[:, 0], F[:, 0], F[:, 1], F[:, 2]]
    A = coo_matrix((np.ones(len(I)), (I, J)), shape=(nv, nv)).tocsr(); A.data[:] = 1.0
    return diags(1.0 / np.maximum(np.asarray(A.sum(1)).ravel(), 1)) @ A


def band_relief(Vx, N, Wn):
    def smooth(X, it, lam=0.5):
        for _ in range(it):
            X = X + lam * (Wn @ X - X)
        return X
    Sb = smooth(Vx, 60); r = np.einsum("ij,ij->i", Vx - Sb, N); return (r - smooth(r[:, None], 240)[:, 0]) * 1000


def _st(r, m):
    return dict(n=int(m.sum()), rms_mm=round(float(np.sqrt(np.mean(r[m] ** 2))), 4) if m.any() else None,
                p95_abs_mm=round(float(np.percentile(np.abs(r[m]), 95)), 4) if m.any() else None)


def relief(V, F, N, dv, prove=True):
    Wn = relief_ops(V, F); r = band_relief(V, N, Wn)
    out = dict(fur_d_gt_1p5=_st(r, dv > 1.5), fur_d_gt_3=_st(r, dv > 3), furless_d_lt_0p2=_st(r, dv < 0.2),
               back_z_gt_120=_st(r, (dv > 1.5) & (V[:, 2] > 0.12)), legs_z_lt_90=_st(r, (dv > 1.5) & (V[:, 2] < 0.09)))
    if prove:
        c = V[(dv > 1.5) & (V[:, 2] > 0.12)][0]; pm = np.linalg.norm(V - c, axis=1) < 0.010
        pr = dict(patch_clean=_st(r, pm), expected_added_rms_mm=round(0.05 / np.sqrt(2), 4))
        for lam in (0.0019, 0.005):
            Vp = V.copy(); Vp[pm] += (0.00005 * np.sin(2 * np.pi * V[pm, 1] / lam))[:, None] * N[pm]
            rp = band_relief(Vp, N, Wn); rec = float(np.sqrt(np.mean((rp[pm] - r[pm]) ** 2)))
            pr[f"recovered_rms_{lam * 1000:.1f}mm"] = round(rec, 4)
        pr["proven"] = bool(all(pr[f"recovered_rms_{l}mm"] > 0.5 * pr["expected_added_rms_mm"] for l in ("1.9", "5.0")))
        out["proof"] = pr
    return out


# ------------------------------------------------------------------------------------------------ eyes (V3)
def eye_profile(V, md):
    """median signed skin-to-Tripo inset (mm, + = skin inside) by 2-D margin distance; md = twosided.MeshDist(Tripo)"""
    Lh = PT.head_local(V); prof = {}
    for s, Me in zip(("eye.L", "eye.R"), CF.MASKS["eyes"]):
        b = np.all((Lh >= Me["box"][0] - 0.006) & (Lh <= Me["box"][1] + 0.006), axis=1); q = Lh[b] - Me["c"]
        dd = Me["r"](np.c_[q @ Me["e1"], q @ Me["e2"]]) * 1000; sn = q @ Me["n"] * 1000; sel = (sn > -10) & (sn < 6)
        P = V[b][sel]; dd = dd[sel]
        du, sd = md(P); ins = -np.asarray(sd) * 1000        # MeshDist signed: + outside Tripo
        rows = []
        for a in np.arange(-1, 12, 1.0):
            m = (dd >= a) & (dd < a + 1)
            if m.sum() > 3:
                rows.append([float(a), int(m.sum()), round(float(np.median(ins[m])), 3)])
        prof[s] = rows
    return prof


def eye_step(prof, plant=0.0):
    out = {}
    for s, rows in prof.items():
        a = np.array([r[0] for r in rows]); m = np.array([r[2] for r in rows]) + plant * (a >= 0)
        st = np.abs(np.diff(m)); j = int(st.argmax()) if len(st) else 0
        out[s] = dict(max_step_mm=round(float(st.max()), 3) if len(st) else None, between_mm=[float(a[j]), float(a[j] + 1)] if len(st) else None,
                      inset_at_margin_mm=float(m[a == 0][0]) if (a == 0).any() else None,
                      inset_3_4mm=float(m[a == 3][0]) if (a == 3).any() else None, inset_8_9mm=float(m[a == 8][0]) if (a == 8).any() else None)
    return out


def run(path, ref=None, depth_fn=CF.depth_mm):
    t0 = time.time(); Z = np.load(path); V = Z["v"].astype(float); F = Z["f"].astype(np.int64); N = Z["n"].astype(float)
    out = dict(skin=os.path.basename(path), marks=dict(d2_per_mm=D2_MARK, d1=D1_MARK, eye_step_mm=EYE_STEP_MARK))
    rr = rings(V, depth_fn); pp = rings(V, depth_fn, plant=True)
    out["rings"] = dict(legs=rr, all_pass=bool(all(r["passes"] for r in rr.values())),
                        proof=dict(plant="1.0 mm cubic step over 10 mm at z 55-65 mm", caught=bool(not any(r["passes"] for r in pp.values())),
                                   planted_max_d2=max(r["leg_z_le_115"]["max_abs_d2_per_mm"] for r in pp.values())))
    dv = Z["depth_raw_mm"].astype(float) if "depth_raw_mm" in Z else depth_fn(V)
    out["relief"] = relief(V, F, N, dv)
    if ref:
        R = np.load(ref); Vr = R["v"].astype(float); Fr = R["f"].astype(np.int64); Nr = R["n"].astype(float)
        out["relief_ref"] = dict(skin=os.path.basename(ref), **relief(Vr, Fr, Nr, depth_fn(Vr), prove=False))
    from twosided import MeshDist
    D = np.load(os.path.join(TR, "tripo_welded.npz")); md = MeshDist(D["v"].astype(float), D["f"].astype(np.int64))
    prof = eye_profile(V, md); es = eye_step(prof); ep = eye_step(prof, plant=1.5)
    out["eyes"] = dict(profile_cols=["margin_dist_mm_from", "n", "median_inset_mm"], profile=prof, step=es,
                       passes=bool(all((v["max_step_mm"] or 0) <= EYE_STEP_MARK for v in es.values())),
                       proof=dict(plant="+1.5 mm inset outside the margin", caught=bool(all((v["max_step_mm"] or 0) >= 1.5 - 1e-6 for v in ep.values()))))
    if ref:
        pr_ = eye_profile(Vr, md); out["eyes_ref"] = dict(profile=pr_, step=eye_step(pr_))
    out["seconds"] = round(time.time() - t0, 1)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("skin"); ap.add_argument("--ref", default=None); ap.add_argument("--out", default=None)
    a = ap.parse_args(); res = run(a.skin, a.ref)
    s = json.dumps(res, indent=1)
    if a.out:
        open(a.out, "w").write(s)
    print(s[:6000])
