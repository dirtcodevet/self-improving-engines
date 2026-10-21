"""Proofs for relief.py. Run: python engine/loop/test_relief.py (also collectable by pytest)."""
import json
import math
import os
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relief as R  # noqa: E402


def ra_vgroove(depth, frac):
    """analytic Ra of a profile with one V groove (depth, share of the profile it spans = frac), flat elsewhere"""
    mu = frac / 2.0                                    # mean depth / depth
    return depth * ((1 - frac) * mu + frac * (mu ** 2 / 2 + (1 - mu) ** 2 / 2))


def test_exact_hex_lattice_plateau_density():
    p = dict(R.START_PARAMS, jitter=0.0, d2_um=0.0, follicles_per_cm2=0.0, anisotropy=0.0, family2_deg=60.0)
    L, px = 8.0, 1024
    info = R.lattice_info(p, L, 0)
    s = R.stats(R.generate(p, L, px, 0), L)
    analytic = 1.0 / p["plateau_mm2"]
    got = s["plateau_density_per_mm2"]
    print("  hex lattice %dx%d k=%d: %d triangles, area %.4f mm2, lattice angle err %.2f deg" % (
        info["nx"], info["ny"], info["k"], info["plateaus"], info["plateau_mm2_realised"], info["lattice_angle_err_deg"]))
    print("  plateau density measured %.3f, analytic 1/A = %.3f (%+.1f %%), lattice's own %.3f (%+.1f %%)" % (
        got, analytic, 100 * (got / analytic - 1), info["plateau_density_expected"], 100 * (got / info["plateau_density_expected"] - 1)))
    assert abs(got / analytic - 1) < 0.05
    assert abs(got / info["plateau_density_expected"] - 1) < 0.02      # the count is the lattice's, not an artefact


def test_single_vgroove_ra():
    cases = [  # (name, segment mm, L, px, depth, width, profile-direction angle to the groove for x and y profiles)
        ("narrow vertical 30/50 um, 8 mm", [(3.1, -1, 3.1, 9)], 8.0, 1024, 30.0, 50.0, (90.0, None)),
        ("wide vertical 40/400 um, 4 mm", [(1.7, -1, 1.7, 5)], 4.0, 512, 40.0, 400.0, (90.0, None)),
        ("diagonal 45 deg 40/200 um, 4 mm", [(-1, -1, 5, 5)], 4.0, 1024, 40.0, 200.0, (45.0, 45.0)),
    ]
    for name, seg, L, px, D, W, (ax, ay) in cases:
        h = R.render_grooves(seg, L, px, D, W)
        s = R.stats(h, L)
        want_x = ra_vgroove(D, W / (L * 1000.0 * math.sin(math.radians(ax)))) if ax else 0.0
        want_y = ra_vgroove(D, W / (L * 1000.0 * math.sin(math.radians(ay)))) if ay else 0.0
        want = 0.5 * (want_x + want_y)
        print("  %-34s Ra %.4f um vs analytic %.4f (%+.2f %%); x %.4f/%.4f, y %.4f/%.4f; depth min %.2f" % (
            name, s["ra_um"], want, 100 * (s["ra_um"] / want - 1), s["ra_x_um"], want_x, s["ra_y_um"], want_y, h.min()))
        assert abs(s["ra_um"] / want - 1) < 0.05
        assert abs(s["ra_x_um"] / want_x - 1) < 0.05
        if want_y == 0:
            assert s["ra_y_um"] < 1e-6
        else:
            assert abs(s["ra_y_um"] / want_y - 1) < 0.05
        assert s["primary_depth_um"] > 0.85 * D and s["primary_depth_um"] <= D + 1e-3


def test_flat_tile():
    s = R.stats(np.zeros((256, 256), np.float32), 4.0)
    print("  flat tile:", {k: round(v, 6) for k, v in s.items()})
    assert s["ra_um"] == 0 and s["rq_um"] == 0 and s["rz_um"] == 0 and s["rt_um"] == 0
    assert s["plateau_density_per_mm2"] == 0 and s["anisotropy_index"] == 0 and s["primary_depth_um"] == 0
    assert all(np.isfinite(v) for v in s.values())


def _seam(h):
    """per direction: the seam's mean jump (last -> first row / column), the 99th percentile of the interior row-pair
    mean jumps, the seam's largest single jump, the interior's largest single jump, and the share of seam pixels above
    the interior pixel-jump p99"""
    out = []
    for a in (h, h.T):
        d = np.abs(np.diff(a, axis=0))
        seam = np.abs(a[0] - a[-1])
        out.append((float(seam.mean()), float(np.percentile(d.mean(1), 99)), float(seam.max()), float(d.max()),
                    float((seam > np.percentile(d, 99)).mean())))
    return out


def _seam_ok(res):
    return all(mean <= p99 and mx <= dmax for mean, p99, mx, dmax, _ in res)


def test_seamless():
    # (1) exact: grooves centred on the seam (x = 8 = 0, y = 0) leave identical first and last rows / columns, and an
    #     oblique segment drawn one tile period away (periodic image) gives the very same tile
    g = R.render_grooves([(8.0, -1, 8.0, 9), (-1, 0.0, 9, 0.0)], 8.0, 512, 30.0, 60.0)
    assert np.allclose(g[:, 0], g[:, -1]) and np.allclose(g[0, :], g[-1, :]) and g.min() < -20
    seg = np.array([(-0.7, 2.1, 6.3, 7.7), (5.0, 7.0, 8.9, 9.4)])
    base = R.render_grooves(seg, 8.0, 512, 30.0, 60.0)
    for dx, dy in ((8.0, 0.0), (0.0, -8.0), (8.0, 8.0)):
        assert np.allclose(base, R.render_grooves(seg + np.array([dx, dy, dx, dy]), 8.0, 512, 30.0, 60.0), atol=1e-3)
    # (2) generated tiles: the seam jump is never larger than the interior's 99th percentile of row-pair jumps
    for seed in (0, 1, 2, 3):
        h = R.generate(R.START_PARAMS, 8.0, 1024, seed)
        res = _seam(h)
        print("  seed %d seam mean jump rows/cols %.2f/%.2f um vs interior p99 %.2f/%.2f; max jump %.1f/%.1f vs %.1f/%.1f; "
              "seam pixels above pixel p99: %.1f/%.1f %%" % ((seed, res[0][0], res[1][0], res[0][1], res[1][1], res[0][2], res[1][2],
                                                             res[0][3], res[1][3], 100 * res[0][4], 100 * res[1][4])))
        assert _seam_ok(res)
    # (3) negative control: the same tile cropped (no longer periodic) is caught
    ctrl = _seam(h[:, :-30][:-30, :])
    print("  control (cropped, not periodic): seam mean jump %.2f/%.2f um (interior p99 %.2f/%.2f)" % (
        ctrl[0][0], ctrl[1][0], ctrl[0][1], ctrl[1][1]))
    assert not _seam_ok(ctrl)


def _ang_dist(a, b):
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def test_anisotropy():
    for seed in (0, 1, 2):
        res = {}
        for a in (0.0, 1.0):
            p = dict(R.START_PARAMS, jitter=0.2, anisotropy=a)
            res[a] = R.stats(R.generate(p, 8.0, 1024, seed), 8.0)
        dom = res[1.0]["dominant_deg"]
        err = min(_ang_dist(dom, 0.0), _ang_dist(dom, 65.0))
        print("  seed %d: index %.3f (anisotropy 0) -> %.3f (anisotropy 1); dominant %.1f deg (%.1f from nearest family); "
              "plateaus/mm2 %.2f -> %.2f" % (seed, res[0.0]["anisotropy_index"], res[1.0]["anisotropy_index"], dom, err,
                                            res[0.0]["plateau_density_per_mm2"], res[1.0]["plateau_density_per_mm2"]))
        assert res[1.0]["anisotropy_index"] > res[0.0]["anisotropy_index"] + 0.1
        assert err <= 10.0


def test_determinism():
    a = R.generate(R.START_PARAMS, 4.0, 256, 5)
    b = R.generate(R.START_PARAMS, 4.0, 256, 5)
    c = R.generate(R.START_PARAMS, 4.0, 256, 6)
    assert a.dtype == np.float32 and a.shape == (256, 256)
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_start_parameters_report():
    cited = {"ra_um": (7, 10), "rz_um": (32, 40), "rt_um": (0, 85), "plateau_density_per_mm2": (5.8, 5.9)}
    for px in (1024, 2048):
        t0 = time.time()
        h = R.generate(R.START_PARAMS, 8.0, px, 0)
        tg = time.time() - t0
        t0 = time.time()
        s = R.stats(h, 8.0)
        ts = time.time() - t0
        print("  START_PARAMS, 8 mm, px %d (%.2f um/px): generate %.2f s, stats %.2f s" % (px, 8000.0 / px, tg, ts))
        print("   ", {k: round(v, 2) for k, v in s.items()})
        print("    vs cited:", {k: ("in" if lo <= s[k] <= hi else "OUT %.2f vs %s-%s" % (s[k], lo, hi)) for k, (lo, hi) in cited.items()})
        assert s["rt_um"] < 85.0 and abs(s["plateau_density_per_mm2"] / 5.88 - 1) < 0.1
        assert tg < 20.0


def test_loop_wiring():
    import core
    state = {"relief": dict(R.START_PARAMS)}
    handle = R.FieldParams(["d1_um", "d2_um"], state)
    new = handle.apply(state, np.array([40.0, 12.0]))
    assert new["relief"]["d1_um"] == 40.0 and new["relief"]["d2_um"] == 12.0 and state["relief"]["d1_um"] == 30.0
    assert handle.n == 2 and np.allclose(handle.x0, [30.0, 10.0]) and len(handle.bounds[0]) == 2 and len(handle.scale) == 2
    descs = [(R.relief_stats, {"size_mm": 4.0, "px": 256, "seed": 0})]
    m = core.measure(state, descs)
    assert "relief_ra_um" in m and "relief_plateau_density_per_mm2" in m
    targets = [core.Target("relief_ra_um", 8.5, 1.0, "R7/R8", 1)]
    _, x, rep = core.solve(state, [handle], descs, targets, reg=0.01, max_nfev=8, log=lambda *a: None)
    z0, z1 = rep["before"][0]["z"], rep["after"][0]["z"]
    print("  loop: relief_ra_um z %+.2f -> %+.2f with d1, d2 = %s (%d evaluations)" % (z0, z1, np.round(x, 1), rep["nfev"]))
    assert abs(z1) < abs(z0)


def test_save_tile():
    from PIL import Image
    h = R.generate(R.START_PARAMS, 4.0, 256, 1)
    with tempfile.TemporaryDirectory() as d:
        png, js = os.path.join(d, "t.png"), os.path.join(d, "t.json")
        meta = R.save_tile(h, png, js, 4.0, R.START_PARAMS, 1)
        im = Image.open(png)
        a = np.array(im)
        assert a.dtype == np.uint16 and a.shape == (256, 256) and a.min() == 0 and a.max() == 65535, (a.dtype, a.min(), a.max())
        m = json.load(open(js))
        back = m["height_min_um"] + a / 65535.0 * (m["height_max_um"] - m["height_min_um"])
        err = float(np.abs(back - h).max())
        assert err < (m["height_max_um"] - m["height_min_um"]) / 65535.0 + 1e-6
        assert m["size_mm"] == 4.0 and m["px"] == 256 and m["seed"] == 1 and m["params"]["d1_um"] == 30.0
        # the dependency-free writer gives the same pixels
        R._write_png16(os.path.join(d, "z.png"), a)
        assert np.array_equal(np.array(Image.open(os.path.join(d, "z.png"))), a)
        print("  PNG round trip: max error %.5f um (one level = %.5f um), json keys %s" % (
            err, (m["height_max_um"] - m["height_min_um"]) / 65535.0, sorted(m)[:6]))


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    order = ["test_exact_hex_lattice_plateau_density", "test_single_vgroove_ra", "test_flat_tile", "test_seamless",
             "test_anisotropy", "test_determinism", "test_start_parameters_report", "test_loop_wiring", "test_save_tile"]
    tests.sort(key=lambda t: order.index(t[0]) if t[0] in order else 99)
    failed = 0
    for name, fn in tests:
        print(name)
        try:
            fn()
            print("  PASS")
        except Exception as e:  # noqa: BLE001
            failed += 1
            import traceback
            traceback.print_exc()
            print("  FAIL", repr(e))
    print("%d/%d passed" % (len(tests) - failed, len(tests)))
    sys.exit(1 if failed else 0)
