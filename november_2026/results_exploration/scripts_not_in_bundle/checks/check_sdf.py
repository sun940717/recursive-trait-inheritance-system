import sys, numpy as np
sys.path.insert(0, "/home/claude")
import skeleton_sdf_demo as sk, fourier3d_demo as fd, fourier_genetics as fg
g = sk.tube_genome_to_skeleton(fg.biped_genome(), bones={"arm_front": 4, "horn": 3})
mesh, fp, pieces = sk.build_sdf_creature(g, 0.03)
rep = sk.mesh_report(mesh); print("biped:", rep)
# 1. the closed-check must fail on a mesh with a hole (so it is not a vacuous test)
holed = fd.Mesh(mesh.vertices, mesh.faces[1:])
print("check detects a hole:", sk.mesh_report(holed)["closed"] is False)
# 2. order independence: same pieces in reverse order -> same field
f1, _, lo1 = sk.build_field(pieces, 0.03); f2, _, lo2 = sk.build_field(pieces[::-1], 0.03)
print("order-independent field:", np.allclose(lo1, lo2) and float(np.abs(f1 - f2).max()) < 1e-9, float(np.abs(f1 - f2).max()))
# 3. resampling a chain keeps its end point and total shape
p = g.parts[0]; q = sk.resample_part(p, 9)
print("resample keeps end point:", np.allclose(p.offsets.sum(0), q.offsets.sum(0)))
# 4. round-cone distance sanity: on-axis point at an end cap, and a far point
a, b = np.array([0.,0,0]), np.array([1.,0,0])
d = sk.sd_round_cone(np.array([[-0.5,0,0],[0.5,0.3,0],[2.0,0,0]]), a, b, 0.2, 0.1)
print("round cone distances:", np.round(d, 4), "(expect -0.5-(-0.2)=0.3, ~0.3-0.15 band, 0.9)")
# 5. finer grid still one closed piece
m2, _, _ = sk.build_sdf_creature(g, 0.0125); print("fine grid:", sk.mesh_report(m2))
