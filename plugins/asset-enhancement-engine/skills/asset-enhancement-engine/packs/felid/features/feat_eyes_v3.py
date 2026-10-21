"""EYES v3 feature (felid pack, case cat1, cat v3) - builder 'feat-eyes-v3', 2026-10-18. feat_eyes.py (v2) is IMPORTED
and left unchanged; every v2 value not overridden here stands. Spec: spec_eyes_v3.json.

WHAT CHANGES (spec_eyes_v3 phase2_eye_fixes)
  * TUNNEL v3: the old skin over the opening is cut by a PRISM seen along the eye axis, not by v2's radial cone:
      tunnel = max(Ma - TUNNEL_OFF_PL, -h - TUNNEL_BACK, h - (H + TUNNEL_TOP))
    Ma = PLANAR margin distance (p and the margin polygon, both projected along n onto the plane normal to n, + outside).
    v2 measured M along the RADIAL projection from Cs, so periocular skin standing 3-5 mm above the globe projected
    INSIDE the margin and was deleted (a cone widening with height = the goggle moat). The lid and socket keep v2's
    radial M (their walls rise along the globe normal).
  * The RESOLUTION CONTRACT (A20) is DECLARED here: REGION, NEED_MM (0.15 everywhere in REGION), NEED_MM_LID_BAND (0.10
    in the lid band |M| < 2.5 mm, h < 3 mm), lid_band(P) and opening_sdf(P) (the intended air fill_voids must never
    seal: the globe cavity + socket GAP + the aperture prism).
  * The EYE is separate CLOSED objects per side (never unioned with the skin; the whole stack rotates about Cs):
      cornea (genus 0: anterior r 8.82 = the v2 globe surface, posterior r 8.24 concentric, limbal rim),
      sclera (genus 0 thick shell: outer = the v2 globe surface from the limbus back, inner r_in, limbal rim),
      iris (genus 1: the PUPIL is its intended hole; front, back, pupil wall, root wall on the sclera inner surface),
      lens (genus 0: anterior r 7.0, posterior r 6.0, thickness 7.17).
    Every face carries an optical INTERFACE tag (spec materials_cycles: normal to the lower-index side, IOR = ratio),
    so a closed solid gives Cycles the nested-dielectric stack without coincident open shells.
  * The UNSEEN SIDE (the person's direction, NOTES_v3 09:45) is the CLASS model: everything behind the cornea comes
    from cited cat ocular biometry, never a flat disc painted on the cornea.

API
  edit(P_head_mm, F_mm) -> F_mm ; REGION ; NEED_MM ; NEED_MM_LID_BAND ; lid_band(P, side) ; opening_sdf(P)
  margin_dist_planar(P, side) ; eye_parts_v3(P, side)
  build_parts(side) -> {part: dict(v_head, f, tag, ...)} ; save_parts() -> tripo_rebuild/layers/eye_v3_<side>_<part>.npz
  probes: probe_parts(parts, side) (closed/genus/orientation, G1-G7), skin probes F1 F2 F6 tunnel_cone, v2 probes kept.
usage (run from tripo_rebuild):  python <this> parts | preview [L|R|LR] [r] | probe
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feat_eyes as V2  # noqa: E402  (Phase 2, unchanged)

TR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "tripo_rebuild"))
LAYERS = os.path.join(TR, "layers")
SPEC3 = json.load(open(os.path.join(HERE, "spec_eyes_v3.json")))
P_ = dict(V2.P_)
EYES = V2.EYES
REGION = V2.REGION                      # head-frame mm boxes per side (unchanged: the prism lies inside v2's box)

# ------------------------------------------------------------------ the resolution contract (A20), declared
GRID_CAP_MM = 0.15
NEED_MM = 0.15            # lid edge round EDGE_R 0.45 mm -> 3 voxels across (jagged at 0.5 mm, V3_BRIEF)
NEED_MM_LID_BAND = 0.10   # rim smoothness probe F2 (rms <= 0.03 mm) and the 0.45 mm round at 4.5 voxels
RESOLUTION = {"region_mm": NEED_MM, "lid_band_mm": NEED_MM_LID_BAND, "cap_mm": GRID_CAP_MM,
              "lid_band": "|M| < 2.5 mm and h < 3 mm (radial M, globe distance h)",
              "socket_gap": "GAP 0.05 mm is a HARD max carve (air by construction), not a grid-resolved gap",
              "source": "NOTES_v3 A20; spec_eyes_v3 probes F2, F6"}

V3_PARAMS = {
    "TUNNEL_OFF_PL": (1.0, "v2 builder's 1 mm offset (cut wall inside the lid), now PLANAR", "estimate"),
    "TUNNEL_TOP": (0.5, "spec_eyes_v3 fix: the prism stops 0.5 mm above the lid top H (Tripo lid wall top 1.6-2.3 mm)", "derived"),
    "CCT": (0.578, "cited: Gilger 1993, 35 cats (PMID 8430933)", "cited"),
    "ACD": (4.66, "cited: Konrade 2012, 98 cats: anterior chamber length (apex -> anterior lens)", "cited"),
    "LENS_T": (7.17, "derived: 19.75 - 4.66 - 7.92 (Konrade 2012)", "derived"),
    "LENS_RA": (7.0, "spec_eyes_v3 estimate", "estimate"),
    "LENS_RP": (6.0, "spec_eyes_v3 estimate", "estimate"),
    "IRIS_ROOT_R": (8.0, "spec_eyes_v3 estimate (root diameter 16.0)", "estimate"),
    "IRIS_T": ((0.2, 0.375, 0.3), "spec_eyes_v3 estimate: margin / mid / root", "estimate"),
    "IRIS_BOW": (0.15, "forward convexity of the iris cone; estimate", "estimate"),
    "IRIS_LENS_GAP": (0.02, "pupil margin rests on the anterior lens capsule (G5 <= 0.05)", "derived"),
    "PUPIL_H": (8.3, "spec_eyes_v3 photo_reading.pupil.true_mm (derived, R3 fits it)", "derived/estimate"),
    "PUPIL_W": (4.8, "same", "derived/estimate"),
    "PUPIL_PINCH": (0.3, "spec_eyes_v3 pupil shape_model (photo quarter-height widths)", "estimate"),
    "H_FINE": (0.10, "edge length on the cornea, pupil edge, iris (spec geometry_build.resolution)", "spec"),
    "H_COARSE": (0.20, "edge length elsewhere", "spec"),
}
Q_ = {k: v[0] for k, v in V3_PARAMS.items()}


import os as _os_mg, sys as _sys_mg  # noqa: E402  (build A1: the engine's one closest point, normals, cotangent Laplacian)
_MG_DIR = _os_mg.path.normpath(_os_mg.path.join(_os_mg.path.dirname(_os_mg.path.abspath(__file__)), '../../../tools'))
if _MG_DIR not in _sys_mg.path:
    _sys_mg.path.append(_MG_DIR)
import mesh_geom as _MG  # noqa: E402


def _unit(x):
    x = np.asarray(x, float); return x / np.linalg.norm(x)


def _plane(E, P):
    q = np.atleast_2d(P) - E["Cs"]; return np.c_[q @ E["u"], q @ E["v"]]


def _radial_to_globe(E, side, W, lo=4.0, hi=16.0, it=48):
    """distance along unit directions W from Cs to the v2 globe surface G = 0 (the globe is star-shaped about Cs)"""
    lo = np.full(len(W), lo); hi = np.full(len(W), hi)
    for _ in range(it):
        mid = 0.5 * (lo + hi); g = V2.globe_field(E["Cs"] + mid[:, None] * W, side) < 0
        lo = np.where(g, mid, lo); hi = np.where(g, hi, mid)
    return 0.5 * (lo + hi)


for _sd, _E in EYES.items():   # the margin polygon ON the globe surface, then projected along n (planar polygon)
    _W = _E["poly_sph"] - _E["Cs"]; _W /= np.linalg.norm(_W, axis=1)[:, None]
    _E["poly_globe"] = _E["Cs"] + _radial_to_globe(_E, _sd, _W)[:, None] * _W
    _E["poly_pl"] = _plane(_E, _E["poly_globe"])


def margin_dist_planar(P, side, chunk=100000):
    """Ma(p): signed planar distance (mm) from p to the margin polygon, both projected along n; + outside the opening"""
    E = EYES[side]; X = _plane(E, P); A = E["poly_pl"]; B = np.roll(A, -1, axis=0); AB = B - A; L2 = (AB ** 2).sum(1)
    d = np.empty(len(X))
    for s in range(0, len(X), chunk):
        Y = X[s:s + chunk, None, :] - A[None]; t = np.clip((Y * AB[None]).sum(2) / L2[None], 0, 1)
        d[s:s + chunk] = np.sqrt(((Y - t[:, :, None] * AB[None]) ** 2).sum(2)).min(1)
    return np.where(V2._pip(X, A), -d, d)


def eye_parts_v3(P, side, tunnel="v3", **kw):
    pr = V2.eye_parts(P, side, **kw); h = pr["h"]
    if tunnel == "v3":
        Ma = margin_dist_planar(P, side); pr["Ma"] = Ma
        pr["tunnel"] = np.maximum.reduce([Ma - Q_["TUNNEL_OFF_PL"], -h - P_["TUNNEL_BACK"], h - (P_["H"] + Q_["TUNNEL_TOP"])])
    return pr


def edit_side(P, F, side, tunnel="v3", **kw):
    pr = eye_parts_v3(P, side, tunnel=tunnel, **kw)
    S1 = np.maximum(F, -pr["tunnel"])
    S3 = V2.smin(S1, pr["lid"], P_["LID_TO_SKIN_K"])
    S3 = V2.smin(S3, pr["tel"], P_["TEL_K"])
    return np.maximum(S3, pr["socket"])                    # socket LAST (v2 B2), hard max


def edit(P_head_mm, F_mm, chunk=200000, tunnel="v3", **kw):
    """the skin-field edit (mm, negative inside). Only points inside REGION change. tunnel='v2' reproduces feat_eyes."""
    P = np.asarray(P_head_mm, float); F = np.array(F_mm, float, copy=True)
    for sd in ("L", "R"):
        lo, hi = EYES[sd]["box"]; idx = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
        for s in range(0, len(idx), chunk):
            ii = idx[s:s + chunk]; F[ii] = edit_side(P[ii], F[ii], sd, tunnel=tunnel, **kw)
    return F


def lid_band(P, side):
    h = V2.globe_field(P, side); M = V2.margin_dist(P, side); return (np.abs(M) < 2.5) & (h < 3.0)


def opening_sdf(P):
    """intended air (mm, < 0 inside): the globe cavity + socket GAP (swept globe) and the aperture prism. fill_voids must
    never fill a void touching it (NOTES_v3 A20: the eye fornix)."""
    P = np.asarray(P, float); out = np.full(len(P), np.inf)
    for sd in ("L", "R"):
        lo, hi = EYES[sd]["box"]; b = np.all((P >= lo) & (P <= hi), axis=1)
        if b.any():
            pr = eye_parts_v3(P[b], sd); out[b] = np.minimum(out[b], np.minimum(-pr["socket"], pr["tunnel"]))
    return out


# ------------------------------------------------------------------ eye optics: closed solids (head-frame mm)
def _zip(A, B):
    """stitch closed ring A (indices, azimuth 2 pi j / NA) to ring B; consistent orientation along a ring sequence"""
    na, nb = len(A), len(B); aa = np.r_[np.arange(na) / na, 1.0]; bb = np.r_[np.arange(nb) / nb, 1.0]
    Ae = np.r_[A, A[:1]]; Be = np.r_[B, B[:1]]; i = j = 0; T = []
    while i < na or j < nb:
        if i < na and (j == nb or aa[i + 1] < bb[j + 1]):
            T.append((Ae[i], Ae[i + 1], Be[j])); i += 1
        else:
            T.append((Ae[i], Be[j + 1], Be[j])); j += 1
    T = np.array(T, np.int64)
    return T[(T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 0] != T[:, 2])]


class _Solid:
    def __init__(self):
        self.V = []; self.n = 0; self.rings = []; self.uv = []

    def ring(self, rho, z, frame, N, uvv=None):
        """a ring: rho (scalar or (N,)), z (scalar or (N,)) in the eye frame; N = 1 is a pole"""
        Cs, n, u, v = frame; ph = 2 * np.pi * np.arange(N) / N
        rho = np.broadcast_to(np.asarray(rho, float), (N,)); z = np.broadcast_to(np.asarray(z, float), (N,))
        P = Cs + z[:, None] * n + (rho * np.cos(ph))[:, None] * u + (rho * np.sin(ph))[:, None] * v
        idx = np.arange(self.n, self.n + N); self.V.append(P); self.n += N
        self.uv.append(np.c_[ph / (2 * np.pi), np.full(N, -1.0 if uvv is None else uvv)])
        self.rings.append(idx); return idx

    def strip_all(self, tags, cyclic=False):
        F, Tg = [], []
        m = len(self.rings) if cyclic else len(self.rings) - 1
        for k in range(m):
            t = _zip(self.rings[k], self.rings[(k + 1) % len(self.rings)]); F.append(t); Tg.append(np.full(len(t), tags[k], np.int8))
        V = np.vstack(self.V); F = np.vstack(F); Tg = np.concatenate(Tg)
        vol = np.einsum("ij,ij->i", V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6
        if vol < 0:
            F = F[:, ::-1]
        return V, F, Tg, np.vstack(self.uv)


def _arc_rings(rho, z, h, n_end=None):
    """resample a meridian polyline (rho, z) at arc spacing <= h; returns rho_k, z_k incl. both ends"""
    s = np.r_[0, np.cumsum(np.hypot(np.diff(rho), np.diff(z)))]; K = max(1, int(np.ceil(s[-1] / h)))
    sk = np.linspace(0, s[-1], K + 1); return np.interp(sk, s, rho), np.interp(sk, s, z)


def _nring(rho, h, nb=None):
    return 1 if rho < 1e-9 else max(6, int(np.ceil(2 * np.pi * rho / h)))


def pupil_radius(ph, H=None, W=None, pinch=None):
    """vesica pupil (spec optics.pupil.shape_model) as a polar radius r(phi), phi from u (lateral) toward v (up)"""
    H = Q_["PUPIL_H"] if H is None else H; W = Q_["PUPIL_W"] if W is None else W; pinch = Q_["PUPIL_PINCH"] if pinch is None else pinch
    lo = np.zeros(len(ph)); hi = np.full(len(ph), H)
    for _ in range(50):
        r = 0.5 * (lo + hi); x = np.abs(r * np.cos(ph)); y = r * np.sin(ph); s = np.clip(np.abs(2 * y / H), 0, 1)
        half = (W / 2) * np.sqrt(np.clip(1 - s ** 2, 0, 1)) * (1 - pinch * s ** 2); ins = (x <= half) & (np.abs(2 * y / H) <= 1)
        lo = np.where(ins, r, lo); hi = np.where(ins, hi, r)
    return 0.5 * (lo + hi)


def optics_geom(side):
    E = EYES[side]; rc, dc, apex = V2.cornea_geom(); RS, a = P_["RS"], P_["LIMBUS_R"]; zl = np.sqrt(RS ** 2 - a ** 2)
    rcb = rc - Q_["CCT"]; rho_b = np.sqrt(rcb ** 2 - (zl - dc) ** 2); r_in = np.hypot(rho_b, zl)
    z_la = apex - Q_["ACD"]; c_lf = z_la - Q_["LENS_RA"]; z_lp = z_la - Q_["LENS_T"]; c_lb = z_lp + Q_["LENS_RP"]
    ra, rp = Q_["LENS_RA"], Q_["LENS_RP"]
    lo_, hi_ = 3.0, min(ra, rp) - 1e-6
    for _ in range(60):                                     # lens equator: front and back caps meet
        m = 0.5 * (lo_ + hi_); d = (c_lf + np.sqrt(ra ** 2 - m ** 2)) - (c_lb - np.sqrt(rp ** 2 - m ** 2))
        lo_, hi_ = (m, hi_) if d > 0 else (lo_, m)
    a_eq = 0.5 * (lo_ + hi_)
    return dict(E=E, rc=rc, dc=dc, apex=apex, zl=zl, rcb=rcb, rho_b=rho_b, r_in=r_in, t_sclera_limbus=RS - r_in,
                z_la=z_la, c_lf=c_lf, z_lp=z_lp, c_lb=c_lb, a_eq=a_eq, theta_l=np.arctan2(a, zl))


def _outer_meridian(side, g, n=6001):
    E = g["E"]; th = np.linspace(0, np.pi, n); W = np.cos(th)[:, None] * E["n"] + np.sin(th)[:, None] * E["u"]
    t = _radial_to_globe(E, side, W); return th, t * np.sin(th), t * np.cos(th)


TAGS = {"cornea": ["cornea_front", "limbus_rim", "cornea_back"], "sclera": ["sclera_outer", "limbus_rim", "angle", "fundus"],
        "iris": ["iris_front", "iris_root", "iris_back", "pupil_margin"], "lens": ["lens_front", "lens_back"]}
INTERFACE = {"cornea_front": "air 1.000 | cornea 1.376: normal to AIR, IOR 1.376 (+ tear-film coat 1.337)",
             "cornea_back": "cornea 1.376 | aqueous 1.336: normal to AQUEOUS, IOR 1.0299",
             "lens_front": "aqueous 1.336 | lens 1.42: normal to AQUEOUS, IOR 1.0629",
             "lens_back": "lens 1.42 | vitreous 1.336: normal to VITREOUS, IOR 1.0629",
             "limbus_rim": "opaque: SCLERA shader (hidden; cornea and sclera rims coincide)",
             "sclera_outer": "SCLERA (subsurface, wet coat)", "angle": "opaque dark (ciliary / angle), albedo 0.03 estimate",
             "fundus": "FUNDUS diffuse 0.02 (tapetum off)", "iris_front": "IRIS (IRIS_TEX, bump 0.1 mm)",
             "iris_back": "IRIS_BACK diffuse 0.03", "pupil_margin": "IRIS_BACK diffuse 0.03", "iris_root": "IRIS_BACK diffuse 0.03"}


def build_parts(side, iris_root_r=None, iris_lens_gap=None):
    g = optics_geom(side); E = g["E"]; fr = (E["Cs"], E["n"], E["u"], E["v"]); hf, hc = Q_["H_FINE"], Q_["H_COARSE"]
    NB = int(np.ceil(2 * np.pi * 8.3 / hf / 8) * 8)
    th, mr, mz = _outer_meridian(side, g); kl = np.searchsorted(th, g["theta_l"])
    rho_o = np.r_[mr[:kl], np.interp(g["theta_l"], th, mr)]; z_o = np.r_[mz[:kl], np.interp(g["theta_l"], th, mz)]
    out = {}
    # ---- cornea: front pole -> limbus (outer, G = 0) -> rim -> posterior sphere -> back pole
    S = _Solid(); tags = []
    rk, zk = _arc_rings(rho_o, z_o, hf)
    for i, (r_, z_) in enumerate(zip(rk, zk)):
        S.ring(r_, z_, fr, NB if i == len(rk) - 1 else _nring(r_, hf)); tags.append(0)
    rr = np.linspace(rk[-1], g["rho_b"], max(2, int(np.ceil(np.hypot(rk[-1] - g["rho_b"], zk[-1] - g["zl"]) / hf)) + 1))
    zz = np.linspace(zk[-1], g["zl"], len(rr))
    tags[-1] = 1
    for i in range(1, len(rr)):
        S.ring(rr[i], zz[i], fr, NB); tags.append(1 if i < len(rr) - 1 else 2)
    psi_b = np.arccos((g["zl"] - g["dc"]) / g["rcb"]); ps = np.linspace(psi_b, 0, 4000)
    rk2, zk2 = _arc_rings(g["rcb"] * np.sin(ps), g["dc"] + g["rcb"] * np.cos(ps), hf)
    for i in range(1, len(rk2)):
        S.ring(rk2[i], zk2[i], fr, _nring(rk2[i], hf)); tags.append(2)
    V, F, T, _ = S.strip_all(tags[:-1]); out["cornea"] = dict(v_head=V, f=F, tag=T)
    # ---- sclera: outer back pole -> limbus (outer) -> rim -> inner sphere r_in -> inner back pole
    S = _Solid(); tags = []
    ths = th[kl:]; rho_s = np.r_[np.interp(g["theta_l"], th, mr), mr[kl:]]; z_s = np.r_[np.interp(g["theta_l"], th, mz), mz[kl:]]
    rk, zk = _arc_rings(rho_s[::-1], z_s[::-1], hc)          # back pole -> limbus
    rk[0] = 0.0
    for i, (r_, z_) in enumerate(zip(rk, zk)):
        S.ring(r_, z_, fr, NB if i == len(rk) - 1 else _nring(r_, hc)); tags.append(0)
    tags[-1] = 1
    for i in range(1, len(rr)):
        S.ring(rr[i], zz[i], fr, NB); tags.append(1 if i < len(rr) - 1 else 2)
    th_in = np.arccos(g["zl"] / g["r_in"]); ts = np.linspace(th_in, np.pi, 6000)
    rk3, zk3 = _arc_rings(g["r_in"] * np.sin(ts), g["r_in"] * np.cos(ts), hc); rk3[-1] = 0.0
    root_r = Q_["IRIS_ROOT_R"] if iris_root_r is None else iris_root_r
    z_root = np.sqrt(g["r_in"] ** 2 - Q_["IRIS_ROOT_R"] ** 2)
    for i in range(1, len(rk3)):
        S.ring(rk3[i], zk3[i], fr, _nring(rk3[i], hc) if i > 1 else max(_nring(rk3[i], hc), 64)); tags.append(2 if zk3[i] > z_root else 3)
    tags[len(rk) - 1 + len(rr) - 1] = 2
    V, F, T, _ = S.strip_all(tags[:-1]); out["sclera"] = dict(v_head=V, f=F, tag=T)
    # ---- lens: anterior pole -> equator -> posterior pole
    S = _Solid(); tags = []; ra, rp, a_eq = Q_["LENS_RA"], Q_["LENS_RP"], g["a_eq"]
    al = np.linspace(0, np.arcsin(a_eq / ra), 3000); rk, zk = _arc_rings(ra * np.sin(al), g["c_lf"] + ra * np.cos(al), hf)
    NE = _nring(a_eq, hf)
    for i, (r_, z_) in enumerate(zip(rk, zk)):
        S.ring(r_, z_, fr, NE if i == len(rk) - 1 else _nring(r_, hf)); tags.append(0)
    tags[-1] = 1
    al2 = np.linspace(np.arcsin(a_eq / rp), 0, 3000); rk4, zk4 = _arc_rings(rp * np.sin(al2), g["c_lb"] - rp * np.cos(al2), hf); rk4[-1] = 0.0
    for i in range(1, len(rk4)):
        S.ring(rk4[i], zk4[i], fr, _nring(rk4[i], hf)); tags.append(1)
    V, F, T, _ = S.strip_all(tags[:-1]); out["lens"] = dict(v_head=V, f=F, tag=T)
    # ---- iris: torus; ring sequence front (margin -> root), root wall, back (root -> margin), pupil wall (cyclic)
    NI = 720; ph = 2 * np.pi * np.arange(NI) / NI; rpup = pupil_radius(ph); gap = Q_["IRIS_LENS_GAP"] if iris_lens_gap is None else iris_lens_gap
    zlens = lambda r: g["c_lf"] + np.sqrt(np.maximum(ra ** 2 - r ** 2, 0))
    t0, t1, t2 = Q_["IRIS_T"]; K = 60; s = np.linspace(0, 1, K + 1)
    z_m = zlens(rpup) + gap; z_rb = np.sqrt(g["r_in"] ** 2 - Q_["IRIS_ROOT_R"] ** 2); gp0 = Q_["IRIS_ROOT_R"] - root_r
    S = _Solid(); tags = []
    tt = lambda s_: t0 + (4 * t1 - 3 * t0 - t2) * s_ + (2 * t0 + 2 * t2 - 4 * t1) * s_ ** 2   # quadratic through t0, t1, t2
    back = []
    for s_ in s:
        rb = rpup + s_ * (root_r - rpup); zb = (1 - s_) * z_m + s_ * z_rb + Q_["IRIS_BOW"] * np.sin(np.pi * s_)
        inl = rb < a_eq; zb = np.where(inl, np.maximum(zb, zlens(np.minimum(rb, a_eq)) + gap), zb); back.append((rb, zb))
    front = []
    for k, s_ in enumerate(s):
        rb, zb = back[k]; zf = zb + tt(s_)
        cap = np.sqrt(np.maximum(g["r_in"] ** 2 - zf ** 2, 0))           # never inside the sclera solid
        front.append((cap if k == K else np.minimum(rb, cap), zf))
    back = [(np.minimum(rb, np.sqrt(np.maximum(g["r_in"] ** 2 - zb ** 2, 0))), zb) for rb, zb in back]
    if iris_root_r is not None:                              # planted root gap: the root wall pulled off the sclera
        gp = Q_["IRIS_ROOT_R"] - root_r
        front[-1] = (front[-1][0] - gp, front[-1][1])
    for k in range(K + 1):
        S.ring(front[k][0], front[k][1], fr, NI, uvv=s[k]); tags.append(0 if k < K else 1)
    for w_ in (1 / 3, 2 / 3):                                # root wall on the sclera inner sphere
        z_ = (1 - w_) * front[K][1] + w_ * back[K][1]; S.ring(np.sqrt(np.maximum(g["r_in"] ** 2 - z_ ** 2, 0)) - gp0, z_, fr, NI, uvv=1.0); tags.append(1)
    for k in range(K, -1, -1):
        S.ring(back[k][0], back[k][1], fr, NI, uvv=s[k]); tags.append(2 if k > 0 else 3)
    S.ring(back[0][0], 0.5 * (back[0][1] + front[0][1]), fr, NI, uvv=0.0); tags.append(3)   # pupil wall mid ring
    V, F, T, UV = S.strip_all(tags, cyclic=True); out["iris"] = dict(v_head=V, f=F, tag=T, uv=UV)
    out["_geom"] = {k: (float(v) if np.ndim(v) == 0 and not isinstance(v, dict) else None) for k, v in g.items() if k != "E"}
    out["_geom"].update(z_root_back=float(z_rb), iris_root_r=float(root_r), pupil_ring_r_range=[float(rpup.min()), float(rpup.max())],
                        NB=NB, NI=NI)
    return out


def head_to_world(Vh):
    import partition as PT
    return PT.HC + (np.asarray(Vh) / 1000.0) @ PT.HR.T


def save_parts(sides=("L", "R")):
    files = []
    for sd in sides:
        parts = build_parts(sd); Cs_w = head_to_world(EYES[sd]["Cs"][None])[0]
        for name in ("cornea", "sclera", "iris", "lens"):
            p = parts[name]; fn = os.path.join(LAYERS, f"eye_v3_{sd}_{name}.npz")
            extra = {"uv": p["uv"].astype(np.float32)} if "uv" in p else {}
            np.savez_compressed(fn, v=head_to_world(p["v_head"]), f=p["f"], face_tag=p["tag"], tag_names=np.array(TAGS[name]),
                                v_head_mm=p["v_head"], pivot_world=Cs_w, object_name=f"Eye_{sd}_{name}",
                                interfaces=json.dumps({t: INTERFACE[t] for t in TAGS[name]}),
                                note=f"feat_eyes_v3 {name} ({sd}): CLOSED solid, outward normals, world metres; parent all eye parts "
                                     f"to one empty at pivot_world (the eye bone). Per-face interface tags: tag_names[face_tag].", **extra)
            files.append(fn)
    return files


# ------------------------------------------------------------------ ray tracing (numba, brute force; probes only)
def _tracer():
    from numba import njit, prange

    @njit(parallel=True, cache=False)
    def trace(O, D, T0, E1, E2, out_t, out_id):
        nr, mh = out_t.shape
        for r in prange(nr):
            c = 0
            for k in range(T0.shape[0]):
                px = D[r, 1] * E2[k, 2] - D[r, 2] * E2[k, 1]; py = D[r, 2] * E2[k, 0] - D[r, 0] * E2[k, 2]; pz = D[r, 0] * E2[k, 1] - D[r, 1] * E2[k, 0]
                det = E1[k, 0] * px + E1[k, 1] * py + E1[k, 2] * pz
                if abs(det) < 1e-14:
                    continue
                inv = 1.0 / det; sx = O[r, 0] - T0[k, 0]; sy = O[r, 1] - T0[k, 1]; sz = O[r, 2] - T0[k, 2]
                u = (sx * px + sy * py + sz * pz) * inv
                if u < 0.0 or u > 1.0:
                    continue
                qx = sy * E1[k, 2] - sz * E1[k, 1]; qy = sz * E1[k, 0] - sx * E1[k, 2]; qz = sx * E1[k, 1] - sy * E1[k, 0]
                v = (D[r, 0] * qx + D[r, 1] * qy + D[r, 2] * qz) * inv
                if v < 0.0 or u + v > 1.0:
                    continue
                t = (E2[k, 0] * qx + E2[k, 1] * qy + E2[k, 2] * qz) * inv
                if t > 1e-9 and c < mh:
                    out_t[r, c] = t; out_id[r, c] = k; c += 1
    return trace


_TR = {}


def raycast(O, D, V, F, maxhits=24, chunk=512):
    if "f" not in _TR:
        _TR["f"] = _tracer()
    T0 = V[F[:, 0]].copy(); E1 = V[F[:, 1]] - T0; E2 = V[F[:, 2]] - T0
    ts = np.full((len(O), maxhits), np.inf); ids = np.full((len(O), maxhits), -1, np.int64)
    for s in range(0, len(O), chunk):
        t_ = np.full((min(chunk, len(O) - s), maxhits), np.inf); i_ = np.full(t_.shape, -1, np.int64)
        _TR["f"](np.ascontiguousarray(O[s:s + chunk]), np.ascontiguousarray(D[s:s + chunk]), T0, E1, E2, t_, i_)
        ts[s:s + chunk], ids[s:s + chunk] = t_, i_
    o = np.argsort(ts, axis=1); return np.take_along_axis(ts, o, 1), np.take_along_axis(ids, o, 1)


def _stack(parts, names):
    V, F, P, T, off = [], [], [], [], 0
    for pi, nm in enumerate(names):
        p = parts[nm]; V.append(p["v_head"]); F.append(p["f"] + off); P.append(np.full(len(p["f"]), pi)); T.append(p["tag"]); off += len(p["v_head"])
    return np.vstack(V), np.vstack(F), np.concatenate(P), np.concatenate(T)


# ------------------------------------------------------------------ part probes (G-series)
def probe_closed(V, F, genus_expected):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    e = np.r_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]; ue, cnt = np.unique(np.sort(e, 1), axis=0, return_counts=True)
    de = np.unique(e, axis=0); used = np.unique(F)
    A = coo_matrix((np.ones(len(ue)), (ue[:, 0], ue[:, 1])), shape=(len(V), len(V)))
    nc = connected_components(A, directed=False)[0] - (len(V) - len(used)); chi = len(used) - len(ue) + len(F)
    vol = float(np.einsum("ij,ij->i", V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6)
    area = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1) / 2
    el = np.linalg.norm(V[ue[:, 0]] - V[ue[:, 1]], axis=1)
    genus = (2 - chi) / 2; ok = bool((cnt == 2).all() and len(de) == len(e) and nc == 1 and genus == genus_expected and vol > 0 and area.min() > 0)
    return dict(status="PASS" if ok else "FAIL", components=int(nc), euler=int(chi), genus=float(genus), genus_expected=genus_expected,
                edges_not_2=int((cnt != 2).sum()), orientation_consistent=bool(len(de) == len(e)), volume_mm3=round(vol, 2),
                min_tri_area_mm2=float(area.min()), edge_mm_p50_max=[round(float(np.median(el)), 4), round(float(el.max()), 4)])


def _hits_along(parts, names, side, O, D):
    V, F, Pi, Tg = _stack(parts, names); t, ids = raycast(O, D, V, F)
    res = []
    for r in range(len(O)):
        k = np.isfinite(t[r]); hh = []
        for j in np.nonzero(k)[0]:
            x = (float(t[r][j]), names[Pi[ids[r][j]]], TAGS[names[Pi[ids[r][j]]]][Tg[ids[r][j]]])
            if not hh or abs(x[0] - hh[-1][0]) > 1e-6 or x[2] != hh[-1][2]:       # an edge / vertex hit counts once
                hh.append(x)
        res.append(hh)
    return res


def probe_parts(parts, side, label="v3"):
    E = EYES[side]; Cs, n, u, v = E["Cs"], E["n"], E["u"], E["v"]; out = {"label": label}
    names = [k for k in ("cornea", "sclera", "iris", "lens", "globe") if k in parts]
    exp_genus = {"cornea": 0, "sclera": 0, "lens": 0, "iris": 1, "globe": 0}
    out["closed"] = {k: probe_closed(parts[k]["v_head"], parts[k]["f"], exp_genus[k]) for k in names}
    # G7 outer surface = v2 globe_field
    outer = []
    for k, tg in (("cornea", 0), ("sclera", 0), ("globe", None)):
        if k in parts:
            p = parts[k]; vi = np.unique(p["f"][p["tag"] == tg]) if tg is not None else np.arange(len(p["v_head"]))
            outer.append(p["v_head"][vi])
    Vo = np.vstack(outer); Go = np.abs(V2.globe_field(Vo, side))
    out["G7_outer_surface"] = dict(status="PASS" if Go.max() <= 0.02 else "FAIL", max_abs_G_mm=round(float(Go.max()), 4), expected_mm="<= 0.02")
    # G1 cornea shape on the outer vertices
    q = Vo - Cs; zq = q @ n; fit = []
    for t_, o_ in ((u, v), (v, u)):
        k = (np.abs(q @ o_) < 0.06) & (np.abs(q @ t_) <= 4.0) & (zq > 0)
        x, y = q[k] @ t_, zq[k]; sol = np.linalg.lstsq(np.c_[2 * x, 2 * y, np.ones(len(x))], x ** 2 + y ** 2, rcond=None)[0]
        fit.append(round(float(np.sqrt(sol[2] + sol[0] ** 2 + sol[1] ** 2)), 3))
    apex = Cs + zq.max() * n; axial = float(zq.max() - zq.min())
    out["G1_cornea"] = dict(status="PASS" if all(abs(r - 8.82) <= 0.5 for r in fit) and np.linalg.norm(apex - E["apex_spec"]) <= 0.5
                            and abs(axial - 19.75) <= 0.3 else "FAIL", corneal_radius_fit_mm=fit,
                            apex_vs_spec_mm=round(float(np.linalg.norm(apex - E["apex_spec"])), 3), axial_length_mm=round(axial, 3))
    # axial and off-axis rays from the front
    offs = [0.013, 3.0, 6.0]; O = np.array([Cs + 14.0 * n + o * u + 0.007 * v for o in offs]); D = np.tile(-n, (3, 1))
    H = _hits_along(parts, names, side, O, D)
    row = []
    for o, h in zip(offs, H):
        z0 = h[0][0] if h else None
        cb = next((x[0] for x in h if x[2] == "cornea_back"), None); lf = next((x[0] for x in h if x[2] == "lens_front"), None)
        lb = next((x[0] for x in h if x[2] == "lens_back"), None)
        icb = next((j for j, x in enumerate(h) if x[2] == "cornea_back"), None)
        nxt = h[icb + 1][0] if icb is not None and icb + 1 < len(h) else None
        row.append(dict(offset_mm=o, sequence=[x[1] + ":" + x[2] for x in h][:8], cct_along_n=None if cb is None else round(cb - z0, 4),
                        apex_to_lens_front=None if lf is None else round(lf - z0, 4),
                        apex_to_first_behind_cornea=None if nxt is None else round(nxt - z0, 4), lens_thickness=None if (lf is None or lb is None) else round(lb - lf, 4)))
    out["axial_rays"] = row
    # G2 thickness along the local normal (nearest back vertex from front vertices at the stations)
    if "cornea" in parts:
        from scipy.spatial import cKDTree
        p = parts["cornea"]; fv = p["v_head"][np.unique(p["f"][p["tag"] == 0])]; bv = p["v_head"][np.unique(p["f"][p["tag"] == 2])]
        tr = cKDTree(bv); th_ = []
        for o in offs:
            k = np.argmin(np.linalg.norm((fv - Cs) - ((fv - Cs) @ n)[:, None] * n - o * u, axis=1)); th_.append(round(float(tr.query(fv[k])[0]), 4))
        out["G2_cct"] = dict(status="PASS" if all(abs(x - Q_["CCT"]) <= 0.06 for x in th_) else "FAIL", normal_thickness_mm=th_,
                             expected_mm=Q_["CCT"], tol_mm=0.06,
                             note="measured along the local normal; along n at 6 mm off-axis a correct concentric cornea reads 0.817 (spec G2 wording corrected)")
    else:
        out["G2_cct"] = dict(status="FAIL", why="no posterior corneal surface (single-surface globe): no second hit", sequence=row[0]["sequence"])
    a = row[0]["apex_to_first_behind_cornea"]; out["G3_anterior_chamber"] = dict(status="PASS" if a is not None and abs(a - Q_["ACD"]) <= 0.3 else "FAIL",
                                                                          apex_to_first_surface_behind_cornea_mm=a, expected_mm=Q_["ACD"], tol_mm=0.3)
    lt = row[0]["lens_thickness"]; out["G4_lens"] = dict(status="PASS" if lt is not None and abs(lt - Q_["LENS_T"]) <= 0.4 else "FAIL",
                                                         thickness_mm=lt, expected_mm=Q_["LENS_T"], tol_mm=0.4)
    if "iris" in parts and "lens" in parts:
        p = parts["iris"]; q = p["v_head"] - Cs; rho = np.linalg.norm(q - (q @ n)[:, None] * n, axis=1)
        root_b = p["v_head"][np.unique(p["f"][p["tag"] == 1])]; rr_ = np.linalg.norm((root_b - Cs) - ((root_b - Cs) @ n)[:, None] * n, axis=1)
        g = optics_geom(side); marg = p["v_head"][np.unique(p["f"][p["tag"] == 3])]
        dlens = np.abs(np.linalg.norm(marg - (Cs + g["c_lf"] * n), axis=1) - Q_["LENS_RA"])
        fr_ = p["v_head"][np.unique(p["f"][p["tag"] == 0])]; depth_f = (Cs + g["apex"] * n - fr_) @ n
        root_on_sclera = np.abs(np.linalg.norm(root_b - Cs, axis=1) - g["r_in"])
        ok = abs(2 * rr_.max() - 16.0) <= 0.5 and dlens.min() <= 0.05 and depth_f.min() >= 4.0 and root_on_sclera.max() <= 0.01
        out["G5_iris"] = dict(status="PASS" if ok else "FAIL", root_diameter_mm=round(float(2 * rr_.max()), 3), margin_to_lens_gap_min_max_mm=[round(float(dlens.min()), 4), round(float(dlens.max()), 4)],
                              iris_front_min_depth_behind_apex_mm=round(float(depth_f.min()), 3), root_off_sclera_inner_max_mm=round(float(root_on_sclera.max()), 4))
    else:
        out["G5_iris"] = dict(status="FAIL", why="no iris / lens object")
    out["G6_sealed"] = probe_sealed(parts, side)
    out["status"] = "PASS" if all(v_.get("status") == "PASS" for k_, v_ in out.items() if k_.startswith("G")) and all(c["status"] == "PASS" for c in out["closed"].values()) else "FAIL"
    return out


def probe_sealed(parts, side, nrays=2000, n_target=2000, cone_deg=30.0, seed=7):
    """G6: rays from in front of the eye within +-30 deg of the axis, aimed into the opening. A ray that enters the
    cornea front must stop at an opaque surface reached through the aqueous (iris, angle) or pass the LENS before the
    fundus. LEAK = it reaches the fundus without crossing the lens, or leaves the eye."""
    names = [k for k in ("cornea", "sclera", "iris", "lens", "globe") if k in parts]
    if not all(k in parts for k in ("cornea", "iris", "lens")):
        return dict(status="FAIL", why="no cornea / iris / lens solids: optics cannot be sealed or traced", parts=names)
    E = EYES[side]; Cs, n, u, v = E["Cs"], E["n"], E["u"], E["v"]; rng = np.random.default_rng(seed)
    a = rng.uniform(0, 2 * np.pi, nrays); rr = 8.3 * np.sqrt(rng.uniform(0, 1, nrays))
    tilt = np.radians(cone_deg) * np.sqrt(rng.uniform(0, 1, nrays)); az = rng.uniform(0, 2 * np.pi, nrays)
    D = -(np.cos(tilt)[:, None] * n + np.sin(tilt)[:, None] * (np.cos(az)[:, None] * u + np.sin(az)[:, None] * v))
    tgt = Cs + 9.0 * n + (rr * np.cos(a))[:, None] * u + (rr * np.sin(a))[:, None] * v; O = tgt - 6.0 * D
    # TARGETED rays through the iris-root / angle annulus (where a root gap would be), outward-going, 12-30 deg off axis
    g = optics_geom(side); a2 = rng.uniform(0, 2 * np.pi, n_target); z2 = rng.uniform(3.8, 4.6, n_target)
    r2 = np.sqrt(np.maximum(g["r_in"] ** 2 - z2 ** 2, 0)) - rng.uniform(0.0, 0.3, n_target)
    rad = np.cos(a2)[:, None] * u + np.sin(a2)[:, None] * v; T2 = Cs + z2[:, None] * n + r2[:, None] * rad
    tl = np.radians(rng.uniform(12, cone_deg, n_target)); D2 = -(np.cos(tl)[:, None] * n) + np.sin(tl)[:, None] * rad
    O = np.vstack([O, T2 - 14.0 * D2]); D = np.vstack([D, D2])
    H = _hits_along(parts, names, side, O, D); entered = leaks = 0; stops = {}
    opaque = {"iris_front", "iris_back", "iris_root", "pupil_margin", "angle", "fundus", "limbus_rim"}
    for h in H:
        if not h or h[0][2] != "cornea_front":
            continue
        if len(h) > 1 and h[1][2] == "cornea_front":
            continue                                          # grazed the cornea and left: never inside the eye
        entered += 1; through_lens = False; stop = None
        for t_, part, tag in h[1:]:
            if tag == "lens_front":
                through_lens = True
            if tag in opaque:
                stop = tag; break
            if tag in ("sclera_outer",):
                stop = "escaped"; break
        stop = stop or "escaped"
        leak = stop == "escaped" or (stop == "fundus" and not through_lens); leaks += leak; stops[stop] = stops.get(stop, 0) + 1
    return dict(status="PASS" if entered > 0 and leaks == 0 else "FAIL", rays=nrays, entered_cornea=entered, leaks=int(leaks), first_opaque=stops)


# ------------------------------------------------------------------ skin probes
def mesh_normals(V, F):
    return _MG.vertex_normals(V, F, eps=1e-30)


def probe_F1(Vh, Nh, side, inset_fn, ref_rows=None, step_mark=0.5, ref_tol=0.3):
    """outer-layer eye ring profile: skin vertices binned by PLANAR distance to the margin polygon (1 mm bins, 1-10 mm);
    the lid inner face / socket lining (h < 1.5 mm, normal facing the globe) is dropped; inset = inside Tripo (mm)"""
    E = EYES[side]; near = np.linalg.norm(Vh - E["Cs"], axis=1) < 26; P, N = Vh[near], Nh[near]
    zq = (P - E["Cs"]) @ E["n"]; P, N = P[zq > -2], N[zq > -2]
    h = V2.globe_field(P, side); rad = (P - E["Cs"]) / np.linalg.norm(P - E["Cs"], axis=1)[:, None]
    lining = (h < 1.5) & (np.einsum("ij,ij->i", N, rad) < 0); Ma = margin_dist_planar(P, side)
    keep = ~lining & (Ma >= 1) & (Ma < 10); ins = inset_fn(P[keep]); Mk = Ma[keep]; rows = []
    for b in range(1, 10):
        m = (Mk >= b) & (Mk < b + 1)
        rows.append(dict(bin=[b, b + 1], n=int(m.sum()), median_inset=round(float(np.median(ins[m])), 3) if m.sum() > 3 else None))
    med = [r["median_inset"] for r in rows if r["median_inset"] is not None]; step = float(np.abs(np.diff(med)).max()) if len(med) > 1 else None
    dev = None
    if ref_rows is not None:
        dd = [abs(a["median_inset"] - b["median_inset"]) for a, b in zip(rows, ref_rows) if a["median_inset"] is not None and b["median_inset"] is not None]
        dev = round(float(max(dd)), 3) if dd else None
    ok = step is not None and step <= step_mark and (dev is None or dev <= ref_tol)
    return dict(status="PASS" if ok else "FAIL", max_step_mm=None if step is None else round(step, 3), max_dev_vs_v2_mm=dev, rows=rows,
                marks=dict(step_mm=step_mark, dev_vs_v2_mm=ref_tol))


def probe_F2(Vh, side, stations=360, harmonics=12, rms_mark=0.03, max_mark=0.10, exclude_tel=False):
    """rim smoothness: crease = innermost skin point with |h| < 0.1 mm per station (radial M); residual after a periodic
    low-pass keeping harmonics <= 12"""
    E = EYES[side]; near = np.linalg.norm(Vh - E["Cs"], axis=1) < P_["RS"] + 3; P = Vh[near]; h = V2.globe_field(P, side)
    P = P[np.abs(h) < 0.1]; M = V2.margin_dist(P, side); P, M = P[np.abs(M) < 3], M[np.abs(M) < 3]
    n_tel = 0
    if exclude_tel and len(P):                                  # third-eyelid surface points are not LID crease points
        tl = V2.eye_parts(P, side)["tel"]; keep = tl > 0.1; n_tel = int((~keep).sum()); P, M = P[keep], M[keep]
    uv = V2._uv(E, P) - E["centre_uv"]; st = ((np.arctan2(uv[:, 1], uv[:, 0]) + np.pi) / (2 * np.pi) * stations).astype(int) % stations
    cr = np.full(stations, np.nan)
    for s in range(stations):
        m = st == s
        if m.any():
            cr[s] = M[m].min()
    fin = np.isfinite(cr)
    if fin.sum() < stations * 0.8:
        return dict(status="FAIL", why="crease found at too few stations", stations_with_crease=int(fin.sum()))
    x = np.arange(stations); c = np.interp(x, x[fin], cr[fin], period=stations)
    Fc = np.fft.rfft(c); Fc[harmonics + 1:] = 0; res = (c - np.fft.irfft(Fc, stations))[fin]
    rms, mx = float(np.sqrt((res ** 2).mean())), float(np.abs(res).max())
    st_ok = x[fin]; worst = st_ok[np.argsort(-np.abs(res))[:5]]
    return dict(status="PASS" if rms <= rms_mark and mx <= max_mark else "FAIL", rms_mm=round(rms, 4), max_mm=round(mx, 4),
                worst_stations_deg_from_minus_u=(worst * 360.0 / stations).round(1).tolist(),
                medial_canthus_deg=round(float((np.degrees(E["phi_med"]) + 180) % 360), 1), lateral_canthus_deg=round(float((np.degrees(E["phi_lat"]) + 180) % 360), 1),
                stations_with_crease=int(fin.sum()), marks_mm=[rms_mark, max_mark], tel_points_excluded=n_tel,
                label="marks ESTIMATE: the spec's plants (0.5 mm build, 0.2 mm sawtooth) not run")


def probe_tunnel_cone(Fbase_fn, side, tunnel="v3", n=40000, seed=3):
    """root-cause probe: base-skin OUTER surface points 2-5 mm (planar) outside the margin and standing > H + 0.5 above
    the globe must NOT be deleted by the tunnel (v2's radial cone deletes most of them)"""
    E = EYES[side]; rng = np.random.default_rng(seed); g = optics_geom(side)
    rr = rng.uniform(0, 1, n); a = rng.uniform(0, 2 * np.pi, n)
    # sample along rays from in front of the eye toward the face, find the base surface by bisection on F
    X = np.c_[np.cos(a), np.sin(a)] * (6 + 14 * rr)[:, None]
    O = E["Cs"] + 22 * E["n"] + X[:, :1] * E["u"] + X[:, 1:] * E["v"]; lo = np.zeros(n); hi = np.full(n, 30.0)
    Fo = Fbase_fn(O); Fe = Fbase_fn(O - 30 * E["n"]); ok_ = (Fo > 0) & (Fe < 0)
    for _ in range(40):
        mid = 0.5 * (lo + hi); f = Fbase_fn(O - mid[:, None] * E["n"]); lo = np.where(f > 0, mid, lo); hi = np.where(f > 0, hi, mid)
    S = (O - 0.5 * (lo + hi)[:, None] * E["n"])[ok_]
    Ma = margin_dist_planar(S, side); h = V2.globe_field(S, side); sel = (Ma >= 2) & (Ma < 5) & (h > P_["H"] + 0.5)
    pr = eye_parts_v3(S[sel], side, tunnel=tunnel); cut = (-pr["tunnel"]) > 0
    share = float(cut.mean()) if sel.any() else None
    return dict(status="PASS" if share is not None and share <= 0.01 else "FAIL", tunnel=tunnel, surface_points=int(sel.sum()),
                deleted_share=None if share is None else round(share, 4), mark="<= 1 %")


def contract_probe(grid_mm, lid_band_grid_mm=None):
    lb = grid_mm if lid_band_grid_mm is None else lid_band_grid_mm
    ok = grid_mm <= NEED_MM + 1e-9 and lb <= NEED_MM_LID_BAND + 1e-9
    return dict(status="PASS" if ok else "FAIL", grid_mm=grid_mm, lid_band_grid_mm=lb, need_mm=NEED_MM, need_lid_band_mm=NEED_MM_LID_BAND)
