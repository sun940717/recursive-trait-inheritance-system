# 【11 月版本】程式 / November-version code

2026-11-16：這個資料夾原本叫 `b_zone_geometry`，現在是 `RTIS\current_2026-11\code\`。
真正的 `pce.py`、`ontology.py`、`trait.py` 在 `RTIS\rtis\`，用 PYTHONPATH 指過去（不要複製）：

    cd D:\ai-research-lab\RTIS\current_2026-11\code
    $env:PYTHONPATH = "..\..\rtis"
    python rtis_run_once.py --out ..\results\local\out_run

下面是 11-15 的原始說明（指令相同，只有資料夾位置不同）。

---

# RTIS geometry + inheritance prototypes (2026-11-15)

Put these files in your RTIS folder, next to the real `pce.py`, `ontology.py` and `trait.py`
(do not copy those three from anywhere else; the scripts import yours).
把這些檔案放進你的 RTIS 資料夾，跟你真正的 `pce.py`、`ontology.py`、`trait.py` 放在一起。

Python 3.10.12, then / 然後：

    pip install numpy scipy scikit-image matplotlib
    python rtis_run_once.py                       # one full run: biped x spider, seed 7
    python rtis_run_once.py --a quadruped --b jellyfish   # one of the known failures

Expected for the first command / 第一個指令的預期結果：
the last line says **PASS**, and `out_run/biped_x_spider_seed7/` holds run_report.md, run_overview.png and
the morphology package (child.morph.json, child.skin.npz, child.obj, child.state.json, child.genome.json).
In the cloud run the child had 5 parts, 52% of its genes from the biped, 13,492 triangles.
最後一行是 PASS；雲端跑出來的子代有 5 個部位、52% 基因來自二足、13,492 個三角形。

Other scripts / 其他程式：
- `part_interface.py`  exports the morphology package for the six founders + one child / 匯出形體包
- `pce_match_test.py`, `soft_match_lab.py`, `crowd_fix_lab.py`  the matching and crowding experiments / 配對與擁擠實驗

Replay page / 重播頁面:

    python rtis_run_once.py --a biped --b spider --seed 7
    python replay_export.py --a biped --b spider --seed 7     # -> replay_data.json
    python replay_build.py                                    # -> rtis_replay.html (open in a browser)

Part-attribute layer (off by default) / 部位屬性層（預設關閉）:

    python rtis_run_once.py --a biped --b spider --attributes
    python attr_eval.py                 # off versus on, and the leg outcomes -> out_attr_eval/
