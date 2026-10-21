"""C13 WHISKER CHECK: tactile hairs are real, rooted, tapered hair - not clay (PHASE2_ROUND0 C13, fur_plan.md section 5,
check_hair.json B1/B2/S1/S2/S5/S11). Each clause runs per strand against a SKIN (exact point-to-triangle distance,
tripo_rebuild/twosided.MeshDist, proven).

Strand format (tripo_rebuild/layers/hair_whiskers.md): offsets, pts_head_mm, radius_mm, group, side, row, arc,
entry_head_mm, normal_head, root_head_mm, bulb_head_mm, follicle_radius_mm, meta (types + length table).

Clauses (each strand; counts per group):
 a  representation: polylines with a radius per point (>= 8 points); a mesh (v, f) FAILS (clay)
 b1 root 0.5-1.0 mm under the skin (brief)
 b2 root INSIDE its follicle: follicle recorded; entry on the skin (|d| <= 0.1 mm); bulb depth in the type's follicle range
    (S5 maximum included); root within the follicle radius of the entry->bulb axis, between its ends
 b3 the strand crosses the skin exactly once, within 0.5 mm of its entry (dense 0.1 mm sampling; a crossing = a sign
    change between two consecutive samples whose |d| sum <= 0.3 mm)
 b4 clearance (S5): the follicle stays INSIDE the skin over its whole length (samples every 0.2 mm), and the bulb's
    nearest skin is its OWN surface: that closest point lies above the bulb (direction within 60 deg of the entry
    normal) and within the follicle length + 1 mm of the entry. A follicle running toward another skin sheet (eye
    opening, lip, mouth groove) or out through the far side fails. (v1 of this clause, nearest distance >= 0.8 x
    depth, also failed sound follicles under the convex muzzle - curvature, not clearance - and was replaced.)
 c  base diameter (at the entry) in the type's cited range, um; and below the photo bound 500 um (S11 second bracket)
 d  radius never increases root -> tip; base:tip radius ratio 7-13 (Williams & Kramer 2010)
 e  emergent length vs evidence: mystacial cell table +- tolerance (meta length_table_mm / length_evidence); others in
    the type range
 f  counts: mystacial 12 per side, 4 rows x 3 arcs, row label agrees with the root's height (+-1.75 mm of the row),
    arc label agrees with caudal order, length increases front -> back in every row; supraorbital 2-6 / side;
    genal 1-3 / side; chin 2-5; carpal 4-6 / fore leg
 g  smooth: turn per segment < 10 deg; total turn in the type range; curvature profile flat at the base (S1: mean
    curvature of the first 20 % of the length < 1/3 of the last 20 %; Luo & Hartmann 2023)

python whisker_check.py --prove   runs the check on the build (must PASS), on Tripo's baked prisms (must FAIL) and on
planted defects (each must FAIL its clause); writes tripo_rebuild/layers/hair_whiskers_check.json
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
TR = os.path.join(PROJ, "tripo_rebuild")
sys.path.insert(0, TR)
import hair_whiskers as H  # noqa: E402

ROWS_Z = {"A": -14.0, "B": -17.5, "C": -21.0, "D": -24.5}       # palette whiskers_mystacial_layout.rows_z_mm
COUNTS = {"supraorbital": (2, 6), "genal": (1, 3), "chin": (2, 5), "carpal": (4, 6)}


def strands(D):
    o = np.asarray(D["offsets"])
    return [(np.asarray(D["pts_head_mm"])[o[i]:o[i + 1]], np.asarray(D["radius_mm"])[o[i]:o[i + 1]]) for i in range(len(o) - 1)]


def skin_for(D, skin_v, skin_f):
    boxes = []
    for P, _ in strands(D):
        boxes.append((P.min(0) - 6.0, P.max(0) + 6.0))
    return H.SkinCrop(skin_v, skin_f, boxes_head=boxes)


def turn_angles(P):
    t = np.diff(P, axis=0); n = np.linalg.norm(t, axis=1); t = t[n > 1e-9] / n[n > 1e-9, None]
    return np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", t[1:], t[:-1]), -1, 1))), n[n > 1e-9]


def check(D, sk, label=""):
    if "f" in getattr(D, "files", D.keys()) and "offsets" not in getattr(D, "files", D.keys()):
        return {"label": label, "pass": False, "clauses_failed": {"a": "input is a MESH (v, f): clay, not strands"}, "per_strand": []}
    meta = json.loads(str(D["meta"])) if "meta" in getattr(D, "files", D.keys()) else {}
    TT = meta.get("types", H.tactile_types(json.load(open(H.PAL))))
    LT = meta.get("length_table_mm"); TOL = meta.get("length_evidence", {}).get("tolerance_mm", {"arc1": 6, "arc2": 8, "arc3": 8})
    S = strands(D); g, side, row, arc = (np.asarray(D[k]).astype(str) for k in ("group", "side", "row", "arc"))
    E, N, R, B = (np.asarray(D[k], float) for k in ("entry_head_mm", "normal_head", "root_head_mm", "bulb_head_mm"))
    FR = np.asarray(D["follicle_radius_mm"], float)
    rows = []
    # one distance query for everything
    dense, owner = [], []
    for i, (P, _) in enumerate(S):
        seg = np.diff(P, axis=0); ln = np.linalg.norm(seg, axis=1)
        for a, (p, s, l) in enumerate(zip(P[:-1], seg, ln)):
            k = max(1, int(np.ceil(l / 0.1))); tt = (np.arange(k) / k)[:, None]
            dense.append(p + tt * s); owner.append(np.full(k, i))
        dense.append(P[-1:]); owner.append([i])
    dense = np.vstack(dense); owner = np.concatenate(owner)
    fin = lambda X: np.where(np.isfinite(X), X, 0.0)
    q = np.vstack([dense, fin(R), fin(E), fin(B)]); _, sd = sk.md()(q)
    sd_dense, sd_root, sd_entry, sd_bulb = np.split(sd, np.cumsum([len(dense), len(R), len(E)]))
    for i, (P, r) in enumerate(S):
        typ = TT.get(g[i], {}); res = {}
        res["a"] = bool(len(P) >= 8 and len(r) == len(P))
        dr = -sd_root[i]; res["b1"] = bool(0.5 <= dr <= 1.0)
        has_f = bool(np.all(np.isfinite(B[i])) and np.all(np.isfinite(E[i])) and FR[i] > 0)
        if has_f:
            ax = B[i] - E[i]; la = np.linalg.norm(ax); t = (R[i] - E[i]) @ ax / la ** 2
            off_axis = np.linalg.norm(R[i] - (E[i] + t * ax)); fd = -sd_bulb[i]
            fr = typ.get("follicle_depth_mm", {}).get("range", [0, 0])
            res["b2"] = bool(abs(sd_entry[i]) <= 0.1 and fr[0] <= fd <= fr[1] and 0 < t < 1 and off_axis <= FR[i])
            tt = np.linspace(0.0, 1.0, max(3, int(la / 0.2) + 1))[1:, None]; inside = sk.signed(E[i] + tt * ax) < 0
            _, cb = sk.closest_face(B[i]); vb = cb[0] - B[i]
            own = (vb @ N[i] >= 0.5 * np.linalg.norm(vb)) and np.linalg.norm(cb[0] - E[i]) <= la + 1.0
            res["b4"] = bool(np.all(inside) and own)
        else:
            res["b2"] = False; res["b4"] = False; fd = float("nan")
        m = owner == i; sdm = sd_dense[m]; s = np.sign(sdm); s[s == 0] = 1
        ch = np.where((np.diff(s) != 0) & (np.abs(sdm[1:]) + np.abs(sdm[:-1]) <= 0.3))[0]     # a TRUE crossing straddles the
        # surface between two 0.1 mm samples; sign flips far from the skin are open-crop artefacts (found in the reroot test)
        Pd = dense[m]; res["b3"] = bool(len(ch) == 1 and np.linalg.norm(Pd[ch[0]] - E[i]) <= 0.5) if has_f else bool(len(ch) == 1)
        # entry point index: the polyline point nearest the recorded entry
        ie = int(np.argmin(np.linalg.norm(P - E[i], axis=1))) if has_f else 0
        base_um = 2000.0 * r[ie]; br = typ.get("base_um_range", [0, 0])
        res["c"] = bool(br[0] <= base_um <= br[1] and base_um < 500.0)
        ratio = r[ie] / max(r[-1], 1e-12); res["d"] = bool(np.all(np.diff(r) <= 1e-9) and 7.0 <= ratio <= 13.0)
        Pe = P[ie:]; Lm = float(np.linalg.norm(np.diff(Pe, axis=0), axis=1).sum())
        if g[i] == "mystacial":
            ok = LT is not None and row[i] in LT and arc[i] in LT[row[i]]
            res["e"] = bool(ok and abs(Lm - LT[row[i]][arc[i]]) <= TOL.get("arc" + arc[i], 6))
        else:
            lr = typ.get("length_mm", [0, 0]); res["e"] = bool(lr[0] <= Lm <= lr[1])
        ang, sl = turn_angles(Pe); total = float(ang.sum()); tr = typ.get("turn_deg", {}).get("range", [0, 0])
        cum = np.cumsum(sl)[:-1] / sl.sum(); kap = np.radians(ang) / (0.5 * (sl[1:] + sl[:-1]))
        k0 = kap[cum <= 0.2].mean() if np.any(cum <= 0.2) else np.inf; k1 = kap[cum >= 0.8].mean() if np.any(cum >= 0.8) else 0
        res["g"] = bool(len(ang) and ang.max() < 10.0 and tr[0] <= total <= tr[1] and k0 < k1 / 3.0)
        rows.append({"i": i, "group": g[i], "side": side[i], "row": row[i], "arc": arc[i], "root_depth_mm": round(float(dr), 3),
                     "bulb_depth_mm": round(float(fd), 3), "crossings": int(len(ch)), "base_um": round(float(base_um), 1),
                     "taper_ratio": round(float(ratio), 2), "length_mm": round(Lm, 2), "max_seg_turn_deg": round(float(ang.max()) if len(ang) else 0, 2),
                     "total_turn_deg": round(total, 1), "k_base_over_k_tip": round(float(k0 / max(k1, 1e-12)), 3), "ok": res})
    # f: counts and structure
    fres = {}
    for sd_ in ("L", "R"):
        mm = [x for x in rows if x["group"] == "mystacial" and x["side"] == sd_]
        cells = {(x["row"], x["arc"]) for x in mm}
        geom = all(x["row"] in ROWS_Z and abs(E[x["i"], 2] - ROWS_Z[x["row"]]) <= 1.75 for x in mm)
        order = True
        for rw in ROWS_Z:
            cell = sorted([x for x in mm if x["row"] == rw], key=lambda x: x["arc"])
            ys = [E[x["i"], 1] for x in cell]; ls = [x["length_mm"] for x in cell]
            order &= len(cell) == 3 and all(ys[k] > ys[k + 1] for k in range(len(ys) - 1)) and all(ls[k] > ls[k + 1] for k in range(len(ls) - 1))
        fres["mystacial_" + sd_] = bool(len(mm) == 12 and len(cells) == 12 and geom and order)
    for grp, (lo, hi) in COUNTS.items():
        keys = sorted({x["side"] for x in rows if x["group"] == grp}) or ["L", "R"]
        if grp == "chin":
            n = sum(x["group"] == "chin" for x in rows); fres["chin"] = bool(lo <= n <= hi)
        else:
            for sd_ in ("L", "R"):
                n = sum(x["group"] == grp and x["side"] == sd_ for x in rows); fres[f"{grp}_{sd_}"] = bool(lo <= n <= hi)
    failed = {}
    for c in ("a", "b1", "b2", "b3", "b4", "c", "d", "e", "g"):
        bad = [x["i"] for x in rows if not x["ok"][c]]
        if bad:
            failed[c] = bad
    badf = [k for k, v in fres.items() if not v]
    if badf:
        failed["f"] = badf
    return {"label": label, "pass": not failed, "clauses_failed": failed, "counts": fres, "per_strand": rows}


# ---------------------------------------------------------------- planted defects and Tripo's prisms (A10)
def copy(D):
    return {k: np.array(D[k]) for k in D.files} if hasattr(D, "files") else {k: np.array(v) for k, v in D.items()}


def plant(D, kind, i=0):
    X = copy(D); o = X["offsets"]; s = slice(o[i], o[i + 1])
    if kind == "floating_1mm":                         # whole whisker lifted 1 mm off the skin along its normal
        d = X["normal_head"][i] * 1.0
        X["pts_head_mm"][s] += d; X["root_head_mm"][i] += d; X["entry_head_mm"][i] += d; X["bulb_head_mm"][i] += d
    elif kind == "untapered":                          # ratio 1
        X["radius_mm"][s] = X["radius_mm"][o[i]]
    elif kind == "base_0.6mm":
        X["radius_mm"][s] *= 0.3 / X["radius_mm"][o[i]]
    elif kind == "deep_follicle_6mm":                  # S5: follicle driven 6 mm deep
        X["bulb_head_mm"][i] = X["entry_head_mm"][i] - (X["entry_head_mm"][i] - X["bulb_head_mm"][i]) * 6.0 / X["follicle_depth_mm"][i]
    elif kind == "follicle_through":                   # S5: follicle driven 50 mm along -normal, out through the far side of the muzzle
        X["bulb_head_mm"][i] = X["entry_head_mm"][i] - X["normal_head"][i] * 50.0
    elif kind == "kink_30deg":                         # tip half rotated 30 deg about the mid point
        P = X["pts_head_mm"][s]; m = len(P) // 2; ax = H.unit(np.cross(P[m] - P[m - 1], [0, 0, 1.0]))
        from scipy.spatial.transform import Rotation as Rot
        P[m:] = P[m] + Rot.from_rotvec(np.radians(30) * ax).apply(P[m:] - P[m]); X["pts_head_mm"][s] = P
    elif kind == "root_bend_droop":                    # v37-style: curvature largest at the root (S1)
        P = X["pts_head_mm"][s]; E = P[1]; u = H.unit(P[2] - P[1]); L = np.linalg.norm(np.diff(P[1:], axis=0), axis=1).sum()
        w = H.unit(np.array([0, -1.0, -1.0]) - (np.array([0, -1.0, -1.0]) @ u) * u); th = np.radians(35)
        sf = np.linspace(0, L, 881); phi = th * (1 - (1 - sf / L) ** 2)                 # k(s) = A (L - s)
        tan = np.cos(phi)[:, None] * u + np.sin(phi)[:, None] * w
        c = E + np.vstack([np.zeros(3), np.cumsum(np.diff(sf)[:, None] * 0.5 * (tan[1:] + tan[:-1]), axis=0)])
        P[1:] = c[::40]; X["pts_head_mm"][s] = P
    elif kind == "drop_one_mystacial":                 # 11 on one side
        keep = np.ones(len(o) - 1, bool); keep[i] = False; return subset(X, keep)
    elif kind == "length_x1.3":
        P = X["pts_head_mm"][s]; P[1:] = P[1] + (P[1:] - P[1]) * 1.3; X["pts_head_mm"][s] = P
    return X


def subset(X, keep):
    o = X["offsets"]; idx = np.where(keep)[0]
    pt = np.concatenate([np.arange(o[i], o[i + 1]) for i in idx]); Y = dict(X)
    for k in ("pts_head_mm", "radius_mm", "local_pts", "points", "radius"):
        if k in Y:
            Y[k] = X[k][pt]
    Y["offsets"] = np.r_[0, np.cumsum(np.diff(o)[idx])]
    for k, v in X.items():
        if k not in ("pts_head_mm", "radius_mm", "local_pts", "points", "radius", "offsets", "meta") and np.ndim(v) >= 1 and len(v) == len(o) - 1:
            Y[k] = v[idx]
    return Y


def tripo_as_strands(meta_from):
    """Tripo's baked whisker prisms (layers/whiskers.json, Phase 1 measured) in strand format: centreline + radius =
    (width + thickness)/4 per point. No follicle exists in Tripo, so the follicle fields are NaN (= missing)."""
    W = json.load(open(os.path.join(TR, "layers", "whiskers.json")))["whiskers"]
    P, r, off = [], [], [0]
    for w in W:
        c = H.to_head(np.array(w["centreline_world"])); rr = (np.array(w["width_m"]) + np.array(w["thickness_m"])) * 250.0
        P.append(c); r.append(rr); off.append(off[-1] + len(c))
    n = len(W); nan3 = np.full((n, 3), np.nan)
    return {"pts_head_mm": np.vstack(P), "radius_mm": np.concatenate(r), "offsets": np.array(off),
            "group": np.array(["mystacial"] * n), "side": np.array([w["side"] for w in W]), "row": np.array(["?"] * n),
            "arc": np.array(["?"] * n), "entry_head_mm": nan3, "normal_head": nan3, "root_head_mm": np.array([p[0] for p in P]),
            "bulb_head_mm": nan3, "follicle_radius_mm": np.zeros(n), "meta": meta_from}


def prove(npz=os.path.join(TR, "layers", "hair_whiskers.npz"), out=os.path.join(TR, "layers", "hair_whiskers_check.json")):
    t0 = time.time(); D = np.load(npz); Sk = np.load(H.SKIN_V1); v, f = Sk["v"], Sk["f"]
    T = tripo_as_strands(D["meta"])
    boxes = []
    for X in (D, T):                                   # a box round every strand (+ its follicle) only: small crop
        for P, _ in strands(X):
            boxes.append((P.min(0) - 7.0, P.max(0) + 7.0))
    gi = np.asarray(D["group"]).astype(str); si = np.asarray(D["side"]).astype(str)
    sk = H.SkinCrop(v, f, boxes_head=boxes); del Sk, v, f
    rep = {"what": "C13 whisker_check proof (A10): the build must PASS; Tripo's baked prisms and every planted defect must FAIL "
                   "the clause it targets. Skin = skin v1 (person-approved leather top).", "runs": []}
    base = check(D, sk, "BUILD (hair_whiskers.npz on skin v1)"); rep["runs"].append(base)
    tri = check(T, sk, "TRIPO baked whisker prisms (whiskers.json centrelines + measured widths)"); rep["runs"].append(tri)
    rep["runs"].append(check(np.load(os.path.join(TR, "layers", "whiskers_tubes.npz")), sk, "TRIPO whiskers_tubes.npz mesh (clay)"))
    i_my = int(np.where((gi == "mystacial") & (si == "R") & (np.asarray(D["row"]).astype(str) == "C") & (np.asarray(D["arc"]).astype(str) == "1"))[0][0])
    plan = [("floating_1mm", i_my, {"b1", "b3"}), ("untapered", i_my, {"d"}), ("base_0.6mm", i_my, {"c"}),
            ("deep_follicle_6mm", i_my, {"b2"}), ("follicle_through", i_my, {"b4"}), ("kink_30deg", i_my, {"g"}), ("root_bend_droop", i_my, {"g"}),
            ("drop_one_mystacial", i_my, {"f"}), ("length_x1.3", i_my, {"e"}),
            ("floating_1mm", int(np.where(gi == "carpal")[0][0]), {"b1", "b3"}), ("untapered", int(np.where(gi == "chin")[0][0]), {"d"})]
    for kind, i, want in plan:
        r = check(plant(D, kind, i), sk, f"PLANT {kind} on strand {i} ({gi[i]})")
        hit = set(r["clauses_failed"]); r["targets"] = sorted(want); r["caught"] = bool(want <= hit)
        r["per_strand"] = [x for x in r["per_strand"] if not all(x["ok"].values())]; rep["runs"].append(r)
    tri_ok = (not tri["pass"]) and (not rep["runs"][2]["pass"])
    rep["verdict"] = {"build_passes": base["pass"], "tripo_fails": tri_ok, "tripo_clauses": sorted(tri["clauses_failed"]),
                      "plants_caught": all(r.get("caught", True) for r in rep["runs"][3:]),
                      "seconds": round(time.time() - t0, 1)}
    rep["verdict"]["proven"] = bool(base["pass"] and tri_ok and rep["verdict"]["plants_caught"])
    json.dump(rep, open(out, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return rep


if __name__ == "__main__":
    if "--prove" in sys.argv:
        rep = prove()
        for r in rep["runs"]:
            print(f"{'PASS' if r['pass'] else 'FAIL'}  {r['label'][:70]:70s} failed: {sorted(r['clauses_failed'])}"
                  + (f"  targets {r['targets']} caught={r['caught']}" if "targets" in r else ""))
        print(rep["verdict"])
