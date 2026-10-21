"""SURFACE FAIRING by math (2026-10-19). Replaces a band of a surface with the smoothest surface that joins its
surroundings: minimise the squared umbrella Laplacian of the positions over the band, with every vertex outside the
band held fixed (a bi-Laplacian fill), then keep only each vertex's move along its normal (no sliding). Creases that
are real anatomy inside the band (strong concave curvature) can be held fixed. A clearance check against a protected
set (e.g. the arm) scales a vertex's move down wherever it would come closer than a minimum gap.

Why it exists: surface_analysis.py found a flat band then a bump on the outer curve of both breasts (curvature ~+20/m
falling to ~0 at 65-75 mm from the nipple, then ~+12/m at 85 mm) - "mild flattening" the person saw by eye. Fixing it
is a solve, not a sculpt.

usage (as a module): fair(V, F, band_mask, fixed_mask=None, protect_pts=None, min_gap=0.0005, no_outward=None) -> V_new, report
no_outward (2026-10-19, woman2 v5): a vertex mask whose moves may only go inward (along -normal). For two surfaces
pressed together: rounding a corner beside the contact cuts it back, and nothing beside the other surface moves toward it.
"""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.spatial import cKDTree


def umbrella_L(V, F):
    n = len(V); e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    A = sparse.coo_matrix((np.ones(len(e) * 2), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    deg = np.asarray(A.sum(1)).ravel()
    return sparse.eye(n) - sparse.diags(1 / np.maximum(deg, 1)) @ A


def vertex_normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3): np.add.at(vn, F[:, k], fn)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-20)


def dn_min(D, N, B):
    """the most inward normal component of the moves, mm (report only)"""
    return np.einsum("ij,ij->i", D[B], N[B]).min() * 1000


def fair(V, F, band, fixed=None, protect_pts=None, min_gap=0.0005, no_outward=None, normal_only=True):
    band = band.copy()
    if fixed is not None: band &= ~fixed
    L = umbrella_L(V, F)
    Q = (L.T @ L).tocsr()
    B = np.where(band)[0]; R = np.where(~band)[0]
    QBB = Q[B][:, B].tocsc(); QBR = Q[B][:, R]
    Vn = V.copy()
    for k in range(3):
        Vn[B, k] = spsolve(QBB, -(QBR @ V[R, k]))
    N = vertex_normals(V, F)
    d = np.einsum("ij,ij->i", Vn - V, N)                      # normal-only move
    if not normal_only:
        # the full solved position (2026-10-19, woman2 v5): at a sharp corner, normal-only moves of neighbours along
        # diverging normals fold the surface; the solved positions themselves don't. no_outward clips the normal part.
        D = Vn - V
        if no_outward is not None:
            dn = np.einsum("ij,ij->i", D, N); D[no_outward] -= (np.maximum(dn[no_outward], 0.0))[:, None] * N[no_outward]
        out = V.copy(); out[B] += D[B]
        return out, {"band_vertices": int(len(B)), "move_mm": {"min": float(-np.linalg.norm(D[B], axis=1).max() * 1000) if False else float(dn_min(D, N, B)),
                     "max": float(np.linalg.norm(D[B], axis=1).max() * 1000), "rms": float(np.sqrt(np.mean(np.sum(D[B] ** 2, 1))) * 1000)},
                     "mode": "full positions"}
    move = np.zeros(len(V)); move[B] = d[B]
    if no_outward is not None:
        move[no_outward] = np.minimum(move[no_outward], 0.0)
    rep = {"band_vertices": int(len(B)), "move_mm": {"min": float(move[B].min() * 1000), "max": float(move[B].max() * 1000),
                                                     "rms": float(np.sqrt(np.mean(move[B] ** 2)) * 1000)}}
    if protect_pts is not None and len(protect_pts):
        tree = cKDTree(protect_pts)
        before, _ = tree.query(V[B])
        after, _ = tree.query(V[B] + move[B, None] * N[B])
        bad = (after < min_gap) & (after < before)
        # scale a vertex's move so it keeps at least min_gap (or its old clearance, if that was already smaller)
        for _ in range(8):
            if not bad.any(): break
            move[B[bad]] *= 0.5
            after, _ = tree.query(V[B] + move[B, None] * N[B])
            bad = (after < min_gap) & (after < before)
        rep["clearance_mm"] = {"before_min": float(before.min() * 1000), "after_min": float(after.min() * 1000),
                               "scaled_vertices": int(((after < before) & (before < min_gap * 4)).sum())}
    return V + move[:, None] * N, rep
