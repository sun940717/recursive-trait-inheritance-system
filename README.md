# Recursive Trait Inheritance System (RTIS)

**Author:** HongChenHe（洪晨和）  
**Updated:** 2026-11-22  
**Current version:** the November 2026 skeleton prototype (`november_2026/`)

RTIS breeds 3D creatures with **different body plans**. The current version stores each creature as a
**skeleton genome** (a list of parts, each a chain of bones with semantic tags) and grows every child into
**one closed mesh**, with every gene traceable to the parent it came from.

> **Claim (November version).** Two creatures with different body plans can mate; the child is one closed 3D
> body that carries parts and genes from both parents, and every gene can be traced to its source.

The sections after "Earlier design" describe the March 2026 v1 trait-graph system, kept as design history.

---

## Repository map

| Path | What |
|---|---|
| `november_2026/code/` | the current generator (frozen 2026-11-16): `skeleton_sdf_demo.py` (genome, distance field, meshing), `form_fusion_lab.py` (six forms, inheritance rules), `soft_match_lab.py` (probabilistic PCE matching), `rtis_run_once.py` (full pipeline once), `part_interface.py` (morphology package for animation), replay tools, and the labs used while designing the rules |
| `november_2026/experiments/` | the formal experiments of plan v1: `metrics_v1.py`, `run_v1.py`, `precheck_v1.py`, `analyze_v1.py`, `x4_timing_v1.py`, `gallery_v1.py`, `make_replays_v1.py`, `x3_generations_v1.py`; `code_freeze_v1.json` (SHA-256 of every frozen file) |
| `november_2026/experiments/data/` | `X1.csv` (7,650 children), `X2.csv` (9,180), manifests, per-child detail (`*_detail.jsonl`) |
| `november_2026/experiments/results/` | analysis (`analysis_v1.md/.json`), build time (`x4_timing_v1`), X3 feasibility trial (`x3_trial/`, 1 population, not a result) |
| `november_2026/experiments/gallery/gallery_v1.png` | all 30 seed-7 children (15 pairs × both directions), not selected |
| `november_2026/experiments/replays/*.html` | six step-by-step replay pages; open in a browser |
| `november_2026/results_exploration/` | raw outputs of the November design experiments (before plan v1; small test sets, see the data table for their reliability) |
| `november_2026/docs/` | Chinese documents: system description, design plans, experiment plans v0/v1, results, data table, experiment log, paper outline, future directions |
| `docs_project/` | Chinese project-wide documents: history and records of every version, open items, status overview, description of v1 and RTISV2 |
| `rtis/` | `pce.py`, `ontology.py`, `trait.py` (May 2026 versions) used by the November generator |
| `prototype/`, `spec/`, `schema/`, `examples/` | the March 2026 v1 prototype and specification (design history) |

## How the November version makes a child

1. two parent genomes with three-layer ontology tags (cell / organ / part);
2. **PCE matching**: weighted Jaccard of tags (0.5 / 1 / 2); ≥ 0.40 always matches, 0.25–0.40 matches with probability (s − 0.25) / 0.15, below 0.25 never;
3. every gene of a matched part comes whole from one parent, with **linkage** (one switch point per chain);
4. **relative genes**; 5. **grafting** of unmatched parts; 6. **site rule**;
7. round-cone signed distance per bone → smooth union → Fourier cross-section detail → marching cubes → one closed mesh;
8. morphology package (mesh, parts, bones, skin weights, lineage) for a motion system.

No machine learning, no LLM, no physics simulation in the generator.

## Results (experiment plan v1, frozen 2026-11-16)

Six hand-written forms (quadruped, biped, spider, serpent, jellyfish, crab), 15 pairs, both directions, 51 seeds.
"Passing" = one closed manifold shell, no buried part, no hidden part (geometry only).

| | Result |
|---|---|
| **PCE vs random matching with the same number of pairs** | pass 78.4% vs 70.9%, **+7.5 percentage points** (95% CI +5.6 to +9.4, sign-flip p < 0.0001) |
| Parts kept | 79.6% vs 80.1% (−0.5 pp, within the pre-set 5 pp rule) |
| Closed single shell | 99.9% |
| Both parents contribute | 97.1% of children get ≥ 10% of their genes from each parent |
| Ablations | relative genes off (linkage also off): bend +157.9°; linkage off: humps +0.86; site rule off: pass 65.2%; strict matching: no difference detected; attribute layer on: pass 91.6% |
| Jellyfish pairs | 51.2% (PCE matches no non-root part, K = 0); 82.4% with the attribute layer |
| Build time (Windows) | median 0.93 s per child at grid 0.03 |
| Gallery (seed 7, all 30) | 23 / 30 pass the full pipeline including the motion test |

The analysis was recomputed with independently written code; all numbers agreed.
Details: `november_2026/docs/RTIS_實驗結果_v1.md` and `RTIS_數據總表.md`.

**Limits.** Six hand-written forms only; the X1/X2 pass rate does not include the motion test; K = 0 for
38.7% of children; the site rule is partly circular with the buried-part check; the attribute layer is off
by default; no human evaluation, no external baseline. X3 (multi-generation) has only a feasibility trial.

## Run it

Python 3.10.12 with numpy 2.2.6, scipy 1.15.3, scikit-image 0.25.2, matplotlib 3.10.9 (the data environment).

```
cd november_2026/experiments
python precheck_v1.py              # pre-checks
python run_v1.py --exp both        # X1, X2 (about 17k children; --workers N)
python analyze_v1.py
cd ../code
PYTHONPATH=../../rtis python rtis_run_once.py --a biped --b spider --seed 7      # Windows: $env:PYTHONPATH="..\..\rtis"
```

## Version history (short)

| When | Version | What happened |
|---|---|---|
| 2026-03 | v1 | trait graphs, PCE, LLM-guided mutation (below) |
| 2026-05 | RTISV2 | controlled experiment on trait graphs (n = 30) |
| 2026-06 | mesh hybrids | direct mixing of external meshes; parts were lost, dropped |
| 2026-11 | Fourier tubes → skeleton + implicit surface | current version; formal experiments v1 |

Full history: `docs_project/RTIS_專案歷程與紀錄.md`.

---

# Earlier design: v1 (March 2026)

## Overview

RTIS (Recursive Trait Inheritance System) is an **AI-driven biological morphology generation and evolution framework**. It constructs virtual organisms through a layered generative architecture — from genetic encoding to 3D rendering — with LLM-guided mutation and semantic trait inheritance at its core.

> *"A biological body is not a fixed structure — it is a temporary expression of a trait relationship network."*

RTIS is not just a character generator or a procedural modeling tool. It is a **Generative Life System**, applicable to games, generative art, artificial life research, and simulation.

---

## Core Principles

- **Everything is a Trait** — organisms are directed graphs of traits, not fixed skeletons
- **Recursive Attachment** — any trait can attach to any other trait, with no mandatory anatomical hierarchy
- **Semantic Matching** — the Part Correspondence Engine (PCE) uses Jaccard similarity to match traits across organisms, enabling cross-species inheritance
- **LLM-Guided Mutation** — Claude decides mutation content, morphology values, and heritability
- **Emergent Morphology** — cell-level parameter combinations spontaneously produce undesigned structural outputs (see: 佛光 Buddha Light)
- **Evolution as Drift** — evolution is continuous directional drift, not convergence toward a fixed goal

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│  Layer 5: Render Layer                              │
│  Three.js → Interactive 3D HTML Viewer              │
├─────────────────────────────────────────────────────┤
│  Layer 4: Morphology Layer                          │
│  trait.morphology → shape / scale / color / emissive│
├─────────────────────────────────────────────────────┤
│  Layer 3: Semantic / Ontology Layer                 │
│  Hierarchical tag system: cell / organ / part / ... │
├─────────────────────────────────────────────────────┤
│  Layer 2: Structure Layer                           │
│  Trait + BodyGraph → directed node-relationship graph│
├─────────────────────────────────────────────────────┤
│  Layer 1.5: Cell Recipe Layer                       │
│  CellRecipe → cell ratio sampling → tissue properties│
├─────────────────────────────────────────────────────┤
│  Layer 1: Genetic Layer                             │
│  Genome + GeneModule → developmental rules          │
├─────────────────────────────────────────────────────┤
│  Layer 0: Input Layer                               │
│  .obj / .glb / Preset / Text Description            │
└─────────────────────────────────────────────────────┘
```

Data flow: Input → Genetic → Cell Recipe → Structure → Semantic → Morphology → Render

---

## Key Components

### Part Correspondence Engine (PCE)
Cross-organism trait matching via Jaccard semantic similarity. Enables structurally different organisms to exchange traits at semantically compatible attachment points.

```
Organism A: fang [grasping, cutting]
    ↕ Jaccard similarity
Organism B: tentacle [grasping, end_effector]
→ Matched — trait inherits to corresponding position
```

**Hierarchical fallback:** When similarity is zero, PCE retreats from `part → organ → cell` level to find a valid match.

### Cell Recipe System (Layer 1.5)
Seven cell types parametrically sample tissue properties during each `develop()` call, producing stochastic morphological variation:

| Cell Type | Contribution | Visual Hint |
|-----------|-------------|-------------|
| structural_cell | density↑, rigidity↑ | rigid dense matrix |
| motor_cell | flexibility↑ | flexible muscular tissue |
| sensory_cell | conductivity↑ | translucent neural network |
| armor_cell | hardness↑ | plated chitinous surface |
| secretory_cell | flexibility↑ | glandular moist surface |
| neural_cell | conductivity↑↑ | glowing electrically active |
| energy_cell | emissive↑ | bioluminescent pulsing |

### LLM-Guided Mutation
Claude (claude-sonnet) decides mutation outcomes during organism fusion:

- **95%** micro-mutation: scale / color micro-adjustment
- **15%** medium-mutation: add or remove a trait
- **3%** major-mutation: entirely new trait type

Every mutation is tagged `heritable: true/false`. Heritable mutations are written back to the Genome and passed to future generations.

### Procedural Geometry
Four geometry types auto-triggered by semantic tag + morphology value combinations:

- `claw` — branching tip structure (grasping + sharpness > 0.5)
- `glow_orb` — sphere with tilted halo rings (sensor + emissive > 0.3)
- `fin` — wave-form fin surface (locomotion + rigidity < 0.4)
- `blade` — trapezoidal blade shape (cutting + sharpness > 0.7)

---

## Organism Registry

### Base Forms
| Name | Seed | Key Genes |
|------|------|-----------|
| Spider | 42 | body, fang, eye, leg |
| Jellyfish | 99 | bell, tentacle, fin, sensor_tip |
| Crab | 77 | carapace, claw, leg, eye_stalk |
| Serpent | 55 | head, body_segment, fang, tongue |

### Limited Special Forms
| Name | Seed | Origin |
|------|------|--------|
| SpiderJelly Prime | 12345 | Spider × Jellyfish mix() |
| 佛光 Buddha Light | 888 | Jellyfish emergent mutation |

**佛光 (Buddha Light):** When `energy_cell` ratio lands in `(0.25, 0.45)` during Jellyfish development, Shap-E spontaneously generates a floating halo structure — not manually designed. This emergent output cannot be reproduced by directly prompting for a halo; it only arises from specific cell recipe parameter combinations. This is the system's most significant emergent morphology case study.

---

## Web Interface

Flask-based web interface (`app.py`) with full AI fusion pipeline:

- Drag-and-drop `.obj` / `.glb` upload with automatic Claude trait recognition
- Four preset organism selectors (Spider / Jellyfish / Crab / Serpent)
- Three-panel 3D viewer: Parent A | Parent B | ★ AI Offspring
- Right-side mutation report (micro / medium / major, with heritability flags)
- Multi-generation breeding pool: offspring can be added as parents for Gen 2+
- "🧬 Generate Colab Prompt" — copies Shap-E generation code for Google Colab

**Known active bugs:**
- Three-model viewer centering offset
- Offspring label position offset (partially fixed)

---

## Dialectic Engine

A separate Flask web application (`localhost:5050`) featuring:

- Dual AI agents (Alpha / Beta) in structured debate
- 6 discussion modes, 8 assignable roles
- Fact-checker, user interjection, unlimited rounds
- Markdown export
- ~$0.038 per debate round (Anthropic API)

Runs via Flask proxy due to CORS restrictions on direct API calls from browser context.

---

## Mesh Generation

Two parallel generation routes:

**Route A — BaseMesh Morphing (Primary)**  
Template vertex displacement of `FinalBaseMesh.obj` driven by cell recipe tissue properties. Always produces a connected mesh; style-consistent.

**Route B — Shap-E (Auxiliary)**  
Full organism generation from cell recipe prompt. Higher freedom, longer generation time, occasional instability.

- Local: `D:\rtis_env\` (RTX 4050 Laptop, 6GB VRAM, CUDA 12.4)
- Recommended: Google Colab T4 GPU (better quality, no local VRAM pressure)

**Prompt engineering rules:**
- Avoid: `mesh`, `lattice`, `network`, `translucent`, `crystal`
- Prefer: `smooth`, `solid`, `organic`, `rounded`, `curved`

---

## Experiments

**PCE vs No-PCE** — 10 seeds × 10 generations, Spider + Jellyfish parents:

| Metric | PCE | No-PCE |
|--------|-----|--------|
| Final trait count (Gen 10) | 23.6 ±3.4 | 12.4 ±high |
| Diversity std dev | ±0.026~0.122 (stable) | ±0.182~0.291 (volatile) |
| PCE match rate | 100% | N/A |

**Key finding:** PCE produces stable, predictable diversity. No-PCE produces high variance with lower trait accumulation.

---

## Repository Structure

```
D:\ai-research-lab\
├── rtis\
│   ├── trait.py              ← Trait + BodyGraph core data structure
│   ├── genome.py             ← Genome + GeneModule + develop()
│   ├── cell_recipe.py        ← Layer 1.5 cell recipe system
│   ├── ontology.py           ← 3-layer semantic tag system (extensible)
│   ├── pce.py                ← Part Correspondence Engine (Jaccard)
│   ├── evolution.py          ← mutate_genome
│   ├── metrics.py            ← diversity / depth / PCE match rate
│   ├── pruning.py            ← rarity-based trait pruning
│   ├── experiment.py         ← PCE vs no-PCE experiment runner
│   ├── visualize.py          ← 2D SVG evolution strip
│   ├── body3d.py             ← Single-organism 3D viewer
│   ├── fusion3d.py           ← Multi-organism fusion 3D viewer
│   ├── ai_mutation.py        ← Claude-driven mutation system
│   ├── model_parser.py       ← External model (.obj/.glb) trait recognition
│   ├── mesh_generator.py     ← Cell recipe → prompt → Shap-E → .obj
│   ├── morph_engine.py       ← BaseMesh vertex displacement engine
│   ├── generate_creature.py  ← Genome → full creature → Shap-E
│   ├── app.py                ← Flask web interface (main entry point)
│   └── outputs\
│       ├── visuals\          ← Generated 3D HTML viewers
│       ├── mutations\        ← AI mutation record JSON
│       └── parsed_models\    ← Model recognition result JSON
├── outputs\
│   └── paper\
│       └── RTIS_full_draft_v2.md   ← Full paper draft (latest)
├── search_agent.py           ← ArXiv search + Claude summary
├── critic_agent.py           ← Paper review agent (auto-versioned)
└── writer_agent.py           ← Paper section generation agent
```

---

## Research Contributions (CoG 2026)

1. **Trait-based encoding** — Genetic units without fixed anatomical structure; any trait attaches to any trait
2. **PCE semantic matching** — Jaccard + Top-K cross-organism trait correspondence with hierarchical fallback
3. **PCE vs Random experiment** — 10 seeds × 10 generations with standard deviation comparison
4. **Cell-level emergent morphology** — Spontaneous structural emergence from parameter combinations, without explicit design; documented in the 佛光 (Buddha Light) case study

---

## Paper Status

| Section | Status |
|---------|--------|
| Abstract | ✅ Complete |
| Introduction | ✅ Complete |
| Related Work | ✅ Complete (some citation placeholders remain) |
| System Architecture | ✅ Complete |
| PCE | ✅ Complete |
| Experiments | ✅ Complete |
| Discussion | ✅ Complete (includes Buddha Light emergent morphology) |

**Pending:** Fill real citations in Related Work · Convert to LaTeX · Statistical significance (t-test)  
**Critic score:** 3/10 (Strong Reject) — main issues: small experiment scale, no statistical significance tests, PCE 100% match rate needs fallback explanation

---

## Quick Start

```powershell
# Web interface (standard Python environment)
cd D:\ai-research-lab\rtis
python app.py
# → Open browser at localhost:5000

# Shap-E mesh generation (GPU environment)
D:\rtis_env\Scripts\Activate.ps1
cd D:\ai-research-lab\rtis
python mesh_generator.py        # single trait mesh
python generate_creature.py     # full organism

# PCE vs No-PCE experiment
python experiment.py
# → outputs/pce_vs_nopce_with_sd.md

# Dialectic Engine
python dialectic_app.py
# → Open browser at localhost:5050
```

---

## Environment

```
OS:     Windows 10 (26200.8037)
Python: 3.11.9

Standard env:  C:\Users\sun94\AppData\Local\Programs\Python\Python311\
GPU env:       D:\rtis_env\
  PyTorch:     2.6.0+cu124
  Shap-E, trimesh 4.11.5, anthropic 0.86.0

GPU:    NVIDIA GeForce RTX 4050 Laptop (6GB VRAM, CUDA 12.7)
Colab:  T4 GPU (recommended for Shap-E generation)
API:    .env in D:\ai-research-lab\
```

---

## Future Directions

**Planned:**
- Multi-generation lineage tree visualization (route `/generation_tree` exists, frontend pending)
- Game stat layer (strength / mana / vitality / elemental affinity)
- Skill fusion system demo (trait = skill attribute, PCE produces new skills)
- Statistical significance analysis (t-test) for PCE experiment

**Long-term:**
- Stable Diffusion integration (BodyGraph → 2D character sprite)
- Blender Python API integration (3D model export)
- TripoSG as Shap-E replacement (higher quality mesh generation)
- Inheritance fidelity system: Skeleton Lock + Morphology Blend Inheritance + Mutation Budget

---

## License

MIT License
