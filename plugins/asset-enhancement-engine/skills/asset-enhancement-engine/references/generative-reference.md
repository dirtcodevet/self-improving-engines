# Using a generated 3D reference (Hyper3D Rodin) as a measuring stick

Sources (public only - no probing of the service): CLAY paper (Zhang et al., SIGGRAPH 2024, arXiv 2406.13897,
the research behind Rodin Gen-1), Hyper3D API docs (docs.hyper3d.ai), Hyper3D data-retention policy.
Use only with the person's approval: it uploads the case photo. Policy: API inputs/outputs kept 7 days, not used
for training (checked 2026-10-17).

## What Rodin/CLAY does (and what the engine takes from it)

| CLAY / Rodin | Engine takeaway |
|---|---|
| 3D-native latent diffusion: a VAE encodes surface point clouds, a 1.5B DiT generates the latent, a decoder answers *occupancy* queries; mesh = marching cubes on a 512^3 grid | Same representation family as the engine (implicit field -> marching cubes). The difference is the **prior**: CLAY learned shape plausibility from 527K objects, the engine hand-placed primitives. So: borrow the prior as a *reference*, keep the engine's controllable primitives. |
| Training data made watertight by a UDF + grid *visibility* test (a point is inside if it is hidden from every view), avoiding thin-shell artefacts | Any imported reference mesh may be open/thin: make it watertight the same way before slicing/measuring (not yet needed for Rodin's output, which was closed). |
| Raw MC output is "millions of uneven triangles"; they then run QuadriFlow + Blender for quads and UV-atlas | Same pipeline as ours - and QuadriFlow is where our ears collapsed. Their output is fine for smooth objects; thin creature parts need the engine's voxel-remesh + decimate path with a fidelity check. |
| Geometry and materials are separate stages (multi-view material diffusion, back-projected) | Treat a generated model's texture as unreliable; use its *geometry* only. |
| Conditioning adapters add cross-attention for image, multi-view, voxel, point cloud and **bounding box** (8 corner tokens -> aspect/position control) | The add-on's API call accepts `bbox_condition`: pass the case's measured box (from the photo + priors) to constrain proportions. Pass several images when a case has them (up to 5) - one photo leaves depth to the prior. |
| Stated limits: not end-to-end, data scarcity, weak on composed scenes | Expect plausible-but-generic anatomy: the reference is a population prior, not this animal. Where it disagrees with the photo, the photo wins for what the photo sees. |

## Procedure the engine now uses
1. `rodin_ref.py` (add-on, free-trial key) -> import as `Ref3D_Body` (hidden from render), export PLY.
2. `ref_align.py`: similarity transform into the case frame by silhouette IoU through the frozen camera
   (grounded, yaw grid + Nelder-Mead). Rasterise per triangle (`cv2.fillPoly` on a list is even-odd -> holes).
3. Canonicalise: rotate so the paw-pair midpoints lie on +Y; apply the same transform to the camera.
4. `ref_measure.py`: trunk profiles (top/bottom/widest-z/half-width along Y), leg centrelines + radii by
   horizontal slicing, tail by slicing behind the hind legs, head centre.
5. Build the trunk with `loft_y`, limbs/neck/tail with `loft_curve`; keep engineered head parts.
6. `photo_fit.py`: head pose fitted to photo landmarks with a prior to the reference head; paws slid on the
   floor to their photo pixels with a prior to the reference paws. A low camera makes ray-plane paw hits
   useless (~2 cm of depth per pixel) - always check the grazing angle before trusting ray-ground constraints.
7. Gates: `multiview.py` (silhouettes x5 + profiles vs reference) alongside the photo scorer.

## Measured effect (case cat1)
v15 blob body vs v17 lofted (reference measured): side IoU 0.51 -> 0.86, top 0.60 -> 0.86, front/back 0.61 -> 0.83,
topline error 20 -> 4.6 mm, underline 37 -> 2.1 mm, width 15 -> 2.3 mm. Photo IoU 0.858 -> 0.881.
