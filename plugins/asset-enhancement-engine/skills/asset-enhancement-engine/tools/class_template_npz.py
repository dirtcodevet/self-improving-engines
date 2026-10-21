"""class_template_npz.py - convert the fetched MakeHuman CLASS template to numpy and measure it.

numpy + stdlib only; it never runs MakeHuman code. Inputs are the verbatim files that
class_template_fetch.py put in <template>/ (git-blob verified, see manifest.json).

Outputs (written to --out, NOT into the verbatim template folder):
  mh_base.npz     v (V,3) f32 MH units; f (F,4) i32 quads; vt (T,2) f32; f_uv (F,4) i32;
                  face_group (F,) i16; group_names; group_vptr/group_vidx (CSR vertex groups);
                  body_f (Fb,4) i32 = faces of group 'body'; body_vidx = vertices it uses;
                  joint_names / joint_pos (J,3) = centroids of the joint-* helper cubes (landmarks)
  mh_targets_body.npz  t_names; t_ptr (N+1,) i64; t_idx i32; t_delta f32 (MH units)  (CSR)
  mh_template_report.json  every measured number this tool reports (topology, scale, pose,
                  targets, modifiers, licence headers)

Usage: python -I class_template_npz.py --template <template dir> --out <dir>
"""
import argparse, json, os, re, sys, time
import numpy as np


# ---------------------------------------------------------------- OBJ
def parse_obj(path):
    vs, vts, fv, ft, fg = [], [], [], [], []
    names, gid, cur = [], {}, -1
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("v "):
                vs.append(line.split()[1:4])
            elif line.startswith("vt "):
                vts.append(line.split()[1:3])
            elif line.startswith("g "):
                n = line[2:].strip()
                if n not in gid:
                    gid[n] = len(names)
                    names.append(n)
                cur = gid[n]
            elif line.startswith("f "):
                parts = line.split()[1:]
                if len(parts) != 4:
                    raise ValueError("non-quad face: " + line)
                fv.append([int(p.split("/")[0]) - 1 for p in parts])
                ft.append([int(p.split("/")[1]) - 1 if p.count("/") and p.split("/")[1] else -1 for p in parts])
                fg.append(cur)
    return (np.array(vs, np.float64), np.array(vts, np.float32), np.array(fv, np.int32),
            np.array(ft, np.int32), np.array(fg, np.int16), names)


# ---------------------------------------------------------------- topology
def quad_edges(f):
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 3]], f[:, [3, 0]]])
    e.sort(axis=1)
    u, cnt = np.unique(e, axis=0, return_counts=True)
    return u, cnt


def components(f, nv):
    parent = np.arange(nv)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for q in f:
        r0 = find(q[0])
        for k in q[1:]:
            rk = find(k)
            if rk != r0:
                parent[rk] = r0
    used = np.unique(f)
    roots = np.array([find(i) for i in used])
    return used, roots


def boundary_loops(bedges):
    adj = {}
    for a, b in bedges:
        adj.setdefault(int(a), []).append(int(b))
        adj.setdefault(int(b), []).append(int(a))
    seen, loops = set(), []
    for s in adj:
        if s in seen:
            continue
        loop, prev, cur = [s], None, s
        seen.add(s)
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            loop.append(cur)
        loops.append(loop)
    return loops, max(len(v) for v in adj.values()) if adj else 0


# ---------------------------------------------------------------- targets
def parse_target(path):
    idx, d, header = [], [], []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                header.append(s)
                continue
            p = s.split()
            idx.append(int(p[0]))
            d.append((float(p[1]), float(p[2]), float(p[3])))
    return np.array(idx, np.int32), np.array(d, np.float32).reshape(-1, 3), "\n".join(header)


def peak_mb():
    """Peak working set of this process (Windows), else None. Memory budget evidence (A24)."""
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        c = PMC(); c.cb = ctypes.sizeof(PMC)
        k32 = ctypes.WinDLL("kernel32")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        if not k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb):
            return None
        return round(c.PeakWorkingSetSize / 2**20, 1)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0 = time.time()
    T = a.template
    rep = {"tool": "class_template_npz.py", "template": T}
    man = json.load(open(os.path.join(T, "manifest.json")))
    rep["source"] = {k: man[k] for k in ("repo", "tag", "commit", "n_files", "bytes")}

    # --- base mesh
    v, vt, f, fuv, fg, names = parse_obj(os.path.join(T, "3dobjs", "base.obj"))
    V = len(v)
    gv = []
    for g in range(len(names)):
        gv.append(np.unique(f[fg == g]))
    vptr = np.zeros(len(names) + 1, np.int64)
    vptr[1:] = np.cumsum([len(x) for x in gv])
    vidx = np.concatenate(gv).astype(np.int32)
    body_g = names.index("body")
    body_f = f[fg == body_g]
    body_v = np.unique(body_f)
    helper_v = np.unique(f[fg != body_g])
    joints = [(n, gv[i]) for i, n in enumerate(names) if n.startswith("joint-")]
    joint_names = np.array([n for n, _ in joints])
    joint_pos = np.array([v[ix].mean(0) for _, ix in joints])
    J = dict(zip(joint_names.tolist(), joint_pos))

    # --- body topology
    e, cnt = quad_edges(body_f)
    used, roots = components(body_f, V)
    comp_ids, comp_sizes = np.unique(roots, return_counts=True)
    bed = e[cnt == 1]
    loops, max_bdeg = boundary_loops(bed) if len(bed) else ([], 0)
    Vb, Eb, Fb = len(body_v), len(e), len(body_f)
    chi = Vb - Eb + Fb
    chi_capped = chi + len(loops)          # one cap face per boundary loop
    loop_info = []
    for L in sorted(loops, key=len, reverse=True):
        c = v[L].mean(0)
        near = joint_names[np.argmin(np.linalg.norm(joint_pos - c, axis=1))]
        loop_info.append({"n_verts": len(L), "centroid": np.round(c, 3).tolist(),
                          "nearest_joint": str(near),
                          "span": np.round(v[L].max(0) - v[L].min(0), 3).tolist()})
    lo, hi = v[body_v].min(0), v[body_v].max(0)
    rep["base_mesh"] = {
        "file": "3dobjs/base.obj", "n_vertices_total": int(V), "n_faces_total": int(len(f)),
        "n_uv": int(len(vt)), "all_quads": True, "n_groups": len(names),
        "groups_helpers": sorted(n for n in names if n.startswith("helper-")),
        "n_joint_landmarks": int(len(joint_names)),
        "body": {"n_vertices": int(Vb), "n_faces_quads": int(Fb), "n_edges": int(Eb),
                 "n_connected_components": int(len(comp_ids)),
                 "boundary_edges": int((cnt == 1).sum()), "nonmanifold_edges": int((cnt > 2).sum()),
                 "max_boundary_vertex_degree": int(max_bdeg),
                 "boundary_loops": loop_info, "euler_chi": int(chi),
                 "euler_chi_if_each_loop_capped": int(chi_capped),
                 "genus_if_capped": (2 - chi_capped) / 2 if len(comp_ids) == 1 else None,
                 "closed": bool((cnt == 1).sum() == 0 and (cnt > 2).sum() == 0),
                 "shares_vertices_with_helpers": int(len(np.intersect1d(body_v, helper_v))),
                 "unreferenced_vertices_in_file": int(V - len(np.unique(f)))},
        "bbox_body_min": np.round(lo, 4).tolist(), "bbox_body_max": np.round(hi, 4).tolist(),
        "extent_body": np.round(hi - lo, 4).tolist(),
    }

    # --- axes and pose from the joint landmarks (not assumed)
    up = int(np.argmax(hi - lo))
    toe = np.mean([J[n] for n in J if n.startswith("joint-l-toe-") and n.endswith("-1")], 0)
    fwd_vec = toe - J["joint-l-ankle"]
    fwd = int(np.argmax(np.abs(fwd_vec * (np.arange(3) != up))))
    side = J["joint-l-shoulder"] - J["joint-r-shoulder"]
    pose = {"up_axis": "xyz"[up], "up_sign": "+" if J["joint-head"][up] > J["joint-pelvis"][up] else "-",
            "forward_axis": "xyz"[fwd], "forward_sign": "+" if fwd_vec[fwd] > 0 else "-",
            "character_left_axis_sign": ("+" if side[0] > 0 else "-") + "x"}
    for s in ("l", "r"):
        sh, el, wr = J["joint-%s-shoulder" % s], J["joint-%s-elbow" % s], J["joint-%s-hand" % s]
        d, d2 = el - sh, wr - el
        # frontal plane = (lateral x, up); forward pitch = angle of the segment toward +forward
        pose["%s_upperarm_frontal_deg_below_horizontal" % s] = round(float(np.degrees(np.arctan2(-d[up], abs(d[0])))), 2)
        pose["%s_upperarm_forward_pitch_deg" % s] = round(float(np.degrees(np.arcsin(d[fwd] / np.linalg.norm(d)))), 2)
        pose["%s_forearm_frontal_deg_below_horizontal" % s] = round(float(np.degrees(np.arctan2(-d2[up], abs(d2[0])))), 2)
        pose["%s_forearm_forward_pitch_deg" % s] = round(float(np.degrees(np.arcsin(d2[fwd] / np.linalg.norm(d2)))), 2)
        pose["%s_elbow_bend_deg" % s] = round(float(np.degrees(np.arccos(np.dot(d, d2) / np.linalg.norm(d) / np.linalg.norm(d2)))), 2)
    # mirror check: reflect x and look for the nearest body vertex (O(V^2) avoided: hash on rounded coords)
    key = {tuple(np.round(p, 4)): i for i, p in enumerate(v[body_v])}
    mir = v[body_v] * np.array([-1, 1, 1])
    hits = sum(tuple(np.round(p, 4)) in key for p in mir)
    pose["mirror_exact_pairs_at_1e-4"] = f"{hits}/{len(body_v)}"
    pose["mirror_exact_pairs_note"] = "count of body vertices whose x-mirror is a body vertex to 1e-4 units"
    rep["axes_and_pose"] = pose

    # --- targets
    tdir = os.path.join(T, "targets")
    tnames, tidx, tdel, tstats, cc0 = [], [], [], [], {"cc0": 0, "no_cc0": []}
    for root, _, files in os.walk(tdir):
        for fn in sorted(files):
            if not fn.endswith(".target"):
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, tdir).replace(os.sep, "/")[:-7]
            ix, d, hdr = parse_target(p)
            if "CC0" in hdr:
                cc0["cc0"] += 1
            else:
                cc0["no_cc0"].append(rel)
            if len(ix) and (ix.max() >= V or ix.min() < 0):
                raise ValueError("index out of range in " + rel)
            tnames.append(rel); tidx.append(ix); tdel.append(d)
            mag = np.linalg.norm(d, axis=1) if len(d) else np.zeros(1)
            tstats.append({"name": rel, "nnz": int(len(ix)),
                           "nnz_body": int(np.isin(ix, body_v).sum()),
                           "max_disp_units": round(float(mag.max()), 4)})
    order = np.argsort(tnames)
    tnames = [tnames[i] for i in order]; tidx = [tidx[i] for i in order]
    tdel = [tdel[i] for i in order]; tstats = [tstats[i] for i in order]
    tptr = np.zeros(len(tnames) + 1, np.int64)
    tptr[1:] = np.cumsum([len(x) for x in tidx])

    # --- modifiers: which named parameters are fully backed by the targets we fetched
    have = set(tnames)
    mods = []
    for fn in ("modeling_modifiers.json", "measurement_modifiers.json", "bodyshapes_modifiers.json"):
        for grp in json.load(open(os.path.join(T, "modifiers", fn))):
            for m in grp["modifiers"]:
                if "macrovar" in m:
                    mods.append({"group": grp["group"], "name": m["macrovar"], "kind": "macro"})
                    continue
                folder = grp["group"]
                if "min" in m:
                    need = ["%s/%s-%s" % (folder, m["target"], m[k]) for k in ("min", "max")]
                    nm = "%s-%s|%s" % (m["target"], m["min"], m["max"])
                else:
                    need = ["%s/%s" % (folder, m["target"])]
                    nm = m["target"]
                mods.append({"group": folder, "name": nm, "kind": "bipolar" if "min" in m else "unipolar",
                             "backed": all(n in have for n in need)})
    macro_files = {k: sum(1 for n in tnames if n.startswith(k)) for k in
                   ("macrodetails/universal-", "macrodetails/height/", "macrodetails/proportions/")}
    macro_files["macrodetails/<ethnic>-"] = sum(1 for n in tnames if re.match(r"macrodetails/(african|asian|caucasian)-", n))
    macro_files["breast/<macro cup+firmness>"] = sum(1 for n in tnames if re.match(r"breast/(fe)?male-", n))
    rep["targets"] = {"n_targets": len(tnames), "n_deltas_total": int(tptr[-1]),
                      "licence_headers": {"cc0": cc0["cc0"], "without_cc0_word": cc0["no_cc0"]},
                      "macro_files": macro_files,
                      "empty_targets": [s["name"] for s in tstats if s["nnz"] == 0],
                      "helper_only_targets": [s["name"] for s in tstats if s["nnz"] > 0 and s["nnz_body"] == 0],
                      "per_target": tstats}
    backed = [m for m in mods if m.get("backed", True)]
    rep["modifiers"] = {"n_defined_in_json": len(mods),
                        "n_backed_by_fetched_targets": len(backed),
                        "backed_by_group": {}, "groups_with_unfetched_modifiers": sorted({m["group"] for m in mods if m.get("backed") is False})}
    for m in backed:
        rep["modifiers"]["backed_by_group"].setdefault(m["group"], []).append(m["name"])

    # --- scale: base and an estimated young adult female (MH macro rule as read from the
    #     target names; the exact combination rule is MakeHuman's code and is NOT run here)
    def apply(ws):
        x = v.copy()
        for n, w in ws.items():
            k = tnames.index(n)
            x[tidx[k]] += w * tdel[k]
        return x
    fem = {"macrodetails/universal-female-young-averagemuscle-averageweight": 1.0}
    for eth in ("african", "asian", "caucasian"):
        fem["macrodetails/%s-female-young" % eth] = 1.0 / 3
    xf = apply(fem)
    male = {"macrodetails/universal-male-young-averagemuscle-averageweight": 1.0}
    for eth in ("african", "asian", "caucasian"):
        male["macrodetails/%s-male-young" % eth] = 1.0 / 3
    xm = apply(male)
    def h(x):
        return float(x[body_v][:, up].max() - x[body_v][:, up].min())
    rep["scale"] = {"units": "MakeHuman decimetre convention (1 unit = 0.1 m); checked for plausibility below",
                    "base_height_units": round(h(v), 4),
                    "est_young_female_avg_height_units": round(h(xf), 4),
                    "est_young_male_avg_height_units": round(h(xm), 4),
                    "est_weights_used_female": fem,
                    "note": "female/male weights are this tool's reading of MH's macro scheme (gender 0/1, age 25 y, "
                            "muscle 0.5, weight 0.5, ethnic 1/3 each); estimated, not run through MakeHuman"}

    os.makedirs(a.out, exist_ok=True)
    np.savez_compressed(os.path.join(a.out, "mh_base.npz"),
                        v=v.astype(np.float32), f=f, vt=vt, f_uv=fuv, face_group=fg,
                        group_names=np.array(names), group_vptr=vptr, group_vidx=vidx,
                        body_f=body_f, body_vidx=body_v.astype(np.int32),
                        joint_names=joint_names, joint_pos=joint_pos.astype(np.float32),
                        units=np.array("MakeHuman units (dm)"), source=np.array(json.dumps(rep["source"])))
    np.savez_compressed(os.path.join(a.out, "mh_targets_body.npz"),
                        t_names=np.array(tnames), t_ptr=tptr,
                        t_idx=np.concatenate(tidx).astype(np.int32),
                        t_delta=np.concatenate(tdel).astype(np.float32),
                        source=np.array(json.dumps(rep["source"])))
    # round-trip proof: reload and compare against the parsed arrays
    B = np.load(os.path.join(a.out, "mh_base.npz"))
    Tz = np.load(os.path.join(a.out, "mh_targets_body.npz"))
    k = tnames.index("macrodetails/universal-female-young-averagemuscle-averageweight")
    rt = {"v_max_abs_err": float(np.abs(B["v"] - v).max()), "f_equal": bool((B["f"] == f).all()),
          "target_roundtrip_equal": bool(np.array_equal(Tz["t_idx"][Tz["t_ptr"][k]:Tz["t_ptr"][k + 1]], tidx[k]) and
                                         np.array_equal(Tz["t_delta"][Tz["t_ptr"][k]:Tz["t_ptr"][k + 1]], tdel[k]))}
    rep["roundtrip"] = rt
    rep["outputs"] = {n: os.path.getsize(os.path.join(a.out, n)) for n in ("mh_base.npz", "mh_targets_body.npz")}
    rep["seconds"] = round(time.time() - t0, 1)
    rep["peak_working_set_MB"] = peak_mb()
    with open(os.path.join(a.out, "mh_template_report.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    s = dict(rep); s["targets"] = {k2: v2 for k2, v2 in rep["targets"].items() if k2 != "per_target"}
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
