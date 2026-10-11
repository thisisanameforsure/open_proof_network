"""F25-T1 / AC4, derivation half (F25-R5, R7; D-3, D-10 v3.37): registration records are derived,
never rewritten — the latest per registry id wins, a record with no id yet is keyed by its
wrapper commit, a withdrawn registration reads as absent, and the products carry the result.

The admission half (the gate's mode row, F25-T4) lives in ``test_modes_registration.py``.
Each derivation rule is also shown *necessary*: a mutant that drops it fails at least one of
the scenarios below (the F11-T7 pattern, in memory, no file touched).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import copy_graph, take_in

from opn_gate import products, registrations, schemas

TARGET = "listed-target"


def write(target_dir: Path, name: str, **overrides: Any) -> Path:
    where = registrations.directory(target_dir)
    where.mkdir(exist_ok=True)
    path = where / f"{name}.yaml"
    doc = samples.registration(target=TARGET, **overrides)
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return path


def published(target_dir: Path) -> list[tuple[str | None, int | None, str]]:
    return [(r["registry_id"], r["version"], r["status"]) for r in registrations.derive(target_dir)]


# --- scenarios ---------------------------------------------------------------------------------


def scenario_latest_wins(d: Path) -> None:
    write(d, "2026-10-12-1", status="submitted", url=None, version=None)
    write(d, "2026-10-13-1", date="2026-10-13", status="registered", version=1)
    assert published(d) == [("PALOMAR-2026-10-12-000003", 1, "registered")]


def scenario_out_of_order_names(d: Path) -> None:
    """The date decides, not the file name: a record filed under a later name but an earlier
    date is the earlier one."""
    write(d, "2026-10-20-1", date="2026-10-11", status="submitted", version=None)
    write(d, "2026-10-12-1", date="2026-10-12", status="registered", version=1)
    assert published(d) == [("PALOMAR-2026-10-12-000003", 1, "registered")]


def scenario_two_ids(d: Path) -> None:
    write(d, "2026-10-12-1")
    other = {"repository": "o/r", "commit": "e" * 40}
    write(d, "2026-10-12-2", registry_id="PALOMAR-2026-10-12-000004", wrapper=other)
    assert [r for _, _, r in published(d)] == ["registered", "registered"]
    ids = [i for i, _, _ in published(d)]
    assert ids == ["PALOMAR-2026-10-12-000003", "PALOMAR-2026-10-12-000004"]


def scenario_withdrawn_is_absent(d: Path) -> None:
    write(d, "2026-10-12-1")
    write(d, "2026-10-14-1", date="2026-10-14", status="withdrawn")
    assert published(d) == []


def scenario_superseded_version(d: Path) -> None:
    write(d, "2026-10-12-1", version=1)
    other = {"repository": "o/r", "commit": "f" * 40}
    write(d, "2026-10-15-1", date="2026-10-15", version=2, wrapper=other)
    assert published(d) == [("PALOMAR-2026-10-12-000003", 2, "registered")]


def scenario_pending_keyed_by_wrapper(d: Path) -> None:
    """Two submissions with no id yet are two registrations, keyed by what was submitted."""
    write(d, "2026-10-12-1", registry_id=None, version=None, status="submitted", url=None)
    other = {"repository": "o/r", "commit": "e" * 40}
    write(d, "2026-10-12-2", registry_id=None, version=None, status="submitted", url=None,
          wrapper=other)  # fmt: skip
    assert published(d) == [(None, None, "submitted"), (None, None, "submitted")]


def scenario_invalid_file_is_passed_over(d: Path) -> None:
    write(d, "2026-10-12-1")
    where = registrations.directory(d)
    (where / "2026-10-13-1.yaml").write_text("schema: registration/v1\nstatus: nonsense\n")
    (where / "notes.txt").write_text("ignored\n")
    assert published(d) == [("PALOMAR-2026-10-12-000003", 1, "registered")]


SCENARIOS: dict[str, Callable[[Path], None]] = {
    k[len("scenario_") :]: v for k, v in dict(globals()).items() if k.startswith("scenario_")
}


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario(tmp_path: Path, name: str) -> None:
    SCENARIOS[name](tmp_path)


def test_no_directory_is_no_registration(tmp_path: Path) -> None:
    assert registrations.derive(tmp_path) == []
    assert registrations.load(tmp_path) == []


# --- the mutants: each rule is load-bearing ------------------------------------------------


Latest = dict[str, registrations.Record]


def _mutant_last_file_name_wins(records: list[registrations.Record]) -> Latest:
    out: dict[str, registrations.Record] = {}
    for rec in sorted(records, key=lambda r: r.path.name):
        out[rec.key] = rec
    return out


def _mutant_first_wins(records: list[registrations.Record]) -> Latest:
    out: dict[str, registrations.Record] = {}
    for rec in records:
        out.setdefault(rec.key, rec)
    return out


def _mutant_withdrawn_published(target_dir: Path) -> list[dict[str, Any]]:
    return [
        {k: rec.doc.get(k) for k in registrations.PUBLISHED_FIELDS}
        for rec in registrations.latest(registrations.load(target_dir)).values()
    ]


def _mutant_key_ignores_wrapper(self: registrations.Record) -> str:
    rid = self.doc.get("registry_id")
    return f"{self.doc['registry']}:{rid}"


@pytest.mark.parametrize(
    ("where", "attr", "mutant"),
    [
        (registrations, "latest", _mutant_last_file_name_wins),
        (registrations, "latest", _mutant_first_wins),
        (registrations, "derive", _mutant_withdrawn_published),
        (registrations.Record, "key", property(_mutant_key_ignores_wrapper)),
    ],
    ids=["file-name-order", "first-wins", "withdrawn-published", "pending-share-a-key"],
)
def test_each_rule_is_necessary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, where: Any, attr: str, mutant: Any
) -> None:
    monkeypatch.setattr(where, attr, mutant)
    failures = 0
    for i, (name, scenario) in enumerate(sorted(SCENARIOS.items())):
        d = tmp_path / f"{i}-{name}"
        d.mkdir()
        try:
            scenario(d)
        except AssertionError:
            failures += 1
    assert failures >= 1, "the mutant passed every scenario: a rule is untested"


# --- the products carry the derivation (R7) ------------------------------------------------


def test_the_products_publish_registrations(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    take_in(root, TARGET)
    write(root / "targets" / TARGET, "2026-10-12-1")
    tdir = root / "targets" / TARGET
    write(tdir, "2026-10-14-1", date="2026-10-14", status="registered", version=2)
    prod = products.generate(root, rendered_from="5" * 40, commit_time="2026-10-14T12:00:00Z")
    index = json.loads(prod.files[Path("targets/index.json")])
    assert index["schema"] == "targets-index/v10"
    assert schemas.violations(index, "targets-index/v10") == []
    row = next(r for r in index["targets"] if r["target_id"] == TARGET)
    expected = [
        {
            "registry": "palomar",
            "registry_id": "PALOMAR-2026-10-12-000003",
            "version": 2,
            "status": "registered",
            "url": "https://palomar-registry.org/entries/PALOMAR-2026-10-12-000003",
        }
    ]
    assert row["registrations"] == expected
    other = next(r for r in index["targets"] if r["target_id"] != TARGET)
    assert other["registrations"] == []
    graph = json.loads(prod.files[Path(f"targets/{TARGET}/graph.json")])
    assert graph["schema"] == "graph/v7"
    assert schemas.violations(graph, "graph/v7") == []
    assert graph["registrations"] == expected
