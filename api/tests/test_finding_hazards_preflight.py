# ruff: noqa: RUF001 — the fixtures are Lean source, with its double-struck letters
"""F13-T20: the hazard checkers run through the hosted checker before a proposal opens, and
``POST /check`` has a ``hazards`` mode (testers 2026-09-24; ruling D8; F02 owns the checkers).

Found by the erdos-1050 HTTP agent at 12:49:05Z. Its speculative crux ``spec-f2b55478`` went out
as graph PR #202 with no ``acknowledged_hazards``, because "I could not know the location strings
in advance". Three and a half minutes later the gate said ``hazard-unacknowledged`` with 14
findings (5 div-zero, 8 nat-sub, 1 off-by-one-range); the agent copied the locations into a second
proposal (#203), which passed, and #202 stayed open and red beside it. Its wish: "a way to learn
hazard findings *before* opening a PR".

Mechanism: step 6 runs ``opn-hazards`` in the sandbox; the service has no Lean. But the checkers
(``gate/lean/OpnGate/Hazards*.lean``) import only ``Lean``, so, as witness mode inlines
``WitnessType.lean`` (F13-T14), the service inlines them after the statement with a few lines that
ask them one question and log the gate's own finding shape on one tagged info line.

Ruling D8 (Mike, 2026-09-24): ``POST /proposals/variant`` and ``/speculative`` run the target's
checkers first and refuse ``422 hazard-unacknowledged``, in the gate's own diagnostic shape, for
any finding the proposal's ``acknowledged_hazards`` does not cover; if the checker cannot answer the
proposal opens as today and step 6 decides. ``/check`` answers the findings in mode ``hazards``.

#202's own text is not in the tester's log; ``STATEMENT`` below has its shape (a division by a
natural-number difference), and the replies are what ``opn-hazards`` prints for such a statement.
Whether the inlined program *is* the gate's checker is the lean tier's question
(``gate/tests/test_hazards_through_axle_text_lean.py``).
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import dataclass, field
from typing import Any

import pytest
import samples
from api_fakes import AXLE_OKAY, AxleCall, FakeAxle, Harness, make_harness
from mcp_client import TARGET, McpClient
from test_finding_witness_preflight import PIN, token

from opn_api import checks
from opn_api.axle import AxleAnswer, AxleError
from opn_gate import schemas
from opn_gate.steps import hazards as gate_hazards

LEAN = schemas.SCHEMAS_DIR.parent / "lean"
STATEMENT = (
    "import Mathlib\n\n"
    "theorem Opn.erdos_1050_rem :\n"
    "    ∀ n m : ℕ, n < m → (0 : ℚ) < 1 / (2 ^ (m - n) - 3) := by\n"
    "  sorry\n"
)
WITNESS = "import Mathlib\n\ntheorem witness : ∃ (n m : ℕ), n < m := ⟨0, 1, by decide⟩\n"
DIV = {
    "checker": "div-zero",
    "location": "1 / (2 ^ (m - n) - 3)",
    "message": "division by a divisor that is not syntactically non-zero: Lean's / and % are "
    "total and give a junk value at 0",
}
SUB = {
    "checker": "nat-sub",
    "location": "m - n",
    "message": "subtraction on ℕ truncates at 0: a - b is 0 whenever b ≥ a",
}
CHECKERS = ["div-zero", "nat-sub"]
WITNESS_MATCH = {
    **AXLE_OKAY,
    "lean_messages": {
        "errors": [],
        "warnings": [],
        "infos": [
            f"-:9:0-9:8: info: {checks.WITNESS_TAG} "
            + json.dumps({"expected": "X", "given": "X", "matches": True})
        ],
    },
}


def tag() -> str:
    return str(getattr(checks, "HAZARDS_TAG", "OPN-HAZARDS"))


def found(*findings: dict[str, str], checkers: list[str] = CHECKERS) -> dict[str, Any]:
    """The body the hosted checker answers when the hazard program ran: one tagged info line."""
    doc = {"checkers": checkers, "findings": list(findings), "capped": False}
    return {
        **AXLE_OKAY,
        "lean_messages": {
            "errors": [],
            "warnings": [],
            "infos": [f"-:70:0-70:8: info: {tag()} {json.dumps(doc, ensure_ascii=False)}"],
        },
    }


@dataclass
class RoutingAxle(FakeAxle):
    """Answers a hazard program from ``hazards`` and anything else from ``replies``: the two
    pre-flights run side by side, so their order of arrival is not the order of the replies."""

    hazards: list[dict[str, Any] | AxleError] = field(default_factory=list)
    barrier: threading.Barrier | None = None

    def check(self, content: str, *, environment: str, timeout_s: float) -> AxleAnswer:
        if self.barrier is not None:
            self.barrier.wait()
        if tag() in content and "run_meta" in content and "OpnGate.Hazards" in content:
            self.calls.append(AxleCall("check", content, environment, timeout_s))
            reply = self.hazards.pop(0) if self.hazards else AXLE_OKAY
            if isinstance(reply, AxleError):
                raise reply
            return AxleAnswer(body=reply, request_id="fake-hazards", latency_ms=1)
        return super().check(content, environment=environment, timeout_s=timeout_s)


def harness(
    *hazard_replies: Any, checkers: list[str] = CHECKERS, witness: Any = WITNESS_MATCH, **axle: Any
) -> Harness:
    fake = RoutingAxle(replies=[witness], hazards=list(hazard_replies), **axle)
    h = make_harness(axle=fake)
    h.githost.files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(mathlib_sha=PIN, hazard_checkers=checkers)
    )
    h.context.files.clear()
    return h


def speculative(h: Harness, **extra: Any) -> Any:
    body = {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS, **extra}
    return h.client.post("/proposals/speculative", json=body, headers=h.auth(token(h)))


def variant(h: Harness, **extra: Any) -> Any:
    body = {
        "target_id": TARGET,
        "statement": STATEMENT,
        "witness": WITNESS,
        "relation": "related",
        **extra,
    }
    return h.client.post("/proposals/variant", json=body, headers=h.auth(token(h)))


def hazard_calls(h: Harness) -> list[AxleCall]:
    return [c for c in h.axle.calls if "OpnGate.Hazards" in c.content and "run_meta" in c.content]


def ack(finding: dict[str, str], why: str = "the divisor is odd, so never zero") -> dict[str, str]:
    return {"checker": finding["checker"], "location": finding["location"], "justification": why}


# --- the program is the gate's --------------------------------------------------------------------


def gate_sources() -> dict[str, str]:
    """Every checker file the gate's ``opn-hazards`` is built from, import lines removed."""
    files = [
        LEAN / "OpnGate" / "Hazards.lean",
        *sorted((LEAN / "OpnGate" / "Hazards").glob("*.lean")),
    ]
    return {
        str(p.relative_to(LEAN)): re.sub(
            r"^import\s+\S+[ \t]*$", "", p.read_text("utf-8"), flags=re.M
        ).strip("\n")
        for p in files
    }


def test_the_program_sent_is_the_gates_own_source() -> None:
    """Each checker file, byte for byte (by hash) as the gate builds it, is in the text sent, and
    so is ``HazardsMain``'s registry: the network restates no checker."""
    compose = getattr(checks, "hazards_text", None)
    assert compose is not None, "checks.hazards_text"
    text = compose(STATEMENT, "Opn.erdos_1050_rem", CHECKERS)
    for name, source in gate_sources().items():
        digest = hashlib.sha256(source.encode()).hexdigest()
        assert source in text, f"{name} ({digest[:12]}) is not in the program"
    registry = re.search(
        r"#\[[^\]]*\]",
        (LEAN / "OpnGate" / "HazardsMain.lean").read_text("utf-8").split("def registry")[1],
    )
    assert registry is not None and registry.group(0) in text
    assert text.index("theorem Opn.erdos_1050_rem") < text.index("namespace OpnGate.Hazards")
    assert "getConstInfo `Opn.erdos_1050_rem" in text
    assert json.dumps(CHECKERS) in text  # exactly the ids asked for


def test_the_deployed_package_carries_the_files_the_program_reads() -> None:
    """Package what the code *reads* (2026-09-09): the api-deploy workflow copies each file the
    program inlines, its package check names each, and a change to any of them deploys."""
    workflow = (schemas.SCHEMAS_DIR.parents[1] / ".github/workflows/api-deploy.yml").read_text(
        "utf-8"
    )
    for name in [*gate_sources(), "OpnGate/HazardsMain.lean"]:
        assert f"lean/{name}" in workflow, name
    assert (
        "cp gate/lean/OpnGate/Hazards.lean" in workflow
        or "cp -R gate/lean/OpnGate/Hazards" in workflow
    )
    assert '- "gate/lean/OpnGate/Hazards' in workflow


# --- the pre-flight on a proposal -----------------------------------------------------------------


def test_an_unacknowledged_div_zero_is_refused_before_a_pull_request_opens() -> None:
    h = harness(found(DIV, SUB))
    r = speculative(h, acknowledged_hazards=[ack(SUB, "m > n by hypothesis")])
    assert r.status_code == 422, r.text
    doc = r.json()
    assert doc["error"] == "hazard-unacknowledged", r.text
    details = doc["details"]
    # The gate's own diagnostic shape (steps/hazards.py HazardsStep): findings, acknowledged,
    # checkers — plus the call's log id.
    assert details["findings"] == [DIV]
    assert details["acknowledged"] == [ack(SUB, "m > n by hypothesis")]
    assert details["checkers"] == CHECKERS
    assert h.store.checks[details["log_id"]].mode == "hazards"
    assert "div-zero at 1 / (2 ^ (m - n) - 3)" in doc["message"]
    assert h.githost.pushes == [] and h.githost.pulls == []


def test_an_acknowledged_finding_opens() -> None:
    h = harness(found(DIV, SUB))
    r = speculative(h, acknowledged_hazards=[ack(DIV), ack(SUB, "m > n by hypothesis")])
    assert r.status_code == 201, r.text
    assert r.json()["hazards_preflight"] == "clear"
    assert r.json()["witness_preflight"] == "matched"
    assert len(h.githost.pulls) == 1


def test_an_empty_justification_acknowledges_nothing() -> None:
    """The gate's own rule (``evaluate``): an acknowledgment must say why."""
    h = harness(found(DIV))
    r = variant(h, acknowledged_hazards=[{**ack(DIV), "justification": " "}])
    assert (r.status_code, r.json()["error"]) == (422, "hazard-unacknowledged"), r.text


def test_the_variant_route_refuses_too() -> None:
    h = harness(found(DIV))
    r = variant(h)
    assert (r.status_code, r.json()["error"]) == (422, "hazard-unacknowledged"), r.text
    assert h.githost.pulls == []


def test_only_the_targets_checkers_run() -> None:
    h = harness(found(SUB, checkers=["nat-sub"]), checkers=["nat-sub"])
    r = speculative(h, acknowledged_hazards=[ack(SUB)])
    assert r.status_code == 201, r.text
    (sent,) = hazard_calls(h)
    assert json.dumps(["nat-sub"]) in sent.content
    assert json.dumps(CHECKERS) not in sent.content

    none = harness(checkers=[])
    r = speculative(none)
    assert r.status_code == 201, r.text
    assert r.json()["hazards_preflight"] == "clear"
    assert hazard_calls(none) == []  # nothing to ask, nothing spent


def test_axle_unavailable_opens_as_today() -> None:
    """Down, out of time, or no verdict: step 6 remains the authority."""
    for reply, outcome in (
        (AxleError("AXLE check returned 502", status=502), "unavailable"),
        ({"error": "timeout", "error_type": "LeanTimeout", "info": {}}, "unavailable"),
        ({**AXLE_OKAY, "okay": False}, "inconclusive"),  # the program never ran
    ):
        h = harness(reply)
        r = speculative(h)
        assert r.status_code == 201, (outcome, r.text)
        assert r.json()["hazards_preflight"] == outcome
        assert len(h.githost.pulls) == 1


def test_the_two_pre_flights_run_side_by_side() -> None:
    """Both within the one budget the function has before its pull request (F13-T16): the
    hazard call and the witness call are in flight at once, never one after the other."""
    h = harness(found(), barrier=threading.Barrier(2, timeout=5))
    r = speculative(h)
    assert r.status_code == 201, r.text
    assert len(h.axle.calls) == 2
    assert all(c.timeout_s == checks.PREFLIGHT_TIMEOUT_S for c in h.axle.calls)


def test_the_pre_flight_is_charged_and_logged_as_a_check() -> None:
    h = harness(found())
    r = speculative(h)
    assert r.status_code == 201, r.text
    modes = sorted(record.mode for record in h.store.checks.values())
    assert modes == ["hazards", "witness"]


# --- POST /check, mode hazards --------------------------------------------------------------------


def test_check_hazards_mode_answers_the_findings() -> None:
    h = harness(found(DIV, SUB))
    r = h.client.post(
        "/check", json={"target_id": TARGET, "mode": "hazards", "statement": STATEMENT}
    )
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["hazards"] == {"checkers": CHECKERS, "findings": [DIV, SUB], "capped": False}
    assert doc["lint"] == []  # a statement is not a proof
    (sent,) = hazard_calls(h)
    assert "getConstInfo `Opn.erdos_1050_rem" in sent.content
    # The answer is what a proposer pastes: each finding's checker and location, as the gate
    # matches them (steps/hazards.py evaluate).
    acks = [ack(f) for f in doc["hazards"]["findings"]]
    ev = gate_hazards.evaluate(
        gate_hazards.findings_from(doc["hazards"]),
        gate_hazards.acknowledgments_from({"acknowledged_hazards": acks}),
    )
    assert ev.unacknowledged == ()


def test_check_hazards_mode_takes_content_nowhere() -> None:
    h = harness()
    r = h.client.post(
        "/check",
        json={"target_id": TARGET, "mode": "hazards", "statement": STATEMENT, "content": WITNESS},
    )
    assert (r.status_code, r.json()["error"]) == (400, "content-not-used"), r.text
    r = h.client.post("/check", json={"target_id": TARGET, "mode": "hazards"})
    assert (r.status_code, r.json()["error"]) == (400, "node-id-required"), r.text
    assert h.axle.calls == []


def test_the_mcp_tool_offers_the_mode() -> None:
    from opn_api.mcp.server import BY_NAME  # noqa: PLC0415

    tool = BY_NAME["check_lean"]
    assert "hazards" in tool.input_schema["properties"]["mode"]["enum"]
    assert "hazards" in tool.description


def test_mcp_propose_speculative_node_carries_the_refusal() -> None:
    h = harness(found(DIV))
    bearer = token(h)
    with h.client:
        out = McpClient(h).failed(
            "propose_speculative_node",
            {"target_id": TARGET, "stmt": STATEMENT, "witness": WITNESS},
            token=bearer,
        )
    assert out["status"] == 422 and out["body"]["error"] == "hazard-unacknowledged"
    assert out["body"]["details"]["findings"] == [DIV]
    assert h.githost.pulls == []


@pytest.mark.parametrize("name", ["propose_speculative_node", "propose_variant"])
def test_the_mcp_descriptions_name_the_refusal(name: str) -> None:
    from opn_api.mcp.server import BY_NAME  # noqa: PLC0415

    assert "hazard-unacknowledged" in BY_NAME[name].description
