"""PROOF of cat_decisions.py (A22: planted failures on BOTH sides): every decision check must PASS a planted good case and
FAIL planted defects, then it is run on the v2 meshes (the Phase 2 assembled cat, which should FAIL several).
usage: python prove_cat_decisions.py [out.json]   (default tripo_rebuild/layers/cat_decisions_v3_proof.json)
Planted cases are built from the real meshes (skin v1, the v2 assembled skin) by displacing vertices, or analytically
(an ear sheet in the real ear frame; anatomical / wrong globes and full optical eyes in spec_eyes' eye frames).
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cat_decisions as CD  # noqa: E402

ROWS = []


def row(check, case, expect, res, note=""):
    got = res["status"] if isinstance(res, dict) else res
    ok = got == expect; ROWS.append({"check": check, "case": case, "expect": expect, "got": got, "proof_ok": ok, "note": note})
    print(f"{'ok ' if ok else 'BAD'} {check:18s} {case:58s} expect {expect:4s} got {got}", flush=True)
    return res


def displaced(sk, w, delta, label):
    return CD.Skin(sk.P + (delta * w)[:, None] * sk.N, sk.f, sk.N, label)


# ------------------------------------------------------------------ D1 + D2 on skin v1 with planted edits
def prove_nose(v1):
    import coat_field as CF
    import partition as PT
    import skin_build as SB
    import feat_nose as FN
    R = np.load(CD.V1_PATH); u = SB.leather_top_zone(R["v"].astype(float), CF)
    paths = CD.tail_paths(); dt = np.full(len(v1.P), np.inf)
    near = np.all((v1.P > CD.nose_box(0)[0] - 5) & (v1.P < CD.nose_box(0)[1] + 5), axis=1); ni = np.nonzero(near)[0]
    for p in paths.values():
        dt[ni] = np.minimum(dt[ni], CD.dist_to_path(v1.P[ni], p))
    out = {}
    out["v1_itself"] = row("D1_leather_top", "v1 itself", "PASS", CD.check_leather_top(v1))
    w_out = u * (dt >= FN.TAIL_ZONE_MM + 0.5)
    out["v1_+0.30_outside_tails"] = row("D1_leather_top", "v1, band pushed out 0.30 mm outside the tail zones", "FAIL",
                                        CD.check_leather_top(displaced(v1, w_out, 0.30, "p")))
    out["v1_-0.30_outside_tails"] = row("D1_leather_top", "v1, band pushed in 0.30 mm outside the tail zones", "FAIL",
                                        CD.check_leather_top(displaced(v1, w_out, -0.30, "p")))
    out["v1_+0.15_outside_tails"] = row("D1_leather_top", "v1, band pushed out 0.15 mm (inside the 0.2 limit)", "PASS",
                                        CD.check_leather_top(displaced(v1, w_out, 0.15, "p")))
    w_in = (dt < FN.TAIL_ZONE_MM - 0.4).astype(float)
    out["v1_-0.6_inside_tails_only"] = row("D1_leather_top", "v1, 0.6 mm cut inside the tail-entry zones only", "PASS",
                                           CD.check_leather_top(displaced(v1, w_in, -0.6, "p")))
    # ---- D2: grooves planted on v1 (inward = -N), half-depth width 0.5 mm (feat_nose GROOVE_HW)
    from scipy.spatial import cKDTree
    rv, rf = CD.v1_nose(); cl = CD.Closest(rv, rf)

    def groove(depth, legs=(0, 1), sides=("R", "L"), hw=0.5):
        """inward Gaussian groove about the path PROJECTED onto v1 (the straight 3-D chord leaves the curved surface by
        up to ~0.3 mm, which would weaken a groove planted about the chord)"""
        g = np.zeros(len(v1.P))
        for sd in sides:
            p = paths[sd]; pts = []
            for k in legs:
                t = np.linspace(0, 1, max(int(np.linalg.norm(p[k + 1] - p[k]) / 0.03), 2))[:, None]
                pts.append(p[k] + t * (p[k + 1] - p[k]))
            S, _, _ = cl(np.vstack(pts)); d, _ = cKDTree(S).query(v1.P[ni])
            g[ni] = np.maximum(g[ni], 2.0 ** (-(2 * d / hw) ** 2))
        return g * depth
    def gsk(g, label, lift=None):
        P = v1.P - g[:, None] * v1.N
        if lift is not None:
            P = P + (lift * u)[:, None] * v1.N
        return CD.Skin(P, v1.f, v1.N, label)
    out["D2_v1_itself"] = row("D2_nostril_tails", "v1 itself (no cut)", "FAIL", CD.check_nostril_tails(v1))
    out["D2_full_0.4"] = row("D2_nostril_tails", "v1 + 0.4 mm cut along open_end->tail_tip->corner", "PASS",
                             CD.check_nostril_tails(gsk(groove(0.4), "p")))
    out["D2_groove_leg_only"] = row("D2_nostril_tails", "v1 + 0.4 mm cut stopping at the tail tip (as Phase 2)", "FAIL",
                                    CD.check_nostril_tails(gsk(groove(0.4, legs=(0,)), "p")))
    out["D2_full_0.1"] = row("D2_nostril_tails", "v1 + 0.1 mm cut (too shallow)", "FAIL", CD.check_nostril_tails(gsk(groove(0.1), "p")))
    out["D2_full_1.5"] = row("D2_nostril_tails", "v1 + 1.5 mm gouge", "FAIL", CD.check_nostril_tails(gsk(groove(1.5, hw=1.2), "p")))
    out["D2_L_only"] = row("D2_nostril_tails", "v1 + 0.4 mm full cut on L only", "FAIL", CD.check_nostril_tails(gsk(groove(0.4, sides=("L",)), "p")))
    out["D2_lifted_band_plus_cut"] = row("D2_nostril_tails", "v1 band lifted 0.3 mm + 0.4 mm full cut", "PASS",
                                         CD.check_nostril_tails(gsk(groove(0.4), "p", lift=0.3)))
    return out


# ------------------------------------------------------------------ D3 synthetic ear sheet in the real L ear frame
def ear_sheet(E, bulge=0.0, relief=0.0, t0=1.8, t1=1.2, step=0.25):
    H = E["H"]; hs = np.arange(0.05 * H, 0.98 * H, step); V_in, V_bk, fin = [], [], []
    nx = 141; rows = []
    for h in hs:
        W = 32.0 * (1 - h / H) + 2.0; x = np.linspace(-W / 2, W / 2, nx); rows.append((h, x))
    def surf(h, x, back):
        wv = 0.035 * x ** 2 + relief * np.sin(x / 1.2) * np.sin(h / 1.7)
        if not back:
            hb = 0.55 * H; wv = wv + bulge * np.exp(-((x) ** 2 + (h - hb) ** 2) / (2 * 4.0 ** 2))
        else:
            wv = wv - (t0 + (t1 - t0) * h / H)
        return E["O"] + h * E["A"] + np.outer(x, E["l"]) + np.outer(wv, E["w"])
    Pin = np.vstack([surf(h, x, False) for h, x in rows]); Pbk = np.vstack([surf(h, x, True) for h, x in rows])
    nh = len(rows); i = np.arange(nh - 1)[:, None] * nx + np.arange(nx - 1)[None]; i = i.ravel()
    f = np.vstack([np.c_[i, i + 1, i + nx], np.c_[i + 1, i + nx + 1, i + nx]])
    P = np.vstack([Pin, Pbk]); F = np.vstack([f, f[:, ::-1] + len(Pin)]); N = CD.vertex_normals(P, F)
    if (N[:len(Pin)] @ E["w"]).mean() < 0:
        F = F[:, ::-1]; N = -N
    return P, F, N


def prove_ears(v2):
    fr = CD.ear_frames(); E = fr["L"]; out = {}
    for name, kw, exp in (("clean cupped sheet", {}, "PASS"), ("sheet + 0.25 mm conch relief", {"relief": 0.25}, "PASS"),
                          ("sheet + 0.3 mm bulge", {"bulge": 0.3}, "PASS"), ("sheet + 0.8 mm bulge", {"bulge": 0.8}, "FAIL"),
                          ("sheet + 3 mm baked-hair bulge", {"bulge": 3.0}, "FAIL")):
        P, F, N = ear_sheet(E, **kw); r = CD.ear_bulge_one(P, F, N, E); r.pop("_bulge"); r.pop("_inner")
        out[name] = row("D3_ear_bulge", "synthetic " + name, exp, r)
    # real geometry, both sides: v2's REAL back face (Tripo's cupped pinna shape) + an inner sheet 1.3 mm in front of it
    # (an anatomical thin pinna on the real ear shape) -> PASS; the same with a 1.5 mm bulge in the cup -> FAIL
    for sd, Ei in fr.items():
        q = v2.P - Ei["O"]; h = q @ Ei["A"]; rad = np.linalg.norm(q - np.outer(h, Ei["A"]), axis=1)
        bk = (h >= 0.2 * Ei["H"]) & (h <= 0.97 * Ei["H"]) & (rad <= 30) & (v2.N @ Ei["w"] < -0.3)
        fb = v2.f[bk[v2.f].all(1)]; idx = np.unique(fb); rm = -np.ones(len(v2.P), np.int64); rm[idx] = np.arange(len(idx))
        Pb, fb, Nb = v2.P[idx], rm[fb], v2.N[idx]
        for B, exp in ((0.0, "PASS"), (1.5, "FAIL")):
            Pi = Pb - 1.3 * Nb; hb = (Pi - Ei["O"]) @ Ei["A"]; c = Pi[np.argmin(np.abs(hb - 0.55 * Ei["H"]) + 0.05 * np.linalg.norm((Pi - Ei["O"]) - np.outer(hb, Ei["A"]), axis=1))]
            Pi = Pi - (B * np.exp(-np.sum((Pi - c) ** 2, 1) / (2 * 4.0 ** 2)))[:, None] * Nb
            P = np.vstack([Pb, Pi]); F = np.vstack([fb, fb[:, ::-1] + len(Pb)]); N = np.vstack([Nb, -Nb])
            r = CD.ear_bulge_one(P, F, N, Ei); r.pop("_bulge"); r.pop("_inner")
            out[f"v2_back_face_sheet_{sd}_bulge{B}"] = row("D3_ear_bulge", f"v2 real {sd} back face + 1.3 mm inner sheet, bulge {B} mm", exp, r)
    return out


# ------------------------------------------------------------------ D4 + D5 analytic eyes in spec_eyes' frames
def _cap(centre, n, u, v, r, amin, amax, na=28, nphi=72):
    """sphere patch about axis n: polar angle a in [amin, amax] (rad); returns verts, faces (a ring grid)"""
    A = np.linspace(amin, amax, na); Ph = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    a, p = np.meshgrid(A, Ph, indexing="ij")
    d = np.cos(a)[..., None] * n + np.sin(a)[..., None] * (np.cos(p)[..., None] * u + np.sin(p)[..., None] * v)
    V = (centre + r * d).reshape(-1, 3); f = []
    for i in range(na - 1):
        for j in range(nphi):
            a0, a1, b0, b1 = i * nphi + j, i * nphi + (j + 1) % nphi, (i + 1) * nphi + j, (i + 1) * nphi + (j + 1) % nphi
            f += [[a0, b0, a1], [a1, b0, b1]]
    return V, np.array(f, np.int64)


def make_eye(sag=5.70, iris_mode="real", hole=(2.0, 7.0), cornea_only=False, no_cornea=False):
    import feat_eyes as FY
    RS, a = FY.P_["RS"], FY.P_["LIMBUS_R"]; zl = np.sqrt(RS ** 2 - a ** 2); D = {}; meta = {"frame": {}, "chamber": {"depth_mm": {}}}
    for sd in ("L", "R"):
        E = FY.EYES[sd]; C, n, u, v = E["Cs"], E["n"], E["u"], E["v"]
        meta["frame"][sd] = {"centre": C.tolist(), "n": n.tolist(), "u": u.tolist(), "v": v.tolist()}
        if no_cornea:
            Vs, Fs = _cap(C, n, u, v, RS, 0.0, np.pi, na=90)
            D[f"sclera_{sd}_v"], D[f"sclera_{sd}_f"] = Vs, Fs; D[f"cornea_front_{sd}_v"], D[f"cornea_front_{sd}_f"] = Vs[:0], Fs[:0]
            D[f"cornea_front_{sd}_v"] = Vs[(Vs - C) @ n > zl]; continue
        rc = (a ** 2 + sag ** 2) / (2 * sag); dc = zl + sag - rc; Cc = C + dc * n
        al = np.arccos(np.clip((zl - dc) / rc, -1, 1)); Vc, Fc = _cap(Cc, n, u, v, rc, 0.0, al, na=40)
        th = np.arccos(zl / RS); Vs, Fs = _cap(C, n, u, v, RS, th, np.pi, na=60)
        rb = rc - 0.6; alb = np.arccos(np.clip((zl + 0.05 - dc) / rb, -1, 1)); Vb, Fb = _cap(Cc, n, u, v, rb, 0.0, alb, na=30)
        ax_i = zl + 0.15; ro = 0.97 * np.sqrt(max(rb ** 2 - (ax_i - dc) ** 2, 1.0))
        ph = np.linspace(0, 2 * np.pi, 72, endpoint=False); s = np.linspace(0, 1, 12)
        if hole is None:
            inner = np.zeros((72, 2)) + 1e-3
        else:
            inner = np.c_[hole[0] / 2 * np.cos(ph), hole[1] / 2 * np.sin(ph)]
        outer = np.c_[ro * np.cos(ph), ro * np.sin(ph)]; Q = (1 - s)[:, None, None] * inner[None] + s[:, None, None] * outer[None]
        Vi = (C + ax_i * n + Q[..., 0:1] * u + Q[..., 1:2] * v).reshape(-1, 3)
        if iris_mode == "painted":                          # the iris drawn on the cornea: each point pushed onto the cornea - 0.05
            q = Vi - Cc; Vi = Cc + (rc - 0.05) * q / np.linalg.norm(q, axis=1)[:, None]
        Fi = []
        for i in range(len(s) - 1):
            for j in range(72):
                a0, a1, b0, b1 = i * 72 + j, i * 72 + (j + 1) % 72, (i + 1) * 72 + j, (i + 1) * 72 + (j + 1) % 72
                Fi += [[a0, b0, a1], [a1, b0, b1]]
        Fi = np.array(Fi, np.int64)
        if hole is None:                                    # close the centre: a fan to one apex vertex
            Vi = np.vstack([Vi, (C + ax_i * n)[None]]); c0 = len(Vi) - 1; Fi = np.vstack([Fi, [[c0, j, (j + 1) % 72] for j in range(72)]])
        Vl, Fl = _cap(C + (ax_i - 0.1 - 3.8) * n, n, u, v, 3.8, 0.0, np.pi, na=24, nphi=48)
        for k, (V_, F_) in {"cornea_front": (Vc, Fc), "cornea_back": (Vb, Fb), "iris": (Vi, Fi), "lens": (Vl, Fl), "sclera": (Vs, Fs)}.items():
            D[f"{k}_{sd}_v"], D[f"{k}_{sd}_f"] = V_, F_
        pm = Vi[:72] if hole is not None else Vi
        meta["chamber"]["depth_mm"][sd] = round(float(((Vc - C) @ n).max() - np.median((pm - C) @ n)), 3)
    meta.update({"ior": {"cornea": 1.376, "aqueous": 1.336, "lens": 1.40},
                 "iris": {sd: {"lab": [55.0, -5.0, -25.0], "dE00_photo": 1.8, "camera": "camera_v3 (synthetic proof)",
                               "camera_validated": False, "texture": "radial fibre"} for sd in "LR"},
                 "pupil": {sd: {"size_mm": list(hole) if hole else [2.0, 7.0], "shape": "vertical slit", "source": "photo (synthetic proof)"} for sd in "LR"},
                 "sclera_lab": [80.0, 2.0, 8.0]})
    meta["chamber"].update({"definition": "cornea apex to the pupil margin along the axis", "source": "synthetic proof value (declared = built)"})
    D["meta"] = json.dumps(meta)
    return D


def with_meta(D, fn):
    M = json.loads(D["meta"]); fn(M); E = dict(D); E["meta"] = json.dumps(M); return E


def prove_eyes():
    out = {}
    ok = make_eye()
    out["cornea_anatomical"] = row("D4_cornea", "analytic globe, sag 5.70 (r 8.82)", "PASS", CD.check_cornea(ok))
    out["cornea_none"] = row("D4_cornea", "plain sphere, no cornea", "FAIL", CD.check_cornea(make_eye(no_cornea=True)))
    out["cornea_flat"] = row("D4_cornea", "Tripo-flat cornea, sag 4.5 (r 9.81)", "FAIL", CD.check_cornea(make_eye(sag=4.5)))
    out["cornea_steep"] = row("D4_cornea", "over-steep cornea, sag 8.0 (r 8.25)", "FAIL", CD.check_cornea(make_eye(sag=8.0)))
    out["cornea_v2"] = row("D4_cornea", "v2 globes (cat_p2_globes)", "PASS", CD.check_cornea(CD.V2_GLOBES), "the v2 globe was built anatomical")
    out["eye_ok"] = row("D5_eye_optics", "full optical eye (cornea, aqueous, iris, slit pupil, lens)", "PASS", CD.check_eye_optics(ok))
    painted = make_eye(iris_mode="painted")
    out["eye_painted"] = row("D5_eye_optics", "iris + pupil painted on the cornea (declared honestly)", "FAIL", CD.check_eye_optics(painted))
    out["eye_no_refraction"] = row("D5_eye_optics", "no refraction (IOR 1.0)", "FAIL",
                                   CD.check_eye_optics(with_meta(ok, lambda M: M["ior"].update(cornea=1.0, aqueous=1.0))))
    out["eye_grey_iris"] = row("D5_eye_optics", "grey iris = sclera colour, dE not recorded", "FAIL",
                               CD.check_eye_optics(with_meta(ok, lambda M: [M["iris"][s].update(lab=M["sclera_lab"], dE00_photo=None) for s in "LR"])))
    out["eye_dE_6"] = row("D5_eye_optics", "iris dE00 vs photo 6.0", "FAIL",
                          CD.check_eye_optics(with_meta(ok, lambda M: M["iris"]["R"].update(dE00_photo=6.0))))
    out["eye_closed_pupil"] = row("D5_eye_optics", "iris with no pupil hole", "FAIL", CD.check_eye_optics(make_eye(hole=None)))
    out["eye_wrong_pupil"] = row("D5_eye_optics", "built slit 2x7 mm, photo says 4x7 mm", "FAIL",
                                 CD.check_eye_optics(with_meta(ok, lambda M: M["pupil"]["L"].update(size_mm=[4.0, 7.0]))))
    out["eye_uncited_depth"] = row("D5_eye_optics", "chamber depth with no source", "FAIL",
                                   CD.check_eye_optics(with_meta(ok, lambda M: M["chamber"].update(source=""))))
    out["eye_v2"] = row("D5_eye_optics", "v2 globes (blank spheres)", "FAIL", CD.check_eye_optics(CD.V2_GLOBES))
    return out


# ------------------------------------------------------------------ D6 + D7
INV_V2 = os.path.join(os.environ.get("TEMP", ""), "p2_skin_feat", "checks", "chk_inventory.json")
HAIR_V2 = os.path.join(CD.LAYERS, "cat_p2_hair_checks.json")


def prove_lips(v2):
    out = {}; zi, info = CD.lip_zone(v2); zone = (zi, info)
    allp = {"parts": [{"part": p, "status": "PASS"} for p in CD.MOUTH_PARTS]}
    w = np.zeros(len(v2.P)); w[zi] = 1.0
    out["v2_itself_struct"] = row("D6_lips(a)", "v2 itself (structure)", "PASS", CD.check_lips(v2, v2, allp, zone)["a_structure"])
    out["v2_+0.8"] = row("D6_lips(a)", "v2 upper lip pushed out 0.8 mm outside the fixed zones", "FAIL",
                         CD.check_lips(displaced(v2, w, 0.8, "p"), v2, allp, zone)["a_structure"])
    out["v2_-0.8"] = row("D6_lips(a)", "v2 upper lip pulled in 0.8 mm outside the fixed zones", "FAIL",
                         CD.check_lips(displaced(v2, w, -0.8, "p"), v2, allp, zone)["a_structure"])
    out["v2_+0.3"] = row("D6_lips(a)", "v2 upper lip pushed out 0.3 mm (refinement)", "PASS",
                         CD.check_lips(displaced(v2, w, 0.3, "p"), v2, allp, zone)["a_structure"])
    import feat_mouth as FM
    cor = np.array([FM.GEOM[s]["C"][-1] for s in ("L", "R")]); wc = (np.min(np.linalg.norm(v2.P[:, None] - cor[None], axis=2), 1) < 2.5).astype(float)
    out["v2_corners_1.5"] = row("D6_lips(a)", "v2 corners (fixed zone) moved 1.5 mm", "PASS",
                                CD.check_lips(displaced(v2, wc, 1.5, "p"), v2, allp, zone)["a_structure"])
    out["probes_all_pass"] = row("D6_lips", "v2 structure + all mouth parts PASS (unbound result)", "PASS", CD.check_lips(v2, v2, allp, zone))
    one = {"parts": [{"part": p, "status": "FAIL" if p == "lower_lip_chin" else "PASS"} for p in CD.MOUTH_PARTS]}
    out["probes_one_fail"] = row("D6_lips", "v2 structure + lower_lip_chin FAIL", "FAIL", CD.check_lips(v2, v2, one, zone))
    out["probes_missing"] = row("D6_lips", "v2 structure, no inventory result", "FAIL", CD.check_lips(v2, v2, None, zone))
    other = dict(allp, skin_sha1="0" * 40)
    out["probes_other_skin"] = row("D6_lips", "all PASS but run on another skin", "FAIL", CD.check_lips(v2, v2, other, zone))
    if os.path.exists(INV_V2):
        out["v2_real"] = row("D6_lips", "v2 with its Phase 2 inventory result", "FAIL", CD.check_lips(v2, v2, INV_V2, zone))
    return out


def prove_hair_fold():
    out = {}; good_w = {"whiskers": {"pass": True}}; good_e = {"ears": {"status": "PASS"}}
    inv = {"parts": [{"part": "henrys_pocket.R", "status": "PASS"}, {"part": "henrys_pocket.L", "status": "PASS"}]}
    out["all_pass"] = row("D7_hair_and_fold", "C13, C14, C6b all PASS", "PASS", CD.check_hair_and_fold("abc", good_w, good_e, inv))
    out["c13_fail"] = row("D7_hair_and_fold", "C13 FAIL", "FAIL", CD.check_hair_and_fold("abc", {"whiskers": {"pass": False}}, good_e, inv))
    out["c14_missing"] = row("D7_hair_and_fold", "C14 result missing", "FAIL", CD.check_hair_and_fold("abc", good_w, None, inv))
    bad = {"parts": [{"part": "henrys_pocket.R", "status": "PASS"}, {"part": "henrys_pocket.L", "status": "FAIL"}]}
    out["c6b_L_fail"] = row("D7_hair_and_fold", "henrys_pocket.L FAIL", "FAIL", CD.check_hair_and_fold("abc", good_w, good_e, bad))
    out["stale"] = row("D7_hair_and_fold", "all PASS but C13 run on another skin", "FAIL",
                       CD.check_hair_and_fold("abc", dict(good_w, skin_sha1="zzz"), good_e, inv))
    if os.path.exists(INV_V2):
        out["v2_real"] = row("D7_hair_and_fold", "v2 results (cat_p2_hair_checks + Phase 2 inventory)", "FAIL",
                             CD.check_hair_and_fold(None, HAIR_V2, HAIR_V2, INV_V2))
    return out


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, list):
        return [strip(x) for x in o]
    return o


if __name__ == "__main__":
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(CD.LAYERS, "cat_decisions_v3_proof.json")
    t0 = time.time(); R = {"generated_epoch": int(t0)}
    v1 = CD.Skin.load(CD.V1_PATH, "skin v1 (person-approved leather top)")
    R["nose"] = prove_nose(v1); del v1
    v2 = CD.Skin.load(CD.V2_SKIN, "v2 (cat_p2_skin)")
    R["ears"] = prove_ears(v2)
    R["eyes"] = prove_eyes()
    R["lips"] = prove_lips(v2)
    R["hair_fold"] = prove_hair_fold()
    R["rows"] = ROWS; R["all_proofs_ok"] = all(r["proof_ok"] for r in ROWS); R["seconds"] = round(time.time() - t0, 1)
    json.dump(strip(R), open(out_path, "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print("ALL PROOFS OK" if R["all_proofs_ok"] else "SOME PROOFS FAILED", R["seconds"], "s ->", out_path)
