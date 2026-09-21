"""F07-T30: the ``hole-not-roundtrip`` refusal says which hole and what to do, once.

The erdos-69 agent got about 4 kB of Lean, the same text three times over (the message and two
detail fields), and no word on what to change. The refusal is rare after the printer fix, which
is a reason to make the one that remains readable.
"""

from __future__ import annotations

from fakes import artifact_result

from opn_gate.diagnostic import Diagnostic
from opn_gate.steps import artifact as art

LONG = "∀ (b : Nat), (0 : Nat) < b → ∃ N k m, (↑m : Int) * (2 : Int) ≤ (↑N : Int) + (↑k : Int)"


def refusal() -> Diagnostic:
    report = artifact_result(kind="partial", matches=True, holes=[("crux", LONG, False)])
    report.doc["holes"][0]["closed_roundtrip"] = False
    (problem,) = art.check(art.Artifact.of("partial", report.doc))
    assert problem.code == "hole-not-roundtrip"
    return problem


def test_the_message_names_the_hole_and_says_what_to_change() -> None:
    message = refusal().message
    assert "crux" in message
    assert "ascri" in message.lower(), message  # "ascribe the type ..."
    assert "F07-R19" in message


def test_the_holes_text_appears_once_in_the_whole_diagnostic() -> None:
    problem = refusal()
    whole = problem.message + repr(problem.details)
    assert whole.count(LONG) == 1, whole.count(LONG)
    assert problem.details["holes"] == ["crux"]
