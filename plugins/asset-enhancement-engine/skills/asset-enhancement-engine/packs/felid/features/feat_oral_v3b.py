"""ORAL PARTS v3b (felid pack, case cat1, cat v3 round 2, ruling R-M) - builder 'feat-mouth-v3b', 2026-10-18.
The contents of the closed-jaw oral cavity that feat_mouth_v3b carves into the skin, each a SEPARATE mesh so the rig can
open the jaw: the upper-jaw parts move with the skull, the lower-jaw parts with the mandible (hinge = the two TMJs).

  upper jaw (rig parent 'skull'):    oral_v3b_upper_teeth  (16: I1-3, C, P2-4, M1 per side; each tooth its own shell)
                                     oral_v3b_upper_gums   (gingiva + alveolar mucosa of the upper arch)
                                     oral_v3b_palate       (hard palate with 8 rugae + inter-rugal papillae + incisive
                                                            papilla, and the soft palate to the fauces)
  lower jaw (rig parent 'mandible'): oral_v3b_lower_teeth  (14: I1-3, C, P3-4, M1 per side)
                                     oral_v3b_lower_gums
                                     oral_v3b_tongue       (dorsum with ~290 horny filiform papillae pointing caudad, the
                                                            median furrow, smooth ventral surface and borders)
Formula (permanent, cited and verified): I 3/3, C 1/1, P 3/2, M 1/1 = 30 (Reighard & Jennings 1901 p. 224; Merck Vet
Manual, Wright: one molar per quadrant). Every value: spec_mouth_v3b.json (source + confidence). Geometry is defined in the
JAW frame of feat_mouth_v3b (one definition, shared: the cavity, the arches, the gum lines, the palate and the floor) and
meshed in the head frame (mm) with feat_mouth_v3b.mesh_adaptive.

usage: python feat_oral_v3b.py build [part,...]   -> tripo_rebuild/layers/oral_v3b_<part>.npz + oral_v3b_manifest.json
       python feat_oral_v3b.py contacts           -> min distances between every upper and lower part (diagnostic)
"""
import json
import os
import sys
import time

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feat_mouth_v3b as MB  # noqa: E402

SPEC = MB.SPEC
ss, round_int, smax = MB.ss, MB.round_int, MB.smax
LAYERS = os.environ.get("ORAL_V3B_DIR", MB.LAYERS)       # override for scratch / test builds
S = MB.S_JAW
PARTS = {"upper_teeth": ("upper", "skull", "enamel"), "upper_gums": ("upper", "skull", "gingiva"),
         "palate": ("upper", "skull", "palatal mucosa"), "lower_teeth": ("lower", "mandible", "enamel"),
         "lower_gums": ("lower", "mandible", "gingiva"), "tongue": ("lower", "mandible", "tongue mucosa")}
RES = SPEC["resolution"]["parts_mm"]


def smin(a, b, k):
    return -smax(-a, -b, k)


# =============================================================== teeth
def _tooth_frame(t):
    m = np.asarray(t["mesial"], float); buc = np.array([-m[1], m[0]])
    if buc @ (t["base"][:2] - np.array([-15.0, 0.0])) < 0:
        buc = -buc
    return m, buc


def _profile(xn, cusps, base_frac=0.35, w_fixed=None):
    """crown top height fraction along the mesiodistal axis (xn -0.5 mesial .. +0.5 distal): a broad triangular main cusp
    (h >= 0.9) and narrower accessory cusps on its slopes (Reighard's cusp lists), over a low crown base"""
    z = np.zeros_like(xn)
    for c in cusps:
        x0, h = c; w = w_fixed or ((0.55 if len(cusps) == 1 else 0.42) if h >= 0.9 else 0.22)
        z = np.maximum(z, h * np.clip(1 - np.abs(xn - x0) / w, 0, 1) ** 1.15)
    return np.maximum(z, base_frac * np.clip(1 - (2 * xn) ** 2, 0, 1))


def tooth_sdf_jaw(J, t):
    """approximate SDF (skull mm, negative inside) of tooth t at jaw points J"""
    m, buc = _tooth_frame(t); b = t["base"]; T = t["tip"]; H = t["H"]; L = t["L"]; W = t["W"]
    z = (J[:, 2] - b[2]) * t["up"]                           # crown height coordinate (toward the occlusal side)
    zt = np.clip(z / H, 0, 1); c = (T[:2] - b[:2])[None] * zt[:, None]
    rel = J[:, :2] - b[:2][None] - c; x = rel @ m; y = rel @ buc; root = t["root"]; typ = t["type"]
    if typ == "canine":
        a = 0.5 * L * (1 - zt) ** 0.75 + 0.05; bb = 0.5 * W * (1 - zt) ** 0.75 + 0.05; top = z - H
    elif typ.startswith("incisor"):
        thin = 0.55 if typ == "incisor3" else 0.72
        a = 0.5 * L * (1 - 0.18 * zt) + 0.02; bb = 0.5 * W * (1 - thin * zt ** 1.3) + 0.03
        xn = np.clip(x / L, -0.5, 0.5)
        # a chisel edge with three minute cusps (Reighard p. 225): high crown base, narrow equal cusps (I3 more pointed)
        top = z - H * (_profile(xn, t["cusps"], 0.62, 0.30) if typ == "incisor3" else _profile(xn, t["cusps"], 0.82, 0.17))
    else:                                                    # premolars, carnassials, molars: a cusped blade
        xn = np.clip(x / L, -0.5, 0.5); zc = H * _profile(xn, t["cusps"])
        a = 0.5 * L * (1 - 0.06 * zt) + 0.02
        bb = 0.5 * W * np.sqrt(np.clip(1 - (np.clip(z, 0, None) / np.maximum(zc, 0.15)) ** 1.8, 0, 1)) + 0.10
        top = z - zc
    # the root (construction embedding): an elliptic taper below the crown base
    zr = np.clip(-z / max(root, 1e-6), 0, 1)
    a = np.where(z < 0, (0.5 * L) * (1 - 0.45 * zr) + 0.02, a); bb = np.where(z < 0, (0.5 * W) * (1 - 0.45 * zr) + 0.02, bb)
    r = np.sqrt((x / a) ** 2 + (y / bb) ** 2); side = (r - 1) * np.minimum(a, bb)
    F = np.maximum(np.maximum(side, top), -z - root)
    if t.get("protocone"):                                    # the upper P4's medial cusp (ESTIMATE)
        pc = t["protocone"]; xp = -pc["x"] * L; yp = -(0.5 * W + pc["lingual_mm"] * 0.6); hp = pc["height_frac"] * H
        e = np.sqrt(((x - xp) / pc["r"]) ** 2 + ((y - yp) / pc["r"]) ** 2 + (np.clip(z, 0, None) / max(hp, 0.1)) ** 2) - 1
        e = np.maximum(e * pc["r"], -z - 0.6 * root)
        F = smin(F, e, 0.25)
    return F


def _tooth_box(t, pad=0.6):
    """head-mm box holding tooth t (crown, tip, root) in the jaw frame, + pad"""
    b = t["base"]; T = t["tip"]; R = 0.5 * max(t["L"], t["W"]) + 1.2; up = t["up"]
    C = []
    for p, us in ((b, (b[2] - up * (t["root"] + 0.3), b[2] + up * 0.3)), (T, (T[2] - up * 0.3, T[2] + up * 0.3))):
        for dx in (-R, R):
            for dy in (-R, R):
                for u in us:
                    C.append([p[0] + dx, p[1] + dy, u])
    Hh = MB.to_head(np.array(C)); return Hh.min(0) - pad, Hh.max(0) + pad


def build_teeth(jaw, h=None, log=print):
    h = h or RES["teeth"]; Vs, Fs, lab, names, base, stats = [], [], [], [], 0, []
    for i, t in enumerate([t for t in MB.TEETH if t["jaw"] == jaw]):
        lo, hi = _tooth_box(t)
        V, F, st = MB.mesh_adaptive(lambda P, t=t: tooth_sdf_jaw(MB.to_jaw(P), t) * S, lo, hi, h, r=5, band=0.3, border_air=True)
        Vs.append(V); Fs.append(F + base); lab.append(np.full(len(V), i, np.int16)); names.append(t["name"]); base += len(V)
        stats.append(dict(name=t["name"], verts=st["verts"], tris=st["tris"], t_s=st["t_total_s"]))
        log(f"{t['name']}: {st['verts']} v {st['t_total_s']} s")
    return np.vstack(Vs), np.vstack(Fs), dict(label=np.concatenate(lab), label_names=np.array(names), stats=stats)


# =============================================================== gums
def _embrasure(jaw):
    """per dense arch point: 1 at a crown edge (where the interdental papilla stands), decaying 0.5 mm into the crown
    and into a diastema; the gum margin is scalloped with it (higher over each crown's middle)"""
    A = MB.ARCH[jaw]; sa = np.r_[0, np.cumsum(np.hypot(np.diff(A[:, 0]), np.diff(A[:, 1])))]; tree = cKDTree(A[:, :2])
    e = np.zeros(len(A))
    for t in MB.TEETH:
        if t["jaw"] != jaw or t["type"].startswith("molar"):
            continue
        _, j = tree.query(t["base"][:2]); st = sa[j]
        for edge in (st - 0.5 * t["L"], st + 0.5 * t["L"]):
            e = np.maximum(e, np.exp(-((sa - edge) / 0.5) ** 2))
    return e


EMB = {jaw: _embrasure(jaw) for jaw in ("upper", "lower")}
PAPILLA_MM = 0.35     # ESTIMATE: interdental papilla height (scalloped gingival margin)


def gum_sdf_jaw(J, jaw):
    f, l, u = J[:, 0], J[:, 1], J[:, 2]
    d = MB.plan_sample(f"{jaw}_d", f, l); hw = MB.plan_sample(f"{jaw}_hw", f, l); bx = MB._interp(SPEC["arch"]["gum_band_extra_mm"]["by_f"], f)
    col = SPEC["arch"]["gum_collar_mm"]["value"]; ug = MB.gum_line(jaw, f, l); top, bot = MB.bag_heights(f, l)
    w = ss((np.abs(d) - hw) / np.maximum(bx, 0.2)); band = np.abs(d) - (hw + bx)
    jj = np.clip(np.round(MB.plan_sample(f"{jaw}_j", f, l, order=0)).astype(int), 0, len(EMB[jaw]) - 1)
    col = col + PAPILLA_MM * EMB[jaw][jj]                      # the margin reaches further onto the crown at the papillae
    if jaw == "upper":
        target = np.where(d > 0, ug + MB.fornix_rise("upper", f), np.maximum(MB.palate_u(f, l), ug - col + 0.2))
        g = (ug - col) + (target - (ug - col)) * w; F = np.maximum(np.maximum(band, g - u), u - (top + MB.PAL_EMBED))
    else:
        target = np.where(d > 0, ug - MB.fornix_rise("lower", f), np.minimum(MB.floor_u(f), ug + col - 0.2))
        g = (ug + col) + (target - (ug + col)) * w; F = np.maximum(np.maximum(band, u - g), (bot - MB.PAL_EMBED) - u)
    # stay inside the cavity's wall + the embedding (the buccal face meets the lip / cheek lining there)
    return np.maximum(F, MB.cavity_jaw(J) - MB.PAL_EMBED)


# =============================================================== palate
PAL = SPEC["palate"]


def _rugae(f, l):
    R = PAL["rugae"]; n = R["count"]; hw = np.maximum(MB.palate_halfwidth(f), 1.0)
    fk = R["f_first"] + (R["f_last"] - R["f_first"]) * (np.arange(n) / (n - 1)) ** 1.15      # spacing widens caudad
    out = np.zeros_like(f); xl = np.clip(np.abs(l) / hw, 0, 2)
    fade = ss((0.92 - xl) / 0.12) * (1 - 0.35 * np.exp(-(l / 0.4) ** 2))                       # ends, midline raphe
    for k in range(n):
        c = fk[k] + R["bow_mm"] * (1 - xl ** 2)                                                 # concave caudad
        q = np.clip(1 - ((f - c) / (0.5 * R["width_mm"])) ** 2, 0, 1) ** 2; out = np.maximum(out, R["height_mm"] * q * fade)
    # rows of small papillae between the ridges
    P = PAL["inter_rugae_papillae"]
    for k in range(n - 1):
        fm = 0.5 * (fk[k] + fk[k + 1]) + R["bow_mm"] * (1 - xl ** 2); lj = np.round(l / P["pitch_mm"]) * P["pitch_mm"]
        r = np.hypot(f - fm, l - lj); q = np.clip(1 - (r / P["radius_mm"]) ** 2, 0, 1) ** 2
        out = np.maximum(out, P["height_mm"] * q * fade)
    ip = PAL["incisive_papilla"]; r = np.hypot(f - ip["f"], l)
    out = np.maximum(out, ip["height_mm"] * np.clip(1 - (r / ip["radius_mm"]) ** 2, 0, 1) ** 2)
    return out


def palate_sdf_jaw(J):
    f, l, u = J[:, 0], J[:, 1], J[:, 2]
    pu = MB.palate_u(f, l); bottom = pu - _rugae(f, l)               # the ridges hang into the mouth (-u)
    plan = MB.plan_sample("proper_sdf", f, l) - 0.6                  # 0.6 mm under the lingual gum (overlap)
    F = np.maximum(np.maximum(plan, bottom - u), u - (pu + 2 * MB.PAL_EMBED))
    return np.maximum(F, MB.cavity_jaw(J) - MB.PAL_EMBED)


# =============================================================== tongue
TG = SPEC["tongue"]


def _tongue_hw(f):
    tab = np.array(TG["half_w"], float); return np.interp(f, tab[::-1, 0], tab[::-1, 1], left=tab[-1, 1], right=0.0)


def tongue_heights(f, l):
    gap = TG["dorsum_below_palate_mm"]["value"]; fu = TG["furrow"]
    D = MB.palate_u(f, l) - gap - fu["depth_mm"] * np.exp(-(l / (0.5 * fu["width_mm"])) ** 2)
    free = ss((f - TG["free_tip_to_f"]) / 3.0)
    V = MB.floor_u(f) + free * TG["free_gap_mm"] - (1 - free) * TG["embed_mm"]
    return D, V


def _papillae():
    P = TG["papillae"]; f0, f1 = P["field_f"]; rng = np.random.default_rng(20261018)
    hw_mean = float(np.mean([_tongue_hw(x) for x in np.linspace(f1, f0, 50)]))
    area = 2 * P["field_half_w_frac"] * hw_mean * (f0 - f1); a = np.sqrt(area / P["count"] / (np.sqrt(3) / 2))
    pts = []
    for i, f in enumerate(np.arange(f1, f0 + 1e-9, a * np.sqrt(3) / 2)):
        lim = P["field_half_w_frac"] * _tongue_hw(f)
        for l in np.arange(-lim, lim + 1e-9, a) + (0.5 * a if i % 2 else 0.0):
            if abs(l) <= lim:
                pts.append([f + rng.uniform(-0.22, 0.22) * a, l + rng.uniform(-0.22, 0.22) * a])
    pts = np.array(pts); D, _ = tongue_heights(pts[:, 0], pts[:, 1])
    lie = np.radians(P["lie_deg"]); ax = np.array([-np.cos(lie), 0.0, np.sin(lie)])           # caudad (-f), lifting
    base = np.c_[pts, D - 0.12]; return dict(base=base, axis=ax, L=P["length_mm"], rb=P["base_r_mm"], tree=cKDTree(base), n=len(base),
                                             spacing_mm=round(float(a), 3))


PAP = _papillae()


def _papilla_sdf(J, k=3):
    d, j = PAP["tree"].query(J, k=k, distance_upper_bound=PAP["L"] + PAP["rb"] + 0.4); out = np.full(len(J), 1e3)
    ax = PAP["axis"]; L = PAP["L"]
    for c in range(k):
        ok = np.isfinite(d[:, c])
        if not ok.any():
            continue
        B = PAP["base"][j[ok, c]]; q = J[ok] - B; t = np.clip(q @ ax / L, 0, 1)
        r = PAP["rb"] + (0.03 - PAP["rb"]) * t; dist = np.linalg.norm(q - t[:, None] * L * ax[None], axis=1) - r
        out[ok] = np.minimum(out[ok], dist)
    return out


def tongue_sdf_jaw(J, papillae=True):
    f, l, u = J[:, 0], J[:, 1], J[:, 2]
    hw = _tongue_hw(f); plan = round_int(np.abs(l) - hw, f - TG["tip_f"], 1.2)
    plan = np.maximum(plan, (TG["root_f"] - 1.5) - f)                   # the root runs 1.5 mm into the skin
    D, V = tongue_heights(f, l); slab = np.maximum(u - D, V - u)
    F = round_int(plan, slab, 1.8)
    if papillae:
        F = smin(F, _papilla_sdf(J), 0.06)
    return F


# =============================================================== building
def part_fn(name):
    if name == "upper_gums":
        return lambda P: gum_sdf_jaw(MB.to_jaw(P), "upper") * S
    if name == "lower_gums":
        return lambda P: gum_sdf_jaw(MB.to_jaw(P), "lower") * S
    if name == "palate":
        return lambda P: palate_sdf_jaw(MB.to_jaw(P)) * S
    if name == "tongue":
        return lambda P: tongue_sdf_jaw(MB.to_jaw(P)) * S
    raise KeyError(name)


def part_box(name, pad=1.0):
    """head-mm box of a part from its plan region and height range (jaw frame corners -> head)"""
    Fg, Lg = MB.PLAN["F"], MB.PLAN["L"]
    if name == "tongue":
        m = (np.abs(Lg) <= _tongue_hw(Fg) + 0.5) & (Fg <= TG["tip_f"] + 0.5) & (Fg >= TG["root_f"] - 0.5); urng = (-12.0, 4.0)
    elif name == "palate":
        m = MB.PLAN["proper"] | (MB.PLAN["proper_sdf"] < 0.8); urng = (-4.0, 5.0)
    else:
        jaw = name.split("_")[0]; m = MB.PLAN[f"{jaw}_band"] | (np.abs(MB.PLAN[f"{jaw}_d"]) < MB.PLAN[f"{jaw}_hw"] + 2.0)
        urng = (-5.0, 8.0) if jaw == "upper" else (-13.0, 1.0)
    fs, ls = Fg[m], Lg[m]
    C = np.array([[a, b, c] for a in (fs.min(), fs.max()) for b in (ls.min(), ls.max()) for c in urng])
    H = MB.to_head(C); return np.floor(H.min(0) - pad), np.ceil(H.max(0) + pad)


def _vn(V, F):
    return MB._vn(V, F)


def save_part(name, V, F, extra=None):
    sys.path.insert(0, os.path.join(MB.ROOT, "tripo_rebuild"))
    import partition as PT
    jaw, parent, mat = PARTS[name]; N = _vn(V, F); obj = f"oral_v3b_{name}"
    fn = os.path.join(LAYERS, f"{obj}.npz"); extra = extra or {}
    np.savez_compressed(fn, v=PT.HC + (V / 1000) @ PT.HR.T, f=F.astype(np.int32), n=N @ PT.HR.T, v_head_mm=V, object=obj, jaw=jaw,
                        rig_parent=parent, material=mat, hinge_L_head_mm=MB.TMJ_HEAD_MM["L"], hinge_R_head_mm=MB.TMJ_HEAD_MM["R"],
                        note=f"{obj}: feat_oral_v3b ({jaw} jaw, rig parent '{parent}'); world metres (v), head mm (v_head_mm); "
                             f"spec_mouth_v3b.json", **extra)
    return fn


def build(names=None, log=print):
    names = names or list(PARTS); rep = {}
    for name in names:
        t0 = time.time()
        if name.endswith("teeth"):
            V, F, ex = build_teeth(name.split("_")[0], h=float(os.environ.get("ORAL_V3B_HT", RES["teeth"])), log=log); st = {"teeth": ex["stats"], "count": len(ex["label_names"])}
            extra = {"label": ex["label"], "label_names": ex["label_names"]}
        else:
            lo, hi = part_box(name); h = RES["gums"] if name.endswith("gums") else RES[name]
            h = float(os.environ.get("ORAL_V3B_H", h))
            V, F, st = MB.mesh_adaptive(part_fn(name), lo, hi, h, r=5, band=0.5, border_air=True, slab_nodes=12e6, log=log)
            extra = {}
            if name == "tongue":
                extra = {"papillae_base_head_mm": MB.to_head(PAP["base"]), "papillae_axis_head": MB.dir_to_head(PAP["axis"]),
                         "papillae_length_mm": PAP["L"] * S}
        fn = save_part(name, V, F, extra)
        rep[name] = {**(st if isinstance(st, dict) else {}), "file": os.path.basename(fn), "verts": int(len(V)), "tris": int(len(F)),
                     "t_s": round(time.time() - t0, 1), "grid_mm": h if not name.endswith("teeth") else float(os.environ.get("ORAL_V3B_HT", RES["teeth"]))}
        log(f"{name}: {len(V)} v {len(F)} f -> {fn} ({rep[name]['t_s']} s)")
    man_fn = os.path.join(LAYERS, "oral_v3b_manifest.json")
    man = json.load(open(man_fn)) if os.path.exists(man_fn) else {}
    man.update({"_what": "oral cavity parts of mouth v3b (feat_oral_v3b); upper parts follow the skull, lower parts the mandible",
                "objects": {f"oral_v3b_{k}": {"jaw": PARTS[k][0], "rig_parent": PARTS[k][1], "material": PARTS[k][2]} for k in PARTS},
                "hinge_head_mm": {k: np.round(v, 3).tolist() for k, v in MB.TMJ_HEAD_MM.items()},
                "hinge_src": "ref20 lateral TMJ pick (-56.81, -1.50) jaw mm, half-span 16.5 mm (skull_landmarks tmj x), through the jaw frame",
                "dental_formula": "I 3/3, C 1/1, P 3/2, M 1/1 = 30 (Reighard & Jennings 1901 p. 224; Merck Vet Manual, Wright)",
                "registration": MB.registration_report(), "papillae": {"n": PAP["n"], "spacing_mm_skull": PAP["spacing_mm"]}})
    man.setdefault("builds", {}).update(rep); json.dump(man, open(man_fn, "w"), indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x))
    return rep


def load_part(name):
    Z = np.load(os.path.join(LAYERS, f"oral_v3b_{name}.npz")); return Z["v_head_mm"].astype(float), Z["f"].astype(np.int64), Z


def contacts(names_up=("upper_teeth", "upper_gums", "palate"), names_lo=("lower_teeth", "lower_gums", "tongue")):
    out = {}
    for a in names_up:
        Va, _, _ = load_part(a); ta = cKDTree(Va)
        for b in names_lo:
            Vb, _, _ = load_part(b); d, _ = ta.query(Vb); out[f"{a}|{b}"] = round(float(d.min()), 3)
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build(sys.argv[2].split(",") if len(sys.argv) > 2 else None)
    elif cmd == "contacts":
        print(json.dumps(contacts(), indent=1))
