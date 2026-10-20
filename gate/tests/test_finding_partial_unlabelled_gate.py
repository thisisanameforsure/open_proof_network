"""F29-T2 / AC8 (R5; D-12 v3.44): step 4 refuses a partial that does not name its work.

A partial names its approach, its licence and each hole's label and claim in its own comments
(``opn_gate.labels``). The service refuses one that does not before any precheck (F29-T3); the
gate refuses it at step 4 by the same name, ``partial-unlabelled``, against the *extractor's*
hole names rather than the text scan's, so a hand-opened pull request meets the same rule and a
hole the scan did not see is still held to it. A reduction is never asked (the brief's rule: a
partial only); a proof, counterexample or vacuity certificate has no holes to name.
"""

from __future__ import annotations

from pathlib import Path

from fakes import FakeToolchain, artifact_result
from harness import make_context

from opn_gate import codes, labels
from opn_gate.steps import artifact as art
from opn_gate.toolchain import ArtifactRequest

STMT = "OpnProp.and_swap"
S = "∀ (p q : Prop), p ∧ q → q ∧ p"

UNLABELLED = """theorem OpnProp.and_swap : ∀ (p q : Prop), p ∧ q → q ∧ p := by
  intro p q h
  have right : q := sorry
  have left : p := sorry
  exact ⟨right, left⟩
"""

LABELLED = """theorem OpnProp.and_swap : ∀ (p q : Prop), p ∧ q → q ∧ p := by
  -- approach: take the conjunction apart and reassemble it the other way round
  -- licence: CC-BY-4.0
  intro p q h
  -- label: the right half
  -- claim: $q$
  -- The second conjunct of the hypothesis.
  have right : q := sorry
  -- label: the left half
  -- claim: $p$
  have left : p := sorry
  exact ⟨right, left⟩
"""

TWO_HOLES = [("right", "q", False), ("left", "p", False)]


def parsed(kind: art.Kind, holes: list[tuple[str, str, bool]]) -> art.Artifact:
    return art.Artifact.of(kind, artifact_result(kind=kind, holes=holes).doc)


def test_an_unlabelled_partial_is_refused_naming_each_hole() -> None:
    found = art.check(parsed("partial", TWO_HOLES), partial_text=UNLABELLED)
    assert [d.code for d in found] == ["partial-unlabelled"]
    d = found[0]
    assert "approach" in d.message and "licence" in d.message
    assert "D-12 v3.44" in d.message
    problems = d.details["missing"]
    assert [p["code"] for p in problems] == [
        "approach",
        "licence",
        "label",
        "claim",
        "label",
        "claim",
    ]
    assert [p["hole"] for p in problems] == [None, None, "right", "right", "left", "left"]
    for p in problems:
        assert p["message"] in d.message


def test_a_complete_partial_is_not_refused() -> None:
    assert art.check(parsed("partial", TWO_HOLES), partial_text=LABELLED) == []


def test_the_extractors_hole_names_are_the_ones_held_to_the_rule() -> None:
    """The text scan sees ``right`` and ``left``; the extractor reports a third hole the scan
    did not (a ``have`` the regex misses), and that hole is still named as missing its words."""
    three = [*TWO_HOLES, ("hidden", "p ∧ q", False)]
    found = art.check(parsed("partial", three), partial_text=LABELLED)
    assert [d.code for d in found] == ["partial-unlabelled"]
    assert [p["hole"] for p in found[0].details["missing"]] == ["hidden", "hidden"]


BULLETED = """theorem OpnProp.and_swap : ∀ (p q : Prop), p ∧ q → q ∧ p := by
  -- approach: split the goal and take each half from the hypothesis
  -- licence: CC-BY-4.0
  intro p q h
  refine ⟨?_, ?_⟩
  -- label: the right half
  -- claim: $q$
  · have right : q := sorry
    exact right
  -- label: the left half
  -- claim: $p$
  · have left : p := sorry
    exact left
"""


def test_a_hole_under_a_focusing_bullet_is_read_from_its_block() -> None:
    """A hole written ``· have … := sorry`` (the shape F07's carried-witness fixtures and the
    live graph use) is a hole to the extractor, so the scan must read the block above it or
    no such partial could ever be declared."""
    found = art.check(parsed("partial", TWO_HOLES), partial_text=BULLETED)
    assert found == []
    d = labels.declarations(BULLETED)
    assert d.holes["right"].label == "the right half" and d.holes["left"].claim == "p"


def test_a_reduction_is_never_asked() -> None:
    assert art.check(parsed("reduction", [("only", "q", False)]), partial_text=UNLABELLED) == []


def test_without_the_text_nothing_is_asked() -> None:
    """``check`` without the assembly's text (a caller that has only the extractor's report)
    decides as before: the words are checked where the text is."""
    assert art.check(parsed("partial", TWO_HOLES)) == []


def test_the_refusal_sits_after_hole_unnamed_and_before_partial_without_holes() -> None:
    doc = artifact_result(kind="partial", holes=[], unnamed=1).doc
    found = art.check(art.Artifact.of("partial", doc), partial_text=UNLABELLED)
    assert [d.code for d in found] == [
        "hole-unnamed",
        "partial-unlabelled",
        "partial-without-holes",
    ]


def test_step_4_reads_the_assembly_step_2_recorded(tmp_path: Path) -> None:
    """``run`` reads the partial's text from where step 2 recorded it (``ctx.data['partial']``),
    the way the annex-steps check does, so the rule runs in the pipeline, not only in ``check``."""
    assembly = tmp_path / "partial.lean"
    assembly.write_text(UNLABELLED, encoding="utf-8")
    fake = FakeToolchain(artifact=artifact_result(kind="partial", holes=TWO_HOLES))
    ctx = make_context(tmp_path, toolchain=fake)
    ctx.data[art.PARTIAL_KEY] = {"path": "attempts/x.lean", "file": str(assembly)}
    req = ArtifactRequest(
        statement=Path("Statement.lean"),
        statement_module="Nodes.«tutorial-and-swap».Statement",
        decl=STMT,
        artifact=assembly,
        artifact_module="Nodes.«tutorial-and-swap».Proof",
        artifact_decl=STMT,
        kind="partial",
    )
    found, failure = art.run(ctx, fake.resolved, req, "partial")
    assert found is not None and failure is not None and failure.diagnostic is not None
    assert failure.diagnostic.code == "partial-unlabelled"
    assert [p["hole"] for p in failure.diagnostic.details["missing"]][2:] == [
        "right",
        "right",
        "left",
        "left",
    ]

    assembly.write_text(LABELLED, encoding="utf-8")
    found, failure = art.run(ctx, fake.resolved, req, "partial")
    assert found is not None and failure is None


def test_the_code_is_catalogued_at_step_4() -> None:
    row = codes.CATALOG["partial-unlabelled"]
    # F29-T3: the service emits it too, before any precheck, so the source is both.
    assert row.source == "both" and row.step == 4
