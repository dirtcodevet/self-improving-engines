"""SHAPE DESCRIPTORS AND HANDLES for the target-driven loop (engine/loop/core.py). Domain-neutral names: a job maps
them to anatomy (or rock, or tree) in its own story and targets.

Descriptors (fn(state, **p) -> {key: value}); state = {"V": (n,3), "F": (m,3), ...masks}:
  profile_arcs     a surface's profile in a vertical plane (e.g. the back's midline): smoothed, its tangent angle from
                   vertical, the inflection points, and the turn (deg) of the convex and the concave arc between them,
                   plus the concave arc's hollow depth over its chord (H/L) - the surface-topography definition
                   (DIERS Formetric ICT-ITL-ILS tangents; references: packs/human/references/back_sagittal_profile.md)
  limb_sections    cross-sections perpendicular to a limb axis at stations: roundness (share of the perimeter that is
                   nearly flat), ellipse aspect, and the largest curvature jump round the section
Handles (.name .n .x0 .bounds .scale .apply(state, params)):
  SliceBend        bends the body about horizontal axes distributed over a height range (a spine bending): each slice
                   turns about its pivot line by the accumulated angle; below the range everything turns rigidly with
                   the last slice (the pelvis); masked parts (free limbs) are left alone
  NormalBumps      smooth bumps along the surface normal over a region (biharmonic basis: smooth by construction)
"""
import numpy as np
from scipy.ndimage import gaussian_filter1d


# ---------------------------------------------------------------------------------------------- profile_arcs
def _profile(V, F, plane_x, side, z_lo, z_hi, step):
    """outermost surface point per height bin on the plane x = plane_x, on the +y (side=+1) or -y side"""
    s = V[:, 0] - plane_x; sf = s[F]; cr = (sf.min(1) < 0) & (sf.max(1) > 0); T = F[cr]; st = s[T]; P = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        m = (st[:, a] < 0) != (st[:, b] < 0); va, vb = V[T[m, a]], V[T[m, b]]; sa, sb = st[m, a], st[m, b]
        P.append(va + (vb - va) * (sa / (sa - sb))[:, None])
    P = np.concatenate(P)
    zs = np.arange(z_hi, z_lo, -step); ys = np.full(len(zs), np.nan)
    win = max(step / 2, 0.003)          # a sampling window wider than the mesh spacing: a bin with no point on the wanted
    for i, z in enumerate(zs):          # side would otherwise take the far side's outermost point (found on woman2's back)
        m = np.abs(P[:, 2] - z) < win
        if m.any(): ys[i] = (P[m, 1] * side).max() * side
    ok = ~np.isnan(ys)
    return zs[ok], ys[ok]


def profile_arcs(state, plane_x=0.0, side=1, z_lo=-1.0, z_hi=1.0, step=0.001, smooth_mm=20.0, angle_smooth_mm=8.0, prefix="profile",
                 min_turn_deg=3.0):
    """two scales: smooth_mm (heavy) only to find where the curvature changes sign; angle_smooth_mm (light) to read
    the tangent angle there. Heavy smoothing alone blurs the tangent at an inflection, where it peaks, and under-read
    known arcs by 2-8 deg (test_shape.py). An inner arc turning less than min_turn_deg is a sliver (a flat stretch whose
    curvature sign flips with the surface's wobble) and is merged with its two neighbours: at 14 mm smoothing a 1-3 deg
    sliver in a flat lumbar stretch split the lordosis in two and the reading fell from 52 to 2 deg (woman2 v6)."""
    z, y = _profile(state["V"], state["F"], plane_x, side, z_lo, z_hi, step)
    ys = gaussian_filter1d(y, smooth_mm / (step * 1000), mode="nearest")
    dy = np.gradient(ys, z); ddy = np.gradient(dy, z)
    yl = gaussian_filter1d(y, angle_smooth_mm / (step * 1000), mode="nearest")
    phi = np.degrees(np.arctan(np.gradient(yl, z) * -1))      # tangent angle from vertical, walking down the profile
    conv = (ddy * side) < 0                                    # bulging outward on `side` (convex) vs hollow (concave)
    edge = int(smooth_mm / (step * 1000))                      # ignore the smoothing's end effects
    sl = slice(edge, len(z) - edge)
    zc, cc, pc, yc = z[sl], conv[sl], phi[sl], ys[sl]
    flips = np.where(cc[1:] != cc[:-1])[0] + 1
    bounds = np.r_[0, flips, len(zc) - 1]
    # each inflection found at the heavy scale is refined to where the light-scale tangent angle peaks nearby (the
    # tangent is extreme exactly at an inflection): without this, known arcs under-read by 2-4 deg (test_shape.py)
    win = max(1, int(smooth_mm / (step * 1000) / 2))
    ref = []
    for k, i in enumerate(bounds):
        if k == 0 or k == len(bounds) - 1:
            ref.append(i); continue
        lo, hi = max(0, i - win), min(len(pc), i + win + 1)
        # the arc above i bends one way: at its end the angle is a max if it was convex walking down, else a min
        seg = pc[lo:hi]
        ref.append(lo + int(np.argmax(seg) if not cc[i - 1] else np.argmin(seg)))
    arcs = []
    for a, b in zip(ref[:-1], ref[1:]):
        if b - a < 3: continue
        arcs.append(dict(convex=bool(cc[(a + b) // 2]), z_top=float(zc[a]), z_bot=float(zc[b]), turn_deg=float(abs(pc[b] - pc[a])),
                         a=int(a), b=int(b)))
    while len(arcs) > 2:                       # merge inner slivers, smallest first
        inner = [i for i in range(1, len(arcs) - 1) if arcs[i]["turn_deg"] < min_turn_deg]
        if not inner:
            break
        i = min(inner, key=lambda j: arcs[j]["turn_deg"]); a, b = arcs[i - 1]["a"], arcs[i + 1]["b"]
        arcs[i - 1:i + 2] = [dict(convex=arcs[i - 1]["convex"], z_top=float(zc[a]), z_bot=float(zc[b]),
                                  turn_deg=float(abs(pc[b] - pc[a])), a=int(a), b=int(b))]
    out = {}
    # arcs by position round the main concave arc (the largest): the convex arc just above it and just below it
    ccv = [i for i, r in enumerate(arcs) if not r["convex"]]
    if ccv:
        ic = max(ccv, key=lambda i: arcs[i]["turn_deg"]); c2 = arcs[ic]
        out.update({prefix + "_concave_turn_deg": c2["turn_deg"], prefix + "_concave_z_top": c2["z_top"], prefix + "_concave_z_bot": c2["z_bot"]})
        p0 = np.array([yc[c2["a"]], zc[c2["a"]]]); p1 = np.array([yc[c2["b"]], zc[c2["b"]]]); L = np.linalg.norm(p1 - p0)
        q = np.stack([yc[c2["a"]:c2["b"] + 1], zc[c2["a"]:c2["b"] + 1]], 1); u = (p1 - p0) / L
        d = np.abs((q - p0)[:, 0] * u[1] - (q - p0)[:, 1] * u[0])
        out.update({prefix + "_concave_hollow_mm": float(d.max() * 1000), prefix + "_concave_hollow_hl": float(d.max() / L)})
        for tag, j in (("above", ic - 1), ("below", ic + 1)):
            if 0 <= j < len(arcs) and arcs[j]["convex"]:
                out.update({prefix + "_convex_%s_turn_deg" % tag: arcs[j]["turn_deg"], prefix + "_convex_%s_z_top" % tag: arcs[j]["z_top"],
                            prefix + "_convex_%s_z_bot" % tag: arcs[j]["z_bot"]})
    out[prefix + "_arcs"] = len(arcs)
    return out


# ---------------------------------------------------------------------------------------------- SliceBend
class SliceBend:
    """params: K bend densities (deg per 100 mm) at evenly spaced heights over [z_bot, z_top] (piecewise linear);
    the accumulated angle below z_bot turns the rest rigidly. Pivot line = the profile (plane_x, side) moved inward by
    pivot_depth (the axis the slices turn about, e.g. the vertebral bodies). keep_mask: vertices left untouched."""

    def __init__(self, state, z_top, z_bot, k, pivot_depth, keep_mask=None, plane_x=0.0, side=1, bound_deg_per_100mm=15.0,
                 name="slice_bend", step=0.001, carrier_w=None, carrier_z=None, hold="top", rigid_band=None):
        """carrier_w (n,) in 0..1 with carrier_z: a vertex with weight w moves as the slice at height
        (1-w)*z + w*carrier_z (an arm rides with its shoulder's slice instead of the trunk slices beside it). carrier_z
        may be one height per vertex, so several parts ride their own attachments. rigid_band (z_hi, z_lo, taper): heights
        that move as one block (no bend there).
        hold: "top" keeps everything above the range in place and turns what is below; "bottom" keeps everything below
        the range in place (a pelvis that stands where it stands) and turns what is above (woman2 v6). Shape
        descriptors read the same either way (the two differ by one rigid motion); a lean or a position does not."""
        self.name, self.n = name, k
        self.x0 = np.zeros(k); self.bounds = (-np.full(k, bound_deg_per_100mm), np.full(k, bound_deg_per_100mm))
        self.scale = np.full(k, 2.0)
        self.z_top, self.z_bot, self.side = z_top, z_bot, side
        assert hold in ("top", "bottom")
        self.hold = hold
        self.keep = np.zeros(len(state["V"]), bool) if keep_mask is None else keep_mask
        self.cw, self.cz = carrier_w, carrier_z
        self.rigid_band = rigid_band
        V = state["V"]
        self.zg = np.arange(z_top, V[:, 2].min() - 2 * step, -step)
        z, y = _profile(V, state["F"], plane_x, side, V[:, 2].min() - step, z_top + step, step)
        y = gaussian_filter1d(y, 10, mode="nearest")
        self.py = np.interp(self.zg, z[::-1], y[::-1]) - side * pivot_depth   # pivot line y(z)

    def _maps(self, params):
        zg, dz = self.zg, self.zg[0] - self.zg[1]
        knots = np.linspace(self.z_top, self.z_bot, self.n)
        dens = np.interp(-zg, -knots, params, left=0.0, right=0.0)   # deg per 100 mm, zero outside the range
        dens[zg < self.z_bot] = 0.0
        if getattr(self, "rigid_band", None) is not None:
            # a block that moves as one (a rib cage carrying the breasts): no bend inside it, tapered over `taper` m at
            # each edge so the curve's own curvature does not step (woman2 v6 job 1b: a bend under stiff breasts creased
            # them, and a breast-only carrier creased their rim)
            hi, lo, tp = self.rigid_band
            w = np.clip(np.minimum(zg - lo, hi - zg) / tp, 0, 1); w = w * w * (3 - 2 * w)
            dens = dens * (1 - w)
        Phi = np.radians(np.r_[0.0, np.cumsum(dens * dz / 0.1)[:-1]])   # accumulated angle walking down (0 at the top)
        # new pivot line: each step's pivot segment turned by the accumulated angle
        P0 = np.stack([self.py, zg], 1); seg = np.diff(P0, axis=0, prepend=P0[:1])
        c, s = np.cos(Phi), np.sin(Phi)
        segr = np.stack([c * seg[:, 0] - s * seg[:, 1], s * seg[:, 0] + c * seg[:, 1]], 1)
        Pn = P0[0] + np.cumsum(segr, axis=0)
        return zg, dz, Phi, P0, Pn, c, s

    def move_points(self, params, P, w=None, cz=None):
        """the bend's map applied to any points P (n,3) - the skin, bone joints, a key's base positions - with carrier
        weights w (or None). Returns (moved points, each point's net turn in radians about x: an offset vector stored
        at the point, e.g. a corrective key's, turns by it)."""
        zg, dz, Phi, P0, Pn, c, s = self._maps(params)
        Q = np.array(P, float).copy()
        # carrier height: a scalar (one attachment, e.g. the shoulders' slice) or one height per point (each part rides
        # its own attachment: the breasts their chest wall, woman2 v6 job 1b, where slice-by-slice shear distorted the
        # nipple-areola relief); cz overrides for arbitrary points
        czz = cz if cz is not None else self.cz
        ze = Q[:, 2] if (w is None or czz is None) else (1 - w) * Q[:, 2] + w * czz
        # the slice transform interpolated between the two grid slices round each point (continuous in height: rounding
        # to the nearest slice made a 0.02-0.05 mm step that crossed two sheets 0.04 mm apart, woman2 v6)
        fi = np.clip((zg[0] - ze) / dz, 0, len(zg) - 1.000001); i0 = np.floor(fi).astype(int); t = fi - i0
        lerp = lambda A: A[i0] * (1 - t[:, None] if A.ndim > 1 else 1 - t) + A[i0 + 1] * (t[:, None] if A.ndim > 1 else t)
        ang = lerp(Phi); p0, pn = lerp(P0), lerp(Pn)
        q = np.stack([Q[:, 1], Q[:, 2]], 1) - p0
        ci, si = np.cos(ang), np.sin(ang)
        y = pn[:, 0] + ci * q[:, 0] - si * q[:, 1]
        z = pn[:, 1] + si * q[:, 0] + ci * q[:, 1]
        if self.hold == "bottom":       # undo the rigid motion of the slices below the range
            cb, sb = c[-1], s[-1]
            t = Pn[-1] - np.array([cb * P0[-1, 0] - sb * P0[-1, 1], sb * P0[-1, 0] + cb * P0[-1, 1]])
            y, z = y - t[0], z - t[1]
            y, z = cb * y + sb * z, -sb * y + cb * z
            ang = ang - Phi[-1]
        Q[:, 1], Q[:, 2] = y, z
        return Q, ang

    def apply(self, state, params):
        V = state["V"].copy(); m = ~self.keep
        Q, _ = self.move_points(params, V[m], None if self.cw is None else self.cw[m],
                                None if (self.cz is None or np.isscalar(self.cz)) else self.cz[m])
        V[m] = Q
        out = dict(state); out["V"] = V
        out[self.name + "_total_deg"] = float(np.degrees(self._maps(params)[2][-1]))   # the turn across the range
        return out


def state_value(state, key, default=0.0):
    """reads a number a handle left in the state (e.g. a bend's total turn) so a target can hold it"""
    return {key: float(state.get(key, default))}


# ---------------------------------------------------------------------------------------------- limb_sections
def limb_sections(state, head, tail, stations, region_mask, prefix="limb", n_bins=180):
    """sections perpendicular to the axis head->tail at the given fractions along it, over the faces of region_mask
    (the limb). Per station: flat share (share of the outline whose curvature is under a quarter of the outline's
    mean), aspect (minor/major of the second-moment ellipse), curvature jump (largest change of curvature between
    neighbouring outline samples over the mean curvature: unitless). Reported per station and over the stations."""
    V, F = state["V"], state["F"]
    head, tail = np.asarray(head, float), np.asarray(tail, float); ax = tail - head; Lax = np.linalg.norm(ax); ax /= Lax
    ref = np.array([0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(ax, ref); e1 /= np.linalg.norm(e1); e2 = np.cross(ax, e1)
    Fm = F[region_mask[F].all(1)]
    out, flats, asps, jumps = {}, [], [], []
    s0 = V @ ax; sf0 = s0[Fm]; flo, fhi = sf0.min(1), sf0.max(1)      # one projection per call, not per station
    for k, t in enumerate(stations):
        o = head + ax * Lax * t; c = float(o @ ax)
        s = s0 - c; cr = (flo < c) & (fhi > c); T = Fm[cr]; st = s[T]; P = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            m = (st[:, a] < 0) != (st[:, b] < 0); va, vb = V[T[m, a]], V[T[m, b]]; sa, sb = st[m, a], st[m, b]
            P.append(va + (vb - va) * (sa / (sa - sb))[:, None])
        P = np.concatenate(P) if P else np.zeros((0, 3))
        if len(P) < 20:
            continue
        q = np.stack([(P - o) @ e1, (P - o) @ e2], 1); q = q - q.mean(0)
        th = np.arctan2(q[:, 1], q[:, 0]); r = np.hypot(q[:, 0], q[:, 1])
        bins = np.linspace(-np.pi, np.pi, n_bins + 1); rb = np.full(n_bins, np.nan)
        idx = np.clip(np.digitize(th, bins) - 1, 0, n_bins - 1)
        for i in range(n_bins):
            m = idx == i
            if m.any(): rb[i] = r[m].max()
        ok = ~np.isnan(rb)
        if ok.sum() < n_bins * 0.8:
            continue
        rb = np.interp(np.arange(n_bins), np.where(ok)[0], rb[ok], period=n_bins)
        rb = gaussian_filter1d(rb, 1.5, mode="wrap")
        tc = (bins[:-1] + bins[1:]) / 2; x, y = rb * np.cos(tc), rb * np.sin(tc)
        dx, dy = np.gradient(x), np.gradient(y); ddx, ddy = np.gradient(dx), np.gradient(dy)
        kap = (dx * ddy - dy * ddx) / np.maximum((dx * dx + dy * dy) ** 1.5, 1e-12)
        seg = np.hypot(dx, dy); per = seg.sum(); kmean = 2 * np.pi / per
        flat = float(seg[kap < 0.25 * kmean].sum() / per)
        C = np.cov(np.stack([x, y])); ev = np.sort(np.linalg.eigvalsh(C)); asp = float(np.sqrt(ev[0] / ev[1]))
        jump = float(np.abs(np.diff(np.r_[kap, kap[:1]])).max() / kmean)
        out.update({"%s_s%d_flat" % (prefix, k): flat, "%s_s%d_aspect" % (prefix, k): asp, "%s_s%d_jump" % (prefix, k): jump})
        flats.append(flat); asps.append(asp); jumps.append(jump)
    if flats:
        out.update({prefix + "_flat_mean": float(np.mean(flats)), prefix + "_flat_max": float(np.max(flats)),
                    prefix + "_aspect_mean": float(np.mean(asps)), prefix + "_jump_max": float(np.max(jumps)),
                    prefix + "_stations_ok": len(flats)})
    return out


# ---------------------------------------------------------------------------------------------- NormalBumps
class NormalBumps:
    """smooth displacement along the normal (or a given direction field) over a region: params = amplitudes (m) of K
    bumps centred at given vertices, each a biharmonic bump (bi-Laplacian solve over the region, the centre's 1-ring
    held at 1, everything outside the region at 0): smooth, and tangent to the surroundings at the region's rim."""

    def __init__(self, state, region, centres, bound_m=0.01, name="normal_bumps", direction=None):
        from scipy import sparse
        from scipy.sparse.linalg import splu
        V, F = state["V"], state["F"]; n = len(V)
        E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
        A = sparse.coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(n, n)).tocsr()
        A.data[:] = 1.0
        L = sparse.eye(n) - sparse.diags(1 / np.maximum(np.asarray(A.sum(1)).ravel(), 1)) @ A
        Q = (L.T @ L).tocsr()
        B = np.where(region)[0]; pos = -np.ones(n, int); pos[B] = np.arange(len(B))
        Qbb = Q[B][:, B].tocsr()
        self.basis = []
        for c in centres:
            ring = np.unique(np.r_[c, A[c].indices]); ring = ring[region[ring]]
            held = np.zeros(len(B), bool); held[pos[ring]] = True
            phi = np.zeros(len(B)); phi[held] = 1.0
            phi[~held] = splu(Qbb[~held][:, ~held].tocsc()).solve(-(Qbb[~held][:, held] @ phi[held]))
            full = np.zeros(n); full[B] = np.clip(phi, 0, None); self.basis.append(full)
        self.basis = np.array(self.basis)
        fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); vn = np.zeros_like(V)
        for k in range(3): np.add.at(vn, F[:, k], fn)
        self.dir = direction if direction is not None else vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-20)
        self.name, self.n = name, len(centres)
        self.x0 = np.zeros(self.n); self.bounds = (-np.full(self.n, bound_m), np.full(self.n, bound_m)); self.scale = np.full(self.n, 0.002)

    def apply(self, state, params):
        out = dict(state); out["V"] = state["V"] + (params @ self.basis)[:, None] * self.dir
        return out


class RigidTurn:
    """the whole body turned rigidly about a horizontal axis (x) through a pivot (y, z): how it stands over its feet.
    Paired with SliceBend, the bend changes the shape and the turn restores balance (woman2 v6, job 1b: with the chest
    held, a pelvic tilt alone swung the hips 105 mm forward). params: [angle_deg]. Same rotation sense as SliceBend."""

    def __init__(self, pivot_yz, bound_deg=8.0, name="rigid_turn"):
        self.pivot = np.asarray(pivot_yz, float); self.name, self.n = name, 1
        self.x0 = np.zeros(1); self.bounds = (np.array([-bound_deg]), np.array([bound_deg])); self.scale = np.array([1.0])

    def apply(self, state, params):
        a = np.radians(float(params[0])); c, s = np.cos(a), np.sin(a)
        V = state["V"].copy(); q = V[:, 1:3] - self.pivot
        V[:, 1] = self.pivot[0] + c * q[:, 0] - s * q[:, 1]; V[:, 2] = self.pivot[1] + s * q[:, 0] + c * q[:, 1]
        out = dict(state); out["V"] = V; out[self.name + "_deg"] = float(params[0])
        return out
