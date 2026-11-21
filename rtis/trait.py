"""
trait.py — RTIS 核心資料結構
Layer 2 (Structure) + Layer 4 (Morphology)

新增：morphology_blend() 插值函數，支援親代遺傳保真
新增：provenance（血緣來源）欄位，記錄每個 Trait 的演化歷史
     - make_provenance()  建立標準 provenance dict
     - merge_provenance() 雙親 provenance 合併成子代 provenance
     - BodyGraph.provenance_summary() 回傳所有 trait 血緣摘要
"""

import colorsys
import random
import math


# ─────────────────────────────────────────
#  預設 morphology（根據 semantic_tags 自動設定）
# ─────────────────────────────────────────

MORPHOLOGY_HINTS = {
    "grasping":    {"shape": "cylinder", "color": "#C0392B", "sharpness": 0.6, "rigidity": 0.8},
    "cutting":     {"shape": "cone",     "color": "#8B0000", "sharpness": 0.9, "rigidity": 0.9},
    "sensory":     {"shape": "sphere",   "color": "#3498DB", "sharpness": 0.1, "emissive": 0.3},
    "structural":  {"shape": "capsule",  "color": "#7F8C8D", "sharpness": 0.1, "rigidity": 0.9},
    "motor":       {"shape": "cylinder", "color": "#27AE60", "sharpness": 0.2, "rigidity": 0.7},
    "secretory":   {"shape": "sphere",   "color": "#9B59B6", "sharpness": 0.1, "emissive": 0.4},
    "defense":     {"shape": "box",      "color": "#2C3E50", "sharpness": 0.3, "rigidity": 1.0},
    "energy":      {"shape": "sphere",   "color": "#F1C40F", "sharpness": 0.0, "emissive": 0.8},
    "locomotion":  {"shape": "capsule",  "color": "#1ABC9C", "sharpness": 0.2, "rigidity": 0.6},
}

DEFAULT_MORPHOLOGY = {
    "shape":         "sphere",
    "scale":         [1.0, 1.0, 1.0],
    "color":         "#95A5A6",
    "roughness":     0.5,
    "emissive":      0.0,
    "rigidity":      0.5,
    "sharpness":     0.3,
    "heritable":     True,
    "mutation_type": "none",
    "mutation_desc": "",
}


def _default_morphology_from_tags(semantic_tags: list) -> dict:
    """根據 semantic_tags 設定預設 morphology"""
    base = DEFAULT_MORPHOLOGY.copy()
    base["scale"] = [1.0, 1.0, 1.0]
    for tag in semantic_tags:
        for key, hints in MORPHOLOGY_HINTS.items():
            if key in tag:
                base.update(hints)
                break
    return base


# ─────────────────────────────────────────
#  Morphology 插值工具函數
# ─────────────────────────────────────────

def _hex_to_hsv(hex_color: str) -> tuple:
    """#RRGGBB → (h, s, v)"""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    return colorsys.rgb_to_hsv(r, g, b)


def _hsv_to_hex(h: float, s: float, v: float) -> str:
    """(h, s, v) → #RRGGBB"""
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#{:02X}{:02X}{:02X}".format(int(r*255), int(g*255), int(b*255))


def _lerp(a: float, b: float, t: float) -> float:
    """線性插值，t=0 → a，t=1 → b"""
    return a + (b - a) * t


def _lerp_scale(scale_a: list, scale_b: list, t: float) -> list:
    return [_lerp(scale_a[i], scale_b[i], t) for i in range(3)]


def _blend_color_hsv(color_a: str, color_b: str, t: float) -> str:
    """在 HSV 空間做色彩插值，避免 RGB 插值產生的泥色"""
    ha, sa, va = _hex_to_hsv(color_a)
    hb, sb, vb = _hex_to_hsv(color_b)
    # 色相插值要走最短路徑（避免繞遠路）
    dh = hb - ha
    if abs(dh) > 0.5:
        dh -= math.copysign(1.0, dh)
    h = (ha + dh * t) % 1.0
    s = _lerp(sa, sb, t)
    v = _lerp(va, vb, t)
    return _hsv_to_hex(h, s, v)


def morphology_blend(morph_a: dict, morph_b: dict, alpha: float, noise_scale: float = 0.05) -> dict:
    """
    兩個 morphology 的加權插值，加上少量雜訊模擬遺傳變異。

    Args:
        morph_a: 親代 A 的 morphology dict
        morph_b: 親代 B 的 morphology dict
        alpha:   親代 A 的權重 (0.0~1.0)，1-alpha 為親代 B 的權重
        noise_scale: 數值隨機偏移幅度（預設 5%）

    Returns:
        融合後的 morphology dict（不含 heritable / mutation 欄位）
    """
    def noisy(v: float, scale: float = noise_scale) -> float:
        return max(0.0, min(1.0, v + random.gauss(0, scale)))

    result = {}

    # 數值欄位：插值 + 雜訊
    for key in ("roughness", "emissive", "rigidity", "sharpness"):
        va = morph_a.get(key, DEFAULT_MORPHOLOGY[key])
        vb = morph_b.get(key, DEFAULT_MORPHOLOGY[key])
        result[key] = round(noisy(_lerp(va, vb, 1 - alpha)), 3)

    # scale 三軸插值
    sa = morph_a.get("scale", [1.0, 1.0, 1.0])
    sb = morph_b.get("scale", [1.0, 1.0, 1.0])
    blended_scale = _lerp_scale(sa, sb, 1 - alpha)
    result["scale"] = [round(noisy(v, noise_scale * 0.5), 3) for v in blended_scale]

    # 顏色：HSV 空間插值
    ca = morph_a.get("color", DEFAULT_MORPHOLOGY["color"])
    cb = morph_b.get("color", DEFAULT_MORPHOLOGY["color"])
    result["color"] = _blend_color_hsv(ca, cb, 1 - alpha)

    # shape：以 alpha 為機率選擇親代，與數值欄位行為一致
    # alpha=0.5 → 50:50，alpha=0.8 → 80% 選 shape_a
    shape_a = morph_a.get("shape", "sphere")
    shape_b = morph_b.get("shape", "sphere")
    result["shape"] = shape_a if random.random() < alpha else shape_b

    return result


# ─────────────────────────────────────────
#  Provenance 工具函數
# ─────────────────────────────────────────

def make_provenance(
    source_organism: str = None,
    generation: int = 0,
    inherited_from: str = None,
    origin_type: str = "preset",
) -> dict:
    """
    建立標準 provenance dict。

    Args:
        source_organism: 此 trait 來自哪個物種名稱（如 'shark', 'jellyfish'）
        generation:      此 trait 出現在第幾代（原始親代 = 0）
        inherited_from:  繼承自哪個 trait 名稱（None 表示全新產生）
        origin_type:     來源類型：'preset'|'inherited'|'mutated'|'fused'

    Returns:
        dict with keys: source_organism, generation, inherited_from, origin_type
    """
    return {
        "source_organism": source_organism,
        "generation":      generation,
        "inherited_from":  inherited_from,
        "origin_type":     origin_type,
    }


def merge_provenance(
    prov_a: dict,
    prov_b: dict,
    generation: int = 1,
    origin_type: str = "inherited",
) -> dict:
    """
    將雙親的 provenance 合併成子代 provenance。

    - source_organism: 取親代 A 的物種（優先繼承）
    - parent_organisms: 記錄兩個親代的物種名稱列表
    - generation:      傳入的子代世代數
    - inherited_from:  None（子代是融合新生，不繼承單一 trait）
    - origin_type:     傳入值（預設 'inherited'）

    Args:
        prov_a:      親代 A 的 provenance dict
        prov_b:      親代 B 的 provenance dict
        generation:  子代的世代數
        origin_type: 子代的 origin_type

    Returns:
        合併後的子代 provenance dict
    """
    org_a = prov_a.get("source_organism") if prov_a else None
    org_b = prov_b.get("source_organism") if prov_b else None
    parents = [o for o in [org_a, org_b] if o is not None]
    return {
        "source_organism":  org_a,
        "generation":       generation,
        "inherited_from":   None,
        "origin_type":      origin_type,
        "parent_organisms": parents,
    }


# ─────────────────────────────────────────
#  Trait 類別
# ─────────────────────────────────────────

class Trait:
    """
    遺傳的基本單位。

    Attributes:
        name:          trait 名稱
        semantic_tags: 語意標籤列表（連接 Ontology）
        morphology:    幾何與外觀屬性
        children:      子 trait 列表
        parent:        父 trait（或 None）
        is_core:       是否為核心骨架 trait（影響遺傳保真度）
    """

    def __init__(self, name: str, semantic_tags: list = None, morphology: dict = None,
                 is_core: bool = False, provenance: dict = None):
        self.name = name
        self.semantic_tags = semantic_tags or []
        self.morphology = morphology or _default_morphology_from_tags(self.semantic_tags)
        self.children: list["Trait"] = []
        self.parent: "Trait" = None
        self.is_core = is_core
        self.provenance: dict = provenance if provenance is not None else make_provenance()
        # 雙向語意連結：{鄰居 trait 名稱: PCE Jaccard 相似度}
        # 由 pce.py 的 record_semantic_neighbors() 在每次 PCE 後寫入
        self.semantic_neighbors: dict = {}

    def add_child(self, child: "Trait"):
        child.parent = self
        self.children.append(child)

    def depth(self) -> int:
        """此 trait 在樹中的深度（root = 0）"""
        d = 0
        node = self
        while node.parent:
            d += 1
            node = node.parent
        return d

    def all_descendants(self) -> list:
        """回傳所有後代 trait（不含自身）"""
        result = []
        for child in self.children:
            result.append(child)
            result.extend(child.all_descendants())
        return result

    def clone(self, deep: bool = True) -> "Trait":
        """深度複製此 trait（不複製 parent 指標，但複製 provenance 和 semantic_neighbors）"""
        new_trait = Trait(
            name=self.name,
            semantic_tags=list(self.semantic_tags),
            morphology={k: (list(v) if isinstance(v, list) else v)
                        for k, v in self.morphology.items()},
            is_core=self.is_core,
            provenance=dict(self.provenance) if self.provenance else make_provenance(),
        )
        new_trait.semantic_neighbors = dict(self.semantic_neighbors)
        if deep:
            for child in self.children:
                cloned_child = child.clone(deep=True)
                new_trait.add_child(cloned_child)
        return new_trait

    def to_dict(self) -> dict:
        return {
            "name":               self.name,
            "semantic_tags":      self.semantic_tags,
            "morphology":         self.morphology,
            "is_core":            self.is_core,
            "provenance":         self.provenance,
            "semantic_neighbors": self.semantic_neighbors,
            "children":           [c.to_dict() for c in self.children],
        }

    def __repr__(self):
        src = self.provenance.get("source_organism") if self.provenance else None
        gen = self.provenance.get("generation", 0) if self.provenance else 0
        return (
            f"Trait({self.name}, tags={self.semantic_tags}, "
            f"core={self.is_core}, src={src}@gen{gen})"
        )


# ─────────────────────────────────────────
#  BodyGraph 類別
# ─────────────────────────────────────────

class BodyGraph:
    """
    整個生物的 trait 網路。

    Attributes:
        root:      根 trait（body / torso 等）
        organism_name: 生物名稱
        seed:      隨機種子（用於重現）
    """

    def __init__(self, root: Trait, organism_name: str = "Unknown", seed: int = None):
        self.root = root
        self.organism_name = organism_name
        self.seed = seed

    def all_traits(self) -> list:
        """回傳所有 trait（含 root）"""
        return [self.root] + self.root.all_descendants()

    def core_traits(self) -> list:
        """回傳所有核心骨架 trait"""
        return [t for t in self.all_traits() if t.is_core]

    def peripheral_traits(self) -> list:
        """回傳所有周邊 trait"""
        return [t for t in self.all_traits() if not t.is_core]

    def find_trait(self, name: str) -> Trait:
        """依名稱尋找 trait"""
        for t in self.all_traits():
            if t.name == name:
                return t
        return None

    def trait_count(self) -> int:
        return len(self.all_traits())

    def to_dict(self) -> dict:
        return {
            "organism_name": self.organism_name,
            "seed": self.seed,
            "root": self.root.to_dict(),
        }

    def summary(self) -> str:
        traits = self.all_traits()
        core = [t.name for t in traits if t.is_core]
        peripheral = [t.name for t in traits if not t.is_core]
        return (
            f"[{self.organism_name}] total={len(traits)} "
            f"core={core} peripheral={peripheral}"
        )

    def provenance_summary(self) -> list:
        """
        回傳所有 trait 的血緣摘要列表，每筆為 dict：
          { name, source_organism, generation, origin_type, inherited_from }
        可用於視覺化跨代 Trait 流向圖。
        """
        result = []
        for t in self.all_traits():
            prov = t.provenance or {}
            result.append({
                "name":             t.name,
                "source_organism":  prov.get("source_organism"),
                "generation":       prov.get("generation", 0),
                "origin_type":      prov.get("origin_type", "unknown"),
                "inherited_from":   prov.get("inherited_from"),
                "parent_organisms": prov.get("parent_organisms", []),
            })
        return result
