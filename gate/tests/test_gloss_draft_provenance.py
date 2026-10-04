"""F20-T10: a draft arrives only through the service (R2, R18; Q6).

A version with a ``drafter`` block and no ``author`` says a model wrote it, under the drafter's
name. The service writes that block only for the configured drafter identity
(``api/tests/test_glosses_drafter.py``); a pull request opened by hand is judged by its opener,
who could otherwise file any words as "machine-drafted by" any model, and the page would say so.
So the gate accepts a draft only in a pull request the service opened, and refuses one opened by
anyone else by name (``drafter-not-service``). A person's own version is unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from harness import TARGET, copy_graph
from test_gloss_chains import NODE, SERVICE, STRANGER, codes_by, front, node_dir, put, rel
from test_modes import CURATOR, write_curators

from opn_gate import schemas
from opn_gate.paths import Change

DRAFTER = {
    "name": "opn-drafter",
    "model": "claude-opus-5",
    "model_version": "claude-opus-5-20261001",
    "input_commit": "c" * 40,
}


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """The propositional fixture, products published, a curator listed."""
    graph = copy_graph(tmp_path, publish=True)
    write_curators(graph, CURATOR)
    return graph


def draft(root: Path, record: str, *, drafter: dict[str, Any] | None, author: str | None) -> Change:
    nd = node_dir(root)
    doc: dict[str, Any]
    if record == "gloss":
        doc = {
            "schema": "gloss/v1",
            "target": TARGET,
            "subject": {
                "kind": "statement",
                "node": NODE,
                "module": None,
                "lean_hash": schemas.content_hash((nd / "Statement.lean").read_bytes()),
            },
        }
        body = "What the statement says.\n"
    else:
        doc = {
            "schema": "explainer/v1",
            "target": TARGET,
            "node": NODE,
            "proof": schemas.content_hash((nd / "Proof.lean").read_bytes()),
        }
        body = "## The idea\nRegroup.\n"
    doc |= {"supersedes": None, "author": author, "drafter": drafter, "date": "2026-10-05"}
    doc |= {"licence": "CC-BY-4.0"}
    path = put(nd / record, front(doc, body))
    return Change("A", rel(root, path))


@pytest.mark.parametrize("record", ["gloss", "explainer"])
def test_a_draft_through_the_service_passes(root: Path, record: str) -> None:
    change = draft(root, record, drafter=DRAFTER, author=None)
    assert codes_by(root, change, SERVICE) == []


@pytest.mark.parametrize("record", ["gloss", "explainer"])
@pytest.mark.parametrize("opened_by", [STRANGER, CURATOR])
def test_a_draft_opened_by_hand_is_refused(root: Path, record: str, opened_by: str) -> None:
    change = draft(root, record, drafter=DRAFTER, author=None)
    assert codes_by(root, change, opened_by) == ["drafter-not-service"]


@pytest.mark.parametrize("record", ["gloss", "explainer"])
def test_a_persons_version_opened_by_hand_is_unchanged(root: Path, record: str) -> None:
    change = draft(root, record, drafter=None, author=STRANGER)
    assert codes_by(root, change, STRANGER) == []
