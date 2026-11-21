# RTIS run: biped x jellyfish, seed 7

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
**B: jellyfish** (3 parts, 35 genes)
```
bell           single  4 bones   tags torso, structural, central
tentacle       radial  5 bones   tags appendage, grasping, motor_organ
oral_arm       radial  3 bones   tags appendage, grasping, secretion_organ
```
Tags not in ontology.py: none

## 2. Matching / 配對

| A | B | PCE score | how |
|---|---|---|---|
| body | bell | 1.000 | root |

No borderline pairs for these parents. / 這對親代沒有邊界配對。
Unmatched in A: arm_front, horn, leg_rear, neck_head, tail; unmatched in B: oral_arm, tentacle

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| bell | A.body, B.bell | 19% | (root) |
| neck_head | A.neck_head | 100% | bell |
| leg_rear | A.leg_rear | 100% | bell |
| horn | A.horn | 100% | neck_head |
| tentacle | B.tentacle | 0% | bell |

- genes from A overall: 58%; from B: 42%
- not inherited (peripheral parts left out by chance): 1
- grafted: 0; lost to the site rule: 2; dropped orphans: 0
- crossed parts with new humps: 0 of 1

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 36,680; volume: 0.6452; built in 2.4 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 5 parts, 84 nodes, 70 bones, 141 edges, 18,342 vertices; access: read_only
- groups: arrangement:mirror, arrangement:radial, arrangement:single, attached, root, tag:appendage, tag:central, tag:cutting, tag:defense_organ, tag:grasping, tag:head, tag:limb, tag:locomotion, tag:motor_organ, tag:sensor, tag:structural, tag:torso, tag:weapon_part
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 3.3e-16); rest pose reproduces the mesh (largest error 2.2e-16)
- parts with vertices: 5 / 5; bones with vertices: 52 / 70
- turning only neck_head.b0: 86.3% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 10 bones
- demo pose: volume change -0.2%, flipped faces 1.09%
- result: FAIL: turning one part moves mostly that part (> 90%)

## Result / 結果

**FAIL** in 18 s. Output folder: `out_run_all/biped_x_jellyfish_seed7`
