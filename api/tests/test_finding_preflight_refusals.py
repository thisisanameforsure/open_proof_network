# ruff: noqa: RUF001 — the fixtures are Lean source, with its double-struck letters
"""F13-T23: no pull request for what the service can refuse first, part two (the T21 audit's
Q-a, Q-b, Q-c and the same-second append name).

The owner's principle (2026-09-24): "we shouldn't get a pull request at all in these cases — it
should be an error sent back to the user, like reusing theorems, not compiling etc." The F13-T21
audit (``engineering/evidence/F13/task-21-audit.md``) left four ways a pull request still opened
only for the gate to refuse it:

* **Q-a** a proposed statement that does not compile. The witness program never runs, so the
  pre-flight answered ``inconclusive`` and the pull request opened; admission then refused it
  ``statement-elaboration``. Now: when the checker answers ``okay: false`` and one of Lean's
  errors sits on a line of the statement part of the text the service composed (its header, the
  Defs and Context inlined into it, the statement itself), the proposal is refused ``422
  statement-fails`` with those errors. An error anywhere else, or none named, is not the
  statement's, and a checker that cannot answer is never a refusal.
* **Q-b** a witness resting on ``sorryAx`` (through a Context dep's restated ``sorry``) or on an
  axiom outside the target's ``axiom_allowlist``. Step 7 refuses both from the witness's axiom
  set; the program now reports that set (``collectAxioms``, as ``opn-witness-type`` does) and the
  pre-flight refuses ``422 witness-sorry`` / ``422 witness-axiom`` by step 7's own rule.
* **Q-c** a variant's relation proof. The variant route now sends the variant's statement, the
  root's committed statement, ``Relation.lean`` and the gate's own ``expectedRelationType``
  (``ArtifactType.lean``) to the checker and refuses by admission's own codes:
  ``relation-elaboration``, ``relation-sorry``, ``relation-axiom``, ``relation-direction``; a
  ``Relation.lean`` that declares anything but ``theorem relation`` is ``400 relation-decl``
  before any check.
* **the name** two different postmortems (or approach records, or defect claims) from one
  identity in one second share D-13's ``<timestamp>-<pseudonym>`` file name, so the second could
  never merge. Now the second is refused ``409 record-name-taken`` with ``Retry-After``, naming
  the open one.

Each test below was seen red on the defect first (``engineering/evidence/F13/task-23.txt``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import samples
from api_fakes import AXLE_OKAY, AxleCall, FakeAxle, Harness, make_harness
from mcp_client import TARGET, McpClient
from test_finding_check_timeout import LEAN_TIMEOUT
from test_finding_witness_preflight import (
    EXPECTED,
    PIN,
    RIGHT,
    STATEMENT,
    answer,
    token,
)
from test_finding_witness_route_preflight import propose, with_hole

from opn_api import checks
from opn_api.axle import AxleAnswer, AxleError
from opn_gate import schemas

NODES = f"targets/{TARGET}/nodes/"
ROOT = "and-swap-reassoc"  # the fixture graph's root
ROOT_STATEMENT = (
    "import Mathlib\n\n"
    "theorem Opn.erdos_402 :\n"
    "    ∀ (A : Finset ℕ), 0 ∉ A → A.Nonempty →\n"
    "      ∃ᵉ (a ∈ A) (b ∈ A), a.gcd b ≤ (a / A.card : ℚ) := by\n"
    "  sorry\n"
)
RELATION = (
    "import Mathlib\n\ntheorem relation :\n"
    "    (∀ (A : Finset ℕ), 0 ∉ A → A.Nonempty →\n"
    "      ∃ᵉ (a ∈ A) (b ∈ A), a.gcd b ≤ (a / A.card : ℚ)) →\n"
    "    (∀ (A : Finset ℕ), 0 ∉ A → ∀ x ∈ A, A.card ≤ x.minFac →\n"
    "      ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ)) := by\n"
    "  intro h A hA x hx _\n  exact h A hA ⟨x, hx⟩\n"
)
#: An error on line 3 of the text sent: the statement part, whatever is inlined into it.
STATEMENT_ERROR = "-:3:8-3:20: error: unknown identifier 'Finset.crad'"
#: An error far past any statement part the fixtures compose.
LATE_ERROR = "-:400:2-400:9: error: unsolved goals"


def tag() -> str:
    return str(getattr(checks, "RELATION_TAG", "OPN-RELATION"))


def failing(*errors: str, program: dict[str, Any] | None = None) -> dict[str, Any]:
    """``okay: false`` with Lean's errors, and the witness program's line when it ran."""
    body = answer(program, okay=False)
    body["lean_messages"] = {**body["lean_messages"], "errors": list(errors)}
    return body


def with_axioms(*axioms: str, matches: bool = True) -> dict[str, Any]:
    """The witness program's answer once it reports the witness's axioms (Q-b)."""
    return answer(
        {"expected": EXPECTED, "given": EXPECTED, "matches": matches, "axioms": list(axioms)}
    )


def related(
    *, matches: bool = True, axioms: tuple[str, ...] = ("propext",), okay: bool = True
) -> dict[str, Any]:
    doc = {"expected": "V → R", "declared": "R → V", "matches": matches, "axioms": list(axioms)}
    return {
        **AXLE_OKAY,
        "okay": okay,
        "lean_messages": {
            "errors": [],
            "warnings": [],
            "infos": [f"-:90:0-90:8: info: {tag()} {json.dumps(doc, ensure_ascii=False)}"],
        },
    }


@dataclass
class RoutingAxle(FakeAxle):
    """Answers a relation program from ``relations`` and anything else from ``replies``: the
    pre-flights run side by side, so their order of arrival is not the order of the replies."""

    relations: list[dict[str, Any] | AxleError] = field(default_factory=list)

    def check(self, content: str, *, environment: str, timeout_s: float) -> AxleAnswer:
        if tag() in content and "run_meta" in content and "`relation" in content:
            self.calls.append(AxleCall("check", content, environment, timeout_s))
            reply = self.relations.pop(0) if self.relations else AXLE_OKAY
            if isinstance(reply, AxleError):
                raise reply
            return AxleAnswer(body=reply, request_id="fake-relation", latency_ms=1)
        return super().check(content, environment=environment, timeout_s=timeout_s)


def harness(*replies: Any, relations: tuple[Any, ...] = ()) -> Harness:
    """The fixture graph pinned to a hosted Mathlib, the root's statement committed, one dep with a
    sorry statement, and a checker answering witness calls from ``replies``."""
    h = make_harness(axle=RoutingAxle(replies=list(replies), relations=list(relations)))
    files = h.githost.files
    files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(mathlib_sha=PIN)
    )
    files[f"{NODES}{ROOT}/Statement.lean"] = ROOT_STATEMENT.encode()
    files[f"{NODES}and-reassoc/Statement.lean"] = (
        b"theorem OpnProp.and_reassoc : True := by\n  sorry\n"
    )
    h.context.files.clear()
    return h


def variant(h: Harness, **extra: Any) -> Any:
    body = {
        "target_id": TARGET,
        "statement": STATEMENT,
        "witness": RIGHT,
        "relation": "partial",
        "relation_proof": RELATION,
        **extra,
    }
    return h.client.post("/proposals/variant", json=body, headers=h.auth(token(h)))


def speculative(h: Harness, **extra: Any) -> Any:
    body = {"target_id": TARGET, "statement": STATEMENT, "witness": RIGHT, **extra}
    return h.client.post("/proposals/speculative", json=body, headers=h.auth(token(h)))


def relation_calls(h: Harness) -> list[AxleCall]:
    return [c for c in h.axle.calls if tag() in c.content and "`relation" in c.content]


def refused(r: Any, status: int, code: str) -> None:
    """The status first, so a pull request that opened reads as that, not as a missing key."""
    assert r.status_code == status, r.text
    assert r.json()["error"] == code, r.text


def opened_nothing(h: Harness) -> None:
    assert h.githost.pushes == [] and h.githost.pulls == []


# --- Q-a: a statement that does not compile


def test_a_statement_that_does_not_compile_opens_no_pull_request() -> None:
    h = harness(failing(STATEMENT_ERROR))
    r = speculative(h)
    assert r.status_code == 422, r.text
    doc = r.json()
    assert doc["error"] == "statement-fails"
    assert doc["details"]["errors"] == [STATEMENT_ERROR]
    assert doc["details"]["log_id"] in h.store.checks
    opened_nothing(h)


def test_the_variant_route_refuses_it_too() -> None:
    h = harness(failing(STATEMENT_ERROR))
    r = variant(h, relation="related", relation_proof=None)
    refused(r, 422, "statement-fails")
    opened_nothing(h)


def test_only_the_statements_own_errors_are_named() -> None:
    """An error past the statement part is the witness's or the program's, not the statement's:
    the refusal carries the statement's errors, and a body with only later errors is not a
    statement refusal."""
    h = harness(failing(STATEMENT_ERROR, LATE_ERROR))
    r = speculative(h)
    refused(r, 422, "statement-fails")
    assert r.json()["details"]["errors"] == [STATEMENT_ERROR]
    h = harness(failing(LATE_ERROR))
    r = speculative(h)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "inconclusive"


def test_a_statement_error_outranks_the_witness_verdict() -> None:
    """A statement whose type has an error still declares a theorem (Lean recovers with a sorry),
    so the program can run and say ``matches``; the statement is what failed."""
    program = {"expected": EXPECTED, "given": EXPECTED, "matches": True}
    h = harness(failing(STATEMENT_ERROR, program=program))
    r = speculative(h)
    refused(r, 422, "statement-fails")


def test_a_checker_that_cannot_answer_is_still_no_refusal() -> None:
    for reply in (LEAN_TIMEOUT, AxleError("AXLE check returned 502", status=502)):
        h = harness(reply)
        r = speculative(h)
        assert r.status_code == 201, r.text
        assert r.json()["witness_preflight"] == "unavailable"
    h = harness(failing())  # okay: false and no Lean error to name
    r = speculative(h)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "inconclusive"


def test_the_hole_witness_route_refuses_a_hole_statement_that_does_not_compile() -> None:
    """Admission of the hole elaborates its statement; a witness cannot mend a statement."""
    h = with_hole(harness(failing(STATEMENT_ERROR)))
    r = propose(h, RIGHT)
    refused(r, 422, "statement-fails")
    opened_nothing(h)


# --- Q-b: the witness's axioms


def test_a_witness_resting_on_sorry_through_its_context_opens_no_pull_request() -> None:
    h = harness(with_axioms("propext", "sorryAx"))
    r = speculative(h, deps=["and-reassoc"])
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "witness-sorry"
    assert "sorryAx" in r.json()["details"]["axioms"]
    opened_nothing(h)


def test_a_witness_on_an_axiom_outside_the_allowlist_opens_no_pull_request() -> None:
    h = harness(with_axioms("propext", "Opn.cheat"))
    r = speculative(h)
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "witness-axiom"
    assert r.json()["details"]["axioms"] == ["Opn.cheat"]
    opened_nothing(h)


def test_the_allowlist_is_the_targets() -> None:
    h = harness(with_axioms("propext", "Classical.choice", "Quot.sound"))
    r = speculative(h)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "matched"


def test_an_answer_without_axioms_is_read_as_before() -> None:
    h = harness(answer({"expected": EXPECTED, "given": EXPECTED, "matches": True}))
    r = speculative(h)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "matched"


def test_the_hole_witness_route_reads_the_axioms_too() -> None:
    h = with_hole(harness(with_axioms("sorryAx")))
    r = propose(h, RIGHT)
    refused(r, 422, "witness-sorry")
    opened_nothing(h)


def test_the_program_asks_for_the_witness_axioms() -> None:
    text = checks.witness_program("Opn.s", has_witness=True)
    assert "collectAxioms `witness" in text


# --- Q-c: the relation proof


def test_a_relation_in_the_wrong_direction_opens_no_pull_request() -> None:
    h = harness(relations=(related(matches=False),))
    r = variant(h)
    assert r.status_code == 422, r.text
    doc = r.json()
    assert doc["error"] == "relation-direction"
    assert (doc["details"]["expected"], doc["details"]["declared"]) == ("V → R", "R → V")
    opened_nothing(h)


def test_a_relation_resting_on_sorry_opens_no_pull_request() -> None:
    h = harness(relations=(related(axioms=("propext", "sorryAx")),))
    r = variant(h)
    refused(r, 422, "relation-sorry")
    opened_nothing(h)


def test_a_relation_on_an_axiom_outside_the_allowlist_opens_no_pull_request() -> None:
    h = harness(relations=(related(axioms=("Opn.cheat",)),))
    r = variant(h)
    refused(r, 422, "relation-axiom")
    assert r.json()["details"]["axioms"] == ["Opn.cheat"]
    opened_nothing(h)


def test_a_relation_proof_that_does_not_compile_opens_no_pull_request() -> None:
    """The error is placed on the relation proof's own first line in the text that was sent."""
    h = harness(relations=(AXLE_OKAY,))
    r = variant(h)
    assert r.status_code == 201, r.text  # the fake's default: no verdict, so inconclusive
    (sent,) = relation_calls(h)
    line = sent.content[: sent.content.index("theorem relation")].count("\n") + 1
    error = f"-:{line}:8-{line}:16: error: type mismatch"
    body = related(okay=False)
    body["lean_messages"] = {**body["lean_messages"], "errors": [error]}
    h = harness(relations=(body,))
    r = variant(h)
    refused(r, 422, "relation-elaboration")
    assert r.json()["details"]["errors"] == [error]
    opened_nothing(h)


def test_a_right_relation_opens_and_the_receipt_says_so() -> None:
    h = harness(relations=(related(),))
    r = variant(h)
    assert r.status_code == 201, r.text
    assert r.json()["relation_preflight"] == "matched"
    (sent,) = relation_calls(h)
    # The variant's statement, the root's committed statement and the relation proof, with the
    # gate's own expected-relation program: nothing the checker cannot import.
    assert "theorem Opn.erdos_402_minFac" in sent.content
    assert sent.content.count("theorem Opn.erdos_402 :") == 1
    assert "def expectedRelationType" in sent.content
    assert "import Nodes." not in sent.content
    assert "getConstInfo `Opn.erdos_402_minFac" in sent.content
    assert "getConstInfo `Opn.erdos_402\n" in sent.content


def test_a_checker_that_cannot_answer_lets_the_variant_open() -> None:
    for reply in (LEAN_TIMEOUT, AxleError("AXLE check returned 502", status=502)):
        h = harness(relations=(reply,))
        r = variant(h)
        assert r.status_code == 201, r.text
        assert r.json()["relation_preflight"] == "unavailable"


def test_a_related_variant_sends_no_relation() -> None:
    h = harness()
    r = variant(h, relation="related", relation_proof=None)
    assert r.status_code == 201, r.text
    assert r.json()["relation_preflight"] == "skipped"
    assert relation_calls(h) == []


def test_a_relation_proof_declaring_another_name_is_refused_before_any_check() -> None:
    h = harness()
    r = variant(h, relation_proof=RELATION.replace("theorem relation", "theorem my_relation"))
    refused(r, 400, "relation-decl")
    assert h.axle.calls == []
    opened_nothing(h)


def test_a_relation_proof_with_a_sorry_is_refused_before_any_check() -> None:
    h = harness()
    r = variant(h, relation_proof=RELATION.replace("exact h A hA ⟨x, hx⟩", "sorry"))
    refused(r, 400, "relation-sorry")
    assert h.axle.calls == []


def test_a_root_declared_as_a_dep_is_related_to_through_the_context() -> None:
    """F08-T15's shape: the variant's Context restates the root's theorem, so the text declares it
    once (a second declaration is "already declared") and the program reads that one."""
    h = harness(relations=(related(),))
    graph_path = f"targets/{TARGET}/graph.json"
    doc = json.loads(h.githost.files[graph_path])
    doc["nodes"].append({**doc["nodes"][0], "node_id": ROOT, "status": "ready"})
    h.githost.files[graph_path] = json.dumps(doc).encode()
    h.context.files.clear()
    r = variant(h, deps=[ROOT])
    assert r.status_code == 201, r.text
    assert r.json()["relation_preflight"] == "matched"
    (sent,) = relation_calls(h)
    assert sent.content.count("theorem Opn.erdos_402 :") == 1
    assert "getConstInfo `Opn.erdos_402\n" in sent.content


def test_the_hazard_pre_flight_refuses_a_failing_statement_too() -> None:
    """The hazard program runs over the same statement part; its answer is read the same way."""
    from test_finding_hazards_preflight import CHECKERS  # noqa: PLC0415
    from test_finding_hazards_preflight import harness as hazard_harness  # noqa: PLC0415
    from test_finding_hazards_preflight import speculative as hazard_speculative  # noqa: PLC0415

    h = hazard_harness(failing(STATEMENT_ERROR), checkers=CHECKERS, witness=AXLE_OKAY)
    r = hazard_speculative(h)
    refused(r, 422, "statement-fails")
    opened_nothing(h)


def test_mcp_propose_variant_carries_the_relation_refusal() -> None:
    h = harness(relations=(related(matches=False),))
    bearer = token(h)
    with h.client:
        out = McpClient(h).failed(
            "propose_variant",
            {
                "target_id": TARGET,
                "stmt": STATEMENT,
                "witness": RIGHT,
                "relation": "partial",
                "relation_proof": RELATION,
            },
            token=bearer,
        )
    assert out["status"] == 422 and out["body"]["error"] == "relation-direction"
    assert h.githost.pulls == []


# --- the same-second file name -------------------------------------------------------------------


def postmortem_body(route: str) -> dict[str, Any]:
    doc = samples.postmortem(route=route)
    del doc["schema"]
    del doc["node"]
    return {"node_id": "and-reassoc", "yaml": doc}


def test_a_second_postmortem_in_the_same_second_is_refused_not_opened() -> None:
    h = harness()
    bearer = token(h)
    first = h.client.post("/postmortems", json=postmortem_body("one"), headers=h.auth(bearer))
    assert first.status_code == 201, first.text
    second = h.client.post("/postmortems", json=postmortem_body("two"), headers=h.auth(bearer))
    assert second.status_code == 409, second.text
    doc = second.json()
    assert doc["error"] == "record-name-taken"
    assert doc["details"]["path"] == first.json()["path"]
    assert doc["details"]["pr_number"] == first.json()["pr_number"]
    assert second.headers["Retry-After"] == "1"
    assert len(h.githost.pulls) == 1
    h.clock.advance(seconds=1)
    third = h.client.post("/postmortems", json=postmortem_body("two"), headers=h.auth(bearer))
    assert third.status_code == 201, third.text
    assert third.json()["path"] != first.json()["path"]


def test_another_identity_in_the_same_second_has_its_own_name() -> None:
    h = harness()
    alice = token(h)
    bob = h.token_for("code_bob", "bob")
    a = h.client.post("/postmortems", json=postmortem_body("one"), headers=h.auth(alice))
    b = h.client.post("/postmortems", json=postmortem_body("two"), headers=h.auth(bob))
    assert (a.status_code, b.status_code) == (201, 201), (a.text, b.text)


def test_approach_records_are_held_to_the_same_rule() -> None:
    h = harness()
    bearer = token(h)

    def record(route: str) -> dict[str, Any]:
        doc = samples.approach_record(route=route)
        for key in ("schema", "target", "contributor"):
            doc.pop(key, None)
        return {"target_id": TARGET, "record": doc}

    first = h.client.post("/approach-records", json=record("one"), headers=h.auth(bearer))
    assert first.status_code == 201, first.text
    second = h.client.post("/approach-records", json=record("two"), headers=h.auth(bearer))
    refused(second, 409, "record-name-taken")


# --- the program is the gate's, and the package carries it ---------------------------------------


def test_the_relation_program_is_the_gates_own_source() -> None:
    """``WitnessType.lean`` and ``ArtifactType.lean`` byte for byte, import lines aside: the
    network restates no part of admission's ``expectedRelationType``."""
    text = checks.relation_program("Opn.v", "Opn.r", "partial")
    for path in (checks.WITNESS_SOURCE, checks.ARTIFACT_SOURCE):
        source = checks.IMPORT_LINE_RE.sub("", path.read_text("utf-8")).strip("\n")
        assert source in text, path.name
    assert text.index("def expectedWitnessType") < text.index("def expectedRelationType")


def test_the_deployed_package_carries_the_relation_program() -> None:
    """Package what the code *reads* (2026-09-09): copied, checked, and a change to it deploys."""
    workflow = (schemas.SCHEMAS_DIR.parents[1] / ".github/workflows/api-deploy.yml").read_text(
        "utf-8"
    )
    relative = checks.ARTIFACT_SOURCE.relative_to(schemas.SCHEMAS_DIR.parent).as_posix()
    assert relative == "lean/OpnGate/ArtifactType.lean"
    assert f"cp gate/{relative} build/package/{relative}" in workflow
    assert f'"{relative}"' in workflow
    assert f'- "gate/{relative}"' in workflow
