#!/usr/bin/env python3
"""
skeleton_sdf_demo.py
====================
Skeleton genome + implicit surface (smooth-union SDF) + marching cubes,
compared side by side with the Fourier tubes of fourier3d_demo.py on the SAME two creatures.
骨架基因組 ＋ 隱式曲面（平滑聯集 SDF）＋ marching cubes，
用同樣的兩隻生物跟 fourier3d_demo.py 的傅立葉管並排比較。

Requires fourier3d_demo.py and fourier_genetics.py in the same folder.
Target: Python 3.10.12 · numpy, matplotlib, scikit-image (marching cubes), scipy (connected components).
需要同資料夾的 fourier3d_demo.py 與 fourier_genetics.py。
目標環境：Python 3.10.12 · numpy、matplotlib、scikit-image（marching cubes）、scipy（連通元件）。

Idea / 概念
  Genome = a tree of bone chains. Every gene is local and has a name:
      "bone i of the front leg" (one 3D vector = length + direction), "thickness at joint i", "skin blend".
  Body  = one skin wrapped around all bones:
      inside one part  : exact union of round cones (bones)                 d_p = min_i d_i
      between parts    : order-independent smooth union                     g = -log( sum_p exp(-d_p / k_p) )
      surface          : g = 0, extracted with marching cubes -> ONE closed mesh
  Detail layer (optional) = the cross-section outline of each part, stored as a polar Fourier series
      radius multiplier m(angle) = c0 + sum_n a_n cos(n angle) + b_n sin(n angle), given at both ends of
      the chain and blended along it. It pushes the round skin in or out: d_p -> d_p - R * (m - 1).
      One part's detail is ONE gene: it is inherited as a whole pack from one parent.
  基因組 = 骨頭鏈組成的樹。每個基因都是局部、有名字的：
      「前腿第 i 根骨頭」（一個三維向量 = 長度＋方向）、「第 i 個關節的粗細」、「皮膚融合度」。
  身體  = 包住所有骨頭的一層皮：
      同一部位內：圓錐骨頭的精確聯集；部位之間：與順序無關的平滑聯集；
      表面：g = 0，用 marching cubes 取出 -> 一個封閉網格。
  細節層（可選）= 每個部位的截面輪廓，用極座標傅立葉級數儲存：半徑倍率 m(角度)，
      鏈的兩端各一組、沿著鏈內插。它把圓形的皮往外推或往內縮：d_p -> d_p - R * (m - 1)。
      一個部位的細節是「一個」基因：整包從爸爸或媽媽繼承。

What this script does / 這支程式做什麼
  1. Converts the quadruped and the biped from Fourier tube genomes to skeleton genomes.
     把四足與二足從傅立葉管基因組轉成骨架基因組。
  2. Builds both versions and compares: pieces, closed-surface check, triangles, build time.
     兩種做法各建一次並比較：塊數、封閉性檢查、三角形數、建構時間。
  3. Locality test: change ONE gene, measure how much of the limb changes.
     局部性測試：只改一個基因，量整條肢體有多少比例跟著變。
  4. Gene-level crossover (each gene whole from one parent) on skeleton genomes: A x B -> children,
     then checks every child is one closed mesh.
     在骨架基因組上做基因層交配（每個基因整個來自一方）：A x B -> 子代，並檢查每個子代都是一個封閉網格。

Outputs (default ./out_sdf) / 輸出（預設 ./out_sdf）
  compare_fourier_vs_sdf.png   renders + a slice through the shoulder / 渲染圖＋肩膀處的切面
  detail_layer.png             tubes vs round skeleton vs skeleton + detail, with body outlines
                               傅立葉管、圓形骨架、骨架＋細節三者對照，附身體輪廓
  sdf_pedigree.png             founders and children, coloured by ancestry / 親代與子代，顏色代表血緣
  <name>_sdf.obj / .json       single-mesh OBJ (Y-up) and skeleton genome / 單一網格 OBJ 與骨架基因組
  comparison.json              every number printed by this run / 這次執行印出的所有數字

Usage / 用法
  python skeleton_sdf_demo.py
  python skeleton_sdf_demo.py --voxel 0.0125 --children 6 --seed 3
  python skeleton_sdf_demo.py --body-bones 5          # reproduce the 5-bone body / 重現 5 根骨頭的身體
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import colors as mcolors  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

try:
    from skimage import measure as _sk_measure
except ImportError as exc:  # pragma: no cover
    raise SystemExit("scikit-image is required: pip install scikit-image\n"
                     "需要 scikit-image：pip install scikit-image") from exc
from scipy.sparse import coo_matrix  # noqa: E402
from scipy.sparse.csgraph import connected_components  # noqa: E402

import fourier3d_demo as fd  # noqa: E402
import fourier_genetics as fg  # noqa: E402
from fourier3d_demo import Mesh  # noqa: E402

COLOUR_A = np.array(mcolors.to_rgb("#e07b39"))   # founder A (quadruped) / 親代 A（四足）
COLOUR_B = np.array(mcolors.to_rgb("#3b7dd8"))   # founder B (biped) / 親代 B（二足）
GREY = np.array(mcolors.to_rgb("#8a97a8"))


# =============================================================================
# Skeleton genome / 骨架基因組
# =============================================================================

@dataclass
class BonePart:
    """One body part = one chain of bones. / 一個部位 = 一條骨頭鏈。"""
    name: str
    offsets: np.ndarray          # (J, 3) gene "bone i": vector from joint i to joint i+1 / 第 i 根骨頭
    radii: np.ndarray            # (J+1,) gene "thickness at joint i" / 第 i 個關節的粗細
    blend: float                 # gene "skin blend": how softly this part merges into others / 融合度
    origin: np.ndarray = field(default_factory=lambda: np.zeros(3))   # root only / 只有根部位使用
    parent: str | None = None
    attach: float = 0.0          # gene: position along the parent chain, 0..1 / 接在父鏈上的位置
    mirror: bool = False
    tags: list = field(default_factory=list)
    is_core: bool = False
    meta: dict = field(default_factory=dict)
    # Detail gene (optional): cross-section outline as polar Fourier rows n = 0..H, each row [a_n, b_n].
    # Row 0 is the constant term [c0, 0]. detail0 = at the chain start, detail1 = at the chain end.
    # 細節基因（可選）：截面輪廓的極座標傅立葉係數，第 n 列是 [a_n, b_n]，第 0 列是常數項。
    detail0: np.ndarray | None = None
    detail1: np.ndarray | None = None
    # Arrangement gene: radial >= 2 makes that many copies, turned around the parent's bone at the
    # attach point (jellyfish tentacles). 0 = no radial copies. A part is mirrored OR radial, not both.
    # 排列基因：radial >= 2 時，繞著父骨頭在接點處的方向轉出這麼多份（例如水母的觸手）。
    radial: int = 0

    @property
    def n_bones(self) -> int:
        return int(self.offsets.shape[0])

    def gene_count(self, include_detail: bool = True) -> int:
        """bones + joint thicknesses + blend + attach (+ 1 detail pack)
        骨頭＋關節粗細＋融合度＋接點（＋1 包細節）"""
        n = self.n_bones + (self.n_bones + 1) + 1 + (0 if self.parent is None else 1)
        return n + (1 if include_detail and self.detail0 is not None else 0)


@dataclass
class SkeletonGenome:
    parts: list[BonePart]

    def gene_count(self, include_detail: bool = True) -> int:
        return sum(p.gene_count(include_detail) for p in self.parts)

    def to_json(self) -> dict:
        return {"gene_count": self.gene_count(), "parts": [{
            "name": p.name, "parent": p.parent, "attach": float(p.attach), "mirror": bool(p.mirror),
            "radial": int(p.radial),
            "tags": list(p.tags), "is_core": bool(p.is_core), "blend": float(p.blend),
            "origin": np.asarray(p.origin, float).tolist(),
            "offsets": p.offsets.tolist(), "radii": p.radii.tolist(),
            "detail0": None if p.detail0 is None else p.detail0.tolist(),
            "detail1": None if p.detail1 is None else p.detail1.tolist(),
            "meta": {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in p.meta.items()},
        } for p in self.parts]}


def arrangement(part: BonePart) -> str:
    """"radial", "mirror" or "single". / 排列方式。"""
    return "radial" if part.radial >= 2 else ("mirror" if part.mirror else "single")


def rotation_about(axis: np.ndarray, angle: float) -> np.ndarray:
    """Rotation matrix about a unit axis (Rodrigues). / 繞單位軸旋轉的矩陣。"""
    x, y, z = axis
    k = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    return np.eye(3) + np.sin(angle) * k + (1.0 - np.cos(angle)) * (k @ k)


def chain_joints(part: BonePart, start: np.ndarray) -> np.ndarray:
    """(J+1, 3) joint positions. Any set of bone vectors gives a valid connected chain.
    關節位置。任何一組骨頭向量都會得到一條有效、相連的鏈。"""
    return np.vstack([start, start + np.cumsum(part.offsets, axis=0)])


def point_on_chain(joints: np.ndarray, t: float) -> np.ndarray:
    u = float(np.clip(t, 0.0, 1.0)) * (len(joints) - 1)
    i = min(int(np.floor(u)), len(joints) - 2)
    return joints[i] + (u - i) * (joints[i + 1] - joints[i])


def resample_part(part: BonePart, n: int) -> BonePart:
    """Re-express a chain with n bones (same shape). Lets parents with different bone counts cross.
    把一條鏈改用 n 根骨頭表示（形狀不變），讓骨頭數不同的親代也能交配。"""
    if part.n_bones == n:
        return part
    joints = chain_joints(part, np.zeros(3))
    t_old = np.linspace(0.0, 1.0, len(joints))
    t_new = np.linspace(0.0, 1.0, n + 1)
    new_j = np.column_stack([np.interp(t_new, t_old, joints[:, d]) for d in range(3)])
    return dataclasses.replace(part, offsets=np.diff(new_j, axis=0),
                               radii=np.interp(t_new, t_old, part.radii))


def detail_symmetry_mask(n_rows: int) -> np.ndarray:
    """Entries that keep an outline left/right symmetric (angle -> pi - angle):
    cos terms for even n, sin terms for odd n. Shape (n_rows, 2).
    能保持左右對稱的係數：偶數階的 cos、奇數階的 sin。"""
    mask = np.zeros((n_rows, 2))
    mask[0::2, 0] = 1.0
    mask[1::2, 1] = 1.0
    return mask


def fit_polar_detail(contour: np.ndarray, scale: float, harmonics: int) -> np.ndarray:
    """Closed 2D outline -> polar Fourier rows (harmonics + 1, 2) of radius / scale.
    閉合的二維輪廓 -> 「半徑 ÷ scale」的極座標傅立葉係數。"""
    phi = np.arctan2(contour[:, 1], contour[:, 0])
    r = np.hypot(contour[:, 0], contour[:, 1]) / scale
    n = np.arange(1, harmonics + 1)
    basis = np.hstack([np.ones((len(phi), 1)), np.cos(np.outer(phi, n)), np.sin(np.outer(phi, n))])
    coef, *_ = np.linalg.lstsq(basis, r, rcond=None)
    out = np.zeros((harmonics + 1, 2))
    out[0, 0] = coef[0]
    out[1:, 0] = coef[1:harmonics + 1]
    out[1:, 1] = coef[harmonics + 1:]
    return out


DETAIL_MIN, DETAIL_MAX = 0.4, 1.8      # limits of the outline multiplier / 輪廓倍率的上下限


def polar_multiplier(d0: np.ndarray, d1: np.ndarray, z: np.ndarray, s: np.ndarray) -> np.ndarray:
    """m(angle, s): outline multiplier, blended from d0 (s = 0) to d1 (s = 1).
    z = cos(angle) + i sin(angle); z**n gives cos(n angle) and sin(n angle) without trig calls.
    Clamped to [DETAIL_MIN, DETAIL_MAX] so that an extreme mutation cannot pinch a part away.
    輪廓倍率，從 d0 內插到 d1。z 是單位複數，z 的 n 次方直接給出 cos(nθ) 與 sin(nθ)。
    限制在上下限之間，避免極端突變把部位掐斷。"""
    rows = max(len(d0), len(d1))
    pad0 = np.vstack([d0, np.zeros((rows - len(d0), 2))])
    pad1 = np.vstack([d1, np.zeros((rows - len(d1), 2))])
    m = pad0[0, 0] + s * (pad1[0, 0] - pad0[0, 0])
    zn = np.ones_like(z)
    for n in range(1, rows):
        zn = zn * z
        a = pad0[n, 0] + s * (pad1[n, 0] - pad0[n, 0])
        b = pad0[n, 1] + s * (pad1[n, 1] - pad0[n, 1])
        m = m + a * zn.real + b * zn.imag
    return np.clip(m, DETAIL_MIN, DETAIL_MAX)


def tube_genome_to_skeleton(g: fd.Genome, default_bones: int = 5, bones: dict | None = None,
                            detail_harmonics: int = 6) -> SkeletonGenome:
    """Sample each Fourier tube at J+1 points -> joints and thicknesses.
    The tube's cross-section outlines become the detail gene (polar Fourier, `detail_harmonics` terms).
    把每條傅立葉管取樣成 J+1 個關節與粗細；管子的截面輪廓變成細節基因。"""
    bones = bones or {}
    theta = np.linspace(0.0, fd.TAU, 64, endpoint=False)
    dense = np.linspace(0.0, fd.TAU, 360, endpoint=False)
    parts = []
    for t in g.tubes:
        n = int(bones.get(t.name, default_bones))
        s = np.linspace(0.0, 1.0, n + 1)
        joints = fd.eval_cosine_series(t.spine, s)
        r = np.clip(fd.eval_cosine_series(t.radius, s), 0.004, None)
        m0 = np.linalg.norm(fd.eval_section(t.sect0, theta), axis=1).mean()   # mean section radius
        m1 = np.linalg.norm(fd.eval_section(t.sect1, theta), axis=1).mean()
        r = r * ((1.0 - s) * m0 + s * m1)
        parts.append(BonePart(
            name=t.name, offsets=np.diff(joints, axis=0), radii=r,
            blend=float(np.clip(0.3 * r[0], 0.012, 0.05)),
            origin=joints[0].copy() if t.parent is None else np.zeros(3),
            parent=t.parent, attach=float(t.attach), mirror=bool(t.mirror),
            tags=list(t.tags), is_core=bool(t.is_core), meta=dict(t.meta),
            detail0=fit_polar_detail(fd.eval_section(t.sect0, dense), m0, detail_harmonics),
            detail1=fit_polar_detail(fd.eval_section(t.sect1, dense), m1, detail_harmonics),
        ))
    return SkeletonGenome(parts)


@dataclass
class Segment:
    a: np.ndarray
    b: np.ndarray
    ra: float
    rb: float
    frame_a: np.ndarray | None = None   # (2, 3): [binormal, normal] at joint a / 關節 a 的截面座標軸
    frame_b: np.ndarray | None = None
    sa: float = 0.0                     # chain parameter at a and b / 在鏈上的位置
    sb: float = 1.0


def develop_segments(g: SkeletonGenome, use_detail: bool = True) -> list[dict]:
    """Genome -> list of placed pieces {name, gene, k, segments, detail}. Parents must precede children.
    Mirrored parts give a left and a right piece. Positive y = the creature's left.
    Cross-section angle 0 points along the binormal, 90 degrees along the normal (same as the tubes).
    基因組 -> 放好位置的骨頭段。父部位要排在子部位前面；鏡像部位會產生左右各一份。
    截面角度 0 度沿副法線、90 度沿法線（與傅立葉管相同）。"""
    joints_of: dict[str, np.ndarray] = {}
    pieces = []
    flip = np.array([1.0, -1.0, 1.0])
    for p in g.parts:
        if p.parent is None:
            start = np.asarray(p.origin, dtype=float)
        else:
            start = point_on_chain(joints_of[p.parent], p.attach)
        joints = chain_joints(p, start)
        joints_of[p.name] = joints
        _, nrm, binrm = fd.rotation_minimizing_frames(joints)
        j = p.n_bones
        segs = [Segment(joints[i], joints[i + 1], float(p.radii[i]), float(p.radii[i + 1]),
                        np.stack([binrm[i], nrm[i]]), np.stack([binrm[i + 1], nrm[i + 1]]),
                        i / j, (i + 1) / j) for i in range(j)]
        detail = (p.detail0, p.detail1) if (use_detail and p.detail0 is not None
                                             and p.detail1 is not None) else None
        if p.radial >= 2 and p.parent is not None:
            pj = joints_of[p.parent]
            u = float(np.clip(p.attach, 0.0, 1.0)) * (len(pj) - 1)
            i0 = min(int(np.floor(u)), len(pj) - 2)
            axis = pj[i0 + 1] - pj[i0]
            axis = axis / (np.linalg.norm(axis) + 1e-12)
            for c in range(p.radial):
                rot = rotation_about(axis, fd.TAU * c / p.radial)
                turned = [Segment(start + rot @ (s.a - start), start + rot @ (s.b - start), s.ra, s.rb,
                                  s.frame_a @ rot.T, s.frame_b @ rot.T, s.sa, s.sb) for s in segs]
                pieces.append({"name": f"{p.name}_{c}", "gene": p.name, "k": p.blend, "segments": turned,
                               "detail": detail})
        elif p.mirror:
            shift = np.array([0.0, 2.0 * start[1], 0.0])
            mirrored = [Segment(s.a * flip + shift, s.b * flip + shift, s.ra, s.rb,
                                s.frame_a * flip, s.frame_b * flip, s.sa, s.sb) for s in segs]
            pieces.append({"name": f"{p.name}_L", "gene": p.name, "k": p.blend, "segments": segs,
                           "detail": detail})
            pieces.append({"name": f"{p.name}_R", "gene": p.name, "k": p.blend, "segments": mirrored,
                           "detail": detail})
        else:
            pieces.append({"name": p.name, "gene": p.name, "k": p.blend, "segments": segs,
                           "detail": detail})
    return pieces


# =============================================================================
# Implicit surface / 隱式曲面
# =============================================================================

def sd_round_cone(p: np.ndarray, a: np.ndarray, b: np.ndarray, r1: float, r2: float) -> np.ndarray:
    """Exact signed distance to a round cone (a bone with a different radius at each end).
    Vectorised form of Inigo Quilez's sdRoundCone. p: (..., 3).
    到「兩端半徑不同的骨頭」的精確有號距離。"""
    ba = b - a
    l2 = float(ba @ ba)
    rr = r1 - r2
    if l2 <= rr * rr + 1e-12:                         # one end swallows the other / 一端包住另一端
        c, r = (a, r1) if r1 >= r2 else (b, r2)
        return np.linalg.norm(p - c, axis=-1) - r
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pa = p - a
    y = pa @ ba
    z = y - l2
    w = pa * l2 - ba * y[..., None]
    x2 = np.einsum("...i,...i->...", w, w)
    y2 = y * y * l2
    z2 = z * z * l2
    k = np.sign(rr) * rr * rr * x2
    d_b = np.sqrt(x2 + z2) * il2 - r2
    d_a = np.sqrt(x2 + y2) * il2 - r1
    d_m = (np.sqrt(x2 * a2 * il2) + y * rr) * il2 - r1
    return np.where(np.sign(z) * a2 * z2 > k, d_b, np.where(np.sign(y) * a2 * y2 < k, d_a, d_m))


def detail_offset(p: np.ndarray, seg: Segment, ra: float, rb: float, detail) -> np.ndarray:
    """How far the outline moves the round skin outward at each point (negative = inward).
    Faded to zero towards the end caps so the tips stay round.
    輪廓把圓形的皮往外推多少（負值 = 往內）。靠近兩端的圓頭時漸漸歸零，尖端保持圓的。"""
    ab = seg.b - seg.a
    l2 = max(float(ab @ ab), 1e-12)
    t = np.clip(((p - seg.a) @ ab) / l2, 0.0, 1.0)
    w = p - (seg.a + t[..., None] * ab)
    binrm = (1.0 - t)[..., None] * seg.frame_a[0] + t[..., None] * seg.frame_b[0]
    nrm = (1.0 - t)[..., None] * seg.frame_a[1] + t[..., None] * seg.frame_b[1]
    u = np.einsum("...i,...i->...", w, binrm)
    v = np.einsum("...i,...i->...", w, nrm)
    rho = np.sqrt(u * u + v * v)
    z = np.where(rho > 1e-12, (u + 1j * v) / np.maximum(rho, 1e-12), 1.0 + 0.0j)
    m = polar_multiplier(detail[0], detail[1], z, seg.sa + t * (seg.sb - seg.sa))
    side = np.clip(rho / (np.linalg.norm(w, axis=-1) + 1e-9), 0.0, 1.0)
    return (ra + t * (rb - ra)) * (m - 1.0) * side


def build_field(pieces: list[dict], voxel: float):
    """Sample g = -log(sum_p exp(-d_p / k_p)) on a grid. Returns (g, owner, lo).
    owner[i,j,k] = index of the piece with the smallest d_p / k_p (used for colouring).
    Radii below 0.9 voxel are thickened to 0.9 voxel so thin tips do not break into fragments.
    在格點上取樣 g。owner 記錄每個格點最接近哪一塊（著色用）。
    小於 0.9 格的半徑會加粗到 0.9 格，避免細尖端碎成小塊。"""
    r_min = 0.9 * voxel
    pts = np.vstack([np.vstack([s.a, s.b]) for pc in pieces for s in pc["segments"]])
    r_max = max(max(s.ra, s.rb) for pc in pieces for s in pc["segments"])
    k_max = max(pc["k"] for pc in pieces)
    pad = r_max + 8.0 * k_max + 3.0 * voxel
    lo = pts.min(axis=0) - pad
    hi = pts.max(axis=0) + pad
    shape = np.ceil((hi - lo) / voxel).astype(int) + 1
    total = np.zeros(shape, dtype=np.float64)
    best = np.full(shape, np.inf, dtype=np.float32)
    owner = np.zeros(shape, dtype=np.int16)

    for idx, pc in enumerate(pieces):
        k = float(pc["k"])
        segs = pc["segments"]
        seg_pts = np.vstack([np.vstack([s.a, s.b]) for s in segs])
        reach = max(max(s.ra, s.rb, r_min) for s in segs) + 8.0 * k + voxel
        i0 = np.maximum(np.floor((seg_pts.min(axis=0) - reach - lo) / voxel).astype(int), 0)
        i1 = np.minimum(np.ceil((seg_pts.max(axis=0) + reach - lo) / voxel).astype(int) + 1, shape)
        axes = [lo[d] + voxel * np.arange(i0[d], i1[d]) for d in range(3)]
        p = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
        detail = pc.get("detail")
        radii = [(max(s.ra, r_min), max(s.rb, r_min)) for s in segs]
        rounds = [sd_round_cone(p, s.a, s.b, ra, rb) for s, (ra, rb) in zip(segs, radii)]
        if detail is None:                             # exact union inside one part / 同部位內精確聯集
            d = np.minimum.reduce(rounds)
        else:
            # The outline moves a bone's skin by at most (DETAIL_MAX - 1) * R outward and
            # (1 - DETAIL_MIN) * R inward, so `upper` is a ceiling for the final distance. A bone whose
            # best possible value is above that ceiling cannot be the nearest one there: skip it.
            # This pruning is exact. / 輪廓最多把皮往外推 (DETAIL_MAX-1)R、往內縮 (1-DETAIL_MIN)R，
            # 所以 upper 是最終距離的上限；某根骨頭的最佳可能值若高於上限，就不可能是最近的，直接略過（精確）。
            upper = np.minimum.reduce([dr + (1.0 - DETAIL_MIN) * max(ra, rb)
                                       for dr, (ra, rb) in zip(rounds, radii)])
            d = np.full(p.shape[:3], np.inf)
            for s, (ra, rb), dr in zip(segs, radii, rounds):
                live = (dr - (DETAIL_MAX - 1.0) * max(ra, rb)) <= upper
                if live.any():
                    d[live] = np.minimum(d[live], dr[live] - detail_offset(p[live], s, ra, rb, detail))
        q = d / k
        sub = tuple(slice(i0[d_], i1[d_]) for d_ in range(3))
        total[sub] += np.exp(-np.clip(q, -60.0, 60.0))
        closer = q < best[sub]
        best[sub] = np.where(closer, q, best[sub])
        owner[sub] = np.where(closer, idx, owner[sub])

    g = -np.log(np.maximum(total, 1e-30))
    return g, owner, lo


def extract_mesh(g: np.ndarray, lo: np.ndarray, voxel: float) -> Mesh:
    verts, faces, _, _ = _sk_measure.marching_cubes(g, level=0.0, spacing=(voxel, voxel, voxel))
    mesh = Mesh(verts + lo, faces.astype(np.int64))
    if fd.signed_volume(mesh) < 0:                    # normals outward / 法線朝外
        mesh.faces = mesh.faces[:, ::-1].copy()
    return mesh


def build_sdf_creature(g: SkeletonGenome, voxel: float, use_detail: bool = True):
    """Returns (mesh, face_piece, pieces). face_piece[f] = index of the piece each triangle belongs to.
    use_detail=False gives the plain round skeleton skin.
    回傳（網格、每個三角形屬於哪一塊、所有骨頭段）。use_detail=False 會得到沒有細節的圓形皮。"""
    pieces = develop_segments(g, use_detail)
    field_g, owner, lo = build_field(pieces, voxel)
    mesh = extract_mesh(field_g, lo, voxel)
    centroids = mesh.vertices[mesh.faces].mean(axis=1)
    ijk = np.clip(np.rint((centroids - lo) / voxel).astype(int), 0, np.array(owner.shape) - 1)
    face_piece = owner[ijk[:, 0], ijk[:, 1], ijk[:, 2]]
    return mesh, face_piece, pieces


# =============================================================================
# Mesh checks / 網格檢查
# =============================================================================

def mesh_report(mesh: Mesh) -> dict:
    """closed    : every edge is shared by exactly two triangles, with opposite directions
       components: number of separate connected pieces
       封閉：每條邊剛好被兩個三角形共用且方向相反；components：分開的連通塊數。"""
    f = mesh.faces
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    n = int(mesh.vertices.shape[0])
    key = e[:, 0].astype(np.int64) * n + e[:, 1]
    rev = e[:, 1].astype(np.int64) * n + e[:, 0]
    uniq, counts = np.unique(key, return_counts=True)
    closed = bool(np.all(counts == 1) and np.all(np.isin(rev, uniq)))
    graph = coo_matrix((np.ones(len(e), dtype=np.int8), (e[:, 0], e[:, 1])), shape=(n, n))
    used = np.zeros(n, dtype=bool)
    used[f.ravel()] = True
    _, labels = connected_components(graph, directed=False)
    return {"closed": closed, "components": int(len(np.unique(labels[used]))),
            "triangles": int(len(f)), "vertices": n, "volume": float(fd.signed_volume(mesh))}


def merge_parts(parts: list[tuple[str, Mesh]]) -> Mesh:
    verts, faces, off = [], [], 0
    for _, m in parts:
        verts.append(m.vertices)
        faces.append(m.faces + off)
        off += len(m.vertices)
    return Mesh(np.vstack(verts), np.vstack(faces))


def slice_mesh(mesh: Mesh, axis: int, value: float) -> np.ndarray:
    """Cut a mesh with the plane coord[axis] = value -> (N, 2, 2) line segments in the other two axes.
    用平面切網格，回傳另外兩個軸上的線段。"""
    v, f = mesh.vertices, mesh.faces
    d = v[:, axis] - value
    d = np.where(d == 0.0, 1e-12, d)
    td = d[f]
    cross = (td.min(axis=1) < 0) & (td.max(axis=1) > 0)
    keep = [c for c in range(3) if c != axis]
    out = []
    for tri, dd in zip(f[cross], td[cross]):
        pts = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if dd[i] * dd[j] < 0:
                t = dd[i] / (dd[i] - dd[j])
                pts.append(v[tri[i]] + t * (v[tri[j]] - v[tri[i]]))
        if len(pts) == 2:
            out.append([pts[0][keep], pts[1][keep]])
    return np.array(out) if out else np.zeros((0, 2, 2))


def outline_polar(segments: np.ndarray, centre: np.ndarray, n: int = 180) -> np.ndarray:
    """Radius of a slice outline as a function of angle around `centre` (for star-shaped outlines).
    切面輪廓繞著 centre 的半徑對角度的函數（適用於星形輪廓）。"""
    pts = segments.reshape(-1, 2) - centre
    ang = np.arctan2(pts[:, 1], pts[:, 0])
    rad = np.hypot(pts[:, 0], pts[:, 1])
    order = np.argsort(ang)
    grid = np.linspace(-np.pi, np.pi, n, endpoint=False)
    return np.interp(grid, ang[order], rad[order], period=fd.TAU)


def outline_stats(segments: np.ndarray) -> dict:
    pts = segments.reshape(-1, 2)
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    return {"width": float(hi[0] - lo[0]), "height": float(hi[1] - lo[1]),
            "centre": ((lo + hi) / 2.0).tolist()}


# =============================================================================
# Locality test / 局部性測試
# =============================================================================

def locality_test(tube_leg: fd.TubeGene, bone_leg: BonePart, rel: float = 0.05) -> dict:
    """Change ONE gene; report the fraction of the limb's length where the result changes by more than
    `rel` of the largest change. Smaller = more local.
    只改一個基因，回報肢體長度中「變化量超過最大變化 5%」的比例。越小越局部。"""
    s = np.linspace(0.0, 1.0, 801)

    def frac(delta):
        delta = np.abs(delta)
        return float(np.mean(delta > rel * delta.max()))

    # thickness: Fourier radius harmonic 3  vs  thickness at the middle joint
    rad = tube_leg.radius.copy()
    rad[3] += 0.02
    f_thick = frac(fd.eval_cosine_series(rad, s) - fd.eval_cosine_series(tube_leg.radius, s))
    t_j = np.linspace(0.0, 1.0, bone_leg.n_bones + 1)
    r2 = bone_leg.radii.copy()
    mid = bone_leg.n_bones // 2
    r2[mid] += 0.02
    s_thick = frac(np.interp(s, t_j, r2) - np.interp(s, t_j, bone_leg.radii))

    # position: Fourier spine harmonic 2  vs  the middle bone
    sp = tube_leg.spine.copy()
    sp[2] += np.array([0.05, 0.0, 0.0])
    f_pos = frac(np.linalg.norm(fd.eval_cosine_series(sp, s) - fd.eval_cosine_series(tube_leg.spine, s), axis=1))
    off = bone_leg.offsets.copy()
    off[mid] += np.array([0.05, 0.0, 0.0])
    j0 = chain_joints(bone_leg, np.zeros(3))
    j1 = chain_joints(dataclasses.replace(bone_leg, offsets=off), np.zeros(3))
    dj = np.linalg.norm(j1 - j0, axis=1)
    s_pos = frac(np.interp(s, t_j, dj))

    return {"thickness_fourier": f_thick, "thickness_skeleton": s_thick,
            "position_fourier": f_pos, "position_skeleton": s_pos}


# =============================================================================
# Gene-level crossover and mutation on skeleton genomes / 骨架基因組的基因層交配與突變
# =============================================================================

@dataclass
class SkeletonInheritanceConfig:
    """Same field names as RTIS InheritanceConfig / FourierInheritanceConfig where they overlap.
    重疊的欄位名稱與 RTIS InheritanceConfig、FourierInheritanceConfig 相同。"""
    inheritance_factor: float = 0.70
    core_lock: float = 0.90
    alpha: float = 0.50                # chance that a gene comes from parent A / 基因來自 A 的機率
    parent_a_dominance: float = 0.50   # which parent supplies name / tags / topology / 拓樸跟誰
    match_threshold: float = 0.25
    micro_budget: int = 4
    micro_rate: float = 0.5
    micro_sigma: float = 0.15
    detail_sigma: float = 0.05         # mutation size of one detail harmonic / 細節諧波的突變幅度


def match_parts(ga: SkeletonGenome, gb: SkeletonGenome, cfg: SkeletonInheritanceConfig) -> dict:
    """Greedy one-to-one matching by tags (+ attach position). Same rule as fourier_genetics.match_tubes.
    用標籤（＋接點位置）做貪婪一對一配對，規則同 fourier_genetics.match_tubes。"""
    root_a = next(p for p in ga.parts if p.parent is None)
    root_b = next(p for p in gb.parts if p.parent is None)
    pairs = {root_a.name: (root_b.name, 1.0)}
    used_b = {root_b.name}
    cand = []
    for pa in ga.parts:
        if pa.parent is None:
            continue
        for pb in gb.parts:
            if pb.parent is None or arrangement(pa) != arrangement(pb):
                continue
            s = fg.tag_similarity(pa.tags, pb.tags)
            if s < cfg.match_threshold:
                continue
            cand.append((s + 0.25 * (1.0 - abs(pa.attach - pb.attach)), pa.name, pb.name))
    for s, na, nb in sorted(cand, key=lambda c: -c[0]):
        if na not in pairs and nb not in used_b:
            pairs[na] = (nb, s)
            used_b.add(nb)
    return pairs


def cross_part(pa: BonePart, pb: BonePart, cfg: SkeletonInheritanceConfig,
               rng: np.random.Generator) -> tuple[BonePart, dict]:
    """Each gene (one bone, one joint thickness, blend, attach, the detail pack) is copied whole
    from A or from B.
    每個基因（一根骨頭、一個關節粗細、融合度、接點、整包細節）整個從 A 或 B 複製。"""
    n = max(pa.n_bones, pb.n_bones)
    a, b = resample_part(pa, n), resample_part(pb, n)
    bone_a = rng.random(n) < cfg.alpha
    rad_a = rng.random(n + 1) < cfg.alpha
    blend_a = rng.random() < cfg.alpha
    attach_a = rng.random() < cfg.alpha
    detail_a = rng.random() < cfg.alpha
    template = pa if rng.random() < cfg.parent_a_dominance else pb
    fa, fb = pa.meta.get("ancestry_a", 0.5), pb.meta.get("ancestry_a", 0.5)
    picks = np.concatenate([bone_a, rad_a, [blend_a, attach_a, detail_a]])
    src = pa if detail_a else pb
    child = dataclasses.replace(
        template,
        offsets=np.where(bone_a[:, None], a.offsets, b.offsets),
        radii=np.where(rad_a, a.radii, b.radii),
        blend=a.blend if blend_a else b.blend,
        attach=a.attach if attach_a else b.attach,
        detail0=None if src.detail0 is None else src.detail0.copy(),
        detail1=None if src.detail1 is None else src.detail1.copy(),
        origin=np.array(template.origin, dtype=float),
        tags=list(template.tags),
        meta={"ancestry_a": float(np.mean(np.where(picks, fa, fb)))},
    )
    return child, {"A": pa.name, "B": pb.name, "template": "A" if template is pa else "B",
                   "bones": "".join("A" if x else "B" for x in bone_a),
                   "thickness": "".join("A" if x else "B" for x in rad_a),
                   "detail": "A" if detail_a else "B"}


def crossover(ga: SkeletonGenome, gb: SkeletonGenome, cfg: SkeletonInheritanceConfig,
              rng: np.random.Generator) -> tuple[SkeletonGenome, dict]:
    pairs = match_parts(ga, gb, cfg)
    matched_b = {nb for nb, _ in pairs.values()}
    parts_b = {p.name: p for p in gb.parts}
    child: list[BonePart] = []
    name_map: dict[tuple[str, str], str] = {}
    used: set[str] = set()
    log = {"matches": [], "unmatched_inherited": [], "dropped": []}

    def unique(name: str) -> str:
        base, k = name, 2
        while name in used:
            name, k = f"{base}_{k}", k + 1
        used.add(name)
        return name

    def resolve(options):
        for src, p in options:
            if p.parent is None:
                return None
            if (src, p.parent) in name_map:
                return name_map[(src, p.parent)]
        return False

    def copy_part(p: BonePart, name: str, parent) -> BonePart:
        return dataclasses.replace(p, name=name, parent=parent, offsets=p.offsets.copy(),
                                   radii=p.radii.copy(), origin=np.array(p.origin, dtype=float),
                                   tags=list(p.tags), meta=dict(p.meta))

    p_periph = min(1.0, cfg.inheritance_factor)       # dominance 0.5 * 2, as in RTIS / 與 RTIS 相同
    for pa in ga.parts:
        if pa.name in pairs:
            pb = parts_b[pairs[pa.name][0]]
            if not (pa.parent is None or pa.is_core or pb.is_core):
                if rng.random() >= 1.0 - (1.0 - p_periph) ** 2:
                    log["dropped"].append(f"{pa.name}~{pb.name}")
                    continue
            part, info = cross_part(pa, pb, cfg, rng)
            order = [("A", pa), ("B", pb)] if info["template"] == "A" else [("B", pb), ("A", pa)]
            parent = resolve(order)
            if parent is False:
                log["dropped"].append(f"{pa.name}~{pb.name} (parent missing)")
                continue
            name = unique(part.name)
            child.append(dataclasses.replace(part, name=name, parent=parent))
            name_map[("A", pa.name)] = name_map[("B", pb.name)] = name
            log["matches"].append({"child_part": name, "score": round(pairs[pa.name][1], 3), **info})
        else:
            parent = resolve([("A", pa)])
            if rng.random() < (cfg.core_lock if pa.is_core else p_periph) and parent is not False:
                name = unique(pa.name)
                child.append(copy_part(pa, name, parent))
                name_map[("A", pa.name)] = name
                log["unmatched_inherited"].append(f"A:{pa.name}")
            else:
                log["dropped"].append(f"A:{pa.name}")
    for pb in gb.parts:
        if pb.name in matched_b:
            continue
        parent = resolve([("B", pb)])
        if rng.random() < (cfg.core_lock * 0.5 if pb.is_core else p_periph) and parent is not False:
            name = unique(pb.name)
            child.append(copy_part(pb, name, parent))
            name_map[("B", pb.name)] = name
            log["unmatched_inherited"].append(f"B:{pb.name}")
        else:
            log["dropped"].append(f"B:{pb.name}")
    return SkeletonGenome(child), log


def mutate(g: SkeletonGenome, cfg: SkeletonInheritanceConfig,
           rng: np.random.Generator) -> tuple[SkeletonGenome, list[str]]:
    """Micro mutation: one named gene at a time (a bone, a joint thickness, or one detail harmonic).
    微突變：一次只改一個具名基因（一根骨頭、一個關節粗細，或細節裡的一階諧波）。"""
    parts = [dataclasses.replace(
        p, offsets=p.offsets.copy(), radii=p.radii.copy(),
        detail0=None if p.detail0 is None else p.detail0.copy(),
        detail1=None if p.detail1 is None else p.detail1.copy()) for p in g.parts]
    events = []
    for _ in range(int(rng.binomial(cfg.micro_budget, cfg.micro_rate))):
        p = parts[int(rng.integers(len(parts)))]
        roll = rng.random()
        if roll < 0.4:
            i = int(rng.integers(p.n_bones))
            length = float(np.linalg.norm(p.offsets[i]))
            p.offsets[i] = p.offsets[i] * (1.0 + rng.normal(0.0, cfg.micro_sigma)) \
                + rng.normal(0.0, cfg.micro_sigma * 0.5 * length, size=3)
            events.append(f"{p.name}: bone {i}")
        elif roll < 0.8:
            i = int(rng.integers(p.n_bones + 1))
            p.radii[i] = max(0.004, p.radii[i] * (1.0 + rng.normal(0.0, cfg.micro_sigma)))
            events.append(f"{p.name}: thickness at joint {i}")
        else:
            if p.detail0 is None or p.detail1 is None:    # start from a plain circle / 從正圓開始
                base = np.zeros((7, 2))
                base[0, 0] = 1.0
                p.detail0, p.detail1 = base.copy(), base.copy()
            h = int(rng.integers(1, min(len(p.detail0), len(p.detail1))))
            noise = rng.normal(0.0, cfg.detail_sigma, size=2)
            p.detail0[h] += noise                         # same change at both ends: runs along the part
            p.detail1[h] += noise                         # 兩端加同樣的量：沿著整個部位延伸
            events.append(f"{p.name}: detail harmonic {h}")
    return enforce_symmetry(SkeletonGenome(parts)), events


def enforce_symmetry(g: SkeletonGenome) -> SkeletonGenome:
    """Midline parts stay on the y = 0 plane and keep a left/right-symmetric outline.
    中軸部位留在 y = 0 平面，輪廓保持左右對稱。"""
    out = []
    for p in g.parts:
        if p.mirror:
            out.append(p)
            continue
        off = p.offsets.copy()
        off[:, 1] = 0.0
        org = np.array(p.origin, dtype=float)
        org[1] = 0.0
        d0 = None if p.detail0 is None else p.detail0 * detail_symmetry_mask(len(p.detail0))
        d1 = None if p.detail1 is None else p.detail1 * detail_symmetry_mask(len(p.detail1))
        out.append(dataclasses.replace(p, offsets=off, origin=org, detail0=d0, detail1=d1))
    return SkeletonGenome(out)


def reproduce(ga: SkeletonGenome, gb: SkeletonGenome, cfg: SkeletonInheritanceConfig,
              rng: np.random.Generator) -> tuple[SkeletonGenome, dict]:
    child, log = crossover(ga, gb, cfg, rng)
    child, events = mutate(enforce_symmetry(child), cfg, rng)
    log["mutations"] = events
    return child, log


def with_ancestry(g: SkeletonGenome, value: float) -> SkeletonGenome:
    return SkeletonGenome([dataclasses.replace(p, meta={**p.meta, "ancestry_a": value}) for p in g.parts])


# =============================================================================
# Drawing / 繪圖
# =============================================================================

def draw_mesh(ax, mesh: Mesh, face_rgb: np.ndarray, title: str, light=(0.4, -0.7, 0.8), zoom: float = 1.1):
    light = np.asarray(light, dtype=float)
    light /= np.linalg.norm(light)
    tris = mesh.vertices[mesh.faces]
    normal = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    normal /= np.linalg.norm(normal, axis=1, keepdims=True) + 1e-12
    shade = 0.3 + 0.7 * np.clip(normal @ light, 0.0, 1.0)
    ax.add_collection3d(Poly3DCollection(tris, facecolors=np.clip(shade[:, None] * face_rgb, 0, 1),
                                         edgecolors="none", linewidths=0))
    ax.view_init(elev=14, azim=-62)
    fd.style_axes(ax, tris.reshape(-1, 3), pad=0.02, title=title, axis_off=True, zoom=zoom)


def ancestry_colours(g: SkeletonGenome, pieces: list[dict], face_piece: np.ndarray) -> np.ndarray:
    genes = {p.name: p for p in g.parts}
    fracs = np.array([float(genes[pc["gene"]].meta.get("ancestry_a", 0.5)) for pc in pieces])
    f = fracs[face_piece][:, None]
    return f * COLOUR_A + (1.0 - f) * COLOUR_B


def plot_slice(ax, parts: list[tuple[str, Mesh]], x_value: float, title: str, palette,
               show_xlabel: bool = True) -> None:
    for i, (_, m) in enumerate(parts):
        segs = slice_mesh(m, 0, x_value)
        if len(segs):
            ax.add_collection(LineCollection(segs, colors=[palette[i % len(palette)]], linewidths=1.6))
    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.08)
    if show_xlabel:
        ax.set_xlabel("y (left / right)")
    ax.set_ylabel("z (up)")
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.2)


# =============================================================================
# Main / 主程式
# =============================================================================

def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Skeleton + implicit surface (+ Fourier detail) vs Fourier tubes")
    ap.add_argument("--out", default="out_sdf")
    ap.add_argument("--voxel", type=float, default=0.015, help="export grid size / 匯出用格點大小")
    ap.add_argument("--preview-voxel", type=float, default=0.03, help="grid size for figures and checks")
    ap.add_argument("--detail-voxel", type=float, default=0.02, help="grid size for detail_layer.png")
    ap.add_argument("--body-bones", type=int, default=9,
                    help="bones in the body chain (5 = the 11-11 run) / 身體鏈的骨頭數（5 = 11-11 的版本）")
    ap.add_argument("--children", type=int, default=4)
    ap.add_argument("--check-generations", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"voxel": args.voxel, "preview_voxel": args.preview_voxel, "seed": args.seed,
                    "body_bones": args.body_bones}

    tube = {"quadruped": fd.default_genome(), "biped": fg.biped_genome()}
    # body: 9 bones by default (decided 11-12: 5 bones left the quadruped's mid-body ~5% too thin)
    # arm_front and horn use different counts on purpose, to exercise resampling in crossover
    # 身體預設 9 根（11-12 決定：5 根時四足中段偏細約 5%）；手和角故意用不同骨頭數，測試交配時的重新取樣
    bone_counts = {"body": args.body_bones, "arm_front": 4, "horn": 3}
    skel = {k: tube_genome_to_skeleton(v, bones=bone_counts) for k, v in tube.items()}

    # ---- 1 + 2. build all versions and compare / 各種做法各建一次並比較 --------------------
    print("Comparison on the same creatures / 同樣的生物，三種做法")
    print(f"{'':<11}{'method':<22}{'genes':>6}{'pieces':>8}{'closed':>8}{'triangles':>11}{'build s':>9}")
    built = {}
    report["comparison"] = {}
    for name in ("quadruped", "biped"):
        t0 = time.perf_counter()
        parts = fd.build_creature(tube[name])
        t_tube = time.perf_counter() - t0
        rep_t = mesh_report(merge_parts(parts))
        # one gene = one coefficient row, plus the attach position of every non-root tube
        # 一個基因 = 一列係數，再加上每條非根管的接點位置（與骨架版用同一種算法）
        n_rows = sum(getattr(t, f).shape[0] for t in tube[name].tubes for f in fg.SHAPE_FIELDS) \
            + sum(1 for t in tube[name].tubes if t.parent is not None)
        print(f"{name:<11}{'Fourier tubes':<22}{n_rows:>6}{rep_t['components']:>8}"
              f"{str(rep_t['closed']):>8}{rep_t['triangles']:>11}{t_tube:>9.2f}")
        report["comparison"][name] = {
            "fourier": {**rep_t, "genes": int(n_rows), "build_seconds": round(t_tube, 3)}}
        built[name] = {"tube_parts": parts}
        for key, label, use_detail in (("round", "skeleton, round", False),
                                       ("detail", "skeleton + detail", True)):
            t0 = time.perf_counter()
            mesh, _, _ = build_sdf_creature(skel[name], args.voxel, use_detail)
            t_sdf = time.perf_counter() - t0
            rep_s = mesh_report(mesh)
            genes = skel[name].gene_count(include_detail=use_detail)
            print(f"{'':<11}{label:<22}{genes:>6}{rep_s['components']:>8}"
                  f"{str(rep_s['closed']):>8}{rep_s['triangles']:>11}{t_sdf:>9.2f}")
            report["comparison"][name][f"skeleton_{key}"] = {
                **rep_s, "genes": genes, "build_seconds": round(t_sdf, 3)}
            built[name][key] = mesh
        fd.write_obj(out / f"{name}_sdf.obj", [(name, built[name]["detail"])])
        (out / f"{name}_sdf.json").write_text(json.dumps(skel[name].to_json(), indent=1), encoding="utf-8")

    # ---- detail fidelity: body outline against the Fourier tube / 細節還原度：身體輪廓對照傅立葉管 ----
    x_body = {"quadruped": 0.0, "biped": 0.1}           # planes that cut only the body / 只切到身體的平面
    outlines = {}
    report["outline"] = {}
    print("\nBody outline, compared with the Fourier tube / 身體輪廓，與傅立葉管對照")
    print(f"{'':<11}{'method':<22}{'width':>8}{'height':>8}{'w / h':>8}{'outline err':>13}{'shape-only':>12}")
    for name in ("quadruped", "biped"):
        cut = [slice_mesh(m, 0, x_body[name]) for _, m in built[name]["tube_parts"]]
        cut = [c for c in cut if len(c)]
        seg = {"tube": np.concatenate(cut),
               "round": slice_mesh(built[name]["round"], 0, x_body[name]),
               "detail": slice_mesh(built[name]["detail"], 0, x_body[name])}
        centre = np.array(outline_stats(seg["tube"])["centre"])
        polar = {k: outline_polar(v, centre) for k, v in seg.items()}
        outlines[name] = seg
        report["outline"][name] = {"x": x_body[name], "tube_parts_cut": len(cut)}
        for key, label in (("tube", "Fourier tubes"), ("round", "skeleton, round"),
                           ("detail", "skeleton + detail")):
            st = outline_stats(seg[key])
            # outline error: RMS radius difference / mean tube radius.
            # shape-only: same after scaling both outlines to mean radius 1 (removes the size difference).
            # 輪廓誤差：半徑差的 RMS ÷ 管的平均半徑；shape-only：兩者都縮放到平均半徑 1 後再算（去掉大小差異）。
            err = float(np.sqrt(np.mean((polar[key] - polar["tube"]) ** 2)) / polar["tube"].mean())
            shape = float(np.sqrt(np.mean((polar[key] / polar[key].mean()
                                           - polar["tube"] / polar["tube"].mean()) ** 2)))
            e1, e2 = ("(reference)", "") if key == "tube" else (f"{err:.1%}", f"{shape:.1%}")
            print(f"{name if key == 'tube' else '':<11}{label:<22}{st['width']:>8.3f}{st['height']:>8.3f}"
                  f"{st['width'] / st['height']:>8.3f}{e1:>13}{e2:>12}")
            report["outline"][name][key] = {"width": st["width"], "height": st["height"],
                                            "relative_rms_error": err, "shape_only_error": shape}

    # ---- 3. locality / 局部性 -------------------------------------------------------------
    leg_t = next(t for t in tube["quadruped"].tubes if t.name == "leg_front")
    leg_s = next(p for p in skel["quadruped"].parts if p.name == "leg_front")
    loc = locality_test(leg_t, leg_s)
    report["locality"] = loc
    print("\nLocality: share of the front leg that changes when ONE gene changes / 改一個基因，前腿有多少比例跟著變")
    print(f"  thickness gene   Fourier {loc['thickness_fourier']:.0%}   skeleton {loc['thickness_skeleton']:.0%}")
    print(f"  position gene    Fourier {loc['position_fourier']:.0%}   skeleton {loc['position_skeleton']:.0%}")

    # ---- comparison figure / 比較圖 --------------------------------------------------------
    pv = args.preview_voxel
    palette = ["#4f81bd", "#c0504d", "#2e8b57", "#8064a2", "#e39b2d", "#3aa6a6", "#7f7f7f", "#b55d9c"]
    fig = plt.figure(figsize=(16, 8.6))
    fig.suptitle("Same creatures, two geometry methods - top: Fourier tubes, "
                 "bottom: skeleton + implicit surface + detail", fontsize=13)
    body_t = tube["quadruped"].tubes[0]
    x_cut = float(fd.eval_cosine_series(body_t.spine, np.array([leg_t.attach]))[0, 0]) + 0.03
    for col, name in enumerate(("quadruped", "biped")):
        ax = fig.add_subplot(2, 3, col + 1, projection="3d")
        m = merge_parts(fd.build_creature(tube[name], n_s=40, n_theta=20))
        draw_mesh(ax, m, np.tile(GREY, (len(m.faces), 1)),
                  f"{name}: Fourier tubes ({len(built[name]['tube_parts'])} separate pieces)")
        ax = fig.add_subplot(2, 3, col + 4, projection="3d")
        m2, _, _ = build_sdf_creature(skel[name], pv)
        draw_mesh(ax, m2, np.tile(GREY, (len(m2.faces), 1)), f"{name}: skeleton + implicit + detail (1 piece)")
    ax = fig.add_subplot(2, 3, 3)
    plot_slice(ax, built["quadruped"]["tube_parts"], x_cut,
               "slice through the front shoulder: walls of each tube cross inside the body", palette,
               show_xlabel=False)
    ax = fig.add_subplot(2, 3, 6)
    plot_slice(ax, [("skin", built["quadruped"]["detail"])], x_cut,
               "same slice: one outline, no inner walls", ["#222222"])
    fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.06, wspace=0.08, hspace=0.14)
    fig.savefig(out / "compare_fourier_vs_sdf.png", dpi=120)
    plt.close(fig)

    # ---- detail figure / 細節層對照圖 -------------------------------------------------------
    dv = args.detail_voxel
    fig = plt.figure(figsize=(19, 8.6))
    fig.suptitle("Detail layer: Fourier tubes  |  skeleton, round  |  skeleton + Fourier detail  |  "
                 "body outline (front view)", fontsize=13)
    for row, name in enumerate(("quadruped", "biped")):
        meshes = [("Fourier tubes", merge_parts(fd.build_creature(tube[name], n_s=40, n_theta=24))),
                  ("skeleton, round", build_sdf_creature(skel[name], dv, False)[0]),
                  ("skeleton + detail", build_sdf_creature(skel[name], dv, True)[0])]
        for col, (label, m) in enumerate(meshes):
            ax = fig.add_subplot(2, 4, row * 4 + col + 1, projection="3d")
            draw_mesh(ax, m, np.tile(GREY, (len(m.faces), 1)), f"{name}: {label}", light=(0.7, -0.4, 0.6))
            ax.view_init(elev=22, azim=-28)
        ax = fig.add_subplot(2, 4, row * 4 + 4)
        for key, colour, style, width, label in (("tube", "#111111", "--", 2.0, "Fourier tube"),
                                                 ("round", "#9aa3ad", "-", 1.6, "skeleton, round"),
                                                 ("detail", "#d1492e", "-", 1.8, "skeleton + detail")):
            ax.add_collection(LineCollection(outlines[name][key], colors=[colour], linewidths=width,
                                             linestyles=style, label=label))
        ax.set_aspect("equal")
        ax.autoscale()
        ax.margins(0.1)
        if row == 1:
            ax.set_xlabel("y (left / right)")
        ax.set_ylabel("z (up)")
        ax.set_title(f"{name}: body outline at x = {x_body[name]}", fontsize=10)
        ax.grid(True, alpha=0.2)
        ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.subplots_adjust(left=0.0, right=0.98, top=0.92, bottom=0.06, wspace=0.05, hspace=0.12)
    fig.savefig(out / "detail_layer.png", dpi=110)
    plt.close(fig)

    # ---- 4. inheritance on skeleton genomes / 骨架基因組上的遺傳 ----------------------------
    cfg = SkeletonInheritanceConfig()
    rng = np.random.default_rng(args.seed)
    a = with_ancestry(skel["quadruped"], 1.0)
    b = with_ancestry(skel["biped"], 0.0)
    print("\nPart matching A <-> B / 部位配對:")
    for na, (nb, s) in match_parts(a, b, cfg).items():
        print(f"  {na:<10} <-> {nb:<10} score {s:.2f}")
    kids, logs = [], {}
    for i in range(args.children):
        child, log = reproduce(a, b, cfg, rng)
        kids.append(child)
        logs[f"F1-{i + 1}"] = log
        detail_src = ", ".join(f"{m['child_part']}:{m['detail']}" for m in log["matches"])
        print(f"  F1-{i + 1}: " + ", ".join(f"{p.name}({p.meta['ancestry_a']:.0%}A)" for p in child.parts)
              + f"\n        detail pack from: {detail_src}"
              + f"\n        mutations: {'; '.join(log['mutations']) or 'none'}")
    (out / "inheritance_log.json").write_text(json.dumps(logs, indent=1), encoding="utf-8")

    ncols = max(2, args.children)
    fig = plt.figure(figsize=(4.2 * ncols, 6.8))
    fig.suptitle("Gene-level crossover on skeleton genomes (with detail) - one closed mesh per creature; "
                 "colour = ancestry (orange A, blue B)", fontsize=13)
    for col, (title, g) in enumerate([("founder A: quadruped", a), ("founder B: biped", b)]):
        ax = fig.add_subplot(2, ncols, col + 1, projection="3d")
        m, fp, pcs = build_sdf_creature(g, pv)
        draw_mesh(ax, m, ancestry_colours(g, pcs, fp), title)
    for i, g in enumerate(kids):
        ax = fig.add_subplot(2, ncols, ncols + i + 1, projection="3d")
        m, fp, pcs = build_sdf_creature(g, pv)
        draw_mesh(ax, m, ancestry_colours(g, pcs, fp), f"F1-{i + 1} = A x B")
        mesh_full, _, _ = build_sdf_creature(g, args.voxel)
        fd.write_obj(out / f"F1-{i + 1}_sdf.obj", [(f"F1-{i + 1}", mesh_full)])
        (out / f"F1-{i + 1}_sdf.json").write_text(json.dumps(g.to_json(), indent=1), encoding="utf-8")
    fig.subplots_adjust(left=0.0, right=1.0, top=0.9, bottom=0.0, wspace=0.0, hspace=0.08)
    fig.savefig(out / "sdf_pedigree.png", dpi=120)
    plt.close(fig)

    # ---- robustness: several generations, every child must be ONE closed mesh ----------------
    # 穩健性：連續幾代，每個子代都必須是一個封閉網格
    population = [a, b]
    stats = {"children": 0, "closed": 0, "single_piece": 0, "part_counts": {}, "worst_components": 1,
             "detail_mutations": 0}
    for _ in range(args.check_generations):
        nxt = []
        for _ in range(8):
            i, j = rng.choice(len(population), size=2, replace=False)
            child, log = reproduce(population[i], population[j], cfg, rng)
            m, _, _ = build_sdf_creature(child, pv)
            rep = mesh_report(m)
            stats["children"] += 1
            stats["closed"] += int(rep["closed"])
            stats["single_piece"] += int(rep["components"] == 1)
            stats["worst_components"] = max(stats["worst_components"], rep["components"])
            stats["detail_mutations"] += sum("detail" in e for e in log["mutations"])
            n = str(len(child.parts))
            stats["part_counts"][n] = stats["part_counts"].get(n, 0) + 1
            nxt.append(child)
        population = nxt
    report["robustness"] = stats
    print(f"\nRobustness over {args.check_generations} generations (grid {pv}, detail on): "
          f"{stats['children']} children, closed {stats['closed']}, single piece {stats['single_piece']}, "
          f"worst piece count {stats['worst_components']}, detail mutations {stats['detail_mutations']}, "
          f"parts per creature {stats['part_counts']}")

    (out / "comparison.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"Done -> {out.resolve()}")


if __name__ == "__main__":
    main()
