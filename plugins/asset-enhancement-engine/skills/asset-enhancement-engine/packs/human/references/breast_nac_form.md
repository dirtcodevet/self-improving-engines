# Breast lower-outer contour and nipple-areola form (adult woman, relaxed, standing): cited numbers for mesh checks

Compiled 2026-10-19 from abstracts and open full texts (Europe PMC, PMC, Crossref). Nothing downloaded for use. Clinical, plastic-surgery and anthropometric sources only. Skin micro-texture lives in `skin_microrelief_breast.md` (not repeated here).
Confidence: strong = 3+ independent studies agree; single = one study; weak = abstract/snippet only, second-hand, photo-morph or surgeon-chosen sample. "Derived" = my arithmetic from a cited number, not a measurement. Rn = reference list at the end (short titles there are descriptive, not verbatim).
Hard truth first: no study gives a lower-pole radius, a Fourier/ellipse fit, or a lower-outer v lower-inner curvature for healthy women with numbers. The one usable contour number is the catenary alpha' (D1). Everything else is proportions and linear distances.

## 0. Measurable descriptors with cited target and spread
### (a) Lower-outer curve of the breast
| # | Descriptor (how to measure on the mesh) | Target (spread) | Source, conf |
|---|---|---|---|
| D1 | Catenary convexity alpha' = alpha / arc length l of the frontal-view contour from M (medial-most inframammary-fold point) round the underside and lateral edge to A (anterior axillary point). Fit y = -alpha cosh((x-b)/alpha)+c in a frame rotated by the M-A angle, middle 1/5 to 4/5 of points. Bigger alpha' = flatter | median 0.13 (min 0.07, max 0.22); age <50 mean 0.14 (0.09-0.21); BMI <25 mean 0.15 (0.07-0.22), BMI >=25 0.12 | R1 single (96 breasts); R2 agrees, median 0.15 (0.08-0.24), 32 breasts |
| D2 | Curvature must stay positive and rise smoothly toward the lowest point: catenary law R(s) = alpha + s^2/alpha (s = arc distance from lowest point). With alpha' 0.13: R = 0.13 l at the lowest point, 0.21 l at s=0.1 l, 0.44 l at 0.2 l, 0.82 l at 0.3 l, 2.05 l at the ends | any straight or inflecting run in the contour = outside the fitted family | derived from R1; the fit reproduced hand-traced area (ICC 0.99) and length (0.98) |
| D3 | Shape of that curve for alpha' 0.07 / 0.13 / 0.22 (ends assumed level): chord/arc 0.37 / 0.54 / 0.69; sag/arc 0.44 / 0.39 / 0.33; end tangent 82 / 75 / 66 deg from horizontal; lowest-point radius = alpha' x l | numbers to test a model's contour against | derived from R1 |
| D4 | Sagittal/oblique profile: upper pole straight or slightly concave, lower pole convex; nipple axis tilted up 20 deg (mean) from the horizontal nipple meridian | qualitative + 20 deg (no SD in abstract) | R4 single (100 models) |
| D5 | Share of mound above : below the nipple meridian, three-quarter view | 45 : 55 (lower pole is the larger part) | R4 single; R5 weak (morphed photos, 1,315 raters + 53 surgeons chose it) |
| D6 | Same share in frontal photo: nipple height from mound bottom as fraction of mound height | 43% (38-47%) = 57 : 43 above : below | R6 weak (surgeon-chosen images). View changes the answer; name the view |
| D7 | Nipple-to-fold distance (nipple to lowest IMF point, relaxed, standing) | natural 3-D: 6.4 +/- 1.1 cm; B/C cup 20 y: 5.5 +/- 0.9 cm; spread across studies 4.4-7.7 cm | R7 single 3-D; R9; R8; R11; R12 -> range strong, value depends on size and method |
| D8 | Nipple-to-fold over under-breast width | 0.48 (6.4 / 13.3) | derived from R7 |
| D9 | Footprint width (under-breast) and projection (nipple/apex to chest wall) | width 13.3 +/- 1.8 cm (3-D) to 14.3 +/- 1.4 cm; projection 4.0 +/- 1.3 cm; ratio h/w about 0.30 | R7, R12, R13; derived ratio |
| D10 | Spherical-cap equivalent radius (sanity bound only; real profile is not a cap) | base 13.3, h 4.0: R = 7.5 cm (6.9 at h 5, 8.9 at h 3) | derived |
### (b) Nipple-areola form
| # | Descriptor | Target (spread) | Source, conf |
|---|---|---|---|
| N1 | Areola diameter | 35-40 mm centre; spread 30-45 (SD 6-14 in studies) | R22 40 mm; R23 31 +/- 10; R11 45 +/- 14; R35 36 +/- 9; R37 34 +/- 6: strong for 30-45 |
| N2 | Areola diameter / breast base width | 0.29 +/- 0.05 | R21 weak (58 models, photos); R24 1 : 3.4 |
| N3 | Nipple diameter (relaxed) | 10-13 mm (mean 13 R22, 10.2 +/- 4.1 R23; textbook 10-12 R26) | single each, agree: moderate |
| N4 | Nipple height (projection above areola plane) | 6.5-9 mm (6.5 +/- 3.7 R23; 9 R22; textbook 9-10 R26) | single each |
| N5 | Height / diameter | 0.64-0.69 (derived from R22, R23); textbook about 0.85: a short cylinder or plateau, taller than a hemisphere would give (0.5) | derived |
| N6 | Nipple diameter / areola diameter | 0.28-0.33 (1 : 3 to 1 : 3.6) | R24, R25, R21, R22, R23: strong |
| N7 | Nipple top form | elevated plateau without constriction 60.2% of breasts; everted 75%, flat 23%, inverted 2% (MRI); retracted/inverted 2-11% | R22; R30 via Gao 2019; R35 2.6%, R36 11.2% |
| N8 | Duct openings on the tip | 5-9 (over 90% of nipples); textbook says 10-20 | R27 strong; R26 weak |
| N9 | Areola relief | no raised disc and no step at its edge in the adult: the areola recedes onto the breast contour; relief = 5 +/- 5 tubercles of 1-2 mm, nipple alone projects | R34 (qualitative), R31 count; heights none |

## 1. Breast contour and geometry (rows used above, with detail)
| Quantity | Value | n, population | Method | Source | Conf |
|---|---|---|---|---|---|
| Catenary alpha', untreated | median 0.13 (0.07-0.22); age <50 0.14, >=50 0.13 (p=0.0525); BMI <25 0.15, >=25 0.12 (p<0.0001) | 96 breasts of reconstruction patients, 27-66 y (median 46), BMI 18-46 | AP photo, manual points M-A, least-squares catenary | R1 | single |
| Catenary alpha', earlier cohort | untreated median 0.1525 (0.080-0.236); expander/implant 0.1794 (0.128-0.226); curve = lateral + inferior contour via L (most lateral point) | 26 patients (>=21 y), 43 breasts | same; rotation angle theta = M-A line | R2 | single |
| Upper v lower mound curvature (catenary per coronal slice, 1 cm apart) | opposite upper/lower relation in flap v implant reconstructions; no numbers | 9 patients | 3-D torso scan | R3 | weak |
| Upper:lower pole, 3-D | volume 47.8 : 52.2; surface area 70.2 : 29.8 (area bounded by IMF, 1 cm below clavicle); split by horizontal plane at nipple | 13 Chinese women, 28.7 y, BMI 18.7, volume only 41.8 +/- 28.1 mL | non-contact 3-D scanner | R8 | single, small breasts |
| Nipple to fold | 6.4 +/- 1.1 cm; sternal notch-nipple 19.9 +/- 2.3 (R) / 20.1 +/- 2.4 (L); nipple-midline 9.4 +/- 1.3 / 10.0 +/- 1.2; under-breast width 13.4 +/- 1.8 / 13.2 +/- 1.7; L-R fold difference 0.53 +/- 0.35 cm | 100 women, natural breasts, mostly non-ptotic, age n.r. | Vectra, standing | R7 | single |
| Same, other cohorts | 4.4 +/- 0.8 straight, 4.5 surface (R8); bust point to under-bust 5.47 +/- 0.92 cm, 20.5 y, B/C (R9, n=124); 7.7 +/- 1.6 tape (R11, n=53, 22.1 y); 7.5 +/- 1.6 (R12, n=1,210 breasts, patients) | as stated | 3-D / tape | as stated | strong for range |
| Projection | 4.0 +/- 1.3 cm; 43.5 +/- 10.3 mm in a bra (length 151.7, width 157.9 mm); 1.0 +/- 0.7 cm (R8, tiny breasts); about 4.2-4.3 cm Vietnamese 18-25 y | 100 Malay nulliparous 17-30 y (abstract); 97 soldiers (Artec); 13; 128 | caliper/ruler; 3-D; 3-D | R13; R10; R8; R37 snippet | weak to single |
| Shape clusters (young adults) | droopy 31%, small/flat 19%, upward 24%, large/inward 26% (age 26-35); outer breast arc about 93-126 mm across clusters (snippet) | young American women, 3-D | cluster analysis | R19 | weak |
| Shape typology, Chinese 20 y | plump oval 46, uniform oval 50, flat circle 28 of 124; no geometry given | 124, 20.5 y, B/C | 10 mm slices | R9 | weak |

## 2. Lower-outer v lower-inner v outer side (asymmetry around the nipple)
- No study gives numeric lower-outer, lower-inner or outer-side curvature, radius or section shape for healthy women. Plainly: not found.
- The only quantified contour (R1) is one continuous convex arc from the medial fold, under the breast and up the lateral edge to the axilla; D2/D3 are its law. Flat stretches are not part of it.
- Nipple sits outside the middle of the mound: horizontal position 71% (60-80%) across the mound, definition not stated (R6, weak); nipple-to-midline 9.4-10.0 cm against 13.3 cm under-breast width (R7).
- Medial v lateral radius (nipple to midsternal line v nipple to anterior axillary line): 12.9 v 13.9 cm in 370 Lagos students; SDs look wrong (R38, weak).
- 3-D scans of middle-aged women: inner and outer under-breast curve curvature are separate shape factors; some women have an asymmetric under-breast curve; a larger radius on the inner part suited them (R18, weak, abstract only).
- Upper and lower mound curvature vary separately (R3, weak). MRI quadrant work gives density, not contour.

## 3. Nipple morphology, relaxed
| Quantity | Value | n, population | Method | Source | Conf |
|---|---|---|---|---|---|
| Diameter / height / areola | 13 / 9 / 40 mm (no SD) | 300 adult Japanese women (600 breasts) | micrometer calipers | R22 | single |
| Diameter / height / areola | 10.2 +/- 4.1 / 6.5 +/- 3.7 / 30.9 +/- 10.1 mm | 225 Korean women, 20s-50s | caliper (a search summary says questionnaire; unresolved) | R23 | weak-single |
| Diameter / projection, Lagos | 12.3 / 2.8 mm (SDs larger than means) | 370 nulliparous students | caliper | R38 | weak |
| Textbook size and shape | cylindrical papilla 10-12 mm wide x 9-10 mm high; no sebaceous glands; no subcutaneous fat; skin convoluted | review, no measurement cited | - | R26 | weak |
| Hypertrophy line | ideal 6-8 mm, over 10 mm hypertrophic (statement, no data) | - | - | R39 | weak |
| Forms | elevated plateau, no constriction 60.2%; inverted 3.5%; unclassified 0.3%; the other 36% = flat and constricted types (my inference; their definitions not retrieved) | 600 breasts | visual | R22 | single |
| Everted / flat / inverted | 75% / 23% / 2%; 96% symmetric | 530 nipples, 265 asymptomatic women 24-84 y | breast MRI | R30 citing Gao 2019 | single |
| Retracted | 2.6%; 11.2% | 385 Turkish students 18-26 y; 234 Korean premenopausal | clinical | R35; R36 | single each |
| Duct openings | 5-9 on over 90%; 15 orifices for 29 ducts in one 3-D rebuild; 3.8 +/- 1.6 seen in lactation (1-8); textbook 10-20 | six approaches; 3 nipples; 98 lactating women | histology / view | R27; R28; Jutte 2014 BMC Pregnancy Childbirth 14:124 (via skin_microrelief_breast.md) | strong for 5-9 |
| Duct caliber | about half of ducts under 0.5 mm (bounds orifice size, which is itself unmeasured) | 226 mastectomy nipples | histology | R29 | single |
| Smooth muscle | radial (Meyerholz) and circular (Sappey) fibres under the skin | review | - | R26 | weak |
| Growth | nipple diameter +5-6 mm from Tanner 1 to 5 | review | - | R34 | weak |
- Not found: papilla shape classes with numbers (conical v cylindrical v dome), base-to-areola transition profile or angle, fold/wrinkle depth and spacing, duct orifice diameter, 3-D photogrammetry of relaxed nipples. Do not invent them; keep these as free parameters tied to the reference photo.

## 4. Areola morphology
| Quantity | Value | n, population | Method | Source | Conf |
|---|---|---|---|---|---|
| Diameter | 40 mm (R22); 30.9 +/- 10.1 (R23); 45 +/- 14 (R11); 36 +/- 9 Turkish and 33 +/- 3.5 Chinese (quoted in R11); 3.4 +/- 0.6 cm Vietnamese 18-25 y (snippet, R37); 3-6 cm textbook (R26) | as in section 3 | caliper / tape | as cited | strong (30-45 mm) |
| Proportions | nipple : areola : breast about 1 : 3 : 10 (derived from areola:breast 1 : 3.4 and nipple:areola 1 : 3) | 37 women 20-64 y | measured | R24 | single |
| Surface profile by stage | Tanner 3 areola and breast same contour; stage 4 (about 13-14 y) areola + papilla form a secondary mound above the breast contour; stage 5 (about 15 y) areola recedes and contours merge; no mm heights | review of Marshall and Tanner 1969 | clinical staging | R34 | strong (qualitative) |
| Montgomery tubercles, count | mean 5.0 +/- 5.2, range 0-25; more in premenopausal (p=0.018); no link to age, BMI, NAC size | 211 patients, 399 breasts | photo counts | R31 | single |
| Areolar glands postpartum | 97% have glands; 80.2% have 1-20; 33% secrete | 121 mothers, days 0-3 | inspection | R32 | single |
| Tubercle size | raised 1-2 mm papules; 2-5 mm in pregnancy | reviews, Acta Derm Venereol letter, Radiopaedia | no study | R30; R41 | weak |
| Tubercle histology | duct + sebaceous gland in 34 of 35 tubercles | 12 mastectomy specimens | serial sections | R33 | single |
| Areola v breast skin | no subcutaneous fat, thin radial + circular muscle layer, sebaceous glands project from the surface, skin convoluted; pigment 2.1x (see microrelief file) | review | - | R26 | weak |
- Not found: wrinkle depth or spacing of the areola, tubercle height above the surface, areola thickness in mm, any 3-D height map of the areola.

## 5. Published ways to measure it on a 3-D scan
| Method | Detail | Source |
|---|---|---|
| Landmarks and sections | sternal notch, nipple, lowest IMF point, medial/lateral base; landmarks at XZ/YZ plane crossings; poles split by the nipple-level horizontal plane; projection = mean vertical distance from medial and lateral nipple base to a virtual chest wall; distances both straight and over the surface | R8 |
| Inferior contour | principal curvatures + shape index on the mesh; candidates = negative shape index and min principal curvature below ROI mean; 5 deg sectors; cubic spline; error to hand tracing 1.64 +/- 0.76 mm (Dice 0.87 at the 4th threshold), 151 breasts, 21-66 y, 3dMDtorso | R14 |
| Ptosis from curvature and surface orientation | about 13% more accurate than 2-D photogrammetry against 9 surgeons | R15 |
| Contour convexity | catenary fit (D1), also per coronal slice | R1, R3 |
| Global average radius of curvature | radius of the circle through 3 non-collinear points on the under-breast curve; outer curve in 6 parts, inner in 8; single local radii are too unstable | R18 (values not retrieved) |
| Shape space | 110 standing scans, public statistical model, 4 landmarks (not downloaded) | R16 |
| PCA of shape | two components separate breasts; test-retest between 2 operators similar; no numbers | R17 |
| Contour maps | slices perpendicular to the bust point axis, 35 measurements, 4 PCA factors (46 women, 18-45 y) | R20 |

## 6. Gaps and nearest stand-ins
- Lower-pole radius in cm or per mm: none. Stand-ins: D1-D3 (relative to contour length) and D10 (cap bound).
- Ellipse, conic or Fourier fits of the breast with values: none (the elliptic Fourier chest paper and spherical-harmonics model give no numbers in what was read).
- Lower-outer v lower-inner: none (section 2).
- Natural nipple 3-D form, areola height and texture: none beyond calipers (section 3, 4).
- All photo-based proportions (45:55, 43%, 71%, 0.29) come from selected "attractive" images: targets, not population norms.

## References
R1 Lee J, Chen S, Reece GP, Crosby MA, Beahm EK, Markey MK. A novel quantitative measure of breast curvature based on catenary. IEEE Trans Biomed Eng 2012;59:1115-1124. doi:10.1109/TBME.2012.2184541. PMID 22271826.
R2 Lee J, Beahm EK, Crosby MA, Reece GP, Markey MK. Analysis of breast contour using rotated catenary. AMIA Annu Symp Proc 2010:432-436. PMID 21347015.
R3 Lee J, Reece GP, Markey MK. Breast curvature of the upper and lower breast mound. 3DBODY.TECH 2012:171-178 (abstract page only).
R4 Mallucci P, Branford OA. Concepts in aesthetic breast dimensions: analysis of the ideal breast. J Plast Reconstr Aesthet Surg 2012;65:8-16. doi:10.1016/j.bjps.2011.08.006. PMID 21868295.
R5 Mallucci P, Branford OA. Population analysis of the perfect breast. Plast Reconstr Surg 2014;134:436-447. doi:10.1097/PRS.0000000000000485. PMID 25158703.
R6 Artz JD, Hauch AT, Francis CS, Chasan PE. In search of the attractive breast. Aesthet Surg J Open Forum 2021;3:ojab031. doi:10.1093/asjof/ojab031. PMID 34595473.
R7 Henseler H. Exploring natural breast symmetry in the female plastic surgical patient population. GMS Interdiscip Plast Reconstr Surg DGPW 2023;12:Doc03. doi:10.3205/iprs000173. PMID 37577729.
R8 Ji K, Luan J, Liu C, et al. Breast dynamic morphological changes after dual-plane augmentation, 3-D scanning. PLoS One 2014;9:e93010. doi:10.1371/journal.pone.0093010. PMID 24671190.
R9 Zhong Z, Zhang B, Hu Y, Zhang L, Gu B, Sun Y. Young women's breast-bra reshaping by different bra cups. Int J Environ Res Public Health 2023;20:3856. doi:10.3390/ijerph20053856.
R10 Coltman CE, Brisbine BR, Molloy RH, Steele JR. 3-D breast and torso anthropometry, 97 female soldiers. Front Sports Act Living 2022;4:821210. doi:10.3389/fspor.2022.821210.
R11 Al-Qattan MM, Aldakhil SS, Al-Hassan TS, Al-Qahtani A. Average breast in young nulliparous Saudi women. Plast Reconstr Surg Glob Open 2019;7:e2326. doi:10.1097/GOX.0000000000002326.
R12 Huang NS, Quan CL, Mo M, et al. Breast measurements, volume and ptosis in 605 Asian patients. PLoS One 2017;12:e0172122. doi:10.1371/journal.pone.0172122.
R13 Shahlini SU. Anthropometric breast measurements in Malay women. Thesis, Universiti Sains Malaysia, 2014. erepo.usm.my/handle/123456789/24082 (abstract via search).
R14 Zhao L, Cheong A, Reece GP, Fingeret MC, Shah SK, Merchant FA. Inferior breast-chest contour detection in 3-D images of the female torso. IEEE J Transl Eng Health Med 2016;4:4300410. doi:10.1109/JTEHM.2016.2614518. PMID 32519998.
R15 Li D, Cheong A, Reece GP, Crosby MA, Fingeret MC, Merchant FA. Computation of breast ptosis from 3D surface scans of the female torso. Comput Biol Med 2016;78:18-28. doi:10.1016/j.compbiomed.2016.09.002. PMID 27643463.
R16 Weiherer M, Eigenberger A, Egger B, Brebant V, Prantl L, Palm C. Regensburg Breast Shape Model. Visual Computer 2022. doi:10.1007/s00371-022-02431-3.
R17 Catanuto G, Taher W, Rocco N, et al. Breast shape analysis with curvature estimates and PCA. Aesthet Surg J 2019;39:164-173. doi:10.1093/asj/sjy070. PMID 29579138.
R18 Lee HY, Hong K, Kim EA. Appl Ergon 2004;35:353-359; Lee HY, Hong K. Appl Ergon 2007;38:377-384, doi:10.1016/j.apergo.2006.03.014, PMID 16828050; J Korean Soc Cloth Text 2010;34:385-392, doi:10.5850/JKSCT.2010.34.3.385 (abstracts only).
R19 Suh M, Park JH. Breast geometry of young American females, 3-D. Appl Sci 2022;12:8578. doi:10.3390/app12178578 (abstract + snippet; page returned 403).
R20 Pei J, Fan J, Ashdown SP. A novel method to assess breast shape and breast asymmetry. J Text Inst 2018. doi:10.1080/00405000.2018.1555876.
R21 Laschuk MJ, Head LK, Roumeliotis GA, Xuan L, Silverman HJ. Areola/nipple ratios in 58 models. JPRAS Open 2020;23:55-59. doi:10.1016/j.jpra.2019.11.001.
R22 Sanuki J, Fukuma E, Uchida Y. Morphologic study of nipple-areola complex in 600 breasts. Aesthetic Plast Surg 2009;33:295-297. doi:10.1007/s00266-008-9194-y. PMID 18626683.
R23 Lee JH, Yang JD, Chung KH, Chung HY, Cho BC. Anthropometric measurement for the nipple areola complex. Arch Plast Surg 2008;35:461-464.
R24 Hauben DJ, Adler N, Silfen R, Regev D. Breast-areola-nipple proportion. Ann Plast Surg 2003;50:510-513. doi:10.1097/01.sap.0000044145.34573.f0. PMID 12792541.
R25 van Wingerden JJ. Aesthetic Plast Surg 1997;21:408-411. PMID 9354602 (nipple 28% of areola, 20 women, via a search summary).
R26 Zucca-Matthes G, Urban C, Vallejo A. Anatomy of the nipple and breast ducts. Gland Surg 2016;5:32-36. doi:10.3978/j.issn.2227-684X.2015.05.10. PMID 26855906.
R27 Love SM, Barsky SH. Anatomy of the nipple and breast ducts revisited. Cancer 2004;101:1947-1957. doi:10.1002/cncr.20559.
R28 Rusby JE, Brachtel EF, Michaelson JS, Koerner FC, Smith BL. Breast Cancer Res Treat 2007;106:171-179. doi:10.1007/s10549-006-9487-2.
R29 Taneri F, et al. Microanatomy of milk ducts in the nipple. Eur Surg Res 2006;38:545-549. doi:10.1159/000096775.
R30 Del Riego J, et al. Multimodality approach to the nipple-areolar complex. Insights Imaging 2020;11. doi:10.1186/s13244-020-00896-1 (cites Gao 2019, RadioGraphics 39:10-27).
R31 Kandi LA, et al. Montgomery tubercles and 3-D NAC tattooing. Am J Surg 2023;225:99-102. doi:10.1016/j.amjsurg.2022.11.005. PMID 36404166.
R32 Doucet S, Soussignan R, Sagot P, Schaal B. Areolar glands. Early Hum Dev 2012;88:119-128. PMID 21852053.
R33 Smith DM Jr, Peters TG, Donegan WL. Montgomery's areolar tubercle. Arch Pathol Lab Med 1982;106:60-63. PMID 6277270.
R34 Javed A, Lteif A. Development of the human breast. Semin Plast Surg 2013;27:5-12. PMID 24872732; Marshall WA, Tanner JM. Arch Dis Child 1969;44:291-303. PMID 5785179.
R35 Avsar DK, Aygit AC, Benlier E, Top H, Taskinalp O. 385 Turkish female students. Aesthet Surg J 2010;30:44-50. doi:10.1177/1090820X09358078. PMID 20442074.
R36 Park IY, Kim MR, Jo HH, Lee MK, Kim MJ. NAC with age, parity, breastfeeding, Korean women. J Hum Lact 2014;30:474-479. doi:10.1177/0890334414549049.
R37 Nguyen DM, et al. Breast anthropometry in Vietnamese youth, 128 women. Eur J Plast Surg 2023;46:1049-1058. doi:10.1007/s00238-023-02134-5 (abstract; areola and projection values from a search snippet).
R38 Archibong OR, et al. Breast measurements of nulliparous women in Lagos. J West Afr Coll Surg 2022;11(4):1-6. doi:10.4103/jwas.jwas_81_22. PMID 36188056.
R39 Ors S. Nipple dimensions after augmentation, mastopexy, reduction. Aesthetic Plast Surg 2020;44:2089-2093. doi:10.1007/s00266-020-01861-5. PMID 32671450.
R41 Acta Derm Venereol 2004 letter on Montgomery tubercles, doi:10.1080/00015550410024878 (author not verified); Radiopaedia article 14940.
