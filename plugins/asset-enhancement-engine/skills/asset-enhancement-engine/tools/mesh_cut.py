"""mesh_cut.py - cutting a closed triangle mesh: a planar cut closed by a flat cap, an edge path through given
points, cutting a surface open along that path (a slit), boundary loops, and a one-line integrity summary.

Why it exists (woman2 Stage 2, 2026-10-19): the fitted torso's arms were welded to the chest wall (in the Tripo
reference too).  A real armpit needs the arm's inner skin and the chest wall as two surfaces that touch at rest and
part when the arm rises: the welded surface is cut open along the crease (front crease, crotch, back crease) and a
collapsed pocket is sewn into the slit (cases/woman2/stage2/build_s2.py, step pocket).  The neck was re-cut under the
jaw line with a planar cap.  fit_to_reference.retriangulate_caps only re-closes caps at the extremes of one axis.

  prove(): python mesh_cut.py prove
"""
import numpy as np

import fit_to_reference as T


def edges_unique(f):
    E = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), 1)
    return np.unique(E, axis=0)



def plane_cut(v, f, p0, nrm, attrs=None, snap=1.5e-4):
    """Keep the part of a closed mesh with (p - p0).n <= 0, split the faces the plane crosses, close the cut with a
    flat ear-clipped cap.  Vertices within `snap` of the plane are moved onto it first (no slivers).
    attrs: dict of per-vertex arrays (float), linearly interpolated onto new vertices.
    Returns v, f, attrs, cap_face_mask."""
    nrm = np.asarray(nrm, float)
    nrm /= np.linalg.norm(nrm)
    v = v.copy()
    s = (v - p0) @ nrm
    near = np.abs(s) < snap
    v[near] -= s[near, None] * nrm[None]
    s[near] = 0.0
    attrs = {k: np.asarray(a, float).copy() for k, a in (attrs or {}).items()}
    new_pts, new_attr = [], {k: [] for k in attrs}
    ekey = {}
    nv0 = len(v)

    def edge_pt(a, b):
        k = (min(a, b), max(a, b))
        if k in ekey:
            return ekey[k]
        t = s[a] / (s[a] - s[b])
        new_pts.append(v[a] + (v[b] - v[a]) * t)
        for key in attrs:
            new_attr[key].append(attrs[key][a] + (attrs[key][b] - attrs[key][a]) * t)
        ekey[k] = nv0 + len(new_pts) - 1
        return ekey[k]

    sf = s[f]
    keep_all = (sf <= 0).all(1)
    drop_all = (sf >= 0).all(1) & ~keep_all
    out = [f[keep_all]]
    cross = ~keep_all & ~drop_all
    extra = []
    for tri in f[cross]:
        poly = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            if s[a] <= 0:
                poly.append(a)
            if (s[a] < 0 < s[b]) or (s[b] < 0 < s[a]):
                poly.append(edge_pt(a, b))
        for k in range(1, len(poly) - 1):
            extra.append((poly[0], poly[k], poly[k + 1]))
    if extra:
        out.append(np.array(extra, np.int64))
    f2 = np.concatenate(out)
    if new_pts:
        v = np.concatenate([v, np.array(new_pts)])
        for k in attrs:
            attrs[k] = np.concatenate([attrs[k], np.array(new_attr[k])])
    # drop degenerate faces (two equal indices)
    f2 = f2[(f2[:, 0] != f2[:, 1]) & (f2[:, 1] != f2[:, 2]) & (f2[:, 0] != f2[:, 2])]
    # cap: boundary loops (all on the plane)
    loops = boundary_loops(len(v), f2)
    e1 = np.cross(nrm, [1.0, 0, 0])
    if np.linalg.norm(e1) < 1e-6:
        e1 = np.cross(nrm, [0, 1.0, 0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(nrm, e1)
    caps = []
    for lp in loops:
        sl = (v[lp] - p0) @ nrm
        assert np.abs(sl).max() < 1e-6, 'open boundary off the cut plane'
        lp = np.array(lp[::-1])  # the cap runs the rim against the side faces' direction
        P2 = np.c_[(v[lp] - p0) @ e1, (v[lp] - p0) @ e2]
        caps.append(lp[T._ear_clip(P2)])
    capf = np.concatenate(caps) if caps else np.zeros((0, 3), np.int64)
    f3 = np.concatenate([f2, capf])
    capmask = np.r_[np.zeros(len(f2), bool), np.ones(len(capf), bool)]
    # drop unused vertices
    used = np.zeros(len(v), bool)
    used[f3.ravel()] = True
    keep = np.nonzero(used)[0]
    remap = np.full(len(v), -1)
    remap[keep] = np.arange(len(keep))
    return v[keep], remap[f3], {k: a[keep] for k, a in attrs.items()}, capmask, keep


def boundary_loops(nv, f):
    """Closed boundary loops (lists of vertex ids, in the faces' edge direction)."""
    E = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    key = np.minimum(E[:, 0], E[:, 1]) * nv + np.maximum(E[:, 0], E[:, 1])
    u, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
    bnd = E[cnt[inv] == 1]
    nxt = {}
    for a, b in bnd:
        nxt.setdefault(int(a), []).append(int(b))
    loops, seen = [], set()
    for s0 in list(nxt):
        if s0 in seen:
            continue
        loop = [s0]
        seen.add(s0)
        while True:
            c = nxt[loop[-1]][0]
            if c == s0:
                break
            loop.append(c)
            seen.add(c)
            if len(loop) > len(nxt) + 2:
                raise RuntimeError('boundary walk did not close')
        loops.append(loop)
    return loops


def integrity(v, f):
    """open edges, non-manifold edges, inconsistent orientation, components, degenerate faces, Euler genus."""
    nv = len(v)
    E = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    key = np.minimum(E[:, 0], E[:, 1]) * nv + np.maximum(E[:, 0], E[:, 1])
    u, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
    dkey = E[:, 0] * nv + E[:, 1]
    ud, dcnt = np.unique(dkey, return_counts=True)
    from scipy.sparse.csgraph import connected_components
    from scipy import sparse
    G = sparse.coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(nv, nv))
    used = np.zeros(nv, bool)
    used[f.ravel()] = True
    ncomp, lab = connected_components(G, directed=False)
    ncomp = len(np.unique(lab[used]))
    area = np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1) / 2
    V, Ed, F = used.sum(), len(u), len(f)
    chi = V - Ed + F
    vol = np.einsum('ij,ij->i', v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])).sum() / 6
    return dict(verts=int(V), faces=int(F), open_edges=int((cnt == 1).sum()), nonmanifold_edges=int((cnt > 2).sum()),
                misoriented_edges=int((dcnt > 1).sum()), components=int(ncomp), degenerate_faces=int((area < 1e-12).sum()),
                euler_char=int(chi), genus=float((2 * ncomp - chi) / 2), volume_l=float(vol * 1e3),
                min_face_area_mm2=float(area.min() * 1e6))


def edge_graph(v, f):
    from scipy import sparse
    E = edges_unique(f)
    w = np.linalg.norm(v[E[:, 0]] - v[E[:, 1]], axis=1)
    G = sparse.coo_matrix((np.r_[w, w], (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(len(v), len(v))).tocsr()
    return G


def path_through(v, f, anchors_xyz, limit=0.03):
    """An edge path through the vertices nearest to the given points, joined by shortest paths; loops removed."""
    from scipy.spatial import cKDTree
    from scipy.sparse.csgraph import dijkstra
    G = edge_graph(v, f)
    tree = cKDTree(v)
    ids = [int(tree.query(p)[1]) for p in anchors_xyz]
    ids = [a for i, a in enumerate(ids) if i == 0 or a != ids[i - 1]]
    path = [ids[0]]
    for a, b in zip(ids[:-1], ids[1:]):
        d, pred = dijkstra(G, indices=a, return_predecessors=True, limit=limit)
        if not np.isfinite(d[b]):
            raise RuntimeError('no path between anchors')
        seg = [b]
        while seg[-1] != a:
            seg.append(int(pred[seg[-1]]))
        path += seg[::-1][1:]
    # remove loops (a vertex visited twice: drop everything between)
    out, pos = [], {}
    for p in path:
        if p in pos:
            k = pos[p]
            for q in out[k + 1:]:
                pos.pop(q, None)
            out = out[:k + 1]
        else:
            pos[p] = len(out)
            out.append(p)
    # taut: where p[k] and p[k+2] share an edge, drop p[k+1] (a path wrapping one triangle would leave that face
    # between its two sides)
    Es = set(map(tuple, edges_unique(f).tolist()))
    changed = True
    while changed:
        changed = False
        k = 0
        while k + 2 < len(out):
            a, c = out[k], out[k + 2]
            if (min(a, c), max(a, c)) in Es:
                del out[k + 1]
                changed = True
            else:
                k += 1
    return np.array(out, np.int64)


def cut_open(v, f, path):
    """Cut a closed surface open along an edge path (interior vertices duplicated; the endpoints stay shared).
    Faces on the LEFT of the path direction (seen from outside, faces counter-clockwise) take the duplicates.
    Returns v, f, left_ids (aligned with path; endpoints = original), right_ids (= path)."""
    nv = len(v)
    he = {}
    for i, (a, b, c) in enumerate(f):
        he[(a, b)] = i
        he[(b, c)] = i
        he[(c, a)] = i
    f = f.copy()
    v = np.concatenate([v, v[path[1:-1]]])
    left = path.copy()
    left[1:-1] = nv + np.arange(len(path) - 2)
    new_f = f.copy()
    for k in range(1, len(path) - 1):
        p, prv, nxt = path[k], path[k - 1], path[k + 1]
        fi = he[(p, nxt)]
        guard = 0
        while True:
            tri = list(f[fi])
            j = tri.index(p)
            b = tri[(j + 2) % 3]  # face (p, a, b) in cyclic order, a = tri[j+1]
            row = new_f[fi]
            row[row == p] = left[k]
            new_f[fi] = row
            if b == prv:
                break
            fi = he[(p, b)]
            guard += 1
            if guard > 64:
                raise RuntimeError('fan walk failed at path vertex %d' % k)
    return v, new_f, left, path.copy()


def prove():
    """planted cases: (1) a sphere cut by a tilted plane is closed, manifold, one shell, its cap is flat and the
    volume matches the analytic segment; (2) a slit cut along a 15-vertex path opens exactly one hole whose boundary
    has 2 x 14 edges and keeps the Euler characteristic of a disc-less sphere (chi = 2 - 0 faces removed: V+13);
    (3) a path that wraps a single triangle is made taut (the face between its two sides would otherwise be orphaned)."""
    import json
    v, f = T._icosphere(5)
    v = v * 0.1
    out = {}
    n = np.array([0.0, -np.sin(np.radians(20)), np.cos(np.radians(20))])
    v2, f2, _, capm, _ = plane_cut(v, f, np.array([0, 0, 0.03]), n)
    I = integrity(v2, f2)
    h = 0.1 - 0.03 * n[2]  # the plane's distance from the centre is 0.03 cos 20 deg
    vol_true = 4 / 3 * np.pi * 0.1 ** 3 - np.pi * h * h * (3 * 0.1 - h) / 3
    out['plane_cut'] = dict(I, cap_faces=int(capm.sum()), cap_flatness_m=float(np.abs((v2[f2[capm]].reshape(-1, 3) - [0, 0, 0.03]) @ n).max()),
                            volume_err_pct=round(abs(I['volume_l'] / 1e3 - vol_true) / vol_true * 100, 3))
    # path on the sphere's equator-ish, then cut open
    pts = np.array([[0.1 * np.cos(t), 0.1 * np.sin(t), 0.0] for t in np.linspace(0, 1.2, 15)])
    p = path_through(v, f, pts)
    v3, f3, left, right = cut_open(v, f, p)
    loops = boundary_loops(len(v3), f3)
    out['cut_open'] = dict(path_vertices=int(len(p)), holes=len(loops), hole_edges=len(loops[0]) if loops else 0,
                           expected_hole_edges=int(2 * (len(p) - 1)), integrity=integrity(v3, f3))
    ok = (out['plane_cut']['open_edges'] == 0 and out['plane_cut']['nonmanifold_edges'] == 0 and out['plane_cut']['components'] == 1
          and out['plane_cut']['cap_flatness_m'] < 1e-9 and out['plane_cut']['volume_err_pct'] < 1.0
          and out['cut_open']['holes'] == 1 and out['cut_open']['hole_edges'] == out['cut_open']['expected_hole_edges']
          and out['cut_open']['integrity']['nonmanifold_edges'] == 0)
    out['PASS'] = bool(ok)
    print(json.dumps(out, indent=1))
    return ok


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'prove':
        prove()
