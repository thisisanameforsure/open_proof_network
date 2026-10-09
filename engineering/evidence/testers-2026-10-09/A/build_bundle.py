import json, sys
ts = sys.argv[1]
base = f"targets/erdos-1094/nodes/erdos-1094--h3--h1/attempts/{ts}-t1009-a-partial"
hdr = "import Mathlib\n\nopen scoped Nat\n\n"
w1 = "-- hole: h_keven\n\n" + hdr + "theorem witness : True := trivial\n"
w2 = "-- hole: h_odd\n\n" + hdr + "theorem witness : True := trivial\n"
bundle = {base + ".lean": open("skeleton.lean").read(), base + ".1.witness": w1, base + ".2.witness": w2}
if "--nowit" in sys.argv: bundle = {base + ".lean": bundle[base + ".lean"]}
json.dump({"node_id": "erdos-1094--h3--h1", "artifact_type": "partial", "bundle": bundle}, open("precheck-req.json", "w"))
print(list(bundle))
