"""mcpfix WA1 item 5 (testers 2026-11-25, t883 2/5/9, t257b 1/12, qa-eb L1/L5/L6): what a
tester learned only from a refusal is said before the call."""

from __future__ import annotations

import pytest
from api_fakes import Harness
from mcp_client import TARGET, McpClient

from opn_api.mcp import results
from opn_api.mcp.server import BY_NAME, declare

BUDGET = 1000


@pytest.mark.parametrize("name", ["precheck_submission", "submit_proof"])
def test_partial_comment_lines_are_told(name: str) -> None:
    text = BY_NAME[name].description
    for line in ("-- approach:", "-- licence:", "-- label:", "-- claim:", "partial-unlabelled"):
        assert line in text, (name, line)
    assert "not checked for truth" in text
    assert "check_lean" in text


@pytest.mark.parametrize("name", ["precheck_submission", "submit_proof"])
def test_partial_and_reduction_are_one_for_one_hole(name: str) -> None:
    text = BY_NAME[name].input_schema["properties"]["artifact_type"]["description"]
    assert "reduction" in text and "partial" in text and "one hole" in text, text


def test_explainer_sections_are_told() -> None:
    text = BY_NAME["submit_gloss"].input_schema["properties"]["text"]["description"]
    assert "##" in text and "explainer-invalid" in text, text


def test_propose_variant_names_relation_proof_required() -> None:
    assert "relation-proof-required" in BY_NAME["propose_variant"].description


def test_submit_candidate_requires_read_others() -> None:
    assert "read_others" in BY_NAME["submit_candidate"].input_schema["required"]


def test_claim_ttl_has_its_cap() -> None:
    assert BY_NAME["claim_node"].input_schema["properties"]["ttl"]["maximum"] == 168


@pytest.mark.parametrize(
    "name",
    ["precheck_submission", "submit_proof", "submit_gloss", "propose_variant", "claim_node"],
)
def test_descriptions_fit_the_budget(name: str) -> None:
    """The budget is the declared description, plain path included (legacy surface)."""
    assert len(declare(BY_NAME[name]).description or "") <= BUDGET


def test_a_candidate_without_read_others_keeps_the_route_code(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    doc = McpClient(harness).failed(
        "submit_candidate", {"target_id": TARGET, "lean": "l"}, token=token
    )
    assert doc["error"] == "candidate-not-blind" and doc["status"] == 400
    assert results.violations("submit_candidate", doc) == []
    doc = McpClient(harness).failed(
        "submit_candidate", {"target_id": TARGET, "lean": "l", "read_others": "no"}, token=token
    )
    assert doc["error"] == "arguments-invalid"
