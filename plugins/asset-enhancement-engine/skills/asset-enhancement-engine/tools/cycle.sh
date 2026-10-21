#!/usr/bin/env bash
# One build cycle for a case: spec -> mesh -> Blender import -> camera fit -> probe.
# usage: engine/tools/cycle.sh <case_dir> <version> [voxel_m] [fitcam=1]
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CASE="$1"; VER="$2"; VOX="${3:-0.002}"; FIT="${4:-1}"
T="$ROOT/engine/tools"; C="$ROOT/$CASE"
W() { cygpath -w "$1"; }
python "$C/spec.py" "$C/mesh/$VER" "$VOX"
python "$T/bmcp.py" code "MESH=r'$(W "$C/mesh/$VER")'; exec(open(r'$(W "$T/import_mesh.py")').read())"
if [ -f "$C/camera_frozen.json" ]; then
  python "$T/bmcp.py" code "CAM_JSON=r'$(W "$C/camera_frozen.json")'; exec(open(r'$(W "$T/set_camera.py")').read())"
  python "$T/fit_camera.py" "$C/mesh/${VER}_landmarks.json" "$C/ref_points.json" "$C/mesh/${VER}_camera.json" > /dev/null  # residuals only, informational
elif [ "$FIT" = "1" ]; then
  python "$T/fit_camera.py" "$C/mesh/${VER}_landmarks.json" "$C/ref_points.json" "$C/mesh/${VER}_camera.json"
  python "$T/bmcp.py" code "CAM_JSON=r'$(W "$C/mesh/${VER}_camera.json")'; exec(open(r'$(W "$T/set_camera.py")').read())"
fi
python "$T/bmcp.py" code "OUT=r'$(W "$C/renders/$VER")'; exec(open(r'$(W "$T/probe.py")').read())"
