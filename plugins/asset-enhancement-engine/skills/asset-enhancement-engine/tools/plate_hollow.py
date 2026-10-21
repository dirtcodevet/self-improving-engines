"""PLATE HOLLOW (2026-10-19, woman2 v5): a hollow in a skin surface made as a clamped plate under a load.

Why: with the arm raised, the woman2 armpit floor spanned flat (stage 4 released it as an unloaded membrane). A real
armpit floor is pulled up into the hollow by the suspensory ligament of the axilla, which continues the clavipectoral
fascia into the axillary fascia (Gray's Anatomy, the axilla). Skin plus fascia held at its rim (the folds) and pulled
over its middle bends like a clamped plate under a uniform load: D * lap^2 w = q, w = 0 and dw/dn = 0 at the rim. The
shape is smooth everywhere, joins the rim tangentially (no crease), and is deepest in the middle.
The same solve serves any loaded hollow of soft tissue (the navel's surround, a dimple over a ligament attachment).

plate_profile(V, F, region) -> phi in [0, 1] on the mesh (0 outside the region and tangent at its rim, 1 at the
deepest point). Discrete form: the umbrella bi-Laplacian (L^T L) solved over the region with every vertex outside
held at 0 (two held rings clamp the slope), unit load.
"""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve


def plate_profile(V, F, region):
    n = len(V); E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    A = sparse.coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    L = sparse.eye(n) - sparse.diags(1 / np.maximum(np.asarray(A.sum(1)).ravel(), 1)) @ A
    Q = (L.T @ L).tocsr()
    B = np.where(region)[0]
    phi = np.zeros(n)
    phi[B] = spsolve(Q[B][:, B].tocsc(), np.ones(len(B)))
    return phi / max(phi.max(), 1e-30)
