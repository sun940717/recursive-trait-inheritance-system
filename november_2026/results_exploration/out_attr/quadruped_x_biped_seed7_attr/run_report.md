# RTIS run: quadruped x biped, seed 7

## 0. Environment / 環境

- python: `3.10.12`
- numpy: `2.2.6`
- platform: `Linux-6.18.44-fc-v470-x86_64-with-glibc2.39`
- pce.py: `/home/claude/rtis_real/pce.py`
- ontology.py: `/home/claude/rtis_real/ontology.py`

## 1. Parents / 親代

**A: quadruped** (5 parts, 77 genes)
```
body           single  9 bones   tags torso, structural, central
neck_head      single  5 bones   tags head, sensor
tail           single  5 bones   tags tail, structural
leg_front      mirror  5 bones   tags limb, locomotion, motor_organ
leg_rear       mirror  5 bones   tags limb, locomotion, motor_organ
```
**B: biped** (6 parts, 85 genes)
```
body           single  9 bones   tags torso, structural, central
neck_head      single  5 bones   tags head, sensor
tail           single  5 bones   tags tail, structural
leg_rear       mirror  5 bones   tags limb, locomotion, motor_organ
arm_front      mirror  4 bones   tags limb, grasping, end_effector
horn           mirror  3 bones   tags weapon_part, cutting, defense_organ
```
Tags not in ontology.py: none

## 2. Matching / 配對

| A | B | PCE score | how |
|---|---|---|---|
| body | body | 1.000 | root |
| neck_head | neck_head | 1.000 | clear |
| tail | tail | 1.000 | clear |
| leg_rear | leg_rear | 1.000 | set |

Borderline pairs (decided by chance in this mating) / 邊界配對：
- leg_front ~ arm_front: score 0.333, chance 56% -> not matched
Unmatched in A: leg_front; unmatched in B: arm_front, horn

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| body | A.body, B.body | 13% | (root) |
| neck_head | A.neck_head, B.neck_head | 47% | body |
| tail | A.tail, B.tail | 37% | body |
| leg_rear | A.leg_rear, B.leg_rear | 89% | body |
| horn | B.horn | 0% | neck_head |

- genes from A overall: 37%; from B: 63%
- not inherited (peripheral parts left out by chance): 1
- grafted: 0; lost to the site rule: 0; dropped orphans: 0
- crossed parts with new humps: 0 of 4

**Part-attribute layer (on) / 部位屬性層（開啟）**

- limb set leg_front, leg_rear ~ leg_rear: count and placement from B (1 parts in the set), attributes from length B, thickness A, taper B, bend A
- neck_head: length A, thickness B, taper B, bend A; reach beyond the surface 0.187, thickness 0.026 (body-size units)
- tail: length B, thickness A, taper B, bend A; reach beyond the surface 0.319, thickness 0.017 (body-size units)
- leg_rear: length B, thickness A, taper B, bend A; reach beyond the surface 0.290, thickness 0.021 (body-size units)
- horn: own; reach beyond the surface 0.056, thickness 0.007 (body-size units)

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 26,040; volume: 0.2636; built in 2.7 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 5 parts, 42 nodes, 35 bones, 51 edges, 13,020 vertices; access: read_only
- groups: arrangement:mirror, arrangement:single, attached, root, tag:central, tag:cutting, tag:defense_organ, tag:head, tag:limb, tag:locomotion, tag:motor_organ, tag:sensor, tag:structural, tag:tail, tag:torso, tag:weapon_part
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 3.3e-16); rest pose reproduces the mesh (largest error 4.4e-16)
- parts with vertices: 5 / 5; bones with vertices: 35 / 35
- turning only neck_head.b0: 99.2% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 10 bones
- demo pose: volume change -0.1%, flipped faces 0.81%
- result: PASS

## Result / 結果

**PASS** in 18 s. Output folder: `out_attr/quadruped_x_biped_seed7_attr`
