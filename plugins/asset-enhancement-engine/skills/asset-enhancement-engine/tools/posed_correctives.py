"""POSED CORRECTIVES (2026-10-19, woman2 v5): linear-blend skinning in numpy, matched to Blender's armature modifier,
and the inverse step that turns a fix made on the POSED surface into a rest-space corrective shape-key offset.

Why: a form that only exists with the arm raised (the armpit cup) has to be measured and solved where it lives, in
the posed frame, but the rig stores it as a rest-space shape key that Blender applies BEFORE skinning. For a vertex
with skinning matrix A_v (weighted sum of bone deform matrices, weights normalised as Blender does), a posed move d
comes from a rest-space offset A_v[:3,:3]^-1 d.

skin_matrices(W, M) -> (n, 4, 4)     W: (n, bones) deform weights (columns in the order of M); M: (bones, 4, 4)
skin(Y, A) -> posed positions        Y: rest positions with shape keys already added
to_rest(d, A) -> rest-space offsets  d: posed-space moves
"""
import numpy as np


def skin_matrices(W, M):
    s = W.sum(1, keepdims=True)
    Wn = np.where(s > 0, W / np.maximum(s, 1e-12), 0.0)          # Blender normalises by the total deform weight
    A = np.einsum("nb,bij->nij", Wn, M)
    A[s[:, 0] <= 0] = np.eye(4)                                  # unweighted vertices stay where they are
    return A


def skin(Y, A):
    return np.einsum("nij,nj->ni", A[:, :3, :3], Y) + A[:, :3, 3]


def to_rest(d, A):
    return np.linalg.solve(A[:, :3, :3], d[:, :, None])[:, :, 0]
