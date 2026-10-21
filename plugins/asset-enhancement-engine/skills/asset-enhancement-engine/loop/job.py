"""THE JOB RUNNER (2026-10-20): one generic recipe stage that carries an issue from a SPEC, with no new code when the
catalogue (engine/loop/catalogue.py, engine/loop/lib/) already has the pieces.

    python engine/loop/job.py <job.json> <in_pack> <out_pack>

job.json: {"name", "story" (words: what the subject is, what the input can't show), "report" (path, optional),
           "params" {...case values...}, "steps": [{"op": <catalogue op>, "args": {...}}, ...]}
Steps run in order on one Pack (pack_io.py); ops may leave values in ctx["vars"] for later steps. An argument written
"$var:<name>" is replaced by that value. The built-in op "solve" is the target-driven loop on a region:

  {"op": "solve", "args": {"name": "arm_L",
     "region": {"mask": "arm_limb", "x_sign": 1, "margin_m": 0.01}   (or {"var": <name of a mask in ctx vars>}),
     "descriptors": [{"name": <catalogue descriptor>, "args": {...}}],   "$core" = the region's movable mask,
     "targets": [{"key", "value", "sd", "source", "rank", "weight"?, "inside_free"?}],   "$mask:<k>" = state[k] > 0.5
     "handles": [{"name": <catalogue handle>, "args": {...}}],
     "solve": {"reg", "max_nfev", "diff_step", ...}}}

The report (before/after tables per solve, each op's own report) goes to job["report"] and ctx["report"].
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "engine"))
from loop import catalogue as CAT                     # noqa: E402
from loop.catalogue import op                         # noqa: E402
from loop.core import Target, solve as core_solve     # noqa: E402
from loop.region import Region                        # noqa: E402
from loop.pack_io import Pack                         # noqa: E402


def resolve(x, ctx, sub=None, core=None):
    if isinstance(x, str) and x.startswith("$"):
        if x == "$core": return x if core is None else core           # left for the op that has a region
        if x.startswith("$var:"): return ctx["vars"][x[5:]]
        if x.startswith("$mask:"): return x if sub is None else np.asarray(sub[x[6:]]) > 0.5
        raise KeyError("unknown reference " + x)
    if isinstance(x, dict): return {k: resolve(v, ctx, sub, core) for k, v in x.items()}
    if isinstance(x, list): return [resolve(v, ctx, sub, core) for v in x]
    return x


def region_mask(state, spec, ctx):
    if "var" in spec: return np.asarray(ctx["vars"][spec["var"]], bool)
    m = np.asarray(state[spec["mask"]]) > spec.get("threshold", 0.5) if spec.get("mask") else np.ones(len(state["V"]), bool)
    if spec.get("invert"): m = ~m
    for k in spec.get("exclude", []): m &= ~(np.asarray(state[k]) > 0.5)
    if spec.get("x_sign"): m &= np.sign(state["V"][:, 0]) == spec["x_sign"]
    for ax, i in (("x", 0), ("y", 1), ("z", 2)):
        if ax + "_min" in spec: m &= state["V"][:, i] >= spec[ax + "_min"]
        if ax + "_max" in spec: m &= state["V"][:, i] <= spec[ax + "_max"]
    assert m.any(), "empty region %s" % spec
    return m


@op("solve")
def solve_op(pack, ctx, name, region, descriptors, targets, handles, solve=None):
    """the target-driven loop on one region: descriptors, ranked targets and handles by catalogue name"""
    st = pack.state(); core_full = region_mask(st, region, ctx)
    R = Region(st, core_full, region.get("margin_m", 0.01)); sub = R.state
    desc = [(CAT.get("descriptor", d["name"]), resolve(d.get("args", {}), ctx, sub, R.core)) for d in descriptors]
    hs = [CAT.get("handle", h["name"])(sub, ctx, R.core, **resolve(h.get("args", {}), ctx, sub, R.core)) for h in handles]
    tg = [Target.from_dict(t) for t in targets]
    t0 = time.time()
    new_sub, x, rep = core_solve(sub, hs, desc, tg, log=ctx["log"], **(solve or {}))
    new = R.put(st, new_sub); pack.put_state(new)
    moved = np.linalg.norm(new["V"] - st["V"], axis=1)
    rep["region"] = {"core_vertices": int(R.core.sum()), "sub_vertices": len(R.ids), "full_vertices": R.n_full,
                     "max_move_mm": float(moved.max() * 1000), "seconds": round(time.time() - t0, 1)}
    ctx["report"][name] = rep


@op("measure")
def measure_op(pack, ctx, name, region, descriptors):
    """descriptors on a region, no change: the 'measure first' step (its table goes in the report)"""
    st = pack.state(); R = Region(st, region_mask(st, region, ctx), region.get("margin_m", 0.0)); sub = R.state
    out = {}
    for d in descriptors:
        out.update(CAT.get("descriptor", d["name"])(sub, **resolve(d.get("args", {}), ctx, sub, R.core)))
    ctx["report"][name] = out; ctx["log"]("%s: %s" % (name, {k: round(v, 3) if isinstance(v, float) else v for k, v in out.items()}))


def run(job_path, pin, pout):
    job = json.load(open(job_path)); CAT.load_library(); t0 = time.time()
    ctx = {"params": job.get("params", {}), "vars": {}, "report": {"job": job["name"], "story": job.get("story", "")},
           "log": print, "pin": pin, "pout": pout, "root": ROOT}
    pack = Pack(pin)
    for i, stp in enumerate(job["steps"]):
        ts = time.time()
        CAT.get("op", stp["op"])(pack, ctx, **resolve(stp.get("args", {}), ctx))
        print("step %d %-22s %6.1f s" % (i, stp["op"], time.time() - ts))
    pack.save(pout)
    ctx["report"]["seconds"] = round(time.time() - t0, 1)
    if job.get("report"):
        rp = os.path.join(ROOT, job["report"]); os.makedirs(os.path.dirname(rp), exist_ok=True)
        json.dump(ctx["report"], open(rp, "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o))
    print("job %s done in %.1f s" % (job["name"], time.time() - t0))
    return ctx


if __name__ == "__main__":
    a = sys.argv[1:]
    run(a[0], a[1], a[2])
