# Scapula and shoulder girdle in every movement: cited kinematics, back-surface signs, modelling, test poses

Compiled 2026-10-20 (build 14) from open full texts and abstracts; seven PDFs saved as `reference content/research
papers/scapula_girdle_motion_*`. Overlap with build 11 is cited, not repeated: "B11:S1" = key S1 in
`shoulder_axilla_motion.md` (arm-elevation rhythm, sex, skin slide, skinning methods, Blender add-ons there); rest
posture and layers in `arm_axilla_lateral_torso.md`. strong = several studies agree; single = one study; weak =
abstract, snippet, secondary, cadaver or one subject; (calc) = my arithmetic; (fig) = read off a figure, +/-1-2 deg;
(checked) = read from our files this session. Angles are ISB Euler angles (B11:S1 conventions): scapula upward
rotation UR, internal rotation IR (a few papers call it "protraction"), posterior tilt PT (negative = anterior);
clavicle retraction RET, elevation ELE, posterior axial rotation PAR. Values are changes from the start pose unless
marked "abs". Women and men pooled unless stated.

## 0. How the girdle is built and how it moves (my words)
1. The girdle is a closed loop: thorax - SC joint - clavicle - AC joint - scapula gliding on the ribs - thorax.
   The clavicle turns 3 ways about the SC joint (RET, ELE, PAR); the scapula turns 3 ways (UR, IR, PT) and glides over
   the curved ribs, so each girdle pose is 5-6 numbers, not one (R1, R5).
2. Arm elevation in every plane is a blend of all of these, not UR alone: UR about 40-50, PT about 20-30, small net
   IR change, clavicle RET about 16, ELE 6-11 (bone pins) to 25-30 (radiographs), PAR about 31 (B11:S1-S3). The plane
   changes the mix: flexion keeps the scapula about 7 deg more internally rotated and the clavicle up to 15 deg less
   retracted than coronal abduction (R0).
3. The girdle also moves with the arm still: shrug (clavicle ELE about 25 with scapular UR about 18-26), retraction and
   protraction (clavicle RET/protraction about 10, scapular IR -6/+7 passive; more when active with the arm), rolls
   that sweep the widest retraction-protraction and tilt ranges measured, and reaches across the body that drive
   scapular IR ("protraction") to its maximum (R1-R4). A rig coupled only to the arm cannot do these (R2).
4. Rest is variable: upright CT gives UR 9.2, IR 29, anterior tilt 7 (women, arm_axilla_lateral_torso.md); bone pins
   give UR 5, IR 41, anterior tilt 13.5 (B11:S1); differences of 5-12 deg between methods are normal.
5. On the back the scapula shows through thin cover (skin about 2.5 mm suprascapular, soft_tissue_mechanics.md; fat
   7.6 mm subscapular, arm_axilla_lateral_torso.md), then trapezius, rhomboids medially, infraspinatus/teres on the
   blade, latissimus over the inferior angle, posterior deltoid laterally. Bony signs: spine of scapula (oblique ridge
   from about T3 to the acromion), medial border (vertical at rest), inferior angle (about T8-T9 in women), acromion.
   Contracted muscles thicken and bulge; stretched ones flatten.
6. Skin lags the bone by 3-7 cm over the scapula at full elevation (B11:S6): bony bumps glide under the skin, so skin
   weighted 1:1 to a scapula bone moves too much.
7. Rhythm regressions predict scapula and clavicle from the humerus with RMSE above 5 deg for every angle (R15): allow
   about +/-5 deg, and add girdle channels independent of the arm (R2).

## 0b. Measurable descriptors and cited targets
| # | Descriptor | Target | Source | Conf |
|---|---|---|---|---|
| D1 | Scapula UR/IR/PT and clavicle RET/ELE/PAR per test pose | section 6 rows | sections 1-3 | per row |
| D2 | Spine-root (TS) to TS distance at rest | 17.19 cm (8.6 per side); medial borders parallel to the spine; surface within 0.56 cm / 1.7 deg of radiographs | R8 (15 F, 19-21 y) | single (abstract) |
| D3 | Inferior angle level, standing | T8 most often overall, T8/9 interspace most often in women (100 films); mean about T9 body, range T7-T10 (50 films) | R9 | single each |
| D4 | Scapula length (superior to inferior angle); breadth | women 14.5 +/- 0.66 cm (R), 14.4 +/- 0.67 (L); breadth 9.66 +/- 0.45 cm; men 16.4 / 10.8 | R7 (93 F, 20-80 y, Indian, MDCT) | single |
| D5 | Inferior angle sweep, rest to overhead (UR +40) | 7-10 cm lateral and round the ribs toward the posterior axillary line; TS 0 to 6 cm down (pivot TS vs AC) | calc from D4 + B11:S1 | weak (calc) |
| D6 | TS shift, pinch back / round forward | about -2 cm (to midline) / +1.5 cm per side | calc: clavicle 13.7 cm (checked, rig), RET +10, IR -15 / protraction 10, IR +10 | weak (calc) |
| D7 | Acromion rise in a full shrug | about 5.6 cm (clavicle ELE 25 deg) | calc from R1 | weak (calc) |
| D8 | Skin-to-bone slip over AA / TS / AI at 146 deg | 30 / 53 / 70 mm, mostly skin above bone | B11:S6 | single |
| D9 | Forward shoulder angle (side view, C7 to shoulder line vs horizontal) | 49.2 +/- 5.2 deg in rounded shoulders (inclusion <= 50); 56-61 after correction | R10b (40 adults) | single, weak |
| D10 | Rig tolerance for scapula/clavicle angles | about 5 deg (regression RMSE > 5 deg) | R15 | single |

## 0c. How to measure on our rig and mesh (my method)
(a) Rig: bone-parented empties at AA, TS, AI (scapula, sizes D2-D4) and SC, AC (clavicle); thorax frame from C7, T8,
IJ, PX; Y-X-Z Euler angles per pose vs section 6. (b) Mesh: bony signs per pose as mean-curvature ridges and bumps near
the rest landmarks, positions in the thorax frame (D5, D2/D6, spine-of-scapula angle). (c) Skin slip: skin vertices
over AA/TS/AI at rest vs the posed bone landmarks (D8). (d) Interscapular groove: sagitta below a chord between the
medial-border ridges at TS height. (e) Neck-shoulder line: C7-acromion angle to horizontal, back and side (D7, D9).

## 1. Arm movement in each plane (adds to B11:S1-S3; rhythm ratios there)
| Plane / task | Values | n, method | Citation | Conf |
|---|---|---|---|---|
| Flexion vs scapular plane vs abduction (all to >= 120 HT) | ST IR: flexion +7 vs scapular plane, abduction -7.5; ST UR: abduction +2 at 60, +3 at 90-120; ST PT: no plane difference; SC RET: abduction > scapular plane > flexion, up to 15 deg mid-range; SC ELE: abduction +4 vs flexion, +2.5 vs scapular plane; SC PAR: flexion 2.5 less at 30-60; AC IR: flexion up to +4 | 12 (5 F), pins | R0 (= B11:S1) | single |
| Flexion vs scapular plane | patterns "do not differ substantially"; GH/ST 2.0 flexion, 1.7 scapular plane (2.3 / 1.9 from a 0 deg start) | 8 (3 F), pins | B11:S2 | single |
| Frontal vs sagittal vs scapular plane, 30-120 HT | widest UR range in the elevations: 44 deg (frontal); largest UR 41 +/- 5 (abs; text says sagittal, table says frontal and scapular plane) | 8 (2 F), 25-40 y, EM tracker | R4 | single |
| External rotation at 90 abduction (wind-up) | little scapular motion until end-range ER, then UR, PT, external rotation and clavicle RET | 8, pins | B11:S2 | single |
| Same, prone, with retraction effort: 90 abd ER minus neutral rotation | UR +9.0, PT +10.0, IR -4.1, RET +5.1, ELE +7.2 | 23 (11 F of 25), 23 y, EM, prone | R3 (ex 2 - ex 1) | single |
| 120 abduction, prone, retraction effort (abs) | UR 42.6 +/- 14.7, IR 18.0, PT 5.2, RET 34.2, ELE 4.2 (neutral stance abs: UR 0.9, IR 27.3, PT -16.1, RET 16.2, ELE 8.2) | same | R3 | single |
| Extension (arm back), prone, lifted 66 deg, retraction effort (abs) | UR 1.5, IR 17.6, PT -15.8, RET 17.1, ELE -8.2: vs neutral stance UR and tilt unchanged, IR -10, clavicle depressed 16 deg | same | R3 (ex 6) | single, prone |
| Extension, standing | textbook: downward rotation and anterior tilt; no standing 3-D value found | - | - | none |
| Horizontal sweep at 60/90/120 elevation, cross-body to coronal | scapular "protraction" (IR) reaches its maximum, 56 +/- 7 (abs), at the cross-body end; widest tilt range after rolls | 8 (2 F), EM | R4 | single |
| Mid-humeral rotation at 90 (IR 0-90) | scapula tilts anteriorly mostly beyond 60 deg IR (MRI, 10 shoulders) | 10 | Koishi 2011 via search (R4b) | weak (snippet) |

## 2. Girdle movements with the arm passive or at the side
| Movement | Values | n, method | Citation | Conf |
|---|---|---|---|---|
| Shrug, active, in vivo | ST UR 13 -> 31 (+18), ST elevation coordinate -4 -> +7 (+11), winging (IR) 5 -> -1 (-6), ST abduction -7 -> -10 (fig); levator scapulae and upper trapezius active, serratus low | 1 F, 26 y, 162 cm; EM sensors (acromion), 6 trials | R2 | weak (one subject, fig) |
| Shrug, passive (superior force, elbow 90) | SC ELE +25 +/- 5, RET +17 +/- 5, PAR +5 +/- 6; ST lateral (upward) rotation +26 +/- 4, protraction -9 +/- 2, anterior tilt about +3; AC PT +23 +/- 6, AC upward +13 +/- 4 | 14 shoulders, 8 cadavers (3 F), 85 y; pins + optical | R1 | single, cadaver |
| Depression | NO 3-D VALUE FOUND (textbook SC depression about 5-15 deg, unchecked) | - | - | none |
| Retraction (pinch back), passive | SC RET +9 +/- 2, PAR +3 +/- 2; ST protraction -6 +/- 5, lateral rotation +4 +/- 3; tilt change small; AC negligible | same cadavers | R1 | single, cadaver |
| Retraction, active, prone, arm at 90-120 abd or 45 abd + elbow 90 | clavicle RET 24-34 (abs; +8 to +18 vs standing neutral 16.2); ST IR 2.4-18 (abs; -9 to -25 vs 27.3) | 23 (11 F of 25), EM | R3 | single, prone, arm confounded |
| Protraction (round forward), passive | SC protraction 10 +/- 2, anterior rotation 3 +/- 2; ST protraction +7 +/- 2, medial rotation 1 +/- 1; AC PT +4 +/- 3, AC protraction -3 | same cadavers | R1 | single, cadaver |
| Forward-head rounded-shoulder posture | more ST IR in loaded flexion and overhead reach; more UR and anterior tilt in flexion; less serratus activity | 80 pain-free, EM + EMG | R11 | single (abstract) |
| Slouched vs erect sitting | less posterior tilt, more elevation; abduction range down about 24 deg (attribution secondary) | n not read | R10 | weak (secondary) |
| Shoulder rolls, forward and back, arms at sides, bilateral | rolls give the widest retraction-protraction and tilt ranges of all tasks (whole-study ranges 51 IR, 46 UR, 27 tilt); the most retracted IR, 5 +/- 10 (abs), and the only downward rotation (5 +/- 5) occur in rolls | 8 (2 F), EM | R4 | single |

## 3. Reaches and compound tasks (static holds, abs values, R4: 8 healthy, 2 F, EM tracker, ISB)
| Task | Scapular "protraction" (IR) | UR | Tilt (+ posterior) | HT elevation; plane | Conf |
|---|---|---|---|---|---|
| Hand to opposite shoulder | 48 +/- 8 (study max) | 17 +/- 9 | -11 +/- 5 | 54 +/- 9; 111 +/- 8 (cross-body) | single |
| Hand to opposite ear | 46 +/- 8 | 16 +/- 5 | -11 +/- 4 | 62; 102 | single |
| Hand to back of neck | 29 +/- 8 (least) | 36 +/- 7 (most) | 0 +/- 6 | 124 +/- 13; 47 | single |
| Hand to top of head / back of head | 38 / 33 | 28 / 30 | -4 / -1 | 105 / 110; 59 / 47 | single |
| Chin / forehead | 38 / 41 | 3 / 12 | -8 / -7 | 38 / 64; 77 / 80 | single |
| Axe swing (wind-up overhead, both hands; chop down to the front) | NO MEASURED SCAPULA DATA FOUND (chopping studies give joint sequencing only, R12). Estimate from rows above: top = flexion 150-170 + hands converging (UR 45-50, PT 20-30, IR between back-of-neck 29 and cross-body 48, clavicle RET and PAR near their peaks); strike = flexion 90 -> 20 with hands converging (IR toward 46-56, anterior tilt, UR back toward rest); follow-through = protraction + depression | - | - | - | estimated |

## 4. How the girdle shows on the back (surface)
| Item | Value / sign | Source | Conf |
|---|---|---|---|
| Rest landmarks | see D2-D4: TS about 8.6 cm off midline, medial borders vertical, inferior angle T8-T9 | R7-R9 | single each |
| Cover over the blade | skin 2.54 mm suprascapular (adults); fat 7.6 +/- 1.9 mm subscapular (women) | soft_tissue_mechanics.md; arm_axilla_lateral_torso.md | single each |
| Skin slip over the scapula overhead | B11:S6 (3-7 cm; markers under-read UR by 13.5 and PT by 14.6 deg) | B11:S6 | single |
| Which muscles contract (bulge) in retraction | middle trapezius 53-77 %MVIC, lower 37-72, upper 15-72, serratus 10-21 across 6 retraction exercises | R3 | single |
| Which muscles drive shrug and overhead | shrug: levator scapulae + upper trapezius elevate, trapezius and serratus upward-rotate; overhead: trapezius + serratus do more work than the glenohumeral muscles | R2 | weak (model + 1 subject) |
| Overhead (any plane) | inferior angle sweeps laterally 7-10 cm round the ribs (D5); medial border turns oblique by the UR change; spine of scapula tilts lateral-end-up; upper trapezius shortens between neck and acromion (B11 sec 0 item 2); latissimus/teres major stretch into the posterior fold | calc + B11 | estimated |
| Shrug | acromion up about 5.6 cm (D7), upper trapezius bunches into a thick ridge, neck looks shorter, transverse folds at the base of the neck; UR +18-26 swings the inferior angle about 4-5 cm laterally (calc, pivot TS or AC) | R1, R2 + calc | estimated |
| Pinch back | medial borders close toward the spine about 2 cm each (D6), stay parallel; middle trapezius/rhomboids bulge between them with a vertical midline groove and vertical skin folds | R1, R3 + calc | estimated |
| Round forward | blades slide apart (TS about +1.5 cm each) and wrap round the ribs; IR turns the medial border backward so it stands off the ribs (pseudo-winging); interscapular region flat and wide, spinous processes show | R1, R11 + calc | estimated |
| Arm back (extension) | clavicle depressed (shoulder line lower), less IR; textbook anterior tilt lifts the inferior angle off the ribs | R3 | weak |
| Reach across | that blade far protracted (IR 48) and anteriorly tilted: medial border and inferior angle lift, the interscapular gap widens on that side | R4 | estimated sign, measured angles |
| Measured back-surface shapes per pose (3-D) | NO VALUES; DFAUST has 4-D scans of 10 people (5 F) at 60 fps, minimal clothing, painted skin, 82% of points within 1-2 mm, texture-registered (no tangential sliding): a ground-truth source to obtain | R19 | single (dataset) |

## 5. How it is modelled and rigged
| Approach | What it does / evidence | Blender (needs) | Conf |
|---|---|---|---|
| Scapulothoracic ellipsoid joint (OpenSim; R5) | scapula frame origin (centroid of AA, TS, AI) slides on a thorax ellipsoid: abduction and elevation (longitude/latitude), UR about the surface normal, winging about scapula Y; 4 DOF, marker RMS 1.9 mm vs bone pins (1 subject); radii fitted per subject and task | Shrinkwrap constraint (Target Normal Project, Above Surface, Align To Normal) on an ellipsoid or the v12 ribcage, plus Damped Track to the AC; no install (R20) | single |
| Thoracoscapular muscle model (R2) | same joint + trapezius, rhomboids, serratus, levator; tracks shrug and elevation within 1 cm marker RMSE; the authors note a rhythm coupled to the humerus cannot shrug; model and data on SimTK | reading its .osim XML needs no install; running it needs OpenSim (install, consent) | single |
| SKEL (SMPL re-rigged with a biomechanical skeleton; R6) | scapula 3 DOF (abduction, elevation, UR) on the Seth ellipsoid; fitted to DFAUST it shows scapula sliding; joints with no SMPL equivalent (scapula) use plain LBS without pose correctives; vertex error vs SMPL < 3 cm | research licence + Python package (install, consent) | single |
| Delft shoulder model (R18); graphics shoulder with scapulo-thoracic constraint (R17) | scapula points constrained to an ellipsoid (5 or 4 DOF); constrained optimisation can give nonphysical poses high up (R5); Maurel-Thalmann used the same constraint plus joint sinus cones for IK | method only | weak (secondary) |
| Regression shoulder rhythms (R13-R15) | scapula and clavicle from HT elevation, plane and axial rotation (de Groot-Brand 23 postures; Grewal-Dickerson incl. overhead; Xu 2014 incl. axial rotation); six rhythms tested on 14 people x 118 postures: none consistently best, RMSE > 5 deg for every angle, UR best predicted | Blender drivers (simple expressions, no install); coefficients are in paywalled papers | single + abstracts |
| Data-driven shoulder IK for animation (R16) | interpolates measured shoulder-complex poses from upper-arm orientation | lookup table of sections 1-3 interpolated in drivers | weak (abstract) |
| Pose-driven correctives (RBF; R21) | MetaHuman body: RBF solvers let one joint's rotation drive corrective joints that stop volume loss at elbows and shoulders | Pose Shape Keys / CloudRig (B11 sec 6, install) or shape keys + drivers | single (vendor docs) |
| Skinning, delta mush, correctives, weight transfer | B11:P1-P10 and B11 sec 5-6 (MPFB default rig has a scapula bone "shoulder01") | B11 | - |
| Muscle / tissue simulation (film practice) | not needed first (B11:G1); no Blender built-in | add-ons (install) | weak |

Our rig (checked, rig.json v12): scapula.L/R and clavicle.L/R are driven only by upper_arm rotation_euler[2] (the
abduction channel): st = max(0, (g - 24.07)/2), one rotation about the scapula bone's head (6.5 cm off midline, at
acromion height; bone 11.4 cm long, tail 7.2 cm off midline); clavicle ELE = asin(0.66 sin st). So flexion, horizontal
movement, axial rotation and every girdle-only movement leave the scapula still; PT, IR, clavicle RET and PAR are
absent; full abduction (st 50) gives clavicle ELE about 30 deg (calc), the radiograph value, against +6 to +11 with
PAR 31 in bone pins (B11:D4). Worth testing (my ranking): (1) 3-axis scapula + 3-axis clavicle drivers fed by HT
elevation, plane and axial rotation, targets in section 6; (2) independent girdle channels (elevate, protract,
tilt) as custom properties added into the same drivers; (3) a TS/AI helper kept on the ribcage by Shrinkwrap so the
blade wraps forward in protraction and overhead; (4) partial skin weights on the scapula or a slide shape key so the
skin lags the bone by D8; (5) correctives per test pose; (6) ground truth from DFAUST/SKEL (licences: the person).

## 6. Test poses (targets for the rig and the back view; abs where marked, else change from rest)
| # | Pose | Measured targets | Surface signs to see | Source | Conf |
|---|---|---|---|---|---|
| T0 | Stand, arms hanging | abs UR 5-9, IR 29-41, anterior tilt 7-13.5; clavicle RET 19, ELE 6 | borders vertical, TS 8.6 cm off midline, inferior angle T8-9, flat trapezius | B11:S1, arm_axilla, R8, R9 | single each |
| T1 | Scapular-plane raise 90 / max | rhythm 2.2:1; at max UR +50, PT +30, ER 24 | D5 sweep; spine of scapula tilts; neck line steepens | B11:S1-S2 | strong |
| T2 | T-pose (coronal 90) and coronal max | as T1 but IR -7.5, clavicle RET up to +15 more than flexion, ELE +4 more | widest UR range (44) | R0, R4 | single |
| T3 | Flexion 90 / max (forward swing high) | IR +7 vs T1, less RET; ratio 2.4:1 | blades less retracted than T2 | R0, B11:S2 | single |
| T4 | Arm back (backswing) | prone ref: IR -10, clavicle ELE -16, UR/tilt ~0 | lower shoulder line; inferior angle may lift | R3 | single, prone |
| T5 | Horizontal sweep at 90, across to out | IR 56 (abs) at cross-body end | blade wraps round the side, then returns | R4 | single |
| T6 | Hand to opposite shoulder | abs IR 48, UR 17, tilt -11; HT 54, plane 111 | that blade lifts at border and angle; gap widens | R4 | single |
| T7 | Hand to back of neck | abs IR 29, UR 36, tilt 0; HT 124 | blade near spine at top, angle far lateral | R4 | single |
| T8 | Shrug | UR +18 (vivo) to +26 (cad), clavicle ELE +25, RET +17 (cad) | acromion +5.6 cm, trapezius ridge, neck folds | R1, R2 | weak |
| T9 | Pinch back | clavicle RET +9 (passive) to +18 (active), IR -6 to -25 | borders -2 cm each, groove, folds | R1, R3 | single |
| T10 | Round forward | clavicle protraction 10, IR +7 (passive); FSA about 49 deg | borders +1.5 cm each, stand off ribs | R1, R10b | weak |
| T11 | Shoulder roll back / forward | IR range up to about 51 from 5 (abs), tilt range up to 27, slight downward rotation | the T8-T10 signs in order | R4 | single |
| T12 | ER at 90 abduction (wind-up) | UR +9, PT +10, IR -4, RET +5 vs neutral rotation | blade tips back, borders close | R3, B11:S2 | single |
| T13 | Axe: top / strike / follow-through | estimated in section 3 | T1 + T6 blend, then T10 | sections 1-3 | estimated |

## 7. Not found
In vivo 3-D values for depression, standing retraction or protraction with the arm at the side (cadaver and prone
only), a full shrug in more than one living subject, standing arm extension, any axe, wood-chopping or golf scapula
data, women-only girdle data, measured back-surface shape or skin slide per girdle pose, scapular muscle thickness
change with contraction (trapezius reliability studies give no means), ellipsoid radii for a woman's thorax (fitted
per subject in R5), and the regression coefficients (paywalled).

## References
R0 Ludewig PM, et al. J Bone Joint Surg Am 2009;91:378-389. doi 10.2106/JBJS.G.01483, PMC2657311 (= B11:S1; plane differences read in PMC).
R1 Peeters I, Braeckevelt T, Palmans T, Van Tongel A, De Wilde L. JSES Int 2023;7(1):147-152. doi 10.1016/j.jseint.2022.09.014, PMC9937811 (read in PMC).
R2 Seth A, Dong M, Matias R, Delp S. Front Neurorobot 2019;13:90. doi 10.3389/fnbot.2019.00090 (PDF saved, 04; Fig 2 read).
R3 Oyama S, Myers JB, Wassinger CA, Lephart SM. J Orthop Sports Phys Ther 2010;40(3):169-179. doi 10.2519/jospt.2010.3018 (PDF saved, 01; Table 1 read).
R4 Sheikhzadeh A, Yoon J, Pinto VJ, Kwon YW. J Shoulder Elbow Surg 2008;17(6):936-942. doi 10.1016/j.jse.2008.04.008 (PDF saved, 02; Tables I-II read). R4b Koishi H, et al. 2011 (MRI internal rotation; snippet).
R5 Seth A, Matias R, Veloso AP, Delp SL. PLoS One 2016;11(1):e0141028. doi 10.1371/journal.pone.0141028 (PDF saved, 03).
R6 Keller M, Werling K, Shin S, Delp S, Pujades S, Liu CK, Black MJ. From skin to skeleton. ACM TOG 2023;42(6). doi 10.1145/3618381 (PDF saved, 05).
R7 Debnath M, Kotian RP, Sharma D. J Clin Diagn Res 2018. doi 10.7860/JCDR/2018/29560.11241 (PDF saved, 06).
R8 Sobush DC, et al. J Orthop Sports Phys Ther 1996;23(1):39-50. doi 10.2519/jospt.1996.23.1.39 (abstract). R9 J Can Chiropr Assoc 2008;52(1):24-29, PMC2258239 (50 radiographs; authors not re-read, likely Haneline MT et al.); Ir Med J 2025 review of 100 films (imj.ie PDF; snippet).
R10 Kebaetse M, McClure P, Pratt NA. Arch Phys Med Rehabil 1999;80:945-950. doi 10.1016/s0003-9993(99)90088-6 (secondary summaries only). R10b Kwon JW, Son SM, Lee NK. J Phys Ther Sci 2015;27(6):1739-1742. doi 10.1589/jpts.27.1739 (read in PMC4499973).
R11 Thigpen CA, Padua DA, Michener LA, et al. J Electromyogr Kinesiol 2010;20(4):701-709 (abstract read; pages not re-read).
R12 Coe D, Barham L, Gardiner J, Crompton R. Biomechanical test of hafted-tool efficiency, chopping and scraping (Liverpool repository 3150944; abstract via search).
R13 de Groot JH, Brand R. Clin Biomech 2001;16:735-743 (secondary). R14 Grewal TJ, Dickerson CR. J Biomech 2013;46:608-611; Xu X, Lin JH, McGorry RW. J Biomech 2014;47:1206-1210 (both cited via R15 and a 2021 IST thesis; not read).
R15 Xu X, Dickerson CR, Lin JH, McGorry RW. J Electromyogr Kinesiol 2016. doi 10.1016/j.jelekin.2015.07.005 (abstract, UWSpace hdl 10012/17860). R16 Kim YB, Park BH, Jung KM, Han JH. Data-driven shoulder inverse kinematics. arXiv 1612.07353 (abstract).
R17 Maurel W, Thalmann D. Computers & Graphics 2000;24(2):203-218. doi 10.1016/S0097-8493(99)00155-7 (abstract). R18 van der Helm FCT. J Biomech 1994;27:551-569 (secondary, via R5).
R19 Bogo F, Romero J, Pons-Moll G, Black MJ. Dynamic FAUST. CVPR 2017 (PDF saved, 07); data at dfaust.is.tue.mpg.de (research licence, registration).
R20 Blender manual, Shrinkwrap constraint (read 2026-10-20). R21 Epic Games, MetaHuman component documentation (Enable Body Correctives, RBF solvers; read via search 2026-10-20).
