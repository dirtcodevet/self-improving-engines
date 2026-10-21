"""NO FLAT LIMBS: the person's standing limit in numbers - no flat arms or torso (build 13a's m_arm.py,
cases/woman2/build13/; moved here in build A1, 2026-10-21, unchanged in what it reads). Any body whose limb runs from one
joint to the next; the defaults are a human upper arm's.

  section_loop_faces(V, T, o, a, near, max_loop_r=0.085)
        faces crossed by the closed section contour (plane through o, normal a) that winds round `near` (the limb's
        axis point): contour segments joined through the mesh edges they cross (exact, no link distance); None when the
        limb is no loop of its own there (joined to the trunk)
  limb_flats(V, T, j0, j1, stations=STATIONS, max_loop_r=0.085)
        flat share of the limb's sections perpendicular to j0 -> j1 at the given fractions (engine/loop/shape.py
        limb_sections: share of each outline whose curvature is under a quarter of the outline's mean), per station and
        as the mean / max over the stations where the limb is a loop of its own; aspect; curvature jump
  measure(V, T, J, arm, overlap=True, mid_x=0.0)
        the gate as build 13a ran it, per side L / R of J (joints: "gh", "elbow"; arm: the limb's vertex mask):
        flat share (above); clearance of the inner upper arm to the side (the upper-arm zone 30-85 % of gh -> elbow,
        within 55 mm of the axis, facing away from it, its medial half: an outward ray along each vertex normal to the
        first other surface; build 12 measured v12 p5 0.5-0.6 mm, 22-24 % under 2 mm); the armpit vault (the highest
        downward-facing skin, normal z < -0.5, within 4 mm of the joint's frontal plane, 50 mm medial to 10 mm lateral,
        10-250 mm below the joint); with overlap=True also the whole mesh's crossing triangle pairs (a crossing anywhere
        is a defect). Frame: x = the subject's left, z up, metres.
Proofs: engine/checks/test_limb_flats.py (planted: a round limb, the same limb with a flat cut along it, a side wall at a
known gap, an armpit roof at a known depth; json beside it); on a known answer, v12, whose arm values earlier builds
recorded with other instruments: cases/woman2/build13/prove_m_arm.py (work/prove_m_arm.json).
"""
import os
import sys

import numpy as np

_E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
for _p in (os.path.normpath(os.path.join(_E, "tools")), os.path.normpath(_E)):
    if _p not in sys.path:
        sys.path.append(_p)
import mesh_geom as MG  # noqa: E402
import bvh  # noqa: E402
from loop import shape as SH  # noqa: E402

STATIONS = [0.15, 0.25, 0.35, 0.45, 0.6]
MAX_LOOP_R = 0.085   # m: an upper arm's section lies within ~50 mm of its axis (v12 49 mm deltoid protrusion)


def section_loop_faces(V, T, o, a, near, max_loop_r=MAX_LOOP_R):
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    s = (V - o) @ a
    sf = s[T]; cr = np.nonzero((sf.min(1) < 0) & (sf.max(1) > 0))[0]
    if len(cr) < 10:
        return None
    E = np.sort(np.concatenate([T[cr][:, [0, 1]], T[cr][:, [1, 2]], T[cr][:, [2, 0]]]), 1)
    fid = np.tile(np.arange(len(cr)), 3)
    cut = (s[E[:, 0]] < 0) != (s[E[:, 1]] < 0)
    E, fid = E[cut], fid[cut]
    key = E[:, 0].astype(np.int64) * len(V) + E[:, 1]
    _, inv = np.unique(key, return_inverse=True)
    g = sparse.coo_matrix((np.ones(len(fid)), (fid, inv)), shape=(len(cr), inv.max() + 1)).tocsr()
    nc, lab = connected_components(g @ g.T, directed=False)
    ref = np.array([0, 0, 1.0]) if abs(a[2]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(a, ref); e1 /= np.linalg.norm(e1); e2 = np.cross(a, e1)
    cen = V[T[cr]].mean(1); q = np.c_[(cen - near) @ e1, (cen - near) @ e2]
    best = None
    for c in range(nc):
        m = lab == c
        if m.sum() < 20:
            continue
        th = np.sort(np.arctan2(q[m, 1], q[m, 0]))
        gap = np.max(np.diff(np.r_[th, th[0] + 2 * np.pi]))          # a loop round `near` leaves no wide angular gap
        rr = np.hypot(q[m, 0], q[m, 1]).mean()
        rmax = np.hypot(q[m, 0], q[m, 1]).max()                       # the limb's own loop, not trunk + limb
        if gap < np.radians(30) and rmax < max_loop_r and (best is None or rr < best[1]):
            best = (cr[m], rr)
    return None if best is None else best[0]


def limb_flats(V, T, j0, j1, stations=STATIONS, max_loop_r=MAX_LOOP_R):
    a_ = (j1 - j0) / np.linalg.norm(j1 - j0); La = np.linalg.norm(j1 - j0); ls = {}
    for k, tt in enumerate(stations):
        o_ = j0 + a_ * La * tt
        fc = section_loop_faces(V, T, o_, a_, o_, max_loop_r)
        if fc is None:
            continue
        rm = np.zeros(len(V), bool); rm[T[fc].ravel()] = True
        r1 = SH.limb_sections({"V": V, "F": T}, j0, j1, [tt], rm, prefix="up")
        for kk, vv in r1.items():
            if kk.startswith("up_s0_"):
                ls[kk.replace("up_s0_", "up_s%d_" % k)] = vv
    n = len(stations)
    fl = [ls["up_s%d_flat" % k] for k in range(n) if "up_s%d_flat" % k in ls]
    if fl:
        ls.update(up_flat_mean=float(np.mean(fl)), up_flat_max=float(np.max(fl)), up_stations_ok=len(fl),
                  up_aspect_mean=float(np.mean([ls["up_s%d_aspect" % k] for k in range(n) if "up_s%d_aspect" % k in ls])),
                  up_jump_max=float(np.max([ls["up_s%d_jump" % k] for k in range(n) if "up_s%d_jump" % k in ls])))
    return {"flat_share_mean": round(ls.get("up_flat_mean", np.nan), 4), "flat_share_max": round(ls.get("up_flat_max", np.nan), 4),
            "stations_ok": ls.get("up_stations_ok", 0),
            "flat_by_station": {str(stations[k]): round(ls["up_s%d_flat" % k], 4) for k in range(n) if "up_s%d_flat" % k in ls},
            "aspect_mean": round(ls.get("up_aspect_mean", np.nan), 4), "curv_jump_max": round(ls.get("up_jump_max", np.nan), 3)}


def measure(V, T, J, arm, overlap=True, mid_x=0.0, stations=STATIONS):
    N = MG.vertex_normals(V, T)
    reg = {"L": arm & (V[:, 0] > 0), "R": arm & (V[:, 0] < 0)}
    out = {}
    O, D, owner = [], [], []
    for s, sg in (("L", 1), ("R", -1)):
        gh, el = J[s]["gh"], J[s]["elbow"]
        o = limb_flats(V, T, gh, el, stations)
        o.update(arm_vertices=int(reg[s].sum()), stations_note="stations where the arm is a closed section loop of its own")
        u = (el - gh) / np.linalg.norm(el - gh); alen = np.linalg.norm(el - gh)
        d = V - gh; t = d @ u; rad = d - t[:, None] * u; r = np.linalg.norm(rad, axis=1)
        xs = sg * (V[:, 0] - mid_x); ghx = sg * (gh[0] - mid_x)
        ua = (xs > 0) & (t > 0.30 * alen) & (t < 0.85 * alen) & (r < 0.055) & ((rad * N).sum(1) > 0)
        med = ua & ((d * sg)[:, 0] < 0)
        O.append(V[med] + 0.0 * N[med]); D.append(N[med]); owner.append(np.full(med.sum(), 0 if s == "L" else 1))
        ap = (np.abs(V[:, 1] - gh[1]) < 0.004) & (xs > ghx - 0.05) & (xs < ghx + 0.01) & (V[:, 2] < gh[2] - 0.01) & (V[:, 2] > gh[2] - 0.25) & (N[:, 2] < -0.5)
        o["vault_apex_below_joint_mm"] = round(float((gh[2] - V[ap, 2].max()) * 1000), 2) if ap.any() else None
        o["vault_apex_point_m"] = V[ap][np.argmax(V[ap, 2])].round(5).tolist() if ap.any() else None
        out[s] = o
    O = np.concatenate(O); D = np.concatenate(D); owner = np.concatenate(owner)
    rr = bvh.rays(V, T, O=O, D=D, overlap=overlap)
    for k, s in enumerate(("L", "R")):
        c = rr["dist"][owner == k] * 1000
        fin = np.isfinite(c)
        out[s]["inner_arm_clearance_mm"] = {"p5": round(float(np.nanpercentile(c, 5)), 2), "p50": round(float(np.nanpercentile(c, 50)), 2),
                                            "share_under_2mm": round(float(np.nanmean(c < 2.0)), 4), "rays": int(len(c)),
                                            "rays_hit": int(fin.sum())}
    if overlap:
        P = bvh.drop_shared(T, rr["pairs"])
        ar = MG.face_areas(V, T)
        cen = V[T].mean(1)
        out["self_crossing"] = {"pairs": int(len(P)), "area_cm2": round(float(ar[np.unique(P.ravel())].sum() * 1e4), 3) if len(P) else 0.0,
                                "where_m": cen[np.unique(P.ravel())].round(3).tolist()[:20]}
    return out
