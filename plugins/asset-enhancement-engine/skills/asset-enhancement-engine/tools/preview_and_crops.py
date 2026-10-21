"""PREVIEW + CROPS for the person's review (A28, R-V): one quadric-decimated preview of a big skin (never vertex
clustering: it tore thin features and made specks on cat v3) plus full-detail crops of named regions.
usage: <venv-mesh python> preview_and_crops.py <skin.npz> <out_dir> [target_tris]
Writes preview.npz and crop_<name>.npz (v, f) and stats.json (bounds, counts, geometric flip counts).
"""
import json, os, sys, time
import numpy as np
import fast_simplification as fs

def flips(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    fn = np.cross(b - a, c - a)
    vn = np.zeros_like(v)
    for k in range(3): np.add.at(vn, f[:, k], fn)
    vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-30
    fnu = fn / (np.linalg.norm(fn, axis=1, keepdims=True) + 1e-30)
    m = (vn[f[:, 0]] + vn[f[:, 1]] + vn[f[:, 2]]) / 3.0
    return int(((fnu * m).sum(1) < -0.5).sum())

def crop(v, f, mask):
    keep = mask[f].all(1); ff = f[keep]
    used = np.unique(ff); remap = -np.ones(len(v), np.int64); remap[used] = np.arange(len(used))
    return v[used], remap[ff].astype(np.int32)

skin, out = sys.argv[1], sys.argv[2]; target = int(sys.argv[3]) if len(sys.argv) > 3 else 1_500_000
t0 = time.time(); Z = np.load(skin); v = Z["v"].astype(np.float64); f = Z["f"].astype(np.int64)
lo, hi = v.min(0), v.max(0); st = {"verts": len(v), "tris": len(f), "lo_m": lo.tolist(), "hi_m": hi.tolist()}
ymid = 0.5 * (lo[1] + hi[1])
regions = {   # the cat faces -y; z up; x lateral
    "muzzle": v[:, 1] < lo[1] + 0.030,
    "ears": v[:, 2] > hi[2] - 0.035,
    "paw_fore": (v[:, 2] < lo[2] + 0.035) & (v[:, 1] < ymid),
    "paw_hind": (v[:, 2] < lo[2] + 0.035) & (v[:, 1] > ymid),
    "tail_tip": v[:, 1] > hi[1] - 0.030,
}
for name, m in regions.items():
    cv, cf = crop(v, f, m)
    np.savez(os.path.join(out, f"crop_{name}.npz"), v=cv.astype(np.float32), f=cf)
    st[f"crop_{name}"] = {"verts": len(cv), "tris": len(cf)}
red = 1.0 - target / len(f)
pv, pf = fs.simplify(v.astype(np.float32), f.astype(np.int32), target_reduction=red, agg=7)
st["preview"] = {"verts": len(pv), "tris": len(pf), "flipped_faces": flips(pv.astype(np.float64), pf.astype(np.int64))}
np.savez(os.path.join(out, "preview.npz"), v=pv.astype(np.float32), f=pf.astype(np.int32))
st["seconds"] = round(time.time() - t0, 1)
json.dump(st, open(os.path.join(out, "stats.json"), "w"), indent=1); print(json.dumps(st, indent=1))
