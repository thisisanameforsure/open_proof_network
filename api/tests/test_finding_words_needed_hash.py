"""Testers 2026-10-09b (C3): ``list_words_needed`` asked for an explainer and never gave the hash
``submit_gloss`` needs as its ``proof`` subject; the only place it appeared was inside the outline's
path, and the description of ``subject`` did not say ``proof`` is that hash. Two 400s to learn it.

Every row now carries ``lean_hash``, the SHA-256 of the Lean text the words would describe: for a
proof, alternate or partial it is the ``proof`` of a ``submit_gloss`` explainer subject, and for a
statement, witness or relation the optional ``lean_hash`` of a gloss subject. The description of
``submit_gloss``'s subject says so.
"""

from __future__ import annotations

from pathlib import Path

from api_fakes import Harness
from mcp_client import McpClient
from test_gloss_coverage import ALTERNATE, ROOT, TARGET, nodes
from test_mcp_words_needed import h, rendered, tree  # noqa: F401 — the fixtures, by name

from opn_api.mcp import results
from opn_api.mcp.server import TOOLS
from opn_gate import schemas


def test_every_row_carries_the_hash_of_the_lean_it_describes(h: Harness, tree: Path) -> None:  # noqa: F811
    out = McpClient(h).ok("list_words_needed", {})
    assert results.violations("list_words_needed", out) == []
    assert out["subjects"], "guard: something lacks words"
    for row in out["subjects"]:
        digest = schemas.content_hash((tree / row["file"]).read_bytes())
        assert row["lean_hash"] == digest, row["file"]
    [proof] = [
        r for r in out["subjects"] if r["file"] == f"targets/{TARGET}/nodes/{ROOT}/{ALTERNATE}"
    ]
    assert proof["outline"] == f"targets/{TARGET}/outlines/{proof['lean_hash']}.json"
    assert proof["lean_hash"] == schemas.content_hash((nodes(tree) / ROOT / ALTERNATE).read_bytes())


def test_the_hash_round_trips_into_an_explainer_subject(h: Harness, tree: Path) -> None:  # noqa: F811
    """The row's hash is exactly what ``submit_gloss`` takes as ``proof``: a dry run accepts it."""
    out = McpClient(h).ok("list_words_needed", {"kind": "alternate"})
    [proof] = out["subjects"]
    token = h.token_for("code_alice", "alice-p")
    text = "## The argument\n\nIt covers step s1.\n"
    answer = McpClient(h).ok(
        "submit_gloss",
        {
            "subject": {"kind": "proof", "node_id": proof["node"], "proof": proof["lean_hash"]},
            "text": text,
            "licence": "CC-BY-4.0",
            "dry_run": True,
        },
        token=token,
    )
    assert answer["body"]["ok"] is True and answer["body"]["dry_run"] is True, answer


def test_the_subject_description_says_proof_is_the_rows_hash() -> None:
    tool = next(t for t in TOOLS if t.name == "submit_gloss")
    subject = tool.input_schema["properties"]["subject"]
    assert "lean_hash" in subject["description"] and "list_words_needed" in subject["description"]
