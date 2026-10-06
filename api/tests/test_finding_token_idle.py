"""F05-T29 (decisions v3.29, D-19): a write token lapses only after long disuse.

D-19 v3.29: "An agent keeps no memory between sessions, so no part of this policy depends on an
agent remembering anything. v3.28's ninety-day lapse is replaced: a write token lapses only after
a long stretch in which it is not used (a published number of days, 180 at the pilot), so a token
in use never lapses and none has to be renewed; a token left behind in a log by an identity that
has stopped working dies on its own. [...] Rotation stays available and is never required."

What the service does (Q29):
  - each authenticated use refreshes the token's ``last_used``, written at most once a day per
    token by a conditional update, so a busy agent costs one store write a day, not one a request;
  - a token unused for ``OPN_API_TOKEN_IDLE_DAYS`` (default 180) is 401 ``token-expired``, with a
    message naming the recovery route;
  - a token with no recorded use counts from ``OPN_API_TOKEN_CUTOVER`` (or its own issue, if
    later), so none lapses at the deploy.

Both stores.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from test_store_seam import FakeTable, dynamo

from opn_api import auth, config
from opn_api.store import KEY_TOKEN, DynamoStore, Identity, MemoryStore, TokenRecord


@pytest.fixture(params=["memory", "dynamodb"])
def harness(request: pytest.FixtureRequest) -> Harness:
    return make_harness(store=MemoryStore() if request.param == "memory" else dynamo())


def use(h: Harness, token: str) -> Any:
    """One authenticated call that changes nothing: the caller's own claims."""
    return h.client.get("/claims/mine", headers=h.auth(token))


class CountingTokens(dict[str, TokenRecord]):
    """The memory store's token table, counting every write to it."""

    writes = 0

    def __setitem__(self, key: str, value: TokenRecord) -> None:
        type(self).writes += 1
        super().__setitem__(key, value)


def token_writes(h: Harness) -> int:
    """Writes to ``token#`` records so far (rate counters, claims and the rest not counted)."""
    if isinstance(h.store, DynamoStore):
        table = h.store._tokens
        assert isinstance(table, FakeTable)
        count = 0
        for op, kwargs in table.calls:
            if op == "put_item":
                key = str(kwargs["Item"]["key"])
            elif op in ("update_item", "delete_item"):
                key = str(kwargs["Key"]["key"])
            else:
                continue
            count += key.startswith(KEY_TOKEN)
        return count
    assert isinstance(h.store.tokens, CountingTokens)
    return CountingTokens.writes


def counting(h: Harness) -> None:
    if isinstance(h.store, MemoryStore):
        CountingTokens.writes = 0
        h.store.tokens = CountingTokens(h.store.tokens)


# --- a token in use never lapses -------------------------------------------------------------


def test_a_token_used_every_day_for_a_year_still_authenticates(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    for day in range(366):
        answer = use(harness, token)
        assert answer.status_code == 200, (day, answer.text)
        harness.clock.advance(days=1)
    assert use(harness, token).status_code == 200


def test_a_token_used_every_hundred_days_never_lapses(harness: Harness) -> None:
    """Long gaps inside the window are fine: the window counts from the last use."""
    token = harness.token_for("code_alice", "alice")
    for _ in range(5):
        harness.clock.advance(days=179)
        assert use(harness, token).status_code == 200


def test_a_token_unused_for_181_days_is_refused(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.clock.advance(days=30)
    assert use(harness, token).status_code == 200  # last use: 2026-10-09
    harness.clock.advance(days=181)
    refused = use(harness, token)
    assert refused.status_code == 401, refused.text
    body = refused.json()
    assert body["error"] == "token-expired"
    assert refused.headers["www-authenticate"].startswith("Bearer")
    assert "180 days" in body["message"]
    # restated by F22-T25: the way back names a route that exists (the recovery code, F05-T30,
    # is not built, and its route answered 404)
    assert "GET /auth/github/start" in body["message"]
    assert "/tokens/recover" not in body["message"]
    assert "2026-10-09" in body["message"]  # when it was last used


def test_a_token_unused_for_179_days_still_works(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.clock.advance(days=179)
    assert use(harness, token).status_code == 200


def test_the_idle_window_is_configuration() -> None:
    settings = config.load({"OPN_API_TOKEN_IDLE_DAYS": "30"})
    assert settings.token_idle_days == 30
    assert config.load({}).token_idle_days == 180
    with pytest.raises(config.ConfigError):
        config.load({"OPN_API_TOKEN_IDLE_DAYS": "0"})
    h = make_harness(env={"OPN_API_TOKEN_IDLE_DAYS": "7"})
    token = h.token_for("code_alice", "alice")
    h.clock.advance(days=7)
    assert use(h, token).json()["error"] == "token-expired"


# --- one store write a day -------------------------------------------------------------------


def test_last_use_is_written_at_most_once_a_day(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")  # issue records the first use
    counting(harness)
    before = token_writes(harness)
    harness.clock.advance(days=1)
    for _ in range(3):
        for _ in range(40):
            assert use(harness, token).status_code == 200
            harness.clock.advance(minutes=10)  # 40 uses over 6 h 40 min
        harness.clock.advance(hours=18)  # next day
    assert token_writes(harness) - before == 3


def test_the_last_use_is_recorded(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.clock.advance(days=3)
    use(harness, token)
    record = harness.store.get_token(auth.token_hash(harness.settings.token_secret or "", token))
    assert record is not None
    assert record.last_used == "2026-09-12T12:00:00Z"


# --- tokens from before the field ------------------------------------------------------------


def test_a_token_with_no_recorded_use_counts_from_the_cutover() -> None:
    """A token issued before tokens recorded their use: its window starts at the cutover, so a
    deploy never lapses a token an agent is still holding."""
    h = make_harness(env={"OPN_API_TOKEN_CUTOVER": "2026-10-10"})
    held = Identity("01LEGACY", "old-hand", "github", "old-hand", "2026-09-01T00:00:00Z")
    h.store.put_identity(held)
    token = auth.new_token()
    h.store.put_token(
        TokenRecord(
            token_hash=auth.token_hash(h.settings.token_secret or "", token),
            identity_id=held.id,
            created="2026-09-01T00:00:00Z",
        )
    )
    cutover = datetime(2026, 10, 10, tzinfo=UTC)
    h.clock.current = cutover + timedelta(days=180) - timedelta(minutes=1)
    assert use(h, token).status_code == 200  # and that use resets the window
    h.clock.current = cutover + timedelta(days=359)
    assert use(h, token).status_code == 200
    h.clock.current = cutover + timedelta(days=360 + 180)
    assert use(h, token).json()["error"] == "token-expired"


def test_an_unused_legacy_token_lapses_180_days_after_the_cutover() -> None:
    h = make_harness(env={"OPN_API_TOKEN_CUTOVER": "2026-10-10"})
    held = Identity("01LEGACY", "old-hand", "github", "old-hand", "2026-09-01T00:00:00Z")
    h.store.put_identity(held)
    token = auth.new_token()
    h.store.put_token(
        TokenRecord(
            token_hash=auth.token_hash(h.settings.token_secret or "", token),
            identity_id=held.id,
            created="2026-09-01T00:00:00Z",
        )
    )
    h.clock.current = datetime(2026, 10, 10, tzinfo=UTC) + timedelta(days=180)
    assert use(h, token).json()["error"] == "token-expired"


# --- rotation stays, and is never required ----------------------------------------------------


def test_rotation_is_optional_and_still_works(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.clock.advance(days=400)  # used never: lapsed
    assert use(harness, token).json()["error"] == "token-expired"
    other = harness.token_for("code_bob", "bob")
    harness.clock.advance(days=1)
    rotated = harness.client.post("/tokens/renew", headers=harness.auth(other))
    assert rotated.status_code == 201, rotated.text
    assert "expires" not in rotated.json()  # no fixed end any more
    assert use(harness, rotated.json()["token"]).status_code == 200
    assert use(harness, other).json()["error"] == "invalid-token"
