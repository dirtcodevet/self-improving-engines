# Findings on human subjects (measured; not rules, not models)

Each entry: what was done, what resulted, the measurements and the proof, and where it was measured. They are evidence
for the engine to weigh on a new subject (the person's D30, 2026-10-20: "if you do x, then y is the result and here are
the measurements and proofs"), never a definition of the subject or a default. Case code that produced them stays in
its case (cases/woman2/lib, cases/woman2/recipe/stages). Cited research: references/*.md.

## Measuring

- **Sections through a feature's own axis see what a frontal outline cannot.** On a breast's lower-outer slope, curvature
  along planes through the nipple axis (every 10 deg) found a flat band 21-31 mm beyond the areola edge, 9-20.5 mm long,
  at 0.14-0.44 of its neighbours' curvature; the cited frontal-outline measure (catenary alpha', Lee 2012) read inside
  its normal range on the same breasts. Proof: a planted 15 mm band recovered within 0.5-2 mm at the skin's noise.
  (woman2 run 1, a breast's lower pole.)
- **A label from a whole-surface scan is not a measurement.** Patches named by the scan's region labels were read as
  "breast flats" and were arm vertices. (woman2, before run 1.)
- **Curvature-based roughness can invert the truth.** It read arms 65 % rougher than the abdomen while normal deviation
  from an 8 mm-smoothed copy read them smoother (96 vs 115-128 um); the real defect was a tail of sharp 1-2 mm folds
  (dihedral p99.9 15-28 deg against 6-7 on the back). (woman2 v7, upper arms.)
- **High dihedral percentiles find small folds.** Upper arms p99.9 28-40 deg (worst 53 deg at the arm root) against the
  back's 7.0 and the forearms' 7.3 on the same mesh. (woman2 v12, run 5.)
- **A whole-mesh scan's smoothing scale must follow the local edge length.** Scaled by the global mean edge (pulled to
  ~0.5 mm by a dense patch), a "5 mm" window acted over ~15 mm on 1.8 mm regions. (woman2 v7.)
- **Counts of crossing triangle pairs or crease edges follow the mesh's density; areas and lengths compare bodies.** At
  90 deg on the same rig, the base body (677k vertices) had more crossing pairs than v12 (278k), 2870 against 2166, and
  less crossing skin, 8.4 against 23.3 cm2. (woman2 build 12, engine/tools/pose_study.py.)

## Shaping

- **Smooth normal bumps restore a redistributed curve without touching its neighbours.** 7 x 4 bumps per breast
  (-2.2..+3.8 mm, +12.1 mL) took flat bands from 9-20.5 mm to 0-5 mm; the nipple-areola and the fold moved 0.000 mm.
  (woman2 run 1.)
- **A deterministic farthest-point placement makes a regular ring.** Glands placed that way on an areola read as evenly
  spaced; random size-weighted sites with a minimum gap (2.5 mm) and per-site size/height/elongation read irregular
  (3 and 5 per side). (woman2 run 2, Montgomery tubercles.)
- **Scaling only a radial median keeps the misfit and the old long waves.** Grain stayed 16 um at 3.6 mm wavelength
  until the disc was scaled above a quadric + degree-4 surface fit. (woman2 run 2, areola.)
- **Blending a model surface back to an old one over a ring can raise a bump.** 0.38 mm over 2.3 mm became a 2.1 cm2
  bump the whole-surface scan flagged. (woman2 run 2.)
- **A footprint defined by the surface being fitted feeds back and runs away.** A breast footprint taken as "skin above
  the wall" grew the volume to 760-2570 mL as the window widened; outlines read from the skin alone did not.
  (woman2 run 4, chest wall.)
- **A smoothing prior's error across a hole belongs to the body; measure it by holdout on the same body.** The chest
  wall's prior sat 3-6 mm proud at side and sternum spots, 0.6 mm on the abdomen. (woman2 run 4.)
- **Arm-form fixes that are not checked with the arm raised create raised-arm overlaps.** A section-goal fit with
  fairing cut fold sharpness away from the root (34 -> 12.6 deg) but left the root band (52 deg) and the raised-arm
  sweep then failed. (woman2 run 5, stopped.)

## Carrying detail

- **Relief finer than ~0.5 mm moves well to a height map.** Two nipple-areola patches of 278k vertices at 0.09 mm
  rebuilt at 14.4k vertices with a 16-bit height map at 27 um texels: surface vs the original RMS 1.7/3.7 um, p99
  5.1/5.5 um; grain and fold Rq 3-4 % low (bilinear sampling); torso 542k -> 279k vertices, pose 3.6 -> 1.6 ms, build
  1.66 -> 0.85 s, .blend 108.5 -> 54.8 MB; render contrast 0.96-1.05 of the original in every ring. Relief that
  shows in outline (tubercles, 0.36-0.43 mm peaks, 8 % lost at 0.5 mm) stayed geometry. A height map cannot hold folds
  that fold over in projection (82/279 um misses on a papilla wall). (woman2 run 3.)
- **16-bit colour maps load as float.** A first map set cost 82 MB more RAM than the geometry it replaced; 8-bit sRGB
  colour matched to p99 0.003. (woman2 run 3.)
- **Render-time displacement depends on mesh density.** Pore displacement realised 24.7 um RMS on a dense ring and 23.1
  on a 0.5 mm band (17 % weaker contrast) until the difference was baked into the map. (woman2 run 3.)
- **Zipping a rebuilt patch to old skin needs an inversion test.** A rim that turned back round the patch axis folded
  3-12 triangles to 179 deg at the seam. (woman2 run 3.)

## Junctions

- **A limb built pressed into the body cannot be repaired in place.** On one torso, the stage that made the arms laid
  the inner upper arm flat against the side wall, fused to it. The band where arm met body kept a flat inner arm
  (flat share of the inner-arm section 0.14 / 0.16, L / R), sharp folds up toward the armpit (172 edges folded past
  150 deg; curvature jump max 9.2 / 25.6; normal change p99.9 127, max 221 deg/mm) and creasing along the rib cage.
  Three in-place repairs (v5, the clean-up pass, run 5) and a fit to a generator's model (build 07, whose arm is welded
  there too) left the band as it was. (woman2 v10-v12.)
- **Moving the work onto a body with its arms out improved the fold numbers but not the junction.** A CC0 base body
  with its arms out was posed down to the torso's arm angle, fitted onto the torso outside the band (surface distance
  p50 0.0 mm, p99 3.0 mm) and kept its own skin inside it, moved with the band's rim, with a 2 mm gap left where the
  lowered arm meets the side. The fold measures improved (flat share 0.14 / 0.16 -> 0.06 / 0.06, folded edges
  172 -> 0, curvature jump max 9.2 / 25.6 -> 0.8 / 0.7, normal change p99.9 127 -> 37 deg/mm) and a 0-90 deg pose
  sweep ran with 0 overlaps, yet the person's review rejected it: the inner arm was reshaped and a slit opened between
  arm and side. None of those measures sees the junction's anatomy (a continuous padded axillary crease, arm down);
  they read folds and flatness only. (woman2 build 08; 5.2 M new tokens, 191 min.)
- **The width of the arm-weight transition decides whether a posed arm crosses the body.** A 30 / 70 mm transition left
  825 crossings in the posed band; 80 / 150 mm left none. Linear skinning; dual-quaternion skinning was not tested.
  (woman2 build 08.)

## Posing the shoulder (arms from 6 to 180 deg from vertical)

Measured in woman2 build 12 (engine/tools/pose_study_bl.py and pose_study.py; case files cases/woman2/build12) on v12,
build 08 and Blender Studio's realistic female base body (multires level 3), each posed at 6, 90, 135 and 180 deg and
compared with its own rest. Zones follow the joints (the tool's docstring). Crossing = skin passing through skin, as the
rest area of the crossing triangles; crease = rest length of edges whose dihedral rose over 30 deg; sheet = triangles
grown over 4x in area. Linear skinning unless named. Figures: cases/woman2/build12/figs.
- **A limb modelled touching the side leaves the armpit as a slit.** v12's frontal section through the shoulder
  joints: arm and side are parted by a slit that reaches 27 / 32 mm (R / L) below the joint; 22-24 % of the inner upper
  arm lies within 2 mm of the side (p5 0.5-0.6 mm); 172 edges are folded past 150 deg at rest at the slit's top, 34-38 mm
  below the joint. The base body, modelled arms out (19.4 / 19.6 deg): an armpit vault 94-99 mm below the joint, the
  inner arm at least 3.9 mm (p5) from the side, no folds. Build 08, the base body's skin in the band: vault 106-110 mm.
  (rest meshes; figs/rest_sections.png.)
- **The base body's skin is a regular grid with loops round the arm; v12's is isotropic triangles.** Vertices off the
  usual valence: 1 % on the base body, 18-57 % on v12 (50-57 % at the shoulder and trapezius). Upper-arm edges within
  20 deg of the bone axis or its ring: 65 % on the base body, 59-60 % on build 08, 46-50 % on v12 (44 % for random
  directions). Median edge at the arm, shoulder and armpit 2.2-2.6 mm against 1.6-1.8 mm; breasts 2.9 against 0.6 mm.
  Triangle quality is not the difference (minimum-angle p1 20-28 deg on both). (rest meshes.)
- **A steep arm-to-torso weight step at the front of the armpit stretches into a sheet as the arm rises.** v12's own
  weights go 0 -> 1 over 2.5-3.7 mm at their steepest (0.27-0.40 per mm), 57-58 mm in front of and 65-68 mm below the
  joint (armpit transition p10 33-41 mm). On our rig without the corrective shapes, the skin there grew over 4x: 59 cm2
  at 90 deg, 173 cm2 at 180 deg, with 27 / 61 cm of new creases in the armpit. Bone-heat weights on the same mesh and the
  same motion (steepest 0.048 per mm, p10 69-71 mm): 1.3 / 12 cm2 and 2.4 / 23 cm. Build 08's own weights step
  0.25-0.93 per mm across its 2 mm slit, 109-114 mm below the joint: 17-18 cm2 per side stretched to 185-201 cm2 by
  90 deg. The base body's bone heat (at most 0.047 per mm) on Rigify at 180 deg: armpit creases 2.1 cm, crossings
  0.2 cm2, sheet 15 cm2, against v12 on its rig 100 cm, 1.9 cm2, 270 cm2. (woman2 build 12; agrees with build 08's
  transition-width finding.)
- **On a body built touching itself, bone heat creases where the same rig and weighting on an open body does not.** v12
  under Rigify's bone heat, same rig and motion as the base body: at 90 deg 60 cm of creases on the trapezius and 90 cm
  on the side against 0 and 0; at 180 deg 12.7 cm2 of crossings in the armpit against 0.2. Its bone-heat arm weight is
  steeper on the trapezius (gradient p99 0.016-0.017 against 0.0036-0.0038 per mm). (woman2 build 12; the mechanism
  inside the bone-heat solve was not traced.)
- **A Rigify rig fitted by moving its metarig's bones left the spine and legs off the body, and bone heat followed
  them.** In both generated rigs of the rig test (cases/woman2/rigtest/bl_std_rig.py) the DEF spine and leg bones run
  from the body out to x -14.3 m (base body) and -18.6 m (v12); the thighs lean to the subject's right and pass 12-20 mm
  (v12) and 38-62 mm (base body) from the right hand bone. Right wrist and hand skin took thigh weight (v12: 932
  vertices, all on the arm; base body: 1303 from the left thigh), stayed behind as the arm rose and stretched: v12
  73-80 cm2 -> 930-1350 cm2 at 90-180 deg (also on our rig with those weights mapped on), base body 122 -> 898 cm2 at
  180 deg (the strands in the shots). The right side wall holds 33-35 % spine weight against 3-4 % on the left. Arm-only
  poses don't move those bones, so the shoulder comparison stands, but the right-side sheets on Rigify are the fit's,
  not the meshes'. (woman2 rig test.)
- **The girdle's movement decides how the neck and trapezius read.** Our rig (glenohumeral : scapular 2:1 above
  30 deg): the shoulder joint rose 30-32 mm at 90 deg and 77-82 mm at 180, the trapezius 3.3-3.7 / 6.9-8.4 mm, and the
  front contour from neck to shoulder flattened from -37 / -34 deg to -21 / -18 deg with a 6.8-8.5 mm concave sag. Rigify FK
  (its shoulder control at rest): joint 0 mm, trapezius -1 to -4 mm (pulled down by the arm), contour unchanged
  (-31 to -37 deg, sag at most 1.2 mm), the rigid straight neck line seen in the shots. The same girdle turn on Rigify
  (its shoulder control turned by our clavicle elevation) raised the joint 69-74 mm and the trapezius 12-15 mm on both
  meshes. (woman2 build 12.)
- **A breast moves with the arm only if arm or shoulder bones hold part of it.** v12 and build 08: breasts 100 % on
  the chest bone, untouched by the corrective shapes: nipple shift 0.0 mm in every pose. The base body on Rigify:
  87-92 % on its breast bones (children of the chest): 0.0 mm. The base body on the rig test's quick rig (root, head,
  collarbones, arms; bone heat): 4-5 % arm and 8-9 % collarbone weight on the breast; at 180 deg the nipple moved
  +16 / +15 mm outward and +23 / +18 mm up with our girdle movement, +10.5 / +8.8 and +14 / +10.5 mm without it; the
  breast changed shape by 14 mm RMS. The shift seen on the base body came from that weight; the girdle added about
  40 % of the rise. (woman2 build 12.)
- **Corrective shapes made up to 90 deg and held beyond it make the overhead pose worse.** v12's keys (abd15-abd90,
  abd90 held at 1 above 90 deg): at 90 deg they cut the armpit sheet 59 -> 15 cm2 and crossings 0.2 -> 0, and added
  8.8 cm of creases on the upper arm (15 edges past 90 deg; 0 without). At 135 deg shoulder creases 23 -> 72 cm,
  crossings 0.9 -> 3.1 cm2; at 180 armpit creases 61 -> 100 cm, sheet 173 -> 270 cm2. The right keys carry larger
  offsets in the stretched armpit (abd90.R up to 94 mm, left 51) and moved the right sheet up to 84 mm (left 48): right
  sheet 166 cm2 against 91 at 180 deg. (woman2 v12 on its rig.)
- **At 180 deg linear skinning pinches the top of the shoulder on every body.** Skin passed through itself 0-40 mm
  lateral of and above the shoulder joint: 10-12 cm2 on v12, 13 on the base body (Rigify), 17 on the base body (quick
  rig, our girdle movement), 17-18 on build 08; the zone's inward thickness fell under half its rest value at 45-84 % of
  its vertices. Dual-quaternion skinning on our rig, whose 180 deg is 124 at the shoulder joint and 50 at the scapula,
  removed it on v12 (all crossings 17.2 -> 1.7 cm2, none at the shoulder) and inflated the shoulder (cone volume about
  the joint x2.2 against x0.86 linear; an open patch, approximate) and the armpit sheet (173 -> 1065 cm2). On Rigify FK,
  all 180 deg at one joint, it stayed (15-21 cm2). (woman2 build 12.)
- **Lowering the base body to arms-down depends on what holds its armpit.** Bone heat on Rigify gives its breast bones
  a third of the armpit (0.33-0.35); adducted from its modelled 19.5 deg to 6 deg, the arm crossed into the side over
  13.8 cm2 (upper arm 5.9, side 5.0, armpit 2.6 cm2). The quick rig's bone heat (armpit 63 % arm): 0.6 cm2. (woman2
  build 12.)

## Volumes and sizes

- **Tape girths read as a convex hull of the horizontal slice.** Underbust 74.1 cm, bust 94.1 cm on one torso gave
  EN 75D, JIS 75E, US/UK traditional 34C, US/UK modern 29H: sizing systems disagree for the same body. (woman2 v8-v9.)
- **Breast volume against a chest wall:** 470 / 474 mL (444-509 / 458-503 over 12 settings), projection 49 mm, on a
  body measuring 34C traditional; cited 34C ~410 mL +-25 %. Underbust on the wall 73.9 cm vs 79.8 cm for a tape at the
  fold level (it bridged the lower poles). (woman2 run 4.)
