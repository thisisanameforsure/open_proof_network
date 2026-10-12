"""F26-T9 (R10; D-9 v3.39): back-translation leaves the QA pass's floors.

A pass without a back-translation row is complete for the root and for a definition; a record
written under the old floor, with its back-translation row, still reads and still counts, since
it did more than the new floor asks and the ``qa`` schema keeps the value for old records.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
import yaml
from harness import copy_graph, take_in

from opn_gate import qa, schemas

DEFS = {"Primes.lean": "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p\n"}
WHEN = "2026-10-12T10:00:00Z"
TOOL = "opn-gate qa"


@pytest.fixture
def target(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path)
    take_in(root, defs=DEFS)
    return root / "targets" / "euclid-primes"


def a_row(check: qa.Check, verdict: qa.Verdict = "pass") -> qa.Row:
    extra = {"model": "fake-model", "model_version": "1"} if qa.KIND_OF[check] == "brief" else {}
    return qa.row(check, verdict, tool=TOOL, tool_version="0.0.0", timestamp=WHEN, **extra)


def test_the_floors_no_longer_name_backtranslation() -> None:
    """R10: neither floor asks for a back-translation; the check itself stays known to the
    reader (``CHECKS``, ``KIND_OF``) so old records still load."""
    assert "backtranslation" not in qa.FLOOR_ROOT
    assert "backtranslation" not in qa.FLOOR_DEFINITION
    assert ("compile", *qa.SCREENS, "brief") == qa.FLOOR_ROOT
    assert qa.FLOOR_DEFINITION == ("compile", "brief")
    assert "backtranslation" in qa.CHECKS and qa.KIND_OF["backtranslation"] == "brief"


@pytest.mark.parametrize("subject", ["root", "Primes"])
def test_a_pass_without_backtranslation_is_complete(target: Path, subject: str) -> None:
    """R10: compile, the screens (root only) and the brief make a complete pass."""
    rows = [a_row(c) for c in qa.floor_for(subject) if c != "backtranslation"]
    assert "backtranslation" not in {r.check for r in rows}
    qa.write(target, subject, rows, date=WHEN, produced_by=TOOL)
    state = qa.require_complete(target, subject)
    assert state.complete and state.missing == ()


def test_an_old_record_with_backtranslation_still_counts(target: Path) -> None:
    """R10: a record written under the old floor validates against the schema, loads, and
    its pass is complete; the extra row is read as a passing check, not refused."""
    rows = [a_row(c) for c in ("compile", *qa.SCREENS, "brief", "backtranslation")]
    path = qa.write(target, "root", rows, date=WHEN, produced_by=TOOL)
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    schemas.validate(doc, qa.SCHEMA)
    assert "backtranslation" in [c["check"] for c in doc["checks"]]
    state = qa.require_complete(target, "root")
    assert state.complete and state.checks["backtranslation"] == "pass"


def test_the_definition_message_names_the_new_floor() -> None:
    """The one message that names a definition's floor says compile and brief, not
    back-translation (the floor's words follow the floor)."""
    src = inspect.getsource(qa)
    assert "compile, brief and backtranslation" not in src
