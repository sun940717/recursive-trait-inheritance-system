#!/usr/bin/env python3
"""
surject_audit.py
================
Which inheritance combinations can a child of biped x spider actually have under the adopted rules
(with the part-attribute layer on)? Breeds many children and counts what appears.
在已採用的規則下（屬性層開啟），二足 × 蜘蛛的子代實際上可能出現哪些遺傳組合？交配多次並統計。
Target: Python 3.10.12 · numpy. Needs the same files as attr_eval.py.
"""
from __future__ import annotations
import argparse, json
from collections import Counter
import numpy as np
import skeleton_sdf_demo as sk
import form_fusion_lab as lab
import attr_eval


def switches(flags) -> int:
    f = list(flags)
    return sum(f[i] != f[i + 1] for i in range(len(f) - 1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--matings", type=int, default=1500)
    ap.add_argument("--a", default="biped")
    ap.add_argument("--b", default="spider")
    args = ap.parse_args(argv)
    forms = lab.all_forms(ontology_tags=True)
    legs, presence, body_sw, body_pure, both_leg_kinds, tail_and_abdomen, per_leg_mixed = (
        Counter(), Counter(), Counter(), 0, 0, 0, 0)
    for s in range(args.matings):
        child, log, attr = attr_eval.breed(forms, args.a, args.b, 5000 + s, True)
        n = sum(2 if sk.arrangement(p) == "mirror" else 1 for p in child.parts if "locomotion" in p.tags)
        legs[n] += 1
        srcs = {k.split(".")[0] + "." + k.split(".")[1] for k in log["sources"]}
        presence[tuple(sorted(k for k in srcs if not k.endswith(("body", "cephalothorax"))))] += 1
        root = child.parts[0].name
        g = log["genes"].get(root, {})
        flags = [g["head"], *g["lengths"]] if "lengths" in g else []
        body_sw[switches(g.get("lengths", []))] += 1
        body_pure += bool(g) and (all(g["lengths"] + g["radii"] + g["bends"]) or not any(g["lengths"] + g["radii"] + g["bends"]))
        kinds = {o.split(".")[0] for p in child.parts if "locomotion" in p.tags for o in [k for k, v in log["sources"].items() if v == p.name]}
        both_leg_kinds += any("A.leg_rear" == k for k in log["sources"] if log["sources"][k] in [p.name for p in child.parts if "locomotion" in p.tags]) and \
            sum(1 for p in child.parts if "locomotion" in p.tags) > 1 and len([1 for st in attr.log["sets"]]) == 0
        tail_and_abdomen += ("A.tail" in log["sources"]) and ("B.abdomen" in log["sources"])
        st = attr.log["sets"]
        per_leg_mixed += bool(st) and len({tuple(sorted(attr.log["parts"].get(l[0] if st[0]["count_from"] == "A" else l[1], {}).get("from", {}).items()))
                                            for l in st[0]["limbs"]}) > 1
    out = {"matings": args.matings, "legs": dict(sorted(legs.items())),
           "body_length_switch_points": dict(sorted(body_sw.items())),
           "body_all_genes_from_one_parent": body_pure,
           "tail_and_abdomen_both": tail_and_abdomen,
           "legs_with_different_attribute_sources_in_one_set": per_leg_mixed,
           "distinct_part_presence_patterns": len(presence)}
    print(json.dumps(out, indent=1))
    json.dump(out, open("surject_audit.json", "w"), indent=1)


if __name__ == "__main__":
    main()
