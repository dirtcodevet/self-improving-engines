"""A10 proofs for inventory_check.py (checksB, Phase 2 C4).
  N1 nostril probe on Tripo must FAIL (Phase 1: blind 2.15 / 2.31 mm dishes) - and read near those depths
  N2 control: the same nose re-meshed from the exact face SDF (0.4 mm) with NO hole must still FAIL
  N3 plant: a cylinder cavity (r 1.2 mm) carved into the SDF copy to planted depth 3/4/5/6 mm -> the probe reads
     the planted depth (sized to what it reads) and passes from 5 mm (4.0 mark)
  E1 eyelid probe on Tripo must PASS with an overhang (REVIEW_eyes: ~0.3-0.5 mm, ~1 mm medial)
  E2 synthetic eyes: lid wrapping 0.5 / 1.0 mm -> PASS reading ~w; butted lid -> FAIL; globe poking through the skin
     -> FAIL (inside share)
  R1 registry: no builder -> every entry FAILS; a stub part claimed -> FAIL; the eye entry FAILS while the third
     eyelid is a stub even when the lid wrap passes; every inventory entry is mapped
  +-1 step of every setting for N1 / E1.
usage (from tripo_rebuild): python ../engine/checks/prove_inventory_check.py [out.json]
"""
import json
import os
import sys
import time

import numpy as np
from skimage.measure import marching_cubes

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TR = os.path.join(ROOT, "tripo_rebuild"); sys.path.insert(0, HERE); sys.path.insert(0, TR)
import inventory_check as IC  # noqa: E402
import partition as PT  # noqa: E402
from eyes import quad_dist  # noqa: E402
from scipy.sparse import coo_matrix  # noqa: E402
from scipy.sparse.csgraph import connected_components  # noqa: E402

t0 = time.time(); OUT = {}; ALL = []


def ok(name, cond, msg):
    ALL.append(bool(cond)); print(f"{'PASS' if cond else 'FAIL'}  {name}: {msg}", flush=True); OUT[name] = {"ok": bool(cond), "msg": msg}


T = np.load(os.path.join(TR, "tripo_welded.npz")); v, f = T["v"], T["f"]; L = PT.head_local(v) * 1000
NB = json.load(open(os.path.join(TR, "layers", "nose_basins.json")))
NIN = {sd: {"opening_centre_mm": np.array(NB[sd]["rim_head"]).mean(0).tolist(), "axis_into_head": NB[sd]["best_view_axis_into_head"]} for sd in "RL"}

# ---------------- N1 Tripo nostrils
for sd in "RL":
    r = IC.nostril_probe(L, f, NIN[sd]); grid = []
    for rho in (0.5, 1.0, 1.5):
        for al in (8.0, 16.0, 24.0):
            for bk in ((0.5, 1.0, 2.0) if (rho, al) == (1.0, 16.0) else (1.0,)):
                q = IC.nostril_probe(L, f, NIN[sd], rho=rho, alpha=al, back=bk); grid.append((rho, al, bk, q["value_mm"], q["status"]))
    vals = [g[3] for g in grid]
    ok(f"N1 Tripo nostril {sd} FAILS", r["status"] == "FAIL" and all(g[4] == "FAIL" for g in grid) and abs(r["value_mm"] - NB[sd]["depth_max_over_views_mm"]) < 1.0,
       f"depth {r['value_mm']} mm (nose_basins {NB[sd]['depth_max_over_views_mm']}), breach {r['breach_rays']}; +-1 step of rho/alpha/back {min(vals):.2f}-{max(vals):.2f} mm, all FAIL")
    OUT[f"N1_grid_{sd}"] = grid

# ---------------- N2/N3 SDF copy with a planted cylinder cavity
D = np.load(os.path.join(TR, "vol", "face.npz")); sdf, lo, vox = D["sdf"], D["lo"], float(D["vox"])
for sd in "RL":
    c = np.array(NIN[sd]["opening_centre_mm"]); a = IC.unit(NIN[sd]["axis_into_head"])
    cw = (c / 1000) @ PT.HR.T + PT.HC; ic = np.round((cw - lo) / vox).astype(int); h = int(14e-3 / vox)
    s0 = [max(ic[k] - h, 0) for k in range(3)]; s1 = [min(ic[k] + h, sdf.shape[k]) for k in range(3)]
    S = sdf[s0[0]:s1[0], s0[1]:s1[1], s0[2]:s1[2]].astype(np.float64)
    gi = np.stack(np.meshgrid(*[np.arange(s0[k], s1[k]) for k in range(3)], indexing="ij"), -1).reshape(-1, 3)
    Lg = PT.head_local(lo + gi * vox) * 1000; X = Lg - c; u = X @ a; rr = np.linalg.norm(X - u[:, None] * a, axis=1)
    print(f"   SDF at the {sd} opening centre: {sdf[tuple(ic)]*1000:+.2f} mm (crop {S.shape})", flush=True)
    reads = {}
    for Dp in (None, 3.0, 4.0, 5.0, 6.0):
        if Dp is None:
            S2 = S
        else:
            cyl = np.maximum(rr - 1.2, np.maximum(-3.0 - u, u - Dp)).reshape(S.shape) / 1000
            S2 = np.maximum(S, -cyl)
        vv, ff, _, _ = marching_cubes(S2, 0.0)
        ff = ff[:, ::-1].copy()                                   # outward normals for a negative-inside field
        Lm = PT.head_local(lo + (vv + np.array(s0)) * vox) * 1000
        reads[Dp] = IC.nostril_probe(Lm, ff, NIN[sd])
    r0 = reads[None]
    ok(f"N2 SDF-copy control {sd} FAILS", r0["status"] == "FAIL" and abs(r0["value_mm"] - NB[sd]["depth_max_over_views_mm"]) < 1.0,
       f"no hole: {r0['value_mm']} mm (Tripo dish {NB[sd]['depth_max_over_views_mm']})")
    errs = {Dp: reads[Dp]["value_mm"] - Dp for Dp in (3.0, 4.0, 5.0, 6.0)}
    ok(f"N3 planted cavity {sd}", reads[3.0]["status"] == "FAIL" and reads[5.0]["status"] == "PASS" and reads[6.0]["status"] == "PASS" and max(abs(e) for e in errs.values()) < 0.6,
       "planted 3/4/5/6 mm -> read " + " / ".join(f"{reads[Dp]['value_mm']:.2f} {reads[Dp]['status']}" for Dp in (3.0, 4.0, 5.0, 6.0)) + f"; max |read - planted| {max(abs(e) for e in errs.values()):.2f} mm")
    OUT[f"N3_reads_{sd}"] = {str(k): r for k, r in reads.items()}
del sdf, D

# ---------------- E1 Tripo eyelids
E = json.load(open(os.path.join(TR, "layers", "eyes.json")))
used = np.zeros(len(v), bool); used[f.ravel()] = True
EIN = {}
for sd, sx in (("L", 1), ("R", -1)):
    e = E[f"eye.{sd}"]; q, m = np.array(e["quadric"]), np.array(e["quadric_origin_mm"]); icn = np.array(e["iris_centre_mm"])
    box = used & (np.abs(L[:, 0] - sx * 19) < 16) & (np.abs(L[:, 1] + 32) < 16) & (np.abs(L[:, 2] - 5) < 14)
    d = np.full(len(v), np.inf); d[box] = quad_dist(q, m, L[box], sign_ref=icn + np.array([0, -5.0, 0]))
    cand = box & (np.abs(d) < 0.25) & (np.linalg.norm(L - icn, axis=1) < 12)
    fr = f[cand[f].all(1)]; G = coo_matrix((np.ones(2 * len(fr)), (np.r_[fr[:, 0], fr[:, 1]], np.r_[fr[:, 1], fr[:, 2]])), shape=(len(v), len(v)))
    _, lab = connected_components(G, directed=False); idx = np.nonzero(cand)[0]; seed = idx[np.argmin(np.linalg.norm(L[idx] - icn, axis=1))]
    reg = cand & (lab == lab[seed]); gfaces = np.nonzero(reg[f].all(1))[0]
    EIN[sd] = {"globe_faces": gfaces.tolist(), "centre_mm": icn.tolist(), "outward": [0, -1.0, 0]}
    r = IC.eyelid_probe(L, f, EIN[sd]); steps = []
    for kw in ({"mark": 0.15}, {"mark": 0.25}, {"gmax": 1.5}, {"gmax": 2.5}, {"nsect": 16}, {"nsect": 32}, {"per_mm2": 32.0}, {"per_mm2": 128.0}, {"attach": 1.5}, {"attach": 2.5}, {"frac_mark": 0.65}, {"frac_mark": 0.85}):
        qq = IC.eyelid_probe(L, f, EIN[sd], **kw); steps.append((kw, qq["status"], qq["overhang_median_mm"], qq["frac_sectors_ok"]))
    ok(f"E1 Tripo eyelid {sd} PASSES", r["status"] == "PASS",
       f"cap {int(reg.sum())} verts (eyes.py {e['cap_vertices']}); overhang median {r['overhang_median_mm']} mm, max {r['overhang_max_mm']}, "
       f"{r['frac_sectors_ok']*100:.0f} % sectors >= 0.2, inside {r['inside_share']*100:.2f} %; +-1 step: " +
       ", ".join(f"{list(k.items())[0][0]}={list(k.items())[0][1]}:{s} {om}" for k, s, om, _ in steps))
    OUT[f"E1_{sd}"] = {k: r[k] for k in r if k != "sector_overhang_mm"} | {"sector_overhang_mm": r["sector_overhang_mm"], "steps": [(str(k), s, om, fr_) for k, s, om, fr_ in steps]}


# ---------------- E2 synthetic eyes (globe R 10 mm at the origin, eye axis +z)
def revolve(prof, n=180, ref=None):
    """profile [(rho, z)] revolved about z; triangles oriented so their normal . ref(centroid) > 0"""
    prof = np.asarray(prof, float); th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    V = np.array([[p[0] * np.cos(t), p[0] * np.sin(t), p[1]] for p in prof for t in th]); F = []
    for i in range(len(prof) - 1):
        for j in range(n):
            a, b, c2, d2 = i * n + j, i * n + (j + 1) % n, (i + 1) * n + j, (i + 1) * n + (j + 1) % n
            F += [[a, b, d2], [a, d2, c2]]
    F = np.array(F); Fn = IC.face_normals(V, F); C = V[F].mean(1)
    if ref is not None:
        flip = np.einsum("ij,ij->i", Fn, ref(C)) < 0; F[flip] = F[flip][:, ::-1]
    return V, F


def arc(R, t0_, t1_, k=120):
    t = np.linspace(np.radians(t0_), np.radians(t1_), k); return np.c_[R * np.sin(t), R * np.cos(t)]


def merge(*parts):
    V, F, o = [], [], 0
    for pv, pf in parts:
        V.append(pv); F.append(pf + o); o += len(pv)
    return np.vstack(V), np.vstack(F)


Rg, TE = 10.0, 35.0                                                   # globe radius; lid edge at polar angle 35 deg
gv, gf_ = revolve(arc(Rg, 0, 120, 240), ref=lambda C: C)              # globe, outward normals
radial_in = lambda C: -C                                             # noqa: E731


def synth(kind, w=0.0, gap=0.15, thick=1.0):
    parts = [(gv, gf_)]
    tw = TE + np.degrees(w / Rg)
    if kind == "wrap":                                                # underside on the globe from TE to TE+w, then lifts 3 mm away
        under = np.r_[arc(Rg + gap, TE, tw, 60), arc(Rg + 3.5, tw + 0.5, 120, 60)]
        parts.append(revolve(under, ref=radial_in))
        parts.append(revolve(np.r_[arc(Rg + gap + thick, TE, tw, 60), arc(Rg + 4.5, tw + 0.5, 120, 60)], ref=lambda C: C))
        rim = np.array([[(Rg + gap) * np.sin(np.radians(TE)), (Rg + gap) * np.cos(np.radians(TE))], [(Rg + gap + thick) * np.sin(np.radians(TE)), (Rg + gap + thick) * np.cos(np.radians(TE))]])
        parts.append(revolve(rim, ref=lambda C: np.c_[C[:, 0], C[:, 1], np.zeros(len(C))] * -1 + np.c_[np.zeros((len(C), 2)), np.ones(len(C)) * 5]))
    elif kind == "butt":                                              # socket wall 3 mm off the globe right at the edge
        parts.append(revolve(arc(Rg + 3.0, TE, 120, 120), ref=radial_in))
        parts.append(revolve(arc(Rg + 4.0, TE, 120, 120), ref=lambda C: C))
    elif kind == "through":                                           # closed skin plane z = Rg cos(TE): globe pokes out of it
        zc = Rg * np.cos(np.radians(TE)); g = np.linspace(-20, 20, 81); X, Y = np.meshgrid(g, g)
        pv = np.c_[X.ravel(), Y.ravel(), np.full(X.size, zc)]; pf = []
        for i in range(80):
            for j in range(80):
                a = i * 81 + j; pf += [[a, a + 1, a + 82], [a, a + 82, a + 81]]
        pf = np.array(pf); n = IC.face_normals(pv, pf); fl = n[:, 2] < 0; pf[fl] = pf[fl][:, ::-1]
        hole = np.linalg.norm(pv[pf].mean(1)[:, :2], axis=1) < Rg * np.sin(np.radians(TE)) - 0.3   # the visible cap pokes through
        parts.append((pv, pf[~hole]))
    V, F = merge(*parts); return V, F, np.arange(len(gf_))


for kind, w, want in (("wrap", 0.1, "FAIL"), ("wrap", 0.3, "PASS"), ("wrap", 0.5, "PASS"), ("wrap", 1.0, "PASS"), ("butt", 0.0, "FAIL"), ("through", 0.0, "FAIL")):
    V, F, gi_ = synth(kind, w); r = IC.eyelid_probe(V, F, {"globe_faces": gi_.tolist(), "centre_mm": [0, 0, Rg], "outward": [0, 0, 1.0], "axis": [0, 0, 1.0], "radius_mm": 30})
    expect = (w + np.radians(0.5 * (2.0 - 0.15) / 3.35) * Rg) * (1 + (w / 2 / Rg) / np.tan(np.radians(TE)))   # band + the lift wall's first 0.28 deg
    good = r["status"] == want and (kind != "wrap" or abs(r["overhang_median_mm"] - expect) <= 0.05) and (kind != "through" or r["inside_share"] >= 0.02)
    ok(f"E2 synthetic {kind} w={w}", good, f"{r['status']} (want {want}); expect {expect:.3f}, overhang median {r.get('overhang_median_mm')} mm, inside {r.get('inside_share')}, {r['why']}")

# ---------------- R1 registry
IC.REGISTRY.clear(); rows = IC.run(L, f)
ok("R1a every inventory entry is mapped", all(r.get("parts") is not None for r in rows), f"{len(rows)} entries")
ok("R1b empty registry -> all FAIL 'no registered builder'", all(r["status"] == "FAIL" and all(s["why"] == "no registered builder" for s in r["parts"]) for r in rows), f"{len(rows)} FAIL")
IC.register("nose_builder", ["nostril_cavity.R", "nostril_cavity.L", "nose_leather"], {f"nostril_cavity.{k}": x for k, x in NIN.items()})
IC.register("eye_builder", ["eyelid_wrap.R", "eyelid_wrap.L", "third_eyelid.R", "third_eyelid.L"], {f"eyelid_wrap.{k}": x for k, x in EIN.items()})
rows = IC.run(L, f); by = {r["entry"][:20]: r for r in rows}
nos = next(r for r in rows if r["entry"].startswith("NOSTRILS")); eye = next(r for r in rows if r["entry"].startswith("eyelids"))
leat = next(r for r in rows if r["entry"].startswith("nose leather"))
ok("R1c nostrils claimed on Tripo -> entry FAILS on the probe", nos["status"] == "FAIL" and all("depth" in s["why"] for s in nos["parts"]), "; ".join(f"{s['part']} {s.get('value_mm')}" for s in nos["parts"]))
ok("R1d stub part claimed -> FAIL 'declared stub'", leat["status"] == "FAIL" and "stub" in leat["parts"][0]["why"], leat["parts"][0]["why"])
lid = [s for s in eye["parts"] if s["part"].startswith("eyelid")]
ok("R1e eye entry FAILS on the third-eyelid stub while the lid wrap passes", eye["status"] == "FAIL" and all(s["status"] == "PASS" for s in lid), ", ".join(f"{s['part']} {s['status']}" for s in eye["parts"]))

print(f"\n{'ALL PROOFS PASS' if all(ALL) else 'A PROOF FAILED'} ({sum(ALL)}/{len(ALL)}) in {time.time()-t0:.0f} s")
if len(sys.argv) > 1:
    json.dump(OUT, open(sys.argv[1], "w"), indent=1, default=str)
