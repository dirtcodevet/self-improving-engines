"""Proof of build_log.py's output (build A2, 2026-10-21):  python engine/tools/test_build_log.py
 1. a missing log reads as empty ("no build log yet", exit 0), --init starts one, --list / --id / a search on it say so
 2. on the real log, for last night's six searches: the default output is a ranked list (id, score, title, keys) with the
    top entries whole (1 to 3, within 7,000 characters), at most 60 % of the old output (--full), every one of the old
    top 6 is in the list in the old order, the whole ones are the old first ones, --whole N gives exactly N, and --id
    prints entries whole (several ids at once, an unknown id said so)
Prints PASS / FAIL per check; exit 1 on any FAIL. Without a log (a fresh install) part 2 is skipped (2026-10-21)."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "build_log.py")
sys.path.insert(0, HERE)
import build_log as B

SIX = {
    "K1": "fold self-intersection inside-out crossing toes eye socket eyes remesh connectivity",
    "L4": "head face ear nose eye lips segmentation word list split",
    "13b": "rig weights scapula clavicle shoulder armpit topology loops pole skinning dual quaternion",
    "L5": "variance view translator relief colour",
    "13c": "corrective shape key pose armpit breast",
    "L5b": "variance sign mirror normals winding handedness",
}


def run(args, log=None):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if log:
        env["BUILD_LOG_FILE"] = log
    r = subprocess.run([sys.executable, TOOL] + args, capture_output=True, env=env)
    return r.returncode, r.stdout.decode("utf-8", "replace")


bad = []


def check(name, ok, note=""):
    print(("PASS " if ok else "FAIL ") + name + (("  " + note) if note else ""))
    if not ok:
        bad.append(name)


tmp = os.path.join(tempfile.mkdtemp(), "BUILD_LOG.md")
rc, out = run(["breast"], tmp); check("missing log: search reads as empty", rc == 0 and "no build log yet" in out)
rc, out = run(["--list"], tmp); check("missing log: --list reads as empty", rc == 0 and "no build log yet" in out)
rc, out = run(["--id", "x"], tmp); check("missing log: --id reads as empty", rc == 0 and "no build log yet" in out)
rc, out = run(["--init"], tmp); check("--init starts a log", rc == 0 and os.path.exists(tmp) and "started" in out)
rc, out = run(["--init"], tmp); check("--init does not overwrite", "already there" in out)
rc, out = run(["breast"], tmp); check("empty log: a search finds nothing and says so", rc == 0 and "no entry matches" in out)
open(tmp, "a", encoding="utf-8").write("\n## t1: a planted entry about breast cups (2026-10-21)\n- keys: breast, cup, planted\n- task: x\n")
rc, out = run(["cup"], tmp); check("a planted entry is found, whole", "## t1:" in out and "- task: x" in out and "1. t1" in out)

real = B.entries()
if not real:                                          # a fresh install (the public copy) ships no log: only part 1 runs
    print("SKIP part 2: no build log here (" + os.path.normpath(B.LOG) + ")")
    print("ALL PASS" if not bad else "FAILED: " + ", ".join(bad))
    sys.exit(1 if bad else 0)
check("real log: has entries", len(real) > 30, f"{len(real)} entries")
tot_old = tot_new = 0
for k, w in SIX.items():
    words = w.split()
    _, new = run(words); _, full = run(words + ["--full"])
    res = B.scored(words); ids = [e["id"] for sc, e in res]
    tot_old += len(full); tot_new += len(new)
    check(f"{k}: default output is at most 60 % of the old output", len(new) <= 0.6 * len(full), f"{len(new)} against {len(full)} characters")
    listed = [ln.split()[1] for ln in new.split("\n") if ln[:2].strip().isdigit() and ". " in ln[:5]]
    check(f"{k}: the old top 6 are all in the ranked list, in the old order", listed[:6] == ids[:6], f"{listed[:6]}")
    whole = [ln[3:].split(":")[0] for ln in new.split("\n") if ln.startswith("## ")]
    tw = sum(len(e["text"]) for sc, e in res[:len(whole)])
    check(f"{k}: the top entries are whole, 1 to 3, within 7,000 characters (or the first alone)", whole == ids[:len(whole)] and 1 <= len(whole) <= 3
          and (tw <= 7000 or len(whole) == 1), f"{whole}, {tw} characters")
    _, w2 = run(words + ["--whole", "2"])
    check(f"{k}: --whole 2 gives exactly two", [ln[3:].split(":")[0] for ln in w2.splitlines() if ln.startswith("## ")] == ids[:2])
    _, w0 = run(words + ["--whole", "0"]); check(f"{k}: --whole 0 prints the list only", "## " not in w0 and len(w0) < len(new))
check("six searches together", tot_new < 0.6 * tot_old, f"{tot_new} against {tot_old} characters")
a, b = real[3]["id"], real[7]["id"]
rc, out = run(["--id", a, b, "nope"]); check("--id: several ids whole, an unknown one said so",
                                              out.count("\n## ") + out.startswith("## ") == 2 and "no entry nope" in out)
rc, out = run(["--id", f"{a},{b}"]); check("--id: comma-separated ids too", out.count("\n## ") + out.startswith("## ") == 2)
print("ALL PASS" if not bad else "FAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
