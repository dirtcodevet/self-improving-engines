"""C14 EAR HAIR CHECK (Phase 2 Stage 5, builder hair-earhair 2026-10-18). Fixes check_hair.json B4.
ONE zone definition (M7) used by the builder (tripo_rebuild/hair_ears.py) and by this check. The check never trusts
the builder's zone labels: it re-classifies every root from GEOMETRY (skin normal side test, rim distance, canal
distance, apex distance) and tests the hair TYPE and LENGTH it finds there against follicle_palette_cat1.json.

ZONES (per ear, ear frame from tripo_rebuild/layers/ears_base_<sd>.npz; h = mm along the ear axis):
  canal  - inside the CANAL OPENING disk (radius r) or its ramp (r .. r + 2 mm, palette ear_canal rule). The canal is
           defined geometrically (canal_opening() below), so the 'zero roots in the canal' test has a place to fail.
  rim    - within RIM_MM of Tripo's lateral / medial rim polylines (ears_rims_<sd>.npz) -> ear_back types
  back   - convex side (skin normal . ear front <= 0) -> ear_back types (short, dense)
  furn   - concave side within FURN_BAND_MM of the medial rim -> ear_furnishing (long, fine)
  inner  - the rest of the concave side -> inner_pinna_sparse
  apex   - roots within APEX_MM below the skin apex may carry ear_tip_wisp (5-10 per ear, no lynx tuft)
PROBES: per zone type / length / density in the palette range; canal hairless + canal definition valid (FAILS when
the definition is missing or not on a conch floor); furnishings present; tip wisp count/length.
usage: python ear_hair_check.py <hair_ears.npz> [--prove]
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TR = os.path.join(ROOT, "tripo_rebuild")
sys.path.insert(0, TR)
import partition as PA  # noqa: E402

PALETTE = json.load(open(os.path.join(ROOT, "engine", "packs", "felid", "follicle_palette_cat1.json")))
RIM_MM, FURN_BAND_MM, FURN_CORE_MM, APEX_MM, H_MIN = 0.8, 5.0, 3.0, 3.0, 1.0
CANAL_R_MM, CANAL_RAMP_MM = 2.5, 2.0          # spec_ears structure.conch canal_opening_diameter 4-6 mm (ESTIMATE) -> r 2.5
ZONES = ["canal", "ramp", "rim", "back", "furn", "inner"]
TYPES = ["ear_back_guard", "ear_back_down", "ear_furnishing", "inner_pinna_sparse", "ear_tip_wisp"]


def _rng(d):
    return float(d["min"]), float(d["max"])


def palette_ranges():
    """length (mm) and density (per mm2) ranges, read from the palette (no hand copies)"""
    T, M = PALETTE["types"], PALETTE["map"]["regions"]
    eb = T["ear_back"]["length_mm"]
    L = {"ear_back_guard": (eb["guard"]["min"], eb["guard"]["max"]), "ear_back_down": (eb["down"]["min"], eb["down"]["max"]),
         "ear_furnishing": tuple(T["ear_furnishing"]["length_mm"]["range"]),
         "inner_pinna_sparse": tuple(T["inner_pinna_sparse"]["length_mm"]["range"]),
         "ear_tip_wisp": tuple(T["ear_tip_wisp"]["length_mm"]["range"])}
    D = {"back": _rng(M["ear_back"]["density_per_mm2"]), "rim": _rng(M["ear_rim"]["density_per_mm2"]),
         "furn": _rng(M["ear_furnishing_band"]["density_per_mm2"]), "inner": _rng(M["ear_inner_skin"]["density_per_mm2"]),
         "canal": (0.0, 0.0)}
    allowed = {"back": {"ear_back_guard", "ear_back_down"}, "rim": {"ear_back_guard", "ear_back_down", "ear_tip_wisp"},
               "furn": {"ear_furnishing"}, "inner": {"inner_pinna_sparse"}, "canal": set(), "ramp": {"inner_pinna_sparse", "ear_furnishing"}}
    wisp_n = tuple(T["ear_tip_wisp"]["count_per_ear"]["range"])
    return L, D, allowed, wisp_n


class Ear:
    """geometry context of one ear: frame, rims, pocket floor (head mm)"""
    def __init__(self, sd):
        b = np.load(os.path.join(TR, "layers", f"ears_base_{sd}.npz"))
        self.sd = sd; self.o = b["origin"]; v = b["axis"] / np.linalg.norm(b["axis"])
        w = b["front"] - (b["front"] @ v) * v; w /= np.linalg.norm(w)
        l_ = np.cross(v, w); l_ /= np.linalg.norm(l_)
        if (l_ @ PA.HR[:, 0]) * (1 if sd == "L" else -1) < 0: l_ = -l_
        self.v, self.w, self.l, self.tip = v, w, l_, b["tip"]
        r = np.load(os.path.join(TR, "layers", f"ears_rims_{sd}.npz"))
        self.med, self.lat = r["medial_rim"], r["lateral_rim"]
        self.med_tree, self.rim_tree = cKDTree(self.med), cKDTree(np.r_[self.med, self.lat])
        pk = json.load(open(os.path.join(TR, "layers", "ears_pocket.json")))["ears"][sd]["slot"]
        self.pocket_floor_head = np.array(pk["floor_line_head_mm"])

    def coords(self, P):
        q = (np.asarray(P) - self.o) * 1000.0; return np.c_[q @ self.l, q @ self.v, q @ self.w]


def ear_mask(P, sd):
    """skin points that belong to ear `sd` (partition's ear region within that ear's stack span, h >= H_MIN)"""
    E = Ear(sd) if isinstance(sd, str) else sd
    m = PA.ear_region(P) & PA.ear_extent(P, E.sd)
    return m & (E.coords(P)[:, 1] >= H_MIN)


def classify(P, N, E, canal, apex_h=None):
    """zone index (into ZONES) per point; P world m, N unit normals; canal dict or None (then no canal zone)"""
    P = np.asarray(P); N = np.asarray(N); z = np.full(len(P), ZONES.index("inner"))
    side = N @ E.w
    d_med = E.med_tree.query(P)[0] * 1000; d_rim = E.rim_tree.query(P)[0] * 1000
    z[(side > 0) & (d_med < FURN_BAND_MM)] = ZONES.index("furn")
    z[side <= 0] = ZONES.index("back")
    z[d_rim < RIM_MM] = ZONES.index("rim")
    if canal is not None:
        dc = np.linalg.norm(P - np.array(canal["centre_world"]), axis=1) * 1000
        z[dc < canal["radius_mm"] + canal["ramp_mm"]] = ZONES.index("ramp")
        z[dc < canal["radius_mm"]] = ZONES.index("canal")
    return z, d_med


def canal_opening(skin_v, skin_n, E, cup_min=4.0, h_lo=1.0, h_hi=20.0):
    """GEOMETRIC canal opening (fixes check_hair B4). The concave side carries a VALLEY (the conch's floor groove) that
    runs up the ear from the base with no single deepest point (measured on skin v1: cup depth below the rims rises
    3.97 -> 7.61 mm (L) from h 3 to 14), so depth alone cannot place the opening. Anatomy places it at the BOTTOM of the
    conch: 'the cartilage rolls into a semitube at the base' (Lanz & Wood 2005) leading to the hairless canal (Kumar &
    Roman-Auerhahn 2016) - spec_ears structure.conch / sdf_recipe S7. Rule: walk 1-mm slices up from h 1; the opening is
    the deepest valley point of the LOWEST slice whose valley is a structural cup (>= cup_min 4 mm below the rims = the
    opening's own diameter lower bound, spec 4-6 mm) AND lies >= r + ramp (4.5 mm) from Henry's pocket floor line
    (ears_pocket.json), so the hairless disk never eats the pocket slot. Valley candidates: concave side (n.front > 0.3),
    >= 1.5 mm from the medial rim. Radius 2.5 mm (spec 4-6 mm dia, ESTIMATE). Inward axis = the inward skin normal."""
    C = E.coords(skin_v); Hd = PA.head_local(skin_v) * 1000
    dpk = cKDTree(E.pocket_floor_head).query(Hd)[0]
    RC = E.coords(np.r_[E.med, E.lat])
    cand = ((skin_n @ E.w) > 0.3) & (E.med_tree.query(skin_v)[0] * 1000 > 1.5)
    prof = []
    for h in np.arange(h_lo, h_hi + 1e-9, 1.0):
        s = cand & (np.abs(C[:, 1] - h) < 0.5); rr = np.abs(RC[:, 1] - h) < 2.0
        if not s.any() or not rr.any(): prof.append([float(h), None]); continue
        idx = np.nonzero(s)[0]; cup = np.median(RC[rr, 2]) - C[idx, 2]
        ok = dpk[idx] >= CANAL_R_MM + CANAL_RAMP_MM
        if not ok.any(): prof.append([float(h), "pocket"]); continue
        jj = np.argmax(np.where(ok, cup, -np.inf)); i = idx[jj]; prof.append([float(h), round(float(cup[jj]), 2)])
        if cup[jj] >= cup_min: break
    else:
        return None
    c = skin_v[i]; a = -skin_n[i] / np.linalg.norm(skin_n[i])
    return {"side": E.sd, "centre_world": c.tolist(), "centre_head_mm": np.round(PA.head_local(c) * 1000, 2).tolist(),
            "centre_ear_mm": np.round(C[i], 2).tolist(), "axis_in_world": a.tolist(), "radius_mm": CANAL_R_MM,
            "ramp_mm": CANAL_RAMP_MM, "pocket_floor_dist_mm": round(float(dpk[i]), 2), "cup_depth_mm": round(float(cup[jj]), 2),
            "slice_profile_h_cup": prof,
            "rule": "lowest 1-mm slice (h >= 1) whose valley floor is >= 4 mm below the rims and >= 4.5 mm from the pocket "
                    "floor; centre = that slice's deepest valley point; r 2.5 mm (spec 4-6 mm dia, ESTIMATE) + 2 mm ramp (palette)",
            "source": "geometry of the skin's conch valley (Lanz & Wood 2005 semitube at the base; Kumar 2016 hairless canal)",
            "confidence": "estimate: position +-1 mm in h (slice step) along the valley; Tripo's conch is closed and the photo "
                          "does not see the canal, so no measured reference exists"}


def validate_canal(canal, skin_v, skin_n, E):
    """the canal definition must EXIST and sit on a conch floor: on the skin (<= 1 mm), concave side (n.front > 0.3),
    at least 3 mm behind the rims at its height (a cup, not a flat face), and not in Henry's pocket (>= 3 mm away)"""
    if canal is None: return {"status": "FAIL", "why": "no canal opening defined (B4: a missing canal must fail)"}
    c = np.array(canal["centre_world"]); tr = cKDTree(skin_v); dd, j = tr.query(c)
    side = float(skin_n[j] @ E.w); cc = E.coords(c[None])[0]
    R = np.r_[E.med, E.lat]; RC = E.coords(R); near = np.abs(RC[:, 1] - cc[1]) < 3.0
    cup = float(np.median(RC[near, 2]) - cc[2]) if near.any() else 0.0
    dpk = float(cKDTree(E.pocket_floor_head).query(PA.head_local(c) * 1000)[0])
    ok = dd * 1000 <= 1.0 and side > 0.3 and cup >= 3.0 and dpk >= 3.0
    return {"status": "PASS" if ok else "FAIL", "skin_dist_mm": round(float(dd * 1000), 3), "normal_dot_front": round(side, 3),
            "cup_depth_behind_rims_mm": round(cup, 2), "pocket_floor_dist_mm": round(dpk, 2),
            "marks": "skin <= 1 mm, n.front > 0.3, cup >= 3 mm, pocket >= 3 mm"}


TIE_M = 2e-6


def nearest_face(P, v, fs, fc, k=24, both=False):
    """index (into fs) of the face holding each point: exact closest point over the k nearest face centroids"""
    if len(P) == 0: return (np.zeros(0, int),) * 2 + (np.zeros(0, bool),) if both else np.zeros(0, int)
    sys.path.insert(0, TR); import exact_sdf as XS
    _, J = cKDTree(fc).query(P, k=k); D = np.zeros(J.shape)
    for c in range(k):
        tri = fs[J[:, c]]; Q = XS.closest_on_tri(P, v[tri[:, 0]], v[tri[:, 1]], v[tri[:, 2]]); D[:, c] = np.linalg.norm(Q - P, axis=1)
    o = np.argsort(D, axis=1); r = np.arange(len(P))
    best, second = J[r, o[:, 0]], J[r, o[:, 1]]
    tie = D[r, o[:, 1]] - D[r, o[:, 0]] < TIE_M          # the root lies on an edge shared by two faces
    return (best, second, tie) if both else best


UNDER_MM, UNDER_FRAC, SAMPLE = 0.1, 0.01, 20000


def strands_above_skin(hair, k, v, fs, fc, fn):
    """no hair may run THROUGH the skin (closes Henry's pocket, pierces the pinna: check_hair S6). Every strand point
    after the root is tested against the EXACT nearest skin face (closest point, its face normal); a strand FAILS when
    any point lies > UNDER_MM (0.1 mm) on the tissue side. PASS when <= UNDER_FRAC (1 %) of the strands of every type
    fail. Up to SAMPLE strands per type are tested (random, seeded) to bound memory."""
    sys.path.insert(0, TR); import exact_sdf as XS
    st = np.asarray(hair["strands"]); typ = np.asarray(hair["type"]); sel = np.asarray(hair["ear"]) == k
    rng = np.random.default_rng(0); res = {}; ok = True
    for t, tn in enumerate(TYPES):
        idx = np.nonzero(sel & (typ == t))[0]
        if len(idx) == 0: continue
        if len(idx) > SAMPLE: idx = rng.choice(idx, SAMPLE, replace=False)
        Pk = st[idx][:, 1:].astype(float).reshape(-1, 3); j = nearest_face(Pk, v, fs, fc, k=8)
        tri = fs[j]; Q = XS.closest_on_tri(Pk, v[tri[:, 0]], v[tri[:, 1]], v[tri[:, 2]])
        sdist = ((Pk - Q) * fn[j]).sum(1) * 1000; bad = (sdist < -UNDER_MM).reshape(len(idx), -1).any(1)
        fr = float(bad.mean()); ok &= fr <= UNDER_FRAC
        res[tn] = {"tested": int(len(idx)), "frac_through_skin": round(fr, 4), "deepest_mm": round(float(-sdist.min()), 2)}
    return {"status": "PASS" if ok else "FAIL", "per_type": res, "marks": f"point > {UNDER_MM} mm under skin; <= {UNDER_FRAC:.0%} per type"}


_SKIN_CACHE = {}


def load_skin_ear(skin_path, sd):
    if (skin_path, sd) in _SKIN_CACHE: return _SKIN_CACHE[(skin_path, sd)]
    _SKIN_CACHE[(skin_path, sd)] = _load_skin_ear(skin_path, sd); return _SKIN_CACHE[(skin_path, sd)]


def _load_skin_ear(skin_path, sd):
    S = np.load(skin_path); v, f, n = S["v"], S["f"], S["n"].astype(float)
    E = Ear(sd); m = ear_mask(v, E)
    fs = f[m[f].all(1)]; used = np.unique(fs); remap = -np.ones(len(v), np.int64); remap[used] = np.arange(len(used))
    return v[used], remap[fs], n[used], E


def check(hair, skin_path, canals=None, verbose=True):
    """hair: dict-like with roots (N,3) world, root_normal (N,3), type (N,) idx into TYPES, length_mm (N,), ear (N,) 0=L 1=R.
    canals: {sd: canal dict or None}; defaults to hair['canal_<sd>'] JSON. Returns the report dict."""
    L_rng, D_rng, allowed, wisp_n = palette_ranges(); rep = {"ears": {}}; allpass = True
    roots = np.asarray(hair["roots"]); typ = np.asarray(hair["type"]); Lmm = np.asarray(hair["length_mm"]); ear = np.asarray(hair["ear"])
    for k, sd in enumerate("LR"):
        v, fs, n, E = load_skin_ear(skin_path, sd)
        canal = canals[sd] if canals is not None else json.loads(str(hair[f"canal_{sd}"])) if f"canal_{sd}" in hair else None
        r = {"canal_definition": validate_canal(canal, v, n, E)}
        A, B, C = v[fs[:, 0]], v[fs[:, 1]], v[fs[:, 2]]; fn = np.cross(B - A, C - A); ar = np.linalg.norm(fn, axis=1) / 2 * 1e6
        fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-30)[:, None]; fc = (A + B + C) / 3
        if (fn * n[fs].mean(1)).sum(1).mean() < 0: fn = -fn
        fz, fdm = classify(fc, fn, E, canal)
        sel = ear == k; P = roots[sel]; T = typ[sel]; LL = Lmm[sel]
        # zone of each root from the SKIN geometry at its nearest face (never the builder's label)
        j, j2, tie = nearest_face(P, v, fs, fc, both=True)
        rz, rdm = classify(P, fn[j], E, canal) if len(P) else (np.zeros(0, int), np.zeros(0))
        rz2 = classify(P, fn[j2], E, canal)[0] if len(P) else np.zeros(0, int)     # the other face of an edge tie
        hmax = E.coords(v[np.unique(fs)])[:, 1].max(); rh = E.coords(P)[:, 1] if len(P) else np.zeros(0)
        apex = rh > hmax - APEX_MM; is_w = T == TYPES.index("ear_tip_wisp")
        zr = {}
        for zi, zn in enumerate(ZONES):
            area = float(ar[fz == zi].sum()); inz = rz == zi; cnt = int(inz.sum())
            if zn == "furn":   # density in the band core (d_med < 3 mm), where the palette's band density applies
                core_a = float(ar[(fz == zi) & (fdm < FURN_CORE_MM)].sum()); cnt_core = int((inz & (rdm < FURN_CORE_MM) & (T == TYPES.index("ear_furnishing"))).sum())
                dens = cnt_core / max(core_a, 1e-9)
            else:
                dens = cnt / max(area, 1e-9)
            okw = is_w[inz] & apex[inz] & (zn != "canal")          # tip wisps are allowed at the apex in any zone but the canal
            alt_ok = np.array([tie[i] and TYPES[T[i]] in allowed[ZONES[rz2[i]]] for i in np.nonzero(inz)[0]], bool)
            bad_t = sorted({TYPES[t] for t in T[inz][~okw & ~alt_ok]} - allowed[zn]) if cnt else []
            wisp_off_apex = int((is_w[inz] & ~apex[inz]).sum())
            if wisp_off_apex: bad_t = sorted(set(bad_t) | {"ear_tip_wisp(off apex)"})
            bad_len = int(sum(1 for t, l in zip(T[inz], LL[inz]) if not (L_rng[TYPES[t]][0] - 1e-6 <= l <= L_rng[TYPES[t]][1] + 1e-6)))
            st = "PASS"
            if bad_t or bad_len: st = "FAIL"
            if zn in D_rng and zn != "canal" and area > 5.0 and not (D_rng[zn][0] <= dens <= D_rng[zn][1]): st = "FAIL"
            if zn == "canal" and cnt > 0: st = "FAIL"
            if zn == "ramp":   # the ramp may hold hair, but thinner than outside: density <= the band / inner typical
                pass
            zr[zn] = {"status": st, "area_mm2": round(area, 1), "roots": cnt, "density_per_mm2": round(dens, 2),
                      "range": D_rng.get(zn), "wrong_types": bad_t, "length_out_of_range": bad_len}
        r["zones"] = zr
        r["canal_hairless"] = {"status": "PASS" if (r["canal_definition"]["status"] == "PASS" and zr["canal"]["roots"] == 0) else "FAIL",
                               "roots_in_canal": zr["canal"]["roots"]}
        nf = int(((T == TYPES.index("ear_furnishing")) & (rz == ZONES.index("furn"))).sum())
        fl = LL[T == TYPES.index("ear_furnishing")]
        need = D_rng["furn"][0] * float(ar[(fz == ZONES.index("furn")) & (fdm < FURN_CORE_MM)].sum())
        r["furnishings_present"] = {"status": "PASS" if (nf >= need and len(fl) and np.median(fl) >= L_rng["ear_furnishing"][0]) else "FAIL",
                                    "count_in_band": nf, "min_needed": round(need, 1), "median_len_mm": round(float(np.median(fl)), 2) if len(fl) else 0}
        wl = LL[T == TYPES.index("ear_tip_wisp")]; nw = len(wl)
        r["tip_wisp"] = {"status": "PASS" if (wisp_n[0] <= nw <= wisp_n[1] and (nw == 0 or wl.max() <= L_rng["ear_tip_wisp"][1])) else "FAIL",
                         "count": nw, "max_len_mm": round(float(wl.max()), 2) if nw else 0, "range": wisp_n}
        r["strands_above_skin"] = strands_above_skin(hair, k, v, fs, fc, fn) if "strands" in hair else {"status": "FAIL", "why": "no strand points"}
        ok = all(x["status"] == "PASS" for x in [r["canal_definition"], r["canal_hairless"], r["furnishings_present"], r["tip_wisp"],
                                                 r["strands_above_skin"]] + list(zr.values()))
        r["status"] = "PASS" if ok else "FAIL"; allpass &= ok; rep["ears"][sd] = r
    rep["status"] = "PASS" if allpass else "FAIL"
    return rep


def _load(path):
    d = np.load(path, allow_pickle=True); return {k: d[k] for k in d.files}


if __name__ == "__main__":
    h = _load(sys.argv[1]); skin = str(h.get("skin_path", os.path.join(TR, "layers", "skin_v1_person_approved_leather_top.npz")))
    print(json.dumps(check(h, skin), indent=1))
