"""F13-T15: the fast check says when the node it was asked about has been replaced (testers
2026-09-21). The erdos-1050 agent ran verify against ``erdos-1050--h1`` and got ``okay: null``,
"failed to compile formal_statement", with no word that the node was superseded by ``-v2``;
``POST /claims`` on the same node names the replacement. A check is not refused for it (checking
a superseded statement is how a defect is shown), so it is a warning, with the replacement.
"""

from __future__ import annotations

import samples
from api_fakes import Harness, make_harness
from mcp_client import TARGET, seed_node
from test_checks import PIN, post
from test_finding_superseded_refusals import NEW, OLD, add_revision

from opn_gate import schemas

STATEMENT = "theorem OpnProp.old_hole : True := by\n  sorry\n"
PROOF = "theorem OpnProp.old_hole : True := by\n  trivial\n"


def harness() -> Harness:
    h = make_harness(None)
    seed_node(h)
    add_revision(h)
    files = h.githost.files
    files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(mathlib_sha=PIN)
    )
    for node in (OLD, NEW):
        files[f"targets/{TARGET}/nodes/{node}/Statement.lean"] = STATEMENT.encode()
    h.context.files.clear()
    return h


def lint_of(h: Harness, node_id: str) -> list[dict[str, object]]:
    r = post(h, {"target_id": TARGET, "node_id": node_id, "content": PROOF})
    assert r.status_code == 200, r.text
    warnings: list[dict[str, object]] = r.json()["lint"]
    return warnings


def test_a_check_against_a_superseded_node_names_its_replacement() -> None:
    (warning,) = [w for w in lint_of(harness(), OLD) if w["code"] == "node-superseded"]
    assert warning["replacement"] == NEW and NEW in str(warning["message"])


def test_the_replacement_itself_is_not_warned_about() -> None:
    assert [w for w in lint_of(harness(), NEW) if w["code"] == "node-superseded"] == []
