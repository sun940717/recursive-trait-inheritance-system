import sys, json, numpy as np
from collections import Counter
sys.path.insert(0, "/home/claude")
import fourier3d_demo as fd
g = fd.default_genome()
rng = np.random.default_rng(0)
bad = 0
for trial in range(20):
    gg = fd.mutate(g, 0.3, rng) if trial else g
    for name, m in fd.build_creature(gg):
        e = Counter()
        for f in m.faces:
            for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                e[(a, b)] += 1
        # closed + consistently oriented: every directed edge appears once and its reverse once
        ok = all(c == 1 and e.get((b, a), 0) == 1 for (a, b), c in e.items())
        vol = fd.signed_volume(m)
        if not ok or vol <= 0:
            bad += 1; print("BAD", trial, name, ok, vol)
print("bad parts:", bad)
# JSON round trip
j = g.to_json(); g2 = fd.Genome.from_json(json.loads(json.dumps(j)))
print("roundtrip equal:", np.allclose(g.to_vector(), g2.to_vector()))
# symmetry check on midline sections after mutation
gm = fd.mutate(g, 0.5, rng, "all")
body = gm.tubes[0]
th = np.linspace(0, 2*np.pi, 64, endpoint=False)
c = fd.eval_section(body.sect0, th)
cm = fd.eval_section(body.sect0, np.pi - th) * np.array([-1, 1])
print("midline section symmetric:", np.allclose(c, cm))
