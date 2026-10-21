# Fur plan v3 for cat1: real density, lilac points, no ear tufts, stray control, regrowth (J16)

Written 2026-10-18 by the fur-plan-v3 agent. It builds on `fur_plan.md` (Phase 2 spec), which still holds wherever this file is silent.
- **Code:** `tripo_rebuild/fur_v3.py` (the generator) and `tripo_rebuild/fur_v3_patch_test.py` (the patch proof).
- **Results:** `tripo_rebuild/layers/fur_v3_patch_test.json` and `layers/fur_v3_patch_*.png`.
- **Counts:** `engine/packs/felid/fur_v3_counts.json`.

Nothing in this stage touched Blender.

**Labels**
- *checked*: measured by a check that also fails on its planted defects (A22).
- *estimated*: arithmetic, or a value without a measurement.
- *unchecked*: not measured.

**The skin used.** The v3 skin does not exist yet, so the proof runs on `cat_p2_skin.npz` as a stand-in. The generator reads any skin (`v`, `f`, `n`), and it measures the inset itself, so it runs unchanged on the v3 skin.

**TEMP-only code moved into the project.** The Phase 2 coat generator existed only in `%TEMP%` (PHASE2_ASSESSMENT 2.1). It is now copied to `tripo_rebuild/hair_coat_p2/`, together with `cf_snap/coat.json` and `coat_field_snap.py`. The only edit is its `SCR` path.

## 0. Results at a glance

**Back patch:** dorsal outline, 809 mm² of roots. **Tail patch:** lilac, 878 mm² of roots.

| Job | Result | Label |
|---|---|---|
| (1) Density at real values | Children follow the palette: 96.6 /mm² on the back and 94.7 on the tail, against 93. Per type: guard 5.05, awn 10.48, down 81.0 /mm², against 4.89, 10.2, 77.9. The C10 check passes. Planted half and double densities both FAIL. | checked |
| (1) Coverage at real thickness | Skin visible through the coat at real diameters (47/30/15 µm): **0.002 % top-down and 0.04 % at 45°** on the back; 0.03 % and 0.35 % on the tail. At guide density only (Phase 2's 1 + 2 /mm²), **62-68 % of the skin is visible**. That is the measured reason the Phase 2 coat read thin. A planted 4× diameter (thickness standing in for density) still leaves 52-55 % visible, and the diameter check refuses it. | checked (numbers); "reads as fur" by eye on `fur_v3_patch_tail_colour.png`: estimated |
| (2) Lilac points | Per-strand colour along the shaft, solved from the pigment hair-colour targets at the skin point under the TIP. 92.5 % of lilac guards and 94.6 % of lilac awns have tips darker than their roots. The visible shaft reaches the target exactly in the solve. A planted uniform white shaft misses by ΔE p95 51.6 and FAILs. Sampling at the root instead of the tip changes the target by ΔE > 5 on 50-52 % of tail strands, so the upstream rule matters. | solve checked; **render ΔE unchecked** (J12); the targets are estimated (camera hold-out failed) |
| (3) No ear-tip tufts | **Phase 2 ear hair FAILs.** The "lynx tufts" are the **ear furnishings**: 596 L / 507 R reach past the apex plane, up to 9.7 / 10.9 mm. Some ear-back guard (58 / 75) and down (25 / 18) do too. The tip wisps themselves are in spec: 7 per ear, at most 3.1 / 3.2 mm. After `ear_tip_control` the check PASSes on both ears. A planted 15 mm tuft and planted missing wisps both FAIL. | checked |
| (4) Stray strands | Back: PASS after control (p99 1.08 mm against a 1.2 mm fringe; 81 guards flattened). **Tail: FAIL after control:** guard p99 4.41 mm, max 7.6 mm; 97 guards and 116 awns are flagged as skin faults. The Phase 2 guides on the same tail patch are worse: p99 14.5 mm, with 57 % past the fringe. A planted 2 % of 1.6× strays FAILs on both patches. | checked; **tail OPEN** (cause unchecked, see 4) |
| (5) Regrowth on the measured inset (J16) | Guard tips regrown on the measured inset: median −0.12 mm (back), −0.22 mm (tail), against ±fringe/2. The Phase 2 groom carried onto this skin FAILs on the tail (+1.92 mm, matching C8's +1.39 mm finding). Planted ×0.6 and ×1.4 lengths FAIL on both patches. | checked (stand-in skin) |
| Memory, whole body at real density | **23.3 M strands** (2,203 cm² of furred skin × palette density). That is about **2.6 GB in Blender** and **~5.5 GB in Cycles**, ~8.1 GB in all. Free RAM now: 2.65-3.05 GB. Blender holds 25.4 GB committed and a 2.0 GB working set. **The full body at real density does not fit this session.** See section 3. | Blender bytes: layout arithmetic (estimated). Cycles: estimated. RAM: checked |

## 1. Decision: how children are made

The brief offered three ways: UVs on the skin plus Blender's Interpolate Hair Curves; our own Geometry Nodes setup; or numpy children with a memory budget.

**Decision: numpy children, written per region, loaded as Curves.** Reasons:
1. **The checks see what renders.** C8 tips, C10 density, strays, ear tips and colour are all numpy checks. With GN children, the rendered strands exist only inside Blender's evaluation, and no check would see them.
2. **One child rule (J6).** A GN Interpolate Curves tree would be a second implementation of the child rule, and the two would drift.
3. **GN saves no render memory.** Cycles materialises the evaluated curves either way. GN only saves the file transfer.
4. **No UV map is needed for children.** Each child stores `root_tri` + `root_bary` on the skin it grew on.

**Rig deformation (later stage, *unchecked*).** Two ways:
- **(a)** A small GN group that re-seats each curve from `root_tri` / `root_bary` on the deformed skin. It uses Corners of Face → Vertex of Corner → Sample Index, and moves the strand in its root frame.
- **(b)** Deform Curves on Surface, with a generated per-face UV atlas. One cell per triangle, made in numpy, non-overlapping. That is 1,616² cells for 2.6 M faces: cheap, with no seams to design.

(a) is preferred, because it needs no UV map. Neither is needed for a still render.

**How a child is made** (`fur_v3.children`):
1. **Follicle groups.** Poisson at density/19 per mm². Each group holds Poisson(19) hairs: one guard lead, the rest awn or down by the palette fractions. Roots cluster within 0.08 mm (*estimate*).
2. **Shape.** Each child takes the inverse-square blend of its 3 nearest **regrown** guides' shapes, in the root frame (tangent, binormal, normal), normalised by length.
3. **Length (J16).** The guides' length per unit of inset (L/inset, which encodes the lie) × the inset **measured at the child's own root** × the type ratio (awn 0.85) × U(0.85, 1.15).
4. **Finish.** Direction jitter 6°. Crimp on awn and down. Per-point radius from the palette taper.
5. **Points per strand.** guard 6, awn 5, down 4 (Catmull-Rom in Cycles). Down is 83 % of the strands, so its point count is the main memory lever. Density stays at the real value.

## 2. Colour along the shaft (lilac points)

The rule is `fur_v3.shaft_colour`:
- **Where colour is sampled.** The target is `hair_rgb` / `hair_lilac_w` from `cat_p2_pigment.npz` (on v3: transferred with `pigment_attach.py`). It is sampled at the skin point under each strand's **tip**: a pixel shows hair whose root lies upstream (fur_plan 2b).
- **Root.** It blends the palette roots: white (0.95, 0.94, 0.93), lilac ground (0.90, 0.87, 0.90).
- **Band start.** The palette's position: lilac 0.45, white 0.90.
- **Tip.** Solved so that the mean of the visible outer shaft (guard/awn t ≥ 0.5, down t ≥ 0.7) equals the target. Down goes half-way.
- **When the tip cannot reach the target in [0, 1].** The band moves toward the root (0.35 → 0.05). That is the palette's stripe hair, "pigmented almost root to tip".
- **What is stored, per CURVE:** `col_root`, `col_tip`, `band_t0`. The shader computes the shaft colour from Curves Info → Intercept with a smoothstep. This saves 16 B per point against a per-point colour, about 1.6 GB at full density.

**OPEN.** The targets are apparent (lit) photo colours. Stage 4 tone match (`tools/tone_match.py`, `light.json`) must turn them into albedo before render. The done-when is a render ΔE against the photo through the camera (J12), which needs a validated camera.

## 3. Memory budget and render tiers

### Whole body at real density

| Type | Strands | Points | Blender GB | Cycles GB (est.) |
|---|---|---|---|---|
| guard | 1.14 M | 6.8 M | 0.16 | 0.40 |
| awn | 2.52 M | 12.6 M | 0.32 | 0.73 |
| down | 19.4 M | 77.7 M | 2.12 | 4.35 |
| **Total** | **23.1 M** | | **2.59** | **5.48** |

Ears add 0.24 M strands (`fur_v3_counts.json`).

**Byte layout.**
- Blender: 16 B per point (position + radius), plus 49 B per curve (offset, int8 type, colour root/tip, band, face, bary).
- Cycles: 16 B per key, 16 B per curve, ~48 B per segment for the BVH. *These are estimates.*
- numpy in the patch: 93-117 B per strand, measured.

### Rules

1. **Restart Blender before any full-coat render.** It holds 25.4 GB committed. Then render with no other heavy agent running (A24).
2. **T1 swatches (real density, any region):** about 80 k strands per 10 cm² patch, about 10 MB. This always fits. The coverage proof above is a T1.
3. **T2 full body at real density.** Generate per region, and load only the strands whose root faces the camera and is not occluded. That is about 55 % for one view: about 4.4 GB in all (*estimated*). This keeps real density everywhere the camera sees.
   - If it still does not fit after the restart, the next lever is down at 3 points: about −0.8 GB.
   - Lowering density is the last resort. It is then a stated fraction, written into the render's metadata (fur_plan T2).
4. **First action of the display stage:** load one T1 tile into Blender and read the real MB per 1 k strands. That replaces the layout arithmetic above with a measurement.
5. **Viewport:** a subset, as in fur_plan section 4, with the fractions stored on the object.

## 4. Stray control along the outline

The rule is `fur_v3.stray_control` / `stray_check`.

**When a strand is a stray.** Its outermost point stands past the fur envelope (Tripo) by more than the region's `photo_fringe_mm_p50` (coat.json, photo: back 1.2, chest 1.6, tail 1.75 mm). **Pass:** p99 ≤ fringe and max ≤ 2× fringe.

**What happens to a stray, in order:**
1. Its lie is flattened (height above the root plane scaled down).
2. If still out, it is shortened, but only within the palette length range.
3. Anything left is **flagged as a skin fault and sent back to the skin layer**, never absorbed (J16, J13).

**Tail patch: OPEN.** 97 guards and 116 awns are flagged.
- Probable causes (*unchecked*):
  - the tail tip's Tripo crater (J15: the tail tip had no owner);
  - the guide shape carried round the tail's tight curvature (radius ~12 mm against 26 mm hairs).
- Next step: map the flagged roots on the tail. If they cluster at the tip, it is the skin. If they are spread along the shaft, give children on high-curvature parts their own surface-following march (`hair_coat.grow_layer`), not the shape blend.
- The back and chest strays the person saw were **not** on the dorsal outline patch: Phase 2 guides PASS there. **Chest and flank outline patches have not been run** (*unchecked*).

## 5. Ear tips

The rule is `fur_v3.ear_tip_control` / `ear_tip_check`, applied per ear in the ear frame (`layers/ears.json`: tip, axis).
- Only `ear_tip_wisp` may pass the apex plane: at most 4 mm (palette: 2-4 mm visible), 5-8 hairs per ear.
- Every other ear type ends within 0.68 mm of the plane (coat.json ear photo fringe). Longer strands are shortened along their own arc.
- When rebuilding the ear hair on the v3 skin, cap the furnishing length at its root's distance to the apex. Then the control has nothing left to cut, and it stays as a check.

## 6. Order of work on the v3 skin

1. **Measure the inset** on the v3 skin against Tripo (`fur_v3.measure_inset`). Furless masks give 0, and the eye-socket lining is masked furless (PHASE2_ASSESSMENT 1 item).
2. **Regrow the guides** with `hair_coat.grow_layer`, with depth = the measured inset. Check the tips (J16).
3. **Make children per region** at palette density. Then run stray control and the C10 / tip / stray checks per region.
4. **Colour** (`shaft_colour`). Ear hair is regrown and passed through `ear_tip_control`.
5. **Display stage:** restart Blender, measure a T1 tile, then T2 with camera-facing culling.

## 7. OPEN

- The tail strays (section 4).
- The chest and flank outline patches have not been run.
- Colour: tone match to albedo, and a render ΔE through a validated camera.
- Rig deformation, (a) or (b): not built.
- Cycles bytes are estimated, and the T1 load measurement is pending.
- The density and fraction values are palette [C] / estimated sources (palette gaps).
- The cluster radius of 0.08 mm and the visible-shaft zones are estimates.
- The stand-in skin is cat_p2. The proof must be re-run on the v3 skin (J16).
