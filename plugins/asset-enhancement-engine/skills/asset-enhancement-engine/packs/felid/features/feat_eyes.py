"""EYES feature edit (felid pack, case cat1, Phase 2 Stage 3) - builder 'feat-eyes', 2026-10-18.

Built from spec_eyes.json with every BLOCKING item of check_eyes.json fixed (see FIXES below).
Head frame mm: x = the cat's LEFT, y = BACK (face points -y), z = UP. head mm = partition.head_local(world) * 1000
= (world - HC) @ HR * 1000; back to world: HC + (mm / 1000) @ HR.T (HR is a ROTATION, orthonormal - not the identity).

API
  edit(P_head_mm (N,3), F_mm (N,)) -> F_mm   skin field edit (negative inside), vectorised, chunked, touches REGION only
  REGION                                      {'L': (lo, hi), 'R': (lo, hi)} head-frame mm boxes the edit can change
  globe_field(P_head_mm, side)                the GLOBE (own closed object; never unioned into the skin)
  globe_mesh(side, vox)                       closed globe mesh, head-frame mm
  EYES[side]                                  geometry (centres, frame, margin polygon) used by the probes
  CORNEA_SAG_MM                               THE single cornea parameter (anatomical 5.70; see 'flatten' below)
  register_probes(globe_faces)                registers builder 'feat_eyes' + probe inputs in engine/checks/inventory_check

FIXES (check_eyes.json, blocking)
  B1 step-5 rounding sign: the free edge is rounded with a ROUNDED INTERSECTION (hg_sdf fOpIntersectionRound) of the
     lid top (h - H) and the cut face, which erodes-then-dilates (never grows). Only the ANTERIOR edge is rounded
     (should-fix 3); the posterior edge on the globe stays sharp, so the crease sits ON the margin polygon.
  B2 order: the socket (skin >= GAP from the globe) is carved LAST, after the lids and third eyelid are unioned.
  B3 third eyelid bounded: within TEL_REACH_MM of the medial canthus (hidden body included); probe on its extent.
  B4 probes that fail on a fused lid / unioned globe: see engine/checks/inventory_check.py (feat_eyes block) and
     feat_eyes_probes() here (globe own closed component, inner-face coverage, +-15 deg rotate clearance), each with
     planted failures run by the preview script.
  B5 C3 vs anatomy: default per ORCHESTRATOR_NOTES 05:22 (anatomical globe as its own object, C3 on the SKIN only);
     the cornea is ONE parameter CORNEA_SAG_MM; FLAT_SAG_MM puts the apex on Tripo's cap (person's 'no'); the probe
     'apex_to_envelope_mm' reports the chosen offset.
Should-fix done: lean ramp gives the 66 deg crease angle at every station (c(h) = h / (o tan 66)); isotropic margin
distance (3-D chord on the sclera sphere, scaled to height h) instead of the anisotropic atan2 (U,V); every value
carries a source / confidence in PARAMS; supraorbital whisker root zone handed off (SUPRAORBITAL).
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = json.load(open(os.path.join(HERE, "spec_eyes.json")))

# ------------------------------------------------------------------ parameters (value, source, confidence)
PARAMS = {
    "RS": (9.45, "spec globe_derivation (axial length 19.75 Konrade 2012, limbus 16.5 Carrington 1986)", "medium-low (derived)"),
    "LIMBUS_R": (8.25, "cited: cornea 16.5 mm (Carrington 1986 via cat-anatomy.md)", "medium"),
    "LIMBUS_BLEND": (0.8, "spec blend_radii.limbus; ESTIMATE (makes the limbal sulcus)", "low"),
    "GAP": (0.05, "spec lids.model contact gap; ESTIMATE", "low"),
    "H": (1.9, "spec lids.height_above_eye_surface.skin_on_this_globe (REVIEW_eyes B1 2.0-2.4 envelope, derived)", "medium-low"),
    "O_MID": (0.4, "REVIEW_eyes B2 overhang 0.3-0.5", "medium"),
    "O_MED": (1.0, "REVIEW_eyes B2 medial corner", "medium"),
    "O_LAT": (0.6, "REVIEW_eyes B2 lateral third 0.5-0.7", "medium"),
    "O_RAMP_DEG": (25.0, "spec step 3 'within 25 deg'; ESTIMATE", "low"),
    "CREASE_DEG": (66.0, "REVIEW_eyes S1 exact sections 64-69", "medium"),
    "EDGE_R": (0.45, "spec margin_edge_radius ESTIMATE (half the 1.0 mm photo margin thickness)", "low"),
    "LID_ZONE": (6.0, "spec step 4; ESTIMATE (wall top at 2.4 mm, REVIEW_eyes B1, plus the face run-out)", "low"),
    "LID_ZONE_K": (1.5, "spec blend_radii.lid_zone_fade; ESTIMATE", "low"),
    "LID_TO_SKIN_K": (1.0, "spec blend_radii.lid_to_skin; ESTIMATE (Tripo's profile turns > 60 deg at the wall top)", "low"),
    "TUNNEL_OFF": (1.0, "BUILDER: the old skin is cut 1 mm outside the margin so its cut wall lies INSIDE the lid "
                         "(spec tunnel at M=0 made the lid-to-skin smin bulge the crease 0.25 mm into the opening)", "estimate"),
    "TUNNEL_BACK": (0.5, "spec step 6; ESTIMATE", "low"),
    "TUNNEL_FRONT": (6.0, "spec step 6; ESTIMATE", "low"),
    "FORNIX_ROT_DEG": (15.0, "spec fornix_depth reason 'globe can rotate 15 deg'; ESTIMATE", "low"),
    "FORNIX_FROM": (0.5, "BUILDER: swept-globe clearance starts 0.5 mm under the lid, full at 1.5 mm; ESTIMATE", "estimate"),
    "TEL_T": (0.6, "spec third_eyelid thickness ESTIMATE 0.4-0.8", "low"),
    "TEL_EXPOSED": (0.5, "PHOTO L 0.4-0.7 mm; R by symmetry (flagged)", "low-medium"),
    "TEL_ARC_R": (6.0, "spec crescent arc ESTIMATE", "low"),
    "TEL_EDGE_R": (0.3, "spec leading-edge radius ESTIMATE", "low"),
    "TEL_REACH_MM": (4.0, "BUILDER (check_eyes B3): bounded to 4 mm from the medial canthus (spec text: ~3 mm along "
                          "the lower margin, ~1.5 mm upper, hidden body into the fornix)", "estimate"),
    "TEL_K": (0.2, "spec blend_radii.tel_to_skin; ESTIMATE", "low"),
}
P_ = {k: v[0] for k, v in PARAMS.items()}

# THE cornea parameter. Anatomical: 5.70 mm sag at the 8.25 mm limbus radius -> r 8.82 (keratometry, 73 cats).
# If the person says NO to the cornea standing ~1.2 mm in front of Tripo's painted cap: set CORNEA_SAG_MM = FLAT_SAG_MM
# (apex moved back by the spec's cornea_vs_tripo_cap median 1.23 / 1.15 mm -> sag 4.5 -> r 9.81).
CORNEA_SAG_MM = 5.70
FLAT_SAG_MM = 4.50
SOCKET_HARD = True   # BUILDER: the socket is a hard max; a smax(k=0.3) shifts the lid's inner face 0.075 mm off the globe


def cornea_geom(sag=None):
    sag = CORNEA_SAG_MM if sag is None else sag
    a, RS = P_["LIMBUS_R"], P_["RS"]
    zl = np.sqrt(RS ** 2 - a ** 2)                     # limbus plane in front of the sclera centre (4.61)
    rc = (a ** 2 + sag ** 2) / (2 * sag)               # cornea radius (8.82 at sag 5.70)
    dc = zl + sag - rc                                  # cornea centre in front of the sclera centre (1.49)
    return rc, dc, zl + sag


def _unit(x):
    x = np.asarray(x, float); return x / np.linalg.norm(x)


def _build_eye(side):
    e = SPEC["eyes"][f"eye.{side}"]; g = e["globe"]; fr = g["eye_frame"]
    Cs = np.array(g["sclera_sphere"]["centre_head_mm"], float)
    n = _unit(fr["n_axis"]); u = _unit(fr["u_lateral"]); u = _unit(u - (u @ n) * n); v = np.cross(n, u)
    if v @ np.array(fr["v_up"]) < 0:
        v = -v
    E = {"side": side, "Cs": Cs, "n": n, "u": u, "v": v}
    poly3 = np.array(e["lid_margin"]["outline_head_mm"], float)
    E["poly_sph"] = Cs + P_["RS"] * (poly3 - Cs) / np.linalg.norm(poly3 - Cs, axis=1)[:, None]   # margin on the sclera sphere
    E["poly_uv"] = _uv(E, poly3)
    E["centre_uv"] = E["poly_uv"].mean(0)
    for k in ("medial", "lateral"):
        E[k + "_uv"] = _uv(E, np.array([e["lid_margin"][k + "_canthus_head_mm"]], float))[0]
        E[k + "_head"] = np.array(e["lid_margin"][k + "_canthus_head_mm"], float)
    E["phi_med"] = np.arctan2(*(E["medial_uv"] - E["centre_uv"])[::-1])
    E["phi_lat"] = np.arctan2(*(E["lateral_uv"] - E["centre_uv"])[::-1])
    E["e_med"] = _unit(E["centre_uv"] - E["medial_uv"])
    # the third eyelid is anchored at the OPENING's medial tip (the margin polygon's most medial point along e_med):
    # the Phase 1 skin canthus lies 0.9-1.0 mm outside the polygon, so a crescent anchored there never enters the opening
    E["tel_tip_uv"] = E["poly_uv"][np.argmin((E["poly_uv"] - E["centre_uv"]) @ E["e_med"])]
    E["apex_spec"] = np.array(g["apex_head_mm"], float)
    reach = P_["RS"] * np.radians(100) + P_["LID_ZONE"] + 3.0      # nothing the edit changes lies beyond this
    E["box"] = (Cs - P_["RS"] - P_["TUNNEL_FRONT"] - 1.0, Cs + P_["RS"] + P_["TUNNEL_FRONT"] + 1.0)
    return E


def _uv(E, P):
    """azimuthal-equidistant map of the radial direction about the eye axis (mm of arc on the sclera sphere)"""
    q = P - E["Cs"]; w = q / np.maximum(np.linalg.norm(q, axis=1), 1e-9)[:, None]
    th = np.arccos(np.clip(w @ E["n"], -1, 1)); ph = np.arctan2(w @ E["v"], w @ E["u"])
    return P_["RS"] * th[:, None] * np.c_[np.cos(ph), np.sin(ph)]


EYES = {sd: _build_eye(sd) for sd in ("L", "R")}
REGION = {sd: (EYES[sd]["box"][0].tolist(), EYES[sd]["box"][1].tolist()) for sd in EYES}


# ------------------------------------------------------------------ SDF helpers
def smin(a, b, k):
    h = np.clip(k - np.abs(a - b), 0, None) / k; return np.minimum(a, b) - h * h * k / 4


def smax(a, b, k):
    return -smin(-a, -b, k)


def round_int(a, b, r):
    """rounded intersection (hg_sdf fOpIntersectionRound): rounds the convex edge with radius r, never grows"""
    return np.minimum(-r, np.maximum(a, b)) + np.sqrt(np.maximum(a + r, 0) ** 2 + np.maximum(b + r, 0) ** 2)


def _pip(uv, poly):
    """point in polygon (crossing number), vectorised over points"""
    x, y = uv[:, 0], uv[:, 1]; inside = np.zeros(len(uv), bool); m = len(poly)
    for i in range(m):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % m]
        c = (y0 > y) != (y1 > y)
        xi = x0 + (y - y0) * (x1 - x0) / np.where(y1 - y0 == 0, 1e-12, y1 - y0)
        inside ^= c & (x < xi)
    return inside


def globe_field(P, side, sag=None, rot=None):
    """G(p): sclera sphere smin cornea sphere (k LIMBUS_BLEND). rot = (axis, deg) rotates the globe about Cs."""
    E = EYES[side]; rc, dc, _ = cornea_geom(sag); n = E["n"]
    if rot is not None:
        ax = _unit(rot[0]); t = np.radians(rot[1])
        n = n * np.cos(t) + np.cross(ax, n) * np.sin(t) + ax * (ax @ n) * (1 - np.cos(t))
    q = P - E["Cs"]; zl = np.sqrt(P_["RS"] ** 2 - P_["LIMBUS_R"] ** 2)
    cor = np.maximum(np.linalg.norm(q - dc * n, axis=1) - rc, (zl - 1.0) - q @ n)   # cornea cap only in front (flat sag)
    return smin(np.linalg.norm(q, axis=1) - P_["RS"], cor, P_["LIMBUS_BLEND"])


def globe_swept(P, side, sag=None):
    """the globe swept over every rotation up to FORNIX_ROT_DEG about Cs (only the cornea moves): the fornix clearance"""
    E = EYES[side]; rc, dc, _ = cornea_geom(sag); q = P - E["Cs"]; r = np.linalg.norm(q, axis=1)
    al = np.arccos(np.clip((q @ E["n"]) / np.maximum(r, 1e-9), -1, 1)); a0 = np.radians(P_["FORNIX_ROT_DEG"])
    dcap = np.where(al <= a0, np.abs(r - dc), np.sqrt(np.maximum(r ** 2 + dc ** 2 - 2 * r * dc * np.cos(al - a0), 0)))
    zl = np.sqrt(P_["RS"] ** 2 - P_["LIMBUS_R"] ** 2)
    cor = np.maximum(dcap - rc, (zl - 1.0) * np.cos(a0) - r * np.cos(np.maximum(al - a0, 0)))
    return smin(r - P_["RS"], cor, P_["LIMBUS_BLEND"])


def margin_dist(P, side, chunk=60000):
    """M(p): signed distance (mm) from p's radial projection to the lid margin, + outside the opening (on the lid),
    measured as the 3-D chord on the sclera sphere (isotropic) and scaled by |q|/RS (lateral distance at height h)."""
    E = EYES[side]; q = P - E["Cs"]; r = np.linalg.norm(q, axis=1); w = q / np.maximum(r, 1e-9)[:, None]
    S = E["Cs"] + P_["RS"] * w; A = E["poly_sph"]; B = np.roll(A, -1, axis=0); AB = B - A; L2 = (AB ** 2).sum(1)
    d = np.empty(len(P))
    for s in range(0, len(P), chunk):
        X = S[s:s + chunk, None, :] - A[None]; t = np.clip((X * AB[None]).sum(2) / L2[None], 0, 1)
        d[s:s + chunk] = np.sqrt(((X - t[:, :, None] * AB[None]) ** 2).sum(2)).min(1)
    inside = _pip(_uv(E, P), E["poly_uv"])
    return np.where(inside, -d, d) * (r / P_["RS"])


def overhang(P, side):
    E = EYES[side]; uv = _uv(E, P) - E["centre_uv"]; ph = np.arctan2(uv[:, 1], uv[:, 0]); R = np.radians(P_["O_RAMP_DEG"])
    def near(p0):
        d = np.abs(np.angle(np.exp(1j * (ph - p0)))); return 0.5 * (1 + np.cos(np.pi * np.clip(d / R, 0, 1)))
    return P_["O_MID"] + (P_["O_MED"] - P_["O_MID"]) * near(E["phi_med"]) + (P_["O_LAT"] - P_["O_MID"]) * near(E["phi_lat"])


def eye_parts(P, side, sag=None, tel_reach=None, overhang_scale=1.0, H=None, margin_shift=0.0):
    """the pieces of the edit at points P (head mm): dict of h, M, Lid, TEL, tunnel, socket fields"""
    E = EYES[side]; H = P_["H"] if H is None else H
    h = globe_field(P, side, sag); M = margin_dist(P, side) + margin_shift
    o = overhang(P, side) * overhang_scale
    c = np.clip(h / np.maximum(o * np.tan(np.radians(P_["CREASE_DEG"])), 1e-6), 0, 1)
    cut = -(M + o * c)                                                      # lid where M > -o c(h): leans over the globe
    lid = round_int(h - H, cut, P_["EDGE_R"])                               # rounded ANTERIOR edge (never grows)
    lid = np.maximum(lid, P_["GAP"] - h)                                    # sharp posterior edge ON the globe
    lid = smax(lid, M - P_["LID_ZONE"], P_["LID_ZONE_K"])                   # fades into the face
    tunnel = np.maximum.reduce([M - P_["TUNNEL_OFF"], -h - P_["TUNNEL_BACK"], h - P_["TUNNEL_FRONT"]])
    # third eyelid: slab on the globe, crescent leading edge (rounded), bounded to the medial canthus
    uv = _uv(E, P); dmed = np.linalg.norm(uv - E["tel_tip_uv"], axis=1)
    cdisk = E["tel_tip_uv"] + (P_["TEL_EXPOSED"] + P_["TEL_ARC_R"]) * E["e_med"]
    Cr = P_["TEL_ARC_R"] - np.linalg.norm(uv - cdisk, axis=1)
    half = P_["TEL_T"] / 2; slab = np.abs(h - (P_["GAP"] + half)) - half
    tel = round_int(slab, Cr, min(P_["TEL_EDGE_R"], half))
    reach = P_["TEL_REACH_MM"] if tel_reach is None else tel_reach
    tel = np.maximum.reduce([tel, dmed - reach, M - 4.0])
    hs = globe_swept(P, side, sag)
    wf = np.clip((M - P_["FORNIX_FROM"]) / 1.0, 0, 1)                      # 0 at the margin -> 1 at 1.5 mm under the lid
    hsock = h * (1 - wf) + np.minimum(h, hs) * wf
    return {"h": h, "M": M, "lid": lid, "tel": tel, "tunnel": tunnel, "socket": P_["GAP"] - hsock}


def edit_side(P, F, side, **kw):
    pr = eye_parts(P, side, **kw)
    S1 = np.maximum(F, -pr["tunnel"])                           # remove the cap / envelope skin over the opening
    S3 = smin(S1, pr["lid"], P_["LID_TO_SKIN_K"])               # lids into the skin
    S3 = smin(S3, pr["tel"], P_["TEL_K"])                       # third eyelid
    return np.maximum(S3, pr["socket"]) if SOCKET_HARD else smax(S3, pr["socket"], 0.3)   # socket LAST (B2)


def edit(P_head_mm, F_mm, chunk=200000, **kw):
    """the skin-field edit: F (mm, negative inside) at head-frame mm points -> edited F. Only points inside REGION change."""
    P = np.asarray(P_head_mm, float); F = np.array(F_mm, float, copy=True)
    for sd in ("L", "R"):
        lo, hi = EYES[sd]["box"]; idx = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
        for s in range(0, len(idx), chunk):
            ii = idx[s:s + chunk]; F[ii] = edit_side(P[ii], F[ii], sd, **kw)
    return F


# ------------------------------------------------------------------ globe mesh (own closed object)
def globe_mesh(side, vox=0.15, sag=None):
    from skimage.measure import marching_cubes
    E = EYES[side]; rc, dc, apex = cornea_geom(sag); R = max(P_["RS"], apex) + 1.0
    lo = E["Cs"] - R; n = int(np.ceil(2 * R / vox)) + 1
    g = np.arange(n) * vox; X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
    P = np.c_[X.ravel(), Y.ravel(), Z.ravel()] + lo; del X, Y, Z
    G = globe_field(P, side, sag).reshape(n, n, n).astype(np.float32); del P
    v, f, _, _ = marching_cubes(G, 0.0, spacing=(vox,) * 3)
    v = v + lo
    # marching_cubes orientation: make normals point out of the globe
    c = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]); out = v[f].mean(1) - E["Cs"]
    if (np.einsum("ij,ij->i", c, out) < 0).mean() > 0.5:
        f = f[:, ::-1]
    return v, f.astype(np.int64)


# ------------------------------------------------------------------ C13 hand-off: supraorbital whisker roots
SUPRAORBITAL = {
    "what": "root zone for the superciliary (supraorbital) whiskers, 'a few long hairs over each eye' (Mivart 1881 via "
            "cat-hair-streams.md); a Stage 5 strand item. Kept CLEAR of this edit: it lies above the lid zone (M > LID_ZONE).",
    "zone_head_mm": {sd: {"centre": (EYES[sd]["Cs"] + (P_["RS"] + 3.0) * _unit(0.5 * EYES[sd]["n"] + EYES[sd]["v"]
                                                                         - 0.3 * EYES[sd]["u"])).round(2).tolist(),
                          "radius": 3.0} for sd in EYES},
    "confidence": "estimate (position from anatomy text only, above the medial upper lid); count 2-5 per side",
}


# ------------------------------------------------------------------ probes (feat_eyes)
def front_faces(gv, gf, side):
    """globe faces in front of the sclera centre (the eyelid_wrap probe flips all normals when their mean along the
    outward axis is < 0, which a full closed sphere can trigger: give it the front half)"""
    E = EYES[side]; return np.nonzero((gv[gf].mean(1) - E["Cs"]) @ E["n"] > 0)[0]


def register_probes(globe_faces, IC=None):
    """register builder 'feat_eyes' with inventory_check: globe_faces = {'L': face ids, 'R': face ids} in the mesh the
    check will read (skin + globes, head-frame mm)."""
    if IC is None:
        import importlib, sys
        sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "checks")))
        IC = importlib.import_module("inventory_check")
    inputs = {}
    for sd in ("L", "R"):
        E = EYES[sd]
        inputs[f"eyelid_wrap.{sd}"] = {"globe_faces": np.asarray(globe_faces[sd]).tolist(), "centre_mm": E["Cs"].tolist(),
                                       "outward": E["n"].tolist(), "axis": E["n"].tolist(), "radius_mm": 16.0}
        inputs[f"third_eyelid.{sd}"] = {"globe_faces": np.asarray(globe_faces[sd]).tolist(), "side": sd}
    IC.register("feat_eyes", [f"{p}.{sd}" for p in ("eyelid_wrap", "third_eyelid") for sd in ("R", "L")], inputs)
    return inputs


# ------------------------------------------------------------------ feature probes (field + mesh; head-frame mm)
def _sectors(P, side, ns=48):
    E = EYES[side]; uv = _uv(E, P) - E["centre_uv"]
    return ((np.arctan2(uv[:, 1], uv[:, 0]) + np.pi) / (2 * np.pi) * ns).astype(int) % ns


def probe_globe_closed(gv, gf):
    """the globe is its own CLOSED, single-component manifold (V - E + F = 2, every edge in exactly 2 faces)"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    e = np.sort(np.r_[gf[:, [0, 1]], gf[:, [1, 2]], gf[:, [2, 0]]], axis=1); ue, cnt = np.unique(e, axis=0, return_counts=True)
    nv = len(gv); used = np.unique(gf)
    A = coo_matrix((np.ones(len(ue)), (ue[:, 0], ue[:, 1])), shape=(nv, nv))
    ncomp = connected_components(A, directed=False)[0] - (nv - len(used))
    chi = len(used) - len(ue) + len(gf); ok = bool((cnt == 2).all() and ncomp == 1 and chi == 2)
    return {"status": "PASS" if ok else "FAIL", "components": int(ncomp), "euler": int(chi), "edges_not_2": int((cnt != 2).sum())}


def probe_skin_clear(sv, side, mark=None):
    """no SKIN vertex within GAP/2 of the globe (a globe unioned into the skin, or skin through the globe, FAILS)"""
    mark = P_["GAP"] / 2 if mark is None else mark
    E = EYES[side]; near = np.linalg.norm(sv - E["Cs"], axis=1) < P_["RS"] + 3; G = globe_field(sv[near], side)
    n = int((G < mark).sum())
    return {"status": "PASS" if n == 0 else "FAIL", "skin_vertices_on_or_in_globe": n,
            "min_h_mm": round(float(G.min()), 3) if len(G) else None, "mark_mm": mark}


def _globe_pts(gv, side, mlo, mhi):
    E = EYES[side]; M = margin_dist(gv, side); k = (M >= mlo) & (M <= mhi); P = gv[k]
    Nn = (P - E["Cs"]) / np.linalg.norm(P - E["Cs"], axis=1)[:, None]
    return P, Nn, M[k]


def probe_inner_face(Ffn, gv, side, mlo=0.3, mhi=4.0, reach=1.0, frac_mark=0.8, sect_mark=0.9):
    """a lid FOLD resting on a separate globe: at globe points under the lid (M 0.3-4 mm, the fornix) the skin field is
    OUTSIDE (> 0) on the globe surface and an inner face (F < 0) lies within `reach` mm along the globe normal.
    Per 48 stations the share of such samples >= 0.8 in >= 90 % of stations. A fused lid / unioned globe has F < 0 ON
    the globe and FAILS; a lid floating > 1 mm off the globe FAILS."""
    P, Nn, M = _globe_pts(gv, side, mlo, mhi); F0 = Ffn(P + 0.005 * Nn)
    Fm = np.min(np.stack([Ffn(P + t * Nn) for t in np.linspace(0.1, reach, 10)]), axis=0)
    good = (F0 > 0) & (Fm < 0); sec = _sectors(P, side); per = []
    for s in range(48):
        m = sec == s
        if m.sum() >= 5:
            per.append(float(good[m].mean()))
    per = np.array(per); frac = float((per >= frac_mark).mean()) if len(per) else 0.0
    return {"status": "PASS" if frac >= sect_mark else "FAIL", "stations": int(len(per)), "frac_stations_ok": round(frac, 3),
            "share_median": round(float(np.median(per)), 3) if len(per) else None,
            "on_globe_inside_skin_share": round(float((F0 <= 0).mean()), 4)}


def probe_rotate(Ffn, gv, side, deg=None, free_mark=0.35, fornix_mark=0.03, free_m=1.5):
    """+-15 deg rotations about u and v (the fornix's stated reason): penetration of the rotated globe into the skin.
    PASS: <= 0.03 mm (grid) where the rotated point lies > 1.5 mm under the lid, <= 0.35 mm at the free margin (lid
    compliance, ESTIMATE). A fused lid or a skin through the globe FAILS."""
    E = EYES[side]; deg = P_["FORNIX_ROT_DEG"] if deg is None else deg; rows = []
    M0 = margin_dist(gv, side); keep = M0 > -1.0
    for ax_name, ax in (("u", E["u"]), ("v", E["v"])):
        for sg in (1, -1):
            t = np.radians(sg * deg); q = gv[keep] - E["Cs"]; a = ax
            qr = q * np.cos(t) + np.cross(a, q) * np.sin(t) + np.outer(q @ a, a) * (1 - np.cos(t)); Pr = E["Cs"] + qr
            Fr = Ffn(Pr); Mr = margin_dist(Pr, side); pen = np.maximum(-Fr, 0)
            fx = Mr > free_m; fr = (Mr > -0.5) & ~fx
            rows.append({"rot": ("+" if sg > 0 else "-") + f"{deg:.0f} about {ax_name}",
                         "fornix_pen_max_mm": round(float(pen[fx].max()) if fx.any() else 0.0, 3),
                         "free_margin_pen_max_mm": round(float(pen[fr].max()) if fr.any() else 0.0, 3)})
    ok = all(r["fornix_pen_max_mm"] <= fornix_mark and r["free_margin_pen_max_mm"] <= free_mark for r in rows)
    return {"status": "PASS" if ok else "FAIL", "rotations": rows, "marks_mm": [fornix_mark, free_mark]}


def probe_crease(sv, side, tol=0.5, hmax=0.15):
    """crease = innermost skin vertex lying on the globe (|h| < 0.15) per station; |M| <= 0.5 at >= 90 % of 48 stations"""
    E = EYES[side]; near = np.linalg.norm(sv - E["Cs"], axis=1) < P_["RS"] + 3; P = sv[near]; h = globe_field(P, side)
    P = P[(h >= -hmax) & (h < hmax)]; M = margin_dist(P, side); P, M = P[np.abs(M) < 3], M[np.abs(M) < 3]
    sec = _sectors(P, side); cr = np.full(48, np.nan)
    for s in range(48):
        m = sec == s
        if m.any():
            cr[s] = M[m].min()
    okf = float(np.mean(np.abs(np.nan_to_num(cr, nan=9.0)) <= tol)); fin = np.isfinite(cr).any()
    return {"status": "PASS" if okf >= 0.9 else "FAIL", "frac_stations_ok": round(okf, 3),
            "crease_M_median_mm": round(float(np.nanmedian(cr)), 3) if fin else None,
            "crease_M_p10_p90": [round(float(np.nanpercentile(cr, q)), 3) for q in (10, 90)] if fin else None,
            "stations_with_crease": int(np.isfinite(cr).sum())}


def probe_lid_height(Ffn, gv, side, mlo=0.5, mhi=1.2, exp=None, tol=0.4):
    """lid height = where the solid that starts on the globe first EXITS, marching out along the globe normal, at globe
    points 0.5-1.2 mm under the lid (the flat lid top, past the 0.45 mm edge round); per station median; PASS when the
    median of stations is within 1.9 +- 0.4 and >= 80 % of stations are in tolerance (a brow above does not count)"""
    exp = P_["H"] if exp is None else exp
    P, Nn, M = _globe_pts(gv, side, mlo, mhi); ts = np.arange(0.1, 4.01, 0.05)
    Fl = np.stack([Ffn(P + t * Nn) for t in ts], 1); solid = Fl < 0; started = np.maximum.accumulate(solid, axis=1)
    ex = started & ~solid; first = np.where(ex.any(1), ts[np.argmax(ex, 1)] - 0.025, np.nan)
    h0 = globe_field(P, side); first = first + 0.0 * h0
    sec = _sectors(P, side); h = first; ok_ = np.isfinite(h)
    hh = np.array([np.nanmedian(h[(sec == s) & ok_]) for s in range(48) if ((sec == s) & ok_).sum() >= 3])
    if len(hh) == 0:
        return {"status": "FAIL", "why": "no lid vertices"}
    inn = float(np.mean(np.abs(hh - exp) <= tol)); med = float(np.median(hh))
    return {"status": "PASS" if abs(med - exp) <= tol and inn >= 0.8 else "FAIL", "median_mm": round(med, 3),
            "p10_p90": [round(float(np.percentile(hh, q)), 3) for q in (10, 90)], "frac_stations_ok": round(inn, 3), "expected": exp}


def _ray_to_globe(o, d, side, sag, hi=14.0):
    lo = 0.0
    for _ in range(60):
        mid = 0.5 * (lo + hi); g = globe_field((o + mid * d)[None], side, sag)[0]
        lo, hi = (mid, hi) if g < 0 else (lo, mid)
    return 0.5 * (lo + hi)


def probe_globe_shape(side, sag=None):
    """construction values of the globe field: corneal radius by circle fit (central +-4 mm, two axial sections),
    apex vs the spec, axial length, limbus diameter"""
    E = EYES[side]; rc, dc, apex = cornea_geom(sag); out = {}
    a_front = _ray_to_globe(E["Cs"], E["n"], side, sag); a_back = _ray_to_globe(E["Cs"], -E["n"], side, sag)
    out["apex_head_mm"] = (E["Cs"] + a_front * E["n"]).round(3).tolist()
    out["apex_vs_spec_mm"] = round(float(np.linalg.norm(E["Cs"] + a_front * E["n"] - E["apex_spec"])), 3)
    out["axial_length_mm"] = round(a_front + a_back, 3); fits = []
    for t in (E["u"], E["v"]):
        pts = []
        for a in np.radians(np.linspace(-25, 25, 21)):
            d = np.cos(a) * E["n"] + np.sin(a) * t; c0 = E["Cs"] + dc * E["n"]; p = c0 + _ray_to_globe(c0, d, side, sag) * d
            pts.append([(p - E["Cs"]) @ t, (p - E["Cs"]) @ E["n"]])
        pts = np.array(pts); keep = np.abs(pts[:, 0]) <= 4.0; x, y = pts[keep, 0], pts[keep, 1]
        sol = np.linalg.lstsq(np.c_[2 * x, 2 * y, np.ones(len(x))], x ** 2 + y ** 2, rcond=None)[0]
        fits.append(float(np.sqrt(sol[2] + sol[0] ** 2 + sol[1] ** 2)))
    out["corneal_radius_fit_mm"] = [round(r, 3) for r in fits]; out["limbus_diameter_mm"] = round(2 * P_["LIMBUS_R"], 2)
    zl = np.sqrt(P_["RS"] ** 2 - P_["LIMBUS_R"] ** 2); out["corneal_sag_mm"] = round(a_front - zl, 3)
    out["corneal_sag_cited_spread_mm"] = [5.0, 7.18]   # sag at r 9.31 / 8.33 (8.82 +- 0.49, PMC8437713) on the 8.25 mm limbus
    ok = all(abs(r - 8.82) <= 0.5 for r in fits) and out["apex_vs_spec_mm"] <= 0.5 and abs(out["axial_length_mm"] - 19.75) <= 0.3
    out["status"] = "PASS" if ok else "FAIL"
    return out
