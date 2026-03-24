from trait import Trait, BodyGraph
from pce import get_all_traits


def trait_fitness(trait: Trait, all_traits: list[Trait]) -> float:
    """
    計算單一 trait 的 fitness：
    - tag 越稀有分數越高（鼓勵多樣性）
    - 越深的 trait 分數略低（避免無限膨脹）
    """
    # 統計所有 tag 的頻率
    tag_counts = {}
    for t in all_traits:
        for tag in t.semantic_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # trait 的稀有度分數：tag 越少見分數越高
    if not trait.semantic_tags:
        return 0.0
    rarity = sum(1 / tag_counts[tag] for tag in trait.semantic_tags)
    rarity /= len(trait.semantic_tags)
    return round(rarity, 4)


def prune_body(body: BodyGraph, max_traits: int = 20) -> BodyGraph:
    """
    修剪 BodyGraph：保留 fitness 最高的 trait
    保護 root 節點不被刪除
    """
    all_traits = get_all_traits(body)

    if len(all_traits) <= max_traits:
        return body

    # 計算 fitness，root 節點強制保留
    scored = []
    for t in all_traits:
        if t in body.nodes:
            score = 999  # root 永遠保留
        else:
            score = trait_fitness(t, all_traits)
        scored.append((t, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    keep = set(id(t) for t, _ in scored[:max_traits])

    # 確保所有 root 都在 keep 裡
    for node in body.nodes:
        keep.add(id(node))

    def filter_children(trait: Trait) -> Trait:
        trait.children = [
            filter_children(c) for c in trait.children
            if id(c) in keep
        ]
        return trait

    for node in body.nodes:
        filter_children(node)

    return body