"""F21-AC2 (R2, Q2): no new drafts; the seven existing ones stay readable.

v3.31 makes the words contributors' work, and the network drafts nothing (R1). The schemas still
allow a ``drafter`` block, because seven merged versions carry one, so deleting F20-T10's
``drafter-not-service`` with nothing in its place would let a hand-opened pull request file any
words as "machine-drafted by" any model (Q2). The rule tightens instead: an *added* gloss or
explainer file carrying a ``drafter`` block is refused ``draft-not-accepted``, whoever opened the
pull request — the service, a curator or a stranger. A merged draft still validates, renders in
``glosses.json`` and can be superseded by a person. Replaces ``test_gloss_draft_provenance.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from harness import TARGET, copy_graph
from test_gloss_chains import (
    NODE,
    SERVICE,
    STRANGER,
    chains_of,
    codes_by,
    front,
    node_dir,
    put,
    rel,
)
from test_modes import CURATOR, write_curators

from opn_gate import explainers, glosses, schemas
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


def version(
    root: Path,
    record: str,
    *,
    drafter: dict[str, Any] | None,
    author: str | None,
    supersedes: str | None = None,
    body: str | None = None,
) -> tuple[str, Change]:
    """Write a gloss of the node's statement or an explainer of its proof; ``(hash, change)``."""
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
        text = body or "What the statement says.\n"
    else:
        doc = {
            "schema": "explainer/v1",
            "target": TARGET,
            "node": NODE,
            "proof": schemas.content_hash((nd / "Proof.lean").read_bytes()),
        }
        text = body or "## The idea\nRegroup.\n"
    doc |= {"supersedes": supersedes, "author": author, "drafter": drafter, "date": "2026-10-05"}
    doc |= {"licence": "CC-BY-4.0"}
    path = put(nd / record, front(doc, text))
    return path.stem, Change("A", rel(root, path))


@pytest.mark.parametrize("record", ["gloss", "explainer"])
@pytest.mark.parametrize("opened_by", [SERVICE, CURATOR, STRANGER])
def test_an_added_draft_is_refused_whoever_opens_it(
    root: Path, record: str, opened_by: str
) -> None:
    _, change = version(root, record, drafter=DRAFTER, author=None)
    assert codes_by(root, change, opened_by) == ["draft-not-accepted"]


@pytest.mark.parametrize("record", ["gloss", "explainer"])
@pytest.mark.parametrize("opened_by", [SERVICE, STRANGER])
def test_a_persons_version_is_unchanged(root: Path, record: str, opened_by: str) -> None:
    _, change = version(root, record, drafter=None, author=STRANGER)
    assert codes_by(root, change, opened_by) == []


@pytest.mark.parametrize("record", ["gloss", "explainer"])
def test_a_merged_draft_validates_renders_and_is_superseded_by_a_person(
    root: Path, record: str
) -> None:
    # Merged: on the tree, in no pull request's diff.
    merged, _ = version(root, record, drafter=DRAFTER, author=None)
    read = (
        glosses.load_versions(node_dir(root))
        if record == "gloss"
        else explainers.versions(node_dir(root))
    )
    [draft] = [v for v in read if v.hash == merged]
    assert draft.drafter is not None and draft.author is None

    kind = "statement" if record == "gloss" else "proof"
    [chain] = chains_of(root, kind)
    assert [v["hash"] for v in chain["versions"]] == [merged]
    assert chain["versions"][0]["drafter"]["model"] == DRAFTER["model"]

    # A person supersedes it, through the service or by hand: not a new draft, so it passes.
    _, by_service = version(root, record, drafter=None, author=STRANGER, supersedes=merged)
    assert codes_by(root, by_service, SERVICE) == []
    (root / by_service.path).unlink()  # one pull request at a time: the next is a different one
    _, by_hand = version(
        root,
        record,
        drafter=None,
        author=STRANGER,
        supersedes=merged,
        body="Corrected by hand.\n" if record == "gloss" else "## The idea\nBy hand.\n",
    )
    assert codes_by(root, by_hand, STRANGER) == []
