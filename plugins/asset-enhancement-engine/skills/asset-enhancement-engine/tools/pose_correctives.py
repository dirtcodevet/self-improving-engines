"""POSE CORRECTIVES BY COMPUTATION (2026-10-21, woman2 build 13c): what a skinned body's posed skin should be, worked out
from its rest skin and measured tissue values, and stored as rest-space shape-key offsets driven by the pose. No
sculpting: every offset is the difference between a computed posed skin and the skinned one.

Three mechanisms, each a real one, computed on the posed skin of one sample pose:
  1. ArapField: the skin keeps its own rest shape locally (as-rigid-as-possible, Sorkine & Alexa 2007): linear skinning
     loses volume, pinches and bunches where weights blend bones turned far apart, and concentrates stretch where its
     weights step. The posed skin is re-solved on a region so each vertex's neighbourhood is its rest neighbourhood
     turned (rotations started from the skinning Jacobian's polar part), held to the skinned skin by a data weight that
     is small in the region's core and large at its edge. Volume, the rest form of the armpit and shoulder, and the
     spread of stretch over the skin come back; the region's edge stays where skinning put it.
  2. breast_envelope: the breast as a soft incompressible mass under a pre-tensioned skin membrane, on the chest wall.
     The pose stretches the skin envelope (the skinning's strain of the breast skin); the tension it adds presses the
     convex skin in (p = N : S, membrane tension against the curvature tensor); the mass keeps its volume (a uniform
     pressure change), its own stiffness and the weight of its column (density x g) resist, the rib cage / chest wall
     is the hard limit. Linearised about the skinned pose; one sparse solve plus an active set for the limit.
  3. self_contact: skin that has passed into skin it was far from at rest (a fold closing on itself, the arm pressed on
     the side or the breast) is pushed out along the other surface's normal, half each, and the region re-solved with
     those points held, so soft tissue flattens where it touches and the surface round it follows.
Then to_rest(J, D) turns the posed fix D into the rest-space key offset (J from pose_samples_bl.py), and the hat
functions give each key a weight that is a simple driver expression of the pose (0 at rest, a partition of unity
between nodes), so the keys cover the range continuously.

  polar(J) -> rotations; to_rest(J, D) -> offsets
  ArapField(V0, F, lam, R_init=None).solve(Y, T=None, extra=None, iters=8) -> X      (sub-mesh arrays)
  breast_envelope(V0, F, Y, patch_w, cw_V, cw_F, prm) -> (u, info)                   normal move per patch vertex
  self_contact(X, F, V0, cand, rest_sep, max_d, gap, share=None) -> (ids, targets, depth, face)
  sheets_creases(V0, Y, F) -> per-triangle area ratio and per-edge dihedral rise (for quick checks)
  hat(x, knots, j) / hat_expr(var, knots, j) -> the weight of knot j (piecewise linear, flat beyond the end knots)
Proof: engine/tools/test_pose_correctives.py.
"""
import numpy as np

import mesh_geom as MG


# ----------------------------------------------------------------------------------------------- rest space and rotations
def polar(J):
    """nearest rotation to each 3x3 (SVD, reflection removed)"""
    U, s, Vt = np.linalg.svd(J)
    d = np.sign(np.linalg.det(U @ Vt))
    U[:, :, 2] *= d[:, None]
    return U @ Vt


def to_rest(J, D):
    """posed moves D (n, 3) -> rest-space offsets with J d = D (J: d posed / d rest, (n, 3, 3))"""
    return np.linalg.solve(np.asarray(J, float), np.asarray(D, float)[:, :, None])[:, :, 0]


# ----------------------------------------------------------------------------------------------- 1. ARAP on a region
class ArapField:
    """as-rigid-as-possible posed skin on a sub-mesh (V0 rest, F its triangles), data weight lam (n,) per vertex.
    E = sum_ij w_ij |(x_i - x_j) - R_i (r_i - r_j)|^2 + sum_i lam_i |x_i - t_i|^2 (+ extra holds). w = clamped cotangent."""

    def __init__(self, V0, F, lam):
        from scipy import sparse
        from scipy.sparse.linalg import splu
        self.V0 = np.asarray(V0, float); self.F = np.asarray(F, np.int64); self.lam = np.asarray(lam, float)
        Lm, _ = MG.cot_laplacian(self.V0, self.F, clamp=True)
        K = -Lm
        self.K = K.tocsr()
        C = sparse.triu(self.K, k=1).tocoo()
        self.ei, self.ej, self.w = C.row.astype(np.int64), C.col.astype(np.int64), -C.data
        self.R0e = self.V0[self.ei] - self.V0[self.ej]
        self.A0 = (self.K + sparse.diags(self.lam)).tocsc()
        self.lu = splu(self.A0)

    def _acc(self, idx, vals, n):
        out = np.zeros((n,) + vals.shape[1:])
        flat = vals.reshape(len(vals), -1)
        o = out.reshape(n, -1)
        for c in range(flat.shape[1]):
            o[:, c] = np.bincount(idx, flat[:, c], minlength=n)
        return out

    def local(self, X):
        n = len(X); e = X[self.ei] - X[self.ej]
        S = self.w[:, None, None] * e[:, :, None] * self.R0e[:, None, :]
        St = self._acc(self.ei, S, n) + self._acc(self.ej, S, n)
        return polar(St + 1e-12 * np.eye(3))

    def rhs(self, R):
        n = len(R)
        b = 0.5 * self.w[:, None] * np.einsum("eij,ej->ei", R[self.ei] + R[self.ej], self.R0e)
        return self._acc(self.ei, b, n) - self._acc(self.ej, b, n)

    def solve(self, Y, T=None, R_init=None, extra=None, iters=8, cg_tol=1e-10, return_R=False):
        """Y: posed start (n, 3); T: data targets (default Y); extra: (ids, targets, weights) strong holds (contact),
        solved by CG preconditioned with the factorised base matrix. Returns X (and the last rotations if return_R).
        iters=1 with R_init: one global step with the rotations given (no re-fit)."""
        from scipy import sparse
        from scipy.sparse.linalg import LinearOperator, cg
        T = Y if T is None else T
        X = np.array(Y, float)
        R = R_init if R_init is not None else self.local(X)
        A = None
        if extra is not None and len(extra[0]):
            dl = np.zeros(len(X)); np.add.at(dl, extra[0], extra[2])
            A = (self.A0 + sparse.diags(dl)).tocsr()
            M = LinearOperator(A.shape, matvec=self.lu.solve, dtype=float)
        for it in range(iters):
            b = self.rhs(R) + self.lam[:, None] * T
            if A is None:
                X = self.lu.solve(b)
            else:
                b = b.copy(); np.add.at(b, extra[0], extra[2][:, None] * extra[1])
                for c in range(3):
                    X[:, c], _ = cg(A, b[:, c], x0=X[:, c], M=M, rtol=cg_tol, maxiter=200)
            if it < iters - 1 or return_R:
                R = self.local(X) if it < iters - 1 else R
        return (X, R) if return_R else X


# ----------------------------------------------------------------------------------------------- 2. the breast envelope
def _tri_frames(P, F):
    a = P[F[:, 1]] - P[F[:, 0]]; b = P[F[:, 2]] - P[F[:, 0]]
    n = np.cross(a, b); A2 = np.linalg.norm(n, axis=1); n = n / np.maximum(A2, 1e-30)[:, None]
    e1 = a / np.maximum(np.linalg.norm(a, axis=1), 1e-30)[:, None]; e2 = np.cross(n, e1)
    return e1, e2, n, A2 / 2


def breast_envelope(V0, F, Y, wpatch, cw_V, cw_F, prm, Nv=None, pressed=None):
    """u (n,) outward normal move of the posed skin Y on a breast patch (sub-mesh arrays), info dict.
    wpatch (n,): 1 inside the breast, falling to 0 at its edge (the footprint); u = 0 where wpatch < prm['edge'].
    prm: E_breast (Pa), membrane (N/m, skin E x thickness), nu, T0 (N/m pre-tension), rho (kg/m3), g, h_floor (m),
    d_min (m) or d_min_share (of rest depth), restore_volume (bool).
    pressed: (ids, u) normal moves imposed by contact (another part pressing the breast); the mass keeps its volume
    round them, the chest wall's limit still holds."""
    from scipy import sparse
    from scipy.sparse.linalg import spsolve
    V0 = np.asarray(V0, float); Y = np.asarray(Y, float); F = np.asarray(F, np.int64); n = len(Y)
    Nv = MG.vertex_normals(Y, F) if Nv is None else Nv
    # membrane tension from the pose's stretch of the skin (small strain, plane stress), tension only past -T0
    r1, r2, _, Ar = _tri_frames(V0, F); p1, p2, nP, Ap = _tri_frames(Y, F)
    ra = V0[F[:, 1]] - V0[F[:, 0]]; rb = V0[F[:, 2]] - V0[F[:, 0]]
    pa = Y[F[:, 1]] - Y[F[:, 0]]; pb = Y[F[:, 2]] - Y[F[:, 0]]
    Rm = np.stack([np.stack([(ra * r1).sum(1), (rb * r1).sum(1)], 1), np.stack([(ra * r2).sum(1), (rb * r2).sum(1)], 1)], 1)
    Pm = np.stack([np.stack([(pa * p1).sum(1), (pb * p1).sum(1)], 1), np.stack([(pa * p2).sum(1), (pb * p2).sum(1)], 1)], 1)
    Fg = Pm @ np.linalg.inv(Rm)                                       # posed frame <- rest frame, 2x2
    Eg = 0.5 * (np.transpose(Fg, (0, 2, 1)) @ Fg - np.eye(2))           # Green strain, rest frame
    c = prm["membrane"] / (1 - prm["nu"] ** 2)
    tr = Eg[:, 0, 0] + Eg[:, 1, 1]
    N = c * ((1 - prm["nu"]) * Eg + prm["nu"] * tr[:, None, None] * np.eye(2))
    lw, lv = np.linalg.eigh(N)
    lw = np.maximum(lw, -prm["T0"])
    N = lv @ (lw[:, :, None] * np.transpose(lv, (0, 2, 1)))
    J2 = np.linalg.det(Fg)
    Np = Fg @ N @ np.transpose(Fg, (0, 2, 1)) / np.maximum(J2, 1e-6)[:, None, None]   # pushed to the posed frame
    # curvature tensor per posed triangle from its vertex normals (S e = dn; convex with outward normals: positive)
    E3 = np.stack([pa, pb, Y[F[:, 2]] - Y[F[:, 1]]], 1)
    DN = np.stack([Nv[F[:, 1]] - Nv[F[:, 0]], Nv[F[:, 2]] - Nv[F[:, 0]], Nv[F[:, 2]] - Nv[F[:, 1]]], 1)
    eu = np.einsum("tki,ti->tk", E3, p1); ev = np.einsum("tki,ti->tk", E3, p2)
    du = np.einsum("tki,ti->tk", DN, p1); dv = np.einsum("tki,ti->tk", DN, p2)
    # unknowns s = (S11, S12, S22): S11 eu + S12 ev = du ; S12 eu + S22 ev = dv
    Z = np.zeros_like(eu)
    Am = np.concatenate([np.stack([eu, ev, Z], -1), np.stack([Z, eu, ev], -1)], 1)
    bm = np.concatenate([du, dv], 1)
    s = np.linalg.solve(np.transpose(Am, (0, 2, 1)) @ Am + 1e-14 * np.eye(3), np.einsum("tki,tk->ti", Am, bm)[:, :, None])[:, :, 0]
    S = np.stack([np.stack([s[:, 0], s[:, 1]], 1), np.stack([s[:, 1], s[:, 2]], 1)], 1)
    kw, kv = np.linalg.eigh(S)                                          # small triangles read noisy normals: bound the
    kw = np.clip(kw, -prm.get("kappa_max", 200.0), prm.get("kappa_max", 200.0))   # curvature (1/m), then smooth below
    S = kv @ (kw[:, :, None] * np.transpose(kv, (0, 2, 1)))
    p_tri = np.einsum("tij,tji->t", Np, S)                              # N : S (Pa)
    k2_tri = np.einsum("tij,tij->t", S, S)                              # |kappa|^2 = k1^2 + k2^2
    area = np.zeros(n)
    for k in range(3):
        np.add.at(area, F[:, k], Ap / 3)
    pv = np.zeros(n); k2v = np.zeros(n)
    for k in range(3):
        np.add.at(pv, F[:, k], p_tri * Ap / 3); np.add.at(k2v, F[:, k], k2_tri * Ap / 3)
    pv /= np.maximum(area, 1e-30); k2v /= np.maximum(area, 1e-30)
    if prm.get("smooth_iters", 0):                                     # area-weighted one-ring averaging (a few mm)
        from scipy import sparse
        Ad = sparse.coo_matrix((np.ones(6 * len(F)), (np.concatenate([F[:, 0], F[:, 1], F[:, 2], F[:, 1], F[:, 2], F[:, 0]]),
                                np.concatenate([F[:, 1], F[:, 2], F[:, 0], F[:, 0], F[:, 1], F[:, 2]]))), shape=(n, n)).tocsr()
        Ad.data[:] = 1.0
        Ad = Ad + sparse.eye(n)
        Aw = Ad @ sparse.diags(area)
        den = np.asarray(Aw.sum(1)).ravel()
        for _ in range(int(prm["smooth_iters"])):
            pv = (Aw @ pv) / np.maximum(den, 1e-30); k2v = (Aw @ k2v) / np.maximum(den, 1e-30)
    # thickness to the chest wall along -n (rest and posed), for stiffness, the volume and the hard limit
    def depth(P, NN, CV):
        X, d = MG.closest_on_mesh(P, CV, cw_F, k=6)
        sgn = np.sign(((P - X) * NN).sum(1))
        return d * np.where(sgn == 0, 1, sgn)
    N0 = MG.vertex_normals(V0, F)
    h0 = depth(V0, N0, prm["cw_rest"]); h = depth(Y, Nv, cw_V)
    free = wpatch >= prm.get("edge", 0.05)
    hf = np.maximum(h, prm["h_floor"])
    k = prm["E_breast"] / hf                                          # Winkler foundation of the soft mass (Pa/m)
    cdiag = k + prm["rho"] * prm["g"] * Nv[:, 2] - prm["T0"] * k2v
    clamped = int((cdiag < 0.25 * k)[free].sum())
    cdiag = np.maximum(cdiag, 0.25 * k)
    Lm, _ = MG.cot_laplacian(Y, F, clamp=True)
    Kf = (-prm["T0"] * Lm + sparse.diags(area * cdiag)).tocsr()
    fi = np.nonzero(free)[0]
    Kff = Kf[fi][:, fi].tocsc()
    area0 = np.zeros(n)
    for kk in range(3):
        np.add.at(area0, F[:, kk], Ar / 3)
    vol0 = float((area0 * np.maximum(h0, 0))[free].sum()); vol1 = float((area * np.maximum(h, 0))[free].sum())
    dV = (vol0 - vol1) if prm.get("restore_volume", True) else 0.0
    dmin = np.minimum(prm["d_min"], prm["d_min_share"] * np.maximum(h0, 0))
    lo = -(h - dmin)                                                   # u >= lo: the chest wall's hard limit
    fixed = np.zeros(len(fi), bool); ufix = np.zeros(len(fi))
    npressed = 0
    if pressed is not None and len(pressed[0]):
        pos = -np.ones(n, np.int64); pos[fi] = np.arange(len(fi))
        pi_, pu = np.asarray(pressed[0]), np.asarray(pressed[1], float)
        okp = pos[pi_] >= 0
        fixed[pos[pi_[okp]]] = True; ufix[pos[pi_[okp]]] = np.maximum(pu[okp], lo[pi_[okp]])
        npressed = int(okp.sum())
    a_f = area[fi]; p_f = pv[fi]
    for it in range(6):
        act = ~fixed
        K = Kff[act][:, act].tocsc()
        corr = Kff[act][:, fixed] @ ufix[fixed] if fixed.any() else 0.0
        ua = spsolve(K, a_f[act]); ub = spsolve(K, -a_f[act] * p_f[act] - corr)
        dp0 = (dV - (a_f[~act] * ufix[~act]).sum() - (a_f[act] * ub).sum()) / max((a_f[act] * ua).sum(), 1e-30)
        u = np.zeros(len(fi)); u[act] = ub + dp0 * ua; u[~act] = ufix[~act]
        bad = (u < lo[fi] - 1e-9) & ~fixed
        if not bad.any():
            break
        fixed |= bad; ufix[bad] = lo[fi][bad]
    U = np.zeros(n); U[fi] = u
    info = {"patch_vertices": int(len(fi)), "membrane_pressure_Pa_p1_p50_p99": np.percentile(pv[fi], [1, 50, 99]).round(2).tolist(),
            "uniform_pressure_change_Pa": round(float(dp0), 3), "volume_rest_ml": round(vol0 * 1e6, 1),
            "volume_skinned_ml": round(vol1 * 1e6, 1), "volume_after_ml": round((vol1 + (a_f * u).sum()) * 1e6, 1),
            "u_mm_min_max": [round(float(u.min()) * 1e3, 2), round(float(u.max()) * 1e3, 2)],
            "pressed_by_contact": npressed, "at_chest_wall_limit": int(fixed.sum()) - npressed, "stiffness_clamped": clamped,
            "depth_mm_p5_p50": np.percentile(h[fi], [5, 50]).round(4).__mul__(1e3).round(1).tolist()}
    return U, info


# ----------------------------------------------------------------------------------------------- 3. self contact
def self_contact(X, F, V0, cand, rest_sep=0.02, max_d=0.03, gap=0.0005, facing=-0.2, k=24, share=None):
    """vertices of cand that lie inside skin they were at least rest_sep from at rest: (ids, targets, depth, face).
    The target moves a vertex out along the other surface's normal by share x its depth plus half the gap; share (n,)
    per vertex is its part of the meeting (default a half each: the other surface's own vertices are pushed back the
    same way and both flatten to meet; a softer tissue takes more: share_i = E_j / (E_i + E_j)). k must reach past the
    vertex's own surface (on a 2 mm mesh the nearest 48 face centres lie within about 8 mm)."""
    from scipy.spatial import cKDTree
    X = np.asarray(X, float); V0 = np.asarray(V0, float)
    cen = X[F].mean(1); cen0 = V0[F].mean(1)
    fn = MG.face_normals(X, F); vn = MG.vertex_normals(X, F)
    tree = cKDTree(cen)
    dd, ii = tree.query(X[cand], k=k, distance_upper_bound=max_d)
    best = np.full(len(cand), np.inf); bc = np.zeros((len(cand), 3)); bn = np.zeros((len(cand), 3)); bf = np.zeros(len(cand), np.int64)
    for j in range(k):
        f = ii[:, j]; ok = f < len(F)
        if not ok.any():
            continue
        f = np.where(ok, f, 0)
        far = np.linalg.norm(cen0[f] - V0[cand], axis=1) > rest_sep
        q, bw = MG.closest_on_triangles(X[cand], X[F[f, 0]], X[F[f, 1]], X[F[f, 2]], bary=True)
        nq = (bw[:, :, None] * vn[F[f]]).sum(1)                         # the surface normal at the closest point: the
        nq /= np.maximum(np.linalg.norm(nq, axis=1, keepdims=True), 1e-30)   # face normal misreads the side at an edge
        s = ((X[cand] - q) * nq).sum(1)
        face = (vn[cand] * nq).sum(1) < facing
        d = np.linalg.norm(X[cand] - q, axis=1)
        good = ok & far & face & (s < 0) & (d < best)
        best[good] = d[good]; bc[good] = q[good]; bn[good] = nq[good]; bf[good] = f[good]
    hit = np.isfinite(best)
    ids = np.asarray(cand)[hit]; depth = best[hit]
    sh = np.full(len(ids), 0.5) if share is None else share(ids, bf[hit])
    T = X[ids] + bn[hit] * (depth * sh + gap / 2)[:, None]
    return ids, T, depth, bf[hit]


# ----------------------------------------------------------------------------------------------- quick checks
def sheets_creases(V0, Y, F):
    a0 = MG.face_areas(V0, F); a1 = MG.face_areas(Y, F)
    e0, d0 = MG.dihedral_edges(V0, F); e1, d1 = MG.dihedral_edges(Y, F)
    return a1 / np.maximum(a0, 1e-30), a0, e1, d1 - d0, np.linalg.norm(V0[e1[:, 0]] - V0[e1[:, 1]], axis=1)


# ----------------------------------------------------------------------------------------------- pose-space weights
def hat(x, knots, j):
    """piecewise-linear weight of knot j over sorted knots, flat beyond the first and last knots (partition of unity)"""
    x = np.asarray(x, float); K = knots; n = len(K)
    if n == 1:
        return np.ones_like(x)
    up = np.ones_like(x) if j == 0 else np.clip((x - K[j - 1]) / (K[j] - K[j - 1]), 0, 1)
    dn = np.ones_like(x) if j == n - 1 else np.clip((K[j + 1] - x) / (K[j + 1] - K[j]), 0, 1)
    return np.minimum(up, dn)


def _f(v):
    return ("%.4g" % v).replace("+", "")


def hat_expr(var, knots, j, zero_first=False):
    """the same weight as a Blender simple expression; zero_first: knot 0 carries no key (0 there, e.g. the rest)"""
    K = knots; n = len(K)
    parts = []
    sub = lambda a, b: ("%s-%s" % (a, b[1:]) if False else ("%s+%s" % (a, b[1:]) if b.startswith("-") else "%s-%s" % (a, b)))
    if j > 0:
        parts.append("(%s)/%s" % (sub(var, _f(K[j - 1])), _f(K[j] - K[j - 1])))
    if j < n - 1:
        parts.append("(%s)/%s" % (sub(_f(K[j + 1]), var), _f(K[j + 1] - K[j])))
    if len(parts) == 1:
        return "clamp(%s,0,1)" % parts[0]
    return "clamp(min(%s,%s),0,1)" % tuple(parts)
