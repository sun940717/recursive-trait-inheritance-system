# RTIS run: quadruped x jellyfish, seed 7

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
Unmatched in A: leg_front, leg_rear, neck_head, tail; unmatched in B: oral_arm, tentacle

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| bell | A.body, B.bell | 19% | (root) |
| neck_head | A.neck_head | 100% | bell |
| leg_front | A.leg_front | 100% | bell |
| leg_rear | A.leg_rear | 100% | bell |
| tentacle | B.tentacle | 0% | bell |
| oral_arm | B.oral_arm | 0% | bell |

- genes from A overall: 53%; from B: 47%
- not inherited (peripheral parts left out by chance): 1
- grafted: 0; lost to the site rule: 0; dropped orphans: 0
- crossed parts with new humps: 0 of 1

**Part-attribute layer (on) / 部位屬性層（開啟）**

- neck_head: own; reach beyond the surface 0.187, thickness 0.028 (body-size units)
- leg_front: own; reach beyond the surface 0.187, thickness 0.019 (body-size units)
- leg_rear: own; reach beyond the surface 0.186, thickness 0.021 (body-size units)
- tentacle: own; reach beyond the surface 0.535, thickness 0.013 (body-size units)
- oral_arm: own; reach beyond the surface 0.199, thickness 0.023 (body-size units)

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 41,936; volume: 0.6641; built in 2.5 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 6 parts, 104 nodes, 86 bones, 179 edges, 20,970 vertices; access: read_only
- groups: arrangement:mirror, arrangement:radial, arrangement:single, attached, root, tag:appendage, tag:central, tag:grasping, tag:head, tag:limb, tag:locomotion, tag:motor_organ, tag:secretion_organ, tag:sensor, tag:structural, tag:torso
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 3.3e-16); rest pose reproduces the mesh (largest error 3.3e-16)
- parts with vertices: 6 / 6; bones with vertices: 61 / 86
- turning only neck_head.b0: 91.1% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 20 bones
- demo pose: volume change -0.0%, flipped faces 1.13%
- result: PASS

## Result / 結果

**PASS** in 21 s. Output folder: `out_attr/quadruped_x_jellyfish_seed7_attr`
