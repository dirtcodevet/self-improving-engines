#!/usr/bin/env python3
"""Refresh the packaged skill copies from the project (copies only; the originals are never touched).

Why (2026-10-21): the project keeps changing, and the repo publishes only part of it: the skills, the tools and the
foundation, not the case work, sample models and run logs (`tools/publish_rules.json` says which). This mirrors each
packaged folder onto its project source under those rules: new and changed files are copied, and files that left
the project or that the rules now exclude are removed from the copy. Then run `verify_copies.py --write` to record
the snapshot, and regenerate `plugins/<engine>/BINARIES.md` from the report this prints. Text files are published
with the rules' rewrites applied (`publish_bytes`), so a copy can differ from its original by exactly those.

usage:
  python tools/refresh_copies.py --project "<path to the project folder>"          # show what would change
  python tools/refresh_copies.py --project "<path to the project folder>" --apply  # change the copies
"""
import argparse
import hashlib
import json
import shutil
from fnmatch import fnmatch
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES = json.loads((REPO / "tools" / "publish_rules.json").read_text(encoding="utf-8"))


def skipped(rel):
    return any(fnmatch(part, pat) for part in rel.split("/") for pat in RULES["skip_everywhere"])


def published(rel, copy):
    """True when the rules publish this project-relative path (posix, relative to copy['project'])."""
    if skipped(rel):
        return False
    if any(fnmatch(rel, pat) for pat in copy["keep"]):
        return True
    return not any(fnmatch(rel, pat) for pat in copy["exclude"])


def files(root, keep=lambda rel: True):
    out = {}
    if root.is_dir():
        for p in root.rglob("*"):
            if p.is_file():
                rel = p.relative_to(root).as_posix()
                if keep(rel):
                    out[rel] = p
    return out


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


LOCAL = REPO / "tools" / "publish_rewrites.local.json"   # personal rewrites; git ignores it (publish_rules.json)


def rewrites():
    """The personal rewrites first (the local file, never committed), then the rules' own. A missing local file stops
    the tool: publishing without it would put the strings it hides into the copies."""
    if not LOCAL.is_file():
        raise SystemExit(f"missing {LOCAL.relative_to(REPO)}: the personal rewrites must be applied before publishing")
    return json.loads(LOCAL.read_text(encoding="utf-8"))["rewrite"] + RULES.get("rewrite", [])


def publish_bytes(p):
    """The bytes the repo publishes for project file p: text files get the rewrites (personal paths, the maintainer's
    other project, the engine's public name), applied in order; everything else is copied as is."""
    b = p.read_bytes()
    if p.suffix.lower() not in RULES.get("text_files", []):
        return b
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        return b
    for r in rewrites():
        s = s.replace(r["find"], r["replace"])
    return s.encode("utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    project = Path(a.project)
    report = {}
    for copy in RULES["copies"]:
        src_root, dst_root = project / copy["project"], REPO / copy["repo"]
        s = files(src_root, lambda rel: published(rel, copy))
        d = files(dst_root)
        added = sorted(r for r in s if r not in d)
        removed = sorted(r for r in d if r not in s)
        changed = sorted(r for r in s if r in d and publish_bytes(s[r]) != d[r].read_bytes())
        if a.apply:
            for r in added + changed:
                t = dst_root / r
                t.parent.mkdir(parents=True, exist_ok=True)
                t.write_bytes(publish_bytes(s[r]))
                shutil.copystat(s[r], t)
            for r in removed:
                (dst_root / r).unlink()
            for p in sorted(dst_root.rglob("*"), reverse=True):     # folders the removals emptied
                if p.is_dir() and not any(p.iterdir()):
                    p.rmdir()
        report[copy["repo"]] = dict(added=len(added), changed=len(changed), removed=len(removed),
                                    added_sample=added[:10], removed_sample=removed[:10])
    print(json.dumps(report, indent=1))
    if not a.apply:
        print("(dry run: nothing changed; add --apply)")


if __name__ == "__main__":
    main()
