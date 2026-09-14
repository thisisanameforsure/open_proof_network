# ruff: noqa: RUF001 — the registry fixtures are Lean source, with its double-struck letters
"""F14-T11: the wave driver (R13; AC13).

A miniature registry at a pin: a clean Erdős row, one using a helper-library name, one using a
file-local definition, a value-typed one, one with binders before its colon, and a second clean
row. The driver drafts the clean two, refuses each of the others by name, and the drafts import
through ``intake import-fc`` with their catalog evidence and classify as intake pull requests.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph
from test_intake import import_fc

from opn_gate import intake, layout, modes, schemas
from opn_gate.paths import Change

TOOL = Path(__file__).resolve().parents[1] / "tools" / "wave.py"
HEADER = (
    "/-\nCopyright 2025 The Formal Conjectures Authors.\n\n"
    'Licensed under the Apache License, Version 2.0 (the "License");\n-/\n\n'
)
PIN = "c" * 40
NETWORK = "1" * 40
CURATORS = modes.Curators((("curator", "curator"),))


def load_tool() -> Any:
    spec = importlib.util.spec_from_file_location("wave", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # a dataclass resolves its module's namespace at definition
    spec.loader.exec_module(module)
    return module


def registry_file(n: int, body: str, *, before: str = "") -> str:
    return (
        f"{HEADER}import FormalConjecturesUtil\n\nopen scoped Pointwise\n\nnamespace Erdos{n}\n\n"
        f"{before}/--\nA question about {n}.\n-/\n@[category research open, AMS 11]\n"
        f"theorem erdos_{n}{body} := by\n  sorry\n\nend Erdos{n}\n"
    )


FILES: dict[int, str] = {
    7001: registry_file(7001, " : answer(sorry) ↔ ∀ n : ℕ, n ≤ n + 1"),
    7002: registry_file(7002, " : answer(sorry) ↔ ∀ S : Set ℕ, S.IsAPOfLength 3"),
    7003: registry_file(
        7003, " : answer(sorry) ↔ ∀ n : ℕ, Good n", before="def Good (n : ℕ) : Prop := n = n\n\n"
    ),
    7004: registry_file(7004, " : (7 : ℕ) = answer(sorry)"),
    7005: registry_file(7005, " (n : ℕ) (h : 0 < n) : n ≤ n + 1"),
    7006: registry_file(7006, " : ∃ n : ℕ, n = 7006"),
}
#: Rows the refined helper and name rules must draft: a dotted declaration name, a bound variable
#: named like a helper definition, and a dotted Mathlib member the helper library also declares as
#: a theorem or under an unrelated namespace.
EXTRA: dict[int, str] = {
    7009: (
        f"{HEADER}import FormalConjecturesUtil\n\nnamespace Erdos7009\n\n"
        "@[category research open, AMS 11]\ntheorem erdos_7009.parts.i : answer(sorry) ↔ "
        "∀ S : Finset ℕ, S.card ≤ S.card + 1 := by\n  sorry\n\n"
        "@[category research open, AMS 11]\ntheorem erdos_7009.parts.ii : 1 = 1 := by\n  sorry\n\n"
        "end Erdos7009\n"
    ),
    # A helper defined in a namespace the file opens, used bare: still a helper.
    7012: registry_file(7012, " : answer(sorry) ↔ ∀ n : ℕ, 0 < hyperRamsey n"),
    # A helper inside a type ascription, after binder groups: an ascription binds nothing.
    7014: registry_file(
        7014, " : answer(sorry) ↔ ∃ (A : Set ℕ) (c : ℝ), (hyperRamsey c.toNat : ℝ) = c"
    ),
    # A helper written out with its own namespace: still a helper.
    7013: registry_file(7013, " : answer(sorry) ↔ ∀ x : ℝ, Geometry.area x = x"),
    7010: (
        f"{HEADER}import FormalConjecturesUtil\n\nnamespace Erdos7010\n\n"
        "@[category research open, AMS 11]\ntheorem erdos_7010 : answer(sorry) ↔\n"
        "    ∀ a : ℕ → ℕ, StrictMono a → a 0 ≤ a 1 :=\n  sorry\n\nend Erdos7010\n"
    ),
}


def catalog_doc() -> dict[str, Any]:
    def row(n: int, **kw: Any) -> dict[str, Any]:
        doc = {
            "key": f"erdos:{n}",
            "kind": "erdos",
            "srcdir": "ErdosProblems",
            "file": f"FormalConjectures/ErdosProblems/{n}.lean",
            "decl": f"erdos_{n}",
            "score": 6,
            "letter": "A",
            "reasons": ["+2 Bloom selected it", "+2 attempted by AlphaProof Nexus", "+1 a", "+1 b"],
            "site_status": "OPEN",
            "history": {"first": "2025-04-26", "last": "2026-07-16", "n": 3},
            "issues": [],
            "local_defs": [],
            "imports": ["FormalConjecturesUtil"],
            "statements": [f"erdos_{n}"],
            "docstring": f"A question about {n}.",
            "value_typed": False,
            "hazards": [],
            "mathlib_definition": None,
            "ams": ["11"],
            "nexus_attempted": [f"erdos_{n}"],
        }
        doc.update(kw)
        return doc

    return {
        "schema": "lean-conjecture-catalog/v1",
        "fc_commit": PIN,
        "mathlib_rev": "0df444a360eaa60ab8c11dca51a86af692955474",
        "nexus_published": "2026-05-13",
        "rows": [
            row(7001),
            row(7002),
            row(7003, local_defs=["Good"]),
            row(7004, value_typed=True),
            row(7005),
            row(7006),
            row(
                7009, decl="erdos_7009.parts.i"
            ),  # a dotted declaration name, as the file writes it
            row(7010),  # a term-mode `:= sorry` body
            # The open statement is a variant of a problem resolved upstream: never drafted as it.
            row(7011, decl="erdos_7011.variants.generalisation"),
            row(7012),
            row(7013),
            row(7014),
            row(7007, score=4, letter="B"),  # below the minimum: not chosen at all
            row(7008, site_status="PROVED (LEAN)"),  # closed: not chosen
        ],
    }


@pytest.fixture
def wave(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    fc = tmp_path / "fc"
    for n, text in {**FILES, **EXTRA}.items():
        path = fc / "FormalConjectures" / "ErdosProblems" / f"{n}.lean"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    helpers = fc / "FormalConjecturesForMathlib" / "Combinatorics" / "AP.lean"
    helpers.parent.mkdir(parents=True)
    helpers.write_text(
        "namespace Set\ndef IsAPOfLength (s : Set ℕ) (k : ℕ) : Prop := True\nend Set\n"
        # A definition named like a bound variable, under a namespace no statement opens:
        "namespace Degrees\ndef S (n : ℕ) : ℕ := n\nend Degrees\n"
        "namespace Ramsey\ndef hyperRamsey (n : ℕ) : ℕ := n\nend Ramsey\n"
        "namespace Geometry\ndef area (x : ℝ) : ℝ := x\nend Geometry\n"
        # A theorem named like a Mathlib member (`card`): a theorem is not vocabulary.
        "namespace Set.IsAPOfLengthWith\ntheorem card : True := trivial\nend Set.IsAPOfLengthWith\n"
    )
    catalog = tmp_path / "catalog.json"
    doc = catalog_doc()
    catalog.write_text(json.dumps(doc), encoding="utf-8")
    out = tmp_path / "wave1"
    tool = load_tool()
    assert tool.main(["--catalog", str(catalog), "--fc", str(fc), "--out", str(out)]) == 0
    result = {"out": out, "fc": fc}
    return out, result, doc


def test_the_clean_rows_are_drafted_and_the_rest_refused_by_name(
    wave: tuple[Path, dict[str, Any], dict[str, Any]], capsys: pytest.CaptureFixture[str]
) -> None:
    out, _result, _doc = wave
    report = (out / "REPORT.md").read_text(encoding="utf-8")
    assert "Drafted 4, refused 8." in report
    assert (
        "`erdos:7014`: uses names FormalConjecturesForMathlib declares (port first): hyperRamsey"
        in report
    )
    assert (
        "`erdos:7012`: uses names FormalConjecturesForMathlib declares (port first): hyperRamsey"
        in report
    )
    assert (
        "`erdos:7013`: uses names FormalConjecturesForMathlib declares (port first): area" in report
    )
    assert (
        "`erdos:7011`: the open statement is a variant (erdos_7011.variants.generalisation)"
        in report
    )
    record = yaml.safe_load((out / "erdos-7009" / "record.yaml").read_text(encoding="utf-8"))
    assert record["title"].startswith("Erdős problem 7009, part i: ")
    assert sorted(p.name for p in out.iterdir() if p.is_dir()) == [
        "erdos-7001",
        "erdos-7006",
        "erdos-7009",
        "erdos-7010",
        "upstream",
    ]
    # The bound `S` and the dotted Mathlib member `card` in erdos_7009 are not helper uses.
    theorem = (out / "erdos-7009" / "Statement.lean").read_text(encoding="utf-8")
    assert "∀ S : Finset ℕ, S.card ≤ S.card + 1 := by" in theorem
    assert (
        "`erdos:7002`: uses names FormalConjecturesForMathlib declares (port first): IsAPOfLength"
        in report
    )
    assert "`erdos:7003`: uses file-local definitions (port into defs/): Good" in report
    assert "`erdos:7004`: value-typed" in report
    assert "`erdos:7005`: binders before the colon" in report
    assert "7007" not in report and "7008" not in report


def test_a_draft_keeps_the_header_and_states_the_proposition(
    wave: tuple[Path, dict[str, Any], dict[str, Any]],
) -> None:
    out, _result, _doc = wave
    statement = (out / "erdos-7001" / "Statement.lean").read_text(encoding="utf-8")
    header = intake.copyright_header(FILES[7001])
    assert header is not None and statement.startswith(header)
    assert "import Mathlib\n" in statement and "FormalConjecturesUtil" not in statement
    assert "open scoped Pointwise\n" in statement and "namespace" not in statement
    parsed = layout.parse_statement(statement)
    assert isinstance(parsed, layout.Statement) and parsed.decl_name == "Opn.erdos_7001"
    theorem = statement[statement.index("theorem Opn.") :]
    assert "answer(sorry)" not in theorem and "∀ n : ℕ, n ≤ n + 1 := by" in theorem
    record = yaml.safe_load((out / "erdos-7001" / "record.yaml").read_text(encoding="utf-8"))
    schemas.validate(record, intake.SCHEMA)
    assert record["informal"] == "A question about 7001." and record["domains"] == ["number-theory"]
    assert "Catalog score 6 (A)" in record["prior_art"]["summary"]
    script = (out / "import.sh").read_text(encoding="utf-8")
    assert (
        "--key erdos:7001" in script and "--key erdos:7006" in script and "erdos:7002" not in script
    )
    assert "--evidence-from" in script and '--network-commit "$NETWORK"' in script


def test_the_drafts_import_with_their_evidence_and_classify_as_intakes(
    wave: tuple[Path, dict[str, Any], dict[str, Any]], tmp_path: Path
) -> None:
    out, _result, doc = wave
    root = copy_graph(tmp_path / "graph-parent", publish=True)
    for n in (7001, 7006):
        target_id = f"erdos-{n}"
        directory = out / target_id
        rel = f"FormalConjectures/ErdosProblems/{n}.lean"
        imported = import_fc(
            root,
            target_id=target_id,
            source=out / "upstream" / rel,
            rel_path=rel,
            commit=PIN,
            base=yaml.safe_load((directory / "record.yaml").read_text(encoding="utf-8")),
            witness=(directory / "Witness.lean").read_text(encoding="utf-8"),
            statement=(directory / "Statement.lean").read_text(encoding="utf-8"),
            evidence_catalog=doc,
            evidence_key=f"erdos:{n}",
            network_commit=NETWORK,
        )
        assert imported.evidence, target_id
        target = root / "targets" / target_id
        changes = [
            Change("A", p.relative_to(root).as_posix())
            for p in sorted(target.rglob("*"))
            if p.is_file()
        ]
        c = modes.classify(changes, author="curator", curators=CURATORS)
        assert c.mode == "intake", (target_id, c.as_dict())
        assert modes.check(root, c) == [], target_id
