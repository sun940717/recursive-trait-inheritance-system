#!/usr/bin/env python3
"""
bead_fix_lab.py
===============
The "string of beads" problem found on 2026-11-13, and three candidate fixes tested side by side.
2026-11-13 發現的「念珠狀身體」問題，以及並排測試的三種修法。

The problem: with one gene per joint thickness, a child takes fat joints from one parent and thin
joints from the other, in no particular order, so a body becomes a string of balls.
問題：每個關節的粗細各是一個基因時，子代會不規則地從一方拿到粗關節、從另一方拿到細關節，
身體就變成一串球。

Requires fourier3d_demo.py, fourier_genetics.py, skeleton_sdf_demo.py and form_fusion_lab.py in the
same folder. Target: Python 3.10.12 · numpy, matplotlib, scikit-image, scipy.
需要同資料夾的 fourier3d_demo.py、fourier_genetics.py、skeleton_sdf_demo.py、form_fusion_lab.py。

Variants (all use relative genes, tag matching and grafting; only the item named changes)
比較的做法（都用相對基因、標籤配對、嫁接；只改變列出的那一項）:
  independent   every gene on its own (the 11-13 behaviour) / 每個基因各自獨立（11-13 的做法）
  ratio         thickness stored as a ratio of the neighbouring bone length / 粗細改存成相對骨頭長度的比例
  linkage 1     genes along a chain inherited in runs, 1 switch point per part / 成段遺傳，每個部位 1 個交換點
  linkage 2     the same with 2 switch points / 同上，2 個交換點
  pack          the whole thickness profile of a part from one parent / 整條粗細剖面來自同一個親代

Measures / 量測:
  humps         peaks along a chain's visible outline, at least 5% above the dips on both sides
                (a plain body has 1; a string of four balls has 4)
                沿著鏈看得到的輪廓上的隆起數（普通的身體是 1，四顆球串在一起是 4）
  new humps     humps in a crossed part beyond the lumpier of its two parents
                交配部位比兩個親代中隆起較多的那個還多出的隆起數
  variation     population variation of the body's genes over 10 generations of random mating
                隨機交配 10 代後，族群中身體基因的變異還剩多少

Outputs (default ./out_beads) / 輸出:
  bead_fixes.png     three pairs: parents and one child per variant / 三組配對：親代與每種做法各一個子代
  results.json       every number printed by this run / 這次執行印出的所有數字

Usage / 用法:
  python bead_fix_lab.py
  python bead_fix_lab.py --children 5 --seed 3
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
from form_fusion_lab import FuseOptions  # noqa: E402

BASE = dict(relative=True, graft=True)
VARIANTS = {
    "independent": FuseOptions(**BASE),
    "ratio": FuseOptions(**BASE, thickness="ratio"),
    "linkage 1": FuseOptions(**BASE, linkage=1),
    "linkage 2": FuseOptions(**BASE, linkage=2),
    "pack": FuseOptions(**BASE, thickness="pack"),
}
FIGURE_PAIRS = [("serpent", "crab"), ("quadruped", "serpent"), ("biped", "crab")]


def body_vector(g, n: int = 9) -> np.ndarray:
    """Relative genes of the body chain as one vector (lengths, thicknesses, bends).
    身體那條鏈的相對基因，排成一個向量（長度、粗細、彎折）。"""
    root = sk.resample_part(g.parts[0], n)
    rel = lab.encode(root, None, lab.body_scale(g))
    return np.concatenate([rel["lengths"], rel["radii"], rel["bends"].ravel()])


def variation_experiment(forms, pop: int = 40, gens: int = 10, seeds: int = 6) -> dict[str, np.ndarray]:
    """Random mating, no mutation, no selection: only the inheritance rule differs.
    Founders: 20 mutated quadrupeds and 20 mutated bipeds.
    隨機交配、無突變、無選擇：只有遺傳規則不同。起始族群：20 隻突變過的四足＋20 隻突變過的二足。"""
    cfg = sk.SkeletonInheritanceConfig(micro_budget=0)
    spread = sk.SkeletonInheritanceConfig(micro_budget=12, micro_rate=1.0)
    out = {}
    for name, opt in VARIANTS.items():
        curves = []
        for s in range(seeds):
            rng = np.random.default_rng([2026, s])
            population = [sk.mutate(sk.with_ancestry(forms[f], a), spread, rng)[0]
                          for f, a in (("quadruped", 1.0), ("biped", 0.0)) for _ in range(pop // 2)]
            v0 = np.var(np.stack([body_vector(g) for g in population]), axis=0).mean()
            curve = [1.0]
            for _ in range(gens):
                nxt = []
                for _ in range(pop):
                    i, j = rng.choice(pop, size=2, replace=False)
                    nxt.append(lab.fuse(population[i], population[j], rng, cfg, opt)[0])
                population = nxt
                curve.append(float(np.var(np.stack([body_vector(g) for g in population]), axis=0).mean() / v0))
            curves.append(curve)
        out[name] = np.array(curves)
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Bead problem: three candidate fixes compared")
    ap.add_argument("--out", default="out_beads")
    ap.add_argument("--preview-voxel", type=float, default=0.03)
    ap.add_argument("--children", type=int, default=3, help="children per pair per variant / 每組每種做法的子代數")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pv = args.preview_voxel
    forms = lab.all_forms()
    names = list(forms)
    pairs_all = list(itertools.combinations(names, 2))
    cfg = sk.SkeletonInheritanceConfig(micro_budget=0)
    report: dict = {"preview_voxel": pv, "children_per_cell": args.children, "seed": args.seed}

    # ---- does the measure see the problem at all? / 指標看得到問題嗎？ -------------------------------
    print("Humps on the founders' bodies (a smooth body should have 1) / 原始形體身體上的隆起數")
    report["founder_bulges"] = {n: lab.beads(g.parts[0]) for n, g in forms.items()}
    print("  " + ", ".join(f"{n} {b}" for n, b in report["founder_bulges"].items()))

    # ---- every pair under every variant --------------------------------------------------------------
    stats = {v: [] for v in VARIANTS}
    keep: dict[tuple, object] = {}
    t0 = time.perf_counter()
    for a, b in pairs_all:
        print(f"  breeding {a} x {b} ...", flush=True)
        ga, gb = sk.with_ancestry(forms[a], 1.0), sk.with_ancestry(forms[b], 0.0)
        for name, opt in VARIANTS.items():
            rng = np.random.default_rng([args.seed, names.index(a), names.index(b)])
            for c in range(args.children):
                child, log = lab.fuse(ga, gb, rng, cfg, opt)
                mesh, _, _ = sk.build_sdf_creature(child, pv)
                outer, bubbles = lab.shells(mesh)
                share = lab.ancestry_share(child)
                stats[name].append({
                    "pair": f"{a} x {b}", "valid": bool(sk.mesh_report(mesh)["closed"] and outer == 1),
                    "bubbles": bubbles, "minority": min(share, 1.0 - share),
                    "beads_body": int(log["extra_beads"][0]), "beads_all": float(np.mean(log["extra_beads"])),
                    "humps_body": int(log["humps"][0]),
                    "kinks_all": float(np.mean(log["extra_bend"]))})
                if c == 0 and (a, b) in FIGURE_PAIRS:
                    keep[(a, b, name)] = child
    n_children = len(pairs_all) * args.children
    print(f"\n{len(pairs_all)} pairs x {args.children} children per variant ({time.perf_counter() - t0:.0f} s) "
          f"/ 每種做法 {n_children} 個子代")
    print(f"{'variant':<13}{'one closed body':>17}{'humps on body':>15}{'new humps, body':>17}{'bodies with any':>17}"
          f"{'new humps, all parts':>22}{'new kinks':>11}{'smaller parent':>16}")
    report["variants"] = {}
    for name, rows in stats.items():
        agg = {"children": len(rows), "valid": sum(r["valid"] for r in rows),
               "with_bubble": sum(r["bubbles"] > 0 for r in rows),
               "new_bulges_body": float(np.mean([r["beads_body"] for r in rows])),
               "bodies_with_new_bulges": sum(r["beads_body"] > 0 for r in rows),
               "new_bulges_per_part": float(np.mean([r["beads_all"] for r in rows])),
               "humps_body": float(np.mean([r["humps_body"] for r in rows])),
               "worst_humps_body": int(max(r["humps_body"] for r in rows)),
               "new_kinks_deg": float(np.mean([r["kinks_all"] for r in rows])),
               "minority_share": float(np.mean([r["minority"] for r in rows]))}
        report["variants"][name] = agg
        print(f"{name:<13}{agg['valid']:>10} / {agg['children']:<4}{agg['humps_body']:>8.2f} (max {agg['worst_humps_body']})"
              f"{agg['new_bulges_body']:>14.2f}{agg['bodies_with_new_bulges']:>12} / {agg['children']:<2}"
              f"{agg['new_bulges_per_part']:>22.2f}{agg['new_kinks_deg']:>7.0f} deg{agg['minority_share']:>15.0%}")
    print("  new humps / kinks = beyond the worse of the two parents, per crossed part")

    # ---- variation over generations -----------------------------------------------------------------------
    t0 = time.perf_counter()
    var = variation_experiment(forms)
    print(f"\nVariation left in the body's genes, random mating, no mutation ({time.perf_counter() - t0:.0f} s)"
          " / 身體基因的變異還剩多少")
    print(f"{'variant':<13}{'after 1 gen':>13}{'after 5':>10}{'after 10':>10}{'range over 6 seeds at 10':>27}")
    report["variation"] = {}
    for name, curves in var.items():
        m = curves.mean(axis=0)
        report["variation"][name] = {"gen1": float(m[1]), "gen5": float(m[5]), "gen10": float(m[10]),
                                     "gen10_min": float(curves[:, 10].min()), "gen10_max": float(curves[:, 10].max())}
        print(f"{name:<13}{m[1]:>13.0%}{m[5]:>10.0%}{m[10]:>10.0%}"
              f"{curves[:, 10].min():>17.0%} - {curves[:, 10].max():.0%}")

    # ---- figure -------------------------------------------------------------------------------------------
    cols = ["parent A", "parent B"] + list(VARIANTS)
    fig = plt.figure(figsize=(3.3 * len(cols), 3.3 * len(FIGURE_PAIRS)))
    fig.suptitle("Bead problem - one child per variant (same parents); colour = ancestry (orange A, blue B)",
                 fontsize=13)
    for r, (a, b) in enumerate(FIGURE_PAIRS):
        cells = [(f"A: {a}", sk.with_ancestry(forms[a], 1.0)), (f"B: {b}", sk.with_ancestry(forms[b], 0.0))]
        cells += [(v, keep[(a, b, v)]) for v in VARIANTS]
        for c, (title, g) in enumerate(cells):
            ax = fig.add_subplot(len(FIGURE_PAIRS), len(cols), r * len(cols) + c + 1, projection="3d")
            m, fp, pcs = sk.build_sdf_creature(g, pv)
            title = f"{title}: body has {lab.beads(g.parts[0])} hump{'s' if lab.beads(g.parts[0]) != 1 else ''}"
            sk.draw_mesh(ax, m, sk.ancestry_colours(g, pcs, fp), title, light=(0.5, -0.6, 0.7))
            ax.view_init(elev=18, azim=-58)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.92, bottom=0.0, wspace=0.0, hspace=0.08)
    fig.savefig(out / "bead_fixes.png", dpi=100)
    plt.close(fig)

    (out / "results.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"Done -> {out.resolve()}")


if __name__ == "__main__":
    main()
