"""MOUTH v3b feature (felid pack, case cat1, cat v3 round 2) - builder 'feat-mouth-v3b', 2026-10-18.
Ruling R-M (NOTES_v3 13:25) and the person on flag_49: "the form of the lip is generally right, the shape of it... But it
doesn't cut all the way through, and there's no cavity and mouth area with tongue or teeth or lips or gums ... And with
the chin mess, it would be very difficult to get it right." This cat gets the skeleton and the rig: the jaw must open.

feat_mouth_v3.py (and through it feat_mouth.py, v2) is IMPORTED and left unchanged. Its GEOM, slot sheet, overhang, Y,
commissures and every value not named here stand. Values from outside the photo / Tripo are in spec_mouth_v3b.json with
source and confidence; the unseen inside comes from the CLASS model (Reighard 1901 anatomy + the felid pack's measured
ref20 skull, scaled to this head), never from a slab or a mirror.

WHAT v3b ADDS TO THE SKIN FIELD (head mm, negative inside)
  1. THE PARTING LINE GOES THROUGH. v3's slot sheet A -> P0 -> P1 -> P2 ended blind at P2 (0.4 mm wide, 1.5 mm past the
     lower-lip top). v3b's parting sheet, per station: just outside the margin -> P0 -> P1 -> P2 (v3's own sheet, made
     air where v3's nearest-U station rule had sealed it: its P1 -> P2 leg was solid at s 12-20 on both sides) -> P3 =
     the nearest cavity-wall point + PAST_WALL inside, smoothed along s; the station's gap g kept. ext_air(P) =
     dist(sheet) - g/2 (dense samples, <= 0.035 mm apart). Checked: every station's path outside -> cavity is air.
  2. THE ORAL CAVITY (closed jaw). cavity_sdf(P): the skin turning inward at the lips lines a closed 'mouth bag' that
     holds the vestibule (VEST mm of air round the teeth and gums, Reighard: 'the sides of the mouth cavity are formed by
     the teeth and the gums'), roofed by the palate and floored under the tongue, closed at the fauces. Built in the JAW
     frame from plan fields (the upper and lower dental outlines, used by height zones; the inner arch) and height fields
     (gum lines, fornices, palate, floor). F' = max(max(F_v3, -ext_air), -cavity), rounded by JOIN_K only within 1 mm of
     the parting sheet (a smooth max everywhere let the base field's internal near-zero seams, F ~ -0.1 deep in the head,
     bulge the lining): ONE continuous manifold, mucosa inside. The upper labial fornix is shallow in front of the
     canines (2.3 mm) so the nose owner's passages keep >= 3 mm (NOTES 15:05).
  3. THE CHIN IS ONE SMOOTH SURFACE (C1). Below the contact C, v3's receding cut plane still cut shallow scoops out of
     Tripo's chin where the chin bulges (0.57 mm deep at the midline, z -24..-27.5) and left the chin through a kink; and
     v3 split the two sides hard at the midline (a seam down the lower lip and chin). v3b (a) FADES the lower-lip cut out
     between 0.5 and 3.0 mm below C (fLL = F + w (f_v3 - F), smoothstep; v3 bitwise above), and (b) blends the L and R
     fields linearly over |x - MID_X| < MID_BLEND. Tried and dropped (sections + the M2 metric on FIELD profiles, which
     reproduced v3's mesh result 0.38 vs 0.40): a round intersection R 2.5 mm and a wide smooth max (k 2) both ERODED the
     chin up to 0.85 mm where v3's receding plane runs near it (line share 0.96-0.98); a vertical plane below C stopped
     its cut abruptly (a 0.4 mm step) because v3's min(fup, flo) ends the cut away from the slot sheet.
  The parts (teeth, gums, palate, tongue) are NOT in the skin: feat_oral_v3b builds them as separate meshes from the same
  jaw frame (one definition, shared: M7).

JAW FRAME: a weighted similarity (Umeyama, as tools/skull_place) of skull landmarks (eye seats, incisors) onto the head
(globe centres from feat_eyes, the midline slot end); scale and residuals reported (G5) by registration_report().

API (feat_mouth_v3's, so the merge stage can swap this module in): REGION ; NEED_MM ; RESOLUTION ; GEOM ; edit(P, F) ;
opening_sdf(P) ; fix_zone(P) ; probe_inputs() ; Y_HEAD_MM() ; contract_probe(grid_mm) ; V3_PARAMS (+ V3B_PARAMS)
plus: cavity_sdf(P), ext_air(P), parting_zone(P), chin_zone(P), opening_shell_sdf(P), to_jaw / to_head, JAW, TMJ_HEAD_MM,
mesh_adaptive (shared mesher), run_preview(grid) (CLI: python feat_mouth_v3b.py preview 0.10 | register).
"""
import json
import os
import sys
import time

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feat_mouth_v3 as M3  # noqa: E402  (unchanged)

V2 = M3.V2
MID_X, S_C, DS = M3.MID_X, M3.S_C, M3.DS
ss, smax, _seg2 = M3.ss, M3.smax, M3._seg2
GEOM = M3.GEOM
V3_PARAMS = M3.V3_PARAMS
Y_HEAD_MM = M3.Y_HEAD_MM
SPEC_PATH = os.path.join(HERE, "spec_mouth_v3b.json")
SPEC = json.load(open(SPEC_PATH))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
LAYERS = os.path.join(ROOT, "tripo_rebuild", "layers")

GRID_CAP_MM = 0.15
NEED_MM = 0.10
RESOLUTION = {"region_mm": NEED_MM, "cap_mm": GRID_CAP_MM, "parts_mm": SPEC["resolution"]["parts_mm"],
              "source": "v3: slot g 0.30 mm -> 3 voxels at 0.10 mm; v3b: vestibule 0.5 mm -> 5 voxels; the opening "
                        "(opening_sdf: slot + extension + cavity) must stay air"}

VEST = SPEC["bag"]["vestibule_mm"]["value"]
BAG_R = SPEC["bag"]["round_mm"]["value"]
PAL_EMBED = SPEC["palate"]["embed_mm"]["value"]
EXT_MAX = SPEC["slot_ext"]["max_len_mm"]["value"]
PAST_WALL = SPEC["slot_ext"]["past_wall_mm"]["value"]
EXT_SMOOTH = SPEC["slot_ext"]["smooth_mm"]["value"]
JOIN_K = SPEC["slot_ext"]["join_k_mm"]["value"]
MID_BLEND = SPEC["chin"]["mid_blend_mm"]["value"]
CHIN_FADE = SPEC["chin"]["fade_hc_mm"]["value"]
KEEPOUT = SPEC["bag"]["keepout_mm"]["value"]
V3B_PARAMS = {
    "VEST": (VEST, SPEC["bag"]["vestibule_mm"]["src"], "construction"),
    "BAG_R": (BAG_R, SPEC["bag"]["round_mm"]["src"], "construction"),
    "CHIN_FADE": (CHIN_FADE, SPEC["chin"]["fade_hc_mm"]["src"], "construction"),
    "MID_BLEND": (MID_BLEND, SPEC["chin"]["mid_blend_mm"]["src"], "construction"),
    "EXT_MAX": (EXT_MAX, SPEC["slot_ext"]["max_len_mm"]["src"], "construction"),
    "PAST_WALL": (PAST_WALL, SPEC["slot_ext"]["past_wall_mm"]["src"], "construction"),
    "JOIN_K": (JOIN_K, SPEC["slot_ext"]["join_k_mm"]["src"], "construction"),
    "KEEPOUT": (KEEPOUT, SPEC["bag"]["keepout_mm"]["src"], "estimate"),
}


def _unit(x):
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12)


def round_int(a, b, r):
    """round intersection (hg_sdf fOpIntersectionRound): max(a, b) with the convex edge rounded by radius r"""
    r = np.asarray(r, float)
    return np.minimum(-r, np.maximum(a, b)) + np.hypot(np.maximum(r + a, 0.0), np.maximum(r + b, 0.0))


# =============================================================== the jaw frame (registration)
def umeyama(A, B, w):
    """weighted similarity B ~ s R A + t (tools/skull_place.umeyama)"""
    w = np.asarray(w, float) / np.sum(w); ma, mb = (w[:, None] * A).sum(0), (w[:, None] * B).sum(0)
    A0, B0 = A - ma, B - mb; C = (w[:, None] * B0).T @ A0; U, D, Vt = np.linalg.svd(C)
    S = np.eye(3); S[2, 2] = np.sign(np.linalg.det(U @ Vt)); R = U @ S @ Vt
    s = np.trace(np.diag(D) @ S) / (w * (A0 ** 2).sum(1)).sum(); return s, R, mb - s * R @ ma


def _p2(sd, s0):
    G_ = GEOM[sd]; k = int(round(s0 / DS)); P0 = np.array([G_["P0a"][k], 0.0]); P1 = P0 + G_["v"][k] * G_["eu2"][k]
    P2 = P1 - np.array([G_["D"][k], 0.0]); return G_["U"][k] + P2[0] * G_["n"][k] + P2[1] * G_["b"][k]


def _register():
    import feat_eyes as FY
    reg = SPEC["registration"]; A, B, w, names = [], [], [], []
    for p in reg["pairs"]:
        A.append(p["skull"]); w.append(p["weight"]); names.append(p["name"])
        if p["name"] == "eye.L":
            B.append(FY.EYES["L"]["Cs"])
        elif p["name"] == "eye.R":
            B.append(FY.EYES["R"]["Cs"])
        else:
            q = 0.5 * (_p2("L", 0.0) + _p2("R", 0.0)); q[0] = reg["x_mid"]["value"]; q[1] += 1.5; B.append(q)
    A = np.array(A, float); B = np.array(B, float); s, R, t = umeyama(A, B, w)
    res = {n: round(float(np.linalg.norm(s * R @ a + t - b)), 3) for n, a, b in zip(names, A, B)}
    O_sk = np.array(SPEC["sources"]["ref20_picks"]["derived_skull_mm"]["O_jaw_in_skull_model"], float)
    # jaw axes in the skull model: f = -y, l = +x, u = +z ; head = t + s R (O_sk + f e_f + l e_l + u e_u)
    E = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]).T          # columns e_f, e_l, e_u (skull model)
    O = t + s * R @ O_sk; M = R @ E                                                  # head = O + s M [f, l, u]
    # symmetry: the jaws are built about x = MID_X; the fit's own x offset is reported, the frame is re-centred
    O = O.copy(); dx = O[0] - reg["x_mid"]["value"]; O[0] = reg["x_mid"]["value"]
    sl = 89.4 * s
    return dict(s=float(s), R=R, t=t, O=O, M=M, residual_mm=res, x_offset_removed_mm=round(float(dx), 3),
                skull_length_mm=round(float(sl), 1), ramos_range_mm=[82.8, 98.2],
                ramos_z=round(float((sl - 89.4) / 4.5), 2), A=A, B=B, names=names)


JAW = _register()
S_JAW = JAW["s"]


def to_jaw(P):
    """head mm (N,3) -> jaw (f, l, u) skull-model mm"""
    return ((np.asarray(P, float) - JAW["O"]) @ JAW["M"]) / S_JAW


def to_head(J):
    return JAW["O"] + S_JAW * (np.asarray(J, float) @ JAW["M"].T)


def dir_to_head(D):
    return np.asarray(D, float) @ JAW["M"].T


_TMJ_FU = SPEC["sources"]["ref20_picks"]["derived_skull_mm"]["tmj_fu"]
TMJ_HEAD_MM = {sd: to_head([_TMJ_FU[0], sg * 16.5, _TMJ_FU[1]]) for sd, sg in (("L", 1.0), ("R", -1.0))}


# =============================================================== the dental model (jaw frame, skull mm)
def _interp(tab, x):
    tab = np.asarray(tab, float); o = np.argsort(tab[:, 0]); return np.interp(x, tab[o, 0], tab[o, 1])


def _arch_nodes(jaw):
    """left-side arch centre nodes (f, l, u_gum, half_w, tooth index or -1) in ARCH ORDER (the spec's tooth order: incisors
    -> canine -> premolars, the extra nodes after their tooth), from the midline node to the end node"""
    T = SPEC["teeth"][jaw]; A = SPEC["arch"]; extra = A[f"{jaw}_centre_extra"]; nodes = []
    for i, tt in enumerate(T):
        if tt["type"].startswith("molar"):
            continue                                   # the upper M1 lies off the row (caudomediad of P4)
        f, l, u = tt["base"]; nodes.append((f, l, u, 0.5 * tt["W"] + A["gum_collar_mm"]["value"], i))
        for e in extra:
            if e["after"] == tt["id"]:
                nodes.append((e["f"], e["l"], e["u_gum"], e["half_w"], -1))
    e = A[f"{jaw}_end"]; nodes.append((e["f"], e["l"], e["u_gum"], e["half_w"], -1))
    f0 = nodes[0][0]; nodes.insert(0, (f0, 0.0, nodes[0][2], nodes[0][3], -1))      # the midline node (mirror junction)
    return np.array(nodes, float)


def _arch_poly(jaw, step=0.02):
    """the full arch centre polyline R end -> midline -> L end in plan (f, l), dense, with attributes"""
    N = _arch_nodes(jaw)[:, :4]                       # left half from the midline
    pts = []
    for a, b in zip(N[:-1], N[1:]):
        m = max(int(np.ceil(np.hypot(b[0] - a[0], b[1] - a[1]) / step)), 1)
        t = np.linspace(0, 1, m, endpoint=False)[:, None]; pts.append(a + t * (b - a))
    pts.append(N[-1:]); L = np.vstack(pts)
    # smooth the polyline (Gaussian 0.6 mm along it, ends pinned) so the band has no corners
    k = int(0.6 / step); w = np.exp(-0.5 * (np.arange(-3 * k, 3 * k + 1) / k) ** 2); w /= w.sum()
    Ls = L.copy()
    for c in range(L.shape[1]):
        Ls[:, c] = np.convolve(np.pad(L[:, c], 3 * k, mode="edge"), w, "valid")
    Ls[0, 1] = 0.0
    R = Ls[::-1].copy(); R[:, 1] *= -1
    full = np.vstack([R[:-1], Ls]); return full


ARCH = {jaw: _arch_poly(jaw) for jaw in ("upper", "lower")}


def tooth_list():
    """every tooth (both sides): dict with jaw, id, side, type, base (f, l, u), tip, mesial dir (plan), L, W, H, cusps"""
    out = []
    for jaw in ("upper", "lower"):
        sg_u = -1.0 if jaw == "upper" else 1.0; P = ARCH[jaw]
        for tt in SPEC["teeth"][jaw]:
            for side, sg in (("L", 1.0), ("R", -1.0)):
                f, l, u = tt["base"]; base = np.array([f, sg * l, u])
                if tt.get("axis_from_to"):
                    a, b = np.array(tt["axis_from_to"], float); mes = _unit(a - b)
                elif tt.get("axis") is not None:
                    ang = np.radians(tt["axis"]); mes = np.array([np.cos(ang), np.sin(ang)])
                else:                                                  # from the arch: tangent toward the front
                    Pl = P[P[:, 1] >= 0]; j = np.argmin(np.hypot(Pl[:, 0] - f, Pl[:, 1] - l))
                    a, b = Pl[max(j - 25, 0)], Pl[min(j + 25, len(Pl) - 1)]; mes = _unit(np.array([a[0] - b[0], a[1] - b[1]]))
                    if mes[0] < 0:
                        mes = -mes
                mes = np.array([mes[0], sg * mes[1]])
                tip = base + np.array([tt.get("tip_df", 0.0), sg * tt.get("tip_dl", 0.0), sg_u * tt["H"]])
                xm = 0.0
                if tt.get("cusps"):
                    xm = max(tt["cusps"], key=lambda c: c[1])[0]           # the main cusp's place on the mesiodistal axis
                cusp = tip + np.r_[-xm * tt["L"] * mes, 0.0]                  # (x: -0.5 mesial .. +0.5 distal)
                out.append(dict(jaw=jaw, id=tt["id"], side=side, name=f"{'u' if jaw == 'upper' else 'l'}{tt['id']}.{side}",
                                type=tt["type"], base=base, tip=tip, cusp=cusp, mesial=mes, L=tt["L"], W=tt["W"], H=tt["H"],
                                cusps=tt.get("cusps"), protocone=tt.get("protocone"), root=tt["root"], src=tt["src"],
                                up=sg_u))
    return out


TEETH = tooth_list()


# =============================================================== plan fields (2-D grids in f, l; skull mm)
PLAN_H = 0.05
PLAN_LO = np.array([-47.0, -21.0]); PLAN_HI = np.array([12.0, 21.0])     # f to +12: no clamped distances in front


def _plan_grid():
    nf = int(round((PLAN_HI[0] - PLAN_LO[0]) / PLAN_H)) + 1; nl = int(round((PLAN_HI[1] - PLAN_LO[1]) / PLAN_H)) + 1
    f = PLAN_LO[0] + PLAN_H * np.arange(nf); l = PLAN_LO[1] + PLAN_H * np.arange(nl)
    return np.meshgrid(f, l, indexing="ij")


def _arch_coords(jaw, F, L):
    """nearest arch point index, signed lateral distance d (+ buccal = away from the arch's inside), attributes"""
    P = ARCH[jaw]; tree = cKDTree(P[:, :2]); Q = np.c_[F.ravel(), L.ravel()]; dist, j = tree.query(Q)
    tan = np.gradient(P[:, :2], axis=0); tan = _unit(tan)
    nrm = np.c_[tan[:, 1], -tan[:, 0]]                          # rotate: for the L half (moving back, l > 0) -> +l side
    # orient: buccal = pointing away from the arch's centroid line (l -> 0 inside, f -> back inside at the front)
    inside_ref = np.array([P[:, 0].mean() - 4.0, 0.0])
    sgn = np.sign(((P[:, :2] - inside_ref) * nrm).sum(1)); sgn[sgn == 0] = 1; nrm = nrm * sgn[:, None]
    d = ((Q - P[j, :2]) * nrm[j]).sum(1)
    d = np.where(np.abs(d) > 0, np.sign(d) * dist, d)
    return j.reshape(F.shape), d.reshape(F.shape)


def _sdf2(mask, h=PLAN_H):
    """signed distance (negative inside) of a boolean plan mask"""
    return (ndimage.distance_transform_edt(~mask) - ndimage.distance_transform_edt(mask)) * h


def _build_plan():
    Fg, Lg = _plan_grid(); out = {"F": Fg, "L": Lg}
    for jaw in ("upper", "lower"):
        j, d = _arch_coords(jaw, Fg, Lg); P = ARCH[jaw]
        out[f"{jaw}_j"] = j; out[f"{jaw}_d"] = d
        # nearest-point attributes jump where the nearest arch point jumps (the medial axis, beyond the arch end): smooth
        out[f"{jaw}_ugum"] = ndimage.gaussian_filter(P[j, 2], 0.3 / PLAN_H); out[f"{jaw}_hw"] = ndimage.gaussian_filter(P[j, 3], 0.3 / PLAN_H)
        # the vestibule weight (buccal / labial of the arch centre line, in front of its end), CONTINUOUS: the sign of d
        # flips across the end node's normal line, which made the cavity roof jump 1.7 mm behind the last teeth
        fe = float(P[-1, 0]); w = (1.0 / (1.0 + np.exp(-(d + 0.3) / 0.25))) * np.clip((Fg - (fe - 1.5)) / 1.0, 0, 1)
        out[f"{jaw}_wv"] = ndimage.gaussian_filter(w, 0.5 / PLAN_H).astype(np.float32)
    # crown footprints (ellipses at the base + the tip disc, per jaw) and the gum bands
    foot = {"upper": np.zeros(Fg.shape, bool), "lower": np.zeros(Fg.shape, bool)}
    for t in TEETH:
        m = t["mesial"]; b = np.array([-m[1], m[0]]); dq = np.stack([Fg - t["base"][0], Lg - t["base"][1]], -1)
        x = dq @ m; y = dq @ b; foot[t["jaw"]] |= (x / (0.5 * t["L"] + 0.05)) ** 2 + (y / (0.5 * t["W"] + 0.05)) ** 2 <= 1.0
        tp = np.stack([Fg - t["tip"][0], Lg - t["tip"][1]], -1); foot[t["jaw"]] |= np.hypot(tp[..., 0], tp[..., 1]) < 0.6
        if t.get("protocone"):
            pc = t["protocone"]; c = t["base"][:2] - pc["x"] * t["L"] * m          # x: -0.5 mesial .. +0.5 distal
            lin = -np.array([0.0, np.sign(t["base"][1])]); c = c + (0.5 * t["W"] + pc["lingual_mm"]) * lin
            foot[t["jaw"]] |= np.hypot(Fg - c[0], Lg - c[1]) < pc["r"] + 0.05
    band_x = _interp(SPEC["arch"]["gum_band_extra_mm"]["by_f"], Fg)
    band = {jaw: (np.abs(out[f"{jaw}_d"]) <= out[f"{jaw}_hw"] + band_x) for jaw in ("upper", "lower")}
    out["band_x"] = band_x
    tg = SPEC["tongue"]; tf = np.array(tg["half_w"], float)
    hw_t = np.interp(Fg, tf[::-1, 0], tf[::-1, 1], left=0.0, right=0.0)
    tongue_fp = (np.abs(Lg) <= hw_t + 0.3) & (Fg <= tg["tip_f"] + 0.3) & (Fg >= tg["root_f"])
    # back closure: from behind the last teeth converge to the fauces (f back_f, half fauces_half_w)
    bf, fh = SPEC["bag"]["back_f"], SPEC["bag"]["fauces_half_w"]
    fend = min(ARCH["upper"][-1, 0], ARCH["lower"][-1, 0]); endL = float(np.interp(fend, tf[::-1, 0], tf[::-1, 1])) + 2.5
    tback = np.clip((fend - Fg) / max(fend - bf, 1e-6), 0, 1); hw_back = endL + (fh - endL) * tback
    back = (Fg <= fend + 1.0) & (Fg >= bf) & (np.abs(Lg) <= hw_back)

    def fill(solid, f_front):                # fill the U row by row (between its sides) BEHIND the midline arch front
        filled = solid.copy()                # (in front of it, e.g. between the protruding lower canines, stays open)
        for i in range(Fg.shape[0]):
            row = solid[i]
            if row.any() and Fg[i, 0] <= f_front:
                idx = np.flatnonzero(row); filled[i, idx.min():idx.max() + 1] = True
        return ndimage.binary_closing(filled, iterations=4) | filled
    filled = {}
    for jaw in ("upper", "lower"):
        filled[jaw] = fill(foot[jaw] | band[jaw] | tongue_fp | back, float(ARCH[jaw][len(ARCH[jaw]) // 2, 0]))
        out[f"outer_{jaw}_sdf"] = (ndimage.gaussian_filter(_sdf2(filled[jaw]), 0.3 / PLAN_H) - VEST).astype(np.float32)
    out["filled"] = filled["upper"] | filled["lower"]
    # the oral proper (inside the lingual edges of both bands, and the throat entrance behind)
    lingual = np.zeros(Fg.shape, bool)
    for jaw in ("upper", "lower"):
        lingual |= (out[f"{jaw}_d"] > -(out[f"{jaw}_hw"] + band_x))      # on/outside the band's lingual edge
    proper = out["filled"] & ~lingual & ~foot["upper"] & ~foot["lower"]
    proper |= back & (Fg < fend - 0.5)
    proper = ndimage.binary_opening(proper, iterations=2)
    out["proper_sdf"] = ndimage.gaussian_filter(_sdf2(proper), 0.3 / PLAN_H).astype(np.float32)
    out["foot_upper"] = foot["upper"]; out["foot_lower"] = foot["lower"]; out["proper"] = proper
    for jaw in ("upper", "lower"):
        out[f"{jaw}_band"] = band[jaw]
    # crown height envelopes in plan: the lowest upper crown point and the highest lower crown point near (f, l)
    big = 1e3; lowU = np.full(Fg.shape, big); hiL = np.full(Fg.shape, -big)
    for t in TEETH:
        m = t["mesial"]; b = np.array([-m[1], m[0]]); dq = np.stack([Fg - t["base"][0], Lg - t["base"][1]], -1)
        x = dq @ m; y = dq @ b; reach = (np.hypot(x / (0.5 * t["L"] + 1.0), y / (0.5 * t["W"] + 1.0)) <= 1.0)
        tp = np.hypot(Fg - t["tip"][0], Lg - t["tip"][1]) < 1.6; reach |= tp
        if t["jaw"] == "upper":
            lowU[reach] = np.minimum(lowU[reach], t["tip"][2])
        else:
            hiL[reach] = np.maximum(hiL[reach], t["tip"][2])
    for A, bad in ((lowU, lowU > big - 1), (hiL, hiL < -big + 1)):        # no crown near: the nearest crown's value
        _, ind = ndimage.distance_transform_edt(bad, return_indices=True); A[bad] = A[tuple(ind)][bad]
    lowU = ndimage.gaussian_filter(ndimage.minimum_filter(lowU, 9), 0.4 / PLAN_H)
    hiL = ndimage.gaussian_filter(ndimage.maximum_filter(hiL, 9), 0.4 / PLAN_H)
    # the zones must overlap: the upper zone reaches down to min(lowU, hiL), the lower zone up to max(hiL, lowU)
    out["lowU"] = np.minimum(lowU, hiL).astype(np.float32); out["hiL"] = np.maximum(hiL, lowU).astype(np.float32)
    return out


PLAN = _build_plan()


def plan_sample(name, f, l, order=1):
    A = PLAN[name]; X = np.stack([(np.asarray(f) - PLAN_LO[0]) / PLAN_H, (np.asarray(l) - PLAN_LO[1]) / PLAN_H])
    return ndimage.map_coordinates(A, X.reshape(2, -1), order=order, mode="nearest").reshape(np.shape(f))


def palate_mid(f):
    return _interp(SPEC["palate"]["mid_u"], f)


def palate_halfwidth(f):
    """distance from the midline to the edge of the oral proper at f (plan)"""
    fi = np.clip(np.round((np.asarray(f) - PLAN_LO[0]) / PLAN_H).astype(int), 0, PLAN["proper"].shape[0] - 1)
    hw = _HW_PROPER[fi]; return hw


def _hw_proper():
    pr = PLAN["proper"]; nl = pr.shape[1]; mid = int(round(-PLAN_LO[1] / PLAN_H)); hw = np.zeros(pr.shape[0])
    for i in range(pr.shape[0]):
        row = pr[i]
        if row[mid]:
            k = mid
            while k + 1 < nl and row[k + 1]:
                k += 1
            hw[i] = (k - mid) * PLAN_H
    hw = np.maximum.accumulate(hw[::-1])[::-1] * 0 + hw                    # keep raw
    hw = ndimage.uniform_filter1d(np.maximum(hw, 0.5), 21)
    return hw


_HW_PROPER = _hw_proper()


def palate_u(f, l):
    """the palate's visible (lower) surface without rugae: the vault falls VAULT mm from the midline to the edge"""
    hw = np.maximum(palate_halfwidth(f), 3.0); x = np.clip(np.abs(l) / hw, 0, 1.0)
    return palate_mid(f) - SPEC["palate"]["vault_mm"] * x ** 2


def floor_u(f):
    return _interp(SPEC["floor"]["u"], f)


def gum_line(jaw, f, l):
    return plan_sample(f"{jaw}_ugum", f, l)


def fornix_rise(jaw, f):
    return _interp(SPEC["arch"]["fornix_rise_mm"][jaw], f)


# =============================================================== the cavity (skin-side), jaw frame then head
F_END = {jaw: float(ARCH[jaw][-1, 0]) for jaw in ("upper", "lower")}


def bag_heights(f, l):
    """the cavity's roof and floor at plan (f, l): BUCCAL/LABIAL of an arch's centre line the vestibule reaches that
    jaw's fornix (gum line +- fornix_rise); LINGUAL of it, and behind the teeth, the roof is the palate (+ PAL_EMBED, the
    palate mesh's top is buried there) and the floor is the floor of the mouth under the tongue"""
    wU = plan_sample("upper_wv", f, l); wL = plan_sample("lower_wv", f, l)
    top_v = gum_line("upper", f, l) + fornix_rise("upper", f); bot_v = gum_line("lower", f, l) - fornix_rise("lower", f)
    top_p = palate_u(f, l) + PAL_EMBED; bot_p = floor_u(f)
    return (1 - wU) * top_p + wU * top_v, (1 - wL) * bot_p + wL * bot_v
def cavity_jaw(J):
    """cavity SDF in skull-mm units (negative = air), J (N,3) jaw coords"""
    f, l, u = J[:, 0], J[:, 1], J[:, 2]
    # plan outline by height: the upper zone (down to the lowest upper crown) uses the upper outline, the lower zone (up
    # to the highest lower crown) the lower outline, their overlap the union; rounded where the zones change
    oU = plan_sample("outer_upper_sdf", f, l); oL = plan_sample("outer_lower_sdf", f, l)
    lowU = plan_sample("lowU", f, l); hiL = plan_sample("hiL", f, l)
    zU = round_int(oU, (lowU - VEST) - u, 0.5); zL = round_int(oL, u - (hiL + VEST), 0.5)
    outer = -smax(-zU, -zL, 0.4)
    top, bot = bag_heights(f, l)
    slab = np.maximum(u - top, bot - u)
    return round_int(outer, slab, BAG_R)


def _hidden_gap_tree(step=0.05):
    """dense points on v3's hidden-gap sheet per station (just outside the margin -> P0 -> P1), both sides"""
    pts = []
    for sd in ("L", "R"):
        G_ = GEOM[sd]
        for k in range(0, len(G_["s"])):
            U, n, b = G_["U"][k], G_["n"][k], G_["b"][k]
            a0 = np.array([G_["P0a"][k], 0.0]); a1 = a0 + G_["v"][k] * G_["eu2"][k]
            for A, B in ((np.array([0.5, 0.0]), a0), (a0, a1)):
                m = max(int(np.ceil(np.linalg.norm(B - A) / step)), 1); t = np.linspace(0, 1, m + 1)[:, None]; ah = A + t * (B - A)
                pts.append(U + ah[:, :1] * n + ah[:, 1:] * b)
    return cKDTree(np.vstack(pts))


HIDDEN = _hidden_gap_tree()


def cavity_sdf(P):
    """the oral cavity (head mm, negative = air): the mouth bag the skin lines, kept KEEPOUT mm off v3's hidden gap (the
    first full preview: the vestibule reached the gap at the corners, 1.5 mm gaps at L s 20 and the slot tip 0.77 mm from
    the R corner)"""
    P = np.asarray(P, float); c = cavity_jaw(to_jaw(P)) * S_JAW
    d, _ = HIDDEN.query(P, distance_upper_bound=KEEPOUT + 2.0)
    return np.maximum(c, np.where(np.isfinite(d), KEEPOUT - d, -10.0))


# =============================================================== the slot extension (the parting line through the lip)
def _cav_project(X, it=12):
    X = X.copy()
    for _ in range(it):
        g = np.zeros_like(X); h = 0.02
        for k in range(3):
            e = np.zeros(3); e[k] = h; g[:, k] = (cavity_sdf(X + e) - cavity_sdf(X - e)) / (2 * h)
        v = cavity_sdf(X); X -= (v / np.maximum((g * g).sum(1), 1e-9))[:, None] * g
    g = np.zeros_like(X)
    for k in range(3):
        e = np.zeros(3); e[k] = 0.02; g[:, k] = (cavity_sdf(X + e) - cavity_sdf(X - e)) / 0.04
    return X, _unit(g)


def _build_ext(step=0.035):
    """the parting sheet per station: U + 0.5 n (just outside the margin) -> P0 -> P1 -> P2 (v3's own slot sheet, made
    air where v3's nearest-U station rule sealed it) -> P3 (the cavity, PAST_WALL inside its wall); dense samples with
    their gap g, interpolated between stations so no sample is more than `step` from its neighbours"""
    out = {}
    for sd in ("L", "R"):
        G_ = GEOM[sd]; ns = len(G_["s"]); poly = np.zeros((ns, 5, 3))
        for k in range(ns):
            U, n, b = G_["U"][k], G_["n"][k], G_["b"][k]
            a0 = np.array([G_["P0a"][k], 0.0]); a1 = a0 + G_["v"][k] * G_["eu2"][k]; a2 = a1 - np.array([G_["D"][k], 0.0])
            for j, (aa, hh) in enumerate(((0.5, 0.0), tuple(a0), tuple(a1), tuple(a2))):
                poly[k, j] = U + aa * n + hh * b
        P2 = poly[:, 3].copy(); W, nW = _cav_project(P2)                     # nearest cavity-wall point, its normal
        P3 = W - PAST_WALL * nW
        k_ = max(int(EXT_SMOOTH / DS), 1); ker = np.exp(-0.5 * (np.arange(-3 * k_, 3 * k_ + 1) / k_) ** 2); ker /= ker.sum()
        P3s = np.stack([np.convolve(np.pad(P3[:, c], 3 * k_, mode="edge"), ker, "valid") for c in range(3)], 1)
        poly[:, 4] = P3s
        live = G_["g"] > 0.05
        out[sd] = dict(poly=poly, P2=P2, P1=poly[:, 2].copy(), P3=P3s, live=live, g=G_["g"].copy(), wall=W,
                       len=np.linalg.norm(P3s - P2, axis=1))
    pts, gs = [], []
    for sd in ("L", "R"):
        E = out[sd]; idx = np.flatnonzero(E["live"]); seg = np.linalg.norm(np.diff(E["poly"], axis=1), axis=2)
        Ltot = seg.sum(1); N = int(np.ceil(Ltot[idx].max() / step)) + 1; T = np.linspace(0, 1, N)
        R = np.zeros((len(idx), N, 3))
        for r, k in enumerate(idx):                                        # resample each polyline by arc fraction
            cum = np.r_[0, np.cumsum(seg[k])] / max(Ltot[k], 1e-9)
            for c in range(3):
                R[r, :, c] = np.interp(T, cum, E["poly"][k, :, c])
        for r in range(len(idx)):
            pts.append(R[r]); gs.append(np.full(N, E["g"][idx[r]]))
            if r + 1 < len(idx) and idx[r + 1] == idx[r] + 1:
                m = int(np.ceil(np.linalg.norm(R[r + 1] - R[r], axis=1).max() / step))
                for t in np.arange(1, m) / m:
                    pts.append(R[r] + t * (R[r + 1] - R[r])); gs.append(np.full(N, (1 - t) * E["g"][idx[r]] + t * E["g"][idx[r + 1]]))
    out["pts"] = np.vstack(pts); out["g"] = np.concatenate(gs); out["tree"] = cKDTree(out["pts"])
    out["max_len_mm"] = float(max(out[sd]["len"][out[sd]["live"]].max() for sd in ("L", "R")))
    return out


EXT = _build_ext()


def ext_air(P):
    """the parting line's continuation (head mm, negative = air): distance to the extension sheet minus g/2"""
    P = np.asarray(P, float); d, j = EXT["tree"].query(P, distance_upper_bound=3.0)
    out = np.full(len(P), 1e3); ok = np.isfinite(d); out[ok] = d[ok] - 0.5 * EXT["g"][j[ok]]; return out


# =============================================================== the v3 lip edit with the C1 chin (one change: fLL)
def _edit_side_v3b(q, F, G_):
    S = M3._section(q, G_); i, a, h, Z, g, v, P0, QA, dist2 = (S[k] for k in ("i", "a", "h", "Z", "g", "v", "P0", "QA", "dist2"))
    nl, eu = G_["nl2"][i], G_["eu2"][i]
    wB = (a - P0[:, 0]) * nl[:, 0] + (h - P0[:, 1]) * nl[:, 1]; uB = (a - P0[:, 0]) * eu[:, 0] + (h - P0[:, 1]) * eu[:, 1]
    dA = P0 - QA; crossA = dA[:, 0] * (h - QA[:, 1]) - dA[:, 1] * (a - QA[:, 0])
    lower = ((wB < 0) & (uB < v)) | ((wB >= 0) & (crossA >= 0))
    delta = np.where(lower, -dist2, dist2)
    dc = q - G_["C"][i]; dLL = (dc * G_["nLL"][i]).sum(1) + G_["lloff"][i]; hc = (dc * G_["eup"][i]).sum(1)
    Q = M3.Q_
    kLL = 0.2 + (Q["LL_K"] - 0.2) * ss((-hc - 0.5) / 1.5)
    plane = dLL + M3._ramp(-hc - Q["LL_H0"])
    f_v3 = smax(F, plane, kLL)                                                   # v3, unchanged
    # v3b, the C1 chin: below the contact C v3's receding plane still cut shallow scoops out of Tripo's chin where the
    # chin bulges (0.57 mm deep at the midline, z -24..-27.5) and left the chin through a kink (v3's M2 lines at the
    # midline, hc -2.3..-3.7). v3b FADES the cut out below C: fLL = F + w (f_v3 - F), w = 1 above hc = FADE[0] (v3
    # bitwise) -> 0 at hc = FADE[1], smoothstep, so the lower lip turns into Tripo's chin with no scoop and no crease
    w = ss((hc - CHIN_FADE[1]) / (CHIN_FADE[0] - CHIN_FADE[1]))
    fLL = np.where(w < 1, F + w * (f_v3 - F), f_v3)
    rm, lr = G_["r_m"][i], G_["low_r"][i]
    fup = smax(F, g / 2 - delta, rm); flo = smax(fLL, delta + g / 2, lr)
    out = Z * np.minimum(fup, flo) + (1 - Z) * F
    tc = M3._trees(G_)[1]; dcr, ic = tc.query(q); lc = G_["crease_l"][ic]
    out += M3.CREASE_D0 * np.clip(1 - lc / M3.CREASE_L, 0, 1) * np.exp(-(dcr / M3.CREASE_W) ** 2) * (dcr < 3 * M3.CREASE_W)
    return out


def lip_edit(P, F, chin=True, chunk=400000):
    """v3's lip edit (chin=False: exactly feat_mouth_v3.edit inside v3's region) with the v3b chin (chin=True)"""
    if not chin:
        return M3.edit(P, F)
    P = np.asarray(P, float); F = np.array(F, float, copy=True)
    lo, hi = M3.region(GEOM); idx = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
    for c0 in range(0, len(idx), chunk):
        ii = idx[c0:c0 + chunk]; q = P[ii]; f0 = F[ii]; x = q[:, 0] - MID_X; out = f0.copy()
        # v3 splits L / R at the midline (MID_W = 0): the two sides' geometry differs at s = 0 (P2 0.6 mm apart), which
        # leaves a vertical seam and a dimple down the lower lip and chin. v3b blends the two sides' fields linearly
        # over |x| < MID_BLEND (each side's construction is valid there), not a union (v3 run 1 lost the Y notch)
        wL = (x >= 0).astype(float)
        if MID_BLEND > 0:
            G0 = GEOM["L"]; hc0 = ((q - G0["C"][0]) * G0["eup"][0]).sum(1)              # height above the midline contact
            wM = ss((-0.3 - hc0) / 1.0)                                                  # 0 above C - 0.3, 1 below C - 1.3
            wL = (1 - wM) * wL + wM * ss((x + MID_BLEND) / (2 * MID_BLEND))
        mL = wL > 0; mR = wL < 1; fL = np.zeros(len(q)); fR = np.zeros(len(q))
        if mL.any():
            fL[mL] = _edit_side_v3b(q[mL], f0[mL], GEOM["L"])
        if mR.any():
            fR[mR] = _edit_side_v3b(q[mR], f0[mR], GEOM["R"])
        out = wL * fL + (1 - wL) * fR
        F[ii] = out
    return F


# =============================================================== REGION, edit, openings, zones
def _region():
    lo3, hi3 = M3.region(GEOM)
    c = PLAN["filled"]; Fg, Lg = PLAN["F"], PLAN["L"]; fs, ls = Fg[c], Lg[c]
    us = []
    for jaw in ("upper", "lower"):
        us.append(PLAN[f"{jaw}_ugum"][c])
    umax = float(np.max(us[0])) + 4.0; umin = float(np.min(us[1])) - 4.0
    umin = min(umin, float(np.min(floor_u(fs))) - 1.0)
    corners = np.array([[a, b, c_] for a in (fs.min(), fs.max()) for b in (ls.min(), ls.max()) for c_ in (umin, umax)])
    H = to_head(corners); lo = np.minimum(lo3, np.floor(H.min(0) - 2.5)); hi = np.maximum(hi3, np.ceil(H.max(0) + 2.5))
    E = EXT["pts"]; lo = np.minimum(lo, np.floor(E.min(0) - 2.0)); hi = np.maximum(hi, np.ceil(E.max(0) + 2.0))
    return lo, hi


REGION = _region()


def region(geom=None):
    return REGION


def edit(P_head_mm, F_mm, geom=None, chunk=400000):
    """the v3b mouth edit of the skin field; P (N,3) head-frame mm, F (N,) mm (negative inside) -> new F (N,)"""
    P = np.asarray(P_head_mm, float); F = np.array(F_mm, float, copy=True)
    lo, hi = REGION; idx = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
    for c0 in range(0, len(idx), chunk):
        ii = idx[c0:c0 + chunk]; q = P[ii]
        f = lip_edit(q, F[ii]); e = ext_air(q)
        f = np.maximum(f, -e); c = cavity_sdf(q)
        # the cavity is carved with a HARD max (a smooth max let the base field's internal near-zero seams, F ~ -0.1..-0.3
        # deep in the head, bulge the lining: first 0.10 mm preview), rounded with JOIN_K only where the parting line
        # enters the cavity (within 1 mm of the extension sheet)
        hard = np.maximum(f, -c); w = ss((1.0 - e) / 0.5)
        F[ii] = hard + w * (smax(f, -c, JOIN_K) - hard)
    return F


def opening_sdf(P, geom=None):
    """the INTENDED AIR of the mouth (mm, < 0 inside): v3's slot sheet + the parting-line extension + the oral cavity.
    fill_voids must never seal it (A20). NOTE for band selection: the cavity's deep interior is air far from any
    surface; use opening_shell_sdf (or |opening| < band) to choose fine nodes."""
    P = np.asarray(P, float); out = np.asarray(M3.opening_sdf(P), float).copy()
    lo, hi = REGION; b = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
    if len(b):
        q = P[b]; out[b] = np.minimum(out[b], np.minimum(ext_air(q), cavity_sdf(q)))
    return out


def opening_shell_sdf(P, shell=1.0):
    """opening_sdf restricted to a SHELL of the cavity (the slot and extension whole, the cavity only within `shell` mm
    of its wall): for selecting fine-evaluation nodes without filling the cavity's interior at 0.10 mm"""
    P = np.asarray(P, float); out = np.asarray(M3.opening_sdf(P), float).copy()
    lo, hi = REGION; b = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
    if len(b):
        q = P[b]; c = cavity_sdf(q); out[b] = np.minimum(out[b], np.minimum(ext_air(q), np.maximum(c, -c - shell)))
    return out


def parting_zone(P, pad=0.6):
    """True where v3b MEANS to add surface the v3 lip never had: the extension sheet and the cavity (+ pad mm)"""
    P = np.asarray(P, float); return (ext_air(P) < pad) | (cavity_sdf(P) < pad)


def chin_zone(P):
    """True where the C1 changes can move the surface: within the v3 tube, below the fade start (hc < FADE[0] + 0.2),
    or within MID_BLEND + 0.2 mm of the midline"""
    P = np.asarray(P, float); m = np.abs(P[:, 0] - MID_X) < MID_BLEND + 0.2
    for sd in ("L", "R"):
        G_ = GEOM[sd]; tU = M3._trees(G_)[0]; dist, i = tU.query(P)
        hc = ((P - G_["C"][i]) * G_["eup"][i]).sum(1); m |= (hc < CHIN_FADE[0] + 0.2) & (dist < G_["z_r"][i] + M3.Z_W)
    return m


def fix_zone(P, geom=None):
    """True where v3b MEANS to differ from v3 (for D6a 'lip form within 0.5 mm of v3 outside the fixed zones')"""
    return parting_zone(P) | chin_zone(P)


def probe_inputs(geom=None, stations=(2.0, 7.0, 12.0, 20.0)):
    return M3.probe_inputs(geom, stations)


def contract_probe(grid_mm):
    ok = grid_mm <= NEED_MM + 1e-9
    return dict(status="PASS" if ok else "FAIL", grid_mm=grid_mm, need_mm=NEED_MM, cap_mm=GRID_CAP_MM,
                why="REGION meshed at %.3f mm (need <= %.2f)" % (grid_mm, NEED_MM))


def registration_report():
    J = JAW; Ln = SPEC["teeth"]["upper"]
    p4 = [t for t in TEETH if t["name"] == "uP4.L"][0]; p4d = p4["base"][:2] - 0.5 * p4["L"] * p4["mesial"]
    p4d_h = to_head([p4d[0], p4d[1], p4["base"][2]]); import feat_eyes as FY
    dy = float(p4d_h[1] - FY.EYES["L"]["Cs"][1])
    return dict(scale=round(J["s"], 4), skull_length_mm=J["skull_length_mm"], ramos_range_mm=J["ramos_range_mm"],
                ramos_z=J["ramos_z"], residual_mm=J["residual_mm"], x_offset_removed_mm=J["x_offset_removed_mm"],
                O_head_mm=np.round(J["O"], 3).tolist(), axes_head=np.round(J["M"], 4).tolist(),
                tmj_head_mm={k: np.round(v, 2).tolist() for k, v in TMJ_HEAD_MM.items()},
                schellenberg_P4M1_junction_minus_globe_y_mm=round(dy, 2),
                schellenberg_gate="|dy| <= 1/2 P4 = %.1f mm (globe over P4 45 %% / M1 55 %%)" % (0.5 * p4["L"] * J["s"]),
                schellenberg_status="PASS" if abs(dy) <= 0.5 * p4["L"] * J["s"] else "FAIL",
                label="estimated (one skull, picked +-1 mm; eyes from feat_eyes)")


# =============================================================== the shared adaptive mesher (slabbed, welded)
def mesh_adaptive(fn, lo, hi, h, r=5, band=0.75, open_fn=None, open_band=0.5, border_air=True, slab_nodes=24e6, log=None,
                  mapper=None, chunk=250000):
    """mesh fn's zero set (fn: (N,3) -> F, negative inside) on [lo, hi]: a coarse grid h*r, exact fine nodes in coarse
    cells within `band` of the level set, with a sign change, or with |open_fn| < open_band (dilated one cell); the
    other fine nodes are the trilinear coarse field. Marched in x-slabs that share their seam plane (identical values),
    welded. border_air closes the crop. Returns V (N,3), F (M,3) int64 (outward), stats."""
    from skimage.measure import marching_cubes
    t0 = time.time(); lo = np.asarray(lo, float); H = h * r
    nc = np.floor((np.asarray(hi, float) - lo) / H + 1e-9).astype(int) + 1
    ax = [lo[d] + H * np.arange(nc[d]) for d in range(3)]
    Pc = np.stack(np.meshgrid(*ax, indexing="ij"), -1).reshape(-1, 3)
    mapper = mapper or (lambda g, xs: [g(x) for x in xs])
    Ec = np.concatenate(mapper(fn, [Pc[s0:s0 + chunk] for s0 in range(0, len(Pc), chunk)]))
    Ec = Ec.reshape(tuple(nc))
    Oc = None
    if open_fn is not None:
        Oc = np.empty(len(Pc))
        for s0 in range(0, len(Pc), 500000):
            Oc[s0:s0 + 500000] = open_fn(Pc[s0:s0 + 500000])
        Oc = Oc.reshape(tuple(nc))
    del Pc
    sh = lambda A, i, j, k: A[i:A.shape[0] - 1 + i, j:A.shape[1] - 1 + j, k:A.shape[2] - 1 + k]
    cmin = np.minimum.reduce([np.abs(sh(Ec, i, j, k)) for i in (0, 1) for j in (0, 1) for k in (0, 1)])
    sgn = [np.sign(sh(Ec, i, j, k)) for i in (0, 1) for j in (0, 1) for k in (0, 1)]
    act = (cmin < band) | (np.max(sgn, 0) != np.min(sgn, 0))
    if Oc is not None:
        omin = np.minimum.reduce([np.abs(sh(Oc, i, j, k)) for i in (0, 1) for j in (0, 1) for k in (0, 1)])
        act |= omin < open_band
    act = ndimage.binary_dilation(act, iterations=1); t1 = time.time()
    nf = (nc - 1) * r + 1; plane = nf[1] * nf[2]; cps = max(int(slab_nodes // (plane * r)), 1)
    Vs, Fs, base, n_exact = [], [], 0, 0
    for c0 in range(0, nc[0] - 1, cps):
        c1 = min(c0 + cps, nc[0] - 1); i0, i1 = c0 * r, c1 * r                     # fine planes i0..i1 inclusive
        ii = np.arange(i0, i1 + 1); X = np.stack(np.meshgrid(ii / r, np.arange(nf[1]) / r, np.arange(nf[2]) / r, indexing="ij"), 0)
        Ff = ndimage.map_coordinates(Ec, X.reshape(3, -1), order=1).reshape(len(ii), nf[1], nf[2]).astype(np.float32); del X
        # fine nodes of active cells (cells c0-1 .. c1 so the seam planes agree between slabs)
        a = act[max(c0 - 1, 0):min(c1 + 1, nc[0] - 1)]; ia = np.argwhere(a); ia[:, 0] += max(c0 - 1, 0)
        fm = np.zeros(Ff.shape, bool)
        for d0 in range(r + 1):
            gi = ia[:, 0] * r + d0 - i0; ok = (gi >= 0) & (gi < len(ii))
            for d1 in range(r + 1):
                for d2 in range(r + 1):
                    fm[gi[ok], ia[ok, 1] * r + d1, ia[ok, 2] * r + d2] = True
        idx = np.argwhere(fm); del fm; n_exact += len(idx)
        if len(idx):
            Ps = [lo + (idx[s0:s0 + chunk] + np.array([i0, 0, 0])) * h for s0 in range(0, len(idx), chunk)]
            Ff[tuple(idx.T)] = np.concatenate(mapper(fn, Ps)); del Ps
        del idx
        if border_air:
            if i0 == 0:
                Ff[0] = 10
            if i1 == nf[0] - 1:
                Ff[-1] = 10
            Ff[:, 0], Ff[:, -1], Ff[:, :, 0], Ff[:, :, -1] = 10, 10, 10, 10
        if np.nanmin(Ff) < 0 < np.nanmax(Ff):
            v, f, _, _ = marching_cubes(Ff, 0.0, spacing=(h,) * 3); v[:, 0] += i0 * h
            Vs.append(v); Fs.append(f[:, ::-1] + base); base += len(v)
        del Ff
        if log:
            log(f"slab {c0}-{c1}/{nc[0] - 1} exact {n_exact} verts {base} t {time.time() - t0:.0f}s")
    V = np.vstack(Vs) + lo; F = np.vstack(Fs).astype(np.int64)
    # weld seam-plane duplicates
    key = np.round((V - lo) / (h * 1e-3)).astype(np.int64)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True); inv = inv.ravel()
    first = np.full(inv.max() + 1, -1, np.int64); order = np.arange(len(V)); first[inv[::-1]] = order[::-1]
    V = V[first]; F = inv[F]; F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    # outward orientation: signed volume must be positive
    vol = np.einsum("ij,ij->i", V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6.0
    if vol < 0:
        F = F[:, ::-1]
    st = dict(coarse_mm=H, fine_mm=h, coarse_nodes=int(np.prod(nc)), fine_nodes=int(np.prod(nf)), exact_nodes=int(n_exact),
              exact_share=round(n_exact / float(np.prod(nf)), 4), verts=int(len(V)), tris=int(len(F)),
              welded=int((cnt > 1).sum()), t_coarse_s=round(t1 - t0, 1), t_total_s=round(time.time() - t0, 1))
    return V, F, st


# =============================================================== the preview crop (skin + v3b edit at 0.10 mm)
PREVIEW_FILE = os.path.join(LAYERS, "feat_mouth_v3b_preview.npz")


def preview_crop():
    """the v3 mouth crop (-23,-73,-34)..(24,-47,-15) grown to hold the cavity, the extension and the chin"""
    lo3, hi3 = np.array([-23.0, -73.0, -34.0]), np.array([24.0, -47.0, -15.0])
    lo = np.minimum(lo3, REGION[0] + 1.0); hi = np.maximum(hi3, REGION[1] - 1.0)
    lo = np.maximum(lo, np.array([-27.0, -76.0, -40.0])); hi = np.minimum(hi, np.array([28.0, -10.0, -6.0]))
    return np.floor(lo), np.ceil(hi)


_W = {}


def base_block(lo, hi):
    """the v2 PRE-edit 0.5 mm cores over a head-frame box as ONE array (as mouth_v3_preview.base_field builds it), so
    worker processes load a few MB instead of the cores"""
    sys.path.insert(0, os.path.join(ROOT, "tripo_rebuild"))
    import mouth_v3_preview as MP
    import partition as PT
    import skin_build as SB
    from skin_build_v3 import Coarse
    SB._init(0.0005, 0.001, 0.02); vc = 0.0005
    lo_eff = SB.G["lo"] + np.array([SB.JIT[0] * vc, SB.JIT[1] * vc, 0.0]); rs = SB.slab_ranges()
    lo = np.asarray(lo, float) - 1; hi = np.asarray(hi, float) + 1
    cor = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])])
    W = PT.HC + (cor / 1000) @ PT.HR.T
    i0 = np.floor((W.min(0) - lo_eff) / vc).astype(int) - 4; i1 = np.ceil((W.max(0) - lo_eff) / vc).astype(int) + 4
    sl = sorted({si for si, (j0, j1) in enumerate(rs) if j1 >= i0[1] - 3 and j0 <= i1[1] + 3})
    pre = Coarse([(rs[si][0], np.load(os.path.join(MP.V2_CORES, f"core_{si:03d}.npy"))) for si in sl])
    g = np.stack(np.meshgrid(*[np.arange(i0[d], i1[d] + 1) for d in range(3)], indexing="ij"), -1).reshape(-1, 3)
    pblk = pre.node(g).reshape(tuple(i1 - i0 + 1)).astype(np.float64)
    return dict(pblk=pblk, lo_blk=lo_eff + i0 * vc, vc=vc)


def base_fn(B):
    sys.path.insert(0, os.path.join(ROOT, "tripo_rebuild"))
    import partition as PT
    from skin_build_v3 import keys_cubic

    def Fbase(Phm):
        Wp = PT.HC + (np.asarray(Phm) / 1000) @ PT.HR.T; X = (Wp - B["lo_blk"]) / B["vc"]; out = np.empty(len(X))
        for s in range(0, len(X), 400000):
            out[s:s + 400000] = keys_cubic(B["pblk"], X[s:s + 400000]) * 1000
        return out
    return Fbase


def _winit(block_path, which):
    Z = np.load(block_path); _W["Fb"] = base_fn({k: Z[k] for k in ("pblk", "lo_blk", "vc")}); _W["which"] = which


def _weval(P):
    Fb = _W["Fb"]
    if _W["which"] == "v3b":
        return edit(P, Fb(P))
    if _W["which"] == "v3b_sealed":
        return sealed_field(edit(P, Fb(P)), P)
    if _W["which"] == "v3":
        return M3.edit(P, Fb(P))
    raise ValueError(_W["which"])


def run_preview(grid=0.10, which="v3b", workers=4):
    """the preview crop meshed at `grid` with `workers` processes (each holds the base block + this module, ~0.3 GB)"""
    sys.path.insert(0, os.path.join(ROOT, "tripo_rebuild"))
    import multiprocessing as mp
    import partition as PT
    lo, hi = preview_crop(); t0 = time.time()
    blk = os.path.join(os.environ.get("TEMP", LAYERS), "feat_mouth_v3b_baseblock.npz"); np.savez(blk, **base_block(lo, hi))
    with mp.get_context("spawn").Pool(workers, initializer=_winit, initargs=(blk, which)) as pool:
        V, F, st = mesh_adaptive(_weval, lo, hi, grid, r=int(round(0.5 / grid)), band=0.75, open_fn=opening_shell_sdf,
                                 open_band=0.5, log=lambda m: print(m, flush=True), mapper=lambda g, xs: pool.map(_weval, xs))
    border = np.any((V < lo + 2 * grid) | (V > hi - 2 * grid), axis=1)
    lab = label_vertices(V, F)
    fn_ = os.path.join(LAYERS, f"feat_mouth_{which}_preview{'' if grid <= 0.1 + 1e-9 else '_%03d' % round(grid * 1000)}.npz")
    N = _vn(V, F)
    np.savez_compressed(fn_, v=PT.HC + (V / 1000) @ PT.HR.T, f=F.astype(np.int32), n=N @ PT.HR.T, v_head_mm=V, border=border,
                        grid_mm=grid, label=lab,
                        label_names=np.array(["outer skin", "parting-line lining (lip mucosa)", "oral cavity lining (mucosa)"]),
                        note=f"feat_mouth_v3b {which} preview crop ({grid} mm, head frame {lo.tolist()}..{hi.tolist()}): v2 pre-edit "
                             f"cores (Keys) + the v3b edit at the fine nodes; world metres; crop closed by an air border")
    rep = dict(which=which, grid_mm=grid, crop_head_mm=[lo.tolist(), hi.tolist()], region_head_mm=[REGION[0].tolist(), REGION[1].tolist()],
               **st, border_verts=int(border.sum()), label_counts={int(k): int((lab == k).sum()) for k in (0, 1, 2)},
               ext_max_len_mm=round(EXT["max_len_mm"], 2), file=os.path.basename(fn_), t_wall_s=round(time.time() - t0, 1))
    json.dump(rep, open(fn_.replace(".npz", ".json"), "w"), indent=1); print(rep, flush=True); return rep


def sealed_field(F, P, t=0.3):
    """PLANTED failure (mouth_through / fill_voids, both sides): a solid membrane t mm thick, from 0.3 mm outside the
    cavity wall, closes the parting line's entrance into the cavity (what an unresolved slot leaves). A grid of spacing h
    sees it only if t > h (use t >= 2 h)"""
    c = cavity_sdf(P); return np.minimum(F, np.maximum(c - (0.3 + t), 0.3 - c))


def label_vertices(V, F):
    """0 outer skin, 1 parting-line lining (within 0.15 mm of v3's slot air or the extension sheet's air), 2 oral cavity
    lining: within 1 mm of the cavity wall AND facing into the cavity (normal . -grad cavity_sdf > 0.3), so small bumps
    of the lining are not mistaken for outer skin"""
    lab = np.zeros(len(V), np.int8); c = cavity_sdf(V); e = ext_air(V); s3 = np.asarray(M3.opening_sdf(V))
    lab[(s3 < 0.15) | (e < 0.15)] = 1
    near = np.flatnonzero(c < 1.0)
    if len(near):
        N = _vn(V, F)[near]; g = np.zeros((len(near), 3))
        for k in range(3):
            d = np.zeros(3); d[k] = 0.03; g[:, k] = (cavity_sdf(V[near] + d) - cavity_sdf(V[near] - d)) / 0.06
        g = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9); inward = (N * -g).sum(1) > 0.3
        lab[near[inward | (c[near] < 0.15)]] = 2
    return lab


def _vn(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "register"
    if cmd == "register":
        print(json.dumps(registration_report(), indent=1))
        print("ext max len", EXT["max_len_mm"], "REGION", REGION)
    elif cmd == "preview":
        for w in (sys.argv[3].split(",") if len(sys.argv) > 3 else ["v3b"]):
            run_preview(float(sys.argv[2]) if len(sys.argv) > 2 else 0.10, w, int(sys.argv[4]) if len(sys.argv) > 4 else 2)
