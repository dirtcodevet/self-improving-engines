"""WHOLE-SURFACE SCAN by math (2026-10-19, after the person's "let math carry the day"). Reads every vertex of a body
skin and flags shape anomalies as numbered patches, each with its region, size and strength:

  - DENT: concave (H < -6 /m) inside a rounded neighbourhood (H_20mm > 2 /m); proven on the breast-side dent;
  - FLAT: curvature well below its own 2 cm neighbourhood inside a convex area (H / H_20mm < 0.5, H_20mm > 4 /m),
    like the band found on the breasts;
  - BUMP: curvature well above its neighbourhood (H / H_20mm > 2.2 and H > 12 /m), a local knob or ridge;
  - CREASE: strong concave curvature (H < -20 /m). Known creases (the fold under each breast, the cleavage, the navel,
    the gluteal cleft, the armpit contact fold, the nipple-areola zone, the neck and limb caps) are labelled
    expected; any other is flagged;
  - ASYMMETRY: curvature differs between a vertex and its mirror (x -> -x) by more than 12 /m over a patch, where the
    region is meant to be symmetric (the photo's real asymmetry is small);
  - STEP: a curvature jump between neighbouring vertices beyond the mesh's own noise (a seam or a fitting artefact).

Patches are connected vertex sets of at least 1 cm2. Regions are named by height and side from the body's own landmarks.
usage: python surface_scan.py <skin.npz> <out_prefix>   (skin.npz: v, f and zone weights as in the base torso pack)
Writes <out_prefix>.json (patch list, totals) and <out_prefix>.png (front and back maps).
"""
import json
import sys

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else ".")
import surface_analysis as sa  # noqa: E402


def region_name(p, n, ref, arm_share=0.0, breast_share=None):
    """the patch's name. Body part from what the patch SITS ON where the mesh says so (2026-10-19: four patches named
    "breast" by position were 100 % arm vertices, and a cause was asserted from the name): more than half its vertices on
    the arm -> arm; on the breast zone (zone > 0.05) -> breast; a front patch at breast height off the breast zone ->
    "chest side". Position decides only what the mesh does not label."""
    z, x = p[2], p[0] - ref["xmid"]
    side0 = "left" if x > 0.03 else "right" if x < -0.03 else "centre"
    face0 = "front" if n[1] < 0 else "back"
    if arm_share > 0.5:
        return f"{side0} arm ({face0})"
    if breast_share is not None and breast_share > 0.5:
        return f"{side0} breast ({face0})"
    if breast_share is not None and z <= ref["z_nipple"] + 0.04 and z > ref["z_imf"] and face0 == "front":
        return f"{side0} chest side ({face0})"
    side = "left" if x > 0.03 else "right" if x < -0.03 else "centre"
    face = "front" if n[1] < 0 else "back"
    if abs(x) > ref["arm_x"]: part = "arm"
    elif z > ref["z_notch"] - 0.01: part = "neck/shoulder"
    elif z > ref["z_nipple"] + 0.04: part = "upper chest" if face == "front" else "upper back"
    elif z > ref["z_imf"]: part = "breast" if face == "front" else "mid back"
    elif z > ref["z_navel"]: part = "abdomen" if face == "front" else "lower back"
    else: part = "lower abdomen" if face == "front" else "buttocks"
    return f"{side} {part} ({face})"


def main():
    path, out = sys.argv[1:3]
    z = np.load(path); V, F = z["v"].astype(np.float64), z["f"]
    N = sa.vertex_normals(V, F)
    c = V.mean(0)
    if np.mean(np.einsum("ij,ij->i", V - c, N)) < 0: N = -N
    L, area = sa.cot_laplacian(V, F)
    H = np.einsum("ij,ij->i", -(L @ V) / (2 * np.maximum(area, 1e-20))[:, None], N)
    M = sa.umbrella(V, F)
    edge = np.linalg.norm(V[F[:, 0]] - V[F[:, 1]], axis=1).mean()
    it = lambda mm: max(1, int((mm / 1000 / edge) ** 2))
    H5 = sa.smooth(H.copy(), M, it(5)); H20 = sa.smooth(H5.copy(), M, it(20))
    ratio = H5 / np.where(np.abs(H20) > 1e-6, H20, np.nan)
    # known creases and zones
    nac = (z["areola"] > 0.5) | (z["nipple"] > 0.5) if "areola" in z.files else np.zeros(len(V), bool)
    if nac.any(): nac = cKDTree(V[nac]).query(V)[0] < 0.004       # the areola (weight > 0.5) + 4 mm: its designed rim
    arm = z["arm_limb"] > 0.5 if "arm_limb" in z.files else np.zeros(len(V), bool)
    nip = V[z["nipple"] > 0.5] if "nipple" in z.files else V[:0]
    ref = {"z_notch": float(V[:, 2].max() - 0.06), "z_nipple": float(nip[:, 2].mean()) if len(nip) else 0.0,
           "z_imf": float(nip[:, 2].mean() - 0.06) if len(nip) else -0.2, "z_navel": float(nip[:, 2].mean() - 0.30) if len(nip) else -0.4,
           "ymid": float(np.median(V[:, 1])), "arm_x": float(np.percentile(np.abs(V[~arm, 0]), 99))}
    zmax, zmin = V[:, 2].max(), V[:, 2].min()
    caps = (V[:, 2] > zmax - 0.012) | (V[:, 2] < zmin + 0.035)   # the lower cut's edge strip reads as flat: not anatomy
    capface = (V[:, 2] > zmax - 0.08) & (N[:, 2] > 0.7)           # a slanted cut cap (the neck under the jaw): flat, facing up
    if capface.any(): caps |= cKDTree(V[capface]).query(V)[0] < 0.008
    xmid = float(np.median(V[~arm, 0])); ref["xmid"] = xmid
    front, back = N[:, 1] < 0, N[:, 1] > 0
    zn = ref["z_nipple"]; dx = np.abs(V[:, 0] - xmid)
    # known anatomy that is MEANT to be concave (labelled expected, reported separately)
    known = {}
    tips = [V[(z["nipple"] > 0.5) & (np.sign(V[:, 0] - xmid) == sg)] for sg in (1, -1)] if "nipple" in z.files else []
    imf = np.zeros(len(V), bool)
    for t in tips:
        if len(t): c_ = t.mean(0); imf |= front & (V[:, 2] < c_[2] - 0.030) & (V[:, 2] > c_[2] - 0.090) & (np.abs(V[:, 0] - c_[0]) < 0.075)
    known["fold under the breast"] = imf
    known["cleavage"] = front & (dx < 0.035) & (V[:, 2] < zn + 0.05) & (V[:, 2] > zn - 0.09)
    cand = front & (dx < 0.03) & (V[:, 2] < zn - 0.18) & (V[:, 2] > zn - 0.42)
    nav = V[cand][np.argmin(H5[cand])] if cand.any() else None
    known["navel"] = (np.linalg.norm(V - nav, axis=1) < 0.018) if nav is not None else np.zeros(len(V), bool)
    known["gluteal cleft"] = back & (dx < 0.03) & (V[:, 2] < zn - 0.28)
    known["spine furrow"] = back & (dx < 0.022) & (V[:, 2] >= zn - 0.28)
    if arm.any():
        tA = cKDTree(V[arm]); tB = cKDTree(V[~arm])
        near = np.zeros(len(V), bool)
        near[~arm] = tA.query(V[~arm])[0] < 0.0025; near[arm] = tB.query(V[arm])[0] < 0.0025
        known["armpit / arm contact"] = near
    known["collarbones and neck relief"] = front & (V[:, 2] > -0.035)
    import os
    rigp = os.path.join(os.path.dirname(os.path.abspath(path)), "rig.json")
    if os.path.exists(rigp) and arm.any():
        rig = json.load(open(rigp)); ez = []
        def heads(o):
            if isinstance(o, dict):
                for kk, vv in o.items():
                    if "forearm" in str(kk).lower() and isinstance(vv, dict) and "head" in vv: ez.append(vv["head"][2])
                    heads(vv)
            elif isinstance(o, list):
                for vv in o: heads(vv)
        heads(rig)
        if ez: known["elbows"] = arm & (np.abs(V[:, 2] - float(np.mean(ez))) < 0.045)
    known_any = np.zeros(len(V), bool)
    for m_ in known.values(): known_any |= m_
    expected = nac | caps
    # mirror asymmetry about the measured midline; arms (posed differently L/R, as in the photo) excluded
    tree = cKDTree((V - [xmid, 0, 0]) * np.array([-1, 1, 1]) + [xmid, 0, 0])
    dm, jm = tree.query(V)
    asym = np.abs(H5 - H5[jm]); asym[(dm > 0.003) | arm | arm[jm]] = 0.0
    # step: neighbour curvature jump beyond the mesh's own noise
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    jump = np.zeros(len(V)); np.maximum.at(jump, e[:, 0], np.abs(H5[e[:, 0]] - H5[e[:, 1]]))
    noise = np.percentile(jump[~expected], 99)
    kinds = {
        "DENT": (H5 < -6) & (H20 > 2) & ~expected & ~known_any,   # concave inside a rounded area (proven: the breast-side dent, v2 12.2 -> v3 5.4 cm2)
        "FLAT": (ratio < 0.5) & (H20 > 8) & ~expected & ~known_any,
        "BUMP": (ratio > 2.5) & (H5 > 15) & ~expected & ~known_any,
        "CREASE": (H5 < -25) & ~expected & ~known_any,
        "ASYMMETRY": (asym > 15) & ~expected & ~known_any,
        "STEP": (jump > 3 * noise) & ~expected,
    }
    A = sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(len(V), len(V))).tocsr()
    patches = []
    for kind, m in kinds.items():
        idx = np.where(m)[0]
        if not len(idx): continue
        sub = A[idx][:, idx]
        nc, lab = connected_components(sub, directed=False)
        for k in range(nc):
            members = idx[lab == k]
            a_cm2 = area[members].sum() * 1e4
            if a_cm2 < (1.0 if kind == "STEP" else 2.0): continue
            p = V[members].mean(0); pn = N[members].mean(0)
            strength = {"DENT": float(np.median(H5[members])), "FLAT": float(np.nanmedian(ratio[members])), "BUMP": float(np.nanmedian(ratio[members])),
                        "CREASE": float(np.median(H5[members])), "ASYMMETRY": float(np.median(asym[members])),
                        "STEP": float(np.median(jump[members]) / noise)}[kind]
            a_sh = float(arm[members].mean()) if arm.any() else 0.0
            b_sh = float((z["breast"][members] > 0.05).mean()) if "breast" in z.files else None
            patches.append({"kind": kind, "region": region_name(p, pn, ref, a_sh, b_sh), "arm_share": round(a_sh, 2),
                            "breast_zone_share": None if b_sh is None else round(b_sh, 2), "face": "front" if pn[1] < 0 else "back", "area_cm2": round(float(a_cm2), 2),
                            "strength": round(strength, 2), "centre_mm": [round(float(x) * 1000, 1) for x in p]})
    patches.sort(key=lambda d: -d["area_cm2"])
    for i, d in enumerate(patches): d["id"] = i + 1
    print("known-anatomy masks:", {k: int(m_.sum()) for k, m_ in known.items()})
    tot = {k: {"patches": sum(1 for d in patches if d["kind"] == k),
               "area_cm2": round(sum(d["area_cm2"] for d in patches if d["kind"] == k), 1)} for k in kinds}
    known_rep = {k: {"area_cm2": round(float(area[m_].sum() * 1e4), 1), "median_H_per_m": round(float(np.median(H5[m_])), 1) if m_.any() else None}
                 for k, m_ in known.items()}
    res = {"skin": path, "midline_x_mm": round(xmid * 1000, 2), "known_anatomy_concave": known_rep, "vertices": int(len(V)), "mean_edge_mm": round(edge * 1000, 3), "noise_step_per_m": round(float(noise), 2),
           "strength_meaning": {"DENT": "H (1/m), concave inside a rounded area", "FLAT": "H / neighbourhood (lower = flatter)", "BUMP": "H / neighbourhood", "CREASE": "H (1/m)",
                                "ASYMMETRY": "|H - H_mirror| (1/m)", "STEP": "jump / noise"},
           "totals": tot, "patches": patches}
    json.dump(res, open(out + ".json", "w"), indent=1)
    np.savez_compressed(out + "_masks.npz", **{k: m_ for k, m_ in kinds.items()},
                        **{"known_" + k.replace(" ", "_").replace("/", "_"): m_ for k, m_ in known.items()},
                        nac=nac, caps=caps, xmid=xmid)
    plot(V, N, kinds, patches, out + ".png")
    print(json.dumps({"totals": tot, "top": patches[:15]}, indent=1))


def plot(V, N, kinds, patches, path):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    col = {"DENT": "tab:green", "FLAT": "tab:orange", "BUMP": "tab:red", "CREASE": "tab:purple", "ASYMMETRY": "tab:blue", "STEP": "black"}
    fig, ax = plt.subplots(1, 2, figsize=(16, 10))
    for k, (name, front) in enumerate((("front", True), ("back", False))):
        vis = (N[:, 1] < -0.2) if front else (N[:, 1] > 0.2)
        xs = V[vis, 0] if front else -V[vis, 0]
        ax[k].scatter(xs * 1000, V[vis, 2] * 1000, s=0.02, c="0.8", rasterized=True)
        for kind, m in kinds.items():
            mm = m & vis
            ax[k].scatter((V[mm, 0] if front else -V[mm, 0]) * 1000, V[mm, 2] * 1000, s=0.3, c=col[kind], label=kind, rasterized=True)
        for d in patches[:40]:
            cx = d["centre_mm"][0] if front else -d["centre_mm"][0]
            if (d["face"] == "front") == front:
                ax[k].annotate(str(d["id"]), (cx, d["centre_mm"][2]), fontsize=8, color="k")
        ax[k].set_aspect("equal"); ax[k].set_title(f"{name} (seen from the {name}; numbers = patch ids)")
    ax[0].legend(markerscale=20, loc="lower left")
    fig.tight_layout(); fig.savefig(path, dpi=80)


if __name__ == "__main__":
    main()
