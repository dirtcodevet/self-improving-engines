"""Generate a 3D shape REFERENCE (measuring stick only, never the deliverable) from the case photo with
Hyper3D Rodin through the Blender MCP add-on (free-trial key), import it as <PREFIX>_Ref3D (hidden from render).
Uploads the photo to Hyper3D's servers - only run with the person's approval.

usage: python rodin_ref.py <photo> <mask.png> <name>
"""
import base64, io, json, os, sys, time
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bmcp import send  # noqa: E402

photo, mask_p, name = sys.argv[1:4]
im = Image.open(photo).convert("RGB")
m = np.asarray(Image.open(mask_p).convert("L")) > 127
ys, xs = np.nonzero(m)
pad = 60
box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, im.width), min(ys.max() + pad, im.height))
crop = im.crop(box)
buf = io.BytesIO(); crop.save(buf, "JPEG", quality=95)
b64 = base64.b64encode(buf.getvalue()).decode()
print("crop", box, crop.size, f"{len(buf.getvalue())/1e3:.0f} KB")

r = send("execute_code", {"code": "import bpy; s=bpy.context.scene; s.blendermcp_use_hyper3d=True; "
                                  "s.blendermcp_hyper3d_mode='MAIN_SITE'; s.blendermcp_hyper3d_api_key='vibecoding'; print('ok')"})
print("enable:", r.get("status"))
print("status:", send("get_hyper3d_status").get("result"))
job = send("create_rodin_job", {"images": [[".jpg", b64]]}, timeout=300)
print("job:", json.dumps(job)[:600])
res = job.get("result", {})
sub = (res.get("jobs") or {}).get("subscription_key")
uuid = res.get("uuid")
if not sub:
    sys.exit("no subscription key - job not created")
t0 = time.time()
while True:
    st = send("poll_rodin_job_status", {"subscription_key": sub}).get("result", {})
    lst = st.get("status_list", [])
    print(f"  {time.time()-t0:5.0f}s  {lst}", flush=True)
    if lst and all(s == "Done" for s in lst):
        break
    if any(s == "Failed" for s in lst) or time.time() - t0 > 900:
        sys.exit("rodin job failed/timeout")
    time.sleep(10)
imp = send("import_generated_asset", {"task_uuid": uuid, "name": name}, timeout=600)
print("import:", json.dumps(imp)[:800])
