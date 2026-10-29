"""A claim on a proved node is released (F05-R8; the owner, 2026-10-28: "it should be released
after proven").

The story. On erdos-68 (2026-10-28) agent B's claims on ``erdos-68--h1`` and ``--h2`` were still
listed active an hour and twenty minutes after both proofs merged: a claim lived until its TTL ran
out whatever happened to its node. It went on counting against the holder's active-claims cap,
appearing in ``GET /claims/mine``, naming the holder in other receipts' ``others``, and reaching
the public registry (``claims.json``, which the graph renders through the claims URL).

The rule. Lazy, like expiry: a claim whose node the target's committed ``graph.json`` calls
``proved`` counts as released wherever it is read, and nothing is written to the store. Like an
expired claim it simply stops being listed; its ``released`` stays null, and ``history_count``
still counts it. Only ``proved`` releases: a blocked, shelved, abandoned or superseded node keeps
its claims until they expire, as before. The graph is read once per target per request through
the committed-file cache, never once per claim; a graph that cannot be read releases nothing (C7).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from test_store_seam import dynamo

from opn_api import claims as claimsmod
from opn_api import frontier
from opn_api.store import MemoryStore

NODE = "and-reassoc"
OTHER = "tutorial-and-swap"
TARGET = "propositional"
GRAPH = f"targets/{TARGET}/graph.json"


@pytest.fixture(params=["memory", "dynamodb"])
def h(request: pytest.FixtureRequest) -> Iterator[Harness]:
    store = MemoryStore() if request.param == "memory" else dynamo()
    harness = make_harness(store=store)
    with harness.client:
        yield harness


def claim(h: Harness, token: str, node: str = NODE, **body: object) -> dict[str, Any]:
    r = h.client.post("/claims", json={"node_id": node, **body}, headers=h.auth(token))
    assert r.status_code == 201, r.text
    doc: dict[str, Any] = r.json()
    return doc


def settle(h: Harness, node: str, status: str = "proved", **row: Any) -> None:
    """The graph's ``main`` moves: ``node`` takes ``status`` in ``graph.json`` and leaves the
    frontier, as a merge and its post-merge render leave it; the service's cache sees the move."""
    graph = json.loads(h.githost.files[GRAPH])
    for n in graph["nodes"]:
        if n["node_id"] == node:
            n["status"] = status
            n.update(row)
    h.githost.files[GRAPH] = json.dumps(graph).encode()
    front = json.loads(h.githost.files["frontier.json"])
    front["entries"] = [e for e in front["entries"] if e["node_id"] != node]
    h.githost.files["frontier.json"] = json.dumps(front).encode()
    frontier.expire(h.context)


def mine_nodes(h: Harness, token: str) -> list[str]:
    r = h.client.get("/claims/mine", headers=h.auth(token))
    assert r.status_code == 200, r.text
    return [c["node_id"] for c in r.json()["claims"]]


def registry_node(h: Harness, node: str) -> dict[str, Any]:
    r = h.client.get("/claims.json")
    assert r.status_code == 200, r.text
    got: dict[str, Any] = r.json()["nodes"].get(node, {"active": [], "history_count": 0})
    return got


def test_mine_leaves_out_a_claim_whose_node_is_proved(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    claim(h, alice, ttl_hours=24)
    claim(h, alice, OTHER, ttl_hours=24)
    assert sorted(mine_nodes(h, alice)) == sorted([NODE, OTHER])
    settle(h, NODE)
    assert mine_nodes(h, alice) == [OTHER]


def test_the_registry_drops_a_proved_nodes_claims_and_keeps_their_history(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    bob = h.token_for("code_bob", "bob-p")
    claim(h, alice, ttl_hours=24)
    claim(h, bob, ttl_hours=24)
    assert len(registry_node(h, NODE)["active"]) == 2
    settle(h, NODE)
    assert registry_node(h, NODE) == {"active": [], "history_count": 2}


def test_a_proved_claim_no_longer_counts_against_the_cap() -> None:
    h = make_harness(env={"OPN_API_ACTIVE_CLAIMS": "1"})
    with h.client:
        alice = h.token_for("code_alice", "alice-p")
        claim(h, alice, ttl_hours=24)
        refused = h.client.post("/claims", json={"node_id": OTHER}, headers=h.auth(alice))
        assert refused.status_code == 429, refused.text
        settle(h, NODE)
        claim(h, alice, OTHER)


def test_others_never_names_the_holder_of_a_claim_on_a_proved_node(h: Harness) -> None:
    """``others`` is read from the store (Q15). A receipt for a proved node is not normally
    served, so the function is driven directly over the stored claims."""
    alice = h.token_for("code_alice", "alice-p")
    bob = h.token_for("code_bob", "bob-p")
    mine = claim(h, alice, ttl_hours=24)
    theirs = claim(h, bob, ttl_hours=24)
    assert [o["pseudonym"] for o in theirs["others"]] == ["alice-p"]
    settle(h, NODE)
    stored = h.store.list_claims()
    held = next(c for c in stored if c.id == mine["id"])
    assert claimsmod.others(h.context, held, stored) == []


def test_reading_a_proved_claim_writes_nothing(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    made = claim(h, alice, ttl_hours=24)
    settle(h, NODE)
    mine_nodes(h, alice)
    registry_node(h, NODE)
    h.client.get("/frontier.json")
    stored = h.store.get_claim(made["id"])
    assert stored is not None and stored.released is None


@pytest.mark.parametrize(
    ("status", "row"),
    [
        ("blocked", {"cause": None}),
        ("abandoned", {}),
        ("superseded", {}),
        (
            "ready",
            {
                "shelved": {
                    "cause": "does-not-serve-root",
                    "by": "steward-p",
                    "date": "2026-10-28",
                    "record": "shelvings/1.yaml",
                    "scope": "node",
                    "from": NODE,
                }
            },
        ),
    ],
    ids=["blocked", "abandoned", "superseded", "shelved"],
)
def test_only_proved_releases_a_claim(h: Harness, status: str, row: dict[str, Any]) -> None:
    alice = h.token_for("code_alice", "alice-p")
    claim(h, alice, ttl_hours=24)
    settle(h, NODE, status, **row)
    assert mine_nodes(h, alice) == [NODE]
    assert len(registry_node(h, NODE)["active"]) == 1


def test_a_graph_that_cannot_be_read_releases_nothing(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    claim(h, alice, ttl_hours=24)
    del h.githost.files[GRAPH]
    h.context.files.pop(GRAPH, None)
    frontier.expire(h.context)
    assert mine_nodes(h, alice) == [NODE]
    assert len(registry_node(h, NODE)["active"]) == 1


def test_the_graph_is_read_once_per_target_not_once_per_claim(h: Harness) -> None:
    tokens = [h.token_for("code_alice", "alice-p"), h.token_for("code_bob", "bob-p")]
    for token in tokens:
        claim(h, token, ttl_hours=24)
        claim(h, token, OTHER, ttl_hours=24)
    frontier.expire(h.context)
    h.githost.fetches.clear()
    assert len(registry_node(h, NODE)["active"]) == 2
    assert [p for p, _ in h.githost.fetches].count(GRAPH) == 1
