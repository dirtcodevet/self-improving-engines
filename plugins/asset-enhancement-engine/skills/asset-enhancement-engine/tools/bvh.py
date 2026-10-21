"""BVH queries from system Python, run in background factory-startup Blender (bl_bvh.py beside this; never a live Blender).
Made in build 13a as cases/woman2/build13/b13lib.rays(), moved here in build A1 (2026-10-21).

  rays(V, F, O=None, D=None, Q=None, overlap=False, maxd=0.4, min_hit=3e-4) -> dict
      O, D (k, 3): first hit beyond min_hit along each ray (dist (k,), NaN = none within maxd; hit_face (k,));
      Q (j, 3): nearest surface point (near_d, near_p, near_n, near_face);  overlap=True: self-overlapping triangle
      pairs (pairs (p, 2); pairs that share a vertex are included: drop them with drop_shared(F, pairs)).
  inside(V, F, ids, V0, rest_sep, maxd_in, overlap=False) -> dict (build 13c): skin passed into the body's volume (odd
      crossings along the outward normal of a closed skin) and its depth along the inward normal.
  blender(script, *args, log=None, timeout=3600) -> stdout tail: any background Blender job, raising on a traceback.
Each call writes its in/out files to a fresh temporary folder (absolute paths: a relative output path in Blender -b
lands under Blender's own working folder, and renders were lost that way in build 13a), so calls can run in parallel.
"""
import os
import shutil
import subprocess
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"


def blender(script, *args, log=None, timeout=3600):
    cmd = [BLENDER, "-b", "--factory-startup", "--python", os.path.abspath(script), "--"] + [str(a) for a in args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if log:
        with open(log, "a") as fh:
            fh.write(r.stdout[-20000:] + r.stderr[-5000:])
    if r.returncode != 0 or "Traceback" in r.stdout or "Traceback" in r.stderr:
        raise RuntimeError("blender job failed: %s\n%s\n%s" % (script, r.stdout[-3000:], r.stderr[-3000:]))
    return r.stdout[-3000:]


def rays(V, F, O=None, D=None, Q=None, overlap=False, maxd=0.4, min_hit=3e-4):
    tmp = tempfile.mkdtemp(prefix="bvh_")
    try:
        inp = os.path.join(tmp, "in.npz"); out = os.path.join(tmp, "out.npz")
        kw = dict(V=np.asarray(V, float), F=np.asarray(F, np.int64), maxd=maxd, min_hit=min_hit, overlap=overlap)
        if O is not None:
            kw.update(O=np.asarray(O, float), D=np.asarray(D, float))
        if Q is not None:
            kw["Q"] = np.asarray(Q, float)
        np.savez(inp, **kw)
        blender(os.path.join(HERE, "bl_bvh.py"), inp, out)
        return dict(np.load(out))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def inside(V, F, ids, V0, rest_sep=0.012, maxd_in=0.05, overlap=False):
    """build 13c: which skin vertices ids lie inside the body's volume (the closed skin V, F passed through itself):
    returns dict cross_out (odd = inside), depth_in (distance along the inward normal to the first face exited that
    was rest_sep from the vertex at rest; NaN none), depth_face, and pairs if overlap."""
    import mesh_geom as MG
    V = np.asarray(V, float); ids = np.asarray(ids, np.int64)
    N = MG.vertex_normals(V, np.asarray(F, np.int64))
    tmp = tempfile.mkdtemp(prefix="bvh_")
    try:
        inp = os.path.join(tmp, "in.npz"); out = os.path.join(tmp, "out.npz")
        np.savez(inp, V=V, F=np.asarray(F, np.int64), P=V[ids], PN=N[ids], P0=np.asarray(V0, float)[ids], V0=np.asarray(V0, float),
                 rest_sep=rest_sep, maxd_in=maxd_in, overlap=overlap)
        blender(os.path.join(HERE, "bl_bvh.py"), inp, out)
        return dict(np.load(out))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def drop_shared(F, pairs):
    """the overlap pairs whose two triangles share no vertex (real crossings, not neighbours touching)"""
    F = np.asarray(F); P = np.asarray(pairs).reshape(-1, 2)
    if not len(P):
        return P
    share = (F[P[:, 0]][:, :, None] == F[P[:, 1]][:, None, :]).any((1, 2))
    return P[~share]
