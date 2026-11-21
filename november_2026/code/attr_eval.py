#!/usr/bin/env python3
"""
attr_eval.py
============
Tests the part-attribute layer (attribute_layer.py) against the adopted rules without it.
測試部位屬性層，跟沒有它的已採用規則比較。

1. Leg outcomes for biped x spider: over many matings, how often each of the outcomes the user
   described happens (2 or 8 legs; length and thickness from the biped or the spider).
   二足 × 蜘蛛的腳：多次交配中，使用者描述的每種結果各出現幾次。
2. Off versus on: 15 pairs of forms x several seeds, same matching and same seeds for both.
   關閉與開啟：15 組形體 × 數個種子，兩邊用相同的配對與種子。
   - one closed body / 一個封閉的身體
   - hidden parts: an attached part with almost no surface of its own (fewer than 20 triangles at the
     preview grid) / 幾乎沒有自己表面的部位（預覽格點下少於 20 個三角形）
   - swallowed limbs (form_fusion_lab.crowding) / 被另一條肢體吞掉的肢體
   - new humps on crossed parts / 交配部位多出的隆起
   - parts per child, genes from the smaller parent / 平均部位數、較少一方的基因比例
3. Figure: the parents and one child for each of the four leg outcomes.
   圖：兩個親代，以及四種腿的結果各一個子代。

Requires the same files as rtis_run_once.py plus attribute_layer.py.
Target: Python 3.10.12 · numpy, scipy, scikit-image, matplotlib.

Usage / 用法:
  python attr_eval.py                     # -> out_attr_eval/
  python attr_eval.py --seeds 4 --matings 200
"""

from __future__ import annotations

import argparse
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
import attribute_layer  # noqa: E402

CFG = sk.SkeletonInheritanceConfig(micro_budget=0)


def breed(forms, a, b, seed, on: bool):
    """The same steps as rtis_run_once.py. / 與 rtis_run_once.py 相同的步驟。"""
    rng = np.random.default_rng(seed)
    ga, gb = sk.with_ancestry(forms[a], 1.0), sk.with_ancestry(forms[b], 0.0)
    pairs, _ = soft.soft_match(ga, gb, rng, "soft")
    attr, exclude = None, set()
    if on:
        attr = attribute_layer.AttributeLayer(np.random.default_rng([seed, 101]))
        pairs, exclude = attr.plan(ga, gb, pairs)
    child, log = lab.fuse(ga, gb, rng, CFG, lab.ADOPTED, pairs=pairs, exclude=exclude, attr=attr)
    return child, log, attr


def leg_outcome(child, attr) -> tuple[int, str]:
    """(number of legs, label). Legs = parts tagged locomotion; x2 for mirrored ones.
    （腳的數量、標籤）。腳＝帶 locomotion 標籤的部位；鏡像的算 2 隻。"""
    legs = [p for p in child.parts if "locomotion" in p.tags]
    n = sum(2 if sk.arrangement(p) == "mirror" else 1 for p in legs)
    st = next((s for s in attr.log["sets"] if "leg_rear" in s["a"]), None) if attr else None
    if st is None:
        return n, "no set"
    src = {st["attributes_from"]["length"], st["attributes_from"]["thickness"]}
    look = "biped" if src == {"A"} else "spider" if src == {"B"} else "mixed"
    return n, look


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Test the part-attribute layer")
    ap.add_argument("--out", default="out_attr_eval")
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--matings", type=int, default=400)
    ap.add_argument("--preview-voxel", type=float, default=0.03)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    forms = lab.all_forms(ontology_tags=True)
    report: dict = {"seeds": args.seeds, "matings": args.matings, "preview_voxel": args.preview_voxel}

    # ---- 1. leg outcomes / 腳的結果 ------------------------------------------------------------------------
    tally: dict[str, int] = {}
    examples: dict[str, int] = {}
    for seed in range(args.matings):
        child, _, attr = breed(forms, "biped", "spider", 1000 + seed, True)
        n, look = leg_outcome(child, attr)
        key = f"{n} legs, {look} look"
        tally[key] = tally.get(key, 0) + 1
        examples.setdefault(key, 1000 + seed)
    report["leg_outcomes"] = tally
    print(f"1. biped x spider, {args.matings} matings with the layer on (look = where length and thickness came from)")
    for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"   {k:<26}{v:>5}  ({v / args.matings:.0%})")

    # ---- 2. off versus on / 關閉與開啟 ----------------------------------------------------------------------
    names = list(forms)
    rows = {"off": [], "on": []}
    t0 = time.perf_counter()
    for a, b in itertools.combinations(names, 2):
        for seed in range(1, args.seeds + 1):
            for mode in ("off", "on"):
                child, log, attr = breed(forms, a, b, seed, mode == "on")
                mesh, fp, pieces = sk.build_sdf_creature(child, args.preview_voxel)
                outer, bubbles = lab.shells(mesh)
                faces = np.bincount(fp, minlength=len(pieces))
                per_part: dict[str, int] = {}
                for pc, nf in zip(pieces, faces):
                    per_part[pc["gene"]] = per_part.get(pc["gene"], 0) + int(nf)
                root = next(p.name for p in child.parts if p.parent is None)
                hidden = [n for n, nf in per_part.items() if n != root and nf < 20]
                share = lab.ancestry_share(child)
                rows[mode].append({"pair": f"{a} x {b}", "seed": seed,
                                   "valid": bool(sk.mesh_report(mesh)["closed"] and outer == 1),
                                   "hidden": hidden, "swallowed": len(lab.crowding(child)["swallowed"]),
                                   "humps": float(np.mean(log["extra_beads"])) if log["extra_beads"] else 0.0,
                                   "parts": len(child.parts), "minority": min(share, 1 - share)})
        print(f"   {a} x {b} done ({time.perf_counter() - t0:.0f} s)", flush=True)
    n = len(rows["off"])
    print(f"\n2. {n // args.seeds} pairs x {args.seeds} seeds = {n} children per mode")
    print(f"{'mode':<6}{'one closed body':>17}{'with a hidden part':>20}{'hidden parts':>14}"
          f"{'with swallowed limb':>21}{'new humps':>11}{'parts':>7}{'smaller parent':>16}")
    report["modes"] = {}
    for mode, rs in rows.items():
        agg = {"children": len(rs), "valid": sum(r["valid"] for r in rs),
               "with_hidden": sum(bool(r["hidden"]) for r in rs), "hidden": sum(len(r["hidden"]) for r in rs),
               "with_swallowed": sum(r["swallowed"] > 0 for r in rs),
               "humps": float(np.mean([r["humps"] for r in rs])), "parts": float(np.mean([r["parts"] for r in rs])),
               "minority": float(np.mean([r["minority"] for r in rs]))}
        report["modes"][mode] = agg
        print(f"{mode:<6}{agg['valid']:>10} / {n:<4}{agg['with_hidden']:>13} / {n:<4}{agg['hidden']:>12}"
              f"{agg['with_swallowed']:>14} / {n:<4}{agg['humps']:>11.2f}{agg['parts']:>7.1f}{agg['minority']:>16.0%}")
    for mode in rows:
        kinds: dict[str, int] = {}
        for r in rows[mode]:
            for h in r["hidden"]:
                key = f"{r['pair']}: {h}"
                kinds[key] = kinds.get(key, 0) + 1
        report["modes"][mode]["hidden_kinds"] = kinds
        print(f"   hidden parts, {mode}: " + ("; ".join(f"{k} ({v})" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])) or "none"))
    report["rows"] = rows

    # ---- 3. figure / 圖 --------------------------------------------------------------------------------------
    want = ["2 legs, biped look", "8 legs, spider look", "2 legs, spider look", "8 legs, biped look"]
    cells = [("A: biped", sk.with_ancestry(forms["biped"], 1.0)), ("B: spider", sk.with_ancestry(forms["spider"], 0.0))]
    for k in want:
        cells.append((k, breed(forms, "biped", "spider", examples[k], True)[0] if k in examples else None))
    fig = plt.figure(figsize=(3.4 * len(cells), 3.8))
    fig.suptitle("biped x spider with the part-attribute layer: count and placement from one parent, "
                 "length and thickness from either (colour = ancestry: orange biped, blue spider)", fontsize=12)
    for i, (title, g) in enumerate(cells):
        ax = fig.add_subplot(1, len(cells), i + 1, projection="3d")
        if g is None:
            ax.set_axis_off()
            ax.set_title(f"{title}: not seen", fontsize=10)
            continue
        m, fp, pcs = sk.build_sdf_creature(g, args.preview_voxel)
        sk.draw_mesh(ax, m, sk.ancestry_colours(g, pcs, fp), title, light=(0.5, -0.6, 0.7))
        ax.view_init(elev=22, azim=-60)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.84, bottom=0.0, wspace=0.0)
    fig.savefig(out / "leg_outcomes.png", dpi=100)
    plt.close(fig)
    report["example_seeds"] = examples
    (out / "results.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"Done -> {out.resolve()}")


if __name__ == "__main__":
    main()
