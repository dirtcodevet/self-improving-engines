"""CONTACT CREASE (2026-10-19, woman2 v5): round the crease where two soft surfaces of one body press together
(an arm resting on the chest wall, a thigh on a thigh, a chin on a neck).

Why: at rest the woman2 arm's medial side was a flat plane pressed on the side wall, meeting the arm's free surface
in a sharp corner (radius ~3 mm). From the front it read as a raised lip along the contact line. Two elastic bodies
pressed together don't leave a corner: outside the contact patch the gap opens smoothly from zero (Hertz contact:
the gap grows like (r - a)^1.5 past the patch edge a), so each surface curves away from the patch tangentially.
The fix is a solve, not a sculpt: on each side, a band around the patch EDGE is replaced by the smoothest surface
joining the patch (held where it is) and the free surface (held) - surface_fairing.fair's bi-Laplacian fill,
normal-only, with the other side as a clearance guard so the rounding never pushes one surface into the other.

contact_bands(V, F, partA, partB, touch, width, keep_inside)
  partA/partB: vertex masks of the two surfaces; touch: distance under which a vertex counts as in contact;
  width: band half-width around the patch edge; keep_inside: patch vertices deeper than this from the edge stay fixed.
  -> dict per side: band, fixed, protect (the other side's points near the patch), patch, edge
"""
import numpy as np
from scipy.spatial import cKDTree


def _normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3): np.add.at(vn, F[:, k], fn)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-20)


def contact_bands(V, F, partA, partB, touch, width, keep_inside, facing=-0.3):
    """the patch edge is found topologically (a patch vertex with a mesh neighbour on the same side outside the patch),
    so it holds on meshes whose density varies (the woman2 mesh is 0.16 mm at the nipple, ~1-2 mm on the arm).
    A contact needs the two surfaces FACING each other (normal dot < facing): where one mesh simply continues into the
    other (the woman2 shoulder, where the arm mask ends on a continuous surface) the points are close but the normals
    agree, and that line is not a contact (found 2026-10-19: without it the band covered the shoulder line)."""
    N = _normals(V, F)
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]); E = np.concatenate([E, E[:, ::-1]])
    out = {}
    for name, me, other in (("A", partA, partB), ("B", partB, partA)):
        io, im = np.where(other)[0], np.where(me)[0]
        d_other, j = cKDTree(V[io]).query(V[im])
        face = np.einsum("ij,ij->i", N[im], N[io[j]]) < facing
        patch = np.zeros(len(V), bool); patch[im[(d_other < touch) & face]] = True
        pe = np.where(patch)[0]
        if len(pe) == 0:
            out[name] = None; continue
        m = patch[E[:, 0]] & ~patch[E[:, 1]] & me[E[:, 1]]
        edge = np.zeros(len(V), bool); edge[E[m, 0]] = True                         # patch vertices beside free ones
        d_edge, _ = cKDTree(V[edge]).query(V[im])
        band = np.zeros(len(V), bool); band[im[d_edge < width]] = True
        fixed = np.zeros(len(V), bool); fixed[im[patch[im] & (d_edge >= keep_inside)]] = True
        guard = io[cKDTree(V[pe]).query(V[io])[0] < width + touch]
        out[name] = dict(band=band, fixed=fixed, protect=V[guard], patch=patch, edge=edge)
    return out



def revert_crossings(V0, V, F, zone_faces, crossing_pairs, radius, rounds=6):
    """Where a refill made faces cross, blend back toward the original surface (which had none) with a smooth falloff
    (1 at the crossing faces' vertices, 0 at `radius`), growing the blend until no crossing is left.
    Why (woman2 v5): a one-shot refill of a corner carrying ~1 mm hooks folds a few hooks through their neighbours
    (46 crossing pairs out of ~10k refilled vertices); the stage-2 push-apart resolver diverged on them (46 -> 553) and
    explicit smoothing went unstable. Local reversion converges by construction: the original had no crossings.
    Returns V, history of crossing counts."""
    r = np.zeros(len(V)); hist = []
    for k in range(rounds):
        X = V0 + (1 - r)[:, None] * (V - V0)
        P = crossing_pairs(X, F, zone_faces); hist.append(int(len(P)))
        if len(P) == 0:
            return X, hist
        seeds = np.unique(F[P.ravel()])
        d, _ = cKDTree(V0[seeds]).query(V0, distance_upper_bound=radius * (1 + k))
        w = np.clip(1 - d / (radius * (1 + k)), 0, 1); w = w * w * (3 - 2 * w)      # smoothstep falloff
        r = np.maximum(r, w)
    return V0 + (1 - r)[:, None] * (V - V0), hist
