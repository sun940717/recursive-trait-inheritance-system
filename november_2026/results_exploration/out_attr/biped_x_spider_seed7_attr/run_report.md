# RTIS run: biped x spider, seed 7

## 0. Environment / 環境

- python: `3.10.12`
- numpy: `2.2.6`
- platform: `Linux-6.18.44-fc-v470-x86_64-with-glibc2.39`
- pce.py: `/home/claude/rtis_real/pce.py`
- ontology.py: `/home/claude/rtis_real/ontology.py`

## 1. Parents / 親代

**A: biped** (6 parts, 85 genes)
```
body           single  9 bones   tags torso, structural, central
neck_head      single  5 bones   tags head, sensor
tail           single  5 bones   tags tail, structural
leg_rear       mirror  5 bones   tags limb, locomotion, motor_organ
arm_front      mirror  4 bones   tags limb, grasping, end_effector
horn           mirror  3 bones   tags weapon_part, cutting, defense_organ
```
**B: spider** (7 parts, 81 genes)
```
cephalothorax  single  4 bones   tags torso, structural, central
abdomen        single  4 bones   tags structural, secretion_organ
fang           mirror  3 bones   tags weapon_part, cutting, grasping
leg_1          mirror  4 bones   tags limb, locomotion, motor_organ
leg_2          mirror  4 bones   tags limb, locomotion, motor_organ
leg_3          mirror  4 bones   tags limb, locomotion, motor_organ
leg_4          mirror  4 bones   tags limb, locomotion, motor_organ
```
Tags not in ontology.py: none

## 2. Matching / 配對

| A | B | PCE score | how |
|---|---|---|---|
| body | cephalothorax | 1.000 | root |
| horn | fang | 0.600 | clear |
| leg_rear | leg_1 | 1.000 | set |
| leg_rear | leg_2 | 1.000 | set |
| leg_rear | leg_3 | 1.000 | set |
| leg_rear | leg_4 | 1.000 | set |

Borderline pairs (decided by chance in this mating) / 邊界配對：
- arm_front ~ leg_1: score 0.333, chance 56% -> not matched
- tail ~ abdomen: score 0.250, chance 0% -> not matched
Unmatched in A: arm_front, neck_head, tail; unmatched in B: abdomen

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| body | A.body, B.cephalothorax | 32% | (root) |
| neck_head | A.neck_head | 100% | body |
| leg_1 | A.leg_rear, B.leg_1 | 84% | body |
| leg_2 | B.leg_2 | 32% | body |
| leg_3 | B.leg_3 | 74% | body |
| leg_4 | B.leg_4 | 53% | body |
| arm_front | A.arm_front | 100% | body |
| horn | A.horn, B.fang | 62% | neck_head |
| abdomen | B.abdomen | 0% | body |

- genes from A overall: 58%; from B: 42%
- not inherited (peripheral parts left out by chance): 0
- grafted: 0; lost to the site rule: 1; dropped orphans: 0
- crossed parts with new humps: 1 of 6

**Part-attribute layer (on) / 部位屬性層（開啟）**

- limb set leg_rear ~ leg_1, leg_2, leg_3, leg_4: count and placement from B (4 parts in the set), attributes from length B, thickness A, taper B, bend A
- neck_head: own; reach beyond the surface 0.197, thickness 0.026 (body-size units)
- tail: own; reach beyond the surface 0.319, thickness 0.019 (body-size units)
- leg_1: length B, thickness A, taper B, bend A; reach beyond the surface 0.450, thickness 0.027 (body-size units)
- leg_2: length B, thickness A, taper B, bend A; reach beyond the surface 0.413, thickness 0.027 (body-size units)
- leg_3: length B, thickness A, taper B, bend A; reach beyond the surface 0.408, thickness 0.027 (body-size units)
- leg_4: length B, thickness A, taper B, bend A; reach beyond the surface 0.443, thickness 0.027 (body-size units)
- arm_front: own; reach beyond the surface 0.073, thickness 0.012 (body-size units)
- horn: length A, thickness B, taper B, bend A; reach beyond the surface 0.056, thickness 0.014 (body-size units)

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 22,440; volume: 0.1724; built in 1.2 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 9 parts, 87 nodes, 72 bones, 119 edges, 11,218 vertices; access: read_only
- groups: arrangement:mirror, arrangement:single, attached, root, tag:central, tag:cutting, tag:defense_organ, tag:end_effector, tag:grasping, tag:head, tag:limb, tag:locomotion, tag:motor_organ, tag:secretion_organ, tag:sensor, tag:structural, tag:torso, tag:weapon_part
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 3.3e-16); rest pose reproduces the mesh (largest error 2.2e-16)
- parts with vertices: 9 / 9; bones with vertices: 69 / 72
- turning only neck_head.b0: 99.6% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 48 bones
- demo pose: volume change -1.8%, flipped faces 0.95%
- result: PASS

## Result / 結果

**PASS** in 12 s. Output folder: `out_attr/biped_x_spider_seed7_attr`
