"""F14-T9: the catalog of every conjecture with a Lean statement (R11; AC11).

The catalog is research data written by ``docs/seed_conjecture_sources_build.py`` from fetched
inputs (``docs/seed_conjecture_sources_fetch.sh``), so what a test can hold is its shape and its
arithmetic: every row names a Lean file, every letter is the one its score gives, the Riemann
Hypothesis grades A through the Mathlib predicate, and wherever a problem kept the score it had in
the F11 dataset of 2026-09-08 it kept its letter (with B split into B+ and B).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
CATALOG = REPO / "docs" / "lean_conjecture_catalog.json"
F11_DATASET = REPO / "docs" / "seed_conjecture_sources.json"
RIEMANN = "fc:FormalConjectures/Millenium/RiemannHypothesis.lean#riemannHypothesis"
LIVE_ERDOS = (52, 68, 172, 376, 406)  # the five open targets F11 listed on the graph
HIGH = 5  # F14-R5's default minimum: "B+"


def expected_letter(score: int | None) -> str:
    """The letter scale, written out independently of the build (F14-R11)."""
    if score is None:
        return "n/a"
    if score >= 6:
        return "A"
    if score == HIGH:
        return "B+"
    if score == 4:
        return "B"
    return "C" if score >= 2 else "D"


@pytest.fixture(scope="module")
def catalog() -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(CATALOG.read_text(encoding="utf-8"))
    return doc


@pytest.fixture(scope="module")
def rows(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["key"]: row for row in catalog["rows"]}


def test_every_row_names_a_lean_statement(catalog: dict[str, Any]) -> None:
    """R11: a problem with no Lean statement does not appear; every row is a registry file."""
    assert catalog["schema"] == "lean-conjecture-catalog/v1"
    assert catalog["count"] == len(catalog["rows"]) > 1000
    keys = [row["key"] for row in catalog["rows"]]
    assert len(keys) == len(set(keys)), "a key appears twice"
    for row in catalog["rows"]:
        assert row["file"].startswith("FormalConjectures/") and row["file"].endswith(".lean"), row
        assert re.fullmatch(r"[0-9a-f]{40}", catalog["fc_commit"])
        if row["kind"] == "fc":
            assert row["decl"] and row["key"] == f"fc:{row['file']}#{row['decl']}", row["key"]
        else:
            assert row["kind"] == "erdos" and row["key"].startswith("erdos:"), row["key"]


def test_every_letter_is_the_one_its_score_gives(catalog: dict[str, Any]) -> None:
    for row in catalog["rows"]:
        assert row["letter"] == expected_letter(row["score"]), (row["key"], row["score"])
        if row["score"] is not None:
            assert row["reasons"], row["key"]
            signed = re.findall(r"^([+-]\d+) ", "\n".join(row["reasons"]), re.M)
            assert sum(int(p) for p in signed) == row["score"], (row["key"], row["reasons"])


def test_the_riemann_hypothesis_grades_a(rows: dict[str, dict[str, Any]]) -> None:
    """F14-Q6, Q8: the registry's `riemannHypothesis` is Mathlib's own definition, so the Mathlib
    predicate grades it, and it clears the high grade on its own evidence."""
    row = rows[RIEMANN]
    assert row["mathlib_definition"] == "RiemannHypothesis"
    assert row["letter"] == "A" and row["score"] >= 6, row["reasons"]
    assert any("Mathlib's own `RiemannHypothesis`" in r for r in row["reasons"])


def test_oeis_open_is_never_high(catalog: dict[str, Any]) -> None:
    """Report §2: OEIS Open is not eligible, so no OEIS row reaches the high grade."""
    oeis = [row for row in catalog["rows"] if row["srcdir"] == "OEIS" and row["score"] is not None]
    assert oeis, "guard: the registry has OEIS rows"
    assert all(row["score"] < HIGH for row in oeis)


def test_erdos_letters_agree_with_the_f11_dataset(rows: dict[str, dict[str, Any]]) -> None:
    """AC11: where an Erdős problem kept the points it had on 2026-09-08, it kept its letter, with
    B read as B+ at five points; and the five listed targets are still high-graded."""
    dataset = json.loads(F11_DATASET.read_text(encoding="utf-8"))
    compared = 0
    for problem in dataset["problems"]:
        old = re.match(r"([ABCD]) \(\+?(-?\d+)\)", problem["trust_text"])
        if old is None:  # n/a in 2026-09: a closed problem or no open statement
            continue
        row = rows.get(f"erdos:{problem['number']}")
        assert row is not None, problem["number"]
        if row["score"] != int(old.group(2)):
            continue
        compared += 1
        letter = old.group(1)
        expected = ("B+" if row["score"] == HIGH else "B") if letter == "B" else letter
        assert row["letter"] == expected, (problem["number"], letter, row["letter"])
    assert compared > 250, f"only {compared} problems kept their score; read the rebuild's evidence"
    for number in LIVE_ERDOS:
        assert rows[f"erdos:{number}"]["score"] >= HIGH, (
            number,
            rows[f"erdos:{number}"]["reasons"],
        )
