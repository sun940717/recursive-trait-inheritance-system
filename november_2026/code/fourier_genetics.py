#!/usr/bin/env python3
"""
fourier_genetics.py
===================
Inheritance for Fourier tube genomes: correspondence -> crossover -> mutation -> symmetry.
傅立葉管狀基因組的遺傳：對應 -> 交配 -> 突變 -> 對稱。

Requires fourier3d_demo.py in the same folder. Target: Python 3.10.12 · numpy, matplotlib.
需要同資料夾的 fourier3d_demo.py。目標環境：Python 3.10.12 · numpy、matplotlib。

Everything happens on the genotype (coefficients); develop() = build_creature() runs once at the end,
so the child is one unified form, not a patchwork of parent meshes.
所有操作都在基因型（係數）上做，最後才呼叫一次 build_creature() 發育，
所以子代是一個統一的形體，不是把親代網格拼貼起來。

Pipeline (mirrors RTIS genome.develop_from_parents) / 流程（對應 RTIS 的 develop_from_parents）:
  1. Correspondence  Match tubes of parent A and B by semantic tags (+ attach position).
                     Uses RTIS pce.semantic_similarity_layered when importable, else Jaccard.
                     Inside a matched tube correspondence is free: harmonic n of A <-> harmonic n of B.
     對應            用語意標籤（＋接點位置）配對兩親代的管；有 RTIS 的 PCE 就用 PCE，否則用 Jaccard。
                     配對到的管內部不需要再找對應：A 的第 n 階諧波就對應 B 的第 n 階。
  2. Inheritance     Matched core pairs are always inherited; unmatched tubes follow the RTIS rules
                     (core_lock, inheritance_factor x dominance).
     繼承            配對到的核心管一定繼承；沒配對到的管照 RTIS 規則（core_lock、保真度 × 主導權重）。
  3. Crossover       Coefficients of a matched pair are zero-padded to equal length, then combined:
       "locus" (default)  each harmonic row is one locus, copied intact from A or B (Mendelian)
       "band"             low band from one parent, high band from one parent
       "blend"            alpha*A + (1-alpha)*B — looks intermediate, but population variation dies out
     交配            配對管的係數補零到同長度後組合：
       locus（預設）每一階諧波 = 一個基因座，整段從 A 或 B 複製（孟德爾式）
       band         低頻整段來自一方、高頻整段來自一方
       blend        加權平均：外觀介於中間，但族群變異會逐代消失
  4. Mutation        micro  = coefficient noise; core tubes' low band is protected with prob. core_lock
                     medium = duplicate or remove a peripheral tube (like RTIS gene duplication "_v2")
     突變            micro  = 係數雜訊；核心管的低頻有 core_lock 的機率受保護
                     medium = 複製或移除一條周邊管（對應 RTIS 的基因複製）
  5. Symmetry        Midline tubes are projected back onto the left/right-symmetric subspace.
     對稱            中軸管投影回左右對稱的子空間。

Outputs (default ./out_genetics) / 輸出（預設 ./out_genetics）:
  pedigree.png           founders -> F1 -> F2; tubes coloured by ancestry (orange = A, blue = B)
                         親代 -> F1 -> F2；顏色代表血緣（橘 = A，藍 = B）
  variance_by_mode.png   population shape variance over generations, per crossover mode
                         各交配模式下，族群形狀變異隨世代的變化
  <id>.obj / <id>.json   mesh and genome of every individual / 每個個體的網格與基因組
  inheritance_log.json   per child: parents, tube matches, loci sources, mutations
                         每個子代的親代、管配對、基因座來源、突變紀錄

Usage / 用法:
  python fourier_genetics.py
  python fourier_genetics.py --mode band --seed 3
  python fourier_genetics.py --no-experiment          # skip the variance experiment / 跳過變異實驗
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import colors as mcolors  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from fourier3d_demo import (  # noqa: E402
    GENE_FIELDS, Genome, TubeGene, build_creature, default_genome, ellipse_section,
    fit_open_polyline, radius_profile, style_axes, symmetric_section_mask, write_obj,
)
from fourier3d_demo import mutate as band_mutate  # noqa: E402

try:  # use RTIS PCE when this file sits inside the RTIS folder / 放在 RTIS 資料夾時改用 PCE
    from pce import semantic_similarity_layered as _PCE_SIMILARITY
except Exception:  # pragma: no cover
    _PCE_SIMILARITY = None

SHAPE_FIELDS = ("spine", "radius", "sect0", "sect1")


# =============================================================================
# Config / 參數
# =============================================================================

@dataclass
class FourierInheritanceConfig:
    """Field names follow RTIS genome.InheritanceConfig so the two can be merged later.
    欄位名稱沿用 RTIS 的 InheritanceConfig，之後可以直接合併。"""
    inheritance_factor: float = 0.70   # peripheral tube fidelity / 周邊管遺傳保真度
    core_lock: float = 0.90            # keep unmatched core tubes; protect core low band / 核心鎖定
    morphology_noise: float = 0.03     # multiplicative copy noise / 複製雜訊（乘法，0 維持 0）
    alpha: float = 0.50                # weight / probability of parent A / 親代 A 的權重或機率
    alpha_jitter: float = 0.15         # per-tube spread of alpha in blend mode / blend 模式每條管 alpha 的擾動
    parent_a_dominance: float = 0.50   # which parent supplies a tube's topology / 拓樸跟誰
    mutation_budget_micro: int = 4
    mutation_budget_medium: int = 1
    # Fourier-specific / 傅立葉專屬
    mode: str = "locus"                # "locus" | "band" | "blend"
    cutoff: int = 2                    # harmonics <= cutoff are "low" / 低頻分界
    micro_rate: float = 0.5            # chance each micro budget unit fires / 每單位 micro 觸發機率
    micro_sigma: float = 0.20
    medium_rate: float = 0.15          # chance each medium budget unit fires / 每單位 medium 觸發機率
    match_threshold: float = 0.25      # minimum tag similarity to call two tubes homologous / 同源門檻


# =============================================================================
# 1. Correspondence / 對應
# =============================================================================

def tag_similarity(tags_a, tags_b) -> float:
    if _PCE_SIMILARITY is not None:
        try:
            return float(_PCE_SIMILARITY(list(tags_a), list(tags_b)))
        except Exception:
            pass
    sa, sb = set(tags_a), set(tags_b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0


def match_tubes(ga: Genome, gb: Genome, cfg: FourierInheritanceConfig) -> dict[str, tuple[str, float]]:
    """Greedy one-to-one matching, roots forced together, mirrored only with mirrored.
    Returns {name_in_A: (name_in_B, score)}.
    貪婪一對一配對：根節點強制配對，鏡像管只跟鏡像管配。"""
    root_a = next(t for t in ga.tubes if t.parent is None)
    root_b = next(t for t in gb.tubes if t.parent is None)
    pairs = {root_a.name: (root_b.name, 1.0)}
    used_b = {root_b.name}
    candidates = []
    for ta in ga.tubes:
        if ta.parent is None:
            continue
        for tb in gb.tubes:
            if tb.parent is None or ta.mirror != tb.mirror:
                continue
            s = tag_similarity(ta.tags, tb.tags)
            if s < cfg.match_threshold:
                continue
            s += 0.25 * (1.0 - abs(ta.attach - tb.attach))      # position breaks ties / 位置當平手判斷
            candidates.append((s, ta.name, tb.name))
    for s, na, nb in sorted(candidates, key=lambda c: -c[0]):
        if na not in pairs and nb not in used_b:
            pairs[na] = (nb, s)
            used_b.add(nb)
    return pairs


# =============================================================================
# 3. Crossover of one matched pair / 一對配對管的交配
# =============================================================================

def _pad_rows(x: np.ndarray, n: int) -> np.ndarray:
    """Zero-pad along the harmonic axis. Adding zero harmonics does not change the shape.
    沿諧波軸補零。補上 0 的高階項不會改變形狀，所以不同長度的基因組可以直接交配。"""
    x = np.asarray(x, dtype=float)
    if x.shape[0] >= n:
        return x.copy()
    return np.concatenate([x, np.zeros((n - x.shape[0],) + x.shape[1:])])


def _row_harmonics(field_name: str, n_rows: int) -> np.ndarray:
    return np.arange(n_rows) if field_name in ("spine", "radius") else np.arange(1, n_rows + 1)


def cross_tube(ta: TubeGene, tb: TubeGene, cfg: FourierInheritanceConfig,
               rng: np.random.Generator) -> tuple[TubeGene, dict]:
    template_is_a = rng.random() < cfg.parent_a_dominance
    template = ta if template_is_a else tb
    fa, fb = ta.meta.get("ancestry_a", 0.5), tb.meta.get("ancestry_a", 0.5)
    alpha = float(np.clip(cfg.alpha + rng.normal(0.0, cfg.alpha_jitter), 0.0, 1.0))
    low_from_a = rng.random() < cfg.alpha
    high_from_a = rng.random() < cfg.alpha

    new, loci, ancestry_terms = {}, {}, []
    for f in SHAPE_FIELDS:
        a, b = getattr(ta, f), getattr(tb, f)
        n = max(a.shape[0], b.shape[0])
        a, b = _pad_rows(a, n), _pad_rows(b, n)
        h = _row_harmonics(f, n)
        if cfg.mode == "blend":
            c = alpha * a + (1.0 - alpha) * b
            ancestry_terms += [alpha * fa + (1.0 - alpha) * fb] * n
            loci[f] = f"blend a={alpha:.2f}"
        elif cfg.mode in ("locus", "band"):
            if cfg.mode == "locus":
                from_a = rng.random(n) < cfg.alpha
            else:
                from_a = np.where(h <= cfg.cutoff, low_from_a, high_from_a)
            c = np.where(from_a.reshape((n,) + (1,) * (a.ndim - 1)), a, b)
            ancestry_terms += [fa if x else fb for x in from_a]
            loci[f] = "".join("A" if x else "B" for x in from_a)
        else:
            raise ValueError(f"unknown crossover mode: {cfg.mode}")
        if cfg.morphology_noise > 0:
            c = c * (1.0 + cfg.morphology_noise * rng.standard_normal(c.shape))
        new[f] = c

    if cfg.mode == "blend":
        attach = alpha * ta.attach + (1.0 - alpha) * tb.attach
    elif cfg.mode == "band":
        attach = ta.attach if low_from_a else tb.attach        # attach is harmonic 0 / 接點屬於第 0 階
    else:
        attach = ta.attach if rng.random() < cfg.alpha else tb.attach

    child = dataclasses.replace(
        template, **new, attach=float(np.clip(attach, 0.0, 1.0)),
        tags=list(template.tags), meta={"ancestry_a": float(np.mean(ancestry_terms))},
    )
    info = {"template": "A" if template_is_a else "B", "A": ta.name, "B": tb.name, "loci": loci}
    return child, info


def _copy_tube(t: TubeGene, cfg: FourierInheritanceConfig, rng: np.random.Generator) -> TubeGene:
    noisy = {f: np.asarray(getattr(t, f), float)
             * (1.0 + cfg.morphology_noise * rng.standard_normal(np.shape(getattr(t, f))))
             for f in SHAPE_FIELDS}
    return dataclasses.replace(t, **noisy, tags=list(t.tags), meta=dict(t.meta))


# =============================================================================
# 2 + 3. Crossover of whole genomes / 整個基因組的交配
# =============================================================================

def crossover(ga: Genome, gb: Genome, cfg: FourierInheritanceConfig,
              rng: np.random.Generator) -> tuple[Genome, dict]:
    pairs = match_tubes(ga, gb, cfg)
    matched_b = {nb for nb, _ in pairs.values()}
    tubes_b = {t.name: t for t in gb.tubes}
    dom_a, dom_b = cfg.parent_a_dominance, 1.0 - cfg.parent_a_dominance

    child: list[TubeGene] = []
    name_map: dict[tuple[str, str], str] = {}      # (source, parent-genome name) -> child name
    used: set[str] = set()
    log = {"matches": [], "unmatched_inherited": [], "dropped": []}

    def unique(name: str) -> str:
        base, k = name, 2
        while name in used:
            name, k = f"{base}_{k}", k + 1
        used.add(name)
        return name

    def resolve_parent(options):
        """First mapped parent among (source, tube) options; None = root; False = parent missing."""
        for src, t in options:
            if t.parent is None:
                return None
            if (src, t.parent) in name_map:
                return name_map[(src, t.parent)]
        return False

    def p_peripheral(dom: float) -> float:
        return min(1.0, cfg.inheritance_factor * dom * 2.0)    # same formula as RTIS / 與 RTIS 相同

    for ta in ga.tubes:
        if ta.name in pairs:
            tb = tubes_b[pairs[ta.name][0]]
            core_pair = ta.parent is None or ta.is_core or tb.is_core
            if not core_pair:   # peripheral pair: either parent may pass it on / 周邊管：任一親代傳下來即可
                p = 1.0 - (1.0 - p_peripheral(dom_a)) * (1.0 - p_peripheral(dom_b))
                if rng.random() >= p:
                    log["dropped"].append(f"{ta.name}~{tb.name} (not inherited)")
                    continue
            tube, info = cross_tube(ta, tb, cfg, rng)
            first = ("A", ta) if info["template"] == "A" else ("B", tb)
            second = ("B", tb) if info["template"] == "A" else ("A", ta)
            parent = resolve_parent([first, second])
            if parent is False:
                log["dropped"].append(f"{ta.name}~{tb.name} (parent missing)")
                continue
            name = unique(tube.name)
            child.append(dataclasses.replace(tube, name=name, parent=parent))
            name_map[("A", ta.name)] = name
            name_map[("B", tb.name)] = name
            log["matches"].append({"child_tube": name, "score": round(pairs[ta.name][1], 3), **info})
        else:
            keep_p = cfg.core_lock if ta.is_core else p_peripheral(dom_a)
            parent = resolve_parent([("A", ta)])
            if rng.random() < keep_p and parent is not False:
                name = unique(ta.name)
                child.append(dataclasses.replace(_copy_tube(ta, cfg, rng), name=name, parent=parent))
                name_map[("A", ta.name)] = name
                log["unmatched_inherited"].append(f"A:{ta.name}")
            else:
                log["dropped"].append(f"A:{ta.name}")

    for tb in gb.tubes:
        if tb.name in matched_b:
            continue
        keep_p = cfg.core_lock * 0.5 if tb.is_core else p_peripheral(dom_b)   # RTIS: B's unique core x0.5
        parent = resolve_parent([("B", tb)])
        if rng.random() < keep_p and parent is not False:
            name = unique(tb.name)
            child.append(dataclasses.replace(_copy_tube(tb, cfg, rng), name=name, parent=parent))
            name_map[("B", tb.name)] = name
            log["unmatched_inherited"].append(f"B:{tb.name}")
        else:
            log["dropped"].append(f"B:{tb.name}")

    return Genome(child), log


# =============================================================================
# 4. Mutation / 突變
# =============================================================================

def _tube_slices(g: Genome) -> list[slice]:
    out, k = [], 0
    for t in g.tubes:
        n = sum(np.asarray(getattr(t, f)).size for f in GENE_FIELDS)
        out.append(slice(k, k + n))
        k += n
    return out


def _descendants(g: Genome, name: str) -> set[str]:
    out, frontier = {name}, [name]
    while frontier:
        cur = frontier.pop()
        for t in g.tubes:
            if t.parent == cur and t.name not in out:
                out.add(t.name)
                frontier.append(t.name)
    return out


def mutate_child(g: Genome, cfg: FourierInheritanceConfig,
                 rng: np.random.Generator) -> tuple[Genome, list[str]]:
    events: list[str] = []

    # micro: noise on one tube, one band / 對一條管的一個頻帶加雜訊
    for _ in range(int(rng.binomial(cfg.mutation_budget_micro, cfg.micro_rate))):
        vec = g.to_vector()
        rel, floor, harm, mask = g.entry_meta()
        i = int(rng.integers(len(g.tubes)))
        t = g.tubes[i]
        if t.is_core and rng.random() < cfg.core_lock:
            band = "high"                                      # core body plan protected / 保護核心藍圖
        else:
            band = "low" if rng.random() < 0.5 else "high"
        sel = np.zeros_like(vec)
        sel[_tube_slices(g)[i]] = 1.0
        band_mask = (harm <= cfg.cutoff) if band == "low" else (harm > cfg.cutoff)
        std = cfg.micro_sigma * (rel * np.abs(vec) + floor) * mask * sel * band_mask
        g = g.with_vector(vec + rng.standard_normal(vec.size) * std)
        events.append(f"micro: {t.name} {band}-band")

    # medium: duplicate or remove a peripheral tube / 複製或移除一條周邊管
    for _ in range(cfg.mutation_budget_medium):
        if rng.random() >= cfg.medium_rate:
            continue
        peripheral = [t for t in g.tubes if t.parent is not None and not t.is_core]
        if not peripheral:
            continue
        t = peripheral[int(rng.integers(len(peripheral)))]
        if rng.random() < 0.5:
            gone = _descendants(g, t.name)
            g = Genome([u for u in g.tubes if u.name not in gone])
            events.append(f"medium: removed {', '.join(sorted(gone))}")
        else:
            names = {u.name for u in g.tubes}
            new_name, k = f"{t.name}_dup", 2
            while new_name in names:
                new_name, k = f"{t.name}_dup{k}", k + 1
            dup = dataclasses.replace(t, name=new_name, tags=list(t.tags), meta=dict(t.meta),
                                      attach=float(np.clip(t.attach + rng.normal(0.0, 0.15), 0.0, 1.0)))
            g = Genome(g.tubes + [dup])
            events.append(f"medium: duplicated {t.name} -> {new_name}")
    return g, events


# =============================================================================
# 5. Symmetry + full reproduction / 對稱 + 完整繁殖
# =============================================================================

def enforce_symmetry(g: Genome) -> Genome:
    """Midline tubes: spine stays on y = 0, sections keep only left/right-symmetric harmonics.
    中軸管：脊椎留在 y = 0，截面只保留左右對稱的諧波。"""
    out = []
    for t in g.tubes:
        if t.mirror:
            out.append(t)
            continue
        spine = np.array(t.spine, dtype=float)
        spine[:, 1] = 0.0
        m0 = symmetric_section_mask(t.sect0.shape[0]).reshape(-1, 2, 2)
        m1 = symmetric_section_mask(t.sect1.shape[0]).reshape(-1, 2, 2)
        out.append(dataclasses.replace(t, spine=spine, sect0=t.sect0 * m0, sect1=t.sect1 * m1))
    return Genome(out)


def reproduce(ga: Genome, gb: Genome, cfg: FourierInheritanceConfig,
              rng: np.random.Generator) -> tuple[Genome, dict]:
    child, log = crossover(ga, gb, cfg, rng)
    child = enforce_symmetry(child)
    child, events = mutate_child(child, cfg, rng)
    log["mutations"] = events
    return enforce_symmetry(child), log


# =============================================================================
# A second species (biped) to cross with the quadruped / 第二個物種（二足），用來跟四足雜交
# =============================================================================

def biped_genome(k_spine: int = 5, k_radius: int = 10, h_section: int = 6) -> Genome:
    """Different harmonic counts on purpose (R=10, H=6 vs 8, 4): zero-padding handles it.
    It also has a tube the quadruped lacks (horns) and arms instead of front legs.
    故意用不同的諧波數量（R=10、H=6，四足是 8、4），由補零處理。
    牠還有四足沒有的管（角），而且前肢是手不是腳。"""
    sec = ellipse_section
    body_s0 = sec(h_section, 0.85, 1.0)
    body_s0[2, 1] = (0.0, 0.10)                 # 3rd harmonic B_y: flatter back and belly / 第三階 B_y：背與腹變平
    body_s1 = sec(h_section, 0.8, 1.0)
    body_s1[2, 1] = (0.0, 0.08)
    body = TubeGene(
        "body",
        spine=fit_open_polyline([(-0.6, 0, 0.55), (-0.3, 0, 0.62), (0.0, 0, 0.70),
                                 (0.3, 0, 0.80), (0.55, 0, 0.92)], k_spine),
        radius=radius_profile([0, 0.2, 0.5, 0.8, 1], [0.15, 0.25, 0.26, 0.20, 0.13], k_radius),
        sect0=body_s0, sect1=body_s1, tags=["structural", "central"], is_core=True,
    )
    neck = TubeGene(
        "neck_head",
        spine=fit_open_polyline([(0, 0, 0), (0.12, 0, 0.25), (0.25, 0, 0.45),
                                 (0.45, 0, 0.52), (0.7, 0, 0.48)], k_spine),
        radius=radius_profile([0, 0.35, 0.6, 0.8, 0.95, 1],
                              [0.12, 0.08, 0.09, 0.15, 0.12, 0.05], k_radius),
        sect0=sec(h_section), sect1=sec(h_section, 0.8, 1.0),
        parent="body", attach=0.97, tags=["sensory", "neural"], is_core=True,
    )
    tail = TubeGene(
        "tail",
        spine=fit_open_polyline([(0, 0, 0), (-0.4, 0, -0.08), (-0.8, 0, -0.12),
                                 (-1.2, 0, -0.1), (-1.5, 0, -0.05)], k_spine),
        radius=radius_profile([0, 0.4, 1], [0.14, 0.08, 0.02], k_radius),
        sect0=sec(h_section, 0.9, 1.0), sect1=sec(h_section),
        parent="body", attach=0.03, tags=["structural", "balance"], is_core=False,
    )
    leg_rear = TubeGene(
        "leg_rear",
        spine=fit_open_polyline([(0, 0, 0), (0.05, 0.22, -0.2), (0.25, 0.27, -0.6),
                                 (0.0, 0.27, -1.0), (0.15, 0.27, -1.3)], k_spine),
        radius=radius_profile([0, 0.2, 0.5, 0.85, 1], [0.15, 0.14, 0.09, 0.06, 0.08], k_radius),
        sect0=sec(h_section), sect1=sec(h_section),
        parent="body", attach=0.20, mirror=True,
        tags=["motor", "locomotion", "rear"], is_core=True,
    )
    arm_front = TubeGene(
        "arm_front",
        spine=fit_open_polyline([(0, 0, 0), (0.08, 0.2, -0.08), (0.2, 0.24, -0.22),
                                 (0.28, 0.24, -0.18)], k_spine),
        radius=radius_profile([0, 0.3, 0.7, 1], [0.07, 0.05, 0.035, 0.025], k_radius),
        sect0=sec(h_section), sect1=sec(h_section),
        parent="body", attach=0.85, mirror=True,
        tags=["motor", "grasping", "front"], is_core=True,
    )
    horn = TubeGene(
        "horn",
        spine=fit_open_polyline([(0, 0, 0), (0.0, 0.08, 0.12), (-0.05, 0.12, 0.25),
                                 (-0.12, 0.13, 0.32)], k_spine),
        radius=radius_profile([0, 0.4, 1], [0.05, 0.03, 0.005], k_radius),
        sect0=sec(h_section), sect1=sec(h_section),
        parent="neck_head", attach=0.82, mirror=True,
        tags=["defense", "cutting"], is_core=False,
    )
    return Genome([body, neck, tail, leg_rear, arm_front, horn])


def with_ancestry(g: Genome, value: float) -> Genome:
    return Genome([dataclasses.replace(t, meta={**t.meta, "ancestry_a": value}) for t in g.tubes])


# =============================================================================
# Variance experiment: why not plain blending / 變異實驗：為什麼不用單純平均
# =============================================================================

def body_variance(population: list[Genome]) -> float:
    """Mean per-coefficient variance of the root (body) tube across the population.
    族群中根節點（身體）每個係數的平均變異數。"""
    roots = [next(t for t in g.tubes if t.parent is None) for g in population]
    rows = []
    for f in SHAPE_FIELDS:
        n = max(getattr(t, f).shape[0] for t in roots)
        rows.append(np.stack([_pad_rows(getattr(t, f), n).ravel() for t in roots]))
    return float(np.var(np.hstack(rows), axis=0).mean())


def variance_experiment(base_cfg: FourierInheritanceConfig, founder_a: Genome, founder_b: Genome,
                        modes=("blend", "band", "locus"), pop: int = 40, gens: int = 10,
                        seeds: int = 5) -> dict[str, np.ndarray]:
    """Random mating, no mutation, no selection: only the inheritance rule differs.
    隨機交配、無突變、無選擇：唯一的差別是遺傳規則。"""
    results = {}
    for mode in modes:
        cfg = dataclasses.replace(base_cfg, mode=mode, morphology_noise=0.0,
                                  mutation_budget_micro=0, mutation_budget_medium=0)
        curves = []
        for s in range(seeds):
            rng = np.random.default_rng(1000 + s)
            population = ([band_mutate(founder_a, 0.15, rng) for _ in range(pop // 2)]
                          + [band_mutate(founder_b, 0.15, rng) for _ in range(pop - pop // 2)])
            v0 = body_variance(population)
            curve = [1.0]
            for _ in range(gens):
                nxt = []
                for _ in range(pop):
                    i, j = rng.choice(pop, size=2, replace=False)
                    child, _ = reproduce(population[i], population[j], cfg, rng)
                    nxt.append(child)
                population = nxt
                curve.append(body_variance(population) / v0)
            curves.append(curve)
        results[mode] = np.array(curves)
    return results


def plot_variance(results: dict[str, np.ndarray], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.2))
    styles = {"blend": ("#c0504d", "blend: alpha*A + (1-alpha)*B"),
              "band": ("#4f81bd", "band: low / high band from one parent"),
              "locus": ("#2e8b57", "locus: each harmonic from one parent")}
    for mode, curves in results.items():
        colour, label = styles.get(mode, ("0.4", mode))
        mean = curves.mean(axis=0)
        gens = np.arange(len(mean))
        ax.plot(gens, mean, color=colour, lw=2.2, marker="o", ms=3.5, label=label)
        ax.fill_between(gens, curves.min(axis=0), curves.max(axis=0), color=colour, alpha=0.12, lw=0)
    ax.set_yscale("log")
    ax.set_xlabel("generation")
    ax.set_ylabel("body-shape variance (relative to gen 0)")
    ax.set_title("Random mating, no mutation, no selection", fontsize=11)
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


# =============================================================================
# Pedigree figure / 家譜圖
# =============================================================================

COLOUR_A = np.array(mcolors.to_rgb("#e07b39"))   # founder A (quadruped) / 親代 A（四足）
COLOUR_B = np.array(mcolors.to_rgb("#3b7dd8"))   # founder B (biped) / 親代 B（二足）


def draw_genome(ax, g: Genome, title: str, light=(0.4, -0.7, 0.8)) -> None:
    genes = {t.name: t for t in g.tubes}
    light = np.asarray(light, dtype=float)
    light /= np.linalg.norm(light)
    tris_all, cols_all = [], []
    for name, m in build_creature(g, n_s=40, n_theta=20):
        t = genes.get(name) or genes.get(name[:-2])           # strip _L / _R / 去掉左右後綴
        frac = float(t.meta.get("ancestry_a", 0.5))
        base = frac * COLOUR_A + (1.0 - frac) * COLOUR_B
        tris = m.vertices[m.faces]
        normal = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        normal /= np.linalg.norm(normal, axis=1, keepdims=True) + 1e-12
        shade = 0.3 + 0.7 * np.clip(normal @ light, 0.0, 1.0)
        tris_all.append(tris)
        cols_all.append(np.clip(shade[:, None] * base, 0, 1))
    tris = np.concatenate(tris_all)
    ax.add_collection3d(Poly3DCollection(tris, facecolors=np.concatenate(cols_all),
                                         edgecolors="none", linewidths=0))
    ax.view_init(elev=14, azim=-62)
    style_axes(ax, tris.reshape(-1, 3), pad=0.02, title=title, axis_off=True, zoom=1.1)


def plot_pedigree(rows: list[list[tuple[str, Genome]]], out_path: Path, mode: str) -> None:
    ncols = max(len(r) for r in rows)
    fig = plt.figure(figsize=(4.2 * ncols, 3.4 * len(rows)))
    fig.suptitle(f"Fourier genome inheritance (mode = {mode}) - colour = ancestry: "
                 "orange = A (quadruped), blue = B (biped)", fontsize=13)
    for r, row in enumerate(rows):
        for c, (title, g) in enumerate(row):
            ax = fig.add_subplot(len(rows), ncols, r * ncols + c + 1, projection="3d")
            draw_genome(ax, g, title)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.92, bottom=0.0, wspace=0.0, hspace=0.1)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


# =============================================================================
# Main / 主程式
# =============================================================================

def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Inheritance for Fourier tube genomes")
    ap.add_argument("--out", default="out_genetics")
    ap.add_argument("--mode", default="locus", choices=("locus", "band", "blend"))
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-experiment", action="store_true", help="skip variance experiment / 跳過變異實驗")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = FourierInheritanceConfig(mode=args.mode)
    rng = np.random.default_rng(args.seed)
    print(f"tag similarity: {'RTIS PCE' if _PCE_SIMILARITY else 'Jaccard fallback'}")

    founder_a = with_ancestry(default_genome(), 1.0)
    founder_b = with_ancestry(biped_genome(), 0.0)

    pairs = match_tubes(founder_a, founder_b, cfg)
    print("Correspondence A <-> B / 對應:")
    for na, (nb, s) in pairs.items():
        print(f"  {na:<10} <-> {nb:<10} score {s:.2f}")

    individuals = {"A": founder_a, "B": founder_b}
    logs = {}

    def breed(child_id: str, pa: str, pb: str):
        g, log = reproduce(individuals[pa], individuals[pb], cfg, rng)
        individuals[child_id] = g
        logs[child_id] = {"parents": [pa, pb], **log}
        tubes = ", ".join(f"{t.name}({t.meta['ancestry_a']:.0%}A)" for t in g.tubes)
        muts = "; ".join(log["mutations"]) or "none"
        print(f"  {child_id} = {pa} x {pb}: {tubes}\n      mutations: {muts}")

    print(f"Breeding (mode = {cfg.mode}) / 繁殖:")
    for k in range(1, 5):
        breed(f"F1-{k}", "A", "B")
    breed("F2-1", "F1-1", "F1-2")
    breed("F2-2", "F1-1", "F1-2")
    breed("F2-3", "F1-3", "F1-4")
    breed("F2-4", "F1-3", "F1-4")

    for ind_id, g in individuals.items():
        write_obj(out / f"{ind_id}.obj", build_creature(g))
        (out / f"{ind_id}.json").write_text(json.dumps(g.to_json(), indent=1), encoding="utf-8")
    (out / "inheritance_log.json").write_text(json.dumps(logs, indent=1), encoding="utf-8")

    rows = [[("founder A: quadruped", founder_a), ("founder B: biped", founder_b)],
            [(f"F1-{k} = A x B", individuals[f"F1-{k}"]) for k in range(1, 5)],
            [("F2-1 = F1-1 x F1-2", individuals["F2-1"]), ("F2-2 = F1-1 x F1-2", individuals["F2-2"]),
             ("F2-3 = F1-3 x F1-4", individuals["F2-3"]), ("F2-4 = F1-3 x F1-4", individuals["F2-4"])]]
    plot_pedigree(rows, out / "pedigree.png", cfg.mode)

    if not args.no_experiment:
        print("Variance experiment (pop 40, 10 generations, 5 seeds) / 變異實驗:")
        res = variance_experiment(cfg, founder_a, founder_b)
        for mode, curves in res.items():
            m = curves.mean(axis=0)
            print(f"  {mode:<6} variance left after 1 gen: {m[1]:.3f}   after 10 gens: {m[-1]:.4f}")
        plot_variance(res, out / "variance_by_mode.png")
    print(f"Done -> {out.resolve()}")


if __name__ == "__main__":
    main()
