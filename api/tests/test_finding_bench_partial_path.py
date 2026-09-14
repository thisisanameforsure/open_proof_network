"""Bench finding (2026-09-14): a precheck is spent on a bundle the submission will refuse.

A fresh agent prechecked a partial assembly (``sorry`` holes) as ``nodes/<id>/Proof.lean``.
``POST /precheck`` answered 202 and the run passed; ``POST /submissions`` with that job then
answered ``400 artifact-path-mismatch`` (F07-R1 as amended by T7, F07-Q26), because a partial is
``attempts/<ts>-<pseudonym>-partial.lean`` (D-12, F11-Q28). The precheck was wasted.

``POST /precheck`` takes no ``artifact_type`` today (F06-R1: ``node_id``, ``bundle``), so it
cannot know the bundle is meant as a partial. Neither F06 nor F07 says a precheck deliberately
leaves the type-to-path rule to the submission; F06-Q11's principle is the opposite ("a precheck
that cannot pass is refused before it costs anything"). Asserted here: a precheck that declares
the ``artifact_type`` it will be submitted as is refused up front with the submission's own
``400 artifact-path-mismatch``, naming the path the type belongs at, before any job is dispatched.
The pin keeps a precheck without the field working as it does today.
"""

from __future__ import annotations

from api_fakes import PROOF_PREFIX, TUTORIAL_NODE, TUTORIAL_PROOF, Harness
from mcp_client import McpClient

PROOF_PATH = f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean"
PARTIAL_ASSEMBLY = (
    "import Nodes.X.Context\n\ntheorem x : True := by\n  have h : True := sorry\n  exact h\n"
)


def test_precheck_refuses_an_unknown_artifact_type(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    pushed = len(harness.githost.pushes)
    r = harness.client.post(
        "/precheck",
        json={
            "node_id": TUTORIAL_NODE,
            "artifact_type": "lemma",
            "bundle": {PROOF_PATH: TUTORIAL_PROOF},
        },
        headers=harness.auth(token),
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "artifact-type-invalid", r.text
    assert "partial" in r.json()["message"], r.text
    assert len(harness.githost.pushes) == pushed


def test_precheck_accepts_a_proof_declared_at_proof_lean(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = harness.client.post(
        "/precheck",
        json={
            "node_id": TUTORIAL_NODE,
            "artifact_type": "proof",
            "bundle": {PROOF_PATH: TUTORIAL_PROOF},
        },
        headers=harness.auth(token),
    )
    assert r.status_code == 202, r.text


def test_precheck_refuses_a_partial_declared_at_proof_lean(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    pushed = len(harness.githost.pushes)
    r = harness.client.post(
        "/precheck",
        json={
            "node_id": TUTORIAL_NODE,
            "artifact_type": "partial",
            "bundle": {PROOF_PATH: PARTIAL_ASSEMBLY},
        },
        headers=harness.auth(token),
    )
    assert r.status_code == 400, f"precheck took a partial at Proof.lean: {r.status_code} {r.text}"
    assert r.json()["error"] == "artifact-path-mismatch", r.text
    message = r.json()["message"]
    assert "attempts/" in message and "-partial.lean" in message, message
    assert len(harness.githost.pushes) == pushed, "a job branch was pushed for a doomed precheck"


def test_pin_precheck_without_artifact_type_is_unchanged(harness: Harness) -> None:
    """**PIN.** F06-R1's two-field body still dispatches a job (202)."""
    token = harness.token_for("code_alice", "alice")
    r = harness.client.post(
        "/precheck",
        json={"node_id": TUTORIAL_NODE, "bundle": {PROOF_PATH: TUTORIAL_PROOF}},
        headers=harness.auth(token),
    )
    assert r.status_code == 202, r.text


def test_mcp_precheck_submission_forwards_artifact_type(harness: Harness) -> None:
    """The adapter's ``precheck_submission`` passes the optional type through, so the same
    refusal reaches an MCP client, and nothing is pushed."""
    client = McpClient(harness)
    pushed = len(harness.githost.pushes)
    refused = client.failed(
        "precheck_submission",
        {
            "node_id": TUTORIAL_NODE,
            "artifact_type": "partial",
            "bundle": {PROOF_PATH: PARTIAL_ASSEMBLY},
        },
    )
    assert refused["status"] == 400, refused
    assert refused["body"]["error"] == "artifact-path-mismatch", refused
    assert len(harness.githost.pushes) == pushed
