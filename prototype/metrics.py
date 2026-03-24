from trait import Trait, BodyGraph
from pce import get_all_traits


def trait_diversity(body: BodyGraph) -> float:
    """trait 多樣性：不同種類的 trait 佔總數的比例"""
    all_traits = get_all_traits(body)
    if not all_traits:
        return 0.0
    unique_names = set(t.name for t in all_traits)
    return round(len(unique_names) / len(all_traits), 3)


def structural_complexity(body: BodyGraph) -> float:
    """結構複雜度：trait graph 的平均深度"""
    def get_depth(trait: Trait, depth: int) -> list[int]:
        depths = [depth]
        for child in trait.children:
            depths.extend(get_depth(child, depth + 1))
        return depths

    all_depths = []
    for node in body.nodes:
        all_depths.extend(get_depth(node, 0))

    if not all_depths:
        return 0.0
    return round(sum(all_depths) / len(all_depths), 3)


def total_trait_count(body: BodyGraph) -> int:
    """總 trait 數量"""
    return len(get_all_traits(body))


def pce_match_rate(results: list[dict]) -> float:
    """PCE 匹配成功率"""
    if not results:
        return 0.0
    matched = sum(1 for r in results if r["status"] == "matched")
    return round(matched / len(results), 3)


def tag_distribution(body: BodyGraph) -> dict:
    """各 semantic tag 的出現次數"""
    all_traits = get_all_traits(body)
    dist = {}
    for trait in all_traits:
        for tag in trait.semantic_tags:
            dist[tag] = dist.get(tag, 0) + 1
    return dict(sorted(dist.items(), key=lambda x: x[1], reverse=True))


def evaluate(body: BodyGraph, label: str = "") -> dict:
    """一次計算所有指標"""
    result = {
        "label": label,
        "total_traits": total_trait_count(body),
        "diversity": trait_diversity(body),
        "avg_depth": structural_complexity(body),
        "tag_distribution": tag_distribution(body)
    }
    return result


def print_metrics(metrics: dict):
    print(f"\n📊 [{metrics['label']}]")
    print(f"  總 trait 數：{metrics['total_traits']}")
    print(f"  多樣性：{metrics['diversity']} （越高越好）")
    print(f"  平均深度：{metrics['avg_depth']}")
    print(f"  Tag 分布：{metrics['tag_distribution']}")