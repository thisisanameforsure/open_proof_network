"""F13-T15: ``context-restated`` warns only when the Context restates something (testers
2026-09-21). The erdos-402 agent's variant had a Context reading "Declared dependencies: none",
and verify mode still said its Context "restates its dependencies with sorry bodies, so verify
reports a proof that uses one as incomplete". Since F08-T13 every statement imports its own
Context, so the lint fired on every node and said nothing.
"""

from __future__ import annotations

from mcp_client import NODE, TARGET
from test_checks import harness_with, post, seed

OWN = f"import Nodes.«{NODE}».Context"
STATEMENT = f"{OWN}\n\ntheorem OpnProp.and_reassoc : True := by\n  sorry\n"
PROOF = f"{OWN}\n\ntheorem OpnProp.and_reassoc : True := by\n  trivial\n"
EMPTY = "/-! Declared dependencies (D-4 step 8): none. -/\n"
RESTATING = (
    "/-! Declared dependencies (D-4 step 8): `dep`. -/\n\n"
    "theorem OpnProp.dep : True := by\n  sorry\n"
)


def codes(context: str) -> list[str]:
    h = harness_with()
    seed(h, statement=STATEMENT)
    h.githost.files[f"targets/{TARGET}/nodes/{NODE}/Context.lean"] = context.encode()
    h.context.files.clear()
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": PROOF, "mode": "verify"})
    assert r.status_code == 200, r.text
    return [w["code"] for w in r.json()["lint"]]


def test_a_context_that_restates_nothing_is_not_warned_about() -> None:
    assert "context-restated" not in codes(EMPTY)


def test_a_context_that_restates_a_dependency_still_is() -> None:
    assert "context-restated" in codes(RESTATING)
