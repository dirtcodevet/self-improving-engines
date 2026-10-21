"""NOSE v3b checks + test harness (cat v3 round 2, owner 'nose', ruling R-N). Every check is two-sided (A10 / A22): it
FAILS on a planted or known defect sized to what it reads, PASSES a correct case, and its pass mark carries a reason.

Decision checks, reported FIRST:
  D1   approved leather TOP EDGE within 0.2 mm of v1 outside the tail-entry zones (cat_decisions.check_leather_top, as
       written AND the edge-only zone of feat_nose_v3 Tool lesson 1)
  D2   nostril tails cut into the approved corners (cat_decisions.check_nostril_tails)
  LIP  lip form within 0.5 mm of feat_nose_v3's preview outside the fixed zones (two-sided, exact mesh distance)
Checks:
  LP   LINES PRESENT: median groove sections, alar groove (comma tail) sections, alar fold in the vestibule, against the
       photo-measured / cited values in spec_nose_v3b.json. FAILS on skin_v3's smoothed nose.
  NW   NO ARTEFACT WRINKLES: N5 (local quadratic residual + normal scatter) after subtracting the DECLARED design relief,
       outside the designed line zones, plus the top-band rib spectrum (1.5-6 / mm); its noise floor is MEASURED on a
       smoothed-form correct case meshed the same way.
  IP   INTO PASSAGE: from every opening pixel, the best straight probe within 60 deg of the inward axis travels >= D_VEST
       inside the cavity. FAILS on feat_nose_v3's blind tail half.
Harness: base field, adaptive 0.10 mm crop preview (nose_v3_preview.run_preview's scheme), a uniform-grid ray tracer
(nearest hit, numba; checked against feat_eyes_v3.raycast), an AO renderer, the skin_v3 nose-crop extractor.

usage (heavy steps through engine/tools/heavy_lock.py --label nose):
  python nose_checks_v3b.py preview [grid] [parts|all] [name]   -> tripo_rebuild/layers/<name>.npz/.json
  python nose_checks_v3b.py crop_skin_v3                         -> tripo_rebuild/layers/skin_v3_nose_crop_v3b.npz (full-skin pass)
  python nose_checks_v3b.py floor                                -> NW floor case
  python nose_checks_v3b.py check | prove | render
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
TR = os.path.join(ROOT, "tripo_rebuild"); L = os.path.join(TR, "layers")
FEL = os.path.join(ROOT, "engine", "packs", "felid"); FEAT = os.path.join(FEL, "features")
for _p in (FEAT, FEL, HERE, TR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import numpy as np  # noqa: E402

import feat_nose as V2  # noqa: E402
import feat_nose_v3 as N3  # noqa: E402
import feat_nose_v3b as NB  # noqa: E402

PAD = 1.5
BAND, OPEN = 0.75, 0.5
OUT_JSON = os.path.join(L, "feat_nose_v3b_checks.json")
PROOF_JSON = os.path.join(L, "feat_nose_v3b_proofs.json")


def jdump(o, fn):
    json.dump(o, open(fn, "w"), indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else (float(x) if isinstance(x, np.floating) else str(x)))


# ================================================================== base field (v2 PRE cores, Keys cubic), any box
def base_field(lo, hi, pad=2.5):
    import partition as PT
    import skin_build as SB
    from skin_build_v3 import Coarse, keys_cubic
    SB._init(0.0005, 0.001, 0.02); vc = 0.0005
    lo_eff = SB.G["lo"] + np.array([SB.JIT[0] * vc, SB.JIT[1] * vc, 0.0]); rs = SB.slab_ranges()
    lo = np.asarray(lo, float) - pad; hi = np.asarray(hi, float) + pad
    cor = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])])
    W = PT.HC + (cor / 1000) @ PT.HR.T
    i0 = np.floor((W.min(0) - lo_eff) / vc).astype(int) - 4; i1 = np.ceil((W.max(0) - lo_eff) / vc).astype(int) + 4
    sl = sorted({si for si, (j0, j1) in enumerate(rs) if j1 >= i0[1] - 3 and j0 <= i1[1] + 3})
    cores = os.path.join(os.environ["TEMP"], "p2_skin_v2", "full")
    pre = Coarse([(rs[si][0], np.load(os.path.join(cores, f"core_{si:03d}.npy"))) for si in sl])
    g = np.stack(np.meshgrid(*[np.arange(i0[d], i1[d] + 1) for d in range(3)], indexing="ij"), -1).reshape(-1, 3)
    pblk = pre.node(g).reshape(tuple(i1 - i0 + 1)).astype(np.float64); lo_blk = lo_eff + i0 * vc

    def Fbase(Phm):
        Wp = PT.HC + (np.asarray(Phm, float) / 1000) @ PT.HR.T; X = (Wp - lo_blk) / vc; out = np.empty(len(X))
        for s in range(0, len(X), 400000):
            out[s:s + 400000] = keys_cubic(pblk, X[s:s + 400000]) * 1000
        return out
    return Fbase


# ================================================================== adaptive fine-grid crop (nose_v3_preview scheme)
def mesh_crop(field_fn, open_fn, lo, hi, grid, band=BAND, open_band=OPEN):
    """field_fn(P head mm) -> F mm; coarse 0.5 mm pass, exact at fine nodes in active coarse cells (near the level set,
    with a sign change, or near an intended opening), trilinear elsewhere; marching cubes; air border."""
    from scipy import ndimage
    from skimage.measure import marching_cubes
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    r = int(round(0.5 / grid)); nc = np.floor((hi - lo) / 0.5).astype(int) + 1; hi = lo + (nc - 1) * 0.5
    ax = [lo[d] + 0.5 * np.arange(nc[d]) for d in range(3)]
    Pc = np.stack(np.meshgrid(*ax, indexing="ij"), -1).reshape(-1, 3)
    Ec = field_fn(Pc).reshape(tuple(nc)); Oc = (open_fn(Pc) if open_fn else np.full(len(Pc), np.inf)).reshape(tuple(nc))
    sh = lambda A, i, j, k: A[i:A.shape[0] - 1 + i, j:A.shape[1] - 1 + j, k:A.shape[2] - 1 + k]  # noqa: E731
    cmin = np.minimum.reduce([np.abs(sh(Ec, i, j, k)) for i in (0, 1) for j in (0, 1) for k in (0, 1)])
    sg = [np.sign(sh(Ec, i, j, k)) for i in (0, 1) for j in (0, 1) for k in (0, 1)]
    omin = np.minimum.reduce([sh(Oc, i, j, k) for i in (0, 1) for j in (0, 1) for k in (0, 1)])
    act = (cmin < band) | (np.max(sg, 0) != np.min(sg, 0)) | (omin < open_band); act = ndimage.binary_dilation(act, iterations=1)
    nf = (nc - 1) * r + 1
    Ff = ndimage.zoom(Ec.astype(np.float32), [nf[d] / nc[d] for d in range(3)], order=1, grid_mode=False).astype(np.float32)[:nf[0], :nf[1], :nf[2]]
    fm = np.zeros(tuple(nf), bool); ia = np.argwhere(act)
    for d0 in range(r + 1):
        for d1 in range(r + 1):
            for d2 in range(r + 1):
                fm[ia[:, 0] * r + d0, ia[:, 1] * r + d1, ia[:, 2] * r + d2] = True
    idx = np.argwhere(fm).astype(np.int32); n_ex = len(idx); del fm
    for s in range(0, n_ex, 600000):
        P = lo + idx[s:s + 600000] * grid; Ff[tuple(idx[s:s + 600000].T)] = field_fn(P)
    del idx
    Ff[0], Ff[-1], Ff[:, 0], Ff[:, -1], Ff[:, :, 0], Ff[:, :, -1] = 10, 10, 10, 10, 10, 10
    v, f, _, _ = marching_cubes(Ff, 0.0, spacing=(grid,) * 3); f = f[:, ::-1].astype(np.int64); Vh = v + lo
    n = vnormals(Vh, f)
    fr = (Vh[:, 1] < -70) & (np.abs(Vh[:, 0]) < 3) & (Vh[:, 2] < -6) & (Vh[:, 2] > -9)
    if fr.any() and np.median(n[fr, 1]) > 0:
        f = f[:, ::-1]; n = -n
    border = np.any((Vh < lo + 2 * grid) | (Vh > hi - 2 * grid), axis=1)
    return Vh, f, n, border, dict(fine_nodes=int(np.prod(nf)), exact_nodes=int(n_ex), exact_share=round(n_ex / float(np.prod(nf)), 4))


def vnormals(P, f):
    fn = np.cross(P[f[:, 1]] - P[f[:, 0]], P[f[:, 2]] - P[f[:, 0]]); N = np.zeros_like(P)
    for k in range(3):
        np.add.at(N, f[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def crop_box():
    return np.array(NB.REGION["lo_mm"]) - PAD, np.array(NB.REGION["hi_mm"]) + PAD


def run_preview(grid=0.10, parts="all", name="feat_nose_v3b_preview"):
    import partition as PT
    t0 = time.time(); lo, hi = crop_box(); Fb = base_field(lo, hi)
    pp = NB.PARTS if parts == "all" else tuple(parts.split(","))
    fn_ = lambda P: NB.edit(P, Fb(P), base_fn=Fb, parts=pp)  # noqa: E731
    Vh, f, n, border, rep = mesh_crop(fn_, NB.opening_sdf, lo, hi, grid)
    out = os.path.join(L, name + ".npz")
    np.savez_compressed(out, v=PT.HC + (Vh / 1000) @ PT.HR.T, f=f, n=n @ PT.HR.T, v_head_mm=Vh, border=border, grid_mm=grid,
                        note=f"feat_nose_v3b fine-grid preview crop ({grid} mm, head frame, REGION + {PAD} mm), v2 pre-edit cores (Keys) + "
                             f"feat_nose_v3b.edit(parts={pp}) at the fine nodes; world metres; crop closed by an air border")
    rep.update(which="v3b", parts=list(pp), grid_mm=grid, crop_head_mm=[lo.tolist(), hi.tolist()], verts=int(len(Vh)), tris=int(len(f)),
               border_verts=int(border.sum()), t_total_s=round(time.time() - t0, 1), file=os.path.basename(out))
    jdump(rep, out.replace(".npz", ".json")); print(rep, flush=True); return rep


# ================================================================== meshes (head mm)
def load_mesh(fn, preview=True, keep_border=False, box=None):
    import partition as PT
    Z = np.load(fn if os.path.isabs(fn) else os.path.join(L, fn))
    if "v_head_mm" in Z.files:
        Vh = Z["v_head_mm"].astype(float); f = Z["f"].astype(np.int64)
        if not keep_border and "border" in Z.files:
            f = f[~Z["border"][f].any(1)]
    else:
        Vh = PT.head_local(Z["v"].astype(float)) * 1000; f = Z["f"].astype(np.int64)
    if box is not None:
        lo, hi = box; ins = np.all((Vh >= lo) & (Vh <= hi), axis=1); f = f[ins[f].all(1)]
    idx = np.unique(f); rm = -np.ones(len(Vh), np.int64); rm[idx] = np.arange(len(idx))
    return Vh[idx], rm[f]


def crop_skin_v3():
    """one pass over the FULL skin_v3 (5.9 M verts / 11.7 M tris; run under heavy_lock): keep the nose crop, head mm"""
    import partition as PT
    t0 = time.time(); Z = np.load(os.path.join(L, "skin_v3.npz")); v = Z["v"]; f = Z["f"]
    lo, hi = crop_box(); Vh = PT.head_local(v.astype(np.float64)) * 1000
    ins = np.all((Vh >= lo - 1) & (Vh <= hi + 1), axis=1); del v
    keep = ins[f].all(1); fk = f[keep].astype(np.int64); idx = np.unique(fk); rm = -np.ones(len(Vh), np.int64); rm[idx] = np.arange(len(idx))
    out = os.path.join(L, "skin_v3_nose_crop_v3b.npz")
    np.savez_compressed(out, v_head_mm=Vh[idx], f=rm[fk], note="skin_v3.npz cropped to feat_nose_v3b REGION + 2.5 mm (head mm); open crop, no border caps")
    rep = dict(file=os.path.basename(out), verts=int(len(idx)), tris=int(len(fk)), seconds=round(time.time() - t0, 1)); print(rep); return rep


# ================================================================== uniform-grid ray tracer (nearest hit)
_NB = {}


def _numba():
    if _NB:
        return _NB
    from numba import njit, prange

    @njit(cache=True)
    def fill(i0, i1, n, cells, tris):
        c = 0
        for t in range(i0.shape[0]):
            for a in range(i0[t, 0], i1[t, 0] + 1):
                for b in range(i0[t, 1], i1[t, 1] + 1):
                    for d in range(i0[t, 2], i1[t, 2] + 1):
                        cells[c] = (a * n[1] + b) * n[2] + d; tris[c] = t; c += 1

    @njit(cache=True)
    def tri(ox, oy, oz, dx, dy, dz, V, F, t):
        a = F[t, 0]; b = F[t, 1]; c = F[t, 2]
        e1x = V[b, 0] - V[a, 0]; e1y = V[b, 1] - V[a, 1]; e1z = V[b, 2] - V[a, 2]
        e2x = V[c, 0] - V[a, 0]; e2y = V[c, 1] - V[a, 1]; e2z = V[c, 2] - V[a, 2]
        px = dy * e2z - dz * e2y; py = dz * e2x - dx * e2z; pz = dx * e2y - dy * e2x
        det = e1x * px + e1y * py + e1z * pz
        if abs(det) < 1e-18:
            return np.inf
        inv = 1.0 / det; sx = ox - V[a, 0]; sy = oy - V[a, 1]; sz = oz - V[a, 2]
        u = (sx * px + sy * py + sz * pz) * inv
        if u < 0.0 or u > 1.0:
            return np.inf
        qx = sy * e1z - sz * e1y; qy = sz * e1x - sx * e1z; qz = sx * e1y - sy * e1x
        v = (dx * qx + dy * qy + dz * qz) * inv
        if v < 0.0 or u + v > 1.0:
            return np.inf
        tt = (e2x * qx + e2y * qy + e2z * qz) * inv
        return tt if tt > 1e-9 else np.inf

    @njit(parallel=True, cache=True)
    def trace(O, D, tmax, lo, cell, n, start, tris, V, F, out_t, out_id):
        for r in prange(O.shape[0]):
            ox, oy, oz = O[r, 0], O[r, 1], O[r, 2]; dx, dy, dz = D[r, 0], D[r, 1], D[r, 2]
            t0 = 0.0; t1 = tmax[r]; bad = False
            for k in range(3):
                o = O[r, k]; d = D[r, k]; bl = lo[k]; bh = lo[k] + n[k] * cell
                if abs(d) < 1e-15:
                    if o < bl or o > bh:
                        bad = True
                else:
                    ta = (bl - o) / d; tb = (bh - o) / d
                    if ta > tb:
                        ta, tb = tb, ta
                    if ta > t0:
                        t0 = ta
                    if tb < t1:
                        t1 = tb
            best = np.inf; bid = -1
            if bad or t0 > t1:
                out_t[r] = best; out_id[r] = bid
                continue
            px = ox + dx * t0; py = oy + dy * t0; pz = oz + dz * t0
            ix = min(max(int((px - lo[0]) / cell), 0), n[0] - 1); iy = min(max(int((py - lo[1]) / cell), 0), n[1] - 1)
            iz = min(max(int((pz - lo[2]) / cell), 0), n[2] - 1)
            sx = 1 if dx > 0 else -1; sy = 1 if dy > 0 else -1; sz = 1 if dz > 0 else -1; big = 1e30
            tdx = cell / abs(dx) if abs(dx) > 1e-15 else big; tdy = cell / abs(dy) if abs(dy) > 1e-15 else big
            tdz = cell / abs(dz) if abs(dz) > 1e-15 else big
            tnx = (lo[0] + (ix + (1 if sx > 0 else 0)) * cell - ox) / dx if abs(dx) > 1e-15 else big
            tny = (lo[1] + (iy + (1 if sy > 0 else 0)) * cell - oy) / dy if abs(dy) > 1e-15 else big
            tnz = (lo[2] + (iz + (1 if sz > 0 else 0)) * cell - oz) / dz if abs(dz) > 1e-15 else big
            while True:
                c = (ix * n[1] + iy) * n[2] + iz
                for j in range(start[c], start[c + 1]):
                    t = tris[j]; tt = tri(ox, oy, oz, dx, dy, dz, V, F, t)
                    if tt < best:
                        best = tt; bid = t
                tcell = min(tnx, min(tny, tnz))
                if best <= tcell or tcell > t1:
                    break
                if tnx <= tny and tnx <= tnz:
                    ix += sx; tnx += tdx
                    if ix < 0 or ix >= n[0]:
                        break
                elif tny <= tnz:
                    iy += sy; tny += tdy
                    if iy < 0 or iy >= n[1]:
                        break
                else:
                    iz += sz; tnz += tdz
                    if iz < 0 or iz >= n[2]:
                        break
            if best > tmax[r]:
                best = np.inf; bid = -1
            out_t[r] = best; out_id[r] = bid
    _NB.update(fill=fill, trace=trace); return _NB


class Tracer:
    """nearest-hit ray tracer over a uniform grid of triangle bins (proof: trace_selfcheck vs feat_eyes_v3.raycast)"""
    def __init__(self, V, F, cell=0.3):
        nb = _numba(); self.V = np.ascontiguousarray(V, np.float64); self.F = np.ascontiguousarray(F, np.int64)
        self.lo = self.V.min(0) - 1e-6; hi = self.V.max(0) + 1e-6; self.cell = float(cell)
        self.n = np.maximum(np.ceil((hi - self.lo) / cell).astype(np.int64), 1)
        T = self.V[self.F]; i0 = np.clip(((T.min(1) - self.lo) / cell).astype(np.int64), 0, self.n - 1)
        i1 = np.clip(((T.max(1) - self.lo) / cell).astype(np.int64), 0, self.n - 1); tot = int((i1 - i0 + 1).prod(1).sum())
        cells = np.empty(tot, np.int64); tris = np.empty(tot, np.int64); nb["fill"](i0, i1, self.n, cells, tris)
        o = np.argsort(cells, kind="stable"); self.tris = tris[o]; self.start = np.searchsorted(cells[o], np.arange(self.n.prod() + 1)).astype(np.int64)
        fc = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); self.fn = fc / np.maximum(np.linalg.norm(fc, axis=1, keepdims=True), 1e-18)

    def __call__(self, O, D, tmax=1e9, chunk=2_000_000):
        O = np.ascontiguousarray(O, np.float64); D = np.asarray(D, np.float64); D = np.ascontiguousarray(D / np.linalg.norm(D, axis=1, keepdims=True))
        tm = np.full(len(O), float(tmax)) if np.isscalar(tmax) else np.ascontiguousarray(tmax, np.float64)
        t = np.empty(len(O)); i = np.empty(len(O), np.int64)
        for s in range(0, len(O), chunk):
            e = min(s + chunk, len(O)); tt = np.empty(e - s); ii = np.empty(e - s, np.int64)
            _numba()["trace"](O[s:e], D[s:e], tm[s:e], self.lo, self.cell, self.n, self.start, self.tris, self.V, self.F, tt, ii)
            t[s:e] = tt; i[s:e] = ii
        return t, i


def trace_selfcheck():
    """the grid tracer against feat_eyes_v3.raycast (brute force over every triangle) on the v3 preview crop"""
    import feat_eyes_v3 as FY
    V, F = load_mesh("feat_nose_v3_preview.npz"); tr = Tracer(V, F)
    rng = np.random.default_rng(1); O = rng.uniform([-8, -90, -18], [8, -85, -3], size=(1500, 3))
    D = np.tile([0, 1.0, 0], (1500, 1)) + rng.normal(scale=0.25, size=(1500, 3)); D /= np.linalg.norm(D, axis=1, keepdims=True)
    tg, _ = tr(O, D); tb, _ = FY.raycast(O, D, V, F, maxhits=32)
    both = np.isfinite(tg) & np.isfinite(tb[:, 0])
    return dict(status="PASS" if (np.isfinite(tg) == np.isfinite(tb[:, 0])).all() and (np.abs(tg[both] - tb[both, 0]).max() < 1e-9) else "FAIL",
                rays=1500, hits=int(both.sum()), max_abs_dt=float(np.abs(tg[both] - tb[both, 0]).max()) if both.any() else None,
                hit_mismatch=int((np.isfinite(tg) != np.isfinite(tb[:, 0])).sum()))


# ================================================================== rendering (Lambert x ambient occlusion)
def render_ao(V, F, d, up, px, center, size, ao_rays=48, ao_reach=2.5, tracer=None, seed=0):
    sys.path.insert(0, os.path.join(ROOT, "cases", "cat1", "v3_skinfix", "locate_data"))
    from render import render
    sh, fid, dep, cam = render(V, F, d, up, px, center=center, size=size)
    tr = tracer or Tracer(V, F); hit = fid >= 0; H, W = sh.shape
    yy, xx = np.nonzero(hit); X = (cam["x0"] + (xx + 0.5) * px)[:, None] * cam["r"] + (cam["y1"] - (yy + 0.5) * px)[:, None] * cam["u"] + dep[hit][:, None] * cam["d"]
    nrm = tr.fn[fid[hit]]; nrm = nrm * -np.sign(np.einsum("ij,j->i", nrm, cam["d"]))[:, None]
    rng = np.random.default_rng(seed); occ = np.zeros(len(X))
    t1 = np.cross(nrm, np.where(np.abs(nrm[:, :1]) < 0.9, [[1.0, 0, 0]], [[0, 1.0, 0]])); t1 /= np.linalg.norm(t1, axis=1, keepdims=True); t2 = np.cross(nrm, t1)
    for k in range(ao_rays):
        u1, u2 = rng.random(len(X)), rng.random(len(X)); r_ = np.sqrt(u1); ph = 2 * np.pi * u2
        Dk = t1 * (r_ * np.cos(ph))[:, None] + t2 * (r_ * np.sin(ph))[:, None] + nrm * np.sqrt(1 - u1)[:, None]
        t, _ = tr(X + 1e-3 * nrm, Dk, tmax=ao_reach); occ += np.isfinite(t)
    openness = 1 - occ / ao_rays; img = np.full((H, W), np.nan); img[hit] = sh[hit] * (0.12 + 0.88 * openness)
    return img, openness, cam


def save_png(imgs, fn, gap=4, labels=None):
    from PIL import Image, ImageDraw
    arr = [(np.clip(np.nan_to_num(i, nan=0.22), 0, 1) * 255).astype(np.uint8) for i in imgs]; h = max(a.shape[0] for a in arr)
    row = np.concatenate([np.pad(a, ((0, h - a.shape[0]), (0, gap)), constant_values=40) for a in arr], 1)
    im = Image.fromarray(row).convert("RGB")
    if labels:
        dr = ImageDraw.Draw(im); x = 4
        for a, lab in zip(arr, labels):
            dr.text((x, 4), lab, fill=(255, 220, 0)); x += a.shape[1] + gap
    im.save(fn); return fn



# ================================================================== marks (each with its reason)
MARKS = {
    "D1_edge_max_mm": 0.2,
    "LIP_max_mm": 0.5,
    "LP_depth_rel": [0.6, 1.6],
    "LP_fwhm_rel": [0.5, 2.0],
    "LP_station_share": 0.9,
    "LP_gap_mm": 0.5,
    "LP_alar_depth_min_mm": 0.15,
    "LP_alar_fwhm_mm": [0.25, 1.2],
    "LP_alar_share": 0.85,
    "LP_fold_defect_min": 0.055,
    "LP_fold_side_deg": 60.0,
    "LP_fold_clear_min_mm": 0.4,
    "IP_cone_deg": 60.0,
    "IP_share_min": 0.98,
}
MARK_REASONS = {
    "D1_edge_max_mm": "the person's approval, G13 (0.2 mm)",
    "LIP_max_mm": "the person's ruling on the lips (R-M / BRIEF): within 0.5 mm of v3 outside the fixed zones",
    "LP_depth_rel": "the groove depth targets are LOW-confidence estimates (photo contrast + spec stations, ~+-40 %): 0.6-1.6 x keeps "
                    "'present at the right scale'; a smoothed-out groove reads <= 0.1 mm (skin_v3) = <= 0.35 x and fails",
    "LP_fwhm_rel": "photo width is +-1 px (0.35 mm) on 0.55-1.1 mm targets: 0.5-2.0 x",
    "LP_station_share": "continuity: >= 90 % of stations and no failing run longer than LP_gap_mm (the photo shows one continuous line)",
    "LP_gap_mm": "2 stations at 0.25 mm: a photo row is 0.35-0.48 mm of z, so a longer gap would be visible as a break",
    "LP_alar_depth_min_mm": "the alar groove is 'barely marked' (IMAIOS) but present: spec 0.3-0.5; 0.15 = D2's tail-cut minimum (the person's decision)",
    "LP_alar_fwhm_mm": "spec alar_groove width 0.4-0.9 mm, widened by one 0.15 mm step each side for the section sampling",
    "LP_alar_share": "the path ends fade (last 0.5 mm excluded); 85 % allows the open_end overlap where the section crosses the slit",
    "LP_fold_defect_min": "revised in the proof run (stated): spec_nose's 0.15 FAILED the spec's own design (the v2 analytic vestibule "
                          "with its alar-fold ridge reads 0.109 R / 0.110 L at s 2.5; without the ridge 0.001). Mark = midway, 0.055",
    "LP_fold_side_deg": "spec_nose alar_fold probe: defect on the lateral-dorsal wall (within 60 deg of the ridge direction)",
    "LP_fold_clear_min_mm": "spec_nose alar_fold probe: the fold must not close the lumen (clear width >= 0.4 mm)",
    "IP_cone_deg": "a probe is INSERTED, not slid: every leg within 60 deg of the inward axis keeps an inward component >= 0.5, so a "
                   "grazing slide along a shallow trench cannot count; ONE bend is allowed (push to the wall, redirect) because the "
                   "vestibule turns and the alar fold bulges into it by design (a straight probe cannot pass a turn or a fold)",
    "IP_share_min": "revised after run 1 (stated): the correct case (v3b run 1) reached 100 % in every half; 2 % tolerates isolated "
                    "start points against a wall, while the mask's edge ring alone is 4-13 % of a half, so a structural blind zone "
                    "(v3's tail ramp: 78 / 91 %) cannot hide inside the allowance",
}


def decisions(V, F, label):
    """D1 as written + edge-only (nose_v3_preview.decisions, reused) and D2 (cat_decisions)"""
    import nose_v3_preview as NP
    d1, d1e, d2 = NP.decisions(V, F, label)
    return {"D1_leather_top_as_written": d1, "D1_top_edge_only": d1e, "D2_nostril_tails": d2}


def _lip_zone(P):
    z = P[:, 2]; xc = np.interp(-np.clip(z, NB.GM["z"].min(), NB.GM["z"].max()), -NB.GM["z"], NB.GM["x"])
    return (z >= -24.0) & (z <= -16.0) & (np.abs(P[:, 0]) <= 12) & (P[:, 1] < -55) & (np.abs(P[:, 0] - xc) > 1.5) & ~NB.edit_zone(P, 1.0)


def lip_form(V, F, Vr, Fr):
    """LIP: the lip zone (z -24..-16, |x| <= 12, front) outside the fixed zones (median-groove band |x - xc| <= 1.5,
    nostril edit zone): exact two-sided distance between this mesh and feat_nose_v3's preview"""
    import cat_decisions as CD
    nA = vnormals(V, F); nB = vnormals(Vr, Fr)
    a = _lip_zone(V) & (nA[:, 1] < -0.2); b = _lip_zone(Vr) & (nB[:, 1] < -0.2)
    da, _ = CD.mesh_dist(Vr, Fr)(V[a]); db, _ = CD.mesh_dist(V, F)(Vr[b])
    mx = float(max(da.max() if len(da) else 0, db.max() if len(db) else 0))
    return {"decision": "lip form kept (R-M / BRIEF: within 0.5 mm of v3 outside the fixed zones)", "status": "PASS" if mx <= MARKS["LIP_max_mm"] else "FAIL",
            "n_this_to_v3": int(a.sum()), "n_v3_to_this": int(b.sum()),
            "this_to_v3_p99_max_mm": [round(float(np.percentile(da, 99)), 4), round(float(da.max()), 4)] if len(da) else None,
            "v3_to_this_p99_max_mm": [round(float(np.percentile(db, 99)), 4), round(float(db.max()), 4)] if len(db) else None,
            "worst_point_mm": np.round(V[a][np.argmax(da)], 2).tolist() if len(da) else None,
            "gate": f"max two-sided distance <= {MARKS['LIP_max_mm']} mm", "label": "checked"}


# ================================================================== LP: lines present
def _straight_edge(u, t, ok, lip_lo, lip_hi):
    """groove depth by a STRAIGHT EDGE laid across it, touching the two lips: on each side the most outward point (smallest
    ray distance t) with lip_lo <= |u| <= lip_hi; depth = max of t below that chord between the lips; FWHM around it.
    Threshold-free and valid on a slope or a step (nose_basins v2's straight-edge rule)."""
    L_ = ok & (u <= -lip_lo) & (u >= -lip_hi); R_ = ok & (u >= lip_lo) & (u <= lip_hi)
    if L_.sum() < 3 or R_.sum() < 3:
        return None
    a = np.flatnonzero(L_)[np.argmin(t[L_])]; b = np.flatnonzero(R_)[np.argmin(t[R_])]
    chord = t[a] + (t[b] - t[a]) * (u - u[a]) / (u[b] - u[a]); r = t - chord
    m = ok & (u > u[a]) & (u < u[b])
    if not m.any():
        return None
    k = np.flatnonzero(m)[np.argmax(r[m])]; dep = float(r[k])
    if dep <= 0:
        return dict(depth=0.0, fwhm=0.0, u_bottom=float(u[k]))
    half = r >= dep / 2; lo_ = k; hi_ = k
    while lo_ > a and half[lo_ - 1] and ok[lo_ - 1]:
        lo_ -= 1
    while hi_ < b and half[hi_ + 1] and ok[hi_ + 1]:
        hi_ += 1
    return dict(depth=dep, fwhm=float(u[hi_] - u[lo_] + (u[1] - u[0])), u_bottom=float(u[k]))


def _groove_section(tr, O, D, u, lip_lo, lip_hi):
    t, _ = tr(O, D); ok = np.isfinite(t)
    if ok.sum() < 0.8 * len(u):
        return None
    return _straight_edge(u, t, ok, lip_lo, lip_hi)


def lines_median(tr, dz=0.25):
    GM = NB.GT; z = np.arange(-9.8, -18.5 - 1e-9, -dz); rows = []; ok_all = []
    u = np.arange(-2.2, 2.2001, 0.02)
    for zz in z:
        xc = float(np.interp(-zz, -GM["z"], GM["x"])); tgt_d = float(np.interp(-zz, -GM["z"], GM["depth"])); tgt_w = float(np.interp(-zz, -GM["z"], GM["fwhm"]))
        O = np.c_[xc + u, np.full(len(u), -95.0), np.full(len(u), zz)]; D = np.tile([0, 1.0, 0], (len(u), 1))
        s = _groove_section(tr, O, D, u, 0.3, 1.4)
        if s is None:
            rows.append(dict(z=round(float(zz), 2), status="FAIL", reason="no section")); ok_all.append(False); continue
        okd = MARKS["LP_depth_rel"][0] * tgt_d <= s["depth"] <= MARKS["LP_depth_rel"][1] * tgt_d
        okw = MARKS["LP_fwhm_rel"][0] * tgt_w <= s["fwhm"] <= MARKS["LP_fwhm_rel"][1] * tgt_w
        okx = abs(s["u_bottom"]) <= 0.4
        rows.append(dict(z=round(float(zz), 2), depth=round(s["depth"], 3), target_depth=round(tgt_d, 3), fwhm=round(s["fwhm"], 3), target_fwhm=round(tgt_w, 3),
                         x_bottom=round(xc + s["u_bottom"], 2), status="PASS" if okd and okw and okx else "FAIL"))
        ok_all.append(okd and okw and okx)
    ok_all = np.array(ok_all); share = float(ok_all.mean()); run = 0; worst = 0
    for o in ok_all:
        run = 0 if o else run + 1; worst = max(worst, run)
    st = share >= MARKS["LP_station_share"] and worst * dz <= MARKS["LP_gap_mm"]
    dep = np.array([r.get("depth", 0) for r in rows]); fw = np.array([r.get("fwhm", 0) for r in rows])
    return dict(status="PASS" if st else "FAIL", stations=len(rows), share_pass=round(share, 3), longest_fail_run_mm=round(worst * dz, 2),
                depth_p10_p50_p90_mm=np.round(np.percentile(dep, [10, 50, 90]), 3).tolist(), fwhm_p10_p50_p90_mm=np.round(np.percentile(fw, [10, 50, 90]), 3).tolist(),
                rows=rows)


def lines_alar(V, F, ref_closest, tr=None, ds=0.25):
    """comma tail = alar groove along open_end -> tail_tip -> approved corner (the D2 path). Sections ACROSS the path in the
    v1 reference frame (cat_decisions.check_nostril_tails' normals), rays onto the TESTED surface, depth by a straight edge
    on the lips (|u| 0.25-1.2). Run-1 revisions (stated): a quadratic of the shoulders was ill-posed where the path rides
    the leather->fur step; a v1-relative inset was biased inside the dish fill (L first leg read negative). Each station
    now reads BOTH (two methods, M5) and keeps the larger, since each is biased low only in its stated zone."""
    import cat_decisions as CD
    tr = tr or Tracer(V, F); md = CD.mesh_dist(V, F); out = {}; allok = True; u = np.arange(-1.6, 1.6001, 0.02)
    for sd, path in N3.tail_paths().items():
        seg = np.linalg.norm(np.diff(path, axis=0), axis=1); Lp = seg.sum(); s = np.arange(0, Lp - 0.5 + 1e-9, ds)
        cum = np.r_[0, np.cumsum(seg)]; X = np.c_[[np.interp(s, cum, path[:, k]) for k in range(3)]].T
        T = np.gradient(X, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
        Xs, Nn, _ = ref_closest(X); lat = np.cross(Nn, T); lat /= np.linalg.norm(lat, axis=1, keepdims=True)
        # method 2 (M5): inset below v1 relative to the shoulders (|u| >= 1.2): valid on the leather->fur step, biased LOW in the
        # dish fill; method 1 (straight edge on the tested surface): valid on the plug, biased LOW on a convex step -> max
        Q = (Xs[:, None, :] + u[None, :, None] * lat[:, None, :]).reshape(-1, 3); Qs, _, _ = ref_closest(Q)
        _, sdv = md(Qs); ins = sdv.reshape(len(X), len(u))
        rows = []; oks = []
        for x, n, l, iv in zip(Xs, Nn, lat, ins):
            O = x[None] + u[:, None] * l[None] + 3.0 * n[None]; D = np.tile(-n, (len(u), 1))
            r = _groove_section(tr, O, D, u, 0.25, 1.2)
            prof = iv - np.median(iv[np.abs(u) >= 1.2]); mm = np.abs(u) < 0.7; k = np.flatnonzero(mm)[np.argmax(prof[mm])]; d2 = float(prof[k])
            half = prof >= d2 / 2; a_ = k; b_ = k
            while a_ > 0 and half[a_ - 1]:
                a_ -= 1
            while b_ < len(u) - 1 and half[b_ + 1]:
                b_ += 1
            r2 = dict(depth=d2, fwhm=float(u[b_] - u[a_] + 0.02) if d2 > 0 else 0.0)
            if r is None or r2["depth"] > r["depth"]:
                r = r2; meth = "v1rel"
            else:
                meth = "edge"
            ok = r["depth"] >= MARKS["LP_alar_depth_min_mm"] and (MARKS["LP_alar_fwhm_mm"][0] <= r["fwhm"] <= MARKS["LP_alar_fwhm_mm"][1] or r["depth"] >= 1.0)
            rows.append([round(r["depth"], 3), round(r["fwhm"], 3), meth]); oks.append(ok)
        oks = np.array(oks); share = float(oks.mean()); ok = share >= MARKS["LP_alar_share"]; allok &= ok
        out[sd] = dict(status="PASS" if ok else "FAIL", stations=len(rows), share_pass=round(share, 3), path_mm=round(float(Lp), 2),
                       depth_fwhm_every_0p5=[rows[i] for i in range(0, len(rows), 2)])
    out["status"] = "PASS" if allok else "FAIL"; return out


def lines_fold(tr, nth=180, sides=None):
    """sides: the builder's centrelines (objects with s, cl, T, A, B); default the v2 spec centreline (v2 / v3 builds)"""
    from scipy.spatial import ConvexHull
    out = {}; allok = True
    for sd in ("R", "L"):
        S2 = (sides or V2.SIDES)[sd]; lat = np.array([-1.0 if sd == "R" else 1.0, 0, 0]); rows = []
        for s0 in (1.5, 2.5, 3.5):
            i = int(np.argmin(np.abs(S2.s - s0))); C = S2.cl[i]; T = S2.T[i]; A = S2.A[i]; B = S2.B[i]
            th = np.linspace(0, 2 * np.pi, nth, endpoint=False); Dd = np.cos(th)[:, None] * A + np.sin(th)[:, None] * B
            t, fid = tr(np.tile(C, (nth, 1)), Dd, tmax=4.0); hit = np.isfinite(t)
            inside_tissue = bool(hit.any() and np.mean(np.einsum("ij,ij->i", tr.fn[fid[hit]], Dd[hit]) > 0) > 0.5)
            r = np.where(hit, t, 4.0)
            if inside_tissue or r.min() < 0.05:
                rows.append(dict(s=s0, status="FAIL", reason="centreline point in tissue (sealed)" if inside_tissue else "wall at the centreline")); allok = False; continue
            P2 = np.c_[r * np.cos(th), r * np.sin(th)]; area = 0.5 * abs(np.dot(P2[:, 0], np.roll(P2[:, 1], -1)) - np.dot(P2[:, 1], np.roll(P2[:, 0], -1)))
            hull = ConvexHull(P2); harea = hull.volume
            E = P2[hull.vertices]; rh = np.zeros(nth)
            for a_, b_ in zip(E, np.roll(E, -1, 0)):
                d_ = b_ - a_; den = np.cos(th) * d_[1] - np.sin(th) * d_[0]; ok_ = np.abs(den) > 1e-12; dd = np.where(ok_, den, 1)
                tt = (a_[0] * d_[1] - a_[1] * d_[0]) / dd; ww = (a_[0] * np.sin(th) - a_[1] * np.cos(th)) / dd
                good = ok_ & (tt > 0) & (ww >= -1e-9) & (ww <= 1 + 1e-9); rh = np.where(good, np.maximum(rh, tt), rh)
            gap = rh - r; k = int(np.argmax(gap)); dvec = Dd[k]
            ridge = lat * np.cos(np.radians(45)) + np.array([0, 0, 1.0]) * np.sin(np.radians(45)); ridge = ridge - (ridge @ T) * T; ridge /= np.linalg.norm(ridge)
            ang = float(np.degrees(np.arccos(np.clip(dvec @ ridge, -1, 1)))); defect = float((harea - area) / harea)
            clear = float(np.min(r[: nth // 2] + r[nth // 2:]))
            ok = defect >= MARKS["LP_fold_defect_min"] and ang <= MARKS["LP_fold_side_deg"] and clear >= MARKS["LP_fold_clear_min_mm"]
            allok &= ok
            rows.append(dict(s=s0, status="PASS" if ok else "FAIL", defect=round(defect, 3), defect_angle_to_ridge_deg=round(ang, 1),
                             fold_depth_mm=round(float(gap[k]), 3), clear_width_min_mm=round(clear, 3), escaped_rays=int((~hit).sum())))
        out[sd] = rows
    out["status"] = "PASS" if allok else "FAIL"; return out


def lines_present(V, F, tr=None, sides=None):
    import cat_decisions as CD
    tr = tr or Tracer(V, F); rv, rf = CD.v1_nose(); cl = CD.Closest(rv, rf)
    med = lines_median(tr); ala = lines_alar(V, F, cl, tr); fold = lines_fold(tr, sides=sides)
    st = all(x["status"] == "PASS" for x in (med, ala, fold))
    return dict(status="PASS" if st else "FAIL", median_groove=med, alar_groove=ala, alar_fold=fold,
                label="checked (sections on the mesh); targets estimated (photo + cited, spec_nose_v3b.json)")


# ================================================================== NW: no artefact wrinkles (N5 with a measured floor)
NW_DEG = 3   # revised (stated): quadratic windows read the stem's own non-quadratic FORM (v3 0.014-0.016 at the stem side,
             # a floor built on a smoothed form under-reads it); a cubic removes form to third order, while a wrinkle of
             # <= 0.8 mm period (>= 2 periods per 1.6 mm window) cannot be fitted by it
def nw_measure(V, F, subtract_design=False, R=0.8, step=0.3, band_x=np.arange(-4.0, 4.01, 0.5), tr=None, deg=NW_DEG):
    from scipy.spatial import cKDTree
    n = vnormals(V, F); od = NB.outline_dist(V); tree = cKDTree(V)
    if subtract_design:
        nb_ = tree.query_ball_point(V, 0.4); ns = np.array([n[j].mean(0) for j in nb_]); ns /= np.linalg.norm(ns, axis=1, keepdims=True)
        rel = NB.declared_relief(V); Vc = V - rel[:, None] * ns
    else:
        Vc = V
    m = (od < -0.8) & (n[:, 1] < -0.2) & (V[:, 1] < -64) & ~NB.line_zone(V)
    # the OUTER leather sheet only: a vertex counts if nothing lies in front of it along -y (run-1 revision, stated: the
    # vestibule walls behind the leather passed the normal / outline filters and dominated the worst windows)
    tr = tr or Tracer(V, F); idx = np.flatnonzero(m); th, _ = tr(V[idx] + 0.05 * n[idx], np.tile([0, -1.0, 0], (len(idx), 1)), tmax=40.0)
    m[idx[np.isfinite(th)]] = False
    P = Vc[m]; Nn = n[m]
    if len(P) < 50:
        return dict(reason="no leather vertices", rms_p95_mm=None)
    treec = cKDTree(Vc)
    key = np.floor(P / step).astype(np.int64); _, first = np.unique(key, axis=0, return_index=True); C = P[first]; CN = Nn[first]
    rms = []
    for c, cn in zip(C, CN):
        ii = treec.query_ball_point(c, R)
        if len(ii) < 12:
            continue
        X = Vc[ii] - c; X = X[np.abs(X @ cn) < 0.6]
        if len(X) < 12:
            continue
        t1 = np.cross(cn, [1, 0, 0] if abs(cn[0]) < 0.9 else [0, 1, 0]); t1 /= np.linalg.norm(t1); t2 = np.cross(cn, t1)
        uu, vv, hh = X @ t1, X @ t2, X @ cn; A = np.c_[np.ones_like(uu), uu, vv, uu * uu, uu * vv, vv * vv]
        if deg == 3:
            A = np.c_[A, uu ** 3, uu * uu * vv, uu * vv * vv, vv ** 3]
        co, *_ = np.linalg.lstsq(A, hh, rcond=None); rms.append(np.sqrt(np.mean((hh - A @ co) ** 2)))
    rms = np.array(rms); bands = []
    z = np.arange(-2.5, -6.5, -0.02)
    for x0 in band_x:
        O = np.c_[np.full(len(z), x0), np.full(len(z), -95.0), z]; t, fid = tr(O, np.tile([0, 1.0, 0], (len(z), 1)))
        if not np.isfinite(t).all():
            continue
        y = -95.0 + t
        if subtract_design:
            Ph = O + t[:, None] * np.array([0, 1.0, 0]); ny = np.abs(tr.fn[fid][:, 1]); y = y + NB.declared_relief(Ph) / np.maximum(ny, 0.3)
        c = np.polyfit(z, y, 4); r = y - np.polyval(c, z); r -= r.mean()
        Fr = np.abs(np.fft.rfft(r * np.hanning(len(r)))) * 4 / len(r); f = np.fft.rfftfreq(len(r), 0.02)
        bands.append(float(np.sqrt(np.sum(Fr[(f >= 1.5) & (f < 6)] ** 2))))
    bands = np.array(bands)
    return dict(leather_verts=int(m.sum()), centres=int(len(rms)), rms_p50_mm=round(float(np.median(rms)), 5), rms_p95_mm=round(float(np.percentile(rms, 95)), 5),
                rms_max_mm=round(float(rms.max()), 5), band_profiles=int(len(bands)),
                band_amp_p50_mm=round(float(np.median(bands)), 5) if len(bands) else None, band_amp_max_mm=round(float(bands.max()), 5) if len(bands) else None)


def floor_case(grid=0.10, ripple=None, cobbles=True):
    """the CORRECT case for NW: this nose's FORM (the base field Gaussian-smoothed, sigma 0.4 mm: no sub-mm artefacts) +
    the DECLARED design (cobbles + median groove cut, feat_nose_v3b.declared_relief) applied as edit() does, meshed by the
    same marching cubes at `grid`. ripple = (amp, period, axis)
    plants an artefact along the normal on the leather and its band."""
    from scipy import ndimage
    from skimage.measure import marching_cubes
    lo = np.array([-9.5, -77.0, -17.5]); hi = np.array([9.5, -62.5, -1.5]); Fb = base_field(lo, hi)
    n = np.floor((hi - lo) / grid).astype(int) + 1; ax = [lo[d] + grid * np.arange(n[d]) for d in range(3)]
    P = np.stack(np.meshgrid(*ax, indexing="ij"), -1).reshape(-1, 3); Fv = Fb(P).reshape(tuple(n))
    Fs = ndimage.gaussian_filter(Fv, 0.4 / grid, mode="nearest")
    gx, gy, gz = np.gradient(Fs, grid); G = np.sqrt(gx ** 2 + gy ** 2 + gz ** 2).ravel(); Fs = Fs.ravel()
    near = np.abs(Fs) < 1.5
    if cobbles:
        rel = np.zeros(len(P)); rel[near] = NB.declared_relief(P[near]); Fs = Fs - rel * G
    if ripple is not None:
        amp, per, axis = ripple; Fs = Fs - amp * np.sin(2 * np.pi * P[:, axis] / per) * G * (NB.outline_dist(P) < 1.5)
    Ff = Fs.reshape(tuple(n)).astype(np.float32); Ff[0], Ff[-1], Ff[:, 0], Ff[:, -1], Ff[:, :, 0], Ff[:, :, -1] = 10, 10, 10, 10, 10, 10
    v, f, _, _ = marching_cubes(Ff, 0.0, spacing=(grid,) * 3); f = f[:, ::-1].astype(np.int64); V = v + lo
    nn = vnormals(V, f)
    if np.median(nn[(V[:, 1] < -70) & (np.abs(V[:, 0]) < 3), 1]) > 0:
        f = f[:, ::-1]
    bd = np.any((V < lo + 2 * grid) | (V > hi - 2 * grid), axis=1); f = f[~bd[f].any(1)]
    idx = np.unique(f); rm = -np.ones(len(V), np.int64); rm[idx] = np.arange(len(idx)); return V[idx], rm[f]


# ================================================================== IP: into passage
def _fib_cone(n, deg):
    i = np.arange(n) + 0.5; cz = 1 - (1 - np.cos(np.radians(deg))) * i / n; ph = np.pi * (1 + 5 ** 0.5) * i
    sz = np.sqrt(1 - cz ** 2); return np.c_[sz * np.cos(ph), sz * np.sin(ph), cz]


def opening_pixels(tr, sd, px=0.04, depth=0.6):
    """N1's opening (nose_v3_preview.opening_mask) on the grid tracer: rays along the rim-plane normal from 6 mm out;
    opening = first hit >= `depth` below the v2 plug-top envelope (or no hit at all)"""
    from scipy import ndimage
    S = V2.SIDES[sd]; rim_uv = np.c_[(S.rim - S.c) @ S.u1, (S.rim - S.c) @ S.u2]
    a0, b0 = rim_uv.min(0) - 1.0; a1, b1 = rim_uv.max(0) + 1.0
    au = np.arange(a0, a1, px); bu = np.arange(b0, b1, px); AA, BB = np.meshgrid(au, bu, indexing="ij"); uv = np.c_[AA.ravel(), BB.ravel()]
    d2 = S.poly(uv); keep = d2 < 0.5; uvk = uv[keep]
    O = S.c + uvk[:, :1] * S.u1 + uvk[:, 1:] * S.u2 + 6.0 * S.nrm; t, _ = tr(O, np.tile(-S.nrm, (len(O), 1)))
    t_env = 6.0 - V2.DOME_MM * V2.ss(-d2[keep] / 1.5); dep = t - t_env
    op = (np.isfinite(dep) & (dep >= depth)) | ~np.isfinite(t)
    mask = np.zeros(len(uv), bool); mask[np.flatnonzero(keep)[op]] = True; mask = mask.reshape(AA.shape)
    edge = (mask & ~ndimage.binary_erosion(mask)).ravel()[np.flatnonzero(keep)[op]]
    X0 = O[op] - (t_env[op] + depth)[:, None] * S.nrm
    return dict(X0=X0, uv=uvk[op], edge=edge)


def into_passage(V, F, tr=None, ndir=240, cap=40.0, legs=2, n1=60, n2=120):
    tr = tr or Tracer(V, F); out = {}; allok = True
    for sd in ("R", "L"):
        S = V2.SIDES[sd]; OP = opening_pixels(tr, sd)
        if not len(OP["X0"]):
            out[sd] = dict(status="FAIL", reason="no opening"); allok = False; continue
        cone = _fib_cone(ndir, MARKS["IP_cone_deg"]); w = -S.nrm
        e1 = np.cross(w, [1.0, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(w, e1); Dd = cone[:, :1] * e1 + cone[:, 1:2] * e2 + cone[:, 2:] * w
        X0 = OP["X0"]; nP = len(X0); best = np.zeros(nP)
        for s in range(0, nP, 4000):
            Xb = X0[s:s + 4000]; O = np.repeat(Xb, ndir, 0); D = np.tile(Dd, (len(Xb), 1)); t, _ = tr(O, D, tmax=cap)
            best[s:s + 4000] = np.where(np.isfinite(t), t, cap).reshape(len(Xb), ndir).max(1)
        travel1 = 0.6 + best; travel = travel1.copy()
        if legs == 2:                     # one bend: push until the wall (pulled back 0.05 mm), redirect, both legs in the cone
            short = np.flatnonzero(travel1 < NB.D_VEST); D1 = Dd[::max(ndir // n1, 1)]; D2 = Dd[::max(ndir // n2, 1)]
            for s in range(0, len(short), 200):
                ii = short[s:s + 200]; O = np.repeat(X0[ii], len(D1), 0); D = np.tile(D1, (len(ii), 1)); t1, _ = tr(O, D, tmax=cap)
                t1 = np.where(np.isfinite(t1), t1, cap); Bp = O + np.maximum(t1 - 0.05, 0)[:, None] * D
                t2, _ = tr(np.repeat(Bp, len(D2), 0), np.tile(D2, (len(Bp), 1)), tmax=cap); t2 = np.where(np.isfinite(t2), t2, cap).reshape(len(Bp), len(D2)).max(1)
                tot = (np.maximum(t1 - 0.05, 0) + t2).reshape(len(ii), len(D1)).max(1)
                travel[ii] = np.maximum(travel[ii], 0.6 + tot)
        H_uv = np.array([(S.H - S.c) @ S.u1, (S.H - S.c) @ S.u2]); Oe = np.array([(S.open_end - S.c) @ S.u1, (S.open_end - S.c) @ S.u2])
        tail = np.linalg.norm(OP["uv"] - Oe, axis=1) < np.linalg.norm(OP["uv"] - H_uv, axis=1)
        res = {}
        for nm, m in (("head_half", ~tail), ("tail_half", tail)):
            if not m.any():
                res[nm] = dict(status="FAIL", pixels=0); allok = False; continue
            sh = float((travel[m] >= NB.D_VEST).mean()); ok = sh >= MARKS["IP_share_min"]; allok &= ok
            mi = m & ~OP["edge"]
            res[nm] = dict(status="PASS" if ok else "FAIL", pixels=int(m.sum()), share_reaching_d_vest=round(sh, 4),
                           share_straight_probe_only=round(float((travel1[m] >= NB.D_VEST).mean()), 4),
                           travel_p5_p50_mm=np.round(np.percentile(travel[m], [5, 50]), 2).tolist(),
                           boundary_share=round(float(OP["edge"][m].mean()), 4),
                           share_reaching_interior_pixels=round(float((travel[mi] >= NB.D_VEST).mean()), 4) if mi.any() else None)
        bad = travel < NB.D_VEST
        res["short_pixels_uv_p50"] = np.round(np.median(OP["uv"][bad], 0), 2).tolist() if bad.any() else None
        out[sd] = res
    out["status"] = "PASS" if allok else "FAIL"; out["d_vest_mm"] = NB.D_VEST; out["cone_deg"] = MARKS["IP_cone_deg"]; out["legs"] = legs
    return out


def plant_seal(V, F, s0=1.5, radius=2.6):
    """planted failure for IP: a disc of triangles across each vestibule at s0 (the passage sealed)"""
    Vs, Fs = [V], [F]; off = len(V)
    for sd in ("R", "L"):
        S2 = V2.SIDES[sd]; i = int(np.argmin(np.abs(S2.s - s0))); C = S2.cl[i]; A, B = S2.A[i], S2.B[i]
        th = np.linspace(0, 2 * np.pi, 64, endpoint=False); ring = C + radius * (np.cos(th)[:, None] * A + np.sin(th)[:, None] * B)
        Vs.append(np.vstack([C, ring])); k = np.arange(64); Fs.append(np.c_[np.zeros(64, np.int64), 1 + k, 1 + (k + 1) % 64] + off); off += 65
    return np.vstack(Vs), np.vstack(Fs)



# ================================================================== NW proof: floor (correct case) and planted ripples
NW_PLANTS = {"rib_0p01mm_0p5mm_z": (0.010, 0.5, 2), "n5_ripple_0p02mm_0p8mm_x": (0.020, 0.8, 0)}


def nw_floor_and_marks():
    """measure the NW noise floor on the correct case (form smoothed, designed cobbles, same marching cubes, design
    subtracted) and on planted artefacts sized to what NW reads: the measured 2/mm rib (0.0096-0.0113 mm band amplitude on
    the base, so a 0.01 mm sine) and v3's N5 ripple (0.02 mm, 0.8 mm). Mark = midway between floor and the smaller plant."""
    out = {}
    V, F = floor_case(); out["floor_correct"] = nw_measure(V, F, subtract_design=True)
    for nm, rp in NW_PLANTS.items():
        V, F = floor_case(ripple=rp); out["planted_" + nm] = nw_measure(V, F, subtract_design=True)
    marks = {}
    for k, nm in (("rms_p95_mm", "n5_ripple_0p02mm_0p8mm_x"), ("band_amp_max_mm", "rib_0p01mm_0p5mm_z")):
        fl = out["floor_correct"][k]; pl = out["planted_" + nm][k]
        marks[k] = round(fl + 0.5 * (pl - fl), 5); marks[k + "_plant"] = nm; marks[k + "_separation"] = round(pl / max(fl, 1e-9), 2)
    out["marks"] = marks
    out["mark_reason"] = ("each NW metric is sized to the artefact it reads: the interior local-quadratic residual (rms p95) against "
                          "v3's N5 wrinkle plant (0.02 mm, 0.8 mm), the top-band 1.5-6 / mm amplitude against the rib plant (0.01 mm, "
                          "0.5 mm along z = the base cores' measured 2/mm ringing). Mark = midway between the measured correct case "
                          "(this nose's form Gaussian-smoothed 0.4 mm + the designed cobbles, meshed at 0.10 mm, design subtracted) and "
                          "that plant. NW FAILS if either metric is over its mark. Revised after the first proof run (stated): one "
                          "shared 'smaller plant' put the rms mark only 1.29x above its floor")
    return out


def nw_status(meas, marks):
    if meas.get("rms_p95_mm") is None:
        return "FAIL"
    ok = meas["rms_p95_mm"] <= marks["rms_p95_mm"] and (meas["band_amp_max_mm"] is None or meas["band_amp_max_mm"] <= marks["band_amp_max_mm"])
    return "PASS" if ok else "FAIL"


# ================================================================== the run: decisions first, then the checks
def run_checks(floor=None):
    t0 = time.time()
    R = {"epoch_start": int(t0), "marks": MARKS, "mark_reasons": MARK_REASONS, "geometry": NB.geometry_report(),
         "resolution": NB.RESOLUTION, "contract": NB.contract_probe(0.10, 0.10, 0.10), "tracer_selfcheck": trace_selfcheck()}
    if floor is None and os.path.exists(PROOF_JSON):
        floor = json.load(open(PROOF_JSON)).get("NW_floor")
    nwm = floor["marks"] if floor else None
    Vb, Fb_ = load_mesh("feat_nose_v3b_preview.npz"); Vbk, Fbk = load_mesh("feat_nose_v3b_preview.npz", keep_border=True)
    V3, F3 = load_mesh("feat_nose_v3_preview.npz"); V3k, F3k = load_mesh("feat_nose_v3_preview.npz", keep_border=True)
    trb = Tracer(Vb, Fb_); tr3 = Tracer(V3, F3)
    # ---- DECISIONS FIRST
    dec = decisions(Vb, Fb_, "feat_nose_v3b_preview")
    dec["LIP_lip_form_vs_v3"] = lip_form(Vb, Fb_, V3, F3)
    R["DECISIONS"] = dec
    # ---- candidate
    c = {"file": "feat_nose_v3b_preview.npz", "verts": int(len(Vb)), "tris": int(len(Fb_))}
    c["LP_lines_present"] = lines_present(Vb, Fb_, trb, sides=NB.SIDES)
    c["IP_into_passage"] = into_passage(Vbk, Fbk)
    c["NW_no_artefact_wrinkles"] = nw_measure(Vb, Fb_, subtract_design=True, tr=trb)
    if nwm:
        c["NW_no_artefact_wrinkles"]["status"] = nw_status(c["NW_no_artefact_wrinkles"], nwm); c["NW_no_artefact_wrinkles"]["marks"] = nwm
    R["v3b_candidate"] = c
    # ---- the other side of each check (known defects)
    o = {}
    o["feat_nose_v3_preview (IP must FAIL: the blind tail half)"] = {"IP_into_passage": into_passage(V3k, F3k),
                                                                     "LP_lines_present (info)": lines_present(V3, F3, tr3),
                                                                     "NW (info)": nw_measure(V3, F3, tr=tr3)}
    if nwm:
        o["feat_nose_v3_preview (IP must FAIL: the blind tail half)"]["NW (info)"]["status"] = nw_status(o["feat_nose_v3_preview (IP must FAIL: the blind tail half)"]["NW (info)"], nwm)
    if os.path.exists(os.path.join(L, "skin_v3_nose_crop_v3b.npz")):
        Vs, Fs = load_mesh("skin_v3_nose_crop_v3b.npz"); trs = Tracer(Vs, Fs)
        o["skin_v3 (LP must FAIL: the smoothed nose)"] = {"LP_lines_present": lines_present(Vs, Fs, trs), "NW (info)": nw_measure(Vs, Fs, tr=trs)}
        if nwm:
            o["skin_v3 (LP must FAIL: the smoothed nose)"]["NW (info)"]["status"] = nw_status(o["skin_v3 (LP must FAIL: the smoothed nose)"]["NW (info)"], nwm)
    R["other_side"] = o
    R["seconds"] = round(time.time() - t0, 1); R["epoch_end"] = int(time.time())
    jdump(R, OUT_JSON); return R


def run_proofs():
    """A22 both sides for every check this file adds: planted defects must FAIL, correct cases must PASS"""
    t0 = time.time(); P = {"epoch_start": int(t0)}
    P["tracer_selfcheck"] = trace_selfcheck()
    P["NW_floor"] = nw_floor_and_marks(); m = P["NW_floor"]["marks"]
    P["NW_status"] = {"floor_correct (must PASS)": nw_status(P["NW_floor"]["floor_correct"], m)}
    for nm in NW_PLANTS:
        P["NW_status"][f"planted_{nm} (must FAIL)"] = nw_status(P["NW_floor"]["planted_" + nm], m)
    # LP: planted = the v3b build WITHOUT its lines (median groove + alar groove), correct = the v3b build
    Vn, Fn = load_mesh("feat_nose_v3b_plant_nolines.npz"); lp = lines_present(Vn, Fn, sides=NB.SIDES)
    P["LP_planted_lines_absent (must FAIL)"] = {"status": lp["status"], "median": lp["median_groove"]["status"], "median_share": lp["median_groove"]["share_pass"],
                                                "alar": lp["alar_groove"]["status"], "alar_share": {sd: lp["alar_groove"][sd]["share_pass"] for sd in "RL"},
                                                "fold (kept in the plant)": lp["alar_fold"]["status"]}
    # LP fold: planted = the v3b build with each vestibule's fold removed is not built; the fold side is proven by skin_v3 /
    # v3 (see run_checks) and by a synthetic convex lumen below
    th = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    P["LP_fold_synthetic"] = _fold_synthetic(th)
    # IP: planted = v3b with both vestibules sealed by a disc at s 1.5
    Vk, Fk = load_mesh("feat_nose_v3b_preview.npz", keep_border=True); Vs, Fs = plant_seal(Vk, Fk)
    ip = into_passage(Vs, Fs); P["IP_planted_sealed_at_s1.5 (must FAIL)"] = {sd: {h: ip[sd][h]["share_reaching_d_vest"] for h in ("head_half", "tail_half")} for sd in "RL"}
    P["IP_planted_sealed_at_s1.5 (must FAIL)"]["status"] = ip["status"]
    P.update(lip_proof())
    P["seconds"] = round(time.time() - t0, 1); P["epoch_end"] = int(time.time())
    jdump(P, PROOF_JSON); return P


def lip_proof(push=0.6):
    """LIP both sides: v3 against itself must PASS (0 mm); v3 with its lip zone pushed out `push` mm along the normals
    (just over the person's 0.5 mm) must FAIL"""
    V3, F3 = load_mesh("feat_nose_v3_preview.npz"); same = lip_form(V3, F3, V3, F3)
    n = vnormals(V3, F3); z = _lip_zone(V3) & (n[:, 1] < -0.2); Vp = V3.copy(); Vp[z] = Vp[z] + push * n[z]
    moved = lip_form(Vp, F3, V3, F3)
    return {"LIP_v3_vs_itself (must PASS)": {"status": same["status"], "max": same["this_to_v3_p99_max_mm"]},
            f"LIP_planted_lip_pushed_{push}mm (must FAIL)": {"status": moved["status"], "max": moved["this_to_v3_p99_max_mm"]}}


def _fold_synthetic(th, s0=2.5):
    """the fold metric on the DESIGN itself: the v2 analytic vestibule section at s0 with its alar-fold ridge (the spec's
    correct case, must PASS) and the same lumen without the ridge (planted 'no fold', must FAIL); r(theta) = first zero of
    the analytic air field along each in-plane ray"""
    from scipy.spatial import ConvexHull
    out = {}
    for sd in ("R", "L"):
        S = V2.SIDES[sd]; i = int(np.argmin(np.abs(S.s - s0))); C = S.cl[i]; A, B = S.A[i], S.B[i]
        Dd = np.cos(th)[:, None] * A + np.sin(th)[:, None] * B; t = np.arange(0.01, 4.0, 0.005)
        P = C[None, None, :] + t[None, :, None] * Dd[:, None, :]; P = P.reshape(-1, 3)
        for nm, fld in (("with_fold (must PASS)", lambda Q: V2.smax(S.lumen(Q), -S.ridge_sdf(Q), 0.08)), ("no_fold (must FAIL)", S.lumen)):
            f = fld(P).reshape(len(th), len(t)); r = np.array([t[np.argmax(row >= 0)] if (row >= 0).any() else 4.0 for row in f])
            P2 = np.c_[r * np.cos(th), r * np.sin(th)]; area = 0.5 * abs(np.dot(P2[:, 0], np.roll(P2[:, 1], -1)) - np.dot(P2[:, 1], np.roll(P2[:, 0], -1)))
            h = ConvexHull(P2).volume; defect = (h - area) / h; clear = float(np.min(r[: len(th) // 2] + r[len(th) // 2:]))
            ok = defect >= MARKS["LP_fold_defect_min"] and clear >= MARKS["LP_fold_clear_min_mm"]
            out[f"{sd}_{nm}"] = dict(status="PASS" if ok else "FAIL", defect=round(float(defect), 3), clear_mm=round(clear, 3))
    return out


def render_views(out_png=None):
    """the person-facing look: v3b vs v3 vs skin_v3 at full detail (AO), nostril close-ups and a cut through the passage"""
    out_png = out_png or os.path.join(L, "feat_nose_v3b_views.png"); rows = []
    for fn, lab in (("feat_nose_v3b_preview.npz", "v3b"), ("feat_nose_v3_preview.npz", "v3"), ("skin_v3_nose_crop_v3b.npz", "skin_v3")):
        if not os.path.exists(os.path.join(L, fn)):
            continue
        V, F = load_mesh(fn); tr = Tracer(V, F); imgs = []; labs = []
        for d, up, c, sz, nm in (((-0.038, 0.971, -0.236), (0, 0, 1), (0, -70, -10.5), (22, 20), "front, photo view"),
                                 ((0.62, 0.72, -0.3), (0, 0, 1), (-5.2, -68.5, -9.3), (9, 8), "R nostril"),
                                 ((-0.6, 0.74, -0.3), (0, 0, 1), (4.3, -69.5, -9.6), (9, 8), "L nostril")):
            img, _, _ = render_ao(V, F, d, up, sz[0] / 520, c, sz, tracer=tr, ao_reach=8.0); imgs.append(img); labs.append(f"{lab}: {nm}")
        keep = V[F].mean(1)[:, 0] > -3.3; Fk = F[keep]
        img, _, _ = render_ao(V, Fk, (1, 0, 0), (0, 0, 1), 28 / 520, (-3.3, -61, -6), (28, 16), tracer=Tracer(V, Fk), ao_reach=8.0)
        imgs.append(img); labs.append(f"{lab}: cut x > -3.3 (R passage), from the side")
        fnr = os.path.join(L, f"_tmp_{lab}.png"); save_png(imgs, fnr, labels=labs); rows.append(fnr)
    from PIL import Image
    ims = [Image.open(f) for f in rows]; W = max(i.width for i in ims); H = sum(i.height for i in ims) + 4 * len(ims)
    canvas = Image.new("RGB", (W, H), (40, 40, 40)); y = 0
    for i, f in zip(ims, rows):
        canvas.paste(i, (0, y)); y += i.height + 4; os.remove(f)
    canvas.save(out_png); return out_png


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "preview":
        run_preview(float(sys.argv[2]) if len(sys.argv) > 2 else 0.10, sys.argv[3] if len(sys.argv) > 3 else "all",
                    sys.argv[4] if len(sys.argv) > 4 else "feat_nose_v3b_preview")
    elif cmd == "crop_skin_v3":
        crop_skin_v3()
    elif cmd == "selfcheck":
        print(trace_selfcheck())
    elif cmd == "prove":
        P = run_proofs(); print(json.dumps({k: v for k, v in P.items() if k != "NW_floor"}, indent=1, default=str)); print(json.dumps(P["NW_floor"]["marks"]))
    elif cmd == "check":
        R = run_checks(); print("written", OUT_JSON, R["seconds"], "s")
    elif cmd == "render":
        print(render_views())
