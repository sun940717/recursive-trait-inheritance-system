import random
import os
from copy import deepcopy
from trait import Trait, BodyGraph
from genome import Genome, GeneModule
from pce import get_all_traits, apply_trait
from metrics import evaluate, print_metrics, pce_match_rate


def mutate_genome(genome: Genome, mutation_rate: float = 0.3) -> Genome:
    new_genome = deepcopy(genome)
    new_genome.seed = random.randint(0, 9999)
    for gene in new_genome.gene_modules:
        if random.random() < mutation_rate:
            gene.probability = max(0.1, min(1.0,
                gene.probability + random.uniform(-0.2, 0.2)))
    if new_genome.gene_modules and random.random() < mutation_rate:
        duplicated = deepcopy(random.choice(new_genome.gene_modules))
        duplicated.name = duplicated.name + "_v2"
        new_genome.gene_modules.append(duplicated)
    return new_genome


def reproduce(body_a: BodyGraph, body_b: BodyGraph,
              genome_a: Genome, genome_b: Genome) -> tuple[BodyGraph, Genome, list[dict]]:
    child_genome = Genome(seed=random.randint(0, 9999))
    genes_a = genome_a.gene_modules
    genes_b = genome_b.gene_modules
    for gene in genes_a:
        if random.random() > 0.5:
            child_genome.add_gene(deepcopy(gene))
    for gene in genes_b:
        if random.random() > 0.5:
            child_genome.add_gene(deepcopy(gene))
    if not child_genome.gene_modules:
        child_genome.add_gene(deepcopy(random.choice(genes_a + genes_b)))
    child_genome = mutate_genome(child_genome)
    child_body = child_genome.develop()

    # PCE 繼承 + 記錄結果
    pce_results = []
    traits_a = get_all_traits(body_a)
    for trait in traits_a[:5]:
        result = apply_trait(trait, child_body)
        pce_results.append(result)

    # 修剪：控制結構膨脹
    from pruning import prune_body
    child_body = prune_body(child_body, max_traits=25)

    return child_body, child_genome, pce_results


def run_evolution(generations: int = 5):
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

    # 記錄每代數據
    history = []

    print("=" * 50)
    print("第 0 代（親代）")
    print("=" * 50)
    m_a = evaluate(body_a, "Organism A")
    m_b = evaluate(body_b, "Organism B")
    print_metrics(m_a)
    print_metrics(m_b)
    history.append({"gen": 0, "avg_traits": (m_a["total_traits"] + m_b["total_traits"]) / 2,
                    "avg_diversity": (m_a["diversity"] + m_b["diversity"]) / 2,
                    "avg_depth": (m_a["avg_depth"] + m_b["avg_depth"]) / 2,
                    "pce_match_rate": None})

    current_a = (body_a, genome_a)
    current_b = (body_b, genome_b)

    for gen in range(1, generations + 1):
        print(f"\n{'=' * 50}")
        print(f"第 {gen} 代")
        print("=" * 50)

        child1_body, child1_genome, pce1 = reproduce(
            current_a[0], current_b[0], current_a[1], current_b[1])
        child2_body, child2_genome, pce2 = reproduce(
            current_b[0], current_a[0], current_b[1], current_a[1])

        m1 = evaluate(child1_body, f"子代1 gen{gen}")
        m2 = evaluate(child2_body, f"子代2 gen{gen}")
        all_pce = pce1 + pce2

        print_metrics(m1)
        print_metrics(m2)
        print(f"\n  PCE 匹配率：{pce_match_rate(all_pce)}")

        history.append({
            "gen": gen,
            "avg_traits": (m1["total_traits"] + m2["total_traits"]) / 2,
            "avg_diversity": (m1["diversity"] + m2["diversity"]) / 2,
            "avg_depth": (m1["avg_depth"] + m2["avg_depth"]) / 2,
            "pce_match_rate": pce_match_rate(all_pce)
        })

        current_a = (child1_body, child1_genome)
        current_b = (child2_body, child2_genome)

    # 印出演化趨勢
    print(f"\n{'=' * 50}")
    print("演化趨勢摘要")
    print("=" * 50)
    print(f"{'代數':<6} {'平均trait數':<12} {'多樣性':<10} {'平均深度':<10} {'PCE匹配率'}")
    for h in history:
        pce = str(h['pce_match_rate']) if h['pce_match_rate'] is not None else "N/A"
        print(f"{h['gen']:<6} {h['avg_traits']:<12} {h['avg_diversity']:<10} {h['avg_depth']:<10} {pce}")

    # 存成 markdown
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/evolution_results.md", "w", encoding="utf-8") as f:
        f.write("# RTIS Evolution Results\n\n")
        f.write("| 代數 | 平均trait數 | 多樣性 | 平均深度 | PCE匹配率 |\n")
        f.write("|------|------------|--------|----------|----------|\n")
        for h in history:
            pce = str(h['pce_match_rate']) if h['pce_match_rate'] is not None else "N/A"
            f.write(f"| {h['gen']} | {h['avg_traits']} | {h['avg_diversity']} | {h['avg_depth']} | {pce} |\n")
    print("\n✅ 結果已存到 outputs/evolution_results.md")


if __name__ == "__main__":
    run_evolution(generations=5)