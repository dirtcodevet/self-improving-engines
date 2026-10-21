# Back sagittal profile (skin surface), healthy adult women, upright standing: normals for mesh checks

## How to measure it on a 3-D mesh (derived from the DIERS Formetric / Spinal Mouse / flexicurve definitions)
1. Pose the mesh upright (head Frankfurt-horizontal, arms off the trunk) and extract the midline sagittal profile along the spinous-process line (floor of the median furrow) from C7 (vertebra prominens, VP) down to DM (midpoint of the two sacral dimples, about S2); T12 = thoracolumbar landmark.
2. Smooth it (cubic spline or 3rd-order polynomial) and compute the tangent angle phi(s) from vertical along it; the inflection points (curvature changes sign) are ICT (cervical to thoracic), ITL (kyphosis to lordosis) and ILS (lordosis to sacral).
3. Kyphosis = |phi(ICT) - phi(ITL)|; lordosis = |phi(ITL) - phi(ILS)| (Formetric definition; ILS may be replaced by DM). Cross-check with fixed landmarks: kyphosis = tangent angle between C7(or T1) and T12, lordosis = between T12 and DM(or L5).
4. Hollow depth H = largest perpendicular distance from the chord ITL-to-ILS (or T12-to-DM, length L) to the profile; arc check: theta = 4*atan(2H/L), so H/L = tan(theta/4)/2 (flexicurve/Youdas form). Apex = point farthest from the VP-DM line (posterior for kyphosis, anterior for lordosis); report its vertebral level.
5. Women's check windows (my pooling of three Formetric 4D cohorts, n=315): kyphosis 46 +/- 9 deg, lordosis 43 +/- 9 deg. Lordosis above about 52 deg (+1 SD, H/L above 0.115) is high-normal; above about 61 deg (+2 SD, H/L above 0.136) is outside the healthy range. Compare to radiographic Cobb values only with matching landmarks (section 2).

Confidence key: strong = several independent studies agree; single = one study; weak = abstract/snippet only, unverified, or indirect. Compiled 2026-10-19 from open full texts (Europe PMC) and abstracts. Ages are mean years.

## 1. Surface-measured angles, women, standing (deg, mean +/- SD)
| Method and definition | Kyphosis | Lordosis | n women, age | Source | Conf |
|---|---|---|---|---|---|
| Formetric 4D, ICT-ITL / ITL-ILS tangents | 45.6 +/- 8.7 | 41.6 +/- 8.6 | 167-185, 26 | Bode 2024 | strong |
| Formetric III 4D, same, habitual stance | 47.3 +/- 8.5 (<=40 y 44.2 +/- 7.9; >40 y 50.4 +/- 7.9) | 43.8 +/- 9.1 (<=40 y 41.5 +/- 9.2; >40 y 46.1 +/- 8.6) | 100, 20-64 | Wolf 2021 | strong |
| Formetric 4D, same | 47.4 +/- 9.3 | 47.1 +/- 9.4 | 48, 28.8 | Colonna 2024 | strong |
| Formetric, tangent C7 to T12 / T12 to DM | 44.0 +/- 8.6 | 37.4 +/- 9.8 | 56, 23.6 | Michalik 2020 | single |
| Formetric, kyphosis only, cup size A/B/C/D | 47.9 / 49.3 / 53.9 / 56.7 (SD 10-13.5; weighted mean 51.8, mine) | not reported | 100, 32 | Michalik 2024 | single |
| ABW-BodyMapper video rasterstereo (C7 turning point to TL point; TL to PSIS marker), median | 56.3 (CI 54.7-57.8; 21-30 y 52.3) | 49.0 (CI 47.5-50.6) | 407, 21-60 | Ohlendorf 2023 | single (other device) |
| 3-D skin-marker spline, tangents at inflection points | 46.0 +/- 8.8 (range 25-76; both sexes, no sex split) | 44.2 +/- 9.7 (24-68); fixed T12-L5 39.5 +/- 9.0 | 57 of 124, 23.5 | D'Amico 2017 | single |
| 3-D skin markers, fixed segments (both sexes) | T1-T12 42.6 +/- 8.9; T4-T12 31.9 +/- 7.7 | - | 124, 24 | D'Amico 2017 | single |
| Spinal Mouse (Idiag), wheel trace C7-S3, sum of segment angles Th1-12 / lumbar | 46.3 (SE 2.3) | 29.6 (SE 2.2); sacral inclination 15.6 (SE 1.8) | 25, 27.5 | Bayartai 2025 | weak (n small) |
| Spinal Mouse, standing | 38.9 +/- 9.4 | 26.9 +/- 11.1; sacral 11.2 +/- 10.4 | 72, 18-28 | Hakuta 2007 (abstract) | weak |
| Flexicurve T12-S2 (Youdas), all ages / 20-29 y | - | 46.0 +/- 13.4 / 48.6 +/- 11.2 (n=200); 30-39 y 49.5 +/- 13.7 | 1264, 5-85 | Rajabi 2024 | single (large) |
| Flexicurve C7-S1, polynomial tangents at T1/T12 and L1/L5 | 42.9 +/- 8.8 | 40.0 +/- 7.9 | 47 mixed sex, 45 | de Oliveira 2012 | single |
| Rippstein inclinometer (C7/upper thoracic to TL; sacrum to TL) | 32.9 +/- 7.3 (12-58) | 30.1 +/- 7.3 (5-52) | 380, 20.7 | Grabara 2024 | single |
- Pooled Formetric ICT-ITL / ITL-ILS women (Bode, Wolf, Colonna; n=315, my weighted calc): kyphosis 46.4 +/- 8.8, lordosis 43.1 +/- 9.1.
- Sex: women's lordosis exceeds men's by 7-15 deg in every surface study (Bode 41.6 v 34.2; Michalik 37.4 v 29.0; Colonna 47.1 v 35.0; D'Amico 44.2 v 32.8; Rajabi 46.0 v 38.6; Grabara 30.1 v 23.6; Hakuta 26.9 v 17.4; Ohlendorf 49 v 32): strong. Kyphosis differs little (women 0-3 deg lower in Bode, Grabara).
- Age/BMI: kyphosis +6 deg from <=40 y to >40 y (Wolf); both angles rise with age and BMI (Ohlendorf 2023): single. Device or definition changes the answer by 10-20 deg, so never mix methods.
- Repeatability of Formetric: ICC 0.80-0.96 kyphosis, 0.91-0.95 lordosis, n=50 (Guidetti 2013): single.

## 2. Radiographic Cobb normals and surface-to-Cobb relation
| Cobb measure | Women | n, population | Source | Conf |
|---|---|---|---|---|
| T1-T12 kyphosis | 41.0 +/- 10.2 (men 43.7 +/- 9.0) | 96 F of 136, 20-69 (EOS), Japan | Hasegawa 2017 | single |
| L1-S1 lordosis | 55.1 +/- 10.3 (men 56.4 +/- 12.7) | same | Hasegawa 2017 | single |
| T4-T12 / L1-S1 / "LL" as listed (L1-L5 per methods) | 34.3 +/- 9.4 / 60.0 +/- 7.8 / 45.8 +/- 9.8 (men 35.3 / 54.9 / 42.7) | about 41 F of 100, 27, India | Sangondimath 2022 | single |
| Pooled adults, both sexes: thoracic / L1-L5 / L1-S1 | 95% CI of pooled mean 33.7-40.3 / 38.1-45.6 / 54.2-61.7 | 31 studies | Furlanetto 2018 | strong |
| Healthy <40 y, both sexes: T4-T12 / T1-T12 / T5-T12 | 33.9 +/- 4.9 / 39.8 +/- 5.9 / 26.3 +/- 4.3 (mean +/- SD across studies) | 34 studies, 7633 | Zappala 2021 | strong |
- Kyphosis rises with age (T4-T12 33.9 under 40 y to 47.6 over 60 y); Zappala found no pooled sex difference. Radiographic lordosis sex difference is mixed (Sangondimath +5 deg in women, p=.021; Hasegawa -1.3, ns); surface lordosis difference is consistent (section 1).
- Landmark effect (cross-cohort, not paired; my inference): skin tangents at fixed spinous levels land near Cobb (skin T1-T12 42.6 v Cobb 41.0 and 39.8; skin T4-T12 31.9 v 33.9; skin T12-L5 women 39.5 v L1-L5 38-46). Formetric ITL-ILS (43) sits 12-17 deg below L1-S1 (55-60) and ICT-ITL (46) sits 6-12 deg above T4-T12 (about 34).
- Paired, scoliosis teens (n=19, 14.5 y), Zebris spinous-process spline T1/T12/L5 tangents v Cobb: kyphosis bias +2.6 deg (limits -6.3 to +11.0, r=0.95); lordosis bias -2.5 deg (limits -17 to +12, r=0.76) (Takacs 2018): single.
- Flexicurve v Cobb: thoracic r=0.70, mean diff 0.8, absolute diff 6.5 deg; lumbar r=0.60, 0.5, 6.8 deg (de Oliveira 2012, n=47). Barrett 2018 (n=11): flexicurve reads 20.3 +/- 6.1 deg under Cobb (r=0.96), manual inclinometer +4.8 +/- 8.9 deg (r=0.86). Older adults: flexicurve needed x1.53 (not checked against full paper): weak.
- Rasterstereography v radiograph: r=0.68 (T2-T12) and 0.70 (C7-max) in Scheuermann teens, n=52 (Coneys 2025); meta-analysis of 19 studies validity rs>0.70, lower in healthy subjects than scoliosis (Krott 2020); Kinect surface index v Cobb: thoracic r=0.70, lumbar r=0.32, n=29 (Hannink 2022). Expect about 6-7 deg per-person error, correlation only moderate.

## 3. Profile as geometry
- Apex height: kyphosis apex T8 on skin (Formetric, 100 F; Wolf 2021) and T7 radiographic (Hasegawa 2017, 5.0 cm behind the gravity line); lordosis apex L3 on skin (Wolf 2021) and L4 radiographic (0.6 cm in front of the gravity line); kyphosis-to-lordosis crossover about L2 (Hasegawa; Wolf discussion). Strong for T7-T8 and L3-L4.
- Arc length of the skin curve (vertebral levels): kyphosis 10.25 +/- 1.11 (7-14, both sexes); lordosis women 6.84 +/- 1.36 (4-10) v men 7.9 +/- 1.34, so women's lordosis is shorter and tighter (D'Amico 2017): single.
- Trunk: VP-DM length women 452 +/- 27 mm (Michalik 2020); VP-DM forward lean 1.8-3.2 deg (Colonna, Michalik, Wolf 3.1 +/- 2.1 deg, Bode 3.2 +/- 2.2 deg): strong.
- Plumb-line depth (tangent to thoracic kyphosis apex; n=584 of 341 F, ages about 6-20, normal x-rays; sexes pooled): at C7 39.9 +/- 16.7, T12 21.4 +/- 15.3, L3 39.9 +/- 15.0, S2 20.6 +/- 17.0 mm; sagittal index (C7+L3) 79.8 +/- 26.8, r=0.47 with Cobb kyphosis (Negrini 2019): single, adolescent. An adult "30-50 mm" fleche range appears only in an unsourced glossary entry: weak, do not rely on it.
- No measured hollow depth from a scapula-to-buttock line, no radius of curvature, and no chord-based skin sagitta for adult women were found. Derived from the angle by the arc formula (computed here, not measured), H/L for lordosis 34 / 43 / 52 / 61 deg = 0.075 / 0.095 / 0.115 / 0.136; for a T12-to-DM chord of about 190-230 mm (my estimate) H = 14-17 / 18-22 / 22-27 / 26-31 mm. Radius R = L/(2 sin(theta/2)), or S/theta for arc length S.
- Consistent indirect checks: Kinect lumbar index (depth/chord x 100, chord L1 to PSIS midpoint) 8.6 +/- 4.0, so H/L about 0.09 (n=29 clinical, 76% F; Hannink 2022): weak. MRI lumbar offset distance (internal, L3 posterior cortex to L1-L5 chord) 9.6 +/- 3.6 mm in normal lordosis (LLA 31.9 +/- 7.0), range 5-15 mm, supine, mean age 55, n=78 of 101 (Shirodkar 2024): weak, not skin.
- Whole-trunk AP depth, women, 19-23 y (3-D torso scan, n=62): T1 124 +/- 21, T4 165 +/- 24, T8 207 +/- 27, T12 203 +/- 32 mm (Zurawski 2025): single, includes chest, not hollow depth.

## 4. Pelvic tilt / sacral slope as seen at the skin
| Measure | Women | n, age | Source | Conf |
|---|---|---|---|---|
| Formetric pelvic inclination (tilt of surface normals at the dimples; positive = anterior tilt) | 25.5 +/- 7.5 (men 16.7 +/- 6.8) | 167-185, 26 | Bode 2024 | strong |
| same | 25.3 +/- 5.2 (men 16.1 +/- 5.1) | 48, 28.8 | Colonna 2024 | strong |
| same | 18.7 +/- 9.0 (<=40 y 20.5 +/- 8.0; >40 y 16.9 +/- 9.6) | 100, 20-64 | Wolf 2021 | strong |
| Spinal Mouse sacral inclination (vertical-referenced) | 11.2 +/- 10.4; 15.6 (SE 1.8) | 72, 18-28; 25, 27.5 | Hakuta 2007; Bayartai 2025 | weak |
| ASIS-PSIS line v horizontal (caliper inclinometer) | 12.2 +/- 5.2 R, 11.8 +/- 4.5 L; 11.7 +/- 3.8 (2-19); men 8.6-9.6 | n not stated | Nguyen & Shultz 2007; McKeon & Hertel 2009, quoted in Suits 2021 | weak (secondary) |
| Radiographic sacral slope / pelvic tilt / pelvic incidence | 40.7 +/- 7.8 / 12.2 +/- 7.8 / 52.9 +/- 10.7; 41.8 +/- 6.0 / 15.3 +/- 8.6 / 56.7 +/- 11.7 | 96 F Japan; about 41 F India | Hasegawa 2017; Sangondimath 2022 | single each |
- Women have more anterior pelvic tilt than men by about 4-9 deg (Bode, Colonna, ASIS-PSIS); Formetric pelvic inclination correlates with lordotic angle r=0.72 (Bode 2024, both sexes): strong that more tilt goes with more hollow. ASIS-PSIS angle varies 0-23 deg (13 +/- 5) with pelvic shape alone in 30 cadaver pelves (Preece 2008, snippet): weak.

## 5. Transverse back shape (spinal furrow)
- No study reporting the depth (mm) of the skin furrow between the paraspinal muscles in healthy women was found (Europe PMC, PubMed, web). A laser-triangulation paper (n=24 scoliosis patients, 21 F) uses the median furrow only as a landmark line: manual v automatic curve RMS 4.6 +/- 1.5 mm frontal, 0.9 +/- 0.4 mm sagittal, no depth (Poredos 2015). An MRI conference poster defines a "T-back" groove value but gives only counts of flat/negative values in elderly (women 22%, men 13%, mean age 68; Takayama 2015): weak. Treat furrow depth as unconstrained by data; any value used is an art choice, not a normal.

## References
Bode T et al. Heliyon 2024;10(7):e29239, doi 10.1016/j.heliyon.2024.e29239, PMID 38633646. | Wolf C et al. J Orthop Surg Res 2021;16:703, doi 10.1186/s13018-021-02843-2, PMID 34863230. | Colonna S et al. Cureus 2024;16(3):e55586, doi 10.7759/cureus.55586. | Michalik R et al. J Orthop Surg Res 2020;15:389, doi 10.1186/s13018-020-01825-0, PMID 32900390. | Michalik R et al. Aesthetic Plast Surg 2022/24, doi 10.1007/s00266-022-03141-w, PMID 36280605. | Ohlendorf D et al. Sci Rep 2023;13:873, doi 10.1038/s41598-023-27976-8. | D'Amico M, Kinel E, Roncoletta P. PLoS One 2017;12(6):e0179619, doi 10.1371/journal.pone.0179619, PMID 28640899. | Bayartai ME et al. J Clin Med 2025;14(11):3723, doi 10.3390/jcm14113723. | Hakuta R, Sato M. Yamanashi Nursing J 2007;5(2):13-18 (English abstract only). | Mannion AF et al. Eur Spine J 2004;13(2):122-136 (Spinal Mouse method; values not retrieved). | Rajabi R et al. Asian Spine J 2024;18(6):836-845, doi 10.31616/asj.2024.0317, PMID 39587422. | de Oliveira TS et al. Rehabil Res Pract 2012;2012:186156, doi 10.1155/2012/186156. | Grabara M, Witkowska A. Sci Rep 2024;14:12221, doi 10.1038/s41598-024-62929-9, PMID 38806548. | Guidetti L et al. Biomed Res Int 2013;2013:745480, doi 10.1155/2013/745480, PMID 23819119. | Hasegawa K et al. J Anat 2017;230(5):619-630, doi 10.1111/joa.12586. | Sangondimath G et al. Asian Spine J 2022;16(1), doi 10.31616/asj.2020.0301, PMID 33957746. | Furlanetto TS et al. Motricidade 2018;14(2-3):115-128, doi 10.6063/motricidade.10890. | Zappala M et al. J Orthop Surg Res 2021;16:447, doi 10.1186/s13018-021-02592-2. | Takacs M et al. PLoS One 2018;13(7):e0200245, doi 10.1371/journal.pone.0200245. | Barrett E et al. Physiother Theory Pract 2018;34(4):301-308, doi 10.1080/09593985.2017.1394411. | Coneys U et al. Eur Spine J 2025;34(3):831-836, doi 10.1007/s00586-024-08610-1. | Krott NL et al. Eur Spine J 2020;29(9):2392-2401, doi 10.1007/s00586-020-06402-x, PMID 32277336. | Hannink E et al. Spine Deform 2022;10(6):1299-1306, doi 10.1007/s43390-022-00538-0, PMID 35809201. | Negrini A et al. Phys Ther 2019;99(12):1712-1718, doi 10.1093/ptj/pzz123, PMID 31504925. | Shirodkar K et al. J Craniovertebr Junction Spine 2024, doi 10.4103/jcvjs.jcvjs_40_24, PMID 39483832. | Zurawski AL et al. Sensors 2025;25(21):6626, doi 10.3390/s25216626. | Suits WH. Int J Sports Phys Ther 2021;16(5), doi 10.26603/001c.27978. | Preece SJ et al. Man Ther 2008 (via search snippet; not opened). | Poredos P et al. BMC Med Imaging 2015;15, doi 10.1186/s12880-015-0044-5, PMID 25651841. | Takayama K et al. ECR 2015 poster C-0802. | Landmark definitions (ICT/ITL/ILS/KA/LA): Wilczynski J. J Clin Med 2025;14(2):501, doi 10.3390/jcm14020501 (children's data, used for definitions only).
