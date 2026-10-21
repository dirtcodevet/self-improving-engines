"""Fit the L1 FRAME's pose to the photo with bone lengths held at real anatomy (one size factor) - runs outside Blender.

Evidence, ranked (engine-grounding G3): the photo's paw contact points (measured), paws on the ground (constraint),
every bone inside the photo's silhouette with a soft-tissue margin (measured + constraint), sourced bone lengths and
ratios (estimates with sources, fixed), natural standing joint angles (weak prior). Depth is unobserved: the prior
and the containment of BOTH sides' bones carry it.

usage: python frame_fit.py <case_dir> <mesh_ver> <out_dir>
writes <out_dir>/frame.json (pose, joints, bone lengths) and <out_dir>/frame_on_photo.png (overlay)
"""
import json
import os
import sys

import cv2
import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "review"))
import frame as FR  # noqa: E402
from project_mask import project  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# QUIET-STANCE posture prior, radians from straight down (+ forward). SOURCED (R4c): Fung & Macpherson 1999 J
# Neurophysiol 82:3056, Fig. 5 (intact cat Re, 3.8 kg, preferred paw spacing; read off the graph, +-3 deg; n = 1):
# hind metatarsus 78 deg to the ground, ankle 140, knee 90 (hip 121: inconsistent with the paper's own pelvis line,
# not used - the frame has no pelvis angle); fore scapula 61 deg above horizontal, shoulder 128, elbow 150, wrist 178.
# Chained from the ground up (references/cat-standing-posture.md): hip and shoulder joints ~23 cm at s = 1, the
# paper's measured ~22 cm. sd 15 deg: n = 1 plus unknown cat-to-cat spread (a stated judgment, flagged).
# The previous prior (a_fem 34, a_tib -36, a_mt 14; scapula 55) was unsourced and did not stand on four paws.
PRIOR = {
    "fore": dict(a_hum=np.radians(-23), a_rad=np.radians(7), a_mc=np.radians(5), abd=0.02),
    "hind": dict(a_fem=np.radians(62), a_tib=np.radians(-28), a_mt=np.radians(12), abd=0.02),
}
PRIOR_SD = np.radians(15)
SCAP_PRIOR = np.radians(61)
NAMES_F, NAMES_H = ("a_hum", "a_rad", "a_mc", "abd"), ("a_fem", "a_tib", "a_mt", "abd")
# ablation (find which evidence conflicts): FRAME_FIT_DISABLE="tail,side,dorsal,trunkprior,scapprior,posture,pawv,refpaw,contain_limbs,size"
DISABLE = set(filter(None, os.environ.get("FRAME_FIT_DISABLE", "").split(",")))


def pack(P):
    v = [P["s"], *P["hip_c"], P["yaw"], P["pitch"], P["w_shoulder"], P["w_hip"], P["trunk"], P["scap"], P["pelvis"]]
    for sd in "RL":
        v += [P[f"fore.{sd}"][k] for k in NAMES_F] + [P[f"hind.{sd}"][k] for k in NAMES_H]
    return np.array(v, float)


def unpack(v):
    P = dict(s=v[0], hip_c=v[1:4], yaw=v[4], pitch=v[5], w_shoulder=v[6], w_hip=v[7], trunk=v[8], scap=v[9], pelvis=v[10])
    i = 11
    for sd in "RL":
        P[f"fore.{sd}"] = dict(zip(NAMES_F, v[i:i + 4])); i += 4
        P[f"hind.{sd}"] = dict(zip(NAMES_H, v[i:i + 4])); i += 4
    return P


def main(case, mv, out):
    os.makedirs(out, exist_ok=True)
    T, B = FR.load_template(os.path.join(ROOT, "engine", "packs", "felid", "frame_template.json"))
    cam = json.load(open(os.path.join(case, "mesh", f"{mv}_camera.json")))
    L = json.load(open(os.path.join(case, "mesh", f"{mv}_landmarks.json")))["landmarks"]
    pts = json.load(open(os.path.join(case, "ref_points.json")))["points"]
    img = cv2.imread(os.path.join(case, "ref.jpg")); H, W = img.shape[:2]
    mask = (cv2.imread(os.path.join(case, "ref_mask.png"), 0) > 127).astype(np.uint8)
    sdf = cv2.distanceTransform(mask, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - mask, cv2.DIST_L2, 5)

    def proj(p):
        return project(np.atleast_2d(p), cam, W, H)[0]

    sdf_s = cv2.GaussianBlur(sdf.astype(np.float32), (0, 0), 2.0)

    def inside(uv):
        """signed distance to the silhouette edge (px, + inside), BILINEAR: integer pixel lookup gave the optimiser
        a zero slope, so the containment term could not move the pose (A1: a knob that did not move the output)"""
        x, y = np.clip(uv[:, 0], 0, W - 2), np.clip(uv[:, 1], 0, H - 2)
        x0, y0 = x.astype(int), y.astype(int); fx, fy = x - x0, y - y0
        return (sdf_s[y0, x0] * (1 - fx) * (1 - fy) + sdf_s[y0, x0 + 1] * fx * (1 - fy)
                + sdf_s[y0 + 1, x0] * (1 - fx) * fy + sdf_s[y0 + 1, x0 + 1] * fx * fy)

    # initial pose from the current model (trunk, widths) and the prior (angles)
    hip_c0 = (np.array(L["hip.R"]) + np.array(L["hip.L"])) / 2
    sh_c0 = (np.array(L["shoulder.R"]) + np.array(L["shoulder.L"])) / 2
    d = sh_c0 - hip_c0
    yaw0 = np.arctan2(d[0], -d[1])
    P0 = dict(s=0.95, trunk=0.28, scap=SCAP_PRIOR, pelvis=0.05, hip_c=hip_c0 + np.array([0, 0, 0.03]), yaw=yaw0, pitch=0.05,
              w_shoulder=abs(L["shoulder.L"][0] - L["shoulder.R"][0]) or 0.05, w_hip=abs(L["hip.L"][0] - L["hip.R"][0]) or 0.06)
    for sd in "RL":
        P0[f"fore.{sd}"] = dict(PRIOR["fore"]); P0[f"hind.{sd}"] = dict(PRIOR["hind"])
    v0 = pack(P0)
    paws = {k: np.array(pts[k], float) for k in ("fpaw.R", "fpaw.L", "hpaw.R", "hpaw.L")}
    MARGIN = 6.0                                                     # px of soft tissue around every bone (at least)
    # MEASURED landmarks (frame/landmarks_measured.json: tail pigment, outline corners, dorsal line); the old
    # model's tail root was a derived value 146 px off the photo's - it bent the whole trunk (R4b)
    MEAS = json.load(open(os.path.join(case, "frame", "landmarks_measured.json")))
    SIDE = json.load(open(os.path.join(case, "frame", "side_proportions.json")))
    tail_root_px = np.array(MEAS["points"]["tail_emergence"]["xy"], float)
    dorsal = np.array(MEAS["dorsal_line"]["xy"], float)
    # G5: a reference supplies geometry only where it agrees with the photo. The reference trunk's tail root misses
    # the measured one by > 40 px -> its trunk depth is NOT used (paw depth kept, weakened)
    ref_tail_err = float(np.linalg.norm(proj(np.array(L["tail"][0]))[0] - tail_root_px))
    USE_REF_TRUNK = ref_tail_err < 40
    print(f"reference trunk agreement: tail root {ref_tail_err:.0f} px off the photo -> trunk depth from the reference: {USE_REF_TRUNK}", file=sys.stderr)
    # the head is already registered to the photo (eyes 1-2 px): the neck runs from the withers to the skull base,
    # taken as the head centre moved back and down by a third of the eye spacing x 2 (no skull yet at L1)
    eyes = np.array(L["eye.R"]), np.array(L["eye.L"]); E = np.linalg.norm(eyes[1] - eyes[0])
    Rh = np.array(L["head_R"]); skull_base = np.array(L["head"]) + Rh @ np.array([0, 0.9 * E, -0.4 * E])
    # DEPTH (unobserved by the photo; skill lesson J3: the camera is ~16 cm above the floor, so paws-on-the-ground
    # along a photo ray fixes depth badly): the trunk's depth along the camera ray comes from the 3-D reference
    # (person 2026-10-17: a good reference may supply geometry), sd 20 mm; the photo still sets everything it sees
    cpos = np.array(cam["location"], float)
    ref_hip, ref_sh = hip_c0, sh_c0

    def resid(v):
        P = unpack(v); J = FR.build(P, B)
        r = []
        for k, p in paws.items():                                    # 1. paw contact points on the photo: the
            e = proj(J[k])[0] - p                                    # HORIZONTAL pixel is reliable; at a 4 deg
            r += [e[0] / 2.0, ("pawv" not in DISABLE) * e[1] / 6.0]  # camera the vertical one mostly encodes depth (J3)
            mid = J[k.replace("fpaw", "mcp").replace("hpaw", "mtp")]   # paw depth from the reference (G3 rank 3)
            ref = np.array(L[k]); ray = (ref - cpos) / np.linalg.norm(ref - cpos)
            r.append(("refpaw" not in DISABLE) * float((mid - ref) @ ray) / 0.040)   # weak: the reference's paws were 20-40 px off
        for sd in "RL":                                              # 2. digitigrade: toes and MCP/MTP on the ground
            r += [(J[f"fpaw.{sd}"][2] - 0.006 * P["s"]) / 0.002, (J[f"hpaw.{sd}"][2] - 0.006 * P["s"]) / 0.002]
        for a, b, A, Bp in FR.segments(J):                           # 3. bones inside the silhouette: the TRUNK
            q = A[None] + np.linspace(0, 1, 6)[:, None] * (Bp - A)[None]   # strongly (spine, girdles, scapulae); limbs
            trunk = (a, b) in [(x, y) for x, y in FR.SPINE] or "scapula" in b   # weakly - the whole-cat outline cannot
            on_c = ("contain_limbs" not in DISABLE) or trunk
            r += list(on_c * np.maximum(0, (10.0 if trunk else 3.0) - inside(proj(q))) / (2.0 if trunk else 6.0))   # tell legs apart
        for sd in "RL":                                              # 4. weak posture prior (15 deg)
            for k in NAMES_F: r.append(("posture" not in DISABLE) * (P[f"fore.{sd}"][k] - PRIOR["fore"][k]) / PRIOR_SD)
            for k in NAMES_H: r.append(("posture" not in DISABLE) * (P[f"hind.{sd}"][k] - PRIOR["hind"][k]) / PRIOR_SD)
        r.append(("size" not in DISABLE) * (P["s"] - 1.0) / 0.08)    # 5. size prior (anatomical spread)
        tail_root = J["sacrum"] - FR.axes(P["yaw"], P["pitch"])[3] * 0.025 * P["s"]   # 6. tail root behind the sacrum
        tr = proj(tail_root)[0]                                      # the measured point is where the tail EMERGES
        on = "tail" not in DISABLE
        r.append(on * (tr[0] - tail_root_px[0]) / 8.0)               # below the rump (occluded root): the root projects
        r.append(on * max(0.0, tr[1] - tail_root_px[1]) / 6.0)       # within ~30 px sideways, at or ABOVE it,
        r.append(on * max(0.0, 10.0 - float(inside(tr[None])[0])) / 4.0)  # and inside the rump outline
        if USE_REF_TRUNK:
            for jn, ref in (("hip_c", ref_hip), ("shoulder_c", ref_sh)):  # 8. trunk depth from the reference (if it agrees)
                ray = (ref - cpos) / np.linalg.norm(ref - cpos)
                r.append(float((J[jn] - ref) @ ray) / 0.015)
        # 9. side proportion: trunk / withers height (Day & Jayne 1.23 joint-to-joint; side reference 1.34), sd 0.10
        r.append(("side" not in DISABLE) * (np.linalg.norm(J["shoulder_c"] - J["hip_c"]) / max(J["withers"][2], 1e-3) - 1.28) / 0.10)
        # 10. the spine lies UNDER the photo's dorsal line by a soft-tissue gap (band 10-120 px, unsourced: flagged)
        sp = np.array([proj(J["withers"] + (J["sacrum"] - J["withers"]) * t)[0] for t in np.linspace(0, 1, 24)])
        o = np.argsort(sp[:, 0]); sx, sy = sp[o, 0], sp[o, 1]
        for x, y in dorsal[::2]:                                     # one residual per sample, always (fixed length)
            if sx[0] <= x <= sx[-1]:
                g = float(np.interp(x, sx, sy)) - y
                r.append(("dorsal" not in DISABLE) * max(0.0, 10 - g, g - 120) / 5.0)
            else:   # outside the trunk spine's span: that part of the top outline is the NECK crest (no neck yet) - no term
                r.append(0.0)
        neck = np.linalg.norm(skull_base - J["withers"]) / P["s"]  # 7. neck length 60-110 mm (weak, anatomical)
        r.append(max(0, 0.060 - neck, neck - 0.110) / 0.01)
        r += [(P["w_shoulder"] - 0.055) / 0.015, (P["w_hip"] - 0.060) / 0.015]
        r.append(("trunkprior" not in DISABLE) * (P["trunk"] - 0.320 * P["s"]) / 0.060)   # trunk length: soft prior
        r.append(("scapprior" not in DISABLE) * (P["scap"] - SCAP_PRIOR) / np.radians(10))   # Fung & Macpherson 1999 (n = 1)
        SR = SIDE["ratios"]; whh = max(J["withers"][2], 1e-3)         # side reference (picked, one sample: flagged)
        r.append(("side" not in DISABLE) * (P["pelvis"] / whh - SR["croup_above_hip_over_withers"]) / 0.05)
        r.append(("side" not in DISABLE) * ((J["shoulder.R"][2] + J["shoulder.L"][2]) / 2 / whh - SR["shoulder_joint_over_withers"]) / 0.08)
        return np.array(r)

    lo = np.full_like(v0, -np.inf); hi = np.full_like(v0, np.inf)
    lo[0], hi[0] = T["size_factor_range"]
    lo[6] = lo[7] = 0.03; hi[6] = hi[7] = 0.10
    lo[8], hi[8] = 0.12, 0.40
    lo[9], hi[9] = np.radians(40), np.radians(75)                    # scapula inclination: UNSOURCED range (flagged)
    lo[10], hi[10] = 0.020, 0.090                                    # croup above the hip joints (m)
    # anatomical joint ranges (hard): no fit may bend a joint the wrong way
    RANGE_F = dict(a_hum=(-70, 10), a_rad=(-25, 25), a_mc=(0, 60), abd=(-15, 15))
    RANGE_H = dict(a_fem=(0, 80), a_tib=(-80, 0), a_mt=(-10, 50), abd=(-15, 15))
    i = 11
    for sd in "RL":
        for k in NAMES_F: lo[i], hi[i] = np.radians(RANGE_F[k]); i += 1
        for k in NAMES_H: lo[i], hi[i] = np.radians(RANGE_H[k]); i += 1
    res = least_squares(resid, np.clip(v0, lo + 1e-6, hi - 1e-6), bounds=(lo, hi), max_nfev=4000, x_scale="jac")
    P = unpack(res.x); J = FR.build(P, B)

    # report + overlay
    rep = dict(s=float(P["s"]), cost=float(res.cost), paw_px={k: float(np.linalg.norm(proj(J[k])[0] - p)) for k, p in paws.items()})
    viol = []
    for a, b, A, Bp in FR.segments(J):
        q = A[None] + np.linspace(0, 1, 6)[:, None] * (Bp - A)[None]
        m = inside(proj(q)).min()
        if m < 0: viol.append((f"{a}->{b}", round(float(m), 1)))
    rep["bones_outside_silhouette_px"] = viol
    rep["angles_deg"] = {f"{g}.{sd}": {k: round(float(np.degrees(P[f"{g}.{sd}"][k])), 1) for k in (NAMES_F if g == "fore" else NAMES_H)}
                         for g in ("fore", "hind") for sd in "RL"}
    rep["withers_height_mm"] = float(J["withers"][2] * 1000)
    rep["trunk_mm"] = float(P["trunk"] * 1000); rep["trunk_prior_mm"] = float(320 * P["s"])
    rep["scapula_deg"] = float(np.degrees(P["scap"]))
    rep["pinned_at_bounds"] = [i for i in range(len(res.x)) if min(res.x[i] - lo[i], hi[i] - res.x[i]) < 1e-3]
    rep["lengths_mm"] = {k: round(v * P["s"] * 1000, 1) for k, v in B.items()}
    ov = (img * 0.55).astype(np.uint8)
    cv2.drawContours(ov, cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0], -1, (200, 200, 200), 1)
    for a, b, A, Bp in FR.segments(J):
        ua, ub = proj(A)[0], proj(Bp)[0]
        col = (80, 220, 255) if a.endswith("R") or b.endswith("R") else ((255, 160, 80) if a.endswith("L") or b.endswith("L") else (120, 255, 120))
        cv2.line(ov, tuple(int(x) for x in ua), tuple(int(x) for x in ub), col, 3, cv2.LINE_AA)
    for k, p in paws.items():
        cv2.circle(ov, tuple(int(x) for x in p), 7, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(out, "frame_on_photo.png"), ov)
    json.dump(dict(pose={k: (np.asarray(v).tolist() if not isinstance(v, dict) else {kk: float(vv) for kk, vv in v.items()})
                         for k, v in P.items()}, joints={k: np.asarray(v).tolist() for k, v in J.items()}, report=rep),
              open(os.path.join(out, "frame.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
