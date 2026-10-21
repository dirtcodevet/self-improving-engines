"""C4 STRUCTURE INVENTORY CHECK (Phase 2, checksB 2026-10-18).
Every L3_features part in packs/felid/structure_inventory.json must (a) have a REGISTERED BUILDER that says it builds
the part and (b) pass a GEOMETRIC PROBE on the mesh. A part with no builder, no probe (stub) or a failing probe FAILS.
Paint can never pass: every probe reads geometry only (E5).

REGISTRY  - a case manifest (JSON) {"builders": {"<builder>": {"parts": [part ids], "inputs": {part id: {...}}}}}.
            `register(name, parts, inputs)` does the same in code. Inputs are what the probe needs to find the part
            (e.g. the nostril opening centre and inward axis, the globe's face set) - the builder knows them.
PART IDS  - INVENTORY below maps each inventory entry (by its text) to the sub-parts that must all pass.
PROBES    - built now: nostril_cavity (nose), eyelid_wrap (eyes). Everything else is a declared STUB that FAILS.
  nostril_cavity: a bundle of rays enters the nostril opening along its inward axis; the cavity depth is the
      greatest axial travel past the opening plane before a ray meets skin. PASS >= 4.0 mm. Reason: Tripo's blind
      dish reads 2.15 / 2.31 mm (nose_basins, +-0.5) so 4.0 clears it by > 1 mm; and for the measured opening
      (minor width ~2.6-3.0 mm at half depth, r ~1.4 mm) a floor at 4 mm sees the sky at view factor r2/(r2+d2) ~ 11 %
      (dark in clay) against ~27 % at 2.3 mm (a shaded dish). A ray that meets nothing (open mesh) is a FAIL (breach).
  eyelid_wrap: globe samples cast rays along their outward normal. COVERED = first hit is a skin face ENTERED from
      the globe side within GMAX 2.0 mm (the lid's underside lies on the globe); INSIDE = first hit EXITS skin within
      GMAX (the globe point is inside the skin: the lid cuts through the globe); VISIBLE = no hit. Per sector (24 round
      the eye axis) the OVERHANG = covered area attached to the opening / lid-edge length in that sector - the mean
      width of the globe band
      the lid lies over, measured from the lid edge (chord from the centre: x0.95 of arc length at 35 deg).
      PASS when >= 75 % of the sectors that hold globe samples overhang >= 0.20 mm AND the INSIDE share < 2 %.
      Reasons: 0.20 mm = just under one Tripo mesh edge near the eye (~0.25 mm), so a band any narrower cannot be told
      from a flush (butted / painted) lid; 75 % allows the canthi, where the margin turns, to read short; GMAX 2.0 mm
      = the lid height REVIEW_eyes measured (2.0-2.4 mm), anything further is a brow or socket wall, not lid contact.
usage: python inventory_check.py <mesh.npz (v,f metres world)> <manifest.json> [--headframe] [out.json]
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
INV_PATH = os.path.join(HERE, "..", "packs", "felid", "structure_inventory.json")

# ---------------------------------------------------------------- inventory entry -> sub-part ids (all must pass)
INVENTORY = {
    "nose leather (planum nasale)": ["nose_leather"],
    "NOSTRILS opening into a NASAL CAVITY (vestibule) with depth": ["nostril_cavity.R", "nostril_cavity.L"],
    "nostril wings (alar folds)": ["alar_fold.R", "alar_fold.L"],
    "crease between the leather and the furred bridge": ["leather_bridge_crease"],
    "philtrum groove": ["philtrum"],
    "upper lip lobes overhanging the lower lip": ["upper_lip_overhang.R", "upper_lip_overhang.L"],
    "MOUTH CREASE (closed)": ["mouth_crease"],
    "mouth-corner (commissure) creases": ["commissure.R", "commissure.L"],
    "lower lip and chin": ["lower_lip_chin"],
    "whisker pads with follicle rows": ["whisker_pad.R", "whisker_pad.L"],
    "eyelids wrapping the globe, third eyelid at the inner corner": ["eyelid_wrap.R", "eyelid_wrap.L", "third_eyelid.R", "third_eyelid.L"],
    "ear": ["ear_shell.R", "ear_shell.L", "helix.R", "helix.L", "henrys_pocket.R", "henrys_pocket.L", "conch.R", "conch.L"],
    "front paw": ["fore_toes.R", "fore_toes.L", "dewclaw.R", "dewclaw.L", "fore_digital_pads", "metacarpal_pad", "carpal_pad"],
    "hind paw": ["hind_toes.R", "hind_toes.L", "hind_digital_pads", "metatarsal_pad"],
}


import os as _os_mg, sys as _sys_mg  # noqa: E402  (build A1: the engine's one closest point, normals, cotangent Laplacian)
_MG_DIR = _os_mg.path.normpath(_os_mg.path.join(_os_mg.path.dirname(_os_mg.path.abspath(__file__)), '../tools'))
if _MG_DIR not in _sys_mg.path:
    _sys_mg.path.append(_MG_DIR)
import mesh_geom as _MG  # noqa: E402


def inventory_entries(path=INV_PATH):
    """every L3_features entry of the pack, matched to INVENTORY (an unmatched entry is itself a FAIL)"""
    inv = json.load(open(path)); out = []
    for region, layers in inv.items():
        if region.startswith("_"):
            continue
        for e in layers.get("L3_features", []):
            key = next((k for k in INVENTORY if e["part"].startswith(k)), None)
            out.append((region, e["part"], key))
    return out


# ---------------------------------------------------------------- registry
REGISTRY = {}


def register(name, parts, inputs=None):
    REGISTRY[name] = {"parts": list(parts), "inputs": dict(inputs or {})}


def load_manifest(path):
    REGISTRY.clear()
    for name, b in json.load(open(path)).get("builders", {}).items():
        register(name, b.get("parts", []), b.get("inputs", {}))


# ---------------------------------------------------------------- geometry
def first_hit(O, D, tri, tmax=np.inf, budget=2_000_000):
    """Moller-Trumbore, first hit of each ray (O + t D, 1e-6 < t <= tmax) on triangles tri (m,3,3). Returns t (inf =
    none) and the hit triangle index (-1). Rays are sorted into 2 mm cells and chunked so that rays x triangles stays
    under `budget` pairs (memory ~0.4 GB); with a finite tmax triangles are prefiltered by the chunk's segment box."""
    n = len(O); T = np.full(n, np.inf); I = np.full(n, -1)
    if len(tri) == 0 or n == 0:
        return T, I
    order = np.lexsort(np.floor(O / 2.0).T[::-1]); O, D = O[order], D[order]
    tlo, thi = tri.min(1), tri.max(1); big = np.isinf(tmax); s = 0
    while s < n:
        k0 = max(1, min(256, budget // max(len(tri), 1))) if big else 64
        o, d = O[s:s + k0], D[s:s + k0]
        if big:
            sel = np.arange(len(tri))
        else:
            e = o + tmax * d; lo = np.minimum(o, e).min(0) - 1e-6; hi = np.maximum(o, e).max(0) + 1e-6
            sel = np.nonzero(np.all(thi >= lo, 1) & np.all(tlo <= hi, 1))[0]
        if len(sel):
            for c0 in range(0, len(sel), max(1, budget // len(o))):
                ss = sel[c0:c0 + max(1, budget // len(o))]
                v0 = tri[ss, 0]; e1 = tri[ss, 1] - v0; e2 = tri[ss, 2] - v0
                p = np.cross(d[:, None, :], e2[None]); det = np.einsum("rtk,tk->rt", p, e1)
                okd = np.abs(det) > 1e-12; inv = np.where(okd, 1.0 / np.where(okd, det, 1.0), 0.0); del det
                sv = o[:, None, :] - v0[None]; u = np.einsum("rtk,rtk->rt", sv, p) * inv; del p
                q = np.cross(sv, e1[None]); del sv
                w = np.einsum("rk,rtk->rt", d, q) * inv; t = np.einsum("tk,rtk->rt", e2, q) * inv; del q
                hit = okd & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 1e-6) & (t <= tmax)
                t = np.where(hit, t, np.inf); k = t.argmin(1); tk = t[np.arange(len(o)), k]
                better = tk < T[order[s:s + len(o)]]
                idx = order[s:s + len(o)][better]; T[idx] = tk[better]; I[idx] = ss[k[better]]
        s += len(o)
    return T, I


def face_normals(v, f):
    n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]); return n / np.maximum(np.linalg.norm(n, axis=1), 1e-15)[:, None]


def vertex_normals(v, f):
    return _MG.vertex_normals(v, f, eps=1e-15)


def area_samples(v, f, per_mm2, seed=0):
    """stratified-ish area samples: returns points, the face each came from, barycentrics"""
    rng = np.random.default_rng(seed); a = 0.5 * np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1)
    cnt = np.floor(a * per_mm2 + rng.random(len(f))).astype(int); fi = np.repeat(np.arange(len(f)), cnt)
    r1, r2 = rng.random(len(fi)), rng.random(len(fi)); s = np.sqrt(r1); b = np.c_[1 - s, s * (1 - r2), s * r2]
    P = (v[f[fi]] * b[:, :, None]).sum(1); return P, fi, b


def unit(x):
    x = np.asarray(x, float); return x / np.linalg.norm(x)


def perp_basis(a):
    t = np.cross(a, [0, 0, 1.0]) if abs(a[2]) < 0.9 else np.cross(a, [1.0, 0, 0]); t = unit(t); return t, np.cross(a, t)


# ---------------------------------------------------------------- probes (Lmm = vertices in mm, any frame)
def nostril_probe(Lmm, f, inp, mark=4.0, rho=1.0, alpha=16.0, back=1.0, crop=15.0):
    c = np.asarray(inp["opening_centre_mm"], float); a = unit(inp["axis_into_head"]); t1, t2 = perp_basis(a)
    keep = np.linalg.norm(Lmm[f].mean(1) - c, axis=1) < crop; tri = Lmm[f[keep]]
    O, D = [], []
    for r in (0.0, rho / 2, rho):
        for ph in (np.arange(8) * np.pi / 4 if r > 0 else [0.0]):
            o = c + r * (np.cos(ph) * t1 + np.sin(ph) * t2) - back * a
            for al in (0.0, alpha / 2, alpha):
                for ps in (np.arange(8) * np.pi / 4 if al > 0 else [0.0]):
                    A = np.radians(al); D.append(np.cos(A) * a + np.sin(A) * (np.cos(ps) * t1 + np.sin(ps) * t2)); O.append(o)
    O, D = np.array(O), np.array(D); T, _ = first_hit(O, D, tri)
    for i in np.nonzero(~np.isfinite(T))[0]:                     # left the crop: recast on the whole mesh near its line
        C = Lmm[f].mean(1) - O[i]; dl = np.linalg.norm(C - np.outer(C @ D[i], D[i]), axis=1)
        T[i] = first_hit(O[i:i + 1], D[i:i + 1], Lmm[f[(dl < 3.0) & (C @ D[i] > -1.0)]])[0][0]
    depth = T * (D @ a) - back; breach = int((~np.isfinite(T)).sum()); fin = depth[np.isfinite(depth)]
    val = float(fin.max()) if len(fin) else float("nan")
    ok = bool(breach == 0 and len(fin) and val >= mark)
    return {"status": "PASS" if ok else "FAIL", "value_mm": round(val, 3), "mark_mm": mark, "rays": len(O), "breach_rays": breach,
            "p90_depth_mm": round(float(np.percentile(fin, 90)), 3) if len(fin) else None,
            "why": "cavity depth past the opening plane" + ("; rays escaped (open mesh)" if breach else "")}


def eyelid_probe(Lmm, f, inp, mark=0.20, gmax=2.0, nsect=24, frac_mark=0.75, inside_mark=0.02, per_mm2=64.0, attach=2.0):
    gmask = np.zeros(len(f), bool); gmask[np.asarray(inp["globe_faces"], int)] = True
    gf = f[gmask]; c = np.asarray(inp["centre_mm"], float)
    VN = vertex_normals(Lmm, gf)                                   # normals from the globe faces only
    P, fi, b = area_samples(Lmm, gf, per_mm2); N = (VN[gf[fi]] * b[:, :, None]).sum(1); N /= np.linalg.norm(N, axis=1)[:, None]
    out = unit(inp["outward"]) if "outward" in inp else unit(N.mean(0))
    if (N @ out).mean() < 0:
        N = -N
    ax = unit(inp.get("axis", N.mean(0)))
    near = ~gmask & (np.linalg.norm(Lmm[f].mean(1) - c, axis=1) < float(inp.get("radius_mm", 16.0)))
    sf = f[near]; tri = Lmm[sf]; fn = face_normals(Lmm, sf)
    T, I = first_hit(P + 1e-4 * N, N, tri, tmax=gmax + 1.0)
    hit = np.isfinite(T); dotn = np.where(hit, np.einsum("ij,ij->i", fn[np.maximum(I, 0)], N), 0.0)
    covered = hit & (T <= gmax) & (dotn < 0); inside = hit & (T <= gmax) & (dotn > 0); visible = ~hit
    # only samples that can see out or are near the opening matter: globe points far behind (hit > gmax) are socket
    res = {"samples": int(len(P)), "visible": int(visible.sum()), "covered": int(covered.sum()), "inside": int(inside.sum())}
    if visible.sum() == 0:
        return {**res, "status": "FAIL", "why": "no globe visible (fissure closed or globe not exposed)"}
    # overhang per sector = COVERED AREA / EDGE LENGTH: covered samples attached to the opening (within 2 mm of a
    # visible one) x area per sample, divided by the lid-edge length in the sector (rho_edge x sector angle, rho =
    # distance from the eye axis, rho_edge = p10 of the band's own samples = its inner edge, the lid margin; 'visible'
    # only means no hit within gmax + 1 mm, so it cannot place the edge on a globe whose back is in a socket). An area ratio, so no bin edges: a clean band
    # of width w reads w x (1 + w cot(theta_edge) / 2R) (+2 % at 0.3 mm on a 10 mm globe); an edge that crosses the
    # sector obliquely (the canthi) reads short, which the 75 % sector allowance is for.
    t1, t2 = perp_basis(ax); X = P - c; th = np.arctan2(X @ t2, X @ t1); sec = ((th + np.pi) / (2 * np.pi) * nsect).astype(int) % nsect
    rho = np.linalg.norm(X - np.outer(X @ ax, ax), axis=1); band = np.zeros(len(P), bool)
    if covered.any():
        band[covered] = cKDTree(P[visible]).query(P[covered])[0] <= attach
    per = []
    for s in range(nsect):
        m = sec == s
        if m.sum() < 10:
            continue
        bs = m & band
        if bs.sum() < 5:                                  # < 0.08 mm2 of cover: no band in this sector
            per.append(0.0); continue
        edge = np.percentile(rho[bs], 10) * 2 * np.pi / nsect
        per.append(float(bs.sum() / per_mm2 / max(edge, 1e-9)))
    per = np.array(per); frac = float((per >= mark).mean()); ish = float(inside.sum() / max(len(P), 1))
    ok = frac >= frac_mark and ish < inside_mark
    why = []
    if frac < frac_mark: why.append(f"lid overhang >= {mark} mm in only {frac*100:.0f} % of sectors")
    if ish >= inside_mark: why.append(f"globe inside the skin at {ish*100:.1f} % of samples (lid cuts through the globe)")
    return {**res, "status": "PASS" if ok else "FAIL", "sectors": len(per), "sector_overhang_mm": np.round(per, 2).tolist(),
            "overhang_median_mm": round(float(np.median(per)), 3), "overhang_max_mm": round(float(per.max()), 3),
            "frac_sectors_ok": round(frac, 3), "inside_share": round(ish, 4), "mark_mm": mark, "why": "; ".join(why) or "lid lies over the globe"}


def stub(part):
    def p(Lmm, f, inp):
        return {"status": "FAIL", "why": f"probe for '{part}' not built yet (declared stub)"}
    return p


PROBES = {}
for _k, _subs in INVENTORY.items():
    for _s in _subs:
        PROBES[_s] = stub(_s)
for _sd in ("R", "L"):
    PROBES[f"nostril_cavity.{_sd}"] = nostril_probe
    PROBES[f"eyelid_wrap.{_sd}"] = eyelid_probe
BUILT_PROBES = sorted(k for k, p in PROBES.items() if p in (nostril_probe, eyelid_probe))


# ---------------------------------------------------------------- feat_eyes block (builder 'feat-eyes', 2026-10-18; appended)
def third_eyelid_probe(Lmm, f, inp, tmax=0.20, mopen=-0.15, wmin=0.2, wmax=0.8, far=None, far_mark=0.01, per_mm2=64.0):
    """THIRD EYELID: globe samples INSIDE the lid margin (feat_eyes M < -0.15 mm) cast rays along their outward normal;
    MEMBRANE-covered = first hit is a non-globe face entered from the globe side within 0.20 mm (the membrane's inner face
    lies on the globe; the leaning lid's cut face is hit at h = |M| tan 66 >= 0.34 mm there, so it cannot count).
    EXPOSED WIDTH = furthest membrane-covered sample (within 0.5 mm of the fissure axis) from the opening's medial tip
    (feat_eyes tel_tip_uv) along the canthus->opening-centre direction
    (spec probe 'exposed width ... 0.5 +- 0.3'); FAR SHARE = membrane-covered samples > far (feat_eyes TEL_REACH_MM)
    from the medial canthus / all opening samples (check_eyes B3: a membrane over the lateral cornea). PASS when
    0.2 <= width <= 0.8 mm and far share < 1 %. Head-frame mm only (it uses feat_eyes' margin geometry, M7)."""
    import importlib
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "packs", "felid", "features")))
    FE = importlib.import_module("feat_eyes"); sd = inp.get("side")
    if sd not in ("L", "R") or "globe_faces" not in inp:
        return {"status": "FAIL", "why": "builder gave no side / globe faces"}
    E = FE.EYES[sd]; far = FE.P_["TEL_REACH_MM"] if far is None else far
    gmask = np.zeros(len(f), bool); gmask[np.asarray(inp["globe_faces"], int)] = True; gf = f[gmask]
    if len(gf) == 0:
        return {"status": "FAIL", "why": "no globe faces"}
    VN = vertex_normals(Lmm, gf); P, fi, b = area_samples(Lmm, gf, per_mm2); N = (VN[gf[fi]] * b[:, :, None]).sum(1)
    N /= np.linalg.norm(N, axis=1)[:, None]
    if (np.einsum("ij,ij->i", N, P - E["Cs"]) < 0).mean() > 0.5:
        N = -N
    M = FE.margin_dist(P, sd); op = M < mopen; P, N, M = P[op], N[op], M[op]
    if len(P) == 0:
        return {"status": "FAIL", "why": "no globe samples inside the margin"}
    near = ~gmask & (np.linalg.norm(Lmm[f].mean(1) - E["Cs"], axis=1) < 16.0); sf = f[near]
    T, I = first_hit(P + 1e-4 * N, N, Lmm[sf], tmax=tmax + 0.5)
    fn = face_normals(Lmm, sf); dotn = np.where(np.isfinite(T), np.einsum("ij,ij->i", fn[np.maximum(I, 0)], N), 0.0)
    mem = np.isfinite(T) & (T <= tmax) & (dotn < 0)
    uv = FE._uv(E, P); rel = uv - E["tel_tip_uv"]; along = rel @ E["e_med"]; dm = np.linalg.norm(rel, axis=1)
    cross = np.abs(rel @ np.array([-E["e_med"][1], E["e_med"][0]]))
    mm = mem & (dm <= far) & (cross <= 0.5)                       # ON the fissure axis at the opening's medial tip
    width = float(along[mm].max()) if mm.sum() >= 5 else 0.0
    far_share = float((mem & (dm > far)).sum() / len(P))
    ok = wmin <= width <= wmax and far_share < far_mark
    why = []
    if not (wmin <= width <= wmax): why.append(f"exposed width {width:.2f} mm outside {wmin}-{wmax}")
    if far_share >= far_mark: why.append(f"membrane over {far_share*100:.1f} % of the opening beyond {far} mm of the medial canthus")
    return {"status": "PASS" if ok else "FAIL", "opening_samples": int(len(P)), "membrane_samples": int(mem.sum()),
            "exposed_width_mm": round(width, 3), "far_share": round(far_share, 4),
            "membrane_area_mm2": round(float(mem.sum() / per_mm2), 3), "why": "; ".join(why) or "membrane at the medial canthus only"}


for _sd in ("R", "L"):
    PROBES[f"third_eyelid.{_sd}"] = third_eyelid_probe
BUILT_PROBES = sorted(k for k, p in PROBES.items() if p in (nostril_probe, eyelid_probe, third_eyelid_probe))


# ---------------------------------------------------------------- MOUTH probes (feat-mouth builder, Phase 2 Stage 3)
# Inputs come from engine/packs/felid/features/feat_mouth.probe_inputs() (design sections in head mm). Every probe reads
# the MESH only, by rays (paint cannot pass). Hits along a ray from outside alternate enter / exit (orientation-free).
# upper_lip_overhang.<sd> (P2): sections at s = 2/7/12/20, rays along -n at heights h above the margin U:
#   (a) sigma = depth(h=-0.8) - depth(h=+0.6) within 0.3 mm of the design (LL plane at h=-0.8) and > 0.3 (no flush/underbite)
#   (b)+(c) at every h in [0.25, v-0.35]: enter flap, exit (flap >= 0.3 mm), gap 0.1-0.45 mm, enter lower lip: the flap
#       is hit first, so the lower lip's top margin is hidden; at h = v + 0.6 no gap (overlap length v +-0.6)
# mouth_crease (P1 + C6 + P3a): midline rays along +y: 1 mm below the Y the first hit lies >= 1.2 mm behind the skin at
#   the Y (Tripo's receding face reads ~0.6); the notch top within 0.8 mm of the Y and still open 0.9 mm above the contact;
#   the lobe margin leaves the Y at 25-45 deg (chord to 1.9 mm in x); a gap at every station s = 0.5..24.5 both sides;
#   the margin edge (lowest h still on the flap) within 0.5 mm of U at every station
# commissure.<sd> (P4): the slot tip (last station with a gap) within 0.7 mm of the corner; |x - mid| L/R within 0.3;
#   crease depth at 1/2/3 mm = 0.3 (1 - l/4) +-0.1 against the level 1.6 mm either side; no gap beyond the corner
# lower_lip_chin (P5): at x = mid +-4 the lower lip is recessed (sigma > 0.3) with a hidden top margin (gap); the chin
#   (|x| < 6, 2-8 mm below the contact) lies 1.5 +-0.5 mm (median) inside Tripo's envelope (C3)
def _mouth_hits(Lmm, f, O, D, centre, crop=10.0, nmax=4, tmax=10.0):
    keep = np.linalg.norm(Lmm[f].mean(1) - centre, axis=1) < crop; tri = Lmm[f[keep]]; out = [[] for _ in range(len(O))]
    o = O.copy(); acc = np.zeros(len(O)); live = np.ones(len(O), bool)
    for _ in range(nmax):
        if not live.any():
            break
        T, _ = first_hit(o[live], D[live], tri, tmax=tmax); li = np.nonzero(live)[0]
        for j, t in zip(li, T):
            if np.isfinite(t):
                out[j].append(acc[j] + t)
        ok = np.isfinite(T); acc[li[ok]] += T[ok] + 1e-3; o[li[ok]] = o[li[ok]] + (T[ok] + 1e-3)[:, None] * D[li[ok]]
        live[li[~ok]] = False
    return out


def _gap_at(Lmm, f, U, n, b, h, back=3.0):
    U, n, b = (np.asarray(x, float) for x in (U, n, b)); h = np.atleast_1d(h)
    O = U + np.outer(h, b) + back * n; D = np.tile(-n, (len(h), 1)); H = _mouth_hits(Lmm, f, O, D, U)
    res = []
    for hh in H:
        if len(hh) >= 3:
            res.append({"d0": hh[0] - back, "flap": hh[1] - hh[0], "gap": hh[2] - hh[1]})
        else:
            res.append({"d0": (hh[0] - back) if hh else None, "flap": None, "gap": None})
    return res


def _mouth_has_gap(r, lo=0.08, hi=0.6, flap_min=0.2, scale=1.0):
    """scale = |n . n_LL|: the ray runs along -n, the slot is the LL plane, so the gap across the slot = ray gap x scale"""
    return r["gap"] is not None and lo <= r["gap"] * scale <= hi and r["flap"] >= flap_min


def mouth_overhang_probe(Lmm, f, inp, side):
    if not inp:
        return {"status": "FAIL", "why": "builder gave no probe inputs"}
    rows, ok = [], True
    for S in inp[side]["sections"]:
        v = S["v"]; eh = S["eu2"][1]; sc = abs(S["nl2"][0])      # heights along the slot (its own frame), not along b
        hs = np.r_[np.linspace(0.45, max(v - 0.35, 0.5), 4), v + 0.6] * eh
        g = _gap_at(Lmm, f, S["U"], S["n"], S["b"], np.r_[-0.8, 0.6, hs])
        exp_sig = S["sigma"] - 0.8 * S["nl2"][1] / S["nl2"][0]
        sig = (g[0]["d0"] - g[1]["d0"]) if (g[0]["d0"] is not None and g[1]["d0"] is not None) else None
        a_ok = sig is not None and abs(sig - exp_sig) <= 0.3 and sig > 0.3
        bc = [r for r in g[2:-1]]; b_ok = all(_mouth_has_gap(r, 0.1, 0.45, 0.3, sc) for r in bc)
        top_ok = not _mouth_has_gap(g[-1], scale=sc)
        ok &= a_ok and b_ok and top_ok
        rows.append({"s": S["s"], "sigma_mm": None if sig is None else round(sig, 3), "sigma_design_mm": round(exp_sig, 3),
                     "gaps_across_slot_mm": [None if r["gap"] is None else round(r["gap"] * sc, 3) for r in bc],
                     "flap_mm": [None if r["flap"] is None else round(r["flap"], 3) for r in bc],
                     "closed_above_v": top_ok, "a": a_ok, "bc": b_ok})
    return {"status": "PASS" if ok else "FAIL", "sections": rows,
            "why": "upper lip overhangs a recessed lower lip over a hidden gap" if ok else "overhang / hidden gap / sigma not as designed"}


def mouth_crease_probe(Lmm, f, inp):
    if not inp:
        return {"status": "FAIL", "why": "builder gave no probe inputs"}
    Y = np.asarray(inp["Y_mm"]); Cz = inp["contact_mm"][2]; mx = inp["mid_x"]; why = []
    def front(x, zs):
        O = np.stack([np.full(len(zs), x), np.full(len(zs), Y[1] - 4.0), zs], 1); D = np.tile([0, 1.0, 0], (len(zs), 1))
        return np.array([(h[0] + Y[1] - 4.0) if h else np.nan for h in _mouth_hits(Lmm, f, O, D, Y, crop=12.0, nmax=1)])
    zs = np.arange(Y[2] + 1.0, Cz - 1.0, -0.1); yh = front(mx, zs); yref = front(mx, np.array([Y[2]]))[0]
    rec = yh - yref; notch = rec >= 1.2
    r1 = float(np.interp(Y[2] - 1.0, zs[::-1], rec[::-1])); ok1 = r1 >= 1.2
    top = float(zs[np.argmax(notch)]) if notch.any() else None
    ok2 = top is not None and abs(top - Y[2]) <= 0.8
    ok3 = float(np.interp(Cz + 0.9, zs[::-1], rec[::-1])) >= 1.2
    if not ok1: why.append(f"no notch: 1 mm below the Y the front ray is only {r1:.2f} mm behind the Y")
    if not ok2: why.append("notch top not within 0.8 mm of the Y")
    if not ok3: why.append("notch closed before the contact")
    ang = {}
    for sd, sg in (("L", 1), ("R", -1)):
        xs = mx + sg * np.array([0.5, 1.0, 1.5, 1.9]); zm = []
        for x in xs:
            r = front(x, zs) - yref; still = r < 0.6; k = np.argmax(~still) if (~still).any() else len(zs)
            zm.append(zs[max(k - 1, 0)] if k > 0 else np.nan)
        zm = np.array(zm)
        if top is None or np.isnan(zm).any():
            ang[sd] = None; continue
        ang[sd] = round(float(np.degrees(np.arctan2(Y[2] - zm[-1], 1.9))), 1)     # from the Y over the first ~2.5 mm
    ok4 = all(a is not None and 25 <= a <= 45 for a in ang.values())
    if not ok4: why.append(f"lobe margin angle {ang} outside 25-45 deg")
    nsep, nedge, bad = 0, 0, []
    for sd in ("L", "R"):
        for S in inp[sd]["walk"]:
            g = _gap_at(Lmm, f, S["U"], S["n"], S["b"], [max(0.25, S["v"] / 2) * S["eu2"][1]])[0]
            if _mouth_has_gap(g, scale=abs(S["nl2"][0])): nsep += 1
            else: bad.append((sd, S["s"]))
            hs = np.arange(1.0, -1.5, -0.05); r = _gap_at(Lmm, f, S["U"], S["n"], S["b"], hs)
            d0 = np.array([np.nan if x["d0"] is None else x["d0"] for x in r]); onf = d0 < 0.5 * max(S["sigma"], 0.6)
            k = np.argmax(~onf) if (~onf).any() else len(hs); he = hs[k - 1] if k > 0 else 1.0
            if abs(he) <= 0.5: nedge += 1
            else: bad.append(("edge", sd, S["s"], round(float(he), 2)))
    nw = 2 * len(inp["L"]["walk"]); ok5 = nsep == nw; ok6 = nedge == nw
    if not ok5: why.append(f"lips not separated at {nw - nsep}/{nw} stations e.g. {[b for b in bad if b[0] != 'edge'][:4]}")
    if not ok6: why.append(f"margin edge off U by > 0.5 mm at {nw - nedge}/{nw} stations {[b for b in bad if b[0] == 'edge'][:4]}")
    ok = ok1 and ok2 and ok3 and ok4 and ok5 and ok6
    return {"status": "PASS" if ok else "FAIL", "notch_recess_1mm_below_Y_mm": round(r1, 3), "notch_top_z": top, "Y_z": float(Y[2]),
            "lobe_angle_deg": ang, "separated_stations": f"{nsep}/{nw}", "margin_edge_ok": f"{nedge}/{nw}",
            "why": "; ".join(why) or "notch at the Y, margin over a slot along the whole line"}


def mouth_commissure_probe(Lmm, f, inp, side):
    if not inp:
        return {"status": "FAIL", "why": "builder gave no probe inputs"}
    P = inp[side]; corner = np.asarray(P["corner_mm"]); tip = None; why = []
    for S in P["tip"]:
        gs = _gap_at(Lmm, f, S["U"], S["n"], S["b"], [max(0.1, u * S["v"]) * S["eu2"][1] for u in (0.3, 0.5, 0.7)])
        if any(_mouth_has_gap(g, 0.05, 0.6, 0.05, abs(S["nl2"][0])) for g in gs):      # any ray across the slot
            tip = S
    dtip = float(np.linalg.norm(np.asarray(tip["U"]) - corner)) if tip else None
    ok1 = dtip is not None and dtip <= 0.7
    if not ok1: why.append(f"slot tip {dtip} mm from the corner (> 0.7)")
    other = inp["R" if side == "L" else "L"]["corner_mm"]; ok2 = abs(abs(corner[0] - inp["mid_x"]) - abs(other[0] - inp["mid_x"])) <= 0.3
    cp = np.asarray(P["crease"]); cl = np.asarray(P["crease_l"]); keep = np.linalg.norm(Lmm - corner, axis=1) < 8
    VN = vertex_normals(Lmm, f); tree = cKDTree(Lmm[keep]); VNk = VN[keep]; deps = []
    for l in (1.0, 2.0, 3.0):
        k = int(np.argmin(np.abs(cl - l))); p = cp[k]; tc = unit(cp[min(k + 1, len(cp) - 1)] - cp[max(k - 1, 0)])
        nb = tree.query_ball_point(p, 2.0); nc = unit(VNk[nb].mean(0)); nc = unit(nc - (nc @ tc) * tc)
        if nc @ np.asarray(P["tip"][-1]["n"]) < 0: nc = -nc                  # orient by the design normal (mesh-orientation free)
        lat = np.cross(nc, tc)
        O = np.array([p + w * lat + 2.0 * nc for w in (-1.6, 0.0, 1.6)]); H = _mouth_hits(Lmm, f, O, np.tile(-nc, (3, 1)), p, nmax=3)
        t = [h[0] if h else np.nan for h in H]; dep = t[1] - 0.5 * (t[0] + t[2]); deps.append(round(float(dep), 3))
        if l >= 2.0 and len(H[1]) >= 3 and H[1][2] - H[1][1] < 0.6: why.append(f"slot continues past the corner at {l} mm")
    expd = [P["crease_D0"] * (1 - l / P["crease_L"]) for l in (1, 2, 3)]
    ok3 = all(np.isfinite(d) and abs(d - e) <= 0.1 for d, e in zip(deps, expd))
    if not ok3: why.append(f"crease depth {deps} vs {np.round(expd, 3).tolist()} +-0.1")
    ok = ok1 and ok2 and ok3 and not any("past the corner" in w for w in why)
    return {"status": "PASS" if ok else "FAIL", "tip_to_corner_mm": None if dtip is None else round(dtip, 3), "crease_depth_mm": deps,
            "why": "; ".join(why) or "slot ends at the corner, crease set back"}


def mouth_chin_probe(Lmm, f, inp, env_npz=None):
    if not inp:
        return {"status": "FAIL", "why": "builder gave no probe inputs"}
    why = []; ok1 = True; rows = []
    for sd in ("L", "R"):
        W = inp[sd]["walk"]; S = min(W, key=lambda r: abs(abs(r["U"][0] - inp["mid_x"]) - 4.0))
        g = _gap_at(Lmm, f, S["U"], S["n"], S["b"], [-0.8, 0.6, max(0.25, S["v"] / 2) * S["eu2"][1]])
        sig = (g[0]["d0"] - g[1]["d0"]) if (g[0]["d0"] is not None and g[1]["d0"] is not None) else None
        o = sig is not None and sig > 0.3 and _mouth_has_gap(g[2], scale=abs(S["nl2"][0])); ok1 &= o; rows.append({"side": sd, "s": S["s"], "sigma": sig, "hidden_top": o})
    if not ok1: why.append("lower lip not recessed under a hidden top margin at x = mid +-4")
    sys.path.insert(0, os.path.join(ROOT, "tripo_rebuild")); import partition as PT  # noqa: E402
    from exact_sdf import closest_on_tri  # noqa: E402
    T = np.load(env_npz or os.path.join(ROOT, "tripo_rebuild", "tripo_welded.npz")); tv = PT.head_local(T["v"]) * 1000; tf = T["f"]
    Cz = inp["contact_mm"][2]; c = np.asarray(inp["contact_mm"])
    m = (np.abs(Lmm[:, 0] - inp["mid_x"]) < 6) & (Lmm[:, 2] < Cz - 2) & (Lmm[:, 2] > Cz - 8) & (Lmm[:, 1] < c[1] + 6)
    Q = Lmm[m]
    if len(Q) < 20:
        return {"status": "FAIL", "why": "no chin surface found", "lower_lip": rows}
    near = np.linalg.norm(tv[tf].mean(1) - c, axis=1) < 20; tfn = tf[near]; cen = tv[tfn].mean(1)
    _, nn = cKDTree(cen).query(Q, k=8); best = np.full(len(Q), np.inf)
    for k in range(8):
        t = tfn[nn[:, k]]; best = np.minimum(best, np.linalg.norm(Q - closest_on_tri(Q, tv[t[:, 0]], tv[t[:, 1]], tv[t[:, 2]]), axis=1))
    med = float(np.median(best)); ok2 = abs(med - 1.5) <= 0.5
    if not ok2: why.append(f"chin {med:.2f} mm inside the envelope (want 1.5 +-0.5)")
    ok = ok1 and ok2
    return {"status": "PASS" if ok else "FAIL", "lower_lip": rows, "chin_inset_median_mm": round(med, 3),
            "chin_inset_p10_p90_mm": [round(float(np.percentile(best, 10)), 3), round(float(np.percentile(best, 90)), 3)],
            "why": "; ".join(why) or "recessed lower lip with a hidden top margin; chin inset as C3"}


for _sd in ("R", "L"):
    PROBES[f"upper_lip_overhang.{_sd}"] = (lambda sd: lambda Lmm, f, inp: mouth_overhang_probe(Lmm, f, inp, sd))(_sd)
    PROBES[f"commissure.{_sd}"] = (lambda sd: lambda Lmm, f, inp: mouth_commissure_probe(Lmm, f, inp, sd))(_sd)
PROBES["mouth_crease"] = mouth_crease_probe
PROBES["lower_lip_chin"] = mouth_chin_probe
BUILT_PROBES = sorted(set(BUILT_PROBES) | {"upper_lip_overhang.R", "upper_lip_overhang.L", "commissure.R", "commissure.L",
                                           "mouth_crease", "lower_lip_chin"})
MOUTH_PARTS = ["upper_lip_overhang.R", "upper_lip_overhang.L", "mouth_crease", "commissure.R", "commissure.L", "lower_lip_chin"]


def register_mouth(inputs):
    """feat-mouth builder: every mouth part gets the same input dict (feat_mouth.probe_inputs())"""
    register("feat-mouth", MOUTH_PARTS, {p: inputs for p in MOUTH_PARTS})


# ---------------------------------------------------------------- EARS block (builder 'feat-ears', 2026-10-18; appended)
# henrys_pocket.<sd> = check_ears B1's fixed P1 (engine/packs/felid/features/feat_ears.pocket_probe): across lines from
# 40 mm lateral (parity) on every slot height of spec_ears tables; PASS needs two layers + open slot, depth = the table
# +-0.5 mm, flap tissue 0.4-1.1 mm at a = 0.5 / 1 / 2 / 3 mm below the free edge, at D/2 >= 2 mm thinner than Tripo's
# lip, and the free edge within 0.5 mm. Head-frame mm only (run with --headframe). No inputs needed (the probe reads
# the spec tables and ears_base_<sd>.npz itself); helix / conch / ear_shell stay declared stubs (OPEN).
def _feat_ears():
    import importlib
    fp = os.path.join(HERE, "..", "packs", "felid", "features")
    if fp not in sys.path:
        sys.path.insert(0, fp)
    return importlib.import_module("feat_ears")


def ears_pocket_probe(Lmm, f, inp, side):
    r = _feat_ears().pocket_probe(Lmm, f, inp or {}, side)
    r = dict(r); r.pop("rows", None)                       # the per-height rows stay in feat_ears' own report
    return r


for _sd in ("R", "L"):
    PROBES[f"henrys_pocket.{_sd}"] = (lambda s: (lambda Lmm, f, inp: ears_pocket_probe(Lmm, f, inp, s)))(_sd)
BUILT_PROBES = sorted(set(BUILT_PROBES) | {"henrys_pocket.R", "henrys_pocket.L"})


def register_ears():
    """feat-ears builder: Henry's pocket both sides (no inputs: the probe reads the spec tables)"""
    register("feat-ears", ["henrys_pocket.R", "henrys_pocket.L"], {})


# ---------------------------------------------------------------- NOSE block (feat-nose builder, 2026-10-18; spec_nose.json +
# the check_nose.json fixes). Appended; the entries above are unchanged. Every probe reads geometry only (E5), plus the
# skin's coat-depth attribute where the part IS the coat boundary (leather, crease). Lmm = head-frame mm vertices.
def _closest_dist(Q, Lmm, f, k=8):
    """exact unsigned point-to-mesh distance (nearest k face centroids -> exact point-triangle) and the hit face"""
    sys.path.insert(0, os.path.join(ROOT, "tripo_rebuild")); import exact_sdf  # noqa: E402
    tr = cKDTree(Lmm[f].mean(1)); _, nn = tr.query(Q, k=min(k, len(f))); best = np.full(len(Q), np.inf); bi = np.zeros(len(Q), int)
    bc = np.zeros_like(Q)
    for j in range(nn.shape[1]):
        t = nn[:, j]; c = exact_sdf.closest_on_tri(Q, Lmm[f[t, 0]], Lmm[f[t, 1]], Lmm[f[t, 2]]); d = np.linalg.norm(Q - c, axis=1)
        b = d < best; best[b] = d[b]; bi[b] = t[b]; bc[b] = c[b]
    return best, bi, bc


def _in_air(Q, Lmm, f, fn=None):
    """signed distance by the nearest face's outward normal (+ = air); the mesh must be consistently outward"""
    d, i, c = _closest_dist(Q, Lmm, f); fn = face_normals(Lmm, f) if fn is None else fn
    s = np.sign(np.einsum("ij,ij->i", Q - c, fn[i])); return d * np.where(s == 0, 1, s)


def vestibule_probe(Lmm, f, inp, path_mark=8.0, axis_mark=3.0, clear=0.3):
    """check_nose B1 fix: air path ALONG THE CENTRELINE (every sample in air with clearance >= 0.3 mm) >= 8.0 mm, plus
    the straight axis ray from H along T0 >= 3.0 mm (Tripo dish 2.15 / 2.31 mm); hidden end: no straight segment from
    the rim lifted 1 mm along n_out to the end of the air path is free of skin."""
    cl = np.asarray(inp["centreline_mm"], float); s = np.asarray(inp["centreline_s_mm"], float); H = np.asarray(inp["H_mm"], float)
    keep = np.linalg.norm(Lmm[f].mean(1) - H, axis=1) < 25; ff = f[keep]
    sd = _in_air(cl, Lmm, ff); ok = sd >= clear; bad = np.nonzero(~ok)[0]
    path = float(s[bad[0]] if len(bad) else s[-1])
    T, _ = first_hit(H[None], unit(inp["T0"])[None], Lmm[ff]); axis = float(T[0])
    end = cl[min(len(cl) - 1, int(np.searchsorted(s, min(path, s[-1]))))]
    rim = np.asarray(inp["rim_mm"], float) + 1.0 * np.asarray(inp["n_out"], float)
    D = end - rim; ln = np.linalg.norm(D, axis=1); Th, _ = first_hit(rim, D / ln[:, None], Lmm[ff], tmax=float(ln.max()))
    seen = int((Th >= ln - 1e-6).sum())
    st = path >= path_mark and axis >= axis_mark and seen == 0
    return {"status": "PASS" if st else "FAIL", "air_path_mm": round(path, 2), "path_mark_mm": path_mark, "axis_ray_mm": round(axis, 2),
            "axis_mark_mm": axis_mark, "min_clearance_first_2mm": round(float(sd[s <= 2].min()), 2), "rim_lines_seeing_end": seen,
            "why": "passage along the centreline" if st else "air path / axis ray short or the end visible"}


def _section_polar(Lmm, ff, c, T, nang=72, rmax=4.0):
    t1, t2 = perp_basis(unit(T)); ang = np.arange(nang) * 2 * np.pi / nang
    D = np.outer(np.cos(ang), t1) + np.outer(np.sin(ang), t2); Tt, _ = first_hit(np.repeat(c[None], nang, 0), D, ff, tmax=rmax)
    return ang, np.minimum(Tt, rmax), t1, t2


def alar_fold_probe(Lmm, f, inp, stations=(1.5, 2.5, 3.5), defect_mark=0.15, clear_mark=0.4, crown=(0.4, 0.9)):
    """nostril wing = (a) the INNER alar fold: lumen sections at s 1.5/2.5/3.5 mm are crescents - convexity defect (hull
    area - area)/hull >= 0.15 on the lateral-dorsal side (within 60 deg), clear width >= 0.4 mm, section centre in air;
    (b) the OUTER ala: crown height along n_out over the PATCHED (dish-filled, no-ala) surface at the ala centre +-0.8 mm
    along e1 in [0.4, 0.9] mm (check_nose B4: not over the groove floor). The patched-surface level is a builder input
    (ala_patched_level_mm: signed offset along n_out from the ala centre)."""
    from scipy.spatial import ConvexHull
    cl = np.asarray(inp["centreline_mm"], float); s = np.asarray(inp["centreline_s_mm"], float); H = np.asarray(inp["H_mm"], float)
    keep = np.linalg.norm(Lmm[f].mean(1) - H, axis=1) < 20; ff = Lmm[f[keep]]; fk = f[keep]
    ld = unit(inp["lateral_dorsal"]); secs = []; okA = True
    for st in stations:
        i = int(np.argmin(np.abs(s - st))); c = cl[i]; T = cl[min(i + 1, len(cl) - 1)] - cl[max(i - 1, 0)]
        air = float(_in_air(c[None], Lmm, fk)[0])
        ang, r, t1, t2 = _section_polar(Lmm, ff, c, T)
        xy = np.c_[r * np.cos(ang), r * np.sin(ang)]
        area = 0.5 * abs(np.sum(xy[:, 0] * np.roll(xy[:, 1], -1) - np.roll(xy[:, 0], -1) * xy[:, 1]))
        try:
            hull = ConvexHull(xy); ha = float(hull.volume)
        except Exception:
            ha = area
        defect = (ha - area) / max(ha, 1e-9)
        # where is the defect: hull radius - r per angle (hull radius by ray-polygon on the hull vertices)
        hv = xy[hull.vertices] if ha > area else xy; hv = np.vstack([hv, hv[:1]])
        dense = np.vstack([hv[j] + np.linspace(0, 1, 60, endpoint=False)[:, None] * (hv[j + 1] - hv[j]) for j in range(len(hv) - 1)])
        da = np.arctan2(dense[:, 1], dense[:, 0]) % (2 * np.pi); o = np.argsort(da)
        rh = np.interp(ang, da[o], np.linalg.norm(dense, axis=1)[o], period=2 * np.pi)
        gap = rh - r; k = int(np.argmax(gap)); dvec = np.cos(ang[k]) * t1 + np.sin(ang[k]) * t2
        dang = float(np.degrees(np.arccos(np.clip(dvec @ unit(ld - (ld @ unit(T)) * unit(T)), -1, 1))))
        width = float(np.min(r[:len(r) // 2] + r[len(r) // 2:]))
        ok = air > 0 and defect >= defect_mark and dang <= 60 and width >= clear_mark and r.max() < 4.0
        okA &= ok
        secs.append({"s_mm": st, "centre_in_air_mm": round(air, 2), "defect": round(float(defect), 3), "defect_dir_deg": round(dang, 1),
                     "clear_width_mm": round(width, 2), "area_mm2": round(float(area), 2), "pass": bool(ok)})
    crowns = []; pts = inp.get("ala_patched_pts_mm"); nrs = inp.get("ala_patched_normals")
    lvl = pts
    for j in range(len(pts or [])):
        p = np.asarray(pts[j], float); n = unit(nrs[j]); Tt, _ = first_hit((p + 3 * n)[None], (-n)[None], ff, tmax=6.0)
        crowns.append(float(3 - Tt[0]))
    okB = lvl is not None and all(crown[0] <= x <= crown[1] for x in crowns)
    st = okA and okB
    return {"status": "PASS" if st else "FAIL", "inner_fold_sections": secs, "ala_crown_over_patched_mm": [round(x, 3) for x in crowns],
            "crown_window_mm": list(crown), "why": ("inner fold crescent + ala crown" if st else
                                                    ("inner fold: " + ("ok" if okA else "FAIL") + "; ala crown: " + ("ok" if okB else "FAIL")))}


def _front_profile(Lmm, ff, z, xs, y0=-95.0):
    O = np.c_[xs, np.full(len(xs), y0), np.full(len(xs), z)]; D = np.tile([0, 1.0, 0], (len(xs), 1))
    T, _ = first_hit(O, D, ff, tmax=40.0); return y0 + T


def philtrum_probe(Lmm, f, inp, step=0.5, xtol=0.4, dtol=0.2, wtol=0.3, L=1.5):
    """horizontal sections every 0.5 mm z -11.3 .. -19.3: the front profile y(x) (rays along +y); groove = largest
    straight-edge depth (chord over +-1.5 mm); minimum within |x - x_c| <= 0.4 mm (x_c -0.2 -> -0.5, check_nose B3:
    midline waypoint), depth within +-0.2 and half-depth width within +-0.3 mm of the stations (linear between);
    continuous: >= 90 % of sections pass and no two adjacent sections fail."""
    Z = np.asarray(inp["z_mm"]); Dp = np.asarray(inp["depth_mm"]); W = np.asarray(inp["half_depth_width_mm"]); X = np.asarray(inp["x_mm"])
    sel = (np.abs(Lmm[f].mean(1)[:, 0]) < 6) & (Lmm[f].mean(1)[:, 2] < Z[0] + 2) & (Lmm[f].mean(1)[:, 2] > Z[-1] - 2)
    ff = Lmm[f[sel]]; xs = np.arange(-3.6, 3.6001, 0.05); rows = []
    for z in np.arange(Z[0], Z[-1] - 1e-6, -step):
        y = _front_profile(Lmm, ff, z, xs); xc = np.interp(-z, -Z, X); dt = np.interp(-z, -Z, Dp); wt = np.interp(-z, -Z, W)
        nL = int(round(L / 0.05)); dep = np.full(len(xs), -np.inf)
        for i in range(nL, len(xs) - nL):
            if np.isfinite(y[i - nL]) and np.isfinite(y[i + nL]) and np.isfinite(y[i]):
                dep[i] = y[i] - 0.5 * (y[i - nL] + y[i + nL])
        win = np.abs(xs - xc) <= 1.5; i = int(np.nonzero(win)[0][np.argmax(dep[win])]); d = float(dep[i])
        chord = y[i - nL] + (y[i + nL] - y[i - nL]) * (xs - xs[i - nL]) / (xs[i + nL] - xs[i - nL])
        prof = y - chord; j0 = i; j1 = i
        while j0 > i - nL and prof[j0] >= d / 2: j0 -= 1
        while j1 < i + nL and prof[j1] >= d / 2: j1 += 1
        hw = float(xs[j1] - xs[j0])
        ok = abs(xs[i] - xc) <= xtol and abs(d - dt) <= dtol and abs(hw - wt) <= wtol and d > 0.05
        rows.append({"z": round(float(z), 2), "x_min": round(float(xs[i]), 2), "depth": round(d, 3), "hw": round(hw, 2), "pass": bool(ok)})
    pf = np.array([r["pass"] for r in rows]); adj = bool(np.any(~pf[1:] & ~pf[:-1]))
    st = pf.mean() >= 0.9 and not adj
    return {"status": "PASS" if st else "FAIL", "sections": len(rows), "pass_frac": round(float(pf.mean()), 3), "adjacent_fails": adj,
            "depth_by_z": [(r["z"], r["depth"], r["hw"], r["x_min"]) for r in rows],
            "why": "philtrum groove along the midline" if st else f"{int((~pf).sum())} of {len(rows)} sections out of tolerance"}


def _mesh_depth(inp, nv):
    p = inp.get("depth_npz")
    if p is None:
        return None
    d = np.load(p)["depth_mm"]
    return d if len(d) == nv else None


def nose_leather_probe(Lmm, f, inp, band=0.25):
    """furless leather = the skin's depth_mm < 0.05 on the front (y < -66): LOWER half widths at z -10/-12/-14 within
    0.5 mm of Phase 1 leather['0'] (14.56 / 9.16 / 5.84); the upper half is the approved edge (leather_bridge_crease).
    (check_nose B2: the photo bbox is dropped until a camera is registered: estimated, not checked.)"""
    dep = _mesh_depth(inp, len(Lmm))
    if dep is None:
        return {"status": "FAIL", "why": "no coat depth (depth_npz) for this mesh"}
    fl = (dep < 0.05) & (Lmm[:, 1] < -60); out = {}; ok = True
    for zs, wt in inp["widths"].items():
        m = fl & (np.abs(Lmm[:, 2] - float(zs)) < band)
        w = float(np.ptp(Lmm[m, 0])) if m.sum() > 2 else 0.0; out[zs] = round(w, 2); ok &= abs(w - wt) <= inp.get("tol_mm", 0.5)
    return {"status": "PASS" if ok else "FAIL", "widths_mm": out, "targets_mm": inp["widths"], "why": "lower leather widths vs Phase 1"}


def _iso_points(v, f, d, iso):
    E = np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]); E = np.unique(np.sort(E, 1), axis=0)
    a, b = d[E[:, 0]] - iso, d[E[:, 1]] - iso; m = (a * b) < 0; t = a[m] / (a[m] - b[m])
    return v[E[m, 0]] + t[:, None] * (v[E[m, 1]] - v[E[m, 0]])


def _ref_crop(inp):
    hd = json.load(open(inp["fit_json"]))["head"]; C = np.array(hd["C"]); R = np.array(hd["R"])
    Z = np.load(inp["ref_npz"]); v = (Z["v"] - C) @ R * 1000.0; f = Z["f"]; dep = Z["depth_mm"]
    box = (np.abs(v[:, 0]) < 16) & (v[:, 1] > -80) & (v[:, 1] < -55) & (v[:, 2] > -26) & (v[:, 2] < 2)
    keep = box[f].all(1); f = f[keep]; idx = np.unique(f); rm = -np.ones(len(v), int); rm[idx] = np.arange(len(idx))
    return v[idx], rm[f], dep[idx]


def leather_bridge_crease_probe(Lmm, f, inp, p95=0.20, mx=0.30):
    """approved_top_edge_regression against the person-approved skin v1 (spec T1-T4), OUTSIDE the photo-shown tail-entry
    zones (person 05:15; balls of tail_zone_mm about each alar-groove tail segment, reported):
    T1 iso depth 0.15 / 0.6 in the sector (0.05 reported, not gating: ill-conditioned, see the result note) z >= -9, y <= -67: two-sided nearest distance p95 <= 0.20, max <= 0.30 mm;
    T2 every v1 vertex of the protected band (<= 4 mm of the arc, z > -9.5, y < -62) to the built surface p95 0.20 / max 0.30,
       and the reverse for built vertices in the band; T3 coat depth at the band vertices |delta| p95 <= 0.20;
    T4 x = 0 sagittal front profile z -6.5 .. 0 within 0.20 mm. Below z -9 (the unapproved rest of the crease) the
    spec's coat-step test is NOT built here (OPEN)."""
    dep = _mesh_depth(inp, len(Lmm))
    if dep is None:
        return {"status": "FAIL", "why": "no coat depth (depth_npz) for this mesh"}
    rv, rf, rd = _ref_crop(inp)
    segs = [(np.asarray(a, float), np.asarray(b, float)) for a, b in inp["tail_segments_mm"]]; zr = float(inp["tail_zone_mm"])

    def outside_zone(P):
        m = np.ones(len(P), bool)
        for a, b in segs:
            ab = b - a; t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1); m &= np.linalg.norm(P - (a + t[:, None] * ab), axis=1) >= zr
        return m

    def sector(P):
        return (P[:, 2] >= -9.0) & (P[:, 1] <= -67.0)
    res = {}; ok = True
    rims = [np.asarray(r, float) for r in inp.get("nostril_rims_mm", [])]
    cls = [np.asarray(c, float) for c in inp.get("vestibule_centrelines_mm", [])]

    def outside_nostril(P, dil=1.0):
        """the nostrils are NOT approved (ORCHESTRATOR 04:52): band points over a rim (inside its polygon, <= 4 mm of its
        plane) or within dil of it are nostril territory, excluded and counted"""
        from matplotlib.path import Path
        m = np.ones(len(P), bool)
        for rim in rims:
            c = rim.mean(0); _, _, Vt = np.linalg.svd(rim - c); u1, u2, nn = Vt[0], Vt[1], Vt[2]
            q = P - c; inside = Path(np.c_[(rim - c) @ u1, (rim - c) @ u2]).contains_points(np.c_[q @ u1, q @ u2]) & (np.abs(q @ nn) < 4)
            m &= ~inside & (cKDTree(rim).query(P)[0] >= dil)
        for cl in cls:                                  # the new vestibule walls (inside v1's tissue) are nostril territory too
            m &= cKDTree(cl).query(P)[0] >= 2.5
        return m
    arc_ref = _iso_points(rv, rf, rd, 0.05); arc_ref = arc_ref[sector(arc_ref) & (arc_ref[:, 1] < -60)]
    for iso in (0.05, 0.15, 0.6):
        A = _iso_points(rv, rf, rd, iso); A = A[sector(A)]; A = A[outside_zone(A) & outside_nostril(A)]
        B = _iso_points(Lmm, f, dep, iso); B = B[sector(B)]; B = B[outside_zone(B) & outside_nostril(B)]
        if len(A) == 0 or len(B) == 0:
            res[f"T1_iso{iso}"] = "missing"; ok = False; continue
        dab = cKDTree(B).query(A)[0]; dba = cKDTree(A).query(B)[0]
        r = {"p95_ref_to_built": round(float(np.percentile(dab, 95)), 3), "max_ref_to_built": round(float(dab.max()), 3),
             "p95_built_to_ref": round(float(np.percentile(dba, 95)), 3), "max_built_to_ref": round(float(dba.max()), 3)}
        r["pass"] = bool(max(r["p95_ref_to_built"], r["p95_built_to_ref"]) <= p95 and max(r["max_ref_to_built"], r["max_built_to_ref"]) <= mx)
        if iso == 0.05:
            r["gating"] = False; r["note"] = ("iso 0.05 is ill-conditioned: v1's depth hovers 0.00-0.05 over ~0.5 mm strips at the ramp foot, "
                                               "so a re-tessellated copy of v1 itself reads p95 ~0.25 / max ~0.34 mm (the preview's grafted band); "
                                               "reported, not gating; iso 0.15 is the conditioned stand-in")
        else:
            ok &= r["pass"]
        res[f"T1_iso{iso}"] = r
    darc = cKDTree(arc_ref).query(rv)[0]; band0 = (darc <= 4.0) & (rv[:, 2] > -9.5) & (rv[:, 1] < -62) & outside_zone(rv)
    band = band0 & outside_nostril(rv); res["T2_nostril_excluded_ref_verts"] = int(band0.sum() - band.sum())
    d1, fi, cc = _closest_dist(rv[band], Lmm, f)
    darc_b = cKDTree(arc_ref).query(Lmm)[0]; bandb = (darc_b <= 4.0) & (Lmm[:, 2] > -9.5) & (Lmm[:, 1] < -62) & outside_zone(Lmm) & outside_nostril(Lmm)
    d2, _, _ = _closest_dist(Lmm[bandb], rv, rf)
    r = {"n_ref": int(band.sum()), "p95_ref_to_built": round(float(np.percentile(d1, 95)), 3), "max_ref_to_built": round(float(d1.max()), 3),
         "n_built": int(bandb.sum()), "p95_built_to_ref": round(float(np.percentile(d2, 95)), 3) if len(d2) else None,
         "max_built_to_ref": round(float(d2.max()), 3) if len(d2) else None}
    r["pass"] = bool(len(d2) and max(r["p95_ref_to_built"], r["p95_built_to_ref"]) <= p95 and max(r["max_ref_to_built"], r["max_built_to_ref"]) <= mx)
    ok &= r["pass"]; res["T2_surface"] = r
    # T3 coat: barycentric depth of the closest built triangle
    tri = Lmm[f[fi]]; v0, e1, e2 = tri[:, 0], tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]; q = cc - v0
    d00, d01, d11 = (e1 * e1).sum(1), (e1 * e2).sum(1), (e2 * e2).sum(1); d20, d21 = (q * e1).sum(1), (q * e2).sum(1)
    den = np.maximum(d00 * d11 - d01 * d01, 1e-18); bb = (d11 * d20 - d01 * d21) / den; cg = (d00 * d21 - d01 * d20) / den
    db = dep[f[fi, 0]] * (1 - bb - cg) + dep[f[fi, 1]] * bb + dep[f[fi, 2]] * cg; dd = np.abs(db - rd[band])
    r = {"p95_abs_delta_mm": round(float(np.percentile(dd, 95)), 3), "max_abs_delta_mm": round(float(dd.max()), 3)}
    r["pass"] = bool(r["p95_abs_delta_mm"] <= p95); ok &= r["pass"]; res["T3_coat"] = r
    zs = np.arange(-6.5, 0.001, 0.1); xs = np.zeros(len(zs))
    O = np.c_[xs, np.full(len(zs), -95.0), zs]; D = np.tile([0, 1.0, 0], (len(zs), 1))
    sb = np.abs(Lmm[f].mean(1)[:, 0]) < 2; sr = np.abs(rv[rf].mean(1)[:, 0]) < 2
    yb = first_hit(O, D, Lmm[f[sb]], tmax=40)[0]; yr = first_hit(O, D, rv[rf[sr]], tmax=40)[0]; dy = np.abs(yb - yr)
    r = {"max_dy_mm": round(float(np.nanmax(dy)), 3), "p95_dy_mm": round(float(np.percentile(dy, 95)), 3)}
    r["pass"] = bool(np.isfinite(dy).all() and r["max_dy_mm"] <= p95); ok &= r["pass"]; res["T4_midline"] = r
    zx = [a for a in _iso_points(rv, rf, rd, 0.05) if a[2] >= -9.0 and a[1] <= -67.0]
    zx = np.array(zx); inz = ~outside_zone(zx) if len(zx) else np.zeros(0, bool)
    res["tail_entry_zones"] = {"radius_mm": zr, "ref_arc_points_excluded": int(inz.sum()), "ref_arc_points_total": int(len(zx)),
                               "excluded_extent_head_mm": (np.round(zx[inz].min(0), 2).tolist() + np.round(zx[inz].max(0), 2).tolist()) if inz.any() else []}
    return {"status": "PASS" if ok else "FAIL", **res, "why": "approved top edge kept (outside the tail-entry zones)" if ok else "approved top edge moved"}


def _needs_inputs(fn):
    def p(Lmm, f, inp):
        if not inp:
            return {"status": "FAIL", "why": "builder gave no probe inputs"}
        return fn(Lmm, f, inp)
    p.__name__ = fn.__name__; p.__doc__ = fn.__doc__; return p


nose_leather_probe, leather_bridge_crease_probe, philtrum_probe, alar_fold_probe, vestibule_probe = map(
    _needs_inputs, (nose_leather_probe, leather_bridge_crease_probe, philtrum_probe, alar_fold_probe, vestibule_probe))
PROBES["nose_leather"] = nose_leather_probe
PROBES["leather_bridge_crease"] = leather_bridge_crease_probe
PROBES["philtrum"] = philtrum_probe
for _sd in ("R", "L"):
    PROBES[f"alar_fold.{_sd}"] = alar_fold_probe
    PROBES[f"vestibule_path.{_sd}"] = vestibule_probe        # not an INVENTORY sub-part (that entry is not mine to rewrite);
                                                              # run with the nostril inputs alongside nostril_cavity
BUILT_PROBES = sorted(set(BUILT_PROBES) | {"nose_leather", "leather_bridge_crease", "philtrum", "alar_fold.R", "alar_fold.L"})
NOSE_PARTS = ["nostril_cavity.R", "nostril_cavity.L", "alar_fold.R", "alar_fold.L", "leather_bridge_crease", "philtrum", "nose_leather"]


def register_nose(base_F=None, depth_npz=None):
    """feat-nose builder: inputs from engine/packs/felid/features/feat_nose.probe_inputs(); base_F(P_head_mm) -> F_mm of
    the skin the edit was applied to (for the ala's patched-surface level); depth_npz = the mesh's coat depth file"""
    import importlib
    fp = os.path.join(HERE, "..", "packs", "felid", "features")
    if fp not in sys.path:
        sys.path.insert(0, fp)
    FN = importlib.import_module("feat_nose"); inp = FN.probe_inputs()
    if base_F is not None:
        for k, x in FN.ala_patched_inputs(base_F).items():
            inp[k].update(x)
    for k in inp:
        if depth_npz:
            inp[k]["depth_npz"] = depth_npz
    for sd in ("R", "L"):
        inp[f"vestibule_path.{sd}"] = inp[f"alar_fold.{sd}"]
    register("feat-nose", NOSE_PARTS, {p: inp[p] for p in NOSE_PARTS})
    return inp


def run(Lmm, f, entries=None):
    entries = entries or inventory_entries(); owner = {}
    for name, b in REGISTRY.items():
        for p in b["parts"]:
            owner.setdefault(p, []).append(name)
    rows = []
    for region, text, key in entries:
        if key is None:
            rows.append({"region": region, "entry": text, "status": "FAIL", "why": "inventory entry has no part ids in inventory_check.INVENTORY"}); continue
        subs = []
        for sp in INVENTORY[key]:
            if sp not in owner:
                subs.append({"part": sp, "status": "FAIL", "why": "no registered builder"}); continue
            bname = owner[sp][0]; inp = REGISTRY[bname]["inputs"].get(sp)
            if PROBES[sp] in (nostril_probe, eyelid_probe) and inp is None:
                subs.append({"part": sp, "builder": bname, "status": "FAIL", "why": "builder gave no probe inputs"}); continue
            r = PROBES[sp](Lmm, f, inp or {}); subs.append({"part": sp, "builder": bname, **r})
        st = "PASS" if all(s["status"] == "PASS" for s in subs) else "FAIL"
        rows.append({"region": region, "entry": text, "status": st, "parts": subs})
    return rows


def main(argv):
    T = np.load(argv[0]); v, f = T["v"], T["f"]
    if "--headframe" in argv:
        sys.path.insert(0, os.path.join(ROOT, "tripo_rebuild")); import partition as PT  # noqa: E402
        Lmm = PT.head_local(v) * 1000
    else:
        Lmm = v * 1000.0
    load_manifest(argv[1]); rows = run(Lmm, f)
    for r in rows:
        print(f"{r['status']}  {r['region']:6s} {r['entry'][:60]}")
        for s in r.get("parts", []):
            print(f"        {s['status']}  {s['part']:24s} {s.get('why', '')}")
    n = sum(r["status"] == "FAIL" for r in rows); print(f"\n{n} of {len(rows)} inventory entries FAIL")
    outs = [a for a in argv[2:] if a.endswith(".json")]
    if outs:
        json.dump(rows, open(outs[0], "w"), indent=1)
    return n


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1:]) else 0)
