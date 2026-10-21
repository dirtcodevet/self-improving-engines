"""Builder-side silhouette check WITH attribution: which named part causes each mismatch.

Compares the probe render (alpha mask + part-ID colours of the fur envelope) with the builder's OWN
mask of the reference photo (made with ref_mask.py). Blue = model excess, owned by the part drawn there.
Red = reference-only (model missing), blamed on the nearest model pixel's part.

usage: python diff_parts.py <own_ref_mask.png> <probe_prefix> <parts.json> [top=10]
"""
import json
import sys
from collections import Counter

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ref_p, probe, parts_p = sys.argv[1:4]
top = int(sys.argv[4]) if len(sys.argv) > 4 else 10
ref = np.asarray(Image.open(ref_p).convert("L")) > 127
H, W = ref.shape
rgba = np.asarray(Image.open(probe + "_mask.png").convert("RGBA").resize((W, H), Image.NEAREST)).astype(int)
mod = rgba[..., 3] > 127
code = np.round((rgba[..., 0] - 8) / 16).clip(0, 15) + 16 * np.round((rgba[..., 1] - 8) / 16).clip(0, 15)
owner = np.where(mod, code - 1, -1).astype(int)
names = json.load(open(parts_p))


def nm(i):
    return names[i] if 0 <= i < len(names) else "?"


iou = (ref & mod).sum() / max((ref | mod).sum(), 1)
excess = mod & ~ref
missing = ref & ~mod
_, (iy, ix) = ndi.distance_transform_edt(~mod, return_indices=True)
blame_missing = owner[iy, ix][missing]
ex = Counter(nm(i) for i in owner[excess])
mi = Counter(nm(i) for i in blame_missing)
print(f"IoU(own mask) {iou:.4f}   excess {excess.sum()} px   missing {missing.sum()} px")
print("  model EXCESS by part (shrink/move away):  " + ", ".join(f"{k} {v}" for k, v in ex.most_common(top)))
print("  model MISSING by part (grow/move toward): " + ", ".join(f"{k} {v}" for k, v in mi.most_common(top)))
