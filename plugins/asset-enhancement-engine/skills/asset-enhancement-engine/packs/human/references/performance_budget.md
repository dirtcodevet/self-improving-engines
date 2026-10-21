# Performance budget for a detailed human model: measured on base_female_torso v9, with cited real-time and offline digital-human practice

Compiled 2026-10-19. Part A is MEASURED by me in background Blender 5.2.1 LTS only (never the live Blenders on 9876/9877); Ryzen 7 8700F 8 cores/16 threads, 16 GB RAM, RTX 5050 8 GB. GPU draw was not measured (background mode), so viewport fps is derived, not observed.
No project file changed; scripts and .blend copies sit in the session scratchpad (perf/). Part B is web research; the shared search budget ran out part-way, so some items are in "not found".
Confidence: strong = measured here (medians of 6-15 repeats) or 2+ sources; single = one source; weak = secondary summary or from memory, not re-checked. "derived" = my arithmetic from the numbers on this page.

## 0. Reading of the numbers (my words)
1. What is heavy. v9 is one closed triangle skin (542,468 vertices, 1,084,932 triangles, 8,239 cm2) meshed at about 1.8 mm everywhere except the two nipple-areola complexes (NAC, together 18.7 cm2 = 0.23% of the skin), meshed at 0.06-0.1 mm. Those two discs hold 51% of all vertices.
What they encode (the NAC micro layer: rings, corrugation, glands, ducts) moves the surface by 4 um median and 43 um at most, tilting the normal 2.5 deg median and 9.2 deg at p99. That is a normal-map signal, not a silhouette. The same cost shape killed the cat: its skin is 11.5 million vertices (21x v9).
2. How cost behaves. Per pose (CPU, 16 threads): Armature 7.5 ns per vertex, normals 17 ns per vertex, each ACTIVE shape key 1.6 ns per vertex; Blender stores every shape key dense (12 B per vertex per key) however few vertices it moves (the 12 corrective keys move 1.4-7.1% of vertices).
A triangle mesh becomes 6.0x the vertices per subdivision level (3 quads per triangle), and a subdivided vertex costs about 2.3 KB RAM and 0.6 us. Memory is about 0.7 KB per base vertex. Load, build and file size are not the problem (build 1.6 s, load 0.3 s); posing at render-stack settings and RAM are.
3. What to do. Four layers: L0 a coarse skinned cage for form; L1 small fine-geometry patches only where relief matters (> 0.2 mm, silhouette or occlusion); L2 height/normal maps for everything under about 50 um or 0.5 mm; L3 detail generated at evaluation/render (stress-driven wrinkle blends, hair from guides, crop-limited true displacement).
Part C gives per-region numbers; the face becomes its own object so its many shape keys loop over about 18k vertices, not the whole body.

### Descriptors a mesh can be checked against (target; basis)
D1 deformed vertices per frame: <= 100k per object, <= 290k per scene (60 fps, 8 ms pose share; derived in A2). D2 pose evaluation at rest and at the hardest pose (both arms 90 deg, elbows 60): <= 8 ms. D3 share of vertices whose local edge < 0.25 mm outside declared fine patches: 0 (v9: 50.7%).
D4 shape-key data per object (keys x vertices x 12 B): <= 100 MB; keys active at once and the share of vertices each key moves (sparsity).
D5 render-stack output vertices (tri x6, quad x4 per level) x 2.3 KB <= 40% of free RAM. D6 each tier vs the reference: p99, RMS, max nearest-surface distance (mm): interactive <= 0.10, review <= 0.04, creases reported separately.
D7 per micro layer: peak displacement (um) and normal tilt (deg); amplitude < 50 um or wavelength < 0.5 mm => map. D8 build s, peak RAM, .blend MB, load s.
### How to measure on a mesh
Counts and local edge length (mean of incident edges) per vertex; area per zone from triangle areas; shape-key sparsity = vertices with |key - Basis| > 1e-9.
Pose time: set a bone angle +-0.05 deg alternately, time view_layer.update() + evaluated_depsgraph_get(), 15 repeats, drop 2, median; read evaluated positions to prove the pose moved (arm: 57.6k vertices > 1 mm, max 713 mm). Memory: Windows GetProcessMemoryInfo (WorkingSet, Private, PeakWorkingSet).
Tier error: BVH find_nearest from every reference vertex to the tier surface (542k queries ~2 s). Micro-layer tilt: vertex normals with and without the layer. Modifier.execution_time returned 0.0 in background, so costs come from differences between stack configurations.

## A1. v9 as built (measured; strong)
| Item | Value |
|---|---|
| Counts | 542,468 vertices; 1,627,398 edges; 1,084,932 triangles (all); closed (0 open, 0 non-manifold edges); area 8,239 cm2; valence mean 6.0 |
| Rig and data | 12 bones; 18 vertex groups; 14 shape keys (Basis + 12 correctives + NAC_micro_off); 16 drivers, all simple expressions and valid (no Python at evaluation); 9 point attributes; mean 3.7 bone influences per vertex (max 7) |
| Build | build() 1.6-2.0 s; exact command `blender -b --factory-startup --python build_base_torso.py -- --save f.blend` 4.95 s wall incl. start-up and save; script header's "about a minute" is out of date |
| Memory | empty Blender 203 MB working set; after build 561 MB (peak 608 MB; plain command peak 690 MB); private +385 MB = 0.71 KB per vertex; dense shape-key data 87 MB (14 x 6.2 MB) |
| Files | .blend 213.4 MB (save 0.37 s) or 108.5 MB compressed (the default for --save); load 0.28 s / 0.38 s; pack folder v9 27.3 MB (npz); relief tile PNG 5.76 MB |
| Edge length (mm) | p25 0.099; p50 0.166; p75 1.81; p95 2.47; per-vertex local edge: 50.5% of vertices < 0.2 mm, 48.2% in 1-3 mm, 1.3% elsewhere |
| NAC_micro_off | 275,396 vertices with offsets (50.8%): 134,642 left + 140,845 right (pack arrays); area 20.9 cm2 (0.25%); bbox 233 x 19 x 36 mm; local edge mean 0.091 mm; nonzero offset p50 4.0 um, p90 13.4, p99 23.5, max 43.0 um; normal tilt p50 2.5, p90 5.9, p99 9.2, max 18.1 deg |
| Zones (vertices; area) | breast zone 292,571; 451 cm2. areola 267,385; 18.7 cm2. nipple 105,773; 3.2 cm2. tubercle 1,214; 0.1 cm2. vein 3,966; 51 cm2. arm limbs 81,064; 2,267 cm2 |
| Density | outside the NAC discs: 275,083 vertices on 8,220 cm2 = 33.5 per cm2, mean local edge 1.87 mm; inside: 14,300 per cm2 (derived) = 427x denser |
| Shape keys moved (share of vertices) | abd15..abd90 .L 5.4-5.5% (29-30k), .R 7.0-7.1% (38-39k); flex60 1.4-1.5% (7.7-8.2k); NAC_micro_off 50.8%; largest offset abd90.R 93.7 mm |
| Dominant bone | chest 352,122 (64.9%; 84,737 without NAC); spine 55,183; hips 31,420; upper_arm 24,662 / 27,492; forearm 15,312 / 14,767; neck 4,404; scapula ~5.7k each; clavicle ~2.8k each |
## A2. Pose evaluation, viewport stack (Armature only; micro layers off as shipped; ms, medians)
| Case | ms | Note |
|---|---|---|
| nothing changed | 0.0 | evaluation is skipped |
| rest, re-skin (hips +-0.0005 rad) | 4.5 | range 4.0-5.5; the 13 keys sit at value 0 |
| one arm raised, glenohumeral 20 / 45 / 64 deg (abduction ~28 / ~61 / 90, by interpolating rig.json) | 5.4 / 5.2 / 5.2 | 2 keys active (tents); 5.0-6.0 range |
| both arms 64 deg | 5.7 | both arms + elbows 60 deg (flex60 on): 6.3 |
| split at arm 64 deg | full 5.2; Armature only (keys muted) 4.05; keys only (Armature off) 1.7 | 1.7 ms = 2 active keys, so ~0.85 ms per active key per 542k vertices |
| key set through the UI/RNA, no driver | 10.5 baseline + 0.88 per active key (1 key 12.0; 13 keys 21.9) | the baseline is the copy-on-write of the whole Key block (87 MB); drivers avoid it |
| normals after the pose | vertex normals 9.3; corner normals 9.4 | 542k vertices; same session evaluation 6.65 |
| data-tag re-evaluation | 8.2 | copy-on-evaluate path (editing) |
Per-vertex coefficients (derived): Armature 7.5 ns; normals 17.2 ns; active key 1.6 ns. Frame budget of 8 ms for pose, k keys active: N_max = 8e6 / (7.5 + 17.2 + 1.6 k) ns = 287k vertices (k=2), 233k (k=6) at 60 fps; 573k (k=2) at 30 fps with 16 ms.
The cat skin (tripo_rebuild/layers/skin_v3d.npz: 11,498,785 vertices, 22,997,826 triangles) would be ~86 ms Armature + 195 ms normals (derived) ~ 3.5 fps before drawing, and ~8.2 GB RAM.
## A3. Render-time stack and other deformers (542k mesh)
| Config (order as shipped: Subdivision, Displace, Armature) | ms per evaluation | Note |
|---|---|---|
| Armature only | 5.1 | evaluated 542,468 vertices |
| + Simple subdivision level 1 | 1,910 (with Armature) | output 3,254,798 vertices = 6.0x, 3,254,796 quads; with Subdivision last it is deferred (7.6 ms) and realising it took 14.3 s under memory pressure |
| + Displace (Voronoi, 0.3 mm, vertex group) | 1,990 for all three; 1,993 without Armature | Subdivision ~1.85 s (93%); Displace ~0.08 s; Armature on 3.25M vertices below noise |
| RAM at that stack | 8.29 GB working set, 10.1 GB commit | free RAM fell to 0.48 GB, so times are upper bounds; level 2 was not run (~4x more); ~2.3 KB per output vertex |
| quarter-size proxy (135.6k verts, no attributes) | 228 | 813,698 outputs = 0.28 us each; v9 is 0.6 us each because 18 vertex groups and 9 attributes are interpolated too |
| Deformers on the posed rig (6.1 ms base, arm 64 deg) | Preserve Volume 7.6 (+25%); Smooth 5 it 117.7; Corrective Smooth 5 it 275, 20 it 720; Surface Deform from a 5,426-vertex cage 20.9 (+14.8), bind 0.3 s | Corrective Smooth 5 it costs as much as ~320 active keys (0.85 ms each) |
| Renders, 640x720, base mesh only (render stack off), 2nd frame arm raised | Workbench 0.11 s; EEVEE 16 spp 0.41 s; Cycles CPU 32 spp no denoise 2.04 s | first frame (sync, upload, shaders): 1.03 / 2.87 / 2.46 s |
| Hair as native Curves, 8 points, 640x720 | 10k / 50k / 150k strands: EEVEE 0.12 / 0.18 / 0.34 s; Cycles CPU 1.58 / 1.63 / 1.78 s | storage ~132 B per strand (derived), 150k strands ~20 MB |
## A4. Geometry versus maps on this model (measured)
| Tier (Decimate Collapse of v9) | Vertices (triangles) | all-skin error mm: RMS / p99 / max | NAC discs (20 mm radius): vertices; RMS / p99 / max um |
|---|---|---|---|
| ratio 0.25 | 135,618 (271k) | 0.020 / 0.016 / 2.02 | 42,958; 4.5 / 13.6 / 27.9 |
| ratio 0.10 | 54,248 (108k) | 0.032 / 0.036 / 2.69 | 14,059; 6.5 / 19.4 / 40.3 |
| ratio 0.03 | 16,275 (33k) | 0.057 / 0.102 / 4.08 | 3,233; 9.4 / 26.5 / 132 |
| ratio 0.01 | 5,426 (11k) | not run | 811; 18.2 / 57.7 / 211 |
Decimation took 5-7 s. The largest errors are few: at ratio 0.1, 261 vertices (0.05%) exceed 0.1 mm, all on the upper arms at the arm-trunk contact (x about +-150 mm, z -67 to -101 mm), up to 2.7 mm; p99 without them 0.036 mm. Creases and contacts need local density; smooth form does not.
16.3k vertices (2.0 per cm2) reproduce 542k vertices to 0.1 mm p99; the person's reference budget is +-0.5 mm.
Visibility (derived): 1 arcmin = 73 um at 0.25 m, 145 um at 0.5 m, 291 um at 1 m; one pixel at 1080p, 30 deg vertical field = 0.50 mm per metre of distance, so half a pixel = 0.25 mm x distance in m. A 43 um surface layer is below acuity at any normal distance and shows only through shading.
# Part B. Literature and documentation
## B1. Digital-human budgets
| Item | Value | Source | Conf |
|---|---|---|---|
| MetaHuman head vertices LOD0-7 | 24,000 / 12,000 / 6,000 / 2,500 / 1,300 / 560 / 270 / 130 | E1 | strong (official) |
| MetaHuman head | blendshapes 669 (LOD0 only); joints 713 / 529 / 397 / 283 / 84 / 70 / 41 / 26; skin influences 12,12,12,8,8,8,4,4; animated (wrinkle) maps LOD0-1 only | E1 | strong |
| MetaHuman body | vertices 30,500 / 7,600 / 3,350 / 1,507 (LOD0-3); influences 8,8,8,4; correctives LOD0-1 only | E1 | strong |
| MetaHuman hair, textures | 50,000 strands LOD0, 25,000 LOD1; facial hair 10,000; cards 30,000 vertices; max texture 8192 (PC, Mac), 2048 (mobile, best LOD 3); triangles and memory budgets not listed | E1 | strong |
| Digital Ira (ICT/Activision 2013) | 30 scans of ~4.5M points; tracked mesh ~20K points; game mesh "4K polygon", 60 bones; maps 2K x 4K optimised to 1K x 2K; 16 ms whole-scene frame; 180 fps at 720p on a GTX 680; 8 key expressions over 12 regions | E2, E3 | single (secondary) |
| Digital Ira, NVIDIA port | 4K textures; 10 static scans, four 4K x 4K maps each; face tiled as 8x8 of 512x512; 30+ fps on a Titan | E2 | single |
| Digital Emily (2008, offline) | ~75 blendshapes; 0.1 mm geometry scans; ~30 displacement maps; Mental Ray | E2 | single |
| SMPL / SMPL-X / STAR | SMPL 6,890 vertices, 24 joints (pose blend shapes linear in rotation-matrix elements; 207 = 23 x 9, derived); SMPL-X 10,475 vertices, 54 joints; STAR keeps 20% of SMPL's parameters with sparse per-joint correctives | R1, R2, R3 | weak / strong / strong |
## B2. Baking detail, deformation, subdivision, Blender
| Item | Value | Source | Conf |
|---|---|---|---|
| Skin microgeometry capture | patches digitised at 10 um; synthesised 16K x 16K displacement against a 4K scanned one; in-vivo scans at 10 um under stretch | R4, R5, E2 | single |
| What static maps lose | stretching smooths and compression roughens pores; filtering the displacement map by strain keeps it right (Nagano); Digital Ira blends maps per vertex by stress | R5, E3 | single |
| Wrinkle maps | normal-map layers added by masks and animated weights; one scheme costs 96 KB | R6, R7 | weak |
| Multires bake | bake from Viewport level 0 against the Render level to a normal or displacement map for the low mesh | M1 | strong |
| Subdivision | "Higher levels ... more vertices ... more memory"; OpenSubdiv; GPU Subdivision preference exists in 5.2 (verified `use_gpu_subdivision`); normals are interpolated, shading can differ from CPU | M2, M3 | strong |
| Cycles adaptive subdivision | Experimental feature set; dicing rate in pixels, offscreen scale, max subdivisions; multi-user data made single-user (more RAM); instances not tessellated separately; default values not stated; the 5.2 Subdivision Surface modifier exposes use_adaptive_subdivision, adaptive_space, adaptive_pixel_size, adaptive_object_edge_length (verified in bpy) | M4 | single |
| Simplify | Max Subdivision cap, Child Particles subset, Texture Size Limit, viewport Normals skip, Camera Cull, Distance Cull | M5 | strong |
| EEVEE displacement | Bump Only changes normals only; Displacement and Bump moves vertices, cost scales with samples, "faster than ... displacement modifier"; 5.2: instancing-heavy CPU-bound scenes up to 2x faster, shadow pool 1.5 / 2 GB | M6, M7 | strong |
| Shape keys in 5.1 | 1M-vertex mesh 25.5 ms -> 6.3 ms at 24 threads (+304%); 2,600-bone action 31.1 -> 13.5 ms | M8 | strong |
| Shape key storage | dense; sparse storage proposed 2025-01-14 as an option, "no benchmark yet"; 2014 GSoC: 3x saving on a head, gone when ~70% of vertices move | M9 | single / weak |
| Armature, Decimate | Preserve Volume uses quaternions, leaves a gap at 180 deg; Collapse ratio counts triangles, no edit-mode preview | M10, M11 | strong |
| GPU skinning in Blender | none found in the 5.0-5.2 notes read; only subdivision uses the GPU. Engines with GPU skinning use 8-12 influences (MetaHuman) | M7, E1 | weak |
# Part C. Recommended layered representation (derived from A and B; adult woman, skin 16,600 cm2 = Mosteller 165 cm / 60 kg)
| Layer | Holds | Representation | Budget, whole body | Evidence |
|---|---|---|---|---|
| L0 form cage | form >= 5 mm wavelength, joints, creases | quad-dominant skinned mesh; 2.0 verts/cm2 smooth, 4 at joints, 24 on the face | 64k interactive; 156k review (6.6/cm2) | A4: 2.0/cm2 = p99 0.10 mm; 6.6/cm2 = 0.036 mm |
| L1 fine patches | relief > 0.2 mm that shows in silhouette or occlusion: nipple 3.4 mm, areola rise 1 mm, lids, lips, nostrils, ears, navel, nails | separate patch meshes at 0.5 mm (nipple 0.25 mm) weighted to L0, switched by LOD | <= 40k; both NAC 8.6k at 0.5 mm, 13.1k with the nipple at 0.25 (derived); measured floor 3,233 | A4: 3,233 vertices hold 267k to p99 26.5 um |
| L2 maps | everything < 50 um or < 0.5 mm: pores 25 um radius, furrows 20-40 um x 50 um, glands 50-100 um, NAC rings 15 um / 0.55 mm, corrugation 6 um / 0.3 mm | 16-bit height, 7.8 um per pixel, 2048^2 = 8.4 MB each, tiled per region along the tension field; one NAC map 4096^2 = 33.6 MB | ~12 tiles + NAC + face set <= 250 MB | A1 micro layer; relief_breast_L.png exists |
| L3 generated | strain-driven wrinkle/pore blends; pores beyond tiles (Voronoi bump); hair from guides; true displacement; SSS | shaders, Curves, crop-limited modifiers | hair 50k strands at LOD0; render subdivision <= 1M output vertices per object | A3, B1, B2 |
Map arithmetic (derived): 16-bit height over the 40 um range steps 0.0006 um, so quantisation is nil; an 8-bit tangent normal steps 0.45 deg (1/127 rad) = 18% of the 2.5 deg median micro tilt, so use 16-bit height (as the pack's tile does) or 16-bit normals.
Unique texels at 0.1 mm over 16,600 cm2 = 166 M = ten 4096^2 tiles = 332 MB at 16 bit; unique at 7.8 um would be 27 G texels (54 GB), so tile an exemplar and blend by region (Graham 2013 approach). One 7.8 um pixel gives 70 pixels per 0.55 mm ring wavelength, 6 across a 50 um furrow.
Replacing the NAC micro layer: bake the NAC_micro_off difference (it IS the micro layer, per vertex) to the NAC map, then build the NAC at 0.5/0.25 mm: 275k vertices (195 MB RAM, 50% of the .blend) become 8.6-13k plus 34 MB of map.
Whole-body at the NAC's 0.1 mm geometry would be 237M vertices (~168 GB); at v9's body density 556k (derived).
### Budget per region (vertices; skin area from the rule of nines x 16,600 cm2; engineering defaults flagged)
| Region | Area cm2 | Interactive | Review | Fine patches | Maps | Rig and keys |
|---|---|---|---|---|---|---|
| Head and neck (9%) | 1,494 | 18k (face 14k at 24/cm2; face area 600 cm2 assumed) | 40k | 10k (lids, lips, nose, ears) | unique face set 4K-8K + tiled pores | own object; <= 300 stored keys, <= 60 active (18k x 60 x 1.6 ns = 1.7 ms); eyebrow raise = 2-6 keys |
| Trunk, front and back (36%) | 5,976 | 12k | 39k | navel 1k | chest, belly, back tiles | 5-8 bones; <= 40 correctives (13 now) |
| Breasts, NAC (inside trunk) | 451 + 18.7 | +1.8k; NAC 3.2k | NAC 8.6k | NAC 8.6-13k | NAC map + breast tile | NAC_micro_off retired |
| Arms to wrist (2 x 1,133) | 2,266 | 9k (4/cm2) | 15k | - | arm tile | 8 bones incl. girdle; shoulder keys 10 (L+R) |
| Hands (2 x ~360) | 720 | 5k (7/cm2) | 12k | nails 2k | palm and back tiles | 30 bones (default; no source here) |
| Legs and feet (36%) | 5,976 | 14k | 40k | - | thigh, shin, foot tiles | 10 bones; <= 12 keys |
| Perineum (1%) | 166 | 0.5k | 1k | - | - | - |
| Total | 16,600 | 64k | 156k | ~26k (cap 40k) | ~250 MB | pose ~2.9 ms (derived) at 64k |
Torso and arms alone (8,239 cm2): interactive 16.3k (measured, ratio 0.03), review 54k (ratio 0.10), against 542k now.
### LOD by distance (half-pixel rule: allowed error 0.25 mm x distance in m; MetaHuman drops 2-4x per LOD)
| Band | Distance | Vertices | Layers on |
|---|---|---|---|
| LOD0 | < 0.5 m | review 156k | L0 + L1 + L2 + crop-limited L3 displacement |
| LOD1 | 0.5-2 m | interactive 64k | L0 + L1 face/hands + L2 |
| LOD2 | 2-6 m | ~20k (MetaHuman LOD1: head 12k + body 7.6k) | L0 + L2, correctives fade out |
| LOD3 | 6-15 m | ~9k (MetaHuman LOD2: 6k + 3.35k) | L0 + L2, 4 influences |
| LOD4 | > 15 m | ~4k (MetaHuman LOD3: 2.5k + 1.5k) | L0 only |
Distances for LOD2-4 are assumed, not measured; confirm each tier with D6 before use (only 16k, 54k, 135k vertices were measured on the torso).
Form-layer check: 16k torso is within half a pixel beyond 0.4 m, 54k beyond 0.15 m, 135k beyond 0.07 m (A4 p99). Blender has no automatic LOD: switch collections by distance with a handler, plus Simplify (Max Subdivision, Camera/Distance Cull).
### Order of work and gates
1. Armature BEFORE subdivision, quads not triangles, GPU Subdivision on (viewport). 2. Face as its own object. 3. NAC: bake the micro difference to a map, rebuild at 0.5/0.25 mm. 4. Keep Skin_micro_subdiv/Skin_micro_detail off for whole bodies; render breast/face crops only. 5.
Add a tool that reports D1-D8 per object and fails on: >100k deformed vertices per object, >100 MB key data, vertices with local edge < 0.25 mm outside patches, pose > 8 ms, est. render-stack RAM > 40% of free, tier p99 > 0.10 mm.
### Caveats
Timings carry about 20% run-to-run spread (the Armature-only stack read 5.1, 5.2 and 6.1 ms in three sessions). GPU draw, upload, UI and Python fixed costs are in no number. The 3.25M-vertex stack ran with 0.5 GB free RAM. One decimation algorithm only (Collapse); others may do better at equal count.
Region areas are rule-of-nines shares of an assumed 16,600 cm2 skin; the face area, hand and foot bone counts and the 2.0 / 4 / 6.6 / 24 per cm2 densities are engineering defaults tied to the A4 errors, not published values.
## Not found
- Official MetaHuman triangle counts and memory budgets (only vertices); AAA character budgets (Naughty Dog, Activision) and the Digital Ira paper's own mesh counts (PDF too large to fetch; "4K polygon" is the secondary wording); blendshape counts for film faces beyond Emily.
- Blender: GPU armature/shape-key deformation (none in the notes read); Cycles adaptive-subdivision default values (manual pages did not state them); Geometry Nodes timings; Blender's hair interpolation node page (404); viewport fps with real GPU draw; per-modifier timers (execution_time = 0 in background).
- Original papers for Pose Space Deformation (Lewis 2000), dual quaternions (Kavan 2007) and Delta Mush were not re-read; SMPL's 207 correctives is my arithmetic. Searching stopped when the shared budget ended.
## References
E1 Epic Games, MetaHuman docs, Platform support and LOD specifications for MetaHumans, dev.epicgames.com/documentation/metahuman/platform-support-and-lod-specifications-for-metahumans (fetched 2026-10-19).
E2 fxguide, "The art of digital faces at ICT - from Digital Emily to Digital Ira", fxguide.com/fxfeatured/the-art-of-digital-faces-at-ict-from-digital-emily-to-digital-ira/. E3 USC ICT, Digital Ira, vgl.ict.usc.edu/Research/DigitalIra/.
R1 Loper M, Mahmood N, Romero J, Pons-Moll G, Black MJ. SMPL. ACM TOG 34(6):248, 2015 (counts via secondary papers). R2 Pavlakos G et al. SMPL-X. CVPR 2019, arXiv:1904.05866; counts from github.com/vchoutas/smplx. R3 Osman AAA, Bolkart T, Black MJ. STAR. ECCV 2020, arXiv:2008.08535 (abstract).
R4 Graham P, Tunwattanapong B, Busch J, Yu X, Jones A, Debevec P, Ghosh A. Measurement-based synthesis of facial microgeometry. Comput Graph Forum 32(2):335-344, 2013, doi:10.1111/cgf.12053 (SIGGRAPH 2012 poster captions). R5 Nagano K et al. Skin microstructure deformation with displacement map convolution.
ACM TOG 34(4), 2015, doi:10.1145/2766894. R6 Oat C. Animated wrinkle maps. SIGGRAPH 2007 Advances in Real-Time Rendering notes. R7 Jimenez J, Echevarria JI, Oat C, Gutierrez D. Practical and realistic facial wrinkles animation. GPU Pro 2, 2011 (96 KB via secondary).
M1 Blender manual, Multiresolution modifier. M2 Subdivision Surface modifier. M3 Preferences > Viewport (GPU Subdivision). M4 Cycles > Render Settings > Subdivision and Adaptive Subdivision. M5 Cycles > Simplify. M6 EEVEE > Material Settings (displacement, performance).
M7 Blender 5.2 release notes, EEVEE & Viewport (developer.blender.org/docs/release_notes/5.2/eevee/). M8 Blender 5.1 notes, Animation & Rigging (.../5.1/animation_rigging/; Ryzen 9 9900X). M9 devtalk.blender.org/t/2025-01-14-shape-keys-performance/38523; GSoC 2014 report via search summary (weak). M10 Armature modifier manual.
M11 Decimate modifier manual. All manual pages: docs.blender.org/manual/en/latest/.
Skin area and rule of nines: Mosteller RD, N Engl J Med 1987;317:1098; Wallace AB, Lancet 1951;257:501 (from memory, not re-checked). Own data: scratchpad perf/results_a..f.json.
