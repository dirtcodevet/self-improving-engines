"""NOSE v3b feature (felid pack, case cat1, cat v3 round 2) - owner 'nose', ruling R-N (NOTES_v3 13:25), 2026-10-18.

The person (13:15, NS1): "there's also no nasal cavities and the line and shapes of the nose leather are basically all
smoothed out rather than being present". feat_nose.py (v2) and feat_nose_v3.py (v3) are IMPORTED and left unchanged.
Every number comes from spec_nose_v3b.json (one definition, M7), each with its source and confidence.

WHAT v3b BUILDS (owner, not inherited from the blurred Tripo field)
  * NASAL CAVITY. Each nostril opens into the vestibule (v2 centreline H -> P1 -> P2, unchanged) and the passage runs on
    BACK AND UP into the head (PASS_SEGS: 6 + 6 + 5 mm, rising 0.25 -> 0.45 -> 0.60), narrowing (LUMEN_*) to a blind end
    in front of the eye REGION; the turn at P1 keeps the deep part out of every line of sight, so it darkens.
  * THE WHOLE COMMA LEADS IN. v3's comma slot (stations, radii and bow kept: N1 PASS) dropped 1.2 mm and ramped to s 1.5:
    its tail end stayed a 1.4 mm trench (v3 N2's blind pixels, located this run). v3b: each station drops CLEFT_IN along
    n_in, then runs as a cleft to the centreline at s = CLEFT_S[0] (head) .. CLEFT_S[1] (tail): the comma's lateral slit
    leads caudally along the alar fold into the vestibule (Diaz Martinez 2024). The alar-fold ridge (v2 rule) rides the
    v3b centreline at s 0.5-6.
  * WING EDGES crisp: the vestibule is carved into the leather with K_LUM_B (0.15) instead of 0.3.
  * MEDIAN GROOVE from the photo: onset z ~ -8.8 (between the nostril heads), 0.5-0.6 mm wide on the leather, running down
    the stem into the philtrum to the Y junction; a compact biweight section, applied as a SURFACE depth (field offset x
    |grad F|: the base is not a unit SDF, feat_nose_v3 Tool lesson 3). The base's OWN blurred midline valley (measured
    0.12-0.58 mm deep, 1.1-1.7 mm wide on a lines-absent build: BASE_VALLEY) is first BRIDGED by a C1 cubic Hermite of
    the base across it (bridge_delta), then the photo groove is cut (GROOVE_MED minus the measured residue
    GROOVE_CUT_CORRECTION). The check reads GROOVE_MED_TARGET (the photo as measured).
  * ALAR GROOVE / COMMA TAILS into the approved corners: v3's construction (D2 PASS on v3), its open_end -> tail_tip leg
    now scaled by |grad F| as well.
  * COBBLED PLANUM: a zero-mean polygonal crease network (Worley F2 - F1), cell COBBLE.cell_mm, on the furless leather,
    fading at the outline and at the openings. designed_relief(P) returns it so the wrinkle check can subtract it.
  * BASE CLEANING (the leather + its top band): 3-tap binomial per WORLD axis at CLEAN_H removes the v2 cores' 2/mm
    Keys ringing (the ribs under the approved top edge) while moving the surface <= 0.041 mm (checked).

API (feat_nose_v3's, kept): REGION, edit(P_mm, F_mm, ..., base_fn=None), probe_inputs(), RESOLUTION, edit_zone(P),
  opening_sdf(P), slit_band(P), contract_probe(...), geometry_report(); new: REGION_BOXES, leather_band(P),
  designed_relief(P) (the cobbles, applied by edit), declared_relief(P) (cobbles + groove cut, for the wrinkle check),
  line_zone(P), cavity_centrelines(), bridge_delta(P, base_fn). edit() needs base_fn (the PRE field) for the cleaning,
  |grad F|, the valley bridge and the groove-path projections; without it those parts fall back (no cleaning, gn = 1).
Checks and harness: engine/checks/nose_checks_v3b.py.
REGION grows (the passage): see REGION / REGION_BOXES and the report.
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feat_nose as V2  # noqa: E402  (Phase 2, unchanged)
import feat_nose_v3 as N3  # noqa: E402  (v3, unchanged)

ROOT = V2.ROOT
SPEC_B = json.load(open(os.path.join(HERE, "spec_nose_v3b.json")))
PR = SPEC_B["params"]
ARC = V2.ARC
TAIL_ZONE_MM = V2.TAIL_ZONE_MM
ss, smin, smax, unit, seg_dist = V2.ss, V2.smin, V2.smax, V2.unit, V2.seg_dist
smin_k = N3.smin_k
K_PLUG = V2.K_PLUG

_RG = SPEC_B["region"]
REGION_BOXES = [{"lo_mm": list(_RG["v3_box"]["lo_mm"]), "hi_mm": list(_RG["v3_box"]["hi_mm"])},
                {"lo_mm": list(_RG["passage_box"]["lo_mm"]), "hi_mm": list(_RG["passage_box"]["hi_mm"])}]
REGION = {"lo_mm": list(_RG["bounding_box"]["lo_mm"]), "hi_mm": list(_RG["bounding_box"]["hi_mm"])}

GRID_CAP_MM = 0.15
NEED_MM = SPEC_B["resolution"]["region_mm"]
NEED_MM_LEATHER = SPEC_B["resolution"]["leather_mm"]
NEED_MM_SLIT = SPEC_B["resolution"]["slit_band_mm"]
RESOLUTION = {"region_mm": NEED_MM, "leather_mm": NEED_MM_LEATHER, "slit_band_mm": NEED_MM_SLIT, "cap_mm": GRID_CAP_MM,
              "leather_band": "leather_band(P): the furless leather outline dilated 1.5 mm, within 1.0 mm of the surface",
              "slit_band": "slit_band(P): within 0.6 mm of the comma slot / cleft",
              "source": SPEC_B["resolution"]["why"]}

D_VEST = float(PR["D_VEST"]["value"])
K_SLIT = N3.Q_["K_SLIT"]
K_LUM_B = float(PR["K_LUM_B"]["value"])
CLEAN_H = float(PR["CLEAN_H"]["value"])
CB = PR["COBBLE"]
GM = {k: np.array(PR["GROOVE_MED"][k], float) for k in ("z", "depth", "fwhm", "x")}
BV = {k: np.array(PR["BASE_VALLEY"][k], float) for k in ("z", "depth", "fwhm", "x")}
GC = {k: np.array(PR["GROOVE_CUT_CORRECTION"][k], float) for k in ("z", "value")}
GT = {k: np.array(PR["GROOVE_MED_TARGET"][k], float) for k in ("z", "depth", "fwhm", "x")}   # what the LP check reads (photo)


def in_boxes(P):
    P = np.asarray(P, float); m = np.zeros(len(P), bool)
    for b in REGION_BOXES:
        m |= np.all((P >= np.array(b["lo_mm"])) & (P <= np.array(b["hi_mm"])), axis=1)
    return m


# ------------------------------------------------------------------ the side: vestibule + passage + cleft
class SideV3b:
    def __init__(self, sd):
        S3 = N3.SIDES[sd]; S2 = S3.v2; self.sd, self.s3, self.v2 = sd, S3, S2
        for k in ("H", "open_end", "tail_tip", "rim", "c", "nrm", "n_in", "n_out", "e1", "e2", "T0", "ala_c", "comma", "r",
                  "top", "t", "corner", "path"):
            setattr(self, k, getattr(S3, k))
        H, T0 = S2.H, S2.T0
        P1 = H + 2.0 * T0; P2 = P1 + 3.0 * unit([0, 1, 0.15]); pts = [H - 2.5 * T0, H, P1, P2]
        for L_, rise in PR["PASS_SEGS"]["value"]:
            pts.append(pts[-1] + L_ * unit([0, 1, rise]))
        self.ctrl = np.array(pts)
        cl = V2.catmull(pts, 300); s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(cl, axis=0), axis=1))]
        s = s - s[np.argmin(np.linalg.norm(cl - H, axis=1))]
        ss_ = np.arange(s[0], s[-1] + 1e-9, 0.04)
        self.cl = np.c_[[np.interp(ss_, s, cl[:, k]) for k in range(3)]].T; self.s = ss_; self.L = ss_[-1]
        self.T = unit(np.gradient(self.cl, axis=0))
        A = self.e1 - (self.T @ self.e1)[:, None] * self.T; self.A = unit(A); self.B = np.cross(self.T, self.A)
        st = PR["LUMEN_S"]["value"]
        self.a = np.interp(np.clip(ss_, 0, None), st, PR[f"LUMEN_A_{sd}"]["value"])
        self.b = np.interp(np.clip(ss_, 0, None), st, PR[f"LUMEN_B_{sd}"]["value"])
        self.tree = cKDTree(self.cl)
        # alar-fold ridge: the v2 rule (feat_nose.Side) along the v3b centreline
        lat = np.array([-1.0 if sd == "R" else 1.0, 0, 0]); up = np.array([0, 0, 1.0]); cen = []; rdir = []
        for i in np.nonzero((ss_ >= 0.5) & (ss_ <= 6.0))[0]:
            T = self.T[i]; u = unit(lat * np.cos(np.radians(45)) + up * np.sin(np.radians(45))); u = unit(u - (u @ T) * T)
            ca, cb = u @ self.A[i], u @ self.B[i]; rho = 1.0 / np.sqrt((ca / self.a[i]) ** 2 + (cb / self.b[i]) ** 2)
            p = min(V2.RIDGE_P, 0.6 * rho) * ss((ss_[i] - 0.5) / 1.0) * (1 - ss((ss_[i] - 3.5) / 2.5))
            cen.append(self.cl[i] + u * (rho + V2.RIDGE_R - p)); rdir.append(u)
        self.ridge = np.array(cen); self.ridge_dir = np.array(rdir); self.ridge_tree = cKDTree(self.ridge)
        # comma slot + cleft: station i -> top_i -> B1_i (CLEFT_IN along n_in) -> C_i (centreline at s_c(t_i))
        c0, c1 = PR["CLEFT_S"]["value"]; din = float(PR["CLEFT_IN"]["value"])
        self.B1 = self.comma + din * self.n_in
        sc = c0 + (c1 - c0) * self.t
        self.C = np.c_[[np.interp(sc, ss_, self.cl[:, k]) for k in range(3)]].T
        X, R = [], []
        for a_, b_, c_, r_ in zip(self.top, self.B1, self.C, self.r):
            for p0, p1 in ((a_, b_), (b_, c_)):
                n = max(int(np.ceil(np.linalg.norm(p1 - p0) / 0.03)), 1); w = np.linspace(0, 1, n + 1)[:, None]
                X.append(p0 + w * (p1 - p0)); R.append(np.full(n + 1, r_))
        self.slit_pts = np.vstack(X); self.slit_r = np.concatenate(R); self.slit_tree = cKDTree(self.slit_pts)
        self.slit_lo = self.slit_pts.min(0) - 2.5; self.slit_hi = self.slit_pts.max(0) + 2.5

    # ---- parts
    def lumen(self, Q):
        """swept ellipse (v2 rule, feat_nose.Side.lumen) along the v3b centreline, rounded end cap (mm, < 0 inside)"""
        _, i = self.tree.query(Q); C = self.cl[i]; D = Q - C
        ax = np.einsum("ij,ij->i", D, self.T[i]); qa = np.einsum("ij,ij->i", D, self.A[i]); qb = np.einsum("ij,ij->i", D, self.B[i])
        a, b = self.a[i], self.b[i]
        over = np.where(i == len(self.cl) - 1, np.maximum(ax, 0), 0.0)
        return (np.sqrt((qa / a) ** 2 + (qb / b) ** 2 + (over / a) ** 2) - 1) * np.minimum(a, b)

    def ridge_sdf(self, Q):
        d, _ = self.ridge_tree.query(Q); return d - V2.RIDGE_R

    def cavity(self, Q):
        return smax(self.lumen(Q), -self.ridge_sdf(Q), 0.08)

    def slit(self, Q):
        Q = np.atleast_2d(Q); out = np.full(len(Q), 2.0)
        m = np.all((Q >= self.slit_lo) & (Q <= self.slit_hi), axis=1)
        if m.any():
            k = int(PR["SLIT_KD"]["value"]); d, j = self.slit_tree.query(Q[m], k=k)
            out[m] = np.minimum((d - self.slit_r[j]).min(1), 2.0)
        return out

    def slit_kept(self, Q):
        """the comma slot + cleft as carved: it passes the alar fold, never through it (RIDGE_KEEP)"""
        return smax(self.slit(Q), -self.ridge_sdf(Q), float(PR["RIDGE_KEEP"]["value"]))

    def opening(self, Q):
        return np.minimum(self.cavity(Q), self.slit_kept(Q))

    # ---- alar groove (comma tail) along the whole path, on the base surface
    def project_path(self, base_fn, step=0.05):
        P = self.path; seg = np.linalg.norm(np.diff(P, axis=0), axis=1); L_ = seg.sum(); s = np.arange(0, L_ + 1e-9, step)
        cum = np.r_[0, np.cumsum(seg)]; X = np.c_[[np.interp(s, cum, P[:, k]) for k in range(3)]].T; h = 0.05
        for _ in range(6):
            F_ = base_fn(X); G = np.stack([(base_fn(X + h * e) - base_fn(X - h * e)) / (2 * h) for e in np.eye(3)], 1)
            X = X - (F_ / np.maximum((G ** 2).sum(1), 1e-9))[:, None] * G
        self.ag = X; self.ag_s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(X, axis=0), axis=1))]; self.ag_tree = cKDTree(X)
        self._ag_base = id(base_fn)

    def alar_groove(self, Q):
        """surface depth (mm, >= 0) of the comma-tail groove: ALAR_GROOVE depth along the projected path, biweight section,
        easing to corner_end over the last fade_mm before the approved corner"""
        if getattr(self, "ag_tree", None) is None:
            return np.zeros(len(Q))
        AG = PR["ALAR_GROOVE"]; d, k = self.ag_tree.query(Q, distance_upper_bound=1.0); ok = np.isfinite(d); out = np.zeros(len(Q))
        if ok.any():
            kk = k[ok]; s_end = self.ag_s[-1] - self.ag_s[kk]
            dep = AG["corner_end_mm"] + (AG["depth_mm"] - AG["corner_end_mm"]) * ss(s_end / AG["fade_mm"])
            dep = dep * ss((s_end + 0.25) / 0.25)
            R = AG["fwhm_mm"] / 1.082; u = d[ok] / R; out[ok] = dep * np.clip(1 - u * u, 0, None) ** 2
        return out


SIDES = {sd: SideV3b(sd) for sd in ("R", "L")}


# ------------------------------------------------------------------ zones
_LZ = {}


def _leather_raster():
    if not _LZ:
        ol = np.array(json.load(open(os.path.join(ROOT, "tripo_rebuild", "layers", "nose.json")))["leather"]["0"]["outline_head"], float)
        _LZ["ol"] = ol; _LZ["r"] = V2.Raster2D(ol[:, [0, 2]])
    return _LZ["r"]


def outline_dist(P):
    """signed x-z distance to the furless leather outline (nose.json leather['0'], mm, < 0 inside), front only (y < -62)"""
    P = np.asarray(P, float); d = _leather_raster()(P[:, [0, 2]]); return np.where(P[:, 1] < -62.0, d, 4.0)


def leather_band(P):
    return outline_dist(P) < 1.5


def opening_sdf(P):
    """intended air (mm, < 0 inside): the vestibule + passage (with the alar fold) and the comma slot + cleft, both sides"""
    P = np.asarray(P, float); out = np.full(len(P), np.inf); b = in_boxes(P)
    if b.any():
        Q = P[b]; out[b] = np.minimum(SIDES["R"].opening(Q), SIDES["L"].opening(Q))
    return out


def slit_band(P):
    P = np.asarray(P, float); m = np.zeros(len(P), bool)
    for S in SIDES.values():
        m |= S.slit_kept(P) < 0.6
    return m


def edit_zone(P, dil=1.0):
    return N3.edit_zone(P, dil)


def cavity_centrelines():
    return {sd: {"cl_mm": S.cl[S.s >= 0], "s_mm": S.s[S.s >= 0], "T": S.T[S.s >= 0], "ridge_dir": S.ridge_dir} for sd, S in SIDES.items()}


# ------------------------------------------------------------------ lines and shapes
def median_groove_depth(Q):
    """BUILT surface depth (mm, >= 0) of the median groove at Q (photo + spec table GROOVE_MED, biweight section)"""
    z = Q[:, 2]; zc = np.clip(z, GM["z"].min(), GM["z"].max())
    dep = np.interp(-zc, -GM["z"], GM["depth"]); fw = np.interp(-zc, -GM["z"], GM["fwhm"]); xc = np.interp(-zc, -GM["z"], GM["x"])
    corr = np.interp(-z, -GC["z"], GC["value"], left=0.0, right=0.0)   # the bridge's measured residue (GROOVE_CUT_CORRECTION)
    dep = np.where(dep > 0, np.maximum(dep - corr, np.minimum(dep, 0.05)), 0.0)
    R = fw / 1.082                                          # biweight (1 - (u/R)^2)^2: FWHM = 1.082 R
    u = (Q[:, 0] - xc) / R; prof = np.clip(1 - u * u, 0, None) ** 2
    inz = (z <= GM["z"].max()) & (z >= GM["z"].min())
    gate = ss((-63.0 - Q[:, 1]) / 2.0)
    return np.where(inz, dep * prof * gate, 0.0)


def bridge_band(Q):
    """(xL, xR, weight) of the base-valley bridge at Q: W = 0.5 fwhm + margin around the valley centre, z-faded"""
    z = Q[:, 2]; zc = np.clip(z, BV["z"].min(), BV["z"].max()); fd = float(PR["BASE_VALLEY"]["fade_mm"])
    fw = np.interp(-zc, -BV["z"], BV["fwhm"]); xc = np.interp(-zc, -BV["z"], BV["x"]); W = 0.5 * fw + float(PR["BASE_VALLEY"]["bridge_margin_mm"])
    fade = ss((BV["z"].max() + fd - z) / fd) * ss((z - (BV["z"].min() - fd)) / fd) * ss((-63.0 - Q[:, 1]) / 2.0)
    inb = np.abs(Q[:, 0] - xc) < W
    return xc - W, xc + W, np.where(inb, fade, 0.0)


def bridge_delta(Q, base_fn, h=0.25):
    """F_bridge - F_base: cubic Hermite in x across the valley band from the base's value and x-slope at both ends"""
    xL, xR, w = bridge_band(Q); out = np.zeros(len(Q)); m = w > 0
    if not m.any():
        return out
    q = Q[m]; L_ = q.copy(); L_[:, 0] = xL[m]; R_ = q.copy(); R_[:, 0] = xR[m]; ex = np.array([h, 0, 0])
    FL, FR = base_fn(L_), base_fn(R_); dL = (base_fn(L_ + ex) - base_fn(L_ - ex)) / (2 * h); dR = (base_fn(R_ + ex) - base_fn(R_ - ex)) / (2 * h)
    D = xR[m] - xL[m]; t = (q[:, 0] - xL[m]) / D
    Fb = (2 * t ** 3 - 3 * t ** 2 + 1) * FL + (t ** 3 - 2 * t ** 2 + t) * D * dL + (-2 * t ** 3 + 3 * t ** 2) * FR + (t ** 3 - t ** 2) * D * dR
    out[m] = w[m] * (Fb - base_fn(q)); return out


def median_fill(Q):
    """outward surface displacement (mm, >= 0) that FILLS the base's own blurred midline valley (BASE_VALLEY, measured)"""
    z = Q[:, 2]; zc = np.clip(z, BV["z"].min(), BV["z"].max()); fd = float(PR["BASE_VALLEY"]["fade_mm"])
    dep = np.interp(-zc, -BV["z"], BV["depth"]); fw = np.interp(-zc, -BV["z"], BV["fwhm"]); xc = np.interp(-zc, -BV["z"], BV["x"])
    R = fw / 1.082; u = (Q[:, 0] - xc) / R; prof = np.clip(1 - u * u, 0, None) ** 2
    fade = ss((BV["z"].max() + fd - z) / fd) * ss((z - (BV["z"].min() - fd)) / fd)
    return dep * prof * fade * ss((-63.0 - Q[:, 1]) / 2.0)


def _cobble_raw(P):
    """polygonal crease network: (F2 - F1)/2 Worley distance to the nearest cell wall, mapped to a crease + dome profile (mm)"""
    c = float(CB["cell_mm"]); X = np.asarray(P, float) / c; I = np.floor(X).astype(np.int64)
    b1 = np.full(len(X), np.inf); b2 = b1.copy()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                C = I + np.array([dx, dy, dz]); h = (C[:, 0] * 73856093 ^ C[:, 1] * 19349663 ^ C[:, 2] * 83492791 ^ 29) & 0xFFFFFF
                j = np.c_[(h % 997) / 997.0, ((h // 997) % 991) / 991.0, ((h * 7 // 13) % 983) / 983.0]
                d = np.linalg.norm(X - (C + 0.15 + 0.7 * j), axis=1)
                b2 = np.minimum(b2, np.maximum(b1, d)); b1 = np.minimum(b1, d)
    dC = 0.5 * (b2 - b1) * c                                 # mm to the bisector wall
    wc = float(CB["crease_halfwidth_mm"]); crease = np.clip(1 - (dC / wc) ** 2, 0, None) ** 2
    dome = ss(dC / (float(CB.get("plate_frac", 0.5)) * c))
    return float(CB["dome_mm"]) * dome - float(CB["crease_depth_mm"]) * crease


def _cobble_mean():
    rng = np.random.default_rng(5); P = rng.uniform(-20, 20, size=(400_000, 3)); return float(_cobble_raw(P).mean())


COBBLE_MEAN = _cobble_mean()


def cobble_weight(P, opening=None):
    lo, hi = CB["fade_outline_mm"]; d = outline_dist(P); w = ss((-d - lo) / (hi - lo))
    if opening is None:
        opening = opening_sdf(P)
    o0, o1 = CB["fade_opening_mm"]; w = w * ss((opening - o0) / (o1 - o0))
    w = w * (1 - 0.85 * ss(median_groove_depth(P) / 0.08))       # the groove floor stays clean
    return w


def designed_relief(P, opening=None):
    """the DESIGNED sub-mm relief (mm along the outward normal, + = out): the cobbles, zero-mean, with their fades"""
    P = np.asarray(P, float); out = np.zeros(len(P)); m = outline_dist(P) < 0
    if m.any():
        o = None if opening is None else opening[m]
        out[m] = (_cobble_raw(P[m]) - COBBLE_MEAN) * cobble_weight(P[m], o)
    return out


def declared_relief(P):
    """everything v3b DECLARES as designed sub-mm relief, for the wrinkle check (mm along the outward normal): the cobbles and
    the photo median groove cut. NOT the base-valley fill: what the fill leaves of Tripo's blurred valley is residue the
    check must see."""
    P = np.asarray(P, float); return designed_relief(P) - median_groove_depth(P)


def line_zone(P):
    """True where a DESIGNED line or shape lies (the wrinkle check excludes it): median groove band, alar groove paths
    (+-0.8 mm), nostril openings and wings (edit_zone dil 1.0 + within 1.0 mm of the opening), ala footprints"""
    P = np.asarray(P, float); m = edit_zone(P, dil=1.0)
    m |= opening_sdf(P) < 1.0                                      # the wing edges / opening rims (designed edges)
    z = P[:, 2]; xc = np.interp(-np.clip(z, GM["z"].min(), GM["z"].max()), -GM["z"], GM["x"])
    m |= (np.abs(P[:, 0] - xc) < 1.2) & (z < GM["z"].max() + 0.3)
    for S in SIDES.values():
        m |= N3.dist_to_path(P, S.path) < 0.8
        q = P - S.ala_c; qq = (q @ S.v2.e1 / S.v2.ala_r[0]) ** 2 + (q @ S.v2.e2 / S.v2.ala_r[1]) ** 2; m |= qq < 1.3
    return m


# ------------------------------------------------------------------ base helpers (need base_fn)
def _world_axes_head():
    import partition as PT                               # rows = world x/y/z axes in the head frame
    return np.asarray(PT.HR, float)


def clean_and_grad(P, base_fn, h=CLEAN_H):
    """(LP(base) - base, |grad base|): 3-tap binomial per WORLD axis at h (zero at 2/mm = the cores' ringing) and the
    central-difference gradient on the same stencil (h 0.25 also cancels the 2/mm ripple's slope)"""
    E = _world_axes_head(); w1 = {-1: 0.25, 0: 0.5, 1: 0.25}; acc = np.zeros(len(P)); F0 = None; G = np.zeros((len(P), 3))
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                f = base_fn(P + h * (i * E[0] + j * E[1] + k * E[2])); acc += w1[i] * w1[j] * w1[k] * f
                if (i, j, k) == (0, 0, 0):
                    F0 = f
                if abs(i) + abs(j) + abs(k) == 1:
                    ax = 0 if i else (1 if j else 2); G[:, ax] += (i + j + k) * f / (2 * h)
    return acc - F0, np.linalg.norm(G, axis=1)


def grad_norm(P, base_fn, h=CLEAN_H):
    E = _world_axes_head(); G = np.zeros((len(P), 3))
    for ax in range(3):
        G[:, ax] = (base_fn(P + h * E[ax]) - base_fn(P - h * E[ax])) / (2 * h)
    return np.linalg.norm(G, axis=1)


# ------------------------------------------------------------------ the edit
PARTS = ("clean", "plug", "ala", "groove", "median", "cobble", "cavity", "slit", "graft")


def edit(P_head_mm, F_mm, graft=True, parts=PARTS, chunk=200_000, base_fn=None):
    """skin-field edit (mm, negative inside). Only points inside REGION_BOXES change. base_fn (the PRE-edit base field,
    head mm -> mm) is needed for the cleaning, |grad F| and the corner-leg projection; without it those parts fall back
    to v3 behaviour (no cleaning, |grad F| = 1)."""
    P = np.asarray(P_head_mm, float); F = np.array(F_mm, float, copy=True)
    idx = np.nonzero(in_boxes(P))[0]
    if base_fn is not None and "groove" in parts:
        for S in N3.SIDES.values():
            if getattr(S, "_leg_base", None) != id(base_fn):
                S.project_leg(base_fn)
        for S in SIDES.values():
            if getattr(S, "_ag_base", None) != id(base_fn):
                S.project_path(base_fn)
    for a0 in range(0, len(idx), chunk):
        ii = idx[a0:a0 + chunk]; Q = P[ii]; f0 = F[ii].copy()
        od = outline_dist(Q); near = np.abs(f0) < 1.5; zl = (od < CLEAN_ZONE[1]) & near
        gn = np.ones(len(Q))
        if base_fn is not None:
            if zl.any():
                dl, gl = clean_and_grad(Q[zl], base_fn)
                if "clean" in parts:
                    f0[zl] = f0[zl] + ss((CLEAN_ZONE[1] - od[zl]) / (CLEAN_ZONE[1] - CLEAN_ZONE[0])) * dl
                gn[zl] = gl
            mg = (~zl) & near & (median_groove_depth(Q) > 0)
            if mg.any():
                gn[mg] = grad_norm(Q[mg], base_fn)
        g = f0.copy()
        for S3 in N3.SIDES.values():
            if "plug" in parts:                                   # v3 rule (no smin halo on the corner leg)
                kp = K_PLUG * ss(seg_dist(Q, S3.tail_tip, S3.corner)[0] / 1.0)
                g = smin_k(g, S3.plug(Q), kp)
            if "ala" in parts:
                g = g - S3.ala(Q)
            if "groove" in parts:                                 # v3 groove (D2 PASS on v3) or the v3b surface groove, the deeper
                gv = S3.groove(Q); ga = SIDES[S3.sd].alar_groove(Q) * gn
                g = g + np.maximum(gv, ga)
        if "median" in parts:                                     # bridge the blurred Tripo valley, cut the photo groove
            if base_fn is not None:
                mb = near & (bridge_band(Q)[2] > 0)
                if mb.any():
                    g[mb] = g[mb] + bridge_delta(Q[mb], base_fn)
            g = g + median_groove_depth(Q) * gn
        op = None
        if "cavity" in parts or "slit" in parts or "cobble" in parts:
            cav = np.minimum(SIDES["R"].cavity(Q), SIDES["L"].cavity(Q)); sl = np.minimum(SIDES["R"].slit_kept(Q), SIDES["L"].slit_kept(Q))
            op = np.minimum(cav, sl)
        if "cavity" in parts:
            g = smax(g, -cav, K_LUM_B)
        if "slit" in parts:
            g = smax(g, -sl, K_SLIT)
        if graft and "graft" in parts:
            w = N3.mask_w(Q); m = w < 1
            if m.any():
                g[m] = w[m] * g[m] + (1 - w[m]) * f0[m]
        if "cobble" in parts:                                     # after the graft: the plates cover the whole planum
            g = g - designed_relief(Q, op) * gn
        F[ii] = g
    return F


CLEAN_ZONE = tuple(PR["CLEAN_ZONE_MM"]["value"])


def contract_probe(grid_mm, slit_grid_mm=None, leather_grid_mm=None):
    sg = grid_mm if slit_grid_mm is None else slit_grid_mm; lg = grid_mm if leather_grid_mm is None else leather_grid_mm
    ok = grid_mm <= NEED_MM + 1e-9 and sg <= NEED_MM_SLIT + 1e-9 and lg <= NEED_MM_LEATHER + 1e-9
    return dict(status="PASS" if ok else "FAIL", grid_mm=grid_mm, slit_band_grid_mm=sg, leather_grid_mm=lg, need_mm=NEED_MM,
                need_slit_mm=NEED_MM_SLIT, need_leather_mm=NEED_MM_LEATHER)


def probe_inputs():
    out = V2.probe_inputs()
    for sd, S in SIDES.items():
        k = S.s >= 0
        out[f"nasal_passage.{sd}"] = {"opening_centre_mm": S.H.tolist(), "n_in": S.n_in.tolist(), "rim_plane_normal_out": S.nrm.tolist(),
                                      "centreline_mm": S.cl[k][::5].tolist(), "centreline_s_mm": S.s[k][::5].tolist(),
                                      "length_mm": round(float(S.L), 2), "d_vest_mm": D_VEST, "ridge_dir": S.ridge_dir[len(S.ridge_dir) // 2].tolist()}
    out["median_groove"] = {k: v.tolist() for k, v in GM.items()}
    out["median_groove_target"] = {k: v.tolist() for k, v in GT.items()}
    out["alar_groove_paths_mm"] = {sd: S.path.tolist() for sd, S in SIDES.items()}
    out["cobble"] = dict(CB)
    return out


def geometry_report():
    from scipy.spatial import cKDTree as _T
    out = {"cobble_mean_mm": COBBLE_MEAN, "region": REGION, "region_boxes": REGION_BOXES}
    for sd, S in SIDES.items():
        k = S.s >= 0; cl = S.cl[k]; rad = np.maximum(S.a[k], S.b[k])
        lo = (cl - rad[:, None]).min(0); hi = (cl + rad[:, None]).max(0)
        o = SIDES["L" if sd == "R" else "R"]; d, _ = _T(o.cl[o.s >= 0]).query(cl)
        out[sd] = {"centreline_length_mm": round(float(S.L), 2), "end_mm": np.round(S.cl[-1], 2).tolist(),
                   "tube_bbox_mm": [np.round(lo, 2).tolist(), np.round(hi, 2).tolist()],
                   "septum_min_gap_mm": round(float((d - rad - np.maximum(o.a[o.s >= 0], o.b[o.s >= 0]).max()).min()), 2),
                   "cleft_targets_s_mm": PR["CLEFT_S"]["value"], "slit_samples": int(len(S.slit_pts)),
                   "ridge_s_range_mm": [0.5, 6.0]}
    return out
