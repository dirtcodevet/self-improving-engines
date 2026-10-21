"""REGION-ONLY EVALUATION (2026-10-19, the person's D20/D26): a job that changes one region solves on that region's
sub-mesh, not the whole body. Measured cost it removes: run 1's six trial solves took ~23 of its 35 tool minutes because
every evaluation re-sliced the whole 542k-vertex mesh ~20 times; builders' own trial scripts took 14-28 min per run.

A Region is the vertices a job may MOVE (the core mask) plus a MARGIN it may only read (context for descriptors that
look a little past the edge: a section that runs off the core, a rim the change must meet smoothly). Its .state is a
self-contained sub-state - V, F (faces with all three corners kept, reindexed) and every per-vertex array of the full
state sliced to the kept vertices - so the existing handles and descriptors run on it unchanged.

    R = Region(state, core_mask, margin_m=0.01)
    sub = R.state                                   # build handles and descriptors on the sub-state
    handles = [NormalBumps(sub, R.core, centres=R.local(ids))]
    new_sub, x, rep = solve(sub, handles, descriptors, targets)
    state = R.put(state, new_sub)                   # writes the moved core back; asserts the margin did not move

Rules it enforces: only core vertices move (put() asserts the margin and everything outside are unchanged, unless
allow_margin=True); per-vertex arrays are sliced, never copied whole; vertex ids map both ways (.ids, .local()).
Not for handles that move the whole body (SliceBend, RigidTurn): they are global by nature - solve those on the full
state. Proof: engine/loop/test_region.py (same answer as the full-mesh solve; outside untouched; the speed on base
torso v11).
"""
import numpy as np
from scipy.spatial import cKDTree


class Region:
    def __init__(self, state, core_mask, margin_m=0.0):
        V = state["V"]; n = len(V); core_mask = np.asarray(core_mask, bool)
        assert core_mask.shape == (n,) and core_mask.any(), "core mask must be a non-empty per-vertex mask"
        keep = core_mask.copy()
        if margin_m > 0:
            d, _ = cKDTree(V[core_mask]).query(V, distance_upper_bound=margin_m)
            keep |= np.isfinite(d)
        self.n_full = n
        self.ids = np.where(keep)[0]                          # sub index -> full index
        self._pos = -np.ones(n, np.int64); self._pos[self.ids] = np.arange(len(self.ids))
        F = state["F"]; Fk = F[keep[F].all(1)]
        sub = {}
        for k, v in state.items():
            if k == "F":
                sub[k] = self._pos[Fk]
            elif isinstance(v, np.ndarray) and v.ndim >= 1 and v.shape[0] == n:
                sub[k] = v[self.ids]
            else:
                sub[k] = v                                    # scalars, settings, non-vertex arrays
        self.core = core_mask[self.ids]                       # the movable part, in sub indices
        self.state = sub

    def local(self, full_ids):
        """full vertex ids -> sub ids (asserts each is in the region)"""
        p = self._pos[np.asarray(full_ids)]
        assert (p >= 0).all(), "vertex outside the region"
        return p

    def put(self, full_state, sub_state, allow_margin=False, tol=0.0):
        """the full state with the sub-state's vertex positions written back. Per-vertex arrays other than V are not
        written back (a job that changes a mask or weights does so on the full state). Asserts that no margin vertex
        moved by more than tol (m) unless allow_margin."""
        Vs = sub_state["V"]; V0 = full_state["V"][self.ids]
        if not allow_margin:
            moved = np.linalg.norm(Vs[~self.core] - V0[~self.core], axis=1)
            assert moved.size == 0 or moved.max() <= tol, "margin moved by %.3g m" % moved.max()
        out = dict(full_state); V = full_state["V"].copy(); V[self.ids] = Vs; out["V"] = V
        for k, v in sub_state.items():                         # results a handle left in the state (e.g. a turn's angle)
            if k not in ("V", "F") and not (isinstance(v, np.ndarray) and v.ndim >= 1 and v.shape[0] == len(self.ids)):
                out[k] = v
        return out


def solve_region(state, core_mask, make, targets, margin_m=0.01, **solve_kw):
    """the whole pattern in one call: make(sub_state, region) -> (handles, descriptors), built on the sub-state; the
    solve runs there; returns (full new state, params, report). margin_m must cover what the handles and descriptors
    read beyond the core (NormalBumps: 2 rings; a section that runs past the core: its length)."""
    try:
        from .core import solve                             # imported as loop.region
    except ImportError:
        from core import solve                              # engine/loop on the path
    R = Region(state, core_mask, margin_m)
    handles, descriptors = make(R.state, R)
    new_sub, x, rep = solve(R.state, handles, descriptors, targets, **solve_kw)
    rep["region"] = {"core_vertices": int(R.core.sum()), "sub_vertices": int(len(R.ids)), "full_vertices": int(R.n_full),
                     "margin_m": float(margin_m)}
    return R.put(state, new_sub), x, rep
