"""DECISION CHECKS for cat v3 (A19; cases/cat1/NOTES_v3.md 2026-10-18 09:45 DECISIONS; V3_BRIEF 'The person's decisions,
each a check'). One check per decision the person made. Each runs at integration and is REPORTED FIRST. Each is proven
on planted failures on both sides (A22) in prove_cat_decisions.py.

All geometry is in the HEAD FRAME, mm (x = cat's left, y = back, z = up; partition.head_local(world) * 1000).

  D1 leather_top      approved nose-leather top edge vs skin v1 (person: "the best of every model we have so far").
                      v1's leather_top_zone core (u = 1) points -> exact distance to the candidate surface; outside the
                      tail-entry zones (balls of feat_nose.TAIL_ZONE_MM about each tail PATH, D2) max <= 0.2 mm.
  D2 nostril_tails    "Let the nostril tails cut into the approved corners where the photo shows them reaching the edge."
                      Tail path per side = open_end -> tail_tip (spec_nose, photo comma) -> the approved CORNER (the end
                      of the protected arc nearest the tail tip). On the corner leg (tail_tip -> corner, stopping 0.25 mm
                      short) the cut depth = inset of the candidate below v1 at the path, minus the median inset of v1
                      points 1.5-2.0 mm to either side (so a uniform lift or sink of the band cancels). PASS: median cut
                      in [0.15, 0.7] mm and the cut 0.5 mm before the corner >= 0.10 mm (spec groove depth 0.3-0.5 mm:
                      the gate is half its lower bound; 0.7 = upper bound + 0.2, no gouge).
  D3 ear_bulge        "The inner-ear bulge is baked hair ... It must be removed from the skin." The pinna is a thin
                      cupped sheet. Shell = the ear's own BACK face offset forward by the fitted sheet thickness (lower
                      envelope: per 1 mm height bin the 10th percentile of thickness, then a straight line in h). Thickness
                      at an inner-face vertex = distance to the nearest back-face vertex of the same ear. Bulge = thickness
                      - shell thickness. PASS per ear: p99 bulge <= 0.5 mm AND area with bulge > 0.5 mm <= 1.0 mm^2.
  D4 cornea           "eyeballs cornea may bulge past Tripo's flat painted eye - if that's what it's meant to do". The
                      cornea must match the CITED anatomy (feat_eyes PARAMS): corneal radius 8.82 +- 0.5 mm (keratometry,
                      73 cats, PMC8437713, SD 0.49), sag at the limbus in [5.0, 7.18] mm (that spread on the 8.25 mm
                      limbus), limbus diameter 16.5 +- 1.0 mm (Carrington 1986; tolerance ESTIMATE), axial length
                      19.75 +- 0.5 mm (Konrade 2012), cornea steeper than the sclera by >= 0.3 mm of radius. Fitted from
                      the mesh: sphere to the central +-4 mm cap, sphere to the back hemisphere, limbus = their
                      intersection circle. Not compared with Tripo: C3 applies to the skin only.
  D5 eye_optics       "we want the eyes to have real depth and color" (V3_BRIEF eye standard). Needs the EYE CONTRACT
                      below. E1 parts; E2 IORs (cornea 1.376, aqueous 1.336 +- 0.005); E3 chamber depth (cornea apex to the PUPIL
                      MARGIN, along the axis) = the declared, CITED value +- 0.3 mm and >= 1.0 mm; E4 rays traced from the view through the refracting cornea
                      reach the iris (>= 30 % of the rays entering the cornea) and the pupil (>= 1 %); E5 parallax: the
                      pupil's apparent centre shifts >= 0.3 mm between views 12 deg either side (a painted pupil: 0);
                      E6 iris colour recorded with dE00 vs the photo <= 3.0 (pigment_check's mark; *estimated* while the
                      camera is unvalidated) and iris-vs-sclera dE00 >= 10 (not a blank globe); E7 pupil size from the
                      photo, the built hole within 0.3 mm of the declared size.
  D6 lips             "the basic structure of the cat lips on the last version was impressive. just needs a little
                      refinement". (a) STRUCTURE: v2's upper-lip band (<= 2.5 mm from feat_mouth's U lines, on or above
                      the lip line) outside the FIXED ZONES (3 mm balls at the corners, the philtrum strip |x - mid| <
                      1.5 mm above the Y, a 2 mm ball at the Y) -> exact distance to the candidate: p99 <= 0.5 mm.
                      (b) the refinements pass: inventory parts upper_lip_overhang.R/L, mouth_crease, commissure.R/L,
                      lower_lip_chin, philtrum all PASS.
  D7 hair_and_fold    "Whiskers as real tactile hair, ear hair as its own types, and Henry's pocket as a real fold":
                      C13 (whisker_check pass), C14 (ear_hair_check status PASS), C6b (henrys_pocket.R and .L PASS).
                      A result that names the skin it was run on (skin_sha1) must match the candidate; one that names
                      none is labelled *estimated* (not bound to this skin).

EYE CONTRACT (D5; the v3 eye builder writes it, e.g. layers/cat_v3_eyes.npz). Per side s in L, R and part p in
cornea_front, cornea_back, iris, lens, sclera: arrays '<p>_<s>_v' (head mm) and '<p>_<s>_f'. The iris is an annulus whose
inner boundary IS the pupil. 'meta' is a JSON string:
  frame   {s: {centre, n (out of the eye), u (lateral), v (up)}}         ior {cornea, aqueous, lens}
  chamber {depth_mm: {s: x}, definition, source}                          view_dirs {s: [[x,y,z], ...]} (optional;
  iris    {s: {lab, dE00_photo, camera, camera_validated, texture}}         default: -n and +-12 deg yaw)
  pupil   {s: {size_mm: [width_u, height_v], shape, source}}              sclera_lab [L, a, b]
"""
import hashlib
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
TR = os.path.join(ROOT, "tripo_rebuild")
FEL = os.path.join(ROOT, "engine", "packs", "felid")
for _p in (TR, HERE, FEL, os.path.join(FEL, "features")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
LAYERS = os.path.join(TR, "layers")
V1_PATH = os.path.join(LAYERS, "skin_v1_person_approved_leather_top.npz")
V2_SKIN = os.path.join(LAYERS, "cat_p2_skin.npz")        # the assembled Phase 2 cat the person reviewed ("the last version")
V2_GLOBES = os.path.join(LAYERS, "cat_p2_globes.npz")

MARKS = {"leather_max_mm": 0.2, "tail_cut_min_mm": 0.15, "tail_cut_max_mm": 0.7, "tail_reach_min_mm": 0.10,
         "ear_bulge_p99_mm": 0.5, "ear_bulge_area_mm2": 1.0, "lip_p99_mm": 0.5, "iris_dE00": 3.0, "iris_vs_sclera_dE00": 10.0,
         "parallax_mm": 0.3, "chamber_tol_mm": 0.3, "chamber_min_mm": 1.0, "pupil_tol_mm": 0.3,
         "ior": {"cornea": 1.376, "aqueous": 1.336, "tol": 0.005},
         "cornea": {"r_mm": 8.82, "r_tol": 0.5, "sag_mm": [5.0, 7.18], "limbus_d_mm": 16.5, "limbus_tol": 1.0,
                    "axial_mm": 19.75, "axial_tol": 0.5, "steeper_by_mm": 0.3}}


def _unit(x):
    x = np.asarray(x, float); return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12)


def _r(x, n=4):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


# ------------------------------------------------------------------ meshes
class Skin:
    """a skin in the head frame (mm): P (N,3), f (M,3), N unit vertex normals (head frame), sha1 of the source file"""
    def __init__(self, P, f, N=None, label="", sha1=None):
        self.P = np.asarray(P, float); self.f = np.asarray(f, np.int64); self.label = label; self.sha1 = sha1
        self.N = vertex_normals(self.P, self.f) if N is None else _unit(N)

    @classmethod
    def load(cls, path, label=None):
        import partition as PT
        Z = np.load(path); v = Z["v"].astype(float); f = Z["f"].astype(np.int64)
        N = (Z["n"].astype(float) @ PT.HR) if "n" in Z.files else None
        return cls(PT.head_local(v) * 1000.0, f, N, label or os.path.basename(path), file_sha1(path))

    def crop(self, lo, hi):
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        ins = np.all((self.P >= lo) & (self.P <= hi), axis=1); keep = ins[self.f].all(1); fk = self.f[keep]
        idx = np.unique(fk); remap = -np.ones(len(self.P), np.int64); remap[idx] = np.arange(len(idx))
        return self.P[idx], remap[fk]


def file_sha1(path, block=1 << 22):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(block)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def vertex_normals(P, f):
    fn = np.cross(P[f[:, 1]] - P[f[:, 0]], P[f[:, 2]] - P[f[:, 0]]); N = np.zeros_like(P)
    for k in range(3):
        np.add.at(N, f[:, k], fn)
    return _unit(N)


def vertex_area(P, f):
    a = 0.5 * np.linalg.norm(np.cross(P[f[:, 1]] - P[f[:, 0]], P[f[:, 2]] - P[f[:, 0]]), axis=1); A = np.zeros(len(P))
    for k in range(3):
        np.add.at(A, f[:, k], a / 3.0)
    return A


def mesh_dist(P, f):
    from twosided import MeshDist
    return MeshDist(P, f, step=0.15, k=10)                  # mm units; (unsigned, signed: + = point OUTSIDE the mesh)


class Closest:
    """exact closest point + face normal on a mesh (KD-tree of centroids -> k candidate triangles)"""
    def __init__(self, P, f, k=10):
        self.P, self.f, self.k = P, f, k; self.tree = cKDTree(P[f].mean(1)); self.fn = _unit(np.cross(P[f[:, 1]] - P[f[:, 0]], P[f[:, 2]] - P[f[:, 0]]))

    def __call__(self, Q):
        from exact_sdf import closest_on_tri
        Q = np.atleast_2d(Q); _, nn = self.tree.query(Q, k=self.k); best = np.full(len(Q), np.inf)
        C = np.zeros_like(Q); Nn = np.zeros_like(Q); P, f = self.P, self.f
        for j in range(nn.shape[1]):
            t = nn[:, j]; c = closest_on_tri(Q, P[f[t, 0]], P[f[t, 1]], P[f[t, 2]]); d = np.linalg.norm(Q - c, axis=1)
            b = d < best; best = np.where(b, d, best); C[b] = c[b]; Nn[b] = self.fn[t[b]]
        return C, Nn, best


# ------------------------------------------------------------------ v1 reference (cached)
_V1 = {}


def v1_zone():
    """v1's approved leather-top zone points (head mm) and their weight u (skin_build.leather_top_zone)"""
    if not _V1:
        import coat_field as CF
        import partition as PT
        import skin_build as SB
        R = np.load(V1_PATH); rv = R["v"].astype(float); u = SB.leather_top_zone(rv, CF); z = u > 0
        _V1.update(Q=PT.head_local(rv[z]) * 1000.0, u=u[z])
    return _V1["Q"], _V1["u"]


def v1_nose():
    """v1's nose crop (feat_nose._load_ref: head mm, outward face normals) as a Skin"""
    import feat_nose as FN
    R = FN._load_ref(); return R["v"], R["f"]


def tail_paths():
    """per side: open_end -> tail_tip -> approved corner (the protected-arc end nearest the tail tip), head mm"""
    import feat_nose as FN
    out = {}
    for sd, S in FN.SIDES.items():
        ends = np.array([FN.ARC[0], FN.ARC[-1]]); c = ends[np.argmin(np.linalg.norm(ends - S.tail_tip, axis=1))]
        out[sd] = np.array([S.open_end, S.tail_tip, c], float)
    return out


def dist_to_path(Q, path):
    import feat_nose as FN
    d = np.full(len(Q), np.inf)
    for a, b in zip(path[:-1], path[1:]):
        d = np.minimum(d, FN.seg_dist(Q, a, b)[0])
    return d


def nose_box(pad=8.0):
    import feat_nose as FN
    return np.array(FN.REGION["lo_mm"]) - pad, np.array(FN.REGION["hi_mm"]) + pad


# ------------------------------------------------------------------ D1
def check_leather_top(skin):
    import feat_nose as FN
    Q, u = v1_zone(); core = u >= 1 - 1e-9
    excl = np.zeros(len(Q), bool)
    for path in tail_paths().values():
        excl |= dist_to_path(Q, path) < FN.TAIL_ZONE_MM
    Pc, fc = skin.crop(*nose_box()); _, sd = mesh_dist(Pc, fc)(Q); d = np.abs(sd)

    def st(m):
        if not m.any():
            return {"n": 0}
        return {"n": int(m.sum()), "p50_mm": _r(np.median(d[m])), "p95_mm": _r(np.percentile(d[m], 95)),
                "p99_mm": _r(np.percentile(d[m], 99)), "max_mm": _r(d[m].max()), "signed_p50_mm": _r(np.median(sd[m]))}
    m = core & ~excl; ok = bool(m.any() and d[m].max() <= MARKS["leather_max_mm"])
    return {"decision": "approved nose-leather top edge", "status": "PASS" if ok else "FAIL",
            "gate": f"max |d| over v1's core zone (u = 1) outside the tail-entry zones <= {MARKS['leather_max_mm']} mm",
            "core_outside_tail_zones": st(m), "core_inside_tail_zones (allowed to move)": st(core & excl),
            "blend_zone (info)": st(~core & ~excl), "label": "checked"}


# ------------------------------------------------------------------ D2
def check_nostril_tails(skin, ds=0.1):
    rv, rf = v1_nose(); cl = Closest(rv, rf)
    Pc, fc = skin.crop(*nose_box()); md = mesh_dist(Pc, fc)
    out = {"decision": "nostril tails cut into the approved corners", "sides": {}}
    allok = True
    for sd, path in tail_paths().items():
        seg = np.linalg.norm(np.diff(path, axis=0), axis=1); L = seg.sum(); s = np.arange(0, L - 0.25 + 1e-9, ds)
        cum = np.r_[0, np.cumsum(seg)]; X = np.c_[[np.interp(s, cum, path[:, k]) for k in range(3)]].T
        T = _unit(np.gradient(X, axis=0))
        Xs, Nn, _ = cl(X); lat = _unit(np.cross(Nn, T))
        _, ins = md(Xs); ring = []
        for o in (-2.0, -1.75, -1.5, 1.5, 1.75, 2.0):
            Xo, _, _ = cl(Xs + o * lat); ring.append(md(Xo)[1])
        cut = ins - np.median(np.array(ring), axis=0)
        entry = s >= cum[1]                                   # the corner leg: tail_tip -> corner (- 0.25 mm)
        med = float(np.median(cut[entry])); reach = float(np.interp(L - 0.5, s, cut))
        ok = MARKS["tail_cut_min_mm"] <= med <= MARKS["tail_cut_max_mm"] and reach >= MARKS["tail_reach_min_mm"]
        allok &= ok
        out["sides"][sd] = {"status": "PASS" if ok else "FAIL", "corner_leg_mm": _r(seg[1], 3),
                            "corner_head_mm": np.round(path[2], 2).tolist(), "median_cut_corner_leg_mm": _r(med),
                            "cut_0p5mm_before_corner_mm": _r(reach), "median_cut_groove_leg_mm (info)": _r(np.median(cut[~entry])),
                            "cut_profile_mm_every_0p5": np.round(cut[::5], 3).tolist()}
    out["status"] = "PASS" if allok else "FAIL"
    out["gate"] = (f"corner leg median cut in [{MARKS['tail_cut_min_mm']}, {MARKS['tail_cut_max_mm']}] mm and cut 0.5 mm "
                   f"before the corner >= {MARKS['tail_reach_min_mm']} mm, both sides")
    out["label"] = "checked (geometry); the corner as the photo's tail end is *estimated* (photo-side camera unvalidated)"
    return out


# ------------------------------------------------------------------ D3
def ear_frames():
    import partition as PT
    out = {}
    for sd in ("L", "R"):
        B = np.load(os.path.join(LAYERS, f"ears_base_{sd}.npz"))
        O = PT.head_local(B["origin"][None])[0] * 1000; A = _unit(B["axis"] @ PT.HR)
        l = _unit(B["lateral"] @ PT.HR); w = _unit(B["front"] @ PT.HR); tip = PT.head_local(B["tip"][None])[0] * 1000
        out[sd] = {"O": O, "A": A, "l": l, "w": w, "H": float((tip - O) @ A)}
    return out


def ear_bulge_one(P, f, N, E, h_lo=0.3, h_hi=0.85, r_max=30.0, nw_min=0.3):
    q = P - E["O"]; h = q @ E["A"]; rad = np.linalg.norm(q - np.outer(h, E["A"]), axis=1); nw = N @ E["w"]; H = E["H"]
    inner = (h >= h_lo * H) & (h <= h_hi * H) & (rad <= r_max) & (nw > nw_min)
    back = (h >= 0.2 * H) & (h <= 0.97 * H) & (rad <= r_max) & (nw < -nw_min)
    if inner.sum() < 50 or back.sum() < 50:
        return {"status": "FAIL", "why": f"ear faces not found (inner {int(inner.sum())}, back {int(back.sum())})"}
    t, _ = cKDTree(P[back]).query(P[inner]); hi_ = h[inner]
    edges = np.arange(np.floor(hi_.min()), np.ceil(hi_.max()) + 1, 1.0); hb, tb = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (hi_ >= a) & (hi_ < b)
        if m.sum() >= 10:
            hb.append(0.5 * (a + b)); tb.append(np.percentile(t[m], 10))
    hb, tb = np.array(hb), np.array(tb); keep = np.ones(len(hb), bool)
    for _ in range(3):                                         # lower envelope: drop bins far above the line, refit
        c = np.polyfit(hb[keep], tb[keep], 1); res = tb - np.polyval(c, hb); keep = res <= max(0.3, np.percentile(res, 75))
    shell = np.polyval(c, hi_); bulge = t - shell
    A = vertex_area(P, f)[inner]; over = float(A[bulge > MARKS["ear_bulge_p99_mm"]].sum())
    p99 = float(np.percentile(bulge, 99))
    ok = p99 <= MARKS["ear_bulge_p99_mm"] and over <= MARKS["ear_bulge_area_mm2"]
    return {"status": "PASS" if ok else "FAIL", "n_inner": int(inner.sum()), "n_back": int(back.sum()),
            "shell_thickness_mm_at_h_lo_hi": [_r(np.polyval(c, h_lo * H), 3), _r(np.polyval(c, h_hi * H), 3)],
            "bulge_p50_mm": _r(np.median(bulge), 3), "bulge_p99_mm": _r(p99, 3), "bulge_max_mm": _r(bulge.max(), 3),
            "area_bulge_over_0p5mm_mm2": _r(over, 2), "inner_area_mm2": _r(A.sum(), 1),
            "worst_head_mm": np.round(P[inner][np.argmax(bulge)], 2).tolist(), "_bulge": bulge, "_inner": np.nonzero(inner)[0]}


def check_ear_bulge(skin, frames=None):
    frames = frames or ear_frames(); out = {"decision": "inner-ear bulge (baked hair) removed", "ears": {}}
    lo = np.min([E["O"] - 60 for E in frames.values()], 0); hi = np.max([E["O"] + 60 for E in frames.values()], 0)
    ins = np.all((skin.P >= lo) & (skin.P <= hi), axis=1); keep = ins[skin.f].all(1); fk = skin.f[keep]
    idx = np.unique(fk); remap = -np.ones(len(skin.P), np.int64); remap[idx] = np.arange(len(idx))
    P, f, N = skin.P[idx], remap[fk], skin.N[idx]
    for sd, E in frames.items():
        r = ear_bulge_one(P, f, N, E); r.pop("_bulge", None); r.pop("_inner", None); out["ears"][sd] = r
    out["status"] = "PASS" if all(r["status"] == "PASS" for r in out["ears"].values()) else "FAIL"
    out["gate"] = (f"per ear p99 bulge <= {MARKS['ear_bulge_p99_mm']} mm and area over 0.5 mm <= {MARKS['ear_bulge_area_mm2']} mm^2;"
                   " shell = back face + fitted sheet thickness (lower envelope, linear in h)")
    out["label"] = "checked"
    return out


# ------------------------------------------------------------------ D4
def _sphere_fit(X):
    A = np.c_[2 * X, np.ones(len(X))]; b = (X ** 2).sum(1); s = np.linalg.lstsq(A, b, rcond=None)[0]
    c = s[:3]; return c, float(np.sqrt(s[3] + c @ c)), float(np.sqrt(np.mean((np.linalg.norm(X - c, axis=1) - np.sqrt(s[3] + c @ c)) ** 2)))


def measure_cornea(P, Cs, n):
    q = P - Cs; ax = q @ n; rad = np.linalg.norm(q - np.outer(ax, n), axis=1)
    front = (ax > 0) & (rad <= 4.0); back = ax < -2.0
    if front.sum() < 20 or back.sum() < 20:
        return {"status": "FAIL", "why": "globe surface not found about the eye frame"}
    cc, rc, rms_c = _sphere_fit(P[front]); cs, RS, rms_s = _sphere_fit(P[back])
    D = float(np.linalg.norm(cc - cs)); x = (D ** 2 + RS ** 2 - rc ** 2) / (2 * D) if D > 1e-6 else np.nan
    a = float(np.sqrt(max(RS ** 2 - x ** 2, 0))) if np.isfinite(x) else np.nan
    sag = D + rc - x if np.isfinite(x) else 0.0
    apex = ax[rad < 0.8].max() if (rad < 0.8).any() else ax.max(); pole = ax[rad < 0.8].min() if (rad < 0.8).any() else ax.min()
    M = MARKS["cornea"]
    cl = {"radius": abs(rc - M["r_mm"]) <= M["r_tol"], "sag": M["sag_mm"][0] <= sag <= M["sag_mm"][1],
          "limbus": np.isfinite(a) and abs(2 * a - M["limbus_d_mm"]) <= M["limbus_tol"],
          "axial": abs((apex - pole) - M["axial_mm"]) <= M["axial_tol"], "steeper_than_sclera": rc <= RS - M["steeper_by_mm"]}
    return {"status": "PASS" if all(cl.values()) else "FAIL", "clauses": {k: bool(v) for k, v in cl.items()},
            "corneal_radius_mm": _r(rc, 3), "cornea_fit_rms_mm": _r(rms_c, 4), "sclera_radius_mm": _r(RS, 3),
            "sag_mm": _r(sag, 3), "limbus_diameter_mm": _r(2 * a, 3), "axial_length_mm": _r(apex - pole, 3)}


def globe_sides(path_or_arrays):
    """{side: verts head mm} from cat_p2_globes.npz (v world m, face_side) or a v3 eye npz (cornea_front + sclera parts)"""
    import partition as PT
    Z = np.load(path_or_arrays) if isinstance(path_or_arrays, str) else path_or_arrays
    files = Z.files if hasattr(Z, "files") else list(Z.keys())
    if "cornea_front_L_v" in files:
        return {sd: np.vstack([Z[f"cornea_front_{sd}_v"], Z[f"sclera_{sd}_v"]]).astype(float) for sd in ("L", "R")}
    v = PT.head_local(Z["v"].astype(float)) * 1000; f = Z["f"]; side = Z["face_side"]; out = {}
    for k, sd in ((0, "L"), (1, "R")):
        out[sd] = v[np.unique(f[side == k])]
    return out


def check_cornea(globes):
    import feat_eyes as FY
    G = globe_sides(globes); out = {"decision": "anatomical cornea (may bulge past Tripo's flat eye)", "eyes": {}}
    for sd in ("L", "R"):
        E = FY.EYES[sd]; out["eyes"][sd] = measure_cornea(G[sd], E["Cs"], E["n"])
    out["status"] = "PASS" if all(r["status"] == "PASS" for r in out["eyes"].values()) else "FAIL"
    M = MARKS["cornea"]
    out["gate"] = (f"corneal radius {M['r_mm']} +- {M['r_tol']} (PMC8437713), sag {M['sag_mm']}, limbus {M['limbus_d_mm']} +- "
                   f"{M['limbus_tol']} (Carrington 1986), axial {M['axial_mm']} +- {M['axial_tol']} (Konrade 2012), steeper than sclera")
    out["label"] = "checked (geometry vs cited anatomy; the eye frame is spec_eyes')"
    return out


# ------------------------------------------------------------------ D5 (ray tracing through the refracting cornea)
def ray_mesh(O, D, V, F, chunk=96):
    """Moller-Trumbore: nearest hit t > 1e-6 per ray (inf if none) and the face index"""
    v0 = V[F[:, 0]]; e1 = V[F[:, 1]] - v0; e2 = V[F[:, 2]] - v0
    T = np.full(len(O), np.inf); I = -np.ones(len(O), np.int64)
    for a in range(0, len(O), chunk):
        o, d = O[a:a + chunk, None, :], D[a:a + chunk, None, :]
        p = np.cross(d, e2[None]); det = np.einsum("rtk,tk->rt", p, e1); ok = np.abs(det) > 1e-12; inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
        s = o - v0[None]; u = np.einsum("rtk,rtk->rt", s, p) * inv; qv = np.cross(s, e1[None])
        w = np.einsum("rtk,rtk->rt", d, qv) * inv; t = np.einsum("tk,rtk->rt", e2, qv) * inv
        hit = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 1e-6); t = np.where(hit, t, np.inf)
        j = np.argmin(t, axis=1); T[a:a + chunk] = t[np.arange(len(j)), j]; I[a:a + chunk] = np.where(np.isfinite(T[a:a + chunk]), j, -1)
    return T, I


def refract(d, nrm, n1, n2):
    nrm = np.where((np.einsum("ij,ij->i", d, nrm) > 0)[:, None], -nrm, nrm); eta = np.broadcast_to(np.asarray(n1, float) / n2, (len(d),))
    ci = -np.einsum("ij,ij->i", d, nrm); k = 1 - eta ** 2 * (1 - ci ** 2)
    out = eta[:, None] * d + (eta * ci - np.sqrt(np.maximum(k, 0)))[:, None] * nrm
    return _unit(out), k >= 0


def trace_eye(parts, ior, vd, apex, spacing=0.4, radius=8.5):
    """rays along vd (camera -> eye) over a disc about the apex. Returns class per ray (0 miss cornea, 1 iris, 2 pupil/lens,
    3 sclera, 4 lost) and the cornea entry points"""
    vd = _unit(vd); a = _unit(np.cross(vd, [0, 0, 1.0] if abs(vd[2]) < 0.9 else [1.0, 0, 0])); b = np.cross(vd, a)
    g = np.arange(-radius, radius + 1e-9, spacing); X, Y = np.meshgrid(g, g); m = X ** 2 + Y ** 2 <= radius ** 2
    O = apex - 30 * vd + X[m][:, None] * a + Y[m][:, None] * b; D = np.tile(vd, (len(O), 1))
    fn = {k: _unit(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])) for k, (V, F) in parts.items()}
    cls = np.zeros(len(O), np.int8); t, i = ray_mesh(O, D, *parts["cornea_front"]); ent = np.isfinite(t)
    entry = O + np.where(ent, t, 0)[:, None] * D
    P = entry[ent]; d, okr = refract(D[ent], fn["cornea_front"][i[ent]], 1.0, ior["cornea"]); idx = np.nonzero(ent)[0]
    medium = np.full(len(idx), ior["cornea"])
    for step in range(3):
        best = np.full(len(idx), np.inf); who = np.full(len(idx), "", object); face = -np.ones(len(idx), np.int64)
        for k in ("cornea_back", "iris", "lens", "sclera"):
            tk, ik = ray_mesh(P, d, *parts[k]); b_ = tk < best; best = np.where(b_, tk, best); who[b_] = k; face[b_] = ik[b_]
        done = np.zeros(len(idx), bool)
        for k, c in (("iris", 1), ("lens", 2), ("sclera", 3)):
            mk = who == k; cls[idx[mk]] = c; done |= mk
        cls[idx[~np.isfinite(best)]] = 4; done |= ~np.isfinite(best)
        cb = (who == "cornea_back") & ~done
        if not cb.any():
            break
        Pn = P[cb] + best[cb][:, None] * d[cb]; dn, _ = refract(d[cb], fn["cornea_back"][face[cb]], medium[cb], ior["aqueous"])
        idx, P, d, medium = idx[cb], Pn, dn, np.full(cb.sum(), ior["aqueous"])
    return cls, entry, ent, (a, b)


def _meta(Z):
    try:
        return json.loads(str(Z["meta"]))
    except Exception:  # noqa: BLE001
        return None


def check_eye_optics(eye_npz):
    from skimage.color import deltaE_ciede2000
    Z = np.load(eye_npz) if isinstance(eye_npz, str) else eye_npz; files = Z.files if hasattr(Z, "files") else list(Z.keys())
    out = {"decision": "eyes with real depth and colour", "eyes": {}}
    need = ("cornea_front", "cornea_back", "iris", "lens", "sclera")
    meta = _meta(Z) if "meta" in files else None
    I = MARKS["ior"]
    for sd in ("L", "R"):
        r = {"clauses": {}}
        miss = [p for p in need if f"{p}_{sd}_v" not in files or len(Z[f"{p}_{sd}_v"]) == 0]
        r["clauses"]["E1_parts"] = not miss
        if miss or meta is None:
            r["why"] = f"missing parts {miss}" + ("; no meta (materials, chamber, iris colour, pupil)" if meta is None else "")
            for k in ("E2_ior", "E3_chamber_depth", "E4_iris_pupil_visible_through_cornea", "E5_parallax", "E6_colour", "E7_pupil"):
                r["clauses"][k] = False
            r["status"] = "FAIL"; out["eyes"][sd] = r; continue
        parts = {p: (Z[f"{p}_{sd}_v"].astype(float), Z[f"{p}_{sd}_f"].astype(np.int64)) for p in need}
        fr = meta["frame"][sd]; C = np.array(fr["centre"], float); n = _unit(fr["n"]); u = _unit(fr["u"]); v = _unit(fr["v"])
        ior = meta.get("ior", {}); r["ior"] = ior
        r["clauses"]["E2_ior"] = (abs(ior.get("cornea", 0) - I["cornea"]) <= I["tol"]) and (abs(ior.get("aqueous", 0) - I["aqueous"]) <= I["tol"])
        cf = parts["cornea_front"][0]; apex_ax = float(((cf - C) @ n).max()); apex = C + apex_ax * n
        Vi, Fi = parts["iris"]; e = np.sort(np.vstack([Fi[:, [0, 1]], Fi[:, [1, 2]], Fi[:, [2, 0]]]), axis=1)
        ue, cnt = np.unique(e, axis=0, return_counts=True); bv = np.unique(ue[cnt == 1])
        rr = np.linalg.norm((Vi[bv] - C) - np.outer((Vi[bv] - C) @ n, n), axis=1); thr = 0.5 * (rr.min() + rr.max()) if len(rr) else 0
        hole = Vi[bv[rr < thr]] if len(rr) and rr.max() - rr.min() > 0.5 else np.zeros((0, 3))
        # depth of the PUPIL MARGIN behind the cornea apex (the iris body if there is no hole): a painted iris reads ~0
        iris_ax = float(np.median(((hole if len(hole) else Vi) - C) @ n)); depth = apex_ax - iris_ax
        ch = meta.get("chamber", {}); dd = (ch.get("depth_mm") or {}).get(sd)
        r["chamber_depth_measured_mm"] = _r(depth, 3); r["chamber_depth_declared_mm"] = dd; r["chamber_source"] = ch.get("source")
        r["clauses"]["E3_chamber_depth"] = bool(dd is not None and ch.get("source") and abs(depth - dd) <= MARKS["chamber_tol_mm"]
                                                and depth >= MARKS["chamber_min_mm"])
        trace_ior = {"cornea": ior.get("cornea", 1.0), "aqueous": ior.get("aqueous", 1.0)}
        vds = (meta.get("view_dirs") or {}).get(sd)
        yaw = lambda deg: _unit(np.cos(np.radians(deg)) * (-n) + np.sin(np.radians(deg)) * u)  # noqa: E731
        main = _unit(vds[0]) if vds else -n
        cls, entry, ent, _ = trace_eye(parts, trace_ior, main, apex)
        ne = max(int(ent.sum()), 1); f_iris = float((cls == 1).sum() / ne); f_pupil = float((cls == 2).sum() / ne)
        r["rays_entering_cornea"] = int(ent.sum()); r["frac_iris"] = _r(f_iris, 3); r["frac_pupil"] = _r(f_pupil, 3)
        r["frac_sclera"] = _r(float((cls == 3).sum() / ne), 3)
        r["clauses"]["E4_iris_pupil_visible_through_cornea"] = f_iris >= 0.30 and f_pupil >= 0.01
        cen = []
        for deg in (-12.0, 12.0):
            vd = yaw(deg); c2, e2, _, (a_, b_) = trace_eye(parts, trace_ior, vd, apex, spacing=0.25, radius=4.5)
            pc = e2[c2 == 2]
            cen.append(np.nan if not len(pc) else float(((pc.mean(0) - apex) @ a_)))
        par = abs(cen[1] - cen[0]) if np.all(np.isfinite(cen)) else 0.0
        r["parallax_mm"] = _r(par, 3); r["clauses"]["E5_parallax"] = par >= MARKS["parallax_mm"]
        ir = (meta.get("iris") or {}).get(sd) or {}; lab = ir.get("lab"); dE = ir.get("dE00_photo"); scl = meta.get("sclera_lab")
        dsc = float(deltaE_ciede2000(np.array([lab], float), np.array([scl], float))[0]) if (lab and scl) else 0.0
        r["iris_lab"] = lab; r["iris_dE00_photo"] = dE; r["iris_vs_sclera_dE00"] = _r(dsc, 2)
        r["iris_camera"] = ir.get("camera"); r["iris_camera_validated"] = bool(ir.get("camera_validated"))
        r["clauses"]["E6_colour"] = bool(lab is not None and isinstance(dE, (int, float)) and dE <= MARKS["iris_dE00"]
                                         and dsc >= MARKS["iris_vs_sclera_dE00"])
        pu = (meta.get("pupil") or {}).get(sd) or {}; ps = pu.get("size_mm")
        if len(hole):
            meas = [float(np.ptp((hole - C) @ u)), float(np.ptp((hole - C) @ v))]
        else:
            meas = [0.0, 0.0]
        r["pupil_measured_mm"] = [round(x, 3) for x in meas]; r["pupil_declared_mm"] = ps; r["pupil_source"] = pu.get("source")
        r["clauses"]["E7_pupil"] = bool(ps and "photo" in str(pu.get("source", "")).lower() and len(hole)
                                        and max(abs(meas[0] - ps[0]), abs(meas[1] - ps[1])) <= MARKS["pupil_tol_mm"])
        r["clauses"] = {k: bool(x) for k, x in r["clauses"].items()}
        r["status"] = "PASS" if all(r["clauses"].values()) else "FAIL"
        out["eyes"][sd] = r
    out["status"] = "PASS" if all(r["status"] == "PASS" for r in out["eyes"].values()) else "FAIL"
    out["label"] = ("checked (geometry, declared materials, traced visibility); colour clause *estimated* while the photo "
                    "camera fails its hold-out; the render through the photo camera is the eye builder's acceptance, not this check")
    return out


# ------------------------------------------------------------------ D6
def lip_zone(ref):
    import feat_mouth as FM
    G = FM.GEOM; U = np.vstack([G[sd]["U"] for sd in ("L", "R")]); tr = cKDTree(U)
    corners = np.array([G[sd]["C"][-1] for sd in ("L", "R")], float); Y = np.asarray(FM.Y_HEAD_MM(G), float)
    lo, hi = U.min(0) - 6, U.max(0) + 6; box = np.all((ref.P >= lo) & (ref.P <= hi), axis=1); idx = np.nonzero(box)[0]
    P = ref.P[idx]; d, i = tr.query(P)
    band = (d <= 2.5) & (P[:, 2] >= U[i, 2] - 0.25)
    corner = np.min(np.linalg.norm(P[:, None] - corners[None], axis=2), axis=1) < 3.0
    phil = (np.abs(P[:, 0] - FM.MID_X) < 1.5) & (P[:, 2] >= Y[2] - 0.5)
    yb = np.linalg.norm(P - Y, axis=1) < 2.0
    return idx[band & ~corner & ~phil & ~yb], {"corners_head_mm": np.round(corners, 2).tolist(), "Y_head_mm": np.round(Y, 2).tolist(),
                                              "fixed_zone_rule": "3 mm corner balls, philtrum strip |x-mid|<1.5 above the Y, 2 mm ball at the Y"}


MOUTH_PARTS = ("upper_lip_overhang.R", "upper_lip_overhang.L", "mouth_crease", "commissure.R", "commissure.L", "lower_lip_chin", "philtrum")


def _parts_status(inv):
    if inv is None:
        return {}
    J = json.load(open(inv)) if isinstance(inv, str) else inv
    return {p["part"]: p["status"] for p in J.get("parts", [])}, J.get("skin_sha1")


def check_lips(skin, ref=None, inventory=None, zone=None):
    ref = ref if ref is not None else Skin.load(V2_SKIN, "v2 (cat_p2_skin)")
    zi, info = zone if zone is not None else lip_zone(ref)
    Q = ref.P[zi]; lo, hi = Q.min(0) - 4, Q.max(0) + 4; Pc, fc = skin.crop(lo, hi); d, sd = mesh_dist(Pc, fc)(Q)
    st = {"n": int(len(Q)), "p50_mm": _r(np.median(d)), "p95_mm": _r(np.percentile(d, 95)), "p99_mm": _r(np.percentile(d, 99)),
          "max_mm": _r(d.max()), "signed_p50_mm": _r(np.median(sd))}
    a_ok = st["p99_mm"] <= MARKS["lip_p99_mm"]
    ps = _parts_status(inventory) if inventory is not None else ({}, None)
    stat, bound = ps if ps else ({}, None)
    probes = {p: stat.get(p, "MISSING") for p in MOUTH_PARTS}
    b_ok = bool(stat) and all(x == "PASS" for x in probes.values())
    lab_b = "checked" if (bound and bound == skin.sha1) else ("*estimated*: inventory result not bound to this skin" if stat else "unchecked: no inventory result")
    if bound and skin.sha1 and bound != skin.sha1:
        b_ok = False; lab_b = "FAIL: inventory result was run on another skin"
    return {"decision": "lips: keep the v2 structure, refine it", "status": "PASS" if (a_ok and b_ok) else "FAIL",
            "a_structure": {"status": "PASS" if a_ok else "FAIL", "gate": f"p99 <= {MARKS['lip_p99_mm']} mm", **st, **info,
                            "reference": ref.label},
            "b_refinements": {"status": "PASS" if b_ok else "FAIL", "parts": probes, "label": lab_b}, "label": "checked (a); see b"}


# ------------------------------------------------------------------ D7
def check_hair_and_fold(skin_sha1=None, whiskers=None, ears=None, inventory=None):
    """whiskers / ears: json files or dicts with whisker_check / ear_hair_check results (cat_p2_hair_checks.json layout:
    {'whiskers': {'pass'}, 'ears': {'status'}} or the bare result); inventory: chk_inventory layout (parts list)"""
    def load(x):
        return None if x is None else (json.load(open(x)) if isinstance(x, str) else x)
    W, E, Iv = load(whiskers), load(ears), load(inventory); rows = {}
    w = (W or {}).get("whiskers", W) if W else None
    rows["C13_whiskers"] = ("PASS" if (w and w.get("pass") is True) else ("MISSING" if not w else "FAIL"), (W or {}).get("skin_sha1"))
    e = (E or {}).get("ears", E) if E else None
    rows["C14_ear_hair"] = ("PASS" if (e and e.get("status") == "PASS") else ("MISSING" if not e else "FAIL"), (E or {}).get("skin_sha1"))
    st = {p["part"]: p["status"] for p in (Iv or {}).get("parts", [])}
    pk = [st.get("henrys_pocket.R", "MISSING"), st.get("henrys_pocket.L", "MISSING")]
    rows["C6b_henrys_pocket"] = ("PASS" if pk == ["PASS", "PASS"] else ("MISSING" if "MISSING" in pk else "FAIL"), (Iv or {}).get("skin_sha1"))
    out = {"decision": "whiskers as tactile hair, ear hair as its own types, Henry's pocket as a real fold", "criteria": {}}
    ok = True
    for k, (s, h) in rows.items():
        if h and skin_sha1 and h != skin_sha1:
            s = "FAIL (result run on another skin)"
        lab = "checked" if (h and skin_sha1 and h == skin_sha1) else "*estimated*: result not bound to this skin"
        out["criteria"][k] = {"status": s, "label": lab}; ok &= s == "PASS"
    if Iv:
        out["criteria"]["C6b_henrys_pocket"]["parts"] = dict(zip(("R", "L"), pk))
    out["status"] = "PASS" if ok else "FAIL"; out["label"] = "checked (reads the C13 / C14 / C6b results)"
    return out


# ------------------------------------------------------------------ run all, decisions first
def run(skin_path, globes=None, eye_npz=None, lips_ref=None, inventory=None, whiskers=None, ears=None, label=None):
    import time
    t0 = time.time(); sk = Skin.load(skin_path, label); rep = {"skin": skin_path, "skin_sha1": sk.sha1, "decisions": {}}
    rep["decisions"]["D1_leather_top"] = check_leather_top(sk)
    rep["decisions"]["D2_nostril_tails"] = check_nostril_tails(sk)
    rep["decisions"]["D3_ear_bulge"] = check_ear_bulge(sk)
    rep["decisions"]["D4_cornea"] = check_cornea(globes) if globes else {"status": "FAIL", "why": "no globes given"}
    rep["decisions"]["D5_eye_optics"] = check_eye_optics(eye_npz or globes) if (eye_npz or globes) else {"status": "FAIL", "why": "no eye given"}
    rep["decisions"]["D6_lips"] = check_lips(sk, Skin.load(lips_ref) if isinstance(lips_ref, str) else lips_ref, inventory)
    rep["decisions"]["D7_hair_and_fold"] = check_hair_and_fold(sk.sha1, whiskers, ears, inventory)
    rep["summary"] = {k: v["status"] for k, v in rep["decisions"].items()}; rep["seconds"] = round(time.time() - t0, 1)
    return rep


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("skin"); ap.add_argument("out"); ap.add_argument("--globes"); ap.add_argument("--eye")
    ap.add_argument("--lips_ref"); ap.add_argument("--inventory"); ap.add_argument("--whiskers"); ap.add_argument("--ears")
    a = ap.parse_args()
    R = run(a.skin, a.globes, a.eye, a.lips_ref, a.inventory, a.whiskers, a.ears)
    json.dump(R, open(a.out, "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(json.dumps(R["summary"]))
