"""F08-T27 (2 of 3; Q38, F18-R2): the products say what each merged proof used.

``graph.json`` carried each node's *declared* dependencies and nothing else, so a closure could
only follow what a node declared: erdos-1050's ``h1-v2`` declares four holes and its proof term
names one, and the digestion closure and the problem page both counted all four. Each node now
lists its merged proofs — ``Proof.lean`` first, then its alternates (D-25 v3.13) — each with the
nodes its proof term rests on, read from the attestation (``attestation/v6``'s footprint) or, for
a merge attested before v6, from ``.footprint-cache.json``. Neither is ``None``: not measured.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness import TARGET, copy_graph
from test_products import MERGE, ROOT_NODE, attest, nodes_dir

from opn_gate import graph, products, schemas

A, B = "tutorial-and-swap", "and-reassoc"


def proved_interior(root: Path) -> None:
    attest(root, A, n=1, footprint={"nodes": []})
    attest(root, B, n=2, footprint={"nodes": []})


def proof_hash(root: Path, node_id: str) -> str:
    return schemas.content_hash((nodes_dir(root) / node_id / "Proof.lean").read_bytes())


def graph_row(root: Path, node_id: str) -> dict[str, Any]:
    tg = graph.load_target(root, TARGET)
    doc = schemas.validate(products.graph_doc(tg, None), products.GRAPH_SCHEMA)
    [row] = [n for n in doc["nodes"] if n["node_id"] == node_id]
    return dict(row)


def test_a_proof_lists_the_nodes_its_term_used_not_the_ones_it_declared(tmp_path: Path) -> None:
    """The erdos-1050 shape: the root declares two deps and its attestation's footprint is one."""
    root = copy_graph(tmp_path, publish=True)
    proved_interior(root)
    attest(
        root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint={"nodes": [A]}
    )
    row = graph_row(root, ROOT_NODE)
    assert row["deps"] == [A, B]  # what it declared, unchanged
    assert row["proofs"] == [
        {
            "kind": "proof",
            "path": "Proof.lean",
            "artifact_hash": proof_hash(root, ROOT_NODE),
            "attestation": "000003.json",
            "merge_commit": MERGE,
            "submitter": None,
            "used": [A],
        }
    ]
    assert row["uses"] == []


def test_an_attestation_before_v6_is_read_from_the_footprint_cache(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    proved_interior(root)
    attest(root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), schema="attestation/v5")
    att = root / "attestations" / "000003.json"
    old = json.loads(att.read_text())
    del old["footprint"]
    att.write_bytes(schemas.canonical_json(old))
    cache = root / "targets" / TARGET / graph.FOOTPRINT_CACHE
    cache.write_bytes(schemas.canonical_json({proof_hash(root, ROOT_NODE): [B]}))
    assert graph_row(root, ROOT_NODE)["proofs"][0]["used"] == [B]


def test_a_proof_measured_nowhere_says_so(tmp_path: Path) -> None:
    """Not measured is ``None``: never the declared deps, never empty (C7)."""
    root = copy_graph(tmp_path, publish=True)
    proved_interior(root)
    attest(root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint=None)
    assert graph_row(root, ROOT_NODE)["proofs"][0]["used"] is None


def test_an_alternate_is_listed_after_the_proof_with_its_own_footprint(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    proved_interior(root)
    attest(
        root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint={"nodes": [A]}
    )
    alt = nodes_dir(root) / ROOT_NODE / "attempts" / "20260930T120000Z-bob-alternate.lean"
    alt.parent.mkdir(exist_ok=True)
    alt.write_text("-- a second proof\n", encoding="utf-8")
    alt_hash = schemas.content_hash(alt.read_bytes())
    attest(
        root, ROOT_NODE, n=4, artifact_hash=alt_hash, submitter="bob", footprint={"nodes": [A, B]}
    )
    proofs = graph_row(root, ROOT_NODE)["proofs"]
    assert [(p["kind"], p["path"], p["used"], p["submitter"]) for p in proofs] == [
        ("proof", "Proof.lean", [A], None),
        ("alternate", "attempts/20260930T120000Z-bob-alternate.lean", sorted([A, B]), "bob"),
    ]


def test_an_open_node_lists_no_proofs(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    assert graph_row(root, ROOT_NODE)["proofs"] == []


def test_the_closure_follows_what_was_used(tmp_path: Path) -> None:
    """Q38: the digestion closure of a proof that used one of two deps holds the one."""
    root = copy_graph(tmp_path, publish=True)
    proved_interior(root)
    attest(
        root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint={"nodes": [A]}
    )
    tg = graph.load_target(root, TARGET)
    assert products.dependency_closure(tg, ROOT_NODE) == sorted([ROOT_NODE, A])


def test_an_unmeasured_proof_is_closed_over_its_declared_deps(tmp_path: Path) -> None:
    """Where the record cannot say, the closure says the most it could rest on, never less."""
    root = copy_graph(tmp_path, publish=True)
    proved_interior(root)
    attest(root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint=None)
    tg = graph.load_target(root, TARGET)
    assert products.dependency_closure(tg, ROOT_NODE) == sorted([ROOT_NODE, A, B])


def test_the_graph_product_is_the_next_version() -> None:
    """T27 made it graph/v4; F08-T36 (D-16 v3.28, every defect claim) took the next one; F08-T39
    (D-12 v3.35, the circular label and the literature status) the one after."""
    assert products.GRAPH_SCHEMA == "graph/v6"
