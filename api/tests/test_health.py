"""F05-T1: health and the R13 gate (AC17); config defaults (R2); request logging (R11)."""

from __future__ import annotations

import logging

import pytest
from api_fakes import TEST_ENV, Harness, make_harness

from opn_api import config


def test_health_ok(harness: Harness) -> None:
    r = harness.client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "store": "memory"}


def test_missing_dependency_503() -> None:
    """AC17: a missing table name makes health 503 naming it, and every route 503."""
    h = make_harness(
        {"OPN_API_STORE": "dynamodb", "OPN_API_TABLE_TOKENS": "t", "OPN_API_TABLE_CLAIMS": "c"}
    )
    r = h.client.get("/health")
    assert r.status_code == 503
    assert r.json()["ok"] is False
    assert "OPN_API_TABLE_IDENTITIES" in r.json()["missing"]
    assert "OPN_API_TABLE_TOKENS" not in r.json()["missing"]
    other = h.client.get("/dco.json")
    assert other.status_code == 503
    assert other.json()["error"] == "not-configured"
    assert "OPN_API_TABLE_IDENTITIES" in other.json()["message"]


def test_missing_secret_503() -> None:
    env = {k: v for k, v in TEST_ENV.items() if k != "OPN_API_TOKEN_SECRET"}
    settings = config.load(env)
    assert settings.missing() == ["OPN_API_TOKEN_SECRET"]


def test_defaults_documented() -> None:
    """R2/C6: every non-secret value has a default; secrets default to None; repr hides them."""
    s = config.load({})
    assert s.store == "memory"
    assert s.writes_per_hour == 120
    assert s.active_claims == 20
    assert s.claim_ttl_min_h == 1 and s.claim_ttl_max_h == 168
    assert s.token_starts_per_day == 10
    assert s.token_secret is None and s.github_client_secret is None
    loaded = config.load(TEST_ENV)
    assert "token-secret-for-tests" not in repr(loaded)
    assert "client-secret-for-tests" not in repr(loaded)
    assert "<set>" in repr(loaded)
    with pytest.raises(config.ConfigError, match="OPN_API_STORE"):
        config.load({"OPN_API_STORE": "files"})
    with pytest.raises(config.ConfigError, match="exceeds"):
        config.load({"OPN_API_CLAIM_TTL_MIN_H": "10", "OPN_API_CLAIM_TTL_MAX_H": "5"})
    with pytest.raises(config.ConfigError, match="integer"):
        config.load({"OPN_API_WRITES_PER_HOUR": "lots"})


def test_rate_limit_policy_shape() -> None:
    assert config.load({}).rate_limit_policy() == {
        "writes_per_hour": 120,
        "active_claims": 20,
        "tokens_per_github_login": 1,
        "token_starts_per_address_per_day": 10,
        "claim_ttl_hours": {"min": 1, "max": 168},
    }


def test_parameter_store_mapping() -> None:
    class Ssm:
        def get_parameters_by_path(self, **kwargs: object) -> dict[str, object]:
            return {
                "Parameters": [
                    {"Name": "/opn/api/token-secret", "Value": "s3cret"},
                    {"Name": "/opn/api/github-client-id", "Value": "Iv1.x"},
                    {"Name": "/opn/api/unrelated", "Value": "ignored"},
                ]
            }

    found = config.load_parameters("/opn/api/", client=Ssm())
    assert found == {"OPN_API_TOKEN_SECRET": "s3cret", "OPN_API_GITHUB_CLIENT_ID": "Iv1.x"}


def test_request_logged_without_body(harness: Harness, caplog: pytest.LogCaptureFixture) -> None:
    """R11: method, route, identity, status, duration — never a body."""
    with caplog.at_level(logging.INFO, logger="opn_api.access"):
        r = harness.client.post("/tokens", json={"pseudonym": "secret-body-content"})
    assert r.status_code == 400
    line = [rec.getMessage() for rec in caplog.records if rec.name == "opn_api.access"][-1]
    assert line.startswith("POST POST /tokens identity=- status=400 ms=")
    assert "secret-body-content" not in caplog.text


def test_unknown_route_404(harness: Harness) -> None:
    r = harness.client.get("/nothing")
    assert r.status_code == 404
    assert r.json()["error"] == "not-found"
