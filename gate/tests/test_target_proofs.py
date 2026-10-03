"""F18-T1 (R1, R2; AC1-AC3): every way a target is proved, each with the nodes it rests on.

A target can be proved more than once — the root's ``Proof.lean``, its alternates (D-25 v3.13),
and each proved ``resolves`` variant (D-30) with its own — and until F18 no product said so: the
problem page drew one tree of declared dependencies for all of them. ``graph.json``'s
``target_proofs`` lists each proof in the record's order, the root's first, with ``closure``:
the node the proof is of and every node its term rests on, transitively, following at each node
its first proof's measured ``used`` (F08-T27) — or, where nothing measured it, its declared
dependencies, which the entry names as ``unmeasured``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import samples
import yaml
from harness import TARGET, copy_graph
from test_node_proofs import proof_hash
from test_products import ROOT_NODE, attest, nodes_dir

from opn_gate import graph, products, scaffold, schemas

A, B = "tutorial-and-swap", "and-reassoc"


def target_proofs(root: Path) -> list[dict[str, Any]]:
    tg = graph.load_target(root, TARGET)
    doc = schemas.validate(products.graph_doc(tg, None), products.GRAPH_SCHEMA)
    return list(doc["target_proofs"])


def resolves_variant(root: Path, node_id: str, n: int, submitter: str) -> None:
    """A proved ``resolves`` variant with no dependencies, attested as merge ``n``."""
    proposal = scaffold.Proposal(
        node_id=node_id,
        target_id=TARGET,
        statement=f"theorem OpnProp.{node_id.replace('-', '_')} : True := by\n  sorry\n",
        witness="theorem witness : True := trivial\n",
        author="proposer",
        origin="variant",
        relation="resolves",
        relation_proof="theorem relation : True := trivial\n",
        date="2026-09-12T00:00:00Z",
    )
    scaffold.validate(proposal)
    written = scaffold.write(nodes_dir(root), proposal)
    statement = (written / "Statement.lean").read_text(encoding="utf-8")
    (written / "Proof.lean").write_text(statement.replace("sorry", "trivial"), encoding="utf-8")
    attest(
        root,
        node_id,
        n=n,
        artifact_hash=proof_hash(root, node_id),
        submitter=submitter,
        footprint={"nodes": []},
    )
    status = root / "targets" / TARGET / "status"
    status.mkdir(exist_ok=True)
    (status / "2026-09-12-curator.yaml").write_text(
        yaml.safe_dump(samples.target_status(root=ROOT_NODE)), encoding="utf-8"
    )


def test_closure_follows_use_not_declaration(tmp_path: Path) -> None:
    """AC1, the erdos-1050 shape: the root declares A and B, its term uses A, and B is still
    open. The proof is the root and A; B is on the graph and not on the proof."""
    root = copy_graph(tmp_path, publish=True)
    attest(root, A, n=1, footprint={"nodes": []})
    attest(
        root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint={"nodes": [A]}
    )
    assert graph.load_target(root, TARGET).statuses[B] == "ready"  # open, as erdos-1050's h1
    [entry] = target_proofs(root)
    assert entry == {
        "node_id": ROOT_NODE,
        "relation": None,
        "kind": "proof",
        "path": "Proof.lean",
        "artifact_hash": proof_hash(root, ROOT_NODE),
        "merge_commit": entry["merge_commit"],
        "submitter": None,
        "closure": sorted([ROOT_NODE, A]),
        "unmeasured": [],
    }


def test_every_way_the_target_is_proved_is_listed_in_record_order(tmp_path: Path) -> None:
    """AC2, the euclid-primes shape: the root's proof, then each proved resolves variant by the
    order its merge was attested."""
    root = copy_graph(tmp_path, publish=True)
    attest(root, A, n=1, footprint={"nodes": []})
    attest(root, B, n=2, footprint={"nodes": []})
    attest(
        root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint={"nodes": [A, B]}
    )
    resolves_variant(root, "variant-later", 9, "carol")
    resolves_variant(root, "variant-earlier", 5, "dave")
    entries = target_proofs(root)
    assert [(e["node_id"], e["relation"], e["submitter"]) for e in entries] == [
        (ROOT_NODE, None, None),
        ("variant-earlier", "resolves", "dave"),
        ("variant-later", "resolves", "carol"),
    ]
    assert entries[0]["closure"] == sorted([ROOT_NODE, A, B])
    assert entries[1]["closure"] == ["variant-earlier"]


def test_an_alternate_of_the_root_is_its_own_entry_with_its_own_closure(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    attest(root, A, n=1, footprint={"nodes": []})
    attest(root, B, n=2, footprint={"nodes": []})
    attest(
        root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint={"nodes": [A]}
    )
    alt = nodes_dir(root) / ROOT_NODE / "attempts" / "20260930T120000Z-bob-alternate.lean"
    alt.parent.mkdir(exist_ok=True)
    alt.write_text("-- a second proof\n", encoding="utf-8")
    attest(
        root,
        ROOT_NODE,
        n=4,
        artifact_hash=schemas.content_hash(alt.read_bytes()),
        submitter="bob",
        footprint={"nodes": [B]},
    )
    entries = target_proofs(root)
    assert [(e["kind"], e["closure"]) for e in entries] == [
        ("proof", sorted([ROOT_NODE, A])),
        ("alternate", sorted([ROOT_NODE, B])),
    ]


def test_an_unmeasured_proof_says_so(tmp_path: Path) -> None:
    """AC3: with no footprint anywhere, the closure follows the declared dependencies and the
    entry names the node whose reading it could not have."""
    root = copy_graph(tmp_path, publish=True)
    attest(root, A, n=1, footprint={"nodes": []})
    attest(root, B, n=2, footprint=None)
    attest(root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint=None)
    [entry] = target_proofs(root)
    assert entry["closure"] == sorted([ROOT_NODE, A, B])
    assert entry["unmeasured"] == sorted([ROOT_NODE, B])


def test_an_open_target_lists_no_proofs(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    assert target_proofs(root) == []
