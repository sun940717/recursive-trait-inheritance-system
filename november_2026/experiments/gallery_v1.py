#!/usr/bin/env python3
"""
gallery_v1.py
=============
The unselected gallery of RTIS experiment plan v1 ("展示"): 15 pairs x seed 7 x both directions = 30
children, each made by the frozen ..\\code\\rtis_run_once.py, all shown, none picked out.
RTIS 實驗計畫 v1 的展示：15 組 × 種子 7 × 兩個方向＝30 個子代，全部用凍結的 rtis_run_once.py 產生，全部放、不挑。

Usage (PowerShell, in RTIS\\current_2026-11\\experiments) / 用法:
  D:\\rtis_env\\Scripts\\python.exe gallery_v1.py
Output: gallery\\<A>_x_<B>_seed7\\ (one rtis_run_once.py folder each), gallery\\gallery_v1.png (contact sheet
of the 30 run_overview.png images, PASS/FAIL in each title), gallery\\gallery_v1.json.
A failed run is kept in the sheet as a grey tile with its error. / 執行失敗的也放進總表（灰色格子並寫出錯誤）。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
FORMS = ("quadruped", "biped", "spider", "serpent", "jellyfish", "crab")
SEED = 7


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out = HERE / "gallery"
    out.mkdir(exist_ok=True)
    env = {**__import__("os").environ, "PYTHONPATH": str(HERE.parent.parent / "rtis")}
    runs = []
    for i in range(6):
        for j in range(i + 1, 6):
            for a, b in ((FORMS[i], FORMS[j]), (FORMS[j], FORMS[i])):
                folder = out / f"{a}_x_{b}_seed{SEED}"
                cmd = [sys.executable, "rtis_run_once.py", "--a", a, "--b", b, "--seed", str(SEED),
                       "--out", str(out)]          # rtis_run_once.py makes <out>\\<A>_x_<B>_seed7\\ itself
                p = subprocess.run(cmd, cwd=CODE, env=env, capture_output=True, text=True, encoding="utf-8",
                                   errors="replace")
                last = (p.stdout.strip().splitlines() or [""])[-1]
                ok = "PASS" in last
                runs.append({"a": a, "b": b, "folder": folder.name, "returncode": p.returncode, "last_line": last,
                             "pass": ok, "stderr_tail": p.stderr[-500:]})
                print(f"{a:>9} x {b:<9} {'PASS' if ok else 'FAIL'}  {last[:70]}", flush=True)
    fig, axes = plt.subplots(6, 5, figsize=(25, 30))
    for ax, r in zip(axes.ravel(), runs):
        img = out / r["folder"] / "run_overview.png"
        if img.exists():
            ax.imshow(plt.imread(str(img)))
        else:
            ax.set_facecolor("0.85")
            ax.text(0.5, 0.5, r["stderr_tail"][-200:] or "no image", ha="center", va="center", fontsize=6, wrap=True)
        ax.set_title(f"{r['a']} x {r['b']} · {'PASS' if r['pass'] else 'FAIL'}", fontsize=12,
                     color="black" if r["pass"] else "red")
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle(f"RTIS v1 gallery: all 30 children, seed {SEED}, not selected", fontsize=18)
    fig.tight_layout()
    fig.savefig(out / "gallery_v1.png", dpi=80)
    summary = {"seed": SEED, "children": len(runs), "pass": sum(r["pass"] for r in runs), "runs": runs}
    (out / "gallery_v1.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"PASS {summary['pass']} / {len(runs)} -> {out / 'gallery_v1.png'}")


if __name__ == "__main__":
    main()
