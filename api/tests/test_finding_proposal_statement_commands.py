"""F08-T37, service half (D-3 v3.28): the proposal routes refuse a statement or a Context that
holds a command beyond D-3's list before any pull request opens.

Before this rule a speculative or variant proposal carrying ``instance``, ``set_option`` or an
``#eval`` was scaffolded, pre-flighted on the hosted checker and pushed as a pull request, and
only admission on the runner refused it. The service now asks the gate's own function
(``layout.command_problem``) of the files it scaffolded, so the refusal has the gate's code and
words, costs no hosted check and opens nothing.
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import Harness

from opn_api import proposals
from opn_gate import layout

TARGET = "propositional"
NODES = f"targets/{TARGET}/nodes/"
CODE = "statement-command-forbidden"
THEOREM = "theorem OpnProp.and_weaken : ∀ p q : Prop, p ∧ q → p ∨ q := by\n  sorry\n"  # noqa: RUF001
WITNESS = "theorem witness : ∃ p q : Prop, p ∧ q := ⟨True, True, trivial, trivial⟩\n"


def post(h: Harness, route: str, body: dict[str, Any]) -> Any:
    token = h.token_for("code_alice", "alice")
    return h.client.post(route, json=body, headers=h.auth(token))


@pytest.mark.parametrize(
    ("route", "prefix", "command"),
    [
        ("/proposals/speculative", "instance : Inhabited Prop := ⟨True⟩\n\n", "instance"),
        ("/proposals/variant", "set_option autoImplicit true\n\n", "set_option"),
        ("/proposals/speculative", 'initialize IO.println "loaded"\n\n', "initialize"),
    ],
)
def test_a_statement_with_a_command_is_refused_before_anything_opens(
    harness: Harness, route: str, prefix: str, command: str
) -> None:
    r = post(
        harness, route, {"target_id": TARGET, "statement": prefix + THEOREM, "witness": WITNESS}
    )
    assert r.status_code == 400, r.text
    doc = r.json()
    assert doc["error"] == CODE, doc
    assert doc["details"]["file"] == "Statement.lean"
    assert doc["details"]["command"] == command
    assert harness.githost.pushes == []
    assert harness.githost.pulls == []
    assert harness.axle.calls == []  # no hosted check is spent on it


def test_a_context_generated_from_a_dep_with_a_command_is_refused(harness: Harness) -> None:
    """The Context is the deps' statements verbatim; one carrying ``#eval`` would put it into
    this node's Context too, so the proposal is refused naming Context.lean."""
    harness.githost.files[f"{NODES}and-reassoc/Statement.lean"] = (
        b'theorem OpnProp.and_reassoc : True := by\n  sorry\n\n#eval IO.println "loaded"\n'
    )
    r = post(
        harness,
        "/proposals/speculative",
        {"target_id": TARGET, "statement": THEOREM, "witness": WITNESS, "deps": ["and-reassoc"]},
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"] == CODE
    assert r.json()["details"]["file"] == "Context.lean"
    assert r.json()["details"]["command"] == "#eval"
    assert harness.githost.pushes == []


def test_the_service_names_the_gates_code() -> None:
    assert proposals.STATEMENT_COMMAND_CODE == layout.STATEMENT_COMMAND_CODE
