"""Proof of engine/checks/mesh_faults.py (build K1, 2026-10-21), answers known without the checker:
  fold:      a flat 30 x 30 mm sheet (1 mm quads) bent by 120 deg about x = 15 mm -> exactly the 30 hinge edges at 120,
             sense one-signed; every other edge 0 deg
  crossing:  a flat sheet and a vertical sheet through it -> a pair crosses iff the two triangles' x-intervals on the
             common line overlap (counted analytically)
  inverted:  one triangle of a flat sheet with its winding reversed -> exactly that triangle; none on the clean sheet
  clusters:  the bent sheet and the crossing pair 50 mm apart -> 2 clusters, each with its own counts
  skin:      (optional, `--skin PACK_DIR`) the engine copy against the K1 map's numbers on 13a3's skin (787 folds past
             90, 209 past 150, 3,439 pairs, 3.695 cm2, 159 inside-out faces, 27 clusters: the map's proven instrument)
    python engine/checks/test_mesh_faults.py [--skin cases/woman2/build13/pack_b13a3]
Writes test_mesh_faults.json beside this file.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mesh_faults as MF  # noqa: E402


def grid(nx, ny, h):
    xs, ys = np.meshgrid(np.arange(nx + 1) * h, np.arange(ny + 1) * h, indexing="ij")
    V = np.c_[xs.ravel(), ys.ravel(), np.zeros(xs.size)]
    idx = lambda i, j: i * (ny + 1) + j  # noqa: E731
    Q = [[idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)] for i in range(nx) for j in range(ny)]
    return V, np.array(Q)


def interval(P, axis, val):
    d = P[:, axis] - val
    pts = []
    for i in range(3):
        a, b = P[i], P[(i + 1) % 3]; da, db = d[i], d[(i + 1) % 3]
        if da == 0:
            pts.append(a[0])
        if (da < 0 < db) or (db < 0 < da):
            t = da / (da - db); pts.append(a[0] + t * (b[0] - a[0]))
    return (min(pts), max(pts)) if pts else None


def main():
    out = {}; ok = True
    # fold
    PHI = 120.0
    V, Q = grid(30, 30, 1e-3)
    T, _ = MF.tris(np.full(len(Q), 4), Q.ravel())
    m = V[:, 0] > 15e-3 + 1e-9
    ph = np.radians(PHI); dx = V[m, 0] - 15e-3
    V[m, 0] = 15e-3 + dx * np.cos(ph); V[m, 2] = dx * np.sin(ph)
    F = MF.folds(V, T); sel = F["ang"] > 90
    hinge = np.all(np.isclose(V[F["e"][sel]][:, :, 0], 15e-3), 1)
    out["fold"] = dict(planted=30, found=int(sel.sum()), on_hinge=int(hinge.sum()),
                       deg=[round(float(F["ang"][sel].min()), 6), round(float(F["ang"][sel].max()), 6)],
                       sense=sorted(set(F["sense"][sel].tolist())), others_max_deg=round(float(F["ang"][~sel].max()), 6))
    ok &= out["fold"]["found"] == 30 and out["fold"]["on_hinge"] == 30 and abs(out["fold"]["deg"][0] - PHI) < 1e-6 \
        and len(out["fold"]["sense"]) == 1 and out["fold"]["others_max_deg"] < 1e-4
    Vfold, Tfold = V.copy(), T.copy()

    # crossing
    VA, QA = grid(20, 20, 1e-3); VB, QB = grid(9, 7, 1e-3); y0 = 10.37e-3
    VB = np.c_[VB[:, 0] + 3.21e-3, np.full(len(VB), y0), VB[:, 1] - 3.53e-3]
    V = np.r_[VA, VB]; Q = np.r_[QA, QB + len(VA)]
    T, _ = MF.tris(np.full(len(Q), 4), Q.ravel())
    inA = T[:, 0] < len(VA)
    pr = MF.crossings(V, T, slab=0.004)
    ia, ib = np.nonzero(inA)[0], np.nonzero(~inA)[0]
    IA = [interval(V[T[i]], 1, y0) for i in ia]; IB = [interval(V[T[j]], 2, 0.0) for j in ib]
    truth = set()
    for i, a in zip(ia, IA):
        if a is None:
            continue
        for j, b in zip(ib, IB):
            if b is not None and min(a[1], b[1]) - max(a[0], b[0]) > 1e-12:
                truth.add((min(i, j), max(i, j)))
    got = set(map(tuple, pr.tolist()))
    out["crossing"] = dict(analytic=len(truth), found=len(got), missed=len(truth - got), extra=len(got - truth))
    ok &= len(truth) > 0 and not (truth - got) and not (got - truth)

    # inverted
    V, Q = grid(12, 12, 1e-3)
    T, _ = MF.tris(np.full(len(Q), 4), Q.ravel())
    clean = int(MF.inverted(V, T).sum())
    T2 = T.copy(); k = 77; T2[k] = T2[k][[0, 2, 1]]
    inv = MF.inverted(V + np.c_[np.zeros((len(V), 2)), 1e-4 * np.sin(V[:, 0] * 300)], T2)
    out["inverted"] = dict(clean=clean, planted_tri=k, found=np.nonzero(inv)[0].tolist())
    ok &= clean == 0 and out["inverted"]["found"] == [k]

    # clusters: the bent sheet + the crossing pair far apart
    Vc, Qc = grid(4, 4, 1e-3)
    Vx = np.r_[Vc, np.c_[Vc[:, 0] + 1e-3, np.full(len(Vc), 2e-3), Vc[:, 1] - 2e-3]] + np.array([0.05, 0, 0])
    Qx = np.r_[Qc, Qc + len(Vc)]
    Tx, _ = MF.tris(np.full(len(Qx), 4), Qx.ravel())
    V = np.r_[Vfold, Vx]; T = np.r_[Tfold, Tx + len(Vfold)]
    M = MF.measure(V, T)
    out["clusters"] = dict(n=M["summary"]["clusters"], each=[(c["fold_edges"], c["crossing_pairs"]) for c in M["clusters"]])
    ok &= M["summary"]["clusters"] == 2 and sorted(c["fold_edges"] for c in M["clusters"]) == [0, 30] \
        and all((c["fold_edges"] == 0) == (c["crossing_pairs"] > 0) for c in M["clusters"])

    if "--skin" in sys.argv:
        d = sys.argv[sys.argv.index("--skin") + 1]
        S = np.load(os.path.join(d, "skin.npz"))
        T, _ = MF.tris(S["poly_sizes"], S["poly_verts"])
        M = MF.measure(S["v"].astype(float), T)
        s = M["summary"]
        want = dict(folds_over_deg=787, folds_over_150=209, crossing_pairs=3439, crossing_area_cm2=3.695, inverted_faces=159, clusters=27)
        out["skin"] = dict(pack=d, got={k: s[k] for k in want}, want=want)
        ok &= all((round(s[k], 3) == v) for k, v in want.items())
    out["pass"] = bool(ok)
    with open(os.path.join(HERE, "test_mesh_faults.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out, indent=1))
    print("PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
