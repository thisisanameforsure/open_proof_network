"""F07-T49: a statement line records the model its proposer declared (testers 2026-09-29, item 8).

Five agents read the ledger and the Contributors page saying tooling ``undeclared`` on every
statement line, 39 of 39, although each node's ``META.yaml`` records ``provenance.model`` from the
proposal that made it (D-23). The post-merge job's ``ledger`` command took a statement line's
tooling from nowhere: ``merge_tooling`` reads the attestation of the merge, and a merged proposal
has none, so the default stood. The disclosure D-23 asks for was on the record and never reached
the ledger.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from test_cli_sandboxed import Seam, commit_proposal, git_repo, run

from opn_gate import ledger, schemas

MODEL = "claude-opus-5-5 2026-09 claude-code"


def test_the_statement_tooling_is_the_declared_model() -> None:
    assert ledger.statement_tooling({"provenance": {"author": "alice", "model": MODEL}}) == MODEL


def test_a_proposal_that_declared_no_model_stays_undeclared() -> None:
    for meta in (
        {"provenance": {"author": "alice", "model": None}},
        {"provenance": {"author": "alice"}},
        {},
    ):
        assert ledger.statement_tooling(meta) == ledger.UNDECLARED, meta


def test_the_merged_statement_line_carries_the_model_from_meta(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """Driven through ``opn-gate ledger`` over a merged proposal, as the post-merge job runs it."""
    root, git, _base = git_repo(tmp_path, author="alice")
    head = commit_proposal(root, git, "spec-declared", model=MODEL)
    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", head)
    assert code == 0, err
    assert out["earned"] is True and out["line"] == "statement"
    doc: dict[str, Any] = schemas.load_json(root / "ledger" / "alice.json", ledger.SCHEMA)
    (entry,) = ledger.entries_of(doc)
    assert entry["node"] == "spec-declared"
    assert entry["tooling"] == MODEL
