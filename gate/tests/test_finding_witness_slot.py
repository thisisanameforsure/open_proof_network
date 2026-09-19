"""F07-T20: the witness slot a hole is born with states the obligation, not ``True`` (R21, Q28).

An outside contributor asked to witness ``erdos-69--h2-v2--h1-v2`` found nothing that said what
a witness is, and inferred the shape from sibling files. The file in front of them made it
worse: the post-merge job writes every hole's ``Witness.lean`` as

    theorem witness : True := by
      sorry

``True`` whatever the statement's hypotheses are (``WITNESS_SLOT.format(expected="True")``), so
the one place that names the obligation names the wrong one for every hole that has a
hypothesis. The real type is step 7's (``expectedWitnessType``: exists over the variables of the
conjunction of the hypotheses), and until now it reached a contributor only as the ``expected``
field of a ``witness-type-mismatch`` refusal.

The extractor already holds each hole's closed obligation as an ``Expr``; it now reports the
expected witness type beside it, printed the way ``closed_type`` is and only when that text
reads back to the same type, and the writer puts it in the slot. With no reported type (an
older pin's report, or a type that does not survive printing) the slot claims nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fakes import FakeToolchain, artifact_result
from test_cli_sandboxed import NODES, Seam, run
from test_postmerge_apply import HOLES, ROOT, WITNESS, argv, merged_partial

from opn_gate import cli, graph, postmerge
from opn_gate.steps.artifact import Hole

EXPECTED = "∃ p q r, (p ∧ q) ∧ r"
DOC = {"name": "right", "type": "r", "closed_type": HOLES[0][1], "defeq_goal": False}


def test_the_hole_report_carries_the_expected_witness_type() -> None:
    hole = Hole.of({**DOC, "expected_witness": EXPECTED})
    assert hole.expected_witness == EXPECTED
    assert hole.as_dict()["expected_witness"] == EXPECTED


def test_an_older_report_has_none_and_is_not_guessed() -> None:
    hole = Hole.of(DOC)
    assert hole.expected_witness is None and hole.as_dict()["expected_witness"] is None
    assert Hole.of({**DOC, "expected_witness": ""}).expected_witness is None


def test_the_slot_states_the_type_it_was_given(tmp_path: Path) -> None:
    slot = postmerge.witness_slot(EXPECTED)
    assert f"theorem witness : {EXPECTED} := by\n  sorry\n" in slot
    assert "theorem witness : True" not in slot
    (tmp_path / "Witness.lean").write_text(slot, encoding="utf-8")
    assert graph.witness_is_stub(tmp_path), "still a slot: the node stays blocked (F07-R6)"


def test_with_no_type_the_slot_claims_nothing(tmp_path: Path) -> None:
    slot = postmerge.witness_slot(None)
    assert "placeholder" in slot and "step 7" in slot
    assert "theorem witness : True := by\n  sorry\n" in slot  # a declaration must still parse
    (tmp_path / "Witness.lean").write_text(slot, encoding="utf-8")
    assert graph.witness_is_stub(tmp_path)


def test_a_merged_partial_writes_each_holes_own_obligation(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _assembly, _ = merged_partial(tmp_path)
    report = artifact_result(holes=HOLES)
    report.doc["holes"][0]["expected_witness"] = EXPECTED  # the second hole reports none
    seam.fake = FakeToolchain(witness=WITNESS, artifact=report)
    code, out, err = run(capsys, *argv(root, tmp_path / "o", "--apply-partial", "--author", "c"))
    assert code == cli.EXIT_PASS, err
    first, second = (root / NODES / child / "Witness.lean" for child in out["partial"]["children"])
    assert f"theorem witness : {EXPECTED} := by" in first.read_text(encoding="utf-8")
    assert "placeholder" in second.read_text(encoding="utf-8")
    assert out["partial"]["children"] == [f"{ROOT}--h1", f"{ROOT}--h2"]
