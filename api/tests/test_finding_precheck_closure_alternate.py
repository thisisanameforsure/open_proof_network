"""F28-T11 (bug B5, the 2026-11-19 agent run; D-12 v3.42, D-25 v3.13): precheck says when the
closure sweep has closed, or will close, the node a proof is offered for.

Live: an agent proved the parent's last hole (graph #1508) and then prechecked and submitted the
parent's assembly as its ``Proof.lean`` (#1519), because the guide told it to. The post-merge
sweep had already proved the parent by ``closure.json``, so the file could only land as an
alternate, and nothing the agent read said so. The owner's ruling: a node proved by closure counts
as proved; precheck says the sweep has closed (or will close) the node, and that the file lands as
an alternate. A note, never a refusal: the job is accepted as before.
"""

from __future__ import annotations

import json
from typing import Any

from api_fakes import PROOF_PREFIX, TUTORIAL_PROOF, Harness

GRAPH_JSON = "targets/propositional/graph.json"
CLOSED = "and-reassoc"
OTHER = "listed-only"


def rows(h: Harness) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    doc: dict[str, Any] = json.loads(h.githost.files[GRAPH_JSON])
    return doc, {str(n["node_id"]): n for n in doc["nodes"]}


def commit(h: Harness, doc: dict[str, Any]) -> None:
    h.githost.files[GRAPH_JSON] = json.dumps(doc).encode("utf-8")
    h.context.files.pop(GRAPH_JSON, None)


def precheck(h: Harness, token: str, node: str, file: str = "Proof.lean") -> dict[str, Any]:
    created = h.client.post(
        "/precheck",
        json={"node_id": node, "bundle": {f"{PROOF_PREFIX}{node}/{file}": TUTORIAL_PROOF}},
        headers=h.auth(token),
    )
    assert created.status_code == 202, created.text  # a note, never a refusal
    body: dict[str, Any] = created.json()
    return body


def test_a_proof_for_a_node_the_sweep_closed_is_told_it_lands_as_an_alternate(
    harness: Harness,
) -> None:
    """The row as the products publish a node the sweep closed: proved, a closure object, a proof
    commit (the partial's merge), and no ``Proof.lean`` among its proofs."""
    token = harness.token_for("code_alice", "alice")
    doc, by_id = rows(harness)
    by_id[CLOSED].update(
        status="proved",
        proof_commit="8" * 40,
        closure={
            "kind": "route",
            "id": f"{CLOSED}@1",
            "inputs": ["already-proved"],
            "record": f"{CLOSED}/closure.json",
        },
        proofs=[],
    )
    commit(harness, doc)
    note = precheck(harness, token, CLOSED).get("closure")
    assert note is not None, "no closure note on a node the sweep proved"
    assert note["state"] == "closed" and note["node_id"] == CLOSED
    assert note["link"] == {"kind": "route", "id": f"{CLOSED}@1", "inputs": ["already-proved"]}
    assert "attempts/<ts>-<pseudonym>-alternate.lean" in note["message"]

    # And an alternate offered for it is told the same, since that is where it is going.
    again = precheck(harness, token, CLOSED, "attempts/20261119T120000Z-alice-alternate.lean")
    assert again.get("closure", {}).get("state") == "closed"


def test_a_proof_for_a_node_the_sweep_will_close_is_told_so(harness: Harness) -> None:
    """``closing.closable`` names the node: its one route's only hole is proved, so the next
    sweep proves it, and a ``Proof.lean`` merged after that lands as an alternate."""
    token = harness.token_for("code_alice", "alice")
    doc, by_id = rows(harness)
    by_id[CLOSED]["decompositions"] = [
        {"partial": "attempts/20261118T120000Z-alice-partial.lean",
         "holes": [{"name": "h1", "node": "already-proved"}]},
    ]  # fmt: skip
    commit(harness, doc)
    note = precheck(harness, token, CLOSED).get("closure")
    assert note is not None, "no closure note on a node closing.closable names"
    assert note["state"] == "closable" and note["ready"] is True
    assert note["link"]["id"] == f"{CLOSED}@1"
    assert "alternate" in note["message"]


def test_no_note_where_no_closure_is_in_reach(harness: Harness) -> None:
    """A plain open node, and a node proved by a merged ``Proof.lean``, carry no note."""
    token = harness.token_for("code_alice", "alice")
    assert "closure" not in precheck(harness, token, OTHER)
    doc, by_id = rows(harness)
    by_id[CLOSED].update(
        status="proved",
        proof_commit="8" * 40,
        proofs=[{"kind": "proof", "path": "Proof.lean"}],
        closure=None,
    )
    commit(harness, doc)
    assert "closure" not in precheck(
        harness, token, CLOSED, "attempts/20261119T120000Z-a-alternate.lean"
    )
