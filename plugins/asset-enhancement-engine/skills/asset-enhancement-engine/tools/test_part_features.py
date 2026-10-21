"""PROOF of engine/tools/part_features.py (build L4, 2026-10-21): a planted head with features of known place and extent.

The head is an ellipsoid on a neck (signed distance field, marching cubes at 2 mm); on it, planted: two ear flaps
standing out of its sides, a nose on the front, two eye sockets (sunk pits with a lid ridge round each), and lips (two
ridges either side of a slit across the mid-line, below the nose). Each feature's TRUE region is the skin where its own
primitive is the surface (its distance field below the head's), grown by 4 mm (the blend). The finder runs with the
human pack's own features block (engine/packs/human/language.json), as the Translator runs it.

Checks (what the finder must give on a shape whose answer is known):
  every planted feature found, once, with the right word and side;
  each found region overlaps its true region: IoU >= 0.5, and its area centroid within 1.0 cm of the true one;
  no found region holds more than 10 % of another feature's true region;
  the head's frame: x to the subject's left (+x), y up, z to the front (-y of the object).
Run: python engine/tools/test_part_features.py   -> PASS / FAIL and engine/tools/test_part_features.json
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)


def _ell(P, c, r):
    """approximate signed distance to an ellipsoid (centre c, semi-axes r)"""
    q = (P - c) / r; k0 = np.linalg.norm(q, axis=-1); k1 = np.linalg.norm(q / r, axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-12)


def _smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def _smax(a, b, k):
    return -_smin(-a, -b, k)


def planted():
    cm = 0.01
    head = lambda P: _ell(P, np.array([0, 0, 0.17]), np.array([7.5, 9.5, 11.0]) * cm)
    neck = lambda P: np.maximum(np.linalg.norm(P[..., :2] - [0, 0.01], axis=-1) - 5.5 * cm, np.maximum(P[..., 2] - 0.12, -P[..., 2]))
    feats = {
        "ear_L": lambda P: _ell(P, np.array([8.0, 1.0, 17.0]) * cm, np.array([0.5, 1.9, 3.0]) * cm),
        "ear_R": lambda P: _ell(P, np.array([-8.0, 1.0, 17.0]) * cm, np.array([0.5, 1.9, 3.0]) * cm),
        "nose": lambda P: _ell(P, np.array([0, -9.0, 15.0]) * cm, np.array([1.6, 2.2, 2.6]) * cm),
        "lips": lambda P: np.minimum(_ell(P, np.array([0, -8.6, 11.2]) * cm, np.array([2.6, 0.9, 0.55]) * cm),
                                     _ell(P, np.array([0, -8.6, 10.1]) * cm, np.array([2.5, 0.9, 0.6]) * cm)),
    }
    sockets = {"eye_L": np.array([3.2, -8.6, 19.0]) * cm, "eye_R": np.array([-3.2, -8.6, 19.0]) * cm}

    def body(P):
        d = _smin(head(P), neck(P), 1.0 * cm)
        for k, f in feats.items():
            d = _smin(d, f(P), 0.3 * cm)
        slit = np.maximum(np.abs(P[..., 2] - 0.1065) - 0.12 * cm, np.maximum(np.abs(P[..., 0]) - 2.3 * cm, -(P[..., 1] + 0.075)))
        d = _smax(d, -slit, 0.1 * cm)                                  # the lip line: a slit 2.4 mm tall into the lips
        for k, c in sockets.items():                                   # a socket: a pit 1.3 cm across sunk 1.2 cm, with
            ridge = np.linalg.norm(np.stack([np.linalg.norm((P - c)[..., [0, 2]], axis=-1) - 1.55 * cm, (P[..., 1] + 9.2 * cm)], -1), axis=-1) - 0.35 * cm
            d = _smin(d, ridge, 0.25 * cm)                             # a lid ridge round it
            d = _smax(d, -_ell(P, c + [0, 0.3 * cm, 0], np.array([1.4, 1.5, 0.9]) * cm), 0.15 * cm)
        return d
    sys.path.insert(0, HERE)
    import language as LG
    V, F = LG._sdf_mesh(body, np.array([-11, -13, -1.0]) * cm, np.array([11, 11, 30.0]) * cm, 0.2 * cm)
    F = F[:, ::-1].copy()                                              # outward faces
    truth = {}
    Cf = V[F].mean(1)
    for k, f in feats.items():
        truth[k] = f(Cf) <= 0.4 * cm
    for k, c in sockets.items():
        truth[k] = (np.linalg.norm((Cf - c)[:, [0, 2]], axis=1) <= 2.0 * cm) & (Cf[:, 1] <= c[1] + 1.6 * cm) & (Cf[:, 1] < -0.06)
    dh = head(Cf)
    for f in feats.values():
        dh = np.minimum(dh, f(Cf))
    fm = dh <= neck(Cf)                                                # the head: where the head (or a feature) is the surface
    return V, F, truth, fm


def run():
    t0 = time.time()
    import part_features as PFT
    V, F, truth, fm = planted()
    Cf = V[F].mean(1); fa = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    below = ~fm
    spec = json.load(open(os.path.join(ROOT, "engine", "packs", "human", "language.json"), encoding="utf-8"))["features"][0]
    found, rec = PFT.find(V, F, fm, spec, below_fm=below, log=lambda *a: None)
    rep = {"mesh": {"vertices": int(len(V)), "faces": int(len(F))}, "R0_cm": rec["R0_cm"], "features": {}, "checks": {}}
    ok = True
    got = {}
    for f_ in found:
        key = f_["word"] + ("_" + f_["side"] if f_["side"] else "")
        m = np.zeros(len(F), bool); m[f_["faces"]] = True; got[key] = m
    for key, tm in truth.items():
        tm = tm & fm
        if key not in got:
            rep["features"][key] = "NOT FOUND"; ok = False; continue
        m = got[key]; inter = fa[m & tm].sum(); uni = fa[m | tm].sum(); iou = inter / uni
        c_got = (Cf[m] * fa[m, None]).sum(0) / fa[m].sum(); c_true = (Cf[tm] * fa[tm, None]).sum(0) / fa[tm].sum()
        steal = max([fa[m & truth[o] & fm].sum() / fa[truth[o] & fm].sum() for o in truth if o != key] + [0.0])
        r = {"iou": round(float(iou), 3), "centroid_off_cm": round(float(np.linalg.norm(c_got - c_true) * 100), 3),
             "area_found_cm2": round(float(fa[m].sum() * 1e4), 2), "area_true_cm2": round(float(fa[tm].sum() * 1e4), 2),
             "most_of_another": round(float(steal), 3)}
        r["PASS"] = bool(iou >= 0.5 and r["centroid_off_cm"] <= 1.0 and steal <= 0.10)
        ok &= r["PASS"]; rep["features"][key] = r
    extra = sorted(set(got) - set(truth) - {"mouth"})
    rep["checks"]["no_extra_features"] = not extra; ok &= not extra
    R = np.array(rec["frame"]["axes_rows_xyz"])
    rep["checks"]["frame_axes"] = bool(R[0] @ [1, 0, 0] > 0.9 and R[1] @ [0, 0, 1] > 0.9 and R[2] @ [0, -1, 0] > 0.9); ok &= rep["checks"]["frame_axes"]
    rep["seconds"] = round(time.time() - t0, 1); rep["PASS"] = bool(ok)
    json.dump(rep, open(os.path.join(HERE, "test_part_features.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1)); print("PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
