"""Silhouette of a mesh through the frozen photo camera, WITHOUT Blender (fast head-shape iterations).
Blender convention: camera matrix_world = T(location) @ rot_matrix; looks down local -Z, up +Y; sensor fit horizontal.
Rasterises every triangle (fillConvexPoly per triangle - fillPoly on a list uses even-odd fill).
usage: python project_mask.py <mesh.ply> <camera.json> <out_mask.png> [W=1728] [H=1152]
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "checks"))
import checks as C  # noqa: E402


def project(v, cam, W, H):
    R = np.array(cam["rot_matrix"]); loc = np.array(cam["location"])
    pc = (v - loc) @ R                          # camera coords (R columns = camera axes in world)
    z = -pc[:, 2]
    s = cam["lens"] / cam["sensor_width"]
    u = W / 2 + s * pc[:, 0] / z * W
    w = H / 2 - s * pc[:, 1] / z * W
    return np.stack([u, w], 1), z


def mask(v, f, cam, W=1728, H=1152):
    uv, z = project(v, cam, W, H)
    m = np.zeros((H, W), np.uint8)
    tri = np.round(uv[f] * 4).astype(np.int32)                  # 2 bits sub-pixel (shift=2)
    for t in tri:
        cv2.fillConvexPoly(m, t, 255, cv2.LINE_8, 2)
    return m


if __name__ == "__main__":
    v, f = C.read_ply(sys.argv[1])
    cam = json.load(open(sys.argv[2]))
    W = int(sys.argv[4]) if len(sys.argv) > 4 else 1728
    H = int(sys.argv[5]) if len(sys.argv) > 5 else 1152
    m = mask(v, f, cam, W, H)
    cv2.imwrite(sys.argv[3], m)
    print("mask", sys.argv[3], int((m > 0).sum()), "px")
