"""build_base_torso.py - "give me a woman's torso": build the stored base female torso in Blender from the pack.

Why it exists (woman2 FINISH_SPEC F8, 2026-10-19).  The person: "if I came in tomorrow and had a blank blender file I
could say, 'give me a woman's torso' and you could produce it from scratch and it would be that one."  The pack
`engine/packs/human/base_female_torso/<version>/` holds that torso as Blender-free data (npz + json); this tool turns
it back into the objects of the woman2 scene, with the same names, frame, data layout and settings.

What it builds (the current version, v2, the approved torso of woman2 Stage 4c):
  - <P>_Torso: the one continuous skin (542,468 vertices), smooth shaded, arms as their own limbs; vertex groups for
    the 12 bones, the zones (zone_breast, zone_areola, zone_nipple, zone_tubercle, zone_vein) and pores_strength;
    point attributes for the zones, skin_roughness, skin_sss_scale, arm_limb and the colour attribute skin_colour;
    the corrective shape keys (abd15/45/60/75/90 and flex60 per side) with their drivers, and NAC_micro_off (the
    nipple-areola micro layer's switch); the modifiers Skin_micro_subdiv and Skin_micro_detail (the switchable skin
    micro-detail layer: off in the viewport, on for renders) and Armature; the material <P>_Skin (per-vertex skin
    colour, gloss and translucency);
  - <P>_Rig: the 12-bone armature (hips, spine, chest, neck, clavicle, scapula, upper_arm, forearm .L/.R), rest pose =
    the photo pose, the shoulder girdle driven by the scapulohumeral rhythm (hidden, as in the live scene);
  - <P>_RibCage: the thoracic shell under the skin, hidden, carried by the chest bone;
  - <P>_ChestWall (v12+): the chest wall under each breast as the pectoral fascia the breast rests and slides on
    (cases/woman2/lib/chest_wall.py, the pack's chest_wall.npz), hidden, carried by the chest bone.
  - (build 08 packs) the skin built from its own polygons (polys.npz: a quad base mesh, with its UV map) when the pack
    has them, and <P>_BodyRest: the base body's head, hands and legs, hidden, deformed by the rig (body_rest.npz).
<P> is the pack's prefix (scene.json: "Woman2").  Everything lands in the collection <P>, in the pack's frame (origin
near the jugular notch: measurements.json gives it), or at --location (the rig moves; the skin and rib cage follow).
Older versions build too (v1: scene.json without "format").

Run it:
  a new Blender:      blender --python engine/tools/build_base_torso.py -- [--location X Y Z] [--version v2] [--save out.blend]
                      (--pack <folder>: build that pack folder, e.g. a case's build, instead of a stored version)
  in the background:  blender -b --factory-startup --python engine/tools/build_base_torso.py -- --save out.blend
  a running Blender:  python engine/tools/build_base_torso.py --port 9876 [--instance NAME] [--location X Y Z]
                      (sends this file over the Blender MCP socket, bmcp.py; with --instance every payload first asserts
                      bpy.app.driver_namespace["bmcp_instance"] == NAME, as a second Blender requires)
  from Python inside Blender:  import build_base_torso; build_base_torso.build(location=(0, 0, 0))
It refuses to overwrite objects that already carry the names (use --replace, or another --prefix).
Only numpy and bpy are needed inside Blender.  Build time for v2: about a minute.
"""
import json
import os
import sys
import time

import numpy as np

try:
    _THIS = os.path.abspath(__file__)
except NameError:  # sent over the socket: the caller sets base_torso_args['root']
    _THIS = None


def _root(args):
    if args.get('root'):
        return args['root']
    if _THIS is None:
        raise RuntimeError('build_base_torso: set base_torso_args["root"] (the engine checkout) when sending the code')
    return os.path.abspath(os.path.join(os.path.dirname(_THIS), '..', '..'))


def pack_dir(root, version=None):
    base = os.path.join(root, 'engine', 'packs', 'human', 'base_female_torso')
    pk = json.load(open(os.path.join(base, 'pack.json')))
    return os.path.join(base, version or pk['current']), pk


# --------------------------------------------------------------------------------------------- helpers (bpy)
def _make_mesh(name, v, f, sizes=None):
    """A mesh from triangles f (m x 3), or from polygons: `sizes` (corners per polygon) with f the flat corner list
    (build 08: a pack may store its skin's own polygons, e.g. a quad base mesh, in polys.npz)."""
    import bpy
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(v))
    me.vertices.foreach_set("co", np.asarray(v, np.float32).ravel())
    flat = np.asarray(f, np.int32).ravel()
    sizes = np.full(len(f), 3, np.int32) if sizes is None else np.asarray(sizes, np.int32)
    me.loops.add(flat.size)
    me.loops.foreach_set("vertex_index", flat)
    me.polygons.add(len(sizes))
    me.polygons.foreach_set("loop_start", np.r_[0, np.cumsum(sizes)[:-1]].astype(np.int32))
    me.polygons.foreach_set("loop_total", sizes)
    me.update(calc_edges=True)
    me.validate(verbose=False)
    me.polygons.foreach_set("use_smooth", np.ones(len(sizes), bool))
    return me


def _add_uv(me, uv, name='UVMap'):
    """A UV map from per-corner coordinates in the mesh's loop order."""
    lay = me.uv_layers.new(name=name)
    lay.data.foreach_set('uv', np.asarray(uv, np.float32).ravel())
    return lay


def _add_group(ob, name, w, member):
    """A vertex group holding exactly the members with their weights, added in batches of equal weight (one call per
    distinct value; the per-vertex loop took minutes)."""
    vg = ob.vertex_groups.new(name=name)
    idx = np.nonzero(member)[0]
    if not len(idx):
        return vg
    ww = np.asarray(w, np.float32)[idx]
    o = np.argsort(ww, kind='stable')
    ww, idx = ww[o], idx[o]
    cuts = np.r_[0, np.nonzero(np.diff(ww))[0] + 1, len(ww)]
    for a, b in zip(cuts[:-1], cuts[1:]):
        vg.add(idx[a:b].tolist(), float(ww[a]), 'REPLACE')
    return vg


def _armature(coll, name, A, bones):
    """The armature object with its bones (rest pose = the stored edit bones)."""
    import bpy
    import mathutils
    arm = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, arm)
    coll.objects.link(rig)
    rig.show_in_front = A['show_in_front']
    arm.display_type = A['display_type']
    vl = bpy.context.view_layer
    for o in bpy.context.selected_objects:
        o.select_set(False)
    vl.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for b in A['bone_order']:
        d = bones[b]
        e = arm.edit_bones.new(b)
        e.head, e.tail = d['head'], d['tail']
        # roll: the bone's Z axis toward +Y ('+Y', v1-v5), or toward a stored vector (v6: the shoulder complex turned
        # with a spine bend keeps its frames turned with it, so its deform matrices are the old ones conjugated)
        ra = d['roll_align']
        assert ra == '+Y' or (isinstance(ra, list) and len(ra) == 3)
        e.align_roll(mathutils.Vector((0.0, 1.0, 0.0)) if ra == '+Y' else mathutils.Vector(ra))
        eb[b] = e
    for b in A['bone_order']:
        d = bones[b]
        if d['parent']:
            eb[b].parent = eb[d['parent']]
            eb[b].use_connect = bool(d['connected'])
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:
        pb.rotation_mode = A['rotation_mode']
    rig.select_set(False)
    return rig, arm


def _graph_material(name, spec, pack_dir=None):
    """A material from a stored node graph: nodes in order (name, type, location, settings, unlinked inputs by socket
    identifier) and links by socket identifier. A setting 'image_file' (v6) loads an image stored in the pack folder:
    {"file", "colorspace", "name"} (e.g. a 16-bit relief tile, read as non-colour data)."""
    import bpy
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    made = {}
    for nd in spec['nodes']:
        n = nt.nodes.new(nd['type'])
        n.name = nd['name']
        n.location = nd['location']
        for k, val in nd['settings'].items():
            if k == 'image_file':
                path = os.path.join(pack_dir, val['file'])
                img = bpy.data.images.get(val['name'])
                if img is None or os.path.normcase(bpy.path.abspath(img.filepath)) != os.path.normcase(path):
                    img = bpy.data.images.load(path)
                    img.name = val['name']
                img.colorspace_settings.name = val.get('colorspace', 'Non-Color')
                n.image = img
                continue
            setattr(n, k, val)
        for ident, val in nd['inputs'].items():
            sock = [s for s in n.inputs if s.identifier == ident]
            if sock:
                sock[0].default_value = val
        made[nd['name']] = n
    for fn, fs, tn, ts in spec['links']:
        so = [s for s in made[fn].outputs if s.identifier == fs][0]
        si = [s for s in made[tn].inputs if s.identifier == ts][0]
        nt.links.new(so, si)
    mat.diffuse_color = spec['diffuse_color']
    mat.roughness = spec['roughness']
    mat.metallic = spec['metallic']
    return mat


def _rest_and_report(ob, rig, rc, coll, me, v32, location, ver, ndrivers, t0, log, prev_active):
    import bpy
    vl = bpy.context.view_layer
    for p in rig.pose.bones:
        p.location = (0, 0, 0)
        p.scale = (1, 1, 1)
        if not p.name.startswith(('scapula', 'clavicle')):  # the girdle bones are driven
            p.rotation_euler = (0, 0, 0)
    rig.data.pose_position = 'POSE'
    rig.location = tuple(float(x) for x in location)
    vl.objects.active = prev_active if prev_active is not None and prev_active.name in vl.objects else ob
    vl.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg).to_mesh()
    Pe = np.zeros(len(ev.vertices) * 3, np.float32)
    ev.vertices.foreach_get('co', Pe)
    ob.evaluated_get(dg).to_mesh_clear()
    Pw = Pe.reshape(-1, 3) + np.array(rig.location, np.float32)  # evaluated in the skin's local space (parented to the rig)
    rest_dev = float(np.abs(Pw - (v32 + np.array(location, np.float32))).max())
    info = dict(version=ver, objects=[ob.name, rig.name, rc.name], collection=coll.name, verts=len(me.vertices),
                faces=len(me.polygons), vertex_groups=len(ob.vertex_groups),
                shape_keys=[k.name for k in me.shape_keys.key_blocks], drivers=ndrivers,
                modifiers=[m.name for m in ob.modifiers], location=list(rig.location),
                rest_pose_max_dev_mm=round(rest_dev * 1e3, 5), seconds=round(time.time() - t0, 1))
    log('build_base_torso: ' + json.dumps(info))
    return info


def _free_names(names, replace):
    import bpy
    taken = [n for n in (names['torso'], names['rig'], names['rc'], names.get('cw'), names.get('rest')) if n and n in bpy.data.objects]
    if taken and not replace:
        raise RuntimeError('build_base_torso: objects already exist: %s (pass replace=True / --replace, or another prefix)' % taken)
    for n in taken:
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    for coll_, n in ((bpy.data.meshes, names['torso']), (bpy.data.meshes, names['rc']), (bpy.data.meshes, names.get('cw') or ''),
                     (bpy.data.meshes, names.get('rest') or ''), (bpy.data.armatures, names['rig'])):
        d = coll_.get(n)
        if d is not None and d.users == 0:
            coll_.remove(d)
    coll = bpy.data.collections.get(names['coll'])
    if coll is None:
        coll = bpy.data.collections.new(names['coll'])
        bpy.context.scene.collection.children.link(coll)
    return coll


# --------------------------------------------------------------------------------------------- the build (bpy)
def build(location=(0.0, 0.0, 0.0), version=None, prefix=None, replace=False, root=None, log=print, pack=None):
    t0 = time.time()
    root = root or _root({})
    V = os.path.abspath(pack) if pack else pack_dir(root, version)[0]   # pack: any pack folder (e.g. a case's build)
    scene_spec = json.load(open(os.path.join(V, 'scene.json')))
    fmt = scene_spec.get('format', 1)
    if fmt == 2:
        return _build_v2(V, scene_spec, location, prefix, replace, log, t0)
    if fmt == 1:
        return _build_v1(V, scene_spec, location, prefix, replace, log, t0)
    raise RuntimeError('build_base_torso: unknown pack format %r' % fmt)


def _build_v2(V, sc, location, prefix, replace, log, t0):
    import bpy
    import mathutils
    ver = os.path.basename(V)
    rigd = json.load(open(os.path.join(V, 'rig.json')))
    mats = json.load(open(os.path.join(V, 'materials.json')))
    micro = json.load(open(os.path.join(V, 'micro_detail.json')))
    S = np.load(os.path.join(V, 'skin.npz'))
    SH = np.load(os.path.join(V, 'shading.npz'))
    Wd = np.load(os.path.join(V, 'weights.npz'))
    K = np.load(os.path.join(V, 'shape_keys.npz'))
    RC = np.load(os.path.join(V, 'ribcage.npz'))
    P0 = sc['prefix']
    P = prefix or P0
    pre = lambda n: P + n[len(P0):] if n.startswith(P0) else n
    names = dict(coll=P, torso=pre(sc['objects']['torso']), rig=pre(sc['objects']['rig']), rc=pre(sc['objects']['ribcage']))
    if 'chest_wall' in sc['objects']:   # v12+: the chest wall under the breasts (cases/woman2/lib/chest_wall.py)
        names['cw'] = pre(sc['objects']['chest_wall'])
    if 'body_rest' in sc['objects']:    # build 08+: the base body's head, hands and legs, hidden
        names['rest'] = pre(sc['objects']['body_rest'])
    status = 'base_female_torso %s (engine/packs/human/base_female_torso), rebuilt by build_base_torso.py' % ver
    coll = _free_names(names, replace)
    vl = bpy.context.view_layer
    prev_active = vl.objects.active

    # ---- the armature (rest pose = the photo pose)
    rig, arm = _armature(coll, names['rig'], rigd['armature'], rigd['bones'])
    rig['status'] = status

    # ---- the skin: mesh, vertex groups and attributes in the live scene's order
    v32 = S['v'].astype(np.float32)
    PL = np.load(os.path.join(V, sc['polygons']['file'])) if 'polygons' in sc else None   # build 08+: the skin's polygons
    if PL is not None:
        me = _make_mesh(pre(sc['meshes']['torso']), v32, PL['poly_verts'], PL['poly_sizes'])
        _add_uv(me, PL['uv_corner'], sc['polygons'].get('uv_map', 'UVMap'))
    else:
        me = _make_mesh(pre(sc['meshes']['torso']), v32, S['f'].astype(np.int32))
    ob = bpy.data.objects.new(names['torso'], me)
    coll.objects.link(ob)
    gnames = [str(x) for x in Wd['names']]
    assert gnames == sc['vertex_group_order']
    W, M = Wd['W'], Wd['member']
    col = {g: j for j, g in enumerate(gnames)}
    attr_spec = {a['name']: a for a in sc['attributes']}
    for g in gnames:
        if g == 'pores_strength':
            continue  # made with the micro-detail layer, after the shape keys (the live order)
        _add_group(ob, g, W[:, col[g]], M[:, col[g]])
        if g in attr_spec:  # a zone: its attribute right after its group (Blender names it <zone>.001)
            at = me.attributes.new(g, 'FLOAT', 'POINT')
            at.data.foreach_set('value', S[g[len('zone_'):]].astype(np.float32))
    for nm in ('skin_roughness', 'skin_sss_scale'):
        at = me.attributes.new(nm, 'FLOAT', 'POINT')
        at.data.foreach_set('value', SH[nm].astype(np.float32))
    ca = me.color_attributes.new('skin_colour', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', SH['skin_colour'].astype(np.float32).ravel())
    al = me.attributes.new('arm_limb', 'BOOLEAN', 'POINT')
    al.data.foreach_set('value', S['arm_limb'].astype(bool))
    for xa in sc.get('extra_attributes', []):  # v6: e.g. the left breast's relief coordinates (FLOAT2, metres on the skin)
        at = me.attributes.new(xa['name'], xa['type'], xa['domain'])
        at.data.foreach_set('vector' if xa['type'] == 'FLOAT2' else 'value', S[xa['npz_key']].astype(np.float32).ravel())
    # corrective keys and the NAC micro switch (rest + stored offsets, exact in float32)
    ob.shape_key_add(name='Basis', from_mix=False)
    ks = rigd['shape_keys']
    for kn in [str(x) for x in K['names']]:
        tag = kn.replace('.', '_')
        co = v32.copy()
        idx = K['idx_' + tag]
        co[idx] = v32[idx] + K['d_' + tag]
        if 'exact_idx_' + tag in K.files:
            co[K['exact_idx_' + tag]] = K['exact_co_' + tag]
        k = ob.shape_key_add(name=kn, from_mix=False)
        k.data.foreach_set('co', co.ravel())
        k.slider_min, k.slider_max = ks['sliders'][kn]
        k.value = ks['values_at_rest'][kn]
    assert [k.name for k in me.shape_keys.key_blocks] == ks['order']

    # ---- drivers, exactly as stored
    for d in rigd['drivers']:
        owner = me.shape_keys if d['owner'] == 'shape_keys' else rig
        fc = owner.driver_add(d['data_path'], d['index']) if d['owner'] != 'shape_keys' else owner.driver_add(d['data_path'])
        drv = fc.driver
        drv.type = 'SCRIPTED'
        var = drv.variables.new()
        var.name = d['variable']['name']
        var.type = d['variable']['type']
        var.targets[0].id_type = d['variable']['id_type']
        var.targets[0].id = rig
        var.targets[0].data_path = d['variable']['data_path']
        drv.expression = d['expression']

    # ---- the micro-detail layer, then the armature
    if 'pores_strength' in col:
        _add_group(ob, 'pores_strength', W[:, col['pores_strength']], M[:, col['pores_strength']])
    for m in micro['modifiers']:
        md = ob.modifiers.new(m['name'], m['type'])
        if m['type'] == 'DISPLACE':
            t = m['texture']
            tname = pre(t['name'])
            tex = bpy.data.textures.get(tname)
            if tex is None or tex.type != t['settings']['type']:
                tex = bpy.data.textures.new(tname, t['settings']['type'])
            for k, val in t['settings'].items():
                if k != 'type':
                    setattr(tex, k, val)
            md.texture = tex
        if m['type'] == 'ARMATURE':
            md.object = rig
        for k, val in m['settings'].items():
            setattr(md, k, val)
        for k in ('show_viewport', 'show_render', 'show_in_editmode', 'show_on_cage'):
            setattr(md, k, m[k])
    ob.parent = rig
    ob.matrix_parent_inverse = rig.matrix_world.inverted()

    # ---- materials
    mat = _graph_material(pre(mats['skin']['name']), mats['skin'], pack_dir=V)
    me.materials.clear()
    me.materials.append(mat)

    # ---- the rib cage (hidden), carried by the chest bone
    rme = _make_mesh(pre(sc['meshes']['ribcage']), RC['v'], RC['f'])
    rc = bpy.data.objects.new(names['rc'], rme)
    coll.objects.link(rc)
    rme.materials.append(_graph_material(pre(mats['ribcage']['name']), mats['ribcage']))
    rc.parent = rig
    rc.parent_type = sc['ribcage']['parent_type']
    rc.parent_bone = sc['ribcage']['parent_bone']
    vl.update()
    rc.matrix_world = mathutils.Matrix.Identity(4)  # keep its world placement (the frame)
    rc.hide_set(sc['ribcage']['hidden'])
    rc.hide_render = sc['ribcage']['hide_render']
    rc['status'] = status + ': thoracic shell under the skin, for breathing volumes later (hidden)'
    if names.get('cw'):  # the chest wall under the breasts (hidden), carried by the chest bone like the rib cage
        cs = sc['chest_wall']
        CWz = np.load(os.path.join(V, cs['file']))
        cme = _make_mesh(pre(sc['meshes']['chest_wall']), CWz[cs['vertices']].astype(np.float32), CWz['mesh_f'].astype(np.int32))
        cw = bpy.data.objects.new(names['cw'], cme)
        coll.objects.link(cw)
        cme.materials.append(_graph_material(pre(mats['chest_wall']['name']), mats['chest_wall']))
        cw.parent = rig
        cw.parent_type = cs['parent_type']
        cw.parent_bone = cs['parent_bone']
        vl.update()
        cw.matrix_world = mathutils.Matrix.Identity(4)
        cw.hide_set(cs['hidden'])
        cw.hide_render = cs['hide_render']
        cw['status'] = status + ': ' + cs['status']
    if names.get('rest'):  # the base body's head, hands and legs (build 08+), hidden, deformed by the rig
        rs = sc['body_rest']
        R = np.load(os.path.join(V, rs['file']))
        rme = _make_mesh(pre(sc['meshes']['body_rest']), R['v'].astype(np.float32), R['poly_verts'], R['poly_sizes'])
        _add_uv(rme, R['uv_corner'], sc.get('polygons', {}).get('uv_map', 'UVMap'))
        ro = bpy.data.objects.new(names['rest'], rme)
        coll.objects.link(ro)
        WR = R['W']
        for j, b in enumerate([str(x) for x in R['bones']]):
            _add_group(ro, b, WR[:, j], WR[:, j] > 1e-4)
        for nm in ('skin_roughness', 'skin_sss_scale'):
            at = rme.attributes.new(nm, 'FLOAT', 'POINT')
            at.data.foreach_set('value', R[nm].astype(np.float32))
        rca = rme.color_attributes.new('skin_colour', 'FLOAT_COLOR', 'POINT')
        rca.data.foreach_set('color', R['skin_colour'].astype(np.float32).ravel())
        rme.materials.append(mat)
        md = ro.modifiers.new('Armature', 'ARMATURE')
        md.object = rig
        ro.parent = rig
        ro.matrix_parent_inverse = rig.matrix_world.inverted()
        ro.hide_set(rs['hidden'])
        ro.hide_render = rs['hide_render']
        ro['status'] = status + ': ' + rs['status']
    ob['status'] = status
    ob['pack_version'] = ver
    info = _rest_and_report(ob, rig, rc, coll, me, v32, location, ver, len(rigd['drivers']), t0, log, prev_active)
    if names.get('rest'):
        info['objects'].append(names['rest'])
    rig.hide_set(sc['rig']['hidden'])
    return info


def _build_v1(V, scene_spec, location, prefix, replace, log, t0):
    """The v1 pack (superseded; kept buildable as a record and a test fixture)."""
    import bpy
    import mathutils
    ver = os.path.basename(V)
    rigd = json.load(open(os.path.join(V, 'rig.json')))
    mats = json.load(open(os.path.join(V, 'materials.json')))
    micro = json.load(open(os.path.join(V, 'micro_detail.json')))
    S = np.load(os.path.join(V, 'skin.npz'))
    Wd = np.load(os.path.join(V, 'weights.npz'))
    K = np.load(os.path.join(V, 'shape_keys.npz'))
    RC = np.load(os.path.join(V, 'ribcage.npz'))
    P = prefix or scene_spec['collection']
    names = dict(coll=P, torso=P + '_Torso', rig=P + '_Rig', rc=P + '_RibCage', skin_mat=P + '_Skin',
                 rc_mat=P + '_RibCage_mat', tex=P + '_skin_pores')
    status = 'base_female_torso %s (engine/packs/human/base_female_torso), rebuilt by build_base_torso.py' % ver
    coll = _free_names(names, replace)
    vl = bpy.context.view_layer
    prev_active = vl.objects.active

    def srgb2lin(c):
        c = np.asarray(c, float) / 255.0
        return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

    rig, arm = _armature(coll, names['rig'], rigd['armature'], rigd['bones'])
    rig['status'] = status
    v32 = S['v'].astype(np.float32)
    me = _make_mesh(names['torso'], v32, S['f'].astype(np.int32))
    ob = bpy.data.objects.new(names['torso'], me)
    coll.objects.link(ob)
    W = Wd['W']
    for i, b in enumerate([str(b) for b in Wd['bones']]):
        _add_group(ob, b, W[:, i], W[:, i] > 0)
    for zn in ('breast', 'areola', 'nipple'):
        w = S[zn]
        _add_group(ob, 'zone_' + zn, w, w > 1e-4)
        at = me.attributes.new('zone_' + zn, 'FLOAT', 'POINT')
        at.data.foreach_set('value', w.astype(np.float32))
    pa = me.attributes.new('armpit_part', 'INT', 'POINT')
    pa.data.foreach_set('value', S['part'].astype(np.int32))
    ob.shape_key_add(name='Basis', from_mix=False)
    for kn in [str(x) for x in K['names']]:
        k = ob.shape_key_add(name=kn, from_mix=False)
        d = np.zeros_like(v32)
        tag = kn.replace('.', '_')
        d[K['idx_' + tag]] = K['d_' + tag]
        k.data.foreach_set('co', (v32 + d).astype(np.float32).ravel())
        k.slider_min, k.slider_max = rigd['shape_keys']['slider']
    assert [k.name for k in me.shape_keys.key_blocks] == rigd['shape_keys']['order']

    def add_driver(owner, path, index, spec):
        fc = owner.driver_add(path, index) if index is not None else owner.driver_add(path)
        drv = fc.driver
        drv.type = 'SCRIPTED'
        var = drv.variables.new()
        var.name = spec['var']['name']
        var.type = 'SINGLE_PROP'
        var.targets[0].id_type = 'OBJECT'
        var.targets[0].id = rig
        var.targets[0].data_path = 'pose.bones["%s"].%s[%d]' % (spec['var']['bone'], spec['var']['path'], spec['var']['index'])
        drv.expression = spec['expression']

    for spec in rigd['drivers']:
        if spec['target'] == 'shape_key':
            add_driver(me.shape_keys.key_blocks[spec['key']], 'value', None, spec)
        else:
            add_driver(rig.pose.bones[spec['bone']], spec['path'], spec['index'], spec)
    for m in micro['modifiers']:
        md = ob.modifiers.new(m['name'], m['type'])
        if m['type'] == 'SUBSURF':
            md.subdivision_type = m['subdivision_type']
            md.levels, md.render_levels = m['levels'], m['render_levels']
        elif m['type'] == 'DISPLACE':
            t = m['texture']
            tex = bpy.data.textures.get(names['tex']) or bpy.data.textures.new(names['tex'], t['type'])
            tex.noise_scale = t['noise_scale']
            tex.distance_metric = t['distance_metric']
            tex.color_mode = t['color_mode']
            md.texture = tex
            md.texture_coords = m['texture_coords']
            md.direction = m['direction']
            md.strength = m['strength']
            md.mid_level = m['mid_level']
        elif m['type'] == 'ARMATURE':
            md.object = rig
            md.use_vertex_groups = m['use_vertex_groups']
            md.use_deform_preserve_volume = m['use_deform_preserve_volume']
        md.show_viewport, md.show_render = m['show_viewport'], m['show_render']
    ob.parent = rig
    ob.matrix_parent_inverse = rig.matrix_world.inverted()
    sm = mats['skin']
    mat = bpy.data.materials.get(names['skin_mat']) or bpy.data.materials.new(names['skin_mat'])
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (600, 0)
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); bs.location = (300, 0)
    skin, are, nip = (srgb2lin(sm[k]) for k in ('base_rgb', 'areola_rgb', 'nipple_rgb'))
    ca = nt.nodes.new('ShaderNodeAttribute'); ca.attribute_name = 'zone_areola'; ca.location = (-500, 100)
    cn = nt.nodes.new('ShaderNodeAttribute'); cn.attribute_name = 'zone_nipple'; cn.location = (-500, -150)
    m1 = nt.nodes.new('ShaderNodeMix'); m1.data_type = 'RGBA'; m1.location = (-250, 100)
    m1.inputs['A'].default_value = (*skin, 1.0); m1.inputs['B'].default_value = (*are, 1.0)
    nt.links.new(ca.outputs['Fac'], m1.inputs['Factor'])
    m2 = nt.nodes.new('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.location = (0, 0)
    m2.inputs['B'].default_value = (*nip, 1.0)
    nt.links.new(m1.outputs['Result'], m2.inputs['A'])
    nt.links.new(cn.outputs['Fac'], m2.inputs['Factor'])
    nt.links.new(m2.outputs['Result'], bs.inputs['Base Color'])
    for k, val in sm['principled'].items():
        bs.inputs[k].default_value = val
    nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    me.materials.clear()
    me.materials.append(mat)
    rme = _make_mesh(names['rc'], RC['v'], RC['f'])
    rc = bpy.data.objects.new(names['rc'], rme)
    coll.objects.link(rc)
    rmat = bpy.data.materials.get(names['rc_mat']) or bpy.data.materials.new(names['rc_mat'])
    rmat.diffuse_color = mats['ribcage']['diffuse']
    rme.materials.append(rmat)
    rc.parent = rig
    rc.parent_type = 'BONE'
    rc.parent_bone = scene_spec['ribcage']['parent_bone']
    vl.update()
    rc.matrix_world = mathutils.Matrix.Identity(4)
    rc.hide_set(scene_spec['ribcage']['hidden'])
    rc.hide_render = scene_spec['ribcage']['hide_render']
    rc['status'] = status + ': thoracic shell under the skin, for breathing volumes later (hidden)'
    ob['status'] = status
    ob['pack_version'] = ver
    return _rest_and_report(ob, rig, rc, coll, me, v32, location, ver, len(rigd['drivers']), t0, log, prev_active)


# --------------------------------------------------------------------------------------------- entry points
def _parse(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='build_base_torso.py')
    ap.add_argument('--location', nargs=3, type=float, default=[0.0, 0.0, 0.0])
    ap.add_argument('--version')
    ap.add_argument('--pack', help='build this pack folder instead of a stored version (e.g. cases/woman2/build08/pack_b08)')
    ap.add_argument('--prefix')
    ap.add_argument('--replace', action='store_true')
    ap.add_argument('--save', help='save the .blend here afterwards (inside Blender)')
    ap.add_argument('--port', type=int, help='outside Blender: send to the Blender MCP socket on this port')
    ap.add_argument('--instance', help='outside Blender: assert bpy.app.driver_namespace["bmcp_instance"] first')
    return ap.parse_args(argv)


def _in_blender():
    try:
        import bpy  # noqa: F401
        return True
    except ImportError:
        return False


def _blender_main(args):
    import bpy
    info = build(location=args.get('location', (0, 0, 0)), version=args.get('version'), prefix=args.get('prefix'),
                 replace=args.get('replace', False), root=_root(args), pack=args.get('pack'))
    if args.get('save'):
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args['save']))
        print('saved', args['save'])
    return info


def _socket_main(a):
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    os.environ['BMCP_PORT'] = str(a.port)
    import importlib
    import bmcp
    importlib.reload(bmcp)
    src = open(os.path.abspath(__file__), encoding='utf-8').read()
    args = dict(location=a.location, version=a.version, prefix=a.prefix, replace=a.replace, save=a.save,
                root=os.path.abspath(os.path.join(here, '..', '..')), pack=os.path.abspath(a.pack) if a.pack else None)
    head = 'import bpy\n'
    if a.instance:
        head += 'assert bpy.app.driver_namespace.get("bmcp_instance") == %r, "wrong Blender"\n' % a.instance
    head += 'bpy.app.driver_namespace["base_torso_args"] = %r\n' % args
    r = bmcp.send('execute_code', {'code': head + src})
    print(json.dumps(r, indent=1)[:4000])


def _auto():
    if _in_blender():
        import bpy
        args = bpy.app.driver_namespace.pop('base_torso_args', None)
        if args is not None:  # sent over the socket
            return _blender_main(args)
        if __name__ == '__main__':  # blender --python build_base_torso.py -- ...
            argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
            a = _parse(argv)
            return _blender_main(dict(location=a.location, version=a.version, prefix=a.prefix, replace=a.replace,
                                      save=a.save, pack=a.pack))
    elif __name__ == '__main__':
        a = _parse(sys.argv[1:])
        if a.port is None:
            raise SystemExit('outside Blender give --port (a running Blender with the MCP add-on), or run it with '
                             'blender --python engine/tools/build_base_torso.py -- ...')
        _socket_main(a)


_auto()
