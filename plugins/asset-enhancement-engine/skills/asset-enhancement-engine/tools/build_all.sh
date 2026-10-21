#!/usr/bin/env bash
# Rebuild a case end-to-end in the live Blender (crash recovery + frozen-reference regression run).
# usage: engine/tools/build_all.sh <case_dir> <version> [voxel=0.0008] [from=sdf|production|look]
set -eo pipefail
# run from a snapshot: bash reads scripts incrementally, so editing this file mid-run executed half-edited steps (v20)
if [ -z "$BUILD_ALL_SNAPSHOT" ]; then
  SNAP="$(mktemp -t build_all.XXXXXX.sh)"; cp "$0" "$SNAP"
  BUILD_ALL_SNAPSHOT=1 BUILD_ALL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)" exec bash "$SNAP" "$@"
fi
ROOT="${BUILD_ALL_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"; T="$ROOT/engine/tools"; C="$ROOT/$1"; VER="$2"
VOX="${3:-0.0008}"; FROM="${4:-sdf}"
W() { cygpath -w "$1"; }
# every Blender-side call can import shared engine modules (mouth_geom: ONE mouth definition, v27)
run() { python "$T/bmcp.py" code "import sys; _t = r'$(W "$T")'; _t in sys.path or sys.path.insert(0, _t)
$1"; }
if [ "$FROM" = "sdf" ]; then
  "$T/cycle.sh" "$1" "$VER" "$VOX" 1 | grep -v "^  "
  FROM=production
fi
if [ "$FROM" = "production" ]; then
  run "exec(open(r'$(W "$T/production_mesh.py")').read())"
  run "exec(open(r'$(W "$T/feature_smooth.py")').read())"
  FROM=look
fi
run "exec(open(r'$(W "$C/coat.py")').read())"
if [ -f "$C/photo_markings.json" ]; then   # markings captured from the photo (falls back to procedural where unseen)
  run "import json; _c=json.load(open(r'$(W "$C/photo_markings.json")')); MARK_RGB=tuple(_c['MARK_RGB']); MARK_DARK_RGB=tuple(_c['MARK_DARK_RGB']); TAIL_MARK_RGB=tuple(_c.get('TAIL_MARK_RGB', _c['MARK_RGB'])); TAIL_DARK_RGB=tuple(_c.get('TAIL_DARK_RGB', _c['MARK_DARK_RGB'])); PHOTO=r'$(W "$C/ref.jpg")'; exec(open(r'$(W "$T/photo_markings.py")').read())"
fi
LOOK=""
[ -f "$C/look.py" ] && LOOK="exec(open(r'$(W "$C/look.py")').read()); "
run "${LOOK}exec(open(r'$(W "$T/materials.py")').read())"
run "exec(open(r'$(W "$T/groom.py")').read())"
run "LABEL='${VER}_look'; exec(open(r'$(W "$T/checkpoint.py")').read())"
# rig + accessories + EEVEE fallbacks + demo animation
run "exec(open(r'$(W "$T/rig.py")').read())"
run "CLOSED_DEG=0.5; exec(open(r'$(W "$T/lip_seal.py")').read())"
run "exec(open(r'$(W "$T/accessories.py")').read())"
run "exec(open(r'$(W "$T/eevee_outputs.py")').read())"
run "exec(open(r'$(W "$T/anim_idle.py")').read())"
run "LABEL='${VER}_rigged'; exec(open(r'$(W "$T/checkpoint.py")').read())"
# open mouth at the widest jaw frame (meow): taper, tongue/teeth showing, rendered interior brightness (v28)
run "TOOLS=r'$(W "$T")'; OUT_JSON=r'$(W "$C/renders/${VER}_mouthopen.json")'; DEBUG_PNG=r'$(W "$C/renders/${VER}_mouthopen.png")'; exec(open(r'$(W "$T/mouth_open_check.py")').read())" | python -c "import json,sys; d=json.loads(sys.stdin.read().strip().splitlines()[-1]); print('MOUTH_OPEN', {k: d.get(k) for k in ('taper','tongue','teeth','canines_up','interior_lum')}, 'PASS' if d['PASS'] else 'FAIL')"
# gates: engine checks + multi-view vs reference (if the case has one)
python "$ROOT/engine/checks/checks.py" "$C/mesh/$VER" || echo "GATE: engine checks FAILED"
[ -f "$C/ref3d/rodin_canon.ply" ] && python "$ROOT/engine/checks/multiview.py" "$C/mesh/$VER" "$C/ref3d/rodin_canon.ply" "$C/ref3d/mv_$VER.png" | python -c "import json,sys; d=json.load(sys.stdin); print('MULTIVIEW', d['weighted_iou'], d['profiles'], 'PASS' if d['PASS'] else 'FAIL')"
run "OUT=r'$(W "$C/renders/$VER")'; exec(open(r'$(W "$T/probe.py")').read())"
