"""blueprint_setup.py - place orthographic reference images ("blueprints") around a model, aligned by LANDMARKS.

Why it exists (woman2 Stage 4, 2026-10-19).  The person supplied front / side / back / close-up images of a body and
asked to "center them on the same x,y coordinates, and use them to give you form references. This is the cheaper
version of handing you a 3d model."  Nothing in the toolkit placed a set of views around a model by evidence:
`cases/woman2/bl_ref_plane.py` places ONE photo through a fitted camera.  Under A29 a view is aligned from evidence it
shares with the model (landmark heights, a midline) and never by fitting the outline it will be compared on, or the
comparison hides exactly the difference it is meant to show.

What it does
  1. masks each image's subject against its plain backdrop (CIE76 dE from the backdrop fitted by `backdrop_mask`;
     a fixed threshold, no GrabCut: GrabCut closed the thin arm-to-torso gaps of a clean studio image);
  2. evaluates named landmark RULES on the image mask (or picked image points), and the SAME rules on the model's own
     orthographic silhouette in the same view (model points are projected 3-D points);
  3. fits, per image, the vertical scale and offset (z = Z0 - s * row) by weighted least squares over the landmark
     heights, and the horizontal offset from a centre rule; square pixels (one scale per image);
  4. writes a placement JSON: for each image the world corners of its plane, the view, the scale (mm/px), the
     landmark residuals (mm) - a large residual says the image differs in build there, not that the fit failed;
  5. in Blender (`build_planes`), makes one textured plane per image in a collection, behind the model as seen from
     that image's camera, visible only from its own side (backface culling).

Views (model frame: x = subject LEFT, y = BACK, z = UP; image u to the right, v down):
  front  camera at -y looking +y   u = +x      back   camera at +y looking -y   u = -x
  left   camera at +x looking -x   u = +y      right  camera at -x looking +x   u = -y
  ("left" = the camera on the subject's left side: she faces image-left.)

Landmark rules (each landmark: {"name", "rule", "sd_mm", ...}; rules may refer to earlier landmarks of the same image):
  point          a named point: image px from "points_px" / model 3-D from "model_points" (projected)
  mean_points    the mean height of several named points
  top_at_frac    the silhouette's top row at columns centre +- frac * (half the widest row above landmark `below`)
  min_width_row  the row of minimum width of the run that contains the centre column, between two landmarks
  extreme_u      the row of the most extreme column (min or max u) of the silhouette between two landmarks
  row_frac       a helper row (search bands only; "use": false): top + frac * (bottom - top) of the mask's rows
Centre rules: "midline" = mean of the centre-run mid columns between two landmarks (front/back), "run_mid_at" = the
mid column of the centre run at a landmark row (sides: the waist section's centre).

Usage
  python blueprint_setup.py fit CONFIG.json OUT_placement.json      (CPU; also writes OUT_dir/<image>_mask.png)
  in Blender:  import blueprint_setup as BS; BS.build_planes(placement_json_path, collection="Blueprints")
"""
import json
import os
import sys

import numpy as np

VIEWS = {
    'front': dict(u=(1.0, 0.0, 0.0), look=(0.0, 1.0, 0.0)),
    'back': dict(u=(-1.0, 0.0, 0.0), look=(0.0, -1.0, 0.0)),
    'left': dict(u=(0.0, 1.0, 0.0), look=(-1.0, 0.0, 0.0)),
    'right': dict(u=(0.0, -1.0, 0.0), look=(1.0, 0.0, 0.0)),
}
DE_EDGE = 12.0      # dE threshold: the backdrop residual is 0-2 dE on these studio images, skin 22-78 (measured on the
                    # woman2 set); half-way leaves margin both sides and puts the edge near the half-level crossing
SMALL_HOLE_PX = 400  # px; a highlight or JPEG speck, far below any arm-to-body gap (thousands of px)
MODEL_PX_M = 0.0005  # the model's own silhouette grid (0.5 mm): finer than any landmark's sd


# ------------------------------------------------------------------------------------------------ masks & rasters
def image_mask(path):
    import numpy as np
    from PIL import Image
    from scipy import ndimage as ndi
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import backdrop_mask as BM
    rgb = np.asarray(Image.open(path).convert('RGB')).astype(float) / 255.0
    bg, used, lab, chroma = BM.fit_backdrop(rgb)
    de = np.linalg.norm(lab - BM.srgb_to_lab(bg), axis=-1)
    m = de >= DE_EDGE
    m = ndi.binary_opening(m, iterations=1)
    lab_c, n = ndi.label(m)
    if n > 1:
        sz = ndi.sum(m, lab_c, range(1, n + 1))
        m = np.isin(lab_c, 1 + np.flatnonzero(sz >= 0.01 * sz.max()))
    # fill only SMALL holes (highlights); a gap between an arm and the body closed off by the wrist is a hole too,
    # and filling it erased the arm-to-torso gaps of the back view
    holes = ndi.binary_fill_holes(m) & ~m
    hl, nh = ndi.label(holes)
    if nh:
        hs = ndi.sum(holes, hl, range(1, nh + 1))
        m = m | np.isin(hl, 1 + np.flatnonzero(hs < SMALL_HOLE_PX))
    return m, dict(backdrop_median_dE=float(np.median(de[used])), threshold_dE=DE_EDGE)


def project(v, view):
    import numpy as np
    u = np.asarray(VIEWS[view]['u'])
    return v @ u, v[:, 2]


def _cover_kernel():
    from numba import njit

    @njit(cache=True)
    def cover(P, f, m):
        H, W = m.shape
        for i in range(f.shape[0]):
            a, b, c = f[i, 0], f[i, 1], f[i, 2]
            x0, y0, x1, y1, x2, y2 = P[a, 0], P[a, 1], P[b, 0], P[b, 1], P[c, 0], P[c, 1]
            A = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
            if A == 0.0:
                continue
            lo_x = max(int(np.floor(min(x0, min(x1, x2)))), 0)
            hi_x = min(int(np.ceil(max(x0, max(x1, x2)))), W - 1)
            lo_y = max(int(np.floor(min(y0, min(y1, y2)))), 0)
            hi_y = min(int(np.ceil(max(y0, max(y1, y2)))), H - 1)
            for py in range(lo_y, hi_y + 1):
                yc = py + 0.5
                for px in range(lo_x, hi_x + 1):
                    xc = px + 0.5
                    w0 = ((x1 - xc) * (y2 - yc) - (x2 - xc) * (y1 - yc)) / A
                    w1 = ((x2 - xc) * (y0 - yc) - (x0 - xc) * (y2 - yc)) / A
                    w2 = 1.0 - w0 - w1
                    if w0 >= -1e-9 and w1 >= -1e-9 and w2 >= -1e-9:
                        m[py, px] = 1
    import numpy as np  # noqa: F811  (numba resolves np from the closure's globals)
    return cover


_COVER = None


def raster(v, f, view, U0, Z0, s, W, H):
    """silhouette mask of a triangle mesh at an image's pixel grid: px u = (p.u - U0)/s, row = (Z0 - z)/s.
    Pixel-centre coverage with inclusive edge tests, so triangles sharing an edge leave no crack (cv2.fillPoly per
    triangle left 1-px cracks between neighbours)."""
    import numpy as np
    global _COVER
    if _COVER is None:
        _COVER = _cover_kernel()
    pu, pz = project(v, view)
    P = np.stack([(pu - U0) / s, (Z0 - pz) / s], 1).astype(np.float64)
    m = np.zeros((H, W), np.uint8)
    _COVER(P, np.ascontiguousarray(f, dtype=np.int64), m)
    return m.astype(bool)


def model_grid(v, view, pad=0.02):
    pu, pz = project(v, view)
    s = MODEL_PX_M
    U0, Z0 = pu.min() - pad, pz.max() + pad
    W = int((pu.max() - pu.min() + 2 * pad) / s) + 1
    H = int((pz.max() - pz.min() + 2 * pad) / s) + 1
    return U0, Z0, s, W, H


# ------------------------------------------------------------------------------------------------ landmark rules
def _runs(row):
    import numpy as np
    d = np.diff(np.r_[0, row.astype(np.int8), 0])
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1))


def _centre_run(row, c):
    rr = _runs(row)
    if not rr:
        return None
    for a, b in rr:
        if a <= c <= b:
            return a, b
    return min(rr, key=lambda ab: min(abs(ab[0] - c), abs(ab[1] - c)))


def eval_rules(mask, rules, points_px, centre_col=None):
    """landmark rows (float px) on one mask.  points_px: name -> (col, row)."""
    import numpy as np
    H, W = mask.shape
    rows_any = np.flatnonzero(mask.any(1))
    if centre_col is None:
        centre_col = float(np.nonzero(mask)[1].mean())
    out = {}
    for r in rules:
        k = r['rule']
        if k == 'point':
            out[r['name']] = float(points_px[r['point']][1])
        elif k == 'row_frac':
            out[r['name']] = float(rows_any.min() + r['frac'] * (rows_any.max() - rows_any.min()))
        elif k == 'mean_points':
            out[r['name']] = float(np.mean([points_px[p][1] for p in r['points']]))
        elif k == 'top_at_frac':
            lo = int(rows_any.min())
            hi = int(round(out[r['below']]))
            widest = 0
            for y in range(lo, hi):
                xs = np.flatnonzero(mask[y])
                if len(xs):
                    widest = max(widest, max(centre_col - xs.min(), xs.max() - centre_col))
            tops = []
            for sgn in (-1, 1):
                col = int(round(centre_col + sgn * r['frac'] * widest))
                col = min(max(col, 0), W - 1)
                ys = np.flatnonzero(mask[:, col])
                if len(ys):
                    tops.append(ys.min())
            out[r['name']] = float(np.mean(tops))
        elif k == 'min_width_row':
            a, b = sorted(int(round(out[n])) for n in r['between'])
            best, by = 1e9, None
            for y in range(a, b + 1):
                cr = _centre_run(mask[y], centre_col)
                if cr and cr[1] - cr[0] < best:
                    best, by = cr[1] - cr[0], y
            # the minimum is broad: take the middle of the rows within 0.5 % of it
            ws = []
            for y in range(a, b + 1):
                cr = _centre_run(mask[y], centre_col)
                ws.append(cr[1] - cr[0] if cr else 1e9)
            ws = np.array(ws)
            near = np.flatnonzero(ws <= best * 1.005) + a
            out[r['name']] = float(np.median(near))
        elif k == 'extreme_u':
            a, b = sorted(int(round(out[n])) for n in r['between'])
            best, by = None, None
            for y in range(a, b + 1):
                xs = np.flatnonzero(mask[y])
                if not len(xs):
                    continue
                val = xs.min() if r['side'] == 'min' else -xs.max()
                if best is None or val < best:
                    best, by = val, y
            out[r['name']] = float(by)
        else:
            raise ValueError('unknown rule ' + k)
    return out


def eval_centre(mask, rule, rows, centre_col=None):
    import numpy as np
    if centre_col is None:
        centre_col = float(np.nonzero(mask)[1].mean())
    if rule['rule'] == 'midline':
        a, b = sorted(int(round(rows[n])) for n in rule['between'])
        mids = []
        for y in range(a, b + 1):
            cr = _centre_run(mask[y], centre_col)
            if cr:
                mids.append(0.5 * (cr[0] + cr[1]))
        return float(np.median(mids))
    if rule['rule'] == 'run_mid_at':
        y = int(round(rows[rule['at']]))
        cr = _centre_run(mask[y], centre_col)
        return 0.5 * (cr[0] + cr[1])
    raise ValueError(rule['rule'])


# ------------------------------------------------------------------------------------------------ the fit
def fit(config_path, out_path):
    import numpy as np
    from PIL import Image
    cfg = json.load(open(config_path))
    root = cfg.get('root', os.path.dirname(os.path.abspath(config_path)))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fit_to_reference as FT
    v, f, _ = FT.read_ply(os.path.join(root, cfg['model']))
    mp = {k: np.asarray(p, float) for k, p in cfg.get('model_points', {}).items()}
    out_dir = os.path.dirname(os.path.abspath(out_path))
    res = dict(tool='engine/tools/blueprint_setup.py', config=os.path.relpath(config_path, root).replace('\\', '/'),
               model=cfg['model'], images={})
    for name, im in cfg['images'].items():
        view = im['view']
        path = os.path.join(root, im['file'])
        mask, minfo = image_mask(path)
        H, W = mask.shape
        Image.fromarray(mask.astype(np.uint8) * 255).save(os.path.join(out_dir, name + '_mask.png'))
        rules = im['landmarks']
        # image side
        rows_i = eval_rules(mask, rules, im.get('points_px', {}), im.get('centre_hint_px'))
        c_i = eval_centre(mask, im['centre'], rows_i, im.get('centre_hint_px'))
        # model side: the same rules on the model silhouette (posed vertices if the image says so)
        vm = v
        if im.get('model_vertices'):
            vm = np.load(os.path.join(root, im['model_vertices']))['v']
        U0m, Z0m, sm, Wm, Hm = model_grid(vm, view)
        mmask = raster(vm, f, view, U0m, Z0m, sm, Wm, Hm)
        pts_m = {}
        for k, p in mp.items():
            pu, pz = project(p[None], view)
            pts_m[k] = ((pu[0] - U0m) / sm, (Z0m - pz[0]) / sm)
        rows_m = eval_rules(mmask, rules, pts_m)
        c_m = eval_centre(mmask, im['centre'], rows_m)
        z_m = {k: Z0m - sm * r for k, r in rows_m.items()}
        uc_m = U0m + sm * c_m
        # weighted LSQ: z_model = Z0 - s * row_image
        names = [r['name'] for r in rules if r.get('use', True)]
        wts = np.array([1.0 / (r['sd_mm'] / 1000.0) ** 2 for r in rules if r.get('use', True)])
        A = np.c_[np.ones(len(names)), -np.array([rows_i[n] for n in names])]
        b = np.array([z_m[n] for n in names])
        sw = np.sqrt(wts)
        sol, *_ = np.linalg.lstsq(A * sw[:, None], b * sw, rcond=None)
        Z0, s = float(sol[0]), float(sol[1])
        if im.get('fixed_scale_mm_per_px'):
            s = im['fixed_scale_mm_per_px'] / 1000.0
            Z0 = float(np.average(b + s * np.array([rows_i[n] for n in names]), weights=wts))
        U0 = float(uc_m - s * c_i)
        resid = {r['name']: round(float(Z0 - s * rows_i[r['name']] - z_m[r['name']]) * 1000, 2) for r in rules
                 if r['rule'] != 'row_frac'}
        # world corners of the image plane (pixel corners), placed behind the model as seen from this camera
        uax = np.asarray(VIEWS[view]['u'])
        look = np.asarray(VIEWS[view]['look'])
        depth = float((v @ look).max()) + im.get('plane_gap_m', 0.03)
        corners = []
        for (cu, cr) in ((0, H), (W, H), (W, 0), (0, 0)):   # bottom-left, bottom-right, top-right, top-left
            u = U0 + s * cu
            z = Z0 - s * cr
            corners.append((uax * u + look * depth + np.array([0, 0, z])).tolist())
        res['images'][name] = dict(
            file=im['file'], view=view, size_px=[W, H], mm_per_px=round(s * 1000, 5), U0_m=U0, Z0_m=Z0,
            plane_corners_m=corners, plane_depth_m=depth, look=look.tolist(),
            landmarks_px={k: round(x, 1) for k, x in rows_i.items()}, centre_px=round(c_i, 1),
            landmarks_model_z_mm={k: round(x * 1000, 2) for k, x in z_m.items()}, centre_model_mm=round(uc_m * 1000, 2),
            residual_mm=resid, rms_residual_mm=round(float(np.sqrt(np.mean([resid[n] ** 2 for n in names]))), 2), used=names,
            mask=minfo, hidden=bool(im.get('hidden', False)))
        print(name, view, 'mm/px %.4f' % (s * 1000), 'resid mm', resid)
    json.dump(res, open(out_path, 'w'), indent=1)
    return res


def to_px(placement_img, p):
    """world points -> (col, row) px of a placed image"""
    import numpy as np
    pu, pz = project(np.atleast_2d(p), placement_img['view'])
    s = placement_img['mm_per_px'] / 1000.0
    return np.stack([(pu - placement_img['U0_m']) / s, (placement_img['Z0_m'] - pz) / s], 1)


# ------------------------------------------------------------------------------------------------ Blender side
def build_planes(placement_path, collection='Blueprints', root=None, names=None):
    """one textured, one-sided plane per placed image (run inside Blender)"""
    import bpy
    P = json.load(open(placement_path))
    root = root or os.path.dirname(os.path.abspath(placement_path))
    coll = bpy.data.collections.get(collection)
    if coll is None:
        coll = bpy.data.collections.new(collection)
        bpy.context.scene.collection.children.link(coll)
    made = []
    for name, im in P['images'].items():
        if names and name not in names:
            continue
        nm = 'BP_' + name
        img = bpy.data.images.load(os.path.join(root, im['file']), check_existing=True)
        me = bpy.data.meshes.get(nm) or bpy.data.meshes.new(nm)
        me.clear_geometry()
        c = im['plane_corners_m']
        # winding so the face normal points back toward the camera of this view (-look)
        me.from_pydata([tuple(x) for x in c], [], [(0, 1, 2, 3)])
        me.update()
        n = me.polygons[0].normal
        look = im['look']
        flip = (n[0] * look[0] + n[1] * look[1] + n[2] * look[2]) > 0
        if flip:
            me.clear_geometry()
            me.from_pydata([tuple(x) for x in c[::-1]], [], [(0, 1, 2, 3)])
            uvs = [(0, 1), (1, 1), (1, 0), (0, 0)][::-1]
        else:
            uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
        uvl = me.uv_layers.new(name='UV') if not me.uv_layers else me.uv_layers[0]
        for li, uv in enumerate(uvs):
            uvl.data[li].uv = uv
        mat = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = img
        em = nt.nodes.new('ShaderNodeEmission')
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(tex.outputs['Color'], em.inputs['Color'])
        nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
        nt.nodes.active = tex
        mat.use_backface_culling = True
        me.materials.clear()
        me.materials.append(mat)
        ob = bpy.data.objects.get(nm) or bpy.data.objects.new(nm, me)
        ob.data = me
        for cc in list(ob.users_collection):
            if cc != coll:
                cc.objects.unlink(ob)
        if ob.name not in coll.objects:
            coll.objects.link(ob)
        ob['mm_per_px'] = im['mm_per_px']
        ob['landmark_rms_mm'] = im['rms_residual_mm']
        ob['view'] = im['view']
        ob.hide_set(bool(im.get('hidden', False)))
        ob.hide_render = True
        made.append(nm)
    return made


if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == 'fit':
        fit(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
