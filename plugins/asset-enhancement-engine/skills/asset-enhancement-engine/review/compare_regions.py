"""Region COLOUR and TEXTURE: photo vs model render (same frozen camera/frame). Regions are placed from the
builder's photo points/traces and used identically on both images. Per region: mean CIELAB and dE (CIE76),
lightness contrast (std L), fine texture (mean gradient magnitude of L: fur strands / leather grain), and fur-flow
coherence + dominant orientation (structure tensor). Each OFF line is a finding.
usage: python compare_regions.py <case_dir> <model_render.png> [out_prefix]
"""
import json
import os
import sys

import cv2
import numpy as np

case, rimg = sys.argv[1], sys.argv[2]
outp = sys.argv[3] if len(sys.argv) > 3 else os.path.join(case, "review", os.path.splitext(os.path.basename(rimg))[0] + "_regions")
P = json.load(open(os.path.join(case, "ref_points.json")))["points"]
F = json.load(open(os.path.join(case, "review", "photo_features.json")))["features"]
ph, md = cv2.imread(os.path.join(case, "ref.jpg")), cv2.imread(rimg)
mask = cv2.imread(os.path.join(case, "ref_mask.png"), 0) > 127
eR, eL, nose, chin = (np.array(P[k], float) for k in ("eye.R", "eye.L", "nose", "chin"))
iod = eL[0] - eR[0]                                     # inter-ocular distance: the face's own scale


def box(cx, cy, w, h):
    return int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2)


R = {
    "forehead":  box((eR[0] + eL[0]) / 2, eR[1] - 0.75 * iod, 1.1 * iod, 0.55 * iod),
    "cheek.R":   box(eR[0] - 0.25 * iod, eR[1] + 0.55 * iod, 0.45 * iod, 0.4 * iod),
    "cheek.L":   box(eL[0] + 0.25 * iod, eL[1] + 0.55 * iod, 0.45 * iod, 0.4 * iod),
    "muzzle.R":  box(nose[0] - 0.3 * iod, nose[1] + 0.25 * iod, 0.3 * iod, 0.3 * iod),
    "muzzle.L":  box(nose[0] + 0.3 * iod, nose[1] + 0.25 * iod, 0.3 * iod, 0.3 * iod),
    "chin":      box(chin[0], chin[1] + 0.2 * iod, 0.4 * iod, 0.25 * iod),
    "chest":     box(nose[0] + 0.1 * iod, chin[1] + 1.6 * iod, 1.2 * iod, 0.9 * iod),
    "leg.fR":    box(P["fpaw.R"][0], P["fpaw.R"][1] - 1.2 * iod, 0.35 * iod, 0.8 * iod),
    "leg.fL":    box(P["fpaw.L"][0], P["fpaw.L"][1] - 1.2 * iod, 0.35 * iod, 0.8 * iod),
}
polys = {"nose_leather": F.get("nose"), "ear_in.R": F.get("ear_in.R"), "ear_in.L": F.get("ear_in.L")}


def stats(img, sel):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = lab[..., 0] * 100 / 255
    g = cv2.GaussianBlur(L, (3, 3), 0.8)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    # fur flow from hair-scale detail only (v37c): markings and broad shading out, as in tools/photo_flow.py
    band = g - cv2.GaussianBlur(L, (0, 0), 2.5)
    bx, by = cv2.Sobel(band, cv2.CV_32F, 1, 0), cv2.Sobel(band, cv2.CV_32F, 0, 1)
    jxx, jyy, jxy = (cv2.GaussianBlur(t, (9, 9), 3)[sel] for t in (bx * bx, by * by, bx * by))
    Jxx, Jyy, Jxy = jxx.mean(), jyy.mean(), jxy.mean()
    lam = np.sqrt((Jxx - Jyy) ** 2 + 4 * Jxy ** 2)
    coh = lam / max(Jxx + Jyy, 1e-9)
    orient = 0.5 * np.degrees(np.arctan2(2 * Jxy, Jxx - Jyy))        # gradient orientation; fur runs across it
    return {"L": float(L[sel].mean()), "a": float(lab[..., 1][sel].mean() - 128), "b": float(lab[..., 2][sel].mean() - 128),
            "contrast": float(L[sel].std()), "texture": float(np.hypot(gx, gy)[sel].mean()), "flow_coh": float(coh),
            "flow_deg": float((orient + 90) % 180)}


rows = []
H, W = ph.shape[:2]
for name in list(R) + list(polys):
    sel = np.zeros((H, W), bool)
    if name in R:
        x0, y0, x1, y1 = R[name]; sel[max(y0, 0):y1, max(x0, 0):x1] = True; sel &= mask
    else:
        pts = polys[name]
        if not pts:
            continue
        m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.array(pts, np.int32)], 1); sel = m > 0
    if sel.sum() < 30:
        continue
    a, b = stats(ph, sel), stats(md, sel)
    dE = float(np.sqrt((a["L"] - b["L"]) ** 2 + (a["a"] - b["a"]) ** 2 + (a["b"] - b["b"]) ** 2))
    tex = (b["texture"] - a["texture"]) / max(a["texture"], 1e-9)
    con = (b["contrast"] - a["contrast"]) / max(a["contrast"], 1e-9)
    dflow = abs(((b["flow_deg"] - a["flow_deg"]) + 90) % 180 - 90)
    verdict = []
    if dE > 6: verdict.append(f"colour dE {dE:.0f}")
    if abs(tex) > 0.35: verdict.append(f"texture {tex*100:+.0f}%")
    if abs(con) > 0.4: verdict.append(f"contrast {con*100:+.0f}%")
    if a["flow_coh"] > 0.25 and b["flow_coh"] < 0.12:                 # a direction only means something if it exists
        verdict.append(f"no visible fur flow (coherence {b['flow_coh']:.2f} vs photo {a['flow_coh']:.2f})")
    elif a["flow_coh"] > 0.25 and dflow > 25: verdict.append(f"fur flow {dflow:.0f} deg off")
    rows.append((name, a, b, dE, tex, con, dflow, verdict))
lines = [f"{'region':13s} {'photo Lab':>18s} {'model Lab':>18s} {'dE':>5s} {'texture':>8s} {'contrast':>8s} {'flow':>5s}  verdict"]
for name, a, b, dE, tex, con, dflow, v in rows:
    lines.append(f"{name:13s} {a['L']:5.0f}/{a['a']:+5.1f}/{a['b']:+5.1f}  {b['L']:5.0f}/{b['a']:+5.1f}/{b['b']:+5.1f} {dE:5.1f} "
                 f"{tex*100:+7.0f}% {con*100:+7.0f}% {dflow:5.0f}  {'; '.join(v) if v else 'ok'}")
txt = "\n".join(lines) + f"\n\n{sum(1 for r in rows if r[7])} of {len(rows)} regions with findings"
open(outp + ".txt", "w").write(txt)
print(txt)
ov = np.hstack([ph, md])
for name in R:
    x0, y0, x1, y1 = R[name]
    for off in (0, W):
        cv2.rectangle(ov, (x0 + off, y0), (x1 + off, y1), (0, 200, 255), 2)
        cv2.putText(ov, name, (x0 + off, y0 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1, cv2.LINE_AA)
cv2.imwrite(outp + ".png", cv2.resize(ov, None, fx=0.5, fy=0.5))
