"""BAKED ORAL PARTS for ChainV3b.oral_union: each part's SDF (every tooth, both gums, the palate, the tongue with its
papillae near the smooth body - exactly the composite oral_union evaluates) baked ONCE onto a sparse brick grid at the
part's own resolution (feat_oral_v3b.RES: teeth 0.035, gums 0.07, palate / tongue 0.05 mm), cached in
%TEMP%/p2_skin_v3b/oral_bake, sampled trilinearly. Opt-in: ChainV3b opt oral_bake=True (field_probe.py --oral baked).
MEASURED 2026-10-19: NO GAIN - NOT USED. The weld is ~2.5 % of the chain near the mouth (exact 0.49 us/pt, baked 0.50);
baked at the parts' own grids the final field misses 0.02 mm (p99 0.038 mm; 4 of 240 probe lines change crossing count)
because these SDFs jump. The mouth crop's time is feat_mouth_v3b.edit (ext_air 42 %, _section 34 %). Kept as a record.

Bricks of BRICK^3 cells. The part's exact SDF is evaluated on a dense grid at 2 h over its whole box; a brick whose own
2 h nodes come within FINE_MM (0.3 mm) of zero, or change sign, also holds (BRICK+1)^3 nodes at the part's resolution h
(FINE); everywhere else the 2 h grid is sampled. No Lipschitz assumption: these SDFs are not metric (|grad| p99 5-11,
jumps up to 140 per mm measured 2026-10-19), so a brick is classed by its own values, not by its centre.
The cache key is the sources' SHA-1 (feat_oral_v3b, feat_mouth_v3b, spec_mouth_v3b.json), the constants and the exact SDF
at 256 fixed points; any change rebuilds that part.
usage: python oral_bake.py [bake|check]        bake all parts (~minutes once) | baked vs exact near each part's surface
"""
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
FEAT = os.path.join(ROOT, "engine", "packs", "felid", "features")
TR = os.path.join(ROOT, "tripo_rebuild")
for _p in (FEAT, TR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import numpy as np  # noqa: E402

SCR = os.environ.get("V3B_SCRATCH") or os.path.join(os.environ.get("TEMP", "/tmp"), "p2_skin_v3b")
BAKE_DIR = os.path.join(SCR, "oral_bake")
BRICK = 8
FINE_MM = 0.3
FAR_MM = 1.2           # check(): the error is also reported out to this distance
ORAL_NEAR = 0.6         # = skin_build_v3b.ChainV3b.ORAL_NEAR (the tongue papillae only this close to the smooth tongue)


def part_defs():
    """[(name, (lo, hi) head mm, exact fn(P head mm) -> mm, h)] - the same parts, boxes and functions as oral_union"""
    import feat_oral_v3b as FO
    R = FO.RES; out = [(nm, FO.part_box(nm), FO.part_fn(nm), R["gums"]) for nm in ("upper_gums", "lower_gums")]
    out.append(("palate", FO.part_box("palate"), FO.part_fn("palate"), R["palate"]))
    full = FO.part_fn("tongue")

    def tongue(P):
        f0 = FO.tongue_sdf_jaw(FO.MB.to_jaw(P), papillae=False) * FO.S; near = np.abs(f0) < ORAL_NEAR; f = f0.copy()
        if near.any():
            f[near] = full(P[near])
        return f
    out.append(("tongue", FO.part_box("tongue"), tongue, R["tongue"]))
    for t in FO.MB.TEETH:
        out.append((f"tooth_{t['name']}", FO._tooth_box(t), (lambda P, t=t: FO.tooth_sdf_jaw(FO.MB.to_jaw(P), t) * FO.S), R["teeth"]))
    return out


def _src_sig():
    h = hashlib.sha1()
    for p in ("feat_oral_v3b.py", "feat_mouth_v3b.py", "spec_mouth_v3b.json"):
        with open(os.path.join(FEAT, p), "rb") as fh:
            h.update(fh.read())
    h.update(json.dumps([BRICK, FINE_MM, ORAL_NEAR, "dense2h"]).encode())
    return h.hexdigest()


def _signature(nm, box, fn, h, src):
    lo, hi = np.asarray(box[0], float), np.asarray(box[1], float)
    P = lo + np.random.default_rng(7).random((256, 3)) * (hi - lo)
    return hashlib.sha1((src + nm + json.dumps([lo.tolist(), hi.tolist(), h]) + np.round(fn(P), 6).tobytes().hex()).encode()).hexdigest()


def _eval(fn, P, chunk=500000):
    out = np.empty(len(P))
    for a in range(0, len(P), chunk):
        out[a:a + chunk] = fn(P[a:a + chunk])
    return out


def bake(nm, box, fn, h, sig):
    lo = np.asarray(box[0], float); hi = np.asarray(box[1], float); E = BRICK * h; q = BRICK // 2
    nb = np.ceil((hi - lo) / E).astype(int) + 1; nm_ = nb * q + 1                    # bricks / 2h nodes per axis
    M = np.empty(tuple(nm_), np.float32); gy, gz = np.meshgrid(np.arange(nm_[1]), np.arange(nm_[2]), indexing="ij")
    for ix in range(nm_[0]):                                                          # the dense 2h grid, exact
        P = lo + 2 * h * np.stack([np.full(gy.size, ix), gy.ravel(), gz.ravel()], 1); M[ix] = fn(P).reshape(gy.shape)
    vmin = np.full(tuple(nb), np.inf, np.float32); vmax = np.full(tuple(nb), -np.inf, np.float32)
    for ox in range(q + 1):                                                           # each brick's own 5^3 nodes
        for oy in range(q + 1):
            for oz in range(q + 1):
                sl = M[ox:ox + q * nb[0]:q, oy:oy + q * nb[1]:q, oz:oz + q * nb[2]:q]
                vmin = np.minimum(vmin, sl); vmax = np.maximum(vmax, sl)
    amin = np.where(vmin > 0, vmin, np.where(vmax < 0, -vmax, 0.0)); fine = (amin < FINE_MM).ravel()
    ids = np.flatnonzero(fine); slot = np.full(fine.size, -1, np.int32); slot[ids] = np.arange(len(ids))
    bi = np.stack(np.unravel_index(ids, nb), 1); n_ = BRICK + 1
    g = np.stack(np.meshgrid(*(np.arange(n_),) * 3, indexing="ij"), -1).reshape(-1, 3) * h
    S = np.empty((len(ids), n_, n_, n_), np.float16); step = max(1, 400000 // len(g))
    for a0 in range(0, len(ids), step):
        o = lo + bi[a0:a0 + step] * E
        S[a0:a0 + step] = _eval(fn, (o[:, None, :] + g[None]).reshape(-1, 3)).reshape(-1, n_, n_, n_).astype(np.float16)
    os.makedirs(BAKE_DIR, exist_ok=True)
    np.save(os.path.join(BAKE_DIR, f"{nm}_fine.npy"), S); np.save(os.path.join(BAKE_DIR, f"{nm}_mid.npy"), M.astype(np.float16))
    np.savez(os.path.join(BAKE_DIR, f"{nm}.npz"), lo=lo, h=h, nb=nb, slot=slot, sig=sig)
    return dict(bricks=int(fine.size), fine=int(len(ids)), mb=round((S.nbytes + M.nbytes / 2) / 1e6, 1))


class Baked:
    def __init__(self, nm):
        Z = np.load(os.path.join(BAKE_DIR, f"{nm}.npz"))
        self.lo, self.h, self.nb, self.slot = Z["lo"], float(Z["h"]), Z["nb"], Z["slot"]
        self.S = np.load(os.path.join(BAKE_DIR, f"{nm}_fine.npy"), mmap_mode="r"); self.M = np.load(os.path.join(BAKE_DIR, f"{nm}_mid.npy"), mmap_mode="r")

    @staticmethod
    def _tri(A, I, w, pre=()):
        v = np.zeros(len(w))
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    ww = (w[:, 0] if dx else 1 - w[:, 0]) * (w[:, 1] if dy else 1 - w[:, 1]) * (w[:, 2] if dz else 1 - w[:, 2])
                    v += ww * A[pre + (I[:, 0] + dx, I[:, 1] + dy, I[:, 2] + dz)]
        return v

    def __call__(self, P):
        P = np.asarray(P, float); E = BRICK * self.h; X = (P - self.lo) / E
        bi = np.clip(np.floor(X).astype(int), 0, self.nb - 1); s = self.slot[np.ravel_multi_index(bi.T, self.nb)]
        out = np.empty(len(P)); f = s >= 0
        if f.any():                                                     # FINE brick: the part's own grid
            u = np.clip(X[f] - bi[f], 0, 1) * BRICK; i0 = np.minimum(u.astype(int), BRICK - 1)
            out[f] = self._tri(self.S, i0, u - i0, (s[f],))
        if (~f).any():                                                  # elsewhere: the dense 2h grid
            u = np.clip((P[~f] - self.lo) / (2 * self.h), 0, np.array(self.M.shape) - 1.0); i0 = np.minimum(u.astype(int), np.array(self.M.shape) - 2)
            out[~f] = self._tri(self.M, i0, u - i0)
        return out


def parts(log=print, build=True):
    """oral_union's part list [(name, (lo, hi), fn, None)] with baked samplers (baking any part whose cache is stale)"""
    src = _src_sig(); out = []; t0 = time.time()
    for nm, box, fn, h in part_defs():
        sig = _signature(nm, box, fn, h, src); p = os.path.join(BAKE_DIR, f"{nm}.npz")
        if not (os.path.exists(p) and str(np.load(p)["sig"]) == sig):
            if not build:
                raise RuntimeError(f"oral bake of {nm} missing or stale: python engine/tools/oral_bake.py bake")
            t = time.time(); r = bake(nm, box, fn, h, sig); log(f"  oral bake {nm}: {r}, {time.time() - t:.1f} s")
        out.append((nm, (np.asarray(box[0], float), np.asarray(box[1], float)), Baked(nm), None))
    return out


def check(n=60000, noise=0.4):
    """baked vs exact near every part's surface (part mesh vertices, layers/oral_v3b_<part>.npz, +- noise mm) and uniform
    in its box: max and p99.9 |error| where |exact| < FINE_MM, the count above 0.02 mm, and the max out to FAR_MM"""
    L = os.path.join(TR, "layers"); rng = np.random.default_rng(1); defs = {d[0]: d for d in part_defs()}; P_ = {d[0]: d for d in parts()}
    rows = []; worst = 0.0
    for nm, (_, box, fn, h) in defs.items():
        lo, hi = np.asarray(box[0], float), np.asarray(box[1], float)
        mesh = ("upper_teeth" if nm.startswith("tooth_u") else "lower_teeth") if nm.startswith("tooth_") else None
        src = {"upper_gums": "upper_gums", "lower_gums": "lower_gums", "palate": "palate", "tongue": "tongue"}.get(nm, mesh)
        V = None
        if src and os.path.exists(os.path.join(L, f"oral_v3b_{src}.npz")):
            V = np.load(os.path.join(L, f"oral_v3b_{src}.npz"))["v_head_mm"].astype(float)
            V = V[np.all((V >= lo) & (V <= hi), axis=1)]
        Pn = (V[rng.choice(len(V), n)] + rng.normal(0, noise, (n, 3))) if V is not None and len(V) else lo + rng.random((n, 3)) * (hi - lo)
        Pu = lo + rng.random((n // 2, 3)) * (hi - lo); P = np.clip(np.vstack([Pn, Pu]), lo, hi)
        fe = fn(P); fb = P_[nm][2](P); d = np.abs(fb - fe)
        e1 = float(d[np.abs(fe) < FINE_MM].max()) if (np.abs(fe) < FINE_MM).any() else 0.0
        e2 = float(d[np.abs(fe) < FAR_MM].max()) if (np.abs(fe) < FAR_MM).any() else 0.0
        near = np.abs(fe) < FINE_MM; bad = int((d[near] > 0.02).sum())
        rows.append((nm, e1, e2, bad, float(np.percentile(d[near], 99.9)) if near.any() else 0.0, int(near.sum()))); worst = max(worst, e1)
    tw = max((r for r in rows if r[0].startswith("tooth_")), key=lambda r: r[1])
    for r in rows:
        if not r[0].startswith("tooth_"):
            print(f"{r[0]}: |baked - exact| where |f| < {FINE_MM}: max {r[1]:.4f} p99.9 {r[4]:.4f} mm, > 0.02 at {r[3]} of {r[5]}; max where < {FAR_MM}: {r[2]:.4f}")
    print(f"teeth ({sum(1 for r in rows if r[0].startswith('tooth_'))}): worst {tw[0]} {tw[1]:.4f} mm (< {FINE_MM}), "
          f"{max(r[2] for r in rows if r[0].startswith('tooth_')):.4f} (< {FAR_MM}); > 0.02 at {sum(r[3] for r in rows if r[0].startswith('tooth_'))} of {sum(r[5] for r in rows if r[0].startswith('tooth_'))}")
    print(f"ALL PARTS: worst {worst:.4f} mm within {FINE_MM} mm of a part surface")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "bake"
    if cmd == "bake":
        t = time.time(); parts(); print(f"baked / checked cache in {time.time() - t:.1f} s -> {BAKE_DIR}")
    else:
        check()
