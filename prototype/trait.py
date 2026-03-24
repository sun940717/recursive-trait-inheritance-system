from dataclasses import dataclass, field
from typing import Optional
import uuid

@dataclass
class Trait:
    trait_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    semantic_tags: list[str] = field(default_factory=list)
    morphology: dict = field(default_factory=dict)
    children: list["Trait"] = field(default_factory=list)

    def attach(self, other: "Trait"):
        """把另一個 trait 附著到這個 trait 上"""
        self.children.append(other)
        return self

    def describe(self, depth=0) -> str:
        indent = "  " * depth
        desc = f"{indent}[{self.trait_id}] {self.name} {self.semantic_tags}\n"
        for child in self.children:
            desc += child.describe(depth + 1)
        return desc


@dataclass
class BodyGraph:
    organism_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    nodes: list[Trait] = field(default_factory=list)

    def add_trait(self, trait: Trait):
        self.nodes.append(trait)
        return self

    def describe(self) -> str:
        out = f"Organism [{self.organism_id}]\n"
        for node in self.nodes:
            out += node.describe(depth=1)
        return out


if __name__ == "__main__":
    # 測試：建一個簡單的 organism
    head = Trait(name="head", semantic_tags=["sensor", "central"])
    eye = Trait(name="eye", semantic_tags=["sensor", "visual"])
    hand = Trait(name="hand", semantic_tags=["grasping", "end_effector"])
    finger = Trait(name="finger", semantic_tags=["grasping", "end_effector"])

    # 遞迴附著：eye 長在 head 上，finger 長在 hand 上
    head.attach(eye)
    hand.attach(finger)

    # 奇異附著：hand 長在 head 上（RTIS 的核心特性）
    head.attach(hand)

    body = BodyGraph()
    body.add_trait(head)

    print(body.describe())