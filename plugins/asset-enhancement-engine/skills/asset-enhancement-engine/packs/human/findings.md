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

- **Height above a smoothed copy reads curvature, not relief.** A copy averaged 10 times over each one-ring
  ((x + mean) / 2) shrinks a curved skin by ~0.15 mm at 12 /m. On a breast patch of untouched skin it read the patch
  0.78 of the skin round it, the patch filled as a thin plate 0.76 and the patch with its relief tripled 0.77; the
  height above the quadric best fitting the skin within 10 mm read 0.99 / 0.07 / 2.97 (on the waist 1.03 / 0.75 /
  3.04, the around's own sector spread 0.84-1.12). Take relief above a local quadric. (woman2 build 13a3,
  a3_prove_relief.py.)

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
- **A breast carried as its height above its own chest wall keeps its volume on another body's wall.** v12's skin height
  above v12's wall, set on Blender Studio's base body's wall (the same smoothing-spline definition, read on the base's
  chest outside both bodies' breasts): 469.7 / 473.7 mL above that wall against v12's 469.9 / 473.7; the finished skin lies
  within -0.3..+0.3 mm (L) and -0.5..+0.7 mm (R) of the carried surface (p1-p99). Its axis turned 6-8 deg more lateral and
  5-7 deg more upward in the notch frame (2.8 deg of it the frame map's own turn). (woman2 build 13a.)
- **A move along a breast frame's axis folds the skin the frame sees edge-on.** The band round the carried breasts, moved
  by its height change along each frame's axis (tilted 28 deg laterally), made an S-fold 5-8 mm deep at the side of the
  chest (z -165..-180 mm); moved along each vertex's normal where that converged (11,668 of 13,561 vertices) and
  harmonically filled elsewhere, 0 folds over 90 deg and 0 crossings. (woman2 build 13a.)
- **Held to its outline on a different chest, a carried breast creases along it.** Where v12's outline met the base
  chest 0-6 mm apart, a correction held to the outline creased the upper-lateral rim (visible in clay); freeing the outer
  10 mm of the footprint where the outline is not a fold (upper half only) let the thin plate join them smoothly, volume
  restored (beta 0.002-0.005). Freeing it on the lower half folded v12's overhanging lower pole (its underside moved
  with the front's change). (woman2 build 13a.)
- **A step where a carried breast meets a held side is removed by one smooth fill, without a re-run.** On 13a the base
  body's protected side stood proud of the wall the breast was carried onto, so horizontal sections at each breast's
  outer side ran side -> step inward -> breast (an S-kink 1-2 cm across; a hooked crease of 62 deg on the right). The
  person's picked regions plus a 15 mm border, filled as the smoothest surface joining the held skin (cotangent
  bi-Laplacian, positions in full, 2.6 s): edge turn 62 / 32 -> 7.6 / 7.6 deg, curvature roughness 33 / 18 -> 1.1 / 2.0
  per m (the base body's own sculpt there: 2.1 / 2.6), moves up to 9 / 14 mm, the breast's volume over its wall +0.5 %
  (473.7 -> 476.0 / 469.7 -> 472.2 mL), nothing else moved. Border 10 / 20 mm: region turn 8.6 / 6.7 deg (R), 9.8 /
  6.7 (L), volume within 2 mL. (woman2 build 13a2.)
- **The chest-wall instrument's lateral outline is unstable on a smooth side.** It reads a breast's outline as the
  strongest concavity past the mound's turn; on 13a the step gave a strong one, on the smoothed side it is weak and
  moves: footprint width 171 -> 152 mm (R), 150 -> 160 mm (L), volume above the re-read wall 398 -> 415 / 412 -> 443 mL
  (422-450 L over border 10-20 mm), while the carry's volume over a fixed wall moved 0.5 %. Its fold share came nearer
  v12's 0.5 (0.76 / 0.64 -> 0.61 / 0.51). Read volumes over a fixed wall when only the side changed. (woman2 build 13a2.)

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
- **Rings that sample an areola at 0.5-1.2 mm lose its tubercles; the difference baked into the height map brings them
  back.** Per texel (27 um), v12's carried surface minus ours along our normal: p1/p50/p99 -27 / +3.5 / +40 um, up to
  +235 um at the tubercles; added to v12's nipple-areola height map, renders of the two match (explore3/q_nac3).
  (woman2 build 13a.)

- **A thin-plate fill erases the skin's relief; the body's own relief, read where that skin came from, brings it back
  without the defect.** 13a2's filled patches read 0.24x the relief round them (relief() p75, 10 mm) and looked
  blurry. 13a's own skin inside the picked patches was the deformation (2.4x the surroundings; carried back ungated it
  returned pieces of K2's crease). Read instead from v12's breast through the carry's side-frame map on the breast
  blocks (13a's unmoved breast skin correlates with it, r 0.45 / 0.55) and from the base sculpt on the protected side,
  gated against outliers (14.7 % left bare): 0.67x (L 0.82, R 0.52; the right's surroundings carry 13a's own build
  roughness, 1.4x v12's there), K2's place 4.8 / 1.9 deg (13a 62 / 29), moves up to 0.27 mm, nothing else moved.
  (woman2 build 13a3.)
- **Detail taken at the radius it is read at comes back at less than half.** Heights from relief() at r laid on a
  smooth surface read 0.44 of the source's relief at r; taken at 1.5 r 0.84, at 2 r 1.00 (planted, a skin-like test
  surface). Take detail at twice the reading radius. (engine/tools/test_fill_detail.py, build 13a3.)
- **Detail read on another mesh aliases into lines unless the source's vertex-scale ripple is averaged out first.**
  v12's and the base's heights read at our vertices drew grooves and notched shadow edges in raking light; two
  one-ring averages on the source mesh before reading removed them (inside/around 0.97 -> 0.67: a third of the
  matched "relief" was that ripple). (woman2 build 13a3, a3_detail.py.)

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
- **Adding loops to a quad grid in place: inset a block of it.** A grid rectangle of the base body's own quads kept and
  inset (rings of new quads between it and its old boundary) gives loops whose every vertex is valence 4, with poles only
  at the block's corners: 4 valence-5 on the old boundary and 4 valence-3 on the kept block's (6 + 6 with a notched
  corner). Three nested blocks per breast (breast, nipple-areola, tip): 28 poles a side. Placing the base loop's vertices
  at even angles from the nipple sheared the spokes against the block's long straight side (38-70 cm2 of crossing
  faces); at equal arc length matched to the block boundary's own arc fractions, with the transitions walked along the
  surface, 0. (woman2 build 13a.)
- **The base body's side stands proud of its chest wall beside a carried breast.** At the breast's side the base's
  protected side lies up to ~8 mm outside the base chest wall the breast rests on (explore3/e16_walls.png); v12's narrower
  breast sits inside it, joined by a 25 mm blend. (woman2 build 13a.)
- **Blender Studio's realistic female base body has a valence-5 pole under each breast's side,** at (+-0.13, -0.014,
  -0.21) m after x1.044: on the mid-axillary line 25-40 mm below and behind the fold. A grid walk past it is two-valued.
  (woman2 build 13a.)

- **A carried breast whose run-out was cut at its outline meets the chest at a corner.** 13a set v12's height on the
  base's wall only inside v12's outline, so the upper pole ran nearly straight into the chest and turned there: peak
  concavity on rays across it p50 18 / 31 per m (L / R; 6 of 22 right rays over 40 /m, the chest-wall instrument's fold
  mark) against v12's own junction at the same rays, 10 / 14. A thin-plate band +-12 mm round the outline (+10 mm fade;
  a smoothing spline whose data weight drops to ~0 in the band) took it to 9 / 12 /m, 0 rays over 40. The person had
  picked it as a crease. (woman2 build 13a4.)
- **That corner has a sharp core along the mesh's ring loops, which a detail-keeping resize keeps.** After a resize
  that scales only the smooth height (6 mm), relief() at 10 mm along the upper outline read 1.6-2x the pole's; the
  thin plate alone (finer relief kept) still 1.2-2x. Taking out the part of the finer relief that runs along the rings
  (averaged in bins of distance to the base loop and angle) and, within 5 mm of the base loop, putting in the same
  skin's relief from 22 mm further in along the ray: 0.83 / 1.26x the pole's at 10 mm, 0.83 / 1.03x at 5 mm (L / R). Replacing it
  with the sources' relief (v12 through the carry's map) left 0.3-0.75x: those sources are smoother than the carried
  skin. (woman2 build 13a4.)
- **A one-sided bulge beside a breast is removed by the other side's form, not by a thin plate.** A thin-plate fill of
  the right breast's bulge and divot (+12 mm) left the region 2.8 mm (p50) proud of the left's mirrored form, because
  its held edge on the side is proud (the base body's own asymmetry); giving it the left's mirrored form with the smooth
  offset between the sides carried in from its own edge took the bulge from p95 7.7 to 2.8 mm (the skin round it
  +-1.9 mm) and its most convex turn on lateral rays from 27 to 10 /m (the left's 3). (woman2 build 13a4.)
- **A smaller breast lights its outer side.** 13a3's carried relief on the outer sides, in the larger breast's shadow
  before, shows as soft undulations in raking light once the breast is smaller, though it is unchanged there (relief()
  at 10 mm changed by p75 0.004 mm); Blender Studio's own side renders smooth at the same place. (woman2 build 13a4.)
- **A nipple-areola held rigid on a flattened mound stands proud of it.** Translated as one body while the mound round
  it flattened by 25 %, its ring showed as an edge in raking light; riding on the mound under it (its own relief above
  the mound kept, the mound under it the smoothest surface joining the mound round it) shows none: areola diameter
  -0.5 %, nipple projection above the areola 2.33 -> 2.24 mm, the nipple's own shape within 0.15 mm. (woman2 build 13a4.)

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
- **A chest wall re-read from the skin round a carried breast is not the wall it was carried onto.** On build 13a the
  chest-wall instrument re-run on the finished skin reads 412 / 398 mL and a 44.7 / 43.7 mm projection (the carry's own
  wall: 469.7 / 473.7 mL; v12 48.6 / 48.9 mm): the re-read wall rests 2.9 / 4.0 mm higher on average, up to ~8 mm at the
  side, where the protected side is chest data. Margin 20 mm: 456 / 428 mL; fold threshold 60-80: 395-414 mL. The
  outline itself moved little (463 / 471 mL over the new outline against the carry's wall). (woman2 build 13a.)
- **Arms and armpits left untouched measure exactly as before:** inner-arm flat share 0.017 / 0.016, clearance p5
  4.1 / 3.8 mm with none under 2 mm, armpit vault 104 / 98 mm below the shoulder joint, on the scaled base and on 13a
  (v12: flat 0.04-0.19 by station, p5 0.5-0.6 mm, 22-24 % under 2 mm). (woman2 build 13a.)
- **Resizing a breast by its smooth height above its chest wall, footprint kept.** A factor 0.75 (moves along the wall's
  axis, folds held, the nipple-areola riding on the mound) took 472 / 476 mL to 355 / 355 mL on the wall it was carried
  onto (297-386 / 290-378 over that wall's settings); the wall re-read from the finished skin went 442 / 414 -> 325 /
  308 mL. Projection 49 -> 37.5 mm (-24 %), upper : lower share unchanged (0.53 / 0.58). The tape difference 17.0 ->
  14.3 cm: EN 75C -> 75B, US/UK traditional 34B -> 34A - one letter for ~117 mL (cited ~110 mL per letter, B2);
  underbust unchanged (74.55 / 75.03 cm on the wall). (woman2 build 13a4.)
- **What a breast's proportions do when its volume changes (measured on the same carry wall and footprint grid).** Kept
  footprint, height scaled (13a4): 472 / 476 -> 355 mL left the area standing 3 mm off the wall at 162 / 159 cm2 and took
  the apex 47.6 -> 36.0 mm, so apex over that area's radius fell 0.66 -> 0.50: a quarter flatter for its size, which
  the person saw as "squished". Kept proportions (13a5, mound_resize.resize_similar): at 355 mL with apex over radius
  held at the approved 0.665, the area fell to 144 / 140 cm2 (x 0.88 / 0.87) and the apex only to 45.1 / 44.4 mm (x
  0.95 / 0.93); the outline moved in 6-12 mm (fold up 6-8 mm, upper border down 11-12 mm, the outer side in 10-12 mm).
  A plain similarity of the approved form (s = 0.909 on width and height) read 375 / 373 mL and 0.63 / 0.65 on the same
  instruments: the skin round the breast that stands off this wall inside the footprint (the left's outer edge up to
  9 mm, p95; the right's 2 mm) counts as breast in volume and area but does not shrink with the breast. To read the approved proportions on this instrument the breast proper came out narrower than a
  similarity (width x 0.851 / 0.867) and taller (height x 0.944 / 0.926 of the approved form). Where the breast meets
  the held midline strip (the approved form's breasts already meet it, the valley 2 mm under the wall) it cannot narrow:
  there its inner wall keeps its place and is lowered by the height factor (24 -> 18 mm at 60 mm from the nipple).
  (woman2 build 13a5.)

## The Translator on human bodies (build L2: the human word list)

Bodies: woman2 13a (`cases/woman2/build13/pack_b13a/skin.npz`, 686k vertices; the pack's words were set on it), two
Blender Studio CC0 base bodies whose failures shaped later rules (`GEO-body_male_realistic` at multires level 2, 169k
vertices; `GEO-body_female_stylized`, 12.5k vertices), and one run at the end with the pack as it stood
(`GEO-body_male_stylized`, 12.5k vertices). Builds and numbers: `cases/human_l2/` (`summary.json`, `summarize.py`).

- **The held-out body (stylized male), first run:** torso, head, neck, arms, hands, legs, feet found and named (100 % of
  the surface); no fingers or toes part at 12.5k vertices; the head's fold lay at the neck's base, leaving a 59-vertex
  neck that does not ring the trunk, so the torso's seam with the neck was empty and its definition could not be laid
  (29.7 % addressed by the last fallback). With the torso's top seam bound to the neck and the head together (pack data;
  identical on the other bodies, where a neck lies between) the torso's frame lays: 99.0 %. (cases/human_l2/male_stylized.)

- **Walking-distance rings slide past a limb's junction; plane sections across the limb's own axis jump there.** From a
  hand's fingers the rings grew 4.5 -> 16 cm over 22 cm at the armpit (0.55 per unit length, under the generic 35 deg
  flare), so the generic pack left the arms in the "body". Sections across the limb's axis merge with the chest's (an
  arm) or the other thigh's (a leg) within a station: all six limbs of both realistic bodies were cut there. (woman2 13a,
  the realistic male.)
- **A ring's centroid slides toward a junction before its section does.** From a foot, the band centroids above the
  knee moved 19 cm across the crotch (x -10.8 -> +8.7 cm) and tilted the sections into the pelvis (the leg took the
  buttock); re-laid through the sections' own centres, the thigh's axis stayed at x -10.6 to -10.3 cm and the cut fell
  at the crotch. (woman2 13a.)
- **The average walking distance peaks at the chin; the walking distance from the centre does not.** The generic
  function gave the head two tips, the crown and the chin, and a 9 cm "protrusion" round the mouth (whole_13a); from
  the centre (the place of least average walking distance) the head has one tip. (woman2 13a.)
- **A tip's own scale finds toes.** At the body's step (8.6 mm, a 3.6 cm minimum shaft) no toe was cut; at a quarter of
  the tip's thickness and a shaft as long as it is thick: 4 / 3 toes on 13a, 3 / 3 on the male (the small toes are not
  tips at 0.57 cm persistence), 1 / 1 on the stylized female, none on the stylized male. Fingers: 5 per hand on both realistic bodies, numbered 1 (thumb)
  to 5 by their place front to back; none on the stylized body (its fingers do not part at 12.5k vertices).
- **A bent elbow cuts a limb in two; the pieces are one limb by structure.** On the male the forearm-with-hand was cut
  from its upper arm (the forearm's sections met the upper arm); a protrusion whose only grown child has children of its
  own takes it in (4 joins on the male, 2 on 13a, 2 on the stylized body). A rule by seam width (seam radius against the
  parent's mean radius) merged fingers into palms and legs into pelvises instead: dropped. (cases/human_l2.)
- **Where two limbs meet, the walk has reached the trunk.** The male's arms and head came out as one "protrusion" cut at
  the chest (0.20 of the surface, both arms and the head under it) until a part whose grown children each hold a quarter
  or more of it was refused, and a head or an arm holding more than one hand's tips was left unnamed (then joined to the
  trunk, shallowest first). (realistic male.)
- **The narrowest section finds the wrist and the ankle, if the walk skips the toes.** Wrist girths (loop length): 13a
  16.2 / 16.2 cm, male 16.4 / 16.4, stylized 13.0 / 13.0; ankle 20.6 / 20.6, 21.0 / 21.0, 14.5 / 14.5 (21-23 cm up from
  the toes' tips on the realistic bodies). Walked from the toes the narrowest section was at the toes' seams (0.4 cm in,
  15.5-19.1 cm): the search starts at 10 % of the limb. (cases/human_l2.)
- **A fold plane under the jaw holds where the bends ring the neck.** 13a: 23 of 36 directions, the plane 10.1 deg off
  square to the axis, rms 0.16 cm; the stylized body: 30 of 36. On the male the bends nearest the neck lay on the face's
  folds, not round the neck (a fitted plane 75 deg off square cut the face away): a plane square to the axis through
  their median is used there (tilt_limited). Recutting the neck's base at a fold the same way gave planes 22-87 deg off
  square, rms 0.4-3 cm: not kept. (cases/human_l2.)
- **The neck's base is where its sections flare into the shoulders, 5 cm above the jugular notch.** The torso's origin,
  the most anterior point of its seam with the neck, lies 5.26 cm from woman2 13a's measured notch (-0.02, -1.77, +4.96
  cm: higher and in front), so the neck is short at the front and the torso's y numbers run from that point, not from
  the notch. OPEN. (woman2 13a against its pack's `measurements.json` frame origin.)
- **Breasts as mounds above the front skin's own course.** The front skin as a height field, its 6 cm Gaussian course,
  the skin 0.3 cm or more above it: on 13a two mounds, tops 3.94 / 3.84 cm, 186 / 183 cm2, IoU 0.71 / 0.71 with the
  pack's own painted breast zone (weight >= 0.5: 186 / 182 cm2; the zone was not used to find them). The male's
  pectorals stand 2.48 / 2.50 cm, the stylized female's breasts 2.69 cm (one mound across the mid-plane): the 3.0 cm
  threshold separates 13a from the male but misses the stylized breasts. A thin plate fitted under the skin with
  asymmetric weights (a profile baseline) passed under the whole front instead (one 2,600 cm2 mound 12-13 cm high): the
  chest's own turn is as large as a breast. (cases/human_l2.)
- **The torso as its own definition addresses nearly all of a realistic trunk by the frame's x and y.** 13a: 105,926
  vertices, 99.4 % addressed (chest 48,677, front 17,892, back 29,012 by discs; 5,062 by rings; the rest build-09 tube);
  male 99.7 %; stylized female 95.9 % (there the discs addressed 478 of 2,454 vertices and the rings 1,684: discs need
  finer skin); stylized male 99.0 %. Measured: trunk 72.1 / 72.7 / 61.6 cm; arms' seams 39.5 / 45.9 / 29.9 cm apart; waist (the narrowest section
  between the hips and the chest's lower edge) 67.4 / 80.0 / 49.4 cm. (cases/human_l2.)
- **A head is no tube.** The generic tube chart's rings over a head's cap ran away (339k grid points on the male's
  48k-vertex head, 404k on the stylized 2.6k-vertex head: 28-30 MB pages) and its build-09 rings addressed 46-56 %; with
  face and back discs round the head's centre: 99.3 % (13a), 92.5 % (male), 96.7 % (stylized). A neck between its two
  seams: 99.5 % (13a), 100 % (male), against 56 % for the generic template on 13a. (cases/human_l2.)
- **A planted capsule figure is not a human body to this pack.** Capsule legs standing under an ellipsoid trunk were not
  cut at a crotch (IoU 0.25-0.29 with the leg) and a foot at right angles to its leg was cut at the ankle as a "leg": the
  method leans on what real bodies have, thighs that meet at the crotch and a heel that makes its own tip. Not kept as a
  proof. (build L2 exploration.)
- **Addresses name the same place only on the build they were picked on.** The Translator's pages say addresses keep
  naming the same place; that holds for one build (rebuilding the same part, or a tool change: build L3, build A1's
  regression, 0.0 mm). Across builds it does not: the person's 930 right-breast lines picked on 13a, re-read on 13a2's
  parts, missed on 298, because the breast frames moved 1.1 / 2.3 mm (L / R) and turned 2.1 deg when the chest wall
  was re-read on the reshaped skin (build 13a2, measured). Pick again on each build, or carry picks as vertex ids /
  surface points, not as frame addresses. Even on 13a's own parts 82 of the 2,351 pasted lines resolve to nothing (74
  picked at a vertex, 8 at a grid point; why is not measured; the same 82 before and after builds L3 and A1).
  (cases/woman2/build13/picks_deformation_2026-10-21.md; `python engine/tools/language.py regress`.)
- **Not addressed well yet:** feet (13a 94.5 / 66.5 %, male 81.5 / 62.9 %, stylized 46.7 %: the generic tube on an
  L-shaped part falls back), hands 96.7-96.9 % (84 % stylized), the stylized body's neck and toes (42-49 %).
  (cases/human_l2.)

### The head's own parts (build L4: ears, eyes, nose, lips, the inside of the mouth)

Bodies: woman2 13a4 (`cases/woman2/build13/pack_b13a4/skin.npz`), the realistic male and the stylized female (tuned
on these three), the stylized male held out to the end; K1's skin with and without its eyes. Builds, sheets and checks:
`cases/human_l4/` (`summary.json`, `checks/`, `shots/*_sheet.png`). Tool: `engine/tools/part_features.py`; data: the
human pack's `features` block.

- **Every feature found on the four bodies; every other part rebuilds identical.** Ears, eyes, nose and lips on all four,
  the inside of the mouth where the model has one; on each body the parts other than the head rebuild array for array
  as before (28 on woman2 13a4 against a build of 13a4 with the L2 pack, 27 / 13 / 11 on L2's own stored builds; only the
  build folder and the pack's fingerprint differ), and the head before = the head after plus its features, face for
  face. (`checks/compare_*.json`.)
- **Measured against cited sizes (a check, not an input).** woman2 13a4 / realistic male: ear height 5.8-5.9 / 5.7 cm
  (cited 5.5-7.0, head_face.md F16, F17); eye opening (the lid-margin creases) 3.5 / 3.6 cm (fissure 2.8-3.1: the creases
  run past the canthi, x1.18-1.22); nose width 3.6 / 3.9 cm (al-al 3.1-3.5, x1.10-1.17: the border falls on the cheek
  past the alar crease); lip line 5.9 / 6.5 cm (ch-ch 5.0-5.5, x1.13-1.24). The stylized heads are not human
  proportions (eye openings 5.2-7.1 cm); on the stylized male each ear runs down onto the jaw behind the cheek (12.5 cm
  tall, seen in `shots/male_stylized_sheet.png`): there the skin below the ear stands out of the course too. (`summary.json`.)
- **Where each border falls.** Ears: where the skin comes within 0.02 R0 of the skull's course (2.0 mm on woman2,
  R0 = 9.79 cm: the head's median course radius), plus the ear's front seen from its side inside its outline closed by
  0.08 R0 (the concha); the root's front, at the tragus, is that outline (estimate). Eyes: the socket (sunk 0.1-0.3 R0
  below the course) and the lid-margin creases (a 0.49 cm ball cannot reach them), then the lids: every skin within
  0.09 R0 of the margins and the convex skin to 0.18 R0, so the border is the lid crease where it lies within 1.8 cm and
  a band 0.9 cm out elsewhere (estimate: a band, not a measured crease, below the eye). Nose: 0.03 R0 (2.9 mm) above the
  course, capped at the eyes' openings and at 1.3 x their inner corners from the mid-line (from the cited al-al / en-en
  0.99-1.05). Lips: the convex skin round the lip line, out to the concave ring round the lips (mean curvature under
  3 / R0 = 31 /m), between the corners; measured on realistic meshes, coarse on 2.6k-vertex heads.
- **The inside of the mouth is a part of its own.** woman2's and the realistic male's heads hold a mouth lining (206 /
  135 cm2, back to 12 cm behind the lips) cut off from the rest of the head by the lips; it would otherwise be a piece
  of the head with no way to it. The nostrils' passages go to the nose (each vertex to the nearest feature along the
  skin), each eye's socket floor to its eye.
- **The nose tip is the most prominent point of the front mid-line between the eyes' level and 0.6 R0 below it.** The
  most anterior mid-line point was the forehead on the realistic male (his head leans so); the most prominent
  anywhere was his lips, and the stylized female's chin. Finding the eyes first and searching below them held on all four.
- **Held out (stylized male): ears, eyes and nose held; the lips did not, at first.** The widest crease across the
  mid-line below the nose was the crease under the nose and round the nostrils (8.0 cm wide), not the mouth (6.8 cm),
  so his lips part lay under the nose. A rule "wholly below the nose" found the mouth there but cut the stylized
  female's lips to 1.5 cm (dropped). Kept: a crease that borders the nose (an edge to it) is the nose's own, unless no
  other crosses the mid-line (the stylized female's lip line runs along her nose's foot). Same lips as before on the
  three tuning bodies (woman2 13a4: the same 26,550 faces); the held-out male's lips on his mouth. Made after the
  held-out run, so the lips are no longer a blind check on any body here.
- **The eyes' globes go with the eyes.** K1's skin with its two eyes in the model: every one of the 20,544 globe faces
  per side went to its eye (the sclera as a shell set in the socket, the cornea and iris as pieces). K1's skin alone:
  every part as on 13a4 (face IoU 0.95-1.00; the right eye 0.82, its socket skin laid on the globe). With the eyes in the
  model the head's fold under the jaw was not found and the neck stayed in the head (L2's split; the eyes are their
  own file in K1's pack, so the skin alone builds with a neck). (`checks/k1_check.json`.)
- **What the head keeps.** The head's frame is read on the whole head (base and crown with its features), so it stands
  where it did; its own skin is addressed 88 % (woman2 13a4, was 95 % with the features), 90 % (male, was 92.5 %),
  74 % (stylized female, was 96.7 %), 82.5 % (stylized male, was 98.4 %): the face disc's meridian walks stop at the
  features' borders (on woman2 40,859 of the face chart's 88,165 vertices got no walk; 37,415 head vertices are
  addressed by build 09's kind only). Moving the face chart's axis up to the brows (62 % of the head's height) did not
  help (62.6 / 74.1 %). OPEN: a chart laid on the whole head and read on the head's own skin.
- **L2's fold under the jaw is not under the jaw on every body.** On 13a it ran through the mouth (the lips and the chin
  in the neck), on the realistic male through the chin, on the stylized female through the lower lip and both earlobes;
  on 13a4, the same head, it lies under the jaw (widest station 26.0 -> 19.8 cm: the cut follows the whole body's walk,
  which the resized breasts moved). L4 leaves the neck as L2 cut it, so the stylized female's lips and earlobes are
  partly in her neck. On 13a4 the right breast (2.91 cm high) also falls under the pack's 3.0 cm mound threshold. OPEN.

## Mesh soundness (build K1: a base body's own faults)

- **A sculpt's faults sit on a sound subdivision surface; refill the sculpt's displacement there, not the positions.**
  Blender Studio's realistic female base body (cage x3 + multires sculpt) carried 787 folds past 90 deg, 159 inside-out
  faces and 3,439 crossing pairs at 12 places; the cage subdivided x3 without the sculpt (same vertex order) has faults
  only at the two eye-socket floors. Refilling the sculpt's displacement over the unsculpted surface (bi-Laplacian,
  cotangent weights of that surface) at the smallest radius of 1-6 mm that left a place clean fixed 16 places with 0
  new faults: 1 mm at finger roots, thumbs, ear and nose; 1.5-4 mm at the toe roots (moves up to 11 mm inside the toe
  gaps; depth maps from above / below: 1-4 % of rays moved over 0.1 mm). (woman2 build K1, `cases/woman2/buildK1/
  k1_fix.py`; `engine/tools/mesh_repair.py refill`.)
- **A position fill across a pleat between two close parts makes it worse.** The same toe root (2nd-3rd, left) filled
  as the smoothest patch (uniform weights, 1.5 mm round the fault): 334 -> 535 crossing pairs, moves 5.8 mm (the patch
  spans both toes); refills of the turned-out vertices repeated 4 times did not converge (folds 43 -> 61 -> 101 -> 118 ->
  94). The displacement refill cleaned it at 2 mm. (woman2 build K1, explorations `x03_try.py`, `x06_pleat.py`.)
- **The winding number just inside each vertex tells a pleat from a contact.** ~0 = the skin there is turned inside out
  (a pleat), ~2 = it lies inside another part (two parts pressed through each other). Measured: toes 2nd-3rd L 74
  turned / 4 inside (pleat), ear L 54 / 0 (pleat), toes 4th-little L 0 / 151 (contact), lips L 0 / 288 (contact).
  (woman2 build K1; `mesh_repair.turned`, proof `test_mesh_repair.py`: 1 / 2 / 1 / 0 at planted points.)
- **Contacts separate in one step when "inside" is the winding number, not a nearest face's normal.** Half the depth
  each (along the vertex's inward normal to the first face it meets), 0.04 mm film, eased over 4 mm: toes 4th-little
  147 / 153 -> 0 pairs and lips 379 / 348 -> 0 in one iteration, moves 0.15-0.43 mm, still touching (vertices within
  0.1 mm of the other part 46 -> 143, 212 -> 502), the lips' closing line seen from the front moved at most 0.2 mm.
  An inside test by the nearest face's normal sign against a labelled sheet diverged (334 -> 11,300 pairs in 12
  rounds): open patches give false insides. A straight-on ray grid still finds 5 of 45,261 rays passing the 0.04 mm
  film at the lip line. (woman2 build K1.)
- **The base body's eyeball is not a sphere, and its socket skin lies inside it.** GEO-body_female_realistic.eye (546
  vertices, scaled x1.0442): sclera fit 12.22 mm outside the front cap (rms 0.24 mm), its front cap 1.3 mm inside the
  sphere fitted to the back half alone, gaze 4.6 deg outward; its corneal bulge 0.83 mm (cited 1.0-1.2, eye.md B7). The
  socket's skin lay inside a 12.22 mm globe with a cited cornea at 1,563 L / 1,245 R vertices, up to 1.07 mm deep
  (most of it the lining behind the lid margins; the rim in front of the limbus moved at most 0.27 mm when laid on the
  globe). The socket floors sit 3.2-4.5 mm behind the globe (p50 3.5-3.7 before their refill, 4.2-4.5 after). (woman2 build K1,
  `k1_eyes.py`.)

## Rigging the whole body (build 13b: the shoulder's topology, the girdle on all its axes, weights, mixed skinning)

Measured in woman2 build 13b (`cases/woman2/build13b`, its pack `pack_b13b`) on K1's body (Blender Studio's base, 686k
quads). Instruments: `engine/tools/quad_grid.py` (mirror_map, grid_line), `quad_relayout.py`, `pose_study*.py`.
- **The base body's mesh is an exact topological mirror, but only a walk on a near-symmetric parent finds it.** Walked on
  the unsculpted level-3 base (it mirrors itself within 0.15 mm p50) and carried to the skin through base_index, every
  one of 686,416 faces matched, 0 conflicts, 0 valence mismatches, 13a's inset rings included. Walked on the sculpted
  skin itself (shape off its mirror by up to 13 mm; the breasts 5.6 mm p50) the walk shifted by a quad near poles: 977
  twins of the wrong valence. A walk seeded on the face (an asymmetric spot) shifted everything (2.8 % agreement).
- **The base body's shoulder already holds most of the loop list.** 75 / 77 closed rings round the upper arm, 2.37 mm
  apart, spacing CV 0.05, tilt p50 10 deg (max 23); one edge loop runs along the deltopectoral groove (100 % of it within
  2.6 mm) and one along the anterior axillary fold (92 % within 5 mm). No loop follows the deltoid's posterior border or
  the posterior fold (51-61 % within 5 mm), and the skin shows no groove there to follow (mean curvature +6.5 / -0.8 per
  m along the paths). Poles: a 3-5-5 cluster at the front of each armpit (60-80 mm below the joint), a 5 at the back
  (94 mm below); six or seven within 25 mm of the lower base loop (the base's own beside the notch, 13a's inset corners).
- **A pole can be slid out of the armpit over the skin's own surface, if the vault's crease holds.** Moving the front
  cluster 30 mm and the back pole 19 mm in a 100 mm patch (`quad_relayout.relayout_surface`): 0 faces turned, the form
  kept within 1.07 mm (p99 0.23 mm), the patch's smallest quad corners p1 57-59 -> 43-44 deg (the single smallest 31-38
  -> 6-10 deg: a few slivers next to the held crease). Dragged across the vault's crease (mean curvature
  under -60 per m) the chords cut it by up to 8.6 mm; 26-28 mm moves without the hold turned 2-5 faces. Laid out flat
  instead (a conformal map of the armpit), the moves landed up to 150 mm off: the map's scale varies too much there.
- **K3 read with exact twins: the right breast's rings are the left's plus a smooth difference, except a dent at the
  notch.** In each breast's own frame the right rings run 4.5-6 mm smaller over the lower pole and 3-4 mm larger at the
  top (the breasts' own difference); at 330-358 deg the base loop fell a further 8.8 mm in (the notch). Removing the dent
  (the difference taken straight across 318-358 deg, three passes) left 0.75 mm. 13a's outline instrument still reads
  42.6 mm: v12's carried right outline bulges 24 mm at 0-15 deg, the bulge 13a4 replaced with the left's mirrored form.
- **B14's scapula numbers are thoracic; driving the AC joint with them counts the clavicle twice.** With the clavicle at
  its cited SC values (RET +16, ELE +11, PAR +31 at max) and the AC joint driven to the ST targets, ST upward rotation
  read 73-75 deg at max elevation (target 40-55). With the AC terms refitted so SC then AC gives ST (ridge least squares
  over 12 anchor poses), 54 of 69 target checks fell in range, 63 within 5 deg (B14 D10's tolerance).
- **The rib contact moves the scapula's inferior angle by up to 38 mm at the extremes.** Driven alone, the inferior angle
  ran 28 mm into and 38 mm off a glide surface 13 mm under the back's smoothed skin (max elevation, reach across); held
  on it by Shrinkwrap targets with Damped and Locked Track, it stayed within 8 mm.
- **Bone heat on the base's cage, subdivided, gives a clean arm-to-torso transition on the dense skin:** steepness p99
  0.019-0.020 per mm, max 0.041-0.061 at the armpit (v12's own: 0.27-0.40). It also put 12 % upper-arm weight in each
  breast's outer half and 0.53-0.84 clavicle (0.02 scapula) on the upper trapezius, where v12 held 0.07-0.37 clavicle
  and 0.30 scapula.
- **Per region, dual quaternion wins at the shoulder top and the elbow, linear wins in the armpit, arm and side.** Summed
  over 20 test poses, both sides: shoulder crossings 126 -> 70 cm2, collapse 11.2 -> 6.1 (volume change 3.4 -> 8.9);
  armpit crossings 47 -> 16 cm2 but sheets 28 -> 1,008 cm2; upper arm sheets 25 -> 167 cm2; side sheets 87 -> 776 cm2;
  elbow volume change 1.5 -> 0.5 (linear -> dual quaternion). Build 12's v12 finding (sheet 173 -> 1065 cm2) holds on
  a clean mesh with smooth weights.
- **The cited skin slip leaves little of the scapula's motion to the skin over it.** The rig's acromial angle, spine
  root and inferior angle travel 44 / 34 / 89 mm at 146 deg HT; the skin slips 30 / 53 / 70 mm behind (B11 D6, 10
  men), so the skin follows 32 / 0 / 21 % of the bone (25 % used as the floor; estimate).

## Corrective shapes by computation (build 13c: the whole range of the arm and the girdle)

Measured in woman2 build 13c (`cases/woman2/build13c`, pack `pack_b13c`) on 13b's body and rig. Instruments:
`engine/tools/pose_correctives.py`, `pose_samples_bl.py`, `pose_study*.py` (build 12's), `bvh.inside`.
- **Restoring the skin's own rest shape on a region (as-rigid-as-possible, rotations started from the skinning
  Jacobian's polar part) removes most of linear skinning's damage away from contact.** Coronal 170 deg, region of 158k
  vertices: crossings 564 -> 0 pairs, sheets (area x4) 20.3 -> 3.5 cm2, creases over 30 deg 449 -> 27 cm, the held
  edge moved 0.07 mm. Over the 20 test poses with the keys: crossings 288 -> 123 cm2, sheets 450 -> 43 cm2, armpit and
  shoulder creases 2,108 -> 346 cm; between the keys' nodes 83 -> 31, 164 -> 19, 851 -> 155.
- **Three local-global steps, not more.** The same sample's creases fell 443 -> 33 cm at 2-3 steps and rose to 80 cm by 8:
  with a near-free core the solve buckles where the armpit must shorten. A second pass continuing the iterations
  (after the breast) raised them 27 -> 50 cm; one global step with the first pass's rotations kept them at 27 cm.
- **A pose fix stored as a rest-space key needs each vertex's skinning Jacobian, and Blender can give it exactly.** Three
  unit shape keys read d(posed)/d(rest) off the mixed linear / dual-quaternion armature (0.4 s per pose for 686k
  vertices); the stored keys reproduce the computed posed skin within 0.004 mm. Its singular values reach 0.27 in the
  armpit (blended bones turned far apart), so rest offsets run up to 2-3x the posed fix (max 134 mm).
- **Keys on a pose grid with hat weights cover the range continuously; residual keys must be narrow.** Grid knots e 55 /
  90 / 130 / 170 deg x plane rows, 0 at the rest elevation; a residual key for a compound pose with 30 deg half-widths
  leaked 0.11-0.19 of itself into two grid nodes (3.6 mm off there); 15 deg (e, p) / 20 (a) / 30 (elbow) left every
  sample exact.
- **The breast as a soft incompressible mass under its envelope moves 2-7 mm, and only one tissue family keeps it in
  range.** With R9's gravity-fitted family (breast 0.25 kPa, skin 4 kPa x 1.44 mm = 5.8 N/m) and density 951 kg/m3 the
  overhead poses press the top and outer side in by up to 5-6 mm and the patch keeps its rest volume (381 mL by the
  chest-wall depth; skinned 410-433). With the in vivo suction skin (344 kPa, R7: 495 N/m) on the 0.25 kPa mass the
  linearised membrane moved the breast 10-20 cm: a small-strain local skin value cannot be paired with a whole-breast
  gravity fit. Reading the envelope's stretch on the skinned skin (sheets of x4-x43 at the axillary tail) gave 100 mm;
  read on the restored skin, a few mm.
- **Pushing contact apart vertex by vertex does not clear crossings.** Across-body 90 deg: by closest point on skin far at
  rest (face normals misread the side at edges; with interpolated normals the same), by arm-against-torso labels (the
  shoulder cap and chest are both "torso"; an open arm patch reads torso vertices as inside), and by ray parity on the
  closed skin (0 of 4,000 rest vertices read inside; 3,270 -> 125-200 inside after one push) spread harmonically or
  biharmonically: the inside vertices came out but triangle crossings rose 2,578 -> 2,900-25,600 pairs round the pressed
  patch every time. Without a contact solve the contact poses improve only through 1: T5 33 -> 24, T6 38 -> 31, T13c
  36 -> 17 cm2.
- **The corrected skin steepens the neck line in the full raises** (front chord T2b -40.7 / -38.8 -> -48.7 / -45.4 deg,
  T1b -40 / -39 -> -50 / -50; rest -29): the shoulder's rest form is carried up with the bone-pin clavicle rise instead
  of being stretched flat. The chord measure flips by 15 deg between sides in some mid poses on 13b as well.
- **Skin slip over the scapula with the correctives** (T1b, 165 deg HT): spine root 36, inferior angle 63 mm (13b 32 / 80;
  B11 D6, 146 deg, 10 men: 53 / 70). The nipple moves up 9-10 mm, out 8 mm and back 3-6 mm overhead; notch to nipple
  -8 mm (B11 D9's tables say +20 mm standing, its text "shortens").
- **A breast made taller moves more when posed, and meets the arm sooner** (woman2 13a5: 355 mL, apex 36 -> 45 mm, the
  correctives recomputed by 13c's own stages): the breast's posed change RMS x 1.21 p50 (max 1.62) over the 33 test
  poses; with the arm across the chest the crossings rose 24.0 -> 28.0 cm2 (T5) and 25.3 -> 28.0 (TM5) and the armpit
  creases 38.8 -> 49.2 cm (T5 L); without contact only T1b's left armpit crease rose past 13c's L-R spread (3.6 ->
  4.8 cm).
- **A chest wall re-read on a resized breast is a new mesh, and its own weights must be made again.** On 13a5 the wall
  read on the smaller footprints has 31.6k vertices against 13b's 40.6k; with 13b's cw_idx / cw_w the posed wall came
  through the skin (depth p5 -16 mm) and the breast envelope pushed the breast up to 41 mm out (pressure +100 Pa
  against 13c's -10). Remade by 13b's own rule (nearest skin vertex's weights, 20 smoothing passes): u -5 to +6 mm, as
  13c. Blender's check of the keys (posed = computed) cannot see this: the wall is not part of the skin. (woman2 13a5.)
