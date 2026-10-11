"""F05-T21 (audit 2026-10-04): the founder can revoke an identity's tokens.

F05 §7 promises that "tokens can be revoked by the founder via a CLI against the store", and
both verifiers already refuse a record marked ``revoked`` (``auth.authenticate`` with 401
``invalid-token``, the MCP ``StoreTokenVerifier`` with no access token) — but nothing ever wrote
the mark, so a leaked or abused token could only be stopped by rotating the service's token
secret, which logs every identity out at once.

``Store.revoke_tokens`` marks every token of one identity (DynamoDB has no index by identity, so
it scans the ``token#`` prefix for it), and ``api/tools/tokens.py revoke --pseudonym`` finds the
identity by the pseudonym's uniqueness marker and calls it. Both stores.
"""

from __future__ import annotations

import asyncio
import importlib.util
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from test_store_seam import dynamo

from opn_api.mcp.auth import StoreTokenVerifier
from opn_api.store import MemoryStore
from opn_gate import schemas

CLAIM = {"node_id": "and-reassoc"}


def tokens_tool() -> Any:
    path = schemas.SCHEMAS_DIR.parents[1] / "api" / "tools" / "tokens.py"
    spec = importlib.util.spec_from_file_location("opn_tokens_tool", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=["memory", "dynamodb"])
def harness(request: pytest.FixtureRequest) -> Harness:
    return make_harness(store=MemoryStore() if request.param == "memory" else dynamo())


def write(h: Harness, token: str) -> Any:
    return h.client.post("/claims", json=CLAIM, headers=h.auth(token))


def verified(h: Harness, token: str) -> Any:
    return asyncio.run(StoreTokenVerifier(h.context).verify_token(token))


def test_a_revoked_token_is_refused_on_both_paths(
    harness: Harness, capsys: pytest.CaptureFixture[str]
) -> None:
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    assert write(harness, alice).status_code == 201
    assert verified(harness, alice) is not None

    code = tokens_tool().main(["revoke", "--pseudonym", "Alice"], store=harness.store)
    assert code == 0
    assert "revoked 1 token(s) of alice" in capsys.readouterr().out

    refused = write(harness, alice)
    assert refused.status_code == 401, refused.text
    assert refused.json()["error"] == "invalid-token"
    assert verified(harness, alice) is None
    # Another identity's token is untouched.
    assert write(harness, bob).status_code == 201
    assert verified(harness, bob) is not None


def test_revoking_again_revokes_nothing_new(harness: Harness) -> None:
    harness.token_for("code_alice", "alice")
    tool = tokens_tool()
    assert tool.revoke(harness.store, "alice")[1] == 1
    assert tool.revoke(harness.store, "alice")[1] == 0


def test_an_unknown_pseudonym_is_named_and_changes_nothing(
    harness: Harness, capsys: pytest.CaptureFixture[str]
) -> None:
    alice = harness.token_for("code_alice", "alice")
    assert tokens_tool().main(["revoke", "--pseudonym", "nobody"], store=harness.store) == 1
    assert "nobody" in capsys.readouterr().err
    assert write(harness, alice).status_code == 201


def test_the_tool_refuses_a_memory_store(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Settings come from the environment only; with no DynamoDB named there is nothing to revoke
    in, and the tool says so rather than revoking in a store of its own."""
    monkeypatch.setenv("OPN_API_STORE", "memory")
    assert tokens_tool().main(["revoke", "--pseudonym", "alice"]) == 2
    assert "OPN_API_STORE" in capsys.readouterr().err
