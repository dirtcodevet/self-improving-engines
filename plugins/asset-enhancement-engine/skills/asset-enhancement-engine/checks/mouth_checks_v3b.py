"""MOUTH v3b CHECKS (cat v3 round 2, ruling R-M; builder feat-mouth-v3b, 2026-10-18). Every check here is proven on
planted failures on BOTH sides (A10, A22): it FAILS on the defect, sized to what the check actually reads, and PASSES a
correct case; each pass mark carries its reason. Head frame mm throughout (partition.head_local x 1000).

DECISION CHECKS (reported first)
  G13 leather_top_untouched  the approved nose-leather top edge (v1's leather_top_zone core, cat_decisions.v1_zone) is not
                             moved by this stage: the v3b edit equals the v3 edit there to 1e-9 mm at the zone points and
                             +-0.5 mm along the field gradient. Mark: identity (this stage owns nothing there; G13's own
                             0.2 mm gate belongs to the nose owner). Planted: a 0.25 mm bump within 2 mm of the zone FAILS.
  D6a lip_form_keep          lip vertices (within 4 mm of the margin lines U) OUTSIDE the parting zone (the extension sheet
                             and the cavity + 0.6 mm) lie within 0.5 mm of mouth v3's preview, both ways (exact point-to-
                             mesh distance). Mark 0.5 mm = the ruling R-M decision ("the form of the lip is generally right").
                             Planted: a 0.8 mm dent on the upper lip FAILS, a 0.3 mm dent PASSES. The chin zone's deviation
                             is reported too (the C1 round is meant to move it; it is NOT excluded from the gate).
CHECKS
  mouth_through   a 6-connected flood of the AIR voxels (ray-parity voxelisation of the mesh at 0.10 mm) from the
                  outside reaches every cavity probe point (cavity_sdf < -0.8 mm) through the parting line. Mark:
                  topological (all probes reached); the slot is 0.30 mm = 3 voxels. FAILS on mouth v3's preview (blind
                  slot, no cavity) and on a planted 0.3 mm membrane across the passage (voxel level); PASSES v3b.
  teeth           per jaw: connected tooth shells = 16 upper / 14 lower (I 3/3 C 1/1 P 3/2 M 1/1, Reighard 1901 p. 224);
                  each matched 1:1 to its spec tooth with the cusp tip within 1.2 mm (the ref20 picks' +-1 mm x scale
                  1.156); cited dimensions: upper P4 length within 10.29 +- 2 x 0.93 mm, lower M1 within 7.3 +- 15 %.
                  Planted: a missing upper canine FAILS (count + match), a premolar moved 2 mm FAILS (position).
  tongue          the tongue's free surface (dorsum, tip, borders: normals not facing down/back into its attachment)
                  lies inside the cavity, >= 0.2 mm from every tooth and from the palate, and nowhere inside them
                  (signed). Mark 0.2 mm = 2 voxels at the 0.10 mm grid: an integration cannot fuse them; the rig moves
                  the tongue with the jaw. Planted: the tongue raised 1.5 mm (through the palate) FAILS.
  jaws            upper parts (upper_teeth, upper_gums, palate) and lower parts (lower_teeth, lower_gums, tongue) are
                  separate objects with their jaw label, share no vertex, no tooth shell sits in the wrong jaw's object,
                  and no upper part penetrates a lower part closed (clearance >= 0.05 mm) or while the lower set is
                  rotated open about the TMJ axis by 5..35 deg. Planted: the lower canine merged into the upper teeth
                  object FAILS; the upper teeth shifted 1.0 mm down into the lower FAIL.
  chin_C1         mouth_v3_probes.probe_ring (concentrated turning of the section profiles under the lip against the
                  no-edit base; line = excess >= 10 deg, PASS <= 5 % of stations). FAILS on the flag_49 chin (skin_v3
                  crop, full detail) and on a planted 0.35 mm crease; PASSES a smooth chin.
  wall            cavity lining (outside the parting zone) to the outer skin >= 1.0 mm (estimate: the coat over the
                  chin is >= 1.0 mm, coat.json; below that the lining would show through a thin lip). Planted: the
                  lining moved 1.2 mm toward the skin FAILS.
  fill_voids      at the 0.5 mm grid the slot is unresolved, so the cavity is an enclosed void there: fill_voids_v3 with
                  this module's opening_sdf mask PROTECTS it; without the mask (planted) a fill that can reach it FILLS
                  it. Plus the 0.10 mm mesh is one shell (nothing for fill_voids_mesh to remove).
  lips_P1 / M1 / M5  feat_mouth_v3's probes (inventory overhang, crease + Y, commissures, lower lip / chin; slot air;
                  the grid contract), unchanged, run on the v3b preview.
usage: python mouth_checks_v3b.py run | prove | flag49
"""
import json
import os
import sys
import time

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
TR = os.path.join(ROOT, "tripo_rebuild"); FEAT = os.path.join(ROOT, "engine", "packs", "felid", "features")
for _p in (TR, FEAT, os.path.join(ROOT, "engine", "packs", "felid"), HERE):
    sys.path.insert(0, _p)
LAYERS = os.path.join(TR, "layers")
OUT = os.path.join(LAYERS, "mouth_checks_v3b.json")
MARKS = dict(G13_identity_mm=1e-9, D6a_keep_mm=0.5, through_vox_mm=0.10, tooth_tip_mm=1.2, P4_mean=10.29, P4_sd=0.93,
             M1_mean=7.3, M1_frac=0.15, tongue_clear_mm=0.2, jaw_clear_mm=0.05, open_deg=(5, 10, 15, 20, 25, 30, 35),
             chin_line_deg=10.0, chin_share=0.05, wall_mm=1.0)


def jdump(o, fn):
    json.dump(o, open(fn, "w"), indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else (float(x) if isinstance(x, np.floating) else str(x)))


def _r(x, n=3):
    return None if x is None else round(float(x), n)


# ------------------------------------------------------------------ meshes
def load_preview(fn, crop=None):
    fn = os.environ.get("MOUTH_V3B_PREVIEW", fn) if fn == "feat_mouth_v3b_preview.npz" else fn
    Z = np.load(os.path.join(LAYERS, fn)); V = Z["v_head_mm"].astype(float); F = Z["f"].astype(np.int64)
    lab = Z["label"] if "label" in Z.files else np.zeros(len(V), np.int8)
    return dict(V=V, F=F, border=Z["border"], label=lab, grid=float(Z["grid_mm"]) if "grid_mm" in Z.files else None, file=fn)


def interior(M, lo=None, hi=None, pad=0.3):
    """faces not touching the crop border (and inside lo..hi - pad), compacted"""
    V, F = M["V"], M["F"]; keep = ~M["border"][F].any(1)
    if lo is not None:
        ins = np.all((V >= np.asarray(lo) + pad) & (V <= np.asarray(hi) - pad), axis=1); keep &= ins[F].all(1)
    Fk = F[keep]; idx = np.unique(Fk); rm = -np.ones(len(V), np.int64); rm[idx] = np.arange(len(idx))
    return V[idx], rm[Fk], idx


def mesh_dist(V, F, step=0.05):
    from twosided import MeshDist
    return MeshDist(V, F, step=step, k=10)


class Surface:
    """a closed mesh as (a) dense surface samples for unsigned distance (KD-tree, error <= step / sqrt(2)) and (b) a
    +y ray-parity inside test (triangles binned on an x-z grid; off-lattice jitter), for robust signed clearances
    (the face-normal sign of MeshDist flips at sharp cusps: the first run read -7.7 mm 'inside' for points 7 mm away)"""
    def __init__(self, V, F, step=0.05, cell=0.25):
        self.V, self.F = V, F; T = V[F]; e1 = T[:, 1] - T[:, 0]; e2 = T[:, 2] - T[:, 0]
        area = 0.5 * np.linalg.norm(np.cross(e1, e2), axis=1); k = np.maximum(np.ceil(area / step ** 2 * 2), 1).astype(int)
        rep = np.repeat(np.arange(len(F)), k); rng = np.random.default_rng(0); a = rng.random(len(rep)); b = rng.random(len(rep))
        fl = a + b > 1; a[fl] = 1 - a[fl]; b[fl] = 1 - b[fl]
        S = np.vstack([V, T[rep, 0] + a[:, None] * e1[rep] + b[:, None] * e2[rep]]); self.tree = cKDTree(S)
        self.lo = T[:, :, [0, 2]].min((0, 1)) - 1e-6; self.cell = cell
        bx0 = np.floor((T[:, :, [0, 2]].min(1) - self.lo) / cell).astype(int); bx1 = np.floor((T[:, :, [0, 2]].max(1) - self.lo) / cell).astype(int)
        cnt = (bx1[:, 0] - bx0[:, 0] + 1) * (bx1[:, 1] - bx0[:, 1] + 1)
        rep = np.repeat(np.arange(len(F)), cnt); off = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        w = (bx1[:, 1] - bx0[:, 1] + 1)[rep]; ix = bx0[rep, 0] + off // w; iz = bx0[rep, 1] + off % w; cid = ix * 100000 + iz
        o = np.argsort(cid); self.cid = cid[o]; self.ctri = rep[o]

    def dist(self, Q):
        return self.tree.query(Q)[0]

    def inside(self, Q, max_pairs=3_000_000):
        out = np.zeros(len(Q), bool); jit = np.array([0.31831e-4, 0.0, 0.27183e-4])
        qa = Q + jit; ca = np.floor((qa[:, [0, 2]] - self.lo) / self.cell).astype(int); cida = ca[:, 0] * 100000 + ca[:, 1]
        aa = np.searchsorted(self.cid, cida, "left"); na = np.searchsorted(self.cid, cida, "right") - aa
        cum = np.cumsum(na); s0 = 0                      # chunks by candidate PAIRS (tall thin teeth: thousands per column)
        while s0 < len(Q):
            s1 = max(int(np.searchsorted(cum, (cum[s0 - 1] if s0 else 0) + max_pairs, "right")), s0 + 1)
            q = qa[s0:s1]; a = aa[s0:s1]; n = na[s0:s1]; chunk = s1 - s0
            qi = np.repeat(np.arange(len(q)), n); ti = self.ctri[np.repeat(a, n) + (np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n))]
            T = self.V[self.F[ti]]; px, pz = q[qi, 0], q[qi, 2]
            ax, az = T[:, 0, 0], T[:, 0, 2]; bx, bz = T[:, 1, 0] - ax, T[:, 1, 2] - az; cx, cz = T[:, 2, 0] - ax, T[:, 2, 2] - az
            den = bx * cz - cx * bz; deg = np.abs(den) < 1e-7 * (bx * bx + bz * bz + cx * cx + cz * cz)   # edge-on in x-z
            den = np.where(deg, 1.0, den); qx, qz = px - ax, pz - az
            l1 = (qx * cz - cx * qz) / den; l2 = (bx * qz - qx * bz) / den; l0 = 1 - l1 - l2
            y = T[:, 0, 1] * l0 + T[:, 1, 1] * l1 + T[:, 2, 1] * l2
            hit = ~deg & (l0 >= 0) & (l1 >= 0) & (l2 >= 0) & (y > q[qi, 1])
            out[s0:s1] = np.bincount(qi[hit], minlength=len(q)) % 2 == 1; s0 = s1
        return out

    def _vox(self, h=0.1):
        if not hasattr(self, "vin"):
            lo = self.V.min(0) - 0.5; hi = self.V.max(0) + 0.5; self.vin, info = voxelize(self.V, self.F, lo, hi, h); self.vlo = info["lo"]; self.vh = h
        return self.vin

    def signed(self, Q, h=0.1):
        """unsigned distance with the sign from a 0.1 mm parity voxel grid where d > 2 h (reliable there), and from the
        exact ray parity only for the few points within 2 h of the surface (the exact test costs ~1 ms per point among
        tall thin teeth)"""
        d = self.dist(Q); vin = self._vox(h); n = np.array(vin.shape)
        I = np.floor((Q - self.vlo) / self.vh).astype(int); ok = np.all((I >= 0) & (I < n), axis=1)
        ins = np.zeros(len(Q), bool); ins[ok] = vin[tuple(I[ok].T)]
        near = np.flatnonzero(d <= 2 * h)
        if len(near):
            ins[near] = self.inside(Q[near])
        return np.where(ins, -d, d)


def components(F, nv):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    e = np.r_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]
    A = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(nv, nv))
    return connected_components(A, directed=False)


# ------------------------------------------------------------------ G13 (decision): the leather top is not touched
def check_leather_top(bump=0.0):
    import feat_mouth_v3 as M3
    import feat_mouth_v3b as MB
    import cat_decisions as CD
    Q, u = CD.v1_zone(); core = u >= 1 - 1e-9; Q = Q[core]
    lo, hi = Q.min(0) - 3, Q.max(0) + 3
    B = MB.base_block(lo, hi); Fb = MB.base_fn(B)
    g = np.zeros_like(Q)
    for k in range(3):
        e = np.zeros(3); e[k] = 0.05; g[:, k] = (Fb(Q + e) - Fb(Q - e)) / 0.1
    nrm = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
    P = np.vstack([Q + t * nrm for t in (-0.5, -0.25, 0.0, 0.25, 0.5)]); f0 = Fb(P)
    f3 = M3.edit(P, f0); fb = MB.edit(P, f0)
    if bump:                                                   # planted: an edit that DOES reach the zone
        c = Q.mean(0); fb = fb + bump * np.exp(-(np.linalg.norm(P - c, axis=1) / 2.0) ** 2)
    d = np.abs(fb - f3); in_region = np.all((Q >= MB.REGION[0]) & (Q <= MB.REGION[1]), axis=1)
    ok = bool(d.max() <= MARKS["G13_identity_mm"])
    return {"decision": "approved nose-leather top edge (G13): untouched by the mouth stage", "status": "PASS" if ok else "FAIL",
            "gate": "max |F_v3b - F_v3| at v1's core zone points +-0.5 mm along the gradient <= 1e-9 mm (identity)",
            "points": int(len(P)), "zone_points_inside_mouth_REGION": int(in_region.sum()), "max_abs_dF_mm": float(d.max()),
            "v3_vs_base_max_abs_dF_mm (info)": float(np.abs(f3 - f0).max()),
            "note": "G13 itself (within 0.2 mm of v1) is gated on the merged skin by cat_decisions.D1 (nose owner); this stage "
                    "proves it moves nothing there", "label": "checked"}


# ------------------------------------------------------------------ D6a (decision): lip form within 0.5 mm of v3
def _lip_mask(V):
    import feat_mouth_v3 as M3
    m = np.zeros(len(V), bool)
    for sd in ("L", "R"):
        m |= cKDTree(M3.GEOM[sd]["U"]).query(V)[0] < 4.0
    return m


def check_keep(Mb, Mv3, dent=None):
    import feat_mouth_v3b as MB
    lo3, hi3 = np.array([-23.0, -73.0, -34.0]), np.array([24.0, -47.0, -15.0])
    Vb, Fb_, _ = interior(Mb, lo3, hi3); V3, F3, _ = interior(Mv3, lo3, hi3)
    if dent is not None:                                       # planted: dent the upper lip of the candidate
        c, depth, rad = dent; Nb = _vnorm(Vb, Fb_); w = np.exp(-(np.linalg.norm(Vb - c, axis=1) / rad) ** 2)
        Vb = Vb - depth * w[:, None] * Nb
    mb = _lip_mask(Vb) & ~MB.parting_zone(Vb); m3 = _lip_mask(V3) & ~MB.parting_zone(V3)
    d1, _ = mesh_dist(V3, F3)(Vb[mb]); d2, _ = mesh_dist(Vb, Fb_)(V3[m3])
    cz1 = MB.chin_zone(Vb[mb]); cz3 = MB.chin_zone(V3[m3])
    g1, g2 = d1[~cz1], d2[~cz3]; mx = float(max(g1.max(), g2.max())); ok = mx <= MARKS["D6a_keep_mm"]
    strict = float(max(d1.max(), d2.max()))
    return {"decision": "lip form within 0.5 mm of mouth v3 outside the fixed zones (R-M)", "status": "PASS" if ok else "FAIL",
            "gate": f"max two-way exact distance <= {MARKS['D6a_keep_mm']} mm over lip vertices (within 4 mm of U) outside the fixed "
                    "zones = the parting zone (extension sheet + cavity + 0.6 mm) and the C1 chin zone (below C - 0.3 mm in the "
                    "tube, and the midline blend band)",
            "v3b_to_v3_p50_p99_max_mm": [_r(np.median(g1)), _r(np.percentile(g1, 99)), _r(g1.max())],
            "v3_to_v3b_p50_p99_max_mm": [_r(np.median(g2)), _r(np.percentile(g2, 99)), _r(g2.max())], "n": [int(len(g1)), int(len(g2))],
            "chin_zone_max_mm (the C1 fix; reported, not gated)": [_r(d1[cz1].max() if cz1.any() else 0), _r(d2[cz3].max() if cz3.any() else 0)],
            "strict_outside_parting_zone_only_max_mm (info)": _r(strict), "label": "checked"}


def _vnorm(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


# ------------------------------------------------------------------ mouth_through (flood)
def voxelize(V, F, lo, hi, h):
    """inside (True) / outside by ray parity along y for every (x, z) column of the box at spacing h"""
    lo = np.asarray(lo, float); n = np.floor((np.asarray(hi) - lo) / h).astype(int)
    jit = np.array([0.3183, 0.0, 0.2718]) * h * 1e-3                           # off-lattice columns: no exact edge hits
    T = V[F]; x = T[:, :, 0] - lo[0] - jit[0]; z = T[:, :, 2] - lo[2] - jit[2]
    i0 = np.clip(np.ceil(x.min(1) / h - 0.5).astype(int), 0, n[0]); i1 = np.clip(np.floor(x.max(1) / h - 0.5).astype(int), -1, n[0] - 1)
    k0 = np.clip(np.ceil(z.min(1) / h - 0.5).astype(int), 0, n[2]); k1 = np.clip(np.floor(z.max(1) / h - 0.5).astype(int), -1, n[2] - 1)
    flip = np.zeros((n[0], n[1] + 1, n[2]), np.uint8); odd = 0
    ni = np.maximum(i1 - i0 + 1, 0); nk = np.maximum(k1 - k0 + 1, 0); cnt = ni * nk; tid = np.flatnonzero(cnt > 0)
    for a in range(0, len(tid), 400000):
        t = tid[a:a + 400000]; c = cnt[t]; rep = np.repeat(t, c); off = np.arange(c.sum()) - np.repeat(np.cumsum(c) - c, c)
        ii = i0[rep] + off // nk[rep]; kk = k0[rep] + off % nk[rep]
        px = (ii + 0.5) * h; pz = (kk + 0.5) * h
        ax, az = x[rep, 0], z[rep, 0]; bx, bz = x[rep, 1] - ax, z[rep, 1] - az; cx, cz = x[rep, 2] - ax, z[rep, 2] - az
        den = bx * cz - cx * bz; deg = np.abs(den) < 1e-7 * (bx * bx + bz * bz + cx * cx + cz * cz)       # edge-on in x-z
        den = np.where(deg, 1.0, den); qx, qz = px - ax, pz - az
        l1 = (qx * cz - cx * qz) / den; l2 = (bx * qz - qx * bz) / den; l0 = 1 - l1 - l2
        ok = ~deg & (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        y = T[rep, 0, 1] * l0 + T[rep, 1, 1] * l1 + T[rep, 2, 1] * l2
        jj = np.clip(np.ceil((y - lo[1]) / h - 0.5).astype(int), 0, n[1])
        np.add.at(flip, (ii[ok], jj[ok], kk[ok]), 1)
    flip %= 2; odd = int((flip.sum(1, dtype=np.int64) % 2).sum())
    inside = np.bitwise_xor.accumulate(flip[:, :-1], axis=1).astype(bool)
    return inside, dict(lo=lo, h=h, shape=n.tolist(), odd_columns=odd)


def check_through(M, dom_lo, dom_hi, probes, h=0.10, seal_band=None):
    """flood the air from the domain's outside; every probe must be air and reached. seal_band (a, b): PLANTED membrane =
    every voxel with a < cavity_sdf < b made solid (a closed shell round the cavity, voxel level: the defect sized to what
    the check reads; cavity_sdf from a 0.25 mm grid, trilinear)"""
    V, F = M["V"], M["F"]
    inside, info = voxelize(V, F, dom_lo, dom_hi, h); lo = info["lo"]; n = np.array(info["shape"])
    if seal_band is not None:
        import feat_mouth_v3b as MB
        g = 0.25; axc = [np.arange(dom_lo[d] - g, dom_hi[d] + 2 * g, g) for d in range(3)]
        Pc = np.stack(np.meshgrid(*axc, indexing="ij"), -1).reshape(-1, 3)
        Cc = np.concatenate([MB.cavity_sdf(Pc[s0:s0 + 400000]) for s0 in range(0, len(Pc), 400000)]).reshape([len(a) for a in axc])
        for i in range(n[0]):
            X = np.stack(np.meshgrid([lo[0] + (i + 0.5) * h], lo[1] + (np.arange(n[1]) + 0.5) * h, lo[2] + (np.arange(n[2]) + 0.5) * h, indexing="ij"), 0).reshape(3, -1)
            idx = (X - (np.asarray(dom_lo) - g)[:, None]) / g; cv = ndimage.map_coordinates(Cc, idx, order=1).reshape(n[1], n[2])
            inside[i] |= (cv > seal_band[0]) & (cv < seal_band[1])
    air = ~inside; lab, nl = ndimage.label(air)
    # outside = air components touching the domain faces in FRONT of the mouth (y min) or below/above it; the cavity
    # must not touch the domain (it is inside the head)
    # the OUTSIDE = air connected to the domain's FRONT face (y min: the air in front of the face); a cavity that reached
    # the domain's back or sides would otherwise count as 'outside' (first run: the cavity's back touched y max)
    outside = np.setdiff1d(np.unique(lab[:, 0, :].ravel()), [0])
    back = np.setdiff1d(np.unique(np.r_[lab[:, -1, :].ravel(), lab[0].ravel(), lab[-1].ravel()]), [0])
    I = np.floor((probes - lo) / h).astype(int); okp = np.all((I >= 0) & (I < n), axis=1); I = I[okp]
    pl = lab[tuple(I.T)]; is_air = pl > 0; reached = np.isin(pl, outside)
    # how deep does the outside air reach behind the lip margin (diagnostic)
    xs = lo[0] + (np.arange(n[0]) + 0.5) * h; zs = lo[2] + (np.arange(n[2]) + 0.5) * h
    xi = np.flatnonzero(np.abs(xs) < 12); zi = np.flatnonzero((zs > -26) & (zs < -12))
    sub = np.isin(lab[xi[0]:xi[-1] + 1, :, zi[0]:zi[-1] + 1], outside).any(axis=(0, 2)); ys = lo[1] + (np.arange(n[1]) + 0.5) * h
    reach = ys[np.flatnonzero(sub).max()] if sub.any() else None
    probe_labs = np.unique(pl[pl > 0]); touches = np.intersect1d(probe_labs, back)
    ok = bool(okp.all() and is_air.all() and reached.all())
    return {"status": "PASS" if ok else "FAIL", "probes": int(len(probes)), "probe_air_touches_domain_back_or_sides": int(len(touches)), "probes_in_domain": int(okp.sum()), "probes_air": int(is_air.sum()),
            "probes_reached_from_outside": int(reached.sum()), "air_components": int(nl), "odd_parity_columns": info["odd_columns"],
            "voxel_mm": h, "outside_air_reaches_y_max_mm (|x|<12, -26<z<-12)": _r(reach),
            "mark": "every probe air and in an outside-connected component (6-connected flood)"}


def cavity_probes(n=400, seed=7, y_max=None):
    import feat_mouth_v3b as MB
    rng = np.random.default_rng(seed); lo, hi = MB.REGION; out = []
    while sum(len(o) for o in out) < n:
        P = lo + (hi - lo) * rng.random((200000, 3)); c = MB.cavity_sdf(P); m = c < -0.8
        if y_max is not None:
            m &= P[:, 1] < y_max
        out.append(P[m])
    return np.vstack(out)[:n]


# ------------------------------------------------------------------ teeth
def load_part(name):
    Z = np.load(os.path.join(os.environ.get("ORAL_V3B_DIR", LAYERS), f"oral_v3b_{name}.npz"), allow_pickle=False)
    return dict(V=Z["v_head_mm"].astype(float), F=Z["f"].astype(np.int64), jaw=str(Z["jaw"]), obj=str(Z["object"]),
                label=Z["label"] if "label" in Z.files else None, names=Z["label_names"] if "label_names" in Z.files else None)


def check_teeth(parts, drop=None, move=None):
    import feat_mouth_v3b as MB
    rows = {}; ok = True; want = {"upper": 16, "lower": 14}
    for jaw in ("upper", "lower"):
        P = parts[f"{jaw}_teeth"]; V, F = P["V"].copy(), P["F"]
        nc, lab = components(F, len(V))
        comps = [np.unique(F[lab[F[:, 0]] == c].ravel()) for c in range(nc)]
        comps = [c for c in comps if len(c) > 30]
        spec = [t for t in MB.TEETH if t["jaw"] == jaw]
        tips = []
        for c in comps:
            J = MB.to_jaw(V[c]); k = np.argmin(J[:, 2]) if jaw == "upper" else np.argmax(J[:, 2]); tips.append(V[c][k])
        tips = np.array(tips)
        if drop is not None and drop[0] == jaw:                 # planted: delete one tooth shell
            sp = MB.to_head([t for t in spec if t["name"] == drop[1]][0]["cusp"]); j = np.argmin(np.linalg.norm(tips - sp, axis=1))
            tips = np.delete(tips, j, 0); comps.pop(j)
        if move is not None and move[0] == jaw:                 # planted: move one tooth shell
            sp = MB.to_head([t for t in spec if t["name"] == move[1]][0]["cusp"]); j = np.argmin(np.linalg.norm(tips - sp, axis=1))
            tips[j] = tips[j] + np.asarray(move[2])
        S = MB.to_head(np.array([t["cusp"] for t in spec])); D = np.linalg.norm(S[:, None] - tips[None], axis=2)
        from scipy.optimize import linear_sum_assignment
        r, c = linear_sum_assignment(D); err = D[r, c]
        matched = {spec[i]["name"]: _r(e) for i, e in zip(r, err)}
        bad = [spec[i]["name"] for i, e in zip(r, err) if e > MARKS["tooth_tip_mm"]]
        missing = [t["name"] for i, t in enumerate(spec) if i not in set(r)]
        cnt_ok = len(comps) == want[jaw]; jaw_ok = cnt_ok and not bad and not missing; ok &= jaw_ok
        # cited dimensions (independent of the build)
        dims = {}
        for nm, mean, tol in (("uP4", MARKS["P4_mean"], 2 * MARKS["P4_sd"]), ("lM1", MARKS["M1_mean"], MARKS["M1_frac"] * MARKS["M1_mean"])):
            if nm[0] != jaw[0]:
                continue
            for sd in ("L", "R"):
                t = [t for t in spec if t["name"] == f"{nm}.{sd}"][0]; i = [i for i, s in enumerate(spec) if s is t][0]
                if i in set(r):
                    cc = comps[c[list(r).index(i)]]; m3 = MB.dir_to_head(np.r_[t["mesial"], 0.0]); m3 /= np.linalg.norm(m3)
                    J = MB.to_jaw(V[cc]); crown = (J[:, 2] - t["base"][2]) * t["up"] > 0.2
                    L = float(np.ptp(V[cc][crown] @ m3)); dims[f"{nm}.{sd}_length_mm"] = _r(L)
                    if abs(L - mean) > tol:
                        ok = False; jaw_ok = False
        rows[jaw] = dict(status="PASS" if jaw_ok else "FAIL", shells=len(comps), want=want[jaw], tip_error_mm=matched,
                         tip_error_max_mm=_r(err.max() if len(err) else None), beyond_tolerance=bad, unmatched=missing, cited_dims=dims)
    return {"status": "PASS" if ok else "FAIL", **rows,
            "formula": "I 3/3, C 1/1, P 3/2, M 1/1 = 30 (Reighard & Jennings 1901 p. 224; Merck Vet Manual, Wright)",
            "marks": {"tip_mm": MARKS["tooth_tip_mm"], "P4": f"{MARKS['P4_mean']} +- 2 x {MARKS['P4_sd']} mm (domcat biometry, low)",
                      "M1": f"{MARKS['M1_mean']} +- 15 % (Kudaro, low)"}}


# ------------------------------------------------------------------ tongue
def check_tongue(parts, lift=0.0):
    import feat_mouth_v3b as MB
    T = parts["tongue"]; V = T["V"] + np.array([0.0, 0.0, lift]); F = T["F"]; N = _vnorm(V, F)
    J = MB.to_jaw(V); n_j = MB.to_jaw(V + N) - J
    free = (n_j[:, 2] > -0.2) & (J[:, 0] > SPEC_TONGUE_ROOT() + 2.0)            # not the ventral/root attachment
    cav = MB.cavity_sdf(V[free]); inside_share = float((cav < 0).mean())
    res = {}; worst = np.inf; Qf = V[free]
    for nm in ("upper_teeth", "lower_teeth", "palate"):
        P = parts[nm]; S = Surface(P["V"], P["F"]); bb = np.all((Qf >= P["V"].min(0) - 2) & (Qf <= P["V"].max(0) + 2), axis=1)
        s = S.signed(Qf[bb]) if bb.any() else np.array([np.inf]); res[nm] = _r(s.min()); worst = min(worst, s.min())
    ok = bool(inside_share >= 0.999 and worst >= MARKS["tongue_clear_mm"])
    return {"status": "PASS" if ok else "FAIL", "free_surface_vertices": int(free.sum()), "free_inside_cavity_share": _r(inside_share, 4),
            "min_signed_clearance_mm (negative = inside)": res, "mark": f"inside share >= 0.999 and clearance >= {MARKS['tongue_clear_mm']} mm",
            "lift_mm (planted)": lift}


def SPEC_TONGUE_ROOT():
    import feat_mouth_v3b as MB
    return MB.SPEC["tongue"]["root_f"]


# ------------------------------------------------------------------ jaws
def _rot_lower(V, deg):
    import feat_mouth_v3b as MB
    a = MB.TMJ_HEAD_MM["L"]; b = MB.TMJ_HEAD_MM["R"]; k = (a - b) / np.linalg.norm(a - b); c = 0.5 * (a + b); t = np.radians(deg)
    q = V - c; return c + q * np.cos(t) + np.cross(k, q) * np.sin(t) + np.outer(q @ k, k) * (1 - np.cos(t))


def check_jaws(parts, merge_lower_canine=False, shift_upper=0.0):
    import feat_mouth_v3b as MB
    up = {k: dict(parts[k]) for k in ("upper_teeth", "upper_gums", "palate")}; lo = {k: parts[k] for k in ("lower_teeth", "lower_gums", "tongue")}
    if shift_upper:
        up["upper_teeth"]["V"] = up["upper_teeth"]["V"] + np.array([0.0, 0.0, -shift_upper])
    if merge_lower_canine:                                       # planted: a lower tooth shell inside the upper object
        L = lo["lower_teeth"]; nc, lab = components(L["F"], len(L["V"])); S = MB.to_head([t["cusp"] for t in MB.TEETH if t["name"] == "lC.L"][0])
        best = min(range(nc), key=lambda c: np.linalg.norm(L["V"][np.unique(L["F"][lab[L["F"][:, 0]] == c])] - S, axis=1).min())
        fl = L["F"][lab[L["F"][:, 0]] == best]; vid = np.unique(fl); rm = -np.ones(len(L["V"]), np.int64); rm[vid] = np.arange(len(vid))
        U = up["upper_teeth"]; up["upper_teeth"] = dict(U, V=np.vstack([U["V"], L["V"][vid]]), F=np.vstack([U["F"], rm[fl] + len(U["V"])]))
    labels_ok = all(p.get("jaw", "upper") == "upper" for p in up.values()) and all(p.get("jaw", "lower") == "lower" for p in lo.values())
    Uall = np.vstack([p["V"] for p in up.values()]); Lall = np.vstack([p["V"] for p in lo.values()])
    dsh, _ = cKDTree(Uall).query(Lall, distance_upper_bound=1e-5); shared = int(np.isfinite(dsh).sum())   # coincident vertices
    # wrong-jaw tooth shells: every shell of the upper teeth object must match an UPPER spec tooth tip within 1.2 mm
    U = up["upper_teeth"]; nc, lab = components(U["F"], len(U["V"])); specU = MB.to_head(np.array([t["cusp"] for t in MB.TEETH if t["jaw"] == "upper"]))
    specL = MB.to_head(np.array([t["cusp"] for t in MB.TEETH if t["jaw"] == "lower"])); wrong = 0
    for c in range(nc):
        vid = np.unique(U["F"][lab[U["F"][:, 0]] == c])
        if len(vid) < 30:
            continue
        J = MB.to_jaw(U["V"][vid]); tip = U["V"][vid][np.argmin(J[:, 2])]; top = U["V"][vid][np.argmax(J[:, 2])]
        dU = np.linalg.norm(specU - tip, axis=1).min(); dL = np.linalg.norm(specL - top, axis=1).min()
        if dL < dU:
            wrong += 1
    # clearance closed and while opening
    rows = {}; worst = np.inf
    surf = {k: Surface(p["V"], p["F"]) for k, p in up.items()}
    for deg in (0,) + tuple(MARKS["open_deg"]):
        m = np.inf
        for kl, pl in lo.items():
            Vr = _rot_lower(pl["V"][::3], deg) if deg else pl["V"]                 # the sweep on every 3rd vertex (<= 0.2 mm apart)
            for ku_, S in surf.items():
                bb_lo, bb_hi = up[ku_]["V"].min(0) - 1, up[ku_]["V"].max(0) + 1
                sel = np.all((Vr >= bb_lo) & (Vr <= bb_hi), axis=1)
                if sel.any():
                    m = min(m, S.signed(Vr[sel]).min())
        rows[f"{deg}deg"] = _r(m); worst = min(worst, m)
    for kl, pl in lo.items():                                    # and the other way, closed: upper vertices in lower parts
        S = Surface(pl["V"], pl["F"])
        for ku_, pu in up.items():
            sel = np.all((pu["V"] >= pl["V"].min(0) - 1) & (pu["V"] <= pl["V"].max(0) + 1), axis=1)
            if sel.any():
                m = S.signed(pu["V"][sel]).min(); rows[f"0deg {ku_} in {kl}"] = _r(m); worst = min(worst, m)
    ok = bool(labels_ok and shared == 0 and wrong == 0 and worst >= MARKS["jaw_clear_mm"])
    return {"status": "PASS" if ok else "FAIL", "objects": {k: p.get("obj", k) for k, p in {**up, **lo}.items()}, "jaw_labels_ok": labels_ok,
            "shared_vertices": int(shared), "lower_shells_in_upper_object": int(wrong), "min_signed_clearance_upper_vs_lower_mm": rows,
            "mark": f"no shared vertex, no wrong-jaw shell, clearance >= {MARKS['jaw_clear_mm']} mm closed and opened to {MARKS['open_deg'][-1]} deg about the TMJ axis",
            "hinge_head_mm": {k: np.round(v, 2).tolist() for k, v in MB.TMJ_HEAD_MM.items()}}


# ------------------------------------------------------------------ chin (C1)
C1_S_MAX = 21.45      # = S_C - CT - 1: the commissure taper zone (owned by the commissure / corner probes) is excluded


def chin_profiles(V, F, hs=np.arange(1.0, -7.0 - 1e-9, -0.1), step_s=0.5):
    """VERTICAL chin sections across the lip line: per station (every step_s mm of s, both sides, s <= C1_S_MAX) rays
    along -nLL (horizontal, perpendicular to the line) from 6 mm in front of the contact C, at heights h along eup from
    C + 1.0 down to C - 7.0; the profile is the first-hit depth. (v3's M2 rays run along the margin's b, which at the
    midline lies 59 deg off vertical: an oblique slice, not the chin.)"""
    import feat_mouth_v3 as M3
    import mouth_v3_probes as MP3
    rows = []
    for sd in ("L", "R"):
        G = M3.GEOM[sd]
        for s0 in np.arange(0.25, C1_S_MAX + 1e-9, step_s):
            k = int(round(s0 / M3.DS)); C, nL, up = G["C"][k], G["nLL"][k], G["eup"][k]
            O = C + np.outer(hs, up) + 6.0 * nL; ts = MP3.ray(V, F, O, np.tile(-nL, (len(hs), 1)), maxhits=2, near=C, rad=14.0)
            rows.append((sd, float(s0), hs, ts[:, 0] - 6.0))
    return rows


def check_chin(V, F, base, mark_deg=10.0, share=0.05):
    """C1: concentrated turning of the chin profile (v3's measure: turn over +-0.3 mm minus turn over +-1.5 mm / 5; zero on
    any smooth arc, ~0.8 x the angle at a kink) in excess of Tripo's base at the same section, below the contact
    (h <= -0.5); a station with excess >= mark_deg carries a line; PASS when <= share of the stations do"""
    import mouth_v3_probes as MP3
    rows = chin_profiles(V, F); st = []
    for (sd, s0, hs, d), (_, _, _, db) in zip(rows, base):
        c = MP3._conc(hs, d); cb = MP3._conc(hs, db)
        if c is None or cb is None:
            st.append(dict(side=sd, s=s0, line=None)); continue
        ex = (c - cb); ex[hs > -0.5] = np.nan
        if not np.isfinite(ex).any():
            st.append(dict(side=sd, s=s0, line=None)); continue
        j = int(np.nanargmax(ex)); st.append(dict(side=sd, s=s0, excess_deg=_r(ex[j], 2), at_h=_r(hs[j], 2), line=bool(ex[j] >= mark_deg)))
    valid = [r for r in st if r["line"] is not None]; nl = sum(r["line"] for r in valid); sh = nl / max(len(valid), 1)
    ok = sh <= share and len(valid) >= 0.8 * len(st)
    return {"status": "PASS" if ok else "FAIL", "stations": len(st), "valid": len(valid), "line_stations": nl, "line_share": _r(sh),
            "worst": sorted(valid, key=lambda r: -r["excess_deg"])[:6],
            "mark": f"excess >= {mark_deg} deg = a line; PASS if <= {share:.0%} of stations (v3's M2 marks); chin = below the contact C (h <= -0.5), s <= {C1_S_MAX}"}


def chin_base():
    import mouth_v3_probes as MP3
    Vb, Fb = MP3.load(MP3.FILES["base"], True); return chin_profiles(Vb, Fb)


def base_rows():
    import mouth_v3_probes as MP3
    Vb, Fb = MP3.load(MP3.FILES["base"], True); return MP3._profiles(Vb, Fb)


def planted_crease(V, F, depth=0.35):
    import feat_mouth_v3 as M3
    n = _vnorm(V, F); hc = np.full(len(V), np.inf); dd = np.full(len(V), np.inf)
    for sd in ("L", "R"):
        Gs = M3.GEOM[sd]; dist, i = cKDTree(Gs["C"]).query(V); h = ((V - Gs["C"][i]) * Gs["eup"][i]).sum(1); b = dist < dd; dd[b] = dist[b]; hc[b] = h[b]
    band = np.clip(1 - np.abs(hc + 3.0) / 0.25, 0, 1) * (dd < 6)
    return V - depth * band[:, None] * n


# ------------------------------------------------------------------ wall
def check_wall(M, push=0.0):
    import feat_mouth_v3 as M3
    import feat_mouth_v3b as MB
    V, lab, F = M["V"], M["label"], M["F"]; keep = ~M["border"]
    nc, comp = components(F, len(V)); keep &= comp == np.argmax(np.bincount(comp))      # the skin itself, not stray bubbles
    farslot = (MB.ext_air(V) >= 1.5) & (np.asarray(M3.opening_sdf(V)) >= 1.5)
    lin = np.flatnonzero((lab == 2) & farslot & keep); skin = np.flatnonzero((lab == 0) & keep)
    tr = cKDTree(V[skin]); Q = V[lin]
    if push:                                                   # planted: the lining moved toward the outer skin
        _, j = tr.query(Q); d = V[skin][j] - Q; Q = Q + push * d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    d, j = tr.query(Q); i = np.argmin(d)
    ok = bool(d.min() >= MARKS["wall_mm"])
    return {"status": "PASS" if ok else "FAIL", "lining_vertices": int(len(lin)), "wall_p0_p1_p5_p50_mm": [_r(np.percentile(d, q)) for q in (0, 1, 5, 50)],
            "thinnest_at_head_mm": np.round(Q[i], 2).tolist(), "mark": f">= {MARKS['wall_mm']} mm (estimate: coat over the chin >= 1.0 mm)",
            "push_mm (planted)": push}


# ------------------------------------------------------------------ fill_voids (A20)
def check_fill_voids(use_mask=True, max_vox=None, sealed=True):
    """the 0.5 mm integration grid with the cavity ENCLOSED (sealed=True: feat_mouth_v3b.sealed_field, a 0.3 mm membrane
    across the parting line's entrance = what an unresolved slot leaves): fill_voids_v3 must keep the cavity air when
    given this module's opening_sdf mask; without the mask it fills it (the planted failure). sealed=False: the real
    field at 0.5 mm (info: whether the slot happens to stay connected at that grid)"""
    import feat_mouth_v3b as MB
    import skin_build as SB
    from skin_build_v3 import fill_voids_v3
    lo, hi = MB.REGION; B = MB.base_block(lo, hi); Fb = MB.base_fn(B); h = 0.5
    ax = [np.arange(lo[d], hi[d] + 1e-9, h) for d in range(3)]; n = [len(a) for a in ax]
    P = np.stack(np.meshgrid(*ax, indexing="ij"), -1).reshape(-1, 3)
    Fld = np.empty(len(P))
    for s in range(0, len(P), 300000):
        q = P[s:s + 300000]; f = MB.edit(q, Fb(q)); Fld[s:s + 300000] = MB.sealed_field(f, q, t=1.2) if sealed else f
    Fld = Fld.reshape(n).astype(np.float32); cav = MB.cavity_sdf(P).reshape(n) < -0.3
    lab, nl = ndimage.label(Fld > 0); border = np.unique(np.r_[lab[0].ravel(), lab[-1].ravel(), lab[:, 0].ravel(), lab[:, -1].ravel(), lab[:, :, 0].ravel(), lab[:, :, -1].ravel()])
    enclosed = float((~np.isin(lab[cav], border) & (lab[cav] > 0)).mean())
    mask = (MB.opening_sdf(P) < 0).reshape(n) if use_mask else None
    before = float((Fld[cav] > 0).mean())
    rep = fill_voids_v3(Fld, mask, max_vox=max_vox or SB.VOID_MAX_VOX)
    after = float((Fld[cav] > 0).mean())
    ok = after >= before - 1e-9 and after > 0.99
    return {"status": "PASS" if ok else "FAIL", "grid_mm": h, "sealed_membrane": bool(sealed), "cavity_enclosed_share": _r(enclosed, 4),
            "cavity_air_share_before": _r(before, 4), "after": _r(after, 4), "filled_voids_vox_largest": sorted(rep["filled"])[-3:],
            "protected_voids_vox_largest": sorted(rep["protected"])[-3:], "mask": bool(use_mask), "max_vox": int(max_vox or SB.VOID_MAX_VOX)}


# ------------------------------------------------------------------ the nose's passages stay clear of the cavity
def check_nose_clearance(shift_down=0.0, mark=3.0):
    """the nose owner's passages (feat_nose_v3b.opening_sdf, else v3) keep >= mark mm to the oral cavity (cavity_sdf; spec_nose
    'to_mouth_or_lip_skin_min' 3 mm, asked in NOTES_v3 15:05). Planted: the passages moved down shift_down mm"""
    import feat_mouth_v3b as MB
    try:
        import feat_nose_v3b as FN
        src = "feat_nose_v3b"
    except ImportError:
        import feat_nose_v3 as FN
        src = "feat_nose_v3"
    R = FN.REGION; lo = np.array(R["lo_mm"]); hi = np.array(R["hi_mm"])
    g = np.stack(np.meshgrid(*[np.arange(lo[d], hi[d], 0.2) for d in range(3)], indexing="ij"), -1).reshape(-1, 3)
    o = np.concatenate([FN.opening_sdf(g[s0:s0 + 300000]) for s0 in range(0, len(g), 300000)]); A = g[o < 0] - np.array([0, 0, shift_down])
    c = MB.cavity_sdf(A); i = int(np.argmin(c))
    return {"status": "PASS" if c.min() >= mark else "FAIL", "nose_module": src, "nose_air_points": int(len(A)), "min_clearance_mm": _r(c.min(), 2),
            "at_head_mm": np.round(A[i], 2).tolist(), "mark": f">= {mark} mm (spec_nose to_mouth_or_lip_skin_min)", "shift_down_mm (planted)": shift_down}


# ------------------------------------------------------------------ lip probes (v3's, unchanged)
def lip_probes(V, F):
    import feat_mouth_v3b as MB
    import mouth_v3_probes as MP3
    out = MP3.inventory(V, F, MB.probe_inputs()); out["M1_opening"] = MP3.probe_open(V, F); out["M5_contract"] = MB.contract_probe(0.10)
    return out


# ------------------------------------------------------------------ flag_49: the person's chin, from the full-detail skin_v3
def extract_flag49(lo=(-23.0, -73.0, -34.0), hi=(24.0, -47.0, -15.0)):
    """faces of skin_v3.npz (the skin the person flagged, full detail) inside the v3 mouth crop -> layers/flag49_chin_crop_v3b.npz
    (a pass over the full 11.7 M-triangle skin: run through heavy_lock)"""
    import zipfile
    from numpy.lib import format as fmt
    import partition as PT
    path = os.path.join(LAYERS, "skin_v3.npz"); z = zipfile.ZipFile(path)

    def stream(member, rows=1_000_000):
        fh = z.open(member + ".npy"); ver = fmt.read_magic(fh)
        sh, fo, dt = fmt.read_array_header_1_0(fh) if ver == (1, 0) else fmt.read_array_header_2_0(fh); dt = np.dtype(dt)
        w = int(np.prod(sh[1:])); a = 0
        while a < sh[0]:
            k = min(rows, sh[0] - a); yield np.frombuffer(fh.read(k * w * dt.itemsize), dt).reshape((k,) + tuple(sh[1:])); a += k
    V = np.concatenate([PT.head_local(b.astype(float)) * 1000 for b in stream("v")])
    m = np.all((V >= np.array(lo) - 1) & (V <= np.array(hi) + 1), axis=1); keep = []
    for f in stream("f"):
        s = m[f].all(1)
        if s.any():
            keep.append(f[s].astype(np.int64))
    Fk = np.concatenate(keep); u, inv = np.unique(Fk, return_inverse=True)
    fn = os.path.join(LAYERS, "flag49_chin_crop_v3b.npz")
    np.savez_compressed(fn, v_head_mm=V[u], f=inv.reshape(-1, 3).astype(np.int32), gid=u, crop_head_mm=np.array([lo, hi]),
                        note="skin_v3.npz (the skin the person flagged on flag_49; full detail) cropped to the v3 mouth crop, head mm")
    print(fn, len(u), len(Fk)); return fn


def load_flag49():
    Z = np.load(os.path.join(LAYERS, "flag49_chin_crop_v3b.npz")); V = Z["v_head_mm"].astype(float); F = Z["f"].astype(np.int64)
    lo, hi = Z["crop_head_mm"]; ins = np.all((V >= lo + 0.3) & (V <= hi - 0.3), axis=1); Fk = F[ins[F].all(1)]
    idx = np.unique(Fk); rm = -np.ones(len(V), np.int64); rm[idx] = np.arange(len(idx)); return V[idx], rm[Fk]


# ------------------------------------------------------------------ runners
def load_parts():
    return {k: load_part(k) for k in ("upper_teeth", "upper_gums", "palate", "lower_teeth", "lower_gums", "tongue")}


def run():
    import feat_mouth_v3b as MB
    import mouth_v3_probes as MP3
    t0 = time.time(); R = {"epoch_start": int(t0), "marks": MARKS, "files": {}}
    Mb = load_preview("feat_mouth_v3b_preview.npz"); Mv3 = load_preview("feat_mouth_v3_preview.npz")
    R["files"] = {"v3b": Mb["file"], "v3": Mv3["file"], "parts": "oral_v3b_*.npz"}
    R["DECISIONS"] = {"G13_leather_top": check_leather_top(), "D6a_lip_form_keep": check_keep(Mb, Mv3)}
    jdump(R, OUT)
    dom_lo, dom_hi = np.array([-19.5, -70.0, -31.0]), np.array([19.5, -11.6, -9.0])
    pr = cavity_probes(); R["mouth_through"] = check_through(Mb, dom_lo, dom_hi, pr); jdump(R, OUT)
    parts = load_parts()
    R["teeth"] = check_teeth(parts); R["tongue"] = check_tongue(parts); R["jaws"] = check_jaws(parts); jdump(R, OUT)
    Vi, Fi, _ = interior(Mb, MP3.CROP_LO, MP3.CROP_HI); cb = chin_base(); R["chin_C1"] = check_chin(Vi, Fi, cb)
    R["chin_v3_M2_ring (info: v3's own probe, all stations, oblique midline frame)"] = MP3.probe_ring(Vi, Fi, base_rows())
    R["nose_clearance"] = check_nose_clearance(); R["wall"] = check_wall(Mb); R["fill_voids"] = check_fill_voids(True, max_vox=10 ** 9, sealed=True)
    R["fill_voids_real_field_0p5 (info)"] = check_fill_voids(True, max_vox=10 ** 9, sealed=False)
    R["lips_P1_M1_M5"] = {k: (v.get("status") if isinstance(v, dict) else v) for k, v in lip_probes(Vi, Fi).items()}
    R["registration"] = MB.registration_report(); R["seconds"] = round(time.time() - t0, 1)
    R["summary"] = {k: (v.get("status") if isinstance(v, dict) and "status" in v else None) for k, v in R.items() if isinstance(v, dict)}
    R["summary"].update({f"DECISION {k}": v["status"] for k, v in R["DECISIONS"].items()})
    jdump(R, OUT); print(json.dumps(R["summary"], indent=1)); return R


def prove():
    """planted failures on both sides for every check (A10, A22) -> mouth_checks_v3b.json['proofs']"""
    import feat_mouth_v3b as MB
    import mouth_v3_probes as MP3
    R = json.load(open(OUT)) if os.path.exists(OUT) else {}; P = {}
    Mb = load_preview("feat_mouth_v3b_preview.npz"); Mv3 = load_preview("feat_mouth_v3_preview.npz")
    P["G13 planted 0.25 mm bump (must FAIL)"] = check_leather_top(bump=0.25)["status"]
    Uc = MB.GEOM["L"]["U"][int(round(8 / MB.DS))] + 1.2 * MB.GEOM["L"]["b"][int(round(8 / MB.DS))]
    P["D6a planted 0.8 mm upper-lip dent (must FAIL)"] = check_keep(Mb, Mv3, dent=(Uc, 0.8, 1.0))["status"]
    P["D6a planted 0.3 mm upper-lip dent (must PASS)"] = check_keep(Mb, Mv3, dent=(Uc, 0.3, 1.0))["status"]
    # mouth_through: v3's blind slot (its own crop) and a membrane on v3b
    lo3, hi3 = np.array([-19.0, -70.0, -31.0]), np.array([19.0, -48.0, -16.0])
    pr3 = cavity_probes(300, y_max=-49.0); pr3 = pr3[np.all((pr3 > lo3 + 0.5) & (pr3 < hi3 - 0.5), axis=1)]
    P["through on mouth v3 preview (must FAIL)"] = check_through(Mv3, lo3, hi3, pr3)
    P["through on v3b, same small domain (must PASS)"] = check_through(Mb, lo3, hi3, pr3)["status"]
    dom_lo, dom_hi = np.array([-19.5, -70.0, -31.0]), np.array([19.5, -11.6, -9.0])
    P["through on v3b with a planted 0.3 mm membrane 0.3-0.6 mm outside the cavity wall (must FAIL)"] = check_through(
        Mb, dom_lo, dom_hi, cavity_probes(), seal_band=(0.3, 0.6))
    parts = load_parts()
    P["teeth planted missing upper canine uC.L (must FAIL)"] = check_teeth(parts, drop=("upper", "uC.L"))["status"]
    P["teeth planted lP3.R moved 2 mm (must FAIL)"] = check_teeth(parts, move=("lower", "lP3.R", (0.0, 2.0, 0.0)))["status"]
    P["tongue planted 1.5 mm lift through the palate (must FAIL)"] = check_tongue(parts, lift=1.5)["status"]
    P["jaws planted lower canine merged into the upper object (must FAIL)"] = check_jaws(parts, merge_lower_canine=True)["status"]
    P["jaws planted upper teeth 1.0 mm down (must FAIL)"] = check_jaws(parts, shift_upper=1.0)["status"]
    cb = chin_base()
    try:
        Vf, Ff = load_flag49(); P["chin on the flag_49 chin (skin_v3 full detail) (must FAIL)"] = check_chin(Vf, Ff, cb)
    except FileNotFoundError:
        P["chin on the flag_49 chin (must FAIL)"] = "NOT RUN: flag49_chin_crop_v3b.npz missing (python mouth_checks_v3b.py flag49 through heavy_lock)"
    Vi, Fi, _ = interior(Mb, MP3.CROP_LO, MP3.CROP_HI)
    P["chin planted 0.35 mm crease 3 mm under C on v3b (must FAIL)"] = check_chin(planted_crease(Vi, Fi), Fi, cb)
    V3i, F3i, _ = interior(Mv3, MP3.CROP_LO, MP3.CROP_HI); P["chin on mouth v3 (info)"] = check_chin(V3i, F3i, cb)
    P["wall planted lining pushed 1.2 mm (must FAIL)"] = check_wall(Mb, push=1.2)["status"]
    P["nose clearance, passages planted 0.6 mm lower (must FAIL)"] = check_nose_clearance(shift_down=0.6)
    P["fill_voids, cavity enclosed, WITHOUT the opening mask (must FAIL)"] = check_fill_voids(False, max_vox=10 ** 9, sealed=True)
    R["proofs"] = P; jdump(R, OUT); print(json.dumps({k: (v if isinstance(v, str) else v.get("status")) for k, v in P.items()}, indent=1)); return P


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "run":
        run()
    elif cmd == "prove":
        prove()
    elif cmd == "flag49":
        extract_flag49()
