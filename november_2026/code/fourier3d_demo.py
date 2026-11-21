#!/usr/bin/env python3
"""
fourier3d_demo.py
=================
3D Fourier epicycles + Fourier-based tube sweeping for procedural 3D model generation.
三維傅立葉本輪 ＋ 用傅立葉係數掃掠管狀曲面，做程序化三維模型生成。

Target: Python 3.10.12 · Dependencies: numpy, matplotlib (Pillow only for --gif)
目標環境：Python 3.10.12 · 相依套件：numpy、matplotlib（只有 --gif 需要 Pillow）

Part A  Closed 3D curve -> Fourier coefficients -> epicycles.
        Each frequency n contributes a_n cos(nt) + b_n sin(nt) with a_n, b_n in R^3,
        i.e. a tilted ELLIPSE in the plane span(a_n, b_n) instead of a 2D circle.
        三維閉合曲線 -> 傅立葉係數 -> 本輪。
        每個頻率 n 貢獻一個位於 span(a_n, b_n) 平面上的「傾斜橢圓」，而不是二維的圓。

Part B  Open spine (cosine series) + closed cross-sections (2D elliptic Fourier)
        + radius profile (cosine series) -> swept tube with rotation-minimizing frames.
        Faces come for free: there is no "fill in the wireframe" step.
        開放脊椎（餘弦級數）＋ 閉合截面（二維橢圓傅立葉）＋ 半徑剖面（餘弦級數）
        -> 用旋轉最小化標架掃掠成管。面直接產生，不需要「補面」。

Part C  A creature = several tubes. All coefficients flatten into one genome vector.
        Mutating low harmonics changes the body plan; high harmonics change details.
        Bilateral symmetry is enforced: limbs are mirrored, midline tubes stay symmetric.
        生物 = 多條管。所有係數攤平成一個基因組向量。
        突變低階係數改變身體藍圖，突變高階係數改變細節。
        強制左右對稱：四肢鏡像，中軸管（身體、脖子、尾巴）保持對稱。

Outputs (default ./out) / 輸出（預設 ./out）:
    partA_curve_fourier.png    reconstructions with N terms + epicycle chain / 不同項數的重建 + 本輪鏈
    partA_epicycles.gif        (--gif) animated epicycles / 本輪動畫
    partB_creatures.png        original creature + mutated variants / 原始生物 + 突變變體
    creature_XX_<band>.obj     meshes, Y-up (Blender's default OBJ import stands them upright)
                               網格，Y 軸朝上（Blender 預設匯入會自動站正）
    creature_XX_<band>.json    genome of each creature (reloadable with --genome)
                               每隻生物的基因組（可用 --genome 重新載入）

Usage / 用法:
    python fourier3d_demo.py
    python fourier3d_demo.py --gif
    python fourier3d_demo.py --curve my_loop.csv --terms 64   # your own closed 3D polyline, x,y,z per row
    python fourier3d_demo.py --sigma 0.3 --per-band 3 --seed 7
    python fourier3d_demo.py --genome out/creature_03_low.json  # evolve from a saved creature
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import colors as mcolors  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

TAU = 2.0 * np.pi


# =============================================================================
# Shared helpers / 共用工具
# =============================================================================

def style_axes(ax, pts: np.ndarray, pad: float = 0.06, title: str | None = None,
               axis_off: bool = False, zoom: float = 1.0) -> None:
    """Equal scale on all three axes, no tick labels. / 三軸等比例、隱藏刻度。"""
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    margin = pad * float(np.max(hi - lo))
    lo, hi = lo - margin, hi + margin
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(np.maximum(hi - lo, 1e-6), zoom=zoom)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_zticklabels([])
    if axis_off:
        ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=10)


def _dedupe_consecutive(pts: np.ndarray) -> np.ndarray:
    """Drop consecutive duplicate points (keeps np.interp well defined).
    移除連續重複點，避免弧長插值出錯。"""
    keep = np.ones(len(pts), dtype=bool)
    keep[1:] = np.linalg.norm(np.diff(pts, axis=0), axis=1) > 1e-12
    return pts[keep]


# =============================================================================
# Part A — closed 3D curve Fourier / 三維閉合曲線傅立葉
# =============================================================================

def resample_closed_polyline(vertices: np.ndarray, m: int) -> np.ndarray:
    """Uniformly resample a closed polyline by arc length (m points, no repeat).
    依弧長把閉合折線均勻重新取樣成 m 點（不重複首點）。"""
    v = np.asarray(vertices, dtype=float)
    if len(v) > 1 and np.allclose(v[0], v[-1]):
        v = v[:-1]
    pts = _dedupe_consecutive(np.vstack([v, v[:1]]))
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    targets = np.linspace(0.0, cum[-1], m, endpoint=False)
    return np.column_stack([np.interp(targets, cum, pts[:, d]) for d in range(3)])


@dataclass
class ClosedFourier3D:
    """r(t) = a0 + sum_{n=1..N} [ a_n cos(n t) + b_n sin(n t) ],  a_n, b_n in R^3.

    Term n traces an ellipse in the plane span(a_n, b_n). That ellipse can itself be split
    into two counter-rotating circles in that plane, which is the 2D picture you know.
    第 n 項在 span(a_n, b_n) 平面上畫一個橢圓；這個橢圓又可以拆成該平面上兩個反向旋轉的圓，
    也就是你熟悉的二維畫面。
    """
    a0: np.ndarray   # (3,)   centre / 中心
    a: np.ndarray    # (N, 3) cosine vectors / 餘弦向量
    b: np.ndarray    # (N, 3) sine vectors / 正弦向量

    @property
    def n_terms(self) -> int:
        return int(self.a.shape[0])

    def truncated(self, n: int) -> "ClosedFourier3D":
        return ClosedFourier3D(self.a0, self.a[:n], self.b[:n])

    def evaluate(self, t: np.ndarray) -> np.ndarray:
        t = np.atleast_1d(np.asarray(t, dtype=float))
        n = np.arange(1, self.n_terms + 1)
        phase = np.outer(t, n)                                  # (T, N)
        return self.a0 + np.cos(phase) @ self.a + np.sin(phase) @ self.b


def fit_closed_curve(points: np.ndarray, n_terms: int) -> ClosedFourier3D:
    """FFT each coordinate separately: c_n = mean_k p_k e^{-i n t_k}.
    For a real signal: a_n = 2 Re(c_n), b_n = -2 Im(c_n).
    對每個座標各做一次 FFT；實數訊號的係數換算成 a_n = 2Re(c_n)、b_n = -2Im(c_n)。"""
    m = points.shape[0]
    c = np.fft.rfft(points, axis=0) / m                         # (m//2 + 1, 3)
    n_terms = int(min(n_terms, (m - 1) // 2))                  # stay below Nyquist / 避開奈奎斯特頻率
    return ClosedFourier3D(
        a0=c[0].real.copy(),
        a=2.0 * c[1:n_terms + 1].real,
        b=-2.0 * c[1:n_terms + 1].imag,
    )


def epicycle_chain(f: ClosedFourier3D, t: float, sort_by_size: bool = True):
    """Rings (full ellipse of each term, placed at its moving centre) and arm joints at time t.
    回傳時間 t 時每一項的橢圓（放在它當下的中心）以及手臂關節點。"""
    order = np.arange(f.n_terms)
    if sort_by_size:
        size = np.sum(f.a ** 2, axis=1) + np.sum(f.b ** 2, axis=1)
        order = np.argsort(-size)
    tau = np.linspace(0.0, TAU, 72)
    centre = f.a0.copy()
    rings, joints = [], [centre.copy()]
    for k in order:
        n = k + 1
        rings.append(centre + np.outer(np.cos(tau), f.a[k]) + np.outer(np.sin(tau), f.b[k]))
        centre = centre + f.a[k] * np.cos(n * t) + f.b[k] * np.sin(n * t)
        joints.append(centre.copy())
    return rings, np.array(joints)


def demo_target_curve() -> np.ndarray:
    """A closed path through all 8 cube corners (sharp corners -> needs many terms).
    走過立方體 8 個頂點的閉合路徑（有尖角，需要很多項才能逼近）。"""
    cube = np.array([
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
        [0, 1, 1], [1, 1, 1], [1, 0, 1], [0, 0, 1],
    ], dtype=float) - 0.5
    return cube


def plot_part_a(target: np.ndarray, fit: ClosedFourier3D, out_path: Path,
                ns=(1, 2, 4, 8, 32), chain_terms: int = 8, chain_t: float = 1.9) -> None:
    t = np.linspace(0.0, TAU, 900)
    fig = plt.figure(figsize=(15, 9.5))
    fig.suptitle("Part A - a closed 3D curve as a sum of tilted ellipses (3D Fourier epicycles)",
                 fontsize=13)
    for i, n in enumerate(ns):
        ax = fig.add_subplot(2, 3, i + 1, projection="3d")
        rec = fit.truncated(n).evaluate(t)
        ax.plot(*target.T, color="0.7", lw=1.0)
        ax.plot(*rec.T, color="tab:blue", lw=2.0)
        ax.view_init(elev=24, azim=-55)
        style_axes(ax, target, title=f"N = {n} frequency term{'s' if n > 1 else ''}")

    ax = fig.add_subplot(2, 3, 6, projection="3d")
    f = fit.truncated(chain_terms)
    rings, joints = epicycle_chain(f, chain_t)
    trace = f.evaluate(np.linspace(0.0, chain_t, 400))
    ax.plot(*target.T, color="0.85", lw=1.0)
    for ring in rings:
        ax.plot(*ring.T, color="tab:orange", lw=0.8, alpha=0.75)
    ax.plot(*joints.T, color="black", lw=1.2, marker="o", ms=2)
    ax.plot(*trace.T, color="tab:blue", lw=2.0)
    ax.scatter(*joints[-1], color="red", s=25, depthshade=False)
    ax.view_init(elev=24, azim=-55)
    style_axes(ax, np.vstack([target, *rings]),
               title=f"epicycle chain: {chain_terms} tilted ellipses, t = {chain_t:.2f}")

    fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.03, wspace=0.05, hspace=0.12)
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def save_epicycle_gif(fit: ClosedFourier3D, target: np.ndarray, out_path: Path,
                      n_terms: int = 12, frames: int = 120) -> None:
    from matplotlib.animation import FuncAnimation, PillowWriter

    f = fit.truncated(n_terms)
    ts = np.linspace(0.0, TAU, frames, endpoint=False)
    bounds = np.vstack([target, *epicycle_chain(f, 0.0)[0]])
    fig = plt.figure(figsize=(5, 5))
    ax = fig.add_subplot(projection="3d")
    fig.subplots_adjust(left=0.0, right=1.0, top=0.95, bottom=0.0)

    def draw(i: int):
        ax.cla()
        t0 = ts[i]
        rings, joints = epicycle_chain(f, t0)
        ax.plot(*target.T, color="0.85", lw=1.0)
        for ring in rings:
            ax.plot(*ring.T, color="tab:orange", lw=0.7, alpha=0.6)
        ax.plot(*joints.T, color="black", lw=1.0)
        if i > 0:
            ax.plot(*f.evaluate(np.linspace(0.0, t0, 4 * i + 2)).T, color="tab:blue", lw=2.0)
        ax.scatter(*joints[-1], color="red", s=20, depthshade=False)
        ax.view_init(elev=24, azim=-60 + 1.5 * i)
        style_axes(ax, bounds, title=f"3D epicycles, N = {n_terms}")
        return []

    anim = FuncAnimation(fig, draw, frames=frames, blit=False)
    anim.save(out_path, writer=PillowWriter(fps=24), dpi=72)
    plt.close(fig)


# =============================================================================
# Part B — spine + cross-section sweep / 脊椎＋截面掃掠
# =============================================================================

def cosine_basis(s: np.ndarray, k: int) -> np.ndarray:
    """B[i, n] = cos(n pi s_i), n = 0..k-1.
    The Fourier series of an OPEN curve: mirror it to make it periodic, the sine terms vanish.
    開放曲線的傅立葉級數：把曲線鏡像延拓成週期函數，正弦項就會消失，只剩餘弦。"""
    return np.cos(np.pi * np.outer(np.atleast_1d(s), np.arange(k)))


def fit_cosine_series(s: np.ndarray, values: np.ndarray, k: int) -> np.ndarray:
    coef, *_ = np.linalg.lstsq(cosine_basis(s, k), values, rcond=None)
    return coef


def eval_cosine_series(coef: np.ndarray, s: np.ndarray) -> np.ndarray:
    return cosine_basis(s, coef.shape[0]) @ coef


def fit_open_polyline(points, k: int, m: int = 200) -> np.ndarray:
    """Hand-placed anchor points -> k cosine coefficients per axis (smooths the corners).
    手動放的錨點 -> 每個軸 k 個餘弦係數（會自動把尖角變平滑）。"""
    pts = _dedupe_consecutive(np.asarray(points, dtype=float))
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)]) / seg.sum()
    s = np.linspace(0.0, 1.0, m)
    dense = np.column_stack([np.interp(s, cum, pts[:, d]) for d in range(pts.shape[1])])
    return fit_cosine_series(s, dense, k)


def eval_section(coef: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """2D elliptic Fourier contour. coef: (H, 2, 2), coef[n-1, 0] = A_n, coef[n-1, 1] = B_n.
    c(theta) = sum_n A_n cos(n theta) + B_n sin(n theta)  ->  (len(theta), 2)
    二維橢圓傅立葉輪廓。"""
    n = np.arange(1, coef.shape[0] + 1)
    phase = np.outer(theta, n)
    return np.cos(phase) @ coef[:, 0, :] + np.sin(phase) @ coef[:, 1, :]


def rotation_minimizing_frames(points: np.ndarray, up=(0.0, 0.0, 1.0)):
    """Double-reflection RMF (Wang, Juettler, Zheng & Liu, 2008): frames that do not twist.
    雙反射法旋轉最小化標架：沿著曲線前進時截面不會亂扭。"""
    n = len(points)
    tang = np.gradient(points, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-12

    up = np.asarray(up, dtype=float)
    r0 = up - np.dot(up, tang[0]) * tang[0]
    if np.linalg.norm(r0) < 1e-6:                     # tangent parallel to up / 切線跟 up 平行
        alt = np.array([1.0, 0.0, 0.0])
        r0 = alt - np.dot(alt, tang[0]) * tang[0]
    normals = np.empty_like(points)
    normals[0] = r0 / np.linalg.norm(r0)

    for i in range(n - 1):
        v1 = points[i + 1] - points[i]
        c1 = float(v1 @ v1)
        if c1 < 1e-14:
            normals[i + 1] = normals[i]
            continue
        r_l = normals[i] - (2.0 / c1) * (v1 @ normals[i]) * v1
        t_l = tang[i] - (2.0 / c1) * (v1 @ tang[i]) * v1
        v2 = tang[i + 1] - t_l
        c2 = float(v2 @ v2)
        r_next = r_l if c2 < 1e-14 else r_l - (2.0 / c2) * (v2 @ r_l) * v2
        r_next = r_next - (r_next @ tang[i + 1]) * tang[i + 1]   # remove drift / 消除數值漂移
        normals[i + 1] = r_next / (np.linalg.norm(r_next) + 1e-12)

    binormals = np.cross(tang, normals)
    return tang, normals, binormals


@dataclass
class Mesh:
    vertices: np.ndarray   # (V, 3)
    faces: np.ndarray      # (F, 3) int, 0-based


def signed_volume(mesh: Mesh) -> float:
    v = mesh.vertices[mesh.faces]
    return float(np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2])).sum() / 6.0)


def sweep_tube(spine: np.ndarray, radii: np.ndarray, contours: np.ndarray, cap: bool = True) -> Mesh:
    """spine (S, 3), radii (S,), contours (S, T, 2) -> closed triangle mesh (outward normals).
    The section's local x follows the binormal, local y follows the normal.
    脊椎、半徑、截面 -> 封閉三角網格（法線朝外）。截面的局部 x 對應副法線，局部 y 對應法線。"""
    s_count, t_count = contours.shape[:2]
    _, nrm, binrm = rotation_minimizing_frames(spine)
    local = contours * radii[:, None, None]
    verts = (spine[:, None, :]
             + local[..., 0:1] * binrm[:, None, :]
             + local[..., 1:2] * nrm[:, None, :]).reshape(-1, 3)

    i = np.arange(s_count - 1)[:, None]
    j = np.arange(t_count)[None, :]
    a = i * t_count + j
    b = i * t_count + (j + 1) % t_count
    c = (i + 1) * t_count + (j + 1) % t_count
    d = (i + 1) * t_count + j
    faces = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3),
                            np.stack([a, c, d], -1).reshape(-1, 3)])

    if cap:
        start, end = len(verts), len(verts) + 1
        verts = np.vstack([verts, spine[0], spine[-1]])
        jj = np.arange(t_count)
        last = (s_count - 1) * t_count
        cap0 = np.stack([np.full(t_count, start), (jj + 1) % t_count, jj], -1)
        cap1 = np.stack([np.full(t_count, end), last + jj, last + (jj + 1) % t_count], -1)
        faces = np.vstack([faces, cap0, cap1])

    mesh = Mesh(verts, faces.astype(np.int64))
    if signed_volume(mesh) < 0:                       # make normals point outward / 讓法線朝外
        mesh.faces = mesh.faces[:, ::-1].copy()
    return mesh


def mirror_mesh(mesh: Mesh, plane_y: float = 0.0) -> Mesh:
    v = mesh.vertices.copy()
    v[:, 1] = 2.0 * plane_y - v[:, 1]
    return Mesh(v, mesh.faces[:, ::-1].copy())        # mirroring flips winding / 鏡像會翻轉繞序


# =============================================================================
# Part C — genome, mutation, creature / 基因組、突變、生物
# =============================================================================

GENE_FIELDS = ("spine", "radius", "sect0", "sect1", "attach")

# Absolute noise floor per gene group, so zero-valued harmonics can still mutate.
# 每組基因的絕對雜訊下限，讓原本是 0 的高階係數也能突變。
NOISE_FLOOR = {"spine": 0.06, "radius": 0.03, "section": 0.25, "attach": 0.15}


@dataclass
class TubeGene:
    name: str
    spine: np.ndarray            # (K, 3) cosine coefficients of the spine / 脊椎餘弦係數
    radius: np.ndarray           # (R,)   cosine coefficients of the radius profile / 半徑剖面餘弦係數
    sect0: np.ndarray            # (H, 2, 2) elliptic Fourier section at s = 0 / 起點截面
    sect1: np.ndarray            # (H, 2, 2) section at s = 1, lerped in between / 終點截面，中間線性插值
    parent: str | None = None    # tube this one grows from / 從哪條管長出來
    attach: float = 0.0          # position s on the parent spine / 接在父脊椎的位置 s
    mirror: bool = False         # emit a left/right mirrored pair / 是否產生左右鏡像一對
    tags: list = field(default_factory=list)   # semantic tags, as in RTIS GeneModule / 語意標籤
    is_core: bool = False        # core skeleton tube (protected in inheritance) / 核心骨架管
    meta: dict = field(default_factory=dict)   # non-genetic bookkeeping, e.g. ancestry / 非遺傳的紀錄


def symmetric_section_mask(h: int) -> np.ndarray:
    """Which elliptic-Fourier entries keep a section left/right symmetric (local x -> -x).
    Per harmonic the entries are [A_x, A_y, B_x, B_y]:
      odd n  -> only A_x, B_y may be non-zero;  even n -> only A_y, B_x.
    哪些截面係數能保持左右對稱：奇數階只能有 A_x、B_y；偶數階只能有 A_y、B_x。"""
    mask = np.zeros((h, 4))
    for n in range(1, h + 1):
        mask[n - 1] = (1, 0, 0, 1) if n % 2 == 1 else (0, 1, 1, 0)
    return mask.ravel()


@dataclass
class Genome:
    tubes: list[TubeGene]

    # ---- flatten / 攤平 --------------------------------------------------------
    def to_vector(self) -> np.ndarray:
        return np.concatenate([np.ravel(np.asarray(getattr(t, f), dtype=float))
                               for t in self.tubes for f in GENE_FIELDS])

    def with_vector(self, vec: np.ndarray) -> "Genome":
        vec = np.asarray(vec, dtype=float)
        new_tubes, k = [], 0
        for t in self.tubes:
            updates = {}
            for f in GENE_FIELDS:
                cur = np.asarray(getattr(t, f), dtype=float)
                updates[f] = vec[k:k + cur.size].reshape(cur.shape).copy()
                k += cur.size
            updates["attach"] = float(np.clip(updates["attach"], 0.0, 1.0))
            new_tubes.append(dataclasses.replace(t, **updates))
        if k != vec.size:
            raise ValueError(f"genome vector length {vec.size} != expected {k}")
        return Genome(new_tubes)

    def entry_meta(self):
        """Per-entry (relative scale, noise floor, harmonic order, mutable mask), same order as to_vector().
        每個基因值的（相對尺度、雜訊下限、諧波階數、可否突變），順序跟 to_vector() 一致。"""
        rel, floor, harm, mask = [], [], [], []

        def add(r, fl, h, m):
            rel.append(np.ravel(r))
            floor.append(np.ravel(fl))
            harm.append(np.ravel(h))
            mask.append(np.ravel(m))

        for t in self.tubes:
            k = t.spine.shape[0]
            m = np.ones((k, 3))
            if t.parent is None:
                m[0, :] = 0.0             # root stays centred / 根節點位置固定
            if not t.mirror:
                m[:, 1] = 0.0             # midline tubes stay on the y = 0 plane / 中軸管留在 y = 0 平面
            add(np.ones(k * 3), np.full(k * 3, NOISE_FLOOR["spine"]),
                np.repeat(np.arange(k), 3), m)

            r = t.radius.shape[0]
            add(np.ones(r), np.full(r, NOISE_FLOOR["radius"]), np.arange(r), np.ones(r))

            for sect in (t.sect0, t.sect1):
                h = sect.shape[0]
                sm = np.ones(h * 4) if t.mirror else symmetric_section_mask(h)
                add(np.ones(h * 4), np.full(h * 4, NOISE_FLOOR["section"]),
                    np.repeat(np.arange(1, h + 1), 4), sm)

            # attach: absolute noise only (rel = 0) / 接點只用絕對雜訊
            add([0.0], [NOISE_FLOOR["attach"]], [0], [0.0 if t.parent is None else 1.0])

        return tuple(np.concatenate(x).astype(float) for x in (rel, floor, harm, mask))

    # ---- JSON ----------------------------------------------------------------
    def to_json(self) -> dict:
        return {
            "genome_length": int(self.to_vector().size),
            "tubes": [{
                "name": t.name, "parent": t.parent, "attach": float(t.attach), "mirror": bool(t.mirror),
                "tags": list(t.tags), "is_core": bool(t.is_core),
                "meta": {k: (float(v) if isinstance(v, (float, np.floating)) else v)
                         for k, v in t.meta.items()},
                "spine": t.spine.tolist(), "radius": t.radius.tolist(),
                "sect0": t.sect0.tolist(), "sect1": t.sect1.tolist(),
            } for t in self.tubes],
        }

    @classmethod
    def from_json(cls, data: dict) -> "Genome":
        return cls([TubeGene(
            name=d["name"], parent=d["parent"], attach=float(d["attach"]), mirror=bool(d["mirror"]),
            tags=list(d.get("tags", [])), is_core=bool(d.get("is_core", False)),
            meta=dict(d.get("meta", {})),
            spine=np.array(d["spine"], dtype=float), radius=np.array(d["radius"], dtype=float),
            sect0=np.array(d["sect0"], dtype=float), sect1=np.array(d["sect1"], dtype=float),
        ) for d in data["tubes"]])


def mutate(genome: Genome, sigma: float, rng: np.random.Generator,
           band: str = "all", cutoff: int = 2) -> Genome:
    """Gaussian mutation, std = sigma * (|gene| + floor), restricted to a frequency band.
      band = "low"  -> harmonics <= cutoff (body plan / 身體藍圖)
      band = "high" -> harmonics >  cutoff (detail / 細節)
      band = "all"  -> everything / 全部"""
    g = genome.to_vector()
    rel, floor, harm, mask = genome.entry_meta()
    if band == "low":
        mask = mask * (harm <= cutoff)
    elif band == "high":
        mask = mask * (harm > cutoff)
    elif band != "all":
        raise ValueError(f"unknown band: {band}")
    std = sigma * (rel * np.abs(g) + floor) * mask
    return genome.with_vector(g + rng.standard_normal(g.size) * std)


def ellipse_section(h: int, sx: float = 1.0, sy: float = 1.0) -> np.ndarray:
    """Axis-aligned ellipse as H-harmonic elliptic Fourier coefficients.
    用 H 階橢圓傅立葉係數表示的軸對齊橢圓。"""
    c = np.zeros((h, 2, 2))
    c[0, 0] = (sx, 0.0)   # A_1 -> cos(theta)
    c[0, 1] = (0.0, sy)   # B_1 -> sin(theta)
    return c


def radius_profile(s_ctrl, r_ctrl, k: int) -> np.ndarray:
    """Piecewise-linear radius control points -> k cosine coefficients.
    半徑控制點（折線）-> k 個餘弦係數。"""
    s = np.linspace(0.0, 1.0, 200)
    return fit_cosine_series(s, np.interp(s, s_ctrl, r_ctrl), k)


def default_genome(k_spine: int = 5, k_radius: int = 8, h_section: int = 4) -> Genome:
    """A toy quadruped: body, neck+head, tail, front and rear leg pairs. x = forward, z = up.
    Tags follow RTIS semantic tags so PCE can match tubes across species.
    一隻玩具四足動物：身體、脖子+頭、尾巴、前後腿各一對。x 朝前、z 朝上。
    標籤沿用 RTIS 的語意標籤，讓 PCE 可以跨物種配對。"""
    sec = ellipse_section
    body = TubeGene(
        "body",
        spine=fit_open_polyline([(-1.0, 0, 0.0), (-0.5, 0, 0.06), (0.0, 0, 0.10),
                                 (0.5, 0, 0.08), (1.0, 0, 0.04)], k_spine),
        radius=radius_profile([0, 0.15, 0.5, 0.85, 1], [0.12, 0.24, 0.27, 0.24, 0.14], k_radius),
        sect0=sec(h_section, 1.0, 0.85), sect1=sec(h_section, 0.9, 1.0),
        tags=["structural", "central"], is_core=True,
    )
    neck = TubeGene(
        "neck_head",
        spine=fit_open_polyline([(0, 0, 0), (0.2, 0, 0.2), (0.38, 0, 0.38),
                                 (0.6, 0, 0.42), (0.82, 0, 0.36)], k_spine),
        radius=radius_profile([0, 0.3, 0.55, 0.75, 0.9, 1],
                              [0.13, 0.09, 0.10, 0.16, 0.14, 0.04], k_radius),
        sect0=sec(h_section), sect1=sec(h_section, 0.85, 1.0),
        parent="body", attach=0.96, tags=["sensory", "neural"], is_core=True,
    )
    tail = TubeGene(
        "tail",
        spine=fit_open_polyline([(0, 0, 0), (-0.35, 0, 0.02), (-0.7, 0, 0.12),
                                 (-1.0, 0, 0.3), (-1.2, 0, 0.5)], k_spine),
        radius=radius_profile([0, 0.5, 1], [0.12, 0.06, 0.015], k_radius),
        sect0=sec(h_section), sect1=sec(h_section),
        parent="body", attach=0.04, tags=["structural", "balance"], is_core=False,
    )
    leg_front = TubeGene(
        "leg_front",
        spine=fit_open_polyline([(0, 0, 0), (0.02, 0.2, -0.1), (0.05, 0.26, -0.45),
                                 (0.0, 0.27, -0.75), (0.1, 0.27, -0.9)], k_spine),
        radius=radius_profile([0, 0.15, 0.5, 0.85, 1], [0.10, 0.09, 0.06, 0.05, 0.07], k_radius),
        sect0=sec(h_section), sect1=sec(h_section),
        parent="body", attach=0.82, mirror=True,
        tags=["motor", "locomotion", "front"], is_core=True,
    )
    leg_rear = TubeGene(
        "leg_rear",
        spine=fit_open_polyline([(0, 0, 0), (-0.02, 0.2, -0.08), (0.08, 0.27, -0.4),
                                 (-0.05, 0.27, -0.7), (0.05, 0.27, -0.87)], k_spine),
        radius=radius_profile([0, 0.15, 0.5, 0.85, 1], [0.12, 0.11, 0.07, 0.05, 0.07], k_radius),
        sect0=sec(h_section), sect1=sec(h_section),
        parent="body", attach=0.18, mirror=True,
        tags=["motor", "locomotion", "rear"], is_core=True,
    )
    return Genome([body, neck, tail, leg_front, leg_rear])


def tube_mesh(gene: TubeGene, offset: np.ndarray, n_s: int, n_theta: int) -> Mesh:
    s = np.linspace(0.0, 1.0, n_s)
    theta = np.linspace(0.0, TAU, n_theta, endpoint=False)
    spine = eval_cosine_series(gene.spine, s) + offset
    radii = np.clip(eval_cosine_series(gene.radius, s), 0.008, None)
    c0 = eval_section(gene.sect0, theta)
    c1 = eval_section(gene.sect1, theta)
    contours = (1.0 - s)[:, None, None] * c0 + s[:, None, None] * c1
    return sweep_tube(spine, radii, contours)


def build_creature(genome: Genome, n_s: int = 64, n_theta: int = 32) -> list[tuple[str, Mesh]]:
    """Parents must come before children in genome.tubes. Positive local y = the creature's left.
    genome.tubes 裡父管要排在子管前面。局部 y 為正 = 生物的左側。"""
    genes = {t.name: t for t in genome.tubes}
    offsets: dict[str, np.ndarray] = {}
    parts: list[tuple[str, Mesh]] = []
    for t in genome.tubes:
        if t.parent is None:
            offset = np.zeros(3)
            anchor = eval_cosine_series(t.spine, np.array([0.0]))[0]
        else:
            p = genes[t.parent]
            anchor = eval_cosine_series(p.spine, np.array([t.attach]))[0] + offsets[t.parent]
            offset = anchor - eval_cosine_series(t.spine, np.array([0.0]))[0]   # child starts at anchor
        offsets[t.name] = offset
        mesh = tube_mesh(t, offset, n_s, n_theta)
        if t.mirror:
            parts.append((f"{t.name}_L", mesh))
            parts.append((f"{t.name}_R", mirror_mesh(mesh, plane_y=float(anchor[1]))))
        else:
            parts.append((t.name, mesh))
    return parts


def write_obj(path: Path, parts: list[tuple[str, Mesh]]) -> None:
    """OBJ, converted from Z-up to the usual Y-up: (x, y, z) -> (x, z, -y) (a pure rotation).
    匯出 OBJ，從 Z 朝上轉成一般的 Y 朝上（純旋轉，不影響法線方向）。"""
    lines = ["# fourier3d_demo.py — Y-up OBJ"]
    offset = 1
    for name, m in parts:
        v = m.vertices
        lines.append(f"o {name}")
        lines.extend(f"v {x:.5f} {z:.5f} {-y:.5f}" for x, y, z in v)
        lines.extend(f"f {a} {b} {c}" for a, b, c in (m.faces + offset))
        offset += len(v)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


BAND_COLOURS = {"original": "#7f93ad", "low": "#d98c4a", "high": "#5aa36a", "all": "#9b72c4"}
BAND_LABELS = {"original": "original", "low": "low-freq mutation (body plan)",
               "high": "high-freq mutation (detail)", "all": "all-band mutation"}


def plot_creatures(previews, bands, out_path: Path, light=(0.4, -0.7, 0.8)) -> None:
    n = len(previews)
    ncols = min(4, n)
    nrows = math.ceil(n / ncols)
    fig = plt.figure(figsize=(4.3 * ncols, 3.3 * nrows))
    fig.suptitle("Part B/C - spine + cross-section sweep, genome mutation by frequency band",
                 fontsize=13)
    light = np.asarray(light, dtype=float)
    light /= np.linalg.norm(light)
    counts: dict[str, int] = {}
    for i, (parts, band) in enumerate(zip(previews, bands)):
        counts[band] = counts.get(band, 0) + 1
        ax = fig.add_subplot(nrows, ncols, i + 1, projection="3d")
        tris = np.concatenate([m.vertices[m.faces] for _, m in parts])
        normal = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        normal /= np.linalg.norm(normal, axis=1, keepdims=True) + 1e-12
        shade = 0.3 + 0.7 * np.clip(normal @ light, 0.0, 1.0)
        base = np.array(mcolors.to_rgb(BAND_COLOURS[band]))
        ax.add_collection3d(Poly3DCollection(tris, facecolors=np.clip(shade[:, None] * base, 0, 1),
                                             edgecolors="none", linewidths=0))
        ax.view_init(elev=16, azim=-60)
        label = BAND_LABELS[band] + ("" if band == "original" else f" #{counts[band]}")
        style_axes(ax, tris.reshape(-1, 3), pad=0.02, title=label, axis_off=True, zoom=1.1)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.9, bottom=0.0, wspace=0.0, hspace=0.08)
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


# =============================================================================
# Main / 主程式
# =============================================================================

def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="3D Fourier epicycles + Fourier tube sweep model generator")
    ap.add_argument("--out", default="out", help="output folder / 輸出資料夾")
    ap.add_argument("--curve", help="CSV of a closed 3D polyline, one x,y,z per row / 自訂閉合曲線")
    ap.add_argument("--terms", type=int, default=64, help="Fourier terms to fit in Part A / 擬合項數")
    ap.add_argument("--gif", action="store_true", help="also save epicycle animation / 輸出本輪動畫")
    ap.add_argument("--genome", help="start from a saved genome JSON / 從存好的基因組開始")
    ap.add_argument("--sigma", type=float, default=0.25, help="mutation strength / 突變強度")
    ap.add_argument("--per-band", type=int, default=2, help="variants per band / 每個頻帶的變體數")
    ap.add_argument("--cutoff", type=int, default=2, help="low/high harmonic split / 高低頻分界")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # ---- Part A ----------------------------------------------------------------
    verts = np.loadtxt(args.curve, delimiter=",", ndmin=2) if args.curve else demo_target_curve()
    target = resample_closed_polyline(verts, 1024)
    fit = fit_closed_curve(target, args.terms)
    t_samples = TAU * np.arange(len(target)) / len(target)
    print("Part A: RMS error vs number of terms / 誤差 vs 項數")
    for n in (1, 2, 4, 8, 16, 32, 64):
        if n > fit.n_terms:
            break
        err = np.sqrt(np.mean(np.sum((fit.truncated(n).evaluate(t_samples) - target) ** 2, axis=1)))
        print(f"  N = {n:3d}   RMS = {err:.4f}")
    plot_part_a(target, fit, out / "partA_curve_fourier.png")
    if args.gif:
        print("  rendering GIF ... / 產生動畫中 ...")
        save_epicycle_gif(fit, target, out / "partA_epicycles.gif")

    # ---- Part B / C ------------------------------------------------------------
    base = (Genome.from_json(json.loads(Path(args.genome).read_text(encoding="utf-8")))
            if args.genome else default_genome())
    print(f"Part B/C: genome length = {base.to_vector().size} floats / 基因組長度")
    rng = np.random.default_rng(args.seed)
    creatures = [("original", base)]
    for band in ("low", "high", "all"):
        for _ in range(args.per_band):
            creatures.append((band, mutate(base, args.sigma, rng, band, args.cutoff)))

    previews = []
    for idx, (band, g) in enumerate(creatures):
        stem = f"creature_{idx:02d}_{band}"
        parts = build_creature(g)
        write_obj(out / f"{stem}.obj", parts)
        (out / f"{stem}.json").write_text(json.dumps(g.to_json(), indent=1), encoding="utf-8")
        n_tri = sum(len(m.faces) for _, m in parts)
        print(f"  {stem}.obj   {len(parts)} parts, {n_tri} triangles")
        previews.append(build_creature(g, n_s=40, n_theta=20))
    plot_creatures(previews, [b for b, _ in creatures], out / "partB_creatures.png")
    print(f"Done -> {out.resolve()}")


if __name__ == "__main__":
    main()
