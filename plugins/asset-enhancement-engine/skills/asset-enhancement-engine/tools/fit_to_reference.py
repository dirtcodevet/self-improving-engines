"""fit_to_reference.py - regularised non-rigid fit of a mesh's OWN surface to one or more reference surfaces.

Why it exists (woman2 FINISH_SPEC F1, 2026-10-19): the engine torso had the right parts but the wrong form
(sections 10-38 mm off a 3-D reference stacked in the same frame), and slice ridges along its sides and back (J1).
Engine E7 makes the reference the start input for FORM, but never for the zones the reference gets wrong (here
Tripo's puffy nipples and its welded armpits).  So the fit has to (a) move the engine's own vertices, keeping its
topology, colour and parts, (b) step them onto the reference along their normals, (c) stay smooth (no ridges, steps
or flat facets), and (d) leave masked zones to be carried smoothly by their surroundings instead of copying the
reference there.

Method (one outer iteration):
  1. normals of the current mesh;
  2. per reference, the step along each vertex normal to the reference's local tangent plane, using the nearest
     reference face whose normal agrees with the vertex normal (cos >= cos_min) within dmax; reference faces can be
     masked (e.g. where the reference's own surfaces touch: `facing_contact`) and labelled by part (a vertex only
     takes faces of its own part); optional guards: `mutual` (drop a pull when another source surface facing that
     way is nearer to the reference point) and `robust` (Cauchy down-weighting of steps that disagree with their
     neighbourhood's);
  3. the per-reference steps are blended per vertex with caller-given weights (keep them FIXED: weights read from the
     current normals feed back);
  4. COARSE levels (`cell` in the schedule): one translation per cluster (the connected mesh pieces inside each cubic
     cell), data averaged per cluster, a thin-plate term on the cluster graph, solved directly; clusters without data
     are filled harmonically; the field is prolonged to the vertices and smoothed.  These take the large moves.
     FINE levels: an increment field u (N x 3) minimises
         sum_i w_i (n_i . u_i - d_i)^2 + lam |L u|^2 + tang |u_i - n_i (n_i . u_i)|^2 + eps |u|^2
           + kappa sum_pinned (u_i . e_axis)^2
     (L = graph Laplacian: a thin-plate smoothness of the step field; `tang` holds the tangential part), solved by
     Jacobi-PCG on the GPU via CuPy when available (numpy fallback); then excluded vertices (keep ~ 0) and vertices
     with no correspondence take the harmonic fill of their neighbours' increments (bounded by the rim).
  5. a schedule runs coarse (60 -> 8 mm cells) then fine (lam 1e3 -> 3).
Afterwards `fair` (masked Taubin) removes what the data did not (slice ridges inside excluded zones).  Flat caps are
best split off before the fit (`split_caps`) and re-closed afterwards (`retriangulate_caps`).

Also here: `harmonic_fill` / `biharmonic_fill` (replace a zone by the smooth surface its rim implies),
`heightfield_fill` (the same in the zone's own height frame: keeps a dome), `refine_local` (conforming edge-split
refinement, colours interpolated), soft masks, `twosided` (masked two-sided surface distances), `ridge_metric`
(vertical high-pass of horizontal sections: the slice banding J1 is about).

CLI:  python fit_to_reference.py prove      (synthetic proof: sphere -> ellipsoid with a planted bump inside an
                                             excluded zone; the fit must reach the ellipsoid outside and must NOT
                                             adopt the bump inside, without a crease at the zone's rim)
Case values (masks, schedules, which reference where) live in the case's own script, never here (G14).
"""
# ---- FUNCTION INDEX (engine/tools/func_index.py; grep 'def <name>' to jump) ----
#   read_ply(path)  - Binary little-endian PLY with float x,y,z (+ optional uchar red,green,blue) and triangle faces.
#   write_ply(path, v, f, col, comment)
#   face_normals(v, f, unit)
#   vertex_normals(v, f)
#   adjacency(nv, f)
#   laplacian(nv, f)  - Row-normalised graph Laplacian L = I - D^-1 A (L v = v - mean of neighbours).
#   smooth_field(x, L, iters, alpha)  - Plain Laplacian smoothing of a per-vertex field (used for normals and masks, ...
#   weld(v, f, tol)
#   boundary_vertices(nv, f)
#   smoothstep(t)
#   soft_ball(p, centre, r0, r1)  - 1 inside radius r0, 0 beyond r1, smooth between.
#   soft_box(p, lo, hi, ramp)  - 1 inside the axis box [lo, hi], falling smoothly to 0 over `ramp` (per axis) outside...
#   class RefSurface [mask_faces, step]  - A reference mesh as face samples (centroid + unit normal) in direction-bin...
#   facing_contact(v, f, gap, cos_opp, k)  - Faces of a mesh that face another part of the same mesh within `gap` (op...
#   solve_increment(Lop, n, w, d, lam, eps, pin, pin_axis, kappa,...)  - argmin_u sum w (n.u - d)^2 + lam |L u|^2 + t...
#   clusters(v, f, cell)  - Coarse graph for the stiff levels: the connected pieces of the mesh inside each cubic cel...
#   fit(v, f, refs, ref_weights, keep, schedule, pin,...)  - Fit vertices v (faces f) to the references.
#   fair(v, f, weight, iters, lam, mu, pin)  - Taubin smoothing (no shrinkage), applied per vertex with strength `wei...
#   harmonic_fill(v, f, region)  - Replace the vertices in `region` by the harmonic (membrane) interpolation of their...
#   split_caps(v, f, axis, tol)  - Flat caps at the extremes of `axis`: returns (side faces, cap faces, cap-interior ...
#   heightfield_fill(v, f, centre, axis, r_fit, r_fill, r_blend, d...)
#   retriangulate_caps(v, side_faces, axis, tol)  - Close the open rims of a side mesh that lie in planes at the extr...
#   biharmonic_fill(v, f, region)  - Replace the vertices in `region` (bool) by the solution of L^2 x = 0 with everyt...
#   refine_local(v, f, sel_fn, levels, col, extra)  - Conforming refinement: at each level, every edge with an endpoi...
#   surface_samples(v, f, per_face, rng)  - Points on the surface (face centroids, plus random barycentric points if ...
#   point_to_surface(p, v, f, tree, k)  - Approximate distance from points p to a triangle mesh: nearest of the k nea...
#   twosided(v, f, rv, rf, src_keep, ref_side, per_face)  - Two-sided distances between a mesh (v, f) and a reference...
#   ridge_metric(v, f, z0, z1, step, band, nang, keep)  - Slice banding (J1): horizontal sections every `step`; per a...
#   prove()  - Sphere r = 100 mm (with 0.4 mm horizontal ridges planted, J1) fitted to an ellipsoid 130 x 90 x 110 mm...
#   blend_fit(v0, v_fit, alpha)  - A region fit laid into a body that stays: v0 + alpha (v_fit - v0), alpha a smooth ...
#   prove_frozen()  - FROZEN mode + blend (pin_axis=None, blend_fit; woman2 build 07: arms, shoulders and side walls ...
#   (+ 9 private helpers: grep '^def _')
# ---- END FUNCTION INDEX ----
import os
import sys
import time
import json

import numpy as np
from scipy import sparse
from scipy.spatial import cKDTree

try:  # cuSPARSE is not installed with the engine's CuPy (no nvJitLink), so sparse products are ELL gathers
    import cupy as cp
    _HAS_CUPY = True
except Exception:  # pragma: no cover
    cp = None
    _HAS_CUPY = False


import os as _os_mg, sys as _sys_mg  # noqa: E402  (build A1: the engine's one closest point, normals, cotangent Laplacian)
_MG_DIR = _os_mg.path.normpath(_os_mg.path.join(_os_mg.path.dirname(_os_mg.path.abspath(__file__)), '.'))
if _MG_DIR not in _sys_mg.path:
    _sys_mg.path.append(_MG_DIR)
import mesh_geom as _MG  # noqa: E402


# ----------------------------------------------------------------------------------------------- PLY in / out
def read_ply(path):
    """Binary little-endian PLY with float x,y,z (+ optional uchar red,green,blue) and triangle faces."""
    b = open(path, 'rb').read()
    i = b.find(b'end_header') + len(b'end_header')
    while b[i:i + 1] in (b'\r', b'\n'):
        i += 1
    hdr = b[:i].decode('ascii').split('\n')
    nv = nf = 0
    props, cur = [], None
    for L in hdr:
        t = L.split()
        if not t:
            continue
        if t[0] == 'element':
            cur = t[1]
            nv = int(t[2]) if cur == 'vertex' else nv
            nf = int(t[2]) if cur == 'face' else nf
        elif t[0] == 'property' and cur == 'vertex':
            props.append((t[2], t[1]))
    tm = {'float': 'f4', 'uchar': 'u1', 'double': 'f8', 'int': 'i4'}
    dt = np.dtype([(n, '<' + tm[k]) for n, k in props])
    V = np.frombuffer(b, dt, nv, i)
    Fr = np.frombuffer(b, np.dtype([('n', 'u1'), ('i', '<i4', 3)]), nf, i + nv * dt.itemsize)
    assert (Fr['n'] == 3).all(), 'triangles only'
    v = np.stack([V['x'], V['y'], V['z']], 1).astype(np.float64)
    col = np.stack([V['red'], V['green'], V['blue']], 1).copy() if 'red' in V.dtype.names else None
    return v, Fr['i'].astype(np.int64), col


def write_ply(path, v, f, col=None, comment=None):
    nv, nf = len(v), len(f)
    h = ['ply', 'format binary_little_endian 1.0']
    if comment:
        h.append('comment ' + comment)
    h += ['element vertex %d' % nv, 'property float x', 'property float y', 'property float z']
    fields = [('x', '<f4'), ('y', '<f4'), ('z', '<f4')]
    if col is not None:
        h += ['property uchar red', 'property uchar green', 'property uchar blue']
        fields += [('r', 'u1'), ('g', 'u1'), ('b', 'u1')]
    h += ['element face %d' % nf, 'property list uchar int vertex_indices', 'end_header']
    V = np.empty(nv, np.dtype(fields))
    V['x'], V['y'], V['z'] = v[:, 0], v[:, 1], v[:, 2]
    if col is not None:
        V['r'], V['g'], V['b'] = col[:, 0], col[:, 1], col[:, 2]
    Fw = np.empty(nf, np.dtype([('n', 'u1'), ('i', '<i4', 3)]))
    Fw['n'] = 3
    Fw['i'] = f
    with open(path, 'wb') as fh:
        fh.write(('\n'.join(h) + '\n').encode('ascii'))
        fh.write(V.tobytes())
        fh.write(Fw.tobytes())


# ----------------------------------------------------------------------------------------------- mesh basics
def face_normals(v, f, unit=True):
    n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    if unit:
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-30
    return n


def vertex_normals(v, f):
    n = _MG.vertex_normal_sums(v, f)  # area weighted
    return n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-30)


def adjacency(nv, f):
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    e = np.concatenate([e, e[:, ::-1]])
    A = sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(nv, nv)).tocsr()
    A.data[:] = 1.0
    return A


def laplacian(nv, f):
    """Row-normalised graph Laplacian L = I - D^-1 A (L v = v - mean of neighbours)."""
    A = adjacency(nv, f)
    deg = np.asarray(A.sum(1)).ravel()
    Dinv = sparse.diags(1.0 / np.maximum(deg, 1))
    return (sparse.identity(nv, format='csr') - Dinv @ A).tocsr()


def smooth_field(x, L, iters=10, alpha=0.5):
    """Plain Laplacian smoothing of a per-vertex field (used for normals and masks, never for positions)."""
    for _ in range(iters):
        x = x - alpha * (L @ x)
    return x


def weld(v, f, tol=1e-7):
    q = np.round(v / tol).astype(np.int64)
    _, idx, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    f2 = inv[f]
    keep = (f2[:, 0] != f2[:, 1]) & (f2[:, 1] != f2[:, 2]) & (f2[:, 2] != f2[:, 0])
    return v[idx], f2[keep]


def boundary_vertices(nv, f):
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), 1)
    key = e[:, 0] * nv + e[:, 1]
    u, c = np.unique(key, return_counts=True)
    b = u[c == 1]
    out = np.zeros(nv, bool)
    out[b // nv] = True
    out[b % nv] = True
    return out


# ----------------------------------------------------------------------------------------------- soft masks
def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def soft_ball(p, centre, r0, r1):
    """1 inside radius r0, 0 beyond r1, smooth between."""
    d = np.linalg.norm(p - np.asarray(centre)[None], axis=1)
    return 1.0 - smoothstep((d - r0) / max(r1 - r0, 1e-12))


def soft_box(p, lo, hi, ramp):
    """1 inside the axis box [lo, hi], falling smoothly to 0 over `ramp` (per axis) outside it."""
    lo, hi, ramp = (np.broadcast_to(np.asarray(a, float), (3,)) for a in (lo, hi, ramp))
    m = np.ones(len(p))
    for k in range(3):
        out = np.maximum(lo[k] - p[:, k], 0) + np.maximum(p[:, k] - hi[k], 0)
        m *= 1.0 - smoothstep(out / ramp[k])
    return m


# ----------------------------------------------------------------------------------------------- reference surface
def _directions():
    d = np.array([[i, j, k] for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1) if (i, j, k) != (0, 0, 0)],
                 float)
    return d / np.linalg.norm(d, axis=1, keepdims=True)


class RefSurface:
    """A reference mesh as face samples (centroid + unit normal) in direction-binned KD-trees.

    `step(v, n)` returns, per query vertex, the signed distance along its normal n to the tangent plane of the
    nearest reference face whose normal agrees with n (cos >= cos_min), within dmax.  Faces touching an open
    boundary of the (welded) reference and faces in `face_mask_out` are never used."""

    def __init__(self, v, f, face_mask_out=None, bin_cos=0.64, weld_tol=1e-7, name='ref', face_part=None):
        self.name = name
        if face_part is None:
            v, f = weld(v, f, weld_tol)
        self.v, self.f = v, f
        # part label per face (-1 = any): a vertex of part p only takes faces of part p (or -1); pass an already
        # welded mesh with it
        self.part = np.full(len(f), -1) if face_part is None else np.asarray(face_part)
        self.c = v[f].mean(1)
        self.n = face_normals(v, f)
        bnd = boundary_vertices(len(v), f)
        ok = ~bnd[f].any(1)
        self.n_open_faces = int((~ok).sum())
        if face_mask_out is not None:
            ok &= ~face_mask_out
        self.ok = ok
        self.dirs = _directions()
        self.trees, self.members = [], []
        for d in self.dirs:
            m = np.nonzero(ok & (self.n @ d >= bin_cos))[0]
            self.members.append(m)
            self.trees.append(cKDTree(self.c[m]))

    def mask_faces(self, face_mask_out, bin_cos=0.64):
        """Rebuild with an extra face exclusion (e.g. the contact faces found by facing_contact)."""
        self.ok &= ~face_mask_out
        self.trees, self.members = [], []
        for d in self.dirs:
            m = np.nonzero(self.ok & (self.n @ d >= bin_cos))[0]
            self.members.append(m)
            self.trees.append(cKDTree(self.c[m]))

    def step(self, v, n, cos_min=0.6, dmax=0.05, k=12, part=None):
        N = len(v)
        d = np.zeros(N)
        ok = np.zeros(N, bool)
        dist = np.full(N, np.inf)
        fid = np.full(N, -1)
        b = np.argmax(n @ self.dirs.T, axis=1)
        for bi in range(len(self.dirs)):
            q = np.nonzero(b == bi)[0]
            if len(q) == 0 or len(self.members[bi]) == 0:
                continue
            kk = min(k, len(self.members[bi]))
            dd, ii = self.trees[bi].query(v[q], k=kk, distance_upper_bound=dmax)
            if kk == 1:
                dd, ii = dd[:, None], ii[:, None]
            valid = np.isfinite(dd)
            ii2 = np.where(valid, ii, 0)
            fidx = self.members[bi][ii2]
            cosn = np.einsum('qkj,qj->qk', self.n[fidx], n[q])
            valid &= cosn >= cos_min
            if part is not None:
                fp = self.part[fidx]
                qp = part[q][:, None]
                valid &= (fp == qp) | (fp < 0) | (qp < 0)
            first = np.argmax(valid, axis=1)
            has = valid[np.arange(len(q)), first]
            fsel = fidx[np.arange(len(q)), first]
            m = self.n[fsel]
            c = self.c[fsel]
            den = np.einsum('qj,qj->q', m, n[q])
            step = np.einsum('qj,qj->q', m, c - v[q]) / np.maximum(den, 1e-3)
            d[q] = np.where(has, step, 0.0)
            ok[q] = has
            dist[q] = np.where(has, dd[np.arange(len(q)), first], np.inf)
            fid[q] = np.where(has, fsel, -1)
        return d, ok, dist, fid


class _BinnedNearest:
    """Points with normals in direction-binned KD-trees: the nearest point whose normal agrees with a query normal.
    Used for the MUTUAL check: a reference point may pull a vertex only if no other part of the mesh, facing the same
    way, is clearly nearer to it (woman2: the forearms' fronts were pulled onto the hips' front-lateral surface)."""

    def __init__(self, p, n, bin_cos=0.64):
        self.p, self.n = p, n
        self.dirs = _directions()
        good = np.linalg.norm(n, axis=1) > 0.5
        self.members = [np.nonzero(good & (n @ d >= bin_cos))[0] for d in self.dirs]
        self.trees = [cKDTree(p[m]) if len(m) else None for m in self.members]

    def nearest_dist(self, q, qn, cos_min, dmax, k=12):
        out = np.full(len(q), np.inf)
        b = np.argmax(qn @ self.dirs.T, axis=1)
        for bi in range(len(self.dirs)):
            s = np.nonzero(b == bi)[0]
            if len(s) == 0 or self.trees[bi] is None:
                continue
            kk = min(k, len(self.members[bi]))
            dd, ii = self.trees[bi].query(q[s], k=kk, distance_upper_bound=dmax)
            if kk == 1:
                dd, ii = dd[:, None], ii[:, None]
            valid = np.isfinite(dd)
            idx = self.members[bi][np.where(valid, ii, 0)]
            valid &= np.einsum('qkj,qj->qk', self.n[idx], qn[s]) >= cos_min
            first = np.argmax(valid, axis=1)
            has = valid[np.arange(len(s)), first]
            out[s] = np.where(has, dd[np.arange(len(s)), first], np.inf)
        return out


def facing_contact(v, f, gap=0.005, cos_opp=-0.5, k=24):
    """Faces of a mesh that face another part of the same mesh within `gap` (opposite normals, in front):
    where a reference's surfaces touch or are welded (an arm pressed to the chest wall, a slit).  Returns a face mask."""
    v, f = weld(v, f)
    c = v[f].mean(1)
    n = face_normals(v, f)
    tree = cKDTree(c)
    dd, ii = tree.query(c, k=k, distance_upper_bound=gap)
    valid = np.isfinite(dd)
    ii = np.where(valid, ii, 0)
    opp = np.einsum('qkj,qj->qk', n[ii], n) < cos_opp
    infront = np.einsum('qkj,qj->qk', c[ii] - c[:, None], n) > 0.2 * gap
    hit = (valid & opp & infront).any(1)
    return v, f, hit


# ----------------------------------------------------------------------------------------------- the solver
class _Backend:
    def __init__(self, use_gpu):
        self.gpu = bool(use_gpu and _HAS_CUPY)
        if self.gpu:
            try:
                free, _ = cp.cuda.runtime.memGetInfo()
                self.gpu = free > 1.5e9  # leave room for the Blenders and Cycles (E8)
            except Exception:
                self.gpu = False
        self.xp = cp if self.gpu else np

    def arr(self, a):
        return cp.asarray(a) if self.gpu else np.asarray(a)

    def host(self, a):
        return cp.asnumpy(a) if self.gpu else a


class _EllLaplacian:
    """L = I - D^-1 A and its transpose as padded neighbour gathers (works on numpy and CuPy alike)."""

    def __init__(self, f, nv, be):
        A = adjacency(nv, f).tocsr()
        deg = np.diff(A.indptr)
        md = int(deg.max())
        nbr = np.zeros((nv, md), np.int64)
        msk = np.zeros((nv, md), np.float64)
        for k in range(md):
            has = deg > k
            nbr[has, k] = A.indices[A.indptr[:-1][has] + k]
            msk[has, k] = 1.0
        self.xp = be.xp
        self.nbr = be.arr(nbr)
        self.msk = be.arr(msk)[:, :, None]
        self.inv_deg = be.arr(1.0 / np.maximum(deg, 1))[:, None]
        L = laplacian(nv, f)
        self.diagK = be.arr(np.asarray(L.multiply(L).sum(0)).ravel())[:, None]

    def _nsum(self, u):
        return (u[self.nbr] * self.msk).sum(1)

    def L(self, u):
        return u - self.inv_deg * self._nsum(u)

    def LT(self, u):
        return u - self._nsum(self.inv_deg * u)


def solve_increment(Lop, n, w, d, lam, eps=1e-6, pin=None, pin_axis=2, kappa=1e3, u0=None, tol=1e-4,
                    maxit=4000, be=None, tang=0.0):
    """argmin_u sum w (n.u - d)^2 + lam |L u|^2 + tang |u - n (n.u)|^2 + eps |u|^2 + kappa sum_pin u_axis^2
    (Jacobi-PCG).  Lop: an _EllLaplacian on the same backend.  `tang` holds the tangential part of a FINE step: the
    data only fix the normal part, and without it vertices slid 4-12 mm per iteration along the surface on woman2
    (normal part 0.5 mm, data step 0.03 mm)."""
    be = be or _Backend(True)
    xp = be.xp
    n_ = be.arr(n)
    w_ = be.arr(w)[:, None]
    b = w_ * be.arr(d)[:, None] * n_
    pinw = xp.zeros_like(n_)
    if pin is not None:
        if pin_axis is None:              # FROZEN vertices: all three axes held (a region fit inside a kept body)
            pinw += be.arr(pin.astype(float))[:, None] * kappa
        else:
            pinw[:, pin_axis] = be.arr(pin.astype(float)) * kappa
    M = w_ * n_ * n_ + lam * Lop.diagK + eps + pinw + tang * (1 - n_ * n_)

    def A(u):
        un = xp.sum(n_ * u, 1, keepdims=True)
        return (w_ * un * n_ + lam * Lop.LT(Lop.L(u)) + eps * u + pinw * u
                + (tang * (u - un * n_) if tang else 0.0))

    u = xp.zeros_like(n_) if u0 is None else be.arr(u0)
    r = b - A(u)
    z = r / M
    p = z.copy()
    rz = xp.sum(r * z)
    bn = float(xp.sqrt(xp.sum(b * b))) + 1e-30
    it = 0
    for it in range(maxit):
        Ap = A(p)
        alpha = rz / xp.sum(p * Ap)
        u += alpha * p
        r -= alpha * Ap
        if it % 25 == 0 and float(xp.sqrt(xp.sum(r * r))) / bn < tol:
            break
        z = r / M
        rz2 = xp.sum(r * z)
        p = z + (rz2 / rz) * p
        rz = rz2
    res = float(xp.sqrt(xp.sum(r * r))) / bn
    return be.host(u), it + 1, res


def clusters(v, f, cell):
    """Coarse graph for the stiff levels: the connected pieces of the mesh inside each cubic cell of size `cell`
    (an arm and the chest wall that share a cell stay separate clusters, because only mesh edges join vertices).
    Returns per-vertex cluster labels, their count, and the cluster adjacency (from mesh edges between clusters)."""
    from scipy.sparse.csgraph import connected_components
    nv = len(v)
    q = np.floor(v / cell).astype(np.int64)
    q -= q.min(0)
    key = (q[:, 0] * (q[:, 1].max() + 1) + q[:, 1]) * (q[:, 2].max() + 1) + q[:, 2]
    E = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    same = key[E[:, 0]] == key[E[:, 1]]
    G = sparse.coo_matrix((np.ones(same.sum()), (E[same, 0], E[same, 1])), shape=(nv, nv))
    nc, lab = connected_components(G, directed=False)
    a, b = lab[E[~same, 0]], lab[E[~same, 1]]
    Ac = sparse.coo_matrix((np.ones(len(a)), (a, b)), shape=(nc, nc)).tocsr()
    Ac = ((Ac + Ac.T) > 0).astype(float)
    return lab, nc, Ac


def _coarse_increment(v, f, n, w, d, lab, nc, Ac, lam, pin, pin_axis, kappa=1e3, eps=1e-8, L=None, h=None,
                      cell=None):
    """One coarse step: per-cluster translations t (nc x 3) minimising sum_c (mean data of c) + lam |Lc t|^2,
    solved directly; prolonged to the vertices and smoothed on the mesh so no cluster edge shows."""
    from scipy.sparse.linalg import spsolve
    cnt = np.bincount(lab, minlength=nc).astype(float)
    H = np.zeros((nc, 3, 3))
    g = np.zeros((nc, 3))
    np.add.at(H, lab, w[:, None, None] * n[:, :, None] * n[:, None, :])
    np.add.at(g, lab, (w * d)[:, None] * n)
    H /= cnt[:, None, None]
    g /= cnt[:, None]
    if pin is not None:
        pf = np.bincount(lab, weights=pin.astype(float), minlength=nc) / cnt
        for a in ((0, 1, 2) if pin_axis is None else (pin_axis,)):
            H[:, a, a] += kappa * pf
    deg = np.asarray(Ac.sum(1)).ravel()
    Lc = (sparse.identity(nc) - sparse.diags(1 / np.maximum(deg, 1)) @ Ac).tocsr()
    K = (Lc.T @ Lc).tocsr()
    rows = np.repeat(np.arange(nc) * 3, 9) + np.tile(np.repeat(np.arange(3), 3), nc)
    cols = np.repeat(np.arange(nc) * 3, 9) + np.tile(np.tile(np.arange(3), 3), nc)
    Hs = sparse.coo_matrix((H.reshape(-1), (rows, cols)), shape=(3 * nc, 3 * nc))
    A = (Hs + lam * sparse.kron(K, sparse.identity(3)) + eps * sparse.identity(3 * nc)).tocsc()
    t = spsolve(A, g.reshape(-1)).reshape(nc, 3)
    # clusters with no data: harmonic fill on the cluster graph (bounded by their neighbours).  Left to the
    # thin-plate term they extrapolate their neighbours' slope; at an open boundary (a cap's rim) that drifted
    # 20-25 mm per iteration on woman2.
    wsum = np.bincount(lab, weights=w, minlength=nc)
    nodata = wsum <= 1e-9
    if pin is not None and pin_axis is None:   # frozen clusters are rim (their solved t ~ 0), never filled
        nodata &= pf < 0.5
    X = np.nonzero(nodata)[0]
    O = np.nonzero(~nodata)[0]
    if len(X) and len(O):
        Lx = Lc[X]
        rhs = -(Lx[:, O] @ t[O])
        Lxx = Lx[:, X].tocsc()
        t[X] = np.stack([spsolve(Lxx, rhs[:, k]) for k in range(3)], 1)
    u = t[lab]
    # prolongation: Laplacian smoothing over about one cell (the piecewise-constant field has steps at cell edges)
    k = int(np.ceil(1.5 * (cell / h) ** 2))
    for _ in range(k):
        u = u - 0.5 * (L @ u)
        if pin is not None:
            u[pin, slice(None) if pin_axis is None else pin_axis] = 0.0
    return u


class _ExcludedFill:
    """Extension of a FINE-level increment field into the excluded vertices (keep below `thr`), solved directly
    (CG leaves such data-free zones unconverged).  order=1 (default): harmonic, bounded by the rim's increments
    (max principle).  order=2: biharmonic (C1), but it extrapolates the rim's slope like a cantilever: on woman2 the
    fine steps' slope noise (p90 0.3 mm per 2 mm) moved the 140 mm armpit zone 20-50 mm per iteration.  The
    posture-scale moves of excluded zones come from the coarse levels, which carry them smoothly."""

    def __init__(self, f, nv, keep, thr=0.02, order=1):
        L = laplacian(nv, f)
        self.K = (L.T @ L).tocsr() if order == 2 else L.tocsr()
        self.base = keep < thr
        self.X = np.nonzero(self.base)[0]

    def __call__(self, u, extra=None, fixed=None):
        """extra: bool mask of further vertices to fill this time (e.g. vertices that found no correspondence:
        left to the smoothness alone they drift, an open boundary most of all - the woman2 bottom rim moved 330 mm).
        fixed: vertices never filled (frozen ones: they stay part of the rim with their own increment, zero)."""
        from scipy.sparse.linalg import splu
        Xm = self.base | extra if extra is not None else self.base
        if fixed is not None:
            Xm = Xm & ~fixed
        X = np.nonzero(Xm)[0]
        O = np.nonzero(~Xm)[0]
        if len(X) == 0:
            return u
        Kx = self.K[X]
        lu = splu(Kx[:, X].tocsc())
        u = u.copy()
        rhs = -(Kx[:, O] @ u[O])
        u[X] = np.stack([lu.solve(np.ascontiguousarray(rhs[:, k])) for k in range(3)], 1)
        return u


def fit(v, f, refs, ref_weights, keep, schedule, pin=None, pin_axis=2, use_gpu=True, log=print,
        on_iter=None, part=None):
    """Fit vertices v (faces f) to the references.

    refs        : list of RefSurface
    ref_weights : function(v, n) -> array (N, len(refs)) of blend weights (rows need not sum to 1)
    keep        : per-vertex data weight in [0, 1] (0 = excluded: carried smoothly by its surroundings)
    schedule    : list of dicts {lam, iters, cos_min, dmax[, cell][, mutual][, tang][, robust]} (tang: fine levels'
                  hold on the tangential part of a step, default 1; robust (metres): Cauchy down-weighting of steps
                  that disagree with their neighbourhood's): `mutual` (metres) drops a pull when
                  another source surface facing the same way is that much nearer to the reference point; with `cell`
                  (metres) a COARSE level (clusters of
                  that size, direct solve, lam acts on the cluster graph: ~1-10); without it a FINE level (per-vertex
                  thin-plate step field, Jacobi-PCG, lam ~1e3 .. 1; excluded zones filled biharmonically)
    pin         : bool mask of vertices whose `pin_axis` coordinate must not move (flat caps); with pin_axis=None
                  they are FROZEN (all axes; never filled): a region fitted inside a body that stays as it is, the
                  thin-plate term carrying the fit smoothly into the frozen rim (proof: `prove_frozen`)
    part        : optional int label per vertex (-1 = any), matched against each RefSurface's face labels: an arm
                  vertex only takes arm faces (woman2: the hips were pulled toward a reference arm posed elsewhere)
    Returns the fitted vertices and a per-iteration log."""
    v = v.copy()
    be = _Backend(use_gpu)
    Lell = _EllLaplacian(f, len(v), be)
    Lsp = laplacian(len(v), f)
    E = np.concatenate([f[:, [0, 1]], f[:, [1, 2]]])
    h = float(np.median(np.linalg.norm(v[E[:, 0]] - v[E[:, 1]], axis=1)))
    fill = _ExcludedFill(f, len(v), keep)
    cl_cache = {}
    hist = []
    log('fit: %d vertices, %d refs, edge %.2f mm, %d excluded (filled), backend %s'
        % (len(v), len(refs), h * 1e3, len(fill.X), 'GPU (CuPy)' if be.gpu else 'numpy'))
    for st in schedule:
        coarse = 'cell' in st
        if coarse and st['cell'] not in cl_cache:
            cl_cache[st['cell']] = clusters(v, f, st['cell'])
        for it in range(st['iters']):
            t0 = time.time()
            n = vertex_normals(v, f)
            W = ref_weights(v, n)
            num = np.zeros(len(v))
            den = np.zeros(len(v))
            mutual = st.get('mutual')
            src = _BinnedNearest(v, n) if mutual else None
            n_rej = 0
            for j, R in enumerate(refs):
                d, ok, dist, fid = R.step(v, n, st['cos_min'], st['dmax'], part=part)
                if mutual:
                    q = np.nonzero(ok)[0]
                    back = src.nearest_dist(R.c[fid[q]], R.n[fid[q]], st['cos_min'], st['dmax'])
                    bad = dist[q] > back + mutual
                    ok[q[bad]] = False
                    n_rej += int(bad.sum())
                wj = W[:, j] * ok
                num += wj * d
                den += wj
            has = den > 1e-9
            d = np.where(has, num / np.maximum(den, 1e-9), 0.0)
            w = keep * has
            if st.get('robust') and not coarse:
                # a step that disagrees with its neighbourhood's steps is down-weighted (Cauchy): where two
                # reference surfaces lie close (an arm hanging by the flank) the pulls alternate and tore the skin
                a, b = w * d, w.copy()
                for _ in range(st.get('robust_iters', 8)):
                    a = a - 0.5 * (Lsp @ a)
                    b = b - 0.5 * (Lsp @ b)
                ds = a / np.maximum(b, 1e-9)
                r = np.abs(d - ds)
                w = w / (1.0 + (r / st['robust']) ** 2)
            if coarse:
                lab, nc, Ac = cl_cache[st['cell']]
                u = _coarse_increment(v, f, n, w, d, lab, nc, Ac, st['lam'], pin, pin_axis, L=Lsp, h=h,
                                      cell=st['cell'])
                cgit, res = nc, 0.0
            else:
                u, cgit, res = solve_increment(Lell, n, w, d, st['lam'], pin=pin, pin_axis=pin_axis, be=be,
                                               tang=st.get('tang', 1.0), kappa=1e6 if pin_axis is None else 1e3)
                u = fill(u, extra=~has, fixed=pin if pin_axis is None else None)
                if pin is not None:
                    u[pin, slice(None) if pin_axis is None else pin_axis] = 0.0
            v += u
            sel = (w > 0.5)
            mv = np.linalg.norm(u, axis=1)
            rec = dict(level=('coarse %.0f mm' % (st['cell'] * 1e3)) if coarse else 'fine', lam=st['lam'],
                       cos_min=st['cos_min'], dmax=st['dmax'], data_frac=float(has.mean()),
                       step_abs_p50_mm=float(np.median(np.abs(d[sel])) * 1e3),
                       step_abs_p90_mm=float(np.percentile(np.abs(d[sel]), 90) * 1e3),
                       move_max_mm=float(mv.max() * 1e3),
                       move_max_excluded_mm=float(mv[keep < 0.5].max() * 1e3) if (keep < 0.5).any() else 0.0,
                       solver=int(cgit), res=float(res), mutual_rejected=n_rej, sec=round(time.time() - t0, 1))
            hist.append(rec)
            log('  %s lam %.0e it %d: |step| p50 %.2f p90 %.2f mm, data %.3f (mutual-rejected %d), move max %.1f '
                '(excl %.1f) mm, solver %d (%.1e), %.1fs' % (rec['level'], st['lam'], it, rec['step_abs_p50_mm'],
                                                            rec['step_abs_p90_mm'], rec['data_frac'], n_rej,
                                                            rec['move_max_mm'], rec['move_max_excluded_mm'], cgit,
                                                            res, rec['sec']))
            if on_iter:
                on_iter(v, rec)
    return v, hist


# ----------------------------------------------------------------------------------------------- fairing / fill
def fair(v, f, weight, iters=10, lam=0.5, mu=-0.53, pin=None):
    """Taubin smoothing (no shrinkage), applied per vertex with strength `weight` in [0, 1]."""
    L = laplacian(len(v), f)
    w = np.asarray(weight, float)[:, None]
    if pin is not None:
        w = w * (~pin)[:, None]
    v = v.copy()
    for _ in range(iters):
        v = v - lam * w * (L @ v)
        v = v - mu * w * (L @ v)
    return v


def harmonic_fill(v, f, region):
    """Replace the vertices in `region` by the harmonic (membrane) interpolation of their fixed neighbours over the
    faces f.  Bounded by its rim (max principle), so it is the right rebuild for a flat cap: a planar rim gives a
    planar cap.  (A biharmonic fill of a large data-free disc amplifies rim noise: the woman2 caps drifted 145 mm.)"""
    from scipy.sparse.linalg import spsolve
    L = laplacian(len(v), f)
    I = np.nonzero(region)[0]
    O = np.nonzero(~region)[0]
    Lii = L[I][:, I].tocsc()
    rhs = -(L[I][:, O] @ v[O])
    out = v.copy()
    for k in range(3):
        out[I, k] = spsolve(Lii, rhs[:, k])
    return out


def split_caps(v, f, axis=2, tol=2e-4):
    """Flat caps at the extremes of `axis`: returns (side faces, cap faces, cap-interior vertices, rim vertices).
    The fit runs on the side faces only (caps would otherwise be large data-free discs); the caps are rebuilt from
    their rims afterwards with harmonic_fill."""
    lo, hi = v[:, axis].min(), v[:, axis].max()
    on = (np.abs(v[:, axis] - lo) < tol) | (np.abs(v[:, axis] - hi) < tol)
    capf = on[f].all(1)
    side = f[~capf]
    used = np.zeros(len(v), bool)
    used[side.ravel()] = True
    interior = on & ~used
    rim = on & used
    return side, f[capf], interior, rim


def heightfield_fill(v, f, centre, axis, r_fit, r_fill, r_blend, deg=4, ridge=1e-6, method='poly'):
    """Re-make a round zone of a surface as the smooth surface its surroundings imply, in the zone's own height frame:
    a degree-`deg` polynomial height h(u, w) along `axis` is fitted to the surface in the annulus r_fit = (r0, r1)
    (r measured across the axis), then vertices inside r_fill take it, blended back to the surface by r_blend.
    Why: on a dome (a breast's apex under an excluded nipple zone) the biharmonic fill of positions with the graph
    Laplacian came out ~2 mm flat at the apex (woman2), a flat facet; the height frame keeps the dome's curvature.
    method='biharmonic': instead of the polynomial, the height inside r_fill solves the graph thin-plate equation with
    the surface outside fixed (heights and slopes carried in, C1): it keeps a steep side the polynomial cannot (the
    woman2 breasts turn sharply at their lateral edge, inside the nipple zone; a membrane (harmonic) fill cut that
    corner by ~10 mm).  rms is then 0.
    Only the sheet facing along the axis is touched.  Returns (new vertices, rms of the annulus fit in metres)."""
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    e1 = np.cross(a, [0.0, 0.0, 1.0])
    if np.linalg.norm(e1) < 1e-6:
        e1 = np.cross(a, [1.0, 0.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    d = v - np.asarray(centre)[None]
    h, u, w = d @ a, d @ e1, d @ e2
    r = np.hypot(u, w)
    n = vertex_normals(v, f)
    sheet = (n @ a > 0.2) & (np.abs(h) < r_fit[1]) & (r < r_fit[1])
    if method == 'biharmonic':
        from scipy.sparse.linalg import spsolve
        reg = sheet & (r < r_fill)
        L = laplacian(len(v), f)
        K = (L.T @ L).tocsr()
        I = np.nonzero(reg)[0]
        O = np.nonzero(~reg)[0]
        hn = h.copy()
        hn[I] = spsolve(K[I][:, I].tocsc(), -(K[I][:, O] @ h[O]))
        return v + ((hn - h) * reg)[:, None] * a[None], 0.0
    fitm = sheet & (r >= r_fit[0])
    s = r_fit[1]
    terms = [(i, j) for i in range(deg + 1) for j in range(deg + 1 - i)]
    X = np.stack([(u / s) ** i * (w / s) ** j for i, j in terms], 1)
    A = X[fitm]
    coef = np.linalg.solve(A.T @ A + ridge * np.eye(len(terms)), A.T @ h[fitm])
    rms = float(np.sqrt(np.mean((A @ coef - h[fitm]) ** 2)))
    wt = 1.0 - smoothstep((r - r_fill) / max(r_blend - r_fill, 1e-9))
    wt = wt * sheet
    out = v + ((X @ coef - h) * wt)[:, None] * a[None]
    return out, rms


def _ear_clip(P):
    """Triangulate a simple polygon P (n x 2, either orientation) by ear clipping; triangles keep P's order."""
    n = len(P)
    sgn = 1.0 if (np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]) > 0) else -1.0
    idx = list(range(n))
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 10 * n:
        guard += 1
        m = len(idx)
        Q = P[idx]
        a, b, c = np.roll(Q, 1, 0), Q, np.roll(Q, -1, 0)
        cr = sgn * ((b[:, 0] - a[:, 0]) * (c[:, 1] - b[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - b[:, 0]))
        order = np.argsort(-cr)  # try the most convex corners first
        done = False
        for k in order[:64]:
            if cr[k] <= 1e-14:
                break
            A, B, C = Q[k - 1], Q[k], Q[(k + 1) % m]
            others = np.ones(m, bool)
            others[[k - 1 if k > 0 else m - 1, k, (k + 1) % m]] = False
            R = Q[others]

            def side(p, q, r):
                return sgn * ((q[0] - p[0]) * (r[:, 1] - p[1]) - (q[1] - p[1]) * (r[:, 0] - p[0]))
            inside = (side(A, B, R) > 0) & (side(B, C, R) > 0) & (side(C, A, R) > 0)
            if not inside.any():
                tris.append((idx[k - 1], idx[k], idx[(k + 1) % m]))
                idx.pop(k)
                done = True
                break
        if not done:  # degenerate remainder: clip the most convex corner anyway
            k = int(order[0])
            tris.append((idx[k - 1], idx[k], idx[(k + 1) % m]))
            idx.pop(k)
    if len(idx) == 3:
        tris.append(tuple(idx))
    return np.array(tris, np.int64)


def retriangulate_caps(v, side_faces, axis=2, tol=2e-4):
    """Close the open rims of a side mesh that lie in planes at the extremes of `axis` with ear-clipped flat caps
    (no interior vertices).  A harmonic re-fill of a cap's old interior folds where its rim is not convex (the woman2
    bottom cap folded at the gluteal cleft: 11 edges over 160 deg).  Returns (v, f, kept_old_index)."""
    nv = len(v)
    E = np.concatenate([side_faces[:, [0, 1]], side_faces[:, [1, 2]], side_faces[:, [2, 0]]])
    key = np.minimum(E[:, 0], E[:, 1]) * nv + np.maximum(E[:, 0], E[:, 1])
    u, cnt = np.unique(key, return_counts=True)
    bset = set(u[cnt == 1].tolist())
    bnd = np.array([e for e, k in zip(E, key) if k in bset])
    nxt = {int(a): int(b) for a, b in bnd}
    lo, hi = v[:, axis].min(), v[:, axis].max()
    caps = []
    seen = set()
    for s0 in list(nxt):
        if s0 in seen:
            continue
        loop = [s0]
        seen.add(s0)
        while nxt[loop[-1]] != s0:
            loop.append(nxt[loop[-1]])
            seen.add(loop[-1])
        loop = np.array(loop[::-1])  # the cap runs the rim against the side faces' direction
        zc = v[loop, axis]
        assert np.ptp(zc) < tol and (abs(zc.mean() - lo) < tol or abs(zc.mean() - hi) < tol), 'rim not on a cap plane'
        ax2 = [k for k in range(3) if k != axis]
        caps.append(loop[_ear_clip(v[loop][:, ax2])])
    f = np.concatenate([side_faces] + caps)
    used = np.zeros(nv, bool)
    used[f.ravel()] = True
    kept = np.nonzero(used)[0]
    remap = np.full(nv, -1)
    remap[kept] = np.arange(len(kept))
    return v[kept], remap[f], kept


def biharmonic_fill(v, f, region):
    """Replace the vertices in `region` (bool) by the solution of L^2 x = 0 with everything outside fixed:
    the smooth membrane the rim (two rings, so C1) implies.  Used to remove a feature before rebuilding it."""
    from scipy.sparse.linalg import spsolve
    L = laplacian(len(v), f)
    K = (L.T @ L).tocsr()
    I = np.nonzero(region)[0]
    O = np.nonzero(~region)[0]
    Kii = K[I][:, I].tocsc()
    Kio = K[I][:, O]
    out = v.copy()
    rhs = -(Kio @ v[O])
    for k in range(3):
        out[I, k] = spsolve(Kii, rhs[:, k])
    return out


# ----------------------------------------------------------------------------------------------- local refinement
def refine_local(v, f, sel_fn, levels, col=None, extra=None):
    """Conforming refinement: at each level, every edge with an endpoint selected by sel_fn(level, v) is split at
    its midpoint; each face is split by its number of split edges (1 -> 2, 2 -> 3, 3 -> 4), so no T-junctions.
    Per-vertex colour (uint8) and extra float fields are interpolated."""
    col = None if col is None else col.astype(np.float64)
    extra = {} if extra is None else {k: np.asarray(a, float) for k, a in extra.items()}
    for lev in range(levels):
        sel = sel_fn(lev, v)
        E = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
        Es = np.sort(E, 1)
        key = Es[:, 0] * len(v) + Es[:, 1]
        uk, inv = np.unique(key, return_inverse=True)
        a, b = uk // len(v), uk % len(v)
        split = sel[a] | sel[b]
        mid = np.full(len(uk), -1)
        ns = int(split.sum())
        mid[split] = len(v) + np.arange(ns)
        v = np.vstack([v, 0.5 * (v[a[split]] + v[b[split]])])
        if col is not None:
            col = np.vstack([col, 0.5 * (col[a[split]] + col[b[split]])])
        for kname in extra:
            x = extra[kname]
            extra[kname] = np.concatenate([x, 0.5 * (x[a[split]] + x[b[split]])], 0)
        nf = len(f)
        m = mid[inv].reshape(3, nf).T  # m[:,0] = mid of (0,1), m[:,1] = (1,2), m[:,2] = (2,0)
        cnt = (m >= 0).sum(1)
        out = [f[cnt == 0]]
        # one split edge: rotate so the split edge is (0,1)
        for r in range(3):
            s = (cnt == 1) & (m[:, r] >= 0)
            if s.any():
                F = np.roll(f[s], -r, axis=1)
                M = m[s, r]
                out += [np.c_[F[:, 0], M, F[:, 2]], np.c_[M, F[:, 1], F[:, 2]]]
        # two split edges: rotate so the unsplit edge is (2,0)
        for r in range(3):
            s = (cnt == 2) & (m[:, (r + 2) % 3] < 0)
            if s.any():
                F = np.roll(f[s], -r, axis=1)
                M = np.roll(m[s], -r, axis=1)  # M[:,0]=mid(0,1), M[:,1]=mid(1,2)
                # triangles: (m01, 1, m12), and the quad (0, m01, m12, 2) split along its shorter diagonal
                out.append(np.c_[M[:, 0], F[:, 1], M[:, 1]])
                d1 = np.linalg.norm(v[F[:, 0]] - v[M[:, 1]], axis=1)
                d2 = np.linalg.norm(v[M[:, 0]] - v[F[:, 2]], axis=1)
                use1 = d1 <= d2
                out.append(np.where(use1[:, None], np.c_[F[:, 0], M[:, 0], M[:, 1]], np.c_[F[:, 0], M[:, 0], F[:, 2]]))
                out.append(np.where(use1[:, None], np.c_[F[:, 0], M[:, 1], F[:, 2]], np.c_[M[:, 0], M[:, 1], F[:, 2]]))
        s = cnt == 3
        if s.any():
            F, M = f[s], m[s]
            out += [np.c_[F[:, 0], M[:, 0], M[:, 2]], np.c_[M[:, 0], F[:, 1], M[:, 1]],
                    np.c_[M[:, 2], M[:, 1], F[:, 2]], np.c_[M[:, 0], M[:, 1], M[:, 2]]]
        f = np.concatenate(out)
    if col is not None:
        col = np.clip(np.round(col), 0, 255).astype(np.uint8)
    return v, f, col, extra


# ----------------------------------------------------------------------------------------------- measures
def surface_samples(v, f, per_face=1, rng=0):
    """Points on the surface (face centroids, plus random barycentric points if per_face > 1)."""
    pts = [v[f].mean(1)]
    fid = [np.arange(len(f))]
    g = np.random.default_rng(rng)
    for _ in range(per_face - 1):
        r = g.random((len(f), 2))
        flip = r.sum(1) > 1
        r[flip] = 1 - r[flip]
        pts.append(v[f[:, 0]] + r[:, :1] * (v[f[:, 1]] - v[f[:, 0]]) + r[:, 1:] * (v[f[:, 2]] - v[f[:, 0]]))
        fid.append(np.arange(len(f)))
    return np.concatenate(pts), np.concatenate(fid)


def point_to_surface(p, v, f, tree=None, k=8):
    """Approximate distance from points p to a triangle mesh: nearest of the k nearest face centroids, measured to
    that face's plane where the foot lies in the face (else to the centroid).  Good to ~0.1 mm on ~2 mm faces."""
    c = v[f].mean(1)
    nrm = face_normals(v, f)
    tree = tree or cKDTree(c)
    dd, ii = tree.query(p, k=k)
    best = np.full(len(p), np.inf)
    for j in range(k):
        fi = ii[:, j]
        a, b_, c_ = v[f[fi, 0]], v[f[fi, 1]], v[f[fi, 2]]
        nn = nrm[fi]
        h = np.einsum('ij,ij->i', p - a, nn)
        q = p - h[:, None] * nn
        # barycentric inside test
        v0, v1, v2 = b_ - a, c_ - a, q - a
        d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
        d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01 + 1e-30
        bv = (d11 * d20 - d01 * d21) / den
        bw = (d00 * d21 - d01 * d20) / den
        inside = (bv >= 0) & (bw >= 0) & (bv + bw <= 1)
        dist = np.where(inside, np.abs(h), dd[:, j])
        best = np.minimum(best, dist)
    return best


def twosided(v, f, rv, rf, src_keep=None, ref_side=None, per_face=2):
    """Two-sided distances between a mesh (v, f) and a reference (rv, rf), in metres.
    src_keep : per-vertex weight of the mesh; samples with keep < 0.5 (excluded zones) are dropped from BOTH
               directions (reference points whose nearest mesh sample is excluded are dropped too).
    ref_side : optional bool mask of reference faces to use (e.g. its front for reference A)."""
    ps, pf = surface_samples(v, f, per_face)
    keep_s = np.ones(len(ps), bool) if src_keep is None else (src_keep[f[pf]].mean(1) >= 0.5)
    rf_use = rf if ref_side is None else rf[ref_side]
    pr, _ = surface_samples(rv, rf_use, per_face)
    d_sr = point_to_surface(ps[keep_s], rv, rf_use)
    tree_s = cKDTree(ps)
    _, nn = tree_s.query(pr)
    keep_r = keep_s[nn]
    d_rs = point_to_surface(pr[keep_r], v, f)
    return d_sr, d_rs


def ridge_metric(v, f, z0, z1, step=0.001, band=(0.002, 0.012), nang=180, keep=None):
    """Slice banding (J1): horizontal sections every `step`; per angle about each section's centroid, the outermost
    radius r(theta, z); the RMS of r's vertical high-pass (detrended over `band[1]`), in mm.  Ridges, steps and
    terraces between sections raise it; a smooth surface reads near the sampling floor."""
    zs = np.arange(z0, z1, step)
    R = np.full((len(zs), nang), np.nan)
    a = v[f]
    for i, z in enumerate(zs):
        s = a[:, :, 2] - z
        pts = []
        for p_, q_ in [(0, 1), (1, 2), (2, 0)]:
            m = (s[:, p_] * s[:, q_]) < 0
            t = s[m, p_] / (s[m, p_] - s[m, q_])
            pts.append(a[m, p_] + (a[m, q_] - a[m, p_]) * t[:, None])
        P = np.concatenate(pts)
        if len(P) < 20:
            continue
        c = P[:, :2].mean(0)
        th = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])
        r = np.hypot(P[:, 0] - c[0], P[:, 1] - c[1])
        bi = ((th + np.pi) / (2 * np.pi) * nang).astype(int) % nang
        out = np.full(nang, np.nan)
        np.fmax.at(out, bi, r)
        R[i] = out
    from scipy.ndimage import uniform_filter1d
    good = np.isfinite(R).all(0)
    Rg = R[:, good]
    w = max(3, int(round(band[1] / step)))
    lo = uniform_filter1d(Rg, w, axis=0, mode='nearest')
    hp = (Rg - lo)[w:-w]
    return float(np.sqrt(np.nanmean(hp ** 2)) * 1e3), float(np.nanpercentile(np.abs(hp), 99) * 1e3)


# ----------------------------------------------------------------------------------------------- proof
def _icosphere(level):
    t = (1 + 5 ** 0.5) / 2
    v = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
                  [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
    f = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2],
                  [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5],
                  [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]])
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    for _ in range(level):
        v, f, _, _ = refine_local(v, f, lambda l, x: np.ones(len(x), bool), 1)
        v /= np.linalg.norm(v, axis=1, keepdims=True)
    return v, f


def prove():
    """Sphere r = 100 mm (with 0.4 mm horizontal ridges planted, J1) fitted to an ellipsoid 130 x 90 x 110 mm that
    carries a planted 12 mm bump at +x inside an excluded zone.  Must: reach the ellipsoid outside the zone
    (p90 < 0.5 mm), NOT adopt the bump (zone height over the bump-free ellipsoid < 3 mm), stay smooth across the
    zone's rim (no crease: the rim band's p99 dihedral within 1.5x that of the fitted area), remove the ridges after `fair`
    (ridge metric over each surface's clean floor falls by >= 5x).  The same run without the exclusion must adopt the bump (> 9 mm): the
    proof fails on that side too (A22)."""
    out = {}
    v0, f = _icosphere(6)
    s = v0 * 0.1
    s[:, 0] += 0.0  # sphere at origin
    s *= (1 + 0.004 * np.sin(2 * np.pi * s[:, 2:3] / 0.006))  # horizontal ridges: 0.4 mm amplitude, 6 mm apart
    rv, rf = _icosphere(6)
    ax = np.array([0.13, 0.09, 0.11])
    r_clean = rv * ax
    bump = 0.012 * np.exp(-((rv[:, 1] / 0.18) ** 2 + (rv[:, 2] / 0.18) ** 2)) * (rv[:, 0] > 0)
    nrm = vertex_normals(r_clean, rf)
    r_bump = r_clean + bump[:, None] * nrm
    centre = np.array([0.1, 0, 0])
    keep_ex = 1.0 - soft_ball(s, centre, 0.035, 0.055)
    sched = [dict(cell=0.03, lam=3.0, iters=3, cos_min=0.5, dmax=0.08),
             dict(cell=0.01, lam=3.0, iters=3, cos_min=0.5, dmax=0.05),
             dict(lam=1e3, iters=2, cos_min=0.6, dmax=0.04), dict(lam=1e2, iters=3, cos_min=0.7, dmax=0.02),
             dict(lam=1e1, iters=4, cos_min=0.7, dmax=0.02)]
    res = {}
    for tag, keep in [('excluded', keep_ex), ('not_excluded', np.ones(len(s)))]:
        R = RefSurface(r_bump, rf, name='ellipsoid+bump')
        vf, _ = fit(s, f, [R], lambda v, n: np.ones((len(v), 1)), keep, sched, log=lambda *a: None)
        vf = fair(vf, f, np.ones(len(vf)), iters=10)  # the pipeline's fairing pass (J1) ...
        vf = fair(vf, f, 1.0 - keep, iters=30)  # ... stronger where no data replaced the source surface
        # outside: distance to the clean ellipsoid (the bump is far from there)
        outside = keep_ex > 0.99
        d_out = point_to_surface(vf[outside], r_clean, rf)
        # inside: height over the clean ellipsoid at the bump's top (direction +x)
        tip = np.argmax(vf[:, 0])
        h_tip = float(point_to_surface(vf[tip:tip + 1], r_clean, rf)[0])
        res[tag] = dict(outside_p90_mm=float(np.percentile(d_out, 90) * 1e3), tip_height_mm=h_tip * 1e3, vf=vf)
    # crease at the zone rim: dihedral angles of edges in the rim band vs the global median
    vf = res['excluded']['vf']
    fn = face_normals(vf, f)
    E = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    Fi = np.tile(np.arange(len(f)), 3)
    Es = np.sort(E, 1)
    key = Es[:, 0] * len(vf) + Es[:, 1]
    o = np.argsort(key)
    k2 = key[o]
    pair = np.nonzero(k2[1:] == k2[:-1])[0]
    fa, fb = Fi[o][pair], Fi[o][pair + 1]
    ang = np.degrees(np.arccos(np.clip((fn[fa] * fn[fb]).sum(1), -1, 1)))
    ev = Es[o][pair][:, 0]
    rim = (keep_ex[ev] > 0.02) & (keep_ex[ev] < 0.98)
    far = keep_ex[ev] > 0.999
    # ridge excess over each surface's own clean floor (a curved surface reads > 0 without any ridge)
    floor0 = ridge_metric(v0 * 0.1, f, -0.06, 0.06)[0]
    floor1 = ridge_metric(r_clean, rf, -0.06, 0.06)[0]
    rid0 = ridge_metric(s, f, -0.06, 0.06)[0] - floor0
    rid1 = ridge_metric(vf, f, -0.06, 0.06)[0] - floor1
    out = dict(
        excluded=dict(outside_p90_mm=res['excluded']['outside_p90_mm'], tip_height_mm=res['excluded']['tip_height_mm']),
        not_excluded=dict(outside_p90_mm=res['not_excluded']['outside_p90_mm'],
                          tip_height_mm=res['not_excluded']['tip_height_mm']),
        rim_dihedral_p99_deg=float(np.percentile(ang[rim], 99)),
        fitted_dihedral_p99_deg=float(np.percentile(ang[far], 99)),
        ridge_excess_mm_before=rid0, ridge_excess_mm_after=rid1)
    ok = (out['excluded']['outside_p90_mm'] < 0.5 and out['excluded']['tip_height_mm'] < 3.0
          and out['not_excluded']['tip_height_mm'] > 9.0
          and out['rim_dihedral_p99_deg'] <= 1.5 * out['fitted_dihedral_p99_deg']
          and rid1 * 5 <= rid0)
    out['PASS'] = bool(ok)
    print(json.dumps(out, indent=1))
    return out


def blend_fit(v0, v_fit, alpha):
    """A region fit laid into a body that stays: v0 + alpha (v_fit - v0), alpha a smooth per-vertex field (1 where the
    fit is taken, 0 where the body is kept). The fit itself must cover the blend band with data (frozen only beyond
    it): an iterative fit pulls every vertex with data fully onto the reference, so a data-weight ramp does not blend
    and a freeze right at the edge leaves a crease (prove_frozen: rim p99 dihedral ~39 deg); the blended displacement
    of a smooth fit is smooth."""
    return v0 + np.asarray(alpha, float)[:, None] * (v_fit - v0)


def prove_frozen():
    """FROZEN mode + blend (pin_axis=None, blend_fit; woman2 build 07: arms, shoulders and side walls fitted inside a
    body that stays). Sphere r = 100 mm fitted to an ellipsoid 108 x 100 x 104 mm (moves up to 8 mm, the size of the
    build-07 steps); z < -50 mm frozen (the sub-mesh rim of a region fit), data everywhere above it; the fit is taken
    fully above z = 0 and blended out to the kept sphere by z = -30 mm. Must: frozen vertices move 0 (< 1e-6 mm);
    below the blend nothing moves; the taken cap reaches the ellipsoid (p90 < 0.3 mm); no crease in the blend band
    (p99 dihedral <= the cap's + the blend's own smooth bend |D| 6/W^2 h). Planted sides (A22), each must show the defect: the old one-axis pin moves the
    frozen part (> 1 mm); the unblended fit has a crease at its freeze line (p99 over that same bound)."""
    v0, f = _icosphere(6)
    s = v0 * 0.1
    rv, rf = _icosphere(6)
    r = rv * np.array([0.108, 0.100, 0.104])
    frozen = s[:, 2] < -0.05
    keep = (~frozen).astype(float)
    alpha = smoothstep((s[:, 2] + 0.03) / 0.03)
    sched = [dict(lam=1e3, iters=2, cos_min=0.6, dmax=0.03), dict(lam=1e2, iters=3, cos_min=0.7, dmax=0.02),
             dict(lam=1e1, iters=3, cos_min=0.7, dmax=0.015), dict(lam=3.0, iters=3, cos_min=0.7, dmax=0.012)]
    R = RefSurface(r, rf, name='ellipsoid')

    def p99(v, lo, hi):
        e, a, b, ang = _edge_angles(v, f, face_normals(v, f))
        z = s[e[:, 0], 2]
        return float(np.percentile(ang[(z > lo) & (z < hi)], 99))

    out = {}
    for tag, pa in (('frozen', None), ('planted_one_axis_pin', 2)):
        vf, _ = fit(s, f, [R], lambda v, n: np.ones((len(v), 1)), keep, sched, pin=frozen, pin_axis=pa,
                    log=lambda *a: None)
        out[tag] = dict(frozen_move_max_mm=float(np.linalg.norm(vf - s, axis=1)[frozen].max() * 1e3), vf=vf)
    vf = out['frozen'].pop('vf'); out['planted_one_axis_pin'].pop('vf')
    vb = blend_fit(s, vf, alpha)
    top = s[:, 2] > 0.005
    cap = p99(vb, 0.03, 1.0)
    out['blend'] = dict(kept_move_max_mm=float(np.linalg.norm(vb - s, axis=1)[s[:, 2] < -0.03].max() * 1e3),
                        cap_fit_p90_mm=float(np.percentile(point_to_surface(vb[top], r, rf), 90) * 1e3),
                        band_dihedral_p99_deg=p99(vb, -0.035, 0.005), cap_dihedral_p99_deg=cap)
    # the blend's own smooth bend: |D| max|alpha''| h (alpha = smoothstep over W: max|alpha''| = 6 / W^2); a crease is
    # bending beyond the cap's own plus that bound
    E = np.concatenate([f[:, [0, 1]], f[:, [1, 2]]])
    h = float(np.median(np.linalg.norm(s[E[:, 0]] - s[E[:, 1]], axis=1)))
    band = (s[:, 2] > -0.03) & (s[:, 2] < 0.0)
    bound = float(np.degrees(np.linalg.norm(vf - s, axis=1)[band].max() * 6 / 0.03 ** 2 * h))
    out['blend']['allowed_p99_deg'] = cap + bound
    out['planted_unblended'] = dict(freeze_line_dihedral_p99_deg=p99(vf, -0.056, -0.044))
    b = out['blend']
    out['PASS'] = bool(out['frozen']['frozen_move_max_mm'] < 1e-6 and b['kept_move_max_mm'] < 1e-6
                       and b['cap_fit_p90_mm'] < 0.3 and b['band_dihedral_p99_deg'] <= cap + bound
                       and out['planted_one_axis_pin']['frozen_move_max_mm'] > 1.0
                       and out['planted_unblended']['freeze_line_dihedral_p99_deg'] > cap + bound)
    print(json.dumps(out, indent=1))
    return out


def _edge_angles(v, f, fn):
    E = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    Fi = np.tile(np.arange(len(f)), 3)
    Es = np.sort(E, 1)
    key = Es[:, 0] * len(v) + Es[:, 1]
    o = np.argsort(key)
    k2 = key[o]
    pair = np.nonzero(k2[1:] == k2[:-1])[0]
    fa, fb = Fi[o][pair], Fi[o][pair + 1]
    ang = np.degrees(np.arccos(np.clip((fn[fa] * fn[fb]).sum(1), -1, 1)))
    return Es[o][pair], fa, fb, ang


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'prove_frozen':
        r = prove_frozen()
        if len(sys.argv) > 2:
            json.dump(r, open(sys.argv[2], 'w'), indent=1)
    elif len(sys.argv) > 1 and sys.argv[1] == 'prove':
        r = prove()
        if len(sys.argv) > 2:
            json.dump(r, open(sys.argv[2], 'w'), indent=1)
    else:
        print(__doc__)
