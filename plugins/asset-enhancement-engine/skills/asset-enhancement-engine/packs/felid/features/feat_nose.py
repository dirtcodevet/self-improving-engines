"""NOSE feature edit (Phase 2, Stage 3; spec_nose.json, fix list check_nose.json; builder feat-nose 2026-10-18).

edit(P_head_mm (N,3), F_mm (N,)) -> F_mm : a signed-distance EDIT of the skin field (head frame mm, x = cat's left,
y = back, z = up; F negative inside tissue). Vectorised; points outside REGION are returned unchanged.

Order (spec construction_sdf, with the check_nose fixes):
  0  DISH FILL   Tripo's blind dishes (2.15 / 2.31 mm) are filled by a plug bounded by the Phase 1 rim polygon
                 (nose_basins rim_head, exact-planar), its top = the rim plane + a 0.15 mm dome, dilated min(0.3,
                 dist-to-arc - 0.6) mm, smin k 0.6. (Spec step 0 asks for a thin-plate patch; a plane+dome plug is used
                 instead: it is analytic, so it does not depend on which skin it is applied to, and the rim is planar to
                 0.00 mm so the plane IS the rim's straight edge -> the 'no concavity under the rim' gate holds by construction.)
  1  ALA         outward DISPLACEMENT bump (h R 0.75 / L 0.5 mm, calibrated on the preview to a ~0.6 mm crown) with the spec ellipsoid's footprint (e1 3.2, e2 1.5 mm), profile
                 (1 - q^2)^2. A displacement, not an ellipsoid union, so the crown over the patched surface is h whatever
                 the final skin's offset (check_nose B4 asks the crown be measured against the patched surface).
  2  ALAR GROOVE inward displacement along open_end -> tail_tip, depth 0.4 mm, half-depth width 0.5 mm, fading to 0
                 over the last 1.0 mm at the tail tip.
  3  NOSTRIL     slit = round cone H (r_h) -> open_end (0.3 mm) laid on the plug top; vestibule = swept ellipse along a
                 Catmull-Rom centreline (spec rule, P-1 = H - 2.5 T0 so it opens through the surface), stations a/b, end
                 cap; alar-fold ridge (tube r 0.45, protrusion min(1.0, 0.6 x local radius) at s 1.5-3.5; spec r 0.6 / 0.7 ESTIMATE) subtracted from the lumen on the
                 LATERAL-DORSAL wall (direction built per side from lateral + dorsal, so mirror handedness cannot flip it -
                 check_nose should-fix 'e2 rule wrong for R'). carve = smax(F, -lumen, k 0.3).
  4  CREASE      CANCELLED (person-approved v1 top edge; check_nose B5).
  5  PHILTRUM    inward displacement, Gaussian section; BUILT targets = the spec's circular-arc sections (half-depth widths
                 0.60 / 0.96 / 1.33 mm, depths 0.20 / 0.45 / 0.80 at z -11.3 / -16.3 / -19.3); the CUT is target minus the base's own
                 midline relief (PH_BASE, measured on the preview crop) with cut widths 0.5 / 0.8 / 1.0, centre x -0.2 on the
                 leather (check_nose B3: midline waypoint at the tip height, not the off-midline outline point) -> -0.5 at
                 the Y junction; ends faded over 0.8 mm; front-only gate y < -63.
  5b MASK (R1)   F = lerp(d_ref, F_edit, w), w = smoothstep(0.6, 1.2, dist_to_band_core); d_ref = signed distance to the
                 person-approved skin v1 (reference crop). band_core = v1 vertices in the protected sector (z >= -9,
                 y <= -67) with depth_mm in [0.05, 1.0] + the protected arc, dilated 0.5 mm; MINUS the TAIL-ENTRY ZONES
                 (person 05:15: the nostril tails cut into the approved corners where the photo shows them reaching the
                 edge): balls of radius TAIL_ZONE_MM about each alar-groove tail segment. TAIL_ZONES describes them.
Every number's source is spec_nose.json (G2) unless marked ESTIMATE here.
"""
import json
import os

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
SPEC = json.load(open(os.path.join(HERE, "spec_nose.json")))
BASINS = json.load(open(os.path.join(ROOT, "tripo_rebuild", "layers", "nose_basins.json")))
REF_PATH = os.path.join(ROOT, "tripo_rebuild", "layers", "skin_v1_person_approved_leather_top.npz")
FIT_PATH = os.path.join(ROOT, "scratch_cat", "cat_fit14.json")

REGION = {"lo_mm": [-13.5, -77.5, -23.0], "hi_mm": [13.5, -55.0, -1.5]}   # head-frame mm box the edit touches

K_PLUG, K_LUMEN = 0.6, 0.3
DOME_MM = 0.15                 # ESTIMATE (IMAIOS 'bulging around the nostrils'; kept small), confidence low
ALA_H_MM = {"R": 0.75, "L": 0.5}  # per side: at 0.65 the preview crowns read R 0.53/0.49/0.39 (groove overlap), L 0.84/0.93/0.81
                                  # (smin blend lowers |grad F|); scaled so the crown lands ~0.6 (base-dependent: re-measure)
_ALA_OLD = 0.65                # inside the spec's 0.4-0.9 crown window, confidence low (size ESTIMATE in the spec)
GROOVE_D, GROOVE_HW = 0.4, 0.5  # spec depth 0.3-0.5, width 0.4-0.9 -> mid values
PH_Z = np.array([-11.3, -16.3, -19.3]); PH_D = np.array([0.20, 0.45, 0.80]); PH_HW = np.array([0.50, 0.80, 1.00])   # CUT widths; spec targets 0.60/0.96/1.33 are for the BUILT groove: the base's broad lip set-back adds ~0.3-0.4 (preview)   # onset 0.6 -> 0.5: the preview read 0.9 at 0.6 (base adds width)
PH_X = np.array([-0.2, -0.2, -0.5])
# the base skin's own midline straight-edge depth (+-1.5 mm chord) measured on the no-edit preview crop (skin v1 recipe):
# the cut is target - base so the BUILT groove meets the spec stations (superposition; re-measure on the final skin).
PH_BZ = np.array([-10.5, -11.0, -11.5, -12.0, -12.5, -13.0, -13.5, -14.0, -14.5, -15.0, -15.5, -16.0, -16.5, -17.0, -17.5, -18.0, -18.5, -19.0, -19.5, -20.0])
PH_BASE = np.array([0.105, 0.088, 0.07, 0.05, 0.041, 0.06, 0.117, 0.121, 0.116, 0.085, 0.002, 0.199, 0.376, 0.338, 0.383, 0.324, 0.264, 0.235, 0.232, 0.256])
RIDGE_R = 0.45                 # ridge tube radius (spec 0.6, ESTIMATE low): 0.6 bit only a 0.06 crescent defect on the preview
RIDGE_P = 1.0                  # alar-fold protrusion (spec 0.7, size ESTIMATE low): 0.7 left a 0.08 crescent defect on the 0.3 mm
                               # preview (rounding eats the bite); 1.0 keeps the clear width >= 1.2 mm
TAIL_ZONE_MM = 1.7             # groove half-width 0.5 + R1 ramp 1.2 mm: where the tail edit can reach


def ss(t):
    t = np.clip(t, 0.0, 1.0); return t * t * (3 - 2 * t)


def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k; return np.minimum(a, b) - h * h * k / 4


def smax(a, b, k):
    return -smin(-a, -b, k)


def unit(x):
    x = np.asarray(x, float); return x / np.linalg.norm(x, axis=-1, keepdims=True)


def seg_dist(P, a, b):
    ab = b - a; t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1); return np.linalg.norm(P - (a + t[:, None] * ab), axis=1), t


def catmull(pts, n=400):
    pts = np.asarray(pts, float); ext = np.vstack([2 * pts[0] - pts[1], pts, 2 * pts[-1] - pts[-2]]); out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1:i + 3]; t = np.linspace(0, 1, n, endpoint=False)[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1][None]); return np.vstack(out)


class Raster2D:
    """signed 2-D distance (negative inside) to a polygon, raster 0.04 mm, bilinear lookup"""
    def __init__(self, poly, pad=4.0, h=0.04):
        from matplotlib.path import Path
        from scipy import ndimage
        self.lo = poly.min(0) - pad; hi = poly.max(0) + pad; self.h = h
        n = np.ceil((hi - self.lo) / h).astype(int) + 1
        g = np.stack(np.meshgrid(*[self.lo[i] + np.arange(n[i]) * h for i in range(2)], indexing="ij"), -1).reshape(-1, 2)
        ins = Path(poly).contains_points(g).reshape(n)
        self.S = (ndimage.distance_transform_edt(~ins) - ndimage.distance_transform_edt(ins)) * h; self.n = n

    def __call__(self, Q):
        u = (Q - self.lo) / self.h; i = np.clip(np.floor(u).astype(int), 0, self.n - 2); fr = np.clip(u - i, 0, 1)
        S = self.S; a = S[i[:, 0], i[:, 1]] * (1 - fr[:, 0]) + S[i[:, 0] + 1, i[:, 1]] * fr[:, 0]
        b = S[i[:, 0], i[:, 1] + 1] * (1 - fr[:, 0]) + S[i[:, 0] + 1, i[:, 1] + 1] * fr[:, 0]
        out = a * (1 - fr[:, 1]) + b * fr[:, 1]
        far = np.any((u < 0) | (u > self.n - 1), axis=1)
        return np.where(far, 4.0, out)


ARC = np.array(SPEC["approved_top_edge_FROZEN"]["protected_arc"]["points_head_mm_resampled_40_angle_bins"], float)


class Side:
    def __init__(self, sd):
        P = SPEC["parts"][f"nostril_{sd}"]; self.sd = sd
        fr = P["frame"]; self.n_in = unit(fr["n_in"]); self.n_out = -self.n_in
        self.e1 = unit(fr["e1_tail"]); e2 = np.asarray(fr["e2_dorsal"], float)
        e2 = e2 - (e2 @ self.e1) * self.e1 - (e2 @ self.n_out) * self.n_out; self.e2 = unit(e2)
        sl = P["open_slit"]; self.H = np.array(sl["head_disc_centre_H"], float); self.rh = float(sl["head_disc_radius_mm"])
        self.open_end = np.array(sl["open_end"], float)
        self.tail_tip = np.array(P["outer_extent_comma"]["tail_tip"], float)
        # ---- rim plane + polygon (Phase 1, exact rim at overflow)
        rim = np.array(BASINS[sd]["rim_head"], float); self.rim = rim; c = rim.mean(0)
        _, _, Vt = np.linalg.svd(rim - c); nrm = Vt[2] if Vt[2] @ self.n_out > 0 else -Vt[2]
        self.c, self.nrm, self.u1, self.u2 = c, nrm, Vt[0], np.cross(nrm, Vt[0])
        self.poly = Raster2D(np.c_[(rim - c) @ self.u1, (rim - c) @ self.u2])
        dmin = float(np.min(np.linalg.norm(rim[:, None] - ARC[None], axis=2)))
        self.rim_to_arc = dmin; self.dil = min(0.3, dmin - 0.6)                                   # R4
        # ---- vestibule centreline (spec rule)
        m = np.array([0.5, 1, 1]); T0 = unit(self.n_in * m); self.T0 = T0
        P1 = self.H + 2.0 * T0; P2 = P1 + 3.0 * unit([0, 1, 0.15]); P3 = P2 + 7.0 * unit([0, 1, 0.10])
        Pm = self.H - 2.5 * T0
        cl = catmull([Pm, self.H, P1, P2, P3], 300)
        seg = np.linalg.norm(np.diff(cl, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
        s0 = np.interp(0, [0, 1], [0, 0]); iH = np.argmin(np.linalg.norm(cl - self.H, axis=1)); s = s - s[iH]
        L = s[-1]; ss_ = np.arange(s[0], L + 1e-9, 0.04)
        self.cl = np.c_[[np.interp(ss_, s, cl[:, k]) for k in range(3)]].T; self.s = ss_; self.L = L
        Tn = np.gradient(self.cl, axis=0); self.T = unit(Tn)
        A = self.e1 - (self.T @ self.e1)[:, None] * self.T; self.A = unit(A); self.B = np.cross(self.T, self.A)
        lum = P["vestibule"]["lumen_section"]
        self.a = np.interp(np.clip(ss_, 0, None), lum["stations_s_mm"], lum["a_mm"])
        self.b = np.interp(np.clip(ss_, 0, None), lum["stations_s_mm"], lum["b_mm"])
        self.tree = cKDTree(self.cl)
        # ---- alar-fold ridge (lateral-dorsal wall)
        lat = np.array([-1.0 if sd == "R" else 1.0, 0, 0]); up = np.array([0, 0, 1.0])
        sr = (ss_ >= 0.5) & (ss_ <= 6.0); cen = []
        for i in np.nonzero(sr)[0]:
            T = self.T[i]; u = unit(lat * np.cos(np.radians(45)) + up * np.sin(np.radians(45))); u = unit(u - (u @ T) * T)
            ca, cb = u @ self.A[i], u @ self.B[i]
            rho = 1.0 / np.sqrt((ca / self.a[i]) ** 2 + (cb / self.b[i]) ** 2)              # ellipse radius along u
            p = min(RIDGE_P, 0.6 * rho) * ss((ss_[i] - 0.5) / 1.0) * (1 - ss((ss_[i] - 3.5) / 2.5))   # leaves >= 0.45 rho open
            cen.append(self.cl[i] + u * (rho + RIDGE_R - p))
        self.ridge = np.array(cen); self.ridge_tree = cKDTree(self.ridge)
        self.ridge_dir_at = lambda i: None
        # ---- slit on the plug top
        self.Hs = self.on_plug(self.H); self.Os = self.on_plug(self.open_end)
        # ---- ala
        al = P["ala_outer"]; self.ala_c = np.array(al["ellipsoid_centre"], float); self.ala_r = np.array(al["radii_mm_e1_e2_n"], float)

    def plug_top_offset(self, Q):
        q = Q - self.c; uv = np.c_[q @ self.u1, q @ self.u2]; d2 = self.poly(uv)
        dome = DOME_MM * ss(-d2 / 1.5); return q @ self.nrm, d2, dome

    def on_plug(self, X):
        h, d2, dome = self.plug_top_offset(X[None]); return X - (h[0] - dome[0]) * self.nrm

    def plug(self, Q):
        h, d2, dome = self.plug_top_offset(Q)
        top = h - dome + 0.3 * np.maximum(d2, 0)            # slope away outside the rim
        return np.maximum.reduce([top, d2 - self.dil, -h - 4.0])

    def lumen(self, Q):
        _, i = self.tree.query(Q); C = self.cl[i]; D = Q - C
        ax = np.einsum("ij,ij->i", D, self.T[i]); qa = np.einsum("ij,ij->i", D, self.A[i]); qb = np.einsum("ij,ij->i", D, self.B[i])
        a, b = self.a[i], self.b[i]
        over = np.where(i == len(self.cl) - 1, np.maximum(ax, 0), 0.0)
        return (np.sqrt((qa / a) ** 2 + (qb / b) ** 2 + (over / a) ** 2) - 1) * np.minimum(a, b)

    def ridge_sdf(self, Q):
        d, _ = self.ridge_tree.query(Q); return d - RIDGE_R

    def slit(self, Q):
        d, t = seg_dist(Q, self.Hs, self.Os); return d - (self.rh + (0.3 - self.rh) * t)

    def ala(self, Q):
        q = Q - self.ala_c; qq = (q @ self.e1 / self.ala_r[0]) ** 2 + (q @ self.e2 / self.ala_r[1]) ** 2
        nz = np.abs(q @ self.n_out) < 4.0
        return np.where(nz, ALA_H_MM[self.sd] * np.clip(1 - qq, 0, 1) ** 2, 0.0)

    def groove(self, Q):
        d, t = seg_dist(Q, self.open_end, self.tail_tip); L = np.linalg.norm(self.tail_tip - self.open_end)
        depth = GROOVE_D * ss((1 - t) * L / 1.0)
        return depth * 2.0 ** (-(2 * d / GROOVE_HW) ** 2)


SIDES = {sd: Side(sd) for sd in ("R", "L")}

# ---------------------------------------------------------------- R1 mask: reference (skin v1) crop + band core
_REF = {}


def _load_ref():
    if _REF:
        return _REF
    hd = json.load(open(FIT_PATH))["head"]; C = np.array(hd["C"]); R = np.array(hd["R"])
    Z = np.load(REF_PATH); v = (Z["v"] - C) @ R * 1000.0; f = Z["f"]; dep = Z["depth_mm"]
    box = (np.abs(v[:, 0]) < 16) & (v[:, 1] > -80) & (v[:, 1] < -55) & (v[:, 2] > -26) & (v[:, 2] < 2)
    keep = box[f].all(1); f = f[keep]; idx = np.unique(f); remap = -np.ones(len(v), int); remap[idx] = np.arange(len(idx))
    v, dep, f = v[idx], dep[idx], remap[f]
    fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-12)[:, None]
    if "n" in Z.files:
        vn = Z["n"][idx] @ R
        if np.mean(np.einsum("ij,ij->i", fn, vn[f].mean(1))) < 0:
            fn = -fn
    sector = (v[:, 2] >= -9.0) & (v[:, 1] <= -67.0)
    core_v = v[sector & (dep >= 0.05) & (dep <= 1.0)]
    core = np.vstack([core_v, ARC])
    tails = [(SIDES[s].open_end, SIDES[s].tail_tip) for s in ("R", "L")]
    excl = np.zeros(len(core), bool)
    for a, b in tails:
        excl |= seg_dist(core, a, b)[0] < TAIL_ZONE_MM
    _REF.update(v=v, f=f, dep=dep, fn=fn, tri_tree=cKDTree(v[f].mean(1)), core=core[~excl], core_tree=cKDTree(core[~excl]),
                excluded_core=core[excl], tails=tails)
    return _REF


def tail_zones():
    """extent of the photo-shown tail-entry zones on the protected arc (dense arc not needed: the 40-bin arc + core)"""
    R = _load_ref(); out = {}
    for sd, (a, b) in zip(("R", "L"), R["tails"]):
        da = seg_dist(ARC, a, b)[0]; inz = da < TAIL_ZONE_MM
        out[sd] = {"arc_points_in_zone": int(inz.sum()), "min_dist_arc_to_tail_mm": round(float(da.min()), 3),
                   "zone_radius_mm": TAIL_ZONE_MM, "tail_segment_head_mm": [np.round(a, 2).tolist(), np.round(b, 2).tolist()]}
    out["core_points_excluded"] = int(len(R["excluded_core"]))
    return out


def d_ref(Q):
    import sys
    sys.path.insert(0, os.path.join(ROOT, "tripo_rebuild")); import exact_sdf  # noqa: E402  (proven closest-point tool)
    R = _load_ref(); v, f, fn = R["v"], R["f"], R["fn"]; _, nn = R["tri_tree"].query(Q, k=8)
    best = np.full(len(Q), np.inf); sgn = np.ones(len(Q))
    for k in range(nn.shape[1]):
        t = nn[:, k]; c = exact_sdf.closest_on_tri(Q, v[f[t, 0]], v[f[t, 1]], v[f[t, 2]]); d = np.linalg.norm(Q - c, axis=1)
        better = d < best; best = np.where(better, d, best)
        s = np.sign(np.einsum("ij,ij->i", Q - c, fn[t])); sgn = np.where(better, np.where(s == 0, 1, s), sgn)
    return sgn * best


def mask_w(Q):
    R = _load_ref(); d, _ = R["core_tree"].query(Q); return ss((d - 0.5 - 0.6) / 0.6)


# ---------------------------------------------------------------- the edit
def edit(P_head_mm, F_mm, graft=True, parts=("plug", "ala", "groove", "nostril", "philtrum")):
    P = np.asarray(P_head_mm, float); F = np.array(F_mm, float, copy=True)
    lo, hi = np.array(REGION["lo_mm"]), np.array(REGION["hi_mm"])
    ins = np.all((P >= lo) & (P <= hi), axis=1); idx = np.nonzero(ins)[0]
    for a0 in range(0, len(idx), 400_000):
        ii = idx[a0:a0 + 400_000]; Q = P[ii]; f = F[ii]
        near = np.abs(f) < 25.0                              # everything in the box (the vestibule runs ~12 mm deep)
        Qn, g = Q[near], f[near]
        for S in SIDES.values():
            if "plug" in parts:
                g = smin(g, S.plug(Qn), K_PLUG)
            if "ala" in parts:
                g = g - S.ala(Qn)
            if "groove" in parts:
                g = g + S.groove(Qn)
        if "nostril" in parts:
            for S in SIDES.values():
                lum = smax(S.lumen(Qn), -S.ridge_sdf(Qn), 0.08)
                lum = smin(lum, S.slit(Qn), 0.3)
                g = smax(g, -lum, K_LUMEN)
        if "philtrum" in parts:
            z = Qn[:, 2]; zc = np.clip(z, PH_Z[2], PH_Z[0])
            dep = np.maximum(np.interp(-zc, -PH_Z, PH_D) - np.interp(-zc, -PH_BZ, PH_BASE), 0.05); hw = np.interp(-zc, -PH_Z, PH_HW); xc = np.interp(-zc, -PH_Z, PH_X)
            fade = ss((PH_Z[0] + 0.8 - z) / 0.8) * ss((z - (PH_Z[2] - 0.8)) / 0.8)
            gate = ss((-63.0 - Qn[:, 1]) / 2.0)
            g = g + dep * fade * gate * 2.0 ** (-(2 * (Qn[:, 0] - xc) / hw) ** 2)
        if graft:
            w = mask_w(Qn); m = w < 1
            if m.any():
                g[m] = w[m] * g[m] + (1 - w[m]) * d_ref(Qn[m])
        f[near] = g; F[ii] = f
    return F


def depth_edit(P_head_mm, depth_mm):
    """R3: coat depth in the protected band copied from the person-approved v1 (same lerp weight as the field graft)"""
    P = np.asarray(P_head_mm, float); d = np.array(depth_mm, float, copy=True)
    lo, hi = np.array(REGION["lo_mm"]), np.array(REGION["hi_mm"]); ii = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
    if not len(ii):
        return d
    w = mask_w(P[ii]); m = w < 1
    if m.any():
        import sys
        sys.path.insert(0, os.path.join(ROOT, "tripo_rebuild")); import exact_sdf  # noqa: E402
        R = _load_ref(); v, f = R["v"], R["f"]; Q = P[ii[m]]; _, nn = R["tri_tree"].query(Q, k=8); best = np.full(len(Q), np.inf)
        dv = np.zeros(len(Q))
        for k in range(nn.shape[1]):
            t = nn[:, k]; A, B, C = v[f[t, 0]], v[f[t, 1]], v[f[t, 2]]; c = exact_sdf.closest_on_tri(Q, A, B, C)
            dd = np.linalg.norm(Q - c, axis=1); e1, e2, q = B - A, C - A, c - A
            d00, d01, d11 = (e1 * e1).sum(1), (e1 * e2).sum(1), (e2 * e2).sum(1); d20, d21 = (q * e1).sum(1), (q * e2).sum(1)
            den = np.maximum(d00 * d11 - d01 * d01, 1e-18); bb = (d11 * d20 - d01 * d21) / den; cg = (d00 * d21 - d01 * d20) / den
            val = R["dep"][f[t, 0]] * (1 - bb - cg) + R["dep"][f[t, 1]] * bb + R["dep"][f[t, 2]] * cg
            better = dd < best; best = np.where(better, dd, best); dv = np.where(better, val, dv)
        d[ii[m]] = w[m] * d[ii[m]] + (1 - w[m]) * dv
    return d


def probe_inputs():
    """what the inventory probes need to find each part (the builder knows them)"""
    out = {}
    for sd, S in SIDES.items():
        out[f"nostril_cavity.{sd}"] = {"opening_centre_mm": S.H.tolist(), "axis_into_head": S.T0.tolist()}
        out[f"alar_fold.{sd}"] = {
            "centreline_mm": S.cl[S.s >= 0][::5].tolist(), "centreline_s_mm": S.s[S.s >= 0][::5].tolist(),
            "H_mm": S.H.tolist(), "T0": S.T0.tolist(), "lateral_dorsal": unit(np.array([-1.0 if sd == "R" else 1.0, 0, 1])).tolist(),
            "ala_centre_mm": S.ala_c.tolist(), "n_out": S.n_out.tolist(), "e1": S.e1.tolist(), "e2": S.e2.tolist(),
            "rim_mm": S.rim.tolist(), "groove_mm": [S.open_end.tolist(), S.tail_tip.tolist()]}
    out["philtrum"] = {"z_mm": PH_Z.tolist(), "depth_mm": PH_D.tolist(), "half_depth_width_mm": PH_HW.tolist(), "x_mm": PH_X.tolist()}
    out["nose_leather"] = {"widths": {"-10": 14.56, "-12": 9.16, "-14": 5.84}, "tol_mm": 0.5}
    out["leather_bridge_crease"] = {"ref_npz": REF_PATH, "fit_json": FIT_PATH,
                                    "tail_segments_mm": [[S.open_end.tolist(), S.tail_tip.tolist()] for S in SIDES.values()],
                                    "tail_zone_mm": TAIL_ZONE_MM, "nostril_rims_mm": [S.rim.tolist() for S in SIDES.values()],
                                    "vestibule_centrelines_mm": [S.cl[S.s >= 0][::5].tolist() for S in SIDES.values()]}
    return out


def ala_patched_inputs(base_F):
    """alar_fold probe inputs that depend on the BASE skin: the dish-filled, no-ala surface point + normal under each ala
    station (-0.8 / 0 / +0.8 mm along e1). base_F(P_head_mm) -> F_mm of the skin the edit is applied to."""
    out = {}
    for sd, S in SIDES.items():
        pts, nrs = [], []
        for o in (-0.8, 0.0, 0.8):
            t = np.linspace(-4, 4, 801); P = S.ala_c + o * S.e1 + t[:, None] * S.n_out
            F = edit(P, base_F(P), graft=False, parts=("plug",)); k = np.nonzero((F[:-1] < 0) & (F[1:] >= 0))[0][-1]
            X = S.ala_c + o * S.e1 + (t[k] - F[k] * (t[1] - t[0]) / (F[k + 1] - F[k])) * S.n_out; h = 0.15
            G = np.array([edit((X + h * e)[None], base_F((X + h * e)[None]), graft=False, parts=("plug",))[0]
                          - edit((X - h * e)[None], base_F((X - h * e)[None]), graft=False, parts=("plug",))[0] for e in np.eye(3)])
            pts.append(X.tolist()); nrs.append((G / np.linalg.norm(G)).tolist())
        out[f"alar_fold.{sd}"] = {"ala_patched_pts_mm": pts, "ala_patched_normals": nrs}
    return out
