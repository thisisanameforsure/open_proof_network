"""F29-T12 (B13, 2026-11-19 run): the service takes a hole's label on its bullet's own line.

The service refuses an unlabelled partial before any precheck (F29-T3) with the gate's own
reader, so a ``· -- label: …`` line the reader skipped was refused ``partial-unlabelled`` here
too, before the gate was ever asked. ``POST /precheck`` and ``POST /submissions`` must both take
the bullet-line form.
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import AUTOMATION, PROOF_PREFIX, TUTORIAL_NODE, Harness

from opn_api import submissions

PARTIAL_PATH = f"{PROOF_PREFIX}{TUTORIAL_NODE}/attempts/20261119T100000Z-alice-partial.lean"

ON_THE_BULLET = (
    "import Nodes.X.Context\n\n"
    "theorem x : True ∧ True := by\n"
    "  -- approach: split the conjunction and close each half directly\n"
    "  -- licence: CC-BY-4.0\n"
    "  refine ⟨?_, ?_⟩\n"
    "  · -- label: the left half\n"
    "    -- claim: $\\top$\n"
    "    have h_left : True := sorry\n"
    "    exact h_left\n"
    "  · -- label: the right half\n"
    "    -- claim: $\\top$\n"
    "    have h_right : True := sorry\n"
    "    exact h_right\n"
)


def test_check_declarations_takes_the_bullet_line_label() -> None:
    submissions.check_declarations({PARTIAL_PATH: ON_THE_BULLET}, "partial")


def test_precheck_takes_a_label_on_the_bullet_line(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = harness.client.post(
        "/precheck",
        json={
            "node_id": TUTORIAL_NODE,
            "bundle": {PARTIAL_PATH: ON_THE_BULLET},
            "artifact_type": "partial",
        },
        headers=harness.auth(token),
    )
    assert r.status_code == 202, r.text


def test_submission_does_not_refuse_it_as_unlabelled(harness: Harness) -> None:
    """The submission route's own check (the one a job minted before the rule must still meet)
    reads the same reader; without a precheck job the next refusal is about the job, not the
    words."""
    token = harness.token_for("code_alice", "alice")
    body: dict[str, Any] = {
        "node_id": TUTORIAL_NODE,
        "artifact_type": "partial",
        "bundle": {PARTIAL_PATH: ON_THE_BULLET},
        "precheck_job_id": "0" * 32,
        "automation": AUTOMATION,
    }
    r = harness.client.post("/submissions", json=body, headers=harness.auth(token))
    assert r.json().get("error") != "partial-unlabelled", r.text


@pytest.mark.parametrize("artifact_type", ["partial", None])
def test_both_declared_and_inferred_partials_take_it(artifact_type: str | None) -> None:
    submissions.check_declarations({PARTIAL_PATH: ON_THE_BULLET}, artifact_type)
