"""TOKEN LEDGER: real token usage per piece of work, summed from the Claude Code transcripts (the person, 2026-10-18:
"log the amount of tokens we used on the original cat, then how many we used on the rock, and how many tokens it takes
for the next cat. The difference there matters to me.").

Reads every transcript of this project: the main session, its subagents (direct agents and workflow agents), and the
side sessions in the same project folder. Each assistant message carries usage {input_tokens, output_tokens,
cache_creation_input_tokens, cache_read_input_tokens}; a message id is counted once (a hard-linked or resumed copy of a
transcript must not double-count).

Attribution
  - a WORKFLOW's agents -> the workflow's name (from the scripts dir file name / journal 'launched' line) mapped to a
    project via WORKFLOW_PROJECT below;
  - a direct AGENT -> its description (meta.json) mapped by keyword;
  - a SIDE SESSION -> its first user prompt mapped by keyword;
  - the MAIN LOOP (the orchestrator) -> by time window (PHASES below). The main loop interleaves topics, so its split is
    an ESTIMATE; workflow/agent/side-session numbers are exact.
Totals
  - 'fresh' = input + output + cache_creation (tokens processed new); 'cache_read' is reported separately (cheap reuse of
    already-seen context). Both are shown; comparisons use the same definition every time.
usage: python token_ledger.py [--json out.json] [--md out.md]
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

MAIN = "b98bba0a-684a-41e1-ae73-906b9dc847fc"
# the workspace moved to <project> on 2026-10-18 (person's request); the app moved this
# session's transcripts to that project folder with it. PROJ = whichever folder holds the main session now; the others
# are scanned for side sessions (message ids are counted once, so overlap cannot double-count)
PROJS = [r"C:\Users\<you>\.claude\projects\<project-id>",
         r"C:\Users\<you>\.claude\projects\<project-id>"]
PROJ = next((p for p in PROJS if os.path.exists(os.path.join(p, MAIN + ".jsonl"))), PROJS[0])
EXTRA_PROJS = [p for p in PROJS if p != PROJ]
# workflow script-name prefix -> project
WORKFLOW_PROJECT = [
    (r"^phase2-", "cat"),
    (r"^lessons-", "skills"),
    (r"^cat-engine-report|^report-multipage", "cat_docs"),
    (r"^rock1", "rock"),
    (r"^blueprint-site|^film-", "site+film"),
    (r"^cat-v3", "cat_v3"),
    (r"^woman", "woman"),
]
AGENT_KEYWORDS = [(r"woman|torso", "woman"), (r"cat v3|cat-v3", "cat_v3"), (r"rock", "rock"), (r"site|cinetic|film|taste", "site+film"),
                  (r"review|measurement|reference|repo internals|3D AI", "cat"), (r"review the (ears|tail|eyes)|ears measuring|tail measuring|eyes measuring|mouth|skin|feature|cat", "cat"),
                  (r"site|cinetic|film|taste", "site+film"), (r"cat v3|cat-v3", "cat_v3"), (r"woman|torso", "woman")]
SIDE_KEYWORDS = [(r"paws|toes", "cat"), (r"\bears?\b", "cat"), (r"\btail\b", "cat"), (r"repo|marketplace|plugin|reporter", "repo")]
# main-loop windows (UTC). Local time is UTC-7.
PHASES = [
    ("cat (Phase 1 and earlier)", "2000-01-01T00:00:00Z", "2026-10-18T10:41:00Z", "cat"),
    ("cat (Phase 2)", "2026-10-18T10:41:00Z", "2026-10-18T14:20:00Z", "cat"),
    ("lessons, rock and site start", "2026-10-18T14:20:00Z", "2026-10-18T16:15:00Z", "mixed"),
    ("cat v3 onward", "2026-10-18T16:15:00Z", "2100-01-01T00:00:00Z", "cat_v3+"),
]
# runs whose script was relaunched from a copied path (name not recoverable from the scripts dir)
ID_NAMES = {"wf_eca7e759-b29": "blueprint-site-v2"}
# agents with no meta description (duplicate copies spawned by mid-run messages, LOG #91)
AGENT_IDS = {"a57468b22af592964": "cat", "a5b47b98a17716466": "cat", "a877235b0d7697b0d": "cat"}
KEYS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def usage_lines(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"usage"' not in line: continue
            try: d = json.loads(line)
            except Exception: continue
            m = d.get("message") or {}
            u = m.get("usage")
            if not u or m.get("role") not in (None, "assistant"): continue
            yield d.get("timestamp", ""), (m.get("id") or d.get("uuid")), u


def add(acc, u):
    for k in KEYS: acc[k] += int(u.get(k) or 0)


def first_prompt(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try: d = json.loads(line)
            except Exception: continue
            m = d.get("message") or {}
            if m.get("role") == "user":
                c = m.get("content")
                return (c if isinstance(c, str) else json.dumps(c))[:3000]
    return ""


def classify(text, table, default):
    for pat, name in table:
        if re.search(pat, text, re.I): return name
    return default


def main():
    seen = set()
    by = defaultdict(lambda: defaultdict(int))     # (project, item) -> usage
    def count(path, project, item, window=False):
        for ts, mid, u in usage_lines(path):
            if mid in seen: continue
            seen.add(mid)
            if window:
                for name, a, b, proj in PHASES:
                    if a <= ts < b: add(by[(proj, "main loop: " + name)], u); break
            else:
                add(by[(project, item)], u)
    sub = os.path.join(PROJ, MAIN, "subagents")
    # workflows
    names = {}
    for sd in glob.glob(os.path.join(os.path.dirname(PROJ), "*", MAIN, "workflows", "scripts", "*.js")):
        b = os.path.basename(sd); m = re.match(r"(.+)-(wf_[0-9a-f-]+)\.js$", b)
        if m: names[m.group(2)] = m.group(1)
    names.update(ID_NAMES)
    for wdir in glob.glob(os.path.join(sub, "workflows", "wf_*")):
        wid = os.path.basename(wdir); wname = names.get(wid, wid)
        proj = classify(wname, WORKFLOW_PROJECT, "other")
        for a in glob.glob(os.path.join(wdir, "agent-*.jsonl")): count(a, proj, "workflow: " + wname)
    # direct agents
    for a in glob.glob(os.path.join(sub, "agent-*.jsonl")):
        meta = a.replace(".jsonl", ".meta.json"); desc = ""
        if os.path.exists(meta):
            try: desc = json.load(open(meta, encoding="utf-8")).get("description", "")
            except Exception: pass
        aid = os.path.basename(a)[6:-6]
        count(a, AGENT_IDS.get(aid) or classify(desc, AGENT_KEYWORDS, "other"), "agent: " + (desc or os.path.basename(a)))
    # side sessions
    for pdir in [PROJ] + EXTRA_PROJS:
        for s in glob.glob(os.path.join(pdir, "*.jsonl")):
            sid = os.path.basename(s)[:-6]
            if sid == MAIN: continue
            fp = first_prompt(s); proj = classify(fp, SIDE_KEYWORDS, "other")
            count(s, proj, "side session: " + re.sub(r"\s+", " ", fp[:70]))
            for a in glob.glob(os.path.join(pdir, sid, "subagents", "**", "agent-*.jsonl"), recursive=True):
                count(a, proj, "side session agents: " + sid[:8])
    # main loop last (its windows)
    count(os.path.join(PROJ, MAIN + ".jsonl"), None, None, window=True)

    rows = []
    for (proj, item), u in by.items():
        fresh = u["input_tokens"] + u["output_tokens"] + u["cache_creation_input_tokens"]
        rows.append(dict(project=proj, item=item, fresh=fresh, output=u["output_tokens"], cache_read=u["cache_read_input_tokens"], **u))
    rows.sort(key=lambda r: (r["project"], -r["fresh"]))
    tot = defaultdict(lambda: defaultdict(int))
    for r in rows:
        for k in ("fresh", "output", "cache_read"): tot[r["project"]][k] += r[k]
    out = dict(generated_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), definition="fresh = input + output + cache_creation; cache_read separate",
               totals={k: dict(v) for k, v in tot.items()}, rows=rows)
    if "--json" in sys.argv: json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
    if "--md" in sys.argv:
        L = ["# Token ledger", "", f"Generated {out['generated_utc']} from the transcripts (engine/tools/token_ledger.py).",
             "", "**fresh** = input + output + cache creation (new tokens processed); **cache read** = re-used context (cheaper). Workflow, agent and side-session numbers are exact; the orchestrator's main loop is split by time window (an estimate).", "",
             "| Project | Fresh tokens | Output tokens | Cache read |", "|---|---:|---:|---:|"]
        for p, v in sorted(tot.items(), key=lambda kv: -kv[1]["fresh"]):
            L.append(f"| {p} | {v['fresh']:,} | {v['output']:,} | {v['cache_read']:,} |")
        L += ["", "<details><summary>Every item</summary>", "", "| Project | Item | Fresh | Output | Cache read |", "|---|---|---:|---:|---:|"]
        for r in rows: L.append(f"| {r['project']} | {r['item']} | {r['fresh']:,} | {r['output']:,} | {r['cache_read']:,} |")
        L += ["", "</details>", ""]
        open(sys.argv[sys.argv.index("--md") + 1], "w", encoding="utf-8").write("\n".join(L))
    for p, v in sorted(tot.items(), key=lambda kv: -kv[1]["fresh"]): print(f"{p:12s} fresh {v['fresh']:>14,}  output {v['output']:>12,}  cache_read {v['cache_read']:>15,}")


if __name__ == "__main__":
    main()
