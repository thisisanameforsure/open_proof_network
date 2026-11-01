"""F33-T0: list every surviving mutant question with the variant rebuilt by the gate's own code.

Reads the graph tree given as argv[1] (read-only); writes mutants.json beside this script.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from opn_gate import review_lean, review_mutants

graph = Path(sys.argv[1])
out = []
for rv in sorted(graph.glob("targets/*/review/review.yaml")):
    rdir = rv.parent
    target = rdir.parent.name
    review = yaml.safe_load(rv.read_text())
    concepts = review.get("concepts") or []
    words = review.get("words") or ""
    for q in sorted(rdir.glob("questions/*.yaml")):
        qd = yaml.safe_load(q.read_text())
        rb = qd.get("raised_by") or {}
        if rb.get("kind") != "mutant":
            continue
        ex = json.loads((rdir / "exhibits" / f"{rb['ref']}.json").read_text())
        lab = review_mutants.label_of(ex["detail"])
        cid = ex["candidate"]
        src = (rdir / "candidates" / f"{cid}.lean").read_text()
        rec = {
            "target": target,
            "question": qd["id"],
            "exhibit": ex["id"],
            "detail": ex["detail"],
            "candidate": cid,
            "words": words,
            "concepts": concepts,
            "exhibit_lean": (rdir / "exhibits" / ex["lean_file"]).read_text()
            if ex.get("lean_file")
            else None,
        }
        if lab is None:
            rec["error"] = "no label"
            out.append(rec)
            continue
        label, cls = lab
        rec.update(label=label, cls=cls)
        c = review_lean.prepare("c-orig", src, concepts)
        found, _ = review_mutants.mutants(c, concepts)
        mu = next((m for m in found if m.label == label), None)
        if mu is None:
            rec["error"] = "label not rebuilt"
            out.append(rec)
            continue
        v = review_lean.prepare("c-var", mu.source, concepts)
        rec.update(
            imports=list(c.imports),
            orig_body=c.body,
            orig_prop=" ".join(c.claim_prop.split()),
            orig_claim=c.claim,
            var_body=v.body if isinstance(v, review_lean.Cand) else None,
            var_prop=" ".join(v.claim_prop.split()) if isinstance(v, review_lean.Cand) else None,
            var_claim=v.claim if isinstance(v, review_lean.Cand) else None,
            shape=c.shape,
            variant_line=review_mutants.variant(src, concepts, label),
        )
        out.append(rec)
Path(__file__).with_name("mutants.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(len(out), sum("error" in r for r in out))
