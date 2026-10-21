# Human hair: cited numbers for a strand-based hair engine (scalp, brows, lashes, body hair)

Compiled 2026-10-19 from abstracts, open full texts (Europe PMC), BioNumbers entries, pbrt and Blender docs, Wikipedia (secondary) and search-result text. Nothing saved for use; the fetch tool cached 5 PDFs by itself (see end). The web-search budget ran out part-way, so "Not found" items were not searched to exhaustion.
Conf: S = 2+ sources agree or large cohort; 1 = single study; W = weak (abstract, snippet, secondary, clinic page, small n, or recalled). (d) = my arithmetic. "via X" = number read in X, not in the primary. a/b = major/minor axis of the shaft section (>= 1). Keys Rn at the end.

## 0. How hair is built and behaves (own words)
1. Build. A hair is a keratin tube grown from a bulb in an oblique follicle. Shell (cuticle): 4-8 flat cell layers, each cell ~0.5 um thick x 50 um long, overlapping up to 5/6, lifted ~2.5-3 deg off the fibre axis (R8, R34); that tilt shifts the highlight lobes off the mirror direction. Core (cortex): pigment granules and nearly all stiffness (E ~3 GPa); a medulla is optional. Section shape and curl are set in the bulb: straight follicle -> round, curved bulb -> flat and curly (R25). Section a/b ~1.25 East Asian, ~1.3 European, ~1.75 African descent (W).
2. Layout. Follicles sit in follicular units (FU) of 1-4 (rarely 5) hairs: ~1 FU/mm2 in Caucasian posterior scalp, ~0.6 in Black patients (R6); a FU is the natural clump (mean 1.55 hairs in one trichoscopy series (d), ~2.0 in surgical series). Density is regional (temporoparietal ~18% below vertex (d)) and ancestral (Caucasian ~225 > Hispanic ~175 > Asian ~155-165 ~ African descent ~150-160 per cm2) and falls ~0.33/cm2 per year.
3. Direction. Roots leave the skin at ~5-20 deg at the front hairline and temples and steepen to 30-60 deg over the mid and back scalp (surgical sources, W). The direction field is smooth, points forward over the front, turns down at the temple, and spins about one posterior-vertex whorl (85-95% Caucasian; double apical in ~90% of one African-American series).
4. Cycle. Each follicle cycles alone: anagen 2-7 y at ~0.3-0.45 mm/day (1 cm per 28 d), catagen ~2-3 wk, telogen ~3 mo; 85-90% of scalp follicles in anagen; 50-100 shed per day. Length cap = rate x anagen (d: 25-105 cm); records past 5 m are outliers. Brows and lashes cycle in months and stay short (lash <= 12 mm).
5. Colour. Eumelanin sets black/brown/blond (black ~22, blond ~5 ug/mg, W); pheomelanin stays ~1 ug/mg except in red hair. Greying = loss of bulb melanocytes (onset ~34 y European, ~43 y African descent, W).
6. Motion. A stiff slender rod: E 3.1 GPa, d 80 um -> EI 6.2e-9 N m2 (d); gravity length (EI/(rho A g))^(1/3) = 4.6 cm (d). A free 5 cm strand sags only ~16% of its length (d), so curl, lift and clump hold for a few cm; flat (a/b 1.75) fibres bend ~3x easier across the flat face than across the edge (d).

## 1. Checkable descriptors (target +/- spread; detail in section 3)
D1 Scalp density /cm2: Caucasian 230+/-33 front, 226+/-20 vertex, 214+/-28 occiput (R1, n 23); African descent 160/149/148 (R1, n 44); Thai 154/163/160, temporoparietal 134 (R2, n 239). T1.
D2 FU density 96+/-38 (front), 95+/-44 (occ), 79+/-32 (temple) /cm2; hairs per FU 1 / 2 / 3 / 4 = 60 / 29 / 9 / 3% (R5). Mean root spacing from density: 0.66-0.79 mm (d).
D3 Front hairline height, glabella to mid hairline: F 6.2 cm, M 6.65 cm (range 2-9.5) (R12); trichion-glabella 63.6+/-7.9 mm M, 63.3+/-10.3 mm F (R13).
D4 Whorls per head: 1 = 85%, 2 = 12%, 3 = 2% (R14); clockwise ~70-84%, counter-clockwise 8-18% (R14, R15); 56% right of the midline, 30% left, 14% midline (R14 via Smith & Gong).
D5 Emergence angle: front edge 10-20 deg, posterior mid-scalp 45-60 deg, lower occiput 10-20 deg (R16, R17; W).
D6 Shaft diameter 80 +/- 5-7 um (Thai, R2); other cohorts 57-122 um by method (T4); section area 3857 / 4274 / 4804 um2 (Caucasian / African / Asian, R10).
D7 Growth 0.36 mm/day typical; Caucasian 396+/-55, Asian 411+/-53, African 256+/-44 to 280+/-50 um/day (R3, R10).
D8 Anagen share 85-90%, telogen 10-14% (R8, R36); shed 50-100/day.
D9 Cuticle tilt 2.5-3 deg; specular lobe FWHM 9-10 deg; eta 1.55 (R34, R32).
D10 Young's modulus 3.1+/-0.16 GPa; strain at break 47+/-4% (R22).
D11 Lashes: upper 90-160 in 5-6 rows, lower 75-80 in 3-4 rows; upper length 7-8 mm (max ~12); growth 0.12 mm/day (R29, R27).
D12 Brows: ~600 hairs both brows (R9, W). Body: ~25,000 hairs excluding head (R9, W).

## 2. Measuring on a 3-D mesh
- Density: cut 1 cm2 geodesic discs at the Thai sites (12, 24, 30 cm from glabella along the midline; temporoparietal 6 cm above the ear canal, R2) and count roots; compare to D1 by ancestry. Trichoscopy reads ~25% under biopsy (W), so test a +/-25% band.
- FU/clumps: cluster roots at ~0.3 mm; histogram of cluster size vs D2; nearest-neighbour root distance vs 0.66-1.0 mm.
- Hairline: landmarks glabella, trichion (midline hairline), frontotemporal point, temporal point; arc length glabella->trichion on the forehead surface; shape class by M-notch depth.
- Whorls: project root directions onto the scalp's tangent plane; whorl = zero of the field with index +1; count, signed curl (clockwise seen from above), position vs midline and vertex.
- Angle: angle between the first 0.5-1 mm of each strand and the tangent plane, binned by region (T3). Note the buried follicle differs from the emergent hair by 15-35 deg (R16).
- Shaft: tube section area, major/minor axes, a/b; equivalent diameter = sqrt(4A/pi). Curl: fit a helix to each strand (radius, pitch, torsion), arc length vs chord (curl index), waves per 5 cm.
- Length and growth: arc length per strand <= rate x days; clump bundle radius vs length.
- Optics: render a lit single fibre; check lobe offsets R +2a, TT -a, TRT -4a and widths (T7). Mass check: 6.6 mg/m at 80 um (d, density 1.32 g/cm3 assumed, not sourced).

## 3. Tables
### T1 Scalp density, counts, units
| Quantity | Value [n, population, method / source] | Ref | Conf |
|---|---|---|---|
| Density, Caucasian F/V/O | 230+/-33, 226+/-20, 214+/-28 /cm2 [23 (16F), 34.7 y, NYC, Folliscope 50x, hair parted] | R1 | 1 |
| Same, Hispanic | 174+/-32, 178+/-33, 169+/-31 [99 (71F), 40.2 y] | R1 | 1 |
| Same, African descent | 160+/-27, 149+/-23, 148+/-25 (0.66-0.70 x Caucasian, d) [44 (32F), 41.9 y; sex ns] | R1 | 1 |
| Thai F/V/TP/O | 154.3+/-12.8, 162.9+/-15.7, 133.7+/-14.6, 160.2+/-15.3; 60s ~6% below 20s [239 (79M), 37.9 y, Folliscope; sex ns] | R2 | 1 |
| Indian men F/O/T | 160+/-87, 156+/-98, 124+/-65 [120, 18-50 y, FotoFinder 20x/70x] | R5 | 1 |
| African phototrichogram | 190+/-40 (90-290); vertex highest; Caucasian ref 227+/-55 [38 (19F), 27+/-10 y, Africa-born] | R3 | 1 |
| Afro-textured, S. Africa | 139+/-34 mean [search snippet (Int J Dermatol 2025, DOI 10.1111/ijd.17633)] | - | W |
| Classic | 223 terminal /cm2 (175-300) [Barman 1965, 60x, via Robbins 2002] | R7 | W |
| Method bias | trichoscopy 163 vs biopsy 215 /cm2; 1.87 vs 2.24 hairs/FU (occiput, Chinese) [snippet, authors not seen] | - | W |
| Total scalp hairs | ~150,000 (Wolfram); blond 150k, brown 110k, black 100k, red 90k [150,000 / 223 = 673 cm2 of scalp (d)] | R8, R9 | W |
| FU density | 96+/-38 F, 95+/-44 O, 79+/-32 T /cm2; ~1/mm2 Caucasian, 0.6/mm2 Black; "100/cm2 average non-balding" | R5; R6, R19 | S |
| Hairs per FU | 1/2/3/4: 57/30/10/3% F, 59/28/9/3% O, 62/27/8/2% T; mean 1.55 (d); surgical 1.5-3.0, mean 2.0; Asian 1-2 | R5; R6 | S |
| Hair size classes | thin <30 um 8-10%, medium 30-50 um 16-23%, thick >50 um 69-75% | R5 | 1 |
| Anagen / telogen | ~90% / 10% (Wolfram); 85% / 10-14% / catagen 1-2% (Wikipedia) | R8, R36 | S |
| Season | anagen >90% in March; ~60 shed/day Aug-Sep (> 2x winter); beard +60% in July [14 men 18-39 y, 18 mo, Sheffield] | R26 | 1 |
### T2 Hairline and whorls
| Quantity | Value [n, population, method / source] | Ref | Conf |
|---|---|---|---|
| Glabella to mid hairline | F 6.2 cm (2-8.5), M 6.65 (2.7-9.5); no SD [456 Japanese 20-39 y (122M); tape] | R12 | 1 |
| Trichion-glabella | M 63.64+/-7.88, F 63.27+/-10.25 mm [297 Saudi 17-35 y; ruler +/-1 mm, Frankfurt plane] | R13 | 1 |
| Trichion-nasion | M 70.4, F 68.0 mm [825 Korean adults, Willis gauge (snippet)] | - | W |
| Designed male hairline | mid-frontal pt 7.9 cm above glabella (design 8 +/-1); frontotemporal pt 8 cm lateral of it, 8 cm above lateral canthus; temporal peak 5 cm from it toward canthus [431 men with hair loss, India; no SD] | R11 | W |
| Intertemporal / canthus-temple | 14.9 (9-23.5) F, 15.8 (12-23) M cm / 4.2 F, 4.4 M cm | R12 | 1 |
| Front shape | F: round 38.5, linear 36.1, M 18.2, triangular 7.2%; M: linear 45.9, M-shaped 42.6, round 10.7, triangular 0.8% | R12 | 1 |
| Temple shape | F: inv. triangle 20, inv. round 28, straight 25, convex 27%; M: 66 / 17 / 11 / 7% | R12 | 1 |
| Widow's peak | F 29.6%, M 32.8% | R12 | 1 |
| Whorl count | 1: 85.4%, 2: 12.4%, 3: 1.8% (of two-whorl heads, 66% have both whorls in one region); double 4.5% in healthy (Smith & Gong 1973 via R14) [501 Caucasian children, median 11 y] | R14 | 1 |
| Apical whorl, ancestry | single 95.5% Caucasian vs 10% African American; double 90% African American [Wunderlich & Heerema 1975, via R14] | R14 | W |
| Direction | clockwise 70.3%, counter-clockwise 15.2-15.7% (82/18% of single) (R14); 84/16% (Milano & De Palma 2013 via R14); CCW 8.4% (R15); range CCW 8-18% | R14, R15 | S |
| Side and site | 56% right, 30% left, 14% mid (Smith & Gong 1974 via R14); parietal commonest; frontal 1% (controls), 7.8% of 510 clinic patients | R14 | W |
### T3 Emergence angle (skin plane to hair)
| Region | Value [n, population, method / source] | Ref | Conf |
|---|---|---|---|
| Front hairline edge | 10-20 deg estimate; measured 17.4 (14.3-23.1) straight blade, 9.6 (8.6-11.3) curved blade, recipient slits [5 patients, macrophotography] | R17 | W |
| Frontotemporal / temple edge / mid-scalp | 10-15 / 5-10 / 30-45 deg [clinic page, no primary] | - | W |
| Posterior mid-scalp / lower occiput | 45-60 / 10-15 (or 15-20) deg; follicle vs hair angle differs 15-35 deg (Rassman via R16) [12 men] | R16 | W |
| Occiput | 6.4-35 deg (Rose via R17); graft angle <= 45 deg, more acute at temples | R17, R18 | W |
| Direction field | forward at front, downward-forward at temple then downward-back at temple apex, radial about the vertex transition point | R19 (no degrees) | 1 |
### T4 Shaft, section, curl
| Quantity | Value [n, population, method / source] | Ref | Conf |
|---|---|---|---|
| Diameter | Thai 80.1-81.1 (SD 4.5-6.9, n 239); Turkish 57.1+/-10.6 (n 120); Korean occiput 85.9+/-18.9 (AFM); Afro-ethnic standard sample 122+/-16 (OCT); Indian men 100+/-40 (n 120); review 60-80 | R2, R23, R24, R5, R8 | S (method spread 57-122) |
| Forensic ranges | African 60-90 flat; European/Mid-East 70-100 oval; Asian/Native American 90-120 round [via Wikipedia] | R36 | W |
| Range in a clinic | 60 um fine to 140 um coarse (area ratio 5.4x, d) | R6 | W |
| Section area | Caucasian 3857+/-132, African 4274+/-215, Asian 4804+/-159 um2 (eq. circle 70.1, 73.8, 78.2 um, d); Tunisian women 4643+/-817 [table of a review; R22] | R10, R22 | W |
| a/b | Asian ~1.25, European ~1.3-1.35, African descent ~1.75-1.83 (axes at same area: 87/70, 80/62, 98/56 um; I ratio 1.6, 1.7, 3.1, d). Review R10 words it opposite ("greatest ellipticity") - sign convention [snippets of secondary reviews] | R10 | W |
| Rendering eccentricity | e = minor/major 0.85-1.0 typical [Pixar patent Table 1] | R35 | W |
| Curl classes | European n 2138: straight 40.7, wavy 46.6, curly 12.7%; East/West Asian n 92: 46.7 / 41.3 / 12%; African n 39: wavy 5.1, curly 94.9% [DNA-phenotyping cohort via R21] | R21 | W |
| Curl radius | 0.6-16 cm (47% of 230 Japanese women curly); curl-meter ring 0.98 cm diameter | via R21; R20 | W |
| Classing | 8 types I-VIII from curve diameter, curl index, waves (1442 people, 18 countries); kappa 0.38-0.46 (8 groups) vs 0.61-0.73 (6) | R20 | 1 |
| Growth vs curl | 0.72+/-0.3 straightest vs 0.39+/-0.2 cm/month curliest (TrichoScan) [128 volunteers, UCT thesis abstract] | R20 | 1 |
| Follicle | African: curved, retrocurved at bulb; Caucasian: straight [abstract] | R25 | 1 |
| Cuticle | Asian: more layers and thicker than Caucasian/African; no numbers | via R10 | W |
### T5 Growth, cycle, length
| Quantity | Value [n, population, method / source] | Ref | Conf |
|---|---|---|---|
| Scalp rate | 1 cm per 28 d = 0.357 mm/d; range 0.6-3.36 cm/month; >60 um hairs 11.4 vs 20-30 um 7.6 mm/month [textbook via BioNumbers 109909; Wikipedia refs] | R36 | W |
| By ancestry (um/d) | Caucasian 396+/-55, African 256+/-44 (R3); Asian 411+/-53, Caucasian 367+/-56, African 280+/-50 (R10 table); African individuals 150-363 [38 African (R3); 2249 people, 24 groups, 3 scalp sites (R4, numbers unread)] | R3, R4, R10 | S for order |
| Telogen share | African 18+/-9%, Caucasian 14+/-11% (range 2-46%) | R3 | 1 |
| Phases | anagen 2-7 y (2-8), catagen 2-3 wk, telogen ~3 mo (Wikipedia); anagen 3-5 y, telogen 2-4 mo (Wolfram) | R36, R8 | W |
| Length cap (d) | 0.357 mm/d: 26 cm (2 y), 65 (5 y), 91 (7 y); 0.396: 101 cm (7 y) | | derived |
| Records | 5.627 m, Xie Qiuping 1973-2004 (Guinness, via Wikipedia) = 0.50 mm/d over 31 y (d), i.e. an anagen of decades | R36 | W |
### T6 Pigment and grey
| Quantity | Value [n, population, method / source] | Ref | Conf |
|---|---|---|---|
| Eumelanin / pheomelanin | black ~22.2, blond ~4.7 ug/mg; pheomelanin 0.85-0.99 ug/mg nearly constant black to blond; red ~equal [search snippet of Ito & Wakamatsu (paper not confirmed)] | R31 | W |
| Shares | black/brown > 95% eumelanin; blond and red ~1/3 pheomelanin; red "~67% pheomelanin" (Robbins 2012 via Wikipedia) - disagree with "~equal" | R36 | W |
| Hidden pheomelanin | benzothiazole type 11-17% of eumelanic hair by acid hydrolysis [Ito 2018 abstract] | R31 | 1 |
| Classes | black, dark brown, brown, light brown, blond, red; eumelanin falls in that order; MC1R predicts ratio | R31 abstract | 1 |
| Grey | onset ~34 y Caucasian, ~43 y African descent; premature <20 y Europe, <25 Asia, <30 Africa; white hair has no bulb melanocytes [onset from a 2025 Acta Dermosifiliogr review seen via search; thresholds via Wikipedia] | R36 | W |
### T7 Optics (Marschner family)
| Quantity | Value [n, population, method / source] | Ref | Conf |
|---|---|---|---|
| eta | 1.55 (pbrt typical; Blender default) | R32, R33 | W-S |
| Tilt alpha | pbrt typical 2 (range 2-4) deg; goniophotometry 2.5 (Stamm) to 3 deg; peak at 36 deg for 40 deg incidence [brown Caucasian female hair] | R32, R34 | 1 |
| Lobe shifts | R +2a, TT -a, TRT -4a: a=2 -> +4, -2, -8 deg; a=2.5-3 -> R +5..+6, TRT -10..-12 deg (d); sign convention differs between papers [pbrt] | R32 | S |
| Lobe widths | sd_TT = sd_R/2, sd_TRT = 2 sd_R; pbrt "typical" beta_m 0.25 -> sd_R 13.3 deg (d); beta_m 0.1 -> 4.6 deg, "too shiny"; 0.7 "flat" | R32 | S |
| Measured width | specular peak FWHM 9-10 deg -> sd 3.8-4.3 deg (d) = beta_m ~0.08-0.1: ~3x narrower than pbrt typical (bundle, wear, section shape?) | R34 | 1 |
| Azimuthal | beta_n 0.1-0.3 in examples; logistic scale s = sqrt(pi)/8 (0.265 bn + 1.194 bn^2 + 5.372 bn^22) | R32 | W |
| pbrt sigma_a (RGB per hair diameter) | black 3.35 5.58 10.96; brown 0.84 1.39 2.74; blond 0.06 0.10 0.20 | R32 | W |
| pbrt pigment basis | eumelanin 0.419 0.697 1.37; pheomelanin 0.187 0.4 1.05; black ce = 8; fig values imply brown 2.0, blond 0.14 (d) but text says 1.3, 0.3 (inconsistent) | R32 | W |
| Blender (Chiang 2016) | eumelanin 0.506 0.841 1.653; pheomelanin 0.343 0.733 1.924; qty = -ln(1 - melanin); presets white 0, blond 0.25, reddish 0.5, brown 0.75, black 1.0 -> qty 0, 0.29, 0.69, 1.39, 9.2 (d) | R33 | S |
| Cuticle | 0.5 um x 50 um cells; hair 4-8 layers of 350-500 nm (ellipsometry snippet); lash layers 8.0+/-1.2 Asian vs 6.5+/-1.1 Caucasian | R8, R28 | W |
### T8 Mechanics and motion
| Quantity | Value [n, population, method / source] | Ref | Conf |
|---|---|---|---|
| Young's modulus | 3.1+/-0.16 GPa; stress at break 201+/-11.3 MPa; strain 47.3+/-3.6%; area 4643+/-817 um2; humidity and n not in abstract [Tunisian women, MTT675 tester] | R22 | 1 |
| Strength vs size | break force higher for d >= 51 um; strain vs d r = 0.361; no E reported [120 anagen hairs, 50 N cell] | R23 | 1 |
| Curly fibres | toe-region stress adds to strength, ~0 in straight [Cloete 2020 abstract] | R21 | W |
| Composition | protein 85-91%, water 4-13%, fat ~2.3%, ash 0.23-0.9% (fresh weight) | ICRP 23 via BioNumbers 110309 (R9 family) | W |
| EI, round fibre, E 3.1 GPa | 60 um 2.0e-9; 80 um 6.2e-9; 100 um 1.5e-8 N m2 (d) | | derived |
| Mass per length | 3.7 / 6.6 / 10.4 mg/m at 60 / 80 / 100 um (d; rho 1320 kg/m3 assumed) | | derived |
| Gravity length | 3.8 / 4.6 / 5.3 cm (d); tip sag/L for 2 / 5 / 10 cm strand 0.01 / 0.16 / (>0.2, nonlinear) (d) | | derived |
### T9 Eyebrow and T10 Eyelash
| Quantity | Value [n, population, method / source] | Ref | Conf |
|---|---|---|---|
| Brow count | ~600 both brows (~300 each, d) [Flindt 2006] | R9 | W |
| Brow cycle | anagen 4-7 mo, catagen 3-4 wk, telogen ~9 mo (Wikipedia) vs anagen ~70 d (review snippet) [conflict] | R36 | W |
| Brow direction / shape | no cited angles. Classical rules, recalled, unverified: medial end over the nasal-ala vertical, tail on the ala-lateral-canthus line, peak over the lateral limbus to lateral third (check Gunter & Antrobus 1997); 10% of 200 Caucasian children had medial brow outflare | R14 | W |
| Lash count | upper 90-160 (5-6 rows), lower 75-80 (3-4 rows); upper 150 Asian vs 170 Caucasian; all lids 420 (d check: 2 x (105+80) ~ 370) | R29 (cites Montagna & Ford 1969, Liotet 1977, Na 2006); R9 | W |
| Lash length | upper 7-8 mm typical (3-10), lower 5-6 mm, rarely > 12 mm; ~1/3 of eye width (24.2 mm -> 8.1 mm, d) | R27, R29, R30, Wikipedia | W |
| Lash diameter / curl | 71.7 Asian vs 61.0 um Caucasian; curl-up and lift-up angles lower in Asians (degrees not in abstract) [20 Asian + 10 Caucasian F, 4661 lashes] | R28 | 1 |
| Lash cycle | rate 0.12+/-0.05 mm/d; anagen 34+/-9 d; cycle 90+/-5 d (29 Caucasian F 26-60 y, 4 followed 9 mo, 17 biopsies); reviews 0.12-0.14 mm/d, anagen 4-10 wk, cycle 4-11 mo; Asian anagen share 17.8+/-3.3% (n 5); regrow 7-8 wk | R27, R28, R29 | S |
### T11 Body hair
| Quantity | Value [n, population, method / source] | Ref | Conf |
|---|---|---|---|
| Number | ~25,000 body hairs excluding head [Flindt 2006] | R9 | W |
| Density by site | only order known: forehead densest, calf least dense with largest orifices; follicles take > 0.1% of skin surface [Otberg 2004 abstract (7 sites; numbers unread)] | R37 | W |
| Growth | axilla ~0.4, pubis ~0.3 mm/d (forensic studies via a 2026 review snippet); arm hair record 18.4 cm (Guinness 2024) | R36 | W |
| Finger-joint hair | Andamanese 0, Inuit 1, African American 16-28, Japanese 45, Europeans 60-80% | R36 (Hindley & Damon 1973) | W |

## 4. Not found
- Body hair density by region and sex; per-site growth rates (Saitoh 1970 and Otberg 2004 numbers unreadable); vellus vs terminal counts.
- Eyebrow hair length, diameter, angle field, brow-shape coordinates; whorl swirl geometry and position in cm; crown and vertex emergence angles from peer-reviewed measurement.
- De la Mettrie curve diameter and curl index per type; curl radius by ancestry; Lasisi 2016 and Loussouarn 2016 numbers; primary ellipticity values (Franbourg 2003).
- Marschner 2003 fitted numbers (PDF unreadable); measured melanin per colour in a primary paper; hair bending test (EI), torsion modulus, damping, fibre friction, clump cohesion, wet vs dry modulus.

## 5. References
R1 Birnbaum MR et al. Skin Appendage Disord 2018;4:304, 10.1159/000485522. R2 Leerunyakul K, Suchonwanit P. Biomed Res Int 2020:2476890, 10.1155/2020/2476890. R3 Loussouarn G. Br J Dermatol 2001;145:294, PMID 11531795. R4 Loussouarn G et al. Eur J Dermatol 2016;26:144, 10.1684/ejd.2015.2726 (abstract only).
R5 Asfiya A et al. Indian Dermatol Online J 2024;16:81, 10.4103/idoj.idoj_201_24. R6 Bernstein RM. Hair Transplant Forum Int 1998;8(1):27. R7 Barman JM et al. J Invest Dermatol 1965;44:233 (via BioNumbers 116431, Robbins 2002). R8 Wolfram LJ. J Am Acad Dermatol 2003;48:S106, PMID 12789162 (via BioNumbers 114255-114259).
R9 Flindt R. Amazing Numbers in Biology, Springer 2006 (via BioNumbers 101509-101512). R10 Leerunyakul K, Suchonwanit P. Clin Cosmet Investig Dermatol 2020;13:309, 10.2147/CCID.S247390. R11 Garg AK, Garg S. J Cutan Aesthet Surg 2017;10:195, 10.4103/JCAS.JCAS_51_17.
R12 Kashiyama K et al. Plast Reconstr Surg Glob Open 2021;9:e3751, 10.1097/GOX.0000000000003751. R13 Bakri M et al. Open Dent J 2026;20:e18742106428778, 10.2174/0118742106428778260327080856. R14 Sechi A et al. Int J Trichology 2020;12:56, 10.4103/ijt.ijt_25_20.
R15 Klar AJS. Genetics 2003;165:269, 10.1093/genetics/165.1.269. R16 Gharwade CR. Indian J Plast Surg 2016;49:390, 10.4103/0970-0358.197227. R17 Ahmad M. Int J Trichology 2018;10:68, 10.4103/ijt.ijt_84_17. R18 Marwah MK, Mysore V. J Cutan Aesthet Surg 2018;11:202, 10.4103/JCAS.JCAS_124_18.
R19 Bernstein RM. Follicular Unit Transplantation, 2005 web chapter, bernsteinmedical.com/research/follicular-unit-transplantation-2005/3/. R20 Mkentane K et al. PLoS One 2017;12:e0172834, 10.1371/journal.pone.0172834; Mkentane K, UCT PhD thesis 2016 (abstract).
R21 Cloete E, Khumalo NP, Ngoepe MN. Proc R Soc A 2019;475:20190516, 10.1098/rspa.2019.0516 (cites Pospiech 2018); Cloete et al. J Invest Dermatol 2020;140:113 (abstract). R22 Sayahi E et al. Int J Cosmet Sci 2016;38:470, 10.1111/ics.12313. R23 Erik B et al. Skin Res Technol 2008;14:147, 10.1111/j.1600-0846.2007.00268.x.
R24 Jeong KH et al. Skin Res Technol 2011;17:63; Velasco MV et al. Skin Res Technol 2009;15:440 (both via BioNumbers 106857-106859). R25 Thibaut S et al. Br J Dermatol 2005;152:632; Franbourg A et al. J Am Acad Dermatol 2003;48:S115, PMID 12789163 (abstracts). R26 Randall VA, Ebling FJ. Br J Dermatol 1991;124:146, 10.1111/j.1365-2133.1991.tb00423.x.
R27 Thibaut S et al. Br J Dermatol 2010;162:304, 10.1111/j.1365-2133.2009.09487.x. R28 Na JI et al. Br J Dermatol 2006;155:1170, 10.1111/j.1365-2133.2006.07495.x. R29 Aumond S, Bitton E. J Optom 2018;11:211, 10.1016/j.optom.2018.05.003. R30 Amador GJ et al. J R Soc Interface 2015;12:20141294, 10.1098/rsif.2014.1294.
R31 Ito S, Wakamatsu K. J Eur Acad Dermatol Venereol 2011;25:1369, 10.1111/j.1468-3083.2011.04278.x (abstract); Ito S et al. Pigment Cell Melanoma Res 2018;31:393, 10.1111/pcmr.12673. R32 Pharr M, Jakob W, Humphreys G. Physically Based Rendering 4e, sec 9.9, pbr-book.org/4ed/Reflection_Models/Scattering_from_Hair.
R33 Blender 4.4 manual, Principled Hair BSDF (after Chiang M et al. Comput Graph Forum 2016;35(2)). R34 Wortmann et al. (authors per search summary, not shown on the page), J Cosmet Sci 2003;54(3):304 ff, 'Analyzing the laser-light reflection from human hair fibers. I' (goniophotometry). R35 US patent 9,905,045 B1 (statistical hair scattering model, Table 1). R36 Wikipedia: Hair, Hair follicle, Body hair, Eyelash, Eyebrow, Human hair color (read 2026-10-19; secondary).
R37 Otberg N et al. J Invest Dermatol 2004;122:14, 10.1046/j.0022-202x.2003.22110.x (abstract). Unread: Marschner SR et al. ACM TOG 2003;22(3); d'Eon E et al. Comput Graph Forum 2011 (abstracts only); Lasisi T et al. Am J Phys Anthropol 2016;160:341; Koch SL et al. J Struct Biol 2019;205:60 (no numbers in abstracts).
Files cached by the fetch tool (not by me), in C:\Users\<you>\.claude\projects\<project-id>\4e1e86a0-3fb8-4e95-be51-ae522fcc2a80\tool-results\: webfetch-1792470577489-f5yay0.pdf, -1792470782993-5p2wxc.pdf, -1792470808394-ml3ixf.pdf, -1792471509750-0hd4ou.pdf, -1792471646490-e1udou.pdf.
