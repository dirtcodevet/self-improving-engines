"""Pick the view transform / look that best matches the photo's tonal distribution: for each candidate,
1-D search exposure, keep the lowest loss. Uses light_match's stats/render. usage: same args as light_match."""
import json, sys, os, importlib.util
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = sys.argv[:5] + ["0"]
spec = importlib.util.spec_from_file_location("lm", os.path.join(here, "light_match.py"))
lm = importlib.util.module_from_spec(spec); spec.loader.exec_module(lm)   # runs the 0-iteration pass, defines helpers
import subprocess
cands = [("AgX", "AgX - Medium High Contrast"), ("AgX", "AgX - High Contrast"), ("AgX", "AgX - Punchy"),
         ("Standard", "None"), ("Filmic", "High Contrast"), ("Filmic", "Very High Contrast")]
best = None
cfg = json.load(open(lm.out_p))
for vt, look in cands:
    subprocess.run([sys.executable, lm.BM, "code", f"import bpy; vs=bpy.context.scene.view_settings; vs.view_transform='{vt}'; vs.look='{look}'"], check=True, capture_output=True)
    lo, hi = -3.0, 1.5
    for _ in range(7):  # golden-ish bisection on exposure via 3-point compare
        m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        l1 = lm.loss(dict(cfg, exposure=m1))[0]; l2 = lm.loss(dict(cfg, exposure=m2))[0]
        if l1 < l2: hi = m2
        else: lo = m1
    e = (lo + hi) / 2
    l, s = lm.loss(dict(cfg, exposure=e))
    print(f"{vt:8s} {look:28s} exposure {e:+.2f} loss {l:7.1f} stats {s.round(1)}")
    if best is None or l < best[0]:
        best = (l, vt, look, e)
l, vt, look, e = best
cfg.update(exposure=e, view_transform=vt, look=look)
json.dump(cfg, open(lm.out_p, "w"), indent=1)
subprocess.run([sys.executable, lm.BM, "code", f"import bpy; vs=bpy.context.scene.view_settings; vs.view_transform='{vt}'; vs.look='{look}'; vs.exposure={e}"], check=True)
print("chosen", vt, look, round(e, 2), "loss", round(l, 1))
