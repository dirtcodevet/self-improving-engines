"""FIT the skull loft's cross-section shape to the reference views instead of clipping it (a clip against an
extruded silhouette leaves flat walls - streaks - wherever the assumed section is wrong: R4c, J13).
Coordinate descent over q_up, q_dn (superellipse exponents above/below the widest line) and mid_f / mid_b (height of
the widest line in the face / braincase, fraction of the section height), scored by the mean silhouette IoU of the
three views at a coarse voxel size. Writes <spec dir>/ref20_sections.json.
usage: python skull_fit_sections.py <spec.json> <picks.json> [vox_mm=0.8]
"""
import io
import json
import os
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import skull_build  # noqa: E402

GRID = dict(q_up=[1.6, 1.8, 2.0, 2.3, 2.6, 3.0], q_dn=[1.6, 1.8, 2.0, 2.3, 2.6, 3.0, 3.5],
            mid_f=[0.3, 0.4, 0.5, 0.6, 0.7], mid_b=[0.3, 0.4, 0.5, 0.6, 0.7])


def score(spec, picks, prm, vox, tmp):
    os.environ["SKULL_PARAMS"] = json.dumps(prm)
    with redirect_stdout(io.StringIO()):
        rep = skull_build.main(spec, picks, tmp, vox, mesh=False)
    iou = rep["silhouette_iou"]
    return sum(iou[v] for v in ("lateral", "dorsal", "front")) / 3, iou


def main(spec, picks, vox=0.8):
    tmp = os.path.join(os.environ.get("TEMP", "."), "skull_fit_tmp")
    cur = dict(skull_build.SECTION_DEFAULT, clip=0)
    best, iou = score(spec, picks, cur, vox, tmp); hist = [(dict(cur), best)]
    print("start", cur, round(best, 4))
    for rnd in range(3):
        moved = False
        for k, vals in GRID.items():
            for v in vals:
                if v == cur[k]: continue
                trial = dict(cur, **{k: v}); sc, io_ = score(spec, picks, trial, vox, tmp)
                if sc > best + 1e-4:
                    best, iou, cur, moved = sc, io_, trial, True
            print(f"round {rnd} {k}: {cur[k]}  mean IoU {best:.4f}")
        hist.append((dict(cur), best))
        if not moved: break
    os.environ.pop("SKULL_PARAMS", None)
    out = os.path.join(os.path.dirname(os.path.abspath(spec)), "ref20_sections.json")
    json.dump(dict(_what="cross-section shape of the skull loft, FITTED to the reference views (tools/skull_fit_sections.py); no silhouette clip",
                   params=cur, mean_iou=round(best, 4), iou=iou, vox_mm=vox, history=hist), open(out, "w"), indent=1)
    print("best", cur, round(best, 4), iou)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.8)
