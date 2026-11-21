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
| arm_front | A.arm_front | 100% | bell |
| horn | A.horn | 100% | neck_head |
| tentacle | B.tentacle | 0% | bell |
| oral_arm | B.oral_arm | 0% | bell |

- genes from A overall: 57%; from B: 43%
- not inherited (peripheral parts left out by chance): 1
- grafted: 0; lost to the site rule: 0; dropped orphans: 0
- crossed parts with new humps: 0 of 1

**Part-attribute layer (on) / 部位屬性層（開啟）**

- neck_head: own; reach beyond the surface 0.197, thickness 0.026 (body-size units)
- leg_rear: own; reach beyond the surface 0.290, thickness 0.027 (body-size units)
- arm_front: own; reach beyond the surface 0.073, thickness 0.012 (body-size units)
- horn: own; reach beyond the surface 0.056, thickness 0.007 (body-size units)
- tentacle: own; reach beyond the surface 0.535, thickness 0.013 (body-size units)
- oral_arm: own; reach beyond the surface 0.199, thickness 0.023 (body-size units)

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 41,440; volume: 0.6659; built in 2.6 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 7 parts, 110 nodes, 90 bones, 188 edges, 20,722 vertices; access: read_only
- groups: arrangement:mirror, arrangement:radial, arrangement:single, attached, root, tag:appendage, tag:central, tag:cutting, tag:defense_organ, tag:end_effector, tag:grasping, tag:head, tag:limb, tag:locomotion, tag:motor_organ, tag:secretion_organ, tag:sensor, tag:structural, tag:torso, tag:weapon_part
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 3.3e-16); rest pose reproduces the mesh (largest error 2.2e-16)
- parts with vertices: 7 / 7; bones with vertices: 67 / 90
- turning only neck_head.b0: 86.2% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 18 bones
- demo pose: volume change -0.4%, flipped faces 1.16%
- result: FAIL: turning one part moves mostly that part (> 90%)

## Result / 結果

**FAIL** in 21 s. Output folder: `out_attr/biped_x_jellyfish_seed7_attr`
