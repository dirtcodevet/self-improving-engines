"""Generic pieces (domain-neutral): the existing shape descriptors and handles under catalogue names, and rig points. Domain names (which mask is an arm) come from the job spec, never from here."""
import json, os
import numpy as np
from ..catalogue import descriptor, handle, op
from .. import shape as SH


descriptor("profile_arcs")(SH.profile_arcs)
descriptor("limb_sections")(SH.limb_sections)
descriptor("state_value")(SH.state_value)


@handle("normal_bumps")
def normal_bumps(state, ctx, core, n_centres=16, bound_m=0.005, name="normal_bumps"):
    """smooth bumps along the normal over the region's movable core (biharmonic basis), centres spread evenly over it
    by farthest-point sampling from the core's most central vertex (deterministic)"""
    V = state["V"]; ids = np.where(core)[0]; P = V[ids]
    first = int(np.argmin(np.linalg.norm(P - P.mean(0), axis=1))); chosen = [first]
    d = np.linalg.norm(P - P[first], axis=1)
    for _ in range(n_centres - 1):
        j = int(np.argmax(d)); chosen.append(j); d = np.minimum(d, np.linalg.norm(P - P[j], axis=1))
    return SH.NormalBumps(state, core, ids[chosen], bound_m=bound_m, name=name)


@op("rig_points")
def rig_points(pack, ctx, bones, rig="rig.json"):
    """bone heads and tails (rest pose) into ctx vars as '<bone>.head' / '<bone>.tail' (axes for limb sections)"""
    R = pack.json(rig); B = R.get("bones", R)
    items = B.items() if isinstance(B, dict) else [(b["name"], b) for b in B]
    found = {}
    for nm, b in items:
        if nm in bones:
            found[nm] = b; ctx["vars"][nm + ".head"] = list(map(float, b["head"])); ctx["vars"][nm + ".tail"] = list(map(float, b["tail"]))
    missing = sorted(set(bones) - set(found))
    assert not missing, "bones not in %s: %s (it has %s)" % (rig, missing, [n for n, _ in items][:20])
