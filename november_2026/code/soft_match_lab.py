#!/usr/bin/env python3
"""
soft_match_lab.py
=================
Borderline matches decided by chance: a pair of parts whose PCE score is in between "clearly the same"
and "clearly different" counts as the same part in some matings and not in others. After that decision,
inheritance runs as usual.
邊界配對交給機率決定：PCE 分數介於「明顯相同」與「明顯不同」之間的一組部位，在某些交配中算同一種部位，
在其他交配中不算。決定之後，遺傳流程照常進行。

Rule / 規則:
  score >= 0.40          always matched / 一定配對
  0.25 <= score < 0.40   matched with chance (score - 0.25) / 0.15 / 依分數決定機率
  score <  0.25          never matched / 不配對
  Clear matches are settled first. Each part then gets at most one roll: if the roll fails, the part
  stays unmatched in this mating (otherwise a part with four borderline partners would get four tries).
  先處理明確的配對；之後每個部位最多擲一次，沒中就在這次交配中維持沒有對象
  （否則有四個邊界對象的部位會有四次機會）。

Requires, in the same folder: fourier3d_demo.py, fourier_genetics.py, skeleton_sdf_demo.py,
form_fusion_lab.py (2026-11-14 version: fuse() accepts pairs=), pce_match_test.py, and RTIS's pce.py
and ontology.py. Target: Python 3.10.12 · numpy, matplotlib, scikit-image, scipy.
需要同資料夾的上述檔案，以及 RTIS 的 pce.py 與 ontology.py。

Modes compared (everything else is the adopted rule set: relative genes, grafting, linkage 1)
比較的模式（其餘都是已採用的規則：相對基因、嫁接、連鎖 1）:
  strict   borderline pairs never match (threshold 0.40) / 邊界配對一律不算
  soft     borderline pairs match by chance / 邊界配對依機率
  loose    borderline pairs always match (threshold 0.25) / 邊界配對一律算

Measures / 量測:
  outcome of a borderline pair in one child / 一組邊界配對在一個子代身上的結果:
      matched (one part in that place), kept both, kept one, kept neither
      配上（那個位置只有一個部位）、兩個都留、只留一個、都沒留
  swallowed limb   at least half of the outer three quarters of a limb lies inside another limb
                   一條肢體外側四分之三有一半以上埋在另一條肢體裡
  (A second measure, "two limbs whose bases are closer than the thicker base radius", was tried first and
  removed: it fired on four of the six founder forms, so it could not tell good bodies from bad ones.)
  （原本還有第二個指標「兩條肢體的根部距離小於較粗那條的根部半徑」，已移除：六種原始形體中有四種
  會觸發它，分不出好壞。）

Outputs (default ./out_soft) / 輸出:
  soft_match_children.png   parents, a child where the pair matched, a child where it did not
  results.json              every number printed by this run

Usage / 用法:
  python soft_match_lab.py
  python soft_match_lab.py --children 20 --seed 3
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import time
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import skeleton_sdf_demo as sk  # noqa: E402
import form_fusion_lab as lab  # noqa: E402
from form_fusion_lab import FuseOptions  # noqa: E402
from pce import semantic_similarity_layered  # noqa: E402
from pce_match_test import retag  # noqa: E402

LOW, HIGH = 0.25, 0.40
MODES = ("strict", "soft", "loose")
ADOPTED = FuseOptions(relative=True, graft=True, linkage=1)
FIGURE_PAIRS = [("quadruped", "biped"), ("biped", "spider"), ("serpent", "crab")]


def match_chance(score: float, low: float = LOW, high: float = HIGH) -> float:
    """0 below low, 1 from high up, a straight line in between. / low 以下 0，high 以上 1，中間直線。"""
    return float(np.clip((score - low) / (high - low), 0.0, 1.0))


def soft_match(ga, gb, rng: np.random.Generator, mode: str = "soft", sim=semantic_similarity_layered,
               low: float = LOW, high: float = HIGH):
    """Returns (pairs, decisions). pairs is what lab.fuse(..., pairs=) expects, root pair included.
    decisions lists every borderline pair that came up for a decision in this mating.
    sim, low, high: the similarity function and the two ends of the chance line (defaults = the rule above).
    回傳（配對、決定）。配對可直接交給 lab.fuse；決定列出這次交配中每一組被拿出來決定的邊界配對。
    sim、low、high：相似度函式與機率直線的兩個端點（預設就是上面的規則）。"""
    root_a = next(p for p in ga.parts if p.parent is None)
    root_b = next(p for p in gb.parts if p.parent is None)
    pairs = [{"a": root_a.name, "b": root_b.name, "score": 1.0, "how": "root"}]
    used_a, used_b = {root_a.name}, {root_b.name}
    cand = []
    for pa in ga.parts:
        for pb in gb.parts:
            if pa.parent is None or pb.parent is None:
                continue
            s = float(sim(pa.tags, pb.tags))
            if s >= low:
                cand.append((s + 0.25 * (1.0 - abs(pa.attach - pb.attach)), s, pa.name, pb.name))
    cand.sort(key=lambda c: -c[0])
    for _, s, na, nb in cand:                                   # clear matches first / 先處理明確的配對
        if s >= high and na not in used_a and nb not in used_b:
            pairs.append({"a": na, "b": nb, "score": s, "how": "clear"})
            used_a.add(na)
            used_b.add(nb)
    decisions, rolled_a, rolled_b = [], set(), set()
    for _, s, na, nb in cand:                                   # then the borderline ones / 再處理邊界配對
        if s >= high or na in used_a or nb in used_b or na in rolled_a or nb in rolled_b:
            continue
        chance = match_chance(s, low, high)
        matched = {"strict": False, "loose": True}.get(mode)
        if matched is None:
            matched = bool(rng.random() < chance)
        rolled_a.add(na)
        rolled_b.add(nb)
        decisions.append({"a": na, "b": nb, "score": s, "chance": chance, "matched": matched})
        if matched:
            pairs.append({"a": na, "b": nb, "score": s, "how": "borderline"})
            used_a.add(na)
            used_b.add(nb)
    return pairs, decisions


def kind(name: str) -> str:
    """leg_1 ... leg_4 -> leg (serial repeats reported together). / 重複的部位合併回報。"""
    return re.sub(r"_\d+$", "", name)


def outcome(decision: dict, sources: dict) -> str:
    a, b = sources.get(f"A.{decision['a']}"), sources.get(f"B.{decision['b']}")
    if decision["matched"]:
        return "matched" if a is not None else "kept neither"
    return "kept both" if (a and b) else ("kept one" if (a or b) else "kept neither")


# =============================================================================
# Main / 主程式
# =============================================================================

def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Borderline matches decided by chance")
    ap.add_argument("--out", default="out_soft")
    ap.add_argument("--preview-voxel", type=float, default=0.03)
    ap.add_argument("--children", type=int, default=16, help="children per pair per mode / 每組每種模式的子代數")
    ap.add_argument("--draws", type=int, default=2000, help="matings per pair for the match-rate check")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pv = args.preview_voxel
    forms = retag(lab.all_forms(), False)            # ontology.py tags / 改用 ontology.py 的標籤
    names = list(forms)
    cfg = sk.SkeletonInheritanceConfig(micro_budget=0)
    report: dict = {"low": LOW, "high": HIGH, "preview_voxel": pv, "children_per_cell": args.children,
                    "seed": args.seed}

    # ---- 1. how often does each borderline pair match? / 每組邊界配對多常配上？ --------------------------
    print(f"1. Borderline pairs, {args.draws} matings per pair of forms (matching only, no bodies built)")
    print(f"{'pair of parts':<44}{'PCE score':>10}{'chance':>8}{'matched':>9}")
    report["match_rates"], affected = {}, []
    for a, b in itertools.combinations(names, 2):
        rng = np.random.default_rng([args.seed, names.index(a), names.index(b), 1])
        tally: dict[str, list] = {}
        for _ in range(args.draws):
            _, decisions = soft_match(forms[a], forms[b], rng, "soft")
            seen = set()
            for d in decisions:
                key = f"{a}.{kind(d['a'])} ~ {b}.{kind(d['b'])}"
                row = tally.setdefault(key, [d["score"], d["chance"], 0])
                if d["matched"] and key not in seen:
                    row[2] += 1
                    seen.add(key)
        if tally:
            affected.append((a, b))
        for key, (score, chance, hits) in tally.items():
            report["match_rates"][key] = {"score": score, "chance": chance, "matched": hits / args.draws}
            print(f"{key:<44}{score:>10.3f}{chance:>8.0%}{hits / args.draws:>9.0%}")
    print(f"  pairs of forms with at least one borderline pair: {len(affected)} of 15")

    # ---- 2. founders: is the crowding measure quiet on bodies we know are fine? ---------------------------
    print("\n2. Crowding on the six founders / 六種原始形體的擁擠情形")
    report["founder_crowding"] = {}
    for n, g in forms.items():
        c = lab.crowding(g)
        report["founder_crowding"][n] = c
        print(f"  {n:<10} swallowed limbs {len(c['swallowed'])}" + (f"   {c['swallowed']}" if c["swallowed"] else ""))

    # ---- 3. children under the three modes / 三種模式的子代 ------------------------------------------------
    stats = {m: [] for m in MODES}
    keep: dict[tuple, object] = {}
    t0 = time.perf_counter()
    for a, b in affected:
        print(f"  breeding {a} x {b} ...", flush=True)
        ga, gb = sk.with_ancestry(forms[a], 1.0), sk.with_ancestry(forms[b], 0.0)
        for mode in MODES:
            rng = np.random.default_rng([args.seed, names.index(a), names.index(b), 2])
            for _ in range(args.children):
                pairs, decisions = soft_match(ga, gb, rng, mode)
                child, log = lab.fuse(ga, gb, rng, cfg, ADOPTED, pairs=pairs)
                mesh, _, _ = sk.build_sdf_creature(child, pv)
                outer, bubbles = lab.shells(mesh)
                share = lab.ancestry_share(child)
                crowd = lab.crowding(child)
                outs = [outcome(d, log["sources"]) for d in decisions]
                # is the swallowed limb one of the two parts of a borderline pair that were both kept?
                # 被吞掉的是不是「兩個都留」的那組邊界配對本身？
                own, by_kind = 0, []
                for d, o in zip(decisions, outs):
                    hit = False
                    if o == "kept both":
                        key = tuple(sorted((log["sources"][f"A.{d['a']}"], log["sources"][f"B.{d['b']}"])))
                        hit = key in crowd["swallowed"]
                        own += hit
                    by_kind.append([f"{a}.{kind(d['a'])} ~ {b}.{kind(d['b'])}", o, bool(hit)])
                stats[mode].append({
                    "pair": f"{a} x {b}", "valid": bool(sk.mesh_report(mesh)["closed"] and outer == 1),
                    "bubbles": int(bubbles), "parts": len(child.parts), "minority": min(share, 1.0 - share),
                    "new_humps": float(np.mean(log["extra_beads"])), "new_kinks": float(np.mean(log["extra_bend"])),
                    "outer_shells": int(outer), "swallowed": len(crowd["swallowed"]), "swallowed_own_pair": own,
                    "crowd_detail": crowd, "outcomes": outs, "by_kind": by_kind})
                if mode == "soft":
                    for tag in ("matched", "kept both"):
                        if tag in outs:
                            keep.setdefault((a, b, tag), child)
    n_rows = len(affected) * args.children
    print(f"\n3. {len(affected)} pairs of forms x {args.children} children per mode = {n_rows} children per mode"
          f" ({time.perf_counter() - t0:.0f} s)")
    print(f"{'mode':<8}{'one closed body':>17}{'bubbles':>9}{'parts':>7}{'smaller parent':>16}{'new humps':>11}"
          f"{'new kinks':>11}{'with swallowed limb':>21}")
    report["modes"] = {}
    for mode, rows in stats.items():
        flat = [o for r in rows for o in r["outcomes"]]
        agg = {"children": len(rows), "valid": sum(r["valid"] for r in rows),
               "with_bubble": sum(r["bubbles"] > 0 for r in rows),
               "parts": float(np.mean([r["parts"] for r in rows])),
               "minority_share": float(np.mean([r["minority"] for r in rows])),
               "new_humps": float(np.mean([r["new_humps"] for r in rows])),
               "new_kinks_deg": float(np.mean([r["new_kinks"] for r in rows])),
               "with_swallowed": sum(r["swallowed"] > 0 for r in rows),
               "outcomes": {k: flat.count(k) for k in ("matched", "kept both", "kept one", "kept neither")}}
        report["modes"][mode] = agg
        print(f"{mode:<8}{agg['valid']:>10} / {agg['children']:<4}{agg['with_bubble']:>9}{agg['parts']:>7.1f}"
              f"{agg['minority_share']:>16.0%}{agg['new_humps']:>11.2f}{agg['new_kinks_deg']:>7.0f} deg"
              f"{agg['with_swallowed']:>14} / {agg['children']}")
        for r in rows:
            if not r["valid"]:
                print(f"         not one closed body: {r['pair']}, outer shells {r['outer_shells']}, parts {r['parts']}")

    print("\n   What happened to the borderline pairs / 邊界配對的結果")
    print(f"{'mode':<8}{'decisions':>10}{'matched':>9}{'kept both':>11}{'kept one':>10}{'kept neither':>14}")
    for mode in MODES:
        o = report["modes"][mode]["outcomes"]
        print(f"{mode:<8}{sum(o.values()):>10}{o['matched']:>9}{o['kept both']:>11}{o['kept one']:>10}{o['kept neither']:>14}")

    print("\n   Soft mode, by borderline pair / 依邊界配對分列（soft 模式）")
    print(f"{'pair of parts':<44}{'decisions':>10}{'matched':>9}{'kept both':>11}{'kept both and one swallowed':>29}")
    table: dict[str, list[int]] = {}
    for r in stats["soft"]:
        for label, o, hit in r["by_kind"]:
            row = table.setdefault(label, [0, 0, 0, 0])
            row[0] += 1
            row[1] += o == "matched"
            row[2] += o == "kept both"
            row[3] += hit
    report["soft_by_pair"] = {k: dict(zip(("decisions", "matched", "kept_both", "kept_both_swallowed"), v))
                              for k, v in table.items()}
    for label, (n, m, kb, sw) in table.items():
        print(f"{label:<44}{n:>10}{m:>9}{kb:>11}{sw:>29}")
    report["swallowed_limbs"] = {}
    for mode in MODES:
        which: dict[str, int] = {}
        for r in stats[mode]:
            for key in r["crowd_detail"]["swallowed"]:
                label = f"{r['pair']}: {kind(key[0])} + {kind(key[1])}"
                which[label] = which.get(label, 0) + 1
        report["swallowed_limbs"][mode] = which
        print(f"   swallowed limbs, {mode}: "
              + ("; ".join(f"{k} ({v})" for k, v in sorted(which.items(), key=lambda kv: -kv[1])) or "none"))

    # ---- figure -------------------------------------------------------------------------------------------
    cols = ["parent A", "parent B", "child: pair matched", "child: pair not matched, kept both"]
    fig = plt.figure(figsize=(3.6 * len(cols), 3.6 * len(FIGURE_PAIRS)))
    fig.suptitle("Borderline pair decided by chance - same parents, two outcomes; colour = ancestry (orange A, blue B)",
                 fontsize=13)
    for r, (a, b) in enumerate(FIGURE_PAIRS):
        cells = [(f"A: {a}", sk.with_ancestry(forms[a], 1.0)), (f"B: {b}", sk.with_ancestry(forms[b], 0.0)),
                 ("matched", keep.get((a, b, "matched"))), ("kept both", keep.get((a, b, "kept both")))]
        for c, (title, g) in enumerate(cells):
            ax = fig.add_subplot(len(FIGURE_PAIRS), len(cols), r * len(cols) + c + 1, projection="3d")
            if g is None:
                ax.set_axis_off()
                ax.set_title(f"{title}: did not occur in this run", fontsize=9)
                continue
            m, fp, pcs = sk.build_sdf_creature(g, pv)
            sk.draw_mesh(ax, m, sk.ancestry_colours(g, pcs, fp), f"{title} ({len(g.parts)} parts)",
                         light=(0.5, -0.6, 0.7))
            ax.view_init(elev=18, azim=-58)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.92, bottom=0.0, wspace=0.0, hspace=0.08)
    fig.savefig(out / "soft_match_children.png", dpi=100)
    plt.close(fig)

    for rows in stats.values():
        for r in rows:
            r.pop("crowd_detail")
    report["children"] = stats
    (out / "results.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"Done -> {out.resolve()}")


if __name__ == "__main__":
    main()
