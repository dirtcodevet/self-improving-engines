#!/usr/bin/env bash
# FAST HAIR/EAR LOOP on the live scene (~1-2 min instead of a full build): coat -> photo markings -> groom ->
# border renders of the ear + temple boxes from the frozen camera -> photo | render sheet.
# The groom is rebuilt WITHOUT its rig binding: use for look decisions only, then run a full build.
# usage: engine/review/ear_lab.sh <case_dir> <mesh_ver> <tag> ["GROOM_GLOBALS; ..."]
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; T="$ROOT/engine/tools"; RV="$ROOT/engine/review"; C="$ROOT/$1"; MV="$2"; TAG="$3"
GG="${4:-}"
O="$C/lab/ears_$TAG"; mkdir -p "$O"
W() { cygpath -w "$1"; }
run() { local out; out=$(python "$T/bmcp.py" code "import sys; _t = r'$(W "$T")'; _t in sys.path or sys.path.insert(0, _t)
$1"); echo "$out" | grep -v "^Client\|^Queued" | tail -3; if echo "$out" | grep -q '"status": "error"'; then exit 1; fi; }
run "exec(open(r'$(W "$C/coat.py")').read())"
if [ -f "$C/photo_markings.json" ]; then
  run "import json; _c=json.load(open(r'$(W "$C/photo_markings.json")')); MARK_RGB=tuple(_c['MARK_RGB']); MARK_DARK_RGB=tuple(_c['MARK_DARK_RGB']); TAIL_MARK_RGB=tuple(_c.get('TAIL_MARK_RGB', _c['MARK_RGB'])); TAIL_DARK_RGB=tuple(_c.get('TAIL_DARK_RGB', _c['MARK_DARK_RGB'])); PHOTO=r'$(W "$C/ref.jpg")'; exec(open(r'$(W "$T/photo_markings.py")').read())"
fi
run "${GG}
exec(open(r'$(W "$T/groom.py")').read())"
python "$RV/ear_crops.py" boxes "$C/ref.jpg" "$C/mesh/${MV}_landmarks.json" "$C/mesh/${MV}_camera.json" "$O/boxes.json" > /dev/null
BX=$(python -c "import json; b=json.load(open(r'$(W "$O/boxes.json")'))['boxes']; print({'ear_'+k: v for k, v in b.items()})")
run "BOXES=$BX; OUT_DIR=r'$(W "$O")'; SAMPLES=512; DENOISE=False; exec(open(r'$(W "$RV/crop_render.py")').read())"
python "$RV/ear_crops.py" compose "$C/ref.jpg" "$O/boxes.json" "$O" "$O/sheet.png"
# score: paste the crops into the last full review render and run the SAME region metric the review uses
LAST=$(ls -d "$C"/review/v*/render_rest.png 2>/dev/null | sort -V | tail -1)
python -c "
import json; from PIL import Image
b = json.load(open(r'$(W "$O/boxes.json")'))['boxes']; im = Image.open(r'$(W "$LAST")').convert('RGB')
for sd, bx in b.items(): im.paste(Image.open(r'$(W "$O")/ear_%s.png' % sd).convert('RGB'), tuple(bx[:2]))
im.save(r'$(W "$O/full.png")')"
python "$RV/compare_regions.py" "$C" "$O/full.png" "$O/regions" > /dev/null; grep -E "^region|^ear_in" "$O/regions.txt"
