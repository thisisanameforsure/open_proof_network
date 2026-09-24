"""Finding: the MCP write tools rename arguments silently (2026-09-13, the Euclid tester).

D-28's parameter names and the endpoints' body fields differ in four places (``ttl`` is
``ttl_hours``, ``stmt`` is ``statement`` twice, ``attestation`` binds through the ``id`` it
carries as ``precheck_job_id``). The mapping lives only inside the handlers' bodies, so neither
the guide nor a caller can see it, and ``submit_proof`` demands the whole ``get_precheck``
result when the endpoint needs one id — the tester had the id and not the document.

Mike's decision (2026-09-14, plan F09-T7): ``writes.RENAMES`` is the one table, per tool
``{argument: body field}``, and the handlers send what it says, so the guide's appendix can be
checked against it (F10-T7); ``submit_proof`` accepts ``precheck_job_id`` directly, forwarding the
same body as the ``attestation`` form, and exactly one of the two or ``arguments-invalid``.

``RENAMES`` and the new parameter are looked up inside the test body, never imported: they were
held as strict xfails until F09-T7 landed, and the marks came off with it (conventions §2).
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any, cast

import pytest
from api_fakes import (
    PROOF_PREFIX,
    TUTORIAL_NODE,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_precheck_key,
)
from mcp_client import McpClient

from opn_api.mcp import writes
from opn_api.mcp.calls import Answer, Call, Tool

BUNDLE = {f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean": TUTORIAL_PROOF}
JOB_ID = "01M00000000000000000000001"
BEARER = "a-bearer-the-stub-never-sends"
EXPECTED_RENAMES = {
    "claim_node": {"ttl": "ttl_hours"},
    "propose_speculative_node": {"stmt": "statement"},
    "propose_variant": {"stmt": "statement"},
    "submit_proof": {"attestation": "precheck_job_id"},
}


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


class RecordingCall(Call):
    """A ``Call`` whose endpoint records the request instead of making it, and answers 201."""

    def __init__(self) -> None:
        super().__init__(ctx=cast(Any, None), http=cast(Any, None), token=BEARER)
        self.sent: list[tuple[str, str, dict[str, Any] | None]] = []

    async def endpoint(
        self, method: str, path: str, *, json: Mapping[str, Any] | None = None
    ) -> Answer:
        self.sent.append((method, path, dict(json) if json is not None else None))
        return Answer(201, {"id": "01M00000000000000000000002"})


def sent_body(tool: Tool, args: dict[str, Any]) -> dict[str, Any] | None:
    call = RecordingCall()

    async def go() -> None:
        await tool.handler(call, args)

    asyncio.run(go())
    [(_, _, body)] = call.sent
    return body


def value_for(tool: str, name: str) -> Any:
    """A distinct value for each argument; ``attestation`` is a get_precheck result."""
    if tool == "submit_proof" and name == "attestation":
        return {"id": JOB_ID, "state": "done"}
    return f"{tool}.{name}"


def expected_value(tool: str, name: str) -> Any:
    if tool == "submit_proof" and name == "attestation":
        return JOB_ID
    return value_for(tool, name)


def test_renames_is_what_the_handlers_send() -> None:
    """``writes.RENAMES`` is the four renames, and for every write tool that sends a body the
    body's fields are exactly its arguments passed through ``RENAMES`` — no other rename hides
    in a handler."""
    renames = getattr(writes, "RENAMES", None)
    assert isinstance(renames, Mapping), "writes.RENAMES does not exist"
    assert {tool: dict(m) for tool, m in renames.items()} == EXPECTED_RENAMES

    with_body = 0
    for tool in writes.TOOLS:
        names = [
            n
            for n in tool.input_schema["properties"]
            if not (tool.name == "submit_proof" and n == "precheck_job_id")
        ]
        args = {n: value_for(tool.name, n) for n in names}
        body = sent_body(tool, args)
        if body is None:
            continue  # a path-only call (release_claim, withdraw_submission)
        with_body += 1
        mapping = dict(renames.get(tool.name, {}))
        assert body == {mapping.get(n, n): expected_value(tool.name, n) for n in names}, tool.name
    assert with_body == len(writes.TOOLS) - 2


def test_submit_proof_accepts_precheck_job_id_and_forwards_the_same_body(
    harness: Harness, key: PrecheckKey
) -> None:
    """``precheck_job_id`` is a declared parameter; given it, the handler sends exactly the
    body the ``attestation`` form sends; through the adapter it opens the pull request; both
    or neither is ``arguments-invalid`` and nothing is opened."""
    client = McpClient(harness)
    [declared] = [t for t in client.list_tools() if t.name == "submit_proof"]
    properties = declared.inputSchema["properties"]
    assert "precheck_job_id" in properties, sorted(properties)

    [tool] = [t for t in writes.TOOLS if t.name == "submit_proof"]
    common = {"node_id": TUTORIAL_NODE, "artifact_type": "proof", "bundle": BUNDLE}
    by_id = sent_body(tool, {**common, "precheck_job_id": JOB_ID})
    by_attestation = sent_body(tool, {**common, "attestation": {"id": JOB_ID, "state": "done"}})
    assert by_id == by_attestation == {**common, "precheck_job_id": JOB_ID}

    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    doc = client.ok("submit_proof", {**common, "precheck_job_id": job["id"]}, token=token)
    assert doc["status"] == 201, doc
    assert doc["body"]["pr_number"] == 1
    assert len(harness.githost.pulls) == 1

    attestation = harness.client.get(f"/precheck/{job['id']}").json()
    both = client.failed(
        "submit_proof",
        {**common, "precheck_job_id": job["id"], "attestation": attestation},
        token=token,
    )
    assert both["error"] == "arguments-invalid", both
    neither = client.failed("submit_proof", common, token=token)
    assert neither["error"] == "arguments-invalid", neither
    assert len(harness.githost.pulls) == 1
