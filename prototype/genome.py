import random
from trait import Trait, BodyGraph

class GeneModule:
    """單一基因模組：定義一個生長操作"""
    def __init__(self, name: str, semantic_tags: list[str], 
                 condition_tags: list[str] = None, probability: float = 1.0):
        self.name = name
        self.semantic_tags = semantic_tags
        self.condition_tags = condition_tags or []
        self.probability = probability

    def can_apply(self, trait: Trait) -> bool:
        """檢查這個基因能不能作用在這個 trait 上"""
        if not self.condition_tags:
            return True
        return any(tag in trait.semantic_tags for tag in self.condition_tags)

    def apply(self, trait: Trait) -> Trait | None:
        """把基因模組套用到 trait，長出新的子 trait"""
        if not self.can_apply(trait):
            return None
        if random.random() > self.probability:
            return None
        new_trait = Trait(name=self.name, semantic_tags=self.semantic_tags.copy())
        trait.attach(new_trait)
        return new_trait


class Genome:
    """基因組：一組基因模組 + 生長規則"""
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.gene_modules: list[GeneModule] = []
        self.max_depth: int = 3

    def add_gene(self, gene: GeneModule):
        self.gene_modules.append(gene)
        return self

    def develop(self) -> BodyGraph:
        """執行發育過程：Genome → BodyGraph"""
        random.seed(self.seed)
        body = BodyGraph()

        # 起點：一個 root trait
        root = Trait(name="root", semantic_tags=["central", "structural"])
        body.add_trait(root)

        # 遞迴生長
        self._grow(root, depth=0)
        return body

    def _grow(self, trait: Trait, depth: int):
        if depth >= self.max_depth:
            return
        for gene in self.gene_modules:
            new_trait = gene.apply(trait)
            if new_trait:
                self._grow(new_trait, depth + 1)


if __name__ == "__main__":
    genome = Genome(seed=42)
    genome.add_gene(GeneModule(
        name="sensor_node",
        semantic_tags=["sensor", "visual"],
        condition_tags=["central", "structural"],
        probability=0.8
    ))
    genome.add_gene(GeneModule(
        name="grasping_appendage",
        semantic_tags=["grasping", "end_effector"],
        condition_tags=["structural"],
        probability=0.6
    ))
    genome.add_gene(GeneModule(
        name="branch",
        semantic_tags=["structural"],
        condition_tags=["structural"],
        probability=0.5
    ))

    body = genome.develop()
    print(body.describe())
    print(f"總 trait 數量：{sum(1 for _ in body.nodes)}")