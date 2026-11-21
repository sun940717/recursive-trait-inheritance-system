# RTIS run: spider x serpent, seed 7

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
| cephalothorax | torso | 1.000 | root |
| fang | fang | 1.000 | clear |

No borderline pairs for these parents. / 這對親代沒有邊界配對。
Unmatched in A: abdomen, leg_1, leg_2, leg_3, leg_4; unmatched in B: head, tail_tip

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| torso | A.cephalothorax, B.torso | 20% | (root) |
| abdomen | A.abdomen | 100% | torso |
| fang | A.fang, B.fang | 46% | torso |
| leg_1 | A.leg_1 | 100% | torso |
| leg_2 | A.leg_2 | 100% | torso |
| leg_4 | A.leg_4 | 100% | torso |

- genes from A overall: 66%; from B: 34%
- not inherited (peripheral parts left out by chance): 3
- grafted: 0; lost to the site rule: 0; dropped orphans: 0
- crossed parts with new humps: 1 of 2

**Part-attribute layer (on) / 部位屬性層（開啟）**

- fang: length B, thickness B, taper A, bend B; reach beyond the surface 0.022, thickness 0.005 (body-size units)
- leg_1: own; reach beyond the surface 0.470, thickness 0.016 (body-size units)
- leg_2: own; reach beyond the surface 0.433, thickness 0.016 (body-size units)
- leg_4: own; reach beyond the surface 0.462, thickness 0.016 (body-size units)

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 67,044; volume: 0.9192; built in 6.5 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 6 parts, 58 nodes, 48 bones, 76 edges, 33,524 vertices; access: read_only
- groups: arrangement:mirror, arrangement:single, attached, root, tag:central, tag:cutting, tag:grasping, tag:limb, tag:locomotion, tag:motor_organ, tag:secretion_organ, tag:structural, tag:torso, tag:weapon_part
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 4.4e-16); rest pose reproduces the mesh (largest error 8.9e-16)
- parts with vertices: 6 / 6; bones with vertices: 48 / 48
- turning only abdomen.b0: 100.0% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 24 bones
- demo pose: volume change -0.3%, flipped faces 0.37%
- result: PASS

## Result / 結果

**PASS** in 37 s. Output folder: `out_attr/spider_x_serpent_seed7_attr`
