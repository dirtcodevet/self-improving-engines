"""THE TARGET-DRIVEN LOOP (2026-10-19, the person's math method; cases/woman2/MATH_METHOD_RECORD.md).

Language says what a thing is; numbers say what shape it has. A job is a STORY with numbers (what the subject is, what
the inputs can't show and the hypothesis for it), a set of DESCRIPTORS (measurable properties of a region: a profile
angle, a cross-section's roundness, a gap, a roughness), a TARGET for each (value, normal spread, source, rank), and
HANDLES (a few smooth ways the region may change: a spine bend, smooth bumps, a texture's parameters). The loop
measures, expresses every gap in units of normal variation (z), moves the handles until the descriptors sit inside
their normal range with the smallest change, checks the constraints, and reports the same table before and after.

Why: smoothing found irregularity, not wrongness (a smooth shelf passes any curvature threshold), guessed magnitudes
stood in for data, and screenshots stood in for acceptance (woman2 v5 armpit). Here nothing changes without a target
that says what right is, and nothing is accepted on a picture.

Targets are ranked (engine-grounding G3): measured in the input > a known-good reference measured with the SAME
descriptor > cited data with its normal spread > the story's own range (flagged). A target is a band, not a point:
inside +-1 sd costs almost nothing (anatomically normal variation is kept), outside it costs quadratically.

API (domain-free; named descriptors, handles and ops register in catalogue.py / lib/, used by job.py):
  Target(key, value, sd, source, rank, weight=1)
  measure(state, descriptors) -> {key: value}
  table(measured, targets) -> rows with z
  solve(state, handles, descriptors, targets, reg) -> (new state, params, report)
"""
import json
import numpy as np
from scipy.optimize import least_squares


class Target:
    def __init__(self, key, value, sd, source, rank, weight=1.0, inside_free=True):
        self.key, self.value, self.sd, self.source, self.rank = key, float(value), float(sd), source, rank
        self.weight, self.inside_free = float(weight), inside_free

    def z(self, x):
        return (x - self.value) / self.sd

    def cost(self, x):
        """residual: ~0 inside +-1 sd when inside_free (normal variation kept), linear in z beyond it"""
        z = self.z(x)
        if not self.inside_free:
            return self.weight * z
        return self.weight * np.sign(z) * max(0.0, abs(z) - 1.0) + 0.05 * self.weight * z   # a light pull to the mean

    @staticmethod
    def from_dict(d):
        return Target(d["key"], d["value"], d["sd"], d["source"], d["rank"], d.get("weight", 1.0), d.get("inside_free", True))


def measure(state, descriptors):
    out = {}
    for fn, params in descriptors:
        out.update(fn(state, **params))
    return out


def table(measured, targets):
    rows = []
    for t in targets:
        x = measured.get(t.key)
        rows.append({"key": t.key, "measured": None if x is None else float(x), "target": t.value, "sd": t.sd,
                     "z": None if x is None else float(t.z(x)), "inside": None if x is None else bool(abs(t.z(x)) <= 1.0),
                     "source": t.source, "rank": t.rank})
    return rows


def solve(state, handles, descriptors, targets, reg=0.05, max_nfev=60, log=print, diff_step=0.05, workers=8, jac_every=1):
    """least squares over the handles' parameters: target residuals + reg * (params - start) / scale (the smallest
    change that works; woman2 v6: regularised toward 0, a nipple scale starting at 1 was pulled to 0.37).
    handles: list of handle objects with .n, .x0, .bounds, .scale, .apply(state, params) -> new state.
    The solve runs on params / scale with its own forward differences of step diff_step x each handle's scale (woman2
    v6: scipy's relative step is diff_step x |x|, about 1e-8 at x = 0, so a handle starting at 0 was probed far below
    what its descriptor resolves; the raised-arm solve stalled)."""
    sizes = [h.n for h in handles]
    scales = np.concatenate([np.broadcast_to(np.asarray(h.scale, float), (h.n,)) for h in handles])
    x0 = np.concatenate([h.x0 for h in handles])
    lo = np.concatenate([h.bounds[0] for h in handles]); hi = np.concatenate([h.bounds[1] for h in handles])

    def split(x):
        out, i = [], 0
        for n in sizes:
            out.append(x[i:i + n]); i += n
        return out

    def apply(x):
        s = state
        for h, p in zip(handles, split(x)):
            s = h.apply(s, p)
        return s

    ustart = x0 / scales

    def resid(u):
        x = u * scales
        m = measure(apply(x), descriptors)
        r = [t.cost(m[t.key]) if m.get(t.key) is not None else 0.0 for t in targets]
        return np.r_[r, reg * (u - ustart)]      # the smallest change FROM THE START (a scale factor starts at 1, not 0)

    before = measure(state, descriptors)
    ul, uh = lo / scales, hi / scales
    u0 = np.clip(x0 / scales, ul, uh)
    # scipy's trust-region-reflective solver starts with a radius of |x0| (moved 1e-10 inside the bounds): a handle
    # starting at 0 took a first step of 1e-10 and gave up after a few evaluations (woman2 v6). The solve runs on
    # v = u + off with |v0| = 1, so the first trust region is one handle scale wide, wherever the start is.
    off = np.full(len(u0), 1.0 / np.sqrt(len(u0))) - u0
    cache = {"J": None, "n": 0}

    def jac(u):
        """forward differences with the step diff_step x each handle's scale (backward at an upper bound). scipy's own
        relative step is diff_step x |x| (and ~1e-8 at x = 0), so a handle starting at 0 was probed with steps far below
        what its descriptor resolves: an inflation from 0 never moved (woman2 v6).
        Speed (2026-10-19, the person: runs took hours): the columns run on `workers` threads, and a Jacobian is reused
        for `jac_every` calls (handles like bumps are linear, so it barely changes; the raised-arm job made ~2400
        serial evaluations per pose)."""
        if cache["J"] is not None and cache["n"] < jac_every:
            cache["n"] += 1; return cache["J"]
        f0 = resid(u)
        steps = [diff_step if u[i] + diff_step <= uh[i] else -diff_step for i in range(len(u))]
        def col(i):
            e = u.copy(); e[i] += steps[i]; return (resid(e) - f0) / steps[i]
        if workers > 1 and len(u) > 1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=workers) as ex:
                cols = list(ex.map(col, range(len(u))))
        else:
            cols = [col(i) for i in range(len(u))]
        J = np.stack(cols, 1); cache["J"], cache["n"] = J, 1
        return J

    res = least_squares(lambda v: resid(v - off), u0 + off, jac=lambda v: jac(v - off), bounds=(ul + off, uh + off), max_nfev=max_nfev)
    xs = (res.x - off) * scales
    new = apply(xs)
    after = measure(new, descriptors)
    res.x = xs
    rep = {"params": {h.name: [float(v) for v in p] for h, p in zip(handles, split(res.x))}, "nfev": int(res.nfev),
           "status": int(res.status), "before": table(before, targets), "after": table(after, targets),
           "all_before": {k: float(v) for k, v in before.items()}, "all_after": {k: float(v) for k, v in after.items()}}
    log("loop: %d evaluations; %s" % (res.nfev, ", ".join("%s z %+.2f -> %+.2f" % (a["key"], a["z"], b["z"])
                                                            for a, b in zip(rep["before"], rep["after"]) if a["z"] is not None)))
    return new, res.x, rep


def save_report(rep, path):
    json.dump(rep, open(path, "w"), indent=1, default=float)
