"""EARS v3 feature (felid pack, case cat1, cat v3) - builder 'feat-ears-v3', 2026-10-18. feat_ears.py (v2) is IMPORTED and
left unchanged: Henry's pocket (flap + slot, check_ears B1/B2/S1-S3 fixes), the coat cap and the v2 probes all stand.
Head-frame mm throughout (partition.head_local(world) * 1000); a field F is negative inside tissue.

WHAT CHANGES (V3_BRIEF 'EARS'; NOTES_v3 RULINGS A20 + DECISIONS)
  * RESOLUTION CONTRACT (A20), DECLARED. REGION per ear = the v2 pocket box UNION the pinna box (the shell carve below
    reaches the whole cupped plate), NEED_MM = 0.125 inside it: the flap's free edge is T_EDGE 0.6 mm of tissue and the
    slot is >= G_MIN 0.5 mm of air, so 0.125 mm gives >= 4 voxels across each (v2 was integrated at 0.5 mm: flap and slot
    at or below one voxel -> the shredded pocket of the person's 07:00 review). opening_sdf(P) = the INTENDED AIR of the
    pocket slot (v2 Ear.fields slot, hard-carved): fill_voids must never seal it.
  * INNER SHELL CARVED (D3, the person: "The inner-ear bulge is baked hair ... It must be removed from the skin").
    THE CLASS RULE (NOTES_v3 DIRECTION: the unseen / untrusted side comes from a fitted model of the class, never from
    the mesh's mass): a cat pinna is a THIN CUPPED SHEET (lanz_wood_2005: elastic cartilage plate with skin on both faces;
    spec_ears structure.shell: mid 1.0-1.5 mm, apex 0.5-0.8 mm tissue, ESTIMATE). Its BACK (convex) skin is the trusted
    surface (Tripo's back fur is short; the v2 skin there = envelope inset by ear_back). So the INNER skin = the back skin
    offset forward by the sheet thickness T(h), rim to rim; anything farther from the back skin than T(h) is the baked
    hair and becomes air:  F <- max(F, dist(P, BACK) - T(h)), weighted in.
      BACK (per ear, cached in layers/feat_ears_v3_shell.npz): sections of skin v2 (layers/skin.npz, read only) every
      SEC_DH mm perpendicular to the ear axis, h/H in [H_LO, H_HI]; in each section the ear's loop is walked from its
      most-caudal point both ways until the smoothed tangent has turned TURN_MAX (180 deg = the rim tip, where the outer
      skin folds over into the inner face). That convex chain - and only it - is the back skin, rims included, so the
      rims stay ON the outline the photo sees (spec structure.shell). v3 skin_build's run-1 carve used 'n.w < 0.2'
      instead, which also takes the lump's own side walls as 'back' and left p99 bulge 10 mm (skin_v3_decisions D3).
      The walk also stops EXT_ARC past the loop's medial / lateral extreme (near the apex the loop is convex all round,
      so 180 deg each way would take the whole loop, front lump included).
      The carve is a smooth max (CARVE_K) with T_eff = T(h) + (1 - w) CARVE_SOFT: the weight w moves the carved SURFACE
      in from beyond the lump, so no enclosed void can form (a field-value blend did: run 1, 26 floating pieces).
      T(h): spec structure.shell numbers (1.5 mm at the base of the plate, 1.25 mid, 0.8 at the apex; ESTIMATE, low).
      Kept clear of Henry's pocket zone (1 mm, ramped over 1 mm) and tapered in at h/H 0.22-0.30 (the conch / head below).
  * OWNERSHIP (J15): this module OWNS the inner-ear carve. The integrator must NOT also apply skin_build_v3 Chain step 4
    (ear_carve) when it uses feat_ears_v3 (OWNS = {...} below says so).
  * The pocket itself: v2's construction, now meshed at <= 0.125 mm. Probes unchanged from v2 (check_ears B1 window).

API (skin_build_v3 / skin_feat_integrate read these names; v2 names kept):
  REGION {sd: (lo, hi)} ; NEED_MM ; RESOLUTION ; OWNS ; EARS (v2 Ear objects) ; edit(P, F, D_mm=None) ;
  opening_sdf(P) ; shell_carve(P, F) ; coat_cap_mm / skin_cap_apply (v2) ; PROBES {name: f(Lmm, f, inp)}
usage: the preview + probes are tripo_rebuild/ears_v3_preview.py (preview [grid] | probe).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import feat_ears as V2  # noqa: E402  (Phase 2, unchanged)

PT = V2.PT
TR = V2.TR
LAYERS = os.path.join(TR, "layers")
SHELL_FILE = os.path.join(LAYERS, "feat_ears_v3_shell.npz")
SKIN_V2 = os.path.join(LAYERS, "skin.npz")                 # v2 skin (progress marker, read only)
_ss, _unit = V2._ss, V2._unit

# ------------------------------------------------------------------ the resolution contract (A20), declared
GRID_CAP_MM = 0.15
NEED_MM = 0.125
RESOLUTION = {"region_mm": NEED_MM, "cap_mm": GRID_CAP_MM,
              "source": "flap free edge T_EDGE 0.6 mm tissue and slot >= G_MIN 0.5 mm air (feat_ears v2) -> >= 4 voxels "
                        "across each at 0.125 mm; the shell sheet T >= 0.8 mm -> >= 6 voxels; = skin_build_v3 r = 4 at 0.5 mm"}
OWNS = {"inner_ear_carve": True, "pocket": True,
        "note": "skin_build_v3.Chain step 4 (ear_carve) must be skipped when this module is used"}

# ------------------------------------------------------------------ the shell (class model) parameters
SEC_DH = 0.25           # section spacing along the ear axis (mm)
SEC_DS = 0.1            # chain resample step (mm)
TAN_HALF = 0.5          # tangent smoothing half-window (mm of arc)
TURN_MAX = np.pi        # the back chain ends where the tangent has turned 180 deg (rim tip)
H_LO, H_HI = 0.18, 0.99 # h / H range of the sections
RAD_MAX = 34.0          # loops whose centroid is farther than this from the ear axis are not the ear
CARVE_H = (0.22, 0.30, 0.94, 0.97)   # carve weight ramps in over h/H 0.22-0.30, out over 0.94-0.97
CARVE_RAD = 32.0
T_SHELL_HH = np.array([0.25, 0.60, 0.97])
T_SHELL_MM = np.array([1.50, 1.25, 0.80])   # spec_ears structure.shell: mid 1.0-1.5, apex 0.5-0.8 (ESTIMATE, low)
POCKET_CLEAR = 1.0      # keep the carve this far (mm) outside v2's pocket zone, ramped over 1 mm


CARVE_SOFT = 40.0       # mm added to T where the carve weight is 0 (larger than any baked-hair lump, max ~22 mm)
CARVE_K = 0.2           # smooth-max radius (mm) where the carved inner face meets the kept skin (no crease)
EXT_ARC = 1.0           # the back chain stops this far (mm of arc) past the loop's medial / lateral extreme (rim tip)


def _smax(a, b, k):
    return -V2._smin(-np.asarray(a, float), -np.asarray(b, float), k)


def T_shell(hh):
    return np.interp(hh, T_SHELL_HH, T_SHELL_MM)


def ear_frame(sd):
    B = np.load(os.path.join(LAYERS, f"ears_base_{sd}.npz"))
    O = PT.head_local(B["origin"][None])[0] * 1000; A = _unit(B["axis"] @ PT.HR)
    l = _unit(B["lateral"] @ PT.HR); w = _unit(B["front"] @ PT.HR); tip = PT.head_local(B["tip"][None])[0] * 1000
    u = _unit(l - (l @ A) * A); v = np.cross(A, u); v = v if v @ w > 0 else -v
    return {"O": O, "A": A, "u": u, "v": v, "w": w, "H": float((tip - O) @ A)}


# ------------------------------------------------------------------ section loops of a mesh (ordered polylines)
def section_loops(V, F, hv, hs):
    """closed loops of the mesh section {h = hs}: list of (n, 3) point arrays (ordered)"""
    s = hv - hs
    s = np.where(np.abs(s) < 1e-9, 1e-9, s)
    sf = s[F]; m = (sf.min(1) < 0) & (sf.max(1) > 0); T = F[m]
    if not len(T):
        return []
    edges = {}                                       # edge key -> list of (tri index, point)
    for ti, t in enumerate(T):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            i, j = int(t[a]), int(t[b])
            if (s[i] < 0) != (s[j] < 0):
                k = (min(i, j), max(i, j)); u = s[i] / (s[i] - s[j]); p = V[i] + u * (V[j] - V[i])
                edges.setdefault(k, []).append((ti, p))
    tri_edges = {}
    for k, lst in edges.items():
        for ti, _ in lst:
            tri_edges.setdefault(ti, []).append(k)
    pt = {k: lst[0][1] for k, lst in edges.items()}
    used = set(); loops = []
    for k0 in list(edges.keys()):
        if k0 in used:
            continue
        loop = [pt[k0]]; used.add(k0); k = k0; ti = edges[k0][0][0]
        for _ in range(200000):
            nxt = [e for e in tri_edges.get(ti, []) if e != k]
            if not nxt:
                break
            k = nxt[0]
            if k == k0:
                break
            if k in used:
                break
            used.add(k); loop.append(pt[k])
            tis = [t2 for t2, _ in edges[k] if t2 != ti]
            if not tis:
                break
            ti = tis[0]
        if len(loop) >= 8:
            loops.append(np.array(loop))
    return loops


def back_chain(loop, fr):
    """the convex back chain of one ear section loop (3D points, resampled at SEC_DS), rim tip to rim tip"""
    q = loop - fr["O"]; X = np.c_[q @ fr["u"], q @ fr["v"]]
    Xc = np.vstack([X, X[:1]]); seg = np.linalg.norm(np.diff(Xc, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
    L = s[-1]
    if L < 3.0:
        return None
    ns = int(L / SEC_DS); sq = np.linspace(0, L, ns, endpoint=False)
    Y = np.c_[np.interp(sq, s, Xc[:, 0]), np.interp(sq, s, Xc[:, 1])]
    P3 = np.stack([np.interp(sq, s, np.r_[loop[:, k], loop[0, k]]) for k in range(3)], -1)
    k = max(1, int(round(TAN_HALF / SEC_DS)))
    d = np.roll(Y, -k, 0) - np.roll(Y, k, 0)
    dth = (np.diff(np.r_[np.arctan2(d[:, 1], d[:, 0]), np.arctan2(d[0, 1], d[0, 0])]) + np.pi) % (2 * np.pi) - np.pi
    b = int(np.argmin(Y[:, 1]))                                   # most caudal point (the back of the cup)
    ext = {int(np.argmin(Y[:, 0])), int(np.argmax(Y[:, 0]))}      # the medial / lateral extremes (rim tips)
    nx = max(1, int(round(EXT_ARC / SEC_DS)))
    keep = np.zeros(ns, bool); keep[b] = True
    for step in (1, -1):                                          # forward, backward
        acc = 0.0; i = b; past = -1
        for _ in range(ns - 1):
            j = (i + step) % ns; acc += dth[i] if step == 1 else dth[j]; i = j
            if past < 0 and i in ext:
                past = 0
            if past >= 0:
                past += 1
            if abs(acc) >= TURN_MAX or keep[i] or past > nx:
                break
            keep[i] = True
    return P3[keep]


def build_shell(skin_path=SKIN_V2, out=SHELL_FILE):
    """BACK point sets per ear from skin v2 (cached); returns {sd: dict(B, frame)}"""
    Z = np.load(skin_path); V = PT.head_local(Z["v"].astype(float)) * 1000; F = Z["f"].astype(np.int64)
    rec = {}
    for sd in ("L", "R"):
        fr = ear_frame(sd); q = V - fr["O"]; h = q @ fr["A"]; rad = np.linalg.norm(q - np.outer(h, fr["A"]), axis=1)
        near = (h > (H_LO - 0.03) * fr["H"]) & (h < (H_HI + 0.03) * fr["H"]) & (rad < RAD_MAX + 4)
        fm = near[F].all(1); Fk = F[fm]; idx = np.unique(Fk); remap = -np.ones(len(V), np.int64); remap[idx] = np.arange(len(idx))
        Vk = V[idx]; Fk = remap[Fk]; hk = h[idx]
        pts, hsec, nloop = [], [], []
        for hs in np.arange(H_LO * fr["H"], H_HI * fr["H"], SEC_DH):
            loops = section_loops(Vk, Fk, hk, hs)
            cand = []
            for lp in loops:
                c = lp.mean(0) - fr["O"]; cr = np.linalg.norm(c - (c @ fr["A"]) * fr["A"])
                if cr < RAD_MAX:
                    cand.append((len(lp), lp))
            nloop.append(len(cand))
            if not cand:
                continue
            lp = max(cand, key=lambda x: x[0])[1]
            ch = back_chain(lp, fr)
            if ch is not None and len(ch):
                pts.append(ch); hsec.append(np.full(len(ch), hs))
        B = np.vstack(pts); rec[sd] = dict(B=B, hs=np.concatenate(hsec), n_sections=len(nloop), loops_per_section_max=int(max(nloop)))
    np.savez_compressed(out, **{f"B_{sd}": rec[sd]["B"].astype(np.float32) for sd in rec},
                        **{f"hs_{sd}": rec[sd]["hs"].astype(np.float32) for sd in rec},
                        note="feat_ears_v3 BACK chains (head mm) of skin v2 (layers/skin.npz) ear sections every 0.25 mm, "
                             "rim tip to rim tip (tangent turned 180 deg each way from the most caudal point)")
    return rec


_SH = {}


def shell():
    if not _SH:
        from scipy.spatial import cKDTree
        if not os.path.exists(SHELL_FILE):
            build_shell()
        Z = np.load(SHELL_FILE)
        for sd in ("L", "R"):
            B = Z[f"B_{sd}"].astype(float); fr = ear_frame(sd)
            _SH[sd] = dict(B=B, tree=cKDTree(B), fr=fr)
    return _SH


def _region():
    out = {}
    S = shell()
    for sd, e in V2.EARS.items():
        B = S[sd]["B"]; lo = np.minimum(e.lo, B.min(0) - 3.0); hi = np.maximum(e.hi, B.max(0) + 3.0)
        out[sd] = (lo, hi)
    return out


REGION = _region()


# ------------------------------------------------------------------ the edit
def shell_carve(P, F, stats=None):
    """D3: F <- F + w (max(F, dist(P, BACK) - T(h)) - F); P head mm (inside REGION), F mm"""
    P = np.asarray(P, float); out = np.array(F, float, copy=True)
    for sd, S in shell().items():
        lo, hi = REGION[sd]; b = np.all((P >= lo) & (P <= hi), axis=1)
        if not b.any():
            continue
        fr = S["fr"]; ib = np.flatnonzero(b); q = P[ib] - fr["O"]; h = q @ fr["A"]; hh = h / fr["H"]
        rad = np.linalg.norm(q - np.outer(h, fr["A"]), axis=1)
        sel = (hh > CARVE_H[0]) & (hh < CARVE_H[3]) & (rad < CARVE_RAD) & (out[ib] < 0.5)
        if not sel.any():
            continue
        ii = ib[sel]; hs = hh[sel]
        t, _ = S["tree"].query(P[ii])
        wgt = _ss((hs - CARVE_H[0]) / (CARVE_H[1] - CARVE_H[0])) * _ss((CARVE_H[3] - hs) / (CARVE_H[3] - CARVE_H[2]))
        e = V2.EARS[sd]; inz = np.all((P[ii] >= e.lo) & (P[ii] <= e.hi), axis=1)
        if inz.any():
            _, _, zone = e.fields(P[ii][inz]); wz = np.ones(len(ii)); wz[inz] = _ss((zone - POCKET_CLEAR) / 1.0); wgt = wgt * wz
        # the weight moves the carve SURFACE (T_eff = T + (1 - w) CARVE_SOFT), never blends field values: a value blend
        # cut the lump's middle before its surface (run 1: enclosed voids = 26 floating pieces at the 0.22-0.30 H ramp)
        T_eff = T_shell(hs) + (1.0 - wgt) * CARVE_SOFT
        g = t - T_eff; f0 = out[ii]; fn = _smax(f0, g, CARVE_K); out[ii] = fn
        if stats is not None:
            stats[f"carve_{sd}_raised"] = stats.get(f"carve_{sd}_raised", 0) + int(((fn - f0) > 0.01).sum())
    return out


def floor_sdf(e, P):
    """the slot FLOOR as tissue: the skin U-turn round the floor disk (radius gD / 2 at af = D - gD / 2), thickness
    T_ROOT, lower half only (a >= af), at the slot's heights. v2 built the floor disk as AIR only; below it the zone
    replacement (base inset by D_CAP - D_BASE = 3.1 mm) left air, so the slot ran 1.5-2.6 mm deeper than Tripo's
    measured floor (v2 builder preview 13.7 / 13.3 vs 12.2 / 11.84; v3 run 1 13.85 vs 12.2)"""
    hq, a, b, D = e.local(P)
    _, gD, cD = e.walls(hq, D, D); af = D - gD / 2; t = e.thick(D, D)
    ann = np.abs(np.hypot(a - af, b - cD) - (gD / 2 + t / 2)) - t / 2
    ann = np.maximum(ann, af - a)
    return np.maximum(ann, np.maximum((e.h_lo - 0.25) - hq, hq - (e.h_hi + 0.25)))


def edit(P_head_mm, F_mm, D_mm=None, stats=None):
    """v3 ear edit: v2 pocket (flap + hard-carved slot) + the floor U-turn, then the inner-shell carve; the slot stays air"""
    P = np.asarray(P_head_mm, float)
    F1 = V2.edit(P, F_mm, D_mm)
    for sd, e in V2.EARS.items():
        b = np.all((P >= e.lo) & (P <= e.hi), axis=1)
        if b.any():
            slot, _, _ = e.fields(P[b])
            F1[b] = np.maximum(np.minimum(F1[b], floor_sdf(e, P[b])), -slot)
    return shell_carve(P, F1, stats)          # the carve only raises F, so the hard-carved slot stays air


def opening_sdf(P_head_mm):
    """the pocket slot's intended air (mm, < 0 inside the air; +inf outside the v2 pocket boxes)"""
    P = np.asarray(P_head_mm, float); out = np.full(len(P), np.inf)
    for sd, e in V2.EARS.items():
        b = np.all((P >= e.lo) & (P <= e.hi), axis=1)
        if b.any():
            out[b] = np.minimum(out[b], e.fields(P[b])[0])
    return out


coat_cap_mm = V2.coat_cap_mm
skin_cap_apply = V2.skin_cap_apply
EARS = V2.EARS


# ------------------------------------------------------------------ probes (mesh vertices head mm, faces)
def _vnormals(P, f):
    fn = np.cross(P[f[:, 1]] - P[f[:, 0]], P[f[:, 2]] - P[f[:, 0]]); N = np.zeros_like(P)
    for k in range(3):
        np.add.at(N, f[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def shell_probe(Lmm, f, inp, sd):
    """D3 (cat_decisions.ear_bulge_one, the decision check itself, unchanged) on this mesh, one ear"""
    sys.path.insert(0, os.path.normpath(os.path.join(TR, "..", "engine", "checks")))
    import cat_decisions as CD
    E = CD.ear_frames()[sd]
    border = (inp or {}).get("border")
    P = np.asarray(Lmm, float); ff = np.asarray(f, np.int64)
    if border is not None:
        ff = ff[~np.asarray(border, bool)[ff].any(1)]
    N = _vnormals(P, ff)
    r = CD.ear_bulge_one(P, ff, N, E); bul = r.pop("_bulge", None); inn = r.pop("_inner", None)
    if bul is not None:
        q = P[inn] - E["O"]; h = q @ E["A"]
        r["bulge_over_0p5_by_hH"] = {f"{a:.1f}-{a + 0.1:.1f}": int(((bul > 0.5) & (h / E["H"] >= a) & (h / E["H"] < a + 0.1)).sum())
                                     for a in np.arange(0.3, 0.85, 0.1)}
    r["why"] = f"p99 bulge {r.get('bulge_p99_mm')} mm, area over 0.5 mm {r.get('area_bulge_over_0p5mm_mm2')} mm^2 (D3 gate 0.5 / 1.0)"
    return r


def islands_probe(Lmm, f, inp, sd):
    """no islands: connected pieces of the ear crop that do not touch the crop border (a crop cut makes border pieces;
    anything else is a floating piece). PASS = 0 such pieces."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    P = np.asarray(Lmm, float); ff = np.asarray(f, np.int64); lo, hi = REGION[sd]
    inb = np.all((P >= lo - 0.5) & (P <= hi + 0.5), axis=1); ff = ff[inb[ff].all(1)]
    n = len(P); e = np.r_[ff[:, 0], ff[:, 1], ff[:, 2]], np.r_[ff[:, 1], ff[:, 2], ff[:, 0]]
    G = coo_matrix((np.ones(len(e[0])), e), shape=(n, n)); nc, lab = connected_components(G, directed=False)
    used = np.unique(ff); border = (inp or {}).get("border")
    bflag = np.asarray(border, bool) if border is not None else np.any((P < lo + 0.6) | (P > hi - 0.6), axis=1)
    pieces = []
    for c in np.unique(lab[used]):
        vv = used[lab[used] == c]
        if not bflag[vv].any():
            fp = ff[np.isin(ff[:, 0], vv)]; nt = len(fp)
            vol = float(np.einsum("ij,ij->i", P[fp[:, 0]], np.cross(P[fp[:, 1]], P[fp[:, 2]])).sum() / 6.0)
            cen = P[vv].mean(0); op = float(opening_sdf(cen[None])[0])
            pieces.append({"tris": nt, "volume_mm3": round(vol, 4), "kind": "tissue" if vol > 0 else "void",
                           "in_opening": bool(op < 0.5), "centre_head_mm": np.round(cen, 2).tolist()})
    # run-2 revision (stated): an enclosed VOID (inside-out piece, volume < 0) is air sealed inside tissue; the integrator's
    # fill_voids_v3 fills it unless it touches an intended opening. A floating TISSUE piece (volume > 0, the C2 defect: v2's
    # two 16-tri pieces at the L ear) or a void in the opening (a sealed slot) FAILS.
    bad = [p for p in pieces if p["kind"] == "tissue" or p["in_opening"]]
    ok = len(bad) == 0
    return {"status": "PASS" if ok else "FAIL", "islands": len(bad), "tissue_islands": sum(p["kind"] == "tissue" for p in pieces),
            "voids_sealed_in_opening": sum(p["in_opening"] for p in pieces), "voids_for_fill_voids": sum(p["kind"] == "void" and not p["in_opening"] for p in pieces),
            "pieces": sorted(pieces, key=lambda p: (p["kind"] != "tissue", -p["tris"]))[:20],
            "why": "no floating tissue and no sealed opening in the ear REGION" if ok else f"{len(bad)} floating tissue piece(s) / sealed opening(s)"}


def pocket_probe_v3(Lmm, f, inp, sd):
    """C6b on v3: v2's pocket_probe (two layers, open, depth, free edge: unchanged) with two readings fixed.
    (1) FLAP THICKNESS at a = 0.5..3 is read on the FLAP itself: the tissue interval of the across line whose centre is
        nearest the flap's predicted mid-sheet b_f = b_in(a) + t(a) / 2 (within 1.0 mm), so it no longer needs the
        medial wall in the same line (near the mouth Tripo's antitragic wall recedes into the bay and v2's reading
        returned None = FAIL for a correct 0.6 mm flap). Window [0.4, 1.1] unchanged. Tripo's own lip there is 1.0-3.8 mm
        (out of the window) and a missing flap reads None: both still FAIL.
    (2) THINNER THAN TRIPO'S LIP at D/2 by >= min(2.0, 0.5 lip): v2's fixed 2.0 mm cannot be met where D/2 < ~2.5 mm
        (L rows h -5.5..-4.25: Tripo's lip there is 2.1-2.6 mm, so a 0.6 mm flap is 'only' 1.5-2.0 mm thinner). Tripo's
        wedge (flap = lip) still FAILS."""
    r = V2.pocket_probe(Lmm, f, inp, sd)
    e = V2.EARS[sd]; c = np.vstack([e.E, e.Fl]).mean(0)
    keep = np.linalg.norm(np.asarray(Lmm)[f].mean(1) - c, axis=1) < 32.0; tri = np.asarray(Lmm)[f[keep]]
    th_ok, d2_ok, tv = [], [], []
    for row in r["rows"]:
        hq = row["h"]; i = int(np.argmin(np.abs(e.h - hq))); D = float(e.D[i]); E, m, n, _ = V2._row(e, hq); th = {}
        for a in (0.5, 1.0, 2.0, 3.0, 0.5 * D):
            if a >= D - 0.5 and a != 0.5 * D:
                continue
            O = E - a * m + 40.0 * n; iv, _ = V2._intervals(O, -n, tri, 80.0)
            tis = [(40.0 - t1, 40.0 - t0) for t0, t1 in iv]
            bi, _, _ = e.walls(np.array([hq]), np.array([a]), np.array([D])); bf = float(bi[0]) + float(e.thick(a, D)) / 2
            best = min(tis, key=lambda x: abs(0.5 * (x[0] + x[1]) - bf), default=None)
            val = None if best is None or abs(0.5 * (best[0] + best[1]) - bf) > 1.0 else round(best[1] - best[0], 3)
            th[f"{a:g}" if a != 0.5 * D else "D2"] = val
        row["flap_thick_v3"] = th
        for k, v in th.items():
            if k != "D2":
                th_ok.append(bool(v is not None and 0.4 <= v <= 1.1)); tv += [v] if v is not None else []
        lipfit = np.polyfit([0.5, 1, 2, 3], e.lip[i], 1); lip_half = float(np.polyval(lipfit, 0.5 * D))
        need = min(2.0, 0.5 * lip_half); v = th.get("D2")
        d2_ok.append(bool(v is not None and v <= lip_half - need))
    frac = lambda xs: float(np.mean(xs)) if len(xs) else 0.0   # noqa: E731
    crit = dict(r["criteria"]); crit["flap_thickness_0.5_to_3"] = frac(th_ok) >= 0.9; crit["flap_thinner_than_tripo_lip_at_D2"] = frac(d2_ok) >= 0.9
    r["criteria_v2"] = r["criteria"]; r["criteria"] = crit
    r["frac"]["flap_thickness_v3"] = round(frac(th_ok), 3); r["frac"]["thinner_D2_v3"] = round(frac(d2_ok), 3)
    r["flap_thick_v3_p10_p50_p90"] = [round(float(np.percentile(tv, q)), 3) for q in (10, 50, 90)] if tv else None
    ok = all(crit.values()); r["status"] = "PASS" if ok else "FAIL"
    r["why"] = "pocket = two skin layers + open slot (v3 readings)" if ok else "FAIL: " + ", ".join(k for k, v in crit.items() if not v)
    return r


PROBES = {}
for _sd in "LR":
    PROBES[f"henrys_pocket.{_sd}"] = (lambda s: (lambda Lmm, f, inp: pocket_probe_v3(Lmm, f, inp, s)))(_sd)
    PROBES[f"ear_tip.{_sd}"] = (lambda s: (lambda Lmm, f, inp: V2.tip_probe(Lmm, f, inp, s)))(_sd)
    PROBES[f"ear_shell.{_sd}"] = (lambda s: (lambda Lmm, f, inp: shell_probe(Lmm, f, inp, s)))(_sd)
    PROBES[f"ear_islands.{_sd}"] = (lambda s: (lambda Lmm, f, inp: islands_probe(Lmm, f, inp, s)))(_sd)
