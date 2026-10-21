"""QUAD GRIDS: topology and layout for adding edge loops IN PLACE to a quad mesh, and harmonic / conformal layouts of a
region (build 13a's third builder, cases/woman2/build13/loops_lib.py; moved here in build A1, 2026-10-21, unchanged).

A modeller adds loops with a selection of the grid's faces, its boundary made round and inset: the selected faces are
KEPT (shrunk inside) and rings of new quads are added between them and their old boundary. Here:
  EdgeFaces(Q).faces(a, b)       the quads on an edge
  grid_coords(Q, seed, allow)    integer (i, j) per vertex by a walk over the allowed quads from `seed` (a regular patch:
                                 no extraordinary vertex inside; conflicts counted)
  rect_faces(Q, ij, has, i0, i1, j0, j1)  the quads of a grid rectangle (its largest connected piece)
  boundary_loop(Q, faces)        a face block's boundary, ordered as its faces run (asserts one simple loop)
  inset(Q, faces, K, nv)         K rings of new quads between a block and its old boundary -> (Q', rings, loop, nv')
  corner_index(Q, faces, loop)   where the block's boundary turns (convex corners, concave corners)
  ring_neighbours(Q, nv)         the quad edges' adjacency (sparse 0/1)
  harmonic(Q, verts, fixed_pos, nv)  a block's free vertices as the uniform-weight harmonic map of its fixed ones
  periodic_interp(th_q, th_t, y_t)   periodic interpolation in an angle
  mvc_uv(V, T, region_v, fixed_uv)   Floater mean-value parametrisation (bijective for a convex boundary)
  lscm_uv(V, T, region_v, pinned_uv) least-squares conformal map (Levy et al. 2002) with pinned vertices
  quad_tris(Q)                   two triangles per quad
  uv_charts(Q, faces, UVc)       connected UV charts of a face set (neighbours whose corner uvs agree)
  (build 13b, 2026-10-21: reading a whole quad mesh's own topology)
  HalfEdges(Q)                   directed edge a->b -> (face, corner); vertex neighbours; valence
  mirror_map(Q, V, x_mid)        the mesh's topological mirror (vertex i -> its mirror twin) by a face walk from a
                                 midline seed, the orientation reversed; vertices the walk could not match get -1 and
                                 every conflict (an asymmetric place) is counted
  grid_line(HE, a, b, max_n)     the edge loop through a -> b, walked straight on through valence-4 vertices (the edge
                                 sharing no face with the incoming one) until a pole, a boundary or its own start
Proof: engine/tools/test_quad_grid.py (planted grids; its json beside it).
"""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve


class EdgeFaces:
    def __init__(self, Q):
        Q = np.asarray(Q, np.int64)
        self.nv = int(Q.max()) + 1
        e = np.sort(np.stack([Q, np.roll(Q, -1, 1)], 2).reshape(-1, 2), 1)
        key = e[:, 0] * self.nv + e[:, 1]
        self.fid = np.repeat(np.arange(len(Q)), 4)
        self.o = np.argsort(key, kind="stable"); self.ks = key[self.o]

    def faces(self, a, b):
        k = int(min(a, b)) * self.nv + int(max(a, b))
        lo = np.searchsorted(self.ks, k); hi = np.searchsorted(self.ks, k, side="right")
        return self.fid[self.o[lo:hi]]


def grid_coords(Q, seed, allow):
    """(i, j) per vertex by a breadth-first walk over the allowed quads from `seed` (first assignment wins; conflicts
    counted: none inside a regular patch)"""
    Q = np.asarray(Q, np.int64)
    EF = EdgeFaces(Q)
    nv = EF.nv
    ij = np.zeros((nv, 2), np.int64); has = np.zeros(nv, bool)
    for v_, p in zip(Q[seed], [(0, 0), (1, 0), (1, 1), (0, 1)]):
        ij[v_] = p; has[v_] = True
    done = np.zeros(len(Q), bool); done[seed] = True
    queue = [seed]; conflicts = 0; qi = 0
    while qi < len(queue):
        f = queue[qi]; qi += 1; c = Q[f]
        for k in range(4):
            a, b = c[k], c[(k + 1) % 4]
            for g in EF.faces(a, b):
                if done[g] or not allow[g]:
                    continue
                d = list(Q[g]); ia = d.index(a); ib = d.index(b)
                if d[(ib + 1) % 4] == a:
                    p = d[(ia + 1) % 4]; q = d[(ib - 1) % 4]
                else:
                    p = d[(ia - 1) % 4]; q = d[(ib + 1) % 4]
                a_ = c[(k - 1) % 4]; b_ = c[(k + 2) % 4]
                pp = 2 * ij[a] - ij[a_]; qq = 2 * ij[b] - ij[b_]
                for v_, w in ((p, pp), (q, qq)):
                    if has[v_]:
                        conflicts += int((ij[v_] != w).any())
                    else:
                        ij[v_] = w; has[v_] = True
                done[g] = True; queue.append(g)
    return ij, has, done, conflicts


def rect_faces(Q, ij, has, i0, i1, j0, j1):
    """quads whose four corners are grid vertices of the unit square [i, i+1] x [j, j+1], i0 <= i < i1, j0 <= j < j1"""
    Q = np.asarray(Q, np.int64)
    ok = has[Q].all(1)
    c = ij[Q]
    lo = c.min(1); hi = c.max(1)
    unit = (hi - lo == 1).all(1)
    inr = (lo[:, 0] >= i0) & (lo[:, 0] < i1) & (lo[:, 1] >= j0) & (lo[:, 1] < j1)
    sel = np.nonzero(ok & unit & inr)[0]
    # the walk can give the same coordinates to quads elsewhere (past a pole, round the body): the largest piece
    from scipy.sparse.csgraph import connected_components
    F = Q[sel]
    a = F.ravel(); b = np.roll(F, -1, 1).ravel(); fid = np.repeat(np.arange(len(sel)), 4)
    key = np.minimum(a, b) * (Q.max() + 1) + np.maximum(a, b)
    o = np.argsort(key, kind="stable"); ks = key[o]
    same = np.nonzero(ks[1:] == ks[:-1])[0]
    G = sparse.coo_matrix((np.ones(len(same)), (fid[o[same]], fid[o[same + 1]])), shape=(len(sel),) * 2)
    nc, lab = connected_components(G, directed=False)
    return sel[lab == np.argmax(np.bincount(lab))]


def boundary_loop(Q, faces):
    """the block's boundary vertices in order (each directed edge a->b as its own face runs); asserts one simple loop"""
    Q = np.asarray(Q, np.int64)
    F = Q[faces]
    a = F.ravel(); b = np.roll(F, -1, 1).ravel()
    key = np.minimum(a, b) * (Q.max() + 1) + np.maximum(a, b)
    u, c = np.unique(key, return_counts=True)
    bnd = np.isin(key, u[c == 1])
    nxt = dict(zip(a[bnd].tolist(), b[bnd].tolist()))
    assert len(nxt) == bnd.sum(), "a boundary vertex with two outgoing edges (pinched block)"
    start = min(nxt)
    loop = [start]
    while True:
        n = nxt[loop[-1]]
        if n == start:
            break
        loop.append(n)
        assert len(loop) <= len(nxt)
    assert len(loop) == len(nxt), "more than one boundary loop"
    return np.array(loop, np.int64)


def inset(Q, faces, K, nv):
    """K rings of new quads between the block `faces` and its boundary. Returns (Q', rings, loop, nv'): rings[0] is the
    old boundary (its own vertices), rings[1..K] new vertex ids (rings[K] now bounds the block's faces)."""
    Q = np.asarray(Q, np.int64).copy()
    loop = boundary_loop(Q, faces)
    N = len(loop)
    rings = [loop]
    for k in range(K):
        rings.append(nv + np.arange(N)); nv += N
    new = []
    for k in range(K):
        A, B = rings[k], rings[k + 1]
        for j in range(N):
            j1 = (j + 1) % N
            new.append([A[j], A[j1], B[j1], B[j]])
    rep = -np.ones(nv, np.int64); rep[loop] = rings[K]
    F = Q[faces]
    m = rep[F] >= 0
    F[m] = rep[F][m]
    Q[faces] = F
    return np.vstack([Q, np.array(new, np.int64)]), rings, loop, nv


def corner_index(Q, faces, loop):
    """positions along the loop where the block's boundary turns (vertices of one block face only = convex corners)"""
    cnt = np.bincount(np.asarray(Q, np.int64)[faces].ravel(), minlength=int(np.max(Q)) + 1)
    return np.nonzero(cnt[loop] == 1)[0], np.nonzero(cnt[loop] == 3)[0]


def ring_neighbours(Q, nv):
    E = np.concatenate([Q[:, [0, 1]], Q[:, [1, 2]], Q[:, [2, 3]], Q[:, [3, 0]]])
    E = np.unique(np.sort(E, 1), axis=0)
    A = sparse.coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nv, nv)).tocsr()
    A.data[:] = 1.0
    return A


def harmonic(Q, verts, fixed_pos, nv):
    """positions (n, d) of `verts` (the block's vertices) with those in `fixed_pos` (dict id -> position) held: the
    uniform-weight harmonic map over the edges of the faces Q (only edges between the block's vertices count)"""
    verts = np.asarray(verts, np.int64)
    A = ring_neighbours(Q, nv)
    loc = -np.ones(nv, np.int64); loc[verts] = np.arange(len(verts))
    A = A[verts][:, verts]
    fid = np.array(list(fixed_pos.keys()), np.int64)
    fpos = np.array([fixed_pos[k] for k in fid.tolist()])
    isf = np.zeros(len(verts), bool); isf[loc[fid]] = True
    free = np.nonzero(~isf)[0]
    deg = np.asarray(A.sum(1)).ravel()
    Lm = sparse.diags(deg) - A
    X = np.zeros((len(verts), fpos.shape[1])); X[loc[fid]] = fpos
    if len(free):
        Lff = Lm[free][:, free].tocsc(); Lfc = Lm[free][:, np.nonzero(isf)[0]]
        rhs = -(Lfc @ X[isf])
        for d in range(X.shape[1]):
            X[free, d] = spsolve(Lff, rhs[:, d])
    return X


def periodic_interp(th_q, th_t, y_t):
    """interpolate a function sampled at angles th_t (any order) at angles th_q, periodic"""
    o = np.argsort(np.mod(th_t, 2 * np.pi)); t = np.mod(th_t, 2 * np.pi)[o]; y = np.asarray(y_t)[o]
    return np.interp(np.mod(th_q, 2 * np.pi), np.r_[t - 2 * np.pi, t, t + 2 * np.pi], np.r_[y, y, y])


def mvc_uv(V, T, region_v, fixed_uv):
    """Floater mean-value coordinates over the triangles T restricted to region_v; fixed_uv: dict vertex -> uv"""
    region_v = np.asarray(region_v, np.int64)
    loc = -np.ones(len(V), np.int64); loc[region_v] = np.arange(len(region_v))
    Tm = T[(loc[T] >= 0).all(1)]
    rows, cols, vals = [], [], []
    for k in range(3):
        i, j, l = Tm[:, k], Tm[:, (k + 1) % 3], Tm[:, (k + 2) % 3]
        a = V[j] - V[i]; b = V[l] - V[i]
        la = np.linalg.norm(a, axis=1); lb = np.linalg.norm(b, axis=1)
        cosang = np.clip((a * b).sum(1) / np.maximum(la * lb, 1e-30), -1, 1)
        t = np.tan(np.arccos(cosang) / 2)
        rows += [loc[i], loc[i]]; cols += [loc[j], loc[l]]; vals += [t / np.maximum(la, 1e-12), t / np.maximum(lb, 1e-12)]
    W = sparse.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(len(region_v),) * 2).tocsr()
    fid = np.array(list(fixed_uv.keys()), np.int64); fuv = np.array([fixed_uv[k] for k in fid.tolist()])
    isf = np.zeros(len(region_v), bool); isf[loc[fid]] = True
    Lm = sparse.diags(np.asarray(W.sum(1)).ravel()) - W
    U = np.zeros((len(region_v), 2)); U[loc[fid]] = fuv
    free = np.nonzero(~isf)[0]
    Lff = Lm[free][:, free].tocsc(); rhs = -(Lm[free][:, np.nonzero(isf)[0]] @ U[isf])
    for d in range(2):
        U[free, d] = spsolve(Lff, rhs[:, d])
    return U


def quad_tris(Q):
    Q = np.asarray(Q, np.int64)
    return np.concatenate([Q[:, [0, 1, 2]], Q[:, [0, 2, 3]]])


def lscm_uv(V, T, region_v, pinned_uv):
    """least-squares conformal map (Levy et al. 2002) over the triangles T restricted to region_v, the vertices in
    pinned_uv (dict vertex -> uv) held: a conformal extension of the pinned chart over the region"""
    region_v = np.asarray(region_v, np.int64)
    loc = -np.ones(len(V), np.int64); loc[region_v] = np.arange(len(region_v))
    Tm = T[(loc[T] >= 0).all(1)]
    n = len(region_v)
    p0, p1, p2 = V[Tm[:, 0]], V[Tm[:, 1]], V[Tm[:, 2]]
    e1 = p1 - p0; l1 = np.linalg.norm(e1, axis=1); x_ = e1 / np.maximum(l1, 1e-30)[:, None]
    nrm = np.cross(e1, p2 - p0); A2 = np.linalg.norm(nrm, axis=1)
    y_ = np.cross(nrm / np.maximum(A2, 1e-30)[:, None], x_)
    W = np.stack([np.zeros(len(Tm)) + 0j, l1 + 0j, ((p2 - p0) * x_).sum(1) + 1j * ((p2 - p0) * y_).sum(1)], 1)
    s = 1.0 / np.sqrt(np.maximum(A2, 1e-30))
    coef = np.stack([W[:, 2] - W[:, 1], W[:, 0] - W[:, 2], W[:, 1] - W[:, 0]], 1) * s[:, None]
    rows_r, rows_i, cols, a, b = [], [], [], [], []
    for k in range(3):
        rows_r.append(np.arange(len(Tm))); cols.append(loc[Tm[:, k]]); a.append(coef[:, k].real); b.append(coef[:, k].imag)
    rr = np.concatenate(rows_r); cc = np.concatenate(cols); aa = np.concatenate(a); bb = np.concatenate(b)
    m = len(Tm)
    # real rows: a u - b v ; imaginary rows: b u + a v   (unknowns [u (n), v (n)])
    R = np.r_[rr, rr, rr + m, rr + m]; C = np.r_[cc, cc + n, cc, cc + n]; D = np.r_[aa, -bb, bb, aa]
    A = sparse.coo_matrix((D, (R, C)), shape=(2 * m, 2 * n)).tocsc()
    pid = np.array(list(pinned_uv.keys()), np.int64); puv = np.array([pinned_uv[k] for k in pid.tolist()])
    isp = np.zeros(2 * n, bool); isp[loc[pid]] = True; isp[loc[pid] + n] = True
    x = np.zeros(2 * n); x[loc[pid]] = puv[:, 0]; x[loc[pid] + n] = puv[:, 1]
    Af = A[:, ~isp]; Ap = A[:, isp]
    rhs = -(Ap @ x[isp])
    x[~isp] = spsolve((Af.T @ Af).tocsc(), Af.T @ rhs)
    return np.c_[x[:n], x[n:]]


def uv_charts(Q, faces, UVc):
    """connected charts of a face set: neighbours across an edge whose two corner uvs agree on both ends"""
    from scipy.sparse.csgraph import connected_components
    Q = np.asarray(Q, np.int64); faces = np.asarray(faces)
    loc = {int(f): k for k, f in enumerate(faces)}
    edges = {}
    for k, f in enumerate(faces):
        for c in range(4):
            a, b = int(Q[f, c]), int(Q[f, (c + 1) % 4])
            edges.setdefault((min(a, b), max(a, b)), []).append((k, c, a, b))
    I, J = [], []
    for key, lst in edges.items():
        if len(lst) != 2:
            continue
        (k1, c1, a1, b1), (k2, c2, a2, b2) = lst
        f1, f2 = faces[k1], faces[k2]
        uv1 = {a1: UVc[f1, c1], b1: UVc[f1, (c1 + 1) % 4]}; uv2 = {a2: UVc[f2, c2], b2: UVc[f2, (c2 + 1) % 4]}
        if all(np.abs(uv1[v] - uv2[v]).max() < 1e-6 for v in key):
            I.append(k1); J.append(k2)
    G = sparse.coo_matrix((np.ones(len(I)), (I, J)), shape=(len(faces),) * 2)
    nc, lab = connected_components(G, directed=False)
    return nc, lab


class HalfEdges:
    """directed edges of a quad mesh: key a * nv + b -> (face, corner of a); each vertex's neighbours (sorted by id)"""
    def __init__(self, Q):
        Q = np.asarray(Q, np.int64)
        self.Q = Q; self.nv = int(Q.max()) + 1
        a = Q.ravel(); b = np.roll(Q, -1, 1).ravel()
        self.key = a * self.nv + b
        self.o = np.argsort(self.key, kind="stable"); self.ks = self.key[self.o]
        self.face = np.repeat(np.arange(len(Q)), 4); self.corner = np.tile(np.arange(4), len(Q))
        E = np.unique(np.sort(np.stack([a, b], 1), 1), axis=0)
        self.edges = E
        self.val = np.bincount(E.ravel(), minlength=self.nv)
        both = np.r_[E, E[:, ::-1]]; both = both[np.argsort(both[:, 0], kind="stable")]
        self.nb_start = np.r_[0, np.cumsum(np.bincount(both[:, 0], minlength=self.nv))]
        self.nb = both[:, 1]

    def find(self, a, b):
        """(face, corner) of the directed edge a -> b, or (-1, -1)"""
        k = int(a) * self.nv + int(b)
        i = np.searchsorted(self.ks, k)
        if i < len(self.ks) and self.ks[i] == k:
            j = self.o[i]
            return int(self.face[j]), int(self.corner[j])
        return -1, -1

    def neighbours(self, v):
        return self.nb[self.nb_start[v]:self.nb_start[v + 1]]


def mirror_map(Q, V, x_mid, seed_face=None, tol=0.004, init=None):
    """the topological mirror twin of every vertex (x -> 2 x_mid - x), found by walking the faces from a seed face near
    the midline whose mirror is a face: the face across each edge of a matched face is matched to the face across the
    twin edge, with the orientation reversed. The walk is best-first by the candidate pair's geometric mirror distance,
    and a candidate that contradicts an earlier match (a vertex given a second twin, a twin taken twice) is not taken
    and counted as a conflict, so an asymmetric place stops the walk there instead of shifting everything beyond it.
    Returns (mp, info): mp[i] = twin or -1; info counts faces matched, conflicts (a
    vertex matched to two twins: the topology is not symmetric there) and the largest geometric mirror distance of a
    matched pair (mm), which says how far the SHAPE departs from its mirror (not a topology test).
    init: a known map (n,) with -1 where unknown (e.g. from a symmetric parent mesh); the walk then starts from every
    face whose four vertices and their twins are known and only fills the rest. A shape far from its mirror (more
    than about half an edge) can shift the walk by a quad: walk a near-symmetric parent instead and pass it here."""
    Q = np.asarray(Q, np.int64); V = np.asarray(V, float)
    HE = HalfEdges(Q)
    cen = V[Q].mean(1)
    from scipy.spatial import cKDTree
    vtree = cKDTree(V)
    # the seed: a face whose nearest-mirror twins form a reversed face, inside a neighbourhood where that holds for
    # every face (a seed on an asymmetric spot, e.g. the face of a head, would shift the whole walk)
    seed = None
    if init is None:
        mv = V.copy(); mv[:, 0] = 2 * x_mid - mv[:, 0]
        dnn, nn = vtree.query(mv)
        tq = nn[Q]
        a_ = tq[:, 1] * HE.nv + tq[:, 0]
        pos = np.searchsorted(HE.ks, a_); pos = np.minimum(pos, len(HE.ks) - 1)
        hit = HE.ks[pos] == a_
        h_all = np.where(hit, HE.face[HE.o[pos]], -1)
        fok = hit & (dnn[Q].max(1) < tol)
        fok &= (np.sort(Q[np.maximum(h_all, 0)], 1) == np.sort(tq, 1)).all(1)
        ctree = cKDTree(cen)
        cand = np.nonzero(fok)[0] if seed_face is None else np.array([seed_face])
        rng = np.random.default_rng(0)
        cand = cand[rng.permutation(len(cand))[:400]] if seed_face is None else cand
        best = None
        for f in cand:
            nb = ctree.query_ball_point(cen[f], 0.03)
            sc = float(fok[nb].mean())
            if best is None or sc > best[0]:
                best = (sc, int(f))
            if sc == 1.0 and len(nb) > 50:
                break
        f = best[1]
        seed = (f, int(h_all[f]), nn[Q[f]])
    assert seed is not None or init is not None, "no seed face whose mirror is a face"
    mp = -np.ones(HE.nv, np.int64)
    conflicts = 0
    fmatch = -np.ones(len(Q), np.int64)
    import heapq
    taken = -np.ones(HE.nv, np.int64)                  # taken[w] = the vertex whose twin is w
    starts = []
    if init is not None:
        init = np.asarray(init, np.int64)
        mp[:len(init)] = init[:HE.nv]
        k_ = np.nonzero(mp >= 0)[0]; taken[mp[k_]] = k_
        full = (mp[Q] >= 0).all(1)
        for f in np.nonzero(full)[0]:
            tq = mp[Q[f]]
            h, _ = HE.find(int(tq[1]), int(tq[0]))
            if h >= 0 and set(Q[h].tolist()) == set(tq.tolist()):
                fmatch[f] = h; starts.append(int(f))
    else:
        seed_face, seed_twin, w = seed
        q = Q[seed_face]
        for k in range(4):
            mp[q[k]] = w[k]; taken[w[k]] = q[k]
        fmatch[seed_face] = seed_twin
        starts = [seed_face]
    mirror = lambda ids: np.c_[2 * x_mid - V[ids, 0], V[ids, 1:]]

    def push(heap, f):
        c = Q[f]
        for k in range(4):
            a, b = int(c[k]), int(c[(k + 1) % 4])
            g, _ = HE.find(b, a)
            if g < 0 or fmatch[g] >= 0:
                continue
            h, _ = HE.find(int(mp[a]), int(mp[b]))
            if h < 0:
                continue
            dg = Q[g].tolist(); dh = Q[h].tolist(); ig = dg.index(b); ih = dh.index(int(mp[b]))
            pair = [(dg[(ig + s_) % 4], dh[(ih - s_) % 4]) for s_ in range(4)]
            err = float(np.linalg.norm(V[[p_ for p_, _ in pair]] - mirror([q_ for _, q_ in pair]), axis=1).mean())
            heapq.heappush(heap, (err, g, h, pair))

    heap = []
    for f0 in starts:
        push(heap, f0)
    while heap:
        err, g, h, pair = heapq.heappop(heap)
        if fmatch[g] >= 0:
            continue
        okp = True
        for v, w_ in pair:
            if (mp[v] >= 0 and mp[v] != w_) or (mp[v] < 0 and taken[w_] >= 0 and taken[w_] != v):
                okp = False; break
        if not okp:
            conflicts += 1
            continue
        for v, w_ in pair:
            mp[v] = w_; taken[w_] = v
        fmatch[g] = h
        push(heap, g)
    ok = mp >= 0
    dm = np.full(HE.nv, np.nan)
    mv = V[mp[ok]].copy(); mv[:, 0] = 2 * x_mid - mv[:, 0]
    dm[ok] = np.linalg.norm(V[ok] - mv, axis=1)
    inv_ok = bool((mp[mp[ok]] == np.nonzero(ok)[0]).all())
    info = {"faces_matched": int((fmatch >= 0).sum()), "faces": int(len(Q)), "vertices_unmatched": int((~ok).sum()),
            "conflicts": int(conflicts), "involution": inv_ok,
            "mirror_distance_mm_p50_p99_max": [round(float(x) * 1e3, 3) for x in np.nanpercentile(dm, [50, 99, 100])]}
    return mp, info


def grid_line(HE, a, b, max_n=100000):
    """vertices of the edge loop through the directed edge a -> b, walked on straight through valence-4 vertices (at
    each, the edge that shares no face with the incoming one) until a pole, an open boundary or the start again.
    Returns (vertices, closed)."""
    line = [int(a), int(b)]
    while len(line) < max_n:
        p, v = line[-2], line[-1]
        if HE.val[v] != 4:
            return np.array(line, np.int64), False
        f1, _ = HE.find(p, v); f2, _ = HE.find(v, p)
        if f1 < 0 or f2 < 0:
            return np.array(line, np.int64), False
        used = set(HE.Q[f1].tolist()) | set(HE.Q[f2].tolist())
        nxt = [int(w) for w in HE.neighbours(v) if w != p and w not in used]
        if len(nxt) != 1:
            return np.array(line, np.int64), False
        w = nxt[0]
        if w == line[0]:
            return np.array(line, np.int64), True
        line.append(w)
    return np.array(line, np.int64), False
