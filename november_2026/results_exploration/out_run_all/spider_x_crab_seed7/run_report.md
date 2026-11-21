# RTIS run: spider x crab, seed 7

## 0. Environment / 環境

- python: `3.10.12`
- numpy: `2.2.6`
- platform: `Linux-6.18.44-fc-v470-x86_64-with-glibc2.39`
- pce.py: `/home/claude/rtis_real/pce.py`
- ontology.py: `/home/claude/rtis_real/ontology.py`

## 1. Parents / 親代

**A: spider** (7 parts, 81 genes)
```
cephalothorax  single  4 bones   tags torso, structural, central
abdomen        single  4 bones   tags structural, secretion_organ
fang           mirror  3 bones   tags weapon_part, cutting, grasping
leg_1          mirror  4 bones   tags limb, locomotion, motor_organ
leg_2          mirror  4 bones   tags limb, locomotion, motor_organ
leg_3          mirror  4 bones   tags limb, locomotion, motor_organ
leg_4          mirror  4 bones   tags limb, locomotion, motor_organ
```
**B: crab** (7 parts, 79 genes)
```
carapace       single  4 bones   tags torso, shell, defense_organ, central
claw           mirror  4 bones   tags limb, grasping, cutting, end_effector
leg_1          mirror  4 bones   tags limb, locomotion, motor_organ
leg_2          mirror  4 bones   tags limb, locomotion, motor_organ
leg_3          mirror  4 bones   tags limb, locomotion, motor_organ
leg_4          mirror  4 bones   tags limb, locomotion, motor_organ
eye_stalk      mirror  2 bones   tags sensory_cluster, sensor
```
Tags not in ontology.py: none

## 2. Matching / 配對

| A | B | PCE score | how |
|---|---|---|---|
| cephalothorax | carapace | 1.000 | root |
| leg_4 | leg_4 | 1.000 | clear |
| leg_3 | leg_3 | 1.000 | clear |
| leg_2 | leg_2 | 1.000 | clear |
| leg_1 | leg_1 | 1.000 | clear |

Borderline pairs (decided by chance in this mating) / 邊界配對：
- fang ~ claw: score 0.286, chance 24% -> not matched
Unmatched in A: abdomen, fang; unmatched in B: claw, eye_stalk

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| carapace | A.cephalothorax, B.carapace | 25% | (root) |
| abdomen | A.abdomen | 100% | carapace |
| fang | A.fang | 100% | carapace |
| leg_1 | A.leg_1, B.leg_1 | 50% | carapace |
| leg_2 | A.leg_2, B.leg_2 | 12% | carapace |
| leg_3 | A.leg_3, B.leg_3 | 19% | carapace |
| leg_4 | A.leg_4, B.leg_4 | 19% | carapace |
| claw | B.claw | 0% | carapace |
| eye_stalk | B.eye_stalk | 0% | carapace |

- genes from A overall: 36%; from B: 64%
- not inherited (peripheral parts left out by chance): 0
- grafted: 0; lost to the site rule: 0; dropped orphans: 0
- crossed parts with new humps: 0 of 5

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 34,456; volume: 0.3324; built in 1.7 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 9 parts, 74 nodes, 58 bones, 105 edges, 17,230 vertices; access: read_only
- groups: arrangement:mirror, arrangement:single, attached, root, tag:central, tag:cutting, tag:defense_organ, tag:end_effector, tag:grasping, tag:limb, tag:locomotion, tag:motor_organ, tag:secretion_organ, tag:sensor, tag:sensory_cluster, tag:shell, tag:structural, tag:torso, tag:weapon_part
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 4.4e-16); rest pose reproduces the mesh (largest error 3.3e-16)
- parts with vertices: 9 / 9; bones with vertices: 58 / 58
- turning only abdomen.b0: 97.4% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 40 bones
- demo pose: volume change -0.8%, flipped faces 1.44%
- result: PASS

## Result / 結果

**PASS** in 15 s. Output folder: `out_run_all/spider_x_crab_seed7`
