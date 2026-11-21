# RTIS 專案文件總索引（2026-11-16）

**先讀這份。** 文件分成三區，用標題開頭的標記區分：

| 標記 | 意思 |
|---|---|
| **【11 月版本】** | 現在的版本（骨架＋隱式曲面），論文要講的就是它。要改、要看，都在這一區 |
| 【整個專案】 | 跨版本的文件：索引、現況、歷程、待辦 |
| 【舊版本】 | v1、RTISV2、5 月的論文、4 月的文件與程式快照。只當歷史，不要修改 |

硬碟上，11 月版本的所有東西都在 `D:\ai-research-lab\RTIS\current_2026-11\`（2026-11-16 建立）。

文件之間有衝突時：先信【11 月版本】，再信【整個專案】，最後才是【舊版本】。

---

## 一、【11 月版本】專區

依閱讀順序。硬碟位置：`RTIS\current_2026-11\docs\`。

| Project 裡的文件 | 內容 | 什麼時候讀 |
|---|---|---|
| `claude/RTIS_11月版本_系統說明.md` | **這個版本是什麼、八步流程、基因組、怎麼跑、專區的資料夾** | 一開始；要向別人說明時 |
| `claude/RTIS_新論文大綱.md` | **論文唯一的主張**（第一節）、各版本主張的對照、貢獻、章節、需要的實驗、後續工作 | 想知道論文要寫什麼 |
| `claude/RTIS_實驗計畫_v1.md` | **正式實驗的計畫**（11-16；依 ChatGPT 的審查與你的三個決定改寫；規約與程式都已凍結） | 要跑實驗之前 |
| `claude/RTIS_實驗結果_v1.md` | **正式實驗 X1、X2 的結果**（11-16；等 ChatGPT 獨立比對） | 要知道實驗跑出什麼 |
| `claude/RTIS_實驗計畫_v0.md` | 計畫的第一版，已被 v1 取代，保留作紀錄 | 查 v0 到 v1 改了什麼 |
| `claude/RTIS_數據總表.md` | 每一個數字、原始檔在哪、可信度。第一、三節是 11 月版本，第二節是舊版本 | 要引用數字之前 |
| `claude/RTIS_實驗歷程.md` | 11-09 起每一步做了什麼，含失敗與錯誤 | 查某個實驗 |
| `claude/RTIS_遺傳與幾何企劃.md` | 設計的理由（含你原本的想法與前兩版） | 查為什麼這樣設計 |
| `claude/RTIS_形體實驗與無對應融合.md` | 11-13、11-14 的詳細結果 | 查詳細數字 |
| `claude/RTIS_ATMS_部位接口.md` | 給動作系統的形體包格式 | 接動作系統時 |
| `claude/RTIS_滿射審判判決.md` | 滿射提案的審判（結果：擱置） | 想重啟滿射時 |
| `claude/RTIS_未來方向_3D資料轉基因組.md` | 你提出的未來方向：把 3D 模型、骨骼轉成基因組；各種資料的可行性與定位（不是這篇論文的主張） | 想做下一階段時 |

**只在硬碟、不在 Project 的專區內容**

| 位置（都在 `RTIS\current_2026-11\` 底下） | 內容 |
|---|---|
| `README.md` | 專區的地圖 |
| `code\` | 16 個腳本＋重播範本 |
| `results\local\` | 在你的電腦上跑的結果 |
| `results\cloud_2026-11\` | 11 月在雲端跑的原始結果 |
| `experiments\` | 正式實驗的腳本與 CSV（計畫凍結後才會有） |
| `paper\` | 新論文（還沒開始） |
| `handoff\` | 給 Gemini、ChatGPT 的任務說明與檔案包；`handoff\chatgpt_shared\` 是可以開放給 ChatGPT 的資料夾，它的產出在裡面的 `outbox\`（11-16：v0 的審查結論、樣本數分析） |

另外：「RTIS 生成重播」網頁 https://claude.ai/artifact/Kkc44JJUdDzWm32YHz7WDw

## 二、【整個專案】

硬碟位置：`RTIS\docs\`。

| 文件 | 內容 | 什麼時候讀 |
|---|---|---|
| `claude/00_RTIS_總索引.md` | 本文件 | 一開始 |
| `claude/RTIS_專案歷程與紀錄.md` | 2025 年底到現在的時間軸、每個版本為什麼換掉、決定的紀錄、出過的錯與作廢的數字、名詞表 | 寫論文的思路歷程；查某個詞 |
| `claude/RTIS_待辦與未決事項.md` | 所有待辦；各節標了【11 月版本】或【舊版本】 | 想知道接下來做什麼 |
| `claude/RTIS_現況總覽_20261115.md` | 資料夾位置；5 月那份論文的狀態；論文以外的舊實驗 | 找東西在哪裡 |
| `RTIS_參考論文清單.md` | 7 篇已引用＋7 篇建議引用，含 BibTeX（4 月整理；沒有 2025–2026 的新文獻） | 寫相關研究時 |

## 三、【舊版本】（保留，不修改，不要當成現況）

**舊版本的說明**

| 文件 | 內容 |
|---|---|
| `claude/RTIS_舊版本系統說明_v1與RTISV2.md` | v1 與 RTISV2 怎麼運作（由六份 4–5 月的文件合併，並與硬碟上的程式核對）。原本叫「系統說明_現行版」，11-16 改名 |

**4–5 月的文件**（硬碟：`RTIS\docs\old_2026-04_to_06\`）

| 文件 | 日期 | 過時的地方 |
|---|---|---|
| `RTIS_概念文件.md` | 04-20 | v1 的 n = 30 數字已作廢；目標 CoG 2026；路徑是搬移前的 |
| `RTIS_架構文件.md` | 04-17 | 比概念文件更早 |
| `RTIS_總整理.md` | 04-18 | 論文 674 行、評分 3/10、v1 n = 30 數字；PCE 例子寫 0.5（正確 0.333） |
| `RTIS_進度整理.md` | 04-18 | 四月的進度 |
| `RTIS_使用者待辦清單.md` | 04-17 | 目標 CoG 2026；買模型與 Colab 已不需要 |
| `RTIS_專案結構整理.md` | 04-17 | 資料夾結構是搬移前的 |
| `RTIS_思路歷程.md` | 04-17 | 內容已併入專案歷程與紀錄；PCE 例子的 0.67 是錯的 |
| `RTIS_交接文件_20260521.md` | 05-21 | 程序性骨骼路線之後又變了兩次 |
| `pce_vs_nopce_with_sd.md`（兩份，重複） | 04 月 | v1 的 n = 10 結果 |

**副線**（與 RTIS 研究主線無關或關係間接）

| 文件 | 內容 |
|---|---|
| `數位大腦_技術文件.md`、`RTIS_技術差距分析.md` | 知識圖譜視覺化的技術筆記與差距分析 |
| `PLAN.md` | VS Code 擴充套件的計畫（宇宙網視覺化的副線） |
| `brain_graph.html`（兩份，重複） | 4 月產生的知識圖譜網頁 |
| `Flutter_CleanArchitecture_任務文件.md` | Flutter 的學習筆記，**與 RTIS 無關** |

**程式快照**（2026-04-24 上傳，全部是 v1 的舊版；現行的 v1 程式在硬碟 `RTIS\rtis\`）

| 類別 | 檔案 |
|---|---|
| 核心 | `trait.py`、`genome.py`、`pce.py`、`ontology.py`、`evolution.py`、`pruning.py`、`metrics.py`、`experiment.py` |
| 發育與細胞 | `morphogen.py`、`cell_recipe.py`、`development.py`、`cell_recipe_test.json` |
| 幾何 | `geometry_gene.py`、`lsystem_expander.py`、`organ_generator.py`、`organ_defs.py` |
| LLM | `ai_mutation.py`、`ai_morph_judge.py`、`agent_bridge.py` |
| 輸入 | `model_parser.py`、`model_parser_enhanced.py` |
| 視覺化 | `body3d.py`、`fusion3d.py`、`ancestry_tree.py`、`brain_graph.py`、`visualize.py`、`timeline.py` |
| 網頁與紀錄 | `app.py`、`hub_app.py`、`hub.html`、`data_logger.py` |

注意：這些快照裡的 `pce.py`、`ontology.py` 是 4 月的版本。11 月版本用的是硬碟 `RTIS\rtis\` 裡的現行檔案，**11 月版本的程式不在 Project 裡**。

**硬碟上的舊版本**

| 位置 | 內容 |
|---|---|
| `RTIS\rtis\` | v1 完整系統 |
| `RTIS\RTISV2\` | 5 月的受控實驗（n = 30 的結果在這裡） |
| `RTIS\outputs\paper\` | 5 月的論文 |
| `RTIS\archive\` | 舊備份 |

## 四、可以刪除的候選（沒有刪）

- `pce_vs_nopce_with_sd.md` 的其中一份、`brain_graph.html` 的其中一份（重複）。
- `Flutter_CleanArchitecture_任務文件.md`（與 RTIS 無關）。
