"""F15-T9 / AC13: the problem proposal form (R13; D-6 v3.17, D-27 v3.17).

The form is a GitHub issue template: a proposal is an issue, never a commit (D-35). Its source
copy lives beside the guide in this repository so the suite can read it; the graph carries the
copy GitHub serves, checked byte for byte where the sibling checkout is present.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
FORM = ROOT / "gate" / "agents" / "problem-proposal.yml"
GRAPH_COPY = ROOT.parent / "open_proof_network_graph" / ".github" / "ISSUE_TEMPLATE" / FORM.name
#: R13's fields, by the id each block declares.
REQUIRED_IDS: tuple[str, ...] = (
    "statement",
    "references",
    "why-open",
    "area",
    "will-steward",
    "skip-upstream",
    "skip-upstream-why",
    "publishes",
)


def blocks() -> dict[str, dict[str, Any]]:
    doc = yaml.safe_load(FORM.read_text(encoding="utf-8"))
    return {str(b["id"]): b for b in doc["body"] if isinstance(b, dict) and "id" in b}


def test_the_form_declares_every_field_r13_names() -> None:
    doc = yaml.safe_load(FORM.read_text(encoding="utf-8"))
    assert doc["name"] and doc["description"] and "proposal" in doc["labels"]
    found = blocks()
    assert tuple(found) == REQUIRED_IDS
    for required in (
        "statement",
        "references",
        "why-open",
        "area",
        "will-steward",
        "skip-upstream",
    ):
        validations = found[required].get("validations") or {}
        assert validations.get("required") is True, required
    assert found["will-steward"]["type"] == "dropdown"
    assert found["skip-upstream"]["type"] == "dropdown"
    assert found["skip-upstream-why"]["type"] == "textarea"
    publishes = found["publishes"]
    assert publishes["type"] == "checkboxes"
    [box] = publishes["attributes"]["options"]
    assert box["required"] is True and "publishes" in box["label"]
    text = FORM.read_text(encoding="utf-8")
    for decision in ("D-6", "D-32", "D-10", "D-35"):
        assert decision in text


def test_graph_copy_is_identical() -> None:
    """D-35: the graph carries the form GitHub serves, byte for byte (skipped where the sibling
    checkout is absent, as in CI)."""
    if not GRAPH_COPY.is_file():
        pytest.skip(f"{GRAPH_COPY} is not checked out beside this repo")
    assert GRAPH_COPY.read_bytes() == FORM.read_bytes(), "the graph's form drifted; recopy it"
