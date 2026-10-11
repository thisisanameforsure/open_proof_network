"""F10-T16: the guide says what the 2026-10-01 testers had to find out for themselves.

Twenty-six agents worked the three Erdős targets on 2026-10-01
(``engineering/evidence/testers-2026-10-01/bugs.md``, items A10, A18, A20 and B4). Five things an
agent could only learn by spending a gate round or a token start on them, each now a sentence, and
each read against the code that makes it true, so the two cannot drift (log, 2026-09-11: docs are
tests):

* ``decide +kernel`` is accepted where ``native_decide`` is not (402-R6-b, 69-R2-b).
* A many-lemma skeleton needs its holes scoped, each in its own bullet of one ``refine``, and a
  partial carries at most twenty (402-R5-a, 402-R6-a: a flat hole after twenty others carried all
  twenty as hypotheses).
* A hole whose hypotheses cannot be satisfied can never be witnessed (402-R1-a's abandoned
  design); the remaining cases go in the conclusion as disjuncts.
* ``POST /check`` needs no token (three agents spent token starts believing it did).
* An annex's disclosure field is ``model_and_tooling``; ``tooling`` is refused there (402-R1-b).

The owner, 2026-10-01: "Decide kernel plus sounds fine to me."
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from opn_api import appends, routes, submissions
from opn_gate.steps import artifact, axioms

ROOT = Path(__file__).resolve().parents[2]
GUIDE = (ROOT / "gate" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
FLAT = re.sub(r"\s+", " ", GUIDE)

PRESENT = {
    "decide +kernel is accepted": "`decide +kernel` is accepted",
    "why native_decide is not": "trusts the compiler",
    "the refusal's own code": "`native-decide-unwaived`",
    "the scoped layout": "refine ⟨?_, ?_⟩",
    "what scoping buys": "closed over its own binders",
    "the cap's own refusal": "`too-many-holes`",
    "a hole that can never be witnessed": "can never be witnessed",
    "the cure: positive disjuncts": "as disjuncts of the conclusion",
    "the fast check needs no token": "`POST /check` needs no token",
    "the annex's disclosure field": '"model_and_tooling"',
    "the two names for one disclosure": "`400 unknown-field`",
}


@pytest.mark.parametrize("what", sorted(PRESENT))
def test_the_guide_says(what: str) -> None:
    assert PRESENT[what] in FLAT, what


def test_the_hole_cap_is_the_gates() -> None:
    assert f"at most {artifact.MAX_HOLES} holes" in FLAT


def test_the_native_decide_refusal_is_step_fives() -> None:
    """The code the guide names is the one step 5 answers with."""
    source = Path(axioms.__file__).read_text("utf-8")
    assert '"native-decide-unwaived"' in source


def test_the_fast_check_is_an_open_route() -> None:
    (spec,) = [r for r in routes.ROUTES if r.label == "POST /check"]
    assert not spec.authenticated


def test_the_disclosure_fields_are_the_routes() -> None:
    assert "model_and_tooling" in appends.ANNEX_FIELDS and "tooling" not in appends.ANNEX_FIELDS
    assert "tooling" in submissions.SUBMISSION_FIELDS
    # the guide's own annex request sends it, and that block is run by the walkthrough
    block = GUIDE.split('> "$WORK/annex-request.json"', 1)[1].split("PY\n", 1)[0]
    assert '"model_and_tooling"' in block
