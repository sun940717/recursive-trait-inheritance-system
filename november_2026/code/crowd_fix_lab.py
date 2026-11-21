#!/usr/bin/env python3
"""
crowd_fix_lab.py
================
The "buried tail" problem found on 2026-11-14, and four candidate fixes tested side by side.
2026-11-14 發現的「尾巴埋在腹部裡」問題，以及並排測試的四種修法。

The problem: a tail (quadruped, biped) and the spider's abdomen both grow from the rear end of the body.
Their PCE score is exactly 0.25, the bottom of the chance line, so they never match; when a child
inherits both, the tail ends up buried inside the abdomen.
問題：尾巴（四足、二足）和蜘蛛的腹部都長在身體後端。它們的 PCE 分數剛好是 0.25，是機率直線的底，
所以永遠配不上；子代兩個都遺傳到時，尾巴就埋在腹部裡。

Requires, in the same folder: fourier3d_demo.py, fourier_genetics.py, skeleton_sdf_demo.py,
form_fusion_lab.py (2026-11-14 version with crowding() and site_rule), soft_match_lab.py,
pce_match_test.py, and RTIS's pce.py and ontology.py.
Target: Python 3.10.12 · numpy, matplotlib, scikit-image, scipy.

Variants (all: ontology tags, borderline pairs by chance, relative genes, grafting, linkage 1)
比較的做法（都用 ontology 標籤、邊界配對依機率、相對基因、嫁接、連鎖 1）:
  baseline        the rule of soft_match_lab.py as it is / soft_match_lab.py 原本的規則
  rear tag        tail, tail tip and abdomen get a shared tag "posterior"; it is not in ontology.py, so
                  PCE gives it weight 1 / 尾巴、尾尖、腹部加上共同標籤 posterior（不在 ontology.py 裡，權重 1）
  rear tag, half  the same tag with weight 0.5 (what a new "position" layer below the organ layer would give)
                  同一個標籤，權重 0.5（相當於在器官層之下新增一個「位置」層）
  lower bottom    the chance line starts at 0.15 instead of 0.25 / 機率直線的下限從 0.25 降到 0.15
  site rule       no change to matching; an unmatched part that would swallow, or be swallowed by, a part
                  already placed competes with it for the site, and only one stays
                  配對不變；沒配對的部位如果會吞掉（或被吞掉）已放好的部位，兩者競爭位置，只留一個

Measures / 量測:
  swallowed limb  at least half of the outer three quarters of a limb lies inside another limb
                  一條肢體外側四分之三有一半以上埋在另一條肢體裡
  The site rule removes exactly what this measure counts, so its score here is what the rule guarantees,
  not evidence. Its cost shows in the other columns.
  「位置規則」移除的正是這個指標在數的東西，所以它在這一欄的分數是規則保證的結果，不是證據；
  它的代價要看其他欄位。

Outputs (default ./out_crowd) / 輸出:
  crowd_fixes.png   two pairs: parents and one child per variant
  results.json      every number printed by this run

Usage / 用法:
  python crowd_fix_lab.py
  python crowd_fix_lab.py --children 20 --seed 3
"""

from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import time
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import skeleton_sdf_demo as sk  # noqa: E402
import form_fusion_lab as lab  # noqa: E402
import soft_match_lab as soft  # noqa: E402
from form_fusion_lab import FuseOptions  # noqa: E402
from ontology import get_ontology  # noqa: E402
from pce import semantic_similarity_layered  # noqa: E402
from pce_match_test import retag  # noqa: E402

REAR_PARTS = ("tail", "tail_tip", "abdomen")
LAYER_WEIGHTS = {0: 0.5, 1: 1.0, 2: 2.0}        # the weights in RTIS pce.py / RTIS pce.py 的權重
FIGURE_PAIRS = [("quadruped", "spider"), ("biped", "spider")]
BASE = dict(relative=True, graft=True, linkage=1)


def weighted_similarity(overrides: dict[str, float]):
    """The PCE formula with the weight of some tags replaced. With no overrides it must equal PCE
    (checked in main). / PCE 公式，但可替換某些標籤的權重；不替換時必須與 PCE 相同（main 會檢查）。"""
    onto = get_ontology()

    def weight(tag):
        if tag in overrides:
            return overrides[tag]
        t = onto.get_tag(tag)
        return LAYER_WEIGHTS.get(t.layer, 1.0) if t else 1.0

    def sim(tags_a, tags_b):
        a, b = set(tags_a), set(tags_b)
        if not a or not b:
            return 0.0
        union = sum(weight(t) for t in a | b)
        return sum(weight(t) for t in a & b) / union if union > 0 else 0.0
    return sim


def add_rear_tag(forms: dict) -> dict:
    return {n: sk.SkeletonGenome([dataclasses.replace(p, tags=list(p.tags) + ["posterior"])
                                  if p.name in REAR_PARTS else p for p in g.parts]) for n, g in forms.items()}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Buried tail: four candidate fixes compared")
    ap.add_argument("--out", default="out_crowd")
    ap.add_argument("--preview-voxel", type=float, default=0.03)
    ap.add_argument("--children", type=int, default=12, help="children per pair per variant / 每組每種做法的子代數")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pv = args.preview_voxel
    plain = retag(lab.all_forms(), False)
    rear = add_rear_tag(plain)
    names = list(plain)
    cfg = sk.SkeletonInheritanceConfig(micro_budget=0)

    check = weighted_similarity({})
    worst = max(abs(check(pa.tags, pb.tags) - semantic_similarity_layered(pa.tags, pb.tags))
                for a, b in itertools.combinations(names, 2) for pa in rear[a].parts for pb in rear[b].parts)
    assert worst < 1e-12, worst
    print(f"weighted_similarity with no overrides vs PCE: largest difference {worst:.1e}")

    # name -> (forms, similarity, low, fuse options)
    variants = {
        "baseline": (plain, semantic_similarity_layered, soft.LOW, FuseOptions(**BASE)),
        "rear tag": (rear, semantic_similarity_layered, soft.LOW, FuseOptions(**BASE)),
        "rear tag, half": (rear, weighted_similarity({"posterior": 0.5}), soft.LOW, FuseOptions(**BASE)),
        "lower bottom": (plain, semantic_similarity_layered, 0.15, FuseOptions(**BASE)),
        "site rule": (plain, semantic_similarity_layered, soft.LOW, FuseOptions(**BASE, site_rule=True)),
    }
    report: dict = {"preview_voxel": pv, "children_per_cell": args.children, "seed": args.seed, "high": soft.HIGH}

    # ---- 1. what each variant does to the scores / 每種做法對分數的影響 --------------------------------
    print("\n1. Borderline pairs under each variant (score -> chance of matching) / 各做法下的邊界配對")
    affected: set[tuple[str, str]] = set()
    report["borderline"] = {}
    for vname, (forms, sim, low, _) in variants.items():
        rows = {}
        for a, b in itertools.combinations(names, 2):
            for pa in forms[a].parts[1:]:
                for pb in forms[b].parts[1:]:
                    s = float(sim(pa.tags, pb.tags))
                    if low <= s < soft.HIGH:
                        rows[f"{a}.{soft.kind(pa.name)} ~ {b}.{soft.kind(pb.name)}"] = (s, soft.match_chance(s, low))
                        affected.add((a, b))
        report["borderline"][vname] = {k: {"score": v[0], "chance": v[1]} for k, v in rows.items()}
        print(f"  {vname}: {len(rows)} kinds of borderline pair")
        for k, (s, c) in sorted(rows.items(), key=lambda kv: -kv[1][0]):
            print(f"      {k:<44}{s:>7.3f}{c:>6.0%}")
    for vname, (forms, sim, low, _) in variants.items():
        ta = [(sim(pa.tags, pb.tags)) for a, b in (("quadruped", "spider"), ("biped", "spider"))
              for pa in forms[a].parts if pa.name == "tail" for pb in forms[b].parts if pb.name == "abdomen"]
        print(f"  tail ~ abdomen under {vname}: score {ta[0]:.3f}, chance "
              f"{soft.match_chance(ta[0], low) if ta[0] < soft.HIGH else 1.0:.0%}")
    pairs_used = [pr for pr in itertools.combinations(names, 2) if pr in affected]
    report["form_pairs"] = [f"{a} x {b}" for a, b in pairs_used]

    # ---- 2. children / 子代 ------------------------------------------------------------------------------
    stats = {v: [] for v in variants}
    keep: dict[tuple, object] = {}
    t0 = time.perf_counter()
    for a, b in pairs_used:
        print(f"  breeding {a} x {b} ...", flush=True)
        for vname, (forms, sim, low, opt) in variants.items():
            ga, gb = sk.with_ancestry(forms[a], 1.0), sk.with_ancestry(forms[b], 0.0)
            rng = np.random.default_rng([args.seed, names.index(a), names.index(b), 3])
            for c in range(args.children):
                pairs, decisions = soft.soft_match(ga, gb, rng, "soft", sim=sim, low=low)
                child, log = lab.fuse(ga, gb, rng, cfg, opt, pairs=pairs)
                mesh, _, _ = sk.build_sdf_creature(child, pv)
                outer, bubbles = lab.shells(mesh)
                share = lab.ancestry_share(child)
                crowd = lab.crowding(child)["swallowed"]
                stats[vname].append({
                    "pair": f"{a} x {b}", "valid": bool(sk.mesh_report(mesh)["closed"] and outer == 1),
                    "bubbles": int(bubbles), "parts": len(child.parts), "minority": min(share, 1.0 - share),
                    "new_humps": float(np.mean(log["extra_beads"])), "swallowed": [list(k) for k in crowd],
                    "site_lost": int(log["site_lost"]),
                    "matched": [f"{a}.{soft.kind(d['a'])} ~ {b}.{soft.kind(d['b'])}" for d in decisions if d["matched"]]})
                if (a, b) in FIGURE_PAIRS:
                    if vname == "baseline" and crowd:
                        keep.setdefault((a, b, vname), child)
                    elif vname != "baseline" and c == 0:
                        keep[(a, b, vname)] = child
    n = len(pairs_used) * args.children
    print(f"\n2. {len(pairs_used)} pairs of forms x {args.children} children = {n} children per variant"
          f" ({time.perf_counter() - t0:.0f} s)")
    print(f"{'variant':<16}{'one closed body':>17}{'bubbles':>9}{'parts':>7}{'smaller parent':>16}{'new humps':>11}"
          f"{'with swallowed limb':>21}{'tail in abdomen':>17}{'parts lost to site rule':>25}")
    report["variants"] = {}
    for vname, rows in stats.items():
        kinds: dict[str, int] = {}
        for r in rows:
            for k in r["swallowed"]:
                label = f"{soft.kind(k[0])} + {soft.kind(k[1])}"
                kinds[label] = kinds.get(label, 0) + 1
        matched: dict[str, int] = {}
        for r in rows:
            for m in r["matched"]:
                matched[m] = matched.get(m, 0) + 1
        agg = {"children": len(rows), "valid": sum(r["valid"] for r in rows),
               "with_bubble": sum(r["bubbles"] > 0 for r in rows),
               "parts": float(np.mean([r["parts"] for r in rows])),
               "minority_share": float(np.mean([r["minority"] for r in rows])),
               "new_humps": float(np.mean([r["new_humps"] for r in rows])),
               "with_swallowed": sum(bool(r["swallowed"]) for r in rows),
               "tail_in_abdomen": kinds.get("abdomen + tail", 0),
               "site_lost": sum(r["site_lost"] for r in rows),
               "swallowed_kinds": kinds, "borderline_matched": matched}
        report["variants"][vname] = agg
        print(f"{vname:<16}{agg['valid']:>10} / {agg['children']:<4}{agg['with_bubble']:>9}{agg['parts']:>7.1f}"
              f"{agg['minority_share']:>16.0%}{agg['new_humps']:>11.2f}{agg['with_swallowed']:>14} / {agg['children']:<4}"
              f"{agg['tail_in_abdomen']:>17}{agg['site_lost']:>25}")
    for vname in variants:
        agg = report["variants"][vname]
        print(f"\n  {vname}")
        print("    swallowed limbs: " + ("; ".join(f"{k} ({v})" for k, v in sorted(agg["swallowed_kinds"].items(), key=lambda kv: -kv[1])) or "none"))
        print("    borderline pairs that matched: " + ("; ".join(f"{k} ({v})" for k, v in sorted(agg["borderline_matched"].items(), key=lambda kv: -kv[1])) or "none"))
        bad = [r for r in stats[vname] if not r["valid"]]
        if bad:
            print("    not one closed body: " + "; ".join(r["pair"] for r in bad))

    # ---- figure -------------------------------------------------------------------------------------------
    cols = ["parent A", "parent B"] + list(variants)
    fig = plt.figure(figsize=(3.2 * len(cols), 3.4 * len(FIGURE_PAIRS)))
    fig.suptitle("Buried tail - one child per variant; baseline shows a child where it happened; "
                 "colour = ancestry (orange A, blue B)", fontsize=13)
    for r, (a, b) in enumerate(FIGURE_PAIRS):
        cells = [(f"A: {a}", sk.with_ancestry(plain[a], 1.0)), (f"B: {b}", sk.with_ancestry(plain[b], 0.0))]
        cells += [(v, keep.get((a, b, v))) for v in variants]
        for c, (title, g) in enumerate(cells):
            ax = fig.add_subplot(len(FIGURE_PAIRS), len(cols), r * len(cols) + c + 1, projection="3d")
            if g is None:
                ax.set_axis_off()
                ax.set_title(f"{title}: did not occur in this run", fontsize=9)
                continue
            m, fp, pcs = sk.build_sdf_creature(g, pv)
            sw = len(lab.crowding(g)["swallowed"])
            sk.draw_mesh(ax, m, sk.ancestry_colours(g, pcs, fp), f"{title}: {len(g.parts)} parts, {sw} swallowed",
                         light=(0.5, -0.6, 0.7))
            ax.view_init(elev=18, azim=-122)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.9, bottom=0.0, wspace=0.0, hspace=0.08)
    fig.savefig(out / "crowd_fixes.png", dpi=100)
    plt.close(fig)

    report["children"] = stats
    (out / "results.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"Done -> {out.resolve()}")


if __name__ == "__main__":
    main()
