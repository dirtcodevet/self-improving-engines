"""Search the build log (engine/log/BUILD_LOG.md): which earlier builds did something like the task in hand.
    python engine/tools/build_log.py <word> [word ...]     the matching entries, best first, printed whole
    python engine/tools/build_log.py --list                every entry's id and title
    python engine/tools/build_log.py --id 13a3             one entry
    python engine/tools/build_log.py --init                start an empty log (its header and the entry shape)
Scoring: each query word (case-insensitive; a word matches a longer one: "fill" finds "match_fill") counts 3 on the
entry's keys line, 2 in its title and 1 anywhere else; entries with no match are left out. Made in build A1 (2026-10-21).
A missing log reads as empty (a fresh install has none until its first build); --init added 2026-10-21.
"""
import os
import re
import sys

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "log", "BUILD_LOG.md")


HEADER = """# Build log: one entry per build (search it before you start; add yours before you report)

A record of what happened, written by each builder when it finishes, with no approval needed. It is not a rule book:
lessons that are judgments go to `METHOD.md` as candidates.

Search: `python engine/tools/build_log.py <words>`; `--list` prints every id and title.

Entry shape (keep it to about a dozen lines; numbers measured where there is a measure, labelled estimate otherwise):

```
## <id>: <the task in plain words> (<date>)
- keys: subject, region, the tools and methods it used or made, the failure modes it met
- task: one line (brief: path)
- did: what was done, in order
- didn't work: what was tried -> what it gave
- worked: what was kept -> what it gave
- made / used: files and tools made (engine or case), engine tools used
- time, cost: span min (tool, model), new tokens
- open: what was left for the next build
- sources: brief, report
```
"""


def entries(path=LOG):
    if not os.path.exists(path):
        return []
    txt = open(path, encoding="utf-8").read()
    parts = re.split(r"(?m)^## ", txt)[1:]
    out = []
    for p in parts:
        head = p.split("\n", 1)[0]; body = "## " + p.rstrip() + "\n"
        m = re.match(r"([^:]+):\s*(.*)", head)
        keys = re.search(r"(?m)^- keys:(.*)$", p)
        if head.startswith("<"):                                         # the entry shape in the header
            continue
        out.append({"id": (m.group(1) if m else head).strip(), "title": (m.group(2) if m else "").strip(),
                    "keys": keys.group(1).lower() if keys else "", "text": body})
    return out


def search(words, path=LOG):
    words = [w.lower() for w in words if w.strip()]
    res = []
    for e in entries(path):
        low = e["text"].lower(); sc = 0
        for w in words:
            sc += 3 * e["keys"].count(w) + 2 * (e["id"] + " " + e["title"]).lower().count(w) + low.count(w)
        if sc:
            res.append((sc, e))
    return [e for sc, e in sorted(res, key=lambda t: -t[0])]


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__); sys.exit(0)
    if a[0] == "--init":
        if os.path.exists(LOG):
            print("already there: " + os.path.normpath(LOG))
        else:
            open(LOG, "w", encoding="utf-8").write(HEADER); print("started " + os.path.normpath(LOG))
        sys.exit(0)
    if not os.path.exists(LOG):
        print("no build log yet (" + os.path.normpath(LOG) + "); `build_log.py --init` starts one"); sys.exit(0)
    if a[0] == "--list":
        for e in entries():
            print(f"{e['id']}: {e['title']}")
    elif a[0] == "--id":
        hit = [e for e in entries() if e["id"].lower() == a[1].lower()]
        print(hit[0]["text"] if hit else f"no entry {a[1]}")
    else:
        hits = search(a)
        print(f"{len(hits)} entries match {a}; best first\n")
        for e in hits[:int(os.environ.get("BUILD_LOG_MAX", "6"))]:
            print(e["text"])
        if len(hits) > 6:
            print("more: " + ", ".join(e["id"] for e in hits[6:]))
