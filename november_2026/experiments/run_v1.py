#!/usr/bin/env python3
"""
run_v1.py
=========
Runs experiments X1 and X2 of RTIS experiment plan v1 (protocol frozen 2026-11-16) and writes one CSV
row per child (section 8). The generator in ..\\code is used as it is; nothing in it is changed.
執行 RTIS 實驗計畫 v1（規約 2026-11-16 凍結）的 X1 與 X2，每個子代寫一列 CSV（第八節）。
生成程式（..\\code）照原樣使用，不做任何修改。

Design (plan section 3) / 設計:
  15 pairs of the six forms, both directions, seeds 1-51. Random streams:
  numpy SeedSequence([20261116, pair, direction, seed, purpose]); purpose 0 = matching, 1 = inheritance,
  2 = the baseline's random draws (also used for the tag shuffle and the attribute layer).
  15 組配對、兩個方向、種子 1–51。亂數流的鍵如上；用途 0＝配對、1＝遺傳、2＝基準的隨機抽取
  （標籤打亂與屬性層也用這一條）。

Conditions / 條件:
  X1  pce            current matching (soft) / 現行配對
      random_k       same number K of non-root pairs as pce for the same key, chosen at random
                     與同一個鍵下 PCE 配成的非根部位對數 K 相同，隨機選
      order          parts paired in genome order, no tags / 依基因組順序、不看標籤
      root_only      only the roots are paired / 只配根部位
      shuffled_tags  each parent's tags shuffled among its non-root parts, then pce
                     每個親代的標籤在自己的非根部位之間打亂後再跑 PCE
  X2  (full = the X1 pce rows) / （完整＝X1 的 pce 資料）
      relative_off   relative=False (this path also has no linkage) / 同時沒有連鎖
      linkage_off    linkage=0
      graft_off      graft=False
      site_off       site_rule=False
      strict         matching mode "strict" / 嚴格配對
      attr           attribute layer on / 屬性層開啟

Usage (PowerShell, from RTIS\\current_2026-11\\experiments) / 用法:
  python run_v1.py --exp X1 --workers 6
  python run_v1.py --exp X2 --workers 6
  python run_v1.py --pilot --workers 2          # seeds 9001-9003, both experiments, into pilot\\
An interrupted run can be started again with the same command: finished rows are kept and skipped.
Failed rows are written once with status=error and are never re-run.
中斷後用同一個指令重跑即可：已完成的列會保留並跳過；失敗的列只寫一次（status=error），不會重跑。

Outputs (in --out, default data\\) / 輸出:
  <exp>.csv                one row per child (plan section 8) / 每個子代一列
  <exp>_detail.jsonl       per child: pairs, borderline decisions, dropped parts, sources, G3/G4 detail
                           每個子代：配對、邊界決定、消失的部位、來源、G3／G4 細節
  <exp>_manifest.json      conditions expanded, parent genome hashes, file hashes, package versions
                           展開後的條件、親代基因組雜湊、檔案雜湊、套件版本
Target: Python 3.10.12 · numpy, scipy, scikit-image, matplotlib.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import itertools
import json
import os
import platform
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
RTIS = HERE.parent.parent / "rtis"
for _p in (str(HERE), str(CODE), str(RTIS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np  # noqa: E402

import skeleton_sdf_demo as sk  # noqa: E402
import form_fusion_lab as lab  # noqa: E402
from form_fusion_lab import FuseOptions  # noqa: E402
import soft_match_lab as soft  # noqa: E402
import metrics_v1 as M  # noqa: E402

RUN_VERSION = "run_v1.0"
MASTER = 20261116
FORMS = ("quadruped", "biped", "spider", "serpent", "jellyfish", "crab")
PAIRS = list(itertools.combinations(range(len(FORMS)), 2))          # 15, numbered 0-14 / 編號 0–14
VOXEL = 0.03
ADOPTED = lab.ADOPTED                                                 # relative, graft, linkage 1, site rule
CONDITIONS = {
    "X1": ["pce", "random_k", "order", "root_only", "shuffled_tags"],
    "X2": ["relative_off", "linkage_off", "graft_off", "site_off", "strict", "attr"],
}
FUSE_OPTIONS = {
    "relative_off": dataclasses.replace(ADOPTED, relative=False),
    "linkage_off": dataclasses.replace(ADOPTED, linkage=0),
    "graft_off": dataclasses.replace(ADOPTED, graft=False),
    "site_off": dataclasses.replace(ADOPTED, site_rule=False),
}
COLUMNS = ["experiment", "condition", "pair", "parent_a", "parent_b", "direction", "seed", "status", "error",
           "k_matched", "g1_closed", "g1_manifold", "outer_shells", "bubbles", "n_instances", "n_buried",
           "n_hidden_005", "n_hidden_010", "n_hidden_020", "pass_geo", "share_from_a", "sources_total",
           "sources_kept", "lost_not_inherited", "lost_orphan", "lost_site", "new_bend_deg", "new_humps",
           "legacy_m3_pairs", "parts", "triangles", "seconds", "metrics_version", "code_hash"]
GENERATOR_FILES = [CODE / f for f in ("skeleton_sdf_demo.py", "form_fusion_lab.py", "soft_match_lab.py",
                                      "fourier3d_demo.py", "fourier_genetics.py", "attribute_layer.py",
                                      "pce_match_test.py")] + [RTIS / f for f in ("pce.py", "ontology.py", "trait.py")]
OWN_FILES = [HERE / "metrics_v1.py", HERE / "run_v1.py"]


# =============================================================================
# Keys, parents, matching / 鍵、親代、配對
# =============================================================================

def rng_for(pair: int, direction: int, seed: int, purpose: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([MASTER, pair, direction, seed, purpose]))


_FORMS_CACHE: dict = {}


def parents(pair: int, direction: int):
    """(name A, name B, genome A with ancestry 1, genome B with ancestry 0). Direction 1 swaps the pair.
    方向 1 把配對對調。"""
    if not _FORMS_CACHE:
        _FORMS_CACHE.update(lab.all_forms(ontology_tags=True))
    i, j = PAIRS[pair]
    a, b = (FORMS[i], FORMS[j]) if direction == 0 else (FORMS[j], FORMS[i])
    return a, b, sk.with_ancestry(_FORMS_CACHE[a], 1.0), sk.with_ancestry(_FORMS_CACHE[b], 0.0)


def root_pair(ga, gb) -> dict:
    ra = next(p for p in ga.parts if p.parent is None)
    rb = next(p for p in gb.parts if p.parent is None)
    return {"a": ra.name, "b": rb.name, "score": 1.0, "how": "root"}


def non_root(g) -> list[str]:
    return [p.name for p in g.parts if p.parent is not None]


def random_k_pairs(ga, gb, k: int, rng: np.random.Generator) -> list[dict]:
    """K non-root parts drawn uniformly without replacement on each side, paired one-to-one at random.
    兩邊各均勻、不放回地抽 K 個非根部位，再隨機一對一配。"""
    na, nb = non_root(ga), non_root(gb)
    pick_a = list(rng.choice(na, size=k, replace=False)) if k else []
    pick_b = list(rng.choice(nb, size=k, replace=False)) if k else []
    order = rng.permutation(k) if k else []
    return [root_pair(ga, gb)] + [{"a": str(pick_a[t]), "b": str(pick_b[order[t]]), "score": 0.0, "how": "random"}
                                  for t in range(k)]


def order_pairs(ga, gb) -> list[dict]:
    na, nb = non_root(ga), non_root(gb)
    return [root_pair(ga, gb)] + [{"a": x, "b": y, "score": 0.0, "how": "order"} for x, y in zip(na, nb)]


def shuffle_tags(g, rng: np.random.Generator):
    """Tags of the non-root parts shuffled among themselves; the root keeps its tags.
    非根部位的標籤互相打亂；根部位保留自己的標籤。"""
    idx = [k for k, p in enumerate(g.parts) if p.parent is not None]
    tags = [list(g.parts[k].tags) for k in idx]
    perm = rng.permutation(len(idx))
    parts = list(g.parts)
    for t, k in enumerate(idx):
        parts[k] = dataclasses.replace(parts[k], tags=tags[perm[t]])
    return sk.SkeletonGenome(parts)


# =============================================================================
# One child / 一個子代
# =============================================================================

def make_child(condition: str, pair: int, direction: int, seed: int):
    """Returns (child, log, ga, gb, pairs, decisions, k). / 回傳子代與紀錄。"""
    a, b, ga, gb = parents(pair, direction)
    r_match, r_inherit, r_base = (rng_for(pair, direction, seed, u) for u in (0, 1, 2))
    cfg = sk.SkeletonInheritanceConfig(micro_budget=0)
    opt, exclude, attr, decisions = ADOPTED, set(), None, []
    if condition in ("pce", "relative_off", "linkage_off", "graft_off", "site_off", "attr"):
        pairs, decisions = soft.soft_match(ga, gb, r_match, "soft")
    elif condition == "strict":
        pairs, decisions = soft.soft_match(ga, gb, r_match, "strict")
    elif condition == "random_k":
        pce_pairs, _ = soft.soft_match(ga, gb, r_match, "soft")
        pairs = random_k_pairs(ga, gb, len(pce_pairs) - 1, r_base)
    elif condition == "order":
        pairs = order_pairs(ga, gb)
    elif condition == "root_only":
        pairs = [root_pair(ga, gb)]
    elif condition == "shuffled_tags":
        ga, gb = shuffle_tags(ga, r_base), shuffle_tags(gb, r_base)
        pairs, decisions = soft.soft_match(ga, gb, r_match, "soft")
    else:
        raise ValueError(f"unknown condition {condition}")
    if condition in FUSE_OPTIONS:
        opt = FUSE_OPTIONS[condition]
    k = len(pairs) - 1
    if condition == "attr":
        import attribute_layer
        attr = attribute_layer.AttributeLayer(r_base)
        pairs, exclude = attr.plan(ga, gb, pairs)
    child, log = lab.fuse(ga, gb, r_inherit, cfg, opt, pairs=pairs, exclude=exclude, attr=attr)
    return child, log, ga, gb, pairs, decisions, k


def run_one(job: tuple) -> tuple[dict, dict]:
    experiment, condition, pair, direction, seed, code_hash, pilot = job
    a, b, _, _ = parents(pair, direction)
    row = {c: "" for c in COLUMNS}
    row.update({"experiment": experiment, "condition": condition, "pair": pair, "parent_a": a, "parent_b": b,
                "direction": direction, "seed": seed, "metrics_version": M.METRICS_VERSION, "code_hash": code_hash})
    side = {"key": [condition, pair, direction, seed]}
    t0 = time.perf_counter()
    try:
        child, log, ga, gb, pairs, decisions, k = make_child(condition, pair, direction, seed)
        mesh, face_piece, _ = sk.build_sdf_creature(child, VOXEL)
        fields, detail = M.measure_child(child, log, ga, gb, mesh, face_piece, VOXEL, g3_density2=pilot)
        row.update(fields)
        row.update({"status": "ok", "k_matched": k})
        side.update({"pairs": pairs, "decisions": decisions, "dropped": log.get("dropped", []),
                     "sources": log["sources"], **detail})
    except Exception as exc:  # noqa: BLE001 - every planned run keeps a row / 每個預定的執行都留一列
        row.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"[:300], "pass_geo": 0})
        side["traceback"] = traceback.format_exc()[-2000:]
    row["seconds"] = round(time.perf_counter() - t0, 3)
    return row, side


# =============================================================================
# Bookkeeping / 紀錄
# =============================================================================

def file_hashes() -> dict:
    return {str(p.name if p.parent != RTIS else f"rtis/{p.name}"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in GENERATOR_FILES + OWN_FILES}


def combined_hash(hashes: dict) -> str:
    return hashlib.sha256("".join(f"{k}:{v}\n" for k, v in sorted(hashes.items())).encode()).hexdigest()[:16]


def manifest(experiment: str, conditions: list[str], seeds: list[int], hashes: dict) -> dict:
    import scipy
    import skimage
    forms = lab.all_forms(ontology_tags=True)
    return {
        "run_version": RUN_VERSION, "metrics_version": M.METRICS_VERSION, "experiment": experiment,
        "conditions": conditions, "seeds": [min(seeds), max(seeds), len(seeds)], "voxel": VOXEL,
        "pairs": {k: [FORMS[i], FORMS[j]] for k, (i, j) in enumerate(PAIRS)},
        "rng_key": "SeedSequence([20261116, pair, direction, seed, purpose]); purpose 0 matching, 1 inheritance, 2 baseline",
        "inheritance_config": dataclasses.asdict(sk.SkeletonInheritanceConfig(micro_budget=0)),
        "fuse_options": {"adopted": dataclasses.asdict(ADOPTED),
                         **{c: dataclasses.asdict(o) for c, o in FUSE_OPTIONS.items()}},
        "parent_genome_sha256": {n: hashlib.sha256(json.dumps(g.to_json(), sort_keys=True).encode()).hexdigest()
                                 for n, g in forms.items()},
        "file_sha256": hashes, "code_hash": combined_hash(hashes),
        "python": platform.python_version(), "platform": platform.platform(),
        "numpy": np.__version__, "scipy": scipy.__version__, "scikit_image": skimage.__version__,
    }


def parse_seeds(text: str) -> list[int]:
    out = []
    for part in text.split(","):
        lo, _, hi = part.partition("-")
        out += list(range(int(lo), int(hi or lo) + 1))
    return out


def run_experiment(experiment: str, conditions: list[str], seeds: list[int], out: Path, workers: int,
                   pilot: bool, pairs: list[int], deadline: float | None = None) -> bool:
    """Returns True when every child of this experiment has a row. / 全部子代都有一列時回傳 True。"""
    out.mkdir(parents=True, exist_ok=True)
    hashes = file_hashes()
    code_hash = combined_hash(hashes)
    csv_path, side_path = out / f"{experiment}.csv", out / f"{experiment}_detail.jsonl"
    man = manifest(experiment, conditions, seeds, hashes)
    man_path = out / f"{experiment}_manifest.json"
    if man_path.exists():
        old = json.loads(man_path.read_text(encoding="utf-8"))
        if old.get("code_hash") != code_hash:
            sys.exit(f"{man_path} was written with code {old.get('code_hash')}, now {code_hash}: "
                     "use a new --out folder / 程式已改變，請換一個 --out 資料夾")
    man_path.write_text(json.dumps(man, indent=1), encoding="utf-8")
    done = set()
    if csv_path.exists():
        with csv_path.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                done.add((r["condition"], int(r["pair"]), int(r["direction"]), int(r["seed"])))
    jobs = [(experiment, c, p, d, s, code_hash, pilot)
            for s in seeds for p in pairs for d in (0, 1) for c in conditions if (c, p, d, s) not in done]
    print(f"{experiment}: {len(jobs)} children to run ({len(done)} already done), {workers} workers, "
          f"code {code_hash}", flush=True)
    new_file = not csv_path.exists()
    t0 = time.perf_counter()
    with csv_path.open("a", encoding="utf-8", newline="") as fh, side_path.open("a", encoding="utf-8") as sf:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        if new_file:
            writer.writeheader()

        def write(row, side, n):
            writer.writerow(row)
            fh.flush()
            sf.write(json.dumps(side, default=float) + "\n")
            sf.flush()
            if n % 25 == 0 or n == len(jobs):
                rate = (time.perf_counter() - t0) / n
                print(f"  {n}/{len(jobs)}  {rate:.2f} s per child  about {rate * (len(jobs) - n) / 60:.0f} min left",
                      flush=True)

        stopped = False
        if workers <= 1:
            for n, job in enumerate(jobs, 1):
                if deadline and time.perf_counter() > deadline:
                    stopped = True
                    break
                write(*run_one(job), n)
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(run_one, job) for job in jobs]
                n = 0
                for fut in as_completed(futures):
                    if deadline and time.perf_counter() > deadline and not stopped:
                        stopped = True                 # stop cleanly: no new children / 乾淨停下，不再開始新的
                        for f in futures:
                            f.cancel()
                    if fut.cancelled():
                        continue
                    n += 1
                    write(*fut.result(), n)
    state = "stopped at the time limit (run the same command again to continue)" if stopped else "done"
    print(f"{experiment}: {state} after {(time.perf_counter() - t0) / 60:.1f} min -> {csv_path}", flush=True)
    return not stopped


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="RTIS experiment plan v1: X1 and X2")
    ap.add_argument("--exp", choices=["X1", "X2", "both"], default="both")
    ap.add_argument("--seeds", default="1-51", help="e.g. 1-51 or 1,2,5-9")
    ap.add_argument("--pairs", default="all", help="pair numbers 0-14, e.g. 0,3,7 (default all)")
    ap.add_argument("--conditions", default="", help="subset of conditions, comma separated (default all)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--out", default=None)
    ap.add_argument("--pilot", action="store_true",
                    help="seeds 9001-9003 into pilot\\ (data not used for results) / 預跑，資料不進結果")
    ap.add_argument("--max-minutes", type=float, default=0.0,
                    help="stop cleanly after this many minutes; 0 = no limit / 時間到就乾淨停下；0＝不限")
    args = ap.parse_args(argv)
    seeds = parse_seeds("9001-9003" if args.pilot else args.seeds)
    pairs = list(range(len(PAIRS))) if args.pairs == "all" else [int(x) for x in args.pairs.split(",")]
    out = Path(args.out) if args.out else HERE / ("pilot" if args.pilot else "data")
    wanted = set(filter(None, args.conditions.split(",")))
    deadline = time.perf_counter() + 60.0 * args.max_minutes if args.max_minutes > 0 else None
    for exp in (["X1", "X2"] if args.exp == "both" else [args.exp]):
        conds = [c for c in CONDITIONS[exp] if not wanted or c in wanted]
        if conds and not run_experiment(exp, conds, seeds, out, args.workers, args.pilot, pairs, deadline):
            break


if __name__ == "__main__":
    main()
