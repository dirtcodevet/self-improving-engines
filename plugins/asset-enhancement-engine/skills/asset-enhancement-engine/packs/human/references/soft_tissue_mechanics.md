# Soft-tissue mechanics by body region: cited numbers for a contact/deformation model

Compiled 2026-10-19 from abstracts and open full texts (Europe PMC, PMC, PLoS, arXiv abstract) and search-result text. Nothing was saved for use. Biomechanics and clinical sources only.
Confidence: strong = 2+ independent studies agree or one large cohort; single = one study; weak = n<10, pilot, assumed, animal, or abstract-only / second-hand. "via R3" = number read in review R3, not in the primary paper. "derived" = my arithmetic on cited numbers. E = Young's modulus, G = shear modulus; for nu 0.49-0.5, E ~ 3G; neo-Hookean mu = G, C10 = G/2 = E/6. All moduli kPa unless stated.

## 0. Proposed per-region deformation model (my reading of the numbers)
1. Picture each contact patch as a short stack (skin, fat, muscle) glued to a rigid floor at depth H = t_skin + t_fat + t_muscle (bone, rib or cartilage). Tissue is nearly incompressible (nu 0.49-0.495, R1, R10), so a dent cannot lose volume: what is pushed in must go sideways.
2. Inputs: region id, pressure p (or force F and footprint radius a), thicknesses t_s, t_f, t_m (section 2), support type (bone-fixed; ribs-sliding for breast; cartilage shell for nose tip), muscle activation 0-1.
3. Stiffening, not softness, limits depth. Gluteal E at load rises 26 -> 2200 (fat, strain 0.16 -> 0.33) and 62 -> 440 (muscle, 0.19 -> 0.47) (R31); breast fat 0.7 -> 17-19 by 30-50% strain (via R3). Use E_t(eps) = E0 exp(k eps), k ~ 26 fat, ~ 7 muscle (derived from the two R31 points; integrates to 1.25-1.65x the measured stress rise, so an upper bound); clamp strain at 0.33 (fat) and 0.47 (muscle).
4. Collapse the stack to one layer of thickness H with 1/E_eff = sum_i (t_i/H)/E_i when the footprint is broad (a >= H). For a narrow footprint (a << H) only layers within about 2a of the surface count.
5. Depth: solve F = (16/9) E_eff sqrt(R) d^1.5 P(chi) for d, chi = sqrt(R d)/H, P = 1 + 1.133 chi + 1.283 chi^2 + 0.769 chi^3 + 0.0975 chi^4 (Hertz sphere with bonded-layer correction, nu 0.5, R48). P grows fast once a > H: a wide press on a thin layer over bone hardly moves. For a >> H the limit is F ~ pi E a^4 d / (2 H^3) (derived, thin incompressible layer). Plain Hertz is only good below ~5% strain in gels and not acceptable for tissue (R49).
6. Skin is a pre-tensioned membrane, not a layer: with a >> t_s it carries load as tension T = E_s t_s eps and adds pressure 2T/R_c on a curved surface. Membrane stiffness E_s t_s: 56 kPa x 1.5 mm = 84 N/m (aspiration, R4) up to 344 kPa x 1.55 mm = 530 N/m (suction, R7). Matters for breast and nose tip; ignore on abdomen and arm.
7. Dent shape: parabola d(r) = d (1 - r^2/a^2) inside the footprint, decaying outside over a length l ~ H.
8. Bulge (my choice, no cited measurement; calibrate on scans): displaced volume V = pi a^2 d/2 goes into a ring of width l; share phi = a^2/(a^2 + H^2) (~0 for a << H where the surface outside also sinks, ~1 for a >= H). Crest height b = phi a^2 d / (l (2a + l)), cap b <= 0.5 d.
9. Muscle activation scales G_m: ~4 relaxed (R25, R27, R28), 22 / 43 at 3 / 7 % max EMG in biceps (R29), 480-880 at 100% MVC (vastus intermedius, R30); E_m = 3 G_m. A lightly flexed arm is 5-10x stiffer; a hard flex far more.
10. Region switches: breast = soft mass (E 0.2-3 in vivo) inside a skin envelope sliding on the chest wall, gravity as body force with sliding boundary (R9, R10). Nose tip = skin envelope 3.7-4.0 mm (R39) over cartilage (aggregate modulus 0.44-0.70 MPa, R40): shell, not slab.
11. Starting small-strain E0: subcutaneous fat 1.6-3 (R3, R23, R4); glandular 3 (R1); relaxed muscle 9-13 (= 3 G); whole abdominal wall 21-28 (R34); cheek 16-31 (R36, R37); skin as membrane (item 6).
12. Check against: mammographic press 11.3 kPa at 91 N (n = 25,286, R19), sitting 17 kPa under the ischial tuberosity with gluteus strain 74% (R32), palpation 70-90 kPa (R52). Values differ 10-100x by method (section 6): pick one method family per region and stay in it.

### Region sheet (cited values only; "-" = no source found; thickness in mm, E in kPa)
| Region | t_skin | t_fat | t_muscle | Support | E0 / notes | Refs |
|---|---|---|---|---|---|---|
| Breast | 1.4-1.6 | mass, from scan | pectoralis behind | ribs, sliding | mass 0.2-3 in vivo (3.2 ex vivo); skin membrane 84-530 N/m | R4, R7-R9 |
| Abdomen | 1.9 (waist) | 19-25 | rectus 14-17 | soft viscera, not bone | whole wall 21-28 | R34, R43, R44 |
| Upper arm, triceps face | 2.0 (deltoid proxy) | 17.6 (F) | 32 | humerus | muscle G 3-4.5 relaxed | R25, R43, R44 |
| Upper arm, biceps face | 2.0 (proxy) | - (8-18 from neighbours) | - | humerus | G 4 relaxed, 22-43 at 3-7% EMG | R29 |
| Shoulder, deltoid | 2.0 | 8.3 (M) - 11.7 (F) | - | humerus | stiffness - | R43, R45 |
| Cheek | - | midface ~14.7 (weak) | - | zygoma, mandible | 16-31; 35-65 over cheekbone | R36, R37 |
| Forehead | 0.73-0.95 | 2.0-2.1 (superficial + deep) | frontalis 0.25-0.35 | frontal bone | 17.3 | R36, R38 |
| Nose tip | envelope 3.7-4.0 | (inside envelope) | - | cartilage 0.44-0.70 MPa | skin tensile ~1 MPa is not nasal | R22, R39, R40 |
| Buttock | dermis 1.3-1.6 | 12.6 | 55.5 | pelvis; seated peak under ischium | fat 26 -> 2200, muscle 62 -> 440 | R31, R32, R42 |
| Thigh | 1.55 | 8.1 (M) - 18.0 (F) | 32.5-38.9 | femur | effective 10-89 | R35, R43, R44 |

## 1. Material stiffness
| Tissue / condition | Value | n, population, method | Ref | Conf |
|---|---|---|---|---|
| Breast fat, ex vivo indentation + inverse, nu 0.495 | 3.25 +/- 0.91 | 169 fresh samples (all types), ex vivo | R1 via R3 | single |
| Breast fibroglandular, same | 3.24 +/- 0.61 | same | R1 via R3 | single |
| Breast fat / gland / fibrous, ex vivo compression at 5% (20%) precompression, 0.1-4 Hz | fat 18-22 (20-24); gland 28-35 (48-66); fibrous 96-116 (218-244) | ex vivo, n not seen | R2 via R3 | single; modulus rises with precompression |
| Breast fat / gland, ex vivo indentation as strain rises to 30-50% | fat 0.7 -> 17-19; gland 0.7-0.8 -> 15-17 | ex vivo (Matsumura 2009, Umemoto 2014) | via R3 | weak |
| Breast fat+gland as one layer, in vivo aspiration (<40 mbar, bilayer inverse) | 3.04 +/- 1.17 | 7 volunteers | R4 | weak (pilot) |
| Breast fat / gland, in vivo shear-wave elastography (E) | 26.1 / 66.4 | 200 healthy women | R5 | single |
| Breast fat / fibroglandular, in vivo MRE (G) | 0.82 / 1.55 right; 0.81 / 1.46 left | 43 women 40-79 y, 1.5 T, passive driver | R6 | single (E ~ 2.5 / 4.7) |
| Breast MRE, other groups (G): fat / gland | 0.43 / 2.45 (1998); 0.33 / 0.64 (2013); 3.3 / 7.5 (2002) | small n, different frequencies | via R3 | weak; 10x spread |
| Breast gravity-fitted neo-Hookean (E): breast / skin / fascia | 0.2-0.3 / 4 / 120 | subject-specific MRI, prone + supine + tilted | R9 | weak |
| Breast neo-Hookean initial G: fibroglandular / adipose | 0.4 / 0.3 | MR images in water and prone | R11 | weak (abstract text seen via search only) |
| Breast FE defaults (E): adipose / glandular / skin; nu | 1 / 10 / 88; 0.49 | assumed from earlier FE papers, no validation | R10 | weak |
| Skin forearm, air-flow indentation, reduced modulus at 10 mN | 14.38 +/- 3.61 (23 y); 6.20 +/- 1.45 (60 y) | two groups of healthy women, n/group not seen | R20 | single |
| Skin breast, in vivo suction cup | 344 +/- 88 (195-480) | 23 women, 16 sites/breast, supine + upright | R7 | single |
| Skin breast, in vivo aspiration bilayer | 56.3 +/- 16.4 | 7 volunteers | R4 | weak |
| Skin forearm, indentation + MRI, neo-Hookean C10 | epidermis 0.12 MPa; dermis 1.11 MPa; hypodermis 0.42 kPa | 1 young man | R21 | weak |
| Skin ex vivo tension (E) | forearm 1.03 +/- 0.06 MPa; neck 1.28 +/- 0.06 MPa | 10 cadavers | R22 | single |
| Subcutaneous fat, ex vivo stretch, initial / final modulus (to 30% strain) | 1.6 +/- 0.8 / 11.7 +/- 6.4 (omental 2.9 / 32) | 44 surgical donors, 19 paired | R23 | single |
| Subcutaneous fat, MRE (G) | 1.85 +/- 0.17 | adults + children, not split | R24 | weak |
| Gluteal fat in vivo, ultrasound + compression, E at load (reads as tangent: secant stress/strain would be ~11 and ~158, derived) | 26.1 +/- 19.0 at 1 N (eps 0.16); 2199 +/- 1355 at 30 N (eps 0.33) | 16 men 20-22 y, 576 mm2 probe | R31 | single |
| Gluteal muscle, same | 62.2 +/- 10.3 at 5 N (eps 0.19); 440.4 +/- 80.0 at 30 N (eps 0.47) | same | R31 | single |
| Relaxed muscle, SSI (G) | 2.99 (gastrocnemius medialis) to 4.50 (tibialis anterior); biceps, triceps inside | 30 adults, 9 muscles | R25 | strong |
| Relaxed gastrocnemius medialis, SWE (E) | 13.84 / 12.78 left / right (G ~ 4.3-4.6, derived) | 24 men, 28 y | R26 | strong (agrees R25) |
| Relaxed muscle, MRE 90-120 Hz (G) | vastus lateralis 3.73 +/- 0.85; medialis 3.91 +/- 1.15; sartorius 7.53 +/- 1.63 | 12 / 14 / 13 subjects | R27 | single |
| Muscle contraction, MRE 90 Hz (G), vastus medialis | 3.69 +/- 0.80 -> 9.52 +/- 2.74 at 20% MVC (1-D); 4.36 -> 9.22 (2-D) | n not seen | R28 | single |
| Biceps brachii, SSI, (G) at 3% / 7% max EMG | 21.7 +/- 6.7 / 42.6 +/- 14.1 | 6 subjects, ramps 0-40% MVC | R29 | single |
| Vastus intermedius, vibro-ultrasound 100 Hz (G): rest; 100% MVC | young 9.5 +/- 3.3; 877.5 +/- 566.7. Older 12.8 +/- 5.4; 482.5 +/- 189.6 | 10 + 10 women (paper's Discussion swaps rest values; Results used) | R30 | single |

## 2. Regional layers and effective stiffness
| Region | Quantity | Value | n, population, method | Ref | Conf |
|---|---|---|---|---|---|
| Breast | skin thickness | 1.44 +/- 0.25 mm (0.87-2.34) | 136 women, breast CT; also 1.45 +/- 0.30 (51 women, CT) | R8 | strong |
| Breast | skin thickness | 1.55 +/- 0.25 mm (0.83-2.4) | 23 women, DermaScanC ultrasound, 16 sites | R7 | strong (agrees R8) |
| Abdomen | subcutaneous fat; rectus muscle | F 25.2 +/- 13.5; 13.9 +/- 3.2 mm. M 19.1 +/- 12.7; 17.1 +/- 3.4 mm | 513 F, 1117 M, 2.5 MHz portable US (abstract/Methods counts differ) | R44 | single |
| Abdomen | skin (waist) | 1.91 mm | 342 adults 18-70 y, 20 MHz US | R43 | strong |
| Abdomen | whole-wall E | M 27.7 +/- 4.5; F 21.0 +/- 3.7 | 18 laparoscopy patients, motion analysis, 20% surface strain | R34 | single |
| Upper arm (triceps face) | fat; muscle thickness | F 17.6 +/- 5.4; 32.1 +/- 6.5 mm | 832 women, US | R44 | single |
| Upper arm / shoulder (deltoid) | fat pad | F 11.7; M 8.3 mm | 220 adults, US | R45 | single |
| Deltoid; suprascapular; thigh | skin (epidermis + dermis) | 2.02; 2.54; 1.55 mm | 342 adults, 20 MHz US | R43 | strong |
| Skin, 28 body regions | total; buttock/chest/neck dermis; back dermis | 0.52-1.98 mm total; 1.32-1.59 mm; 1.94 mm | 452 biopsies, Korean adults, histology | R42 | single |
| Thigh | fat; muscle | F 18.0 +/- 7.4; 32.5 +/- 8.4 mm. M 8.1 +/- 4.1; 38.9 +/- 9.0 mm | 1085 F, 1112 M, US | R44 | single |
| Lower limb, 4 sites, 3 postures | effective E (skin + fat + muscle) | 10.4-89.2; males ~40% above females; no correlation with total thickness | 8 young adults, handheld ultrasound indentation | R35 | single |
| Buttock (gluteal) | fat; muscle thickness | 12.6 +/- 4.7; 55.5 +/- 7.6 mm | 16 young men, US | R31 | single |
| Buttock, seated | peak principal compression: gluteus; fat | strain 74 +/- 7%, stress 32 +/- 9 kPa; strain 46 +/- 7%, 18 +/- 4 kPa | 6 healthy, MRI + FE; paraplegics 1.9x compressive stress | R32, R33 | single |
| Cheek / cheekbone / forehead / lower lip | E, aspiration + neo-Hookean inverse | 31.0 +/- 4.6 / 34.9 +/- 6.6 / 17.3 +/- 4.1 / 33.7 +/- 7.3 | 16 young subjects | R36 | single |
| Cheek; near lip; below cheekbone; cheekbone; chin | E, low-cost indenter + US thickness | 16.2 +/- 5.1; 16.3 +/- 8.4; 27.1 +/- 11.4; 64.8 +/- 17.1; 53.0 +/- 21.0 | 28 subjects | R37 | single; cheek 2x lower than R36, bone-near sites 2-4x cheek |
| Forehead | skin; superficial fat; frontalis; deep fat | M 0.95; 0.75; 0.35; 1.26 mm. F 0.73; 0.67; 0.25; 1.42 mm | 238 volunteers, US | R38 | single |
| Face (39 sites) | dermis max / min; epidermis max | 1.97 mm lower nasal sidewall / 0.76 mm upper eyelid; 63 um upper lip | 10 cadaver heads, punch biopsy | R41 | single |
| Nose | tip / supratip skin-envelope thickness (paper says "skin thickness", US, so likely skin + subcutis) | 3.98 +/- 0.84 / 3.54 +/- 0.72 mm (group A); 3.69 +/- 0.64 / 3.73 +/- 0.54 (group B) | 72 rhinoplasty patients, 26 y, US | R39 | single |
| Nose | septal cartilage aggregate modulus (confined compression) | 0.44-0.70 MPa | 49 tests, 21 patients | R40 | single |

## 3. Contact models for layered tissue over bone
- Hertz sphere on half-space: F = (4/3) E* sqrt(R) d^1.5, E* = E/(1 - nu^2), a = sqrt(R d). Valid only at small strain (gels below ~0.05; unacceptable for biological tissue; Fung or one-term Ogden fit best) (R49).
- Flat punch on half-space: F = 2 a E* d. Hayes 1972 for a layer of thickness h bonded to a rigid base: E = (1 - nu^2) F / (2 a kappa d), kappa(a/h, nu) from tabulated solutions, kappa -> 1 for thick layers and rises with a/h and nu (R46). Nonlinear FE shows kappa also rises with indentation depth, and friction matters at large a/h and nu near 0.5 (R47). Hayes assumes a rigid base, fine for bone, wrong for ribs/cartilage that flex.
- Bonded-layer correction for the Hertz sphere: factor 1 + 1.133 chi + 1.283 chi^2 + 0.769 chi^3 + 0.0975 chi^4, chi = sqrt(R d)/h, nu 0.5 (Dimitriadis 2002, R48; coefficients read in two later papers, arXiv 2406.17157 and RSC Soft Matter 2023 d3sm00432e supplement, which also mention a more accurate variant; original full text not read). Confidence single.
- Thin incompressible bonded layer, a >> h: F ~ pi E a^4 d / (2 h^3) (derived; same scaling as rubber-block compression factor 1 + 2S^2, S = a/2h). Squeezed fat cannot escape: stiffness grows with (a/h)^2.
- Winkler (elastic foundation, independent springs): p = K d/h small, p = -K ln(1 - d/h) larger, K = (1 - nu) E / ((1 + nu)(1 - 2 nu)); K = 17 E at nu 0.49, 34 E at 0.495 (derived), i.e. confined-column stiffness: upper bound for wide contact, no bulge, no neighbour coupling (R50, knee-cartilage use, E 4 MPa, nu 0.45; no soft-tissue use found).
- Whole-stack indentation gives effective moduli (R35: 10-89, R34: 21-28, R36-R37: 16-65 on face) that are not material constants: they move with probe size, site and posture.

## 4. Gravity and posture
| Item | Value | n, method | Ref | Conf |
|---|---|---|---|---|
| FE breast in 3 positions, neo-Hookean, sliding chest-wall boundary | Hausdorff error prone 2.17, supine 1.72, supine-tilted 5.90 mm; neo-Hookean struggles at large strain | subject-specific MRI | R9 | weak |
| Prone-to-supine registration, neo-Hookean, gravity as the only load | target error 69.7 -> 5.6 mm (14 data sets); phantom 19.3 -> 0.9 mm | 14 clinical data sets | R12 | single |
| Same, optimised material parameters + gravity direction | 8.44 +/- 5.5 mm on 45 skin markers; fibroglandular overlap > 82% | 5 breasts | R14 | single |
| Homogeneous tissue model, gravity-loaded prone | skin RMS error 4.2 and 3.6 mm; internal 3.7 and 4.7 mm | 2 volunteers | R13 | weak |
| Heterogeneous template FE, gravity 1 G, chest wall constrained in AP only (sliding) | no posture validation reported | phantoms | R10 | weak |
| Nipple displacement prone -> supine: AP to sternum; mediolateral; craniocaudal; to chest wall | 84 +/- 44; 54 +/- 24; 27 +/- 15; 48 +/- 20 mm | 11 patients, MRI | R15 | single |
| Same, lesion: to chest wall; to skin; to nipple base | 32 +/- 31; 6 +/- 5; 8 +/- 6 mm | same | R15 | single |
| Breast volume standing vs supine (surface scan) | supine vs standing differ by 120.31 cc (p<0.01, sign not stated); sitting vs standing 7.15 cc (ns) | 100 women, 200 breasts, handheld 3-D scanner | R16 | single |
| Same question, structured-light scanner | no significant volume effect of posture (F(2,57) = 0.151); scan completeness differs by posture | 10 women, standing + supine | R17 | weak; conflicts R16 |
| Breast surface change upright -> supine | significant, tracks BMI and cup size (no mm in abstract) | 5 subjects, tilt table + 3-D imaging | R18 | weak |
| Anterior mid-thigh "muscle thickness", standing vs supine | M 3.7 +/- 1.0 vs 3.1 +/- 0.8 cm; F 2.5 +/- 0.7 vs 2.1 +/- 0.7 cm | 283 inpatients, 10 MHz US (fluid shift and contraction confound) | R51 | weak |
| Upper-arm tissue sag by gravity | no biomechanical source found | - | - | gap |

## 5. Typical contact pressures
| Situation | Value | n, method | Ref | Conf |
|---|---|---|---|---|
| Breast pressed between mammography plates | CC 90.8 +/- 14.2 N = 11.3 +/- 3.6 kPa; MLO 106.3 +/- 20.6 N = 8.7 +/- 2.0 kPa. 100-140 N / 10.3-13.5 kPa judged acceptable for pain; > 20 kPa in 12.3% (NL), < 5 kPa in 0.6% | 25,286 women; 1,155 women; 37,518 compressions | R19 | strong |
| Sitting, ischial tuberosity, measured; FE | 17 +/- 4; 18 +/- 3 kPa | 6 healthy, measured interface pressure + MRI-based FE | R32 | single |
| Hand pressing during clinical breast exam | 70-90 kPa over > 1 cm2 | stated in an abstract, no primary source seen | R52 | weak |
| Light / deep abdominal palpation | 0.51 / 0.55 N (four-quadrant); 0.50 / 0.58 N (nine-region); area not given | 23 healthy adults, force sensor | R53 | single |
| Pressure at the skin that gives gluteal fat strain 0.33 / muscle 0.47 | ~52 kPa (30 N / 576 mm2, derived) | 16 men | R31 | single |
| Arm resting against torso | no measurement found. Estimate: arm segments ~5% of body mass (textbook anthropometry, not checked here) = 34 N at 70 kg; over 50-150 cm2 = 2-7 kPa | derived | - | weak |
| Pressure pain thresholds by hand algometer (1 cm2 disc) | thresholds not in the abstract, not recorded | 50 volunteers, 9 muscles, deltoid reference | R54 | gap |

## 6. Where methods disagree, and gaps
- Breast fat, small strain: MRE G 0.8 (E ~ 2.5), in vivo aspiration 3.0, ex vivo 3.2, gravity fit 0.2-0.3, SWE 26, ex vivo compression 18-24 at 5-20% precompression. A 100x spread. Precompression is shown to matter (R2); frequency (MRE / SWE are dynamic), sliding vs fixed chest wall, and one-layer vs bilayer fits are plausible but untested here.
- Skin: tensile 1000+ (cadaver), suction 344, aspiration 56, air-flow indentation 6-14, gravity-fitted 4. Each probes different depth, strain and assumed thickness; do not mix.
- Relaxed muscle: SSI and MRE 3-4.5 vs vibro-ultrasound at 100 Hz 9.5-12.8 (assumed density 1000 kg/m3).
- Cheek: aspiration 31 vs indenter 16; bone-near sites 2-4x stiffer in the indenter data (R37), consistent with a thinner layer over bone but not shown to be caused by it (R35 found no thickness correlation).
- Gaps: no in-vivo modulus for deltoid, biceps face or triceps face skin/fat; no in-vivo modulus for nose tip; no cheek fat-pad thickness (midface fat ~14.7 mm in 25 women BMI < 21 is the nearest, PMID 42602736, weak); Hayes kappa table values and Sommer 2013 human abdominal fat parameters (PMID 23811521) not in any readable text; Joodaki and Panzer 2018 skin review (R55) not mined; Rajagopal-era c1 values not found.

## References
R1 Samani A, Zubovits J, Plewes D. Phys Med Biol 2007;52:1565-76. PMID 17327649. || R2 Krouskop TA, Wheeler TM, Kallel F, Garra BS, Hall T. Ultrason Imaging 1998;20:260-74. PMID 10197347.
R3 Teixeira AM, Martins P. Front Bioeng Biotechnol 2023 (review). doi:10.3389/fbioe.2023.1161815. || R4 Briot N, Chagnon G, Connesson N, Payan Y. Clin Biomech 2022;99:105743. PMID 36099706.
R5 Dzoic Dominkovic M, et al. Diagnostics 2020;10:393. PMID 32532143. || R6 Aloufi AS, et al. NMR Biomed 2025;38:e70134. PMID 40887883.
R7 Sutradhar A, Miller MJ. Skin Res Technol 2013;19:e191-9. PMID 22891621. || R8 Shi L, et al. Med Phys 2013 (breast CT skin). PMID 23464328; Huang SY, et al. Med Phys 2008. PMID 18491511.
R9 Mira A, Carton AK, Muller S, Payan Y. Clin Biomech 2018;60:191-9. doi:10.1016/j.clinbiomech.2018.10.020 (arXiv 1811.10221). || R10 Sturgeon GM, et al. Med Phys 2016;43:2207. PMID 27147333.
R11 Carter TJ, Tanner C, Hawkes DJ. Proc SPIE 7261:726124 (2009). doi:10.1117/12.810092. || R12 Eiben B, et al. Ann Biomed Eng 2016;44:154-73. PMID 26577254.
R13 Rajagopal V, et al. Acad Radiol 2008;15:1425-36. PMID 18995193. || R14 Han L, et al. IEEE Trans Med Imaging 2014;33:682-94. PMID 24595342.
R15 Carbonaro LA, et al. Eur J Radiol 2012;81:e771-4. PMID 22502792. || R16 Macek A, et al. J Clin Med 2024;13:709. PMID 38337404.
R17 Tong OLH, et al. Sci Rep 2020;10:14087. doi:10.1038/s41598-020-70476-2. || R18 Reece GP, et al. Med Eng Phys 2015;37:375-83. PMID 25703742.
R19 Moshina N, et al. Eur J Radiol 2021 PMID 33823373; Radiography 2020 PMID 32052779; Branderhorst W, et al. Eur J Radiol 2015 PMID 25596915.
R20 Boyer G, Pailler Mattei C, et al. Med Eng Phys 2012;34:172-8. PMID 21807547. || R21 Tran HV, et al. Comput Methods Biomech Biomed Engin 2007;10:401-7. PMID 17891674.
R22 Griffin MF, et al. J Otolaryngol Head Neck Surg 2017. PMID 28420435. || R23 Alkhouli N, et al. Am J Physiol Endocrinol Metab 2013;305:E1427-35. PMID 24105412.
R24 Debernard L, et al. J Biomech 2011. PMID 21074773. || R25 Lacourpaille L, et al. Physiol Meas 2012;33:N19-28. PMID 22370174.
R26 Lima K, et al. Muscles Ligaments Tendons J 2017;7:347-52. doi:10.11138/mltj/2017.7.2.347. || R27 Bensamoun SF, et al. J Magn Reson Imaging 2006. PMID 16374878.
R28 Bensamoun SF, et al. J Magn Reson Imaging 2008. PMID 18407545. || R29 Nordez A, Hug F. J Appl Physiol 2010;108:1389-94. PMID 20167669.
R30 Wang CZ, Li TJ, Zheng YP. PLoS One 2014;9:e101769. PMID 24991890. || R31 Isogai K, et al. J Phys Ther Sci 2022;34:777-83. doi:10.1589/jpts.34.777.
R32 Linder-Ganz E, et al. J Biomech 2007;40:1443-54. PMID 16920122. || R33 Linder-Ganz E, et al. J Biomech 2008;41:567-80. PMID 18054024.
R34 Song C, et al. J Biomech 2006;39:587-91. PMID 16389099. || R35 Zheng Y, Mak AF. IEEE Trans Rehabil Eng 1999;7:257-67. PMID 10498372.
R36 Luboz V, Promayon E, Payan Y. Ann Biomed Eng 2014;42:2369-78. PMID 25186433. || R37 Martelly E, et al. Ann Biomed Eng 2024;52:3184-95. PMID 38977529.
R38 Zhuang J, et al. Aesthet Surg J Open Forum 2025;7:ojaf140. PMID 41451119. || R39 Mohebbi A, et al. Med J Islam Repub Iran 2021;35:170. PMID 35685194.
R40 Richmon JD, et al. Am J Rhinol 2006. PMID 17063745. || R41 Chopra K, et al. Aesthet Surg J 2015;35:1007-13. PMID 26508650.
R42 Lee Y, Hwang K. Surg Radiol Anat 2002;24:183-9. PMID 12375070. || R43 Laurent A, et al. Vaccine 2007;25:6423-30. PMID 17640778.
R44 Annunziata G, et al. J Transl Med 2025;23:236. doi:10.1186/s12967-025-06159-1. || R45 Poland GA, et al. JAMA 1997;277:1709-11. PMID 9169899.
R46 Hayes WC, Keer LM, Herrmann G, Mockros LF. J Biomech 1972;5:541-51. PMID 4667277. || R47 Zhang M, Zheng YP, Mak AF. Med Eng Phys 1997;19:512-7. PMID 9394898.
R48 Dimitriadis EK, et al. Biophys J 2002;82:2798-810. PMID 11964265. || R49 Lin DC, Shreiber DI, Dimitriadis EK, Horkay F. Biomech Model Mechanobiol 2009;8:345-58. PMID 18979205.
R50 Bei Y, Fregly BJ. Med Eng Phys 2004;26:777-89. PMID 15564115. || R51 Yasuda T, et al. Arch Rehabil Res Clin Transl 2020;2:100063. PMID 33543089.
R52 Van Nguyen C, Saraf RF. ACS Appl Mater Interfaces 2014;6:16368-74. PMID 25148477. || R53 Hsu JL, Lee CH, Hsieh CH. PeerJ 2020;8:e10511. PMID 33362971.
R54 Fischer AA. Pain 1987;30:115-26. PMID 3614975. || R55 Joodaki H, Panzer MB. Proc Inst Mech Eng H 2018;232:323-43. PMID 29506427.
