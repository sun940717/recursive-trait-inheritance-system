import random
import os
from copy import deepcopy
from trait import Trait, BodyGraph
from genome import Genome, GeneModule
from pce import get_all_traits, apply_trait
from metrics import evaluate, pce_match_rate
from pruning import prune_body


def random_attach(source_trait: Trait, target_body: BodyGraph) -> dict:
    """隨機附著（no-PCE baseline）：不用語意匹配，隨機選附著點"""
    all_traits = get_all_traits(target_body)
    if not all_traits:
        return {"status": "fallback", "attached_to": "none", "score": 0.0}
    
    target = random.choice(all_traits)
    from copy import deepcopy
    new_trait = deepcopy(source_trait)
    target.attach(new_trait)
    return {"status": "random", "attached_to": target.name, "score": 0.0}


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


def run_one_experiment(use_pce: bool, seed: int, generations: int = 10) -> list[dict]:
    """跑一次實驗，回傳每代的指標"""
    random.seed(seed)

    genome_a = Genome(seed=seed)
    genome_a.add_gene(GeneModule("sensor_node", ["sensor", "visual"], ["central"], 0.8))
    genome_a.add_gene(GeneModule("grasping_appendage", ["grasping", "end_effector"], ["structural"], 0.6))
    genome_a.add_gene(GeneModule("branch", ["structural"], ["structural"], 0.5))

    genome_b = Genome(seed=seed + 1)
    genome_b.add_gene(GeneModule("antenna", ["sensor", "receiver"], ["central"], 0.9))
    genome_b.add_gene(GeneModule("claw", ["grasping", "cutting"], ["structural"], 0.7))
    genome_b.add_gene(GeneModule("limb", ["structural", "locomotion"], ["structural"], 0.6))

    body_a = genome_a.develop()
    body_b = genome_b.develop()

    history = []
    m_a = evaluate(body_a, "A")
    m_b = evaluate(body_b, "B")
    history.append({
        "gen": 0,
        "avg_traits": (m_a["total_traits"] + m_b["total_traits"]) / 2,
        "avg_diversity": (m_a["diversity"] + m_b["diversity"]) / 2,
        "avg_depth": (m_a["avg_depth"] + m_b["avg_depth"]) / 2,
        "pce_match_rate": None
    })

    current_a = (body_a, genome_a)
    current_b = (body_b, genome_b)

    for gen in range(1, generations + 1):
        # 產生子代 Genome
        child1_genome = Genome(seed=random.randint(0, 9999))
        for gene in current_a[1].gene_modules:
            if random.random() > 0.5:
                child1_genome.add_gene(deepcopy(gene))
        for gene in current_b[1].gene_modules:
            if random.random() > 0.5:
                child1_genome.add_gene(deepcopy(gene))
        if not child1_genome.gene_modules:
            child1_genome.add_gene(deepcopy(current_a[1].gene_modules[0]))
        child1_genome = mutate_genome(child1_genome)
        child1_body = child1_genome.develop()

        child2_genome = Genome(seed=random.randint(0, 9999))
        for gene in current_b[1].gene_modules:
            if random.random() > 0.5:
                child2_genome.add_gene(deepcopy(gene))
        for gene in current_a[1].gene_modules:
            if random.random() > 0.5:
                child2_genome.add_gene(deepcopy(gene))
        if not child2_genome.gene_modules:
            child2_genome.add_gene(deepcopy(current_b[1].gene_modules[0]))
        child2_genome = mutate_genome(child2_genome)
        child2_body = child2_genome.develop()

        # PCE 或 random 繼承
        pce_results = []
        traits_a = get_all_traits(current_a[0])
        for trait in traits_a[:5]:
            if use_pce:
                result = apply_trait(trait, child1_body)
            else:
                result = random_attach(trait, child1_body)
            pce_results.append(result)

        traits_b = get_all_traits(current_b[0])
        for trait in traits_b[:5]:
            if use_pce:
                result = apply_trait(trait, child2_body)
            else:
                result = random_attach(trait, child2_body)
            pce_results.append(result)

        child1_body = prune_body(child1_body, max_traits=25)
        child2_body = prune_body(child2_body, max_traits=25)

        m1 = evaluate(child1_body, f"child1_gen{gen}")
        m2 = evaluate(child2_body, f"child2_gen{gen}")

        match_rate = pce_match_rate(pce_results) if use_pce else 0.0

        history.append({
            "gen": gen,
            "avg_traits": (m1["total_traits"] + m2["total_traits"]) / 2,
            "avg_diversity": (m1["diversity"] + m2["diversity"]) / 2,
            "avg_depth": (m1["avg_depth"] + m2["avg_depth"]) / 2,
            "pce_match_rate": match_rate
        })

        current_a = (child1_body, child1_genome)
        current_b = (child2_body, child2_genome)

    return history


def run_comparison(seeds: list[int] = None, generations: int = 10):
    """跑多個 seed，比較 PCE vs no-PCE"""
    if seeds is None:
        seeds = [42, 123, 456, 789, 1024, 2048, 3141, 9999, 7777, 5555]

    print("🧪 RTIS 實驗：PCE vs No-PCE")
    print("=" * 60)
    print(f"Seeds: {seeds}")
    print(f"Generations: {generations}")
    print()

    pce_results = []
    no_pce_results = []

    for seed in seeds:
        print(f"  Running seed {seed}...", end=" ")
        pce_hist = run_one_experiment(use_pce=True, seed=seed, generations=generations)
        no_pce_hist = run_one_experiment(use_pce=False, seed=seed, generations=generations)
        pce_results.append(pce_hist)
        no_pce_results.append(no_pce_hist)
        print("done")

    # 計算每代的平均值
    print("\n📊 結果比較")
    print("=" * 60)
    print(f"{'代數':<6} {'PCE多樣性':>12} {'No-PCE多樣性':>14} {'PCE trait數':>12} {'No-PCE trait數':>15}")

    os.makedirs("outputs", exist_ok=True)
    lines = ["# PCE vs No-PCE 實驗結果\n\n"]
    lines.append(f"| 代數 | PCE多樣性 | No-PCE多樣性 | PCE trait數 | No-PCE trait數 | PCE匹配率 |\n")
    lines.append(f"|------|-----------|-------------|------------|---------------|----------|\n")

    for gen in range(generations + 1):
        pce_div = sum(r[gen]["avg_diversity"] for r in pce_results) / len(seeds)
        no_pce_div = sum(r[gen]["avg_diversity"] for r in no_pce_results) / len(seeds)
        pce_traits = sum(r[gen]["avg_traits"] for r in pce_results) / len(seeds)
        no_pce_traits = sum(r[gen]["avg_traits"] for r in no_pce_results) / len(seeds)
        pce_match = sum(r[gen]["pce_match_rate"] or 0 for r in pce_results) / len(seeds)

        print(f"{gen:<6} {pce_div:>12.3f} {no_pce_div:>14.3f} {pce_traits:>12.1f} {no_pce_traits:>15.1f}")
        lines.append(f"| {gen} | {pce_div:.3f} | {no_pce_div:.3f} | {pce_traits:.1f} | {no_pce_traits:.1f} | {pce_match:.3f} |\n")

    with open("outputs/pce_vs_nopce.md", "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n✅ 結果已存到 outputs/pce_vs_nopce.md")


if __name__ == "__main__":
    run_comparison(generations=10)