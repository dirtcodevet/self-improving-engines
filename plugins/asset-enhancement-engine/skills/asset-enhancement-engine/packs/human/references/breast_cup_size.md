# Bra cup size as measurable geometry (adult women): reading a cup off a mesh and building to a cup
Compiled 2026-10-19 from PubMed abstracts, Europe PMC/PMC open full texts, Crossref and publisher pages. Read-only web research; clinical, anthropometric, textile and standards sources. Keys (Xx##) are listed in section 7.
Confidence: strong = 2+ independent studies agree; single = one study; weak = abstract/second-hand/secondary transcription/unverified. "Derived" = my arithmetic on cited numbers, not a measurement. 1 in = 2.54 cm. UBCC/OBCC = under-bust / over-bust chest circumference.
Hard truth: cup letter is a retail label built on a girth difference, not a volume. At a fixed letter, volume varies about +-25% between women (CV 18-27%, section 2) and about +-10-16% between brands (derived, rough, from Mos25 SDs). Build to volume; delta is only the readable label.
Provenance: web pages and abstracts read; six report/conference PDFs were auto-cached by the fetch tool in its session folder; five were read there (CAESAR vols I-II, Zhe10, Hass18, Hohenstein summary), one was encrypted and unread; nothing else saved.

## 0. Procedures (12 lines)
R1 Read, pose and landmarks: stand the mesh as in a tape survey (arms hanging/slightly abducted, normal expiration). Inspiration raises UBCC-based band by mean 1.9 in (SD 1.8, up to 4 band sizes) and OBCC by 0.75 in (about 1 cup) [McG06]. Mark sternal notch, both nipples (most anterior point), IMF (lowest breast contour).
R2 UBCC: take the horizontal girth at IMF height of the TORSO WITH BREAST TISSUE REMOVED (chest-wall section); the raw scan path overestimates it by about 12 cm (limits -4.6 to +28) in large/ptotic breasts [McG18].
R3 OBCC: horizontal girth through the nipple plane (ISO/CAESAR convention), taut-tape = convex hull of the section; also log the widest-breast level (tape surveys use either; no study gives the difference). OBCC from scans is biased only +2.4 cm (-3.4 to +8.4) [McG18].
R4 Arithmetic: delta = OBCC - UBCC. EN 13402-3: band = UBCC to nearest 5 cm, letter from 2-cm bins on delta (AA 10-12, A 12-14, B 14-16, C 16-18, D 18-20 ...). JIS/KS/GB: 2.5-cm bins (AA 7.5, A 10, B 12.5, C 15, D 17.5). US/UK: 1 in per letter, band = UBCC+0 (modern) or +4/+5 in (traditional). Same delta gives different letters (bin-centre list under table 1); state the system in every output.
R5 Calibrate: tape/EN delta under-calls the fitted (worn) cup by 1-2 letters [Hass18; McG06 and Whi12 agree in sign]; output "tape cup" and "fitted cup = tape + 1.5 +-0.5" (derived from Hass18) separately; never a single letter without the band and system.
R6 Prefer volume: segment each breast (outline: IMF below, change of curvature above, sternal edge, anterior axillary fold), close with a posterior surface following the pectoral curvature, V in mL per breast. Standing-mesh volumes read 8-22% below prone ones, rising with size [Col23]; correct before using prone/specimen-based tables. Mesh-friendly cross-check: geodesic medial-IMF to lateral-IMF arc over the nipple (Pechter hemi-circumference, band-34 chart under table 1).
B1 Build, input: system, band b, letter c. Convert to US/UK index k (A=1, B=2, C=3, D=4, DD=5, E=6) and EU band cm; UBCC target = band cm (EN) +-2.
B2 Target volume per breast at band 75 EU (UK 34, AU 12): A 230, B 300, C 410, D 520, DD 640 mL (derived pool of Sand23, Hua17, McG11; range +-25%; E+ add about 120-150 mL per letter, weak). Pooled step about 110 mL/letter from B (King17: 135-138 cc/cup from bra capacity/implants; Asia practice 100).
B3 Band shift by the sister rule (default full strength, contested [Hass18]): one EU band step up (+5 cm) at the same letter equals one letter up at band 75, V(b,k) = V75(k + (b-75)/5). So V(80,C) = V75(D) = 520 mL and V(70,C) = V75(B) = 300 mL; 36B = 34C = 32D [Cha19: 14B ~ 12C].
B4 Footprint: width W = 14.1 + 0.14 (band - 75) cm, times (V/350)^0.16; length = 0.96 W [Zhe10, Hua11, Col22]. Lower pole (nipple-to-underbust surface arc) 6.2 (A) to 7.6 (D) cm at band 75, about +0.5 cm per letter [Zhe10].
B5 Projection P: closed cap on that footprint, V = 0.81 * (pi/6) P (3 r^2 + P^2), r^2 = W*L/4 (0.81 calibrated on Col22 means, derived). At band 75: V 230/300/410/520/640 gives P about 3.9/4.5/5.4/6.2/6.9 cm, W 13.2/13.8/14.5/15.0/15.5 cm (derived; +-0.7 cm).
B6 Verify by re-running R1-R6 on the built mesh: accept when delta falls in the requested bin (+-1 bin of tape cup is normal), V within +-15%, UBCC within +-2 cm. SN-N 19 +-2 cm, nipple-midline 10 cm (section 3).

## 1. Definitions (how band and letter are computed)
| System | Band rule | Cup rule and step | Source | Conf |
|---|---|---|---|---|
| EN 13402-3 (EU) | UBCC rounded to nearest 5 cm (60=58-62 ... 125=123-127) | delta=bust girth - underbust girth, ranges (lo,hi]; 2 cm: AA 10-12, A 12-14, B 14-16, C 16-18, D 18-20, E 20-22, F 22-24, G 24-26, H 26-28 | MFish, Wik; DIN EN 13402-3:2017 uses only the two girths [Hass18] | weak (standard text not read; 2 transcriptions agree) |
| Japan JIS (L 4006:1998 per Wik; "L 4005" elsewhere) | UBCC to 5 cm | 2.5 cm: AA 7.5 (+-1.25), A 10, B 12.5, C 15, D 17.5, E 20 | Wik, Wacoal text via search | weak |
| Korea KS K 9404 | UBCC to 5 cm | 2.5 cm: AAA 5.0, AA 7.5, A 10, B 12.5, C 15, D 17.5, E 20 (bust at fullest point, UBCC at IMF) | Lee23, Wik | single |
| China FZ/T 73012-2004 | UBCC 5 cm steps (65-100 used) | 2.5 cm: AA 7.5 ... G 25.0 | Zhe10 | single |
| US/UK traditional | UBCC (in) +4 if even, +5 if odd; across 26 websites the add-on ranged 2-6 in | cup = OBCC - band, 1 in per letter; US A1 B2 C3 D4 DD/E5 DDD/F6 G7 H8; UK A B C D DD E F FF G GG H HH J (1 in each) | McG06, Wik | strong (rule), weak (letter lists) |
| US/UK modern | band = UBCC to even inch (+0) or store chart; Army ATB: +4 in, reduced to 0 when UBCC >= 34 in | 1 in per letter | Choi23, Wik | weak |
| Australia/NZ | dress-size bands (AU 12 = EU 75 = UK 34) | Wik says 2 cm/cup, AA-DD UK labels; AU papers use UK-type letters A-G | Hass18, Wik | weak |
| France/Italy | 5 cm | 2 cm (some French makers 3 cm); Italy 2.5 cm, some 2 cm. Inch vs 2-cm systems differ 21% per letter | Wik | weak |
| Half cups A/B, B/C | no standard defines them; EN bins are half-open, JIS bins +-1.25 cm. My convention: label "A/B" when delta is within +-0.25 step of the A|B edge | none found | weak |
Same delta in different systems (centres of bins, derived): delta=15 cm is EN B, JIS C, US/UK(+0) DDD/F, US/UK(+4.5) A/B. Centres, delta cm: EN AA 11, A 13, B 15, C 17, D 19, E 21 | JIS AA 7.5, A 10, B 12.5, C 15, D 17.5, E 20 | US+0 A 2.5, B 5.1, C 7.6, D 10.2, DD 12.7 | US+4.5 A 14.0, B 16.5, C 19.1, D 21.6, DD 24.1 (+-1.3 for +4/+5).
Pechter hemi-circumference (medial IMF to lateral IMF over nipple, supine, band-34 chart): 7-7.5 in A, 8-8.5 B, 9-9.5 C, 10-10.5 D, 11 DD (= 17.8-18.4, 20.3-21.6, 22.9-24.1, 25.4-26.7, 27.9 cm); standing differs from supine by 2 in [Pec98 via McG06, Wik; weak]. Hemi-circumference cup matched subject-reported cup exactly in 6/16 and within one size in 13/16 (n=16, mean D); the standard tape method differed significantly [McG06; single].

## 1b. What moves the measured number
| Factor | Effect | n, population, method | Ref | Conf |
|---|---|---|---|---|
| Respiration | inspiration: band +1.9 in (SD 1.8; 0-6), OBCC +0.75 in (0-2), cup under-called 1-4 sizes (0-4 on expiration) | 16 large-breasted AU women (mean D), tape | McG06 | single |
| CAESAR vs Wollongong protocol | CAESAR UBCC at max of quiet respiration; Wollongong at end of normal expiration | protocols | CA02, Col22 | single each |
| Posture for volume | standing scans under-read prone by 8-22% (rises with size); 7-10% in D+ ptotic | n=378; n=50 | Col23; Col17a | strong |
| Posture for hemi-circumference | 2 in supine vs standing | Pechter via McG06 | | weak |
| Scan UBCC | bias about +12 cm (LoA -4.6 to +28) in large ptotic breasts; shrinks if breasts digitally removed; bias grows with band, volume, ptosis | n=111 AU, volume 57-1672 mL, bra 10A-18G, handheld scan vs tape | McG18 | single |
| Scan OBCC and cup | OBCC bias +2.4 (LoA -3.4 to +8.4); scan cup within one cup size over range | same | McG18 | single |
| Scan delta vs tape delta | scan bust-minus-underbust about 11% smaller | n=176 plus-size ZA women, TC2 scanner | Pan11 | single |
| Tape tension | "firm, not tight, no indentation"; ICC 0.998-0.999 over 3 repeats; no quantitative tension study found | n=16 | McG06 | weak |
| Nipple level vs fullest point | ISO/CAESAR use nipple level; McG06/Lee23/Col22 use fullest/widest; three overbust paths gave three values (no numbers) | | CA02, Cha19 | weak |
| Over a bra vs nude | CAESAR women measured over own bra; thin bra (13 mm) lifts breast 2.16 cm, thick (23 mm) moves it 2.15 cm medially | CAESAR; n=129 students, 3D scan | CA02; Zho23 | single |
| Band label vs body | a 30-in UBCC wears label 36; 36-band bras measure only 27 in unstretched (3 makers) | Pechter via Cha19 | | weak |
| Fitted vs measured | 85% of 104 wore ill-fitting bras; traditional method over-calls band, under-calls cup (n=45, worse at big bands); only 56.4% of 163 Korean patients wore the correct cup | | McG10; Whi12; Lee23 | strong |
| Judging cup by eye/scan | surgeons estimating cup from 3D scans: kappa 0.148 (weighted 0.623), n=32 subjects x 10 raters; lay raters right 43.3% (27 photos, 500 raters) | | Sand23; Mal22 | single |
| Brand | cup volume SD across 7 brands, band 36: A 30.9, B 40.1, C 62.2, D 69.7, DD 122.8 cc; interval not always >100 cc | bras on mannequin | Mos25; King17 | strong |

## 2. Volume per cup (per breast, mL)
| Study | n, population, method | A | B | C | D | DD+ | Notes | Conf |
|---|---|---|---|---|---|---|---|---|
| Sand23 | 32 Norwegian students 19-29, Vectra 3D, self-reported US cup, mean+-SD | 159+-70 (n=2) | 270+-71 (10) | 417+-114 (8) | 517+-137 (6) | DD 440 (1); E 641; G 702; J 920; DDD+ 675+-141 (5) | volumes rise with cup except DD n=1 | single |
| Hua17 | 278 of 605 Chinese patients (48.8 y) who knew cup; V from anthropometric formula; +- is SE (inferred) | 261+-8 (78) | 328+-7 (142) | 408+-11 (44) | >=D 539+-34 (14) | | whole group 340+-109 (92-919) | single |
| Hua11 | 216 US patients 35-82 y (median 54), dedicated breast CT (prone pendant), self-reported cup, +-SE | A/AA 325+-44 (21) | 468+-36 (55) | 803+-33 (78) | D/DD 1204+-69 (62) | | 1.4-2.3x the others (B to D): outlier geometry | single |
| McG11 | 104 AU women (43.5 y per McG10, same n and mean fit), water displacement, professionally fitted in one brand | | | | | mean fit 12DD | mean 642 L / 643 R mL; range 125 (10A) to 1900 (24DD); same fitted size spans a range; same cup not same volume across bands | single |
| Hass18 | 57 Austrian women 19-67 y, bra 75B-95G, handheld 3D | | | | | | 691.8+-349.6 (128.9-1860); 80B spans 129-551 | single |
| Col22 | 97 AU soldiers 25.6 y, BMI 25.4, standing scan in sports bra | | | | | | 365.2+-167.7 (103.6-885.8); fitted cup mode C (A-H) | single |
| Col20, Col17b | 378 AU women (prone Artec): R breast by BMI: normal 367+-32 (n=163), overweight 683+-38 (103), obese 1077+-38 (112), +-SE; 356 women 48-3100 mL, age no effect | | | | | | BMI x2-3; overlapping samples, one group | single |
Increments: King17 135 cc/letter (3 brands x 5 sizes by water/CT) and 138.2 cc (79 augmentations), 130 narrow band / 150 wide band; single. Chan19 (22 bras of one style, clay fill, water displacement; AU bands 12-18): cup volume rises steadily with letter and band; 14B ~ 12C; single. 100 mL/letter "Asian practice" (cited in Lee23) and 205 mL (Bengtson, cited in Sand23): weak. Derived steps from the pool: +70, +110, +110, +120 mL; ratio 1.25-1.3 per letter (V ~ L^3).
Sister sizes (same volume when band +1 step and cup -1): supported by Cha19 and bra-capacity logic (Wik underwire table = hemisphere piD^3/12, geometric not measured); NOT supported by Hass18 (group SDs overlap), McG11 (volume of one cup not uniform across bands). Treat as default with large error.
Cup vs volume correlation is weak: cup vs mastectomy weight r 0.25-0.38 (n=243) [Per22]; delta vs volume r=0.169 (n=37, 80A wearers) [Lee03]. Tissue density 0.98+-0.05 g/mL (0.92-1.09; n=15 specimens) [Cha19] (0.94 used by Col20). Asymmetry: |L-R|/L 1.1-14.9% by size group [Hass18]; 125 women: <=10 mL 2.2%, 11-25 21.9%, 26-50 28.9%, 51-100 29.3%, >100 17.7% (Gabriel 2011 via Hass18, weak).

## 3. Other 3-D geometry
| Quantity | Value (cm unless noted) | n, population, method | Ref | Conf |
|---|---|---|---|---|
| Footprint width by band (3D nude, standing) | band 70: 13.1-14.0; 75: 14.0-14.2; 80: 14.6-14.8; 85: 15.7-16.0 (about +0.14 cm per cm band); same across A*-D* at a band | 456 Chinese 20-39 y; 322 in the 14 common sizes; classes by depth/width ratio | Zhe10 | single |
| Depth (projection) by class | DWR 0.30/0.34/0.38/0.42 (A*-D*); band 75: 4.3/4.8/5.3/5.9; 70: 4.0/4.8/5.3; 80: 4.4/4.8/5.6/6.1; 85 (B-D): 5.4/6.1/6.6. Their letters are DWR classes, not retail cups | same | Zhe10 | single |
| Bust point to underbust arc (lower pole) | 75: 6.2/6.7/7.0/7.6; 70: 5.9/6.7/6.7; 80: 6.4/6.6/7.2/7.4; 85: 7.1/7.5/7.8 (A*-D*) | same | Zhe10 | single |
| Soldiers | width 15.79+-1.73, length 15.17+-1.48, projection 4.35+-1.03 (2.32-7.12), SN-N 18.38+-1.95, notch to upper border 5.77+-1.08, notch to lower border 20.94+-1.84, closed-model surface 444+-104 cm^2 | 97 AU, standing in sports bra, outline markers | Col22 | single |
| Chinese patients (tape, standing) | base width 14.3+-1.4 (8.5-23.5); N-IMF 7.5+-1.6 (stretched 9.1+-1.7); SN-N 21.6+-2.8; nipple-midline 10.0+-1.5; areola 3.8+-1.0; nipple projection 0.9+-0.3 | 605 pts, 48.8 y, 1210 breasts | Hua17 | single |
| Vietnamese patients | N-IMF (IR) 7.1+-1.5; projection MP 3.8+-0.7 (90 deg to chest wall under breast); medial/lateral radii 9.6/11.7 (nipple to fold ends, horizontal; NOT base width); SN-N 19.7+-2.6; nipple-nipple 19.3+-2.1 | 240 pts, 48.9 y; Archimedes on specimens | Vie22 | single |
| Other SN-N / N-IMF | Longo (88 Caucasian mastectomy, 51 y) SN-N 24.7+-3.5, N-IMF 9.3+-3.2, base 16.7+-4.8; Westreich (50 "perfect") SN-N 18.6; Qiao (young Chinese, 250 breasts) SN-N 19.1, volume 310-330 mL; see breast_nac_form.md | quoted in Hua17 | | weak |
| Pendant breast CT by cup | effective diameter at chest wall A/AA 11.1+-0.5, B 11.4+-0.3, C 13.0+-0.2, D/DD 13.7+-0.2; length 5.7/7.1/9.4/9.7; glandular fraction 17.7/19.2/13.2/13.2% | n=216, as in section 2 | Hua11 | single |
| Width vs volume | W ~ V^0.16 (11.1 to 13.7 cm for 325 to 1204 mL) (derived from Hua11); length/width 0.96 (Col22) | | | weak |
| Predictors of mass | SN-N and BMI explain about half the variance of breast mass | 93 UK women A-H, bra-fitter cup | Bro12 | single |
Volume formulas: Qiao V = (pi/3) MP^2 (MR+LR+IR-MP) = spherical cap of height MP on a sphere of radius mean(MR,LR,IR); vs specimen y=0.808x+53.3, r=0.966, bias +22.7+-51.8 mL (242 breasts) [Vie22/Qiao 1997; single]. Hua17 BREAST-V variant: V = -231.66 + 0.5747 SN-N^2 + 18.5478 BP + 14.5087 N-IMF (reproduces 340 mL mean; not specimen-validated by authors; single). Descamps: weight g = 35.4 SN-N + 60.66 N-IMF - 1239.64 (214 reductions; gives -20 g at Chinese-patient means, so hypertrophy only) [Des08; single]. Cap-model check on Zhe10 band 75 (A*-D*, L=0.96W, k=0.81): 294/342/380/450 mL (derived, within pool +-25%).
Shape: upper:lower pole 45:55, nipple angle +20 deg, convex lower pole, linear/slightly concave upper pole (100 attractive models, 3/4 view) [Mal12; single]. Martin 1957 breast height: flat 3-5, hemispheric 5-6, conical >6 cm (via Zhe10, weak).

## 4. How cup is obtained from scans in practice
| Source | Landmarks | Circumference path | Notes |
|---|---|---|---|
| CAESAR (US/NL/IT, 18-65 y; women 1255/691/386) CA02 | bust point (thelion) = most anterior protrusion of the bra cup; scan landmarks Z13/Z14; bust-point breadth and chest height measured on scan | bust/chest girth at nipple level (ISO 4.4.9), steel tape; underbust horizontal, parallel to floor, just below cups, at max quiet respiration | women wore own bra; self-reported bra size recorded (US/IT band 30-48 x cups a-dd; NL UBCC cm). Statistics not obtained |
| ANSUR II / Army ATB Choi23 | bust available, underbust not measured | underbust extracted from 3D scans, regressed to tape values; cup per 1 in delta; 10 cups x 7 bands; bands 32/34/36 cover 92.03% | single, weak details |
| Wollongong Col22, Col20 | sternal notch, nipple, 1-cm outline markers | tape OBCC at widest bust, UBCC just below bust, end of normal expiration; volume from scan with a posterior wall cut by a plane/curve following pectoralis | prone for volume, standing for position |
| Hassmann Hass18 | skin-marker outline and fiducials; IMF taken from supine scan in ptotic breasts | Coons-patch posterior base; EN 13402 cup under-calls worn cup by 1-2 | handheld Sense, n=59 |
| PolyU Zhe07/Zhe10 | vertical-section breast boundary; 103 measures | nude scans, DWR instead of delta | classes cover 97.4% vs 94.3% for FZ/T 73012 |
| Lee04, Lee03 | "folding line" method gives a natural breast boundary | moire scan, n=37 | base area about 235 cm^2, volume 547 cm^3 |
Accuracy of volume methods: 3D laser scan 2.27+-0.99% repeat deviation vs MRI 1.56+-0.52% (12 breasts) [Kov07]; anthropometric 645 vs specimen 623.5 mL, r=0.975; mammography r=0.997 (30 mastectomies) [Kay11]. ISO 8559-1:2017 / ISO 20685-1 define the girths and scan protocol; text not read (paywalled).

## 5. Population distributions
| Survey | n, population | UBCC / OBCC (cm) | Cup / band distribution | Ref | Conf |
|---|---|---|---|---|---|
| Soldiers | 97 AU women, 25.6 y | UBCC 76.9+-5.6 (67.4-95.2); OBCC 89.7+-8.6; delta 12.8 (derived); earlier AU Army survey 76.5+-5.9 / 90.7+-7.5 | fitted band mode AU 10 (8-16; = EU 70), cup mode C (A-H) | Col22 | single |
| Vietnam | 240 patients, 48.9 y, BMI 22.2 | CC3 (lower breast) 77.4+-6.2; CC2 (nipple) 85.2+-6.8; delta 7.8 (derived) | | Vie22 | single |
| Fudan | 605 patients, 48.8 y | chest under axilla 86.9+-6.2; across nipple 89.6+-8.4 (65-122) | self-reported cup (n=278): A 28.1, B 51.1, C 15.8, D 3.2, E 1.4, F 0.4% | Hua17 | single |
| Asan (Korea) | 163 patients, 44 y, BMI 23.0 | | tape cup (KS): A 62.6, B 16.0, C 16.0, D-E 5.5%; specimen 362+-240 g | Lee23 | single |
| UTSW (US) | 243 patients (486 breasts), BMI 27.1, 77% white | | US cup A 4.1, B 15.6, C 30.5, D 23.0, DD/E 18.5, DDD/F 4.5, G 3.7%; band 32 7.0, 34 36.6, 36 24.7, 38 18.5, 40 6.2, 42 4.5% | Per22 | single |
| Oslo students | 32, 19-29 y | | A 2, B 10, C 8, D 6, DD 1, E 2, G 2, J 1 (counts) | Sand23 | single |
| Wollongong community | 104 AU women, 43.5 y | | mean fitted 12DD; bands 10-24, cups A-G (recruited with large breasts) | McG10/11 | single |
| PolyU | 456 Chinese 20-39 y | band 65-100; about 3% fall outside FZ/T 73012 | 75 band most populated | Zhe10 | single |
Not found in open sources: SizeUSA, Size UK, SizeGermany, Size Korea, Size China, Wacoal means for underbust/bust/cup (press items say C is commonest in Germany, B-C in Japan; unverifiable, weak). CAESAR stats sit in the restricted database.

## 6. Where sources disagree (use the range)
- Volume of a given letter: B 270-470, C 410-800, D 520-1200 mL; low end = standing 3D/formula in Asian and young cohorts, high end = prone pendant CT in older US patients.
- Per-letter step: 70-135 (pool, King17) to 205 mL (Bengtson, weak); steps grow with size.
- Tape delta vs fitted cup: soldiers' mean delta 12.8 cm is EN "A" while the fitted mode is C (derived); Vietnamese delta 7.8 cm is below EN AA. EN under-calls Western fits; JIS/KS 2.5-cm bins may track Asian retail letters better (my inference, weak).
- Sister sizes: Cha19 yes; Hass18, McG11 no. Base "width" is 14.3 (Hua17) to 21 cm (Vie22 radii sum) depending on definition: always record the definition.
- Gaps: no numeric nipple-level vs fullest-point difference; no tape-tension study; no per-band volume table (McG11 table unread); half-cup definitions; Japan/Australia standard text unread.

## 7. Sources (key: authors year, journal, DOI/PMID)
CA02 Robinette KM, Blackwell S, Daanen H et al. 2002, CAESAR Final Report Vols I-II, AFRL-HE-WP-TR-2002-0169 (TU Delft DINED copy).
Cha19 Chan M, Lonie S, Mackay S, MacGill K. 2019, PRS Glob Open 7:e2273. 10.1097/GOX.0000000000002273 PMID 31624680.
Choi23 Choi-Rokas H, Li P, Mitchell KB. 2023, AHFE Digital Human Modeling. 10.54941/ahfe1003348.
Col17a Coltman CE, McGhee DE, Steele JR. 2017, Ergonomics 60:439. 10.1080/00140139.2016.1176258 PMID 27066812.
Col17b Coltman CE, Steele JR, McGhee DE. 2017, Ergonomics 60:1576. 10.1080/00140139.2017.1330968 PMID 28532249.
Col20 Steele JR, Coltman CE, McGhee DE. 2020, J Sport Health Sci 9:140. 10.1016/j.jshs.2019.05.003 PMID 32099722.
Col22 Coltman CE, Brisbine BR, Molloy RH, Steele JR. 2022, Front Sports Act Living 4:821210. 10.3389/fspor.2022.821210 PMID 35356093.
Col23 Coltman CE, McGhee DE, Steele JR. 2023, Ergonomics 66:330. 10.1080/00140139.2022.2081365 PMID 35603985.
Des08 Descamps MJL et al. 2008, PRS 121:397. 10.1097/01.prs.0000298319.01574.02 PMID 18300955.
Hass18 Hassmann M, Dastl J, Krach W. 2018, 3DBODY.TECH proc. 10.15221/18.207.
Hua11 Huang SY, Boone JM, Yang K et al. 2011, Med Phys 38:2180. 10.1118/1.3567147 PMID 21626952.
Hua17 Huang NS, Quan CL, Mo M et al. 2017, PLoS One 12:e0172122. 10.1371/journal.pone.0172122 PMID 28192525.
Bro12 Brown N, White J, Milligan A et al. 2012, Am J Hum Biol 24:158. 10.1002/ajhb.22212 PMID 22287066.
Kay11 Kayar R et al. 2011, Breast Cancer (Auckl) 5:43. 10.4137/BCBCR.S6128 PMID 21494401.
King17 King NM, Lovric V, Parr WCH, Walsh WR, Moradi P. 2017, PRS 139:1084. 10.1097/PRS.0000000000003247 PMID 28445356.
Kov07 Kovacs L et al. 2007, Breast 16:137. 10.1016/j.breast.2006.08.001 PMID 17029808.
Lee03 Lee HY, Lee OK, Hong KH. 2003, J Korean Soc Cloth Text 27:270. Lee04 Lee HY, Hong K, Kim EA. 2004, Appl Ergon 35:353. 10.1016/j.apergo.2004.03.004 PMID 15159200.
Lee23 Lee SJ, Han WY, Eom JS, Kim EK, Han HH. 2023, PRS Glob Open 11:e5141. 10.1097/GOX.0000000000005141 PMID 37583394.
Mal12 Mallucci P, Branford OA. 2012, JPRAS 65:8. 10.1016/j.bjps.2011.08.006 PMID 21868295. Mal22 Malphrus EL et al. 2022, JPRAS 75:4197. 10.1016/j.bjps.2022.08.038 PMID 36180339.
McG06 McGhee DE, Steele JR. 2006, Br J Sports Med 40:970. 10.1136/bjsm.2005.025171 PMID 17021004.
McG10 McGhee DE, Steele JR. 2010, J Sci Med Sport 13:568. 10.1016/j.jsams.2010.03.003 PMID 20451452.
McG11 McGhee DE, Steele JR. 2011, Int J Cloth Sci Technol 23:351. 10.1108/09556221111166284.
McG18 McGhee DE, Ramsay LG, Coltman CE, Gho SA, Steele JR. 2018, Ergonomics 61:464. 10.1080/00140139.2017.1349936 PMID 28673203.
Mos25 Moscarelli J et al. 2025, Aesthetic Plast Surg 49:1954. 10.1007/s00266-024-04546-5 PMID 39623226 (means unread; SDs only).
Pan11 Pandarum R, Yu W, Hunter L. 2011, Ergonomics 54:866. 10.1080/00140139.2011.597515 PMID 21846287.
Pec98 Pechter EA. 1998, PRS 102:1259. 10.1097/00006534-199809040-00056 PMID 9734454 (abstract only; numbers via McG06, Cha19, Wik).
Per22 Perez K, Teotia SS, Haddock NT. 2022, PRS Glob Open 10:e4401. 10.1097/GOX.0000000000004401 PMID 35837131.
Sand23 Sandberg LJ, Tonseth K, Kloster-Jensen K, Reece G, Selber JC. 2023, PRS Glob Open 11:e5046. 10.1097/GOX.0000000000005046 PMID 37305199.
Vie22 Le QH, Nguyen HC. 2022, Asian Pac J Cancer Prev 23:665. 10.31557/apjcp.2022.23.2.665 PMID 35225480.
Whi12 White J, Scurr J. 2012, Ergonomics 55:704. 10.1080/00140139.2011.647096 PMID 22397508.
Zho23 Zhong Z, Zhang B, Hu Y et al. 2023, Int J Environ Res Public Health 20:3856. 10.3390/ijerph20053856 PMID 36900867.
Zhe07 Zheng R, Yu W, Fan J. 2007, Int J Ind Ergon 37:697 (not opened). Zhe10 Zheng R, Yu W, Fan J. 2010, Int Conf 3D Body Scanning, Lugano, 113-119. 10.15221/10.113.
MFish mobilefish.com EN 13402 cup/band table page (secondary). Wik en.wikipedia.org "Brassiere measurement" (read 2026-10-19; secondary, partly unsourced; its underwire volume table is a geometric hemisphere, not data).
