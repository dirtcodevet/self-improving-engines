"""blueprint_compare.py - a model's silhouette against placed blueprint images: overlays and contour distances by region.

Why it exists (woman2 Stage 4, 2026-10-19).  Blueprint images are FORM references (the person: "the cheaper version of
handing you a 3d model").  To use them for what the photo and the generated 3-D reference do not show well (the side
body and armpit, the breast's side profile), each view needs a direct, local comparison: where the model's outline is
outside or inside the image's outline, by how much, and whether the image shows a GAP (an arm apart from the body)
where the model shows none.  `blueprint_setup.py` places the images by landmarks (A29), never by the outlines compared
here, so the comparison cannot hide what it measures.

For each image (placement JSON from blueprint_setup):
  - the model's silhouette is rasterised at the image's own pixel grid (same view, same scale, same offsets);
  - every image boundary pixel gets the distance to the model's boundary, signed + where the model lies OUTSIDE the
    image's outline there (model bigger) and - where inside; reported in mm per region = height band (case-given,
    model z) x side of the midline x class: 'outer' (the outermost edge of the row), 'gap_body' (a gap edge on the
    run that holds the centre column: the body's side) and 'gap_limb' (a gap edge on a lateral run: the limb's inner
    edge);
  - gap rows: per band and side, the share of rows where the image shows a gap between a lateral run and the centre
    run, the same for the model, and their median gap widths (mm);
  - an overlay PNG: the image dimmed, the image outline green, the model outline magenta, model-only area red,
    image-only area blue, the bands' top lines grey.

What it cannot see: anything inside the outline (a fold, a crease, a breast's front); depth along the view.  Images of
a different build differ by a smooth scale-like error; read regions against each other, not each number alone.

usage: python blueprint_compare.py PLACEMENT.json MESH(.ply|.npz) OUT_DIR TAG --bands BANDS.json [--images a,b]
  BANDS.json: {"bands": [[name, z_top_m, z_bottom_m], ...]}
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blueprint_setup as BS  # noqa: E402


def load_mesh(path):
    if path.endswith('.npz'):
        d = np.load(path)
        return d['v'], d['f']
    import fit_to_reference as FT
    v, f, _ = FT.read_ply(path)
    return v, f


def boundary(m):
    from scipy import ndimage as ndi
    return m & ~ndi.binary_erosion(m, iterations=1, border_value=0)


def classify_rows(m, centre):
    """per boundary pixel: 0 outer, 1 gap edge on the centre run (body), 2 gap edge on a lateral run (limb)"""
    H, W = m.shape
    cls = np.full((H, W), -1, np.int8)
    gaps = {}
    for y in range(H):
        rr = BS._runs(m[y])
        if not rr:
            continue
        cr = BS._centre_run(m[y], centre)
        for i, (a, b) in enumerate(rr):
            for x, is_outer in ((a, i == 0), (b, i == len(rr) - 1)):
                if is_outer:
                    cls[y, x] = 0
                else:
                    cls[y, x] = 1 if (a, b) == cr else 2
        # gaps beside the centre run, each side: (left gap width, right gap width) in px, or None
        if cr is not None:
            ci = rr.index(cr)
            gl = (cr[0] - rr[ci - 1][1] - 1) if ci > 0 else None
            gr = (rr[ci + 1][0] - cr[1] - 1) if ci < len(rr) - 1 else None
            gaps[y] = (gl, gr)
    return cls, gaps


def compare_one(im, v, f, bands, img_path, out_png):
    from PIL import Image
    from scipy import ndimage as ndi
    W, H = im['size_px']
    s = im['mm_per_px'] / 1000.0
    img_mask, _ = BS.image_mask(img_path)
    mod_mask = BS.raster(v, f, im['view'], im['U0_m'], im['Z0_m'], s, W, H)
    c_px = im['centre_px']
    bi, bm = boundary(img_mask), boundary(mod_mask)
    dist_to_model = ndi.distance_transform_edt(~bm) * s * 1000.0  # mm
    sign = np.where(mod_mask, 1.0, -1.0)
    cls_i, gaps_i = classify_rows(img_mask, c_px)
    cls_m, gaps_m = classify_rows(mod_mask, c_px)
    ys, xs = np.nonzero(bi)
    z_of = im['Z0_m'] - s * (ys + 0.5)
    side = np.where(xs >= c_px, 'imgR', 'imgL')
    out = dict(view=im['view'], mm_per_px=im['mm_per_px'], regions={}, gaps={})
    cname = {0: 'outer', 1: 'gap_body', 2: 'gap_limb'}
    for bname, zt, zb in bands:
        inb = (z_of <= zt) & (z_of > zb)
        for sd in ('imgL', 'imgR'):
            for c in (0, 1, 2):
                sel = inb & (side == sd) & (cls_i[ys, xs] == c)
                if sel.sum() < 5:
                    continue
                d = dist_to_model[ys[sel], xs[sel]] * sign[ys[sel], xs[sel]]
                out['regions']['%s.%s.%s' % (bname, sd, cname[c])] = dict(
                    n=int(sel.sum()), median_signed_mm=round(float(np.median(d)), 2),
                    p90_abs_mm=round(float(np.percentile(np.abs(d), 90)), 2))
            # gap rows
            rows = [y for y in range(H) if zb < im['Z0_m'] - s * (y + 0.5) <= zt]
            k = 0 if sd == 'imgL' else 1
            gi = [gaps_i.get(y, (None, None))[k] for y in rows]
            gm = [gaps_m.get(y, (None, None))[k] for y in rows]
            if rows and (img_mask[rows].any() or mod_mask[rows].any()):
                hi = [g for g in gi if g is not None]
                hm = [g for g in gm if g is not None]
                out['gaps']['%s.%s' % (bname, sd)] = dict(
                    rows=len(rows), image_gap_share=round(len(hi) / len(rows), 3),
                    model_gap_share=round(len(hm) / len(rows), 3),
                    image_gap_median_mm=round(float(np.median(hi)) * s * 1000, 1) if hi else None,
                    model_gap_median_mm=round(float(np.median(hm)) * s * 1000, 1) if hm else None)
    # overlay
    rgb = np.asarray(Image.open(img_path).convert('RGB')).astype(float) / 255.0
    o = 0.35 + 0.45 * rgb
    o[mod_mask & ~img_mask] = o[mod_mask & ~img_mask] * 0.5 + np.array([0.5, 0.0, 0.0])
    o[img_mask & ~mod_mask] = o[img_mask & ~mod_mask] * 0.5 + np.array([0.0, 0.1, 0.5])
    bi2 = ndi.binary_dilation(bi, iterations=1)
    bm2 = ndi.binary_dilation(bm, iterations=1)
    o[bi2] = (0.1, 0.85, 0.2)
    o[bm2] = (0.95, 0.1, 0.95)
    for bname, zt, zb in bands:
        y = int((im['Z0_m'] - zt) / s)
        if 0 <= y < H:
            o[y, ::6] = (0.6, 0.6, 0.6)
    Image.fromarray((np.clip(o, 0, 1) * 255).astype(np.uint8)).save(out_png)
    out['overlay'] = os.path.basename(out_png)
    out['area_iou'] = round(float((img_mask & mod_mask).sum() / max((img_mask | mod_mask).sum(), 1)), 4)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('placement')
    ap.add_argument('mesh')
    ap.add_argument('out_dir')
    ap.add_argument('tag')
    ap.add_argument('--bands', required=True)
    ap.add_argument('--images', default=None)
    a = ap.parse_args()
    P = json.load(open(a.placement))
    root = json.load(open(a.bands)).get('root') or os.path.dirname(os.path.abspath(a.placement))
    bands = json.load(open(a.bands))['bands']
    v, f = load_mesh(a.mesh)
    names = a.images.split(',') if a.images else list(P['images'])
    res = dict(tool='engine/tools/blueprint_compare.py', mesh=a.mesh.replace('\\', '/'), tag=a.tag, images={})
    os.makedirs(a.out_dir, exist_ok=True)
    for n in names:
        im = P['images'][n]
        r = compare_one(im, v, f, bands, os.path.join(root, im['file']),
                        os.path.join(a.out_dir, 'bp_%s_%s.png' % (a.tag, n)))
        res['images'][n] = r
        print(n, 'IoU', r['area_iou'])
        for k, g in r['gaps'].items():
            print('  gap', k, g)
    json.dump(res, open(os.path.join(a.out_dir, 'bp_%s.json' % a.tag), 'w'), indent=1)


if __name__ == '__main__':
    main()
