"""class_template_fetch.py - fetch the human CLASS template (MakeHuman base mesh + body targets).

Stdlib only. Downloads from the official makehumancommunity/makehuman GitHub repo at a PINNED
commit, selects only the base mesh, the modifier definitions and the body-shape targets a
torso/arms/back fit needs, and proves every file twice:
  1. its git blob SHA-1 (sha1(b"blob <len>\\0" + bytes)) must equal the SHA in the repo tree
     listing for that commit (so the bytes are exactly what the repo holds), and
  2. its sha256 is recorded in manifest.json for later re-verification.

Usage (run from anywhere, with -I):
  python -I class_template_fetch.py --dest <empty dir> [--commit <sha>] [--dry-run]

The selection rule is data (SELECT below), so a different subject class can widen it later.
"""
import argparse, concurrent.futures as cf, hashlib, json, os, re, sys, time, urllib.request

OWNER_REPO = "makehumancommunity/makehuman"
TAG = "v1.3.0"
COMMIT = "1f508f6083b2f823dab15de924b3bde72e08d77c"   # tag v1.3.0 (resolved via GitHub API 2026-10-18)
API = "https://api.github.com/repos/" + OWNER_REPO
RAW = "https://raw.githubusercontent.com/" + OWNER_REPO + "/{commit}/{path}"

LICENCE_FILES = ["LICENSE.md", "LICENSE.ASSETS.md"]
MESH_FILES = ["makehuman/data/3dobjs/base.obj"]
MODIFIER_FILES = ["makehuman/data/modifiers/" + n for n in (
    "modeling_modifiers.json", "modeling_modifiers_desc.json",
    "measurement_modifiers.json", "measurement_modifiers_desc.json",
    "bodyshapes_modifiers.json", "bodyshapes_modifiers_desc.json")]

# Body-shape targets for a torso + arms + back fit. Paths are relative to makehuman/data/targets.
# Each rule: (folder regex, filename-keep regex, filename-drop regex or None)
SELECT = [
    (r"^macrodetails$",             r"\.target$", r"-baby"),   # gender/age/muscle/weight + ethnic
    (r"^macrodetails/height$",      r"\.target$", r"-baby-"),
    (r"^macrodetails/proportions$", r"\.target$", r"-baby-"),
    (r"^breast$",                   r"\.target$", None),
    (r"^torso$",                    r"\.target$", None),
    (r"^hip$",                      r"\.target$", None),
    (r"^stomach$",                  r"\.target$", None),
    (r"^buttocks$",                 r"\.target$", None),
    (r"^pelvis$",                   r"\.target$", None),
    (r"^neck$",                     r"\.target$", None),
    (r"^bodyshapes$",               r"\.target$", None),
    (r"^armslegs$", r"^[lr]-(upperarm|lowerarm|upperleg-(fat|muscle|scale))|^[lr]-hand-(scale|trans)", None),
    (r"^measure$", r"measure-(bust|underbust|waist|hips|frontchest|napetowaist|waisttohip|shoulder|neck|"
                   r"upperarm|lowerarm|wrist|thigh)-", None),
]


def get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "class-template-fetch"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def git_blob_sha1(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def listing(commit):
    """{repo path: (git blob sha, size)} for the files this tool may select."""
    out = {}
    top = get_json(API + "/contents/?ref=" + commit)
    for e in top:
        if e["type"] == "file":
            out[e["path"]] = (e["sha"], e["size"])
    data = {e["name"]: e["sha"] for e in get_json(API + "/contents/makehuman/data?ref=" + commit)}
    for sub in ("3dobjs", "modifiers", "targets"):
        t = get_json(API + "/git/trees/%s?recursive=1" % data[sub])
        if t.get("truncated"):
            raise SystemExit("tree listing truncated for " + sub)
        for e in t["tree"]:
            if e["type"] == "blob":
                out["makehuman/data/%s/%s" % (sub, e["path"])] = (e["sha"], e["size"])
    return out


def select(lst):
    keep = list(LICENCE_FILES) + MESH_FILES + MODIFIER_FILES
    pre = "makehuman/data/targets/"
    for p in sorted(lst):
        if not p.startswith(pre):
            continue
        rel = p[len(pre):]
        folder, name = rel.rsplit("/", 1) if "/" in rel else ("", rel)
        for fre, kre, dre in SELECT:
            if re.search(fre, folder) and re.search(kre, name) and not (dre and re.search(dre, name)):
                keep.append(p)
                break
    missing = [p for p in keep if p not in lst]
    if missing:
        raise SystemExit("not in listing: %s" % missing)
    return keep


def local_name(p):
    if p.startswith("makehuman/data/"):
        return p[len("makehuman/data/"):]
    return p


def fetch_one(commit, p, want_sha, dest):
    url = RAW.format(commit=commit, path=p)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "class-template-fetch"}),
                                        timeout=120) as r:
                b = r.read()
            break
        except Exception as ex:   # transient network errors: retry, then fail loudly
            if attempt == 2:
                raise
            time.sleep(2)
    got = git_blob_sha1(b)
    if got != want_sha:
        raise RuntimeError("git blob sha mismatch %s: %s != %s" % (p, got, want_sha))
    out = os.path.join(dest, *local_name(p).split("/"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as f:
        f.write(b)
    return {"repo_path": p, "local": local_name(p), "bytes": len(b), "git_blob_sha1": got,
            "sha256": hashlib.sha256(b).hexdigest(), "url": url}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    ap.add_argument("--commit", default=COMMIT)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    lst = listing(a.commit)
    keep = select(lst)
    total = sum(lst[p][1] for p in keep)
    print("selected %d files, %.1f MB" % (len(keep), total / 1e6))
    if a.dry_run:
        for p in keep:
            print(p, lst[p][1])
        return
    if os.path.isdir(a.dest) and os.listdir(a.dest):
        raise SystemExit("dest not empty: " + a.dest)
    os.makedirs(a.dest, exist_ok=True)
    rows = []
    with cf.ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(fetch_one, a.commit, p, lst[p][0], a.dest) for p in keep]
        for f in cf.as_completed(futs):
            rows.append(f.result())
    rows.sort(key=lambda r: r["repo_path"])
    man = {"repo": "https://github.com/" + OWNER_REPO, "tag": TAG, "commit": a.commit,
           "fetched_unix": int(time.time()), "n_files": len(rows),
           "bytes": sum(r["bytes"] for r in rows),
           "proof": "every file's git blob SHA-1 equals the repo tree listing at this commit",
           "select_rules": SELECT, "files": rows}
    with open(os.path.join(a.dest, "manifest.json"), "w") as f:
        json.dump(man, f, indent=1)
    print("fetched %d files, %.1f MB, all git-blob verified, %.0f s" % (len(rows), man["bytes"] / 1e6, time.time() - t0))


if __name__ == "__main__":
    main()
