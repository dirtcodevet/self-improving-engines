"""COAT DEPTH FIELD v3b (felid pack; cat v3 round 2, owner: skin construction). Starts from coat_field.py (copied; that
file stays unchanged). Every line is coat_field's except the two changes below, each fixing a flag at the cause LOCATE.md
located (cases/cat1/v3_skinfix/LOCATE.md).

CHANGE 1 (N1 / N2, the neck ring): the head / neck_ruff blend H(ne) and the neck_ruff / core blend H(ne + 35 mm) were
  smootherstep over BLEND = 10 mm. ss5's peak second derivative is 5.77 / w^2 per unit of depth change, so a 2-3 mm coat
  change over 10 mm bends the inset at 0.115-0.17 /mm: 5.8-8.7 x the 0.02 /mm d'' budget the ring check uses
  (skin_smooth_checks.D2_MARK). The widths are now SIZED FROM THE BUDGET: W = sqrt(5.7735 x delta / (D2_MARGIN x 0.02)),
  delta = the largest coat change across the blend (coat.json typicals): head side {head_crown, cheeks, chin} vs
  neck_ruff -> 3.0 mm -> W_HEAD 34.0 mm; core {back, flanks, chest, belly} vs neck_ruff -> 1.0 mm -> W_RUFF 19.6 mm.
  The head blend ENDS where v2's ended (ne = +5 mm), so every head-side point at ne >= 5 mm keeps v2's weights exactly
  (the face, lips, nose and ears are untouched; the decision checks need that); it starts at ne = -29 mm. The ruff blend
  keeps v2's centre (ne = -35 mm). Composite profile (worst case chin 1.5 / ruff 4.5 / chest 5.5): max d'' 0.0148 /mm
  (74 % of the budget; v2: 0.153). Source of the depths: coat.json (ESTIMATE, as before); of the widths: the budget.
CHANGE 3 (the tail ROOT ring, LOCATE 'also seen', s 0-15 mm, kink p90 7-18 deg): the same defect as N1 - the tail
  region's root end is a z blend H(TAIL_Z.max - z) over 10 mm for a 3.0 mm coat change (tail 7.5 vs back / flanks 4.5):
  d'' 0.17 /mm. Measured on the v3b tail-root crop: the coat goes 4.5 -> 7.5 between s 0 and 10 mm while K_TAPER x lt
  stays 7.3-7.8 (the taper does not bind there), and the seam scan FAILs s 1-8. Now W_TAIL = blend_width(3.0) = 34.0 mm,
  ENDING where v2's ended (TAIL_Z.max + 5 mm, so the rump above the root is unchanged) and reaching full tail coat 34 mm
  lower down the tail.
CHANGE 2 (P1, toes like stacked coins): the paw_pads furless mask was each pad's outline EXTRUDED to a z plane (dz = z -
  ztop, a 1.5 mm ramp in z), so the coat switched on at one height round every toe (a 1.3 mm ledge). Now:
    * the paws owner's feat_paws_v3.furless_mask(P_mm) (weight 0..1, 1 = hairless pad skin) inside its REGIONS
      (world-mm AABBs), the agreed interface (cat v3 round 2); 0 outside them;
    * FALLBACK (no feat_paws_v3, or COAT_V3B_PAWS=fallback): 1 - smoothstep(d3 / PAD_RAMP_FB), d3 = the 3-D distance
      to the pad's own SOLE (Tripo surface samples inside the pad outline whose surface faces down), with
      PAD_RAMP_FB = 2.5 mm: the coat ramps over >= 2 mm along the surface (3-D distance ~ geodesic within a few mm on a
      smooth paw), never at a z cut in space.
  Which mask ran is reported by paws_source().

COAT DEPTH FIELD of the felid pack (Phase 2, criterion C1): depth_mm(P) -> how far the fur surface stands off the
skin at world points P (N,3 metres; z-up, the cat faces -y, +x = the cat's LEFT). Values come from coat.json (regions,
min / typical / max, source + confidence per value); this file only says WHERE each region is and how they blend.

Construction (all smooth, so the skin built by insetting the fur envelope has no seams):
  * every region boundary is a soft half-space H(s) = smoothstep(0.5 + s / BLEND) of a signed distance s (metres) to
    a simple rule in partition's head frame or in world coordinates; BLEND = 10 mm (the brief), so the steepest region
    blend is 1.5 * |delta depth| / 10 mm (smoothstep's peak slope is 1.5 / width)
  * regions are layered in a fixed order (core sub-regions -> legs -> tail -> head sub-regions -> ears); each layer
    lerps over what is below it, so the effective weights are a partition of unity (weights() returns them)
  * the FURLESS masks (nose leather, paw pads, eye opening, pink inner ear) multiply the depth by a ramp that is 0 on
    the mask and rises with smoothstep to 1 at RAMP = 1.5 mm outside it
Rules (head frame mm: x = the cat's left, y = back, z = up; world mm for the body):
  head      = neck(P) > 0 (partition's neck plane through the throat notch), ears excluded
    muzzle    y < -48 and z < 0            (whisker pads, upper lip, in front of the eyes, below the nose bridge)
    chin      y < -30 and z < -24          (below the mouth corners at z -27.5)
    forehead  y < 5 and z > 12             (above the eyes; the eye tops sit at z ~13)
    cheeks    |x| > 24 and z < 12 and y > -50
    crown     the rest of the head (top/back of the skull, throat side)
  ears      = partition's ear region AND the ear stack's span (soft); inner side = SDF gradient faces the ear's front
              (ears.json frame front_head) -> ear_inner, else ear_back
  core      = neck(P) < 0, sub-regions by the trunk sections (atlas_body.json): centre z_c(y) = (top + bottom) / 2,
              half height h(y); back = z - z_c > 0.45 h; ventral = z - z_c < -0.45 h (chest for y < -85 mm, belly
              behind it); flanks in between; neck_ruff = within 35 mm behind the neck plane
  legs      = partition's leg cylinders (smoothed crop radius 32 -> 24 mm about z 30 mm) below the leg cut;
              paw_top z < 25 mm, leg_lower z < 70 mm, leg_upper above
  tail      = within the tail's measured radius + 2 mm of its traced centre, over its traced heights
Furless masks (0 depth, ramp RAMP outside):
  nose_leather   inside the Phase 1 leather outline (nose.json leather['0'].outline_head) seen along the head's y
                 (the leather faces forward), between 2 mm in front of its tip and 2 mm behind its back edge
  eye_opening    inside the eyelid margin polygon (eyes.json margin_head_mm) seen along the margin plane's normal,
                 from 10 mm behind the plane to 4 mm in front of it
  paw_pads       inside each pad's outline at its free level (paws_pads_<paw>.npz core_<pad>, xy) and below the
                 pad's free level + 0.3 mm (paws.json pads.<pad>.free_level_z_mm)
  inner_ear_pink ear inner side (unnormalised 1 mm SDF gradient . front > 0.3) and inside the pink band's height range along the ear axis
                 (ears.json inner_colour.pink_otsu.height_range_mm, ears.json frame)
Speed: vectorised numpy; masks are evaluated only on points inside their bounding boxes; 2-D signed distances come
from rasters built once at import (0.05 mm for nose/eyes, 0.1 mm for pads). Call in slabs of <= 2e6 points.
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
TR = os.path.join(ROOT, "tripo_rebuild")
if TR not in sys.path:
    sys.path.insert(0, TR)
import partition as PT  # noqa: E402

COAT_PATH = os.path.join(HERE, "coat.json")
BLEND = 0.010   # region blend width (m), the brief's ~10 mm
RAMP = 0.0015   # furless ramp (m), the brief's ~1-2 mm


def ss(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ss5(t):
    """C2 smootherstep 6t^5-15t^4+10t^3 for the REGION blends (Phase 2 fix round V1: the cubic smoothstep's 2nd
    derivative JUMPS at both ends of every blend, and on the legs that showed as light rings; this one's is continuous).
    The furless ramps and the ear side test keep the cubic: its peak slope 1.5/w is what coat_check C's X = 4 budgets."""
    t = np.clip(t, 0.0, 1.0)
    return t * t * t * (t * (6.0 * t - 15.0) + 10.0)


LEG_BLEND = 0.035   # V1: the leg height bands (paw_top / leg_lower / leg_upper / leg cut) blend over 35 mm, not 10
TRUNK_BLEND = 0.030  # skin v2 (C3b): back / flanks / ventral (chest, belly) blend over 30 mm, not 10 (10 mm gave d'' 0.05-0.086
                     # per mm at z 130-137; smootherstep's peak d'' = 5.77 x delta / w^2 -> 0.0064 for delta 1 mm)
LEG_CROP_BLEND = 0.035  # skin v2 (C3b): the RADIAL leg crop blends over 35 mm; its INNER edge stays where the 10 mm blend
                        # put it (crop - 5 mm) so the leg surface keeps its own depth, the blend extends outward
PERIOCULAR_MM = None  # V3/B3: periocular fur depth, read from coat.json region 'periocular' (skin v2; was a constant 0.75)
PERI_IN, PERI_W = 0.003, 0.010   # periocular depth held to 3 mm outside the lid margin, back to the region over 10 mm more
# ---- v3b CHANGE 1: the neck blends sized from the d'' budget
D2_BUDGET = 0.02        # /mm: skin_smooth_checks.D2_MARK (the ring check's pass mark)
D2_MARGIN = 0.75        # design to 75 % of it (central differences over +-2 mm read ~1 % under the analytic peak)
SS5_D2_PEAK = 10.0 / np.sqrt(3.0)   # max |ss5''| on [0, 1] (at t = (3 - sqrt 3) / 6)
HEAD_BLEND_END = 0.005  # m: v2's head blend reached 1 at ne = +BLEND/2 = 5 mm; v3b ends there too (head side unchanged)
RUFF_CENTRE = -0.035    # m: v2's neck_ruff centre (1 within ~35 mm behind the neck plane)


def H(s, w=BLEND):
    """soft half-space: 0 for s < -w/2, 1 for s > w/2, smoothstep between (s in metres)"""
    return ss5(0.5 + s / w)


def ramp_out(d, r=RAMP):
    """furless ramp: 0 inside (d <= 0, d = signed distance outside the mask, metres), 1 at d >= r"""
    return ss(d / r)


# ---------------------------------------------------------------- 2-D signed-distance rasters (built once)
class Raster2D:
    """signed distance (metres, + outside) to a filled 2-D region given as a polygon or as a set of filled cells"""

    def __init__(self, inside, lo, step):
        din = ndimage.distance_transform_edt(inside) * step
        dout = ndimage.distance_transform_edt(~inside) * step
        self.sd = (dout - din).astype(np.float32); self.lo = np.asarray(lo, float); self.step = step
        self.hi = self.lo + (np.array(inside.shape) - 1) * step

    @classmethod
    def from_polygon(cls, uv, step=0.00005, pad=0.004):
        from skimage.draw import polygon as fill
        lo = uv.min(0) - pad; n = np.ceil((uv.max(0) + pad - lo) / step).astype(int) + 1
        ins = np.zeros(n, bool); rr, cc = fill((uv[:, 0] - lo[0]) / step, (uv[:, 1] - lo[1]) / step, shape=ins.shape)
        ins[rr, cc] = True
        return cls(ins, lo, step)

    @classmethod
    def from_cells(cls, uv, step=0.0001, pad=0.004):
        lo = uv.min(0) - pad; n = np.ceil((uv.max(0) + pad - lo) / step).astype(int) + 1
        ins = np.zeros(n, bool); ij = np.round((uv - lo) / step).astype(int); ins[ij[:, 0], ij[:, 1]] = True
        ins = ndimage.binary_closing(ins, iterations=2) | ins       # the catchment points sit on a 0.05-0.1 mm lattice
        return cls(ndimage.binary_fill_holes(ins), lo, step)

    def __call__(self, uv):
        out = np.full(len(uv), 1.0)      # outside the raster: far outside the region (raster pads by 4 mm > RAMP)
        ok = np.all((uv >= self.lo) & (uv <= self.hi), axis=1)
        if ok.any():
            out[ok] = ndimage.map_coordinates(self.sd, ((uv[ok] - self.lo) / self.step).T, order=1, mode="nearest")
        return out


def _load_layers():
    L = os.path.join(TR, "layers")
    M = {}
    # nose leather (head frame mm -> m), projected on (x, z)
    ol = np.array(json.load(open(os.path.join(L, "nose.json")))["leather"]["0"]["outline_head"]) / 1000
    M["nose"] = dict(r=Raster2D.from_polygon(ol[:, [0, 2]]), ymax=float(ol[:, 1].max()) + 0.002, ymin=float(ol[:, 1].min()) - 0.002,
                     box=(ol.min(0) - 0.006, ol.max(0) + 0.006))
    # eyes: margin polygon in its own plane
    E = json.load(open(os.path.join(L, "eyes.json"))); M["eyes"] = []
    for s in ("eye.L", "eye.R"):
        m = np.array(E[s]["margin_head_mm"]) / 1000; c = m.mean(0)
        _, _, vt = np.linalg.svd(m - c); e1, e2, nn = vt[0], vt[1], vt[2]
        if nn @ np.array([0, -1.0, 0]) < 0:
            nn = -nn                                     # normal points out of the face (head -y)
        uv = np.c_[(m - c) @ e1, (m - c) @ e2]
        M["eyes"].append(dict(c=c, e1=e1, e2=e2, n=nn, r=Raster2D.from_polygon(uv), box=(m.min(0) - 0.012, m.max(0) + 0.012),
                              # periocular raster: padded past PERI_IN + PERI_W so its distance never jumps to 'far' inside the taper
                              r_peri=Raster2D.from_polygon(uv, step=0.0001, pad=PERI_IN + PERI_W + 0.004)))
    # paw pads: per pad footprint (world xy) + free level
    PJ = json.load(open(os.path.join(L, "paws.json")))["paws"]; M["pads"] = []
    for paw, d in PJ.items():
        Z = np.load(os.path.join(L, f"paws_pads_{paw}.npz"))
        for pad, info in d["pads"].items():
            ring = Z[f"core_{pad}"][:, :2]          # the pad's outline at its free level (ordered contour, world m)
            M["pads"].append(dict(paw=paw, pad=pad, r=Raster2D.from_polygon(ring), ztop=info["free_level_z_mm"] / 1000 + 0.0003,
                                  box=(ring.min(0) - 0.004, ring.max(0) + 0.004)))
    # ears: frames + pink band
    A = json.load(open(os.path.join(L, "ears.json")))["ears"]; M["ears"] = {}
    for s in ("L", "R"):
        fr = A[s]["frame"]; hr = A[s]["inner_colour"]["pink_otsu"]["height_range_mm"]
        M["ears"][s] = dict(o=np.array(fr["origin_head_mm"]) / 1000, ax=np.array(fr["axis_head"]), front=np.array(fr["front_head"]),
                            h0=hr[0] / 1000, h1=hr[1] / 1000, side=1.0 if s == "L" else -1.0)
    EV = np.load(os.path.join(TR, "vol", "ears.npz"))
    M["ear_sdf"] = dict(sdf=EV["sdf"], lo=EV["lo"].astype(float), vox=float(EV["vox"]))
    return M


MASKS = _load_layers()
BODY = json.load(open(os.path.join(TR, "atlas_body.json")))
_TS = BODY["trunk_sections"]
TR_Y = np.array([s["y_mm"] for s in _TS]) / 1000
TR_ZC = np.array([(s["top_mm"] + s["bottom_mm"]) / 2 for s in _TS]) / 1000
TR_HZ = np.array([(s["top_mm"] - s["bottom_mm"]) / 2 for s in _TS]) / 1000
# the sections in front of y = -130 mm include the head; the core's own band is taken from -130 mm back
_core = TR_Y >= -0.130
TR_Y, TR_ZC, TR_HZ = TR_Y[_core], TR_ZC[_core], TR_HZ[_core]
CHEST_Y = -0.085   # chest -> belly (40 mm behind the fore legs' top centres, y -0.127 m)


def load_coat(path=COAT_PATH):
    return json.load(open(path))


def blend_width(delta_mm, budget=D2_BUDGET, margin=D2_MARGIN):
    """smootherstep width (m) whose peak inset curvature for a delta_mm coat change is margin x budget (/mm)"""
    return float(np.sqrt(SS5_D2_PEAK * abs(delta_mm) / (margin * budget))) / 1000.0


def neck_blends(coat=None):
    """(W_HEAD, W_RUFF, delta_head_mm, delta_ruff_mm) from coat.json's typicals"""
    T = typical(coat or load_coat())
    dh = max(abs(T[k] - T["neck_ruff"]) for k in ("head_crown", "cheeks", "chin"))
    dr = max(abs(T[k] - T["neck_ruff"]) for k in ("back", "flanks", "chest", "belly"))
    return blend_width(dh), blend_width(dr), dh, dr


def typical(coat):
    return {k: float(v["depth_mm"]["typical"]) for k, v in coat["regions"].items()}


# ---------------------------------------------------------------- region weights
EAR_FD = 0.001   # central-difference half step (m) for the ear side test


def _ear_grad_cos(P, front_head):
    """the ear SDF's central-difference gradient (half step EAR_FD = 1 mm) dotted with the ear's front, NOT normalised:
    ~ +1 on the front (inner) surface, ~ -1 on the back, and it passes smoothly through 0 at the ear's medial surface
    (a normalised gradient flips there - a step in the field, caught by coat_check C on the first run)"""
    S = MASKS["ear_sdf"]; e = S["vox"]
    g = np.zeros((len(P), 3))
    for k in range(3):
        d = np.zeros(3); d[k] = EAR_FD
        a = ndimage.map_coordinates(S["sdf"], ((P + d - S["lo"]) / e).T, order=1, mode="nearest")
        b = ndimage.map_coordinates(S["sdf"], ((P - d - S["lo"]) / e).T, order=1, mode="nearest")
        g[:, k] = (a - b) / (2 * EAR_FD)
    return (g @ PT.HR) @ front_head                   # world -> head frame, then . front


def weights(P):
    """effective weight of every region at P (dict name -> (N,)), summing to 1. Furless masks are separate (masks())."""
    P = np.asarray(P, float); N = len(P)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    # --- core sub-regions (world)
    zc = np.interp(y, TR_Y, TR_ZC); hz = np.interp(y, TR_Y, TR_HZ); dz = z - zc
    w_back = H(dz - 0.45 * hz, TRUNK_BLEND); w_ventral = H(-0.45 * hz - dz, TRUNK_BLEND); w_belly = H(y - CHEST_Y)
    ne = PT.neck(P)                                     # + on the head side (metres)
    w_neckruff = H(ne - RUFF_CENTRE, W_RUFF)            # v3b: 1 within ~35 mm behind the neck plane; width from the budget
    layers = [("flanks", np.ones(N)), ("back", w_back), ("chest", w_ventral * (1 - w_belly)), ("belly", w_ventral * w_belly),
              ("neck_ruff", w_neckruff)]
    # --- legs
    for k in PT.LEGS:
        cx, cy = PT.leg_centre(k, z); r = np.hypot(x - cx, y - cy)
        crop = 0.024 + 0.008 * (1.0 - H(z - 0.03))       # partition's 32 -> 24 mm crop, smoothed about z = 30 mm
        w_leg = H(crop + 0.5 * (LEG_CROP_BLEND - BLEND) - r, LEG_CROP_BLEND) * H(PT.LEGS[k]["zcut"] - z, LEG_BLEND)
        w_low = H(0.070 - z, LEG_BLEND); w_paw = H(0.025 - z, LEG_BLEND)
        layers += [(f"leg_upper", w_leg * (1 - w_low)), (f"leg_lower", w_leg * w_low * (1 - w_paw)), (f"paw_top", w_leg * w_paw)]
    # --- tail
    tcx, tcy = PT.tail_centre(z); rt = np.hypot(x - tcx, y - tcy)
    w_tail = H(np.interp(z, PT.TAIL_Z, PT.TAIL_R) + 0.002 - rt) * H(z - PT.TAIL_Z.min())         * H((PT.TAIL_Z.max() + BLEND / 2 - W_TAIL / 2) - z, W_TAIL)   # v3b CHANGE 3: root blend from the budget, same top end
    layers.append(("tail", w_tail))
    # --- head sub-regions (head frame)
    Lh = PT.head_local(P); hx, hy, hzz = Lh[:, 0], Lh[:, 1], Lh[:, 2]
    w_head = H(ne - (HEAD_BLEND_END - W_HEAD / 2), W_HEAD)   # v3b: ends at ne = +5 mm as v2's did; width from the budget
    w_cheek = H(np.abs(hx) - 0.024) * H(0.012 - hzz) * H(hy + 0.050)
    w_fore = H(0.005 - hy) * H(hzz - 0.012)
    w_muz = H(-0.048 - hy) * H(-hzz)
    w_chin = H(-0.030 - hy) * H(-0.024 - hzz)
    layers.append(("head_crown", w_head))
    layers += [("cheeks", w_head * w_cheek), ("forehead", w_head * w_fore), ("muzzle", w_head * w_muz), ("chin", w_head * w_chin)]
    # --- ears (soft version of partition.ear_region & ear_extent)
    dome = PT.dome(hx, hy)
    w_er = H(hzz - dome - 0.002) * H(np.abs(hx) - 0.012) * H(hzz - 0.02)
    w_inner = np.zeros(N); w_ear_all = np.zeros(N)
    for sd in ("R", "L"):
        F = PT.EAR_FRAMES[sd]; q = P - F["base"]; t = q @ F["v"]
        w_ext = H(t - PT.EAR_T0) * H(PT.EAR_T1 - t) * H(PT.EAR_HALF - np.abs(q @ F["u"])) * H(PT.EAR_HALF - np.abs(q @ F["w"])) \
            * H(F["side"] * hx - 0.012)
        w_e = w_er * w_ext
        sel = w_e > 0
        if sel.any():
            c = _ear_grad_cos(P[sel], MASKS["ears"]["L" if sd == "L" else "R"]["front"])
            w_inner[sel] = np.maximum(w_inner[sel], ss(0.5 + c / 1.6))      # inner side: gradient faces the front
        w_ear_all = np.maximum(w_ear_all, w_e)
    layers.append(("ear", w_ear_all))
    eff = _seq_named(layers)
    # ONE ear layer split afterwards (two sequential ear layers left a w(1-w) hole the crown showed through - LOG coat C)
    e = eff.pop("ear"); eff["ear_back"] = e * (1 - w_inner); eff["ear_inner"] = e * w_inner
    return eff      # legs repeat their names per leg: each repeat lerps over all before it


def _seq_named(layers):
    """layers = [(name, w)] in order, w in [0,1]; each lerps over everything before it -> effective weights (sum 1)"""
    eff = {}
    first = True
    for name, w in layers:
        if first:
            eff[name] = np.ones_like(w); first = False
            continue
        for k in eff:
            eff[k] = eff[k] * (1.0 - w)
        eff[name] = eff.get(name, 0.0) + w
    return eff


# ---------------------------------------------------------------- furless masks
def masks(P):
    """furless mask strength in [0,1] per mask (1 = on the furless area, 0 = >= RAMP outside it)"""
    P = np.asarray(P, float); N = len(P); out = {k: np.zeros(N) for k in ("nose_leather", "eye_opening", "paw_pads", "inner_ear_pink")}
    Lh = PT.head_local(P)
    # nose
    Mn = MASKS["nose"]; b = np.all((Lh >= Mn["box"][0]) & (Lh <= Mn["box"][1]), axis=1)
    if b.any():
        d = Mn["r"](Lh[b][:, [0, 2]])
        dy = Lh[b][:, 1] - Mn["ymax"]                          # + behind the leather's back edge
        dyf = Mn["ymin"] - Lh[b][:, 1]                         # + in front of the nose tip (air): the mask ends there too
        out["nose_leather"][b] = (1 - ramp_out(d)) * (1 - ramp_out(dy)) * (1 - ramp_out(dyf))
    # eyes
    for Me in MASKS["eyes"]:
        b = np.all((Lh >= Me["box"][0]) & (Lh <= Me["box"][1]), axis=1)
        if b.any():
            q = Lh[b] - Me["c"]; d = Me["r"](np.c_[q @ Me["e1"], q @ Me["e2"]]); s = q @ Me["n"]
            win = (1 - ramp_out(s - 0.004)) * (1 - ramp_out(-0.010 - s))
            out["eye_opening"][b] = np.maximum(out["eye_opening"][b], (1 - ramp_out(d)) * win)
    # paw pads (world): v3b CHANGE 2 - the paws owner's mask, or the surface-ramp fallback (never a z cut)
    out["paw_pads"] = paw_furless(P)
    # inner ear pink
    hi = Lh[:, 2] > 0.015
    if hi.any():
        for s, Ma in MASKS["ears"].items():
            b = hi & (Ma["side"] * Lh[:, 0] > 0.005)   # the ear weight is 0 below |x| 7 mm, so this cut is never seen
            if not b.any():
                continue
            hgt = (Lh[b] - Ma["o"]) @ Ma["ax"]
            band = (1 - ramp_out(Ma["h0"] - hgt)) * (1 - ramp_out(hgt - Ma["h1"]))
            sel = np.where(b)[0][band > 0]
            if len(sel):
                c = _ear_grad_cos(P[sel], Ma["front"])
                v = ss((c + 0.15) / 0.8) * band[band > 0]          # full mask for c >= 0.65 (conch floor and walls), 0 on the back
                # only on the ear itself (not the skull top under it): the soft ear weight
                out["inner_ear_pink"][sel] = np.maximum(out["inner_ear_pink"][sel], v)
    return out


# ---------------------------------------------------------------- v3b: paw furless mask
PAD_RAMP_FB = 0.0025    # m: fallback ramp along the surface (>= 2 mm, the brief); cubic smoothstep, as RAMP
PAD_FB_STEP = 0.00015   # m: surface sample spacing of the pad patches (<= 1/10 of the ramp)
PAD_FB_DOWN = -0.5      # the pad sole faces down: outward normal z below -0.5 (more than 30 deg below horizontal)
_PAWS = {}


def _paws_module():
    if "mod" not in _PAWS:
        _PAWS["mod"] = None; _PAWS["err"] = None
        if os.environ.get("COAT_V3B_PAWS", "auto") != "fallback":
            try:
                import importlib
                feat = os.path.join(HERE, "features")
                if feat not in sys.path:
                    sys.path.insert(0, feat)
                m = importlib.import_module(os.environ.get("COAT_V3B_PAWS_MODULE", "feat_paws_v3"))
                assert hasattr(m, "furless_mask") and hasattr(m, "REGIONS"), "feat_paws_v3 lacks furless_mask / REGIONS"
                _PAWS["mod"] = m
            except Exception as e:                          # not written yet, or broken: the fallback runs, and says so
                _PAWS["err"] = repr(e)
        else:
            _PAWS["err"] = "COAT_V3B_PAWS=fallback"
    return _PAWS["mod"]


def paws_source():
    m = _paws_module()
    return dict(source=("feat_paws_v3.furless_mask" if m is not None else "fallback: 3-D surface-distance ramp"),
                ramp_mm=None if m is not None else PAD_RAMP_FB * 1000, import_error=_PAWS.get("err"))


def _pad_patches():
    """per pad: KD-tree of the pad's SOLE: Tripo surface samples inside the pad outline (+0.5 mm) whose triangle faces
    down (normal z < PAD_FB_DOWN, i.e. more than 30 deg below horizontal) and that lie on the paw bottom (z below the
    free level + 3 mm, a bounding filter only). The patch ends where the toe surface turns from facing down to facing
    sideways - a curve that follows each toe, not a z plane."""
    if "patch" in _PAWS:
        return _PAWS["patch"]
    from scipy.spatial import cKDTree
    D = np.load(os.path.join(TR, "tripo_welded.npz")); v = D["v"].astype(float); f = D["f"].astype(np.int64)
    from exact_sdf import surface_samples
    fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-30)[:, None]
    T = v[f]; sv = np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])).sum(); del T
    fn = fn if sv > 0 else -fn                                       # outward normals
    out = []
    for Mp in MASKS["pads"]:
        lo = np.r_[Mp["box"][0], -0.01]; hi = np.r_[Mp["box"][1], Mp["ztop"] + 0.003]
        S, tri = surface_samples(v, f, lo, hi, PAD_FB_STEP, 0.0)
        m = np.all((S >= lo) & (S <= hi), axis=1) & (Mp["r"](S[:, :2]) <= 0.0005) & (fn[tri, 2] < PAD_FB_DOWN)
        S = S[m]
        if len(S):
            out.append(dict(tree=cKDTree(S), lo=S.min(0) - PAD_RAMP_FB - 0.001, hi=S.max(0) + PAD_RAMP_FB + 0.001, n=len(S),
                            paw=Mp["paw"], pad=Mp["pad"]))
    _PAWS["patch"] = out
    return out


def region_lo_hi(R):
    """a paws REGION as (lo_mm, hi_mm): feat_paws_v3 gives dict(paw, lo_mm, hi_mm); a (lo, hi) pair is accepted too"""
    if isinstance(R, dict):
        return R["lo_mm"], R["hi_mm"]
    return R[0], R[1]


def paw_furless(P):
    """paw pad furless weight in [0,1] at world points P (m): feat_paws_v3.furless_mask in its REGIONS, else the fallback"""
    P = np.asarray(P, float); out = np.zeros(len(P)); m = _paws_module()
    if m is not None:
        for R in m.REGIONS:
            lo, hi = (np.asarray(x, float) / 1000 for x in region_lo_hi(R))
            b = np.all((P >= lo) & (P <= hi), axis=1)
            if b.any():
                out[b] = np.maximum(out[b], np.clip(np.asarray(m.furless_mask(P[b] * 1000), float), 0, 1))
        return out
    low = P[:, 2] < 0.02
    if not low.any():
        return out
    for pp in _pad_patches():
        b = low & np.all((P >= pp["lo"]) & (P <= pp["hi"]), axis=1)
        if b.any():
            d, _ = pp["tree"].query(P[b], distance_upper_bound=PAD_RAMP_FB + 0.0005)
            out[b] = np.maximum(out[b], 1 - ss(np.minimum(d, 1.0) / PAD_RAMP_FB))
    return out


def ear_weight(P):
    w = weights(P)
    return w["ear_back"] + w["ear_inner"]


_THICK = {}


def _thick_vol(name, win_m, blur_vox):
    """local half-thickness of the fur envelope: max of the inside distance within +-win_m (a cube), Gaussian-smoothed
    by blur_vox voxels so the cap has no kinks; computed once per process from vol/<name>.npz and cached in %TEMP%"""
    if name in _THICK:
        return _THICK[name]
    V = np.load(os.path.join(TR, "vol", f"{name}.npz")); vox = float(V["vox"])
    cache = os.path.join(os.environ.get("TEMP", "/tmp"), "p2_skin-fix", f"halfthick_{name}_{int(win_m * 1e4)}_b{blur_vox:g}.npy")
    try:
        R = np.load(cache, mmap_mode="r")
    except Exception:
        inside = np.clip(-V["sdf"].astype(np.float32), 0, None)
        R = ndimage.maximum_filter(inside, size=2 * int(round(win_m / vox)) + 1)
        R = ndimage.gaussian_filter(R, blur_vox).astype(np.float32)
        try:
            os.makedirs(os.path.dirname(cache), exist_ok=True); np.save(cache, R)
        except Exception:
            pass
    _THICK[name] = (R, V["lo"].astype(float), vox)
    return _THICK[name]


def half_thickness_mm(P, w_ear=None):
    """the fur envelope's local half-thickness (mm) at P: body volume (1 mm, window +-15 mm); ON THE EAR (soft ear weight
    w_ear, so there is no step at the ear volume's box faces - coat_check C caught a 29 mm/mm step there) it moves to
    the min with the 0.4 mm ear volume (window +-5 mm); exact to about a voxel (estimated)"""
    P = np.asarray(P, float); out = np.empty(len(P))
    R, lo, vox = _thick_vol("body", 0.015, 2.0)
    out[:] = ndimage.map_coordinates(R, ((P - lo) / vox).T, order=1, mode="nearest")
    R2, lo2, vox2 = _thick_vol("ears", 0.005, 4.0)    # 1.6 mm smoothing: at 0.8 mm coat_check C read 5.2 mm/mm at the L ear tip
    hi2 = lo2 + (np.array(R2.shape) - 1) * vox2; b = np.all((P >= lo2) & (P <= hi2), axis=1)
    if w_ear is not None:
        b &= w_ear > 0
    if b.any():
        re = np.minimum(out[b], ndimage.map_coordinates(R2, ((P[b] - lo2) / vox2).T, order=1, mode="nearest"))
        we = 1.0 if w_ear is None else w_ear[b]
        out[b] = out[b] + we * (re - out[b])
    return out * 1000


def _smin(a, b, k):
    h = np.clip(k - np.abs(a - b), 0, None) / k
    return np.minimum(a, b) - h * h * k / 4


def periocular_weight(P):
    """1 within PERI_IN of either eye's lid margin (2-D, in the margin plane, the eye mask's window widened), 0 beyond
    PERI_IN + PERI_W (V3: the bare eye no longer bulges out of a 2.5 mm crown/cheek inset)"""
    P = np.asarray(P, float); Lh = PT.head_local(P); w = np.zeros(len(P))
    for Me in MASKS["eyes"]:
        rp = PERI_IN + PERI_W + 0.002
        b = np.all((Lh >= Me["box"][0] - rp) & (Lh <= Me["box"][1] + rp), axis=1)     # box >= the taper's whole reach
        if b.any():
            q = Lh[b] - Me["c"]; dd = Me["r_peri"](np.c_[q @ Me["e1"], q @ Me["e2"]]); s_ = q @ Me["n"]
            win = (1 - ramp_out(s_ - 0.006, 0.004)) * (1 - ramp_out(-0.014 - s_, 0.004))
            w[b] = np.maximum(w[b], (1 - ss5((dd - PERI_IN) / PERI_W)) * win)
    return w


def depth_mm(P, coat=None, return_parts=False, return_thickness=False):
    """coat depth (mm) at world points P (N,3 metres): smooth region blend, periocular taper, x furless ramps"""
    coat = coat or COAT
    T = typical(coat); W = weights(P)
    d = np.zeros(len(P))
    for k, w in W.items():
        if k not in T:
            raise KeyError(f"region {k} has no depth in coat.json")
        d += w * T[k]
    # periocular is a REGION (coat.json 'periocular', skin v2): it lerps over the regions under it, so W still sums to 1
    # and coat_check's value test sees periocular points as periocular, not as crown / cheek / forehead
    wp = periocular_weight(P); pm = float(T["periocular"]) if "periocular" in T else 0.75
    d = d * (1 - wp) + pm * wp
    W0 = W
    if return_parts:
        W = {k: w * (1 - wp) for k, w in W.items()}; W["periocular"] = wp
    # NO thin-part cap here: a cube max-filter half-thickness over-reads the tips (measured in the fix round: tail end
    # y > 225 mm reads 11-14 mm, ear tips p10 4.3 mm, so a 0.6 x cap engaged on 0 % of them). B1/B2 are skin_build's
    # local-thickness taper (depth_eff). half_thickness_mm stays available for information only.
    Rt = half_thickness_mm(P, W0["ear_back"] + W0["ear_inner"]) if return_thickness else None
    Mk = masks(P)
    ew = W0["ear_back"] + W0["ear_inner"]
    Mk["inner_ear_pink"] = Mk["inner_ear_pink"] * ss(ew / 0.5)        # pink mask only where the point is ear
    keep = np.ones(len(P))
    for k, m in Mk.items():
        keep *= (1 - m)
    d = d * keep
    if return_thickness:
        return d, Rt
    if return_parts:
        return d, W, Mk
    return d


COAT = load_coat() if os.path.exists(COAT_PATH) else None
W_HEAD, W_RUFF, DELTA_HEAD_MM, DELTA_RUFF_MM = neck_blends(COAT)
DELTA_TAIL_MM = abs(typical(COAT)["tail"] - max(typical(COAT)[k] for k in ("back", "flanks")))
W_TAIL = blend_width(DELTA_TAIL_MM)
