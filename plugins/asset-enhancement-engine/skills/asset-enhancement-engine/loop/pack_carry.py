"""A NEW PACK FROM THE LAST ONE with the skin moved (build A1, 2026-10-21; the steps woman2's build 13 copied from
s5_pack.py into a2_pack, a3_pack and a4_pack, now written once).

  S = carry(prev_dir, out_dir, V, note, copy=None, keep=("skin.npz",))
      out_dir made afresh; every file of prev_dir copied byte for byte (or only those in `copy`) except the ones the
      caller re-reads on the new skin (`keep` names files NOT copied); skin.npz written with the new positions (float32)
      and every other array of the previous skin as it was, its note extended by `note`. Returns the new skin (np.load)
  d = a28_diff(V_prev, V, declared, masks=None)
      A28 item 9, one diff against the last checked state: the vertices that moved, how many and how far outside the
      region the build declared it may change (0 / 0.0 when it held), the largest move under each named mask, and the
      moves inside the region (p50 / p99 / max, mm)
  dep = depth_under(V, T, P)
      signed depth (m) of points P under the surface (V, T): + inside (behind the nearest face's normal), - outside;
      e.g. a rib cage under a skin (a point outside the skin is a defect)
What reads the skin (chest wall, measurements, the case's own tables) stays with the case: carry() only moves files.
Proof: engine/loop/test_pack_carry.py (a planted pack; json beside it).
"""
import os
import shutil
import sys

import numpy as np

_T = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
if _T not in sys.path:
    sys.path.append(_T)
import mesh_geom as MG  # noqa: E402


def carry(prev_dir, out_dir, V, note, copy=None, keep=("skin.npz",)):
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    names = copy if copy is not None else sorted(f for f in os.listdir(prev_dir) if os.path.isfile(os.path.join(prev_dir, f)) and f not in keep)
    for f in names:
        shutil.copy2(os.path.join(prev_dir, f), os.path.join(out_dir, f))
    S0 = np.load(os.path.join(prev_dir, "skin.npz"))
    arrays = {k: S0[k] for k in S0.files if k not in ("v", "note")}
    np.savez_compressed(os.path.join(out_dir, "skin.npz"), v=np.asarray(V).astype(np.float32), **arrays,
                        note=(str(S0["note"]) if "note" in S0.files else "") + note)
    return np.load(os.path.join(out_dir, "skin.npz"))


def _r(x, n=3):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


def a28_diff(V_prev, V, declared, masks=None):
    d = np.linalg.norm(np.asarray(V, float) - np.asarray(V_prev, float), axis=1) * 1e3
    out = {"declared_region_vertices": int(declared.sum()), "moved_vertices": int((d > 0).sum()),
           "moved_outside_declared": int(((d > 0) & ~declared).sum()), "outside_declared_max_mm": float(d[~declared].max())}
    for k, m in (masks or {}).items():
        out[k + "_max_mm"] = float(d[m].max())
    out["inside_p50_p99_max_mm"] = [_r(x, 3) for x in np.percentile(d[declared], [50, 99, 100])]
    return out


def depth_under(V, T, P):
    MP = MG.MeshProj(V, T); X, dist, f = MP.project(P)
    return -np.sign(((P - X) * MP.n[f]).sum(1)) * dist
