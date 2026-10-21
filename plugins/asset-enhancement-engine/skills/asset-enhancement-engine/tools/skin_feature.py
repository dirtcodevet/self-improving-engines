"""skin_feature.py - a feature ZONE on one continuous skin, built in its own layers: layered relief (a raised mound,
discrete glands, a central papilla), micro-texture (ring-wise and radial wrinkles, fine noise, pits), a radial pigment
profile and per-vertex material qualities; every quality a named parameter, every random choice from one seed.

Why it exists (woman2 Stage 4, 2026-10-19).  The person asked for "a unique and proper way ... to create the nipples
and areolas, with the coloring and unique skin textures and qualities of a real breast" (cases/woman2/NAC_DESIGN.md).
The earlier nipple was a height bump on the fitted mesh at 0.23 mm edges (Stage 1): one layer, no glands, no texture,
pigment as two flat zone colours.  The engine already builds features as a zone on one skin (the cat's nose leather
and lips); this is that pattern as a general builder: the CORE is domain-neutral (zones, mounds, bumps, rings, a
surface of revolution, pits, a pigment profile), the DATA (what a human nipple-areola complex is) lives in a pack
(engine/packs/human/nac_female.json), and the case gives only the place, the frame and the size.

Method, in the feature's own frame (J14: centre C on the skin, axis n = the feature's normal, e1/e2 in its plane):
  1. patch: the faces within `patch_radius` of C (plane distance, near the surface, connected) are removed; the
     hole's rim stays (its vertices and every face outside are untouched, so the skin stays one closed surface);
  2. rings: concentric rings inside the rim at the resolution the layers need (h(r) per radius band), zipped ring to
     ring by angle; the papilla's rings map onto its own profile (a surface of revolution), so its side walls get
     real vertices instead of stretched height-field faces;
  3. base: the skin under the feature is the skin's own continuation - a polynomial height field in the frame fitted
     on an annulus outside the old feature (the old relief is not copied), corrected at the rim so it meets the
     kept skin exactly;
  4. relief layers (heights along n, or radial on the papilla): mound (rise, soft margin, low-frequency margin
     irregularity), bumps (Poisson-disk glands in a ring band), papilla (base flare, body, rounded cap; corrugation
     fissures wrapping round it; pits on the cap), micro (ring and radial wrinkles, fine noise) - the micro layer is
     also returned separately (`micro`), so it can be switched off (a shape key);
  5. zones and material: per-vertex weights (feature zone with its pigment profile's soft margin, papilla, glands),
     pigment colour from a radial profile r/R -> strength times the zone colours, roughness, translucency scale.

What it cannot see: the base is a height field over the patch (a feature on a surface that folds over itself within
the patch radius is out of scope); very small pits (< 2 vertices across at the chosen resolution) become shading only.

API:  build(v, f, spec, seed) -> dict(v, f, new_ids, keep_map, micro, attrs, report)
      prove() -> a sphere with a planted old bump: the bump is not copied, the rim is exact, the mesh stays closed
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


# ------------------------------------------------------------------------------------------------ small helpers
def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def frame(axis, up_hint=(0.0, 0.0, 1.0)):
    n = np.asarray(axis, float)
    n = n / np.linalg.norm(n)
    u = np.asarray(up_hint, float)
    e1 = u - n * (u @ n)
    if np.linalg.norm(e1) < 1e-6:
        e1 = np.array([1.0, 0, 0]) - n * n[0]
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    return e1, e2, n


class Noise2:
    """smooth band-limited noise on the plane (random Fourier features), zero mean, ~unit RMS; deterministic"""

    def __init__(self, rng, wavelength, n=24):
        k = 2 * np.pi / wavelength
        ang = rng.uniform(0, 2 * np.pi, n)
        mag = k * rng.uniform(0.7, 1.4, n)
        self.w = np.c_[np.cos(ang) * mag, np.sin(ang) * mag]
        self.p = rng.uniform(0, 2 * np.pi, n)
        self.a = np.sqrt(2.0 / n)

    def __call__(self, x, y):
        return self.a * np.sin(np.c_[x, y] @ self.w.T + self.p).sum(1)


class Noise1:
    """smooth periodic noise of an angle (low harmonics), zero mean, ~unit RMS"""

    def __init__(self, rng, harmonics=(2, 3, 4, 5)):
        self.h = np.array(harmonics)
        self.c = rng.normal(0, 1, (len(harmonics), 2)) / np.sqrt(len(harmonics))

    def __call__(self, th):
        th = np.asarray(th)
        return (self.c[:, 0][:, None] * np.cos(self.h[:, None] * th) + self.c[:, 1][:, None] * np.sin(self.h[:, None] * th)).sum(0)


def poisson_disk(rng, n_target, r_min, r_max, d_min, density, tries=20000):
    """points in the annulus [r_min, r_max] at least d_min apart, accepted with probability density(r) (0..1)"""
    pts = []
    for _ in range(tries):
        if len(pts) >= n_target:
            break
        r = math.sqrt(rng.uniform(r_min ** 2, r_max ** 2))
        t = rng.uniform(0, 2 * np.pi)
        if rng.uniform() > density(r):
            continue
        p = np.array([r * math.cos(t), r * math.sin(t)])
        if all(np.hypot(*(p - q)) >= d_min for q in pts):
            pts.append(p)
    return np.array(pts).reshape(-1, 2)


def face_adjacency_components(f, sel):
    """connected components of the selected faces (sharing an edge)"""
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    idx = np.nonzero(sel)[0]
    F = f[idx]
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    E = np.sort(E, 1)
    key = E[:, 0].astype(np.int64) * (f.max() + 1) + E[:, 1]
    fid = np.tile(np.arange(len(idx)), 3)
    o = np.argsort(key)
    k2 = key[o]
    same = np.nonzero(k2[1:] == k2[:-1])[0]
    a, b = fid[o][same], fid[o][same + 1]
    A = sparse.coo_matrix((np.ones(len(a)), (a, b)), shape=(len(idx), len(idx)))
    nc, lab = connected_components(A, directed=False)
    return idx, lab


def boundary_loop(f_kept_removed):
    """the single boundary loop of a disc of faces, ordered (vertex ids), following the faces' winding"""
    F = f_kept_removed
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    und = np.sort(E, 1)
    key = und[:, 0].astype(np.int64) * (F.max() + 1) + und[:, 1]
    u, cnt = np.unique(key, return_counts=True)
    bset = set(u[cnt == 1].tolist())
    nxt = {}
    for (a, b), k in zip(E, key):
        if int(k) in bset:
            nxt[int(a)] = int(b)
    start = next(iter(nxt))
    loop = [start]
    while True:
        c = nxt[loop[-1]]
        if c == start:
            break
        loop.append(c)
        if len(loop) > len(nxt) + 2:
            raise RuntimeError('boundary is not one loop')
    if len(loop) != len(nxt):
        raise RuntimeError('patch boundary has %d loops' % (1 + (len(nxt) != len(loop))))
    return np.array(loop)


def zip_rings(A_ids, A_ang, B_ids, B_ang):
    """triangles between ring A (outer) and ring B (inner), both sorted by increasing angle (cyclic); returns faces
    (outer_i, outer_i+1, inner_j) / (outer_i, inner_j+1, inner_j): counter-clockwise about the frame normal"""
    na, nb = len(A_ids), len(B_ids)
    # rotate B so its first angle is the closest at or after A's first
    a0 = A_ang[0]
    db = np.mod(B_ang - a0, 2 * np.pi)
    j0 = int(np.argmin(db))
    B_ids = np.roll(B_ids, -j0)
    B_ang = np.roll(B_ang, -j0)
    ua = np.unwrap(A_ang)
    ua = np.r_[ua, ua[0] + 2 * np.pi]
    ub = np.unwrap(B_ang)
    while ub[0] < ua[0] - np.pi:
        ub += 2 * np.pi
    ub = np.r_[ub, ub[0] + 2 * np.pi]
    i = j = 0
    out = []
    while i < na or j < nb:
        if j >= nb or (i < na and ua[i + 1] <= ub[j + 1]):
            out.append((A_ids[i % na], A_ids[(i + 1) % na], B_ids[j % nb]))
            i += 1
        else:
            out.append((A_ids[i % na], B_ids[(j + 1) % nb], B_ids[j % nb]))
            j += 1
    return out


# ------------------------------------------------------------------------------------------------ the profile of a papilla
def papilla_profile(p, n=4000):
    """the papilla's profile as an arc-length table from the tip: (s, rho, t).  p: radius, projection, cap_height,
    flare_width, flare_height (m).  Base flare (a concave fillet into the zone), a body, a rounded (elliptic) cap.
    Or p['profile'] = [[rho / radius, t / projection], ...] from the tip (0, 1) to the foot (rho_f, 0): a measured
    profile, interpolated monotonically (PCHIP over the chord length, no overshoot)."""
    if p.get('profile'):
        from scipy.interpolate import PchipInterpolator
        Q = np.array(p['profile'], float) * np.array([p['radius'], p['projection']])
        u = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
        uu = np.linspace(0, u[-1], n)
        P = np.c_[PchipInterpolator(u, Q[:, 0])(uu), PchipInterpolator(u, Q[:, 1])(uu)]
        ds = np.linalg.norm(np.diff(P, axis=0), axis=1)
        s = np.r_[0, np.cumsum(ds)]
        return s, P[:, 0], P[:, 1]
    r, H, c, fw, fh = p['radius'], p['projection'], p['cap_height'], p['flare_width'], p['flare_height']
    c = min(c, H - 1e-5)
    fh = min(fh, H - c)
    # cap: ellipse quadrant from the tip (0, H) to (r, H - c)
    a_ = np.linspace(0, np.pi / 2, n // 2)
    cap = np.c_[r * np.sin(a_), H - c + c * np.cos(a_)]
    # body: (r, H - c) down to (r, fh)
    body = np.c_[np.full(n // 4, r), np.linspace(H - c, fh, n // 4)]
    # flare: quarter circle concave, from (r, fh) to (r + fw, 0)
    b_ = np.linspace(0, np.pi / 2, n // 4)
    fl = np.c_[r + fw - fw * np.cos(b_), fh - fh * np.sin(b_)]
    P = np.concatenate([cap, body[1:], fl[1:]])
    ds = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.r_[0, np.cumsum(ds)]
    return s, P[:, 0], P[:, 1]


# ------------------------------------------------------------------------------------------------ the build
def build(v, f, spec, seed):
    """spec keys (lengths in metres):
       centre, axis, up_hint, zone_radius (R), patch_radius, base_fit=(r_in, r_out, degree),
       resolution=[[r_max, h], ...] (ascending r_max; the papilla uses papilla.h),
       mound={rise, margin_in, margin_out, irregularity, irregularity_harmonics},
       bumps={count, ring=(lo, hi) as r/R, size=(lo, hi) diameters, height=(lo, hi), d_min, ring_weight},
       papilla={radius, projection, cap_height, flare_width, flare_height, h,
                corrugation={wavelength, depth, wander}, pits={count, cluster_r (r/radius), size, depth},
                texture={wavelength, amp}},
       micro={ring={wavelength, amp, wander}, radial={wavelength, amp}, noise={wavelength, amp}, zone=(in, out) r/R},
       pigment={profile_r=[...] (r/R), profile_s=[...] strength, angular_amp, colours={zone, papilla, glands_lighten}},
       material={roughness={skin, zone, papilla}, translucency={skin, zone}}
    """
    rng = np.random.default_rng(seed)
    C = np.asarray(spec['centre'], float)
    e1, e2, n = frame(spec['axis'], spec.get('up_hint', (0, 0, 1)))
    R = spec['zone_radius']
    Rp = spec['patch_radius']
    d = v - C
    hv = d @ n
    uv = np.c_[d @ e1, d @ e2]
    rv = np.hypot(uv[:, 0], uv[:, 1])
    # ---------------- 1. the patch
    inside_v = (rv < Rp) & (np.abs(hv) < spec.get('height_window', 0.03))
    sel = inside_v[f].all(1)
    idx, lab = face_adjacency_components(f, sel)
    # the component holding the face nearest the centre
    fc = v[f[idx]].mean(1)
    k0 = int(np.argmin(np.linalg.norm(fc - C, axis=1)))
    rem = idx[lab == lab[k0]]
    loop = boundary_loop(f[rem])
    used_rem = np.unique(f[rem])
    interior = np.setdiff1d(used_rem, loop)
    # loop orientation about n in the plane: we want increasing angle (CCW about n) for the zipper; record whether
    # the loop as given (the removed faces' winding) runs CCW
    la = np.arctan2(uv[loop, 1], uv[loop, 0])
    ccw = np.sum(np.angle(np.exp(1j * np.diff(np.r_[la, la[0]])))) > 0
    # ---------------- 2. base surface (the skin's own continuation)
    bi, bo, deg = spec['base_fit']
    ann = (rv > bi) & (rv < bo) & (np.abs(hv) < spec.get('height_window', 0.03))
    X, Y = uv[ann, 0], uv[ann, 1]
    terms = [(i, j) for i in range(deg + 1) for j in range(deg + 1 - i)]
    A = np.stack([X ** i * Y ** j for i, j in terms], 1)
    sc = max(bo, 1e-3)
    As = np.stack([(X / sc) ** i * (Y / sc) ** j for i, j in terms], 1)
    coef = np.linalg.lstsq(As, hv[ann], rcond=None)[0]

    def base_h(x, y):
        return np.stack([(x / sc) ** i * (y / sc) ** j for i, j in terms], 1) @ coef
    # rim correction (angle-interpolated, faded inward)
    lr = rv[loop]
    res = hv[loop] - base_h(uv[loop, 0], uv[loop, 1])
    o = np.argsort(la)
    la_s, res_s = la[o], res[o]
    fade_in = spec.get('rim_fade_in', R + 0.001)

    def corr(x, y):
        t = np.arctan2(y, x)
        rr = np.hypot(x, y)
        c_ = np.interp(t, la_s, res_s, period=2 * np.pi)
        r_rim = np.interp(t, la_s, lr[o], period=2 * np.pi)
        return c_ * smoothstep((rr - fade_in) / np.maximum(r_rim - fade_in, 1e-4))
    rep = dict(patch_faces_removed=int(len(rem)), interior_vertices_removed=int(len(interior)), rim_vertices=int(len(loop)),
               rim_radius_mm=[round(float(lr.min() * 1e3), 2), round(float(lr.max() * 1e3), 2)],
               base_fit_rms_mm=round(float(np.sqrt(np.mean((As @ coef - hv[ann]) ** 2)) * 1e3), 4),
               rim_residual_mm_max=round(float(np.abs(res).max() * 1e3), 3))
    # ---------------- 3. rings
    pap = spec['papilla']
    s_tab, rho_tab, t_tab = papilla_profile(pap)
    L_pap = s_tab[-1]
    r_pb = float(rho_tab[-1]) if pap.get('profile') else pap['radius'] + pap['flare_width']   # the papilla's foot
    res_tab = spec['resolution']

    def h_at(r):
        for rmax, h in res_tab:
            if r <= rmax:
                return h
        return res_tab[-1][1]
    rings = []   # list of (plane_r, kind, s or None)
    r = lr.min() - 0.5 * h_at(lr.min())
    while r > r_pb + 0.5 * h_at(r_pb + 1e-6):
        rings.append((r, 'zone', None))
        r -= 0.866 * h_at(r)
    # papilla rings by arc length from the foot (s = L) to near the tip
    hp = pap['h']
    ns = max(int(L_pap / (0.866 * hp)), 4)
    for k in range(ns):
        s = L_pap * (1 - k / ns)
        if s < 0.6 * hp:
            break
        rings.append((None, 'papilla', s))
    # vertices
    newV, newA, kinds, ring_ids = [], [], [], []
    base_id = len(v)
    cur = base_id
    noise_margin = Noise1(rng, tuple(spec['mound'].get('irregularity_harmonics', (2, 3, 4, 5))))
    for (rp, kind, s) in rings:
        if kind == 'zone':
            npts = max(int(math.ceil(2 * np.pi * rp / h_at(rp))), 8)
            rho = rp
        else:
            rho = float(np.interp(s, s_tab, rho_tab))
            npts = max(int(math.ceil(2 * np.pi * rho / hp)), 6)
        off = rng.uniform(0, 2 * np.pi / npts)
        th = off + 2 * np.pi * np.arange(npts) / npts
        ring_ids.append((np.arange(cur, cur + npts), th, kind, rp if kind == 'zone' else rho, s))
        cur += npts
    tip_id = cur
    # ---------------- 4. relief
    mo = spec['mound']
    bm = spec.get('bumps', {})
    mic = spec['micro']
    pigs = spec['pigment']
    # gland positions
    if bm and bm.get('count', 0) > 0:
        ring_lo, ring_hi = bm['ring']
        dens = lambda rr: (bm.get('ring_weight', 0.6) + (1 - bm.get('ring_weight', 0.6)) *
                           smoothstep((rr / R - ring_lo) / max(ring_hi - ring_lo, 1e-6)))
        G = poisson_disk(rng, bm['count'], ring_lo * R, ring_hi * R, bm['d_min'], dens)
        g_r = rng.uniform(bm['size'][0], bm['size'][1], len(G)) / 2
        g_h = rng.uniform(bm['height'][0], bm['height'][1], len(G))
    else:
        G = np.zeros((0, 2))
        g_r = g_h = np.zeros(0)
    n_ring = Noise2(rng, mic['ring'].get('wander', 0.004))
    n_ramp = Noise2(rng, 0.003)
    n_fine = Noise2(rng, mic['noise']['wavelength'])
    n_fine2 = Noise2(rng, mic['noise']['wavelength'] * 0.55)
    cor = pap.get('corrugation', {})
    n_cor = Noise2(rng, cor.get('wander', 0.003))
    ptex = pap.get('texture', {})
    n_ptex = Noise2(rng, ptex.get('wavelength', 0.0003))
    pits = pap.get('pits', {})
    if pits and pits.get('count', 0) > 0:
        Pp = poisson_disk(rng, pits['count'], 0.0, pits['cluster_r'] * pap['radius'], pits['size'][1] * 1.6, lambda rr: 1.0)
        p_r = rng.uniform(pits['size'][0], pits['size'][1], len(Pp)) / 2
        p_d = rng.uniform(pits['depth'][0], pits['depth'][1], len(Pp))
    else:
        Pp = np.zeros((0, 2))
        p_r = p_d = np.zeros(0)
    Rm = lambda th: R * (1 + mo.get('irregularity', 0.0) * noise_margin(th))
    if len(G):
        # the glands stay inside the zone's own (irregular) edge: the band is relative to R(theta), not to R
        gth = np.arctan2(G[:, 1], G[:, 0])
        inside_g = np.hypot(G[:, 0], G[:, 1]) + g_r < bm['ring'][1] * Rm(gth)
        G, g_r, g_h = G[inside_g], g_r[inside_g], g_h[inside_g]

    def mound(x, y):
        rr = np.hypot(x, y)
        th = np.arctan2(y, x)
        t = rr / Rm(th)
        return mo['rise'] * (1 - smoothstep((t - mo['margin_in']) / (mo['margin_out'] - mo['margin_in'])))

    def glands(x, y):
        out = np.zeros(len(x))
        msk = np.zeros(len(x))
        for (gx, gy), gr, gh in zip(G, g_r, g_h):
            dd = np.hypot(x - gx, y - gy) / gr
            m = dd < 1
            out[m] += gh * (1 - dd[m] ** 2) ** 2
            msk[m] = np.maximum(msk[m], (1 - dd[m] ** 2))
        return out, msk

    def micro_zone(x, y):
        rr = np.hypot(x, y)
        th = np.arctan2(y, x)
        zi, zo = mic['zone']
        w = smoothstep((rr / R - zi) / 0.08) * (1 - smoothstep((rr / R - zo) / 0.12))
        ph = 2 * np.pi * rr / mic['ring']['wavelength'] + mic['ring'].get('phase_wander', 1.2) * n_ring(x, y)
        amp_mod = 0.55 + 0.45 * np.tanh(1.5 * n_ramp(x, y))
        rings_ = mic['ring']['amp'] * amp_mod * (np.cos(ph) ** 3)
        nrad = max(int(2 * np.pi * R / mic['radial']['wavelength']), 8)
        radial = mic['radial']['amp'] * np.sin(nrad * th + 3.0 * n_ring(y, x)) * smoothstep(rr / R)
        fine = mic['noise']['amp'] * (0.6 * n_fine(x, y) + 0.4 * n_fine2(x, y))
        return w * (rings_ + radial + fine)
    allP, allMicro, allKind, allR, allS, allTh = [], [], [], [], [], []
    for ids, th, kind, rr_, s in ring_ids:
        if kind == 'zone':
            x, y = rr_ * np.cos(th), rr_ * np.sin(th)
            gl, _ = glands(x, y)
            mic_h = micro_zone(x, y)
            hgt = base_h(x, y) + corr(x, y) + mound(x, y) + gl + mic_h
            P = C + np.outer(x, e1) + np.outer(y, e2) + np.outer(hgt, n)
            allMicro.append(mic_h)
        else:
            rho = rr_
            t_ = float(np.interp(s, s_tab, t_tab))
            x, y = rho * np.cos(th), rho * np.sin(th)
            # corrugation: circumferential fissures along the body (radial inward), weaker on the cap
            onb = smoothstep((t_ - pap['flare_height']) / 0.0005) * (1 - smoothstep((t_ - (pap['projection'] - 0.3 * pap['cap_height'])) / 0.0008))
            fis = 0.0
            if cor:
                ph = 2 * np.pi * s / cor['wavelength'] + 2.0 * n_cor(x * 2, y * 2)
                fis = -cor['depth'] * np.clip(np.cos(ph), 0, 1) ** 6 * (cor.get('cap_factor', 0.15) + (1 - cor.get('cap_factor', 0.15)) * onb)
            # pits on the cap (near the tip)
            pit = np.zeros(len(th))
            for (px, py), pr, pd in zip(Pp, p_r, p_d):
                dd = np.hypot(x - px, y - py) / pr
                m = (dd < 1) & (t_ > pap['projection'] - pap['cap_height'])
                pit[m] -= pd * (1 - dd[m] ** 2) ** 2
            fine = pap.get('fine_noise_factor', 1.0) * mic['noise']['amp'] * (0.6 + 0.6 * (1 - onb)) * n_fine(x * 1.7, y * 1.7)
            if ptex:
                # the papilla's own pebbly texture (nipple skin), over body and cap
                fine = fine + ptex['amp'] * n_ptex(x + 0.37 * t_, y - 0.29 * t_)
            base_here = base_h(x * 0 + rho * np.cos(th), rho * np.sin(th)) + corr(x, y) + mound(x, y)
            # the papilla stands on the mound at its foot radius: heights along n; corrugation moves radially
            mic_r = fis + fine
            rr2 = rho + mic_r * (1 - smoothstep((t_ - (pap['projection'] - 0.6 * pap['cap_height'])) / 0.0006))
            hgt = base_here + t_ + pit + mic_r * smoothstep((t_ - (pap['projection'] - 0.6 * pap['cap_height'])) / 0.0006)
            P = C + np.outer(rr2 * np.cos(th), e1) + np.outer(rr2 * np.sin(th), e2) + np.outer(hgt, n)
            allMicro.append(mic_r + pit)
        allP.append(P)
        allKind.append(np.full(len(th), 0 if kind == 'zone' else 1))
        allR.append(np.full(len(th), rr_ if kind == 'zone' else -1.0))
        allS.append(np.full(len(th), -1.0 if kind == 'zone' else s))
        allTh.append(th)
    # tip
    t_tip = pap['projection']
    tip = C + n * (base_h(np.zeros(1), np.zeros(1))[0] + mound(np.zeros(1), np.zeros(1))[0] + t_tip)
    newP = np.concatenate(allP + [tip[None]])
    micro_new = np.concatenate(allMicro + [np.zeros(1)])
    kind_new = np.concatenate(allKind + [np.ones(1, int)])
    r_new = np.concatenate(allR + [np.full(1, -1.0)])
    s_new = np.concatenate(allS + [np.zeros(1)])
    th_new = np.concatenate(allTh + [np.zeros(1)])
    # ---------------- faces
    faces = []
    # rim (the kept loop) to the first ring; the loop sorted by increasing angle
    if ccw:
        rim_ids, rim_ang = loop, la
    else:
        rim_ids, rim_ang = loop[::-1], la[::-1]
    prev_ids, prev_ang = rim_ids, rim_ang
    for ids, th, kind, rr_, s in ring_ids:
        faces += zip_rings(prev_ids, prev_ang, ids, th)
        prev_ids, prev_ang = ids, th
    # fan to the tip
    m_ = len(prev_ids)
    for i in range(m_):
        faces.append((prev_ids[i], prev_ids[(i + 1) % m_], tip_id))
    faces = np.array(faces, np.int64)
    # orientation: the kept faces around the rim traverse the rim edges in one direction; our faces must traverse
    # them the opposite way
    keep_f = np.ones(len(f), bool)
    keep_f[rem] = False
    Fk = f[keep_f]
    rim_set = set(loop.tolist())
    kept_dir = {}
    for a_, b_ in np.concatenate([Fk[:, [0, 1]], Fk[:, [1, 2]], Fk[:, [2, 0]]]):
        if int(a_) in rim_set and int(b_) in rim_set:
            kept_dir[(int(a_), int(b_))] = True
    flip = False
    for a_, b_, c_ in faces[:50]:
        for x_, y_ in ((a_, b_), (b_, c_), (c_, a_)):
            if (int(x_), int(y_)) in kept_dir:
                flip = True
    if flip:
        faces = faces[:, ::-1]
    # ---------------- assemble: drop interior vertices, renumber
    V_all = np.concatenate([v, newP])
    F_all = np.concatenate([Fk, faces])
    keepv = np.ones(len(V_all), bool)
    keepv[interior] = False
    remap = -np.ones(len(V_all), np.int64)
    remap[keepv] = np.arange(keepv.sum())
    F_out = remap[F_all]
    V_out = V_all[keepv]
    keep_map = remap[:len(v)]              # old vertex -> new id (-1 removed)
    new_ids = remap[len(v):]
    # ---------------- zones, pigment, material
    rr_all = np.hypot((newP - C) @ e1, (newP - C) @ e2)
    th_all = np.arctan2((newP - C) @ e2, (newP - C) @ e1)
    x_all, y_all = rr_all * np.cos(th_all), rr_all * np.sin(th_all)
    pr_ = np.array(pigs['profile_r'])
    ps_ = np.array(pigs['profile_s'])
    ang_noise = Noise1(rng, (1, 2, 3))
    t_rel = rr_all / Rm(th_all)
    zone_s = np.interp(t_rel, pr_, ps_, right=0.0) * (1 + pigs.get('angular_amp', 0.0) * ang_noise(th_all))
    zone_s = np.where(kind_new == 1, 1.0, zone_s)
    zone_w = np.clip(np.interp(t_rel, [0, mo['margin_out'] * 0.95, mo['margin_out'] * 1.05], [1, 1, 0]), 0, 1)
    zone_w = np.where(kind_new == 1, 1.0, zone_w)
    # papilla weight: 1 on the papilla rings, a short fade into the zone beyond its foot
    pap_w = np.where(kind_new == 1, 1.0, 1 - smoothstep((rr_all - r_pb) / 0.0008))
    _, gmask = glands(x_all, y_all)
    gmask = np.where(kind_new == 1, 0.0, gmask)
    rep.update(new_vertices=int(len(newP)), new_faces=int(len(faces)), rings=len(ring_ids), glands=int(len(G)),
               pits=int(len(Pp)), papilla_profile_length_mm=round(float(L_pap * 1e3), 3), flipped=bool(flip),
               gland_positions_mm=np.round(G * 1e3, 2).tolist(), gland_diam_mm=np.round(2 * g_r * 1e3, 3).tolist(),
               gland_height_mm=np.round(g_h * 1e3, 3).tolist())
    attrs = dict(zone_pigment=zone_s, zone_weight=zone_w, papilla=pap_w, glands=gmask, kind=kind_new,
                 frame=np.stack([e1, e2, n]), centre=C)
    return dict(v=V_out, f=F_out, new_ids=new_ids, keep_map=keep_map, micro=micro_new, attrs=attrs, report=rep,
                normal=n, rim=remap[loop])


# ------------------------------------------------------------------------------------------------ proof
def _icosphere(level):
    t = (1 + 5 ** 0.5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1),
         (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7),
         (9, 8, 1)]
    V = [np.array(p, float) / np.linalg.norm(p) for p in V]
    for _ in range(level):
        mid = {}
        F2 = []

        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                p = (V[a] + V[b]) / 2
                V.append(p / np.linalg.norm(p))
                mid[k] = len(V) - 1
            return mid[k]
        for a, b, c in F:
            ab, bc, ca = m(a, b), m(b, c), m(c, a)
            F2 += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        F = F2
    return np.array(V), np.array(F)


def prove(out_path=None):
    """known answers: a 60 mm sphere carrying a planted 4 mm 'old' bump at the pole; a feature rebuilt there.
    Pass when: the mesh is closed and manifold with consistent winding; every kept vertex is unchanged; the old bump
    is gone (the base under the feature is the sphere: off by < 0.05 mm at the zone's edge, where only the mound
    acts); the papilla tip stands at base + mound + projection; glands and pits are present."""
    V, F = _icosphere(6)
    V = V * 0.06
    pole = np.array([0, 0, 0.06])
    dd = np.linalg.norm(V - pole, axis=1)
    V = V + (V / np.linalg.norm(V, axis=1, keepdims=True)) * (0.004 * np.exp(-(dd / 0.006) ** 2))[:, None]
    spec = dict(centre=[0, 0, 0.06], axis=[0, 0, 1], up_hint=[0, 1, 0], zone_radius=0.012, patch_radius=0.018,
                base_fit=(0.020, 0.032, 4), resolution=[[0.012, 0.0004], [1.0, 0.0012]],
                mound=dict(rise=0.001, margin_in=0.6, margin_out=1.1, irregularity=0.03),
                bumps=dict(count=10, ring=(0.6, 0.95), size=(0.0008, 0.0012), height=(0.0002, 0.0004), d_min=0.0018, ring_weight=0.5),
                papilla=dict(radius=0.003, projection=0.003, cap_height=0.002, flare_width=0.0006, flare_height=0.0005, h=0.0003,
                             corrugation=dict(wavelength=0.0005, depth=0.00004, wander=0.003),
                             pits=dict(count=8, cluster_r=0.5, size=(0.0002, 0.0003), depth=(0.00005, 0.0001))),
                micro=dict(ring=dict(wavelength=0.0008, amp=0.00003, wander=0.004), radial=dict(wavelength=0.001, amp=0.00001),
                           noise=dict(wavelength=0.0004, amp=0.00001), zone=(0.25, 1.0)),
                pigment=dict(profile_r=[0, 0.5, 0.9, 1.1], profile_s=[1, 1, 0.3, 0], angular_amp=0.05))
    out = build(V, F, spec, seed=7)
    v2, f2 = out['v'], out['f']
    import mesh_cut as MC
    integ = MC.integrity(v2, f2)
    km = out['keep_map']
    kept = km >= 0
    dv = float(np.abs(v2[km[kept]] - V[kept]).max())
    n = out['normal']
    newp = v2[out['new_ids']]
    rr = np.hypot(newp[:, 0], newp[:, 1])
    edge = (rr > 0.0135) & (rr < 0.0165)
    sph = np.sqrt(np.maximum(0.06 ** 2 - rr ** 2, 0))
    base_err = float(np.abs(newp[edge, 2] - sph[edge]).max())
    tip = newp[-1, 2]
    tip_expect = 0.06 + 0.001 + 0.003
    rep = dict(integrity=integ, kept_vertices_max_move_m=dv, base_error_at_zone_edge_mm=round(base_err * 1e3, 4),
               old_bump_mm_planted=4.0, tip_z_mm=round(tip * 1e3, 3), tip_expected_mm=round(tip_expect * 1e3, 3),
               glands=out['report']['glands'], pits=out['report']['pits'])
    ok = (integ['open_edges'] == 0 and integ['nonmanifold_edges'] == 0 and integ['misoriented_edges'] == 0 and dv == 0.0
          and base_err < 5e-5 and abs(tip - tip_expect) < 1e-4 and rep['glands'] > 0 and rep['pits'] > 0)
    rep['PASS'] = bool(ok)
    # the planted failure: with the base fitted INSIDE the old bump the bump is copied (the test must fail there)
    spec2 = dict(spec, base_fit=(0.0, 0.012, 4))
    out2 = build(V, F, spec2, seed=7)
    newp2 = out2['v'][out2['new_ids']]
    rr2 = np.hypot(newp2[:, 0], newp2[:, 1])
    e2_ = (rr2 > 0.0135) & (rr2 < 0.0165)
    sph2 = np.sqrt(np.maximum(0.06 ** 2 - rr2 ** 2, 0))
    rep['planted_base_inside_old_bump_error_mm'] = round(float(np.abs(newp2[e2_, 2] - sph2[e2_]).max()) * 1e3, 4)
    rep['planted_fails'] = bool(rep['planted_base_inside_old_bump_error_mm'] >= 0.05)
    print(json.dumps(rep, indent=1, default=float))
    if out_path:
        json.dump(rep, open(out_path, 'w'), indent=1, default=float)
    return rep


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'prove':
        prove(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        print(__doc__)
