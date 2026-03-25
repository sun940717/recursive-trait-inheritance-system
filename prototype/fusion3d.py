import json
import os
import random
from copy import deepcopy
from trait import Trait, BodyGraph
from genome import Genome, GeneModule
from pce import get_all_traits, apply_trait
from pruning import prune_body
from body3d import body_to_3d_json

PRESET_ORGANISMS = {
    "1": {
        "name": "Spider",
        "genes": [
            GeneModule("body", ["central", "structural"], ["central"], 1.0),
            GeneModule("leg", ["structural", "locomotion"], ["structural"], 0.9),
            GeneModule("fang", ["grasping", "cutting"], ["structural"], 0.8),
            GeneModule("eye", ["sensor", "visual"], ["central"], 0.9),
        ],
        "seed": 42
    },
    "2": {
        "name": "Jellyfish",
        "genes": [
            GeneModule("bell", ["central", "structural"], ["central"], 1.0),
            GeneModule("tentacle", ["grasping", "end_effector"], ["structural"], 0.9),
            GeneModule("sensor_tip", ["sensor", "receiver"], ["end_effector"], 0.7),
            GeneModule("fin", ["structural", "locomotion"], ["structural"], 0.6),
        ],
        "seed": 99
    },
    "3": {
        "name": "Crab",
        "genes": [
            GeneModule("carapace", ["central", "structural"], ["central"], 1.0),
            GeneModule("claw", ["grasping", "cutting"], ["structural"], 0.9),
            GeneModule("leg", ["structural", "locomotion"], ["structural"], 0.8),
            GeneModule("eye_stalk", ["sensor", "visual"], ["central"], 0.8),
        ],
        "seed": 77
    },
    "4": {
        "name": "Serpent",
        "genes": [
            GeneModule("head", ["central", "sensor"], ["central"], 1.0),
            GeneModule("body_segment", ["structural", "locomotion"], ["structural"], 0.9),
            GeneModule("tongue", ["sensor", "receiver"], ["central"], 0.8),
            GeneModule("tail_blade", ["cutting", "end_effector"], ["structural"], 0.7),
        ],
        "seed": 55
    },
}


def build_organism(preset: dict, randomize: bool = False) -> tuple:
    seed = random.randint(0, 99999) if randomize else preset["seed"]
    genome = Genome(seed=seed)
    for gene in preset["genes"]:
        g = deepcopy(gene)
        if randomize:
            g.probability = max(0.3, min(1.0, g.probability + random.uniform(-0.3, 0.3)))
        genome.add_gene(g)
    body = genome.develop()
    body = prune_body(body, max_traits=12)
    return body, genome


def fuse_organisms(bodies: list, genomes: list) -> tuple:
    fusion_seed = random.randint(0, 99999)
    random.seed(fusion_seed)

    child_genome = Genome(seed=fusion_seed)
    for genome in genomes:
        child_genome.add_gene(deepcopy(genome.gene_modules[0]))
        for gene in genome.gene_modules[1:]:
            if random.random() > random.uniform(0.1, 0.5):
                g = deepcopy(gene)
                g.probability = max(0.3, min(1.0, g.probability + random.uniform(-0.2, 0.2)))
                child_genome.add_gene(g)

    child_body = child_genome.develop()

    for body in bodies:
        traits = get_all_traits(body)
        inherit_count = random.randint(2, min(6, len(traits)))
        sampled = random.sample(traits, inherit_count)
        for trait in sampled:
            apply_trait(trait, child_body)

    child_body = prune_body(child_body, max_traits=20)
    return child_body, child_genome


def bodies_to_combined_json(bodies_info: list) -> dict:
    all_nodes, all_edges, all_groups = [], [], []
    spacing = 16
    for i, info in enumerate(bodies_info):
        offset_x = (i - len(bodies_info) / 2 + 0.5) * spacing
        data = body_to_3d_json(info["body"])
        node_offset = len(all_nodes)
        for node in data["nodes"]:
            n = dict(node)
            n["id"] = node["id"] + node_offset
            n["position"] = [node["position"][0] + offset_x, node["position"][1], node["position"][2]]
            n["group"] = i
            all_nodes.append(n)
        for edge in data["edges"]:
            all_edges.append({"from": edge["from"] + node_offset, "to": edge["to"] + node_offset, "group": i})
        all_groups.append({
            "index": i, "name": info["name"], "color": info["color"],
            "offset_x": offset_x, "node_count": len(data["nodes"])
        })
    return {"nodes": all_nodes, "edges": all_edges, "groups": all_groups}


def generate_fusion_viewer(bodies_info: list, filename: str = "outputs/visuals/fusion_3d.html"):
    data = bodies_to_combined_json(bodies_info)
    json_str = json.dumps(data)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>RTIS Fusion Viewer</title>
<style>
  body {{ margin: 0; background: #0d0d1a; overflow: hidden; font-family: Arial; }}
  #info {{ position: absolute; top: 16px; left: 16px; color: #aaa; font-size: 13px; pointer-events: none; }}
  #info h3 {{ color: white; margin: 0 0 8px; font-size: 16px; }}
  #labels {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }}
  #legend {{ position: absolute; bottom: 16px; left: 16px; color: #aaa; font-size: 11px; }}
  .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }}
</style>
</head>
<body>
<div id="info">
  <h3>RTIS Fusion 3D Viewer</h3>
  <div style="color:#555;margin-top:6px">滑鼠拖曳旋轉 · 滾輪縮放</div>
</div>
<div id="labels"></div>
<div id="legend">
  <span class="dot" style="background:#9B59B6"></span>central &nbsp;
  <span class="dot" style="background:#4A9EDB"></span>sensor &nbsp;
  <span class="dot" style="background:#E74C3C"></span>grasping &nbsp;
  <span class="dot" style="background:#95A5A6"></span>structural &nbsp;
  <span class="dot" style="background:#F39C12"></span>locomotion
</div>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script>
<script>
const DATA = {json_str};

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, window.innerWidth/window.innerHeight, 0.1, 1000);
camera.position.set(0, 0, 45);

const renderer = new THREE.WebGLRenderer({{antialias: true}});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setClearColor(0x0d0d1a);
document.body.appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const dir1 = new THREE.DirectionalLight(0xffffff, 1.0);
dir1.position.set(10, 20, 10);
scene.add(dir1);
const dir2 = new THREE.DirectionalLight(0x8888ff, 0.3);
dir2.position.set(-10, -5, -10);
scene.add(dir2);

const group = new THREE.Group();
scene.add(group);

const cx = DATA.nodes.reduce((s,n) => s+n.position[0], 0) / DATA.nodes.length;
const cy = DATA.nodes.reduce((s,n) => s+n.position[1], 0) / DATA.nodes.length;
const cz = DATA.nodes.reduce((s,n) => s+n.position[2], 0) / DATA.nodes.length;

DATA.nodes.forEach(node => {{
  let geo;
  const color = parseInt(node.color.replace('#',''), 16);
  const mat = new THREE.MeshPhongMaterial({{color, shininess: 100, specular: 0x333333}});
  if (node.shape === 'sphere') geo = new THREE.SphereGeometry(node.radius||0.5, 20, 20);
  else if (node.shape === 'box') {{ const s = node.size||[1,1,1]; geo = new THREE.BoxGeometry(s[0],s[1],s[2]); }}
  else if (node.shape === 'cylinder') geo = new THREE.CylinderGeometry(node.radius||0.3, node.radius||0.3, node.height||1, 14);
  else if (node.shape === 'cone') geo = new THREE.ConeGeometry(node.radius||0.3, node.height||1, 14);
  else geo = new THREE.SphereGeometry(0.3, 8, 8);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(node.position[0]-cx, node.position[1]-cy, node.position[2]-cz);
  group.add(mesh);
}});

DATA.edges.forEach(edge => {{
  const a = DATA.nodes[edge.from].position;
  const b = DATA.nodes[edge.to].position;
  const pts = [
    new THREE.Vector3(a[0]-cx, a[1]-cy, a[2]-cz),
    new THREE.Vector3(b[0]-cx, b[1]-cy, b[2]-cz)
  ];
  const isOffspring = edge.group === DATA.groups.length - 1;
  group.add(new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(pts),
    new THREE.LineBasicMaterial({{color: isOffspring ? 0x886644 : 0x334466}})
  ));
}});

DATA.groups.slice(0,-1).forEach(g => {{
  const x = g.offset_x + 8 - cx;
  group.add(new THREE.Line(
    new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(x,-15,0),
      new THREE.Vector3(x,8,0)
    ]),
    new THREE.LineBasicMaterial({{color: 0x223344}})
  ));
}});

function updateLabels() {{
  const w = renderer.domElement.clientWidth;
  const h = renderer.domElement.clientHeight;
  const container = document.getElementById('labels');
  container.innerHTML = '';
  DATA.groups.forEach(g => {{
    const isOffspring = g.index === DATA.groups.length - 1;
    const v = new THREE.Vector3(g.offset_x - cx, 6 - cy, 0 - cz);
    v.applyEuler(group.rotation);
    v.project(camera);
    const sx = (v.x + 1) / 2 * w;
    const sy = (-v.y + 1) / 2 * h;

    const label = document.createElement('div');
    label.style.cssText = `position:absolute;left:${{sx}}px;top:${{sy}}px;transform:translateX(-50%);
      color:${{g.color}};font-size:${{isOffspring?'18px':'15px'}};font-weight:${{isOffspring?'bold':'500'}};
      text-shadow:0 0 12px ${{g.color}}88;white-space:nowrap;`;
    label.textContent = isOffspring ? `★ ${{g.name}}` : g.name;
    container.appendChild(label);

    const sub = document.createElement('div');
    sub.style.cssText = `position:absolute;left:${{sx}}px;top:${{sy+22}}px;transform:translateX(-50%);
      color:#445566;font-size:11px;white-space:nowrap;`;
    sub.textContent = `${{g.node_count}} traits`;
    container.appendChild(sub);

    if (isOffspring) {{
      const badge = document.createElement('div');
      badge.style.cssText = `position:absolute;left:${{sx}}px;top:${{sy+40}}px;transform:translateX(-50%);
        color:#886644;font-size:10px;border:1px solid #886644;padding:1px 6px;border-radius:4px;white-space:nowrap;`;
      badge.textContent = 'PCE Fusion';
      container.appendChild(badge);
    }}
  }});
}}

let isDragging = false, prevX = 0, prevY = 0, autoRotate = true;
renderer.domElement.addEventListener('mousedown', e => {{ isDragging = true; autoRotate = false; prevX = e.clientX; prevY = e.clientY; }});
window.addEventListener('mouseup', () => isDragging = false);
window.addEventListener('mousemove', e => {{
  if (!isDragging) return;
  group.rotation.y += (e.clientX - prevX) * 0.008;
  group.rotation.x += (e.clientY - prevY) * 0.008;
  prevX = e.clientX; prevY = e.clientY;
}});
renderer.domElement.addEventListener('wheel', e => {{
  camera.position.z = Math.max(10, Math.min(120, camera.position.z + e.deltaY * 0.05));
}});
window.addEventListener('resize', () => {{
  camera.aspect = window.innerWidth/window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}});

function animate() {{
  requestAnimationFrame(animate);
  if (autoRotate) group.rotation.y += 0.002;
  renderer.render(scene, camera);
  updateLabels();
}}
animate();
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 已存到 {filename}")
    print("   用瀏覽器打開就能看到 3D 融合結果！")


def run():
    print("🧬 RTIS Fusion 3D")
    print("=" * 40)
    print("選擇要融合的生物（輸入數字，空格分隔）：")
    for k, v in PRESET_ORGANISMS.items():
        print(f"  {k}. {v['name']}")
    print()

    choices = input("例如輸入 '1 2' 融合 Spider + Jellyfish：").strip().split()
    if len(choices) < 2:
        print("請至少選2個")
        return

    selected = [PRESET_ORGANISMS[c] for c in choices if c in PRESET_ORGANISMS]
    if len(selected) < 2:
        print("有效選擇不足2個")
        return

    rand_input = input("要隨機化親代結構嗎？(y/n，預設n)：").strip().lower()
    randomize_parents = rand_input == 'y'

    colors = ["#4A9EDB", "#E74C3C", "#2ECC71", "#F39C12"]
    bodies_info, all_bodies, all_genomes = [], [], []

    for i, preset in enumerate(selected):
        body, genome = build_organism(preset, randomize=randomize_parents)
        all_bodies.append(body)
        all_genomes.append(genome)
        bodies_info.append({"body": body, "name": preset["name"], "color": colors[i % len(colors)]})
        print(f"✓ {preset['name']}: {len(get_all_traits(body))} traits")

    print("\n🔀 PCE 融合中...")
    child_body, child_genome = fuse_organisms(all_bodies, all_genomes)
    bodies_info.append({"body": child_body, "name": "Offspring", "color": "#FFD700"})
    print(f"✓ Offspring: {len(get_all_traits(child_body))} traits")

    generate_fusion_viewer(bodies_info)
    print("\n用瀏覽器打開 outputs/visuals/fusion_3d.html")


if __name__ == "__main__":
    run()
