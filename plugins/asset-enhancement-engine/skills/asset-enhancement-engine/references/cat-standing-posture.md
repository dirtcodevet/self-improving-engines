# Cat standing posture: sourced values for the quiet-stance frame

**What this is for:** sourced joint angles, segment tilts, joint heights, soft-tissue depths and withers height. They are for fitting the simplified skeleton ("frame") of an adult domestic cat standing still on four paws. Bone lengths are in `cat-skeleton-muscle.md` (Poradowski 2024).

Compiled 2026-10-17 from web pages, PMC/publisher HTML, published figure images and scanned journal pages. Two PDFs were auto-cached by the fetch tool (see the end of this file).

**Confidence tags**
- **[M]** Measured in the study. I read the number in the text or a table on the cited page.
- **[F]** Measured in the study, but published only as a graph. I read it off the figure; precision is about ±3° or ±0.5 cm.
- **[B]** Read only in an abstract or an API abstract summary. The full text was not opened.
- **[D]** Derived by me from sourced numbers. The method is stated each time.
- **NOT FOUND** Searched for, nothing usable located. No estimate is given.

---

## Key sources

| Short name | Citation | Where read |
|---|---|---|
| **Fung & Macpherson 1999** | Fung J, Macpherson JM (1999). Attributes of quiet stance in the chronic spinal cat. *J Neurophysiol* 82(6):3056-3065. doi:10.1152/jn.1999.82.6.3056. **This is the only quiet-stance source with joint angles that I could open.** It reports intact cats (pre-spinalization) as controls. | Full text HTML: https://journals.physiology.org/doi/full/10.1152/jn.1999.82.6.3056 . Figure images: `.../asset/images/large/9k1290637001.jpeg` (Fig. 1), `...004.jpeg` (Fig. 4), `...005.jpeg` (Fig. 5) |
| Fung & Macpherson 1995 | Fung J, Macpherson JM (1995). Determinants of postural orientation in quadrupedal stance. *J Neurosci* 15(2):1121-1131. | **Abstract only** (Europe PMC API). The full text (PMC6577830 PDF, jneurosci.org) was blocked by a 403 error or a bot-verification page, so its numbers were **not read**. |
| Lacquaniti et al. 1990 | Lacquaniti F, Le Taillanter M, Lopiano L, Maioli C (1990). The control of limb geometry in cat posture. *J Physiol* 426:177-192. | Scanned pages on PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC1189882/ (pages 179-184 viewed as images) |
| Day & Jayne 2007 | Day LM, Jayne BC (2007). Interspecific scaling of the morphology and posture of the limbs during the locomotion of cats (Felidae). *J Exp Biol* 210:642-654. | https://journals.biologists.com/jeb/article/210/4/642/17244/Interspecific-scaling-of-the-morphology-and |
| Carlson-Kuhta et al. 1998 | Carlson-Kuhta P, Trank TV, Smith JL (1998). Forms of forward quadrupedal locomotion. II. *J Neurophysiol* 79:1687-1701. | https://journals.physiology.org/doi/full/10.1152/jn.1998.79.4.1687 |
| Kuhtz-Buschbeck et al. 1994 | Kuhtz-Buschbeck JP, Boczek-Funcke A, Illert M, Weinhardt C (1994). X-ray study of the cat hindlimb during treadmill locomotion. *Eur J Neurosci* 6(7):1187-1198. | [B] Europe PMC API abstract: https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=AUTH:%22Boczek-Funcke%20A%22&resultType=core&format=json&pageSize=25 |
| Zanna et al. 2017 | Zanna G, Zini E, Scarampella F, Attanasi A, Arrighi S, Auriemma E (2017). Ultrasonography as a complementary diagnostic method for evaluating the skin of healthy cats. *Can J Vet Res* 81(4):292-296. | https://pmc.ncbi.nlm.nih.gov/articles/PMC5644443/ |
| Iwazaki & Nade 2020 | Iwazaki E, Nade T (2020). Evaluation of ultrasound assessments of subcutaneous adiposity and epaxial muscularity in cats: a preliminary study. *Jpn J Vet Res* 68(1):35-45. | PDF (auto-cached; text extracted locally): https://eprints.lib.hokudai.ac.jp/repo/huscap/all/76752/JJVR68-1_35-45_EijiIwazaki.pdf |
| Poradowski et al. 2024 | Poradowski D, Mutlu Z, Altundağ Y, Chrószcz A, Sarıtaş Ö, Wolińska J, Onar V (2024). Estimation of height at withers based on long bone measurements of living cats. *Vet Sci* 11(11):522. | https://pmc.ncbi.nlm.nih.gov/articles/PMC11598937/ |

**Fung & Macpherson 1999: setup** [M]
- **Cats.** Four adult males: Ru 3.9 kg, Ni 4.8 kg, Re 3.8 kg, Go 4.36 kg.
- **Task.** Each cat stood unrestrained on four force plates, quiet stance, at five fore-hind plate distances.
- **Preferred stance distance.** Measured from the cats' natural stance on the floor: 29 cm for Ru and Ni, 28 cm for Re and Go.
- **What "stance distance" means.** The MCP marker to MTP marker distance (AP distance).
- **Markers.** Optotrak markers on the skin over bony landmarks, left side: scapula, shoulder (glenohumeral), elbow, wrist, MCP, iliac crest ("pelvis"), hip, knee, ankle, MTP.
  - Loose-skin sites (knee, shoulder, scapula) were marked with the cat standing.
  - Joint radius, skin depth and marker-base thickness were subtracted along the mediolateral axis only.
- **Results.** All angle results below are the **intact (black) data**.

---

## 1. Hindlimb joint angles in quiet stance

### 1a. Quiet stance: Fung & Macpherson 1999, Fig. 5B
**Sample and reading** [F]
- **Cat.** One cat (Re, 3.8 kg, intact). Values are at AP distance 28 cm, Re's preferred distance.
- **Read from.** The black regression or LOWESS line of Fig. 5B.
- **Same values for all four cats?** Not available. Only this cat's joint angles are plotted.

**Angle definitions** [M] [D]
- **What the paper states.** Fig. 5 legend: figurines show each definition, and increases mean extension [M].
- **Side of measurement.** I read the measuring side off the figurines (cat drawn facing left). The full chain closes (section 7), which supports these readings [D].

| Angle | Value | Definition |
|---|---|---|
| Pelvis (segment) | ≈113° | Hip marker → iliac-crest marker, measured from the **caudal-pointing horizontal**. The pelvis line therefore rises about 67° above the cranial horizontal [D]. |
| Hip (joint) | ≈121° (119-123) | Inter-segment angle between the pelvis segment and the femur (hip → knee), cranial side |
| Knee / stifle (joint) | ≈90° | Inter-segment angle, femur to tibia (knee → ankle), caudal side |
| Ankle / hock (joint) | ≈140° | Inter-segment angle, tibia to hind-paw segment (ankle → MTP), cranial side |
| Hind paw (segment) | ≈102° | Ankle → MTP segment, measured from the caudal horizontal. The metatarsus is about 78° to the ground [D]. |
| MTP (joint) | **NOT FOUND for quiet stance** | Fung reports the paw segment, not an MTP joint angle |

**How the angles change with stance distance** (17 → 37 cm, cat Re) [F]
- Pelvis 102 → 122°
- Hip 113 → 120°, with a shallow peak
- Knee about 91°, flat
- Ankle 122 → 148°
- Hind paw 73 → 127°

So the hind-paw and ankle angles depend strongly on how far apart the paws are. The knee and hip do not.

**What the text says** [M]
- Intact cats keep the trunk horizontal. Hindlimbs are "semiflexed" in quiet stance.
- When the stance lengthens, the limb rotates mainly at the pelvic segment. The hip angle stays nearly constant.

### 1b. Comparators from walking: stance-phase values, not quiet stance

**Day & Jayne 2007, Table 5: midstance** [M]
- **Sample.** n = 4 cats, 16 strides, 3.7 ± 0.2 kg, overground walking at 80 ± 3 cm/s. Values are mean ± s.e.m.
- **Markers.** Paper stickers on the fur over palpated joints.
- **Convention.** Inter-segment angle; 180° = straight.
- **Joint angles at midstance.**
  - Knee 115 ± 3°
  - Ankle 114 ± 3°
  - MTP 112 ± 2°
  - At footfall: knee 130, ankle 118, MTP 140.
- **Hip angle.** Not measured.
- **Segment angles from vertical at midstance (Table 6).** Positive means the distal end is cranial to the proximal end.
  - Femur +13 ± 2°
  - Tibia −51 ± 2°
  - Metatarsal +13 ± 2°

**Carlson-Kuhta et al. 1998, Table 2: level treadmill walking, 0% grade** [M]
- **Sample.** 0.6 m/s; 20 steps (5 per cat × 4 cats). Values are mean ± SD.
- **Segments (Fig. 3).** Pelvis = anterior iliac crest to hip; thigh = hip to knee; shank = knee to ankle; paw = ankle to MTP of the 5th digit; digits = MTP to the distal phalanx of the 4th digit.

| Joint | Paw contact | Stance yield → extension reversal | Peak extension | Liftoff |
|---|---|---|---|---|
| Hip | 83 ± 10° | (not listed) | 135 ± 10° | 127 ± 12° |
| Knee | 120 ± 6° | 105 ± 6° | 121 ± 3° | 114 ± 3° |
| Ankle | 116 ± 9° | 105 ± 8° | 140 ± 5° | 136 ± 5° |
| MTP | 215 ± 7° | (not listed) | 260 ± 7° | 199 ± 5° |

- **MTP convention.** Carlson-Kuhta's MTP values sit above 180°, so they are measured on the side opposite to Day & Jayne's. 360 − 248 = 112°, the Day & Jayne midstance value [D].

**Kuhtz-Buschbeck et al. 1994: X-ray, bone-based** [B]
- The MTP angle went from about 230° at touchdown to about 270° at the end of stance.
- The PIP joint stayed at about 75° through most of stance.

### 1c. Requested sources not read
- **Fung & Macpherson 1995.** Full text blocked. The abstract states only that the trunk stays horizontal and intralimb geometry stays constant across stance distance [B].
- **Macpherson 1988; Goslow, Reinking & Stuart 1973.** Not accessed (paywalled; no free full text found).
- **Lacquaniti & Maioli 1994** (*J Neurophysiol* 72:1476). Subscriber-only; the abstract gives no angles.

---

## 2. Forelimb and scapula in quiet stance

### 2a. Quiet stance: Fung & Macpherson 1999, Fig. 5A
Same cat (Re), 28 cm, intact, same conventions as 1a. [F]

| Angle | Value | Definition |
|---|---|---|
| **Scapula inclination (segment)** | **≈61°** (black line about 62; points 58-63) | Shoulder (glenohumeral) marker → scapula marker, measured from the **caudal-pointing horizontal**. The dorsal scapula lies caudodorsal to the shoulder joint (Fig. 1A) [M]. A higher value means closer to vertical: the text says the spinal-cat scapula was "closer to vertical", and those values are higher [M]. |
| Shoulder (joint) | ≈128° | Inter-segment angle, scapula segment to humerus (shoulder → elbow), caudal side |
| Elbow (joint) | ≈150° | Inter-segment angle, humerus to forearm (elbow → wrist), cranial side |
| Wrist (joint) | ≈178° (essentially straight) | Inter-segment angle, forearm to fore-paw segment (wrist → MCP) |
| Fore paw (segment) | ≈84° | Wrist → MCP segment, measured from the horizontal. The metacarpus is about 6° off vertical [D]. |

**How the angles change with stance distance** (17 → 37 cm) [F]
- Scapula about 63 → 58°
- Shoulder about 124-130°
- Elbow 155 → 145°
- Wrist about 177-184°
- Fore paw 97 → 71°

**What the text says** [M]
- Forelimbs are "almost fully extended" in quiet stance.
- The forelimb is held habitually near maximum extension; the hindlimb is semiflexed.

**Scapula landmark** [M]
- The text does not name the exact scapular landmark; Fig. 1A draws the "Scapula" marker at the dorsal end of the scapula.
- It is a skin marker, not a radiographic bone measurement.

### 2b. Corroborating quiet-stance note: Lacquaniti et al. 1990 [M]
- **Wrist.** The wrist was left out of their analysis because it was fully extended under all conditions (p. 181).
- **Sample.** 4 female cats, 1.9-2.4 kg, standing on a platform.
- **Forelimb axis landmark.** It starts at the top of the scapular spine: the "upper end-point of the scapular spine", chosen as the forelimb's proximal pivot.

### 2c. Comparators from walking: Day & Jayne 2007, midstance [M]
- **Joint angles (Table 5).**
  - Elbow 127 ± 2°
  - Wrist 176 ± 3°
  - MCP 107 ± 2°
  - At footfall: 129, 184, 133.
- **Segment angles from vertical (Table 6).**
  - Humerus −45 ± 2°
  - Radius/ulna +8 ± 1°
  - Metacarpal +11 ± 2°
- **Not measured.** Scapula and shoulder joint angle.

### 2d. Scapula inclination from X-ray
**NOT FOUND.**
- **Boczek-Funcke, Kuhtz-Buschbeck & Illert 1996** (*Eur J Neurosci* 8:261-272). Two cats on a treadmill. The abstract gives no scapula angles [B]. Full text paywalled.
- **Fischer & Blickhan 2006** (*J Exp Zool* 305A:935). Not accessed; no cat scapula value found in search results.
- **Zhang et al. 2012** (*PLoS One* e34619) has no cat scapula orientation value (checked on page) [M].

---

## 3. Joint heights and limb axes in stance

### 3a. Quiet stance: Fung & Macpherson 1999, Fig. 4
Cat Ni, 4.8 kg, intact, near the preferred 29 cm. [F]

| Quantity | Value | Definition |
|---|---|---|
| **Shoulder (glenohumeral) joint height** | **≈22 cm** (flat across 20-39 cm stance) | Vertical height of the shoulder marker above the support surface (Fig. 4H) |
| **Hip joint height** | **≈22 cm** (about 23 at 20 cm, about 21 at 39 cm) | Vertical height of the hip marker (Fig. 4I) |
| Trunk axis (shoulder joint → hip joint) | ≈0-1° to horizontal | Fig. 4G |
| Forelimb axis (shoulder joint → MCP) orientation | ≈91° at 29 cm (about 106 at 15 cm → about 75 at 45 cm) | Measured from the horizontal; 90 = vertical. Values above 90 appear to mean the paw is caudal to the shoulder: inferred from the text, where the spinal cats "incline the forelimb axis more forward" and have higher values [D]. |
| Hindlimb axis (hip → MTP) orientation | ≈96° at 29 cm (about 73 at 15 cm → about 122 at 45 cm) | Same convention |
| Limb axis lengths | Not plotted in 1999; **NOT FOUND** | |

- **Paper's statement** [M]. Trunk orientation and the heights of the shoulder and hip stayed constant across stance distance.
- **Is the height a joint centre?** The correction for joint radius and skin depth was applied along the mediolateral (x) axis only. The height is therefore the height of the skin marker over the joint. That counts as a joint-centre height only to the extent the marker sits level with the centre [M].

### 3b. Quiet stance: Lacquaniti et al. 1990, Table 1
Four female cats (1.9-2.4 kg) on a horizontal platform; the regression intercept at 0° tilt. [M]

**Axis definitions**
- **Forelimb axis.** Top of the scapular spine → paw contact point.
- **Hindlimb axis.** Hip → paw contact point.
- **Paw contact point.** The ground projection of the marker on the proximal interphalangeal joint of digit V.
- **Orientation.** Measured from the horizontal, counter-clockwise positive.

| Cat | Forelimb axis length | Hindlimb axis length | Forelimb orientation | Hindlimb orientation |
|---|---|---|---|---|
| 1 | 23.78 cm | 19.62 cm | 93.36° | 90.22° |
| 2 | 22.54 | 16.98 | 86.80 | 86.72 |
| 3 | 24.10 | 15.22 | 83.68 | 91.90 |
| 4 | 22.90 | 16.06 | 86.00 | 87.88 |
| **Mean [D]** | **23.3 cm** | **17.0 cm** | **87.5°** | **89.2°** |

- **What the abstract says.** The limb axes stay close to vertical.
- **Size caveat.** These are small females, and the forelimb axis includes the scapula.

### 3c. Comparators from walking: Day & Jayne 2007, Table 6, midstance [M]
- **Shoulder height** = 74 ± 2 % of forelimb length; **hip height** = 77 ± 2 % of hindlimb length.
- **Limb lengths.** FLL is 24 ± 1 cm and HLL is 33 ± 1 cm, each a sum of the segments: humerus to phalanges, femur to phalanges.
- **Derived heights** [D]. Shoulder joint about 17.8 cm and hip about 25.4 cm while walking. This is a walking crouch and does not match the level, equal-height quiet stance in 3a.

### 3d. Heights of the other joints
**NOT FOUND.** No numeric height was found in any source for the elbow, wrist, MCP, knee, ankle or MTP during stance.

---

## 4. Soft tissue over the skeleton

### 4a. Skin thickness: Zanna et al. 2017 [M]
- **Method.** 18-MHz ultrasound, hair clipped to 1 mm. Epidermal entry echo + dermis only; **subcutis excluded**.
- **Sample.** n = 21 adult DSH, 1.9-6 kg (median 3.1 kg).

| Site | Median (range) |
|---|---|
| Dorsal neck (C2-C3 junction) | 1.7 mm (1.1-2.2); males 1.7, females 1.5 |
| **Sacral (midway between the tubera coxae) ≈ croup** | **1.4 mm (1.0-1.9)**; males 1.6, females 1.4 |
| Frontal | 1.4 mm (0.8-2.0) |
| Abdominal (linea alba) | 1.0 mm (0.8-1.5) |

- **Ultrasound vs histology.** Ultrasound read about 13 % thicker than histology (median; range −30 to +53 %).
- **Textbook range (secondary).** Zanna cites Muller & Kirk (2013): general body skin is 0.4-2 mm, thickest on the back and dorsal neck [M, secondary].
- **Withers (between the scapulae) and mid-back skin thickness.** **NOT FOUND.**

### 4b. Subcutaneous fat and epaxial muscle beside the spine: Iwazaki & Nade 2020 [M]
I extracted the text from the cached PDF; some table cells came out unreadable.

**Method**
- Ultrasound, cat in lateral recumbency, **hair not clipped**.
- Transducer parallel to the rib and centred over the longissimus: **paramedian, not over the spinous processes**.
- **Back fat (BF).** From the inner limit of the dermis to the fascia of the latissimus dorsi (6-7th rib) or the serratus posterior (just caudal to the 13th rib).
- **Sample (Experiment 1).** Lean 2.6 ± 0.1 kg (n = 10); ideal 3.5 ± 0.2 kg (n = 5); overweight 4.4 ± 0.1 kg (n = 5). Values are mean ± SE.

| Measure | Lean | Ideal BW | Overweight |
|---|---|---|---|
| Back fat, 6-7th rib (≈ caudal withers / cranial mid-back) | 0.2 ± 0.1 mm | 0.2 ± 0.1 mm | 0.3 ± 0.1 mm |
| Back fat, caudal to the 13th rib (thoracolumbar) | 1.7 mm | 2.7 ± 0.2 mm | 3.9 ± 0.4 mm |
| Epaxial muscle depth, 6-7th rib | 11.9 mm | 14.9 ± 0.9 mm | 16.0 ± 1.2 mm |
| Epaxial (longissimus) depth, caudal to the 13th rib | 12.3 mm | 14.1 mm | unreadable in extraction |

- **Experiment 2** (10 cats, 3.3 ± 0.3 kg). Back fat at the 13th rib 1.6 ± 0.2 mm; longissimus depth at the 13th rib 12.3-12.7 mm.

### 4c. Distance from the vertebrae to the dorsal skin
**NOT FOUND.**
- **What was searched for.** The distance from the spinous-process tips (or vertebral bodies) to the dorsal skin, at the withers, mid-back and croup.
- **Result.** No cat CT or radiograph study with this number was located.
- **Nearest material.**
  - Okada et al. 2019 (*Front Vet Sci*). CT of the subcutaneous fat at L3/L5/L7 in 10 cats, reported as areas (cm²), not depths. Seen only in search results; not opened [B].
  - Dog CT skin-to-epidural studies exist; they were not used.
- **Related anatomy** (already in `cat-skeleton-muscle.md`). In a standing cat, the dorsal border of the scapula rises above the thoracic spines [S, Macpherson & Ye 1998 abstract]. So the withers skin line is set by the scapulae, not by the spinous processes.

---

## 5. Withers height of adult domestic cats

| Population | Withers height | n | How measured | Source |
|---|---|---|---|---|
| **Adult European-shorthair-type cats, 3-5 y, not overweight** | **25.98 ± 2.57 cm** (mean ± SD) | 37 | Live animals. Measured with a zoometric stick (stated in the Simple Summary), on the external body surface. **The exact landmark and posture are not stated.** | [M] Poradowski et al. 2024, Table 1 |
| — females | 24.68 ± 2.4 cm | 17 | same | [M] same |
| — males | 27.09 ± 2.21 cm | 20 | same | [M] same |
| Angora cats, Ankara Zoo | males 23.20 ± 0.583 cm; females 22.60 ± 0.354 cm | 5 M, 28 F | The method is not stated in the abstract. **The ± is probably SE** (it is too small for an SD), but this is unverified. | [M] Doctoral thesis, Ankara Univ. Fen Bilimleri Enstitüsü, 2007 (the author is not shown on the record page): https://dspace.ankara.edu.tr/items/51072762-e18f-4a1a-bfc7-9a74cf2841a9 |

- **Typo in Poradowski Table 4.** The radius "R" total reads 2.59 ± 2.48; it is clearly meant to be about 26.
- **Poradowski bone lengths** (humerus 10.06, radius 9.74, femur 10.81, tibia 11.38 cm) come from the same cats. These are the engine's existing size-factor-1.0 lengths, so this withers height is the matching one.
- **Skin or bone?** Neither study measured withers height on bone. Both are external measurements on the live cat. **A bone-referenced withers height (top of the scapula or the T1-T3 spines) was NOT FOUND.**

---

## 6. Master table of values

| # | Quantity (quiet stance unless marked) | Value | Definition | Source | Conf. |
|---|---|---|---|---|---|
| 1 | Hip joint angle | ≈121° | Pelvis segment (hip → iliac crest) to femur, cranial side | Fung & Macpherson 1999, Fig. 5B, cat Re, 28 cm | F |
| 2 | Knee / stifle angle | ≈90° | Femur to tibia, caudal side | same | F |
| 3 | Ankle / hock angle | ≈140° | Tibia to metatarsus (ankle → MTP), cranial side | same | F |
| 4 | Hind-paw (metatarsus) segment | ≈102° from caudal horizontal (≈78° to ground) | Ankle → MTP vs horizontal | same | F (+D) |
| 5 | Pelvis segment | ≈113° from caudal horizontal (≈67° above cranial horizontal) | Hip → iliac crest vs horizontal | same | F (+D) |
| 6 | MTP joint angle | NOT FOUND (quiet). Walking midstance 112 ± 2° (180 = straight); walking stance 215-260° on the opposite-side scale | Metatarsal to phalanges | Day & Jayne 2007 T5; Carlson-Kuhta 1998 T2 | M (walking) |
| 7 | Scapula inclination | ≈61° above horizontal, dorsal end caudal | Shoulder joint → scapula marker vs caudal horizontal | Fung & Macpherson 1999, Fig. 5A, cat Re | F |
| 8 | Shoulder joint angle | ≈128° | Scapula to humerus, caudal side | same | F |
| 9 | Elbow angle | ≈150° | Humerus to forearm, cranial side | same | F |
| 10 | Wrist angle | ≈178° (straight); "fully extended" | Forearm to metacarpus | Fung 1999 Fig. 5A; Lacquaniti 1990 p. 181 | F; M |
| 11 | Fore-paw (metacarpus) segment | ≈84° from horizontal | Wrist → MCP vs horizontal | Fung 1999 Fig. 5A | F |
| 12 | Shoulder (glenohumeral) height | ≈22 cm | Marker height above the support | Fung 1999 Fig. 4H, cat Ni 4.8 kg | F |
| 13 | Hip joint height | ≈22 cm | Marker height above the support | Fung 1999 Fig. 4I, cat Ni | F |
| 14 | Trunk axis (shoulder → hip) | ≈0° (horizontal) | Line joining the shoulder and hip joints | Fung 1999 Fig. 4G; abstracts of 1995 and 1999 | F; M |
| 15 | Forelimb / hindlimb axis orientation | ≈91° / ≈96° at the preferred distance | Shoulder → MCP / hip → MTP vs horizontal | Fung 1999 Fig. 4A, D | F |
| 16 | Forelimb / hindlimb axis length and orientation (small females) | 23.3 cm / 17.0 cm; 87.5° / 89.2° (means of 4) | Scapular-spine top → paw contact / hip → paw contact | Lacquaniti 1990 Table 1 | M (means D) |
| 17 | Preferred fore-hind paw distance | 28-29 cm (MCP to MTP) | Natural stance on the floor | Fung 1999 Methods | M |
| 18 | Skin thickness, croup (sacral) | 1.4 mm median (1.0-1.9) | Epidermis + dermis, ultrasound | Zanna 2017 | M |
| 19 | Skin thickness, dorsal neck (C2-C3) | 1.7 mm median (1.1-2.2) | same | Zanna 2017 | M |
| 20 | Back fat, 6-7th rib / caudal to the 13th rib | 0.2-0.3 mm / 1.7-3.9 mm (lean → overweight) | Dermis to muscle fascia, paramedian | Iwazaki & Nade 2020 Table 1 | M |
| 21 | Epaxial muscle depth, 6-7th rib | 11.9-16.0 mm | Ultrasound | Iwazaki & Nade 2020 | M |
| 22 | Spinous-process tip → skin distance | NOT FOUND | | | — |
| 23 | Withers height | 25.98 ± 2.57 cm (n = 37) | External, zoometric stick | Poradowski 2024 Table 1 | M |

---

## 7. Derived consistency check [D]

**Method**
- I chained the Fung 1999 Fig. 5 angles for cat Re, using the side conventions in sections 1 and 2.
- Lengths: Poradowski bone lengths, plus the Day & Jayne segment lengths already in `cat-skeleton-muscle.md` (metatarsal segment about 73 mm, carpus + metacarpus about 34 mm).
- This only checks that the conventions are read correctly. It is not a measurement.

**Hindlimb**
- **Segment tilts.**
  - Pelvis line 67° above the cranial horizontal.
  - Hip 121° → femur runs cranioventrally at about 54° below horizontal.
  - Knee 90° → tibia runs caudoventrally at about 36° below horizontal.
  - Ankle 140° → metatarsus about 76° to the ground, ankle slightly cranial of the MTP.
- **Closure.** The figure's own hind-paw reading (102°, i.e. 78°) closes the chain within about 2°.
- **Hip height.** Vertical drops 87 + 67 + 71 mm = 225 mm plus the MTP joint height, against about 220 mm measured (cat Ni). Bone lengths are greatest lengths, so a slight overshoot is expected.

**Forelimb**
- **Segment tilts.**
  - Scapula 61°.
  - Shoulder 128° → humerus caudoventral at about 67° below horizontal.
  - Elbow 150° → forearm about 7° off vertical, wrist cranial of the elbow.
  - Wrist about 180° → metacarpus about 5-9° off vertical.
- **Closure.** The figure's fore-paw reading (84°, i.e. 6° off vertical) closes the chain within about 3°.
- **Shoulder height.** 93 + 96 + 34 mm = 223 mm plus the MCP height, against about 220 mm measured.

**Scapula top**
- A 71 mm scapula at 61° rises about 62 mm above the shoulder joint, so its top is about 282 mm above the ground.
- That is within one SD of the male withers height of 271 ± 22 mm (Poradowski). Rough agreement only: different cats.

**Caveat**
- The quiet-stance knee (≈90°) is more flexed than the walking knee (105-121°, Carlson-Kuhta; 115°, Day & Jayne).
- The quiet-stance ankle (≈140°) is more open than the walking midstance ankle (≈114°, Day & Jayne).
- These are from one cat in one lab, read off a graph. Treat them as a starting pose, not a population mean.

---

## 8. NOT FOUND (or not readable)

1. **Joint angles in quiet stance averaged over several cats, with SD.** Only one intact cat's angles (Fung 1999 Fig. 5) are published in a readable form.
2. **Fung & Macpherson 1995 numeric angles, limb axis angles and lengths.** Full text blocked (403 and a bot-verification page); abstract only.
3. **MTP and MCP joint angles in quiet stance.** Fung reports paw segment angles instead.
4. **Limb axis lengths in quiet stance for normal-size adult cats.** Only Lacquaniti 1990 (2 kg females, scapula-based forelimb axis).
5. **Stance heights of the elbow, wrist, MCP, knee, ankle and MTP.**
6. **Bone-based (X-ray) scapula inclination in standing cats.** Boczek-Funcke 1996: abstract has no angles; full text paywalled. Fischer & Blickhan 2006: not accessed.
7. **Goslow, Reinking & Stuart 1973; Macpherson 1988; Lacquaniti & Maioli 1994 full texts.** Not accessed.
8. **Distance from the spinous-process tips or vertebral bodies to the dorsal skin** at the withers, mid-back or croup, from CT, radiograph or ultrasound.
9. **Skin thickness at the withers and mid-back specifically.** Measured sites are the dorsal neck (C2-C3) and sacral.
10. **A bone-referenced withers height, and the exact withers landmark used by Poradowski 2024.**

---

## Access notes
**PDFs auto-cached by WebFetch** (not saved on purpose). Folder: `C:\Users\<you>\.claude\projects\<project-id>\b98bba0a-684a-41e1-ae73-906b9dc847fc\tool-results\`
- `webfetch-1792275028490-66xqc3.pdf`: 329,782 bytes (322.1 KB). McKay et al. 2007, *J Biomech* 40:2254 (no numeric stance angles in it).
- `webfetch-1792275571745-c4t699.pdf`: 781,587 bytes (763.3 KB). Iwazaki & Nade 2020, *Jpn J Vet Res* 68:35.

**Not opened as PDF.** The Fung 1999 figures and the Lacquaniti 1990 pages were viewed as JPEG/PNG images in the browser.
