"""F05-T2: per-identity and per-source rate limits (R6; AC7)."""

from __future__ import annotations

from api_fakes import Harness, make_harness

CLAIM = {"node_id": "and-reassoc"}


def test_hourly_write_limit() -> None:
    """AC7: the 121st write in an hour is 429 with Retry-After."""
    h = make_harness({"OPN_API_ACTIVE_CLAIMS": "1000"})
    token = h.token_for("code_alice", "alice-p")
    for n in range(120):
        r = h.client.post("/claims", json=CLAIM, headers=h.auth(token))
        assert r.status_code == 201, (n, r.text)
    over = h.client.post("/claims", json=CLAIM, headers=h.auth(token))
    assert over.status_code == 429
    assert over.json()["error"] == "rate-limited"
    assert int(over.headers["retry-after"]) == 3600 - 0  # the clock sits at the hour boundary

    # The next window is fresh.
    h.clock.advance(hours=1)
    assert h.client.post("/claims", json=CLAIM, headers=h.auth(token)).status_code == 201


def test_limit_is_per_identity() -> None:
    h = make_harness({"OPN_API_WRITES_PER_HOUR": "1"})
    alice = h.token_for("code_alice", "alice-p")
    bob = h.token_for("code_bob", "bob-p")
    assert h.client.post("/claims", json=CLAIM, headers=h.auth(alice)).status_code == 201
    assert h.client.post("/claims", json=CLAIM, headers=h.auth(alice)).status_code == 429
    assert h.client.post("/claims", json=CLAIM, headers=h.auth(bob)).status_code == 201


def test_token_starts_limited_per_source() -> None:
    """R6: unauthenticated starts are limited per address per day."""
    h = make_harness({"OPN_API_TOKEN_STARTS_PER_DAY": "2"})
    headers = {"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}
    for _ in range(2):
        r = h.client.get("/auth/github/start", headers=headers, follow_redirects=False)
        assert r.status_code == 302
    over = h.client.get("/auth/github/start", headers=headers, follow_redirects=False)
    assert over.status_code == 429
    assert int(over.headers["retry-after"]) > 0
    # A different source is unaffected.
    other = h.client.get(
        "/auth/github/start", headers={"X-Forwarded-For": "198.51.100.2"}, follow_redirects=False
    )
    assert other.status_code == 302


def test_reads_are_not_write_limited(harness: Harness) -> None:
    h = make_harness({"OPN_API_WRITES_PER_HOUR": "1"})
    for _ in range(5):
        assert h.client.get("/dco.json").status_code == 200
