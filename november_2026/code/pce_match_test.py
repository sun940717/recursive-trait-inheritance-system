#!/usr/bin/env python3
"""
pce_match_test.py
=================
Does RTIS's own PCE (layer-weighted tag similarity) match parts better than plain tag overlap?
RTIS 自己的 PCE（依層級加權的標籤相似度）配對部位，會不會比單純的標籤重疊好？

Put this file in the RTIS folder (next to pce.py and ontology.py) together with fourier3d_demo.py,
fourier_genetics.py, skeleton_sdf_demo.py and form_fusion_lab.py. Target: Python 3.10.12 · numpy.
請放在 RTIS 資料夾（跟 pce.py、ontology.py 同一層），並連同其他四個原型檔案。

Tag sets compared / 比較的標籤組:
  prototype   the tags used so far (mostly not in ontology.py) / 目前原型用的標籤（大多不在 ontology.py 裡）
  ontology    retagged with ontology.py tags only, including the part layer (torso, head, limb, tail ...)
              改用 ontology.py 的標籤，包含部位層
  + position  the same plus two proposed position tags (anterior / posterior)
              再加上提議的兩個位置標籤（前／後）

"Agrees with role" uses a role I assigned to each part by hand (head, tail, walking limb, grasping limb,
weapon, sensor, trunk). It is my judgment of what should correspond, not ground truth.
「符合角色」用的是我手動給每個部位指定的角色，是我對「應該對應什麼」的判斷，不是標準答案。
"""
from __future__ import annotations
import dataclasses, itertools, json
from pathlib import Path
import numpy as np
import fourier_genetics as fg
import skeleton_sdf_demo as sk
import form_fusion_lab as lab
from pce import semantic_similarity_layered

from form_fusion_lab import ONTOLOGY_TAGS  # noqa: E402  (moved there 2026-11-15 / 11-15 移到那裡)
POSITION = {"leg_front": "anterior", "arm_front": "anterior", "leg_1": "anterior", "claw": "anterior",
            "leg_rear": "posterior", "leg_4": "posterior"}
ROLE = {"neck_head": "head", "head": "head", "tail": "tail", "tail_tip": "tail", "leg_front": "walk", "leg_rear": "walk",
        "leg_1": "walk", "leg_2": "walk", "leg_3": "walk", "leg_4": "walk", "arm_front": "grasp", "claw": "grasp",
        "tentacle": "grasp", "oral_arm": "grasp", "fang": "weapon", "horn": "weapon", "eye_stalk": "sensor", "abdomen": "trunk"}


def retag(forms, with_position):
    out = {}
    for name, g in forms.items():
        parts = []
        for p in g.parts:
            tags = list(ONTOLOGY_TAGS[name][p.name])
            if with_position and p.name in POSITION:
                tags.append(POSITION[p.name])
            parts.append(dataclasses.replace(p, tags=tags))
        out[name] = sk.SkeletonGenome(parts)
    return out


def greedy_match(ga, gb, sim, threshold, same_arrangement):
    """One-to-one, best score first (the rule of sk.match_parts, with the similarity passed in)."""
    cand = []
    for pa in ga.parts[1:]:
        for pb in gb.parts[1:]:
            if same_arrangement and sk.arrangement(pa) != sk.arrangement(pb):
                continue
            s = sim(pa.tags, pb.tags)
            if s >= threshold:
                cand.append((s + 0.25 * (1.0 - abs(pa.attach - pb.attach)), pa.name, pb.name))
    used_a, used_b, pairs = set(), set(), []
    for s, na, nb in sorted(cand, key=lambda c: -c[0]):
        if na not in used_a and nb not in used_b:
            pairs.append((na, nb, s)); used_a.add(na); used_b.add(nb)
    return pairs


def evaluate(forms, sim, threshold, same_arrangement):
    cov, agree, total, examples = [], 0, 0, []
    for a, b in itertools.combinations(forms, 2):
        pairs = greedy_match(forms[a], forms[b], sim, threshold, same_arrangement)
        n = len(forms[a].parts) + len(forms[b].parts) - 2
        cov.append(2 * len(pairs) / n)
        for na, nb, _ in pairs:
            total += 1
            ok = ROLE[na] == ROLE[nb]
            agree += ok
            if not ok:
                examples.append(f"{a}.{na}~{b}.{nb}")
    return float(np.mean(cov)), agree, total, examples


def main():
    forms = lab.all_forms()
    sets = {"prototype": forms, "ontology": retag(forms, False), "+ position": retag(forms, True)}
    sims = {"plain overlap": lambda x, y: (len(set(x) & set(y)) / len(set(x) | set(y))) if (set(x) | set(y)) else 0.0,
            "PCE": semantic_similarity_layered}
    report = {}
    print("PCE on the docs' example: tentacle [motor, grasping] vs foreleg [motor, locomotion] =",
          round(semantic_similarity_layered(["motor", "grasping"], ["motor", "locomotion"]), 3))
    for same in (True, False):
        print(f"\n{'Same arrangement required' if same else 'Any arrangement allowed (mirror may pair with radial)'}"
              f" / {'排列方式要相同' if same else '不限排列方式'}")
        print(f"{'tags':<12}{'similarity':<15}{'threshold':>10}{'parts with a partner':>22}{'pairs':>7}{'agree with role':>17}{'disagree':>10}")
        for tname, fs in sets.items():
            for sname, sim in sims.items():
                for thr in (0.25, 0.4):
                    cov, agree, total, ex = evaluate(fs, sim, thr, same)
                    report[f"{tname}|{sname}|{thr}|{'same' if same else 'any'}"] = {
                        "coverage": cov, "pairs": total, "agree": agree, "disagree_examples": ex}
                    print(f"{tname:<12}{sname:<15}{thr:>10}{cov:>21.0%}{total:>8}{agree:>12} ({agree / max(total, 1):.0%})"
                          f"{total - agree:>9}")
    best = report["+ position|PCE|0.4|any"]
    print("\nDisagreements left with ontology + position tags, PCE, threshold 0.4, any arrangement:")
    print("  " + ("; ".join(best["disagree_examples"]) or "none"))
    Path("out_pce").mkdir(exist_ok=True)
    Path("out_pce/results.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
