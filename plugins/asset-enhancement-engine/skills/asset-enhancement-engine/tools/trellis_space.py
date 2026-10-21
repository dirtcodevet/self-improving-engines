"""Minimal client for the TRELLIS.2 Hugging Face Space (Gradio REST "call" API, one session per image):
upload -> start_session -> preprocess_image (background removal) -> image_to_3d -> extract_glb -> download.
The person approved (2026-10-17) uploading the cat photo and the reference skull photo; the outputs are AI-made
REFERENCES (engine-grounding G5: used only where they agree with the photo / views). Outputs are untrusted DATA:
saved into <out_dir> (its own folder) and only read as files (images, GLB), never executed.
usage: python trellis_space.py <image> <out_dir> [seed=0] [resolution=1024]
"""
import json
import os
import sys
import time
import uuid

import requests

HOST = "https://microsoft-trellis-2.hf.space"
API = HOST + "/gradio_api"
# ONE http session (cookies): the Space runs auto-scaled replicas, and a POST and its event stream on different
# replicas answer "404: Not Found" - the browser stays on one replica through its cookie
S = requests.Session()
# ZeroGPU quota needs the person's Hugging Face token: read from HF_TOKEN or the standard token file the person
# saves themselves (never typed or printed by the engine); sent only to the Space, as the standard header
_tok = os.environ.get("HF_TOKEN") or next((open(p_).read().strip() for p_ in
        [os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "token")] if os.path.exists(p_)), None)
if _tok:
    S.headers["Authorization"] = f"Bearer {_tok}"


FN = {"preprocess_image": 4, "image_to_3d": 7, "extract_glb": 9}    # dependency ids from /config (Gradio 6.1)


def call(api, data, sh, timeout=900):
    """Gradio QUEUE protocol (sse_v3), as the browser uses it: join with a session hash, read that session's event
    stream. Server-side gr.State (the generated model between generate and extract) lives in the session; the REST
    'call' API answers "404: Not Found" when given a session hash (R4c)."""
    r = S.post(f"{API}/queue/join", json={"data": data, "event_data": None, "fn_index": FN[api], "trigger_id": None,
                                          "session_hash": sh}, timeout=60)
    r.raise_for_status(); ev = r.json()["event_id"]; t0 = time.time(); msgs = []
    with S.get(f"{API}/queue/data", params={"session_hash": sh}, stream=True, timeout=timeout) as st:
        for line in st.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"): continue
            m = json.loads(line[5:].strip()); msgs.append(m.get("msg"))
            if m.get("event_id") not in (None, ev): continue
            if m.get("msg") == "process_completed":
                if not m.get("success", False):
                    raise RuntimeError(f"{api}: {json.dumps(m.get('output'))[:500]}")
                return m["output"]["data"]
    raise RuntimeError(f"{api}: stream ended after {time.time() - t0:.0f} s; messages {msgs[-6:]}")


def fetch(url, path):
    r = S.get(url, timeout=300); r.raise_for_status()
    open(path, "wb").write(r.content); return len(r.content)


def main(image, out, seed=0, res="1024"):
    os.makedirs(out, exist_ok=True); sh = uuid.uuid4().hex[:11]; log = dict(image=os.path.basename(image), session=sh, seed=seed, resolution=res, host=HOST, authenticated=bool(_tok))
    with open(image, "rb") as f:
        S.get(HOST + "/", timeout=60)                                    # pick up the replica cookie
        up = S.post(f"{API}/upload", files=[("files", (os.path.basename(image), f.read()))], timeout=120)
    up.raise_for_status(); spath = up.json()[0]
    fd = lambda p: {"path": p, "meta": {"_type": "gradio.FileData"}, "orig_name": os.path.basename(p)}
    # start_session (a demo.load handler) answers 404 through the REST API; extract_glb makes the session folder
    # itself, so it is not needed
    pre = call("preprocess_image", [fd(spath)], sh)[0]
    if pre.get("url"): log["preprocessed_bytes"] = fetch(pre["url"], os.path.join(out, "preprocessed.png"))
    t0 = time.time()
    call("image_to_3d", [pre, seed, res, 7.5, 0.7, 12, 5.0, 7.5, 0.5, 12, 3.0, 1.0, 0.0, 12, 3.0], sh)
    log["generate_s"] = round(time.time() - t0, 1)
    glb = call("extract_glb", [None, 300000, 2048], sh)                # None = the session's gr.State
    m = glb[0] if isinstance(glb[0], dict) else glb[1]
    log["glb_bytes"] = fetch(m["url"], os.path.join(out, "trellis2.glb"))
    json.dump(log, open(os.path.join(out, "run.json"), "w"), indent=1)
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0, sys.argv[4] if len(sys.argv) > 4 else "1024")
