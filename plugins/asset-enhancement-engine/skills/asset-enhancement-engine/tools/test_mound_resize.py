"""Proof of mound_resize.py (2026-10-21, woman2 build 13a4). Planted cases with known answers:
  1. a mound H (1 - (r/R0)^2)^1.5 on a curved wall (a cylinder, radius 130 mm), a quad grid at 2 mm, seeded fine relief
     (+-0.03 mm, a few mm across) and a cap (a 3 mm bump 8 mm across at the top, its own detail):
       volume over the footprint scales by c (to the share the band and the ramp take: reported), the fine relief rides
       unchanged (its correlation and amplitude before / after), the cap keeps its own height above the mound round it
       (changed by no more than the dome's own flattening under it, + 2 %),
       nothing outside the footprint and band moves (exactly 0), no face turns over;
  2. an overhanging lip (a strip whose profile runs out past its own base and back: a lower pole over its fold): the
     column order is kept and no face turns over at c = 0.6;
  4. band_mode "fill" on case 1 (band 40 mm): volume over the footprint still scales by c, nothing moves past the band,
     no face turns over (its outward overshoot past the footprint's edge is reported);
  3. rim_concavity: the same mound truncated (it meets the wall with a kink: the crease) against one that meets it
     tangentially; the kinked one must read over 40 /m (the chest-wall instrument's fold threshold), the smooth one under.
    python engine/tools/test_mound_resize.py   (writes test_mound_resize.json beside it)"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mound_resize as MR  # noqa: E402


def grid_mesh(nu, nv):
    idx = np.arange(nu * nv).reshape(nv, nu)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel()
    return np.r_[np.c_[a, b, d], np.c_[a, d, c]]


def wall_frame(Rc=0.13, n=241, step=0.001):
    """frame at the origin, axis +z; wall = cylinder about the v axis (curving back with u)"""
    k = (np.arange(n) - (n - 1) / 2) * step; U, Vv = np.meshgrid(k, k)
    W = np.sqrt(np.maximum(Rc ** 2 - U ** 2, 0)) - Rc
    return {"o": np.zeros(3), "R": np.eye(3), "step": step, "n": n, "wall": W}, U, Vv


def case_mound(c=0.75, seed=0, kink=False):
    fr, U, Vv = wall_frame()
    st = 0.0015; ku = np.arange(-0.110, 0.1101, st); KU, KV = np.meshgrid(ku, ku)
    R0, H = 0.065, 0.040
    r = np.hypot(KU, KV)
    if kink:                    # truncated: meets the wall at a slope of 2H/R0 (a crease)
        mound = H * np.clip(1 - (r / R0) ** 2, 0, None)
    else:                       # meets the wall tangentially with its curvature going to 0 (wider support, same height)
        mound = H * np.clip(1 - (r / 0.080) ** 2, 0, None) ** 3
    rng = np.random.default_rng(seed)
    fine = np.zeros_like(r)
    for _ in range(1500):                                  # fine relief: small gaussian bumps, +-0.03 mm, sigma 1.5-3 mm
        cx, cy = rng.uniform(-0.11, 0.11, 2); s = rng.uniform(0.0015, 0.003); a = rng.uniform(-3e-5, 3e-5)
        fine += a * np.exp(-((KU - cx) ** 2 + (KV - cy) ** 2) / (2 * s * s))
    cap = 0.003 * np.exp(-(r / 0.004) ** 2)                # the rigid cap: a 6 mm-wide bump on the top
    Wv = np.sqrt(np.maximum(0.13 ** 2 - KU ** 2, 0)) - 0.13
    Z = Wv + mound + fine + cap
    V = np.c_[KU.ravel(), KV.ravel(), Z.ravel()]
    F = grid_mesh(len(ku), len(ku))
    fp = np.hypot(U, Vv) <= R0
    return fr, fp, V, F, (KU.ravel(), KV.ravel(), Wv.ravel(), mound.ravel(), fine.ravel(), cap.ravel(), r.ravel()), st


def run():
    out = {}
    # ---- 1. mound with cap and relief
    c = 0.75
    fr, fp, V, F, (ku, kv, wv, mound, fine, cap, r), st = case_mound(c)
    rigid = r <= 0.008
    Vn, rep, aux = MR.resize(V, F, fr, fp, c, cap=rigid, smooth_mm=6.0, band_mm=15.0, ramp_mm=4.0)
    h0 = V[:, 2] - wv; h1 = Vn[:, 2] - wv
    inside = r <= 0.065
    vol0 = h0[inside].sum() * st * st * 1e6; vol1 = h1[inside].sum() * st * st * 1e6
    d = Vn - V
    moved_outside = np.abs(d[r > 0.065 + 0.015 + 0.003]).max() * 1e3
    # the cap's own height: its top above the plane fitted to the ring just outside it (8-12 mm), before and after
    def cap_height(X):
        ring = (r > 0.008) & (r < 0.012); P = X[ring]
        G = np.c_[P[:, 0], P[:, 1], np.ones(len(P))]; co = np.linalg.lstsq(G, P[:, 2], rcond=None)[0]
        k = np.argmin(r); return float(X[k, 2] - (co[0] * X[k, 0] + co[1] * X[k, 1] + co[2]))
    ch0, ch1 = cap_height(V), cap_height(Vn)
    # the planted dome under the cap flattens by c: its own sag over the ring would change the reading by
    sag = float((0.040 - 0.040 * (1 - (0.010 / 0.065) ** 2) ** 1.5) * (1 - c))
    cap_spread = abs((ch1 - ch0) + 0.0)
    # the fine relief: what is left after removing the smooth part, before and after (away from the cap and rim)
    import surface_fairing as SF            # the engine's relief instrument: height above the local quadric (10 mm)
    body = (r > 0.022) & (r < 0.050); bid = np.nonzero(body)[0]   # past the cap's blend ring (8 + 10 mm)
    det0 = SF.relief(V, F, bid, 0.010); det1 = SF.relief(Vn, F, bid, 0.010)
    det0 = np.r_[det0]; det1 = np.r_[det1]; ok_ = np.isfinite(det0) & np.isfinite(det1); det0, det1 = det0[ok_], det1[ok_]
    corr = float(np.corrcoef(det0, det1)[0, 1]); amp = float(np.std(det1) / np.std(det0))
    out["1_mound"] = {"c": c, "volume_ml_before": vol0, "volume_ml_after": vol1, "ratio": vol1 / vol0,
                      "fine_relief_corr": corr, "fine_relief_amplitude_ratio": amp, "cap_height_mm_before_after": [ch0 * 1e3, ch1 * 1e3], "cap_height_change_mm": (ch1 - ch0) * 1e3,
                      "dome_sag_change_under_cap_mm": sag * 1e3, "max_move_outside_footprint_and_band_mm": moved_outside,
                      "faces_turned_over": rep["faces_turned_over"],
                      "pass": bool(abs(vol1 / vol0 - c) < 0.03 and corr > 0.97 and abs(amp - 1) < 0.05 and abs(ch1 - ch0) <= sag + 0.02 * abs(ch0)
                                   and moved_outside == 0.0 and rep["faces_turned_over"] == 0)}
    # ---- 2. an overhanging lip: a strip whose profile in (v, a) runs down, out past its base, and back in (a pole over its fold)
    # profile in (v, a): an upper slope (v .08 -> 0, a 0 -> .03), the lip (an ellipse centred at (0, .015), radii .03 x
    # .015: down the front to its lowest point v = -.03, back along its underside to the fold at (0, 0)), then the chest
    # below the fold (a = 0, v 0 -> -.06): the columns v in (-.03, 0) cross the front, the underside and the chest
    phi = np.linspace(0, np.pi, 120)
    up = np.c_[np.linspace(0.08, 0.0, 50)[:-1], np.linspace(0.0, 0.03, 50)[:-1]]
    lip = np.c_[-0.03 * np.sin(phi), 0.015 + 0.015 * np.cos(phi)]
    chest = np.c_[np.linspace(0.0, -0.06, 40)[1:], np.zeros(39)]
    P = np.r_[up, lip, chest]; vv, aa = P[:, 0], P[:, 1]
    ku = np.arange(-0.03, 0.0301, 0.002)
    nu, nv = len(ku), len(P)
    V2 = np.zeros((nu * nv, 3))
    for j in range(nv):
        V2[j * nu:(j + 1) * nu] = np.c_[ku, np.full(nu, P[j, 0]), np.full(nu, P[j, 1])]
    F2 = grid_mesh(nu, nv)
    k = (np.arange(241) - 120) * 0.001
    fr2 = {"o": np.zeros(3), "R": np.eye(3), "step": 0.001, "n": 241, "wall": np.zeros((241, 241))}
    fp2 = np.ones((241, 241), bool)
    Vn2, rep2, aux2 = MR.resize(V2, F2, fr2, fp2, 0.6, smooth_mm=6.0, band_mm=15.0, ramp_mm=4.0)
    # the column order: for the middle u, every pair of points within 0.5 mm in v keeps the order of their heights
    mid = np.arange(nv) * nu + nu // 2
    a0, a1, v0 = V2[mid, 2], Vn2[mid, 2], V2[mid, 1]
    bad = 0; pairs = 0
    for i in range(nv):
        for j in range(i + 1, nv):
            if abs(v0[i] - v0[j]) < 0.0005 and abs(a0[i] - a0[j]) > 0.001:
                pairs += 1; bad += int(np.sign(a1[i] - a1[j]) != np.sign(a0[i] - a0[j]))
    out["2_overhang"] = {"column_pairs_tested": pairs, "order_changed": bad, "faces_turned_over": rep2["faces_turned_over"],
                         "lip_front_move_mm": float((Vn2[mid] - V2[mid])[:, 2].min() * 1e3),
                         "pass": bool(pairs > 0 and bad == 0 and rep2["faces_turned_over"] == 0)}
    # ---- 3. rim concavity: a kinked rim (truncated paraboloid) against a tangential one
    res = {}
    for tag, kink in (("kink", True), ("tangential", False)):
        fr3, fp3, V3, F3, (ku3, kv3, wv3, mo3, fi3, ca3, r3), st3 = case_mound(kink=kink)
        # rasterise the front height on the frame grid (the mesh is a height field on its own grid here)
        n = fr3["n"]; kk = (np.arange(n) - (n - 1) / 2) * fr3["step"]
        from scipy.interpolate import RegularGridInterpolator
        g = np.arange(-0.110, 0.1101, st3)
        Zg = V3[:, 2].reshape(len(g), len(g))
        I = RegularGridInterpolator((g, g), Zg, bounds_error=False, fill_value=np.nan)
        UU, VV = np.meshgrid(kk, kk)
        skin = I(np.c_[VV.ravel(), UU.ravel()]).reshape(n, n)
        pk, at = MR.rim_concavity(skin, fr3, np.arange(0, 360, 30), 45, 95)
        res[tag] = {"peak_per_m_median": float(np.nanmedian(pk)), "peak_per_m_max": float(np.nanmax(pk)), "at_mm_median": float(np.nanmedian(at))}
    out["3_rim_concavity"] = dict(res, threshold_per_m=40.0,
                                  **{"pass": bool(res["kink"]["peak_per_m_median"] > 40 and res["tangential"]["peak_per_m_max"] < 40)})
    # ---- 4. band_mode "fill": the move outside the footprint is the smoothest field joining it to nothing at band_mm
    fr4, fp4, V4, F4, (ku4, kv4, wv4, mo4, fi4, ca4, r4), st4 = case_mound(c)
    Vn4, rep4, aux4 = MR.resize(V4, F4, fr4, fp4, c, cap=r4 <= 0.008, smooth_mm=6.0, band_mm=40.0, ramp_mm=0.0, band_mode="fill")
    d4 = (Vn4 - V4)[:, 2]
    h40 = V4[:, 2] - wv4; h41 = Vn4[:, 2] - wv4; ins = r4 <= 0.065
    out["4_band_fill"] = {"volume_ratio_over_footprint": float(h41[ins].sum() / h40[ins].sum()), "max_move_past_band_mm": float(np.abs(d4[r4 > 0.065 + 0.040 + 0.003]).max() * 1e3),
                          "max_outward_move_mm": float(d4.max() * 1e3), "faces_turned_over": rep4["faces_turned_over"]}
    out["4_band_fill"]["pass"] = bool(abs(out["4_band_fill"]["volume_ratio_over_footprint"] - c) < 0.03 and out["4_band_fill"]["max_move_past_band_mm"] == 0.0
                                      and rep4["faces_turned_over"] == 0)
    out["all_pass"] = all(v["pass"] for v in out.values() if isinstance(v, dict) and "pass" in v)
    return out


if __name__ == "__main__":
    o = run()
    json.dump(o, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_mound_resize.json"), "w"), indent=1)
    print(json.dumps(o, indent=1))
