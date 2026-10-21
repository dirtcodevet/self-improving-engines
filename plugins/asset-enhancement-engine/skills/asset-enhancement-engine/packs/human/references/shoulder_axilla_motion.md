# Shoulder, armpit, breast and neck in motion (arms down to overhead): cited anatomy and rigging practice

Compiled 2026-10-20 (build 11) from open full texts and abstracts (six PDFs saved as `reference content/research
papers/shoulder_axilla_motion_*`), the add-ons and blends in `reference content/Blender woman generation stuff/` (read
from zips or in background Blender; nothing installed) and `cases/woman2/woman2_rigtest.blend` (read only). strong =
several studies agree; single = one study; weak = abstract/snippet, secondary, practitioner, or my derivation; (calc) =
my arithmetic; (checked) = measured by me this session. Rest posture, layers, fold height: `arm_axilla_lateral_torso.md`.

## 0. How it is built and how it moves (my words)
1. The arm hangs from a chain of three joints, not one: sternoclavicular (SC, the only bony link to the trunk), then
   acromioclavicular (AC), then glenohumeral (GH). The scapula glides on the ribs (scapulothoracic). Raising the arm
   overhead is roughly 2 parts GH to 1 part scapular upward rotation after a first ~30 deg that is mostly GH (S1-S3).
2. The clavicle does three things as the arm rises: elevates (bone pins: about +6 to +11 deg; old radiographs:
   25-30 deg), retracts (about +16 to +20 deg) and spins backwards on its own long axis (about 30 deg) (S1, S3). The
   S-shaped clavicle's spin lifts its lateral end; the acromion therefore rises and moves back and in, the upper
   trapezius shortens, and the neck-to-shoulder line steepens. This is the "shoulder line disappears" seen overhead.
3. The scapula rotates upward 40-60 deg, tilts posteriorly 20-30 deg and rotates externally about 24 deg; upward
   rotation is roughly linear with elevation, while tilt and external rotation happen mostly after 90 deg (S2). Up and
   down paths differ by under 5 deg, so a rig needs no up/down hysteresis (S1, S2).
4. Skin does not follow bone: over the scapula it slides 3-7 cm relative to the bone at full elevation, mostly
   upward (S6). Across the upper torso the surface moves up to ~8 cm at 170 deg abduction, most at the upper lateral
   chest, least low and medial (S9).
5. The deltoid shortens as it lifts the arm (about 4 cm over the GH range, calc from moment arms) and stiffens; the
   pectoralis major, latissimus dorsi and teres major, which form the front and back walls of the armpit, lengthen by
   about 5-6 cm each (calc, S8). Their stretched lower borders are the two axillary folds overhead.
6. The armpit hollow is pulled in by the axillary fascia (suspensory ligament of the axilla) when the arm is abducted
   (S14); with the arm down the walls meet in a fold. No study measures the hollow's depth or the fold geometry.
7. The breast lies on pectoralis major fascia, ribs 2-6, sternum to mid-axillary line, with an axillary tail and a
   loose retromammary layer that lets it slide (S15); raising the arms stretches the pectoral attachments and
   suspensory ligaments (S18). Measured nipple moves are few and disagree (section 4). Sex: women may use more GH and
   less scapular upward rotation than men (S4, S5); studies conflict, 11-19 per sex.

## 1. Measurable descriptors (rig and mesh) and cited targets
| # | Descriptor | Target | Source | Conf |
|---|---|---|---|---|
| D1 | GH elevation : scapular upward rotation | 2.1:1 abduction, 2.2 scapular plane, 2.4 flexion (S1); GH:total scapulothoracic 1.7:1 (S2); 2:1 after a ~30 deg setting phase (S3) | S1-S3 | strong |
| D2 | Scapular upward rotation, rest to max | +39 (11 -> 50 deg, to 120 HT) (S1); 50 +/- 4.8 (S2); 32-64 across 8 studies (S2 table) | S1, S2 | strong |
| D3 | Scapular posterior tilt; external rotation | +21 (S1), 30 +/- 13 (S2); external 24 +/- 12.8 (S2); mostly beyond 90 deg | S1, S2 | single each |
| D4 | Clavicle elevation; retraction; posterior axial rotation | +6 (11 -> 17; rest 5.9) bone pins vs 25-30 radiographs; +16 (23 -> 39; rest 19.2); 0 -> 31 deg | S1, S3 | single each; elevation conflicts |
| D5 | Acromion displacement, rest -> 120 deg HT, clavicle 14 cm | up 2.6 cm (S1 angles) to 6.8 cm (S3 angles); back about 4 cm; in about 2.7 cm | calc from D4 | weak |
| D6 | Skin slide over scapula, 4 -> 146 deg HT | acromial angle 30.4 mm (IQR 25.9-33.2), spine root 53.1, inferior angle 70.0; superior parts 24.5 / 42.7 / 58.7 mm | S6 (10 men) | single |
| D7 | Upper-torso skin displacement at 170 deg abduction | total 79 mm upper lateral down to 15 mm lower medial; vertical 68-83 mm; medial-lateral 47-65 mm at 90 deg | S9 (FE + motion capture) | weak (abstract) |
| D8 | Muscle length change over GH 10 -> 120 deg | middle deltoid about -4 cm; inferior pectoralis +5; middle latissimus +5.5; teres major +6 cm | calc from S8 moment arms | weak |
| D9 | Nipple position, arms overhead vs down (standing 3-D scan) | sternal notch-nipple straight 194.5 +/- 16.6 vs 174.5 +/- 15.0 mm (R); nipple-nipple straight 193.2 vs 192.2; nipple-IMF 62.6 vs 61.5 | S10 | single, internally contradictory |
| D10 | Nipple position, arms raised vs akimbo (supine CT) | each nipple 1.5-2.0 cm more medial (to midline L 10.7 -> 9.2, R 9.9 -> 7.9 cm); craniocaudal no change | S11 (6 girls) | single, wrong posture |
| D11 | Axillary hollow depth, fold separation, fold geometry overhead | NO VALUE FOUND | - | none |

How to measure (my method): (a) read clavicle elevation/retraction/spin and scapular upward rotation/tilt from the posed
bones at humerothoracic 0/30/60/90/120/150/180 vs D1-D4; (b) track an acromion landmark (D5); (c) sternal notch,
nipple and IMF landmarks, arms down vs up (D9, with its caveat); (d) vertex displacement in the scapula frame near the
spine root and inferior angle (D6); (e) collapse/creasing: per-edge length ratio posed/rest (`stretching_gn_overlay`
shows it) plus a self-intersection test in the fold; no cited compression limit, so report the distribution;
(f) origin-insertion distances (sternum to humeral crest, iliac crest to humerus) vs D8.

## 2. Joint kinematics (detail)
| Item | Value | n, population, method | Citation | Conf |
|---|---|---|---|---|
| Rest (standing), bone pins | clavicle retraction 19.2, elevation 5.9; scapula upward 5.4, anterior tilt 13.5; GH elevation 0.8 deg | 12 (7 M, 5 F), 22-41 y; transcortical pins + EM sensors | S1 | single |
| Plane differences | GH plane of elevation differs up to 46 deg flexion vs abduction; scapular upward rotation +3 deg in abduction at 90-120 | same | S1 | single |
| SC vs AC share | most scapulothoracic upward rotation comes through the SC joint (clavicle), the rest at AC (+11 deg upward, +19 tilt, +8 internal at AC) | same | S1 | single |
| Linearity | upward rotation and clavicle motion about linear beyond 50 deg; tilt and external rotation mostly beyond 90 deg | 8 (5 M, 3 F), pins | S2 | single |
| First 30 deg | scapula contributes about 2.5% of motion in the first 30 deg; whole-arc ratio 2.34:1 | 13 healthy | secondary via search (PMC3377910) | weak |
| Sex | men more upward rotation (20-110 deg, p<0.05), women more internal rotation, tilt equal; women GH-dominant; women +5 deg external rotation, equal upward | 19 F 20.5 y EM skin sensors; 11 F; 11 F | S4; S5; S5 (Liege) | single each, conflicting |
| Max humerothoracic elevation | 146.1 +/- 4.5 deg (upright CT, 10 men); clinical norm 180 | S6; skeleton.md | single / standard |

## 3. Soft tissue: skin, muscle walls, armpit
| Item | Value | n, method | Citation | Conf |
|---|---|---|---|---|
| Skin-bone slide over scapula | see D6; inferior angle marker also moves medial 22.5 mm, posterior 12.1 | 10 M, 21.6 y, upright CT, arms down vs max | S6 | single |
| Skin strain field at shoulder, abduction and flexion | exists (3D digital image correlation, MIT space-suit work, IEEE 2016); values not reachable | - | S19 | none read |
| Deltoid | middle deltoid abduction moment arm 8.3 mm at 2.5 deg -> 29.1 at 86; anterior 2.0 -> 30.2 at 120 | 8 cadavers (4 F), 81-98 y | S8 | single |
| Deltoid stiffness | shear-wave speed higher at 90 deg than 0 deg; reference 4.9-7.1 m/s at 90 deg; thickness did not affect elasticity | 70 adults (35 F) | S17 | single (abstract) |
| Pectoralis / latissimus / teres major | adductor moment arms peak -33.6 (inferior pec, 64 deg), -38.6 (middle lat, 64), -46.1 mm (teres major, 83) | S8 | S8 | single |
| Pec major tendon | two laminae, posterior (sternocostal) lamina inserts higher on the humerus (twisted) | Gray's text | S14 | weak; "untwists overhead" NOT FOUND |
| Armpit hollow | produced mainly by traction of the axillary fascia (suspensory ligament) when the arm is abducted | Gray's text | S14 | weak (textbook) |
| Hollow depth, fold-to-fold distance, fat pad behaviour | NO VALUE FOUND | - | - | none |

## 4. Breast and nipple with the arm
| Item | Value | n, method | Citation | Conf |
|---|---|---|---|---|
| Standing, arms overhead vs at sides (pre-op) | SN-Ni surface 192.9 vs 177.5 mm R, 194.6 vs 177.4 L; straight 194.5 vs 174.5 R, 200.8 vs 180.6 L; midline projection 165.0 vs 143.8; Ni-Ni surface 209.5 vs 203.3; text says arm elevation "shortens" SN-Ni and Ni-Ni, the tables show lengthening | 45 F (90 breasts), 33.6 y (22-55), Caucasian; Artec handheld 3-D scan | S10 | single; use with caution |
| Supine, arms raised vs akimbo | nipples and breast centroids 0.9-2.0 cm more medial with arms raised; total separation -2.8 (breast) / -3.0 cm (nipple); no craniocaudal difference (p>0.05); larger breasts move more (r 0.85) | 6 girls (pediatric lymphoma), CT, 107-1063 cm3 breasts | S11 | single; supine, adolescent |
| Apparent volume by posture | lowest with arms overhead; about 23% between largest and smallest shape across postures | depth-camera scans (J Text Polym 2021;9(1):13) | S12 | weak (snippet) |
| Scan practice | arms up improves lateral-breast visibility but breast shape changes because of skin movement and muscle tone | 3DBODY.TECH 2018 | S13 | weak |
| Clinical exam | arms overhead "stretches pectoral attachments and suspensory ligaments" and shows the lower half | nursing text | S18 | weak |
| FE breast + pectoralis model, abduction 30-90 deg | pectoralis E 0.1 MPa clavicular, 0.08 sternocostal; validated on motion data; no displacement in abstract | elderly women | S16 | weak |
| Standing nipple shift up/laterally in mm with arms overhead | NO DIRECT VALUE FOUND | - | - | none |

## 5. Production practice: methods
| Method | What it does / evidence | In Blender? | Conf |
|---|---|---|---|
| Linear blend skinning (LBS) | shrinks geometry toward zero at 180 deg from rest; candy-wrapper on twist (P10, P2) | Armature modifier default | strong |
| Dual quaternion (DQS) | no shrink or candy-wrapper (P2) but bulges around joints, shown on the chest (P3), and jumps at 180 deg from rest (P10) | Armature "Preserve Volume"; LBS/DQS mix by a vertex group via two Armature modifiers + Multi Modifier (P10) | strong |
| Optimized centres of rotation | removes both LBS collapse and DQS bulge, real time, same weights (P3) | not built in; community C++ code | single |
| Delta mush | smooths skinning distortion while keeping rest detail (P4) | Smooth Corrective modifier; needs Bind if Subdivision is before it (P10) | strong |
| Pose-space correctives | sculpted or learned shapes interpolated by pose (P1); learned pose blend shapes from 1786 scans in SMPL (P5) | shape keys + drivers; Pose Shape Keys add-on | strong |
| Helper / half-rotation bones | extra joints placed to fix LBS at shoulders and elbows (P6); MPFB Rigify rig: DEF-shoulder-helper copies 50% of upper-arm rotation and adds up to 6 / -24 / -30 deg (x/y/z) between 40 and 100 deg of arm rotation (checked) | bones + constraints | single + checked |
| Twist segments | Rigify DEF-upper_arm + .001 (checked); MPFB helper adds 10 deg per 90 deg twist (checked) | B-Bones / extra deform bones | checked |
| Automatic weights | Blender's bone heat = heat diffusion (P7); needs a clean connected mesh; failed on build 08 (rigtest README) | built in | strong |
| Weight transfer | copy weights only where confident, inpaint the rest (P8) | Data Transfer modifier (built in); Robust Weight Transfer add-on (not in the folder) | single |
| Soft-tissue dynamics | breast and belly motion depend on pose and motion; learned from 4-D scans (P9) | jiggle / spring-bone add-ons (section 6) | single |

## 6. Tools in `Blender woman generation stuff/` (read, not installed) and the rig test (checked)
- Pose Shape Keys 1.1.1 (Blender Studio, Blender >= 5.0; install needed): stores the wanted posed shape in a storage
  object and writes the shape key as (target - current evaluated) mapped back through Blender's crazyspace, so the
  corrective survives later weight or constraint changes and works with any deform stack (LBS or DQS). Auto-driver:
  product of ramps max(0, v)/v_pose per channel, local swing-twist rotation. Can clamp overlapping masks to 1.
- CloudRig 2.2.27 (Blender Studio, >= 5.0; install): shoulder is a single FK bone (no automatic rhythm); "Shape Key
  Helpers" (SKH bones that read the rotation between two deform bones to drive correctives); B-Bone deform segments;
  Action-constraint system for corrective bone motion.
- MPFB 2.0.17 (MakeHuman; install): ships rigs and weights as JSON. Default rig: clavicle -> shoulder01 (scapula) ->
  upperarm01/02 and breast bones. Rigify rig: shoulder is basic.super_copy on spine.004 with no constraints (does not
  follow the arm); breast bones ride an armature constraint 65% spine.003 / 35% spine.004. Its weights put shoulder
  bones on the breast: of the 402 breast.L vertices, 287 also carry shoulder.L (max 0.62), 106 the shoulder helper
  (max 0.81), 165 upper_arm (max 0.30).
- Jiggle Physics 4.5.2, Wiggle 2 2.2.9 (install): spring bones for motion only (Jiggle breast preset: gravity 0,
  elasticity root 0.9 / angle 0.8 / length 0.9, soften 0.5, drag 0, friction 0.1). Not a fix for static poses.
- stretching_gn_overlay.blend (no install; append): node group "edge_stretching" compares each edge with an unmodified
  copy (Source Object, same subdivision) as a colour ramp (grey none, blue -> red -> purple stretch; Range input).
- Human Base Meshes 1.4.1: meshes only (GEO-body_female_realistic 10,582 v: 10,570 quads, 20 triangles, 244 5-poles,
  232 3-poles), no armature, weights or shape keys. Its Rigify result came from topology plus bone-heat weights.
- Rig test (woman2_rigtest.blend): v12 has 12 deform bones (hips, spine, chest, neck, clavicle, scapula, upper_arm,
  forearm), LBS (Preserve Volume off), correctives abd15/45/60/75/90 + flex60 per side whose drivers saturate at about
  64 deg of upper-arm rotation (about 90 deg abduction): nothing is sculpted for 90-180 deg. Its breast vertices
  (zone_breast > 0.5, left) are weighted chest 0.64, spine 0.26, hips 0.07, with zero clavicle, scapula or upper-arm
  weight. The base body under Rigify: about a quarter of its breast vertices carry DEF-shoulder (max 0.63) and
  DEF-upper_arm (max 0.65). Rest arm angle: base body 19.9 deg from vertical, v12 6.5 deg.

## 7. Grok's points (GROK_RESEARCH.md) against sources
| # | Grok's point | Verdict | Basis |
|---|---|---|---|
| G1 | Armature + topology + weights + correctives is the practical standard; full muscle system unnecessary | held | P1, P5, Blender Studio tools; base body deformed well without correctives (checked) |
| G2 | Armpit = soft pocket, front wall pectoralis major, back wall latissimus/teres major, keeps thickness | held | S14, arm_axilla_lateral_torso.md |
| G3 | Raised: deltoid contracts, more prominent and rounded | partly held | shortens and stiffens (S8 calc, S17); contour change unmeasured |
| G4 | Raised: axillary pocket opens | held | S14 (fascia traction); depth unmeasured |
| G5 | Pectoralis and latissimus stretch and shift | held | about +5-6 cm (calc, S8) |
| G6 | Skin slides over the underlying mass | held | 3-7 cm over scapula (S6); up to 8 cm on chest (S9) |
| G7 | Breast shifts upward and/or laterally | unsupported | standing: notch-nipple longer, nipples no wider (S10); supine: nipples move medially (S11) |
| G8 | Breast shift comes mostly from pectoralis movement + skin sliding | unsupported | plausible from S15, S18; no measurement |
| G9 | Topology: deltoid border loop, rings round the arm, fold loops, radial breast loops, poles out of the joint, quads | unsupported | practitioner advice only (P12); base body is 99.8% quads (checked); its pole placement not checked |
| G10 | Model in a neutral A-pose, test both extremes | held (practice) | LBS loss grows toward 180 deg from rest (P10); base body rests at 20 deg (checked); P12 |
| G11 | Williamson CG Cookie shoulder topology videos | not held | only a "Topology Overview: Male and Female Torso" video found (P12) |
| G12 | Upper-arm bone root should be medial or it pinches | unsupported | anatomically the arm pivots at the humeral head and the chain starts medially at SC (S1) |
| G13 | Less upper-arm weight deep in the armpit; deltoid more from shoulder side | unsupported | practice; MPFB helper (50% of arm rotation) is the same idea (checked) |
| G14 | Breast mainly chest/spine with some shoulder influence | held | MPFB weights and base body weights (checked); v12 has none (checked) |
| G15 | Use dual quaternion for volume | partly held | fixes LBS shrink (P2) but bulges at the chest (P3), jumps at 180 deg (P10): test both |
| G16 | Correctives driven by arm rotation, zero at rest, ramping near the extreme | held | P1, P5; Pose Shape Keys drivers (checked) |
| G17 | Breast helper bones constrained to follow the shoulder | unsupported | no source; MPFB breast bones follow the spine only (checked) |
| G18 | Soft body / cloth for contact and jiggle | unsupported for poses | dynamics only (P9; jiggle add-ons) |
| G19 | Almost nobody gets it right without correctives | not held as stated | base body held arm, armpit and breast form with bone-heat weights and no shape keys (person's review; checked) |
| -- | Missed: neck/trapezius and clavicle motion, shoulder rhythm, measured skin slide, rest-pose angle, Smooth Corrective, correctives past 90 deg, weight transfer | new | S1-S6, P3-P8, section 6 |

## 8. Not found
Standing nipple displacement in mm with arms overhead; armpit hollow depth or fold geometry in any pose; deltoid
contour or thickness change with elevation; women-only bone-pin clavicle data; in vivo pectoralis/latissimus fibre
length overhead; shoulder skin strain values (S19 not reachable); any measured limit for skin compression in a fold.

## References
S1 Ludewig PM, Phadke V, Braman JP, Hassett DR, Cieminski CJ, LaPrade RF. J Bone Joint Surg Am 2009;91:378-389. doi 10.2106/JBJS.G.01483, PMC2657311 (read in PMC).
S2 McClure PW, Michener LA, Sennett BJ, Karduna AR. J Shoulder Elbow Surg 2001;10:269-277. doi 10.1067/mse.2001.112954 (PDF saved, 01).
S3 Inman VT, Saunders JB, Abbott LC. J Bone Joint Surg 1944;26:1-30 (reprint Clin Orthop 1996;330:3-12, PMID 8804269); values as tabulated in S2.
S4 Nagamatsu T, Kai Y, Gotoh M, Madokoro K, Shiba N. SICOT J 2015;1:9. doi 10.1051/sicotj/2015004 (PDF saved, 02).
S5 Nakayama et al. J Phys Fitness Sports Med 2018 (DOAJ 22acf9eb...; snippet); Liege abstract hdl.handle.net/2268/172993 (snippet).
S6 Yoshida Y, Matsumura N, Yamada Y, et al. Sensors 2022;22:6502. doi 10.3390/s22176502 (PDF saved, 03).
S8 Ackland DC, Pak P, Richardson M, Pandy MG. J Anat 2008;213:383-390. doi 10.1111/j.1469-7580.2008.00965.x (PMC2644775).
S9 Liu X, Sun Y, Kuang C, Yick KL, Ji X. J Eng Fibers Fabr 2026. doi 10.1177/15589250261491307 (abstract only).
S10 Benito-Ruiz J. Aesthet Surg J 2023;43:NP751-NP762. doi 10.1093/asj/sjad099 (tables read on the publisher page).
S11 Denniston KA, Verma V, Bhirud AR, Bennion NR, Lin C. Front Oncol 2016;6:176. doi 10.3389/fonc.2016.00176 (PDF saved, 04).
S12 J Textiles and Polymers 2021;9(1):13-26 (profdoc.um.ac.ir 1105334; snippet only). S13 Hassmann M, Dastl J, Krach W. 3DBODY.TECH 2018, doi 10.15221/18.207 (saved as breast_cup_size_02).
S14 Gray H. Anatomy of the Human Body (1918 text via hithera.com): pectoralis major, axillary fascia. S15 Skandhan A, Hacking C. Breast. Radiopaedia (revised 2026-07-13).
S16 Zhang J, Lau NML, Sun Y, Yip J, Yick KL, Yu W, Chen J. Text Res J 2022;92:3511-3521. doi 10.1177/00405175221075049 (abstract). S17 Middle deltoid shear-wave elastography, 70 adults, Sci Rep 2021 (PMC8203697; abstract).
S18 Nursing Physical Assessment 15.9, cod.pressbooks.pub (weak). S19 Skin strain fields at the shoulder joint, 3D-DIC, IEEE Aerospace Conf 2016 (ieee 7500744; authors not confirmed).
P1 Lewis JP, Cordner M, Fong N. Pose space deformation. SIGGRAPH 2000:165-172. doi 10.1145/344779.344862.
P2 Kavan L, Collins S, Zara J, O'Sullivan C. ACM TOG 2008;27(4):105. doi 10.1145/1409625.1409627 (PDF saved, 05).
P3 Le BH, Hodgins JK. Real-time skeletal skinning with optimized centers of rotation. ACM TOG 2016;35(4):37. doi 10.1145/2897824.2925959 (abstract and figure caption).
P4 Mancewicz J, Derksen ML, Rijpkema H, Wilson CA. Delta Mush. SIGGRAPH/DigiPro 2014. doi 10.1145/2633374.2633376.
P5 Loper M, Mahmood N, Romero J, Pons-Moll G, Black MJ. SMPL. ACM TOG 2015;34(6):248. doi 10.1145/2816795.2818013 (not re-read).
P6 Mohr A, Gleicher M. ACM TOG 2003;22(3):562-568. doi 10.1145/882262.882308 (cited in P2). P7 Baran I, Popovic J. ACM TOG 2007;26(3):72. doi 10.1145/1276377.1276467 (not re-read).
P8 Abdrashitov R, Raichstat K, Monsen J, Hill D. SIGGRAPH Asia 2023 Tech Comm. doi 10.1145/3610543.3626180 (PDF saved, 06). P9 Pons-Moll G, et al. Dyna. ACM TOG 2015;34(4):120. doi 10.1145/2766993 (not re-read).
P10 Blender 5.2 manual: Armature modifier; Smooth Corrective modifier (read 2026-10-20).
P12 Practitioner sources: Blender Artists threads 520763 and 475445 (shoulder loops; model arms about 20 deg down); CG Cookie torso topology video (named in thread); CG Cookie and Polycount A-pose vs T-pose threads.
