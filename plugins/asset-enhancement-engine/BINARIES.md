# Binary pack data - in the working tree, NOT committed

These files are copied into the local package (so the engine is complete on this machine) but `.gitignore`
keeps them out of git until the maintainer decides how to ship them: **Git LFS**, **release assets**, or
**regenerate** from the pack's JSON (decision D7 in `docs/maintainer/DECISIONS.md`).

- `packs/felid/skull/`: derived from reference skull 20 (`ref20_*`), a photo under CC BY-SA 4.0 (see
  `packs/felid/skull/ref20_spec.json`). ShareAlike may bind data derived from it - a licensing decision. The
  engine's skull tools (`tools/view_hull.py`, `tools/skull_build.py`) rebuild them; not yet verified from this repo.
- `packs/human/mh_*.npz`: MakeHuman base-mesh and body-target data (`tools/class_template_npz.py` builds them from the
  template that `tools/class_template_fetch.py` downloads).

Not shipped at all (`tools/publish_rules.json`): the sample torso model (`packs/human/base_female_torso/`), the
MakeHuman template folder (`packs/human/template/`) and the engine's run logs. Tests that load the sample torso
(`loop/test_region.py`, `loop/test_shape.py`, `checks/folds.py`) need it supplied locally.

Regenerated 2026-10-21 from the working tree.

| File (skill-relative) | Bytes | sha256 |
|---|---:|---|
| `packs/felid/skull/ref20_hull.npz` | 2,557,213 | `d068b074b4c3223be291101faa8b2e16d34a61b6423e8e534b217f955b405e49` |
| `packs/felid/skull/ref20_hull.ply` | 3,885,375 | `13f1497c52ef5d2e2ed99a8eeb3e2ba36e26010f1985cdb5fcd5cb4cd7d7c727` |
| `packs/felid/skull/ref20_skull.npz` | 4,466,152 | `46bdc2cb41da23e229f9b3fcffd2a0c9126937c503e51422809efc0602eb3b08` |
| `packs/felid/skull/ref20_skull.ply` | 3,879,581 | `8422f4a5b33e59bca8553ed2128160c115f7cbf0231d2df84f0627777f4cafac` |
| `packs/felid/skull/skull.npz` | 72,267,423 | `c65377537c1f1fcb9e1351a4f93eded447d74ece956b85e55393d64fb371289e` |
| `packs/felid/skull/skull_cranium.ply` | 4,974,231 | `bd081869d634ee284977a3a819b1599660845f6355ae746c82ee9a14f87d5f64` |
| `packs/felid/skull/skull_mandible.ply` | 1,167,865 | `a4ac7ca50664a38c750de9dc24af23baff4c5227999188e6f9e72cf42f0466f8` |
| `packs/human/mh_base.npz` | 691,410 | `a4c06c7599200fdd7b9e022fd235a3ae3618a535a70814c6708aea6574b7f738` |
| `packs/human/mh_targets_body.npz` | 26,099,136 | `de581439b0af5fb2d0be1c878533a363fbe58244f8e144db16bccf4318beca9b` |

9 files, 120.0 MB.
