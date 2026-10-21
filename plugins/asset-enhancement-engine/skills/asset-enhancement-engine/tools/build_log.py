"""Search the build log (engine/log/BUILD_LOG.md): which earlier builds did something like the task in hand.
    python engine/tools/build_log.py <word> [word ...]     a short ranked list, best first (id, score, title, keys), then
                                                           the top entries whole while they fit 7,000 characters (1 to 3)
        --whole N    exactly the top N entries whole (0: the list only)       --top N   list length (default 12)
        --full       the old output: the top 6 matches whole (BUILD_LOG_MAX=N changes the 6), the rest by id
    python engine/tools/build_log.py --id 13a3 L5 ...      those entries, whole (a brief names related builds by id)
    python engine/tools/build_log.py --list                every entry's id and title
    python engine/tools/build_log.py --init                start an empty log (its header and the entry shape)
Scoring: each query word (case-insensitive; a word matches a longer one: "fill" finds "match_fill") counts 3 on the
entry's keys line, 2 in its title and 1 anywhere else; entries with no match are left out. Made in build A1 (2026-10-21);
build A2 (2026-10-21) made the default output a ranked list with only the top entries whole, 1 to 3 within 7,000
characters (a search used to print 6 whole entries, 16-23k characters). A missing log reads as empty (a fresh install
has none until its first build); --init added 2026-10-21. BUILD_LOG_FILE=<path> reads another log (tests)."""
import os
import re
import sys

LOG = os.environ.get("BUILD_LOG_FILE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "log", "BUILD_LOG.md")
WHOLE_MAX = 3                                                             # entries printed whole by default: at most this many,
WHOLE_CHARS = 7000                                                        # while together within this (the first is always printed)
TOP = 12                                                                  # ranked-list length by default
KEYS_MAX = 140                                                            # characters of an entry's keys shown in the list


HEADER = """# Build log: one entry per build (search it before you start; add yours before you report)

A record of what happened, written by each builder when it finishes, with no approval needed. It is not a rule book:
lessons that are judgments go to `METHOD.md` as candidates.

Search: `python engine/tools/build_log.py <words>` (a short ranked list, the top entries whole); `--id <id> [id ...]`
prints entries whole; `--list` prints every id and title.

Entry shape (keep it to about a dozen lines; numbers measured where there is a measure, labelled estimate otherwise):

```
## <id>: <the task in plain words> (<date>)
- keys: subject, region, the tools and methods it used or made, the failure modes it met
- task: one line (brief: path)
- did: what was done, in order
- didn't work: what was tried -> what it gave
- worked: what was kept -> what it gave
- made / used: files and tools made (engine or case), engine tools used
- time, cost: span min (tool, model), new tokens (COSTS.md); where the time went if it was lost
- open: what was left for the next build
- sources: brief, report, agent id
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
                    "keys": keys.group(1).lower() if keys else "", "keys_raw": keys.group(1).strip() if keys else "",
                    "text": body})
    return out


def scored(words, path=LOG):
    """[(score, entry)] best first; entries with no match are left out"""
    words = [w.lower() for w in words if w.strip()]
    res = []
    for e in entries(path):
        low = e["text"].lower(); sc = 0
        for w in words:
            sc += 3 * e["keys"].count(w) + 2 * (e["id"] + " " + e["title"]).lower().count(w) + low.count(w)
        if sc:
            res.append((sc, e))
    return sorted(res, key=lambda t: -t[0])


def search(words, path=LOG):
    return [e for sc, e in scored(words, path)]


def keys_line(e, words, width=KEYS_MAX):
    """the entry's keys, those that hold a query word first (they say why it matched), cut at a key boundary"""
    ks = [k.strip() for k in e["keys_raw"].split(",") if k.strip()]
    w = [x.lower() for x in words if x.strip()]
    ks = [k for k in ks if any(x in k.lower() for x in w)] + [k for k in ks if not any(x in k.lower() for x in w)]
    out = ""
    for i, k in enumerate(ks):
        nxt = k if not out else out + ", " + k
        if len(nxt) > width and out:
            return out + ", ... (+%d)" % (len(ks) - i)
        out = nxt
    return out[:width + 20]


def ranked(res, words, top=TOP):
    lines = []
    for i, (sc, e) in enumerate(res[:top], 1):
        lines.append(f"{i:2d}. {e['id']}  [{sc}]  {e['title']}")
        lines.append(f"      keys: {keys_line(e, words)}")
    return "\n".join(lines)


def whole_entries(res, n=None):
    """the entries printed whole: the top n if n is given, else the top ones while together within WHOLE_CHARS (1 to WHOLE_MAX)"""
    if n is not None:
        return [e for sc, e in res[:max(0, n)]]
    out, tot = [], 0
    for sc, e in res[:WHOLE_MAX]:
        if out and tot + len(e["text"]) > WHOLE_CHARS:
            break
        out.append(e); tot += len(e["text"])
    return out


def _flag(a, name, default):
    """pop `name N` from the argument list; the number, or the default"""
    if name in a:
        i = a.index(name)
        try:
            n = int(a[i + 1]); del a[i:i + 2]; return n
        except (IndexError, ValueError):
            del a[i:i + 1]; return default
    return default


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
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
        ids = [x for w in a[1:] for x in w.split(",") if x.strip()]
        allx = entries()
        for i in ids:
            hit = [e for e in allx if e["id"].lower() == i.lower()]
            print(hit[0]["text"] if hit else f"no entry {i}")
    else:
        full = "--full" in a
        if full:
            a.remove("--full")
        whole = _flag(a, "--whole", None); top = _flag(a, "--top", TOP)
        res = scored(a)
        if full:                                                          # the pre-A2 output
            print(f"{len(res)} entries match {a}; best first\n")
            n = int(os.environ.get("BUILD_LOG_MAX", "6"))
            for sc, e in res[:n]:
                print(e["text"])
            if len(res) > n:
                print("more: " + ", ".join(e["id"] for sc, e in res[n:]))
        elif not res:
            print(f"no entry matches {a}; `--list` prints every id and title")
        else:
            shown = whole_entries(res, whole)
            print(f"{len(res)} entries match {a}; best first, [score] after the id"
                  + (f"; the top {len(shown)} whole after the list" if shown else "")
                  + ". `--id <id> [id ...]` prints any entry whole, `--full` the old output (top 6 whole)\n")
            print(ranked(res, a, top))
            if len(res) > top:
                print("more: " + ", ".join(e["id"] for sc, e in res[top:]))
            if shown:
                print(f"\n---- the top {len(shown)} whole ----\n")
                for e in shown:
                    print(e["text"])
