# RTIS run: serpent x jellyfish, seed 7

## 0. Environment / 環境

- python: `3.10.12`
- numpy: `2.2.6`
- platform: `Linux-6.18.44-fc-v470-x86_64-with-glibc2.39`
- pce.py: `/home/claude/rtis_real/pce.py`
- ontology.py: `/home/claude/rtis_real/ontology.py`

## 1. Parents / 親代

**A: serpent** (4 parts, 59 genes)
```
torso          single  14 bones   tags torso, structural, central
head           single  3 bones   tags head, sensor
fang           mirror  2 bones   tags weapon_part, cutting, grasping
tail_tip       single  3 bones   tags tail, motor_organ
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
| torso | bell | 1.000 | root |

No borderline pairs for these parents. / 這對親代沒有邊界配對。
Unmatched in A: fang, head, tail_tip; unmatched in B: oral_arm, tentacle

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| bell | A.torso, B.bell | 20% | (root) |
| head | A.head | 100% | bell |
| tail_tip | A.tail_tip | 100% | bell |
| tentacle | B.tentacle | 0% | bell |

- genes from A overall: 40%; from B: 60%
- not inherited (peripheral parts left out by chance): 1
- grafted: 0; lost to the site rule: 1; dropped orphans: 0
- crossed parts with new humps: 0 of 1

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 36,564; volume: 0.6482; built in 2.2 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 4 parts, 71 nodes, 60 bones, 118 edges, 18,284 vertices; access: read_only
- groups: arrangement:radial, arrangement:single, attached, root, tag:appendage, tag:central, tag:grasping, tag:head, tag:motor_organ, tag:sensor, tag:structural, tag:tail, tag:torso
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 3.3e-16); rest pose reproduces the mesh (largest error 4.4e-16)
- parts with vertices: 4 / 4; bones with vertices: 43 / 60
- turning only head.b0: 95.8% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 0 bones
- demo pose: volume change -0.0%, flipped faces 0.70%
- result: PASS

## Result / 結果

**PASS** in 15 s. Output folder: `out_run_all/serpent_x_jellyfish_seed7`
