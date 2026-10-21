"""Proofs for object_checks.py on PLANTED failures on every side each check can fail (A22), using synthetic objects
only (never the case photo): a faceted ellipsoid built as an intersection of half-spaces (every face a true plane,
like a fracture face), rendered through a test camera with a granite-like Voronoi grain.

Usage: python object_checks_prove.py [out.json]      (default: cases/rock1/checks_proven.json)
Each case records what it must give (expect pass / fail), what it gave, and the metrics. A case is OK only when the
verdict equals the expectation; for a planted failure the side that must catch it is named and checked too.
"""
import json
import os
import sys
import time

import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull, HalfspaceIntersection, cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import object_checks as oc  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "cases", "rock1", "checks_proven.json")
IMG_DIR = os.path.join(os.path.dirname(OUT), "checks_proof")
T0 = time.time()
CASES = []


def case(check, name, expect_pass, res, side=None, note=None):
    """side: the sub-verdict key that must be False for a planted failure (e.g. 'pass_iou')"""
    got = bool(res["pass"])
    ok = got == expect_pass
    if side is not None and not expect_pass:
        ok = ok and (res.get(side) is False)
    CASES.append(dict(check=check, case=name, expect="pass" if expect_pass else "fail", got="pass" if got else "fail",
                      must_catch=side, ok=bool(ok), metrics={k: v for k, v in res.items() if k != "pass"}, note=note))
    print(f"  [{'OK ' if ok else 'BAD'}] {check:18s} {name:34s} expect {'pass' if expect_pass else 'fail'} got {'pass' if got else 'fail'}"
          + (f"  ({side})" if side else ""), flush=True)


# =====================================================================  synthetic objects
AX = np.array([0.36, 0.26, 0.19])


def rand_planes(n, seed, hemi=None):
    """planes tangent to the ellipsoid AX at random points; hemi=+1/-1 keeps normals with sign(n_y) = hemi"""
    rng = np.random.default_rng(seed); out = []
    while len(out) < n:
        u = rng.normal(size=3); u /= np.linalg.norm(u); p = AX * u; nn = p / AX ** 2; nn /= np.linalg.norm(nn)
        if hemi is not None and np.sign(nn[1]) != hemi:
            continue
        out.append((nn, float(nn @ p)))
    return out


BOTTOM = [(np.array([0.0, 0.0, -1.0]), 0.8 * AX[2])]


def polytope(planes):
    N = np.array([p[0] for p in planes]); d = np.array([p[1] for p in planes])
    hi = HalfspaceIntersection(np.c_[N, -d], np.zeros(3))
    V = np.unique(np.round(hi.intersections, 10), axis=0)
    h = ConvexHull(V); F = h.simplices.copy(); eq = h.equations[:, :3]
    nt = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    flip = np.einsum("ij,ij->i", nt, eq) < 0; F[flip] = F[flip][:, ::-1]
    lab = np.argmax(eq @ N.T, 1)
    keep = np.linalg.norm(nt, axis=1) > 1e-14
    return V, F[keep], lab[keep]


def subdivide(v, f, lab, k=2):
    for _ in range(k):
        e = np.sort(np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]], 1)
        ue, inv = np.unique(e, axis=0, return_inverse=True); inv = inv.ravel()
        mid = 0.5 * (v[ue[:, 0]] + v[ue[:, 1]]); base = len(v); v = np.r_[v, mid]
        F = len(f); m01, m12, m20 = base + inv[:F], base + inv[F:2 * F], base + inv[2 * F:]
        a, b, c = f[:, 0], f[:, 1], f[:, 2]
        f = np.r_[np.c_[a, m01, m20], np.c_[m01, b, m12], np.c_[m20, m12, c], np.c_[m01, m12, m20]]
        lab = np.r_[lab, lab, lab, lab]
    return v, f, lab


def build(planes, S, TR):
    v, f, lab = polytope(planes); v, f, lab = subdivide(v, f, lab, 2)
    return v * S + TR, f, lab


FRONT = [p for p in rand_planes(40, 11) if p[0][1] <= 0]
BACK = [p for p in rand_planes(40, 11) if p[0][1] > 0]
TRUTH_PLANES = FRONT + BACK + BOTTOM
v0, f0, l0 = polytope(TRUTH_PLANES); v0, f0, l0 = subdivide(v0, f0, l0, 2)
S = 0.70 / oc.horizontal_extent(v0)["extent_m"]
TR = np.array([0.0, 0.0, -v0[:, 2].min() * S])
VT, FT, LT = build(TRUTH_PLANES, S, TR)
CEN = VT.mean(0)

W, H = 1728, 1152
CAM = oc.Camera.look_at(eye=(0.0, -2.3, 0.95), target=(0.0, 0.0, 0.17), fx=3400, W=W, H=H)
LIGHT = np.array([-0.45, -0.65, 0.62]); LIGHT /= np.linalg.norm(LIGHT)
MINERALS = np.array([[0.22, 0.22, 0.24], [0.55, 0.54, 0.52], [0.82, 0.80, 0.78]]); MIN_P = [0.25, 0.45, 0.30]


def voronoi_grain(cell_px, seed, contrast=1.0, box=(250, 1480, 150, 1050)):
    rng = np.random.default_rng(seed); x0, x1, y0, y1 = box
    ns = int((x1 - x0) * (y1 - y0) / cell_px ** 2)
    sd = np.c_[rng.uniform(x0, x1, ns), rng.uniform(y0, y1, ns)]
    col = MINERALS[rng.choice(3, ns, p=MIN_P)] * rng.uniform(0.92, 1.08, (ns, 1))
    mean = (MINERALS * np.array(MIN_P)[:, None]).sum(0)
    col = mean + contrast * (col - mean)
    yy, xx = np.mgrid[y0:y1, x0:x1]; _, j = cKDTree(sd).query(np.c_[xx.ravel() + 0.5, yy.ravel() + 0.5])
    alb = np.tile(mean, (H, W, 1)); alb[y0:y1, x0:x1] = col[j].reshape(y1 - y0, x1 - x0, 3)
    return np.clip(alb, 0, 1)


def photo_of(v, f, alb, light=LIGHT, seed=0, rast=None):
    rast = rast or oc.rasterize(v, f, CAM)
    img = oc.lambert_render(v, f, rast, light, alb)
    img = img + np.random.default_rng(seed).normal(0, 0.01, img.shape) * rast["mask"][..., None]
    return np.clip(img, 0, 1), rast


def save_png(name, img):
    try:
        from PIL import Image
        os.makedirs(IMG_DIR, exist_ok=True)
        a = np.asarray(img, float); a = (np.clip(a, 0, 1) * 255).astype(np.uint8)
        Image.fromarray(a).save(os.path.join(IMG_DIR, name))
    except Exception as e:  # pictures are for the person; the JSON is the record
        print("   (png not saved:", e, ")")


print(f"truth object: {len(VT)} verts, {len(FT)} tris, {len(set(LT.tolist()))} planar faces, scale {S:.4f}", flush=True)

# =====================================================================  0. the instrument itself
print("== instrument", flush=True)
cam0 = oc.Camera(np.eye(3), np.zeros(3), 1000, 1000, 200, 200, 400, 400)
sq = np.array([[-0.1, -0.1, 2.0], [0.1, -0.1, 2.0], [0.1, 0.1, 2.0], [-0.1, 0.1, 2.0]]) + [0.0003, 0.0002, 0]
sqf = np.array([[0, 2, 1], [0, 3, 2]])                                     # normal -z: faces the camera
r0 = oc.rasterize(sq, sqf, cam0)
area = int(r0["mask"].sum()); zc = float(r0["zfront"][200, 200])
res = dict(area_px=area, expected_px=10000, depth_centre_m=zc, **{"pass": abs(area - 10000) <= 100 and abs(zc - 2.0) < 1e-12})
case("raster", "square 0.2 m at 2 m -> 100x100 px", True, res)
# tilted plane: perspective-correct depth vs the analytic ray-plane hit
tq = np.array([[-0.3, -0.3, 1.6], [0.3, -0.3, 1.6], [0.3, 0.3, 2.4], [-0.3, 0.3, 2.4]])
r1 = oc.rasterize(tq, sqf, cam0); yy, xx = np.nonzero(r1["mask"])
dx = (xx + 0.5 - 200) / 1000; dy = (yy + 0.5 - 200) / 1000           # ray (dx, dy, 1); plane z = 2 + (4/3) y
zt = 2.0 / (1 - (0.8 / 0.6) * dy); err = float(np.abs(r1["zfront"][yy, xx] - zt).max())
case("raster", "tilted plane depth = analytic", True, dict(max_err_m=err, **{"pass": err < 1e-9}))
# box: first-exit thickness through an orthographic camera, and the inward-ray thickness
bx = np.array([[x, y, z] for x in (-0.2, 0.2) for y in (-0.15, 0.15) for z in (0.0, 0.2)])
bf = ConvexHull(bx).simplices.copy(); nt = np.cross(bx[bf[:, 1]] - bx[bf[:, 0]], bx[bf[:, 2]] - bx[bf[:, 0]])
inw = np.einsum("ij,ij->i", nt, bx[bf].mean(1) - bx.mean(0)) < 0; bf[inw] = bf[inw][:, ::-1]   # outward about the BOX centre
camo = oc.Camera.look_at((0, -3, 0.1), (0, 0, 0.1), fx=800, W=400, H=300, ortho=True)
rb = oc.rasterize(bx, bf, camo); th = (rb["zexit"] - rb["zfront"])[rb["mask"]]
case("raster", "box first-exit thickness = 0.30 m", True, dict(px=int(rb["mask"].sum()), max_err_m=float(np.abs(th - 0.3).max()),
     **{"pass": float(np.abs(th - 0.3).max()) < 1e-9 and rb["mask"].sum() > 1000}))
P, fi, N, _ = oc.surface_samples(bx, bf, 3000, 1); t = oc.ray_first_hit(bx, bf, P - 1e-9 * N, -N, skip=fi)
want = np.abs(N) @ np.array([0.4, 0.3, 0.2]); e = float(np.abs(t + 1e-9 - want).max())   # rays start 1e-9 m inside
case("raster", "box inward-ray thickness exact", True, dict(max_err_m=e, **{"pass": e < 1e-9}))
xs = oc.horizontal_extent(bx)
case("decision", "box 0.4x0.3 Feret = 0.5 m", True, dict(extent=xs["extent_m"], **{"pass": abs(xs["extent_m"] - 0.5) < 1e-9}))

# =====================================================================  photo of the truth
GRAIN_PX = 7.0
ALB = voronoi_grain(GRAIN_PX, 1)
PHOTO, RT = photo_of(VT, FT, ALB, seed=2)
PLUM = oc.luminance(PHOTO); PMASK = RT["mask"]; PLAB = np.where(PMASK, LT[np.maximum(RT["face"], 0)], -1)
save_png("photo_truth.png", PHOTO)
print(f"photo of truth: {int(PMASK.sum())} px silhouette ({time.time() - T0:.0f} s)", flush=True)

# =====================================================================  R1 silhouette
print("== R1 silhouette", flush=True)


def scaled(v, s, c=None):
    c = v.mean(0) if c is None else c
    return c + (v - c) * s


def r1(v, cam=CAM, ref=PMASK):
    return oc.silhouette_match(oc.rasterize(v, FT, cam)["mask"], ref)


case("R1", "truth", True, r1(VT))
case("R1", "scaled 0.3 % (sub-tolerance)", True, r1(scaled(VT, 1.003)))
case("R1", "outline shrunk 2 %", False, r1(scaled(VT, 0.98)), side="pass_iou")
case("R1", "outline grown 2 %", False, r1(scaled(VT, 1.02)), side="pass_iou")
vb = VT.copy(); sel = vb[:, 0] > 0.55 * vb[:, 0].max(); vb[sel, 0] += 0.008 * np.clip((vb[sel, 0] - 0.55 * vb[:, 0].max()) / (0.1 * vb[:, 0].max()), 0, 1)
case("R1", "local bulge 8 mm (contour side)", False, r1(vb), side="pass_contour", note="IoU should stay >= 0.97: only the contour p95 can see it")
camfar = oc.Camera.look_at(eye=(0.0, -2.3, 0.95), target=(0.0, 0.0, 0.17), fx=3400 / 4.5, W=W, H=H)
pm_far = oc.rasterize(VT, FT, camfar)["mask"]
case("R1", "shrunk 2 %, seen small (IoU side)", False, r1(scaled(VT, 0.98), camfar, pm_far), side="pass_iou",
     note="object ~215 px wide: a 2 % shrink moves the contour ~2 px, under 3 px; only IoU can see it")

# =====================================================================  R3 shading
print("== R3 shading", flush=True)


def model_lum(v, f, light=LIGHT):
    r = oc.rasterize(v, f, CAM); img = oc.lambert_render(v, f, r, light, 0.6)
    return img, r


def r3(v, f, lab, light=LIGHT):
    img, r = model_lum(v, f, light); lm = np.where(r["mask"], lab[np.maximum(r["face"], 0)], -1)
    return oc.shading_consistency(lm, img, PLUM)


case("R3", "truth (photo has grain + noise)", True, r3(VT, FT, LT))
# pick the face to tilt: large in the photo, lit at 45-70 deg
ids, cnt = np.unique(PLAB[PLAB >= 0], return_counts=True)
pl_n = np.array([p[0] for p in TRUTH_PLANES])
theta = np.degrees(np.arccos(np.clip(pl_n @ LIGHT, -1, 1)))
cands = [(c, i) for i, c in zip(ids, cnt) if 45 <= theta[i] <= 70]
TILT_FACE = int(max(cands)[1])


def tilted(deg, face=TILT_FACE):
    pl = [(p[0].copy(), p[1]) for p in TRUTH_PLANES]
    nn, d = pl[face]; ax = np.cross(nn, LIGHT); ax /= np.linalg.norm(ax)
    vv0, ff0, ll0 = polytope(TRUTH_PLANES); c = vv0[np.unique(ff0[ll0 == face])].mean(0)   # face centroid (unscaled)
    th = np.radians(deg); K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    Rm = np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K; n2 = Rm @ nn
    pl[face] = (n2, float(n2 @ c))
    return build(pl, S, TR)


tinfo = dict(face=TILT_FACE, face_px=int(cnt[list(ids).index(TILT_FACE)]), theta_light_deg=round(float(theta[TILT_FACE]), 1))
for deg, exp in ((2.0, True), (10.0, False), (-10.0, False)):
    vt_, ft_, lt_ = tilted(deg)
    res = r3(vt_, ft_, lt_)
    case("R3", f"face {TILT_FACE} tilted {deg:+.0f} deg", exp, res, side=None if exp else "pass_resid", note=str(tinfo))
case("R3", "light flipped", False, r3(VT, FT, LT, -LIGHT), side="pass_corr")
case("R3", "light mirrored left-right", False, r3(VT, FT, LT, LIGHT * [-1, 1, 1]), side="pass_corr")
case("R3", "light from behind-above (no front light)", False, r3(VT, FT, LT, np.array([0.2, 0.7, 0.68]) / np.linalg.norm([0.2, 0.7, 0.68])),
     side="pass_corr")

# =====================================================================  R4 colour and grain
print("== R4 colour + grain", flush=True)
MREND, _ = photo_of(VT, FT, voronoi_grain(GRAIN_PX, 101), seed=3, rast=RT)    # model: an INDEPENDENT grain realisation
save_png("model_independent_grain.png", MREND)


def shift_lab(img, dlab):
    lab = oc.srgb_to_lab(img); lab = lab + np.asarray(dlab, float); out = oc.lab_to_srgb(lab)
    return np.where(PMASK[..., None], out, img)


def r4c(img):
    return oc.colour_match(img, PHOTO, PLAB, min_px=3000)


case("R4-colour", "independent grain, same minerals", True, r4c(MREND))
case("R4-colour", "shifted dE 3 (+L)", True, r4c(shift_lab(MREND, [3, 0, 0])))
for nm, d in (("+L", [8, 0, 0]), ("-L", [-8, 0, 0]), ("+a", [0, 8, 0]), ("-b", [0, 0, -8]), ("mixed", [4.62, 4.62, 4.62])):
    case("R4-colour", f"shifted dE 8 ({nm})", False, r4c(shift_lab(MREND, d)))


def r4g(cell, contrast=1.0, seed=101):
    if cell is None:
        alb = np.tile((MINERALS * np.array(MIN_P)[:, None]).sum(0), (H, W, 1))
    else:
        alb = voronoi_grain(cell, seed, contrast)
    img, _ = photo_of(VT, FT, alb, seed=4, rast=RT)
    return oc.grain_match(oc.luminance(img), PLUM, PMASK, PLAB)


case("R4-grain", "independent realisation, same size", True, r4g(GRAIN_PX))
case("R4-grain", "grain x1.1 (sub-tolerance)", True, r4g(GRAIN_PX * 1.1))
case("R4-grain", "grain scaled x2", False, r4g(GRAIN_PX * 2), side="pass_size")
case("R4-grain", "grain scaled x0.5", False, r4g(GRAIN_PX * 0.5), side="pass_size")
case("R4-grain", "grain removed", False, r4g(None))
case("R4-grain", "grain contrast x3", False, r4g(GRAIN_PX, 3.0), side="pass_amplitude")
case("R4-grain", "grain contrast x0.3", False, r4g(GRAIN_PX, 0.3), side="pass_amplitude")

# =====================================================================  R5 solid and ground
print(f"== R5 solid + ground ({time.time() - T0:.0f} s)", flush=True)
case("R5-solid", "truth", True, oc.solid_integrity(VT, FT))
case("R5-solid", "a hole (one triangle removed)", False, oc.solid_integrity(VT, FT[1:]))
vx = VT.copy(); k = int(np.argmax(vx[:, 0])); vx[k] = CEN + 1.6 * (CEN - vx[k])
case("R5-solid", "a crossing (vertex pushed through)", False, oc.solid_integrity(vx, FT))
ff = FT.copy(); ff[0] = ff[0, ::-1]
case("R5-solid", "one face flipped", False, oc.solid_integrity(VT, ff))
tet = np.array([[2, 0, 0], [2.1, 0, 0], [2, 0.1, 0], [2, 0, 0.1]]); tf = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]) + len(VT)
case("R5-solid", "a second shell", False, oc.solid_integrity(np.r_[VT, tet], np.r_[FT, tf]))
case("R5-solid", "inside-out (all flipped)", False, oc.solid_integrity(VT, FT[:, ::-1]))

# contact-shadow mask of the truth: its visible 5 mm ground band, dilated 2 px
low = np.flatnonzero(VT[FT].min(1)[:, 2] <= oc.CONTACT_BAND)
P, fl, N, _ = oc.surface_samples(VT, FT[low], 60000, 7); fi = low[fl]
vis = oc.visible_samples(VT, FT, CAM, P, fi, RT); nb = vis & (P[:, 2] <= oc.CONTACT_BAND)
uv = np.floor(CAM.project(P[nb])[:, :2]).astype(int)
SHADOW = np.zeros((H, W), bool); SHADOW[uv[:, 1], uv[:, 0]] = True; SHADOW = ndimage.binary_dilation(SHADOW, iterations=2)
save_png("shadow_mask.png", SHADOW.astype(float))


def r5g(v):
    return oc.ground_contact(v, FT, CAM, SHADOW)


def moved(dv):
    return VT + np.asarray(dv, float)


case("R5-ground", "truth", True, r5g(VT))
case("R5-ground", "lifted 0.5 mm (sub-tolerance)", True, r5g(moved([0, 0, 0.0005])))
case("R5-ground", "lifted 3 mm (floating)", False, r5g(moved([0, 0, 0.003])), side="pass_height")
case("R5-ground", "sunk 3 mm (sinking)", False, r5g(moved([0, 0, -0.003])), side="pass_height")
case("R5-ground", "contact displaced 4 cm sideways", False, r5g(moved([0.04, 0, 0])), side="pass_place")
ang = np.radians(8); Rx = np.array([[1, 0, 0], [0, np.cos(ang), -np.sin(ang)], [0, np.sin(ang), np.cos(ang)]])
vr = (VT - CEN) @ Rx.T + CEN; vr[:, 2] -= vr[:, 2].min()
case("R5-ground", "rocked 8 deg (touches elsewhere)", False, r5g(vr), side="pass_place")

# =====================================================================  R6 thickness and mirror
print(f"== R6 thickness + mirror ({time.time() - T0:.0f} s)", flush=True)
res, _ = oc.thickness_check(VT, FT, CAM)
case("R6-thick", "truth", True, res)
DVIS = res["visible_depth_m"]
# paper-thin back: the visible front patch, closed by a copy 3 % of the visible depth behind it
eye = CAM.eye; nt = oc.face_normals(VT, FT)
patch = np.einsum("ij,ij->i", nt, VT[FT].mean(1) - eye) < 0
pf = FT[patch]; used = np.unique(pf); mp = -np.ones(len(VT), int); mp[used] = np.arange(len(used))
pv = VT[used]; dirs = (pv - eye) / np.linalg.norm(pv - eye, axis=1, keepdims=True)
delta = 0.03 * DVIS; nv = len(pv); sv = np.r_[pv, pv + delta * dirs]
fpatch = mp[pf]; back = fpatch[:, ::-1] + nv
de = np.r_[fpatch[:, [0, 1]], fpatch[:, [1, 2]], fpatch[:, [2, 0]]]
key = np.sort(de, 1); u_, inv_, c_ = np.unique(key, axis=0, return_inverse=True, return_counts=True)
bd = de[c_[inv_.ravel()] == 1]
side_f = np.r_[np.c_[bd[:, 1], bd[:, 0], bd[:, 0] + nv], np.c_[bd[:, 1], bd[:, 0] + nv, bd[:, 1] + nv]]
SHELL_F = np.r_[fpatch, back, side_f]
case("R5-solid", "paper-thin back is still a sound solid", True, oc.solid_integrity(sv, SHELL_F),
     note="R5 cannot see a paper-thin back; R6 must")
res, _ = oc.thickness_check(sv, SHELL_F, CAM)
case("R6-thick", "paper-thin back (3 % of visible depth)", False, res)
vf = VT.copy(); x0 = 0.45 * vf[:, 0].max(); s_ = 1 - 0.94 * np.clip((vf[:, 0] - x0) / 0.08, 0, 1)
vf[:, 1] = CEN[1] + (vf[:, 1] - CEN[1]) * s_
res, _ = oc.thickness_check(vf, FT, CAM)
case("R6-thick", "thin flange at one end", False, res)
vfm = VT.copy(); x0 = 0.80 * vfm[:, 0].max(); s_ = 1 - 0.5 * np.clip((vfm[:, 0] - x0) / 0.05, 0, 1)
vfm[:, 1] = CEN[1] + (vfm[:, 1] - CEN[1]) * s_
res, _ = oc.thickness_check(vfm, FT, CAM)
case("R6-thick", "end narrowed to 50 % (not a sliver)", True, res)

case("R6-mirror", "truth (independent back)", True, oc.mirror_similarity(VT, FT, CAM))
v2, f2, _ = build(FRONT + [p for p in rand_planes(40, 77) if p[0][1] > 0] + BOTTOM, S, TR)
case("R6-mirror", "another independent back", True, oc.mirror_similarity(v2, f2, CAM))


def mirrored(a=np.array([0.0, 1.0, 0.0]), c0=0.0):
    a = a / np.linalg.norm(a); pl = []
    for nn, d in FRONT + BOTTOM:
        pl.append((nn, d))
        if nn @ a < -1e-6:
            n2 = nn - 2 * (nn @ a) * a; pl.append((n2, d - 2 * (nn @ a) * c0))
    return build(pl, S, TR)


vm, fm, _ = mirrored()
case("R6-mirror", "mirrored back (plane normal y)", False, oc.mirror_similarity(vm, fm, CAM))
vm2, fm2, _ = mirrored(np.array([np.sin(np.radians(7)), np.cos(np.radians(7)), 0.0]), 0.02)
case("R6-mirror", "mirrored back, plane turned 7 deg + 2 cm", False, oc.mirror_similarity(vm2, fm2, CAM))
vj = vm + np.random.default_rng(5).normal(0, 0.001, vm.shape)
case("R6-mirror", "mirrored back + 1 mm jitter", False, oc.mirror_similarity(vj, fm, CAM))

# HELD-OUT (A23), declared before the v3 run that added the point-to-plane polish: objects and planes never used
# while the mirror score was being designed. Threshold MIRROR_MAX = 0.5 is unchanged from v1.
v3_, f3_, _ = build(FRONT + [p for p in rand_planes(40, 123) if p[0][1] > 0] + BOTTOM, S, TR)
case("R6-mirror", "HELD-OUT independent back (seed 123)", True, oc.mirror_similarity(v3_, f3_, CAM))
vm3, fm3, _ = mirrored(np.array([np.sin(np.radians(-10)), np.cos(np.radians(-10)), 0.0]), -0.03)
vm3 = vm3 + np.random.default_rng(9).normal(0, 0.0007, vm3.shape)
case("R6-mirror", "HELD-OUT mirror turned -10 deg, -3 cm, 0.7 mm jitter", False, oc.mirror_similarity(vm3, fm3, CAM))
FRONT_B = [p for p in rand_planes(40, 31) if p[0][1] <= 0]
vB, fB, _ = build(FRONT_B + [p for p in rand_planes(40, 32) if p[0][1] > 0] + BOTTOM, S, TR)
case("R6-mirror", "HELD-OUT 2nd object, independent back", True, oc.mirror_similarity(vB, fB, CAM))
plB = []
for nn, d in FRONT_B + BOTTOM:
    plB.append((nn, d))
    if nn[1] < -1e-6:
        plB.append((nn * [1, -1, 1], d))
vBm, fBm, _ = build(plB, S, TR)
case("R6-mirror", "HELD-OUT 2nd object, mirrored back", False, oc.mirror_similarity(vBm, fBm, CAM))

# =====================================================================  decisions
print(f"== decisions ({time.time() - T0:.0f} s)", flush=True)
case("D-extent", "truth 0.70 m", True, oc.horizontal_extent(VT))
for s_, exp in ((0.96, True), (1.04, True), (0.94, False), (1.06, False)):
    case("D-extent", f"scaled x{s_}", exp, oc.horizontal_extent(scaled(VT, s_)))
ang = np.radians(40); Rz = np.array([[np.cos(ang), -np.sin(ang), 0], [np.sin(ang), np.cos(ang), 0], [0, 0, 1]])
rb_ = np.array([[x, y, z] for x in (-0.31, 0.31) for y in (-0.2, 0.2) for z in (0, 0.2)]) @ Rz.T
res = oc.horizontal_extent(rb_)
case("D-extent", "0.62x0.40 rotated 40 deg (bbox trap)", False, res,
     note=f"bbox x {res['bbox_x_m']} m would pass a bbox check; the Feret diameter {res['extent_m']} m fails")
clean = [{"name": "Rock1_mesh", "type": "MESH", "modifiers": ["SUBSURF"], "parent_type": None, "constraints": []}]
case("D-armature", "clean mesh", True, oc.no_armature(clean))
case("D-armature", "an armature object", False, oc.no_armature(clean + [{"name": "Rig", "type": "ARMATURE"}]))
case("D-armature", "an armature modifier", False, oc.no_armature([dict(clean[0], modifiers=["ARMATURE"])]))
case("D-armature", "parented to an armature", False, oc.no_armature([dict(clean[0], parent_type="ARMATURE")]))
case("D-armature", "armature constraint", False, oc.no_armature([dict(clean[0], constraints=["ARMATURE"])]))
case("D-armature", "empty inventory (nothing checked)", False, oc.no_armature([]))

# =====================================================================  write
ok = all(c["ok"] for c in CASES)
summary = {}
for c in CASES:
    s = summary.setdefault(c["check"], {"cases": 0, "ok": 0}); s["cases"] += 1; s["ok"] += int(c["ok"])
out = {"tool": "engine/checks/object_checks.py", "prover": "engine/checks/object_checks_prove.py",
       "made": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(time.time() - T0, 1), "all_ok": bool(ok), "summary": summary,
       "test_object": {"kind": "faceted ellipsoid = intersection of half-spaces tangent to an ellipsoid (synthetic, not the rock)",
                       "semi_axes_m_before_scale": AX.tolist(), "planes": len(TRUTH_PLANES), "triangles": int(len(FT)),
                       "largest_horizontal_extent_m": 0.70, "camera": {"W": W, "H": H, "fx": 3400, "eye": [0, -2.3, 0.95], "target": [0, 0, 0.17]},
                       "light_towards": np.round(LIGHT, 4).tolist(), "grain_cell_px": GRAIN_PX, "photo_noise_sd": 0.01,
                       "silhouette_px": int(PMASK.sum())},
       "cases": CASES}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as fh:
    json.dump(out, fh, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
print(f"\n{sum(c['ok'] for c in CASES)}/{len(CASES)} cases OK -> {OUT} ({time.time() - T0:.0f} s)")
