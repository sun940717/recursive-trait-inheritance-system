import sys, time, numpy as np
sys.path.insert(0, "/home/claude")
import skeleton_sdf_demo as sk, fourier3d_demo as fd, fourier_genetics as fg

# 1. detail = None must reproduce the round skin exactly; a circle detail (c0 = 1) must too
g = sk.tube_genome_to_skeleton(fd.default_genome())
m_round, _, _ = sk.build_sdf_creature(g, 0.03, use_detail=False)
import dataclasses
circ = np.zeros((7, 2)); circ[0, 0] = 1.0
g_circ = sk.SkeletonGenome([dataclasses.replace(p, detail0=circ.copy(), detail1=circ.copy()) for p in g.parts])
m_circ, _, _ = sk.build_sdf_creature(g_circ, 0.03, use_detail=True)
print("circle detail == round skin:", m_round.faces.shape == m_circ.faces.shape and np.allclose(m_round.vertices, m_circ.vertices, atol=1e-9))

# 2. polar fit reproduces the tube's section outline
t = fg.biped_genome().tubes[0]
th = np.linspace(0, 2*np.pi, 720, endpoint=False)
c = fd.eval_section(t.sect0, th); scale = np.linalg.norm(fd.eval_section(t.sect0, np.linspace(0, 2*np.pi, 64, endpoint=False)), axis=1).mean()
det = sk.fit_polar_detail(c, scale, 6)
phi = np.arctan2(c[:, 1], c[:, 0]); r = np.hypot(c[:, 0], c[:, 1]) / scale
fit = sk.polar_multiplier(det, det, np.exp(1j * phi), np.zeros_like(phi))
print("polar fit max error (biped body section, 6 harmonics): %.4f of the radius" % np.abs(fit - r).max())

# 3. midline symmetry survives crossover + mutation: body outline is mirror-symmetric
cfg = sk.SkeletonInheritanceConfig(); rng = np.random.default_rng(3)
a = sk.with_ancestry(sk.tube_genome_to_skeleton(fd.default_genome()), 1.0)
b = sk.with_ancestry(sk.tube_genome_to_skeleton(fg.biped_genome(), bones={"arm_front": 4, "horn": 3}), 0.0)
worst = 0.0
for _ in range(20):
    child, _ = sk.reproduce(a, b, cfg, rng)
    for p in child.parts:
        if not p.mirror and p.detail0 is not None:
            for d in (p.detail0, p.detail1):
                m1 = sk.polar_multiplier(d, d, np.exp(1j * th), np.zeros_like(th))
                m2 = sk.polar_multiplier(d, d, np.exp(1j * (np.pi - th)), np.zeros_like(th))
                worst = max(worst, float(np.abs(m1 - m2).max()))
print("midline outline left/right asymmetry after 20 crosses: %.2e" % worst)

# 4. whole-mesh left/right symmetry of a child (vertices mirrored in y should match the surface)
child, _ = sk.reproduce(a, b, cfg, rng)
pieces = sk.develop_segments(child)
f, _, lo = sk.build_field(pieces, 0.03)
ny = f.shape[1]
print("field is mirror-symmetric in y (max abs diff): %.2e" % float(np.abs(f - f[:, ::-1, :]).max()) if abs(lo[1] + (lo[1] + 0.03 * (ny - 1))) < 1e-9 else "grid not centred on y = 0; skipping field symmetry test")

# 5. does the leftover size error come from the bone count? body with 5 vs 9 bones
tube = fd.default_genome()
parts = fd.build_creature(tube)
seg_t = np.concatenate([c for c in (sk.slice_mesh(m, 0, 0.0) for _, m in parts) if len(c)])
centre = np.array(sk.outline_stats(seg_t)["centre"]); pt = sk.outline_polar(seg_t, centre)
for nb in (5, 9):
    gg = sk.tube_genome_to_skeleton(tube, bones={"body": nb})
    m, _, _ = sk.build_sdf_creature(gg, 0.015)
    ps = sk.outline_polar(sk.slice_mesh(m, 0, 0.0), centre)
    print("body with %d bones: outline error %.1f%%, genes %d, closed %s" % (
        nb, 100 * np.sqrt(np.mean((ps - pt) ** 2)) / pt.mean(), gg.gene_count(), sk.mesh_report(m)["closed"]))
