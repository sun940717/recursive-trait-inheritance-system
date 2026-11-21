import sys, numpy as np, dataclasses
sys.path.insert(0, "/home/claude")
import form_fusion_lab as lab, skeleton_sdf_demo as sk
forms = lab.all_forms()
# 1. encode -> decode round trip in the part's own context reproduces the world offsets
worst = 0.0
for name, g in forms.items():
    g = sk.enforce_symmetry(g); ch = lab.chains(g); S = lab.body_scale(g)
    for p in g.parts:
        fr = None if p.parent is None else lab.frame_at(ch[p.parent], p.attach)
        rel = lab.encode(p, fr, S); dec = lab.decode(rel, fr, S, sk.arrangement(p), rel.get("azimuth"))
        worst = max(worst, float(np.abs(dec["offsets"] - p.offsets).max()), float(np.abs(dec["radii"] - p.radii).max()))
print("round trip max error:", f"{worst:.2e}")
# 2. a form crossed with itself under every rule returns itself (same shape genes on both sides)
cfg = sk.SkeletonInheritanceConfig(micro_budget=0, core_lock=1.0, inheritance_factor=1.0)
for rule, opt in lab.RULES.items():
    w = 0.0; ok = True
    for name, g in forms.items():
        g = sk.enforce_symmetry(sk.with_ancestry(g, 1.0))
        child, log = lab.fuse(g, g, np.random.default_rng(1), cfg, opt)
        ok &= [p.name for p in child.parts] == [p.name for p in g.parts]
        if ok:
            w = max(w, max(float(np.abs(c.offsets - p.offsets).max()) for c, p in zip(child.parts, g.parts)))
    print(f"self-cross under '{rule}': same parts {ok}, max offset change {w:.2e}")
# 3. radial copies: jellyfish has 1 + 8 + 4 chains, and is symmetric left/right
pcs = sk.develop_segments(forms["jellyfish"]); print("jellyfish chains:", len(pcs))
f, _, lo = sk.build_field(pcs, 0.03)
m = sk.extract_mesh(f, lo, 0.03); v = m.vertices
print("jellyfish mesh y-range symmetric:", round(float(v[:,1].min()), 3), round(float(v[:,1].max()), 3), "| x-range:", round(float(v[:,0].min()), 3), round(float(v[:,0].max()), 3))
