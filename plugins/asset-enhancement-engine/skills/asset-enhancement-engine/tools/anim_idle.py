# Blender-side: an 8 s idle + meow action for the felid rig (24 fps). Directions were MEASURED on the rig
# (pose_test): lid_up closes with -X, lid_lo closes with +X, jaw opens with -X, closed mouth = +2.3 deg.
# Breathing, tail wave + flick, ear twitch/swivel/perk, blinks, eye saccades, head turns, whisker twitch, meow.
import bpy, math
import numpy as np

PREFIX = globals().get("PREFIX", "Cat")
FPS, END = 24, 192
rig = bpy.data.objects[f"{PREFIX}_Rig"]
sc = bpy.context.scene
sc.render.fps, sc.frame_start, sc.frame_end = FPS, 1, END
if rig.animation_data and rig.animation_data.action:
    old = rig.animation_data.action
    rig.animation_data.action = None
    bpy.data.actions.remove(old)
rig.animation_data_create()
act = bpy.data.actions.new(f"{PREFIX}_Idle_Meow")
rig.animation_data.action = act
pb = rig.pose.bones
for p in pb:
    p.rotation_mode = 'XYZ'
    p.rotation_euler = (0, 0, 0)

CLOSED_JAW = float(globals().get("CLOSED_JAW", 0.5))  # v27: rest = closed (thin lip zone); v22-v26 3.0: lips_seal shape key (lip_seal.py) closes the remaining gap; 4.5 alone left a dark line


def key(bone, frame, rx=0.0, ry=0.0, rz=0.0):
    b = pb[bone]
    b.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    b.keyframe_insert("rotation_euler", frame=frame)


def curve(bone, fn, step=2):
    for f in range(1, END + 1, step):
        key(bone, f, *fn(f / FPS))


def pulse(t, t0, dur):
    """smooth 0->1->0 bump starting at t0 lasting dur seconds"""
    u = (t - t0) / dur
    return math.sin(math.pi * u) ** 2 if 0 <= u <= 1 else 0.0


def env(t, t0, t1, ramp=0.12):
    """0->1 hold ->0 between t0 and t1 with smooth ramps"""
    a = min(max((t - t0) / ramp, 0), 1); b = min(max((t1 - t) / ramp, 0), 1)
    s = min(a, b)
    return s * s * (3 - 2 * s)


MEOW = (5.0, 5.9)
# breathing (spine) + head turns / meow lift
curve("spine1", lambda t: (0.8 * math.sin(2 * math.pi * t / 3.2), 0, 0))
curve("spine2", lambda t: (-0.6 * math.sin(2 * math.pi * t / 3.2 + 0.4), 0, 0))
curve("neck2", lambda t: (6 * env(t, *MEOW, 0.25) + 2 * math.sin(2 * math.pi * t / 7.0), 0,
                          10 * math.sin(2 * math.pi * (t - 0.6) / 8.0) * (1 - 0.6 * env(t, *MEOW, 0.3))), step=2)
curve("head", lambda t: (4 * env(t, *MEOW, 0.2), 4 * math.sin(2 * math.pi * t / 5.5), 0), step=2)
# tail: travelling wave, amplitude grows toward the tip, plus a flick at 3.4 s
for i in range(8):
    amp = 3 + 2.2 * i
    curve(f"tail{i+1}", lambda t, i=i, amp=amp: (2.5 * math.sin(2 * math.pi * t / 2.6 - 0.55 * i) + (6 * pulse(t, 3.4, 0.5) if i > 4 else 0),
                                              0, amp * math.sin(2 * math.pi * t / 2.6 - 0.55 * i) + (14 * pulse(t, 3.4 + 0.04 * i, 0.45) if i > 3 else 0)))
# ears: right twitch @1.6 s (fast double flick), left swivel toward a sound @3.0-4.2 s, both perk for the meow
curve("ear.R", lambda t: (-14 * pulse(t, 1.6, 0.18) - 10 * pulse(t, 1.85, 0.16) + 5 * env(t, *MEOW), 0, -6 * env(t, *MEOW)), step=1)
curve("ear_tip.R", lambda t: (-18 * pulse(t, 1.62, 0.18) - 12 * pulse(t, 1.87, 0.16), 0, 0), step=1)
curve("ear.L", lambda t: (6 * env(t, *MEOW), -35 * env(t, 3.0, 4.2, 0.18), 6 * env(t, *MEOW)), step=1)
curve("ear_tip.L", lambda t: (-10 * pulse(t, 3.05, 0.2), 0, 0), step=1)
# blinks @2.5 s and @6.8 s (lids meet low: upper travels further)
for side in "RL":
    curve(f"lid_up.{side}", lambda t: (-42 * (pulse(t, 2.5, 0.25) + pulse(t, 6.8, 0.28)) - 6 * env(t, *MEOW), 0, 0), step=1)
    curve(f"lid_lo.{side}", lambda t: (14 * (pulse(t, 2.5, 0.25) + pulse(t, 6.8, 0.28)) + 4 * env(t, *MEOW), 0, 0), step=1)
# eye saccades: hold-and-dart gaze targets (deg about Z = left/right, X = up/down)
gaze = [(0.0, 0, 0), (1.2, 0, 9), (2.2, -3, 9), (3.0, 0, 16), (4.3, 2, -4), (5.0, 4, 0), (6.2, 0, -8), (7.4, 0, 0)]


def eye_fn(t):
    cur = gaze[0]
    for g in gaze:
        if t >= g[0]:
            cur = g
    nxt = next((g for g in gaze if g[0] > t), None)
    if nxt and nxt[0] - t < 0.06:  # 60 ms saccade
        u = 1 - (nxt[0] - t) / 0.06
        return (cur[1] + (nxt[1] - cur[1]) * u, 0, cur[2] + (nxt[2] - cur[2]) * u)
    return (cur[1], 0, cur[2])


for side in "RL":
    curve(f"eye.{side}", eye_fn, step=1)
# meow: jaw opens, tongue curls, whiskers forward, nose wiggles; closed jaw otherwise
curve("jaw", lambda t: (CLOSED_JAW - (CLOSED_JAW + 26) * env(t, MEOW[0] + 0.05, MEOW[1] - 0.1, 0.15)
                        + 6 * pulse(t, MEOW[0] + 0.35, 0.25), 0, 0), step=1)
curve("tongue2", lambda t: (-8 * env(t, *MEOW), 0, 0))
curve("tongue3", lambda t: (-14 * env(t, *MEOW), 0, 0))
for side, s in (("R", -1), ("L", 1)):
    curve(f"whisker.{side}", lambda t, s=s: (-6 * env(t, *MEOW) + 5 * pulse(t, 0.9, 0.2) + 4 * pulse(t, 1.15, 0.15), 0,
                                             s * (-8 * env(t, *MEOW) + 6 * pulse(t, 0.9, 0.2))), step=1)
curve("nose", lambda t: (4 * pulse(t, 0.8, 0.15) + 3 * pulse(t, 1.0, 0.15) + 3 * pulse(t, 4.6, 0.2), 0, 0), step=1)
for fc in (act.fcurves if hasattr(act, "fcurves") else []):
    for kp in fc.keyframe_points:
        kp.interpolation = 'BEZIER'
sc.frame_set(1)
print("action", act.name, "frames", END, "bones keyed", len({fc.data_path.split('"')[1] for fc in act.fcurves}) if hasattr(act, "fcurves") else "?")
