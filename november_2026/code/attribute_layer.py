#!/usr/bin/env python3
"""
attribute_layer.py
==================
The part-attribute layer (plan section 13, proposed by the user on 2026-11-15), added on top of the
existing inheritance rules. Off unless form_fusion_lab.fuse() is given an AttributeLayer.
部位屬性層（企劃第十三節，使用者 11-15 提出），加在現有遺傳規則之上。只有把 AttributeLayer 交給
form_fusion_lab.fuse() 時才會作用。

What it does / 做什麼:
1. Measures each part as a few whole-part attributes, from the genes that already exist:
   length (how far the part reaches beyond the surface of the part it grows from, measured along
   the part's own direction on the real surface), thickness (mean
   radius), taper (tip radius / base radius) and bend (total turning). All in units of body size.
   用現有的基因量出每個部位的屬性：長度（伸出父部位表面多遠）、粗細（平均半徑）、
   漸細（末端半徑 ÷ 根部半徑）、彎曲（總轉角），單位都是體型。
2. Inherits attribute by attribute: each one whole from parent A or B. The bone-by-bone genes still
   cross as before and now only give the part its pattern; the part is then rescaled to the
   inherited attributes. No existing gene is rewritten.
   逐項遺傳屬性：每項整個來自 A 或 B。逐根骨頭的基因照舊交配，現在只負責「樣式」；部位再縮放到遺傳到的屬性。
3. Limb sets: repeated parts (same parent, same arrangement, same tags; e.g. the spider's four leg
   pairs) form one set. Count and placement come from one parent's set; attributes come from either.
   肢體組：重複的部位（同父部位、同排列、同標籤，例如蜘蛛的四對腳）算一組。數量與位置來自一方，屬性逐項來自任一方。

The four assumptions the user approved on 2026-11-15 / 使用者 11-15 同意的四個假設:
  1. the count is one parent's count, never in between / 數量一定是其中一方的數量
  2. count and placement travel together / 數量與位置一起遺傳
  3. with fewer limbs than the attribute parent has, each takes the attributes of the attribute
     parent's limb nearest to its position / 數量較少時，用位置最接近的那一條的屬性
  4. front-to-back differences come with the attributes (8 legs from a parent with one leg pair are
     all alike) / 前後差異跟著屬性走

Not done (on the to-do list) / 還沒做（已列入待辦）:
  - crossing a long part with a round part: such pairs keep the existing rules
    長條 × 胖圓的部位交配：這種組合照舊用現有規則
  - attributes of round parts (bell, abdomen) and of the root part: left as they are
    胖圓部位與根部位的屬性：維持原樣

Target: Python 3.10.12 · numpy. Imports form_fusion_lab only through the objects fuse() passes in.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import skeleton_sdf_demo as sk

ATTRIBUTES = ("length", "thickness", "taper", "bend")
LONG_RATIO = 2.0          # length / mean diameter at or above this = a long part / 以上算長條部位
MIN_REACH = 0.2           # a part keeps at least this share of its own reach / 至少保留這個比例的伸出長度


# =============================================================================
# Measuring / 量測
# =============================================================================

def exit_distance(parts, parent_name: str, start: np.ndarray, heading: np.ndarray, steps: int = 240) -> float:
    """How far a limb travels from its attach point, along its own first bone, before it leaves the
    surface of the part it grows from. Uses the real surface (round cones plus the cross-section
    outline), so a flat crab shell is thin upward and wide sideways.
    肢體從接點沿著自己第一根骨頭的方向，走多遠才離開父部位的表面。用真正的表面（圓錐加上截面輪廓），
    所以扁平的蟹殼往上薄、往側邊寬。
    (First version, discarded: the parent's radius times its widest outline direction. It made the
    crab's upward eye stalks look buried in their own shell, so they were shortened to nothing.)
    （第一版已放棄：父部位半徑乘上輪廓最寬方向的倍率。這讓朝上的蟹眼柄看起來埋在自己的殼裡，結果被縮到看不見。）"""
    pieces = sk.develop_segments(sk.SkeletonGenome(list(parts)), use_detail=True)
    pc = next(pc for pc in pieces if pc["gene"] == parent_name)
    segs, detail = pc["segments"], pc.get("detail")
    reach = 2.2 * max(max(sg.ra, sg.rb) for sg in segs)
    t = np.linspace(0.0, reach, steps)
    pts = np.asarray(start, float)[None, :] + t[:, None] * (heading / (np.linalg.norm(heading) + 1e-12))
    d = np.full(steps, np.inf)
    for sg in segs:
        dd = sk.sd_round_cone(pts, sg.a, sg.b, sg.ra, sg.rb)
        if detail is not None:
            dd = dd - sk.detail_offset(pts, sg, sg.ra, sg.rb, detail)
        d = np.minimum(d, dd)
    outside = np.flatnonzero(d > 0.0)
    return float(t[outside[0]]) if len(outside) else float(reach)


def bend_angles(bends: np.ndarray) -> np.ndarray:
    if len(bends) == 0:
        return np.zeros(0)
    b = np.asarray(bends, float)
    return np.arccos(np.clip(b[:, 0] / (np.linalg.norm(b, axis=1) + 1e-12), -1.0, 1.0))


def measure(rel: dict, parent_r: float | None) -> dict:
    """Attributes of one part from its relative genes (lengths and radii already in body-size units).
    parent_r = surface radius of the parent at the attach point, in body-size units (None for the root).
    從相對基因量出一個部位的屬性。"""
    lengths, radii = np.asarray(rel["lengths"]), np.asarray(rel["radii"])
    total, thick = float(lengths.sum()), float(radii.mean())
    return {"class": "long" if total / (2.0 * thick + 1e-12) >= LONG_RATIO else "round",
            "length": None if parent_r is None else total - parent_r, "total": total,
            "thickness": thick, "taper": float(radii[-1] / (radii[0] + 1e-12)),
            "bend": float(bend_angles(rel["bends"]).sum())}


def reshape(rel: dict, target: dict, parent_r: float, source_total: float) -> dict:
    """Rescale crossed relative genes so the part has the target attributes. The bone-by-bone pattern
    is kept: lengths scale together, radii keep their profile, bends keep their directions.
    把交配後的相對基因縮放到目標屬性；逐根骨頭的樣式保留。"""
    rel = dict(rel)
    lengths, radii = np.asarray(rel["lengths"], float), np.asarray(rel["radii"], float)
    n = len(radii) - 1
    t0 = radii[-1] / (radii[0] + 1e-12)
    if t0 > 1e-6 and target["taper"] > 1e-6:                     # taper first, base unchanged / 先調漸細
        radii = radii * (target["taper"] / t0) ** (np.arange(n + 1) / max(n, 1))
    radii = radii * target["thickness"] / (radii.mean() + 1e-12)   # then thickness / 再調粗細
    reach = max(target["length"], MIN_REACH * source_total)          # length beyond the parent's surface
    lengths = lengths * (parent_r + reach) / (lengths.sum() + 1e-12)
    bends = np.asarray(rel["bends"], float)
    cur = bend_angles(bends).sum()
    if len(bends) and cur > 1e-3:
        k = target["bend"] / cur
        out = []
        for loc in bends:
            ang = np.arccos(np.clip(loc[0] / (np.linalg.norm(loc) + 1e-12), -1.0, 1.0))
            side = loc[1:] / (np.linalg.norm(loc[1:]) + 1e-12)
            a = float(np.clip(ang * k, 0.0, np.pi * 0.95))
            out.append([np.cos(a), *(np.sin(a) * side)])
        bends = np.array(out)
    rel.update(lengths=lengths, radii=radii, bends=bends)
    return rel


# =============================================================================
# Limb sets / 肢體組
# =============================================================================

def limb_sets(g) -> dict[str, tuple]:
    """part name -> set key. Same parent, same arrangement and the same tags = one set.
    部位名稱 -> 組的鍵。同父部位、同排列、同標籤＝同一組。"""
    return {p.name: (p.parent, sk.arrangement(p), frozenset(p.tags)) for p in g.parts if p.parent is not None}


@dataclass
class AttributeLayer:
    exit_distance = staticmethod(exit_distance)
    """Passed to form_fusion_lab.fuse(attr=...). Uses its own random generator, so turning it on does
    not change which genes the rest of the inheritance step picks.
    交給 fuse(attr=...)。用自己的亂數產生器，所以開啟它不會改變遺傳步驟其他基因的選擇。"""
    rng: np.random.Generator
    alpha: float = 0.5
    log: dict = field(default_factory=lambda: {"sets": [], "parts": {}, "skipped": []})
    _set_sources: dict = field(default_factory=dict)

    # ---- matching stage: limb sets / 配對階段：肢體組 ----------------------------------------------------
    def plan(self, ga, gb, pairs: list[dict]) -> tuple[list[dict], set[str]]:
        """Rewrites the matching for limb sets. Returns (pairs, excluded) where excluded lists parent
        parts ("A.name") left out because the other parent supplied the count.
        依肢體組改寫配對。回傳（配對、排除）；排除是因為數量來自另一方而不用的部位。"""
        sa, sb = limb_sets(ga), limb_sets(gb)
        members_a, members_b = {}, {}
        for n, k in sa.items():
            members_a.setdefault(k, []).append(n)
        for n, k in sb.items():
            members_b.setdefault(k, []).append(n)
        attach_a = {p.name: p.attach for p in ga.parts}
        attach_b = {p.name: p.attach for p in gb.parts}
        links: dict[tuple, float] = {}
        for pr in pairs:
            if pr["a"] in sa and pr["b"] in sb:
                key = (sa[pr["a"]], sb[pr["b"]])
                links[key] = max(links.get(key, 0.0), pr["score"])
        chosen, used_a, used_b = [], set(), set()
        for (ka, kb), s in sorted(links.items(), key=lambda kv: -kv[1]):
            if ka not in used_a and kb not in used_b:
                chosen.append((ka, kb, s))
                used_a.add(ka)
                used_b.add(kb)
        grouped = [(ka, kb, s) for ka, kb, s in chosen if len(members_a[ka]) > 1 or len(members_b[kb]) > 1]
        touched_a = {n for ka, _, _ in grouped for n in members_a[ka]}
        touched_b = {n for _, kb, _ in grouped for n in members_b[kb]}
        # a pair that links a set to anything other than its chosen partner set is dissolved
        # 把組跟「選定的對象組以外」連在一起的配對拆掉
        out = [pr for pr in pairs if pr["a"] not in touched_a and pr["b"] not in touched_b]
        excluded: set[str] = set()
        for ka, kb, s in grouped:
            count_src = "A" if self.rng.random() < self.alpha else "B"
            attrs = {k: ("A" if self.rng.random() < self.alpha else "B") for k in ATTRIBUTES}
            ma, mb = members_a[ka], members_b[kb]
            if count_src == "A":
                links_ = [(a, min(mb, key=lambda b: abs(attach_b[b] - attach_a[a]))) for a in ma]
                excluded |= {f"B.{b}" for b in mb if b not in {x for _, x in links_}}
            else:
                links_ = [(min(ma, key=lambda a: abs(attach_a[a] - attach_b[b])), b) for b in mb]
                excluded |= {f"A.{a}" for a in ma if a not in {x for x, _ in links_}}
            set_id = len(self.log["sets"])
            for a, b in links_:
                out.append({"a": a, "b": b, "score": s, "how": "set", "set": set_id,
                            "template": count_src, "placement": count_src})
            self._set_sources[set_id] = attrs
            self.log["sets"].append({"a": ma, "b": mb, "count_from": count_src, "attributes_from": attrs,
                                     "limbs": [list(x) for x in links_],
                                     "count": len(ma) if count_src == "A" else len(mb)})
        # parts of a dissolved pair that are not in any chosen set become unmatched, as they would be
        # 被拆掉的配對裡、不屬於任何選定組的部位，變成沒配對的部位
        return out, excluded

    # ---- inheritance stage: attributes / 遺傳階段：屬性 -------------------------------------------------
    def adjust_pair(self, name, rel, ea, eb, ra_par, rb_par, child_exit, pr) -> dict:
        """ea / eb: relative genes of the A and B part; ra_par / rb_par: how far each travels inside its
        parent before reaching the surface (body-size units; None for the root); child_exit(rel): the
        same distance in the child for genes rel (None for the root).
        A 與 B 部位的相對基因；它們在父部位裡走多遠才到表面；child_exit(rel)：子代裡的同一個距離。"""
        if ra_par is None or rb_par is None:
            return rel
        ma, mb = measure(ea, ra_par), measure(eb, rb_par)
        if ma["class"] != mb["class"] or ma["class"] != "long":
            self.log["skipped"].append({"part": name, "why": f"{ma['class']} x {mb['class']}"})
            return rel
        src = (self._set_sources[pr["set"]] if "set" in pr
               else {k: ("A" if self.rng.random() < self.alpha else "B") for k in ATTRIBUTES})
        target = {k: (ma if src[k] == "A" else mb)[k] for k in ATTRIBUTES}
        r_child = child_exit(rel)
        out = reshape(rel, target, r_child, (ma if src["length"] == "A" else mb)["total"])
        self.log["parts"][name] = {"from": src, "target": target, "set": pr.get("set"),
                                   "result": measure(out, child_exit(out))}
        return out

    def adjust_single(self, name, rel, own_par_r, child_exit) -> dict:
        """An unmatched part keeps its own attributes; only its reach beyond the surface is re-applied
        on the child's parent, so it cannot disappear inside a fatter body.
        沒配對的部位保留自己的屬性；只把「伸出表面的長度」套到子代的父部位上，讓它不會消失在更胖的身體裡。"""
        if own_par_r is None:
            return rel
        m = measure(rel, own_par_r)
        if m["class"] != "long":
            return rel
        r_child = child_exit(rel)
        out = reshape(rel, {k: m[k] for k in ATTRIBUTES}, r_child, m["total"])
        self.log["parts"][name] = {"from": "own", "target": {k: m[k] for k in ATTRIBUTES},
                                   "result": measure(out, child_exit(out))}
        return out
