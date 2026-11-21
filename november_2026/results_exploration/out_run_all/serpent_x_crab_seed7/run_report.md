# RTIS run: serpent x crab, seed 7

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
| torso | carapace | 1.000 | root |

Borderline pairs (decided by chance in this mating) / 邊界配對：
- fang ~ claw: score 0.286, chance 24% -> not matched
Unmatched in A: fang, head, tail_tip; unmatched in B: claw, eye_stalk, leg_1, leg_2, leg_3, leg_4

## 3. Inheritance / 遺傳

| child part | from | share of genes from A | parent part |
|---|---|---|---|
| carapace | A.torso, B.carapace | 9% | (root) |
| head | A.head | 100% | carapace |
| fang | A.fang | 100% | head |
| tail_tip | A.tail_tip | 100% | carapace |
| claw | B.claw | 0% | carapace |
| leg_1 | B.leg_1 | 0% | carapace |
| leg_2 | B.leg_2 | 0% | carapace |

- genes from A overall: 32%; from B: 68%
- not inherited (peripheral parts left out by chance): 3
- grafted: 0; lost to the site rule: 0; dropped orphans: 0
- crossed parts with new humps: 0 of 1

## 4. Body / 身體

- closed mesh: yes; outer shells: 1; sealed bubbles: 0
- triangles: 20,568; volume: 0.1632; built in 3.6 s
- swallowed limbs: none
- result: PASS

## 5. Handoff / 交接

- morphology package v0.2: 7 parts, 59 nodes, 48 bones, 76 edges, 10,286 vertices; access: read_only
- groups: arrangement:mirror, arrangement:single, attached, root, tag:central, tag:cutting, tag:defense_organ, tag:end_effector, tag:grasping, tag:head, tag:limb, tag:locomotion, tag:motor_organ, tag:sensor, tag:shell, tag:tail, tag:torso, tag:weapon_part
- files: child.genome.json, child.morph.json, child.obj, child.skin.npz, child.state.json

## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）

- weights sum to 1 (largest error 2.2e-16); rest pose reproduces the mesh (largest error 2.2e-16)
- parts with vertices: 7 / 7; bones with vertices: 48 / 48
- turning only head.b0: 100.0% of the vertices that moved belong to that part (and what hangs from it)
- `tag:limb` addresses 24 bones
- demo pose: volume change -0.6%, flipped faces 1.68%
- result: PASS

## Result / 結果

**PASS** in 17 s. Output folder: `out_run_all/serpent_x_crab_seed7`
