"""F21-T6 / AC5 (gate half): ``gloss/v2`` and ``explainer/v2`` carry ``drafted_with`` (R6; D-3
v3.31, D-23).

A contributor's version may say which model drafted it. v2 is v1 plus that one optional field;
the gate reads both versions, each against the schema it declares, and the product
(``glosses/v2``) publishes the field per version. A version that names a model is a model's
words for the section states (R11): its changed sections are ``drafted``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from harness import TARGET
from test_gloss_chains import NODE, STRANGER, codes, front, keys, node_dir, put, rel, root
from test_products import generate, loads

from opn_gate import schemas
from opn_gate.paths import Change

__all__ = ["keys", "root"]  # the fixtures, imported for pytest

MODEL = "anthropic/claude-opus-5.5 via Claude Code"
ABSENT = object()


def gloss_doc(root: Path, schema: str, drafted_with: Any = ABSENT) -> dict[str, Any]:
    file = node_dir(root) / "Statement.lean"
    doc: dict[str, Any] = {
        "schema": schema,
        "target": TARGET,
        "subject": {
            "kind": "statement",
            "node": NODE,
            "module": None,
            "lean_hash": schemas.content_hash(file.read_bytes()),
        },
        "supersedes": None,
        "author": "carol",
        "drafter": None,
        "date": "2026-10-05",
        "licence": "CC-BY-4.0",
    }
    if drafted_with is not ABSENT:
        doc["drafted_with"] = drafted_with
    return doc


def explainer_doc(root: Path, schema: str, drafted_with: Any = ABSENT) -> dict[str, Any]:
    proof = schemas.content_hash((node_dir(root) / "Proof.lean").read_bytes())
    doc: dict[str, Any] = {
        "schema": schema,
        "target": TARGET,
        "node": NODE,
        "proof": proof,
        "supersedes": None,
        "author": "carol",
        "drafter": None,
        "date": "2026-10-05",
        "licence": "CC-BY-4.0",
    }
    if drafted_with is not ABSENT:
        doc["drafted_with"] = drafted_with
    return doc


def file_record(root: Path, record: str, doc: dict[str, Any], body: str) -> tuple[str, Change]:
    path = put(node_dir(root) / record, front(doc, body))
    return path.stem, Change("A", rel(root, path))


CASES = [
    ("v1", ABSENT),
    ("v2", ABSENT),
    ("v2", None),
    ("v2", MODEL),
]


@pytest.mark.parametrize("record", ["gloss", "explainer"])
@pytest.mark.parametrize(("version", "drafted_with"), CASES)
def test_both_versions_validate_and_classify(
    root: Path, record: str, version: str, drafted_with: Any
) -> None:
    """AC5: v1, and v2 with or without ``drafted_with`` (absent, null, a model), each validate
    against the schema they declare and classify as the explainer mode with no problem."""
    make = gloss_doc if record == "gloss" else explainer_doc
    doc = make(root, f"{record}/{version}", drafted_with)
    assert schemas.violations(doc) == []
    _, change = file_record(root, record, doc, "## The idea\nWhy it holds.\n")
    assert codes(root, change, author=STRANGER) == []


@pytest.mark.parametrize("record", ["gloss", "explainer"])
@pytest.mark.parametrize(
    ("version", "drafted_with"),
    [("v2", "x" * 201), ("v2", 123), ("v2", ""), ("v1", MODEL)],
)
def test_a_bad_drafted_with_is_refused(
    root: Path, record: str, version: str, drafted_with: Any
) -> None:
    """AC5: an over-long, empty or non-string ``drafted_with``, or one on a v1 record (which has
    no such field), is refused as the record's own invalid code."""
    make = gloss_doc if record == "gloss" else explainer_doc
    doc = make(root, f"{record}/{version}", drafted_with)
    _, change = file_record(root, record, doc, "## The idea\nWhy it holds.\n")
    assert codes(root, change, author=STRANGER) == [f"{record}-invalid"]


@pytest.mark.parametrize("record", ["gloss", "explainer"])
def test_the_product_carries_drafted_with(root: Path, record: str) -> None:
    """AC5 (product): ``glosses/v2`` publishes ``drafted_with`` per version — the model for a v2
    version naming one, null for a v2 version without and for every v1 version — and a version
    that names a model wrote its sections as ``drafted`` (R11)."""
    make = gloss_doc if record == "gloss" else explainer_doc
    first, _ = file_record(root, record, make(root, f"{record}/v1"), "## The idea\nOne.\n")
    second_doc = make(root, f"{record}/v2", MODEL)
    second_doc["supersedes"] = first
    second, _ = file_record(root, record, second_doc, "## The idea\nTwo.\n")
    doc = loads(generate(root), f"targets/{TARGET}/glosses.json")
    assert doc["schema"] == "glosses/v2"
    assert schemas.violations(doc) == []
    kind = "statement" if record == "gloss" else "proof"
    [subject] = [s for s in doc["subjects"] if s["kind"] == kind and s["node"] == NODE]
    [chain] = subject["chains"]
    versions = {v["hash"]: v for v in chain["versions"]}
    assert versions[first]["drafted_with"] is None
    assert versions[first]["schema"] == f"{record}/v1"
    assert versions[second]["drafted_with"] == MODEL
    assert versions[second]["schema"] == f"{record}/v2"
    key = "whole" if record == "gloss" else "overview"
    assert versions[first]["sections"] == [{"key": key, "state": "written"}]
    # A model's change over a person's words is not shown (R11, R12); the person's stay.
    assert versions[second]["sections"] == [{"key": key, "state": "pending"}]
    assert chain["shown"] == [{"key": key, "version": first, "state": "written"}]


@pytest.mark.parametrize("record", ["gloss", "explainer"])
def test_a_models_first_version_is_drafted(root: Path, record: str) -> None:
    """R11: a new chain whose version names a model shows its words as ``drafted``."""
    make = gloss_doc if record == "gloss" else explainer_doc
    digest, _ = file_record(root, record, make(root, f"{record}/v2", MODEL), "## The idea\nX.\n")
    doc = loads(generate(root), f"targets/{TARGET}/glosses.json")
    kind = "statement" if record == "gloss" else "proof"
    [subject] = [s for s in doc["subjects"] if s["kind"] == kind and s["node"] == NODE]
    [chain] = subject["chains"]
    key = "whole" if record == "gloss" else "overview"
    assert chain["shown"] == [{"key": key, "version": digest, "state": "drafted"}]
    assert chain["pending"] == []
