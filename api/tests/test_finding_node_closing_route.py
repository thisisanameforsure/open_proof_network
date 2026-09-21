"""The "closable through its holes" flag on ``get_node`` (Mike, 2026-09-21; testers finding 2).

Two agents spent a session on holes that could not finish their target, and learned it at minute
37 by experiment: the parent's statement did not import its own Context, so no proof of it could
name the holes' theorems. Since F00-T10 a proof may add that one import, so every node *is*
closable through its holes; what a contributor needs to be told is *how*: whether the line is
already in the statement, or is theirs to add. One function answers
(``layout.imports_own_context``), so the fact has one home.
"""

from __future__ import annotations

from api_fakes import Harness
from mcp_client import NODE, NODE_DIR, McpClient, seed_node

from opn_api.mcp import results

OWN = f"import Nodes.«{NODE}».Context"
OLD = "import Init\n\ntheorem OpnProp.and_reassoc : True := by\n  sorry\n"
NEW = f"import Init\n{OWN}\n\ntheorem OpnProp.and_reassoc : True := by\n  sorry\n"


def closing(harness: Harness, statement: str) -> dict[str, object]:
    seed_node(harness)
    harness.githost.files[NODE_DIR + "Statement.lean"] = statement.encode()
    harness.context.files.clear()
    doc = McpClient(harness).ok("get_node", {"node_id": NODE})
    assert results.violations("get_node", doc) == []  # the tool's own result schema
    route: dict[str, object] = doc["closing"]
    return route


def test_an_old_statement_says_the_proof_adds_the_import(harness: Harness) -> None:
    route = closing(harness, OLD)
    assert route["through_holes"] is True
    assert route["context_import"] == "proof" and route["import_line"] == OWN


def test_a_new_statement_says_the_line_is_already_there(harness: Harness) -> None:
    route = closing(harness, NEW)
    assert route["through_holes"] is True
    assert route["context_import"] == "statement" and route["import_line"] == OWN
