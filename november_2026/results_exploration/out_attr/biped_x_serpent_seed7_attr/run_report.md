# RTIS run: biped x serpent, seed 7

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
**B: serpent** (4 parts, 59 genes)
```
torso          single  14 bones   tags torso, structural, central
head           single  3 bones   tags head, sensor
fang           mirror  2 bones   tags weapon_part, cutting, grasping
tail_tip       single  3 bones   tags tail, motor_organ
```
Tags not in ontology.py: none

## 2. Matching / 配對

| A | B | PCE score | how |
|---|---|---|---|
| body | torso | 1.000 | root |
| neck_head | head | 1.000 | clear |
| horn | fang | 0.600 | clear |
| tail | tail_tip | 0.500 | clear |

No borderline pairs for these parents. / 這對親代沒有邊界配對。
Unmatched in A: arm_front, leg_rear; unmatched in B: none

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| torso | A.body, B.torso | 20% | (root) |
| head | A.neck_head, B.head | 68% | torso |
| tail | A.tail, B.tail_tip | 37% | torso |
| arm_front | A.arm_front | 100% | torso |
| fang | A.horn, B.fang | 62% | head |

- genes from A overall: 48%; from B: 52%
- not inherited (peripheral parts left out by chance): 1
- grafted: 0; lost to the site rule: 0; dropped orphans: 0
- crossed parts with new humps: 2 of 4

**Part-attribute layer (on) / 部位屬性層（開啟）**

- tail: length B, thickness B, taper A, bend B; reach beyond the surface 0.112, thickness 0.007 (body-size units)
- arm_front: own; reach beyond the surface 0.073, thickness 0.012 (body-size units)
- fang: length A, thickness A, taper B, bend B; reach beyond the surface 0.056, thickness 0.007 (body-size units)
- A.neck_head~B.head: kept the existing rules (long x round; long x round is on the to-do list)

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 17,024; volume: 0.1384; built in 1.6 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 5 parts, 45 nodes, 38 bones, 53 edges, 8,514 vertices; access: read_only
- groups: arrangement:mirror, arrangement:single, attached, root, tag:central, tag:cutting, tag:end_effector, tag:grasping, tag:head, tag:limb, tag:sensor, tag:structural, tag:tail, tag:torso, tag:weapon_part
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 3.3e-16); rest pose reproduces the mesh (largest error 4.4e-16)
- parts with vertices: 5 / 5; bones with vertices: 38 / 38
- turning only head.b0: 99.4% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 8 bones
- demo pose: volume change -0.2%, flipped faces 0.20%
- result: PASS

## Result / 結果

**PASS** in 11 s. Output folder: `out_attr/biped_x_serpent_seed7_attr`
