# 【11 月版本】系統說明

**這份文件只講 11 月的版本**（骨架＋隱式曲面），也就是論文要講的版本。舊版本（v1、RTISV2）的說明在 `RTIS_舊版本系統說明_v1與RTISV2.md`，不要混在一起看。

**日期：** 2026-11-16
**專區位置：** `D:\ai-research-lab\RTIS\current_2026-11\`（硬碟）。Project 裡屬於這個專區的文件列在 `00_RTIS_總索引.md` 第一節。

---

## 一、一句話

給兩個身體結構不同的親代，產生一個子代：它是一個封閉的 3D 網格，每個基因都查得到來自哪一方。先用語意標籤配對部位（PCE），再在基因層遺傳，不把兩個形狀平均。

系統裡沒有機器學習、沒有 LLM、沒有物理模擬。

## 二、專區裡有什麼

```
RTIS\current_2026-11\
├── README.md        專區的地圖
├── code\            程式（16 個腳本＋重播範本）
├── docs\            這個版本的文件（設計、實驗歷程、數據、大綱、實驗計畫）
├── results\
│   ├── local\           在你的電腦上跑出來的結果
│   └── cloud_2026-11\   11 月在雲端跑的原始結果（285 個檔案）
├── experiments\     正式實驗的腳本與 CSV（計畫凍結後才會有東西）
├── paper\           新論文（還沒開始）
└── handoff\         給 Gemini、ChatGPT 的任務說明與檔案包
```

**規則：要改 11 月版本的任何東西，都在這個資料夾裡改。** `RTIS\rtis\`、`RTIS\RTISV2\`、`RTIS\outputs\paper\` 是舊版本，不要為了 11 月版本去改它們。唯一的例外：這裡的程式會讀 `RTIS\rtis\` 裡的 `pce.py`、`ontology.py`、`trait.py`（只讀，不改）。

## 三、一隻生物是什麼（基因組）

一隻生物＝一份**骨架基因組**＝一串**部位**。每個部位是一條骨頭鏈，程式裡叫 `BonePart`：

| 基因 | 意思 |
|---|---|
| `offsets` | 每根骨頭的方向與長度 |
| `radii` | 每個關節處的粗細 |
| `blend` | 這個部位和別的部位融合得多柔 |
| `parent`、`attach` | 接在哪個部位上、接在那條鏈的哪個位置（0 到 1） |
| `mirror` | 左右各長一個 |
| `radial` | 繞一圈長幾個（水母的觸手） |
| `detail0`、`detail1` | 截面輪廓（極座標傅立葉係數），鏈的起點與終點各一組 |
| `tags` | 語意標籤，給配對用 |
| `is_core` | 是不是核心部位 |

四足動物 77 個基因，二足 85 個。起始的六種形體（四足、二足、蜘蛛、蛇、水母、螃蟹）是手寫的基因組，在 `form_fusion_lab.py`。

## 四、生成流程（八步）

| 步 | 做什麼 | 在哪個檔案 |
|---|---|---|
| 1 | 取兩個親代的基因組，換上 ontology 的三層標籤 | `form_fusion_lab.py`（`all_forms`、`ONTOLOGY_TAGS`） |
| 2 | **配對部位**：算每一對部位的加權 Jaccard 分數（細胞層 0.5、器官層 1、部位層 2）。0.40 以上一定配；0.25–0.40 依機率 (s − 0.25) / 0.15；低於 0.25 不配 | `soft_match_lab.py`（`soft_match`）；分數來自 `rtis\pce.py` |
| 3 | **遺傳**：配成對的部位，每個基因整個來自一方；同一條鏈上只有一個交換點（連鎖） | `form_fusion_lab.py`（`fuse`） |
| 4 | **相對基因**：部位的大小與位置相對於體型記錄，換到別種身體上會跟著縮放 | 同上 |
| 5 | **嫁接**：沒配到的部位整個接到子代身上 | 同上 |
| 6 | **位置規則**：兩個部位搶同一個接點時只留一個 | 同上 |
| 7 | **長出形狀**：每根骨頭一個距離場 → 平滑聯集 → 加上截面細節 → marching cubes 取出網格 | `skeleton_sdf_demo.py`（`build_sdf_creature`） |
| 8 | **輸出形體包**：網格、部位、骨頭、頂點權重、血緣 | `part_interface.py` |

採用的規則在程式裡是一行：`ADOPTED = FuseOptions(relative=True, graft=True, linkage=1, site_rule=True)`，加上第 2 步的機率配對。

**選配、預設關閉：部位屬性層**（`attribute_layer.py`）。肢體的數量與擺放來自一方，每根肢體的長度、粗細、漸細、彎曲各自來自任一方。

## 五、怎麼跑

PowerShell，需要 Python 3.10.12 與 numpy、scipy、scikit-image、matplotlib：

```powershell
cd D:\ai-research-lab\RTIS\current_2026-11\code
$env:PYTHONPATH = "..\..\rtis"      # 讀 rtis\ 裡真正的 pce.py、ontology.py、trait.py
python rtis_run_once.py --out ..\results\local\out_run
```

最後一行應該是 **PASS**。可以換親代與種子：`--a quadruped --b crab --seed 3`；加 `--attributes` 開啟屬性層。

輸出（每次一個資料夾）：`run_report.md`（報告）、`run_overview.png`（圖）、`child.obj`（網格）、`child.genome.json`（基因組）、`child.morph.json` 與 `child.skin.npz`（形體包）、`run.json`（所有檢查的結果）。

**PASS 的意思：** 子代是一個封閉的身體、通過身體檢查，而且形體包的動作測試（權重總和為 1、只轉一個部位時動到的頂點幾乎都在該部位內）通過。

2026-11-16 搬進專區之後在你的電腦上重跑過：PASS，6 秒。

## 六、其他腳本

| 腳本 | 做什麼 |
|---|---|
| `skeleton_sdf_demo.py` | 基因組、距離場、取網格、網格檢查（核心） |
| `form_fusion_lab.py` | 六種形體、配對、遺傳規則、擁擠指標（核心） |
| `soft_match_lab.py` | 機率配對 |
| `rtis_run_once.py` | 完整流程跑一次 |
| `part_interface.py` | 形體包 |
| `attribute_layer.py`、`attr_eval.py` | 部位屬性層與它的評估 |
| `pce_match_test.py` | 配對測試 |
| `bead_fix_lab.py` | 念珠（多餘隆起）的五種修法 |
| `crowd_fix_lab.py` | 擁擠的四種修法 |
| `reach_audit.py`、`surject_audit.py` | 遺傳組合能到哪裡（滿射的檢查） |
| `replay_export.py`、`replay_build.py`、`replay_template.html` | 生成過程的重播網頁 |
| `fourier3d_demo.py`、`fourier_genetics.py` | 上一版（傅立葉管）；現行程式還會用到裡面幾個函式，不要刪 |

## 六之二、哪些公式是外面現成的、哪些是這個專案自己的

**外面現成的（論文裡要引用出處）**

| 用在哪裡 | 公式／方法 | 出處 | 程式位置 |
|---|---|---|---|
| 每根骨頭的形狀 | 兩端半徑不同的圓錐（round cone）的精確距離公式 | Inigo Quilez 的 `sdRoundCone` | `skeleton_sdf_demo.sd_round_cone` |
| 部位之間的融合 | 平滑聯集：g = −log Σ exp(−d / k)（指數式的平滑最小值） | 圖學裡通用的 smooth minimum | `skeleton_sdf_demo.build_field` |
| 從距離場取出網格 | marching cubes | Lorensen & Cline 1987；用的是 scikit-image 的實作 | `skeleton_sdf_demo.extract_mesh` |
| 沿骨頭的截面不亂扭 | 旋轉最小化標架（雙反射法） | Wang, Jüttler, Zheng & Liu 2008 | `fourier3d_demo.rotation_minimizing_frames` |
| 截面輪廓 | 用傅立葉級數描述封閉曲線（舊版用橢圓傅立葉） | Kuhl & Giardina 1982 | `skeleton_sdf_demo`、`fourier3d_demo` |
| 部位相似度 | Jaccard 相似度 | 標準做法；層級權重 0.5／1／2 是本專案定的 | `rtis\pce.py` |

出處的完整書目還沒有逐一核對，寫論文時要查原文。

**這個專案自己的**
- 骨架基因組的設計（哪些東西是基因、怎麼分部位、鏡射與放射）。
- 三層標籤與權重、機率式的配對門檻（0.40／0.25）。
- 遺傳規則：整個基因來自一方、連鎖、相對基因、嫁接、位置規則，以及它們的組合順序。
- 把這些接成「兩個不同形體 → 一個封閉、可追溯的子代」的完整流程，還有形體包。

用現成的公式長出形狀是正常做法；這個專案的價值在「怎麼遺傳」和「整套流程」，不在距離公式。

## 七、現在知道的限制

- 有水母的配對：15 組裡 3 組失敗，都是其他親代的頭和腿埋進鐘形體。
- 做不到中空與左右彎的身體；部位很簡單（沒有腳掌、手指、花紋）。
- 遺傳組合不是滿射（二足 × 蜘蛛的腳只會是 2 或 8 隻）。
- 位置規則的輸家整個消失。
- 匯出格點下每隻約 4.5–5.4 秒（雲端計時）。
- **證據還不夠：** 幾乎所有數字都只在雲端、用小測試組量過；沒有對照組與統計。見 `RTIS_數據總表.md`。

## 八、專區裡的文件，依閱讀順序

| 文件 | 內容 |
|---|---|
| `RTIS_11月版本_系統說明.md` | 本文件 |
| `RTIS_新論文大綱.md` | 論文要主張什麼、需要哪些實驗 |
| `RTIS_實驗計畫_v1.md` | 正式實驗的計畫（等你確認後凍結；v0 已被取代，保留作紀錄） |
| `RTIS_數據總表.md` | 每一個數字與它的可信度（第一節是 11 月版本，第二節是舊版本） |
| `RTIS_實驗歷程.md` | 11-09 起每一步做了什麼 |
| `RTIS_遺傳與幾何企劃.md` | 設計的理由（含你原本的想法） |
| `RTIS_形體實驗與無對應融合.md` | 11-13、11-14 的詳細結果 |
| `RTIS_ATMS_部位接口.md` | 形體包的格式 |
| `RTIS_滿射審判判決.md` | 滿射提案的審判（擱置） |
