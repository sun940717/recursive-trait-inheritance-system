import json
import os
from trait import Trait, BodyGraph
from genome import Genome, GeneModule
from pce import get_all_traits

TAG_3D = {
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

DEFAULT_3D = {"shape": "sphere", "radius": 0.3, "color": "#BDC3C7"}


def get_3d_props(trait: Trait) -> dict:
    for tag in trait.semantic_tags:
        if tag in TAG_3D:
            return TAG_3D[tag]
    return DEFAULT_3D


def body_to_3d_json(body: BodyGraph) -> dict:
    nodes = []
    edges = []

    def process(trait: Trait, parent_pos: list, depth: int, sibling_idx: int, total_siblings: int):
        import math
        angle = (2 * math.pi * sibling_idx / max(total_siblings, 1))
        spread = 2.5
        x = parent_pos[0] + spread * math.cos(angle) if depth > 0 else 0
        y = parent_pos[1] - 2.5
        z = parent_pos[2] + spread * math.sin(angle) if depth > 0 else 0

        pos = [round(x, 2), round(y, 2), round(z, 2)]
        props = get_3d_props(trait)

        idx = len(nodes)
        nodes.append({
            "id": idx,
            "name": trait.name,
            "tags": trait.semantic_tags,
            "position": pos,
            **props
        })

        for i, child in enumerate(trait.children):
            child_idx = len(nodes)
            process(child, pos, depth + 1, i, len(trait.children))
            edges.append({"from": idx, "to": child_idx})

    for i, root in enumerate(body.nodes):
        root_pos = [i * 6, 0, 0]
        process(root, root_pos, 0, i, len(body.nodes))

    return {"nodes": nodes, "edges": edges}


def generate_viewer(body: BodyGraph, filename: str = "outputs/visuals/viewer_3d.html"):
    data = body_to_3d_json(body)
    json_str = json.dumps(data)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>RTIS 3D Viewer</title>
<style>
  body {{ margin: 0; background: #0d0d1a; overflow: hidden; }}
  #info {{ position: absolute; top: 16px; left: 16px; color: #aaa; font-family: Arial; font-size: 13px; pointer-events: none; }}
  #info h3 {{ color: white; margin: 0 0 6px; font-size: 15px; }}
  #legend {{ position: absolute; bottom: 16px; left: 16px; color: #aaa; font-family: Arial; font-size: 11px; }}
  .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }}
</style>
</head>
<body>
<div id="info">
  <h3>RTIS 3D Body Viewer</h3>
  <div>節點數：{len(data['nodes'])}</div>
  <div>連線數：{len(data['edges'])}</div>
  <div style="margin-top:8px;color:#555">滑鼠拖曳旋轉 · 滾輪縮放</div>
</div>
<div id="legend">
  <span class="dot" style="background:#9B59B6"></span>central &nbsp;
  <span class="dot" style="background:#4A9EDB"></span>sensor &nbsp;
  <span class="dot" style="background:#E74C3C"></span>grasping &nbsp;
  <span class="dot" style="background:#95A5A6"></span>structural &nbsp;
  <span class="dot" style="background:#F39C12"></span>locomotion
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
const DATA = {json_str};

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, window.innerWidth/window.innerHeight, 0.1, 1000);
camera.position.set(0, 0, 30);

const renderer = new THREE.WebGLRenderer({{antialias: true}});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setClearColor(0x0d0d1a);
document.body.appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const dir = new THREE.DirectionalLight(0xffffff, 1.0);
dir.position.set(10, 20, 10);
scene.add(dir);
const dir2 = new THREE.DirectionalLight(0x8888ff, 0.3);
dir2.position.set(-10, -5, -10);
scene.add(dir2);

// 全部放進 group，旋轉時連線也一起動
const group = new THREE.Group();
scene.add(group);

// 計算中心點，置中
const cx = DATA.nodes.reduce((s,n) => s+n.position[0], 0) / DATA.nodes.length;
const cy = DATA.nodes.reduce((s,n) => s+n.position[1], 0) / DATA.nodes.length;
const cz = DATA.nodes.reduce((s,n) => s+n.position[2], 0) / DATA.nodes.length;

DATA.nodes.forEach(node => {{
  let geo;
  const color = parseInt(node.color.replace('#',''), 16);
  const mat = new THREE.MeshPhongMaterial({{color, shininess: 100, specular: 0x333333}});

  if (node.shape === 'sphere') {{
    geo = new THREE.SphereGeometry(node.radius || 0.5, 24, 24);
  }} else if (node.shape === 'box') {{
    const s = node.size || [1,1,1];
    geo = new THREE.BoxGeometry(s[0], s[1], s[2]);
  }} else if (node.shape === 'cylinder') {{
    geo = new THREE.CylinderGeometry(node.radius||0.3, node.radius||0.3, node.height||1, 16);
  }} else if (node.shape === 'cone') {{
    geo = new THREE.ConeGeometry(node.radius||0.3, node.height||1, 16);
  }} else {{
    geo = new THREE.SphereGeometry(0.3, 8, 8);
  }}

  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(node.position[0]-cx, node.position[1]-cy, node.position[2]-cz);
  group.add(mesh);
}});

DATA.edges.forEach(edge => {{
  const a = DATA.nodes[edge.from].position;
  const b = DATA.nodes[edge.to].position;
  const points = [
    new THREE.Vector3(a[0]-cx, a[1]-cy, a[2]-cz),
    new THREE.Vector3(b[0]-cx, b[1]-cy, b[2]-cz)
  ];
  const geo = new THREE.BufferGeometry().setFromPoints(points);
  const mat = new THREE.LineBasicMaterial({{color: 0x556688}});
  group.add(new THREE.Line(geo, mat));
}});

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
  camera.position.z = Math.max(5, Math.min(80, camera.position.z + e.deltaY * 0.04));
}});
window.addEventListener('resize', () => {{
  camera.aspect = window.innerWidth/window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}});

function animate() {{
  requestAnimationFrame(animate);
  if (autoRotate) group.rotation.y += 0.003;
  renderer.render(scene, camera);
}}
animate();
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 已存到 {filename}")
    print("   用瀏覽器打開就能看到 3D 形體！")


if __name__ == "__main__":
    from evolution import mutate_genome
    from pruning import prune_body
    from pce import apply_trait
    import random
    from copy import deepcopy

    random.seed(42)

    genome = Genome(seed=42)
    genome.add_gene(GeneModule("sensor_node", ["sensor", "visual"], ["central"], 0.8))
    genome.add_gene(GeneModule("grasping_appendage", ["grasping", "end_effector"], ["structural"], 0.6))
    genome.add_gene(GeneModule("branch", ["structural"], ["structural"], 0.5))
    genome.add_gene(GeneModule("antenna", ["sensor", "receiver"], ["central"], 0.7))
    genome.add_gene(GeneModule("claw", ["grasping", "cutting"], ["structural"], 0.6))
    genome.add_gene(GeneModule("limb", ["structural", "locomotion"], ["structural"], 0.7))

    body = genome.develop()
    body = prune_body(body, max_traits=15)

    print(f"🧬 生成生物：{len(get_all_traits(body))} 個 trait")
    generate_viewer(body)
