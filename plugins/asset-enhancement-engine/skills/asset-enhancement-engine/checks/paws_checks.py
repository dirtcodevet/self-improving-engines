"""PAWS checks (cat v3 round 2, owner 'paws', 2026-10-18): the paws built by engine/packs/felid/features/feat_paws_v3.py,
each check proven on planted failures on BOTH sides (A10, A22) and with its pass mark's reason stated here.

  P-SEP   toe separation   per cleft, on exact horizontal sections of the skin over the digits' band (z_s + 1 mm .. the
                           digits' mean centre height), the cleft notch = the deepest convexity defect whose deepest point
                           lies within 10 deg of the cleft's MEASURED direction (paws.json), in front of the pads' rear
                           edge, and whose bridge lands on the two neighbouring toes (paws_toes.defects, the Phase 1
                           definition). PASS iff every cleft has: a notch at >= 50 % of the band heights (else it is
                           CLOSED), skin notch p50 >= CLEFT_MIN 2.7 mm, and - with the typical coat laid on (the section
                           dilated by 1.3 mm, shapely) - fur-surface notch p50 >= CLEFT_FUR_MIN 0.5 mm.
                           Reasons: spec_paws_v3.json design.CLEFT_MIN_MM / CLEFT_FUR_MIN_MM (coat max 2.2 + 0.5 floor).
  P-COIN  no coin ledge    per toe, vertical half-planes through the toe's measured digital-pad centroid, every 10 deg
                           within +-50 deg of its measured direction; r(z) = the outermost section point at height z;
                           ledge = max over z (up to the profile's widest point) of r(z - 0.75) - r(z + 0.75): how far the
                           surface just below a height sticks out beyond the surface just above it. A rounded digit standing on a pad narrower than itself
                           has r non-decreasing up to its widest point, so ledge <= ~0. PASS iff every toe <= 0.25 mm.
                           Reason: half the paws' 0.5 mm precision floor; the coin (the coat switching 0 -> 1.3 mm over
                           1.5 mm of height, LOCATE P1) reads ~1 mm on this statistic.
  P-DOME  pad doming + rim per pad: DOME RISE of the pad's own face (a flat plate reads 0) >= 0.15 mm, and RIM WALL
                           (p90 angle of the normal from straight down at the pad's outline) <= 65 deg (a plate's rim wall is
                           vertical). Reasons in check_dome.
  P-FURL  furless ramp     the furless mask's surface gradient (per triangle, p99.9) <= 0.80 / mm: a smoothstep ramp over
                           R >= 2 mm peaks at 1.5 / R = 0.75 / mm (+ 0.05 for the mesh's sampling).
  P-SEEN  seen side        the digits' crowns (front half, |v| < b/2, facing forward or up) vs Tripo inset by the coat:
                           |p50| <= 0.6 mm for fronts and tops (the coat's +-0.5 mm precision + 0.1 mm meshing). The
                           front-view outline of skin + coat vs Tripo is reported beside it (outline_report, not gated).
                           Depth along the view axis is reported (crown_depth), not gated: the photo cannot see it.
  P-SEAM  REGION seam      within 6 mm below a REGION's top face, the crop's distance to today's skin_v3 (same place, both
                           Tripo inset by the coat) p99 <= 0.3 mm: the hand-over at the REGION boundary is seamless.
  P-TOPO  topology         the crop (open only at its top cut) is ONE component with ONE boundary loop; genus reported.
  P-DEW   dewclaw + carpal (fore; NOTES_v3 13:33: L1 IS the dewclaw) prominence of the dewclaw digit over the leg
                           (+-7 mm along it, on the measured normal line) >= 1.5 mm with its pad furless and its sheath
                           open; the carpal pad's prominence >= 0.8 mm. Reasons in check_dew. FAILS on skin_v3's soft lump.
  P-SHTH  claw sheaths     every declared sheath pocket is open air on the crop: a ray from the opening along its axis
                           travels >= 2.0 mm before it meets skin (not sealed at the contract grid).
usage:
  python paws_checks.py skinv3   (HEAVY: reads skin_v3.npz once) -> tripo_rebuild/layers/paws_v3b_skinv3_crops.npz
  python paws_checks.py crop [paws...] [vox=0.10]  (HEAVY per paw)  -> tripo_rebuild/layers/paws_v3b_crop_<paw>.npz
  python paws_checks.py checks   -> tripo_rebuild/layers/paws_v3b_checks.json (all checks on the crops + skin_v3 + plants)
"""
import json
import os
import sys
import time

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
TR = os.path.join(ROOT, "tripo_rebuild"); LAYERS = os.path.join(TR, "layers")
FEAT = os.path.join(ROOT, "engine", "packs", "felid", "features"); FELID = os.path.join(ROOT, "engine", "packs", "felid")
for p_ in (TR, FEAT, FELID):
    if p_ not in sys.path: sys.path.insert(0, p_)
import feat_paws_v3 as FP  # noqa: E402
import paws_lib as PL  # noqa: E402
import paws_toes as PTo  # noqa: E402

D_ = FP.D_
CLEFT_MIN = D_["CLEFT_MIN_MM"]; CLEFT_FUR_MIN = D_["CLEFT_FUR_MIN_MM"]; COAT_TYP = 1.3
LEDGE_MAX = 0.25; DOME_MIN = 0.15; RIM_WALL_MAX = 65.0; FURL_GRAD_MAX = 0.80; SEEN_TOL = 0.6; SEEN_P90 = 1.5; SEAM_P99 = 0.3; SHEATH_MIN = 2.0
PJ = json.load(open(os.path.join(LAYERS, "paws.json")))["paws"]


import os as _os_mg, sys as _sys_mg  # noqa: E402  (build A1: the engine's one closest point, normals, cotangent Laplacian)
_MG_DIR = _os_mg.path.normpath(_os_mg.path.join(_os_mg.path.dirname(_os_mg.path.abspath(__file__)), '../tools'))
if _MG_DIR not in _sys_mg.path:
    _sys_mg.path.append(_MG_DIR)
import mesh_geom as _MG  # noqa: E402


def _adiff(a, b):
    return (a - b + np.pi) % (2 * np.pi) - np.pi


# =====================================================================  meshing a paw REGION at the contract grid
def mesh_region(k, vox=0.10, fn=None, zmax=None, coarse=0.5, band=1.2, slab_layers=20, verbose=True):
    """adaptive fine mesh of paw k's REGION: the field on a coarse grid; coarse cells with a corner |F| < band (dilated by
    one cell) are ACTIVE and get every fine node evaluated; other fine nodes take the coarse cell's sign (no surface there:
    |F| >= band = 1.2 mm > the cell diagonal x |grad F|). Marching cubes per z-slab of fine layers; slabs share a layer,
    whose vertices are welded by exact coordinates. Returns V (mm), F, stats."""
    from scipy import ndimage
    from skimage import measure
    R = FP.REG[k]; lo = np.array(R["lo_mm"], float); hi = np.array(R["hi_mm"], float)
    if zmax is not None: hi[2] = min(hi[2], zmax)
    fn = fn or (lambda P: FP.paw_field(k, P)); t0 = time.time()
    r = int(round(coarse / vox)); nc = np.ceil((hi - lo) / coarse).astype(int) + 1; hi = lo + (nc - 1) * coarse
    G = np.stack(np.meshgrid(*[lo[i] + np.arange(nc[i]) * coarse for i in range(3)], indexing="ij"), -1).reshape(-1, 3)
    Fc = np.empty(len(G))
    for a in range(0, len(G), 400000): Fc[a:a + 400000] = fn(G[a:a + 400000])
    Fc = Fc.reshape(nc); near = np.abs(Fc) < band; cell = np.zeros(tuple(nc - 1), bool); pos = Fc > 0
    anyp = np.zeros_like(cell); allp = np.ones_like(cell)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                s_ = (slice(dx, nc[0] - 1 + dx), slice(dy, nc[1] - 1 + dy), slice(dz, nc[2] - 1 + dz))
                cell |= near[s_]; anyp |= pos[s_]; allp &= pos[s_]
    cell |= anyp & ~allp; act = ndimage.binary_dilation(cell, np.ones((3, 3, 3), bool))
    sgn_cell = np.where(allp, 1.0, -1.0)
    nf = (nc - 1) * r + 1; Vs, Fs = [], []; nv = 0; n_eval = 0
    kz = 0
    while kz < nf[2] - 1:
        k1 = min(kz + slab_layers, nf[2] - 1); L = k1 - kz + 1
        A = np.empty((nf[0], nf[1], L), np.float32)
        # default: the sign of the coarse cell holding each fine node (the cell below/left for nodes on cell faces)
        ci = np.minimum(np.arange(nf[0]) // r, nc[0] - 2); cj = np.minimum(np.arange(nf[1]) // r, nc[1] - 2)
        ck = np.minimum(np.arange(kz, k1 + 1) // r, nc[2] - 2)
        A[:] = sgn_cell[np.ix_(ci, cj, ck)]
        # active fine nodes: every node of an active cell (cells overlapping this slab)
        cks = np.unique(np.r_[ck, np.minimum((np.arange(kz, k1 + 1) - 1).clip(0) // r, nc[2] - 2)])
        ac = np.argwhere(act[:, :, cks.min():cks.max() + 1]); ac[:, 2] += cks.min()
        if len(ac):
            off = np.stack(np.meshgrid(np.arange(r + 1), np.arange(r + 1), np.arange(r + 1), indexing="ij"), -1).reshape(-1, 3)
            for a in range(0, len(ac), 20000):
                nodes = (ac[a:a + 20000, None, :] * r + off[None]).reshape(-1, 3)
                nodes = nodes[(nodes[:, 2] >= kz) & (nodes[:, 2] <= k1)]
                if not len(nodes): continue
                nodes = np.unique(nodes, axis=0); n_eval += len(nodes)
                P = lo + nodes * vox; A[nodes[:, 0], nodes[:, 1], nodes[:, 2] - kz] = fn(P)
        if (A.min() < 0) and (A.max() > 0):
            V, F, _, _ = measure.marching_cubes(A, 0.0, spacing=(vox,) * 3)
            V = V + lo + np.array([0, 0, kz * vox]); Vs.append(V); Fs.append(F + nv); nv += len(V)   # skimage's faces are OUTWARD here (checked: cos(N, grad F) = +1)
        kz = k1
        if verbose: print(f"   slab to z {lo[2] + k1 * vox:6.2f} mm: {n_eval} nodes, {time.time() - t0:6.1f} s", flush=True)
    V = np.vstack(Vs); F = np.vstack(Fs)
    key = np.round(V / (vox * 1e-4)).astype(np.int64); _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    V = V[idx]; F = inv.reshape(-1)[F]
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    return V, F, dict(vox_mm=vox, nodes_evaluated=int(n_eval), active_cells=int(act.sum()), seconds=round(time.time() - t0, 1), verts=int(len(V)), tris=int(len(F)))


def vnormals(V, F):
    return _MG.vertex_normals(V, F, eps=1e-30)


# =====================================================================  P-SEP toe separation
def paw_geom(k):
    p = PJ[k]; C = np.array(p["pads"]["central"]["core_outline"]["centroid_mm"])
    cl = list(p["clefts"].keys()); cdir = np.radians([p["clefts"][c]["direction_deg"] for c in cl])
    sb = np.array([p["clefts"][c]["pads_rear_edge_from_C_mm"] for c in cl])
    return C, cdir, sb, cl


def cleft_notches(V, F, k, zs, offset=0.0):
    """per cleft (Tripo's measured directions) and height: the cleft notch depth (mm) on the horizontal section;
    offset > 0 dilates the section by `offset` mm first (the coat laid on: the notch the fur surface keeps)"""
    from shapely.geometry import Polygon
    C, cdir, sb, cl = paw_geom(k); out = np.full((len(cl), len(zs)), np.nan)
    for zi, z in enumerate(zs):
        loops = [L for L in PL.plane_section(V, F, np.array([0, 0, z]), [0, 0, 1]) if L["closed"] and len(L["P"]) >= 8
                 and np.linalg.norm(L["P"][:, :2].mean(0) - C) < 35]
        for L in loops:
            P2 = L["P"][:, :2]
            if offset > 0:
                g = Polygon(P2).buffer(offset, quad_segs=16)
                if g.geom_type != "Polygon": g = max(g.geoms, key=lambda q: q.area)
                P2 = np.asarray(g.exterior.coords)[:-1]
            for d in PTo.defects(P2):
                q = P2[d["j"]]; aq = np.arctan2(*(q - C)[::-1])
                ea, eb = np.arctan2(*(P2[d["a"]] - C)[::-1]), np.arctan2(*(P2[d["b"]] - C)[::-1])
                for i in range(len(cl)):
                    if abs(_adiff(aq, cdir[i])) > np.radians(10): continue
                    if (q - C) @ np.array([np.cos(cdir[i]), np.sin(cdir[i])]) < sb[i]: continue
                    if np.sign(_adiff(ea, cdir[i])) == np.sign(_adiff(eb, cdir[i])): continue
                    if not np.isfinite(out[i, zi]) or d["depth"] > out[i, zi]: out[i, zi] = d["depth"]
    return out, cl


def sep_band(k):
    pw = FP.paw(k); zc = float(np.mean([T_["z_c"] for T_ in pw.hull]))
    return np.round(np.arange(pw.z_s + 1.0, zc + 1e-6, 0.5), 3)


def check_sep(V, F, k):
    zs = sep_band(k); skin, cl = cleft_notches(V, F, k, zs); fur, _ = cleft_notches(V, F, k, zs, offset=COAT_TYP); res = {}; ok = True
    for i, c in enumerate(cl):
        present = np.isfinite(skin[i]); frac = float(present.mean())
        s50 = float(np.nanmedian(skin[i])) if present.any() else 0.0
        f50 = float(np.nanmedian(np.where(np.isfinite(fur[i]), fur[i], 0.0)))
        good = frac >= 0.5 and s50 >= CLEFT_MIN and f50 >= CLEFT_FUR_MIN; ok &= good
        res[c] = dict(present_frac=round(frac, 3), skin_notch_p50_mm=round(s50, 3), fur_notch_p50_mm=round(f50, 3),
                      skin_notch_by_z_mm=[None if not np.isfinite(x) else round(float(x), 2) for x in skin[i]], status="PASS" if good else "FAIL")
    return dict(status="PASS" if ok else "FAIL", band_z_mm=[float(zs[0]), float(zs[-1])], clefts=res,
                pass_mark=f"every cleft: present >= 50 % of heights, skin p50 >= {CLEFT_MIN} mm, fur (+{COAT_TYP} mm) p50 >= {CLEFT_FUR_MIN} mm")


# =====================================================================  P-COIN no coin ledge
def profile_r(V, F, A, ang, zs):
    """r(z): outermost distance from the vertical axis through A along direction ang, on the half-plane section"""
    t = np.array([np.cos(ang), np.sin(ang), 0.0]); n = np.array([-t[1], t[0], 0.0]); r = np.full(len(zs), np.nan)
    for L in PL.plane_section(V, F, np.r_[A, 0.0], n):
        P = L["P"]; u = (P[:, :2] - A) @ t[:2]; z = P[:, 2]
        Q = np.roll(np.c_[u, z], -1, 0) if L["closed"] else np.c_[u, z][1:]
        Pp = np.c_[u, z] if L["closed"] else np.c_[u, z][:-1]
        for zi, zz in enumerate(zs):
            cr = np.flatnonzero((Pp[:, 1] - zz) * (Q[:, 1] - zz) < 0)
            if not len(cr): continue
            tt = (zz - Pp[cr, 1]) / (Q[cr, 1] - Pp[cr, 1]); uu = Pp[cr, 0] + tt * (Q[cr, 0] - Pp[cr, 0]); uu = uu[uu > 0]
            if len(uu): r[zi] = np.nanmax([r[zi], uu.max()])
    return r


def check_coin(V, F, k, h=0.75):
    p = PJ[k]; res = {}; ok = True
    for t in ["toe1_medial", "toe2", "toe3", "toe4_lateral"]:
        A = np.array(p["pads"][t]["core_outline"]["centroid_mm"]); a0 = np.radians(p["toes"][t]["direction_deg"]); ztip = float(p["toes"][t]["tip_mm"][2])
        zs = np.round(np.arange(0.2, ztip + h + 1e-6, 0.1), 3); worst = -np.inf; where = None
        for dphi in np.radians(np.arange(-50, 51, 10)):
            r = profile_r(V, F, A, a0 + dphi, zs); j0 = int(round(h / 0.1))
            led = r[:-2 * j0] - r[2 * j0:]                 # r(z - h) - r(z + h) at z = zs[j0:-j0]
            if np.isfinite(r).any():                       # below the profile's widest point only (its top's own rounding is no ledge)
                jw = int(np.nanargmax(r)); led = np.where(np.arange(len(led)) + 2 * j0 <= jw, led, np.nan)
            if np.isfinite(led).any():
                j = int(np.nanargmax(led))
                if led[j] > worst: worst = float(led[j]); where = dict(z_mm=float(zs[j + j0]), phi_deg=float(np.degrees(dphi)))
        good = worst <= LEDGE_MAX; ok &= good
        res[t] = dict(ledge_mm=round(worst, 3), at=where, status="PASS" if good else "FAIL")
    return dict(status="PASS" if ok else "FAIL", toes=res, pass_mark=f"ledge (r(z-{h}) - r(z+{h}), max over z and +-50 deg) <= {LEDGE_MAX} mm per toe")


# =====================================================================  P-DOME pad doming and soft rim
def check_dome(V, F, k, domes=None):
    """per pad (footprint from the build's geometry record):
      DOME RISE = the pad face's height at 55-70 % of its radius above its lowest point (a flat plate: 0);
      RIM WALL  = p90 of the angle between the surface normal and straight down, on the skin within +-15 % of the pad's
                  outline and below the sole plane + 0.3 mm (a plate's or a cut half-ellipsoid's rim wall is vertical: 90).
    PASS iff rise >= 0.15 mm (a spherical cap whose rim stands 0.6 mm - the smallest measured Tripo pad free height - above
    its apex rises 0.6 x 0.6^2 = 0.22 mm at 60 % of its radius; 2/3 of that) and rim wall p90 <= 65 deg (the soft-rim dome
    meets the sole at ~37 deg, spec DOME_C_OVER_H; 65 = halfway to a vertical wall, with room for the normals' scatter)."""
    pw = FP.paw(k); domes = domes or pw.domes; res = {}; ok = True; N = vnormals(V, F)
    for D in domes:
        part = D["parts"][0]; cen = part["cen"][:2]; Rm = part["R"][:2, :2]; ax = part["ax"]; h = part["h"]; c_ = ax[2]
        fs = np.sqrt(1 - (1 - h / c_) ** 2); A2 = ax[:2] * fs                      # footprint semi-axes at the sole plane
        q = (V[:, :2] - cen) @ Rm; e = np.sqrt(((q / A2) ** 2).sum(1)); low = V[:, 2] < pw.z_s + 0.5
        inner = (e < 0.3) & low; ring = (e > 0.55) & (e < 0.7) & low; rim = (e > 0.85) & (e < 1.15) & (V[:, 2] < pw.z_s + 0.3)
        if not inner.any() or not ring.any() or not rim.any():
            res[D["pad"]] = dict(status="FAIL", why="no pad surface found"); ok = False; continue
        rise = float(np.median(V[ring, 2]) - V[inner, 2].min())
        wall = float(np.percentile(np.degrees(np.arccos(np.clip(-N[rim, 2], -1, 1))), 90))
        good = rise >= DOME_MIN and wall <= RIM_WALL_MAX; ok &= good
        res[D["pad"]] = dict(dome_rise_mm=round(rise, 3), rim_wall_p90_deg=round(wall, 1), status="PASS" if good else "FAIL")
    return dict(status="PASS" if ok else "FAIL", pads=res, pass_mark=f"dome rise >= {DOME_MIN} mm and rim wall p90 <= {RIM_WALL_MAX} deg, every pad")


# =====================================================================  P-FURL furless ramp along the skin
def check_furless(V, F, mask):
    """per-triangle surface gradient magnitude of a per-vertex mask (linear in each triangle)"""
    A, B, Cc = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]; mA, mB, mC = mask[F[:, 0]], mask[F[:, 1]], mask[F[:, 2]]
    e1, e2 = B - A, Cc - A; n = np.cross(e1, e2); a2 = (n * n).sum(1); ok_ = a2 > 1e-12
    g = (np.cross(n, e2) * (mB - mA)[:, None] + np.cross(e1, n) * (mC - mA)[:, None]) / np.where(ok_, a2, 1)[:, None]
    gm = np.linalg.norm(g, axis=1)[ok_ & (np.maximum.reduce([mA, mB, mC]) > 0.0)]
    p999 = float(np.percentile(gm, 99.9)) if len(gm) else 0.0
    return dict(status="PASS" if p999 <= FURL_GRAD_MAX else "FAIL", grad_p999_per_mm=round(p999, 3), grad_max_per_mm=round(float(gm.max()) if len(gm) else 0.0, 3),
                pass_mark=f"furless-mask surface gradient p99.9 <= {FURL_GRAD_MAX} / mm (smoothstep over >= 2 mm peaks at 0.75)")


# =====================================================================  P-SEEN seen side vs Tripo
def _silhouette(V, F, d, up, center, size, px):
    sys.path.insert(0, os.path.join(ROOT, "cases", "cat1", "v3_skinfix", "locate_data")); import render as RV   # the LOCATE rasteriser, reused
    sh, *_ = RV.render(V, F, d, up, px, center=center, size=size)
    return np.isfinite(sh)


def outline_report(V, F, k, tripo, px=0.05):
    """the seen side as the photo sees it: the paw's FRONT-VIEW silhouette (view along the paw's forward axis, the
    camera's side) of skin + coat (each vertex pushed out along its normal by the coat depth there) against Tripo's,
    below the digits' tops + 1 mm. Boundary-to-boundary distance, both ways, p50 <= 0.6 mm (the coat's own +-0.5 mm
    precision + 0.1 mm rasterising) and p90 <= 1.5 mm. Depth along the view axis is not seen by the photo, so it is not
    gated here (it is reported by `crown_depth`: the digits' fronts sit ~1 mm behind Tripo minus the coat, TOE_PROFILE_P).
    Photo-side: via Tripo (camera_tripo failed its hold-out: estimated)."""
    from scipy import ndimage
    pw = FP.paw(k); p = PJ[k]; fwd = np.r_[np.array(p["forward_axis_xy"]) / np.linalg.norm(p["forward_axis_xy"]), 0.0]
    ztop = max(T_["z_c"] + T_["c_up"] for T_ in pw.hull) + 1.0
    N = vnormals(V, F); Vd = V + N * FP.d_mm(k, V)[:, None]
    keepA = (Vd[F][:, :, 2] < ztop).all(1); Tv, Tf = tripo; keepB = (Tv[Tf][:, :, 2] < ztop).all(1)
    up = np.array([0, 0, 1.0]); d = -fwd                                        # camera in front, looking back at the toes
    allv = np.vstack([Vd, Tv]); r = np.cross(d, up); r /= np.linalg.norm(r)
    X = allv @ r; Z = allv[:, 2]; center = 0.5 * (X.min() + X.max()) * r + 0.5 * ztop * up
    size = (X.max() - X.min() + 4, ztop + 4)
    A = _silhouette(Vd, F[keepA], d, up, center, size, px); B = _silhouette(Tv, Tf[keepB], d, up, center, size, px)
    rows = np.arange(A.shape[0]); zrow = (center @ up) + size[1] / 2 - (rows + 0.5) * px
    band = (zrow > pw.z_s + 2.0) & (zrow < ztop - 0.5)                   # the sole (pads, short hair) is not dilated by the coat
    # the OUTLINE the photo sees: per row the outer left / right extents (the cleft notches inside it are the designed
    # anatomy and do not count), per digit the top height on the digit centre's column
    cols = np.arange(A.shape[1])
    def ext(M):
        L = np.where(M.any(1), M.argmax(1), -1); R_ = np.where(M.any(1), M.shape[1] - 1 - M[:, ::-1].argmax(1), -1); return L, R_
    (La, Ra), (Lb, Rb) = ext(A), ext(B); ok_r = band & (La >= 0) & (Lb >= 0)
    dl = np.abs(La[ok_r] - Lb[ok_r]) * px; dr = np.abs(Ra[ok_r] - Rb[ok_r]) * px
    side_p50 = float(np.median(np.r_[dl, dr])); side_p90 = float(np.percentile(np.r_[dl, dr], 90))
    iou = float((A & B & band[:, None]).sum() / max((A | B)[band].sum(), 1))
    return dict(outline_side_dist_p50_p90_mm=[round(side_p50, 3), round(side_p90, 3)], iou=round(iou, 4), px_mm=px,
                note="REPORT (not gated): front-view outline of skin + coat (vertex normals x coat depth) vs Tripo, rows above the sole + 2 mm",
                label="checked vs Tripo; photo via Tripo (estimated: camera_tripo failed its hold-out)")


def check_seen(V, F, k, tripo):
    """the SEEN side: the digits' crowns (|v| < b/2, front half, facing forward or up: what the photo shows from the
    front and above) against Tripo inset by the coat (exact distance inside Tripo minus the coat depth there). PASS iff
    |p50| <= 0.6 mm for the fronts AND the tops (the coat's own +-0.5 mm precision + 0.1 mm meshing). Photo-side: via
    Tripo (camera_tripo failed its hold-out: estimated). The front-view outline is reported beside it (outline_report)."""
    from twosided import MeshDist
    p = PJ[k]; fwd = np.r_[np.array(p["forward_axis_xy"]) / np.linalg.norm(p["forward_axis_xy"]), 0.0]
    pw = FP.paw(k); N = vnormals(V, F); crown = np.zeros(len(V), bool)
    for T_ in pw.hull:
        q = V[:, :2] - T_["cen"]; u = q @ T_["t"]; v = q @ T_["n"]; b = 0.5 * (T_["b"][1] + T_["b"][-1])
        crown |= (np.abs(v) < 0.5 * b) & (u > 0)
    out = {}; ok = True; md = MeshDist(tripo[0] / 1000, tripo[1])
    for nm, sel in (("fronts", crown & ((N @ fwd) > 0.5)), ("tops", crown & (N[:, 2] > 0.5))):
        sel = sel & (V[:, 2] > pw.z_s + 1.0) & (pw.toe_weight(V) > 0.99)
        if not sel.any(): ok = False; continue
        _, sd = md(V[sel] / 1000); ex = -sd * 1000 - FP.d_mm(k, V[sel]); q = np.percentile(ex, [10, 50, 90])
        out[nm] = dict(n=int(sel.sum()), inset_minus_coat_p10_p50_p90_mm=[round(float(x), 3) for x in q]); ok &= abs(q[1]) <= SEEN_TOL
    return dict(status="PASS" if ok else "FAIL", pass_mark=f"|p50(distance inside Tripo - coat)| <= {SEEN_TOL} mm on the digits' crown fronts and tops",
                label="checked vs Tripo; photo via Tripo (estimated: camera_tripo failed its hold-out)", **out)


# =====================================================================  P-SEAM REGION hand-over
def check_seam(V, k, skin):
    from twosided import MeshDist
    R = FP.REG[k]; top = R["hi_mm"][2]; sel = (V[:, 2] > top - 6.0) & (V[:, 2] < top - 0.3)
    m = np.all((skin[0][skin[1]][:, :, 2] > top - 9.0), 1); Sf = skin[1][m]
    if not sel.any() or not len(Sf): return dict(status="FAIL", why="empty")
    md = MeshDist(skin[0] / 1000, Sf); d, _ = md(V[sel] / 1000); d = d * 1000; p99 = float(np.percentile(d, 99))
    return dict(status="PASS" if p99 <= SEAM_P99 else "FAIL", n=int(sel.sum()), dist_to_skin_v3_p50_p99_mm=[round(float(np.median(d)), 3), round(p99, 3)],
                pass_mark=f"exact distance to today's skin_v3, p99 <= {SEAM_P99} mm within 6 mm below the REGION top")


# =====================================================================  P-TOPO
def check_topo(V, F):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    nv = len(V); A = coo_matrix((np.ones(3 * len(F)), (np.r_[F[:, 0], F[:, 1], F[:, 2]], np.r_[F[:, 1], F[:, 2], F[:, 0]])), shape=(nv, nv))
    nc, lab = connected_components(A, directed=False); used = np.unique(F); ncomp = len(np.unique(lab[used]))
    e = np.sort(np.c_[np.r_[F[:, 0], F[:, 1], F[:, 2]], np.r_[F[:, 1], F[:, 2], F[:, 0]]], axis=1)
    ue, cnt = np.unique(e, axis=0, return_counts=True); bd = ue[cnt == 1]; nonman = int((cnt > 2).sum())
    if len(bd):
        B = coo_matrix((np.ones(len(bd)), (bd[:, 0], bd[:, 1])), shape=(nv, nv)); _, bl = connected_components(B, directed=False)
        nloops = len(np.unique(bl[np.unique(bd)]))
    else:
        nloops = 0
    chi = len(used) - len(ue) + len(F); genus = (2 - chi - nloops) / 2 if ncomp == 1 else None
    comp_sizes = np.bincount(lab[F[:, 0]]); small = int((comp_sizes[comp_sizes > 0] < 0.01 * len(F)).sum())
    good = ncomp == 1 and nloops == 1 and nonman == 0
    return dict(status="PASS" if good else "FAIL", components=int(ncomp), small_components=small, boundary_loops=int(nloops), nonmanifold_edges=nonman,
                genus=genus, pass_mark="one component, one boundary loop (the REGION's top cut), no non-manifold edge; genus reported")


# =====================================================================  P-SHTH claw sheaths open
def check_sheaths(V, F, k):
    """free depth of each declared pocket on THIS mesh: the ray along the pocket axis from outside, minus the mean depth at
    which four parallel rays 1.5 x the pocket's half-width beside it meet the skin (the mesh's own surface there): an open
    pocket reads ~its depth, a sealed one or no pocket ~0"""
    pw = FP.paw(k); res = []; ok = True
    for s in pw.sh:
        a = s["ax"] / np.linalg.norm(s["ax"]); O = s["O"] - 1.0 * a; l = s["lat"] - (s["lat"] @ a) * a; l /= np.linalg.norm(l); h = np.cross(a, l)
        t0 = _ray_first(V, F, O, a, reach=s["L"] + 4)
        side = [_ray_first(V, F, O + o, a, reach=s["L"] + 4) for o in (1.5 * s["hw"] * l, -1.5 * s["hw"] * l, 2.5 * s["ht"] * h, -2.5 * s["ht"] * h)]
        side = [x for x in side if np.isfinite(x)]
        free = float(t0 - np.mean(side)) if (np.isfinite(t0) and side) else (np.inf if side else -np.inf)
        good = free >= SHEATH_MIN; ok &= good
        res.append(dict(free_depth_mm=(round(free, 3) if np.isfinite(free) else None), status="PASS" if good else "FAIL"))
    return dict(status="PASS" if ok else "FAIL", sheaths=res, pass_mark=f"free depth along the pocket axis beyond the skin beside it >= {SHEATH_MIN} mm")


# =====================================================================  P-DEW dewclaw + carpal pad defined (fore paws)
DEW_PROM_MIN = 2.5; CARPAL_PROM_MIN = 1.5


def _ray_first(V, F, O, a, reach=12.0):
    """distance from O along unit a to the first triangle of (V, F) (Moller-Trumbore over triangles near the ray)"""
    T = V[F]; mid = T.mean(1); rel = mid - O; s = rel @ a; perp = np.linalg.norm(rel - np.outer(s, a), axis=1)
    m = (s > -2) & (s < reach + 2) & (perp < 3.0); Tn = T[m]
    if not len(Tn): return np.inf
    e1, e2 = Tn[:, 1] - Tn[:, 0], Tn[:, 2] - Tn[:, 0]; pv = np.cross(a, e2); det = (e1 * pv).sum(1); ok_ = np.abs(det) > 1e-12
    inv = 1 / np.where(ok_, det, 1); tv = O - Tn[:, 0]; u = (tv * pv).sum(1) * inv; qv = np.cross(tv, e1); v = (a[None] * qv).sum(1) * inv
    t = (e2 * qv).sum(1) * inv; hit = ok_ & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
    return float(t[hit].min()) if hit.any() else np.inf


def prominence(V, F, P0, n, along, off):
    """how far the surface at P0 stands out along n beyond the mean of the surface at P0 +- off * along (same normal
    lines, rays cast from 6 mm outside): a bump's height over its surroundings, independent of the view"""
    n = n / np.linalg.norm(n); along = along - (along @ n) * n; along /= np.linalg.norm(along)
    d = [_ray_first(V, F, Q + 6.0 * n, -n) for Q in (P0, P0 + off * along, P0 - off * along)]
    return float(0.5 * (d[1] + d[2]) - d[0]) if np.all(np.isfinite(d)) else -np.inf, [round(x, 3) for x in d]


def check_dew(V, F, k, mask_fn):
    """NOTES_v3 13:33 (the person: L1 is the dewclaw, 'flagged because it got smoothed over'): on each forelimb the
    dewclaw is a DEFINED digit raised on the medial side with its own pad and claw sheath, and the carpal pad on the back
    of the wrist is defined. Probe lines are the MEASURED ones (paws.json section-lobe apex / wrist angle, the normal of
    Tripo's surface there), the same for every mesh; mask_fn = THAT mesh's furless mask (per vertex).
    PASS iff
      dewclaw prominence over +-7 mm along the leg >= 2.5 mm: a DIGIT, not a lump - it stands at least half its own width
        (5-6 mm, spec DEWCLAW) above the leg; Tripo's lobe inset by the coat reads <= 1.9 mm here (the plant);
      its pad is furless (mask >= 0.5 within the dewclaw) and its sheath pocket is open (free depth >= 2 mm, P-SHTH);
      carpal pad prominence over +-5 mm >= 1.5 mm and furless: clear of the measured wrist contour angle (Tripo 0.71-1.45 mm
        over its bridges, paws.json), so a contour angle cannot pass as a pad."""
    pw = FP.paw(k); rd, rc = pw.rec["dewclaw"], pw.rec["carpal"]; up = np.array([0, 0, 1.0])
    pd, dd = prominence(V, F, np.array(rd["skin_point_mm"]), np.array(rd["normal"]), up, 7.0)
    pc, dc = prominence(V, F, np.array(rc["skin_point_mm"]), np.array(rc["normal"]), up, 5.0)
    near_d = np.linalg.norm(V - pw.dc["cen"], axis=1) < max(pw.dc["ax"]) + 0.5
    near_c = np.linalg.norm(V - pw.cp["cen"], axis=1) < max(pw.cp["ax"]) + 0.5
    pad_d = bool(near_d.any() and mask_fn(V[near_d]).max() >= 0.5); pad_c = bool(near_c.any() and mask_fn(V[near_c]).max() >= 0.5)
    sh = check_sheaths(V, F, k)["sheaths"][-1]; sheath_ok = sh["status"] == "PASS"
    good = pd >= DEW_PROM_MIN and pad_d and sheath_ok and pc >= CARPAL_PROM_MIN and pad_c
    return dict(status="PASS" if good else "FAIL", dewclaw_prominence_mm=round(pd, 3), dewclaw_ray_depths_mm=dd, dewclaw_pad_furless=pad_d,
                dewclaw_sheath=sh, carpal_prominence_mm=round(pc, 3), carpal_ray_depths_mm=dc, carpal_pad_furless=pad_c,
                pass_mark=f"dewclaw prominence >= {DEW_PROM_MIN} mm with its pad furless and its sheath open; carpal prominence >= {CARPAL_PROM_MIN} mm and furless")


# =====================================================================  drivers
def _load_crop(path):
    Z = np.load(path); return Z["v"].astype(float), Z["f"].astype(np.int64)


def cmd_skinv3():
    """HEAVY: cut today's skin_v3 (layers/skin_v3.npz, 11.75 M tris) to the four paw REGIONS (+2 mm), streamed"""
    t0 = time.time(); Z = np.load(os.path.join(LAYERS, "skin_v3.npz")); V = Z["v"].astype(np.float32) * 1000; out = {}
    masks = {R["paw"]: np.all((V >= np.array(R["lo_mm"]) - 2) & (V <= np.array(R["hi_mm"]) + 2), 1) for R in FP.REGIONS}
    F = Z["f"]
    for k, m in masks.items():
        keep = m[F].all(1); Fk = F[keep]; u, inv = np.unique(Fk, return_inverse=True)
        out[f"{k}_v"] = V[u]; out[f"{k}_f"] = inv.reshape(-1, 3).astype(np.int32)
    np.savez_compressed(os.path.join(LAYERS, "paws_v3b_skinv3_crops.npz"), **out)
    print("skin_v3 paw crops", {k: int(v.shape[0]) for k, v in out.items() if k.endswith("_f")}, round(time.time() - t0, 1), "s")


def cmd_crop(paws, vox):
    for k in paws:
        V, F, st = mesh_region(k, vox=vox)
        np.savez_compressed(os.path.join(LAYERS, f"paws_v3b_crop_{k}.npz"), v=V.astype(np.float32), f=F.astype(np.int32), meta=json.dumps(st))
        print(k, st, flush=True)


def tripo_crop(k, pad=2.0):
    v, f, _ = PL.load_mesh(); v = v * 1000; R = FP.REG[k]
    m = np.all((v >= np.array(R["lo_mm"]) - pad) & (v <= np.array(R["hi_mm"]) + pad), 1); keep = m[f].all(1); Fk = f[keep]
    u, inv = np.unique(Fk, return_inverse=True); return v[u], inv.reshape(-1, 3)


# =====================================================================  planted cases (A10 / A22: each check FAILS on its defect, PASSES the build)
def _field_fn(k, kind=None):
    """the build's field, or a PLANTED defect of it (all mm). Every plant is sized to what its check reads."""
    pw = FP.paw(k)
    if kind is None:
        return lambda P: pw.field(P)
    if kind == "cleft_filled":                 # P-SEP: the middle cleft webbed shut over the digits' band
        A_, B_ = pw.hull[1], pw.hull[2]; mid = 0.5 * (A_["cen"] + B_["cen"]); cd = (B_["cen"] - A_["cen"]) / np.linalg.norm(B_["cen"] - A_["cen"])
        fwd = np.array([-cd[1], cd[0]]); fwd = fwd if fwd @ (A_["t"] + B_["t"]) > 0 else -fwd
        af = 0.5 * (A_["a_f"] + B_["a_f"]); zc = 0.5 * (A_["z_c"] + B_["z_c"]); Rm = np.c_[np.r_[fwd, 0], np.r_[cd, 0], [0, 0, 1.0]]
        cen = np.r_[mid + 0.5 * af * fwd, zc - 1.0]; ax = np.array([0.6 * af + 1.0, 3.0, 7.5])   # fills the gap from the centres to the fronts
        return lambda P: FP.smin(pw.field(P), FP.ell_sdf((P - cen) @ Rm, ax), 0.5)
    if kind == "coin":                         # P-COIN: today's construction - coat switched on over 1.5 mm of height
        return lambda P: pw.field(P) + 1.3 * FP.ss((P[:, 2] - pw.z_s - 1.0) / 1.5) * pw.toe_weight(P)
    if kind == "flat_plate":                   # P-DOME: every pad a flat plate with vertical edges
        def fn(P):
            F = pw.field_nopads(P, sheaths=False, pads=False)
            for D in pw.domes:
                for part in D["parts"]:
                    h = part["h"]; c = part["ax"][2]; fs = np.sqrt(1 - (1 - h / c) ** 2); a2 = part["ax"][:2] * fs
                    q = (P - part["cen"]) @ part["R"]; e2 = FP.ell_sdf(np.c_[q[:, 0], q[:, 1], np.zeros(len(P))], [a2[0], a2[1], 1.0])
                    low = part["cen"][2] - c; plate = np.maximum.reduce([e2, low - P[:, 2], P[:, 2] - (pw.z_s + 0.5)])
                    F = np.minimum(F, plate)
            if pw.fore: F = pw._fore(P, F)
            return FP.smax(F, -pw.sheath_sdf(P), D_["SHEATH"]["k_mm"])
        return fn
    if kind == "sharp_rim":                    # P-DOME: domes kept but cut as half-ellipsoids (vertical rim walls), no soft rim
        def fn(P):
            F = pw.field_nopads(P, sheaths=False, pads=False)
            for D in pw.domes:
                for part in D["parts"]:
                    h = part["h"]; c = part["ax"][2]; fs = np.sqrt(1 - (1 - h / c) ** 2); a2 = part["ax"][:2] * fs
                    q = (P - np.r_[part["cen"][:2], part["cen"][2] - c + h]) @ part["R"]
                    F = np.minimum(F, FP.ell_sdf(q, [a2[0], a2[1], h]))
            if pw.fore: F = pw._fore(P, F)
            return FP.smax(F, -pw.sheath_sdf(P), D_["SHEATH"]["k_mm"])
        return fn
    if kind == "toes_shrunk":                  # P-SEEN: the digits 1 mm smaller than the photo / Tripo shows
        return lambda P: pw.field(P) + 1.0 * pw.toe_weight(P)
    if kind == "no_fore_extras":               # P-DEW: no dewclaw digit, no carpal pad (Tripo's lobe / wrist inset only)
        def fn(P):
            F = pw.field_nopads(P, sheaths=False, pads=False); F = FP.smin(F, pw.pads_sdf(P), D_["K_PAD_MM"])
            sh = np.full(len(P), np.inf)
            for s_ in pw.sh[:4]:                   # the four toe sheaths only (no dewclaw to hold the fifth)
                sh = np.minimum(sh, FP.slot_sdf(P, s_["O"], s_["ax"], s_["lat"], s_["L"], s_["hw"], s_["ht"]))
            return FP.smax(F, -sh, D_["SHEATH"]["k_mm"])
        return fn
    if kind == "no_sheaths":                   # P-SHTH: the pockets sealed
        return lambda P: pw.field_nopads(P, sheaths=False, pads=True)
    raise KeyError(kind)


_MESHES = {}


def _mesh(k, kind=None, vox=0.25):
    key = (k, kind, vox)
    if key not in _MESHES:
        V, F, st = mesh_region(k, vox=vox, fn=_field_fn(k, kind), verbose=False); _MESHES[key] = (V, F, st)
    return _MESHES[key]


def decisions_check():
    """D1 (approved nose-leather top edge within 0.2 mm of v1) and the lip form (within 0.5 mm of v3 outside the fixed
    zones) cannot be moved by this module: (a) its REGIONS are disjoint from the nose and mouth REGIONS (world AABBs of
    their head-frame boxes, partition's head frame) and lie wholly below them, (b) edit() returns F bit-identical outside
    its REGIONS (random points over the whole cat and inside the nose / mouth boxes)."""
    import partition as PT
    import feat_mouth_v3 as FM
    import feat_nose_v3 as FN

    def world_box(lo, hi):
        c = np.array(np.meshgrid(*[[lo[i], hi[i]] for i in range(3)], indexing="ij")).reshape(3, -1).T
        W = (PT.HC + (c / 1000) @ PT.HR.T) * 1000; return W.min(0), W.max(0)
    boxes = {"nose": world_box(np.array(FN.REGION["lo_mm"]), np.array(FN.REGION["hi_mm"])),
             "mouth": world_box(np.asarray(FM.REGION[0], float), np.asarray(FM.REGION[1], float))}
    disjoint = {nm: all(bool(np.any(lo > np.array(R["hi_mm"])) or np.any(hi < np.array(R["lo_mm"]))) for R in FP.REGIONS) for nm, (lo, hi) in boxes.items()}
    rng = np.random.default_rng(3)
    P = np.vstack([rng.uniform([-80, -260, -5], [80, 260, 330], (200000, 3))] + [rng.uniform(lo, hi, (20000, 3)) for lo, hi in boxes.values()])
    out = ~np.any([FP._in_region(P, R) for R in FP.REGIONS], axis=0); F0 = rng.normal(0, 3, len(P))
    F1 = FP.edit(P, F0); identical = bool(np.array_equal(F1[out], F0[out]))
    zmax = max(R["hi_mm"][2] for R in FP.REGIONS); zhead = float(min(b[0][2] for b in boxes.values()))
    ok = all(disjoint.values()) and identical and zmax < zhead
    return dict(status="PASS" if ok else "FAIL", D1_leather_top_edge="unchanged by construction (checked)", lip_form="unchanged by construction (checked)",
                regions_disjoint_from=disjoint, edit_identity_outside_regions=identical, n_points_outside=int(out.sum()),
                paw_regions_z_max_mm=zmax, nose_mouth_boxes_z_min_mm=round(zhead, 1),
                boxes_world_mm={k_: [np.round(v[0], 1).tolist(), np.round(v[1], 1).tolist()] for k_, v in boxes.items()})


def edit_blend_check():
    """the REGION hand-over: at a REGION face edit() returns F_in exactly (w = 0); deep inside it returns the paw field"""
    R = FP.REGIONS[0]; k = R["paw"]; lo, hi = np.array(R["lo_mm"]), np.array(R["hi_mm"]); rng = np.random.default_rng(5)
    P = rng.uniform(lo, hi, (4000, 3)); P[:2000, 2] = hi[2]; F0 = rng.normal(0, 2, len(P)); F1 = FP.edit(P, F0)
    face = bool(np.allclose(F1[:2000], F0[:2000], atol=1e-12))
    inner = np.all((P[2000:] > lo + D_["BLEND_MM"]) & (P[2000:] < hi - D_["BLEND_MM"]), 1)
    deep = bool(np.allclose(F1[2000:][inner], FP.paw_field(k, P[2000:][inner]), atol=1e-9))
    return dict(status="PASS" if face and deep else "FAIL", at_top_face_equals_input=face, deep_inside_equals_paw_field=deep)


WANT_FAIL = (("P-SEP", ["skin_v3", "plant_cleft_filled"]), ("P-COIN", ["skin_v3", "plant_coin"]), ("P-DOME", ["plant_flat_plate"]),
             ("P-FURL", ["plant_coat_field_z_prism", "plant_ramp_1mm"]), ("P-SEEN", ["plant_toes_shrunk_1mm"]), ("P-SEAM", ["plant_offset_0p6"]),
             ("P-TOPO", ["plant_island", "plant_hole"]), ("P-SHTH", ["plant_sealed"]))


def main_checks(paws=None):
    t0 = time.time(); paws = paws or FP.PAWS
    out = dict(what="paws_checks (feat_paws_v3): every check on the build's crops, on today's skin_v3, and on planted defects",
               labels="checked = measured here", pass_marks=dict(CLEFT_MIN=CLEFT_MIN, CLEFT_FUR_MIN=CLEFT_FUR_MIN, LEDGE_MAX=LEDGE_MAX, DOME_MIN=DOME_MIN, RIM_WALL_MAX=RIM_WALL_MAX, FURL_GRAD_MAX=FURL_GRAD_MAX, SEEN_TOL=SEEN_TOL, SEAM_P99=SEAM_P99, SHEATH_MIN=SHEATH_MIN))
    out["decisions"] = decisions_check(); out["edit_blend"] = edit_blend_check()
    print("decisions", out["decisions"]["status"], "| edit blend", out["edit_blend"]["status"], flush=True)
    SK = np.load(os.path.join(LAYERS, "paws_v3b_skinv3_crops.npz"))
    import coat_field as CF
    for k in paws:
        rec = {}; cp = os.path.join(LAYERS, f"paws_v3b_crop_{k}.npz")
        if os.path.exists(cp):
            V, F = _load_crop(cp); rec["crop"] = json.loads(str(np.load(cp)["meta"]))
        else:
            V, F, st = _mesh(k); rec["crop"] = dict(st, note="0.10 mm crop missing: 0.25 mm used")
        Sv, Sf = SK[f"{k}_v"].astype(float), SK[f"{k}_f"].astype(np.int64); Tv, Tf = tripo_crop(k)
        Vq, Fq, _ = _mesh(k)
        rec["P-SEP"] = dict(build=check_sep(V, F, k), build_0p25=check_sep(Vq, Fq, k), skin_v3=check_sep(Sv, Sf, k),
                            plant_cleft_filled=check_sep(*_mesh(k, "cleft_filled")[:2], k), tripo_reference=check_sep(Tv, Tf, k))
        rec["P-COIN"] = dict(build=check_coin(V, F, k), skin_v3=check_coin(Sv, Sf, k), plant_coin=check_coin(*_mesh(k, "coin")[:2], k), tripo_reference=check_coin(Tv, Tf, k))
        rec["P-DOME"] = dict(build=check_dome(V, F, k), plant_flat_plate=check_dome(*_mesh(k, "flat_plate")[:2], k),
                             plant_sharp_rim_informational=check_dome(*_mesh(k, "sharp_rim")[:2], k))   # a ~1 mm half-ellipsoid: not reliably caught (stated)
        m_build = FP.furless_mask(V); m_cf = CF.masks(V / 1000)["paw_pads"]
        R0 = D_["FURLESS_RAMP_MM"]; D_["FURLESS_RAMP_MM"] = 1.0; m_1mm = FP.furless_mask(V); D_["FURLESS_RAMP_MM"] = R0
        rec["P-FURL"] = dict(build=check_furless(V, F, m_build), plant_coat_field_z_prism=check_furless(V, F, m_cf), plant_ramp_1mm=check_furless(V, F, m_1mm))
        rec["P-SEEN"] = dict(build=check_seen(V, F, k, (Tv, Tf)), plant_toes_shrunk_1mm=check_seen(*_mesh(k, "toes_shrunk")[:2], k, (Tv, Tf)),
                             outline_report=outline_report(V, F, k, (Tv, Tf)))
        Vp = V.copy(); top = FP.REG[k]["hi_mm"][2]; band = (V[:, 2] > top - 6.0); Vp[band] += 0.6 * vnormals(V, F)[band]
        rec["P-SEAM"] = dict(build=check_seam(V, k, (Sv, Sf)), plant_offset_0p6=check_seam(Vp, k, (Sv, Sf)))
        isl = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1.0]]) + V.mean(0) + 40; isf = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]) + len(V)
        rec["P-TOPO"] = dict(build=check_topo(V, F), plant_island=check_topo(np.vstack([V, isl]), np.vstack([F, isf])),
                             plant_hole=check_topo(V, F[np.r_[0:len(F) // 2, len(F) // 2 + 30:len(F)]]))
        rec["P-SHTH"] = dict(build=check_sheaths(V, F, k), plant_sealed=check_sheaths(*_mesh(k, "no_sheaths")[:2], k),
                             contract_0p5mm_grid=check_sheaths(*_mesh(k, None, 0.5)[:2], k))
        if FP.paw(k).fore:
            cfm = lambda Q: CF.masks(Q / 1000)["paw_pads"]                 # skin_v3's own furless mask (coat_field)
            rec["P-DEW"] = dict(build=check_dew(V, F, k, FP.furless_mask), skin_v3=check_dew(Sv, Sf, k, cfm),
                                plant_no_dewclaw_no_carpal=check_dew(*_mesh(k, "no_fore_extras")[:2], k, FP.furless_mask))
        out[k] = rec
        print(k, {c: {kk: v.get("status") for kk, v in r.items() if isinstance(v, dict)} for c, r in rec.items() if c.startswith("P-")}, round(time.time() - t0), "s", flush=True)
    proofs = {c: {k: dict(build_passes=out[k][c]["build"]["status"] == "PASS", **{f"{w}_fails": out[k][c][w]["status"] == "FAIL" for w in wf}) for k in paws if c in out[k]}
              for c, wf in WANT_FAIL + (("P-DEW", ["skin_v3", "plant_no_dewclaw_no_carpal"]),)}
    out["proofs"] = proofs; out["all_proofs_hold"] = all(all(all(v.values()) for v in pc.values()) for pc in proofs.values()); out["seconds"] = round(time.time() - t0, 1)
    json.dump(FP._jsonable(out), open(os.path.join(LAYERS, "paws_v3b_checks.json"), "w"), indent=1)
    print(json.dumps(FP._jsonable(proofs), indent=0)); print("all proofs hold:", out["all_proofs_hold"], "seconds", out["seconds"])
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "checks"
    if cmd == "skinv3":
        cmd_skinv3()
    elif cmd == "crop":
        args = [a for a in sys.argv[2:] if not a.startswith("vox=")]; vox = float(([a for a in sys.argv[2:] if a.startswith("vox=")] or ["vox=0.10"])[0][4:])
        cmd_crop(args or FP.PAWS, vox)
    elif cmd == "checks":
        main_checks([a for a in sys.argv[2:]] or None)
