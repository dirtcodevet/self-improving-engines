"""Measure quadruped anatomy from an ALIGNED 3D reference mesh (world frame: faces -Y, +Z up, ground z=0):
trunk profiles along Y, four leg centrelines + radii (paw -> body), tail centreline + radii, head centre/size.
Output JSON feeds a lofted spec (loft_y trunk + loft_curve limbs). Also writes a diagnostic plot.

usage: python ref_measure.py <ref_aligned.ply> <out.json> [plot.png]
"""
import json, sys, os
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "checks"))
from checks import read_ply  # noqa: E402

ref_p, out_p = sys.argv[1:3]
plot_p = sys.argv[3] if len(sys.argv) > 3 else None
v, f = read_ply(ref_p)
# densify: sample points on triangles so thin slices always have support
rng = np.random.default_rng(0)
A, B, C = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
k = rng.choice(len(f), 400000, p=area / area.sum())
r1, r2 = rng.random(len(k)), rng.random(len(k))
s1 = np.sqrt(r1)
P = (1 - s1)[:, None] * A[k] + (s1 * (1 - r2))[:, None] * B[k] + (s1 * r2)[:, None] * C[k]
P = np.vstack([P, v])


def smooth(a, s=1.2):
    a = np.asarray(a, float)
    good = ~np.isnan(a)
    if good.sum() < 3:
        return a
    a = np.interp(np.arange(len(a)), np.nonzero(good)[0], a[good])
    return gaussian_filter1d(a, s)


# ---------------------------------------------------------------- legs: 4 clusters at low height
low = P[(P[:, 2] > 0.012) & (P[:, 2] < 0.045)]
tr = cKDTree(low[:, :2])
nc, lab = connected_components(tr.sparse_distance_matrix(tr, 0.004).tocsr() > 0, directed=False)
sizes = np.bincount(lab)
big = np.argsort(sizes)[::-1][:5]
cents = np.array([low[lab == i, :2].mean(0) for i in big])
# the tail tip may touch the floor: legs are the 4 clusters closest to the body's x-centre band
order = np.argsort(np.abs(cents[:, 0] - np.median(cents[:, 0])) + 0 * cents[:, 1])
legs_c = cents[np.argsort([np.abs(c[0] - np.median(cents[:4, 0])) for c in cents])[:4]]
front = legs_c[np.argsort(legs_c[:, 1])[:2]]
hind = legs_c[np.argsort(legs_c[:, 1])[2:]]
legs = {}
for nm, pair in (("f", front), ("h", hind)):
    for c in pair:
        side = "L" if c[0] > pair[:, 0].mean() else "R"
        legs[f"{nm}.{side}"] = c


def trace_leg(c0, ztop):
    pts, rad = [], []
    c = np.array(c0, float)
    for z in np.arange(0.006, ztop, 0.004):
        sl = P[np.abs(P[:, 2] - z) < 0.002]
        sl = sl[np.linalg.norm(sl[:, :2] - c, axis=1) < 0.03]
        if len(sl) < 20:
            break
        t2 = cKDTree(sl[:, :2])
        n2, l2 = connected_components(t2.sparse_distance_matrix(t2, 0.003).tocsr() > 0, directed=False)
        best = min(range(n2), key=lambda i: np.linalg.norm(sl[l2 == i, :2].mean(0) - c))
        blob = sl[l2 == best]
        cc = blob[:, :2].mean(0)
        if np.linalg.norm(cc - c) > 0.012:
            break
        c = cc
        r = np.median(np.linalg.norm(blob[:, :2] - c, axis=1))
        pts.append([c[0], c[1], z]); rad.append(r)
    return np.array(pts), np.array(rad)


# ---------------------------------------------------------------- trunk profiles along Y
ys = np.linspace(P[:, 1].min() + 0.01, P[:, 1].max() - 0.01, 90)
top, bot, mid, hw = [], [], [], []
for y in ys:
    sl = P[np.abs(P[:, 1] - y) < 0.003]
    m_ = sl[np.abs(sl[:, 0] - np.median(sl[:, 0])) < 0.008] if len(sl) else sl
    if len(m_) < 10:
        top.append(np.nan); bot.append(np.nan); mid.append(np.nan); hw.append(np.nan); continue
    t = m_[:, 2].max()
    cand = m_[(m_[:, 2] > 0.06)]
    b = cand[:, 2].min() if len(cand) else np.nan
    band = sl[(sl[:, 2] > b + 0.25 * (t - b)) & (sl[:, 2] < t - 0.05 * (t - b))] if not np.isnan(b) else sl[:0]
    if len(band) < 10:
        top.append(t); bot.append(b); mid.append(np.nan); hw.append(np.nan); continue
    xc = np.median(band[:, 0])
    half = (band[:, 0].max() - band[:, 0].min()) / 2
    zz = np.linspace(b, t, 30)
    widths = [np.ptp(band[np.abs(band[:, 2] - z_) < 0.004, 0]) if (np.abs(band[:, 2] - z_) < 0.004).sum() > 3 else 0 for z_ in zz]
    top.append(t); bot.append(b); hw.append(half); mid.append(zz[int(np.argmax(widths))])
top, bot, mid, hw = (smooth(a) for a in (top, bot, mid, hw))

# ---------------------------------------------------------------- head: points above the shoulder line, front half
yfront = P[:, 1].min()
headpts = P[(P[:, 1] < yfront + 0.10) & (P[:, 2] > np.nanmax(top[:20]) - 0.02)]
head_c = headpts.mean(0) if len(headpts) else None

res = {"trunk": {"y": ys.tolist(), "top": top.tolist(), "bot": bot.tolist(), "mid": mid.tolist(), "half_w": hw.tolist()},
       "legs": {}, "head": {"center": head_c.tolist() if head_c is not None else None,
                            "bbox_min": headpts.min(0).tolist(), "bbox_max": headpts.max(0).tolist()},
       "overall": {"bbox_min": v.min(0).tolist(), "bbox_max": v.max(0).tolist()}}
for nm, c in legs.items():
    under = np.interp(c[1], ys, bot)
    pts, rad = trace_leg(c, under + 0.03)
    res["legs"][nm] = {"paw_xy": c.tolist(), "centre": pts.tolist(), "radius": smooth(rad, 1.0).tolist(),
                       "underline_z": float(under)}
# ---------------------------------------------------------------- tail: z-slices behind the hind legs
yh = max(legs["h.L"][1], legs["h.R"][1]) if "h.L" in legs and "h.R" in legs else 0.1
tp, trad = [], []
body_end = P[:, 1].max()
prev = None
for z in np.arange(0.20, 0.008, -0.006):
    sl = P[(np.abs(P[:, 2] - z) < 0.003) & (P[:, 1] > yh + 0.03)]
    if len(sl) < 8:
        continue
    t2 = cKDTree(sl[:, :2])
    n2, l2 = connected_components(t2.sparse_distance_matrix(t2, 0.003).tocsr() > 0, directed=False)
    cl = [(sl[l2 == i, :2].mean(0), sl[l2 == i]) for i in range(n2) if (l2 == i).sum() >= 6]
    if not cl:
        continue
    if prev is None:   # start: the cluster nearest the body midline at the top
        c, blob = min(cl, key=lambda t: abs(t[0][0]))
    else:
        c, blob = min(cl, key=lambda t: np.linalg.norm(t[0] - prev))
        if np.linalg.norm(c - prev) > 0.03:
            break
    prev = c
    tp.append([c[0], c[1], z]); trad.append(float(np.median(np.linalg.norm(blob[:, :2] - c, axis=1))))
res["tail"] = {"centre": tp, "radius": smooth(trad, 1.0).tolist() if len(trad) > 2 else trad}
# ---------------------------------------------------------------- leg cross-sections (horizontal slices) until they join the trunk
res["leg_sections"] = {}
for nm, c0 in legs.items():
    prev, secs = np.array(c0), []
    for z in np.arange(0.03, 0.16, 0.0075):
        sl = P[np.abs(P[:, 2] - z) < 0.002]
        t2 = cKDTree(sl[:, :2]); n2, l2 = connected_components(t2.sparse_distance_matrix(t2, 0.003).tocsr() > 0, directed=False)
        cand = [(sl[l2 == i, :2].mean(0), sl[l2 == i, :2]) for i in range(n2) if (l2 == i).sum() >= 15]
        if not cand:
            break
        c, q = min(cand, key=lambda t: np.linalg.norm(t[0] - prev))
        ext = q.max(0) - q.min(0)
        if ext[0] > 0.07:          # slice has joined the trunk
            break
        secs.append([float(z), float((q[:, 0].max() + q[:, 0].min()) / 2), float((q[:, 1].max() + q[:, 1].min()) / 2),
                     float(ext[0] / 2), float(ext[1] / 2)])
        prev = c
    res["leg_sections"][nm] = secs
json.dump(res, open(out_p, "w"), indent=1)
print("tail:", len(tp), "slices", np.round(tp[0], 3).tolist() if tp else None, "->", np.round(tp[-1], 3).tolist() if tp else None,
      "r(mm) top/bottom", round(trad[0] * 1000, 1) if trad else None, round(trad[-1] * 1000, 1) if trad else None)
print("legs:", {k: (np.round(v_["paw_xy"], 3).tolist(), len(v_["centre"]), round(float(np.median(v_["radius"])) * 1000, 1))
                for k, v_ in res["legs"].items()})
print("trunk y range", round(ys[0], 3), round(ys[-1], 3), " max half-width", round(float(np.nanmax(hw)) * 1000, 1), "mm",
      " topline max", round(float(np.nanmax(top)), 3), " head centre", np.round(head_c, 3) if head_c is not None else None)
if plot_p:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    side = P[np.abs(P[:, 0] - np.median(P[:, 0])) < 0.03]
    ax[0].scatter(side[::20, 1], side[::20, 2], s=0.2, c="0.7")
    ax[0].plot(ys, top, "r"); ax[0].plot(ys, bot, "b"); ax[0].plot(ys, mid, "g--")
    for nm, L in res["legs"].items():
        c = np.array(L["centre"])
        if len(c):
            ax[0].plot(c[:, 1], c[:, 2], "k-")
    ax[0].set_aspect("equal"); ax[0].set_title("side: top(r) bottom(b) widest(g) legs(k)")
    ax[1].scatter(P[::20, 1], P[::20, 0], s=0.2, c="0.7"); ax[1].plot(ys, hw, "r"); ax[1].plot(ys, -hw, "r")
    ax[1].set_aspect("equal"); ax[1].set_title("top: half-width")
    plt.tight_layout(); plt.savefig(plot_p, dpi=110)
