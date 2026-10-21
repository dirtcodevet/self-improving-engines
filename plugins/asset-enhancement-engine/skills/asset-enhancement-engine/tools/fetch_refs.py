"""Polite downloader for a reference manifest (Wikimedia Commons): one file at a time, ~20 s apart, backing off on
HTTP 429 (honours Retry-After), ASCII filenames, each file verified against its stated byte size.
usage: python fetch_refs.py <manifest.json>   (run from the destination folder)"""
import json, os, sys, time, unicodedata, urllib.parse, urllib.request, urllib.error

UA = "CatEngineReference/1.0 (personal 3-D modelling reference; low request rate)"
rows = json.load(open(sys.argv[1]))
ascii_name = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().replace(" ", "_")
for r in rows:
    fn = f"{r['id'].zfill(2)}_" + ascii_name(urllib.parse.unquote(r['url'].rsplit('/', 1)[1]))
    old = r.get("file")
    if old and old != fn and os.path.exists(old) and os.path.getsize(old) == r["bytes"]:
        os.replace(old, fn)
    r["file"] = fn
    wait = 20
    while not (os.path.exists(fn) and os.path.getsize(fn) == r["bytes"]):
        try:
            req = urllib.request.Request(r["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as resp, open(fn + ".part", "wb") as f:
                f.write(resp.read())
            os.replace(fn + ".part", fn)
            print(f"{r['id']:>3} got {os.path.getsize(fn)} / {r['bytes']}", flush=True)
            time.sleep(20)
        except urllib.error.HTTPError as e:
            ra = e.headers.get("Retry-After")
            wait = max(int(ra) if ra and ra.isdigit() else 0, min(wait * 2, 600))
            print(f"{r['id']:>3} HTTP {e.code}, waiting {wait} s", flush=True)
            time.sleep(wait)
    r["size_ok"] = os.path.getsize(fn) == r["bytes"]
    json.dump(rows, open(sys.argv[1], "w"), indent=1)
print(f"done: {sum(r.get('size_ok', False) for r in rows)}/{len(rows)} files match their stated size", flush=True)
