# ruff: noqa: RUF001 — the fixtures are Lean source, with its double-struck letters
"""Finding wave-id-collisions (2026-11-24): the bulk load never drafted 376 open statements.

``wave.target_id_for`` named a row by its declaration's last segment, so every registry row
whose last segment another row shared was given the same target id: `i` and `ii` for Oppermann's,
Artin's primitive-roots and Green 17's parts, `conjecture`, `conjecture_1`, `upper`, `lower`
and 24 more, 28 ids claimed by 404 rows. The admission workflow skips a row whose id is live, so
once Oppermann's `i` landed, Artin's and Green's parts read as already imported; and the ids
nobody held collided inside one run.

Now every row the catalog can draft gets an id of its own. A short id one row alone claims is
unchanged, so no live target moves. Where several rows claim one, the row the graph already holds
under it keeps it (``docs/lean_conjecture_holders.json``, each holder matched to the live
statement text) and every other row is named by its registry file and full declaration. A live
id that comes to be shared by a new row without a named holder is refused by name, never
guessed: guessing wrong drafts the live statement a second time.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("wave", ROOT / "gate" / "tools" / "wave.py")
assert spec is not None and spec.loader is not None
wave = importlib.util.module_from_spec(spec)
sys.modules["wave"] = wave
spec.loader.exec_module(wave)

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def row(file: str, decl: str) -> dict[str, Any]:
    return {"key": f"fc:{file}#{decl}", "kind": "fc", "file": file, "decl": decl}


OPPERMANN = row("FormalConjectures/Wikipedia/Oppermann.lean", "oppermann_conjecture.parts.i")
ARTIN = row(
    "FormalConjectures/Wikipedia/ArtinPrimitiveRootsConjecture.lean",
    "artin_primitive_roots.parts.i",
)
GREEN = row("FormalConjectures/GreensOpenProblems/17.lean", "green_17.parts.i")
ALONE = row("FormalConjectures/Wikipedia/Singmaster.lean", "singmaster")


def test_a_short_id_one_row_claims_is_unchanged() -> None:
    ids = wave.assign_ids([ALONE, OPPERMANN, ARTIN], live=set(), holders={})
    assert ids[ALONE["key"]] == "singmaster"


def test_the_holder_keeps_a_shared_id_and_the_others_are_qualified() -> None:
    ids = wave.assign_ids([OPPERMANN, ARTIN, GREEN], live={"i"}, holders={"i": OPPERMANN["key"]})
    assert ids[OPPERMANN["key"]] == "i"
    assert ids[ARTIN["key"]] == "artin-primitive-roots-conjecture-artin-primitive-roots-parts-i"
    assert ids[GREEN["key"]] == "greens-open-problems-17-green-17-parts-i"


def test_a_shared_id_nobody_holds_is_qualified_for_every_row() -> None:
    ids = wave.assign_ids([ARTIN, GREEN], live=set(), holders={})
    assert len(set(ids.values())) == 2
    assert "i" not in ids.values()


def test_a_live_shared_id_without_a_named_holder_is_refused() -> None:
    with pytest.raises(wave.WaveError, match=r"\bi\b.*holder"):
        wave.assign_ids([OPPERMANN, ARTIN], live={"i"}, holders={})


def test_a_holder_that_names_no_claimant_is_refused() -> None:
    with pytest.raises(wave.WaveError, match="holder"):
        wave.assign_ids([OPPERMANN, ARTIN], live={"i"}, holders={"i": GREEN["key"]})


BUCHI = row("FormalConjectures/Wikipedia/Buchi.lean", "buchi_problem_M5")


def test_a_held_row_keeps_a_live_id_the_rule_no_longer_computes() -> None:
    """T25 collapsed `--` after `buchi-problem--m5` was imported, so the rule now says
    `buchi-problem-m5`, the workflow read the row as not yet live, and graph #1903 imported the
    same statement a second time. A holder names the row's live id, whatever the rule says."""
    ids = wave.assign_ids(
        [BUCHI], live={"buchi-problem--m5"}, holders={"buchi-problem--m5": BUCHI["key"]}
    )
    assert ids[BUCHI["key"]] == "buchi-problem--m5"


def test_the_row_carries_its_assigned_id_into_the_draft() -> None:
    assert wave.target_id_for({**ARTIN, "target_id": "assigned"}) == "assigned"
    assert wave.target_id_for(ARTIN) == "i"  # the short id, unassigned


def test_the_catalog_gives_every_draftable_row_an_id_of_its_own() -> None:
    catalog = json.loads((ROOT / "docs" / "lean_conjecture_catalog.json").read_text("utf-8"))
    holders = wave.load_holders()
    ids = wave.assign_ids(catalog["rows"], live=set(holders), holders=holders)
    values = list(ids.values())
    assert len(values) == len(set(values)), "two rows share a target id"
    # A target id is its root node's id, and a node id is at most 64 characters (the intake of
    # Artin's parts was refused at 73).
    too_long = [v for v in values if len(v) > 64]
    assert not too_long, f"{len(too_long)} ids over 64 characters, e.g. {too_long[:2]}"
    assert all(ID_RE.match(v) for v in values)
    for target_id, key in holders.items():
        assert ids[key] == target_id


# --- the declaration a distinct id names (the admission run of 2026-11-24) ---------------------

TWO_NAMESPACES = """\
namespace riemannZeta

theorem distinct_prop_lt : ∃ c > (1 : ℝ), c = c := by
  sorry

end riemannZeta

namespace DirichletCharacter

theorem distinct_prop_lt (hχ : χ.IsPrimitive) : ∃ c > (2 : ℝ), c = c := by
  sorry

end DirichletCharacter
"""


def test_a_short_name_two_declarations_share_is_refused() -> None:
    """Given ids of their own, the two ``DirichletCharacter`` rows were drafted and admitted, but
    each carried the ``riemannZeta`` statement: the extractor fell back to the short name and
    took the first theorem by it, so the import would have put the live statement on the record a
    second time under another target's name. An ambiguous short name is refused by name."""
    prop, how, _ = wave.extract(TWO_NAMESPACES, "DirichletCharacter.distinct_prop_lt")
    assert prop is None
    assert "distinct_prop_lt" in how and "2" in how


def test_a_short_name_one_declaration_holds_is_still_found() -> None:
    text = TWO_NAMESPACES.split("namespace DirichletCharacter", maxsplit=1)[0]
    prop, how, _ = wave.extract(text, "riemannZeta.distinct_prop_lt")
    assert prop == "∃ c > (1 : ℝ), c = c"
    assert how == "as stated"
