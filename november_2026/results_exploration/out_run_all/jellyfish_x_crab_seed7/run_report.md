# RTIS run: jellyfish x crab, seed 7

## 0. Environment / 環境

- python: `3.10.12`
- numpy: `2.2.6`
- platform: `Linux-6.18.44-fc-v470-x86_64-with-glibc2.39`
- pce.py: `/home/claude/rtis_real/pce.py`
- ontology.py: `/home/claude/rtis_real/ontology.py`

## 1. Parents / 親代

**A: jellyfish** (3 parts, 35 genes)
```
bell           single  4 bones   tags torso, structural, central
tentacle       radial  5 bones   tags appendage, grasping, motor_organ
oral_arm       radial  3 bones   tags appendage, grasping, secretion_organ
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
| bell | carapace | 1.000 | root |

No borderline pairs for these parents. / 這對親代沒有邊界配對。
Unmatched in A: oral_arm, tentacle; unmatched in B: claw, eye_stalk, leg_1, leg_2, leg_3, leg_4

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| carapace | A.bell, B.carapace | 19% | (root) |
| tentacle | A.tentacle | 100% | carapace |
| leg_1 | B.leg_1 | 0% | carapace |
| leg_2 | B.leg_2 | 0% | carapace |
| leg_3 | B.leg_3 | 0% | carapace |
| leg_4 | B.leg_4 | 0% | carapace |
| eye_stalk | B.eye_stalk | 0% | carapace |

- genes from A overall: 20%; from B: 80%
- not inherited (peripheral parts left out by chance): 2
- grafted: 0; lost to the site rule: 0; dropped orphans: 0
- crossed parts with new humps: 0 of 1

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 34,940; volume: 0.3362; built in 1.5 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 7 parts, 99 nodes, 80 bones, 169 edges, 17,472 vertices; access: read_only
- groups: arrangement:mirror, arrangement:radial, arrangement:single, attached, root, tag:appendage, tag:central, tag:defense_organ, tag:grasping, tag:limb, tag:locomotion, tag:motor_organ, tag:sensor, tag:sensory_cluster, tag:shell, tag:torso
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 3.3e-16); rest pose reproduces the mesh (largest error 2.2e-16)
- parts with vertices: 6 / 7; bones with vertices: 76 / 80
- turning only tentacle.0.b0: 96.6% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 32 bones
- demo pose: volume change -0.3%, flipped faces 1.14%
- result: FAIL: every part has a visible surface (none: eye_stalk)

## Result / 結果

**FAIL** in 14 s. Output folder: `out_run_all/jellyfish_x_crab_seed7`
