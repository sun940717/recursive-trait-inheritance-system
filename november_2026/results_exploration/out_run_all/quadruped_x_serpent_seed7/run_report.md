# RTIS run: quadruped x serpent, seed 7

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
| tail | tail_tip | 0.500 | clear |

No borderline pairs for these parents. / 這對親代沒有邊界配對。
Unmatched in A: leg_front, leg_rear; unmatched in B: fang

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| torso | A.body, B.torso | 20% | (root) |
| head | A.neck_head, B.head | 68% | torso |
| tail | A.tail, B.tail_tip | 37% | torso |
| leg_rear | A.leg_rear | 100% | torso |
| fang | B.fang | 0% | head |

- genes from A overall: 43%; from B: 57%
- not inherited (peripheral parts left out by chance): 1
- grafted: 0; lost to the site rule: 0; dropped orphans: 0
- crossed parts with new humps: 2 of 3

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 23,176; volume: 0.1854; built in 1.7 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 5 parts, 45 nodes, 38 bones, 53 edges, 11,590 vertices; access: read_only
- groups: arrangement:mirror, arrangement:single, attached, root, tag:central, tag:cutting, tag:grasping, tag:head, tag:limb, tag:locomotion, tag:motor_organ, tag:sensor, tag:structural, tag:tail, tag:torso, tag:weapon_part
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 4.4e-16); rest pose reproduces the mesh (largest error 4.4e-16)
- parts with vertices: 5 / 5; bones with vertices: 38 / 38
- turning only head.b0: 97.0% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 10 bones
- demo pose: volume change -0.4%, flipped faces 0.10%
- result: PASS

## Result / 結果

**PASS** in 12 s. Output folder: `out_run_all/quadruped_x_serpent_seed7`
