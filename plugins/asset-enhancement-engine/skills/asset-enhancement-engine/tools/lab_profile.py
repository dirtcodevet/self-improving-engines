# Head-local profile of a part_lab mesh: for thin slabs at given x (head-local, unscaled), print the frontmost
# skin point (min local y) per z band. Usage: python lab_profile.py <case_mesh_landmarks.json> <lab.ply> [x ...]
import json, sys
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__file__))
from sdf_core import V  # noqa
J = json.load(open(sys.argv[1])); L, P = J["landmarks"], J["params"]
R = np.array(L["head_R"]); H0 = np.array(L["head"]); hs = P["head_scale"]


def read_ply(p):
    with open(p, "rb") as f:
        h = b""
        while not h.endswith(b"end_header\n"):
            h += f.readline()
        nv = int(h.split(b"element vertex ")[1].split()[0])
        return np.frombuffer(f.read(nv * 12), np.float32).reshape(-1, 3).astype(float)


v = read_ply(sys.argv[2])
hl = ((v - H0) @ R) / hs
for xs in [float(a) for a in sys.argv[3:]] or [0.0, 0.0046]:
    s = np.abs(hl[:, 0] - xs) < 0.00025
    print(f"x = {xs*1000:.1f} mm   z(mm)  front-y(mm)")
    for z in np.arange(-0.040, -0.020, 0.0005):
        b = s & (np.abs(hl[:, 2] - z) < 0.00025)
        if b.any():
            print(f"   {z*1000:6.1f}  {hl[b,1].min()*1000:7.2f}")
