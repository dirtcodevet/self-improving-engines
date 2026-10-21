# Head and face (skin surface, soft-tissue thickness, expression, ageing): cited numbers for a mesh check

Compiled 2026-10-19 from abstracts and open full texts read through the Europe PMC full-text API (PMC web pages were behind a browser check and were not bypassed), plus search-result text. Nothing was saved. Eyeball, mouth interior and hair are other researchers' topics. Adults unless stated.
Confidence: strong = several studies agree or pooled n in the thousands; single = one study; weak = abstract-only, second-hand, adolescent, n<30 or definition unclear. "derived" = my arithmetic on cited numbers. Landmarks (Farkas): tr trichion, g glabella, n nasion, sn subnasale, prn pronasale, al alare, ac alar curvature, sto stomion, ls/li labiale sup/inf, sl sublabiale, gn/me gnathion/menton, en/ex endo/exocanthion, ch cheilion, ft frontotemporale, zy zygion, go gonion.

## 0. In my words
1. Build. The face surface is a skull-shaped frame plus a soft blanket. Blanket thickness (pooled, F1) runs 3 mm over rhinion, 5.5-6 at glabella and nasion, 7-7.5 at mid-supraorbital, zygion and menton, 11-13.5 at the lips, chin point and chin crease, 22-26 over the molar cheek. Skin proper is thin: 0.57 mm upper eyelid to 1.9 mm nose tip (F8); epidermis 30-63 um (F9). Cartilage (nose tip, ear) frames the soft parts; mimetic muscles insert into dermis, so expressions are skin slide plus fat shear, not rigid motion. Tissue stiffness by region is in soft_tissue_mechanics.md (R36-R41).
   Behaviour. Voluntary expressions move surface points 8-18 mm (mouth corner in a wide smile 16-18, brow 10, lid 11.5, nose wing 9-10, F11, F12). Sex: men are ~4-8% larger in widths and lengths, soft-tissue thickness differs <1 mm pooled (F1). Ancestry: nose width, lip heights and the nasofrontal/nasolabial angles differ most (F3, F5). Age 25-45: slow drift only (brow tail down ~2.5 mm, ear +4 mm, nose slightly longer, forehead skin thins in the 40s); large changes start after 50 (F13, F20).
2. Descriptors a mesh can be checked against (targets in sections 1-10): D1 thirds ratio tr-n : n-sn : sn-me (1 : 0.82 : 1.08 M, 1 : 0.80 : 1.02 F, derived); D2 widths en-en 33/32, al-al 35/31, ch-ch 54/50, zy-zy 139/130 mm (M/F); D3 nose angles (nasolabial 100-104 deg, nasofrontal 130-141 deg by ancestry); D4 lip protrusion to the sn-pg' line (upper 3.0+/-1.0, lower 2.0+/-1.0 mm); D5 per-landmark soft-tissue thickness (24 values, F1); D6 skin thickness map (F8); D7 ear height ~63 mm, width 50-60% of height, helix-to-head 6-20 mm, helix-mastoid angle 20-30 deg; D8 gonial angle ~123+/-8 deg; D9 men's inferior brow border ~11 mm above the lateral canthus and pupil level; D10 expression ranges (section 11); D11 age drift (section 10); D12 head circumference/breadth/length.
3. Measuring on a mesh. Place 3-D landmarks by curvature (pronasale = max protrusion in the midline profile; subnasale = nasal-floor/lip junction; alare = max lateral nostril wing; cheilion; zygion needs the arch; go and ft are bony and must be taken from a skull proxy). Linear: Euclidean (Farkas uses calipers, so 3-5 mm of tape/contour length differs from straight chord). Angles: sagittal midline section (nasolabial = columella-sn-ls; nasofrontal = glabella-nasion-prn; Burstone convexity G'-Sn-Pg'). Protrusion: perpendicular distance to a reference line (Sn-Pg'). Thickness: ray from each surface landmark along the normal to the inner skull mesh (needs the skull inside the head; report mean/SD per T-table landmark). Curvature: nose tip radius, vermilion border, lid/brow arch. Expression: displacement modulus of a landmark between rest and peak mesh after rigid registration on the cranium. Symmetry: treat a left-right Procrustes modulus >6 mm or an index >10% as a flagged defect (F11).

## 1. Facial proportions, North American White norms (Farkas data as quoted in F3; mm)
| Item | Male | Female | n, method | Ref | Conf |
|---|---|---|---|---|---|
| tr-g forehead I (derived from F3 differences) | 57.0 | 52.7 | NAW 109 M / 200 F, caliper | F3 | single, secondary |
| tr-n forehead II | 67.1 +/-7.5 | 63.0 +/-6.0 | same (direct) | F3 | single |
| g-sn midface (derived) | 67.2 | 63.1 | same | F3 | single |
| n-sn nasal height | 54.8 +/-3.3 | 50.6 +/-3.1 | same (direct) | F3 | single |
| sn-me lower face | 72.6 +/-4.5 | 64.3 +/-4.0 | same (direct) | F3 | single |
| en-en intercanthal | 33.3 +/-2.7 | 31.8 +/-2.3 | same | F3 | single |
| ex-en eye fissure | 31.3 +/-1.3 | 30.7 +/-1.2 | same | F3 | single |
| ex-ex biocular | 91.2 +/-3.0 | 87.8 +/-3.2 | same | F3 | single |
| al-al nasal width | 34.9 +/-2.1 | 31.4 +/-2.0 | same | F3 | single |
| ch-ch mouth width | 54.5 +/-3.0 | 50.2 +/-3.5 | same | F3 | single |
| ft-ft bitemporal; zy-zy bizygomatic; go-go bigonial (all derived) | 115.9; 139.1; 105.6 | 111.5; 130.0; 94.5 | same, soft-tissue landmarks | F3 | single |
Ratios (derived): thirds tr-n : n-sn : sn-me = 1 : 0.82 : 1.08 (M), 1 : 0.80 : 1.02 (F), so the "equal thirds" canon fails in the middle third. Fifths: ex-ex/ex-en = 2.91 M, 2.86 F (canon 3); en-en/ex-en 1.06 / 1.04; al-al/en-en 1.05 / 0.99; ch-ch/al-al 1.56 / 1.60 (canon 1.5); al-al/zy-zy 0.251 / 0.242 (canon 0.25); go-go/zy-zy 0.76 / 0.73; ex-ex/zy-zy 0.66 / 0.68; al-al/n-sn 0.64 / 0.62. In young US Caucasians the most valid neoclassical canons (their numbers 5 and 8) held in only 40% and 37% of subjects (Farkas and Kolar, via F26, weak). European Caucasians matched North American in 99.7% of subjects for forehead height, mouth width, ear height (Farkas 2005, n=1470, 18-30 y, via F26/F4, weak). Original Farkas 1994 tables, head length g-op, head width eu-eu and circumference: not read.

## 2. Head and face size by sex and ancestry (mm)
| Item | Male | Female | n, population, method | Ref | Conf |
|---|---|---|---|---|---|
| Head circumference | 572.7 (derived) / 588.2 +/-17.6 | 556.1 / 560.0 +/-18.9 | US NIOSH workers 18-29 y (n=551 M, 191 F) back-calculated from ratios / Taiwan 21-30 y (101 M, 105 F), traditional anthropometry | F6 | single, derived |
| Head breadth; length | 152.1; 196.2 (US) / 160.5 +/-7.1; 186.4 +/-7.2 (Taiwan) | 146.7; 187.6 / 154.6 +/-7.1; 176.0 +/-6.4 | same; cephalic index 77.5 M, 78.2 F (US) vs 86.1, 87.8 (Taiwan), derived | F6 | single |
| Bizygomatic breadth | 142.3 / 128.2 +/-6.6 | 135.1 / 122.7 +/-7.0 | same (caliper; Farkas soft-tissue zy-zy is 139.1 / 130.0, definitions differ) | F6 | single |
| Min frontal; max frontal breadth | 105.3; 111.8 (US) / 111.4; 124.6 (Tw) | 103.9; 108.2 / 107.0; 118.2 | same | F6 | single |
| Menton-sellion; bigonial breadth | 120.9; 119.0 (US) / 115.8; 114.0 (Tw) | 112.9; 108.8 / 107.8; 105.5 | same; caliper bigonial is ~13 mm above Farkas go-go 105.6 / 94.5: do not mix | F6, F3 | single |
| Interpupillary; lip length | 63.8; 49.9 (US) / 61.6; 48.0 (Tw) | 61.9; 46.7 / 58.8; 44.9 | same | F6 | single |
| Nose breadth; nasal root breadth; sn-sellion; protrusion | 36.4; 16.8; 50.7; 21.1 (US) / 36.5; 19.3; 48.7; 19.8 (Tw) | 33.1; 16.5; 47.4; 19.8 / 33.6; 17.6; 45.8; 18.4 | same | F6 | single |
Sex is significant for 19 of 24 NIOSH variables (men larger in all the means above); African-Americans have shorter, wider, shallower noses; Hispanic workers larger in 14 features with shorter nose protrusion/head length; subjects >=45 y differ from 18-29 y in 19 values (abstract only, no numbers, F6b). Kenyan men vs NAW men: nose width 43.2 vs 34.9, biocular 98.2 vs 91.2, upper lip 25.5 vs 22.3, lower face 76.4 vs 72.6, bizygomatic 133.8 vs 139.1 (derived); African-American (n=50) close to Kenyan except intercanthal 35.8 and nasolabial angle 71 (F3, single). Max mouth opening (caliper, n=400, Saudi, 18-60+ y): 45.7 +/-6.9 mm; M 47.9 +/-6.7, F 44.3 +/-6.7; no age effect (F24, single).

## 3. Nose
| Item | Value | n, population, method | Ref | Conf |
|---|---|---|---|---|
| Nasolabial angle (columella-sn-ls) | Caucasian M 100.1 (CrI 94.0-105.8), F 103.3 (96.9-109.3); Asian 94.7 / 94.2; African 87.5 / 85.9 | Bayesian meta-analysis, 38 photogrammetric studies; Caucasian 360 M / 628 F | F5 | strong |
| Same, other methods | NAW 99.8 +/-11.8 M, 104.2 +/-9.8 F (n=50 each); Burstone Caucasian 102 +/-8; Taiwan 3-D 99.2 +/-8.3; Kenyan 85.5 / 85.2; adolescent 3-D Caucasian 112.9 +/-8.3 | direct measurement / 2-D cephalometry / 3-D CBCT, n=60 / photos | F3, F7, F25 | single each |
| Nasofrontal angle | Caucasian M 137.9 (133.6-142.0), F 140.6 (134.6-146.8); Asian 133.7 / 139.3; African 129.7 / 132.2. NAW 130.3 +/-7.4 / 134.3 +/-7.0 | F5 meta-analysis; F3 direct | F5, F3 | strong |
| Nasal tip angle | Caucasian M 75.7, F 77.6 (CrI +/-6); African 78.8 / 79.4 | n=191 M / 334 F Caucasian, photogrammetric | F5 | single |
| Nasal tip protrusion | 12.6 (M), 15.3 (F) photogrammetric Caucasian; 21.1 M / 19.8 F (NIOSH nose protrusion, derived); 19.9 +/-1.7 (3-D, age ~16 y, Caucasian) | n=102 / 429 (F5); 551 M, 191 F (F6); 21 (F25) | F5, F6, F25 | disagree: 12-21 mm, definition-dependent |
| Nasal height n-sn; width al-al | see section 1; 3-D adolescent controls: nasal length 42.2 +/-2.8, alar width 31.2 +/-2.5, tip width 17.7 +/-1.6, columella height 9.9 +/-0.9, width 7.2 +/-1.0, nostril 11.5 x 10.3 | n=21, 15.8 y | F25 | weak |
| Nasal bridge length (female Caucasian) | 42.2 (34.7-49.7) | 209 women, photogrammetric meta-analysis | F5 | weak |
| Alar curvature width ac-ac | M 32.8, F 30.5 (derived) | NAW, 109 M / 200 F | F3 | single |
| Skin / envelope | tip 1.91, ala 1.74, dorsum 1.28, lateral surface 1.16 mm (see section 9); tip envelope 3.7-4.0 mm (soft_tissue_mechanics R39) | | F8 | single |
| Bone-to-skin thickness | rhinion 3.0, mid-nasal 4.5, nasion 6.0, subspinale 13.5 mm (section 8) | | F1 | strong |
Goode ratio (tip projection / nasal length 0.55-0.60), columellar show, supratip break: no source read.

## 4. Ear
| Item | Value | n, population, method | Ref | Conf |
|---|---|---|---|---|
| Total ear height | 6.30 cm (both sexes, both ears); men +6.5% pinna height vs women; lobule height 1.88 cm, width 1.96 cm (sex-equal) | 123 volunteers, 89 F 19-65 y, 34 M 18-61 y, caliper | F16 | single |
| Ear length and width | length 55-70 mm, width 30-45 mm (width 50-60% of length) | surgical reference ranges, review | F17 | weak |
| Position | auricle ~ one ear length (55-70 mm) behind the lateral orbital margin; ear axis about parallel to the nasal bridge | review | F17 | weak |
| Protrusion | helix-to-head distance 6-20 mm adults (upper, middle, tail; Wodak); mastoid-helix angle <=30 deg, 20-30 deg (Vargas), 90 deg in severe protrusion; lobule-head >18-20 mm = prominent; ~5% of Germans have prominent ears | review of anthropometric studies | F17 | weak |
| Ear dimensions vs sex | all dimensions larger in men (p<0.001); L-R symmetry 92-96% | 497 M + 346 F, 4-73 y, electromagnetic digitizer (values in tables, not in abstract) | F9b | single |
| Helix/antihelix/concha geometry | antihelical fold absent or flat in most protruding ears; conchal bowl hyperplasia; numbers (conchal depth, fold angle): not found | | F17 | gap |

## 5. Cheek, zygoma, jaw, chin
| Item | Value | n, population, method | Ref | Conf |
|---|---|---|---|---|
| Soft tissue over cheek | zygion 7.5 +/-3.0, mid-infraorbital 6.5, supra/infra canine 10.5 / 11.0, alar curvature 10, supra/infra second molar 26.0 / 22.0 (+/-7), mid-ramus 19.5, gonion 12.5 +/-6.0, mid-mandibular body 11.0 | pooled, 139 studies (section 8) | F1 | strong |
| Cheek contour (most convex point below the orbit, relative to the eyelid plumb line) | 2.1 +/-1.0 (M), 2.2 +/-1.3 (F) mm | 60 Taiwanese adults with balanced profile, CBCT 3-D | F7 | weak |
| Malar fat pad thickness, malar projection from a facial plane, zygomatic arch prominence in mm | not found (midfacial fat 14.7 mm in 25 thin women is in soft_tissue_mechanics.md, weak) | | | gap |
| Gonial angle (bone) | 122.2 +/-8.2 (R), 124.1 +/-8.2 (L) deg; ramus height 69.0 +/-8.3 mm; female angle larger, male ramus and bigonial width larger | 220 dentate adults 19-69 y, panoramic radiographs | F22 | single |
| Mandible, 3-D | Co-Go 65.9 +/-6.5 M, 57.7 +/-3.1 F; Go-Pg 92.1 / 88.9 (Burstone Caucasian 83.7 / 74.3); mandibular plane angle 23.9 / 25.3 (Caucasian 23.0 / 24.2) | 60 Taiwanese Chinese, CBCT | F7 | single |
| Chin projection (soft tissue, G-Pg' horizontal) | Caucasian 0 +/-3 mm; Taiwan 2.1 +/-3.6; facial convexity G'-Sn-Pg' 12 +/-4 deg (Taiwan 11.4 +/-3.1); lower-face throat angle 100 +/-7 (Taiwan 100.7 +/-5.9); mentolabial sulcus depth 4.0 +/-2.0 (3.8 +/-0.8) | Burstone norms, Caucasian n=40 (14 M, 16 F in bone set), via F7 | F7 | single |
| Labiomental angle | NAW 113.5 +/-20.7 M, 121.4 +/-14.4 F (direct); Caucasian 128.6 M / 132.0 F (meta-analysis); mentocervical 94.3 M / 91.1 F | method-dependent, 15 deg gap | F3, F5 | disagree |
| Chin height | fml-me 33.1 (M), sl-gn 27.0 (F) (derived, different landmark pairs) | NAW via F3 | F3 | weak |

## 6. Eyebrow (relative to the orbital rim)
| Item | Value | n, population, method | Ref | Conf |
|---|---|---|---|---|
| Men, lower brow border above lateral canthus; above pupil centre; upper border above pupil | 11.2; 11.2; 19.8 mm, so brow hair band ~8.7 mm thick (derived) | 222 men 10-86 y (mean 46.8), 444 brows | F18 | single |
| Age effect, men | none in mean brow position; deep-set eyes give lower brows (r 0.43) | same | F18 | single |
| Lateral brow descent, both sexes | plumb line (tail to canthal horizontal) -2.5 mm per 20 y; nasal ala-to-lateral-brow -3 mm per 20 y; mid-to-tail angle -3 deg per 20 y (so ~ -2.5 mm and -3 deg over 25-45, derived) | 1024 adults, 1944 eyes, mixed ethnicity | F20 | single; conflicts F18 for men |
| Shape / position | women: lower border just below the rim at the medial canthus, at the rim at mid-pupil, several mm above the rim at the lateral canthus; men lower, flatter, lower tail; peak just medial to the lateral canthus in both; brow mobility larger medially in men, at the tail in women | 40 adults, photographs, 6 positions (mm not in abstract) | F19 | single |
| Bone under the brow | mid-supraorbital soft tissue 7.0 +/-2.0 mm; supraorbital skin 1.36 mm | pooled 8,966 / 45 women | F1, F8 | strong / single |

## 7. Lips from outside (mm; derived values from F3 differences)
| Item | Male | Female | Ref | Conf |
|---|---|---|---|---|
| Upper lip sn-sto | 22.3 +/-2.1 | 20.1 +/-2.0 | F3 | single |
| Lower lip sto-sl | 19.7 +/-2.1 | 17.8 +/-4.7 | F3 | single |
| Philtrum sn-ls (derived) | 15.9 | 13.8 | F3 | single |
| Upper / lower vermilion height (derived) | 7.8 / 9.3 | 8.7 / 9.4 | F3 | weak |
| Mouth width ch-ch | 54.5 +/-3.0 | 50.2 +/-3.5 | F3 | single |
| Upper lip height, photogrammetric Caucasian | 21.6 (16.9-26.3) | 19.7 (18.7-20.6) | F5 | strong |
| Protrusion to the Sn-Pg' line, upper / lower | 3.0 +/-1.0 / 2.0 +/-1.0 (Caucasian, sexes pooled) | Taiwan 6.4 / 4.5 M, 5.5 / 3.8 F | F7 | single |
| Sn-Stm / Stm-Me' ratio; interlabial gap; incisor show | 0.5; 2 +/-2; 2 +/-2 mm (Taiwan 0.50; 1.2; 1.3) | | F7 | single |
| Lip skin | vermilion 1.06 mm, philtrum 1.62, oral commissure 1.23; epidermis max at the upper lip 62.6 um | | F8, F9 | single |
| Soft tissue over teeth | upper lip margin 12.0 +/-3.0, lower lip margin 13.5 +/-3.0, mid-philtrum 11.5, labiomental 11.0 mm | | F1 | strong |

## 8. Soft-tissue thickness over the skull, adults >=18 y (F1, pooled 2023 T-Table; mean in mm rounded to 0.5, s = SD of studies reporting SD)
Method: skin surface to bone at skull landmarks; 139 studies, >220,000 measurements, >19,500 adults; needle, cephalogram, ultrasound, CT, CBCT, MRI mixed. Sex differences <1 mm (men slightly thicker at midline landmarks, women at some bilateral ones); no clear ancestry clustering (F2, abstract text via search only, weak). Names per T-Table convention, not all re-verified here.
- Midline: opisthocranion 6.0 (s 2.0); vertex 5.0 (1.5); glabella 5.5 (1.0); nasion 6.0 (1.5); mid-nasal 4.5 (1.5); rhinion 3.0 (1.0); subspinale 13.5 (3.5); mid-philtrum 11.5 (2.5); upper-lip margin (pr-ls) 12.0 (3.0); lower-lip margin (id-li) 13.5 (3.0); labiomental sm 11.0 (2.0); pogonion 11.0 (2.5); gnathion 7.5 (2.5); menton 7.0 (2.5). n 2,272-17,075 per landmark.
- Bilateral: mid-supraorbital 7.0 (2.0); mid-infraorbital 6.5 (3.0); ac 10.0 (3.0); gonion 12.5 (6.0); zygion 7.5 (3.0); supra-canine 10.5 (2.5); infra-canine 11.0 (2.5); supra-M2 26.0 (7.0); infra-M2 22.0 (6.5); mid-ramus 19.5 (5.0); mid-mandibular body 11.0 (4.0). n 3,417-10,399.
- Use as target: a mean-thickness face is off by 3.5 mm per landmark on average (standard error of the estimate 1.0 at rhinion to 7.7 supra-M2, n=1,460 known faces). Method matters: cephalograms give the largest midline values, CT the largest bilateral; ultrasound compresses; supine posture thins the midline and thickens the sides. Since 2008: +3 mm infra-M2, +2.5 gonion, +2 mid-ramus, +1.5 zygion.

## 9. Skin thickness by region (mm)
| Item | Value | n, method | Ref | Conf |
|---|---|---|---|---|
| Ultrasound skin thickness, median (IQR) | nasal tip 1.91 (0.46); nasal ala 1.74; upper nasolabial fold 1.64; philtrum 1.62; mental 1.61; superolateral forehead 1.52; glabella 1.50; lateral forehead 1.49; upper forehead 1.48; infraorbital 1.45; buccal 1.37; supraorbital 1.36; zygomatic 1.30; nasal dorsum 1.28; tear trough 1.24; oral commissure 1.23; mandibular angle 1.20; lateral nose 1.16; temporal 1.13; upper vermilion 1.06; lower eyelid 0.81; upper eyelid 0.57 | 45 women 22-73 y, 38 sites, 75 MHz, >8,000 measurements | F8 | single |
| Histology | dermis thickest lower nasal sidewall 1.97, thinnest upper medial eyelid 0.76; epidermis thickest upper lip 63 um, thinnest posterior auricular 30 um (39 sites) | 10 cadaver heads | F9 | single |
| Relative thickness | nasal tip 3.30 x, brow/forehead 2.8 x upper eyelid; nasal dorsum 0.73, philtrum 0.83 mm (as quoted in F8) | 3 cadavers, 15 sites | F10 | weak |
Skin plus subcutis over nose tip and forehead layers are in soft_tissue_mechanics.md (R38, R39).

## 10. Age changes, roughly 25-45 y (cross-sectional unless stated)
| Item | Value | n, method | Ref | Conf |
|---|---|---|---|---|
| Whole-face shape, 3-D | first signs 20-30 y; men and women follow one pattern to ~50 y (flatter face, sagging soft tissue, deeper nasolabial folds, smaller visible eyes, thinner lips, longer nose and ears, "broken" jawline); female rate ~2 x male before 50, up to 3 x at 50-60 y; no mm in the paper | 88 Croatians 26-90 y (32 M, 56 F), 585 landmarks | F13 | single |
| Lateral brow | -2.5 mm and -3 deg per 20 y (section 6) | 1024 adults | F20 | single |
| Ear length | +0.22 mm/y, 30-93 y (derived +4.4 mm over 20 y); in F16 only the lobule changes (its width falls); width/length ratio and auricle sagittal angle fall with age (F9b) | Heathcote 1995 cross-section via F13; F16 n=123; F9b n=843 | F13, F16, F9b | weak / single; sources differ on which part grows |
| Nose | all linear dimensions, volume and surface grow from childhood to old age; tip angle falls (tip drops); nasal skin thicker after 54 y (tip, ala, philtrum) | 859 subjects 4-73 y (F15b); F8 | single |
| Skin thickness | forehead -0.4 to -0.5 mm in the 40-54 group then back; cheek, commissure, mandibular angle within +/-0.1 mm 22-73 y; age explains <1% of variance | 45 women, medians | F8 | single |
| Mandible | angle increases, ramus height, body height and length fall, bigonial width stable (20-40 vs 41-64 vs >=65 y, 120 CT, no mm in abstract); orbital aperture, pyriform area up, glabellar and maxillary angles down | 60 M + 60 F Caucasians | F21 | single |
| Smile mobility | 55-65 y women move soft tissue less than 18-32 y women from rest to smile | 130 Japanese women, 3-D | F23 | single |

Soft-tissue thickness by age: not found in a usable form. A 2026 JPRAS Open review of bone ageing (PMC12914125) lists studies under generic author names with numbers I could not match to real papers: not used.

## 11. Expression mechanics
FACS (Ekman and Friesen 1978; Ekman, Friesen, Hager 2002, F27) codes action units, no mm: AU1 inner brow raise and AU2 outer brow raise (frontalis), AU4 brow lower (corrugator, procerus), AU5 upper-lid raise, AU6 cheek raise and AU7 lid tighten (orbicularis oculi), AU9 nose wrinkle (levator labii superioris alaeque nasi), AU10 upper-lip raise, AU11 (zygomaticus minor), AU12 lip-corner pull (zygomaticus major), AU14 dimple (buccinator), AU15 corner depress (depressor anguli oris), AU16 lower-lip depress, AU17 chin raise (mentalis), AU18 pucker, AU20 lip stretch (risorius), AU23-24 lip tighten/press, AU25 lips part, AU26 jaw drop, AU27 mouth stretch, AU43 eyes close. Standard coding system, strong.
| Task (muscle) | Peak marker displacement, 3-D modulus from rest, mean +/-SD mm | Ref | Conf |
|---|---|---|---|
| Brow raise (frontalis) | brow 10.3 +/-2.7; forehead 8.7; eyelid 9.2-9.5; chin region 4.7 | F11 | single |
| Frown (corrugator) | forehead 9.7 +/-2.2; brow 7.1-7.4; eyelid 7.4-8.0 | F11 | single |
| Nose crinkle (procerus) | nose wing 9.0 +/-3.1; high cheek 10.1; brow 8.5; forehead 8.4 | F11 | single |
| Nose wings up (canine) | nose wing 10.0 +/-2.3; high cheek 10.2 +/-3.4 | F11 | single |
| Eyes closed (orbicularis oculi) | lid 11.5 +/-2.6; eye 10.3 +/-1.8; forehead 9.4; high cheek 9.4 | F11 | single |
| Smile, mouth open (zygomaticus) | mouth corner 17.5-17.6 +/-4.3; low cheek 11.4-11.6; high cheek 9.9-10.2 | F11 | single |
| Corners down (triangularis) | mouth corner 10.5 +/-4.4 | F11 | single |
| Lower-lip curl (mentalis) | chin centre 12.1 +/-3.6; chin sides 10.7-10.9 | F11 | single |
| Cheek suck / puff | chin centre 16.5 +/-7.0, mouth corner 12.2-12.8 / (orbicularis oris, cheeks inflated) mouth corner 15.1 +/-3.6, low cheek 13.0 | F11 | single |
F11: 53 healthy adults (26 M, 43 +/-14 y), 25 skin markers, 3 maximal contractions, helmet capture; marker placement error 1-3.9 mm; asymmetry flagged beyond 6 mm / 10%.
- Smile by intensity (4 levels): lip corner moves 9.2, 11.4, 13.5, 16.0 mm (direction 44 +/-21 deg outward, 37 +/-15 deg upward); cheek up to 4.5, 5.7, 6.8, 7.9 mm, directed upward (51-59 deg) and outward; n=100, 3-D scans of a diverse database (F12, single). Along the cheekbone-maxilla-nasolabial contour the peak amplitude sits near the mouth-corner end: smile 9.0 +/-3.9 (L), 9.9 +/-2.7 (R); laugh 11.9 / 12.3 mm; other contour points 3.4-7.4 (smile) (F13b, single, n not read). Nasolabial fold displacement 7-15 mm (mean 11.6) in a Duchenne smile, n=20 aged 18-23 (search-result text only, weak). Men move more than women; facial shape has a small effect (50 adults, 7 animations; no mm, F13c).
- Jaw: maximum opening 45.7 mm (section 2). Facial skin strain during expression in %: not found.

## 12. Not found
Farkas head length g-op, head width eu-eu, head circumference (original tables); ANSUR II head/face means; Farkas sn-prn, columella and ear tables; nasal tip projection ratios (Goode); malar projection (mm from a facial plane) and malar fat pad thickness; helix/antihelix/concha depths; sex- and ancestry-resolved thickness by landmark; soft-tissue thickness change 25-45 y; per-decade 3-D shape change in mm for 25-45 y (Windhager has no mm); facial skin strain in expression; eyebrow-to-rim distance in mm from the 2010 photographic study (F19 abstract gives no numbers); dedicated lip volume/curvature targets.

## References
F1 Hona TWPT, Stephan CN. Int J Legal Med 2024 (online 2023). PMID 37804332, doi 10.1007/s00414-023-03087-x. F2 Stephan CN, Simpson EK. J Forensic Sci 2008;53:1257-72. doi 10.1111/j.1556-4029.2008.00852.x (abstract text only).
F3 Virdi SS, Wertheim D, Naini FB. Maxillofac Plast Reconstr Surg 2019;41:9. PMID 30863739 (NAW = Farkas data, n=109 M, 200 F; angles n=50). F4 Farkas LG, Katic MJ, Forrest CR. J Craniofac Surg 2005;16:615-46. doi 10.1097/01.scs.0000171847.58031.9e (abstract only); Farkas LG, Anthropometry of the Head and Face, 2nd ed., Raven 1994 (not read).
F5 Wen YF, Wong HM, Lin R, Yin G, McGrath C. PLoS One 2015;10:e0134525. PMID 26247212. F6 Lin YC, Chen CP. PLoS One 2017;12:e0188638. PMID 29176833 (US values back-calculated from its NIOSH ratios; NIOSH = F6b Zhuang Z, et al. Ann Occup Hyg 2010;54:391-402. PMID 20219836).
F7 Ho CT, Denadai R, Lai HC, Lo LJ, Lin HH. J Clin Med 2019;8:2106. PMID 31810228 (Burstone Caucasian norms quoted). F8 Korzekwa S, et al. J Clin Med 2025;14:8401. doi 10.3390/jcm14238401. F9 Chopra K, et al. Aesthet Surg J 2015;35:1007-13. PMID 26508650; F9b Sforza C, et al. Forensic Sci Int 2009;187:110.e1-7. PMID 19356871.
F10 Ha RY, Nojima K, Adams WP, Brown SA. Plast Reconstr Surg 2005;115:1769-73. PMID 15861089. F11 Guihard M, Gracies JM, Baude M. Biomed Res Int 2022. PMID 35252441. F12 Fishman Z, et al. J Plast Reconstr Aesthet Surg 2022;75:4273-80. PMID 36171175.
F13 Windhager S, et al. Am J Phys Anthropol 2019;169:678-88. PMID 31189026 (quotes Heathcote JA, BMJ 1995;311:1668). F13b Lin Y, et al. Sci Rep 2016. PMID 26911450. F13c Weeden JC, Trotman CA, Faraway JJ. Angle Orthod 2001;71:132-40. PMID 11302590.
F15b Sforza C, et al. Forensic Sci Int 2011;204:205.e1-9. PMID 20729017. F16 Brucker MJ, Patel J, Sullivan PK. Plast Reconstr Surg 2003;112:647-52. PMID 12900628. F17 Naumann A. GMS Curr Top Otorhinolaryngol Head Neck Surg 2007 (otoplasty review). PMID 22073080.
F18 Goldstein SM, Katowitz JA. Ophthalmic Plast Reconstr Surg 2005;21:285-91. PMID 16052142. F19 Sclafani AP, Jung M. Arch Facial Plast Surg 2010;12:123-7. PMID 20231595. F20 Glass LR, et al. Ophthalmic Plast Reconstr Surg 2014;30:295-300. PMID 25069068.
F21 Shaw RB, et al. Plast Reconstr Surg 2010;125:332-42 (PMID 20048624) and 2011;127:374-83 (PMID 20871486). F22 Leversha J, et al. J Clin Exp Dent 2016 (PMC4739368, PMID 26855706). F23 Tanikawa C, et al. PLoS One 2019;14:e0219451. PMID 31291323.
F24 Almohaimeed B, Ikram R. Front Oral Health 2025-26. PMID 41602589. F25 Harrison LM, et al. Cleft Palate Craniofac J 2024 (online 2023). PMID 36972478, doi 10.1177/10556656231167066 (controls only, ~16 y). F26 McKnight AN, Momoh AO, Bullocks JM. Semin Plast Surg 2009;23:163-7. PMID 20676309. F27 Ekman P, Friesen WV. Facial Action Coding System, 1978; Ekman P, Friesen WV, Hager JC. FACS manual, 2002.
