# results_cloud_2026-11

2026-11-09 到 11-15 在雲端跑的所有實驗的結果檔，2026-11-15 從雲端工作區複製過來。
每個數字對應哪個檔案，見 `RTIS\docs\RTIS_數據總表.md`。

| 資料夾 | 內容 | 產生它的腳本 |
|---|---|---|
| `logs\` | 執行時印出的表格（`run.log` 是傅立葉示範；其餘依名稱） | — |
| `out\` | 3D 傅立葉示範的圖與生物的 JSON | `fourier3d_demo.py` |
| `out_genetics\`、`out_genetics_band\`、`out_genetics_blend\` | 傅立葉基因組的三種交配模式 | `fourier_genetics.py` |
| `out_sdf\` | 骨架＋隱式曲面的示範 | `skeleton_sdf_demo.py` |
| `out_fusion\` | 六種形體、四種融合規則、場混合基準 | `form_fusion_lab.py` |
| `out_beads\` | 念珠問題的五種做法 | `bead_fix_lab.py`（在 `scripts_not_in_bundle\`） |
| `out_pce\` | PCE 配對測試 | `pce_match_test.py` |
| `out_soft\`、`out_soft_310\` | 機率配對（`_310` 是用 Python 3.10.12 與真正的 pce.py 重跑） | `soft_match_lab.py` |
| `out_crowd\`、`out_crowd_310\` | 擁擠問題的四種修法 | `crowd_fix_lab.py` |
| `out_interface_v02\` | 形體包 v0.2（七個身體） | `part_interface.py` |
| `out_run_all\` | 15 組各跑一次完整流程（屬性層關閉） | `rtis_run_once.py` |
| `out_attr\` | 同上，屬性層開啟 | `rtis_run_once.py --attributes` |
| `out_attr_eval\` | 屬性層開與關的比較（6 個種子 × 15 組） | `attr_eval.py` |
| `out_reach\` | 遺傳組合的範圍（三對親代各 1,000 次） | `reach_audit.py`（在 `scripts_not_in_bundle\`） |
| `scripts_not_in_bundle\` | 原本只在雲端的腳本：`bead_fix_lab.py`、`surject_audit.py`、`reach_audit.py`、`checks\` | — |
| `web_workbench_source\` | 瀏覽器「生成實作台」的原始碼（不含參考資料檔） | — |

不含 3D 模型檔（.obj、.npz）；重跑腳本就會產生。
`scripts_not_in_bundle\` 裡的腳本要和 `b_zone_geometry\` 的腳本放在同一個資料夾才能執行。
這些結果都只在雲端跑過（等級 B 或 C），用在論文之前要在本機重跑。
