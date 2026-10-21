"""ONE-LINE MESH CHECKS for meshes that already exist (crops in %TEMP%/p2_skin_v3b, or any npz with v / f): one summary line
per mesh - verts / tris, shells, open edges (boundary loops), non-manifold edges, genus of the main shell and WHERE (the
ear-frame zones of cases/cat1/v3_finish/genus_locate.py), the up-facing shelf area (ear_shelf_probe.py's rule) and the loose
pieces (ear_shell_pieces.py's split). Same rules as those scripts, gathered so one call answers them all.

usage:
  python mesh_check.py <crop name | npz path> [...] [--side L|R|none]        -> one line per mesh
  python mesh_check.py line <crop name | npz path> x0 y0 z0 x1 y1 z1 [--frame world|head|earL|earR]
        -> where the mesh crosses the line (mm along it), the same answer field_probe.py line gives for the field
side: auto from the name (earP / earL -> L, earN / earR -> R), else none (genus without ear zones, no shelf).
Coordinates: world mm (a mesh stored in metres is scaled). A full-body mesh (> 5 M tris) takes minutes and ~3 GB: run it
under engine/tools/heavy_lock.py.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
FEAT = os.path.join(ROOT, "engine", "packs", "felid", "features")
FIN = os.path.join(ROOT, "cases", "cat1", "v3_finish")
for _p in (FEAT, FIN):
    sys.path.insert(0, _p)
import numpy as np  # noqa: E402
from scipy.sparse import coo_matrix  # noqa: E402
from scipy.sparse.csgraph import connected_components  # noqa: E402

SCR = os.environ.get("V3B_SCRATCH") or os.path.join(os.environ.get("TEMP", "/tmp"), "p2_skin_v3b")
RAD, H_MIN = 30.0, -0.45                                  # genus_locate.py's ear zone
BANDS = [-0.2, 0.0, 0.1, 0.2, 0.35, 0.6]                  # genus_locate.py's h/H bands


def load(name):
    p = name if os.path.exists(name) else os.path.join(SCR, f"crop_{name}.npz")
    Z = np.load(p, mmap_mode="r"); v = np.asarray(Z["v"], float); f = np.asarray(Z["f"], np.int64)
    if np.abs(v).max() < 5.0:                              # metres
        v = v * 1000
    return v, f, os.path.basename(p)


def side_of(name, side):
    if side in ("L", "R"):
        return side
    if side == "none":
        return None
    n = os.path.basename(name)
    return "L" if ("earP" in n or "earL" in n or "ear_L" in n) else ("R" if ("earN" in n or "earR" in n or "ear_R" in n) else None)


def comps(f, n):
    e = np.r_[f[:, [0, 1]], f[:, [1, 2]]]
    return connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)), directed=False)


def edge_counts(f):
    e = np.sort(np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]], axis=1)
    key = e[:, 0] * (int(e.max()) + 1) + e[:, 1]
    _, c = np.unique(key, return_counts=True)
    return c


def genus(fc):
    from mesh_boundary_loops import boundary_loops
    V = len(np.unique(fc)); c = edge_counts(fc); b = len(boundary_loops(fc)) if (c == 1).any() else 0
    return (2 - (V - len(c) + len(fc)) - b) // 2, b


def ear_frame_world(sd):
    import feat_ears_v3b as FE
    fr = FE.shell()[sd]["fr"]
    return FE, fr


def check(name, side="auto"):
    t0 = time.time(); v, f, nm = load(name); sd = side_of(name, side)
    k, lab = comps(f, len(v)); fl = lab[f[:, 0]]; cnt = np.bincount(fl, minlength=k); main = cnt.argmax()
    c = edge_counts(f); open_e = int((c == 1).sum()); nonman = int((c > 2).sum())
    fm = f[fl == main]; gm, bm = genus(fm)
    out = [f"{nm}: {len(v)} v {len(f)} t | shells {int((cnt > 0).sum())} (main {100 * cnt[main] / len(f):.1f} % of tris; "
           f"others {int(cnt.sum() - cnt[main])} tris)", f"open edges {open_e} (main shell {bm} loops)", f"non-manifold {nonman}",
           f"genus main {gm}"]
    if sd is not None:
        FE, fr = ear_frame_world(sd)
        C = FE.PT.head_local(v[fm].mean(1) / 1000) * 1000 - fr["O"]; h = C @ fr["A"]; hh = h / fr["H"]
        rad = np.linalg.norm(C - np.outer(h, fr["A"]), axis=1); zone = np.where((rad < RAD) & (hh > H_MIN), np.digitize(hh, BANDS), -1)
        where = []
        for z in np.unique(zone):
            fz = fm[zone == z]; lz = comps(fz, len(v))[1][fz[:, 0]]
            for cc in np.unique(lz):
                fc = fz[lz == cc]
                if len(fc) < 50:
                    continue
                g, _ = genus(fc)
                if g:
                    lbl = "head" if z < 0 else (f"ear h/H<{BANDS[0]}" if z == 0 else
                                                f"ear h/H {BANDS[z - 1]}..{BANDS[z] if z < len(BANDS) else 'tip'}")
                    where.append(f"{lbl} g{g} @ {np.round(v[np.unique(fc)].mean(0), 1).tolist()}")
        out.append("where: " + ("; ".join(where) if where else "-"))
        # ear_shelf_probe.py: area of faces facing up the ear axis (ears_base_<sd> frame, world), rad < 14, h/H -0.2..0.6
        E = np.load(os.path.join(ROOT, "tripo_rebuild", "layers", f"ears_base_{sd}.npz")); O = E["origin"] * 1000
        A = E["axis"] / np.linalg.norm(E["axis"]); H = (E["tip"] * 1000 - O) @ A
        fn = np.cross(v[fm[:, 1]] - v[fm[:, 0]], v[fm[:, 2]] - v[fm[:, 0]]); ar = np.linalg.norm(fn, axis=1) * 0.5
        fn /= np.maximum(ar[:, None] * 2, 1e-12); cq = v[fm].mean(1) - O; hq = cq @ A; rq = np.linalg.norm(cq - np.outer(hq, A), axis=1)
        up = (fn @ A > 0.85) & (rq < 14) & (hq > -0.2 * H) & (hq < 0.6 * H)
        hist, ed = np.histogram(hq[up] / H, bins=np.arange(-0.2, 0.62, 0.02), weights=ar[up]); pk = hist.argmax()
        out.append(f"shelf {ar[up].sum():.0f} mm2 up-facing (peak {hist[pk]:.0f} mm2 at h/H {ed[pk]:.2f})")
        # ear_shell_pieces.py: the loose pieces
        if k > 1:
            small = np.flatnonzero((cnt > 0) & (np.arange(k) != main)); vl = lab[f[:, 0]]
            ext = [float(np.ptp(v[np.unique(f[vl == s_])], axis=0).max()) for s_ in small[:400]]
            out.append(f"loose pieces {len(small)}, extent max {max(ext):.2f} mm")
    return " | ".join(out) + f" | {time.time() - t0:.1f} s"


def line_hits(v, f, A, B):
    """crossings of segment A-B with the mesh (Moller-Trumbore on the triangles near the segment): sorted mm along it"""
    d = B - A; L = np.linalg.norm(d); u = d / L
    T = v[f]; cen = T.mean(1); r = np.linalg.norm(T - cen[:, None], axis=2).max(1)
    q = cen - A; t = np.clip(q @ u, 0, L); near = np.linalg.norm(q - np.outer(t, u), axis=1) <= r + 1e-6
    T = T[near]; e1 = T[:, 1] - T[:, 0]; e2 = T[:, 2] - T[:, 0]; p = np.cross(u, e2); det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-12; inv = np.where(ok, 1 / np.where(ok, det, 1), 0); s = A - T[:, 0]
    bu = np.einsum("ij,ij->i", s, p) * inv; qv = np.cross(s, e1); bv = (qv @ u) * inv; tt = np.einsum("ij,ij->i", e2, qv) * inv
    hit = ok & (bu >= 0) & (bv >= 0) & (bu + bv <= 1) & (tt >= 0) & (tt <= L)
    return np.sort(tt[hit])


MIN_FREE_GB = 3.0      # this tool's peak (~0.9 GB) + the 2 GB floor of the 16 GB machine: wait, never squeeze a build


def wait_for_memory(log=print):
    """the probes do not take engine/tools/heavy_lock.py's lock (seconds, < 1 GB), but they wait while free memory is short"""
    import heavy_lock as HL
    said = False
    while HL.free_gb() < MIN_FREE_GB:
        if not said:
            log(f"waiting: {HL.free_gb():.1f} GB free < {MIN_FREE_GB} (a heavy run is on)", flush=True); said = True
        time.sleep(10)


def main(argv):
    wait_for_memory()
    side = "auto"
    if "--side" in argv:
        i = argv.index("--side"); side = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    if argv and argv[0] == "line":
        frame = "world"
        if "--frame" in argv:
            i = argv.index("--frame"); frame = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
        t0 = time.time(); v, f, nm = load(argv[1]); P = np.array([float(x) for x in argv[2:8]]).reshape(2, 3)
        if frame != "world":
            import feat_ears_v3b as FE
            PT = FE.PT
            if frame.startswith("ear"):
                fr = FE.ear_frame(frame[-1]); P = fr["O"] + P[:, :1] * fr["u"] + P[:, 1:2] * fr["v"] + P[:, 2:3] * fr["A"]
            P = (PT.HC + (P / 1000) @ PT.HR.T) * 1000
        x = line_hits(v, f, P[0], P[1])
        print(f"{nm} line {frame} {argv[2:5]}->{argv[5:8]} ({np.linalg.norm(P[1] - P[0]):.2f} mm): mesh crossings at "
              f"{np.round(x, 2).tolist()} mm | {time.time() - t0:.1f} s", flush=True)
        return
    for nm in argv:
        print(check(nm, side), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
