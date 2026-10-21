"""Proof of pack_carry.py on a planted pack (A10). python engine/loop/test_pack_carry.py -> test_pack_carry.json beside it.
A pack (a UV sphere R = 0.1 m skin with a mask, a note, a json and a png) carried with 50 vertices moved 1 mm inside a
declared disc: the copied files are byte for byte the previous ones, every skin array but v is the previous one, v is
the new positions in float32, the note is extended; a28_diff reads 50 moved, 0 outside, then 1 outside when one vertex
outside the disc is moved too; depth_under reads planted points 5 mm inside / 5 mm outside the sphere as +-5 mm."""
import json
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, "..", "tools"))
import pack_carry as PC  # noqa: E402
from test_mesh_geom import sphere  # noqa: E402


def main():
    out = {}; ok = True
    tmp = tempfile.mkdtemp(prefix="pack_carry_")
    try:
        V, F = sphere(0.1); a = os.path.join(tmp, "a"); b = os.path.join(tmp, "b"); os.makedirs(a)
        mask = (V[:, 2] > 0.05)
        np.savez_compressed(os.path.join(a, "skin.npz"), v=V.astype(np.float32), f=F, breast=mask, note="the base.")
        json.dump({"x": 1}, open(os.path.join(a, "measurements.json"), "w")); open(os.path.join(a, "map.png"), "wb").write(bytes(range(256)))
        disc = np.linalg.norm(V - [0, 0, 0.1], axis=1) < 0.03
        ids = np.nonzero(disc)[0][:50]; V2 = V.copy(); V2[ids] -= 0.001 * V[ids] / 0.1
        S = PC.carry(a, b, V2, " Moved 50 vertices.", copy=["map.png"])
        out["copied_bytes_same"] = open(os.path.join(a, "map.png"), "rb").read() == open(os.path.join(b, "map.png"), "rb").read()
        out["not_copied_left_out"] = not os.path.exists(os.path.join(b, "measurements.json"))
        out["arrays_same"] = bool(np.array_equal(S["f"], F) and np.array_equal(S["breast"], mask))
        out["v_new_float32"] = bool(S["v"].dtype == np.float32 and np.array_equal(S["v"], V2.astype(np.float32)))
        out["note"] = str(S["note"])
        d1 = PC.a28_diff(V.astype(np.float32).astype(float), S["v"].astype(float), disc, masks={"breast": mask})
        V3 = V2.copy(); V3[np.nonzero(~disc)[0][0], 0] += 0.002; d2 = PC.a28_diff(V, V3, disc)
        out["diff_inside_only"] = d1; out["diff_one_outside"] = d2
        P = np.array([[0, 0, 0.095], [0, 0, 0.105], [0.0707, 0, 0.0707 + 0.0]]) ; P[2] = P[2] / np.linalg.norm(P[2]) * 0.095
        dep = PC.depth_under(V, F, P) * 1000; out["depth_mm"] = dep.round(3).tolist()
        ok &= out["copied_bytes_same"] and out["not_copied_left_out"] and out["arrays_same"] and out["v_new_float32"]
        ok &= out["note"] == "the base. Moved 50 vertices." and d1["moved_vertices"] == 50 and d1["moved_outside_declared"] == 0
        ok &= d2["moved_outside_declared"] == 1 and abs(d2["outside_declared_max_mm"] - 2.0) < 1e-9
        ok &= abs(dep[0] - 5) < 0.1 and abs(dep[1] + 5) < 0.1 and abs(dep[2] - 5) < 0.1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out["PASS"] = bool(ok)
    json.dump(out, open(os.path.join(HERE, "test_pack_carry.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
