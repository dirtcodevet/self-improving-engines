"""FOLDED FACES (2026-10-19, woman2 issue 03; the orchestrator's finding on pack_maps: folded triangles at the seam where
a rebuilt nipple-areola patch joins the old skin, 178.5-179.9 deg between neighbouring face normals, a dark notch in
clay and white specks in colour). A fold is an interior edge whose two faces' normals differ by more than `deg` (a face
turned back over its neighbour); a crease, a cut cap or a contact pocket stays well under it.
    folded(V, F, deg=150) -> dict(count, max_deg, clusters=[{centre_mm, edges, max_deg}], midpoints)
    compare(result_pack, reference_pack) -> the result's folds, and those NEW against the reference (no reference fold
                                            within 2 mm): the gate a build must pass (new == 0)
    python engine/checks/folds.py --prove     (planted folds on a grid and on a pack skin)
    python engine/checks/folds.py <pack> [<reference pack>]
engine/loop/recipe.py runs compare() on every build's result against the recipe's reference pack."""
import json, os, sys
import numpy as np


def edge_pairs(V, F):
    """interior edges (sorted vertex pairs), their two faces, and the angle between the faces' normals (deg)"""
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); fu = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-30)
    E = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1); fid = np.tile(np.arange(len(F)), 3)
    k = E[:, 0].astype(np.int64) * (len(V) + 1) + E[:, 1]; o = np.argsort(k, kind="stable"); ks = k[o]
    same = np.where(ks[1:] == ks[:-1])[0]; a, b = fid[o][same], fid[o][same + 1]
    ang = np.degrees(np.arccos(np.clip((fu[a] * fu[b]).sum(1), -1, 1)))
    return E[o][same], a, b, ang


def folded(V, F, deg=150.0, cluster_mm=5.0):
    V = np.asarray(V, float); F = np.asarray(F, np.int64)
    e, a, b, ang = edge_pairs(V, F); sel = ang > deg
    mid = (V[e[sel, 0]] + V[e[sel, 1]]) / 2; out = {"deg": deg, "count": int(sel.sum()), "max_deg": float(ang.max()) if len(ang) else 0.0,
                                                   "midpoints": mid, "clusters": []}
    if sel.any():
        from scipy.sparse.csgraph import connected_components
        from scipy.spatial import cKDTree
        pairs = cKDTree(mid).query_pairs(cluster_mm / 1000, output_type="ndarray")
        from scipy.sparse import coo_matrix
        A = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(mid), len(mid))) if len(pairs) else coo_matrix((len(mid), len(mid)))
        nc, lab = connected_components(A, directed=False); ga = ang[sel]
        for c in range(nc):
            m = lab == c
            out["clusters"].append({"centre_mm": [round(float(x) * 1000, 1) for x in mid[m].mean(0)], "edges": int(m.sum()), "max_deg": round(float(ga[m].max()), 1)})
        out["clusters"].sort(key=lambda d: -d["edges"])
    return out


def compare(pack, reference=None, deg=150.0):
    S = np.load(os.path.join(pack, "skin.npz")); r = folded(S["v"], S["f"], deg)
    rep = {k: r[k] for k in ("deg", "count", "max_deg", "clusters")}
    if reference:
        from scipy.spatial import cKDTree
        R = np.load(os.path.join(reference, "skin.npz")); rr = folded(R["v"], R["f"], deg)
        if r["count"] and rr["count"]:
            d = cKDTree(rr["midpoints"]).query(r["midpoints"])[0]; new = d > 0.002
        else:
            new = np.ones(r["count"], bool)
        rep["reference"] = {"pack": reference, "count": rr["count"]}
        rep["new"] = int(new.sum()); rep["new_midpoints_mm"] = (r["midpoints"][new] * 1000).round(1).tolist()[:20]
    return rep


def prove():
    ok = []
    def check(name, cond, info):
        ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + ": " + info)
    # a gently curved grid: no folds; one vertex pushed through its neighbours' plane: a fold; a 90 deg crease: none
    n = 30; g = np.linspace(0, 0.03, n); X, Y = np.meshgrid(g, g, indexing="ij")
    V = np.c_[X.ravel(), Y.ravel(), 0.002 * np.sin(X.ravel() * 100)]
    idx = np.arange(n * n).reshape(n, n); a_, b_, c_, d_ = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel()
    F = np.r_[np.c_[a_, b_, d_], np.c_[a_, d_, c_]]
    check("smooth grid", folded(V, F)["count"] == 0, "folded %d" % folded(V, F)["count"])
    Vf = V.copy(); i = idx[15, 15]; Vf[i, :2] = V[idx[17, 17], :2] + 0.0003    # dragged across two cells: its faces turn over
    r = folded(Vf, F); check("planted fold found", r["count"] > 0 and r["max_deg"] > 170, "folded %d, max %.1f deg" % (r["count"], r["max_deg"]))
    Vc = V.copy(); Vc[:, 2] = np.where(V[:, 0] > 0.015, V[:, 0] - 0.015, 0.0)   # a 45 deg bend: a crease, not a fold
    check("a crease is not a fold", folded(Vc, F)["count"] == 0, "folded %d" % folded(Vc, F)["count"])
    # on a pack skin: the pack's own folds, then one more planted near a nipple and found as NEW against the pack
    P = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "engine", "packs", "human", "base_female_torso", "v10")
    if os.path.exists(os.path.join(P, "skin.npz")):
        S = np.load(os.path.join(P, "skin.npz")); V0, F0 = S["v"].astype(float), S["f"].astype(np.int64)
        base = folded(V0, F0)
        nip = np.where((S["nipple"] > 0.5) & (V0[:, 0] > 0))[0]; c = V0[nip].mean(0)          # the left nipple
        far = np.where(np.abs(np.linalg.norm(V0 - c, axis=1) - 0.019) < 0.0005)[0][0]
        nb = np.unique(F0[(F0 == far).any(1)]); nb = nb[nb != far]
        V1 = V0.copy(); V1[far] = V0[nb].mean(0) + 2.2 * (V0[nb[0]] - V0[nb].mean(0))   # dragged out over its own ring
        r1 = folded(V1, F0)
        from scipy.spatial import cKDTree
        new = (cKDTree(base["midpoints"]).query(r1["midpoints"])[0] > 0.002).sum() if base["count"] else r1["count"]
        check("planted fold on the v10 skin found as new", new > 0, "v10 has %d folded edges in %d clusters (largest %s); planted: %d new"
              % (base["count"], len(base["clusters"]), base["clusters"][:2], new))
    print("ALL PASS" if all(ok) else "SOME FAILED")
    return all(ok)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--prove":
        prove()
    else:
        print(json.dumps(compare(a[0], a[1] if len(a) > 1 else None), indent=1))
