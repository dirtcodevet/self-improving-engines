"""FIELD PROBE: answers cat-skin questions from COORDINATES instead of crops or screenshots. It evaluates the final skin
field exactly as skin_build_v3b.build's fine boxes do - the cached v3b PRE cores (%TEMP%/p2_skin_v3b/pre, else v2's core
for a slab the scan kept) Keys-cubic at the point, then ChainV3b (every feature edit, the leather restore, the lid clamp,
the paws, the oral weld) - at chosen points, without meshing. One line per probe, seconds per run. Field sign: < 0 tissue,
> 0 air (mm). Not included: the tail-tip cap (TailCap, built from a marched tail block; tail questions need a crop).

usage (world mm unless --frame; every mode prints ONE line, --ascii / --png add a picture):
  python field_probe.py line x0 y0 z0 x1 y1 z1 [--frame world|head|earL|earR] [--step 0.02]
        -> the surface crossings along the line and the tissue (T) / air runs with their lengths
  python field_probe.py slice ox oy oz ux uy uz vx vy vz su sv [--frame ...] [--step 0.25] [--ascii] [--png out.png]
        -> inside/outside map of the plane origin + a u + b v (a in 0..su, b in 0..sv mm): tissue share, pieces, holes
  python field_probe.py wall L|R [--hh 0.02,0.05,0.10,0.15,0.20] [--az 12]
        -> ear wall thickness at the base: rays from the ear axis outward per azimuth; '-' = no tissue (a window)
  python field_probe.py wallmap L|R [--hh-range 0.20 -0.10] [--az 36]
        -> the same as an unwrapped map (rows h/H, columns azimuth); one summary line, --ascii for the map
  python field_probe.py shelf L|R [--rad 0,3,6]
        -> the ear floor ("shelf") height along the ear axis: lines down the axis direction at offsets, first tissue h/H
  python field_probe.py mouth [--n 12]
        -> upper/lower oral part gaps IN THE FIELD: lines through the closest upper-lower part pairs, the air run between
options: --set module.NAME=value (repeatable: a feature constant, e.g. feat_ears_v3b.EDGE_R_LAT=4 reproduces crop v3b7)
         --opt key=value (ChainV3b option, e.g. oral_union=False)   --paws auto|on|off   --tag text (echoed first)
         --oral exact|baked (the oral weld's parts: their exact SDFs as the build does, or oral_bake.py's cached grids)
frames: 'head' = head-local mm (feat_* modules' frame); 'earL'/'earR' = feat_ears_v3b's ear frame: x lateral (u), y front
(v), z up the ear axis (A), origin at the ear base origin (h/H = z / H).
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
TR = os.path.join(ROOT, "tripo_rebuild")
sys.path.insert(0, TR)
import numpy as np  # noqa: E402

AZ_NAMES = {0: "lat", 45: "lat-fr", 90: "front", 135: "med-fr", 180: "med", 225: "med-bk", 270: "back", 315: "lat-bk"}


class Field:
    """the build's fine field f(P) in mm at world-mm points (see the module doc)"""

    def __init__(self, sets=(), opt=None, paws="auto", feats="v3", modules=None, oral="exact"):
        import skin_build as SB
        import skin_build_v3 as S3
        import skin_build_v3b as B
        self.SB, self.S3, self.B = SB, S3, B
        B.init(); B.use_modules(feats, modules, log=lambda *a: None)
        self.sets = apply_sets(sets)
        self.pre, self.stale = B.pre_cached()
        self.vox = SB.G["vox"]; self.le = B.lo_eff()
        opt = dict(opt or {}); opt.setdefault("oral_bake", oral == "baked")
        self.ch = B.ChainV3b(opt, B._paws_for_build(paws)); self.oral = oral
        if self.ch.v3:                                       # the nose edit's base field: the PRE at the point (build: PB0)
            def base_fn(Phm):
                return self.pre_mm(self.ch.PT.HC + (np.asarray(Phm, float) / 1000) @ self.ch.PT.HR.T)
            self.ch.base_fn = base_fn
        self.PT = self.ch.PT

    def pre_mm(self, Pw, chunk=4096):
        """PRE field (mm) at world-m points: Keys cubic on the cached cores' 0.5 mm nodes (local 4^3 stencil)"""
        Pw = np.asarray(Pw, float); out = np.empty(len(Pw))
        for a in range(0, len(Pw), chunk):
            X = (Pw[a:a + chunk] - self.le) / self.vox; lo = np.floor(X.min(0)).astype(int) - 2; hi = np.ceil(X.max(0)).astype(int) + 2
            blk = self.S3._block(self.pre, lo, hi).astype(np.float64)
            out[a:a + chunk] = self.S3.keys_cubic(blk, X - lo) * 1000
        return out

    def __call__(self, P_mm, chunk=200000):
        P_mm = np.asarray(P_mm, float); out = np.empty(len(P_mm))
        for a in range(0, len(P_mm), chunk):
            Pw = P_mm[a:a + chunk] / 1000
            out[a:a + chunk] = self.ch(Pw, self.pre_mm(Pw))
        return out

    # ---- frames
    def head_to_world(self, Ph_mm):
        return (self.PT.HC + (np.atleast_2d(np.asarray(Ph_mm, float)) / 1000) @ self.PT.HR.T) * 1000

    def ear_frame(self, sd):
        import feat_ears_v3b as FE
        return FE.ear_frame(sd)

    def to_world(self, P, frame):
        P = np.atleast_2d(np.asarray(P, float))
        if frame == "world":
            return P
        if frame == "head":
            return self.head_to_world(P)
        fr = self.ear_frame(frame[-1])
        return self.head_to_world(fr["O"] + P[:, :1] * fr["u"] + P[:, 1:2] * fr["v"] + P[:, 2:3] * fr["A"])

    def dir_to_world(self, d, frame):
        d = np.asarray(d, float)
        if frame == "world":
            return d
        if frame == "head":
            return self.PT.HR @ d
        fr = self.ear_frame(frame[-1])
        return self.PT.HR @ (d[0] * fr["u"] + d[1] * fr["v"] + d[2] * fr["A"])


def apply_sets(sets):
    """--set module.NAME=value: a feature module constant for this run only (import-time caches are rebuilt)"""
    import importlib
    done = []
    for s in sets or ():
        k, v = s.split("=", 1); mod, name = k.rsplit(".", 1); m = importlib.import_module(mod)
        old = getattr(m, name); val = type(old)(eval(v)) if isinstance(old, (int, float, bool)) else eval(v)
        setattr(m, name, val); done.append(f"{k}={val}")
        if hasattr(m, "_SH"):
            m._SH.clear()
        if hasattr(m, "_region") and hasattr(m, "REGION"):
            m.REGION = m._region()
    return done


# ================================================================================================ line analysis
def runs_along(f, s):
    """crossings (linear interpolation of the samples) and the tissue / air runs along a sampled line: f (mm) at arc s (mm)"""
    neg = f < 0; idx = np.flatnonzero(neg[1:] != neg[:-1])
    xs = s[idx] + (s[idx + 1] - s[idx]) * f[idx] / (f[idx] - f[idx + 1])
    cuts = np.r_[s[0], xs, s[-1]]; kind = []
    state = neg[0]
    for _ in range(len(cuts) - 1):
        kind.append("T" if state else "air"); state = not state
    return xs, [(k, float(a), float(b)) for k, a, b in zip(kind, cuts[:-1], cuts[1:])]


def fmt_runs(runs, interior_only=False):
    return " | ".join(f"{k} {a:.2f}-{b:.2f} ({b - a:.2f})" for k, a, b in runs)


def line_probe(FD, A, Bp, step=0.02):
    A = np.asarray(A, float); Bp = np.asarray(Bp, float); L = float(np.linalg.norm(Bp - A)); n = max(int(np.ceil(L / step)) + 1, 2)
    s = np.linspace(0, L, n); P = A + np.outer(s / L, Bp - A); f = FD(P)
    xs, runs = runs_along(f, s)
    return dict(L=L, n=n, s=s, f=f, crossings=xs, runs=runs)


# ================================================================================================ presets
def ear_rays(FD, sd, hh_list, az_list, r0=0.0, r1=32.0, step=0.02):
    """rays from the ear axis outward (ear frame, at h = hh H) per azimuth; returns [(hh, az, runs)]"""
    fr = FD.ear_frame(sd); H = fr["H"]; s = np.arange(r0, r1 + step / 2, step); out = []
    P_all = []
    for hh in hh_list:
        for az in az_list:
            d = np.cos(np.radians(az)) * fr["u"] + np.sin(np.radians(az)) * fr["v"]
            P_all.append(fr["O"] + hh * H * fr["A"] + np.outer(s, d))
    f_all = FD(FD.head_to_world(np.vstack(P_all))).reshape(len(hh_list) * len(az_list), len(s))
    k = 0
    for hh in hh_list:
        for az in az_list:
            out.append((hh, az, runs_along(f_all[k], s)[1])); k += 1
    return out, H


def wall_of(runs):
    """the wall a ray from the axis crosses: the first tissue run that ENDS in air before the ray's end (a run reaching
    the end is head, not wall); None = no tissue at all on the ray (a window or the open front)"""
    T = [(a, b) for k, a, b in runs if k == "T"]
    if not T:
        return None, False
    end = runs[-1][2]; walls = [(a, b) for a, b in T if b < end - 1e-6]
    if walls:
        return walls[0][1] - walls[0][0], False
    return T[0][1] - T[0][0], True              # tissue to the ray's end: runs into the head


def preset_wall(FD, sd, hh_list, naz):
    az = [i * 360.0 / naz for i in range(naz)]; R, H = ear_rays(FD, sd, hh_list, az)
    parts = []
    for hh in hh_list:
        cells = []
        for (h_, a_, runs) in R:
            if h_ != hh:
                continue
            t, head = wall_of(runs); nm = AZ_NAMES.get(int(round(a_)), f"{a_:.0f}")
            cells.append(f"{nm} {'-' if t is None else ('head' if head else f'{t:.2f}')}")
        parts.append(f"h/H {hh:.2f}: " + ", ".join(cells))
    win = [(h_, a_) for (h_, a_, runs) in R if wall_of(runs)[0] is None]
    return f"wall {sd} (H {H:.1f} mm, mm of tissue per azimuth; '-' no tissue) " + " || ".join(parts) + \
        f" || no-tissue rays {len(win)}/{len(R)}" + (f" at (h/H, az) {[(round(a, 2), round(b)) for a, b in win[:8]]}" if win else "")


def preset_wallmap(FD, sd, hh0, hh1, naz, nh, ascii_=False):
    hh_list = list(np.round(np.linspace(hh0, hh1, nh), 3)); az = [i * 360.0 / naz for i in range(naz)]
    R, H = ear_rays(FD, sd, hh_list, az, step=0.03)
    M = np.full((len(hh_list), len(az)), "?", dtype="<U1"); k = 0; win = []
    for i, hh in enumerate(hh_list):
        for j, a in enumerate(az):
            t, head = wall_of(R[k][2]); k += 1
            M[i, j] = "." if t is None else ("#" if head else str(min(int(t / 0.25), 9)))
            if t is None:
                win.append((hh, a))
    lat = [w for w in win if (w[1] <= 60 or w[1] >= 300)]
    line = (f"wallmap {sd} (H {H:.1f}): rows h/H {hh0}..{hh1} x {naz} az; no-tissue cells {len(win)} of {M.size}, lateral "
            f"sector (az<=60 or >=300) {len(lat)}" + (f": h/H {min(w[0] for w in lat):.2f}..{max(w[0] for w in lat):.2f}, "
                                                       f"az {sorted(set(round(w[1]) for w in lat))[:10]}" if lat else ""))
    if ascii_:
        hdr = "".join("|" if round(a) % 90 == 0 else " " for a in az)
        line += "\n       " + hdr + "   (| = lat 0, front 90, med 180, back 270; digit = wall mm / 0.25, # = into head, . = none)"
        for i, hh in enumerate(hh_list):
            line += f"\n{hh:6.2f} " + "".join(M[i])
    return line


def preset_shelf(FD, sd, rads):
    """lines parallel to the ear axis, from TOP x H (inside the cavity, ear_shelf_probe.py's upper limit 0.6) down to -0.4 H,
    at offset `rad` (lateral / front / medial / back): the first tissue entered going down (the ear floor), as h/H"""
    fr = FD.ear_frame(sd); H = fr["H"]; TOP = 0.6; s = np.arange(0.0, (TOP + 0.4) * H, 0.02); res = []
    for r in rads:
        dirs = [(0, "ax")] if r == 0 else [(0, "lat"), (90, "fr"), (180, "med"), (270, "bk")]
        for az, nm in dirs:
            off = r * (np.cos(np.radians(az)) * fr["u"] + np.sin(np.radians(az)) * fr["v"])
            P = fr["O"] + off + np.outer(TOP * H - s, fr["A"]); f = FD(FD.head_to_world(P)); xs, runs = runs_along(f, s)
            first = next((a for k, a, b in runs if k == "T"), None)
            res.append(f"{nm}{r:g} {'-' if first is None else ('in tissue at start' if first == 0 else f'{(TOP * H - first) / H:.3f}')}")
    return f"shelf {sd} (H {H:.1f} mm): first tissue h/H going down from h/H {TOP} parallel to the axis: " + ", ".join(res)


def preset_mouth(FD, n=12, pad=1.5):
    """the field's air gap between the upper and lower oral parts: for the n closest upper-lower part point pairs (part
    meshes, layers/oral_v3b_<part>.npz, head mm) the line through the pair, extended `pad` mm each side; the air run that
    contains the pair's midpoint is the gap (none = FUSED)"""
    from scipy.spatial import cKDTree
    L = os.path.join(TR, "layers"); up, lo = ("upper_teeth", "upper_gums", "palate"), ("lower_teeth", "lower_gums", "tongue")
    rng = np.random.default_rng(0)

    def pts(nm, k=200000):
        v = np.load(os.path.join(L, f"oral_v3b_{nm}.npz"))["v_head_mm"].astype(float)
        return v if len(v) <= k else v[rng.choice(len(v), k, replace=False)]
    U = np.vstack([pts(nm) for nm in up]); Ulab = np.concatenate([[nm] * min(200000, len(np.load(os.path.join(L, f"oral_v3b_{nm}.npz"))["v_head_mm"])) for nm in up])
    Lw = {nm: pts(nm) for nm in lo}; best = []
    for nm, V in Lw.items():
        d, i = cKDTree(V).query(U, distance_upper_bound=3.0); ok = np.isfinite(d)
        for j in np.flatnonzero(ok):
            best.append((d[j], Ulab[j], nm, U[j], V[i[j]]))
    best.sort(key=lambda t: t[0]); picked = []
    for b in best:                                           # n pairs at least 1 mm apart from each other
        if all(np.linalg.norm(b[3] - p[3]) > 1.0 for p in picked):
            picked.append(b)
        if len(picked) >= n:
            break
    out = []
    for d, nu, nl, pu, pl in picked:
        e = (pl - pu) / max(np.linalg.norm(pl - pu), 1e-9); A = FD.head_to_world(pu - pad * e)[0]; Bp = FD.head_to_world(pl + pad * e)[0]
        r = line_probe(FD, A, Bp, step=0.01); mid = pad + d / 2
        gap = next((b - a for k, a, b in r["runs"] if k == "air" and a <= mid <= b), None)
        out.append((d, gap, nu, nl, pu))
    fused = [o for o in out if o[1] is None]; g = [o[1] for o in out if o[1] is not None]
    worst = min(out, key=lambda o: (o[1] if o[1] is not None else -1))
    return (f"mouth: {len(out)} closest upper-lower pairs (parts {min(o[0] for o in out):.3f}-{max(o[0] for o in out):.3f} mm apart): "
            f"field air gap min {min(g) if g else float('nan'):.3f} median {np.median(g) if g else float('nan'):.3f} mm, FUSED {len(fused)}; "
            f"tightest {worst[2]}-{worst[3]} at head mm {np.round(worst[4], 1).tolist()} (parts {worst[0]:.3f}, field "
            f"{'FUSED' if worst[1] is None else f'{worst[1]:.3f}'})")


# ================================================================================================ slice
def slice_probe(FD, O, U, Vv, su, sv, step, frame):
    a = np.arange(0, su + step / 2, step); b = np.arange(0, sv + step / 2, step)
    G = np.stack(np.meshgrid(a, b, indexing="ij"), -1).reshape(-1, 2)
    O = np.asarray(O, float); U = np.asarray(U, float) / np.linalg.norm(U); Vv = np.asarray(Vv, float) / np.linalg.norm(Vv)
    P = O + G[:, :1] * U + G[:, 1:] * Vv
    f = FD(FD.to_world(P, frame)).reshape(len(a), len(b))
    return a, b, f


def slice_summary(f):
    from scipy import ndimage
    T = f < 0; nT = ndimage.label(T)[1]; air, nA = ndimage.label(~T)
    edge = set(np.unique(np.r_[air[0], air[-1], air[:, 0], air[:, -1]])) - {0}
    holes = nA - len(edge)
    return f"tissue {100 * T.mean():.1f} %, tissue pieces {nT}, air pieces {nA} ({holes} enclosed)"


def slice_ascii(f, width=100):
    k = max(1, int(np.ceil(f.shape[0] / width))); g = f[::k, ::k]
    return "\n".join("".join("#" if x < 0 else "." for x in g[:, j]) for j in range(g.shape[1] - 1, -1, -1))


MIN_FREE_GB = 3.0      # this tool's peak (~0.9 GB) + the 2 GB floor of the 16 GB machine: wait, never squeeze a build


def wait_for_memory(log=print):
    """the probes do not take engine/tools/heavy_lock.py's lock (seconds, < 1 GB), but they wait while free memory is short"""
    import heavy_lock as HL
    said = False
    while HL.free_gb() < MIN_FREE_GB:
        if not said:
            log(f"waiting: {HL.free_gb():.1f} GB free < {MIN_FREE_GB} (a heavy run is on)", flush=True); said = True
        time.sleep(10)


# ================================================================================================ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["line", "slice", "wall", "wallmap", "shelf", "mouth"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--frame", default="world"); ap.add_argument("--step", type=float, default=None)
    ap.add_argument("--set", action="append", default=[]); ap.add_argument("--opt", action="append", default=[])
    ap.add_argument("--paws", default="auto"); ap.add_argument("--tag", default="")
    ap.add_argument("--oral", default="exact", choices=["exact", "baked"])
    ap.add_argument("--hh", default="0.02,0.05,0.10,0.15,0.20"); ap.add_argument("--az", type=int, default=None)
    ap.add_argument("--hh-range", nargs=2, type=float, default=[0.20, -0.10]); ap.add_argument("--nh", type=int, default=16)
    ap.add_argument("--rad", default="0,3,6"); ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--ascii", action="store_true"); ap.add_argument("--png", default=None)
    a = ap.parse_args(argv); t0 = time.time()
    wait_for_memory(); t0 = time.time()
    opt = {}
    for o in a.opt:
        k, v = o.split("=", 1); opt[k] = eval(v)
    FD = Field(sets=a.set, opt=opt, paws=a.paws, oral=a.oral); t_init = time.time() - t0
    head = (a.tag + " " if a.tag else "") + (f"[{' '.join(FD.sets)}] " if FD.sets else "") + (f"[opt {opt}] " if opt else "")
    if FD.stale:
        head += f"[PRE STALE slabs {FD.stale}: run skin_build_v3b.py pre] "
    v = [float(x) for x in a.args] if a.mode in ("line", "slice") else []
    if a.mode == "line":
        A, Bp = FD.to_world(v[:3], a.frame)[0], FD.to_world(v[3:6], a.frame)[0]
        r = line_probe(FD, A, Bp, a.step or 0.02)
        msg = (f"line {a.frame} {v[:3]}->{v[3:6]} ({r['L']:.2f} mm, step {a.step or 0.02}): surface at "
               f"{np.round(r['crossings'], 2).tolist()} mm || {fmt_runs(r['runs'])}")
    elif a.mode == "slice":
        su, sv = v[9], v[10]; step = a.step or 0.25
        ga, gb, f = slice_probe(FD, v[0:3], v[3:6], v[6:9], su, sv, step, a.frame)
        msg = f"slice {a.frame} o {v[0:3]} u {v[3:6]} x {su} v {v[6:9]} x {sv} @ {step} mm: " + slice_summary(f)
        if a.png:
            import matplotlib
            matplotlib.use("Agg"); import matplotlib.pyplot as plt
            plt.imsave(a.png, (f.T[::-1] < 0).astype(float), cmap="gray_r"); msg += f" -> {a.png}"
        if a.ascii:
            msg += "\n" + slice_ascii(f)
    elif a.mode == "wall":
        msg = preset_wall(FD, a.args[0], [float(x) for x in a.hh.split(",")], a.az or 12)
    elif a.mode == "wallmap":
        msg = preset_wallmap(FD, a.args[0], a.hh_range[0], a.hh_range[1], a.az or 36, a.nh, a.ascii)
    elif a.mode == "shelf":
        msg = preset_shelf(FD, a.args[0], [float(x) for x in a.rad.split(",")])
    else:
        msg = preset_mouth(FD, a.n)
    print(f"{head}{msg} || {time.time() - t0:.1f} s (init {t_init:.1f})", flush=True)


if __name__ == "__main__":
    main()
