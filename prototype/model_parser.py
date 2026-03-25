import os
import json
import numpy as np
from dotenv import load_dotenv
import anthropic

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM = """You are a biological trait analysis system for RTIS (Recursive Trait Inheritance System).

Given a description of a 3D model's geometric structure, you must:
1. Identify what kind of organism or creature this model represents
2. Decompose it into semantic traits based on the mesh groups and their properties
3. Assign appropriate semantic tags to each trait

Available semantic tags:
- central: main body core
- structural: skeleton, limbs, rigid parts
- sensor: sensory organs (eyes, antennae)
- visual: decorative or visual features
- grasping: claws, hands, gripping parts
- cutting: blades, teeth, sharp edges
- end_effector: tips of limbs or tentacles
- locomotion: legs, fins, wings for movement
- receiver: organs that detect signals
- armor: protective shell or plating
- appendage: general attachment

You must respond ONLY with valid JSON, no explanation, no markdown.

JSON format:
{
  "organism_name": "detected creature type",
  "organism_description": "one sentence description",
  "traits": [
    {
      "name": "trait_name",
      "semantic_tags": ["tag1", "tag2"],
      "description": "what this part is",
      "relative_size": "large/medium/small",
      "position_hint": "top/center/bottom/left/right/peripheral"
    }
  ]
}"""


def parse_obj(filepath: str) -> dict:
    """解析 .obj 檔案，提取 mesh 群組資訊"""
    groups = {}
    current_group = "default"
    vertices = []

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line.startswith('g ') or line.startswith('o '):
                current_group = line.split()[1] if len(line.split()) > 1 else "unnamed"
                if current_group not in groups:
                    groups[current_group] = {"vertices": [], "face_count": 0}
            elif line.startswith('v ') and not line.startswith('vt') and not line.startswith('vn'):
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        v = [float(parts[1]), float(parts[2]), float(parts[3])]
                        vertices.append(v)
                        if current_group in groups:
                            groups[current_group]["vertices"].append(v)
                    except ValueError:
                        pass
            elif line.startswith('f '):
                if current_group in groups:
                    groups[current_group]["face_count"] += 1

    # 計算每個群組的幾何描述
    result = []
    all_verts = np.array(vertices) if vertices else np.zeros((1, 3))
    model_size = all_verts.max(axis=0) - all_verts.min(axis=0) if len(all_verts) > 1 else np.ones(3)

    for name, data in groups.items():
        if not data["vertices"]:
            continue
        verts = np.array(data["vertices"])
        center = verts.mean(axis=0)
        size = verts.max(axis=0) - verts.min(axis=0)
        volume = size[0] * size[1] * size[2]

        # 相對位置（相對於整體模型）
        rel_pos = center / (model_size + 1e-6)
        if rel_pos[1] > 0.6:
            pos_hint = "top"
        elif rel_pos[1] < 0.4:
            pos_hint = "bottom"
        else:
            pos_hint = "center"

        # 形狀描述
        dims = sorted(size)
        if dims[2] / (dims[0] + 1e-6) > 3:
            shape = "elongated"
        elif dims[2] / (dims[0] + 1e-6) < 1.5:
            shape = "compact/spherical"
        else:
            shape = "medium"

        result.append({
            "name": name,
            "vertex_count": len(data["vertices"]),
            "face_count": data["face_count"],
            "center": center.tolist(),
            "size": size.tolist(),
            "shape": shape,
            "position_hint": pos_hint,
            "relative_volume": float(volume / (model_size.prod() + 1e-6))
        })

    return {
        "format": "obj",
        "total_vertices": len(vertices),
        "groups": result,
        "group_count": len(result)
    }


def parse_glb(filepath: str) -> dict:
    """解析 .glb/.gltf 檔案"""
    from pygltflib import GLTF2
    gltf = GLTF2().load(filepath)

    meshes_info = []
    for i, mesh in enumerate(gltf.meshes):
        name = mesh.name or f"mesh_{i}"
        prim_count = len(mesh.primitives)
        meshes_info.append({
            "name": name,
            "primitive_count": prim_count,
            "position_hint": "center"
        })

    nodes_info = []
    for node in gltf.nodes:
        n = {"name": node.name or "unnamed"}
        if node.translation:
            t = node.translation
            if t[1] > 0.5:
                n["position_hint"] = "top"
            elif t[1] < -0.5:
                n["position_hint"] = "bottom"
            else:
                n["position_hint"] = "center"
            n["position"] = list(t)
        if node.scale:
            n["scale"] = list(node.scale)
        nodes_info.append(n)

    return {
        "format": "glb/gltf",
        "mesh_count": len(gltf.meshes),
        "node_count": len(gltf.nodes),
        "meshes": meshes_info,
        "nodes": nodes_info[:20]  # 最多20個節點避免過長
    }


def parse_json_rtis(filepath: str) -> dict:
    """解析自訂 RTIS JSON 格式"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {"format": "rtis_json", "data": data}


def detect_format(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    return {
        ".obj": "obj",
        ".glb": "glb",
        ".gltf": "gltf",
        ".json": "json",
    }.get(ext, "unknown")


def parse_model(filepath: str) -> dict:
    """自動偵測格式並解析"""
    fmt = detect_format(filepath)
    print(f"📂 偵測到格式：{fmt.upper()}")

    if fmt == "obj":
        return parse_obj(filepath)
    elif fmt in ["glb", "gltf"]:
        return parse_glb(filepath)
    elif fmt == "json":
        return parse_json_rtis(filepath)
    else:
        raise ValueError(f"不支援的格式：{fmt}")


def ai_identify_traits(model_info: dict, filename: str = "") -> dict:
    """讓 Claude 辨識模型結構並拆解成 trait graph"""

    prompt = f"""Analyze this 3D model and decompose it into RTIS traits.

Model file: {filename}
Format: {model_info.get('format', 'unknown')}

Geometric structure:
{json.dumps(model_info, indent=2)[:3000]}

Identify the organism type and decompose into semantic traits."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    return json.loads(text)


def traits_to_bodygraph(ai_result: dict):
    """把 AI 辨識結果轉成 BodyGraph"""
    from trait import Trait, BodyGraph
    from genome import Genome, GeneModule

    genome = Genome(seed=42)
    for t in ai_result.get("traits", []):
        gene = GeneModule(
            name=t["name"],
            semantic_tags=t["semantic_tags"],
            condition_tags=["central"] if "central" in t["semantic_tags"] else ["structural"],
            probability=0.9
        )
        genome.add_gene(gene)

    from pruning import prune_body
    body = genome.develop()
    body = prune_body(body, max_traits=15)
    return body


def run():
    print("🔍 RTIS Model Parser")
    print("=" * 50)
    print("支援格式：.obj  .glb  .gltf  .json")
    print()

    filepath = input("輸入模型檔案路徑：").strip().strip('"')

    if not os.path.exists(filepath):
        print(f"❌ 找不到檔案：{filepath}")
        return

    print(f"\n📊 解析模型中...")
    model_info = parse_model(filepath)
    print(f"✓ 解析完成：{model_info.get('format', '?')} 格式")

    print(f"\n🤖 Claude 辨識 trait 結構中...")
    ai_result = ai_identify_traits(model_info, os.path.basename(filepath))

    print(f"\n✅ 辨識結果：")
    print(f"   生物類型：{ai_result.get('organism_name', '?')}")
    print(f"   描述：{ai_result.get('organism_description', '?')}")
    print(f"   Traits：{len(ai_result.get('traits', []))} 個")
    for t in ai_result.get("traits", []):
        print(f"   - {t['name']} [{', '.join(t['semantic_tags'])}] ({t.get('position_hint', '?')})")

    # 存辨識結果
    os.makedirs("outputs/parsed_models", exist_ok=True)
    out_path = f"outputs/parsed_models/{os.path.splitext(os.path.basename(filepath))[0]}_traits.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ai_result, f, indent=2, ensure_ascii=False)
    print(f"\n💾 結果存到：{out_path}")

    # 問是否生成 3D viewer
    view = input("\n要生成 3D viewer 嗎？(y/n)：").strip().lower()
    if view == 'y':
        body = traits_to_bodygraph(ai_result)
        from body3d import generate_viewer
        out_html = f"outputs/visuals/{os.path.splitext(os.path.basename(filepath))[0]}_3d.html"
        generate_viewer(body, out_html)

    # 問是否要跟其他模型合成
    fuse = input("\n要跟其他模型合成嗎？(y/n)：").strip().lower()
    if fuse == 'y':
        print("\n選擇要合成的對象：")
        print("  1. Spider")
        print("  2. Jellyfish")
        print("  3. Crab")
        print("  4. Serpent")
        print("  5. 輸入另一個模型檔案")

        choice = input("選擇：").strip()

        from fusion3d import PRESET_ORGANISMS, build_organism, fuse_organisms, generate_fusion_viewer
        from pce import get_all_traits
        from ai_mutation import ai_mutate, build_offspring_from_ai, print_mutation_log

        body_a = traits_to_bodygraph(ai_result)
        name_a = ai_result.get("organism_name", "Model A")

        if choice in ["1", "2", "3", "4"]:
            preset_map = {"1": "1", "2": "2", "3": "3", "4": "4"}
            preset = PRESET_ORGANISMS[preset_map[choice]]
            body_b, genome_b = build_organism(preset)
            name_b = preset["name"]
        elif choice == "5":
            path_b = input("輸入第二個模型路徑：").strip().strip('"')
            model_b = parse_model(path_b)
            result_b = ai_identify_traits(model_b, os.path.basename(path_b))
            body_b = traits_to_bodygraph(result_b)
            name_b = result_b.get("organism_name", "Model B")
        else:
            print("無效選擇")
            return

        print(f"\n🤖 AI 決定突變中...")
        mutation_result = ai_mutate(body_a, body_b, name_a, name_b)
        offspring_body, mutation_log = build_offspring_from_ai(mutation_result, body_a)
        print_mutation_log(mutation_log, mutation_result.get("mutation_summary", ""))

        from genome import Genome
        bodies_info = [
            {"body": body_a, "name": name_a, "color": "#4A9EDB"},
            {"body": body_b, "name": name_b, "color": "#E74C3C"},
            {"body": offspring_body, "name": "AI Offspring", "color": "#FFD700"},
        ]
        out_fusion = f"outputs/visuals/{name_a}_x_{name_b}_fusion.html"
        generate_fusion_viewer(bodies_info, out_fusion)
        print(f"\n用瀏覽器打開 {out_fusion}")


if __name__ == "__main__":
    run()