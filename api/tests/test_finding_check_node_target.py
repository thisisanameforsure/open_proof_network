"""``POST /check`` finds a node's target itself, and hazards mode says what the node acknowledged
(lead's live probe, 2026-09-27; the testers of 2026-09-24 hit the same shape).

Three findings, one route:

1. A call with ``node_id`` and no ``target_id`` answered ``400 target-id-invalid "target_id must
   match ^[a-z0-9][a-z0-9-]*$"``. The field was missing, not invalid, and a node belongs to one
   target, which the products name (``precheck.node_facts``, as ``get_node`` and the precheck read
   it). So the target is derived from the node; with neither, the refusal is its own code naming
   both ways to supply one; a ``target_id`` the node does not belong to is refused as a mismatch
   before anything is looked up under the wrong target. MCP ``check_lean`` follows: its input
   schema no longer requires ``target_id``, as ``get_node`` never did.
2. ``mode: hazards`` on a node listed every finding bare, even the ones the node's own
   ``META.yaml`` acknowledges (live: erdos-69's div-zero), so the answer read as work to do. Each
   finding an acknowledgement matches — by step 6's own rule, ``steps.hazards.evaluate`` — now
   says ``acknowledged: true`` with the justification; the rest are as they were.
3. The proposal pre-flight's ``hazards_preflight`` said ``clear`` when there were findings and the
   proposal acknowledged every one. ``clear`` now means no findings; that case is ``acknowledged``.
"""

from __future__ import annotations

from typing import Any

import samples
import yaml
from api_fakes import Harness
from mcp_client import NODE, NODE_DIR, TARGET, McpClient
from test_checks import PIN, post, refused, seed
from test_finding_hazards_preflight import (
    CHECKERS,
    DIV,
    SUB,
    ack,
    found,
    harness,
    hazard_calls,
    speculative,
)

from opn_api import checks
from opn_gate import schemas

PROOF = "theorem OpnProp.and_reassoc : True := by\n  trivial\n"


def seeded(*hazard_replies: Any, acks: list[dict[str, str]] | None = None) -> Harness:
    """The fixture node on a pinned target naming ``CHECKERS``, its ``META.yaml`` acknowledging
    ``acks``, and the hosted checker answering ``hazard_replies`` to the hazard program."""
    h = harness(*hazard_replies)
    seed(h)
    files = h.githost.files
    files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(mathlib_sha=PIN, hazard_checkers=CHECKERS)
    )
    meta = yaml.safe_load(files[NODE_DIR + "META.yaml"])
    meta["acknowledged_hazards"] = acks or []
    files[NODE_DIR + "META.yaml"] = yaml.safe_dump(meta, sort_keys=True).encode()
    h.context.files.clear()
    return h


# --- 1. the target is the node's --------------------------------------------------------------


def test_a_node_id_alone_finds_its_target() -> None:
    h = seeded()
    r = post(h, {"node_id": NODE, "content": PROOF})
    assert r.status_code == 200, r.text
    record = h.store.checks[r.json()["log_id"]]
    assert (record.target_id, record.node_id) == (TARGET, NODE)


def test_a_node_id_alone_serves_every_node_mode() -> None:
    h = seeded(found())
    r = post(h, {"node_id": NODE, "mode": "hazards"})
    assert r.status_code == 200, r.text
    assert r.json()["hazards"]["checkers"] == CHECKERS


def test_neither_target_nor_node_is_its_own_refusal() -> None:
    h = seeded()
    doc = refused(post(h, {"content": PROOF}), 400, "target-id-required")
    assert "target_id" in doc["message"] and "node_id" in doc["message"]
    assert h.store.checks == {} and h.axle.calls == []


def test_a_malformed_target_is_still_invalid() -> None:
    h = seeded()
    body = {"target_id": "Bad!", "node_id": NODE, "content": PROOF}
    refused(post(h, body), 400, "target-id-invalid")
    refused(post(h, {"target_id": None, "content": PROOF}), 400, "target-id-required")


def test_a_target_the_node_does_not_belong_to_is_a_mismatch() -> None:
    """Refused as the mismatch it is, before the wrong target's pin is looked up (that answered
    ``404 target-unknown`` for a target that merely is not the node's)."""
    h = seeded()
    doc = refused(
        post(h, {"target_id": "other-target", "node_id": NODE, "content": PROOF}),
        400,
        "node-target-mismatch",
    )
    assert TARGET in doc["message"] and "other-target" in doc["message"]
    assert h.axle.calls == []


def test_an_unknown_node_without_a_target_is_unknown() -> None:
    h = seeded()
    doc = refused(post(h, {"node_id": "no-such-node", "content": PROOF}), 404, "node-unknown")
    assert h.store.checks[doc["details"]["log_id"]].outcome == "node-unknown"


def test_the_mcp_tool_does_not_require_a_target() -> None:
    from opn_api.mcp.server import BY_NAME  # noqa: PLC0415

    tool = BY_NAME["check_lean"]
    assert "target_id" not in tool.input_schema["required"]
    assert "target_id" in tool.input_schema["properties"]
    h = seeded()
    with h.client:
        out = McpClient(h).ok("check_lean", {"node_id": NODE, "content": PROOF})
    assert out["status"] == 200, out
    assert "derived from the node" in tool.description


# --- 2. hazards mode reads the node's acknowledgements ------------------------------------------


def test_an_acknowledged_finding_says_so() -> None:
    h = seeded(found(DIV, SUB), acks=[ack(DIV)])
    r = post(h, {"target_id": TARGET, "node_id": NODE, "mode": "hazards"})
    assert r.status_code == 200, r.text
    findings = r.json()["hazards"]["findings"]
    assert findings == [
        {**DIV, "acknowledged": True, "justification": ack(DIV)["justification"]},
        SUB,
    ]
    assert len(hazard_calls(h)) == 1


def test_an_acknowledgement_is_matched_by_step_sixs_rule() -> None:
    """Checker and location exactly, and a justification that says something (``evaluate``)."""
    near = {**ack(DIV), "location": "1 / (2 ^ (m - n) - 3) "}
    blank = {**ack(SUB), "justification": "  "}
    h = seeded(found(DIV, SUB), acks=[near, blank])
    r = post(h, {"target_id": TARGET, "node_id": NODE, "mode": "hazards"})
    assert r.json()["hazards"]["findings"] == [DIV, SUB], r.text


def test_a_statement_not_yet_a_node_has_nothing_acknowledged() -> None:
    h = seeded(found(DIV), acks=[ack(DIV)])
    statement = "theorem Opn.x : True := by\n  sorry\n"
    r = post(h, {"target_id": TARGET, "mode": "hazards", "statement": statement})
    assert r.json()["hazards"]["findings"] == [DIV], r.text


# --- 3. the pre-flight's word -------------------------------------------------------------------


def test_the_pre_flight_says_acknowledged_when_every_finding_was() -> None:
    h = harness(found(DIV, SUB))
    r = speculative(h, acknowledged_hazards=[ack(DIV), ack(SUB, "m > n by hypothesis")])
    assert r.status_code == 201, r.text
    assert r.json()["hazards_preflight"] == "acknowledged"


def test_the_pre_flight_says_clear_only_with_no_findings() -> None:
    h = harness(found())
    r = speculative(h)
    assert r.status_code == 201, r.text
    assert r.json()["hazards_preflight"] == checks.PREFLIGHT_CLEAR == "clear"


def test_the_mcp_descriptions_name_every_pre_flight_word() -> None:
    from opn_api.mcp.server import BY_NAME  # noqa: PLC0415

    for name in ("propose_speculative_node", "propose_variant"):
        text = BY_NAME[name].description
        assert "`hazards_preflight` says clear, acknowledged, inconclusive or unavailable" in text


def test_the_mcp_description_says_hazards_takes_no_content() -> None:
    from opn_api.mcp.server import BY_NAME  # noqa: PLC0415

    text = BY_NAME["check_lean"].description
    hazards = text.split("Mode hazards", 1)[1]
    assert "send no content" in hazards and "400 content-not-used" in hazards
    assert "acknowledged: true" in text
