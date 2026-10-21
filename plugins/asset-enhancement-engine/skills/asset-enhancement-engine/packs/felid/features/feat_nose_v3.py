"""NOSE v3 feature (felid pack, case cat1, cat v3) - builder 'feat-nose-v3', 2026-10-18. feat_nose.py (v2) is IMPORTED and
left unchanged; every v2 value not overridden here stands (spec_nose.json, check_nose.json, V3_BRIEF NOSE).

WHAT CHANGES (V3_BRIEF 'NOSE: interesting detail')
  * RESOLUTION CONTRACT (A20), DECLARED: REGION (v2's box, which holds both corner legs), NEED_MM 0.15 in REGION,
    NEED_MM_SLIT 0.10 in the comma band (slit_band(P)), and opening_sdf(P) = the intended air fill_voids must never
    seal (each vestibule lumen with its alar-fold ridge + the v3 comma slit).
  * COMMA OPENING INTO THE PASSAGE (v2: a straight 1.5 -> 0.3 mm round cone laid 0-1.5 mm under the plug top = a round
    hole at H plus a 0.3-0.5 mm-deep BLIND notch toward the tail; check_nose should-fix 'the slit tail is a dish in
    miniature'). v3: the comma centre line is a quadratic Bezier H -> open_end bowed DORSALLY by COMMA_BOW (the tail
    curls up and out round the ala, IMAIOS: 'lateral narrow end raised into a comma'); its half-width falls from the
    head disc r_h to R_TAIL as (1 - t)^2 (round head, thin tail); every station is a WEDGE capsule from 0.3 mm above
    the plug top down to the vestibule centreline at s = WEDGE_S, so every part of the opening leads into the lumen.
  * TAILS CUT INTO THE APPROVED CORNERS (the person, 05:15: "Let the nostril tails cut into the approved corners where
    the photo shows them reaching the edge"). The alar groove runs on from tail_tip to the approved CORNER (the end of
    the protected arc nearest the tail tip = cat_decisions.tail_paths) at CORNER_D deep, fading over the last
    CORNER_FADE mm; the R1 graft core now excludes balls of TAIL_ZONE_MM about the WHOLE path (v2 excluded only
    open_end -> tail_tip, so the graft wrote v1 back over the corner leg: D2 0.00 / 0.04 mm on v2).
  * LEATHER WITHOUT WRINKLE ARTEFACTS. Two causes found in v2 (checked on the code): (1) the philtrum cut depth used a
    raw 20-sample base-relief table PH_BASE (0.002 -> 0.199 mm between z -15.5 and -16.0) so the cut jumped 0.2 mm in
    0.5 mm of z: a transverse ridge across the leather stem; v3 uses a least-squares quadratic of the same table
    (PH_BASE_FIT, residual reported by philtrum_base_fit()); (2) the graft reference d_ref is the signed distance to
    v1's 0.5 mm marching-cubes facets: evaluated finely it reproduces the facet creases. v3 grafts to the BASE field
    the edit is applied to (graft_ref='base', R2: valid only while the base's top edge passes D1; skin v2 pre-edit:
    max 0.098 mm, cat_decisions_v3_on_skin_v2_preintegration.json), 'v1' keeps v2's behaviour. The leather's
    cobblestone texture is SHADER detail (spec nose_leather.surface; Strickland 1958 via cat-anatomy.md; cell size in
    cats not published): leather_bump(P) gives a procedural cell field for the shader, never the skin field.
  * APPROVED TOP EDGE KEPT: v2's band core + R1 graft, plus the full-path tail exclusion above. FINDING (checked): the
    decision check D1 zone (skin_build.leather_top_zone: 3 mm inside .. 5 mm outside the outline's upper half) covers
    the nostrils: on the v2 cat 154 of the 155 points over 0.2 mm lie INSIDE the nostril rim polygons (the intended dish
    fill), none within 2.47 mm of the protected arc; within 2 mm of the arc v2 moved at most 0.047 mm. EDIT_ZONE
    (edit_zone(P)) declares the nostril openings so D1 and skin_build_v3's leather restore can exclude them.

API (compatible with skin_build_v3 / cat_decisions, which read feat_nose names):
  REGION ; NEED_MM ; NEED_MM_SLIT ; RESOLUTION ; slit_band(P) ; opening_sdf(P) ; edit_zone(P) ; leather_bump(P)
  edit(P_head_mm, F_mm, graft=True, graft_ref='base', base_fn=None) ; leather_w(P) ; smooth_delta(P, base_fn) ; SIDES[sd].lumen/ridge_sdf/slit ; TAIL_ZONE_MM ; ARC ; tail_paths()
usage: the preview + probes are tripo_rebuild/nose_v3_preview.py (preview | probe).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feat_nose as V2  # noqa: E402  (Phase 2, unchanged)

ROOT = V2.ROOT
SPEC = V2.SPEC
REGION = V2.REGION
ARC = V2.ARC
TAIL_ZONE_MM = V2.TAIL_ZONE_MM
ss, smin, smax, unit, seg_dist = V2.ss, V2.smin, V2.smax, V2.unit, V2.seg_dist
K_PLUG, K_LUMEN = V2.K_PLUG, V2.K_LUMEN

# ------------------------------------------------------------------ the resolution contract (A20), declared
GRID_CAP_MM = 0.15
NEED_MM = 0.15          # the A20 cap everywhere in REGION
NEED_MM_SLIT = 0.10     # comma tail full width 2 R_TAIL = 0.40 mm -> 4 voxels; the taper stays smooth (no 0.5 mm steps)
RESOLUTION = {"region_mm": NEED_MM, "slit_band_mm": NEED_MM_SLIT, "cap_mm": GRID_CAP_MM,
              "slit_band": "within 0.6 mm of the comma wedge (slit_band(P))",
              "source": "NOTES_v3 A20; tail width 0.40 mm needs <= 0.16 mm for 2.5 voxels; 0.10 keeps the taper smooth"}

V3_PARAMS = {
    "R_HEAD": (float(SPEC["parts"]["nostril_R"]["open_slit"]["head_disc_radius_mm"]), "spec open_slit head_disc_radius (photo core + Phase 1 widths)", "spec"),
    "R_TAIL": (0.20, "comma tail half-width at open_end; v2 0.3 read as a round hole at 0.5 mm; 0.2 keeps 4 voxels at 0.10", "estimate"),
    "COMMA_BOW": (0.45, "dorsal bow of the comma centre line (photo: the dark tail curls dorsolaterally to px (684,367) R; "
                        "IMAIOS 'lateral narrow end raised into a comma'); kept small so the tail stays inside the rim", "estimate"),
    "WEDGE_S": (1.5, "vestibule centreline station the wedge runs to (lumen a 1.4 / b 1.0 there, spec lumen_section)", "derived"),
    "N_STATIONS": (64, "comma stations (spacing <= 0.07 mm on the 4.4 mm R chord)", "derived"),
    "D_SLOT": (1.2, "depth of the comma slot under every station along n_in before it turns to the lumen (first probe run: a "
                    "single oblique wedge read < 0.6 mm deep at the tail = a groove, not an opening)", "derived/estimate"),
    "K_SLIT": (0.10, "carve blend of the comma slot (v2's K_LUMEN 0.3 rounds a 0.4 mm slot shut at its mouth)", "derived"),
    "SMOOTH_STEP": (0.45, "leather smoothing stencil offset (3-tap binomial per axis, sigma 0.32 mm): passes 5 mm form at 92 %, "
                          "removes 0.8-0.9 mm ripple (>= 96 %)", "derived"),
    "SMOOTH_IN": (0.6, "smoothing weight ramps 0 -> 1 from the leather outline to 0.6 mm inside it (the approved leather->fur step untouched)", "estimate"),
    "CORNER_D": (0.40, "corner-leg groove depth: spec alar_groove depth 0.3-0.5 (mid 0.4) eased toward the arc; D2 gate 0.15-0.7", "spec/derived"),
    "CORNER_FADE": (0.4, "the corner-leg depth fades to CORNER_END over the last 0.4 mm before the corner (no gouge at the arc)", "estimate"),
    "CORNER_END": (0.25, "depth left AT the corner (the tail visibly enters the corner; D2 asks >= 0.10 at 0.5 mm before)", "estimate"),
    "PH_FIT_DEG": (2, "least-squares polynomial degree for the philtrum base relief (wrinkle fix)", "derived"),
}
Q_ = {k: v[0] for k, v in V3_PARAMS.items()}

# philtrum base relief: smooth fit of v2's raw table (the raw table made the cut jump 0.2 mm in 0.5 mm of z)
_PHC = np.polyfit(V2.PH_BZ, V2.PH_BASE, Q_["PH_FIT_DEG"])
PH_BASE_FIT = np.polyval(_PHC, V2.PH_BZ)


def philtrum_base_fit():
    r = V2.PH_BASE - PH_BASE_FIT
    dz = np.diff(V2.PH_BZ)
    return {"coef": _PHC.tolist(), "residual_rms_mm": float(np.sqrt(np.mean(r ** 2))), "residual_max_mm": float(np.abs(r).max()),
            "raw_max_step_per_mm": float(np.abs(np.diff(V2.PH_BASE) / dz).max()),
            "fit_max_step_per_mm": float(np.abs(np.diff(PH_BASE_FIT) / dz).max()), "label": "checked (arithmetic on the table)"}


def smin_k(a, b, k):
    k = np.maximum(k, 1e-3); h = np.maximum(k - np.abs(a - b), 0.0) / k; return np.minimum(a, b) - h * h * k / 4


def tail_paths():
    """per side: open_end -> tail_tip -> approved corner (the protected-arc end nearest the tail tip), head mm
    (identical rule to cat_decisions.tail_paths, kept here so the feature owns its path)"""
    out = {}
    for sd, S in V2.SIDES.items():
        ends = np.array([ARC[0], ARC[-1]]); c = ends[np.argmin(np.linalg.norm(ends - S.tail_tip, axis=1))]
        out[sd] = np.array([S.open_end, S.tail_tip, c], float)
    return out


def dist_to_path(Q, path):
    d = np.full(len(Q), np.inf)
    for a, b in zip(path[:-1], path[1:]):
        d = np.minimum(d, seg_dist(Q, a, b)[0])
    return d


class SideV3:
    """v2 Side (plug, ala, groove, lumen, ridge unchanged) + the v3 comma wedge and the corner leg"""
    def __init__(self, sd):
        S = V2.SIDES[sd]; self.v2 = S; self.sd = sd
        for k in ("H", "open_end", "tail_tip", "rim", "c", "nrm", "n_in", "n_out", "e1", "e2", "T0", "cl", "s", "ala_c"):
            setattr(self, k, getattr(S, k))
        self.path = tail_paths()[sd]; self.corner = self.path[2]
        # comma centre line on the plug top: quadratic Bezier H -> open_end bowed along the in-surface dorsal direction
        Hs, Os = S.Hs, S.Os; ch = Os - Hs; nrm = S.nrm
        dors = S.e2 - (S.e2 @ nrm) * nrm; dors = dors - (dors @ unit(ch)) * unit(ch); dors = unit(dors)
        Cc = 0.5 * (Hs + Os) + 2.0 * Q_["COMMA_BOW"] * dors          # Bezier control: the curve's mid-bow = COMMA_BOW
        t = np.linspace(0, 1, int(Q_["N_STATIONS"]))[:, None]
        B = (1 - t) ** 2 * Hs + 2 * t * (1 - t) * Cc + t ** 2 * Os
        self.comma = np.array([S.on_plug(b) for b in B]); self.t = t[:, 0]
        self.r = Q_["R_TAIL"] + (S.rh - Q_["R_TAIL"]) * (1 - self.t) ** 2
        self.top = self.comma + 0.3 * S.n_out                         # wedge starts 0.3 mm above the plug top
        k = int(np.argmin(np.abs(S.s - Q_["WEDGE_S"]))); self.K = S.cl[k]
        self.Bt = self.comma + Q_["D_SLOT"] * S.n_in                  # the slot floor under each station
        self.dors = dors

    # v2 parts, unchanged
    def lumen(self, Q):
        return self.v2.lumen(Q)

    def ridge_sdf(self, Q):
        return self.v2.ridge_sdf(Q)

    def plug(self, Q):
        return self.v2.plug(Q)

    def ala(self, Q):
        return self.v2.ala(Q)

    def slit(self, Q):
        """v3 comma slot (mm, < 0 inside): union over stations of capsules top(t) -> B(t) = comma(t) + D_SLOT n_in -> K, radius r(t)"""
        Q = np.atleast_2d(Q); out = np.full(len(Q), np.inf)
        pad = 2.0 + float(self.r.max()) + 0.1
        bb_lo = np.minimum(np.minimum(self.top.min(0), self.Bt.min(0)), self.K) - pad
        bb_hi = np.maximum(np.maximum(self.top.max(0), self.Bt.max(0)), self.K) + pad
        m = np.all((Q >= bb_lo) & (Q <= bb_hi), axis=1)
        if not m.any():
            return out
        Qm = Q[m]; best = np.full(len(Qm), np.inf)
        for a, b, r in zip(self.top, self.Bt, self.r):
            d, _ = seg_dist(Qm, a, b); best = np.minimum(best, d - r)          # slot under the station
            d, _ = seg_dist(Qm, b, self.K); best = np.minimum(best, d - r)     # its floor runs on into the lumen
        out[m] = best
        # far points (> pad from every capsule end: true value >= 2.1 mm): clamp to 2.0
        out[~m] = 2.0
        return out

    def project_leg(self, base_fn, n=80):
        """the corner leg ON the base surface (Newton steps onto F = 0) and the base |grad F| there. Probe run 2 found
        (checked): the base field is not a unit SDF on R (|grad F| 1.9-2.15 at the corner leg, L 1.0-1.1) and the chord
        tail_tip -> corner leaves the curved surface, so a 0.45 mm field offset moved the R surface only 0.05-0.10 mm"""
        from scipy.spatial import cKDTree
        X = self.tail_tip + np.linspace(0, 1, n)[:, None] * (self.corner - self.tail_tip); h = 0.05
        for _ in range(5):
            F = base_fn(X); G = np.stack([(base_fn(X + h * e) - base_fn(X - h * e)) / (2 * h) for e in np.eye(3)], 1)
            X = X - (F / np.maximum((G ** 2).sum(1), 1e-9))[:, None] * G
        self.leg = X; self.leg_gn = np.linalg.norm(G, axis=1); self.leg_s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(X, axis=0), axis=1))]
        self.leg_tree = cKDTree(X); self._leg_base = id(base_fn)

    def groove(self, Q):
        """v2 groove (open_end -> tail_tip) + the v3 corner leg (tail_tip -> corner)"""
        g = self.v2.groove(Q)
        if getattr(self, "leg_tree", None) is not None:            # corner leg on the base surface, offset scaled by |grad F|
            dd, k = self.leg_tree.query(Q); L = self.leg_s[-1]; s_to_end = L - self.leg_s[k]
            depth = Q_["CORNER_END"] + (Q_["CORNER_D"] - Q_["CORNER_END"]) * ss(s_to_end / Q_["CORNER_FADE"])
            corner = depth * self.leg_gn[k] * 2.0 ** (-(2 * dd / V2.GROOVE_HW) ** 2) * ss((s_to_end + 0.25) / 0.25)
            dv, tv = seg_dist(Q, self.open_end, self.tail_tip); Lv = np.linalg.norm(self.tail_tip - self.open_end)
            bridge = Q_["CORNER_D"] * self.leg_gn[0] * (1 - ss((1 - tv) * Lv / 1.0)) * 2.0 ** (-(2 * dv / V2.GROOVE_HW) ** 2)
            return np.maximum.reduce([g, corner, bridge])
        a, b = self.tail_tip, self.corner; d, t = seg_dist(Q, a, b); L = np.linalg.norm(b - a)
        s_to_end = (1 - t) * L
        depth = Q_["CORNER_END"] + (Q_["CORNER_D"] - Q_["CORNER_END"]) * ss(s_to_end / Q_["CORNER_FADE"])
        # at the tail tip the v2 groove has faded to 0: carry the corner depth back over its last 1 mm so the cut is continuous
        dv, tv = seg_dist(Q, self.open_end, self.tail_tip); Lv = np.linalg.norm(self.tail_tip - self.open_end)
        bridge = Q_["CORNER_D"] * (1 - ss((1 - tv) * Lv / 1.0)) * 2.0 ** (-(2 * dv / V2.GROOVE_HW) ** 2)
        corner = depth * 2.0 ** (-(2 * d / V2.GROOVE_HW) ** 2)
        return np.maximum.reduce([g, corner, bridge])


SIDES = {sd: SideV3(sd) for sd in ("R", "L")}

# ------------------------------------------------------------------ R1 graft core v3 (full-path tail exclusion)
_REF3 = {}


def _ref3():
    if _REF3:
        return _REF3
    from scipy.spatial import cKDTree
    R = V2._load_ref(); core = np.vstack([R["core"], R["excluded_core"]]); excl = np.zeros(len(core), bool)
    for p in tail_paths().values():
        excl |= dist_to_path(core, p) < TAIL_ZONE_MM
    _REF3.update(core=core[~excl], tree=cKDTree(core[~excl]), excluded=int(excl.sum()), v2_excluded=int(len(R["excluded_core"])))
    return _REF3


def mask_w(Q):
    d, _ = _ref3()["tree"].query(Q); return ss((d - 0.5 - 0.6) / 0.6)


# ------------------------------------------------------------------ declared zones
def opening_sdf(P):
    """intended air (mm, < 0 inside): per side min(smax(lumen, -ridge, 0.08), comma slot) (v3 carves them separately)"""
    P = np.asarray(P, float); out = np.full(len(P), np.inf)
    lo, hi = np.array(REGION["lo_mm"]), np.array(REGION["hi_mm"]); b = np.all((P >= lo) & (P <= hi), axis=1)
    if b.any():
        Q = P[b]; o = np.full(len(Q), np.inf)
        for S in SIDES.values():
            o = np.minimum.reduce([o, smax(S.lumen(Q), -S.ridge_sdf(Q), 0.08), S.slit(Q)])
        out[b] = o
    return out


def slit_band(P):
    P = np.asarray(P, float); m = np.zeros(len(P), bool)
    for S in SIDES.values():
        m |= S.slit(P) < 0.6
    return m


def edit_zone(P, dil=1.0):
    """True where the nose edit is MEANT to change v1 inside D1's zone: each nostril rim polygon (rim-plane projection)
    dilated `dil` mm and within 4 mm of the rim plane (dish fill + comma), and the tail paths' TAIL_ZONE_MM balls"""
    P = np.asarray(P, float); m = np.zeros(len(P), bool)
    for sd, S in SIDES.items():
        q = P - S.c; uv = np.c_[q @ S.v2.u1, q @ S.v2.u2]; d2 = S.v2.poly(uv); h = q @ S.nrm
        m |= (d2 < dil) & (np.abs(h) < 4.0)
        m |= dist_to_path(P, S.path) < TAIL_ZONE_MM
    return m


def leather_bump(P, cell_mm=0.45, seed=11):
    """SHADER detail, never the skin field: a procedural cobblestone (F2 - F1 Worley distance, mm) for the leather's
    bump/normal map. cell_mm is an ESTIMATE (cat cell size not published, cat-anatomy.md); the shader scales it."""
    P = np.asarray(P, float) / cell_mm; I = np.floor(P).astype(np.int64); best1 = np.full(len(P), np.inf); best2 = best1.copy()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                C = I + np.array([dx, dy, dz]); h = (C[:, 0] * 73856093 ^ C[:, 1] * 19349663 ^ C[:, 2] * 83492791 ^ seed) & 0xFFFFFF
                j = np.c_[(h % 997) / 997.0, ((h // 997) % 991) / 991.0, ((h // 988027) % 17) / 17.0]
                d = np.linalg.norm(P - (C + j), axis=1); b2 = np.minimum(best2, np.maximum(best1, d)); best1 = np.minimum(best1, d); best2 = b2
    return (best2 - best1) * cell_mm


# ------------------------------------------------------------------ leather smoothing (the wrinkle fix, base side)
_LZ = {}


def leather_w(P):
    """0..1: furless leather (nose.json leather['0'] outline, x-z projection, front y < -62), ramping in over SMOOTH_IN"""
    if not _LZ:
        import json as _j
        ol = np.array(_j.load(open(os.path.join(ROOT, "tripo_rebuild", "layers", "nose.json")))["leather"]["0"]["outline_head"], float)
        _LZ["r"] = V2.Raster2D(ol[:, [0, 2]])
    d = _LZ["r"](np.asarray(P, float)[:, [0, 2]])
    return ss(-d / Q_["SMOOTH_IN"]) * ss((-62.0 - np.asarray(P)[:, 1]) / 1.0)


def smooth_delta(P, base_fn):
    """binomial 3x3x3 smoothing of the BASE field minus the base (mm): removes the sub-mm relief the base carries on the
    leather (measured: 0.025 mm rms p95, 6.9 deg normal scatter on the fine preview) without moving the >= 5 mm form"""
    h = Q_["SMOOTH_STEP"]; w1 = {-1: 0.25, 0: 0.5, 1: 0.25}; acc = np.zeros(len(P))
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                acc += w1[i] * w1[j] * w1[k] * base_fn(P + h * np.array([i, j, k], float))
    return acc - base_fn(P)


# ------------------------------------------------------------------ the edit
def edit(P_head_mm, F_mm, graft=True, graft_ref="base", parts=("smooth", "plug", "ala", "groove", "nostril", "philtrum"), chunk=400_000,
         base_fn=None):
    """skin-field edit (mm, negative inside). Only points inside REGION change. graft_ref 'base' = keep the input field in
    the protected band (R2 rule: the base's top edge must pass D1), 'v1' = v2's d_ref graft."""
    P = np.asarray(P_head_mm, float); F = np.array(F_mm, float, copy=True)
    lo, hi = np.array(REGION["lo_mm"]), np.array(REGION["hi_mm"])
    idx = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
    for a0 in range(0, len(idx), chunk):
        ii = idx[a0:a0 + chunk]; Q = P[ii]; f0 = F[ii]; g = f0.copy()
        if "groove" in parts and base_fn is not None:
            for S in SIDES.values():
                if getattr(S, "_leg_base", None) != id(base_fn):
                    S.project_leg(base_fn)
        if "smooth" in parts and base_fn is not None:            # needs the base field function (skin_build_v3 mode A has it)
            wl = leather_w(Q); ml = wl > 0
            if ml.any():
                g[ml] = g[ml] + wl[ml] * smooth_delta(Q[ml], base_fn)
            f0 = g.copy()                                         # the graft keeps the SMOOTHED base in the protected band
        for S in SIDES.values():
            if "plug" in parts:                 # no smooth-min halo on the corner leg (it lifted the tail entry 0.1 mm)
                kp = K_PLUG * ss(seg_dist(Q, S.tail_tip, S.corner)[0] / 1.0)
                g = smin_k(g, S.plug(Q), kp)
            if "ala" in parts:
                g = g - S.ala(Q)
            if "groove" in parts:
                g = g + S.groove(Q)
        if "nostril" in parts:
            for S in SIDES.values():
                lum = smax(S.lumen(Q), -S.ridge_sdf(Q), 0.08)
                g = smax(g, -lum, K_LUMEN)
                g = smax(g, -S.slit(Q), Q_["K_SLIT"])
        if "philtrum" in parts:
            z = Q[:, 2]; zc = np.clip(z, V2.PH_Z[2], V2.PH_Z[0])
            base = np.polyval(_PHC, np.clip(zc, V2.PH_BZ.min(), V2.PH_BZ.max()))
            dep = np.maximum(np.interp(-zc, -V2.PH_Z, V2.PH_D) - base, 0.05)
            hw = np.interp(-zc, -V2.PH_Z, V2.PH_HW); xc = np.interp(-zc, -V2.PH_Z, V2.PH_X)
            fade = ss((V2.PH_Z[0] + 0.8 - z) / 0.8) * ss((z - (V2.PH_Z[2] - 0.8)) / 0.8)
            gate = ss((-63.0 - Q[:, 1]) / 2.0)
            g = g + dep * fade * gate * 2.0 ** (-(2 * (Q[:, 0] - xc) / hw) ** 2)
        if graft:
            w = mask_w(Q); m = w < 1
            if m.any():
                ref = f0[m] if graft_ref == "base" else V2.d_ref(Q[m])
                g[m] = w[m] * g[m] + (1 - w[m]) * ref
        F[ii] = g
    return F


def contract_probe(grid_mm, slit_grid_mm=None):
    sg = grid_mm if slit_grid_mm is None else slit_grid_mm
    ok = grid_mm <= NEED_MM + 1e-9 and sg <= NEED_MM_SLIT + 1e-9
    return dict(status="PASS" if ok else "FAIL", grid_mm=grid_mm, slit_band_grid_mm=sg, need_mm=NEED_MM, need_slit_mm=NEED_MM_SLIT)


def geometry_report():
    """clearances of the v3 parts (checked arithmetic on the declared geometry)"""
    out = {"philtrum_base_fit": philtrum_base_fit(), "graft_core": {k: v for k, v in _ref3().items() if k in ("excluded", "v2_excluded")}}
    for sd, S in SIDES.items():
        q = S.comma - S.c; d2 = S.v2.poly(np.c_[q @ S.v2.u1, q @ S.v2.u2])
        out[sd] = {"comma_chord_mm": round(float(np.linalg.norm(S.comma[-1] - S.comma[0])), 3),
                   "comma_inside_rim_max_d2_mm": round(float((d2 + S.r).max()), 3),
                   "comma_to_arc_min_mm": round(float(np.min(np.linalg.norm(S.comma[:, None] - ARC[None], axis=2) - S.r[:, None])), 3),
                   "comma_to_graft_core_min_mm": round(float((_ref3()["tree"].query(S.comma)[0] - S.r).min()), 3),
                   "corner_leg_mm": round(float(np.linalg.norm(S.corner - S.tail_tip)), 3), "corner_head_mm": np.round(S.corner, 2).tolist(),
                   "wedge_target_K_mm": np.round(S.K, 2).tolist()}
    return out
