"""Fit the trunk loft's cross-section model (superellipse exponents, haunch width scale, haunch widest-z offset)
against a 3D reference with the multi-view metrics, by small grid search at a coarse voxel. Station values stay
the measured ones; only the SHAPE MODEL between them is fitted (hand-tuning it overcorrected in v17c).

usage: python fit_section.py <case_dir> <ref.ply> [vox=0.002]
"""
import importlib.util, itertools, json, os, sys, tempfile
import numpy as np

case, ref_p = sys.argv[1], sys.argv[2]
vox = float(sys.argv[3]) if len(sys.argv) > 3 else 0.002
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "checks"))
import sdf_core  # noqa: E402
import multiview as mvm  # noqa: E402
from checks import read_ply  # noqa: E402

sp = importlib.util.spec_from_file_location("casespec", os.path.join(case, "spec.py"))
S = importlib.util.module_from_spec(sp); sp.loader.exec_module(S)
rv, rf = read_ply(ref_p)
T0 = {k: list(v) for k, v in S.TRUNK.items()}
haunch = [i for i, y in enumerate(T0["y"]) if 0.05 <= y <= 0.13]
tmp = tempfile.mkdtemp()
orig_loft = sdf_core.loft_y
results = []
for q_up, q_dn, wscale, dmid in itertools.product((2.0, 2.3), (2.0, 2.3, 2.6), (0.96, 1.0, 1.04), (0.0, -0.006)):
    T = {k: list(v) for k, v in T0.items()}
    for i in haunch:
        T["hw"][i] = T0["hw"][i] * wscale
        T["mid"][i] = T0["mid"][i] + dmid
    S.TRUNK = T

    def loft_patch(*a, q_up_=q_up, q_dn_=q_dn, **kw):
        kw["q_up"], kw["q_dn"] = q_up_, q_dn_
        return orig_loft(*a, **kw)
    S.loft_y = loft_patch
    out = os.path.join(tmp, "fit")
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        sdf_core.run(S.build, S.P, out, vox, *S.BOUNDS)
    mv, mf = read_ply(out + ".ply")
    L = json.load(open(out + "_landmarks.json"))["landmarks"]
    r = mvm.score(mv, mf, None, [], rv, rf, head=np.array(L["head"]))
    v = r["views"]
    trunk_iou = (v["side_L"]["iou"] + v["top"]["iou"] + v["back"]["iou"]) / 3
    sd = r["surface"]
    loss = (1 - trunk_iou) * 100 + 0.15 * (sd["bulge_cell_p90_mm"] + sd["dent_cell_p90_mm"]) + 0.3 * r["profiles"]["half_width_mae_mm"]
    results.append((loss, dict(q_up=q_up, q_dn=q_dn, wscale=wscale, dmid=dmid), round(trunk_iou, 4), sd["bulge_cell_p90_mm"], sd["dent_cell_p90_mm"]))
    print(f"q_up {q_up} q_dn {q_dn} w x{wscale} mid {dmid:+.3f} -> loss {loss:6.2f}  iou(side/top/back) {trunk_iou:.4f}  bulge {sd['bulge_cell_p90_mm']}  dent {sd['dent_cell_p90_mm']}", flush=True)
results.sort(key=lambda t: t[0])
print("BEST", json.dumps(results[0][1]), "loss", round(results[0][0], 2), "iou", results[0][2], "bulge/dent", results[0][3], results[0][4])
