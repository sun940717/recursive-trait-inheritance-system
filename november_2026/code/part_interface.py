#!/usr/bin/env python3
"""
part_interface.py
=================
The part interface between RTIS-generated bodies and a motion system (ATMS): a "morphology package"
that tells the motion system which parts a body has, how they connect, and which piece of the mesh
belongs to which part, so that it can move each part.
RTIS 產生的身體與動作系統（ATMS）之間的部位接口：一份「形體包」，告訴動作系統這個身體有哪些部位、
怎麼連接、網格的哪一塊屬於哪個部位，讓它可以操作每個部位。

It uses ATMS's own vocabulary (nodes, edges, parameters) and assumes no anatomy: a quadruped, a
jellyfish and a fused child all come out in the same format.
用的是 ATMS 自己的詞彙（節點、邊、參數），不假設任何解剖結構：四足、水母、融合出來的子代格式都一樣。

Requires fourier3d_demo.py, fourier_genetics.py, skeleton_sdf_demo.py and form_fusion_lab.py in the
same folder. Target: Python 3.10.12 · numpy, matplotlib, scikit-image, scipy.

One package = three files / 一份形體包＝三個檔案:
  <name>.morph.json   nodes, bones, edges, parts, groups (format described in the JSON's "about" field)
                      節點、骨頭、邊、部位、群組
  <name>.skin.npz     vertices (V,3), faces (F,3), bone_index (V,4), bone_weight (V,4), vertex_part (V,),
                      face_part (F,)   - same frame as the JSON: x forward, y left, z up
                      網格與每個頂點的骨頭權重；座標系與 JSON 相同：x 向前、y 向左、z 向上
  <name>.obj          the mesh for viewing, one group per part, converted to Y-up like the other exports
                      (x, y, z) -> (x, z, -y).  Do not mix its coordinates with the JSON's.
                      給人看的網格，每個部位一個群組；跟其他匯出一樣轉成 Y 朝上，座標不要跟 JSON 混用

What a motion system can address / 動作系統可以指定的對象:
  a node    "leg_front.L.j2"     one joint of one copy of one part / 某部位某一份的某個關節
  a bone    "leg_front.L.b1"     the stretch between two neighbouring nodes / 兩個相鄰節點之間的那一段
  a part    "leg_front"          all copies of a part / 一個部位的所有複本
  a group   "tag:limb", "arrangement:radial", "tips", "root", "side:L" ...

The pose functions at the bottom (pose, demo_tokens) are only a test that the interface is enough to
move a body. They are not ATMS and not a proposal for how ATMS should work.
檔案後半的姿勢函式只是用來測試「這個接口足以讓身體動起來」，不是 ATMS，也不是在建議 ATMS 該怎麼做。

Usage / 用法:
  python part_interface.py                      # six founders + one fused child -> ./out_interface
  python part_interface.py --voxel 0.015
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import fourier3d_demo as fd  # noqa: E402
import skeleton_sdf_demo as sk  # noqa: E402
import form_fusion_lab as lab  # noqa: E402

FORMAT_VERSION = "0.2"   # 0.2 (2026-11-15): adds "access" and "lineage" / 新增 access 與 lineage
MAX_INFLUENCES = 4

ABOUT = {
    "what": "Morphology package: the body of one creature as a topological entity (nodes, edges, parameters).",
    "frame": "x forward, y to the creature's left, z up; lengths in the generator's units (see 'size')",
    "nodes": "one per joint of each placed copy of a part; id = <part>[.<copy>].j<index>; index 0 is where the part starts",
    "bones": "one per stretch between neighbouring nodes; id = <part>[.<copy>].b<index>; 'parent' is the bone it moves with",
    "edges": "bone: two nodes of one chain. attach: first node of a part to a bone of its parent part, at "
             "'t' along that bone (0 = start, 1 = end). mirror: the same node on the left and right copy. "
             "radial: the same node on neighbouring copies around the parent.",
    "parts": "one per gene of the genome; 'copies' lists the placed copies ('' = single, L/R = mirrored, 0..N-1 = radial)",
    "groups": "named sets of part names, for addressing several parts at once",
    "skin": "per mesh vertex: up to 4 bones (indices into 'bones') and their weights (sum 1). A default "
            "binding; a motion system may ignore it and bind the mesh its own way.",
    "access": "read_only: a motion system may move nodes (pose) but not add, remove or rewire them. The body is "
              "grown from the genome; a change to its structure has to go back to RTIS as a gene change, and RTIS "
              "grows a new body and a new package.",
    "lineage": "how this body came to be. Inheritance is done by RTIS on genes; a motion system receives the "
               "result here and does not redo it. ancestry_a per part = share of the part's genes from parent A.",
}


def _copy_label(piece_name: str, gene: str) -> str:
    return piece_name[len(gene) + 1:] if piece_name != gene else ""


def _join(part: str, copy: str, leaf: str) -> str:
    return f"{part}.{copy}.{leaf}" if copy else f"{part}.{leaf}"


def build_package(g: sk.SkeletonGenome, voxel: float = 0.02, name: str = "creature",
                  lineage: dict | None = None) -> tuple[dict, dict]:
    """Genome -> (package, skin). package is JSON-ready; skin holds the numpy arrays.
    lineage: how the body came to be, e.g. {"generation": 1, "parents": ["biped", "spider"], "seed": 7,
    "rules": [...]}; None = a founder (generation 0, no parents).
    基因組 ->（形體包、蒙皮資料）。lineage：這個身體怎麼來的；None＝原始形體（第 0 代、沒有親代）。"""
    mesh, face_piece, pieces = sk.build_sdf_creature(g, voxel)
    genes = {p.name: p for p in g.parts}
    part_index = {p.name: i for i, p in enumerate(g.parts)}

    nodes, bones, edges = [], [], []
    bone_id_of: dict[tuple[str, int], int] = {}      # (piece name, bone number) -> index in bones
    first_piece_of: dict[str, dict] = {}             # the copy a child part hangs from / 子部位掛在哪一份複本上
    copies: dict[str, list[str]] = {p.name: [] for p in g.parts}
    piece_bones: list[list[int]] = []
    for pc in pieces:
        gene = genes[pc["gene"]]
        copy = _copy_label(pc["name"], gene.name)
        copies[gene.name].append(copy)
        segs = pc["segments"]
        first_piece_of.setdefault(gene.name, pc)
        # where this chain hangs / 這條鏈掛在哪裡
        parent_bone = None
        if gene.parent is not None:
            ppc = first_piece_of[gene.parent]
            n_parent = len(ppc["segments"])
            u = float(np.clip(gene.attach, 0.0, 1.0)) * n_parent
            i0 = min(int(np.floor(u)), n_parent - 1)
            parent_bone = bone_id_of[(ppc["name"], i0)]
            edges.append({"type": "attach", "node": _join(gene.name, copy, "j0"),
                          "bone": bones[parent_bone]["id"], "t": round(u - i0, 6)})
        ids = []
        for j in range(len(segs) + 1):
            pos = segs[j].a if j < len(segs) else segs[-1].b
            rad = segs[j].ra if j < len(segs) else segs[-1].rb
            nodes.append({"id": _join(gene.name, copy, f"j{j}"), "part": gene.name, "copy": copy, "index": j,
                          "position": [round(float(x), 6) for x in pos], "radius": round(float(rad), 6),
                          "tip": j == len(segs)})
        for i, s in enumerate(segs):
            bid = len(bones)
            bone_id_of[(pc["name"], i)] = bid
            ids.append(bid)
            bones.append({"id": _join(gene.name, copy, f"b{i}"), "part": gene.name, "copy": copy, "index": i,
                          "from": _join(gene.name, copy, f"j{i}"), "to": _join(gene.name, copy, f"j{i + 1}"),
                          "length": round(float(np.linalg.norm(s.b - s.a)), 6),
                          "parent": None if (i == 0 and parent_bone is None)
                          else bones[parent_bone if i == 0 else bid - 1]["id"]})
            edges.append({"type": "bone", "a": bones[bid]["from"], "b": bones[bid]["to"]})
        piece_bones.append(ids)
    for p in g.parts:                                 # symmetry edges / 對稱關係
        n = p.n_bones + 1
        if copies[p.name] == ["L", "R"]:
            edges += [{"type": "mirror", "a": f"{p.name}.L.j{j}", "b": f"{p.name}.R.j{j}"} for j in range(n)]
        elif len(copies[p.name]) >= 3:
            c = copies[p.name]
            edges += [{"type": "radial", "a": f"{p.name}.{c[k]}.j{j}", "b": f"{p.name}.{c[(k + 1) % len(c)]}.j{j}"}
                      for k in range(len(c)) for j in range(n)]

    # ---- skin: each vertex follows the bones whose surface it lies on / 每個頂點跟著它所在表面的骨頭 ----
    # Distance to a bone = the same distance the surface was built from (round cone, thin radii thickened
    # to 0.9 voxel, cross-section outline applied), so a vertex on a wide flat shell still belongs to it.
    # 到骨頭的距離＝建表面時用的同一個距離（圓錐、過細的半徑加粗到 0.9 格、套用截面輪廓），
    # 這樣又寬又扁的殼上的頂點仍然屬於那個殼。
    flat = [(bid, s, pc.get("detail")) for pc, ids in zip(pieces, piece_bones) for bid, s in zip(ids, pc["segments"])]
    v = mesh.vertices
    r_min = 0.9 * voxel
    cols = []
    for _, s, detail in flat:
        ra, rb = max(s.ra, r_min), max(s.rb, r_min)
        d = sk.sd_round_cone(v, s.a, s.b, ra, rb)
        cols.append(d if detail is None else d - sk.detail_offset(v, s, ra, rb, detail))
    dist = np.stack(cols, axis=1)                                                              # (V, B)
    mean_r = np.array([0.5 * (s.ra + s.rb) for _, s, _ in flat])
    nearest = dist.argmin(axis=1)
    # Width of the transition between two bones = 0.35 x the thinner of the two, so a thin limb does not
    # drag a large patch of a thick body with it. / 兩根骨頭之間的過渡寬度＝較細那根的 0.35 倍，
    # 細的肢體才不會拖著粗身體的一大片一起動。
    soft = np.maximum(0.35 * np.minimum(mean_r[None, :], mean_r[nearest][:, None]), 0.5 * voxel)
    w = np.exp(-(dist - dist.min(axis=1, keepdims=True)) / soft)
    order = np.argsort(-w, axis=1)[:, :MAX_INFLUENCES]
    top = np.take_along_axis(w, order, axis=1)
    top[top < 0.02] = 0.0
    top /= top.sum(axis=1, keepdims=True)
    bone_ids = np.array([bid for bid, _, _ in flat])
    bone_part = np.array([part_index[b["part"]] for b in bones])
    vertex_part = bone_part[bone_ids[order[:, 0]]]
    piece_part = np.array([part_index[pc["gene"]] for pc in pieces])
    skin = {"vertices": v.astype(np.float64), "faces": mesh.faces.astype(np.int32),
            "bone_index": bone_ids[order].astype(np.int32), "bone_weight": top.astype(np.float64),
            "vertex_part": vertex_part.astype(np.int32), "face_part": piece_part[face_piece].astype(np.int32)}

    # ---- parts and groups / 部位與群組 ----------------------------------------------------------------------
    parts = []
    for p in g.parts:
        parts.append({"name": p.name, "tags": list(p.tags), "arrangement": sk.arrangement(p),
                      "copies": copies[p.name], "parent": p.parent, "attach": round(float(p.attach), 6),
                      "is_core": bool(p.is_core), "bones_per_copy": int(p.n_bones),
                      "ancestry_a": p.meta.get("ancestry_a"),
                      "vertices": int((vertex_part == part_index[p.name]).sum())})
    groups: dict[str, list[str]] = {"root": [p.name for p in g.parts if p.parent is None],
                                    "attached": [p.name for p in g.parts if p.parent is not None]}
    for p in g.parts:
        for t in p.tags:
            groups.setdefault(f"tag:{t}", []).append(p.name)
        groups.setdefault(f"arrangement:{sk.arrangement(p)}", []).append(p.name)
    lo, hi = v.min(axis=0), v.max(axis=0)
    digest = hashlib.sha1(json.dumps([[p.name, p.parent, np.round(p.offsets, 6).tolist(),
                                       np.round(p.radii, 6).tolist()] for p in g.parts]).encode()).hexdigest()[:12]
    package = {"format": "rtis-morphology-package", "version": FORMAT_VERSION, "name": name, "about": ABOUT,
               "genome_digest": digest, "voxel": voxel,
               "access": {"motion_system": "read_only"},
               "lineage": {"generation": 0, "parents": [], **(lineage or {}),
                           "ancestry_a": {p.name: p.meta.get("ancestry_a") for p in g.parts}},
               "size": {"bounds_min": [round(float(x), 5) for x in lo], "bounds_max": [round(float(x), 5) for x in hi],
                        "diagonal": round(float(np.linalg.norm(hi - lo)), 5)},
               "files": {"skin": f"{name}.skin.npz", "mesh_for_viewing": f"{name}.obj"},
               "counts": {"parts": len(parts), "nodes": len(nodes), "bones": len(bones), "edges": len(edges),
                          "vertices": int(len(v)), "faces": int(len(mesh.faces))},
               "parts": parts, "groups": groups, "nodes": nodes, "bones": bones, "edges": edges}
    return package, skin


def write_package(package: dict, skin: dict, out: Path) -> None:
    name = package["name"]
    (out / f"{name}.morph.json").write_text(json.dumps(package, indent=1, ensure_ascii=False), encoding="utf-8")
    np.savez_compressed(out / f"{name}.skin.npz", **skin)
    lines = [f"# {name} - RTIS morphology package v{package['version']}, viewing mesh, Y-up: (x, y, z) -> (x, z, -y)"]
    lines += [f"v {x:.5f} {z:.5f} {-y:.5f}" for x, y, z in skin["vertices"]]
    for i, p in enumerate(package["parts"]):
        f = skin["faces"][skin["face_part"] == i] + 1
        if len(f):
            lines.append(f"g {p['name']}")
            lines += [f"f {a} {b} {c}" for a, b, c in f]
    (out / f"{name}.obj").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_package(folder: Path, name: str) -> tuple[dict, dict]:
    package = json.loads((folder / f"{name}.morph.json").read_text(encoding="utf-8"))
    with np.load(folder / package["files"]["skin"]) as z:
        skin = {k: z[k] for k in z.files}
    return package, skin


def resolve(package: dict, target: str) -> list[int]:
    """Bone indices addressed by a bone id, a node id (the bone that starts there), a part name or a
    group name. / 把骨頭 id、節點 id（從那裡開始的骨頭）、部位名稱或群組名稱換成骨頭索引。"""
    bones = package["bones"]
    if target in package["groups"]:
        names = set(package["groups"][target])
        return [i for i, b in enumerate(bones) if b["part"] in names]
    hit = [i for i, b in enumerate(bones) if target in (b["id"], b["from"], b["part"])]
    if not hit:
        raise KeyError(f"nothing in the package is called {target!r}")
    return hit


# =============================================================================
# Test only: can the interface move a body? / 僅供測試：這個接口能不能讓身體動起來？
# =============================================================================

def _rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    return sk.rotation_about(axis / (np.linalg.norm(axis) + 1e-12), angle)


def pose(package: dict, skin: dict, turns: dict[str, tuple]) -> np.ndarray:
    """turns: {bone id: (axis (3,), angle in radians)} - each bone turns about its own start node, and
    everything hanging from it follows. Returns the posed vertices (linear blend of bone motions).
    turns：{骨頭 id:（軸、弧度）}，每根骨頭繞自己的起點轉，掛在它上面的東西跟著動。回傳擺好姿勢的頂點。"""
    bones = package["bones"]
    index = {b["id"]: i for i, b in enumerate(bones)}
    node_pos = {n["id"]: np.array(n["position"]) for n in package["nodes"]}
    mats = np.zeros((len(bones), 4, 4))
    for i, b in enumerate(bones):                       # parents always come before children / 父骨頭一定排在前面
        local = np.eye(4)
        if b["id"] in turns:
            axis, angle = turns[b["id"]]
            r = _rotation(np.asarray(axis, float), float(angle))
            pivot = node_pos[b["from"]]
            local[:3, :3] = r
            local[:3, 3] = pivot - r @ pivot
        mats[i] = (mats[index[b["parent"]]] if b["parent"] is not None else np.eye(4)) @ local
    v = np.c_[skin["vertices"], np.ones(len(skin["vertices"]))]
    out = np.zeros((len(v), 3))
    for k in range(skin["bone_index"].shape[1]):
        m = mats[skin["bone_index"][:, k]]
        out += skin["bone_weight"][:, k, None] * np.einsum("vij,vj->vi", m, v)[:, :3]
    return out


def demo_tokens(package: dict, phase: float) -> dict[str, tuple]:
    """Two action tokens written against the package only (no anatomy assumed):
       OSCILLATE(group=attached, where=first bone)   every attached part swings at its base
       PROPAGATE(along each chain)                   a small bend travels down each chain
    只靠形體包寫出來的兩個動作（不假設解剖）：每個附屬部位在根部擺動；一個小彎折沿著每條鏈傳下去。"""
    bones = package["bones"]
    index = {b["id"]: i for i, b in enumerate(bones)}
    node_pos = {n["id"]: np.array(n["position"]) for n in package["nodes"]}
    direction = [node_pos[b["to"]] - node_pos[b["from"]] for b in bones]
    attached = set(package["groups"]["attached"])
    side = {"L": 0.0, "R": np.pi}
    turns = {}
    for i, b in enumerate(bones):
        if b["part"] not in attached:
            continue
        ref = direction[index[b["parent"]]]
        axis = np.cross(direction[i], ref)
        if np.linalg.norm(axis) < 0.2 * np.linalg.norm(direction[i]) * np.linalg.norm(ref):
            axis = np.array([0.0, 0.0, 1.0])            # in line with its parent: wag sideways / 與父骨頭同向：左右擺
        offset = side.get(b["copy"], 0.0) + (0.7 * int(b["copy"]) if b["copy"].isdigit() else 0.0)
        amp = np.radians(22.0) if b["index"] == 0 else np.radians(9.0)
        turns[b["id"]] = (axis, amp * np.sin(phase + offset - 0.9 * b["index"]))
    return turns


def checks(package: dict, skin: dict) -> dict:
    """Numbers that say whether the package is usable. / 判斷形體包能不能用的數字。"""
    w, idx = skin["bone_weight"], skin["bone_index"]
    faces, vp, fpart = skin["faces"], skin["vertex_part"], skin["face_part"]
    agree = np.mean(np.any(vp[faces] == fpart[:, None], axis=1))
    rest = pose(package, skin, {})
    bones = package["bones"]
    used = np.zeros(len(bones), bool)
    used[np.unique(idx[w > 0])] = True
    # move one attached part at its base: who moves? / 只轉一個附屬部位的根部：誰會動？
    locality = None
    att = [b for b in bones if b["parent"] is not None and b["index"] == 0]
    if att:
        b = att[0]
        moved = np.linalg.norm(pose(package, skin, {b["id"]: ((0.0, 1.0, 0.0), np.radians(30.0))}) - rest, axis=1)
        far = moved > 0.01 * package["size"]["diagonal"]
        names = [p["name"] for p in package["parts"]]
        below = {b["part"]}
        grew = True
        while grew:
            grew = False
            for p in package["parts"]:
                if p["parent"] in below and p["name"] not in below:
                    below.add(p["name"])
                    grew = True
        inside = np.isin(vp, [names.index(n) for n in below])
        locality = {"bone": b["id"], "moved_vertices": int(far.sum()),
                    "share_in_that_part": float(np.mean(inside[far])) if far.any() else 1.0}
    posed = pose(package, skin, demo_tokens(package, 1.2))
    vol0 = fd.signed_volume(fd.Mesh(rest, faces.astype(np.int64)))
    vol1 = fd.signed_volume(fd.Mesh(posed, faces.astype(np.int64)))
    n0 = np.cross(rest[faces[:, 1]] - rest[faces[:, 0]], rest[faces[:, 2]] - rest[faces[:, 0]])
    n1 = np.cross(posed[faces[:, 1]] - posed[faces[:, 0]], posed[faces[:, 2]] - posed[faces[:, 0]])
    return {"weights_sum_error": float(np.abs(w.sum(axis=1) - 1.0).max()),
            "rest_pose_error": float(np.abs(rest - skin["vertices"]).max()),
            "parts_with_vertices": int(sum(p["vertices"] > 0 for p in package["parts"])),
            "bones_with_vertices": int(used.sum()),
            "bones_without_vertices": [bones[i]["id"] for i in np.flatnonzero(~used)],
            "vertex_part_agrees_with_face_part": float(agree),
            "one_part_moved": locality,
            "demo_pose_volume_change": float(vol1 / vol0 - 1.0),
            "demo_pose_flipped_faces": float(np.mean(np.einsum("ij,ij->i", n0, n1) < 0.0))}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Part interface (morphology package) for a motion system")
    ap.add_argument("--out", default="out_interface")
    ap.add_argument("--voxel", type=float, default=0.02)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    forms = dict(lab.all_forms(ontology_tags=True))
    rng = np.random.default_rng(args.seed)
    cfg = sk.SkeletonInheritanceConfig(micro_budget=0)
    forms["child_biped_x_spider"], _ = lab.fuse(
        sk.with_ancestry(forms["biped"], 1.0), sk.with_ancestry(forms["spider"], 0.0), rng, cfg, lab.ADOPTED)

    print(f"{'creature':<22}{'parts':>6}{'nodes':>7}{'bones':>7}{'edges':>7}{'vertices':>10}"
          f"{'parts / bones with vertices':>29}{'part labels agree':>19}{'one part moved: stays in it':>29}"
          f"{'volume change':>15}{'flipped faces':>15}")
    report, packs = {}, {}
    for name, g in forms.items():
        lineage = ({"generation": 1, "parents": ["biped", "spider"], "seed": args.seed}
                   if name.startswith("child_") else None)
        package, skin = build_package(g, args.voxel, name, lineage)
        write_package(package, skin, out)
        package, skin = load_package(out, name)          # test what was written, not what is in memory
        c = checks(package, skin)
        assert c["weights_sum_error"] < 1e-9 and c["rest_pose_error"] < 1e-9, c
        report[name] = {"counts": package["counts"], "checks": c}
        packs[name] = (package, skin)
        n = package["counts"]
        loc = c["one_part_moved"]
        print(f"{name:<22}{n['parts']:>6}{n['nodes']:>7}{n['bones']:>7}{n['edges']:>7}{n['vertices']:>10}"
              f"{c['parts_with_vertices']:>14} / {n['parts']:<2}{c['bones_with_vertices']:>5} / {n['bones']:<4}"
              f"{c['vertex_part_agrees_with_face_part']:>19.1%}{loc['share_in_that_part']:>29.1%}"
              f"{c['demo_pose_volume_change']:>15.1%}{c['demo_pose_flipped_faces']:>15.2%}")

    shown = ["quadruped", "jellyfish", "crab", "child_biped_x_spider"]
    phases = [None, 0.6, 2.2, 3.8]
    fig = plt.figure(figsize=(3.6 * len(phases), 3.4 * len(shown)))
    fig.suptitle("Part interface test - the same two action tokens on four bodies; colour = part", fontsize=13)
    palette = plt.get_cmap("tab10")(np.arange(10))[:, :3]
    for r, name in enumerate(shown):
        package, skin = packs[name]
        colours = palette[skin["face_part"] % 10]
        for c, ph in enumerate(phases):
            ax = fig.add_subplot(len(shown), len(phases), r * len(phases) + c + 1, projection="3d")
            verts = skin["vertices"] if ph is None else pose(package, skin, demo_tokens(package, ph))
            title = f"{name}: rest" if ph is None else f"posed, phase {ph}"
            sk.draw_mesh(ax, fd.Mesh(verts, skin["faces"].astype(np.int64)), colours, title, light=(0.5, -0.6, 0.7))
            ax.view_init(elev=18, azim=-58)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.93, bottom=0.0, wspace=0.0, hspace=0.08)
    fig.savefig(out / "pose_test.png", dpi=90)
    plt.close(fig)
    (out / "results.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"Done -> {out.resolve()}")


if __name__ == "__main__":
    main()
