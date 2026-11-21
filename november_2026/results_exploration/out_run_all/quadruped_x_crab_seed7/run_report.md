# RTIS run: quadruped x crab, seed 7

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
| leg_rear | leg_4 | 1.000 | clear |
| leg_front | leg_1 | 1.000 | clear |

No borderline pairs for these parents. / 這對親代沒有邊界配對。
Unmatched in A: neck_head, tail; unmatched in B: claw, eye_stalk, leg_2, leg_3

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| carapace | A.body, B.carapace | 19% | (root) |
| neck_head | A.neck_head | 100% | carapace |
| leg_front | A.leg_front, B.leg_1 | 47% | carapace |
| leg_4 | A.leg_rear, B.leg_4 | 37% | carapace |
| claw | B.claw | 0% | carapace |
| leg_2 | B.leg_2 | 0% | carapace |
| eye_stalk | B.eye_stalk | 0% | carapace |

- genes from A overall: 31%; from B: 69%
- not inherited (peripheral parts left out by chance): 2
- grafted: 0; lost to the site rule: 0; dropped orphans: 0
- crossed parts with new humps: 0 of 3

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 23,320; volume: 0.2171; built in 0.9 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 7 parts, 66 nodes, 54 bones, 90 edges, 11,660 vertices; access: read_only
- groups: arrangement:mirror, arrangement:single, attached, root, tag:central, tag:cutting, tag:defense_organ, tag:end_effector, tag:grasping, tag:head, tag:limb, tag:locomotion, tag:motor_organ, tag:sensor, tag:sensory_cluster, tag:shell, tag:torso
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 3.3e-16); rest pose reproduces the mesh (largest error 2.2e-16)
- parts with vertices: 7 / 7; bones with vertices: 46 / 54
- turning only neck_head.b0: 98.5% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 36 bones
- demo pose: volume change -0.1%, flipped faces 1.11%
- result: PASS

## Result / 結果

**PASS** in 10 s. Output folder: `out_run_all/quadruped_x_crab_seed7`
