import sys, numpy as np
sys.path.insert(0, "/home/claude")
import form_fusion_lab as lab, skeleton_sdf_demo as sk, fourier3d_demo as fd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
forms = lab.all_forms(); names = list(forms); cfg = sk.SkeletonInheritanceConfig(micro_budget=0)
for a, b in (("biped", "jellyfish"), ("serpent", "jellyfish")):
    ga, gb = sk.with_ancestry(forms[a], 1.0), sk.with_ancestry(forms[b], 0.0)
    rng = np.random.default_rng([7, names.index(a), names.index(b)])
    for c in range(3):
        child, log = lab.fuse(ga, gb, rng, cfg, lab.RULES["wide"])
        mesh, _, _ = sk.build_sdf_creature(child, 0.03)
        f = mesh.faces; n = len(mesh.vertices)
        g = coo_matrix((np.ones(len(f) * 3), (np.r_[f[:, 0], f[:, 1], f[:, 2]], np.r_[f[:, 1], f[:, 2], f[:, 0]])), shape=(n, n))
        k, lab_ = connected_components(g, directed=False)
        vols = []
        for comp in np.unique(lab_[f[:, 0]]):
            sub = fd.Mesh(mesh.vertices, f[lab_[f[:, 0]] == comp]); vols.append(round(fd.signed_volume(sub), 5))
        print(a, "x", b, "child", c, "components", len(vols), "signed volumes", vols,
              "| parts:", [(p.name, sk.arrangement(p), p.radial) for p in child.parts])
        if len(vols) > 1:
            fine, _, _ = sk.build_sdf_creature(child, 0.015); print("   at the fine grid 0.015:", sk.mesh_report(fine)["components"], "piece(s)")
