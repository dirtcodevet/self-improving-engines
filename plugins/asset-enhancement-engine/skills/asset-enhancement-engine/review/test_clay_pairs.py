"""Proof of clay_pairs.py / clay_rake_bl.py on a planted relief (A10). python engine/review/test_clay_pairs.py
-> test_clay_pairs.json beside it (renders in a temporary folder; ~1 min, background Blender).
A smooth dome (radius 0.25 m, 12 x 12 cm, 1.5 mm grid) facing the camera, and the same dome with a planted bump 0.3 mm
high (Gaussian, sd 4 mm) 2 cm right of centre; both rendered with the same camera and the same raking light. Known
answer: the pair differs inside the bump's projected box and not outside it (mean |difference| inside >= 10x outside),
and project_box puts the bump where it is."""
import json
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clay_pairs as CP  # noqa: E402


def dome(bump=0.0, h=0.0015, half=0.06, R=0.25):
    x = np.arange(-half, half + 1e-9, h); X, Z = np.meshgrid(x, x, indexing="ij"); n = len(x)
    Y = -(np.sqrt(R * R - X ** 2 - Z ** 2) - R)                       # faces -y (the front), apex at y = 0
    Y = Y - bump * np.exp(-((X - 0.02) ** 2 + Z ** 2) / (2 * 0.004 ** 2))
    V = np.c_[X.ravel(), Y.ravel(), Z.ravel()]; vid = np.arange(len(V)).reshape(n, n)
    Q = np.array([[vid[i, j], vid[i, j + 1], vid[i + 1, j + 1], vid[i + 1, j]] for i in range(n - 1) for j in range(n - 1)], np.int64)
    return V, Q


def main():
    from PIL import Image
    tmp = tempfile.mkdtemp(prefix="clay_pairs_"); out = {}; ok = True
    try:
        meshes = {}
        for tag, b in (("clean", 0.0), ("bump", 0.0003)):
            V, Q = dome(b); p = os.path.join(tmp, tag + ".npz")
            np.savez(p, v=V.astype(np.float32), poly_sizes=np.full(len(Q), 4), poly_verts=Q.ravel()); meshes[tag] = p
        view = {"name": "front", "loc": [0, -0.45, 0], "target": [0, 0, 0], "lens": 85.0, "resolution": [400, 400], "rake_from": 0, "rake_elev": 12}
        CP.render({"samples": 16, "views": [view]}, meshes, tmp)
        A = np.asarray(Image.open(os.path.join(tmp, "clean", "front.png")).convert("L"), float)
        B = np.asarray(Image.open(os.path.join(tmp, "bump", "front.png")).convert("L"), float)
        x0, y0, x1, y1 = CP.project_box(view, np.array([[0.02 + dx, 0, dz] for dx in (-0.01, 0.01) for dz in (-0.01, 0.01)]))
        m = np.zeros(A.shape, bool); m[int(y0):int(y1) + 1, int(x0):int(x1) + 1] = True
        D = np.abs(A - B); inside, outside = float(D[m].mean()), float(D[~m].mean())
        cx, cy = CP.project_box(view, np.array([[0.02, 0.0, 0.0]]))[:2]
        out = {"box_px": [round(v, 1) for v in (x0, y0, x1, y1)], "bump_centre_px": [round(cx, 1), round(cy, 1)],
               "mean_abs_diff_inside": round(inside, 3), "mean_abs_diff_outside": round(outside, 4),
               "ratio": round(inside / max(outside, 1e-6), 1)}
        CP.pair(os.path.join(tmp, "clean", "front.png"), os.path.join(tmp, "bump", "front.png"), os.path.join(tmp, "pair.png"), "planted bump", "clean", "bump")
        out["pair_size"] = list(Image.open(os.path.join(tmp, "pair.png")).size)
        ok &= inside >= 10 * max(outside, 0.01) and 200 < cx < 300 and 190 < cy < 210 and out["pair_size"] == [812, 444]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out["PASS"] = bool(ok)
    json.dump(out, open(os.path.join(HERE, "test_clay_pairs.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
