"""L1 SKULL (felid pack asset): a SIMPLIFIED, form-giving skull built from PARTS measured on a real reference skull
photographed from several sides (layered-build.md, L1 head inventory: cranium with brow, orbits, zygomatic arches,
nasal bridge and NASAL APERTURE, maxilla and mandible meeting at the JAW LINE, jaw angle and chin).

Every dimension is measured on the reference views - profiles auto-extracted from the view masks, a few points picked
on grid crops (G4) - and scaled by the sourced skull length. Shape choices without a source are flagged in the
report. The visual hull of the same views is NOT the geometry (three silhouettes cannot carry rounded sections:
tried and rejected, R4c); it CLIPS the parts (no part may leave a silhouette) and MEASURES the result (silhouette
IoU per view).

Parts: cranium = superelliptic loft (top = lateral silhouette; bottom = the picked jaw line in front, the silhouette
behind the jaw joint; width = the dorsal view's central run with the arch roots interpolated); zygomatic arches =
tubes through the picked lateral centreline at the dorsal view's arch positions; postorbital processes = cones;
mandible = two lofted rami (top = jaw line + picked ramus outline, bottom = silhouette) fused at the chin, with
condyles; nasal aperture = the front view's dark opening carved back to the orbits; orbits = sockets carved for the
eyeballs (here at the reference's estimated eye seats; a case carves at its registered eyes).

Frame: x = left, y = back, z = up, mm, origin = the views' box centre.
usage: python skull_build.py <spec.json> <picks.json> <out_prefix> [vox_mm=0.4]
writes <out>_cranium.ply, <out>_mandible.ply (metres), <out>.npz (fields), <out>_landmarks.json, <out>_report.json
"""
import json
import os
import sys

import cv2
import numpy as np
from scipy import ndimage
from scipy.interpolate import PchipInterpolator

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from view_hull import load_views, pick_to_model, img_to_model  # noqa: E402
from sdf_core import loft_y, round_cone, smin, smax, write_ply  # noqa: E402

EYE_R = 10.0          # mm, sourced eyeball radius (pack: eyeball_diameter 20.0)


def close_ends(st, T, B, M, W, length=3.0):
    """close a loft with shrinking sections over `length` mm at both ends (rounded, not a flat cap)"""
    f = np.sqrt(1 - np.array([1, 2, 2.85]) ** 2 / 9.0)               # quarter-circle closure (rounded, not a point)
    ye = [st[0] - length * np.array([1, 2, 3]) / 3, st[-1] + length * np.array([1, 2, 3]) / 3]
    S_, T_, B_, M_, W_ = [st], [T], [B], [M], [W]
    for end, yv in ((0, ye[0]), (-1, ye[1])):
        m = M[end]
        S_.append(yv); M_.append(np.full(3, m)); T_.append(m + f * (T[end] - m)); B_.append(m - f * (m - B[end])); W_.append(f * W[end])
    st2 = np.concatenate(S_); o = np.argsort(st2)
    return st2[o], np.concatenate(T_)[o], np.concatenate(B_)[o], np.concatenate(M_)[o], np.concatenate(W_)[o]


def side_profiles(d):
    m = d["m"]; out = []
    for c in range(m.shape[1]):
        rows = np.nonzero(m[:, c])[0]
        if len(rows) < 2: continue
        _, y = img_to_model(d, "right", c)
        _, z0 = img_to_model(d, "down", rows.min()); _, z1 = img_to_model(d, "down", rows.max())
        out.append((y, max(z0, z1), min(z0, z1)))
    out.sort()
    a = np.array(out); return a[:, 0], a[:, 1], a[:, 2]


def dorsal_runs(d):
    m = d["m"]; e0, e1 = d["ext"]["down"]; mid = int(round((e0 + e1) / 2)); out = []
    for c in range(m.shape[1]):
        idx = np.nonzero(m[:, c])[0]
        if len(idx) == 0: continue
        _, y = img_to_model(d, "right", c)
        runs = np.split(idx, np.where(np.diff(idx) > 1)[0] + 1)
        mm = [sorted([img_to_model(d, "down", r[0])[1], img_to_model(d, "down", r[-1])[1]]) for r in runs]
        cen = [q for q, r in zip(mm, runs) if r[0] <= mid <= r[-1]]
        out.append(dict(y=y, runs=mm, central=cen[0] if cen else None))
    out.sort(key=lambda r: r["y"]); return out


def has_gap(r, x_min=20.0):
    """a dorsal station with a SEE-THROUGH gap beside the central run: three or more runs, the outermost on each side
    lying beyond x_min (where the arches are) - rostral segmentation specks are not gaps (R4c)"""
    return (r["central"] is not None and len(r["runs"]) >= 3 and any(q[0] > x_min for q in r["runs"])
            and any(q[1] < -x_min for q in r["runs"]))                 # run order follows image rows, not +x


def view_sdf(d, P):
    """2-D signed distance of a view's mask (mm), extruded along the axis the view does not show"""
    m = d["m"]; s = d["scale_mm_per_px"]
    sd = (cv2.distanceTransform(1 - m, cv2.DIST_L2, 5) - cv2.distanceTransform(m, cv2.DIST_L2, 5)) * s
    cols = []
    for k in ("right", "down"):
        a, sg = d["ax"][k]; e0, e1 = d["ext"][k]
        cols.append((e0 + e1) / 2 + sg * P[a] / s)
    u, w = cols
    return ndimage.map_coordinates(sd, [w.ravel(), u.ravel()], order=1, mode="constant", cval=50.0).reshape(P[0].shape).astype(np.float32)


def nasal_aperture_mask(img, d, box, midline_x):
    """the dark opening inside a search box of the front view (Otsu on luminance inside the object), nearest the box
    centre -> a mask in the view's local coordinates"""
    x, y, w, h = d["v"]["bbox"]
    c = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2GRAY)
    x0, y0, x1, y1 = box[0] - x, box[1] - y, box[2] - x, box[3] - y
    sub = c[y0:y1, x0:x1]; inside = d["m"][y0:y1, x0:x1] > 0
    t, _ = cv2.threshold(sub[inside].reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = ((sub < t) & inside).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(dark, 8)
    if n < 2: return None, t
    ctr = np.array([(x1 - x0) / 2, (y1 - y0) / 2])
    j = 1 + int(np.argmin([np.linalg.norm(cen[i] - ctr) - 0.002 * st[i, 4] for i in range(1, n)]))
    ap = np.zeros_like(d["m"]); ap[y0:y1, x0:x1] = (lab == j)
    ap = cv2.morphologyEx(ap, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    # the opening's RIM, not the threshold's pixel noise (a jagged carve showed in the viewport, R4c / J13): fill it,
    # then smooth the outline at ~1 mm (sigma 12 px at ~0.078 mm/px) and re-threshold at half
    ap = ndimage.binary_fill_holes(ap).astype(np.float32)
    ap = (cv2.GaussianBlur(ap, (0, 0), 12) > 0.5).astype(np.uint8)
    # bilateral symmetry: the threshold catches the shadowed side more (an asymmetric opening, R4c) -> union with the
    # mirror about the picked midline
    mc = midline_x - x; W_ = ap.shape[1]; mir = np.zeros_like(ap)
    cols = np.arange(W_); src = np.round(2 * mc - cols).astype(int); ok = (src >= 0) & (src < W_)
    mir[:, cols[ok]] = ap[:, src[ok]]
    ap = np.maximum(ap, mir)
    return ap, float(t)


SECTION_DEFAULT = dict(q_up=2.0, q_dn=2.3, mid_b=0.5, mid_f=0.5, clip=0)


def main(spec_path, picks_path, out, vox=0.4, mesh=True):
    S = json.load(open(spec_path)); K = json.load(open(picks_path))
    # cross-section shape: FITTED to the views (tools/skull_fit_sections.py -> <spec dir>/ref20_sections.json), not
    # clipped - a clip against an extruded silhouette cuts flat walls (streaks) wherever the assumed section is wrong
    SEC = dict(SECTION_DEFAULT)
    sec_path = os.path.join(os.path.dirname(os.path.abspath(spec_path)), "ref20_sections.json")
    if os.path.exists(sec_path): SEC.update(json.load(open(sec_path))["params"])
    if os.environ.get("SKULL_PARAMS"): SEC.update(json.loads(os.environ["SKULL_PARAMS"]))
    V, scale, implied, ext_all, box, la = load_views(S)
    lat, dor, fr = V["lateral"], V["dorsal"], V["front"]
    img = cv2.imread(S["image"])
    flags = []
    LP = lambda xy: pick_to_model(lat, xy); FP = lambda xy: pick_to_model(fr, xy)
    yz = lambda xy: (LP(xy)[1], LP(xy)[2])
    # ---- profiles
    ys, T, B = side_profiles(lat)
    # profiles are per pixel column (~0.07 mm): smooth at bone scale (sigma 1.2 mm) - a 5-px window left the mask's
    # pixel ripple, which the loft turned into rings and vertical streaks (R4c, isolated with SKULL_NOCLIP)
    sig = lambda yv: max(1.0, 1.2 / max(np.median(np.diff(yv)), 1e-6))
    fT = PchipInterpolator(ys, ndimage.gaussian_filter1d(T, sig(ys), mode="nearest"))
    fB = PchipInterpolator(ys, ndimage.gaussian_filter1d(B, sig(ys), mode="nearest"))
    jl = sorted(yz(p) for p in K["lateral"]["jaw_line"]["xy"])        # front (most negative y) first
    jy, jz = np.array([p[0] for p in jl]), np.array([p[1] for p in jl])
    y_tmj, z_tmj = yz(K["lateral"]["tmj"]["xy"])
    arch = sorted(yz(p) for p in K["lateral"]["arch"]["xy"])
    ay0, ay1 = arch[0][0], arch[-1][0]
    DR = dorsal_runs(dor)
    # ---- cranium width: the dorsal central run; inside the arch span only where holes flank it (the roots merge
    # with the arch there), interpolated across the roots
    keep = [r for r in DR if r["central"] and (not (ay0 - 2 <= r["y"] <= ay1 + 2) or has_gap(r))]
    ky = np.array([r["y"] for r in keep]); kw = np.array([(r["central"][1] - r["central"][0]) / 2 for r in keep])
    _, iu = np.unique(np.round(ky, 2), return_index=True); ky, kw = ky[iu], kw[iu]
    fW = PchipInterpolator(ky, ndimage.gaussian_filter1d(kw, sig(ky), mode="nearest"))
    flags.append("cranium width inside the arch span: interpolated across the arch roots (no direct view of the braincase there)")
    # ---- cranium bottom: jaw line in front, silhouette behind the jaw joint, straight between (hidden by the ramus)
    y_back = y_tmj + 3.0

    def cbot(y):
        y = np.asarray(y, float)
        return np.where(y <= jy[-1], np.interp(y, jy, jz),
                        np.where(y >= y_back, fB(np.clip(y, ys[0], ys[-1])),
                                 jz[-1] + (y - jy[-1]) / (y_back - jy[-1]) * (fB(y_back) - jz[-1])))
    flags.append("cranial base between the jaw line's back end and the jaw joint: straight line (hidden by the ramus in the lateral view)")
    st = np.arange(max(jy[0], ys[0], DR[0]["y"]) + 0.5, min(ys[-1], DR[-1]["y"]) - 0.5, 1.0)
    cT, cB, cW = fT(st), cbot(st), fW(st)
    y_eye_guess = yz(((K["lateral"]["orbit_rim_box"]["xyxy"][0] + K["lateral"]["orbit_rim_box"]["xyxy"][2]) / 2, 300))[0]
    mf = SEC["mid_f"] + (SEC["mid_b"] - SEC["mid_f"]) * np.clip((st - y_eye_guess + 5) / 10, 0, 1)   # face -> braincase
    cM = cB + mf * (cT - cB)
    st, cT, cB, cM, cW = close_ends(st, cT, cB, cM, cW)
    flags.append(f"sections FITTED to the three views (q_up {SEC['q_up']}, q_dn {SEC['q_dn']}, widest at {SEC['mid_f']} (face) / {SEC['mid_b']} (braincase) of the height); ends closed by quarter-circle shrinking over 3 mm")
    # ---- grid
    pad = 4.0; lo = -box / 2 - pad; n = np.ceil((box + 2 * pad) / vox).astype(int) + 1
    g = [lo[a] + np.arange(n[a]) * vox for a in range(3)]
    X, Y, Z = np.meshgrid(*g, indexing="ij"); P = (X, Y, Z)
    hull = np.maximum(np.maximum(view_sdf(lat, P), view_sdf(dor, P)), view_sdf(fr, P))
    cr = loft_y(st, cT, cB, cM, cW, q_up=SEC["q_up"], q_dn=SEC["q_dn"], name="cranium").fn(X, Y, Z).astype(np.float32)
    # ---- eye seats (reference only; a case carves at its registered eyes): lateral rim box centre (y, z) + front
    # rim box centre (x, z); the two z values are an agreement test
    bx = K["lateral"]["orbit_rim_box"]["xyxy"]; c_lat = yz(((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2))
    fb = K["front"]["orbit_rim_box_image_left"]["xyxy"]; c_fr = FP(((fb[0] + fb[2]) / 2, (fb[1] + fb[3]) / 2))
    eye_x = abs(c_fr[0]); eye = {"R": np.array([-eye_x, c_lat[0], (c_lat[1] + c_fr[2]) / 2]),
                                 "L": np.array([eye_x, c_lat[0], (c_lat[1] + c_fr[2]) / 2])}
    orbit_z_disagreement = abs(c_lat[1] - c_fr[2])
    # FRONT CENTRAL WIDTH: per height z, the front view's run through the midline (bounded by the see-through gaps
    # beside the orbits) = the widest the cranium is at that height at ANY depth. A smooth 1-D profile (sigma 1.2 mm),
    # applied with a rounded max - not the pixel-jagged extruded mask, whose clip made the streaks (R4c, J13)
    mid_c = K["front"]["midline_x"] - fr["v"]["bbox"][0]; zs_c, ws_c = [], []
    for row in range(fr["m"].shape[0]):
        r_ = fr["m"][row]
        if not r_[mid_c]: continue
        a_ = mid_c; b_ = mid_c
        while a_ > 0 and r_[a_ - 1]: a_ -= 1
        while b_ < len(r_) - 1 and r_[b_ + 1]: b_ += 1
        zs_c.append(img_to_model(fr, "down", row)[1])
        ws_c.append(max(abs(img_to_model(fr, "right", a_)[1]), abs(img_to_model(fr, "right", b_)[1])))
    o_ = np.argsort(zs_c); zs_c = np.array(zs_c)[o_]; ws_c = ndimage.gaussian_filter1d(np.array(ws_c)[o_], 1.2 / fr["scale_mm_per_px"], mode="nearest")
    w_fc = np.interp(Z, zs_c, ws_c, left=ws_c[0], right=ws_c[-1])
    cr = smax(cr, (np.abs(X) - w_fc).astype(np.float32), 1.5)
    flags.append("cranium limited per height by the front view's central run (smooth profile): the see-through gaps beside the orbits are measured 'no bone at any depth'")
    # ---- ORBIT FLOOR (maxilla + palate under the orbits): seen from above between each arch and the cranium, in
    # front of the temporal gaps (dorsal view: R4c / D2). A slab from the jaw line up to the arch's height, as wide as
    # the dorsal outline less the arch, from the arch's front root back to the gaps' front edge. Shelf top = arch
    # height: inferred (flagged)
    th_ = [(q[1] - q[0]) / 2 for r in DR if has_gap(r) for q in r["runs"] if q[0] > 20 or q[1] < -20]
    a_th = float(np.median(th_)) if th_ else 1.5
    gap_ys = [r["y"] for r in DR if has_gap(r)]
    y_f0, y_f1 = min(a_[0] for a_ in arch), (min(gap_ys) if gap_ys else max(a_[0] for a_ in arch))
    fsta = [r for r in DR if y_f0 <= r["y"] <= y_f1]
    if len(fsta) > 10:
        fy = np.array([r["y"] for r in fsta])
        fw = np.array([max(abs(v) for q in r["runs"] for v in q) - 2 * a_th for r in fsta])
        _, iu_ = np.unique(np.round(fy, 2), return_index=True); fy, fw = fy[iu_], ndimage.gaussian_filter1d(fw[iu_], sig(fy[iu_]), mode="nearest")
        az = np.interp(fy, [a_[0] for a_ in arch], [a_[1] for a_ in arch])
        fb = cbot(fy); ftop = np.maximum(az, fb + 2.0); fmid = fb + 0.5 * (ftop - fb)
        fst, fT_, fB_, fM_, fW_ = close_ends(fy, ftop, fb, fmid, fw, length=2.0)
        shelf = loft_y(fst, fT_, fB_, fM_, fW_, q_up=4.0, q_dn=4.0, name="orbit_floor").fn(X, Y, Z).astype(np.float32)
        shelf = smax(shelf, (np.abs(X) - w_fc).astype(np.float32), 1.5)   # same measured per-height width limit
        cr = smin(cr, shelf, 2.0)
        flags.append(f"orbit floor (maxilla/palate under the orbits): y {y_f0:.1f}..{y_f1:.1f} mm, width from the dorsal outline (measured), top at the arch height (inferred), boxy sections q 4 (unsourced)")
    for e in eye.values():
        sph = np.sqrt((X - e[0]) ** 2 + (Y - e[1]) ** 2 + (Z - e[2]) ** 2) - (EYE_R + 0.5)
        cr = np.maximum(cr, -sph)
    # ---- nasal aperture: carve the front view's dark opening back to the eye seats' y (the nasal cavity runs back
    # between the orbits), narrowing 15 % per 10 mm
    ap, thr = nasal_aperture_mask(img, fr, K["front"]["nasal_aperture_box"]["xyxy"], K["front"]["midline_x"])
    ap_rep = None
    if ap is not None and ap.sum() > 50:
        s_ = fr["scale_mm_per_px"]
        sd2 = (cv2.distanceTransform(1 - ap, cv2.DIST_L2, 5) - cv2.distanceTransform(ap, cv2.DIST_L2, 5)) * s_
        u = (fr["ext"]["right"][0] + fr["ext"]["right"][1]) / 2 + X / s_
        w = (fr["ext"]["down"][0] + fr["ext"]["down"][1]) / 2 - Z / s_
        d2 = ndimage.map_coordinates(sd2, [w.ravel(), u.ravel()], order=1, mode="constant", cval=50.0).reshape(X.shape)
        y_front = float(st[0]); y_end = float(eye["L"][1])
        d_ap = np.maximum(d2 + 0.015 * np.maximum(Y - y_front, 0) * 10 / 10, np.maximum(Y - y_end, y_front - 6 - Y))
        # the cavity has WALLS: behind the opening (ramp over the first 4 mm) it stays >= 1.5 mm inside the face's
        # outer surface - a free tunnel broke out through the sides of the narrowing face and the nasal bridge (R4c)
        ys_, xs_ = np.nonzero(ap)
        xa = float(np.mean([img_to_model(fr, "right", v)[1] for v in (xs_.min(), xs_.max())]))
        za = float(np.mean([img_to_model(fr, "down", v)[1] for v in (ys_.min(), ys_.max())]))
        i0 = int(round((xa - lo[0]) / vox)); k0 = int(round((za - lo[2]) / vox))
        inside_col = np.nonzero(cr[i0, :, k0] < 0)[0]
        y_surf = float(lo[1] + inside_col[0] * vox) if len(inside_col) else y_front   # the face surface AT the opening
        ramp = np.clip((Y - y_surf - 1.0) / 3.0, 0, 1)
        d_ap = np.maximum(d_ap, (cr + 1.5) * ramp - 50.0 * (1 - ramp))
        cr = np.maximum(cr, -d_ap.astype(np.float32))
        ys_, xs_ = np.nonzero(ap)
        ap_x = [img_to_model(fr, "right", v)[1] for v in (xs_.min(), xs_.max())]
        ap_z = [img_to_model(fr, "down", v)[1] for v in (ys_.min(), ys_.max())]
        ap_rep = dict(width_mm=round(abs(ap_x[1] - ap_x[0]), 2), height_mm=round(abs(ap_z[1] - ap_z[0]), 2),
                      centre_xz=[round(float(np.mean(ap_x)), 2), round(float(np.mean(ap_z)), 2)], depth_to_y=round(y_end, 2), otsu=thr)
        cv2.imwrite(out + "_aperture_check.png", np.dstack([fr["m"] * 120, fr["m"] * 120, np.maximum(fr["m"] * 120, ap * 255)]))
        flags.append("nasal cavity: carved back to the eye seats' y, narrowing, with 1.5 mm walls (wall thickness unsourced; depth derived: the cavity runs between the orbits)")
    # ---- zygomatic arches: lateral centreline (y, z) at the dorsal view's arch x (outer run's centre where a hole
    # separates it; else the outermost mask edge minus the arch radius = a root)
    r_arch = K["lateral"]["arch"]["half_height_px"] * lat["scale_mm_per_px"]     # vertical half-height (lateral)
    DRy = np.array([r["y"] for r in DR])
    # horizontal half-thickness MEASURED in the dorsal view: the outer run beside each see-through gap (the arch is a
    # flat bar, not a round tube: R4c / D6)
    th = [(q[1] - q[0]) / 2 for r in DR if has_gap(r) for q in r["runs"] if q[0] > 20 or q[1] < -20]
    a_arch = float(np.median(th)) if th else r_arch
    arches = np.full(X.shape, 1e3, np.float32); arch_pts = {}
    for sd, sg in (("L", 1), ("R", -1)):
        pts = []
        for y, z in arch:
            r = DR[int(np.argmin(np.abs(DRy - y)))]
            side = [q for q in r["runs"] if (q[0] * sg > 0 or q[1] * sg > 0) and q != r["central"]]
            if has_gap(r) and side:
                q = max(side, key=lambda q: abs(q[0] + q[1])); x = (q[0] + q[1]) / 2
            else:
                x = sg * (max(abs(v) for q in r["runs"] for v in q if v * sg > 0) - a_arch)
            pts.append(np.array([x, y, z]))
        arch_pts[sd] = pts
        P_ = np.array(pts); o_ = np.argsort(P_[:, 1]); P_ = P_[o_]
        fx, fz = PchipInterpolator(P_[:, 1], P_[:, 0]), PchipInterpolator(P_[:, 1], P_[:, 2])
        yc = np.clip(Y, P_[0, 1], P_[-1, 1])
        u, v = (X - fx(yc)) / a_arch, (Z - fz(yc)) / r_arch                # elliptic section in the x-z plane
        k0 = np.sqrt(u * u + v * v); k1 = np.sqrt((u / a_arch) ** 2 + (v / r_arch) ** 2)
        de = np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -min(a_arch, r_arch))
        over = np.maximum(P_[0, 1] - Y, Y - P_[-1, 1])
        d_bar = np.minimum(np.maximum(de, over), 0) + np.sqrt(np.maximum(de, 0) ** 2 + np.maximum(over, 0) ** 2)
        arches = smin(arches, d_bar.astype(np.float32), 1.0)
    flags.append(f"arches: elliptic bars, horizontal half-thickness {a_arch:.2f} mm (dorsal view, measured), vertical half-height {r_arch:.2f} mm (lateral, picked)")
    # ---- postorbital processes (frontal from the brow, jugal from the arch): tips picked in two views; the two z
    # estimates are an agreement test
    procs = np.full(X.shape, 1e3, np.float32); proc_rep = {}
    for nm, lk, fk, base_from in (("frontal", "frontal_process_tip", "frontal_process_tips", "brow"), ("jugal", "jugal_process_tip", "jugal_process_tips", "arch")):
        ty, tz_l = yz(K["lateral"][lk]["xy"])
        for sd, sg, fxy in (("R", -1, K["front"][fk]["xy"][0]), ("L", 1, K["front"][fk]["xy"][1])):
            f = FP(fxy); tip = np.array([sg * abs(f[0]), ty, (tz_l + f[2]) / 2])
            if base_from == "brow":
                base = np.array([tip[0] * 0.6, ty + 1.0, tip[2] + 6.0]); r0, r1 = 2.4, 0.8
            else:
                ap_ = min(arch_pts[sd], key=lambda p: abs(p[1] - ty)); base = ap_.copy(); r0, r1 = 2.0, 0.7
            procs = smin(procs, round_cone(base, tip, r0, r1).fn(X, Y, Z).astype(np.float32), 1.0)
            proc_rep[f"{nm}.{sd}"] = dict(tip=tip.round(2).tolist(), z_lateral=round(tz_l, 2), z_front=round(f[2], 2))
    flags.append("postorbital process BASES inferred (tips picked); cone radii unsourced")
    cranium = smin(cr, smin(arches, procs, 1.0), 2.0)
    if SEC.get("clip"):                                              # off by default: clipping made streaks (R4c, J13)
        cranium = smax(cranium, hull, 1.2)
    # ---- mandible: two lofted rami fused at the chin
    rt = sorted(yz(p) for p in K["lateral"]["ramus_top"]["xy"])
    ty_all = np.r_[jy, [p[0] for p in rt[1:]]]; tz_all = np.r_[jz, [p[1] for p in rt[1:]]]
    o = np.argsort(ty_all); ty_all, tz_all = ty_all[o], tz_all[o]
    y_ang, z_ang = yz(K["lateral"]["mandible_angle"]["xy"])
    mst = np.arange(jy[0] + 0.5, max(y_ang, y_tmj) - 0.5, 1.0)
    mT = np.interp(mst, ty_all, tz_all); mB = fB(mst)
    mB = np.minimum(mB, mT - 2.0)
    half_t = np.where(mst <= jy[-1], 2.4, 1.4)
    mM0 = mB + 0.5 * (mT - mB)
    mst, mT, mB, _, half_t = close_ends(mst, mT, mB, mM0, half_t, length=2.0)
    flags.append("mandible half-thickness 2.4 mm (body) / 1.4 mm (ramus): unsourced; coronoid tips from the front view (measured), their y inferred from the lateral view")
    w_tmj = float(np.interp(z_tmj, zs_c, ws_c))                       # front view: widest anything is at that height
    x_cond = w_tmj - 4.0                                              # condyle (r 2.2, outer end +1.8) inside it
    x_sym = 2.5
    lobes = [FP(p)[0] for p in K["front"]["mandible_ventral_lobes"]["xy"]]
    x_lobe = (abs(lobes[0]) + abs(lobes[1])) / 2
    y_low = float(mst[int(np.argmin(mB))])                           # the lowest point of the ventral border
    xm = lambda yv: np.interp(yv, [mst[0], y_low, y_tmj], [x_sym, x_lobe, x_cond])
    flags.append(f"rami: chin x {x_sym} mm (symphysis, unsourced) -> {x_lobe:.1f} mm at the lowest ventral point (front-view lobes, picked) -> condyles inside the front view's width at the jaw-joint height ({w_tmj:.1f} mm, measured; condyle size unsourced)")
    mand = np.full(X.shape, 1e3, np.float32)
    mM = mB + 0.5 * (mT - mB)
    ram = loft_y(mst, mT, mB, mM, half_t, q_up=2.0, q_dn=2.0, name="ramus")
    for sg in (1, -1):
        d = ram.fn(X - sg * xm(Y), Y, Z).astype(np.float32)
        cond = round_cone((sg * (x_cond - 3.5), y_tmj, z_tmj), (sg * (x_cond + 1.8), y_tmj, z_tmj), 2.6, 2.2).fn(X, Y, Z).astype(np.float32)
        # coronoid process: from the ramus at the (lateral, inferred) coronoid y up to the tip SEEN in the front view
        y_c = yz(K["lateral"]["ramus_top"]["xy"][2])[0]
        tips = [FP(p) for p in K["front"]["coronoid_tips"]["xy"]]
        x_t = float(np.mean([abs(t_[0]) for t_ in tips])); z_t = float(np.mean([t_[2] for t_ in tips]))
        base = (sg * float(xm(y_c)), y_c, float(np.interp(y_c, ty_all, tz_all)) - 4.0)
        cor = round_cone(base, (sg * x_t, y_c, z_t), 2.2, 1.1).fn(X, Y, Z).astype(np.float32)
        cond = smin(cond, cor, 1.5)
        mand = smin(mand, smin(d, cond, 1.5), 2.0)
    if SEC.get("clip"):
        mand = np.maximum(mand, np.maximum(view_sdf(lat, P), view_sdf(fr, P)))
    # ---- meshes
    from skimage import measure
    res = {}
    if mesh:
        for nm, F in (("cranium", cranium), ("mandible", mand)):
            v_, f_, _, _ = measure.marching_cubes(F, 0.0, spacing=(vox, vox, vox)); v_ += lo
            write_ply(f"{out}_{nm}.ply", v_ / 1000.0, f_); res[nm] = dict(verts=len(v_), faces=len(f_))
        np.savez_compressed(out + ".npz", cranium=cranium, mandible=mand, lo=lo, vox=vox)
    # ---- acceptance instrument: silhouette IoU per view (union of the parts)
    occ = np.minimum(cranium, mand) < 0
    iou = {}
    for nm, d in V.items():
        a_r, s_r = d["ax"]["right"]; a_d, s_d = d["ax"]["down"]
        hid = 3 - a_r - a_d
        proj = occ.any(axis=hid)                                      # indexed by the remaining two axes in order
        m = d["m"]; H, W = m.shape
        cc, rr = np.meshgrid(np.arange(W), np.arange(H))
        mr = (cc - (d["ext"]["right"][0] + d["ext"]["right"][1]) / 2) * s_r * d["scale_mm_per_px"]
        md = (rr - (d["ext"]["down"][0] + d["ext"]["down"][1]) / 2) * s_d * d["scale_mm_per_px"]
        idx = {a_r: np.clip(np.round((mr - lo[a_r]) / vox).astype(int), 0, n[a_r] - 1), a_d: np.clip(np.round((md - lo[a_d]) / vox).astype(int), 0, n[a_d] - 1)}
        ax_sorted = sorted([a_r, a_d])
        built = proj[idx[ax_sorted[0]], idx[ax_sorted[1]]]
        inter = (built & (m > 0)).sum(); uni = (built | (m > 0)).sum()
        iou[nm] = round(float(inter / uni), 4)
        iou[nm + "_excess"] = round(float((built & (m == 0)).sum() / max((m > 0).sum(), 1)), 4)
        iou[nm + "_missed"] = round(float(((m > 0) & ~built).sum() / max((m > 0).sum(), 1)), 4)
        if mesh: cv2.imwrite(f"{out}_iou_{nm}.png", np.dstack([m * 255, built.astype(np.uint8) * 255, m * 0]))
    # ---- landmarks (reference frame, mm)
    chin_i = int(np.argmin(mst)); chin = [0.0, float(mst[0]), float(mB[0])]
    LM = dict(eye_seat={k: v.round(2).tolist() for k, v in eye.items()},
              tmj={"R": [-x_cond, y_tmj, z_tmj], "L": [x_cond, y_tmj, z_tmj]},
              jaw_line={sd: [[sg * float(fW(y)), float(y), float(z)] for y, z in zip(jy, jz)] for sd, sg in (("R", -1), ("L", 1))},
              chin=chin, nasal_tip=[0.0, float(st[0]), float(cT[0])],
              nasal_aperture=ap_rep, occiput=[0.0, float(ys[-1]), float(fT(ys[-1]))],
              meatus={sd: [sg * float(fW(yz(K["lateral"]["meatus"]["xy"])[0])), *yz(K["lateral"]["meatus"]["xy"])] for sd, sg in (("R", -1), ("L", 1))},
              arch_widest_mm=round(2 * max(abs(p[0]) + a_arch for p in arch_pts["L"]), 2))
    json.dump(LM, open(out + "_landmarks.json", "w"), indent=1)
    rep = dict(section=SEC, views=dict(scale_mm_per_px={k: round(v, 5) for k, v in scale.items()}, front_scale_spread=implied),
               silhouette_iou=iou, orbit_z_disagreement_mm=round(orbit_z_disagreement, 2), processes=proc_rep,
               arch_widest_mm=LM["arch_widest_mm"], meshes=res, flags=flags, aperture=ap_rep)
    json.dump(rep, open(out + "_report.json", "w"), indent=1, default=float)
    print(json.dumps(dict(silhouette_iou=iou, orbit_z_disagreement_mm=rep["orbit_z_disagreement_mm"], arch_widest_mm=LM["arch_widest_mm"],
                          aperture=ap_rep, x_condyle=round(x_cond, 2), eye_seat=LM["eye_seat"], meshes=res), indent=1, default=float))
    return rep


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else 0.4,
         mesh=os.environ.get("SKULL_NOMESH") != "1")
