# 【11 月版本】RTIS × ATMS 部位接口：形體包（Morphology Package）v0.2
**Part interface between RTIS bodies and ATMS: the morphology package, v0.2**

**日期：** 2026-11-14（v0.1）；2026-11-15（v0.2：第五節三個決定定案，新增 `access`、`lineage`、狀態包）
**狀態：** 屬 B 區。11-15 在雲端用 Python 3.10.12 與專案裡真正的 pce.py／ontology.py 執行過；**還沒在你的電腦上執行。**
**原型：** `part_interface.py`、`rtis_run_once.py`（完整流程跑一次）
**對應的 ATMS 文件：** `docs/rtis_interface.md`（v0.1）、`docs/glossary.md`（讀取自 github.com/sun940717/Adaptive-Topological-Motion-System，commit efb2848）

---

## 〇、摘要

- ATMS 現有的接口規格（`rtis_interface.md` v0.1）只定義了「狀態包」：RTIS 告訴 ATMS 現在是什麼狀態、意圖是什麼。它**沒有定義身體長什麼樣子要怎麼交給 ATMS**。這份文件補的就是這一塊。
- 做法：每個產出的身體附一份「形體包」，用 ATMS 自己的詞彙（節點、邊、參數）描述身體，不假設任何解剖結構。四足、水母、融合出來的子代，格式完全一樣。
- 動作系統可以指定四種對象：一個節點、一根骨頭、一個部位、一個群組（例如所有帶 `limb` 標籤的部位）。
- 已測試：用同一組只靠形體包寫出來的動作，讓七個身體（六種原始形體＋一個融合子代）動起來。
- 第五節的三件事已在 11-15 定案（照我的建議）。

A short English summary: ATMS's current interface spec covers the semantic state package only. This draft adds the missing half: how a generated body is handed to ATMS. Each body ships with a morphology package (nodes, edges, parameters, in ATMS's vocabulary, no anatomy assumed) plus a default mesh binding. A motion system can address a node, a bone, a part or a group.

---

## 一、它在整個系統裡的位置

```
RTIS 基因組 ──發育──> 骨架 ──隱式曲面──> 網格
                        │                    │
                        └──── 形體包 ────────┘      （這份文件）
                                 │
RTIS 狀態包（rtis_interface.md）─┤
                                 ▼
                               ATMS ──> 動作紀錄（Action Trace）／節點的變換
                                 │
                                 ▼
                    把節點的變換套到網格上（蒙皮） ──> 會動的模型
```

對照 ATMS 詞彙表：

| ATMS 的詞 | 形體包裡的對應 |
|---|---|
| Topological Entity 拓樸實體 | 一份形體包 |
| Node 節點 | 每個部位每一份複本上的每個關節 |
| Edge 邊 | 四種：`bone`（同一條鏈上相鄰的節點）、`attach`（部位接在父部位的哪根骨頭上）、`mirror`（左右對應）、`radial`（放射排列中相鄰的複本） |
| Parameter 參數 | 節點的位置與粗細、骨頭長度、部位的標籤與排列方式 |
| `group=limb_like` | `groups` 裡的 `tag:limb` 等群組 |

---

## 二、一份形體包＝三個檔案

| 檔案 | 內容 |
|---|---|
| `<name>.morph.json` | 節點、骨頭、邊、部位、群組 |
| `<name>.skin.npz` | 網格（頂點、三角形）、每個頂點跟著哪幾根骨頭動、每個頂點／三角形屬於哪個部位 |
| `<name>.obj` | 給人看的網格，每個部位一個群組（Blender 可直接開） |
| `<name>.state.json` | v0.2 新增（`rtis_run_once.py` 產出）。ATMS 的狀態包；RTIS 的狀態邏輯還沒接上，所以先填 `rtis_interface.md` 的預設值，並指向形體包 |

**座標系**：JSON 與 npz 是 x 向前、y 向生物的左邊、z 向上。OBJ 跟其他匯出一樣轉成 Y 朝上（(x, y, z) → (x, z, −y)），**兩者的座標不要混用**。

### `morph.json` 的欄位

| 欄位 | 內容 |
|---|---|
| `format`、`version` | `rtis-morphology-package`、`0.2` |
| `about` | 格式說明（寫在檔案裡，讀檔的人不需要這份文件） |
| `genome_digest` | 基因組的指紋，用來確認形體包和基因組是同一隻 |
| `size` | 包圍盒與對角線長度（長度單位的基準） |
| `access` | v0.2 新增。`{"motion_system": "read_only"}`：見第五節第 2 點 |
| `lineage` | v0.2 新增。`generation`、`parents`、`seed`、`rules`、`matched_pairs`、每個部位來自親代 A 的基因比例 `ancestry_a`。原始形體是第 0 代、沒有親代 |
| `parts[]` | 每個基因一筆：`name`、`tags`、`arrangement`（single／mirror／radial）、`copies`（`""`、`L`／`R`、`0..N-1`）、`parent`、`attach`、`is_core`、`bones_per_copy`、`ancestry_a`、`vertices` |
| `groups{}` | 具名的部位集合：`root`、`attached`、`tag:<標籤>`、`arrangement:<排列>` |
| `nodes[]` | `id`、`part`、`copy`、`index`、`position`、`radius`、`tip` |
| `bones[]` | `id`、`part`、`copy`、`index`、`from`、`to`、`length`、`parent`（它跟著哪根骨頭動） |
| `edges[]` | `bone`／`attach`（含 `t`：接在那根骨頭的哪個位置）／`mirror`／`radial` |

### `skin.npz` 的陣列

| 陣列 | 形狀 | 內容 |
|---|---|---|
| `vertices` | (V, 3) | 頂點 |
| `faces` | (F, 3) | 三角形 |
| `bone_index` | (V, 4) | 每個頂點最多跟 4 根骨頭（`bones[]` 的索引） |
| `bone_weight` | (V, 4) | 對應的權重，總和為 1 |
| `vertex_part` | (V,) | 頂點屬於哪個部位（`parts[]` 的索引） |
| `face_part` | (F,) | 三角形屬於哪個部位 |

權重的算法：頂點到每根骨頭的距離，用的是建表面時的同一個距離（含截面輪廓）；兩根骨頭之間的過渡寬度是較細那根半徑的 0.35 倍。這是預設的綁定，ATMS 可以不用，自己綁。

---

## 三、怎麼指定對象

| 對象 | 寫法 | 例子 |
|---|---|---|
| 節點 | `<部位>[.<複本>].j<編號>` | `leg_front.L.j2` |
| 骨頭 | `<部位>[.<複本>].b<編號>` | `tentacle.3.b0` |
| 部位（所有複本） | 部位名稱 | `leg_front` |
| 群組 | 群組名稱 | `tag:limb`、`arrangement:radial`、`attached` |

`part_interface.resolve(package, target)` 會把以上任何一種換成骨頭索引。

ATMS README 裡的例子可以這樣對應：`OSCILLATE(group=limb_like, ...)` → `resolve(package, "tag:limb")`；`PROPAGATE(source=A, depth=2)` → 從一根骨頭沿著 `parent` 關係往下走兩層。

---

## 四、測試

`part_interface.py` 把七個身體各寫成一份形體包，**再從檔案讀回來**做檢查（測的是寫出去的東西，不是記憶體裡的東西）。匯出格點 0.02。

| 身體 | 部位 | 節點 | 骨頭 | 邊 | 頂點 | 有頂點的骨頭 | 兩種部位標記一致 | 只轉一個部位時，動到的頂點在那個部位內 | 示範姿勢的體積變化 | 翻面的三角形 |
|---|---|---|---|---|---|---|---|---|---|---|
| 四足 | 5 | 46 | 39 | 57 | 17,608 | 39 / 39 | 99.9% | 97.8% | −0.3% | 0.30% |
| 二足 | 6 | 52 | 43 | 66 | 15,046 | 43 / 43 | 99.5% | 99.9% | −0.5% | 0.61% |
| 蜘蛛 | 7 | 58 | 46 | 81 | 9,118 | 46 / 46 | 99.3% | 98.1% | −1.0% | 0.81% |
| 蛇 | 4 | 29 | 24 | 31 | 8,604 | 24 / 24 | 99.3% | 99.8% | −0.2% | 0.03% |
| 水母 | 3 | 69 | 56 | 132 | 19,638 | 44 / 56 | 99.8% | 96.8% | −0.1% | 0.70% |
| 螃蟹 | 7 | 61 | 48 | 88 | 12,030 | 48 / 48 | 97.8% | 99.2% | −0.5% | 1.97% |
| 二足 × 蜘蛛的子代 | 8 | 72 | 59 | 96 | 8,636 | 54 / 59 | 99.7% | 99.3% | −0.4% | 0.69% |

另外：每個頂點的權重總和為 1、不給任何動作時讀回來的網格與原本完全相同（兩者誤差都小於 10⁻⁹）；七個身體的每個部位都有頂點。

**示範姿勢**（`pose_test.png`）：只靠形體包寫的兩個動作，「每個附屬部位在根部擺動」和「一個小彎折沿著每條鏈傳下去」，同一段程式碼套在四足、水母、螃蟹、融合子代上都會動。這段程式碼只是測試，不是 ATMS，也不是在建議 ATMS 該怎麼做。

**過程中修掉的兩個問題**
- 第一版的權重讓水母的鐘形體跟著一條細觸手動（只轉一條觸手時，動到的頂點只有 47.6% 在觸手上）。原因是過渡寬度用了粗的那根骨頭的半徑；改成用較細的那根後是 96.8%。
- 第一版用圓形骨頭的距離算權重，螃蟹又寬又扁的甲殼邊緣被算成腳（兩種部位標記只有 91.5% 一致）。改成用建表面時的同一個距離後是 97.8%。

**v0.2 重新匯出（11-15，Python 3.10.12）**：七個身體的數字與上表相同（翻面比例最多差 0.03 個百分點）；每份都帶 `access` 與 `lineage`，群組名稱改為 ontology 標籤。

**已知的不足**
- 完全埋在身體裡的骨頭沒有自己的頂點（水母每條觸手和口腕的第一根骨頭、子代的 5 根）。轉它，掛在它上面的東西還是會跟著動。
- 示範姿勢有 0.03%–2% 的三角形翻面，是關節處線性混合的常見瑕疵。沒有檢查網格自我穿插。
- 沒有關節的活動範圍、質量、接地點。ATMS 的連續性與拓樸有效性檢查會需要其中一些，等 ATMS 有實作再補（v0.2）。
- 節點 id 在同一隻生物內固定，但**不保證跨世代相同**：子代的部位名稱來自親代，撞名時會加 `_2`。
- **肢體埋在主體裡**（11-15 跑完整流程時發現，見結果文件第十節）：主體來自水母時，其他親代的頭、腿只剩小凸起，甚至完全沒有表面。這種部位在形體包裡存在，但轉它幾乎看不到東西在動。

---

## 五、三個決定（2026-11-15 定案）

1. **遺傳歸 RTIS 管。** 遺傳在 RTIS 的基因上做；ATMS 不重做遺傳，只透過形體包的 `lineage` 接收結果。ATMS `system_overview.md` 裡的「Feature Redistribution」改成描述 RTIS 這一側在做的事，或在 ATMS 那邊標成「由 RTIS 負責」。**這需要你改 ATMS repo 的文件，我沒辦法推送。**
2. **形體包唯讀。** 動作系統可以移動節點（擺姿勢），不能新增、移除或重接節點（`access.motion_system = "read_only"`）。要改結構，得回到 RTIS 改基因、重新長出身體與新的形體包。ATMS 的輸出 B（Topology Transform Trace）在 v0.2 不使用。
3. **群組用 ontology 標籤。** 六種原始形體從 11-15 起預設帶 `ontology.py` 的標籤（`form_fusion_lab.all_forms(ontology_tags=True)`），群組名稱變成 `tag:limb`、`tag:head`、`tag:torso` 這類穩定的名稱。舊的原型標籤只留給重現 11-13 的實驗。

## 六、名稱

- **ATMS** 本身：repo 名稱已經叫 System，維持「動作系統（motion system）」。
- 它在 RTIS 流程裡的那一格：「動作模組（motion module）」。
- 之後真正跑起來的程式：「動作引擎（motion engine）」。
- 這份文件定義的東西：「形體包（morphology package）」；口頭上叫「部位接口」。
