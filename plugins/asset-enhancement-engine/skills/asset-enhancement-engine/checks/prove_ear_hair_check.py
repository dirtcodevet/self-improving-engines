"""A10 proof of ear_hair_check.py: it must PASS the built ear hair and FAIL each planted failure it exists to catch
(PHASE2_ROUND0 C14 planted failures + check_hair B4). usage: python prove_ear_hair_check.py [hair_ears.npz]"""
import copy
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ear_hair_check as EHC  # noqa: E402

TYP = EHC.TYPES.index


def sub(H, keep):
    G = dict(H)
    for k in ("roots", "root_normal", "type", "length_mm", "ear", "zone", "strands"): G[k] = H[k][keep]
    return G


def add(H, P, N, t, L, ear):
    G = dict(H)
    G["roots"] = np.r_[H["roots"], P]; G["root_normal"] = np.r_[H["root_normal"], N]; G["type"] = np.r_[H["type"], t]
    G["length_mm"] = np.r_[H["length_mm"], L]; G["ear"] = np.r_[H["ear"], ear]; G["zone"] = np.r_[H["zone"], np.zeros(len(P), int)]
    K = H["strands"].shape[1]; Ls = np.asarray(L, float)[:, None, None] / 1000 * np.linspace(0, 1, K)[None, :, None]
    G["strands"] = np.r_[H["strands"], (np.asarray(P)[:, None, :] + Ls * np.asarray(N)[:, None, :]).astype(H["strands"].dtype)]   # straight out of the skin
    return G


def main(path):
    H = {k: v for k, v in np.load(path, allow_pickle=True).items()}
    skin = str(H["skin_path"]); canals = {sd: json.loads(str(H[f"canal_{sd}"])) for sd in "LR"}
    rng = np.random.default_rng(7); res = {}

    def run(name, G, cn=canals, expect="PASS", key=None):
        r = EHC.check(G, skin, cn); st = r["status"]
        which = sorted({f"{sd}.{k}" for sd, e in r["ears"].items() for k, x in list(e.items()) + [(f"zones.{z}", y) for z, y in e["zones"].items()]
                        if isinstance(x, dict) and x.get("status") == "FAIL" and not k == "zones"})
        res[name] = {"status": st, "expected": expect, "ok": st == expect, "failing_probes": which}
        print(name, st, "expected", expect, which, flush=True); return r

    base = run("built", H, expect="PASS")
    # 1. Tripo's version: no hair at all (the envelope is baked fur)
    run("tripo_no_hair", sub(H, np.zeros(len(H["type"]), bool)), expect="FAIL")
    # 2. planted canal tuft: 25 hairs rooted within 1.5 mm of the left canal centre (ear-back guard, 4 mm)
    c = np.array(canals["L"]["centre_world"]); a = np.array(canals["L"]["axis_in_world"])
    u = np.cross(a, [0, 0, 1.0]); u /= np.linalg.norm(u); w = np.cross(a, u)
    rr = rng.uniform(0, 1.5e-3, 25); ph = rng.uniform(0, 2 * np.pi, 25)
    P = c + rr[:, None] * (np.cos(ph)[:, None] * u + np.sin(ph)[:, None] * w)
    run("canal_tuft", add(H, P, np.tile(-a, (25, 1)), np.full(25, TYP("ear_back_guard")), np.full(25, 4.0), np.zeros(25, int)), expect="FAIL")
    # 2b. a single canal hair of the ALLOWED inner type (density 0 means zero, not 'thin')
    run("canal_one_sparse_hair", add(H, c[None], -a[None], [TYP("inner_pinna_sparse")], [2.0], [0]), expect="FAIL")
    # 3. furnishings removed
    run("furnishings_removed", sub(H, H["type"] != TYP("ear_furnishing")), expect="FAIL")
    # 4. back-of-ear fur used inside the ear: every furnishing and sparse hair becomes ear_back down, 2 mm
    G = dict(H); G["type"] = H["type"].copy(); G["length_mm"] = H["length_mm"].copy()
    m = np.isin(H["type"], [TYP("ear_furnishing"), TYP("inner_pinna_sparse")]); G["type"][m] = TYP("ear_back_down"); G["length_mm"][m] = 2.0
    run("back_fur_inside", G, expect="FAIL")
    # 5. a 15 mm lynx tuft at the tip
    G = dict(H); G["length_mm"] = H["length_mm"].copy(); G["length_mm"][H["type"] == TYP("ear_tip_wisp")] = 15.0
    run("lynx_tuft_15mm", G, expect="FAIL")
    # 6. canal definition missing (check_hair B4: must FAIL, not pass trivially)
    run("canal_missing", H, cn={"L": None, "R": canals["R"]}, expect="FAIL")
    # 7. canal definition moved onto the ear BACK (no conch there): 6 mm behind along -front
    E = EHC.Ear("L"); cn = copy.deepcopy(canals); cn["L"]["centre_world"] = (c - 0.006 * E.w).tolist()
    run("canal_on_ear_back", H, cn=cn, expect="FAIL")
    # 8. canal definition placed in Henry's pocket (the other deep hollow at the base)
    import partition as PA
    pf = np.array(E.pocket_floor_head[len(E.pocket_floor_head) // 2]) / 1000.0; pw = PA.HC + PA.HR @ pf
    cn = copy.deepcopy(canals); cn["L"]["centre_world"] = pw.tolist()
    run("canal_in_pocket", H, cn=cn, expect="FAIL")
    # 9. ear-back density halved and halved again (25 %): 15/mm2 < palette min 30
    keep = ~(np.isin(H["type"], [TYP("ear_back_guard"), TYP("ear_back_down")]) & (rng.random(len(H["type"])) < 0.75))
    run("ear_back_density_quartered", sub(H, keep), expect="FAIL")
    # 10. hair through the skin: every furnishing's points 4..K pushed 1 mm into the tissue (the first build's real
    #     defect: straight tangent shapes cut the concave cup - see the negative control in the build record)
    G = dict(H); st = H["strands"].copy(); m = H["type"] == TYP("ear_furnishing")
    st[m, 3:] -= (H["root_normal"][m][:, None, :] * 0.001).astype(st.dtype); G["strands"] = st
    run("furnishings_through_skin", G, expect="FAIL")
    allok = all(r["ok"] for r in res.values())
    print(json.dumps({"proof": "PASS" if allok else "FAIL", "cases": res}, indent=1))
    return base, res


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(EHC.TR, "layers", "hair_ears.npz"))
