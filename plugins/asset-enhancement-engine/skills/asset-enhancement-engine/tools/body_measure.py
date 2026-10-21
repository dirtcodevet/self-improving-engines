"""body_measure.py - anthropometric measurements of a closed human body mesh (a torso with its arms).

Why it exists (woman2 FINISH_SPEC F8, Stage 3, 2026-10-19).  The person wants the finished base torso stored with
"our completed base torso measurements/volume/dimensions, etc" so that a rebuild from scratch "would be that one",
and so the base can evolve by measured steps.  A stored mesh says what the torso IS; this tool says it in the terms
anatomy and anthropometry use (ANSUR II landmarks, levels, girths, breadths, depths), so a rebuild, a later version,
a generator's mesh or another case can be compared by numbers.  Nothing in the toolkit measured a body:
`checks/section_check.py` looks for creases, `fit_to_reference.py` compares surfaces.

Vocabulary (A9): this is the human pack's measuring tool.  Its landmark and girth names are the ANSUR II ones cited in
`engine/packs/human/anatomy_torso.json`.  Every setting (steps, chord windows, thresholds, search bands) is read by
named key from a definitions file kept in the pack (G14); a missing key stops the run.

Frame: x = subject LEFT, y = BACK (posterior), z = UP (the human pack's frame); metres in, millimetres out.  Positions
are reported in the frame whose ORIGIN is the suprasternale (jugular notch) found on the mesh, together with the
notch's own position in the mesh's coordinates.

What it measures (definitions in `measurements()`; each value carries its definition and the definition's source):
  - landmarks: suprasternale, thelion L/R, bust points L/R, inframammary folds L/R, omphalion, buttock point,
    the arm-separation (axilla) level per side, deltoid points;
  - horizontal sections every `section_step_mm`, the torso and each arm kept apart (by the arm bones' skin weights;
    a loop that holds both is split, the torso part closed by chords);
  - girths (tape = the perimeter of the section's convex hull: a tape bridges the cleavage and the spine furrow),
    breadths and depths at the bust, under-bust, narrowest waist, navel and buttock levels, and two neck levels;
  - arms: acromion-elbow, elbow-wrist and acromion-wrist lengths; girths perpendicular to the arm at the mid upper
    arm, the elbow, the forearm maximum and the wrist; each arm's volume;
  - volumes: the whole closed mesh, each arm and the torso without arms (the openings closed by a fan to each
    opening's centroid), each breast within its zone (between the skin and the membrane spanning the zone's rim);
  - zone geometry: areola and nipple diameters, nipple projection, areola rise, the nipple axis; plus a geometry-only
    relief profile around each nipple axis (usable on meshes without zones, e.g. a generator's); and, when the
    definitions carry nac.anatomical, the anatomical sizes in the nipple's own frame (projection above the areola's
    own surface, diameter at half and a tenth of the projection, the areola's pigment-edge diameter from the colour);
  - joint positions: the supplied joint centres and, when the rig file has them, every bone's head and tail, in the
    notch frame (added for the base torso v2, 2026-10-19).

What it cannot see: a bony landmark under the skin (acromion, radiale, iliac crest) unless joints are supplied; it
reports the acromion and the elbow and wrist joint centres from the supplied joints.  Tape girths assume the tape
lies in the horizontal (or the plane's) section; a real tape sags.  The notch is found on the sagittal profile at the
torso's mid x, not as a 2-D dimple.

Usage:
  python body_measure.py MESH(.ply|.npz) --defs DEFS.json [--zones Z.npz] [--weights W.npz] [--joints rig.json]
                         [--colour SHADING.npz] [--out measurements.json]
      MESH .npz holds v (N x 3, metres) and f (M x 3); zones .npz holds breast / areola / nipple weights per vertex;
      weights .npz holds W (N x B) and its column names as 'names' (every vertex group) or 'bones'; joints = a
      rig.json with joints.L/R acromion, gh, elbow, wrist (and optionally 'bones', reported as joint positions).
  python body_measure.py --prove --defs DEFS.json     (known-answer shapes, see prove())
"""
# ---- FUNCTION INDEX (engine/tools/func_index.py; grep 'def <name>' to jump) ----
#   read_ply(path)  - Binary little-endian PLY with float x,y,z (+ optional uchar colour) and triangle faces.
#   load_mesh(path)
#   mesh_sha1(v, f)
#   D(defs, *keys)  - A definition by named key (G14): a missing key stops the run, never a fallback literal.
#   face_normals(v, f, unit)
#   vertex_normals(v, f)
#   closed_volume(v, f)
#   plane_basis(n)  - (e1, e2) with e1 x e2 = n: horizontal planes give (x, y), sagittal planes (y, z).
#   plane_loops(v, f, p0, n, min_perimeter)  - Closed loops where the plane (p0, n) cuts the closed triangle mesh.  E...
#   poly_area(Q)
#   poly_perimeter(Q)
#   hull_perimeter(Q)  - A tape's girth: the perimeter of the convex hull (the tape bridges every concavity).
#   point_in_poly(pt, Q)
#   resample(Q, step)  - A closed 2-D polyline resampled at a uniform arc step (keeps its orientation).
#   chord_depth(R, k)  - Depth of each point of a counter-clockwise closed curve behind the chord between its neighbo...
#   edge_list(f)
#   face_components(f, mask)  - Connected components (sharing an edge) of the faces in mask: labels (-1 outside).
#   patch_volume(v, f, fmask)  - Volume of a surface patch closed over each of its openings by a fan to that opening'...
#   membrane_fill(v, f, region_faces)  - The membrane (uniform harmonic) surface spanning the rim of a face region, i...
#   class Body [point_class, horizontal, part_metrics, level_metrics, sagittal, front_dent, arm_faces, breast_volume,...
#   measurements(body, log)  - Every measurement of the body (see the module docstring).  Positions in mm in the notc...
#   prove(defs)  - Known answers (A10, once): (1) a tape girth bridges a planted concavity (the loop perimeter does n...
#   main(argv)
#   (+ 2 private helpers: grep '^def _')
# ---- END FUNCTION INDEX ----
import argparse
import hashlib
import json
import os
import sys

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve
from scipy.spatial import ConvexHull

MM = 1000.0  # unit conversion: metres -> millimetres
SIDES = ('L', 'R')
SIDE_SIGN = {'L': 1.0, 'R': -1.0}  # x = subject LEFT


import os as _os_mg, sys as _sys_mg  # noqa: E402  (build A1: the engine's one closest point, normals, cotangent Laplacian)
_MG_DIR = _os_mg.path.normpath(_os_mg.path.join(_os_mg.path.dirname(_os_mg.path.abspath(__file__)), '.'))
if _MG_DIR not in _sys_mg.path:
    _sys_mg.path.append(_MG_DIR)
import mesh_geom as _MG  # noqa: E402


# ------------------------------------------------------------------------------------------------------- io, defs
def read_ply(path):
    """Binary little-endian PLY with float x,y,z (+ optional uchar colour) and triangle faces."""
    b = open(path, 'rb').read()
    i = b.find(b'end_header') + len(b'end_header')
    while b[i:i + 1] in (b'\r', b'\n'):
        i += 1
    props, cur, nv, nf = [], None, 0, 0
    for L in b[:i].decode('ascii').split('\n'):
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
    return np.stack([V['x'], V['y'], V['z']], 1).astype(np.float64), Fr['i'].astype(np.int64)


def load_mesh(path):
    if path.lower().endswith('.ply'):
        return read_ply(path)
    d = np.load(path)
    return d['v'].astype(np.float64), d['f'].astype(np.int64)


def mesh_sha1(v, f):
    h = hashlib.sha1()
    h.update(np.ascontiguousarray(v, np.float32).tobytes())
    h.update(np.ascontiguousarray(f, np.int32).tobytes())
    return h.hexdigest()


def D(defs, *keys):
    """A definition by named key (G14): a missing key stops the run, never a fallback literal."""
    o = defs
    for k in keys:
        if not isinstance(o, dict) or k not in o:
            raise KeyError('measure_defs: missing key %s' % '.'.join(keys))
        o = o[k]
    return o['value'] if isinstance(o, dict) and 'value' in o else o


# ------------------------------------------------------------------------------------------------------- geometry
def face_normals(v, f, unit=True):
    n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    if unit:
        n = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-30)
    return n


def vertex_normals(v, f):
    n = _MG.vertex_normal_sums(v, f)
    return n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-30)


def closed_volume(v, f):
    return float(np.einsum('ij,ij->i', v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])).sum() / 6.0)


def plane_basis(n):
    """(e1, e2) with e1 x e2 = n: horizontal planes give (x, y), sagittal planes (y, z)."""
    n = np.asarray(n, float) / np.linalg.norm(n)
    if abs(n[2]) > 0.999:
        e1 = np.array([1.0, 0.0, 0.0])
    elif abs(n[0]) > 0.999:
        e1 = np.array([0.0, 1.0, 0.0])
    else:
        h = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        e1 = h - n * (h @ n)
        e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    return e1, e2


def plane_loops(v, f, p0, n, min_perimeter):
    """Closed loops where the plane (p0, n) cuts the closed triangle mesh.  Each loop is a dict with P (k x 3), the
    edge's vertex pair ia / ib and the parameter t (P = v[ia] + t (v[ib] - v[ia])), so per-vertex fields can be
    interpolated onto it; Q is P in the plane's basis (counter-clockwise about n).  A vertex exactly on the plane is
    moved off it by 1e-12 m.  Loops shorter than min_perimeter (metres) are dropped (grazing slivers)."""
    n = np.asarray(n, float) / np.linalg.norm(n)
    s = (v - np.asarray(p0, float)) @ n
    s = np.where(s == 0.0, 1e-12, s)
    sf = s[f]
    cross = (sf.min(1) < 0) & (sf.max(1) > 0)
    if not cross.any():
        return []
    F = f[cross]
    a = F
    b = F[:, [1, 2, 0]]
    m = (s[a] < 0) != (s[b] < 0)  # exactly two crossing edges per crossing face
    lo = np.minimum(a, b)[m].reshape(-1, 2)
    hi = np.maximum(a, b)[m].reshape(-1, 2)
    nv = len(v)
    key = lo.astype(np.int64) * nv + hi
    uk, inv = np.unique(key.ravel(), return_inverse=True)
    seg = inv.reshape(-1, 2)
    ia, ib = uk // nv, uk % nv
    t = s[ia] / (s[ia] - s[ib])
    P = v[ia] + (v[ib] - v[ia]) * t[:, None]
    npt = len(uk)
    src = np.r_[seg[:, 0], seg[:, 1]]
    dst = np.r_[seg[:, 1], seg[:, 0]]
    order = np.argsort(src, kind='stable')
    src, dst = src[order], dst[order]
    cnt = np.bincount(src, minlength=npt)
    if not (cnt == 2).all():
        raise ValueError('plane_loops: the mesh is not closed and manifold along this plane (%d points of degree != 2)'
                         % int((cnt != 2).sum()))
    nb = dst.reshape(npt, 2)
    seen = np.zeros(npt, bool)
    e1, e2 = plane_basis(n)
    loops = []
    for start in range(npt):
        if seen[start]:
            continue
        idx = [start]
        seen[start] = True
        prev, cur = -1, start
        while True:
            nxt = nb[cur, 0] if nb[cur, 0] != prev else nb[cur, 1]
            if nxt == start or seen[nxt]:
                break
            idx.append(nxt)
            seen[nxt] = True
            prev, cur = cur, nxt
        idx = np.array(idx)
        Pl = P[idx]
        if len(idx) < 3:
            continue
        per = np.linalg.norm(np.diff(np.vstack([Pl, Pl[:1]]), axis=0), axis=1).sum()
        if per < min_perimeter:
            continue
        Q = np.stack([Pl @ e1, Pl @ e2], 1)
        if poly_area(Q) < 0:
            idx = idx[::-1]
            Pl, Q = Pl[::-1], Q[::-1]
        loops.append(dict(P=Pl, Q=Q, ia=ia[idx], ib=ib[idx], t=t[idx]))
    return loops


def poly_area(Q):
    x, y = Q[:, 0], Q[:, 1]
    return 0.5 * float((x * np.roll(y, -1) - np.roll(x, -1) * y).sum())


def poly_perimeter(Q):
    return float(np.linalg.norm(np.diff(np.vstack([Q, Q[:1]]), axis=0), axis=1).sum())


def hull_perimeter(Q):
    """A tape's girth: the perimeter of the convex hull (the tape bridges every concavity)."""
    if len(Q) < 3:
        return 0.0
    H = Q[ConvexHull(Q).vertices]
    return poly_perimeter(H)


def point_in_poly(pt, Q):
    x, y = pt
    xa, ya = Q[:, 0], Q[:, 1]
    xb, yb = np.roll(xa, -1), np.roll(ya, -1)
    c = ((ya > y) != (yb > y)) & (x < (xb - xa) * (y - ya) / (yb - ya + 1e-300) + xa)
    return bool(c.sum() % 2)


def resample(Q, step):
    """A closed 2-D polyline resampled at a uniform arc step (keeps its orientation)."""
    C = np.vstack([Q, Q[:1]])
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
    n = max(int(s[-1] / step), 8)
    u = np.linspace(0, s[-1], n, endpoint=False)
    return np.stack([np.interp(u, s, C[:, 0]), np.interp(u, s, C[:, 1])], 1), s[-1] / n


def chord_depth(R, k):
    """Depth of each point of a counter-clockwise closed curve behind the chord between its neighbours k samples
    before and after (positive = toward the inside: a dent), and the chord's outward unit normal."""
    A = np.roll(R, k, 0)
    B = np.roll(R, -k, 0)
    c = B - A
    cl = np.linalg.norm(c, axis=1) + 1e-30
    d = (c[:, 0] * (R[:, 1] - A[:, 1]) - c[:, 1] * (R[:, 0] - A[:, 0])) / cl
    nout = np.stack([c[:, 1], -c[:, 0]], 1) / cl[:, None]
    return d, nout


def edge_list(f):
    E = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), 1)
    return np.unique(E, axis=0)


def face_components(f, mask):
    """Connected components (sharing an edge) of the faces in mask: labels (-1 outside)."""
    idx = np.nonzero(mask)[0]
    lab = np.full(len(f), -1)
    if len(idx) == 0:
        return lab, 0
    F = f[idx]
    E = np.concatenate([np.sort(F[:, [0, 1]], 1), np.sort(F[:, [1, 2]], 1), np.sort(F[:, [2, 0]], 1)])
    fid = np.tile(np.arange(len(idx)), 3)
    key = E[:, 0] * (f.max() + 1) + E[:, 1]
    o = np.argsort(key, kind='stable')
    k2, f2 = key[o], fid[o]
    same = k2[1:] == k2[:-1]
    a, b = f2[:-1][same], f2[1:][same]
    G = sparse.coo_matrix((np.ones(len(a)), (a, b)), shape=(len(idx), len(idx)))
    nc, l = connected_components(G, directed=False)
    lab[idx] = l
    return lab, nc


def patch_volume(v, f, fmask):
    """Volume of a surface patch closed over each of its openings by a fan to that opening's centroid:
    (1/6) [sum over patch faces det(p0, p1, p2) + sum over boundary edges a->b of det(p_b, p_a, c_loop)].
    Returns (volume m^3, number of openings, the openings' centroids)."""
    F = f[fmask]
    if len(F) == 0:
        return 0.0, 0, []
    vol = np.einsum('ij,ij->i', v[F[:, 0]], np.cross(v[F[:, 1]], v[F[:, 2]])).sum()
    De = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    nv = len(v)
    fw = De[:, 0] * nv + De[:, 1]
    bw = De[:, 1] * nv + De[:, 0]
    bnd = De[~np.isin(fw, bw)]
    if len(bnd) == 0:
        return float(vol / 6.0), 0, []
    u, inv = np.unique(bnd.ravel(), return_inverse=True)
    e = inv.reshape(-1, 2)
    G = sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(len(u), len(u)))
    nc, lab = connected_components(G, directed=False)
    cents = []
    for c in range(nc):
        ee = bnd[lab[e[:, 0]] == c]
        mid = (v[ee[:, 0]] + v[ee[:, 1]]) / 2
        L = np.linalg.norm(v[ee[:, 1]] - v[ee[:, 0]], axis=1)
        cc = (mid * L[:, None]).sum(0) / L.sum()
        cents.append(cc)
        vol += np.einsum('ij,ij->i', v[ee[:, 1]], np.cross(v[ee[:, 0]], np.broadcast_to(cc, (len(ee), 3)))).sum()
    return float(vol / 6.0), int(nc), cents


def membrane_fill(v, f, region_faces):
    """The membrane (uniform harmonic) surface spanning the rim of a face region, interior vertices solved with the
    rim fixed.  Returns the filled vertex array (only the region's interior vertices change)."""
    F = f[region_faces]
    De = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    nv = len(v)
    fw = De[:, 0] * nv + De[:, 1]
    bw = De[:, 1] * nv + De[:, 0]
    rim = np.unique(De[~np.isin(fw, bw)].ravel())
    used = np.unique(F.ravel())
    inner = np.setdiff1d(used, rim)
    E = np.unique(np.sort(De, 1), axis=0)
    A = sparse.coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])),
                          shape=(nv, nv)).tocsr()
    A.data[:] = 1.0
    deg = np.asarray(A.sum(1)).ravel()
    L = (sparse.diags(deg) - A).tocsr()
    out = v.copy()
    if len(inner):
        Lii = L[inner][:, inner].tocsc()
        rhs = -(L[inner][:, rim] @ v[rim])
        for k in range(3):
            out[inner, k] = spsolve(Lii, rhs[:, k])
    return out, rim, inner


# ------------------------------------------------------------------------------------------------------- the body
class Body:
    """A closed mesh plus its optional per-vertex arm weights (L, R), zones and joints."""

    def __init__(self, v, f, defs, zones=None, weights=None, joints=None, bones=None, colour=None):
        self.v = np.asarray(v, np.float64)
        self.f = np.asarray(f, np.int64)
        self.defs = defs
        self.zones = zones
        self.joints = joints
        self.bones = bones  # optional: rig.json 'bones' (head, tail, parent per bone), reported in the notch frame
        self.colour = None if colour is None else np.asarray(colour, np.float64)[:, :3]  # optional: linear RGB per vertex
        self.arm = None
        if weights is not None:
            W, wn = weights
            wn = [str(b) for b in wn]
            ab = D(defs, 'arm_bones')
            self.arm = {s: sum(W[:, wn.index(b)].astype(np.float64) for b in ab[s]) for s in SIDES}
        self.thr = D(defs, 'label_weight_min')
        self.minper = D(defs, 'min_loop_perimeter_mm') / MM
        self.zmin, self.zmax = float(self.v[:, 2].min()), float(self.v[:, 2].max())
        self.x_mid = None

    # ---------------------------------------------------------------------------- sections
    def point_class(self, L):
        """0 torso, 1 arm L, 2 arm R per loop point (by the arm weights, interpolated along the cut edge)."""
        cls = np.zeros(len(L['t']), int)
        if self.arm is None:
            return cls
        for c, s in ((1, 'L'), (2, 'R')):
            w = self.arm[s]
            wp = (1 - L['t']) * w[L['ia']] + L['t'] * w[L['ib']]
            cls[wp >= self.thr] = c
        return cls

    def horizontal(self, z):
        """The level z (mesh metres) split into torso / arm_L / arm_R parts.
        Loops nested inside another loop (sections of an internal cavity, e.g. a collapsed armpit pocket above its
        openings) are left out.  Each outer loop takes its majority class (by the arm weights).  An arm that has a
        loop of its own at this level is SEPARATE: its points elsewhere (e.g. a pocket wall with high arm weight) stay
        with the loop they are on.  An arm with no loop of its own is JOINED to the loop holding its points: that loop
        is split by point class and each part closed by chords.  Without arm weights the largest loop is the torso and
        the others are arms by side."""
        loops = plane_loops(self.v, self.f, (0.0, 0.0, z), (0.0, 0.0, 1.0), self.minper)
        parts = {'torso': [], 'arm_L': [], 'arm_R': []}
        if not loops:
            return parts, 0, 0, {'L': False, 'R': False}
        areas = [abs(poly_area(L['Q'])) for L in loops]
        nested = [any(j != i and areas[j] > areas[i] and point_in_poly(L['Q'][0], loops[j]['Q'])
                      for j in range(len(loops))) for i, L in enumerate(loops)]
        outer = [L for L, n_ in zip(loops, nested) if not n_]
        oa = [abs(poly_area(L['Q'])) for L in outer]
        names = ('torso', 'arm_L', 'arm_R')
        cls_l, maj = [], []
        for i, L in enumerate(outer):
            if self.arm is None:
                xm = self.x_mid if self.x_mid is not None else 0.0
                c = 0 if i == int(np.argmax(oa)) else (1 if L['P'][:, 0].mean() > xm else 2)
                cls = np.full(len(L['t']), c)
            else:
                cls = self.point_class(L)
            cls_l.append(cls)
            maj.append(int(np.argmax(np.bincount(cls, minlength=3))))
        own = {'L': 1 in maj, 'R': 2 in maj}
        joined = 0
        for L, cls, m in zip(outer, cls_l, maj):
            if m != 0:
                parts[names[m]].append(dict(Q=L['Q'], whole=True))
                continue
            split = [c for c, s in ((1, 'L'), (2, 'R')) if not own[s] and (cls == c).sum() >= 3]
            if not split:
                parts['torso'].append(dict(Q=L['Q'], whole=True))
                continue
            joined += 1
            keep = np.ones(len(cls), bool)
            for c in split:
                parts[names[c]].append(dict(Q=L['Q'][cls == c], whole=False))
                keep &= cls != c
            parts['torso'].append(dict(Q=L['Q'][keep], whole=False))
        return parts, joined, len(outer), own

    @staticmethod
    def part_metrics(polys):
        if not polys:
            return None
        Q = np.vstack([p['Q'] for p in polys])
        area = sum(abs(poly_area(p['Q'])) for p in polys)
        return dict(girth_tape_mm=hull_perimeter(Q) * MM, breadth_mm=float(np.ptp(Q[:, 0])) * MM,
                    depth_mm=float(np.ptp(Q[:, 1])) * MM, area_cm2=area * 1e4,
                    x_min=float(Q[:, 0].min()), x_max=float(Q[:, 0].max()),
                    y_min=float(Q[:, 1].min()), y_max=float(Q[:, 1].max()),
                    loops=len(polys), whole=all(p['whole'] for p in polys))

    def level_metrics(self, z):
        parts, joined, nloops, own = self.horizontal(z)
        out = {k: self.part_metrics(p) for k, p in parts.items()}
        out['joined_loops'] = joined
        out['loops'] = nloops
        out['arm_own_loop'] = own
        return out

    def sagittal(self, x):
        """The largest loop of the sagittal plane at x, resampled counter-clockwise in (y, z)."""
        loops = plane_loops(self.v, self.f, (x, 0.0, 0.0), (1.0, 0.0, 0.0), self.minper)
        if not loops:
            raise ValueError('no sagittal section at x = %.4f' % x)
        L = loops[int(np.argmax([abs(poly_area(L['Q'])) for L in loops]))]
        R, ds = resample(L['Q'], D(self.defs, 'resample_mm') / MM)
        return R, ds

    def front_dent(self, x, z_lo, z_hi, half_mm):
        """The deepest front concavity of the sagittal profile at x with z in [z_lo, z_hi]: (y, z, depth, R, i, d)."""
        R, ds = self.sagittal(x)
        k = max(1, int(round(half_mm / MM / ds)))
        d, nout = chord_depth(R, k)
        front = nout[:, 0] < D(self.defs, 'front_chord_normal_y_max')
        cand = front & (R[:, 1] >= z_lo) & (R[:, 1] <= z_hi)
        if not cand.any():
            raise ValueError('no front concavity in z [%.4f, %.4f] at x %.4f' % (z_lo, z_hi, x))
        i = int(np.nonzero(cand)[0][np.argmax(d[cand])])
        return R[i, 0], R[i, 1], float(d[i]), R, i, d

    # ---------------------------------------------------------------------------- volumes
    def arm_faces(self, side):
        fw = self.arm[side][self.f].mean(1) >= self.thr
        lab, nc = face_components(self.f, fw)
        if nc > 1:
            big = np.argmax(np.bincount(lab[lab >= 0]))
            fw = lab == big
        # torso faces cut off from the main torso by the arm region (islands inside it) belong to the arm
        lab2, nc2 = face_components(self.f, ~fw)
        if nc2 > 1:
            big2 = np.argmax(np.bincount(lab2[lab2 >= 0]))
            fw = fw | ((lab2 >= 0) & (lab2 != big2))
        return fw

    def breast_volume(self, side, wmin, bust_vertex):
        w = self.zones['breast'].astype(np.float64)
        sidem = (self.v[:, 0] - self.x_mid) * SIDE_SIGN[side] > 0
        fm = (w[self.f] > wmin).all(1) & sidem[self.f].all(1)
        lab, nc = face_components(self.f, fm)
        # the piece holding the bust point
        touching = np.nonzero((self.f == bust_vertex).any(1) & fm)[0]
        if len(touching) == 0:
            raise ValueError('bust point not inside the breast footprint (%s)' % side)
        fm = lab == lab[touching[0]]
        base, rim, inner = membrane_fill(self.v, self.f, fm)
        F = self.f[fm]
        vs = np.einsum('ij,ij->i', self.v[F[:, 0]], np.cross(self.v[F[:, 1]], self.v[F[:, 2]])).sum()
        vb = np.einsum('ij,ij->i', base[F[:, 0]], np.cross(base[F[:, 1]], base[F[:, 2]])).sum()
        area = np.linalg.norm(np.cross(self.v[F[:, 1]] - self.v[F[:, 0]], self.v[F[:, 2]] - self.v[F[:, 0]]), axis=1).sum() / 2
        h = np.linalg.norm(self.v[inner] - base[inner], axis=1) if len(inner) else np.zeros(1)
        ext = np.ptp(self.v[np.unique(F.ravel())], 0)
        return dict(volume_ml=float((vs - vb) / 6.0) * 1e6, footprint_area_cm2=float(area) * 1e4,
                    max_height_above_base_mm=float(h.max()) * MM, footprint_extent_mm=(ext * MM).tolist(),
                    footprint_faces=int(fm.sum()))

    # ---------------------------------------------------------------------------- zones
    def nac(self, side):
        z = self.zones
        thr = D(self.defs, 'nac', 'zone_weight_min')
        sidem = (self.v[:, 0] - self.x_mid) * SIDE_SIGN[side] > 0
        fa = (z['areola'][self.f].mean(1) >= thr) & sidem[self.f].all(1)
        fnp = (z['nipple'][self.f].mean(1) >= thr) & sidem[self.f].all(1)
        fn = face_normals(self.v, self.f, unit=False)
        ar = np.linalg.norm(fn, axis=1) / 2
        axis = fn[fa].sum(0)
        axis /= np.linalg.norm(axis)
        cen = (self.v[self.f[fa]].mean(1) * ar[fa, None]).sum(0) / ar[fa].sum()
        nv_ = np.unique(self.f[fnp].ravel())
        tip = nv_[np.argmax((self.v[nv_] - cen) @ axis)]
        e1 = np.array([0.0, 0.0, 1.0]) - axis * axis[2]
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(axis, e1)
        rel = self.v - cen
        U, W_, H = rel @ e1, rel @ e2, rel @ axis
        proj = lambda m: float((fn[m] @ axis).sum() / 2)  # projected area along the axis
        A_surf, A_proj = float(ar[fa].sum()), proj(fa)
        N_surf, N_proj = float(ar[fnp].sum()), proj(fnp)
        r_a, r_n = np.sqrt(A_proj / np.pi), np.sqrt(N_proj / np.pi)
        tipc = self.v[tip] - cen
        # tip's own radial frame: radii about the line through the TIP along the axis
        ut, wt = tipc @ e1, tipc @ e2
        r = np.hypot(U - ut, W_ - wt)
        vn = vertex_normals(self.v, self.f)
        facing = (vn @ axis > D(self.defs, 'nac', 'relief_facing_min')) & (np.abs(H) < D(self.defs, 'nac', 'relief_depth_mm') / MM)
        # nipple projection above the plane of the areola just outside the nipple
        fac = D(self.defs, 'nac', 'nipple_annulus_factor')
        ann = facing & (r >= r_n) & (r <= fac * r_n) & (z['nipple'] < thr) & sidem
        X = np.c_[np.ones(ann.sum()), U[ann], W_[ann]]
        cpl, *_ = np.linalg.lstsq(X, H[ann], rcond=None)
        proj_tip = float(H[tip] - (cpl[0] + cpl[1] * ut + cpl[2] * wt))
        # areola rise above the breast's continuation (quadric on the ring just outside the areola)
        r0, r1 = D(self.defs, 'nac', 'continuation_ring_areola_radii')
        ring = facing & (r >= r0 * r_a) & (r <= r1 * r_a) & sidem
        q = lambda u, w: np.c_[np.ones(len(u)), u, w, u * u, u * w, w * w]
        cq, *_ = np.linalg.lstsq(q(U[ring], W_[ring]), H[ring], rcond=None)
        hrel = H - q(U, W_) @ cq
        base_ring = facing & (r >= r_n) & (r <= r_n + D(self.defs, 'nac', 'base_ring_mm') / MM) & (z['nipple'] < thr) & sidem
        are_ann = facing & (z['areola'] >= thr) & (z['nipple'] < thr) & sidem
        lat = np.degrees(np.arctan2(axis[0] * SIDE_SIGN[side], -axis[1]))
        up = np.degrees(np.arcsin(axis[2]))
        anat = None
        if 'anatomical' in self.defs['nac']:  # the anatomical sizes block (v2 definitions); absent in v1's
            anat = self.nac_anatomical(axis, tip, r_a, r_n, sidem, vn, fn)
        return dict(anatomical=anat,
            areola_d_eq_surface_mm=2 * np.sqrt(A_surf / np.pi) * MM, areola_d_eq_projected_mm=2 * r_a * MM,
            nipple_d_eq_surface_mm=2 * np.sqrt(N_surf / np.pi) * MM, nipple_d_eq_projected_mm=2 * r_n * MM,
            nipple_projection_above_areola_mm=proj_tip * MM,
            areola_rise_at_nipple_base_mm=float(np.median(hrel[base_ring])) * MM,
            areola_rise_mean_mm=float(np.mean(hrel[are_ann])) * MM,
            tip_above_breast_continuation_mm=float(hrel[tip]) * MM,
            axis=axis.tolist(), axis_lateral_deg=float(lat), axis_up_deg=float(up),
            centre_mesh_m=cen.tolist(), tip_vertex=int(tip), tip_mesh_m=self.v[tip].tolist())

    def nac_anatomical(self, axis, tip, r_a, r_n, sidem, vn, fn):
        """Anatomical nipple-areola sizes in the nipple's own frame (J14), not the zones' soft extents.  The frame is
        the line through the nipple tip along the nipple axis.  The areola's own surface around the nipple (an annulus
        outside the papilla's foot, inside the areolar mound's flat top) gets a fitted quadric, its continuation under
        the nipple (a plane would add the breast's curvature: +0.86 mm on woman2); heights are measured above it.
        Nipple projection = the tip's height above that surface; nipple diameter at a fraction of the
        projection = twice the median distance from the axis of the skin at that height (its circumference's mean,
        the close-up's 'half-height width' at 0.5).  Areola diameter (pigment) = the equivalent diameter of the
        projected area whose colour is at least the threshold of the way from the skin ring to the areola body
        (one colour channel; needs the per-vertex colour)."""
        A = lambda *k: D(self.defs, 'nac', 'anatomical', *k)
        v = self.v
        rel = v - v[tip]
        h = rel @ axis
        rho = np.linalg.norm(rel - np.outer(h, axis), axis=1)
        e1 = np.array([0.0, 0.0, 1.0]) - axis * axis[2]
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(axis, e1)
        U, Wc = rel @ e1, rel @ e2
        near = sidem & (np.abs(h) < A('depth_mm') / MM) & (rho < A('search_areola_radii') * r_a)
        a0, a1 = A('surface_annulus')
        ann = near & (rho >= a0 * r_n) & (rho <= a1 * r_a)
        q = lambda u, w: np.c_[np.ones(len(u)), u, w, u * u, u * w, w * w]
        c, *_ = np.linalg.lstsq(q(U[ann], Wc[ann]), h[ann], rcond=None)
        Hp = h - q(U, Wc) @ c  # height above the areola's own surface continued under the nipple (a quadric)
        P = float(Hp[tip])
        band = A('height_band_mm') / MM
        pap = near & (rho < A('papilla_search_nipple_radii') * r_n)
        out = dict(nipple_projection_mm=P * MM, surface_fit_annulus_mm=[a0 * r_n * MM, a1 * r_a * MM],
                   surface_fit_rms_mm=float(np.sqrt(np.mean((Hp[ann]) ** 2))) * MM, surface_fit_vertices=int(ann.sum()))
        for fr in A('fractions'):
            sel = pap & (np.abs(Hp - fr * P) < band)
            out['nipple_diameter_at_%g_projection_mm' % fr] = float(2 * np.median(rho[sel])) * MM if sel.any() else None
            out['nipple_diameter_at_%g_projection_vertices' % fr] = int(sel.sum())
        dh = out.get('nipple_diameter_at_0.5_projection_mm')
        out['projection_over_half_height_width'] = P * MM / dh if dh else None
        if self.colour is not None:
            g = self.colour[:, A('pigment_channel')]
            facing = vn @ axis > 0
            b0, b1 = A('pigment_body_areola_radii')
            s0, s1 = A('pigment_skin_ring_areola_radii')
            body = near & facing & (rho >= b0 * r_a) & (rho <= b1 * r_a)
            ring = near & facing & (rho >= s0 * r_a) & (rho <= s1 * r_a)
            gb, gs = float(np.median(g[body])), float(np.median(g[ring]))
            s = (gs - g) / (gs - gb)
            varea = np.zeros(len(v))
            for k in range(3):
                np.add.at(varea, self.f[:, k], np.abs(fn @ axis) / 6.0)  # projected area along the axis (fn = 2 x area)
            inside = near & facing & (rho < s0 * r_a) & (s >= A('pigment_threshold'))
            Ap = float(varea[inside].sum())
            da = 2 * np.sqrt(Ap / np.pi) * MM
            out.update(areola_diameter_pigment_mm=da, pigment_body_value=gb, pigment_skin_ring_value=gs,
                       nipple_over_areola=(dh / da) if dh else None)
        return out

    def relief(self, centre, axis, side=None):
        """Geometry-only relief around a nipple axis: the skin's height above a quadric fitted on a ring around the
        axis (the breast's continuation), as a radial profile about the relief's own peak.  Works without zones."""
        axis = np.asarray(axis, float) / np.linalg.norm(axis)
        e1 = np.array([0.0, 0.0, 1.0]) - axis * axis[2]
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(axis, e1)
        vn = vertex_normals(self.v, self.f)
        fn = face_normals(self.v, self.f, unit=False)
        varea = np.zeros(len(self.v))
        for k in range(3):
            np.add.at(varea, self.f[:, k], np.abs(fn @ axis) / 6.0)
        R0, R1 = (np.array(D(self.defs, 'nac', 'relief_ring_mm')) / MM)
        depth = D(self.defs, 'nac', 'relief_depth_mm') / MM
        facing_min = D(self.defs, 'nac', 'relief_facing_min')
        q = lambda u, w: np.c_[np.ones(len(u)), u, w, u * u, u * w, w * w]
        c = np.asarray(centre, float)
        for it in range(2):  # pass 1 finds the relief's own peak; pass 2 is centred on it
            rel = self.v - c
            U, W_, H = rel @ e1, rel @ e2, rel @ axis
            r = np.hypot(U, W_)
            ok = (vn @ axis > facing_min) & (np.abs(H) < depth)
            ring = ok & (r >= R0) & (r <= R1)
            cq, *_ = np.linalg.lstsq(q(U[ring], W_[ring]), H[ring], rcond=None)
            h = H - q(U, W_) @ cq
            inside = ok & (r < R0)
            ip = np.nonzero(inside)[0][np.argmax(h[inside])]
            if it == 0:
                c = c + e1 * U[ip] + e2 * W_[ip]
        bins = D(self.defs, 'nac', 'relief_bin_mm') / MM
        edges = np.arange(0, R0 + bins / 2, bins)
        prof = []
        for a, b in zip(edges[:-1], edges[1:]):
            k = inside & (r >= a) & (r < b)
            prof.append(float(np.median(h[k])) * MM if k.any() else None)
        peak = float(h[ip])
        out = dict(peak_mm=peak * MM, profile_bin_mm=bins * MM, profile_mm=[None if p is None else round(p, 3) for p in prof],
                   peak_mesh_m=self.v[ip].tolist(),
                   relief_volume_ml=float((np.clip(h[inside], 0, None) * varea[inside]).sum()) * 1e6)
        mids = (edges[:-1] + edges[1:]) / 2
        pv = np.array([np.nan if p is None else p for p in prof])
        for fr in D(self.defs, 'nac', 'relief_fractions'):
            lvl = fr * peak * MM
            below = np.nonzero(pv < lvl)[0]
            out['diameter_at_%g_peak_mm' % fr] = float(2 * mids[below[0]] * MM) if len(below) else None
        return out

    # ---------------------------------------------------------------------------- arms
    def arm_plane_girth(self, point, normal):
        loops = plane_loops(self.v, self.f, point, normal, self.minper)
        if not loops:
            return None
        e1, e2 = plane_basis(normal)
        p2 = (np.asarray(point) @ e1, np.asarray(point) @ e2)
        hit = [L for L in loops if point_in_poly(p2, L['Q'])]
        if not hit:
            return None
        L = min(hit, key=lambda L: abs(poly_area(L['Q'])))
        return dict(girth_tape_mm=hull_perimeter(L['Q']) * MM, perimeter_mm=poly_perimeter(L['Q']) * MM,
                    area_cm2=abs(poly_area(L['Q'])) * 1e4)


# ------------------------------------------------------------------------------------------------------- measuring
def _r(x, nd=4, key=''):
    """Rounding for the record: 4 decimals (0.0001 mm, mL, cm2); 7 for values in metres (keys ending in _m)."""
    k_nd = 7 if key.endswith('_m') else nd
    if isinstance(x, dict):
        return {k: _r(v, nd, k) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_r(v, nd, key) for v in x]
    if isinstance(x, (float, np.floating)):
        return round(float(x), k_nd)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def measurements(body, log=print):
    """Every measurement of the body (see the module docstring).  Positions in mm in the notch frame."""
    v, f, defs = body.v, body.f, body.defs
    out = dict(tool='engine/tools/body_measure.py', mesh=dict(sha1=mesh_sha1(v, f), verts=len(v), faces=len(f)))
    step = D(defs, 'section_step_mm') / MM
    sstep = D(defs, 'search_step_mm') / MM

    # ---- mid x: the torso's own centre over the levels where it is one whole loop
    zs = np.arange(body.zmin + step, body.zmax, step)
    mids = []
    for z in zs:
        parts, joined, _, _ = body.horizontal(z)
        m = Body.part_metrics(parts['torso'])
        if m and m['whole'] and m['loops'] == 1:
            mids.append((m['x_min'] + m['x_max']) / 2)
    body.x_mid = float(np.median(mids))
    log('x_mid %.2f mm over %d levels' % (body.x_mid * MM, len(mids)))

    # ---- suprasternale
    if body.joints is not None:
        zac = np.mean([body.joints[s]['acromion'][2] for s in SIDES])
        lo, hi = np.array(D(defs, 'notch', 'band_about_acromion_mm')) / MM
        band = (zac + lo, zac + hi)
        band_src = 'joints: acromion height %+.1f mm, band [%g, %g] mm about it' % (zac * MM, lo * MM, hi * MM)
    else:
        band = (body.zmax - D(defs, 'notch', 'band_below_top_mm') / MM, body.zmax)
        band_src = 'no joints: the top %g mm of the mesh' % D(defs, 'notch', 'band_below_top_mm')
    ny, nz, nd, _, _, _ = body.front_dent(body.x_mid, band[0], band[1], D(defs, 'notch', 'chord_half_mm'))
    notch = np.array([body.x_mid, ny, nz])
    P = lambda p: ((np.asarray(p) - notch) * MM).tolist()  # mesh metres -> notch frame mm
    out['frame'] = dict(axes=D(defs, 'frame', 'axes'), origin=D(defs, 'frame', 'origin'),
                        origin_in_mesh_m=notch.tolist(), units='mm (positions relative to the origin), cm2, mL, L',
                        x_mid_mesh_m=body.x_mid,
                        x_mid_def='median x-centre of the torso section over the levels where the torso is one whole loop')
    LM = {}
    LM['suprasternale'] = dict(mm=P(notch), mesh_m=notch.tolist(), chord_depth_mm=nd * MM,
                               definition='deepest front concavity (chord depth, +-%g mm along the profile) of the sagittal profile at the torso mid x, searched %s' % (D(defs, 'notch', 'chord_half_mm'), band_src),
                               definition_source='ANSUR II handbook: inferior point of the jugular notch (anatomy_torso.json landmark_definitions.suprasternale); the search rule is the engine\'s')

    has_z = body.zones is not None
    bust_v = {}
    if has_z:
        out['zones'] = {}
        for s in SIDES:
            nz_ = body.nac(s)
            out['zones'][s] = nz_
            tipp = np.array(nz_['tip_mesh_m'])
            LM['thelion_' + s] = dict(mm=P(tipp), mesh_m=tipp.tolist(),
                                      definition='the nipple zone vertex furthest along the nipple axis (the areola zone\'s area-weighted mean normal)',
                                      definition_source='ANSUR II handbook: centre (tip) of the nipple')
            sidem = (v[:, 0] - body.x_mid) * SIDE_SIGN[s] > 0
            bz = np.nonzero((body.zones['breast'] >= body.thr) & sidem)[0]
            bv = bz[np.argmin(v[bz, 1])]
            bust_v[s] = int(bv)
            LM['bust_point_' + s] = dict(mm=P(v[bv]), mesh_m=v[bv].tolist(),
                                         definition='the most anterior (min y) point of the breast zone (weight >= %g)' % body.thr,
                                         definition_source='ANSUR II handbook: chest point anterior, for women the bust point')
        # inframammary folds: the crease below each breast on the sagittal profile through the thelion
        lo, hi = np.array(D(defs, 'imf', 'search_below_thelion_mm')) / MM
        for s in SIDES:
            t = np.array(LM['thelion_' + s]['mesh_m'])
            iy, iz, idp, _, _, _ = body.front_dent(t[0], t[2] - hi, t[2] - lo, D(defs, 'imf', 'chord_half_mm'))
            p = np.array([t[0], iy, iz])
            LM['inframammary_fold_' + s] = dict(mm=P(p), mesh_m=p.tolist(), chord_depth_mm=idp * MM,
                                                definition='deepest front concavity (chord +-%g mm) of the sagittal profile through the thelion, %g-%g mm below it' % (D(defs, 'imf', 'chord_half_mm'), lo * MM, hi * MM),
                                                definition_source='anatomy: the lower crease of the breast against the chest wall (anatomy_torso.json landmark_definitions.inframammary_fold); the search rule is the engine\'s')
    # omphalion
    lo, hi = np.array(D(defs, 'navel', 'band_below_notch_mm')) / MM
    _, _, _, R, i, d = body.front_dent(body.x_mid, nz - hi, nz - lo, D(defs, 'navel', 'chord_half_mm'))
    frac = D(defs, 'navel', 'pit_fraction')
    j0 = j1 = i
    n_ = len(R)
    while d[(j0 - 1) % n_] >= frac * d[i]:
        j0 -= 1
    while d[(j1 + 1) % n_] >= frac * d[i]:
        j1 += 1
    jc = ((j0 + j1) // 2) % n_
    om = np.array([body.x_mid, R[jc, 0], R[jc, 1]])
    LM['omphalion'] = dict(mm=P(om), mesh_m=om.tolist(), pit_depth_mm=float(d[i]) * MM,
                           pit_deepest_mm=P([body.x_mid, R[i, 0], R[i, 1]]),
                           opening_z_span_mm=float(R[j0 % n_, 1] - R[j1 % n_, 1]) * MM,
                           definition='the middle of the front-profile stretch deeper than %g of the navel pit\'s maximum chord depth (chord +-%g mm), searched %g-%g mm below the notch' % (frac, D(defs, 'navel', 'chord_half_mm'), lo * MM, hi * MM),
                           definition_source='ANSUR II handbook: centre of the navel (omphalion); the search rule is the engine\'s')

    # ---- levels
    levels = {}
    girths = {}

    def at(name, z, definition, src, extra=None):
        m = body.level_metrics(z)
        e = dict(z_mm=(z - nz) * MM, definition=definition, definition_source=src)
        if m['torso']:
            e.update({k: m['torso'][k] for k in ('girth_tape_mm', 'breadth_mm', 'depth_mm', 'area_cm2', 'loops', 'whole')})
            e['front_y_mm'] = (m['torso']['y_min'] - notch[1]) * MM
            e['back_y_mm'] = (m['torso']['y_max'] - notch[1]) * MM
        e['joined_loops'] = m['joined_loops']
        if extra:
            e.update(extra)
        girths[name] = e
        levels[name] = e['z_mm']
        return m

    if has_z:
        zb = np.mean([LM['bust_point_' + s]['mesh_m'][2] for s in SIDES])
        at('bust', zb, 'horizontal tape girth (convex hull), breadth and depth of the torso at the mean height of the two bust points',
           'ANSUR II handbook: chest circumference, breadth and depth at the bust point level (anatomy_torso.json chest_point_anterior)')
        zt = np.mean([LM['thelion_' + s]['mesh_m'][2] for s in SIDES])
        at('bust_thelion', zt, 'horizontal tape girth, breadth and depth of the torso at the mean height of the two nipple tips',
           'engine definition (the common nude-body bust girth over the nipples); the ANSUR level is the bust point (above)')
        zu = np.mean([LM['inframammary_fold_' + s]['mesh_m'][2] for s in SIDES])
        at('under_bust', zu, 'horizontal tape girth, breadth and depth of the torso at the mean height of the two inframammary folds',
           'engine definition (the pack\'s ANSUR set has no under-bust measure)')
    else:
        zu = nz - 0.15
    zom = om[2]
    at('waist_navel', zom, 'horizontal tape girth, breadth and depth of the torso at the omphalion',
       'ANSUR II handbook: waist circumference / breadth / depth (omphalion)')
    # narrowest waist
    zz = np.arange(zu - sstep, zom, -sstep)
    gs = []
    for z in zz:
        m = Body.part_metrics(body.horizontal(z)[0]['torso'])
        gs.append(m['girth_tape_mm'] if m else np.inf)
    zw = zz[int(np.argmin(gs))]
    at('waist_narrowest', zw, 'the level of least horizontal torso tape girth between the under-bust and the navel (searched every %g mm)' % (sstep * MM),
       'engine definition of the natural waist (least girth between the ribs and the pelvis)')
    # buttock point
    zz = np.arange(zom - D(defs, 'buttock', 'search_below_navel_mm') / MM, body.zmin, -sstep)
    yb, xb = [], []
    for z in zz:
        m = Body.part_metrics(body.horizontal(z)[0]['torso'])
        yb.append(m['y_max'] if m else -np.inf)
        xb.append(m['breadth_mm'] if m else 0.0)
    ib = int(np.argmax(yb))
    zbt = zz[ib]
    at_edge = (zbt - body.zmin) * MM <= D(defs, 'buttock', 'edge_flag_mm') + sstep * MM
    at('buttock', zbt, 'the level of greatest posterior torso protrusion below the navel (searched every %g mm); tape girth, breadth (hip breadth at this level) and depth there' % (sstep * MM),
       'ANSUR II handbook: buttock point; buttock circumference and depth, hip breadth at that level (anatomy_torso.json hip_breadth)',
       extra=dict(at_mesh_bottom=bool(at_edge)))
    ihx = int(np.argmax(xb))
    girths['hip_breadth_max'] = dict(z_mm=(zz[ihx] - nz) * MM, breadth_mm=float(xb[ihx]),
                                     definition='the greatest horizontal torso breadth below %g mm under the navel' % D(defs, 'buttock', 'search_below_navel_mm'),
                                     definition_source='ANSUR II: hip breadth (maximum); engine search')
    for h in D(defs, 'neck_levels_above_notch_mm'):
        at('neck_plus%d' % h, nz + h / MM, 'horizontal tape girth, breadth and depth of the neck %g mm above the notch' % h, 'engine definition')

    # ---- armpits: the highest level at which each arm is its own loop; bideltoid above it
    ax = {}
    if body.arm is not None:
        zz = np.arange(nz + 0.03, nz - 0.25, -sstep)
        sep = {s: None for s in SIDES}
        for z in zz:
            own = body.horizontal(z)[3]
            for s in SIDES:
                if sep[s] is None and own[s]:
                    sep[s] = z
            if all(sep[s] is not None for s in SIDES):
                break
        for s in SIDES:
            ax[s] = sep[s]
            LM['arm_separation_' + s] = dict(z_mm=None if sep[s] is None else (sep[s] - nz) * MM,
                                             definition='the highest horizontal level (searched every %g mm from 30 mm above the notch down) at which the arm is an outer loop of its own, apart from the torso: where the armpit hollow opens through the section (front and back)' % (sstep * MM),
                                             definition_source='engine definition (the axilla vault as the sections see it)')
        if body.joints is not None:
            # deltoid point: the greatest lateral protrusion of the arm from its own axis (shoulder joint -> elbow),
            # between the acromion and the deltoid's insertion (taken at the acromion-elbow midpoint); hanging arms
            # that flare outward are wider lower down, so the raw maximum breadth would land on the forearm
            dl = {}
            for s in SIDES:
                j = {k: np.array(body.joints[s][k], float) for k in ('acromion', 'gh', 'elbow')}
                zt_, zb_ = j['acromion'][2], (j['acromion'][2] + j['elbow'][2]) / 2
                best = (-np.inf, None, None)
                for z in np.arange(zt_, zb_, -sstep):
                    pa = Body.part_metrics(body.horizontal(z)[0]['arm_' + s])
                    if pa is None:
                        continue
                    lat = pa['x_max'] if s == 'L' else -pa['x_min']
                    tt = (z - j['gh'][2]) / (j['elbow'][2] - j['gh'][2])
                    axx = (j['gh'] + tt * (j['elbow'] - j['gh']))[0] * SIDE_SIGN[s]
                    if lat - axx > best[0]:
                        best = (lat - axx, z, lat * SIDE_SIGN[s])
                dl[s] = best
                LM['deltoid_point_' + s] = dict(z_mm=(best[1] - nz) * MM, x_mm=(best[2] - notch[0]) * MM,
                                                protrusion_from_arm_axis_mm=best[0] * MM,
                                                definition='the greatest lateral protrusion of the arm section from the upper arm axis (shoulder joint to elbow), searched every %g mm from the acromion to the acromion-elbow midpoint' % (sstep * MM),
                                                definition_source='ANSUR II: deltoid point / bideltoid breadth (the lateral margins of the deltoids); the axis-relative search is the engine rule')
            girths['bideltoid'] = dict(breadth_mm=(dl['L'][2] - dl['R'][2]) * MM,
                                       z_L_mm=(dl['L'][1] - nz) * MM, z_R_mm=(dl['R'][1] - nz) * MM,
                                       definition='horizontal distance between the left and right deltoid points',
                                       definition_source='ANSUR II: bideltoid breadth')

    out['landmarks'] = LM
    out['levels_z_mm'] = levels
    out['girths'] = girths

    # ---- lengths (scale-carrying, vertical where named so)
    lengths = dict(notch_to_navel_vertical_mm=float(nz - om[2]) * MM)
    if has_z:
        tL, tR = (np.array(LM['thelion_' + s]['mesh_m']) for s in SIDES)
        lengths.update(internipple_mm=float(np.linalg.norm(tL - tR)) * MM,
                       notch_to_thelion_L_straight_mm=float(np.linalg.norm(tL - notch)) * MM,
                       notch_to_thelion_R_straight_mm=float(np.linalg.norm(tR - notch)) * MM,
                       notch_to_bust_level_vertical_mm=float(nz - zb) * MM,
                       thelion_to_imf_L_vertical_mm=float(tL[2] - LM['inframammary_fold_L']['mesh_m'][2]) * MM,
                       thelion_to_imf_R_vertical_mm=float(tR[2] - LM['inframammary_fold_R']['mesh_m'][2]) * MM)
    out['lengths'] = lengths

    # ---- arms
    if body.joints is not None:
        arms = {}
        for s in SIDES:
            j = {k: np.array(body.joints[s][k], float) for k in ('acromion', 'gh', 'elbow', 'wrist')}
            ua = (j['elbow'] - j['gh']) / np.linalg.norm(j['elbow'] - j['gh'])
            fa = (j['wrist'] - j['elbow']) / np.linalg.norm(j['wrist'] - j['elbow'])
            a = dict(acromion_to_elbow_mm=float(np.linalg.norm(j['elbow'] - j['acromion'])) * MM,
                     acromion_to_elbow_vertical_mm=float(j['acromion'][2] - j['elbow'][2]) * MM,
                     elbow_to_wrist_mm=float(np.linalg.norm(j['wrist'] - j['elbow'])) * MM,
                     acromion_to_wrist_mm=float(np.linalg.norm(j['wrist'] - j['acromion'])) * MM,
                     joints_mm={k: P(p) for k, p in j.items()},
                     lengths_definition='straight distances between the supplied joint points (acromion; elbow and wrist joint centres); acromion to elbow approximates ANSUR acromion-radiale length',
                     mid_upper_arm=body.arm_plane_girth((j['acromion'] + j['elbow']) / 2, ua),
                     elbow=body.arm_plane_girth(j['elbow'], ua + fa),
                     wrist=body.arm_plane_girth(j['wrist'], fa))
            L_ = np.linalg.norm(j['wrist'] - j['elbow'])
            mg = D(defs, 'arm', 'forearm_scan_margin_mm') / MM
            best = None
            for tt in np.arange(mg, L_ - mg, D(defs, 'arm', 'forearm_scan_step_mm') / MM):
                g = body.arm_plane_girth(j['elbow'] + fa * tt, fa)
                if g and (best is None or g['girth_tape_mm'] > best['girth_tape_mm']):
                    best = dict(g, from_elbow_mm=float(tt) * MM)
            if best is not None:
                best['at_scan_start'] = bool(best['from_elbow_mm'] <= mg * MM + 1e-6)
            a['forearm_max'] = best
            a['girths_definition'] = ('tape (convex hull) girths in planes perpendicular to the arm: the upper arm axis '
                                      '(shoulder joint to elbow) at the midpoint of acromion and elbow; the bisector at '
                                      'the elbow; the forearm axis at its maximum (scanned every %g mm, %g mm off each '
                                      'joint) and at the wrist joint' % (D(defs, 'arm', 'forearm_scan_step_mm'), mg * MM))
            a['girths_definition_source'] = ('NHANES mid upper arm circumference (midpoint acromion-olecranon; here the '
                                             'elbow joint centre); ANSUR II wrist and forearm circumferences; engine planes')
            arms[s] = a
        out['arms'] = arms

    # ---- joint positions: every supplied joint centre and bone, in the notch frame
    if body.joints is not None:
        jo = {s: {k: P(p) for k, p in body.joints[s].items() if isinstance(p, (list, tuple)) and len(p) == 3}
              for s in SIDES}
        jo['definition'] = ('the rig\'s joint centres (rig.json joints: acromion, glenohumeral centre gh, elbow and '
                            'wrist joint centres, acromioclavicular ac and sternoclavicular sc points), in the notch frame')
        if body.bones is not None:
            jo['bones'] = {b: dict(head=P(d['head']), tail=P(d['tail']), parent=d.get('parent'))
                           for b, d in body.bones.items()}
            jo['bones_definition'] = 'every rig bone\'s head and tail (rig.json bones), in the notch frame'
        out['joints'] = jo

    # ---- volumes
    vol = dict(whole_l=closed_volume(v, f) * 1e3, whole_definition='signed volume of the closed mesh (torso, neck and arms)')
    if body.arm is not None:
        tf = np.ones(len(f), bool)
        for s in SIDES:
            fm = body.arm_faces(s)
            tf &= ~fm
            va, nop, cents = patch_volume(v, f, fm)
            vol['arm_%s_l' % s] = va * 1e3
            vol['arm_%s_openings' % s] = nop
        vt, nop, _ = patch_volume(v, f, tf)
        vol['torso_without_arms_l'] = vt * 1e3
        vol['closure_check_l'] = vol['whole_l'] - vol['torso_without_arms_l'] - vol['arm_L_l'] - vol['arm_R_l']
        vol['arm_definition'] = ('the faces whose arm-bone weight (%s) averages >= %g, one connected piece; its opening '
                                 'at the shoulder closed by a fan to the opening\'s centroid; the torso is the rest, '
                                 'closed by the same fans' % (D(defs, 'arm_bones'), body.thr))
    if has_z:
        for s in SIDES:
            b0 = body.breast_volume(s, D(defs, 'breast', 'footprint_weight_min'), bust_v[s])
            b1 = body.breast_volume(s, D(defs, 'breast', 'sensitivity_weight_min'), bust_v[s])
            vol['breast_%s' % s] = dict(b0, volume_ml_at_half_weight_footprint=b1['volume_ml'])
        vol['breast_definition'] = ('the volume between the skin over the breast zone (weight > %g, the piece holding the '
                                    'bust point) and the membrane (uniform harmonic surface) spanning that footprint\'s '
                                    'rim; also given for the half-weight footprint' % D(defs, 'breast', 'footprint_weight_min'))
    out['volumes'] = vol

    # ---- sections every step (torso and arms apart)
    z0 = np.ceil((body.zmin - nz) / step) * step + nz
    zs = np.arange(z0, body.zmax, step)
    sec = dict(z_mm=[], torso=[], arm_L=[], arm_R=[], joined_loops=[], loops=[], arm_own_loop=[])
    keys = ('girth_tape_mm', 'breadth_mm', 'depth_mm', 'area_cm2', 'x_min', 'x_max', 'y_min', 'y_max', 'loops', 'whole')
    for z in zs:
        m = body.level_metrics(z)
        sec['z_mm'].append((z - nz) * MM)
        for part in ('torso', 'arm_L', 'arm_R'):
            e = m[part]
            if e is None:
                sec[part].append(None)
            else:
                e = {k: e[k] for k in keys}
                for k in ('x_min', 'x_max'):
                    e[k] = (e[k] - notch[0]) * MM
                for k in ('y_min', 'y_max'):
                    e[k] = (e[k] - notch[1]) * MM
                sec[part].append(e)
        sec['joined_loops'].append(m['joined_loops'])
        sec['loops'].append(m['loops'])
        sec['arm_own_loop'].append(m['arm_own_loop'])
    sec['definition'] = ('horizontal sections every %g mm in the notch frame; each loop point classed torso / arm by the '
                         'arm-bone weights (>= %g); a loop holding both is split and each part closed by chords; '
                         'girth = tape (convex hull) perimeter; x/y extents in the notch frame' % (step * MM, body.thr))
    out['sections'] = sec
    if has_z:
        for s in SIDES:
            zz_ = out['zones'][s]
            zz_['centre_mm'] = P(zz_.pop('centre_mesh_m'))
            zz_['tip_mm'] = P(zz_.pop('tip_mesh_m'))
            rl = body.relief(np.array(LM['thelion_' + s]['mesh_m']), zz_['axis'])
            rl['peak_mm_pos'] = P(rl.pop('peak_mesh_m'))
            zz_['relief'] = rl
        out['zones']['definitions'] = dict(
            membership='areola and nipple regions: faces whose zone weight averages >= %g' % D(defs, 'nac', 'zone_weight_min'),
            diameters='equivalent diameters 2 sqrt(A / pi): A the region\'s surface area, or its area projected along the nipple axis',
            axis='the areola region\'s area-weighted mean normal; lateral angle from straight forward, up angle from horizontal',
            nipple_projection='tip height along the axis above the plane fitted to the areola from the nipple base radius to %g times it' % D(defs, 'nac', 'nipple_annulus_factor'),
            areola_rise='height above the quadric fitted to the breast on the ring %s areola radii out (the breast\'s continuation): median in the first %g mm outside the nipple base, and the mean over the areola' % (D(defs, 'nac', 'continuation_ring_areola_radii'), D(defs, 'nac', 'base_ring_mm')),
            relief='geometry only (no zones): height above a quadric fitted on the ring %s mm around the axis, re-centred on its own peak; radial profile by %g mm bins; diameters where the profile falls below %s of the peak; relief volume = the positive relief integrated over the projected area inside the ring' % (D(defs, 'nac', 'relief_ring_mm'), D(defs, 'nac', 'relief_bin_mm'), D(defs, 'nac', 'relief_fractions')),
            source='engine definitions; ANSUR has no areola or nipple measures')
        if 'anatomical' in defs['nac']:
            out['zones']['definitions']['anatomical'] = (
                'the anatomical sizes, in the nipple\'s own frame (the line through the tip along the axis): a quadric '
                'fitted to the areola\'s own surface on the annulus from %g x the nipple zone radius to %g x the '
                'areola zone radius, its continuation under the nipple; nipple projection = the tip\'s height above '
                'it; nipple diameter at a fraction %s '
                'of the projection = twice the median distance from the axis of the skin within %g mm of that height '
                '(0.5: the half-height width); areola diameter (pigment) = equivalent diameter of the projected area '
                'whose colour channel %d lies at least %g of the way from the skin ring (%s areola zone radii) to the '
                'areola body (%s); the zone-based diameters above measure the zones\' soft extents instead (the areola '
                'zone runs to 1.05 R, the nipple zone past the papilla\'s foot)' % (
                    D(defs, 'nac', 'anatomical', 'surface_annulus')[0], D(defs, 'nac', 'anatomical', 'surface_annulus')[1],
                    D(defs, 'nac', 'anatomical', 'fractions'), D(defs, 'nac', 'anatomical', 'height_band_mm'),
                    D(defs, 'nac', 'anatomical', 'pigment_channel'), D(defs, 'nac', 'anatomical', 'pigment_threshold'),
                    D(defs, 'nac', 'anatomical', 'pigment_skin_ring_areola_radii'),
                    D(defs, 'nac', 'anatomical', 'pigment_body_areola_radii')))
    return _r(out)


# ------------------------------------------------------------------------------------------------------- proof
def _tube(a_fn, b_fn, z0, z1, nz, nth, dent=None):
    """A closed tube of elliptical sections (x semi-axis a(z), y semi-axis b(z)) with flat caps;
    dent(x, y, z) -> inward offset (metres) along -radial for planted features."""
    zs = np.linspace(z0, z1, nz)
    th = np.linspace(0, 2 * np.pi, nth, endpoint=False)
    V = []
    for z in zs:
        a, b = a_fn(z), b_fn(z)
        x, y = a * np.cos(th), b * np.sin(th)
        if dent is not None:
            r = np.hypot(x, y)
            d = dent(x, y, z)
            x, y = x * (1 - d / r), y * (1 - d / r)
        V.append(np.stack([x, y, np.full(nth, z)], 1))
    V = np.vstack(V + [[[0, 0, z0]], [[0, 0, z1]]])
    F = []
    for i in range(nz - 1):
        for j in range(nth):
            a_, b_ = i * nth + j, i * nth + (j + 1) % nth
            c_, d_ = a_ + nth, b_ + nth
            F += [[a_, b_, d_], [a_, d_, c_]]
    cb, ct = nz * nth, nz * nth + 1
    for j in range(nth):
        F.append([cb, (j + 1) % nth, j])
        F.append([ct, (nz - 1) * nth + j, (nz - 1) * nth + (j + 1) % nth])
    return V, np.array(F)


def prove(defs):
    """Known answers (A10, once): (1) a tape girth bridges a planted concavity (the loop perimeter does not) and
    matches the ellipse; (2) the closed volume matches the analytic tube; (3) a planted front notch and a planted
    navel pit are found where they were planted, on a tube whose y axis points back; (4) a planted bump's volume on a
    flat front is found by the breast-volume rule; (5) the arm split's closure identity holds."""
    res = {}
    a, b, H = 0.15, 0.10, 0.6
    notch_z, navel_z = -0.05, -0.40
    groove_z = (-0.25, -0.15)

    def dent(x, y, z):
        d = np.zeros_like(x)
        front = y < 0
        # a notch: a 3 mm deep, 28 mm wide hollow at the front midline at notch_z
        d += front * 0.003 * np.exp(-(x / 0.010) ** 2 - ((z - notch_z) / 0.010) ** 2)
        # a navel pit: 6 mm deep, 6 mm wide
        d += front * 0.006 * np.exp(-(x / 0.004) ** 2 - ((z - navel_z) / 0.004) ** 2)
        # a vertical front groove (a 'cleavage') between groove_z: 5 mm deep, 15 mm wide
        g = (z > groove_z[0]) & (z < groove_z[1])
        d += front * g * 0.005 * np.exp(-(x / 0.0075) ** 2)
        return d

    v, f = _tube(lambda z: a, lambda z: b, -H + 0.05, 0.05, 1201, 720, dent=dent)
    body = Body(v, f, defs)
    body.x_mid = 0.0
    # (1) girth at the groove: the tape follows the ellipse except where it bridges the groove; the loop does not
    th = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    E = np.stack([a * np.cos(th), b * np.sin(th)], 1)
    p_ell = poly_perimeter(E)
    th2 = np.linspace(0, 2 * np.pi, 200000, endpoint=False)
    x2, y2 = a * np.cos(th2), b * np.sin(th2)
    r2 = np.hypot(x2, y2)
    d2 = dent(x2, y2, np.full_like(x2, -0.2))
    excess = poly_perimeter(np.stack([x2 * (1 - d2 / r2), y2 * (1 - d2 / r2)], 1)) - poly_perimeter(np.stack([x2, y2], 1))
    L = plane_loops(v, f, (0, 0, -0.2), (0, 0, 1), 0.005)
    tape, per = hull_perimeter(L[0]['Q']), poly_perimeter(L[0]['Q'])
    span, Rc = 6 * 0.0075, a * a / b
    bridge = span ** 3 / (24 * Rc ** 2)
    res['tape_bridges_groove'] = dict(tape_mm=tape * MM, ellipse_mm=p_ell * MM, loop_perimeter_mm=per * MM,
                                      groove_excess_analytic_mm=excess * MM,
                                      pass_=(0 <= (p_ell - tape) < bridge) and abs((per - tape) - excess) * MM < 0.1,
                                      mark='tape short of the ellipse by less than the chord over the groove '
                                           '(span^3 / 24 R^2 = %.3f mm, span 6 sigma, R the front curvature radius '
                                           'a^2/b); loop - tape = the analytic extra wall of the groove within 0.1 mm' % (bridge * MM))
    # (2) volume: the inscribed-polygon prism (dents remove a little: their analytic volume is subtracted)
    vpoly = 0.5 * 720 * np.sin(2 * np.pi / 720) * a * b * H
    vol = closed_volume(v, f)
    res['volume'] = dict(mesh_l=vol * 1e3, prism_l=vpoly * 1e3, pass_=abs(vol - vpoly) / vpoly < 0.002,
                         mark='0.2 %: the planted dents remove ~0.1 % of the volume')
    # (3) notch and navel on the sagittal profile (front = -y)
    ny, nz, _, _, _, _ = body.front_dent(0.0, notch_z - 0.04, notch_z + 0.04, D(defs, 'notch', 'chord_half_mm'))
    _, _, _, R, i, d = body.front_dent(0.0, navel_z - 0.05, navel_z + 0.05, D(defs, 'navel', 'chord_half_mm'))
    res['notch'] = dict(found_z_mm=nz * MM, planted_z_mm=notch_z * MM, pass_=abs(nz - notch_z) * MM < 1.0,
                        mark='1 mm: the profile is sampled every 0.5 mm and the sections every 0.5 mm')
    res['navel'] = dict(found_z_mm=R[i, 1] * MM, planted_z_mm=navel_z * MM, pass_=abs(R[i, 1] - navel_z) * MM < 1.0,
                        mark='1 mm, as the notch')
    # a failure side (A22): with the dents removed nothing is deeper than the tube's own (convex) profile
    v0, f0 = _tube(lambda z: a, lambda z: b, -H + 0.05, 0.05, 1201, 720)
    b0 = Body(v0, f0, defs)
    _, _, d0, _, _, _ = b0.front_dent(0.0, notch_z - 0.04, notch_z + 0.04, D(defs, 'notch', 'chord_half_mm'))
    res['no_dent_side'] = dict(max_chord_depth_mm=d0 * MM, pass_=d0 * MM < 0.01,
                               mark='a straight profile has no depth: < 0.01 mm')
    # (4) breast-volume rule on a flat-fronted slab with a planted Gaussian bump (known integral)
    n = 401
    xs = np.linspace(-0.1, 0.1, n)
    X, Z = np.meshgrid(xs, xs)
    A0, s0 = 0.03, 0.025
    Y = -A0 * np.exp(-(X ** 2 + Z ** 2) / (2 * s0 ** 2))  # bump toward -y (front)
    vs = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    F = []
    for i_ in range(n - 1):
        for j in range(n - 1):
            p = i_ * n + j
            F += [[p, p + 1, p + n + 1], [p, p + n + 1, p + n]]
    F = np.array(F)
    w = np.exp(-(X ** 2 + Z ** 2) / (2 * s0 ** 2)).ravel()
    rim_r = 0.075  # 3 sigma
    inside = (np.hypot(vs[:, 0], vs[:, 2]) < rim_r)
    fm = inside[F].all(1)
    base, rim, inner = membrane_fill(vs, F, fm)
    # orientation: the slab faces -y; the volume between skin and base along the face winding
    FF = F[fm]
    vsum = np.einsum('ij,ij->i', vs[FF[:, 0]], np.cross(vs[FF[:, 1]], vs[FF[:, 2]])).sum()
    bsum = np.einsum('ij,ij->i', base[FF[:, 0]], np.cross(base[FF[:, 1]], base[FF[:, 2]])).sum()
    vb = abs(vsum - bsum) / 6.0
    r_ = rim_r
    # analytic: integral of A0 exp(-r^2/2s^2) over r < R minus the rim level times the disc area
    exact = A0 * 2 * np.pi * s0 ** 2 * (1 - np.exp(-r_ ** 2 / (2 * s0 ** 2))) - A0 * np.exp(-r_ ** 2 / (2 * s0 ** 2)) * np.pi * r_ ** 2
    res['bump_volume'] = dict(found_ml=vb * 1e6, analytic_ml=exact * 1e6, pass_=abs(vb - exact) / exact < 0.01,
                              mark='1 %: the 0.5 mm grid and the polygonal rim')
    # (5) closure identity on a tube with an 'arm' label (the top third)
    wv = (v[:, 2] > -0.15).astype(float)
    fm = wv[f].mean(1) >= 0.5
    va, _, _ = patch_volume(v, f, fm)
    vt, _, _ = patch_volume(v, f, ~fm)
    res['closure'] = dict(sum_l=(va + vt) * 1e3, whole_l=vol * 1e3, pass_=abs(va + vt - vol) < 1e-12,
                          mark='exact: the same fans close both parts')
    res['all_pass'] = all(r['pass_'] for r in res.values() if isinstance(r, dict))
    return _r(res, 5)


# ------------------------------------------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('mesh', nargs='?')
    ap.add_argument('--defs', required=True)
    ap.add_argument('--zones')
    ap.add_argument('--weights')
    ap.add_argument('--joints')
    ap.add_argument('--colour', help='npz with per-vertex linear colour (skin_colour or colour; N x 3 or N x 4)')
    ap.add_argument('--out')
    ap.add_argument('--prove', action='store_true')
    a = ap.parse_args(argv)
    defs = json.load(open(a.defs))
    if a.prove:
        r = prove(defs)
        print(json.dumps(r, indent=1))
        if a.out:
            json.dump(r, open(a.out, 'w'), indent=1)
        return 0 if r['all_pass'] else 1
    v, f = load_mesh(a.mesh)
    zones = None
    if a.zones:
        z = np.load(a.zones)
        zones = {k: z[k].astype(np.float64) for k in ('breast', 'areola', 'nipple')}
    weights = None
    if a.weights:
        w = np.load(a.weights)
        # 'names' (every vertex group's column, a pack v2 weights file) or 'bones' (bone columns only)
        weights = (w['W'], [str(b) for b in w['names' if 'names' in w.files else 'bones']])
    joints = bones = None
    if a.joints:
        rj = json.load(open(a.joints))
        joints, bones = rj['joints'], rj.get('bones')
    colour = None
    if a.colour:
        c = np.load(a.colour)
        colour = c['skin_colour' if 'skin_colour' in c.files else 'colour']
    body = Body(v, f, defs, zones=zones, weights=weights, joints=joints, bones=bones, colour=colour)
    m = measurements(body)
    m['inputs'] = dict(mesh=a.mesh, defs=a.defs, zones=a.zones, weights=a.weights, joints=a.joints, colour=a.colour)
    if a.out:
        json.dump(m, open(a.out, 'w'), indent=1)
        print('wrote', a.out)
    else:
        print(json.dumps(m, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
