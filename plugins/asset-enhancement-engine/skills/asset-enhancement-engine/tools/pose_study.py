"""POSE STUDY (numpy side of pose_study_bl.py): where and why a skinned body creases, collapses, loses volume or passes
through itself as its arms rise, per anatomical zone, so meshes, weights, rigs and skinning can be told apart.
Created 2026-10-20 (woman2 build 12: v12, build 08 and Blender Studio's base body, on their own rigs and on Rigify).

usage: python pose_study.py OUT_DIR variant [variant ...] [--json result.json]
Reads OUT_DIR/rest_<variant>.npz and OUT_DIR/<variant>_<pose>.npz (pose_study_bl.py) and prints / writes per variant:
  structure (rest, once per mesh): zone edge lengths, irregular vertices, edge alignment with the humerus, rest folds
     and crossings, the arm's rest abduction, the inner arm's clearance to the side, the armpit apex depth;
  weights (rest): per zone the share held by arm / girdle / torso bones, the arm weight's gradient (1/mm) and the
     transition width (mm per unit weight), unweighted vertices and vertices held by a bone far from them;
  per pose, against the variant's own rest: crossing triangle pairs that were not crossing at rest, split into local
     (centroids < 15 mm apart at rest: the skin folding into itself) and distant (two separate surfaces meeting), by
     zone, as pair counts and as the rest area of the crossing triangles (compare bodies by area: counts follow mesh
     density); sheets (triangles grown > 4x in area); new creases (edges whose dihedral rose > 30 deg; > 90 deg; folded
     > 150 deg), as counts and as rest edge length; clusters of crossings and sheets with their place relative to the
     shoulder joint; thickness collapse (inward
     ray thickness < 0.5 of rest); edge strain (stretch > 1.5x, squash < 0.67x); the shoulder complex's cone volume
     about the posed shoulder joint; the nipple's and the breast's shift; the trapezius and neck motion; the front
     contour from neck to shoulder (chord angle and sag: a straight ramp = sag 0 = a triangular neck).
Zones (rest, per side, from the deform bones' joints and the rest normals; one rule for every mesh):
  upper_arm: along the humerus 0.30-0.85 of its length, within 55 mm of its axis, the skin facing away from the axis;
  shoulder:  within 75 mm of the shoulder (glenohumeral) joint, not below it by more than 20 mm, facing away from it;
  axilla:    within 110 mm of the joint, more than 30 mm below it, not lateral of it by more than 30 mm;
  breast:    within 75 mm of the nipple (the most anterior chest point per side), front half;
  trapezius: from 10 mm below to 70 mm above the SC joint, 40 mm from the midline to 20 mm medial of the shoulder top;
  neck:      within 50 mm of the midline, 20-70 mm above the SC joints;
  side:      110-220 mm from the joint, more than 80 mm below it, within 80 mm medial / 10 mm lateral of it.
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

ZONES = ["breast", "axilla", "shoulder", "upper_arm", "trapezius", "neck", "side"]
SIDES = ("L", "R")


def load(out, name):
    R = dict(np.load(os.path.join(out, f"rest_{name}.npz"), allow_pickle=False))
    tags = [p[len(name) + 1:-4] for p in os.listdir(out) if p.startswith(name + "_") and p.endswith(".npz")]
    num = sorted(int(t) for t in tags if t.isdigit())
    named = sorted(t for t in tags if not t.isdigit() and "_" in t and t[0] == "T")      # build 13b: named test poses (T0_rest ...)
    poses = num + named
    P = {T: dict(np.load(os.path.join(out, f"{name}_{T}.npz"), allow_pickle=False)) for T in poses}
    return R, P


def bone_index(R):
    return {str(b): i for i, b in enumerate(R["bones"])}


def joints(R, heads=None, tails=None):
    """SC, GH, elbow per side, from the deform bones (ours: clavicle / upper_arm / forearm; Rigify: DEF-shoulder /
    DEF-upper_arm / DEF-forearm)"""
    bi = bone_index(R); H = R["heads"] if heads is None else heads; T = R["tails"] if tails is None else tails
    rig = "DEF-upper_arm.L" in bi
    J = {}
    for s in SIDES:
        if rig:
            J[s] = dict(sc=H[bi["DEF-shoulder." + s]], gh=H[bi["DEF-upper_arm." + s]], el=H[bi["DEF-forearm." + s]])
        else:
            J[s] = dict(sc=H[bi["clavicle." + s]], gh=H[bi["upper_arm." + s]], el=H[bi["forearm." + s]])
    return J, rig


def bone_groups(groups, rig):
    g = [str(x) for x in groups]
    out = {}
    for s in SIDES:
        if rig:
            arm = [i for i, n in enumerate(g) if n.startswith(("DEF-upper_arm." + s, "DEF-forearm." + s, "DEF-hand." + s))]
            gir = [i for i, n in enumerate(g) if n == "DEF-shoulder." + s]
        else:
            arm = [i for i, n in enumerate(g) if n in ("upper_arm." + s, "forearm." + s)]
            gir = [i for i, n in enumerate(g) if n in ("clavicle." + s, "scapula." + s)]
        out[s] = dict(arm=arm, girdle=gir)
    return out


def frame(R):
    J, rig = joints(R)
    v = R["v"].astype(float); n = R["n"].astype(float)
    mid = (J["L"]["sc"][0] + J["R"]["sc"][0]) / 2
    F = {"mid": float(mid), "rig": rig, "J": J}
    for s, sg in (("L", 1), ("R", -1)):
        gh = J[s]["gh"].astype(float); el = J[s]["el"].astype(float)
        xs = sg * (v[:, 0] - mid); ghx = sg * (gh[0] - mid)
        col = (np.abs(v[:, 0] - gh[0]) < 0.010) & (np.abs(v[:, 1] - gh[1]) < 0.015) & (v[:, 2] > gh[2])
        top = int(np.where(col)[0][np.argmax(v[col, 2])])
        band = (v[:, 2] < gh[2] - 0.06) & (v[:, 2] > gh[2] - 0.22) & (xs > 0.03) & (xs < ghx - 0.01)
        nip = int(np.where(band)[0][np.argmin(v[band, 1])])
        F[s] = dict(gh=gh, el=el, sc=J[s]["sc"].astype(float), top=top, nipple=nip, ghx=float(ghx),
                    topx=float(sg * (v[top, 0] - mid)), arm_len=float(np.linalg.norm(el - gh)),
                    rest_abd=float(np.degrees(np.arctan2(abs(el[0] - gh[0]), gh[2] - el[2]))))
    return F


def zones(R, F):
    v = R["v"].astype(float); n = R["n"].astype(float); N = len(v)
    lab = np.full(N, "other", object); side = np.full(N, "", object)
    for s, sg in (("L", 1), ("R", -1)):
        S = F[s]; gh, el, sc = S["gh"], S["el"], S["sc"]
        xs = sg * (v[:, 0] - F["mid"]); u = (el - gh) / np.linalg.norm(el - gh)
        d = v - gh; t = d @ u; rad = d - t[:, None] * u; r = np.linalg.norm(rad, axis=1)
        dist = np.linalg.norm(d, axis=1)
        mine = (xs > 0)
        m = {}
        m["upper_arm"] = mine & (t > 0.30 * S["arm_len"]) & (t < 0.85 * S["arm_len"]) & (r < 0.055) & ((rad * n).sum(1) > 0)
        m["shoulder"] = mine & (dist < 0.075) & (v[:, 2] > gh[2] - 0.020) & ((d * n).sum(1) > 0)
        m["axilla"] = mine & (dist < 0.110) & (v[:, 2] < gh[2] - 0.030) & (xs < S["ghx"] + 0.030) & ~m["upper_arm"]
        nip = v[S["nipple"]]
        m["breast"] = mine & (np.linalg.norm(v - nip, axis=1) < 0.075) & (v[:, 1] < nip[1] + 0.06)
        m["trapezius"] = mine & (v[:, 2] > sc[2] - 0.010) & (v[:, 2] < sc[2] + 0.070) & (xs > 0.040) & (xs < S["topx"] - 0.020)
        m["neck"] = mine & (xs < 0.050) & (v[:, 2] > sc[2] + 0.020) & (v[:, 2] < sc[2] + 0.070)
        m["side"] = mine & (dist > 0.110) & (dist < 0.220) & (v[:, 2] < gh[2] - 0.080) & (xs > S["ghx"] - 0.080) & (xs < S["ghx"] + 0.010)
        for z in reversed(ZONES):               # priority: the first zone in ZONES wins (written last)
            lab[m[z]] = z; side[m[z]] = s
    return lab, side


def tri_normals(v, f):
    c = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    a = np.linalg.norm(c, axis=1)
    return c / np.maximum(a[:, None], 1e-30), a / 2


def edge_faces(f, nv):
    E = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), 1); fid = np.tile(np.arange(len(f)), 3)
    k = E[:, 0].astype(np.int64) * (nv + 1) + E[:, 1]; o = np.argsort(k, kind="stable"); ks = k[o]
    same = np.where(ks[1:] == ks[:-1])[0]
    return E[o][same], fid[o][same], fid[o][same + 1]


def dihedral(v, f, a, b):
    fu, _ = tri_normals(v, f)
    return np.degrees(np.arccos(np.clip((fu[a] * fu[b]).sum(1), -1, 1)))


def grad_mag(v, f, w):
    e1 = v[f[:, 1]] - v[f[:, 0]]; e2 = v[f[:, 2]] - v[f[:, 0]]
    dw = np.stack([w[f[:, 1]] - w[f[:, 0]], w[f[:, 2]] - w[f[:, 0]]], 1)
    G = np.stack([e1, e2], 1)                                   # t x 2 x 3
    GG = G @ G.transpose(0, 2, 1); det = GG[:, 0, 0] * GG[:, 1, 1] - GG[:, 0, 1] ** 2
    inv = np.stack([np.stack([GG[:, 1, 1], -GG[:, 0, 1]], 1), np.stack([-GG[:, 1, 0], GG[:, 0, 0]], 1)], 1) / np.maximum(det, 1e-30)[:, None, None]
    g = (G.transpose(0, 2, 1) @ (inv @ dw[:, :, None]))[:, :, 0]
    return np.linalg.norm(g, axis=1) / 1000.0                  # per mm


def contour(vp, sel, mid, sg, x0, x1, nb=20):
    """front-view upper contour z(x) of the selected posed vertices between x0 and x1 (mm from the midline)"""
    xs = sg * (vp[sel, 0] - mid) * 1000; z = vp[sel, 2] * 1000
    edges = np.linspace(x0, x1, nb + 1); pts = []
    for i in range(nb):
        m = (xs >= edges[i]) & (xs < edges[i + 1])
        if m.sum() >= 3:
            pts.append(((edges[i] + edges[i + 1]) / 2, z[m].max()))
    if len(pts) < 4:
        return None
    p = np.array(pts); a, b = p[0], p[-1]; ch = b - a; L = np.linalg.norm(ch)
    sag = ((p[:, 0] - a[0]) * ch[1] - (p[:, 1] - a[1]) * ch[0]) / L       # + = contour below the chord (concave neck)
    return {"chord_deg": round(float(np.degrees(np.arctan2(ch[1], ch[0]))), 1), "sag_max_mm": round(float(sag.max()), 1),
            "rise_mm": round(float(ch[1]), 1)}


def structure(R, F, lab, side, e, ea, eb):
    v = R["v"].astype(float); f = R["f"].astype(np.int64)
    out = {"verts": int(len(v)), "tris": int(len(f))}
    el = np.linalg.norm(v[e[:, 0]] - v[e[:, 1]], axis=1) * 1000
    val = np.bincount(e.ravel(), minlength=len(v))
    ang0 = dihedral(v, f, ea, eb)
    rp = R["pairs"]; tz = lab[f[:, 0]]
    for s in SIDES:
        S = F[s]; u = (S["el"] - S["gh"]) / np.linalg.norm(S["el"] - S["gh"])
        o = {"rest_abduction_deg": round(S["rest_abd"], 2), "humerus_mm": round(S["arm_len"] * 1000, 1)}
        for z in ZONES:
            em = (lab[e[:, 0]] == z) & (side[e[:, 0]] == s)
            vm = (lab == z) & (side == s)
            if not em.any():
                continue
            d = v[e[em, 1]] - v[e[em, 0]]; d /= np.linalg.norm(d, axis=1, keepdims=True)
            al = np.degrees(np.arccos(np.clip(np.abs(d @ u), 0, 1)))
            o[z] = {"verts": int(vm.sum()), "edge_mm_p5_p50_p95": [round(float(x), 2) for x in np.percentile(el[em], [5, 50, 95])],
                    "valence_mode": int(np.bincount(val[vm]).argmax()), "irregular_share": round(float((val[vm] != np.bincount(val[vm]).argmax()).mean()), 3),
                    "edges_within20_of_axis_or_ring": round(float(((al < 20) | (al > 70)).mean()), 3),
                    "rest_dihedral_p99": round(float(np.percentile(ang0[em], 99)), 1),
                    "rest_folds_150": int((ang0[em] > 150).sum())}
        # inner arm's clearance to the side (outward rays at rest) and the armpit apex depth below the joint
        am = (lab == "upper_arm") & (side == s); c = R["clear"][am] * 1000
        sg = 1 if s == "L" else -1; xs = sg * (v[:, 0] - F["mid"])
        medial = am & (((v - S["gh"]) * sg)[:, 0] < 0)
        cm = R["clear"][medial] * 1000
        o["inner_arm_clearance_mm"] = {"p5": round(float(np.nanpercentile(cm, 5)), 1), "p50": round(float(np.nanpercentile(cm, 50)), 1),
                                       "share_under_2mm": round(float(np.nanmean(cm < 2.0)), 3)} if np.isfinite(cm).any() else None
        ap = (np.abs(v[:, 1] - S["gh"][1]) < 0.004) & (xs > S["ghx"] - 0.05) & (xs < S["ghx"] + 0.01) & (v[:, 2] < S["gh"][2] - 0.01) & (R["n"][:, 2] < -0.5)
        o["armpit_apex_below_joint_mm"] = round(float((S["gh"][2] - v[ap, 2].max()) * 1000), 1) if ap.any() else None
        out[s] = o
    out["rest_crossing_pairs"] = int(len(rp))
    return out


def weights(R, F, lab, side, rig):
    v = R["v"].astype(float); f = R["f"].astype(np.int64); W = R["W"].astype(float)
    bg = bone_groups(R["groups"], rig); tot = W.sum(1)
    out = {"unweighted": int((tot <= 1e-6).sum())}
    if out["unweighted"]:
        uw = np.where(tot <= 1e-6)[0]
        out["unweighted_where"] = {z: int((lab[uw] == z).sum()) for z in ZONES + ["other"] if (lab[uw] == z).any()}
    # vertices held mostly by a bone far from them
    bi = bone_index(R); H, T = R["heads"].astype(float), R["tails"].astype(float)
    gi = [bi.get(str(g)) for g in R["groups"]]
    top = W.argmax(1); far = np.zeros(len(v), bool)
    for j, b in enumerate(gi):
        m = (top == j) & (tot > 1e-6)
        if b is None or not m.any():
            continue
        a, c = H[b], T[b]; ab = c - a; t = np.clip(((v[m] - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
        dd = np.linalg.norm(v[m] - (a + t[:, None] * ab), axis=1); far[np.where(m)[0][dd > 0.25]] = True
    out["held_by_bone_over_250mm_away"] = int(far.sum())
    for s in SIDES:
        Wn = W / np.maximum(tot, 1e-12)[:, None]
        arm = Wn[:, bg[s]["arm"]].sum(1); gir = Wn[:, bg[s]["girdle"]].sum(1)
        g = grad_mag(v, f, arm); tz = lab[f[:, 0]]; ts = side[f[:, 0]]
        wt = arm[f].mean(1)
        o = {}
        for z in ZONES:
            vm = (lab == z) & (side == s)
            if not vm.any():
                continue
            tm = (tz == z) & (ts == s); tr = tm & (wt > 0.1) & (wt < 0.9)
            o[z] = {"arm": round(float(arm[vm].mean()), 3), "girdle": round(float(gir[vm].mean()), 3),
                    "torso": round(float(1 - arm[vm].mean() - gir[vm].mean()), 3),
                    "arm_grad_per_mm_p99_max": [round(float(np.percentile(g[tm], 99)), 4), round(float(g[tm].max()), 4)] if tm.any() else None,
                    "transition_mm_p10_p50": [round(float(np.percentile(1 / np.maximum(g[tr], 1e-9), 10)), 1),
                                              round(float(np.percentile(1 / np.maximum(g[tr], 1e-9), 50)), 1)] if tr.sum() > 10 else None}
        out[s] = o
    return out


def clusters(v0, f, F, lab, tris, ar0, ar1, kind, top=4, min_cm2=0.5):
    """connected groups (shared vertices) of the given triangles: rest / posed area, zones, rest place relative to the
    nearer shoulder joint (mm: lateral, forward, up)"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    if not len(tris):
        return []
    ii = np.repeat(np.arange(len(tris)), 3); jj = f[tris].ravel()
    A = coo_matrix((np.ones(len(ii)), (ii, jj)), shape=(len(tris), len(v0))).tocsr()
    nc, lb = connected_components(A @ A.T, directed=False)
    out = []
    for c in range(nc):
        t = tris[lb == c]
        if ar0[t].sum() * 1e4 < min_cm2 and ar1[t].sum() * 1e4 < 4 * min_cm2:
            continue
        vv = np.unique(f[t]); cen = v0[vv].mean(0); s = "L" if cen[0] > F["mid"] else "R"; sg = 1 if s == "L" else -1
        zs, zn = np.unique(lab[vv], return_counts=True)
        out.append({"kind": kind, "side": s, "rest_cm2": round(float(ar0[t].sum() * 1e4), 2), "posed_cm2": round(float(ar1[t].sum() * 1e4), 1),
                    "zones": {str(a): int(b) for a, b in zip(zs, zn)},
                    "rest_mm_from_joint": [round(float(x), 0) for x in (cen - F[s]["gh"]) * 1000 * np.array([sg, -1, 1])]})
    out.sort(key=lambda d: -(d["rest_cm2"] + d["posed_cm2"] / 10))
    return out[:top]


def pose_metrics(R, P, F, lab, side, e, ea, eb, rig):
    v0 = R["v"].astype(float); f = R["f"].astype(np.int64); nt = len(f)
    ang0 = dihedral(v0, f, ea, eb)
    l0 = np.linalg.norm(v0[e[:, 0]] - v0[e[:, 1]], axis=1)
    cen0 = v0[f].mean(1)
    rk = set((np.minimum(R["pairs"][:, 0], R["pairs"][:, 1]).astype(np.int64) * nt + np.maximum(R["pairs"][:, 0], R["pairs"][:, 1])).tolist())
    tz = lab[f[:, 0]]; ts = side[f[:, 0]]
    ez = lab[e[:, 0]]; es = side[e[:, 0]]
    _, ar0 = tri_normals(v0, f)
    out = {}
    for T, Q in P.items():
        v = Q["v"].astype(float)
        J, _ = joints(R, Q["heads"].astype(float), Q["tails"].astype(float))
        pk = np.minimum(Q["pairs"][:, 0], Q["pairs"][:, 1]).astype(np.int64) * nt + np.maximum(Q["pairs"][:, 0], Q["pairs"][:, 1])
        new = np.array([k not in rk for k in pk.tolist()], bool) if len(pk) else np.zeros(0, bool)
        pa, pb = (pk[new] // nt), (pk[new] % nt)
        local = np.linalg.norm(cen0[pa] - cen0[pb], axis=1) < 0.015
        ang = dihedral(v, f, ea, eb); dang = ang - ang0
        l1 = np.linalg.norm(v[e[:, 0]] - v[e[:, 1]], axis=1); st = np.log(np.maximum(l1, 1e-12) / np.maximum(l0, 1e-12))
        th = Q["thick"] / R["thick"]
        _, ar1 = tri_normals(v, f); arat = ar1 / np.maximum(ar0, 1e-14)
        xl = np.zeros(nt, bool); xl[np.r_[pa[local], pb[local]]] = True
        xd = np.zeros(nt, bool); xd[np.r_[pa[~local], pb[~local]]] = True
        el0 = l0 * 100                                           # cm
        o = {"arm_deg": [round(float(x), 1) for x in Q["arm"]], "girdle": json.loads(str(Q["girdle"])),
             "new_crossing_pairs": int(new.sum()), "local": int(local.sum()), "distant": int((~local).sum()),
             "crossing_cm2": round(float(ar0[xl | xd].sum() * 1e4), 2), "sheet_cm2": round(float(ar1[arat > 4].sum() * 1e4), 1),
             "clusters": clusters(v0, f, F, lab, np.where(xl | xd)[0], ar0, ar1, "crossing") + clusters(v0, f, F, lab, np.where(arat > 4)[0], ar0, ar1, "sheet")}
        for s, sg in (("L", 1), ("R", -1)):
            S = F[s]; gh1 = J[s]["gh"].astype(float)
            so = {"joint_move_mm": {"lateral": round(float(sg * (gh1[0] - S["gh"][0]) * 1000), 1),
                                    "up": round(float((gh1[2] - S["gh"][2]) * 1000), 1),
                                    "back": round(float((gh1[1] - S["gh"][1]) * 1000), 1)}}
            for z in ZONES:
                vm = (lab == z) & (side == s); em = (ez == z) & (es == s); tm = (tz == z) & (ts == s)
                if not vm.any():
                    continue
                cz = np.isin(pa, np.where(tm)[0]) | np.isin(pb, np.where(tm)[0])
                thz = th[vm]; thz = thz[np.isfinite(thz)]
                so[z] = {"crossing_local": int((cz & local).sum()), "crossing_distant": int((cz & ~local).sum()),
                         "crossing_local_cm2": round(float(ar0[tm & xl].sum() * 1e4), 2), "crossing_distant_cm2": round(float(ar0[tm & xd & ~xl].sum() * 1e4), 2),
                         "crease30_cm": round(float(el0[em & (dang > 30)].sum()), 1), "sharp90_cm": round(float(el0[em & (ang > 90) & (ang0 <= 90)].sum()), 1),
                         "sheet_cm2": round(float(ar1[tm & (arat > 4)].sum() * 1e4), 2), "crushed_area_share": round(float(ar0[tm & (arat < 0.25)].sum() / max(ar0[tm].sum(), 1e-12)), 4),
                         "crease_gt30": int((dang[em] > 30).sum()), "sharp_gt90": int(((ang[em] > 90) & (ang0[em] <= 90)).sum()),
                         "folded_gt150": int(((ang[em] > 150) & (ang0[em] <= 150)).sum()),
                         "dihedral_p999": round(float(np.percentile(ang[em], 99.9)), 1),
                         "collapse_share": round(float((thz < 0.5).mean()), 4) if len(thz) else None,
                         "thick_ratio_p5": round(float(np.percentile(thz, 5)), 3) if len(thz) else None,
                         "stretch_share": round(float((st[em] > np.log(1.5)).mean()), 4),
                         "squash_share": round(float((st[em] < np.log(1 / 1.5)).mean()), 4),
                         "strain_p1_p99": [round(float(np.exp(np.percentile(st[em], 1))), 3), round(float(np.exp(np.percentile(st[em], 99))), 3)],
                         "move_mm_mean": [round(float(x), 1) for x in ((v[vm] - v0[vm]).mean(0) * 1000 * np.array([sg, -1, 1]))]}
            # shoulder complex volume: shoulder + axilla + upper arm, cone about the posed joint
            cm = np.isin(tz, ["shoulder", "axilla", "upper_arm"]) & (ts == s) & np.isin(lab[f[:, 1]], ["shoulder", "axilla", "upper_arm"]) & np.isin(lab[f[:, 2]], ["shoulder", "axilla", "upper_arm"])
            def cone(vv, c):
                a, b, d = vv[f[cm, 0]] - c, vv[f[cm, 1]] - c, vv[f[cm, 2]] - c
                return float(np.einsum("ij,ij->i", a, np.cross(b, d)).sum() / 6)
            V0, V1 = cone(v0, S["gh"]), cone(v, gh1)
            so["shoulder_complex_volume_ratio"] = round(V1 / V0, 4) if abs(V0) > 1e-9 else None
            nip = S["nipple"]
            so["nipple_shift_mm"] = [round(float(x), 1) for x in (v[nip] - v0[nip]) * 1000 * np.array([sg, -1, 1])]   # lateral, forward, up
            bm = (lab == "breast") & (side == s)
            dm = v[bm] - v0[bm]; so["breast_shape_change_rms_mm"] = round(float(np.sqrt(((dm - dm.mean(0)) ** 2).sum(1).mean()) * 1000), 2)
            sel = np.isin(lab, ["neck", "trapezius"]) & (side == s)
            nk = (lab == "neck") & (side == s) & (np.abs(v0[:, 2] - S["sc"][2] - 0.045) < 0.004)
            x0 = float((sg * (v0[nk, 0] - F["mid"])).max() * 1000) if nk.any() else 40.0
            so["neck_halfwidth_mm"] = round(x0, 1)
            so["neck_contour_rest"] = contour(v0, sel, F["mid"], sg, x0 - 5, S["topx"] * 1000)
            so["neck_contour"] = contour(v, sel, F["mid"], sg, x0 - 5, S["topx"] * 1000)
            o[s] = so
        out[str(T)] = o
    return out


def study(out, name):
    R, P = load(out, name)
    F = frame(R)
    lab, side = zones(R, F)
    f = R["f"].astype(np.int64)
    e, ea, eb = edge_faces(f, len(R["v"]))
    res = {"variant": name, "frame": {"mid_mm": round(F["mid"] * 1000, 1), **{s: {k: (F[s][k].round(4).tolist() if hasattr(F[s][k], "round") and not isinstance(F[s][k], (int, float)) else F[s][k]) for k in ("gh", "sc", "el", "top", "nipple", "rest_abd", "arm_len")} for s in SIDES}},
           "zone_verts": {z: int((lab == z).sum()) for z in ZONES},
           "structure": structure(R, F, lab, side, e, ea, eb),
           "weights": weights(R, F, lab, side, F["rig"]),
           "poses": pose_metrics(R, P, F, lab, side, e, ea, eb, F["rig"])}
    return res, (R, P, F, lab, side)


if __name__ == "__main__":
    a = sys.argv[1:]; js = None
    if "--json" in a:
        i = a.index("--json"); js = a[i + 1]; a = a[:i] + a[i + 2:]
    out, names = a[0], a[1:]
    allres = {}
    for nm in names:
        r, _ = study(out, nm); allres[nm] = r
        print(json.dumps(r)[:3000])
    if js:
        json.dump(allres, open(js, "w"), indent=1)
