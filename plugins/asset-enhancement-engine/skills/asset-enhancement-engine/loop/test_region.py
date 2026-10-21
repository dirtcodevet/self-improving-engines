"""PROOF of engine/loop/region.py (A10: on the failure it exists for).
1. Same answer: a NormalBumps solve on a dense sphere's cap gives the same parameters and the same surface when run on
   the cap's Region (with a margin) as on the whole mesh; vertices outside the cap are bit-identical; the margin did
   not move. Planted failure: with NO margin the bi-Laplacian basis loses its outer rings at the rim and the answer
   changes - the margin must cover what the handles and descriptors read (NormalBumps reads 2 rings).
2. Speed on base torso v11 (279k vertices): one evaluation of a breast job (a bump field applied + 20 plane sections,
   the pattern run 1 used) on the whole mesh vs on the left breast's Region.
    python engine/loop/test_region.py
"""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import Target, solve            # noqa: E402
from shape import NormalBumps             # noqa: E402
from region import Region                 # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def sphere(nu=400, nv=200, r=0.1):
    th = np.linspace(0, np.pi, nv)[1:-1]; ph = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    T, P = np.meshgrid(th, ph, indexing="ij")
    V = np.stack([r * np.sin(T) * np.cos(P), r * np.sin(T) * np.sin(P), r * np.cos(T)], -1).reshape(-1, 3)
    V = np.r_[V, [[0, 0, r], [0, 0, -r]]]; top, bot = len(V) - 2, len(V) - 1; F = []
    for i in range(nv - 3):
        for j in range(nu):
            a, b, c, d = i * nu + j, i * nu + (j + 1) % nu, (i + 1) * nu + j, (i + 1) * nu + (j + 1) % nu
            F += [[a, c, b], [b, c, d]]
    for j in range(nu):
        F += [[top, j, (j + 1) % nu], [bot, (nv - 3) * nu + (j + 1) % nu, (nv - 3) * nu + j]]
    return V, np.array(F)


def cap_reach(state, axis=(1.0, 0, 0), prefix="cap"):
    """how far the cap reaches along the axis, and its mean reach over the cap's vertices (descriptors)"""
    s = state["V"] @ np.asarray(axis); m = state["cap"]
    return {prefix + "_max_mm": float(s[m].max() * 1000), prefix + "_mean_mm": float(s[m].mean() * 1000)}


def same_answer():
    V, F = sphere(); n = len(V)
    cap = (V @ np.array([1.0, 0, 0])) > 0.1 * np.cos(np.radians(30))
    state = {"V": V, "F": F, "cap": cap}
    ids = np.where(cap)[0]; c = ids[np.argsort(-(V[ids] @ np.array([1.0, 0, 0])))]
    centres = [c[0], c[len(c) // 3], c[2 * len(c) // 3]]
    targets = [Target("cap_max_mm", 106.0, 0.2, "test", 1, inside_free=False), Target("cap_mean_mm", 94.0, 0.2, "test", 1, inside_free=False)]
    desc = [(cap_reach, {})]
    t0 = time.time()
    full, xf, _ = solve(state, [NormalBumps(state, cap, centres)], desc, targets, log=lambda *a: None)
    t_full = time.time() - t0
    edge = np.median(np.linalg.norm(V[F[:, 0]] - V[F[:, 1]], axis=1))
    out = {"vertices": n, "cap": int(cap.sum()), "edge_mm": edge * 1000, "full_s": t_full}
    for tag, margin in (("margin_4_edges", 4 * edge), ("no_margin", 0.0)):
        R = Region(state, cap, margin_m=margin); sub = R.state
        t0 = time.time()
        new_sub, xr, _ = solve(sub, [NormalBumps(sub, R.core, R.local(centres))], desc, targets, log=lambda *a: None)
        dt = time.time() - t0
        got = R.put(state, new_sub)
        out[tag] = {"sub_vertices": len(R.ids), "seconds": dt, "param_diff_um": float(np.abs(xr - xf).max() * 1e6),
                    "surface_diff_um": float(np.linalg.norm(got["V"] - full["V"], axis=1).max() * 1e6),
                    "outside_identical": bool(np.array_equal(got["V"][~cap], V[~cap]))}
    return out


def speed_v11():
    z = np.load(os.path.join(ROOT, "engine", "packs", "human", "base_female_torso", "v11", "skin.npz"))
    V, F = z["v"].astype(float), z["f"]; breast = (z["breast"] > 0.5) & (V[:, 0] > 0)
    state = {"V": V, "F": F, "breast": breast}
    nip = (z["nipple"] > 0.5) & (V[:, 0] > 0); c0 = V[nip].mean(0)

    def sections(st):
        """20 vertical plane cuts through the nipple's axis (the pattern of run 1's descriptor): crossing points count"""
        Vs, Fs = st["V"], st["F"]; tot = 0
        for a in np.linspace(0, np.pi, 20, endpoint=False):
            nrm = np.array([np.cos(a), 0.0, np.sin(a)]); s = (Vs - c0) @ nrm; sf = s[Fs]
            tot += int(((sf.min(1) < 0) & (sf.max(1) > 0)).sum())
        return tot

    ids = np.where(breast)[0]; rng = np.random.default_rng(0); centres = rng.choice(ids, 12, replace=False)
    out = {}
    for tag in ("whole mesh", "region"):
        if tag == "region":
            R = Region(state, breast, margin_m=0.01); st = R.state; cs = R.local(centres); core = R.core
        else:
            st = state; cs = centres; core = breast
        t0 = time.time(); H = NormalBumps(st, core, cs); t_build = time.time() - t0
        p = np.full(len(cs), 0.001); t0 = time.time()
        for _ in range(5):
            s2 = H.apply(st, p); k = sections(s2)
        out[tag] = {"vertices": len(st["V"]), "handle_build_s": round(t_build, 2), "evaluation_s": round((time.time() - t0) / 5, 3), "crossings": k}
    return out


if __name__ == "__main__":
    a = same_answer()
    ok1 = a["margin_4_edges"]["param_diff_um"] < 0.01 and a["margin_4_edges"]["surface_diff_um"] < 0.01 and a["margin_4_edges"]["outside_identical"]
    ok2 = a["no_margin"]["param_diff_um"] > 1.0          # the planted failure is seen
    print("same answer:", a)
    print("  region with margin matches the full solve: %s; no margin differs (planted): %s" % (ok1, ok2))
    b = speed_v11()
    print("speed on v11:", b)
    print("PASS" if ok1 and ok2 else "FAIL")
