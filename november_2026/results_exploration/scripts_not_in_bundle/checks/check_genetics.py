import sys, json, numpy as np
from collections import Counter
sys.path.insert(0, "/home/claude")
import fourier_genetics as fg
import fourier3d_demo as fd
A = fg.with_ancestry(fd.default_genome(), 1.0); B = fg.with_ancestry(fg.biped_genome(), 0.0)
bad = 0; n = 0; structs = Counter()
for mode in ("locus", "band", "blend"):
    cfg = fg.FourierInheritanceConfig(mode=mode, medium_rate=0.6)  # force structural mutations often
    rng = np.random.default_rng(1)
    pop = [A, B]
    for gen in range(6):
        kids = []
        for _ in range(8):
            i, j = rng.choice(len(pop), 2, replace=len(pop) < 2)
            c, log = fg.reproduce(pop[i], pop[j], cfg, rng)
            # json round trip
            c2 = fd.Genome.from_json(json.loads(json.dumps(c.to_json())))
            assert np.allclose(c.to_vector(), c2.to_vector())
            names = [t.name for t in c.tubes]; assert len(names) == len(set(names))
            seen = set()
            for t in c.tubes:  # parents before children
                assert t.parent is None or t.parent in seen, (t.name, t.parent)
                seen.add(t.name)
            structs[len(c.tubes)] += 1
            for name, m in fd.build_creature(c, 24, 12):
                e = Counter()
                for f in m.faces:
                    for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])): e[(a, b)] += 1
                ok = all(v == 1 and e.get((b, a), 0) == 1 for (a, b), v in e.items())
                n += 1
                if not ok or fd.signed_volume(m) <= 0: bad += 1
            kids.append(c)
        pop = kids
print("parts checked:", n, "bad:", bad, "tube-count distribution:", dict(sorted(structs.items())))
