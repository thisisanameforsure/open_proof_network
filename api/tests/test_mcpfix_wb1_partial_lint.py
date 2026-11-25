"""mcpfix WB1 item 4 (testers 2026-11-25, t257b item 1): the fast check names a skeleton's
missing comment lines.

A partial names its approach, a licence and each hole's label and claim in its comments (D-12
v3.44); the precheck refuses one that does not, ``partial-unlabelled`` with ``details.missing``.
``check_lean`` already said ``sorry-present`` of the same text and said nothing of the comments,
so the rule cost a precheck round trip. A text with ``sorry`` is now read by the same rule
(``opn_gate.labels.problems``) and each missing line is reported as one ``partial-unlabelled``
finding carrying the precheck's own ``missing`` list.
"""

from __future__ import annotations

from mcp_client import TARGET
from test_checks import harness_with, post, seed
from test_finding_partial_unlabelled import HALF_LABELLED, LABELLED, UNLABELLED

from opn_gate import labels

TEXT = UNLABELLED.replace("import Nodes.X.Context\n\n", "")


def lint_of(content: str) -> list[dict[str, object]]:
    h = harness_with()
    seed(h)
    r = post(h, {"target_id": TARGET, "content": content})
    assert r.status_code == 200, r.text
    found: list[dict[str, object]] = r.json()["lint"]
    return found


def test_an_unlabelled_skeleton_is_told_what_its_partial_lacks() -> None:
    found = [w for w in lint_of(TEXT) if w["code"] == "partial-unlabelled"]
    assert len(found) == 1
    assert found[0]["missing"] == [p.as_dict() for p in labels.problems(TEXT)]
    assert [m["code"] for m in found[0]["missing"]] == [p.code for p in labels.problems(TEXT)]
    assert "approach" in str(found[0]["message"])


def test_one_missing_label_is_named() -> None:
    text = HALF_LABELLED.replace("import Nodes.X.Context\n\n", "")
    (found,) = [w for w in lint_of(text) if w["code"] == "partial-unlabelled"]
    assert found["missing"] == [p.as_dict() for p in labels.problems(text)]
    assert len(found["missing"]) == 1


def test_a_labelled_skeleton_and_a_proof_without_sorry_are_quiet() -> None:
    text = LABELLED.replace("import Nodes.X.Context\n\n", "")
    assert "partial-unlabelled" not in [w["code"] for w in lint_of(text)]
    proof = "theorem x : True := by\n  trivial\n"
    assert "partial-unlabelled" not in [w["code"] for w in lint_of(proof)]
