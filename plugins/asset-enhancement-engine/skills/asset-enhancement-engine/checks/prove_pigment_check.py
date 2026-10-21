"""A10 proofs for pigment_check.py (checksB, Phase 2 C7), all ON THE PHOTO (no render of the model exists yet):
  P0 photo vs itself: every region dE00 = 0, extra blur 0 -> PASS
  P1 each region in turn shifted by exactly dE00 5 (L* moved, solved by bisection) -> that region FAILS reading ~5,
     the regions that do not overlap it PASS; +-1 step of the dE mark and the region box scale
  P2 the marking edges blurred (Gaussian 3 px, in a feathered band round the photo's own boundary) -> crispness FAILS;
     sizing: planted sigma 0.5 / 1 / 2 / 3 / 4 px -> read extra blur; sigma 1 must still PASS (render softness);
     +-1 step of the blur mark, profile half-length and edge-strength percentile at sigma 3
usage: python prove_pigment_check.py [case_dir] [out.json]
"""
import json
import os
import sys
import time

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000, lab2rgb

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pigment_check as PC  # noqa: E402

t0 = time.time()
CASE = sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else os.path.join(HERE, "..", "..", "cases", "cat1")
OUTP = next((a for a in sys.argv[1:] if a.endswith(".json")), None)
P, F, ph, mask = PC.load_case(CASE); OUT = {}; ALL = []


def ok(name, cond, msg):
    ALL.append(bool(cond)); print(f"{'PASS' if cond else 'FAIL'}  {name}: {msg}", flush=True); OUT[name] = {"ok": bool(cond), "msg": msg}


# P0
r = PC.check(CASE, ph.copy())
ok("P0 photo vs itself", r["status"] == "PASS" and max(x["dE00"] for x in r["regions"].values()) == 0 and r["crispness"]["extra_blur_sigma_px"] == 0,
   f"{len(r['regions'])} regions max dE00 {max(x['dE00'] for x in r['regions'].values())}; edges n={r['crispness']['n']} photo width {r['crispness']['photo_width_px']} px, extra blur {r['crispness']['extra_blur_sigma_px']}")

# P1
LAB = PC.lab(ph); R = PC.regions(P, F, mask)
for k, sel in R.items():
    mu = LAB[sel].mean(0); sgn = -1.0 if mu[0] > 50 else 1.0; lo_, hi_ = 0.0, 30.0
    for _ in range(50):
        mid = (lo_ + hi_) / 2; d = deltaE_ciede2000(mu[None], (mu + [sgn * mid, 0, 0])[None])[0]
        lo_, hi_ = (mid, hi_) if d < 5.0 else (lo_, mid)
    sh = LAB.copy(); sh[sel, 0] += sgn * lo_
    img = ph.copy(); rgb = np.clip(lab2rgb(sh[sel][None])[0], 0, 1); img[sel] = np.round(rgb[:, ::-1] * 255).astype(np.uint8)
    res = PC.check(CASE, img); rk = res["regions"][k]
    others = {j: x for j, x in res["regions"].items() if j != k and (R[j] & sel).sum() / R[j].sum() < 0.05}
    steps = []
    for kw in ({"de_mark": 2.5}, {"de_mark": 3.5}, {"region_scale": 0.9}, {"region_scale": 1.1}):
        q = PC.check(CASE, img, **kw)["regions"].get(k, {"status": "n/a", "dE00": None}); steps.append(f"{list(kw.items())[0][0]}={list(kw.items())[0][1]}:{q['status']} {q['dE00']}")
    good = rk["status"] == "FAIL" and abs(rk["dE00"] - 5.0) < 0.3 and all(x["status"] == "PASS" for x in others.values()) and all("FAIL" in s for s in steps)
    ok(f"P1 shift dE5 {k}", good, f"read {rk['dE00']} FAIL={rk['status'] == 'FAIL'} (L* {sgn * lo_:+.2f}); {len(others)} non-overlapping regions max dE00 "
       f"{max((x['dE00'] for x in others.values()), default=0):.3f} all PASS={all(x['status'] == 'PASS' for x in others.values())}; +-1 step: {', '.join(steps)}")

# P2
pts, nrm, bnd = PC.edge_samples(ph, mask, F, PC.marking_axis(CASE, ph, mask))
band = cv2.GaussianBlur((cv2.dilate(bnd.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0).astype(np.float32), (0, 0), 3)[..., None]
OUT["P2_edge_samples"] = int(len(pts)); sizing = {}
for sg in (0.5, 1.0, 2.0, 3.0, 4.0):
    bl = cv2.GaussianBlur(ph.astype(np.float32), (0, 0), sg); img = np.round(band * bl + (1 - band) * ph).astype(np.uint8)
    res = PC.check(CASE, img); c = res["crispness"]; sizing[sg] = (c["extra_blur_sigma_px"], c["status"], max(x["dE00"] for x in res["regions"].values()))
    if sg == 3.0:
        img3 = img
ok("P2 blurred marking edges sigma 3 FAIL", sizing[3.0][1] == "FAIL", f"extra blur read {sizing[3.0][0]} px (mark 1.5); region colour still max dE00 {sizing[3.0][2]:.2f}")
ok("P2 sigma 1 (render softness) PASSES", sizing[1.0][1] == "PASS", f"read {sizing[1.0][0]} px")
ok("P2 sizing: read tracks planted sigma (2-4 px within 0.6 px)", all(abs(sizing[s][0] - s) < 0.6 for s in (2.0, 3.0, 4.0)),
   " / ".join(f"{s}->{sizing[s][0]} {sizing[s][1]}" for s in sizing))
steps = []
for kw in ({"sig_mark": 1.0}, {"sig_mark": 2.0}, {"half": 10}, {"half": 14}, {"strength_pct": 60}, {"strength_pct": 80}):
    c = PC.check(CASE, img3, **kw)["crispness"]; c0 = PC.check(CASE, ph.copy(), **kw)["crispness"]
    steps.append((kw, c["status"], c["extra_blur_sigma_px"], c0["status"]))
ok("P2 +-1 step: sigma 3 FAILS and the photo PASSES at every step", all(s[1] == "FAIL" and s[3] == "PASS" for s in steps),
   ", ".join(f"{list(k.items())[0][0]}={list(k.items())[0][1]}:{s} {v}/self {s0}" for k, s, v, s0 in steps))
OUT["P2_sizing"] = {str(k): v for k, v in sizing.items()}
dbg = ph.copy(); dbg[bnd] = (0, 255, 255)
for (x, y), (nx, ny) in zip(pts.astype(int), nrm):
    cv2.line(dbg, (int(x - 12 * nx), int(y - 12 * ny)), (int(x + 12 * nx), int(y + 12 * ny)), (0, 0, 255), 1)
tmp = os.path.join(os.environ.get("TEMP", "."), "p2_checksB"); os.makedirs(tmp, exist_ok=True); cv2.imwrite(os.path.join(tmp, "pigment_edges.png"), dbg)
print(f"\n{'ALL PROOFS PASS' if all(ALL) else 'A PROOF FAILED'} ({sum(ALL)}/{len(ALL)}) in {time.time()-t0:.0f} s")
if OUTP:
    json.dump(OUT, open(OUTP, "w"), indent=1, default=str)
