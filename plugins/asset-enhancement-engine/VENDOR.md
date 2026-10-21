# Third-party tools: in the project, NOT in this package

The engine's `tools/vendor.py` loads three third-party tools from `engine/vendor/` (465 MB in the project). They are
not copied here: they bring their own licences (two GPL-3.0 add-ons, Apache-2.0 OpenSim), which is a packaging
decision (DECISIONS D1), and their size. Sources, versions, sha256 and proofs are in
`skills/asset-enhancement-engine/log/TOOLMAKING.md` (2026-10-21, woman2 build 15).

| Tool | Where `vendor.py` expects it | Source | Licence | Use |
|---|---|---|---|---|
| Pose Shape Keys 1.1.1 | `vendor/blender/addons/pose_shape_keys` | Blender Studio, extensions.blender.org | GPL-3.0-or-later | corrective shapes per pose, re-pushed after weight changes |
| Robust Weight Transfer (v1.1.9, libigl 2.6 build) + scipy 1.18.1, libigl 2.6.1, robust_laplacian 1.0.0 | `vendor/blender/addons/robust_weight_transfer`, `vendor/blender/site-packages-cp313` | github.com/sentfromspacevr/robust-weight-transfer; PyPI | GPL-3.0; BSD-3 / MPL-2.0 / MIT | carrying skin weights between meshes |
| OpenSim 4.6 + the thoracoscapular shoulder model | `vendor/python/cp312`, `vendor/opensim/models/ThoracoscapularShoulderModel.osim` | PyPI wheel; github.com/opensim-org/opensim-core tag 4.6 | Apache-2.0 | a scapula that glides on the rib cage, with the clavicle following |

Without them the engine runs as before. Only the steps that call `vendor.enable(...)` or `vendor.opensim()` need
them. `vendor.py` refuses to load them in any Blender not started with `-b --factory-startup`, so a user's own
Blender setup is never changed.
