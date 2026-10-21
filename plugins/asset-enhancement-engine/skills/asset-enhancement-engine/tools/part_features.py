"""PART FEATURES (build L4, 2026-10-21): the features of a part - the ears, nose, eyes and lips of a head - found from
the part's own shape, as regions of its skin, for the Translator's word lists (engine/tools/language.py, run after a
pack's splits, mounds and merges; data: a pack's "features" block, e.g. engine/packs/human/language.json).

Why it exists. The person (2026-10-21): "If I want to open a hand, or an ear, or a nose, or a breast, or an arm"; the
head rung needs the face's parts too (eyes, lips). Build L2 named the head as one part.

THE MEASURES (all in the part's own frame and scaled by the part's own size, so no one body's numbers decide):
  frame    origin at the part's centre (the head: 45 % of the way from its seam with what it sits on to the crown),
           y up the part's axis, z the body's front made square to it, x the subject's left;
  course   the part's smooth radial course: r(u), the distance of the skin from the centre in direction u, fitted by
           a polynomial in u of low degree (a spherical-harmonic space) with Tukey re-weighting, so what stands out
           of the skull or sinks into it (ears, nose, lips, eye openings) does not pull it; R0 = its median radius;
  height   h = r - course(u) per vertex: + stands out (an ear's rim, the nose), - sinks in (an eye socket);
  pocket   the skin a ball of radius rho (a share of R0) resting on it from outside cannot touch: the inside of an
           opening or a narrow crease (the eye openings, the mouth line, the nostrils, the folds of an ear);
  bulge    the mean curvature averaged over a small ball (a share of R0): + convex (a lid, a lip), - concave (the
           crease round it).
THE REGIONS (each feature's spec in the pack, tried in the pack's order; what one feature takes no later one can):
  seed     where the feature starts: "protrusion" the largest patch standing out by seed_h (an ear: on its side), or
           the most anterior point on the mid-line (the nose tip); "opening" the largest pocket patch in its place
           (an eye: the highest large one either side; the lips: the widest across the mid-line below the nose tip
           that does not border the nose, the crease round the nostrils being the nose's own);
  grow     a protrusion grows over the skin still standing out by grow_h; an opening grows its rim over the convex skin
           (bulge > 0) round it, out to the concave crease that bounds it (a lid's crease, the lips' borders) and no
           farther than rim_max x the opening's width;
  close    a geodesic closing (dilate, then erode, by close x R0) bridges small gaps (an ear's notch between the
           tragus and the antitragus);
  islands  at the end, every piece of the part's skin cut off from the rest by features (a concha inside an ear, the
           inside of a nostril, the socket behind an eye opening, the inside of a mouth) joins the feature it borders
           most; a separate shell lying in a feature (an eye's globe in its socket) joins that feature.
Returns, per feature, the faces it holds and a record of where its border fell and what was measured.
Proof: engine/tools/test_part_features.py (a planted head with ears, a nose, eye openings and lips of known extent).
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------------------------------------ the measures
def _unit(a):
    a = np.asarray(a, float); return a / max(np.linalg.norm(a), 1e-30)


def frame_of(V, F, fm, below_fm=None, front=(0.0, -1.0, 0.0), left=(1.0, 0.0, 0.0), centre_at=0.45):
    """the part's frame: base = the centroid of its seam with below_fm (else its lowest skin along -up), crown = its
    skin farthest from the base, centre = centre_at of the way from base to crown; rows x (subject's left), y (up the
    axis), z (front made square to y)"""
    vk = np.unique(F[fm])
    if below_fm is not None and below_fm.any():
        seam = np.intersect1d(vk, np.unique(F[below_fm]))
    else:
        seam = np.zeros(0, np.int64)
    if not len(seam):
        up = np.cross(_unit(front), _unit(left)) * -1.0
        z = V[vk] @ up; seam = vk[z <= np.percentile(z, 2)]
    base = V[seam].mean(0); crown = V[vk[np.argmax(np.linalg.norm(V[vk] - base, axis=1))]]
    y = _unit(crown - base); z = np.asarray(front, float); z = _unit(z - (z @ y) * y); x = np.cross(y, z)
    if x @ np.asarray(left, float) < 0:
        x = -x
    return {"base": base, "crown": crown, "centre": base + centre_at * (crown - base), "R": np.stack([x, y, z]),
            "height": float(np.linalg.norm(crown - base)), "seam_vertices": int(len(seam))}


def _monomials(U, deg):
    cols = []
    for a in range(deg + 1):
        for b in range(deg + 1 - a):
            for c in range(deg + 1 - a - b):
                cols.append(U[:, 0] ** a * U[:, 1] ** b * U[:, 2] ** c)
    return np.stack(cols, 1)


def course(P, A, degree=8, iters=6, tukey=4.685):
    """the radial course of points P (frame coordinates, from the centre) with areas A: returns h (the height of each
    point above the course), the course radius per point and the robust scale of the residuals"""
    r = np.linalg.norm(P, axis=1); U = P / np.maximum(r[:, None], 1e-30); M = _monomials(U, degree); w = A.astype(float).copy()
    for _ in range(iters):
        sw = np.sqrt(w); coef = np.linalg.lstsq(M * sw[:, None], r * sw, rcond=None)[0]
        res = r - M @ coef; s = 1.4826 * np.median(np.abs(res - np.median(res))) + 1e-12
        t = res / (tukey * s); w = A * np.where(np.abs(t) < 1, (1 - t ** 2) ** 2, 0.0)
    cr = M @ coef
    return r - cr, cr, float(s)


def pockets(V, F, N, rho):
    """skin a ball of radius rho resting on it from outside cannot touch: the ball's centre (rho out along the normal)
    has other skin (vertices or face centres) nearer than rho"""
    from scipy.spatial import cKDTree
    cloud = np.vstack([V, V[F].mean(1)]); d, _ = cKDTree(cloud).query(V + rho * N)
    return d < 0.98 * rho


def bulge(V, F, A, s):
    """mean curvature (1/m; convex +) averaged over a ball of radius s (area weights); the vertex's own value where s
    is under its edges"""
    from scipy.sparse import csr_matrix
    from scipy.spatial import cKDTree
    sys.path.insert(0, HERE)
    import mesh_geom as MG
    H, _ = MG.mean_curvature(V, F); H = np.nan_to_num(H)
    lim = np.percentile(np.abs(H), 99.5) if len(H) else 1.0
    H = np.clip(H, -lim, lim)
    pr = cKDTree(V).query_pairs(s, output_type="ndarray")
    i = np.r_[pr[:, 0], pr[:, 1], np.arange(len(V))]; j = np.r_[pr[:, 1], pr[:, 0], np.arange(len(V))]
    W = csr_matrix((A[j], (i, j)), shape=(len(V), len(V)))
    return (W @ H) / np.maximum(np.asarray(W.sum(1)).ravel(), 1e-30)


# ---------------------------------------------------------------------------------------------- region tools
class _Graph:
    def __init__(self, V, F):
        from scipy.sparse import coo_matrix
        n = len(V); E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
        L = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
        self.n = n; self.G = coo_matrix((np.r_[L, L], (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(n, n)).tocsr()
        self.G.sum_duplicates()

    def comps(self, mask):
        from scipy.sparse.csgraph import connected_components
        idx = np.nonzero(mask)[0]; out = -np.ones(self.n, np.int64)
        if not len(idx):
            return out, 0
        k, lab = connected_components(self.G[idx][:, idx], directed=False); out[idx] = lab
        return out, k

    def grow(self, seed, allowed):
        lab, _ = self.comps(allowed | seed); keep = np.unique(lab[seed & (lab >= 0)])
        return np.isin(lab, keep) & (lab >= 0)

    def dist(self, mask, limit, within=None):
        from scipy.sparse.csgraph import dijkstra
        if within is None:
            G = self.G
        else:                                                          # the edges between vertices both within (an explicit
            G = self.G.multiply(within[:, None]).multiply(within[None, :]).tocsr(); G.eliminate_zeros()   # zero is an edge)
        if not mask.any():
            return np.full(self.n, np.inf)
        return dijkstra(G, indices=np.nonzero(mask)[0], min_only=True, limit=limit)

    def close(self, mask, c, within):
        """geodesic closing inside `within`: dilate by c, erode by c; the mask itself always stays"""
        if c <= 0 or not mask.any():
            return mask
        dil = (self.dist(mask, 2.5 * c, within) <= c) & within
        ero = self.dist(~dil & within, 2.5 * c, within) > c
        return (dil & ero) | mask


def _near_base(P, fr, rim):
    """open edges at the part's base (its cut end when nothing below shares the seam): the lowest 10 % along y"""
    lo = np.percentile(P[:, 1], 10)
    return P[:, 1] <= lo


def _largest(Gr, mask, A):
    lab, k = Gr.comps(mask)
    if k == 0:
        return mask & False
    a = np.bincount(lab[lab >= 0], weights=A[lab >= 0], minlength=k)
    return lab == int(np.argmax(a))


def _seen_from_side(V, F, P, main, reg, sg, close_r, tol):
    """(an ear's front) the skin of the main shell seen from the side sg (+1 the subject's left, -1 right) inside the
    footprint of reg: reg's outline in the plane square to x, closed by close_r and its holes filled; seen = within tol
    of the outermost skin in its cell (a z-buffer of vertices and face centres)"""
    from scipy import ndimage
    C = np.vstack([P, P[F].mean(1)]); cm = np.r_[main, main[F].all(1)]
    el = np.linalg.norm(V[F[:, 0]] - V[F[:, 1]], axis=1); g = max(close_r / 4, 1.5 * float(np.median(el)))
    yz = C[:, 1:]; lo = yz[np.r_[reg, reg[F].all(1)]].min(0) - 3 * close_r; hi = yz[np.r_[reg, reg[F].all(1)]].max(0) + 3 * close_r
    nb = np.ceil((hi - lo) / g).astype(int) + 1
    ij = np.floor((yz - lo) / g).astype(int); ok = cm & (ij >= 0).all(1) & (ij < nb).all(1)
    cell = np.where(ok, ij[:, 0] * nb[1] + ij[:, 1], -1)
    zb = np.full(nb[0] * nb[1], -np.inf); np.maximum.at(zb, cell[ok], sg * C[ok, 0])
    fp = np.zeros(nb[0] * nb[1], bool); rr = np.r_[reg, reg[F].all(1)] & ok; fp[cell[rr]] = True
    k = max(int(round(close_r / g)), 1); yy, xx = np.mgrid[-k:k + 1, -k:k + 1]; disc = yy ** 2 + xx ** 2 <= k * k
    fp = ndimage.binary_fill_holes(ndimage.binary_closing(fp.reshape(nb), disc, border_value=0)).ravel()
    nv = len(P); cv = cell[:nv]; okv = ok[:nv]
    return okv & fp[np.maximum(cv, 0)] & (sg * P[:, 0] >= zb[np.maximum(cv, 0)] - tol)


# ------------------------------------------------------------------------------------------------- features
def find(V, F, fm, spec, below_fm=None, front=(0.0, -1.0, 0.0), left=(1.0, 0.0, 0.0), log=print):
    """the features of part fm (a face mask over F) by the pack's spec (see the module doc). Returns (features,
    record): features = [{"word", "side" ('L', 'R' or ''), "faces" (indices into F), "info"}], record = what was
    measured on the part (its frame, R0, the share of the skin in pockets)"""
    ff = np.nonzero(fm)[0]; vk = np.unique(F[ff]); rm = -np.ones(len(V), np.int64); rm[vk] = np.arange(len(vk))
    Vs, Fs = V[vk].astype(float), rm[F[ff]]
    fr = frame_of(V, F, fm, below_fm, front, left, spec.get("centre_at", 0.45))
    fa = 0.5 * np.linalg.norm(np.cross(Vs[Fs[:, 1]] - Vs[Fs[:, 0]], Vs[Fs[:, 2]] - Vs[Fs[:, 0]]), axis=1)
    A = np.zeros(len(Vs))
    for k in range(3):
        np.add.at(A, Fs[:, k], fa / 3)
    sys.path.insert(0, HERE)
    import mesh_geom as MG
    N = MG.vertex_normals(Vs, Fs)
    Gr = _Graph(Vs, Fs)
    # the main shell (separate shells, e.g. an eye's globe, are placed at the end)
    flab, nsh = Gr.comps(np.ones(len(Vs), bool))
    sha = np.bincount(flab, weights=A, minlength=nsh); main = flab == int(np.argmax(sha))
    P = (Vs - fr["centre"]) @ fr["R"].T; x, y, z = P.T
    cs = spec.get("course", {})
    h = np.full(len(Vs), np.nan); cr = np.full(len(Vs), np.nan)
    h[main], cr[main], scale = course(P[main], A[main], cs.get("degree", 8), cs.get("iters", 6))
    R0 = float(np.median(cr[main]))
    pk = pockets(Vs, Fs, N, spec.get("pocket_ball", 0.05) * R0) & main
    E = np.sort(np.concatenate([Fs[:, [0, 1]], Fs[:, [1, 2]], Fs[:, [2, 0]]]), 1); Eu, ec = np.unique(E, axis=0, return_counts=True)
    rim = np.zeros(len(Vs), bool); rim[Eu[ec == 1].ravel()] = True     # an open edge that is not the part's own seam (an
    if below_fm is not None:                                           # eye opening cut through: the rim of a hole)
        rim[rm[np.intersect1d(vk, np.unique(F[below_fm]))]] = False
    rim &= main & ~_near_base(P, fr, rim)
    pk |= rim
    bl = bulge(Vs, Fs, A, spec.get("bulge_ball", 0.02) * R0)
    rec = {"frame": {"centre_m": fr["centre"].tolist(), "base_m": fr["base"].tolist(), "crown_m": fr["crown"].tolist(),
                     "axes_rows_xyz": fr["R"].tolist(), "height_cm": round(fr["height"] * 100, 2)},
           "R0_cm": round(R0 * 100, 3), "course_residual_scale_cm": round(scale * 100, 3),
           "pocket_share": round(float(A[pk].sum() / A[main].sum()), 4), "shells": int(nsh), "vertices": int(len(Vs))}
    claimed = np.zeros(len(Vs), bool); out = {}; tip = None
    mid = main & (np.abs(x) <= spec.get("midline", 0.12) * R0) & (z > 0)

    def front_tip():
        """the nose tip: the point of the front mid-line standing out most from the course, between the eyes' level and
        tip_band x R0 below it when the eyes are found (a chin or the lips can stand out as far), else on the whole front
        mid-line"""
        eyes = [o for kk, o in out.items() if o["word"] == spec.get("tip_below", "eye")]
        m = mid.copy()
        if eyes:
            ey = float(np.mean([o["_cy"] for o in eyes])); m &= (y <= ey) & (y >= ey - spec.get("tip_band", 0.6) * R0)
        if not m.any():
            m = mid if mid.any() else main
        t = int(np.nonzero(m)[0][np.argmax(h[m])]); rec["front_tip_cm"] = (P[t] * 100).round(2).tolist()
        return t
    for word in spec.get("order", list(spec.get("parts", {}))):
        sp = spec["parts"][word]
        sides = [("L", 1.0), ("R", -1.0)] if sp.get("pair") else [("", 0.0)]
        for side, sg in sides:
            key = word + (("_" + side) if side else "")
            free = main & ~claimed
            where = free.copy()
            w = sp.get("where", {})
            if sg:
                where &= sg * x >= w.get("side_min", 0.0) * R0
                if "side_max" in w:
                    where &= sg * x <= w["side_max"] * R0
            if "front_min" in w:
                where &= z >= w["front_min"] * R0
            if "front_tip" in (w.get("above"), w.get("below"), sp.get("seed")) and tip is None:
                tip = front_tip()
            if w.get("above") == "front_tip":
                where &= y > y[tip]
            if w.get("below") == "front_tip":
                where &= (y < y[tip]) & (y >= y[tip] - w.get("below_band", 9.0) * R0)
            info = {"how": sp["kind"]}
            if sp["kind"] == "protrusion":
                if sp.get("seed") == "front_tip":
                    seed = np.zeros(len(Vs), bool); seed[tip] = free[tip]
                else:
                    seed = _largest(Gr, where & (h >= sp["seed_h"] * R0), A)
                if not seed.any():
                    log(f"  feature {key}: no seed"); continue
                allow = free & (h >= sp["grow_h"] * R0)
                if sg:
                    allow &= sg * x >= sp.get("grow_side_min", w.get("side_min", 0.0)) * R0
                if "front_min" in w:
                    allow &= z >= sp.get("grow_front_min", w["front_min"]) * R0
                caps = [o for o in out.values() if o["word"] == sp.get("cap_at")]
                if caps and all("_inner_x" in o for o in caps):       # (the nose) no higher than the eyes' openings and no
                    allow &= y <= max(o["_open_top_y"] for o in caps)  # wider than half-way past their inner corners (the
                    allow &= np.abs(x) <= sp.get("half_width", 1.3) * min(o["_inner_x"] for o in caps)   # nose is about
                    info["half_width_cap_cm"] = round(sp.get("half_width", 1.3) * min(o["_inner_x"] for o in caps) * 100, 2)   # as wide as they are apart)
                reg = Gr.grow(seed, allow)
                info.update(seed_h_cm=round(sp.get("seed_h", 0) * R0 * 100, 3), border_h_cm=round(sp["grow_h"] * R0 * 100, 3))
                if sp.get("footprint") and sg:                         # (an ear) its front: what is seen from its side
                    vis = _seen_from_side(Vs, Fs, P, main, reg, sg, sp["footprint"] * R0, spec.get("seen_tol", 0.02) * R0)
                    reg = Gr.grow(reg, reg | (vis & free))
                    info["footprint_close_cm"] = round(sp["footprint"] * R0 * 100, 3)
            elif sp["kind"] == "opening":
                # the opening: skin a ball cannot reach (its rim's crease) or sunk below the course (what lies behind
                # it: a socket, the inside of a mouth), the largest such patch in its place, with the rim's creases
                # beside it (within join x R0)
                sunk = sp.get("sink_h", 0.1) * R0; cand = where & (pk | ((h <= -sunk) & (h >= -sp.get("sink_max", 9.0) * R0)))
                if sp.get("crosses_midline"):
                    lab, k = Gr.comps(cand); best, ba = None, 0.0
                    away = [o["mask"] for o in out.values() if o["word"] in sp.get("apart_from", []) and o["mask"].any()]
                    nbr = None
                    if away:                                           # (the lips) a crease that touches the nose (an edge
                        Gc = Gr.G.tocoo(); am = np.logical_or.reduce(away)   # to it) is the nose's own, round the
                        nbr = np.zeros(len(Vs), bool); nbr[Gc.row[am[Gc.col]]] = True   # nostrils, not the mouth
                    for strict in ((True, False) if nbr is not None else (False,)):   # apart from the nose if any is;
                        for c in range(k):                             # else the best of all (a coarse mesh's lip line
                            m = lab == c                               # may run along the nose's foot)
                            if strict and (m & nbr).any():
                                continue
                            score = np.ptp(x[m]) if sp.get("pick") == "widest" else A[m].sum()   # (the lips: the widest: a
                            if x[m].min() < 0 < x[m].max() and score > ba:                    # mouth is wider than the nostrils)
                                best, ba = m, score
                        if best is not None:
                            info["apart_from_" + "_".join(sp.get("apart_from", []))] = bool(strict)
                            break
                    seed = best if best is not None else cand & False
                elif sp.get("pick") == "highest":                      # (an eye) the highest of the large patches: a
                    lab, k = Gr.comps(cand); seed = cand & False       # socket, not the inside of a nose or a mouth
                    if k:
                        a = np.bincount(lab[lab >= 0], weights=A[lab >= 0], minlength=k)
                        cy = np.bincount(lab[lab >= 0], weights=(A * y)[lab >= 0], minlength=k) / np.maximum(a, 1e-30)
                        ok = np.nonzero(a >= sp.get("pick_share", 0.25) * a.max())[0]
                        seed = lab == int(ok[np.argmax(cy[ok])])
                else:
                    seed = _largest(Gr, cand, A)
                if not seed.any():
                    log(f"  feature {key}: no opening found"); continue
                # its rim: the crease patches (pockets) in its place within join x R0 of it (an eye's lid margins
                # in front of its socket; the lips' line in front of the inside of the mouth)
                from scipy.spatial import cKDTree
                Ta = cKDTree(Vs[seed]); plab, pkk = Gr.comps(where & pk); rim_ = seed & pk
                for c in range(pkk):
                    m = plab == c
                    if Ta.query(Vs[m], distance_upper_bound=sp.get("join", 0.1) * R0)[0].min() <= sp.get("join", 0.1) * R0:
                        rim_ |= m
                if not rim_.any():
                    rim_ = seed.copy()
                opening = Gr.close(seed | rim_, spec.get("close", 0.0) * R0, free)
                fz = z[opening].max(); front_ = rim_
                width = float(np.ptp(x[front_])); height_ = float(np.ptp(y[front_]))
                unit = R0 if sp.get("rim_unit") == "R0" else width     # the band round the rim: a share of the part's
                rmax = sp.get("rim_max", 0.5) * unit; rmin = sp.get("rim_min", 0.0) * unit   # size or of the opening's width
                d = Gr.dist(rim_, rmax * 1.05, free)
                allow = free & (d <= rmax) & ((bl >= sp.get("bulge_min", 0.0) / R0) | (d <= rmin))
                if sp.get("within_width"):                             # (the lips) between the corners of the opening
                    allow &= (x >= x[front_].min() - sp["within_width"] * width) & (x <= x[front_].max() + sp["within_width"] * width)
                reg = Gr.grow(opening, allow) | opening
                info.update(opening_width_cm=round(width * 100, 2), opening_height_cm=round(height_ * 100, 2),
                            opening_depth_cm=round(float(fz - z[opening].min()) * 100, 2),
                            rim_max_cm=round(rmax * 100, 2), rim_min_cm=round(rmin * 100, 2),
                            bulge_min_per_m=round(sp.get("bulge_min", 0.0) / R0, 2))
            else:
                raise ValueError(f"unknown feature kind {sp['kind']}")
            reg = Gr.close(reg, sp.get("close", 0.0) * R0, free) & free
            reg = Gr.grow(reg & seed, reg)
            claimed |= reg
            out[key] = {"word": word, "side": side, "mask": reg, "_top_y": float(y[reg].max()) if reg.any() else -np.inf, "info": info,
                        "_cy": float((A[reg] * y[reg]).sum() / max(A[reg].sum(), 1e-30))}
            if sp["kind"] == "opening":                                # an opening's inner corner (to the mid-line) and top
                out[key]["_inner_x"] = float(np.abs(x[rim_]).min()); out[key]["_open_top_y"] = float(y[rim_].max())
                info.update(inner_corner_cm=round(out[key]["_inner_x"] * 100, 2), opening_top_cm=round(out[key]["_open_top_y"] * 100, 2))
            log(f"  feature {key}: {int(reg.sum())} vertices, {A[reg].sum() * 1e4:.2f} cm2")
    # islands: pieces of the main shell cut off from the rest by features (a concha inside an ear, a nostril's passage,
    # the socket behind an eye opening, the inside of a mouth) go to the features they border, each vertex to the one
    # nearest along the skin; a feature with an inside_word (the lips) passes what it gets to that word (the mouth)
    rest = main & ~claimed; lab, k = Gr.comps(rest)
    if k > 1:
        a = np.bincount(lab[lab >= 0], weights=A[lab >= 0], minlength=k); big = int(np.argmax(a))
        keys = list(out); isl = rest & (lab != big)
        best = np.full(len(Vs), np.inf); who = -np.ones(len(Vs), np.int64)
        for i, kk in enumerate(keys):
            dd = Gr.dist(out[kk]["mask"], np.inf, isl | out[kk]["mask"])
            better = isl & (dd < best); best[better] = dd[better]; who[better] = i
        Gc = Gr.G.tocoo(); own = -np.ones(len(Vs), np.int64)
        for i, kk in enumerate(keys):
            own[out[kk]["mask"]] = i
        for c in range(k):
            if c == big:
                continue
            e = (lab[Gc.row] == c) & (own[Gc.col] >= 0)
            log(f"  island {c}: {A[lab == c].sum() * 1e4:.2f} cm2 borders " + str({keys[j]: int(n) for j, n in enumerate(np.bincount(own[Gc.col[e]], minlength=len(keys))) if n}))
        for i, kk in enumerate(keys):
            m = isl & (who == i)
            if not m.any():
                continue
            sp = spec["parts"].get(out[kk]["word"], {}); iw = sp.get("inside_word")
            if iw:
                if iw not in out:
                    out[iw] = {"word": iw, "side": "", "mask": np.zeros(len(Vs), bool), "_top_y": -np.inf, "_cy": 0.0,
                               "info": {"how": f"inside the {out[kk]['word']}: the skin behind its opening, cut off from the rest of the {spec.get('on_word', 'part')} by it"}}
                out[iw]["mask"] |= m; out[iw]["info"].setdefault("islands", []).append(round(float(A[m].sum() * 1e4), 3))
            else:
                out[kk]["mask"] |= m; out[kk]["info"].setdefault("islands", []).append(round(float(A[m].sum() * 1e4), 3))
    # separate shells: one lying in a feature (its centre nearer that feature's skin than any other skin) joins it
    if nsh > 1:
        from scipy.spatial import cKDTree
        lab_v = -np.ones(len(Vs), np.int64); keys = list(out)
        for i, kk in enumerate(keys):
            lab_v[out[kk]["mask"]] = i
        T = cKDTree(Vs[main]); idx_main = np.nonzero(main)[0]
        for c in range(nsh):
            m = flab == c
            if (m & main).any():
                continue
            cen = (Vs[m] * A[m, None]).sum(0) / A[m].sum(); _, j = T.query(cen, k=min(50, int(main.sum())))
            own = lab_v[idx_main[np.atleast_1d(j)]]; own = own[own >= 0]
            if len(own) and (len(own) >= 0.5 * np.size(j)):
                kk = keys[int(np.bincount(own).argmax())]; out[kk]["mask"] |= m
                out[kk]["info"].setdefault("shells", []).append(round(float(A[m].sum() * 1e4), 2))
    # faces: a face goes to the feature holding the most of its corners (two or three of three); the rest stay
    res = []; flab_f = -np.ones(len(Fs), np.int64); keys = list(out)
    for i, kk in enumerate(keys):
        cnt = out[kk]["mask"][Fs].sum(1); flab_f[(cnt >= 2) & (flab_f < 0)] = i
    for i, kk in enumerate(keys):
        o = out[kk]; fsel = ff[flab_f == i]
        if not len(fsel):
            continue
        m = o["mask"]; info = o["info"]
        info.update(area_cm2=round(float(fa[flab_f == i].sum() * 1e4), 3), vertices=int(m.sum()),
                    extent_cm={"x": [round(float(x[m].min() * 100), 2), round(float(x[m].max() * 100), 2)],
                               "y": [round(float(y[m].min() * 100), 2), round(float(y[m].max() * 100), 2)],
                               "z": [round(float(z[m].min() * 100), 2), round(float(z[m].max() * 100), 2)]},
                    frame="the part's frame: x subject's left, y up its axis, z front; cm from its centre")
        res.append({"word": o["word"], "side": o["side"], "faces": fsel, "info": info})
    return res, rec
