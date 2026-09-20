"""Finding proposal-declaration-clash (agent E, 2026-09-20): a proposal whose theorem name an
existing node of the target already declares is refused only by the gate (``declaration-clash``),
three minutes and one pull request later, and the dead pull request cannot be withdrawn. The
service reads the siblings' statements anyway (they are cached), so it refuses at ``POST`` and
names the node that holds the declaration (F08-T16)."""

from __future__ import annotations

from api_fakes import Harness
from test_proposals import DEP_STATEMENT, NODES, STATEMENT, TARGET, WITNESS, post


def body(statement: str) -> dict[str, str]:
    return {"target_id": TARGET, "statement": statement, "witness": WITNESS}


def test_a_theorem_name_a_sibling_holds_is_refused_before_any_pull_request(
    harness: Harness,
) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.githost.files[f"{NODES}and-reassoc/Statement.lean"] = DEP_STATEMENT.encode()
    clash = "theorem OpnProp.and_reassoc : ∀ p : Prop, p → p := by\n  sorry\n"
    r = post(harness, "/proposals/variant", token, body(clash))
    assert r.status_code == 409, r.text
    doc = r.json()
    assert doc["error"] == "declaration-clash"
    assert doc["details"] == {"declaration": "OpnProp.and_reassoc", "node": "and-reassoc"}
    assert "and-reassoc" in doc["message"] and harness.githost.pushes == []


def test_a_fresh_name_is_proposed_as_before(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.githost.files[f"{NODES}and-reassoc/Statement.lean"] = DEP_STATEMENT.encode()
    r = post(harness, "/proposals/speculative", token, body(STATEMENT))
    assert r.status_code == 201, r.text


def test_a_sibling_whose_statement_cannot_be_read_does_not_block_a_proposal(
    harness: Harness,
) -> None:
    """C7: this is a courtesy ahead of the gate, which still decides. A node with no readable
    statement is skipped, never a reason to refuse."""
    token = harness.token_for("code_alice", "alice")
    for path in [p for p in harness.githost.files if p.endswith("/Statement.lean")]:
        del harness.githost.files[path]
    harness.context.files.clear()
    r = post(harness, "/proposals/variant", token, body(STATEMENT))
    assert r.status_code == 201, r.text
