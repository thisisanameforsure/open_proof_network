"""F05-T20 (audit 2026-10-04): the claims registry scanned the whole claims table on every
anonymous read.

``frontier.registry`` called ``store.list_claims`` — a full DynamoDB ``Scan``, paged — for each
``GET /frontier.json`` and ``GET /claims.json``, so the cost of an anonymous poll grew with every
claim ever made (released and expired rows are kept: R9's ``history_count`` counts them).

The rule. The scan is kept on the ``Context`` for ``claims_max_stale_s`` and reused; which claims
are active is still decided on each read against the clock, so a claim still lapses at its
``expires`` (R8). A claim or a release through this process drops the kept scan at once, so the
writer's next read sees its own write. No row is ever deleted: the owner ruled the claims table
keeps its full history (no TTL), since R9's ``history_count`` counts every claim.
"""

from __future__ import annotations

import time
from typing import Any

from api_fakes import Harness

from opn_api.store import Claim

NODE = "and-reassoc"


def count_scans(h: Harness) -> list[int]:
    scans: list[int] = []
    real = h.store.list_claims

    def counting() -> list[Claim]:
        scans.append(1)
        return real()

    h.store.list_claims = counting  # type: ignore[method-assign]
    return scans


def reads(h: Harness, n: int) -> list[Any]:
    out = []
    for i in range(n):
        path = "/frontier.json" if i % 2 else "/claims.json"
        r = h.client.get(path)
        assert r.status_code == 200, r.text
        out.append(r.json())
    return out


def test_ten_reads_scan_the_claims_table_once(harness: Harness) -> None:
    scans = count_scans(harness)
    reads(harness, 10)
    assert len(scans) == 1


def test_a_claim_and_a_release_are_seen_by_the_next_read(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    reads(harness, 2)
    made = harness.client.post("/claims", json={"node_id": NODE}, headers=harness.auth(token))
    assert made.status_code == 201, made.text
    nodes = harness.client.get("/claims.json").json()["nodes"]
    assert [a["pseudonym"] for a in nodes[NODE]["active"]] == ["alice-p"]

    released = harness.client.delete(f"/claims/{made.json()['id']}", headers=harness.auth(token))
    assert released.status_code == 200, released.text
    nodes = harness.client.get("/claims.json").json()["nodes"]
    assert nodes[NODE]["active"] == []
    assert nodes[NODE]["history_count"] == 1


def test_the_scan_is_read_again_after_the_window(harness: Harness) -> None:
    scans = count_scans(harness)
    reads(harness, 3)
    kept = harness.context.claims_scan
    assert kept is not None
    kept.fetched_at = time.monotonic() - (harness.settings.claims_max_stale_s + 1)
    reads(harness, 3)
    assert len(scans) == 2


def test_a_kept_claim_still_lapses_at_its_expiry(harness: Harness) -> None:
    """The kept rows are judged against the clock on every read, so caching never extends a
    claim past ``expires``."""
    token = harness.token_for("code_alice", "alice-p")
    made = harness.client.post("/claims", json={"node_id": NODE}, headers=harness.auth(token))
    assert made.status_code == 201, made.text
    assert harness.client.get("/claims.json").json()["nodes"][NODE]["active"]
    harness.clock.advance(hours=2)  # past the one-hour minimum TTL, inside no new scan
    assert harness.client.get("/claims.json").json()["nodes"][NODE]["active"] == []
