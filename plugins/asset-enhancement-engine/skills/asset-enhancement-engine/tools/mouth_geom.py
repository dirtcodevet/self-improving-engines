# ONE definition of the engineered mouth (slit) geometry for every tool that needs it: sdf_core.slit_cavity
# (the shape), feature_smooth, lip_seal, rig jaw weights, case coat painting (Blender side).
# v27: five hand copies had drifted (outline power 4 vs 2.6, old thickness ramp): once the slit changed, the
# coat would have painted outer lip skin as mouth interior. Blender scripts: `import mouth_geom as MG;
# importlib.reload(MG)` (Blender caches modules across runs). numpy only (no scipy inside Blender).
import numpy as np


def lip_line(x, y, a, z0, slope, y_flat, droop=0.0, lobe_x=0.004, lobe_w=0.003, corner_rise=0.0):
    """mid-surface z of the separation: flat under the lips, rising toward the back (slope); dips under the two
    upper-lip lobes (two gaussians - smooth at the midline; v19-v26 exp(-((|x|-x0)/w)^2) had a cusp at x=0);
    corners rise."""
    zm = z0 + slope * np.maximum(0.0, y - y_flat)
    if droop or corner_rise:
        lobes = np.exp(-((x - lobe_x) / lobe_w) ** 2) + np.exp(-((x + lobe_x) / lobe_w) ** 2)
        zm = zm - droop * lobes + corner_rise * np.clip((np.abs(x) - 0.6 * a) / (0.4 * a), 0, 1) ** 2
    return zm


def outline_e(x, y, a, b, yc, power):
    """superellipse outline coordinate in the local xy plane (<1 inside the mouth outline)"""
    return (np.abs(x / a) ** power + np.abs((y - yc) / b) ** power) ** (1.0 / power)


def half_gap(e, gap_edge, gap_in, lip_e=1.0):
    """slab half-thickness: gap_edge through the lip zone (e > lip_e), ramping to gap_in (oral cavity) inside"""
    return gap_edge + (gap_in - gap_edge) * np.clip((lip_e - e) / 0.35, 0, 1)


def from_landmarks(L, hs):
    """head-local UNSCALED parameters (x/hs units). L['mouth'] is world-scaled (except slope/power/lip_e);
    L['mouth_lip'] is already unscaled."""
    M, lp = L["mouth"], L.get("mouth_lip", {})
    return dict(a=M["a"] / hs, b=M["b"] / hs, yc=M["yc"] / hs, z0=M["z0"] / hs, slope=M["slope"], y_flat=M["y_flat"] / hs,
                power=M.get("power", 4.0), gap_edge=M.get("gap_edge", 0.0009) / hs, gap_in=M.get("gap_in", 0.0042) / hs,
                lip_e=M.get("lip_e", 1.0), droop=lp.get("droop", 0.0), lobe_x=lp.get("lobe_x", 0.004),
                lobe_w=lp.get("lobe_w", 0.003), corner_rise=lp.get("corner_rise", 0.0),
                corner_hold=M.get("corner_hold", 0.0), warp=M.get("warp"))


def muzzle_map(y, dy, ya, yb):
    """forward map of head-local y (unscaled): the face in front of the eye plane (ya) is stretched forward, reaching
    a rigid shift of dy beyond yb (v32: muzzle depth from the anatomical prior - a frontal photo cannot see it)"""
    t = np.clip((y - ya) / (yb - ya), 0, 1)
    return y - dy * t * t * (3 - 2 * t)


def muzzle_unmap(y, dy, ya, yb):
    g = np.linspace(yb - 0.08, ya + 0.08, 4001)
    return np.interp(y, muzzle_map(g, dy, ya, yb), g)


def zm_e_h(x, y, G):
    """(mid-surface z, outline e, half-gap h) at head-local (x, y) for a parameter dict from from_landmarks"""
    if G.get("warp"):
        y = muzzle_unmap(y, *G["warp"])
    zm = lip_line(x, y, G["a"], G["z0"], G["slope"], G["y_flat"], G["droop"], G["lobe_x"], G["lobe_w"], G["corner_rise"])
    e = outline_e(x, y, G["a"], G["b"], G["yc"], G["power"])
    return zm, e, half_gap(e, G["gap_edge"], G["gap_in"], G["lip_e"])


def _ss(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def jaw_weight(hl, G):
    """jaw bone weight for head-local UNSCALED points hl (n,3). SHARP split along the lips (inside the slit
    outline, where geometry is already separate); behind the mouth corners the cheek skin is continuous -> soft
    vertical falloff (v1 sharp everywhere = 20x edge stretch streaks down the cheeks at 25 deg). Shared by rig.py
    and part_lab's open-jaw preview."""
    x, y, z = hl.T
    zm, e, _ = zm_e_h(x, y, G)
    head_zone = np.linalg.norm(hl - np.array([0, -0.005, 0.0]), axis=1) < 0.075
    sharp = _ss(zm + 0.0002, zm - 0.0012, z)
    soft = _ss(zm + 0.004, zm - 0.006, z)
    blend = _ss(0.92, 1.12, e)
    vert = sharp * (1 - blend) + soft * blend
    # v28: lower-lip skin near the corners is soft tissue that stays up while the mandible drops (the commissure
    # stretches diagonally) -> the meow opening tapers toward the corners instead of vertical "curtains". Only the
    # outer lip zone (e > 0.55) fades; teeth/tongue (e < 0.5) stay on the jaw.
    vert = vert * (1.0 - G.get("corner_hold", 0.0) * _ss(0.55, 0.97, e))
    a = G["a"]          # lateral falloff follows the outline (v28 corners moved back/out; was fixed 33->16 mm for a=17)
    return head_zone * vert * _ss(0.018, -0.002, y) * _ss(a + 0.016, a - 0.001, np.abs(x)) * _ss(-0.068, -0.046, z)


def open_jaw(hl, G, hinge, deg):
    """preview: rotate head-local points about the jaw hinge (x axis) by deg (front goes down), blended by
    jaw_weight (linear blend skinning, like the armature)"""
    w = jaw_weight(hl, G)
    a = np.radians(deg)
    p = hl - hinge
    rot = np.stack([p[:, 0], p[:, 1] * np.cos(a) - p[:, 2] * np.sin(a), p[:, 1] * np.sin(a) + p[:, 2] * np.cos(a)], 1)
    return hl + w[:, None] * (rot - p)
