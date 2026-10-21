"""MOUTH feature edit (Phase 2, Stage 3; criteria C4, C5, C6; spec spec_mouth.json, fix list check_mouth.json).
A SIGNED-DISTANCE edit of the SKIN field in head-frame mm (negative inside), applied once in the skin build:

    edit(P_head_mm (N,3), F_mm (N,)) -> F_mm      vectorised, chunked; only points inside REGION are touched

Parts built (inventory L3): upper-lip lobes overhanging the lower lip (L and R), the closed MOUTH CREASE (margin over a
hidden slot, never a cut or painted line), the notch where the philtrum meets the lip (the Y, one midline), the
commissure creases, the lower lip (recessed face + hidden top margin) and the chin (left as the skin has it).

GEOMETRY (per side, built by prepare() from a skin field and the Tripo envelope field, both callables in head mm):
  s        = the LABEL parameter of spec gamma_env (knots 0..25 + the commissure at s_c = 25.45), NOT arc length along the
             smoothed polyline (check_mouth blocking 2: the polyline is 24.6 mm long; with labels the tapers reach 0 at
             the corner exactly).
  Gamma_env = spec gamma_env (L), R = its mirror about x = MID_X; a cubic spline through the knots.
  U_env(s) = the envelope point at z = Gamma_env.z + u_m(s), found by marching horizontally (perpendicular to the line)
             onto the envelope (check_mouth should-fix 1: the spec's Y_junction_env lay ~1.5 mm INSIDE the envelope).
  U(s), C(s) = U_env and Gamma_env projected onto the skin (closest point, Newton on the field): the margin and the
             contact line on the skin. n = skin normal at U, t = dU/ds, b = n x t signed b.z > 0.
  LL(s)    = the lower lip's face plane: VERTICAL through C, normal horizontal and perpendicular to the line (the
             spec's 'skin normal 1 mm below C' lies on the V's up-facing lower flank); sigma(s) = how far the margin
             stands in front of it along n. sigma is an OUTPUT (check_mouth blocking 1: the spec's expected 1.3/1.5 mm
             was read 1 mm above Tripo's apex, not at the margin height); the probe checks the mesh against it.
  The section (a = along n, h = along b, origin U) holds the slot sheet: A from (2, 0) to P0 (spec: (2, -r_m); moved
  to h = 0 so the rounded margin edge lands ON U, P3a) (on LL + g/2 at h = 0),
  B from P0 up LL for v(s), C from there inward (-n) for D_in. delta = distance to the sheet, + on the upper side.
  REGION CLASSIFICATION for the sign (check_mouth should-fix 4): lower = (behind B and below the top of B) or (in front
  of B and below line A); beyond the sheet's inner end both sides give f_S (solid), so a sign flip there is harmless.
  LEFT/RIGHT (should-fix 3): x >= MID_X uses the L sheet, x < MID_X the R sheet; both start at the Y on the midline.
  f_LL = max(f_S, dLL + 3 (1 - wC)): the plane above C (wC = 1 above C + 0.5), the skin below C - 0.5 (Tripo's lower
         lip / chin kept); this removes Tripo's fill under the overhang (the photo's shadow crescent).
  f_up = smax(f_S, g/2 - delta, r_m);  f_lo = smax(f_LL, delta + g/2, 0.4);  f_m = min(f_up, f_lo)  (hard min: the gap)
  F' = Z f_m + (1 - Z) f_S,  Z = tube of 8 mm round U with a 2 mm smoothstep edge, clipped 1 mm past the corner.
  Commissure creases: + D(l) exp(-(r/0.5)^2) along a 4 mm path continuing the line's tangent at the corner (projected on
  the skin); D = 0.3 (1 - l/4) -> 0.225 / 0.15 / 0.075 at 1 / 2 / 3 mm.
  Lower-lip side folds: OPTIONAL, default OFF (should-fix 6: may be a Tripo fur parting; no source).

VALUES (source / confidence): u_m knots = spec (PHOTO via a translation-only registration, medium-low; the P3 photo test
  is a consistency check only, should-fix 5). v = 0.5 -> 2.5 over s 0-3 (spec, ESTIMATE), then a concave taper
  2.5 (1 - u^3), u = (s - s_c + 4)/4 (ESTIMATE, changed from the spec's cosine so the slot tip lands within 0.7 mm of the
  corner on a 0.12 mm grid; the spec's range [1.5, 4.0] is for the plateau only, should-fix 10).
  g = 0.30 mm (CONSTRUCTION, spec range 0.1-0.3, top end chosen so the gap is >= 2.5 voxels at 0.12 mm; the field MUST
  be evaluated at <= g/2.5 voxels inside REGION or the gap fills: hand-off to the integration). r_m = 0.4 (ESTIMATE,
  confidence low), D_in = 1.5 (ESTIMATE, low), lower-lip top rounding 0.4 (ESTIMATE, low), Z 8 mm + 2 mm edge
  (CONSTRUCTION: the sheet and the cavity lie within 5 mm of U), the 1 mm blend at C (CONSTRUCTION).
MIDLINE: x = MID_X = +0.25 (the measured muzzle mirror plane); the Y is (+0.25, y on the skin, z -19.3). spec_nose's
  philtrum ends at (-0.5, -68.2, -19.3) on a chord; the nose build should end its groove at Y_HEAD_MM (hand-off).
"""
import json
import os

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
MID_X = 0.25
S_C = 25.45
G_ENV_L = np.array([
    [0.25, -66.29, -22.85], [1.23, -66.44, -23.01], [2.16, -66.61, -23.26], [3.09, -66.63, -23.57], [4.02, -66.51, -23.89],
    [4.95, -66.3, -24.18], [5.85, -66.01, -24.49], [6.68, -65.59, -24.83], [7.51, -65.14, -25.15], [8.38, -64.76, -25.4],
    [9.22, -64.33, -25.68], [10.01, -63.86, -25.97], [10.71, -63.29, -26.34], [11.4, -62.7, -26.71], [12.0, -62.05, -27.12],
    [12.69, -61.41, -27.42], [13.29, -60.69, -27.7], [13.85, -59.92, -27.94], [14.48, -59.18, -28.08], [15.13, -58.44, -28.15],
    [15.73, -57.76, -28.2], [16.47, -57.47, -27.91], [17.25, -57.06, -27.55], [17.85, -56.36, -27.38], [18.3, -55.49, -27.39],
    [18.64, -54.61, -27.38], [18.77, -54.31, -27.35]])
S_ENV = np.r_[np.arange(26.0), S_C]
UM_S = np.array([0, 1.5, 3, 5, 7.5, 9, 11.3, 12.8, 21.45]); UM_V = np.array([3.55, 2.2, 1.9, 1.7, 1.7, 1.5, 1.35, 1.3, 1.0])
G, R_M, D_IN, LOW_R = 0.30, 0.4, 1.5, 0.4
SIG_MIN = 0.6   # ESTIMATE (spec sigma taper ends at 0.5 at the corner; 0.6 keeps a 0.3 mm flap over the 0.3 mm gap)
Z_R, Z_W, Z_END = 8.0, 2.0, 1.0
CREASE_L, CREASE_D0, CREASE_W = 4.0, 0.3, 0.5
SIDE_FOLDS = False
DS = 0.05
Y_Z = -19.3


def ss(t):
    t = np.clip(t, 0.0, 1.0); return t * t * (3.0 - 2.0 * t)


def smax(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k; return np.maximum(a, b) + h * h * k * 0.25


def u_m(s):
    s = np.asarray(s, float); out = np.interp(s, UM_S, UM_V)
    tail = s > 21.45; out[tail] = 0.5 * (1 + np.cos(np.pi * np.clip((s[tail] - 21.45) / (S_C - 21.45), 0, 1)))
    return out


def v_of(s):
    s = np.asarray(s, float); out = np.where(s < 3, 0.5 + 2.0 * s / 3, 2.5)
    u = np.clip((s - (S_C - 4)) / 4, 0, 1); return np.where(s > S_C - 4, 2.5 * (1 - u ** 3), out)


def g_of(s):
    return G * ss((S_C - np.asarray(s, float)) / 0.5)


def d_of(s):
    return D_IN * (0.4 + 0.6 * ss((S_C - np.asarray(s, float)) / 2.0))


def _unit(x):
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12)


def _grad(field, P, h=0.05):
    g = np.zeros_like(P)
    for k in range(3):
        e = np.zeros(3); e[k] = h; g[:, k] = (field(P + e) - field(P - e)) / (2 * h)
    return g


def _project(field, P, it=6):
    P = P.copy()
    for _ in range(it):
        g = _grad(field, P); P -= (field(P) / np.maximum((g * g).sum(1), 1e-9))[:, None] * g
    return P


def _side(skin, env, Genv, tenv, s):
    z = np.array([0, 0, 1.0]); um = u_m(s)
    o = _unit(np.cross(z, tenv)); o[o[:, 1] > 0] *= -1                      # horizontal, outward (face is at -y)
    lam = np.arange(-3.0, 6.0, 0.05); base = Genv + um[:, None] * z
    Q = base[:, None, :] + lam[None, :, None] * o[:, None, :]
    E = env(Q.reshape(-1, 3)).reshape(len(s), len(lam)); inside = E < 0
    i0 = np.argmax(inside, axis=1); out_ = ~inside & (np.arange(len(lam))[None] > i0[:, None])
    last = np.argmax(out_, axis=1) - 1                                       # first exit going outward (not a whisker)
    last = np.clip(last, 0, len(lam) - 2); r = np.arange(len(s))
    e0, e1 = E[r, last], E[r, last + 1]; fr = np.clip(e0 / np.minimum(e0 - e1, -1e-9), 0, 1)
    Uenv = base + (lam[last] + fr * 0.05)[:, None] * o
    U = _project(skin, Uenv); C = _project(skin, Genv)
    k = 6; w = np.exp(-0.5 * (np.arange(-3 * k, 3 * k + 1) / k) ** 2); w /= w.sum()   # sigma 0.3 mm along s
    from scipy.ndimage import median_filter
    Um = median_filter(U, size=(41, 1), mode="nearest")                      # 2 mm median: drops single-station jumps
    Us = np.stack([np.convolve(np.pad(Um[:, i], 3 * k, mode="edge"), w, "valid") for i in range(3)], 1)
    Us[0] = U[0]; U = _project(skin, Us)
    t = _unit(np.gradient(U, axis=0)); n = _unit(_grad(skin, U)); n = _unit(n - (n * t).sum(1)[:, None] * t)
    b = _unit(np.cross(n, t)); b[b[:, 2] < 0] *= -1
    # LL plane: VERTICAL through C, normal = the horizontal outward direction perpendicular to the line (check_mouth
    # blocking 1: the skin normal just below Tripo's apex lies on the V's lower flank and faces UP, which tilts the
    # plane forward and makes sigma 0.2-0.7 mm; the check re-derived the step on sagittal cuts as a y-step: 2.2-3.3 mm)
    nLL = _unit(np.cross(z, t)); nLL[(nLL * n).sum(1) < 0] *= -1; nLL = _unit(nLL - (nLL * t).sum(1)[:, None] * t)
    eup = _unit(np.cross(t, nLL)); eup[(eup * b).sum(1) < 0] *= -1
    C2 = np.c_[((C - U) * n).sum(1), ((C - U) * b).sum(1)]
    nl2 = _unit(np.c_[(nLL * n).sum(1), (nLL * b).sum(1)]); eu2 = _unit(np.c_[(eup * n).sum(1), (eup * b).sum(1)])
    g = g_of(s); sigma = -(C2[:, 0] + C2[:, 1] * nl2[:, 1] / nl2[:, 0])
    P0a = C2[:, 0] + (g / 2 + C2[:, 1] * nl2[:, 1]) / nl2[:, 0]
    # sigma floor SIG_MIN (spec: the step tapers to 0.5 at the corner, not to 0): where the geometry gives less (u_m -> 0
    # makes U = C near the corner), the LL plane moves back so the flap keeps >= SIG_MIN - g of thickness to the end
    dlt = np.maximum(SIG_MIN - sigma, 0.0); P0a = P0a - dlt; sigma = sigma + dlt; lloff = dlt * nl2[:, 0]
    # commissure crease path: the line's tangent at the corner, projected on the skin
    l = np.arange(0.0, CREASE_L + 1e-9, 0.1); cp = _project(skin, C[-1] + l[:, None] * t[-1])
    return dict(s=s, Uenv=Uenv, U=U, C=C, n=n, b=b, t=t, nLL=nLL, eup=eup, C2=C2, nl2=nl2, eu2=eu2, sigma=sigma, P0a=P0a,
                v=v_of(s), g=g, D=d_of(s), crease=cp, crease_l=l, lloff=lloff)


def prepare(skin, env, ds=DS):
    """GEOM from a skin field and the envelope field (callables: (N,3) head mm -> mm, negative inside)"""
    s = np.arange(0.0, S_C + 1e-9, ds); cs = CubicSpline(S_ENV, G_ENV_L, axis=0)
    GL = cs(s); tL = _unit(cs(s, 1)); GR = GL.copy(); GR[:, 0] = 2 * MID_X - GR[:, 0]; tR = tL.copy(); tR[:, 0] *= -1
    return {"L": _side(skin, env, GL, tL, s), "R": _side(skin, env, GR, tR, s)}


def region(geom):
    A = np.concatenate([geom[k][q] for k in ("L", "R") for q in ("U", "C", "crease")])
    return np.floor(A.min(0) - Z_R - 0.5), np.ceil(A.max(0) + Z_R + 0.5)


def _seg2(qa, qh, A, B):
    da, dh = B[..., 0] - A[..., 0], B[..., 1] - A[..., 1]
    tt = np.clip(((qa - A[..., 0]) * da + (qh - A[..., 1]) * dh) / np.maximum(da * da + dh * dh, 1e-12), 0, 1)
    return np.hypot(qa - A[..., 0] - tt * da, qh - A[..., 1] - tt * dh)


_TREES = {}


def _edit_side(q, F, G_):
    key = id(G_)
    if key not in _TREES:
        _TREES[key] = (cKDTree(G_["U"]), cKDTree(G_["crease"]))
    tU, tc = _TREES[key]
    dist, i = tU.query(q); d = q - G_["U"][i]
    a = (d * G_["n"][i]).sum(1); h = (d * G_["b"][i]).sum(1); e = (d * G_["t"][i]).sum(1)
    Z = ss((Z_R - dist) / Z_W); end = (i == len(G_["s"]) - 1) & (e > 0); Z[end] *= ss((Z_END - e[end]) / Z_END)
    g, v, D = G_["g"][i], G_["v"][i], G_["D"][i]
    QA = np.stack([np.full(len(q), 2.0), np.zeros(len(q))], 1); P0 = np.stack([G_["P0a"][i], np.zeros(len(q))], 1)
    P1 = P0 + v[:, None] * G_["eu2"][i]; P2 = P1 - np.stack([D, np.zeros(len(q))], 1)
    dist2 = np.minimum(np.minimum(_seg2(a, h, QA, P0), _seg2(a, h, P0, P1)), _seg2(a, h, P1, P2))
    nl, eu = G_["nl2"][i], G_["eu2"][i]
    wB = (a - P0[:, 0]) * nl[:, 0] + (h - P0[:, 1]) * nl[:, 1]; uB = (a - P0[:, 0]) * eu[:, 0] + (h - P0[:, 1]) * eu[:, 1]
    dA = P0 - QA; crossA = dA[:, 0] * (h - QA[:, 1]) - dA[:, 1] * (a - QA[:, 0])
    lower = ((wB < 0) & (uB < v)) | ((wB >= 0) & (crossA >= 0))
    delta = np.where(lower, -dist2, dist2)
    dc = q - G_["C"][i]; dLL = (dc * G_["nLL"][i]).sum(1) + G_["lloff"][i]; wC = ss(((dc * G_["eup"][i]).sum(1) + 0.5) / 1.0)
    fLL = smax(F, dLL + 3.0 * (1 - wC), 0.2)
    fup = smax(F, g / 2 - delta, R_M); flo = smax(fLL, delta + g / 2, LOW_R)
    out = Z * np.minimum(fup, flo) + (1 - Z) * F
    dcr, ic = tc.query(q); lc = G_["crease_l"][ic]
    out += CREASE_D0 * np.clip(1 - lc / CREASE_L, 0, 1) * np.exp(-(dcr / CREASE_W) ** 2) * (dcr < 3 * CREASE_W)
    return out


def edit(P_head_mm, F_mm, geom=None, chunk=400000):
    """the mouth edit of the skin field; P (N,3) head-frame mm, F (N,) mm (negative inside) -> new F (N,)"""
    geom = geom or GEOM
    P = np.asarray(P_head_mm, float); F = np.array(F_mm, float, copy=True)
    lo, hi = region(geom); idx = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
    for c0 in range(0, len(idx), chunk):
        ii = idx[c0:c0 + chunk]; q = P[ii]; R = q[:, 0] < MID_X
        for side, m in (("L", ~R), ("R", R)):
            if m.any():
                F[ii[m]] = _edit_side(q[m], F[ii[m]], geom[side])
    return F


def probe_inputs(geom=None, stations=(2.0, 7.0, 12.0, 20.0)):
    """what the inventory probes need (JSON-able): design sections, the Y, the corners, the crease paths"""
    geom = geom or GEOM; out = {"mid_x": MID_X, "Y_mm": Y_HEAD_MM(geom).tolist(), "contact_mm": geom["L"]["C"][0].tolist()}
    for sd in ("L", "R"):
        G_ = geom[sd]; rows = []
        for s0 in list(stations) + list(np.arange(0.5, S_C - 0.4, 1.0)):
            i = int(round(s0 / DS))
            rows.append({k: (G_[k][i].tolist() if np.ndim(G_[k][i]) else float(G_[k][i]))
                         for k in ("s", "U", "C", "n", "b", "t", "sigma", "v", "g", "P0a", "eu2", "nl2")})
        tip = []
        for s0 in np.arange(S_C - 3.0, S_C + 1e-9, 0.25):
            i = min(int(round(s0 / DS)), len(G_["s"]) - 1)
            tip.append({k: (G_[k][i].tolist() if np.ndim(G_[k][i]) else float(G_[k][i])) for k in ("s", "U", "n", "b", "v", "g", "eu2", "nl2", "sigma")})
        out[sd] = {"sections": rows[:len(stations)], "walk": rows[len(stations):], "tip": tip, "corner_mm": G_["C"][-1].tolist(),
                   "U_line": G_["U"][::10].tolist(), "U_s": G_["s"][::10].tolist(),
                   "crease": G_["crease"].tolist(), "crease_l": G_["crease_l"].tolist(), "crease_D0": CREASE_D0,
                   "crease_L": CREASE_L}
    return out


def Y_HEAD_MM(geom=None):
    geom = geom or GEOM; return 0.5 * (geom["L"]["U"][0] + geom["R"]["U"][0])


def _load(path=os.path.join(HERE, "feat_mouth_geom.json")):
    if not os.path.exists(path):
        return None
    J = json.load(open(path)); return {sd: {k: np.asarray(v) for k, v in J[sd].items()} for sd in ("L", "R")}


def save_geom(geom, path=os.path.join(HERE, "feat_mouth_geom.json")):
    json.dump({sd: {k: np.round(np.asarray(v), 5).tolist() for k, v in geom[sd].items()} for sd in ("L", "R")}, open(path, "w"))


GEOM = _load()
REGION = region(GEOM) if GEOM is not None else None
