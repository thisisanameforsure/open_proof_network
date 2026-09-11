"""F09-T2 / AC7: list_frontier filters by equality or containment, in file order, no ranking."""

from __future__ import annotations

import json
from typing import Any

from api_fakes import Harness
from mcp_client import McpClient

from opn_api.mcp import reads


def entry(node_id: str, **overrides: Any) -> dict[str, Any]:
    out: dict[str, Any] = json.loads(json.dumps(json.loads(open_fixture())["entries"][0]))
    out["node_id"] = node_id
    out["statement_hash"] = "".join(c if c in "0123456789abcdef" else "a" for c in node_id * 64)[
        :64
    ]
    for key, value in overrides.items():
        head, _, tail = key.partition("__")
        if tail:
            out[head][tail] = value
        else:
            out[key] = value
    return out


def open_fixture() -> str:
    from api_fakes import FIXTURES  # noqa: PLC0415

    return (FIXTURES / "frontier.json").read_text()


def commit_frontier(harness: Harness, entries: list[dict[str, Any]]) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(open_fixture())
    doc["entries"] = entries
    harness.githost.files["frontier.json"] = json.dumps(doc).encode()
    harness.context.files.clear()
    return doc


def test_filters_no_ranking(harness: Harness) -> None:
    """AC7: {origin: authored, tags.library contains "Nat"} returns only the matching entries,
    in the file's order — the second match listed after the first however it scores."""
    commit_frontier(
        harness,
        [
            entry("z-nat-first", origin="authored", tags__library=["Nat", "Int"], attempts=9),
            entry("variant-nat", origin="variant", tags__library=["Nat"]),
            entry("a-real", origin="authored", tags__library=["Real"]),
            entry("b-nat-second", origin="authored", tags__library=["Nat"], attempts=0),
        ],
    )
    client = McpClient(harness)
    doc = client.ok("list_frontier", {"filters": {"origin": "authored", "tags.library": "Nat"}})
    assert [e["node_id"] for e in doc["entries"]] == ["z-nat-first", "b-nat-second"]
    assert doc["schema"] == "frontier/v1"
    # Equality on a list field is containment; equality on a scalar is equality; both compose.
    assert [
        e["node_id"] for e in client.ok("list_frontier", {"filters": {"attempts": 0}})["entries"]
    ] == ["b-nat-second"]
    assert client.ok("list_frontier", {"filters": {"origin": "speculative"}})["entries"] == []


def test_no_filters_is_the_overlay(harness: Harness) -> None:
    """R5: the unfiltered result is GET /frontier.json — claims overlaid, nothing else touched."""
    token = harness.token_for("code_alice", "alice-p")
    harness.client.post("/claims", json={"node_id": "and-reassoc"}, headers=harness.auth(token))
    served = harness.client.get("/frontier.json").json()
    assert McpClient(harness).ok("list_frontier") == served
    assert McpClient(harness).ok("list_frontier", {"filters": {}}) == served
    by_node = {e["node_id"]: e for e in served["entries"]}
    assert by_node["and-reassoc"]["claims"]["active"][0]["pseudonym"] == "alice-p"


def test_unknown_filter_named(harness: Harness) -> None:
    """C7: a filter on a field the frontier schema does not have is refused by name, never an
    empty answer that looks like "no such node"."""
    doc = McpClient(harness).failed("list_frontier", {"filters": {"score": 1, "tags.libary": "x"}})
    assert doc["error"] == "filter-unknown"
    assert doc["source"] == "adapter"
    assert "score" in doc["message"] and "tags.libary" in doc["message"]
    assert "node_id" in doc["message"]  # the known fields are listed
    assert reads.matches(
        {"tags": {"library": ["Nat"]}, "origin": "authored"}, {"tags.library": "Nat"}
    )
    assert not reads.matches({"tags": {"library": []}}, {"tags.library": "Nat"})
    assert not reads.matches(
        {"origin": "authored"}, {"tags.library": "Nat"}
    )  # missing field: no match
