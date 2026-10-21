# Fur plan for cat1 (Phase 2, Stage 5): how strands are grown from the follicle palette

Written 2026-10-18 by the hair builder. **Status: SPEC.** Nothing in it has been built or proven yet.

- **Data:** `follicle_palette_cat1.json` (this folder). It holds the hair TYPES, the MAP, the whisker layout, the sources and the gaps.
- **Criteria:** C8, C9, C10, C13 and C14 in `engine/log/PHASE2_ROUND0.md`. These are approved, including the person's additions C13 (whiskers are real hair) and C14 (ear hair types).
- **Every value** carries a source and a confidence level (G2). Values without a source are marked ESTIMATE.

## 1. Representation (decided)

| Item | Decision | Why |
|---|---|---|
| Blender | 5.2.1 (`bpy.app.version`, read-only query 2026-10-18) | — |
| Hair system | **Hair curves** (`Curves` datablock), attached to the skin through `surface` + `surface_uv_coordinate`. Rig deformation uses Deform Curves on Surface. **No particle hair.** | groom.py and accessories.py already build Curves, so we reuse them (A16). Curves are driven by Geometry Nodes. Particle hair is the legacy system: no GN, weak children, no per-point attributes. |
| Body coat | Python **guides** plus **Geometry-Nodes children**. Children come from Distribute Points on Faces (Poisson) at the palette density, then Interpolate Curves (built-in, 3.5+: Guide Curves, Guide Group ID, Points, Point Group ID, Max Neighbors). Type modifiers follow: length, taper radius, crimp, clump and colour along the shaft. | Render density is defined by the palette, not by a strand budget. Guide Group ID keeps partings crisp: children never blend across a tract border such as the nasal reversal crest, the ear margin or the lid margin. *Verify on 5.2 that the node exists (list node types, read-only) before building.* |
| Tactile hairs | **Explicit curves**, one per follicle, 24 points each. Not interpolated. | Each whisker is an individual, checked structure (C13). |
| Ear furnishings, tip wisps, sparse inner hair | Their own guide group, or explicit curves for the tip wisps, with GN children | C14: these are their own types, not back-of-ear fur |
| Shader | Principled Hair BSDF, coloured directly from the point attribute `hair_col` (the colour along the shaft). Whiskers use roughness 0.18 (accessories.py `M_Whisker`). | Colour is a property of the hair (E6). Nothing is painted on the skin under the fur. |

## 2. Data flow

1. **`follicle_map.py` (new, A16).** It writes skin POINT attributes from the palette map regions, using the region rules in `coat.json` and coat_field.py:
   - `dens_guard`, `dens_awn`, `dens_down` (per m²; Blender's unit is per m², so 93 /mm² = 9.3e7 /m²);
   - `len_guard`, `len_down`;
   - `ear_zone` (back / rim / furnishing band / inner skin / canal / pocket);
   - `w_lilac`, `w_stripe` (from the Stage 4 photo projection; see 2b);
   - `tract_id` (guide group).

   The canal and the furless masks set every density to 0, with a 2 mm ramp at the canal.

   **2b. Pigment goes on ROOTS.** Each follicle's colour is its own. A visible pixel shows a hair whose root lies upstream, so the photo projection is moved upstream along `hair_dir` by about L·cos(lie) before it is written to `w_lilac`. groom.py samples colour at the tip for the same reason. A follicle GROUP draws once (lilac vs white, stripe vs ground) and all its hairs share the draw.

2. **`hair_field.py` (exists, E3).** It writes `hair_dir`: the hair-tract prior turned toward the photo flow (`cases/cat1/photo_flow.npz`) where coherence is at least 0.30. The sign of the direction comes from the prior.
3. **Guides (from groom.py's `roots()` / `grow()` / `comb_field()` / `ear_clip()`, reused).**
   - Spacing: about 1 guide per 3 mm² on the body, 1 per 1 mm² on the face and 1 per 0.5 mm² in the ears. That is roughly 80-120 k guides.
   - Lift and lie per type come from the palette.
   - Length is the region's guard length (scaled per type later).
4. **GN tree `FollicleGroom` (new).** One Distribute → Interpolate branch per type. Then, per type:
   - set the length from `len_*` × the type ratio (awn 0.85, down from `len_down`) × jitter U(0.85, 1.15);
   - set the radius as (base diameter / 2) × taper profile(Spline Parameter), with the profile and tip ratio from the palette;
   - add crimp (down and awn: a sinusoidal offset perpendicular to the strand, amplitude and wavelength from the palette);
   - clump per follicle group: a group of about 19 hairs has its own clump centre. Group spacing is 0.45 mm on the back. This is the clump unit suggested in cat-hair-streams (c).
   - write `hair_col` from Spline Parameter through the type's colour stops.
5. **Tactile builder (from accessories.py `whisker_set()`, rewritten).** Roots come from `whiskers_mystacial_layout` plus the other tactile entries.
   - Each root is snapped to the skin and then sunk by the follicle depth along −normal, so the first point sits in the follicle.
   - Centreline: Cesàro curvature κ(s) = A·s + B with B ≈ 0 and A = 2θ/L². The curve lies in the plane of the emergence direction and down-rostral. The inside segment runs straight up to the skin.
   - Radius falls linearly from r_base to r_base/ratio, with ratio 7-13 (typical 10).

## 3. How each property is set

| Property | Rule | Source (see JSON) |
|---|---|---|
| Density | Per region, all hairs per mm², split by type fraction: guard 0.05, awn 0.11, down 0.84 | coat.json values are [C] (hepper). The growth-mass bracket gives 4,700-9,500 /cm² (ESTIMATE). Group structure: LeRoy 2016 [A], Ryder 1976 [B], Noel & Hu [A] |
| Length | Guard and down from coat.json per region; awn 0.85 × guard; ear types from the photo | Ryder 1976 [A], Lehmann 2020 [A], photo |
| Direction | `hair_dir` (E3). Prior: tail-ward on the body, down the limbs, nasal reversal toward the nostrils, ear interior up and out | Mivart [A], Kidd 1900/1903 [A]. The face sides and ears have no source, so the photo flow decides there |
| Lift / lie | Guard root 20-40°, lying to 4-14°. Down erect 35-55°, lying to 15-30°. Furnishings 6-14°, half at the tip. | groom.py v37 (person-reviewed) + ESTIMATE |
| Taper | Guard: uniform to 0.7 L, then to 0.2. Down: uniform. Whiskers: linear, base:tip radius 7-13 | Gandolfi 2013 [A], Williams & Kramer 2010 [A] |
| Diameter | Guard 47 µm [A]. Awn 30, down 15, furnishing 25 µm (ESTIMATE). Whiskers: D = 0.0023 L + 0.056 mm (rat relation, Belli 2017) → 125-212 µm | LeRoy 2016, Belli 2017 (low confidence for cat) |
| Colour | Colour stops along the shaft per type, chosen per follicle group by `w_lilac` / `w_stripe` | Kaelin 2012 [A] (band order), photo / photo_markings.json (colours) |

### What the photo says, used above

- Legs, paws, muzzle, chin, throat and chest are WHITE. This contradicts the brief's point list: the photo shows a lynx point with white.
- Lilac appears on the forehead/crown stripes, the eye surround and cheek bars, the whole tail (about 5 dark rings and a dark tip), and possibly a faint caudal-thigh patch.
- Ear backs are unseen; they are filled by the colourpoint rule and flagged.
- Each ear tip has a small **wisp** of about 5-8 hairs projecting 2-4 mm. It is not a lynx tuft.
- Dense pale furnishings cover the medial half of each inner pinna.
- 2-3 supraorbital hairs per side are visible.
- The longest mystacial whisker is at least 61 mm projected (on the cat's right). The image scale is 0.35-0.38 mm/px at the face, from the eye spacing and the frozen camera. coat.json's 0.27 mm/px does not fit the face; flagged.

## 4. Strand counts, memory and the viewport subset

**Skin area.** The Tripo envelope area, measured on face-referenced vertices, is 2,527 cm². The skin, inset by the coat depth, is about 2,150-2,350 cm² (ESTIMATE).

**Hair count at the palette density.** About **23 M** in total:
- guard ≈ 1.2 M
- awn ≈ 2.6 M
- down ≈ 19.5 M
- furnishings ≈ 15-20 k
- tactile ≈ 50 curves (24 mystacial, ~8 supraorbital, ~4 genal, ~3 chin, ~10 carpal)

**Memory.** At 8 / 7 / 5 points per strand and about 32 B per point in Blender (position, radius, colour), that is about 4 GB before Cycles copies it and builds its BVH. Full density everywhere at once does not fit this 16 GB machine alongside everything else. The plan:

| Tier | What renders | Purpose |
|---|---|---|
| T0 | The palette density IS the definition. Every type is generated from it, and nothing is hand-tuned to a budget. | — |
| T1 swatch tiles | 100 % of every type, real diameters, on 1-4 cm² patches per region | C10 density and swatch checks; close-up renders |
| T2 full body | Guard, awn, furnishings and tactile at 100 % (about 3.9 M curves). Down at a **stated fraction f_down**, chosen from a measured memory probe (MB per 1 k strands per type, from a T1 tile), starting at 0.25. Diameters are NOT inflated to compensate: the undercoat is mostly hidden. | Full-body render. f_down is written into the render's metadata and the log as the one stated exception to real density. |
| Viewport | Per-type density factor × fraction, applied by GN Is Viewport before Distribute (cheaper than deleting afterwards): guard 3 %, awn 1 %, down 0.5 %, furnishings 25 %, ear tip wisps and tactile 100 % | The fractions are stored as object custom properties `viewport_fraction_<type>` and printed in the build log, so the person knows the viewport is a subset |

## 5. Checks (A10: each one counts only after it catches its planted failure)

| # | Check | Tool (reuse first, A16) | Planted failures it must catch |
|---|---|---|---|
| **C8** tip envelope | Sample 200 k guard/awn tips at T2. Per region, take the signed distance to the Tripo envelope with `tripo_rebuild/twosided.py` MeshDist (proven). Pass: median within ±(region coat-depth spread)/2, and p95 no farther out than the envelope + spread. Furless masks are excluded. | twosided.MeshDist + coat.json regions | One region's lengths × 1.3; down lengths × 2 |
| **C9** directions | hair_dir against the photo flow at coherence ≥ 0.30, mod 180°. Also a render through the frozen camera, re-measured with photo_flow.py. The pass angle is set by its A10 proof (start: median ≤ 20°, no 15 mm patch > 45°). | `hair_field.py`, `review/flow_marks_check.py`, `tools/photo_flow.py` (exist) | A 15 mm patch rotated 90°; the nasal reversal removed |
| **C10** density and locks | Root counts per type in 20 random 1 mm² windows per region of a T1 tile, compared with the palette (within 3√N). `review/fur_swatch_score.py` (exists) on T1 renders against close-up references. | New `density_check.py` (small) + fur_swatch_score | Density halved; the down layer missing; clumping off |
| **C13** whiskers | New `whisker_check.py`, for each tactile curve:<br>(a) the object is CURVES, never a mesh tube;<br>(b) the root is ≥ (follicle depth − 0.5 mm) under the skin, and the strand crosses the skin exactly once within 0.5 mm of its snapped root;<br>(c) base diameter is in the type's range;<br>(d) radius never increases, and the base:tip ratio is 7-13;<br>(e) length is within ±6 mm of the table (mystacial) or the type range;<br>(f) counts per row, side and group are right (12 per side in 4 rows; carpal 4-6 per fore leg);<br>(g) it is smooth (turn per segment < 10°) and the total turn is in range. | New tool; accessories.py layout code reused | A root floating 1 mm off the skin; no taper (ratio 1); 11 whiskers on one side; a mesh tube; a 0.6 mm base; one whisker kinked 30° |
| **C14** ear hair | New `ear_hair_check.py`. Per ear zone (Phase 1 ear masks + pink mask + canal opening + SDF side test from coat.json): type label, root density and length against the palette ranges; zero roots in the canal; ear-back type only on the convex side; tip wisp present (5-10 hairs) and no long tuft. Furnishings are compared with the photo ear crop through the frozen camera using `review/ear_crops.py` + `compare_regions.py` (exist). | New tool + ear_crops + compare_regions | Hair in the canal; furnishings removed; back-of-ear fur used inside; a 15 mm lynx tuft added |

## 6. Order of work (Stage 5, in stages)

1. **Prove the checks (A10).**
   - Build the small new tools first: follicle_map, whisker_check, ear_hair_check, density_check.
   - Prove each one on planted failures, using synthetic curves on a test patch of the Phase 2 skin. This waits for the skin agent.
2. **Tactile hairs first** (C13): they are few, explicit and cheap. Show them in the viewport against the clay skin.
3. **Ear types** (C14). Then a **T1 swatch** per region (C10). Then **T2** (C8, C9).
4. Record each new tool and the reasoning behind it in `engine/log/TOOLMAKING.md`.

## 7. Open items (from the JSON `gaps`)

- **Cat vibrissa base diameter.** No measured value was found, so the rat relation is used (low confidence). Sources tried:
  - Williams & Kramer 2010 and Luo & Hartmann 2023 give no cat diameters;
  - Dougill et al. 2023 and the Noel & Hu SI were blocked (403).
- **Cat per-area hair density.** Only a [C] value plus an estimated bracket.
- **Counts for the supraorbital, genal and chin vibrissae.** Photo hints only for the first two.
- **Mystacial layout.** The per-row split (3 × 4) and the row length factors are estimates. Ahl's general mammal layout has 5 rows.
- **Face-side, periocular, chin, throat and ear-surface directions.** No source; the photo flow decides, otherwise the prior applies (flagged).
- **Ear backs are unseen.** The caudal-thigh lilac patch may be spill from the tail colour.
- **Scale.** coat.json's 0.27 mm/px disagrees with the 0.35-0.38 mm/px measured at the face. The orchestrator should reconcile which reference each one used.
