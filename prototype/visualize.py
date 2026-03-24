import os
import math
from copy import deepcopy
from trait import Trait, BodyGraph
from genome import Genome, GeneModule
from pce import get_all_traits

TAG_SHAPES = {
    "sensor":       ("circle",   "#4A9EDB"),
    "visual":       ("circle",   "#2ECC71"),
    "grasping":     ("circle",   "#E74C3C"),
    "end_effector": ("diamond",  "#E67E22"),
    "structural":   ("rect",     "#95A5A6"),
    "central":      ("hexagon",  "#9B59B6"),
    "receiver":     ("circle",   "#1ABC9C"),
    "cutting":      ("triangle", "#C0392B"),
    "locomotion":   ("oval",     "#F39C12"),
}

def get_trait_appearance(trait):
    for tag in trait.semantic_tags:
        if tag in TAG_SHAPES:
            return TAG_SHAPES[tag]
    return ("circle", "#BDC3C7")

def trait_to_svg(trait, x, y, size=44):
    shape, color = get_trait_appearance(trait)
    label = trait.name[:8]
    cx, cy = x + size//2, y + size//2
    if shape == "circle":
        elem = f'<circle cx="{cx}" cy="{cy}" r="{size//2}" fill="{color}" opacity="0.85"/>'
    elif shape == "rect":
        elem = f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="4" fill="{color}" opacity="0.85"/>'
    elif shape == "diamond":
        pts = f"{cx},{y} {x+size},{cy} {cx},{y+size} {x},{cy}"
        elem = f'<polygon points="{pts}" fill="{color}" opacity="0.85"/>'
    elif shape == "triangle":
        pts = f"{cx},{y} {x+size},{y+size} {x},{y+size}"
        elem = f'<polygon points="{pts}" fill="{color}" opacity="0.85"/>'
    elif shape == "hexagon":
        r = size//2
        pts = " ".join([f"{cx+r*math.cos(math.radians(60*i)):.1f},{cy+r*math.sin(math.radians(60*i)):.1f}" for i in range(6)])
        elem = f'<polygon points="{pts}" fill="{color}" opacity="0.85"/>'
    elif shape == "oval":
        elem = f'<ellipse cx="{cx}" cy="{cy}" rx="{size//2}" ry="{size//3}" fill="{color}" opacity="0.85"/>'
    else:
        elem = f'<circle cx="{cx}" cy="{cy}" r="{size//2}" fill="{color}" opacity="0.85"/>'
    text = f'<text x="{cx}" y="{cy+4}" text-anchor="middle" font-size="8" fill="white" font-family="Arial">{label}</text>'
    return elem + "\n" + text

def body_to_svg(body, title="Organism"):
    all_traits = get_all_traits(body)
    n = len(all_traits)
    cols, size, gap = 5, 44, 12
    rows = (n + cols - 1) // cols
    w = cols * (size + gap) + gap
    h = rows * (size + gap) + gap + 50
    elems = [
        f'<rect width="{w}" height="{h}" fill="#1a1a2e" rx="8"/>',
        f'<text x="{w//2}" y="22" text-anchor="middle" font-size="13" fill="white" font-family="Arial" font-weight="bold">{title}</text>',
        f'<text x="{w//2}" y="38" text-anchor="middle" font-size="9" fill="#aaa" font-family="Arial">{n} traits</text>',
    ]
    for i, trait in enumerate(all_traits):
        col, row = i % cols, i // cols
        x = gap + col * (size + gap)
        y = 50 + gap + row * (size + gap)
        elems.append(trait_to_svg(trait, x, y, size))
    return f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">{"".join(elems)}</svg>'

def make_legend():
    items = [
        ("sensor/visual", "#4A9EDB", "circle"),
        ("grasping", "#E74C3C", "circle"),
        ("structural", "#95A5A6", "rect"),
        ("central", "#9B59B6", "hexagon"),
        ("end_effector", "#E67E22", "diamond"),
        ("locomotion", "#F39C12", "oval"),
        ("cutting", "#C0392B", "triangle"),
        ("receiver", "#1ABC9C", "circle"),
    ]
    svg = '<rect width="2200" height="40" fill="#13132a"/>\n'
    svg += '<text x="10" y="26" font-size="11" fill="#aaa" font-family="Arial">Legend:</text>\n'
    lx = 75
    for label, color, shape in items:
        if shape == "circle":
            svg += f'<circle cx="{lx+8}" cy="20" r="8" fill="{color}" opacity="0.85"/>\n'
        elif shape == "rect":
            svg += f'<rect x="{lx}" y="12" width="16" height="16" rx="3" fill="{color}" opacity="0.85"/>\n'
        elif shape == "hexagon":
            pts = " ".join([f"{lx+8+8*math.cos(math.radians(60*i)):.1f},{20+8*math.sin(math.radians(60*i)):.1f}" for i in range(6)])
            svg += f'<polygon points="{pts}" fill="{color}" opacity="0.85"/>\n'
        elif shape == "diamond":
            svg += f'<polygon points="{lx+8},12 {lx+16},20 {lx+8},28 {lx},20" fill="{color}" opacity="0.85"/>\n'
        elif shape == "triangle":
            svg += f'<polygon points="{lx+8},12 {lx+16},28 {lx},28" fill="{color}" opacity="0.85"/>\n'
        elif shape == "oval":
            svg += f'<ellipse cx="{lx+8}" cy="20" rx="10" ry="7" fill="{color}" opacity="0.85"/>\n'
        svg += f'<text x="{lx+22}" y="25" font-size="9" fill="#ccc" font-family="Arial">{label}</text>\n'
        lx += len(label) * 7 + 36
    return svg

def generate_evolution_strip(seed=42, generations=5):
    import random
    from pce import apply_trait
    from pruning import prune_body
    from evolution import mutate_genome

    random.seed(seed)

    genome_a = Genome(seed=seed)
    genome_a.add_gene(GeneModule("sensor_node", ["sensor", "visual"], ["central"], 0.8))
    genome_a.add_gene(GeneModule("grasping_appendage", ["grasping", "end_effector"], ["structural"], 0.6))
    genome_a.add_gene(GeneModule("branch", ["structural"], ["structural"], 0.5))
    genome_a.add_gene(GeneModule("antenna", ["sensor", "receiver"], ["central"], 0.7))
    genome_a.add_gene(GeneModule("claw", ["grasping", "cutting"], ["structural"], 0.6))

    genome_b = Genome(seed=seed+1)
    genome_b.add_gene(GeneModule("limb", ["structural", "locomotion"], ["structural"], 0.8))
    genome_b.add_gene(GeneModule("eye_cluster", ["sensor", "visual"], ["central"], 0.9))
    genome_b.add_gene(GeneModule("tendril", ["grasping", "end_effector"], ["structural"], 0.5))

    body_a = genome_a.develop()
    body_b = genome_b.develop()

    svgs = [body_to_svg(body_a, "Gen 0")]
    current_a = (body_a, genome_a)
    current_b = (body_b, genome_b)

    for gen in range(1, generations + 1):
        child_genome = Genome(seed=random.randint(0, 9999))
        for gene in current_a[1].gene_modules:
            if random.random() > 0.5:
                child_genome.add_gene(deepcopy(gene))
        for gene in current_b[1].gene_modules:
            if random.random() > 0.5:
                child_genome.add_gene(deepcopy(gene))
        if not child_genome.gene_modules:
            child_genome.add_gene(deepcopy(current_a[1].gene_modules[0]))
        child_genome = mutate_genome(child_genome)
        child_body = child_genome.develop()
        for trait in get_all_traits(current_a[0])[:3]:
            apply_trait(trait, child_body)
        child_body = prune_body(child_body, max_traits=20)
        svgs.append(body_to_svg(child_body, f"Gen {gen}"))
        current_a = (child_body, child_genome)

    # 組合最終 SVG
    legend_h = 40
    card_w, card_gap = 300, 25
    total_w = len(svgs) * (card_w + card_gap) + card_gap
    total_h = 450 + legend_h + 10

    defs = '<defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M2 1L8 5L2 9" fill="none" stroke="#555" stroke-width="1.5"/></marker></defs>'

    out = f'<svg width="{total_w}" height="{total_h}" xmlns="http://www.w3.org/2000/svg">\n'
    out += f'<rect width="{total_w}" height="{total_h}" fill="#0d0d1a"/>\n'
    out += defs + "\n"
    out += f'<g transform="translate(0,0)">{make_legend()}</g>\n'

    x = card_gap
    for i, svg in enumerate(svgs):
        out += f'<g transform="translate({x},{legend_h+10})">{svg}</g>\n'
        if i < len(svgs) - 1:
            ax1 = x + card_w + 2
            ax2 = ax1 + card_gap - 4
            ay = legend_h + 10 + 200
            out += f'<line x1="{ax1}" y1="{ay}" x2="{ax2}" y2="{ay}" stroke="#555" stroke-width="2" marker-end="url(#arr)"/>\n'
        x += card_w + card_gap

    out += '</svg>'

    os.makedirs("outputs/visuals", exist_ok=True)
    with open("outputs/visuals/evolution_strip.svg", "w") as f:
        f.write(out)
    print("✅ 已存到 outputs/visuals/evolution_strip.svg")

if __name__ == "__main__":
    print("🎨 RTIS 2D 視覺化")
    generate_evolution_strip(seed=42, generations=5)