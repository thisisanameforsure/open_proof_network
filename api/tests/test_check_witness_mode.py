"""F13-T14: ``POST /check`` with ``mode: "witness"`` previews the type step 7 will hold a witness
to, and says whether a given witness has it (testers 2026-09-21; asked for by all three).

A witness is one declaration whose type is "exists, over the statement's variables, of the
conjunction of its hypotheses". The gate computes that type with a metaprogram at step 7, and
until now a contributor met it there: a six to twenty minute round to learn a guess was wrong.
The erdos-402 agent copied the shape from another node's witness; the erdos-69 agent filed four
without knowing whether they matched.

The service has no Lean. It sends the hosted checker the node's statement, the witness, and the
gate's own ``WitnessType.lean`` with a few lines that log the answer as one JSON line (probed
live first: ``engineering/evidence/F13/task-14-probe.lean``). These tests are the specification
and were written before the mode existed.
"""

from __future__ import annotations

import json
from typing import Any

from api_fakes import AXLE_OKAY, FakeAxle
from mcp_client import NODE, TARGET
from test_checks import harness_with, post, refused, seed

from opn_api import checks
from opn_gate import schemas

STATEMENT = (
    "import Init\n\ntheorem OpnProp.and_reassoc : ∀ p q : Prop, p ∧ q → q ∧ p := by\n  sorry\n"
)
WITNESS = "theorem witness : ∃ (p : Prop) (q : Prop), p ∧ q := ⟨True, True, trivial, trivial⟩\n"
EXPECTED = "∃ (p : Prop), ∃ (q : Prop), p ∧ q"
GATE_SOURCE = schemas.SCHEMAS_DIR.parent / "lean" / "OpnGate" / "WitnessType.lean"


def answer(payload: dict[str, Any] | None, *, okay: bool = True) -> dict[str, Any]:
    infos = (
        []
        if payload is None
        else [f"-:40:0-40:8: info: {checks.WITNESS_TAG} {json.dumps(payload)}\n"]
    )
    return {
        **AXLE_OKAY,
        "okay": okay,
        "lean_messages": {"errors": [], "warnings": [], "infos": infos},
    }


def call(content: str | None, reply: dict[str, Any]) -> tuple[dict[str, Any], str]:
    h = harness_with(axle=FakeAxle(replies=[reply]))
    seed(h, statement=STATEMENT)
    body: dict[str, Any] = {"target_id": TARGET, "node_id": NODE, "mode": "witness"}
    if content is not None:
        body["content"] = content
    r = post(h, body)
    assert r.status_code == 200, r.text
    (sent,) = h.axle.calls
    assert sent.method == "check"  # the checker's verify mode knows nothing of witnesses
    return r.json(), sent.content


def test_the_mode_needs_a_node() -> None:
    h = harness_with()
    seed(h, statement=STATEMENT)
    refused(
        post(h, {"target_id": TARGET, "mode": "witness", "content": WITNESS}),
        400,
        "node-id-required",
    )


def test_a_matching_witness_is_told_so_with_both_types() -> None:
    doc, _ = call(WITNESS, answer({"expected": EXPECTED, "given": EXPECTED, "matches": True}))
    assert doc["mode"] == "witness" and doc["authoritative"] is False
    assert doc["witness"] == {"expected": EXPECTED, "given": EXPECTED, "matches": True}


def test_a_mismatch_shows_the_type_the_gate_wants() -> None:
    given = "∃ (p : Prop), p"
    doc, _ = call(WITNESS, answer({"expected": EXPECTED, "given": given, "matches": False}))
    assert doc["witness"] == {"expected": EXPECTED, "given": given, "matches": False}


def test_without_a_witness_the_answer_is_the_expected_type_alone() -> None:
    doc, sent = call(None, answer({"expected": EXPECTED, "given": None, "matches": None}))
    assert doc["witness"] == {"expected": EXPECTED, "given": None, "matches": None}
    assert "theorem witness" not in sent


def test_the_checker_is_sent_the_statement_the_witness_and_the_gates_own_metaprogram() -> None:
    _, sent = call("import Init\n\n" + WITNESS, answer(None))
    assert sent.startswith("import Init\nimport Lean\n"), sent[:60]  # one header, the statement's
    assert sent.count("import ") == 2  # the witness's own import lines are dropped
    statement_at = sent.index("theorem OpnProp.and_reassoc")
    witness_at = sent.index("theorem witness")
    program_at = sent.index("def expectedWitnessType")
    assert statement_at < witness_at < program_at
    # One source of truth: the text sent is the file step 7 is built from, not a copy of it.
    body = "\n".join(
        line
        for line in GATE_SOURCE.read_text("utf-8").splitlines()
        if not line.startswith("import ")
    )
    assert body.strip() in sent
    assert "`OpnProp.and_reassoc" in sent and checks.WITNESS_TAG in sent


def test_a_witness_is_not_linted_as_a_proof() -> None:
    """The agents' false alarm: ``helper-declarations`` fired on ``theorem witness`` and
    ``imports-differ`` on a witness's header, neither of which the gate holds a witness to."""
    doc, _ = call(
        "import Std\n\n" + WITNESS,
        answer({"expected": EXPECTED, "given": EXPECTED, "matches": True}),
    )
    assert doc["lint"] == []


def test_a_witness_that_does_not_elaborate_has_no_verdict() -> None:
    doc, _ = call("theorem witness : Nonsense := 1\n", answer(None, okay=False))
    assert doc["witness"] is None and doc["okay"] is False


def test_the_other_modes_carry_no_witness_key_they_cannot_fill() -> None:
    h = harness_with()
    seed(h, statement=STATEMENT)
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": WITNESS})
    assert "witness" not in r.json()


def test_the_deployed_package_carries_the_file_the_mode_reads() -> None:
    """Package what the code *reads* (2026-09-09): the Lambda zip once shipped ``opn_gate``
    without ``gate/schemas`` and every validating route answered 500 while health stayed green.
    ``WITNESS_SOURCE`` resolves beside the schemas, so the deploy must copy it there, check it is
    there, and run when it changes."""
    workflow = (schemas.SCHEMAS_DIR.parents[1] / ".github/workflows/api-deploy.yml").read_text(
        "utf-8"
    )
    relative = GATE_SOURCE.relative_to(schemas.SCHEMAS_DIR.parent).as_posix()
    assert relative == "lean/OpnGate/WitnessType.lean"
    assert f"cp gate/{relative} build/package/{relative}" in workflow
    assert f'"{relative}"' in workflow  # the package check names it
    assert f'- "gate/{relative}"' in workflow  # a change to it deploys


def test_the_mcp_tool_offers_the_mode() -> None:
    from opn_api.mcp.server import BY_NAME  # noqa: PLC0415

    tool = BY_NAME["check_lean"]
    assert tool.input_schema["properties"]["mode"]["enum"] == list(checks.MODES)
    assert tool.input_schema["required"] == ["target_id"]  # content is optional in witness mode
    assert "witness" in tool.description


def test_a_node_with_a_context_and_no_witness_asks_for_the_expected_type_alone() -> None:
    """Found live, minutes after the deploy: on ``erdos-69--h2-v2--h1-v2--h4`` the mode answered
    ``witness: null``, "Unknown constant `witness`". With no content the *inlined Context* was
    taken for the witness, so the program looked one up. The first fixture had no Context to
    inline; this one has the live shape (2026-09-12: keep one fixture with the live shape)."""
    own = f"import Nodes.«{NODE}».Context"
    statement = (
        f"import Init\n{own}\n\ntheorem OpnProp.and_reassoc : ∀ p : Prop, p → p := by\n  sorry\n"
    )
    context = "theorem OpnProp.dep : True := by\n  sorry\n"
    h = harness_with(
        axle=FakeAxle(replies=[answer({"expected": "X", "given": None, "matches": None})])
    )
    seed(h, statement=statement)
    h.githost.files[f"targets/{TARGET}/nodes/{NODE}/Context.lean"] = context.encode()
    h.context.files.clear()
    r = post(h, {"target_id": TARGET, "node_id": NODE, "mode": "witness"})
    assert r.status_code == 200, r.text
    (sent,) = h.axle.calls
    assert "getConstInfo `witness" not in sent.content
    assert sent.content.count("theorem OpnProp.dep") == 1  # the Context, inlined once
    assert r.json()["witness"] == {"expected": "X", "given": None, "matches": None}
