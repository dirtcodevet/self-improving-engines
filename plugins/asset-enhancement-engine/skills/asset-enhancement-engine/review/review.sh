#!/usr/bin/env bash
# ONE-COMMAND REVIEW of a built version (live Blender scene = that version):
#   naturalness:  seam fairness scan (curvature jumps, attributed to parts) + heat map + zebra turnaround/close-ups
#   alignment:    photo-vs-model feature traces (same tracer, same camera) + region colour/texture/fur flow
#   outside view: packet for the BLIND reviewer (engine/review/REVIEWER.md) - the orchestrator launches the agent
# Writes <case>/review/<ver>/ (images, tables, packet/, REVIEW.md).
# usage: engine/review/review.sh <case_dir> <ver>
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; T="$ROOT/engine/tools"; RV="$ROOT/engine/review"; C="$ROOT/$1"; VER="$2"
O="$C/review/$VER"; mkdir -p "$O/packet"
W() { cygpath -w "$1"; }
B() { local out; out=$(python "$T/bmcp.py" code "import sys; _t=r'$(W "$T")'; _t in sys.path or sys.path.insert(0, _t)
$1") || true
  if echo "$out" | grep -q '"status": "error"'; then echo "$out"; return 1; fi; echo "$out"; }
REF="$C/ref3d/rodin_canon.ply"
echo "== fairness"
python "$RV/fairness.py" "$C/mesh/$VER" "$REF" --colors "$O/fairness.ply" --json "$O/fairness.json" | tee "$O/fairness.txt"
CENTERS=$(python -c "
import json, numpy as np
b = json.load(open(r'$(W "$O/fairness.json")'))['bands']; out = []
for d in sorted(b, key=lambda d: -d['n'] * d['peak_x_base']):
    p = np.array(d['at'])
    if all(np.linalg.norm(p - q) > 0.04 for q in out): out.append(p)
    if len(out) == 5: break
print(' '.join('(%.3f,%.3f,%.3f)' % tuple(p) for p in out))")
echo "zebra centres: $CENTERS"
echo "== renders"
B "
import bpy
col = bpy.data.collections.new('Lab'); bpy.context.scene.collection.children.link(col)
before = set(bpy.data.objects)
try:
    bpy.ops.wm.ply_import(filepath=r'$(W "$O/fairness.ply")')
    lab = [o for o in bpy.data.objects if o not in before][0]
    for cc in list(lab.users_collection): cc.objects.unlink(lab)
    col.objects.link(lab); lab.name = 'Lab_Body'
    for p in lab.data.polygons: p.use_smooth = True
    if len(lab.data.color_attributes): lab.data.color_attributes.active_color = lab.data.color_attributes[0]
    PREFIX = 'Lab'; SHADE_COLOR = 'VERTEX'; OUT = r'$(W "$O/fairness_heatmap.png")'
    exec(open(r'$(W "$T/views.py")').read())
finally:
    for o in [o for o in bpy.data.objects if o not in before]:
        me = o.data; bpy.data.objects.remove(o, do_unlink=True)
        if me is not None and me.users == 0: bpy.data.meshes.remove(me)
    bpy.data.collections.remove(col)
print('heatmap')" | tail -1
B "FREQ=5; OUT=r'$(W "$O/zebra_turnaround.png")'; VIEWS_PY=r'$(W "$T/views.py")'; exec(open(r'$(W "$RV/zebra_views.py")').read())" | tail -1
i=0; for c in $CENTERS; do i=$((i+1)); B "FREQ=5; CENTER=$c; SIZE=0.10; OUT=r'$(W "$O/zebra_band$i.png")'; VIEWS_PY=r'$(W "$T/views.py")'; exec(open(r'$(W "$RV/zebra_views.py")').read())" | tail -1; done
B "
import bpy
rig = bpy.data.objects['Cat_Rig']; _pp = rig.data.pose_position
_vis = {o.name: o.hide_render for o in bpy.data.objects}
try:
    rig.data.pose_position = 'REST'
    OUT = r'$(W "$O/render_rest.png")'; SAMPLES = 512; PCT = 100; DENOISE = False   # raw: the denoiser erased fur texture (v37)
    exec(open(r'$(W "$T/render_preview.py")').read())
    for o in bpy.data.objects:
        if o.type == 'CURVES' or 'Whisk' in o.name or o.name in ('Cat_Body', 'Cat_SkinRef', 'Cat_FurEnvelope'): o.hide_render = True
    OUT = r'$(W "$O/clay_turnaround.png")'
    exec(open(r'$(W "$T/views.py")').read())
finally:
    rig.data.pose_position = _pp
    for n, h in _vis.items():
        if n in bpy.data.objects: bpy.data.objects[n].hide_render = h
print('renders')" | tail -1
B "
import bpy
rig = bpy.data.objects['Cat_Rig']; _pp2 = rig.data.pose_position
try:
    rig.data.pose_position = 'REST'
    FRAME = 1; CLAY = True; SIZE = 0.09; LANDMARK = 'head'; OUT = r'$(W "$O/clay_head.png")'; VIEWS_PY = r'$(W "$T/views.py")'
    exec(open(r'$(W "$T/face_views.py")').read())
finally:
    rig.data.pose_position = _pp2" | tail -1
echo "== alignment"
[ -f "$C/review/photo_features.json" ] || python "$RV/trace_photo.py" "$1" > /dev/null
python "$RV/trace_photo.py" "$1" "$O/render_rest.png" "$C/renders/${VER}_mask.png" "model_${VER}_features" > /dev/null
python "$RV/compare_features.py" "$1" "model_${VER}_features" "$O/features" | tail -1
python "$RV/compare_regions.py" "$1" "$O/render_rest.png" "$O/regions" | tail -1
echo "== packet"
P_="$O/packet"; cp "$C/ref.jpg" "$P_/01_photo.jpg"; cp "$O/render_rest.png" "$P_/02_render_same_camera.png"
python -c "
import cv2, numpy as np
a = cv2.imread(r'$(W "$C/ref.jpg")'); b = cv2.imread(r'$(W "$O/render_rest.png")')
ca, cb = a[90:480, 530:890], b[90:480, 530:890]
s = np.hstack([ca, np.full((ca.shape[0], 8, 3), 255, np.uint8), cb]); cv2.imwrite(r'$(W "$P_/03_face_photo_left_render_right.png")', cv2.resize(s, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
ba, bb = a[300:1100, 500:1250], b[300:1100, 500:1250]
cv2.imwrite(r'$(W "$P_/03b_body_photo_left_render_right.png")', np.hstack([ba, np.full((ba.shape[0], 8, 3), 255, np.uint8), bb]))"
cp "$O/clay_turnaround.png" "$P_/04_clay_turnaround.png"; cp "$O/clay_head.png" "$P_/05_clay_head.png"
i=0; for f in "$O"/zebra_band*.png; do i=$((i+1)); cp "$f" "$P_/06_zebra_$i.png"; done
cp "$O/zebra_turnaround.png" "$P_/06_zebra_turnaround.png"
echo "== sheet"
{
  echo "# Review $VER"; echo
  echo "Naturalness (seams): ![](fairness_heatmap.png) ![](zebra_turnaround.png)"; echo
  echo '```'; cat "$O/fairness.txt"; echo '```'; echo
  echo "Alignment (photo green / model red): ![](features.png)"; echo
  echo '```'; cat "$O/features.txt"; echo '```'; echo
  echo '```'; cat "$O/regions.txt"; echo '```'; echo
  echo "Blind reviewer: run the agent on packet/ with engine/review/REVIEWER.md and paste its findings below."; echo
} > "$O/REVIEW.md"
echo "REVIEW_DONE $O"
