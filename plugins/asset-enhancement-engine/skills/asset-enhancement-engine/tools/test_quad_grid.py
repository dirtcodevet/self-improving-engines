"""Proof of quad_grid.py on planted grids (A10). python engine/tools/test_quad_grid.py -> test_quad_grid.json beside it.
A flat 20 x 20 quad grid with known (i, j): the walk recovers (i, j) with no conflict; a 10 x 10 rectangle gives 100
quads and a 40-vertex boundary loop with 4 convex corners; inset by 2 rings adds 80 quads, keeps the patch a disc
(V - E + F = 1) and every quad with 4 distinct vertices; the harmonic map, mean-value and conformal layouts of a flat
patch reproduce its own (x, y) inside from the boundary (exact for a plane); a seam in the corner UVs gives 2 charts.
Build 13b: mirror_map recovers the planted mirror (i -> 20 - i) with no conflict, also when the shape is not
symmetric (its distance reads the planted 2 mm); grid_line walks one row to the boundary."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import quad_grid as QG  # noqa: E402


def grid(n=20, h=0.01):
    I, J = np.meshgrid(np.arange(n + 1), np.arange(n + 1), indexing="ij")
    V = np.c_[I.ravel() * h, J.ravel() * h, np.zeros(I.size)]
    vid = lambda i, j: i * (n + 1) + j
    Q = np.array([[vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)] for i in range(n) for j in range(n)], np.int64)
    return V, Q, np.c_[I.ravel(), J.ravel()]


def euler(Q):
    E = np.unique(np.sort(np.concatenate([Q[:, [0, 1]], Q[:, [1, 2]], Q[:, [2, 3]], Q[:, [3, 0]]]), 1), axis=0)
    return len(np.unique(Q)) - len(E) + len(Q)


def main():
    out = {}; ok = True
    V, Q, IJ = grid()
    seed = 0; ij, has, done, conf = QG.grid_coords(Q, seed, np.ones(len(Q), bool))
    rel = ij - ij[Q[seed, 0]]; true = IJ - IJ[Q[seed, 0]]
    same = bool((rel == true).all() or (rel == true[:, ::-1]).all())
    out["grid_coords"] = {"conflicts": int(conf), "recovers_ij": same, "all_reached": bool(has.all())}
    ok &= conf == 0 and same and has.all()
    fc = QG.rect_faces(Q, ij, has, 5, 15, 5, 15); loop = QG.boundary_loop(Q, fc); cvx, ccv = QG.corner_index(Q, fc, loop)
    out["rect"] = {"quads": int(len(fc)), "boundary_vertices": int(len(loop)), "convex_corners": int(len(cvx)), "concave": int(len(ccv))}
    ok &= len(fc) == 100 and len(loop) == 40 and len(cvx) == 4 and len(ccv) == 0
    Q2, rings, lp, nv2 = QG.inset(Q, fc, 2, len(V))
    out["inset"] = {"new_quads": int(len(Q2) - len(Q)), "rings": [int(len(r)) for r in rings], "euler_before_after": [int(euler(Q)), int(euler(Q2))],
                    "quads_with_4_distinct": bool(all(len(set(q)) == 4 for q in Q2.tolist()))}
    ok &= len(Q2) - len(Q) == 80 and euler(Q2) == 1 == euler(Q) and out["inset"]["quads_with_4_distinct"]
    # layouts of a flat patch: the 10 x 10 block, its boundary fixed at (x, y)
    verts = np.unique(Q[fc]); bnd = loop
    X = QG.harmonic(Q, verts, {int(b): V[b, :2] for b in bnd}, len(V))
    T = QG.quad_tris(Q[fc]); U1 = QG.mvc_uv(V, T, verts, {int(b): V[b, :2] for b in bnd})
    U2 = QG.lscm_uv(V, T, verts, {int(bnd[0]): V[bnd[0], :2], int(bnd[20]): V[bnd[20], :2]})
    err = lambda U: float(np.abs(U - V[verts, :2]).max())
    out["layouts_max_err_m"] = {"harmonic": err(X), "mean_value": err(U1), "lscm_two_pins": err(U2)}
    ok &= max(out["layouts_max_err_m"].values()) < 1e-9
    UVc = np.zeros((len(Q), 4, 2))
    for f, q in enumerate(Q):
        UVc[f] = V[q, :2] + (0.5 if IJ[q[0], 0] >= 10 else 0.0)            # a seam at i = 10
    nc, _ = QG.uv_charts(Q, np.arange(len(Q)), UVc)
    out["uv_charts_with_one_seam"] = int(nc); ok &= nc == 2
    # build 13b: the topological mirror of a grid symmetric about x = 10 h, with one row's quads cut asymmetric
    Vm = V.copy(); xm = 10 * 0.01
    mp, info = QG.mirror_map(Q, Vm, xm)
    want = np.array([int(np.where((IJ[:, 0] == 20 - i) & (IJ[:, 1] == j))[0][0]) for i, j in IJ])
    out["mirror_map"] = {"matches_planted": bool((mp == want).all()), **info}
    ok &= bool((mp == want).all()) and info["conflicts"] == 0
    Vs = Vm.copy(); Vs[IJ[:, 0] > 10, 1] += 0.002                   # a shape asymmetry only: topology mirror unchanged
    mp2, info2 = QG.mirror_map(Q, Vs, xm, tol=0.004)
    out["mirror_map_shape_asymmetric"] = {"matches_planted": bool((mp2 == want).all()), "max_mm": info2["mirror_distance_mm_p50_p99_max"][2]}
    ok &= bool((mp2 == want).all()) and abs(info2["mirror_distance_mm_p50_p99_max"][2] - 2.0) < 1e-6
    HE = QG.HalfEdges(Q); a = int(np.where((IJ[:, 0] == 3) & (IJ[:, 1] == 5))[0][0]); b = int(np.where((IJ[:, 0] == 4) & (IJ[:, 1] == 5))[0][0])
    line, closed = QG.grid_line(HE, a, b)
    out["grid_line"] = {"vertices": int(len(line)), "closed": bool(closed), "all_on_row_j5": bool((IJ[line, 1] == 5).all())}
    ok &= len(line) == 18 and not closed and bool((IJ[line, 1] == 5).all())   # i = 3 .. 20 (stops at the boundary)
    out["PASS"] = bool(ok)
    json.dump(out, open(os.path.join(HERE, "test_quad_grid.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
