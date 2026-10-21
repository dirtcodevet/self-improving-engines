"""THE LANGUAGE TOOL FOR ANY OBJECT (build L1, 2026-10-21): feed in a 3-D model or a 2-D image and the engine segments
it into named parts and gives every part its own centimetre frame and skin-following address grid (engine/tools/
part_frame.py, the language tool's core), opens it in the browser view, and keeps it current when the model changes.

Why it exists. The person (2026-10-21): "our engine will create, build, populate this style of a tool for any 2D object
or 3D object that you feed into the model ... here's a brick ... here's a dragon ... we've got a claw. Got a tooth, we've
got an eyeball, we've got a horn, we've got an arm, a leg, a foot ... a wing"; and the same day: as things change or a
final decision is made "that should automatically be updated. Probably by the engine, so the AI isn't having to go
through and manually trigger that change." Before this, part_frame worked for one model: hand-written part definitions
(engine/packs/human/part_frames.json), a hand-written job (cases/woman2/parts/job.json), rebuilt only when run by hand.

HOW A NEW OBJECT GETS ITS LANGUAGE TOOL (`auto`):
  1. ingest   the model (.ply .obj .stl .npz; .glb .gltf .fbx .blend .dae through background Blender; .png .jpg as a
              2-D object: its foreground becomes a flat mesh in the image plane) -> <case>/language/src/model.npz;
  2. segment  by the methods the object's PACK names (engine/packs/<domain>/language.json; data):
              components (separate shells: eyes, teeth), facets (faces of a faceted object, the strips between two
              faces (edges) and the patches where three meet (corners)), branches (protrusions: limbs, horns, claws,
              tails, wing points - tips of the geodesic distance from the body's core with topological persistence,
              each cut where it flares into what it grows from);
  3. name     each part from the pack's vocabulary by its rules (descriptors measured on the part: shape class,
              size, taper, position in the object's frame, parent, children); a part no rule names keeps a generic
              name (piece_3); names the person or an agent gives (`rename`) are kept for good;
  4. define   one part_frame definition per part from the pack's template for its shape class (tube: a tube chart
              along base -> tip; disc: a disc chart on its mean normal; sheet: two discs, upper and under) into
              <case>/language/definitions.json, and a job (<case>/language/job.json) that part_frame builds;
  5. build    every part (part_frame.build) and the object page (object.html: the whole object coloured by part, every
              part's grid; a click names the part and its address) and index.html.
KEPT CURRENT (`sync`, and automatically):
  - every built part records the fingerprint of everything it was made from (model file, bound inputs, definitions,
    the pack, the tool's version); `sync` rebuilds exactly what is stale, for every language job in cases/ (generated
    or hand-written, e.g. woman2's); a job may FOLLOW a pack (its pack.json's current version), so a new version made
    current - a decision - rebinds the job;
  - when an object's model changes, its part labels are carried onto the new mesh (nearest surface; the person's names
    and every part's identity stay) and the segmentation re-runs to report parts that appeared or vanished;
  - automatic triggers: `resolve` brings its part current before reading an address; the engine's writers
    (loop/pack_io.Pack.save, loop/recipe.py) call notify(path), which starts a background sync of the jobs that read
    that path (a no-op for paths no job reads); `watch` polls for a live session.
Everything particular to a kind of object is pack data; everything particular to one model is in its case folder.
BUILD L2 (2026-10-21, the human word list) added, all driven by pack data: branch option profile "sections" (plane
sections across a protrusion's own axis: a limb's section jumps where it merges with the trunk's), function "centre", a
tip's own scale (local_scale), limb_junction_share; after a first naming: chain merges, splits by a plane at the
narrowest section or a fold (wrist, ankle, jaw), mounds above the skin's own course (breasts), merges of a word into
the same word and of parts no domain rule names; rule conditions ancestor_kind, number_by; a pack's own part_frame
definition per word (the human torso and head).
BUILD L3 (2026-10-21, the Translator's home; engine/tools/translator_pages.py): one home page (cases/index.html) lists
every view by model and every page links home, to the model's whole view, its list of parts and its other views, with a
box that finds a part by the name a person would use; `open` opens the home or a model's view on any OS (Python's
webbrowser; `auto --open` too). The object page's frame is recorded as it is, LEFT-handed (x = the object's own right,
y up, z its front: a mirror of the object frame; page_matrix), and the viewer draws a left-handed frame as the model
is (it showed the mirror image: her right on the screen's right in a front view). Its numbers are unchanged, so every
address already pasted resolves where it did. Pages say "Translator".
BUILD L4 (2026-10-21, the head's own parts; engine/tools/part_features.py): a pack's "features" block, run after its
splits, mounds and merges, divides every part of a word (the human head) into its features - ears, eyes, nose, lips and
the inside of the mouth - found from the part's own shape (its height above its smooth radial course, the skin a ball
cannot reach, its curvature), each a part of its own word growing from it, its side by the part's own mid-plane
(describe() takes a part's "side_of"); a separate shell set in a feature joins it (an eye's globe in its socket). The new
parts are added after the others, so those keep their order, uids and builds. A "feature" part takes the template its
pack names (shape_class), else a disc on its mean normal.

Usage:
  python language.py auto MODEL --case DIR [--pack DOMAIN] [--name NAME] [--units-m K] [--up +z] [--front -y] [--open]
                         [--only PART,...]   build only these parts (a name or a pack word); the segmentation is cached
  python language.py sync [JOB ...]        rebuild what is stale (every language job when none is named)
  python language.py status [JOB ...]      what is current, what is stale and why
  python language.py watch [--every S]     sync on change until stopped
  python language.py rename CASE OLD NEW              a part's name, kept across rebuilds
  python language.py cut CASE PART NEW "LINE" ...     split a part by the plane through picked places (pasted lines)
  python language.py merge CASE KEEP GONE             join two parts
  python language.py resolve CASE "ADDRESS" ...       addresses naming any part of the object
  python language.py change-test CASE NEW_MODEL --work DIR [--set key=json,...] [--out F]   what survives a change
  python language.py compare OLD_DIR NEW_DIR          the same, between two builds
  python language.py notify PATH ...                  what the engine's writers call (background sync of readers)
  python language.py prove [--only SECTIONS]         planted objects with known parts (see prove()); --only facets,
                                                      creature, 2d, current, or a pack name (generic, creature, masonry)
  python language.py regress [SPEC] [--update] [--jobs-only|--picks-only] [--only TEXT] [--out F]
                                                      the Translator's guarantees: hand-made parts rebuild identical,
                                                      pasted lines resolve where the baseline says (default spec
                                                      cases/woman2/translator_regress.json)
  python language.py home [--home DIR]                the Translator's home page (DIR/index.html; default cases/)
  python language.py open [WHAT] [--home DIR] [--print]   open the home (no WHAT), a model's whole view, a part, a
                                                      folder or a page in the browser; --print: only say which
                                                      (JSON: page, url, rel = its address under the home)
  python language.py pages [DIR ...] [--stale]        every view's pages with the current viewer, lists, the home
"""
# ---- FUNCTION INDEX (engine/tools/func_index.py; grep 'def <name>' to jump) ----
#   image_mesh(path, px_m, foreground, target_vertices, thre...)  - a 2-D object: the image's foreground as a flat tr...
#   ingest(model, out_npz, units_m, up, front, px_m, for...)  - model file -> npz in the OBJECT FRAME of the engine (...
#   mesh_basics(V, F)
#   face_adjacency(F)  - pairs of faces sharing an edge (manifold or not)
#   face_components(F, n)
#   inner_radius(V, F, B, dim)  - the body's local half-thickness at each vertex: 3-D, half the distance through the ...
#   geodesic(B, seeds)
#   branch_segments(V, F, B, dim, prm, log)  - PROTRUSIONS, nested. f = the protrusion function: (default, function "...
#   facet_segments(V, F, B, prm, log)  - FACES of a faceted object. Region growing over the face graph, flattest seed...
#   segment(V, F, dim, seg, file_labels, log)  - the object's parts by the pack's methods (seg = the pack's "segmenta...
#   object_frame(V, dim, front2d)  - the frame names are read in: 3-D, the engine frame (x left, y back, z up; ingest...
#   describe(V, F, lab, parts, B, fr)  - per part, measured on its faces: area (cm2, share), centroid and its place i...
#   name_parts(parts, desc, rules, keep, log, fixed)  - vocabulary words and names from the pack's rules, in order. A...
#   mound_segments(V, F, lab, k, spec, B, fr, log)  - (L2) MOUNDS on part k (a breast on a chest): the part's skin th...
#   refine_parts(V, F, lab, parts, B, fr, pack, dim, log)  - (L2) a pack's SPLITS and MERGES, after a first naming by...
#   shape_class(p, d, dim, tmpl)  - which template a part gets: flat (a 2-D object's part), plane (a planar facet: a ...
#   part_entry(name, uid, par_uid, cls, d, fr, tmpl, sticky)  - one part_frame definition from the shape class's temp...
#   fallback_entry(e, level)  - when a part's skin chart cannot be laid (an axis that misses a bent part, a seam that...
#   load_pack(domain)  - the object kind's language data: engine/packs/<domain>/language.json over engine/packs/gener...
#   class Obj [job, seg]  - one object's language tool: <case>/language/ holds job.json (part_frame's job, plus a "la...
#   auto(model, case, pack, name, units_m, up, front, ...)  - a new object's language tool, end to end: ingest, segme...
#   refresh(O, force_segment, log, only)  - (re)make the object's parts from its model: ingest; carry the earlier bui...
#   build_parts(O, only, log)  - every part (or `only`) through part_frame.build_part; a part whose template cannot b...
#   write_object_page(O, log)  - object.html (the whole object, coloured by part; every part's grid; a click names th...
#   object_frame_record(dim)  - (L3) the object page's frame as it is: page_matrix's rows in the object frame (q_cm =...
#   render_object_png(path, V, F, flab, names, cols, dim, title)  - the object coloured by part with every part's nam...
#   page_matrix(dim)  - object frame (x left, y back, z up) -> the page frame the viewer reads (x right, y up, z towa...
#   write_index(O, recs, parts_js)  - the object's list of parts (L3: translator_pages.write_list: names a person wou...
#   reindex(O, parts_js)  - (L3) an object's list rewritten without a rebuild: parts_js from its object page (what th...
#   find_jobs()  - every language job, however deep it sits in cases/ (a generated <...>/language/job.json, or a hand...
#   status(job_path)  - per part: current | stale (what changed) | missing | legacy (built before fingerprints: compa...
#   sync(job_path, log)  - rebuild exactly what is stale, for one job or every job; returns what was done
#   reindex_plain(jp)  - (L3) a hand-written job's list rewritten from its parts' .json (no rebuild)
#   watched_files(job_path)  - the files a job is made from (its model, sources, inputs, definitions, a followed pack...
#   notify(paths, wait, jobs)  - called by the engine's writers after they write (loop/pack_io.Pack.save, loop/recipe...
#   ensure_current(npz_path, log)  - part_frame.resolve calls this: if the part's job says anything it is made from c...
#   watch(every, log)  - sync every language job whenever what it is made from changes, until stopped (Ctrl+C)
#   rename(job_or_case, old, new, by)  - a part's name, kept for good (an edit in segmentation.json; the part's files...
#   cut(job_or_case, part, lines, new_name, by)  - split a part along the plane through picked places (pasted address...
#   merge(job_or_case, keep, gone, by)  - join part GONE into part KEEP
#   resolve(dir_or_job, lines)  - address lines naming any part of the object (pasted from object.html or a part's pa...
#   compare(old_dir, new_dir, only)  - what survives a change: for every part in both builds, every grid address of t...
#   change_test(case, new_model, work, overrides, log)  - a model change, end to end, on a copy: the case's language ...
#   prove(log, work, only)  - Planted objects with known parts (A28: once, at the tool's making; a few minutes):
#   regress(spec_path, update, jobs, picks, only, log)  - The Translator's guarantees, checked (build A1). A spec fil...
#   (+ 64 private helpers: grep '^def _')
# ---- END FUNCTION INDEX ----
import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TOOL_VERSION = "L1.1"      # bump when a change alters what a build writes (it marks every built part stale)
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"


def _p(path):
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def _rel(path):
    try:
        return os.path.relpath(os.path.abspath(path), ROOT).replace(os.sep, "/")
    except ValueError:
        return os.path.abspath(path).replace(os.sep, "/")


def _unit(a):
    a = np.asarray(a, float); n = np.linalg.norm(a, axis=-1, keepdims=True)
    return a / np.where(n > 0, n, 1)


def _jload(path):
    with open(_p(path), encoding="utf-8") as f:
        return json.load(f)


def _jsave(path, d):
    os.makedirs(os.path.dirname(_p(path)), exist_ok=True)
    tmp = _p(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, _p(path))


# ============================================================================================================ ingest
def _read_ply(path):
    with open(path, "rb") as fh:
        head = b""
        while not head.endswith(b"end_header\n") and not head.endswith(b"end_header\r\n"):
            line = fh.readline()
            if not line:
                raise ValueError(f"{path}: no PLY header end")
            head += line
        lines = head.decode("ascii", "replace").splitlines(); fmt = "ascii"; els = []
        for ln in lines:
            t = ln.split()
            if not t:
                continue
            if t[0] == "format":
                fmt = t[1]
            elif t[0] == "element":
                els.append([t[1], int(t[2]), []])
            elif t[0] == "property":
                els[-1][2].append(t[1:])
        tmap = {"char": "i1", "uchar": "u1", "short": "i2", "ushort": "u2", "int": "i4", "uint": "u4", "float": "f4",
                "double": "f8", "int8": "i1", "uint8": "u1", "int16": "i2", "uint16": "u2", "int32": "i4", "uint32": "u4",
                "float32": "f4", "float64": "f8"}
        V = F = None; C = None
        if fmt == "ascii":
            rest = fh.read().decode("ascii", "replace").split("\n"); k = 0
            for name, n, props in els:
                rows = rest[k:k + n]; k += n
                if name == "vertex":
                    A = np.array([r.split() for r in rows], float); names = [p[-1] for p in props]
                    V = A[:, [names.index(c) for c in "xyz"]]
                    if all(c in names for c in ("red", "green", "blue")):
                        C = A[:, [names.index(c) for c in ("red", "green", "blue")]] / 255.0
                elif name == "face":
                    tris = []
                    for r in rows:
                        t = r.split(); m = int(t[0]); idx = [int(x) for x in t[1:1 + m]]
                        tris += [[idx[0], idx[j], idx[j + 1]] for j in range(1, m - 1)]
                    F = np.array(tris, np.int64)
        else:
            end = "<" if "little" in fmt else ">"
            for name, n, props in els:
                if props and props[0][0] == "list":
                    cnt_t, idx_t = tmap[props[0][1]], tmap[props[0][2]]; tris = []
                    for _ in range(n):
                        m = int(np.frombuffer(fh.read(np.dtype(cnt_t).itemsize), end + cnt_t)[0])
                        idx = np.frombuffer(fh.read(m * np.dtype(idx_t).itemsize), end + idx_t)
                        tris += [[idx[0], idx[j], idx[j + 1]] for j in range(1, m - 1)]
                        for p in props[1:]:                          # further face properties: skipped
                            fh.read(np.dtype(tmap[p[0]]).itemsize)
                    if name == "face":
                        F = np.array(tris, np.int64)
                else:
                    dt = np.dtype([(p[1], end + tmap[p[0]]) for p in props]); A = np.frombuffer(fh.read(n * dt.itemsize), dt)
                    if name == "vertex":
                        V = np.c_[A["x"], A["y"], A["z"]].astype(float)
                        if all(c in A.dtype.names for c in ("red", "green", "blue")):
                            C = np.c_[A["red"], A["green"], A["blue"]].astype(float) / 255.0
    return V, F, {}, C


def _read_obj(path):
    V, F, grp, mtl, gnames, mnames = [], [], [], [], ["(none)"], ["(none)"]; g = m = 0
    for ln in open(path, encoding="utf-8", errors="replace"):
        t = ln.split()
        if not t:
            continue
        if t[0] == "v":
            V.append([float(x) for x in t[1:4]])
        elif t[0] in ("o", "g"):
            nm = " ".join(t[1:]) or "(none)"
            if nm not in gnames:
                gnames.append(nm)
            g = gnames.index(nm)
        elif t[0] == "usemtl":
            nm = " ".join(t[1:])
            if nm not in mnames:
                mnames.append(nm)
            m = mnames.index(nm)
        elif t[0] == "f":
            idx = [int(x.split("/")[0]) for x in t[1:]]; idx = [i - 1 if i > 0 else len(V) + i for i in idx]
            for j in range(1, len(idx) - 1):
                F.append([idx[0], idx[j], idx[j + 1]]); grp.append(g); mtl.append(m)
    labels = {}
    if len(gnames) > 2:
        labels["object"] = (np.array(grp, np.int32), gnames)
    if len(mnames) > 2:
        labels["material"] = (np.array(mtl, np.int32), mnames)
    return np.array(V, float), np.array(F, np.int64), labels, None


def _read_stl(path):
    raw = open(path, "rb").read()
    if raw[:5] == b"solid" and b"facet" in raw[:400]:
        P = np.array(re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", raw), float).reshape(-1, 3, 3)
    else:
        n = int(np.frombuffer(raw[80:84], "<u4")[0]); dt = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
        P = np.frombuffer(raw[84:84 + n * 50], dt)["v"].astype(float)
    flat = P.reshape(-1, 3); q = np.round(flat / (np.abs(flat).max() * 1e-9 + 1e-30)).astype(np.int64)
    _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    return flat[first], inv.reshape(-1, 3).astype(np.int64), {}, None


def _read_blender(path, work_dir):
    """any format Blender opens: every mesh object, evaluated, in world coordinates, merged; per-face object index"""
    out = os.path.join(work_dir, "blender_export.npz")
    cmd = [BLENDER, "-b", "--factory-startup", "--python", os.path.join(HERE, "bl_export_scene.py"), "--", os.path.abspath(path), out]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if not os.path.exists(out):
        raise RuntimeError(f"Blender export failed: {r.stdout[-2000:]} {r.stderr[-2000:]}")
    z = np.load(out, allow_pickle=False)
    labels = {"object": (z["face_object"].astype(np.int32), [str(x) for x in z["object_names"]])}
    if "face_material" in z.files:
        labels["material"] = (z["face_material"].astype(np.int32), [str(x) for x in z["material_names"]])
    return z["v"].astype(float), z["f"].astype(np.int64), labels, (z["colour"] if "colour" in z.files else None)


def image_mesh(path, px_m=1e-4, foreground="auto", target_vertices=80000, threshold=None):
    """a 2-D object: the image's foreground as a flat triangle mesh in the image plane (x right, y up, z = 0; metres
    at px_m per pixel), its boundary on the sub-pixel outline (marching squares), per-vertex image colour. Foreground:
    alpha (if the image has a varying alpha), dark or light (Otsu split), or auto (alpha, else the side of the Otsu split
    that touches the border less)."""
    from PIL import Image
    from scipy.spatial import Delaunay
    from scipy import ndimage
    from skimage import measure, filters
    im = Image.open(path); H, W = im.size[1], im.size[0]
    rgba = np.asarray(im.convert("RGBA"), float) / 255.0; a = rgba[..., 3]
    lum = rgba[..., :3] @ np.array([0.299, 0.587, 0.114])
    if foreground == "alpha" or (foreground == "auto" and a.min() < 0.5 < a.max()):
        fg = a; how = "alpha"
    else:
        t = threshold if threshold is not None else filters.threshold_otsu(lum)
        dark = (lum < t).astype(float); light = 1.0 - dark
        if foreground == "auto":
            border = np.r_[dark[0], dark[-1], dark[:, 0], dark[:, -1]].mean()
            foreground = "dark" if border < 0.5 else "light"
        fg = ndimage.gaussian_filter(dark if foreground == "dark" else light, 0.7); how = f"{foreground} (luminance split {t:.3f})"
    msk = fg > 0.5
    lab, n = ndimage.label(msk)
    if n > 1:                                                          # the largest region and what touches it
        big = np.bincount(lab.ravel())[1:].argmax() + 1; msk = lab == big
        fg = np.where(ndimage.binary_dilation(msk, iterations=2), fg, 0.0)
    step = max(1.0, math.sqrt(msk.sum() / float(target_vertices)))
    r, c = np.mgrid[0:H:step, 0:W:step]; r, c = r.ravel(), c.ravel()
    inside = ndimage.map_coordinates(fg, [r, c], order=1) > 0.5
    dist = ndimage.distance_transform_edt(msk)
    inside &= ndimage.map_coordinates(dist, [r, c], order=1) > 0.45 * step      # interior points clear of the outline
    pts = [np.c_[r[inside], c[inside]]]
    for cont in measure.find_contours(fg, 0.5):
        seg = np.linalg.norm(np.diff(cont, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
        if s[-1] < 3 * step:
            continue
        k = max(int(s[-1] / step), 3); t = np.linspace(0, s[-1], k, endpoint=False)
        pts.append(np.c_[np.interp(t, s, cont[:, 0]), np.interp(t, s, cont[:, 1])])
    P = np.concatenate(pts); P = np.unique(np.round(P, 4), axis=0)
    tri = Delaunay(P[:, ::-1]).simplices
    T = P[tri]; cen = T.mean(1); mids = (T + np.roll(T, -1, 1)) / 2
    keep = ndimage.map_coordinates(fg, [cen[:, 0], cen[:, 1]], order=1) > 0.5
    for j in range(3):
        keep &= ndimage.map_coordinates(fg, [mids[:, j, 0], mids[:, j, 1]], order=1) > 0.35
    e = np.linalg.norm(T - np.roll(T, -1, 1), axis=2).max(1); keep &= e < 3.5 * step
    F = tri[keep]; used = np.unique(F); remap = -np.ones(len(P), np.int64); remap[used] = np.arange(len(used)); F = remap[F]; P = P[used]
    V = np.c_[P[:, 1] * px_m, (H - P[:, 0]) * px_m, np.zeros(len(P))]
    A = (V[F[:, 1]] - V[F[:, 0]])[:, :2]; B = (V[F[:, 2]] - V[F[:, 0]])[:, :2]
    flip = A[:, 0] * B[:, 1] - A[:, 1] * B[:, 0] < 0; F[flip] = F[flip][:, ::-1]          # every face toward +Z
    col = np.stack([ndimage.map_coordinates(rgba[..., k], [P[:, 0], P[:, 1]], order=1) for k in range(3)], -1)
    note = (f"2-D object from {os.path.basename(path)} ({W} x {H} px): foreground by {how}, {len(V)} vertices at ~{step:.2f} px "
            f"spacing, {px_m * 1000:.3f} mm per pixel (x right, y up, z = 0 toward the viewer)")
    return V, F, col, note


def ingest(model, out_npz, units_m=1.0, up="+z", front="-y", px_m=1e-4, foreground="auto", log=print):
    """model file -> npz in the OBJECT FRAME of the engine (metres; x = the object's left, y = back, z = up; the source's
    own axes turned so its `up` is +z and its `front` is -y). Writes v, f, dim (2 | 3), per-face labels from the file
    (object, material) with their names, colour (2-D) and a note."""
    ext = os.path.splitext(model)[1].lower(); work = os.path.dirname(os.path.abspath(out_npz)); os.makedirs(work, exist_ok=True)
    col = None; labels = {}
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"):
        V, F, col, note = image_mesh(model, px_m, foreground); dim = 2; units = 1.0; R = np.eye(3)
    else:
        if ext == ".ply":
            V, F, labels, col = _read_ply(model)
        elif ext == ".obj":
            V, F, labels, col = _read_obj(model)
        elif ext == ".stl":
            V, F, labels, col = _read_stl(model)
        elif ext == ".npz":
            z = np.load(model, allow_pickle=False); V, F = z["v"].astype(float), z["f"].astype(np.int64)
            for k in z.files:
                if k.startswith("face_") and k + "_names" in z.files:
                    labels[k[5:]] = (z[k].astype(np.int32), [str(x) for x in z[k + "_names"]])
        else:
            V, F, labels, col = _read_blender(model, work)
        dim = 3; units = float(units_m)
        R = _axes_to_engine(up, front)
        note = f"{os.path.basename(model)}: {len(V)} vertices, {len(F)} triangles; source up {up}, front {front}, {units} m per unit"
    V = (np.asarray(V, float) @ R.T) * units
    F = np.asarray(F, np.int64); good = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2]); F = F[good]
    for k in list(labels):
        labels[k] = (labels[k][0][good], labels[k][1])
    used = np.unique(F); remap = -np.ones(len(V), np.int64); remap[used] = np.arange(len(used))   # unreferenced vertices dropped
    V = V[used]; F = remap[F]
    if col is not None and len(col) == len(remap):
        col = np.asarray(col)[used]
    out = {"v": V.astype(np.float64), "f": F.astype(np.int32), "dim": np.array(dim), "note": np.array(note),
           "source_to_engine": np.array(R * units)}
    if col is not None:
        out["colour"] = np.asarray(col, np.float32)
    for k, (ids, names) in labels.items():
        out["face_" + k] = ids.astype(np.int32); out["face_" + k + "_names"] = np.array(names)
    np.savez_compressed(out_npz, **out)
    log(f"  ingest: {note}")
    return out


def _axes_to_engine(up, front):
    """rotation taking the source's `up` to +z and its `front` to -y (engine / Blender convention)"""
    ax = {"x": 0, "y": 1, "z": 2}
    vec = lambda s: (-1.0 if s[0] == "-" else 1.0) * np.eye(3)[ax[s[-1]]]
    u, f = vec(up), vec(front)
    if abs(u @ f) > 0.5:
        raise ValueError(f"up {up} and front {front} are not perpendicular")
    b = -f; l = np.cross(b, u)                          # engine x = left = back x up (y x z = x)
    return np.stack([l, b, u])                          # rows: where the engine's x, y, z come from in the source


# ======================================================================================================= geometry
def mesh_basics(V, F):
    from scipy.sparse import coo_matrix
    n = len(V); E = np.r_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]; E = np.unique(np.sort(E, 1), axis=0)
    L = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1); L = np.maximum(L, 1e-12)
    G = coo_matrix((np.r_[L, L], (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(n, n)).tocsr()
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); fa = 0.5 * np.linalg.norm(fn, axis=1)
    fn = fn / np.maximum(2 * fa, 1e-30)[:, None]
    va = np.bincount(F.ravel(), np.repeat(fa / 3, 3), minlength=n)
    vn = np.zeros((n, 3))
    for j in range(3):
        np.add.at(vn, F[:, j], fn * fa[:, None])
    vn = _unit(vn)
    return {"E": E, "L": L, "G": G, "fn": fn, "fa": fa, "va": va, "vn": vn}


def face_adjacency(F):
    """pairs of faces sharing an edge (manifold or not)"""
    E = np.r_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]; E = np.sort(E, 1); fid = np.tile(np.arange(len(F)), 3)
    key = E[:, 0] * (int(F.max()) + 1) + E[:, 1]; o = np.argsort(key, kind="stable"); k = key[o]; f = fid[o]
    same = k[1:] == k[:-1]
    return np.c_[f[:-1][same], f[1:][same]]


def face_components(F, n):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    e = np.r_[F[:, [0, 1]], F[:, [1, 2]]]
    _, lab = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)), directed=False)
    return lab


def inner_radius(V, F, B, dim):
    """the body's local half-thickness at each vertex: 3-D, half the distance through the body along -normal (the
    shape diameter, median of 5 rays in a 20 deg cone, 1-ring smoothed); 2-D, the distance inside the outline to the
    nearest boundary edge (geodesic)"""
    from scipy.sparse.csgraph import dijkstra
    n = len(V)
    if dim == 2:
        E = np.r_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]; Es = np.sort(E, 1)
        u, cnt = np.unique(Es, axis=0, return_counts=True); bv = np.unique(u[cnt == 1])
        return dijkstra(B["G"], indices=bv, min_only=True)
    sys.path.insert(0, HERE)
    import part_frame as PF
    cas = PF.Caster(V, F); vn = B["vn"]; t0 = np.ones(3) if abs(vn[0, 0]) < 0.9 else np.array([0, 1.0, 0])
    a1 = _unit(np.cross(vn, np.where(np.abs(vn[:, :1]) < 0.9, [[1.0, 0, 0]], [[0, 1.0, 0]])))
    a2 = np.cross(vn, a1); th = math.radians(20); res = []
    for d in [(-vn)] + [-(math.cos(th) * vn + math.sin(th) * (math.cos(p) * a1 + math.sin(p) * a2)) for p in np.radians([0, 90, 180, 270])]:
        _, t, _ = cas.cast(V - vn * 1e-6 * cas.diag, d, tmin=1e-5 * cas.diag)
        res.append(np.where(np.isfinite(t), t, np.nan))
    T = np.nanmedian(np.stack(res), 0) / 2
    T = np.where(np.isfinite(T), T, np.nanmedian(T))
    for _ in range(2):                                              # 1-ring mean, twice
        G = B["G"].copy(); G.data[:] = 1.0; deg = np.asarray(G.sum(1)).ravel()
        T = (G @ T + T) / (deg + 1)
    return T


def geodesic(B, seeds):
    from scipy.sparse.csgraph import dijkstra
    return dijkstra(B["G"], indices=np.asarray(seeds, np.int64), min_only=True)


# ------------------------------------------------------------------------------------------------ branch segmentation
def _merge_tree(indptr, indices, f, tau):
    """0-dimensional persistence of the superlevel sets of f on the vertex graph (union-find, from the highest f
    down). A maximum whose component lives at least tau before merging into an older one is a TIP; each tip opens an
    ARC (the vertices that join its component before it merges); a merge of two components that both lived tau or
    more closes their arcs and opens a new one. Returns per-vertex arc ids, and per arc: parent, tip vertex, the f at
    which it opened (its tip's f, or the merge saddle's) and closed."""
    n = len(f); order = np.argsort(-f, kind="stable"); rank = np.empty(n, np.int64); rank[order] = np.arange(n)
    parent = np.arange(n); tip = np.arange(n); comp_arc = -np.ones(n, np.int64)
    arc_of = -np.ones(n, np.int64); arcs = []                         # arc: [parent, tip, f_open, f_close, kind]
    absorbed = {}

    def find(x):
        r = x
        while parent[r] != r:
            r = parent[r]
        while parent[x] != r:
            parent[x], x = r, parent[x]
        return r

    def arc_find(a):
        while a in absorbed:
            a = absorbed[a]
        return a
    for v in order:
        roots = set()
        for k in range(indptr[v], indptr[v + 1]):
            u = indices[k]
            if rank[u] < rank[v]:
                roots.add(find(u))
        if not roots:
            arcs.append([-1, int(v), float(f[v]), None, "leaf"]); comp_arc[v] = len(arcs) - 1; arc_of[v] = len(arcs) - 1
            continue
        roots = sorted(roots, key=lambda r: -f[tip[r]])
        elder = roots[0]; sig = [elder]
        for y in roots[1:]:
            if f[tip[y]] - f[v] < tau:                                 # a short-lived bump: absorbed into the elder
                absorbed[comp_arc[y]] = comp_arc[elder]; parent[y] = elder
            else:
                sig.append(y)
        if len(sig) > 1:                                               # a real merge: the arcs close, a new one opens
            arcs.append([-1, int(tip[elder]), float(f[v]), None, "internal"]); na = len(arcs) - 1
            for r in sig:
                a = arc_find(comp_arc[r]); arcs[a][0] = na; arcs[a][3] = float(f[v])
                parent[r] = elder
            comp_arc[elder] = na
        parent[v] = elder; arc_of[v] = arc_find(comp_arc[elder])
    lab = np.array([arc_find(a) for a in arc_of])
    return lab, arcs, absorbed


def _ring_profile(g, av, h, g_max, dim):
    """ring radius against the distance g from a tip (or from a part already cut): band area per unit g in bins of
    width h (r = (dA/dg) / 2 pi in 3-D: a tube's radius; / 2 in 2-D: a strip's half width); places with g = 0 (the seeds
    themselves) are not counted"""
    nb = max(int(math.ceil(g_max / h)), 1); m = (g > 0) & (g <= g_max)
    b = np.clip((g[m] / h).astype(np.int64), 0, nb - 1)
    A = np.bincount(b, av[m], minlength=nb)
    return A / h / (2 * math.pi if dim == 3 else 2.0), (np.arange(nb) + 0.5) * h


def _flare_index(r, gb, h, flare_deg, min_len, window=0.5):
    """(L2) the flare cut on plane sections: the index of the last station before the flare (None: no flare). Sections
    across the part's own axis are exact, so they are read unsmoothed (a 3-point mean spread a finger's step into its
    palm, 0.9 -> 2.1 cm in one 8.6 mm station, to a slope of 0.70: on the 35 deg threshold); the slope is read over
    window x the radius (a jaw widening a face reads 0.4, a neck flaring into the shoulders 2.0) and must hold at the
    next station (a fold one station wide is no flare)"""
    if len(r) < 5:
        return None
    rs = np.where(np.isfinite(r), r, 1e9)                              # an open section (inf): grown past any slope
    tanf = math.tan(math.radians(flare_deg)); start = None
    for i in range(1, len(rs)):
        k = max(1, int(round(min(window * max(rs[i - 1], 2 * h), 1e3 * h) / h))); j = max(i - k, 0)
        slope = (rs[i] - rs[j]) / ((i - j) * h)
        if start is None:
            if slope < tanf and i >= 2:
                start = gb[j]
            continue
        if slope > tanf and gb[j] - start >= min_len and (i + 1 >= len(rs) or rs[i + 1] >= 0.9 * rs[i]):
            return j
    return None


def _flare_cut(r, gb, h, flare_deg, min_len):
    """where a protrusion ends: walking out from the tip, the ring radius first settles (grows slower than
    tan(flare_deg) per unit length: a cap or a point gives way to the shaft), and the first place after at least
    min_len of shaft where it grows faster again (the part flares into what it grows from). None: no such place"""
    if len(r) < 5:
        return None
    rs = np.convolve(r, np.ones(3) / 3, mode="same"); rs[0], rs[-1] = r[0], r[-1]
    tanf = math.tan(math.radians(flare_deg)); start = None
    for i in range(1, len(rs)):
        k = max(1, int(round(max(rs[i - 1], 2 * h) / h))); j = max(i - k, 0)
        slope = (rs[i] - rs[j]) / ((i - j) * h)
        if start is None:
            if slope < tanf and i >= 2:
                start = gb[j]
            continue
        if slope > tanf and gb[j] - start >= min_len:
            return gb[j] + 0.5 * h
    return None


class _Sectioner:
    """(L2) plane sections of a mesh: the closed curve where a plane cuts the skin round a point, by exact
    plane-triangle intersection (a slab of vertices breaks apart where edges are longer than the slab is thick)"""

    def __init__(self, V, F):
        from scipy.spatial import cKDTree
        self.V, self.F = V, F; Cf = V[F].mean(1)
        self.tree = cKDTree(Cf); self.frad = float(np.linalg.norm(V[F] - Cf[:, None], axis=2).max())

    def section(self, c, d, R, faces=None):
        """the plane through c with normal d: the piece of its cut (segments joined across shared edges) that runs
        round c (covers >= 300 deg of angle round d, the nearest such), searched within a ball of radius R; returns
        (length, closed, points): length inf when the piece reaches the ball's edge (it has merged with a larger
        body). faces: a face mask that limits the cut (a part and what grows from it)"""
        V, F = self.V, self.F
        fi = np.asarray(self.tree.query_ball_point(c, R + self.frad), np.int64)
        if faces is not None and len(fi):
            fi = fi[faces[fi]]
        if not len(fi):
            return np.nan, False, np.zeros((0, 3))
        s = (V[F[fi]] - c) @ d; neg = s < 0; k = neg.sum(1); x = fi[(k == 1) | (k == 2)]
        if not len(x):
            return np.nan, False, np.zeros((0, 3))
        s = (V[F[x]] - c) @ d; neg = s < 0
        P, E = [], []
        for a, b in ((0, 1), (1, 2), (2, 0)):                          # the two edges of each face the plane crosses
            m = neg[:, a] != neg[:, b]; t = s[m, a] / (s[m, a] - s[m, b])
            va, vb = F[x[m], a], F[x[m], b]
            P.append((np.nonzero(m)[0], V[va] + t[:, None] * (V[vb] - V[va]), np.minimum(va, vb) * (len(V) + 1) + np.maximum(va, vb)))
        fid = np.concatenate([p[0] for p in P]); pts = np.concatenate([p[1] for p in P]); key = np.concatenate([p[2] for p in P])
        o = np.argsort(fid, kind="stable"); fid, pts, key = fid[o], pts[o], key[o]
        if len(fid) != 2 * len(x):                                     # a vertex exactly on the plane: nudge
            return self.section(c + d * 1e-7, d, R, faces)
        A, Bp = pts[0::2], pts[1::2]; ka, kb = key[0::2], key[1::2]; seglen = np.linalg.norm(Bp - A, axis=1)
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
        uk, inv = np.unique(np.r_[ka, kb], return_inverse=True); ns = len(x); ne = len(uk)
        ia, ib = inv[:ns], inv[ns:]
        Gm = coo_matrix((np.ones(2 * ns), (np.r_[np.arange(ns), np.arange(ns)], ns + np.r_[ia, ib])), shape=(ns + ne, ns + ne))
        nc, cl = connected_components(Gm, directed=False); cl = cl[:ns]
        deg = np.bincount(np.r_[ia, ib], minlength=ne)                 # an edge met by one segment only: an open end
        e0 = _unit(np.cross(d, [1.0, 0, 0] if abs(d[0]) < 0.9 else [0, 1.0, 0])); e1 = np.cross(d, e0)
        mid = (A + Bp) / 2 - c; ang = np.arctan2(mid @ e1, mid @ e0); dist = np.linalg.norm(mid, axis=1)
        best = None
        for q in np.unique(cl):
            m = cl == q; h_ = np.histogram(ang[m], bins=36, range=(-math.pi, math.pi))[0]
            cover = (h_ > 0).mean()
            if cover >= 300 / 360:                                     # the outermost: the skin, not a cavity inside it
                md = float(np.median(dist[m]))                         # (a mouth, a nostril)
                if best is None or md > best[0]:
                    best = (md, q)
        if best is None:
            return np.nan, False, np.zeros((0, 3))
        m = cl == best[1]; L = float(seglen[m].sum()); ends = (deg[ia[m]] == 1).any() or (deg[ib[m]] == 1).any()
        far = dist[m].max() > R * 0.92
        return (np.inf if far else L), not ends, np.r_[A[m], Bp[m]]


def _axis_profile(V, B, g, h, span, S, dim, faces=None, stop_after=4, from_tip=False):
    """(L2) a protrusion's own axis and its plane sections, measured from its seeds: stations every h of g (the walking
    distance from the seeds). Pass 1: each station's band of g gives a point (its centroid) and a direction (the
    centroids about one ring radius before and after); the plane section across that direction (_Sectioner) gives the
    skin's own loop. Pass 2: the axis is re-laid through the loops' centres (a band slides toward a junction - a thigh's
    toward the crotch - before its section does) and the sections are cut again across it. r = loop length / 2 pi
    (3-D: a tube's radius); inf where the loop reaches past 3 x the largest radius met so far (it has merged with a
    larger body: a thigh with the other thigh, an arm with the chest); the walk stops after stop_after such stations.
    Returns the stations' g, centres, directions and r"""
    va = B["va"]; ok = np.isfinite(g) & (g <= span) & (g > 0)
    idx = np.nonzero(ok)[0]; bi = (g[idx] / h).astype(np.int64); nb = int(bi.max()) + 1 if len(bi) else 0
    if nb < 3:
        return np.zeros(0), np.zeros((0, 3)), np.zeros((0, 3)), np.zeros(0)
    w = va[idx]; cnt = np.bincount(bi, w, minlength=nb); good = cnt > 0
    C = np.stack([np.bincount(bi, w * V[idx, k], minlength=nb) for k in range(3)], 1) / np.maximum(cnt, 1e-30)[:, None]
    rad = cnt / h / (2 * math.pi)                                      # the geodesic ring's radius: the reach of a section
    for b in np.nonzero(~good)[0]:
        C[b] = C[b - 1] if b else C[np.argmax(good)]
    k2p = 2 * math.pi if dim == 3 else 2.0

    def dirs(P, rr, back=False):
        D = np.zeros((len(P), 3))
        for b in range(len(P)):
            k = max(3 if from_tip else 1, int(round(min(rr[b] if np.isfinite(rr[b]) else h, 50 * h) / h)))   # from a tip:
            if back and b >= k:                                        # >= 3 stations (centroids a step apart turn its plane anyhow)                                        # pass 2: from the stations already walked, so a
                D[b] = _unit(P[b] - P[max(b - 2 * k, 0)])              # junction ahead does not tilt the plane before it
            else:
                D[b] = _unit(P[min(b + k, len(P) - 1)] - P[max(b - k, 0)])
        return D

    def walk(P, D):
        r = np.full(len(P), np.nan); cen = P.copy(); rmax = None; run = 0; n = len(P)
        for b in range(len(P)):
            R = 3.0 * max(rad[b], h) + 3 * h
            if rmax is not None:
                R = min(R, 3.0 * rmax + 3 * h)
            L, closed, pts = S.section(P[b], D[b], R, faces)
            r[b] = L / k2p
            if np.isfinite(L) and len(pts):
                cen[b] = pts.mean(0); rmax = max(rmax or 0.0, r[b]); run = 0
            elif np.isinf(L) and (rmax is not None or not from_tip):  # (a tip's first, tilted cuts do not stop its walk;
                run += 1                                               # a walk from cut parts that starts merged stops)
                if run >= stop_after:
                    n = b + 1; break
        return r[:n], cen[:n], n
    D1 = dirs(C, rad)
    r1, cen, n = walk(C, D1)
    C2 = cen.copy()
    if n >= 3:                                                         # the loops' centres, smoothed along the axis
        C2[1:-1] = (cen[:-2] + cen[1:-1] + cen[2:]) / 3
    D2 = dirs(C2, np.where(np.isfinite(r1), r1, rad[:n]), back=True)
    r, _, n2 = walk(C2, D2)
    C2, D2 = C2[:n2], D2[:n2]
    gb = (np.arange(n2) + 0.5) * h
    m = ~np.isnan(r)                                                   # no loop round the axis point (it left the skin,
    if m.any() and not m.all():                                        # e.g. under a chin): from the stations round it
        ri = np.interp(gb, gb[m], np.where(np.isinf(r[m]), 1e9, r[m])); r = np.where(m, r, np.where(ri >= 1e8, np.inf, ri))
    return gb, C2, D2, r


def branch_segments(V, F, B, dim, prm, log=print):
    """PROTRUSIONS, nested. f = the protrusion function: (default, function "agd") the average geodesic distance to
    agd_samples points spread over the surface - largest at the extremities, smallest at the centre - or ("core") the
    geodesic distance from the thickest place. Lengths are in units of the core radius (the 98th percentile of the
    inner radius). TIPS = maxima of f
    that live at least tau = tip_persistence x the core radius before merging into an older component; tips that
    merge with each other group into one protrusion (a merge-tree arc: the claws of one foot -> the leg). Each
    protrusion is found by RING GROWTH: geodesic distance g from its tip (a leaf) or from the parts already cut from it
    (its children), the ring radius along g, cut where it flares (_flare_cut); a part = what lies inside its cut, less its
    children. What no protrusion takes is the core part (0). Returns per-vertex part index and per part: parent, tip,
    kind (core / leaf / internal), cut length."""
    from scipy.sparse.csgraph import dijkstra, connected_components
    prm = {**prm, **{k[:-3]: v for k, v in prm.items() if k.endswith(f"_{dim}d")}}   # key_2d / key_3d: for that kind only
    n = len(V); T = inner_radius(V, F, B, dim); T = np.where(np.isfinite(T), T, 0.0)
    rc = float(np.percentile(T[T > 0], 98)); deep = int(np.argmax(np.where(T <= rc, T, 0)))
    G = B["G"]
    if prm.get("function", "agd") == "agd":                          # average geodesic distance to samples spread over the
        rng = np.random.default_rng(0); k = int(prm.get("agd_samples", 32))   # surface (far-point sampled): highest at the
        S = [int(rng.integers(len(V)))]; dmin = np.linalg.norm(V - V[S[0]], axis=1)   # extremities, lowest at the centre
        for _ in range(k - 1):
            S.append(int(np.argmax(dmin))); dmin = np.minimum(dmin, np.linalg.norm(V - V[S[-1]], axis=1))
        D = dijkstra(G, indices=np.array(S)); D[~np.isfinite(D)] = np.nan
        f = np.nanmean(D, 0); f = np.where(np.isfinite(f), f, np.nanmin(f)); f = f - np.nanmin(f)
        seeds = np.array([int(np.argmin(f))]); deep = int(seeds[0])
    elif prm.get("function") == "centre":                             # (L2) the walking distance from the centre (the least
        rng = np.random.default_rng(0); k = int(prm.get("agd_samples", 32))   # average geodesic distance): extremities only,
        S = [int(rng.integers(len(V)))]; dmin = np.linalg.norm(V - V[S[0]], axis=1)   # no bumps of their own sides (a chin
        for _ in range(k - 1):                                         # on a head: a maximum of the average, not of this)
            S.append(int(np.argmax(dmin))); dmin = np.minimum(dmin, np.linalg.norm(V - V[S[-1]], axis=1))
        D = dijkstra(G, indices=np.array(S)); D[~np.isfinite(D)] = np.nan
        fa_ = np.nanmean(D, 0); fa_ = np.where(np.isfinite(fa_), fa_, np.nanmax(fa_)); deep = int(np.argmin(fa_)); del D
        d0 = dijkstra(G, indices=deep, limit=prm.get("core_seed", 0.5) * rc); seeds = np.nonzero(np.isfinite(d0))[0]
        f = dijkstra(G, indices=seeds, min_only=True); f = np.where(np.isfinite(f), f, -1.0)
    else:                                                              # geodesic distance from the thickest place
        d0 = dijkstra(G, indices=deep, limit=prm.get("core_seed", 0.5) * rc); seeds = np.nonzero(np.isfinite(d0))[0]
        f = dijkstra(G, indices=seeds, min_only=True); f = np.where(np.isfinite(f), f, -1.0)
    tau = prm.get("tip_persistence", 0.3) * rc
    lab, arcs, absorbed = _merge_tree(G.indptr, G.indices, f, tau)
    live = [i for i in range(len(arcs)) if i not in absorbed]
    children = {i: [] for i in live}
    for i in live:
        if arcs[i][0] >= 0:
            children[arcs[i][0]].append(i)
    root_arc = int(lab[seeds[0]])
    h = prm.get("bin", 0.06) * rc; flare = prm.get("flare_deg", 40.0); min_len = prm.get("min_part_length", 0.25) * rc
    va = B["va"]; total = va.sum(); min_area = prm.get("min_part_area", 0.0005) * total
    sections = prm.get("profile", "rings") == "sections"
    sectioner = _Sectioner(V, F) if sections else None
    piece = {}                       # arc -> vertex set of its piece (with its children's), or the children's when no own part
    parts = [{"arc": root_arc, "parent": -1, "tip": deep, "kind": "core"}]; owner = np.zeros(n, np.int64); made = {}
    for i in sorted(live, key=lambda i: -arcs[i][2]):                 # tips first, then merges, from the top down
        if i == root_arc or arcs[i][2] <= 0:
            continue
        a = arcs[i]; kids = [c for c in children[i] if c in piece]
        sv = np.array([a[1]]) if a[4] == "leaf" else (np.unique(np.concatenate([piece[c] for c in kids])) if kids else np.array([a[1]]))
        span = (a[2] - (a[3] if a[3] is not None else 0.0)) + 2.0 * rc
        g = dijkstra(G, indices=sv, min_only=True, limit=span); g = np.where(np.isfinite(g), g, np.inf)
        plane = None
        if sections:                                                   # (L2) sections across the part's own axis; the cut
            hh, ml, sp = h, min_len, span                              # is that plane
            if a[4] == "leaf" and prm.get("local_scale"):             # a tip's own scale: a finger 1.6 cm thick is walked
                Tt = float(np.median(T[g <= 0.15 * rc])) if (g <= 0.15 * rc).any() else rc   # in steps of a quarter of its
                ls = prm["local_scale"]                                # thickness, and a part needs a shaft as long as it
                hh = min(h, max(h / 8, ls.get("bin", 0.25) * Tt))      # is thick (a toe 2-3 cm long is under the body's
                ml = min(min_len, max(ls.get("min_length", 1.0) * Tt, 2 * hh))   # 3.6 cm minimum shaft)
                sp = min(span, ls.get("span_steps", 40) * hh + ls.get("span_thick", 6.0) * Tt)
            gb, C_, D_, r = _axis_profile(V, B, g, hh, sp, sectioner, dim, from_tip=not kids)
            j = _flare_index(r, gb, hh, flare, ml, prm.get("slope_window", 0.5)) if len(r) else None
            c = None if j is None else gb[j] + 0.5 * hh
            if j is not None:
                plane = (C_[j], D_[j])
        else:
            r, gb = _ring_profile(np.where(np.isfinite(g), g, -1), va, h, span, dim)
            c = _flare_cut(r, gb, h, flare, min_len)
        if os.environ.get("LANGUAGE_DEBUG"):
            log(f"    arc {i} {a[4]} tip {np.round(V[a[1]] * 100, 1)} kids {kids} f {a[2]:.3f}-{a[3]} cut {c} span {span:.3f} "
                f"r {np.round(r[:16] * 100, 2) if sections else ''} sv {len(sv)}")
        if c is None:
            if kids:
                piece[i] = sv                                          # no part of its own: its children stand for it
            continue
        if plane is not None:                                          # the tip's side of the cut plane, near the cut
            rr = r[j] if np.isfinite(r[j]) else hh
            vv = np.nonzero(((V - plane[0]) @ plane[1] < 0) & (g <= c + 4 * rr + 2 * hh))[0]
        else:
            vv = np.nonzero(g <= c)[0]
        Gs = G[vv][:, vv]; _, cl = connected_components(Gs, directed=False)
        keep = np.isin(cl, np.unique(cl[np.isin(vv, sv)])); vv = vv[keep]
        own = np.setdiff1d(vv, sv) if a[4] != "leaf" else vv
        jks = prm.get("limb_junction_share")
        if jks and kids and sum(1 for c_ in kids if va[piece[c_]].sum() >= jks * va[own].sum()) >= 2:
            piece[i] = sv; continue                                    # (L2) where two limbs meet (both legs; the arms and the
        if va[own].sum() < min_area:                                   # head): the body itself, not a protrusion
            if kids:
                piece[i] = sv
            continue
        piece[i] = vv
        parts.append({"arc": i, "parent": 0, "tip": int(a[1]), "kind": a[4], "cut_length": float(c),
                      "children_arcs": kids, **({"cut_plane": [plane[0].tolist(), plane[1].tolist()]} if plane is not None else {})})
        made[i] = len(parts) - 1
        owner[own[owner[own] == 0]] = made[i]                          # an inner (earlier) part keeps its places
    for j, p in enumerate(parts[1:], 1):                               # the parent: the part round its base
        vv = np.nonzero(owner == j)[0]
        nb = np.unique(G[vv].indices); nb = nb[owner[nb] != j]
        outer = nb[(owner[nb] == 0) | (owner[nb] > j)]                 # (L2) a part made later (an outer part) or the core:
        if len(outer):                                                 # a nested part's own children (made earlier) can
            nb = outer                                                 # share more of its border than its parent does
        if len(nb):                                                    # (5 fingers' seams vs a wrist) and made a cycle
            p["parent"] = int(np.bincount(owner[nb]).argmax())
    log(f"  branches: core radius {rc:.4g}, {len(live) - sum(1 for i in live if arcs[i][4] == 'internal')} tips "
        f"(persistence >= {tau:.4g}), {len(parts) - 1} protrusions")
    return owner, parts, {"f": f, "T": T, "rc": rc, "deep": deep}


# ------------------------------------------------------------------------------------------------- facet segmentation
def facet_segments(V, F, B, prm, log=print):
    """FACES of a faceted object. Region growing over the face graph, flattest seeds first: a face joins a region
    while its normal is within facet_deg of the seed's normal (the seed: the flattest face left, so the facet's own
    normal; a running mean drifted across fillets and made mirror faces differ by 4 %); regions of at least
    min_facet x the surface are FACETS. The rest lies between facets: each such face goes to its two nearest facets
    (an EDGE: an arris, a fillet) or, where a third is about as near, to the three (a CORNER), by the walking
    distance over the face graph. Returns per-face part index (0..) and per part: kind, the facets it lies between."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra, connected_components
    fn, fa = B["fn"], B["fa"]; nf = len(F); adj = face_adjacency(F)
    A = coo_matrix((np.ones(2 * len(adj)), (np.r_[adj[:, 0], adj[:, 1]], np.r_[adj[:, 1], adj[:, 0]])), shape=(nf, nf)).tocsr()
    ring = A @ (fn * fa[:, None]) + fn * fa[:, None]; ringa = A @ fa + fa
    flat = np.linalg.norm(ring, axis=1) / np.maximum(ringa, 1e-30)
    cosf = math.cos(math.radians(prm.get("facet_deg", 20.0))); lab = -np.ones(nf, np.int64); regions = []
    for seed in np.argsort(-flat, kind="stable"):
        if lab[seed] >= 0 or flat[seed] < cosf:
            continue
        k = len(regions); lab[seed] = k; nsum = fn[seed] * fa[seed]; mean = fn[seed].copy(); q = [seed]; members = [seed]; qi = 0
        while qi < len(q):
            c = q[qi]; qi += 1
            for g in A.indices[A.indptr[c]:A.indptr[c + 1]]:
                if lab[g] < 0 and fn[g] @ mean >= cosf:              # within facet_deg of the seed's (flattest) normal
                    lab[g] = k; q.append(g); members.append(g)
        regions.append(np.array(members))
    total = fa.sum(); size = float(np.ptp(V, axis=0).max()); keep = []
    for r in regions:                                                  # big enough, and wide (a fillet's strip is not a facet)
        if fa[r].sum() < prm.get("min_facet", 0.004) * total:
            continue
        nm_ = _unit((fn[r] * fa[r, None]).sum(0)); ang = np.degrees(np.arccos(np.clip(fn[r] @ nm_, -1, 1)))
        if fa[r][ang < prm.get("facet_core_deg", 8.0)].sum() < prm.get("facet_core_share", 0.5) * fa[r].sum():
            continue                                                   # no planar core: a curved band (a fillet's strip)
        P = V[np.unique(F[r])]; X = P - P.mean(0); ext = np.sqrt(np.maximum(np.linalg.eigvalsh(X.T @ X / len(P)), 0)) * math.sqrt(12)
        if ext[-2] >= prm.get("min_facet_width", 0.02) * size:
            keep.append(r)
    lab[:] = -1
    for k, r in enumerate(keep):
        lab[r] = k
    nk = len(keep); left = lab < 0
    C = (V[F[:, 0]] + V[F[:, 1]] + V[F[:, 2]]) / 3
    w = np.linalg.norm(C[adj[:, 0]] - C[adj[:, 1]], axis=1)
    D = np.full((nk, nf), np.inf)
    for k in range(nk):                                               # walking distance from facet k over the faces between
        ok = left | (lab == k); e = ok[adj[:, 0]] & ok[adj[:, 1]]
        Gk = coo_matrix((np.r_[w[e], w[e]], (np.r_[adj[e, 0], adj[e, 1]], np.r_[adj[e, 1], adj[e, 0]])), shape=(nf, nf)).tocsr()
        src = np.nonzero(lab == k)[0]
        D[k] = dijkstra(Gk, indices=src, min_only=True, limit=prm.get("edge_reach", 0.05) * np.ptp(V, axis=0).max())
    parts = [{"kind": "facet", "between": [k]} for k in range(nk)]; out = lab.copy()
    li = np.nonzero(left)[0]
    if len(li):
        o = np.argsort(D[:, li], axis=0); d_sorted = np.take_along_axis(D[:, li], o, axis=0)
        key = {}
        ratio = prm.get("corner_ratio", 1.6)
        for j, fi in enumerate(li):
            d1, d2 = d_sorted[0, j], d_sorted[1, j] if nk > 1 else np.inf
            if not np.isfinite(d2):
                out[fi] = o[0, j] if np.isfinite(d1) else -1; continue
            d3 = d_sorted[2, j] if nk > 2 else np.inf
            ks = tuple(sorted(o[:3, j])) if np.isfinite(d3) and d3 <= ratio * max(d2, 1e-12) else tuple(sorted(o[:2, j]))
            if ks not in key:
                key[ks] = len(parts); parts.append({"kind": "corner" if len(ks) == 3 else "edge", "between": [int(x) for x in ks]})
            out[fi] = key[ks]
    # each label's connected pieces: one part each (two arrises between the same pair of facets are two parts)
    final = -np.ones(nf, np.int64); fparts = []
    for k, p in enumerate(parts):
        fk = np.nonzero(out == k)[0]
        if not len(fk):
            continue
        m = np.zeros(nf, bool); m[fk] = True; e = m[adj[:, 0]] & m[adj[:, 1]]
        _, cl = connected_components(coo_matrix((np.ones(e.sum()), (adj[e, 0], adj[e, 1])), shape=(nf, nf)), directed=False)
        for c in np.unique(cl[fk]):
            ff = fk[cl[fk] == c]
            keep_min = prm.get("min_corner", 0.00002) if p["kind"] == "corner" else prm.get("min_strip", 0.0003)
            if p["kind"] == "facet" or fa[ff].sum() >= keep_min * total:
                final[ff] = len(fparts); fparts.append(dict(p))
    final = _fill_unlabelled(final, adj)
    log(f"  facets: {nk} facets, {sum(1 for p in fparts if p['kind'] == 'edge')} edges, "
        f"{sum(1 for p in fparts if p['kind'] == 'corner')} corners")
    return final, fparts


def _fill_unlabelled(lab, adj, rounds=200):
    """faces left with -1 take their labelled neighbours' most common label (grown in rounds)"""
    lab = lab.copy()
    for _ in range(rounds):
        miss = lab < 0
        if not miss.any():
            break
        a, b = adj[:, 0], adj[:, 1]; give = np.r_[np.c_[a, b][miss[a] & ~miss[b]], np.c_[b, a][miss[b] & ~miss[a]]]
        if not len(give):
            break
        o = np.lexsort((lab[give[:, 1]], give[:, 0])); give = give[o]
        lab[give[:, 0]] = lab[give[:, 1]]                               # any labelled neighbour (the last in order)
    return lab


def _vertex_to_face_labels(F, owner):
    """a face takes the part two or three of its vertices agree on, else its innermost (lowest nonzero) part"""
    o = owner[F]; out = np.where((o[:, 0] == o[:, 1]) | (o[:, 0] == o[:, 2]), o[:, 0], np.where(o[:, 1] == o[:, 2], o[:, 1], -1))
    tie = out < 0
    if tie.any():
        oo = np.where(o[tie] > 0, o[tie], 1 << 30); m = oo.min(1); out[tie] = np.where(m == 1 << 30, 0, m)
    return out


def _clean_fragments(lab, adj, fa):
    """a part split in several pieces keeps its largest; the other pieces join the neighbours they touch"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    nf = len(lab)
    for _ in range(3):
        same = lab[adj[:, 0]] == lab[adj[:, 1]]; e = adj[same]
        _, cl = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(nf, nf)), directed=False)
        area = np.bincount(cl, fa); comp_lab = np.zeros(cl.max() + 1, np.int64); comp_lab[cl] = lab
        best = {}
        for c in np.argsort(-area):
            best.setdefault(int(comp_lab[c]), int(c))
        keep = np.array([best[int(comp_lab[c])] == c for c in range(len(area))])
        stray = ~keep[cl]
        if not stray.any():
            break
        lab2 = lab.copy(); lab2[stray] = -1; lab = _fill_unlabelled(lab2, adj)
    return lab


# ------------------------------------------------------------------------------------------------------ segmenting
def _submesh(V, F, fmask):
    ff = np.nonzero(fmask)[0]; used = np.unique(F[ff]); remap = -np.ones(len(V), np.int64); remap[used] = np.arange(len(used))
    return V[used], remap[F[ff]], used, ff


def segment(V, F, dim, seg, file_labels=None, log=print):
    """the object's parts by the pack's methods (seg = the pack's "segmentation" block, with the job's overrides):
    groups first (the file's own labels when seg["use_file_labels"] names one, else separate shells when "components"
    is listed), then each large-enough group by "facets" or "branches". Returns per-face part index (0..) and the part
    list: kind (core / protrusion / facet / edge / corner / shell / labelled), parent index (-1 none), tip vertex,
    the facets an edge or corner lies between, the file label."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    B = mesh_basics(V, F); fa = B["fa"]; total = fa.sum(); nf = len(F); adj = face_adjacency(F)
    methods = seg.get("methods", ["components", "branches"])
    if seg.get("use_file_labels") and file_labels and seg["use_file_labels"] in file_labels:
        gid, gnames = file_labels[seg["use_file_labels"]]; groups = [(np.nonzero(gid == k)[0], gnames[k]) for k in np.unique(gid)]
        gkind = "labelled"
    elif "components" in methods:
        vl = face_components(F, len(V)); fl = vl[F[:, 0]]; groups = [(np.nonzero(fl == k)[0], None) for k in np.unique(fl)]
        gkind = "shell"
    else:
        groups = [(np.arange(nf), None)]; gkind = "shell"
    groups.sort(key=lambda g: -fa[g[0]].sum())
    small = seg.get("min_shell", 0.0005); lab = -np.ones(nf, np.int64); parts = []
    for gi, (ff, gname) in enumerate(groups):
        ga = fa[ff].sum()
        if ga < small * total and gi > 0:                              # debris: joins whatever it touches or is nearest
            continue
        fmask = np.zeros(nf, bool); fmask[ff] = True
        method = "facets" if "facets" in methods else ("branches" if "branches" in methods else None)
        if method and ga >= seg.get("split_min_share", 0.05) * total and len(ff) > 50:
            Vs, Fs, used, ffs = _submesh(V, F, fmask); Bs = mesh_basics(Vs, Fs)
            if method == "facets":
                fl, fparts = facet_segments(Vs, Fs, Bs, seg.get("facets", {}), log)
                base = len(parts)
                for p in fparts:
                    parts.append({"kind": p["kind"], "parent": -1, "tip": -1, "between": [base + b for b in p["between"]],
                                  "group": gi, "file_label": gname})
                lab[ffs] = base + fl
            else:
                owner, bparts, aux = branch_segments(Vs, Fs, Bs, dim, seg.get("branches", {}), log)
                fl = _vertex_to_face_labels(Fs, owner); base = len(parts)
                for j, p in enumerate(bparts):
                    parts.append({"kind": ("core" if j == 0 else "protrusion") if gkind != "labelled" or j else "labelled",
                                  "parent": (base + p["parent"]) if p["parent"] >= 0 else -1,
                                  "tip": int(used[p["tip"]]), "group": gi, "file_label": gname,
                                  "arc_kind": p["kind"], "cut_length": p.get("cut_length")})
                lab[ffs] = base + fl
        else:
            parts.append({"kind": gkind if gi > 0 or gkind == "labelled" else "core", "parent": -1, "tip": -1, "group": gi,
                          "file_label": gname})
            lab[ff] = len(parts) - 1
    lab = _fill_unlabelled(lab, adj)
    if (lab < 0).any():                                                # debris shells touching nothing: the nearest part's
        from scipy.spatial import cKDTree
        Cf = V[F].mean(1); ok = lab >= 0; lab[~ok] = lab[ok][cKDTree(Cf[ok]).query(Cf[~ok])[1]]
    lab0 = lab.copy(); lab = _clean_fragments(lab, adj, fa); lab = np.where(lab < 0, lab0, lab)   # a stray piece that touches
    jr = seg.get("branches", {}).get("junction_share", 0.6)                                       # nothing keeps its part
    for k, p in enumerate(parts):                                      # a short junction piece between a part and the part(s)
        kids_k = [j for j, q in enumerate(parts) if q["parent"] == k]  # growing from it joins what it grows from
        if p["kind"] != "protrusion" or not kids_k or p["parent"] < 0:
            continue
        own = fa[lab == k].sum(); big = max(fa[lab == j].sum() for j in kids_k)
        if own < jr * big:
            lab[lab == k] = p["parent"]
            for j in kids_k:
                parts[j]["parent"] = p["parent"]
            p["merged_into"] = p["parent"]
    used = np.unique(lab); remap = -np.ones(len(parts), np.int64); remap[used] = np.arange(len(used))
    parts2 = []
    for k in used:
        p = dict(parts[k]); p["parent"] = int(remap[p["parent"]]) if p["parent"] >= 0 and remap[p["parent"]] >= 0 else -1
        if "between" in p:
            p["between"] = [int(remap[b]) for b in p["between"] if remap[b] >= 0]
        parts2.append(p)
    lab = remap[lab]
    for k, p in enumerate(parts2):                                    # shells: attached to the nearest other part
        if p["kind"] in ("shell", "labelled") and p["parent"] < 0 and len(parts2) > 1:
            ff = np.nonzero(lab == k)[0]; c = (V[F[ff]].mean(1) * fa[ff, None]).sum(0) / fa[ff].sum()
            other = np.nonzero(lab != k)[0]
            if len(other) and p["kind"] == "shell":
                from scipy.spatial import cKDTree
                Co = V[F[other]].mean(1); j = other[cKDTree(Co).query(c)[1]]; p["parent"] = int(lab[j]); p["attached"] = False
    return lab, parts2, B


# --------------------------------------------------------------------------------------------------- descriptors
def object_frame(V, dim, front2d="+x"):
    """the frame names are read in: 3-D, the engine frame (x left, y back, z up; ingest turned the source so); 2-D, the
    image plane (y up; front = the way the drawn object faces, the job's front: +x right or -x left)"""
    lo, hi = V.min(0), V.max(0); c = (lo + hi) / 2; half = np.maximum((hi - lo) / 2, 1e-12)
    if dim == 3:
        up, front, left = np.array([0, 0, 1.0]), np.array([0, -1.0, 0]), np.array([1.0, 0, 0])
    else:
        up = np.array([0, 1.0, 0]); front = np.array([1.0 if front2d.startswith("+") else -1.0, 0, 0]); left = np.zeros(3)
    return {"centre": c, "half": half, "lo": lo, "hi": hi, "up": up, "front": front, "left": left, "dim": dim,
            "size": float(np.linalg.norm(hi - lo))}


def describe(V, F, lab, parts, B, fr):
    """per part, measured on its faces: area (cm2, share), centroid and its place in the object (up / front / left, -1
    .. 1 of the object's half extent), the mean normal (and how flat: |sum of n a| / sum a), principal extents (cm),
    elongation, flatness, the base (the seam with its parent) and tip, length, taper (radius near the tip / at the
    base), the tree (depth, children, leaves under it), whether it reaches the ground, which way it faces"""
    fa, fn = B["fa"], B["fn"]; total = fa.sum(); out = []; n = len(parts)
    kids = {k: [] for k in range(n)}
    for k, p in enumerate(parts):
        if p["parent"] >= 0:
            kids[p["parent"]].append(k)
    depth = {}

    def dep(k):
        if k not in depth:
            depth[k] = 0 if parts[k]["parent"] < 0 else dep(parts[k]["parent"]) + 1
        return depth[k]

    def leaves(k):
        return 1 if not kids[k] else sum(leaves(c) for c in kids[k])
    vpart = [set() for _ in range(n)]
    for k in range(n):
        vpart[k] = None
    vfaces = {k: np.nonzero(lab == k)[0] for k in range(n)}
    vverts = {k: np.unique(F[vfaces[k]]) for k in range(n)}
    for k, p in enumerate(parts):
        ff = vfaces[k]; a = fa[ff]; A = a.sum(); C = V[F[ff]].mean(1); c = (C * a[:, None]).sum(0) / A
        ns = (fn[ff] * a[:, None]).sum(0); nflat = float(np.linalg.norm(ns) / A); nm = _unit(ns)
        P = V[vverts[k]]; X = P - P.mean(0)
        ev, evec = np.linalg.eigh(X.T @ X / max(len(P), 1)); ax = evec[:, ::-1]
        ext = np.ptp(X @ ax, axis=0) * 100
        rel = (c - fr["centre"]) / fr["half"]
        d = {"area_cm2": round(float(A * 1e4), 4), "area_share": float(A / total), "centroid": c.tolist(),
             "up": float(rel @ fr["up"]), "front": float(rel @ fr["front"]), "left": float(rel @ fr["left"]) if fr["dim"] == 3 else 0.0,
             "normal": nm.tolist(), "normal_flat": nflat,
             "normal_up": float(nm @ fr["up"]), "normal_front": float(nm @ fr["front"]), "normal_left": float(nm @ fr["left"]),
             "extent_cm": ext.round(3).tolist(), "elong": float(ext[0] / max(ext[1], 1e-9)),
             "flatness": float(ext[2] / max(ext[1], 1e-9)) if fr["dim"] == 3 else 0.0,
             "depth": dep(k), "children": len(kids[k]), "leaves_under": leaves(k) if kids[k] else 0, "is_leaf": not kids[k],
             "ground": bool((P[:, 2].min() - fr["lo"][2]) < 0.04 * (fr["hi"][2] - fr["lo"][2])) if fr["dim"] == 3 else
                       bool((P[:, 1].min() - fr["lo"][1]) < 0.04 * (fr["hi"][1] - fr["lo"][1])),
             "facing": "out" if nm @ (c - fr["centre"]) >= 0 else "in", "kind": p["kind"], "dim": fr["dim"]}
        par = p["parent"]
        if par >= 0:
            seam = np.intersect1d(vverts[k], vverts[par])
            base = V[seam].mean(0) if len(seam) else V[vverts[k]][np.argmin(np.linalg.norm(V[vverts[k]] - V[vverts[par]].mean(0), axis=1))]
            tipv = p["tip"] if p.get("tip", -1) >= 0 and p["tip"] in set(vverts[k].tolist()) else int(vverts[k][np.argmax(np.linalg.norm(P - base, axis=1))])
            tip = V[tipv]; L = float(np.linalg.norm(tip - base)); axd = _unit(tip - base)
            t = (P - base) @ axd / max(L, 1e-12); radial = np.linalg.norm((P - base) - np.outer((P - base) @ axd, axd), axis=1)
            rb = float(np.median(radial[t < 0.2])) if (t < 0.2).any() else float("nan")
            rt = float(np.median(radial[(t > 0.7) & (t < 0.95)])) if ((t > 0.7) & (t < 0.95)).any() else float("nan")
            gl, gt, gr = _geo_shape(V, F, vfaces[k], tipv, B, fr["dim"])
            d.update(base=base.tolist(), tip=tip.tolist(), tip_vertex=int(tipv), seam_vertices=int(len(seam)), length_cm=L * 100,
                     length_rel=L / fr["size"], chord_taper=rt / rb if rb > 0 else float("nan"), base_radius_cm=(gr or rb) * 100,
                     taper=gt, geo_length_cm=gl * 100, geo_length_rel=gl / fr["size"],
                     slender=max(L, gl) / max(2 * (gr or rb), 1e-12), direction=axd.tolist(),
                     dir_up=float(axd @ fr["up"]), dir_front=float(axd @ fr["front"]))
        out.append(d)
    _sides(out, fr)
    for d, p in zip(out, parts):                                      # (L4) a side a pack step gave (a face's
        if p.get("side_of") is not None:                              # eyes: by the head's own mid-plane)
            d["side"] = p["side_of"]
    return out


def _geo_shape(V, F, ff, tipv, B, dim):
    """a protrusion measured along itself: the walking distance from its tip over its own faces (its length along a
    curve), the ring radius along it (band area per unit length), and the TAPER = the median ring radius over the
    tip's third / over the base's third (a point: small; a blunt or widening part: about 1 or more)"""
    from scipy.sparse.csgraph import dijkstra
    Fs = F[ff]; used = np.unique(Fs); rm = -np.ones(len(V), np.int64); rm[used] = np.arange(len(used))
    G = B["G"][used][:, used]
    if tipv not in set(used.tolist()):
        return float("nan"), float("nan"), None
    g = dijkstra(G, indices=int(rm[tipv])); g = np.where(np.isfinite(g), g, np.nan); L = float(np.nanmax(g))
    if not L > 0:
        return 0.0, float("nan"), None
    va = B["va"][used]; nb = 12; b = np.clip((g / L * nb).astype(np.int64), 0, nb - 1); ok = np.isfinite(g)
    r = np.bincount(b[ok], va[ok], minlength=nb) / (L / nb) / (2 * math.pi if dim == 3 else 2.0)
    tip_r, base_r = float(np.median(r[:4])), float(np.median(r[8:]))
    return L, (tip_r / base_r if base_r > 0 else float("nan")), base_r


def _sides(desc, fr):
    """left / right / mid by the centroid's place across the object's mid-plane (3-D only: a drawing seen from the
    side has no sides)"""
    for d in desc:
        if fr["dim"] != 3:
            d["side"] = ""; continue
        x = d["left"]; d["side"] = "L" if x > 0.12 else ("R" if x < -0.12 else "")


# ------------------------------------------------------------------------------------------------------- naming
def _cond_ok(d, cond, parts, names, kinds, k, desc):
    for key, want in cond.items():
        if key == "part_kind":
            if d["kind"] not in want:
                return False
        elif key == "parent_kind":
            par = parts[k]["parent"]; pk = kinds.get(par)
            if (pk not in want) if want else (par >= 0):
                return False
        elif key == "children_kind_min":
            for kk, nmin in want.items():
                if sum(1 for j, p in enumerate(parts) if p["parent"] == k and kinds.get(j) == kk) < nmin:
                    return False
        elif key == "ancestor_kind":                                  # (L2) any part it grows from (its parent's parent...)
            q = parts[k]["parent"]; hit = False
            while q >= 0:
                hit |= kinds.get(q) in want; q = parts[q]["parent"]
            if not hit:
                return False
        elif key == "descendant_kind_min":
            for kk, nmin in want.items():
                if _count_desc(k, parts, kinds, kk) < nmin:
                    return False
        elif key == "between_kind_any":                               # an edge / corner beside a part of these words
            if not any(kinds.get(b) in want for b in parts[k].get("between", [])):
                return False
        elif key == "class":
            if d.get("class") not in want:
                return False
        elif key.endswith("_abs_min"):
            v = d.get(key[:-8])
            if v is None or not np.isfinite(v) or abs(v) < want:
                return False
        elif key.endswith("_abs_max"):
            v = d.get(key[:-8])
            if v is None or not np.isfinite(v) or abs(v) > want:
                return False
        elif key.endswith("_min"):
            v = d.get(key[:-4])
            if v is None or not np.isfinite(v) or v < want:
                return False
        elif key.endswith("_max"):
            v = d.get(key[:-4])
            if v is None or not np.isfinite(v) or v > want:
                return False
        else:
            if d.get(key) != want:
                return False
    return True


def _fill(t, k, kd, side, par, parts, desc, names, n, _n):
    d = desc[k]
    fill = {"kind": kd, "side": side, "_side": ("_" + side) if side else "", "n": n, "_n": _n,
            "parent": names.get(par, "") if par >= 0 else "",
            "updown": "top" if d["normal_up"] >= 0 else "bottom", "frontback": "front" if d["normal_front"] >= 0 else "back",
            "leftright": "left" if d["normal_left"] >= 0 else "right", "forehind": "fore" if d["front"] >= 0 else "hind",
            "between": "_".join(names.get(b, "") for b in parts[k].get("between", [])),
            "place": (("front" if d["front"] >= 0 else "back") if abs(d["front"]) >= abs(d["left"]) else ("left" if d["left"] >= 0 else "right"))}
    nm = re.sub(r"[^A-Za-z0-9_]+", "_", t.format(**fill)).strip("_") or f"part_{k}"
    return re.sub(r"_+", "_", nm)


def _count_desc(k, parts, kinds, kk):
    n = 0
    for j, p in enumerate(parts):
        q = p["parent"]
        while q >= 0:
            if q == k:
                n += kinds.get(j) == kk; break
            q = parts[q]["parent"]
    return n


def name_parts(parts, desc, rules, keep=None, log=print, fixed=None):
    """vocabulary words and names from the pack's rules, in order. A rule: kind (the word), when (conditions on the
    part's descriptors; *_min / *_max bounds, part_kind, parent_kind, children_kind_min, descendant_kind_min, any other
    key equal), optionally pick {by, order: max|min, count} among the parts that pass, and a name template:
    {kind} {side} {_side} {parent} {n} {_n} {updown} {frontback} {leftright} (by the normal) {place} (by
    the centroid: front / back / left / right, whichever is larger) {forehind} {between}. keep: names that
    stay (the person's, earlier builds'): {index: (name, kind, by)}. Unnamed parts: {part_kind}_{n}."""
    n = len(parts); kinds, names, by, trule = {}, {}, {}, {}
    for k, (nm, kd, b) in (keep or {}).items():
        names[k], kinds[k], by[k] = nm, kd, b
    rule_of = {}
    for r in rules:                                                    # (L2) a word's first rule: its name template
        rule_of.setdefault(r["kind"], r)
    for k, w in (fixed or {}).items():                                 # (L2) words a pack's split or merge gave
        if k not in kinds and w:
            kinds[k] = w; by[k] = f"{rule_of.get(w, {}).get('_from', 'pack')} rule: {w}"
            trule[k] = rule_of.get(w, {}).get("name", "{kind}{_side}{_n}")
    for ri, r in enumerate(rules):
        cand = [k for k in range(n) if k not in kinds and _cond_ok(desc[k], r.get("when", {}), parts, names, kinds, k, desc)]
        if "pick" in r and cand:
            pk = r["pick"]; key = lambda k: desc[k].get(pk["by"], 0) or 0
            have = sum(1 for k in kinds if kinds[k] == r["kind"])        # (L2) words fixed earlier count toward the picks
            cand = sorted(cand, key=key, reverse=pk.get("order", "max") == "max")[:max(pk.get("count", 1) - have, 0)]
        for k in cand:
            kinds[k] = r["kind"]; by[k] = f"{r.get('_from', 'pack')} rule: {r['kind']}"; trule[k] = r.get("name", "{kind}{_side}{_n}")
    tmpl = {}
    for r in rules:                                                    # the first rule of a word gives its name template
        tmpl.setdefault(r["kind"], r.get("name", "{kind}{_side}{_n}"))
    order_name = lambda k: (desc[k]["depth"], -desc[k]["front"], -desc[k]["up"], desc[k]["left"])
    todo = sorted([k for k in range(n) if k not in names], key=order_name)
    for _ in range(6):                                                 # stems (no index) -> numbered per stem over the whole
        rendered = {}                                                  # object -> again, as children carry parent names
        for k in todo:
            kd = kinds.get(k) or parts[k]["kind"]; t = trule.get(k) or "{kind}{_n}"        # the template of the rule that named it
            rendered[k] = (t, kd, _fill(t, k, kd, desc[k]["side"], parts[k]["parent"], parts, desc, names, "", ""))
        stems = {}
        for k in todo:
            stems.setdefault(rendered[k][2], []).append(k)
        new_names = {}
        for stem, kk in stems.items():
            nb_ = rule_of.get(kinds.get(kk[0]), {}).get("number_by")    # (L2) numbered in an order the pack gives
            if nb_:                                                    # (the digits of a hand: 1 = the thumb)
                kk = sorted(kk, key=lambda k: (abs(desc[k].get(nb_["key"], 0) or 0) if nb_.get("abs") else (desc[k].get(nb_["key"], 0) or 0))
                            * (-1 if nb_.get("order", "max") == "max" else 1))
            for i, k in enumerate(kk):
                t, kd, _ = rendered[k]
                new_names[k] = _fill(t, k, kd, desc[k]["side"], parts[k]["parent"], parts, desc, names, str(i + 1), f"_{i + 1}" if len(kk) > 1 else "")
        if all(names.get(k) == v for k, v in new_names.items()):
            break
        names.update(new_names)
    for k in todo:
        by[k] = by.get(k) or "generic (no rule)"
    seen = {}
    for k in range(n):                                                 # unique names
        nm = names[k]
        if nm in seen:
            j = 2
            while f"{nm}_{j}" in seen:
                j += 1
            names[k] = f"{nm}_{j}"
        seen[names[k]] = k
    return names, kinds, by


# --------------------------------------------------------------------------------------- splits and merges (L2)
def _part_submesh(V, F, fm):
    Fk = F[fm]; vk = np.unique(Fk); rm = -np.ones(len(V), np.int64); rm[vk] = np.arange(len(vk))
    return V[vk], rm[Fk], vk, rm


def _split_plane(V, F, lab, parts, k, spec, dim, log=print):
    """where a pack's split cuts part k: its own axis and plane sections walked from its tip side (the seam with what
    grows from it, else its tip) over the part's own faces (_axis_profile; stations every 1 % of its length), then
    at = "narrowest": the narrowest section in the window (fractions of the part's length from the tip side: a wrist, an
    ankle); at = "fold": per direction round the axis, the most concave bend of the skin's distance from the axis between
    the widest section and the narrowest after it (a jaw over a neck, an occiput over a nape), and the plane fitted
    through those bends. Returns (point, normal toward the base, seeds, info) or None"""
    from scipy.sparse.csgraph import dijkstra
    sys.path.insert(0, HERE)
    import part_frame as PF
    fm = lab == k
    kids = [j for j, q in enumerate(parts) if q["parent"] == k]
    vk0 = np.unique(F[fm])
    seeds = np.intersect1d(vk0, np.unique(F[np.isin(lab, kids)])) if kids else np.zeros(0, np.int64)
    if not len(seeds):
        t = parts[k].get("tip", -1)
        if t is None or t < 0 or t not in set(vk0.tolist()):
            return None
        seeds = np.array([t])
    beyond = spec.get("beyond_cm", 0.0) * 0.01
    if beyond > 0 and parts[k]["parent"] >= 0:                         # a base recut: the walk goes on past the part's base
        par = parts[k]["parent"]; fz = fm | (lab == par)               # into what it grows from, as far as `beyond`
        Vz, Fz, vz, rz = _part_submesh(V, F, fz); gz = dijkstra(mesh_basics(Vz, Fz)["G"], indices=rz[seeds], min_only=True)
        Lk = float(np.nanmax(np.where(np.isfinite(gz) & np.isin(vz, vk0), gz, np.nan)))
        near = np.zeros(len(V), bool); near[vz[np.isfinite(gz) & (gz <= Lk + beyond)]] = True
        fm = fm | ((lab == par) & near[F].all(1))
    Vs, Fs, vk, rm = _part_submesh(V, F, fm)
    Bs = mesh_basics(Vs, Fs); g = dijkstra(Bs["G"], indices=rm[seeds], min_only=True)
    L = float(np.nanmax(np.where(np.isfinite(g), g, np.nan)))
    if not L > 0:
        return None
    h = spec.get("step", 0.01) * L
    gb, C, D, r = _axis_profile(Vs, Bs, g, h, L, _Sectioner(Vs, Fs), dim, stop_after=10 ** 9)
    if len(gb) < 6:
        return None
    w0, w1 = spec.get("window", [0.03, 0.6]); win = (gb >= w0 * L) & (gb <= w1 * L) & np.isfinite(r) & (r > 0)
    if not win.any():
        return None
    info = {"at": spec["at"], "length_cm": round(L * 100, 2), "step_cm": round(h * 100, 3)}
    if spec["at"] == "narrowest":
        b = int(np.nonzero(win)[0][np.argmin(r[win])])
        info.update(station_cm=round(gb[b] * 100, 2), radius_cm=round(r[b] * 100, 3),
                    girth_cm=round(r[b] * 100 * (2 * math.pi if dim == 3 else 2.0), 2))
        return C[b], D[b], seeds, info
    if spec["at"] == "fold":
        idx = np.nonzero(win)[0]
        if spec.get("from") == "narrowest":                            # a base fold: from the narrowest section to the end
            bmax = int(idx[np.argmin(r[idx])]); bmin = int(np.nonzero(np.isfinite(r))[0].max())
            if bmin - bmax < 3:
                return None
        else:                                                          # a tip fold: from the widest to the narrowest after it
            bmax = int(idx[np.argmax(r[idx])])
            after = idx[idx > bmax]
            if len(after) < 3:
                return None
            bmin = int(after[np.argmin(r[after])])
        cas = PF.Caster(V, F); na = int(spec.get("directions", 36)); th = np.radians(np.arange(na) * 360.0 / na)   # the whole
        # skin: a ray from the axis meets the part's own skin first, and does not leave through the part's open ends
        bb = np.arange(max(bmax - 2, 0), min(bmin + 3, len(gb)))
        Rr = np.full((len(bb), na), np.nan); Dirs = np.zeros((len(bb), na, 3))
        for ii, b in enumerate(bb):
            e0 = _unit(np.cross(D[b], [1.0, 0, 0] if abs(D[b][0]) < 0.9 else [0, 1.0, 0])); e1 = np.cross(D[b], e0)
            dirs = np.cos(th)[:, None] * e0 + np.sin(th)[:, None] * e1; Dirs[ii] = dirs
            _, t, f = cas.cast(np.repeat(C[b][None], na, 0), dirs)
            Rr[ii] = np.where(np.isfinite(t) & (f >= 0), t, np.nan)
        P = []
        for a in range(na):
            R_ = Rr[:, a]
            if np.isnan(R_).mean() > 0.3:
                continue
            ok = np.isfinite(R_); R_ = np.interp(np.arange(len(R_)), np.nonzero(ok)[0], R_[ok])
            Rs = np.convolve(R_, np.ones(3) / 3, mode="same"); Rs[0], Rs[-1] = R_[0], R_[-1]
            kap = np.full(len(Rs), -np.inf); kap[1:-1] = Rs[:-2] - 2 * Rs[1:-1] + Rs[2:]
            lo_ = 2 if spec.get("from") != "narrowest" else 3                # (a base fold: not at the narrowest itself)
            kk = kap[lo_:-2] if len(kap) > lo_ + 2 else kap; off = lo_ if len(kap) > lo_ + 2 else 0
            if not np.isfinite(kk).any() or kk.max() <= 0:
                continue
            pk = [q for q in range(len(kk)) if kk[q] >= spec.get("fold_share", 0.4) * kk.max()
                  and (q == 0 or kk[q] >= kk[q - 1]) and (q == len(kk) - 1 or kk[q] >= kk[q + 1])]
            # the strong bend nearest the narrowest section: under a chin, not between a nose and a lip; at the notch,
            # not between two breasts
            i = off + (max(pk) if spec.get("from") != "narrowest" else min(pk))
            P.append(C[bb[i]] + R_[i] * Dirs[i, a])
        P = np.array(P)
        if len(P) < 8:
            return None
        keep = np.ones(len(P), bool)
        for _ in range(3):                                             # a plane through the bends, outliers dropped
            c0 = P[keep].mean(0); n0 = np.linalg.svd(P[keep] - c0)[2][-1]; dd = np.abs((P - c0) @ n0)
            keep = dd <= max(3 * np.median(dd[keep]) + 1e-9, 0.25 * h)
        c0 = P[keep].mean(0); n0 = np.linalg.svd(P[keep] - c0)[2][-1]
        dm = _unit(D[bmax:bmin + 1].mean(0)); n0 = n0 if n0 @ dm >= 0 else -n0
        if n0 @ dm < math.cos(math.radians(spec.get("max_tilt_deg", 45.0))):   # bends that do not ring the part (a face's
            n0 = dm; info["tilt_limited"] = True                       # folds on one side): the plane across the axis
            c0 = np.median(P[keep], 0)                                 # through their middle
        info.update(widest_station_cm=round(gb[bmax] * 100, 2), narrowest_station_cm=round(gb[bmin] * 100, 2),
                    bends=int(keep.sum()), of=len(P), tilt_deg=round(math.degrees(math.acos(min(1.0, abs(n0 @ dm)))), 1),
                    rms_cm=round(float(np.sqrt(np.mean(((P[keep] - c0) @ n0) ** 2))) * 100, 3))
        info["_zone"] = fm
        return c0, n0, seeds, info
    raise ValueError(f"unknown split kind {spec['at']}")


def _face_graph_components(F, fm):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    ff = np.nonzero(fm)[0]; adj = face_adjacency(F[ff])
    _, cl = connected_components(coo_matrix((np.ones(len(adj)), (adj[:, 0], adj[:, 1])), shape=(len(ff), len(ff))), directed=False)
    return ff, cl


def mound_segments(V, F, lab, k, spec, B, fr, log=print):
    """(L2) MOUNDS on part k (a breast on a chest): the part's skin that faces a direction (spec "facing": front;
    faces turned more than ~70 deg away are not height data) as a height field over the plane across it (grid_cm cells,
    the outermost skin per cell); the field's own smooth course (a normalized Gaussian of smooth_cm over the cells that
    hold skin) is the reference; a mound = the skin standing more than low_cm above it, connected, holding a place
    peak_cm or more above it, of min_area_cm2 or more. Woman2 13a's breasts stand 3.8-3.9 cm above the chest's 6 cm
    course, the realistic male's pectorals 2.5 cm, the stylized female's breasts 2.7 cm (cases/human_l2); the cleavage
    between two breasts usually dips under it, so they come apart (split_at_midplane cuts one mound with a top on each
    side). Returns a list of (face indices, top vertex, info)"""
    from scipy import ndimage
    cm = 0.01; fm = lab == k; vk = np.unique(F[fm])
    d = {"front": fr["front"], "back": -fr["front"], "up": fr["up"], "left": fr["left"]}[spec.get("facing", "front")]
    a1 = fr["left"] if abs(d @ fr["left"]) < 0.9 else fr["front"]; a1 = _unit(a1 - (a1 @ d) * d); a2 = np.cross(d, a1)
    vn = B["vn"]; P = V[vk]; hgt = P @ d; u, w = P @ a1, P @ a2; face = vn[vk] @ d
    data = face >= spec.get("facing_min", 0.35)
    g = spec.get("grid_cm", 1.0) * cm
    if data.sum() < 50:
        return []
    u0, w0 = u[data].min() - 3 * g, w[data].min() - 3 * g
    nc, nr = int((u[data].max() - u0) / g) + 4, int((w[data].max() - w0) / g) + 4
    ci = np.clip(((u - u0) / g).astype(np.int64), 0, nc - 1); ri = np.clip(((w - w0) / g).astype(np.int64), 0, nr - 1)
    cell = ri * nc + ci; s = np.full(nr * nc, -np.inf)
    np.maximum.at(s, cell[data], hgt[data]); have = np.isfinite(s).reshape(nr, nc); S = np.where(have, s.reshape(nr, nc), 0.0)
    sig = spec.get("smooth_cm", 6.0) * cm / g
    Wg = ndimage.gaussian_filter(S, sig, mode="constant") / np.maximum(ndimage.gaussian_filter(have.astype(float), sig, mode="constant"), 1e-9)
    fu, fw = (u - u0) / g - 0.5, (w - w0) / g - 0.5                   # bilinear: the reference under every vertex
    i0 = np.clip(np.floor(fw).astype(np.int64), 0, nr - 2); j0 = np.clip(np.floor(fu).astype(np.int64), 0, nc - 2)
    tw, tu = np.clip(fw - i0, 0, 1), np.clip(fu - j0, 0, 1)
    Wv = (Wg[i0, j0] * (1 - tw) * (1 - tu) + Wg[i0 + 1, j0] * tw * (1 - tu) + Wg[i0, j0 + 1] * (1 - tw) * tu + Wg[i0 + 1, j0 + 1] * tw * tu)
    # where the skin is height data (it faces the direction) and the reference rests on data all round (not at the field's edge)
    cover = ndimage.gaussian_filter(have.astype(float), sig, mode="constant")
    cv = (cover[i0, j0] + cover[i0 + 1, j0 + 1]) / 2
    hv = np.full(len(V), -np.inf)
    hv[vk] = np.where((face >= spec.get("rim_facing_min", 0.0)) & (cv >= spec.get("cover_min", 0.6)), hgt - Wv, -np.inf)
    cand = fm & (hv[F] >= spec.get("low_cm", 0.3) * cm).all(1)
    if not cand.any():
        return []
    ff, cl = _face_graph_components(F, cand); fa = B["fa"]; out = []; peaks = []
    # (L5) a dome, not a plate, on the part's upper side: dome_min = the mound's height over its footprint's radius
    # (sqrt(area / pi)); upper_min = its top's height within the part's own vertical extent. Absent: as L2 made it.
    uz = V[vk] @ fr["up"]; zlo, zhi = float(uz.min()), float(uz.max())
    def shape_ok(pk_cm, ar_cm2, tp):
        if "dome_min" in spec and pk_cm / math.sqrt(max(ar_cm2, 1e-9) / math.pi) < spec["dome_min"]:
            return False
        if "upper_min" in spec and (float(V[tp] @ fr["up"]) - zlo) / max(zhi - zlo, 1e-12) < spec["upper_min"]:
            return False
        return True
    for c in np.unique(cl):
        fc = ff[cl == c]; vc = np.unique(F[fc]); top = vc[np.argmax(hv[vc])]
        area = fa[fc].sum() / cm ** 2; peak = hv[top] / cm; peaks.append(round(float(peak), 2))
        if peak >= spec.get("peak_cm", 2.0) and area >= spec.get("min_area_cm2", 40.0) and spec.get("split_at_midplane"):
            side_ = (V[F[fc]].mean(1) - fr["centre"]) @ fr["left"] > 0   # a mound across the mid-plane with a top on each
            halves = [fc[side_], fc[~side_]]                           # side is two (two breasts close together)
            tops = [np.unique(F[x]) for x in halves]
            if all(len(t) and hv[t].max() / cm >= spec.get("peak_cm", 2.0) and fa[x].sum() / cm ** 2 >= spec.get("min_area_cm2", 40.0) / 2
                   and shape_ok(hv[t].max() / cm, fa[x].sum() / cm ** 2, t[np.argmax(hv[t])]) for x, t in zip(halves, tops)):
                for x, t in zip(halves, tops):
                    out.append((x, int(t[np.argmax(hv[t])]), {"peak_cm": round(float(hv[t].max() / cm), 2), "area_cm2": round(float(fa[x].sum() / cm ** 2), 1),
                                                             "split": "one mound across the mid-plane with a top on each side: cut at the mid-plane",
                                                             "reference": f"normalized Gaussian {spec.get('smooth_cm', 6.0)} cm",
                                                             **({"dome": round(float(hv[t].max() / cm / math.sqrt(fa[x].sum() / cm ** 2 / math.pi)), 3)} if "dome_min" in spec else {})}))
                continue
        if peak >= spec.get("peak_cm", 2.0) and area >= spec.get("min_area_cm2", 40.0) and shape_ok(peak, area, top):
            out.append((fc, int(top), {"peak_cm": round(float(peak), 2), "area_cm2": round(float(area), 1),
                                       **({"dome": round(float(peak / math.sqrt(area / math.pi)), 3)} if "dome_min" in spec else {}),
                                       "reference": f"normalized Gaussian {spec.get('smooth_cm', 6.0)} cm over {int(have.sum())} cells of "
                                                    f"{spec.get('grid_cm', 1.0)} cm (skin facing {spec.get('facing', 'front')} within "
                                                    f"{round(math.degrees(math.acos(spec.get('facing_min', 0.35))))} deg)"}))
    log(f"  mounds on part {k}: {len(out)} kept (peaks {sorted(peaks, reverse=True)[:6]} cm; kept areas {[o[2]['area_cm2'] for o in out]} cm2)")
    return out


def _merge_chains(lab, parts, log=print):
    """(L2) a limb cut in a chain: a protrusion with exactly one child that is itself a protrusion with children of its
    own takes that child in (a bent elbow cut a forearm-with-hand from its upper arm; a forefoot cut where its sections
    met the leg). Leaf children (fingers, toes, ears) never join; a part with two such children (a junction) keeps both"""
    while True:
        kids = {k: [j for j, q in enumerate(parts) if q["parent"] == k and not q.get("_gone")] for k in range(len(parts))}
        hit = None
        for k, p in enumerate(parts):
            if p.get("_gone") or p["kind"] != "protrusion":
                continue
            inner = [j for j in kids[k] if parts[j]["kind"] == "protrusion" and kids[j]]
            if len(inner) == 1:
                hit = (k, inner[0]); break
        if hit is None:
            break
        k, j = hit; lab[lab == j] = k; parts[j]["_gone"] = True
        for q in parts:
            if q["parent"] == j:
                q["parent"] = k
        log(f"  joined a chain: part {j} into part {k} (a limb cut at a bend)")
    keep_ = [k for k, p in enumerate(parts) if not p.get("_gone")]
    remap = -np.ones(len(parts), np.int64); remap[keep_] = np.arange(len(keep_)); out = []
    for k in keep_:
        p = dict(parts[k]); q = p["parent"]
        while q >= 0 and remap[q] < 0:
            q = parts[q]["parent"]
        p["parent"] = int(remap[q]) if q >= 0 else -1; out.append(p)
    return remap[lab], out


def refine_parts(V, F, lab, parts, B, fr, pack, dim, log=print):
    """(L2) a pack's SPLITS and MERGES, after a first naming by its rules (data: the pack's "splits" and "merge"):
    a split cuts every part of a word by a plane (_split_plane) into its tip side, a new part of tip_word, and the rest
    (base_word, else its word); what grew from the part grows from the piece it shares more border with. Merges: a
    part of the same word as its parent joins it (the pieces of one hand), and with "unnamed": a protrusion no rule
    names joins its parent (an ear, a nipple bump: not in the word list). Returns lab, parts (each with its word)"""
    splits = pack.get("splits", []); mg = pack.get("merge", {}); tmpl = pack.get("templates", {}); rules = pack.get("rules", [])
    mounds = pack.get("mounds", [])
    if not splits and not mg and not mounds and not pack.get("features"):
        return lab, parts
    lab = lab.copy(); parts = [dict(p) for p in parts]
    if mg.get("chains"):                                               # a limb cut at a bend: one limb again
        lab, parts = _merge_chains(lab, parts, log)

    def words_now():
        desc = describe(V, F, lab, parts, B, fr)
        for k, p in enumerate(parts):
            c = shape_class(p, desc[k], dim, tmpl); desc[k]["class"] = "body" if c == "tube" and p["parent"] < 0 else c
        _, w, by_ = name_parts(parts, desc, rules, fixed={k: p.get("word") for k, p in enumerate(parts) if p.get("word")}, log=lambda *a: None)
        for k, p in enumerate(parts):                                  # the domain pack's words only: a generic word
            if w.get(k) and not str(by_.get(k, "")).startswith("generic"):   # (body, protrusion) names no anatomy
                p["word"] = w[k]
    def compact():
        nonlocal lab, parts
        keep_ = [k for k, p in enumerate(parts) if not p.get("_gone") and (lab == k).any()]
        remap = -np.ones(len(parts), np.int64); remap[keep_] = np.arange(len(keep_)); out = []
        for k in keep_:
            p = dict(parts[k]); q = p["parent"]
            while q >= 0 and remap[q] < 0:
                q = parts[q]["parent"]
            p["parent"] = int(remap[q]) if q >= 0 else -1; out.append(p)
        lab = remap[lab]; parts = out

    def depth(k):
        d_ = 0
        while parts[k]["parent"] >= 0:
            k = parts[k]["parent"]; d_ += 1
        return d_

    def merge_pass():
        """merges one at a time, the shallowest first (a part no rule names that holds named limbs - a walk that went on
        into the trunk - joins the trunk before what grows from it is named), until none applies"""
        compact()
        for _ in range(len(parts) + 1):
            words_now(); cand = []
            for k, p in enumerate(parts):
                if p["parent"] < 0:
                    continue
                par = parts[p["parent"]]
                same = mg.get("same_word_as_parent") and p.get("word") and p.get("word") == par.get("word")
                unnamed = mg.get("unnamed") and not p.get("word") and p["kind"] in mg.get("unnamed", [])
                if same or unnamed:
                    cand.append((depth(k), k, same))
            if not cand:
                break
            _, k, same = min(cand); p = parts[k]; par = parts[p["parent"]]
            lab[lab == k] = p["parent"]; p["_gone"] = True
            for q in parts:
                if q["parent"] == k:
                    q["parent"] = p["parent"]
            log(f"  merged {'a ' + p['word'] if same else 'an unnamed ' + p['kind']} into its parent ({par.get('word')})")
            compact()

    words_now()
    merge_pass()
    for spec in splits:
        for k in [k for k, p in enumerate(parts) if p.get("word") == spec["word"] and not p.get("_gone")]:
            try:
                res = _split_plane(V, F, lab, parts, k, spec, dim, log)
            except Exception as ex:
                res = None; log(f"  split {spec['word']} (part {k}): failed, {type(ex).__name__}: {ex}")
            if res is None:
                log(f"  split {spec['word']} (part {k}): no {spec['at']} cut found; the part stays whole"); continue
            c0, n0, seeds, info = res
            zone = info.pop("_zone", None)
            if spec.get("recut") and zone is not None:                 # a base recut: the seam between the part and its
                par = parts[k]["parent"]; Cf = V[F].mean(1)              # parent moves to the plane
                side_ = zone & ((Cf - c0) @ n0 < 0); ff, cl = _face_graph_components(F, side_)
                sv = set(int(x) for x in seeds); hold = [c for c in np.unique(cl) if sv & set(np.unique(F[ff[cl == c]]).tolist())]
                mine = np.zeros(len(F), bool); mine[ff[np.isin(cl, hold)]] = True
                before = int((lab == k).sum()); lab[zone & mine] = k; lab[zone & ~mine] = par
                parts[k]["recut"] = {**info, "plane_point_m": [float(x) for x in c0], "plane_normal": [float(x) for x in n0]}
                log(f"  recut {spec['word']}'s base: {before} -> {int((lab == k).sum())} faces; {info}")
                continue
            fm = lab == k; Cf = V[F].mean(1); tipside = fm & ((Cf - c0) @ n0 < 0)
            ff, cl = _face_graph_components(F, tipside)
            sv = set(int(x) for x in seeds); hold = [c for c in np.unique(cl) if sv & set(np.unique(F[ff[cl == c]]).tolist())]
            tf = ff[np.isin(cl, hold)]
            if not len(tf) or len(tf) == fm.sum():
                log(f"  split {spec['word']} (part {k}): the cut leaves one side empty; the part stays whole"); continue
            new = len(parts); lab[tf] = new
            parts.append({"kind": parts[k]["kind"], "parent": k, "tip": parts[k].get("tip", -1), "group": parts[k].get("group"),
                          "file_label": parts[k].get("file_label"), "word": spec["tip_word"],
                          "split": {"from_word": spec["word"], **info, "plane_point_m": [float(x) for x in c0],
                                    "plane_normal": [float(x) for x in n0]}})
            parts[k]["tip"] = -1
            if spec.get("base_word"):
                parts[k]["word"] = spec["base_word"]
            vn, vb = set(np.unique(F[lab == new]).tolist()), set(np.unique(F[lab == k]).tolist())
            for j, q in enumerate(parts):                             # what grew from it: from the piece it touches more
                if q["parent"] == k and j != new:
                    vj = set(np.unique(F[lab == j]).tolist())
                    if len(vj & vn) > len(vj & vb):
                        q["parent"] = new
            log(f"  split {spec['word']} -> {spec['tip_word']} + {parts[k]['word']}: {info}")
    for spec in mounds:                                                # mounds on a word's part (breasts on the torso)
        if dim != 3:
            break
        for k in [k for k, p in enumerate(parts) if p.get("word") == spec["on_word"] and not p.get("_gone")]:
            for fc, top, info in mound_segments(V, F, lab, k, spec, B, fr, log):
                new = len(parts); lab[fc] = new
                parts.append({"kind": "mound", "parent": k, "tip": top, "group": parts[k].get("group"),
                              "file_label": parts[k].get("file_label"), "mound": info})
                if info.get("split"):                                  # (L5) a half cut at the mid-plane: its side is the cut's
                    x = float((V[F[fc]].mean((0, 1)) - fr["centre"]) @ fr["left"])   # (small breasts close together sit
                    parts[-1]["side_of"] = "L" if x > 0 else "R"                    # under the centroid rule's 0.12)
                for j, q in enumerate(parts):                         # what grew from the part and lies on the mound
                    if q["parent"] == k and j != new:
                        vj = set(np.unique(F[lab == j]).tolist()); vn_ = set(np.unique(F[fc]).tolist())
                        if len(vj & vn_) > len(vj & set(np.unique(F[lab == k]).tolist())):
                            q["parent"] = new
    merge_pass()
    for spec in pack.get("features", []):                              # (L4) the features of a word's part (a head's
        if dim != 3:                                                   # ears, eyes, nose, lips: engine/tools/part_features.py)
            break
        lab, parts = _feature_parts(V, F, lab, parts, spec, fr, log)

    return lab, parts


def _feature_parts(V, F, lab, parts, spec, fr, log=print):
    """(L4) a pack's FEATURES on every part of spec["on_word"]: each found feature (part_features.find) becomes a part
    of its word growing from that part, its side by the part's own mid-plane; a separate shell growing from the part
    (an eye's globe set in its socket) joins the feature it lies in. New parts are added after the ones already
    there, so those keep their order (and a fresh build's uids)"""
    sys.path.insert(0, HERE)
    import part_features as PFT
    lab = lab.copy(); parts = [dict(p) for p in parts]; Cf = None
    for k in [k for k, p in enumerate(parts) if p.get("word") == spec["on_word"] and not p.get("_gone")]:
        below = None
        for w_ in spec.get("below_words", []):                         # what the part sits on: its frame's base is the seam
            m = np.isin(lab, [j for j, q in enumerate(parts) if q.get("word") == w_])
            if m.any() and np.intersect1d(np.unique(F[lab == k]), np.unique(F[m])).size:
                below = m; break
        try:
            found, rec = PFT.find(V, F, lab == k, spec, below_fm=below, front=fr["front"], left=fr["left"], log=log)
        except Exception as ex:
            log(f"  features on part {k} ({spec['on_word']}): failed, {type(ex).__name__}: {ex}; the part stays whole"); continue
        parts[k]["features_record"] = rec; first = len(parts)
        for f_ in found:
            new = len(parts); lab[f_["faces"]] = new
            parts.append({"kind": "feature", "parent": k, "tip": -1, "group": parts[k].get("group"), "file_label": parts[k].get("file_label"),
                          "word": f_["word"], "side_of": f_["side"], "class": spec["parts"].get(f_["word"], {}).get("class"),
                          "feature": f_["info"]})
        if len(parts) == first:
            continue
        if Cf is None:
            Cf = V[F].mean(1)
        from scipy.spatial import cKDTree
        mine = np.nonzero(np.isin(lab, [k] + list(range(first, len(parts)))))[0]; T = cKDTree(Cf[mine])
        for j, q in enumerate(parts):                                  # a shell set in a feature joins it (an eye's globe)
            if q.get("kind") == "shell" and q["parent"] == k and not q.get("_gone") and (lab == j).any():
                fj = np.nonzero(lab == j)[0]; c = Cf[fj].mean(0); _, ii = T.query(c, k=min(25, len(mine)))
                own = lab[mine[np.atleast_1d(ii)]]; own = own[own >= first]
                if len(own) * 2 >= np.size(ii):
                    t = int(np.bincount(own - first).argmax()) + first; lab[fj] = t; q["_gone"] = True
                    parts[t]["feature"].setdefault("shells", []).append(round(float(len(fj)), 0))
                    log(f"  a shell ({len(fj)} faces) set in {parts[t]['word']}{'_' + parts[t]['side_of'] if parts[t]['side_of'] else ''} joins it")
        log(f"  features on {spec['on_word']} (part {k}): " + ", ".join(f"{p['word']}{'_' + p['side_of'] if p['side_of'] else ''}" for p in parts[first:]))
    keep_ = [k for k, p in enumerate(parts) if not p.get("_gone")]
    if len(keep_) < len(parts):
        remap = -np.ones(len(parts), np.int64); remap[keep_] = np.arange(len(keep_)); out = []
        for k in keep_:
            p = dict(parts[k]); q = p["parent"]
            while q >= 0 and remap[q] < 0:
                q = parts[q]["parent"]
            p["parent"] = int(remap[q]) if q >= 0 else -1; out.append(p)
        lab = remap[lab]; parts = out
    return lab, parts


# --------------------------------------------------------------------------------------------- part definitions
def _nice(x, lo=0.05):
    """a readable grid step near x (cm): 1, 2, 2.5 or 5 x a power of ten (a 26 m lantern capped at 5 cm made 14.6 M
    grid points)"""
    for e in range(-2, 6):
        for m in (1.0, 2.0, 2.5, 5.0):
            s = m * 10.0 ** e
            if s >= x * 0.8 and s >= lo:
                return float(round(s, 6))
    return 1e5


def shape_class(p, d, dim, tmpl):
    """which template a part gets: flat (a 2-D object's part), plane (a planar facet: a height address in its plane),
    tube (a protrusion longer than wide), sheet (a thin plate), patch (a curved facet, an edge, a corner, a short bump: a
    disc chart on its mean normal), body (a core or a shell: a tube along its longest axis)"""
    if dim == 2:
        return "flat"
    if p["kind"] == "facet" and d.get("normal_flat", 0) >= tmpl.get("plane_flat", 0.995):
        return "plane"
    if p["kind"] in ("facet", "edge", "corner"):
        return "patch"
    if p["kind"] == "feature":                                      # (L4) a part's feature (an ear, an eye): the
        return p.get("class") or "patch"                           # template its pack names, else a disc on its normal
    if d.get("flatness", 1) < tmpl.get("sheet_flatness", 0.12) and d["normal_flat"] < 0.5 and d["extent_cm"][1] > 0:
        return "sheet"
    if p["kind"] == "protrusion":
        return "tube" if d.get("slender", 0) >= tmpl.get("tube_slender", 1.0) else "patch"
    return "body" if d["elong"] >= tmpl.get("body_elong", 1.3) else "patch"


def _perp(vecs, axis):
    """the first of vecs at least 35 deg off axis, made a plain list"""
    for v in vecs:
        if abs(np.dot(_unit(v), axis)) < 0.82:
            return [float(x) for x in v]
    return [float(x) for x in vecs[-1]]


def part_entry(name, uid, par_uid, cls, d, fr, tmpl, sticky=None):
    """one part_frame definition from the shape class's template (the generic pack's "templates" block: steps,
    turn, chart kinds). Positions are landmarks read from the part's own faces at every build (area centroids, the
    seam with its parent), so a remesh or a reshaping moves them with the skin; the one fixed choice, the vector the
    second axis is taken from, is kept from the earlier definition (sticky) so a part's frame does not flip."""
    sel = [{"mask": f"part_{uid}"}]
    up, front = fr["up"], fr["front"]; back = -front
    e = {"what": f"{name}: auto-defined by engine/tools/language.py ({cls} template)", "class": cls,
         "_extent_cm": round(float(max(d.get("extent_cm", [1.0])[0], d.get("length_cm", 0) or 0)), 3),
         "select": sel, "largest_component": True, "measures": {"area_cm2": {"area": [], "what": "surface area of the part"}}}
    st = dict(sticky or {})
    floor = _nice(max(d.get("extent_cm", [1.0])[0], d.get("length_cm", 0) or 0, 1e-3) / tmpl.get("max_cells", 150))
    for key, ax in (("y_vector", d.get("normal")), ("z_vector", d.get("direction")), ("z_vector", d.get("pca_axis"))):
        if key in st and ax is not None and abs(np.dot(_unit(np.asarray(st[key], float)), _unit(np.asarray(ax, float)))) >= 0.82:
            st.pop(key)                                                # a kept choice no longer square enough: chosen again
    if cls in ("flat", "plane"):
        # a flat part (a 2-D object's part, a planar facet): the frame in its plane, origin at its area centroid (in the
        # plane, even for a ring), addresses = the frame's x, y read by a ray along -Z (h+): exact on a plane, and the
        # centroid moves only by the mesh's own error on a remesh (a nearest-point origin hopped 56 mm on a ring)
        size = math.sqrt(max(d["area_cm2"], 1e-6)); step = st.get("step_cm") or max(_nice(size / tmpl.get("disc_cells", 10)), floor)
        nz = np.asarray(d["normal"]) if cls == "plane" else np.array([0, 0, 1.0])
        yv = st.get("y_vector") or _perp([up, back, fr["left"] if fr["dim"] == 3 else [1.0, 0, 0]], nz)
        e["axes_names"] = {"x": "across", "y": "up the part" if abs(np.dot(yv, up)) > 0.5 else "along the part", "z": "out (its normal)"}
        e["landmarks"] = {"centre": {"centroid": {"among": sel}, "source": "area centroid of the part (on its plane)"}}
        e["frame"] = {"origin": "centre", "axes": [["z", {"mean_normal": sel} if cls == "plane" else {"vector": [0, 0, 1]}], ["y", {"vector": yv}]],
                      "why": "Z = the part's normal (a 2-D object: the image's), Y = the object's up (or back) made square to it"}
        e["address"] = {"kind": "height", "up": "z", "sides": ["+"], "step_cm": step}
        e["measures"]["extent"] = {"extent": {"among": sel}, "what": "the part's extent along its frame's axes"}
        e["_sticky"] = {"y_vector": yv, "step_cm": step}
        return e
    if cls in ("patch", "sheet"):
        size = math.sqrt(max(d["area_cm2"], 1e-6)); step = st.get("step_cm") or max(_nice(size / tmpl.get("disc_cells", 10)), floor)
        nz = np.asarray(d["normal"])
        yv = st.get("y_vector") or _perp([up, back, fr["left"]], nz)
        e["axes_names"] = {"x": "across", "y": "up the part" if abs(np.dot(yv, up)) > 0.5 else "along the part", "z": "out (its normal)"}
        e["landmarks"] = {"centroid": {"centroid": {"among": sel}, "source": "area centroid of the part"},
                          "centre": {"closest": {"to": "centroid", "among": sel}, "source": "the point of the part nearest its centroid"}}
        e["frame"] = {"origin": "centre", "axes": [["z", {"mean_normal": sel}], ["y", {"vector": yv}]],
                      "why": "Z = the part's mean normal, Y = the object's up (or back) made square to it"}
        e["address"] = {"kind": "height", "up": "z", "sides": ["+", "-"], "step_cm": step}
        charts = [{"name": "skin" if cls != "sheet" else "upper", "kind": "disc", "axis": "z", "through": "centre", "from": "+",
                   "turn_deg": tmpl.get("turn_deg", 30), "grid": [{"step_cm": step}]}]
        if cls == "sheet":
            charts[0]["region"] = [{"normal_toward": {"dir": {"frame_axis": "z"}}}]
            charts.append({"name": "under", "kind": "disc", "axis": "z", "through": "centre", "from": "-",
                           "turn_deg": tmpl.get("turn_deg", 30), "grid": [{"step_cm": step}],
                           "region": [{"not": {"normal_toward": {"dir": {"frame_axis": "z"}}}}]})
        e["skin"] = {"charts": charts, "why": "a disc chart on the part's normal through its centre: addresses = the frame's x, y "
                                              "where the part is flat, growing along the skin past a 30 deg turn"}
        e["measures"]["extent"] = {"extent": {"among": sel}, "what": "the part's extent along its frame's axes"}
        e["_sticky"] = {"y_vector": yv, "step_cm": step}
        return e
    if cls == "tube":
        L = max(d["length_cm"], 1e-3); r = max(d.get("base_radius_cm", 0.1) or 0.1, 0.02)
        step = st.get("step_cm") or max(_nice(L / tmpl.get("tube_cells", 10)), floor)
        dirv = np.asarray(d["direction"]); zv = st.get("z_vector") or _perp([up, front, fr["left"]], dirv)
        e["axes_names"] = {"x": "across", "y": "along (base to tip)", "z": "out (toward the object's up or front)"}
        psel = [{"mask": f"part_{par_uid}"}]
        e["landmarks"] = {"base": {"seam": [sel, psel], "source": "centroid of the seam with the part it grows from"},
                          "tip": {"farthest": {"from": "base", "among": sel}, "source": "the part's point farthest from its base"},
                          "end_cut": {"lerp": ["base", "tip", 0.7]},
                          "end": {"centroid": {"among": sel + [{"plane": {"through": "end_cut", "normal": {"from": "base", "to": "tip"}}}]},
                                  "source": "area centroid of the part beyond 70 % of the way to the tip (stable where a tip vertex hops)"}}
        e["frame"] = {"origin": "base", "axes": [["y", {"from": "base", "to": "end"}], ["z", {"vector": zv}]],
                      "why": "Y from the base (the seam with its parent) toward the tip end, Z toward the object's up (or front) made square"}
        after = (L * 0.3 + 2 * r) if d.get("taper", 1) == d.get("taper", 1) else L * 0.4
        before = min(r * 0.8, L * 0.3)
        e["address"] = {"kind": "tube", "through": ["base", "end"], "before_cm": round(before, 3), "after_cm": round(after, 3),
                        "blend_cm": round(min(0.5, L / 10), 3), "step_cm": step, "angle_deg": 15}
        e["skin"] = {"charts": [{"name": "skin", "kind": "tube", "through": ["base", "end"], "before_cm": round(before, 3),
                                 "after_cm": round(after, 3), "blend_cm": round(min(0.5, L / 10), 3), "ref": {"fraction": 0.5},
                                 "c_from_deg": 0, "turn_deg": tmpl.get("turn_deg", 30), "grid": [{"step_cm": step}]}],
                     "why": "a tube chart along base -> end: s = the ring (cm along the part, along the skin over its tip), "
                            "c = cm round the ring from the line toward Z"}
        e["measures"]["length_cm"] = {"distance": ["base", "tip"], "what": "base (seam centroid) to tip"}
        e["measures"]["sections"] = {"tube_sections": {"step_cm": step, "rays": 90}, "what": "girth every step along the part"}
        e["_sticky"] = {"z_vector": zv, "step_cm": step}
        return e
    # body: a tube along the part's longest axis, ends at the centroids of its end zones
    ax = st.get("axis") or _pca_axis(d)
    L = d["extent_cm"][0]; step = st.get("step_cm") or max(_nice(L / tmpl.get("tube_cells", 10)), floor)
    zv = st.get("z_vector") or _perp([up, front, fr["left"]], np.asarray(ax))
    e["axes_names"] = {"x": "across", "y": "along its longest axis", "z": "out (toward the object's up or front)"}
    e["landmarks"] = {"far_a": {"extreme": {"dir": {"vector": [-x for x in ax]}, "among": sel}},
                      "far_b": {"extreme": {"dir": {"vector": ax}, "among": sel}},
                      "cut_a": {"lerp": ["far_a", "far_b", 0.12]}, "cut_b": {"lerp": ["far_a", "far_b", 0.88]},
                      "a": {"centroid": {"among": sel + [{"plane": {"through": "cut_a", "normal": {"from": "far_b", "to": "far_a"}}}]},
                            "source": "area centroid of the part's first 12 % along its axis"},
                      "b": {"centroid": {"among": sel + [{"plane": {"through": "cut_b", "normal": {"from": "far_a", "to": "far_b"}}}]},
                            "source": "area centroid of its last 12 %"}}
    e["frame"] = {"origin": "a", "axes": [["y", {"from": "a", "to": "b"}], ["z", {"vector": zv}]],
                  "why": "Y along the part's longest axis (end-zone centroids), Z toward the object's up (or front) made square"}
    ext = round(L * 0.2, 3)
    e["address"] = {"kind": "tube", "through": ["a", "b"], "before_cm": ext, "after_cm": ext, "blend_cm": 1.0, "step_cm": step, "angle_deg": 15}
    e["skin"] = {"charts": [{"name": "skin", "kind": "tube", "through": ["a", "b"], "before_cm": ext, "after_cm": ext, "blend_cm": 1.0,
                             "ref": {"fraction": 0.5}, "c_from_deg": 0, "turn_deg": tmpl.get("turn_deg", 30), "grid": [{"step_cm": step}]}],
                 "why": "a tube chart along the part's longest axis"}
    e["measures"]["extent"] = {"extent": {"among": sel}, "what": "the part's extent along its frame's axes"}
    e["_sticky"] = {"axis": ax, "z_vector": zv, "step_cm": step}
    return e


def _pca_axis(d):
    return [float(x) for x in _unit(np.asarray(d.get("pca_axis", [0, 1.0, 0])))]


def fallback_entry(e, level):
    """when a part's skin chart cannot be laid (an axis that misses a bent part, a seam that is empty): level 1 keeps
    build 09's address kind only; level 2 is a disc on the part's mean normal with a height address"""
    e = json.loads(json.dumps(e))
    if level == 1:
        e.pop("skin", None); e["fallback"] = "no skin chart (it could not be laid on this part): build 09's address kind only"
        return e
    sel = e["select"]
    e["landmarks"] = {"centroid": {"centroid": {"among": sel}}, "centre": {"closest": {"to": "centroid", "among": sel}}}
    yv = e.get("_sticky", {}).get("y_vector") or [0, 0, 1.0]
    e["frame"] = {"origin": "centre", "axes": [["z", {"mean_normal": sel}], ["y", {"vector": [0, 1.0, 0] if abs(yv[2]) > 0.9 else [0, 0, 1.0]}]]}
    ext = max(e.get("_extent_cm", 1.0), 1e-3)
    e["address"] = {"kind": "height", "up": "z", "sides": ["+", "-"], "step_cm": max(e.get("address", {}).get("step_cm", 1.0), _nice(ext / 150))}
    e.pop("skin", None); e.pop("overlays", None)                       # (L2) overlays name the template's landmarks
    e["measures"] = {"area_cm2": {"area": []}}
    e["fallback"] = "a height address on the part's mean normal (its template could not be laid)"
    return e


# ----------------------------------------------------------------------------------------------------- packs
def load_pack(domain):
    """the object kind's language data: engine/packs/<domain>/language.json over engine/packs/generic/language.json
    (segmentation, templates and rules; a domain's blocks replace the generic ones key by key, its rules come first)"""
    g = _jload("engine/packs/generic/language.json"); out = json.loads(json.dumps(g)); files = ["engine/packs/generic/language.json"]
    for r in out.get("rules", []):
        r["_from"] = "generic"
    if domain and domain != "generic":
        path = f"engine/packs/{domain}/language.json"; d = _jload(path); files.append(path)
        for k in ("segmentation", "templates"):
            if k in d:
                merged = dict(out.get(k, {}))
                for kk, vv in d[k].items():
                    merged[kk] = {**merged.get(kk, {}), **vv} if isinstance(vv, dict) and isinstance(merged.get(kk), dict) else vv
                out[k] = merged
        out["rules"] = [{**r, "_from": domain} for r in d.get("rules", [])] + out.get("rules", [])
        for k, v in d.items():
            if k not in ("segmentation", "templates", "rules"):
                out[k] = v
    out["_files"] = files
    return out


# ------------------------------------------------------------------------------------------------- the object
class Obj:
    """one object's language tool: <case>/language/ holds job.json (part_frame's job, plus a "language" block: the
    model, the pack, the ingest options), segmentation.json (the parts: uid, name, kind, parent, how named,
    descriptors, the person's edits), definitions.json (generated part_frame entries), src/model.npz (the ingested
    mesh with the per-face part uid) and the built parts, object.html, index.html"""

    def __init__(self, case_or_job):
        p = _p(case_or_job)
        if p.endswith(".json"):
            self.dir = os.path.dirname(p)
        else:
            self.dir = p if os.path.basename(p.rstrip("/\\")) == "language" else os.path.join(p, "language")
        self.job_path = os.path.join(self.dir, "job.json"); self.seg_path = os.path.join(self.dir, "segmentation.json")
        self.defs_path = os.path.join(self.dir, "definitions.json"); self.model_npz = os.path.join(self.dir, "src", "model.npz")

    def job(self):
        return _jload(self.job_path)

    def seg(self):
        return _jload(self.seg_path) if os.path.exists(self.seg_path) else None


def _pack_sha(f):
    """what in a pack decides the parts: its segmentation, templates and rules (its notes, vocabulary and findings do not);
    (L2) and, when it has them, its splits, mounds, merges and word definitions (each definition's entry read from its file)"""
    d = _jload(f); keys = ["segmentation", "templates", "rules"] + [k for k in ("splits", "mounds", "merge", "definitions", "features") if k in d]
    x = {k: d.get(k) for k in keys}
    for w, pdef in (d.get("definitions") or {}).items():
        path, entry = pdef["entry"].split("#"); x.setdefault("_entries", {})[w] = _jload(path)["parts"].get(entry)
    return hashlib.sha1(json.dumps(x, sort_keys=True).encode()).hexdigest()


def _word_definition(pdef, uid, parts, words, desc, job):
    """(L2) a pack's own part_frame definition for a word (\"entry\": file#name, e.g. the human torso), its named
    inputs bound to the parts of the words it names (masks of their faces; a word with no part binds an empty mask);
    the binding goes into the job's inputs under the definition's own input names"""
    path, name = pdef["entry"].split("#"); e = json.loads(json.dumps(_jload(path)["parts"][name]))
    e["class"] = "definition"; e["definition_from"] = pdef["entry"]
    inputs = job["sources"]["model"]["inputs"]; names_ = set(pdef.get("inputs", {}))

    def ns(x):                                                         # the entry's input names, made the definition's own
        if isinstance(x, dict):                                        # (a head's "below" is the neck, a neck's the torso)
            return {k: (f"{name}.{v}" if k in ("mask", "weight", "point", "input") and isinstance(v, str) and v in names_ else ns(v))
                    for k, v in x.items()}
        return [ns(v) for v in x] if isinstance(x, list) else x
    e = ns(e)
    for iname, b in pdef.get("inputs", {}).items():
        if b.get("self"):
            uids = [uid]
        elif b.get("first"):                                           # the first of the words that has a part
            uids = []
            for w_ in b["words"]:
                uids = [parts[j]["uid"] for j in range(len(parts)) if words.get(j) == w_ and (not b.get("side") or desc[j]["side"] == b["side"])]
                if uids:
                    break
        else:
            uids = [parts[j]["uid"] for j in range(len(parts)) if words.get(j) in b["words"] and (not b.get("side") or desc[j]["side"] == b["side"])]
        spec = {"face_sets": "part_labels", "ids": sorted(int(u) for u in uids)}
        inputs[f"{name}.{iname}"] = spec
    e.setdefault("measures", {}).setdefault("area_cm2", {"area": [], "what": "surface area of the part"})
    return e


def _sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def auto(model, case, pack="generic", name=None, units_m=1.0, up="+z", front="-y", px_m=1e-4, foreground="auto",
         seg_override=None, log=print, only=None):
    """a new object's language tool, end to end: ingest, segment, name, define, build, pages (see the module doc).
    only (build A1): build just these parts (names, or a pack word such as "breast" for breast_L and breast_R); the
    other parts keep their last build and show as stale until `sync`. With the segmentation cache (refresh) a re-run
    after a change to the pack's rules re-segments nothing: iterate on one part, then build all once."""
    O = Obj(case); os.makedirs(os.path.join(O.dir, "src"), exist_ok=True)
    name = name or re.sub(r"[^A-Za-z0-9_]+", "_", os.path.splitext(os.path.basename(model))[0])
    lang = {"model": _rel(model), "pack": pack, "name": name, "units_m": units_m, "up": up, "front": front, "px_m": px_m,
            "foreground": foreground, "segmentation_override": seg_override or {}}
    job = {"_": f"language tool job for {name} (engine/tools/language.py; part_frame.py builds it too). Made "
                f"{datetime.date.today().isoformat()}; kept current by `python engine/tools/language.py sync`.",
           "language": lang, "definitions": _rel(O.defs_path), "out_dir": _rel(O.dir), "index_by": "language",
           "sources": {}, "parts": []}
    _jsave(O.job_path, job)
    return refresh(O, force_segment=True, log=log, only=only)


def _prepare_model(O, job, log):
    L = job["language"]; model = _p(L["model"])
    d = ingest(model, O.model_npz + ".new.npz", L.get("units_m", 1.0), L.get("up", "+z"), L.get("front", "-y"),
               L.get("px_m", 1e-4), L.get("foreground", "auto"), log)
    return d


SEGMENT_CODE = ("segment", "branch_segments", "facet_segments", "_axis_profile", "_Sectioner", "_flare_cut", "_flare_index",
                "_ring_profile", "_merge_tree", "geodesic", "inner_radius", "face_components", "face_adjacency", "mesh_basics",
                "_fill_unlabelled", "_vertex_to_face_labels", "_clean_fragments", "_submesh")


def _segment_cached(O, V, F, dim, seg_cfg, flabels, log):
    """segment() with a cache in <case>/language/src/: keyed by the mesh, the segmentation settings, the file labels and
    the source of the segmentation code itself, so a change to any of them segments afresh (build A1: L2 re-segmented
    whole bodies 31 times, 50.6 tool-min, while tuning rules that run after segmentation). LANGUAGE_NO_CACHE=1: off"""
    import inspect, pickle
    h = hashlib.sha1()
    for x in (np.ascontiguousarray(V, float), np.ascontiguousarray(F, np.int64)):
        h.update(x.tobytes())
    h.update(json.dumps(seg_cfg, sort_keys=True, default=str).encode()); h.update(str(dim).encode())
    for k in sorted(flabels or {}):
        a, nm = flabels[k]; h.update(k.encode()); h.update(np.ascontiguousarray(a).tobytes()); h.update("|".join(nm).encode())
    for nm in SEGMENT_CODE:
        if nm in globals():
            h.update(inspect.getsource(globals()[nm]).encode())
    key = h.hexdigest(); path = os.path.join(O.dir, "src", "_segment_cache.pkl")
    if os.environ.get("LANGUAGE_NO_CACHE") != "1" and os.path.exists(path):
        try:
            with open(path, "rb") as fh:
                c = pickle.load(fh)
            if c.get("key") == key:
                log("  segmentation: cached (mesh, settings and code unchanged)")
                return c["lab"], c["parts"], c["B"]
        except Exception:
            pass
    lab, parts, B = segment(V, F, dim, seg_cfg, flabels, log)
    try:
        with open(path, "wb") as fh:
            pickle.dump({"key": key, "lab": lab, "parts": parts, "B": B}, fh, protocol=4)
    except Exception as ex:
        log(f"  (segmentation cache not written: {ex})")
    return lab, parts, B


def _only_names(only, srec):
    """the part names `only` asks for: a part's name, or a pack word / a name's stem (breast -> breast_L, breast_R)"""
    if not only:
        return None
    want = [x.strip() for x in (only if isinstance(only, (list, tuple)) else str(only).split(",")) if x.strip()]
    out = [p["name"] for p in srec if p["name"] in want or p.get("word") in want or re.sub(r"_(L|R|\d+)$", "", p["name"]) in want]
    if not out:
        raise ValueError(f"--only {want}: no part of this object is called that (parts: {[p['name'] for p in srec][:40]})")
    return out


def refresh(O, force_segment=False, log=print, only=None):
    """(re)make the object's parts from its model: ingest; carry the earlier build's part labels onto the new mesh
    (nearest face; names and identities stay) unless segmenting afresh; segment to find parts that appeared; name the
    new ones by the pack's rules; write definitions and the job; build every part; write the pages"""
    t0 = time.time(); job = O.job(); L = job["language"]; pack = load_pack(L["pack"])
    seg_cfg = json.loads(json.dumps(pack.get("segmentation", {})))
    for k, v in L.get("segmentation_override", {}).items():
        seg_cfg[k] = {**seg_cfg.get(k, {}), **v} if isinstance(v, dict) else v
    d = _prepare_model(O, job, log)
    V, F = d["v"].astype(float), d["f"].astype(np.int64); dim = int(d["dim"])
    flabels = {k[5:]: (d[k], [str(x) for x in d[k + "_names"]]) for k in d if k.startswith("face_") and not k.endswith("_names")}
    old = O.seg(); old_npz = O.model_npz if os.path.exists(O.model_npz) else None
    lab_new, parts_new, B = _segment_cached(O, V, F, dim, seg_cfg, flabels, log)
    fr = object_frame(V, dim, L.get("front", "+x") if dim == 2 else "+x")
    lab_new, parts_new = refine_parts(V, F, lab_new, parts_new, B, fr, pack, dim, log)   # (L2) the pack's splits, mounds, merges
    report = {"model": L["model"], "seconds": None}
    if old and old_npz and not force_segment:
        lab, parts, carried = _carry(O, V, F, lab_new, parts_new, old, B, seg_cfg, log)
    else:
        lab, parts = lab_new, parts_new
        for k, p in enumerate(parts):
            p["uid"] = k + 1
        carried = None
    desc = describe(V, F, lab, parts, B, fr); tmpl = pack.get("templates", {})
    for k, p in enumerate(parts):
        c = shape_class(p, desc[k], dim, tmpl); desc[k]["class"] = "body" if c == "tube" and p["parent"] < 0 else c
    keep = {}
    if old and not force_segment:
        byuid = {q["uid"]: q for q in old["parts"]}
        for k, p in enumerate(parts):
            q = byuid.get(p["uid"])
            if q:
                keep[k] = (q["name"], q.get("word"), q.get("named_by", "earlier build"))
    for e in (old or {}).get("edits", []):
        if e["op"] == "rename":
            for k, p in enumerate(parts):
                if p["uid"] == e["uid"]:
                    keep[k] = (e["name"], keep.get(k, (None, None, None))[1], "renamed by " + e.get("by", "the person"))
    names, words, by = name_parts(parts, desc, pack.get("rules", []), keep, log,
                                  fixed={k: p.get("word") for k, p in enumerate(parts) if p.get("word")})
    # write the mesh with the part uids, the segmentation record, the definitions and the job
    uid_face = np.array([parts[k]["uid"] for k in lab], np.int32)
    z = dict(d); z["part"] = uid_face
    _release_npz()                                                     # an open npz cannot be replaced on Windows
    np.savez_compressed(O.model_npz + ".tmp.npz", **{k: v for k, v in z.items()})
    os.replace(O.model_npz + ".tmp.npz", O.model_npz)
    try:
        os.remove(O.model_npz + ".new.npz")
    except OSError:
        pass
    old_defs = _jload(O.defs_path) if os.path.exists(O.defs_path) else {"parts": {}}
    defs = {"_": f"part definitions for {L['name']}, generated by engine/tools/language.py "
                                                  f"from the {L['pack']} pack's templates; edit through the tool (rename, cut, merge), "
                                                  "never by hand: a rebuild regenerates this file", "convention": {
        "units": "cm", "axes": "per part: Y along the part (tubes) or its up (discs), Z out, X across; right-side parts mirrored",
        "addresses": "<part> skin|upper|under <a>=<cm> <b>=<cm> (skin charts), build 09's h+ / h- / tube kinds, <part> xyz"}, "parts": {}}
    job["sources"] = {"model": {"label": f"{L['name']} ({os.path.basename(L['model'])}; {L['pack']} pack)",
                                "mesh": {"npz": _rel(O.model_npz)}, "units_m": 1.0, "left": "+x",
                                "inputs": {"part_labels": {"npz": _rel(O.model_npz), "key": "part"}}}}
    job["parts"] = []; srec = []; pin_store = {}
    old_by_uid = {q["uid"]: q for q in (old or {}).get("parts", [])}
    for k, p in enumerate(parts):
        nm = names[k]; uid = p["uid"]; par = p["parent"]; puid = parts[par]["uid"] if par >= 0 else 0
        cls = desc[k]["class"]
        prev = old_by_uid.get(uid, {}) if not force_segment else {}; prev_entry = old_defs["parts"].get(prev.get("name", ""), {})
        if prev_entry.get("class") and prev_entry["class"] != cls:      # a part keeps its template, so the addresses in use
            cls = desc[k]["class"] = prev_entry["class"]                # keep resolving (its kind of address stays)
        sticky = prev_entry.get("_sticky") if prev_entry.get("class") == cls else None
        if cls == "body":
            desc[k]["pca_axis"] = _body_axis(V, F, lab == k, fr)
        pdef = (pack.get("definitions") or {}).get(words.get(k) or "")
        if pdef:                                                       # (L2) the pack's own definition for this word
            e = _word_definition(pdef, uid, parts, words, desc, job); cls = desc[k]["class"] = "definition"; e["_uid"] = uid
        else:
            e = part_entry(nm, uid, puid, cls, desc[k], fr, tmpl, sticky); e["_uid"] = uid
        fit = (carried or {}).get("_fits", {}).get(uid); pj = os.path.join(O.dir, prev.get("name", "") + ".json")
        if fit and prev and os.path.exists(pj) and seg_cfg.get("carry_frames", True):
            e, pins = _pin(e, _jload(pj), fit, uid); e["_uid"] = uid
            for lm, pt in pins.items():
                pin_store.setdefault(str(uid), {})[lm] = pt
                job["sources"]["model"]["inputs"][f"pin_{uid}_{lm}"] = {"json": _rel(os.path.join(O.dir, "pins.json")), "path": [str(uid), lm]}
        if prev_entry.get("fallback") and prev_entry.get("class") == cls and prev.get("faces_sha") == _face_sha(lab == k):
            e = prev_entry                                             # the same faces as before: keep what built
        e["_faces_sha"] = _face_sha(lab == k); defs["parts"][nm] = e
        job["sources"]["model"]["inputs"][f"part_{uid}"] = {"face_sets": "part_labels", "ids": [uid]}
        side = desc[k]["side"] if desc[k]["side"] in ("L", "R") else None
        job["parts"].append({"part": nm, "name": nm, "source": "model", **({"side": side} if side else {})})
        srec.append({"uid": uid, "name": nm, "word": words.get(k), "kind": p["kind"], "class": cls, "named_by": by.get(k),
                     "parent": puid, "parent_name": names[par] if par >= 0 else None, "side": desc[k]["side"],
                     "file_label": p.get("file_label"), "faces": int((lab == k).sum()), "faces_sha": _face_sha(lab == k),
                     "descriptors": {kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in desc[k].items()
                                     if kk not in ("centroid", "normal", "base", "tip", "direction")},
                     "centroid_cm": (np.asarray(desc[k]["centroid"]) * 100).round(3).tolist(),
                     **({"cut": p.get("split") or p.get("mound") or p.get("feature")} if (p.get("split") or p.get("mound") or p.get("feature")) else {}),
                     **({"features_found": p["features_record"]} if p.get("features_record") else {}),
                     **({"recut": p["recut"]} if p.get("recut") else {})})
    _jsave(os.path.join(O.dir, "pins.json"), {"_": "carried part frames (engine/tools/language.py _pin): each part's earlier "
               "landmarks moved by the rigid fit of its surviving surface, source frame (metres)", **pin_store})
    if carried:
        carried = {k: v for k, v in carried.items() if k != "_fits"}
        carried["frames_carried"] = sorted(int(u) for u in pin_store)
    _jsave(O.defs_path, defs); _jsave(O.job_path, job)
    seg = {"_": "the parts of this object (engine/tools/language.py): uid = the part's identity across rebuilds; "
                "name = what it is called (pack rule, generic, or the person's); word = the pack's vocabulary word",
           "object": L["name"], "model": L["model"], "model_sha1": _sha1_file(_p(L["model"])), "pack": L["pack"],
           "pack_files": {f: _pack_sha(f) for f in pack["_files"]}, "dim": dim,
           "frame": {"what": "object frame: " + ("x left, y back, z up (metres in the model, cm in the pages)" if dim == 3 else
                                                 "the image plane: x right, y up, z toward the viewer"), "centre_m": fr["centre"].tolist(),
                     "half_m": fr["half"].tolist()},
           "segmentation": seg_cfg, "parts": srec, "edits": (old or {}).get("edits", []),
           "coverage": _coverage(srec, L["pack"], len(F)),
           "updated": datetime.datetime.now().isoformat(timespec="seconds"), "carried": carried}
    _jsave(O.seg_path, seg)
    infos = build_parts(O, only=_only_names(only, srec), log=log)
    write_object_page(O, log=log)
    report["seconds"] = round(time.time() - t0, 1); report["parts"] = len(parts); report["built"] = len(infos)
    if carried:
        report["carried"] = carried
    log(f"  {L['name']}: {len(parts)} parts, built in {report['seconds']} s -> {_rel(os.path.join(O.dir, 'index.html'))}")
    return report


def _coverage(srec, pack, nf):
    """faces in a part (all of them, by construction), and in a part named by the domain pack's vocabulary or by the
    person (rather than a generic word: body, face, protrusion, piece)"""
    dom = [r for r in srec if str(r.get("named_by", "")).startswith(pack + " rule") or str(r.get("named_by", "")).startswith("renamed")]
    return {"faces": int(nf), "faces_in_a_part": int(sum(r["faces"] for r in srec)),
            "faces_named_by_the_pack_or_person": int(sum(r["faces"] for r in dom)), "parts": len(srec), "parts_named_by_the_pack_or_person": len(dom),
            "words": sorted({r["word"] for r in dom if r.get("word")})}


def _kabsch(P, Q, w):
    """the rigid motion (R, t) taking points P onto Q (weights w) and its residual (rms, the source's units)"""
    w = np.asarray(w, float) / np.sum(w); cp, cq = (P * w[:, None]).sum(0), (Q * w[:, None]).sum(0)
    H = ((P - cp) * w[:, None]).T @ (Q - cq); U, S_, Vt = np.linalg.svd(H); dd = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, 1, dd]) @ U.T; t = cq - R @ cp
    rms = float(np.sqrt((w * np.sum((P @ R.T + t - Q) ** 2, 1)).sum()))
    return {"R": R.tolist(), "t": t.tolist(), "rms": rms, "faces": int(len(P))}


def _pin(e, info, fit, uid):
    """a carried part's frame: the earlier build's landmarks and axes moved by the rigid fit of the part's surviving
    surface, so an address keeps naming the same place on what survived (measured landmarks moved 8.5 mm when a
    chipped corner took 20 mm off an arris's length). Returns the entry and its pinned points"""
    R, t = np.asarray(fit["R"]), np.asarray(fit["t"])
    e = json.loads(json.dumps(e)); pins = {}
    for lm, p in info["landmarks_source"].items():
        pins[lm] = (R @ np.asarray(p) + t).tolist()
    e["landmarks"] = {lm: {"point": f"pin_{uid}_{lm}", "source": f"carried: the earlier build's {lm}, moved with the part"} for lm in pins}
    rows = np.asarray(info["frame"]["R_rows_source"]); ax = e["frame"]["axes"]; AX = {"x": 0, "y": 1, "z": 2}
    e["frame"] = {"origin": e["frame"]["origin"], "axes": [[a, {"vector": (R @ rows[AX[a]]).tolist()}] for a, _ in ax],
                  "why": "carried: the earlier build's frame moved by the rigid fit of the part's surviving surface (rms "
                         f"{fit['rms'] * 1000:.3f} mm over {fit['faces']} faces)"}
    e["pinned"] = {"rms_mm": round(fit["rms"] * 1000, 4), "faces": fit["faces"]}
    return e, pins


def _release_npz():
    """close the npz files part_frame keeps open (its read cache), so a model file can be rewritten in this process"""
    pf = sys.modules.get("part_frame")
    if pf is not None:
        cache = pf._load_npz.__defaults__[0]
        for z in cache.values():
            try:
                z.close()
            except Exception:
                pass
        cache.clear()


def _face_sha(m):
    return hashlib.sha1(np.packbits(np.asarray(m, bool)).tobytes()).hexdigest()[:12]


def _body_axis(V, F, fm, fr):
    P = V[np.unique(F[fm])]; X = P - P.mean(0); ev, evec = np.linalg.eigh(X.T @ X); a = evec[:, -1]
    ref = fr["front"] if abs(a @ fr["front"]) > 0.3 else fr["up"]
    return [float(x) for x in (a if a @ ref >= 0 else -a)]


def _carry(O, V, F, lab_new, parts_new, old, B, seg_cfg, log):
    """the earlier build's parts onto the new mesh: each new face takes the uid of the nearest old face (by centroid);
    a new face farther than carry_tol x the object's size from the old surface counts as new material. A part the new
    segmentation finds that is mostly new material (a horn sculpted on) is added with a new uid - a part the new
    segmentation merely cuts differently is not (a re-rasterized drawing "grew" a spurious horn while every new face lay
    on the old surface); a part with no faces left is reported gone"""
    from scipy.spatial import cKDTree
    z = np.load(O.model_npz, allow_pickle=False); Vo, Fo, uo = z["v"].astype(float), z["f"].astype(np.int64), z["part"]
    Co = Vo[Fo].mean(1); Cn = V[F].mean(1); dist, j = cKDTree(Co).query(Cn)
    uid = uo[j].astype(np.int64); size = float(np.linalg.norm(V.max(0) - V.min(0)))
    far = dist > seg_cfg.get("carry_tol", 0.01) * size
    olds = {q["uid"]: q for q in old["parts"]}; next_uid = max(olds) + 1 if olds else 1
    fa = B["fa"]; added = []
    for k, p in enumerate(parts_new):                                  # parts that appeared
        m = lab_new == k
        if p["kind"] in ("core",) or not m.any():
            continue
        u, c = np.unique(uid[m], return_counts=True); main = u[np.argmax(c)]
        overlap = fa[m & (uid == main)].sum() / fa[m].sum()
        host = olds.get(int(main))
        frac_host = fa[m & (uid == main)].sum() / max(fa[uid == main].sum(), 1e-30)
        new_mat = fa[m & far].sum() / fa[m].sum()                     # appeared = mostly new material (far from the old
        if host and new_mat >= 0.5 and frac_host < 0.5 and p["kind"] != host["kind"]:   # surface), not a re-cut of the old
            if fa[m].sum() >= seg_cfg.get("new_part_min", 0.002) * fa.sum():
                uid[m] = next_uid; added.append({"uid": next_uid, "kind": p["kind"], "on": host["name"]}); next_uid += 1
    present = np.unique(uid); gone = [olds[u]["name"] for u in olds if u not in set(present.tolist())]
    lab = np.searchsorted(present, uid)
    parts = []
    for u in present:
        q = olds.get(int(u))
        if q:
            parts.append({"uid": int(u), "kind": q["kind"], "parent": -1, "tip": -1, "_parent_uid": q["parent"], "file_label": q.get("file_label")})
        else:
            a = next(x for x in added if x["uid"] == u)
            host_uid = next(qq["uid"] for qq in old["parts"] if qq["name"] == a["on"])
            parts.append({"uid": int(u), "kind": a["kind"], "parent": -1, "tip": -1, "_parent_uid": host_uid})
    pos = {p["uid"]: i for i, p in enumerate(parts)}
    for p in parts:
        p["parent"] = pos.get(p.pop("_parent_uid", 0), -1)
    for p, q in zip(parts, [olds.get(p["uid"]) for p in parts]):
        if q and q.get("kind") in ("edge", "corner"):
            p["between"] = []
    fits = {}                                                          # each part's motion: the rigid fit of its surviving
    for u in present:                                                  # faces (old centroid -> new centroid, area-weighted)
        m = (uid == u) & ~far
        if m.sum() >= 10:
            fits[int(u)] = _kabsch(Co[j[m]], Cn[m], fa[m])
    carried = {"from_previous_build": True, "faces_far_from_old_surface": int(far.sum()), "_fits": fits,
               "far_share": round(float(fa[far].sum() / fa.sum()), 5), "parts_added": added, "parts_gone": gone,
               "rule": f"nearest old face by centroid; far = more than {seg_cfg.get('carry_tol', 0.01)} x the object's size"}
    log(f"  carried {len(present)} parts onto the new mesh ({far.sum()} faces far from the old surface); "
        f"added {len(added)}, gone {len(gone)}")
    return lab, parts, carried


# ------------------------------------------------------------------------------------------------------ building
def build_parts(O, only=None, log=print):
    """every part (or `only`) through part_frame.build_part; a part whose template cannot be laid falls back (its
    entry is rewritten so the next build takes the same way at once)"""
    sys.path.insert(0, HERE)
    import part_frame as PF
    job = O.job(); defs = _jload(O.defs_path); src = PF.Source("model", job["sources"]["model"]); infos = []; changed = False
    meta = {"path": _rel(O.defs_path)}
    for item, side, name in PF.job_items(job):
        if only and name not in only:
            continue
        entry = defs["parts"][item["part"]]; err = None
        for level in (0, 1, 2):
            e = entry if level == 0 else fallback_entry(entry, level)
            try:
                ee = dict(e); ee["_key"] = item["part"]
                P, A, info, data, ov = PF.build_part(ee, src, side, name, meta, log=lambda *a: None)
                ng, nv = len(data["grid_P"]), info["counts"]["vertices"]
                if level < 2 and ng > max(20000, 5 * nv):              # (L2) a chart whose rings ran away (a head's cap on a
                    raise ValueError(f"the grid ran away: {ng} grid points on {nv} vertices")   # coarse mesh: 404k points)
                break
            except Exception as ex:
                err = f"{type(ex).__name__}: {ex}"
                P = None
        if P is None:
            log(f"  {name}: could not be built ({err})"); continue
        if level:
            defs["parts"][item["part"]] = e; changed = True; info["fallback"] = e["fallback"]; info["fallback_reason"] = err
        if changed:
            _jsave(O.defs_path, defs)
        info["job"] = _rel(O.job_path); info["fingerprint"] = PF.fingerprint(O.job(), item, side)
        PF.write_outputs(O.dir, P, A, info, data, ov); infos.append(info)
        cov = info["skin"]["vertices_with_address"] / info["skin"]["vertices"] if info.get("skin") else \
            info["address"].get("vertices_with_address", 0) / max(info["address"].get("vertices", 1), 1)
        log(f"  {name}: {info['counts']['vertices']} vertices, {len(data['grid_P'])} grid points, {cov * 100:.1f} % addressed"
            + (f" [fallback {level}]" if level else ""))
    return infos


def _palette(n):
    base = [(0.90, 0.36, 0.25), (0.26, 0.56, 0.90), (0.30, 0.74, 0.40), (0.96, 0.70, 0.22), (0.62, 0.40, 0.82),
            (0.20, 0.78, 0.78), (0.94, 0.48, 0.70), (0.58, 0.46, 0.30), (0.66, 0.84, 0.28), (0.12, 0.40, 0.60),
            (0.82, 0.56, 0.46), (0.46, 0.62, 0.22), (0.76, 0.24, 0.46), (0.38, 0.38, 0.78), (0.86, 0.80, 0.36)]
    return [base[i % len(base)] if i < len(base) else tuple(0.25 + 0.6 * ((i * x) % 97) / 97 for x in (37, 53, 71)) for i in range(n)]


def _part_colours(F, uidf, recs):
    """(L2) the palette in part order, but no part takes a colour a part it touches already has (the human torso and
    its foot came out the same red when colours ran by index alone)"""
    base = _palette(15); idx = {r["uid"]: i for i, r in enumerate(recs)}; n = len(recs)
    adj = face_adjacency(F); a, b = uidf[adj[:, 0]], uidf[adj[:, 1]]; m = a != b
    nb = {i: set() for i in range(n)}
    for x, y in set(zip(a[m].tolist(), b[m].tolist())):
        if x in idx and y in idx:
            nb[idx[x]].add(idx[y]); nb[idx[y]].add(idx[x])
    out = [None] * n; extra = _palette(n + 15)[15:]
    for i in range(n):
        used = {out[j] for j in nb[i] if out[j] is not None}
        pick = next((c for k in range(15) for c in [base[(i + k) % 15]] if c not in used), None)
        out[i] = pick if pick is not None else extra[i % max(len(extra), 1)]
    return out


def write_object_page(O, log=print):
    """object.html (the whole object, coloured by part; every part's grid; a click names the part and gives its
    address in that part's own system; a list of parts with links) and index.html"""
    sys.path.insert(0, HERE)
    import part_frame as PF
    job = O.job(); seg = O.seg(); z = np.load(O.model_npz, allow_pickle=False); F = z["f"].astype(np.int64)
    M = page_matrix(seg["dim"]); V = (z["v"].astype(float) * 100) @ M.T
    uidf = z["part"]; recs = seg["parts"]; idx = {r["uid"]: i for i, r in enumerate(recs)}
    vp = np.full(len(V), -1, np.int16)
    for j in range(3):
        vp[F[:, j]] = np.array([idx[u] for u in uidf], np.int16)
    ap = np.zeros((len(V), 2), np.float32); vs = np.full(len(V), -1, np.int8)
    gP, gN, gL, gS, gV = [], [], [], [], []; parts_js = []; cols = _part_colours(F, uidf, recs); lm = {}; meas = {}; off = 0
    for i, r in enumerate(recs):
        f = os.path.join(O.dir, r["name"] + ".npz")
        if not os.path.exists(f):
            parts_js.append({"name": r["name"], "systems": [], "colour": cols[i], "kind": r["kind"], "word": r.get("word")}); continue
        q = np.load(f, allow_pickle=False); info = json.loads(str(q["info"])); fr_ = info["frame"]
        o, R, k = np.array(fr_["origin_source"]), np.array(fr_["R_rows_source"]), fr_["source_units_to_cm"]
        vid = q["vid"]; mine = vp[vid] == i
        ap[vid[mine]] = q["addr_params"][mine]; vs[vid[mine]] = q["addr_side"][mine]
        G = q["grid_P"].astype(float)
        if len(G):
            gP.append(((o + (G / k) @ R) * 100) @ M.T); gN += [str(x) for x in q["grid_names"]]
            gS.append(q["grid_side"]); gV.append(q["grid_level"] if "grid_level" in q.files else np.zeros(len(G), np.int8))
            fl = q["grid_lines"].astype(np.int64); fl = np.where(fl >= 0, fl + off, -1); gL.append(fl); off += len(G)
        parts_js.append({"name": r["name"], "systems": info.get("address_systems") or [], "colour": cols[i], "kind": r["kind"],
                         "word": r.get("word"), "page": r["name"] + ".html", "cls": r.get("class"),
                         "addressed": round(100.0 * float((q["addr_side"] >= 0).mean()), 2)})
        lm[r["name"]] = (np.asarray(r["centroid_cm"]) @ M.T).round(3).tolist(); meas[r["name"]] = info["measures"].get("area_cm2", {"value": None, "unit": "cm2"})
    gP = np.concatenate(gP).astype(np.float32) if gP else np.zeros((0, 3), np.float32)
    gL = np.concatenate([np.array([-1], np.int64)] + gL).astype(np.int32)
    fr0 = object_frame_record(int(seg["dim"]))
    info = {"part": job["language"]["name"], "definition": "(the whole object)", "definitions_file": _rel(O.defs_path), "definition_sha1": "-",
            "side": None, "source": job["sources"]["model"]["label"], "built": datetime.datetime.now().isoformat(timespec="seconds"),
            "units": "cm", "axes": fr0["axes"], "handedness": fr0["handedness"], "frame": fr0["frame"],
            "landmarks_cm": lm, "landmark_definitions": {}, "job": _rel(O.job_path),
            "address": {"kind": "xyz", "syntax": "a vertex is written in its part's own address system (open the part for its grid); "
                                                 f"elsewhere: {job['language']['name']} xyz x= y= z= (object frame, cm)",
                        "vertices_with_address": int((vs >= 0).sum()), "vertices": int(len(V)), "round_trip_tol_cm": 0.05},
            "measures": meas, "counts": {"vertices": int(len(V)), "triangles": int(len(F))}, "skin": None,
            "address_systems": [], "what": f"{job['language']['name']}: every part"}
    data = {"V": V.astype(np.float32), "F": F.astype(np.int32), "vid": np.arange(len(V)), "addr_params": ap, "addr_side": np.full(len(V), -1, np.int8),
            "grid_P": gP, "grid_params": np.zeros((len(gP), 2), np.float32), "grid_side": np.concatenate(gS).astype(np.int8) if gS else np.zeros(0, np.int8),
            "grid_level": np.concatenate(gV).astype(np.int8) if gV else np.zeros(0, np.int8), "grid_names": np.array(gN), "grid_lines": gL}
    extra = {"object": {"vp": PF._b64(vp, "<i2"), "ap": PF._b64(ap, "<f4"), "vs": PF._b64(vs, "i1"), "parts": parts_js, "dim": int(seg["dim"]),
                        "colour": PF._b64(z["colour"], "<f4") if "colour" in z.files else None}}
    _write_html(PF, os.path.join(O.dir, "object.html"), info, data, {}, extra)
    try:
        render_object_png(os.path.join(O.dir, "object.png"), V, F, np.array([idx[u] for u in uidf]), [r["name"] for r in recs], cols,
                          seg["dim"], f"{job['language']['name']} - {len(recs)} parts ({job['language']['pack']} pack)")
    except Exception as ex:
        log(f"  (object.png not drawn: {ex})")
    write_index(O, recs, parts_js)
    log(f"  pages: {_rel(os.path.join(O.dir, 'object.html'))}, index.html ({len(recs)} parts, {len(gP)} grid points)")
    _touch_home(O.dir)


def _touch_home(out_dir):
    """(L3) the Translator's home page, after a view's pages are written (translator_pages.touch; never raises)"""
    try:
        sys.path.insert(0, HERE)
        import translator_pages as TP
        TP.touch(out_dir)
    except Exception as ex:
        print(f"(translator home not written: {ex})", file=sys.stderr)


def object_frame_record(dim):
    """(L3) the object page's frame as it is: page_matrix's rows in the object frame (q_cm = p_m @ M.T * 100);
    3-D: x = the object's own right, y up, z its front, LEFT-handed (a mirror of the object frame x left, y back, z up;
    det -1), which the viewer draws as the object is; 2-D: the picture's plane, right-handed"""
    M = page_matrix(dim)
    if dim == 3:
        axes = {"x": "the model's right", "y": "up", "z": "the model's front"}
        hand = ("left-handed: x = the model's own right, y up, z toward its front (a mirror of the model's own frame, x left, "
                "y back, z up); the viewer draws it as the model is, so the front view shows its right on the screen's left")
    else:
        axes = {"x": "right (as the picture shows it)", "y": "up", "z": "toward you"}
        hand = "right-handed: the picture's plane (x right, y up, z toward you)"
    return {"axes": axes, "handedness": hand,
            "frame": {"origin_source": [0, 0, 0], "R_rows_source": M.tolist(), "source_units_to_cm": 100.0,
                      "to_frame": "q_cm = (p_source - origin_source) @ R_rows_source.T * source_units_to_cm",
                      "det": round(float(np.linalg.det(M)), 6)}}


def render_object_png(path, V, F, flab, names, cols, dim, title):
    """the object coloured by part with every part's name, for agents (who read pictures, not WebGL): 2-D one view,
    3-D four (front, right, back-left above, top); page frame: x right, y up, z toward the front"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sys.path.insert(0, os.path.join(ROOT, "engine", "checks")); sys.path.insert(0, HERE)
    import zbuffer_numba as ZB
    from object_checks import Camera
    mirror = np.linalg.det(page_matrix(dim)) < 0                       # (L2) the page frame is a mirror of the object's (its
    if mirror:                                                         # faces' winding turned and the z-buffer drew the far
        V = V * np.array([-1.0, 1.0, 1.0])                             # side, mirrored): drawn in the object's own handedness
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-30)
    C = np.array(cols + [(0.8, 0.8, 0.8)]); cen = (V.min(0) + V.max(0)) / 2; ext = float(np.ptp(V, axis=0).max())
    views = [("front", (0, 0, -1.0))] if dim == 2 else [("front", (0, 0, -1.0)), ("its right side", (1.0, 0, 0)), ("back left, above", (1.0, -0.8, 1.0)), ("top", (0, -1.0, 0))]
    W = 1100 if dim == 2 else 700
    fig, axs = plt.subplots(1, len(views), figsize=(W / 80 * len(views), W / 80), squeeze=False)
    for ax, (ttl, dv) in zip(axs[0], views):
        if mirror:                                                     # the object's handedness: x = its left, y up, z its front
            dv = {"front": (0, 0, -1.0), "its right side": (1.0, 0, 0), "back left, above": (-1.0, -0.8, 1.0), "top": (0, -1.0, 0)}[ttl]
        dv = _unit(np.asarray(dv, float)); eye = cen - dv * ext * 3; up = (0, 1, 0) if abs(dv[1]) < 0.9 else (0, 0, 1)
        cam = Camera.look_at(eye, cen, W / (ext * 1.1), W, W, up=up, ortho=True); r = ZB.rasterize(V, F, cam); fid = r["face"]
        sh = np.where(fid >= 0, 0.45 + 0.55 * np.abs(fn[np.maximum(fid, 0)] @ dv), 1.0)
        img = C[flab[np.maximum(fid, 0)]] * sh[..., None]; img[fid < 0] = 1.0
        ax.imshow(img); ax.set_axis_off(); ax.set_title(ttl, fontsize=10)
        for k, nm in enumerate(names):
            m = (fid >= 0) & (flab[np.maximum(fid, 0)] == k)
            if m.sum() > 25:
                yy, xx = np.nonzero(m); j = np.argmin((yy - yy.mean()) ** 2 + (xx - xx.mean()) ** 2)
                ax.text(xx[j], yy[j], nm, fontsize=6.5, ha="center", va="center", bbox=dict(fc="white", alpha=0.7, lw=0, pad=0.6))
    fig.suptitle(title, fontsize=12); fig.tight_layout(); fig.savefig(path, dpi=80); plt.close(fig)


def page_matrix(dim):
    """object frame (x left, y back, z up) -> the page frame the viewer reads (x right, y up, z toward the front);
    a 2-D object's frame is already x right, y up"""
    return np.eye(3) if dim == 2 else np.array([[-1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])


def _write_html(PF, path, info, data, overlays, extra):
    V, F = data["V"], data["F"]
    d = {"info": info, "V": PF._b64(V, "<f4"), "F": PF._b64(F, "<u4"), "nV": int(len(V)), "nF": int(len(F)),
         "vid": PF._b64(data["vid"], "<u4"), "ap": PF._b64(np.nan_to_num(data["addr_params"], nan=0), "<f4"), "as": PF._b64(data["addr_side"], "i1"),
         "gP": PF._b64(data["grid_P"], "<f4"), "gprm": PF._b64(data["grid_params"], "<f4"), "gside": PF._b64(data["grid_side"], "i1"),
         "glev": PF._b64(data["grid_level"], "i1"), "systems": [], "gnames": [str(x) for x in data["grid_names"]],
         "glines": PF._b64(data["grid_lines"], "<i4"), "fields": {}, "overlays": overlays, **extra}
    sys.path.insert(0, HERE)
    import translator_pages as TP                                      # (L3) the template filled in one place, with its way around
    TP._write(path, TP.fill_viewer(f"{info['part']} - Translator", json.dumps(d).replace("</", "<" + chr(92) + "/"), path))


def write_index(O, recs, parts_js):
    """the object's list of parts (L3: translator_pages.write_list: names a person would use, a find box, links home
    and to the model's other views)"""
    sys.path.insert(0, HERE)
    import translator_pages as TP
    job = O.job(); seg = O.seg(); L = job["language"]; rows = []; pj_by = {p["name"]: p for p in parts_js}
    for r in recs:
        pj = pj_by.get(r["name"], {}); dsc = r["descriptors"]
        col = "rgb(%d,%d,%d)" % tuple(int(255 * c) for c in pj["colour"]) if pj.get("colour") else None
        rows.append({"name": r["name"], "page": r["name"] + ".html", "spoken": TP.spoken(r["name"], L["pack"]), "colour": col,
                     "find": " ".join([r.get("word") or ""] + TP.also(r.get("word"), L["pack"])),
                     "cells": [TP._E(r.get("word") or "-"), TP._E(f"{r['kind']} / {r.get('class')}"), TP._E(r.get("parent_name") or "-"),
                               f"{dsc.get('area_cm2', 0):.2f}", str(pj.get("addressed", "-")), TP._E(r.get("named_by", ""))]})
    named = sum(r["faces"] for r in recs if r.get("word")); tot = sum(r["faces"] for r in recs)
    car = seg.get("carried") or {}
    sub = (f"{TP._E(job['sources']['model']['label'])}. Pack: {TP._E(L['pack'])}. {len(recs)} parts; "
           f"{named * 100.0 / max(tot, 1):.1f} % of the surface in a part the pack's vocabulary names. "
           f"Updated {seg['updated']}{' (parts carried from the previous build)' if car else ''}.")
    intro = ("Each part has its own frame in cm and an address grid on its skin. Open a part, click dots, copy the picks "
             "into chat. Addresses keep naming the same place after the model changes; the engine rebuilds what changed.")
    TP.write_list(O.dir, L["name"].replace("_", " "), sub, ["word", "kind / template", "grows from", "area cm²", "% vertices addressed", "named by"],
                  rows, intro)


def reindex(O, parts_js=None):
    """(L3) an object's list rewritten without a rebuild: parts_js from its object page (what the page shows)"""
    if parts_js is None:
        sys.path.insert(0, HERE)
        import translator_pages as TP
        parts_js = TP.object_parts(TP.data_block(open(os.path.join(O.dir, "object.html"), encoding="utf-8").read())[0])["parts"]
    write_index(O, O.seg()["parts"], parts_js)


# ------------------------------------------------------------------------------------------------- kept current
def find_jobs():
    """every language job, however deep it sits in cases/ (a generated <...>/language/job.json, or a hand-written job
    that part_frame builds: e.g. cases/woman2/build13/parts_13a4/job.json). Build A1: before, only cases/*/*/job.json
    was looked at, which missed 10 of the 15 jobs (cases/human_l2/<body>/language, build 13's parts and whole views)."""
    import glob
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "cases", "**", "job.json"), recursive=True)):
        try:
            j = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(j, dict) and "definitions" in j and "parts" in j and "sources" in j:
            out.append(p)
    return out


def status(job_path):
    """per part: current | stale (what changed) | missing | legacy (built before fingerprints: compared by its mesh)"""
    sys.path.insert(0, HERE)
    import part_frame as PF
    job = _jload(job_path); out_dir = _p(job["out_dir"]); res = {}
    if "language" in job:
        seg = _jload(os.path.join(out_dir, "segmentation.json")) if os.path.exists(os.path.join(out_dir, "segmentation.json")) else None
        L = job["language"]
        if seg is None:
            return {"_object": "never built"}
        why = []
        if seg.get("model_sha1") != _sha1_file(_p(L["model"])):
            why.append("model changed")
        for f, h in seg.get("pack_files", {}).items():
            if not os.path.exists(_p(f)) or _pack_sha(f) != h:
                why.append(f"{f} changed")
        if why:
            return {"_object": "stale: " + "; ".join(why)}
    for item, side, name in PF.job_items(job):
        jf = os.path.join(out_dir, name + ".json")
        if not os.path.exists(jf):
            res[name] = "missing"; continue
        info = json.load(open(jf, encoding="utf-8")); fp = info.get("fingerprint")
        try:
            now = PF.fingerprint(job, item, side)
        except Exception as ex:
            res[name] = f"stale: cannot read its inputs ({ex})"; continue
        if fp is None:
            mesh = now["files"].get(os.path.relpath(_p(PF.mesh_path(job["sources"][item["source"]]["mesh"])), ROOT).replace(os.sep, "/"))
            res[name] = "legacy (current by its mesh)" if info.get("source_files", {}).get("mesh") == mesh else "stale: mesh changed"
            continue
        diff = [k for k in ("tool", "entry", "source") if fp.get(k) != now.get(k)]
        diff += [f for f in set(fp["files"]) | set(now["files"]) if fp["files"].get(f) != now["files"].get(f)]
        res[name] = "current" if not diff else "stale: " + ", ".join(diff)
    return res


def sync(job_path=None, log=print):
    """rebuild exactly what is stale, for one job or every job; returns what was done"""
    jobs = [job_path] if job_path else find_jobs(); done = {}
    for jp in jobs:
        jp = _p(jp)
        with _Lock(jp) as ok:
            if not ok:
                done[_rel(jp)] = "skipped (another sync holds it)"; continue
            try:
                done[_rel(jp)] = _sync_one(jp, log)
            except Exception as ex:                                    # the old build stays; the failure is said
                done[_rel(jp)] = f"FAILED, the previous build stays: {type(ex).__name__}: {ex}"; log(f"sync {_rel(jp)}: {done[_rel(jp)]}")
            try:                                                       # (L3) pages made with an older viewer: re-templated
                sys.path.insert(0, HERE)
                import translator_pages as TP
                d = os.path.dirname(jp); _, sha = TP.template()
                if any(f.endswith(".html") and f != "index.html" and TP.page_stamp(os.path.join(d, f)) != sha for f in os.listdir(d)):
                    TP.pages([d], only_stale=True, log=lambda *a: None); done[_rel(jp)] = {"was": done[_rel(jp)], "pages": "re-templated"}
            except Exception as ex:
                log(f"sync {_rel(jp)}: pages not re-templated ({type(ex).__name__}: {ex})")
    _touch_home(None)
    return done


def _sync_one(jp, log):
    if True:
        if True:
            st = status(jp); job = _jload(jp)
            if "language" in job and st.get("_object", "").startswith(("stale", "never")):
                log(f"sync {_rel(jp)}: {st['_object']}")
                return refresh(Obj(jp), force_segment=st["_object"].startswith("never"), log=log)
            stale = [n for n, s in st.items() if not n.startswith("_") and s.startswith(("stale", "missing"))]
            if not stale:
                return "current"
            log(f"sync {_rel(jp)}: rebuilding {', '.join(stale)}")
            if "language" in job:
                build_parts(Obj(jp), only=stale, log=log); write_object_page(Obj(jp), log=log)
            else:
                sys.path.insert(0, HERE)
                import part_frame as PF
                PF.build(jp, only=stale, log=log); _reindex_plain(PF, jp)
            return {"rebuilt": stale}


def _reindex_plain(PF, jp):
    job = _jload(jp); out = _p(job["out_dir"]); infos = []
    for item, side, name in PF.job_items(job):
        f = os.path.join(out, name + ".json")
        if os.path.exists(f):
            infos.append(json.load(open(f, encoding="utf-8")))
    PF.write_index(out, infos)


def reindex_plain(jp):
    """(L3) a hand-written job's list rewritten from its parts' .json (no rebuild)"""
    sys.path.insert(0, HERE)
    import part_frame as PF
    _reindex_plain(PF, _p(jp))


class _Lock:
    """one sync per job at a time (a lock file with the holder's PID; a dead holder's lock is taken over)"""

    def __init__(self, job_path):
        self.path = os.path.join(os.path.dirname(job_path), ".sync.lock"); self.mine = False

    def __enter__(self):
        for _ in range(600):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, str(os.getpid()).encode()); os.close(fd)
                self.mine = True; return True
            except FileExistsError:
                try:
                    pid = int(open(self.path).read().strip() or 0)
                except Exception:
                    pid = 0
                if not _alive(pid):
                    try:
                        os.remove(self.path)
                    except OSError:
                        pass
                    continue
                time.sleep(0.5)
        return False

    def __exit__(self, *a):
        if self.mine:
            try:
                os.remove(self.path)
            except OSError:
                pass


def _alive(pid):
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not h:
            return False
        code = ctypes.c_ulong(); ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code)); ctypes.windll.kernel32.CloseHandle(h)
        return code.value == 259
    try:
        os.kill(pid, 0); return True
    except OSError:
        return False


def watched_files(job_path):
    """the files a job is made from (its model, sources, inputs, definitions, a followed pack's pack.json)"""
    sys.path.insert(0, HERE)
    import part_frame as PF
    job = _jload(job_path); fs = set()
    if "language" in job:
        fs.add(_p(job["language"]["model"]))
        fs |= {_p(f) for f in load_pack(job["language"]["pack"])["_files"]}
        return fs
    fs.add(_p(job["definitions"]))
    for item, side, name in PF.job_items(job):
        try:
            fs |= {_p(f) for f in PF.part_files(job, item, side)}
        except Exception:
            pass
    return fs


def _strings(d):
    if isinstance(d, str):
        yield d
    elif isinstance(d, dict):
        for v in d.values():
            yield from _strings(v)
    elif isinstance(d, list):
        for v in d:
            yield from _strings(v)


def notify(paths, wait=False, jobs=None):
    """called by the engine's writers after they write (loop/pack_io.Pack.save, loop/recipe.py): every job that names
    a written file, or a file under a written folder (a pack version a job follows included), gets a sync in the
    background (detached; its log: sync.log in the job's folder). Cheap - it only reads the job files and compares
    paths - and a no-op when no job names what was written. Never raises."""
    try:
        if isinstance(paths, str):
            paths = [paths]
        wp = [os.path.normcase(os.path.abspath(_p(p))).rstrip("\\/") for p in paths]; hit = []
        for jp in (jobs or find_jobs()):
            try:
                job = json.load(open(jp, encoding="utf-8"))
            except Exception:
                continue
            for st in _strings({k: v for k, v in job.items() if k != "_"}):
                if not re.search(r"[/\\]|\.(npz|json|ply|obj|stl|png|jpg|glb|blend)$", st):
                    continue
                q = os.path.normcase(os.path.abspath(_p(st.split("{")[0]))).rstrip("\\/")
                if any(q == w or q.startswith(w + os.sep) or w.startswith(q + os.sep) for w in wp):
                    hit.append(jp); break
        for jp in hit:
            log_f = open(os.path.join(os.path.dirname(jp), "sync.log"), "a")
            cmd = [sys.executable, os.path.join(HERE, "language.py"), "sync", jp]
            if wait:
                subprocess.run(cmd, stdout=log_f, stderr=log_f, cwd=ROOT)
            else:
                flags = (0x00000008 | 0x00000200) if os.name == "nt" else 0          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                subprocess.Popen(cmd, stdout=log_f, stderr=log_f, cwd=ROOT, creationflags=flags, close_fds=True)
        return [_rel(j) for j in hit]
    except Exception as ex:                                            # a writer is never broken by this
        print(f"(language.notify: {ex})", file=sys.stderr)
        return []


def ensure_current(npz_path, log=lambda *a: None):
    """part_frame.resolve calls this: if the part's job says anything it is made from changed, sync that job first"""
    info = json.loads(str(np.load(npz_path, allow_pickle=False)["info"]))
    jp = info.get("job")
    if not jp or not os.path.exists(_p(jp)):
        return "no job"
    st = status(_p(jp)); name = info["part"]
    if st.get("_object", "").startswith("stale") or str(st.get(name, "")).startswith(("stale", "missing")):
        print(f"(language: {name} was stale - {st.get('_object') or st.get(name)}; syncing {jp} first)", file=sys.stderr)
        sync(_p(jp), log=lambda *a: print(*a, file=sys.stderr))
        return "synced"
    return "current"


def watch(every=5.0, log=print):
    """sync every language job whenever what it is made from changes, until stopped (Ctrl+C)"""
    log(f"watching {len(find_jobs())} jobs every {every} s (Ctrl+C to stop)")
    last = {}
    while True:
        for jp in find_jobs():
            try:
                sig = tuple(sorted((f, os.path.getmtime(f) if os.path.exists(f) else 0) for f in watched_files(jp)))
            except Exception:
                continue
            if last.get(jp) != sig:
                if jp in last:
                    log(f"{datetime.datetime.now():%H:%M:%S} change in {_rel(jp)}"); log(json.dumps(sync(jp, log=log)))
                last[jp] = sig
        time.sleep(every)


# --------------------------------------------------------------------------------------------- the person's edits
def rename(job_or_case, old, new, by="the person"):
    """a part's name, kept for good (an edit in segmentation.json; the part's files move to the new name)"""
    O = Obj(job_or_case); seg = O.seg(); r = next(p for p in seg["parts"] if p["name"] == old)
    new = re.sub(r"[^A-Za-z0-9_]+", "_", new).strip("_")
    if any(p["name"] == new for p in seg["parts"]):
        raise ValueError(f"a part is already called {new}")
    seg["edits"].append({"op": "rename", "uid": r["uid"], "name": new, "was": old, "by": by,
                         "when": datetime.datetime.now().isoformat(timespec="seconds")})
    r["name"] = new; r["named_by"] = "renamed by " + by; _jsave(O.seg_path, seg)
    for ext in (".json", ".npz", ".html", ".png"):
        try:
            os.remove(os.path.join(O.dir, old + ext))
        except OSError:
            pass
    return _rebuild_from_seg(O)


def cut(job_or_case, part, lines, new_name, by="the person"):
    """split a part along the plane through picked places (pasted address lines: a ring or patch of picks gives the
    plane through them; a line of picks, or two, the plane holding that line and the part's mean normal): the side away
    from the part's parent (or the smaller side) becomes NEW_NAME, recorded as an edit and kept across rebuilds"""
    O = Obj(job_or_case); seg = O.seg(); r = next(p for p in seg["parts"] if p["name"] == part)
    pts = np.array([x["object_cm"] for x in resolve(O.dir, lines) if x.get("object_cm") is not None]) / 100.0
    if len(pts) < 2:
        raise ValueError("need at least two places that resolve")
    with np.load(O.model_npz, allow_pickle=False) as zz:
        z = {k: zz[k] for k in zz.files}
    V = z["v"].astype(float); F = z["f"].astype(np.int64); uidf = z["part"].copy()
    c = pts.mean(0); sv = np.linalg.svd(pts - c)
    if len(pts) >= 3 and sv[1][1] > 0.05 * sv[1][0]:                   # a ring or a patch of picks: the plane through them
        n = sv[2][-1]
    else:                                                              # a line of picks: the plane holding it and the part's normal
        fm0 = uidf == r["uid"]; fn0 = np.cross(V[F[fm0, 1]] - V[F[fm0, 0]], V[F[fm0, 2]] - V[F[fm0, 0]]).sum(0)
        line = sv[2][0] if len(pts) >= 3 else _unit(pts[1] - pts[0]); n = _unit(np.cross(line, _unit(fn0)))
    fm = uidf == r["uid"]; side = (V[F[fm]].mean(1) - c) @ n > 0
    par_c = next((np.asarray(p["centroid_cm"]) / 100 for p in seg["parts"] if p["uid"] == r["parent"]), None)
    pos_is_new = ((par_c - c) @ n < 0) if par_c is not None else (side.sum() < (~side).sum())
    new_uid = max(p["uid"] for p in seg["parts"]) + 1; ff = np.nonzero(fm)[0]
    uidf[ff[side == pos_is_new]] = new_uid; z["part"] = uidf
    _release_npz(); np.savez_compressed(O.model_npz, **z)
    seg["parts"].append({**r, "uid": new_uid, "name": new_name, "word": None, "named_by": "cut by " + by, "parent": r["uid"],
                         "parent_name": r["name"], "faces": int((uidf == new_uid).sum())})
    seg["edits"].append({"op": "cut", "uid": r["uid"], "new_uid": new_uid, "name": new_name, "plane_point_m": c.tolist(),
                         "plane_normal": n.tolist(), "by": by, "when": datetime.datetime.now().isoformat(timespec="seconds"),
                         "picked": list(lines)})
    _jsave(O.seg_path, seg)
    return _rebuild_from_seg(O)


def merge(job_or_case, keep, gone, by="the person"):
    """join part GONE into part KEEP"""
    O = Obj(job_or_case); seg = O.seg(); a = next(p for p in seg["parts"] if p["name"] == keep); b = next(p for p in seg["parts"] if p["name"] == gone)
    with np.load(O.model_npz, allow_pickle=False) as zz:
        z = {k: zz[k] for k in zz.files}
    z["part"] = np.where(z["part"] == b["uid"], a["uid"], z["part"])
    _release_npz(); np.savez_compressed(O.model_npz, **z)
    for p in seg["parts"]:
        if p["parent"] == b["uid"]:
            p["parent"] = a["uid"]
    seg["parts"] = [p for p in seg["parts"] if p["uid"] != b["uid"]]
    seg["edits"].append({"op": "merge", "uid": a["uid"], "gone_uid": b["uid"], "gone": gone, "by": by,
                         "when": datetime.datetime.now().isoformat(timespec="seconds")})
    _jsave(O.seg_path, seg)
    for ext in (".json", ".npz", ".html", ".png"):
        try:
            os.remove(os.path.join(O.dir, gone + ext))
        except OSError:
            pass
    return _rebuild_from_seg(O)


def _rebuild_from_seg(O, log=print):
    """after an edit: the parts as segmentation.json and the mesh's part uids now say (no re-segmentation)"""
    job = O.job(); seg = O.seg(); L = job["language"]; pack = load_pack(L["pack"]); tmpl = pack.get("templates", {})
    z = np.load(O.model_npz, allow_pickle=False); V = z["v"].astype(float); F = z["f"].astype(np.int64); dim = int(z["dim"])
    uids = [p["uid"] for p in seg["parts"]]; pos = {u: i for i, u in enumerate(uids)}
    lab = np.array([pos[u] for u in z["part"]]); B = mesh_basics(V, F)
    parts = [{"uid": p["uid"], "kind": p["kind"], "parent": pos.get(p["parent"], -1), "tip": -1} for p in seg["parts"]]
    fr = object_frame(V, dim, L.get("front", "+x") if dim == 2 else "+x"); desc = describe(V, F, lab, parts, B, fr)
    old_defs = _jload(O.defs_path); defs = {k: v for k, v in old_defs.items() if k != "parts"}; defs["parts"] = {}
    old_job_inputs = dict(job["sources"]["model"]["inputs"])
    job["sources"]["model"]["inputs"] = {"part_labels": {"npz": _rel(O.model_npz), "key": "part"}}; job["parts"] = []
    by_old = {v.get("_uid"): (k, v) for k, v in old_defs["parts"].items()}
    for k, (p, r) in enumerate(zip(parts, seg["parts"])):
        cls = shape_class(p, desc[k], dim, tmpl)
        if cls == "tube" and p["parent"] < 0:
            cls = "body"
        if cls == "body":
            desc[k]["pca_axis"] = _body_axis(V, F, lab == k, fr)
        prev = by_old.get(r["uid"], (None, {}))[1]
        if prev.get("class") and prev["class"] != cls and r["name"] in old_defs["parts"]:
            cls = prev["class"]
        fsha = _face_sha(lab == k)
        if prev and prev.get("_faces_sha") == fsha:                      # untouched by the edit: its entry (and frame) stays
            e = prev
            for inp, spec in old_job_inputs.items():
                if inp.startswith(f"pin_{r['uid']}_"):
                    job["sources"]["model"]["inputs"][inp] = spec
        else:
            e = part_entry(r["name"], r["uid"], seg["parts"][p["parent"]]["uid"] if p["parent"] >= 0 else 0, cls, desc[k], fr, tmpl,
                           prev.get("_sticky") if prev.get("class") == cls else None)
        pdef = (pack.get("definitions") or {}).get(r.get("word") or "")
        if pdef:                                                       # (L2) a word's own definition: its inputs bound again
            wd = {j: q.get("word") for j, q in enumerate(seg["parts"])}
            e2 = _word_definition(pdef, r["uid"], parts, wd, desc, job)
            if e.get("class") != "definition":
                e = e2; cls = "definition"
        e["_uid"] = r["uid"]; e["_faces_sha"] = fsha; defs["parts"][r["name"]] = e; r["class"] = cls; r["faces"] = int((lab == k).sum()); r["faces_sha"] = _face_sha(lab == k)
        r["parent_name"] = seg["parts"][p["parent"]]["name"] if p["parent"] >= 0 else None
        job["sources"]["model"]["inputs"][f"part_{r['uid']}"] = {"face_sets": "part_labels", "ids": [r["uid"]]}
        side = desc[k]["side"] if desc[k]["side"] in ("L", "R") else None
        job["parts"].append({"part": r["name"], "name": r["name"], "source": "model", **({"side": side} if side else {})})
    _jsave(O.defs_path, defs); _jsave(O.job_path, job); seg["updated"] = datetime.datetime.now().isoformat(timespec="seconds"); _jsave(O.seg_path, seg)
    build_parts(O, log=log); write_object_page(O, log=log)
    return {"parts": len(parts)}


# ------------------------------------------------------------------------------------------------------- resolve
def resolve(dir_or_job, lines):
    """address lines naming any part of the object (pasted from object.html or a part's page) -> each place in its
    part's frame and in the object frame (cm); `<object> xyz` lines name the nearest point of the whole object"""
    sys.path.insert(0, HERE)
    import part_frame as PF
    O = Obj(dir_or_job); job = O.job(); objname = job.get("language", {}).get("name"); out = []
    for ln in lines:
        part, kind, kv = PF.parse_address(ln)
        if part == objname and kind == "xyz":                         # the object page's frame (page_matrix)
            z = np.load(O.model_npz, allow_pickle=False); M = page_matrix(int(z["dim"])); V = z["v"].astype(float) * 100; F = z["f"].astype(np.int64)
            Q, _ = PF.closest_points(V, F, (np.array([[kv["x"], kv["y"], kv["z"]]]) @ M))
            out.append({"address": ln.strip(), "object_cm": Q[0].tolist(), "page_cm": (Q[0] @ M.T).tolist(), "part": None}); continue
        f = os.path.join(O.dir, part + ".npz")
        if not os.path.exists(f):
            out.append({"address": ln.strip(), "error": f"no part {part} in {_rel(O.dir)}"}); continue
        r = PF.resolve(f, [ln])[0]
        r["object_cm"] = (np.asarray(r["source"]) * 100).tolist() if r.get("source") and np.isfinite(r["source"]).all() else None
        r["part"] = part; out.append(r)
    return out


# ------------------------------------------------------------------------------------------------- change tests
def compare(old_dir, new_dir, only=None):
    """what survives a change: for every part in both builds, every grid address of the OLD build resolved on the NEW
    build, against where it was (source frame, mm): p50 / p99 / max shift and how many miss; parts kept, gone, added"""
    sys.path.insert(0, HERE)
    import part_frame as PF
    so, sn = _jload(os.path.join(old_dir, "segmentation.json")), _jload(os.path.join(new_dir, "segmentation.json"))
    no, nn = {p["name"] for p in so["parts"]}, {p["name"] for p in sn["parts"]}; out = {"parts": {}}
    for name in sorted(no & nn):
        if only and name not in only:
            continue
        fo, fnw = os.path.join(old_dir, name + ".npz"), os.path.join(new_dir, name + ".npz")
        if not (os.path.exists(fo) and os.path.exists(fnw)):
            continue
        q = np.load(fo, allow_pickle=False); info = json.loads(str(q["info"])); fr = info["frame"]
        o, R, k = np.array(fr["origin_source"]), np.array(fr["R_rows_source"]), fr["source_units_to_cm"]
        names = [str(x) for x in q["grid_names"]]; P0 = o + (q["grid_P"].astype(float) / k) @ R
        if not names:
            continue
        try:
            res = PF.resolve(fnw, names, current=False); P1 = np.array([r["source"] for r in res], float)
        except ValueError as ex:                                       # the new build reads another kind of address
            out["parts"][name] = {"grid_addresses": len(names), "missed": len(names), "shift_mm": {"p50": None, "p99": None, "max": None},
                                  "over_1mm": 0, "error": str(ex)}
            continue
        d = np.linalg.norm(P1 - P0, axis=1) * 1000; ok = np.isfinite(d)
        out["parts"][name] = {"grid_addresses": len(names), "missed": int((~ok).sum()),
                              "shift_mm": {"p50": round(float(np.median(d[ok])), 3) if ok.any() else None,
                                           "p99": round(float(np.percentile(d[ok], 99)), 3) if ok.any() else None,
                                           "max": round(float(d[ok].max()), 3) if ok.any() else None},
                              "over_1mm": int((d[ok] > 1).sum())}
    allp = [v for v in out["parts"].values() if v["shift_mm"]["p99"] is not None]
    D = np.concatenate([[v["shift_mm"]["p50"]] for v in allp]) if allp else np.zeros(0)
    out.update(kept=sorted(no & nn), gone=sorted(no - nn), added=sorted(nn - no),
               addresses=int(sum(v["grid_addresses"] for v in allp)), missed=int(sum(v["missed"] for v in allp)),
               over_1mm=int(sum(v["over_1mm"] for v in allp)), unreadable_parts=[k for k, v in out["parts"].items() if v.get("error")], worst_part_p99_mm=max((v["shift_mm"]["p99"] or 0) for v in allp) if allp else None)
    return out


def change_test(case, new_model, work, overrides=None, log=print):
    """a model change, end to end, on a copy: the case's language folder is copied to WORK, the copy's job is pointed at
    NEW_MODEL, `sync` brings it current the way the engine does on any change (carry the parts, rebuild what is
    stale), and compare() measures what survived"""
    import shutil
    O = Obj(case); w = os.path.join(_p(work), "language")
    if os.path.exists(w):
        shutil.rmtree(w)
    shutil.copytree(O.dir, w, ignore=shutil.ignore_patterns(".sync.lock", "sync.log"))
    job = _jload(os.path.join(w, "job.json")); old_dir = O.dir
    job["language"]["model"] = _rel(_p(new_model)); job["language"].update(overrides or {}); job["definitions"] = _rel(os.path.join(w, "definitions.json")); job["out_dir"] = _rel(w)
    job["sources"]["model"]["mesh"]["npz"] = _rel(os.path.join(w, "src", "model.npz"))
    job["sources"]["model"]["inputs"]["part_labels"]["npz"] = _rel(os.path.join(w, "src", "model.npz"))
    _jsave(os.path.join(w, "job.json"), job)
    for f in os.listdir(w):                                            # the copy's parts name the copy's job
        if f.endswith(".json") and f not in ("job.json", "segmentation.json", "definitions.json"):
            d = _jload(os.path.join(w, f)); d["job"] = _rel(os.path.join(w, "job.json")); _jsave(os.path.join(w, f), d)
    t0 = time.time(); st = status(os.path.join(w, "job.json")); done = sync(os.path.join(w, "job.json"), log=log)
    r = compare(old_dir, w); r["status_before_sync"] = st.get("_object"); r["sync_seconds"] = round(time.time() - t0, 1)
    r["carried"] = _jload(os.path.join(w, "segmentation.json")).get("carried"); r["new_model"] = _rel(_p(new_model))
    return r


# ---------------------------------------------------------------------------------------------------------- proof
def _sdf_mesh(fn, lo, hi, vox):
    """a planted shape: the zero set of a signed distance field (negative inside), marching cubes on a lattice offset
    off the shape's planes"""
    from skimage import measure
    ax = [np.arange(lo[i], hi[i] + 1e-9, vox) + 0.37 * vox for i in range(3)]
    X, Y, Z = np.meshgrid(*ax, indexing="ij"); d = fn(np.stack([X, Y, Z], -1))
    v, f, _, _ = measure.marching_cubes(d, 0.0, spacing=(vox, vox, vox)); v += np.array([a[0] for a in ax])
    return v, f.astype(np.int64)


def _rbox(p, b, r):
    q = np.abs(p) - (np.asarray(b) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - r


def _write_ply(path, V, F):
    with open(path, "w") as fh:
        fh.write(f"ply\nformat ascii 1.0\nelement vertex {len(V)}\nproperty float x\nproperty float y\nproperty float z\n"
                 f"element face {len(F)}\nproperty list uchar int vertex_indices\nend_header\n")
        np.savetxt(fh, V, fmt="%.7f"); np.savetxt(fh, np.c_[np.full(len(F), 3), F], fmt="%d")


def _caps(P, a, b, ra, rb):
    pa, ba = P - a, b - a; h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - h[..., None] * ba, axis=-1) - (ra + (rb - ra) * h)


PROVE_SECTIONS = {"facets": "facets", "creature": "creature", "2d": "2d", "current": "current",
                  "generic": "facets", "masonry": "current"}                # a pack name runs the sections that use it


def _prove_sections(only):
    if not only:
        return ["facets", "creature", "2d", "current"]
    want = []
    for x in (only if isinstance(only, (list, tuple)) else str(only).split(",")):
        x = x.strip().lower()
        if x not in PROVE_SECTIONS:
            raise ValueError(f"prove --only: '{x}' is none of {sorted(PROVE_SECTIONS)}")
        for sct in ([PROVE_SECTIONS[x]] + (["2d"] if x == "creature" and "2d" not in want else [])):
            if sct not in want:
                want.append(sct)
    return want


def prove(log=print, work=None, only=None):
    """Planted objects with known parts (A28: once, at the tool's making; a few minutes):
    1. FACETS: a rounded box (12 x 8 x 5 cm, arris radius 4 mm) with a pocket (6 x 3 x 1.5 cm) in its top: 11 facets
       (6 faces, the pocket's floor and 4 walls), each facet's normal on its analytic axis, each outer face's area = the
       flat face plus the fillet band within facet_deg (closed form) within 3 %, every face in a part, at least 12
       edges between two facets at right angles, the generic words name the faces by their normals;
    2. BRANCHES: a planted creature (an ellipsoid body; 4 legs with 3 claws each; a head with 2 horns; a tapering
       tail) as one smooth field; the truth = the primitive nearest each face: claws, horns, the tail and the legs are
       found (best IoU >= 0.5) and named by the creature pack's words;
    3. 2-D: a drawn image (an oval body, 4 legs with 2 claws each): legs and claws found and named;
    4. KEPT CURRENT: a language job on the planted box is current once made; a changed model (another tessellation)
       makes it stale; part_frame.resolve on one of its parts brings it current by itself (rebuilt: its fingerprint
       changes), names and a person's rename stay, the same addresses land within 0.5 mm; notify() on the model's path
       finds the job, on a path no job reads none.
    (Build L2's human pack is proven on real bodies, cases/human_l2; a planted capsule figure was not segmented as one:
    engine/packs/human/findings.md, Translator.)
    only (build A1): run some sections - "facets", "creature" (with "2d"), "2d", "current", or a pack's name
    (generic = facets, creature = creature + 2d, masonry = current), e.g. `prove --only creature` while tuning a pack."""
    import tempfile, shutil
    sys.path.insert(0, HERE)
    import part_frame as PF
    ok = True

    def chk(name, cond, msg):
        nonlocal ok; ok &= bool(cond); log(f"  {'PASS' if cond else 'FAIL'} {name}: {msg}")
    quiet = lambda *a: None
    work = work or tempfile.mkdtemp(prefix="language_prove_")
    want = _prove_sections(only)
    log(f"prove: {', '.join(want)}")
    Lb, Wb, Hb, r = 0.12, 0.08, 0.05, 0.004; PLb, PWb, PD, pr = 0.06, 0.03, 0.015, 0.003
    box = lambda P: np.maximum(_rbox(P, (Lb / 2, Wb / 2, Hb / 2), r), -_rbox(P - np.array([0, 0, Hb / 2]), (PLb / 2, PWb / 2, PD), pr))
    cpack = load_pack("creature")
    # 1. facets (the generic pack)
    if "facets" in want:
        V, F = _sdf_mesh(box, (-0.065, -0.045, -0.03), (0.065, 0.045, 0.03), 0.001)      # 4 voxels across a fillet (at 2 it is a chamfer)
        pack = load_pack("generic"); seg = json.loads(json.dumps(pack["segmentation"])); seg["methods"] = ["facets"]
        lab, parts, B = segment(V, F, 3, seg, None, quiet); fr = object_frame(V, 3); desc = describe(V, F, lab, parts, B, fr)
        names, words, by = name_parts(parts, desc, pack["rules"])
        fac = [k for k, p in enumerate(parts) if p["kind"] == "facet"]
        chk("facets: count", len(fac) == 11, f"{len(fac)} facets (6 faces, the pocket's floor and 4 walls = 11)")
        band = r * math.sin(math.radians(seg["facets"]["facet_deg"]))       # the fillet's share within facet_deg of a face
        side = {0: (Wb, Hb), 1: (Lb, Hb), 2: (Lb, Wb)}
        errs, nerr = [], []
        for k in fac:
            n = np.asarray(desc[k]["normal"]); a = int(np.argmax(np.abs(n))); nerr.append(math.degrees(math.acos(min(1.0, abs(n[a])))))
            c = np.asarray(desc[k]["centroid"]); half = (Lb / 2, Wb / 2, Hb / 2)[a]
            if abs(abs(c[a]) - half) < 0.001 and not (a == 2 and c[2] > 0):    # an outer face (the top is less the pocket)
                u, v = side[a]; t = (u - 2 * r + 2 * band) * (v - 2 * r + 2 * band); errs.append(abs(desc[k]["area_cm2"] / 1e4 - t) / t)
        chk("facets: normals on their axes", max(nerr) < 2.0, f"max {max(nerr):.2f} deg off the analytic axis over {len(fac)} facets")
        chk("facets: areas = flat face + fillet band", len(errs) == 5 and max(errs) < 0.03,
            f"{len(errs)} outer faces, max error {max(errs) * 100:.2f} % (closed form: flat face + {band * 1000:.2f} mm band per side)")
        chk("facets: every face in a part", (lab >= 0).all() and len(lab) == len(F), f"{len(F)} faces, {len(parts)} parts")
        square = [k for k, p in enumerate(parts) if p["kind"] == "edge" and len(p["between"]) == 2
                  and abs(np.dot(desc[p["between"][0]]["normal"], desc[p["between"][1]]["normal"])) < 0.2]
        chk("facets: edges between faces at right angles", len(square) >= 12, f"{len(square)}, e.g. {[names[k] for k in square[:2]]}")
        fnames = sorted(nm for nm in names.values() if nm.startswith("face"))
        stems = {re.sub(r"_\d+$", "", x) for x in fnames}
        chk("facets: generic words by normal", {"face_top", "face_bottom", "face_front", "face_back", "face_left", "face_right"} <= stems
            and len(fnames) == 11, f"{fnames} (the pocket's floor and walls share the words of the faces they look like)")
    # 2. the planted creature (the creature pack)
    if "creature" in want:
        prims = {"body": lambda P: np.linalg.norm((P - [0, 0, 0.08]) / [0.035, 0.07, 0.035], axis=-1) * 0.035 - 0.035,
                 "head": lambda P: np.linalg.norm(P - [0, -0.078, 0.105], axis=-1) - 0.022,
                 "tail": lambda P: _caps(P, np.array([0, 0.06, 0.08]), np.array([0, 0.17, 0.10]), 0.012, 0.002),
                 "horn_L": lambda P: _caps(P, np.array([0.01, -0.078, 0.12]), np.array([0.02, -0.078, 0.16]), 0.006, 0.0005),
                 "horn_R": lambda P: _caps(P, np.array([-0.01, -0.078, 0.12]), np.array([-0.02, -0.078, 0.16]), 0.006, 0.0005)}
        for i, (x, y) in enumerate([(0.025, -0.04), (-0.025, -0.04), (0.025, 0.04), (-0.025, 0.04)]):
            prims[f"leg{i}"] = (lambda x, y: lambda P: _caps(P, np.array([x, y, 0.07]), np.array([x, y, 0.015]), 0.009, 0.008))(x, y)
            for j, dx in enumerate((-0.008, 0.0, 0.008)):
                prims[f"claw{i}{j}"] = (lambda x, y, dx: lambda P: _caps(P, np.array([x + dx, y - 0.006, 0.010]),
                                                                         np.array([x + 1.6 * dx, y - 0.026, 0.004]), 0.0025, 0.0003))(x, y, dx)

        def crea(P):
            d = None
            for fn_ in prims.values():
                v = fn_(P); d = v if d is None else -np.logaddexp(-d / 0.0015, -v / 0.0015) * 0.0015     # a smooth union
            return d
        V, F = _sdf_mesh(crea, (-0.06, -0.12, 0.0), (0.06, 0.19, 0.17), 0.0015)
        Cf = V[F].mean(1); pn = list(prims); tl = np.stack([prims[n_](Cf) for n_ in pn]).argmin(0)
        lab, parts, B = segment(V, F, 3, cpack["segmentation"], None, quiet)
        fr = object_frame(V, 3); desc = describe(V, F, lab, parts, B, fr)
        for k, p in enumerate(parts):
            c = shape_class(p, desc[k], 3, cpack["templates"]); desc[k]["class"] = "body" if c == "tube" and p["parent"] < 0 else c
        nm, wd, _ = name_parts(parts, desc, cpack["rules"]); fa = B["fa"]; found = {}
        for t, tn in enumerate(pn):
            if tn in ("body", "head"):
                continue
            mt = tl == t; best = (0.0, None)
            for k in range(len(parts)):
                mk = lab == k; u = fa[mt | mk].sum(); iou = fa[mt & mk].sum() / u if u else 0.0
                if iou > best[0]:
                    best = (iou, k)
            found[tn] = (best[0], wd.get(best[1]), nm.get(best[1]))
        claws = [found[t] for t in found if t.startswith("claw")]; horns = [found["horn_L"], found["horn_R"]]
        legs = [found[f"leg{i}"] for i in range(4)]
        chk("creature: claws found", sum(1 for c in claws if c[0] >= 0.5) >= 11,
            f"{sum(1 for c in claws if c[0] >= 0.5)} of 12 at IoU >= 0.5 (IoU {min(c[0] for c in claws):.2f}-{max(c[0] for c in claws):.2f})")
        chk("creature: claws named", sum(1 for c in claws if c[1] == "claw") >= 11, f"{sum(1 for c in claws if c[1] == 'claw')} of 12 named claw, e.g. {claws[0][2]}")
        chk("creature: horns found and named", all(h[0] >= 0.5 and h[1] == "horn" for h in horns), f"{[(round(h[0], 2), h[2]) for h in horns]}")
        chk("creature: tail found and named", found["tail"][0] >= 0.5 and found["tail"][1] == "tail", f"IoU {found['tail'][0]:.2f}, named {found['tail'][2]}")
        chk("creature: legs found and named", sum(1 for x in legs if x[0] >= 0.5 and x[1] == "leg") >= 4, f"{[(round(x[0], 2), x[2]) for x in legs]}")
    # 3. 2-D: a drawn object (the creature pack)
    if "2d" in want:
        from PIL import Image, ImageDraw
        im = Image.new("L", (900, 700), 255); dr = ImageDraw.Draw(im); dr.ellipse((250, 150, 650, 400), fill=0)
        for x in (300, 400, 500, 590):
            dr.rectangle((x - 18, 350, x + 18, 560), fill=0)
            for dx in (-14, 14):
                dr.polygon([(x + dx - 9, 555), (x + dx + 9, 555), (x + 2.2 * dx, 612)], fill=0)
        p2 = os.path.join(work, "drawn.png"); im.save(p2)
        d2 = ingest(p2, os.path.join(work, "drawn.npz"), log=quiet); V2, F2 = d2["v"], d2["f"].astype(np.int64)
        lab2, parts2, B2 = segment(V2, F2, 2, cpack["segmentation"], None, quiet); fr2 = object_frame(V2, 2, "+x")
        desc2 = describe(V2, F2, lab2, parts2, B2, fr2)
        for k in range(len(parts2)):
            desc2[k]["class"] = "flat"
        nm2, wd2, _ = name_parts(parts2, desc2, cpack["rules"])
        nclaw = sum(1 for w in wd2.values() if w == "claw"); nleg = sum(1 for w in wd2.values() if w == "leg")
        chk("2-D: legs and claws", nclaw >= 7 and nleg >= 4, f"{nleg} legs, {nclaw} claws (drawn: 4 legs, 8 claws)")
    # 4. kept current (the masonry pack)
    if "current" in want:
        case = os.path.join(work, "boxcase"); m1 = os.path.join(work, "box_a.ply"); m2 = os.path.join(work, "box_b.ply")
        Va, Fa = _sdf_mesh(box, (-0.065, -0.045, -0.03), (0.065, 0.045, 0.03), 0.002); _write_ply(m1, Va, Fa)
        Vb, Fb = _sdf_mesh(box, (-0.065, -0.045, -0.03), (0.065, 0.045, 0.03), 0.0016); _write_ply(m2, Vb, Fb)
        model = os.path.join(work, "box.ply"); shutil.copy(m1, model)
        auto(model, case, "masonry", "box", log=quiet); O = Obj(case); jp = O.job_path
        st = status(jp); chk("current once made", all(v == "current" for v in st.values()), f"{len(st)} parts current")
        first = O.seg()["parts"][0]["name"]; rename(case, first, "my_face", by="the prove")
        names_a = {p["uid"]: p["name"] for p in O.seg()["parts"]}
        part = next(p["name"] for p in O.seg()["parts"] if p["class"] == "plane" and p["name"] != "my_face")
        q0 = np.load(os.path.join(O.dir, part + ".npz")); addrs = [str(x) for x in q0["grid_names"]][:60]
        inf0 = json.loads(str(q0["info"])); fr0 = inf0["frame"]
        P0 = np.array(fr0["origin_source"]) + (q0["grid_P"][:60].astype(float) / fr0["source_units_to_cm"]) @ np.array(fr0["R_rows_source"])
        fp0 = inf0["fingerprint"]; q0.close()
        shutil.copy(m2, model); st2 = status(jp)
        chk("a changed model makes it stale", st2.get("_object", "").startswith("stale"), st2.get("_object", ""))
        res = PF.resolve(os.path.join(O.dir, part + ".npz"), addrs)          # current=True: brings the part current first
        inf1 = json.loads(str(np.load(os.path.join(O.dir, part + ".npz"))["info"])); st3 = status(jp)
        chk("resolve brought it current by itself", inf1["fingerprint"] != fp0 and "_object" not in st3 and all(v == "current" for v in st3.values()),
            "rebuilt (its fingerprint changed); every part current")
        names_b = {p["uid"]: p["name"] for p in O.seg()["parts"]}
        chk("names and the person's rename stay", names_a == names_b and "my_face" in names_b.values(), f"{len(names_b)} names, my_face kept")
        P1 = np.array([x["source"] for x in res], float); dd = np.linalg.norm(P1 - P0, axis=1) * 1000
        chk("the same addresses land on the same places", np.isfinite(dd).mean() > 0.95 and np.nanmax(dd) < 0.5,
            f"{int(np.isfinite(dd).sum())} of {len(dd)} resolve, max shift {np.nanmax(dd):.3f} mm (2.0 -> 1.6 mm tessellation)")
        hit = notify([model], wait=True, jobs=[jp]); miss = notify([os.path.join(work, "nothing_reads_this.npz")], jobs=[jp])
        chk("notify finds the job that reads a written file", len(hit) >= 1 and miss == [], f"hit {hit}, miss {miss}")
    log("PROVE " + ("PASS" if ok else "FAIL") + f" (work folder {work})")
    return ok


# ------------------------------------------------------------------------------------------------------------ regress
REGRESS_SPEC = "cases/woman2/translator_regress.json"
_VOLATILE = ("built", "seconds", "job", "files")


def _picks_lines(md_path):
    """the pasted lines of a picks file: '<n>. <part> <kind> a=.. b=..   | grid point at (..)' (the whole line, so
    resolve() can also say how far it lands from where it was picked)"""
    txt = open(_p(md_path), encoding="utf-8").read()
    return [m.group(1).strip() for m in re.finditer(r"^\s*\d+\.\s+(\S+ \S+ .*=.*)$", txt, re.M)]


def _cmp_part(a_npz, b_npz):
    A, B = np.load(a_npz), np.load(b_npz)
    worst, bad = 0.0, []
    for k in sorted(set(A.files) | set(B.files)):
        if k == "info":
            ia, ib = json.loads(str(A[k])), json.loads(str(B[k]))
            for kk in sorted(set(ia) | set(ib)):
                if kk not in _VOLATILE and json.dumps(ia.get(kk), sort_keys=True) != json.dumps(ib.get(kk), sort_keys=True):
                    bad.append("info." + kk)
            continue
        if k not in A.files or k not in B.files:
            bad.append(k + " (one side only)"); continue
        x, y = A[k], B[k]
        if x.shape != y.shape:
            bad.append(f"{k} shape {x.shape} vs {y.shape}"); continue
        if x.dtype.kind in "fc":
            same_nan = np.array_equal(np.isnan(x), np.isnan(y))
            d = float(np.nanmax(np.abs(x - y))) if x.size and np.isfinite(x).any() else 0.0
            worst = max(worst, d)
            if not same_nan or d > 1e-9:
                bad.append(f"{k} max {d:.3g}")
        elif not np.array_equal(x, y):
            bad.append(k)
    return bad, worst


def regress(spec_path=REGRESS_SPEC, update=False, jobs=True, picks=True, only=None, log=print):
    """The Translator's guarantees, checked (build A1). A spec file names hand-made jobs and pasted picks files:
      jobs   every part of each job rebuilt into a temporary folder and compared with the stored build, array by
             array (floats within 1e-9 cm, everything else exact; the info record without its time stamps);
      picks  every pasted line of each picks file resolved on the parts it was picked on (current=False: the stored
             build) and compared with the stored baseline: the same lines miss, the rest land within 1 micron.
    update=True writes the picks baseline from this run (do it once, when the baseline is known good, and say why).
    only: a substring; just the jobs / picks files whose path holds it."""
    import tempfile, shutil
    sys.path.insert(0, HERE)
    import part_frame as PF
    spec = _jload(_p(spec_path)); t0 = time.time(); rep = {"spec": spec_path, "jobs": {}, "picks": {}}; ok = True
    if jobs:
        for jp in spec.get("jobs", []):
            if only and only not in jp:
                continue
            job = _jload(_p(jp)); tmp = tempfile.mkdtemp(prefix="regress_"); tj0 = time.time()
            try:
                tj = dict(job); tj["out_dir"] = tmp; tj["index_by"] = "regress"
                tjp = os.path.join(tmp, "job.json"); _jsave(tjp, tj)
                PF.build(tjp, log=lambda *a: None)
                res = {}
                for item, side, name in PF.job_items(job):
                    stored = os.path.join(_p(job["out_dir"]), name + ".npz")
                    if not os.path.exists(stored):
                        res[name] = "not stored"; ok = False; continue
                    bad, worst = _cmp_part(stored, os.path.join(tmp, name + ".npz"))
                    res[name] = ("identical" + (f" (floats within {worst:.1g} cm)" if worst else "")) if not bad else "DIFFERS: " + ", ".join(bad[:6])
                    ok &= not bad
                res["_seconds"] = round(time.time() - tj0, 1)
                rep["jobs"][jp] = res; log(f"  {jp}: " + json.dumps(res))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    if picks:
        bpath = _p(spec["baseline"]); base = _jload(bpath) if os.path.exists(bpath) else {}
        new = {}
        for pk in spec.get("picks", []):
            if only and only not in pk["file"]:
                continue
            lines = _picks_lines(pk["file"]); by_part = {}
            for ln in lines:
                by_part.setdefault(ln.split()[0], []).append(ln)
            got = {}
            for part, lns in by_part.items():
                for ln, r in zip(lns, PF.resolve(os.path.join(_p(pk["parts"]), part + ".npz"), lns, current=False)):
                    got[ln] = r["source"]
            new[pk["file"]] = got
            if update:
                rep["picks"][pk["file"]] = f"{len(got)} lines, baseline written"; continue
            old = base.get(pk["file"], {})
            miss_now = {k for k, v in got.items() if not np.isfinite(np.array(v, float)).all()}
            miss_old = {k for k, v in old.items() if not np.isfinite(np.array(v, float)).all()}
            common = [k for k in got if k in old and k not in miss_now and k not in miss_old]
            d = [float(np.linalg.norm(np.array(got[k]) - np.array(old[k]))) for k in common]
            r = {"lines": len(got), "in_baseline": len(old), "missing_from_baseline": len(set(got) - set(old)),
                 "misses_now": len(miss_now), "misses_in_baseline": len(miss_old), "same_misses": miss_now == miss_old,
                 "max_shift_mm": round(max(d) * 1000, 6) if d else None}
            r["PASS"] = bool(r["same_misses"] and not r["missing_from_baseline"] and len(old) == len(got) and (not d or max(d) <= 1e-6))
            ok &= r["PASS"]; rep["picks"][pk["file"]] = r; log(f"  {pk['file']}: " + json.dumps(r))
        if update:
            _jsave(bpath, {"_": "the Translator's regression baseline (engine/tools/language.py regress): where each pasted line "
                                "resolved (source metres) on the parts it was picked on", "made": datetime.datetime.now().isoformat(timespec="seconds"),
                           **{k: v for k, v in base.items() if k not in new and k not in ("_", "made")}, **new})
    rep["seconds"] = round(time.time() - t0, 1); rep["PASS"] = bool(ok)
    log("REGRESS " + ("PASS" if ok else "FAIL") + f" in {rep['seconds']} s")
    return rep


# ------------------------------------------------------------------------------------------------------------ CLI
def _arg(a, k, default=None, cast=str):
    return cast(a[a.index(k) + 1]) if k in a else default


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd = a[0] if a else "prove"
    if cmd == "auto":
        seg_over = json.loads(_arg(a, "--seg", "{}"))
        r = auto(a[1], _arg(a, "--case"), _arg(a, "--pack", "generic"), _arg(a, "--name"), _arg(a, "--units-m", 1.0, float),
                 _arg(a, "--up", "+z"), _arg(a, "--front", "-y"), _arg(a, "--px-m", 1e-4, float), _arg(a, "--foreground", "auto"), seg_over,
                 only=_arg(a, "--only"))
        print(json.dumps(r, indent=1, default=str))
        if "--open" in a:                                              # (L3) any OS: the model's whole view (else its list)
            sys.path.insert(0, HERE)
            import translator_pages as TP
            d = Obj(_arg(a, "--case")).dir; pg = os.path.join(d, "object.html")
            TP.open_page(pg if os.path.exists(pg) else os.path.join(d, "index.html"))
    elif cmd in ("home", "open", "pages"):                             # (L3) translator_pages
        sys.path.insert(0, HERE)
        import translator_pages as TP
        home = _arg(a, "--home"); rest = []; skip = False
        for i, x in enumerate(a[1:]):
            if skip:
                skip = False; continue
            if x == "--home":
                skip = True; continue
            if not x.startswith("--"):
                rest.append(x)
        if cmd == "home":
            p, nm, nv = TP.write_home(home); print(json.dumps({"home": p, "url": TP._url(p), "models": nm, "views": nv}))
        elif cmd == "pages":
            print(json.dumps(TP.pages(rest or None, home, only_stale="--stale" in a)))
        else:
            try:
                pg, what = TP.find(" ".join(rest), home)
            except ValueError as ex:
                print(json.dumps({"error": str(ex)})); sys.exit(1)
            TP.write_home(home); r = {**TP.where(pg, home), "what": what}
            if "--print" not in a:
                r["opened"] = bool(TP.open_page(pg))
            print(json.dumps(r))
    elif cmd == "sync":
        print(json.dumps(sync(a[1] if len(a) > 1 else None), indent=1, default=str))
    elif cmd == "status":
        for jp in (a[1:] or find_jobs()):
            print(_rel(jp), json.dumps(status(jp), indent=1))
    elif cmd == "watch":
        watch(_arg(a, "--every", 5.0, float))
    elif cmd == "rename":
        print(rename(a[1], a[2], a[3]))
    elif cmd == "cut":
        print(cut(a[1], a[2], a[4:], a[3]))
    elif cmd == "merge":
        print(merge(a[1], a[2], a[3]))
    elif cmd == "resolve":
        lines = [ln for x in a[2:] for ln in x.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        for r in resolve(a[1], lines):
            print(json.dumps(r))
    elif cmd == "change-test":
        ov = {kv.split("=")[0]: json.loads(kv.split("=", 1)[1]) for kv in a[a.index("--set") + 1].split(",")} if "--set" in a else None
        r = change_test(a[1], a[2], _arg(a, "--work"), ov)
        print(json.dumps({k: v for k, v in r.items() if k != "parts"}, indent=1, default=str))
        if "--out" in a:
            _jsave(_arg(a, "--out"), r)
    elif cmd == "compare":
        print(json.dumps(compare(a[1], a[2]), indent=1))
    elif cmd == "notify":
        print(notify(a[1:], wait="--wait" in a))
    elif cmd == "prove":
        sys.exit(0 if prove(only=_arg(a, "--only")) else 1)
    elif cmd == "regress":
        sp = a[1] if len(a) > 1 and not a[1].startswith("--") else REGRESS_SPEC
        r = regress(sp, update="--update" in a, jobs="--picks-only" not in a, picks="--jobs-only" not in a, only=_arg(a, "--only"))
        if "--out" in a:
            _jsave(_arg(a, "--out"), r)
        sys.exit(0 if r["PASS"] else 1)
    else:
        print(__doc__)
