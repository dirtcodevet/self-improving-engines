"""PART FRAMES: one body part's mesh in its own 3-D frame (centimetres, anchored on the part's anatomy), with addresses
that keep naming the same place on the body after the model changes.

Why it exists (woman2 build 09, 2026-10-20). The person's idea: a 3-D space per body part, like a plot of a breast in
X lateral / Y superior / Z projection, but with the real mesh in it, "for geometric modelling, reference and
measurement" (cases/woman2/parts/example_breast_frame_v12_L.png). Two users: agents render a part in its frame and
measure from it; the person opens it in the browser, turns it, clicks a vertex dot for its coordinates. Added the same
day: the view is a SHARED LANGUAGE - the person picks one point, several points or a run of grid points and pastes
them into chat ("these points on the areola, move them 5 along y"; "along this grid series, a 7 degree convex
curve"), so a picked place must still mean the same place after the model changes. Vertex numbers do not survive a
remesh, so every pick is written as an ADDRESS in the part's anatomical frame, which re-resolves on any later mesh.
Build 10 (same day): the build-09 grid was a flat lattice laid along one direction of the part; where the skin turned
away from it (the walls round the breast's base, the fold under it, finger sides, the wrist cap) its segments spanned
up to 4.7 cm of skin per 1 cm step, points were dropped past a 70 deg turn and up to 18 % of a part's vertices had no
address; the nipple had one point. The grid now FOLLOWS THE SKIN: SKIN CHARTS (below) read addresses by walking on the
skin along sections, evenly spaced on the skin, finer where the entry asks (the nipple, the areola), and every vertex
gets an address. The build-09 kinds still resolve, so addresses already pasted keep naming the same places.

DATA, NOT CODE. What makes a part (which vertices, which landmarks, the frame's origin and axes, the address system,
per-vertex fields, measures) is an entry in a definitions file (the human pack's: engine/packs/human/part_frames.json).
This module knows only the generic operations listed below; a new part (torso, leg, neck, head, eyeball) is a new
entry. A JOB file (in the case) binds a definition's named inputs (masks, zone weights, face sets, joints, height grids)
to one source mesh, so the same definition reads another mesh through another binding.

FRAME. Axes X lateral, Y superior, Z anterior / outward, as in the anatomical position. A part on the subject's right
side gets the MIRRORED frame (left-handed), so left and right read alike (lateral is +X on both); a part with no side
gets a right-handed frame. Origin and axes come from the entry's landmarks. Units: cm.

ADDRESSES (text, one per line; `resolve` turns them back into points on any build of the part):
  breast_L h+ x=2.00 y=-3.00      height kind: the outermost surface along +Z (h- : along -Z) over the point (x, y)
  arm_L tube s=12.0 a=90          tube kind: station s (cm along the axis through the entry's landmarks) and angle a
                                  (deg round it, 0 = anterior (+Z), 90 = lateral (+X)); the first surface out from the axis
  head sphere lat=10 lon=-30      sphere kind: direction from the centre landmark (lat from +Y, lon 0 = +Z, 90 = +X)
  breast_L xyz x=2.01 y=-3.02 z=3.71   any point: the nearest surface point
SKIN CHARTS (build 10; an entry's "skin": {"charts": [...]}, in order; the grid and the vertex addresses):
  breast_L skin x=2.00 y=-3.00    disc chart: walk on the skin from the pole (the outermost skin on the chart's axis)
                                  along the section by the plane through the axis toward (x, y); the distance read is
                                  the ring coordinate u. u equals the frame's own radius where the skin turns less than
                                  turn_deg (30) from the frame (so there it IS the h+ number), and keeps growing at
                                  cos(turn_deg) or more per cm of skin past that (walls, folds, the skin under them)
  arm_L skin s=12.00 c=-3.00      tube chart: s = the ring (the station along the axis where the skin runs along it,
                                  read along the skin past a turn, so caps and junction folds get rings of their own);
                                  c = cm along the ring from the reference line (c_from_deg), signed the shorter way,
                                  + toward increasing angle
  hand_L middle s=4.50 c=0.50     a part may have several charts (the hand: palm, back, five digits, five tip caps);
                                  each has a region (select ops) and is drawn only where it addresses the skin
Every walk is a level-set walk on the chart's own mesh (numba): a meridian is a plane (disc) or a half-plane swept
along the axis (tube); a ring is a level set of the per-vertex ring field u (stored, so `resolve` works on the npz).
Walks bridge notches of the part's own edge up to bridge_cm (1 cm) wide (never a seam with another region; an address
that falls in a gap misses), cuts are turned DTH / lifted DU off exact alignment with mesh edges, and tube charts read
skin paths in chords of min(ruler_cm, 0.15 x the distance from the axis) so a remesh's roughness and mm-scale folds do
not shift them. A part's grid is its charts' lattices at the entry's steps (the dots and lines in the view: the disc's
x / y lattice, the tube's rings and the links between them), kept where the cut meets the skin at more than 20 deg;
a grid point's name IS its address. Every vertex gets the address of the first chart whose address resolves back
onto it (to 0.05 cm), else the build-09 kind's if that resolves back, else only xyz.

Generic operations (the entry's vocabulary; units: cm in the entry, the source's own units in the job):
  select:    mask, weight (min), side (by the source's left), grid_mask (a height grid's mask, dilated, near its top
             surface), plane (keep one side), not, any (a list OR-ed; a list at top level is AND-ed)
  landmarks: point (a bound input), extreme (furthest along a direction among a selection), farthest (from a landmark
             among a selection), centroid, seam (centroid of the vertices two selections share), grid_base_under
             (a height grid's base surface under a point, along the grid's normal)
  directions: from/to landmarks, vector (source frame), vector_side (x mirrored for the right side), grid_normal,
             frame_axis (the part's own axis; for selections, which run after the frame)
  frame:     origin landmark; two axes (the first exact, the second made perpendicular); the third by handedness
  fields:    above_grid_base (height above a height grid's base surface), input (a bound per-vertex array)
  measures:  coord, distance, angle, segment_angles, extent (optionally in a band), grid_volume, grid_mask_extent,
             tube_sections (girth, perimeter, area every step; at a landmark, at a midpoint, max/min between two),
             plane_distance
  overlays:  grid_outline (a height grid's polar outline on its base surface), polyline (landmarks)
  build L1 (2026-10-21; engine/tools/language.py writes entries for any object from these):
             select normal_toward (vertices whose normal points toward a direction: dot > min, default 0); landmark
             closest (the nearest point ON a selection's surface to a landmark); direction mean_normal (the area-weighted
             normal of a selection); measure area (of the part's faces, cm2). A job source's mesh may FOLLOW a pack
             ({"follow_pack": dir, "file": name}: the version its pack.json names current) and its paths may hold
             {current}; job items may give "name" and "side". Every built part records the fingerprint of what it was
             made from (fingerprint()), so engine/tools/language.py rebuilds exactly what is stale
  skin:      charts of kind disc (axis: a frame axis or {from, to} landmarks; through; from + / -) or tube (through,
             before_cm, after_cm, blend_cm, ref {mid | at | fraction | cm}, c_from_deg); each: region, turn_deg,
             bridge_cm, ruler_cm, grid [{step_cm, near (a selection), margin_cm}] (a finer level over its zone)

Usage:
  python part_frame.py build JOB.json [NAME ...]     writes NAME.json/.npz/.html/.png per part in the job's out_dir
  python part_frame.py resolve PART.npz ADDRESS ...   points of addresses (an address may be a pasted line)
  python part_frame.py prove                          the proof on analytic shapes (see prove(), prove_skin())
"""
import base64
import datetime
import hashlib
import json
import math
import os
import re
import sys
import time

import numpy as np
from numba import njit, prange
from scipy import ndimage
from scipy.spatial import cKDTree, ConvexHull

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
VIEW_TEMPLATE = os.path.join(HERE, "part_frame_view.html")
TOL_CM = 0.05            # an address round-trips when it resolves within this of the vertex it came from
AXES = {"x": 0, "y": 1, "z": 2}


def _unit(a):
    a = np.asarray(a, float); n = np.linalg.norm(a)
    return a / n if n > 0 else a


def _sha1(obj):
    return hashlib.sha1(json.dumps(obj, sort_keys=True).encode()).hexdigest()


# ----------------------------------------------------------------------------------------------- ray casting (numba)
@njit(cache=True)
def _bin_count(c0, c1, dims, cnt):
    for i in range(c0.shape[0]):
        for x in range(c0[i, 0], c1[i, 0] + 1):
            for y in range(c0[i, 1], c1[i, 1] + 1):
                for z in range(c0[i, 2], c1[i, 2] + 1):
                    cnt[(x * dims[1] + y) * dims[2] + z] += 1


@njit(cache=True)
def _bin_fill(c0, c1, dims, pos, items):
    for i in range(c0.shape[0]):
        for x in range(c0[i, 0], c1[i, 0] + 1):
            for y in range(c0[i, 1], c1[i, 1] + 1):
                for z in range(c0[i, 2], c1[i, 2] + 1):
                    c = (x * dims[1] + y) * dims[2] + z
                    items[pos[c]] = i; pos[c] += 1


@njit(cache=True)
def _tri_t(ox, oy, oz, dx, dy, dz, V, F, k):
    ax, ay, az = V[F[k, 0], 0], V[F[k, 0], 1], V[F[k, 0], 2]
    e1x, e1y, e1z = V[F[k, 1], 0] - ax, V[F[k, 1], 1] - ay, V[F[k, 1], 2] - az
    e2x, e2y, e2z = V[F[k, 2], 0] - ax, V[F[k, 2], 1] - ay, V[F[k, 2], 2] - az
    px, py, pz = dy * e2z - dz * e2y, dz * e2x - dx * e2z, dx * e2y - dy * e2x
    det = e1x * px + e1y * py + e1z * pz
    if abs(det) < 1e-18:
        return np.inf
    inv = 1.0 / det
    sx, sy, sz = ox - ax, oy - ay, oz - az
    u = (sx * px + sy * py + sz * pz) * inv
    if u < -1e-9 or u > 1.0 + 1e-9:
        return np.inf
    qx, qy, qz = sy * e1z - sz * e1y, sz * e1x - sx * e1z, sx * e1y - sy * e1x
    v = (dx * qx + dy * qy + dz * qz) * inv
    if v < -1e-9 or u + v > 1.0 + 1e-9:
        return np.inf
    return (e2x * qx + e2y * qy + e2z * qz) * inv


@njit(cache=True, parallel=True)
def _cast(V, F, lo, cs, dims, start, items, O, D, tmin, tmax, out_t, out_f):
    for r in prange(O.shape[0]):
        out_t[r] = np.inf; out_f[r] = -1
        o0, o1, o2 = O[r, 0], O[r, 1], O[r, 2]
        d0, d1, d2 = D[r, 0], D[r, 1], D[r, 2]
        t0, t1 = tmin, tmax
        ok = True
        for a in range(3):
            oa = O[r, a]; da = D[r, a]; la = lo[a]; ha = lo[a] + dims[a] * cs
            if abs(da) < 1e-15:
                if oa < la or oa > ha:
                    ok = False
            else:
                ta = (la - oa) / da; tb = (ha - oa) / da
                if ta > tb:
                    ta, tb = tb, ta
                if ta > t0:
                    t0 = ta
                if tb < t1:
                    t1 = tb
        if not ok or t0 > t1:
            continue
        ix = np.zeros(3, np.int64); st = np.zeros(3, np.int64); tM = np.zeros(3); tD = np.zeros(3)
        for a in range(3):
            oa = O[r, a]; da = D[r, a]
            i = int((oa + da * t0 - lo[a]) / cs)
            i = min(max(i, 0), dims[a] - 1); ix[a] = i
            if da > 0:
                st[a] = 1; tM[a] = (lo[a] + (i + 1) * cs - oa) / da; tD[a] = cs / da
            elif da < 0:
                st[a] = -1; tM[a] = (lo[a] + i * cs - oa) / da; tD[a] = -cs / da
            else:
                st[a] = 0; tM[a] = np.inf; tD[a] = np.inf
        best = np.inf; bf = -1
        while True:
            c = (ix[0] * dims[1] + ix[1]) * dims[2] + ix[2]
            for q in range(start[c], start[c + 1]):
                k = items[q]
                t = _tri_t(o0, o1, o2, d0, d1, d2, V, F, k)
                if t >= tmin and t <= t1 and t < best:
                    best = t; bf = k
            a = 0
            if tM[1] < tM[a]:
                a = 1
            if tM[2] < tM[a]:
                a = 2
            if best <= tM[a] or tM[a] > t1:
                break
            ix[a] += st[a]
            if ix[a] < 0 or ix[a] >= dims[a]:
                break
            tM[a] += tD[a]
        out_t[r] = best; out_f[r] = bf


class Caster:
    """first hit of rays on a triangle mesh (uniform grid + 3-D DDA, both faces count)"""

    def __init__(self, V, F, cell=None):
        self.V = np.ascontiguousarray(V, np.float64); self.F = np.ascontiguousarray(F, np.int64)
        T = self.V[self.F]; tlo, thi = T.min(1), T.max(1)
        lo = tlo.min(0) - 1e-6; ext = thi.max(0) + 1e-6 - lo
        if cell is None:
            edge = np.median(np.linalg.norm(T[:, 1] - T[:, 0], axis=1))
            cell = max(3.0 * edge, ext.max() / 256.0)
        dims = np.maximum(np.ceil(ext / cell).astype(np.int64), 1)
        c0 = np.clip(((tlo - lo) / cell).astype(np.int64), 0, dims - 1); c1 = np.clip(((thi - lo) / cell).astype(np.int64), 0, dims - 1)
        cnt = np.zeros(int(np.prod(dims)), np.int64); _bin_count(c0, c1, dims, cnt)
        start = np.zeros(len(cnt) + 1, np.int64); np.cumsum(cnt, out=start[1:])
        items = np.zeros(start[-1], np.int64); pos = start[:-1].copy(); _bin_fill(c0, c1, dims, pos, items)
        self.lo, self.cs, self.dims, self.start, self.items = lo, float(cell), dims, start, items
        self.diag = float(np.linalg.norm(ext))

    def cast(self, O, D, tmin=0.0, tmax=None):
        O = np.ascontiguousarray(np.atleast_2d(O), np.float64); D = np.ascontiguousarray(np.atleast_2d(D), np.float64)
        D = D / np.linalg.norm(D, axis=1, keepdims=True)
        t = np.empty(len(O)); f = np.empty(len(O), np.int64)
        _cast(self.V, self.F, self.lo, self.cs, self.dims, self.start, self.items, O, D, float(tmin),
              float(tmax if tmax is not None else 4 * self.diag + np.abs(O).max()), t, f)
        P = O + D * np.where(np.isfinite(t), t, np.nan)[:, None]
        return P, t, f


def closest_points(V, F, P, k=12):
    """exact nearest surface point of each P (among the triangles round its k nearest vertices)"""
    tree = cKDTree(V); _, nn = tree.query(P, k=min(k, len(V)))
    nn = np.atleast_2d(nn)
    vf = [[] for _ in range(len(V))]
    for i, tri in enumerate(F):
        for a in tri:
            vf[a].append(i)
    out = np.empty_like(P); fid = np.empty(len(P), np.int64)
    for j, p in enumerate(P):
        cand = np.unique(np.concatenate([vf[a] for a in nn[j]]))
        Q = _closest_on_tris(p, V[F[cand]])
        d = np.linalg.norm(Q - p, axis=1); i = int(np.argmin(d)); out[j] = Q[i]; fid[j] = cand[i]
    return out, fid


def _closest_on_tris(p, T):
    """closest point on each triangle T (m x 3 x 3) to p (Ericson, Real-Time Collision Detection 5.1.5)"""
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp = p - b; d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
    cp = p - c; d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    va = d3 * d6 - d5 * d4; vb = d5 * d2 - d1 * d6; vc = d1 * d4 - d3 * d2
    den = va + vb + vc; den = np.where(np.abs(den) < 1e-30, 1e-30, den)
    v = vb / den; w = vc / den
    Q = a + ab * v[:, None] + ac * w[:, None]                                     # inside the face
    with np.errstate(divide="ignore", invalid="ignore"):
        e_ab = (vc <= 0) & (d1 >= 0) & (d3 <= 0); t = d1 / (d1 - d3); Q = np.where(e_ab[:, None], a + ab * t[:, None], Q)
        e_ac = (vb <= 0) & (d2 >= 0) & (d6 <= 0); t = d2 / (d2 - d6); Q = np.where(e_ac[:, None], a + ac * t[:, None], Q)
        e_bc = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0); t = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        Q = np.where(e_bc[:, None], b + (c - b) * t[:, None], Q)
    Q = np.where(((d1 <= 0) & (d2 <= 0))[:, None], a, Q)
    Q = np.where(((d3 >= 0) & (d4 <= d3))[:, None], b, Q)
    Q = np.where(((d6 >= 0) & (d5 <= d6))[:, None], c, Q)
    return Q


# --------------------------------------------------------------------------------------------------------- sources
class HeightGrid:
    """two height maps (top, base) over a plane frame (rows of R: e1, e2, normal; origin o; square grid, row = e2)
    with a mask: e.g. a skin and the wall under it. Units: the source's."""

    def __init__(self, o, R, step, n, top, base, mask, outline=None):
        self.o, self.R, self.step, self.n = np.asarray(o, float), np.asarray(R, float), float(step), int(n)
        self.top, self.base, self.mask, self.outline = np.asarray(top, float), np.asarray(base, float), np.asarray(mask, bool), outline

    def uvh(self, P):
        return (np.asarray(P, float) - self.o) @ self.R.T

    def _rc(self, q):
        return q[:, 1] / self.step + (self.n - 1) / 2, q[:, 0] / self.step + (self.n - 1) / 2

    def sample(self, grid, P):
        q = self.uvh(P); r, c = self._rc(q)
        return ndimage.map_coordinates(grid, [r, c], order=1, mode="constant", cval=np.nan), q

    def world(self, u, v, h):
        return self.o + np.stack([u, v, h], -1) @ self.R


def _load_npz(path, cache={}):
    if path not in cache:
        cache[path] = np.load(path, allow_pickle=False)
    return cache[path]


def _p(path):
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def pack_current(pack_dir):
    """the version folder a pack's pack.json names current (build L1: a job may follow it)"""
    pj = json.load(open(os.path.join(_p(pack_dir), "pack.json")))
    cur = pj.get("current") or pj.get("current_version") or pj.get("version")
    return (pack_dir.rstrip("/") + "/" + str(cur)).replace(os.sep, "/")


def _cur(path, mesh_spec):
    """{current} in a path -> the followed pack's current version folder"""
    if isinstance(path, str) and "{current}" in path:
        fp = mesh_spec.get("follow_pack") if isinstance(mesh_spec, dict) else None
        if not fp:
            raise ValueError(f"{path}: {{current}} needs the source's mesh to follow a pack")
        return path.replace("{current}", pack_current(fp))
    return path


def _bind(spec, side, src):
    """one job input -> value. Kinds: npz key (array), json path (number / point), height_grid, face_sets (vertex mask)"""
    fol = src.spec.get("mesh", {}) if isinstance(getattr(src, "spec", None), dict) else {}
    sub = lambda s: _cur(s.replace("{side}", side or ""), fol) if isinstance(s, str) else s
    if "npz" in spec:
        a = _load_npz(_p(sub(spec["npz"])))[sub(spec["key"])]
        return a
    if "json" in spec:
        d = json.load(open(_p(sub(spec["json"]))))
        for k in spec["path"]:
            d = d[sub(k)]
        return np.asarray(d, float)
    if "height_grid" in spec:
        z = _load_npz(_p(sub(spec["height_grid"]))); pre = sub(spec.get("prefix", "")); km = spec["keys"]
        g = lambda k: z[pre + km[k]]
        out = None
        if "outline_theta" in km:
            out = (g("outline_theta"), g("outline_r"))
        return HeightGrid(g("origin"), g("R"), float(g("step")), int(g("n")), g("top"), g("base"), g("mask"), out)
    if "face_sets" in spec:
        fs = src.get_input(spec["face_sets"], side)
        ids = spec["ids"][side] if isinstance(spec["ids"], dict) else spec["ids"]
        ids = _expand_ids(ids)
        m = np.zeros(len(src.V), bool); m[np.unique(src.F[np.isin(fs, ids)])] = True
        return m
    raise ValueError(f"unknown input kind {spec}")


def mesh_path(m):
    """a source's mesh file: its npz, or (build L1) the file in the version its followed pack names current"""
    if "follow_pack" in m:
        return pack_current(m["follow_pack"]) + "/" + m.get("file", "skin.npz")
    return _cur(m["npz"], m)


def _expand_ids(ids):
    out = []
    for x in ids:
        if isinstance(x, str) and "-" in x:
            a, b = x.split("-"); out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(x))
    return out


class Source:
    def __init__(self, name, spec):
        self.name, self.spec = name, spec
        m = spec["mesh"]; mpath = mesh_path(m); z = _load_npz(_p(mpath))
        self.V = z[m.get("v", "v")].astype(np.float64); self.F = z[m.get("f", "f")].astype(np.int64)
        self.to_cm = float(spec.get("units_m", 1.0)) * 100.0
        self.left = np.array({"+x": [1, 0, 0], "-x": [-1, 0, 0]}[spec.get("left", "+x")], float)
        self.label = spec.get("label", name); self._cache = {}
        self.files = {k: _sha1_file(_p(mpath)) for k in ["mesh"]}

    def vertex_normals(self):
        if "_vn" not in self._cache:
            fn = np.cross(self.V[self.F[:, 1]] - self.V[self.F[:, 0]], self.V[self.F[:, 2]] - self.V[self.F[:, 0]]); vn = np.zeros_like(self.V)
            for j in range(3):
                np.add.at(vn, self.F[:, j], fn)
            self._cache["_vn"] = vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-30)
        return self._cache["_vn"]

    def vertex_area(self):
        if "_area" not in self._cache:
            A = 0.5 * np.linalg.norm(np.cross(self.V[self.F[:, 1]] - self.V[self.F[:, 0]], self.V[self.F[:, 2]] - self.V[self.F[:, 0]]), axis=1)
            self._cache["_area"] = np.bincount(self.F.ravel(), np.repeat(A / 3, 3), minlength=len(self.V))
        return self._cache["_area"]

    def get_input(self, name, side):
        key = (name, side)
        if key not in self._cache:
            if name not in self.spec["inputs"]:
                raise KeyError(f"source {self.name}: no input '{name}' bound (the part definition needs it)")
            self._cache[key] = _bind(self.spec["inputs"][name], side, self)
        return self._cache[key]


def _sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------------ evaluation
class Part:
    def __init__(self, entry, src, side, name):
        self.e, self.src, self.side, self.name = entry, src, side, name
        self.s = -1.0 if side == "R" else 1.0                 # handedness: the right side's frame is mirrored
        self.lm = {}                                          # landmarks, source coordinates

    # selections -> vertex mask over the source
    def select(self, ops):
        V = self.src.V
        if isinstance(ops, list):
            m = np.ones(len(V), bool)
            for op in ops:
                m &= self.select(op)
            return m
        k, a = next(iter(ops.items()))
        if k == "mask":
            return np.asarray(self.src.get_input(a, self.side)).astype(bool)
        if k == "weight":
            return np.asarray(self.src.get_input(a, self.side), float) >= ops.get("min", 0.5)
        if k == "side":
            return (V @ self.src.left) * self.s > 0 if a else np.ones(len(V), bool)
        if k == "not":
            return ~self.select(a)
        if k == "any":
            m = np.zeros(len(V), bool)
            for op in a:
                m |= self.select(op)
            return m
        if k == "grid_mask":
            g = self.src.get_input(a["grid"], self.side)
            msk = g.mask
            if a.get("dilate_cm"):
                rpx = a["dilate_cm"] / self.src.to_cm / g.step
                y, x = np.mgrid[-int(rpx) - 1:int(rpx) + 2, -int(rpx) - 1:int(rpx) + 2]
                msk = ndimage.binary_dilation(msk, x * x + y * y <= rpx * rpx)
            top, q = g.sample(g.top, V)
            r, c = g._rc(q); ri, ci = np.rint(r).astype(int), np.rint(c).astype(int)
            ok = (ri >= 0) & (ri < g.n) & (ci >= 0) & (ci < g.n)
            inm = np.zeros(len(V), bool); inm[ok] = msk[ri[ok], ci[ok]]
            if a.get("near_top_cm") is not None:                 # on the top surface's layer
                inm &= np.abs(q[:, 2] - top) < a["near_top_cm"] / self.src.to_cm
            if a.get("above_base_cm") is not None:               # in front of the base surface (less this much)
                base, _ = g.sample(g.base, V); inm &= (q[:, 2] - base) > a["above_base_cm"] / self.src.to_cm
            return inm
        if k == "normal_toward":                                  # (L1) vertex normals toward a direction
            d = self.direction(a["dir"]); return self.src.vertex_normals() @ d > float(a.get("min", 0.0))
        if k == "plane":
            p = self.landmark_or_point(a["through"]); n = self.direction(a["normal"])
            return ((V - p) @ n >= 0) if a.get("keep", "+") == "+" else ((V - p) @ n < 0)
        raise ValueError(f"unknown selection {k}")

    def landmark_or_point(self, ref):
        if isinstance(ref, str):
            if ref in self.lm:
                return self.lm[ref]
            return np.asarray(self.src.get_input(ref, self.side), float)
        return np.asarray(ref, float)

    def direction(self, d):
        if "from" in d:
            return _unit(self.landmark_or_point(d["to"]) - self.landmark_or_point(d["from"]))
        if "vector" in d:
            return _unit(d["vector"])
        if "vector_side" in d:
            v = np.asarray(d["vector_side"], float).copy(); v = v - 2 * (v @ self.src.left) * self.src.left * (self.s < 0)
            return _unit(v)
        if "grid_normal" in d:
            return _unit(self.src.get_input(d["grid_normal"], self.side).R[2])
        if "mean_normal" in d:                                   # (L1) the area-weighted normal of a selection's faces
            m = self.select(d["mean_normal"]); fm = m[self.src.F].all(1); V, F = self.src.V, self.src.F[fm]
            return _unit(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]).sum(0))
        if "frame_axis" in d:                                    # the part's own axis (selections run after the frame)
            return self.R[AXES[d["frame_axis"]]].copy()
        raise ValueError(f"unknown direction {d}")

    def landmark(self, spec):
        k, a = next((kk, vv) for kk, vv in spec.items() if kk not in ("source", "what"))
        V = self.src.V
        if k == "point":
            return np.asarray(self.src.get_input(a, self.side), float).reshape(3)
        if k == "extreme":
            m = self.select(a["among"]); idx = np.nonzero(m)[0]
            return V[idx[np.argmax(V[idx] @ self.direction(a["dir"]))]].copy()
        if k == "farthest":
            m = self.select(a["among"]); idx = np.nonzero(m)[0]; p = self.landmark_or_point(a["from"])
            return V[idx[np.argmax(np.linalg.norm(V[idx] - p, axis=1))]].copy()
        if k == "centroid":                                       # area-weighted (x an input weight): stable under a remesh
            m = self.select(a["among"]); w = self.src.vertex_area() * m
            if a.get("weight"):
                w = w * np.asarray(self.src.get_input(a["weight"], self.side), float)
            return (V * w[:, None]).sum(0) / w.sum()
        if k == "lerp":
            pa, pb = self.landmark_or_point(a[0]), self.landmark_or_point(a[1]); return pa + float(a[2]) * (pb - pa)
        if k == "seam":
            m = self.select(a[0]) & self.select(a[1])
            if not m.any():
                raise ValueError(f"{self.name}: seam {a} is empty")
            return V[m].mean(0)
        if k == "closest":                                        # (L1) the nearest point on a selection's surface
            m = self.select(a["among"]); Fs = self.src.F[m[self.src.F].all(1)]; p = self.landmark_or_point(a["to"])
            T = V[Fs]; ar = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); Fs = Fs[ar > ar.max() * 1e-9]
            used = np.unique(Fs); rm = -np.ones(len(V), np.int64); rm[used] = np.arange(len(used))
            Q, _ = closest_points(V[used], rm[Fs], np.asarray(p, float)[None]); return Q[0]
        if k == "grid_base_under":
            g = self.src.get_input(a["grid"], self.side); p = self.landmark_or_point(a["point"])
            b, q = g.sample(g.base, p[None])
            return g.world(q[:, 0], q[:, 1], b)[0]
        raise ValueError(f"unknown landmark {k}")

    def build_frame(self):
        fr = self.e["frame"]
        o = self.lm[fr["origin"]]
        (n1, d1), (n2, d2) = fr["axes"]
        a1 = self.direction(d1); a2 = self.direction(d2); a2 = _unit(a2 - (a2 @ a1) * a1)
        ax = {n1: a1, n2: a2}
        third = ({"x", "y", "z"} - {n1, n2}).pop()
        X, Y, Z = ax.get("x"), ax.get("y"), ax.get("z")
        if third == "x":
            X = self.s * np.cross(Y, Z)
        elif third == "y":
            Y = self.s * np.cross(Z, X)
        else:
            Z = self.s * np.cross(X, Y)
        R = np.stack([X, Y, Z])
        checks = {}
        for an, dspec in fr.get("check", {}).items():
            dv = self.direction(dspec); checks[an] = float(R[AXES[an]] @ dv)
            if checks[an] <= 0:
                raise AssertionError(f"{self.name}: frame check failed, axis {an} . {dspec} = {checks[an]:.3f}")
        self.o, self.R, self.frame_checks = o, R, checks

    def to_frame(self, P):
        return (np.asarray(P, float) - self.o) @ self.R.T * self.src.to_cm

    def to_source(self, Q):
        return self.o + (np.asarray(Q, float) / self.src.to_cm) @ self.R


# ----------------------------------------------------------------------------------------------- address systems
class Address:
    """the part's address system on its own mesh (frame cm): params of points, resolve params -> points, the grid"""

    def __init__(self, spec, part_name, V, F, lm):
        self.spec, self.kind, self.part = spec, spec["kind"], part_name
        self.V, self.F, self.lm = V, F, lm
        self.caster = Caster(V, F)
        fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); self.fn = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-30)
        # conditioning: an address is kept only where the surface faces its ray within acos(min_facing) (default 70 deg);
        # on a wall nearly parallel to the ray a 0.1 mm surface change moves the hit by mm (measured, remesh proof)
        self.min_facing = float(spec.get("min_facing", 0.34))
        if self.kind == "tube":
            P = np.array([lm[n] for n in spec["through"]]); self._tube_setup(P)
        if self.kind == "sphere":
            self.c = np.asarray(lm[spec["centre"]], float)

    # ---- tube geometry: polyline through landmarks, extended at both ends, direction blended over +-w at joints
    def _tube_setup(self, P):
        seg = np.diff(P, axis=0); L = np.linalg.norm(seg, axis=1); d = seg / L[:, None]
        self.tP, self.td, self.tL = P, d, L
        self.ts = np.r_[0.0, np.cumsum(L)]                       # arc length of the joints
        self.w = float(self.spec.get("blend_cm", 4.0))
        self.smin = -float(self.spec.get("before_cm", 0.0)); self.smax = self.ts[-1] + float(self.spec.get("after_cm", 0.0))

    def _c(self, s):
        s = np.atleast_1d(np.asarray(s, float)); j = np.clip(np.searchsorted(self.ts, s, side="right") - 1, 0, len(self.td) - 1)
        return self.tP[j] + self.td[j] * (s - self.ts[j])[:, None]

    def _d(self, s):
        s = np.atleast_1d(np.asarray(s, float)); j = np.clip(np.searchsorted(self.ts, s, side="right") - 1, 0, len(self.td) - 1)
        d = self.td[j].copy()
        for k in range(1, len(self.td)):                         # joint k between segment k-1 and k
            t = np.clip((s - self.ts[k] + self.w) / (2 * self.w), 0, 1); t = t * t * (3 - 2 * t)
            m = (t > 0) & (t < 1)
            d[m] = (1 - t[m])[:, None] * self.td[k - 1] + t[m][:, None] * self.td[k]
        return d / np.linalg.norm(d, axis=1, keepdims=True)

    def _e(self, d):
        Z = np.array([0, 0, 1.0]); X = np.array([1.0, 0, 0])
        e0 = Z - (d @ Z)[:, None] * d; e0 /= np.linalg.norm(e0, axis=1, keepdims=True)
        e9 = X - (d @ X)[:, None] * d - (e0 @ X)[:, None] * e0; e9 /= np.linalg.norm(e9, axis=1, keepdims=True)
        return e0, e9

    def tube_station(self, P):
        lo = np.full(len(P), self.smin); hi = np.full(len(P), self.smax)
        g = lambda s: ((P - self._c(s)) * self._d(s)).sum(1)
        glo, ghi = g(lo), g(hi); bad = (glo < 0) | (ghi > 0)
        for _ in range(48):
            mid = 0.5 * (lo + hi); gm = g(mid); up = gm > 0; lo = np.where(up, mid, lo); hi = np.where(up, hi, mid)
        s = 0.5 * (lo + hi); s[bad] = np.nan
        return s

    def tube_rays(self, s, a_deg):
        s = np.asarray(s, float); d = self._d(s); e0, e9 = self._e(d); a = np.radians(a_deg)
        return self._c(s), np.cos(a)[:, None] * e0 + np.sin(a)[:, None] * e9

    # ---- params of points and points of params
    def params_of(self, P):
        """address params of points P (frame cm) in this kind, NaN where undefined"""
        if self.kind == "height":
            i, j = self._hij(); return np.c_[P[:, i], P[:, j]]
        if self.kind == "tube":
            s = self.tube_station(P); ok = np.isfinite(s); out = np.full((len(P), 2), np.nan)
            if ok.any():
                c = self._c(s[ok]); d = self._d(s[ok]); e0, e9 = self._e(d); r = P[ok] - c
                out[ok, 0] = s[ok]; out[ok, 1] = np.degrees(np.arctan2((r * e9).sum(1), (r * e0).sum(1))) % 360
            return out
        if self.kind == "sphere":
            r = P - self.c; r /= np.linalg.norm(r, axis=1, keepdims=True)
            return np.c_[np.degrees(np.arcsin(np.clip(r[:, 1], -1, 1))), np.degrees(np.arctan2(r[:, 0], r[:, 2]))]
        raise ValueError(self.kind)

    def _hij(self):
        up = AXES[self.spec.get("up", "z")]; return [a for a in range(3) if a != up]

    def resolve(self, params, side="+", facing=False):
        """points of address params (NaN where the ray misses); facing=True also returns |surface normal . ray|"""
        params = np.atleast_2d(np.asarray(params, float))
        if self.kind == "height":
            up = AXES[self.spec.get("up", "z")]; i, j = self._hij(); O = np.zeros((len(params), 3)); D = np.zeros_like(O)
            far = np.abs(self.V).max() * 2 + 10
            O[:, i], O[:, j] = params[:, 0], params[:, 1]; sg = 1.0 if side == "+" else -1.0
            O[:, up] = sg * far; D[:, up] = -sg
            Q, _, f = self.caster.cast(O, D)
        elif self.kind == "tube":
            O, D = self.tube_rays(params[:, 0], params[:, 1]); Q, _, f = self.caster.cast(O, D, tmin=0.0)
        elif self.kind == "sphere":
            la, lo = np.radians(params[:, 0]), np.radians(params[:, 1])
            D = np.c_[np.cos(la) * np.sin(lo), np.sin(la), np.cos(la) * np.cos(lo)]
            Q, _, f = self.caster.cast(np.repeat(self.c[None], len(D), 0), D)
        else:
            raise ValueError(self.kind)
        if not facing:
            return Q
        fa = np.where(f >= 0, np.abs((self.fn[np.maximum(f, 0)] * D).sum(1)), np.nan)
        return Q, fa

    def sides(self):
        return self.spec.get("sides", ["+"]) if self.kind == "height" else [""]

    def text(self, params, side=""):
        p = params
        if self.kind == "height":
            ax = [n for n, a in AXES.items() if a in self._hij()]
            return f"{self.part} h{side} {ax[0]}={p[0]:.2f} {ax[1]}={p[1]:.2f}"
        if self.kind == "tube":
            return f"{self.part} tube s={p[0]:.2f} a={p[1]:.1f}"
        return f"{self.part} sphere lat={p[0]:.1f} lon={p[1]:.1f}"

    def vertex_addresses(self):
        """per vertex: params, side index (into sides(); -1 = no address of this kind round-trips), round-trip error"""
        P = self.V; prm = self.params_of(P); n = len(P)
        best = np.full(n, np.inf); side = np.full(n, -1)
        for k, sd in enumerate(self.sides()):
            ok = np.isfinite(prm).all(1); Q = np.full_like(P, np.nan); fa = np.zeros(n)
            if ok.any():
                Q[ok], fa[ok] = self.resolve(prm[ok], sd, facing=True)
            err = np.linalg.norm(Q - P, axis=1); err[~np.isfinite(err) | ~(fa >= self.min_facing)] = np.inf
            better = err < best; best[better] = err[better]; side[better & (err <= TOL_CM)] = k
        side[best > TOL_CM] = -1
        return prm, side, best

    def grid(self):
        """the address lattice: names, sides, params, resolved points, and lines (index lists) along the lattice"""
        sp = self.spec; pts, names, prm_l, sd_l, lines = [], [], [], [], []

        def add_lattice(A, B, sd, wrap_b=False):
            AA, BB = np.meshgrid(A, B, indexing="ij"); prm = np.c_[AA.ravel(), BB.ravel()]
            Q, fa = self.resolve(prm, sd, facing=True) if self.kind == "height" else self.resolve(prm, facing=True)
            ok = np.isfinite(Q).all(1) & (fa >= self.min_facing); idx = -np.ones(len(prm), int); base = len(pts)
            idx[ok] = base + np.arange(ok.sum())
            for p, q in zip(prm[ok], Q[ok]):
                pts.append(q); prm_l.append(p); sd_l.append(sd); names.append(self.text(p, sd))
            I = idx.reshape(len(A), len(B))
            for row, wrap in [(r_, wrap_b) for r_ in I] + [(r_, False) for r_ in I.T]:   # runs along both lattice directions
                run = []
                for v in list(row) + ([row[0]] if wrap else []):
                    if v >= 0:
                        run.append(int(v))
                    else:
                        if len(run) > 1:
                            lines.append(run)
                        run = []
                if len(run) > 1:
                    lines.append(run)
        if self.kind == "height":
            st = sp["step_cm"]; i, j = self._hij()
            lo = np.floor(self.V[:, [i, j]].min(0) / st) * st; hi = np.ceil(self.V[:, [i, j]].max(0) / st) * st
            A = np.arange(lo[0], hi[0] + st / 2, st); B = np.arange(lo[1], hi[1] + st / 2, st)
            for sd in self.sides():
                add_lattice(A, B, sd)
        elif self.kind == "tube":
            st = sp["step_cm"]; S = np.arange(math.ceil(self.smin / st) * st, self.smax + st / 2, st)
            A = np.arange(0, 360, sp["angle_deg"]); add_lattice(S, A, "", wrap_b=True)
        elif self.kind == "sphere":
            st = sp["angle_deg"]; add_lattice(np.arange(-90 + st, 90, st), np.arange(-180, 180, st), "", wrap_b=True)
        return np.array(pts).reshape(-1, 3), names, np.array(prm_l).reshape(-1, 2), sd_l, lines


# ---------------------------------------------------------------------------------- skin charts (build 10)
# A skin chart names places by walking ON the skin: along the section of the part's mesh by a plane (or a smooth
# family of surfaces) - a section cuts the skin across even where it turns away from any fixed direction, so the walk
# reaches walls, folds and the skin under them. Two coordinates per chart:
#   along: a RING coordinate u, read along the chart's meridians (sections through its axis) as an envelope:
#          u(p) = max over q before p on p's meridian of [sigma(q) + kappa * arc(q -> p)], kappa = cos(turn_deg),
#          sigma = the frame coordinate the rings stand on (disc: the distance from the axis; tube: the station along
#          it). Where the skin turns less than turn_deg from that coordinate's direction, u = sigma exactly (a local
#          read of the frame, stable on a remesh); where it turns more (a wall, a fold, a cap), u keeps growing at
#          kappa or more per cm of skin, so rings stay at most 1 / kappa cm apart on the skin per cm of u. Past a
#          turn, u relaxes back to sigma at (1 - kappa) per cm, so a small feature near the axis (a nipple) does not
#          shift the addresses beyond it.
#   round: disc: the meridian's direction (the chart is (x, y) = u * direction: an azimuthal map in which, inside
#          the turn, the numbers equal the frame's own x, y); tube: c, the arc length along the ring (the level set
#          of u) from the chart's reference meridian, + toward increasing angle, so points round a limb are evenly
#          spaced whatever its girth.

DTH = 5.4321e-5        # rad: every meridian cut is turned by this, and every ring level lifted by DU (cm), in the inverse
DU = 1.234567e-5       # and the forward walk alike: a cut then never runs along mesh edges (an aligned mesh, a voxel remesh),
MET = 2.5e-3           # whose crossings would zig-zag along them; both exceed float32 noise. A vertex is met within MET cm.


def _topology(F):
    """face adjacency: NB[f, k] = the face across edge k (F[f,k] -> F[f,k+1]) and NBK its edge index; -1 on a
    boundary or a non-manifold edge"""
    m = len(F); E = np.stack([F, np.roll(F, -1, 1)], -1).reshape(-1, 2)
    key = np.sort(E, 1); kid = key[:, 0].astype(np.int64) * (int(F.max()) + 1) + key[:, 1]
    o = np.argsort(kid, kind="stable"); ks = kid[o]
    NB = -np.ones(3 * m, np.int64); NBK = -np.ones(3 * m, np.int64)
    st = np.r_[0, np.nonzero(ks[1:] != ks[:-1])[0] + 1]; cnt = np.diff(np.r_[st, len(ks)])
    two = st[cnt == 2]; a, b = o[two], o[two + 1]
    NB[a] = b // 3; NBK[a] = b % 3; NB[b] = a // 3; NBK[b] = a % 3
    return NB.reshape(m, 3), NBK.reshape(m, 3)


@njit(cache=True)
def _lv(cf, r0, r9, wf, v):
    return cf[0] * r0[v] + cf[1] * r9[v] + cf[2] * wf[v] + cf[3]


@njit(cache=True)
def _sg(cf, r0, r9, sf, v):
    return cf[7] * r0[v] + cf[8] * r9[v] + cf[9] * sf[v]


@njit(cache=True)
def _ev(cf, r0, r9, sf, v):
    return cf[10] * r0[v] + cf[11] * r9[v] + cf[12] * sf[v]


@njit(cache=True)
def _seg(st, Xp, Qm, X, sX, f, mode, kappa, target, Bq, res, outP, outF, outU, gap):
    """one segment Xp -> X of a walk (face f): advance the envelope / arc; 1 = the walk is done (res filled),
    2 = stop (mode 5 past its arc), 3 = the target falls in a bridged gap (not on the skin: a miss), 0 = go on.
    st: [u, arc, s_prev, dmin, vmin, fmin, n, ruler arc at the anchor, ruler length, anchor xyz]. With a ruler (rings),
    the arc is measured in chords of at least the ruler's length (the coastline effect: a rough remesh's wiggles would
    otherwise lengthen every ring)."""
    u, arc, s_prev = st[0], st[1], st[2]
    dv = X - Xp; dl = math.sqrt(dv @ dv)
    un = max(sX, u + kappa * dl); arcn = arc + dl; mv = False
    if st[8] > 0.0:                                              # in chords from the anchor: the envelope too
        ax0 = X[0] - st[9]; ax1 = X[1] - st[10]; ax2 = X[2] - st[11]; da = math.sqrt(ax0 * ax0 + ax1 * ax1 + ax2 * ax2)
        arcn = st[7] + da; mv = da >= st[8]; un = max(sX, st[12] + kappa * da, u)
    if gap:                                                      # a bridged gap: only its far end X is on the skin
        if (mode == 1 and abs(un - target) <= 1e-9) or (mode == 3 and abs(arcn - target) <= 1e-9):
            res[0] = 1.0; res[1] = target; res[2] = X[0]; res[3] = X[1]; res[4] = X[2]; res[5] = f; res[6] = arcn
            return 1
        if (mode == 0 or mode == 2):
            dx = X - Bq
            if math.sqrt(dx @ dx) < 1e-7:
                res[0] = 1.0; res[1] = un if mode == 0 else arcn; res[2] = X[0]; res[3] = X[1]; res[4] = X[2]; res[5] = f
                return 1
        if (mode == 1 and un >= target - 1e-9) or (mode == 3 and arcn >= target - 1e-9) or (mode == 5 and arcn > target):
            return 3
        if mode == 4:
            n = int(st[6])
            if n < outP.shape[0]:
                outP[n] = X; outF[n] = f; outU[n, 0] = un; outU[n, 1] = arcn; outU[n, 2] = 1.0; st[6] = n + 1
        if mv:
            st[7] = arcn; st[9] = X[0]; st[10] = X[1]; st[11] = X[2]; st[12] = un
        st[0] = un; st[1] = arcn; st[2] = sX; Xp[0] = X[0]; Xp[1] = X[1]; Xp[2] = X[2]
        return 0
    if mode == 1 and un >= target - 1e-9:
        if st[8] > 0.0:                                          # chords: u read linearly along the segment (as in the inverse)
            tt = min(1.0, max(0.0, (target - u) / (un - u))) if un > u else 0.0
        else:
            tt = 1.0
            if sX > s_prev:
                tA = (target - s_prev) / (sX - s_prev)
                if 0.0 <= tA < tt:
                    tt = tA
            if kappa * dl > 0.0:
                tB = (target - u) / (kappa * dl)
                if 0.0 <= tB < tt:
                    tt = tB
        Q = Xp + tt * dv
        res[0] = 1.0; res[1] = target; res[2] = Q[0]; res[3] = Q[1]; res[4] = Q[2]; res[5] = f; res[6] = arc + tt * dl
        return 1
    if mode == 3 and arcn >= target - 1e-9:
        tt = min(1.0, max(0.0, (target - arc) / (arcn - arc))) if arcn > arc else 0.0
        Q = Xp + tt * dv
        res[0] = 1.0; res[1] = target; res[2] = Q[0]; res[3] = Q[1]; res[4] = Q[2]; res[5] = f; res[6] = target
        return 1
    if mode == 0 or mode == 2 or mode == 5:
        if dl > 0.0:                                             # the closest approach so far
            tt = ((Bq - Xp) @ dv) / (dl * dl); tt = min(1.0, max(0.0, tt)); Q = Xp + tt * dv; dq = Q - Bq; dd = math.sqrt(dq @ dq)
            if mode == 0:
                val = (u + tt * (un - u)) if st[8] > 0.0 else max(s_prev + tt * (sX - s_prev), u + kappa * tt * dl)
            else:
                val = arc + tt * (arcn - arc)
            if mode != 5 and st[3] < MET and dd > st[3]:         # met: the cut passed the vertex (it is turned DTH off it)
                res[0] = 1.0; res[1] = st[4]; res[2] = Qm[0]; res[3] = Qm[1]; res[4] = Qm[2]; res[5] = st[5]
                return 1
            if dd < st[3]:
                st[3] = dd; Qm[0] = Q[0]; Qm[1] = Q[1]; Qm[2] = Q[2]; st[5] = f; st[4] = val
        if mode == 5 and arcn > target:
            return 2
    if mode == 4:
        n = int(st[6])
        if n < outP.shape[0]:
            outP[n] = X; outF[n] = f; outU[n, 0] = un; outU[n, 1] = arcn; outU[n, 2] = 0.0; st[6] = n + 1
    if mv:
        st[7] = arcn; st[9] = X[0]; st[10] = X[1]; st[11] = X[2]; st[12] = un
    st[0] = un; st[1] = arcn; st[2] = sX; Xp[0] = X[0]; Xp[1] = X[1]; Xp[2] = X[2]
    return 0


@njit(cache=True)
def _bridge(V, F, BN, BP, cf, r0, r9, wf, f, k, X, budget, used, nused, out):
    """the level set left the region at X on boundary edge k of face f: the nearest place along the region's edge
    (either way; the straight gap within budget, the path along the edge within 4 x budget) where it comes back in.
    out = (face, edge, t, gap); face -1 when there is none. Boundary edges already used by this walk (used[:nused],
    as 3 * face + edge) are passed over, so a walk never bridges back and forth."""
    out[0] = -1.0; best = budget
    for way in range(2):
        a = F[f, k]; b = F[f, (k + 1) % 3]
        d = (V[b] - X) if way == 0 else (X - V[a]); L = math.sqrt(d @ d)
        fe = BN[f, k, 0] if way == 0 else BP[f, k, 0]; ke = BN[f, k, 1] if way == 0 else BP[f, k, 1]
        for it in range(2000):
            if fe < 0 or L > 4.0 * budget or (fe == f and ke == k):
                break
            a1 = F[fe, ke]; b1 = F[fe, (ke + 1) % 3]; g1 = _lv(cf, r0, r9, wf, a1); g2 = _lv(cf, r0, r9, wf, b1)
            seen = False
            for q in range(nused):
                if used[q] == 3 * fe + ke:
                    seen = True
            if (g1 >= 0.0) != (g2 >= 0.0) and not seen:
                t1 = g1 / (g1 - g2); Y = V[a1] + t1 * (V[b1] - V[a1]); dd = Y - X; gap = math.sqrt(dd @ dd)
                if gap <= best:
                    best = gap; out[0] = fe; out[1] = ke; out[2] = t1; out[3] = gap
                break
            e = V[b1] - V[a1]; L += math.sqrt(e @ e)
            fn = BN[fe, ke, 0] if way == 0 else BP[fe, ke, 0]; kn = BN[fe, ke, 1] if way == 0 else BP[fe, ke, 1]; fe = fn; ke = kn


@njit(cache=True)
def _walk(V, F, NB, NBK, BN, BP, bridge, r0, r9, wf, sf, cf, f0, P0, mode, kappa, target, tv, tol, maxn, outP, outF, outU, res):
    """Walk the zero set of g = cf0 r0 + cf1 r9 + cf2 wf + cf3 (linear inside each triangle) from P0 in face f0.
    cf4..6: the half condition h = cf4 r0 + cf5 r9 > 0 (when cf6 > 0; a meridian ends where it reaches its axis);
    cf7..9: sigma = cf7 r0 + cf8 r9 + cf9 sf (the envelope's base); cf10..12: the first step leaves P0 toward larger
    e = cf10 r0 + cf11 r9 + cf12 sf. A vertex exactly on the zero set counts as positive (simulation of simplicity),
    so the walk is well defined through vertices. Where the set leaves the region, the walk goes on from the nearest
    place along the region's edge where it comes back in, if that is within `bridge` cm (a notch of the edge).
    mode 0: envelope, until vertex tv (value u)          1: envelope, until u >= target (the point)
         2: arc length, until vertex tv (value arc)      3: arc length, until arc >= target (the point)
         4: record the polyline (outP, outF = the face each segment ends in, outU = (u, arc))
         5: arc to the closest approach to the point outP[0] within arc <= target
    In modes 0 and 2 a walk that passes within tol of tv without meeting it returns the closest point (status 2).
    res: [status, value, x, y, z, face, total arc, steps]; status 1 met, 2 closest within tol, 0 ended (boundary or
    axis), -1 closed loop (total = its length), -2 degenerate."""
    for i in range(8):
        res[i] = 0.0
    a0, b0, c0 = F[f0, 0], F[f0, 1], F[f0, 2]
    e1 = V[b0] - V[a0]; e2 = V[c0] - V[a0]; ep = P0 - V[a0]
    d11 = e1 @ e1; d12 = e1 @ e2; d22 = e2 @ e2; p1 = ep @ e1; p2 = ep @ e2; den = d11 * d22 - d12 * d12
    lb = (d22 * p1 - d12 * p2) / den; lc = (d11 * p2 - d12 * p1) / den
    s0 = (1.0 - lb - lc) * _sg(cf, r0, r9, sf, a0) + lb * _sg(cf, r0, r9, sf, b0) + lc * _sg(cf, r0, r9, sf, c0)
    ruler = cf[13] if len(cf) > 13 else 0.0                     # rings: arc in chords of at least this (cm)
    st = np.array([s0, 0.0, s0, 1e300, 0.0, float(f0), 0.0, 0.0, ruler, P0[0], P0[1], P0[2], s0]); Xp = P0.copy(); Qm = P0.copy()
    Bq = outP[0].copy()
    if tv >= 0 and (mode == 0 or mode == 2):
        dx = P0 - V[tv]
        if math.sqrt(dx @ dx) < 1e-7:
            res[0] = 1.0; res[1] = s0 if mode == 0 else 0.0; res[2] = P0[0]; res[3] = P0[1]; res[4] = P0[2]; res[5] = f0
            return
        Bq = V[tv].copy()
    best = -1; be = -1e300
    for trial in range(4):                                       # P0 on an edge the cut runs beside: start in the face across
        fs = f0 if trial == 0 else NB[f0, trial - 1]
        if fs < 0:
            continue
        for k in range(3):
            a = F[fs, k]; b = F[fs, (k + 1) % 3]
            ga = _lv(cf, r0, r9, wf, a); gb = _lv(cf, r0, r9, wf, b)
            if (ga >= 0.0) != (gb >= 0.0):
                t = ga / (ga - gb); e = _ev(cf, r0, r9, sf, a) + t * (_ev(cf, r0, r9, sf, b) - _ev(cf, r0, r9, sf, a))
                if e > be:
                    be = e; best = k
        if best >= 0:
            f0 = fs; break
    if best < 0:
        res[0] = -2.0; return
    f = f0; kout = best; status = -2.0; br = np.zeros(4); nbr = 0; used = np.zeros(102, np.int64)
    a0, b0, c0 = F[f0, 0], F[f0, 1], F[f0, 2]
    h_prev = 1.0
    if cf[6] > 0:                                                # the half condition at P0 (barycentric in the start face)
        e1 = V[b0] - V[a0]; e2 = V[c0] - V[a0]; ep = P0 - V[a0]
        d11 = e1 @ e1; d12 = e1 @ e2; d22 = e2 @ e2; p1 = ep @ e1; p2 = ep @ e2; den = d11 * d22 - d12 * d12
        lb = (d22 * p1 - d12 * p2) / den; lc = (d11 * p2 - d12 * p1) / den
        h_prev = (1 - lb - lc) * (cf[4] * r0[a0] + cf[5] * r9[a0]) + lb * (cf[4] * r0[b0] + cf[5] * r9[b0]) + lc * (cf[4] * r0[c0] + cf[5] * r9[c0])
    for step in range(maxn):
        a = F[f, kout]; b = F[f, (kout + 1) % 3]
        ga = _lv(cf, r0, r9, wf, a); gb = _lv(cf, r0, r9, wf, b)
        t = ga / (ga - gb); X = V[a] + t * (V[b] - V[a])
        sX = _sg(cf, r0, r9, sf, a) + t * (_sg(cf, r0, r9, sf, b) - _sg(cf, r0, r9, sf, a))
        if ruler > 0.0 and cf[6] <= 0:                           # rings: the ruler here (sf carries it per vertex)
            st[8] = min(ruler, sf[a] + t * (sf[b] - sf[a]))
        if cf[6] > 0:
            ha = cf[4] * r0[a] + cf[5] * r9[a]; hb = cf[4] * r0[b] + cf[5] * r9[b]; hX = ha + t * (hb - ha)
            if ruler > 0.0:                                      # meridians: 0.15 x the distance from the axis
                st[8] = max(min(ruler, 0.15 * hX), 1e-3)
            if hX <= 0.0:                                        # the meridian reaches its axis inside this face: end there
                if h_prev > 0.0:
                    tau = h_prev / (h_prev - hX); Xa = Xp + tau * (X - Xp); sa_ = st[2] + tau * (sX - st[2])
                    r = _seg(st, Xp, Qm, Xa, sa_, f, mode, kappa, target, Bq, res, outP, outF, outU, False)
                    if r == 1:
                        res[7] = step; return
                status = 0.0; break
            h_prev = hX
        r = _seg(st, Xp, Qm, X, sX, f, mode, kappa, target, Bq, res, outP, outF, outU, False)
        if r == 1:
            res[7] = step; return
        if r == 2:
            status = 0.0; break
        nf = NB[f, kout]
        if nf < 0:
            if bridge <= 0.0 or nbr >= 50:
                status = 0.0; break
            used[2 * nbr] = 3 * f + kout
            _bridge(V, F, BN, BP, cf, r0, r9, wf, f, kout, X, bridge, used, 2 * nbr + 1, br)
            if br[0] < 0:
                status = 0.0; break
            fy = int(br[0]); ky = int(br[1]); ty = br[2]; used[2 * nbr + 1] = 3 * fy + ky; nbr += 1
            a = F[fy, ky]; b = F[fy, (ky + 1) % 3]; Y = V[a] + ty * (V[b] - V[a])
            if cf[6] > 0:
                if (cf[4] * r0[a] + cf[5] * r9[a]) * (1 - ty) + (cf[4] * r0[b] + cf[5] * r9[b]) * ty <= 0.0:
                    status = 0.0; break
            sY = _sg(cf, r0, r9, sf, a) + ty * (_sg(cf, r0, r9, sf, b) - _sg(cf, r0, r9, sf, a))
            r = _seg(st, Xp, Qm, Y, sY, fy, mode, kappa, target, Bq, res, outP, outF, outU, True)
            if r == 1:
                res[7] = step; return
            if r >= 2:
                status = 0.0; break
            nf = fy; kin = ky
        else:
            kin = NBK[f, kout]
        if nf == f0:                                             # back in the start face: a closed loop
            s0c = (1.0 - lb - lc) * _sg(cf, r0, r9, sf, a0) + lb * _sg(cf, r0, r9, sf, b0) + lc * _sg(cf, r0, r9, sf, c0)
            r = _seg(st, Xp, Qm, P0, s0c, f0, mode, kappa, target, Bq, res, outP, outF, outU, False)
            if r == 1:
                res[7] = step; return
            status = -1.0; break
        f = nf; kout = -1
        for k in range(3):
            if k == kin:
                continue
            a = F[f, k]; b = F[f, (k + 1) % 3]
            if (_lv(cf, r0, r9, wf, a) >= 0.0) != (_lv(cf, r0, r9, wf, b) >= 0.0):
                kout = k; break
        if kout < 0:
            status = -2.0; break
    res[0] = status; res[1] = st[0] if mode < 2 else st[1]; res[6] = st[1]; res[7] = st[6] if mode == 4 else 0
    if mode == 5 or ((mode == 0 or mode == 2) and st[3] <= max(tol, MET)):
        res[0] = status if mode == 5 else (1.0 if st[3] < MET else 2.0)
        res[1] = st[4]; res[2] = Qm[0]; res[3] = Qm[1]; res[4] = Qm[2]; res[5] = st[5]; res[7] = st[3]


def _boundary_links(F, NB):
    """for each boundary edge (f, k): the next and previous boundary edge along the region's edge, (face, edge)"""
    m = len(F); BN = -np.ones((m, 3, 2), np.int64); BP = -np.ones((m, 3, 2), np.int64)
    fb, kb = np.nonzero(NB < 0)
    if not len(fb):
        return BN, BP
    a = F[fb, kb]; b = F[fb, (kb + 1) % 3]; n = int(F.max()) + 1
    start = -np.ones((n, 2), np.int64); end = -np.ones((n, 2), np.int64)
    start[a] = np.c_[fb, kb]; end[b] = np.c_[fb, kb]
    BN[fb, kb] = start[b]; BP[fb, kb] = end[a]
    return BN, BP


@njit(cache=True, parallel=True)
def _disc_batch(V, F, NB, NBK, BN, BP, bridge, r0, r9, F0, P0, kappa, mode, TH, TG, TV, tol, ruler, out):
    """meridian walks, each from its own start P0[i] (face F0[i]) on its half-plane next to the pole: mode 0 per vertex
    TV[i] at angle TH[i] -> u; mode 1 per chart radius TG[i] at angle TH[i] -> the point. out[i] = res"""
    for i in prange(len(TH)):
        if F0[i] < 0:
            out[i, 0] = -3.0; continue
        c, s = math.cos(TH[i] + DTH), math.sin(TH[i] + DTH)
        cf = np.array([-s, c, 0.0, 0.0, c, s, 1.0, c, s, 0.0, c, s, 0.0, ruler])
        res = np.zeros(8); oP = np.zeros((1, 3)); oF = np.zeros(1, np.int64); oU = np.zeros((1, 3))
        _walk(V, F, NB, NBK, BN, BP, bridge, r0, r9, r0, r0, cf, F0[i], P0[i].copy(), mode, kappa, TG[i], TV[i], tol, 20000, oP, oF, oU, res)
        for k in range(8):
            out[i, k] = res[k]


@njit(cache=True, parallel=True)
def _tube_batch(V, F, NB, NBK, BN, BP, bridge, r0, r9, sv, F0, P0, sref, kappa, TH, TV, tol, ruler, out):
    """meridian walks from the reference ring (P0[i] in face F0[i], at angle TH[i]) to vertex TV[i]: the ring
    coordinate u (signed: distal + from the reference, proximal by the mirrored envelope)"""
    for i in prange(len(TH)):
        if F0[i] < 0:
            out[i, 0] = -3.0; continue
        v = TV[i]; c, s = math.cos(TH[i] + DTH), math.sin(TH[i] + DTH); sg = 1.0 if sv[v] >= sref else -1.0
        cf = np.array([-s, c, 0.0, 0.0, c, s, 1.0, 0.0, 0.0, sg, 0.0, 0.0, sg, ruler])
        res = np.zeros(8); oP = np.zeros((1, 3)); oF = np.zeros(1, np.int64); oU = np.zeros((1, 3))
        _walk(V, F, NB, NBK, BN, BP, bridge, r0, r9, sv, sv, cf, F0[i], P0[i].copy(), 0, kappa, 0.0, v, tol, 20000, oP, oF, oU, res)
        for k in range(8):
            out[i, k] = res[k]
        out[i, 1] = sg * res[1]


@njit(cache=True, parallel=True)
def _ring_batch(V, F, NB, NBK, BN, BP, bridge, r0, r9, uf, rl, aref, FQ, Q, U0, C0, TV, mode, tol, ruler, out):
    """walks round rings (level sets of uf) from their reference crossing Q[i] (face FQ[i]):
    mode 2: to vertex TV[i] (+ first, then -) -> c; mode 3: arc C0[i] (sign = direction; a closed ring wraps)"""
    ca, sa = math.cos(aref + DTH), math.sin(aref + DTH)
    for i in prange(len(U0)):
        if FQ[i] < 0:
            out[i, 0] = -3.0; continue
        res = np.zeros(8); oP = np.zeros((1, 3)); oF = np.zeros(1, np.int64); oU = np.zeros((1, 3))
        if mode == 3:
            sg = 1.0 if C0[i] >= 0 else -1.0
            if abs(C0[i]) < 1e-12:
                out[i, 0] = 1.0; out[i, 2] = Q[i, 0]; out[i, 3] = Q[i, 1]; out[i, 4] = Q[i, 2]; out[i, 5] = FQ[i]; continue
            cf = np.array([0.0, 0.0, 1.0, -(U0[i] + DU), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -sa * sg, ca * sg, 0.0, ruler])
            _walk(V, F, NB, NBK, BN, BP, bridge, r0, r9, uf, rl, cf, FQ[i], Q[i].copy(), 3, 0.0, abs(C0[i]), -1, tol, 20000, oP, oF, oU, res)
            if res[0] == -1.0 and res[6] > 0.0:
                _walk(V, F, NB, NBK, BN, BP, bridge, r0, r9, uf, rl, cf, FQ[i], Q[i].copy(), 3, 0.0, abs(C0[i]) % res[6], -1, tol, 20000, oP, oF, oU, res)
            for k in range(8):
                out[i, k] = res[k]
            continue
        cf = np.array([0.0, 0.0, 1.0, -(U0[i] + DU), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -sa, ca, 0.0, ruler])
        _walk(V, F, NB, NBK, BN, BP, bridge, r0, r9, uf, rl, cf, FQ[i], Q[i].copy(), 2, 0.0, 0.0, TV[i], tol, 20000, oP, oF, oU, res)
        keep = res.copy()                                        # + way round; then the - way: c is the shorter (signed)
        cf[10] = sa; cf[11] = -ca
        _walk(V, F, NB, NBK, BN, BP, bridge, r0, r9, uf, rl, cf, FQ[i], Q[i].copy(), 2, 0.0, 0.0, TV[i], tol, 20000, oP, oF, oU, res)
        pk = keep[0] == 1.0 or keep[0] == 2.0; pm = res[0] == 1.0 or res[0] == 2.0
        if pm and (not pk or (res[0] == 1.0 and keep[0] == 2.0) or (res[0] == keep[0] and res[1] < keep[1])):
            for k in range(8):
                out[i, k] = res[k]
            out[i, 1] = -res[1]
        else:
            for k in range(8):
                out[i, k] = keep[k]


@njit(cache=True, parallel=True)
def _seg_batch(V, F, NB, NBK, BN, BP, X, Y, Z, A, FA, B, N, out):
    """skin length between points A[i] (face FA[i]) and B[i]: the walk along the normal section through both (the
    plane holding A, B and their mean normal N[i]); out[i] = (arc at the closest approach to B, that distance)"""
    for i in prange(len(A)):
        d = B[i] - A[i]; ch = math.sqrt(d @ d)
        if ch < 1e-12 or FA[i] < 0:
            out[i, 0] = 0.0; out[i, 1] = 0.0 if ch < 1e-12 else 1e9; continue
        m0 = d[1] * N[i, 2] - d[2] * N[i, 1]; m1 = d[2] * N[i, 0] - d[0] * N[i, 2]; m2 = d[0] * N[i, 1] - d[1] * N[i, 0]
        mn = math.sqrt(m0 * m0 + m1 * m1 + m2 * m2)
        if mn < 1e-15:
            out[i, 0] = ch; out[i, 1] = 0.0; continue
        m0 /= mn; m1 /= mn; m2 /= mn
        cf = np.array([m0, m1, m2, -(m0 * A[i, 0] + m1 * A[i, 1] + m2 * A[i, 2]), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, d[0], d[1], d[2]])
        res = np.zeros(8); oP = np.zeros((1, 3)); oP[0] = B[i]; oF = np.zeros(1, np.int64); oU = np.zeros((1, 3))
        _walk(V, F, NB, NBK, BN, BP, 0.0, X, Y, Z, Z, cf, FA[i], A[i].copy(), 5, 0.0, 6.0 * ch + 0.5, -1, 0.0, 20000, oP, oF, oU, res)
        out[i, 0] = res[1]; out[i, 1] = res[7]


def skin_lengths(V, F, P, fP, segs):
    """the skin length of each segment (i, j) between surface points P (faces fP) of the mesh (V, F): the shortest of
    the walks along the sections through both ends by six planes (holding the two points and one of: their mean
    normal, either end's normal, the frame's X, Y or Z). Each walk is a path on the skin, so this is an upper bound of
    the geodesic, close to it for short segments (a single normal section over-reads a segment across a deep fold).
    NaN where no walk comes back to the far end within 0.01 cm."""
    V = np.ascontiguousarray(V, np.float64); F = np.ascontiguousarray(F, np.int64); NB, NBK = _topology(F); BN, BP = _boundary_links(F, NB)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-30)
    segs = np.asarray(segs, np.int64).reshape(-1, 2); a, b = segs[:, 0], segs[:, 1]
    nA, nB = fn[fP[a]], fn[fP[b]]; nB = np.where(((nA * nB).sum(1) < 0)[:, None], -nB, nB); Nm = nA + nB
    Nm /= np.maximum(np.linalg.norm(Nm, axis=1, keepdims=True), 1e-30)
    X, Y, Z = (np.ascontiguousarray(V[:, k]) for k in range(3)); A_ = np.ascontiguousarray(P[a], np.float64)
    B_ = np.ascontiguousarray(P[b], np.float64); fa = fP[a].astype(np.int64); L = np.full(len(segs), np.inf)
    for N in (Nm, nA, nB, np.tile([1.0, 0, 0], (len(segs), 1)), np.tile([0, 1.0, 0], (len(segs), 1)), np.tile([0, 0, 1.0], (len(segs), 1))):
        out = np.zeros((len(segs), 2)); _seg_batch(V, F, NB, NBK, BN, BP, X, Y, Z, A_, fa, B_, np.ascontiguousarray(N, np.float64), out)
        ok = out[:, 1] <= 0.01; L[ok] = np.minimum(L[ok], out[ok, 0])
    L[~np.isfinite(L)] = np.nan
    return L


def _bary(V, F, f, P):
    """barycentric coordinates of points P in faces f"""
    a, b, c = V[F[f, 0]], V[F[f, 1]], V[F[f, 2]]; e1, e2, ep = b - a, c - a, P - a
    d11, d12, d22 = (e1 * e1).sum(1), (e1 * e2).sum(1), (e2 * e2).sum(1); p1, p2 = (ep * e1).sum(1), (ep * e2).sum(1)
    den = d11 * d22 - d12 * d12; lb = (d22 * p1 - d12 * p2) / den; lc = (d11 * p2 - d12 * p1) / den
    return np.c_[1 - lb - lc, lb, lc]


class _Sub:
    """a chart's own mesh: the part's faces whose vertices all lie in the chart's region"""

    def __init__(self, V, F, vmask):
        fm = vmask[F].all(1); self.fidx = np.nonzero(fm)[0]; Fs = F[fm]
        self.vidx = np.unique(Fs); remap = -np.ones(len(V), np.int64); remap[self.vidx] = np.arange(len(self.vidx))
        self.V = np.ascontiguousarray(V[self.vidx], np.float64); self.F = np.ascontiguousarray(remap[Fs], np.int64)
        self.NB, self.NBK = _topology(self.F); self.BN, self.BP = _boundary_links(self.F, self.NB); self.caster = Caster(self.V, self.F)
        NBp, _ = _topology(np.ascontiguousarray(F, np.int64)); seam = (self.NB < 0) & (NBp[self.fidx] >= 0)   # an edge another region shares
        self.BN[seam] = -1; self.BP[seam] = -1                    # bridges cross notches of the part's own edge, never a seam
        for L_ in (self.BN, self.BP):
            to = L_[..., 0] >= 0; ff, kk = np.nonzero(to)
            hit = seam[L_[ff, kk, 0], L_[ff, kk, 1]]; L_[ff[hit], kk[hit]] = -1
        fn = np.cross(self.V[self.F[:, 1]] - self.V[self.F[:, 0]], self.V[self.F[:, 2]] - self.V[self.F[:, 0]])
        self.fn = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-30)


DISC_AXES = {"z": ("y", "x"), "x": ("y", "z"), "y": ("z", "x")}      # disc axis -> (angle 0, angle 90) frame axes


class SkinChart:
    """common to the chart kinds: region, grid levels, text, conditioning"""

    def __init__(self, spec, part, V, F, lm, vmask, field=None):
        self.spec, self.name, self.kind, self.part = spec, spec["name"], spec["kind"], part
        self.min_facing = float(spec.get("min_facing", 0.34))
        self.kappa = math.cos(math.radians(float(spec.get("turn_deg", 30.0))))
        self.bridge = float(spec.get("bridge_cm", 1.0))         # walks cross gaps of the region's edge up to this wide
        # tube charts read skin paths in chords of min(ruler_cm, 0.15 x the distance from the axis): a remesh's roughness and
        # mm-scale folds along a limb then do not lengthen rings or count as turns. Discs read exact arcs: their meridians
        # cross sharp folds (a breast's base), whose corners a chord would cut by an amount that depends on the mesh.
        self.ruler = float(spec.get("ruler_cm", 0.5 if spec["kind"] == "tube" else 0.0))
        self.vmask = np.asarray(vmask, bool); self.sub = _Sub(V, F, self.vmask); self.lm = lm
        self.setup(field)

    def text(self, p):
        a, b = self.coord_names
        return f"{self.part} {self.name} {a}={p[0]:.2f} {b}={p[1]:.2f}"

    def _facing(self, f, ncut):
        """transversality of the cut at points in faces f: |skin normal x the cut surface's normal| (1 = square)"""
        c = np.abs((self.sub.fn[f] * ncut).sum(1)); return np.sqrt(np.maximum(0.0, 1 - c * c))


class DiscChart(SkinChart):
    """meridians = planes through the axis (a landmark, a frame axis), walked from the pole (the outermost skin on
    the axis); u by the envelope on sigma = the distance from the axis; the chart (a90, a0) = u * the meridian's
    direction, angle 0 along the a0 axis, 90 along the a90 axis"""

    def setup(self, field):
        sp = self.spec; ax = sp.get("axis", "z"); S = self.sub
        if isinstance(ax, str):                                  # a frame axis: angle 0 / 90 along the table's axes
            a0n, a9n = DISC_AXES[ax]; d = np.eye(3)[AXES[ax]]; self.e0 = np.eye(3)[AXES[a0n]]; self.e9 = np.eye(3)[AXES[a9n]]
        else:                                                    # a landmark direction: angle 0 = +Z, 90 = +X made square to it
            d = _unit(self.lm[ax["to"]] - self.lm[ax["from"]]); e0, e9 = Address._e(None, d[None]); self.e0, self.e9 = e0[0], e9[0]
            a9n, a0n = ("xyz"[int(np.argmax(np.abs(self.e9)))], "xyz"[int(np.argmax(np.abs(self.e0)))])
        self.coord_names = (a9n, a0n)
        self.o = np.asarray(self.lm[sp["through"]], float); R = S.V - self.o
        self.r0 = np.ascontiguousarray(R @ self.e0); self.r9 = np.ascontiguousarray(R @ self.e9)
        sg = 1.0 if sp.get("from", "+") == "+" else -1.0; d = sg * d
        O = self.o + d * (np.abs(S.V - self.o).max() * 2 + 10)
        Q, _, f = S.caster.cast(O[None], -d[None])
        if f[0] < 0:
            raise ValueError(f"{self.part}/{self.name}: the axis misses the chart's skin")
        self.pole, self.fpole, self.d, self.far = Q[0], int(f[0]), d, O

    EPS = 1.2345e-4                                              # cm: a meridian starts this far off the axis, on its own half-plane

    def _starts(self, th):
        """each meridian's start: the skin under the point EPS off the axis toward angle th (a ray along the axis), so
        a walk never starts on a vertex or edge the pole happens to fall on"""
        O = self.far[None] + self.EPS * (np.cos(th + DTH)[:, None] * self.e0[None] + np.sin(th + DTH)[:, None] * self.e9[None])
        Q, _, f = self.sub.caster.cast(O, np.repeat(-self.d[None], len(th), 0))
        return f.astype(np.int64), np.ascontiguousarray(np.nan_to_num(Q))

    def _ncut(self, th):
        return np.cos(th)[:, None] * self.e9[None] - np.sin(th)[:, None] * self.e0[None]

    def params_of_vertices(self, tol):
        S = self.sub; vv = np.arange(len(S.V)); th = np.arctan2(self.r9, self.r0); f0, P0 = self._starts(th)
        out = np.zeros((len(vv), 8))
        _disc_batch(S.V, S.F, S.NB, S.NBK, S.BN, S.BP, self.bridge, self.r0, self.r9, f0, P0, self.kappa, 0, th, np.zeros(len(vv)), vv, tol, self.ruler, out)
        ok = (out[:, 0] == 1) | (out[:, 0] == 2); u = out[:, 1]
        prm = np.full((len(vv), 2), np.nan); prm[ok] = np.c_[u[ok] * np.sin(th[ok]), u[ok] * np.cos(th[ok])]
        at = np.hypot(self.r0, self.r9) < self.EPS                # on the axis: the pole's own address
        prm[at & (np.linalg.norm(S.V - self.pole, axis=1) <= tol)] = 0.0
        return prm

    def resolve(self, prm):
        S = self.sub; prm = np.atleast_2d(np.asarray(prm, float)); th = np.arctan2(prm[:, 0], prm[:, 1]); uu = np.hypot(prm[:, 0], prm[:, 1])
        f0, P0 = self._starts(th); out = np.zeros((len(prm), 8))
        _disc_batch(S.V, S.F, S.NB, S.NBK, S.BN, S.BP, self.bridge, self.r0, self.r9, f0, P0, self.kappa, 1, th, uu, -np.ones(len(prm), np.int64), 0.0, self.ruler, out)
        pole = uu < self.EPS; out[pole, 0] = 1.0; out[pole, 2:5] = self.pole; out[pole, 5] = self.fpole
        ok = out[:, 0] == 1; Q = np.full((len(prm), 3), np.nan); Q[ok] = out[ok, 2:5]; f = np.where(ok, out[:, 5], -1).astype(np.int64)
        fa = np.full(len(prm), np.nan); fa[ok] = self._facing(f[ok], self._ncut(th[ok]))
        return Q, f, fa

    def lattice(self, level, prm_v):
        st = float(level["step_cm"]); lo = np.floor(np.nanmin(prm_v, 0) / st) - 1; hi = np.ceil(np.nanmax(prm_v, 0) / st) + 1
        A = np.arange(lo[0], hi[0] + 1) * st; B = np.arange(lo[1], hi[1] + 1) * st
        AA, BB = np.meshgrid(A, B, indexing="ij"); return np.c_[AA.ravel(), BB.ravel()], (len(A), len(B)), False


class TubeChart(SkinChart):
    """meridians = half-planes round a landmark polyline (the legacy tube's axis, blended at the joints), walked from
    a reference ring; u by the envelope on sigma = the station along the axis; c = the arc length round the ring
    (the level set of u) from the reference meridian (angle c_from_deg: 0 = +Z, 90 = +X), + toward increasing angle,
    the shorter way round (so a ring cut open on its far side, e.g. where a remesh fuses skin that touches, moves
    only the places at the cut), read in chords of min(ring_ruler_cm, 0.15 x the distance from the axis)"""
    coord_names = ("s", "c")

    def setup(self, field):
        sp = self.spec; S = self.sub
        self.axis = Address.__new__(Address); self.axis.spec = {k: sp[k] for k in ("blend_cm", "before_cm", "after_cm") if k in sp}
        self.axis._tube_setup(np.array([self.lm[n] for n in sp["through"]]))
        st = lambda p: float(self.axis.tube_station(np.asarray(p, float)[None])[0])
        ref = sp.get("ref", {"fraction": 0.5})
        if "mid" in ref:
            self.sref = st(0.5 * (self.lm[ref["mid"][0]] + self.lm[ref["mid"][1]]))
        elif "at" in ref:
            self.sref = st(self.lm[ref["at"]])
        elif "fraction" in ref:
            self.sref = float(ref["fraction"]) * self.axis.ts[-1]
        else:
            self.sref = float(ref["cm"])
        self.aref = math.radians(float(sp.get("c_from_deg", 0.0)))
        s = self.axis.tube_station(S.V); self.sv = np.ascontiguousarray(np.nan_to_num(s, nan=-1e6))
        C = self.axis._c(np.nan_to_num(s)); d = self.axis._d(np.nan_to_num(s)); e0, e9 = self.axis._e(d); R = S.V - C
        self.e0, self.e9 = e0, e9
        self.r0 = np.ascontiguousarray((R * e0).sum(1)); self.r9 = np.ascontiguousarray((R * e9).sum(1)); self.sok = np.isfinite(s)
        # the ruler for c: at most ring_ruler_cm, and 0.15 x the distance from the axis (a chord short of its arc by <= 0.1 %)
        self.rl = np.ascontiguousarray(np.maximum(0.15 * np.hypot(self.r0, self.r9), 1e-3))
        self.uf = None if field is None else np.ascontiguousarray(field, np.float64)
        if self.uf is None:
            self.uf = self._ring_field()
        self._ref_polyline()

    def _ring_field(self, tol=0.0):
        """u at every chart vertex: the envelope along its meridian from the reference ring; where that meridian
        does not reach (cut off by the region's edge), the station plus the harmonic extension of the reached
        corrections (u - station)"""
        S = self.sub; n = len(S.V); a = np.arctan2(self.r9, self.r0)
        O, D = self.axis.tube_rays(np.full(n, self.sref + 1.2345e-4), np.degrees(a + DTH)); Q, _, f = S.caster.cast(O, D)
        out = np.zeros((n, 8))
        _tube_batch(S.V, S.F, S.NB, S.NBK, S.BN, S.BP, self.bridge, self.r0, self.r9, self.sv, f.astype(np.int64), np.ascontiguousarray(np.nan_to_num(Q)),
                    self.sref, self.kappa, a, np.arange(n), tol, self.ruler, out)
        ok = (out[:, 0] == 1) & self.sok; u = np.where(ok, out[:, 1], np.nan); self.u_walked = ok
        if (~ok).any() and ok.any():
            from scipy.sparse import coo_matrix
            from scipy.sparse.linalg import spsolve
            E = np.r_[S.F[:, [0, 1]], S.F[:, [1, 2]], S.F[:, [2, 0]]]; E = np.unique(np.sort(E, 1), axis=0)
            W = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(n, n)).tocsr()
            unk = np.nonzero(~ok)[0]; kn = np.nonzero(ok)[0]
            L = (coo_matrix((np.asarray(W.sum(1)).ravel(), (np.arange(n), np.arange(n))), shape=(n, n)) - W).tocsr()
            dl_ = u - self.sv                                    # fill the correction (u - station), not u: 0 where the skin
            Luu = L[unk][:, unk]; rhs = -L[unk][:, kn] @ dl_[kn]  # runs along the limb, so a filled place reads its station
            reach = np.asarray(W[unk][:, kn].sum(1)).ravel() > 0                       # pin components with no known rim
            from scipy.sparse.csgraph import connected_components
            ncomp, lab = connected_components(W[unk][:, unk], directed=False)
            has = np.bincount(lab, weights=reach.astype(float), minlength=ncomp) > 0
            keep = has[lab]
            if keep.any():
                # per cut-off component: where its rim runs along the limb (median correction under 0.05 cm: e.g. a forearm
                # a remesh fused to the body) the station plus the filled correction; where the rim itself turns (a
                # junction fold) or a place has no station, the harmonic fill of u
                A_ = Luu[keep][:, keep].tocsc(); fd = self.sv[unk[keep]] + spsolve(A_, rhs[keep]); fu = spsolve(A_, -L[unk][:, kn][keep] @ u[kn])
                Wk = W[unk[keep]][:, kn]; rr_, cc_ = Wk.nonzero(); lab_k = lab[keep]
                rim_c = lab_k[rr_]; rim_v = np.abs(dl_[kn][cc_]); comp_d = np.full(ncomp, np.inf)
                for k_ in np.unique(rim_c):                      # the component's rim: its median correction
                    comp_d[k_] = np.median(rim_v[rim_c == k_])
                use_d = (comp_d[lab_k] <= 0.05) & self.sok[unk[keep]]
                u[unk[keep]] = np.where(use_d, fd, fu)
        return np.ascontiguousarray(np.nan_to_num(u, nan=-1e6))

    def _ref_polyline(self):
        """the reference meridian from its proximal end to its distal end, with u (the field, interpolated) along it"""
        S = self.sub; ca, sa = math.cos(self.aref + DTH), math.sin(self.aref + DTH)
        O, D = self.axis.tube_rays(np.array([self.sref + 1.2345e-4]), np.array([math.degrees(self.aref + DTH)])); Q, _, f = S.caster.cast(O, D)
        if f[0] < 0:
            raise ValueError(f"{self.part}/{self.name}: the reference meridian misses the chart's skin")
        Pr, fr = Q[0], int(f[0]); parts = []
        for sg in (-1.0, 1.0):                                   # distal: on over a cap's pole, so rings round its top cross it
            cf = np.array([-sa, ca, 0.0, 0.0, ca, sa, 1.0 if sg < 0 else 0.0, 0.0, 0.0, sg, 0.0, 0.0, sg, self.ruler]); res = np.zeros(8)
            oP = np.zeros((20000, 3)); oF = np.zeros(20000, np.int64); oU = np.zeros((20000, 3))
            _walk(S.V, S.F, S.NB, S.NBK, S.BN, S.BP, self.bridge, self.r0, self.r9, self.sv, self.sv, cf, fr, Pr.copy(), 4, self.kappa, 0.0, -1, 0.0, 20000, oP, oF, oU, res)
            k = int(res[7]); parts.append((oP[:k], oF[:k], oU[:k, 2] > 0))
        (Pp, Fp, Gp), (Pd, Fd, Gd) = parts
        self.rP = np.r_[Pp[::-1], Pr[None], Pd]; self.rk0 = len(Pp)                    # rk0: the reference ring's crossing
        self.rFseg = np.r_[Fp[1:][::-1], Fp[:1], Fd[:1], Fd[1:]].astype(np.int64)     # segment k (rP[k] -> rP[k+1]) lies in this face
        self.rGap = np.r_[Gp[::-1], Gd].astype(bool)                                  # ... or crosses a bridged gap
        Fpt = np.r_[Fp[::-1], [fr], Fd].astype(np.int64)
        self.rU = (_bary(S.V, S.F, Fpt, self.rP) * self.uf[S.F[Fpt]]).sum(1)

    def ring_starts(self, u0):
        """the crossing of each ring u0 with the reference meridian, walking out from the reference station:
        (face, point); face -1 where the ring does not reach the reference meridian"""
        u0 = np.atleast_1d(np.asarray(u0, float)); U = self.rU; n = len(U)
        fq = -np.ones(len(u0), np.int64); Q = np.zeros((len(u0), 3)); k0 = self.rk0
        fin = np.isfinite(u0); dist = fin & (u0 >= U[k0]); prox = fin & (u0 < U[k0])
        if dist.any():                                   # distal: the first segment after k0 whose end reaches u0
            Um = np.maximum.accumulate(U[k0:]); j = np.searchsorted(Um, u0[dist], side="left")
            okj = (j >= 1) & (j < len(Um)); k = k0 + j[okj] - 1; ii = np.nonzero(dist)[0][okj]
            t = (u0[ii] - U[k]) / (U[k + 1] - U[k]); fq[ii] = np.where(self.rGap[k], -1, self.rFseg[k])
            Q[ii] = self.rP[k] + t[:, None] * (self.rP[k + 1] - self.rP[k])
            at = np.nonzero(dist)[0][j == 0]; fq[at] = self.rFseg[min(k0, n - 2)]; Q[at] = self.rP[k0]
        ends = fin & (fq < 0)                            # a ring at the reference line's open end, or round a cap's top
        km = k0 + int(np.argmax(U[k0:]))
        for e_, k_ in ((0, 0), (km, min(km, n - 2))):
            m_ = ends & (np.abs(u0 - U[e_]) <= 1e-5) if n > 1 else ends & False
            fq[m_] = -1 if self.rGap[k_] else self.rFseg[k_]; Q[m_] = self.rP[e_]
        if prox.any():                                   # proximal: the first segment before k0 whose start reaches u0
            Um = np.minimum.accumulate(U[k0::-1]); j = np.searchsorted(-Um, -u0[prox], side="left")
            okj = (j >= 1) & (j < len(Um)) & (fq[prox] < 0); k = k0 - j[okj]; ii = np.nonzero(prox)[0][okj]
            t = (u0[ii] - U[k]) / (U[k + 1] - U[k]); fq[ii] = np.where(self.rGap[k], -1, self.rFseg[k])   # not in a bridged gap
            Q[ii] = self.rP[k] + t[:, None] * (self.rP[k + 1] - self.rP[k])
        return fq, Q

    def _ncut(self, f, P):
        """the meridian surface's normal (the direction of increasing angle) at points P in faces f"""
        S = self.sub; w = _bary(S.V, S.F, f, P); r0 = (w * self.r0[S.F[f]]).sum(1); r9 = (w * self.r9[S.F[f]]).sum(1)
        e0 = (w[:, :, None] * self.e0[S.F[f]]).sum(1); e9 = (w[:, :, None] * self.e9[S.F[f]]).sum(1); a = np.arctan2(r9, r0)
        n = -np.sin(a)[:, None] * e0 + np.cos(a)[:, None] * e9; return n / np.linalg.norm(n, axis=1, keepdims=True)

    def params_of_vertices(self, tol):
        S = self.sub; n = len(S.V); u = self.uf; ok = u > -1e5
        fq, Q = self.ring_starts(np.where(ok, u, np.nan)); out = np.zeros((n, 8))
        _ring_batch(S.V, S.F, S.NB, S.NBK, S.BN, S.BP, self.bridge, self.r0, self.r9, u, self.rl, self.aref, fq, Q, u, np.zeros(n), np.arange(n), 2, tol, self.ruler, out)
        good = ok & ((out[:, 0] == 1) | (out[:, 0] == 2)); prm = np.full((n, 2), np.nan); prm[good] = np.c_[u[good], out[good, 1]]
        return prm

    def resolve(self, prm):
        S = self.sub; prm = np.atleast_2d(np.asarray(prm, float)); fq, Q = self.ring_starts(prm[:, 0]); out = np.zeros((len(prm), 8))
        _ring_batch(S.V, S.F, S.NB, S.NBK, S.BN, S.BP, self.bridge, self.r0, self.r9, self.uf, self.rl, self.aref, fq, Q, prm[:, 0].copy(), prm[:, 1].copy(),
                    np.zeros(len(prm), np.int64), 3, 0.0, self.ruler, out)
        ok = out[:, 0] == 1; P = np.full((len(prm), 3), np.nan); P[ok] = out[ok, 2:5]; f = np.where(ok, out[:, 5], -1).astype(np.int64)
        fa = np.full(len(prm), np.nan)
        if ok.any():
            fa[ok] = self._facing(f[ok], self._ncut(f[ok], P[ok]))
        return P, f, fa

    def ring_lengths(self, u0):
        """the length of each ring u0 from its reference crossing (+ way); closed rings: the loop's length, open:
        (+ arc to the edge, - arc to the edge)"""
        S = self.sub; fq, Q = self.ring_starts(u0); out = np.zeros((len(u0), 4))
        for i in range(len(u0)):
            if fq[i] < 0:
                out[i] = np.nan; continue
            for j, sg in enumerate((1.0, -1.0)):
                ca, sa = math.cos(self.aref + DTH), math.sin(self.aref + DTH)
                cf = np.array([0.0, 0.0, 1.0, -(u0[i] + DU), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -sa * sg, ca * sg, 0.0, self.ruler]); res = np.zeros(8)
                _walk(S.V, S.F, S.NB, S.NBK, S.BN, S.BP, self.bridge, self.r0, self.r9, self.uf, self.rl, cf, int(fq[i]), Q[i].copy(), 3, 0.0, 1e9, -1, 0.0, 40000,
                      np.zeros((1, 3)), np.zeros(1, np.int64), np.zeros((1, 3)), res)
                out[i, 2 * j] = res[6]; out[i, 2 * j + 1] = res[0]
                if res[0] == -1.0:
                    break
        return out

    def lattice(self, level, prm_v):
        """rings every step of u; points every step of c round each ring (0 .. < the loop's length on a closed ring,
        both ways to the edges on an open one)"""
        st = float(level["step_cm"]); ok = np.isfinite(prm_v).all(1)
        U = np.arange(math.ceil(np.nanmin(prm_v[ok, 0]) / st), math.floor(np.nanmax(prm_v[ok, 0]) / st) + 1) * st
        L = self.ring_lengths(U); pts, rings = [], []
        for i, u0 in enumerate(U):
            if not np.isfinite(L[i, 0]):
                continue
            if L[i, 1] == -1.0:                                                       # closed: divided evenly, c signed the
                nn = max(1, int(round(L[i, 0] / st))); cs = np.arange(nn) * (L[i, 0] / nn); closed = nn > 2   # shorter way round
                cs = np.where(cs > L[i, 0] / 2 + 1e-9, cs - L[i, 0], cs)
            else:
                cs = np.r_[-np.arange(st, L[i, 2] + 1e-9, st)[::-1], np.arange(0, L[i, 0] + 1e-9, st)]; closed = False
            rings.append((len(pts), len(cs), closed)); pts += [(u0, c) for c in cs]
        return np.array(pts, float).reshape(-1, 2), rings, True


def _make_chart(spec, part, V, F, lm, vmask, field=None):
    return {"disc": DiscChart, "tube": TubeChart}[spec["kind"]](spec, part, V, F, lm, vmask, field)


class SkinAtlas:
    """a part's skin charts, in order: each vertex is addressed by the first chart whose region holds it and whose
    address resolves back onto it (within TOL_CM); the grid is every chart's lattice"""

    def __init__(self, specs, part, V, F, lm, regions, fields=None):
        self.part, self.V, self.F = part, V, F; fields = fields or {}
        self.charts = [_make_chart(sp, part, V, F, lm, regions[sp["name"]], fields.get(sp["name"])) for sp in specs]
        self.by_name = {c.name: c for c in self.charts}

    def vertex_addresses(self):
        n = len(self.V); chart = -np.ones(n, np.int64); prm = np.full((n, 2), np.nan); err = np.full(n, np.inf); stats = {}
        for k, c in enumerate(self.charts):
            S = c.sub; p = c.params_of_vertices(TOL_CM); ok = np.isfinite(p).all(1)
            Q = np.full((len(p), 3), np.nan)
            if ok.any():
                Q[ok], _, _ = c.resolve(p[ok])
            e = np.linalg.norm(Q - S.V, axis=1); e[~np.isfinite(e)] = np.inf
            take = (e <= TOL_CM) & (chart[S.vidx] < 0)
            chart[S.vidx[take]] = k; prm[S.vidx[take]] = p[take]; err[S.vidx[take]] = e[take]
            better = (chart[S.vidx] < 0) & (e < err[S.vidx]); err[S.vidx[better]] = e[better]
            stats[c.name] = {"region_vertices": int(len(S.V)), "addressed_here": int(take.sum()),
                             "round_trip_failed": int(((e > TOL_CM) & ok).sum()), "no_walk": int((~ok).sum())}
        return chart, prm, err, stats

    def grid(self, prm_v, chart_v, zones):
        """lattice points of every chart and level, resolved; names, params, chart index, level, faces (in the
        part's mesh), facing, and the lines (index lists; a closed ring wraps)"""
        P, names, prm_l, ch_l, lev_l, f_l, fa_l, lines = [], [], [], [], [], [], [], []; owner = cKDTree(self.V)
        for k, c in enumerate(self.charts):
            levels = c.spec.get("grid", [{"step_cm": 1.0}]); pv = prm_v[chart_v == k]
            if not np.isfinite(pv).any():
                continue
            regions = []
            for lv in levels:                                    # a finer level's region: near its zone's vertices
                if "near" in lv:
                    zp = prm_v[zones[(c.name, levels.index(lv))] & (chart_v == k)]; zp = zp[np.isfinite(zp).all(1)]
                    regions.append(cKDTree(zp) if len(zp) else None)
                else:
                    regions.append(None)
            for li, lv in enumerate(levels):
                cand, shape, tube = c.lattice(lv, pv)
                if not len(cand):
                    continue
                keep = np.ones(len(cand), bool)
                if regions[li] is not None:
                    keep &= regions[li].query(cand)[0] <= float(lv.get("margin_cm", 0.0)) + 1e-9
                for lj in range(li + 1, len(levels)):            # a finer level takes over its region
                    if regions[lj] is not None:
                        keep &= ~(regions[lj].query(cand)[0] <= float(levels[lj].get("margin_cm", 0.0)) + 1e-9)
                Q = np.full((len(cand), 3), np.nan); f = -np.ones(len(cand), np.int64); fa = np.full(len(cand), np.nan)
                if keep.any():
                    Q[keep], f[keep], fa[keep] = c.resolve(cand[keep])
                good = keep & np.isfinite(Q).all(1) & (fa >= c.min_facing)
                if good.any() and len(self.charts) > 1:          # overlapping regions: drawn by the chart that addresses the place
                    good[good] &= chart_v[owner.query(Q[good])[1]] == k
                idx = -np.ones(len(cand), np.int64); base = len(P); idx[good] = base + np.arange(good.sum())
                for i in np.nonzero(good)[0]:
                    P.append(Q[i]); prm_l.append(cand[i]); names.append(c.text(cand[i])); ch_l.append(k); lev_l.append(li)
                    f_l.append(c.sub.fidx[f[i]]); fa_l.append(fa[i])
                runs = []
                if not tube:
                    I = idx.reshape(shape); runs = [(r, False) for r in I] + [(r, False) for r in I.T]
                else:                                            # rings; along the limb: each point to the nearest on the next ring
                    rings = shape; st = float(lv["step_cm"])
                    for (s0, nn, closed) in rings:
                        runs.append((idx[s0:s0 + nn], closed))
                    nxt = {}
                    for (s0, n0, _), (s1, n1, _) in zip(rings[:-1], rings[1:]):
                        if abs(cand[s1, 0] - cand[s0, 0] - st) > 1e-6:
                            continue
                        a_ = [j for j in range(s0, s0 + n0) if idx[j] >= 0]; b_ = [j for j in range(s1, s1 + n1) if idx[j] >= 0]
                        if not a_ or not b_:
                            continue
                        Pa = np.array([P[idx[j]] for j in a_]); Pb = np.array([P[idx[j]] for j in b_])
                        small, big, Ps, Pg = (a_, b_, Pa, Pb) if len(a_) <= len(b_) else (b_, a_, Pb, Pa)
                        dd, jj = cKDTree(Pg).query(Ps); best = {}
                        for i_s, (d_, j_) in enumerate(zip(dd, jj)):
                            if d_ <= 2.5 * st and (j_ not in best or d_ < best[j_][0]):
                                best[j_] = (d_, i_s)
                        for j_, (d_, i_s) in best.items():
                            pa_, pb_ = (small[i_s], big[j_]) if small is a_ else (big[j_], small[i_s])
                            nxt[idx[pa_]] = idx[pb_]
                    has_prev = set(nxt.values())
                    for start in [k_ for k_ in nxt if k_ not in has_prev]:
                        chain = [start]
                        while chain[-1] in nxt:
                            chain.append(nxt[chain[-1]])
                        runs.append((np.array(chain), False))
                for row, wrap in runs:
                    run = []
                    for v in list(row) + ([row[0]] if wrap and len(row) else []):
                        if v >= 0:
                            run.append(int(v))
                        else:
                            if len(run) > 1:
                                lines.append(run)
                            run = []
                    if len(run) > 1:
                        lines.append(run)
        return (np.array(P, float).reshape(-1, 3), names, np.array(prm_l, float).reshape(-1, 2), np.array(ch_l, np.int64),
                np.array(lev_l, np.int64), np.array(f_l, np.int64), np.array(fa_l, float), lines)

    def resolve(self, name, prm):
        c = self.by_name[name]; Q, f, fa = c.resolve(prm)
        return Q, fa


_ADDR = re.compile(r"(?P<part>[A-Za-z0-9_]+)\s+(?P<kind>h\+|h-|[a-z][a-z0-9_]*)\s+(?P<kv>(?:[a-z]+=[-+0-9.eE]+\s*)+)")


def parse_address(text):
    m = _ADDR.search(text)
    if not m:
        raise ValueError(f"no address in: {text!r}")
    kv = dict((k, float(v)) for k, v in re.findall(r"([a-z]+)=([-+0-9.eE]+)", m.group("kv")))
    return m.group("part"), m.group("kind"), kv


# ------------------------------------------------------------------------------------------------------ the build
def build_part(entry, src, side, name, defs_meta, log=print):
    t0 = time.time(); P = Part(entry, src, side, name)
    for lname, lspec in entry["landmarks"].items():                 # in order: later ones may use earlier ones
        P.lm[lname] = P.landmark(lspec)
    P.build_frame()
    sel = P.select(entry["select"])
    if entry.get("largest_component", True):
        sel = _largest_component(src.F, sel)
    fmask = sel[src.F].all(1); Fs = src.F[fmask]
    vid = np.unique(Fs); P.part = np.zeros(len(src.V), bool); P.part[vid] = True; remap = -np.ones(len(src.V), np.int64); remap[vid] = np.arange(len(vid))
    Vf = P.to_frame(src.V[vid]).astype(np.float32).astype(np.float64); Ff = remap[Fs]   # as stored: a reload resolves alike
    lmf = {k: P.to_frame(v[None])[0] for k, v in P.lm.items()}
    A = Address(entry["address"], name, Vf, Ff, lmf)                 # build 09's address system: still resolves
    skin = entry.get("skin"); extra = {}
    if skin:                                                          # build 10: the skin charts name places and draw the grid
        regions, zones = {}, {}
        for sp in skin["charts"]:
            regions[sp["name"]] = P.select(sp["region"])[vid] if "region" in sp else np.ones(len(vid), bool)
            for li, lv in enumerate(sp.get("grid", [])):
                if "near" in lv:
                    zones[(sp["name"], li)] = P.select(lv["near"])[vid]
        SA = SkinAtlas(skin["charts"], name, Vf, Ff, lmf, regions)
        aside, prm, aerr, cstats = SA.vertex_addresses()
        legacy_used = 0
        if (aside < 0).any():                                    # left over (a rim beyond a notch): build 09's kind if it round-trips
            lp, ls, le = A.vertex_addresses(); take = (aside < 0) & (ls >= 0)
            aside[take] = len(SA.charts) + ls[take]; prm[take] = lp[take]; aerr[take] = le[take]; legacy_used = int(take.sum())
        gP, gnames, gprm, gside, glev, gface, gfa, glines = SA.grid(prm, aside, zones)
        spacing = grid_spacing(Vf, Ff, gP, gface, glines, [c.spec.get("grid", [{"step_cm": 1.0}]) for c in SA.charts], gside, glev)
        for c in SA.charts:
            extra["chart_region_" + c.name] = regions[c.name].astype(np.uint8)
            if c.kind == "tube":
                u = np.full(len(vid), np.nan); u[c.sub.vidx] = c.uf; extra["chart_u_" + c.name] = u
        extra.update(grid_level=glev.astype(np.int8), grid_face=gface.astype(np.int32))
    else:
        SA = None; prm, aside, aerr = A.vertex_addresses()
        gP, gnames, gprm, gside, glines = A.grid()
    fields = {}
    for fname, fspec in entry.get("fields", {}).items():
        fields[fname] = _field(P, fspec, vid)
    meas = {}
    for mname, mspec in entry.get("measures", {}).items():
        try:
            meas[mname] = _measure(P, A, mspec, src.V[vid], Vf, Ff)
        except Exception as ex:                                       # a measure that cannot be read is reported, not hidden
            meas[mname] = {"error": f"{type(ex).__name__}: {ex}"}
        if "source" in mspec:
            meas[mname]["source"] = mspec["source"]
        if "what" in mspec:
            meas[mname]["definition"] = mspec["what"]
    overlays = {}
    for oname, ospec in entry.get("overlays", {}).items():
        overlays[oname] = _overlay(P, ospec)
    info = {
        "part": name, "definition": entry.get("_key"), "side": side, "source": src.label, "source_name": src.name,
        "definitions_file": defs_meta["path"], "definition_sha1": _sha1(entry)[:12],
        "built": datetime.datetime.now().isoformat(timespec="seconds"), "seconds": None,
        "units": "cm", "axes": entry.get("axes_names", {"x": "lateral", "y": "superior", "z": "anterior"}),
        "handedness": "mirrored (left-handed) so lateral is +X on both sides" if P.s < 0 else "right-handed",
        "frame": {"origin_source": P.o.tolist(), "R_rows_source": P.R.tolist(), "source_units_to_cm": src.to_cm,
                  "to_frame": "q_cm = (p_source - origin_source) @ R_rows_source.T * source_units_to_cm",
                  "checks": P.frame_checks},
        "landmarks_cm": {k: [round(float(x), 3) for x in v] for k, v in lmf.items()},
        "landmarks_source": {k: [float(x) for x in v] for k, v in P.lm.items()},
        "landmark_definitions": entry["landmarks"],
        "address": ({**entry["address"], "syntax": _syntax(A), "round_trip_tol_cm": TOL_CM,
                     "vertices_with_address": int((aside >= 0).sum()), "vertices": int(len(Vf)), "grid_points": int(len(gP))}
                    if SA is None else {**entry["address"], "syntax": _syntax(A), "role": "build 09's address system, kept so "
                    "the addresses already in use (h+ / h- / tube) resolve to the same places; the grid and the vertex addresses "
                    "are the skin charts' (info.skin)"}),
        "skin": None if SA is None else {
            "charts": [{**c.spec, **cstats[c.name], "grid_points": int((gside == k).sum()),
                        **({"reference_station_cm": round(c.sref, 3), "ring_field_walked": int(c.u_walked.sum()),
                            "ring_field_filled": int((~c.u_walked & (c.uf > -1e5)).sum())} if c.kind == "tube" else {})}
                       for k, c in enumerate(SA.charts)],
            "syntax": _skin_syntax(SA), "why": skin.get("why", ""), "round_trip_tol_cm": TOL_CM,
            "vertices_with_address": int((aside >= 0).sum()), "vertices": int(len(Vf)), "grid_points": int(len(gP)),
            "vertices_with_a_skin_address": int(((aside >= 0) & (aside < len(SA.charts))).sum()),
            "vertices_with_a_build09_address_only": legacy_used, "grid_spacing": spacing},
        "address_systems": _address_systems(SA, A),
        "measures": meas,
        "counts": {"vertices": int(len(Vf)), "triangles": int(len(Ff))},
        "source_files": src.files, "what": entry.get("what", ""),
    }
    info["seconds"] = round(time.time() - t0, 1)
    data = dict(V=Vf.astype(np.float32), F=Ff.astype(np.int32), vid=vid.astype(np.int64), addr_params=prm.astype(np.float32),
                addr_side=aside.astype(np.int8), addr_err=np.minimum(aerr, 99).astype(np.float32),
                grid_P=gP.astype(np.float32), grid_params=gprm.astype(np.float32),
                grid_side=(np.asarray(gside, np.int8) if SA is not None else
                           np.array([A.sides().index(s) if s in A.sides() else 0 for s in gside], np.int8)),
                grid_names=np.array(gnames), grid_lines=_pack_lines(glines), **extra)
    for k, v in fields.items():
        data["field_" + k] = v.astype(np.float32)
    kinds = A.kind if SA is None else "skin (" + ", ".join(c.name for c in SA.charts) + ")"
    log(f"  {name}: {len(Vf)} vertices, {len(Ff)} triangles, {len(gP)} grid points, "
        f"{(aside >= 0).mean() * 100:.2f}% of vertices with a {kinds} address; {info['seconds']} s")
    P.atlas = SA
    return P, A, info, data, overlays


def _syntax(A):
    return {"height": "<part> h+|h- <a>=<cm> <b>=<cm>  (outermost surface along +/-up over the point)",
            "tube": "<part> tube s=<cm along the axis> a=<deg round it, 0 = +Z, 90 = +X>",
            "sphere": "<part> sphere lat=<deg from the equator toward +Y> lon=<deg, 0 = +Z, 90 = +X>"}[A.kind] + \
        "; any part: <part> xyz x= y= z= (nearest surface point)"


def _address_systems(SA, A):
    """the per-vertex addr_side index -> address system: the skin charts, then build 09's kind (one per side)"""
    out = [] if SA is None else [{"name": c.name, "kind": c.kind, "coords": list(c.coord_names)} for c in SA.charts]
    if A.kind == "height":
        ax = [n for n, a in AXES.items() if a in A._hij()]
        out += [{"name": "h" + sd, "kind": "height", "coords": ax, "build": 9} for sd in A.sides()]
    elif A.kind == "tube":
        out += [{"name": "tube", "kind": "tube_build09", "coords": ["s", "a"], "build": 9}]
    else:
        out += [{"name": "sphere", "kind": "sphere", "coords": ["lat", "lon"], "build": 9}]
    return out


def _skin_syntax(SA):
    out = {}
    for c in SA.charts:
        if c.kind == "disc":
            a, b = c.coord_names
            ax = c.spec.get("axis", "z"); axt = ax.upper() if isinstance(ax, str) else f"{ax['from']}-to-{ax['to']}"
            out[c.name] = (f"<part> {c.name} {a}=<cm> {b}=<cm>: walk on the skin from the {axt} axis "
                           f"through {c.spec['through']} along the section in the direction ({a}, {b}); the distance is the ring "
                           f"coordinate (= the frame's own {a}, {b} where the skin turns less than {c.spec.get('turn_deg', 30)} deg "
                           "from the frame; past that it keeps growing with the skin)")
        else:
            out[c.name] = (f"<part> {c.name} s=<cm> c=<cm>: s = the ring (= the station along the axis through "
                           f"{', '.join(c.spec['through'])} where the skin runs along it; past a turn of {c.spec.get('turn_deg', 30)} "
                           f"deg it keeps growing with the skin), c = cm along the ring from the line at {c.spec.get('c_from_deg', 0)} "
                           "deg (0 = +Z, 90 = +X), + toward increasing angle")
    out["any"] = "<part> xyz x= y= z= (nearest surface point); build 09's h+ / h- / tube addresses still resolve"
    return out


def grid_spacing(V, F, gP, gface, lines, levels, gchart, glev):
    """the skin length of every grid segment (normal-section walk), as a ratio of its level's step: how evenly the grid
    lies on the skin"""
    segs = np.array([(ln[k], ln[k + 1]) for ln in lines for k in range(len(ln) - 1)], np.int64).reshape(-1, 2)
    if not len(segs):
        return {}
    L = skin_lengths(V, F, gP, gface, segs)
    step = np.array([float(levels[gchart[a]][glev[a]]["step_cm"]) for a in segs[:, 0]]); r = L / step; ok = np.isfinite(r)
    out = {"segments": int(len(segs)), "measured": int(ok.sum()),
           "method": "skin length of each segment between neighbouring grid points: the walk along the normal section through "
                     "both (the plane holding them and their mean normal), divided by the level's step",
           "ratio": {"p1": round(float(np.percentile(r[ok], 1)), 3), "p50": round(float(np.median(r[ok])), 3),
                     "p99": round(float(np.percentile(r[ok], 99)), 3), "min": round(float(r[ok].min()), 3), "max": round(float(r[ok].max()), 3)},
           "over_1_5x_step": int((r[ok] > 1.5).sum()), "under_0_5x_step": int((r[ok] < 0.5).sum())}
    for st in sorted(set(step.tolist())):
        m = ok & (step == st)
        if m.any():
            out[f"step_{st:g}_cm"] = {"segments": int(m.sum()), "skin_cm_min": round(float(L[m].min()), 3),
                                     "skin_cm_p50": round(float(np.median(L[m])), 3), "skin_cm_max": round(float(L[m].max()), 3)}
    return out


def _pack_lines(lines):
    flat = [-1]
    for ln in lines:
        flat += ln + [-1]
    return np.array(flat, np.int32)


def _largest_component(F, sel):
    Fs = F[sel[F].all(1)]
    if len(Fs) == 0:
        return sel
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    n = sel.shape[0]; e = np.r_[Fs[:, [0, 1]], Fs[:, [1, 2]]]
    g = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n))
    _, lab = connected_components(g, directed=False)
    used = np.unique(Fs); big = np.bincount(lab[used]).argmax()
    return sel & (lab == big)


def _field(P, spec, vid):
    k, a = next(iter(spec.items()))
    if k == "above_grid_base":
        g = P.src.get_input(a, P.side); b, q = g.sample(g.base, P.src.V[vid])
        return (q[:, 2] - b) * P.src.to_cm
    if k == "input":
        return np.asarray(P.src.get_input(a, P.side), float)[vid]
    raise ValueError(f"unknown field {k}")


def _measure(P, A, spec, Vsrc, Vf, Ff):
    k, a = next((kk, vv) for kk, vv in spec.items() if kk not in ("source", "what"))
    lm = A.lm
    if k == "coord":
        n, ax = a; return {"value": round(float(lm[n][AXES[ax]]), 3), "unit": "cm"}
    if k == "distance":
        return {"value": round(float(np.linalg.norm(lm[a[0]] - lm[a[1]])), 3), "unit": "cm"}
    if k == "angle":                                               # angle at the middle landmark, 180 = straight
        u = lm[a[0]] - lm[a[1]]; v = lm[a[2]] - lm[a[1]]
        return {"value": round(math.degrees(math.acos(np.clip(_unit(u) @ _unit(v), -1, 1))), 2), "unit": "deg"}
    if k == "segment_angles":                                      # a segment's direction against the frame's planes
        d = _unit(lm[a[1]] - lm[a[0]])
        return {"toward_x_deg": round(math.degrees(math.atan2(d[0], -d[1])), 2), "toward_z_deg": round(math.degrees(math.atan2(d[2], -d[1])), 2),
                "unit": "deg", "note": "angles of the segment from -Y (straight down the part) toward +X (lateral) and toward +Z (anterior)"}
    if k == "plane_distance":                                      # a landmark's distance from a plane x = value (source frame)
        p = P.lm[a["point"]]; x0 = float(np.asarray(P.src.get_input(a["x"], P.side)).reshape(-1)[0])
        return {"value": round(abs(p[0] - x0) * P.src.to_cm, 3), "unit": "cm"}
    if k == "extent":                                              # of the part's own vertices only
        m = P.select(a["among"]) & P.part; X = P.to_frame(P.src.V[m])
        if "band" in a:
            b = a["band"]; c = lm[b["at"]][AXES[b["axis"]]]; X = X[np.abs(X[:, AXES[b["axis"]]] - c) <= b["half_cm"]]
        out = {"unit": "cm", "n_vertices": int(len(X))}
        for ax in a.get("axes", "xyz"):
            col = X[:, AXES[ax]]; out[ax] = {"min": round(float(col.min()), 3), "max": round(float(col.max()), 3),
                                             "width": round(float(col.max() - col.min()), 3)}
        return out
    if k == "grid_volume":
        g = P.src.get_input(a, P.side); H = np.where(g.mask, g.top - g.base, 0.0)
        return {"value": round(float(np.nansum(H) * g.step ** 2 * (P.src.to_cm ** 3)), 1), "unit": "mL",
                "below_base_mL": round(float(np.nansum(np.minimum(H, 0)) * g.step ** 2 * (P.src.to_cm ** 3)), 1)}
    if k == "grid_mask_extent":
        g = P.src.get_input(a, P.side); r, c = np.nonzero(g.mask)
        u = (c - (g.n - 1) / 2) * g.step; v = (r - (g.n - 1) / 2) * g.step
        W = g.world(u, v, g.base[r, c]); X = P.to_frame(W)
        return {"x": {"min": round(float(X[:, 0].min()), 2), "max": round(float(X[:, 0].max()), 2), "width": round(float(np.ptp(X[:, 0]) + g.step * P.src.to_cm), 2)},
                "y": {"min": round(float(X[:, 1].min()), 2), "max": round(float(X[:, 1].max()), 2), "width": round(float(np.ptp(X[:, 1]) + g.step * P.src.to_cm), 2)},
                "area_projected_cm2": round(float(g.mask.sum() * (g.step * P.src.to_cm) ** 2), 2), "unit": "cm"}
    if k == "tube_sections":
        return _tube_sections(A, a)
    if k == "area":                                                # (L1) surface area of the part's own faces, cm2
        m = (P.select(a) if a else np.ones(len(P.src.V), bool)) & P.part; fm = m[P.src.F].all(1); T = P.src.V[P.src.F[fm]]
        A_ = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1).sum() * P.src.to_cm ** 2
        return {"value": round(float(A_), 3), "unit": "cm2"}
    raise ValueError(f"unknown measure {k}")


def _tube_sections(A, a):
    st, nr = a.get("step_cm", 1.0), int(a.get("rays", 180))
    S = np.arange(math.ceil(A.smin / st) * st, A.smax + 1e-9, st); ang = np.arange(nr) * 360.0 / nr
    rows = []
    for s in S:
        Q = A.resolve(np.c_[np.full(nr, s), ang])
        if not np.isfinite(Q).all():
            rows.append([s, np.nan, np.nan, np.nan]); continue
        d = A._d(np.array([s]))[0]; e0, e9 = A._e(d[None]); c = A._c(np.array([s]))[0]
        xy = np.c_[(Q - c) @ e0[0], (Q - c) @ e9[0]]
        per = float(np.linalg.norm(np.diff(np.r_[xy, xy[:1]], axis=0), axis=1).sum())
        area = 0.5 * abs(float((xy[:, 0] * np.roll(xy[:, 1], -1) - np.roll(xy[:, 0], -1) * xy[:, 1]).sum()))
        rows.append([s, float(ConvexHull(xy).area), per, area])
    T = np.array(rows); out = {"unit": "cm, cm2", "columns": ["s_cm", "girth_tape_cm", "perimeter_cm", "area_cm2"],
                               "table": [[round(x, 3) if np.isfinite(x) else None for x in r] for r in T.tolist()]}
    st_of = lambda p: float(A.tube_station(np.asarray(p, float)[None])[0])
    for nm, q in a.get("named", {}).items():
        if "at" in q:
            s0 = st_of(A.lm[q["at"]]) if isinstance(q["at"], str) else float(q["at"])
        elif "mid" in q:
            s0 = st_of(0.5 * (A.lm[q["mid"][0]] + A.lm[q["mid"][1]]))
        if "at" in q or "mid" in q:
            g = _section_at(A, s0, nr); out[nm] = {"s_cm": round(s0, 2), **g}; continue
        lo, hi = sorted(st_of(A.lm[x]) for x in q["between"])
        m = (T[:, 0] >= lo + q.get("inset_cm", 0)) & (T[:, 0] <= hi - q.get("inset_cm", 0)) & np.isfinite(T[:, 1])
        i = np.nonzero(m)[0][np.argmax(T[m, 1]) if q["kind"] == "max" else np.argmin(T[m, 1])]
        out[nm] = {"s_cm": round(float(T[i, 0]), 2), "girth_tape_cm": round(float(T[i, 1]), 2), "area_cm2": round(float(T[i, 3]), 2)}
    return out


def _section_at(A, s, nr):
    ang = np.arange(nr) * 360.0 / nr; Q = A.resolve(np.c_[np.full(nr, s), ang])
    if not np.isfinite(Q).all():
        return {"girth_tape_cm": None, "missing_rays": int((~np.isfinite(Q).all(1)).sum())}
    d = A._d(np.array([s])); e0, e9 = A._e(d); c = A._c(np.array([s]))[0]
    xy = np.c_[(Q - c) @ e0[0], (Q - c) @ e9[0]]
    area = 0.5 * abs(float((xy[:, 0] * np.roll(xy[:, 1], -1) - np.roll(xy[:, 0], -1) * xy[:, 1]).sum()))
    return {"girth_tape_cm": round(float(ConvexHull(xy).area), 2), "area_cm2": round(area, 2)}


def _overlay(P, spec):
    k, a = next(iter(spec.items()))
    if k == "grid_outline":
        g = P.src.get_input(a, P.side); th, rb = g.outline
        u, v = rb * np.cos(th), rb * np.sin(th)
        b, _ = g.sample(g.base, g.world(u, v, np.zeros_like(u)))
        Q = P.to_frame(g.world(u, v, b)); return np.r_[Q, Q[:1]].round(3).tolist()
    if k == "polyline":
        return [P.to_frame(P.lm[n][None])[0].round(3).tolist() for n in a]
    raise ValueError(k)


# -------------------------------------------------------------------------------------------------------- outputs
def write_outputs(out_dir, P, A, info, data, overlays):
    name = info["part"]; os.makedirs(out_dir, exist_ok=True)
    np.savez_compressed(os.path.join(out_dir, name + ".npz"), info=np.array(json.dumps(info)), **data)
    info["files"] = {x: name + x for x in (".json", ".npz", ".html", ".png")}
    json.dump(info, open(os.path.join(out_dir, name + ".json"), "w"), indent=1)
    render_png(os.path.join(out_dir, name + ".png"), info, data, overlays)
    write_html(os.path.join(out_dir, name + ".html"), info, data, overlays)


def _b64(a, dt):
    return base64.b64encode(np.ascontiguousarray(a, dt).tobytes()).decode()


def write_html(path, info, data, overlays):
    V, F = data["V"], data["F"]
    d = {"info": info, "V": _b64(V, "<f4"), "F": _b64(F, "<u4"), "nV": int(len(V)), "nF": int(len(F)),
         "vid": _b64(data["vid"], "<u4"), "ap": _b64(np.nan_to_num(data["addr_params"], nan=0), "<f4"), "as": _b64(data["addr_side"], "i1"),
         "gP": _b64(data["grid_P"], "<f4"), "gprm": _b64(data["grid_params"], "<f4"), "gside": _b64(data["grid_side"], "i1"),
         "glev": _b64(data.get("grid_level", np.zeros(len(data["grid_P"]), np.int8)), "i1"), "systems": info.get("address_systems"),
         "gnames": [str(x) for x in data["grid_names"]], "glines": _b64(data["grid_lines"], "<i4"),
         "fields": {k[6:]: _b64(v, "<f4") for k, v in data.items() if k.startswith("field_")}, "overlays": overlays}
    html = open(VIEW_TEMPLATE, encoding="utf-8").read()
    html = html.replace("__TITLE__", f"{info['part']} - part frame").replace("/*__DATA__*/null", json.dumps(d).replace("</", "<" + chr(92) + "/"))
    open(path, "w", encoding="utf-8").write(html)


def render_png(path, info, data, overlays, px_cm=0.04):
    """four views for agents: three orthographic along the frame's axes (cm grid, measurable) and an oblique one"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sys.path.insert(0, os.path.join(ROOT, "engine", "checks"))
    import zbuffer_numba as ZB
    from object_checks import Camera
    V, F = data["V"].astype(float), data["F"].astype(np.int64); lm = info["landmarks_cm"]
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    ax_n = info["axes"]; lab = lambda a: f"{a.upper()} (cm) - {ax_n[a]}"
    views = [("front: from +Z", "x", "y", "z"), ("side: from +X", "z", "y", "x"), ("top: from +Y", "x", "z", "y")]
    fig = plt.figure(figsize=(16, 13)); s = min(1.0 / px_cm, 2000.0 / max(float(np.ptp(V, axis=0).max()) + 2.0, 1e-9))   # (L1) at most ~2000 px a side
    for k, (title, h, v, t) in enumerate(views):
        H, Vv, T = np.eye(3)[AXES[h]], np.eye(3)[AXES[v]], np.eye(3)[AXES[t]]
        sgn = np.linalg.det(np.stack([H, -Vv, -T]))
        Hc = H * sgn                                   # keep the camera a rotation; the plot axis shows true values
        lo = V.min(0) - 1.0; hi = V.max(0) + 1.0
        Wd = int((hi[AXES[h]] - lo[AXES[h]]) * s) + 1; Ht = int((hi[AXES[v]] - lo[AXES[v]]) * s) + 1
        cen = 0.5 * (lo + hi); eye = cen + T * (np.ptp(V) + 10)
        R = np.stack([Hc, -Vv, -T]); cam = Camera(R, -R @ eye, s, s, Wd / 2, Ht / 2, Wd, Ht, ortho=True)
        r = ZB.rasterize(V, F, cam); fid = r["face"]
        shade = np.where(fid >= 0, 0.25 + 0.75 * np.abs(fn[np.maximum(fid, 0)] @ T), 1.0)
        img = np.dstack([shade * 0.86, shade * 0.80, shade * 0.74]); img[fid < 0] = 1.0
        x0 = cen[AXES[h]] - sgn * (Wd / 2) / s; x1 = cen[AXES[h]] + sgn * (Wd / 2) / s
        y1 = cen[AXES[v]] + (Ht / 2) / s; y0 = cen[AXES[v]] - (Ht / 2) / s
        axp = fig.add_subplot(2, 2, k + 1); axp.imshow(img, extent=[x0, x1, y0, y1], interpolation="bilinear")
        for nm, q in lm.items():
            axp.plot(q[AXES[h]], q[AXES[v]], "o", ms=5, color="#c0392b"); axp.annotate(nm, (q[AXES[h]], q[AXES[v]]), fontsize=8,
                                                                                      xytext=(4, 4), textcoords="offset points", color="#7b241c")
        for oname, Q in overlays.items():
            Q = np.asarray(Q); axp.plot(Q[:, AXES[h]], Q[:, AXES[v]], "-", lw=1, color="#1f618d", alpha=0.8)
        axp.set_xlim(x0, x1); axp.set_ylim(y0, y1); axp.set_aspect("equal")
        axp.xaxis.set_major_locator(plt.MultipleLocator(5)); axp.yaxis.set_major_locator(plt.MultipleLocator(5))
        axp.xaxis.set_minor_locator(plt.MultipleLocator(1)); axp.yaxis.set_minor_locator(plt.MultipleLocator(1))
        axp.grid(which="major", lw=0.6, alpha=0.5); axp.grid(which="minor", lw=0.3, alpha=0.25)
        axp.set_xlabel(lab(h)); axp.set_ylabel(lab(v)); axp.set_title(title, fontsize=10)
    # oblique: from lateral-superior-anterior, axes drawn with cm ticks
    axp = fig.add_subplot(2, 2, 4); dview = _unit([0.9, 0.7, 1.2]); up = np.array([0, 1.0, 0]); fwd = -dview
    dn = -_unit(up - (up @ fwd) * fwd); rgt = np.cross(dn, fwd); R = np.stack([rgt, dn, fwd])   # rows: right, down, forward
    ext = np.ptp(V, axis=0).max() + 4; Wd = Ht = 900; sc = Wd / (ext * 1.15); cen = 0.5 * (V.min(0) + V.max(0))
    eye = cen + dview * (ext + 10); cam = Camera(R, -R @ eye, sc, sc, Wd / 2, Ht / 2, Wd, Ht, ortho=True)
    r = ZB.rasterize(V, F, cam); fid = r["face"]
    shade = np.where(fid >= 0, 0.2 + 0.8 * np.abs(fn[np.maximum(fid, 0)] @ _unit(dview + up * 0.6)) ** 0.8, 1.0)
    img = np.dstack([shade * 0.86, shade * 0.80, shade * 0.74]); img[fid < 0] = 1.0
    axp.imshow(img); proj = lambda Q: cam.project(np.atleast_2d(Q))[:, :2]
    for ai, (an, colr) in enumerate(zip("xyz", ["#c0392b", "#27ae60", "#2471a3"])):
        lo_a = min(-5.0, math.floor(V[:, ai].min() / 5) * 5); hi_a = max(5.0, math.ceil(V[:, ai].max() / 5) * 5)
        e = np.zeros(3); e[ai] = 1; Pp = proj(np.array([e * lo_a, e * hi_a]))
        axp.plot(Pp[:, 0], Pp[:, 1], "-", color=colr, lw=1.2, alpha=0.8)
        for tk in np.arange(lo_a, hi_a + 0.1, 5):
            q = proj(e * tk)[0]; axp.plot(q[0], q[1], "+", color=colr, ms=5)
            if tk != 0:
                axp.annotate(f"{tk:g}", q, fontsize=7, color=colr, xytext=(2, 2), textcoords="offset points")
        q = proj(e * hi_a)[0]; axp.annotate(f"+{an.upper()} {ax_n[an]}", q, fontsize=9, color=colr, weight="bold")
    for nm, q in lm.items():
        pp = proj(np.array(q))[0]; axp.plot(pp[0], pp[1], "o", ms=4, color="#c0392b")
    axp.set_axis_off(); axp.set_title("oblique (axes in cm; ticks every 5 cm)", fontsize=10)
    ms = _measure_lines(info)
    fig.suptitle(f"{info['part']} in its own frame - {info['source']}\n" + "; ".join(ms[:4]), fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig(path, dpi=80); plt.close(fig)


def _measure_lines(info):
    out = []
    for k, m in info["measures"].items():
        if "value" in m:
            out.append(f"{k} {m['value']} {m['unit']}")
    return out


def write_index(out_dir, infos):
    rows = []
    for i in infos:
        ms = "<br>".join(_measure_lines(i)[:8])
        rows.append(f"<tr><td><a href='{i['part']}.html'>{i['part']}</a></td><td>{i['source']}</td><td>{i['counts']['vertices']}</td>"
                    f"<td>{i['address']['kind']}</td><td>{ms}</td><td><a href='{i['part']}.png'>views</a> · <a href='{i['part']}.json'>json</a></td></tr>")
    html = ("<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Part frames</title>"
            "<style>body{font:14px system-ui,sans-serif;margin:16px;background:#fafafa;color:#222}table{border-collapse:collapse}"
            "td,th{border-bottom:1px solid #ddd;padding:6px 10px;text-align:left;vertical-align:top}</style>"
            "<h2>Part frames</h2><p>Each part in its own frame: X lateral, Y superior, Z anterior/outward, cm. Right-side parts are "
            "mirrored so lateral is +X on both sides. Open a part, click dots, copy the picks into chat.</p>"
            "<table><tr><th>part</th><th>source</th><th>vertices</th><th>address</th><th>measures</th><th></th></tr>" + "".join(rows) + "</table>")
    open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8").write(html)


TOOL_VERSION = "10.L1"      # what a build writes; a change that alters it marks every built part stale (fingerprint)
_SHA = {}


def _sha_cached(path):
    st = os.stat(path); k = (path, st.st_size, st.st_mtime_ns)
    if k not in _SHA:
        _SHA[k] = _sha1_file(path)
    return _SHA[k]


def job_items(job):
    """(item, side, name) for every part a job builds: name = the item's "name", else part + _side (build 09's rule)"""
    out = []
    for item in job["parts"]:
        for side in (item.get("sides") or [item.get("side")]):
            out.append((item, side, item.get("name") or (item["part"] + ("_" + side if side else ""))))
    return out


def _input_files(spec, side, mesh_spec):
    return [_cur(spec[k].replace("{side}", side or ""), mesh_spec) for k in ("npz", "json", "height_grid") if k in spec]


def part_files(job, item, side):
    """the files a part is read from: its source's mesh (a followed pack's pack.json too) and every input file"""
    src = job["sources"][item["source"]]; m = src["mesh"]; files = [mesh_path(m)]
    if "follow_pack" in m:
        files.append(m["follow_pack"].rstrip("/") + "/pack.json")
    for sp in src.get("inputs", {}).values():
        files += _input_files(sp, side, m)
    return sorted(set(files))


def fingerprint(job, item, side):
    """what a part is made from (build L1): the sha1 of its definition entry and of its job source, the sha1 of every
    file it reads (part_files: the source mesh, each input the job binds, a followed pack's pack.json) and the tool's
    version. Equal fingerprints = the part is current."""
    defs = json.load(open(_p(job["definitions"]))); src = job["sources"][item["source"]]
    out = {}
    for f in part_files(job, item, side):
        rp = os.path.relpath(_p(f), ROOT).replace(os.sep, "/")
        out[rp] = _sha_cached(_p(f)) if os.path.exists(_p(f)) else "missing"
    entry = defs["parts"].get(item["part"])
    return {"tool": TOOL_VERSION, "entry": _sha1(entry)[:12] if entry is not None else "missing",
            "source": _sha1({k: v for k, v in src.items() if k != "label"})[:12], "files": out}


def build(job_path, only=None, log=print):
    job = json.load(open(job_path)); defs_path = _p(job["definitions"]); defs = json.load(open(defs_path))
    out_dir = _p(job["out_dir"]); srcs = {}; infos = []
    for item, side, name in job_items(job):
        if only and name not in only:
            continue
        entry = dict(defs["parts"][item["part"]]); entry["_key"] = item["part"]
        sname = item["source"]; srcs.setdefault(sname, Source(sname, job["sources"][sname]))
        fp = fingerprint(job, item, side)
        P, A, info, data, ov = build_part(entry, srcs[sname], side, name, {"path": os.path.relpath(defs_path, ROOT).replace(os.sep, "/")}, log)
        info["job"] = os.path.relpath(_p(job_path), ROOT).replace(os.sep, "/")
        info["fingerprint"] = fp
        write_outputs(out_dir, P, A, info, data, ov); infos.append(info)
    if not only and not job.get("index_by"):                         # (L1) a language job writes its own index
        write_index(out_dir, infos)
    return infos


# ------------------------------------------------------------------------------------------------------- resolve
def load_part(npz_path):
    """a built part: its info, the npz, build 09's address system and the skin atlas (None for a part without one)"""
    z = np.load(npz_path, allow_pickle=False); info = json.loads(str(z["info"]))
    V, F = z["V"].astype(float), z["F"].astype(np.int64); lm = {k: np.array(v) for k, v in info["landmarks_cm"].items()}
    A = Address(info["address"], info["part"], V, F, lm); SA = None
    if info.get("skin"):
        specs = [{k: v for k, v in c.items() if k not in ("region_vertices", "addressed_here", "round_trip_failed", "no_walk",
                                                           "grid_points", "reference_station_cm", "ring_field_walked", "ring_field_filled")}
                 for c in info["skin"]["charts"]]
        regions = {sp["name"]: z["chart_region_" + sp["name"]].astype(bool) for sp in specs}
        fields = {}
        for sp in specs:
            if "chart_u_" + sp["name"] in z:
                fu = z["chart_u_" + sp["name"]]; sub = _Sub(V, F, regions[sp["name"]]); fields[sp["name"]] = fu[sub.vidx]
        SA = SkinAtlas(specs, info["part"], V, F, lm, regions, fields)
    A.atlas = SA
    return info, z, A


def resolve(npz_path, addresses, current=True):
    """each address -> (frame point cm, source point, nearest vertex of this build); NaN when the address misses.
    Kinds: a skin chart's name (the grid's addresses), build 09's h+ / h- / tube / sphere, xyz.
    current=True (build L1): the part is brought current first - rebuilt if anything it is made from changed
    (engine/tools/language.py ensure_current) - so an address is never read on a stale build."""
    if current:
        try:
            sys.path.insert(0, HERE)
            import language as _LG
            _LG.ensure_current(npz_path)
        except Exception as ex:                                       # never blocks a read; says why
            print(f"(part_frame.resolve: could not check that {os.path.basename(npz_path)} is current: {ex})", file=sys.stderr)
    info, z, A = load_part(npz_path); out = []; SA = A.atlas
    tree = cKDTree(A.V); fr = info["frame"]; o, R, k = np.array(fr["origin_source"]), np.array(fr["R_rows_source"]), fr["source_units_to_cm"]
    for text in addresses:
        part, kind, kv = parse_address(text)
        if part != info["part"]:
            raise ValueError(f"address names part {part}, file holds {info['part']}")
        fa = None; mf = A.min_facing
        if kind == "xyz":
            Q, _ = closest_points(A.V, A.F, np.array([[kv["x"], kv["y"], kv["z"]]]))
        elif SA is not None and kind in SA.by_name:
            c = SA.by_name[kind]; a, b = c.coord_names; Q, _, f_ = c.resolve([[kv[a], kv[b]]]); fa = float(f_[0]); mf = c.min_facing
        elif kind in ("h+", "h-"):
            ax = [n for n, a in AXES.items() if a in A._hij()]; Q, f_ = A.resolve([[kv[ax[0]], kv[ax[1]]]], kind[1], facing=True); fa = float(f_[0])
        elif kind == "tube":
            Q, f_ = A.resolve([[kv["s"], kv["a"]]], facing=True); fa = float(f_[0])
        elif kind == "sphere":
            Q, f_ = A.resolve([[kv["lat"], kv["lon"]]], facing=True); fa = float(f_[0])
        else:
            raise ValueError(f"{info['part']} has no address kind '{kind}'")
        q = Q[0]; vi = int(tree.query(q)[1]) if np.isfinite(q).all() else -1
        at = re.search(r"at \(\s*([-+0-9.]+),\s*([-+0-9.]+),\s*([-+0-9.]+)\)", text)      # a pasted line carries where it was picked
        moved = float(np.linalg.norm(q - np.array([float(x) for x in at.groups()]))) if at and np.isfinite(q).all() else None
        out.append({"address": text.strip(), "frame_cm": q.tolist(), "source": (o + (q / k) @ R).tolist(), "facing": fa,
                    "nearest_vertex_this_build": int(z["vid"][vi]) if vi >= 0 else None,
                    "moved_from_picked_cm": None if moved is None else round(moved, 3),
                    "check": bool(moved is not None and moved > 0.5) or not np.isfinite(q).all() or (fa is not None and fa < mf)})
    return out


# --------------------------------------------------------------------------------------------------------- proof
def prove(log=print):
    """Analytic shapes with known answers (A28: once, at the tool's making):
    1. a smooth mound z = H (1 - r^2/a^2)^2 on a plane (volume pi a^2 H / 3), tilted and moved, under a height grid:
       the frame comes back from the landmarks, height addresses land on the analytic surface, the grid volume is right,
       every vertex's address round-trips;
    2. the same mound tessellated differently (another vertex count, vertices shifted along the surface): the same
       address texts land on the same places (the remesh claim) while the nearest vertex numbers differ;
    3. a tube of radius r0 swept along two segments with a 30 deg bend: tube addresses land at r0, the girth is
       2 pi r0 at every station (the bend included), the bend angle reads 150 deg, vertices round-trip;
    4. planted: a frame against its lateral check is refused; an address off the part misses (NaN), never snaps."""
    ok = True

    def chk(name, cond, msg):
        nonlocal ok; ok &= bool(cond); log(f"  {'PASS' if cond else 'FAIL'} {name}: {msg}")

    a, Hm = 0.06, 0.04
    Rt = _rot([0.3, -0.2, 0.5]); t = np.array([0.1, -0.15, -0.2]); res = {}
    mound = lambda r2: np.where(r2 < a * a, Hm * (1 - r2 / (a * a)) ** 2, 0.0)
    for tag, n in (("A", 241), ("B", 167)):
        u = np.linspace(-0.12, 0.12, n); U, W = np.meshgrid(u, u); h = u[1] - u[0]
        jit = np.sin(U * 977) * np.cos(W * 619) * h * 0.3 if tag == "B" else 0 * U        # B: vertices moved along x
        Vl = np.c_[(U + jit).ravel(), W.ravel(), np.zeros(n * n)]; Vl[:, 2] = mound(Vl[:, 0] ** 2 + Vl[:, 1] ** 2)
        idx = np.arange(n * n).reshape(n, n)
        q0, q1, q2, q3 = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel()
        Fl = np.r_[np.c_[q0, q1, q3], np.c_[q0, q3, q2]]
        Vs = Vl @ Rt.T + t                                      # local (e1, e2, n) -> source (metres)
        k = 0.0005; m = 481; g = (np.arange(m) - (m - 1) / 2) * k; GU, GV = np.meshgrid(g, g); gr = GU ** 2 + GV ** 2
        grid = HeightGrid(t, Rt.T, k, m, mound(gr), np.zeros_like(gr), gr < a * a,
                          (np.linspace(0, 2 * np.pi, 72, endpoint=False), np.full(72, a)))
        src = _MemSource(Vs, Fl, {"wall": grid, "cap": (Vl[:, 0] ** 2 + Vl[:, 1] ** 2) < 0.004 ** 2})
        entry = {"landmarks": {"tip": {"extreme": {"dir": {"grid_normal": "wall"}, "among": [{"mask": "cap"}]}},
                               "foot": {"grid_base_under": {"grid": "wall", "point": "tip"}}},
                 "frame": {"origin": "foot", "axes": [["z", {"grid_normal": "wall"}], ["y", {"vector": list(Rt[:, 1])}]],
                           "check": {"x": {"vector_side": list(Rt[:, 0])}}},
                 "select": [{"grid_mask": {"grid": "wall", "dilate_cm": 2.0}}],
                 "address": {"kind": "height", "up": "z", "sides": ["+"], "step_cm": 1.0},
                 "measures": {"vol": {"grid_volume": "wall"}, "proj": {"coord": ["tip", "z"]}}}
        P, A, info, data, _ = build_part(entry, src, "L", "mound_L", {"path": "-"}, log=lambda *x: None)
        res[tag] = (P, A, info, data)
        G = data["grid_P"].astype(float); zt = mound((G[:, 0] ** 2 + G[:, 1] ** 2) / 1e4) * 100
        err = np.abs(G[:, 2] - zt).max(); kappa = 8 * Hm / a ** 2 / 100           # the mound's largest curvature, 1/cm
        bound = kappa * (h * 100 * 1.5) ** 2 / 8                                  # chordal error of its triangles
        chk(f"height addresses on the analytic surface ({tag})", err <= bound,
            f"max |z - z_true| {err * 10:.4f} mm over {len(G)} grid points (chordal bound {bound * 10:.4f} mm)")
        chk(f"frame from the landmarks ({tag})", np.abs(P.R - Rt.T).max() < 1e-9 and np.linalg.norm(P.o - t) < 1e-9,
            f"axes off by {np.abs(P.R - Rt.T).max():.1e}, origin by {np.linalg.norm(P.o - t) * 1000:.1e} mm")
        vt = math.pi * a * a * Hm / 3 * 1e6
        chk(f"grid volume ({tag})", abs(info["measures"]["vol"]["value"] - vt) / vt < 0.005,
            f"{info['measures']['vol']['value']} mL vs {vt:.1f} analytic")
        chk(f"vertex addresses round-trip ({tag})", (data["addr_side"] >= 0).mean() > 0.999,
            f"{(data['addr_side'] >= 0).mean() * 100:.2f} % of vertices")
    QB = res["B"][1].resolve(res["A"][3]["grid_params"].astype(float), "+")
    dd = np.linalg.norm(QB - res["A"][3]["grid_P"], axis=1)
    chk("remesh: same address, same place", np.nanmax(dd) < 0.01, f"{len(dd)} grid addresses, max shift {np.nanmax(dd) * 10:.4f} mm "
        f"between tessellations of {len(res['A'][3]['V'])} and {len(res['B'][3]['V'])} vertices")
    vA, vB = res["A"][3], res["B"][3]
    ia = cKDTree(vA["V"]).query(vA["grid_P"])[1]; ib = cKDTree(vB["V"]).query(QB)[1]
    chk("remesh: vertex numbers do not carry over", (vA["vid"][ia] != vB["vid"][ib]).mean() > 0.9,
        f"{(vA['vid'][ia] != vB['vid'][ib]).mean() * 100:.0f} % of the nearest vertex numbers differ")
    # 3. the bent tube, swept with the tool's own axis (sections normal to the blended direction)
    r0 = 3.0
    J = np.array([[0, 0, 0], [0, 0, -25.0], [0, -25 * math.sin(math.radians(30)), -25 - 25 * math.cos(math.radians(30))]])
    ax = Address.__new__(Address); ax.spec = {"blend_cm": 4.0}; ax._tube_setup(J)
    S = np.linspace(0, 50, 1001); C = ax._c(S); D = ax._d(S)
    e0 = np.array([0, -1.0, 0]) - (D @ [0, -1.0, 0])[:, None] * D; e0 /= np.linalg.norm(e0, axis=1, keepdims=True); e9 = np.cross(D, e0)
    na = 120; ang = np.arange(na) * 2 * np.pi / na
    Vt = (C[:, None] + r0 * (np.cos(ang)[None, :, None] * e0[:, None] + np.sin(ang)[None, :, None] * e9[:, None])).reshape(-1, 3) / 100
    idx = np.arange(len(S) * na).reshape(len(S), na)
    a0, a1, b0, b1 = idx[:-1], np.roll(idx[:-1], -1, 1), idx[1:], np.roll(idx[1:], -1, 1)
    Ft = np.r_[np.c_[a0.ravel(), a1.ravel(), b1.ravel()], np.c_[a0.ravel(), b1.ravel(), b0.ravel()]]
    src = _MemSource(Vt, Ft, {"j0": J[0] / 100, "j1": J[1] / 100, "j2": J[2] / 100})
    entry = {"landmarks": {"a": {"point": "j0"}, "b": {"point": "j1"}, "c": {"point": "j2"}},
             "frame": {"origin": "a", "axes": [["y", {"from": "b", "to": "a"}], ["z", {"vector": [0, -1, 0]}]],
                       "check": {"x": {"vector_side": [1, 0, 0]}}},
             "select": [{"side": False}],
             "address": {"kind": "tube", "through": ["a", "b", "c"], "blend_cm": 4.0, "step_cm": 1.0, "angle_deg": 15},
             "measures": {"sec": {"tube_sections": {"step_cm": 1.0, "rays": 360}}, "bend": {"angle": ["a", "b", "c"]}}}
    P, A, info, data, _ = build_part(entry, src, "L", "tube_L", {"path": "-"}, log=lambda *x: None)
    T = np.array([r for r in info["measures"]["sec"]["table"] if r[1] is not None], float)
    inner = T[(T[:, 0] >= 1) & (T[:, 0] <= 49)]
    gt = 2 * math.pi * r0 * math.sin(math.pi / na) / (math.pi / na)                # the 120-gon's perimeter
    chk("tube girth at every station (bend included)", len(inner) == 49 and np.abs(inner[:, 1] - gt).max() < 0.002 * gt,
        f"{len(inner)} stations, girth {inner[:, 1].min():.4f}-{inner[:, 1].max():.4f} cm vs {gt:.4f} (120-gon)")
    G = data["grid_P"].astype(float); prm = data["grid_params"].astype(float)
    rr = np.linalg.norm(G - A._c(prm[:, 0]), axis=1)
    chk("tube addresses at the radius", np.abs(rr - r0).max() < r0 * (1 - math.cos(math.pi / na)) + 1e-3,
        f"radius {rr.min():.4f}-{rr.max():.4f} cm over {len(G)} grid points")
    chk("bend angle", abs(info["measures"]["bend"]["value"] - 150) < 0.01,
        f"{info['measures']['bend']['value']} deg at the joint (150 = a 30 deg bend)")
    chk("tube vertex addresses round-trip", (data["addr_side"] >= 0).mean() > 0.99,
        f"{(data['addr_side'] >= 0).mean() * 100:.2f} % of vertices")
    # 4. planted
    bad = json.loads(json.dumps(entry)); bad["frame"]["check"] = {"x": {"vector_side": [-1, 0, 0]}}
    try:
        build_part(bad, src, "L", "tube_bad", {"path": "-"}, log=lambda *x: None); caught = False
    except AssertionError:
        caught = True
    chk("planted: a frame against its lateral check", caught, "refused (AssertionError)" if caught else "NOT caught")
    miss = res["A"][1].resolve([[40.0, 40.0]], "+")
    chk("planted: an address off the part", not np.isfinite(miss).any(),
        "misses (NaN)" if not np.isfinite(miss).any() else f"snapped to {miss}")
    log("  skin charts (build 10):")
    ok &= prove_skin(log)
    log("PROVE " + ("PASS" if ok else "FAIL"))
    return ok


def _ring_mesh(prof, N, off=0.0, closed_pole=True):
    """a surface of revolution (for the proofs): rings of N points round the Z axis at the profile's (rho, z) pairs,
    odd rings turned by off of a step; a pole fan where rho is 0. Returns V (cm), F"""
    V = []; idx = []
    for i, (rho, z) in enumerate(prof):
        if rho < 1e-12:
            idx.append([len(V)]); V.append([0.0, 0.0, z]); continue
        a = 2 * np.pi * (np.arange(N) + off * (i % 2)) / N
        idx.append(list(range(len(V), len(V) + N))); V += [[rho * math.sin(t), rho * math.cos(t), z] for t in a]
    F = []
    for i in range(len(idx) - 1):
        A_, B_ = idx[i], idx[i + 1]
        if len(A_) == 1:
            F += [[A_[0], B_[j], B_[(j + 1) % N]] for j in range(N)]
        else:
            F += [[A_[j], B_[j], B_[(j + 1) % N]] for j in range(N)] + [[A_[j], B_[(j + 1) % N], A_[(j + 1) % N]] for j in range(N)]
    return np.array(V, float), np.array(F, np.int64)


def prove_skin(log=print):
    """Skin charts (build 10) on analytic shapes with known answers (A28: once, at the tool's making):
    (Every cut is turned DTH = 5.4e-5 rad / lifted DU = 1.2e-5 cm off exact alignment, so a vertex's address is read
    where its cut passes it, within rho x DTH: about 0.005 mm at 10 cm.)
    5. a hemisphere (R 5 cm) standing on a plane, a 90 deg crease at its foot (the breast's base wall, sharpened): the
       disc chart's ring coordinate equals its closed form at every vertex - the frame's own radius where the skin
       turns under 30 deg, then sin 30 + cos 30 x the arc past that point, then the plane's radius once it catches
       up; vertex addresses round-trip; grid segments on the skin <= 1 / cos 30 of the step; a second tessellation
       (another ring count, rings rotated half a step, other radii) puts the same addresses on the same places;
       a slot cut into the plane (2 mm wide, 7 mm along the meridians through it) is bridged - the places past it
       keep their closed-form address - and an address that falls inside the slot misses;
    6. a tube (r 3 cm, 20 cm) with a hemispherical cap: the tube chart's s = the station along the cylinder and its
       closed form over the cap, c = the arc round each ring from the reference line (r x angle; r cos psi over the
       cap), read in chords of at most 0.15 x the radius (so <= 0.1 % short of the arc); round trip; remesh as in 5
       (within 0.1 mm: the chords' ends fall on each tessellation's own crossings)."""
    ok = True

    def chk(name, cond, msg):
        nonlocal ok; ok &= bool(cond); log(f"  {'PASS' if cond else 'FAIL'} {name}: {msg}")

    k30 = math.cos(math.radians(30)); R = 5.0
    def u_disc(rho, z):                                   # closed form on the hemisphere-on-a-plane
        phi = np.where(z > 1e-9, np.arctan2(rho, z), np.pi / 2)
        u_s = np.where(phi <= np.pi / 6, R * np.sin(phi), R * (0.5 + k30 * (phi - np.pi / 6)))
        t = np.maximum(rho - R, 0.0); u_eq = R * (0.5 + k30 * np.pi / 3)
        return np.where(z > 1e-9, u_s, np.maximum(R + t, u_eq + k30 * t))
    res = {}
    for tag, N, nphi, nrho, off in (("A", 360, 260, 140, 0.0), ("B", 251, 190, 97, 0.5)):
        phis = np.linspace(0, np.pi / 2, nphi); rhos = np.linspace(R, 12.0, nrho)[1:]
        prof = [(R * math.sin(p), R * math.cos(p)) for p in phis] + [(r, 0.0) for r in rhos]
        V, F = _ring_mesh(prof, N, off)
        src = _MemSource(V / 100, F, {"o": np.zeros(3)})
        entry = {"landmarks": {"foot": {"point": "o"}},
                 "frame": {"origin": "foot", "axes": [["z", {"vector": [0, 0, 1]}], ["y", {"vector": [0, 1, 0]}]], "check": {"x": {"vector_side": [1, 0, 0]}}},
                 "select": [{"side": False}], "address": {"kind": "height", "up": "z", "sides": ["+"], "step_cm": 1.0},
                 "skin": {"charts": [{"name": "skin", "kind": "disc", "axis": "z", "through": "foot", "from": "+", "turn_deg": 30,
                                      "grid": [{"step_cm": 1.0}]}]}}
        P, A, info, data, _ = build_part(entry, src, "L", "dome_L", {"path": "-"}, log=lambda *x: None)
        c = P.atlas.charts[0]; Vf = c.sub.V; prm = c.params_of_vertices(TOL_CM); u = np.hypot(prm[:, 0], prm[:, 1])
        rho = np.hypot(Vf[:, 0], Vf[:, 1]); ut = u_disc(rho, Vf[:, 2]); e = np.abs(u - ut)
        chk(f"disc ring coordinate = closed form ({tag})", np.nanmax(e) < 0.003 and np.isfinite(u).all(),
            f"max |u - u_true| {np.nanmax(e) * 10:.4f} mm over {len(u)} vertices ({N} x {len(prof)} rings)")
        flat = (np.arctan2(rho, np.maximum(Vf[:, 2], 1e-12)) < np.radians(29)) & (Vf[:, 2] > 0)
        chk(f"disc = the frame's own x, y under the turn ({tag})", np.abs(prm[flat] - Vf[flat][:, :2]).max() < 1e-3,
            f"max |(x, y) - frame (x, y)| {np.abs(prm[flat] - Vf[flat][:, :2]).max():.1e} cm over {flat.sum()} vertices turned < 29 deg")
        chk(f"disc vertex addresses round-trip ({tag})", (data["addr_side"] == 0).mean() == 1.0,
            f"{(data['addr_side'] == 0).mean() * 100:.2f} % of vertices")
        sp = info["skin"]["grid_spacing"]["ratio"]
        chk(f"disc grid on the skin ({tag})", sp["max"] <= 1 / k30 + 0.01, f"segments {sp['min']}-{sp['max']} x the step (bound 1 / cos 30 = {1 / k30:.3f})")
        res[tag] = (P, data)
    QB, _, _ = res["B"][0].atlas.charts[0].resolve(res["A"][1]["grid_params"].astype(float))
    dd = np.linalg.norm(QB - res["A"][1]["grid_P"], axis=1)
    chk("disc remesh: same address, same place", np.nanmax(dd) < 0.005 and np.isfinite(dd).all(),
        f"{len(dd)} grid addresses, max shift {np.nanmax(dd) * 10:.4f} mm between tessellations of {len(res['A'][1]['V'])} and {len(res['B'][1]['V'])} vertices")
    # the notch: faces within 1 mm of the plane x = 0 beyond rho 10.5 (y > 0) removed
    V, F = _ring_mesh([(R * math.sin(p), R * math.cos(p)) for p in np.linspace(0, np.pi / 2, 260)] + [(r, 0.0) for r in np.linspace(R, 12.0, 140)[1:]], 360, 0.003)
    C = V[F].mean(1); keepF = ~((np.abs(C[:, 0]) < 0.1) & (C[:, 1] > 10.5) & (C[:, 1] < 11.2)); F = F[keepF]
    src = _MemSource(V / 100, F, {"o": np.zeros(3)})
    P, A, info, data, _ = build_part(entry, src, "L", "dome_L", {"path": "-"}, log=lambda *x: None)
    c = P.atlas.charts[0]; Vf = c.sub.V; prm = c.params_of_vertices(TOL_CM); u = np.hypot(prm[:, 0], prm[:, 1])
    beyond = (np.abs(Vf[:, 0]) < 0.3) & (Vf[:, 1] > 11.25); e = np.abs(u - u_disc(np.hypot(Vf[:, 0], Vf[:, 1]), Vf[:, 2]))
    chk("bridge: a 2 x 7 mm slot in the plane", np.isfinite(u[beyond]).all() and np.nanmax(e[beyond]) < 0.003,
        f"{beyond.sum()} vertices past it keep the closed form (max {np.nanmax(e[beyond]) * 10:.4f} mm)")
    Qn, _, _ = c.resolve([[0.0, u_disc(np.array([10.85]), np.array([0.0]))[0]]])
    chk("bridge: an address inside the slot misses", not np.isfinite(Qn).any(), "NaN" if not np.isfinite(Qn).any() else f"landed at {Qn}")
    # 6. the capped tube, along -Y
    r0, Lc = 3.0, 20.0
    def tube_mesh(N, ns, npsi, off):
        Vt, Ft, rings = [], [], []
        for i, s_ in enumerate(np.linspace(0, Lc, ns)):
            a = 2 * np.pi * (np.arange(N) + off * (i % 2)) / N; rings.append(list(range(len(Vt), len(Vt) + N)))
            Vt += [[r0 * math.sin(t), -s_, r0 * math.cos(t)] for t in a]
        for j, ps in enumerate(np.linspace(0, np.pi / 2, npsi)[1:]):
            rr = r0 * math.cos(ps)
            if rr < 1e-9:
                rings.append([len(Vt)]); Vt.append([0.0, -(Lc + r0), 0.0]); continue
            a = 2 * np.pi * (np.arange(N) + off * (j % 2)) / N; rings.append(list(range(len(Vt), len(Vt) + N)))
            Vt += [[rr * math.sin(t), -(Lc + r0 * math.sin(ps)), rr * math.cos(t)] for t in a]
        for A_, B_ in zip(rings[:-1], rings[1:]):
            if len(B_) == 1:
                Ft += [[A_[j], A_[(j + 1) % N], B_[0]] for j in range(N)]
            else:
                Ft += [[A_[j], B_[j], B_[(j + 1) % N]] for j in range(N)] + [[A_[j], B_[(j + 1) % N], A_[(j + 1) % N]] for j in range(N)]
        return np.array(Vt, float), np.array(Ft, np.int64)
    def tube_true(Vt):
        s_ = -Vt[:, 1]; cap = s_ > Lc + 1e-9; ps = np.where(cap, np.arcsin(np.clip((s_ - Lc) / r0, 0, 1)), 0.0)
        u = np.where(~cap, s_, np.where(ps <= np.pi / 6, s_, Lc + r0 * (0.5 + k30 * (ps - np.pi / 6))))
        rr = np.hypot(Vt[:, 0], Vt[:, 2]); a = np.arctan2(Vt[:, 0], Vt[:, 2]); cc = rr * (((a - np.pi / 2 + np.pi) % (2 * np.pi)) - np.pi)   # signed, the shorter way
        return u, cc, rr
    res = {}
    for tag, N, ns, npsi, off in (("A", 240, 401, 90, 0.0), ("B", 199, 331, 71, 0.5)):
        Vt, Ft = tube_mesh(N, ns, npsi, off)
        src = _MemSource(Vt / 100, Ft, {"j0": np.zeros(3), "j1": np.array([0, -Lc / 100, 0])})
        entry_t = {"landmarks": {"a": {"point": "j0"}, "b": {"point": "j1"}},
                   "frame": {"origin": "a", "axes": [["y", {"from": "b", "to": "a"}], ["z", {"vector": [0, 0, 1]}]], "check": {"x": {"vector_side": [1, 0, 0]}}},
                   "select": [{"side": False}], "address": {"kind": "tube", "through": ["a", "b"], "after_cm": 5.0, "step_cm": 1.0, "angle_deg": 15},
                   "skin": {"charts": [{"name": "skin", "kind": "tube", "through": ["a", "b"], "before_cm": 1.0, "after_cm": 5.0, "blend_cm": 1.0,
                                        "ref": {"fraction": 0.5}, "c_from_deg": 90, "turn_deg": 30, "grid": [{"step_cm": 1.0}]}]}}
        P, A, info, data, _ = build_part(entry_t, src, "L", "tube_L", {"path": "-"}, log=lambda *x: None)
        c = P.atlas.charts[0]; Vf = c.sub.V; prm = c.params_of_vertices(TOL_CM); ut, ct, rr = tube_true(Vf)
        okp = np.isfinite(prm).all(1); far = rr > 0.05                                   # c is undefined at the pole itself
        eu = np.abs(prm[:, 0] - ut); ec = np.abs(prm[:, 1] - ct); ec = np.minimum(ec, np.abs(ec - 2 * np.pi * rr))   # ties at the far side
        chk(f"tube s = the station, the cap's closed form past the turn ({tag})", okp.mean() > 0.999 and np.nanmax(eu[okp]) < 0.003,
            f"{okp.mean() * 100:.2f} % of vertices; max |s - s_true| {np.nanmax(eu[okp]) * 10:.4f} mm")
        walked = np.abs(prm[:, 1])                                           # the arc the ring walk covered to the vertex
        bound = 0.0011 * walked + 0.003                                      # c is read in chords <= 0.15 r: short by <= 0.1 %
        chk(f"tube c = the arc round the ring ({tag})", (ec[okp & far] <= bound[okp & far]).all(),
            f"max |c - r x angle| {np.nanmax(ec[okp & far]) * 10:.4f} mm, max relative {np.nanmax((ec / np.maximum(walked, 1e-9))[okp & far & (walked > 1)]) * 100:.3f} % of the arc walked "
            f"(chords of about 0.15 r: about 0.1 %; the {N}-gon's perimeter is short by {2 * np.pi * r0 * (1 - math.sin(math.pi / N) / (math.pi / N)) * 10:.4f} mm)")
        chk(f"tube vertex addresses round-trip ({tag})", (data["addr_side"] == 0).mean() > 0.999, f"{(data['addr_side'] == 0).mean() * 100:.2f} % of vertices")
        sp = info["skin"]["grid_spacing"]["ratio"]
        bt = math.hypot(1 / k30, 0.5)                    # rings <= 1 / cos 30 apart along the meridian, a link <= half a step round
        chk(f"tube grid on the skin ({tag})", sp["max"] <= bt + 0.01, f"segments {sp['min']}-{sp['max']} x the step (bound hypot(1 / cos 30, 1/2) = {bt:.3f})")
        res[tag] = (P, data)
    QB, _, _ = res["B"][0].atlas.charts[0].resolve(res["A"][1]["grid_params"].astype(float))
    dd = np.linalg.norm(QB - res["A"][1]["grid_P"], axis=1)
    chk("tube remesh: same address, same place", np.nanmax(dd) < 0.01 and np.isfinite(dd).mean() > 0.99,
        f"{len(dd)} grid addresses ({(~np.isfinite(dd)).sum()} missed), max shift {np.nanmax(dd) * 10:.4f} mm between {len(res['A'][1]['V'])} and {len(res['B'][1]['V'])} vertices")
    return ok


class _MemSource(Source):
    def __init__(self, V, F, inputs):
        self.name, self.V, self.F, self.to_cm = "mem", np.asarray(V, float), np.asarray(F, np.int64), 100.0
        self.left, self.label, self._inputs, self.files, self._cache = np.array([1.0, 0, 0]), "analytic", inputs, {}, {}

    def get_input(self, name, side):
        return self._inputs[name]


def _rot(w):
    w = np.asarray(w, float); th = np.linalg.norm(w); k = w / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "prove":
        sys.exit(0 if prove() else 1)
    if a[0] == "build":
        build(a[1], a[2:] or None)
    elif a[0] == "resolve":
        for r in resolve(a[1], a[2:]):
            print(json.dumps(r))
