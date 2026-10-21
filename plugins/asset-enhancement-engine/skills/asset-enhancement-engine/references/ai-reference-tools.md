# AI 3-D reference tools: SAM 3D Objects, SAM 3D Body, TRELLIS.2

Purpose: decide whether any of these three tools can give the engine a *measuring-stick* reference (depth, posture,
skull volume, masks) that is accepted only where it agrees with the photo. None of them would make the final asset.

Checked 2026-10-17, read-only: GitHub READMEs, setup docs, LICENSE files, Hugging Face model cards, arXiv HTML pages
and GitHub issues. Nothing was downloaded, installed or uploaded. No PDF was fetched (arXiv HTML versions were read
instead), so no PDF was cached. **[UNVERIFIED]** marks anything I could not confirm from a primary source.
This complements `generative-reference.md` (Hyper3D Rodin), and the same `ref_align.py` / `ref_measure.py`
procedure applies to any mesh these tools produce.

Machine context: Windows 11, 16 GB RAM, RTX 5050 8 GB. The RTX 5050 is consumer Blackwell (sm_120). PyTorch only
supports sm_120 in builds made with CUDA 12.8 or later (PyTorch 2.7+, `cu128` wheels). Older builds such as
`2.5.1+cu121` fail with "no kernel image" ([PyTorch forum](https://discuss.pytorch.org/t/pytorch-support-for-sm-120-nvidia-geforce-rtx-5060/220941)).
This matters below.

---

## 1. SAM 3D Objects (Meta): https://github.com/facebookresearch/sam-3d-objects

**What it does.** "Visually grounded" single-image 3-D reconstruction of one masked object. It outputs the object's
shape, texture **and layout relative to the camera**. Paper: *SAM 3D: 3Dfy Anything in Images*, arXiv 2511.16624
(https://arxiv.org/abs/2511.16624, v1 20 Nov 2025, v2 2 Jun 2026; CVPR 2026).
- **Inputs:** one RGB image plus one binary mask per object (the HF card says RGBA with the mask in the alpha
  channel). It does **not** make masks itself. Optional input: a scene pointmap (LiDAR or monocular depth). When none
  is given, the pipeline runs an internal depth model on the image (`sam3d_objects/pipeline/depth_models/moge.py`
  exists, so this is probably MoGe; **[UNVERIFIED]** which model the shipped `pipeline.yaml` selects). Camera
  intrinsics are taken from the depth model or inferred from the pointmap. No multi-view input. Several objects are
  handled one at a time and then merged (`demo_multi_object.ipynb`).
- **Model:** a 1.2B-parameter geometry flow transformer predicts a coarse 64^3 voxel shape plus layout. A
  600M-parameter texture-and-refinement model then adds detail. Two decoders read the same latent: one for a mesh,
  one for Gaussian splats (up to 32 per occupied voxel).
- **Outputs:**
  - a Gaussian splat (`output["gs"].save_ply("splat.ply")`, PLY);
  - a textured mesh, `output["glb"]` (GLB), when mesh post-processing or texture baking is enabled (issues
    [#29](https://github.com/facebookresearch/sam-3d-objects/issues/29) and #12);
  - `rotation` (normalized 6D representation in the paper), `translation` t (3), `scale` s (3-vector, made uniform
    by the layout post-optimization), all in camera coordinates;
  - `pointmap` and `pointmap_colors`;
  - when `with_layout_postprocess=True`: `iou`, `iou_before_optim` and `optim_accepted`, a built-in mask-agreement
    score.

  **[UNVERIFIED]** whether the exported GLB already has the layout applied. Nobody answered this in issue #29.
  `notebook/demo_3db_mesh_alignment.ipynb` and `mesh_alignment.py` handle placement.
- **Animals / a cat:** not excluded, but not shown either. The paper's data curation names "non-rigid and highly
  deformable objects (e.g., animals, humans, clothing)" and groups dog breeds together. The benchmark description
  includes "animals". No animal result, figure or failure case is shown in the paper, blog, README or model card.
  So: **a cat can be input, but cat quality is unverified.**
- **Hardware (official):** "A linux 64-bits architecture" and "A NVIDIA GPU with at least 32 Gb of VRAM"
  ([doc/setup.md](https://github.com/facebookresearch/sam-3d-objects/blob/main/doc/setup.md)). The environment is
  pinned to CUDA 12.1 wheels (`cu121`), kaolin for torch-2.5.1_cu121, and pytorch3d. A contributor states "we are
  indeed solely running on the linux platform".
- **Community reports (issues [#19](https://github.com/facebookresearch/sam-3d-objects/issues/19), [#30](https://github.com/facebookresearch/sam-3d-objects/issues/30)):**

  | Setup | Reported result |
  |---|---|
  | WSL2, RTX 3090 24 GB | about 35 s inference |
  | WSL2, 12 GB card | about 1 hour |
  | WSL2, 16 GB card | about 1 hour |
  | 16 GB RTX 4080 | one user ran it fine, another hit out-of-memory |

  One native-Windows fork exists ("sam-3d-objects-win", **[UNVERIFIED]**). Native Windows builds struggle with
  Linux-only conda packages and flash-attn. Meta's blog claims "within a few seconds" on its own hardware.
- **On the RTX 5050 8 GB under Windows: not plausible.** No 8 GB success is reported. The pinned `cu121`/torch 2.5.1
  stack has no sm_120 kernels, so the whole stack (torch, pytorch3d, kaolin, gsplat) would need rebuilding for
  cu128. Offloading to the 16 GB of system RAM would be very slow, if it fits at all.
  - Options: Meta's web demo, which uploads the photo to Meta. Or a rented Linux GPU with at least 32 GB (for
    example an A100 40/80 GB, L40S 48 GB or RTX 5090 32 GB, **[UNVERIFIED]** pricing). That uploads the photo to
    the cloud provider and needs the gated weights.
- **Licence:** code and checkpoints are under the **"SAM License"** (last updated November 19, 2025;
  [LICENSE](https://github.com/facebookresearch/sam-3d-objects/blob/main/LICENSE)). The HF card metadata says
  `License: other`.
  - Grant: "non-exclusive, worldwide, non-transferable and royalty-free limited license".
  - Redistribution requires a copy of the agreement. Publications must acknowledge the SAM Materials.
  - No reverse engineering. No ITAR or military use. On termination, "delete and cease use of the SAM Materials".
  - Outputs are provided "AS IS". I found no clause restricting use of outputs or training on them, and no separate
    acceptable-use policy. It does not explicitly address commercial use.
  - It is not an OSI open-source licence. Not legal advice.
- **Gated weights:** https://huggingface.co/facebook/sam-3d-objects needs an access request. The form asks for
  "full legal name, date of birth, and full organization name with all corporate identifiers". The data is handled
  under the Meta Privacy Policy. The form cannot be edited after submission, and access is excluded in
  "comprehensively sanctioned jurisdictions". Download requires `hf auth login`.
- **Hosted demo:** https://www.aidemos.meta.com/segment-anything/editor/convert-image-to-3d (Segment Anything
  Playground). Using it **uploads the image to Meta**. **[UNVERIFIED]** its terms, retention, training use, login
  requirement and whether it exports GLB/PLY. The page is a JavaScript app and the fetch returned no text. Read the
  terms on the page before any upload.
- **Help for our problems:**
  - **(a) Hind-limb posture and body depth. Best fit of the three.** It is fitted to *our* photo and returns a
    camera-frame layout, so its rotation and its translation direction can be compared with our frozen camera's cat
    yaw and ray. The returned intrinsics can be compared with our focal length.
    - The pointmap gives depth of the **visible** surface. That is the most trustworthy part.
    - The mesh gives a trunk-depth and hind-limb hypothesis to run through `ref_align.py` and `ref_measure.py`.
    - The built-in `iou` is a first agreement number. Recompute it through our own camera rather than trusting it.
  - **(b) Rounded skull:** usable, run on one skull photo at a time. A skull is a rigid object, which is in-domain,
    and the paper says a single head or hand "works significantly better" than one inside a full body. It cannot
    fuse our multi-view photos. Each view would give its own hypothesis to check against the other views'
    silhouettes.
  - **(c) Masks:** no help. It *consumes* masks. Use SAM 3 (below) or our own segmentation.
- **Limits:**
  - Hidden geometry (the far hind leg, the far side of the trunk) is generated, not measured.
  - The 64^3 coarse grid distorts thin parts: legs, ears, tail, whiskers.
  - **Fur is baked into the surface.** The mesh is the fur envelope, not skin. Subtract the coat depth from
    `cat-hair-streams.md` before using it for L2 or L3.
  - Monocular **scale is ambiguous.** Keep the engine's size priors and compare only direction and ratios.
  - It has no ground-contact reasoning, so paws may float or sink. Our floor constraint wins.
  - Texture is unreliable, and can be mis-rotated on symmetric objects.
  - One object at a time.

## 2. SAM 3D Body (Meta): https://github.com/facebookresearch/sam-3d-body

**What it does.** "A promptable model for single-image full-body 3D human mesh recovery (HMR)". Paper: *SAM 3D Body:
Robust Full-Body Human Mesh Recovery*, arXiv 2602.15989 (https://arxiv.org/abs/2602.15989, 17 Feb 2026).
- **Inputs:** one image. Optional prompts: 2-D keypoints and masks. People are found by a human detector (ViTDet
  by default, or `--detector_name sam3`), with a MoGe2 field-of-view estimator.
- **Outputs:** per person, a dict with
  - `pred_vertices` (mesh in camera coordinates) and `pred_keypoints_3d` / `pred_keypoints_2d`;
  - `pred_cam_t` and `focal_length`;
  - `body_pose_params`, `hand_pose_params` and `shape_params`.

  The body model is **MHR (Momentum Human Rig)**, "a new parametric mesh representation that decouples skeletal
  structure and surface shape". MHR has 45 identity, 204 pose and 72 expression parameters
  ([github.com/facebookresearch/MHR](https://github.com/facebookresearch/MHR), "Apache Software License 2.0").
  Not SMPL.
- **Animals: no.** The output space is a human body model. The README, model card and paper never mention animals,
  and an issue search for "animal" returns 0 results. It cannot represent a cat.
- **Hardware:** no official figure. INSTALL.md gives Python 3.11, PyTorch "following the official instructions",
  and detectron2 at a pinned commit. A contributor in [issue #136](https://github.com/facebookresearch/sam-3d-body/issues/136)
  said it "typically uses less VRAM than SAM 3D Objects" and that 24 GB "might be sufficient" without guarantee.
  Native Windows has been made to work with pyrender/OpenGL workarounds
  ([issue #58](https://github.com/facebookresearch/sam-3d-body/issues/58)). A CPU-offloading PR is open (#130).
  8 GB: **[UNVERIFIED]**, and the question is moot for a cat.
- **Licence:** code and checkpoints are under the **"SAM License"** (same text and date as above;
  [LICENSE](https://github.com/facebookresearch/sam-3d-body/blob/main/LICENSE)). HF metadata says `sam-license`.
  The gated checkpoints `facebook/sam-3d-body-dinov3` (840M) and `facebook/sam-3d-body-vith` (631M) need the same
  kind of contact-information request. MHR itself is Apache 2.0.
- **Hosted demo:** https://www.aidemos.meta.com/segment-anything/editor/convert-body-to-3d, which uploads to Meta.
  Terms are **[UNVERIFIED]**.
- **Help for our problems:**
  - (a), (b), (c): **none directly.**
  - The idea is worth copying, not the tool. MHR's split of skeleton from surface shape mirrors our L1 skeleton
    under L2/L3 surfaces. The keypoint-prompted fit is the same pattern as our `photo_fit.py`.
  - The quadruped equivalent would be a SMAL-family animal model. **Not evaluated here.**

## 3. TRELLIS.2 (Microsoft): https://github.com/microsoft/TRELLIS.2 (brief re-check)

Confirmed as already known:
- It is a 4B-parameter image-to-3D generator using "O-Voxel" sparse voxels. Paper: arXiv 2512.14692, *Native and
  Compact Structured Latents for 3D Generation*.
- **Input:** one image. **[UNVERIFIED]** whether background removal is internal.
- **Output:** a mesh with PBR materials (base colour, roughness, metallic, opacity) exported as GLB, plus an MP4
  preview. It works at 512^3, 1024^3 or 1536^3.
- **No camera or layout output.** The asset comes out in a canonical frame, so alignment is by silhouettes, as with
  Rodin.
- "NVIDIA GPU with at least 24GB of memory", verified on A100/H100, "currently tested only on Linux", CUDA 12.4.
  H100 timings are about 3 s, 17 s and 60 s for the three resolutions.
- Limits stated on the card: small holes, and the model is "not aligned with human preferences".
- **Licence:** code and model are **MIT** (HF metadata `mit`), not gated
  ([microsoft/TRELLIS.2-4B](https://huggingface.co/microsoft/TRELLIS.2-4B)). Its dependencies nvdiffrast and
  nvdiffrec are under their own NVIDIA licences. From prior knowledge, I believe nvdiffrast's licence is
  non-commercial; **[UNVERIFIED]** in this pass.
- **Demo:** https://huggingface.co/spaces/microsoft/TRELLIS.2 ("Running on Zero", i.e. ZeroGPU). It uploads the
  image to a Hugging Face-hosted Space run by Microsoft. **[UNVERIFIED]** retention, login requirement and quota.
- **8 GB on Windows:** not supported officially. A vendor blog (trellis2.app) claims ComfyUI low-VRAM runs on
  6–8 GB, and a community GGUF quantisation exists (`ChrisColeTech/TRELLIS.2-4B-GGUF`). Both are **[UNVERIFIED]**
  and both are third-party.
- **Animals:** not mentioned.
- **Help for our problems:**
  - **(b) is its best use.** A single skull photo gives a high-resolution, closed, rounded skull mesh to check
    against the other skull views.
  - (a): a generic whole-cat hypothesis, much like Rodin, with no camera grounding.
  - (c): none.

---

## Comparison

| | SAM 3D Objects | SAM 3D Body | TRELLIS.2 |
|---|---|---|---|
| Inputs | 1 image + object mask (+ optional pointmap) | 1 image (+ optional keypoints/mask prompts) | 1 image |
| Outputs | Gaussian splat PLY, textured GLB, camera-frame rotation/translation/scale, pointmap, mask IoU | Human MHR mesh in camera frame, 2-D/3-D keypoints, pose/shape params, cam_t, focal | PBR-textured GLB (no camera pose) |
| Animals? | Not excluded, cat quality unverified | **No** (human body model) | Not mentioned (generic objects) |
| VRAM (official) | >= 32 GB (community: 12–16 GB in about 1 h, mixed) | Not stated (about 24 GB "might be sufficient") | >= 24 GB |
| OS | Linux only (WSL2 works for some) | Not stated; native Windows with workarounds | Linux only (tested) |
| Licence | "SAM License" (code + weights), weights gated | "SAM License" (code + weights), weights gated; MHR Apache 2.0 | MIT (code + weights), not gated |
| Hosted demo | aidemos.meta.com (upload to Meta) | aidemos.meta.com (upload to Meta) | HF Space microsoft/TRELLIS.2 (upload to HF/Microsoft) |
| Runs on RTX 5050 8 GB / Windows? | No (VRAM, Linux, and cu121 build lacks sm_120) | Irrelevant for a cat | No (officially) |
| Best use for us | (a) trunk depth, hind-limb hypothesis and camera-layout cross-check for the cat photo; (b) a skull hypothesis per view | None, beyond the skeleton-vs-shape design idea | (b) high-resolution rounded skull reference |

## Recommendation and open decisions for the person

**Recommendation.**
1. Do not try a local install on this PC. None of the three is supported on 8 GB, Windows or sm_120.
2. If a reference is wanted, **SAM 3D Objects is the best match for (a).** It is the only one grounded in *our* photo
   and camera.
   - Run it on the case photo plus our cat mask.
   - Import the GLB through `ref_align.py`. Compare its layout and intrinsics with the frozen camera.
   - Accept only measurements that pass the agreement test: silhouette IoU through our camera, visible-side
     pointmap depth versus our surface, and hidden parts kept as low-confidence.
   - Subtract the coat depth before use, and keep scale from the engine's priors.
3. **TRELLIS.2 (or SAM 3D Objects) for (b)**, one skull view at a time, each checked against the other skull views'
   silhouettes.
4. **For (c), none of the three helps.** The fitting tool is SAM 3 (https://github.com/facebookresearch/sam3).
   - It is promptable with text, points or boxes, has 848M parameters, uses the "SAM License" and has gated weights.
   - It needs Python 3.12+, PyTorch 2.7+ and CUDA 12.6+; this card needs cu128.
   - It might fit in 8 GB, but that and Windows support are **[UNVERIFIED]**.
   - Its demo at https://segment-anything.com/ also uploads images.

   A mask is a measurement, not generated geometry, so it fits the engine's vision best of all.
5. Skip SAM 3D Body for the cat.
6. Record every value taken from these tools with its source tool, version, date and agreement score, in line with
   engine-grounding.

**Decisions only the person can make (nothing below has been done):**
- Upload the **cat photo** to Meta's Playground (SAM 3D Objects)? Its terms and retention are unverified; read them
  on the page first.
- Upload **cat or skull photos** to the Hugging Face TRELLIS.2 Space? Same caveat. Also confirm the skull photos are
  yours or licensed for upload.
- Request **gated Hugging Face access** to Meta weights? That shares your full legal name, date of birth and
  organisation with Meta, and the form cannot be edited later.
- Rent a **cloud GPU** (Linux, at least 32 GB for SAM 3D Objects)? That means cost, uploading photos to the provider
  and downloading weights there.
- Accept the **SAM License** for any reference meshes kept in the project? It is not OSI open source, and it requires
  a licence copy on redistribution, bans ITAR/military use, and requires deletion on termination. TRELLIS.2 is MIT,
  though its NVIDIA dependencies may be non-commercial (unverified).
