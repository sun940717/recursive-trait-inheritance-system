#!/usr/bin/env python3
"""
replay_export.py
================
Runs the adopted pipeline once (the same steps and seed as rtis_run_once.py) and records everything the
replay page needs to redraw the process: the Fourier fit of the original idea, both parents, the
matching, which parent each gene came from, the skeleton, the skin at several stages of growth, the
cross-section outlines as epicycles, and the finished morphology package.
用已採用的規則跑一次（步驟與種子和 rtis_run_once.py 相同），把重播頁面需要的東西都記下來。

Requires the same files as rtis_run_once.py, and that rtis_run_once.py has been run for the same pair
and seed (the package is read from its output folder).
需要與 rtis_run_once.py 相同的檔案，並且要先用同樣的親代與種子跑過 rtis_run_once.py。

Usage / 用法:
  python rtis_run_once.py --a biped --b spider --seed 7
  python replay_export.py --a biped --b spider --seed 7      # -> replay_data.json
"""

from __future__ import annotations

import argparse
import base64
import dataclasses
import json
import platform
from pathlib import Path

import numpy as np

import fourier3d_demo as fd
import skeleton_sdf_demo as sk
import form_fusion_lab as lab
import soft_match_lab as soft
import pce


def b64(arr: np.ndarray, dtype) -> str:
    return base64.b64encode(np.ascontiguousarray(arr, dtype=dtype).tobytes()).decode("ascii")


def pack_mesh(mesh, vertex_value: np.ndarray, value_dtype=np.uint8) -> dict:
    return {"v": b64(mesh.vertices, np.float32), "f": b64(mesh.faces, np.uint32),
            "c": b64(vertex_value, value_dtype), "nv": int(len(mesh.vertices)), "nf": int(len(mesh.faces))}


def vertex_from_faces(n_vertices: int, faces: np.ndarray, face_value: np.ndarray) -> np.ndarray:
    out = np.zeros(n_vertices, dtype=face_value.dtype)
    for k in range(3):
        out[faces[:, k]] = face_value
    return out


def pieces_json(pieces, part_index: dict) -> list:
    out = []
    for pc in pieces:
        segs = pc["segments"]
        joints = [segs[0].a] + [s.b for s in segs]
        radii = [segs[0].ra] + [s.rb for s in segs]
        out.append({"part": pc["gene"], "pi": part_index[pc["gene"]], "copy": pc["name"][len(pc["gene"]) + 1:],
                    "joints": np.round(np.array(joints), 5).tolist(), "radii": np.round(radii, 5).tolist()})
    return out


def epicycles(detail0, detail1, s: float = 0.5, samples: int = 512, keep: float = 1e-5) -> dict:
    """The cross-section outline z(angle) = m(angle) e^{i angle} as rotating circles (complex Fourier
    series). The polar series has 7 rows (n = 0..6), so at most 13 circles describe it exactly.
    截面輪廓寫成旋轉的圓（複數傅立葉級數）。極座標級數有 7 列，所以最多 13 個圓就能精確描述。"""
    theta = np.linspace(0.0, 2 * np.pi, samples, endpoint=False)
    z = np.exp(1j * theta)
    if detail0 is None or detail1 is None:
        m = np.ones(samples)
    else:
        m = sk.polar_multiplier(np.asarray(detail0), np.asarray(detail1), z, np.full(samples, s))
    curve = m * z
    c = np.fft.fft(curve) / samples
    freq = np.fft.fftfreq(samples, d=1.0 / samples).astype(int)
    order = np.argsort(-np.abs(c))
    terms = [[int(freq[k]), float(abs(c[k])), float(np.angle(c[k]))] for k in order if abs(c[k]) > keep][:40]
    return {"terms": terms, "outline": np.round(np.c_[curve.real, curve.imag][::4], 5).tolist(),
            "width_to_height": float(np.ptp(curve.real) / max(np.ptp(curve.imag), 1e-9))}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Record one run for the replay page")
    ap.add_argument("--a", default="biped")
    ap.add_argument("--b", default="spider")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--voxel", type=float, default=0.03, help="grid for the replay meshes / 重播網格的格點")
    ap.add_argument("--run-dir", default="out_run")
    ap.add_argument("--out", default="replay_data.json")
    args = ap.parse_args(argv)
    run_dir = Path(args.run_dir) / f"{args.a}_x_{args.b}_seed{args.seed}"
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    pv = args.voxel
    data: dict = {"run": {"a": args.a, "b": args.b, "seed": args.seed, "voxel": pv,
                          "export_voxel": run["voxel"], "python": platform.python_version(),
                          "pce": Path(pce.__file__).name, "rules": run["rules"]}}

    # ---- the original idea: a closed 3D path drawn by epicycles / 最初的想法 ---------------------------
    target = fd.demo_target_curve()
    fit = fd.fit_closed_curve(fd.resample_closed_polyline(target, 400), 40)
    errors = {}
    dense = fd.resample_closed_polyline(target, 400)
    t = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    for n in (1, 3, 8, 20, 40):
        errors[n] = float(np.mean(np.linalg.norm(fit.truncated(n).evaluate(t) - dense, axis=1)))
    data["prologue"] = {"a0": fit.a0.tolist(), "a": np.round(fit.a, 6).tolist(), "b": np.round(fit.b, 6).tolist(),
                        "target": target.tolist(), "mean_error": errors}

    # ---- parents / 親代 -----------------------------------------------------------------------------------
    forms = lab.all_forms(ontology_tags=True)
    ga, gb = sk.with_ancestry(forms[args.a], 1.0), sk.with_ancestry(forms[args.b], 0.0)
    data["parents"] = []
    for label, name, g in (("A", args.a, ga), ("B", args.b, gb)):
        idx = {p.name: i for i, p in enumerate(g.parts)}
        mesh, face_piece, pieces = sk.build_sdf_creature(g, pv)
        piece_part = np.array([idx[pc["gene"]] for pc in pieces])
        vpart = vertex_from_faces(len(mesh.vertices), mesh.faces, piece_part[face_piece].astype(np.uint8))
        data["parents"].append({
            "label": label, "name": name, "genes": int(g.gene_count()),
            "parts": [{"name": p.name, "tags": list(p.tags), "arrangement": sk.arrangement(p), "core": bool(p.is_core),
                       "bones": int(p.n_bones), "parent": p.parent, "fourier": epicycles(p.detail0, p.detail1)}
                      for p in g.parts],
            "pieces": pieces_json(pieces, idx), "mesh": pack_mesh(mesh, vpart)})

    # ---- matching and inheritance (same steps as rtis_run_once.py) / 配對與遺傳 ----------------------------
    rng = np.random.default_rng(args.seed)
    pairs, decisions = soft.soft_match(ga, gb, rng, "soft")
    data["matching"] = {"pairs": pairs, "decisions": decisions,
                        "unmatched_a": run["matching"]["unmatched_a"], "unmatched_b": run["matching"]["unmatched_b"]}
    cfg = sk.SkeletonInheritanceConfig(micro_budget=0)
    child, log = lab.fuse(ga, gb, rng, cfg, lab.ADOPTED, pairs=pairs)
    recorded = json.loads((run_dir / "child.genome.json").read_text(encoding="utf-8"))
    assert [p["name"] for p in recorded] == [p.name for p in child.parts], "the replay child differs from the run"
    assert all(np.allclose(np.round(p.offsets, 6), r["offsets"]) for p, r in zip(child.parts, recorded))

    idx = {p.name: i for i, p in enumerate(child.parts)}
    origin: dict[str, list] = {}
    for key, cname in log["sources"].items():
        origin.setdefault(cname, []).append(key)
    parts = []
    for p in child.parts:
        gene = log["genes"].get(p.name, {})
        bone_src = (["A" if x else "B" for x in gene["lengths"]] if "lengths" in gene
                    else [gene.get("template", "A")] * p.n_bones)
        parts.append({"name": p.name, "parent": p.parent, "tags": list(p.tags), "arrangement": sk.arrangement(p),
                      "bones": int(p.n_bones), "origin": origin.get(p.name, []), "genes": gene,
                      "bone_src": bone_src, "ancestry_a": float(p.meta.get("ancestry_a", 0.5)),
                      "fourier": epicycles(p.detail0, p.detail1),
                      "detail_src": ("A" if gene["detail"] else "B") if "detail" in gene else gene.get("template")})
    pieces = sk.develop_segments(child, use_detail=True)
    anc = np.array([float(child.parts[idx[pc["gene"]]].meta.get("ancestry_a", 0.5)) for pc in pieces])
    piece_part = np.array([idx[pc["gene"]] for pc in pieces])

    # skin growing: the real surface builder, with every bone's thickness scaled from 20% to 100%.
    # 長皮：用真正的表面建構程式，把每根骨頭的粗細從 20% 放大到 100%。
    growth = []
    for frac in (0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 1.0):
        g_f = sk.SkeletonGenome([dataclasses.replace(p, radii=p.radii * frac) for p in child.parts])
        m, fp, _ = sk.build_sdf_creature(g_f, pv)
        vanc = vertex_from_faces(len(m.vertices), m.faces, np.rint(anc[fp] * 255).astype(np.uint8))
        growth.append({"level": frac, "mesh": pack_mesh(m, vanc)})
    round_mesh, rfp, rpieces = sk.build_sdf_creature(child, pv, use_detail=False)
    detail_mesh, dfp, _ = sk.build_sdf_creature(child, pv, use_detail=True)
    data["child"] = {
        "scale_src": log["scale_src"], "dropped": log["dropped"], "parts": parts,
        "pieces": pieces_json(sk.develop_segments(child, use_detail=False), idx),
        "growth": growth,
        "round": pack_mesh(round_mesh, vertex_from_faces(len(round_mesh.vertices), round_mesh.faces,
                                                          piece_part[rfp].astype(np.uint8))),
        "detail": pack_mesh(detail_mesh, vertex_from_faces(len(detail_mesh.vertices), detail_mesh.faces,
                                                            piece_part[dfp].astype(np.uint8))),
        "ancestry_overall": run["inheritance"]["ancestry_a_overall"],
        "body": run["body"], "motion": {k: v for k, v in run["motion_test"].items() if k != "bones_without_vertices"}}

    # ---- the morphology package written by rtis_run_once.py / 形體包 ---------------------------------------
    package = json.loads((run_dir / "child.morph.json").read_text(encoding="utf-8"))
    with np.load(run_dir / "child.skin.npz") as z:
        skin = {k: z[k] for k in z.files}
    data["package"] = {
        "version": package["version"], "access": package["access"], "counts": package["counts"],
        "groups": package["groups"], "size": package["size"],
        "parts": [{"name": p["name"], "copies": p["copies"], "vertices": p["vertices"], "tags": p["tags"]}
                  for p in package["parts"]],
        "nodes": {n["id"]: n["position"] for n in package["nodes"]},
        "bones": [{"id": b["id"], "part": b["part"], "copy": b["copy"], "index": b["index"], "from": b["from"],
                   "to": b["to"], "parent": b["parent"]} for b in package["bones"]],
        "mesh": {"v": b64(skin["vertices"], np.float32), "f": b64(skin["faces"], np.uint32),
                 "c": b64(skin["vertex_part"], np.uint8), "bi": b64(skin["bone_index"], np.uint8),
                 "bw": b64(skin["bone_weight"], np.float32), "nv": int(len(skin["vertices"])),
                 "nf": int(len(skin["faces"]))}}
    text = json.dumps(data, separators=(",", ":"))
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"{args.out}: {len(text) / 1e6:.2f} MB; growth frames {len(growth)}; "
          f"child parts {[p['name'] for p in parts]}; fourier circles "
          f"{ {p['name']: len(p['fourier']['terms']) for p in parts} }")


if __name__ == "__main__":
    main()
