#!/usr/bin/env python3
"""Build a closing proof of erdos-1050--h1-v2 that names h3 (hole theorem) and proves hrem inline
from 1050-A/h4-Proof.lean.  Usage: build_close.py OUT [--count]"""
import sys, re
E = "/home/user/open_proof_network/engineering/evidence/testers-2026-09-29"
G = "graph/targets/erdos-1050/nodes"
h4stmt = open(f"{G}/erdos-1050--h1-v2--h4/Statement.lean", encoding="utf-8").read()
h4proof = open(sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else f"{E}/1050-A/h4-Proof.lean", encoding="utf-8").read()
close = open(f"{E}/1050-D/parent_close_via_h3_h4.lean", encoding="utf-8").read()
# h4 type: text between 'theorem erdos_1050__h1_v2__h4 :' and ':= by'
i = h4stmt.index("theorem erdos_1050__h1_v2__h4 :") + len("theorem erdos_1050__h1_v2__h4 :")
j = h4stmt.index(":= by", i)
h4type = h4stmt[i:j].strip()
assert h4proof.startswith(h4stmt[: h4stmt.index(":= by") + len(":= by")]), "h4 proof header differs"
body = h4proof[h4proof.index(":= by", h4proof.index("theorem erdos_1050__h1_v2__h4")) + len(":= by"):]
body = body.strip("\n")
ind = lambda s, k: "\n".join((" " * k + l) if l.strip() else l for l in s.split("\n"))
block = "  -- hrem, proved inline (the proof of erdos-1050--h1-v2--h4 by this pseudonym, 1050-A/h4-Proof.lean),\n" \
        "  -- so that this closing proof needs only h3 to have merged as proved.\n" \
        "  have hrem_all : " + ind(h4type, 4).lstrip() + " := by\n" + ind(body, 2) + "\n"
old = "    erdos_1050__h1_v2__h4 Qc hQc Qx hQx Aq hAq hden\n"
assert close.count(old) == 1
close = close.replace(old, "    hrem_all Qc hQc Qx hQx Aq hAq hden\n")
anchor = "  -- Informal account: annex f593a93a8960"
assert close.count(anchor) == 1
close = close.replace(anchor, block + anchor)
if "--count" in sys.argv:
    close = close.replace("theorem erdos_1050__h1 :", "#count_heartbeats in\ntheorem erdos_1050__h1 :", 1)
open(sys.argv[1], "w", encoding="utf-8").write(close)
print("wrote", sys.argv[1], len(close), "bytes", close.count("\n"), "lines")
