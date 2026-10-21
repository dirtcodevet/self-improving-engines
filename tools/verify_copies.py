#!/usr/bin/env python3
"""Prove the packaged files are byte-identical copies of the project originals, and show what changed since.

Why (2026-10-18): the repo packages COPIES of skills and an engine that are still changing in the project folder,
and the lessons assessment will decide what goes in. Two questions come up every time: "is the packaged file
still exactly the original?" and "what changed in the project since the snapshot?". This answers both from
SOURCES.json (written by --write at snapshot time) without touching the originals (read-only).

usage:
  python tools/verify_copies.py --project "<path to the project folder>" --write   # record a snapshot
  python tools/verify_copies.py --project "<path to the project folder>"           # compare copies, project, record
Exit 1 if any copy differs from its recorded hash.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from refresh_copies import RULES, published, publish_bytes  # noqa: E402  (one definition of what is published)

# packaged folder (repo-relative) -> source folder (project-relative)
MAP = {c["repo"]: c["project"] for c in RULES["copies"]}
COPY = {c["repo"]: c for c in RULES["copies"]}
SKIP = {"__pycache__"}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def files(root):
    return sorted(p for p in root.rglob("*") if p.is_file() and not SKIP & set(p.parts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    project = Path(a.project)
    record_path = REPO / "SOURCES.json"
    if a.write:
        rec = {"_what": "sha256 of every packaged copy, the project-relative file it was copied from, and that "
                        "original's sha256 (they differ by the publish rules' rewrites only). Paths are relative; the "
                        "project folder itself is not recorded.", "files": {}}
        for dst, src in MAP.items():
            for f in files(REPO / dst):
                rel = f.relative_to(REPO / dst).as_posix()
                s = project / src / rel
                if s.is_file() and publish_bytes(s) != f.read_bytes():
                    print(f"NOT A CLEAN COPY {dst}/{rel} (differs from its original by more than the rewrites)")
                rec["files"][f"{dst}/{rel}"] = {"source": f"{src}/{rel}", "sha256": sha(f),
                                                "source_sha256": sha(s) if s.is_file() else None}
        record_path.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
        print(f"recorded {len(rec['files'])} files")
    rec = json.loads(record_path.read_text(encoding="utf-8"))["files"]
    bad = changed = missing = 0
    for dst, info in rec.items():
        copy, src = REPO / dst, project / info["source"]
        if not copy.is_file() or sha(copy) != info["sha256"]:
            bad += 1
            print(f"COPY CHANGED   {dst}")
        if not src.is_file():
            missing += 1
            print(f"SOURCE GONE    {info['source']}")
        elif sha(src) != info.get("source_sha256", info["sha256"]):
            changed += 1
            print(f"SOURCE CHANGED {info['source']} (project moved on since the snapshot)")
    known = {info["source"] for info in rec.values()}
    for dst, src in MAP.items():                       # only files the publish rules would take
        for f in files(project / src):
            rel = f.relative_to(project / src).as_posix()
            if published(rel, COPY[dst]) and f"{src}/{rel}" not in known:
                print(f"NEW IN PROJECT {src}/{rel}")
    print(f"{len(rec)} recorded: {bad} copies changed, {changed} sources changed, {missing} sources gone")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
