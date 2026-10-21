"""A10 proofs of skin_checks.py on planted failures sized to what each check reads.

usage (run from tripo_rebuild so the shared libraries import):  python ../engine/checks/skin_checks_prove.py [c2] [c3] [c8]

Test skins come from tripo_rebuild/layers/base_relief.npz (base form v, outward normals n, relief: v + relief*n = Tripo
to 0.006 mm). The envelope is tripo_welded.npz (face-referenced vertices only).
C2  clean = the base form itself (a constant-depth NORMAL inset is reported separately: it is not a clean skin).
    planted: a pinched toe cleft (one sheet pushed through the facing sheet), one removed face, a duplicated shell.
C3  clean = (v + relief*n) - D*n, depth_fn = D. planted: +0.3 mm bump, -0.3 mm dent, +0.8 mm bump (over tolerance),
    and a wrong-region depth (the head built at the core's depth).
C8  tips = (v + relief*n) + uniform scatter inside +-0.4 mm along n; planted: fur 30 % too long in one region
    (and 30 % too short in another).
C3/C8 run on the FRONT of the cat (y < -115 mm: head, ears, fore legs, chest) to keep memory low while other agents
run; the envelope is cropped 10 mm wider than the skin, more than the 1-6 mm the points sit from it.
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import time

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
TRIPO = os.path.normpath(os.path.join(HERE, "..", "..", "tripo_rebuild"))
sys.path.insert(0, HERE); sys.path.insert(0, TRIPO)
import skin_checks as sc  # noqa: E402
from twosided import MeshDist, area_samples  # noqa: E402

OUT = {}


class _PMC(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD)] + [(k, ctypes.c_size_t) for k in (
        "PeakWorkingSetSize", "WorkingSetSize", "QPPP", "QPP", "QPNP", "QNP", "PagefileUsage", "PeakPagefileUsage")]


def free_gb():
    import subprocess
    o = subprocess.run(["powershell", "-NoProfile", "-c", "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"], capture_output=True, text=True).stdout
    return float(o.strip() or 0) / 1e6


def peak_gb():
    k = ctypes.WinDLL("kernel32"); p = ctypes.WinDLL("psapi")
    k.GetCurrentProcess.restype = wt.HANDLE
    p.GetProcessMemoryInfo.argtypes = [wt.HANDLE, ctypes.POINTER(_PMC), wt.DWORD]
    m = _PMC(); m.cb = ctypes.sizeof(m); p.GetProcessMemoryInfo(k.GetCurrentProcess(), ctypes.byref(m), m.cb)
    return m.PeakWorkingSetSize / 1e9


def load_base():
    D = np.load(os.path.join(TRIPO, "layers", "base_relief.npz"))
    return D["v"], D["f"], D["n"], D["relief"].astype(np.float64)


def show(tag, r, keys):
    print(f"  {tag:34s} " + "  ".join(f"{k}={r[k]}" for k in keys) + f"  -> {'PASS' if r['pass'] else 'FAIL'}", flush=True)


# ===================================================================== C2
def find_cleft(v, n, every=3, tmax=0.006):
    """the NARROWEST cleft: march out along each vertex normal (0.3..6 mm, 0.2 mm steps) until a vertex of a FACING
    sheet (normal < -0.7 against ours) is within 0.3 mm. The blurred base form has no open toe cleft (sigma 1 mm fills
    them: no facing sheet within 6 mm below z 30 mm), so the narrowest cleft on the whole skin is used.
    Returns (vertex index, partner index, gap m)."""
    tr = cKDTree(v); sel = np.arange(0, len(v), every); P, N = v[sel], n[sel]
    gap = np.full(len(sel), np.inf); part = np.full(len(sel), -1)
    for t in np.arange(0.0003, tmax, 0.0002):
        d, j = tr.query(P + t * N, k=1); ok = (d < 0.0003) & ((n[j] * N).sum(1) < -0.7) & np.isinf(gap)
        gap[ok] = t; part[ok] = j[ok]
    k = int(np.argmin(gap)); i, j = int(sel[k]), int(part[k])
    return i, j, float(np.linalg.norm(v[j] - v[i]))


def ray_gap(v, f, n, i, j, L=0.006):
    """exact distance along n[i] from v[i] to the facing sheet (faces within 4 mm of v[j] facing back at us)"""
    c = v[f].mean(1); fk = np.flatnonzero(np.linalg.norm(c - v[j], axis=1) < 0.004)
    T = v[f[fk]]; fnn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); fk = fk[(fnn @ n[i]) < 0]; T = v[f[fk]]
    P0 = np.repeat(v[i][None], len(fk), 0); d = np.repeat((L * n[i])[None], len(fk), 0)
    e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]; h = np.cross(d, e2); a = (e1 * h).sum(1); a = np.where(np.abs(a) < 1e-30, 1e-30, a)
    s_ = P0 - T[:, 0]; u = (s_ * h).sum(1) / a; q = np.cross(s_, e1); w = (d * q).sum(1) / a; t = (e2 * q).sum(1) / a
    ok = (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 0) & (t <= 1)
    return float(t[ok].min() * L)


def prove_c2():
    print("C2 skin_integrity", flush=True); t0 = time.time()
    v, f, n, _ = load_base(); res = {}
    r = sc.skin_integrity(v, f); res["clean_base_form"] = r
    show("clean base form", r, ["open_edges", "nonmanifold_edges", "pinched_vertices", "shells", "selfint_pairs"])
    # --- planted 1: pinched cleft. The narrowest facing gap between the toes; the near sheet is pushed OUT along its
    # normal by gap + 0.3 mm (Gaussian, sigma 1.5 mm, same sheet only) so it crosses the facing sheet.
    i, j, gap_v = find_cleft(v, n)
    gap = ray_gap(v, f, n, i, j)                                   # the TRUE gap along the normal (the vertex pair is only
    print(f"  vertex-pair gap {gap_v * 1000:.3f} mm, exact ray gap {gap * 1000:.3f} mm", flush=True)   # 0.3 mm-accurate)
    print(f"  cleft found: {np.round(v[i] * 1000, 2)} -> {np.round(v[j] * 1000, 2)}, gap {gap * 1000:.3f} mm", flush=True)
    rr = np.linalg.norm(v - v[i], axis=1); same = (n @ n[i]) > 0.5
    h = gap + 0.0003; P1 = v + (h * np.exp(-(rr / 0.0015) ** 2) * same)[:, None] * n
    rows = []
    for cell in (None, 0.0004, 0.0015):                                                    # A14: grid cell +-1 step
        r = sc.skin_integrity(P1, f, cell=cell); rows.append((r["selfint_info"]["cell_mm"], r["selfint_pairs"]))
        if cell is None:
            res["pinched_cleft"] = dict(r, site_mm=np.round(v[i] * 1000, 2).tolist(), gap_mm=gap * 1000)
            show("pinched cleft (gap+0.3 mm push)", r, ["open_edges", "pinched_vertices", "shells", "selfint_pairs"])
            near = [s for s in r["selfint_sites"] if np.linalg.norm(np.array(s[0]) - v[i] * 1000) < 4.0]
            print(f"    sites {r['selfint_sites'][:3]} (within 4 mm of the plant: {len(near)})", flush=True)
            res["pinched_cleft"]["sites_at_plant"] = len(near)
    print(f"    A14 cell size -> pairs: {rows}", flush=True); res["pinched_cleft_cell_steps"] = rows
    OUT["c2"] = res
    return v, f, n, i, gap, res


def prove_c2_rest(v=None, f=None, n=None, i=None, gap=None, res=None):
    if v is None:
        v, f, n, _ = load_base(); i, j, _ = find_cleft(v, n); gap = ray_gap(v, f, n, i, j); res = {}
    t0 = time.time(); rr = np.linalg.norm(v - v[i], axis=1); same = (n @ n[i]) > 0.5
    # a just-touching control: pushed to gap - 0.1 mm (sheets stay 0.1 mm apart) must NOT report an intersection
    P0 = v + ((gap - 0.0001) * np.exp(-(rr / 0.0015) ** 2) * same)[:, None] * n
    r = sc.skin_integrity(P0, f); res["cleft_control_gap_0p1"] = r
    show("control: pushed to 0.1 mm short", r, ["selfint_pairs"])
    # --- planted 2: one face removed (a hole of one triangle): the face nearest the top of the head above the cleft
    top = v[int(np.argmin(np.linalg.norm(v - (v[i] + np.array([0, 0, 0.05])), axis=1)))]
    k = int(np.argmin(np.linalg.norm(v[f].mean(1) - top, axis=1)))
    r = sc.skin_integrity(v, np.delete(f, k, 0)); res["one_face_removed"] = r
    show("one face removed", r, ["open_edges", "nonmanifold_edges", "shells", "selfint_pairs"])
    # --- planted 3a: a duplicated shell, coincident (the classic doubled surface); 3b: the same copy pushed 0.5 mm in.
    # The full 5.7 M-face run needs ~2.5 GB; it runs only with >= 4 GB free, else topology only + the coincident
    # overlap test on the duplicated faces within 3 mm of a cheek point (the same 0.5 mm triangles).
    v2 = np.r_[v, v]; f2 = np.r_[f, f + len(v)]
    full = free_gb() >= 4.0
    r = sc.skin_integrity(v2, f2, check_self_intersection=full); res["duplicated_shell_coincident"] = dict(r, full_selfint=full)
    show("duplicated shell (coincident)", r, ["open_edges", "nonmanifold_edges", "shells"] + (["selfint_pairs"] if full else []))
    if not full:
        c = top; fk = np.flatnonzero(np.linalg.norm(v[f].mean(1) - c, axis=1) < 0.003)
        a = np.r_[fk, fk + len(f)]; pairs, _ = sc.self_intersections(v2, f2[a])
        res["duplicated_patch_selfint_pairs"] = int(len(pairs)); res["duplicated_patch_faces"] = int(len(fk))
        print(f"    coincident overlap on the {len(fk)} duplicated faces near {np.round(c * 1000, 1)}: {len(pairs)} pairs (each face meets its copy: expect >= {len(fk)})", flush=True)
    r = sc.skin_integrity(np.r_[v, v - 0.0005 * n], f2, check_self_intersection=False); res["duplicated_shell_inset_0p5"] = r
    show("duplicated shell (0.5 mm inside)", r, ["open_edges", "shells"])
    # --- the brief's constant-depth normal inset, as a finding (not a proof): does it stay a valid skin?
    for D in (0.0005, 0.001):
        r = sc.skin_integrity(v - D * n, f); res[f"normal_inset_{D * 1000:.1f}mm"] = dict(r, selfint_sites=r["selfint_sites"][:12])
        show(f"FINDING normal inset {D * 1000:.1f} mm", r, ["shells", "selfint_pairs"])
        print(f"    biggest sites {r['selfint_sites'][:6]}", flush=True)
    print(f"  C2 rest {time.time() - t0:.0f} s, peak {peak_gb():.2f} GB", flush=True)
    OUT["c2rest"] = res


# ===================================================================== C3 / C8 shared set-up
def front_set(y_cut=-0.115, margin=0.010):
    v, f, n, rel = load_base()
    fy = v[f][:, :, 1].max(1); fk = fy < y_cut; sf = f[fk]; used = np.unique(sf)
    remap = np.full(len(v), -1, np.int64); remap[used] = np.arange(len(used))
    S = dict(v=v[used], f=remap[sf], n=n[used], rel=rel[used])
    T = np.load(os.path.join(TRIPO, "tripo_welded.npz")); tv, tf = T["v"], T["f"]
    ek = tv[tf][:, :, 1].min(1) < y_cut + margin; ef = tf[ek]; eu = np.unique(ef)
    rm = np.full(len(tv), -1, np.int64); rm[eu] = np.arange(len(eu))
    E = dict(v=tv[eu], f=rm[ef])
    return S, E


def region_fn():
    import partition as pt
    return pt.owner, pt.PART_NAMES


def prove_c3(S, E, md):
    print("C3 skin_vs_envelope", flush=True); t0 = time.time(); res = {}
    own, names = region_fn(); D = 0.001
    surf = S["v"] + S["rel"][:, None] * S["n"]
    skin = surf - D * S["n"]
    const = lambda P: np.full(len(P), D)  # noqa: E731
    r0, _ = sc.skin_vs_envelope(surf, S["f"], E["v"], E["f"], lambda P: np.zeros(len(P)), own, names, env_md=md)
    res["clean_depth0"] = r0; summarize("clean depth 0 (relief surface ON the envelope, furless case)", r0)
    r, (P, err, lab) = sc.skin_vs_envelope(skin, S["f"], E["v"], E["f"], const, own, names, env_md=md)
    res["clean_1mm"] = dict(r, watch_sites=r["watch_sites"][:30]); summarize("FINDING naive normal inset 1 mm", r)
    # planted sites: clean |err| < 0.05 mm within 5 mm, one in each of head / core / a fore leg
    tr = cKDTree(P); bad = np.abs(err) > 0.00005
    btree = cKDTree(P[bad]) if bad.any() else None
    sites = []
    for want in ("head", "core", "leg_fore.L"):
        cand = np.flatnonzero(lab == names.index(want))[::97]
        for c in cand:
            if btree is None or btree.query(P[c])[0] > 0.005:
                sites.append((want, P[c])); break
    print(f"  plant sites: {[(w, np.round(p * 1000, 1).tolist()) for w, p in sites]}", flush=True)
    sv = cKDTree(S["v"])
    def plant(h_by_site):
        X = skin.copy()
        for (w, p), h in zip(sites, h_by_site):
            k = sv.query(p)[1]; nn = S["n"][k]; rr = np.linalg.norm(S["v"] - S["v"][k], axis=1); same = (S["n"] @ nn) > 0.5
            X += (h * np.exp(-(rr / 0.0012) ** 2) * same)[:, None] * S["n"]
        return X
    for per in (4.0, 8.0, 16.0):                                                              # A14: sampling +-1 step
        X = plant([+0.0003, -0.0003, +0.0008])
        r, (Pp, ep, lp) = sc.skin_vs_envelope(X, S["f"], E["v"], E["f"], const, own, names, env_md=md, per_mm2=per)
        found = []
        for (w, p), h in zip(sites, (+0.3, -0.3, +0.8)):
            near = np.linalg.norm(Pp - p, axis=1) < 0.004
            e = ep[near] * 1000; pk = e[np.argmax(np.abs(e))] if near.any() else float("nan")
            a02 = float((np.abs(ep[near]) > 0.0002).sum() / per); a05 = float((np.abs(ep[near]) > 0.0005).sum() / per)
            listed = any(np.linalg.norm(np.array(s["centre_mm"]) - p * 1000) < 3.0 for s in r["watch_sites"])
            found.append(dict(site=w, planted_mm=h, peak_err_mm=round(float(pk), 3), area_over_0p2_mm2=a02, area_over_tol_mm2=a05,
                              watch_listed=bool(listed), fails_region_on_its_own=bool(a05 > sc.MAX_AREA_C3)))
        res[f"planted_per{per:g}"] = dict(sites=found, regions={k: (v_["passed"], round(v_["area_over_tol_mm2"], 2)) for k, v_ in r["regions"].items()})
        print(f"  planted, {per:g}/mm2:", flush=True)
        for row in found:
            print(f"    {row}", flush=True)
    # wrong-region depth: the head built at 2 mm (the core's depth) while depth_fn wants 1 mm there
    lv = own(S["v"]); hd = lv == names.index("head")
    for step, Dw in (("-1", 0.0015), ("0", 0.002), ("+1", 0.0025)):
        X = surf - np.where(hd, Dw, D)[:, None] * S["n"]
        r, _ = sc.skin_vs_envelope(X, S["f"], E["v"], E["f"], const, own, names, env_md=md)
        r["watch_sites"] = r["watch_sites"][:10]
        res[f"wrong_region_head_{Dw * 1000:.1f}mm"] = {k: (v_["passed"], round(v_["frac_over_tol"], 3), round(v_["median_err_mm"], 3)) for k, v_ in r["regions"].items()}
        print(f"  wrong-region depth: head built at {Dw * 1000:.1f} mm, wanted 1.0 -> "
              + ", ".join(f"{k} {'P' if v_['passed'] else 'F'} {v_['frac_over_tol']:.3f} med {v_['median_err_mm']:+.2f}" for k, v_ in r["regions"].items()), flush=True)
    print(f"  C3 proofs {time.time() - t0:.0f} s, peak {peak_gb():.2f} GB", flush=True)
    OUT["c3"] = res


def summarize(tag, r):
    print(f"  {tag}: passed={r['passed']}", flush=True)
    for k, v_ in r["regions"].items():
        print(f"    {k:11s} area {v_['area_mm2']:9.0f} mm2  over tol {v_['area_over_tol_mm2']:8.1f} mm2 ({100 * v_['frac_over_tol']:.2f} %)  "
              f"over 0.2 {v_['area_over_watch_mm2']:8.1f}  med {v_['median_err_mm']:+.3f}  p1..p99 {v_['p1_mm']:+.3f}..{v_['p99_mm']:+.3f}  "
              f"{'PASS' if v_['passed'] else 'FAIL'}", flush=True)
    print(f"    watch sites (top 6): {r['watch_sites'][:6]}", flush=True)


def prove_c8(S, E, md):
    print("C8 fur_tips_vs_envelope", flush=True); t0 = time.time(); res = {}
    own, names = region_fn()
    Dmap = {"head": 0.003, "core": 0.006, "ear_R": 0.0015, "ear_L": 0.0015, "tail": 0.008}       # test coat depths (m)
    k = np.arange(0, len(S["v"]), 5); root_s = S["v"][k] + S["rel"][k, None] * S["n"][k]           # envelope points
    lab = own(root_s); Dk = np.array([Dmap.get(names[l], 0.004) for l in lab])
    rng = np.random.default_rng(3); scat = rng.uniform(-0.0004, 0.0004, len(k))
    skin = root_s - Dk[:, None] * S["n"][k]                                                         # roots on the skin
    def tips(scale_by_region):
        L = Dk * np.array([scale_by_region.get(names[l], 1.0) for l in lab]) + scat
        return skin + L[:, None] * S["n"][k]                                                        # straight strands
    for spread in (0.00075, 0.001, 0.00125):                                                        # A14: spread +-1 step
        sp = lambda P: np.full(len(P), spread)  # noqa: E731
        for tag, sc_ in (("clean", {}), ("core 30% long", {"core": 1.3}), ("head 30% long", {"head": 1.3}),
                         ("leg_fore.L 30% short", {"leg_fore.L": 0.7})):
            r, sd = sc.fur_tips_vs_envelope(tips(sc_), E["v"], E["f"], sp, own, names, env_md=md)
            res[f"{tag}_spread{spread * 1000:.2f}"] = r
            print(f"  spread {spread * 1000:.2f} mm, {tag:20s}: " + ", ".join(
                f"{kk} {'P' if vv['passed'] else 'F'} med {vv['median_mm']:+.2f} out {vv['frac_out']:.2f} short {vv['frac_short']:.2f}"
                for kk, vv in r["regions"].items()), flush=True)
    # A14 on the pass fraction: core 30 % long at spread 1 mm against max_frac 5 / 10 / 20 %
    for mf in (0.05, 0.10, 0.20):
        r, _ = sc.fur_tips_vs_envelope(tips({"core": 1.3}), E["v"], E["f"], lambda P: np.full(len(P), 0.001), own, names, max_frac=mf, env_md=md)
        rc, _ = sc.fur_tips_vs_envelope(tips({}), E["v"], E["f"], lambda P: np.full(len(P), 0.001), own, names, max_frac=mf, env_md=md)
        res[f"maxfrac_{mf}"] = dict(planted=r["passed"], clean=rc["passed"])
        print(f"  max_frac {mf:.2f}: clean passed={rc['passed']}, core 30% long passed={r['passed']}", flush=True)
    print(f"  C8 proofs {time.time() - t0:.0f} s, peak {peak_gb():.2f} GB", flush=True)
    OUT["c8"] = res


# ===================================================================== C2 cross-check (no false positives / misses)
def moller_scalar(TA, TB, shared):
    """independent tri-tri test (Moller 1997 interval overlap on the planes' line), one pair at a time, plain Python
    floats. Coplanar pairs return None. Touching only at a point (e.g. a shared vertex) is not an intersection."""
    def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
    def crs(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    def dt(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    A = [tuple(map(float, x)) for x in TA]; B = [tuple(map(float, x)) for x in TB]
    nA = crs(sub(A[1], A[0]), sub(A[2], A[0])); nB = crs(sub(B[1], B[0]), sub(B[2], B[0]))
    ln = lambda x: dt(x, x) ** 0.5  # noqa: E731
    nA = tuple(c / ln(nA) for c in nA); nB = tuple(c / ln(nB) for c in nB)
    dB = [0.0 if s else dt(sub(b, A[0]), nA) for b, s in zip(B, shared[1])]
    dA = [0.0 if s else dt(sub(a, B[0]), nB) for a, s in zip(A, shared[0])]
    e = 1e-13
    if all(abs(x) <= e for x in dB):
        return None
    if all(x >= -e for x in dB) or all(x <= e for x in dB) or all(x >= -e for x in dA) or all(x <= e for x in dA):
        return False
    L = crs(nA, nB)
    def interval(T, d):
        ts = []
        for i in range(3):
            j = (i + 1) % 3
            if abs(d[i]) <= e:
                ts.append(dt(T[i], L))
            if (d[i] > e and d[j] < -e) or (d[i] < -e and d[j] > e):
                w = d[i] / (d[i] - d[j]); P = tuple(T[i][k] + (T[j][k] - T[i][k]) * w for k in range(3)); ts.append(dt(P, L))
        return min(ts), max(ts)
    a0, a1 = interval(A, dA); b0, b1 = interval(B, dB)
    return min(a1, b1) - max(a0, b0) > 1e-13 * ln(L)


def prove_xc(depth=0.001, n_each=3000):
    """(1) the vectorised exact test agrees with the independent scalar Moller test on hit AND non-hit pairs;
    (2) the grid finds every intersecting pair a brute-force all-pairs search finds in 3 boxes."""
    print("C2 cross-check", flush=True); t0 = time.time(); res = {}
    v, f, n, _ = load_base(); X = v - depth * n; f = f.astype(np.int64)
    T = X[f]; fn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); fn /= np.linalg.norm(fn, axis=1)[:, None]
    pairs, info = sc.self_intersections(X, f)
    rng = np.random.default_rng(5); hits = pairs[rng.choice(len(pairs), min(n_each, len(pairs)), replace=False)]
    cen = T.mean(1); tr = cKDTree(cen); probe = rng.choice(len(f), n_each, replace=False); near = []
    for a in probe:                                                    # near pairs that are NOT edge-neighbours
        js = tr.query_ball_point(cen[a], 0.0008)
        for b in js:
            if b != a and len(set(f[a]) & set(f[b])) <= 1:
                near.append((a, b)); break
    cand = np.r_[hits, np.array(near)]
    vec = sc._tri_tri(X, f, cand[:, 0], cand[:, 1], fn)
    agree = dis = cop = 0
    for (a, b), h in zip(cand, vec):
        sh = (np.isin(f[a], f[b]), np.isin(f[b], f[a])); m = moller_scalar(T[a], T[b], sh)
        if m is None:
            cop += 1; continue
        agree += int(m == bool(h)); dis += int(m != bool(h))
    res["exact_test"] = dict(pairs=len(cand), reported_hits_in_sample=int(len(hits)), agree=agree, disagree=dis, coplanar_skipped=cop,
                             vec_hits=int(vec.sum()))
    print(f"  exact test vs scalar Moller: {agree} agree, {dis} disagree, {cop} coplanar (of {len(cand)}; {int(vec.sum())} vec hits)", flush=True)
    # grid completeness: brute force all non-edge-neighbour pairs among faces whose centroid is in a 4 mm box
    rows = []                                                          # boxes centred on 3 random intersecting faces
    for c in (cen[pairs[rng.choice(len(pairs), 3, replace=False), 0]] * 1000).round(2).tolist():
        inb = np.flatnonzero(np.all(np.abs(cen - np.array(c) / 1000) < 0.002, axis=1))
        ia, ib = np.triu_indices(len(inb), 1); a, b = inb[ia], inb[ib]
        sh = (f[a][:, :, None] == f[b][:, None, :]).sum((1, 2)); a, b = a[sh <= 1], b[sh <= 1]
        bf = sc._tri_tri(X, f, a, b, fn); brute = set(map(tuple, np.sort(np.c_[a[bf], b[bf]], 1).tolist()))
        grid = set(map(tuple, pairs[np.isin(pairs[:, 0], inb) & np.isin(pairs[:, 1], inb)].tolist()))
        rows.append(dict(box_mm=c, faces=int(len(inb)), brute=len(brute), grid=len(grid), missed=len(brute - grid), extra=len(grid - brute)))
        print(f"  grid vs brute force at {c}: {rows[-1]}", flush=True)
    res["grid_completeness"] = rows
    print(f"  cross-check {time.time() - t0:.0f} s, peak {peak_gb():.2f} GB", flush=True)
    OUT["xc"] = res


if __name__ == "__main__":
    want = set(sys.argv[1:]) or {"c2", "xc", "c3", "c8"}  # c2rest = the C2 plants after the cleft, alone
    os.chdir(TRIPO); t = time.time()
    if "c2" in want:
        prove_c2_rest(*prove_c2())
    elif "c2cleft" in want:
        a_ = prove_c2(); v_, f_, n_, i_, g_, _ = a_; rr_ = np.linalg.norm(v_ - v_[i_], axis=1); sm_ = (n_ @ n_[i_]) > 0.5
        for back in (0.0001, 0.0002):                              # controls: stop 0.1 / 0.2 mm short of the facing sheet
            r_ = sc.skin_integrity(v_ + ((g_ - back) * np.exp(-(rr_ / 0.0015) ** 2) * sm_)[:, None] * n_, f_)
            OUT.setdefault("c2_controls", {})[f"short_{back * 1000:.1f}mm"] = r_
            show(f"control: pushed to {back * 1000:.1f} mm short", r_, ["selfint_pairs"]); print("    sites", r_["selfint_sites"][:3])
    elif "c2rest" in want:
        prove_c2_rest()
    if "xc" in want:
        prove_xc()
    if want & {"c3", "c8"}:
        S, E = front_set(); md = MeshDist(E["v"], E["f"])
        print(f"front set: skin {len(S['f'])} faces, envelope {len(E['f'])} faces; MeshDist built, peak {peak_gb():.2f} GB", flush=True)
        if "c3" in want:
            prove_c3(S, E, md)
        if "c8" in want:
            prove_c8(S, E, md)
    out = os.path.join(os.environ.get("TEMP", "."), "p2_checksA", f"prove_{'_'.join(sorted(want))}.json")
    json.dump(OUT, open(out, "w"), default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o), indent=1)
    print(f"done in {time.time() - t:.0f} s -> {out}; peak {peak_gb():.2f} GB")
