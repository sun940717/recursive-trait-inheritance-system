"""
pce.py — RTIS Phenotypic Compatibility Engine
Layer 2 核心算法

v2：雙通道升級
  - 語意通道：加權 Jaccard（保留 ontology 層級權重）
  - 數值通道：Cosine similarity（新增，來自 trait.morphology）
  - 加權融合：α·S_sem + β·S_num
  - 向後相容：PCEConfig(alpha=1.0, beta=0.0) 還原 v1 行為
  - 保留：semantic_similarity_layered / validate_coherence / record_semantic_neighbors
"""

from __future__ import annotations
import math
from copy import deepcopy
from trait import Trait, BodyGraph


# ─────────────────────────────────────────────────────────
#  Ontology 層級權重表（語意通道用）
# ─────────────────────────────────────────────────────────

_LAYER_WEIGHTS = {0: 0.5, 1: 1.0, 2: 2.0}


# ─────────────────────────────────────────────────────────
#  PCE 配置
# ─────────────────────────────────────────────────────────

class PCEConfig:
    """
    PCE 雙通道權重配置。

    alpha: 語意通道權重（加權 Jaccard）
    beta:  數值通道權重（Cosine）
    要求：alpha + beta = 1.0

    預設 alpha=0.6, beta=0.4：
      - 語意仍是主導因素
      - 數值提供細緻區分（同語意的 trait 中選更接近的）

    向後相容：alpha=1.0, beta=0.0 → 純語意，等同 v1 行為
    """
    def __init__(self, alpha: float = 0.6, beta: float = 0.4, top_k: int = 2):
        assert abs(alpha + beta - 1.0) < 1e-9, "alpha + beta 必須等於 1.0"
        self.alpha = alpha
        self.beta  = beta
        self.top_k = top_k

    def describe(self) -> str:
        return f"PCEConfig(α={self.alpha}, β={self.beta}, top_k={self.top_k})"


DEFAULT_CONFIG = PCEConfig()


# ─────────────────────────────────────────────────────────
#  語意通道
# ─────────────────────────────────────────────────────────

def semantic_similarity(tags_a: list[str], tags_b: list[str]) -> float:
    """純 Jaccard 語意相似度（向後相容保留）"""
    if not tags_a or not tags_b:
        return 0.0
    intersection = set(tags_a) & set(tags_b)
    union        = set(tags_a) | set(tags_b)
    return len(intersection) / len(union)


def semantic_similarity_layered(tags_a: list[str], tags_b: list[str],
                                 ontology=None) -> float:
    """
    加權 Jaccard，根據 ontology 層級給予不同權重。
    layer 2 (part) 2.0 / layer 1 (organ) 1.0 / layer 0 (cell) 0.5

    被 genome._find_corresponding() 使用，需保留此函數。
    """
    if not tags_a or not tags_b:
        return 0.0

    if ontology is None:
        try:
            from ontology import get_ontology
            ontology = get_ontology()
        except ImportError:
            return semantic_similarity(tags_a, tags_b)

    def weight(tag: str) -> float:
        t = ontology.get_tag(tag)
        return _LAYER_WEIGHTS.get(t.layer, 1.0) if t else 1.0

    set_a, set_b   = set(tags_a), set(tags_b)
    intersection   = set_a & set_b
    union          = set_a | set_b
    weighted_inter = sum(weight(t) for t in intersection)
    weighted_union = sum(weight(t) for t in union)
    return weighted_inter / weighted_union if weighted_union > 0 else 0.0


# ─────────────────────────────────────────────────────────
#  數值通道：NumericProfile + Cosine
# ─────────────────────────────────────────────────────────

NUMERIC_FIELDS = [
    ("scale",     0),    # scale[0] = x
    ("scale",     1),    # scale[1] = y
    ("scale",     2),    # scale[2] = z
    ("roughness", None),
    ("emissive",  None),
    ("rigidity",  None),
    ("sharpness", None),
]

NUMERIC_RANGES = {
    "scale":     (0.0, 5.0),
    "roughness": (0.0, 1.0),
    "emissive":  (0.0, 1.0),
    "rigidity":  (0.0, 1.0),
    "sharpness": (0.0, 1.0),
}


def _normalize(value: float, field: str) -> float:
    lo, hi = NUMERIC_RANGES.get(field, (0.0, 1.0))
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def extract_numeric_profile(trait: Trait) -> list[float]:
    """
    從 trait.morphology 提取 7 維數值向量。

    ── 來自真實 mesh（_from_mesh=True）──────────────────
    使用幾何特徵，所有值已在 [0, 1]：
      [scale_x, scale_y, scale_z,
       elongation_norm, flatness_norm,
       rigidity, sharpness]

    ── 手寫 GeneModule（_from_mesh=False）───────────────
    使用 morphology 欄位（原有 7 維）：
      [scale_x, scale_y, scale_z,
       roughness, emissive, rigidity, sharpness]
    """
    morph = trait.morphology

    if morph.get("_from_mesh") and "_pca_linearity" in morph:
        # ── Mesh-derived：PCA 幾何向量 ──────────────────
        # 7 維：[spread_2, spread_3, linearity, planarity, sphericity,
        #        rigidity, sharpness]
        # 全部在 [0, 1]，cosine 量的是「形狀方向」而非大小
        return [
            float(morph.get("_pca_spread_2",   0.5)),
            float(morph.get("_pca_spread_3",   0.5)),
            float(morph.get("_pca_linearity",  0.33)),
            float(morph.get("_pca_planarity",  0.33)),
            float(morph.get("_pca_sphericity", 0.33)),
            float(morph.get("rigidity",  0.5)),
            float(morph.get("sharpness", 0.3)),
        ]

    # ── Manual：原有 7 維 morphology 向量 ────────────────
    vector = []
    for field, idx in NUMERIC_FIELDS:
        raw = morph.get(field, 0.0)
        if idx is not None:
            raw = raw[idx] if isinstance(raw, list) and len(raw) > idx else 0.0
        vector.append(_normalize(float(raw), field))
    return vector


def numeric_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Cosine 相似度（數值通道）。
    對 [0,1] 正規化向量，結果值域 [0, 1]。
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot   = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a < 1e-9 or mag_b < 1e-9:
        return 0.0
    return max(0.0, min(1.0, dot / (mag_a * mag_b)))


# ─────────────────────────────────────────────────────────
#  融合分數
# ─────────────────────────────────────────────────────────

def pce_score(trait_a: Trait, trait_b: Trait,
              config: PCEConfig = None) -> dict:
    """
    計算兩個 trait 的 PCE 雙通道相容分數。

    Returns:
        {"total": float, "semantic": float, "numeric": float}
    """
    cfg   = config or DEFAULT_CONFIG
    s_sem = semantic_similarity_layered(trait_a.semantic_tags, trait_b.semantic_tags)

    if cfg.beta > 0:
        s_num = numeric_similarity(
            extract_numeric_profile(trait_a),
            extract_numeric_profile(trait_b),
        )
    else:
        s_num = 0.0

    total = cfg.alpha * s_sem + cfg.beta * s_num
    return {
        "total":    round(total, 4),
        "semantic": round(s_sem, 4),
        "numeric":  round(s_num, 4),
    }


# ─────────────────────────────────────────────────────────
#  一致性驗證（ai_mutation.py 使用，保留）
# ─────────────────────────────────────────────────────────

def validate_coherence(body: BodyGraph, ontology=None) -> list[str]:
    """
    根據 Ontology 組合規則驗證 BodyGraph 的功能一致性。
    回傳警告列表，空列表代表一致性通過。
    """
    if ontology is None:
        try:
            from ontology import get_ontology
            ontology = get_ontology()
        except ImportError:
            return []

    all_tags: set[str] = set()
    for t in body.all_traits():
        all_tags.update(t.semantic_tags)

    warnings = []
    for rule in ontology.composition_rules:
        inputs = rule.get("inputs", set())
        output = rule.get("output", "")
        if inputs.issubset(all_tags) and output and output not in all_tags:
            warnings.append(
                f"has {sorted(inputs)} but missing expected '{output}'"
            )
    return warnings


# ─────────────────────────────────────────────────────────
#  雙向語意連結（trait 圖寫回，保留）
# ─────────────────────────────────────────────────────────

def record_semantic_neighbors(source_trait: Trait,
                               candidates: list[tuple]) -> None:
    """
    PCE 配對結果雙向寫回 trait.semantic_neighbors。
    candidates 可為 (Trait, float) 或 (Trait, dict) 格式。
    """
    for item in candidates:
        candidate_trait, score_val = item
        if isinstance(score_val, dict):
            score = score_val.get("total", 0.0)
        else:
            score = float(score_val)
        if score <= 0:
            continue
        s = round(score, 3)
        source_trait.semantic_neighbors[candidate_trait.name]    = s
        candidate_trait.semantic_neighbors[source_trait.name]    = s


# ─────────────────────────────────────────────────────────
#  主要 API
# ─────────────────────────────────────────────────────────

def get_all_traits(body: BodyGraph) -> list[Trait]:
    if body.root is None:
        return []
    return body.all_traits()


def find_candidates(
    trait: Trait,
    target_body: BodyGraph,
    config: PCEConfig = None,
    top_k: int = None,
) -> list[tuple[Trait, dict]]:
    """
    找出 target_body 裡最相容的節點（雙通道分數）。

    Returns:
        [(Trait, score_dict), ...] 按 total 降序，只含 total > 0。
    """
    cfg    = config or DEFAULT_CONFIG
    k      = top_k if top_k is not None else cfg.top_k
    scored = []
    for candidate in get_all_traits(target_body):
        score = pce_score(trait, candidate, cfg)
        if score["total"] > 0:
            scored.append((candidate, score))
    scored.sort(key=lambda x: x[1]["total"], reverse=True)
    return scored[:k]


def apply_trait(
    source_trait: Trait,
    target_body: BodyGraph,
    config: PCEConfig = None,
) -> dict:
    """
    PCE 核心：把 source trait 附著到 target_body 的最佳位置。

    Returns:
        {
            "status":      "matched" | "fallback",
            "attached_to": str,
            "score":       float,   # total 融合分數
            "semantic":    float,
            "numeric":     float,
            "candidates":  [(name, score_dict), ...]
        }
    """
    cfg        = config or DEFAULT_CONFIG
    candidates = find_candidates(source_trait, target_body, cfg)

    if not candidates:
        fallback = target_body.root
        new_trait = deepcopy(source_trait)
        fallback.add_child(new_trait)
        return {
            "status":      "fallback",
            "attached_to": fallback.name,
            "score":       0.0,
            "semantic":    0.0,
            "numeric":     0.0,
            "candidates":  [],
        }

    best_node, best_score = candidates[0]
    new_trait = deepcopy(source_trait)
    best_node.add_child(new_trait)

    record_semantic_neighbors(new_trait, candidates)

    return {
        "status":      "matched",
        "attached_to": best_node.name,
        "score":       best_score["total"],
        "semantic":    best_score["semantic"],
        "numeric":     best_score["numeric"],
        "candidates":  [(c.name, s) for c, s in candidates],
    }


# ─────────────────────────────────────────────────────────
#  __main__ 自測
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    from genome import Genome, GeneModule

    genome_a = Genome(seed=42)
    genome_a.add_gene(GeneModule("sensor_node",         ["sensor", "visual"],         ["central"],    0.8))
    genome_a.add_gene(GeneModule("grasping_appendage",  ["grasping", "end_effector"], ["structural"], 0.6))
    genome_a.add_gene(GeneModule("branch",              ["structural"],               ["structural"], 0.5))

    genome_b = Genome(seed=99)
    genome_b.add_gene(GeneModule("antenna",  ["sensor", "receiver"],          ["central"],    0.9))
    genome_b.add_gene(GeneModule("claw",     ["grasping", "cutting"],         ["structural"], 0.7))
    genome_b.add_gene(GeneModule("limb",     ["structural", "locomotion"],    ["structural"], 0.6))

    body_a = genome_a.develop()
    body_b = genome_b.develop()

    print("=== PCE v2 雙通道自測 ===\n")

    # v1 相容模式
    cfg_v1   = PCEConfig(alpha=1.0, beta=0.0)
    # 雙通道預設
    cfg_v2   = PCEConfig(alpha=0.6, beta=0.4)
    # 消融：純數值
    cfg_num  = PCEConfig(alpha=0.0, beta=1.0)

    all_a = get_all_traits(body_a)
    all_b = get_all_traits(body_b)

    print(f"{'TraitA':25s} {'TraitB':25s} {'v1(sem)':>10} {'v2(total)':>10} {'sem':>8} {'num':>8}")
    print("-" * 90)
    for ta in all_a:
        for tb in all_b:
            s_v1 = pce_score(ta, tb, cfg_v1)
            s_v2 = pce_score(ta, tb, cfg_v2)
            if s_v2["total"] > 0 or s_v1["total"] > 0:
                print(f"{ta.name:25s} {tb.name:25s} "
                      f"{s_v1['total']:>10.4f} {s_v2['total']:>10.4f} "
                      f"{s_v2['semantic']:>8.4f} {s_v2['numeric']:>8.4f}")

    print("\n=== apply_trait（雙通道）===")
    grasping = next((t for t in all_a if "grasping" in t.semantic_tags), None)
    if grasping:
        result = apply_trait(grasping, body_b, cfg_v2)
        print(f"狀態：{result['status']}")
        print(f"附著到：{result['attached_to']}")
        print(f"total={result['score']}  sem={result['semantic']}  num={result['numeric']}")
        print(f"候選：{result['candidates']}")
