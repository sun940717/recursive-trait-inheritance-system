# RTIS run: spider x jellyfish, seed 7

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
| cephalothorax | bell | 1.000 | root |

No borderline pairs for these parents. / 這對親代沒有邊界配對。
Unmatched in A: abdomen, fang, leg_1, leg_2, leg_3, leg_4; unmatched in B: oral_arm, tentacle

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| bell | A.cephalothorax, B.bell | 19% | (root) |
| abdomen | A.abdomen | 100% | bell |
| leg_1 | A.leg_1 | 100% | bell |
| leg_2 | A.leg_2 | 100% | bell |
| leg_3 | A.leg_3 | 100% | bell |
| leg_4 | A.leg_4 | 100% | bell |
| tentacle | B.tentacle | 0% | bell |
| oral_arm | B.oral_arm | 0% | bell |

- genes from A overall: 65%; from B: 35%
- not inherited (peripheral parts left out by chance): 1
- grafted: 0; lost to the site rule: 0; dropped orphans: 0
- crossed parts with new humps: 0 of 1

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 53,912; volume: 0.8580; built in 3.4 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 8 parts, 114 nodes, 92 bones, 197 edges, 26,958 vertices; access: read_only
- groups: arrangement:mirror, arrangement:radial, arrangement:single, attached, root, tag:appendage, tag:central, tag:grasping, tag:limb, tag:locomotion, tag:motor_organ, tag:secretion_organ, tag:structural, tag:torso
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 3.3e-16); rest pose reproduces the mesh (largest error 4.4e-16)
- parts with vertices: 8 / 8; bones with vertices: 78 / 92
- turning only abdomen.b0: 94.4% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 32 bones
- demo pose: volume change -0.8%, flipped faces 2.20%
- result: PASS

## Result / 結果

**PASS** in 24 s. Output folder: `out_run_all/spider_x_jellyfish_seed7`
