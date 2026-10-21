"""SDF modelling core: vectorised primitives (ellipsoid, round cone, tube, cupped ear shell),
sparse per-primitive smooth-union evaluation, marching cubes -> PLY, landmarks -> JSON.
Generic: no case facts live here. A case supplies build(P) -> (prims, landmarks) and bounds.
"""
import json
import time

import numpy as np
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import mouth_geom as MG  # noqa: E402
from skimage.measure import marching_cubes

# ----------------------------------------------------------------------------- helpers
def V(*a):
    return np.asarray(a[0] if len(a) == 1 else a, dtype=np.float64)


def unit(v):
    v = V(v)
    return v / np.linalg.norm(v)


def rotz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def rotx(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1.0, 0, 0], [0, c, -s], [0, s, c]])


def roty(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1.0, 0], [-s, 0, c]])


SMIN_ORDER = 3   # v30: CUBIC polynomial smooth-min (curvature-continuous, C2). v1-v29 used the quadratic one (C1):
                 # tangent-continuous but the curvature JUMPS at the blend edges -> the "lines" at every junction
                 # (neck, legs, tail, whisker pads; review fairness.py + zebra). Width x1.5 keeps the max fillet k/4.


def smin(a, b, k):
    if np.isscalar(k) and k <= 0:
        return np.minimum(a, b)
    k = np.maximum(k, 1e-6)
    if SMIN_ORDER == 2:
        h = np.maximum(k - np.abs(a - b), 0.0) / k
        return np.minimum(a, b) - h * h * k * 0.25
    k3 = 1.5 * k
    h = np.maximum(k3 - np.abs(a - b), 0.0) / k3
    return np.minimum(a, b) - h * h * h * k3 / 6.0


def smax(a, b, k):
    return -smin(-a, -b, k)


class Prim:
    def __init__(self, fn, lo, hi, k, op="u", name=""):
        self.fn, self.lo, self.hi, self.k, self.op, self.name = fn, V(lo), V(hi), k, op, name
        self.fur = None  # fur depth over this part (m); None -> P['fur_depth']
        self.kfn = None  # optional VARIABLE blend radius kfn(X, Y, Z) -> k field (v31: wide where a leg meets the
        #                  body, narrow between the legs; one k per primitive filled the gaps between the legs)


def var_blend(prim, k_small, k_big, weight):
    """give `prim` a variable blend radius: k = k_small + (k_big - k_small) * weight(X, Y, Z) (weight 0..1)"""
    prim.k = k_big
    prim.kfn = lambda X, Y, Z: k_small + (k_big - k_small) * weight(X, Y, Z)
    return prim


def ss01(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def with_fur(prims, fur):
    """Tag parts with their fur depth: the photo silhouette = skin + fur, and fur length varies by region."""
    for p in (prims if isinstance(prims, list) else [prims]):
        p.fur = fur
    return prims


def ellipsoid(c, r, R=None, k=0.01, op="u", name=""):
    c, r = V(c), V(r)
    Rt = None if R is None else np.asarray(R).T

    def fn(X, Y, Z):
        px, py, pz = X - c[0], Y - c[1], Z - c[2]
        if Rt is not None:
            px, py, pz = (Rt[0, 0] * px + Rt[0, 1] * py + Rt[0, 2] * pz,
                          Rt[1, 0] * px + Rt[1, 1] * py + Rt[1, 2] * pz,
                          Rt[2, 0] * px + Rt[2, 1] * py + Rt[2, 2] * pz)
        k0 = np.sqrt((px / r[0]) ** 2 + (py / r[1]) ** 2 + (pz / r[2]) ** 2)
        k1 = np.sqrt((px / r[0] ** 2) ** 2 + (py / r[1] ** 2) ** 2 + (pz / r[2] ** 2) ** 2)
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)

    m = r.max()
    return Prim(fn, c - m, c + m, k, op, name)


def round_cone(a, b, r1, r2, k=0.01, op="u", name=""):
    a, b = V(a), V(b)
    ba = b - a
    l2 = float(ba @ ba)
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2

    def fn(X, Y, Z):
        pax, pay, paz = X - a[0], Y - a[1], Z - a[2]
        y = pax * ba[0] + pay * ba[1] + paz * ba[2]
        z = y - l2
        qx, qy, qz = pax * l2 - ba[0] * y, pay * l2 - ba[1] * y, paz * l2 - ba[2] * y
        x2 = qx * qx + qy * qy + qz * qz
        y2 = y * y * l2
        z2 = z * z * l2
        kk = np.sign(rr) * rr * rr * x2
        d_end = np.sqrt(x2 + z2) * il2 - r2
        d_start = np.sqrt(x2 + y2) * il2 - r1
        d_mid = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1
        return np.where(np.sign(z) * a2 * z2 > kk, d_end, np.where(np.sign(y) * a2 * y2 < kk, d_start, d_mid))

    lo = np.minimum(a - r1, b - r2)
    hi = np.maximum(a + r1, b + r2)
    return Prim(fn, lo, hi, k, op, name)


def tube(pts, radii, k_joint=0.004, k_first=0.01, name=""):
    out = []
    for i in range(len(pts) - 1):
        out.append(round_cone(pts[i], pts[i + 1], radii[i], radii[i + 1],
                              k=k_first if i == 0 else k_joint, name=f"{name}{i}"))
    return out


def tri2d(px, py, p0, p1, p2):
    """IQ exact 2D triangle SDF, vectorised."""
    def dot(ax, ay, bx, by):
        return ax * bx + ay * by
    e0, e1, e2 = p1 - p0, p2 - p1, p0 - p2
    v0x, v0y = px - p0[0], py - p0[1]
    v1x, v1y = px - p1[0], py - p1[1]
    v2x, v2y = px - p2[0], py - p2[1]
    t0 = np.clip(dot(v0x, v0y, *e0) / (e0 @ e0), 0, 1)
    t1 = np.clip(dot(v1x, v1y, *e1) / (e1 @ e1), 0, 1)
    t2 = np.clip(dot(v2x, v2y, *e2) / (e2 @ e2), 0, 1)
    q0x, q0y = v0x - e0[0] * t0, v0y - e0[1] * t0
    q1x, q1y = v1x - e1[0] * t1, v1y - e1[1] * t1
    q2x, q2y = v2x - e2[0] * t2, v2y - e2[1] * t2
    s = np.sign(e0[0] * e2[1] - e0[1] * e2[0])
    d0 = dot(q0x, q0y, q0x, q0y); c0 = s * (v0x * e0[1] - v0y * e0[0])
    d1 = dot(q1x, q1y, q1x, q1y); c1 = s * (v1x * e1[1] - v1y * e1[0])
    d2 = dot(q2x, q2y, q2x, q2y); c2 = s * (v2x * e2[1] - v2y * e2[0])
    dd = np.minimum(np.minimum(d0, d1), d2)
    cc = np.minimum(np.minimum(c0, c1), c2)
    return -np.sqrt(dd) * np.sign(cc)


def ear(B1, B2, T, thick=0.006, thick_tip=0.003, cup=0.004, wall=0.0022, inset=0.0026,
        round_r=0.0018, k=0.006, name="ear"):
    """Cupped triangular ear shell. B1 inner base, B2 outer base, T tip (world).
    Opening faces the frame normal n (oriented toward -Y = forward)."""
    B1, B2, T = V(B1), V(B2), V(T)
    O = (B1 + B2) / 2
    v = unit(T - O)
    u0 = B2 - B1
    u = unit(u0 - (u0 @ v) * v)
    n = np.cross(u, v)
    if n[1] > 0:
        n = -n
    loc = lambda P_: np.array([(P_ - O) @ u, (P_ - O) @ v])
    # extend the base 4 mm below the attachment line so it sinks into the skull
    b1, b2, t = loc(B1) + [0, -0.004], loc(B2) + [0, -0.004], loc(T)
    h = t[1]
    half_w = abs(b2[0] - b1[0]) / 2
    cen = (b1 + b2 + t) / 3

    def shrink(p, d):
        return p + (cen - p) * d

    # inset triangle for the cavity (roughly offset inward by `inset`)
    s_in = inset / max(half_w, 1e-6)
    c1, c2, c3 = shrink(b1 + [0, 0.006], s_in), shrink(b2 + [0, 0.006], s_in), shrink(t, s_in * 1.4)

    def fn(X, Y, Z):
        px, py, pz = X - O[0], Y - O[1], Z - O[2]
        pu = px * u[0] + py * u[1] + pz * u[2]
        pv = px * v[0] + py * v[1] + pz * v[2]
        pn = px * n[0] + py * n[1] + pz * n[2]
        un = (pu - (b1[0] + b2[0]) / 2) / max(half_w, 1e-6)
        pnb = pn - cup * un * un            # edges bend forward -> cupped
        frac = np.clip(pv / h, 0, 1)
        ht = (thick + (thick_tip - thick) * frac) / 2
        d2 = tri2d(pu, pv, b1, b2, t) + round_r
        d2 = d2 - round_r  # keep size, rounded corners come from the extrusion below
        wx, wy = d2, np.abs(pnb) - ht
        outer = np.minimum(np.maximum(wx, wy), 0) + np.sqrt(np.maximum(wx, 0) ** 2 + np.maximum(wy, 0) ** 2) - round_r * 0.5
        # cavity: inset triangle, slab from back-wall plane forward through the front face
        dc2 = tri2d(pu, pv, c1, c2, c3)
        lo_n = -ht + wall
        cz = pnb - (lo_n + 0.02)
        cwy = np.abs(cz) - 0.02
        cav = np.minimum(np.maximum(dc2, cwy), 0) + np.sqrt(np.maximum(dc2, 0) ** 2 + np.maximum(cwy, 0) ** 2)
        return smax(outer, -cav, 0.0015)

    pts = np.array([B1, B2, T])
    lo = pts.min(0) - 0.012
    hi = pts.max(0) + 0.012
    return Prim(fn, lo, hi, k, "u", name)


def _smooth_profile(xs, ys):
    from scipy.interpolate import PchipInterpolator
    return PchipInterpolator(np.asarray(xs, float), np.asarray(ys, float), extrapolate=True)


def _fit_front_ellipsoid(fT, fB, fM, fW, y0, y_fit, tip_y, q_up, q_dn):
    """Tilted ellipsoid (symmetric in x; tilt in the y-z plane; separate upper/lower half-axes) least-squares fitted
    to the loft surface between the first station y0 and y_fit, frontmost point at tip_y.
    Returns (yc, zc, phi, A, B, C_up, C_dn)."""
    from scipy.optimize import least_squares
    ys = np.linspace(y0, y_fit, 7)
    th = np.linspace(0, np.pi, 19)
    P = []
    for y in ys:
        t, b, m, w = float(fT(y)), float(fB(y)), float(fM(y)), float(fW(y))
        for a_ in th:
            c, s = np.cos(a_), np.sin(a_)        # a_ from +x round over the top (0..pi/2) / underside mirrored
            for sg, aa, q in ((1, t - m, q_up), (-1, m - b, q_dn)):
                r = (abs(c) ** q + abs(s) ** q) ** (-1.0 / q)      # superellipse radius on the unit section
                P.append((w * r * c, y, m + sg * aa * r * s))
    P = np.array(P)
    w0, m0 = float(fW(y0)), float(fM(y0))

    def frame(p):
        yc, zc, phi = p[:3]
        cph, sph = np.cos(phi), np.sin(phi)
        u, v = P[:, 1] - yc, P[:, 2] - zc
        return P[:, 0], cph * u + sph * v, -sph * u + cph * v

    def front_y(p):
        yc, zc, phi, A, B, Cu, Cd = p
        t = np.linspace(-np.pi, np.pi, 721)
        vv = np.where(np.sin(t) > 0, Cu, Cd) * np.sin(t)
        return yc + (np.cos(phi) * B * np.cos(t) - np.sin(phi) * vv).min()

    def res(p):
        x, u, v = frame(p)
        A, B, Cu, Cd = p[3:]
        C = np.where(v > 0, Cu, Cd)              # half-ellipsoids sharing the tilted equator plane (C1 there)
        k0 = np.sqrt((x / A) ** 2 + (u / B) ** 2 + (v / C) ** 2)
        k1 = np.sqrt((x / A ** 2) ** 2 + (u / B ** 2) ** 2 + (v / C ** 2) ** 2)
        d = k0 * (k0 - 1) / np.maximum(k1, 1e-9)
        return np.concatenate([d, [4.0 * (front_y(p) - tip_y)]])

    p0 = (y_fit, m0, 0.0, max(w0, 0.03), y_fit - tip_y, 0.04, 0.04)
    sol = least_squares(res, p0, bounds=([y0, m0 - 0.08, -1.2, 0.01, 0.01, 0.01, 0.01],
                                         [y_fit + 0.05, m0 + 0.08, 1.2, 0.2, 0.3, 0.2, 0.2]))
    rms = float(np.sqrt(np.mean(sol.fun[:-1] ** 2)))
    print(f"front ellipsoid fit: yc {sol.x[0]:.4f} zc {sol.x[1]:.4f} tilt {np.degrees(sol.x[2]):.1f} deg "
          f"axes A {sol.x[3]*1000:.1f} B {sol.x[4]*1000:.1f} Cup {sol.x[5]*1000:.1f} Cdn {sol.x[6]*1000:.1f} mm  "
          f"rms {rms*1000:.2f} mm  tip-res {sol.fun[-1]/4*1000:.2f} mm")
    return tuple(float(a) for a in sol.x)


def loft_y(stations, top, bot, mid, half_w, q_up=2.3, q_dn=2.0, k=0.0, name="trunk", dome_front=0.0,
           front_fit=None):
    """Trunk as ONE measured surface (replaces stacked ellipsoid blobs, which smooth-min into lobes/bulges).
    Profiles over y (body axis): top(y) topline z, bot(y) underline z, mid(y) z of the widest point,
    half_w(y) half-width. Cross-section = superellipse, rounder above (q_up) than below (q_dn).
    Ends taper to zero radius just beyond the first/last station.
    front_fit=dict(y_fit, tip, blend=(y_loft, y_ell)): the chest front is a tilted ellipsoid FITTED to the loft's
    own closing stations (y0..y_fit) with its tip at `tip`, cross-faded into the loft over blend (smoothstep)."""
    st = np.asarray(stations, float)
    fT, fB, fM, fW = (_smooth_profile(st, a) for a in (top, bot, mid, half_w))
    y0, y1 = st[0], st[-1]
    if front_fit:
        E = _fit_front_ellipsoid(fT, fB, fM, fW, y0, front_fit["y_fit"], front_fit["tip"], q_up, q_dn)
        yl, ye = front_fit["blend"]

        def fn_ff(X, Y, Z):
            X, Y, Z = np.broadcast_arrays(X, Y, Z)
            d_l = fn(X, Y, Z)
            yc, zc, phi, A, B, Cu, Cd = E
            cph, sph = np.cos(phi), np.sin(phi)
            u, v = Y - yc, Z - zc
            uu, vv = cph * u + sph * v, -sph * u + cph * v
            C = np.where(vv > 0, Cu, Cd)
            k0 = np.sqrt((X / A) ** 2 + (uu / B) ** 2 + (vv / C) ** 2)
            k1 = np.sqrt((X / A ** 2) ** 2 + (uu / B ** 2) ** 2 + (vv / C ** 2) ** 2)
            d_e = np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -min(A, B, Cu, Cd))
            t_ = np.clip((Y - yl) / (ye - yl), 0, 1)
            al = t_ * t_ * (3 - 2 * t_)
            return (1 - al) * d_l + al * d_e
        dome_front = 0.0                                  # the fitted ellipsoid replaces the dome

    def fn(X, Y, Z):
        X, Y, Z = np.broadcast_arrays(X, Y, Z)
        y = np.clip(Y, y0, y1)
        t, b, m, w = fT(y), fB(y), fM(y), fW(y)
        a_up, a_dn = np.maximum(t - m, 1e-4), np.maximum(m - b, 1e-4)
        dz = Z - m
        a = np.where(dz > 0, a_up, a_dn)
        # near-Euclidean ellipse distance (IQ k0*(k0-1)/k1) per half. v1 used (e-1)*min(w,a): distances
        # collapse where a section is thin, so the +fur offset surface grew blade-like fins at the end caps.
        w_ = np.maximum(w, 1e-4)
        k0 = np.sqrt((X / w_) ** 2 + (dz / a) ** 2)
        k1 = np.sqrt((X / w_ ** 2) ** 2 + (dz / a ** 2) ** 2)
        q = np.where(dz > 0, q_up, q_dn)
        e = (np.abs(X / w_) ** q + np.abs(dz / a) ** q) ** (1.0 / q)   # superellipse radius (boxier haunch at q>2)
        d = np.where(k1 > 1e-9, k0 * (e - 1.0) / np.maximum(k1, 1e-9), -np.minimum(w_, a))   # 0/0 on the axis -> -r
        # end caps = exact extrusion distance (flat face, rounded rim). v1 used sqrt(..)+min(d,0), which inside the
        # section pushes the surface out by the section's own radius -> a cone/spike at the chest front (v21-v22)
        # SIGNED distance to the end planes (negative between them); with a dome the front end is the dome, not a plane
        over = (Y - y1) if dome_front > 0 else np.maximum(y0 - Y, Y - y1)
        d_ext = np.minimum(np.maximum(d, over), 0) + np.sqrt(np.maximum(d, 0) ** 2 + np.maximum(over, 0) ** 2)
        if dome_front > 0:
            # front cap = a TRUE 3D half-ellipsoid (IQ) on the first section: semi-axes (w0, dome, a_up/a_dn about m0).
            # v25 scaled the 2D section with y, leaving almost no y-gradient -> marching-cubes terraces (rings).
            w0, m0 = fW(y0), fM(y0)
            au0, ad0 = max(fT(y0) - m0, 1e-4), max(m0 - fB(y0), 1e-4)
            dz0 = Z - m0
            az = np.where(dz0 > 0, au0, ad0)
            px, py, pz = X / w0, (Y - y0) / dome_front, dz0 / az
            k0 = np.sqrt(px * px + py * py + pz * pz)
            k1 = np.sqrt((X / w0 ** 2) ** 2 + ((Y - y0) / dome_front ** 2) ** 2 + (dz0 / az ** 2) ** 2)
            d_cap = np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -min(w0, au0, ad0))
            return np.where(Y < y0, d_cap, d_ext)
        return d_ext

    lo = (-max(half_w) - 0.005, y0 - 0.02 - dome_front, min(bot) - 0.005)
    hi = (max(half_w) + 0.005, y1 + 0.02, max(top) + 0.005)
    if front_fit:
        lo = (lo[0], min(lo[1], front_fit["tip"] - 0.01), lo[2])
        return Prim(fn_ff, lo, hi, k, "u", name)
    return Prim(fn, lo, hi, k, "u", name)


def loft_z(sections, k=0.01, name="limb_z"):
    """Vertical limb loft from MEASURED horizontal slices: sections = [(z, cx, cy, rx, ry), ...] (ellipses, axis
    aligned). Interpolated smoothly (PCHIP), near-Euclidean ellipse distance, rounded end caps. Built for haunches
    and forearms whose real cross-sections are much deeper front-to-back than wide (v19: round-tube hind legs
    read as sticks under the body; reference haunch at z=0.10 is 38 x 63 mm)."""
    S = np.asarray(sections, float)
    S = S[np.argsort(S[:, 0])]
    zs = S[:, 0]
    f = [_smooth_profile(zs, S[:, i]) for i in range(1, 5)]
    z0, z1 = zs[0], zs[-1]

    def fn(X, Y, Z):
        X, Y, Z = np.broadcast_arrays(X, Y, Z)
        zc = np.clip(Z, z0, z1)
        cx, cy, rx, ry = (np.maximum(fi(zc), 1e-4) if i >= 2 else fi(zc) for i, fi in enumerate(f))
        dx, dy = X - cx, Y - cy
        k0 = np.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)
        k1 = np.sqrt((dx / rx ** 2) ** 2 + (dy / ry ** 2) ** 2)
        d2 = np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -np.minimum(rx, ry))   # axis 0/0 -> -r
        over = np.maximum(z0 - Z, Z - z1)             # exact extrusion caps, signed (see loft_y)
        return np.minimum(np.maximum(d2, over), 0) + np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(over, 0) ** 2)

    m = max(S[:, 3].max(), S[:, 4].max()) + 0.004
    lo = (S[:, 1].min() - m, S[:, 2].min() - m, z0 - m)
    hi = (S[:, 1].max() + m, S[:, 2].max() + m, z1 + m)
    return Prim(fn, lo, hi, k, "u", name)


def loft_curve(ctrl, radii, samples=40, k=0.006, flatten=None, name="limb"):
    """Smooth limb/neck/tail: Catmull-Rom spline through control points (joints), radius interpolated
    smoothly (PCHIP) along arc length, distance to a dense polyline minus local radius. No joint balls,
    no kinks (v1 legs/tail = round cones meeting at joints -> knee balls, mangled tail).
    flatten=(axis_vec, ratio): squash the section along a world axis (e.g. legs are narrower front-to-back)."""
    C = np.asarray(ctrl, float)
    if len(C) == 2:
        pts = np.linspace(C[0], C[1], samples + 1)
    else:
        P = np.vstack([2 * C[0] - C[1], C, 2 * C[-1] - C[-2]])
        pts = []
        per = max(samples // (len(C) - 1), 2)
        for i in range(1, len(P) - 2):
            p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            for t in np.linspace(0, 1, per, endpoint=False):
                t2, t3 = t * t, t * t * t
                pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
        pts.append(C[-1])
        pts = np.array(pts)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    # control points sit at their nearest dense-sample arc length
    cs = [cum[int(np.argmin(np.linalg.norm(pts - c, axis=1)))] for c in C]
    cs = np.maximum.accumulate(np.array(cs) + np.arange(len(cs)) * 1e-9)
    fr = _smooth_profile(cs, radii)
    rr = np.maximum(fr(cum), 1e-4)
    if flatten is not None:
        fa, fr_ratio = unit(flatten[0]), flatten[1]

    def fn(X, Y, Z):
        X, Y, Z = np.broadcast_arrays(X, Y, Z)
        if flatten is not None:   # squash space along the axis -> elliptical sections
            dd = X * fa[0] + Y * fa[1] + Z * fa[2]
            corr = dd * (1.0 / fr_ratio - 1.0)
            X, Y, Z = X + corr * fa[0], Y + corr * fa[1], Z + corr * fa[2]
        best = np.full(X.shape, 1e9)
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            ba = b - a
            l2 = float(ba @ ba)
            t = np.clip(((X - a[0]) * ba[0] + (Y - a[1]) * ba[1] + (Z - a[2]) * ba[2]) / l2, 0, 1)
            dx, dy, dz = X - (a[0] + t * ba[0]), Y - (a[1] + t * ba[1]), Z - (a[2] + t * ba[2])
            d = np.sqrt(dx * dx + dy * dy + dz * dz) - (rr[i] + t * (rr[i + 1] - rr[i]))
            best = np.minimum(best, d)
        return best

    m = rr.max() + 0.003
    if flatten is not None:
        m = m / min(fr_ratio, 1.0)
    return Prim(fn, pts.min(0) - m, pts.max(0) + m, k, "u", name)


def ear_cone(base, tip, width_dir, facing, w, thick_ratio=0.38, tip_r=0.0018, wall=0.0022, cup_off=None,
             k=0.006, name="ear"):
    """Cupped cone ear: a round cone flattened along the facing axis (front outline = triangle), minus a
    smaller flattened cone pushed toward the front = open cup. Thick at the base, thin at the rim/tip.
    Robust at 1 mm voxels (v1 extruded-triangle shells aliased into jagged paper slabs)."""
    base, tip = V(base), V(tip)
    v = unit(tip - base)
    h = float(np.linalg.norm(tip - base))
    u = unit(V(width_dir) - (V(width_dir) @ v) * v)
    n = np.cross(u, v)
    if n @ V(facing) < 0:
        n = -n
    tr = thick_ratio
    off = (w / 2) * tr * 0.75 if cup_off is None else cup_off
    outer_rc = round_cone((0, 0, 0), (0, h, 0), w / 2, tip_r).fn
    cav_rc = round_cone((0, h * 0.10, 0), (0, h * 0.86, 0), w / 2 - wall, tip_r * 0.4).fn

    def fn(X, Y, Z):
        px, py, pz = X - base[0], Y - base[1], Z - base[2]
        lu = px * u[0] + py * u[1] + pz * u[2]
        lv = px * v[0] + py * v[1] + pz * v[2]
        ln = px * n[0] + py * n[1] + pz * n[2]
        outer = outer_rc(lu, lv, ln / tr) * tr ** 0.5
        cav = cav_rc(lu, lv, (ln - off) / tr) * tr ** 0.5
        return smax(outer, -cav, 0.0012)

    m = max(w, h) * 0.6 + 0.004
    mid = (base + tip) / 2
    return Prim(fn, mid - m, mid + m, k, "u", name)


def _poly_sdf2(px, py, poly):
    """signed 2-D distance to a closed polygon (negative inside), vectorised over the edges"""
    d2 = np.full(px.shape, np.inf); inside = np.zeros(px.shape, bool)
    poly = np.asarray(poly, float)
    keep = np.r_[True, np.linalg.norm(np.diff(poly, axis=0), axis=1) > 1e-9]
    poly = poly[keep]
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]; bx, by = poly[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        if ex * ex + ey * ey < 1e-18:
            continue
        t = np.clip(((px - ax) * ex + (py - ay) * ey) / (ex * ex + ey * ey), 0, 1)
        d2 = np.minimum(d2, (px - ax - t * ex) ** 2 + (py - ay - t * ey) ** 2)
        cond = ((ay > py) != (by > py)) & (px < (bx - ax) * (py - ay) / (by - ay + 1e-12) + ax)
        inside ^= cond
    d = np.sqrt(d2)
    return np.where(inside, -d, d)


def pinna(base, tip, width_dir, facing, w_base, tip_r=0.0045, t_base=0.0050, t_rim=0.0012, cup=0.30, outer_bulge=0.12,
          inner_bulge=0.03, conch=(0.22, 0.24, 0.26), henry=True, k=0.007, name="ear"):
    """Anatomical PINNA (cat ear) - replaces the blade-like ear_cone (v34 ear review: flat fin, no cup, no conch,
    no Henry's pocket, tall narrow outline).
    Frame: v base->tip, u across the base (toward the OUTER edge), n facing (the opening).
    Outline (u, v): a ROUNDED polygon - base width w_base, convex outer edge (bulge x w_base), nearly straight inner
    edge, tip rounded by tip_r (inner shape offset outward). Shell: mid-surface a smooth trough recessed toward -n,
    deepest on the centre line (average half-width -> no crease), thickness t_base at the base -> t_rim at the edges
    and tip. Conch: a rounded bowl low in the centre (fractions of w_base: depth, height, width). Henry's pocket: a
    rounded notch in the lower outer edge."""
    base, tip = V(base), V(tip)
    v_ = unit(tip - base); h = float(np.linalg.norm(tip - base))
    u_ = unit(V(width_dir) - (V(width_dir) @ v_) * v_)
    n_ = np.cross(u_, v_)
    if n_ @ V(facing) < 0:
        n_ = -n_
    r = tip_r
    ts = np.linspace(0, 1, 24)

    def hw(t, side):
        lin = (w_base / 2) * (1 - t)
        return lin + (outer_bulge if side > 0 else inner_bulge) * w_base * 4 * t * (1 - t)
    # inner (shrunk) outline; the surface is its offset by r -> rounded tip and rounded base corners
    # shrunk half-widths clamped at 0: the polygon closes where they meet (v2 crossed itself at the tip -> a "flag")
    vs = -0.0015 + np.linspace(0, 1, 48) * (h + 0.0015)     # v36: no collar band below the base (it creased the skull junction)
    tv = np.clip(vs / h, 0, 1)
    wo = np.maximum(hw(tv, 1) - r, 0.0); wi = np.maximum(hw(tv, -1) - r, 0.0)
    keep = (wo > 1e-5) | (wi > 1e-5)
    last = int(np.nonzero(keep)[0].max()) + 1
    vs, wo, wi = vs[:last + 1], wo[:last + 1], wi[:last + 1]
    poly = np.array([(wo[j], vs[j]) for j in range(len(vs))] + [(-wi[j], vs[j]) for j in range(len(vs) - 1, -1, -1)])

    def fn(X, Y, Z):
        px, py, pz = X - base[0], Y - base[1], Z - base[2]
        lu = px * u_[0] + py * u_[1] + pz * u_[2]
        lv = px * v_[0] + py * v_[1] + pz * v_[2]
        ln = px * n_[0] + py * n_[1] + pz * n_[2]
        d2 = _poly_sdf2(lu, lv, poly) - r
        t = np.clip(lv / h, 0, 1)
        w_in, w_out = hw(t, -1), hw(t, 1)
        wavg = np.maximum((w_in + w_out) / 2, 1e-4)
        uu = np.clip(np.where(lu >= 0, lu / np.maximum(w_out, 1e-4), lu / np.maximum(w_in, 1e-4)), -1, 1)
        n_mid = -cup * (2 * wavg) * (1 - uu * uu) * (0.35 + 0.65 * (1 - t))
        thick = t_base + (t_rim - t_base) * np.clip(np.maximum(t, np.abs(uu) ** 3), 0, 1)
        d_sh = np.abs(ln - n_mid) - thick / 2
        d = smax(d2, d_sh, 0.0012)
        cd, chh, cw = conch       # a shallow DISH sunk into the front face, low in the centre (never through the shell)
        dish_depth = 0.55 * thick
        e = np.sqrt((lu / (cw * w_base)) ** 2 + ((lv - chh * w_base) / (0.9 * cw * w_base)) ** 2
                    + ((ln - (n_mid + thick / 2 + 0.3 * dish_depth)) / (1.3 * dish_depth)) ** 2)
        d = smax(d, -(e - 1.0) * dish_depth, 0.0015)
        if henry:
            hv = 0.18 * h; hu = hw(hv / h, 1) + 0.0004
            seg = np.sqrt((lu - hu) ** 2 + np.maximum(np.abs(lv - hv) - 0.0030, 0) ** 2 + (ln - n_mid) ** 2) - 0.0014
            d = smax(d, -seg, 0.0008)
        return d

    m = max(w_base, h) * 0.75 + 0.006
    mid = (base + tip) / 2
    return Prim(fn, mid - m, mid + m, k, "u", name)


def tri_pad(origin, R, p0, p1, p2, round_r=0.0025, thick=0.0030, dome=0.0015, y0=0.0, k=0.004, name="pad"):
    """Rounded-triangle pad (e.g. a rhinarium): 2D triangle in the frame's local x-z plane (front view),
    rounded by round_r, extruded along local y around y0 with a forward dome. Frame: origin + R (local -> world).
    A cat's nose leather is a rounded INVERTED triangle (flat top, point down), not an ellipse."""
    origin, R = V(origin), np.asarray(R)
    Rt = R.T
    q0, q1, q2 = V(p0), V(p1), V(p2)
    cen = (q0 + q1 + q2) / 3
    shrink = lambda q: q + (cen - q) * (round_r / max(np.linalg.norm(q - cen), 1e-6)) * 1.6
    s0, s1, s2 = shrink(q0), shrink(q1), shrink(q2)
    span = max(np.linalg.norm(q0 - cen), np.linalg.norm(q1 - cen), np.linalg.norm(q2 - cen))

    def fn(X, Y, Z):
        px, py, pz = X - origin[0], Y - origin[1], Z - origin[2]
        lx = Rt[0, 0] * px + Rt[0, 1] * py + Rt[0, 2] * pz
        ly = Rt[1, 0] * px + Rt[1, 1] * py + Rt[1, 2] * pz
        lz = Rt[2, 0] * px + Rt[2, 1] * py + Rt[2, 2] * pz
        d2 = tri2d(lx, lz, s0, s1, s2) - round_r
        rr = np.sqrt((lx - cen[0]) ** 2 + (lz - cen[1]) ** 2) / span
        front = y0 - dome * np.clip(1 - rr ** 2, 0, 1)            # dome bulges toward -y (forward)
        wy = np.maximum(front - ly, ly - (y0 + thick))
        return np.minimum(np.maximum(d2, wy), 0) + np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(wy, 0) ** 2)

    m = span + round_r + thick + dome + 0.004
    w = origin + R @ V((cen[0], y0, cen[1]))
    return Prim(fn, w - m, w + m, k, "u", name)


def slit_cavity(origin, R, a, b, yc, z0, slope, y_flat, gap_edge=0.0009, gap_in=0.0042, power=4.0, k=0.0008,
                name="mouth", lip_droop=0.0, lobe_x=0.004, lobe_w=0.003, corner_rise=0.0, lip_e=1.0):
    """Subtractive mouth: a thin slab whose mid-plane z = z0 + slope*max(0, y - y_flat) (frame-local),
    clipped to a superellipse outline |x/a|^p + |(y-yc)/b|^p <= 1 in the local xy plane. Thin (gap_edge)
    where it exits the skin = lips that meet; thickens to gap_in inside = oral cavity. Lower jaw becomes a
    separable volume a jaw bone can open. origin/R map local -> world (local y = forward(-)/back(+)).
    lip_e < 1: the slab stays thin (gap_edge) wherever the outline coordinate e > lip_e, i.e. through the whole lip
    zone where the slab exits the skin, and thickens only behind it (v27: at lip_e=1 the lips sat at e~0.8 and the
    rest gap was ~5 mm - the closed pose needed +3 deg of jaw and still showed a dark ragged line)."""
    origin, R = V(origin), np.asarray(R)
    Rt = R.T

    def fn(X, Y, Z):
        px, py, pz = X - origin[0], Y - origin[1], Z - origin[2]
        lx = Rt[0, 0] * px + Rt[0, 1] * py + Rt[0, 2] * pz
        ly = Rt[1, 0] * px + Rt[1, 1] * py + Rt[1, 2] * pz
        lz = Rt[2, 0] * px + Rt[2, 1] * py + Rt[2, 2] * pz
        e = MG.outline_e(lx, ly, a, b, yc, power)          # shared with the Blender-side tools (mouth_geom.py)
        d2 = (e - 1.0) * min(a, b)
        h = MG.half_gap(e, gap_edge, gap_in, lip_e)
        zm = MG.lip_line(lx, ly, a, z0, slope, y_flat, lip_droop, lobe_x, lobe_w, corner_rise)
        return np.maximum(d2, np.abs(lz - zm) - h)

    m = max(a, b + abs(yc)) + 0.01
    return Prim(fn, origin - m, origin + m, k, "s", name)


def jaw_warp(prims, H0, R, hs, G, c=40.0, k=0.15, y_corner=-0.016, depth=(0.010, 0.022)):
    """Lower jaw tucked INSIDE the upper lip, as in a cat: a smooth domain warp applied to the given (head) union
    primitives BELOW the mouth's separation surface only. The lower lip becomes a U in plan (pulled back by c*x^2)
    and slightly narrower (inward by k*|x|); the warp fades to zero at the outline (corners -> continuous with the
    cheeks), behind y_corner, and with depth below the separation (depth=(full, zero) m), and it switches on inside
    the slab gap, where the subtraction hides the seam. v28: the slab left the lower slices of the whisker pads/lip
    lobes on the jaw -> lower jaw as wide as the upper lip -> the open mouth (meow) was a rectangle; a boolean trim
    (v28a) left flat cut faces and flaps. G = mouth_geom parameters in head-local UNSCALED units."""
    H0, R = V(H0), np.asarray(R)

    def wrap(p):
        f0 = p.fn

        def fn(X, Y, Z):
            X, Y, Z = np.broadcast_arrays(X, Y, Z)
            px, py, pz = X - H0[0], Y - H0[1], Z - H0[2]
            x = (R[0, 0] * px + R[1, 0] * py + R[2, 0] * pz) / hs        # head-local unscaled (R^T p)
            y = (R[0, 1] * px + R[1, 1] * py + R[2, 1] * pz) / hs
            z = (R[0, 2] * px + R[1, 2] * py + R[2, 2] * pz) / hs
            zm, e, h = MG.zm_e_h(x, y, G)
            w = (MG._ss(zm - 0.0001, zm - 0.0006, z) * MG._ss(0.85, 0.5, e) * MG._ss(y_corner, y_corner - 0.010, y)
                 * MG._ss(zm - depth[1], zm - depth[0], z))
            dx = np.sign(x) * k * np.abs(x) * w
            dy = -c * x * x * w
            # back to world: R @ (dx, dy, 0) * hs
            return f0(X + hs * (R[0, 0] * dx + R[0, 1] * dy), Y + hs * (R[1, 0] * dx + R[1, 1] * dy),
                      Z + hs * (R[2, 0] * dx + R[2, 1] * dy))
        q = Prim(fn, p.lo, p.hi, p.k, p.op, p.name)
        q.fur = getattr(p, "fur", None)
        return q
    return [wrap(p) for p in prims]


def muzzle_warp(prims, H0, R, hs, dy, ya, yb):
    """Stretch the face in front of the eye plane forward (head-local unscaled y: identity behind ya, rigid shift dy
    beyond yb): every head part in front of the eyes - nose, pads, lips, lower jaw, chin - advances together. Used to
    give the muzzle the depth the anatomical prior requires (engine/priors.json; a frontal photo cannot see it)."""
    H0, R = V(H0), np.asarray(R)
    g = np.linspace(yb - 0.08, ya + 0.08, 4001)
    fg = MG.muzzle_map(g, dy, ya, yb)

    def wrap(p):
        f0 = p.fn

        def fn(X, Y, Z):
            X, Y, Z = np.broadcast_arrays(X, Y, Z)
            px, py, pz = X - H0[0], Y - H0[1], Z - H0[2]
            y = (R[0, 1] * px + R[1, 1] * py + R[2, 1] * pz) / hs           # head-local y (unscaled)
            dyl = (np.interp(y, fg, g) - y) * hs                              # move back to the unwarped place
            return f0(X + R[0, 1] * dyl, Y + R[1, 1] * dyl, Z + R[2, 1] * dyl)
        lo, hi = p.lo.copy(), p.hi.copy()
        pad = abs(dy) * hs + 0.002
        q = Prim(fn, lo - pad, hi + pad, p.k, p.op, p.name)
        q.fur, q.kfn = getattr(p, "fur", None), getattr(p, "kfn", None)
        return q
    return [wrap(p) for p in prims]


def eye_aperture(c, gaze, up, r_eye, a, b, tilt_deg=8.0, outward=None, gap=0.0006, depth=0.02, k=0.0012, name="eyeopen",
                 lid=0.0016):
    """Subtractive eyelid cut. Use with an 'orbit' ball (r_eye + lid thickness) unioned around the eye:
    removes a snug sphere (eyeball seat) plus an almond prism along the gaze, so lids wrap the eyeball and
    only the almond opening shows. a/b = half width/height of the opening; outer corner tilts up by tilt_deg."""
    c, g = V(c), unit(gaze)
    yv = unit(V(up) - (V(up) @ g) * g)
    xv = np.cross(yv, g)
    if outward is not None and xv @ V(outward) < 0:
        xv = -xv  # x' points away from the face midline (outer canthus)
    t = np.radians(tilt_deg)
    ct, st = np.cos(t), np.sin(t)
    R0 = r_eye + gap

    def fn(X, Y, Z):
        px, py, pz = X - c[0], Y - c[1], Z - c[2]
        lx = px * xv[0] + py * xv[1] + pz * xv[2]
        ly = px * yv[0] + py * yv[1] + pz * yv[2]
        lz = px * g[0] + py * g[1] + pz * g[2]
        qx, qy = ct * lx + st * ly, -st * lx + ct * ly      # rotate so the outer corner rises
        flare = 1.0 + 0.35 * np.clip(lz / depth, 0, 1)      # opening widens outward (lid bevel)
        e = np.sqrt((qx / (a * flare)) ** 2 + (qy / (b * flare)) ** 2)
        d2 = (e - 1.0) * min(a, b)
        prism = np.maximum(d2, np.maximum(-lz, lz - depth))
        dist = np.sqrt(px * px + py * py + pz * pz)
        sphere = dist - R0
        # v8: cut only through the lid shell hugging the eyeball. v7 cut a 16 mm tunnel, leaving a 3 mm
        # gap between eyeball and face that read as a dark socket ring ("ball in a hole").
        shell = dist - (r_eye + lid + 0.0004)
        return np.minimum(sphere, np.maximum(prism, shell))

    m = max(R0, depth, a * 1.4)
    return Prim(fn, c - m, c + m, k, "s", name)


# ----------------------------------------------------------------------------- evaluate + mesh
def evaluate(prims, lo, hi, vox):
    n = np.ceil((hi - lo) / vox).astype(int) + 1
    xs, ys, zs = (lo[i] + np.arange(n[i]) * vox for i in range(3))
    F = np.full(tuple(n), 1.0, np.float32)
    owner = np.full(tuple(n), -1, np.int16)  # which primitive is nearest -> fur depth + diff attribution
    for idx, p in enumerate(prims):
        m = p.k + 2 * vox + 0.014
        i0 = np.maximum(np.floor((p.lo - m - lo) / vox).astype(int), 0)
        i1 = np.minimum(np.ceil((p.hi + m - lo) / vox).astype(int) + 1, n)
        if np.any(i1 <= i0):
            continue
        X = xs[i0[0]:i1[0], None, None]
        Y = ys[None, i0[1]:i1[1], None]
        Z = zs[None, None, i0[2]:i1[2]]
        d = p.fn(X, Y, Z).astype(np.float32)
        d = np.broadcast_to(d, (i1[0] - i0[0], i1[1] - i0[1], i1[2] - i0[2]))
        kk = p.k if p.kfn is None else np.broadcast_to(p.kfn(X, Y, Z), d.shape).astype(np.float32)
        sl = (slice(i0[0], i1[0]), slice(i0[1], i1[1]), slice(i0[2], i1[2]))
        if p.op == "u":
            sub = F[sl]
            owner[sl][d < sub] = idx
            F[sl] = smin(sub, d, kk)
        else:
            F[sl] = smax(F[sl], -d, kk)
    # flat paw contact: intersect with z >= 0 half-space (smoothly)
    kz = int(np.ceil(0.01 / vox))
    F[:, :, :kz] = smax(F[:, :, :kz], (0.0 - zs[None, None, :kz]).astype(np.float32), 0.002)
    F[:, :, 0] = np.maximum(F[:, :, 0], 1e-3)
    return F, owner


def write_ply(path, verts, faces):
    with open(path, "wb") as f:
        f.write((f"ply\nformat binary_little_endian 1.0\nelement vertex {len(verts)}\n"
                 "property float x\nproperty float y\nproperty float z\n"
                 f"element face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n").encode())
        f.write(verts.astype("<f4").tobytes())
        fa = np.empty(len(faces), dtype=[("n", "u1"), ("i", "<i4", 3)])
        fa["n"] = 3
        fa["i"] = faces
        f.write(fa.tobytes())


def to_jsonable(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (list, tuple)):
        return [to_jsonable(x) for x in o]
    if isinstance(o, dict):
        return {k: to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (np.floating,)):
        return float(o)
    return o


def run(build, P, out, vox, lo, hi):
    """Writes <out>.ply (skin) and, if P['fur_depth'] > 0, <out>_env.ply: the same field meshed at
    iso = +fur_depth, i.e. the fur envelope the photo's silhouette actually shows."""
    t0 = time.time()
    prims, L = build(P)
    # auto-bounds: union of every additive primitive's box + blend/fur margin. v17b's hand-set BOUNDS clipped
    # the new tail -> open boundary (294 edges) + a detached tail tip. Hand bounds may only widen, never clip.
    adds = [p for p in prims if p.op == "u"]
    pad = 0.012 + float(P.get("fur_depth", 0)) + max((p.fur or 0) for p in adds) if adds else 0.02
    auto_lo = np.min([p.lo for p in adds], 0) - pad
    auto_hi = np.max([p.hi for p in adds], 0) + pad
    auto_lo[2] = max(auto_lo[2], 0.0)
    lo = np.minimum(np.asarray(lo, float), auto_lo); hi = np.maximum(np.asarray(hi, float), auto_hi)
    lo[2] = max(lo[2], 0.0)
    F, owner = evaluate(prims, lo, hi, vox)
    t1 = time.time()
    n = np.array(F.shape)

    def vowner(v):
        i = np.clip(np.round((v - lo) / vox).astype(int), 0, n - 1)
        return owner[i[:, 0], i[:, 1], i[:, 2]]

    verts, faces, _, _ = marching_cubes(F, 0.0, spacing=(vox, vox, vox), gradient_direction="ascent",
                                        allow_degenerate=False)
    verts += lo
    write_ply(out + ".ply", verts, faces)
    hb = P.get("hires_box")
    if hb:   # two-resolution meshing: fine head box + coarse body with that box removed, both CAPPED (closed)
        hv_ = float(P.get("hires_vox", 0.00035))
        hlo, hhi = np.asarray(hb[0], float), np.asarray(hb[1], float)
        Fh, _ = evaluate(prims, hlo, hhi, hv_)
        Fh[0, :, :] = Fh[-1, :, :] = Fh[:, 0, :] = Fh[:, -1, :] = Fh[:, :, -1] = hv_   # cap at the box faces
        hvv, hff, _, _ = marching_cubes(Fh, 0.0, spacing=(hv_,) * 3, gradient_direction="ascent", allow_degenerate=False)
        write_ply(out + "_hr.ply", hvv + hlo, hff)
        ov = float(P.get("hires_overlap", 0.004))
        n_ = np.array(F.shape)
        xs_, ys_, zs_ = (lo[i] + np.arange(n_[i]) * vox for i in range(3))
        inside = ((xs_[:, None, None] > hlo[0] + ov) & (xs_[:, None, None] < hhi[0] - ov) &
                  (ys_[None, :, None] > hlo[1] + ov) & (ys_[None, :, None] < hhi[1] - ov) &
                  (zs_[None, None, :] > hlo[2] + ov) & (zs_[None, None, :] < hhi[2] - ov))
        Fl = F.copy(); Fl[inside] = np.maximum(Fl[inside], vox)                         # cut + cap the coarse body
        lvv, lff, _, _ = marching_cubes(Fl, 0.0, spacing=(vox,) * 3, gradient_direction="ascent", allow_degenerate=False)
        write_ply(out + "_lr.ply", lvv + lo, lff)
        print(f"hires head box {np.round(hlo,3)}..{np.round(hhi,3)} @ {hv_*1000:.2f} mm: {len(hff)} faces; body cut: {len(lff)} faces")
    np.save(out + "_owner.npy", vowner(verts).astype(np.int16))
    with open(out + "_parts.json", "w") as f:
        json.dump([p.name for p in prims], f)
    fd = float(P.get("fur_depth", 0.0))
    if fd > 0:
        from scipy.ndimage import gaussian_filter
        furs = np.array([fd if p.fur is None else p.fur for p in prims] + [0.0], np.float32)
        fur = gaussian_filter(furs[owner], sigma=0.004 / vox)  # owner -1 -> last entry (0)
        ev, ef, _, _ = marching_cubes(F - fur, 0.0, spacing=(vox, vox, vox), gradient_direction="ascent",
                                      allow_degenerate=False)
        ev += lo
        write_ply(out + "_env.ply", ev, ef)
        np.save(out + "_env_owner.npy", vowner(ev).astype(np.int16))
    with open(out + "_landmarks.json", "w") as f:
        json.dump(to_jsonable({"params": P, "landmarks": L}), f, indent=1)
    print(f"grid {F.shape} vox={vox*1000:.1f}mm  prims={len(prims)}  sdf {t1-t0:.1f}s  mc {time.time()-t1:.1f}s  "
          f"verts={len(verts)} faces={len(faces)}  bbox {verts.min(0).round(3)} {verts.max(0).round(3)}")
    return verts, faces, L
