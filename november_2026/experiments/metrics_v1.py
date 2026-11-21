#!/usr/bin/env python3
"""
metrics_v1.py
=============
The measurements of RTIS experiment plan v1 (protocol frozen 2026-11-16), section 4.
RTIS 實驗計畫 v1（規約 2026-11-16 凍結）第四節的指標。

This file does not change the generator. It does not call the generator's own checks of the same name
(mesh_report, shells, crowding, beads, turning); each measure is written again here from its definition.
It uses the generator only to lay out the bones (develop_segments), for the exact round-cone distance
(sd_round_cone), and to build a part's own surface for G4 (build_field, extract_mesh).
The old measure M3 (form_fusion_lab.crowding) is called as it is, only to be recorded next to G3.
這個檔案不改生成程式，也不呼叫生成程式裡同名的檢查；每個指標都依定義重新寫。
只借用生成程式來排骨頭（develop_segments）、算圓錐的精確距離（sd_round_cone），
以及在 G4 長出單一部位的表面（build_field、extract_mesh）。舊的 M3 照原樣呼叫，只用來和 G3 對照。

Measures / 指標:
  G1  one closed shell / 封閉的單一外殼
      (a) every directed edge appears exactly once and its reverse exactly once
      (b) the triangles around every vertex form one single ring (no two pieces sharing only a point)
      (c) exactly one connected piece with positive signed volume
  G2  bubbles: connected pieces with negative signed volume (reported, not part of passing)
  G3  buried parts, by arc length / 被埋住的部位（依弧長）
  G4  hidden parts, by area / 看不見的部位（依面積）
  G5  parts kept / 部位保留率
  G6  new bend / 新增的彎折
  G7  new humps / 新增的隆起
  G8  share of genes from parent A / 雙親貢獻
  legacy M3: form_fusion_lab.crowding, recorded only / 舊 M3，只記錄

Decisions written down while coding (not changes to the plan) / 寫程式時定下的細節（不是改計畫）:
  - G3, G4 count every placed copy (left / right, each radial copy) as its own instance. Other copies of
    the same gene count as "other parts" for G3.
    G3、G4 把每一份（左右、放射的每一份）當成一個實體；同一個基因的其他份對 G3 算「其他部位」。
  - G3 solids use the same thickening as the generator (radii below 0.9 voxel become 0.9 voxel).
    G3 的實心用和生成時相同的加粗（小於 0.9 格的半徑當成 0.9 格）。
  - G4: if a part's own surface cannot be built, its ratio is NaN and it counts as hidden.
    G4：如果某部位單獨長不出表面，比值記為 NaN，算看不見。
  - G8 weights every child part by 3 n + 3 gene draws (n = its bones: lean, n lengths, n - 1 bends,
    n + 1 radii, blend, attach, detail), whether it was crossed or copied whole, and uses the part's
    recorded share from A (meta "ancestry_a"; 1 or 0 for a part copied whole).
    G8 每個子代部位都以 3n＋3 個基因計（n＝骨頭數），不論交配或整個複製；用部位記錄的 A 比例。

Target: Python 3.10.12 · numpy, scipy, scikit-image (through the generator).
"""

from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

import skeleton_sdf_demo as sk
import form_fusion_lab as lab

METRICS_VERSION = "metrics_v1.0"
OUTER_FROM = 0.25          # G3: only the outer 75% of the arc length / 只看外側 75% 的弧長
BURIED_AT = 0.5            # G3: share inside other parts that counts as buried / 被埋住的門檻
G3_MIN_POINTS = 64
HIDDEN_THRESHOLDS = (0.05, 0.10, 0.20)   # G4; 0.10 is the one used for passing / 0.10 用於合格判定
HUMP_PROMINENCE = 1.05     # G7: a peak at least 5% above the dips on both sides / 比兩側的谷高 5%


# =============================================================================
# G1, G2 — closed single shell, bubbles / 封閉的單一外殼、氣泡
# =============================================================================

def _directed_edges_ok(faces: np.ndarray, n: int) -> bool:
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]).astype(np.int64)
    key = e[:, 0] * n + e[:, 1]
    rev = e[:, 1] * n + e[:, 0]
    uniq, counts = np.unique(key, return_counts=True)
    return bool(np.all(counts == 1) and np.all(np.isin(rev, uniq)))


def _vertex_rings_ok(faces: np.ndarray, n: int) -> bool:
    """Around each vertex v, every triangle gives a link edge from its next corner to its previous corner.
    On a surface that passes (a), these link edges form cycles; one cycle per vertex = one ring.
    每個三角形在頂點 v 處給出一條「下一個角 → 上一個角」的連結邊；通過 (a) 時這些邊會形成環，每個頂點只能有一個環。"""
    f = faces.astype(np.int64)
    v = f.ravel()
    nxt = f[:, [1, 2, 0]].ravel()
    prv = f[:, [2, 0, 1]].ravel()
    keys = np.concatenate([v * n + nxt, v * n + prv])
    uniq, inv = np.unique(keys, return_inverse=True)
    m = len(v)
    a, b = inv[:m], inv[m:]
    graph = coo_matrix((np.ones(m, dtype=np.int8), (a, b)), shape=(len(uniq), len(uniq)))
    _, label = connected_components(graph, directed=False)
    owner_vertex = uniq // n
    pairs = np.unique(np.stack([owner_vertex, label], axis=1), axis=0)
    rings = np.bincount(pairs[:, 0], minlength=n)
    used = np.unique(v)
    return bool(np.all(rings[used] == 1))


def _face_pieces(faces: np.ndarray, n: int) -> np.ndarray:
    """Label of each triangle's connected piece; triangles are connected when they share an edge.
    每個三角形所屬的連通塊；共用一條邊的三角形相連。"""
    f = faces.astype(np.int64)
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    e.sort(axis=1)
    _, edge_id = np.unique(e[:, 0] * n + e[:, 1], return_inverse=True)
    nf = len(f)
    face_of = np.tile(np.arange(nf), 3)
    graph = coo_matrix((np.ones(len(e), dtype=np.int8), (face_of, nf + edge_id)),
                       shape=(nf + edge_id.max() + 1, nf + edge_id.max() + 1))
    _, label = connected_components(graph, directed=False)
    return label[:nf]


def signed_volume(vertices: np.ndarray, faces: np.ndarray) -> float:
    a, b, c = (vertices[faces[:, k]] for k in range(3))
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def g1_g2(mesh) -> dict:
    """G1 (closed single shell) and G2 (bubbles). / G1 與 G2。"""
    v = np.asarray(mesh.vertices, float)
    f = np.asarray(mesh.faces, np.int64)
    n = len(v)
    if len(f) == 0:
        return {"g1_closed": False, "g1_manifold": False, "outer_shells": 0, "bubbles": 0, "g1": False}
    closed = _directed_edges_ok(f, n)
    manifold = closed and _vertex_rings_ok(f, n)
    label = _face_pieces(f, n)
    vols = [signed_volume(v, f[label == c]) for c in np.unique(label)]
    outer = int(sum(x > 0 for x in vols))
    bubbles = int(sum(x <= 0 for x in vols))
    return {"g1_closed": bool(closed), "g1_manifold": bool(manifold), "outer_shells": outer,
            "bubbles": bubbles, "g1": bool(closed and manifold and outer == 1)}


# =============================================================================
# Instances and the part tree / 實體與部位樹
# =============================================================================

def instances(child, use_detail: bool = False) -> list[dict]:
    """Every placed copy of every part, in the same order the generator uses for its ownership field.
    每一個放好的實體，順序與生成程式的歸屬場相同。"""
    return sk.develop_segments(child, use_detail=use_detail)


def _tree(child):
    parent = {p.name: p.parent for p in child.parts}
    root = next(p.name for p in child.parts if p.parent is None)

    def ancestors(name):
        out = set()
        while parent[name] is not None:
            name = parent[name]
            out.add(name)
        return out

    anc = {n: ancestors(n) for n in parent}
    desc = {n: {m for m in parent if n in anc[m]} for n in parent}
    return root, anc, desc


# =============================================================================
# G3 — buried parts, by arc length / 被埋住的部位（依弧長）
# =============================================================================

def arc_points(segments, spacing: float, min_points: int = G3_MIN_POINTS, start: float = OUTER_FROM) -> np.ndarray:
    """Points evenly spaced by arc length on the outer part of a centreline (from `start` of its length).
    Spacing at most `spacing`, at least `min_points` points. Independent of how the chain is cut into bones.
    依弧長均勻取點（從長度的 start 處到末端）；與鏈怎麼切成骨頭無關。"""
    a = np.array([s.a for s in segments], float)
    b = np.array([s.b for s in segments], float)
    seg_len = np.linalg.norm(b - a, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    total = cum[-1]
    if total <= 0:
        return a[:1].copy()
    s0 = start * total
    m = max(min_points, int(np.ceil((total - s0) / spacing)) + 1)
    s = np.linspace(s0, total, m)
    i = np.clip(np.searchsorted(cum, s, side="right") - 1, 0, len(segments) - 1)
    u = np.where(seg_len[i] > 0, (s - cum[i]) / np.maximum(seg_len[i], 1e-15), 0.0)
    return a[i] + u[:, None] * (b[i] - a[i])


def buried_fraction(p_segments, solid_segments, spacing: float, r_min: float = 0.0) -> float:
    """Share of P's outer centreline points inside the union of the given round cones.
    P 外側中心線的點有多少比例落在這些圓錐的聯集裡。"""
    if not solid_segments:
        return 0.0
    pts = arc_points(p_segments, spacing)
    d = np.full(len(pts), np.inf)
    for q in solid_segments:
        d = np.minimum(d, sk.sd_round_cone(pts, np.asarray(q.a, float), np.asarray(q.b, float),
                                           max(q.ra, r_min), max(q.rb, r_min)))
    return float(np.mean(d < 0.0))


def g3(child, voxel: float, density: float = 1.0) -> dict:
    """G3 per instance. density 2 halves the point spacing (pre-check 2).
    每個實體的 G3。density＝2 時取點間距減半（前置檢查第 2 項）。"""
    pcs = instances(child, use_detail=False)
    root, anc, desc = _tree(child)
    spacing = 0.5 * voxel / density
    r_min = 0.9 * voxel
    out = []
    for i, p in enumerate(pcs):
        if p["gene"] == root:
            continue
        excluded = {root} | anc[p["gene"]] | desc[p["gene"]]
        solids = [s for j, q in enumerate(pcs) if j != i and q["gene"] not in excluded for s in q["segments"]]
        frac = buried_fraction(p["segments"], solids, spacing, r_min)
        out.append({"instance": p["name"], "gene": p["gene"], "share_inside": frac, "buried": frac >= BURIED_AT})
    return {"n_instances": len(out), "n_buried": int(sum(r["buried"] for r in out)), "detail": out}


# =============================================================================
# G4 — hidden parts, by area / 看不見的部位（依面積）
# =============================================================================

def triangle_areas(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    a, b, c = (vertices[faces[:, k]] for k in range(3))
    return 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)


def own_surface_area(piece: dict, voxel: float) -> float:
    """Surface area of one instance grown alone, with the same builder and grid size.
    單一實體單獨長出來的表面積（同樣的建構方式與格點）。"""
    try:
        field, _, lo = sk.build_field([piece], voxel)
        if not (field < 0).any():
            return float("nan")
        m = sk.extract_mesh(field, lo, voxel)
        return float(triangle_areas(m.vertices, m.faces).sum())
    except Exception:  # noqa: BLE001 - a part that cannot be grown alone is recorded as NaN
        return float("nan")


def hidden_counts(ratios: list[float]) -> dict:
    """Counts of hidden instances at each threshold; NaN counts as hidden.
    各門檻下看不見的實體數；NaN 算看不見。"""
    r = np.array(ratios, float)
    return {f"n_hidden_{int(round(t * 100)):03d}": int(np.sum(~(r >= t))) for t in HIDDEN_THRESHOLDS}


def instance_ratios(face_piece: np.ndarray, face_area: np.ndarray, own_area: list[float],
                    measured: list[int]) -> list[float]:
    """Area of the final mesh owned by each measured instance / its own area. Counted per instance, so a
    left copy with no triangles is not rescued by its right copy.
    每個實體在最後網格上的面積 ÷ 它單獨的面積。逐個實體算，左邊沒有面時不會被右邊補上。"""
    per_piece = np.bincount(np.asarray(face_piece, np.int64), weights=face_area, minlength=len(own_area))
    out = []
    for i in measured:
        own = own_area[i]
        out.append(float(per_piece[i] / own) if own == own and own > 0 else float("nan"))
    return out


def g4(child, mesh, face_piece: np.ndarray, voxel: float) -> dict:
    pcs = instances(child, use_detail=True)
    root = next(p.name for p in child.parts if p.parent is None)
    area = triangle_areas(np.asarray(mesh.vertices, float), np.asarray(mesh.faces, np.int64))
    measured = [i for i, p in enumerate(pcs) if p["gene"] != root]
    own = [own_surface_area(p, voxel) if i in measured else float("nan") for i, p in enumerate(pcs)]
    ratios = instance_ratios(face_piece, area, own, measured)
    rows = [{"instance": pcs[i]["name"], "gene": pcs[i]["gene"], "area_alone": own[i], "ratio": r}
            for i, r in zip(measured, ratios)]
    return {**hidden_counts(ratios), "detail": rows}


# =============================================================================
# G5 — parts kept / 部位保留率
# =============================================================================

def g5(ga, gb, log: dict) -> dict:
    total = len(ga.parts) + len(gb.parts)
    kept = len(log["sources"])
    lost = {"lost_not_inherited": 0, "lost_orphan": 0, "lost_site": 0}
    for d in log.get("dropped", []):
        n = len(d["parts"])
        why = d["why"]
        if why == "not inherited":
            lost["lost_not_inherited"] += n
        elif why == "parent missing":
            lost["lost_orphan"] += n
        elif why.startswith("lost the site"):
            lost["lost_site"] += n
    return {"sources_total": total, "sources_kept": kept, **lost}


# =============================================================================
# G6, G7 — new bend, new humps (skeleton, crossed parts that are still there) / 新增的彎折與隆起
# =============================================================================

def total_turning_deg(offsets: np.ndarray) -> float:
    d = offsets / (np.linalg.norm(offsets, axis=1, keepdims=True) + 1e-12)
    if len(d) < 2:
        return 0.0
    cos = np.clip(np.sum(d[1:] * d[:-1], axis=1), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos)).sum())


def seen_radius_profile(offsets: np.ndarray, radii: np.ndarray, per_bone: int = 12) -> np.ndarray:
    """Radius seen along the straightened chain: the cone between joints, or a nearby joint's ball if larger.
    拉直的鏈上看得到的半徑：關節之間的圓錐，或附近關節的球（取較大者）。"""
    pos = np.concatenate([[0.0], np.cumsum(np.linalg.norm(offsets, axis=1))])
    s = np.linspace(0.0, pos[-1], per_bone * len(offsets) + 1)
    ball = np.sqrt(np.maximum(radii[None, :] ** 2 - (s[:, None] - pos[None, :]) ** 2, 0.0)).max(axis=1)
    return np.maximum(np.interp(s, pos, radii), ball)


def hump_count(offsets: np.ndarray, radii: np.ndarray) -> int:
    lr = np.log(np.maximum(seen_radius_profile(offsets, radii), 1e-12))
    padded = np.concatenate([[lr.min() - 1.0], lr, [lr.min() - 1.0]])
    return int(len(find_peaks(padded, prominence=np.log(HUMP_PROMINENCE))[0]))


def crossed_parts(child, log: dict, ga, gb) -> list[tuple]:
    """(child part, A part, B part) for every final child part that came from one A part and one B part.
    最後還在、而且由一個 A 部位與一個 B 部位交配而成的子代部位。"""
    by_child: dict[str, dict] = {}
    for key, cname in log["sources"].items():
        side, name = key.split(".", 1)
        by_child.setdefault(cname, {})[side] = name
    A, B = {p.name: p for p in ga.parts}, {p.name: p for p in gb.parts}
    out = []
    for p in child.parts:
        src = by_child.get(p.name, {})
        if "A" in src and "B" in src:
            out.append((p, A[src["A"]], B[src["B"]]))
    return out


def g6_g7(child, log: dict, ga, gb) -> dict:
    bends, humps = [], []
    for p, pa, pb in crossed_parts(child, log, ga, gb):
        n = max(pa.n_bones, pb.n_bones)
        ra, rb = sk.resample_part(pa, n), sk.resample_part(pb, n)
        bends.append(max(0.0, total_turning_deg(p.offsets) - max(total_turning_deg(ra.offsets),
                                                                 total_turning_deg(rb.offsets))))
        humps.append(max(0, hump_count(p.offsets, p.radii) - max(hump_count(ra.offsets, ra.radii),
                                                                 hump_count(rb.offsets, rb.radii))))
    return {"new_bend_deg": float(max(bends)) if bends else 0.0, "new_humps": int(sum(humps)),
            "n_crossed": len(bends)}


# =============================================================================
# G8 — share of genes from parent A / 雙親貢獻
# =============================================================================

def g8(child) -> dict:
    w = np.array([3 * p.n_bones + 3 for p in child.parts], float)
    a = np.array([float(p.meta.get("ancestry_a", 0.5)) for p in child.parts])
    share = float((w * a).sum() / w.sum()) if w.sum() > 0 else float("nan")
    return {"share_from_a": share}


# =============================================================================
# Everything for one child / 一個子代的全部指標
# =============================================================================

def measure_child(child, log: dict, ga, gb, mesh, face_piece, voxel: float, g3_density2: bool = False) -> dict:
    """All v1 measures for one child. Returns (row fields, detail for the side file).
    一個子代的全部 v1 指標。回傳（CSV 欄位、附檔用的細節）。"""
    r12 = g1_g2(mesh)
    r3 = g3(child, voxel)
    r4 = g4(child, mesh, face_piece, voxel)
    r5 = g5(ga, gb, log)
    r67 = g6_g7(child, log, ga, gb)
    r8 = g8(child)
    legacy = lab.crowding(child)["swallowed"]
    row = {
        "g1_closed": int(r12["g1_closed"]), "g1_manifold": int(r12["g1_manifold"]),
        "outer_shells": r12["outer_shells"], "bubbles": r12["bubbles"],
        "n_instances": r3["n_instances"], "n_buried": r3["n_buried"],
        "n_hidden_005": r4["n_hidden_005"], "n_hidden_010": r4["n_hidden_010"], "n_hidden_020": r4["n_hidden_020"],
        "pass_geo": int(r12["g1"] and r3["n_buried"] == 0 and r4["n_hidden_010"] == 0),
        "share_from_a": r8["share_from_a"],
        **r5,
        "new_bend_deg": r67["new_bend_deg"], "new_humps": r67["new_humps"],
        "legacy_m3_pairs": len(legacy),
        "parts": len(child.parts), "triangles": int(len(mesh.faces)),
    }
    detail = {"g3": r3["detail"], "g4": r4["detail"], "legacy_m3": [list(k) for k in legacy],
              "n_crossed": r67["n_crossed"]}
    if g3_density2:
        d2 = g3(child, voxel, density=2.0)
        detail["g3_density2_buried"] = [r["buried"] for r in d2["detail"]]
        detail["g3_density1_buried"] = [r["buried"] for r in r3["detail"]]
    return row, detail
