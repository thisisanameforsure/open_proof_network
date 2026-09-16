"""F15-AC9 (F05-Q5): the api's index fixtures are golden copies from the gate, by recipe.

``targets-index-listed.json`` and ``targets-index-frozen.json`` (with their ``frontier-*.json``)
are what the gate renders for the propositional fixture plus one curated target — listed and
claimable, or listed with an upstream edit frozen on its root. F12-T6's evidence recorded the
recipe in prose and it took three tries to rediscover; this test *is* the recipe, so a schema
bump regenerates the fixtures with ``write_fixtures()`` and the suite says when they drift.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from harness import copy_graph, freeze_upstream, take_in

from opn_gate import products

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RENDERED_FROM = "5" * 40
COMMIT_TIME = "2026-09-09T12:00:00Z"
DEFS = {"Primes.lean": "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p\n"}
#: fixture stem -> (target id, root id, frozen)
RECIPES: dict[str, tuple[str, str, bool]] = {
    "listed": ("listed-target", "listed-lemma", False),
    "frozen": ("frozen-target", "frozen-lemma", True),
}


def render(tmp: Path, target_id: str, root_id: str, *, frozen: bool) -> products.Products:
    root = copy_graph(tmp, publish=True)
    staged = tmp / root_id
    shutil.copytree(root / "targets/propositional/nodes/and-reassoc", staged)
    meta = yaml.safe_load((staged / "META.yaml").read_text(encoding="utf-8"))
    meta["id"] = root_id
    (staged / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    take_in(root, target_id, root_dir=staged, defs=DEFS)
    if frozen:
        freeze_upstream(root / "targets" / target_id)
    return products.generate(root, rendered_from=RENDERED_FROM, commit_time=COMMIT_TIME)


def write_fixtures(base: Path = FIXTURES) -> None:
    """Regenerate the four fixtures (review the diff before committing it with its task)."""
    import tempfile  # noqa: PLC0415

    for stem, (target_id, root_id, frozen) in RECIPES.items():
        with tempfile.TemporaryDirectory() as tmp:
            prod = render(Path(tmp), target_id, root_id, frozen=frozen)
            (base / f"targets-index-{stem}.json").write_bytes(
                prod.files[Path("targets/index.json")]
            )
            (base / f"frontier-{stem}.json").write_bytes(prod.files[Path("frontier.json")])


@pytest.mark.parametrize("stem", sorted(RECIPES))
def test_fixture_is_a_golden_copy(tmp_path: Path, stem: str) -> None:
    target_id, root_id, frozen = RECIPES[stem]
    prod = render(tmp_path, target_id, root_id, frozen=frozen)
    assert (
        prod.files[Path("targets/index.json")]
        == (FIXTURES / f"targets-index-{stem}.json").read_bytes()
    ), f"targets-index-{stem}.json drifted from the gate; run write_fixtures()"
    assert prod.files[Path("frontier.json")] == (FIXTURES / f"frontier-{stem}.json").read_bytes(), (
        f"frontier-{stem}.json drifted from the gate; run write_fixtures()"
    )
