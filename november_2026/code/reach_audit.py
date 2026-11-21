#!/usr/bin/env python3
"""
reach_audit.py
==============
Which inheritance outcomes can never happen under the current rules? (The user's question on
2026-11-15: is the map from parents to children "surjective", i.e. can every combination occur?)
現行規則下，哪些遺傳結果永遠不會出現？（使用者 11-15 的問題：遺傳是不是「滿射」，所有組合都可能出現嗎？）

Method: many matings per pair of parents (adopted rules + the part-attribute layer), recording for
every decision what happened, then listing the options that never occurred.
做法：每對親代交配很多次（已採用規則＋部位屬性層），記下每個決定的結果，再列出從沒出現過的選項。

What is recorded per child / 每個子代記錄:
  fate of every parent part: merged with a part of the other parent, kept alone, or left out
  每個親代部位的去向：跟對方的部位合併、單獨保留、沒有進入子代
  the gene-source pattern along each crossed chain (bone lengths): all A, all B, one switch, 2+ switches
  每條交配鏈的基因來源樣式（骨頭長度）：全 A、全 B、交換一次、交換兩次以上
  leg count; which attributes came from which parent / 腳的數量；屬性來自哪一方

Requires the same files as attr_eval.py. Target: Python 3.10.12 · numpy.
Usage / 用法:  python reach_audit.py --matings 1000
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import skeleton_sdf_demo as sk
import form_fusion_lab as lab
from attr_eval import breed

PAIRS = [("biped", "spider"), ("quadruped", "crab"), ("serpent", "jellyfish")]


def pattern(src: list[bool]) -> str:
    if all(src):
        return "all A"
    if not any(src):
        return "all B"
    switches = sum(a != b for a, b in zip(src, src[1:]))
    return "1 switch" if switches == 1 else "2+ switches"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Which inheritance outcomes never happen")
    ap.add_argument("--matings", type=int, default=1000)
    ap.add_argument("--out", default="out_reach")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    forms = lab.all_forms(ontology_tags=True)
    report = {}
    for a, b in PAIRS:
        fate: dict[str, Counter] = {}
        partner: Counter = Counter()
        chain: Counter = Counter()
        legs: Counter = Counter()
        parts_n: Counter = Counter()
        for seed in range(args.matings):
            child, log, attr = breed(forms, a, b, 5000 + seed, True)
            origin: dict[str, list[str]] = {}
            for key, cname in log["sources"].items():
                origin.setdefault(cname, []).append(key)
            seen = {}
            for cname, keys in origin.items():
                for k in keys:
                    seen[k] = "merged" if len({x[0] for x in keys}) > 1 else "alone"
                if len({x[0] for x in keys}) > 1:
                    partner[" ~ ".join(sorted(keys))] += 1
            for lab_, g in (("A", forms[a]), ("B", forms[b])):
                for p in g.parts:
                    k = f"{lab_}.{p.name}"
                    fate.setdefault(k, Counter())[seen.get(k, "left out")] += 1
            for name, gsrc in log["genes"].items():
                if "lengths" in gsrc and len(gsrc["lengths"]) > 1:
                    chain[pattern(gsrc["lengths"])] += 1
            legs[sum(2 if sk.arrangement(p) == "mirror" else (p.radial or 1)
                     for p in child.parts if "locomotion" in p.tags)] += 1
            parts_n[len(child.parts)] += 1
        n = args.matings
        print(f"\n=== {a} x {b}, {n} matings ===")
        print(f"{'parent part':<22}{'merged':>8}{'alone':>8}{'left out':>10}")
        never = []
        for k, c in fate.items():
            print(f"{k:<22}{c['merged']:>8}{c['alone']:>8}{c['left out']:>10}")
            never += [f"{k} {opt}" for opt in ("merged", "alone", "left out") if c[opt] == 0]
        print("merged pairs seen:", dict(partner.most_common()))
        print("crossed chains (bone lengths):", {k: chain[k] for k in ("all A", "all B", "1 switch", "2+ switches")})
        print("leg counts:", dict(sorted(legs.items())), "| part counts:", dict(sorted(parts_n.items())))
        print("never happened:", "; ".join(never))
        report[f"{a} x {b}"] = {"fate": {k: dict(v) for k, v in fate.items()}, "merged_pairs": dict(partner),
                                "chains": dict(chain), "legs": dict(legs), "parts": dict(parts_n), "never": never}
    (out / "results.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
