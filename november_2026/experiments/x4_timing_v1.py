#!/usr/bin/env python3
"""
x4_timing_v1.py
===============
X4 of RTIS experiment plan v1 (section 5): build time on this computer.
RTIS 實驗計畫 v1 第五節的 X4：在這台電腦上的建構時間。

  The six forms and 15 children (seed 1, direction A x B, current rules), at grid 0.03 and 0.02.
  Each: 1 warm-up, then 5 timed runs; median and range. Only generation + mesh extraction is timed
  (no measures, no saving). Hardware and thread count are recorded.
  六種形體與 15 個子代（種子 1、A×B、現行規則），格點 0.03 與 0.02；每個先暖機 1 次再計時 5 次；
  只計生成與取網格，不含指標與存檔；記下硬體與執行緒數。

Usage (PowerShell, in RTIS\\current_2026-11\\experiments) / 用法:
  D:\\rtis_env\\Scripts\\python.exe x4_timing_v1.py
Writes results\\x4_timing_v1.json and .md. Close other heavy programs first.
輸出 results\\x4_timing_v1.json 與 .md。跑之前先關掉其他吃資源的程式。
"""

from __future__ import annotations

import json
import os
import platform
import statistics
import time
from pathlib import Path

import run_v1 as R          # sets up paths to ..\code and ..\..\rtis / 設定路徑
import numpy as np
import skeleton_sdf_demo as sk
import form_fusion_lab as lab

WARMUP, REPEATS, GRIDS = 1, 5, (0.03, 0.02)


def child_of(pair: int):
    """Child for (pair, direction 0, seed 1) exactly as in X1's pce condition. / 與 X1 pce 條件相同的子代。"""
    child, *_ = R.make_child("pce", pair, 0, 1)
    return child


def time_build(genome, voxel: float) -> list[float]:
    for _ in range(WARMUP):
        sk.build_sdf_creature(genome, voxel)
    out = []
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        sk.build_sdf_creature(genome, voxel)
        out.append(time.perf_counter() - t0)
    return out


def main() -> None:
    forms = lab.all_forms(ontology_tags=True)
    items = [(f"form:{n}", g) for n, g in forms.items()]
    items += [(f"child:{R.FORMS[i]}x{R.FORMS[j]}", child_of(k)) for k, (i, j) in enumerate(R.PAIRS)]
    rows = []
    for voxel in GRIDS:
        for name, g in items:
            t = time_build(g, voxel)
            rows.append({"item": name, "voxel": voxel, "median_s": statistics.median(t), "min_s": min(t),
                         "max_s": max(t), "runs": t})
            print(f"{voxel}  {name:<28} median {statistics.median(t):.3f} s", flush=True)
    summary = {}
    for voxel in GRIDS:
        for kind in ("form", "child"):
            med = [r["median_s"] for r in rows if r["voxel"] == voxel and r["item"].startswith(kind)]
            summary[f"{kind}_{voxel}"] = {"median_of_medians_s": statistics.median(med), "min_s": min(med),
                                          "max_s": max(med), "n": len(med)}
    res = {"experiment": "X4", "plan": "RTIS_實驗計畫_v1.md section 5", "warmup": WARMUP, "repeats": REPEATS,
           "python": platform.python_version(), "platform": platform.platform(), "processor": platform.processor(),
           "cpu_count": os.cpu_count(), "numpy": np.__version__,
           "threads_env": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")},
           "summary": summary, "rows": rows}
    out = Path(__file__).resolve().parent / "results"
    out.mkdir(exist_ok=True)
    (out / "x4_timing_v1.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    lines = ["# X4 build time / 建構時間", "", f"{res['platform']} · {res['processor']} · {res['cpu_count']} logical CPUs · "
             f"Python {res['python']} · numpy {res['numpy']}", "", "| what | grid | median of medians (s) | range (s) |",
             "|---|---|---|---|"]
    for k, v in summary.items():
        kind, voxel = k.split("_")
        lines.append(f"| {kind} | {voxel} | {v['median_of_medians_s']:.3f} | {v['min_s']:.3f} – {v['max_s']:.3f} |")
    (out / "x4_timing_v1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
