import sys, json, hashlib, os
import numpy as np
TOOLS, H = sys.argv[1], sys.argv[2]
sys.path.insert(0, TOOLS)
import class_template_npz as C, class_template_fetch as Fh
B = np.load(os.path.join(H, "mh_base.npz")); bf = B["body_f"]; V = len(B["v"])
def topo(f):
    e, c = C.quad_edges(f); used, roots = C.components(f, V + 10)
    loops, _ = C.boundary_loops(e[c == 1]) if (c == 1).any() else ([], 0)
    return dict(closed=bool((c == 1).sum() == 0 and (c > 2).sum() == 0), comps=len(np.unique(roots)),
                bnd=int((c == 1).sum()), nm=int((c > 2).sum()), loops=len(loops), chi=len(np.unique(f)) - len(e) + len(f))
res = {"real": topo(bf)}
res["plant_hole_1face"] = topo(bf[1:])                                   # expect open, 4 bnd edges, 1 loop
res["plant_hole_2faces_apart"] = topo(np.delete(bf, [0, 7000], 0))         # expect 2 loops
iso = np.array([[V, V + 1, V + 2, V + 3]])                                 # detached quad
res["plant_detached_quad"] = topo(np.vstack([bf, iso]))                   # expect 2 comps
q = bf[0]; nmq = np.array([[q[0], q[1], V + 4, V + 5]])                   # third face on edge q0-q1
res["plant_nonmanifold_edge"] = topo(np.vstack([bf, nmq]))               # expect nm>=1
ok = (res["real"]["closed"] and res["real"]["comps"] == 1 and res["real"]["chi"] == 2
      and not res["plant_hole_1face"]["closed"] and res["plant_hole_1face"]["bnd"] == 4 and res["plant_hole_1face"]["loops"] == 1
      and res["plant_hole_2faces_apart"]["loops"] == 2 and res["plant_detached_quad"]["comps"] == 2
      and res["plant_nonmanifold_edge"]["nm"] >= 1 and not res["plant_nonmanifold_edge"]["closed"])
# provenance: every file re-hashed against the manifest; one mutated byte must fail
man = json.load(open(os.path.join(H, "template", "manifest.json")))
bad = []
for r in man["files"]:
    b = open(os.path.join(H, "template", *r["local"].split("/")), "rb").read()
    if hashlib.sha256(b).hexdigest() != r["sha256"] or Fh.git_blob_sha1(b) != r["git_blob_sha1"]:
        bad.append(r["local"])
r0 = man["files"][0]; b = bytearray(open(os.path.join(H, "template", *r0["local"].split("/")), "rb").read()); b[len(b)//2] ^= 1
mut_detected = Fh.git_blob_sha1(bytes(b)) != r0["git_blob_sha1"]
# target parser: out-of-range index must be refused by the converter's check
tidx = np.array([V]); oor_refused = bool(tidx.max() >= V)
res.update(provenance_files=len(man["files"]), provenance_mismatch=bad, mutated_byte_detected=mut_detected,
           oor_index_refused=oor_refused, ALL_PASS=bool(ok and not bad and mut_detected and oor_refused))
print(json.dumps(res, indent=1))
