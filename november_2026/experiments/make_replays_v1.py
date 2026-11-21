#!/usr/bin/env python3
"""
make_replays_v1.py
==================
Makes "RTIS 生成重播" pages (the same replay as the main figure) for chosen children of the gallery.
Uses the frozen ..\\code\\replay_export.py and replay_template.html as they are, on the runs that
gallery_v1.py saved in gallery\\. Each page is one self-contained .html file; open it in a browser.
用凍結的 replay_export.py 與 replay_template.html，替全套圖（gallery\\）裡選定的子代做重播網頁。
每一頁是一個獨立的 .html 檔，用瀏覽器打開即可。

Usage (PowerShell, in RTIS\\current_2026-11\\experiments; run gallery_v1.py first) / 用法（先跑過 gallery_v1.py）:
  D:\\rtis_env\\Scripts\\python.exe make_replays_v1.py
  D:\\rtis_env\\Scripts\\python.exe make_replays_v1.py quadruped:crab jellyfish:crab
  D:\\rtis_env\\Scripts\\python.exe make_replays_v1.py --all          # all 30 / 全部 30 個
Output: replays\\<A>_x_<B>_seed7.html  /  輸出：replays\\<A>_x_<B>_seed7.html
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
GALLERY = HERE / "gallery"
OUT = HERE / "replays"
SEED = 7
FORMS = ("quadruped", "biped", "spider", "serpent", "jellyfish", "crab")
# default: the main figure, two passing, one passing jellyfish pair, two failing jellyfish pairs
# 預設：主圖、兩組通過、一組通過的水母配對、兩組失敗的水母配對
DEFAULT = ["biped:spider", "quadruped:crab", "spider:serpent", "serpent:jellyfish", "jellyfish:crab",
           "quadruped:jellyfish"]


def make(a: str, b: str) -> str:
    name = f"{a}_x_{b}_seed{SEED}"
    if not (GALLERY / name / "run.json").exists():
        return f"{name}: no gallery run (run gallery_v1.py first) / 沒有全套圖的執行結果"
    OUT.mkdir(exist_ok=True)
    data_path = OUT / f"{name}.json"
    env = {**os.environ, "PYTHONPATH": str(HERE.parent.parent / "rtis"), "MPLBACKEND": "Agg"}
    p = subprocess.run([sys.executable, "replay_export.py", "--a", a, "--b", b, "--seed", str(SEED),
                        "--run-dir", str(GALLERY), "--out", str(data_path)],
                       cwd=CODE, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return f"{name}: replay_export failed / 失敗\n{p.stderr[-800:]}"
    data = data_path.read_text(encoding="utf-8")
    if "</script" in data:
        return f"{name}: data contains </script, page not built / 資料含 </script，未產生網頁"
    html = (CODE / "replay_template.html").read_text(encoding="utf-8").replace("/*DATA*/", data)
    target = OUT / f"{name}.html"
    target.write_text(html, encoding="utf-8")
    return f"{name}: {target} ({len(html) / 1e6:.1f} MB)"


def main(argv: list[str]) -> None:
    if "--all" in argv:
        pairs = [(FORMS[i], FORMS[j]) for i in range(6) for j in range(6) if i != j]
    else:
        pairs = [tuple(x.split(":")) for x in (argv or DEFAULT)]
    for a, b in pairs:
        if a not in FORMS or b not in FORMS:
            print(f"{a}:{b}: unknown form; use {', '.join(FORMS)}")
            continue
        print(make(a, b), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
