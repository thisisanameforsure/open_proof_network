"""Finding proposal-declaration-clash (agent E, 2026-09-20): a proposal whose theorem name an
existing node of the target already declares is refused only by the gate (``declaration-clash``),
three minutes and one pull request later, and the dead pull request cannot be withdrawn. The
service reads the siblings' statements anyway (they are cached), so it refuses at ``POST`` and
names the node that holds the declaration (F08-T16).

F08-T19 (testers 2026-09-24, seen at the 16:30Z queue check): F08-T16 read *merged* siblings
only. Graph #189 and #198, the 402-MCP agent's variants for |A| = 6 and 7, failed the gate's step
``declaration`` with ``declaration-clash`` ("node 'variant-e6d83e6d' already declares
Opn.erdos_402_card_six; a node may only restate a declaration by superseding the node that holds
it (D-8)") because the other agent's #188 and #190, still open, declared the same two theorems.
Their texts differed, so the copy rule rightly let them through, and the service, which opened
#188 and #190 itself, could have read their statements at the pull requests' heads. Now the
route refuses a name held by an open proposal that can still merge, naming its pull request, and
it asks the gate's own question (``admit.declaration_holder``) in the gate's own words
(``admit.clash_message``) rather than a copy of them.

Red run: ``engineering/evidence/F08/task-19.txt``."""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import Harness
from test_finding_duplicate_submissions import GATE_FAILED
from test_proposals import DEP_STATEMENT, NODES, STATEMENT, TARGET, WITNESS, post

from opn_gate import admit, layout

#: The gate's own sentence (``admit.DeclarationCheck``), which the service must speak.
GATE_WORDS = "a node may only restate a declaration by superseding the node that holds it (D-8)"
#: The same theorem name as ``STATEMENT`` over a different proposition, so a different node id.
SAME_NAME = "theorem OpnProp.and_weaken : ∀ p q : Prop, p ∧ q → q ∨ p := by\n  sorry\n"  # noqa: RUF001
RED = "F08-T19: the service reads merged siblings only, in words of its own"


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


# --- F08-T19: open proposals, and the gate's own check ------------------------------------------


def published(h: Harness, pr_number: int) -> None:
    """What the real host has and the fake does not tie together: the pull request's head commit
    carries the files the service pushed for it."""
    push = h.githost.pushes[-1]
    h.githost.files_at[f"{pr_number:040d}"] = {p: t.encode() for p, t in push.files.items()}


def proposed(h: Harness, token: str, statement: str, route: str = "/proposals/variant") -> Any:
    r = post(h, route, token, body(statement))
    assert r.status_code == 201, r.text
    published(h, r.json()["pr_number"])
    return r.json()


@pytest.mark.xfail(strict=True, reason=RED)
def test_the_refusal_is_in_the_gates_words(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.githost.files[f"{NODES}and-reassoc/Statement.lean"] = DEP_STATEMENT.encode()
    clash = "theorem OpnProp.and_reassoc : ∀ p : Prop, p → p := by\n  sorry\n"
    r = post(harness, "/proposals/speculative", token, body(clash))
    assert r.status_code == 409, r.text
    assert "node 'and-reassoc' already declares OpnProp.and_reassoc" in r.json()["message"]
    assert GATE_WORDS in r.json()["message"], r.json()["message"]


@pytest.mark.xfail(strict=True, reason=RED)
def test_a_name_held_by_an_open_proposal_is_refused_with_its_pr(harness: Harness) -> None:
    """#188 open, then #189: a different statement under the same theorem name."""
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    first = proposed(harness, alice, STATEMENT)
    opened = len(harness.githost.pulls)
    for route in ("/proposals/variant", "/proposals/speculative"):
        r = post(harness, route, bob, body(SAME_NAME))
        assert r.status_code == 409, (route, r.text)
        doc = r.json()
        assert doc["error"] == "declaration-clash"
        assert doc["details"]["node"] == first["node_id"]
        assert doc["details"]["declaration"] == "OpnProp.and_weaken"
        assert doc["details"]["pr_number"] == first["pr_number"]
        assert f"#{first['pr_number']}" in doc["message"] and GATE_WORDS in doc["message"]
    assert len(harness.githost.pulls) == opened, "nothing may be opened for a refused name"


def test_an_open_proposal_that_can_no_longer_merge_holds_no_name(harness: Harness) -> None:
    """The copy check's rule (``duplicates.blocks``): a failed gate stands in no one's way."""
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    first = proposed(harness, alice, STATEMENT)
    harness.githost.set_pull_request_state(first["pr_number"], runs=GATE_FAILED)
    r = post(harness, "/proposals/variant", bob, body(SAME_NAME))
    assert r.status_code == 201, r.text


def test_the_same_statement_twice_is_still_a_copy_not_a_clash(harness: Harness) -> None:
    """Guard: the same statement is the same node id, and that refusal names the copy."""
    alice = harness.token_for("code_alice", "alice")
    proposed(harness, alice, STATEMENT)
    r = post(harness, "/proposals/variant", harness.token_for("code_bob", "bob"), body(STATEMENT))
    assert (r.status_code, r.json()["error"]) == (409, "duplicate-submission"), r.text


@pytest.mark.xfail(strict=True, reason=RED)
def test_a_revision_that_supersedes_the_holder_is_allowed() -> None:
    """D-8: a node may restate the declaration of the node it supersedes and of no other. No
    proposal route writes a revision (``opn-gate revise`` does, by curator pull request), so the
    exception lives in the one function the gate and the service share."""
    holder = getattr(admit, "declaration_holder", None)
    assert callable(holder), "the gate exposes no declaration check for the service to import"
    siblings = [("and-reassoc", DEP_STATEMENT)]
    assert holder("OpnProp.and_reassoc", siblings) == "and-reassoc"
    assert holder("OpnProp.and_reassoc", siblings, supersedes="and-reassoc") is None
    assert holder("OpnProp.and_reassoc", siblings, supersedes="elsewhere") == "and-reassoc"
    assert holder("OpnProp.and_reassoc", siblings, own="and-reassoc") is None
    assert holder("OpnProp.other", siblings) is None
    assert holder("OpnProp.and_reassoc", [("broken", "not lean at all")]) is None


@pytest.mark.xfail(strict=True, reason=RED)
def test_the_service_and_the_gate_agree(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> None:
    """The same function, imported, not re-implemented: plant an answer in the gate's check and
    the service gives it, for merged siblings and open proposals alike."""
    calls: list[str] = []

    def planted(decl_name: str, siblings: Any, **_: Any) -> str | None:
        calls.append(decl_name)
        return "planted-holder" if list(siblings) else None

    monkeypatch.setattr(admit, "declaration_holder", planted, raising=False)
    token = harness.token_for("code_alice", "alice")
    r = post(harness, "/proposals/variant", token, body(STATEMENT))
    assert r.status_code == 409, r.text
    assert r.json()["details"]["node"] == "planted-holder"
    parsed = layout.parse_statement(STATEMENT)
    assert isinstance(parsed, layout.Statement) and calls == [parsed.decl_name]
