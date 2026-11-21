/* RTIS breeding bench core: a JavaScript port of skeleton_sdf_demo.py.
   Pure functions, no DOM. Runs in the browser and in node (for tests).
   Genome: { parts: [ {name, parent, attach, mirror, tags, isCore, blend, origin[3],
                       offsets[[3]], radii[], detail0[[2]]|null, detail1[[2]]|null, anc} ] }
   Coordinates: x forward, y left, z up. */
const Core = (() => {
  "use strict";
  const TAU = Math.PI * 2;
  const DETAIL_MIN = 0.4, DETAIL_MAX = 1.8;
  const CFG = {
    inheritanceFactor: 0.7, coreLock: 0.9, alpha: 0.5, dominanceA: 0.5, matchThreshold: 0.25,
    microBudget: 4, microRate: 0.5, microSigma: 0.15, detailSigma: 0.05,
  };

  // ---- random -------------------------------------------------------------------------------
  function makeRng(seed) {
    let a = seed >>> 0;
    const rng = () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    rng.normal = () => {
      const u = Math.max(rng(), 1e-12), v = rng();
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(TAU * v);
    };
    rng.int = (n) => Math.min(n - 1, Math.floor(rng() * n));
    return rng;
  }

  // ---- genome helpers -----------------------------------------------------------------------
  function fromJson(data, anc) {
    return { parts: data.parts.map((p) => ({
      name: p.name, parent: p.parent, attach: p.attach, mirror: p.mirror, tags: p.tags.slice(),
      isCore: p.is_core, blend: p.blend, origin: p.origin.slice(),
      offsets: p.offsets.map((o) => o.slice()), radii: p.radii.slice(),
      detail0: p.detail0 ? p.detail0.map((r) => r.slice()) : null,
      detail1: p.detail1 ? p.detail1.map((r) => r.slice()) : null,
      anc,
    })) };
  }
  function toJson(g) {
    return { gene_count: geneCount(g), parts: g.parts.map((p) => ({
      name: p.name, parent: p.parent, attach: p.attach, mirror: p.mirror, tags: p.tags,
      is_core: p.isCore, blend: p.blend, origin: p.origin, offsets: p.offsets, radii: p.radii,
      detail0: p.detail0, detail1: p.detail1, meta: { ancestry_a: p.anc },
    })) };
  }
  function clonePart(p) {
    return { ...p, tags: p.tags.slice(), origin: p.origin.slice(), offsets: p.offsets.map((o) => o.slice()),
      radii: p.radii.slice(), detail0: p.detail0 ? p.detail0.map((r) => r.slice()) : null,
      detail1: p.detail1 ? p.detail1.map((r) => r.slice()) : null };
  }
  function partGeneCount(p) {
    const n = p.offsets.length;
    return n + (n + 1) + 1 + (p.parent === null ? 0 : 1) + (p.detail0 ? 1 : 0);
  }
  function geneCount(g) { return g.parts.reduce((s, p) => s + partGeneCount(p), 0); }

  function chainJoints(p, start) {
    const out = [start.slice()];
    let c = start.slice();
    for (const o of p.offsets) { c = [c[0] + o[0], c[1] + o[1], c[2] + o[2]]; out.push(c); }
    return out;
  }
  function pointOnChain(joints, t) {
    const u = Math.min(1, Math.max(0, t)) * (joints.length - 1);
    const i = Math.min(Math.floor(u), joints.length - 2), f = u - i;
    return [0, 1, 2].map((d) => joints[i][d] + f * (joints[i + 1][d] - joints[i][d]));
  }
  function interp1(xs, ys, x) {
    if (x <= xs[0]) return ys[0];
    for (let i = 1; i < xs.length; i++) {
      if (x <= xs[i]) return ys[i - 1] + ((x - xs[i - 1]) / (xs[i] - xs[i - 1])) * (ys[i] - ys[i - 1]);
    }
    return ys[ys.length - 1];
  }
  /** Re-express a chain with n bones (same shape), so parents with different bone counts can cross. */
  function resamplePart(p, n) {
    const m = p.offsets.length;
    if (m === n) return p;
    const joints = chainJoints(p, [0, 0, 0]);
    const tOld = joints.map((_, i) => i / m), newJ = [], newR = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      newJ.push([0, 1, 2].map((d) => interp1(tOld, joints.map((j) => j[d]), t)));
      newR.push(interp1(tOld, p.radii, t));
    }
    const offsets = [];
    for (let i = 0; i < n; i++) offsets.push([0, 1, 2].map((d) => newJ[i + 1][d] - newJ[i][d]));
    return { ...p, offsets, radii: newR };
  }

  // ---- 1. correspondence --------------------------------------------------------------------
  function tagSimilarity(a, b) {
    const sa = new Set(a), sb = new Set(b);
    let inter = 0;
    for (const t of sa) if (sb.has(t)) inter++;
    const union = sa.size + sb.size - inter;
    return union ? inter / union : 0;
  }
  /** Greedy one-to-one matching by tags (+ attach position). Returns Map nameA -> {b, score}. */
  function matchParts(ga, gb, cfg = CFG) {
    const rootA = ga.parts.find((p) => p.parent === null), rootB = gb.parts.find((p) => p.parent === null);
    const pairs = new Map([[rootA.name, { b: rootB.name, score: 1 }]]);
    const usedB = new Set([rootB.name]), cand = [];
    for (const pa of ga.parts) {
      if (pa.parent === null) continue;
      for (const pb of gb.parts) {
        if (pb.parent === null || pa.mirror !== pb.mirror) continue;
        const s = tagSimilarity(pa.tags, pb.tags);
        if (s < cfg.matchThreshold) continue;
        cand.push([s + 0.25 * (1 - Math.abs(pa.attach - pb.attach)), pa.name, pb.name]);
      }
    }
    cand.sort((x, y) => y[0] - x[0]);
    for (const [s, na, nb] of cand) {
      if (!pairs.has(na) && !usedB.has(nb)) { pairs.set(na, { b: nb, score: s }); usedB.add(nb); }
    }
    return pairs;
  }

  // ---- 2 + 3. crossover as an editable plan ---------------------------------------------------
  /** One row per part of the child-to-be. Every boolean gene flag: true = from parent A. */
  function planCross(ga, gb, rng, cfg = CFG) {
    const pairs = matchParts(ga, gb, cfg), partsB = new Map(gb.parts.map((p) => [p.name, p]));
    const matchedB = new Set([...pairs.values()].map((v) => v.b));
    const pPeriph = Math.min(1, cfg.inheritanceFactor * 0.5 * 2);
    const pick = () => rng() < cfg.alpha;
    const rows = [];
    for (const pa of ga.parts) {
      if (pairs.has(pa.name)) {
        const { b, score } = pairs.get(pa.name), pb = partsB.get(b);
        const n = Math.max(pa.offsets.length, pb.offsets.length);
        const core = pa.parent === null || pa.isCore || pb.isCore;
        const inherit = core ? true : rng() < 1 - (1 - pPeriph) ** 2;
        const bones = Array.from({ length: n }, pick), radii = Array.from({ length: n + 1 }, pick);
        const blend = pick(), attach = pick(), detail = pick();
        const template = rng() < cfg.dominanceA ? "A" : "B";
        rows.push({ kind: "pair", a: pa.name, b, score, core, root: pa.parent === null, inherit, template,
          bones, radii, blend, attach, detail });
      } else {
        rows.push({ kind: "single", src: "A", name: pa.name, core: pa.isCore,
          inherit: rng() < (pa.isCore ? cfg.coreLock : pPeriph) });
      }
    }
    for (const pb of gb.parts) {
      if (matchedB.has(pb.name)) continue;
      rows.push({ kind: "single", src: "B", name: pb.name, core: pb.isCore,
        inherit: rng() < (pb.isCore ? cfg.coreLock * 0.5 : pPeriph) });
    }
    return rows;
  }

  function crossPart(pa, pb, row) {
    const n = row.bones.length, a = resamplePart(pa, n), b = resamplePart(pb, n);
    const tpl = row.template === "A" ? pa : pb, src = row.detail ? pa : pb;
    const picks = [...row.bones, ...row.radii, row.blend, row.detail];
    if (!row.root) picks.push(row.attach);
    const anc = picks.reduce((s, x) => s + (x ? pa.anc : pb.anc), 0) / picks.length;
    return {
      name: tpl.name, parent: tpl.parent, mirror: tpl.mirror, tags: tpl.tags.slice(), isCore: tpl.isCore,
      origin: tpl.origin.slice(),
      offsets: row.bones.map((x, i) => (x ? a : b).offsets[i].slice()),
      radii: row.radii.map((x, i) => (x ? a : b).radii[i]),
      blend: row.blend ? a.blend : b.blend,
      attach: row.attach ? a.attach : b.attach,
      detail0: src.detail0 ? src.detail0.map((r) => r.slice()) : null,
      detail1: src.detail1 ? src.detail1.map((r) => r.slice()) : null,
      anc,
    };
  }

  /** Deterministic: plan -> child genome. Returns {genome, rowInfo[]} where rowInfo says what became
      of each row ("made" with the child part name, "skipped", or "orphan" when its parent is missing). */
  function buildChild(ga, gb, rows) {
    const A = new Map(ga.parts.map((p) => [p.name, p])), B = new Map(gb.parts.map((p) => [p.name, p]));
    const child = [], nameMap = new Map(), used = new Set(), info = [];
    const unique = (name) => {
      let out = name, k = 2;
      while (used.has(out)) out = `${name}_${k++}`;
      used.add(out);
      return out;
    };
    const resolve = (options) => {
      for (const [src, p] of options) {
        if (p.parent === null) return null;
        const key = `${src}:${p.parent}`;
        if (nameMap.has(key)) return nameMap.get(key);
      }
      return false;
    };
    for (const row of rows) {
      if (!row.inherit) { info.push({ status: "skipped" }); continue; }
      if (row.kind === "pair") {
        const pa = A.get(row.a), pb = B.get(row.b), part = crossPart(pa, pb, row);
        const order = row.template === "A" ? [["A", pa], ["B", pb]] : [["B", pb], ["A", pa]];
        const parent = resolve(order);
        if (parent === false) { info.push({ status: "orphan" }); continue; }
        part.name = unique(part.name);
        part.parent = parent;
        child.push(part);
        nameMap.set(`A:${pa.name}`, part.name);
        nameMap.set(`B:${pb.name}`, part.name);
        info.push({ status: "made", name: part.name });
      } else {
        const p = (row.src === "A" ? A : B).get(row.name), parent = resolve([[row.src, p]]);
        if (parent === false) { info.push({ status: "orphan" }); continue; }
        const part = clonePart(p);
        part.name = unique(p.name);
        part.parent = parent;
        child.push(part);
        nameMap.set(`${row.src}:${p.name}`, part.name);
        info.push({ status: "made", name: part.name });
      }
    }
    return { genome: enforceSymmetry({ parts: child }), rowInfo: info };
  }

  // ---- 4. mutation as replayable operations ---------------------------------------------------
  function rollMutations(genome, rng, cfg = CFG) {
    let count = 0;
    for (let i = 0; i < cfg.microBudget; i++) if (rng() < cfg.microRate) count++;
    const ops = [];
    for (let c = 0; c < count; c++) {
      const p = genome.parts[rng.int(genome.parts.length)], n = p.offsets.length, roll = rng();
      if (roll < 0.4) {
        ops.push({ type: "bone", part: p.name, i: rng.int(n), scale: 1 + rng.normal() * cfg.microSigma,
          noise: [0, 1, 2].map(() => rng.normal() * cfg.microSigma * 0.5) });
      } else if (roll < 0.8) {
        ops.push({ type: "radius", part: p.name, i: rng.int(n + 1), factor: 1 + rng.normal() * cfg.microSigma });
      } else {
        ops.push({ type: "detail", part: p.name, h: 1 + rng.int(6),
          da: rng.normal() * cfg.detailSigma, db: rng.normal() * cfg.detailSigma });
      }
    }
    return ops;
  }
  /** Applies ops where the part and index still exist. Returns {genome, applied[]}. */
  function applyMutations(genome, ops) {
    const parts = genome.parts.map(clonePart), byName = new Map(parts.map((p) => [p.name, p])), applied = [];
    for (const op of ops) {
      const p = byName.get(op.part);
      if (!p) { applied.push(false); continue; }
      if (op.type === "bone" && op.i < p.offsets.length) {
        const o = p.offsets[op.i], len = Math.hypot(o[0], o[1], o[2]);
        p.offsets[op.i] = o.map((v, d) => v * op.scale + op.noise[d] * len);
        applied.push(true);
      } else if (op.type === "radius" && op.i < p.radii.length) {
        p.radii[op.i] = Math.max(0.004, p.radii[op.i] * op.factor);
        applied.push(true);
      } else if (op.type === "detail") {
        if (!p.detail0 || !p.detail1) {
          const base = Array.from({ length: 7 }, (_, i) => [i === 0 ? 1 : 0, 0]);
          p.detail0 = base.map((r) => r.slice());
          p.detail1 = base.map((r) => r.slice());
        }
        if (op.h < p.detail0.length && op.h < p.detail1.length) {
          for (const d of [p.detail0, p.detail1]) { d[op.h][0] += op.da; d[op.h][1] += op.db; }
          applied.push(true);
        } else applied.push(false);
      } else applied.push(false);
    }
    return { genome: enforceSymmetry({ parts }), applied };
  }

  // ---- 5. symmetry ----------------------------------------------------------------------------
  /** Midline parts stay on the y = 0 plane and keep a left/right-symmetric outline. */
  function enforceSymmetry(g) {
    const sym = (d) => (d ? d.map((r, n) => (n % 2 === 0 ? [r[0], 0] : [0, r[1]])) : null);
    return { parts: g.parts.map((p) => (p.mirror ? p : {
      ...p, offsets: p.offsets.map((o) => [o[0], 0, o[2]]), origin: [p.origin[0], 0, p.origin[2]],
      detail0: sym(p.detail0), detail1: sym(p.detail1),
    })) };
  }

  // ---- development: genome -> placed bone segments --------------------------------------------
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const norm = (a) => { const l = Math.hypot(a[0], a[1], a[2]) + 1e-12; return [a[0] / l, a[1] / l, a[2] / l]; };

  /** Double-reflection rotation-minimizing frames (Wang et al. 2008). Returns {nrm, binrm}. */
  function rmFrames(pts) {
    const n = pts.length, tang = [];
    for (let i = 0; i < n; i++) {
      const t = i === 0 ? sub(pts[1], pts[0]) : i === n - 1 ? sub(pts[n - 1], pts[n - 2])
        : sub(pts[i + 1], pts[i - 1]).map((v) => v / 2);
      tang.push(norm(t));
    }
    let r0 = sub([0, 0, 1], tang[0].map((v) => v * tang[0][2]));
    if (Math.hypot(...r0) < 1e-6) r0 = sub([1, 0, 0], tang[0].map((v) => v * tang[0][0]));
    const nrm = [norm(r0)];
    for (let i = 0; i < n - 1; i++) {
      const v1 = sub(pts[i + 1], pts[i]), c1 = dot(v1, v1);
      if (c1 < 1e-14) { nrm.push(nrm[i]); continue; }
      const rl = sub(nrm[i], v1.map((v) => v * (2 / c1) * dot(v1, nrm[i])));
      const tl = sub(tang[i], v1.map((v) => v * (2 / c1) * dot(v1, tang[i])));
      const v2 = sub(tang[i + 1], tl), c2 = dot(v2, v2);
      let rn = c2 < 1e-14 ? rl : sub(rl, v2.map((v) => v * (2 / c2) * dot(v2, rl)));
      rn = sub(rn, tang[i + 1].map((v) => v * dot(rn, tang[i + 1])));
      nrm.push(norm(rn));
    }
    return { nrm, binrm: tang.map((t, i) => cross(t, nrm[i])) };
  }

  function isCircle(d) {
    if (!d) return true;
    return Math.abs(d[0][0] - 1) < 1e-6 && d.every((r, n) => n === 0 || (Math.abs(r[0]) < 1e-6 && Math.abs(r[1]) < 1e-6));
  }

  /** Genome -> pieces [{name, gene, k, anc, segments, detail, joints}]. Mirrored parts give L and R. */
  function develop(g, useDetail = true) {
    const jointsOf = new Map(), pieces = [];
    for (const p of g.parts) {
      const start = p.parent === null ? p.origin.slice() : pointOnChain(jointsOf.get(p.parent), p.attach);
      const joints = chainJoints(p, start), n = p.offsets.length;
      jointsOf.set(p.name, joints);
      const { nrm, binrm } = rmFrames(joints);
      const segs = [];
      for (let i = 0; i < n; i++) {
        segs.push({ a: joints[i], b: joints[i + 1], ra: p.radii[i], rb: p.radii[i + 1],
          fa: [binrm[i], nrm[i]], fb: [binrm[i + 1], nrm[i + 1]], sa: i / n, sb: (i + 1) / n });
      }
      const detail = useDetail && p.detail0 && p.detail1 && !(isCircle(p.detail0) && isCircle(p.detail1))
        ? [p.detail0, p.detail1] : null;
      const base = { gene: p.name, k: p.blend, anc: p.anc, detail };
      if (p.mirror) {
        const sy = 2 * start[1], fl = (v) => [v[0], sy - v[1], v[2]], fv = (v) => [v[0], -v[1], v[2]];
        const mir = segs.map((s) => ({ ...s, a: fl(s.a), b: fl(s.b), fa: s.fa.map(fv), fb: s.fb.map(fv) }));
        pieces.push({ ...base, name: `${p.name}_L`, segments: segs, joints });
        pieces.push({ ...base, name: `${p.name}_R`, segments: mir, joints: joints.map(fl) });
      } else pieces.push({ ...base, name: p.name, segments: segs, joints });
    }
    return pieces;
  }

  // ---- implicit surface -----------------------------------------------------------------------
  /** Sample g = -log(sum_p exp(-d_p / k_p)) on a grid. index = (i * ny + j) * nz + k. */
  function buildField(pieces, voxel) {
    const rMin = 0.9 * voxel;
    let lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity], rMax = 0, kMax = 0;
    for (const pc of pieces) {
      kMax = Math.max(kMax, pc.k);
      for (const s of pc.segments) {
        rMax = Math.max(rMax, s.ra, s.rb);
        for (const q of [s.a, s.b]) for (let d = 0; d < 3; d++) { lo[d] = Math.min(lo[d], q[d]); hi[d] = Math.max(hi[d], q[d]); }
      }
    }
    const pad = rMax + 8 * kMax + 3 * voxel;
    lo = lo.map((v) => v - pad);
    hi = hi.map((v) => v + pad);
    const dims = [0, 1, 2].map((d) => Math.ceil((hi[d] - lo[d]) / voxel) + 1);
    const [nx, ny, nz] = dims, size = nx * ny * nz;
    const total = new Float64Array(size), best = new Float32Array(size).fill(Infinity), owner = new Uint8Array(size);

    pieces.forEach((pc, idx) => {
      const k = pc.k, det = pc.detail;
      const segs = pc.segments.map((s) => {
        const ra = Math.max(s.ra, rMin), rb = Math.max(s.rb, rMin), ba = sub(s.b, s.a), l2 = dot(ba, ba), rr = ra - rb;
        return { s, ra, rb, ba, l2, rr, sphere: l2 <= rr * rr + 1e-12, a2: l2 - rr * rr, il2: 1 / Math.max(l2, 1e-18),
          rm: Math.max(ra, rb) };
      });
      const reach = Math.max(...segs.map((c) => c.rm)) + 8 * k + voxel;
      const i0 = [0, 0, 0], i1 = [0, 0, 0];
      for (let d = 0; d < 3; d++) {
        let mn = Infinity, mx = -Infinity;
        for (const c of segs) { mn = Math.min(mn, c.s.a[d], c.s.b[d]); mx = Math.max(mx, c.s.a[d], c.s.b[d]); }
        i0[d] = Math.max(Math.floor((mn - reach - lo[d]) / voxel), 0);
        i1[d] = Math.min(Math.ceil((mx + reach - lo[d]) / voxel) + 1, dims[d]);
      }
      const m = segs.length, dr = new Float64Array(m);
      for (let i = i0[0]; i < i1[0]; i++) {
        const px = lo[0] + voxel * i;
        for (let j = i0[1]; j < i1[1]; j++) {
          const py = lo[1] + voxel * j;
          for (let kk = i0[2]; kk < i1[2]; kk++) {
            const pz = lo[2] + voxel * kk;
            let dMin = Infinity, upper = Infinity;
            for (let c = 0; c < m; c++) {
              const sg = segs[c], A = sg.s.a, ba = sg.ba;
              const pax = px - A[0], pay = py - A[1], paz = pz - A[2];
              let d;
              if (sg.sphere) {
                const C = sg.ra >= sg.rb ? A : sg.s.b;
                d = Math.hypot(px - C[0], py - C[1], pz - C[2]) - sg.rm;
              } else {
                const y = pax * ba[0] + pay * ba[1] + paz * ba[2], z = y - sg.l2;
                const wx = pax * sg.l2 - ba[0] * y, wy = pay * sg.l2 - ba[1] * y, wz = paz * sg.l2 - ba[2] * y;
                const x2 = wx * wx + wy * wy + wz * wz, y2 = y * y * sg.l2, z2 = z * z * sg.l2;
                const kq = Math.sign(sg.rr) * sg.rr * sg.rr * x2;
                if (Math.sign(z) * sg.a2 * z2 > kq) d = Math.sqrt(x2 + z2) * sg.il2 - sg.rb;
                else if (Math.sign(y) * sg.a2 * y2 < kq) d = Math.sqrt(x2 + y2) * sg.il2 - sg.ra;
                else d = (Math.sqrt(x2 * sg.a2 * sg.il2) + y * sg.rr) * sg.il2 - sg.ra;
              }
              dr[c] = d;
              if (d < dMin) dMin = d;
              const u = d + (1 - DETAIL_MIN) * sg.rm;
              if (u < upper) upper = u;
            }
            if (dMin / k > 30) continue;                      // contributes < 1e-13
            let d = dMin;
            if (det) {
              d = Infinity;
              for (let c = 0; c < m; c++) {
                const sg = segs[c];
                if (dr[c] - (DETAIL_MAX - 1) * sg.rm > upper) continue;   // cannot be the nearest bone
                const s = sg.s, A = s.a, ba = sg.ba;
                const pax = px - A[0], pay = py - A[1], paz = pz - A[2];
                let t = (pax * ba[0] + pay * ba[1] + paz * ba[2]) * sg.il2;
                t = t < 0 ? 0 : t > 1 ? 1 : t;
                const wx = pax - t * ba[0], wy = pay - t * ba[1], wz = paz - t * ba[2], t1 = 1 - t;
                const bx = t1 * s.fa[0][0] + t * s.fb[0][0], by = t1 * s.fa[0][1] + t * s.fb[0][1], bz = t1 * s.fa[0][2] + t * s.fb[0][2];
                const nx_ = t1 * s.fa[1][0] + t * s.fb[1][0], ny_ = t1 * s.fa[1][1] + t * s.fb[1][1], nz_ = t1 * s.fa[1][2] + t * s.fb[1][2];
                const u = wx * bx + wy * by + wz * bz, v = wx * nx_ + wy * ny_ + wz * nz_;
                const rho = Math.sqrt(u * u + v * v);
                const cr = rho > 1e-12 ? u / rho : 1, ci = rho > 1e-12 ? v / rho : 0;
                const sp = s.sa + t * (s.sb - s.sa), d0 = det[0], d1 = det[1];
                let mul = d0[0][0] + sp * (d1[0][0] - d0[0][0]), zr = 1, zi = 0;
                for (let h = 1; h < d0.length; h++) {
                  const nr = zr * cr - zi * ci; zi = zr * ci + zi * cr; zr = nr;
                  mul += (d0[h][0] + sp * (d1[h][0] - d0[h][0])) * zr + (d0[h][1] + sp * (d1[h][1] - d0[h][1])) * zi;
                }
                mul = mul < DETAIL_MIN ? DETAIL_MIN : mul > DETAIL_MAX ? DETAIL_MAX : mul;
                const wl = Math.sqrt(wx * wx + wy * wy + wz * wz) + 1e-9;
                const side = Math.min(1, rho / wl);
                const dd = dr[c] - (sg.ra + t * (sg.rb - sg.ra)) * (mul - 1) * side;
                if (dd < d) d = dd;
              }
            }
            const q = d / k, at = (i * ny + j) * nz + kk;
            total[at] += Math.exp(-(q < -60 ? -60 : q > 60 ? 60 : q));
            if (q < best[at]) { best[at] = q; owner[at] = idx; }
          }
        }
      }
    });
    const g = new Float32Array(size);
    for (let i = 0; i < size; i++) g[i] = -Math.log(Math.max(total[i], 1e-30));
    return { g, owner, lo, dims, voxel };
  }

  /** Naive surface nets: one vertex per cell the surface crosses, one quad per crossed grid edge.
      Returns {positions Float32Array, indices Uint32Array, vertOwner Uint8Array}. Normals point outward. */
  function surfaceNets(field) {
    const { g, owner, lo, dims, voxel } = field, [nx, ny, nz] = dims;
    const at = (i, j, k) => (i * ny + j) * nz + k;
    const cx = nx - 1, cy = ny - 1, cz = nz - 1, cell = new Int32Array(cx * cy * cz).fill(-1);
    const cat = (i, j, k) => (i * cy + j) * cz + k;
    const pos = [], own = [];
    const corners = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1], [1, 1, 1]];
    const edges = [[0, 1], [2, 3], [4, 5], [6, 7], [0, 2], [1, 3], [4, 6], [5, 7], [0, 4], [1, 5], [2, 6], [3, 7]];
    const val = new Float64Array(8);
    for (let i = 0; i < cx; i++) for (let j = 0; j < cy; j++) for (let k = 0; k < cz; k++) {
      let mask = 0, minV = Infinity, minC = 0;
      for (let c = 0; c < 8; c++) {
        const v = g[at(i + corners[c][0], j + corners[c][1], k + corners[c][2])];
        val[c] = v;
        if (v < 0) mask |= 1 << c;
        if (v < minV) { minV = v; minC = c; }
      }
      if (mask === 0 || mask === 255) continue;
      let sx = 0, sy = 0, sz = 0, cnt = 0;
      for (const [e0, e1] of edges) {
        const v0 = val[e0], v1 = val[e1];
        if ((v0 < 0) === (v1 < 0)) continue;
        const t = v0 / (v0 - v1);
        sx += corners[e0][0] + t * (corners[e1][0] - corners[e0][0]);
        sy += corners[e0][1] + t * (corners[e1][1] - corners[e0][1]);
        sz += corners[e0][2] + t * (corners[e1][2] - corners[e0][2]);
        cnt++;
      }
      cell[cat(i, j, k)] = pos.length / 3;
      pos.push(lo[0] + (i + sx / cnt) * voxel, lo[1] + (j + sy / cnt) * voxel, lo[2] + (k + sz / cnt) * voxel);
      own.push(owner[at(i + corners[minC][0], j + corners[minC][1], k + corners[minC][2])]);
    }
    const idx = [];
    const quad = (a, b, c, d, flip) => {
      if (a < 0 || b < 0 || c < 0 || d < 0) return;
      if (flip) idx.push(a, c, b, a, d, c); else idx.push(a, b, c, a, c, d);
    };
    for (let i = 1; i < cx; i++) for (let j = 1; j < cy; j++) for (let k = 1; k < cz; k++) {
      const in0 = g[at(i, j, k)] < 0;
      if (in0 !== (g[at(i + 1, j, k)] < 0)) quad(cell[cat(i, j - 1, k - 1)], cell[cat(i, j, k - 1)], cell[cat(i, j, k)], cell[cat(i, j - 1, k)], !in0);
      if (in0 !== (g[at(i, j + 1, k)] < 0)) quad(cell[cat(i - 1, j, k - 1)], cell[cat(i - 1, j, k)], cell[cat(i, j, k)], cell[cat(i, j, k - 1)], !in0);
      if (in0 !== (g[at(i, j, k + 1)] < 0)) quad(cell[cat(i - 1, j - 1, k)], cell[cat(i, j - 1, k)], cell[cat(i, j, k)], cell[cat(i - 1, j, k)], !in0);
    }
    return { positions: new Float32Array(pos), indices: new Uint32Array(idx), vertOwner: new Uint8Array(own) };
  }

  /** closed: every directed edge has exactly as many reverse twins. components: connected pieces. */
  function meshReport(mesh) {
    const { positions, indices } = mesh, nv = positions.length / 3, edges = new Map();
    const parent = new Int32Array(nv).map((_, i) => i);
    const find = (x) => { while (parent[x] !== x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; };
    let volume = 0;
    for (let f = 0; f < indices.length; f += 3) {
      const t = [indices[f], indices[f + 1], indices[f + 2]];
      for (let e = 0; e < 3; e++) {
        const a = t[e], b = t[(e + 1) % 3], key = a * nv + b;
        edges.set(key, (edges.get(key) || 0) + 1);
        parent[find(a)] = find(b);
      }
      const p = t.map((v) => [positions[3 * v], positions[3 * v + 1], positions[3 * v + 2]]);
      volume += dot(p[0], cross(p[1], p[2])) / 6;
    }
    let closed = true;
    for (const [key, c] of edges) {
      const a = Math.floor(key / nv), b = key % nv;
      if ((edges.get(b * nv + a) || 0) !== c) { closed = false; break; }
    }
    const used = new Set();
    for (let i = 0; i < indices.length; i++) used.add(find(indices[i]));
    return { closed, components: used.size, triangles: indices.length / 3, vertices: nv, volume };
  }

  function buildCreature(genome, voxel, useDetail = true) {
    const pieces = develop(genome, useDetail), field = buildField(pieces, voxel), mesh = surfaceNets(field);
    return { pieces, mesh };
  }

  /** OBJ text, converted to Y-up: (x, y, z) -> (x, z, -y). */
  function toObj(mesh, name) {
    const { positions: p, indices: ix } = mesh, out = [`# RTIS breeding bench - Y-up`, `o ${name}`];
    for (let i = 0; i < p.length; i += 3) out.push(`v ${p[i].toFixed(5)} ${p[i + 2].toFixed(5)} ${(-p[i + 1]).toFixed(5)}`);
    for (let i = 0; i < ix.length; i += 3) out.push(`f ${ix[i] + 1} ${ix[i + 1] + 1} ${ix[i + 2] + 1}`);
    return out.join("\n") + "\n";
  }

  /** Minimal store-only zip. files: [{name, text}] -> Uint8Array. */
  function makeZip(files) {
    const enc = new TextEncoder(), table = new Uint32Array(256);
    for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; table[n] = c >>> 0; }
    const crc32 = (b) => { let c = 0xffffffff; for (let i = 0; i < b.length; i++) c = table[(c ^ b[i]) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
    const chunks = [], central = [];
    let offset = 0;
    const push = (arr) => { chunks.push(arr); offset += arr.length; };
    const header = (sig, extra, nameB, crc, size, localOffset) => {
      const h = new DataView(new ArrayBuffer(extra ? 46 : 30));
      let o = 0;
      const u32 = (v) => { h.setUint32(o, v, true); o += 4; }, u16 = (v) => { h.setUint16(o, v, true); o += 2; };
      u32(sig); if (extra) u16(20); u16(20); u16(0x0800); u16(0); u16(0); u16(0x21);
      u32(crc); u32(size); u32(size); u16(nameB.length); u16(0);
      if (extra) { u16(0); u16(0); u16(0); u32(0); u32(localOffset); }
      return new Uint8Array(h.buffer);
    };
    for (const f of files) {
      const nameB = enc.encode(f.name), data = enc.encode(f.text), crc = crc32(data), local = offset;
      push(header(0x04034b50, false, nameB, crc, data.length, 0)); push(nameB); push(data);
      central.push([header(0x02014b50, true, nameB, crc, data.length, local), nameB]);
    }
    const cdStart = offset;
    for (const [h, n] of central) { push(h); push(n); }
    const end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
    end.setUint32(12, offset - cdStart, true); end.setUint32(16, cdStart, true);
    push(new Uint8Array(end.buffer));
    const out = new Uint8Array(offset);
    let o = 0;
    for (const c of chunks) { out.set(c, o); o += c.length; }
    return out;
  }

  return { CFG, makeRng, fromJson, toJson, geneCount, partGeneCount, matchParts, planCross, buildChild,
    rollMutations, applyMutations, enforceSymmetry, develop, buildField, surfaceNets, meshReport,
    buildCreature, toObj, makeZip, resamplePart, tagSimilarity };
})();
if (typeof module !== "undefined") module.exports = Core;
