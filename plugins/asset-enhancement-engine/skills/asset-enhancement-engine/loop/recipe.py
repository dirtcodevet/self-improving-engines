"""RECIPE RUNNER (2026-10-19, the person's rapid-shot plan): a model is never hand-patched; it is the replay of a recipe -
an ordered list of engine stages from a stored base - so "build a new torso from scratch" means running the whole recipe
again, and a fix counts only once it is a stage that replays.

recipe JSON: {"name", "base_pack", "stages": [{"name", "cmd": [...], "env": {...}, "out_pack", "report"}],
              "verify": {"blender", "script"}, "reference_pack": optional pack to compare the result with}
Each stage runs as its own process from the project root (so it starts clean and its time is its own); its stdout tail,
its time and its report path go into the run card; the last stage's out_pack is the result. Then the Blender sweep
(overlaps at every 5 deg and with the elbows bent, exact rebuild) runs on it, and the result's skin is compared with
the reference pack if one is given.
    python engine/loop/recipe.py <recipe.json> [--from <stage name>] [--only <stage name>] [--no-cache]

STAGE CACHE (2026-10-19, the person's D20 efficiency lever): a stage is skipped when nothing it depends on changed - its
command and settings, its code (its scripts and every module they import from the project, found by reading their
imports; the .json beside its scripts; the packs' .json data) and its input (the content of the previous stage's output,
or the base pack's for the first). A key file in <recipe dir>/cache/<stage>.json records that key and the hash of what
the stage wrote; the stage is skipped only when both still match, so an output changed by hand reruns its stage.
Inputs are hashed by content, so a rerun that writes the same output leaves later stages cached. `--no-cache` replays
every stage (a full fresh build: the queue's item 5 test). `--only` and `--from` run what they name, and refresh its key.
Writes <recipe dir>/runs/<timestamp>/card.json and prints the card.
"""
import ast, glob, hashlib, json, os, subprocess, sys, time
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def _sha_files(paths):
    h = hashlib.sha1()
    for p in sorted(set(paths)):
        h.update(os.path.relpath(p, ROOT).replace("\\", "/").encode())
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


def _dir_files(d):
    d = os.path.join(ROOT, d)
    return [os.path.join(d, fn) for fn in os.listdir(d) if os.path.isfile(os.path.join(d, fn))] if os.path.isdir(d) else []


def _project_imports(path, search, seen):
    """the project's own modules a script imports, recursively (name lookup in the search folders; anything not found
    there is the standard library or a third-party package and is not hashed)"""
    if path in seen:
        return
    seen.add(path)
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except (SyntaxError, UnicodeDecodeError):
        return
    mods = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            mods += [n.module] + [n.module + "." + a.name for a in n.names]
    for m in mods:
        rel = m.replace(".", os.sep)
        for d in [os.path.dirname(path)] + search:
            for c in (os.path.join(d, rel + ".py"), os.path.join(d, rel, "__init__.py")):
                if os.path.isfile(c):
                    _project_imports(c, search, seen)


def _code_hash(st, rdir):
    search = [os.path.join(ROOT, "engine"), os.path.join(ROOT, "engine", "loop"), os.path.join(ROOT, "engine", "tools")]
    search += [d for d in glob.glob(os.path.join(ROOT, "engine", "tools", "*")) if os.path.isdir(d)]
    case = os.path.dirname(rdir)                                   # the case's own folders (stage scripts import them)
    search += [d for d in glob.glob(os.path.join(case, "*")) if os.path.isdir(d)] + [os.path.join(rdir, "stages")]
    seen, data = set(), []
    for c in st["cmd"]:
        p = os.path.join(ROOT, c)
        if c.endswith(".py") and os.path.isfile(p):
            _project_imports(p, search, seen)
            data += glob.glob(os.path.join(os.path.dirname(p), "*.json"))
    data += [p for p in glob.glob(os.path.join(ROOT, "engine", "packs", "**", "*.json"), recursive=True)
             if "base_female_torso" not in p]                      # the base pack is hashed as the first input instead
    return _sha_files(list(seen) + data)


def _out_hash(st):
    if st.get("out_pack"):
        return _sha_files(_dir_files(st["out_pack"]))
    rp = os.path.join(ROOT, st["report"]) if st.get("report") else None
    return _sha_files([rp]) if rp and os.path.isfile(rp) else None


def _stage_key(st, rdir, input_hash):
    spec = json.dumps({k: st.get(k) for k in ("cmd", "env", "out_pack", "report")}, sort_keys=True)
    return hashlib.sha1((spec + _code_hash(st, rdir) + str(input_hash)).encode()).hexdigest()


def run(recipe_path, start=None, only=None, use_cache=True):
    """one recipe run at a time per recipe (two builders working in parallel would rewrite the same work packs): waits
    for <recipe dir>/runs/.lock, held while a run is in progress (a lock older than 2 h is stale and taken over)"""
    rdir = os.path.dirname(os.path.abspath(recipe_path)); os.makedirs(os.path.join(rdir, "runs"), exist_ok=True)
    lock = os.path.join(rdir, "runs", ".lock"); t0 = time.time()
    while os.path.exists(lock) and time.time() - os.path.getmtime(lock) < 7200:
        if time.time() - t0 < 5: print("recipe busy: waiting for the run in progress (%s)" % open(lock).read().strip())
        time.sleep(5)
    open(lock, "w").write("pid %d since %s" % (os.getpid(), time.strftime("%H:%M:%S")))
    try:
        return _run(recipe_path, start, only, use_cache)
    finally:
        if os.path.exists(lock): os.remove(lock)


def _run(recipe_path, start=None, only=None, use_cache=True):
    R = json.load(open(recipe_path)); rdir = os.path.dirname(os.path.abspath(recipe_path))
    rid = time.strftime("%Y%m%d-%H%M%S"); out = os.path.join(rdir, "runs", rid); os.makedirs(out, exist_ok=True)
    cdir = os.path.join(rdir, "cache"); os.makedirs(cdir, exist_ok=True)
    card = {"recipe": os.path.relpath(recipe_path, ROOT).replace("\\", "/"), "run": rid, "base_pack": R["base_pack"],
            "cache": use_cache and not (start or only), "stages": []}
    t_all = time.time(); started = start is None
    input_hash = _sha_files(_dir_files(R["base_pack"]))
    for st in R["stages"]:
        if not started and st["name"] == start: started = True
        if not started or (only and st["name"] != only):
            input_hash = _out_hash(st); continue
        key = _stage_key(st, rdir, input_hash); kf = os.path.join(cdir, st["name"] + ".json")
        if card["cache"] and os.path.isfile(kf):
            k = json.load(open(kf))
            if k.get("key") == key and k.get("out") is not None and k.get("out") == _out_hash(st):
                card["stages"].append({"name": st["name"], "seconds": 0.0, "ok": True, "cached": True,
                                       "out_pack": st.get("out_pack"), "report": st.get("report"), "cached_from": k.get("run")})
                print("%-12s cached (from run %s)" % (st["name"], k.get("run")))
                input_hash = k["out"]; continue
        env = dict(os.environ); env.update({k: str(v) for k, v in st.get("env", {}).items()})
        t0 = time.time()
        p = subprocess.run([sys.executable if c == "python" else c for c in st["cmd"]], cwd=ROOT, env=env, capture_output=True, text=True)
        dt = time.time() - t0
        tail = [l for l in (p.stdout + p.stderr).splitlines() if l.strip() and "Warning" not in l][-8:]
        ok = p.returncode == 0 and (not st.get("out_pack") or os.path.exists(os.path.join(ROOT, st["out_pack"], "skin.npz")))
        card["stages"].append({"name": st["name"], "seconds": round(dt, 1), "ok": ok, "out_pack": st.get("out_pack"),
                               "report": st.get("report"), "tail": tail})
        print("%-12s %6.1f s  %s" % (st["name"], dt, "ok" if ok else "FAILED"))
        if not ok:
            if os.path.isfile(kf): os.remove(kf)
            print("\n".join(tail)); break
        input_hash = _out_hash(st)
        json.dump({"key": key, "out": input_hash, "run": rid}, open(kf, "w"))
    final = next((s["out_pack"] for s in reversed(card["stages"]) if s["ok"] and s.get("out_pack")), None)
    card["result_pack"] = final
    if final and all(s["ok"] for s in card["stages"]) and R.get("verify"):
        v = R["verify"]; vj = os.path.join(out, "verify.json"); t0 = time.time()
        subprocess.run([v["blender"], "-b", "--factory-startup", "--python", os.path.join(ROOT, v["script"]), "--",
                        os.path.join(ROOT, final), vj], cwd=ROOT, capture_output=True, text=True)
        if os.path.exists(vj):
            d = json.load(open(vj)); o = d.get("overlaps_beyond_rest", {})
            card["verify"] = {"seconds": round(time.time() - t0, 1), "overlaps": {k: x for k, x in o.items() if x} or "none",
                              "rest_max_dev_mm": d.get("rest_max_dev_mm")}
        else:
            card["verify"] = {"error": "no verify output"}
        print("verify", card["verify"])
    if final and R.get("reference_pack"):
        a = np.load(os.path.join(ROOT, final, "skin.npz"))["v"].astype(float)
        b = np.load(os.path.join(ROOT, R["reference_pack"], "skin.npz"))["v"].astype(float)
        if a.shape == b.shape:
            dd = np.linalg.norm(a - b, axis=1)
            card["vs_reference"] = {"pack": R["reference_pack"], "max_mm": float(dd.max() * 1e3), "p99_mm": float(np.percentile(dd, 99) * 1e3)}
        else:   # a stage changed the topology (issue 03: the NAC patches rebuilt): each result vertex to the nearest reference vertex
            from scipy.spatial import cKDTree
            dd = cKDTree(b).query(a)[0]
            card["vs_reference"] = {"pack": R["reference_pack"], "topology": "differs: %d vertices vs %d" % (len(a), len(b)),
                                    "nearest_vertex_max_mm": float(dd.max() * 1e3), "nearest_vertex_p99_mm": float(np.percentile(dd, 99) * 1e3),
                                    "share_on_a_reference_vertex": float((dd < 1e-9).mean())}
        print("vs reference", card["vs_reference"])
    if final:   # folded faces on every build (engine/checks/folds.py; woman2 issue 03): the gate is no fold that is new
        sys.path.insert(0, os.path.join(ROOT, "engine", "checks"))
        import folds as FD
        fo = FD.compare(os.path.join(ROOT, final), os.path.join(ROOT, R["reference_pack"]) if R.get("reference_pack") else None)
        card["checks"] = {"folds": {k: fo[k] for k in ("deg", "count", "max_deg", "clusters", "new", "new_midpoints_mm") if k in fo},
                          "folds_gate": "PASS" if fo.get("new", fo["count"]) == 0 else "FAIL"}
        print("folds", card["checks"]["folds_gate"], {k: fo[k] for k in ("count", "new") if k in fo}, fo["clusters"][:3])
    card["seconds_total"] = round(time.time() - t_all, 1)
    # cost (the person: measure the cost of each generation): compute time here; the building agent's tokens are added to
    # the same card by the orchestrator from the agent's transcript (engine/tools/records/cost_ledger.py agent ...)
    card["cost"] = {"compute_seconds_stages": round(sum(s["seconds"] for s in card["stages"]), 1),
                    "compute_seconds_verify": (card.get("verify") or {}).get("seconds"),
                    "agent_tokens": "added by the orchestrator (cost_ledger.py agent)"}
    json.dump(card, open(os.path.join(out, "card.json"), "w"), indent=1)
    print("total %.1f s; card %s" % (card["seconds_total"], os.path.relpath(os.path.join(out, "card.json"), ROOT)))
    try:                                           # (build L1) language-tool jobs that read a stage's pack: kept current
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pack_io
        pack_io.notify_language([os.path.join(ROOT, s["out_pack"]) for s in card["stages"] if s.get("ok") and s.get("out_pack")])
    except Exception as ex:
        print("(recipe: language notify skipped: %s)" % ex)
    return card


if __name__ == "__main__":
    a = sys.argv[1:]
    start = a[a.index("--from") + 1] if "--from" in a else None
    only = a[a.index("--only") + 1] if "--only" in a else None
    run(a[0], start, only, use_cache="--no-cache" not in a)
