"""F15-T14a / AC14: the calibration pool is a committed query, and the three chosen targets are
in it with their grades recorded (R14 a, b; Q12; Stages v3.17)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import yaml

from opn_gate import intake, layout, schemas

ROOT = Path(__file__).resolve().parents[2]
DRAFTS = ROOT / "engineering" / "onramp" / "calibration"
#: The pool at the 2026-09 dataset. The spec's R14 said 29; the committed query yields 30
#: (F15-Q13), and this is the number the suite holds it to.
POOL_SIZE = 30


def _load() -> Any:
    path = ROOT / "docs" / "calibration_pool.py"
    spec = importlib.util.spec_from_file_location("calibration_pool", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


calibration_pool = _load()


def test_the_pool_is_the_committed_query() -> None:
    rows = calibration_pool.pool()
    assert len(rows) == POOL_SIZE
    numbers = [r["number"] for r in rows]
    assert numbers == sorted(set(numbers))
    for row in rows:
        assert row["lean_files"], row
        assert row["site_status"] in calibration_pool.SOLVED_WITHOUT_LEAN, row
        assert "LEAN" not in row["site_status"]
    # The query keeps the registry-proved problems out: a Lean proof is not a calibration target.
    assert 1 not in numbers  # erdos 1 is DISPROVED (LEAN) in the dataset


def test_the_three_choices_are_in_the_pool_with_their_grades() -> None:
    choices = calibration_pool.CHOICES
    assert [c.grade for c in choices] == list(calibration_pool.GRADES)
    found = calibration_pool.choices_in_pool(calibration_pool.pool())
    for choice in choices:
        assert choice.number in found, choice
        assert choice.file in found[choice.number]["lean_files"], choice
        assert len(choice.reason) > 200 and choice.literature, choice
        assert ".variants." not in choice.decl


def test_the_drafts_are_calibration_intakes() -> None:
    """R14 c: each draft is a formalization-track record with ``calibration: true``, the
    literature proof as prior art, a statement that parses and a witness — what the founder's
    intake sitting takes in (T14b)."""
    for choice in calibration_pool.CHOICES:
        directory = DRAFTS / choice.target_id
        assert directory.is_dir(), directory
        doc = yaml.safe_load((directory / "record.yaml").read_text(encoding="utf-8"))
        schemas.validate(doc, intake.SCHEMA)
        assert doc["track"] == "formalization" and doc["calibration"] is True
        assert intake.is_calibration(doc)
        intake.check_calibration(doc)
        assert choice.literature[:30] in doc["prior_art"]["summary"]
        assert choice.grade in doc["prior_art"]["summary"]
        statement = layout.parse_statement(
            (directory / "Statement.lean").read_text(encoding="utf-8")
        )
        assert isinstance(statement, layout.Statement), statement
        assert statement.decl_name == f"Opn.erdos_{choice.number}"
        witness = (directory / "Witness.lean").read_text(encoding="utf-8")
        assert "theorem witness :" in witness
        if choice.hand_witness is not None:  # the one hand-written shape, flagged as unchecked
            assert "checked only by the sandboxed admission" in witness
        assert (DRAFTS / "upstream" / f"{choice.number}.lean").is_file()
