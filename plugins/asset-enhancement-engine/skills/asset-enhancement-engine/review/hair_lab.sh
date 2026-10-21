#!/usr/bin/env bash
# FAST HAIR LOOP for the head (~1-2 min): coat -> photo markings -> hair growth field -> groom -> border renders of
# the face box and both ear boxes from the frozen camera -> the review's own region metric on head regions.
# The groom is rebuilt WITHOUT its rig binding: look decisions only; confirm with a full build (skill item A4).
# usage: engine/review/hair_lab.sh <case_dir> <mesh_ver> <tag> ["GROOM/FIELD GLOBALS; ..."]
#   e.g. "USE_HAIR_FIELD=False" for the old comb field, "USE_HAIR_FIELD=True; PHOTO_W=0.85" for the growth field
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; T="$ROOT/engine/tools"; RV="$ROOT/engine/review"; C="$ROOT/$1"; MV="$2"; TAG="$3"
GG="${4:-}"
O="$C/lab/hair_$TAG"; mkdir -p "$O"
W() { cygpath -w "$1"; }
run() { local out; out=$(python "$T/bmcp.py" code "import sys; _t = r'$(W "$T")'; _t in sys.path or sys.path.insert(0, _t)
$1"); echo "$out" | grep -v "^Client\|^Queued" | tail -3; if echo "$out" | grep -q '"status": "error"'; then exit 1; fi; }
run "${GG}
exec(open(r'$(W "$C/coat.py")').read())"
if [ -f "$C/photo_markings.json" ]; then
  run "import json; _c=json.load(open(r'$(W "$C/photo_markings.json")')); MARK_RGB=tuple(_c['MARK_RGB']); MARK_DARK_RGB=tuple(_c['MARK_DARK_RGB']); TAIL_MARK_RGB=tuple(_c.get('TAIL_MARK_RGB', _c['MARK_RGB'])); TAIL_DARK_RGB=tuple(_c.get('TAIL_DARK_RGB', _c['MARK_DARK_RGB'])); PHOTO=r'$(W "$C/ref.jpg")'; exec(open(r'$(W "$T/photo_markings.py")').read())"
fi
if [ -f "$C/photo_flow.npz" ]; then
  run "${GG}
FLOW=r'$(W "$C/photo_flow.npz")'; exec(open(r'$(W "$T/hair_field.py")').read())"
fi
run "${GG}
exec(open(r'$(W "$T/groom.py")').read())"
python "$RV/ear_crops.py" boxes "$C/ref.jpg" "$C/mesh/${MV}_landmarks.json" "$C/mesh/${MV}_camera.json" "$O/boxes.json" > /dev/null
BX=$(python -c "import json; b=json.load(open(r'$(W "$O/boxes.json")'))['boxes']; d={'ear_'+k: v for k, v in b.items()}; d['face']=[530, 90, 890, 480]; print(d)")
run "BOXES=$BX; OUT_DIR=r'$(W "$O")'; SAMPLES=512; DENOISE=False; exec(open(r'$(W "$RV/crop_render.py")').read())"
LAST=$(ls -d "$C"/review/v*/render_rest.png 2>/dev/null | sort -V | tail -1)
python -c "
import json; from PIL import Image
b = json.load(open(r'$(W "$O/boxes.json")'))['boxes']; b['face'] = [530, 90, 890, 480]
im = Image.open(r'$(W "$LAST")').convert('RGB')
for k in ('face', 'R', 'L'):
    im.paste(Image.open(r'$(W "$O")/%s.png' % (k if k == 'face' else 'ear_' + k)).convert('RGB'), tuple(b[k][:2]))
im.save(r'$(W "$O/full.png")')
p = Image.open(r'$(W "$C/ref.jpg")').convert('RGB').crop((530, 90, 890, 480)); r = im.crop((530, 90, 890, 480))
s = Image.new('RGB', (2 * 720 + 10, 780), (255, 255, 255)); s.paste(p.resize((720, 780)), (0, 0)); s.paste(r.resize((720, 780)), (730, 0))
s.save(r'$(W "$O/face_sheet.png")')"
python "$RV/compare_regions.py" "$C" "$O/full.png" "$O/regions" > /dev/null
grep -E "^region|^(forehead|cheek|muzzle|chin|nose|ear_in)" "$O/regions.txt"
