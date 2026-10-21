# Blender-side crash safety (16 GB machine): cap undo memory, autosave every 2 min, purge orphan data,
# save the working .blend and a numbered copy in <case>/blend/ (keeps the last KEEP copies).
# Optional globals: LABEL (str), KEEP (int, default 8).
import bpy, os, glob, re, shutil

LABEL = globals().get("LABEL", "")
KEEP = globals().get("KEEP", 8)
p = bpy.context.preferences
p.edit.undo_steps = 6
p.edit.undo_memory_limit = 768  # MB - big meshes made the undo stack the main RAM consumer
p.filepaths.use_auto_save_temporary_files = True
p.filepaths.auto_save_time = 2
for _ in range(3):
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

path = bpy.data.filepath
bpy.ops.wm.save_mainfile(filepath=path, compress=False)
d = os.path.join(os.path.dirname(path), "blend")
os.makedirs(d, exist_ok=True)
nums = [int(m.group(1)) for f in glob.glob(os.path.join(d, "*.blend"))
        for m in [re.match(r".*_(\d{3})", os.path.basename(f))] if m]
n = max(nums, default=0) + 1
dst = os.path.join(d, f"cat_{n:03d}{('_' + LABEL) if LABEL else ''}.blend")
shutil.copy2(path, dst)
olds = sorted(glob.glob(os.path.join(d, "cat_*.blend")))
for f in olds[:-KEEP]:
    os.remove(f)
print(f"checkpoint {os.path.basename(dst)}  ({os.path.getsize(dst)/1e6:.0f} MB)")
