"""MOUTH v3 feature (felid pack, case cat1, cat v3) - builder 'feat-mouth-v3', 2026-10-18. feat_mouth.py (v2) is IMPORTED
and left unchanged; its GEOM (feat_mouth_geom.json), lines, sections, slot sheet, overhang and every value not overridden
here stand (spec_mouth.json, check_mouth.json, V3_BRIEF 'MOUTH / CHIN: distorted').

THE PERSON: "the basic structure of the cat lips on the last version was impressive. just needs a little refinement".
So v3 keeps v2's structure (upper-lip lobes overhanging a recessed lower lip over a hidden slot, the Y notch, commissure
creases) and refines only what the review and the probes name.

WHAT CHANGES
  * RESOLUTION CONTRACT (A20), DECLARED: REGION (v2's box, unchanged format (lo, hi) head mm), NEED_MM = 0.10 inside REGION
    (slot gap g = 0.30 mm -> 3 voxels; skin_build_v3 meshes the mouth at 0.5 / 5 = 0.10 mm), and opening_sdf(P) = the
    INTENDED AIR of the mouth slot (the sheet A -> P0 -> P1 -> P2 of every section, half-width g / 2, inside the Z tube):
    fill_voids must never seal it (NOTES_v3 A20; v2 sealed 311 voxels of it at 0.5 mm -> lumps, swollen pout).
  * CHIN WITHOUT A RING LINE. v2 cut the lower-lip face with a VERTICAL plane through the contact C and switched the
    cut off by lifting the plane 3 mm over 1 mm of height (wC, 0.5 mm below C .. 0.5 above), joined to the skin by a
    0.2 mm smooth-max: two hard creases that run round the chin from corner to corner, parallel to the lip line. v3: the
    plane is vertical down to LL_H0 below C, then RECEDES on a circular arc of radius LL_RC into a backward slope LL_SL
    (C1 continuous, never lifted back) and meets the skin through a LL_K smooth-max; where the base already lies behind
    it nothing changes, so no cut has to be switched off.
  * CORNERS WITHOUT LUMPS. v2 floored the overhang step sigma at SIG_MIN 0.6 mm to the very corner and cut the edit off
    1 mm past it (Z_END): a 0.6 mm step ending in 1 mm = a knob at each corner. v3 lets the step die out over the last
    CT mm of the line (sigma floor SIG_MIN -> SIG_END, margin roundings scaled with it) and fades the edit past the corner
    over Z_END3 mm, so the margins converge into the commissure crease.
  * THE Y (midline): UNCHANGED from v2 (MID_W = 0). Tried and reverted (probe runs 1-2): a union of both sides' edits
    lost the Y notch; adding only the other side's slot air removed the own lobe at s = 0.5. OPEN: 'lips not separated
    at R s = 0.5' (v2 code fails it too; the probe ray there crosses the notch air, 2.2 mm).
  * DEEP SHEET TUBE: the slot sheet reaches |P0a| + D_in behind U (up to ~7.6 mm where sigma ~5); v2's 8 mm tube faded it
    (Z 0.82). v3 widens the tube per station (z_r = max(Z_R, |P0a| + D + Z_CLEAR)); REGION grows with it. OPEN: with
    v2's nearest-U station rule the slot mid-sheet at L s = 19-21 and R s = 19.5 is still SOLID in the field (points
    5 mm behind U take stations 18.6 / 21.3); STATION_BY = 'sheet' opens it (field air 1.0) but made label-jump seams
    (run 3), so it is off.
  * OPENING NEVER SEALED: opening_sdf() is what skin_build_v3.fill_voids_v3 / the integrator must protect.

API (skin_build_v3 / skin_feat_integrate read feat_mouth names): REGION ; NEED_MM ; RESOLUTION ; GEOM ; edit(P, F) ;
opening_sdf(P) ; fix_zone(P) ; probe_inputs() ; Y_HEAD_MM() ; contract_probe(grid_mm) ; V3_PARAMS
usage: the preview + probes are tripo_rebuild/mouth_v3_preview.py (preview base|v2|v3 [grid] | probe).
"""
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feat_mouth as V2  # noqa: E402  (Phase 2, unchanged)

MID_X, S_C, DS = V2.MID_X, V2.S_C, V2.DS
ss, smax, _seg2 = V2.ss, V2.smax, V2._seg2
G, R_M, D_IN, LOW_R = V2.G, V2.R_M, V2.D_IN, V2.LOW_R
Z_R, Z_W = V2.Z_R, V2.Z_W
CREASE_L, CREASE_D0, CREASE_W = V2.CREASE_L, V2.CREASE_D0, V2.CREASE_W

# ------------------------------------------------------------------ the resolution contract (A20), declared
GRID_CAP_MM = 0.15
NEED_MM = 0.10
RESOLUTION = {"region_mm": NEED_MM, "cap_mm": GRID_CAP_MM,
              "source": "slot gap g = 0.30 mm needs <= g / 2.5 = 0.12 (v2 hand-off); 0.10 = 3 voxels across the gap and "
                        "skin_build_v3's r = 5 at 0.5 mm; the opening (opening_sdf) must stay air"}

V3_PARAMS = {
    "LL_H0": (1.0, "the lower-lip face stays vertical down to 1.0 mm below the contact C (v2 kept the plane to C - 0.5 and "
                   "then lifted it; the probes' hidden-top / sigma heights are all above C)", "estimate"),
    "LL_RC": (2.0, "radius of the arc on which the face recedes below LL_H0 (no crease: C1 join)", "estimate"),
    "LL_SL": (1.2, "backward slope of the receding face beyond the arc (50 deg from vertical); the chin is the skin's", "estimate"),
    "LL_K": (0.6, "smooth-max blend of the receding face with the skin (v2 0.2 mm = a hard crease)", "estimate"),
    "CT": (3.0, "the overhang step dies out over the last 3 mm of the line (s_c - 3 .. s_c); the photo's corner shows the "
                "upper lip meeting the lower without a step", "estimate"),
    "SIG_END": (0.45, "sigma floor AT the corner (v2 0.6 to the end); keeps flap - g / 2 >= 0.2 mm where g has gone to 0", "estimate"),
    "R_SCALE_END": (0.5, "margin / lower-lip roundings scale to 0.5 x at the corner with the step", "estimate"),
    "Z_END3": (2.5, "the edit fades over 2.5 mm past the corner (v2 1.0 mm: the knob)", "estimate"),
    "MID_W": (0.0, "midline band DISABLED (v2 rule: L for x >= MID_X). Runs 1-2: a union of both edits lost the Y notch; the "
                   "other side's slot air removed the own lobe at s = 0.5 (flap 0.04 mm). Left as an OPEN item", "construction"),
    "STATION_BY": ("U", "station assignment: 'U' (v2, nearest margin point; KEPT) or 'sheet' (nearest slot-sheet sample: run 3 made label-jump seams, overhang FAIL, ring lines at h -2.7); "
                            "probe run 2 (M1) found the v2 rule seals the slot at L s = 19-21 in the field itself", "construction"),
    "Z_CLEAR": (2.5, "the edit tube reaches 2.5 mm past the slot sheet's inner end (+ the 2 mm fade) at every station", "construction"),
    "MID_K": (0.1, "smooth-max blend of the own-side edit with the other side's slot air in the midline band", "construction"),
}
Q_ = {k: v[0] for k, v in V3_PARAMS.items()}


def _geom3(G2):
    """v3 per-station geometry from v2's GEOM: the corner taper of the sigma floor (P0a, sigma, lloff recomputed from v2's
    raw sigma), the taper weight tc (1 on the line, 0 at the corner) and the scaled roundings"""
    out = {}
    for sd, Gs in G2.items():
        g = {k: np.asarray(v).copy() for k, v in Gs.items()}
        nl0 = g["nl2"][:, 0]; dlt2 = g["lloff"] / np.maximum(nl0, 1e-9); sig0 = g["sigma"] - dlt2
        tc = ss((S_C - g["s"]) / Q_["CT"])
        floor = Q_["SIG_END"] + (V2.SIG_MIN - Q_["SIG_END"]) * tc
        dlt3 = np.maximum(floor - sig0, 0.0)
        g["P0a"] = g["P0a"] + dlt2 - dlt3; g["sigma"] = sig0 + dlt3; g["lloff"] = dlt3 * nl0
        g["tc"] = tc; rs = Q_["R_SCALE_END"] + (1 - Q_["R_SCALE_END"]) * tc
        g["r_m"] = R_M * rs; g["low_r"] = LOW_R * rs
        # tube radius per station: the slot sheet reaches |P0a| + D_in behind U (6.4 mm at L s = 20, sigma 5.2), past v2's
        # 8 mm tube's 6-8 mm fade (probe run 3: Z = 0.82 there, the sheet's back third stayed solid = sealed by design)
        g["z_r"] = np.maximum(Z_R, -g["P0a"] + g["D"] + Q_["Z_CLEAR"])
        out[sd] = g
    return out


GEOM = _geom3(V2.GEOM) if V2.GEOM is not None else None


def region(geom=None):
    """v2's box rule with the v3 tube: U, C, crease +- (max station tube radius + 0.5) mm; Z_END3 lies inside it"""
    geom = geom or GEOM; A = np.concatenate([geom[k][q] for k in ("L", "R") for q in ("U", "C", "crease")])
    zr = max(float(np.max(geom[k]["z_r"])) for k in ("L", "R"))
    return np.floor(A.min(0) - zr - 0.5), np.ceil(A.max(0) + zr + 0.5)


REGION = region() if GEOM is not None else None
_TREES = {}


def _sheet_samples(G_, step=0.2):
    """3-D points on every station's slot polyline QA -> P0 -> P1 -> P2 (section coords -> head mm), labelled by station"""
    pts, lab = [], []
    for k in range(len(G_["s"])):
        P0 = np.array([G_["P0a"][k], 0.0]); P1 = P0 + G_["v"][k] * G_["eu2"][k]; P2 = P1 - np.array([G_["D"][k], 0.0])
        for A, B in ((np.array([2.0, 0.0]), P0), (P0, P1), (P1, P2)):
            m = max(int(np.ceil(np.linalg.norm(B - A) / step)), 1); t = np.linspace(0, 1, m + 1)[:, None]; ah = A + t * (B - A)
            pts.append(G_["U"][k] + ah[:, :1] * G_["n"][k] + ah[:, 1:] * G_["b"][k]); lab.append(np.full(len(ah), k))
    return np.vstack(pts), np.concatenate(lab)


def _trees(G_):
    k = id(G_)
    if k not in _TREES:
        X, lab = _sheet_samples(G_)
        _TREES[k] = (cKDTree(G_["U"]), cKDTree(G_["crease"]), cKDTree(X), lab)
    return _TREES[k]


def _ramp(x):
    """0 for x <= 0; a circular-ish arc of radius LL_RC turning into slope LL_SL (C1)"""
    x = np.maximum(x, 0.0); rc, sl = Q_["LL_RC"], Q_["LL_SL"]; xs = rc * sl
    return np.where(x < xs, x * x / (2 * rc), sl * x - 0.5 * sl * xs)


def _section(q, G_):
    """section coordinates and slot-sheet distance at q (shared by the edit and the opening field)"""
    tU, _, tS, lab = _trees(G_)
    dist, _ = tU.query(q)                       # the tube distance stays v2's (nearest margin point)
    dS, j = tS.query(q); i = lab[j]             # v3: the STATION is the one whose slot sheet is nearest (see _sheet_samples)
    if Q_["STATION_BY"] == "U":
        dist, i = tU.query(q)
    d = q - G_["U"][i]
    a = (d * G_["n"][i]).sum(1); h = (d * G_["b"][i]).sum(1); e = (d * G_["t"][i]).sum(1)
    Z = ss((G_["z_r"][i] - dist) / Z_W); end = (i == len(G_["s"]) - 1) & (e > 0); Z[end] *= ss((Q_["Z_END3"] - e[end]) / Q_["Z_END3"])
    g, v, D = G_["g"][i], G_["v"][i], G_["D"][i]
    QA = np.stack([np.full(len(q), 2.0), np.zeros(len(q))], 1); P0 = np.stack([G_["P0a"][i], np.zeros(len(q))], 1)
    P1 = P0 + v[:, None] * G_["eu2"][i]; P2 = P1 - np.stack([D, np.zeros(len(q))], 1)
    dist2 = np.minimum(np.minimum(_seg2(a, h, QA, P0), _seg2(a, h, P0, P1)), _seg2(a, h, P1, P2))
    return dict(i=i, a=a, h=h, e=e, Z=Z, g=g, v=v, P0=P0, QA=QA, dist2=dist2, end=end)


def _edit_side(q, F, G_):
    S = _section(q, G_); i, a, h, Z, g, v, P0, QA, dist2 = (S[k] for k in ("i", "a", "h", "Z", "g", "v", "P0", "QA", "dist2"))
    nl, eu = G_["nl2"][i], G_["eu2"][i]
    wB = (a - P0[:, 0]) * nl[:, 0] + (h - P0[:, 1]) * nl[:, 1]; uB = (a - P0[:, 0]) * eu[:, 0] + (h - P0[:, 1]) * eu[:, 1]
    dA = P0 - QA; crossA = dA[:, 0] * (h - QA[:, 1]) - dA[:, 1] * (a - QA[:, 0])
    lower = ((wB < 0) & (uB < v)) | ((wB >= 0) & (crossA >= 0))
    delta = np.where(lower, -dist2, dist2)
    dc = q - G_["C"][i]; dLL = (dc * G_["nLL"][i]).sum(1) + G_["lloff"][i]; hc = (dc * G_["eup"][i]).sum(1)
    kLL = 0.2 + (Q_["LL_K"] - 0.2) * ss((-hc - 0.5) / 1.5)                 # v2's 0.2 under the overhang, LL_K below
    fLL = smax(F, dLL + _ramp(-hc - Q_["LL_H0"]), kLL)                     # v3: receding face, no lift-back crease
    rm, lr = G_["r_m"][i], G_["low_r"][i]
    fup = smax(F, g / 2 - delta, rm); flo = smax(fLL, delta + g / 2, lr)
    out = Z * np.minimum(fup, flo) + (1 - Z) * F
    tc = _trees(G_)[1]; dcr, ic = tc.query(q); lc = G_["crease_l"][ic]
    out += CREASE_D0 * np.clip(1 - lc / CREASE_L, 0, 1) * np.exp(-(dcr / CREASE_W) ** 2) * (dcr < 3 * CREASE_W)
    return out


def edit(P_head_mm, F_mm, geom=None, chunk=400000):
    """the v3 mouth edit of the skin field; P (N,3) head-frame mm, F (N,) mm (negative inside) -> new F (N,)"""
    geom = geom or GEOM
    P = np.asarray(P_head_mm, float); F = np.array(F_mm, float, copy=True)
    lo, hi = region(geom); idx = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
    for c0 in range(0, len(idx), chunk):
        ii = idx[c0:c0 + chunk]; q = P[ii]; f0 = F[ii]; x = q[:, 0] - MID_X
        band = np.abs(x) < Q_["MID_W"]; out = f0.copy()
        mL = (x >= 0) & ~band; mR = (x < 0) & ~band
        if mL.any():
            out[mL] = _edit_side(q[mL], f0[mL], geom["L"])
        if mR.any():
            out[mR] = _edit_side(q[mR], f0[mR], geom["R"])
        if band.any():                    # the Y: own side's edit + the OTHER side's slot air only (run 1: a union of the
            qb, fb, xb = q[band], f0[band], x[band]                          # whole edits carved the other lobe: notch lost)
            for own, oth, m in (("L", "R", xb >= 0), ("R", "L", xb < 0)):
                if m.any():
                    e = _edit_side(qb[m], fb[m], geom[own]); o = _slot_air(qb[m], geom[oth])
                    ob = out[band]; ob[m] = smax(e, -o, Q_["MID_K"]); out[band] = ob
        F[ii] = out
    return F


def _slot_air(q, G_):
    S = _section(q, G_); return np.where((S["Z"] > 0.5) & (S["g"] > 0.05), S["dist2"] - S["g"] / 2, 1e3)


def opening_sdf(P, geom=None):
    """the INTENDED AIR of the mouth slot (mm, < 0 inside): distance to the slot sheet minus g/2, where the Z tube holds
    (Z > 0.5) and the gap exists (g > 0.05); +inf elsewhere. Protect it: fill_voids must never seal it (A20)."""
    geom = geom or GEOM; P = np.asarray(P, float); out = np.full(len(P), np.inf)
    lo, hi = region(geom); b = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
    if len(b) == 0:
        return out
    q = P[b]; x = q[:, 0] - MID_X; o = np.full(len(q), np.inf)
    for sd, m in (("L", x >= -Q_["MID_W"]), ("R", x < Q_["MID_W"])):
        if m.any():
            val = _slot_air(q[m], geom[sd]); o[m] = np.minimum(o[m], np.where(val >= 1e3, np.inf, val))
    out[b] = o; return out


def fix_zone(P, geom=None):
    """True where v3 MEANS to differ from v2 (for the 'lip silhouette within 0.5 mm of v2 outside the fixes' check):
    the corner taper zone (within CT + 1 mm of the corner along the line, + Z_END3 past it), the chin below LL_H0 - 0.5,
    and the midline band"""
    geom = geom or GEOM; P = np.asarray(P, float); m = np.abs(P[:, 0] - MID_X) < Q_["MID_W"] + 0.3
    for sd in ("L", "R"):
        G_ = geom[sd]; tU = _trees(G_)[0]; dist, i = tU.query(P)
        m |= (G_["s"][i] > S_C - Q_["CT"] - 1.0) & (dist < Z_R)
        m |= G_["z_r"][i] > Z_R + 1e-6                                       # the widened tube (deep sheet)
        dc = P - G_["C"][i]; hc = (dc * G_["eup"][i]).sum(1); m |= (hc < -(Q_["LL_H0"] - 0.5)) & (dist < Z_R + Z_W)
    return m


def probe_inputs(geom=None, stations=(2.0, 7.0, 12.0, 20.0)):
    """v2's probe inputs from the v3 geometry (sigma / P0a now carry the corner taper)"""
    return V2.probe_inputs(geom or GEOM, stations)


def Y_HEAD_MM(geom=None):
    return V2.Y_HEAD_MM(geom or GEOM)


def contract_probe(grid_mm):
    ok = grid_mm <= NEED_MM + 1e-9
    return dict(status="PASS" if ok else "FAIL", grid_mm=grid_mm, need_mm=NEED_MM, cap_mm=GRID_CAP_MM,
                why="REGION meshed at %.3f mm (need <= %.2f)" % (grid_mm, NEED_MM))
