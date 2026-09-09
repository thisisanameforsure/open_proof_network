"""F05-T2: ``GET /info.json`` publishes the policy in force (R6; AC8)."""

from __future__ import annotations

import json

from api_fakes import Harness, make_harness

from opn_gate import schemas


def test_policy_published(harness: Harness) -> None:
    """AC8: rate_limit_policy equals the configured values, and the document still validates."""
    r = harness.client.get("/info.json")
    assert r.status_code == 200
    doc = r.json()
    assert doc["rate_limit_policy"] == harness.settings.rate_limit_policy()
    assert schemas.violations(doc, "info/v1") == []
    committed = json.loads((harness.githost.files["info.json"]).decode())
    assert committed["rate_limit_policy"] is None  # the committed file carries none
    assert {k: v for k, v in doc.items() if k != "rate_limit_policy"} == {
        k: v for k, v in committed.items() if k != "rate_limit_policy"
    }


def test_policy_follows_config() -> None:
    h = make_harness({"OPN_API_WRITES_PER_HOUR": "7", "OPN_API_CLAIM_TTL_MAX_H": "48"})
    doc = h.client.get("/info.json").json()
    assert doc["rate_limit_policy"]["writes_per_hour"] == 7
    assert doc["rate_limit_policy"]["claim_ttl_hours"] == {"min": 1, "max": 48}


def test_graph_unreachable_is_503(harness: Harness) -> None:
    """C7: the api never invents an info.json it could not read."""
    harness.githost.unreachable = True
    r = harness.client.get("/info.json")
    assert r.status_code == 503
    assert r.json()["error"] == "graph-unreachable"
