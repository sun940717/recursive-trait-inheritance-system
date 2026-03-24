from trait import Trait, BodyGraph

def semantic_similarity(tags_a: list[str], tags_b: list[str]) -> float:
    """計算兩組 semantic tags 的相似度"""
    if not tags_a or not tags_b:
        return 0.0
    intersection = set(tags_a) & set(tags_b)
    union = set(tags_a) | set(tags_b)
    return len(intersection) / len(union)


def get_all_traits(body: BodyGraph) -> list[Trait]:
    """取得 BodyGraph 裡所有 trait（遞迴展開）"""
    result = []
    def collect(trait: Trait):
        result.append(trait)
        for child in trait.children:
            collect(child)
    for node in body.nodes:
        collect(node)
    return result


def find_candidates(trait: Trait, target_body: BodyGraph, 
                    top_k: int = 2) -> list[tuple[Trait, float]]:
    """找出 target_body 裡最適合附著的節點"""
    all_traits = get_all_traits(target_body)
    scored = []
    for candidate in all_traits:
        score = semantic_similarity(trait.semantic_tags, candidate.semantic_tags)
        if score > 0:
            scored.append((candidate, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def apply_trait(source_trait: Trait, target_body: BodyGraph) -> dict:
    """PCE 核心：把 source trait 附著到 target_body 的最佳位置"""
    candidates = find_candidates(source_trait, target_body)

    if not candidates:
        # Fallback：附著到 root
        fallback_node = target_body.nodes[0]
        from copy import deepcopy
        new_trait = deepcopy(source_trait)
        fallback_node.attach(new_trait)
        return {
            "status": "fallback",
            "attached_to": fallback_node.name,
            "score": 0.0
        }

    # 正常附著到最高分候選
    best_node, best_score = candidates[0]
    from copy import deepcopy
    new_trait = deepcopy(source_trait)
    best_node.attach(new_trait)

    return {
        "status": "matched",
        "attached_to": best_node.name,
        "score": round(best_score, 3),
        "candidates": [(c.name, round(s, 3)) for c, s in candidates]
    }


if __name__ == "__main__":
    from genome import Genome, GeneModule

    # 建兩個不同的 organism
    genome_a = Genome(seed=42)
    genome_a.add_gene(GeneModule("sensor_node", ["sensor", "visual"], ["central"], 0.8))
    genome_a.add_gene(GeneModule("grasping_appendage", ["grasping", "end_effector"], ["structural"], 0.6))
    genome_a.add_gene(GeneModule("branch", ["structural"], ["structural"], 0.5))

    genome_b = Genome(seed=99)
    genome_b.add_gene(GeneModule("antenna", ["sensor", "receiver"], ["central"], 0.9))
    genome_b.add_gene(GeneModule("claw", ["grasping", "cutting"], ["structural"], 0.7))
    genome_b.add_gene(GeneModule("limb", ["structural", "locomotion"], ["structural"], 0.6))

    body_a = genome_a.develop()
    body_b = genome_b.develop()

    print("=== Organism A ===")
    print(body_a.describe())
    print("=== Organism B ===")
    print(body_b.describe())

    # PCE：把 A 的 grasping trait 對應到 B
    all_a = get_all_traits(body_a)
    grasping_trait = next((t for t in all_a if "grasping" in t.semantic_tags), None)

    if grasping_trait:
        print(f"\n=== PCE：把 '{grasping_trait.name}' 從 A 附著到 B ===")
        result = apply_trait(grasping_trait, body_b)
        print(f"狀態：{result['status']}")
        print(f"附著到：{result['attached_to']}（相似度 {result['score']}）")
        if 'candidates' in result:
            print(f"候選節點：{result['candidates']}")
        print("\n=== Organism B（附著後）===")
        print(body_b.describe())