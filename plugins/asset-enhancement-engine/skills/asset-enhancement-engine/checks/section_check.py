"""SECTION CHECK (domain-neutral): horizontal sections of a closed mesh, and what they say about the unseen side.

Why it exists (woman2, 2026-10-19): rock1's person's note was "everywhere the engine couldn't see became a smooth edge
or a flat surface", and object_checks only tests thickness and mirror copies. A front-photo build needs, per
horizontal section, (a) no crease or step where the surface turns through the occluding contour, (b) a back that is
not a slab, (c) limb sections that are round, not cards. Anatomy-specific tests (furrow, scapulae, lumbar hollow) are
the case's; this module gives the sections and the generic measures.

  sections(v, f, z)       closed loops of the mesh cut by the plane z (edge-keyed chaining; each loop (n,2) in x, y)
  turn_at_extremes(loop)  the largest turn (deg) over any WIN mm of arc within +-SPAN mm of arc around the loop's x-min
                          and x-max points (the occluding contour of a camera looking along y); a smooth section of
                          local radius R turns WIN/R rad, a crease turns at once
  back_flatness(loop, cx, a, y0)   RMS distance (mm) of the back part (y > y0, |x - cx| < 0.6 a) from its best straight line
  roundness(loop)         PCA aspect (minor/major extent) and convexity (area / convex-hull area)

Pass marks are the caller's (case values). Proof: prove() plants a crease and a slab on an ellipse and a card limb.
"""
import numpy as np
from scipy.spatial import ConvexHull

WIN, SPAN = 3.0, 25.0


def sections(v, f, z):
    """v in mm. returns list of loops (n,2)"""
    d = v[:, 2] - z
    s = np.sign(d); s[s == 0] = 1
    F = f[(s[f[:, 0]] != s[f[:, 1]]) | (s[f[:, 1]] != s[f[:, 2]])]
    if len(F) == 0:
        return []
    pts, adj = {}, {}
    for tri in F:
        keys = []
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            if s[a] != s[b]:
                k = (min(a, b), max(a, b))
                if k not in pts:
                    t = d[a] / (d[a] - d[b]); pts[k] = v[a, :2] + t * (v[b, :2] - v[a, :2])
                keys.append(k)
        if len(keys) == 2:
            adj.setdefault(keys[0], []).append(keys[1]); adj.setdefault(keys[1], []).append(keys[0])
    loops, seen = [], set()
    for k0 in adj:
        if k0 in seen:
            continue
        loop = [k0]; seen.add(k0); prev, cur = None, k0
        while True:
            nxt = [q for q in adj[cur] if q != prev and q not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]; seen.add(cur); loop.append(cur)
        if len(loop) >= 8:
            loops.append(np.array([pts[q] for q in loop]))
    return loops


def area(loop):
    x, y = loop[:, 0], loop[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def resample(loop, step=0.5):
    P = np.vstack([loop, loop[:1]]); seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]; L = s[-1]
    t = np.arange(0, L, step)
    return np.c_[np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])], L


def turn_at_extremes(loop, win=WIN, span=SPAN, step=0.5):
    R, L = resample(loop, step)
    tang = np.roll(R, -1, axis=0) - R
    n = len(R); w = max(1, int(round(win / step))); sp = int(round(span / step))
    out = {}
    for name, i0 in (("xmin", int(np.argmin(R[:, 0]))), ("xmax", int(np.argmax(R[:, 0])))):
        best = 0.0
        for k in range(-sp, sp + 1):
            i = (i0 + k) % n; j = (i + w) % n
            a1 = np.arctan2(tang[i, 1], tang[i, 0]); a2 = np.arctan2(tang[j, 1], tang[j, 0])
            dth = (a2 - a1 + np.pi) % (2 * np.pi) - np.pi
            best = max(best, abs(np.degrees(dth)))
        out[name] = best
    return out


def back_flatness(loop, cx, a, y0):
    m = (loop[:, 1] > y0) & (np.abs(loop[:, 0] - cx) < 0.6 * a)
    if m.sum() < 5:
        return None
    P = loop[m]
    c = np.polyfit(P[:, 0], P[:, 1], 1)
    r = P[:, 1] - np.polyval(c, P[:, 0])
    return float(np.sqrt(np.mean(r ** 2)) / np.sqrt(1 + c[0] ** 2))


def roundness(loop):
    C = loop - loop.mean(0)
    ev = np.sort(np.linalg.eigvalsh(np.cov(C.T)))
    try:
        hull = ConvexHull(loop).volume
    except Exception:
        hull = area(loop)
    return dict(aspect=float(np.sqrt(ev[0] / max(ev[1], 1e-12))), convexity=float(area(loop) / max(hull, 1e-12)))


def prove():
    t = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    ell = np.c_[130 * np.cos(t), 100 * np.sin(t)]
    crease = ell.copy(); crease[:, 1] = np.where(crease[:, 1] > 0, np.minimum(crease[:, 1], 15.0), crease[:, 1])   # flat back meeting the side at a corner
    slab = ell.copy(); slab[:, 1] = np.where(slab[:, 1] > 0, np.minimum(slab[:, 1], 80.0), slab[:, 1])
    card = np.c_[40 * np.cos(t), 8 * np.sin(t)]
    limb = np.c_[38 * np.cos(t), 41 * np.sin(t)]
    return dict(ellipse_turn=turn_at_extremes(ell), crease_turn=turn_at_extremes(crease),
                ellipse_back_rms=back_flatness(ell, 0, 130, 10), slab_back_rms=back_flatness(slab, 0, 130, 10),
                limb=roundness(limb), card=roundness(card))


if __name__ == "__main__":
    print(prove())
