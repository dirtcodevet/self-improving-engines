"""STUDIO PHOTO FIT (domain-neutral): one product-style photo of an object on a plain white sweep ->
object mask, cast-shadow mask, pinhole camera and light, each with its evidence and label.

  mask      texture energy (the object is textured, the shadow and sweep are smooth) -> coarse mask, then the
            boundary band is snapped to the half-amplitude luminance threshold where the outside is BRIGHT (sweep);
            where the outside is DARK (contact shadow) the texture boundary is kept.
  shadow    smoothed luminance more than DELTA below the sweep level, outside the object, connected to it.
  contact   per column, the darkest smooth luminance trough found from the profile SHAPE alone, scanning up from
            the image bottom (never uses the mask, so the mask's bottom can be tested against it).
  camera    pinhole; focal from a stated prior; pitch from the outer-shadow ellipse aspect (isotropic footprint
            assumption); scale from the person's extent decision; Blender convention (as tripo_rebuild/
            pigment_project.py: matrix_world = T(location) @ rot_matrix, columns = cam x right, y up, z back;
            f_px = lens / sensor_width * W; principal point at the image centre).
  light     occluding-contour Lambertian fit (normals at the silhouette are known exactly: in the image plane,
            perpendicular to the contour) gives the image-plane light direction and ambient; the shadow's
            sideways offset gives the azimuth sign; world elevation estimated.

usage: python studio_photo_fit.py <photo> <case_dir> --extent-m 0.70 --centre-x -1.25 --centre-y 0
"""
import json, os, sys, argparse
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.optimize import least_squares

# ---- settings (all stated; none tuned on held-out data)
HP_SIGMA, E_SIGMA, E_THRESH = 1.0, 1.0, 3.5      # texture energy (rock grain ~10-25, sweep/shadow ~1)
BAND = 8                                          # boundary band (px) re-decided by the luminance snap
SHADOW_DELTA = 4.0                                # shadow.png: smoothed L below sweep level by > 4 levels (~5 sigma noise)
SHADOW_DELTA_CONTOUR = 10.0                       # iso-level used for the outer-shadow ellipse (H3)
FOCAL_PRIOR_MM, SENSOR_MM, FOCAL_RANGE_MM = 85.0, 36.0, (50.0, 200.0)
N_ARCS = 24
TROUGH_MAX, TROUGH_RUN = 0.2, 15                  # contact trough: near-black and a continuous line (see contact_trough)


def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def load(photo):
    im = np.asarray(Image.open(photo).convert("RGB")).astype(float)
    return im, im.mean(2)


def sweep_level(L):
    return float(np.median(np.concatenate([L[:40].ravel(), L[-40:].ravel(), L[:, :40].ravel(), L[:, -40:].ravel()])))


def texture_energy(L, hp_sigma=HP_SIGMA, e_sigma=E_SIGMA):
    hp = L - ndi.gaussian_filter(L, hp_sigma)
    return np.sqrt(ndi.gaussian_filter(hp * hp, e_sigma))


def largest(m):
    lab, n = ndi.label(m)
    if n == 0:
        return m
    sz = ndi.sum(m, lab, range(1, n + 1))
    return lab == (1 + int(np.argmax(sz)))


def object_mask(L):
    E = texture_energy(L)
    m = E > E_THRESH
    m = ndi.binary_closing(m, disk(4))
    m = ndi.binary_fill_holes(m)
    m = largest(ndi.binary_opening(largest(m), disk(2)))
    coarse = m.copy()
    # boundary snap where the outside is bright
    core = ndi.binary_erosion(m, disk(BAND))
    out = ~ndi.binary_dilation(m, disk(2))
    k = 2 * BAND + 1
    box = lambda a: ndi.uniform_filter(a.astype(float), k)
    in_mean = box(L * core) / np.maximum(box(core), 1e-6)
    in_ok = box(core) > 0.02
    out_mean = box(L * out) / np.maximum(box(out), 1e-6)
    out_ok = box(out) > 0.02
    band = m & ~core
    bright = out_ok & (out_mean > np.where(in_ok, in_mean, L) + 40)
    thr = 0.5 * (np.where(in_ok, in_mean, 100.0) + out_mean)
    drop = band & bright & (L > thr)
    # where the outside is NOT bright (contact shadow), the closing can bridge into the smooth flank of the contact
    # trough: drop band pixels that are not textured themselves (v2 fix; defect found by H2: mask 4-8 px below the
    # contact line in 18 columns). Uses texture only - never the contact trough - so H2 stays a hold-out test.
    # v3: the trough flank has E 3.5-6 (curvature + JPEG), so the bar is the object's OWN texture level: the 5th
    # percentile of E in the object's interior (7.0 on rock1), measured on the coarse mask, never on the shadow.
    e_obj_p5 = float(np.percentile(E[ndi.binary_erosion(m, disk(15))], 5))
    drop |= band & ~bright & (E < e_obj_p5) & ndi.binary_dilation(~m, disk(3))
    m = m & ~drop
    m = ndi.binary_closing(m, disk(2))            # re-close notches cut by bright rim grains
    m = largest(ndi.binary_fill_holes(m))
    return m, coarse, E


def shadow_mask(L, mask, delta=SHADOW_DELTA):
    bg = sweep_level(L)
    # normalised convolution over NON-object pixels only: a plain blur leaks the object's darkness into a 3-4 px halo
    # all round the silhouette (seen on rock1's top edge, v1), which is not shadow
    w = (~mask).astype(float)
    Ls = ndi.gaussian_filter(L * w, 2.0) / np.maximum(ndi.gaussian_filter(w, 2.0), 1e-6)
    s = (Ls < bg - delta) & ~mask
    # the 1-3 px ring of anti-aliased edge pixels (part object, part sweep) is darker than the sweep all round the
    # silhouette: it is not cast shadow. Opening with a disk(3) removes any ring thinner than ~6 px; a real cast
    # shadow is tens of px wide and survives.
    s = ndi.binary_opening(s, disk(3))
    lab, n = ndi.label(s)
    ring = ndi.binary_dilation(mask, disk(5)) & s
    keep = np.unique(lab[ring])
    keep = keep[keep > 0]
    s = np.isin(lab, keep)
    strength = np.clip((bg - Ls) / bg, 0, 1) * s
    return s, strength


def contact_trough(L, x0, x1):
    """per column: scan up from the image bottom through the smooth shadow; the first local minimum of the smoothed
    profile that is < 0.5 x sweep and rises by >= 60 levels over the 15 px below it is the contact trough.
    Uses luminance profile shape only (no texture, no mask)."""
    bg = sweep_level(L)
    Ls = ndi.gaussian_filter(L, 1.5)
    H = L.shape[0]
    cols, rows = [], []
    for c in range(x0, x1 + 1):
        p = Ls[:, c]
        r = H - 2
        # climb up while the profile is non-increasing (moving up into the shadow) with small tolerance
        while r > 1 and p[r - 1] <= p[r] + 1.5:
            r -= 1
        # r is a local minimum (going up, the next pixel is brighter). A contact trough is near-black (< 0.2 x sweep:
        # occlusion is total at the contact) and the ground shadow below it brightens monotonically.
        if (p[r] < TROUGH_MAX * bg and r + 15 < H and p[r + 15] - p[r] >= 60
                and np.all(np.diff(p[r:r + 13]) > -0.5)):
            cols.append(c); rows.append(r)
    cols, rows = np.array(cols), np.array(rows)
    # continuity: keep runs of >= TROUGH_RUN columns (gaps <= 3 columns allowed: the flat-bottomed minimum is sampled
    # per column and a few columns sit just above the darkness limit) whose rows step <= 3 px (a LINE, not a grain).
    # v1 (strict: no gaps, step <= 2) kept 73 of 344 candidate columns - a detector bug seen on the profiles at
    # columns 700-890; fixed after the first H2 run, H2 thresholds unchanged (recorded in camera_validation.json).
    keep = np.zeros(len(cols), bool)
    i = 0
    while i < len(cols):
        j = i
        while (j + 1 < len(cols) and cols[j + 1] - cols[j] <= 4
               and abs(int(rows[j + 1]) - int(rows[j])) <= 3):
            j += 1
        if cols[j] - cols[i] + 1 >= TROUGH_RUN:
            keep[i:j + 1] = True
        i = j + 1
    return cols[keep], rows[keep]


def boundary_points(m, exclude=None):
    b = m & ~ndi.binary_erosion(m)
    if exclude is not None:
        b &= ~exclude
    ys, xs = np.nonzero(b)
    return xs.astype(float), ys.astype(float)


def fit_ellipse_aa(xs, ys):
    """axis-aligned ellipse ((x-u)/a)^2 + ((y-v)/b)^2 = 1, geometric-ish fit by least squares on the algebraic
    residual normalised by the gradient."""
    u0, v0 = xs.mean(), ys.mean()
    a0, b0 = (xs.max() - xs.min()) / 2, (ys.max() - ys.min())

    def res(p):
        u, v, a, b = p
        X, Y = (xs - u) / a, (ys - v) / b
        r = np.sqrt(X * X + Y * Y)
        return (r - 1) * np.sqrt((a * X) ** 2 + (b * Y) ** 2) / np.maximum(r, 1e-9)
    sol = least_squares(res, [u0, v0 - b0 / 2, a0, b0 / 2], loss="soft_l1", f_scale=3.0)
    u, v, a, b = sol.x
    return dict(u=float(u), v=float(v), a=float(abs(a)), b=float(abs(b)),
                rms_px=float(np.sqrt(np.mean(res(sol.x) ** 2))))


# ------------------------------------------------------------------ camera
def make_camera(W, H, f_px, pitch_rad, G, uv_G, depth_G):
    s, c = np.sin(pitch_rad), np.cos(pitch_rad)
    x_cam = np.array([1.0, 0, 0]); y_cam = np.array([0, s, c]); z_cam = np.array([0, -c, s])
    M = np.stack([x_cam, y_cam, z_cam], 1)       # columns
    dc = np.array([(uv_G[0] - W / 2) / f_px, -(uv_G[1] - H / 2) / f_px, -1.0])
    C = np.asarray(G, float) - depth_G * (M @ dc)
    return C, M


def project(P, C, M, f_px, W, H):
    pc = (np.atleast_2d(P) - C) @ M
    z = -pc[:, 2]
    return np.stack([W / 2 + f_px * pc[:, 0] / z, H / 2 - f_px * pc[:, 1] / z], 1), z


def euler_xyz_from_matrix(M):
    """Blender XYZ euler (R = Rz @ Ry @ Rx)"""
    sy = -M[2, 0]
    y = np.arcsin(np.clip(sy, -1, 1))
    x = np.arctan2(M[2, 1], M[2, 2])
    z = np.arctan2(M[1, 0], M[0, 0])
    return [float(x), float(y), float(z)]


# ------------------------------------------------------------------ light (occluding contour)
def contour_samples(L, mask, depth_in=(3, 10)):
    """ordered outer contour with outward unit normals (image coords, y up) and the median luminance in a band
    depth_in px inside along the inward normal."""
    import cv2
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=len)[:, 0, :].astype(float)            # (N,2) x,y (y down)
    # smooth contour, tangents
    k = 9
    cx = ndi.uniform_filter1d(c[:, 0], k, mode="wrap"); cy = ndi.uniform_filter1d(c[:, 1], k, mode="wrap")
    tx = np.gradient(cx); ty = np.gradient(cy)
    tn = np.hypot(tx, ty) + 1e-9
    tx, ty = tx / tn, ty / tn
    # outward normal: test both perpendiculars against the mask
    nx, ny = ty, -tx                                         # image coords (y down)
    probe = np.stack([cx + 4 * nx, cy + 4 * ny], 1).round().astype(int)
    probe[:, 0] = probe[:, 0].clip(0, mask.shape[1] - 1); probe[:, 1] = probe[:, 1].clip(0, mask.shape[0] - 1)
    inside = mask[probe[:, 1], probe[:, 0]]
    flip = inside.mean() > 0.5
    if flip:
        nx, ny = -nx, -ny
    Lm = ndi.median_filter(L, 3)
    vals = []
    for d in range(depth_in[0], depth_in[1] + 1):
        px = (cx - d * nx).round().astype(int).clip(0, mask.shape[1] - 1)
        py = (cy - d * ny).round().astype(int).clip(0, mask.shape[0] - 1)
        v = Lm[py, px].astype(float)
        v[~mask[py, px]] = np.nan
        vals.append(v)
    I = np.nanmedian(np.array(vals), 0)
    I = ndi.uniform_filter1d(np.nan_to_num(I, nan=np.nanmedian(I)), 15, mode="wrap")  # average grain along the contour
    s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(cx), np.diff(cy)))])
    return dict(x=cx, y=cy, nx=nx, ny=-ny, I=I, s=s)       # ny returned with y UP


def lambert_contour(p, nx, ny):
    a0, gx, gy = p
    return a0 + np.maximum(0.0, gx * nx + gy * ny)


def fit_contour_light(cs, sel):
    nx, ny, I = cs["nx"][sel], cs["ny"][sel], cs["I"][sel]
    best = None
    for ang in np.linspace(0, 2 * np.pi, 8, endpoint=False):
        p0 = [np.percentile(I, 20), 60 * np.cos(ang), 60 * np.sin(ang)]
        sol = least_squares(lambda p: lambert_contour(p, nx, ny) - I, p0, loss="soft_l1", f_scale=10.0)
        if best is None or sol.cost < best.cost:
            best = sol
    return best.x


def arcs_split(cs, n=N_ARCS):
    s = cs["s"]
    arc = np.minimum((s / s[-1] * n).astype(int), n - 1)
    return arc % 2 == 0, arc % 2 == 1


def light_holdout(cs, p, test):
    pred = lambert_contour(p, cs["nx"][test], cs["ny"][test])
    obs = cs["I"][test]
    r = float(np.corrcoef(pred, obs)[0, 1]) if pred.std() > 1e-9 else 0.0
    rmse = float(np.sqrt(np.mean((pred - obs) ** 2)))
    rmse0 = float(np.sqrt(np.mean((obs - obs.mean()) ** 2)))
    return dict(r=r, rmse=rmse, rmse_const=rmse0, ratio=rmse / rmse0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo"); ap.add_argument("case")
    ap.add_argument("--extent-m", type=float, default=0.70)
    ap.add_argument("--centre-x", type=float, default=-1.25); ap.add_argument("--centre-y", type=float, default=0.0)
    a = ap.parse_args()
    im, L = load(a.photo)
    H, W = L.shape
    bg = sweep_level(L)
    out = {}

    # ---- mask + shadow
    mask, coarse, E = object_mask(L)
    shadow, strength = shadow_mask(L, mask)
    Image.fromarray((mask * 255).astype(np.uint8)).save(os.path.join(a.case, "mask.png"))
    Image.fromarray((shadow * 255).astype(np.uint8)).save(os.path.join(a.case, "shadow.png"))
    Image.fromarray(np.clip(strength * 255 / max(strength.max(), 1e-6), 0, 255).astype(np.uint8)).save(
        os.path.join(a.case, "shadow_strength.png"))
    ys, xs = np.nonzero(mask)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    width_px = x1 - x0 + 1

    # ---- contact trough (fit set for H2) and outer shadow ellipse (fit set for H3)
    cc, cr = contact_trough(L, x0, x1)
    np.save(os.path.join(a.case, "contact_trough.npy"), np.stack([cc, cr], 1))
    sh10, _ = shadow_mask(L, mask, SHADOW_DELTA_CONTOUR)
    near_obj = ndi.binary_dilation(mask, disk(4))
    sx, sy = boundary_points(sh10, exclude=near_obj)
    ell = fit_ellipse_aa(sx, sy)
    np.save(os.path.join(a.case, "shadow_outer_pts.npy"), np.stack([sx, sy], 1))

    # ---- camera
    f_px = FOCAL_PRIOR_MM / SENSOR_MM * W
    ratio = ell["b"] / ell["a"]
    theta_ray = float(np.arcsin(np.clip(ratio, 0, 1)))
    uv_G = ((x0 + x1) / 2.0, ell["v"])
    pitch = theta_ray - float(np.arctan((uv_G[1] - H / 2) / f_px))
    depth_G = a.extent_m * f_px / width_px
    G = np.array([a.centre_x, a.centre_y, 0.0])
    C, M = make_camera(W, H, f_px, pitch, G, uv_G, depth_G)
    th_lo = float(np.degrees(np.arcsin(np.clip(ratio / 1.33, 0, 1))))
    th_hi = float(np.degrees(np.arcsin(np.clip(ratio / 0.75, 0, 1))))
    cam = dict(
        convention="Blender: matrix_world = T(location) @ rot_matrix; rot_matrix columns = camera x right, y up, z back "
                   "(world); f_px = lens / sensor_width * W; principal point at the image centre; pixel centres at integers. "
                   "Same as tripo_rebuild/pigment_project.py load_camera/project.",
        world="z up, metres, ground z = 0; object centred at x %.2f y %.2f; camera on the -y side looking +y" % (a.centre_x, a.centre_y),
        image_size=[W, H], lens=FOCAL_PRIOR_MM, sensor_width=SENSOR_MM, sensor_fit="HORIZONTAL", f_px=f_px,
        location=C.tolist(), rot_matrix=M.tolist(), rotation_euler_xyz=euler_xyz_from_matrix(M),
        pitch_deg_below_horizontal=float(np.degrees(pitch)),
        ground_view_elevation_deg_at_object=float(np.degrees(theta_ray)),
        distance_to_object_centre_m=float(np.linalg.norm(G - C)),
        object_centre_ground_px=list(map(float, uv_G)),
        labels=dict(
            focal="ESTIMATED: prior %g mm on a %g mm full-frame sensor (3:2 frame matches 1728x1152); plausible %g-%g mm "
                  "(studio tabletop product shots: 50 mm normal to 100-200 mm macro/tele). One photo of an unknown object "
                  "has no usable perspective cue, so it cannot be fitted or held out. Distance scales with it "
                  "(%.2f-%.2f m); pitch and scale do not (weak perspective)." % (
                      FOCAL_PRIOR_MM, SENSOR_MM, FOCAL_RANGE_MM[0], FOCAL_RANGE_MM[1],
                      depth_G * FOCAL_RANGE_MM[0] / FOCAL_PRIOR_MM, depth_G * FOCAL_RANGE_MM[1] / FOCAL_PRIOR_MM),
            pitch="ESTIMATED: outer shadow iso-contour ellipse aspect b/a = %.3f -> view elevation %.1f deg at the object, "
                  "assuming the shadow footprint is as deep as it is wide; range %.1f-%.1f deg for footprint aspect 0.75-1.33. "
                  "Consistency-tested (H3), not hold-out-provable." % (ratio, np.degrees(theta_ray), th_lo, th_hi),
            scale="DECISION (person, 2026-10-18): largest horizontal extent 0.70 m. Applied to the silhouette width "
                  "(%d px) at the object-centre depth: ASSUMES the across-view extent is the largest; the unseen depth "
                  "extent is estimated later and, if larger, the scale must be re-applied." % width_px,
            ground_row="ESTIMATED: the ground point under the object centre is the outer-shadow ellipse centre row "
                       "(%.1f px); a light offset toward/away from the camera would shift it." % ell["v"],
            azimuth="FREE CHOICE (no evidence in one photo): camera on the -y side looking +y.")
    )
    json.dump(cam, open(os.path.join(a.case, "camera.json"), "w"), indent=2)

    # ---- light
    cs = contour_samples(L, mask)
    fit_sel, test_sel = arcs_split(cs)
    p = fit_contour_light(cs, fit_sel)
    hold = light_holdout(cs, p, test_sel)
    a0, gx, gy = map(float, p)
    phi_img = float(np.degrees(np.arctan2(gy, gx)))      # 0 = image right, 90 = image up
    # shadow sideways offset: outer shadow ellipse centre vs silhouette centre (image x); shadow lies AWAY from light
    dx_shadow_px = ell["u"] - (x0 + x1) / 2.0
    # world light direction: l = (lx, ly, lz); image-plane comps: lx, s*ly + c*lz  (s,c of pitch)
    s_, c_ = np.sin(pitch), np.cos(pitch)
    cands = []
    for e in np.radians(np.arange(5, 90.1, 0.5)):
        for az in np.radians(np.arange(0, 360, 1.0)):
            l = np.array([np.cos(e) * np.cos(az), np.cos(e) * np.sin(az), np.sin(e)])
            ix, iy = l[0], s_ * l[1] + c_ * l[2]
            dang = np.degrees(np.angle(np.exp(1j * (np.arctan2(iy, ix) - np.radians(phi_img)))))
            cands.append((abs(dang), e, az, l))
    cands.sort(key=lambda t: t[0])
    ok = [t for t in cands if t[0] < 2.0]
    # among directions matching the image-plane direction, prefer: lighting the camera side (ly < 0, front key,
    # the usual product set-up) and the sideways shadow offset sign; report the elevation spread
    front = [t for t in ok if t[3][1] <= 0]
    pick_from = front if front else ok
    # sideways: shadow offset dx (px) -> light x-component sign opposite to dx
    if abs(dx_shadow_px) > 5:
        pick_from = [t for t in pick_from if np.sign(t[3][0]) == -np.sign(dx_shadow_px)] or pick_from
    elev = np.array([np.degrees(t[1]) for t in pick_from])
    # central estimate: median elevation of the admissible set
    mid = pick_from[int(np.argsort(elev)[len(elev) // 2])]
    lw = mid[3]
    light = dict(
        model="key light (distant, Lambertian response) + uniform ambient; luminance 0-255 of the photo",
        direction_world_to_light=lw.tolist(),
        elevation_deg=float(np.degrees(mid[1])), azimuth_deg_from_plus_x=float(np.degrees(mid[2])),
        elevation_range_deg=[float(elev.min()), float(elev.max())],
        image_plane_direction_deg=phi_img,
        contour_fit=dict(ambient_a0=a0, gx=gx, gy=gy, key_over_ambient=float(np.hypot(gx, gy) / max(a0, 1e-6)),
                         ambient_fraction=float(a0 / (a0 + np.hypot(gx, gy)))),
        shadow=dict(outer_ellipse=ell, sideways_offset_px=float(dx_shadow_px),
                    note="shadow centred under the object within %.0f px -> key light close to overhead/frontal; soft "
                         "edges (penumbra tens of px) -> large source (softbox)" % abs(dx_shadow_px)),
        holdout_H1=hold,
        labels=dict(
            image_plane_direction="CHECKED by H1 hold-out (odd contour arcs)",
            ambient_fraction="CHECKED by H1 (same fit)",
            elevation_azimuth="ESTIMATED: the occluding contour fixes only the image-plane direction; the light's "
                              "toward-camera component is chosen as a front key (camera side) and the elevation is the "
                              "median of the admissible set; range given",
            highlights="UNCHECKED: the rock is matte granular; specular glints are grain-sized and were not used")
    )
    json.dump(light, open(os.path.join(a.case, "light.json"), "w"), indent=2)
    np.savez(os.path.join(a.case, "contour_samples.npz"), **cs)

    summary = dict(bbox=[x0, x1, y0, y1], width_px=width_px, sweep=bg, ellipse=ell, n_contact=len(cc),
                   pitch_deg=float(np.degrees(pitch)), theta_ray_deg=float(np.degrees(theta_ray)),
                   light_img_deg=phi_img, holdout_H1=hold, cam_loc=C.tolist())
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
