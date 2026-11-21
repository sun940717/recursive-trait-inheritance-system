#!/usr/bin/env python3
"""
form_fusion_lab.py
==================
Two experiments on the skeleton + implicit-surface system (skeleton_sdf_demo.py):
  1. Four new body forms (spider, serpent, jellyfish, crab) next to the quadruped and the biped:
     can the system build them, and where does it fall short?
  2. Fusing forms whose parts do not correspond: what the current rule does on all 15 pairs,
     and three changes tested one on top of the other.
兩個實驗，都建立在骨架＋隱式曲面系統（skeleton_sdf_demo.py）上：
  1. 四種新形體（蜘蛛、蛇、水母、螃蟹），加上原本的四足與二足：系統做不做得出來、哪裡不足？
  2. 部位對不上的形體要怎麼融合：現有規則在全部 15 組配對上的表現，以及逐層疊加的三項改動。

Requires fourier3d_demo.py, fourier_genetics.py and skeleton_sdf_demo.py in the same folder.
Target: Python 3.10.12 · numpy, matplotlib, scikit-image, scipy.
需要同資料夾的 fourier3d_demo.py、fourier_genetics.py、skeleton_sdf_demo.py。

The four fusion rules compared (each adds one thing to the previous) / 比較的四種融合規則（逐層疊加）:
  current   tag matching, one-to-one, same arrangement only; bone genes are world vectors;
            a part whose parent is missing is dropped.
            標籤配對、一對一、排列方式要相同；骨頭基因是世界座標向量；父部位不在就丟掉。
  relative  + relative genes: a part is described relative to what it grows from.
            overall size is one gene; every length and thickness is a fraction of it;
            a part's first bone is a lean angle from its parent's axis; later bones are bends
            relative to the previous bone; mirror / radial placement stays with the part's identity.
            ＋相對基因：部位用「相對於它長出來的地方」來描述。體型是一個基因，長度與粗細都是它的比例；
            第一根骨頭是相對父軸的傾角，之後每根是相對前一根的彎折；鏡像／放射的擺法跟著部位身分走。
  wide      + wider matching for parts still unmatched: tags regardless of arrangement, then shape and
            position (no tags needed), then repeats (several parts may share one partner).
            ＋放寬配對：先不管排列方式只看標籤，再看形狀與位置（不需要標籤），最後允許多個部位共用一個對象。
  graft     + grafting: a part whose parent is missing is attached where that parent would have been,
            instead of being dropped.
            ＋嫁接：父部位不在時，接到父部位原本會在的位置，而不是丟掉。

Baseline with no correspondence at all / 完全不需要對應的基準:
  field blend   average the two distance fields (a phenotype-level morph, not inheritance).
                把兩個距離場平均（表現型層級的變形，不是遺傳）。

Outputs (default ./out_fusion) / 輸出（預設 ./out_fusion）:
  forms_gallery.png      the six founder forms / 六種原始形體
  fusion_children.png    three hard pairs: parents, one child per rule, field blend
                         三組最難的配對：親代、每種規則各一個子代、場混合
  results.json           every number printed by this run / 這次執行印出的所有數字
  <form>.obj / .json     founder meshes and genomes / 原始形體的網格與基因組

Usage / 用法:
  python form_fusion_lab.py
  python form_fusion_lab.py --children 6 --seed 3
"""

from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import fourier3d_demo as fd  # noqa: E402
import fourier_genetics as fg  # noqa: E402
import skeleton_sdf_demo as sk  # noqa: E402
from skeleton_sdf_demo import BonePart, SkeletonGenome  # noqa: E402

TAU = fd.TAU


# =============================================================================
# Part 1 — body forms / 形體
# =============================================================================

def make_part(name, joints, radii, tags, *, parent=None, attach=0.0, mirror=False, radial=0,
              core=False, outline=None, harmonics: int = 6) -> BonePart:
    """joints: positions of the chain (absolute for the root, relative to the attach point otherwise).
    outline: (width, height) of an elliptical cross-section; None = round.
    joints：鏈上各關節的位置（根部位用絕對座標，其他相對於接點）。outline：橢圓截面的（寬, 高）。"""
    j = np.asarray(joints, dtype=float)
    r = np.asarray(radii, dtype=float)
    assert len(j) == len(r), name
    if outline is None:
        detail = np.zeros((harmonics + 1, 2))
        detail[0, 0] = 1.0
    else:
        th = np.linspace(0.0, TAU, 360, endpoint=False)
        c = np.column_stack([outline[0] * np.cos(th), outline[1] * np.sin(th)])
        detail = sk.fit_polar_detail(c, np.hypot(c[:, 0], c[:, 1]).mean(), harmonics)
    return BonePart(
        name=name, offsets=np.diff(j, axis=0), radii=r, blend=float(np.clip(0.3 * r[0], 0.012, 0.05)),
        origin=j[0].copy() if parent is None else np.zeros(3), parent=parent, attach=float(attach),
        mirror=mirror, radial=int(radial), tags=list(tags), is_core=core,
        detail0=detail.copy(), detail1=detail.copy())


def spider() -> SkeletonGenome:
    """About half the size of the quadruped. Tags follow RTIS make_spider_genome.
    大小約為四足的一半。標籤沿用 RTIS 的 make_spider_genome。"""
    parts = [
        make_part("cephalothorax", [(-0.05, 0, 0.32), (0.07, 0, 0.33), (0.19, 0, 0.33), (0.31, 0, 0.32), (0.40, 0, 0.30)],
                  [0.10, 0.15, 0.16, 0.13, 0.07], ["structural", "central"], core=True, outline=(1.2, 0.8)),
        make_part("abdomen", [(0, 0, 0), (-0.14, 0, 0.05), (-0.32, 0, 0.07), (-0.50, 0, 0.03), (-0.60, 0, -0.02)],
                  [0.10, 0.21, 0.25, 0.20, 0.08], ["structural", "secretory"], parent="cephalothorax",
                  attach=0.0, core=True),
        make_part("fang", [(0, 0, 0), (0.05, 0.035, -0.05), (0.07, 0.03, -0.12), (0.06, 0.02, -0.17)],
                  [0.035, 0.03, 0.022, 0.012], ["grasping", "cutting"], parent="cephalothorax",
                  attach=1.0, mirror=True),
    ]
    for k, (att, fwd, extra) in enumerate([(0.85, 0.22, ["front"]), (0.62, 0.08, []),
                                           (0.40, -0.08, []), (0.18, -0.24, ["rear"])]):
        parts.append(make_part(
            f"leg_{k + 1}", [(0, 0, 0), (0.3 * fwd, 0.16, 0.10), (0.7 * fwd, 0.36, 0.16),
                             (1.0 * fwd, 0.52, -0.05), (1.15 * fwd, 0.60, -0.30)],
            [0.04, 0.035, 0.03, 0.024, 0.016], ["motor", "locomotion"] + extra,
            parent="cephalothorax", attach=att, mirror=True, core=True))
    return SkeletonGenome(parts)


def serpent() -> SkeletonGenome:
    """One long chain, no limbs. The body waves up and down only: a midline part must stay on the
    y = 0 plane, so a sideways S-curve cannot be stored (it is a pose, not a body plan).
    一條長鏈、沒有四肢。身體只能上下起伏：中軸部位必須留在 y = 0 平面，
    所以左右的 S 形存不進去（那是姿勢，不是身體藍圖）。"""
    s = np.linspace(0.0, 1.0, 15)
    x = -1.5 + 2.6 * s
    z = 0.14 + 0.06 * np.sin(TAU * 1.5 * s) + 0.5 * np.clip((s - 0.72) / 0.28, 0.0, 1.0) ** 1.4
    torso = make_part("torso", np.column_stack([x, np.zeros_like(s), z]),
                      np.interp(s, [0, 0.3, 0.7, 1], [0.04, 0.13, 0.14, 0.10]),
                      ["structural", "central"], core=True)
    return SkeletonGenome([
        torso,
        make_part("head", [(0, 0, 0), (0.12, 0, 0.02), (0.26, 0, 0.0), (0.36, 0, -0.03)],
                  [0.10, 0.14, 0.12, 0.05], ["sensory", "neural"], parent="torso", attach=1.0,
                  core=True, outline=(1.3, 0.75)),
        make_part("fang", [(0, 0, 0), (0.03, 0.05, -0.06), (0.04, 0.05, -0.14)], [0.025, 0.02, 0.008],
                  ["grasping", "cutting"], parent="head", attach=0.8, mirror=True),
        make_part("tail_tip", [(0, 0, 0), (-0.15, 0, -0.01), (-0.30, 0, 0.0), (-0.42, 0, 0.03)],
                  [0.04, 0.03, 0.02, 0.008], ["motor", "cutting"], parent="torso", attach=0.0),
    ])


def jellyfish() -> SkeletonGenome:
    """Radial body plan: a vertical bell with 8 tentacles and 4 oral arms turned around its axis.
    放射狀的身體藍圖：垂直的鐘形體，8 條觸手與 4 條口腕繞著它的軸排列。"""
    return SkeletonGenome([
        make_part("bell", [(0, 0, 0.95), (0, 0, 0.85), (0, 0, 0.72), (0, 0, 0.58), (0, 0, 0.48)],
                  [0.10, 0.34, 0.48, 0.52, 0.40], ["structural", "central"], core=True),
        make_part("tentacle", [(0, 0, 0), (0.40, 0, -0.05), (0.47, 0, -0.35), (0.42, 0, -0.70),
                               (0.50, 0, -1.05), (0.45, 0, -1.35)],
                  [0.05, 0.04, 0.03, 0.025, 0.02, 0.012], ["motor", "grasping"], parent="bell",
                  attach=0.9, radial=8, core=True),
        make_part("oral_arm", [(0, 0, 0), (0.10, 0, -0.25), (0.15, 0, -0.55), (0.10, 0, -0.85)],
                  [0.08, 0.06, 0.045, 0.02], ["secretory", "grasping"], parent="bell", attach=1.0, radial=4),
    ])


def crab() -> SkeletonGenome:
    """Wide flat shell (outline 1.7 : 0.55), claws, four leg pairs, eye stalks.
    又寬又扁的甲殼（截面 1.7 : 0.55）、螯、四對腳、眼柄。"""
    parts = [
        make_part("carapace", [(-0.30, 0, 0.30), (-0.15, 0, 0.31), (0, 0, 0.32), (0.15, 0, 0.31), (0.28, 0, 0.30)],
                  [0.18, 0.27, 0.30, 0.27, 0.17], ["structural", "defense", "central"], core=True,
                  outline=(1.7, 0.55)),
        make_part("claw", [(0, 0, 0), (0.12, 0.28, 0.0), (0.36, 0.42, 0.02), (0.58, 0.34, 0.03), (0.74, 0.22, 0.03)],
                  [0.07, 0.06, 0.07, 0.12, 0.04], ["grasping", "cutting"], parent="carapace", attach=0.92,
                  mirror=True, core=True),
    ]
    for k, (att, fwd, extra) in enumerate([(0.72, 0.10, ["front"]), (0.54, 0.03, []),
                                           (0.36, -0.05, []), (0.18, -0.14, ["rear"])]):
        parts.append(make_part(
            f"leg_{k + 1}", [(0, 0, 0), (0.4 * fwd, 0.30, 0.06), (0.8 * fwd, 0.52, 0.10),
                             (fwd, 0.70, -0.10), (1.1 * fwd, 0.78, -0.28)],
            [0.05, 0.045, 0.04, 0.03, 0.015], ["motor", "locomotion"] + extra,
            parent="carapace", attach=att, mirror=True, core=True))
    parts.append(make_part("eye_stalk", [(0, 0, 0), (0.04, 0.10, 0.14), (0.05, 0.11, 0.26)],
                           [0.03, 0.025, 0.04], ["sensory"], parent="carapace", attach=0.97, mirror=True))
    return SkeletonGenome(parts)


# Tags taken from RTIS ontology.py only (cell / organ / part layers). Adopted on 2026-11-15 as the tags
# every form carries from now on; the older prototype tags are kept for reproducing the 11-13 experiments.
# 只用 RTIS ontology.py 裡的標籤（細胞／器官／部位層）。2026-11-15 起所有形體都用這套；
# 舊的原型標籤保留，只用來重現 11-13 的實驗。
ONTOLOGY_TAGS = {
    "quadruped": {"body": ["torso", "structural", "central"], "neck_head": ["head", "sensor"], "tail": ["tail", "structural"],
                  "leg_front": ["limb", "locomotion", "motor_organ"], "leg_rear": ["limb", "locomotion", "motor_organ"]},
    "biped": {"body": ["torso", "structural", "central"], "neck_head": ["head", "sensor"], "tail": ["tail", "structural"],
              "leg_rear": ["limb", "locomotion", "motor_organ"], "arm_front": ["limb", "grasping", "end_effector"],
              "horn": ["weapon_part", "cutting", "defense_organ"]},
    "spider": {"cephalothorax": ["torso", "structural", "central"], "abdomen": ["structural", "secretion_organ"],
               "fang": ["weapon_part", "cutting", "grasping"],
               **{f"leg_{k}": ["limb", "locomotion", "motor_organ"] for k in range(1, 5)}},
    "serpent": {"torso": ["torso", "structural", "central"], "head": ["head", "sensor"],
                "fang": ["weapon_part", "cutting", "grasping"], "tail_tip": ["tail", "motor_organ"]},
    "jellyfish": {"bell": ["torso", "structural", "central"], "tentacle": ["appendage", "grasping", "motor_organ"],
                  "oral_arm": ["appendage", "grasping", "secretion_organ"]},
    "crab": {"carapace": ["torso", "shell", "defense_organ", "central"], "claw": ["limb", "grasping", "cutting", "end_effector"],
             **{f"leg_{k}": ["limb", "locomotion", "motor_organ"] for k in range(1, 5)},
             "eye_stalk": ["sensory_cluster", "sensor"]},
}


def all_forms(ontology_tags: bool = False) -> dict[str, SkeletonGenome]:
    """The six founder forms. ontology_tags=True gives the adopted tags (ONTOLOGY_TAGS); False gives the
    prototype tags used up to 2026-11-14, so older experiments reproduce unchanged.
    六種原始形體。ontology_tags=True 用已採用的標籤；False 用 11-14 以前的原型標籤，讓舊實驗可以照樣重現。"""
    bones = {"body": 9, "arm_front": 4, "horn": 3}
    forms = {
        "quadruped": sk.tube_genome_to_skeleton(fd.default_genome(), bones=bones),
        "biped": sk.tube_genome_to_skeleton(fg.biped_genome(), bones=bones),
        "spider": spider(), "serpent": serpent(), "jellyfish": jellyfish(), "crab": crab(),
    }
    if ontology_tags:
        forms = {n: SkeletonGenome([dataclasses.replace(p, tags=list(ONTOLOGY_TAGS[n][p.name])) for p in g.parts])
                 for n, g in forms.items()}
    return forms


def thin_report(g: SkeletonGenome, voxel: float) -> int:
    """Number of joints thinner than the grid can resolve (they get thickened to 0.9 voxel).
    比格點解析度還細的關節數（會被加粗到 0.9 格）。"""
    return int(sum((p.radii < 0.9 * voxel).sum() for p in g.parts))


# =============================================================================
# Part 2a — relative genes / 相對基因
# =============================================================================

def unit(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-12)


def body_scale(g: SkeletonGenome) -> float:
    """The size gene: diagonal of the box around the whole skeleton, copies included.
    (First attempt was the length of the root chain. That fails for a jellyfish, whose bell is short
    and whose tentacles are three times longer: a serpent-sized child got tentacles 8 units long.)
    體型基因：包住整副骨架（含鏡像與放射複本）的盒子對角線。
    （第一版用根部位的鏈長，遇到水母就壞了：鐘形體很短、觸手是它的三倍長，
    蛇體型的子代長出 8 單位長的觸手。）"""
    pts = np.vstack([np.vstack([s.a, s.b]) for pc in sk.develop_segments(g, False) for s in pc["segments"]])
    return float(np.linalg.norm(pts.max(axis=0) - pts.min(axis=0)))


def chains(g: SkeletonGenome) -> dict[str, dict]:
    """World joints and frame normals of every part (base copy). / 每個部位的世界座標關節與標架法線。"""
    out: dict[str, dict] = {}
    for p in g.parts:
        start = (np.asarray(p.origin, float) if p.parent is None
                 else sk.point_on_chain(out[p.parent]["joints"], p.attach))
        joints = sk.chain_joints(p, start)
        _, nrm, _ = fd.rotation_minimizing_frames(joints)
        out[p.name] = {"joints": joints, "nrm": nrm}
    return out


def frame_at(chain: dict, attach: float):
    """(tangent, normal, binormal) of a parent chain at an attach position.
    父鏈在接點處的（切線、法線、副法線）。"""
    j = chain["joints"]
    u = float(np.clip(attach, 0.0, 1.0)) * (len(j) - 1)
    i = min(int(np.floor(u)), len(j) - 2)
    t = unit(j[i + 1] - j[i])
    n = chain["nrm"][i] - (chain["nrm"][i] @ t) * t
    if np.linalg.norm(n) < 1e-9:
        n = np.cross(t, [0.0, 1.0, 0.0])
    n = unit(n)
    return t, n, np.cross(t, n)


def _start_normal(h: np.ndarray, pframe) -> np.ndarray:
    """First frame normal of a chain: perpendicular to its heading, leaning towards the parent's axis
    (for the root: towards world up). 鏈的起始法線：垂直於第一根骨頭，朝向父軸（根部位則朝世界的上方）。"""
    candidates = ([pframe[0], pframe[1]] if pframe is not None
                  else [np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0])])
    for c in candidates:
        v = c - (c @ h) * h
        if np.linalg.norm(v) > 1e-6:
            return unit(v)
    return unit(np.cross(h, [0.0, 1.0, 0.0]))


def _transport(n: np.ndarray, t_old: np.ndarray, t_new: np.ndarray) -> np.ndarray:
    """Carry the normal along by the smallest rotation that turns t_old into t_new.
    用把 t_old 轉到 t_new 的最小旋轉，把法線帶過去。"""
    v = np.cross(t_old, t_new)
    s = float(np.linalg.norm(v))
    if s < 1e-12:
        return n
    return unit(sk.rotation_about(v / s, float(np.arctan2(s, t_old @ t_new))) @ n)


def encode(p: BonePart, pframe, scale: float) -> dict:
    """World offsets -> relative genes. pframe = parent's frame at the attach point (None for the root).
    世界座標 -> 相對基因。"""
    lengths = np.linalg.norm(p.offsets, axis=1)
    dirs = p.offsets / (lengths[:, None] + 1e-12)
    h = dirs[0]
    rel = {"lengths": lengths / scale, "radii": p.radii / scale, "blend": p.blend / scale}
    if pframe is None:
        rel["heading"] = h.copy()                      # the root's orientation in the world / 根部位的朝向
    else:
        t_p, n_p, b_p = pframe
        along = float(h @ t_p)
        w = h - along * t_p
        rad = float(np.linalg.norm(w))
        rel["lean"] = float(np.arctan2(rad, along))    # 0 = along the parent's axis, 90 deg = straight out
        rel["azimuth"] = float(np.arctan2(w @ b_p, w @ n_p)) if rad > 1e-9 else 0.0
    n = _start_normal(h, pframe)
    t, bends = h, []
    for d in dirs[1:]:
        b = np.cross(t, n)
        bends.append([d @ t, d @ n, d @ b])            # the next bone seen from the previous one
        n, t = _transport(n, t, d), d
    rel["bends"] = np.array(bends).reshape(-1, 3)
    return rel


def decode(rel: dict, pframe, scale: float, arrange: str, azimuth: float | None) -> dict:
    """Relative genes -> world offsets in the child's own context.
    Parts that are not mirrored are kept on the symmetry plane.
    相對基因 -> 在子代自己的環境裡的世界座標。非鏡像的部位會留在對稱面上。"""
    planar = arrange != "mirror"
    if pframe is None:
        h = np.array(rel["heading"], dtype=float)
        h[1] = 0.0
        h = unit(h)
    else:
        t_p, n_p, b_p = pframe
        az = float(azimuth)
        if planar:
            az = 0.0 if np.cos(az) >= 0.0 else np.pi
        h = unit(np.cos(rel["lean"]) * t_p + np.sin(rel["lean"]) * (np.cos(az) * n_p + np.sin(az) * b_p))
    n = _start_normal(h, pframe)
    t, dirs = h, [h]
    for loc in rel["bends"]:
        b = np.cross(t, n)
        d = loc[0] * t + loc[1] * n + (0.0 if planar else loc[2]) * b
        d = unit(d) if np.linalg.norm(d) > 1e-9 else t
        dirs.append(d)
        n, t = _transport(n, t, d), d
    return {"offsets": np.array(dirs) * (rel["lengths"] * scale)[:, None],
            "radii": rel["radii"] * scale, "blend": float(rel["blend"] * scale)}


# =============================================================================
# Part 2b — matching / 配對
# =============================================================================

@dataclass
class FuseOptions:
    relative: bool = False
    wide: bool = False
    graft: bool = False
    # Bead fixes (only with relative genes) / 念珠問題的修法（只在相對基因下有效）
    linkage: int = 0          # > 0: genes along a chain are inherited in runs, with this many switch points
    #                           > 0：沿著鏈的基因成段遺傳，中間有這麼多個交換點
    thickness: str = "joint"  # "joint": each joint's thickness is its own gene (the 11-13 behaviour)
    #                           "ratio": thickness is stored as a ratio of the neighbouring bone length
    #                           "pack" : the whole thickness profile of a part comes from one parent
    # Crowding fix (2026-11-14) / 擁擠問題的修法
    site_rule: bool = False   # an unmatched part that would swallow, or be swallowed by, a part already
    #                           placed competes with it for the site: only one of the two stays
    #                           沒配對的部位如果會吞掉（或被吞掉）已經放好的部位，兩者競爭同一個位置，只留一個


RULES = {"current": FuseOptions(), "relative": FuseOptions(relative=True),
         "wide": FuseOptions(relative=True, wide=True),
         "graft": FuseOptions(relative=True, wide=True, graft=True)}
SHAPE_THRESHOLD = 0.35     # heuristic, not tuned on results / 經驗值，沒有針對結果調整
# The rule set adopted as of 2026-11-15 (matching is done separately, see soft_match_lab.soft_match).
# 2026-11-15 為止採用的整套規則（配對另外做，見 soft_match_lab.soft_match）。
ADOPTED = FuseOptions(relative=True, graft=True, linkage=1, site_rule=True)


def descriptors(g: SkeletonGenome) -> dict[str, np.ndarray]:
    """Tag-free description of each non-root part: where it attaches, whether it runs along the parent's
    axis or sticks out, how long it is relative to the body, how slender it is, how deep in the tree.
    不靠標籤的部位描述：接在哪、沿著父軸還是往外伸、相對身體多長、多細長、在樹上多深。"""
    ch, scale = chains(g), body_scale(g)
    depth = {g.parts[0].name: 0}
    out = {}
    for p in g.parts[1:]:
        depth[p.name] = depth[p.parent] + 1
        t_p, _, _ = frame_at(ch[p.parent], p.attach)
        length = float(np.linalg.norm(p.offsets, axis=1).sum())
        axial = abs(float(unit(p.offsets.sum(axis=0)) @ t_p))
        out[p.name] = np.array([p.attach, axial, np.log(length / scale),
                                np.log(length / float(p.radii.mean())), depth[p.name]])
    return out


def shape_similarity(da: np.ndarray, db: np.ndarray) -> float:
    widths = np.array([0.3, 0.4, 0.7, 0.7, 1.0])
    return float(np.exp(-0.5 * np.sum(((da - db) / widths) ** 2)))


def match(ga: SkeletonGenome, gb: SkeletonGenome, cfg, wide: bool) -> list[dict]:
    """Returns pairs [{a, b, score, how}]. With wide=False this is exactly sk.match_parts.
    wide=False 時與 sk.match_parts 完全相同。"""
    pairs = [{"a": na, "b": nb, "score": float(s), "how": "tags"}
             for na, (nb, s) in sk.match_parts(ga, gb, cfg).items()]
    if not wide:
        return pairs
    used_a, used_b = {p["a"] for p in pairs}, {p["b"] for p in pairs}
    rest_a = [p for p in ga.parts if p.name not in used_a]
    rest_b = [p for p in gb.parts if p.name not in used_b]

    def greedy(cands, how):
        for s, na, nb in sorted(cands, key=lambda c: -c[0]):
            if na not in used_a and nb not in used_b:
                pairs.append({"a": na, "b": nb, "score": float(s), "how": how})
                used_a.add(na)
                used_b.add(nb)

    def tag_score(pa, pb):
        s = fg.tag_similarity(pa.tags, pb.tags)
        return None if s < cfg.match_threshold else s + 0.25 * (1.0 - abs(pa.attach - pb.attach))

    # pass 2: tags, any arrangement (a mirrored leg may pair with a radial tentacle)
    greedy([(s, pa.name, pb.name) for pa in rest_a for pb in rest_b
            if (s := tag_score(pa, pb)) is not None], "tags, any arrangement")
    # pass 3: shape and position, no tags needed
    da, db = descriptors(ga), descriptors(gb)
    greedy([(s, pa.name, pb.name) for pa in rest_a for pb in rest_b
            if (s := shape_similarity(da[pa.name], db[pb.name])) >= SHAPE_THRESHOLD], "shape and position")
    # pass 4: repeats — a leftover part may share a partner that is already taken (serial repeats, e.g.
    # four leg pairs against two)
    for rest, others, side in ((rest_a, gb.parts[1:], "a"), (rest_b, ga.parts[1:], "b")):
        for p in rest:
            if p.name in (used_a if side == "a" else used_b):
                continue
            best = max(((tag_score(p, q) if side == "a" else tag_score(q, p)) or -1.0, q.name) for q in others)
            if best[0] > 0:
                pair = ({"a": p.name, "b": best[1]} if side == "a" else {"a": best[1], "b": p.name})
                pairs.append({**pair, "score": float(best[0]), "how": "repeat"})
                (used_a if side == "a" else used_b).add(p.name)
    return pairs


def coverage(ga: SkeletonGenome, gb: SkeletonGenome, pairs: list[dict]) -> float:
    """Share of all non-root parts (both parents) that have a partner. / 兩親代所有非根部位中有對象的比例。"""
    a, b = {p["a"] for p in pairs}, {p["b"] for p in pairs}
    total = len(ga.parts) + len(gb.parts) - 2
    return (len(a) + len(b) - 2) / total if total else 1.0


# =============================================================================
# Part 2c — fusion / 融合
# =============================================================================

def _local_length(lengths: np.ndarray) -> np.ndarray:
    """Bone length around each joint (mean of the two neighbours; one neighbour at the ends).
    每個關節附近的骨頭長度（兩側平均；端點只有一側）。"""
    return np.concatenate([[lengths[0]], (lengths[:-1] + lengths[1:]) / 2.0, [lengths[-1]]])


def visible_profile(part: BonePart, per_bone: int = 12) -> np.ndarray:
    """Radius of the skin actually seen along a chain, sampled densely: the cone between joints, or the
    ball of any nearby joint if that reaches further. A thin joint next to a fat one is hidden.
    沿著鏈密集取樣、實際看得到的半徑：關節之間的圓錐，或附近關節的球（取較大者）。"""
    pos = np.concatenate([[0.0], np.cumsum(np.linalg.norm(part.offsets, axis=1))])
    s = np.linspace(0.0, pos[-1], per_bone * part.n_bones + 1)
    ball = np.sqrt(np.maximum(part.radii[None, :] ** 2 - (s[:, None] - pos[None, :]) ** 2, 0.0)).max(axis=1)
    return np.maximum(np.interp(s, pos, part.radii), ball)


def beads(part: BonePart, prominence: float = 1.05) -> int:
    """Number of humps along a chain: peaks of the visible outline that stand at least 5% above the
    dips on both sides (5% is about the shallowest crease you can see). A plain body has 1; a string
    of four balls has 4.
    (The first version, 2026-11-14, only compared each joint with its two neighbours and missed
    balls separated by several thin joints.)
    一條鏈上的隆起數：看得到的輪廓上，比兩側凹處高出至少 5% 的峰（5% 大約是看得出來的最淺凹痕）。
    普通的身體是 1，四顆球串在一起是 4。"""
    from scipy.signal import find_peaks
    lr = np.log(visible_profile(part))
    padded = np.concatenate([[lr.min() - 1.0], lr, [lr.min() - 1.0]])
    return int(len(find_peaks(padded, prominence=np.log(prominence))[0]))


def _buried(p_segs, q_segs, start: float = 0.25, per_bone: int = 8) -> float:
    """Share of limb P's centreline (from `start` of its length outward) that lies inside limb Q.
    肢體 P 的中心線（從長度的 start 處往外）有多少比例落在肢體 Q 裡面。"""
    pts = []
    for s in p_segs:
        for u in np.linspace(0.0, 1.0, per_bone, endpoint=False):
            if s.sa + u * (s.sb - s.sa) >= start:
                pts.append(s.a + u * (s.b - s.a))
    pts.append(p_segs[-1].b)
    pts = np.asarray(pts)
    d = np.min([sk.sd_round_cone(pts, q.a, q.b, q.ra, q.rb) for q in q_segs], axis=0)
    return float(np.mean(d < 0.0))


def crowding(g: SkeletonGenome, only: str | None = None) -> dict:
    """Pairs of different limbs (by gene name) where one is swallowed by the other: at least half of the
    outer three quarters of one limb's centreline lies inside the other. The root part and a part's own
    ancestors are not counted. only = a gene name: check only pairs that involve it.
    一條被另一條吞掉的肢體組合（以基因名稱計）：其中一條外側四分之三的中心線有一半以上落在另一條裡面。
    根部位與自己的祖先部位不算。only＝基因名稱時只檢查跟它有關的組合。"""
    parent = {p.name: p.parent for p in g.parts}

    def ancestors(n):
        out = set()
        while parent[n] is not None:
            n = parent[n]
            out.add(n)
        return out

    pieces = [pc for pc in sk.develop_segments(g, use_detail=False) if parent[pc["gene"]] is not None]
    swallowed = set()
    for pi, pj in itertools.combinations(pieces, 2):
        gi, gj = pi["gene"], pj["gene"]
        if gi == gj or gi in ancestors(gj) or gj in ancestors(gi) or (only is not None and only not in (gi, gj)):
            continue
        if max(_buried(pi["segments"], pj["segments"]), _buried(pj["segments"], pi["segments"])) >= 0.5:
            swallowed.add(tuple(sorted((gi, gj))))
    return {"swallowed": sorted(swallowed)}


def turning(offsets: np.ndarray) -> float:
    """Total bend of a chain in degrees. / 一條鏈的總彎折角度（度）。"""
    d = offsets / (np.linalg.norm(offsets, axis=1, keepdims=True) + 1e-12)
    return float(np.degrees(np.arccos(np.clip(np.sum(d[1:] * d[:-1], axis=1), -1.0, 1.0)).sum()))


def fuse(ga: SkeletonGenome, gb: SkeletonGenome, rng: np.random.Generator, cfg, opt: FuseOptions,
         pairs: list[dict] | None = None, exclude: set | None = None, attr=None):
    """One child of A x B under the given rule. No mutation (so only the fusion rule is being compared).
    pairs: optional matching decided by the caller, [{a, b, score, how}], root pair included
    (added 2026-11-14 for soft_match_lab.py). None = use match() as before.
    依指定規則產生 A x B 的一個子代。不做突變（只比較融合規則本身）。
    pairs：可由呼叫者自己決定配對（要包含根部位那一組）；None 則照舊使用 match()。
    exclude, attr (added 2026-11-15, both optional): parent parts to leave out ("A.name"), and an
    attribute_layer.AttributeLayer. A pair dict may also carry "template" / "placement" ("A" or "B") to
    fix which parent gives the part's identity and position. Without them nothing changes.
    exclude、attr（11-15 新增，皆可省略）：要排除的親代部位，以及部位屬性層。配對也可以帶 template／placement
    指定部位身分與位置來自哪一方。不給就完全不變。"""
    exclude = exclude or set()
    if pairs is None:
        pairs = match(ga, gb, cfg, opt.wide)
    A, B = {p.name: p for p in ga.parts}, {p.name: p for p in gb.parts}
    src_parts, src_chain = {"A": A, "B": B}, {"A": chains(ga), "B": chains(gb)}
    src_scale = {"A": body_scale(ga), "B": body_scale(gb)}
    scale_from_a = rng.random() < cfg.alpha
    child_scale = src_scale["A"] if scale_from_a else src_scale["B"]
    by_a: dict[str, list[dict]] = {}
    for pr in pairs:
        by_a.setdefault(pr["a"], []).append(pr)
    paired_b = {pr["b"] for pr in pairs}
    plan = []
    for pa in ga.parts:
        plan += ([("pair", pa, B[pr["b"]], pr) for pr in by_a[pa.name]] if pa.name in by_a
                 else [("single", "A", pa)] if f"A.{pa.name}" not in exclude else [])
    plan += [("single", "B", pb) for pb in gb.parts if pb.name not in paired_b and f"B.{pb.name}" not in exclude]

    child: list[BonePart] = []
    child_chain: dict[str, dict] = {}
    name_map: dict[tuple[str, str], str] = {}
    used: set[str] = set()
    log = {"pairs": len(pairs), "coverage": coverage(ga, gb, pairs), "orphans_dropped": 0, "grafted": 0,
           "not_inherited": 0, "site_lost": 0, "extra_bend": [], "extra_beads": [], "humps": [],
           # record only (added 2026-11-15 for the replay page; changes no result)
           # 只做紀錄（2026-11-15 為重播頁面新增；不改變任何結果）
           "scale_src": "A" if scale_from_a else "B", "genes": {}, "dropped": []}
    p_periph = min(1.0, cfg.inheritance_factor)

    def unique(name):
        base, k = name, 2
        while name in used:
            name, k = f"{base}_{k}", k + 1
        used.add(name)
        return name

    def resolve(options):
        for src, p in options:
            if p.parent is None:
                return None, p.attach
            if (src, p.parent) in name_map:
                return name_map[(src, p.parent)], None
        if not opt.graft:
            return False, None
        src, cur = options[0]                 # graft: climb to the nearest ancestor that exists
        attach = cur.attach
        while True:
            par = src_parts[src][cur.parent]
            if (src, par.name) in name_map:
                return name_map[(src, par.name)], attach
            attach, cur = par.attach, par

    def pframe_of(src, p):
        return None if p.parent is None else frame_at(src_chain[src][p.parent], p.attach)

    def add(part: BonePart):
        child.append(part)
        start = (np.asarray(part.origin, float) if part.parent is None
                 else sk.point_on_chain(child_chain[part.parent]["joints"], part.attach))
        joints = sk.chain_joints(part, start)
        _, nrm, _ = fd.rotation_minimizing_frames(joints)
        child_chain[part.name] = {"joints": joints, "nrm": nrm}

    for entry in plan:
        if entry[0] == "pair":
            _, pa, pb, pr = entry
            core = pa.parent is None or pa.is_core or pb.is_core
            if not core and rng.random() >= 1.0 - (1.0 - p_periph) ** 2:
                log["not_inherited"] += 1
                log["dropped"].append({"parts": [f"A.{pa.name}", f"B.{pb.name}"], "why": "not inherited"})
                continue
            n = max(pa.n_bones, pb.n_bones)
            ra, rb = sk.resample_part(pa, n), sk.resample_part(pb, n)
            if not opt.relative:
                part, info = sk.cross_part(pa, pb, cfg, rng)
                tpl_src = info["template"]
            else:
                tpl_src = "A" if rng.random() < cfg.parent_a_dominance else "B"
                tpl_src = pr.get("template", tpl_src)
            tpl, other = (pa, pb) if tpl_src == "A" else (pb, pa)
            parent, graft_attach = resolve([(tpl_src, tpl), ("B" if tpl_src == "A" else "A", other)])
            if parent is False:
                log["orphans_dropped"] += 1
                log["dropped"].append({"parts": [f"A.{pa.name}", f"B.{pb.name}"], "why": "parent missing"})
                continue
            if opt.relative:
                ea = encode(ra, pframe_of("A", pa), src_scale["A"])
                eb = encode(rb, pframe_of("B", pb), src_scale["B"])
                fa, fb = pa.meta.get("ancestry_a", 0.5), pb.meta.get("ancestry_a", 0.5)
                pick = lambda size=None: rng.random(size) < cfg.alpha           # noqa: E731
                if opt.linkage > 0:
                    # one run of genes per stretch of the chain: joint j, the bone after it and its bend
                    # travel together; the source flips at each switch point
                    # 沿著鏈成段遺傳：關節 j、它後面那根骨頭和彎折一起走；每遇到交換點就換邊
                    src = np.full(n + 1, bool(pick()))
                    for cut in rng.choice(np.arange(1, n + 1), size=min(opt.linkage, n), replace=False):
                        src[cut:] = ~src[cut:]
                    g_head, g_len, g_bend, g_rad = bool(src[0]), src[:n].copy(), src[1:n].copy(), src.copy()
                else:
                    g_head, g_len, g_bend, g_rad = pick(), pick(n), pick(max(n - 1, 0)), pick(n + 1)
                if opt.thickness == "pack":
                    g_rad = np.full(n + 1, bool(pick()))
                g_blend, g_attach, g_detail = pick(), pick(), pick()
                lengths = np.where(g_len, ea["lengths"], eb["lengths"])
                if opt.thickness == "ratio":
                    radii = np.where(g_rad, ea["radii"] / _local_length(ea["lengths"]),
                                     eb["radii"] / _local_length(eb["lengths"])) * _local_length(lengths)
                else:
                    radii = np.where(g_rad, ea["radii"], eb["radii"])
                rel = {"lengths": lengths,
                       "bends": np.where(g_bend[:, None], ea["bends"], eb["bends"]),
                       "radii": radii,
                       "blend": ea["blend"] if g_blend else eb["blend"]}
                e_head = ea if g_head else eb
                if pa.parent is None:
                    rel["heading"] = e_head["heading"]
                else:
                    rel["lean"] = e_head["lean"]
                attach = (pa if g_attach else pb).attach if graft_attach is None or parent is None else graft_attach
                if "placement" in pr and (graft_attach is None or parent is None):
                    attach = (pa if pr["placement"] == "A" else pb).attach
                e_tpl = ea if tpl_src == "A" else eb
                frame = None if parent is None else frame_at(child_chain[parent], attach)
                if attr is not None and parent is not None:
                    def child_exit(r_, frame=frame, attach=attach, parent=parent, arr=sk.arrangement(tpl),
                                   az=e_tpl.get("azimuth")):
                        h = decode(r_, frame, child_scale, arr, az)["offsets"][0]
                        start = sk.point_on_chain(child_chain[parent]["joints"], attach)
                        return attr.exit_distance(child, parent, start, h) / child_scale

                    def src_exit(src, g, p):
                        start = sk.point_on_chain(src_chain[src][p.parent]["joints"], p.attach)
                        return attr.exit_distance(g.parts, p.parent, start, p.offsets[0]) / src_scale[src]
                    rel = attr.adjust_pair(
                        f"A.{pa.name}~B.{pb.name}", rel, ea, eb,
                        None if pa.parent is None else src_exit("A", ga, pa),
                        None if pb.parent is None else src_exit("B", gb, pb), child_exit, pr)
                dec = decode(rel, frame, child_scale, sk.arrangement(tpl), e_tpl.get("azimuth"))
                src_d = pa if g_detail else pb
                picks = np.concatenate([[g_head], g_len, g_bend, g_rad, [g_blend, g_attach, g_detail]])
                part = dataclasses.replace(
                    tpl, offsets=dec["offsets"], radii=dec["radii"], blend=dec["blend"], attach=float(attach),
                    origin=np.asarray(tpl.origin, float) * child_scale / src_scale[tpl_src],
                    detail0=None if src_d.detail0 is None else src_d.detail0.copy(),
                    detail1=None if src_d.detail1 is None else src_d.detail1.copy(),
                    tags=list(tpl.tags), meta={"ancestry_a": float(np.mean(np.where(picks, fa, fb)))})
            elif graft_attach is not None and parent is not None:
                part = dataclasses.replace(part, attach=float(graft_attach))
                log["grafted"] += 1
            name = unique(part.name)
            if attr is not None and f"A.{pa.name}~B.{pb.name}" in attr.log["parts"]:
                attr.log["parts"][name] = attr.log["parts"].pop(f"A.{pa.name}~B.{pb.name}")
            add(dataclasses.replace(part, name=name, parent=parent))
            name_map.setdefault(("A", pa.name), name)
            name_map.setdefault(("B", pb.name), name)
            log["extra_bend"].append(max(0.0, turning(child[-1].offsets) - max(turning(ra.offsets), turning(rb.offsets))))
            log["extra_beads"].append(max(0, beads(child[-1]) - max(beads(ra), beads(rb))))
            log["humps"].append(beads(child[-1]))
            if opt.relative:
                b2l = lambda v: [bool(x) for x in np.atleast_1d(v)]   # noqa: E731  True = from A / True＝來自 A
                log["genes"][name] = {"template": tpl_src, "head": bool(g_head), "lengths": b2l(g_len),
                                      "bends": b2l(g_bend), "radii": b2l(g_rad), "blend": bool(g_blend),
                                      "attach": bool(g_attach), "detail": bool(g_detail)}
        else:
            _, src, p = entry
            keep = (cfg.core_lock if src == "A" else cfg.core_lock * 0.5) if p.is_core else p_periph
            if rng.random() >= keep:
                log["not_inherited"] += 1
                log["dropped"].append({"parts": [f"{src}.{p.name}"], "why": "not inherited"})
                continue
            parent, graft_attach = resolve([(src, p)])
            if parent is False:
                log["orphans_dropped"] += 1
                log["dropped"].append({"parts": [f"{src}.{p.name}"], "why": "parent missing"})
                continue
            attach = p.attach if graft_attach is None else graft_attach
            if graft_attach is not None and (src, p.parent) not in name_map:
                log["grafted"] += 1
            if opt.relative:
                rel = encode(p, pframe_of(src, p), src_scale[src])
                frame = frame_at(child_chain[parent], attach)
                if attr is not None:
                    def child_exit(r_, frame=frame, attach=attach, parent=parent, arr=sk.arrangement(p),
                                   az=rel.get("azimuth")):
                        h = decode(r_, frame, child_scale, arr, az)["offsets"][0]
                        start = sk.point_on_chain(child_chain[parent]["joints"], attach)
                        return attr.exit_distance(child, parent, start, h) / child_scale
                    g_src = ga if src == "A" else gb
                    own = attr.exit_distance(g_src.parts, p.parent,
                                             sk.point_on_chain(src_chain[src][p.parent]["joints"], p.attach),
                                             p.offsets[0]) / src_scale[src]
                    rel = attr.adjust_single(f"{src}.{p.name}", rel, own, child_exit)
                dec = decode(rel, frame, child_scale, sk.arrangement(p), rel.get("azimuth"))
                part = dataclasses.replace(p, offsets=dec["offsets"], radii=dec["radii"], blend=dec["blend"],
                                           attach=float(attach), tags=list(p.tags), meta=dict(p.meta))
            else:
                part = dataclasses.replace(p, offsets=p.offsets.copy(), radii=p.radii.copy(),
                                           attach=float(attach), tags=list(p.tags), meta=dict(p.meta))
            name = unique(p.name)
            if attr is not None and f"{src}.{p.name}" in attr.log["parts"]:
                attr.log["parts"][name] = attr.log["parts"].pop(f"{src}.{p.name}")
            part = dataclasses.replace(part, name=name, parent=parent)
            if opt.site_rule:
                # Two limbs in one place: the one already there and the newcomer compete for the site.
                # A core part beats a peripheral one; a part that already carries other parts cannot be
                # removed; otherwise a coin decides.
                # 同一個位置有兩條肢體：先到的和後到的競爭。核心部位贏過周邊部位；已經長了其他部位的不能移除；
                # 其餘擲硬幣。
                rivals = [n for key in crowding(SkeletonGenome(child + [part]), only=name)["swallowed"]
                          for n in key if n != name]
                if rivals:
                    by_name = {c.name: c for c in child}
                    fixed = any(by_name[r].is_core and not p.is_core for r in rivals) or \
                        any(c.parent in rivals for c in child)
                    wins = (not fixed) and (p.is_core and not any(by_name[r].is_core for r in rivals)
                                            or rng.random() < 0.5)
                    log["site_lost"] += 1 if not wins else len(rivals)
                    if not wins:
                        log["dropped"].append({"parts": [f"{src}.{p.name}"], "why": f"lost the site to {', '.join(rivals)}"})
                        continue
                    for r in rivals:
                        srcs = [k for k, v in name_map.items() if v == r]
                        log["dropped"].append({"parts": [f"{a}.{b}" for a, b in srcs] or [r],
                                               "why": f"lost the site to {src}.{p.name}"})
                    for r in rivals:
                        child.remove(by_name[r])
                        del child_chain[r]
                        for k in [k for k, v in name_map.items() if v == r]:
                            del name_map[k]
            add(part)
            name_map.setdefault((src, p.name), name)
            log["genes"][name] = {"template": src, "single": True}
    # which child part each parent part ended up in (added 2026-11-14) / 每個親代部位最後變成子代的哪個部位
    log["sources"] = {f"{src}.{name}": child_name for (src, name), child_name in name_map.items()}
    return sk.enforce_symmetry(SkeletonGenome(child)), log


def shells(mesh) -> tuple[int, int]:
    """(outer shells, enclosed bubbles). A connected surface with negative volume is a bubble of empty
    space sealed inside the body, not a separate piece of the creature.
    （外殼數、內部氣泡數）。體積為負的連通曲面是封在身體裡的空洞，不是另一塊身體。"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    f, n = mesh.faces, len(mesh.vertices)
    graph = coo_matrix((np.ones(len(f) * 3, dtype=np.int8),
                        (np.r_[f[:, 0], f[:, 1], f[:, 2]], np.r_[f[:, 1], f[:, 2], f[:, 0]])), shape=(n, n))
    _, label = connected_components(graph, directed=False)
    face_label = label[f[:, 0]]
    vols = [fd.signed_volume(fd.Mesh(mesh.vertices, f[face_label == c])) for c in np.unique(face_label)]
    return sum(v > 0 for v in vols), sum(v <= 0 for v in vols)


def ancestry_share(g: SkeletonGenome) -> float:
    """Gene-weighted share of parent A in a creature. / 以基因數加權的 A 血緣比例。"""
    w = np.array([p.gene_count() for p in g.parts], dtype=float)
    a = np.array([p.meta.get("ancestry_a", 0.5) for p in g.parts])
    return float((w * a).sum() / w.sum())


# =============================================================================
# Baseline: field blend / 基準：場混合
# =============================================================================

def field_blend(ga: SkeletonGenome, gb: SkeletonGenome, voxel: float = 0.03, t: float = 0.5):
    """Average the two exact distance fields after putting the two bounding-box centres together.
    Needs no correspondence. The result has no genome, so it cannot be bred further.
    把兩個形體的包圍盒中心對齊後，平均兩個精確距離場。完全不需要對應；結果沒有基因組，不能繼續繁殖。"""
    def setup(g):
        segs = [s for pc in sk.develop_segments(g, False) for s in pc["segments"]]
        pts = np.vstack([np.vstack([s.a, s.b]) for s in segs])
        r = max(max(s.ra, s.rb) for s in segs)
        centre = (pts.min(axis=0) + pts.max(axis=0)) / 2.0
        return segs, centre, pts.min(axis=0) - centre - r, pts.max(axis=0) - centre + r
    sa, ca, lo_a, hi_a = setup(ga)
    sb, cb, lo_b, hi_b = setup(gb)
    lo = np.minimum(lo_a, lo_b) - 4 * voxel
    hi = np.maximum(hi_a, hi_b) + 4 * voxel
    axes = [np.arange(lo[d], hi[d] + voxel, voxel) for d in range(3)]
    p = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)

    def dist(segs, centre):
        d = np.full(p.shape[:3], np.inf)
        for s in segs:
            d = np.minimum(d, sk.sd_round_cone(p + centre, s.a, s.b, max(s.ra, 0.9 * voxel), max(s.rb, 0.9 * voxel)))
        return d
    da, db = dist(sa, ca), dist(sb, cb)
    cell = voxel ** 3
    info = {"volume_a": float((da < 0).sum() * cell), "volume_b": float((db < 0).sum() * cell)}
    field = (1.0 - t) * da + t * db
    if not (field < 0).any():
        return None, {**info, "empty": True}
    mesh = sk.extract_mesh(field, lo, voxel)
    return mesh, {**info, **sk.mesh_report(mesh), "empty": False}


# =============================================================================
# Main / 主程式
# =============================================================================

HARD_PAIRS = [("spider", "jellyfish"), ("serpent", "crab"), ("quadruped", "jellyfish")]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="New body forms and fusion of forms that do not correspond")
    ap.add_argument("--out", default="out_fusion")
    ap.add_argument("--voxel", type=float, default=0.015, help="grid for founder meshes / 原始形體用的格點")
    ap.add_argument("--preview-voxel", type=float, default=0.03, help="grid for children and figures")
    ap.add_argument("--children", type=int, default=3, help="children per pair per rule / 每組每種規則的子代數")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pv = args.preview_voxel
    report: dict = {"voxel": args.voxel, "preview_voxel": pv, "children_per_cell": args.children, "seed": args.seed}

    # ---- Part 1: forms -------------------------------------------------------------------------
    forms = all_forms()
    print("Part 1 - body forms / 形體")
    print(f"{'form':<11}{'parts':>6}{'genes':>7}{'pieces':>8}{'closed':>8}{'triangles':>11}{'build s':>9}"
          f"{'size':>7}{'thin joints':>13}")
    report["forms"] = {}
    for name, g in forms.items():
        t0 = time.perf_counter()
        mesh, _, pieces = sk.build_sdf_creature(g, args.voxel)
        dt = time.perf_counter() - t0
        rep = sk.mesh_report(mesh)
        row = {"parts": len(g.parts), "genes": g.gene_count(), "bone_chains": len(pieces), **rep,
               "build_seconds": round(dt, 2), "body_size": round(body_scale(g), 3),
               "thin_joints_export": thin_report(g, args.voxel), "thin_joints_preview": thin_report(g, pv)}
        report["forms"][name] = row
        print(f"{name:<11}{row['parts']:>6}{row['genes']:>7}{rep['components']:>8}{str(rep['closed']):>8}"
              f"{rep['triangles']:>11}{dt:>9.2f}{row['body_size']:>7.2f}"
              f"{row['thin_joints_export']:>6} /{row['thin_joints_preview']:>3}")
        fd.write_obj(out / f"{name}.obj", [(name, mesh)])
        (out / f"{name}.json").write_text(json.dumps(g.to_json(), indent=1), encoding="utf-8")
    print("  thin joints: at the export grid / at the preview grid (these get thickened)")

    names = list(forms)
    fig = plt.figure(figsize=(15, 8.4))
    fig.suptitle("Six founder forms in the skeleton + implicit-surface system (each is one closed mesh)", fontsize=13)
    for i, name in enumerate(names):
        ax = fig.add_subplot(2, 3, i + 1, projection="3d")
        m, _, _ = sk.build_sdf_creature(forms[name], 0.02)
        r = report["forms"][name]
        sk.draw_mesh(ax, m, np.tile(sk.GREY, (len(m.faces), 1)),
                     f"{name}: {r['parts']} parts, {r['genes']} genes", light=(0.5, -0.6, 0.7))
        ax.view_init(elev=20, azim=-58)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.92, bottom=0.0, wspace=0.0, hspace=0.06)
    fig.savefig(out / "forms_gallery.png", dpi=110)
    plt.close(fig)

    # ---- Part 2: matching coverage on all pairs ---------------------------------------------------
    cfg = sk.SkeletonInheritanceConfig(micro_budget=0)
    pairs_all = list(itertools.combinations(names, 2))
    print("\nPart 2 - share of parts that have a partner / 有配對對象的部位比例")
    print(f"{'pair':<24}{'tags only':>10}{'wide':>8}   how the extra pairs were found")
    report["coverage"] = {}
    for a, b in pairs_all:
        ga, gb = forms[a], forms[b]
        p0, p1 = match(ga, gb, cfg, False), match(ga, gb, cfg, True)
        extra = [f"{p['a']}~{p['b']} ({p['how']})" for p in p1 if p["how"] != "tags"]
        c0, c1 = coverage(ga, gb, p0), coverage(ga, gb, p1)
        report["coverage"][f"{a} x {b}"] = {"tags_only": c0, "wide": c1, "extra_pairs": extra}
        print(f"{a + ' x ' + b:<24}{c0:>10.0%}{c1:>8.0%}   {'; '.join(extra) if extra else '-'}")
    cov0 = np.mean([v["tags_only"] for v in report["coverage"].values()])
    cov1 = np.mean([v["wide"] for v in report["coverage"].values()])
    print(f"{'mean of 15 pairs':<24}{cov0:>10.0%}{cov1:>8.0%}")

    # ---- Part 2: breed every pair under every rule --------------------------------------------------
    stats = {r: [] for r in RULES}
    keep_for_figure: dict[tuple, SkeletonGenome] = {}
    t_start = time.perf_counter()
    for a, b in pairs_all:
        print(f"  breeding {a} x {b} ...", flush=True)
        ga, gb = sk.with_ancestry(forms[a], 1.0), sk.with_ancestry(forms[b], 0.0)
        for rule, opt in RULES.items():
            rng = np.random.default_rng([args.seed, names.index(a), names.index(b)])
            for c in range(args.children):
                child, log = fuse(ga, gb, rng, cfg, opt)
                mesh, _, _ = sk.build_sdf_creature(child, pv)
                rep = sk.mesh_report(mesh)
                outer, bubbles = shells(mesh)
                share = ancestry_share(child)
                stats[rule].append({
                    "pair": f"{a} x {b}", "valid": bool(rep["closed"] and outer == 1),
                    "components": outer, "bubbles": bubbles, "parts": len(child.parts),
                    "minority": min(share, 1.0 - share), "orphans": log["orphans_dropped"],
                    "grafted": log["grafted"],
                    "extra_bend": float(np.mean(log["extra_bend"])) if log["extra_bend"] else 0.0,
                    "root_extra_bend": float(log["extra_bend"][0]) if log["extra_bend"] else 0.0})
                if c == 0 and (a, b) in HARD_PAIRS:
                    keep_for_figure[(a, b, rule)] = child
    print(f"\nPart 2 - {len(pairs_all)} pairs x {args.children} children per rule "
          f"({time.perf_counter() - t_start:.0f} s) / 每種規則 {len(pairs_all) * args.children} 個子代")
    print(f"{'rule':<10}{'one closed body':>17}{'bubble':>8}{'parts':>7}{'lost parts':>12}{'grafted':>9}"
          f"{'smaller parent':>16}{'new kinks body':>16}{'new kinks all':>15}")
    report["rules"] = {}
    for rule, rows in stats.items():
        n = len(rows)
        agg = {"children": n, "valid": sum(r["valid"] for r in rows),
               "with_bubble": sum(r["bubbles"] > 0 for r in rows),
               "parts": float(np.mean([r["parts"] for r in rows])),
               "orphans_per_child": float(np.mean([r["orphans"] for r in rows])),
               "grafted_per_child": float(np.mean([r["grafted"] for r in rows])),
               "minority_share": float(np.mean([r["minority"] for r in rows])),
               "root_extra_bend_deg": float(np.mean([r["root_extra_bend"] for r in rows])),
               "extra_bend_deg": float(np.mean([r["extra_bend"] for r in rows])),
               "invalid": [(r["pair"], r["components"]) for r in rows if not r["valid"]]}
        report["rules"][rule] = agg
        print(f"{rule:<10}{agg['valid']:>10} / {n:<4}{agg['with_bubble']:>8}{agg['parts']:>7.1f}{agg['orphans_per_child']:>12.2f}"
              f"{agg['grafted_per_child']:>9.2f}{agg['minority_share']:>15.0%}"
              f"{agg['root_extra_bend_deg']:>13.0f} deg{agg['extra_bend_deg']:>11.0f} deg")
    print("  bubble         = children with a small sealed pocket of empty space inside the body")
    print("  smaller parent = gene share of whichever parent gave less (50% = an even fusion)")
    print("  new kinks      = bend in a crossed part beyond the more bent of its two parents")
    for rule, agg in report["rules"].items():
        if agg["invalid"]:
            print(f"  not one closed body under '{rule}': {agg['invalid']}")

    # ---- Graft stress test: force the parent part to be missing ------------------------------------
    # In the runs above almost every part hangs off the root, which always exists, so grafting rarely
    # has anything to do. Here unmatched core parts are always dropped (core_lock = 0) and every other
    # part is always kept, so parts that hang off a dropped part (serpent fangs on the head, biped horns
    # on the neck) lose their parent every time.
    # 上面的實驗裡幾乎所有部位都接在根部位上，嫁接很少派上用場。這裡強制丟掉沒配對到的核心部位，
    # 讓接在它們上面的部位（蛇的毒牙、二足的角）每次都失去父部位。
    stress_cfg = sk.SkeletonInheritanceConfig(micro_budget=0, core_lock=0.0, inheritance_factor=1.0)
    print("\nGraft stress test (parent part forced missing, 10 children each) / 嫁接壓力測試")
    print(f"{'pair':<22}{'rule':<16}{'lost parts':>11}{'grafted':>9}{'one closed body':>17}")
    report["graft_stress"] = {}
    for a, b in (("serpent", "jellyfish"), ("biped", "jellyfish")):
        ga, gb = sk.with_ancestry(forms[a], 1.0), sk.with_ancestry(forms[b], 0.0)
        for label, opt in (("drop orphans", FuseOptions(relative=True)),
                           ("graft orphans", FuseOptions(relative=True, graft=True))):
            rng = np.random.default_rng([args.seed, 99, names.index(a)])
            lost = grafted = ok = 0
            for _ in range(10):
                child, log = fuse(ga, gb, rng, stress_cfg, opt)
                mesh, _, _ = sk.build_sdf_creature(child, pv)
                lost += log["orphans_dropped"]
                grafted += log["grafted"]
                ok += int(sk.mesh_report(mesh)["closed"] and shells(mesh)[0] == 1)
            report["graft_stress"][f"{a} x {b} / {label}"] = {"lost": lost, "grafted": grafted, "valid": ok}
            print(f"{a + ' x ' + b:<22}{label:<16}{lost:>11}{grafted:>9}{ok:>12} / 10")

    # ---- Baseline: field blend ------------------------------------------------------------------------
    print("\nBaseline - field blend at 50% (no correspondence, no genome) / 基準：場混合")
    report["field_blend"] = {}
    blends = {}
    for a, b in HARD_PAIRS:
        mesh, info = field_blend(forms[a], forms[b], pv)
        blends[(a, b)] = mesh
        report["field_blend"][f"{a} x {b}"] = info
        if info["empty"]:
            print(f"  {a} x {b}: nothing left (the two shapes do not overlap enough)")
        else:
            print(f"  {a} x {b}: pieces {info['components']}, closed {info['closed']}, "
                  f"volume {info['volume']:.3f} (parents {info['volume_a']:.3f} and {info['volume_b']:.3f})")

    # ---- Figure: children of the hard pairs --------------------------------------------------------------
    cols = ["parent A", "parent B"] + list(RULES) + ["field blend"]
    fig = plt.figure(figsize=(3.4 * len(cols), 3.5 * len(HARD_PAIRS)))
    fig.suptitle("Fusing forms that do not correspond - one child per rule; colour = ancestry "
                 "(orange A, blue B); grey = field blend, no genome", fontsize=13)
    for r, (a, b) in enumerate(HARD_PAIRS):
        cells = [(f"A: {a}", sk.with_ancestry(forms[a], 1.0)), (f"B: {b}", sk.with_ancestry(forms[b], 0.0))]
        cells += [(rule, keep_for_figure[(a, b, rule)]) for rule in RULES]
        for c, (title, g) in enumerate(cells):
            ax = fig.add_subplot(len(HARD_PAIRS), len(cols), r * len(cols) + c + 1, projection="3d")
            m, fp, pcs = sk.build_sdf_creature(g, pv)
            sk.draw_mesh(ax, m, sk.ancestry_colours(g, pcs, fp), title, light=(0.5, -0.6, 0.7))
            ax.view_init(elev=18, azim=-58)
        ax = fig.add_subplot(len(HARD_PAIRS), len(cols), r * len(cols) + len(cols), projection="3d")
        if blends[(a, b)] is None:
            ax.set_axis_off()
            ax.set_title("field blend: nothing left", fontsize=10)
        else:
            m = blends[(a, b)]
            sk.draw_mesh(ax, m, np.tile(sk.GREY, (len(m.faces), 1)), "field blend", light=(0.5, -0.6, 0.7))
            ax.view_init(elev=18, azim=-58)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.93, bottom=0.0, wspace=0.0, hspace=0.06)
    fig.savefig(out / "fusion_children.png", dpi=100)
    plt.close(fig)

    (out / "results.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"Done -> {out.resolve()}")


if __name__ == "__main__":
    main()
