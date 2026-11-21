"""
RTIS Ontology System — Layer 3
================================
可動態擴展的多層級 tag 系統，定義 trait 的語意身份。

層級結構：
  Layer 0: cell（細胞層）
  Layer 1: organ（器官層）
  Layer 2: part（部位層）
  Layer 3+: 可自由擴展（game_stat / element / ...）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OntologyTag:
    name:            str
    layer:           int
    label:           str
    description:     str  = ""
    morphology_hint: dict = field(default_factory=dict)


class Ontology:
    def __init__(self):
        self.layers: dict[int, dict] = {}
        self.tags:   dict[str, OntologyTag] = {}
        self.composition_rules: list[dict] = []
        self._init_default()

    def _init_default(self):
        # Layer 0: 細胞層
        self.add_layer(0, "cell", "細胞層")
        for name, label, morph in [
            ("structural_cell", "結構細胞", {"shape": "box",      "color": "#95A5A6", "rigidity": 0.9, "roughness": 0.6}),
            ("sensory_cell",    "感知細胞", {"shape": "sphere",   "color": "#4A9EDB", "emissive": 0.3, "roughness": 0.2}),
            ("motor_cell",      "運動細胞", {"shape": "cylinder", "color": "#E67E22", "rigidity": 0.4, "roughness": 0.5}),
            ("secretory_cell",  "分泌細胞", {"shape": "sphere",   "color": "#2ECC71", "emissive": 0.2, "roughness": 0.3}),
            ("armor_cell",      "裝甲細胞", {"shape": "box",      "color": "#7F8C8D", "rigidity": 1.0, "roughness": 0.8}),
            ("neural_cell",     "神經細胞", {"shape": "sphere",   "color": "#9B59B6", "emissive": 0.5, "roughness": 0.1}),
            ("energy_cell",     "能量細胞", {"shape": "sphere",   "color": "#F39C12", "emissive": 0.7, "roughness": 0.2}),
        ]:
            self.add_tag(name, layer=0, label=label, morphology_hint=morph)

        # Layer 1: 器官層
        self.add_layer(1, "organ", "器官層")
        for name, label, morph in [
            ("central",         "中央器官",  {"shape": "sphere",   "color": "#9B59B6", "scale": [1.5, 1.5, 1.5]}),
            ("sensor",          "感知器官",  {"shape": "sphere",   "color": "#4A9EDB", "emissive": 0.4}),
            ("motor_organ",     "運動器官",  {"shape": "cylinder", "color": "#E67E22", "scale": [0.5, 1.5, 0.5]}),
            ("grasping_organ",  "抓握器官",  {"shape": "cylinder", "color": "#E74C3C", "sharpness": 0.6}),
            ("cutting_organ",   "切割器官",  {"shape": "cone",     "color": "#C0392B", "sharpness": 0.9}),
            ("defense_organ",   "防禦器官",  {"shape": "box",      "color": "#7F8C8D", "rigidity": 0.9}),
            ("secretion_organ", "分泌器官",  {"shape": "sphere",   "color": "#2ECC71", "emissive": 0.3}),
            ("energy_organ",    "能量器官",  {"shape": "sphere",   "color": "#F39C12", "emissive": 0.8}),
            ("structural",      "結構性",    {"rigidity": 0.8}),
            ("visual",          "視覺",      {"emissive": 0.4, "color": "#4A9EDB"}),
            ("grasping",        "抓握",      {"sharpness": 0.5}),
            ("cutting",         "切割",      {"sharpness": 0.8}),
            ("locomotion",      "運動",      {"rigidity": 0.3, "roughness": 0.4}),
            ("end_effector",    "末端效應器", {"scale": [0.3, 0.8, 0.3]}),
            ("receiver",        "接收器",    {"emissive": 0.3}),
            ("armor",           "裝甲",      {"rigidity": 1.0, "roughness": 0.7}),
        ]:
            self.add_tag(name, layer=1, label=label, morphology_hint=morph)

        # Layer 2: 部位層
        self.add_layer(2, "part", "部位層")
        for name, label, morph in [
            ("head",            "頭部",    {"shape": "sphere",   "color": "#BDC3C7", "scale": [1.2, 1.2, 1.2]}),
            ("torso",           "軀幹",    {"shape": "box",      "color": "#95A5A6", "scale": [2.0, 2.5, 1.5]}),
            ("limb",            "四肢",    {"shape": "cylinder", "color": "#BDC3C7", "scale": [0.4, 1.8, 0.4]}),
            ("appendage",       "附肢",    {"shape": "cylinder", "color": "#D5D8DC", "scale": [0.3, 1.2, 0.3]}),
            ("sensory_cluster", "感知叢",  {"shape": "sphere",   "color": "#4A9EDB", "scale": [0.6, 0.6, 0.6]}),
            ("weapon_part",     "武器部位", {"shape": "cone",     "color": "#E74C3C", "sharpness": 0.8}),
            ("shell",           "外殼",    {"shape": "box",      "color": "#7F8C8D", "rigidity": 1.0}),
            ("tail",            "尾巴",    {"shape": "cylinder", "color": "#BDC3C7", "scale": [0.3, 2.0, 0.3]}),
        ]:
            self.add_tag(name, layer=2, label=label, morphology_hint=morph)

        # 組合規則
        self.composition_rules = [
            {"inputs": {"sensory_cell", "neural_cell"},   "output": "sensor",          "layer": 1},
            {"inputs": {"motor_cell", "structural_cell"}, "output": "motor_organ",     "layer": 1},
            {"inputs": {"structural_cell", "armor_cell"}, "output": "defense_organ",   "layer": 1},
            {"inputs": {"secretory_cell"},                "output": "secretion_organ", "layer": 1},
            {"inputs": {"energy_cell", "neural_cell"},    "output": "energy_organ",    "layer": 1},
            {"inputs": {"sensor", "neural_cell"},         "output": "sensory_cluster", "layer": 2},
            {"inputs": {"motor_organ"},                   "output": "limb",            "layer": 2},
            {"inputs": {"central"},                       "output": "torso",           "layer": 2},
        ]

    def add_layer(self, layer_id: int, name: str, label: str):
        self.layers[layer_id] = {"name": name, "label": label}

    def add_tag(self, name: str, layer: int, label: str,
                description: str = "", morphology_hint: dict = None):
        self.tags[name] = OntologyTag(
            name=name, layer=layer, label=label,
            description=description,
            morphology_hint=morphology_hint or {}
        )

    def get_tag(self, name: str) -> Optional[OntologyTag]:
        return self.tags.get(name)

    def get_tags_by_layer(self, layer: int) -> list:
        return [t for t in self.tags.values() if t.layer == layer]

    def get_morphology_hint(self, semantic_tags: list) -> dict:
        hint = {}
        for tag_name in semantic_tags:
            tag = self.get_tag(tag_name)
            if tag and tag.morphology_hint:
                hint.update(tag.morphology_hint)
        return hint

    def get_prompt_context(self) -> str:
        lines = ["可用的 semantic tags（請使用這些標準 tag）：\n"]
        for layer_id in sorted(self.layers.keys()):
            layer = self.layers[layer_id]
            lines.append(f"Layer {layer_id} - {layer['label']}：")
            tags = self.get_tags_by_layer(layer_id)
            lines.append("  " + ", ".join(t.name for t in tags))
        return "\n".join(lines)

    def extend_with_game_stats(self):
        self.add_layer(3, "game_stat", "遊戲數值層")
        for name, label, morph in [
            ("strength_node", "力量節點", {"color": "#E74C3C", "emissive": 0.5}),
            ("mana_node",     "魔力節點", {"color": "#9B59B6", "emissive": 0.7}),
            ("vitality_node", "生命節點", {"color": "#2ECC71", "emissive": 0.4}),
            ("agility_node",  "敏捷節點", {"color": "#F39C12", "emissive": 0.3}),
        ]:
            self.add_tag(name, layer=3, label=label, morphology_hint=morph)

    def extend_with_elements(self):
        self.add_layer(4, "element", "元素屬性層")
        for name, label, morph in [
            ("fire_affinity",      "火屬性", {"color": "#E74C3C", "emissive": 0.8}),
            ("ice_affinity",       "冰屬性", {"color": "#85C1E9", "emissive": 0.4}),
            ("lightning_affinity", "雷屬性", {"color": "#F4D03F", "emissive": 0.9}),
            ("poison_affinity",    "毒屬性", {"color": "#27AE60", "emissive": 0.5}),
        ]:
            self.add_tag(name, layer=4, label=label, morphology_hint=morph)

    def validate_tags(self, semantic_tags: list) -> tuple:
        valid   = [t for t in semantic_tags if t in self.tags]
        unknown = [t for t in semantic_tags if t not in self.tags]
        return valid, unknown

    def suggest_tags(self, partial: str) -> list:
        return [name for name in self.tags if partial.lower() in name.lower()]


_default_ontology = None

def get_ontology() -> Ontology:
    global _default_ontology
    if _default_ontology is None:
        _default_ontology = Ontology()
    return _default_ontology


if __name__ == "__main__":
    onto = Ontology()
    print("🧬 RTIS Ontology System")
    print("=" * 50)
    print(f"層級數：{len(onto.layers)}，Tag 總數：{len(onto.tags)}")
    for layer_id in sorted(onto.layers.keys()):
        layer = onto.layers[layer_id]
        tags  = onto.get_tags_by_layer(layer_id)
        print(f"\nLayer {layer_id} - {layer['label']}（{len(tags)} tags）")
        for t in tags:
            print(f"  {t.name}")
    print("\n✅ Ontology 初始化成功")
