"""F05-T14 (Q15; ruling D3(b), 2026-09-24): ``GET /claims/mine`` and the ``list_my_claims`` tool.

The story. The same six agents of 2026-09-24 (finding 3,
``engineering/session-notes/2026-09-24-calibration-testers.md``): an agent that lost its claim
receipt (a restarted session, a context window that dropped it) had no way to find its own claim
ids again. ``claims.json`` and the frontier's overlay publish pseudonyms and expiry times only —
deliberately, since ``claims/v1`` is hash-pinned and public — so ``release_claim`` was unusable
without the receipt, and the claim sat in the overlay until it expired.

The owner's ruling D3: (b) a new authenticated route, ``GET /claims/mine``, listing the caller's
active claims with their ids, and an MCP ``list_my_claims`` tool whose plain path it is. Public
creation times stay deferred. The route answers ``401`` without a bearer, lists only the caller's
claims, and never an expired or released one.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from mcp_client import McpClient
from test_store_seam import dynamo

from opn_api.store import MemoryStore

NODE = "and-reassoc"
OTHER = "tutorial-and-swap"


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


def mine(h: Harness, token: str) -> Any:
    return h.client.get("/claims/mine", headers=h.auth(token))


def mine_ids(h: Harness, token: str) -> list[str]:
    r = mine(h, token)
    assert r.status_code == 200, r.text
    return [c["id"] for c in r.json()["claims"]]


@pytest.mark.xfail(strict=True, reason="F05-T14: no GET /claims/mine route")
def test_mine_lists_the_callers_active_claims_with_ids(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    bob = h.token_for("code_bob", "bob-p")
    first = claim(h, alice, ttl_hours=5)
    h.clock.advance(seconds=1)
    second = claim(h, alice, OTHER)
    claim(h, bob)
    r = mine(h, alice)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["pseudonym"] == "alice-p"
    assert [c["id"] for c in doc["claims"]] == [first["id"], second["id"]]
    listed = doc["claims"][0]
    for key in ("id", "node_id", "target_id", "pseudonym", "created", "expires", "released"):
        assert listed[key] == first[key], key
    assert listed.get("others") == [{"pseudonym": "bob-p", "expires": "2026-09-09T13:00:01Z"}]


@pytest.mark.xfail(strict=True, reason="F05-T14: no GET /claims/mine route")
def test_mine_leaves_out_released_and_expired_claims(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    released = claim(h, alice, OTHER)
    h.client.delete(f"/claims/{released['id']}", headers=h.auth(alice))
    kept = claim(h, alice, ttl_hours=3)
    assert mine_ids(h, alice) == [kept["id"]]
    h.clock.advance(hours=3, seconds=1)
    assert mine_ids(h, alice) == []


@pytest.mark.xfail(strict=True, reason="F05-T14: no GET /claims/mine route")
def test_mine_is_empty_for_someone_with_no_claims(h: Harness) -> None:
    claim(h, h.token_for("code_alice", "alice-p"))
    bob = h.token_for("code_bob", "bob-p")
    r = mine(h, bob)
    assert r.status_code == 200, r.text
    assert r.json()["claims"] == []


@pytest.mark.xfail(strict=True, reason="F05-T14: no GET /claims/mine route")
def test_mine_without_a_bearer_is_401() -> None:
    h = make_harness()
    r = h.client.get("/claims/mine")
    assert r.status_code == 401, r.text
    assert r.json()["error"] == "unauthenticated"
    bad = h.client.get("/claims/mine", headers=h.auth("not-a-token"))
    assert bad.status_code == 401


@pytest.mark.xfail(strict=True, reason="F05-T14: no GET /claims/mine route")
def test_the_route_is_in_the_table_as_an_authenticated_read() -> None:
    from opn_api import routes  # noqa: PLC0415

    spec = next((r for r in routes.ROUTES if r.label == "GET /claims/mine"), None)
    assert spec is not None, "GET /claims/mine is not in the routes table"
    assert spec.authenticated and not spec.write and spec.d35 is None


@pytest.mark.xfail(strict=True, reason="F05-T14: no list_my_claims tool")
def test_list_my_claims_over_mcp_equals_the_route() -> None:
    h = make_harness()
    alice = h.token_for("code_alice", "alice-p")
    claim(h, alice)
    client = McpClient(h)
    over_mcp = client.call("list_my_claims", {}, token=alice)
    assert not over_mcp.isError, over_mcp.structuredContent
    assert over_mcp.structuredContent == mine(h, alice).json()


@pytest.mark.xfail(strict=True, reason="F05-T14: no list_my_claims tool")
def test_list_my_claims_without_a_token_is_refused_before_the_route() -> None:
    h = make_harness()
    result = McpClient(h).call("list_my_claims", {})
    assert result.isError
    doc = result.structuredContent or {}
    assert doc.get("error") == "unauthenticated" and doc.get("status") == 401, doc
