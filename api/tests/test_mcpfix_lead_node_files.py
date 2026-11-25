"""mcpfix (lead; verifier VA, A8, 2026-11-25): ``get_node`` with ``include: []`` stays small when
the node's witness is large.

On spec-a70fcca4--h4--h1--h1--h1 the answer was still 47,508 characters after the context was
narrowed, because ``files`` carried a 43,036-character Witness.lean. ``include`` now names
``witness`` and ``proof`` too: left out, the file's text is null and ``files_omitted`` names it
(null alone would read as "no such file")."""

from __future__ import annotations

from api_fakes import Harness
from mcp_client import NODE, TARGET, McpClient, seed_node
from mcpfix_wa2_fixture import compact

from opn_api.mcp import results

BIG_WITNESS = "theorem witness : True := by\n" + "  -- " + "w" * 40_000 + "\n  trivial\n"


def seeded(h: Harness) -> None:
    seed_node(h)
    h.githost.files[f"targets/{TARGET}/nodes/{NODE}/Witness.lean"] = BIG_WITNESS.encode()
    h.context.files.clear()


def test_include_empty_leaves_a_large_witness_out(harness: Harness) -> None:
    seeded(harness)
    out = McpClient(harness).ok("get_node", {"node_id": NODE, "include": []})
    assert len(compact(out)) < 25_000
    assert out["files"]["Witness.lean"] is None
    assert out["files_omitted"] == ["Witness.lean", "Proof.lean"]
    assert results.violations("get_node", out) == []


def test_naming_witness_answers_it(harness: Harness) -> None:
    seeded(harness)
    out = McpClient(harness).ok("get_node", {"node_id": NODE, "include": ["witness"]})
    assert out["files"]["Witness.lean"] == BIG_WITNESS
    assert out["files_omitted"] == ["Proof.lean"]


def test_omitting_include_answers_every_file(harness: Harness) -> None:
    seeded(harness)
    out = McpClient(harness).ok("get_node", {"node_id": NODE})
    assert out["files"]["Witness.lean"] == BIG_WITNESS
    assert "files_omitted" not in out
