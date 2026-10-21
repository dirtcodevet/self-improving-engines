"""RIG STATE for the target-driven loop: a rigged pack posed in numpy exactly as Blender poses it, and a change made
on the posed surface stored back as the pose's rest-space corrective key (2026-10-19, woman2 v5).

Why: forms that exist only with a limb moved (an arm raised) must be measured and solved where they live, in the posed
frame, but the rig stores them as rest-space shape keys that Blender adds BEFORE skinning. engine/tools/
posed_correctives.py holds the math (weights normalised as Blender's armature modifier does); this module reads a
pack (skin.npz, weights.npz, shape_keys.npz, pose_matrices.npz) so a job needs no live Blender. Matches Blender to
0.0001 mm at every keyed pose of base_female_torso v5.

  pk = load_pack(pack_dir)
  st = posed_state(pk, total_deg)            # {"V": posed, "F", "A": skinning matrices, "T": total, masks...}
  keys = posed_change_to_keys(pk, st, V_new, side_sign=+1 or -1 or None)   # updated sparse keys dict
  save_keys(keys, path)
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import posed_correctives as PC  # noqa: E402


def load_pack(pack_dir):
    sk = np.load(os.path.join(pack_dir, "skin.npz"))
    Wd = np.load(os.path.join(pack_dir, "weights.npz"))
    pm = np.load(os.path.join(pack_dir, "pose_matrices.npz"))
    pk = {"dir": pack_dir, "V": sk["v"].astype(np.float64), "F": sk["f"].astype(np.int64),
          "masks": {k: sk[k] for k in sk.files if k not in ("v", "f", "note")},
          "W": Wd["W"].astype(np.float64), "groups": [str(x) for x in Wd["names"]],
          "keys": dict(np.load(os.path.join(pack_dir, "shape_keys.npz"))),
          "M": {int(t): pm["M_T%d" % t] for t in pm["totals_deg"]}, "bones": [str(b) for b in pm["bones"]]}
    return pk


def dense_key(pk, name, keys=None):
    keys = pk["keys"] if keys is None else keys
    d = np.zeros_like(pk["V"]); d[keys["idx_" + name]] = keys["d_" + name]; return d


def posed_state(pk, total_deg, keys=None):
    """the skin at a keyed total abduction (both arms): rest + that pose's keys, skinned. Only keyed poses (the
    matrices stored in the pack); the key named abd<T>_<side> is at full weight there, the others at zero."""
    T = int(total_deg); M = pk["M"][T]
    A = PC.skin_matrices(np.stack([pk["W"][:, pk["groups"].index(b)] for b in pk["bones"]], 1), M)
    Y = pk["V"].copy()
    if T > 0:
        for s in "LR":
            Y += dense_key(pk, "abd%d_%s" % (T, s), keys)
    st = {"V": PC.skin(Y, A), "F": pk["F"], "A": A, "T": T}
    st.update(pk["masks"])
    return st


def posed_change_to_keys(pk, st, V_new, side_sign=None, keys=None):
    """the posed change V_new - st["V"] as rest-space offsets added to the pose's corrective keys (each side's key
    takes its own side's vertices); returns an updated copy of the sparse keys dict"""
    keys = dict(pk["keys"] if keys is None else keys); T = st["T"]
    d = PC.to_rest(V_new - st["V"], st["A"])
    for s, sg in (("L", 1), ("R", -1)):
        if side_sign is not None and sg != side_sign:
            continue
        name = "abd%d_%s" % (T, s)
        dk = dense_key(pk, name, keys) + np.where((np.sign(pk["V"][:, 0]) == sg)[:, None], d, 0.0)
        idx = np.where(np.abs(dk).max(1) > 1e-9)[0]
        keys["idx_" + name] = idx.astype(np.int32); keys["d_" + name] = dk[idx].astype(np.float32)
    return keys


def save_keys(keys, path):
    np.savez_compressed(path, **keys)
