"""F14-T17: the catalog build reads its inputs as they are today, not as they were in September.

Three inputs of ``docs/seed_conjecture_sources_build.py`` rotted between the first build
(2026-09-08) and the wave-two rebuild (2026-11-21), and each one silently changed every grade:

- the scoring date was a constant, so a rebuild in November read every file touched in October as
  "modified in the last 30 days" and docked the whole registry a point;
- erdosproblems.com became a client-rendered page with no status markup, so every Erdős row read as
  "status ?, not a seed candidate" although the status database the build already clones carries
  the state;
- Epoch removed its ``erdos_autoformalized`` subset, so the build died before writing anything.

These tests drive the build's own functions with inputs shaped like today's.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "docs" / "seed_conjecture_sources_build.py"


@pytest.fixture(scope="module")
def build() -> ModuleType:
    spec = importlib.util.spec_from_file_location("seed_conjecture_sources_build", BUILD)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _history(today: dt.date, *, first_days_ago: int, last_days_ago: int) -> dict[str, str | int]:
    return {
        "first": (today - dt.timedelta(days=first_days_ago)).isoformat(),
        "last": (today - dt.timedelta(days=last_days_ago)).isoformat(),
        "n": 3,
    }


def test_scoring_reads_the_clock_not_a_constant(build: ModuleType) -> None:
    """A file last touched 45 days ago is not "modified in the last 30 days", whatever month the
    build happens to run in; and one public for 400 days has earned its age point."""
    today = dt.date.today()
    decl = {
        "category": "research open",
        "formal_proof": None,
        "statement": "∀ n, P n",
        "name": "x",
        "doc": "",
        "value_typed": False,
    }
    hist = _history(today, first_days_ago=400, last_days_ago=45)
    score, letter, reasons, _ = build.score_decl(
        decl, {"local_defs": []}, "FormalConjectures/Wikipedia/X.lean", hist, [], {}
    )
    assert not any(r.startswith("-1 file modified") for r in reasons), reasons
    assert any("180+ days" in r for r in reasons), reasons
    assert score is not None and letter == build.letter_of(score)


def test_erdos_status_comes_from_the_database_when_the_page_carries_none(build: ModuleType) -> None:
    """erdosproblems.com's page is client-rendered now: ``parse_site`` returns a dict with no
    ``status``. The status database (``ep/data/problems.yaml``) says the problem is open, so the
    row is a seed candidate; a database state of "disproved (Lean)" still excludes it."""
    today = dt.date.today()
    base = {
        "num": 1094,
        "open_stmts": [{"name": "erdos_1094", "doc": ""}],
        "issues": [],
        "hist": _history(today, first_days_ago=400, last_days_ago=45),
        "lean": {"local_defs": []},
        "hazards": [],
        "main_open": {"value_typed": False},
        "wiki": [],
        "_bloom70": set(),
        "_fc48": {},
        "_auto18": {},
        "_nexus_att": {},
        "_nexus_solved": {},
    }
    page_without_status = {"statement": "", "refs": [], "tags": [], "oeis": []}
    open_row = dict(
        base,
        site=page_without_status,
        db={"status": {"state": "open", "last_update": "2025-10-18"}},
    )
    score, letter, reasons = build.score_row(open_row)
    assert score is not None, reasons
    assert letter == build.letter_of(score)

    closed_row = dict(base, site=page_without_status, db={"status": {"state": "disproved (Lean)"}})
    score, letter, reasons = build.score_row(closed_row)
    assert score is None and letter == "n/a"
    assert any("disproved (Lean)" in r for r in reasons), reasons


def test_epoch_autoformalized_subset_is_optional(build: ModuleType, tmp_path: Path) -> None:
    """Epoch removed ``erdos_autoformalized/``; the build reads the subsets it still publishes and
    treats the removed one as empty rather than dying before it writes anything."""
    data = tmp_path / "epoch" / "apn" / "data" / "erdos"
    (data / "subsets").mkdir(parents=True)
    (data / "metadata" / "snapshots").mkdir(parents=True)
    (data / "ERDOS_PROBLEM_STATEMENT_SELECTION.md").write_text(
        "selected 70 Erdős problem numbers:\n\n> 1, 2, 3\n\n", encoding="utf-8"
    )
    (data / "subsets" / "bloom_selection.json").write_text(
        json.dumps({"ids": ["Erdos1.main"]}), encoding="utf-8"
    )
    (data / "metadata" / "snapshots" / "bloom_top10.json").write_text(
        json.dumps({"entries": [{"problems": [1]}]}), encoding="utf-8"
    )
    bloom70, fc48, auto18, top = build.load_epoch(str(tmp_path))
    assert bloom70 == {1, 2, 3} and fc48 == {1: ["main"]} and top == {1}
    assert auto18 == {}


def test_a_name_declared_in_two_namespaces_keys_two_rows(build: ModuleType, tmp_path: Path) -> None:
    """`Millennium/BSD.lean` states `weakBSD` once for a number field and once for the rationals;
    the catalog's key is the file and the declaration, so the repeated short name is qualified by
    its namespace while a unique name keeps the short key every earlier catalog used."""
    src = tmp_path / "BSD.lean"
    src.write_text(
        "namespace WeierstrassCurve\n"
        "namespace NumberField\n"
        "@[category research open, AMS 11]\n"
        "theorem weakBSD : True := by\n  sorry\n"
        "end NumberField\n"
        "namespace Rat\n"
        "@[category research open, AMS 11]\n"
        "theorem weakBSD : True := by\n  sorry\n"
        "@[category research open, AMS 11]\n"
        "theorem onlyOnce : True := by\n  sorry\n"
        "end Rat\n"
        "end WeierstrassCurve\n",
        encoding="utf-8",
    )
    names = [d["name"] for d in build.parse_lean(str(src))["decls"]]
    assert names == [
        "WeierstrassCurve.NumberField.weakBSD",
        "WeierstrassCurve.Rat.weakBSD",
        "onlyOnce",
    ]
