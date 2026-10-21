"""COAT check (Phase 2, criterion C1): the coat-depth table and its field are complete, cited, inside their cited ranges,
continuous, and zero on the furless areas.
usage: python coat_check.py [--coat <coat.json>] [--every K] [--prove]
  --every K  evaluate the field on every K-th vertex of the base form (default 1 = all 1.43 M; each also gets a point
             inset along -n into the band where the skin can lie, see check_field)
  --prove    run the planted failures (A10) and report whether each is caught
PARTS (each one FAILS the check on its own):
  T table     every region the field uses is in coat.json and every partition part (core, head, ears, tail, legs) has
              regions; each region has depth min <= typical <= max, guard and down lengths, density, >= 1 evidence key that
              resolves to a source with cite + says, a confidence and a status label (checked / estimated / unchecked)
  R ranges    depth min..max inside depth_cited_range_mm, guard min..max inside guard_cited_range_mm, depth max <= guard
              max (a hair cannot stand off further than its own length), down max <= guard max
  F furless   (a) wherever the field's own mask is exactly 1 (on it, not on its ramp) the depth is 0 (<= 1e-9 mm); (b) INDEPENDENT anchors read 0:
              nose leather centre at z -10 mm, both iris centres, the 20 pad lowest points, the inner-ear concavity points
              at h 10/15/20/25 mm (each snapped to the nearest base vertex, which must be < 2 mm away); (c) every mask
              covers >= 20 sampled vertices (a mask that covers nothing would pass (a) trivially)
  C continuity  pairs (P, P + h u), u random unit, h = 0.025 mm: G = max |d(P + h u) - d(P)| / h <= X = 4 mm/mm.
              WHY X = 4: the steepest DESIGNED transition is a furless ramp: the deepest neighbour of a mask (2.5 mm,
              cheeks/crown next to the eyes) over smoothstep's peak slope 1.5 / RAMP (1.5 mm) = 2.5 mm/mm; region blends
              are <= 1.5 x 3 mm / 10 mm = 0.45 mm/mm (tail 7.5 vs flanks 4.5). X = 2.5 x 1.6 margin. A step S reads S / h,
              so any step > X h = 0.1 mm is caught - 5x finer than C3's +-0.5 mm tolerance and 3x finer than its 0.3 mm
              planted bump.
  V values    where one region's weight is >= 0.999 and no mask touches, the depth lies in that region's [min, max]; and
              every region owns >= 1 such vertex (a region left empty in the field is caught here)
"""
import argparse
import copy
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(ENGINE, ".."))
TR = os.path.join(ROOT, "tripo_rebuild")
sys.path.insert(0, os.path.join(ENGINE, "packs", "felid")); sys.path.insert(0, TR)
import coat_field as CF  # noqa: E402
import partition as PT  # noqa: E402

X_GRAD = 4.0      # mm per mm (see docstring)
H_STEP = 0.000025  # m
STATUS = {"checked", "estimated", "unchecked"}
PART_OF = {"core": "core", "head": "head", "ear_R": "ear", "ear_L": "ear", "tail": "tail"}


def _rng3(d):
    return d is not None and all(isinstance(d.get(k), (int, float)) for k in ("min", "typical", "max")) and d["min"] <= d["typical"] <= d["max"]


def check_table(coat, field_regions):
    bad = []
    R = coat.get("regions", {}); S = coat.get("sources", {})
    for r in field_regions:
        if r not in R:
            bad.append(f"T: region '{r}' used by the field is missing from coat.json")
    parts = {v.get("part") for v in R.values()}
    for p in PT.PART_NAMES:
        need = PART_OF.get(p, "leg")
        if need not in parts:
            bad.append(f"T: partition part {p} has no region (needs part '{need}')")
    for k, v in R.items():
        for q in ("depth_mm", "guard_mm", "down_mm", "density_per_cm2"):
            if not _rng3(v.get(q)):
                bad.append(f"T: {k}.{q} missing or not min <= typical <= max")
        ev = v.get("evidence") or []
        if not ev:
            bad.append(f"T: {k} has no evidence")
        for e in ev:
            s = S.get(e)
            if not s or not s.get("cite") or not s.get("says"):
                bad.append(f"T: {k} evidence '{e}' has no source with cite + says")
        if not v.get("confidence"):
            bad.append(f"T: {k} has no confidence")
        if v.get("status") not in STATUS:
            bad.append(f"T: {k} status '{v.get('status')}' not one of {sorted(STATUS)}")
    for m in ("nose_leather", "eye_opening", "paw_pads", "inner_ear_pink"):
        if not coat.get("furless", {}).get(m, {}).get("rule"):
            bad.append(f"T: furless mask {m} has no rule")
    return bad


def check_ranges(coat):
    bad = []
    for k, v in coat.get("regions", {}).items():
        d, g, w = v.get("depth_mm"), v.get("guard_mm"), v.get("down_mm")
        if not (_rng3(d) and _rng3(g) and _rng3(w)):
            continue                                   # reported by T
        for name, val, cr in (("depth", d, v.get("depth_cited_range_mm")), ("guard", g, v.get("guard_cited_range_mm"))):
            if not cr or len(cr) != 2:
                bad.append(f"R: {k} has no {name}_cited_range_mm"); continue
            for q in ("min", "typical", "max"):
                if not (cr[0] <= val[q] <= cr[1]):
                    bad.append(f"R: {k}.{name}.{q} = {val[q]} outside its cited range {cr}")
        if d["max"] > g["max"]:
            bad.append(f"R: {k} depth max {d['max']} > guard max {g['max']} (standoff can't exceed hair length)")
        if w["max"] > g["max"]:
            bad.append(f"R: {k} down max {w['max']} > guard max {g['max']}")
    return bad


def _anchors(V, tree):
    """independent furless anchor points (world m), each snapped to its nearest base vertex"""
    L = os.path.join(TR, "layers"); A = []
    nose = json.load(open(os.path.join(L, "nose.json")))["leather"]["0"]["widths_by_height"]["z-10"]
    hx = (nose["x_min"] + nose["x_max"]) / 2000
    Lv = PT.head_local(V); c = np.where((np.abs(Lv[:, 0] - hx) < 0.0005) & (np.abs(Lv[:, 2] + 0.010) < 0.0005))[0]
    A.append(("nose_leather z-10 centre", V[c[np.argmin(Lv[c, 1])]]))
    E = json.load(open(os.path.join(L, "eyes.json")))
    for s in ("eye.L", "eye.R"):
        A.append((f"{s} iris centre", PT.HC + PT.HR @ (np.array(E[s]["iris_centre_mm"]) / 1000)))
    for paw, d in json.load(open(os.path.join(L, "paws.json")))["paws"].items():
        for pad, info in d["pads"].items():
            A.append((f"pad {paw} {pad} lowest", np.array(info["lowest_point_mm"]) / 1000))
    ears = json.load(open(os.path.join(L, "ears.json")))["ears"]
    for s in ("L", "R"):
        for sec in ears[s]["sections"]["per_height"]:
            if sec["h_mm"] in (10.0, 15.0, 20.0, 25.0) and sec.get("concavity_point_head_mm"):
                A.append((f"ear {s} conch h{sec['h_mm']:.0f}", PT.HC + PT.HR @ (np.array(sec["concavity_point_head_mm"]) / 1000)))
    out = []
    for name, p in A:
        dist, i = tree.query(p)
        out.append((name, V[i], dist * 1000))
    return out


def field_points(every):
    B = np.load(os.path.join(TR, "layers", "base_relief.npz")); V, N = B["v"], B["n"]
    sel = np.arange(0, len(V), every)
    P0 = V[sel]; n0 = N[sel]; n0 = n0 / np.linalg.norm(n0, axis=1, keepdims=True)
    return V, P0, n0


def check_field(depth_fn, coat, V, Psurf, Nsurf, slab=300000, seed=1, h=H_STEP, x_grad=X_GRAD, verbose=True):
    """C is tested where the SKIN can lie: on the envelope (base form) and at points inset along -n by U(0,1) x
    (1.6 x the local depth + 2 mm) - 1.6 = the largest max/typical ratio in coat.json, + 2 mm margin. Deeper inside, a
    jump (e.g. the ear's medial surface 3 mm in) can't reach the skin: env_sdf + depth stays < 0 there."""
    from scipy.spatial import cKDTree
    bad = []; rng = np.random.default_rng(seed); info = {}
    R = coat["regions"]
    # --- C continuity (+ V values and F(a) on the surface points)
    gmax, gwhere = 0.0, None; owned = {k: 0 for k in R}; mask_cov = {}; nz_on_mask = 0; vfail = []
    for i0 in range(0, len(Psurf), slab):
        Ps = Psurf[i0:i0 + slab]
        try:
            d0 = depth_fn(Ps, coat, False)
        except KeyError as e:
            return [f"C/V: field failed: {e}"], info
        Pin = Ps - Nsurf[i0:i0 + slab] * (rng.uniform(0, 1, len(Ps)) * (1.6 * np.abs(d0) + 2.0) / 1000)[:, None]
        P = np.r_[Ps, Pin]
        d, W, M = depth_fn(P, coat, True)
        for _ in range(2):
            u = rng.normal(size=P.shape); u /= np.linalg.norm(u, axis=1, keepdims=True)
            d2 = depth_fn(P + h * u, coat, False)
            g = np.abs(d2 - d) / (h * 1000)
            j = int(np.argmax(g))
            if g[j] > gmax:
                gmax, gwhere = float(g[j]), P[j].tolist()
        msum = sum(M.values())
        for k, m in M.items():
            on = m >= 1 - 1e-12                 # exactly on the mask (ramp excluded)
            mask_cov[k] = mask_cov.get(k, 0) + int(on[: len(Ps)].sum())
            nz_on_mask += int((on & (np.abs(d) > 1e-9)).sum())
        for k, w in W.items():
            core = (w >= 0.999) & (msum <= 1e-6)
            if k in R and core.any():
                owned[k] += int(core.sum()); lo, hi = R[k]["depth_mm"]["min"], R[k]["depth_mm"]["max"]
                o = core & ((d < lo - 1e-9) | (d > hi + 1e-9))
                if o.any():
                    vfail.append(f"V: {k}: {int(o.sum())} points outside [{lo}, {hi}] (e.g. {d[o][0]:.3f} mm)")
    info["G_max_mm_per_mm"] = round(gmax, 4); info["G_where_m"] = gwhere; info["mask_coverage_surface_pts"] = mask_cov
    info["region_core_pts"] = owned
    if gmax > x_grad:
        bad.append(f"C: depth changes {gmax:.2f} mm per mm (> X = {x_grad}) at {np.round(gwhere, 4).tolist()} - a step or too-steep ramp")
    bad += vfail
    for k, n in owned.items():
        if n == 0:
            bad.append(f"V: region {k} owns no vertex (empty in the field)")
    if nz_on_mask:
        bad.append(f"F(a): {nz_on_mask} points on a furless mask have depth != 0")
    for k, n in mask_cov.items():
        if n < 20:
            bad.append(f"F(c): furless mask {k} covers only {n} sampled surface vertices")
    # --- F(b) independent anchors
    tree = cKDTree(V); anc = _anchors(V, tree)
    da = depth_fn(np.array([a[1] for a in anc]), coat, False)
    info["anchors"] = {a[0]: [round(float(x), 6), round(a[2], 3)] for a, x in zip(anc, da)}
    for (name, p, dist), x in zip(anc, da):
        if dist > 2.0:      # the masks are >= 9 mm across: a 2 mm snap stays inside them (base form vs Tripo in the eye pocket ~1.3 mm)
            bad.append(f"F(b): anchor {name} is {dist:.2f} mm from the surface")
        if abs(x) > 1e-9:
            bad.append(f"F(b): anchor {name} has depth {x:.3f} mm (furless must be 0)")
    return bad, info


def default_fn(P, coat, parts):
    if parts:
        return CF.depth_mm(P, coat, return_parts=True)
    return CF.depth_mm(P, coat)


def run(coat, every, depth_fn=default_fn, x_grad=X_GRAD, h=H_STEP, pts=None, verbose=True):
    field_regions = sorted(CF.weights(np.zeros((1, 3))).keys())
    bad = check_table(coat, field_regions) + check_ranges(coat)
    V, Ps, Ns = pts if pts is not None else field_points(every)
    fb, info = check_field(depth_fn, coat, V, Ps, Ns, h=h, x_grad=x_grad)
    bad += fb
    return bad, info


def prove(every):
    """A10: each planted failure must FAIL the check; the true table + field must PASS"""
    base = CF.load_coat(); pts = field_points(every); res = {}

    def plant_coat(f):
        c = copy.deepcopy(base); f(c); return c

    cases = {
        "TRUE (must pass)": (base, default_fn),
        "region left empty (cheeks removed)": (plant_coat(lambda c: c["regions"].pop("cheeks")), default_fn),
        "region with no source (tail evidence [])": (plant_coat(lambda c: c["regions"]["tail"].__setitem__("evidence", [])), default_fn),
        "value outside its range (back typical 9 > max 8)": (plant_coat(lambda c: c["regions"]["back"]["depth_mm"].__setitem__("typical", 9.0)), default_fn),
        "value outside its cited range (tail max 25 > cited 19)": (plant_coat(lambda c: c["regions"]["tail"]["depth_mm"].__setitem__("max", 25.0)), default_fn),
    }

    def step_fn(S, rad=0.010, centre=(0.045, -0.02, 0.20)):
        c = np.array(centre)

        def f(P, coat, parts):
            out = default_fn(P, coat, parts)
            bump = S * (np.linalg.norm(P - c, axis=1) < rad)       # a disc of 20 mm with a hard edge on the left flank
            if parts:
                return (out[0] + bump * (out[0] > 0), out[1], out[2])
            return out + bump * (out > 0)
        return f

    def nomask_fn(name):
        def f(P, coat, parts):
            d, W, M = CF.depth_mm(P, coat, return_parts=True)
            # rebuild the depth WITHOUT this mask, but report the mask as present (a field that forgot to apply it)
            T = CF.typical(coat); dd = sum(W[k] * T[k] for k in W); keep = np.ones(len(P))
            for k, m in M.items():
                if k != name:
                    keep *= (1 - m)
            dd = dd * keep
            return (dd, W, M) if parts else dd
        return f

    # ramp_out reads RAMP through its default argument, so the planted steep ramp patches the function itself
    def steep_ramp_fn(ramp):
        def f(P, coat, parts):
            old = CF.ramp_out
            CF.ramp_out = lambda d, r=ramp: CF.ss(d / r)
            try:
                return default_fn(P, coat, parts)
            finally:
                CF.ramp_out = old
        return f

    cases.update({
        "step 0.3 mm (C3's bump size) on a 20 mm disc, left flank": (base, step_fn(0.3)),
        "step 0.15 mm (just above the 0.1 mm floor)": (base, step_fn(0.15)),
        "step 1.0 mm on a 20 mm disc": (base, step_fn(1.0)),
        "nose leather mask not applied": (base, nomask_fn("nose_leather")),
        "paw pad mask not applied": (base, nomask_fn("paw_pads")),
        "furless ramp too steep (0.2 mm instead of 1.5)": (base, steep_ramp_fn(0.0002)),
    })
    for name, (coat, fn) in cases.items():
        bad, info = run(coat, every, fn, pts=pts)
        res[name] = {"verdict": "FAIL" if bad else "PASS", "first_reasons": bad[:4], "G_max": info.get("G_max_mm_per_mm")}
        print(f"{name:60s} -> {res[name]['verdict']}  G={info.get('G_max_mm_per_mm')}  {bad[:2]}")
    ok = res["TRUE (must pass)"]["verdict"] == "PASS" and all(v["verdict"] == "FAIL" for k, v in res.items() if k != "TRUE (must pass)")
    print("PROOF", "PASSES" if ok else "FAILS")
    return ok, res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--coat", default=CF.COAT_PATH); ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--prove", action="store_true"); ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.prove:
        ok, res = prove(a.every)
        if a.out:
            json.dump(res, open(a.out, "w"), indent=1)
        sys.exit(0 if ok else 1)
    bad, info = run(CF.load_coat(a.coat), a.every)
    print(json.dumps(info, indent=1)[:3000])
    print("COAT CHECK", "PASS" if not bad else "FAIL"); [print("  ", b) for b in bad]
    sys.exit(0 if not bad else 1)
