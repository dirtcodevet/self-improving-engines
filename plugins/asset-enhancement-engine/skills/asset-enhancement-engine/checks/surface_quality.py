"""SURFACE QUALITY of a region: is the skin smooth there and is the mesh sound (build 13a2's and 13a's instruments,
cases/woman2/build13/a2_measure.py and m_mesh.py; moved here in build A1, 2026-10-21, unchanged in what they read).

  edge_turns(V, T)                     (edges, deg): the angle between the two faces' normals at every interior edge
                                       (quads split as fan triangles, so each quad's diagonal counts): a crease or a
                                       fold reads directly
  turn_stats(e, ang, sel)              max / p99 / edges over 20 deg over the edges with both ends in `sel`
  curvature_roughness(V, T, sel, H=None, area=None, ball_mm=10)
                                       mean curvature H (cotangent Laplacian, 1/m) minus its area-weighted mean over a
                                       ball: RMS, p99 |.|, max over `sel` (area-weighted). A ridge, a step or a dent reads
                                       as H jumping against its neighbourhood; a mound's own convexity cancels
  quad_stats(V, sizes, flat, sel)      quads in `sel` (per polygon): min corner angle p1 / p5 / min, aspect p99 / max,
                                       edge length p5 / p50 / p95 (mm)
  turned_over(V_ref, V, T, tri_sel)    triangles whose normal turned more than 90 deg from the reference's
  crossings_near(V, T, sel, margin_m=0.1, V_nb=None)  triangle pairs through each other (sharing no vertex) with a triangle
                                       touching `sel`, against every triangle within margin of it (Blender BVH,
                                       background: engine/tools/bvh.py)
  changed_region(V_ref, V, T, sizes, flat, changed, sides=None, labels=("now", "ref"))
                                       the four together over a changed region (build 13a4's table): folds over 90 deg,
                                       the largest edge turn, turned-over triangles, quads, crossings (per side: masks, or a
                                       function of the positions giving them)
Proof: engine/checks/test_surface_quality.py (planted ridge, fold, dent, crossing on a smooth sheet; json beside it).
Reference practice (13a2): read the same instruments on a known-good surface over the same place (e.g. the base body's
own sculpt) as the target, ranked 2.
"""
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

_T = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
if _T not in sys.path:
    sys.path.append(_T)
import mesh_geom as MG  # noqa: E402


def r(x, n=3):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


def edge_turns(V, T):
    return MG.dihedral_edges(V, T)


def turn_stats(e, ang, sel):
    m = sel[e[:, 0]] & sel[e[:, 1]]
    a = ang[m]
    return {"max_deg": r(a.max(), 2), "p99_deg": r(np.percentile(a, 99), 2), "edges_over_20deg": int((a > 20).sum()), "edges": int(m.sum())}


def mean_curv(V, T):
    """(H, lumped area): 13a2's mean curvature, the engine's one cotangent Laplacian (mesh_geom)"""
    return MG.mean_curvature(V, T)


def curvature_roughness(V, T, sel, H=None, area=None, ball_mm=10.0):
    if H is None:
        H, area = mean_curv(V, T)
    ids = np.nonzero(sel)[0]
    near = np.nonzero(np.linalg.norm(V - V[ids].mean(0), axis=1) < np.linalg.norm(V[ids] - V[ids].mean(0), axis=1).max() + 0.03)[0]
    tr = cKDTree(V[near]); balls = tr.query_ball_point(V[ids], ball_mm * 1e-3)
    dev = np.empty(len(ids))
    for k, b in enumerate(balls):
        b = near[b]; dev[k] = H[ids[k]] - (H[b] * area[b]).sum() / area[b].sum()
    w = area[ids]
    o = np.argsort(np.abs(dev)); cw = np.cumsum(w[o]) / w.sum()
    return {"rms": r(np.sqrt((w * dev ** 2).sum() / w.sum()), 2), "p99_abs": r(np.abs(dev)[o][np.searchsorted(cw, 0.99)], 2),
            "max_abs": r(np.abs(dev).max(), 1), "vertices": int(len(ids))}


def quad_stats(V, sizes, flat, sel):
    starts = np.r_[0, np.cumsum(sizes)[:-1]]
    q = np.nonzero((sizes == 4) & sel)[0]
    if not len(q):
        return None
    P = V[flat[starts[q][:, None] + np.arange(4)]]
    ang = []
    for i in range(4):
        a = P[:, (i - 1) % 4] - P[:, i]; b = P[:, (i + 1) % 4] - P[:, i]
        ang.append(np.degrees(np.arccos(np.clip((a * b).sum(1) / np.maximum(np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-30), -1, 1))))
    ang = np.stack(ang, 1)
    el = np.stack([np.linalg.norm(P[:, (i + 1) % 4] - P[:, i], axis=1) for i in range(4)], 1)
    asp = el.max(1) / np.maximum(el.min(1), 1e-12)
    return {"quads": int(len(q)), "min_angle_p1_p5_deg": [round(float(x), 1) for x in np.percentile(ang.min(1), [1, 5])],
            "min_angle_min_deg": round(float(ang.min()), 2), "aspect_p99": round(float(np.percentile(asp, 99)), 2),
            "aspect_max": round(float(asp.max()), 1), "edge_mm_p5_p50_p95": [round(float(x) * 1e3, 2) for x in np.percentile(el, [5, 50, 95])]}


def turned_over(V_ref, V, T, tri_sel):
    n0 = MG.face_normals(V_ref, T); n1 = MG.face_normals(V, T)
    return int((tri_sel & ((n0 * n1).sum(1) < 0)).sum())


def crossings_near(V, T, sel, margin_m=0.1, V_nb=None):
    """V_nb: the positions the neighbourhood is chosen on (default V; 13a2 chose it on the new skin for both skins)"""
    import bvh
    W = V if V_nb is None else V_nb
    c = W[sel].mean(0); nb = np.linalg.norm(W[T].mean(1) - c, axis=1) < np.linalg.norm(W[sel] - c, axis=1).max() + margin_m
    Fs = T[nb]; ids = np.unique(Fs); loc = -np.ones(len(V), np.int64); loc[ids] = np.arange(len(ids))
    P = bvh.drop_shared(Fs, bvh.rays(V[ids], loc[Fs], overlap=True)["pairs"])
    inn = sel[Fs].any(1)
    P = P[inn[P[:, 0]] | inn[P[:, 1]]] if len(P) else P
    return int(len(P))


def changed_region(V_ref, V, T, sizes, flat, changed, sides=None, labels=("now", "ref")):
    a, b = labels
    e1, ang1 = edge_turns(V_ref, T); e2, ang2 = edge_turns(V, T)
    me = changed[e2[:, 0]] | changed[e2[:, 1]]
    tri_in = changed[T].any(1)
    starts = np.r_[0, np.cumsum(sizes)[:-1]]
    pin = np.maximum.reduceat(changed[flat].astype(np.int8), starts) > 0
    out = {"edges_over_90deg": {a: int((ang2[me] > 90).sum()), b: int((ang1[me] > 90).sum())},
           "edge_turn_max_deg": {a: r(ang2[me].max(), 2), b: r(ang1[me].max(), 2)},
           "triangles_turned_over_vs_" + b: turned_over(V_ref, V, T, tri_in),
           "quads": {a: quad_stats(V, sizes, flat, pin), b: quad_stats(V_ref, sizes, flat, pin)}}
    if sides is not None:                                              # a dict of masks, or a function of the positions
        sd = (lambda VV: sides(VV)) if callable(sides) else (lambda VV: sides)
        out["crossings"] = {a: {s: crossings_near(V, T, changed & m) for s, m in sd(V).items()},
                            b: {s: crossings_near(V_ref, T, changed & m) for s, m in sd(V_ref).items()}}
    return out
