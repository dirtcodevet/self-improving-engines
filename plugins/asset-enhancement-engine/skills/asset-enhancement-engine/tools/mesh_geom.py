"""MESH GEOMETRY: the engine's one implementation of the small pieces every tool needs (build A1, 2026-10-21).

Before this, closest point on a triangle was written five times (part_frame, loops_lib, a2_measure, b08lib,
surface_fairing), vertex normals in 20+ files, the cotangent Laplacian three times. Each copy now calls these; the
proof (test_mesh_geom.py, its json beside it) checks each against a planted answer and against the copies it replaced.

  face_normals(V, F, unit=True, eps=1e-30)        (m, 3) face normals (unit, or |n| = 2 x area)
  face_areas(V, F)                                (m,)
  vertex_normals(V, F, eps=1e-30, acc_dtype=None) area-weighted unit vertex normals; vertex_normal_sums(V, F) the
                                                  sums before normalising (each face's cross product, |n| = 2 x area)
  cot_laplacian(V, F, clamp=False)                (L, lumped vertex area): off-diagonal +cot/2, diagonal minus the row
                                                  sum; clamp=True sets an obtuse triangle's negative cotangent to 0
  mean_curvature(V, F)                            (H, area): H = -(L V) . N / (2 A), 1/m, positive on a convex surface
  closest_on_triangles(P, A, B, C, bary=False)    Ericson's closest point (Real-Time Collision Detection 5.1.5),
                                                  vectorised and broadcasting over leading axes; bary=True also gives
                                                  the barycentric weights of A, B, C
  closest_on_mesh(P, V, F, k=4)                   (X, dist): exact on the faces round each point's k nearest vertices
  MeshProj(V, F, k=16).project(P)                 (X, dist, face): exact on the k faces whose centroids are nearest
  dihedral_edges(V, T)                            (edges, angle deg) between the two faces of every interior edge
  poly_edges(sizes, flat), quads_tris(sizes, flat)  a polygon mesh's unique edges; its fan triangles and their owner
  poly_dist(P, Q)                                 distance of each point to the closed polyline Q
Units are the mesh's. Nothing here reads or writes files.
"""
import numpy as np            # scipy is imported where it is needed, so Blender's Python (numpy only) can import this


def face_normals(V, F, unit=True, eps=1e-30):
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    if unit:
        n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), eps)
    return n


def face_areas(V, F):
    return 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)


def vertex_normal_sums(V, F, acc_dtype=None):
    """per vertex the sum of its faces' cross products (|cross| = 2 x area: area-weighted, not unit).
    acc_dtype: accumulate in another dtype than V's (seam_checks: float64)"""
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    if acc_dtype is None:
        vn = np.zeros_like(V)
    else:
        fn = fn.astype(acc_dtype); vn = np.zeros((len(V), 3), acc_dtype)
    for k in range(3):
        np.add.at(vn, F[:, k], fn)
    return vn


def vertex_normals(V, F, eps=1e-30, acc_dtype=None):
    """area-weighted unit vertex normals (a vertex with no faces, or whose faces cancel, gets 0)"""
    vn = vertex_normal_sums(V, F, acc_dtype)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), eps)


def cot_laplacian(V, F, clamp=False):
    from scipy import sparse
    n = len(V); I, J, W = [], [], []
    for a, b, c in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
        u, v = V[F[:, b]] - V[F[:, a]], V[F[:, c]] - V[F[:, a]]
        cot = np.einsum("ij,ij->i", u, v) / np.maximum(np.linalg.norm(np.cross(u, v), axis=1), 1e-20)
        if clamp:
            cot = np.maximum(cot, 0.0)
        I += [F[:, b], F[:, c]]; J += [F[:, c], F[:, b]]; W += [cot / 2, cot / 2]
    Lm = sparse.coo_matrix((np.concatenate(W), (np.concatenate(I), np.concatenate(J))), shape=(n, n)).tocsr()
    Lm = Lm - sparse.diags(np.asarray(Lm.sum(1)).ravel())
    area = np.zeros(n); fa = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1) / 2
    for k in range(3):
        np.add.at(area, F[:, k], fa / 3)
    return Lm.tocsr(), area


def mean_curvature(V, F, N=None):
    """mean curvature per vertex (1/m for metres; a sphere of radius R reads 1/R) and the lumped vertex area"""
    Lm, area = cot_laplacian(V, F)
    N = vertex_normals(V, F) if N is None else N
    return -np.einsum("ij,ij->i", Lm @ V, N) / (2 * np.maximum(area, 1e-20)), area


def _safe(d):
    return np.where(np.abs(d) > 1e-30, d, 1e-30)


def closest_on_triangles(P, A, B, C, bary=False):
    """closest point of each P on its triangle (A, B, C); all (..., 3), broadcast. Ericson's Voronoi regions in his
    order (vertex A, vertex B, edge AB, vertex C, edge AC, edge BC, face): the first region that holds wins"""
    P, A, B, C = np.broadcast_arrays(*(np.asarray(x, float) for x in (P, A, B, C)))
    ab = B - A; ac = C - A; ap = P - A
    d1 = (ab * ap).sum(-1); d2 = (ac * ap).sum(-1)
    bp = P - B; d3 = (ab * bp).sum(-1); d4 = (ac * bp).sum(-1)
    cp = P - C; d5 = (ab * cp).sum(-1); d6 = (ac * cp).sum(-1)
    vc = d1 * d4 - d3 * d2; vb = d5 * d2 - d1 * d6; va = d3 * d6 - d5 * d4
    den = 1.0 / _safe(va + vb + vc); v = vb * den; w = vc * den
    X = A + v[..., None] * ab + w[..., None] * ac                             # inside the face
    wa, wb, wc = 1 - v - w, v, w
    t_bc = (d4 - d3) / _safe((d4 - d3) + (d5 - d6)); t_ac = d2 / _safe(d2 - d6); t_ab = d1 / _safe(d1 - d3)
    regions = [  # lowest priority first; a later region overwrites an earlier one
        ((va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0), B + t_bc[..., None] * (C - B), (0.0, 1 - t_bc, t_bc)),
        ((vb <= 0) & (d2 >= 0) & (d6 <= 0), A + t_ac[..., None] * ac, (1 - t_ac, 0.0, t_ac)),
        ((d6 >= 0) & (d5 <= d6), C, (0.0, 0.0, 1.0)),
        ((vc <= 0) & (d1 >= 0) & (d3 <= 0), A + t_ab[..., None] * ab, (1 - t_ab, t_ab, 0.0)),
        ((d3 >= 0) & (d4 <= d3), B, (0.0, 1.0, 0.0)),
        ((d1 <= 0) & (d2 <= 0), A, (1.0, 0.0, 0.0))]
    X = np.array(X, copy=True)
    if bary:
        wa = np.array(wa, float, copy=True); wb = np.array(wb, float, copy=True); wc = np.array(wc, float, copy=True)
    for m, Q, (ga, gb, gc) in regions:
        X[m] = Q[m]
        if bary:
            for arr, g in ((wa, ga), (wb, gb), (wc, gc)):
                arr[m] = g[m] if np.ndim(g) else g
    if bary:
        return X, np.stack([wa, wb, wc], -1)
    return X


def vertex_face_table(F, nv):
    """(nv, K) the faces round each vertex, -1 padded"""
    cnt = np.bincount(F.ravel(), minlength=nv); K = int(cnt.max()) if len(cnt) else 0
    order = np.argsort(F.ravel(), kind="stable"); st = np.r_[0, np.cumsum(cnt)]
    tab = -np.ones((nv, max(K, 1)), np.int64)
    pos = np.arange(len(order)) - np.repeat(st[:-1], cnt)
    tab[np.repeat(np.arange(nv), cnt), pos] = order // 3
    return tab


def closest_on_mesh(P, V, F, k=4):
    """closest point of each P on the triangles round its k nearest vertices of (V, F) (vectorised; on a regular mesh
    the closest triangle touches one of them). Returns (X, dist)"""
    from scipy.spatial import cKDTree
    P = np.asarray(P, float); V = np.asarray(V, float); F = np.asarray(F, np.int64)
    _, vi = cKDTree(V).query(P, k=k)
    vi = vi.reshape(len(P), -1)
    cand = vertex_face_table(F, len(V))[vi].reshape(len(P), -1)            # (m, k * K) candidate faces
    best = np.full(len(P), np.inf); X = np.zeros_like(P)
    for j in range(cand.shape[1]):
        f = cand[:, j]; ok = f >= 0
        if not ok.any():
            continue
        q = closest_on_triangles(P[ok], V[F[f[ok], 0]], V[F[f[ok], 1]], V[F[f[ok], 2]])
        d = np.linalg.norm(q - P[ok], axis=1)
        idx = np.nonzero(ok)[0]; better = d < best[idx]
        best[idx[better]] = d[better]; X[idx[better]] = q[better]
    return X, best


class MeshProj:
    """nearest points on a triangle mesh (exact on the k faces whose centroids are nearest); .n holds unit face normals"""

    def __init__(self, V, F, k=16):
        from scipy.spatial import cKDTree
        self.V, self.F, self.k = np.asarray(V, float), np.asarray(F, np.int64), k
        self.c = self.V[self.F].mean(1)
        self.n = face_normals(self.V, self.F)
        self.tree = cKDTree(self.c)

    def project(self, P):
        P = np.asarray(P, float)
        dd, ii = self.tree.query(P, k=self.k)
        best = np.full(len(P), np.inf); bp = np.zeros_like(P); bf = np.zeros(len(P), np.int64)
        for j in range(self.k):
            f = ii[:, j]
            X = closest_on_triangles(P, self.V[self.F[f, 0]], self.V[self.F[f, 1]], self.V[self.F[f, 2]])
            d = np.linalg.norm(X - P, axis=1)
            m = d < best
            best[m] = d[m]; bp[m] = X[m]; bf[m] = f[m]
        return bp, best, bf


def dihedral_edges(V, T):
    """every edge shared by two triangles and the angle between their unit normals (deg): a crease or fold reads directly
    (on fan-split quads each quad's own diagonal counts too)"""
    E = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]); fid = np.tile(np.arange(len(T)), 3)
    k = np.minimum(E[:, 0], E[:, 1]).astype(np.int64) * len(V) + np.maximum(E[:, 0], E[:, 1])
    o = np.argsort(k, kind="stable"); ks = k[o]; same = np.nonzero(ks[1:] == ks[:-1])[0]
    a, b = fid[o[same]], fid[o[same + 1]]; e = E[o[same]]
    n = face_normals(V, T)
    ang = np.degrees(np.arccos(np.clip((n[a] * n[b]).sum(1), -1, 1)))
    return e, ang


def poly_edges(sizes, flat):
    sizes = np.asarray(sizes); flat = np.asarray(flat)
    starts = np.r_[0, np.cumsum(sizes)[:-1]]
    nxt = np.arange(len(flat)) + 1
    nxt[starts + sizes - 1] = starts
    E = np.sort(np.c_[flat, flat[nxt]], axis=1)
    return np.unique(E, axis=0)


def quads_tris(sizes, flat):
    """fan triangles of a polygon mesh and, per triangle, its polygon"""
    sizes = np.asarray(sizes); flat = np.asarray(flat)
    starts = np.r_[0, np.cumsum(sizes)[:-1]]
    tris, owner = [], []
    for n in np.unique(sizes):
        sel = np.nonzero(sizes == n)[0]
        P = flat[starts[sel][:, None] + np.arange(n)[None]]
        for k in range(1, n - 1):
            tris.append(np.c_[P[:, 0], P[:, k], P[:, k + 1]]); owner.append(sel)
    return np.concatenate(tris).astype(np.int64), np.concatenate(owner)


def poly_dist(P, Q):
    """distance of each point P to the closed polyline Q"""
    A = Q; B = np.roll(Q, -1, 0); ab = B - A
    out = np.empty(len(P))
    for i0 in range(0, len(P), 128):
        X = P[i0:i0 + 128, None, :]
        t = np.clip(((X - A) * ab).sum(2) / np.maximum((ab * ab).sum(1), 1e-30), 0, 1)
        out[i0:i0 + 128] = np.linalg.norm(X - (A + t[..., None] * ab), axis=2).min(1)
    return out
