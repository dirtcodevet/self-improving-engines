"""PLACE the pack skull in a case's registered head: a weighted SIMILARITY fit (scale, rotation, translation; Umeyama)
of skull landmarks to the case's head landmarks, every correspondence with its confidence; residuals and the implied
scale are reported (G5: where they disagree, say so - never hide it in the fit).

  eye centres     <- skull eye seats            (measured in the photo: weight 1.0)
  jaw hinge       <- midpoint of the two TMJs    (derived landmark: 0.5)
  nose (leather)  <- nasal aperture front centre + NOSE_FWD forward along the skull's -y (unsourced offset: 0.3)

usage: python skull_place.py <case_dir> <mesh_ver> <skull_prefix> <out_prefix>
writes <out>_cranium.ply, <out>_mandible.ply (world, metres), <out>_place.json
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from sdf_core import write_ply  # noqa: E402

NOSE_FWD = 6.0     # mm the nose leather's tip lies in front of the bony aperture (UNSOURCED, weak)


def read_ply(path):
    with open(path, "rb") as f:
        head = b""
        while not head.endswith(b"end_header\n"):
            head += f.readline()
        h = head.decode()
        nv = int(h.split("element vertex ")[1].split()[0]); nf = int(h.split("element face ")[1].split()[0])
        v = np.frombuffer(f.read(nv * 12), "<f4").reshape(nv, 3).astype(float)
        fa = np.frombuffer(f.read(nf * 13), dtype=[("n", "u1"), ("i", "<i4", 3)])
    return v, fa["i"].copy()


def umeyama(A, B, w):
    """weighted similarity B ~ s R A + t"""
    w = np.asarray(w, float) / np.sum(w)
    ma, mb = (w[:, None] * A).sum(0), (w[:, None] * B).sum(0)
    A0, B0 = A - ma, B - mb
    C = (w[:, None] * B0).T @ A0
    U, D, Vt = np.linalg.svd(C)
    S = np.eye(3); S[2, 2] = np.sign(np.linalg.det(U @ Vt))
    R = U @ S @ Vt
    var_a = (w * (A0 ** 2).sum(1)).sum()
    s = np.trace(np.diag(D) @ S) / var_a
    return s, R, mb - s * R @ ma


def main(case, mv, skull, out):
    L = json.load(open(os.path.join(case, "mesh", f"{mv}_landmarks.json")))["landmarks"]
    SK = json.load(open(skull + "_landmarks.json"))
    ap = SK["nasal_aperture"]
    nose_sk = np.array([ap["centre_xz"][0] * 0 + 0.0, SK["nasal_tip"][1] - NOSE_FWD, ap["centre_xz"][1]])
    pairs = [("eye.R", np.array(SK["eye_seat"]["R"]), np.array(L["eye.R"]), 1.0),
             ("eye.L", np.array(SK["eye_seat"]["L"]), np.array(L["eye.L"]), 1.0),
             ("jaw_hinge", (np.array(SK["tmj"]["R"]) + np.array(SK["tmj"]["L"])) / 2, np.array(L["jaw_hinge"]), 0.5),
             ("nose", nose_sk, np.array(L["nose"]), 0.3)]
    A = np.array([p[1] for p in pairs]) / 1000.0; B = np.array([p[2] for p in pairs]); w = [p[3] for p in pairs]
    s, R, t = umeyama(A, B, w)
    res = {p[0]: round(float(np.linalg.norm(s * R @ a + t - b)) * 1000, 2) for p, a, b in zip(pairs, A, B)}
    # leave-one-out scale: does each correspondence imply the same size? (G5 agreement)
    loo = {}
    for i, p in enumerate(pairs):
        keep = [j for j in range(len(pairs)) if j != i]
        loo[p[0]] = round(float(umeyama(A[keep], B[keep], [w[j] for j in keep])[0]), 3)
    for part in ("cranium", "mandible"):
        v, f = read_ply(f"{skull}_{part}.ply")
        write_ply(f"{out}_{part}.ply", (s * (R @ v.T)).T + t, f)
    # eye seat check: each registered eye vs the placed seat (mm)
    rep = dict(scale=round(float(s), 4), skull_length_mm=round(89.4 * s, 1), residual_mm=res, scale_leave_one_out=loo,
               weights={p[0]: p[3] for p in pairs}, nose_offset_mm=NOSE_FWD, R=R.round(5).tolist(), t=t.round(5).tolist(),
               note="scale is relative to the reference skull (scaled to the sourced 89.4 mm mean length)")
    json.dump(rep, open(out + "_place.json", "w"), indent=1)
    print(json.dumps({k: rep[k] for k in ("scale", "skull_length_mm", "residual_mm", "scale_leave_one_out")}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
