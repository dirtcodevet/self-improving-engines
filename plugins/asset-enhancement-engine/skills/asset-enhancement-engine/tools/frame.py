"""LAYER L1 FRAME (domain-neutral core; numpy only): a simplified, form-giving frame - bone chains with lengths from
a domain pack (e.g. engine/packs/felid/frame_template.json) times ONE size factor, posed by a few angles.

World convention (as the cat engine): metres, +Z up, ground z = 0, the subject faces -Y, its LEFT side is +X.
Body axes from the trunk yaw: f (forward, horizontal), u (up), l = u x f (left).

Pose parameters (dict):
  s                       size factor (all lengths x s)
  hip_c (3)               centre between the hip joints
  yaw, pitch              trunk heading (rad, 0 = facing -Y) and nose-up pitch of the hip->shoulder line
  w_shoulder, w_hip       distance between the left and right shoulder / hip joints (m)
  fore.{R,L}: a_hum, a_rad, a_mc, abd       angles from straight DOWN, + = forward (rad); abd = outward roll
  hind.{R,L}: a_fem, a_tib, a_mt, abd
Digitigrade: the phalanges lie FORWARD on the ground from the metacarpo-/metatarsophalangeal joint.
"""
import json

import numpy as np


def unit(v):
    return v / max(np.linalg.norm(v), 1e-12)


def load_template(path):
    T = json.load(open(path))
    mm = lambda k: T["bones"][k]["len"] / 1000.0
    return T, {k: mm(k) for k in T["bones"]}


def axes(yaw, pitch=0.0):
    f = np.array([np.sin(yaw), -np.cos(yaw), 0.0])            # yaw 0 -> facing -Y
    u = np.array([0.0, 0.0, 1.0])
    l = unit(np.cross(u, f))
    fp = unit(np.cos(pitch) * f + np.sin(pitch) * u)          # pitched trunk direction
    return f, u, l, fp


def limb_dir(angle, abd, f, u, l, side):
    """direction from straight down, rotated forward by angle (in the sagittal plane), then rolled outward by abd"""
    d = -np.cos(angle) * u + np.sin(angle) * f
    out = side * l                                             # outward = toward the subject's own side
    return unit(np.cos(abd) * d + np.sin(abd) * out)


def build(P, B, scap_angle=None, pelvis_drop=0.020):
    """joint positions (world, m) for pose P and base bone lengths B (m, at s = 1)"""
    s = P["s"]
    scap_angle = P.get("scap", np.radians(61)) if scap_angle is None else scap_angle   # fitted when present; default = quiet stance (Fung & Macpherson 1999)
    f, u, l, fp = axes(P["yaw"], P["pitch"])
    J = {}
    hip_c = np.asarray(P["hip_c"], float)
    sh_c = hip_c + fp * P.get("trunk", 0.320 * s)             # shoulder-hip joints (prior: Day & Jayne 2007, 320 mm x s)
    J["hip_c"], J["shoulder_c"] = hip_c, sh_c
    for side, sd in ((-1, "R"), (1, "L")):
        # forelimb
        S = sh_c + l * side * P["w_shoulder"] / 2
        fl = P[f"fore.{sd}"]
        E = S + limb_dir(fl["a_hum"], fl["abd"], f, u, l, side) * B["humerus"] * s
        C = E + limb_dir(fl["a_rad"], fl["abd"], f, u, l, side) * B["radius"] * s
        M = C + limb_dir(fl["a_mc"], fl["abd"] * 0.5, f, u, l, side) * B["metacarpal_seg"] * s
        T = M + f * B["fore_phalanges"] * s * 0.85               # toes forward on the ground
        J.update({f"shoulder.{sd}": S, f"elbow.{sd}": E, f"wrist.{sd}": C, f"mcp.{sd}": M, f"fpaw.{sd}": T})
        # scapula: from the shoulder joint up and back to its dorsal border (the withers)
        J[f"scapula_top.{sd}"] = S + unit(np.cos(scap_angle) * -fp + np.sin(scap_angle) * u - 0.25 * side * l) * B["scapula"] * s
        # hindlimb
        H = hip_c + l * side * P["w_hip"] / 2
        hl = P[f"hind.{sd}"]
        K = H + limb_dir(hl["a_fem"], hl["abd"], f, u, l, side) * B["femur"] * s
        A = K + limb_dir(hl["a_tib"], hl["abd"], f, u, l, side) * B["tibia"] * s
        Mt = A + limb_dir(hl["a_mt"], hl["abd"] * 0.5, f, u, l, side) * B["metatarsal_seg"] * s
        Tt = Mt + f * B["hind_phalanges"] * s * 0.85
        J.update({f"hip.{sd}": H, f"knee.{sd}": K, f"hock.{sd}": A, f"mtp.{sd}": Mt, f"hpaw.{sd}": Tt})
        J[f"calcaneus.{sd}"] = A - unit(limb_dir(hl["a_mt"], 0, f, u, l, side)) * B["calcaneus"] * s
    # spine: sacrum above-behind the hip joints, withers between the scapula tops, a gentle dorsal arch
    pelvis_drop = P.get("pelvis", pelvis_drop)              # croup above the hip joints (fitted; side reference prior)
    sacrum = hip_c + u * pelvis_drop - fp * 0.02 * s
    withers = (J["scapula_top.R"] + J["scapula_top.L"]) / 2
    mid = (sacrum + withers) / 2 + u * 0.012 * s
    J["sacrum"], J["withers"], J["spine_mid"] = sacrum, withers, mid
    return J


BONES = [("shoulder.{s}", "elbow.{s}"), ("elbow.{s}", "wrist.{s}"), ("wrist.{s}", "mcp.{s}"), ("mcp.{s}", "fpaw.{s}"),
         ("shoulder.{s}", "scapula_top.{s}"), ("hip.{s}", "knee.{s}"), ("knee.{s}", "hock.{s}"), ("hock.{s}", "mtp.{s}"),
         ("mtp.{s}", "hpaw.{s}"), ("hock.{s}", "calcaneus.{s}")]
SPINE = [("sacrum", "spine_mid"), ("spine_mid", "withers"), ("hip.R", "hip.L"), ("shoulder.R", "shoulder.L")]


def segments(J):
    segs = [(a.format(s=sd), b.format(s=sd)) for sd in "RL" for a, b in BONES] + SPINE
    return [(a, b, J[a], J[b]) for a, b in segs if a in J and b in J]
