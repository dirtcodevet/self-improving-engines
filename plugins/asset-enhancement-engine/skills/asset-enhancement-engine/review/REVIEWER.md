# Blind reviewer brief (outside scoring for the photo -> Blender creature engine)

You review a 3D model of a domestic cat against ONE reference photo of the real cat it should reproduce, and
against your knowledge of how real cats look. You are independent: read ONLY the files in the packet folder you are
given. Do not open any other file or folder (no logs, scores, code, notes) - they would bias you.

## Packet
- `01_photo.jpg` - the reference photo (the truth for this cat).
- `02_render_same_camera.png` - the model rendered from the photo's camera (fur, colour, lighting matched).
- `03_face_photo_left_render_right.png`, `03b_body_photo_left_render_right.png` - the same crops side by side.
- `04_clay_turnaround.png` - the bare skin (no fur) from side, front, top, back three-quarter, front three-quarter.
- `05_clay_head.png` - the bare head close up (face-on, 3/4, profile, from below, other 3/4).
- `06_zebra_*.png` - reflection-line (zebra) renders of the bare skin. Stripes flow smoothly over a fair surface;
  a KINK, a sudden bunching, a whirl/eye pattern or a stripe that changes direction abruptly means a crease, ridge,
  dent or bump. Judge junctions with these: neck, chest, legs into body, tail into body, head.

Fur hides some skin shape; the clay and zebra images show what the fur sits on. A real cat's skin under fur is
smooth and continuous - no seams, steps, rings or bumps where parts meet.

## What to do
Go region by region. Be exhaustive and specific. Report problems even if small; also say which regions look right.
Regions: overall proportions & silhouette; head shape (cranium dome, forehead, cheeks/zygomatic width, profile);
ears (size, set, angle, shape, inner ear, tufts); eyes (opening shape, size, spacing, tilt, iris, pupil, lids/rim,
how much eyeball shows); nose (leather shape, size, texture, nostrils, colour, nose bridge); mouth & muzzle
(lip line, philtrum, whisker pads, chin, whiskers); neck; chest; forelegs (shoulder, elbow, junction with body,
wrist, paws); hind legs (haunch, junction with flank and belly, hock, paws); tail (root/junction, thickness,
taper, shape, rings); back/topline; belly/underline; coat (fur length, texture, flow direction, softness);
markings and colour (pattern, placement, contrast, colours); lighting/material realism.

For each finding give: `region`, `where` (image + position), `what is wrong`, `what a real cat / this photo shows
instead`, `severity` (3 = immediately reads as wrong, 2 = noticeable, 1 = subtle), `confidence` (high/med/low),
`kind` (shape | junction/seam | proportion | detail | texture | colour/markings | pose).
Then a per-region naturalness score 1-5 (5 = indistinguishable from a real cat) and a 3-line overall verdict.

Output: a markdown table of findings sorted by severity, then the region scores, then the verdict. No preamble.
