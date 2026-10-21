"""Load the third-party tools kept inside the project (engine/vendor/), without touching the person's Blender setup.
Created 2026-10-21 (woman2 build 15: bring in the tools and data that make the new base better).

Blender side (background, factory startup only):
    import sys; sys.path.insert(0, ENGINE_TOOLS); import vendor
    psk = vendor.enable("pose_shape_keys")          # Pose Shape Keys 1.1.1 (Blender Studio)
    rwt = vendor.enable("robust_weight_transfer")   # Robust Weight Transfer (libigl 2.6 build) + scipy / libigl
  The add-on folders are put on sys.path and enabled in this session only. enable() refuses to run in a Blender that
  was not started with --factory-startup, so the live Blenders (ports 9876 / 9877) and the person's preferences and
  add-on list are never changed; a factory-startup session does not save preferences.
System Python side (3.12):
    import vendor; osim = vendor.opensim()          # OpenSim 4.6 (pip wheel, Apache-2.0)
    vendor.OSIM_MODELS / "ThoracoscapularShoulderModel.osim"
What each one is, its source, version, licence and hash: engine/log/TOOLMAKING.md (build 15) and
`reference content/MAP.md`.
"""
import os
import sys
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[1] / "vendor"
BL_ADDONS = VENDOR / "blender" / "addons"
BL_SITE = VENDOR / "blender" / "site-packages-cp313"     # scipy 1.18.1, libigl 2.6.1, robust_laplacian 1.0.0
PY_SITE = VENDOR / "python" / "cp312"                    # opensim 4.6
OSIM_MODELS = VENDOR / "opensim" / "models"

ADDONS = {"pose_shape_keys": "Pose Shape Keys 1.1.1", "robust_weight_transfer": "Robust Weight Transfer (libigl26)"}


def _path(p):
    p = str(p)
    if p not in sys.path:
        sys.path.insert(0, p)


def enable(name):
    """Enable a vendored add-on in this background, factory-startup Blender session; returns its module."""
    import bpy
    import addon_utils
    if name not in ADDONS:
        raise KeyError(f"{name}: not vendored ({sorted(ADDONS)})")
    if not bpy.app.factory_startup:
        raise RuntimeError("vendor.enable: start Blender with -b --factory-startup; the person's own Blender "
                           "setup must stay unchanged")
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError(f"vendored Blender packages are cp313, this is {sys.version}")
    _path(BL_SITE)
    _path(BL_ADDONS)
    mod = addon_utils.enable(name, default_set=True, persistent=False, handle_error=None)
    if mod is None:
        raise RuntimeError(f"{name}: addon_utils.enable failed (see the console)")
    return mod


def opensim():
    """Import OpenSim from the vendored wheel (system Python 3.12)."""
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError(f"the vendored OpenSim wheel is cp312, this is {sys.version}")
    _path(PY_SITE)
    if hasattr(os, "add_dll_directory"):
        for d in (PY_SITE / "opensim", PY_SITE / "bin"):
            if d.is_dir():
                os.add_dll_directory(str(d))
    import opensim as osim
    return osim
