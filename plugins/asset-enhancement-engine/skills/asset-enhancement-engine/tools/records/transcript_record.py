# Moved from the session scratchpad (2026-10-19): keeps the person's math-method conversation verbatim (MATH_METHOD_RECORD.md).
"""Extract the person's messages (verbatim) and the assistant's replies (text only) from the session transcript,
from the math-concept message onward, into one markdown record."""
import json, re, sys
p = r"C:\Users\<you>\.claude\projects\<project-id>\4e1e86a0-3fb8-4e95-be51-ae522fcc2a80.jsonl"
out = sys.argv[1]
START = 2808
strip = lambda t: re.sub(r"<system-reminder>.*?</system-reminder>", "", t, flags=re.S).strip()
rows, bad = [], 0
for i, line in enumerate(open(p, encoding="utf-8")):
    if i < START: continue
    try: d = json.loads(line)
    except Exception: continue
    if d.get("isSidechain"): continue
    m = d.get("message", {}); c = m.get("content"); ts = d.get("timestamp", "")
    at = d.get("attachment") if d.get("type") == "attachment" else None
    if isinstance(at, dict) and at.get("type") == "queued_command" and isinstance(at.get("prompt"), str)             and (at.get("origin") or {}).get("kind") == "human":                 # agents' hand-backs are queued too
        rows.append(("THE PERSON (sent while Claude was working)", ts, strip(at["prompt"]))); continue
    if d.get("type") == "user":
        if isinstance(c, str): parts, imgs = [c], 0
        else:
            if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c): continue
            parts = [x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"]
            imgs = sum(1 for x in c if isinstance(x, dict) and x.get("type") == "image")
        t = strip("\n".join(parts))
        if not t or t.startswith("This session is being continued") or t.startswith("[Request interrupted"): continue
        rows.append(("THE PERSON", ts, t + (f"\n\n*[{imgs} image(s) attached]*" if imgs else "")))
    elif d.get("type") == "assistant" and isinstance(c, list):
        t = "\n".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text").strip()
        if t: rows.append(("CLAUDE", ts, t))
# merge consecutive assistant chunks
merged = []
for who, ts, t in rows:
    if merged and merged[-1][0] == who == "CLAUDE": merged[-1] = (who, merged[-1][1], merged[-1][2] + "\n\n" + t)
    else: merged.append((who, ts, t))
with open(out, "w", encoding="utf-8") as fh:
    fh.write("# The math method: the person's concept and everything that followed (verbatim record)\n\n"
             "Kept at the person's request (2026-10-19): \"Let's be sure we are fully retaining my message, the conversation, "
             "the decisions and tests and process, so we can actually build this process right\" and \"The message I wanted "
             "retained by the way was the one that originally spelled out the mathematical concept I had, and everything that "
             "followed\".\n\n"
             "Source: the session transcript (Claude Code session 4e1e86a0), extracted by script. The person's messages are "
             "verbatim; Claude's replies are its chat text, verbatim (tool calls and tool output left out; the work they did "
             "is in LOG.md, NOTES.md, TOOLMAKING.md and the v3/v4 folders). Characters shown as U+FFFD were already "
             "replaced in the transcript (curly quotes and apostrophes from the person's device).\n\n")
    for who, ts, t in merged:
        fh.write(f"---\n\n## {who} - {ts[:19].replace('T', ' ')} UTC\n\n{t}\n\n")
print(len(merged), "entries;", sum(t.count("\ufffd") for _, _, t in merged), "replacement chars")
