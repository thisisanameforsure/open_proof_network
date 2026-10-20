"""F22-T9 (request H of the 2026-10-06 writers, W4 and R1; Q3, deferred until F09-T22 merged):
``get_node`` says what node a statement was proposed for, and which proofs of the target rest on it.

The story. A writer explaining a crux on erdos-1050 had to read the whole ``graph.json`` to learn
which node the crux was proposed for (F18-R8's ``proposed_for``, a pointer the problem page draws)
and whether any merged proof of the target actually uses it (F18-R1's ``target_proofs``, each with
the closure its proof term rests on). Both facts were on the record and neither was on the node's
own answer, so an agent writing words for a node could not say "this lemma is part of the proof"
without a second read and a search. ``get_node`` now carries ``proposed_for`` from the node's row
and ``in_closure``, each proof of the target whose closure contains the node, read from
``graph.json`` beside the labels (F29-R8), never from ``CONTEXT.json`` (its two builders must agree,
F10-Q7). A product rendered before the fields (graph/v7 for the pointer, graph/v6 for the proofs)
answers null and ``[]``, as the generator would with nothing on the record.

The third item of the request, a smaller answer, shipped as ``include`` (F09-T19, Q18): the
size it measured, 120k characters for erdos-1050's node, is 12k with ``include: []`` (F22-Q12).
"""

from __future__ import annotations

import json
from typing import Any

from api_fakes import Harness
from mcp_client import NODE, TARGET, McpClient, seed_node

from opn_api.mcp import results

HASH_A = "a" * 64
HASH_B = "b" * 64
COMMIT = "c" * 40


def proof(
    node_id: str, closure: list[str], artifact_hash: str, kind: str = "proof"
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "relation": None,
        "kind": kind,
        "path": "Proof.lean" if kind == "proof" else f"attempts/{artifact_hash[:8]}-alternate.lean",
        "artifact_hash": artifact_hash,
        "merge_commit": COMMIT,
        "submitter": "someone",
        "closure": sorted(closure),
        "unmeasured": [],
    }


def with_graph(harness: Harness, row: dict[str, Any], target_proofs: list[Any] | None) -> None:
    """The harness's committed ``graph.json`` with ``row`` on the fixture node and, unless
    ``None``, ``target_proofs`` at the top (absent, as on a product older than graph/v6)."""
    path = f"targets/{TARGET}/graph.json"
    graph = json.loads(harness.githost.files[path])
    for r in graph["nodes"]:
        if r["node_id"] == NODE:
            r.update(row)
    if target_proofs is None:
        graph.pop("target_proofs", None)
    else:
        graph["target_proofs"] = target_proofs
    harness.githost.files[path] = json.dumps(graph).encode()
    harness.context.files.clear()


def test_get_node_carries_proposed_for_and_the_proofs_whose_closure_holds_it(
    harness: Harness,
) -> None:
    seed_node(harness)
    uses_it = proof("the-root", ["the-root", NODE, "a-lemma"], HASH_A)
    alternate = proof("the-root", ["the-root", NODE], HASH_B, kind="alternate")
    without_it = proof("other-variant", ["other-variant", "a-lemma"], "d" * 64)
    with_graph(harness, {"proposed_for": "the-root"}, [uses_it, without_it, alternate])
    got = McpClient(harness).ok("get_node", {"node_id": NODE, "include": []})
    assert results.violations("get_node", got) == [], results.violations("get_node", got)
    assert got["proposed_for"] == "the-root"
    # every proof that rests on the node, in the record's order, identified as graph.json does
    assert got["in_closure"] == [
        {"node_id": "the-root", "kind": "proof", "path": "Proof.lean", "artifact_hash": HASH_A},
        {
            "node_id": "the-root",
            "kind": "alternate",
            "path": alternate["path"],
            "artifact_hash": HASH_B,
        },
    ]


def test_a_node_no_proof_rests_on_answers_an_empty_list(harness: Harness) -> None:
    seed_node(harness)
    with_graph(harness, {"proposed_for": None}, [proof("other", ["other"], HASH_A)])
    got = McpClient(harness).ok("get_node", {"node_id": NODE, "include": []})
    assert results.violations("get_node", got) == []
    assert got["proposed_for"] is None
    assert got["in_closure"] == []


def test_an_older_product_answers_null_and_empty(harness: Harness) -> None:
    """A graph rendered before graph/v6 has no ``target_proofs``, and a row before graph/v7 no
    ``proposed_for``: the answer says what the record says, nothing."""
    seed_node(harness)
    with_graph(harness, {}, None)
    got = McpClient(harness).ok("get_node", {"node_id": NODE, "include": []})
    assert results.violations("get_node", got) == []
    assert got["proposed_for"] is None and got["in_closure"] == []


def test_the_answer_moved_to_v3_and_v2_is_still_served(harness: Harness) -> None:
    assert results.schema_id("get_node") == "mcp/get_node/v3"
    client = McpClient(harness)
    for version in ("v3", "v2", "v1"):
        assert client.ok("get_schema", {"name": f"mcp/get_node/{version}"}) == results.load(
            "get_node", version
        )
