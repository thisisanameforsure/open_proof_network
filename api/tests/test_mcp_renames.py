"""F09-T7: the edges of ``writes.RENAMES`` and of ``submit_proof``'s two ways to name a precheck.

The finding tests (``test_finding_argument_renames.py``) hold the table equal to what every
handler sends. Here: both or neither of ``attestation`` and ``precheck_job_id`` is refused before
any endpoint is called, with a schema-valid error naming both; an omitted renamed argument sends
neither its own name nor its body field; and every rename names a parameter the tool declares.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from api_fakes import PROOF_PREFIX, TUTORIAL_NODE, TUTORIAL_PROOF
from test_finding_argument_renames import JOB_ID, RecordingCall

from opn_api.mcp import results, writes
from opn_api.mcp.calls import ToolError

BY_NAME = {t.name: t for t in writes.TOOLS}
COMMON = {
    "node_id": TUTORIAL_NODE,
    "artifact_type": "proof",
    "bundle": {f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean": TUTORIAL_PROOF},
}


def run(tool: str, args: dict[str, Any]) -> tuple[RecordingCall, dict[str, Any] | ToolError]:
    call = RecordingCall()

    async def go() -> dict[str, Any]:
        return await BY_NAME[tool].handler(call, args)

    try:
        return call, asyncio.run(go())
    except ToolError as failure:
        return call, failure


@pytest.mark.parametrize(
    ("given", "said"),
    [
        ({"attestation": {"id": JOB_ID, "state": "done"}, "precheck_job_id": JOB_ID}, "both"),
        ({}, "neither"),
    ],
)
def test_submit_proof_both_or_neither_is_refused_before_any_call(
    given: dict[str, Any], said: str
) -> None:
    call, outcome = run("submit_proof", {**COMMON, **given})
    assert isinstance(outcome, ToolError), outcome
    doc = outcome.doc
    assert (doc["error"], doc["source"]) == ("arguments-invalid", "adapter")
    assert "`attestation`" in doc["message"] and "`precheck_job_id`" in doc["message"]
    assert said in doc["message"]
    assert results.violations("submit_proof", doc) == []
    assert call.sent == []


def test_submit_proof_attestation_without_an_id_sends_a_null_id() -> None:
    """The attestation form sends what the document carries; an id-less document is the
    endpoint's refusal to name, not the adapter's to guess (F09-R7)."""
    call, _ = run("submit_proof", {**COMMON, "attestation": {"state": "done"}})
    [(_, _, body)] = call.sent
    assert body == {**COMMON, "precheck_job_id": None}


@pytest.mark.parametrize(
    ("tool", "renamed"),
    [
        (tool, argument)
        for tool, mapping in writes.RENAMES.items()
        if tool != "submit_proof"  # its argument's omission is the both-or-neither rule above
        for argument in mapping
    ],
)
def test_an_omitted_renamed_argument_sends_nothing(tool: str, renamed: str) -> None:
    properties = BY_NAME[tool].input_schema["properties"]
    args = {n: f"{tool}.{n}" for n in properties if n != renamed}
    call, _ = run(tool, args)
    [(_, _, body)] = call.sent
    assert body is not None
    field = writes.RENAMES[tool][renamed]
    assert renamed not in body and field not in body, body
    assert body == args  # nothing else renamed, nothing added


def test_submit_proof_by_id_sends_no_attestation_field() -> None:
    call, _ = run("submit_proof", {**COMMON, "precheck_job_id": JOB_ID})
    [(_, _, body)] = call.sent
    assert body == {**COMMON, "precheck_job_id": JOB_ID}


def test_every_rename_names_a_declared_parameter() -> None:
    """A rename for an argument the tool does not declare could never apply, and would make the
    guide's column (F10-T7) describe a parameter no client can send."""
    for tool, mapping in writes.RENAMES.items():
        properties = BY_NAME[tool].input_schema["properties"]
        for argument, field in mapping.items():
            assert argument in properties, (tool, argument)
            assert argument != field, (tool, argument)
