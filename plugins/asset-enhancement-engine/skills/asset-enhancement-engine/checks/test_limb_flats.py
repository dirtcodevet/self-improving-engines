"""Proof of limb_flats.py on planted limbs (A10). python engine/checks/test_limb_flats.py -> test_limb_flats.json beside it.
A left "upper arm": a closed tube of radius 40 mm from a joint gh down 300 mm to an elbow (0.8 mm rings), standing
beside a "side wall" (a flat sheet facing it, 6 mm from its inner surface) and under an "armpit roof" (a small
downward-facing sheet 30 mm below gh, in the joint's frontal plane). Known answers:
  round tube          flat share ~0 at every station
  flat cut            the same tube with a chord cut 10 mm deep along its front: the chord is 0.215 of the outline
                      (closed form); the instrument reads 0.5-1.0x of it (measured 0.67x: its outline smoothing curves
                      the chord's ends) and over 5x the round tube
  clearance           p5 of the inner rays to the wall = 6 mm (+-0.3)
  vault               30 mm below the joint (+-0.5)
The right side is the mirror (x -> -x), so both sides read the same."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import limb_flats as LF  # noqa: E402

R, LEN, CUT, GAP, ROOF = 0.04, 0.30, 0.010, 0.006, 0.030


def tube(cx, cut_front=False, n_th=360, dz=0.0008):
    th = np.linspace(0, 2 * np.pi, n_th, endpoint=False); z = np.arange(0.0, -LEN - 1e-9, -dz)
    x = R * np.cos(th); y = R * np.sin(th)
    if cut_front:                                                    # front = -y: the chord y = -(R - CUT)
        y = np.maximum(y, -(R - CUT))
    TH, Z = np.meshgrid(np.arange(n_th), z, indexing="ij")
    V = np.c_[cx + x[TH.ravel()], y[TH.ravel()], Z.ravel()]; nz = len(z); vid = np.arange(len(V)).reshape(n_th, nz); F = []
    for i in range(n_th):
        j = (i + 1) % n_th
        for k in range(nz - 1):
            F += [[vid[i, k], vid[j, k], vid[j, k + 1]], [vid[i, k], vid[j, k + 1], vid[i, k + 1]]]
    F = np.array(F, np.int64)[:, [0, 2, 1]]                         # outward
    c0 = len(V); c1 = c0 + 1; V = np.vstack([V, [[cx, 0, 0], [cx, 0, -LEN]]])          # caps: the tube is closed
    F = np.vstack([F, [[c0, vid[(i + 1) % n_th, 0], vid[i, 0]] for i in range(n_th)], [[c1, vid[i, -1], vid[(i + 1) % n_th, -1]] for i in range(n_th)]])
    return V, F


def grid_sheet(P0, ea, eb, na, nb, down=False):
    """a flat grid: P0 + i ea + k eb, i < na, k < nb; faces wound so the normal is ea x eb (or its opposite)"""
    I, K = np.meshgrid(np.arange(na), np.arange(nb), indexing="ij")
    V = P0 + I.ravel()[:, None] * ea + K.ravel()[:, None] * eb; vid = np.arange(len(V)).reshape(na, nb); F = []
    for i in range(na - 1):
        for k in range(nb - 1):
            F += [[vid[i, k], vid[i + 1, k], vid[i + 1, k + 1]], [vid[i, k], vid[i + 1, k + 1], vid[i, k + 1]]]
    F = np.array(F, np.int64)
    return V, (F[:, [0, 2, 1]] if down else F)


def body(cut):
    parts = []; arm = []
    for sg in (1, -1):
        cx = sg * 0.20
        Vt, Ft = tube(cx, cut); parts.append((Vt, Ft)); arm.append(np.ones(len(Vt), bool))
        wall_x = cx - sg * (R + GAP)                                   # a side wall facing the arm, 6 mm from it
        Vw, Fw = grid_sheet(np.array([wall_x, -0.06, -0.33]), np.array([0, 0.002, 0]), np.array([0, 0, 0.002]), 61, 176, down=sg < 0)
        parts.append((Vw, Fw)); arm.append(np.zeros(len(Vw), bool))
        x0 = cx - sg * 0.045                                           # the armpit roof: ex x ey = +z, wound down
        Vr, Fr = grid_sheet(np.array([min(x0, x0 + sg * 0.04), -0.01, -ROOF]), np.array([0.001, 0, 0]), np.array([0, 0.001, 0]), 41, 21, down=True)
        parts.append((Vr, Fr)); arm.append(np.zeros(len(Vr), bool))
    V = []; F = []; off = 0
    for Vp, Fp in parts:
        V.append(Vp); F.append(Fp + off); off += len(Vp)
    return np.vstack(V), np.vstack(F), np.concatenate(arm)


def main():
    out = {}; ok = True
    J = {s: {"gh": np.array([sg * 0.20, 0.0, 0.0]), "elbow": np.array([sg * 0.20, 0.0, -LEN])} for s, sg in (("L", 1), ("R", -1))}
    al = np.arccos((R - CUT) / R); chord = 2 * R * np.sin(al); expected = chord / (chord + 2 * R * (np.pi - al))
    for name, cut in (("round", False), ("flat_cut", True)):
        V, F, arm = body(cut)
        r = LF.measure(V, F, J, arm, overlap=False)
        out[name] = {s: {k: r[s][k] for k in ("flat_share_mean", "flat_by_station", "stations_ok", "vault_apex_below_joint_mm", "inner_arm_clearance_mm")} for s in "LR"}
    out["flat_cut_expected"] = round(float(expected), 4)
    for s in "LR":
        ok &= out["round"][s]["flat_share_mean"] < 0.02 and out["round"][s]["stations_ok"] == 5
        ok &= 0.5 * expected < out["flat_cut"][s]["flat_share_mean"] <= expected and out["flat_cut"][s]["flat_share_mean"] > 5 * max(out["round"][s]["flat_share_mean"], 0.01)
        ok &= abs(out["round"][s]["inner_arm_clearance_mm"]["p5"] - GAP * 1000) < 0.3
        ok &= abs(out["round"][s]["vault_apex_below_joint_mm"] - ROOF * 1000) < 0.5
    out["PASS"] = bool(ok)
    json.dump(out, open(os.path.join(HERE, "test_limb_flats.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
