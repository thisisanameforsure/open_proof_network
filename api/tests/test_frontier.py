"""F05-T3: the overlay and the snapshot (R9; AC15)."""

from __future__ import annotations

import json
import time

from api_fakes import Harness

from opn_gate import schemas


def force_stale(harness: Harness, rel: str = "frontier.json") -> None:
    """Age a cached file past the window, whatever the monotonic clock's origin is.

    Setting the epoch to 0.0 is not enough: `time.monotonic()` counts from boot on Linux, so on
    a freshly started CI runner "0.0 seconds ago" is still inside the 60-second window and the
    cache is never revalidated. Subtracting the window from *now* is true on any machine.
    """
    window = harness.settings.frontier_max_stale_s
    harness.context.files[rel].fetched_at = time.monotonic() - (window + 1)


def test_overlay_only_touches_claims(harness: Harness) -> None:
    """AC15: the served frontier validates and differs from the committed file only in claims."""
    alice = harness.token_for("code_alice", "alice-p")
    bob = harness.token_for("code_bob", "bob-p")
    harness.client.post("/claims", json={"node_id": "and-reassoc"}, headers=harness.auth(alice))
    harness.client.post(
        "/claims", json={"node_id": "tutorial-and-swap", "ttl_hours": 5}, headers=harness.auth(bob)
    )

    r = harness.client.get("/frontier.json")
    assert r.status_code == 200
    served = r.json()
    assert schemas.violations(served, "frontier/v1") == []

    committed = json.loads(harness.githost.files["frontier.json"].decode())
    assert [e["node_id"] for e in served["entries"]] == [e["node_id"] for e in committed["entries"]]
    for got, was in zip(served["entries"], committed["entries"], strict=True):
        assert {k: v for k, v in got.items() if k != "claims"} == {
            k: v for k, v in was.items() if k != "claims"
        }
        assert was["claims"] == {"active": [], "history_count": 0}
    by_node = {e["node_id"]: e["claims"] for e in served["entries"]}
    assert by_node["and-reassoc"]["active"] == [
        {"pseudonym": "alice-p", "expires": "2026-09-09T13:00:00Z"}
    ]
    assert by_node["tutorial-and-swap"]["active"][0]["pseudonym"] == "bob-p"
    assert by_node["listed-only"] == {"active": [], "history_count": 0}
    assert {k: v for k, v in served.items() if k != "entries"} == {
        k: v for k, v in committed.items() if k != "entries"
    }


def test_claims_json_is_the_registry_alone(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    harness.client.post("/claims", json={"node_id": "and-reassoc"}, headers=harness.auth(token))
    doc = harness.client.get("/claims.json").json()
    assert schemas.violations(doc, "claims/v1") == []
    assert doc["snapshot_at"] == "2026-09-09T12:00:00Z"
    assert doc["nodes"] == {
        "and-reassoc": {
            "active": [{"pseudonym": "alice-p", "expires": "2026-09-09T13:00:00Z"}],
            "history_count": 1,
        }
    }


def test_committed_file_is_cached_and_revalidated(harness: Harness) -> None:
    """R9: at most 60 s stale, then an ETag revalidation rather than a refetch."""
    harness.client.get("/frontier.json")
    assert harness.githost.fetches == [("frontier.json", None)]
    harness.client.get("/frontier.json")
    assert len(harness.githost.fetches) == 1  # inside the window: no call at all

    harness.clock.advance(seconds=61)  # the cache window is wall clock, so force it directly
    force_stale(harness)
    harness.client.get("/frontier.json")
    assert len(harness.githost.fetches) == 2
    assert harness.githost.fetches[1][1] is not None  # If-None-Match carried the ETag


def test_unreachable_graph_serves_the_last_good_copy(harness: Harness) -> None:
    """C7: a fetch failure degrades to the cached file, and to 503 when there is none."""
    assert harness.client.get("/frontier.json").status_code == 200
    harness.githost.unreachable = True
    force_stale(harness)
    assert harness.client.get("/frontier.json").status_code == 200

    harness.context.files.clear()
    down = harness.client.get("/frontier.json")
    assert down.status_code == 503
    assert down.json()["error"] == "graph-unreachable"
