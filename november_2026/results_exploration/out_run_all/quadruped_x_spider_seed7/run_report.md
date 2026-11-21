# RTIS run: quadruped x spider, seed 7

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
| leg_rear | leg_4 | 1.000 | clear |
| leg_front | leg_1 | 1.000 | clear |

Borderline pairs (decided by chance in this mating) / 邊界配對：
- tail ~ abdomen: score 0.250, chance 0% -> not matched
Unmatched in A: neck_head, tail; unmatched in B: abdomen, fang, leg_2, leg_3

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| cephalothorax | A.body, B.cephalothorax | 13% | (root) |
| neck_head | A.neck_head | 100% | cephalothorax |
| leg_front | A.leg_front, B.leg_1 | 42% | cephalothorax |
| leg_4 | A.leg_rear, B.leg_4 | 11% | cephalothorax |
| abdomen | B.abdomen | 0% | cephalothorax |
| fang | B.fang | 0% | cephalothorax |
| leg_2 | B.leg_2 | 0% | cephalothorax |
| leg_3 | B.leg_3 | 0% | cephalothorax |

- genes from A overall: 22%; from B: 78%
- not inherited (peripheral parts left out by chance): 0
- grafted: 0; lost to the site rule: 1; dropped orphans: 0
- crossed parts with new humps: 0 of 3

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 18,592; volume: 0.1449; built in 0.8 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 8 parts, 73 nodes, 60 bones, 98 edges, 9,296 vertices; access: read_only
- groups: arrangement:mirror, arrangement:single, attached, root, tag:central, tag:cutting, tag:grasping, tag:head, tag:limb, tag:locomotion, tag:motor_organ, tag:secretion_organ, tag:sensor, tag:structural, tag:torso, tag:weapon_part
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 3.3e-16); rest pose reproduces the mesh (largest error 2.2e-16)
- parts with vertices: 8 / 8; bones with vertices: 58 / 60
- turning only neck_head.b0: 99.6% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 36 bones
- demo pose: volume change -1.0%, flipped faces 1.10%
- result: PASS

## Result / 結果

**PASS** in 8 s. Output folder: `out_run_all/quadruped_x_spider_seed7`
