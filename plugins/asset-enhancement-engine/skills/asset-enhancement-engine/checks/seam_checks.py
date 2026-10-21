"""SEAM CHECK (cat v3 round 2, owner: skin construction). Measures STEP and KINK - and the two other ways a construction
seam showed on skin_v3 (a torn ledge, a tight coat blend) - across EVERY boundary the skin construction has, each against
LOCAL CONTROLS, the way cases/cat1/v3_skinfix/LOCATE.md measured them. Why: the fine-grid proof checked for cracks (holes)
only, so the person found steps and creases at the construction's boundaries (NOTES_v3 12:50: one-sided, A22).

THE BOUNDARIES (boundaries_*(): what the construction has; each a signed distance s(P) mm, a region, a kind)
  fine_box     the 6 faces of every fine box (build json)                       mesh seams: stitch, conforming layer
  region_edge  the 6 faces of every feature REGION box (world)                  an edit that does not fade at its face
  coat_region  the neck plane (partition.neck = 0), the neck-ruff plane (ne = -35 mm) and v3b's blend ends (-29, +5),
               the leg height bands (z = 25, 70 mm in each leg cylinder)        field seams: the coat-depth blend
  thickness    the tail, every 1 mm of centreline arc                            field seams: the local-thickness taper
  furless      the paw pad boundary: v3's z planes (free level + 0.3 mm + half the 1.5 mm ramp) or v3b's mask contour
THE MEASURES (each against its OWN controls; which ones run depends on the kind, KIND_MEASURES)
  strip  LOCATE's seam_profile: at seeds every 2 mm along the boundary, the surface strip crossing it (same sheet,
         +-0.75 mm along it) is fitted by a quadratic each side (0.3-2.5 mm away): STEP = value jump at s = 0 (mm), KINK =
         slope jump (deg), TORN = the share of seeds whose sheet does not continue to both sides (< 6 points on one).
         Controls: the same at s = +-2.5, +-5 mm.
  xgap   LOCATE's ear_step, slope-corrected: for points of the sections 0.4-0.8 mm above / below a plane, the in-plane
         distance to the other section MINUS what a smooth surface at that point's own slope gives ((g+dz) cot theta;
         theta from the vertex normal; points within 45 deg of parallel to the plane skipped). XGAP = the share over 1 mm.
         Controls: s = +-3, +-6, +-9 mm.
  bend   LOCATE's N1 profile: the MEASURED inset (skin -> Tripo, + inside) binned by s (0.5 mm), median per bin per
         sector, d'' by central differences over +-2 mm (the ring check's own rule) at |s| <= 5 mm. Control: the same
         d'' at 8 <= |s| <= 15 mm.
  scan   a family of parallel boundaries (the tail stations): strip at every station; control = the family median
         (LOCATE's tail scan: baseline kink p90 1.5-2.3 deg).
PASS MARKS (a measure FAILS a boundary when it exceeds BOTH its absolute mark and REL x its control)
  STEP_MM 0.10 (REL 3)   one contract voxel (A20: 0.10 mm): below it a step is at the build's resolution floor. LOCATE's
                         clean box faces read p90 0.007-0.049 mm; the planted step is 0.20 mm.
  KINK_DEG 5.0 (REL 3)   a 5 deg normal change across a line changes Lambert shading by up to sin 5 deg = 8.7 % of the light
                         along it: a drawn line in the person's grey viewport. The box faces the person did not flag read
                         p90 1.1-5.8 deg (LOCATE controls), the rings the person flagged 24-67 deg; the plant is 8 deg.
  TORN 0.10 (REL 3)      a tenth of the boundary's seeds without a continuing sheet is a tear along it, not a fold of
                         the part; LOCATE's ear controls (z 303-323) read <= 0.046, the E1 slot 0.27 / 0.36.
  XGAP 0.10 (REL 3)      a tenth of the section more than 1 mm (2 coarse voxels) from where its own slope puts it; ear
                         controls <= 0.039, the E1 slot 0.44-0.46.
  BEND 0.02 (REL 3)      the ring check's d'' budget (skin_smooth_checks.D2_MARK) on the measured inset, and 3 x the
                         control floor (Tripo's own relief puts that floor at ~0.03 /mm on the neck: the absolute budget
                         alone is not resolvable on a MEASURED inset).
usage: python seam_checks.py prove                      -> tripo_rebuild/layers/seam_checks_proof_v3b.json (A22 both sides)
       python seam_checks.py crop <crop.npz> <build.json>  the boundaries of a build on a crop (v, f, depth_mm in mm)
"""
import json
import os
import sys
import time

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
TR = os.path.join(ROOT, "tripo_rebuild")
FEL = os.path.join(ROOT, "engine", "packs", "felid")
for _p in (TR, FEL, os.path.join(FEL, "features")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
LAYERS = os.path.join(TR, "layers")

STEP_MM, STEP_REL = 0.10, 3.0
KINK_DEG, KINK_REL = 5.0, 3.0
TORN_MAX, TORN_REL = 0.10, 3.0
XGAP_MAX, XGAP_REL, XGAP_MM = 0.10, 3.0, 1.0
BEND_MAX, BEND_REL = 0.02, 3.0
STRIP_CTRL = (-5.0, -2.5, 2.5, 5.0)
GAP_CTRL = (-9.0, -6.0, -3.0, 3.0, 6.0, 9.0)
KIND_MEASURES = {"fine_box": ("strip", "xgap"), "region_edge": ("strip", "xgap"), "coat_region": ("strip", "bend"),
                 "furless": ("strip", "bend"), "plant": ("strip", "xgap")}


import os as _os_mg, sys as _sys_mg  # noqa: E402  (build A1: the engine's one closest point, normals, cotangent Laplacian)
_MG_DIR = _os_mg.path.normpath(_os_mg.path.join(_os_mg.path.dirname(_os_mg.path.abspath(__file__)), '../tools'))
if _MG_DIR not in _sys_mg.path:
    _sys_mg.path.append(_MG_DIR)
import mesh_geom as _MG  # noqa: E402


def vnormals(V, F):
    return _MG.vertex_normals(V, F, eps=1e-30, acc_dtype=np.float64)


# ------------------------------------------------------------------------------------------------ boundaries
class Boundary:
    """s(P) -> signed distance (mm), region(P) -> bool, kind; a PLANE when p0, n are given (xgap needs a plane)"""

    def __init__(self, name, kind, s=None, region=None, p0=None, n=None, sector=None, grad=None):
        self.name, self.kind, self.sector = name, kind, sector
        if n is not None:
            n = np.asarray(n, float); n = n / np.linalg.norm(n); p0 = np.asarray(p0, float); self.p0, self.n = p0, n
            self.s = lambda P: (np.asarray(P, float) - p0) @ n
            self.grad = lambda P: np.tile(n, (len(P), 1))
        else:
            self.p0 = self.n = None; self.s = s; self.grad = grad or (lambda P: _num_grad(s, P))
        self.region = region or (lambda P: np.ones(len(P), bool))

    def offset(self, c):
        b = Boundary(self.name + f"{c:+g}", self.kind, s=lambda P, s0=self.s: s0(P) - c, region=self.region, grad=self.grad,
                     sector=self.sector)
        if self.n is not None:
            b.p0, b.n = self.p0 + c * self.n, self.n
        return b


def _num_grad(s, P, h=0.05):
    P = np.asarray(P, float); g = np.zeros_like(P)
    for k in range(3):
        d = np.zeros(3); d[k] = h; g[:, k] = (s(P + d) - s(P - d)) / (2 * h)
    return g / np.maximum(np.linalg.norm(g, axis=1), 1e-12)[:, None]


# ------------------------------------------------------------------------------------------------ measures
def strip(V, F, N, B, spacing=2.0, R=2.5, band=0.3, half_w=0.75, vmask=None):
    """LOCATE seam_profile on boundary B (s = 0). Returns (rows [x, y, z, step, kink, groove_min, groove_max], n_seeds,
    n_torn): a seed is TORN when its sheet has < 6 points on one side (the surface does not continue across)"""
    s = B.s(V); sec = np.flatnonzero(np.abs(s) < 0.15)
    if len(sec):
        sec = sec[B.region(V[sec])]
    if vmask is not None and len(sec):
        sec = sec[vmask[sec]]
    if len(sec) < 5:
        return np.zeros((0, 7)), 0, 0
    key = np.floor(V[sec] / spacing).astype(np.int64); _, first = np.unique(key, axis=0, return_index=True); seeds = sec[first]
    near = np.flatnonzero(np.abs(s) < R + 0.5); tree = cKDTree(V[near]); G = B.grad(V[seeds]); rows = []; ns_ = 0; nt = 0
    for k, sd in enumerate(seeds):
        c = V[sd]; ns = N[sd]; nrm = G[k]
        t = np.cross(nrm, ns); tn = np.linalg.norm(t)
        if tn < 0.5:
            continue                                     # surface ~ parallel to the boundary: no crossing strip
        t /= tn; a_dir = np.cross(ns, t)
        if a_dir @ nrm < 0:
            a_dir = -a_dir
        idx = near[tree.query_ball_point(c, R + 0.5)]
        q = V[idx] - c; al = q @ t; h = q @ ns; a = q @ a_dir
        ok = (np.abs(al) < half_w) & (N[idx] @ ns > 0.6) & (np.abs(h) < 1.5)
        h, a = h[ok], a[ok]; ns_ += 1
        L = (a < -band) & (a > -R); Rr = (a > band) & (a < R)
        if L.sum() < 6 or Rr.sum() < 6:
            nt += 1; continue
        pl = np.polyfit(a[L], h[L], 2); pr = np.polyfit(a[Rr], h[Rr], 2)
        inb = np.abs(a) <= band
        gro = (h[inb] - 0.5 * (np.polyval(pl, a[inb]) + np.polyval(pr, a[inb]))) if inb.any() else np.zeros(1)
        rows.append([*c, pr[2] - pl[2], np.degrees(np.arctan(pr[1]) - np.arctan(pl[1])), float(gro.min()), float(gro.max())])
    return (np.array(rows) if rows else np.zeros((0, 7))), ns_, nt


def strip_stats(res):
    rows, ns_, nt = res
    out = dict(seeds=int(ns_), torn=int(nt), torn_share=round(nt / ns_, 4) if ns_ else None, n=int(len(rows)))
    if not len(rows):
        return out
    st, kk = np.abs(rows[:, 3]), np.abs(rows[:, 4])
    out.update(step_p50=round(float(np.median(st)), 4), step_p90=round(float(np.percentile(st, 90)), 4), step_max=round(float(st.max()), 4),
               kink_p50=round(float(np.median(kk)), 2), kink_p90=round(float(np.percentile(kk, 90)), 2), kink_max=round(float(kk.max()), 2),
               groove_min=round(float(rows[:, 5].min()), 3))
    return out


def xgap(V, N, B, g=0.8, dz=0.4, thr=XGAP_MM, vmask=None):
    """slope-corrected section gap across a PLANE: share of section points whose in-plane distance to the other section
    exceeds (g + dz) cot(theta) by more than thr mm"""
    if B.n is None:
        return dict(n=0)
    s = B.s(V); r = B.region(V)
    if vmask is not None:
        r = r & vmask
    n = B.n; A = r & (s > g / 2) & (s < g / 2 + dz); Bm = r & (s < -g / 2) & (s > -g / 2 - dz)
    if A.sum() < 20 or Bm.sum() < 20:
        return dict(n=0)
    e1 = np.cross(n, [1.0, 0, 0] if abs(n[0]) < 0.9 else [0, 1.0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
    P = np.c_[V @ e1, V @ e2]; ex = []
    for X, Y in ((A, Bm), (Bm, A)):
        d, _ = cKDTree(P[Y]).query(P[X]); c = np.abs(N[X] @ n); cot = c / np.sqrt(np.maximum(1 - c * c, 1e-6))
        ok = c < 0.7; ex.append((d - (g + dz) * cot)[ok])
    e = np.concatenate(ex)
    if len(e) < 20:
        return dict(n=0)
    return dict(n=int(len(e)), share_over=round(float((e > thr).mean()), 4), p90=round(float(np.percentile(e, 90)), 3),
                p99=round(float(np.percentile(e, 99)), 3))


def bend(V, inset, B, W=16.0, binw=0.5, h=2.0, near=5.0, ctl=(8.0, 15.0), min_n=15, vmask=None):
    """median measured inset vs s (bins binw) per sector; max |d''| (central differences over +-h) at |s| <= near and at
    ctl[0] <= |s| <= ctl[1] (the control floor)"""
    if inset is None:
        return dict(n=0)
    s = B.s(V); r = B.region(V) & (np.abs(s) < W + h)
    if vmask is not None:
        r &= vmask
    if r.sum() < 50:
        return dict(n=0)
    sec = B.sector(V[r]) if B.sector is not None else np.zeros(r.sum(), int)
    edges = np.arange(-W - h, W + h + 1e-9, binw); mid = 0.5 * (edges[1:] + edges[:-1]); k = int(round(h / binw))
    best, best_c, worst_sec = 0.0, 0.0, None
    for sc in np.unique(sec):
        m = sec == sc; ss = s[r][m]; dv = inset[r][m]; bi = np.digitize(ss, edges) - 1; med = np.full(len(mid), np.nan)
        for b in range(len(mid)):
            mm = bi == b
            if mm.sum() >= min_n:
                med[b] = np.median(dv[mm])
        d2 = np.full(len(mid), np.nan); d2[k:-k] = (med[2 * k:] - 2 * med[k:-k] + med[:-2 * k]) / h ** 2
        a = np.abs(d2); nr = np.abs(mid) <= near; ct = (np.abs(mid) >= ctl[0]) & (np.abs(mid) <= ctl[1])
        if np.isfinite(a[nr]).any() and np.nanmax(a[nr]) > best:
            best = float(np.nanmax(a[nr])); worst_sec = int(sc)
        if np.isfinite(a[ct]).any():
            best_c = max(best_c, float(np.nanmax(a[ct])))
    return dict(n=int(r.sum()), d2_near=round(best, 4), d2_ctl=round(best_c, 4), worst_sector=worst_sec)


# ------------------------------------------------------------------------------------------------ one boundary
def judge(B, V, F, N=None, inset=None, measures=None, vmask=None):
    N = vnormals(V, F) if N is None else N; measures = measures or KIND_MEASURES.get(B.kind, ("strip",))
    out = dict(boundary=B.name, kind=B.kind, measures=list(measures)); fails = []
    if "strip" in measures:
        st = strip_stats(strip(V, F, N, B, vmask=vmask))
        cs = [strip_stats(strip(V, F, N, B.offset(c), vmask=vmask)) for c in STRIP_CTRL]
        cf = [c for c in cs if c.get("n", 0) >= 5]
        cstep = max([c["step_p90"] for c in cf], default=None); ckink = max([c["kink_p90"] for c in cf], default=None)
        ctorn = max([c["torn_share"] for c in cs if c.get("seeds", 0) >= 10], default=None)
        o = dict(at=st, ctl_step_p90=cstep, ctl_kink_p90=ckink, ctl_torn_share=ctorn)
        if st.get("n", 0) >= 5:
            ms = max(STEP_MM, STEP_REL * (cstep or 0)); mk = max(KINK_DEG, KINK_REL * (ckink or 0)); o.update(step_mark=round(ms, 4), kink_mark=round(mk, 2))
            if st["step_p90"] > ms:
                fails.append("step")
            if st["kink_p90"] > mk:
                fails.append("kink")
        if st.get("seeds", 0) >= 10:
            mt = max(TORN_MAX, TORN_REL * (ctorn or 0)); o["torn_mark"] = round(mt, 4)
            if st["torn_share"] > mt:
                fails.append("torn")
        out["strip"] = o
    if "xgap" in measures and B.n is not None:
        g0 = xgap(V, N, B, vmask=vmask); gc = [xgap(V, N, B.offset(c), vmask=vmask) for c in GAP_CTRL]
        cg = max([g["share_over"] for g in gc if g.get("n", 0) >= 50], default=None); o = dict(at=g0, ctl_share=cg)
        if g0.get("n", 0) >= 50:
            mg = max(XGAP_MAX, XGAP_REL * (cg or 0)); o["mark"] = round(mg, 4)
            if g0["share_over"] > mg:
                fails.append("xgap")
        out["xgap"] = o
    if "bend" in measures and inset is not None:
        b = bend(V, inset, B, vmask=vmask)
        if b.get("n", 0):
            mb = max(BEND_MAX, BEND_REL * b["d2_ctl"]); b["mark"] = round(mb, 4)
            if b["d2_near"] > mb:
                fails.append("bend")
        out["bend"] = b
    out["fails"] = fails; out["status"] = "FAIL" if fails else "PASS"
    return out


def scan_family(V, F, N, boundaries, spacing=1.5):
    """strip at every member of a family (the tail stations); control = the family median of p90s"""
    rows = []
    for B in boundaries:
        st = strip_stats(strip(V, F, N, B, spacing=spacing))
        if st.get("n", 0) >= 4:
            rows.append((B.name, st))
    if not rows:
        return dict(n=0, status="NO DATA")
    k90 = np.array([r[1]["kink_p90"] for r in rows]); s90 = np.array([r[1]["step_p90"] for r in rows])
    kb, sb = float(np.median(k90)), float(np.median(s90)); mk = max(KINK_DEG, KINK_REL * kb); ms = max(STEP_MM, STEP_REL * sb)
    bad = [dict(station=nm, kink_p90=st["kink_p90"], step_p90=st["step_p90"]) for nm, st in rows if st["kink_p90"] > mk or st["step_p90"] > ms]
    return dict(n=len(rows), baseline_kink_p90=round(kb, 2), baseline_step_p90=round(sb, 4), kink_mark=round(mk, 2), step_mark=round(ms, 4),
                failing=bad, status="FAIL" if bad else "PASS", series=[[nm, st["kink_p90"], st["step_p90"]] for nm, st in rows])


# ------------------------------------------------------------------------------------------------ the construction's boundaries
def boundaries_box(b_lo_mm, b_hi_mm, name="fine_box", kind="fine_box", pad=0.0):
    """the 6 faces of a box (world mm), each limited to the face's own rectangle (+pad)"""
    lo, hi = np.asarray(b_lo_mm, float), np.asarray(b_hi_mm, float); out = []
    for ax in range(3):
        oth = [a for a in range(3) if a != ax]
        reg = (lambda P, oth=oth: np.all((P[:, oth] >= lo[oth] - pad) & (P[:, oth] <= hi[oth] + pad), axis=1))
        for side, val in (("lo", lo[ax]), ("hi", hi[ax])):
            n = np.zeros(3); n[ax] = 1.0; p0 = np.zeros(3); p0[ax] = val
            out.append(Boundary(f"{name}.{'xyz'[ax]}{side}={val:.2f}", kind, p0=p0, n=n, region=reg))
    return out


def boundaries_coat(cf_kind="v3b"):
    """coat-field region planes: the neck plane family (v3: ne = 0 and ruff -35; v3b: also the blend ends -29 / +5) with
    12 sectors round the neck; the leg bands z = 25 / 70 mm inside each leg cylinder (4 sectors)"""
    import partition as PT
    nw = PT.HR @ PT.NECK_N_L; p_notch = (PT.HC + PT.HR @ PT.NOTCH_L) * 1000
    c = np.array([17.1, -203.4, 223.3]); e1 = np.cross(nw, [1, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(nw, e1)

    def sector(P):
        q = P - c; return np.floor((np.degrees(np.arctan2(q @ e2, q @ e1)) + 180) / 30).astype(int)
    neck_reg = lambda P: (P[:, 2] > 120)                     # noqa: E731  (the neck, not the legs below it)
    offs = [0.0, -35.0] + ([-29.0, 5.0, -12.0] if cf_kind == "v3b" else [])
    out = [Boundary(f"coat.neck_plane{o:+g}", "coat_region", p0=p_notch + o * nw, n=nw, sector=sector, region=neck_reg) for o in offs]
    for k in PT.LEGS:
        for zb in (25.0, 70.0):
            def reg(P, k=k):
                cx, cy = PT.leg_centre(k, P[:, 2] / 1000); return np.hypot(P[:, 0] / 1000 - cx, P[:, 1] / 1000 - cy) < 0.030

            def sec(P, k=k):
                cx, cy = PT.leg_centre(k, P[:, 2] / 1000); return np.floor((np.arctan2(P[:, 1] / 1000 - cy, P[:, 0] / 1000 - cx) + np.pi) / (np.pi / 2)).astype(int)
            out.append(Boundary(f"coat.leg_{k}_z{zb:.0f}", "coat_region", p0=(0, 0, zb), n=(0, 0, 1), region=reg, sector=sec))
    return out


def boundaries_tail(step_mm=1.0, extra_mm=8.0, radius=16.0):
    """tail stations every step_mm of centreline arc, + extra_mm past its end along the end tangent. extra 8 mm: closer to
    the apex a station cuts the closing dome in a circle too small for the strip (+-0.75 mm along the boundary on a
    surface curved ~1/4 mm both ways reads 7-9 deg on a smooth ellipsoid); the apex is judged by tip_check instead"""
    C = np.load(os.path.join(LAYERS, "tail_centreline.npz")); Cc = C["C"].astype(float) * 1000; Tt = C["T"].astype(float)
    seg = np.linalg.norm(np.diff(Cc, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]; out = []
    for st in np.arange(0, s[-1] + extra_mm, step_mm):
        i = min(np.searchsorted(s, st), len(Cc) - 1); p = Cc[i]; t = Tt[i] / np.linalg.norm(Tt[i])
        if st > s[-1]:
            p = Cc[-1] + (st - s[-1]) * t
        out.append(Boundary(f"tail.s{st:.0f}", "thickness", p0=p, n=t, region=lambda Q, p=p: np.linalg.norm(Q - p, axis=1) < radius))
    return out


def boundaries_paws_v3():
    """v3's furless boundary: z = pad free level + 0.3 + 0.75 mm (the middle of coat_field's 1.5 mm z ramp) near the toe
    pads (within 2 mm of their outlines, xy)"""
    J = json.load(open(os.path.join(LAYERS, "paws.json")))["paws"]; out = []
    for paw in ("fore.R", "fore.L", "hind.R", "hind.L"):
        Zp = np.load(os.path.join(LAYERS, f"paws_pads_{paw}.npz")); toes = [k for k in Zp.files if k.startswith("core_toe")]
        tr = cKDTree(np.vstack([Zp[k][:, :2] for k in toes]) * 1000)
        zt = np.mean([J[paw]["pads"][k[5:]]["free_level_z_mm"] for k in toes]) + 0.3
        out.append(Boundary(f"furless.pad_zcut_{paw}", "furless", p0=(0, 0, zt + 0.75), n=(0, 0, 1),
                            region=lambda P, tr=tr: tr.query(P[:, :2])[0] < 2.0))
    return out


def boundaries_paws_mask(mask_fn, regions_mm=None, name="furless.mask"):
    """v3b's furless boundary: the 0.5 contour of a furless mask m(P_mm) in [0, 1]; s = (0.5 - m) scaled to mm by the
    mask's own gradient (numeric), so s ~ the distance to the contour; region = near the pads (m in (0.02, 0.98))"""
    memo = {}

    def mask(P):                                         # the mask is costly (feat_paws_v3: ~13 us / point): memoised per array
        k = (id(P), len(P))
        if k not in memo:
            memo.clear(); memo[k] = (P, np.asarray(mask_fn(P), float))
        return memo[k][1]

    def s(P):
        m = mask(P); g = _num_grad(lambda Q: -mask_fn(Q), P)            # direction only
        P2 = P + 0.05 * g; P1 = P - 0.05 * g
        gm = np.maximum(np.abs(mask_fn(P1) - mask_fn(P2)) / 0.1, 1e-3)
        return (0.5 - m) / gm
    smemo = {}

    def s_m(P):
        k = (id(P), len(P))
        if k not in smemo:
            smemo.clear(); smemo[k] = (P, s(P))
        return smemo[k][1]
    reg = (lambda P: (mask(P) > 0.02) & (mask(P) < 0.98))
    return [Boundary(name, "furless", s=s_m, region=reg)]


def boundaries_regions(feats="v3"):
    """the 6 faces of every head feature REGION (head-frame boxes -> world AABB, as the fine box takes them)"""
    import skin_build_v3 as S3
    S3.FEATSET = feats; S3._FM.clear(); out = []
    names = ["mouth", "nose"] + [f"eyes.{s}" for s in S3._feats()["FY"].REGION] + [f"ears.{s}" for s in S3._feats()["FE"].REGION]
    for nm, (lo, hi) in zip(names, S3._region_boxes_head()):
        w = S3._world_aabb(lo, hi); out += boundaries_box(w[0] * 1000, w[1] * 1000, name=f"region.{nm}", kind="region_edge")
    return out


def run(V, F, boundaries, inset=None, N=None, tail_family=None):
    """judge every boundary on a mesh (world mm); returns dict(results, failing, status)"""
    N = vnormals(V, F) if N is None else N; res = {}
    lo, hi = V.min(0), V.max(0)
    for B in boundaries:
        if B.n is not None:
            s = B.s(V)
            if not ((s.min() < -0.5) and (s.max() > 0.5)):
                continue                                  # the crop does not cross this boundary
        r = judge(B, V, F, N, inset)
        if any(r.get(m, {}).get("at", r.get(m, {})).get("n", 0) for m in ("strip", "xgap", "bend")) or r["fails"]:
            res[B.name] = r
    if tail_family:
        res["tail.scan"] = scan_family(V, F, N, tail_family)
    failing = [k for k, v in res.items() if v.get("status") == "FAIL"]
    return dict(results=res, failing=failing, status="FAIL" if failing else "PASS", box_mm=[lo.round(1).tolist(), hi.round(1).tolist()])


# ------------------------------------------------------------------------------------------------ crops of a built skin
SKIN_V3 = os.path.join(LAYERS, "skin_v3.npz")
PROOF_CROPS = dict(                      # world mm boxes (LOCATE's crops, + one smooth body patch for the planted joins)
    earR2=([-45, -240, 262], [0, -190, 340]), earL2=([30, -205, 262], [68, -140, 340]),
    tail=([-1e9, 125, -1e9], [1e9, 1e9, 1e9]), legs=([-1e9, -1e9, -1e9], [1e9, 1e9, 95]),
    neck=([-1e9, -158, 140], [1e9, -140, 330]), bottom=([-1e9, -252, 206], [1e9, -140, 226]), xface=([-50, -252, 206], [-38, -140, 325]),
    flank=([-1e9, -75, 95], [-15, -5, 175]))


def _zstream(path, member, rows=1_000_000):
    import zipfile
    from numpy.lib import format as fmt
    z = zipfile.ZipFile(path); fh = z.open(member + ".npy"); ver = fmt.read_magic(fh)
    sh, fo, dt = fmt.read_array_header_1_0(fh) if ver == (1, 0) else fmt.read_array_header_2_0(fh); dt = np.dtype(dt)
    w = int(np.prod(sh[1:])) if len(sh) > 1 else 1; a = 0
    while a < sh[0]:
        k = min(rows, sh[0] - a); buf = fh.read(k * w * dt.itemsize)
        yield a, np.frombuffer(buf, dt).reshape((k,) + tuple(sh[1:])); a += k


def extract_crops(skin=SKIN_V3, crops=PROOF_CROPS, out_dir=None, ring=True):
    """crops of a full skin npz (v in METRES as the builds store it), streamed: v (mm), f, depth_mm (measured inset), gid.
    A pass over the full skin: run it under engine/tools/heavy_lock.py (~0.5 GB, ~1-2 min)."""
    import partition as PT
    t0 = time.time(); Z = np.load(skin); v = Z["v"].astype(np.float32) * 1000; dm = Z["depth_mm"].astype(np.float32)
    masks = {k: np.all((v >= np.array(lo, np.float32)) & (v <= np.array(hi, np.float32)), 1) for k, (lo, hi) in crops.items()}
    ne = None
    if ring:
        ne = np.empty(len(v), np.float32)
        for a in range(0, len(v), 1_000_000):
            ne[a:a + 1_000_000] = PT.neck(v[a:a + 1_000_000].astype(float) / 1000) * 1000
        masks["ring"] = (np.abs(ne) < 30) & (v[:, 2] > 120)
    keep = {k: [] for k in masks}
    for _, f in _zstream(skin, "f"):
        for k, m in masks.items():
            s = m[f].all(1)
            if s.any():
                keep[k].append(f[s].copy())
    os.makedirs(out_dir, exist_ok=True); out = {}
    for k in masks:
        F = np.concatenate(keep[k]) if keep[k] else np.zeros((0, 3), np.int32); u, inv = np.unique(F, return_inverse=True)
        extra = dict(ne=ne[u]) if (ne is not None and k == "ring") else {}
        np.savez(os.path.join(out_dir, f"crop_{k}.npz"), v=v[u], f=inv.reshape(-1, 3).astype(np.int32), depth_mm=dm[u], gid=u, **extra)
        out[k] = dict(verts=int(len(u)), tris=int(len(F)))
    out["seconds"] = round(time.time() - t0, 1); out["skin"] = skin
    json.dump(out, open(os.path.join(out_dir, "crops.json"), "w"), indent=1)
    return out


def load_crop(d, k):
    Z = np.load(os.path.join(d, f"crop_{k}.npz")); V = Z["v"].astype(float); F = Z["f"].astype(np.int64)
    return V, F, vnormals(V, F), Z["depth_mm"].astype(float), Z


def v3_box_world_mm():
    """skin_v3's fine box faces (world mm) from its build json + the build grid origin (lo_eff), as LOCATE computed them"""
    D = np.load(os.path.join(TR, "tripo_welded.npz")); v = D["v"].astype(float); f = D["f"]; v = v[np.unique(f)]
    vox = 0.0005; lo = np.floor((v.min(0) - 0.006) / vox) * vox
    from exact_sdf import JIT
    le = lo + np.array([JIT[0] * vox, JIT[1] * vox, 0.0])
    fb = json.load(open(os.path.join(LAYERS, "skin_v3_build.json")))["report"]["fine_box"]
    return (le + np.array(fb["b0"]) * vox) * 1000, (le + np.array(fb["b1"]) * vox) * 1000


# ------------------------------------------------------------------------------------------------ the proof (A22, both sides)
def prove(crop_dir, out=None):
    t0 = time.time(); R = dict(marks=dict(STEP_MM=STEP_MM, STEP_REL=STEP_REL, KINK_DEG=KINK_DEG, KINK_REL=KINK_REL, TORN_MAX=TORN_MAX,
                                          XGAP_MAX=XGAP_MAX, XGAP_MM=XGAP_MM, BEND_MAX=BEND_MAX, BEND_REL=BEND_REL),
                               crops=json.load(open(os.path.join(crop_dir, "crops.json"))), fail_side={}, pass_side={})
    blo, bhi = v3_box_world_mm(); R["v3_box_world_mm"] = [blo.round(3).tolist(), bhi.round(3).tolist()]
    faces = {B.name: B for B in boundaries_box(blo, bhi, name="v3box")}

    def face(ax, side):
        return [B for nm, B in faces.items() if nm.startswith(f"v3box.{'xyz'[ax]}{side}")][0]
    # ---- FAIL side: today's skin_v3
    for k in ("earR2", "earL2"):                                       # E1: the box TOP face through the ears
        V, F, N, d, _ = load_crop(crop_dir, k); R["fail_side"][f"E1_{k}"] = judge(face(2, "hi"), V, F, N, d)
    V, F, N, d, Z = load_crop(crop_dir, "ring")                         # N1 / N2: the neck plane
    R["fail_side"]["N1_neck_plane"] = judge([B for B in boundaries_coat("v2") if B.name == "coat.neck_plane+0"][0], V, F, N, d)
    V, F, N, d, _ = load_crop(crop_dir, "tail")                         # T1: the tail scan
    sc = scan_family(V, F, N, boundaries_tail()); bad = {f["station"] for f in sc["failing"]}
    mid = [f"tail.s{s}" for s in range(126, 140)]; tip = [f"tail.s{s}" for s in range(175, 186)]
    sc["mid_ring_caught"] = bool(bad & set(mid)); sc["tip_collar_caught"] = bool(bad & set(tip))
    sc["status_rings"] = "FAIL" if (sc["mid_ring_caught"] and sc["tip_collar_caught"]) else "PASS"
    sc.pop("series"); R["fail_side"]["T1_tail_scan"] = sc
    V, F, N, d, _ = load_crop(crop_dir, "legs")                         # P1: the paw z cuts
    for B in boundaries_paws_v3():
        R["fail_side"][f"P1_{B.name}"] = judge(B, V, F, N, d)
    # planted step and crease on a smooth join (the right flank; the plane y = -40 mm crosses it ~perpendicularly)
    V, F, N, d, _ = load_crop(crop_dir, "flank")
    J = Boundary("plant.flank_y-40", "plant", p0=(0, -40.0, 0), n=(0, 1, 0), region=lambda P: (P[:, 2] > 105) & (P[:, 2] < 165))
    s = J.s(V); far = (s > 0)
    Vs = V.copy(); Vs[far] += 0.20 * N[far]                              # a 0.20 mm step (one side moved out along its normal)
    Vk = V.copy(); Vk[far] += (np.tan(np.radians(8.0)) * s[far])[:, None] * N[far]   # an 8 deg crease (hinge at the plane)
    R["pass_side"]["smooth_join_flank"] = judge(J, V, F, N)
    R["fail_side"]["planted_step_0p2mm"] = judge(J, Vs, F, vnormals(Vs, F))
    R["fail_side"]["planted_crease_8deg"] = judge(J, Vk, F, vnormals(Vk, F))
    # ---- PASS side: the v3 box faces LOCATE measured clean
    V, F, N, d, _ = load_crop(crop_dir, "neck")
    yb = face(1, "hi"); R["pass_side"]["box_face_y_back"] = judge(Boundary(yb.name, "fine_box", p0=yb.p0, n=yb.n,
                                                                             region=lambda P: (P[:, 0] > blo[0]) & (P[:, 2] > blo[2]) & (P[:, 2] < bhi[2])), V, F, N, d)
    V, F, N, d, _ = load_crop(crop_dir, "bottom")
    zb = face(2, "lo"); R["pass_side"]["box_face_z_bottom"] = judge(Boundary(zb.name, "fine_box", p0=zb.p0, n=zb.n,
                                                                                region=lambda P: (P[:, 1] < bhi[1]) & (P[:, 0] > blo[0])), V, F, N, d)
    V, F, N, d, _ = load_crop(crop_dir, "xface")
    xb = face(0, "lo"); R["pass_side"]["box_face_x_side"] = judge(Boundary(xb.name, "fine_box", p0=xb.p0, n=xb.n,
                                                                             region=lambda P: (P[:, 1] < bhi[1]) & (P[:, 2] > blo[2])), V, F, N, d)
    fs = {k: (v.get("status_rings") or v["status"]) for k, v in R["fail_side"].items()}
    ps = {k: v["status"] for k, v in R["pass_side"].items()}
    R["summary"] = dict(fail_side=fs, pass_side=ps, all_fail_side_fail=all(x == "FAIL" for x in fs.values()),
                        all_pass_side_pass=all(x == "PASS" for x in ps.values()))
    R["proven"] = bool(R["summary"]["all_fail_side_fail"] and R["summary"]["all_pass_side_pass"])
    R["seconds"] = round(time.time() - t0, 1)
    if out:
        json.dump(R, open(out, "w"), indent=1, default=float)
    return R


def run_skin(skin, build_json=None, out=None, crop_dir=None, paws="auto"):
    """the SEAM CHECK on a built skin (the merge stage's call): every boundary the construction has, from its build json
    (fine boxes; feature REGIONs incl. the paws), the coat-field planes (v3b set when the build says coat_field_v3b), the
    tail scan + tip check, the paw furless boundary. One streamed pass cuts the crops (heavy_lock it), then each family is
    judged on its own crop. Returns the report; FAIL if any boundary fails."""
    t0 = time.time(); meta = json.load(open(build_json)) if build_json else json.loads(str(np.load(skin)["meta"]))
    rep = meta.get("report", meta); boxes = rep.get("fine_boxes") or [dict(name="head", b0=rep["fine_box"]["b0"], b1=rep["fine_box"]["b1"])]
    D = np.load(os.path.join(TR, "tripo_welded.npz")); vv = D["v"].astype(float); vv = vv[np.unique(D["f"])]
    vox = 0.0005; lo = np.floor((vv.min(0) - 0.006) / vox) * vox
    from exact_sdf import JIT
    le = (lo + np.array([JIT[0] * vox, JIT[1] * vox, 0.0])) * 1000
    fams, crops = {}, {}
    for bx in boxes:
        blo = le + np.array(bx["b0"]) * vox * 1000; bhi = le + np.array(bx["b1"]) * vox * 1000
        for Bd in boundaries_box(blo, bhi, name=f"fine_box.{bx['name']}"):
            ax = int(np.argmax(np.abs(Bd.n))); c_lo, c_hi = blo - 8, bhi + 8; c_lo[ax] = Bd.p0[ax] - 10; c_hi[ax] = Bd.p0[ax] + 10
            k = Bd.name.replace("=", "_"); crops[k] = (c_lo.tolist(), c_hi.tolist()); fams[k] = [Bd]
    feats = rep.get("featset", "v3")
    reg = boundaries_regions(feats)
    for i in range(0, len(reg), 6):                        # one crop per REGION box (its 6 faces, in boundaries_box order)
        six = reg[i:i + 6]; lo3 = np.array([six[0].p0[0], six[2].p0[1], six[4].p0[2]]); hi3 = np.array([six[1].p0[0], six[3].p0[1], six[5].p0[2]])
        k = six[0].name[:six[0].name.index(".xlo")]
        crops[k] = ((lo3 - 10).tolist(), (hi3 + 10).tolist()); fams[k] = six
    cfk = "v3b" if "v3b" in json.dumps(meta.get("what", "")) or rep.get("paws") else "v2"
    crops["coat_ring"] = None; fams["coat_ring"] = [B for B in boundaries_coat(cfk) if B.name.startswith("coat.neck")]
    crops["legs"] = ([-1e9, -1e9, -1e9], [1e9, 1e9, 165]); fams["legs"] = [B for B in boundaries_coat(cfk) if B.name.startswith("coat.leg")]
    crops["tail"] = ([-1e9, 125, -1e9], [1e9, 1e9, 1e9]); fams["tail"] = "scan"
    cd = crop_dir or os.path.join(os.environ.get("TEMP", "/tmp"), "p2_skin_v3b", "seam_run_" + os.path.basename(skin).replace(".npz", ""))
    extract_crops(skin, crops={k: v for k, v in crops.items() if v is not None}, out_dir=cd, ring=True)
    res = {}
    for k, bl in fams.items():
        V, F, N, d, Z = load_crop(cd, "ring" if k == "coat_ring" else k)
        if len(F) < 10:
            res[k] = dict(status="NO DATA", note="the crop holds no skin (a box face outside the surface)"); continue
        if bl == "scan":
            r = scan_family(V, F, N, boundaries_tail()); r.pop("series", None); res["tail.scan"] = r; continue
        if k == "legs":
            pb = boundaries_paws_v3()                     # the v3 z cuts (where P1's coins were) are always scanned
            if (rep.get("paws") or {}).get("module_used") and paws != "off":
                import coat_field_v3b as CF3
                m = CF3._paws_module()
                if m is not None:                         # + the paws owner's own furless contour (its pad rims: REPORTED)
                    pb = pb + boundaries_paws_mask(lambda P: m.furless_mask(P), name="furless.feat_paws_v3_mask")
            bl = bl + pb
        for Bd in bl:
            if Bd.n is not None:
                s = Bd.s(V)
                if not (s.min() < -0.5 < 0.5 < s.max()):
                    continue
            res[Bd.name] = judge(Bd, V, F, N, d)
    failing = [k for k, v in res.items() if v.get("status") == "FAIL"]
    R = dict(skin=skin, n_boundaries=len(res), results=res, failing=failing, status="FAIL" if failing else "PASS", seconds=round(time.time() - t0, 1),
             marks=dict(STEP_MM=STEP_MM, KINK_DEG=KINK_DEG, TORN_MAX=TORN_MAX, XGAP_MAX=XGAP_MAX, BEND_MAX=BEND_MAX, REL=STEP_REL))
    if out:
        json.dump(R, open(out, "w"), indent=1, default=float)
    return R


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "prove"
    if cmd == "run":
        r = run_skin(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else None,
                     out=sys.argv[4] if len(sys.argv) > 4 else sys.argv[2].replace(".npz", "_seams.json"))
        print(json.dumps(dict(status=r["status"], failing=r["failing"], seconds=r["seconds"]), indent=1)); sys.exit(0)
    if cmd == "extract":
        print(json.dumps(extract_crops(sys.argv[2], out_dir=sys.argv[3]), indent=1))
    elif cmd == "prove":
        d = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.environ.get("TEMP", "/tmp"), "p2_skin_v3b", "seam_proof_crops")
        r = prove(d, out=os.path.join(LAYERS, "seam_checks_proof_v3b.json"))
        print(json.dumps(r["summary"], indent=1), "proven", r["proven"], r["seconds"], "s")
