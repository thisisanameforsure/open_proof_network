"""F09-T72 (decisions v3.38, D-12; testers 2026-10-09b, C1): a lemma is legible through the MCP.

A hole that restates a node under another branch of the target makes that node a *lemma* of
the parent: META's ``lemmas`` (meta/v6), the parent's ``CONTEXT.json`` ``lemmas`` (context/v6),
``graph.json``'s row and a decomposition's hole resolving to the lemma's node (graph/v8). The
agent of C1 could see none of it: ``get_node`` served a bundle that said nothing, and
``get_submission`` on the merged partial said "pass" and nothing of what the post-merge job did.

Now ``get_node`` carries ``lemmas`` (the bundle's, ``[]`` for a document older than v6) and
``get_submission`` on a partial carries its holes with ``became``, the node each hole became
as the products record it, read from ``graph.json`` at main's sha (F05-T30); null until the
products carry the decomposition. The v6 and v7 documents here are hand-written to the committed
schemas and checked against them, never regenerated fixtures (the gate agent's).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import samples
from api_fakes import (
    FIXTURES,
    TUTORIAL_NODE,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_precheck_key,
)
from mcp_client import NODE, NODE_DIR, TARGET, McpClient
from test_appends import post, postmortem
from test_finding_hole_child_pending import CHILD, EXISTING, submitted_partial
from test_finding_partial_witnesses import PARTIAL_PATH, STEM
from test_mcp_equivalence import derived_bundle, seed_graph

from opn_api.mcp import reads, results
from opn_api.mcp.server import TOOLS
from opn_gate import review as review_mod
from opn_gate import schemas

LEMMA_NODE = "already-proved"
LEMMA = {
    "node_id": LEMMA_NODE,
    "hole": "h_good",
    "status": "proved",
    "statement_hash": "6" * 64,
    "signature": "theorem OpnProp.good : True := by\n  sorry\n",
    "cause": None,
}


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


@pytest.fixture(autouse=True)
def _accept_v6(monkeypatch: pytest.MonkeyPatch) -> None:
    """The products task adds ``context/v6`` to ``reads.CONTEXT_SCHEMAS`` (and the gate's
    ``context.ACCEPTED``); until that lands beside this, the service is told here, which is a
    no-op once it has."""
    accepted = tuple(dict.fromkeys((*reads.CONTEXT_SCHEMAS, "context/v6")))
    monkeypatch.setattr(reads, "CONTEXT_SCHEMAS", accepted)


# --- get_node -------------------------------------------------------------------------------------


def context_v6(harness: Harness, tree: Path, lemmas: list[dict[str, Any]]) -> dict[str, Any]:
    """The fixture node's derived bundle lifted to context/v6 by hand, carrying ``lemmas``."""
    derived = derived_bundle(harness, tree)
    v6 = {**derived, "schema": "context/v6", "lemmas": lemmas}
    v6.pop("review", None)  # F26-T1: context/v7 added it; a v6 snapshot has none
    for field, value in (("circular", []), ("literature", None), ("literature_proposed", None)):
        v6.setdefault(field, value)
    assert schemas.violations(v6, "context/v6") == [], "the hand-written v6 is not v6"
    return v6


def commit_context(harness: Harness, doc: dict[str, Any]) -> None:
    harness.githost.files[NODE_DIR + "CONTEXT.json"] = schemas.canonical_json(doc)
    harness.context.files.clear()


def test_get_node_carries_the_bundles_lemmas(harness: Harness, tmp_path: Path) -> None:
    """A node whose merged partial restated ``already-proved`` under another branch: the lemma,
    with its signature and status, is in the answer where an agent reads what a proof may use."""
    seed_graph(harness)
    commit_context(harness, context_v6(harness, tmp_path / "tree", [LEMMA]))
    served = McpClient(harness).ok("get_node", {"node_id": NODE, "include": []})
    assert served["context_source"] == "file"
    assert served["context"]["schema"] == "context/v6"
    assert served["lemmas"] == [LEMMA]
    assert served["lemmas"][0]["signature"] == LEMMA["signature"]
    assert served["lemmas"][0]["status"] == "proved"
    assert results.violations("get_node", served) == []


def test_get_node_on_an_older_context_answers_no_lemmas(harness: Harness, tmp_path: Path) -> None:
    """A graph rendered before the v3.38 re-pin commits context/v5, which has no ``lemmas``
    key: the answer says ``[]``, never a KeyError (the deploy-window rule of 2026-09-11)."""
    seed_graph(harness)
    v5 = {**derived_bundle(harness, tmp_path / "tree"), "schema": "context/v5"}
    v5.pop("lemmas", None)
    v5.pop("review", None)  # F26-T1: context/v7 added it
    for field, value in (("circular", []), ("literature", None), ("literature_proposed", None)):
        v5.setdefault(field, value)
    assert schemas.violations(v5, "context/v5") == [], "the hand-written v5 is not v5"
    commit_context(harness, v5)
    served = McpClient(harness).ok("get_node", {"node_id": NODE, "include": []})
    assert served["context"]["schema"] == "context/v5"
    assert served["lemmas"] == []
    assert results.violations("get_node", served) == []


def test_get_node_lemmas_equal_the_plain_path(harness: Harness, tmp_path: Path) -> None:
    """D-28: the tool's ``lemmas`` is exactly the committed ``CONTEXT.json``'s list."""
    seed_graph(harness)
    commit_context(harness, context_v6(harness, tmp_path / "tree", [LEMMA]))
    served = McpClient(harness).ok("get_node", {"node_id": NODE, "include": []})
    committed = json.loads(harness.githost.files[NODE_DIR + "CONTEXT.json"])
    assert served["lemmas"] == committed["lemmas"]


def test_the_tool_and_schema_name_lemmas() -> None:
    tool = next(t for t in TOOLS if t.name == "get_node")
    assert "lemmas" in tool.description
    declared = results.load("get_node")["oneOf"][0]
    assert "lemmas" in declared["properties"]
    assert "lemmas" in declared["required"]
    assert "context/v6" in declared["properties"]["context"]["properties"]["schema"]["enum"]


# --- get_submission ------------------------------------------------------------------------------


def graph_v7(decompositions: list[dict[str, Any]], lemmas: list[dict[str, str]]) -> dict[str, Any]:
    """The fixture's graph/v1 lifted to graph/v8 by hand: every row with v8's fields, the
    tutorial node carrying the merged partial's decomposition and its lemma."""
    doc: dict[str, Any] = json.loads((FIXTURES / "graph.json").read_text())
    doc["schema"] = "graph/v9"
    doc["review"] = review_mod.state_of(Path("/nonexistent"))  # F26-T1: no review
    doc["open_pairs"] = []
    doc["target_proofs"] = []
    doc["registrations"] = []  # F25-T1 (graph/v7): the target's registrations, none here
    for row in doc["nodes"]:
        row.update(
            cause=None,
            relevance=None,
            uses=[],
            proofs=[],
            decompositions=[],
            proposed_for=None,
            outline=None,
            defect_claims=[],
            circular=[],
            literature=None,
            literature_proposed=None,
            lemmas=[],
        )
        if row["node_id"] == TUTORIAL_NODE:
            row["decompositions"] = decompositions
            row["lemmas"] = lemmas
    assert schemas.violations(doc, "graph/v9") == [], "the hand-written v9 is not v9"
    return doc


def serve_products(
    harness: Harness, doc: dict[str, Any], pr_number: int, merged_file: str = TUTORIAL_PROOF
) -> None:
    """What the post-merge job's bot commit leaves on main for a merged partial: the products,
    its attestation naming the artifact's hash, and the merged file itself."""
    harness.githost.files[f"targets/{TARGET}/graph.json"] = json.dumps(doc).encode()
    harness.githost.files[f"attestations/{pr_number:06d}.json"] = json.dumps(
        samples.attestation(
            node_id=TUTORIAL_NODE,
            artifact_hash=schemas.content_hash(TUTORIAL_PROOF.encode()),
        )
    ).encode()
    harness.githost.files[PARTIAL_PATH] = merged_file.encode()
    harness.context.files.clear()


DECOMPOSITION = {
    "partial": f"attempts/{STEM}.lean",
    "annex": None,
    "holes": [{"name": "left", "node": CHILD}, {"name": "right", "node": EXISTING}],
}


def test_get_submission_on_a_merged_partial_says_what_each_hole_became(
    harness: Harness, key: PrecheckKey
) -> None:
    """The partial's ``right`` hole restated ``already-proved`` under another branch; once the
    products carry the decomposition, the submission says the hole became that node, the lemma,
    and ``left`` became the new child."""
    receipt = submitted_partial(harness, key)
    harness.githost.set_pull_request_state(receipt["pr_number"], state="closed", merged=True)
    serve_products(
        harness,
        graph_v7([DECOMPOSITION], [{"hole": "right", "node": EXISTING}]),
        receipt["pr_number"],
    )
    r = harness.client.get(f"/submissions/{receipt['submission_id']}")
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["state"] == "merged"
    assert doc["holes"] == [
        {"name": "left", "expected_node_id": CHILD, "expected_new": True, "became": CHILD},
        {"name": "right", "expected_node_id": EXISTING, "expected_new": False, "became": EXISTING},
    ]
    assert "lemma" in doc["holes_note"]


def test_became_is_null_until_the_products_carry_the_decomposition(
    harness: Harness, key: PrecheckKey
) -> None:
    receipt = submitted_partial(harness, key)
    harness.githost.set_pull_request_state(receipt["pr_number"], state="closed", merged=True)
    serve_products(harness, graph_v7([], []), receipt["pr_number"])
    doc = harness.client.get(f"/submissions/{receipt['submission_id']}").json()
    assert [h["became"] for h in doc["holes"]] == [None, None]
    assert [h["name"] for h in doc["holes"]] == ["left", "right"]


def test_became_is_null_while_the_partial_is_open(harness: Harness, key: PrecheckKey) -> None:
    """Restatement is decided at the merge, by step 4 against the tree as it is then (C1)."""
    receipt = submitted_partial(harness, key)
    serve_products(
        harness,
        graph_v7([DECOMPOSITION], [{"hole": "right", "node": EXISTING}]),
        receipt["pr_number"],
    )
    doc = harness.client.get(f"/submissions/{receipt['submission_id']}").json()
    assert doc["state"] == "open"
    assert [h["became"] for h in doc["holes"]] == [None, None]


def test_a_later_decomposition_with_the_same_hole_names_is_not_this_ones(
    harness: Harness, key: PrecheckKey
) -> None:
    """Two partials of one node may share hole names; the one whose file hashes to this
    submission's attested artifact is read, and an unmatched decomposition leaves every hole
    null rather than guessing."""
    receipt = submitted_partial(harness, key)
    harness.githost.set_pull_request_state(receipt["pr_number"], state="closed", merged=True)
    other = {**DECOMPOSITION, "partial": "attempts/20260101T000000Z-bob-partial.lean"}
    serve_products(harness, graph_v7([other], []), receipt["pr_number"])
    harness.githost.files[f"targets/{TARGET}/nodes/{TUTORIAL_NODE}/{other['partial']}"] = (
        TUTORIAL_PROOF + "-- bob's own\n"
    ).encode()
    harness.context.files.clear()
    doc = harness.client.get(f"/submissions/{receipt['submission_id']}").json()
    assert [h["became"] for h in doc["holes"]] == [None, None]


def test_get_submission_tool_equals_the_route(harness: Harness, key: PrecheckKey) -> None:
    receipt = submitted_partial(harness, key)
    harness.githost.set_pull_request_state(receipt["pr_number"], state="closed", merged=True)
    serve_products(
        harness,
        graph_v7([DECOMPOSITION], [{"hole": "right", "node": EXISTING}]),
        receipt["pr_number"],
    )
    route = harness.client.get(f"/submissions/{receipt['submission_id']}").json()
    tool = McpClient(harness).ok("get_submission", {"submission_id": receipt["submission_id"]})
    assert tool["holes"] == route["holes"]
    assert tool["holes"][1]["became"] == EXISTING
    assert results.violations("get_submission", tool) == []


def test_a_submission_that_is_not_a_partial_carries_no_holes(harness: Harness) -> None:
    """The key is a partial's; a proof, an annex or a postmortem never carries it, as the
    receipt never does (F06-T15)."""
    token = harness.token_for("code_alice", "alice")
    r = post(harness, "/postmortems", token, {"node_id": TUTORIAL_NODE, "yaml": postmortem()})
    assert r.status_code == 201, r.text
    doc = harness.client.get(f"/submissions/{r.json()['pr_number']}").json()
    assert doc["state"] == "open"
    assert "holes" not in doc and "holes_note" not in doc
