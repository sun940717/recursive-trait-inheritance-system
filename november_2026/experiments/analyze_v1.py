#!/usr/bin/env python3
"""
analyze_v1.py
=============
The analysis of RTIS experiment plan v1, section 6, exactly as pre-registered, applied to data\\X1.csv
and data\\X2.csv. Every number in the report comes from this file.
RTIS 實驗計畫 v1 第六節的分析，照事先登記的做法，套用在 data\\X1.csv 與 data\\X2.csv。報告裡的每個數字都出自這個檔案。

Observation (plan section 3) / 觀察值:
  one pair, one seed: the mean of the two directions (0, 0.5 or 1 for passing).
  一組配對、一個種子：兩個方向的平均（合格與否時值是 0、0.5 或 1）。
Estimand / 估計的量:
  Delta = (1/15) sum over pairs of the mean over seeds of (condition - reference), in percentage points
  for rates. Every pair weighs the same. / 15 組等權平均的成對差。
Test / 檢定: within each pair, flip the sign of each seed's paired difference at random; 20,000 flips;
  two-sided; p = (1 + #|Delta*| >= |Delta|) / (1 + 20,000). / 組內符號翻轉。
Interval / 區間: within each pair resample seeds (paired) with replacement, 10,000 times; 95% percentile.
Confirmatory (one) / 確認性（只有一個）: X1, PCE vs same-K random, outcome = passing (pass_geo).
Secondary / 次要: X1 G5 (parts kept) by the same method; X2 six comparisons against the full rule set
  (the X1 pce rows), each on its designated measure, Holm-adjusted as one family. For "site_off" and
  "strict" the plan names two measures; the first one (G3 buried parts; passing) is the one in the Holm
  family, the second (G5) is reported with the same method but outside the family.
  X2 的六個比較各用指定的指標，Holm 校正為一個家族。site_off 與 strict 計畫列了兩個指標：第一個進 Holm 家族，
  第二個（G5）用同樣的方法報告，但不在家族裡。（這是寫分析時定下的細節，不改計畫。）
Interpretation rule (plan section 4) / 解讀規則: a condition is written as better only if its pass rate is
  higher and its parts-kept rate is not lower by more than 5 percentage points.

Usage / 用法:
  python analyze_v1.py                 # reads data\\, writes results\\analysis_v1.json and analysis_v1.md
Target: Python 3.10.12 · numpy.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ANALYSIS_VERSION = "analyze_v1.0"
N_FLIPS, N_BOOT, RNG_SEED = 20_000, 10_000, 20261116
FORMS = ("quadruped", "biped", "spider", "serpent", "jellyfish", "crab")
PAIR_NAMES = {}
_k = 0
for _i in range(6):
    for _j in range(_i + 1, 6):
        PAIR_NAMES[_k] = f"{FORMS[_i]} x {FORMS[_j]}"
        _k += 1
JELLY = [p for p, n in PAIR_NAMES.items() if "jellyfish" in n]

# measure name -> function of a CSV row (higher = more of it) / 指標 -> 由一列算出的值
MEASURES = {
    "pass": lambda r: float(r["pass_geo"]),
    "kept": lambda r: float(r["sources_kept"]) / float(r["sources_total"]),
    "buried": lambda r: float(r["n_buried"]),
    "hidden": lambda r: float(r["n_hidden_010"]),
    "bend": lambda r: float(r["new_bend_deg"]),
    "humps": lambda r: float(r["new_humps"]),
    "minority": lambda r: min(float(r["share_from_a"]), 1.0 - float(r["share_from_a"])),
    "both10": lambda r: float(0.1 <= float(r["share_from_a"]) <= 0.9),
    "g1": lambda r: float(r["g1_closed"] == "1" and r["g1_manifold"] == "1" and r["outer_shells"] == "1"),
    "bubbles": lambda r: float(int(r["bubbles"]) > 0),
    "parts": lambda r: float(r["parts"]),
    "m3": lambda r: float(r["legacy_m3_pairs"]),
}
PERCENT = {"pass", "kept", "both10", "g1", "bubbles", "minority"}
X2_FAMILY = [("relative_off", "bend"), ("linkage_off", "humps"), ("graft_off", "kept"),
             ("site_off", "buried"), ("strict", "pass"), ("attr", "hidden")]
X2_EXTRA = [("site_off", "kept"), ("strict", "kept")]


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def observations(rows: list[dict], measure: str) -> dict:
    """{condition: array (15 pairs, n seeds)} of observations; seeds sorted. A row with status != ok counts
    as not passing for "pass" and is left out (NaN) for other measures.
    status 不是 ok 的列：合格判為 0；其他指標記 NaN。"""
    f = MEASURES[measure]
    acc: dict = defaultdict(lambda: defaultdict(list))
    seeds = sorted({int(r["seed"]) for r in rows})
    s_index = {s: i for i, s in enumerate(seeds)}
    out = {}
    for r in rows:
        if r["status"] == "ok":
            v = f(r)
        else:
            v = 0.0 if measure == "pass" else float("nan")
        acc[r["condition"]][(int(r["pair"]), int(r["seed"]))].append(v)
    for cond, cells in acc.items():
        arr = np.full((15, len(seeds)), np.nan)
        for (p, s), vals in cells.items():
            if len(vals) != 2:
                raise ValueError(f"{cond} pair {p} seed {s}: {len(vals)} directions")
            arr[p, s_index[s]] = float(np.mean(vals))
        out[cond] = arr
    return out


def delta(diff: np.ndarray) -> float:
    return float(np.nanmean(np.nanmean(diff, axis=1)))


def paired_test(cond: np.ndarray, ref: np.ndarray, rng: np.random.Generator) -> dict:
    """Delta, sign-flip p, bootstrap 95% interval, per-pair numbers. / 成對比較的全部數字。"""
    diff = cond - ref
    d0 = delta(diff)
    valid = ~np.isnan(diff)
    filled = np.where(valid, diff, 0.0)
    counts = valid.sum(axis=1)
    # sign flips, done in blocks to bound memory / 分批做符號翻轉
    hits, done = 0, 0
    while done < N_FLIPS:
        b = min(2000, N_FLIPS - done)
        signs = rng.choice([-1.0, 1.0], size=(b,) + diff.shape)
        stat = ((signs * filled).sum(axis=2) / np.maximum(counts, 1)).mean(axis=1)
        hits += int(np.sum(np.abs(stat) >= abs(d0) - 1e-12))
        done += b
    p = (1 + hits) / (1 + N_FLIPS)
    boots = np.empty(N_BOOT)
    n_seeds = diff.shape[1]
    for t in range(N_BOOT):
        idx = rng.integers(0, n_seeds, size=(15, n_seeds))
        boots[t] = delta(np.take_along_axis(diff, idx, axis=1))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    per_pair = np.nanmean(diff, axis=1)
    return {"delta": d0, "p_sign_flip": p, "ci95": [float(lo), float(hi)],
            "pairs_better": int(np.sum(per_pair > 1e-12)), "pairs_worse": int(np.sum(per_pair < -1e-12)),
            "pairs_same": int(np.sum(np.abs(per_pair) <= 1e-12)),
            "observations_different": int(np.sum(np.abs(np.nan_to_num(diff)) > 1e-12)),
            "observations": int(valid.sum()),
            "per_pair": {PAIR_NAMES[p]: {"condition": float(np.nanmean(cond[p])), "reference": float(np.nanmean(ref[p])),
                                         "difference": float(per_pair[p])} for p in range(15)}}


def holm(ps: list[float]) -> list[float]:
    order = np.argsort(ps)
    m, adj, running = len(ps), [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * ps[i])
        adj[i] = min(1.0, running)
    return adj


def describe(rows: list[dict]) -> dict:
    """Mean of every measure per condition (equal weight per pair), all 15 pairs and the jellyfish split.
    每個條件、每個指標的平均（每組等權），以及水母分開的數字。"""
    out: dict = {}
    for m in MEASURES:
        obs = observations(rows, m)
        for cond, arr in obs.items():
            per_pair = np.nanmean(arr, axis=1)
            other = [p for p in range(15) if p not in JELLY]
            out.setdefault(cond, {})[m] = {"all": float(per_pair.mean()), "jellyfish_5": float(per_pair[JELLY].mean()),
                                           "other_10": float(per_pair[other].mean())}
    return out


def k_distribution(rows: list[dict]) -> dict:
    ks = [int(r["k_matched"]) for r in rows if r["condition"] == "pce" and r["status"] == "ok"]
    vals, counts = np.unique(ks, return_counts=True)
    return {"counts": {int(v): int(c) for v, c in zip(vals, counts)}, "share_k0": float(np.mean(np.array(ks) == 0)),
            "share_k0_or_1": float(np.mean(np.array(ks) <= 1)), "rows": len(ks)}


def pct(x: float, m: str) -> str:
    return f"{100 * x:.1f}%" if m in PERCENT else f"{x:.3f}"


def pp(x: float, m: str) -> str:
    return f"{100 * x:+.1f} pp" if m in PERCENT else f"{x:+.3f}"


def pv(p: float) -> str:
    """p values at the floor of the sign-flip test are written as < 0.0001. / 到達下限的 p 值寫成 < 0.0001。"""
    return "< 0.0001" if p < 1e-4 else f"{p:.4f}"


def report_md(res: dict) -> str:
    L = ["# RTIS experiment plan v1: results (X1, X2)", "",
         f"Analysis `{res['analysis_version']}` · data code_hash `{', '.join(res['code_hash'])}` · "
         f"Python {res['python']} · {res['rows']['X1']} + {res['rows']['X2']} rows, errors: {res['errors']}", ""]
    c = res["confirmatory"]
    L += ["## Confirmatory: PCE vs same-K random, passing", "",
          f"- Delta = **{pp(c['delta'], 'pass')}** (95% CI {pp(c['ci95'][0], 'pass')} to {pp(c['ci95'][1], 'pass')}), "
          f"sign-flip p {pv(c['p_sign_flip'])}",
          f"- pairs better / worse / same: {c['pairs_better']} / {c['pairs_worse']} / {c['pairs_same']}; "
          f"observations that differ: {c['observations_different']} of {c['observations']}",
          f"- K (non-root pairs matched by PCE), share K = 0: {100 * res['k']['share_k0']:.1f}%, K <= 1: "
          f"{100 * res['k']['share_k0_or_1']:.1f}%; counts {res['k']['counts']}",
          f"- G5 parts kept, same method (secondary): Delta {pp(res['x1_kept']['delta'], 'kept')} "
          f"(95% CI {pp(res['x1_kept']['ci95'][0], 'kept')} to {pp(res['x1_kept']['ci95'][1], 'kept')}), "
          f"p {pv(res['x1_kept']['p_sign_flip'])}",
          f"- interpretation rule: **{res['interpretation']}**", "",
          "| pair | PCE pass | random pass | difference |", "|---|---|---|---|"]
    for name, v in c["per_pair"].items():
        L.append(f"| {name} | {pct(v['condition'], 'pass')} | {pct(v['reference'], 'pass')} | {pp(v['difference'], 'pass')} |")
    L += ["", "## X2: rules turned off one at a time (vs the full rule set), Holm family of six", "",
          "| condition | measure | full | condition | Delta | 95% CI | p | Holm p |", "|---|---|---|---|---|---|---|---|"]
    for row in res["x2"]:
        m = row["measure"]
        L.append(f"| {row['condition']} | {m} | {pct(row['reference_mean'], m)} | {pct(row['condition_mean'], m)} | "
                 f"{pp(row['delta'], m)} | {pp(row['ci95'][0], m)} to {pp(row['ci95'][1], m)} | {pv(row['p_sign_flip'])} | "
                 f"{pv(row.get('p_holm', float('nan')))} |" if 'p_holm' in row else
                 f"| {row['condition']} | {m} (outside family) | {pct(row['reference_mean'], m)} | {pct(row['condition_mean'], m)} | "
                 f"{pp(row['delta'], m)} | {pp(row['ci95'][0], m)} to {pp(row['ci95'][1], m)} | {pv(row['p_sign_flip'])} | – |")
    L += ["", "## Every condition, every measure (mean over 15 pairs, equal weight)", ""]
    ms = ["pass", "kept", "minority", "both10", "g1", "buried", "hidden", "bubbles", "bend", "humps", "parts", "m3"]
    L += ["| condition | " + " | ".join(ms) + " |", "|---|" + "---|" * len(ms)]
    for cond, d in res["describe"].items():
        L.append(f"| {cond} | " + " | ".join(pct(d[m]['all'], m) for m in ms) + " |")
    L += ["", "## Jellyfish split (pre-specified description) / 水母分開描述", "",
          "| condition | pass, 5 jellyfish pairs | pass, other 10 | kept, jellyfish | kept, other |", "|---|---|---|---|---|"]
    for cond, d in res["describe"].items():
        L.append(f"| {cond} | {pct(d['pass']['jellyfish_5'], 'pass')} | {pct(d['pass']['other_10'], 'pass')} | "
                 f"{pct(d['kept']['jellyfish_5'], 'kept')} | {pct(d['kept']['other_10'], 'kept')} |")
    L += ["", "minority = share of genes from the parent that gave fewer (50% = even); both10 = children where each "
          "parent gave at least 10% of the genes; m3 = old measure, recorded only.", ""]
    return "\n".join(L)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Analysis of RTIS experiment plan v1, section 6")
    ap.add_argument("--data", default=str(HERE / "data"))
    ap.add_argument("--out", default=str(HERE / "results"))
    args = ap.parse_args(argv)
    data, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    x1, x2 = load(data / "X1.csv"), load(data / "X2.csv")
    rng = np.random.default_rng(RNG_SEED)
    res: dict = {"analysis_version": ANALYSIS_VERSION, "python": platform.python_version(), "numpy": np.__version__,
                 "code_hash": sorted({r["code_hash"] for r in x1 + x2}), "rows": {"X1": len(x1), "X2": len(x2)},
                 "errors": sum(r["status"] != "ok" for r in x1 + x2),
                 "n_flips": N_FLIPS, "n_boot": N_BOOT, "rng_seed": RNG_SEED}
    p1, k1 = observations(x1, "pass"), observations(x1, "kept")
    res["confirmatory"] = paired_test(p1["pce"], p1["random_k"], rng)
    res["x1_kept"] = paired_test(k1["pce"], k1["random_k"], rng)
    res["k"] = k_distribution(x1)
    c, kk = res["confirmatory"], res["x1_kept"]
    if c["delta"] > 0 and kk["delta"] >= -0.05:
        res["interpretation"] = "PCE written as better (higher pass rate, parts kept not lower by more than 5 pp)"
    else:
        res["interpretation"] = "not written as better; the two numbers are stated separately"
    both = x1 + x2
    rows_x2 = []
    for cond, m in X2_FAMILY + X2_EXTRA:
        obs = observations(both, m)
        t = paired_test(obs[cond], obs["pce"], rng)
        rows_x2.append({"condition": cond, "measure": m, "in_family": (cond, m) in X2_FAMILY,
                        "reference_mean": float(np.nanmean(np.nanmean(obs["pce"], axis=1))),
                        "condition_mean": float(np.nanmean(np.nanmean(obs[cond], axis=1))), **t})
    fam = [r for r in rows_x2 if r["in_family"]]
    for r, a in zip(fam, holm([r["p_sign_flip"] for r in fam])):
        r["p_holm"] = a
    res["x2"] = rows_x2
    res["describe"] = describe(both)
    (out / "analysis_v1.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    md = report_md(res)
    (out / "analysis_v1.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
