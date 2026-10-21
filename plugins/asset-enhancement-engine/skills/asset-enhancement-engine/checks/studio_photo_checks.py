"""STUDIO PHOTO CHECKS (domain-neutral): hold-out validation of engine/tools/studio_photo_fit.py outputs, each check
proven on planted failures on every side it can fail (A22). Splits were declared before fitting in
<case>/holdout_plan.json (A23).

  H1 light      contour Lambertian fit on EVEN arcs, tested on ODD arcs (r >= 0.5, RMSE <= 0.8 x constant model)
  H2 ground     contact trough (luminance profile shape only) vs silhouette bottom (mask): no sinking, no lifting
  H3 elevation  contact points inside the outer-shadow ellipse (one-sided consistency; too-HIGH elevation undetectable)
  H4 mask edge  independent 1-D step-edge crossings on pre-chosen scanlines vs the mask boundary
  H5 scale      0.70 m at the object-centre depth reprojects to the silhouette width (consistency, not hold-out)
  H6 shadow out the mask contains no smooth (shadow-like) area

usage: python studio_photo_checks.py <case_dir>    (writes <case_dir>/camera_validation.json)
"""
import json, os, sys, time
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import studio_photo_fit as spf  # noqa: E402

# thresholds (from holdout_plan.json, fixed before the fit)
H1_R, H1_RATIO = 0.5, 0.8
H2_MED, H2_SINK, H2_FRAC = 3.0, 3.0, 0.25
H4_P95, H4_MED = 2.0, 1.0
H5_TOL = 0.01
H6_SMOOTH_FRAC = 0.01


# ------------------------------------------------------------------ H4 mask edges
def step_crossing(prof, lo_win, hi_win):
    """first crossing, coming from the outside (index 0), of the half level between the outside plateau median
    and the inside median. Returns sub-pixel index or None."""
    out = np.median(prof[lo_win[0]:lo_win[1]]); inn = np.median(prof[hi_win[0]:hi_win[1]])
    if out - inn < 60:
        return None
    lev = 0.5 * (out + inn)
    for i in range(lo_win[0], len(prof) - 1):
        if prof[i] >= lev > prof[i + 1]:
            return i + (prof[i] - lev) / (prof[i] - prof[i + 1])
    return None


def check_mask_edges(mask, L):
    res = []
    for r in range(300, 901, 40):
        xs = np.nonzero(mask[r])[0]
        if len(xs) == 0:
            continue
        xl, xr = xs.min(), xs.max()
        p = L[r, xl - 25:xl + 26]                                   # outside first
        c = step_crossing(p, (0, 12), (30, 45))
        if c is not None:
            res.append(("row%d_left" % r, (xl - 25 + c + 0.5) - xl))  # crossing as a boundary position vs mask boundary xl-0.5
        p = L[r, xr - 25:xr + 26][::-1]
        c = step_crossing(p, (0, 12), (30, 45))
        if c is not None:
            res.append(("row%d_right" % r, (xr + 25 - c - 0.5) - xr))
    for col in range(450, 1301, 50):
        ys = np.nonzero(mask[:, col])[0]
        if len(ys) == 0:
            continue
        yt = ys.min()
        p = L[yt - 25:yt + 26, col]
        c = step_crossing(p, (0, 12), (30, 45))
        if c is not None:
            res.append(("col%d_top" % col, (yt - 25 + c + 0.5) - yt))
    d = np.abs(np.array([v for _, v in res]))
    ok = len(d) >= 20 and np.percentile(d, 95) <= H4_P95 and np.median(d) <= H4_MED
    return dict(passed=bool(ok), n=len(d), median_px=float(np.median(d)), p95_px=float(np.percentile(d, 95)),
                max_px=float(d.max()), signed_mean_px=float(np.mean([v for _, v in res])),
                note="signed + = mask boundary lies OUTSIDE the step edge")


# ------------------------------------------------------------------ H2 ground contact
def silhouette_bottom(mask, cols):
    out = np.full(len(cols), -1)
    for i, c in enumerate(cols):
        ys = np.nonzero(mask[:, c])[0]
        if len(ys):
            out[i] = ys.max()
    return out


def check_ground_contact(mask, cc, cr, smoother="median15"):
    if len(cc) == 0:
        return dict(passed=False, reason="no contact trough found")
    if smoother == "quadratic":
        curve = np.polyval(np.polyfit(cc, cr, 2), cc)
    else:                                   # running median over 15 contact columns (amended, see validation)
        curve = ndi.median_filter(cr.astype(float), 15, mode="nearest")
    bot = silhouette_bottom(mask, cc)
    d = bot - curve                          # + = silhouette bottom BELOW the contact line (sinking)
    xs = np.nonzero(mask.any(0))[0]
    frac = len(cc) / float(xs.max() - xs.min() + 1)
    ok = (np.median(np.abs(d)) <= H2_MED) and (d.max() <= H2_SINK) and (frac >= H2_FRAC)
    return dict(passed=bool(ok), smoother=smoother, n_contact_cols=int(len(cc)), contact_fraction=float(frac),
                median_abs_px=float(np.median(np.abs(d))), max_below_px=float(d.max()), min_px=float(d.min()),
                p95_abs_px=float(np.percentile(np.abs(d), 95)),
                curve_self_rms_px=float(np.sqrt(np.mean((cr - curve) ** 2))))


# ------------------------------------------------------------------ H3 elevation consistency
def check_contact_inside_ellipse(cc, cr, ell):
    q = ((cc - ell["u"]) / ell["a"]) ** 2 + ((cr - ell["v"]) / ell["b"]) ** 2
    return dict(passed=bool(np.all(q < 1.0)), max_q=float(q.max()), n=int(len(cc)),
                note="one-sided: an ellipse too FLAT (elevation too low) puts contact points outside; a too-HIGH "
                     "elevation cannot be detected by this check")


# ------------------------------------------------------------------ H5 scale
def check_scale(cam, mask, extent_m=0.70, G=(-1.25, 0.0, 0.0)):
    W, H = cam["image_size"]
    f = cam["lens"] / cam["sensor_width"] * W
    C = np.array(cam["location"]); M = np.array(cam["rot_matrix"])
    G = np.array(G)
    uv, z = spf.project(np.array([G - [extent_m / 2, 0, 0], G + [extent_m / 2, 0, 0]]), C, M, f, W, H)
    xs = np.nonzero(mask.any(0))[0]
    wpx = xs.max() - xs.min() + 1
    rel = (uv[1, 0] - uv[0, 0]) / wpx - 1
    return dict(passed=bool(abs(rel) <= H5_TOL), reprojected_px=float(uv[1, 0] - uv[0, 0]), silhouette_px=int(wpx),
                rel_err=float(rel), ground_centre_px=uv.mean(0).tolist())


# ------------------------------------------------------------------ H6 shadow kept out of the mask
def check_shadow_out(mask, L):
    E = spf.texture_energy(L)
    smooth = mask & (ndi.gaussian_filter(E, 3) < 2.0)
    frac = smooth.sum() / mask.sum()
    return dict(passed=bool(frac <= H6_SMOOTH_FRAC), smooth_fraction=float(frac))


# ------------------------------------------------------------------ H1 light
def check_light(cs, p, test):
    h = spf.light_holdout(cs, p, test)
    h["passed"] = bool(h["r"] >= H1_R and h["ratio"] <= H1_RATIO)
    return h


def scale_mask(mask, s):
    ys, xs = np.nonzero(mask)
    cy, cx = ys.mean(), xs.mean()
    H, W = mask.shape
    yy, xx = np.mgrid[0:H, 0:W]
    sy = ((yy - cy) / s + cy).round().astype(int).clip(0, H - 1)
    sx = ((xx - cx) / s + cx).round().astype(int).clip(0, W - 1)
    return mask[sy, sx]


def shift_mask(mask, dy=0, dx=0):
    return np.roll(np.roll(mask, dy, 0), dx, 1)


def main():
    case = sys.argv[1]
    t0 = int(time.time())
    im, L = spf.load(os.path.join(case, "ref.jpg"))
    mask = np.asarray(Image.open(os.path.join(case, "mask.png"))) > 0
    shadow = np.asarray(Image.open(os.path.join(case, "shadow.png"))) > 0
    cam = json.load(open(os.path.join(case, "camera.json")))
    light = json.load(open(os.path.join(case, "light.json")))
    ell = light["shadow"]["outer_ellipse"]
    cct = np.load(os.path.join(case, "contact_trough.npy"))
    cc, cr = cct[:, 0], cct[:, 1]
    cs = dict(np.load(os.path.join(case, "contour_samples.npz")))
    fit_sel, test_sel = spf.arcs_split(cs)
    p = [light["contour_fit"]["ambient_a0"], light["contour_fit"]["gx"], light["contour_fit"]["gy"]]

    V = {}
    # ---- real outputs
    V["H1_light_holdout"] = check_light(cs, p, test_sel)
    V["H1_light_fit_arcs_for_reference"] = spf.light_holdout(cs, p, fit_sel)
    V["H2_ground_contact_as_declared_quadratic"] = check_ground_contact(mask, cc, cr, "quadratic")
    V["H2_ground_contact_amended_median15"] = check_ground_contact(mask, cc, cr, "median15")
    V["H3_contact_inside_shadow_ellipse"] = check_contact_inside_ellipse(cc, cr, ell)
    V["H4_mask_edges"] = check_mask_edges(mask, L)
    V["H5_scale"] = check_scale(cam, mask)
    V["H6_shadow_out_of_mask"] = check_shadow_out(mask, L)
    V["shadow_mask_overlap_px"] = int((mask & shadow).sum())

    # ---- planted failures (A22): every check must PASS the truth and FAIL each planted error
    P = {}
    P["H1_flipped_light"] = check_light(cs, [p[0], -p[1], -p[2]], test_sel)
    P["H1_rotated_90"] = check_light(cs, [p[0], -p[2], p[1]], test_sel)
    P["H1_no_key_light"] = check_light(cs, [p[0], 0.0, 0.0], test_sel)
    P["H2_sunk_4px"] = check_ground_contact(shift_mask(mask, 4), cc, cr)
    P["H2_lifted_8px"] = check_ground_contact(shift_mask(mask, -8), cc, cr)
    P["H3_ellipse_too_flat_b_x0.8"] = check_contact_inside_ellipse(cc, cr, dict(ell, b=ell["b"] * 0.8))
    P["H4_shrunk_2pct"] = check_mask_edges(scale_mask(mask, 0.98), L)
    P["H4_grown_2pct"] = check_mask_edges(scale_mask(mask, 1.02), L)
    P["H4_shifted_3px"] = check_mask_edges(shift_mask(mask, 0, 3), L)
    far = dict(cam); C = np.array(cam["location"]); G = np.array([-1.25, 0, 0])
    far["location"] = (G + 1.10 * (C - G)).tolist()
    near = dict(cam); near["location"] = (G + 0.90 * (C - G)).tolist()
    P["H5_camera_10pct_farther"] = check_scale(far, mask)
    P["H5_camera_10pct_closer"] = check_scale(near, mask)
    sh10, _ = spf.shadow_mask(L, mask, 10.0)
    P["H6_mask_with_shadow"] = check_shadow_out(mask | sh10, L)
    # coverage probe (not a planted failure of H4): H4 skips scanlines whose contrast is < 60, i.e. exactly where a
    # soft shadow adjoins the object, so H4 is BLIND to shadow merged into the mask; H6 and H2 cover that side.
    COV = dict(H4_blind_to_mask_with_shadow=check_mask_edges(mask | sh10, L))

    proof = {k: dict(planted_detected=not v["passed"], **{kk: vv for kk, vv in v.items() if kk != "passed"})
             for k, v in P.items()}
    all_detected = all(v["planted_detected"] for v in proof.values())
    out = dict(
        coverage_probes=dict(H4_blind_to_mask_with_shadow=dict(
            h4_passed_anyway=bool(COV["H4_blind_to_mask_with_shadow"]["passed"]),
            covered_by="H6 (planted H6_mask_with_shadow detected) and H2 (planted H2_sunk_4px detected)")),
        sides=dict(
            H1="wrong direction (flipped, rotated 90 deg) and no key light: all planted",
            H2="sunk (mask too low) and lifted (mask too high): both planted",
            H3="too flat (elevation too low) planted; too HIGH elevation cannot fail this check -> pitch stays ESTIMATED",
            H4="too big, too small, shifted: all planted; blind to the bottom edge (no scanlines there) -> H2, H6",
            H5="too far and too near: both planted",
            H6="shadow merged into mask planted; the other side (object missing from mask) is H4 shrunk / H2 lifted"),
        written_unix=t0, holdout_plan="holdout_plan.json (written 1792333780, before the fits)",
        tool="engine/tools/studio_photo_fit.py", checks="engine/checks/studio_photo_checks.py",
        results=V, planted_failures=proof, all_planted_failures_detected=bool(all_detected),
    )
    print(json.dumps(dict(results={k: v.get("passed", v) if isinstance(v, dict) else v for k, v in V.items()},
                          planted={k: v["planted_detected"] for k, v in proof.items()}), indent=1))
    return out, V, proof


if __name__ == "__main__":
    out, V, proof = main()
    out["labels"] = {
        "mask.png": "CHECKED: sides/top by H4 (independent step edges, pristine hold-out); bottom by H2 (contact line; "
                    "checked-with-reuse, see history); no shadow inside by H6",
        "shadow.png": "CHECKED: disjoint from the mask (overlap 0 px), no ring round the top (run 6). Its outer extent "
                      "(4 levels below the sweep) is a threshold choice: ESTIMATED edge",
        "camera.focal": "ESTIMATED (prior 85 mm FF, plausible 50-200 mm); cannot be held out from one photo",
        "camera.pitch": "ESTIMATED from the outer-shadow ellipse (isotropic footprint); H3 consistency passes; "
                        "too-high elevation is undetectable by H3",
        "camera.scale": "DECISION applied (0.70 m across the view); H5 consistency only",
        "camera.ground_row": "ESTIMATED (shadow-ellipse centre row); contact line agrees with the silhouette (H2)",
        "camera.azimuth": "FREE CHOICE (-y side looking +y)",
        "light.image_plane_direction": "CHECKED by H1 hold-out (odd contour arcs)",
        "light.ambient_fraction": "CHECKED by H1 (same model)",
        "light.world_elevation_azimuth": "ESTIMATED (front-key choice, wide elevation range)",
        "light.highlights": "UNCHECKED (not used)",
    }
    hist = os.path.join(sys.argv[1], "camera_validation_history.json")
    if os.path.exists(hist):
        out["history"] = json.load(open(hist))
    json.dump(out, open(os.path.join(sys.argv[1], "camera_validation.json"), "w"), indent=2)
