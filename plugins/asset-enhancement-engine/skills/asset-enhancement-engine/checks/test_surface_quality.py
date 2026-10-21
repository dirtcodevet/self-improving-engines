"""Proof of surface_quality.py on planted failures (A10). python engine/checks/test_surface_quality.py -> json beside it.
A smooth dome (radius 0.25 m, 1.5 mm grid, 12 x 12 cm) is the known-good surface; planted on copies of it:
  ridge     a 1.2 mm high, 3 mm wide sharp ridge across the middle   -> edge turn max and roughness rise many-fold
  dent      a 0.8 mm deep, 6 mm (sd) Gaussian dent                    -> roughness rises; edge turn stays modest
  fold      one vertex pushed 4 mm sideways, past its neighbour                 -> edges over 90 deg and turned-over triangles
  crossing  a separate triangle pierced through the sheet             -> crossings_near counts it (Blender BVH)
and the clean dome reads 0 folds, 0 turned over, 0 crossings, a small roughness."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import surface_quality as SQ  # noqa: E402


def dome(h=0.0015, half=0.06, R=0.25):
    x = np.arange(-half, half + 1e-9, h); X, Y = np.meshgrid(x, x, indexing="ij"); n = len(x)
    Z = np.sqrt(R * R - X ** 2 - Y ** 2) - R
    V = np.c_[X.ravel(), Y.ravel(), Z.ravel()]; vid = np.arange(len(V)).reshape(n, n)
    Q = np.array([[vid[i, j], vid[i + 1, j], vid[i + 1, j + 1], vid[i, j + 1]] for i in range(n - 1) for j in range(n - 1)], np.int64)
    T = np.concatenate([Q[:, [0, 1, 2]], Q[:, [0, 2, 3]]])
    return V, T, Q


def main():
    out = {}; ok = True
    V, T, Q = dome(); sizes = np.full(len(Q), 4); flat = Q.ravel()
    centre = np.linalg.norm(V[:, :2], axis=1) < 0.03
    def read(VV):
        e, a = SQ.edge_turns(VV, T)
        return {"edge_turn": SQ.turn_stats(e, a, centre), "roughness": SQ.curvature_roughness(VV, T, centre)}
    clean = read(V); out["clean"] = clean
    Vr = V.copy(); Vr[:, 2] += 0.0012 * np.clip(1 - np.abs(V[:, 0]) / 0.0015, 0, 1); ridge = read(Vr); out["ridge"] = ridge
    Vd = V.copy(); Vd[:, 2] -= 0.0008 * np.exp(-((V[:, 0] - 0.01) ** 2 + V[:, 1] ** 2) / (2 * 0.006 ** 2)); dent = read(Vd); out["dent"] = dent
    ok &= ridge["edge_turn"]["max_deg"] > 10 * max(clean["edge_turn"]["max_deg"], 0.1) and ridge["roughness"]["rms"] > 5 * max(clean["roughness"]["rms"], 0.5)
    ok &= dent["roughness"]["rms"] > 3 * max(clean["roughness"]["rms"], 0.5)
    Vf = V.copy(); k = int(np.argmin(np.linalg.norm(V[:, :2] - [0.005, 0.005], axis=1))); Vf[k, 0] += 0.004
    changed = np.zeros(len(V), bool); changed[k] = True
    cr = SQ.changed_region(V, Vf, T, sizes, flat, changed, labels=("fold", "clean"))
    out["fold"] = cr; ok &= cr["edges_over_90deg"]["fold"] > 0 and cr["triangles_turned_over_vs_clean"] > 0 and cr["edges_over_90deg"]["clean"] == 0
    # a triangle pierced through the sheet near the centre (a separate shell)
    V2 = np.vstack([V, [[-0.004, 0, -0.004], [0.004, 0, -0.004], [0, 0, 0.004]]]); n = len(V)
    T2 = np.vstack([T, [[n, n + 1, n + 2]]]); sel = np.zeros(len(V2), bool); sel[n:] = True; selc = np.zeros(len(V), bool); selc[centre] = True
    out["crossings"] = {"pierced": SQ.crossings_near(V2, T2, sel), "clean_centre": SQ.crossings_near(V, T, selc)}
    ok &= out["crossings"]["pierced"] >= 1 and out["crossings"]["clean_centre"] == 0
    out["PASS"] = bool(ok)
    json.dump(out, open(os.path.join(HERE, "test_surface_quality.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
