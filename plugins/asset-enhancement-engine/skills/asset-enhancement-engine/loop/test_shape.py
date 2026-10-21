"""Proofs for engine/loop/shape.py and core.solve on shapes whose answers are known (A10: each instrument is proven on the
failure it exists to catch before it drives a change).   python engine/loop/test_shape.py [--torso]"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from loop.shape import profile_arcs, SliceBend, limb_sections, state_value
from loop.core import Target, solve, measure

OK = []


def check(name, cond, info):
    OK.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + ": " + info)


def ruled(prof_y, prof_z, half_w=0.05, nx=10):   # an even count: no vertex column exactly on the x = 0 cut
    """a surface extruded along x from a (y, z) profile, plus a flat front far away so the slice has two sides"""
    xs = np.linspace(-half_w, half_w, nx); n = len(prof_z)
    V = np.array([[x, y, z] for x in xs for y, z in zip(prof_y, prof_z)])
    F = []
    for i in range(nx - 1):
        for j in range(n - 1):
            a, b, c, d = i * n + j, i * n + j + 1, (i + 1) * n + j, (i + 1) * n + j + 1
            F += [[a, c, b], [b, c, d]]
    return {"V": V, "F": np.array(F)}


def arcs_profile(turns_deg, lengths, ds=0.0005, lead=0.04):
    """walking down from a vertical start: arcs of the given turns and lengths, alternating sense (convex first, as a
    back seen from behind), each with a half-sine curvature (zero at both ends), so curvature is continuous and the
    inflections sit exactly at the joins, as on a real back; straight lead-in and lead-out along the end tangents"""
    ang, sign = 0.0, 1.0
    ks = []
    for T, L in zip(turns_deg, lengths):
        n = int(L / ds); s_ = (np.arange(n) + 0.5) / n
        ks.append(sign * np.radians(T) * np.pi / 2 * np.sin(np.pi * s_) / n); sign = -sign
    dphi = np.r_[np.zeros(int(lead / ds)), np.concatenate(ks), np.zeros(int(lead / ds))]
    phi = np.cumsum(dphi)
    y = 0.1 - np.cumsum(np.sin(phi) * ds); z = -np.cumsum(np.cos(phi) * ds)   # first arc bulges toward +y
    return y, z


def noisy(y, z, noise_mm, seed=0):
    """surface noise: sums of bumps 5-20 mm long with the given RMS, like the spine furrow's wobble on a real back"""
    if noise_mm <= 0: return y
    rng = np.random.default_rng(seed); s = np.cumsum(np.r_[0, np.hypot(np.diff(y), np.diff(z))]); n = np.zeros_like(s)
    for _ in range(40):
        L = rng.uniform(0.005, 0.02); n += np.sin(2 * np.pi * s / L + rng.uniform(0, 6.3)) * rng.uniform(0.5, 1)
    return y + n * noise_mm / 1000 / np.std(n)


# 1. profile_arcs on known arcs (convex 40, concave 45, convex 30) with surface noise up to the woman2 back's 1.2 mm
y0, z = arcs_profile([40, 45, 30], [0.20, 0.22, 0.16])
for noise in (0.0, 0.6, 1.2):
    st = ruled(noisy(y0, z, noise), z)
    m = profile_arcs(st, smooth_mm=20, angle_smooth_mm=8, z_lo=z.min(), z_hi=z.max())
    got = (m.get("profile_convex_above_turn_deg", -99), m.get("profile_concave_turn_deg", -99), m.get("profile_convex_below_turn_deg", -99))
    check("profile arcs, noise %.1f mm" % noise, all(abs(g - t) < 2.0 for g, t in zip(got, (40, 45, 30))),
          "convex %.1f (40), concave %.1f (45), convex %.1f (30)" % got)
# 1b. a sliver: a flat stretch inside the concave arc whose curvature flips by 1.5 deg (woman2 v6's lumbar at 14 mm)
#     must not split the arc: the concave turn is the net 20 - 1.5 + 26.5 = 45 deg (unmerged it reads 26.5, and the
#     "convex above" becomes the 1.5 deg sliver). Tolerance 3 deg: on this five-arc profile the 1.2 mm noise alone moves
#     the worst arc by 2.6 deg (the noise, not the merge: the 0.0 mm case reads within 0.6 deg)
ys_, zs_ = arcs_profile([40, 20, 1.5, 26.5, 30], [0.20, 0.10, 0.04, 0.12, 0.16])
for noise in (0.0, 0.6, 1.2):
    for sm in (14, 20):
        m = profile_arcs(ruled(noisy(ys_, zs_, noise), zs_), smooth_mm=sm, angle_smooth_mm=8, z_lo=zs_.min(), z_hi=zs_.max())
        got = (m.get("profile_convex_above_turn_deg", -99), m.get("profile_concave_turn_deg", -99), m.get("profile_convex_below_turn_deg", -99))
        check("sliver merged, noise %.1f mm, smooth %d mm" % (noise, sm), all(abs(g - t) < 3.0 for g, t in zip(got, (40, 45, 30))),
              "convex %.1f (40), concave %.1f (45), convex %.1f (30)" % got)
st = ruled(y0, z)

# 2. SliceBend over the concave arc's range by a known total changes the concave turn by that total
m0 = profile_arcs(st, smooth_mm=20, angle_smooth_mm=8, z_lo=z.min(), z_hi=z.max())
zt, zb = m0["profile_concave_z_top"], m0["profile_concave_z_bot"]
for total in (+6.0, -6.0):
    h = SliceBend(st, zt, zb, 3, pivot_depth=0.06)
    dens = total / ((zt - zb) / 0.1)
    s2 = h.apply(st, np.full(3, dens))
    m1 = profile_arcs(s2, smooth_mm=20, angle_smooth_mm=8, z_lo=s2["V"][:, 2].min(), z_hi=s2["V"][:, 2].max())
    d = m1["profile_concave_turn_deg"] - m0["profile_concave_turn_deg"]
    check("slice bend %+.0f deg" % total, abs(abs(d) - abs(s2["slice_bend_total_deg"])) < 1.5,
          "concave turn changed %+.2f, bend total %+.2f" % (d, s2["slice_bend_total_deg"]))

# 2b. hold="bottom" (woman2 v6): what lies below the range stays exactly where it was, the arc changes by the same
#     amount as with the top held (the two differ by one rigid motion; 0.2 deg allows the instrument's z-binning of a
#     turned profile), and move_points maps any point like apply
h_t = SliceBend(st, zt, zb, 3, pivot_depth=0.06)
h_b = SliceBend(st, zt, zb, 3, pivot_depth=0.06, hold="bottom")
pp = np.full(3, 6.0 / ((zt - zb) / 0.1))
s_t, s_b = h_t.apply(st, pp), h_b.apply(st, pp)
below = st["V"][:, 2] < zb - 0.002
kw_ = dict(smooth_mm=20, angle_smooth_mm=8)
d_t = profile_arcs(s_t, z_lo=s_t["V"][:, 2].min(), z_hi=s_t["V"][:, 2].max(), **kw_)["profile_concave_turn_deg"]
d_b = profile_arcs(s_b, z_lo=s_b["V"][:, 2].min(), z_hi=s_b["V"][:, 2].max(), **kw_)["profile_concave_turn_deg"]
Qm, ang = h_b.move_points(pp, st["V"])
top = st["V"][:, 2] > zt + 0.002
check("slice bend, bottom held", np.abs(s_b["V"][below] - st["V"][below]).max() < 1e-12 and abs(d_t - d_b) < 0.2
      and np.abs(Qm - s_b["V"]).max() < 1e-12 and abs(np.degrees(ang[top]).mean() + 6.0) < 0.01,
      "below the range moved %.1e m; concave turn top-held %.2f vs bottom-held %.2f; the part above turned %.2f deg"
      % (np.abs(s_b["V"][below] - st["V"][below]).max(), d_t, d_b, np.degrees(ang[top]).mean()))

# 3. limb sections: a round cylinder against one with a flat side (a chord cutting 25% of the circle's perimeter)
def tube(flat_frac, r=0.045, L=0.3, nth=240, nz=60):
    th = np.linspace(-np.pi, np.pi, nth, endpoint=False); cut = np.cos(np.pi * flat_frac)  # chord at x = r*cut
    pts = np.stack([np.minimum(np.cos(th), cut) * r, np.sin(th) * r], 1)
    V = np.array([[p[0], p[1], -zz] for zz in np.linspace(0, L, nz) for p in pts]); F = []
    for i in range(nz - 1):
        for j in range(nth):
            a, b, c, d = i * nth + j, i * nth + (j + 1) % nth, (i + 1) * nth + j, (i + 1) * nth + (j + 1) % nth
            F += [[a, c, b], [b, c, d]]
    return {"V": V, "F": np.array(F)}
for ff in (0.0, 0.25):
    t = tube(ff); m = limb_sections(t, [0, 0, 0], [0, 0, -0.3], [0.3, 0.5, 0.7], np.ones(len(t["V"]), bool))
    print("   tube flat %.2f: flat share %.3f, aspect %.3f, jump %.1f" % (ff, m["limb_flat_mean"], m["limb_aspect_mean"], m["limb_jump_max"]))
    if ff == 0: round_m = m
check("limb sections: a flat side reads as flat, a round tube as round",
      round_m["limb_flat_mean"] < 0.03 and m["limb_flat_mean"] > 0.12 and m["limb_jump_max"] > 3 * round_m["limb_jump_max"],
      "flat share round %.3f vs flat-sided %.3f; jump %.1f vs %.1f" % (round_m["limb_flat_mean"], m["limb_flat_mean"], round_m["limb_jump_max"], m["limb_jump_max"]))

# 3b. the loop fills a planted flat side with radial bumps held to inflation only (woman2 v6 job 2's handle), with
#     parameters in metres: the finite-difference step must follow the handle's scale (core.solve on params / scale)
from loop.shape import NormalBumps  # noqa: E402
t = tube(0.25); Vt = t["V"]; rr = np.hypot(Vt[:, 0], Vt[:, 1]); radial = np.c_[Vt[:, 0] / rr, Vt[:, 1] / rr, np.zeros(len(Vt))]
flat_side = (Vt[:, 0] > 0.045 * np.cos(np.pi * 0.25) - 0.004) & (Vt[:, 2] < -0.04) & (Vt[:, 2] > -0.26)
cen = [int(np.argmin(np.hypot(Vt[:, 0] - 0.0318, Vt[:, 1] - yy) + np.abs(Vt[:, 2] - zz))) for zz in (-0.1, -0.15, -0.2) for yy in (-0.015, 0.0, 0.015)]
hb = NormalBumps(t, flat_side, cen, bound_m=0.03, direction=radial)
hb.bounds = (np.zeros(hb.n), np.full(hb.n, 0.03)); hb.scale = np.full(hb.n, 0.004)
dsc = [(limb_sections, dict(head=[0, 0, 0], tail=[0, 0, -0.3], stations=[0.4, 0.5, 0.6], region_mask=np.ones(len(Vt), bool)))]
m_b = measure(t, dsc)
filled, xb, rep_b = solve(t, [hb], dsc, [Target("limb_flat_mean", 0.0, 0.02, "a round tube", "test")], reg=0.02, max_nfev=40,
                           diff_step=0.5)   # 2 mm probes: a share of an outline is flat to steps much smaller than its curvature threshold
m_a = measure(filled, dsc)
check("loop fills a planted flat side (radial bumps, metres)", m_a["limb_flat_mean"] < 0.04 and m_a["limb_jump_max"] < m_b["limb_jump_max"],
      "flat share %.3f -> %.3f, jump %.2f -> %.2f, %d evaluations, bumps %s mm" % (m_b["limb_flat_mean"], m_a["limb_flat_mean"], m_b["limb_jump_max"],
                                                                              m_a["limb_jump_max"], rep_b["nfev"], np.round(xb * 1000, 1).tolist()))

# 4. the loop recovers a planted bend on the real torso (needs the pack)
if "--torso" in sys.argv:
    P = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "engine", "packs", "human", "base_female_torso", "v5", "skin.npz")
    zz = np.load(P); tor = {"V": zz["v"].astype(float), "F": zz["f"]}; arm = zz["arm_limb"]
    kw = dict(smooth_mm=20, angle_smooth_mm=8, z_lo=-0.56, z_hi=0.09)
    m0 = profile_arcs(tor, **kw)
    plant = SliceBend(tor, -0.20, -0.41, 3, 0.06, keep_mask=arm)
    bent = plant.apply(tor, np.full(3, +8.0 / 2.1)); bent.pop("slice_bend_total_deg", None)
    mb = profile_arcs(bent, **kw)
    h = SliceBend(bent, -0.20, -0.41, 3, 0.06, keep_mask=arm)
    targets = [Target("profile_concave_turn_deg", m0["profile_concave_turn_deg"], 1.0, "the unplanted torso", "test", inside_free=False)]
    desc = [(profile_arcs, kw)]
    new, x, rep = solve(bent, [h], desc, targets, reg=0.02)
    mr = profile_arcs(new, **kw)
    rms = np.sqrt(np.mean(np.sum((new["V"] - tor["V"]) ** 2, 1))) * 1000
    check("loop recovers a planted 8 deg bend", abs(mr["profile_concave_turn_deg"] - m0["profile_concave_turn_deg"]) < 1.0 and rms < 2.0,
          "concave %.1f -> planted %.1f -> solved %.1f; RMS distance to the original %.2f mm" % (m0["profile_concave_turn_deg"], mb["profile_concave_turn_deg"], mr["profile_concave_turn_deg"], rms))

print("ALL PASS" if all(OK) else "SOME FAILED")
