import os
import json
import random
from copy import deepcopy
from dotenv import load_dotenv
import anthropic
from trait import Trait, BodyGraph
from genome import Genome, GeneModule
from pce import get_all_traits

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM = """You are a biological evolution simulation engine.

Your job is to decide how two parent organisms produce an offspring with realistic mutations.

Rules:
- The offspring must retain the core skeletal structure of the dominant parent (the one with more traits)
- Mutation probabilities:
  * micro (95%): slight size/strength changes, color shifts — describe as scale adjustment
  * medium (15%): one trait deleted OR one new similar trait added
  * major (3%): a completely new trait type emerges (rare, surprising)
- Mutations should feel biological — a spider-jellyfish hybrid might have tentacles that end in fang-tips
- Inherited mutations are marked as heritable=true (they pass to the next generation)
- Non-heritable mutations are marked heritable=false (one-time expression)

You must respond ONLY with valid JSON, no explanation, no markdown.

JSON format:
{
  "offspring_traits": [
    {
      "name": "trait_name",
      "semantic_tags": ["tag1", "tag2"],
      "parent_source": "A" or "B" or "mutation",
      "mutation_type": "none" or "micro" or "medium" or "major",
      "mutation_desc": "brief description of what changed",
      "heritable": true or false,
      "scale": 1.0
    }
  ],
  "mutation_summary": "one sentence describing the offspring's overall character"
}"""


def describe_organism(body: BodyGraph, name: str) -> str:
    traits = get_all_traits(body)
    trait_list = ", ".join([f"{t.name}[{','.join(t.semantic_tags)}]" for t in traits])
    return f"{name}: {len(traits)} traits — {trait_list}"


def ai_mutate(body_a: BodyGraph, body_b: BodyGraph,
              name_a: str = "Parent A", name_b: str = "Parent B") -> dict:
    """讓 Claude 決定子代的突變結果"""

    desc_a = describe_organism(body_a, name_a)
    desc_b = describe_organism(body_b, name_b)

    prompt = f"""Two organisms are breeding. Decide the offspring's traits with realistic mutations.

{desc_a}
{desc_b}

The dominant parent (more traits) provides the base skeleton.
Apply mutations following the probability rules.
Return JSON only."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    # 清理可能的 markdown
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    return json.loads(text)


def build_offspring_from_ai(result: dict, parent_body: BodyGraph) -> tuple[BodyGraph, list]:
    """根據 AI 的決定建立子代 BodyGraph"""
    from pce import get_all_traits

    # TAG_3D 對應（用於設定顏色和形狀）
    TAG_SHAPES = {
        "central":      {"shape": "sphere",   "radius": 1.2, "color": "#9B59B6"},
        "structural":   {"shape": "box",      "size": [0.8, 1.5, 0.8], "color": "#95A5A6"},
        "sensor":       {"shape": "sphere",   "radius": 0.5, "color": "#4A9EDB"},
        "visual":       {"shape": "sphere",   "radius": 0.4, "color": "#2ECC71"},
        "grasping":     {"shape": "cylinder", "radius": 0.3, "height": 1.2, "color": "#E74C3C"},
        "end_effector": {"shape": "cone",     "radius": 0.4, "height": 0.8, "color": "#E67E22"},
        "cutting":      {"shape": "cone",     "radius": 0.3, "height": 1.0, "color": "#C0392B"},
        "locomotion":   {"shape": "cylinder", "radius": 0.5, "height": 0.8, "color": "#F39C12"},
        "receiver":     {"shape": "sphere",   "radius": 0.4, "color": "#1ABC9C"},
    }

    mutation_log = []
    offspring_body = BodyGraph()

    # 建立 root
    root = Trait(name="root", semantic_tags=["central", "structural"])
    offspring_body.add_trait(root)

    # 根據 AI 決定的 traits 建立子代
    for t_info in result.get("offspring_traits", []):
        trait = Trait(
            name=t_info["name"],
            semantic_tags=t_info["semantic_tags"]
        )

        # scale 影響形狀大小（存在 morphology 裡）
        scale = t_info.get("scale", 1.0)
        trait.morphology = {
            "scale": scale,
            "heritable": t_info.get("heritable", True),
            "mutation_type": t_info.get("mutation_type", "none"),
            "mutation_desc": t_info.get("mutation_desc", "")
        }

        root.attach(trait)

        if t_info.get("mutation_type", "none") != "none":
            mutation_log.append({
                "trait": t_info["name"],
                "type": t_info["mutation_type"],
                "desc": t_info.get("mutation_desc", ""),
                "heritable": t_info.get("heritable", True)
            })

    return offspring_body, mutation_log


def print_mutation_log(mutation_log: list, summary: str):
    print(f"\n🧬 突變報告：{summary}")
    if not mutation_log:
        print("  無顯著突變")
        return
    for m in mutation_log:
        icon = {"micro": "🟡", "medium": "🟠", "major": "🔴"}.get(m["type"], "⚪")
        heritable = "✓可遺傳" if m["heritable"] else "✗不可遺傳"
        print(f"  {icon} [{m['type']}] {m['trait']}: {m['desc']} ({heritable})")


if __name__ == "__main__":
    from pruning import prune_body
    from body3d import body_to_3d_json, generate_viewer

    # 建兩個親代
    genome_a = Genome(seed=42)
    genome_a.add_gene(GeneModule("body", ["central", "structural"], ["central"], 1.0))
    genome_a.add_gene(GeneModule("leg", ["structural", "locomotion"], ["structural"], 0.9))
    genome_a.add_gene(GeneModule("fang", ["grasping", "cutting"], ["structural"], 0.8))
    genome_a.add_gene(GeneModule("eye", ["sensor", "visual"], ["central"], 0.9))

    genome_b = Genome(seed=99)
    genome_b.add_gene(GeneModule("bell", ["central", "structural"], ["central"], 1.0))
    genome_b.add_gene(GeneModule("tentacle", ["grasping", "end_effector"], ["structural"], 0.9))
    genome_b.add_gene(GeneModule("sensor_tip", ["sensor", "receiver"], ["end_effector"], 0.7))
    genome_b.add_gene(GeneModule("fin", ["structural", "locomotion"], ["structural"], 0.6))

    body_a = genome_a.develop()
    body_b = genome_b.develop()
    body_a = prune_body(body_a, max_traits=12)
    body_b = prune_body(body_b, max_traits=12)

    print("🤖 AI 決定突變中...")
    result = ai_mutate(body_a, body_b, "Spider", "Jellyfish")

    print(f"✓ AI 決定了 {len(result['offspring_traits'])} 個 traits")
    offspring_body, mutation_log = build_offspring_from_ai(result, body_a)
    print_mutation_log(mutation_log, result.get("mutation_summary", ""))

    # 存突變紀錄
    os.makedirs("outputs/mutations", exist_ok=True)
    with open("outputs/mutations/latest_mutation.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("\n✅ 突變紀錄存到 outputs/mutations/latest_mutation.json")

    # 生成 3D viewer
    generate_viewer(offspring_body, "outputs/visuals/ai_offspring_3d.html")
