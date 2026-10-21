"""PAWS v3 feature (felid pack, case cat1, cat v3 round 2) - owner 'paws', 2026-10-18.

WHY (NOTES_v3 R-P; owners_v3.json paws.pads / paws.toes / paws.clefts were MISSING owners). Today's toes are Tripo's
envelope, blurred, inset by the coat depth, with the furless pad mask a z-limited PRISM (coat_field.masks: the coat
switches on at one height round every toe -> the 'stacked coins' P1 and the raised rim P2, LOCATE.md P1), and the
blur closes the clefts ('the toes ... all very thoroughly smoothed together', flag_46-48). This module OWNS the paws:
the toes, the clefts, the pads, the dewclaw, the carpal pad and the claw sheaths, built from ANATOMY (spec_paws_v3.json,
cited) placed at the MEASURED Tripo positions (Phase 1 paws.json / paws_pads_<paw>.npz).

THE FIELD (mm, negative inside, world frame: z up, the cat faces -y, +x = the cat's LEFT), per paw, in its REGION:
  PALM  F_e = S(P') + d(P')  S = Tripo's EXACT signed distance (cached per paw at 0.25 mm, Gaussian sigma 0.6 mm, Keys-cubic
                            read); d = the coat depth WITHOUT any furless mask (coat_field weights x coat.json typical, capped by
                            skin_build's thin-part taper 0.4 x local half-thickness); P' = P with z replaced by a smooth
                            max(z, z_s + 2.5 mm): below that the palm's walls run straight down to the sole plane.
  DIGITS T = smin_i(E_i, K_WEB)  digits II-V as rounded PARAMETRIC digits (the class model): ellipsoids with octant-wise
                            semi-axes on each MEASURED toe direction; front = Tripo's tip (skin level) at Tripo's tip height,
                            top = Tripo's skin-level top over the digit's centre, bottom trimmed by the sole plane, back long
                            into the palm. Lateral semi-axes from the CLEFT RULE (two digits s apart leave a plan notch
                            D = b - sqrt(b^2 - s^2/4); b set for D = CLEFT_TARGET); an outer digit's outer flank = Tripo's
                            measured skin-level flank (tangent to the paw's side wall). SEEN-SIDE FIT: each digit's crown
                            band (front half, |v| < 0.6 b) is offset by the median of Tripo-minus-coat's field over its
                            crown, so the seen front / top sit on Tripo minus the coat (P-SEEN); the 2nd sizing pass asks
                            the cleft rule for the offset's extra depth.
  MIX   F = (1 - w) F_e + w T     w = toe_weight: 0 behind the digit roots (the leg's skin front at z 24 mm), smoothstep to 1
                            over TOE_BLEND in front of them, fading beyond the outer digits: a CONVEX MIX of two near-SDFs, so
                            no cut and no corner; every cleft opens in front of the roots and fades into the web behind.
  SOLE  F = smax(F, z_s - z, K_SOLE)   z_s = median measured pad free level + 0.3 mm (the furred sole between the pads);
                            its edge onto the walls is rounded (no ledge, no rim).
  PADS  F = smin(F, pads, K_PAD) domed ellipsoids at the MEASURED positions / lowest points; digital pads oval along their digit
                            (area <= Tripo's core), the main pad TRILOBED caudally; each scaled so its rim pushed sideways
                            by 0.9 mm is still inside the wall above it (no pad wider than its toe); K_PAD = the soft rim (B4).
  FURLESS  furless_mask = 1 - smoothstep(true 3-D distance to the exposed pad surface / 2 mm) (pad surfaces sampled at 0.1 mm).
  FORE  + dewclaw (digit I: a small rounded digit at the measured medial section lobe, its own pad and sheath); + the carpal
          pad at the measured wrist contour angle.
  CLAWS F = smax(F, -SHEATH, k_sh)  a pocket at every toe tip (claw sheath, skin form only): the claw itself is OPEN for the
                            rig stage; opening_sdf() declares the pockets (fill_voids must never seal them, A20).
  REGION blend (edit): F_out = F_in + w_R (F_paw - F_in), w_R = 1 except within BLEND (4 mm) of a REGION face (only the top
  face crosses tissue: the leg column, where F_paw and F_in are both Tripo inset by the coat).
Design history (each step was looked at on renders and plan / vertical sections): hulls cutting Tripo's envelope gave
knife-slit clefts and flat-faced blocks; hard cuts at the toe roots left corners on the side walls; a height fade left a thin
shelf of Tripo's merged top over the dorsal clefts. The convex mix with parametric digits has none of these. Seen-side
fits tried and rejected (measured): blunter superellipse digits, a Tripo crown mix, a whole-digit offset, a front/top
semi-axis cut (handles at the roots, pad ledges); the crown-band offset kept every check.

INTERFACE (fixed with the skin owner, NOTES_v3 R-P):
  REGIONS                 list of dict(paw, lo_mm, hi_mm): per-paw world-mm AABBs
  furless_mask(P_mm)      weight 0..1, 1 = hairless pad skin (ramps over FURLESS_RAMP >= 2 mm in 3-D from each pad's
                          surface, i.e. along the skin; NOT a z prism)
  edit(P_mm, F_mm)        returns F_mm: the paw's skin field inside its REGION (same sign convention as
                          feat_nose_v3.edit: mm, negative inside); unchanged outside every REGION
  extras: NEED_MM, NEED_MM_SHEATH, opening_sdf(P_mm), coat_depth_mm(P_mm) (= d x (1 - furless): the fur stage's target),
          paw_field(k, P_mm), geometry(k) (the derived construction, recorded by `report`)
usage:  python feat_paws_v3.py cache    -> tripo_rebuild/layers/paws_v3b_field_<paw>.npz (exact SDF + coat grids)
        python feat_paws_v3.py report   -> tripo_rebuild/layers/paws_v3b_geometry.json (every derived value + source)
The previews, crops and probes are engine/checks/paws_checks.py.
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
TR = os.path.join(ROOT, "tripo_rebuild")
LAYERS = os.path.join(TR, "layers")
FELID = os.path.normpath(os.path.join(HERE, ".."))
SPEC = json.load(open(os.path.join(HERE, "spec_paws_v3.json")))
D_ = {k: v["value"] for k, v in SPEC["design"].items()}
NEED_MM = SPEC["contract"]["NEED_MM"]
NEED_MM_SHEATH = SPEC["contract"]["NEED_MM_SHEATH"]
GRID_CAP_MM = 0.15
PAWS = ["fore.R", "fore.L", "hind.R", "hind.L"]
TOES = ["toe1_medial", "toe2", "toe3", "toe4_lateral"]

# REGIONS: Tripo's connected leg piece below z_top (fore 46 mm: holds the carpal pad at z ~35; hind 34 mm), AABB
# measured on tripo_welded.npz (checked 2026-10-18: fore.R [-46.0,-167.8,0]..[-6.1,-116.9,46]; fore.L [6.4,-163.4,0]..
# [47.5,-114.9,46]; hind.R [-65.7,32.9,0.3]..[-22.2,94.8,34]; hind.L [13.9,33.6,0.3]..[57.3,94.8,34]) + REGION_MARGIN
# 3 mm; fore y-max opened to -105 so the carpal pad (y ~ -117.4) sits >= BLEND inside. No two REGIONS overlap.
REGIONS = [
    dict(paw="fore.R", lo_mm=[-49.0, -170.8, -2.0], hi_mm=[-3.1, -105.0, 46.0]),
    dict(paw="fore.L", lo_mm=[3.4, -166.4, -2.0], hi_mm=[50.5, -105.0, 46.0]),
    dict(paw="hind.R", lo_mm=[-68.7, 29.9, -2.0], hi_mm=[-19.2, 97.8, 34.0]),
    dict(paw="hind.L", lo_mm=[10.9, 30.6, -2.0], hi_mm=[60.3, 97.8, 34.0]),
]
RESOLUTION = {"region_mm": NEED_MM, "sheath_band_mm": NEED_MM_SHEATH, "cap_mm": GRID_CAP_MM,
              "source": SPEC["contract"]["why"]}


# ------------------------------------------------------------------ smooth operators (mm)
def ss(t):
    t = np.clip(t, 0.0, 1.0); return t * t * (3 - 2 * t)


def smin(a, b, k):
    if k <= 0: return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k; return np.minimum(a, b) - h * h * k / 4


def smax(a, b, k):
    return -smin(-a, -b, k)


def ell_sdf(Q, ax_pos, ax_neg=None):
    """approximate SDF of an ellipsoid in its own frame (Q (N,3)), semi-axes ax_pos for q >= 0 and ax_neg for q < 0 per
    axis (octant-wise radii keep the value continuous: the term is 0 on each axis plane). IQ's bound k0 (k0 - 1) / k1:
    exact on the surface, |grad| ~ 1 near it."""
    ax_pos = np.asarray(ax_pos, float); ax_neg = ax_pos if ax_neg is None else np.asarray(ax_neg, float)
    R = np.where(Q >= 0, ax_pos, ax_neg)
    k0 = np.linalg.norm(Q / R, axis=1); k1 = np.linalg.norm(Q / (R * R), axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-12)


def slot_sdf(P, O, ax, lat, L, hw, ht):
    """flat capsule ('claw sheath' pocket): axis O -> O + L ax, elliptic section hw (lateral `lat`) x ht, rounded ends"""
    a = ax / np.linalg.norm(ax); l = lat - (lat @ a) * a; l /= np.linalg.norm(l); h = np.cross(a, l)
    q = P - O; s = q @ a; s2 = s - np.clip(s, 0.0, L)
    return ell_sdf(np.c_[s2, q @ l, q @ h], [ht, hw, ht])


# ------------------------------------------------------------------ cached Tripo SDF + coat depth per paw
def _cache_path(k):
    return os.path.join(LAYERS, f"paws_v3b_field_{k}.npz")


def build_cache(k, vox=None, sigma=0.6, band=4.0):
    """Tripo's exact SDF (exact_sdf.compute: ray parity + exact point-triangle distance in a band) on the REGION box +
    1.5 mm at SDF_GRID_MM, Gaussian sigma `sigma` mm; the coat depth d (no furless mask, thin-part taper) on a 1 mm grid"""
    sys.path.insert(0, TR); sys.path.insert(0, FELID)
    from scipy import ndimage
    import exact_sdf as ES
    import coat_field as CF
    vox = vox or D_["SDF_GRID_MM"]; Rg = REG[k]; lo = np.array(Rg["lo_mm"]) - 1.5; hi = np.array(Rg["hi_mm"]) + 1.5
    t0 = time.time(); Z = np.load(os.path.join(TR, "tripo_welded.npz")); v = Z["v"].astype(float); f = Z["f"].astype(np.int64)
    S, n, lo_eff = ES.compute(v, f, lo / 1000, hi / 1000, vox / 1000, band / 1000, quiet=True)
    S = ndimage.gaussian_filter(S.astype(np.float32) * 1000, sigma / vox, mode="nearest").astype(np.float32)
    t1 = time.time()
    # coat depth on a 1 mm grid: sum_k w_k typical_k (coat_field regions, NO furless masks) capped at 0.4 x local thickness
    gd = 1.0; nd = np.ceil((hi - lo) / gd).astype(int) + 1
    G = np.stack(np.meshgrid(*[lo[i] + np.arange(nd[i]) * gd for i in range(3)], indexing="ij"), -1).reshape(-1, 3)
    W = CF.weights(G / 1000); T = CF.typical(CF.COAT); d = np.zeros(len(G))
    for kk, w in W.items():
        d += w * T[kk]
    LT = np.load(os.path.join(os.environ.get("TEMP", "/tmp"), "p2_skin_v2", "full", "local_thickness.npz"))
    lt = ndimage.map_coordinates(LT["lt"].astype(np.float32), ((G / 1000 - LT["lo"]) / float(LT["vox"])).T, order=1, mode="nearest") * 1000
    K_TAPER = 0.4                                       # skin_build.K_TAPER (the skin's own thin-part taper)
    d_eff = np.minimum(d, K_TAPER * lt)
    np.savez_compressed(_cache_path(k), S=S, lo=lo_eff * 1000, vox=vox, d=d_eff.reshape(nd).astype(np.float32), d_raw=d.reshape(nd).astype(np.float32),
                        lo_d=lo, vox_d=gd, sigma=sigma, band=band,
                        meta=json.dumps(dict(what="Tripo exact SDF (mm, - inside) Gaussian sigma mm; coat depth d (mm, no furless mask, "
                                             "min(coat_field typical blend, 0.4 x local half-thickness))", seconds_sdf=round(t1 - t0, 1),
                                             seconds_total=round(time.time() - t0, 1), taper_binds_frac=float((d_eff < d - 1e-6).mean()))))
    return dict(paw=k, shape=list(S.shape), seconds=round(time.time() - t0, 1), taper_binds_frac=float((d_eff < d - 1e-6).mean()))


REG = {R["paw"]: R for R in REGIONS}
_C = {}


def _cache(k):
    if k not in _C:
        Z = np.load(_cache_path(k))
        _C[k] = dict(S=Z["S"], lo=Z["lo"].astype(float), vox=float(Z["vox"]), d=Z["d"], lo_d=Z["lo_d"].astype(float), vox_d=float(Z["vox_d"]))
    return _C[k]


def _keys_w(t):
    """Keys cubic (a = -0.5) weights for the 4 taps at offsets -1, 0, 1, 2 of fractional position t (N,)"""
    def w(s):
        s = np.abs(s); return np.where(s <= 1, 1.5 * s ** 3 - 2.5 * s ** 2 + 1, np.where(s < 2, -0.5 * s ** 3 + 2.5 * s ** 2 - 4 * s + 2, 0.0))
    return np.stack([w(t + 1), w(t), w(1 - t), w(2 - t)], 1)


def keys(A, X):
    """Keys-cubic interpolation of grid A at fractional index coordinates X (N,3) (clamped at the borders)"""
    out = np.empty(len(X)); n = np.array(A.shape); Af = A.reshape(-1)
    for a in range(0, len(X), 200000):
        x = X[a:a + 200000]; i0 = np.floor(x).astype(np.int64); t = x - i0
        W = [_keys_w(t[:, d]) for d in range(3)]
        I = [np.clip(i0[:, d, None] + np.arange(-1, 3)[None], 0, n[d] - 1) for d in range(3)]
        acc = np.zeros(len(x))
        for p in range(4):
            for q in range(4):
                base = (I[0][:, p] * n[1] + I[1][:, q]) * n[2]; wpq = W[0][:, p] * W[1][:, q]
                for r in range(4):
                    acc += wpq * W[2][:, r] * Af[base + I[2][:, r]]
        out[a:a + 200000] = acc
    return out


def S_mm(k, P):
    c = _cache(k); return keys(c["S"], (np.asarray(P, float) - c["lo"]) / c["vox"])


def gradS(k, P, h=0.05):
    P = np.atleast_2d(np.asarray(P, float))
    return np.stack([(S_mm(k, P + h * e) - S_mm(k, P - h * e)) / (2 * h) for e in np.eye(3)], 1)


def d_mm(k, P):
    from scipy import ndimage
    c = _cache(k); return ndimage.map_coordinates(c["d"], ((np.asarray(P, float) - c["lo_d"]) / c["vox_d"]).T, order=1, mode="nearest")


# ------------------------------------------------------------------ measured inputs (Phase 1) -> the paw's construction
_PJ = {}


def _pj():
    if not _PJ:
        _PJ.update(json.load(open(os.path.join(LAYERS, "paws.json")))["paws"])
    return _PJ


def _adiff(a, b):
    return (a - b + np.pi) % (2 * np.pi) - np.pi


def _moments(poly2):
    """area-weighted centroid and covariance of a closed 2-D polygon (Green's theorem) -> centroid, semi-axes, axes"""
    x, y = poly2[:, 0], poly2[:, 1]; x1, y1 = np.roll(x, -1), np.roll(y, -1); cr = x * y1 - x1 * y
    A = cr.sum() / 2; cx = ((x + x1) * cr).sum() / (6 * A); cy = ((y + y1) * cr).sum() / (6 * A)
    Ixx = ((x * x + x * x1 + x1 * x1) * cr).sum() / (12 * A) - cx * cx
    Iyy = ((y * y + y * y1 + y1 * y1) * cr).sum() / (12 * A) - cy * cy
    Ixy = ((x * y1 + 2 * x * y + 2 * x1 * y1 + x1 * y) * cr).sum() / (24 * A) - cx * cy
    ev, evec = np.linalg.eigh(np.array([[Ixx, Ixy], [Ixy, Iyy]]))
    return np.array([cx, cy]), 2 * np.sqrt(np.maximum(ev[::-1], 1e-9)), evec[:, ::-1], abs(A)


class Paw:
    """the construction of one paw (all mm). Derived once from the measurements; every derived value is in .rec"""

    def __init__(self, k):
        self.k = k; p = _pj()[k]; self.fore = k.startswith("fore"); self.rec = dict(paw=k)
        Rg = REG[k]; self.lo, self.hi = np.array(Rg["lo_mm"], float), np.array(Rg["hi_mm"], float)
        self.C = np.array(p["pads"]["central"]["core_outline"]["centroid_mm"], float)
        fw = np.array(p["forward_axis_xy"], float); self.fwd = fw / np.linalg.norm(fw)
        self.th = np.radians([p["toes"][t]["direction_deg"] for t in TOES])
        self.tip = np.array([p["toes"][t]["tip_mm"] for t in TOES], float)
        cl = list(p["clefts"].keys()); self.cth = np.radians([p["clefts"][c]["direction_deg"] for c in cl])
        self.sgn = np.sign(_adiff(self.th[3], self.th[0]))          # +1: angles increase medial -> lateral
        Zp = np.load(os.path.join(LAYERS, f"paws_pads_{k}.npz"))
        self.pads_in = {nm: dict(poly=Zp[f"core_{nm}"][:, :2] * 1000, low=float(p["pads"][nm]["lowest_z_mm"]),
                                 free=float(p["pads"][nm]["free_level_exact_z_mm"])) for nm in p["pads"]}
        frees = [v["free"] for v in self.pads_in.values()]
        self.z_s = float(np.median(frees)) + D_["SOLE_ABOVE_FREE_MM"]
        self.rec["sole"] = dict(z_s_mm=round(self.z_s, 3), rule="median measured pad free level + SOLE_ABOVE_FREE_MM",
                                pad_free_levels_mm={k_: round(v["free"], 3) for k_, v in self.pads_in.items()}, label="measured + rule")
        self._toes(); self._pads()
        if self.fore:
            self._dewclaw(p); self._carpal(p)
        self._sheaths()

    # ---- toes: hull per digit, lateral semi-axes solved through each cleft's web point
    def _march(self, a, z, u0=40.0, u1=-15.0, step=0.1):
        """the first crossing S = 0 marching along direction angle a from C at height z, from u0 back to u1"""
        t = np.array([np.cos(a), np.sin(a)]); u = np.arange(u0, u1, -step)
        P = np.c_[self.C + u[:, None] * t, np.full(len(u), z)]; s = S_mm(self.k, P)
        j = np.flatnonzero(s < 0)
        if not len(j): return None
        j = j[0]; return float(u[j - 1] + (u[j] - u[j - 1]) * s[j - 1] / (s[j - 1] - s[j])) if j > 0 else float(u[0])

    def _toe_top(self, a, u_lo, u_hi):
        """highest Tripo surface point over the toe axis between u_lo and u_hi (vertical march down from z 30)"""
        t = np.array([np.cos(a), np.sin(a)]); best = 0.0
        for u in np.arange(u_lo, u_hi, 0.5):
            z = np.arange(30.0, 0.0, -0.05); P = np.c_[np.tile(self.C + u * t, (len(z), 1)), z]; s = S_mm(self.k, P)
            j = np.flatnonzero(s < 0)
            if len(j): best = max(best, float(z[j[0]]))
        return best

    def skin_slice(self, z, step=0.2):
        """the skin-level envelope (S + d = 0) of the paw at height z: closed contours (world xy mm)"""
        from skimage import measure
        lo, hi = self.lo[:2], self.hi[:2]; nx, ny = (np.ceil((hi - lo) / step).astype(int) + 1)
        X, Y = np.meshgrid(lo[0] + np.arange(nx) * step, lo[1] + np.arange(ny) * step, indexing="ij")
        P = np.c_[X.ravel(), Y.ravel(), np.full(X.size, z)]; F = (S_mm(self.k, P) + d_mm(self.k, P)).reshape(nx, ny)
        return [lo + c * step for c in measure.find_contours(F, 0.0) if len(c) > 20]

    def _sector(self, i):
        """angular sector of toe i (relative to toe1, in the medial -> lateral sense): between its bounding cleft
        directions; an outer toe's outer bound = the mirror of its inner cleft about its axis (paws_toes convention)"""
        rel = lambda a: _adiff(a, self.th[0]) * self.sgn
        cl = [rel(c) for c in self.cth]; ax = rel(self.th[i])
        lo_ = cl[i - 1] if i > 0 else 2 * ax - cl[0]
        hi_ = cl[i] if i < 3 else 2 * ax - cl[2]
        return lo_, hi_

    def _fit_circle(self, i, zs):
        """least-squares (Kasa) circle through toe i's own FRONT arc on the skin-level slices at heights zs"""
        lo_, hi_ = self._sector(i); pts = []
        for z in zs:
            for c in self.skin_slice(z):
                q = c - self.C; r = np.linalg.norm(q, axis=1); a = _adiff(np.arctan2(q[:, 1], q[:, 0]), self.th[0]) * self.sgn
                m = (a > lo_ + np.radians(3)) & (a < hi_ - np.radians(3))
                if m.sum() < 10: continue
                m &= r > r[m].max() - 6.0                           # the front arc only
                pts.append(c[m])
        Q = np.vstack(pts); A = np.c_[2 * Q, np.ones(len(Q))]; sol, *_ = np.linalg.lstsq(A, (Q ** 2).sum(1), rcond=None)
        cen = sol[:2]; r = float(np.sqrt(sol[2] + cen @ cen)); res = np.linalg.norm(Q - cen, axis=1) - r
        return cen, r, dict(n=int(len(Q)), rms_mm=float(np.sqrt(np.mean(res ** 2))), heights_mm=[float(z) for z in zs])

    def _toes(self):
        """digits II-V as ROUNDED PARAMETRIC DIGITS (the class model), each an ellipsoid on its measured direction with
        octant-wise semi-axes: front reaching the measured tip (skin level), top the measured toe top (skin level),
        bottom below the sole plane (trimmed there), back running into the palm. The lateral semi-axes come from the
        CLEFT RULE: two neighbouring digits whose centres are s apart leave a plan notch D = b - sqrt(b^2 - s^2/4) at
        their mid height; b is set so D = CLEFT_TARGET (b = (s^2/4 + D^2) / 2D); the front semi-axis = TOE_FRONT_ROUND x b,
        so the centres (and s) are iterated to a fixed point."""
        k = self.k; H = []
        for i in range(4):
            a = self.th[i]; t = np.array([np.cos(a), np.sin(a)]); nrm = np.array([-t[1], t[0]])
            u_tip = float((self.tip[i, :2] - self.C) @ t); d_tip = float(d_mm(k, self.tip[i][None])[0])
            u_leg = self._march(a, 24.0)                       # the leg's front above the toes (Tripo, fur level)
            d_leg = float(d_mm(k, np.r_[self.C + u_leg * t, 24.0][None])[0])
            u_root = u_leg - d_leg + 0.5                          # just in front of the leg's skin
            z_top = self._toe_top(a, u_leg + 1.0, u_tip)
            d_top = float(d_mm(k, np.r_[self.C + 0.5 * (u_leg + u_tip) * t, z_top][None])[0])
            z_top_s = z_top - d_top; z_c = float(self.tip[i, 2])          # the digit's front-most point at Tripo's tip height
            uu = np.arange(u_leg + 1.0, u_tip, 0.5); prof = np.array([self._toe_top(a, x, x + 0.01) for x in uu])
            prof_s = prof - d_mm(k, np.c_[self.C + uu[:, None] * t, prof])  # Tripo's skin-level top profile along the axis
            H.append(dict(toe=TOES[i], a=a, t=t, n=nrm, u_root=u_root, u_tip_skin=u_tip - d_tip, z_c=z_c, c_up=z_top_s - z_c,
                          c_dn=D_["TOE_CDN_FACTOR"] * (z_c - self.z_s), z_top_fur=z_top, z_top_skin=z_top_s, u_leg_fur=u_leg, d_tip=d_tip,
                          b={+1: 5.0, -1: 5.0}, top_u=uu, top_z=prof_s))
        extra = np.zeros(3)                                     # per-cleft extra rule depth (2nd pass: the fit's front recession)
        for pass_ in range(2):
            for T_ in H:
                T_["b"] = {+1: 5.0, -1: 5.0}; T_.pop("b_side_out", None)
            for it in range(8):
                for T_ in H:
                    T_["a_f"] = D_["TOE_FRONT_ROUND"] * 0.5 * (T_["b"][1] + T_["b"][-1])
                    T_["u_c"] = T_["u_tip_skin"] - T_["a_f"]; T_["cen"] = self.C + T_["u_c"] * T_["t"]
                    T_["c_up"] = max(float(np.interp(T_["u_c"], T_["top_u"], T_["top_z"])) - T_["z_c"], 3.0)   # top over the centre
                for c in range(3):
                    A_, B_ = H[c], H[c + 1]; s_ = float(np.linalg.norm(B_["cen"] - A_["cen"])); Dt = D_["CLEFT_TARGET_MM"] + extra[c]
                    b_new = (s_ ** 2 / 4 + Dt ** 2) / (2 * Dt)
                    for T_, other in ((A_, B_), (B_, A_)):
                        T_["b"][int(np.sign((other["cen"] - T_["cen"]) @ T_["n"])) or 1] = b_new
                for i in (0, 3):                                # an outer digit's outer side mirrors its inner side
                    T_ = H[i]; inner = H[1 if i == 0 else 2]; si = int(np.sign((inner["cen"] - T_["cen"]) @ T_["n"])) or 1
                    T_["b"][-si] = T_["b"][si]
            for T_ in H:
                T_["a_b"] = max(T_["u_c"] - T_["u_root"] + 4.0, D_["TOE_BACK_FACTOR"] * T_["a_f"])
            # an OUTER digit's outer flank sits where Tripo's skin-level flank is (measured along the line through the
            # digit's centre, across its axis, at its centre height): the flank and the paw's side wall meet tangentially
            for i in (0, 3):
                T_ = H[i]; inner = H[1 if i == 0 else 2]; si = int(np.sign((inner["cen"] - T_["cen"]) @ T_["n"])) or 1
                v = np.arange(0.0, 20.0, 0.05); Q = np.c_[T_["cen"] - si * v[:, None] * T_["n"], np.full(len(v), T_["z_c"])]
                f = S_mm(k, Q) + d_mm(k, Q); j = np.flatnonzero(f > 0)
                v_out = float(v[j[0]]) if len(j) else T_["b"][si]
                T_["b"][-si] = float(np.clip(v_out, D_["OUTER_B_RANGE"][0] * T_["b"][si], D_["OUTER_B_RANGE"][1] * T_["b"][si]))
                T_["b_out_measured"] = v_out; T_["b_side_out"] = T_["b"][-si]
            # SEEN-SIDE FIT: each digit's crown (rays from its centre within +-20 deg of its axis plane, from 20 deg below
            # its forward direction to 80 deg above it) against Tripo inset by the coat. The median of that field there is
            # the digit's OFFSET: the whole digit field moves by it (its shape is unchanged; a crown-band-only offset left
            # vertical bevels on the toe fronts, measured on renders), its lateral semi-axes are widened by the same amount
            # so the cleft rule and the measured outer flank hold. Measured need: the ellipsoid crowns stood up to ~1 mm
            # proud of Tripo minus the coat. The fronts recede by it, so the 2nd pass asks the cleft rule for that much
            # more depth (extra = the two digits' mean offset).
            for T_ in H:
                ph, ps = np.meshgrid(np.radians(np.arange(-20, 81, 5)), np.radians(np.arange(-20, 21, 5)), indexing="ij"); ph, ps = ph.ravel(), ps.ravel()
                dl = np.c_[np.cos(ph) * np.cos(ps), np.sin(ps), np.sin(ph) * np.cos(ps)]
                ax_ = np.c_[np.full(len(dl), T_["a_f"]), np.where(dl[:, 1] >= 0, T_["b"][1], T_["b"][-1]), np.where(dl[:, 2] >= 0, T_["c_up"], T_["c_dn"])]
                sr = 1.0 / np.linalg.norm(dl / ax_, axis=1)
                Pw = np.c_[T_["cen"][0] + sr * (dl[:, 0] * T_["t"][0] + dl[:, 1] * T_["n"][0]), T_["cen"][1] + sr * (dl[:, 0] * T_["t"][1] + dl[:, 1] * T_["n"][1]), T_["z_c"] + sr * dl[:, 2]]
                Pw = Pw[Pw[:, 2] > self.z_s + 1.0]
                T_["fit"] = float(np.clip(np.median(S_mm(k, Pw) + d_mm(k, Pw)), -D_["DIGIT_FIT_MAX_MM"], D_["DIGIT_FIT_MAX_MM"]))
                if pass_ == 0: T_["fit1"] = T_["fit"]
                T_["b"] = {s_: bb + T_["fit"] for s_, bb in T_["b"].items()}       # the lateral extents stay the rule's
                if "b_side_out" in T_: T_["b_side_out"] += T_["fit"]
            if pass_ == 1: break
            extra = np.array([max(0.0, 0.5 * (H[c]["fit1"] + H[c + 1]["fit1"])) for c in range(3)])
        self.web = []
        for c in range(3):
            A_, B_ = H[c], H[c + 1]; s_ = float(np.linalg.norm(B_["cen"] - A_["cen"])); bA = A_["b"][int(np.sign((B_["cen"] - A_["cen"]) @ A_["n"])) or 1]
            self.web.append(dict(cleft=c, centre_spacing_mm=s_, facing_semi_axis_mm=float(bA), rule_depth_mm=float(D_["CLEFT_TARGET_MM"] + extra[c]),
                                 plan_notch_mm=float(bA - np.sqrt(max(bA ** 2 - s_ ** 2 / 4, 0.0)))))
        self.hull = H
        self.rec["toes"] = [dict(toe=T_["toe"], direction_deg=round(float(np.degrees(T_["a"])), 2), centre_xy_mm=np.round(T_["cen"], 2).tolist(),
                                 u_root_mm=round(T_["u_root"], 2), u_centre_mm=round(T_["u_c"], 2), u_tip_skin_mm=round(T_["u_tip_skin"], 2),
                                 z_c_mm=round(T_["z_c"], 2), z_top_fur_mm=round(T_["z_top_fur"], 2), z_top_skin_mm=round(T_["z_top_skin"], 2),
                                 a_front_mm=round(T_["a_f"], 2), a_back_mm=round(T_["a_b"], 2), c_up_mm=round(T_["c_up"], 2), c_dn_mm=round(T_["c_dn"], 2),
                                 b_pos_mm=round(T_["b"][1], 2), b_neg_mm=round(T_["b"][-1], 2), seen_fit_offset_mm=round(T_.get("fit", 0.0), 3), b_outer_flank_measured_mm=(round(T_["b_out_measured"], 2) if "b_out_measured" in T_ else None),
                                 label="direction / tip / top / leg front measured on Tripo (fur level -> skin by the coat); the digit's lateral size from the cleft rule (spec CLEFT_TARGET), its front roundness and depth below the sole from spec (estimated)")
                            for T_ in H]
        self.rec["webs"] = [{k_: (round(v, 3) if isinstance(v, float) else v) for k_, v in w.items()} for w in self.web]

    def R_root(self, ang):
        """plan root radius by angle: the digits' roots interpolated across the fan; beyond an OUTER digit's axis it moves
        forward to that digit's centre over its angular half-width, so on the paw's outer flanks the field hands over to
        Tripo's side wall at the digit's widest point (where the digit's flank was set tangent to it)"""
        rel = _adiff(ang, self.th[0]) * self.sgn; span = _adiff(self.th[3], self.th[0]) * self.sgn
        rr = np.array([T_["u_root"] for T_ in self.hull]); at = np.array([_adiff(self.th[i], self.th[0]) * self.sgn for i in range(4)])
        R = np.interp(np.clip(rel, 0, span), at, rr)
        for i, o in ((0, -rel), (3, rel - span)):
            T_ = self.hull[i]; h = np.arctan2(T_["b_side_out"], T_["u_c"]); g = ss(np.clip(o, 0, None) / h)
            R = np.where(o > 0, R + g * (T_["u_c"] - T_["u_root"]), R)
        return R

    def fan_weight(self, ang):
        """1 inside the toe fan out to each outer digit's angular half-width, smoothstep to 0 over KEEP_OPEN_DEG beyond"""
        rel = _adiff(ang, self.th[0]) * self.sgn; span = _adiff(self.th[3], self.th[0]) * self.sgn
        h0 = np.arctan2(self.hull[0]["b_side_out"], self.hull[0]["u_c"]); h3 = np.arctan2(self.hull[3]["b_side_out"], self.hull[3]["u_c"])
        out_ = np.maximum(-rel - h0, rel - span - h3); return 1 - ss(out_ / np.radians(D_["KEEP_OPEN_DEG"]))

    def z_top(self, ang):
        """the digits' skin-level tops interpolated by angle"""
        rel = _adiff(ang, self.th[0]) * self.sgn; span = _adiff(self.th[3], self.th[0]) * self.sgn
        zt = np.array([T_["z_c"] + T_["c_up"] for T_ in self.hull]); at = np.array([_adiff(self.th[i], self.th[0]) * self.sgn for i in range(4)])
        return np.interp(np.clip(rel, 0, span), at, zt)

    def toe_weight(self, P):
        """0..1: where the parametric digits replace Tripo's (merged) toe mass: 0 behind the digit roots (R_root = the leg's
        skin front at z 24 mm + 0.5, so the leg is never mixed), smoothstep to 1 over TOE_BLEND in front of them, at every
        height (a height fade left Tripo's merged top as a thin shelf over the dorsal clefts: hind.R vsec, 2026-10-18).
        The field is a CONVEX MIX of two near-SDFs: no cut, no corner; a cleft fades out across the roots (the web)"""
        q = P[:, :2] - self.C; r = np.linalg.norm(q, axis=1); ang = np.arctan2(q[:, 1], q[:, 0]); W = D_["TOE_BLEND_MM"]
        return ss((r - self.R_root(ang)) / W) * self.fan_weight(ang)

    def toe_hull(self, P, i):
        """a digit: in plan an ellipse (the cleft rule holds exactly at its centre height), in every vertical section a
        SUPERELLIPSE of exponent TOE_PROFILE_P (a blunt front and a flat-ish crown like the measured toe fronts; p = 2 left
        the fronts ~1 mm behind Tripo-minus-coat, P-SEEN). Octant-wise semi-axes. First-order distance (k - 1) / |grad k|."""
        T_ = self.hull[i]; q = P[:, :2] - T_["cen"]; u = q @ T_["t"]; v = q @ T_["n"]; w = P[:, 2] - T_["z_c"]
        p = D_["TOE_PROFILE_P"]
        if p == 2.0:                                   # the ellipsoid (IQ's bound, as proven by the checks), + its seen-side fit
            return ell_sdf(np.c_[u, v, w], [T_["a_f"], T_["b"][1], T_["c_up"]], [T_["a_b"], T_["b"][-1], T_["c_dn"]]) + T_.get("fit", 0.0)
        a = np.where(u >= 0, T_["a_f"], T_["a_b"]); b = np.where(v >= 0, T_["b"][1], T_["b"][-1]); c = np.where(w >= 0, T_["c_up"], T_["c_dn"])
        x, y, zz = u / a, v / b, np.abs(w) / c
        rho = np.sqrt(x * x + y * y) + 1e-12; k = (rho ** p + zz ** p) ** (1.0 / p)
        kp = np.maximum(k, 1e-12) ** (1.0 - p)
        dk_drho = rho ** (p - 1) * kp; dk_dz = zz ** (p - 1) * kp / c
        gu = dk_drho * (x / a) / rho; gv = dk_drho * (y / b) / rho
        return (k - 1.0) / np.maximum(np.sqrt(gu * gu + gv * gv + dk_dz * dk_dz), 1e-9)

    def keep(self, P):
        """the palm / leg keep region (negative inside): behind the toe roots in plan (R_root by angle, open beyond the
        toe fan) OR above the local digit top (z_keep by angle): the cut only removes Tripo's merged toe mass in front
        of the roots and below the digits' tops, where the parametric digits replace it"""
        q = P[:, :2] - self.C; r = np.linalg.norm(q, axis=1); ang = np.arctan2(q[:, 1], q[:, 0])
        return smin(r - self.R_root(ang), self.z_keep(ang) - P[:, 2], 1.0)

    def z_keep(self, ang):
        rel = _adiff(ang, self.th[0]) * self.sgn; span = _adiff(self.th[3], self.th[0]) * self.sgn
        zt = np.array([T_["z_c"] + T_["c_up"] for T_ in self.hull]); at = np.array([_adiff(self.th[i], self.th[0]) * self.sgn for i in range(4)])
        return np.interp(np.clip(rel, 0, span), at, zt) + 0.3

    # ---- pads
    def _dome(self, cen, axes2, evec, low, h, c_over_h=None):
        c = (c_over_h or D_["DOME_C_OVER_H"]) * h; fs = np.sqrt(1 - (1 - h / c) ** 2)
        return dict(cen=np.r_[cen, low + c], ax=np.r_[axes2 / fs, c], R=np.c_[np.r_[evec[:, 0], 0], np.r_[evec[:, 1], 0], [0, 0, 1]], h=h)

    def dome_sdf(self, P, D):
        return ell_sdf((P - D["cen"]) @ D["R"], D["ax"])

    def _pads(self):
        """pads at the MEASURED positions / lowest points, ANATOMICAL shapes: each digital pad an oval under its digit
        (centre = Tripo's pad centroid projected onto the digit's axis, long axis along the digit, aspect PAD_ASPECT,
        area <= Tripo's core area), the main pad trilobed caudally (paw frame, Tripo's core extents). One scale per pad
        (positions about its centre included) is bisected so its whole rim lies >= PAD_MARGIN inside the paw's wall at
        z_s + 0.3 (no pad wider than its toe: a pad sticking out IS the coin ledge)"""
        self.domes = []; recs = []
        need = 0.0                         # the rim, pushed out sideways by 0.6 + 0.3 mm, still inside the wall at z_s + 0.3
        for nm, pi in self.pads_in.items():
            cen, ax2, evec, area = _moments(pi["poly"])
            main = nm == "central"; h_cap = SPEC["anatomy"]["pad_thickness_main_mm" if main else "pad_thickness_digital_mm"]["value"][1]
            h = float(np.clip(self.z_s - pi["low"], 0.4, h_cap))
            if main:      # trilobed caudal border: a front body + three caudal lobes (paw frame: f forward, l lateral)
                fwd = self.fwd; lat = np.array([-fwd[1], fwd[0]]); pf = (pi["poly"] - cen) @ fwd; pl = (pi["poly"] - cen) @ lat
                Af, Al = 2 * np.sqrt(np.mean(pf ** 2)), 2 * np.sqrt(np.mean(pl ** 2))
                Ev = np.c_[fwd, lat]; c0 = cen
                parts = [(0.12 * Af * fwd, np.array([0.80 * Af, 0.95 * Al]))]      # the pad's body (single gentle leading lobe)
                for s_ in (-0.50, 0.0, 0.50):                                      # three caudal lobes fused into it
                    parts.append((-0.36 * Af * fwd + s_ * Al * lat, np.array([0.46 * Af, 0.40 * Al])))
            else:
                T_ = self.hull[TOES.index(nm)]; t = T_["t"]
                c0 = T_["cen"] + ((cen - T_["cen"]) @ t) * t            # measured fore-aft position, centred under the digit
                bq = np.sqrt(area / (np.pi * D_["PAD_ASPECT"]))            # Tripo's core area as an oval of the anatomical aspect
                Ev = np.c_[t, np.array([-t[1], t[0]])]; parts = [(np.zeros(2), np.array([D_["PAD_ASPECT"] * bq, bq]))]

            def worst(scale):
                pts = []
                for off, a2 in parts:
                    ph = np.linspace(0, 2 * np.pi, 72, endpoint=False); e = np.c_[np.cos(ph) * a2[0] * scale, np.sin(ph) * a2[1] * scale]
                    rim = c0 + off * scale + e @ Ev.T; o = rim - (c0 + off * scale); o /= np.maximum(np.linalg.norm(o, axis=1), 1e-9)[:, None]
                    pts.append(rim + (D_["PAD_MARGIN_MM"] + 0.3) * o)       # the rim pushed out sideways by the margin ...
                Q = np.vstack(pts)                                            # ... must still be inside the wall (no sole trim)
                return float(self.field_nopads(np.c_[Q, np.full(len(Q), self.z_s + 0.3)], sole=False).max())
            lo_, hi_ = 0.1, 1.0
            if worst(1.0) <= need: sc = 1.0
            else:
                for _ in range(24):
                    mid = 0.5 * (lo_ + hi_)
                    if worst(mid) <= need: lo_ = mid
                    else: hi_ = mid
                sc = lo_
            ds = [self._dome(c0 + off * sc, a2 * sc, Ev, pi["low"], h) for off, a2 in parts]
            self.domes.append(dict(pad=nm, parts=ds, main=main, centre=c0))
            recs.append(dict(pad=nm, centre_xy_mm=np.round(c0, 2).tolist(), measured_centroid_xy_mm=np.round(cen, 2).tolist(),
                             lowest_z_mm=round(pi["low"], 3), protrusion_mm=round(h, 3), footprint_scale=round(sc, 3),
                             footprint_semi_axes_mm=[round(float(x), 2) for x in parts[0][1] * sc], measured_core_area_mm2=round(area, 1),
                             built_footprint_area_mm2=round(float(sum(np.pi * a2[0] * a2[1] for _, a2 in parts[:1])) * sc * sc, 1),
                             lobes=len(parts) - 1 if main else 0, dome_c_mm=round(ds[0]["ax"][2], 3),
                             label="position / lowest point / core size measured (paws.json, paws_pads npz); shape anatomical (oval digital pads, "
                                   "trilobed main pad); scale bisected to the wall margin (checked at build)"))
        self.rec["pads"] = recs

    def pads_sdf(self, P):
        out = np.full(len(P), np.inf)
        for D in self.domes:
            dd = np.full(len(P), np.inf)
            for part in D["parts"]:
                dd = smin(dd, self.dome_sdf(P, part), D_["K_LOBE_MM"]) if np.isfinite(dd).any() else self.dome_sdf(P, part)
            out = np.minimum(out, dd)
        return out

    # ---- fore extras
    def _skin_point(self, P_fur):
        """skin point under a Tripo surface point: P - n d (n = outward normal of S)"""
        g = gradS(self.k, P_fur[None])[0]; n = g / np.linalg.norm(g); d = float(d_mm(self.k, P_fur[None])[0])
        return P_fur - n * d, n, d

    def _dewclaw(self, p):
        """digit I on the medial metacarpus at the MEASURED section lobe (paws.json dewclaw.section_lobe). A dewclaw hangs
        FREE above the paw: if its distal end would sink into the paw (the leg flares into the paw below the lobe), it is
        moved up along the leg in 0.5 mm steps (<= DEWCLAW.max_lift_mm) until its tip clears the paw by >= 0.5 mm; the lift
        is recorded. The person flagged the lump at z ~18-19 (NOTES_v3 13:33, LOCATE L1 candidates), inside the measured
        lobe's z range (13/14-19 mm)."""
        L = p["dewclaw"]["section_lobe"]; ap = np.array(L["apex_mm_at_max_bulge"], float); DC = D_["DEWCLAW"]
        ax = np.array([DC["len_mm"] / 2, DC["width_mm"] / 2, DC["thick_mm"] / 2])
        Ps0, n0, d0 = self._skin_point(ap)
        a1_0 = np.r_[np.sin(np.radians(DC["tilt_fwd_deg"])) * self.fwd, -np.cos(np.radians(DC["tilt_fwd_deg"]))]
        lift = 0.0
        for lift in np.arange(0.0, DC["max_lift_mm"] + 1e-6, 0.5):
            Q = ap + lift * np.array([0, 0, 1.0])
            # the Tripo surface point at this height on the same horizontal line through the lobe apex, along -n0
            ts = np.arange(4.0, -6.0, -0.02); L_ = Q[None] + ts[:, None] * np.r_[n0[:2], 0.0] / np.linalg.norm(n0[:2])
            sv = S_mm(self.k, L_); j = np.flatnonzero(sv < 0)
            Qs = L_[j[0]] if len(j) else Q
            Ps, n, d = self._skin_point(Qs)
            a1 = a1_0 - (a1_0 @ n) * n; a1 /= np.linalg.norm(a1)
            cen = Ps + n * (DC["protrude_mm"] - DC["thick_mm"] / 2)
            tip_out = cen + a1 * (ax[0] + 0.5)
            if float(smin(self.field_nopads(tip_out[None]), self.pads_sdf(tip_out[None]), D_["K_PAD_MM"])[0]) >= 0.5:
                break
        a2 = np.cross(n, a1)
        self.dc = dict(cen=cen, R=np.c_[a1, a2, n], ax=ax, n=n)
        # its pad: on the dewclaw's caudal-distal face
        back = -np.r_[self.fwd, 0.0]; back = back - (back @ n) * n; back /= np.linalg.norm(back)
        dirp = 0.55 * a1 + 0.83 * back; dirp /= np.linalg.norm(dirp)
        loc = (dirp @ self.dc["R"]); s_ = 1.0 / np.linalg.norm(loc / self.dc["ax"])
        Psurf = cen + s_ * dirp
        pa = DC["pad_mm"]; c_ = 2.5 * pa[2]; npad = dirp
        e1 = np.cross(npad, a2); e1 /= np.linalg.norm(e1); e2 = np.cross(npad, e1)
        self.dc_pad = dict(cen=Psurf - npad * (c_ - pa[2]), R=np.c_[e1, e2, npad], ax=np.array([pa[0] / 2, pa[1] / 2, c_]))
        tipP = cen + a1 * ax[0]                                            # the digit's distal end (on its ellipsoid)
        self.rec["dewclaw"] = dict(apex_fur_mm=ap.round(2).tolist(), lift_mm=float(lift), skin_point_mm=Ps.round(2).tolist(), normal=n.round(3).tolist(),
                                   coat_mm=round(d, 3), centre_mm=cen.round(2).tolist(), axis_down=a1.round(3).tolist(), tip_mm=tipP.round(2).tolist(),
                                   semi_axes_mm=self.dc["ax"].round(2).tolist(), pad_centre_mm=self.dc_pad["cen"].round(2).tolist(),
                                   person_flag_L1_mm={"fore.R": [-11.2, -138.0, 19.0], "fore.L": [8.6, -141.5, 18.3]}.get(self.k),
                                   label="position measured (paws.json dewclaw.section_lobe, fur level -> skin by the coat; lifted so it hangs free); size estimated (spec DEWCLAW)")
        self._dc_tip = (tipP, a1, a2)

    def _carpal(self, p):
        pts = p["carpal"]["back_profile_convex_points"]; best = min(pts, key=lambda q: abs(q["offset_mm"]))
        ap = np.array(best["apex_world_mm"], float); Ps, n, d = self._skin_point(ap); CP = D_["CARPAL"]
        up = np.array([0, 0, 1.0]); e1 = up - (up @ n) * n; e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
        self.cp = dict(cen=Ps - n * (CP["c_mm"] - CP["protrude_mm"]), R=np.c_[e1, e2, n], ax=np.array([CP["axes_mm"][0], CP["axes_mm"][1], CP["c_mm"]]))
        self.rec["carpal"] = dict(apex_fur_mm=ap.round(2).tolist(), skin_point_mm=Ps.round(2).tolist(), normal=n.round(3).tolist(), coat_mm=round(d, 3),
                                  centre_mm=self.cp["cen"].round(2).tolist(), semi_axes_mm=self.cp["ax"].round(2).tolist(),
                                  label="position measured (paws.json carpal wrist contour angle, offset 0); size estimated (spec CARPAL)")

    # ---- claw sheaths
    def _sheaths(self):
        SH = D_["SHEATH"]; self.sh = []; recs = []
        for i, T_ in enumerate(self.hull):
            z = self.z_s + SH["open_above_sole_mm"]; t = np.r_[T_["t"], 0.0]
            u = np.arange(T_["u_tip_skin"] + 4.0, T_["u_root"], -0.05)
            P = np.c_[self.C + u[:, None] * T_["t"], np.full(len(u), z)]; F = self.field_nopads(P, sheaths=False, pads=True)
            j = np.flatnonzero(F < 0)
            if not len(j): continue
            O = P[j[0]]; ax = -np.cos(np.radians(SH["tilt_deg"])) * t + np.sin(np.radians(SH["tilt_deg"])) * np.array([0, 0, 1.0])
            O0 = O - 0.6 * ax; lat = np.r_[T_["n"], 0.0]
            self.sh.append(dict(O=O0, ax=ax, lat=lat, L=SH["depth_mm"] + 0.6, hw=SH["width_mm"] / 2, ht=SH["thick_mm"] / 2, pre=0.6))
            recs.append(dict(toe=T_["toe"], opening_mm=O.round(2).tolist(), axis=ax.round(3).tolist(), label="estimated (spec SHEATH) at the measured toe direction"))
        if self.fore:
            tipP, a1, a2 = self._dc_tip; DS = D_["DEWCLAW"]["sheath"]; ax = -a1
            self.sh.append(dict(O=tipP - 0.5 * ax, ax=ax, lat=a2, L=DS["depth_mm"] + 0.5, hw=DS["width_mm"] / 2, ht=DS["thick_mm"] / 2, pre=0.5))
            recs.append(dict(toe="dewclaw", opening_mm=tipP.round(2).tolist(), axis=ax.round(3).tolist(), label="estimated (spec DEWCLAW.sheath) at the digit's distal end"))
        self.rec["sheaths"] = recs

    def sheath_sdf(self, P):
        out = np.full(len(P), np.inf)
        for s in self.sh:
            bb = np.linalg.norm(P - (s["O"] + 0.5 * s["L"] * s["ax"]), axis=1) < 0.5 * s["L"] + 3.0
            if bb.any():
                o = np.full(len(P), np.inf); o[bb] = slot_sdf(P[bb], s["O"], s["ax"], s["lat"], s["L"], s["hw"], s["ht"]); out = np.minimum(out, o)
        return out

    # ---- the field
    def field_nopads(self, P, sheaths=False, pads=False, sole=True):
        P = np.atleast_2d(np.asarray(P, float)); k = self.k
        zw = self.z_s + D_["WALL_EXTRUDE_ABOVE_SOLE_MM"]; e = D_["WALL_EXTRUDE_SOFT_MM"]
        Pz = P.copy(); dz = P[:, 2] - zw; Pz[:, 2] = zw + 0.5 * (dz + np.sqrt(dz * dz + e * e))   # smooth max(z, z_w)
        F = S_mm(k, Pz) + d_mm(k, Pz)                       # palm / leg: Tripo inset by the coat; below z_w its walls run straight down
        w = self.toe_weight(P); m = w > 0
        if m.any():
            T = self.toe_hull(P[m], 0)
            for i in range(1, 4):
                T = smin(T, self.toe_hull(P[m], i), D_["K_WEB_MM"])               # the digits, joined by the interdigital web
            F[m] = (1 - w[m]) * F[m] + w[m] * T                                  # the digits replace Tripo's toe mass
        if sole:
            F = smax(F, self.z_s - P[:, 2], D_["K_SOLE_MM"])                     # the furred sole between the pads
        if pads:
            F = smin(F, self.pads_sdf(P), D_["K_PAD_MM"])
            if self.fore:
                F = self._fore(P, F)
        if sheaths:
            F = smax(F, -self.sheath_sdf(P), D_["SHEATH"]["k_mm"])
        return F

    def _fore(self, P, F):
        dc = ell_sdf((P - self.dc["cen"]) @ self.dc["R"], self.dc["ax"])
        dc = smin(dc, ell_sdf((P - self.dc_pad["cen"]) @ self.dc_pad["R"], self.dc_pad["ax"]), 0.3)
        F = smin(F, dc, D_["DEWCLAW"]["k_mm"])
        F = smin(F, ell_sdf((P - self.cp["cen"]) @ self.cp["R"], self.cp["ax"]), D_["CARPAL"]["k_mm"])
        return F

    def field(self, P):
        return self.field_nopads(P, sheaths=True, pads=True)

    def _pad_surface_tree(self):
        """the EXPOSED pad skin as dense surface samples (0.1 mm): each dome part's surface below the sole plane + 0.3 mm,
        the dewclaw pad's and the carpal pad's surfaces where they stand out of the rest of the paw. Distances to it are
        true Euclidean distances (|grad| = 1): a first-order E / |grad E| on small, strongly curved pads read the 2 mm ramp
        up to 1.1 / mm (P-FURL, fore.L)"""
        if getattr(self, "_ptree", None) is not None:
            return self._ptree
        from scipy.spatial import cKDTree
        def ell_pts(cen, R, ax, step=0.1):
            n_t = max(int(np.pi * max(ax) / step), 24); n_p = max(int(2 * np.pi * max(ax) / step), 48)
            th, ph = np.meshgrid(np.linspace(0, np.pi, n_t), np.linspace(0, 2 * np.pi, n_p, endpoint=False), indexing="ij")
            loc = np.c_[(np.sin(th) * np.cos(ph)).ravel() * ax[0], (np.sin(th) * np.sin(ph)).ravel() * ax[1], np.cos(th).ravel() * ax[2]]
            return cen + loc @ R.T
        pts = []
        for D in self.domes:
            for part in D["parts"]:
                q = ell_pts(part["cen"], part["R"], part["ax"]); pts.append(q[q[:, 2] <= self.z_s + 0.3])
        if self.fore:
            for E in (self.dc_pad, self.cp):
                q = ell_pts(E["cen"], E["R"], E["ax"]); f = self.field_nopads(q, pads=False)
                pts.append(q[f > -0.1])
        self._ptree = cKDTree(np.vstack(pts)); return self._ptree

    def furless(self, P):
        """1 on hairless pad skin, ramping to 0 over FURLESS_RAMP (>= 2 mm) with the true 3-D distance from the exposed pad
        surface (= along the skin near it; NOT a z prism); 0.05 mm = the sample spacing's half. The claw-sheath pockets' lining is hidden air: not part of the mask (hair grows to
        the sheath's mouth, as on a real toe)"""
        P = np.atleast_2d(np.asarray(P, float)); d, _ = self._pad_surface_tree().query(P, workers=-1)
        return 1 - ss(np.maximum(d - 0.05, 0.0) / D_["FURLESS_RAMP_MM"])


_PAW = {}


def paw(k):
    if k not in _PAW:
        _PAW[k] = Paw(k)
    return _PAW[k]


def _in_region(P, R, pad=0.0):
    return np.all((P >= np.array(R["lo_mm"]) - pad) & (P <= np.array(R["hi_mm"]) + pad), axis=1)


def region_weight(P, R):
    """1 inside, smoothstep to 0 over BLEND at the REGION faces"""
    lo, hi = np.array(R["lo_mm"]), np.array(R["hi_mm"]); dmin = np.minimum((P - lo).min(1), (hi - P).min(1))
    return ss(dmin / D_["BLEND_MM"])


# ------------------------------------------------------------------ the interface
def edit(P_mm, F_mm, chunk=300000):
    """skin field edit (mm, negative inside). Inside each paw REGION: F_in + w (F_paw - F_in); unchanged elsewhere"""
    P = np.asarray(P_mm, float); F = np.array(F_mm, float, copy=True)
    for R in REGIONS:
        idx = np.flatnonzero(_in_region(P, R))
        if not len(idx): continue
        pw = paw(R["paw"])
        for a in range(0, len(idx), chunk):
            ii = idx[a:a + chunk]; w = region_weight(P[ii], R); Fp = pw.field(P[ii])
            F[ii] = F[ii] + w * (Fp - F[ii])
    return F


def paw_field(k, P_mm):
    return paw(k).field(np.asarray(P_mm, float))


def furless_mask(P_mm):
    P = np.asarray(P_mm, float); out = np.zeros(len(P))
    for R in REGIONS:
        idx = np.flatnonzero(_in_region(P, R))
        if len(idx): out[idx] = paw(R["paw"]).furless(P[idx]) * region_weight(P[idx], R)
    return out


def opening_sdf(P_mm):
    """intended air fill_voids must never seal: the claw-sheath pockets (mm, < 0 inside)"""
    P = np.asarray(P_mm, float); out = np.full(len(P), np.inf)
    for R in REGIONS:
        idx = np.flatnonzero(_in_region(P, R))
        if len(idx): out[idx] = paw(R["paw"]).sheath_sdf(P[idx])
    return out


def coat_depth_mm(P_mm):
    """the coat depth the fur stage should grow in the paw REGIONS: d x (1 - furless_mask) (inside REGIONS only; NaN outside)"""
    P = np.asarray(P_mm, float); out = np.full(len(P), np.nan)
    for R in REGIONS:
        idx = np.flatnonzero(_in_region(P, R))
        if len(idx): out[idx] = d_mm(R["paw"], P[idx]) * (1 - paw(R["paw"]).furless(P[idx]))
    return out


def contract_probe(grid_mm, sheath_grid_mm=None):
    sg = grid_mm if sheath_grid_mm is None else sheath_grid_mm
    ok = grid_mm <= NEED_MM + 1e-9 and sg <= NEED_MM_SHEATH + 1e-9
    return dict(status="PASS" if ok else "FAIL", grid_mm=grid_mm, sheath_grid_mm=sg, need_mm=NEED_MM, need_sheath_mm=NEED_MM_SHEATH)


def geometry(k):
    return paw(k).rec


def _jsonable(x):
    if isinstance(x, dict): return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray): return x.tolist()
    if isinstance(x, (np.floating, np.integer)): return x.item()
    return x


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "cache":
        ks = sys.argv[2:] or PAWS
        for k in ks:
            print(build_cache(k), flush=True)
    elif cmd == "report":
        out = dict(what="feat_paws_v3 derived construction per paw (every value derived from the measured inputs + spec_paws_v3.json)",
                   regions=REGIONS, resolution=RESOLUTION, paws={k: geometry(k) for k in PAWS})
        json.dump(_jsonable(out), open(os.path.join(LAYERS, "paws_v3b_geometry.json"), "w"), indent=1)
        print("wrote", os.path.join(LAYERS, "paws_v3b_geometry.json"))
