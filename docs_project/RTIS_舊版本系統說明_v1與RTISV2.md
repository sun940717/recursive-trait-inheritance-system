# 【舊版本】RTIS 系統說明：v1 與 RTISV2（2026-11-15 整理）

**注意：這份講的是舊版本**（v1 完整系統與 RTISV2）。11 月的版本（論文要講的版本）請看 `claude/RTIS_11月版本_系統說明.md`。這份原本叫「系統說明_現行版」，2026-11-16 改名，避免和 11 月版本混淆。

**用途：** 把 4–5 月的六份文件（概念文件 v4.1、架構文件、總整理、專案結構整理、思路歷程、5 月交接文件）裡仍然有效的內容合併成一份，並依 2026-11-15 硬碟上的程式核對過。舊文件保留作歷史，內容與本文件衝突時以本文件為準。

**標記：** 「已核對」＝ 2026-11-15 在 `D:\ai-research-lab\RTIS` 用程式碼搜尋確認；「未核對」＝照舊文件抄錄，沒有重新檢查。

相關文件：`claude/00_RTIS_總索引.md`（所有文件的索引）、`claude/RTIS_現況總覽_20261115.md`（論文與資料夾現況）、`claude/RTIS_待辦與未決事項.md`、`claude/RTIS_實驗歷程.md`（11 月的幾何實驗）。

---

## 一、RTIS 是什麼

RTIS（Recursive Trait Inheritance System）是一個生成與演化虛擬生物的系統。

- 生物不是固定骨架，而是「特徵（trait）」互相附著形成的圖。任何特徵可以附著在任何特徵上。
- 兩個結構完全不同的物種（例如水母 × 蜘蛛）可以交配：系統用語意標籤的相似度找出對應的部位。這個機制叫 **PCE（Part Correspondence Engine）**，是整個專案的核心。
- 另有 LLM（Claude）在預算限制內決定突變。
- 用途：遊戲生物生成、人工生命、演化計算。

**定位（5 月之後的說法）：** 「第一個用語意引導對應做跨物種生物合成的完整互動系統」，不主張發明語意引導方法本身（相關工作：Stable-SCore, CVPR 2025）。

**一個要更正的舊說法：** 概念文件寫「RTIS 沒有適應度函數」。這只對 v1 系統成立。論文使用的 RTISV2 有身體結構適應度與菁英錦標賽選擇（Phase 4），而且論文的主要結論正是「PCE 的優勢要在選擇壓力下才出現」。

---

## 二、三套程式

| 名稱 | 位置 | 內容 | 與論文的關係 |
|---|---|---|---|
| **v1 完整系統** | `RTIS\rtis\` | Flask 網頁介面、PCE、ontology、形態原發育、細胞配方、LLM 突變、L-system、3D 檢視、知識圖譜；5–6 月加入 3D 網格混血 | 論文的系統架構章節描述它；實驗數字已不來自這裡 |
| **RTISV2** | `RTIS\RTISV2\` | 受控實驗用的精簡重寫（純標準函式庫，119 個測試）：特徵圖、加權 Jaccard PCE、適應度、選擇 | **論文所有實驗數字的來源**（Phase 3、Phase 4，n = 30） |
| **11 月幾何原型** | `RTIS\current_2026-11\`（專區） | 骨架基因組＋隱式曲面＋傅立葉細節層、跨形體融合規則、部位屬性層、形體包接口、生成重播 | **論文的主體**（11-15 更正）；詳見 `claude/RTIS_11月版本_系統說明.md` |

v1 在 5 月整理過子資料夾：`rtis\` 底下現在有 `core\`、`domain\`、`infrastructure\`、`presentation\`、`rendering\`、`tools\`、`tests\`、`game\`、`static\` 等。舊文件裡寫在 `rtis\` 最上層的檔案，有些已經移進去（例：`tests\test_lsystem.py`、`tools\morph_engine.py`、`tools\mesh_inherit.py`、`static\cosmos\cosmos_demo.html`）。（已核對）

---

## 三、v1 的分層架構

```
Layer 5  渲染      Three.js 3D 檢視器、並排檢視、血緣樹、知識圖譜
Layer 4  形體      trait.morphology（形狀、縮放、顏色、發光、硬度、銳利度）
                   幾何兩種模式：generative（Shap-E）／lsystem
Layer 3  語意      Ontology：細胞／器官／部位三層標籤        ← 核心
Layer 2  結構      Trait + BodyGraph（有向圖＋橫向語意連結）
Layer 1.5 細胞     Cell Recipe：七種細胞比例 → 組織特性       ← 湧現來源
Layer 1  遺傳      Genome + GeneModule + develop()
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
D3  器官湧現   組織聚集 → 自動命名成 Trait（依物種解剖名稱）
D2  組織形成   同類細胞的連通區域
D1  細胞分化   形態原濃度 → 細胞類型（用百分位，不用固定閾值）
D0  形態原     Gray-Scott 反應擴散 → 化學濃度場
Layer 0  輸入      預設物種／外部 .obj、.glb／（未來）文字描述
```

兩條資料流：
- 完整發育路線：參數 → D0 → D1 → D2 → D3 → BodyGraph → 形體 → 渲染
- 語意路線（跳過發育層）：`Genome.develop()` → BodyGraph → 形體 → 渲染

預設物種四種：蜘蛛、水母、螃蟹、蛇（`make_spider_genome` 等四個函式，已核對）。

Gray-Scott 參數（F, k）：水母 0.055／0.062、蜘蛛 0.035／0.065、螃蟹 0.022／0.059、蛇 0.014／0.054。這些是手動調的，沒有生物學依據。（未核對）

---

## 四、PCE

### 4.1 要解決的問題

兩個形態不同的生物交配時，要決定「哪個部位對應哪個」。NEAT 用歷史標記解決，前提是有共同血緣。PCE 改用語意標籤的相似度，不需要共同演化歷史。

試過而放棄的做法：用名稱配對（不同物種幾乎沒有同名部位）、用圖上的層級位置配對（拓撲差太多）。

### 4.2 加權 Jaccard（已核對：`pce.py` 的 `semantic_similarity_layered`）

```
sim = 交集標籤的權重和 / 聯集標籤的權重和
權重：細胞層 0.5、器官層 1.0、部位層 2.0
```

原則：解剖位置相同 > 功能相同 > 細胞類型相同。

例：水母觸手 [motor, grasping] 對蜘蛛前腿 [motor, locomotion] = 1 / 3 = **0.333**。舊文件（總整理、思路歷程）寫 0.5 或 0.67，是錯的。

### 4.3 配不到時

實際只有一種退路：直接掛到根節點。舊文件寫的「部位 → 器官 → 細胞三層回退」在程式裡不存在。

### 4.4 其他已實作的部分（已核對）

- `semantic_neighbors`：配對結果雙向寫回兩個特徵，BodyGraph 因此從樹變成有橫向連結的圖。
- `validate_coherence`：繼承後依 ontology 組合規則檢查子代，缺少的結構會寫進給 Claude 的突變提示。
- `PCEConfig`（PCE v2 雙通道，5 月）：語意加權 Jaccard（α）＋ PCA 幾何相似度（β），預設 0.6／0.4。消融結果見第十節。

### 4.5 名稱

PCE 一律是 **Part Correspondence Engine**。早期草稿寫過 Phenotypic／Phylogenetic，都不用。

### 4.6 11 月版本裡的配對規則

0.40 以上一定配；0.25–0.40 依機率 (s − 0.25) / 0.15；低於 0.25 不配。細節在 `claude/RTIS_實驗歷程.md`。

---

## 五、遺傳與 LLM 突變（v1）

### 5.1 Genome

`GeneModule` 欄位：名稱、語意標籤、附著條件標籤、表現機率、是否核心、形體覆蓋值、幾何基因（可選）。同一個 Genome 每次 `develop()` 結果可能不同。

`trait_stability` 欄位只是建議，**程式裡沒有**（已核對）。

### 5.2 兩親繁殖 `develop_from_parents(A, B, config)`

核心骨架鎖定 → 周邊特徵繼承 → 形體數值混合 → 回傳子代與剩餘突變預算。

`InheritanceConfig` 預設值（照概念文件 v4.1；`parent_a_dominance` 與 `max_peripheral_traits` 已核對存在，其餘數值未核對）：

| 欄位 | 預設 | 意思 |
|---|---|---|
| inheritance_factor | 0.70 | 整體遺傳保真度 |
| core_lock | 0.90 | 核心骨架鎖定強度 |
| morphology_noise | 0.05 | 形體混合的雜訊 |
| alpha | 0.50 | 親代 A 的形體權重 |
| mutation_budget_micro／medium／major | 5／2／1 | 三種突變的上限 |
| allow_new_core_trait | False | 是否允許突變核心骨架 |
| parent_a_dominance | 0.50 | 親代 A 的周邊特徵佔比 |
| max_peripheral_traits | 0 | 周邊特徵上限，0 表示不限 |

### 5.3 Claude 的角色

在預算內做最後決定：每個特徵的突變類型（none／micro／medium／major）與形體數值；每個突變標記可不可以遺傳。提示裡帶最近三代的摘要（`build_evolution_context`）和相似的湧現紀錄（`find_similar_emergence`）。（兩個函式已核對存在）

### 5.4 專案原則：基因型優先

遺傳要作用在基因上，不是在長好的形狀上做平均。11 月的實驗量過：加權平均的交配，10 代後形狀變異只剩 0.13%；每個基因整個來自一方的交配剩 75–79%。

---

## 六、其他 v1 子系統

**L-system 幾何（4 月完成）**：`geometry_gene.py`、`lsystem_expander.py`。`LSystemGene` 有 axiom、規則、迭代次數、分支角、漸細率、節長、起始半徑、`blend_k`、對稱性。可由細胞配方推出參數。預設物種的 `geometry` 是 `None`，不影響原有行為。11 月評估：這些帶半徑的線段可以直接接上骨架＋隱式曲面。

**細胞配方（Layer 1.5）**：七種細胞（structural、motor、sensory、secretory、armor、neural、energy）的比例 → 組織特性 → 形體提示。

**佛光湧現案例**：seed = 888，energy_cell = 0.35、sensory_cell = 0.30 時，自發出現一個浮動光環，沒有人設計它。這是論文第四個貢獻的唯一正例。紀錄已寫進 `rtis\outputs\training_data\emergence_labels.jsonl`（已核對，共 1 筆）。

**發育時序（`development.py`）**：`onset_timing`、`growth_pattern`、`apoptosis_signal`、`canalization` 有定義，但 `develop()` 仍是一次展開，`onset_timing` 沒有實際作用。（已核對：`genome.py` 沒有用到 `onset_timing`）

**視覺化**：`body3d.py`（Three.js，含 UnrealBloomPass，已核對）、`fusion3d.py`（親代 A／親代 B／子代並排）、`ancestry_tree.py`（D3 血緣樹）、`brain_graph.py`（Canvas 2D 知識圖譜）。

**網頁介面**：`app.py`（localhost:5000；/presets、/upload、/fuse、/morphogen、/viewer）；`hub_app.py`（localhost:5001，研究輔助）；`game_app.py`（localhost:5050，6 月的配種遊戲雛形）。

**訓練資料（`data_logger.py`）**：2026-11-15 的筆數：`genome_eval_pairs` 3,080、`mutation_pairs` 4、`emergence_labels` 1。（已核對）

---

## 七、System A／System B，以及之後的路線變化

4 月的決定：把系統分成兩塊，各自有時間線。

- **System A**（語意、遺傳、知識圖譜）：可獨立發表。
- **System B**（3D 網格）：每個子問題都是獨立研究題目，不讓它拖住 System A。

System B 之後的變化：

| 時間 | 路線 | 結果 |
|---|---|---|
| 4 月以前 | Shap-E／Trellis 生成、真實模型解析、Blender、BaseMesh 頂點位移 | 都卡在：生成的網格沒有部位標記、跨物種幾何對不上 |
| 5-21 | **改成程序性生成**：不辨識外部模型，從語意 Genome 直接生成骨骼／肌肉／器官。`skeleton_generator.py` 第一級（圓柱骨節）已在 `rtis\`（已核對存在） | 第二級（依 BodyGraph 建層級骨架）、第三級（肌肉包覆）沒有做 |
| 5-31 – 6-28 | **又回頭試真實網格**：本機 Shap-E、FFD、體素融合、潛空間插值、functional maps、蟹螯嫁接到錦鯉 | 體素融合掉細節約 26%；潛空間插值產生破碎形狀；魚 × 蟹的 functional maps 效果不佳；嫁接做出一個完整模型。沒有統計 |
| 11 月 | **骨架基因組＋隱式曲面**（程序性路線的新版本）：每隻一個封閉網格 | 目前的版本，論文的主體；見實驗歷程 |

5 月還定了一個低優先方向：在 ontology 加 `mechanical`、`crystalline` 等標籤，讓 PCE 支援非生物合成。**沒有做**（已核對：`ontology.py` 沒有這些標籤）。

---

## 八、架構演變（設計思路的轉折）

| 版本 | 架構 | 為什麼改 |
|---|---|---|
| v0 | 每個基因對應一個固定部位 | 組合空間有限 |
| v1 | 特徵動態圖（BodyGraph） | 跨物種交配需要對應機制 |
| v2 | ＋PCE（語意標籤＋Jaccard） | 名稱配對、位置配對都失敗 |
| v3 | ＋形態原發育層 D0–D3 | Genome 直接輸出身體，缺少發育過程 |
| v4 | ＋`semantic_neighbors`、知識圖譜 | 配對結果用完就消失 |
| v5 | System A／B 分離 | 兩者成熟度不同，不該互等 |
| v6（5 月） | RTISV2：實驗框架先做、永久保留隨機基準、加入選擇壓力 | v1 是先做系統後補實驗，PCE 的效果無法單獨歸因 |
| v7（11 月） | 骨架基因組＋隱式曲面；基因型優先的遺傳規則 | 傅立葉管各部位不相連；加權平均的遺傳會讓變異消失 |

發育層的兩個細節：細胞分化從固定濃度閾值改成百分位，否則有些種子整隻只有一種細胞；器官名稱從通用名改成各物種的解剖名（水母的 motor → tentacle，蜘蛛的 motor → foreleg）。

---

## 九、與既有研究的關係

| 研究 | RTIS 的關係 |
|---|---|
| Karl Sims 1994 | 「基因定義生長規則，不定義固定形體」的前身 |
| NEAT 2002 | PCE 用語意相似度取代歷史標記 |
| MAP-Elites 2015 | RTIS 沒有系統性的多樣性存檔 |
| L-systems 1968 | 幾何的一種模式 |
| EvoPrompting 2023、ELM（Lehman 2022／2024） | 同屬「LLM 當演化算子」；RTIS 作用在語意特徵圖，不是程式碼；另有跨物種對應、發育層、細胞層、湧現紀錄 |
| Stable-SCore（CVPR 2025） | 語意引導對應的既有方法；RTIS 不主張發明這個方法 |

5 月對 ELM 的評估：抄襲風險低，在 Related Work 引用並說明差異即可。完整書目在 `RTIS_參考論文清單.md`（內容仍有效，只有標頭的投稿目標過時）。

---

## 十、實驗結果一覽

| 實驗 | 規模 | 結果 | 在論文裡？ |
|---|---|---|---|
| RTISV2 Phase 3（無選擇） | n = 30、10 代 | PCE 20.6 vs 隨機 20.6，p = .50 | 是 |
| RTISV2 Phase 4（有選擇） | n = 30、10 代 | 特徵數 43.8 vs 38.1，p = .0002，d = 0.963；適應度 0.789 vs 0.404，d = 4.015；多樣性 p = .30 | 是 |
| v1 PCE vs 無 PCE | n = 10 | 舊結果檔 `pce_vs_nopce_with_sd.md` | 否（已被取代） |
| v1 雙通道消融（4 條件） | n = 10、10 代、無選擇 | 全部不顯著；雙通道 vs 無 PCE 特徵數 19.1 vs 15.3，p = .10 | 否 |
| 3D 網格混血（5–6 月） | 個案 | 見第七節 | 否 |
| 11 月幾何 | 固定測試組 | 見實驗歷程 | 否 |

**已作廢的數字：** 舊文件裡的「v1 n = 30：t = 3.098、p = .003、d = 1.017；多樣性 p = .011」與「PCE 匹配率 97.7%（879 次）」。前者在硬碟上找不到對應的輸出檔，論文已不使用；後者未核對。

---

## 十一、已知問題（v1）

| 問題 | 狀態 |
|---|---|
| 子代再當親代時，形體顯示成一層平面（`body3d.py` 取層數的方式） | 擱置；2026-11-15 未確認是否仍存在 |
| `morphology_blend()` 每代向中間靠攏，長期失去多樣性 | 未修；`reset_probability` 沒有實作（已核對）。11 月的原型改用「每個基因整個來自一方」避開這個問題 |
| `onset_timing` 沒有作用 | 未修（已核對） |
| shape 繼承在 alpha = 0.5 時一律選親代 A | 4-20 已修（未核對） |

## 十二、仍開放的架構問題

1. 形態原與 Genome 是兩個平行入口：Genome 的參數還不能控制 Gray-Scott 的 F／k。
2. 跨工作階段的全域特徵索引：沒有做（`trait_index.py` 不存在，已核對）。
3. Ontology 的位置層（前、後、背、腹）：`ontology.py` 沒有；`morphogen.py` 裡有 anterior／dorsal 字樣（已核對），兩者沒有接起來。11 月的原型也需要這一層才能分辨前腳與後腳。
4. 原型生物的標籤要改用 ontology 的部位層標籤（torso／head／limb／tail），才能拿到部位層的 2 倍權重。

---

## 十三、環境與啟動

| 環境 | 用途 |
|---|---|
| `D:\ai-research-lab\.venv-web` | Flask、Anthropic API（網頁介面、LLM 突變、論文輔助腳本） |
| `D:\ai-research-lab\.venv-morph` | numpy（幾何相關） |
| `D:\rtis_env` | Python 3.11、PyTorch、Shap-E（RTX 4050 Laptop 6 GB）；沒有搬動 |
| Python 3.10.12 | 預設版本；RTISV2 與 11 月原型都在這個版本跑過 |

所有指令從 `D:\ai-research-lab\RTIS` 執行（2026-11-15 搬移後）：

```powershell
cd D:\ai-research-lab\RTIS
..\.venv-web\Scripts\Activate.ps1
python .\rtis\app.py            # http://localhost:5000
```

RTISV2 實驗與 11 月原型的指令在 `RTIS\README.md` 與 `CLAUDE.md`。`.env`（API 金鑰）在 `D:\ai-research-lab\.env`。

GitHub：私有 `sun940717/ai-research-lab`（完整程式）；公開 `sun940717/recursive-trait-inheritance-system`（展示）；動作系統 `sun940717/Adaptive-Topological-Motion-System`。

---

## 十四、沒有併入本文件的舊內容

- **宇宙網視覺化副線與商業化路線**（cosmos_demo、Wallpaper Engine 桌布、VS Code 擴充套件 `PLAN.md`）：與 RTIS 研究無關，留在原文件（概念文件第十、十七節，`PLAN.md`）。
- **數位大腦／Obsidian 類比與渲染技術細節**：留在 `數位大腦_技術文件.md`、`RTIS_技術差距分析.md`。後者列的三個缺口，`semantic_neighbors` 與 UnrealBloomPass 已補上，全域索引還沒有。
- **生物遺傳架構對比**（TAD、表觀重設、吸引盆）：留在概念文件第十三節；其中的三項工程建議列在待辦文件。
