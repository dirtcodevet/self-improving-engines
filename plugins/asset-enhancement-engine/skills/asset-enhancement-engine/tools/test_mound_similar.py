"""Proof of mound_resize.resize_similar (2026-10-21, woman2 build 13a5). Planted cases with known answers:
  1. a dome H (1 - (r/80 mm)^2)^3, H 40 mm, on a curved wall (a cylinder, radius 130 mm), a 1.5 mm quad grid, seeded
     fine relief (+-0.03 mm) and a cap (a 3 mm bump 8 mm across on the top, its own detail), made 0.9 x as large (s = k =
     0.9, centre on the cap):
       the smooth form against the analytic similarity 0.9 H(r' / 0.9) where each vertex now stands (r' its new radius)
       over the mound (cap and fine relief taken off by their planted values), the volume over the old footprint against
       s^3, apex over the radius of the area standing over t (t scaled with the mound: exactly kept by a similarity; and
       at a fixed 3 mm), the cap's own size and relief, nothing past the band, no face turned over, the map one-to-one;
  2. an overhanging lip (a strip whose profile runs out past its base and back: a lower pole over its fold) made 0.9 x
     as large about a centre 30 mm above its fold: every column keeps its order, no face turns over, and the fold moves
     towards the centre by (1 - s) x 30 mm.
    python engine/tools/test_mound_similar.py   (writes test_mound_similar.json beside it)"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mound_resize as MR  # noqa: E402
import test_mound_resize as TR  # noqa: E402  (its planted mound and grid)


def raster_height(V, wall_fn, step=0.001, half=0.110):
    """the front height above the wall on a regular grid (linear between the vertices)"""
    from scipy.interpolate import LinearNDInterpolator
    k = np.arange(-half, half + 1e-9, step); KU, KV = np.meshgrid(k, k)
    h = LinearNDInterpolator(V[:, :2], V[:, 2] - wall_fn(V[:, 0]))(KU, KV)
    return KU, KV, h


def run():
    out = {}
    s = 0.9
    fr, _, V, F, (ku, kv, wv, mound, fine, cap, r), st = TR.case_mound(kink=False)
    n = fr["n"]; kk = (np.arange(n) - (n - 1) / 2) * fr["step"]; U, Vv = np.meshgrid(kk, kk)
    fp = np.hypot(U, Vv) <= 0.080
    capm = r <= 0.008
    wall = lambda x: np.sqrt(np.maximum(0.13 ** 2 - x ** 2, 0)) - 0.13
    # the far side of the body in the same columns (a sheet 200 mm behind the wall, wound the other way): never moves
    nv0 = len(V)
    Vb = V.copy(); Vb[:, 2] = wall(V[:, 0]) - 0.200
    V_all = np.r_[V, Vb]; F_all = np.r_[F, F[:, ::-1] + nv0]
    Vn_all, rep, aux = MR.resize_similar(V_all, F_all, fr, fp, s, s, (0.0, 0.0), cap=np.r_[capm, np.zeros(nv0, bool)], band_mm=40.0)
    Vn = Vn_all[:nv0]
    far_side_moved_mm = float(np.abs(Vn_all[nv0:] - Vb).max() * 1e3)
    H = lambda rr: 0.040 * np.clip(1 - (rr / 0.080) ** 2, 0, None) ** 3
    # (a) the form: each vertex's height above the wall less its planted fine relief and cap, against 0.9 H(r' / 0.9)
    rn = np.hypot(Vn[:, 0], Vn[:, 1]); hn = Vn[:, 2] - wall(Vn[:, 0])
    form = hn - fine - cap - s * H(rn / s)
    on = (rn < s * 0.075)
    off_cap = on & ~capm
    e = np.abs(form[off_cap]) * 1e3
    e_cap = np.abs(form[capm]) * 1e3
    from scipy import ndimage
    core_v = ndimage.map_coordinates(aux["core"].astype(float), [V[:, 1] / fr["step"] + (n - 1) / 2, V[:, 0] / fr["step"] + (n - 1) / 2], order=0) > 0.5
    e_core = np.abs(form[core_v & on]) * 1e3
    e_rest = np.abs(form[~core_v & off_cap]) * 1e3
    # (b) volume over the old footprint, (c) apex over radius of the raised area
    KU, KV, h0 = raster_height(V, wall); _, _, h1 = raster_height(Vn, wall)
    fpm = np.hypot(KU, KV) <= 0.080
    vol0 = np.nansum(np.where(fpm, h0, 0)) * 1e-6 * 1e6; vol1 = np.nansum(np.where(fpm, h1, 0)) * 1e-6 * 1e6
    def apex_r(h, t):
        hh = np.where(fpm & np.isfinite(h), h, -1); a = float(np.nanmax(hh)); area = float((hh > t).sum()) * 1e-6
        return a / np.sqrt(area / np.pi)
    ar0 = apex_r(h0, 0.003); ar1_scaled = apex_r(h1, 0.003 * s); ar1_fixed = apex_r(h1, 0.003)
    # (d) the cap: its extent in the plane and its own relief above the dome under it
    q0 = V[capm, :2]; q1 = Vn[capm, :2]
    ext0 = float(np.hypot(q0[:, 0], q0[:, 1]).max()); ext1 = float(np.hypot(q1[:, 0], q1[:, 1]).max())
    relief0 = (V[capm, 2] - wall(V[capm, 0])) - H(r[capm]) - fine[capm]
    relief1 = hn[capm] - s * H(rn[capm] / s) - fine[capm]
    cap_relief_change = float(np.abs(relief1 - relief0).max() * 1e3)
    # (e) nothing past the band
    far = r > 0.080 + 0.040 + 0.003
    moved_far = float(np.abs(Vn[far] - V[far]).max() * 1e3)
    # pass: the similar form within 0.15 mm (p99) and 0.2 mm over the mound (0.4 % of its height) (the field is the soft fit: off the similarity's
    # move by up to ~1 mm at the mound's foot, where it is low and nearly flat; the cap's ring seated), the cap within 0.4 %
    # of the mound's height (resize's own cap error: the mound under a cap is a fill)
    ok1 = bool(np.percentile(e_core, 99) < 0.15 and e_core.max() < 0.20 and e_rest.max() < 0.20 and np.percentile(e_rest, 99) < 0.15
               and e_cap.max() < 0.004 * 40.0 and abs(vol1 / vol0 - s ** 3) < 0.01
               and abs(ar1_scaled / ar0 - 1) < 0.01 and abs(ext1 - ext0) < 5e-5 and moved_far == 0.0 and far_side_moved_mm == 0.0
               and rep["faces_turned_over"] == 0 and rep["lateral"]["jacobian_det_min"] > 0)
    out["1_dome"] = {"s": s, "form_error_mm_p50_p99_max": [float(np.percentile(e, 50)), float(np.percentile(e, 99)), float(e.max())],
                     "form_error_core_mm_p99_max": [float(np.percentile(e_core, 99)), float(e_core.max())],
                     "form_error_filled_mm_p99_max": [float(np.percentile(e_rest, 99)), float(e_rest.max())],
                     "form_error_on_cap_mm_max": float(e_cap.max()), "volume_ml_before_after": [vol0, vol1], "volume_ratio": vol1 / vol0, "s_cubed": s ** 3,
                     "apex_over_radius_before": ar0, "after_threshold_scaled": ar1_scaled, "after_threshold_fixed_3mm": ar1_fixed,
                     "cap_extent_mm_before_after": [ext0 * 1e3, ext1 * 1e3], "cap_relief_change_mm_max": cap_relief_change,
                     "max_move_past_band_mm": moved_far, "far_side_sheet_max_move_mm": far_side_moved_mm,
                     "faces_turned_over": rep["faces_turned_over"], "report": rep["lateral"], "seat": rep["seat"],
                     "pass": ok1}
    # ---- 2. the overhanging lip (test_mound_resize case 2's strip), made 0.9 x as large about (0, 30 mm) on the wall
    phi = np.linspace(0, np.pi, 120)
    up = np.c_[np.linspace(0.08, 0.0, 50)[:-1], np.linspace(0.0, 0.03, 50)[:-1]]
    lip = np.c_[-0.03 * np.sin(phi), 0.015 + 0.015 * np.cos(phi)]
    chest = np.c_[np.linspace(0.0, -0.06, 40)[1:], np.zeros(39)]
    P = np.r_[up, lip, chest]
    kx = np.arange(-0.03, 0.0301, 0.002); nu, nv = len(kx), len(P)
    V2 = np.zeros((nu * nv, 3))
    for j in range(nv):
        V2[j * nu:(j + 1) * nu] = np.c_[kx, np.full(nu, P[j, 0]), np.full(nu, P[j, 1])]
    F2 = TR.grid_mesh(nu, nv)
    fr2 = {"o": np.zeros(3), "R": np.eye(3), "step": 0.001, "n": 241, "wall": np.zeros((241, 241))}
    k2 = (np.arange(241) - 120) * 0.001; U2, W2 = np.meshgrid(k2, k2)
    fp2 = (W2 > -0.035) & (W2 < 0.085) & (np.abs(U2) < 0.05)
    Vn2, rep2, aux2 = MR.resize_similar(V2, F2, fr2, fp2, s, s, (0.0, 0.03), band_mm=30.0, core_h_mm=3.0)
    mid = np.arange(nv) * nu + nu // 2
    a0, a1, v0 = V2[mid, 2], Vn2[mid, 2], V2[mid, 1]
    bad = 0; pairs = 0
    for i in range(nv):
        for j in range(i + 1, nv):
            if abs(v0[i] - v0[j]) < 0.0005 and abs(a0[i] - a0[j]) > 0.001:
                pairs += 1; bad += int(np.sign(a1[i] - a1[j]) != np.sign(a0[i] - a0[j]))
    fold = mid[len(up) + len(lip) - 1]                      # the lip's last point: its fold at (0, 0)
    fold_move = float((Vn2[fold, 1] - V2[fold, 1]) * 1e3)
    ok2 = bool(bad == 0 and rep2["faces_turned_over"] == 0 and abs(fold_move - (1 - s) * 30.0) < 0.3)
    out["2_lip"] = {"column_pairs_checked": pairs, "order_changed": bad, "faces_turned_over": rep2["faces_turned_over"],
                    "fold_moved_up_mm": fold_move, "expected_mm": (1 - s) * 30.0, "jacobian_det_min": rep2["lateral"]["jacobian_det_min"], "pass": ok2}
    # ---- 3. the dome against a held strip (a midline it meets: held cells from 56 mm on one side, its vertices from 60 mm,
    # where the dome still stands 3-5 mm): the strip never moves, the far side keeps the similarity, nothing turns over
    sel3 = V[:, 0] > -0.060                      # the dome's foot at 80 mm; the strip's vertices from 60 mm (the dome 3.3 mm high there), its cells from 56
    hg3 = U < -0.056
    Vn3, rep3, aux3 = MR.resize_similar(V, F, fr, fp, s, s, (0.0, 0.0), sel=sel3, cap=capm, held_grid=hg3, band_mm=40.0)
    rn3 = np.hypot(Vn3[:, 0], Vn3[:, 1]); hn3 = Vn3[:, 2] - wall(Vn3[:, 0])
    form3 = np.abs(hn3 - fine - cap - s * H(rn3 / s)) * 1e3
    far3 = (V[:, 0] > -0.020) & (rn3 < s * 0.075) & ~capm
    near3 = (V[:, 0] <= -0.020) & (V[:, 0] > -0.060) & (r < 0.080)
    strip_moved = float(np.abs(Vn3[~sel3] - V[~sel3]).max() * 1e3)
    ok3 = bool(strip_moved == 0.0 and np.percentile(form3[far3], 99) < 0.12 and rep3["faces_turned_over"] == 0 and rep3["lateral"]["jacobian_det_min"] > 0)
    out["3_held_strip"] = {"strip_max_move_mm": strip_moved, "form_error_away_from_strip_mm_p99_max": [float(np.percentile(form3[far3], 99)), float(form3[far3].max())],
                           "form_error_towards_strip_mm_p50_p99": [float(np.percentile(form3[near3], 50)), float(np.percentile(form3[near3], 99))],
                           "faces_turned_over": rep3["faces_turned_over"], "jacobian_det_min": rep3["lateral"]["jacobian_det_min"], "seat": rep3["seat"], "pass": ok3}
    out["pass"] = bool(ok1 and ok2 and ok3)
    return out


if __name__ == "__main__":
    res = run()
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_mound_similar.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(json.dumps(res, indent=1, default=float))
