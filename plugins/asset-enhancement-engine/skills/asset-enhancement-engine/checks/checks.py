"""Engine checks for a generated creature mesh (raw SDF skin PLY + landmarks JSON). Run on EVERY build.
Each check returns (pass, numbers). Each must fail on its planted defect (see --plant / --prove).

usage:
  python checks.py <mesh_prefix>                 # run all checks on a build
  python checks.py <mesh_prefix> --plant NAME    # run with one planted defect
  python checks.py <mesh_prefix> --prove         # every planted defect must be caught; reference must pass
"""
import json
import os
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lipline  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PRIORS = json.load(open(os.path.join(HERE, "proportion_priors.json")))
CORNEA_APEX = 1.03 * 1.10   # cornea shell = 1.03 r with a front dome bulge of ~0.10 r (materials.py)


# ------------------------------------------------------------------ io
def read_ply(path):
    with open(path, "rb") as f:
        hdr = b""
        while not hdr.endswith(b"end_header\n"):
            hdr += f.readline()
        h = hdr.decode()
        nv = int(h.split("element vertex ")[1].split()[0])
        nf = int(h.split("element face ")[1].split()[0])
        v = np.frombuffer(f.read(nv * 12), "<f4").reshape(-1, 3).astype(np.float64)
        fa = np.frombuffer(f.read(nf * 13), dtype=[("n", "u1"), ("i", "<i4", 3)])
    return v, fa["i"].astype(np.int64)


def load(prefix):
    v, f = read_ply(prefix + ".ply")
    J = json.load(open(prefix + "_landmarks.json"))
    # fine head mesh (two-resolution builds) for face-detail checks; falls back to the main mesh
    vh = read_ply(prefix + "_hr.ply")[0] if os.path.exists(prefix + "_hr.ply") else v
    return {"v": v, "f": f, "L": J["landmarks"], "P": J["params"], "v_head": vh}


# ------------------------------------------------------------------ helpers
def components(v, f):
    n = len(v)
    a = np.concatenate([f[:, 0], f[:, 1], f[:, 2]])
    b = np.concatenate([f[:, 1], f[:, 2], f[:, 0]])
    g = coo_matrix((np.ones(len(a)), (a, b)), shape=(n, n))
    k, lab = connected_components(g, directed=False)
    return k, np.bincount(lab)


def edge_manifold(f):
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    return int((cnt != 2).sum())


def laplacian_smooth(v, f, iters=12):
    n = len(v)
    a = np.concatenate([f[:, 0], f[:, 1], f[:, 2], f[:, 1], f[:, 2], f[:, 0]])
    b = np.concatenate([f[:, 1], f[:, 2], f[:, 0], f[:, 0], f[:, 1], f[:, 2]])
    A = coo_matrix((np.ones(len(a)), (a, b)), shape=(n, n)).tocsr()
    A.data[:] = 1
    deg = np.asarray(A.sum(1)).ravel()
    s = v.copy()
    for _ in range(iters):
        s = 0.5 * s + 0.5 * (A @ s) / deg[:, None]
    return s


def vertex_normals(v, f):
    fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    vn = np.zeros_like(v)
    for k in range(3):
        np.add.at(vn, f[:, k], fn)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)


# ------------------------------------------------------------------ checks
def check_topology(m):
    k, sizes = components(m["v"], m["f"])
    big_extra = int((np.sort(sizes)[:-1] >= 10).sum())
    nm = edge_manifold(m["f"])
    return big_extra == 0 and nm == 0, {"components": int(k), "extra_components_ge10v": big_extra, "nonmanifold_edges": nm}


def check_ground(m):
    v, L = m["v"], m["L"]
    out, ok = {}, True
    for k in ("fpaw.R", "fpaw.L", "hpaw.R", "hpaw.L"):
        p = np.array(L[k])
        near = np.linalg.norm(v[:, :2] - p[:2], axis=1) < 0.025
        zmin = float(v[near, 2].min()) if near.any() else 9.0
        out[k + "_zmin_mm"] = round(zmin * 1000, 2)
        ok &= -0.5 <= zmin * 1000 <= 1.5
    out["global_zmin_mm"] = round(float(v[:, 2].min() * 1000), 2)
    ok &= out["global_zmin_mm"] >= -0.5
    return bool(ok), out


def check_eyes(m):
    v, L = m["v"], m["L"]
    r = L["eye_r"]
    tree = cKDTree(v)
    out, ok = {}, True
    for s in "RL":
        c, g = np.array(L[f"eye.{s}"]), np.array(L[f"eye_dir.{s}"])
        g = g / np.linalg.norm(g)
        inside = len(tree.query_ball_point(c, r - 0.0003))
        rel = v - c
        along = rel @ g
        radial = np.linalg.norm(rel - np.outer(along, g), axis=1)
        ring = (radial > 0.6 * r) & (radial < 1.15 * r) & (along > 0) & (np.linalg.norm(rel, axis=1) < r + 0.006)
        lid_depth = float(np.percentile(along[ring], 90)) if ring.any() else np.nan
        protr = (CORNEA_APEX * r - lid_depth) * 1000   # visible surface = cornea dome (engine materials.py)
        out[f"{s}_skin_inside_eye"] = inside
        out[f"{s}_apex_protrusion_mm"] = round(protr, 2)
        ok &= inside == 0 and 0.8 <= protr <= 4.5
    return bool(ok), out


def measure(m):
    v, L, P = m["v"], m["L"], m["P"]
    T = np.array(L["tail"])
    body = v[(v[:, 1] < T[0][1] + 0.01) | (v[:, 2] > 0.12)]
    sh = np.array(L["shoulder.L"])
    slab = v[(v[:, 1] > sh[1] + 0.015) & (v[:, 1] < sh[1] + 0.045) & (np.abs(v[:, 0]) < 0.02)]
    H = float(slab[:, 2].max())          # withers: topline just BEHIND the neck (v1 slab caught the neck)
    torso = v[(v[:, 2] > 0.10) & (v[:, 2] < 0.20) & (np.abs(v[:, 0]) < 0.05)]
    tail_mask = np.linalg.norm(torso[:, None, :] - T[None, :, :], axis=2).min(1) < 0.015
    torso_nt = torso[~tail_mask]
    BL = float(torso_nt[:, 1].max() - torso_nt[:, 1].min())                 # chest front -> buttocks
    R = np.array(L["head_R"]); H0 = np.array(L["head"])
    hv = v[np.linalg.norm(v - H0, axis=1) < 0.075]
    hl = (hv - H0) @ R
    hl = hl[hl[:, 2] < 0.035]                                             # exclude ears
    HL = float(hl[:, 1].max() - hl[:, 1].min())
    HW = float(hl[:, 0].max() - hl[:, 0].min())
    ED = 2 * L["eye_r"]
    IOD = float(np.linalg.norm(np.array(L["eye.L"]) - np.array(L["eye.R"])))
    EH = float(((np.array(L["ear_tip.L"]) - H0) @ R)[2])
    mid = v[(v[:, 1] > sh[1] - 0.02) & (v[:, 1] < sh[1] + 0.03) & (np.abs(v[:, 0]) < 0.004) & (v[:, 2] > 0.05) & (v[:, 2] < 0.17)]
    chest_bottom = float(mid[:, 2].min())   # sternum on the midline (v1 |x|<12mm hit the inner foreleg skin)
    FL = chest_bottom                                                     # elbow/chest floor height = foreleg clearance
    TL = float(np.linalg.norm(np.diff(T, axis=0), axis=1).sum())
    return {"withers_H": H, "body_len/H": BL / H, "chest_depth/H": (H - chest_bottom) / H, "head_len/H": HL / H,
            "head_w/H": HW / H, "eye_d/head_w": ED / HW, "iod/head_w": IOD / HW, "ear_h/head_w": EH / HW,
            "leg_clear/H": FL / H, "tail_len/H": TL / H}


def check_proportions(m):
    meas = measure(m)
    out, ok = {}, True
    for k, (lo, hi) in PRIORS["bands"].items():
        val = meas[k]
        good = lo <= val <= hi
        out[k] = f"{val:.3f} {'ok' if good else 'OUT'} [{lo}, {hi}]"
        ok &= good
    return bool(ok), out


def _calib_c(e):
    """umbrella-smoothing displacement x radius for a marching-cubes sphere at this edge length"""
    from skimage.measure import marching_cubes
    R0, vox = 0.02, e * 1.15
    g = np.arange(-R0 - 4 * vox, R0 + 4 * vox, vox)
    X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
    sv, sf, _, _ = marching_cubes(np.sqrt(X ** 2 + Y ** 2 + Z ** 2) - R0, 0.0, spacing=(vox,) * 3)
    sv += g[0]
    d = ((sv - laplacian_smooth(sv, sf, SMOOTH_IT)) * vertex_normals(sv, sf)).sum(1)
    return float(np.median(d) * R0)


SMOOTH_IT = 30


def check_coherence(m):
    """(a) bilateral symmetry of the trunk ABOVE elbows/knees (legs may be posed asymmetrically on purpose);
    (b) lumps: convex regions whose curvature radius (calibrated umbrella-smoothing displacement) is under
    14 mm on the trunk - a cat's trunk has no such tight convexities; v5-v9's knee ball (r~20 mm sphere end)
    and sphere-cap blobs do."""
    v, f, L = m["v"], m["f"], m["L"]
    T = np.array(L["tail"])
    excl = np.zeros(len(v), bool)
    excl |= np.linalg.norm(v - np.array(L["head"]), axis=1) < 0.08
    excl |= np.linalg.norm(v[:, None, :] - T[None, :, :], axis=2).min(1) < 0.02
    trunk = (~excl) & (v[:, 2] > 0.13) & (v[:, 1] > -0.12) & (v[:, 1] < 0.12) & (np.abs(v[:, 0]) < 0.06)
    mir = v[trunk] * np.array([-1, 1, 1])
    d, _ = cKDTree(v).query(mir)
    sym = float(np.percentile(d, 95) * 1000)
    e = float(np.median(np.linalg.norm(v[f[:, 0]] - v[f[:, 1]], axis=1)))
    c = _calib_c(e)
    disp = ((v - laplacian_smooth(v, f, SMOOTH_IT)) * vertex_normals(v, f)).sum(1)
    Rest = np.where(disp > 1e-7, c / np.maximum(disp, 1e-12), np.inf)
    zone = (~excl) & (v[:, 2] > 0.09) & (np.abs(v[:, 0]) < 0.07)
    cand = zone & (Rest < 0.014)
    lumps = 0
    if cand.sum() > 0:
        pts = v[cand]
        tr = cKDTree(pts)
        k, lab = connected_components(tr.sparse_distance_matrix(tr, 0.003).tocsr() > 0, directed=False)
        lumps = int((np.bincount(lab) >= 40).sum())
    ok = sym <= 2.5 and lumps == 0
    return bool(ok), {"trunk_symmetry_p95_mm": round(sym, 2), "lumps": lumps,
                      "min_trunk_curv_radius_mm": round(float(Rest[zone].min() * 1000), 1)}


def check_lipline(m):
    """closed-mouth lip margins are smooth curves (no cusp / notch / sawtooth) - see lipline.py"""
    if "mouth" not in m["L"]:
        return True, {"skipped": "no engineered mouth"}
    return lipline.check_lipline(m["v_head"], m["L"], m["P"])


CHECKS = {"topology": check_topology, "ground": check_ground, "eyes": check_eyes,
          "proportions": check_proportions, "coherence": check_coherence, "lipline": check_lipline}


# ------------------------------------------------------------------ planted defects (each targets one check)
def sphere_mesh(c, r, n=24):
    th, ph = np.meshgrid(np.linspace(0, np.pi, n), np.linspace(0, 2 * np.pi, n, endpoint=False), indexing="ij")
    p = np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)], -1).reshape(-1, 3) * r + c
    f = []
    for i in range(n - 1):
        for j in range(n):
            a, b, c2, d = i * n + j, i * n + (j + 1) % n, (i + 1) * n + j, (i + 1) * n + (j + 1) % n
            f += [(a, c2, b), (b, c2, d)]
    return p, np.array(f)


def plant(m, name):
    m = {k: (v.copy() if isinstance(v, np.ndarray) else json.loads(json.dumps(v))) for k, v in m.items()}
    v, L = m["v"], m["L"]
    if name == "bubble":            # internal void left by a sub-voxel groove (seen v9-v11)
        p, f = sphere_mesh(np.array(L["head"]) + np.array([0, -0.01, -0.01]), 0.002, 8)
        m["f"] = np.concatenate([m["f"], f + len(v)]); m["v"] = np.concatenate([v, p])
    elif name == "paw_lift":        # floating paw
        near = np.linalg.norm(v[:, :2] - np.array(L["fpaw.L"])[:2], axis=1) < 0.03
        v[near, 2] += 0.005
    elif name == "eye_bug":         # eye 5 mm too far forward (v5-v6 "bug eyes")
        L["eye.L"] = (np.array(L["eye.L"]) + 0.005 * np.array(L["eye_dir.L"])).tolist()
    elif name == "eye_buried":
        L["eye.R"] = (np.array(L["eye.R"]) - 0.004 * np.array(L["eye_dir.R"])).tolist()
    elif name == "torso_stretch":   # greyhound torso (v5 side view)
        sel = (v[:, 1] > 0.0)
        v[sel, 1] = v[sel, 1] * 1.6
        for k in ("hip.L", "hip.R", "hpaw.L", "hpaw.R", "knee.L", "knee.R", "hock.L", "hock.R"):
            L[k][1] *= 1.6
        L["tail"] = [[p[0], p[1] * 1.6, p[2]] for p in L["tail"]]
    elif name == "lip_cusp":        # v19-v26 midline cusp on the lower lip margin (|x| in the lip-line droop)
        m["v_head"] = lipline.plant_cusp(m["v_head"], L, m["P"])
    elif name == "lump":            # knee-ball style sphere cap on the flank (v5-v9): r 10 mm, 8 mm proud
        n = vertex_normals(v, m["f"])
        flank = (np.abs(v[:, 1] - 0.03) < 0.004) & (v[:, 2] > 0.14) & (v[:, 2] < 0.16) & (v[:, 0] > 0)
        p0 = v[flank][np.argmax(v[flank][:, 0])]; n0 = n[flank][np.argmax(v[flank][:, 0])]
        cc = p0 + n0 * (0.008 - 0.010)
        rel = v - cc
        along = rel @ n0
        rad = np.linalg.norm(rel - np.outer(along, n0), axis=1)
        cap = np.sqrt(np.clip(0.010 ** 2 - rad ** 2, 0, None))
        lift = np.clip(cap - along, 0, None) * (rad < 0.010) * (np.abs(along) < 0.012)
        v += n * lift[:, None]
    else:
        raise SystemExit("unknown defect " + name)
    return m


TARGET = {"bubble": "topology", "paw_lift": "ground", "eye_bug": "eyes", "eye_buried": "eyes",
          "torso_stretch": "proportions", "lump": "coherence", "lip_cusp": "lipline"}


def run_all(m, label):
    allok = True
    print(f"== {label}")
    for name, fn in CHECKS.items():
        ok, out = fn(m)
        allok &= ok
        print(f"  {'PASS' if ok else 'FAIL'} {name:12s} {out}")
    return allok


if __name__ == "__main__":
    m = load(sys.argv[1])
    if "--plant" in sys.argv:
        run_all(plant(m, sys.argv[sys.argv.index("--plant") + 1]), "planted " + sys.argv[sys.argv.index("--plant") + 1])
    elif "--prove" in sys.argv:
        ref_ok = run_all(m, "reference (must pass)")
        caught = {}
        ref_pass = {k: fn(m)[0] for k, fn in CHECKS.items()}
        for d, chk in TARGET.items():
            ok, out = CHECKS[chk](plant(m, d))
            caught[d] = (not ok) and ref_pass[chk]   # failing a check that already fails proves nothing
            print(f"  planted {d:14s} -> {chk:12s} {'CAUGHT' if not ok else 'MISSED'} {out}")
        print("PROOF:", "OK" if ref_ok and all(caught.values()) else "FAILED", "| reference", "pass" if ref_ok else "FAIL",
              "| caught", sum(caught.values()), "/", len(caught))
    else:
        sys.exit(0 if run_all(m, sys.argv[1]) else 1)
