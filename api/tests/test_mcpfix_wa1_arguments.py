"""mcpfix WA1 item 4 (testers 2026-11-25, qa-eb B2, L3): an argument refusal names every schema
error, shows values as JSON, and a missing or malformed ``automation`` answers the service's own
codes (``automation-missing``, ``automation-invalid``) rather than ``arguments-invalid``."""

from __future__ import annotations

from api_fakes import AUTOMATION, TUTORIAL_NODE, Harness
from mcp_client import LEGACY_PATH, NODE, McpClient

from opn_api.mcp import results


def test_null_arguments_read_as_json(harness: Harness) -> None:
    doc = McpClient(harness, raw=True).failed(
        "write", {"operation": "submit_postmortem", "arguments": None}
    )
    assert doc["error"] == "arguments-invalid"
    assert "null is not of type 'object'" in doc["message"]
    assert "None" not in doc["message"]


def test_every_error_is_named(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    doc = McpClient(harness).failed(
        "propose_literature",
        {"node_id": NODE, "status": "hard", "references": [], "summary": ""},
        token=token,
    )
    assert doc["error"] == "arguments-invalid"
    for field in ("status", "references", "summary"):
        assert f"$['{field}']" in doc["message"], doc["message"]
    assert results.violations("propose_literature", doc) == []


def test_a_boolean_shows_as_json(harness: Harness) -> None:
    doc = McpClient(harness).failed("claim_node", {"node_id": NODE, "ttl": True})
    assert "true is not of type 'integer'" in doc["message"], doc["message"]


def test_missing_automation_is_automation_missing(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    for client in (McpClient(harness), McpClient(harness, path=LEGACY_PATH)):
        doc = client.failed(
            "submit_proof", {"artifact_type": "proof", "node_id": TUTORIAL_NODE}, token=token
        )
        assert doc["error"] == "automation-missing", doc
        assert doc["status"] == 400
        assert doc["source"] == "adapter"
        assert results.violations("submit_proof", doc) == []
        doc = client.failed(
            "submit_proof",
            {
                "artifact_type": "proof",
                "node_id": TUTORIAL_NODE,
                "automation": {"method": "agent", "models": ["m"]},
            },
            token=token,
        )
        assert doc["error"] == "automation-missing", doc
    assert harness.githost.pushes == []


def test_malformed_automation_is_automation_invalid(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    bad = {"method": "robot", "models": ["m"], "framework": "f"}
    client = McpClient(harness)
    doc = client.failed(
        "submit_proof",
        {"artifact_type": "proof", "node_id": TUTORIAL_NODE, "automation": bad},
        token=token,
    )
    assert doc["error"] == "automation-invalid", doc
    assert '"robot"' in doc["message"]
    assert results.violations("submit_proof", doc) == []
    doc = client.failed(
        "precheck_submission",
        {"node_id": TUTORIAL_NODE, "bundle": {}, "automation": bad},
        token=token,
    )
    assert doc["error"] == "automation-invalid", doc
    assert results.violations("precheck_submission", doc) == []


def test_automation_beside_another_error_stays_arguments_invalid(harness: Harness) -> None:
    """Only a refusal wholly about automation takes its code; mixed refusals list everything."""
    token = harness.token_for("code_alice", "alice")
    doc = McpClient(harness).failed(
        "submit_proof", {"artifact_type": "nonsense", "node_id": TUTORIAL_NODE}, token=token
    )
    assert doc["error"] == "arguments-invalid"
    assert "automation" in doc["message"] and "artifact_type" in doc["message"]


def test_a_good_automation_block_is_not_refused_by_the_adapter(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    doc = McpClient(harness).failed(
        "submit_proof",
        {"artifact_type": "proof", "node_id": TUTORIAL_NODE, "automation": AUTOMATION},
        token=token,
    )
    assert "error" not in doc or doc["error"] not in ("automation-missing", "automation-invalid")
