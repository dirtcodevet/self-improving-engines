"""Fit a SOURCE / SINK model of hair tracts to trusted photo measurements (runs outside Blender).

Anatomy describes hair tracts as streams that leave sources (the nose, whorls) and gather at sinks (where streams
converge: ear bases, the angles of the jaw, the neck). As a field: v(q) = sum_i k_i (q - s_i) / (|q - s_i|^2 + eps^2)
in the head frame, projected onto the skin's tangent plane; k > 0 a source, k < 0 a sink. Left/right sinks mirror.
Domain-neutral: the same model describes whorls in human hair, grass bending around obstacles, wood grain at knots.

The free values (sink offsets from their landmarks, strengths) are fitted to the photo's TRUSTED directions
(hair_field.py EXPORT); the person's marked directions are NOT used here - they are the held-out test
(review/flow_marks_check.py). Output is a case file: fitted values carry their case (engine-grounding G7).

usage: python fit_tracts.py <trusted_flow.npz> <landmarks.json> <out.json>
"""
import json
import sys

import numpy as np
from scipy.optimize import minimize

ZONES = (1, 2, 4, 5)            # head, forehead/temple, muzzle, cheek (eye surround and ears have their own rules)


sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from hair_tracts import unit, tract_nodes, source_sink_field          # ONE definition, shared with the groom  # noqa: E402

NAMES = ["nose_dy", "nose_dz", "ear_dy", "ear_dz", "ear_k", "jaw_xfrac", "jaw_dy", "jaw_dz", "jaw_k",
         "neck_y", "neck_z", "neck_k"]
nodes = lambda L, R, H0, p: tract_nodes(L, dict(zip(NAMES, p)))
field = source_sink_field


P0 = np.array([0.004, 0.006, 0.0, -0.006, -0.4, 0.9, -0.010, -0.040, -0.6, 0.040, -0.050, -0.5])
BOUNDS = [(-0.02, 0.02), (-0.01, 0.02), (-0.02, 0.02), (-0.03, 0.01), (-2, 0), (0.5, 1.4), (-0.04, 0.03),
          (-0.07, -0.01), (-2, 0), (0.0, 0.09), (-0.10, 0.0), (-2, 0)]

if __name__ == "__main__":
    D = np.load(sys.argv[1]); J = json.load(open(sys.argv[2])); L = J["landmarks"]
    R, H0 = np.array(L["head_R"]), np.array(L["head"])
    sel = (D["w"] > 0.4) & np.isin(D["zone"], ZONES)
    q, nq, T, w = (D["P"][sel] - H0) @ R, unit(D["N"][sel] @ R), unit(D["T"][sel] @ R), D["w"][sel]
    rng = np.random.default_rng(0)
    idx = rng.permutation(len(q)); fit_i, val_i = idx[: int(0.8 * len(q))], idx[int(0.8 * len(q)):]

    def err(p, ii):
        v = field(q[ii], nq[ii], nodes(L, R, H0, p))
        return np.degrees(np.arccos(np.clip(np.abs((v * T[ii]).sum(1)), 0, 1)))          # orientation error

    loss = lambda p: np.average(np.minimum(err(p, fit_i), 60) ** 2, weights=w[fit_i])     # robust: cap outliers
    e0 = err(P0, val_i)
    res = minimize(loss, P0, method="Powell", bounds=BOUNDS, options=dict(maxiter=4000, xtol=1e-4, ftol=1e-3))
    e1 = err(res.x, val_i)
    print(f"trusted points {len(q)} (fit {len(fit_i)}, check {len(val_i)})")
    print(f"orientation error on the check split: start {np.median(e0):.1f} deg median, fitted {np.median(e1):.1f} deg "
          f"(p90 {np.percentile(e0, 90):.0f} -> {np.percentile(e1, 90):.0f})")
    names = NAMES
    out = dict(model="source/sink hair tracts, head frame (metres)", fitted_on="cat1 photo, trusted directions",
               note="fitted values carry their case (engine-grounding G7): defaults only after holding on another case",
               params=dict(zip(names, map(float, res.x))), zones=list(ZONES),
               check_split_median_deg=dict(start=float(np.median(e0)), fitted=float(np.median(e1))))
    json.dump(out, open(sys.argv[3], "w"), indent=1)
    print(json.dumps(out["params"], indent=0))
