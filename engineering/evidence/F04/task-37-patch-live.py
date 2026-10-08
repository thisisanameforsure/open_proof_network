"""F04-T37/T38 evidence: a copy of the live graph clone's tree with its products rewritten as the
v3.35 gate will write them (graph/v6, frontier/v5) for the targets the amendment names.

    python patch_live.py --clone <graph clone> --out <copy> [--literature]

The four live nodes under merged circularity claims (erdos-1050--h1-v2--h1, erdos-69--h2-v2,
erdos-69--h2-v2--h1-v2, erdos-69--h2-v2--h1-v2--h4) get their labels and come back to the
frontier claimable; with --literature, erdos-1094--h2 carries a proposed `open` and --h3 a
confirmed `known` (Konyagin 1999) with a later proposal, the records written into the tree.
Every rewritten document is validated against its schema before it is written.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml

WT = Path("/Users/mikehiggins/Desktop/repos/open_proof_network/.claude/worktrees/agent-ac4d01386c9b917c0")
sys.path[:0] = [str(WT / "gate")]
from opn_gate import schemas  # noqa: E402

LABELS = {
    "erdos-1050": {
        "erdos-1050--h1-v2--h1": [
            {"ancestor": "erdos-1050--h1-v2", "claim": "erdos-1050--h1-v2--h1/defects/20260923T223809Z-lead-0923.yaml"}
        ],
    },
    "erdos-69": {
        "erdos-69--h2-v2": [
            {"ancestor": "erdos-69", "claim": "erdos-69--h2-v2/defects/20260924T123353Z-t0924-69m-8709.yaml"}
        ],
        "erdos-69--h2-v2--h1-v2": [
            {"ancestor": "erdos-69--h2-v2", "claim": "erdos-69--h2-v2--h1-v2--h4/defects/20260924T123205Z-t0924-69m-8709.yaml"}
        ],
        "erdos-69--h2-v2--h1-v2--h4": [
            {"ancestor": "erdos-69--h2-v2--h1-v2", "claim": "erdos-69--h2-v2--h1-v2--h4/defects/20260924T123205Z-t0924-69m-8709.yaml"},
            {"ancestor": "erdos-69--h2-v2", "claim": "erdos-69--h2-v2--h1-v2--h4/defects/20260924T123647Z-agent-e69h-0d8d.yaml"},
        ],
    },
}

KONYAGIN = [
    {
        "title": "S. V. Konyagin, Numbers that become composite after changing one or two digits (1999)",
        "url": "https://www.erdosproblems.com/1094",
        "note": "The 1999 paper proving the bound this hole states; never formalised.",
    },
    {
        "title": "A. Granville and O. Ramaré, Explicit bounds on exponential sums and the scarcity of squarefree binomial coefficients (1996)",
        "url": None,
        "note": "The earlier partial result the hole generalises.",
    },
]


def literature_record(node: str, *, contributor: str, date: str, status: str, references: list, summary: str, confirms: str | None = None, signed: bool = False) -> dict:
    return {
        "schema": "literature/v1",
        "node": node,
        "contributor": contributor,
        "date": date,
        "status": status,
        "references": references,
        "summary": summary,
        "model_and_tooling": "claude-fable-5-1" if not signed else None,
        "confirms": confirms,
        "via": "approval-key" if signed else None,
        "key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakeKeyForTheEvidenceOnly000000000000000000" if signed else None,
        "signature": "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n" if signed else None,
    }


def write_record(root: Path, target: str, node: str, doc: dict) -> str:
    stamp = doc["date"].replace("-", "").replace(":", "")
    rel = f"literature/{stamp}-{doc['contributor']}.yaml"
    path = root / "targets" / target / "nodes" / node / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    schemas.validate(doc, "literature/v1")
    path.write_text(yaml.safe_dump(doc, sort_keys=True, allow_unicode=True), encoding="utf-8")
    return rel


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clone", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--literature", action="store_true")
    a = ap.parse_args()
    if a.out.exists():
        shutil.rmtree(a.out)
    shutil.copytree(a.clone, a.out, ignore=shutil.ignore_patterns(".git"))
    root = a.out

    literature: dict[str, dict] = {}
    proposed: dict[str, dict] = {}
    if a.literature:
        t = "erdos-1094"
        # --h2: a contributor's proposal, awaiting a steward or curator.
        rel = write_record(root, t, "erdos-1094--h2", literature_record(
            "erdos-1094--h2", contributor="t1008-c", date="2026-10-08T14:02:11Z", status="open",
            references=[{"title": "Erdős problem #1094 (erdosproblems.com)", "url": "https://www.erdosproblems.com/1094", "note": "Lists the core case as open."}],
            summary="The Ecklund–Selfridge core: no proof is known for n < k^2; this is what remains open of #1094 once the literature theorem (--h3) is set aside. <b>Untrusted text</b> is shown escaped.",
        ))
        proposed["erdos-1094--h2"] = {"status": "open", "record": rel, "contributor": "t1008-c"}
        # --h3: a proposal, confirmed by the owner through the site, then a later proposal.
        rel3 = write_record(root, t, "erdos-1094--h3", literature_record(
            "erdos-1094--h3", contributor="t1008-c", date="2026-10-08T14:05:40Z", status="known",
            references=KONYAGIN,
            summary="Granville–Ramaré (1996) proved it for n ≥ k^2 up to a constant; Konyagin (1999) proved the stated bound in full. Neither proof is formalised in Lean.",
        ))
        conf = write_record(root, t, "erdos-1094--h3", literature_record(
            "erdos-1094--h3", contributor="thisisanameforsure", date="2026-10-08T15:10:00Z", status="known",
            references=KONYAGIN, summary="Confirmed as stated: Konyagin 1999.", confirms=rel3, signed=True,
        ))
        literature["erdos-1094--h3"] = {"status": "known", "record": rel3, "contributor": "t1008-c", "confirmed_by": "thisisanameforsure", "confirmation": conf}
        later = write_record(root, t, "erdos-1094--h3", literature_record(
            "erdos-1094--h3", contributor="t1008-a", date="2026-10-08T16:20:00Z", status="elementary",
            references=KONYAGIN[:1], summary="A later reading: with Konyagin's lemma in Mathlib this would be routine.",
        ))
        proposed["erdos-1094--h3"] = {"status": "elementary", "record": later, "contributor": "t1008-a"}

    targets = set(LABELS) | ({"erdos-1094"} if a.literature else set())
    rows_by_target: dict[str, dict[str, dict]] = {}
    for t in sorted(targets):
        gp = root / "targets" / t / "graph.json"
        g = json.loads(gp.read_text(encoding="utf-8"))
        assert g["schema"] == "graph/v5", g["schema"]
        g["schema"] = "graph/v6"
        for row in g["nodes"]:
            nid = row["node_id"]
            row["circular"] = LABELS.get(t, {}).get(nid, [])
            row["literature"] = literature.get(nid)
            row["literature_proposed"] = proposed.get(nid)
            if row["cause"] == "circular":
                row["cause"] = None
        rows_by_target[t] = {r["node_id"]: r for r in g["nodes"]}
        gp.write_text(json.dumps(schemas.validate(g, "graph/v6"), indent=1, sort_keys=True) + "\n")
        print("graph/v6:", t, [r["node_id"] for r in g["nodes"] if r["circular"] or r["literature"] or r["literature_proposed"]])

    fp = root / "frontier.json"
    f = json.loads(fp.read_text(encoding="utf-8"))
    assert f["schema"] == "frontier/v4"
    f["schema"] = "frontier/v5"
    present = {(e["target_id"], e["node_id"]) for e in f["entries"]}
    for e in f["entries"]:
        e["circular"] = LABELS.get(e["target_id"], {}).get(e["node_id"], [])
        e["literature"] = literature.get(e["node_id"]) if e["target_id"] == "erdos-1094" else None
        e["literature_proposed"] = proposed.get(e["node_id"]) if e["target_id"] == "erdos-1094" else None
        if e["cause"] == "circular":
            e["cause"] = None
    template = next(e for e in f["entries"] if e["target_id"] == "erdos-69")
    added = []
    for t, labels in LABELS.items():
        for nid, entries in labels.items():
            if (t, nid) in present:
                continue
            row = rows_by_target[t][nid]
            assert row["status"] == "ready", (nid, row["status"])
            e = {**template, "node_id": nid, "target_id": t, "status": "ready", "cause": None,
                 "needs": "proof", "claimable": True, "origin": row["origin"],
                 "statement_hash": row["statement_hash"], "relation": row["relation"],
                 "tags": {"deps": row["deps"], "library": template["tags"]["library"]},
                 "attempts": 0, "failure_class_histogram": {}, "refuted_route_classes": [],
                 "claims": {"active": [], "history_count": 0}, "annex_present": False,
                 "ready_since": "2026-10-08T12:00:00Z", "circular": entries,
                 "literature": None, "literature_proposed": None, "tutorial": False, "dormant": False, "bounty": False}
            f["entries"].append(e)
            added.append(nid)
    f["entries"].sort(key=lambda e: (e["target_id"], e["node_id"]))
    fp.write_text(json.dumps(schemas.validate(f, "frontier/v5"), indent=1, sort_keys=True) + "\n")
    print("frontier/v5: entries", len(f["entries"]), "claimable", sum(1 for e in f["entries"] if e["claimable"]), "added", added)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
