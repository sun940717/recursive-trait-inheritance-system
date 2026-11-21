#!/usr/bin/env python3
"""
precheck_v1.py
==============
The seven pre-checks of RTIS experiment plan v1, section 7. All must pass before the code is frozen.
RTIS 實驗計畫 v1 第七節的七項前置檢查。全部通過才凍結程式。

  1. the six founder forms: G1 holds, no buried and no hidden part
     六種起始形體：G1 成立、沒有被埋住或看不見的部位
  2. G3 convergence: doubling the point density flips no decision in the pilot children
     G3 收斂：取點密度加倍，預跑的子代沒有任何一個判定翻轉
  3. G3 does not depend on how a chain is cut into bones (ChatGPT's example: 2 bones vs 10 bones)
     G3 與骨頭的切法無關（ChatGPT 的反例）
  4. G1 rejects two pieces that share only one vertex / G1 擋得住只共用一個頂點的兩塊
  5. G4 tells "left copy 0 triangles, right copy 30" apart (the left one is hidden)
     G4 分得出左邊 0 個面、右邊 30 個面
  6. every planned run has a row, failed ones included / 每一個預定的執行都有一列
  7. estimated time for the full run on this computer / 估計全部跑完的時間

Usage / 用法:
  python precheck_v1.py                       # checks 1, 3, 4, 5
  python precheck_v1.py --pilot pilot         # all seven, using the pilot folder
Writes precheck_v1.json next to this file (or into --pilot). / 結果寫進 precheck_v1.json。
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import sys
from pathlib import Path
from types import SimpleNamespace

import run_v1 as R          # sets up the paths to ..\code and ..\..\rtis / 設定路徑
import numpy as np
import skeleton_sdf_demo as sk
import form_fusion_lab as lab
import metrics_v1 as M

FULL_RUN = {"X1": 15 * 2 * 51 * 5, "X2": 15 * 2 * 51 * 6}


def check1() -> dict:
    out, ok = {}, True
    for name, g in lab.all_forms(ontology_tags=True).items():
        mesh, fp, _ = sk.build_sdf_creature(g, R.VOXEL)
        r12, r3, r4 = M.g1_g2(mesh), M.g3(g, R.VOXEL), M.g4(g, mesh, fp, R.VOXEL)
        good = r12["g1"] and r3["n_buried"] == 0 and r4["n_hidden_010"] == 0
        ok &= good
        out[name] = {"g1": r12["g1"], "n_buried": r3["n_buried"], "n_hidden_010": r4["n_hidden_010"],
                     "largest_share_inside": max(r["share_inside"] for r in r3["detail"]),
                     "smallest_area_ratio": min(r["ratio"] for r in r4["detail"]), "pass": bool(good)}
    return {"pass": bool(ok), "forms": out}


def check2(pilot: Path) -> dict:
    flips, children, instances = 0, 0, 0
    for exp in ("X1", "X2"):
        p = pilot / f"{exp}_detail.jsonl"
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            if "g3_density2_buried" not in d:
                continue
            a, b = d["g3_density1_buried"], d["g3_density2_buried"]
            children += 1
            instances += len(a)
            flips += sum(x != y for x, y in zip(a, b))
    return {"pass": bool(children > 0 and flips == 0), "children": children, "instances": instances,
            "decisions_flipped": flips}


def _seg(a, b, sa, sb, r=0.01):
    return SimpleNamespace(a=np.array([a, 0.0, 0.0]), b=np.array([b, 0.0, 0.0]), sa=sa, sb=sb, ra=r, rb=r)


def check3() -> dict:
    coarse = [_seg(0, 9, 0, 0.5), _seg(9, 10, 0.5, 1)]
    equal = [_seg(i, i + 1, i / 10, (i + 1) / 10) for i in range(10)]
    other = [_seg(9, 10, 0, 1)]
    spacing = 0.5 * 0.03
    c, e = M.buried_fraction(coarse, other, spacing), M.buried_fraction(equal, other, spacing)
    x = np.linspace(2.5, 10, 100001)
    ref = float(np.mean(sk.sd_round_cone(np.column_stack([x, 0 * x, 0 * x]), other[0].a, other[0].b, 0.01, 0.01) < 0))
    return {"pass": bool(abs(c - e) <= 0.02), "two_bones": c, "ten_bones": e, "dense_reference": ref,
            "old_M3_gave": {"two_bones": 0.6923, "ten_bones": 0.1475}}


def check4() -> dict:
    v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [-1, 0, 0], [0, -1, 0], [0, 0, -1]], float)
    f1 = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    f2 = np.array([[0, 5, 4], [0, 4, 6], [0, 6, 5], [4, 5, 6]])[:, ::-1]
    pinched = M.g1_g2(SimpleNamespace(vertices=v, faces=np.vstack([f1, f2])))
    single = M.g1_g2(SimpleNamespace(vertices=v[:4], faces=f1))
    return {"pass": bool((not pinched["g1"]) and single["g1"]), "pinched": pinched, "one_tetrahedron": single}


def check5() -> dict:
    face_piece = np.array([0] * 100 + [2] * 30)      # root 100 faces, left copy 0, right copy 30
    area = np.ones(len(face_piece))
    ratios = M.instance_ratios(face_piece, area, [100.0, 30.0, 30.0], measured=[1, 2])
    counts = M.hidden_counts(ratios)
    return {"pass": bool(ratios[0] < 0.10 <= ratios[1] and counts["n_hidden_010"] == 1),
            "ratios_left_right": ratios, **counts}


def check6(pilot: Path) -> dict:
    res, ok = {}, True
    for exp, conds in R.CONDITIONS.items():
        p = pilot / f"{exp}.csv"
        rows = list(csv.DictReader(p.open(encoding="utf-8", newline=""))) if p.exists() else []
        keys = [(r["condition"], int(r["pair"]), int(r["direction"]), int(r["seed"])) for r in rows]
        expected = {(c, pr, d, s) for c in conds for pr in range(15) for d in (0, 1) for s in (9001, 9002, 9003)}
        missing, extra = expected - set(keys), set(keys) - expected
        dup = len(keys) - len(set(keys))
        errors = [r for r in rows if r["status"] != "ok"]
        bad_sum = [k for r, k in zip(rows, keys) if r["status"] == "ok" and r["condition"] != "attr" and
                   int(r["sources_kept"]) + int(r["lost_not_inherited"]) + int(r["lost_orphan"])
                   + int(r["lost_site"]) != int(r["sources_total"])]
        good = not missing and not extra and dup == 0
        ok &= good
        res[exp] = {"rows": len(rows), "expected": len(expected), "missing": len(missing), "extra": len(extra),
                    "duplicates": dup, "errors": len(errors),
                    "error_messages": sorted({r["error"] for r in errors})[:10],
                    "G5_parts_not_adding_up": len(bad_sum), "pass": bool(good)}
    return {"pass": bool(ok), **res}


def check7(pilot: Path, workers: int) -> dict:
    secs = []
    for exp in ("X1", "X2"):
        p = pilot / f"{exp}.csv"
        if p.exists():
            secs += [float(r["seconds"]) for r in csv.DictReader(p.open(encoding="utf-8", newline=""))]
    if not secs:
        return {"pass": False, "note": "no pilot rows"}
    med, mean = statistics.median(secs), statistics.fmean(secs)
    total = sum(FULL_RUN.values())
    return {"pass": True, "children_in_full_run": total, "seconds_per_child_median": med,
            "seconds_per_child_mean": mean, "workers_assumed": workers,
            "hours_estimate": mean * total / workers / 3600, "python": platform.python_version()}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Pre-checks of RTIS experiment plan v1, section 7")
    ap.add_argument("--pilot", default=None, help="pilot folder written by run_v1.py --pilot")
    ap.add_argument("--workers", type=int, default=6, help="workers assumed for the time estimate")
    args = ap.parse_args(argv)
    res = {"1_founders": check1(), "3_bone_cut": check3(), "4_vertex_pinch": check4(), "5_left_right": check5()}
    if args.pilot:
        pilot = Path(args.pilot)
        res["2_g3_convergence"] = check2(pilot)
        res["6_every_run_has_a_row"] = check6(pilot)
        res["7_time"] = check7(pilot, args.workers)
    res = dict(sorted(res.items()))
    res["all_pass"] = all(v["pass"] for v in res.values() if isinstance(v, dict))
    res["metrics_version"] = M.METRICS_VERSION
    target = (Path(args.pilot) if args.pilot else Path(__file__).resolve().parent) / "precheck_v1.json"
    target.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for k, v in res.items():
        if isinstance(v, dict):
            print(f"{k:<24} {'PASS' if v['pass'] else 'FAIL'}")
    print(f"ALL: {'PASS' if res['all_pass'] else 'FAIL'}  -> {target}")
    sys.exit(0 if res["all_pass"] else 1)


if __name__ == "__main__":
    main()
