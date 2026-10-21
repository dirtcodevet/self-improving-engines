"""Hair-tract PRIOR: the direction hair grows at any skin point when the photo can't show it (numpy only; used by
groom.py and hair_field.py - one definition). Deterministic: per-strand jitter stays in groom.

Felid tracts (cat-specific knowledge; belongs in a felid pack once the engine is split, skill item A9): face hair
flows out from the nose, body hair back and down the flanks, legs down, chest down, tail toward its tip, ear backs
and rims toward the tip, ear interior and furnishings up and out, the eye surround radially away from the eye.
"""
import numpy as np


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


def ss(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def tract_nodes(L, prm):
    """SOURCE / SINK model of the face's hair tracts in the head frame (metres): the nose source, ear-base sinks,
    jaw-angle sinks (mirrored) and a neck sink; positions from landmarks + fitted offsets (tools/fit_tracts.py)."""
    R, H0 = np.array(L["head_R"]), np.array(L["head"])
    loc = lambda k: (np.array(L[k]) - H0) @ R
    nose = loc("nose")
    out = [(nose + np.array([0, prm["nose_dy"], prm["nose_dz"]]), 1.0)]
    for k, s in (("ear_base.R", -1), ("ear_base.L", 1)):
        eb = loc(k)
        out.append((eb + np.array([0, prm["ear_dy"], prm["ear_dz"]]), prm["ear_k"]))
        out.append((np.array([s * abs(eb[0]) * prm["jaw_xfrac"], eb[1] + prm["jaw_dy"], eb[2] + prm["jaw_dz"]]), prm["jaw_k"]))
    out.append((np.array([0, prm["neck_y"], prm["neck_z"]]), prm["neck_k"]))
    return out


def source_sink_field(q, nq, nodes, eps=0.004):
    """v(q) = sum k_i (q - s_i) / (|q - s_i|^2 + eps^2), tangent-projected, unit; q, nq in the head frame"""
    v = np.zeros_like(q)
    for s, k in nodes:
        d = q - s
        v += k * d / ((d * d).sum(1, keepdims=True) + eps * eps)
    v = v - (v * nq).sum(1, keepdims=True) * nq
    return unit(v)


def tract_field(P, Nn, zone, L, furn_out=1.0, tracts=None):
    """Unit tangent growth directions at points P (world) with normals Nn and hair-zone ids (coat.py).
    tracts: optional fitted source/sink parameters (case hair_tracts.json) - then the FACE follows that model
    instead of the single radial source above the nose (R3f #70: cheek fur fans outward and DOWN toward the jaw)."""
    N = len(P)
    Hc, nose, Rh = np.array(L["head"]), np.array(L["nose"]), np.array(L["head_R"])
    x, y, z = P.T
    side = np.sign(x + 1e-9)
    body = unit(np.stack([0.35 * side * np.abs(Nn[:, 0]), np.ones(N), -0.9 * np.abs(Nn[:, 0]) - 0.15], 1))
    legs = unit(np.stack([np.zeros(N), 0.25 * np.ones(N), -np.ones(N)], 1))
    chest = unit(np.stack([0.2 * side, -0.15 * np.ones(N), -np.ones(N)], 1))
    face = unit(P - nose + Rh @ np.array([0, 0.0, 0.004]))
    if tracts is not None and tracts.get("model", "").startswith("radial"):
        # one radial source on the midline, raised src_up (head frame, metres) above the nose: at the source's
        # height fur runs straight out, below it outward-and-down, above it up (R3f: the person's cheek lines)
        face = unit(P - nose - Rh @ np.array([0, 0.0, tracts["params"]["src_up"]]))
    elif tracts is not None:
        H0 = np.array(L["head"])
        face = source_sink_field((P - H0) @ Rh, unit(Nn @ Rh), tract_nodes(L, tracts["params"])) @ Rh.T
    d_head = np.linalg.norm(P - Hc, axis=1)
    w_head = ss(0.075, 0.055, d_head)
    w_legs = ss(0.115, 0.085, z) * (1 - w_head)
    w_chest = ss(-0.07, -0.11, y) * ss(0.08, 0.11, z) * ss(0.24, 0.20, z) * (1 - w_head)
    comb = body * (1 - np.clip(w_legs + w_chest, 0, 1))[:, None] + legs * w_legs[:, None] + chest * w_chest[:, None]
    comb = comb * (1 - w_head)[:, None] + face * w_head[:, None]
    inside = np.isin(zone, (6, 12))
    for sd in "RL":
        eb, et = np.array(L[f"ear_base.{sd}"]), np.array(L[f"ear_tip.{sd}"])
        ax = unit(et - eb)
        rel = P - eb
        tt = rel @ ax / np.linalg.norm(et - eb)
        rad = np.linalg.norm(rel - np.outer(rel @ ax, ax), axis=1)
        we = ss(0.12, 0.25, tt) * ss(0.026, 0.016, rad)
        we = np.maximum(we, np.isin(zone, (6, 7, 8, 12)) * (side == (1 if sd == "L" else -1)))
        if f"ear_u.{sd}" in L:
            eu = np.array(L[f"ear_u.{sd}"]); eu = unit(eu - (eu @ ax) * ax)
            d_ear = np.where(inside[:, None], unit(ax + furn_out * eu)[None], ax[None])
        else:
            d_ear = np.broadcast_to(ax, (N, 3))
        comb = comb * (1 - we)[:, None] + d_ear * we[:, None]
    T = np.array(L["tail"])
    seg = np.diff(T, axis=0)
    best = np.full(N, 9.0); tdir = np.zeros((N, 3))
    for i in range(len(seg)):
        t = np.clip(((P - T[i]) @ seg[i]) / (seg[i] @ seg[i]), 0, 1)
        d = np.linalg.norm(P - (T[i] + t[:, None] * seg[i]), axis=1)
        b = d < best
        best = np.where(b, d, best)
        tdir[b] = unit(seg[i])
    wt = ss(0.02, 0.012, best) * (y > 0.12)
    comb = comb * (1 - wt)[:, None] + tdir * wt[:, None]
    for sd in "RL":
        if f"eye.{sd}" in L:
            ec = np.array(L[f"eye.{sd}"])
            de = np.linalg.norm(P - ec, axis=1)
            wa = ss(L["eye_r"] + 0.012, L["eye_r"] + 0.004, de)
            comb = comb * (1 - wa)[:, None] + unit(P - ec) * wa[:, None]
    return comb - (comb * Nn).sum(1, keepdims=True) * Nn      # tangent plane (not normalised: groom jitters first)
