# RTIS run: biped x crab, seed 7

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
| body | carapace | 1.000 | root |
| arm_front | claw | 0.800 | clear |
| leg_rear | leg_1 | 1.000 | set |
| leg_rear | leg_2 | 1.000 | set |
| leg_rear | leg_3 | 1.000 | set |
| leg_rear | leg_4 | 1.000 | set |

No borderline pairs for these parents. / 這對親代沒有邊界配對。
Unmatched in A: horn, neck_head, tail; unmatched in B: eye_stalk

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| carapace | A.body, B.carapace | 19% | (root) |
| neck_head | A.neck_head | 100% | carapace |
| leg_1 | A.leg_rear, B.leg_1 | 47% | carapace |
| leg_2 | B.leg_2 | 37% | carapace |
| leg_3 | B.leg_3 | 89% | carapace |
| leg_4 | B.leg_4 | 84% | carapace |
| arm_front | A.arm_front, B.claw | 88% | carapace |
| horn | A.horn | 100% | neck_head |
| eye_stalk | B.eye_stalk | 0% | carapace |

- genes from A overall: 62%; from B: 38%
- not inherited (peripheral parts left out by chance): 1
- grafted: 0; lost to the site rule: 0; dropped orphans: 0
- crossed parts with new humps: 0 of 6

**Part-attribute layer (on) / 部位屬性層（開啟）**

- limb set leg_rear ~ leg_1, leg_2, leg_3, leg_4: count and placement from B (4 parts in the set), attributes from length B, thickness A, taper B, bend A
- neck_head: own; reach beyond the surface 0.197, thickness 0.026 (body-size units)
- leg_1: length B, thickness A, taper B, bend A; reach beyond the surface 0.300, thickness 0.027 (body-size units)
- leg_2: length B, thickness A, taper B, bend A; reach beyond the surface 0.281, thickness 0.027 (body-size units)
- leg_3: length B, thickness A, taper B, bend A; reach beyond the surface 0.287, thickness 0.027 (body-size units)
- leg_4: length B, thickness A, taper B, bend A; reach beyond the surface 0.312, thickness 0.027 (body-size units)
- arm_front: length A, thickness B, taper B, bend A; reach beyond the surface 0.073, thickness 0.034 (body-size units)
- horn: own; reach beyond the surface 0.056, thickness 0.007 (body-size units)
- eye_stalk: own; reach beyond the surface 0.073, thickness 0.015 (body-size units)

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 22,784; volume: 0.2144; built in 1.4 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 9 parts, 88 nodes, 72 bones, 123 edges, 11,394 vertices; access: read_only
- groups: arrangement:mirror, arrangement:single, attached, root, tag:central, tag:cutting, tag:defense_organ, tag:end_effector, tag:grasping, tag:head, tag:limb, tag:locomotion, tag:motor_organ, tag:sensor, tag:sensory_cluster, tag:shell, tag:torso, tag:weapon_part
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 3.3e-16); rest pose reproduces the mesh (largest error 3.3e-16)
- parts with vertices: 9 / 9; bones with vertices: 62 / 72
- turning only neck_head.b0: 98.7% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 48 bones
- demo pose: volume change -0.8%, flipped faces 1.28%
- result: PASS

## Result / 結果

**PASS** in 13 s. Output folder: `out_attr/biped_x_crab_seed7_attr`
