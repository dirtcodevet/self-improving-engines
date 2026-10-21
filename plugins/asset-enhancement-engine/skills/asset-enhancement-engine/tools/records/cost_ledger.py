"""COST LEDGER (2026-10-19, the person: "make sure we measure the cost of each generation of each model too").

Measures, from the session transcripts themselves (never estimates), what a piece of work cost:
  tokens  - new tokens (input + cache writes + output: what the model had to read fresh or write) and cached re-reads
            (cache_read: the conversation re-read on every step, cheaper but the largest volume), per assistant message
            (streamed chunks share an id: the LAST usage of an id is its final count)
  time    - the window's wall-clock span; tool time (from each tool call to its result: compute, Blender, scripts);
            model time (from a tool result to the next assistant message: the model thinking and writing)
  agents  - every sub-agent whose transcript starts inside the window, with the same measures
Rows go to <ledger>.json and a table to <ledger>.md.

  python cost_ledger.py window <label> <start_iso> <end_iso> <ledger_base>      # the orchestrator + its agents in a window
  python cost_ledger.py agent <label> <agent_id> <ledger_base>                  # one agent's whole run (e.g. a rapid-shot builder)
"""
import glob, json, os, sys
from datetime import datetime

PROJ = r"C:\Users\<you>\.claude\projects\<project-id>"
SESSION = "4e1e86a0-3fb8-4e95-be51-ae522fcc2a80"
MAIN = os.path.join(PROJ, SESSION + ".jsonl")
SUB = os.path.join(PROJ, SESSION, "subagents")
ts = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))


def measure(path, t0=None, t1=None, skip_sidechain=True):
    usage, calls, tool_s, model_s, last_res, first, last = {}, {}, 0.0, 0.0, None, None, None
    for line in open(path, encoding="utf-8"):
        try: d = json.loads(line)
        except Exception: continue
        t = d.get("timestamp")
        if not t or (t0 and t < t0) or (t1 and t > t1): continue
        if skip_sidechain and d.get("isSidechain") and path == MAIN: continue
        first = first or t; last = t; tt = ts(t); m = d.get("message") or {}
        if d.get("type") == "assistant":
            mid = m.get("id")
            if mid and m.get("usage"): usage[mid] = m["usage"]
            if last_res is not None:
                model_s += max(0.0, (tt - last_res).total_seconds()); last_res = None
            for c in m.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use": calls[c["id"]] = tt
        elif d.get("type") == "user" and isinstance(m.get("content"), list):
            for c in m["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("tool_use_id") in calls:
                    tool_s += (tt - calls.pop(c["tool_use_id"])).total_seconds(); last_res = tt
    g = lambda k: sum(u.get(k, 0) or 0 for u in usage.values())
    inp, out, cw, cr = g("input_tokens"), g("output_tokens"), g("cache_creation_input_tokens"), g("cache_read_input_tokens")
    span = (ts(last) - ts(first)).total_seconds() if first else 0.0
    return {"messages": len(usage), "new_tokens": inp + cw + out, "output_tokens": out, "cache_writes": cw, "cache_reads": cr,
            "input_tokens": inp, "span_min": round(span / 60, 1), "tool_min": round(tool_s / 60, 1), "model_min": round(model_s / 60, 1),
            "first": first, "last": last}


def agents_in(t0, t1):
    rows = []
    for p in glob.glob(os.path.join(SUB, "agent-*.jsonl")):
        first = None
        for line in open(p, encoding="utf-8"):
            try: first = json.loads(line).get("timestamp")
            except Exception: continue
            if first: break
        if first and t0 <= first <= t1:
            aid = os.path.basename(p)[6:-6]; meta = os.path.join(SUB, "agent-%s.meta.json" % aid)
            desc = json.load(open(meta)).get("description", "") if os.path.exists(meta) else ""
            r = measure(p, skip_sidechain=False); r.update(agent=aid, description=desc); rows.append(r)
    return rows


def write(base, row):
    jp = base + ".json"; rows = json.load(open(jp)) if os.path.exists(jp) else []
    rows = [r for r in rows if r["label"] != row["label"]] + [row]
    json.dump(rows, open(jp, "w"), indent=1)
    with open(base + ".md", "w", encoding="utf-8") as fh:
        fh.write("# Cost of each generation (measured from the session transcripts; engine/tools/records/cost_ledger.py)\n\n"
                 "New tokens = input + cache writes + output (what was read fresh or written). Cached re-reads are the conversation "
                 "read again on every step. Times: span = wall clock; tool = scripts, Blender, compute; model = thinking and writing.\n\n"
                 "| generation | orchestrator new tokens | orchestrator cached re-reads | agents | agents' new tokens | agents' re-reads | "
                 "total new tokens | span min | tool min | model min |\n|---|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            o = r.get("orchestrator") or {}; a = r.get("agents", [])
            an = sum(x["new_tokens"] for x in a); ar = sum(x["cache_reads"] for x in a)
            fh.write("| %s | %s | %s | %d | %s | %s | %s | %s | %s | %s |\n" % (
                r["label"], f'{o.get("new_tokens", 0):,}', f'{o.get("cache_reads", 0):,}', len(a), f"{an:,}", f"{ar:,}",
                f'{o.get("new_tokens", 0) + an:,}', o.get("span_min", sum(x["span_min"] for x in a)),
                round(o.get("tool_min", 0) + sum(x["tool_min"] for x in a), 1), round(o.get("model_min", 0) + sum(x["model_min"] for x in a), 1)))
        fh.write("\nAgents per generation:\n\n")
        for r in rows:
            for x in r.get("agents", []):
                fh.write("- %s: %s (%s): new %s, re-reads %s, %s min (tool %s, model %s)\n" % (
                    r["label"], x.get("description", ""), x["agent"][:8], f'{x["new_tokens"]:,}', f'{x["cache_reads"]:,}',
                    x["span_min"], x["tool_min"], x["model_min"]))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "window":
        label, t0, t1, base = a[1:5]
        row = {"label": label, "window": [t0, t1], "orchestrator": measure(MAIN, t0, t1), "agents": agents_in(t0, t1)}
    else:
        label, aid, base = a[1:4]
        r = measure(os.path.join(SUB, "agent-%s.jsonl" % aid), skip_sidechain=False); r["agent"] = aid
        row = {"label": label, "orchestrator": None, "agents": [r]}
    write(base, row); print(json.dumps({"label": row["label"], "orchestrator_new": (row["orchestrator"] or {}).get("new_tokens"),
                                         "agents": [(x.get("description", "")[:40], x["new_tokens"], x["span_min"]) for x in row["agents"]]}))
