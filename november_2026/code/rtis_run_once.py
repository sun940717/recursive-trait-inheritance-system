#!/usr/bin/env python3
"""
rtis_run_once.py
================
One full run of the adopted pipeline, from two parents to a body a motion system can move.
用已採用的整套規則跑一次完整流程：從兩個親代，到一個動作系統可以操作的身體。

Stages / 階段:
  0. environment        Python version, which pce.py / ontology.py are used / 環境
  1. parents            two founder forms, ontology tags / 兩個原始形體（ontology 標籤）
  2. matching           PCE score per pair of parts: >= 0.40 always, 0.25-0.40 by chance, < 0.25 never
                        每對部位的 PCE 分數：0.40 以上一定配、0.25–0.40 依機率、0.25 以下不配
  3. inheritance        each gene whole from one parent, relative genes, linkage 1, grafting, site rule
                        每個基因整個來自一方、相對基因、連鎖 1、嫁接、位置規則
  4. body               skeleton + implicit surface + Fourier detail -> one closed mesh, with checks
                        骨架＋隱式曲面＋傅立葉細節 -> 一個封閉網格，並檢查
  5. handoff            morphology package (read-only, with lineage) + default ATMS state package
                        形體包（唯讀、含血緣）＋ ATMS 預設狀態包
  6. motion test        the package is read back from disk and posed (test only, not ATMS)
                        從檔案讀回形體包並擺姿勢（只是測試，不是 ATMS）

Not in this run / 這次沒有跑的: mutation (the Claude mutation step of the main RTIS pipeline), the RTIS
state machine (a default state package is written instead), feet / digits / skin / hair.

Requires, in the same folder: fourier3d_demo.py, fourier_genetics.py, skeleton_sdf_demo.py,
form_fusion_lab.py, soft_match_lab.py, pce_match_test.py, part_interface.py, and RTIS's pce.py,
ontology.py, trait.py. Target: Python 3.10.12 · numpy, scipy, scikit-image, matplotlib.
需要同資料夾的上述檔案，以及 RTIS 的 pce.py、ontology.py、trait.py。

Outputs (default ./out_run/<a>_x_<b>_seed<seed>/) / 輸出:
  run_report.md                  every stage in words and numbers / 每個階段的文字與數字
  run.json                       the same, machine-readable / 同上，給程式讀
  run_overview.png               parents, child (colour = ancestry), child posed (colour = part)
  child.morph.json / .skin.npz / .obj     the morphology package / 形體包
  child.state.json               default ATMS state package (rtis_interface.md, "Default Behavior")
  child.genome.json              the child's genome / 子代的基因組

Usage / 用法:
  python rtis_run_once.py
  python rtis_run_once.py --a quadruped --b crab --seed 3
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import fourier3d_demo as fd  # noqa: E402
import skeleton_sdf_demo as sk  # noqa: E402
import form_fusion_lab as lab  # noqa: E402
import soft_match_lab as soft  # noqa: E402
import part_interface as pi  # noqa: E402
import pce  # noqa: E402
import ontology  # noqa: E402

RULES_TEXT = [
    "tags: RTIS ontology.py (cell / organ / part layers)",
    "matching: PCE layered similarity; >= 0.40 always, 0.25-0.40 chance (score - 0.25) / 0.15, < 0.25 never",
    "each gene copied whole from one parent (alpha 0.5)",
    "relative genes (size gene; lengths and radii as fractions; lean and bends relative to the parent)",
    "linkage: 1 switch point per crossed part",
    "grafting: a part whose parent is missing attaches where that parent would have been",
    "site rule: two unmatched limbs in one place compete; only one stays",
    "geometry: skeleton + implicit surface + Fourier cross-section detail",
]
FORMS = ("quadruped", "biped", "spider", "serpent", "jellyfish", "crab")


def describe_part(p) -> str:
    return f"{p.name:<14} {sk.arrangement(p):<7} {p.n_bones} bones   tags {', '.join(p.tags)}"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="One full run of the adopted RTIS geometry + inheritance pipeline")
    ap.add_argument("--a", default="biped", choices=FORMS, help="parent A / 親代 A")
    ap.add_argument("--b", default="spider", choices=FORMS, help="parent B / 親代 B")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--voxel", type=float, default=0.02, help="export grid / 匯出格點")
    ap.add_argument("--out", default="out_run")
    ap.add_argument("--attributes", action="store_true",
                    help="turn on the part-attribute layer (off by default) / 開啟部位屬性層（預設關閉）")
    args = ap.parse_args(argv)
    if args.a == args.b:
        ap.error("pick two different forms / 請選兩種不同的形體")
    out = Path(args.out) / f"{args.a}_x_{args.b}_seed{args.seed}{'_attr' if args.attributes else ''}"
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    run: dict = {"parents": [args.a, args.b], "seed": args.seed, "voxel": args.voxel, "rules": RULES_TEXT}
    md: list[str] = [f"# RTIS run: {args.a} x {args.b}, seed {args.seed}", ""]
    t_all = time.perf_counter()

    def say(text: str = "") -> None:
        print(text)
        md.append(text)

    # ---- 0. environment / 環境 ----------------------------------------------------------------------------
    env = {"python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform(),
           "pce.py": str(Path(pce.__file__).resolve()), "ontology.py": str(Path(ontology.__file__).resolve())}
    run["environment"] = env
    say("## 0. Environment / 環境")
    say("")
    for k, v in env.items():
        say(f"- {k}: `{v}`")
    if env["python"] != "3.10.12":
        say(f"- note: the project's target is Python 3.10.12; this run used {env['python']}")
    say("")

    # ---- 1. parents / 親代 -------------------------------------------------------------------------------
    forms = lab.all_forms(ontology_tags=True)
    ga, gb = sk.with_ancestry(forms[args.a], 1.0), sk.with_ancestry(forms[args.b], 0.0)
    unknown = sorted({t for g in (ga, gb) for p in g.parts for t in ontology.get_ontology().validate_tags(p.tags)[1]})
    run["unknown_tags"] = unknown
    say("## 1. Parents / 親代")
    say("")
    for label, name, g in (("A", args.a, ga), ("B", args.b, gb)):
        say(f"**{label}: {name}** ({len(g.parts)} parts, {sum(p.gene_count() for p in g.parts)} genes)")
        say("```")
        for p in g.parts:
            say(describe_part(p))
        say("```")
    say(f"Tags not in ontology.py: {unknown or 'none'}")
    say("")

    # ---- 2. matching / 配對 --------------------------------------------------------------------------------
    pairs, decisions = soft.soft_match(ga, gb, rng, "soft")
    attr, exclude = None, set()
    if args.attributes:
        import attribute_layer
        attr = attribute_layer.AttributeLayer(np.random.default_rng([args.seed, 101]))
        pairs, exclude = attr.plan(ga, gb, pairs)
        run["attribute_layer"] = attr.log
    names_a, names_b = {p.name for p in ga.parts}, {p.name for p in gb.parts}
    unmatched_a = sorted(names_a - {pr["a"] for pr in pairs})
    unmatched_b = sorted(names_b - {pr["b"] for pr in pairs})
    run["matching"] = {"pairs": pairs, "borderline_decisions": decisions,
                       "unmatched_a": unmatched_a, "unmatched_b": unmatched_b}
    say("## 2. Matching / 配對")
    say("")
    say("| A | B | PCE score | how |")
    say("|---|---|---|---|")
    for pr in pairs:
        say(f"| {pr['a']} | {pr['b']} | {pr['score']:.3f} | {pr['how']} |")
    say("")
    if decisions:
        say("Borderline pairs (decided by chance in this mating) / 邊界配對：")
        for d in decisions:
            say(f"- {d['a']} ~ {d['b']}: score {d['score']:.3f}, chance {d['chance']:.0%} -> "
                f"{'matched' if d['matched'] else 'not matched'}")
    else:
        say("No borderline pairs for these parents. / 這對親代沒有邊界配對。")
    say(f"Unmatched in A: {', '.join(unmatched_a) or 'none'}; unmatched in B: {', '.join(unmatched_b) or 'none'}")
    say("")

    # ---- 3. inheritance / 遺傳 -----------------------------------------------------------------------------
    cfg = sk.SkeletonInheritanceConfig(micro_budget=0)
    child, log = lab.fuse(ga, gb, rng, cfg, lab.ADOPTED, pairs=pairs, exclude=exclude, attr=attr)
    origin = {}
    for key, cname in log["sources"].items():
        origin.setdefault(cname, []).append(key)
    share = lab.ancestry_share(child)
    run["inheritance"] = {"parts": [p.name for p in child.parts], "origin": origin,
                          "ancestry_a_per_part": {p.name: p.meta.get("ancestry_a") for p in child.parts},
                          "ancestry_a_overall": share, "grafted": log["grafted"],
                          "not_inherited": log["not_inherited"], "lost_to_site_rule": log["site_lost"],
                          "orphans_dropped": log["orphans_dropped"],
                          "new_humps": [int(x) for x in log["extra_beads"]],
                          "new_bend_deg": [float(x) for x in log["extra_bend"]]}
    say("## 3. Inheritance / 遺傳")
    say("")
    say("| child part | from | share of genes from A | parent part |")
    say("|---|---|---|---|")
    for p in child.parts:
        src = ", ".join(origin.get(p.name, ["?"]))
        say(f"| {p.name} | {src} | {p.meta.get('ancestry_a', 0.5):.0%} | {p.parent or '(root)'} |")
    say("")
    say(f"- genes from A overall: {share:.0%}; from B: {1 - share:.0%}")
    say(f"- not inherited (peripheral parts left out by chance): {log['not_inherited']}")
    say(f"- grafted: {log['grafted']}; lost to the site rule: {log['site_lost']}; dropped orphans: {log['orphans_dropped']}")
    say(f"- crossed parts with new humps: {sum(x > 0 for x in log['extra_beads'])} of {len(log['extra_beads'])}")
    say("")
    if attr is not None:
        say("**Part-attribute layer (on) / 部位屬性層（開啟）**")
        say("")
        for st in attr.log["sets"]:
            say(f"- limb set {', '.join(st['a'])} ~ {', '.join(st['b'])}: count and placement from {st['count_from']} "
                f"({st['count']} parts in the set), attributes from "
                + ", ".join(f"{k} {v}" for k, v in st["attributes_from"].items()))
        for nm, d in attr.log["parts"].items():
            src = d["from"] if isinstance(d["from"], str) else ", ".join(f"{k} {v}" for k, v in d["from"].items())
            say(f"- {nm}: {src}; reach beyond the surface {d['result']['length']:.3f}, thickness "
                f"{d['result']['thickness']:.3f} (body-size units)")
        for sk_ in attr.log["skipped"]:
            say(f"- {sk_['part']}: kept the existing rules ({sk_['why']}; long x round is on the to-do list)")
        say("")
    (out / "child.genome.json").write_text(json.dumps(
        [{"name": p.name, "parent": p.parent, "attach": float(p.attach), "tags": list(p.tags),
          "arrangement": sk.arrangement(p), "is_core": bool(p.is_core), "blend": float(p.blend),
          "offsets": np.round(p.offsets, 6).tolist(), "radii": np.round(p.radii, 6).tolist(),
          "ancestry_a": p.meta.get("ancestry_a")} for p in child.parts], indent=1), encoding="utf-8")

    # ---- 4. body / 身體 ------------------------------------------------------------------------------------
    t0 = time.perf_counter()
    mesh, face_piece, pieces = sk.build_sdf_creature(child, args.voxel)
    rep = sk.mesh_report(mesh)
    outer, bubbles = lab.shells(mesh)
    crowd = lab.crowding(child)["swallowed"]
    body = {"closed": bool(rep["closed"]), "outer_shells": int(outer), "bubbles": int(bubbles),
            "triangles": int(len(mesh.faces)), "volume": float(fd.signed_volume(mesh)),
            "swallowed_limbs": [list(k) for k in crowd], "seconds": time.perf_counter() - t0}
    body_checks = {"closed mesh": body["closed"], "one outer shell": outer == 1,
                   "no limb swallowed by another limb": not crowd}
    body["failed_checks"] = [k for k, v in body_checks.items() if not v]
    body["ok"] = not body["failed_checks"]
    run["body"] = body
    say("## 4. Body / 身體")
    say("")
    say(f"- closed mesh: {'yes' if body['closed'] else 'NO'}; outer shells: {outer}; sealed bubbles: {bubbles}")
    say(f"- triangles: {body['triangles']:,}; volume: {body['volume']:.4f}; built in {body['seconds']:.1f} s")
    say(f"- swallowed limbs: {', '.join(' + '.join(k) for k in crowd) or 'none'}")
    say(f"- result: {'PASS' if body['ok'] else 'FAIL: ' + '; '.join(body['failed_checks'])}")
    say("")

    # ---- 5. handoff / 交接 ---------------------------------------------------------------------------------
    lineage = {"generation": 1, "parents": [args.a, args.b], "seed": args.seed, "rules": RULES_TEXT,
               "matched_pairs": [[pr["a"], pr["b"]] for pr in pairs]}
    package, skin = pi.build_package(child, args.voxel, "child", lineage)
    pi.write_package(package, skin, out)
    state = {"state_id": "default", "state_phase": 0.0, "intent_vector": [0.5, 0.5, 0.5, 0.5],
             "constraint_profile_id": "balanced", "morphology_package": package["files"]["skin"].replace(".skin.npz", ".morph.json"),
             "note": "RTIS state logic is not connected yet; these are the defaults from ATMS rtis_interface.md v0.1"}
    (out / "child.state.json").write_text(json.dumps(state, indent=1), encoding="utf-8")
    package, skin = pi.load_package(out, "child")           # from here on, only what is on disk / 之後只用檔案裡的
    n = package["counts"]
    run["handoff"] = {"counts": n, "groups": package["groups"], "access": package["access"],
                      "files": sorted(f.name for f in out.iterdir() if f.name.startswith("child."))}
    say("## 5. Handoff / 交接")
    say("")
    say(f"- morphology package v{package['version']}: {n['parts']} parts, {n['nodes']} nodes, {n['bones']} bones, "
        f"{n['edges']} edges, {n['vertices']:,} vertices; access: {package['access']['motion_system']}")
    say(f"- groups: {', '.join(sorted(package['groups']))}")
    say(f"- files: {', '.join(run['handoff']['files'])}")
    say("")

    # ---- 6. motion test / 動作測試 --------------------------------------------------------------------------
    c = pi.checks(package, skin)
    limbs = pi.resolve(package, "tag:limb") if "tag:limb" in package["groups"] else []
    motion = {**c, "bones_in_tag_limb": len(limbs)}
    no_surface = [p["name"] for p in package["parts"] if p["vertices"] == 0]
    motion_checks = {
        "weights sum to 1": c["weights_sum_error"] < 1e-9,
        "rest pose reproduces the mesh": c["rest_pose_error"] < 1e-9,
        "every part has a visible surface" + (f" (none: {', '.join(no_surface)})" if no_surface else ""): not no_surface,
        "turning one part moves mostly that part (> 90%)":
            c["one_part_moved"] is None or c["one_part_moved"]["share_in_that_part"] > 0.9}
    motion["failed_checks"] = [k for k, v in motion_checks.items() if not v]
    motion["ok"] = not motion["failed_checks"]
    run["motion_test"] = motion
    say("## 6. Motion test (not ATMS) / 動作測試（不是 ATMS）")
    say("")
    say(f"- weights sum to 1 (largest error {c['weights_sum_error']:.1e}); rest pose reproduces the mesh "
        f"(largest error {c['rest_pose_error']:.1e})")
    say(f"- parts with vertices: {c['parts_with_vertices']} / {n['parts']}; bones with vertices: "
        f"{c['bones_with_vertices']} / {n['bones']}")
    if c["one_part_moved"]:
        say(f"- turning only {c['one_part_moved']['bone']}: {c['one_part_moved']['share_in_that_part']:.1%} of the "
            "vertices that moved belong to that part (and what hangs from it)")
    say(f"- `tag:limb` addresses {len(limbs)} bones")
    say(f"- demo pose: volume change {c['demo_pose_volume_change']:+.1%}, flipped faces {c['demo_pose_flipped_faces']:.2%}")
    say(f"- result: {'PASS' if motion['ok'] else 'FAIL: ' + '; '.join(motion['failed_checks'])}")
    say("")

    # ---- figure / 圖 ----------------------------------------------------------------------------------------
    fig = plt.figure(figsize=(18, 7.2))
    fig.suptitle(f"RTIS run: {args.a} x {args.b}, seed {args.seed}", fontsize=14)
    palette = plt.get_cmap("tab10")(np.arange(10))[:, :3]
    top = [(f"A: {args.a}", ga), (f"B: {args.b}", gb), ("child (colour = ancestry: orange A, blue B)", child)]
    for i, (title, g) in enumerate(top):
        ax = fig.add_subplot(2, 3, i + 1, projection="3d")
        m, fp, pcs = sk.build_sdf_creature(g, 0.03 if g is not child else args.voxel)
        sk.draw_mesh(ax, m, sk.ancestry_colours(g, pcs, fp), title, light=(0.5, -0.6, 0.7))
        ax.view_init(elev=18, azim=-58)
    for i, ph in enumerate((None, 1.0, 3.0)):
        ax = fig.add_subplot(2, 3, 4 + i, projection="3d")
        verts = skin["vertices"] if ph is None else pi.pose(package, skin, pi.demo_tokens(package, ph))
        sk.draw_mesh(ax, fd.Mesh(verts, skin["faces"].astype(np.int64)), palette[skin["face_part"] % 10],
                     "child from the package, rest (colour = part)" if ph is None else f"posed from the package, phase {ph}",
                     light=(0.5, -0.6, 0.7))
        ax.view_init(elev=18, azim=-58)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.9, bottom=0.0, wspace=0.0, hspace=0.1)
    fig.savefig(out / "run_overview.png", dpi=90)
    plt.close(fig)

    run["seconds"] = time.perf_counter() - t_all
    run["ok"] = bool(body["ok"] and motion["ok"])
    say("## Result / 結果")
    say("")
    say(f"**{'PASS' if run['ok'] else 'FAIL'}** in {run['seconds']:.0f} s. Output folder: `{out}`")
    (out / "run_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "run.json").write_text(json.dumps(run, indent=1, default=float), encoding="utf-8")
    sys.exit(0 if run["ok"] else 1)


if __name__ == "__main__":
    main()
