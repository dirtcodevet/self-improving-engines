# Blender-side: render a part_lab mesh alone with views.py (head-local views). Globals: LAB (out_prefix), OUT (png).
# Imports <LAB>.ply as Lab_Body in collection 'Lab', renders, then deletes it (state restored in try/finally).
import bpy, json
J = json.load(open(LAB + "_frame.json"))
col = bpy.data.collections.new("Lab")
bpy.context.scene.collection.children.link(col)
before = set(bpy.data.objects)
try:
    bpy.ops.wm.ply_import(filepath=LAB + ".ply")
    new = [o for o in bpy.data.objects if o not in before]
    lab = new[0]
    for cc in list(lab.users_collection):
        cc.objects.unlink(lab)
    col.objects.link(lab)
    lab.name = "Lab_Body"
    for p in lab.data.polygons:
        p.use_smooth = True
    PREFIX = "Lab"
    CENTER = tuple(J["center"]); SIZE = J["size"] * 0.8
    VIEWS = {k: (tuple(d), True) for k, d in J["views"].items()}
    exec(open(VIEWS_PY).read())
finally:
    for o in [o for o in bpy.data.objects if o not in before]:
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    bpy.data.collections.remove(col)
print("lab view", OUT)
