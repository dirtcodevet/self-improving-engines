# Simplified functional muscle system: cited numbers for a load-driven muscle dial

Compiled 2026-10-19 from abstracts, open full texts (Europe PMC), OpenSim source code and project pages. Read-only; nothing kept. The web-search budget ran out mid-task, so later items are exact-title or exact-ID lookups of papers I already knew; holes are listed in section 10.
Confidence: strong = 2+ studies agree; single = one study; weak = abstract-only, snippet, secondary, n<10 or from memory. "derived" = my arithmetic or design choice, not measured. Units: volume cm3, force N, stress N/cm2 (1 N/cm2 = 10 kPa), torque Nm, g Earth 9.81, Moon 1.62 m/s2 (ratio 0.165).

## 0. Plain summary
### (1) Build and behaviour
- A visible muscle = belly (volume V, length L_m, fibres L_f at angle theta) + tendons, under fascia, fat (t_f) and skin (1.5-2 mm, companion file soft_tissue_mechanics.md). Surface relief = belly bulk + grooves between bellies; fat low-passes it.
- Size is set by sex, body size, training, age. Whole-body muscle ~ 38% of mass in men, 31% in women (R12). Lower-limb total volume tracks mass x height (R2 0.92, R4). Distribution among muscles is nearly fixed (upper limb: 85% of between-person variance is explained by mean fractions, R6). Strength follows volume (volume explains 68-95% of joint-moment variance, R7). Sex differences are in size, not in stress per area (R14, R31).
- Force = stress x PCSA; PCSA = V cos(theta) / L_f (derived definition). Load fraction a = load torque / max torque at that joint angle; synergists scale together to first order (derived). Part of a load scales with g (weight, friction, traction); inertia does not (derived).
- On contraction a muscle shortens, its belly thickens, pennate fibres rotate; volume stays constant (R29), so mean area = V / belly length. Thickness change is large up to ~30% MVC and small beyond (R24); in pennate muscle bulge falls as force rises (R27, R28). Light effort already stiffens muscle 5-10x (companion file).
- Fatigue lowers force with time at a joint-specific rate and raises the neurally driven 8-12 Hz tremor component (R39-R42). Skin follows bone only partly (R47).
### (2) Descriptors with cited targets (spread in tables below)
D1 muscle mass fraction of body mass M 38.4 / F 30.6 % (R12). D2 upper-limb volume fractions: shoulder 52.5, elbow 31.4, wrist 16.0 %; deltoid 15.2 +/- 1 % (R6). D3 elbow-flexion peak torque M 69.5, F 35.4 Nm (R15). D4 grip median peak M 51, F 31 kgf (R36). D5 specific tension 30 (R30) to 55-60 (R31) N/cm2 in vivo, method-dependent. D6 MG fascicle 50.8 -> 32.9 mm, pennation 15.5 -> 33.6 deg, rest -> MVC (R21). D7 thickness change saturates near 30% MVC (R24). D8 subcutaneous fat sum of 8 sites 10-50 mm in athletes (R44). D9 skin-marker artefact 20-48% of humeral axial rotation (R47). D10 tremor 8-12 Hz (R41).
### (3) Measuring on a mesh
Label each muscle sub-mesh. V = sum of signed tetra volumes. L_m = centroid-line length origin to insertion. PCSA from V, L_f = ratio x L_m, theta (tables). Slices: upper arm at 60% of acromion-to-lateral-epicondyle length (the R25 site) for belly thickness, width, area, fat thickness; forearm at 25-30% from the elbow; thigh at 50%. Relaxed vs flexed: thickness, width, area, girth, with V held constant. Groove depth = height of neighbouring belly crests above the valley line on a slice. Skin slide = displacement of a surface point vs the same bone-fixed point after a pose change. Fat check = skin-to-muscle-surface distance along normals.

## 1. Size and architecture of major superficial muscles
Lower limb: C = Charles 2019 MRI/DTI, 10 adults (5 M, 5 F), 27 +/- 4 y, sexes pooled (R1; Fmax there = PCSA x 30 N/cm2 assumed). H = Handsfield 2014 young female subgroup (n=8, 30 y) as quoted in R3 (units not stated, taken as cm3). W = Ward 2009 fixed cadavers, 21 legs, 83 +/- 9 y, 9 M 12 F, fibre length normalised to sarcomere 2.7 um, density 1.056 g/cm3 (R2).
| Muscle | Volume C (SD) / H | L_m C mm | L_f C / W mm | Pennation C / W deg | PCSA C / W cm2 | Conf |
|---|---|---|---|---|---|---|
| Gluteus maximus | - / 747 (93) | - | - / 157 | - / 22 | - / 33.4 | single |
| Rectus femoris | 249 (65) / 217 | 323 | 142 / 76 | 8 / 14 | 18.5 / 13.5 | single |
| Vastus lateralis | 606 (151) / 699 | 335 | 196 / 99 | 15 / 18 | 32.1 / 35.1 | single |
| Vastus medialis | 415 (115) / 355 | 336 | 159 / 97 | 14 / 30 | 27.1 / 20.6 | single |
| Biceps femoris long head | 194 (55) / 196 | 261 | 204 / 98 | 11 / 12 | 10.0 / 11.3 | single |
| Semitendinosus | 186 (55) / 146 | 324 | 183 / 193 | 8 / 13 | 10.7 / 4.8 | single |
| Gastrocnemius medial | 230 (48) / 243 | 254 | 97 / 51 | 10 / 10 | 23.7 / 21.1 | single |
| Gastrocnemius lateral | 128 (35) / 135 | 240 | 122 / 59 | 9 / 12 | 11.6 / 9.7 | single |
| Soleus | 461 (108) / 410 | 349 | 146 / 44 | 12 / 28 | 32.3 / 51.8 | single, C vs W disagree |
| Tibialis anterior | 129 (22) / 121 | 300 | 137 / 68 | 7 / 10 | 9.6 / 10.9 | single |
Note: soleus fibre length differs 3.3x (C 146 vs W 44 mm; R32 says direct cadaver 56 vs MRI 78 mm in 3 cadavers), PCSA 1.6x, volume +77% in C. Elderly fixed specimens understate size. Age: women 69 y (n=11) vs young H: vastus lateralis 318 vs 699, rectus femoris 120 vs 217, gluteus maximus 576 vs 747, soleus 340 vs 410, tibialis anterior 95 vs 121 cm3 (R3; derived -54, -44, -23, -17, -21 %).
Upper limb and torso: V = Vidt 2012 MRI, 18 adults 75.1 +/- 4.3 y (10 M 176 cm 81 kg, 8 F 162 cm 69 kg), male / female (R5). A = Murray 2000 cadaver architecture, 10 specimens (R8). Young (n=10, 20th pct F to 97th pct M): total 1427-4426 cm3, deltoid 15.2 % (derived 217-673 cm3) (R6).
| Muscle | Volume M / F cm3 (V) | Architecture (A) | Conf |
|---|---|---|---|
| Biceps brachii | 179 (37) / 98 (17) | long head optimal fascicle 12.8 cm, moment arm 4.7 cm | single |
| Brachialis | 111 (20) / 79 (19) | not in abstract | single |
| Brachioradialis | 54 (9) / 26 (7) | fascicle 17.7 cm (longest), PCSA 1.2 cm2 (smallest), peak moment arm 7.7 cm; PCSA ~1/3 of pronator teres at equal mass (R11), pronator fascicle 5.5 cm | single |
| Triceps brachii, 3 heads | 369 (54) / 222 (35) | PCSA 14.9 cm2 (largest), long head 12.7 cm, moment arm 2.3 cm | single |
| Deltoid | 370 (40) / 243 (47) | - | single |
| Pectoralis major | 263 (65) / 130 (38) | - | single |
| Latissimus dorsi | 325 (79) / 197 (47) | - | single |
| Wrist-flexor group (PL, FDS, FDP, FPL, APL) | 199 (53) / 112 (14); FCR 47/34, FCU 48/28 | - | single |
| Wrist-extensor group (ECU, EDC, EDM, EIP, EPL, EPB) | 113 (20) / 70 (14); ECRL+ECRB 60/38 | - | single |
| Total upper limb | 2589 (388) / 1565 (245) | - | single |
Ratios M/F (derived from the volumes): biceps 1.83, brachialis 1.41, brachioradialis 2.08, triceps 1.66, deltoid 1.52, pectoralis 2.03, latissimus 1.65, total 1.65. Density for volume to mass: 1.056 (R2), 1.041 g/mL (R13).

## 2. Scaling with sex, body size, training, age
| Item | Value | n, population, method | Ref | Conf |
|---|---|---|---|---|
| Whole-body skeletal muscle | M 33.0 kg (38.4 %), F 21.0 kg (30.6 %); upper body 40 % and lower body 33 % less in women (read as women lower; consistent with total -36 %, derived) | 468 adults 18-88 y, whole-body MRI | R12 | strong |
| Lower-limb total volume | R2 0.85 on mass, 0.92 on height x mass; single muscles median R2 0.52 (mass), 0.61 (h x m), 0.66 (total volume); muscle length / bone length ~constant; volume vs bone volume R2 0.75 | 24 young adults, MRI | R4 | single |
| Sex, cross-section | women smaller by 45 % biceps, 41 % elbow flexors, 30 % vastus lateralis, 25 % knee extensors; strength 52 % (arm) and 66 % (leg) of men | 8 M + 8 F | R14 | single |
| Sex, biceps in bodybuilders | CSA ~2x in men; 35 % larger per kg lean mass or per cm height; fibre area 9607 vs 5386 um2 | 8 M + 5 F elite, CT | R16 | single |
| Strength per volume (older adults, derived) | elbow flexors 0.156 (M) / 0.166 (F) Nm/cm3; extensors 0.125 / 0.121 | from R5 volumes and torques | R5 | weak |
| Training, time course | upper-body thickness +12-21 % (M), +10-31 % (F), lower body +7-9 % in 12 wk; chest and triceps significant by wk 6 | 17 M + 20 F, ultrasound | R17 | single |
| Training, early | quadriceps CSA +3.5/+5.2 % at d20, +6.5/+7.4 % at d35 (~0.2 %/day, derived); fascicle +9.9 %, pennation +7.7 % | 7 men, MRI + ultrasound | R18 | single |
| Training, pennation | triceps pennation 15-53 deg (long head), 9-26 deg (medial); thickness vs pennation r 0.88 / 0.83; trained differ from normal | 32 men untrained to bodybuilders | R19 | single |
| Elbow strength, trained | peak torque bodybuilders 93.3 vs untrained 69.5 Nm (+34 %, derived) | 11 BB, 18 M, 15 F | R15 | single |

## 3. Shape change with contraction
| Item | Value | n, method | Ref | Conf |
|---|---|---|---|---|
| Medial gastrocnemius, rest -> MVC, ankle 110 deg | pennation 15.5 -> 33.6 deg; fibre 50.8 -> 32.9 mm (-35 %, derived); aponeurosis distance unchanged; PCSA +34.8 %. At rest, ankle 90 -> 150 deg: pennation 15.8 -> 27.7, fibre 57.0 -> 34.0 mm, PCSA 42.1 -> 63.5 cm2 (PCSA depends on posture) | ultrasound, men | R21 | single |
| Passive fascicle length over knee/ankle postures | MG 59 -> 32, LG 65 -> 41, soleus 43 -> 30 mm; MG angle 22-67 deg | 6 men, ultrasound | R22 | single |
| Straight-fibre constant-thickness model | underestimates rest -> MVC change: LG pennation 9-12 deg, fibre 6-15 mm; soleus 9-14 deg, 6-8 mm | 6 men | R23 | single |
| Thickness vs intensity | most changes up to 30 % MVC, little above; smallest detectable: biceps thickness 4 % MVC, brachialis 5 %, tibialis pennation 9 %, internal oblique 22 %; external oblique unreliable | 6 muscles, ultrasound + EMG, 0-100 % MVC | R24 | single |
| Elbow flexors at 30 % MVC | thickness up, width down at every site (shape, not just size); thickness-based area errors at rest from slackness | 11 men, MRI | R25 | single (no values read) |
| Moment arms at 20 / 60 % MVC | generally larger than at rest (thickening), biggest at flexed angles (50, 80, 110 deg) | 10 men, MRI | R26 | single |
| Gearing, force dependence | higher force -> less thickness bulge, smaller pennation rise, faster shortening (cycling); turkey: high force = little fibre rotation | human MG; turkey | R27, R28 | single each |
| Volume | constant in isolated muscle (abstract not read); fibres must bulge radially when they shorten | frog | R29 | weak |
Derived rule: fusiform belly with fibre shortening s: mean area ~ A0 / (1 - s); e.g. s 5 % -> +5.3 %; thickness change ~ half of that if width also changes. For pennate muscle the belly can stay constant in thickness (R21), so show bulge from fibre angle, not from thickness.

## 4. Force-length, force-velocity, stress (Hill type)
Defaults read from OpenSim-core source (R33), literature in R34-R35. l, v normalised to optimal fibre length L0.
| Item | Value | Ref | Conf |
|---|---|---|---|
| Thelen active force-length | f_L = exp(-(l-1)^2 / 0.45); min activation 0.01. Human optimum sarcomere 2.7 um used to normalise fibre length (R2) | R33, R2 | strong (code) |
| Millard active force-length | active from 0.4441 L0; transition 0.73; shallow slope 0.8616; floor 0.1 | R33 | strong (code) |
| Passive force-length | Thelen: f = (exp(5 (l-1)/0.6) - 1)/(exp(5) - 1), l > 1 (strain 0.6 at 1 F0). Millard: strain 0.7 at 1 F0, stiffness 0.2 low / 2.857 at F0, curviness 0.75 | R33 | strong (code) |
| Tendon | Thelen: strain 4 % at F0 (toe shape 3.0, toe force 33 % F0) | R33 | strong (code) |
| Force-velocity | Thelen: a/F0 = Af 0.25, eccentric plateau Flen 1.4, vmax 10 L0/s; Millard: isometric slope 5.0, concentric slope near vmax 0.25, eccentric 0.15, eccentric multiplier 1.4, curviness 0.6 / 0.9. Literature 1.1-1.8 for eccentric (second-hand) | R33; R35 | code strong; literature weak |
| Activation dynamics | Thelen 15 ms up / 50 ms down; Millard 10 / 40 ms; fibre damping 0.1; max pennation acos(0.1) = 84.3 deg | R33 | strong (code) |
| Age | Thelen 2003: Fmax -30 %, lower vmax, slower deactivation, stiffer passive; predicted ankle power at 120 deg/s -40 % vs measured -39-44 % at ~70 y (vmax value not in abstract) | R34 | single |
| Specific tension, quadriceps in vivo | 30 +/- 5 (also 29 +/- 5 by simpler method) | 27 untrained men, tendon force / PCSA | R30 | single |
| Same, other method | M 55 +/- 11, F 57.3 +/- 13, boys 54 +/- 14, girls 59.8 +/- 15; quadriceps force M 11.4 kN (PCSA 214 cm2), F 8.7 kN (152 cm2) | 20 adults, 20 children; PCSA = volume / optimal fascicle | R31 | single |
| Model values in use | 61 (elderly-cadaver PCSA), 25 (young cadaver; cat triceps surae 23), 37, 60, 100 (elbow flexors) | review | R32 | weak |
Lesson (derived): stress and PCSA must come from the same method. Check: triceps PCSA 14.9 cm2 x 30 N/cm2 x moment arm 0.023 m = 10 Nm, against measured 46 Nm (older men, R5): a 4-5x shortfall (long-head moment arm used for all heads), so calibrate Fmax to the measured joint torque, not to stress x cadaver PCSA.

## 5. Strength, load and activation (inputs to the dial)
| Item | Value | n, method | Ref | Conf |
|---|---|---|---|---|
| Elbow flexion peak torque | M 69.5 (SE 4.3) at 120 deg; F 35.4 (2.4) at 90 deg; bodybuilders 93.3 (4.8) at 120 deg; at 75 deg torque is 20 % (M) / 25 % (BB) below the 120 deg value | 18 M, 15 F, 11 BB | R15 | single |
| Upper-limb moments, young | shoulder adductors 67.9 +/- 28.4; wrist extensors 10.2 +/- 4.6 Nm; ratio 6.5 | 10 adults, F 20th pct to M 97th pct | R7 | single |
| Upper-limb moments, older M / F | elbow flexors 53.5 / 33.7; extensors 46.2 / 27.0; wrist flexors 13.7 / 5.4; wrist extensors 11.3 / 5.9 Nm; shoulder abductors 31.7 / 18.3 | 10 M, 8 F, 75 y | R5 | single |
| Grip, median peak | M 51 kgf (500 N, age 29-39); F 31 kgf (304 N, age 26-42) | 49,964 people, 12 UK studies | R36 | strong |
| Surface EMG vs force | linear for first dorsal interosseous; non-linear (curved) for biceps and deltoid, 0-80 % MVC; direction not in abstract | 16 people, ~200 ramps | R38 | single |
| Forearm EMG -> grip force | 6-muscle linear model predicts grip to 300 N within 27-41 N | 8 men | R37 | single |
| Reduced gravity | peak vertical force falls in proportion to g; muscle activation does not scale simply (quadriceps rises at low speed); static holding is purely weight-driven (derived) | review | R52 | single |
Worked cases (all derived; forearm weight ignored; lever 0.33 m elbow to hand centre, my estimate; 10 kg mass):
- Bucket carried at the side, arm straight: hand force 98 N. Grip fraction = 98/500 = 20 % (M), 98/304 = 32 % (F). Elbow torque ~0. On the Moon (16 N): 3.2 % and 5.3 %.
- Same bucket held out, forearm horizontal: torque 32 Nm = 47 % of M peak (69.5; the 90 deg value is lower, 75 deg is -20 %, so the fraction is higher), 91 % of F peak (35.4 at 90 deg). Moon (5.3 Nm): 7.7 % and 15 %. Above 30 % MVC the visible bulge is near its plateau (R24), so Earth strain reads "maximal", Moon reads "light".
- Cart push (symbolic): needed force F = C_rr m g + m a; usable force <= mu_foot m_body g. Weight terms scale with g; the inertia term m a does not, so on the Moon a heavy cart is harder to start relative to traction. No cited mu or C_rr found.

## 6. Fat over muscle, definition
| Item | Value | n, method | Ref | Conf |
|---|---|---|---|---|
| Subcutaneous fat, sum of 8 sites | 10-50 mm in athletes; accuracy 0.2 mm (18 MHz); sites include brachioradialis, distal triceps, lateral and front thigh, medial calf, abdomen, erector spinae | 12 athletes, 36 sums | R44 | single (per-site mm not in abstract) |
| Skinfold vs ultrasound | slope 0.61 (biceps) to 1.59 (thigh); skin thickness varies 2x; skinfolds do not give fat thickness | 19 female athletes | R44 | single |
| Contest body fat | 4.5 % (from 14.8 %, method not stated); 7.4 % DXA (from 17.5 %, 88.6 -> 73.3 kg) | 1 male each | R45 | weak (n=1) |
| Dieting, female fitness | fat mass -35-50 %, lean mass (DXA) unchanged, triceps thickness unchanged: definition comes from fat loss at constant muscle | 27 dieters, 23 controls | R46 | single |
| Population fat thickness | triceps face F 17.6 mm; thigh M 8.1 / F 18.0; abdomen M 19.1 / F 25.2; rectus abdominis 17.1 (M) / 13.9 (F) mm | companion file soft_tissue_mechanics.md, R44 (Annunziata 2025) | companion | single |
| Visibility threshold | no measurement of the fat thickness at which a muscle edge or groove stops being visible was found | - | - | gap |
Derived engine rule (calibrate on scans): skin = muscle surface offset by t_f along normals, then smoothed; for two round bellies (radius R, half-spacing s) the groove depth is g(t) = (R+t) - sqrt((R+t)^2 - s^2). With R = s = 30 mm: 30, 17, 13.5, 10, 8 mm for t = 0, 5, 10, 20, 30 mm. Real fat fills valleys, so measured visibility will fall faster. Anatomy-transfer work also treats the flesh volume as skin eroded by fat thickness (R50).

## 7. Fatigue and tremor
| Item | Value | n, method | Ref | Conf |
|---|---|---|---|---|
| Endurance time vs %MVC | power law, joint-specific; most to least resistant: ankle, trunk, hand/grip, elbow, knee, shoulder; one pooled curve is not adequate | 194 papers, 369 points | R39 | strong (coefficients not read) |
| Three-compartment model | rate constants F (fatigue) 0.00058 (shoulder) to 0.00589 (ankle); R (recovery) 0.00168 to 0.0182; RMS error 2.7 s (shoulder) to 11.2 s (ankle), elbow 9.9 s; fitted at 10-90 % MVC | 1e6 combos, 9e6 runs | R40 | single (elbow F, R not read) |
| Rule of thumb | ~1 min at 50 % MVC, ~6 s at 100 %; "no fatigue below 15 %" is contested | from memory | - | weak |
| Physiological tremor | tremor-coherent EMG peak at 9-12 Hz in all 8 young adults who had one (300 g load); 5-7 Hz in 5 of 7 such elderly; no age effect on the mechanical-resonance component | 100 young + 100 elderly | R41 | single |
| Fatigue and tremor | fatiguing one wrist raises 8-12 Hz peak power in both arms (finger only) | 7 people | R42 | single (no amplitude) |
Derived dial: fatigue state f in 0..1 from the three-compartment model; add 8-12 Hz oscillation to belly thickness and end-point, amplitude growing with f (no cited amplitude).

## 8. Skin sliding over muscle
| Item | Value | n, method | Ref | Conf |
|---|---|---|---|---|
| Upper arm, humeral axial rotation | marker artefact = 20-48 % of the true rotation, depending on person, humeral position, elbow flexion (if it is under-rotation, skin follows 52-80 %, derived) | 6 adults | R47 | single |
| Knee region, four tasks | marker error up to 29.3 mm RMS; knee flexion error 24.3 deg; thigh worse than shank | young adults, fluoroscopy | R47 | single |

## 9. Lightweight muscle models in graphics (what exists, no invented parameters)
| Model | Representation and controls | Ref |
|---|---|---|
| Teran 2005 | 30 upper-limb muscles from Visible Human data; tetrahedral FE in a lattice; transversely isotropic, quasi-incompressible; fibre field; passive + active parts | R48 |
| Saito 2015 | one anatomy template; per-muscle hypertrophy/atrophy dials and a fat dial as physical growth + elasticity; volumetric Projective Dynamics; bone proportion tool | R49 |
| Kadlecek 2016 | personalised bones, muscles, fat fitted to scans of an actor in poses; inertia, gravity, collisions | R50 |
| Dicko 2013 | skin eroded by fat thickness defines the volume into which a reference anatomy is mapped | R50 |
| Neumann 2013 | data-driven arm-muscle bulge from multi-view capture; inputs pose, body shape, external force; later poster cites elbow flexion with 0-14 kg barbell weights | R51 |
| Roussellet 2018; Lee, Sifakis, Terzopoulos 2009 | "Dynamic implicit muscles for character skinning"; "Comprehensive biomechanical modeling and simulation of the upper body": titles only, abstracts not read | - |
| OpenSim Hill models | line-of-action actuators (L0, tendon slack, Fmax, theta; defaults vmax 10 L0/s, Fmax 1000 N, L0 0.1 m, slack 0.2 m); no volume | R33 |
Fit for this engine (derived): muscles as volume-conserving bellies on a line of action, Fmax from calibrated torque, activation a = load fraction, then bulge = f(a) from sections 3 and 5.

## 10. Not found
- Measured flexed-minus-relaxed arm or forearm girth, and thickness increase in mm or % for biceps, triceps, forearm at set %MVC.
- Volumes, PCSA, lengths for trapezius, rectus abdominis, obliques, serratus, sternocleidomastoid; young-adult upper-limb per-muscle volumes (R6 full text is not open).
- Fat thickness at which definition is lost; forearm fat thickness; acute pump swelling %; endurance-time coefficients; tremor amplitude change with fatigue; skin strain % at the elbow (knee strain-field paper, PMID 22961262, has no numbers in its abstract).
- Primary values for eccentric force (1.1-1.8 is second-hand) and human vmax by fibre type.

## References
R1 Charles JP, Suntaxi F, Anderst WJ. PLoS One 2019;14(10). PMID 31613899. || R2 Ward SR, Eng CM, Smallwood LH, Lieber RL. Clin Orthop Relat Res 2009. PMC2650051.
R3 Montefiori E, et al. PLoS One 2020. PMID 33259496. || R4 Handsfield GG, et al. J Biomech 2014;47:631-8. PMID 24368144.
R5 Vidt ME, et al. J Biomech 2012;45:334-41. PMC3246044. || R6 Holzbaur KR, Murray WM, Gold GE, Delp SL. J Biomech 2007;40:742-9. PMID 17241636.
R7 Holzbaur KR, Delp SL, Gold GE, Murray WM. J Biomech 2007;40:2442-9. PMID 17250841. || R8 Murray WM, Buchanan TS, Delp SL. J Biomech 2000;33:943-52. PMID 10828324.
R11 Lieber RL, et al. J Hand Surg 1992;17:787-98. PMID 1401782. || R12 Janssen I, Heymsfield SB, Wang ZM, Ross R. J Appl Physiol 2000;89:81-8. PMID 10904038.
R13 Abe T, Kearns CF, Fukunaga T. Br J Sports Med 2003;37:436-40. PMID 14514537. || R14 Miller AEJ, MacDougall JD, Tarnopolsky MA, Sale DG. Eur J Appl Physiol 1993;66:254-62. PMID 8477683.
R15 Tsunoda N, O'Hagan F, Sale DG, MacDougall JD. Eur J Appl Physiol 1993;66:235-9. || R16 Alway SE, Grumbt WH, Gonyea WJ, Stray-Gundersen J. J Appl Physiol 1989;67:24-31. PMID 2759948.
R17 Abe T, DeHoyos DV, Pollock ML, Garzarella L. Eur J Appl Physiol 2000;81:174-80. PMID 10638374. || R18 Seynnes OR, de Boer M, Narici MV. J Appl Physiol 2007;102:368-73. PMID 17053104.
R19 Kawakami Y, Abe T, Fukunaga T. J Appl Physiol 1993;74:2740-4. PMID 8365975. || R20 Kawakami Y, Abe T, Kuno SY, Fukunaga T. Eur J Appl Physiol 1995;72:37-43. PMID 8789568.
R21 Narici MV, et al. J Physiol 1996;496:287-97 (abstract via search text). || R22 Kawakami Y, Ichinose Y, Fukunaga T. J Appl Physiol 1998;85:398-404.
R23 Maganaris CN, Baltzopoulos V, Sargeant AJ. J Physiol 1998;512:603-14. PMC2231202. || R24 Hodges PW, Pengel LH, Herbert RD, Gandevia SC. Muscle Nerve 2003;27:682-92. PMID 12766979.
R25 Akagi R, et al. J Physiol Anthropol 2011;30:169-74. || R26 Akagi R, et al. J Appl Biomech 2012;28:63-9.
R27 Dick TJM, Wakeling JM. J Appl Physiol 2017;123:1433-42. PMID 28860176. || R28 Azizi E, Brainerd EL, Roberts TJ. PNAS 2008;105:1745-50 (via search text).
R29 Baskin RJ, Paolini PJ. Am J Physiol 1967;213:1025-30. PMID 6051170. || R30 Erskine RM, Jones DA, Maganaris CN, Degens H. Eur J Appl Physiol 2009;106:827-38.
R31 O'Brien TD, et al. Exp Physiol 2010;95:202-10. PMID 19748968. || R32 Chen Z, Franklin DW. Ann Biomed Eng 2023. PMC10172227 (text read to char 100,000 only).
R33 OpenSim-core source (github.com/opensim-org/opensim-core, main): Thelen2003Muscle.cpp, Millard2012EquilibriumMuscle.cpp, Muscle.cpp, ForceVelocityCurve.cpp, FiberForceLengthCurve.cpp, ActiveForceLengthCurve.cpp; read 2026-10-19.
R34 Thelen DG. J Biomech Eng 2003;125:70-7. PMID 12661198. || R35 Millard M, Uchida T, Seth A, Delp SL. J Biomech Eng 2013;135:021005. PMID 23445050.
R36 Dodds RM, et al. PLoS One 2014;9:e113637. PMID 25474696. || R37 Hoozemans MJ, van Dieen JH. J Electromyogr Kinesiol 2005;15:358-66. PMID 15811606.
R38 Lawrence JH, De Luca CJ. J Appl Physiol 1983;54:1653-9. PMID 6874489. || R39 Frey Law LA, Avin KG. Ergonomics 2010;53:109-29. PMID 20069487.
R40 Frey-Law LA, Looft JM, Heitsman J. J Biomech 2012;45:1803-8. PMID 22579269. || R41 Elble RJ. Clin Neurophysiol 2003;114:624-35. PMID 12686271.
R42 Morrison S, et al. Exp Brain Res 2005;167:609-21. PMID 16078030. || R43 Furness P, Jessop J, Lippold OC. J Physiol 1977;265:821-31. PMID 856991.
R44 Muller W, et al. Br J Sports Med 2016;50:45-54. PMID 26702017; Muller W, et al. Br J Sports Med 2013;47:1028-35. PMID 24055780.
R45 Rossow LM, et al. Int J Sports Physiol Perform 2013;8:582-92. PMID 23412685; Kistler BM, et al. Int J Sport Nutr Exerc Metab 2014;24:694-700. PMID 24901578.
R46 Hulmi JJ, et al. Front Physiol 2016;7:689. PMID 28119632. || R47 Cutti AG, et al. Gait Posture 2005;21:341-9. PMID 15760751; Akbarshahi M, et al. J Biomech 2010;43:1292-301. PMID 20206357; Leardini A, et al. Gait Posture 2005;21:212-25. PMID 15639400.
R48 Teran J, et al. IEEE TVCG 2005;11:317-28. PMID 15868831. || R49 Saito S, Zhou ZY, Kavan L. ACM TOG 2015;34(4); project page users.cs.utah.edu/~ladislav/saito15computational/.
R50 Kadlecek P, et al. ACM TOG 2016;35(6); Dicko AH, et al. ACM TOG 2013;32(6); pages on users.cs.utah.edu/~ladislav/. || R51 Neumann T, et al. Comput Graph Forum 2013;32(2):285-94, doi 10.1111/cgf.12048; Gassel poster, SIGGRAPH 2017.
R52 Sylos-Labini F, Lacquaniti F, Ivanenko YP. BioMed Res Int 2014:547242. PMID 25247179.
