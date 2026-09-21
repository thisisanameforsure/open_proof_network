"""F00-T10, the service half: the fast check agrees with the gate about the one import a proof may
add. The gate takes a proof whose header is its statement's plus the node's own Context import
(a statement from before 2026-09-20 has no such line); the ``imports-differ`` lint exists to say
where the gate would refuse what the checker accepts, so it must not fire on that line, and must
still fire on any other.
"""

from __future__ import annotations

from mcp_client import NODE, TARGET
from test_checks import harness_with, post, seed

OWN = f"import Nodes.«{NODE}».Context"
OLD_STATEMENT = "import Init\n\ntheorem OpnProp.and_reassoc : True := by\n  sorry\n"
CONTEXT = "/-! Declared dependencies (D-4 step 8): none. -/\n"


def codes(content: str) -> list[str]:
    h = harness_with()
    seed(h, statement=OLD_STATEMENT)
    h.githost.files[f"targets/{TARGET}/nodes/{NODE}/Context.lean"] = CONTEXT.encode()
    h.context.files.clear()
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": content})
    assert r.status_code == 200, r.text
    return [w["code"] for w in r.json()["lint"]]


def test_the_allowed_line_is_not_a_header_the_gate_would_refuse() -> None:
    proof = f"import Init\n{OWN}\n\ntheorem OpnProp.and_reassoc : True := by\n  trivial\n"
    assert "imports-differ" not in codes(proof)


def test_any_other_import_still_is() -> None:
    for header in (f"import Init\n{OWN}\nimport Std\n", f"{OWN}\nimport Init\n", "import Std\n"):
        proof = f"{header}\ntheorem OpnProp.and_reassoc : True := by\n  trivial\n"
        assert "imports-differ" in codes(proof), header
