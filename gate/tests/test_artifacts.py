"""F07-T2: D-12's artifact types and the offload rule (R4, R5; AC4, AC5, AC6).

The type work is Lean's (``test_artifacts_lean.py`` drives the real metaprogram against goldens);
what is decided here is what the gate does with the answer, which is where the rules live.
"""

from __future__ import annotations

import pytest
from fakes import artifact_result

from opn_gate import layout
from opn_gate.diagnostic import Diagnostic
from opn_gate.steps import artifact as art

STMT = "OpnProp.and_swap"
S = "∀ (p q : Prop), p ∧ q → q ∧ p"
NOT_S = f"¬{S}"
W = "∃ p q, p ∧ q"


def decide(kind: art.Kind, **overrides: object) -> list[Diagnostic]:
    doc = artifact_result(kind=kind, **overrides).doc  # type: ignore[arg-type]
    return art.check(art.Artifact.of(kind, doc))


def codes(problems: list[Diagnostic]) -> list[str]:
    return [d.code for d in problems]


# --- AC4, AC5: the type each artifact must declare -----------------------------------------------


def test_counterexample_type() -> None:
    """AC4: the negation of a different statement fails; the negation of this one passes."""
    wrong = decide(
        "counterexample",
        decl=f"{STMT}_refuted",
        expected=NOT_S,
        declared="¬∀ (p q : Prop), p ∧ q → p ∧ q",
        matches=False,
    )
    assert codes(wrong) == ["artifact-type-mismatch"]
    assert "counterexample" in wrong[0].message
    assert wrong[0].details["expected"] == NOT_S

    right = decide("counterexample", decl=f"{STMT}_refuted", expected=NOT_S, matches=True)
    assert right == []


def test_vacuity_type() -> None:
    """AC5: a certificate of the wrong type fails; ¬W passes."""
    wrong = decide(
        "vacuity",
        decl=f"{STMT}_vacuous",
        expected=f"¬{W}",
        declared="¬∃ p, p",
        matches=False,
    )
    assert codes(wrong) == ["artifact-type-mismatch"]

    right = decide("vacuity", decl=f"{STMT}_vacuous", expected=f"¬{W}", matches=True)
    assert right == []


def test_proof_type_is_the_statement() -> None:
    """R4: a plain proof declares the statement itself; the expected name is unchanged."""
    assert art.expected_decl("proof", STMT) == STMT
    assert art.expected_decl("counterexample", STMT) == f"{STMT}_refuted"
    assert art.expected_decl("vacuity", STMT) == f"{STMT}_vacuous"
    assert art.expected_decl("partial", STMT) == STMT
    assert decide("proof", matches=True) == []


# --- AC6: the offload rule and hole extraction ---------------------------------------------------


def test_offload_rule_and_hole_extraction() -> None:
    """AC6: a single hole whose type is the goal is refused; two honest holes are kept."""
    restated = decide("partial", matches=True, holes=[("restated", S, True)])
    assert "offload-restated-goal" in codes(restated)
    assert restated[0].details["holes"] == ["restated"]

    two = artifact_result(
        kind="partial", matches=True, holes=[("right", "q", False), ("left", "p", False)]
    )
    parsed = art.Artifact.of("partial", two.doc)
    assert art.check(parsed) == []
    assert [(h.name, h.type) for h in parsed.holes] == [("right", "q"), ("left", "p")]
    assert not parsed.is_reduction  # Q1: a reduction is the one-hole case


def test_assembly_that_is_one_hole() -> None:
    """R5: a body that is nothing but a hole decomposes nothing, whatever its type."""
    problems = decide("partial", matches=True, holes=[], unnamed=1, body_is_hole=True)
    assert "offload-whole-goal" in codes(problems)


def test_partial_must_have_holes_and_name_them() -> None:
    """R5: at least one hole, every hole `have`-bound, and no more than the cap."""
    assert codes(decide("partial", matches=True, holes=[])) == ["partial-without-holes"]

    unnamed = decide("partial", matches=True, holes=[("h", "q", False)], unnamed=2)
    assert codes(unnamed) == ["hole-unnamed"]
    assert unnamed[0].details["unnamed"] == 2

    many = [(f"h{i}", "q", False) for i in range(art.MAX_HOLES + 1)]
    over = decide("partial", matches=True, holes=many)
    assert codes(over) == ["too-many-holes"]
    assert over[0].details["cap"] == art.MAX_HOLES

    at_cap = decide("partial", matches=True, holes=many[: art.MAX_HOLES])
    assert at_cap == []


def test_reduction_is_a_one_hole_partial() -> None:
    """Q1: the label is the hole count, and the same checks apply."""
    doc = artifact_result(kind="reduction", matches=True, holes=[("crux", "q", False)]).doc
    reduction = art.Artifact.of("reduction", doc)
    assert art.check(reduction) == []
    assert reduction.is_reduction
    assert reduction.as_dict()["reduction"] is True


def test_a_mismatched_partial_reports_both_problems() -> None:
    """C7: every reason is reported, not just the first — the submitter fixes one round trip."""
    problems = decide("partial", declared="∀ (p q : Prop), p ∧ q → p ∧ q", matches=False, holes=[])
    assert codes(problems) == ["artifact-type-mismatch", "partial-without-holes"]


# --- which artifact a Proof.lean is (R4, Q9) -----------------------------------------------------


@pytest.mark.parametrize(
    ("declared", "kind"),
    [
        (STMT, "proof"),
        (f"{STMT}_refuted", "counterexample"),
        (f"{STMT}_vacuous", "vacuity"),
    ],
)
def test_kind_comes_from_the_declared_name(declared: str, kind: str) -> None:
    """R4, Q9: the file says which artifact it is; the submission block is not consulted."""
    text = f"theorem {declared} : True := trivial\n"
    found, problem = art.declared_kind(STMT, text)
    assert problem is None
    assert found == kind


def test_an_unknown_declaration_is_named() -> None:
    found, problem = art.declared_kind(STMT, "theorem OpnProp.something_else : True := trivial\n")
    assert found is None
    assert problem is not None and problem.code == "artifact-decl-unknown"
    assert "OpnProp.and_swap_refuted" in problem.message

    found, problem = art.declared_kind(STMT, "-- no theorem here\n")
    assert found is None
    assert problem is not None and problem.code == "artifact-shape"


def test_declaration_parsing_respects_namespaces() -> None:
    """The declared name is namespace-qualified, as the statement's is (F00's parser)."""
    text = "namespace OpnProp\ntheorem and_swap_refuted : True := trivial\nend OpnProp\n"
    assert layout.parse_declaration(text) == f"{STMT}_refuted"
    assert art.declared_kind(STMT, text)[0] == "counterexample"


# --- running the metaprogram: every way it can fail to answer (R4, R5; F01-R9's contract) --------

from pathlib import Path  # noqa: E402

from fakes import FakeToolchain, metaprogram_garbage  # noqa: E402
from harness import make_context  # noqa: E402
from scripted import ScriptedToolchain  # noqa: E402

from opn_gate.toolchain import ArtifactRequest, MetaprogramResult  # noqa: E402


def request(kind: art.Kind) -> ArtifactRequest:
    return ArtifactRequest(
        statement=Path("Statement.lean"),
        statement_module="Nodes.«tutorial-and-swap».Statement",
        decl=STMT,
        artifact=Path("Proof.lean"),
        artifact_module="Nodes.«tutorial-and-swap».Proof",
        artifact_decl=art.expected_decl(kind, STMT),
        kind=kind,
    )


def test_a_metaprogram_without_a_verdict_is_named(tmp_path: Path) -> None:
    fake = FakeToolchain(artifact=metaprogram_garbage(exit_code=134, output="Segmentation fault"))
    ctx = make_context(tmp_path, toolchain=fake)
    found, failure = art.run(ctx, fake.resolved, request("counterexample"), "counterexample")
    assert found is None
    assert failure is not None and failure.diagnostic is not None
    assert failure.diagnostic.code == "metaprogram-failed"
    assert failure.diagnostic.details["exit_code"] == 134
    assert "Segmentation fault" in failure.diagnostic.details["output"]
    assert "artifact" not in ctx.data


def test_an_artifact_that_does_not_elaborate_is_named(tmp_path: Path) -> None:
    broken = MetaprogramResult(ok=False, doc={"ok": False, "error": "unknown identifier 'foo'"})
    fake = FakeToolchain(artifact=broken)
    ctx = make_context(tmp_path, toolchain=fake)
    found, failure = art.run(ctx, fake.resolved, request("partial"), "partial")
    assert found is None
    assert failure is not None and failure.diagnostic is not None
    assert failure.diagnostic.code == "artifact-elaboration"
    assert failure.diagnostic.message == "unknown identifier 'foo'"


def test_the_wall_clock_cap_is_a_step_failure(tmp_path: Path) -> None:
    fake = ScriptedToolchain(timeout_on={"artifact_type"})
    ctx = make_context(tmp_path, toolchain=fake)
    found, failure = art.run(ctx, fake.resolved, request("proof"), "proof")
    assert found is None
    assert failure is not None and failure.diagnostic is not None
    assert failure.diagnostic.code == "timeout"
    assert f"{ctx.wallclock_s:g}s" in failure.diagnostic.message


def test_a_report_with_problems_fails_on_the_first_and_lists_them_all(tmp_path: Path) -> None:
    """The step names the first problem (F00-R7) and carries every other one in ``problems``,
    and the parsed artifact is recorded in the context either way."""
    report = artifact_result(
        kind="partial",
        declared="∀ (p q : Prop), p ∧ q → p ∧ q",
        matches=False,
        holes=[("restated", S, True)],
        unnamed=1,
    )
    fake = FakeToolchain(artifact=report)
    ctx = make_context(tmp_path, toolchain=fake)
    found, failure = art.run(ctx, fake.resolved, request("partial"), "partial")
    assert found is not None and failure is not None and failure.diagnostic is not None
    assert failure.diagnostic.code == "artifact-type-mismatch"
    assert failure.diagnostic.details["expected"] == S
    assert len(failure.diagnostic.details["problems"]) == 3
    assert ctx.data["artifact"] == found.as_dict()
    assert ctx.data["artifact"]["holes"][0]["name"] == "restated"


def test_an_empty_report_never_passes() -> None:
    """Fail closed: a report the parser cannot read anything from is a type mismatch and a
    hole-less partial, never a pass."""
    empty = art.Artifact.of("partial", {})
    assert not empty.matches and empty.holes == () and empty.axioms == ()
    assert codes(art.check(empty)) == ["artifact-type-mismatch", "partial-without-holes"]
    proof = art.Artifact.of("proof", {"holes": ["not", "dicts", 3]})
    assert proof.holes == ()
    assert codes(art.check(proof)) == ["artifact-type-mismatch"]


def test_a_hole_without_a_closed_type_falls_back_to_its_local_type() -> None:
    """An older metaprogram report without ``closed_type`` still yields a hole; the local type
    stands in, so nothing is silently dropped."""
    hole = art.Hole.of({"name": "h", "type": "q"})
    assert hole.closed_type == "q" and not hole.defeq_goal
    assert art.Hole.of({}).name == "" and art.Hole.of({}).type == ""
