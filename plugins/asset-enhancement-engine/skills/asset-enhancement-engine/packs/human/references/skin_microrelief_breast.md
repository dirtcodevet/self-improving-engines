# Skin micro-relief for breast, areola and nipple (adult woman, light end of normal): cited numbers for a texture model

Compiled 2026-10-19 from abstracts, open full texts (Europe PMC) and publisher pages. Nothing was downloaded for use. Clinical, dermatological, anatomical sources only.
Confidence: strong = 2+ studies agree; single = one study; weak = abstract only, quoted second-hand, or unverified. "via Rn" = number read inside paper Rn that cites it. "Assumption" = no source found, engineering default.
Method warning: replica-profilometry Ra (young forearm about 17 um) and in-vivo optical Ra (about 7-10 um) differ about 2x by method. Pick one family and stay in it.

## 0. Proposed texture model (my reading of the numbers)
The skin surface is a height field made of four stacked layers, each with a few free parameters:
1. Orientation field. Primary furrows follow the local tension direction, in two families (young skin) with a weak third (secondary) set. On the breast the tension/folding lines run around the areola (stretch marks fan out from the areola, and striae lie across the tension direction, R30), so family 1 = circumferential about the nipple, family 2 about 60-70 deg to it (forearm adults: 50 and 165 deg to the limb axis, R1). Anisotropy is low in young trunk skin (section 2).
2. Network geometry sets plateau size and line spacing. Seed points on a jittered hexagonal lattice, then Delaunay edges = furrows (young, triangular plateaus; Banba R32) or Voronoi borders (older, polygonal; Sun R10). Choose target plateau area A (mm2): Voronoi seed spacing a = sqrt(A/0.866); Delaunay edge s = sqrt(A/0.433). Young adult A = 0.17 mm2 gives a = 0.45 mm, s = 0.63 mm. Jitter (sigma/spacing 0.2-0.3) controls how triangular vs random it looks; raise it with age.
3. Furrow depth sets roughness. Primary depth D1 (light end 25-35 um, hard floor 20 um), secondary D2 (5-15 um); V-shaped section, width Wf (assumption 40-60 um, grows with age). Plateaus lightly domed (assumption). Check: the finished field should give Ra 7-10 um (in-vivo scale) or 15-17 um (replica scale), Rz 32-40 um, Rt under about 85 um.
4. Openings and glands. Follicle/pore mouths at furrow junctions, density 17-28 per cm2 on trunk skin (about 1 per 20 plateaus); fine vellus hair. Areola: Montgomery tubercles (count 3-8, 1-2 mm). Nipple: 5-9 duct openings, plus folds whose depth/count have no source (free parameters).
Stretch rule: tension flattens and aligns furrows (Ra roughly halves at the limit strain, Ferguson and Barbenel quoted in R13, wording ambiguous; stretch smooths along the stretch axis, compression roughens across it, R31). Ageing rule: depth up, polygon count down, second direction lost (R1, R3, R5).

### Recommended starting parameters (young adult, light end), with the row that backs each
| Parameter | Start value | Range to expose | Backing |
|---|---|---|---|
| plateau area A / density | 0.17 mm2 / 5.8 per mm2 | 0.09 (child) - 0.27 mm2 (older adult) | R3 via R4 |
| line families | 2 main + 1 shallow | secondary vanishes after 60 y | R1 |
| D1 primary depth | 30 um | 20-40 | R1, R10, R11 |
| D2 secondary depth | 10 um | 5-15 | R10 (5-40 range) |
| furrow width | 50 um | assumption | none |
| anisotropy index (ICx) | 0.1 belly-like to 0.23 chest-like | 0.05-0.3 | R12 |
| Ra target / Rz target | 8 um / 35 um (in vivo) | 7-10 / 32-40 | R7, R8 |
| follicle density | 17-28 per cm2 | 15-40 | R15 |
| areola diameter | 35 mm | 30-45 | R21, R37 |
| Montgomery tubercles | 5 per areola, 1-2 mm | 0-25 | R17, R20 |
| nipple diameter / projection | 11 mm / 6 mm | 10-14 / 3-9 | R21, R26 |
| nipple:areola diameter | 1:3.6 (28%) | - | R22 |
| duct openings on nipple tip | 7 | 5-9 | R23 |

## 1. Roughness by body site (Ra, Rz, Rt in um)
| Site | Value | n, population | Method | Source | Conf |
|---|---|---|---|---|---|
| Breast, upper inner quadrant | no numbers readable (rougher and deeper furrows after radiotherapy) | 20 women, 43-55 y, irradiated | silicone replicas, image analysis | R36 | weak (abstract) |
| Chest / breast, young | not found. Nearest stand-in: volar forearm | - | - | - | - |
| Volar forearm, healthy adults | Ra 6.7 (SD 0.8) to 7.6 (SD 1.1); Rz 31.9 (4.1) to 36.4 (4.9) | 12 adults, mean 32.9 y (SD 7.2), 4 sites | in-vivo optical (Ra/Rz taken to be PRIMOS; device not confirmed) | R7 via R8 | single |
| Skin, pregnant women (site not stated) | Ra 9.65 (2.20); Rz 39.79 (8.83) | 67 women, 33.1 y | in-vivo topography (Visioscan VC98 named in the paper) | R8 | single |
| Volar forearm, women 20-29 y | Ra 16.9 (SD 3.4); 60-74 y: 28.5 (SD 6.8) | 50 women 20-74, 10 per decade | replicas, interference-fringe profilometry | R6 via R4 | single |
| Human skin, literature span | Ra 6.7-46.2; Rt 74.0-84.3 | various | various | R9 (discussion) | weak |
| Forearm elderly, anterior | Ra 38.4 (SD 20.2; 15.2-107.5) | 22 women, mean 82.6 y | replica + chromatic confocal pen | R4 | single |
| Abdomen vs forearm | abdomen Rz significantly lower than forearm (no values) | 14 subjects, replica casts | stylus profilometer, 2 scan directions | Makki (in R13) | weak |
| Forearm vs back vs face | forearm and back differ only in waviness/Fourier, not Ra/Rz | back 5, forearm 14, face 4 women | optical 3-D device | Jacobi 2004, PMID 15479444 | weak (abstract) |
- Age trend: Ra, developed surface area and peak-to-trough amplitude rise with age at forearm and temple, men more than women (R5); roughness rises about exponentially with age on the ventral upper arm, 142 subjects aged 1-79 (Hoppe, in R13); forearm Ra 16.9 -> 28.5 um (R6): strong direction, few numbers.
- Method spread: replica repeatability CV about 14% for Ra (Makki, in R13); scan direction matters (anisotropic surface).

## 2. Micro-relief line network (forearm unless stated)
| Quantity | Value | n, population | Method | Source | Conf |
|---|---|---|---|---|---|
| Primary line depth | 20-100 um; secondary 5-40 um; tertiary about 0.5 um | consensus guidance | EEMCO 1999 (Leveque) via R10 | R10 | strong (R11 says 20-200 um) |
| Primary furrow mean depth | children 33 (SE 1), adults 41 (SE 2), aged 60 (SE 3) um; some aged 100 | 116 people, 2-98 y, both sexes | Silflo replica, shadow image analysis, 15 mm field | R1 | single |
| Line density, principal axis | 29 per cm in children and adults, 24 in aged (printed "/cm2"; formula is per cm of surface) | same | same | R1 | single |
| Line directions | principal axis 65 deg (child), 50 (adult), 30 (aged) to forearm axis; second axis about 165 deg, gone after about 60 y, rare after 70 | same | same | R1 | single |
| Plateau (polygon) density | 11.1 per mm2 child, 5.8 young adult, 3.7 older adult | 190 people, 6 mo-95 y (site not stated) | replica, semi-automatic image analysis | R3 via R4 | single |
| Polygon size, elderly | 2.41 per mm2, area 0.54 mm2, perimeter 4.04 mm, aspect ratio 3.1 | 22 women, 82.6 y | replica watershed | R4 | single |
| Anisotropy index ICx/ICy, young (n=21 French women) | forearm 0.24/0.07; thigh 0.11/0.08; cheek 0.057/0.044; upper chest 0.226 (SD 0.3); belly 0.107/0.065 | young 21 vs 45-65 y 21 | replicas, Fourier tension model | R12 | single |
| Tension ranking | cheek > anterior arm > thigh > belly > upper chest > forearm > posterior arm | same | same | R12 | single |
| Upper chest tension imbalance | 0.27 young vs 0.65 elderly | same | same | R12 | single |
| Leg, lateral mid-calf | primary-line count and depth rise to age 35, plateau to 65, then rise (no values) | 81 women/men, 6-76 y | replicas | R2 | single |
| Crow's foot | depth 25 um at 6 y, x8 by 65 y; line count doubles 6-35 y then constant | same | same | R2 | single |
| Age effect on lines | density down, depth up, second direction lost, anisotropy up, plateau area up | 40 M + 40 F, 25-35 vs 50-65 y | Dermatop fringe projection | R5 | strong (R1, R3, R5, R33 agree) |
| Cheek, age 0-60s | furrow length and polygon count fall, width and polygon area rise (no values) | 163 Japanese women | 2-D microscope image | R33 | single |
| Orientation vs Langer lines | microrelief families track tension; one family parallels Langer's lines | forearm, 3 subjects 30-80 y | line angles 43/137, 46/104, 81/100 deg | R9 | weak (n=3) |
| Primary lines (young skin appearance) | triangular network; old skin approaches Voronoi polygons | model figure | image-derived | R10 | weak |
- Breast orientation: no replica study found. Striae radiate from the areola outward, so tension lines run around it (R30; Kraissl lines did not match on breasts, same paper). Upper chest striae run mainly horizontal over the pectoral muscle (R30). Inference, not measured.
- Stretch: leg microrelief is less stretch-sensitive than forearm (R2). Skin lines reorient from near-isotropic to single-direction with age (R9, Thieulin 2020, PMID 32090946).

## 3. Pores, follicles, vellus hair (trunk)
| Site | Follicles per cm2 (mean, SD) | n, population | Method | Source | Conf |
|---|---|---|---|---|---|
| Chest (trunk) | 28.4 (6.4) | 15 adults (8 F), mean 23.9 y, 20-32 | cyanoacrylate stripping, 2x2 cm, microscope | R15 | single |
| Abdomen (lower) | 16.9 (6.2) | same | same | R15 | single |
| Back (lower) | 24.7 (5.9) | same | same | R15 | single |
| Forearm / upper arm / thigh / calf / neck | 40.3 (14.9) / 45.9 (14.5) / 21.0 (8.0) / 15.6 (3.6) / 47.3 (17.1) | same | same | R15 | single |
| Forehead | 285 (84.1); Otberg value 292 (quoted on a trichology page) | same; Otberg 7 sites | same | R15, R16 | single (authors say R15 agrees with R16) |
- Orifice diameter and depth for chest/breast: no per-site numbers retrieved (R16 table not accessible; abstract says calf has the largest mean orifice, forearm the lowest values, forehead the highest density). Vellus orifice is about half a terminal one (trichology review, weak). Vellus hair diameter under 40 um (histology definition, weak). Assumption for the model: mouth diameter 30-80 um, depth 100-300 um.
- Breast vellus-hair density: not found. Stand-in: chest 28.4 per cm2 (R15). Most follicles on women's trunk are vellus.
- Facial pores (cheek, 2,585 women) are a different quantity (250 um detection threshold); not used. Flament 2015, PMID 25733918.

## 4. Areola
| Quantity | Value | n, population | Method | Source | Conf |
|---|---|---|---|---|---|
| Montgomery tubercles per NAC | mean 5.0 (SD 5.2), range 0-25; more in premenopausal; no link to age, BMI, NAC size | 211 patients (399 breasts), pre-reconstruction | photograph counts | R17 | single |
| Areolar glands, postpartum | 97% have glands; 80.2% have 1-20 per areola; 33% secreting | 121 Caucasian mothers, days 0-3 | screening | R18 | single |
| Tubercle count, reference sites | 4-25 per side; 10-15 per areola, or 4-28 per breast | - | encyclopedic, no primary study | Radiopaedia 25745; Wikipedia Areolar gland | weak |
| Tubercle size (non-pregnant) | raised 1-2 mm ("Morgagni tubercles"); about 2-5 mm in pregnancy (review snippet, unverified) | - | review | R20 | weak |
| Tubercle histology | 34 of 35 tubercles (97%) had a lactiferous duct joined to a sebaceous gland; no associated hair follicle on light microscopy or ultrasound (Wortsman 2019 via a 2025 case review) | 12 mastectomy specimens | 1,536 serial sections | R19 | single |
| Areola diameter | 30.93 (SD 10.07) mm; nipple fraction 28% (1:3.6) | 225 Korean women 20s-50s; 20 Caucasian nulliparous, 25.5 y | caliper; photometric | R21, R22 | single each |
| Areola diameter, other | mean 40 mm ("4 cm", varies greatly); 50.6 (SD 18.5) mm, 18-32 y Lagos | review; 370 students | caliper | R37; R34 | weak (R34 odd SDs) |
- Areola vs breast skin: more melanin (2.14x per basement-membrane length), melanocyte:keratinocyte 1:9.7 vs 1:14.7; stratified keratinized epithelium, smooth muscle fibres, sensory endings and pilosebaceous follicles (R20); hair density not reported. Surface wrinkling/fold depth and spacing: no numbers found. Assumption: areola relief finer and softer than breast skin, with muscle-driven wrinkles (free parameter).

## 5. Nipple
| Quantity | Value | n, population | Method | Source | Conf |
|---|---|---|---|---|---|
| Diameter / height | 10.21 (SD 4.14) mm / 6.54 (SD 3.74) mm | 225 Korean volunteers 20s-50s | caliper | R21 | single |
| Diameter | 13.9 mm mean | 226 mastectomy specimens (carcinoma, older) | measured | R26 | single |
| Diameter / height, review mean | 13 mm / 9 mm | review, n and ages not stated | secondary | R37 | weak |
| Projection, Lagos students | 2.8 (SD 3.0) mm; diameter 12.3 (SD 13) mm | 370 nulliparous, 18-32 y | caliper | R34 | weak (SD larger than mean) |
| Duct openings on nipple tip | more than 90% have 5-9 | six approaches | in vivo + in vitro | R23 | strong (R20 agrees) |
| Ducts in nipple, orifices | median 23 ducts (IQR 19-28); one nipple: 29 ducts onto 15 orifices | 129 mastectomy nipples | 3 mm blocks, 3-D reconstruction (3 nipples) | R24 | single |
| Ducts, size | mean 17.5 ducts; about 50% under 0.5 mm | 226 specimens | histology | R26 | single |
| Orifices seen in lactation | 3.8 (SD 1.6) per nipple, range 1-8 | 98 women, 32.8 y | direct view, manual expression | R25 | single |
| Orifice diameter, surface papillae, folds | not found. Assumption: orifice 0.2-0.5 mm; fold depth/count free parameters | - | - | - | none |
- Counts disagree by method: 5-9 openings (R23), 15 openings for 29 ducts in one 3-D reconstruction (R24), 3.8 visible per nipple in lactation (R25). Use 7 with 4-12 exposed.
- Texture: histology only says the nipple is keratinized epithelium with smooth muscle, sebaceous glands and duct openings; one histology note (Petrovic 2022, Acta Med Median, search snippet, weak) says the summit has no papillae between duct terminals. No source gives rugae depth or spacing.

## 6. Mathematical and computational models
| Model | Parameters and finding | Source | Conf |
|---|---|---|---|
| Voronoi microrelief by age | random seeds on 1x5 mm patch, triangles merged to polygons; SC 25 um, primary 20 um, secondary 10 um deep (model values); young more triangular, old more Voronoi-like; plateau grid larger with age | R10 | single |
| Delaunay of a pore lattice | pores on triangular grid, Delaunay edges = furrows, triangles = ridges; pore size, furrow width and directionality come from image analysis; no numbers | R32 | single (CG) |
| Furrow network statistics | polygon number, area, perimeter, equivalent diameter: exponential or 4th-order age trends | R3 | single |
| Anisotropy / tension model | 2-D Fourier split into two orientation families, tension indices ICx, ICy | R12 | single |
| Displacement-map convolution | micro-scale about 10 um, stretch blurs and compression sharpens the map; roughness = variance of normal distribution | R31 | single (CG) |
| Fractal dimension, PSD, autocorrelation length | no numeric value for skin found. A Japanese box-counting paper says smoother skin has higher D (unverified, weak) | - | none |
Suggested use (assumption): Voronoi/Delaunay for the furrow graph, then a Gaussian blur of the furrow mask (sigma about 20-30 um) for the groove profile; add low-amplitude correlated noise only if a measured PSD is later supplied.

## 7. Colour (areola, nipple vs breast skin)
- No CIELAB (L*, a*, b*) or melanin/erythema index table for normal areola or nipple against breast skin was found. Nearest data: areola melanin 2.14x breast skin (R27, 20 women); areolas are darker in pregnancy and before menses, reflectance ratios areola:breast differ by population (R28, no values in abstract); reconstructed areolae come out redder, so the better tattoo pigment has less red and about 4-5 deg more yellow on the colour wheel than the normal side (R29, n=25).
- Recommendation: take the areola and nipple colour from the reference photograph for each model, not from a table.

## 8. Gaps and nearest stand-ins
- No microrelief profilometry of normal breast skin found (only irradiated, R36). Stand-ins: forearm (depth, density, Ra), upper chest and belly (anisotropy, R12), chest/abdomen (follicles, R15).
- No numbers for furrow width, areola wrinkle depth, nipple fold depth, duct orifice diameter, fractal/PSD of skin, or Lab colour.
- Several key values are second-hand (R3 via R4, R6 via R4, R7 via R8); check originals before publishing.

## References
R1 Corcuff P, de Rigal J, Leveque JL, Makki S, Agache P. Skin relief and aging. J Soc Cosmet Chem 1983;34:177-190.
R2 Corcuff P, Leveque JL, Grove GL, Kligman AM. Impact of aging on the microrelief of peri-orbital and leg skin. J Soc Cosmet Chem 1987;38:145-152.
R3 Voros E, Robert C, Robert AM. Age-related changes of the human skin surface microrelief. Gerontology 1990;36:276-285. PMID 2076827.
R4 Bachy M, Bosser C, Villain B, Auregan JC. Materials (Basel) 2022;15:8258. doi:10.3390/ma15228258.
R5 Lagarde JM, Rouvrais C, Black D. Topography and anisotropy of the skin surface with ageing. Skin Res Technol 2005;11:110-119. PMID 15807809.
R6 Li L, Mac-Mary S, Marsaut D, et al. Age-related changes in skin topography and microcirculation. Arch Dermatol Res 2006;297:412-416. PMID 16328340.
R7 Kottner J, et al. Comparison of two in vivo measurements for skin surface topography. Skin Res Technol 2013;19:84-90. PMID 23279017.
R8 Wilborn D, et al. Skin Pharmacol Physiol 2025;38:138-148. doi:10.1159/000546770.
R9 Diosa JG, et al. Changes in the 3-D microscale topography of human skin with aging. PLoS One 2021;16:e0241533. doi:10.1371/journal.pone.0241533.
R10 Sun W, et al. Three-dimensional bioprinted skin microrelief and its role in skin aging. Biomimetics 2024;9:366. doi:10.3390/biomimetics9060366 (cites Leveque, EEMCO guidance, J Eur Acad Dermatol Venereol 1999;12:103-114).
R11 Pierard GE, et al. From microrelief to wrinkles. J Cosmet Dermatol 2004;2:21-28.
R12 Zahouani H, Ayadh M, Abellan MA, Bigouret A. Sci Rep 2024;14:31963. doi:10.1038/s41598-024-83490-5.
R13 Profilometry of skin, a useful tool for the substantiation of cosmetic efficacy. J Soc Cosmet Chem 1980;31:339 ff (review quoting Makki, Hoppe, Ferguson and Barbenel; authors not shown on page read).
R15 Jonsson EH, et al. Hair follicle density and touch perception. Sci Rep 2017;7:2499. doi:10.1038/s41598-017-02308-9.
R16 Otberg N, et al. Variations of hair follicle size and distribution in different body sites. J Invest Dermatol 2004;122:14-19. PMID 14962084.
R17 Kandi LA, et al. Montgomery tubercles and 3-D NAC tattooing. Am J Surg 2023;225:99-102. doi:10.1016/j.amjsurg.2022.11.005.
R18 Doucet S, Soussignan R, Sagot P, Schaal B. Areolar glands. Early Hum Dev 2012;88:119-128. PMID 21852053.
R19 Smith DM Jr, Peters TG, Donegan WL. Montgomery's areolar tubercle. Arch Pathol Lab Med 1982;106:60-63. PMID 6277270.
R20 Del Riego J, et al. Multimodality approach to the nipple-areolar complex. Insights Imaging 2020;11. doi:10.1186/s13244-020-00896-1.
R21 Lee JH, Yang JD, Chung KH, Chung HY, Cho BC. Anthropometric measurement for the nipple areola complex. Arch Plast Surg 2008;35:461-464.
R22 van Wingerden JJ. Nummular nipple hypertrophy. Aesthetic Plast Surg 1997;21:408-411. PMID 9354602.
R23 Love SM, Barsky SH. Anatomy of the nipple and breast ducts revisited. Cancer 2004;101:1947-1957. doi:10.1002/cncr.20559.
R24 Rusby JE, et al. Breast duct anatomy in the human nipple. Breast Cancer Res Treat 2007;106:171-179. doi:10.1007/s10549-006-9487-2.
R25 Jutte J, et al. Milk duct orifices in lactating women. BMC Pregnancy Childbirth 2014;14:124. doi:10.1186/1471-2393-14-124.
R26 Taneri F, et al. Microanatomy of milk ducts in the nipple. Eur Surg Res 2006;38:545-549. doi:10.1159/000096775.
R27 Dean N, et al. Nipple-areolar pigmentation: histology. Br J Plast Surg 2005;58:202-208. doi:10.1016/j.bjps.2004.10.027.
R28 Pawson IG, Petrakis NL. Comparisons of breast pigmentation among racial groups. Hum Biol 1975;47(4).
R29 Tomita S, Mori K, Miyawaki T. Color change after paramedical pigmentation of the NAC. Aesthetic Plast Surg 2018. doi:10.1007/s00266-017-1057-y.
R30 Lemperle G. Surgical incisions in main folding lines. Plast Aesthet Res 2020;7:40. doi:10.20517/2347-9264.2020.14.
R31 Nagano K, et al. Skin microstructure deformation with displacement map convolution. ACM Trans Graph 2015;34(4). doi:10.1145/2766894.
R32 Banba F, et al. Micro-geometric skin simulation for face impression analysis. NICOGRAPH International 2013.
R33 Wu Y, Tanaka T. Skin micro-relief by image analysis and age. Skin Res Technol 2021. doi:10.1111/srt.13060.
R34 Archibong OR, et al. Breast measurements of nulliparous women in Lagos. J West Afr Coll Surg 2022;11(4):1-6. doi:10.4103/jwas.jwas_81_22.
R36 Bourgeois JF, Gourgou S, Kramar A, Lagarde JM, Guillot B. Skin Res Technol 2008;14:71-76. doi:10.1111/j.1600-0846.2007.00263.x.
R37 Fuentes PM, et al. NAC reconstruction and tattooing review. Gland Surg 2026. doi:10.21037/gs-2025-aw-522.
