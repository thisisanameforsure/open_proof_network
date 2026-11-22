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


#: The registry's files are Lean modules (F14-T19): `module`, `public import`, an exposed public
#: section, and attributes that may span lines; a port strips the module syntax.
MODULE_HEAD = (
    f"{HEADER}module\n\npublic import FormalConjecturesUtil\n\n@[expose] public section\n\n"
)


def registry_file(n: int, body: str, *, before: str = "") -> str:
    return (
        f"{MODULE_HEAD}open scoped Pointwise\n\nnamespace Erdos{n}\n\n"
        f"{before}/--\nA question about {n}.\n-/\n@[category research open,\n  AMS 11]\n"
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
    # F14-T19: plain data binders before the colon close into the witness like leading ∀s do;
    # 7005's hypothesis binder is still the curator's.
    7025: registry_file(7025, " (n : ℕ) : n ≤ n + 1"),
    # F14-T19: a notation the helper library declares (`ℝ²` lives in Geometry/2d.lean) is not a
    # name, so the port follows notation literals too.
    7026: registry_file(7026, " : ∀ x : ℝ², x = x", before="open Plane\n\n"),
    # F14-T19: a definition the registry leaves as `sorry` (an answer) is a question in disguise.
    7027: registry_file(
        7027, " : erdos_7027.answer = 1", before="def erdos_7027.answer : ℕ := by sorry\n\n"
    ),
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
    # F14-T15, live: hypotheses after the colon make step 7's witness type something other than
    # `True`, so these are refused; an `∃` (bounded or not) carries none and is drafted.
    7015: registry_file(7015, " : ∀ n > 1, n ≤ n * n"),
    7016: registry_file(7016, " : ∀ (A : Set ℕ), A.Infinite → A.Nonempty"),
    7020: registry_file(7020, " : ∀ᵉ (m ≥ 2) (n ≥ 2), m ≤ m * n"),
    7017: registry_file(7017, " : ∃ n > 1, n = 2"),
    # erdos-812's shape: a file-local notation, which is neither a def nor a helper declaration.
    7018: registry_file(7018, " : ∃ c > 0, R 1 = c", before='local notation "R" => Nat.succ\n\n'),
    # erdos-1139's shape: a `letI` opening whose body is on the next line.
    7019: registry_file(7019, " :\n    letI u := (3 : ℕ)\n    u = 3"),
    # F14-T18 (Green's problem 58): `∀ᶠ` is a filter quantifier, not a binder the witness closes;
    # step 7 expects `True` of it.
    7021: registry_file(7021, " : ∀ᶠ n in Filter.atTop, n ≤ n + 1"),
    # F14-T18: a second AMS class beside number theory, and a class D-6 excludes.
    7022: registry_file(7022, " : ∃ n : ℕ, n = 7022"),
    7023: registry_file(7023, " : ∃ n : ℕ, n = 7023"),
    # Below the default minimum score; drafted only when named with --key (F14-T18).
    7007: registry_file(7007, " : ∃ n : ℕ, n = 7007"),
}
#: A non-Erdős registry file (F14-T18): its module doc carries the `# heading` that names the
#: problem, where the theorem's docstring opens with a sentence of context.
WIKI_FILE = (
    f"{HEADER}import FormalConjecturesUtil\n\n/-!\n# The Seven Conjecture\n\n*Reference:* "
    "[Wikipedia](https://en.wikipedia.org/wiki/Seven)\n\nThe question is\n"
    "open; [Kat16, Cor. 4.9] gives a sequence. Also open problems abound.\n-/\n\n"
    "namespace Seven\n\n/--\n"
    "Suppose $n$ is a number. Is it seven?\n-/\n@[category research open, AMS 11]\n"
    "theorem seven_conjecture : "
    "∃ n : ℕ, n = 7 := by\n  sorry\n\nend Seven\n"
)


#: The helper library's module that the statements above take names from, as the registry writes
#: it (F14-T19): a module with `public import`s of Mathlib modules and of a second library module,
#: an exposed public section, and a `public` declaration beside plain ones.
HELPER_AP = (
    f"{HEADER}module\n\npublic import Mathlib.Order.Basic\n"
    "public import FormalConjecturesForMathlib.Combinatorics.Base\n\n@[expose] public section\n\n"
    "namespace Set\npublic def IsAPOfLength (s : Set ℕ) (k : ℕ) : Prop := True\nend Set\n\n"
    # A definition named like a bound variable, under a namespace no statement opens:
    "namespace Degrees\ndef S (n : ℕ) : ℕ := n\nend Degrees\n\n"
    "namespace Ramsey\n@[expose, simp] def hyperRamsey (n : ℕ) : ℕ := n\nend Ramsey\n\n"
    "namespace Geometry\ndef area (x : ℝ) : ℝ := x\nend Geometry\n\n"
    # A theorem named like a Mathlib member (`card`): a theorem is not vocabulary.
    "namespace Set.IsAPOfLengthWith\ntheorem card : True := trivial\nend Set.IsAPOfLengthWith\n"
)
HELPER_BASE = (
    f"{HEADER}module\n\npublic import Mathlib.Order.Basic\n"
    "public import Batteries.Util.ProofWanted\n\n@[expose] public section\n\n"
    "/-- A base definition the AP module rests on. -/\ndef Combinatorics.base : ℕ := 0\n"
)


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
            row(7025),
            row(7026),
            row(7027, local_defs=["erdos_7027.answer"]),
            row(
                7009, decl="erdos_7009.parts.i"
            ),  # a dotted declaration name, as the file writes it
            row(7010),  # a term-mode `:= sorry` body, whose `StrictMono a →` is a hypothesis
            # The open statement is a variant of a problem resolved upstream: never drafted as it.
            row(7011, decl="erdos_7011.variants.generalisation"),
            row(7012),
            row(7013),
            row(7014),
            row(7015),
            row(7016),
            row(7017),
            row(7018),
            row(7019),
            row(7020),
            row(7021),
            row(7022, ams=["11", "33"]),
            row(7023, ams=["14"]),
            row(
                7024,
                key="fc:FormalConjectures/Wikipedia/Seven.lean#seven_conjecture",
                kind="fc",
                srcdir="Wikipedia",
                file="FormalConjectures/Wikipedia/Seven.lean",
                decl="seven_conjecture",
                docstring="Suppose $n$ is a number. Is it seven?",
                site_status=None,
            ),
            row(7007, score=4, letter="B"),  # below the minimum: not chosen at all
            row(7008, site_status="PROVED (LEAN)"),  # closed: not chosen
        ],
    }


def write_registry(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    """The miniature registry, its helper library and the catalog describing it."""
    fc = tmp_path / "fc"
    for n, text in {**FILES, **EXTRA}.items():
        path = fc / "FormalConjectures" / "ErdosProblems" / f"{n}.lean"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    wiki = fc / "FormalConjectures" / "Wikipedia" / "Seven.lean"
    wiki.parent.mkdir(parents=True)
    wiki.write_text(WIKI_FILE, encoding="utf-8")
    helpers = fc / "FormalConjecturesForMathlib" / "Combinatorics" / "AP.lean"
    helpers.parent.mkdir(parents=True)
    helpers.write_text(HELPER_AP, encoding="utf-8")
    (helpers.parent / "Base.lean").write_text(HELPER_BASE, encoding="utf-8")
    plane = fc / "FormalConjecturesForMathlib" / "Geometry" / "Plane.lean"
    plane.parent.mkdir(parents=True)
    plane.write_text(
        f"{HEADER}module\n\npublic import Mathlib.Order.Basic\n\n@[expose] public section\n\n"
        'namespace Plane\nscoped notation "ℝ²" => Fin 2\nend Plane\n',
        encoding="utf-8",
    )
    catalog = tmp_path / "catalog.json"
    doc = catalog_doc()
    catalog.write_text(json.dumps(doc), encoding="utf-8")
    return fc, catalog, doc


def run_wave(tmp_path: Path, *extra: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    fc, catalog, doc = write_registry(tmp_path)
    out = tmp_path / "wave1"
    tool = load_tool()
    argv = ["--catalog", str(catalog), "--fc", str(fc), "--out", str(out), *extra]
    assert tool.main(argv) == 0
    return out, {"out": out, "fc": fc}, doc


@pytest.fixture
def wave(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    return run_wave(tmp_path)


def test_the_clean_rows_are_drafted_and_the_rest_refused_by_name(
    wave: tuple[Path, dict[str, Any], dict[str, Any]], capsys: pytest.CaptureFixture[str]
) -> None:
    out, _result, _doc = wave
    report = (out / "REPORT.md").read_text(encoding="utf-8")
    assert "Drafted 14, refused 11." in report
    # F14-T18: `∀ᶠ` is not a binder; the witness is `True` and nothing is refused.
    assert (
        (out / "erdos-7021" / "Witness.lean")
        .read_text(encoding="utf-8")
        .endswith("theorem witness : True := trivial\n")
    )
    # F14-T18: an AMS class D-6 excludes is refused with D-6's own words, not "no graph domain".
    assert "`erdos:7023`: the drafted record is refused: algebraic-geometry is outside" in report
    hypotheses = "leading ∀ binders carry hypotheses (a bounded binder or an implication)"
    for key in (7010, 7015, 7016, 7020):
        assert f"`erdos:{key}`: {hypotheses}" in report, key
    assert "`erdos:7018`: uses file-local notation (port into defs/): R" in report
    assert "`erdos:7019`: the statement opens with a `let`/`have` binding spanning lines" in report
    assert (
        (out / "erdos-7017" / "Witness.lean")
        .read_text(encoding="utf-8")
        .endswith("theorem witness : True := trivial\n")
    )
    # Step 7 closes every leading binder, hypotheses or not: a data binder's witness is the closure
    # over `True`, inhabited by `default` (F14-T11L's sandbox admission found `True` refused).
    assert (
        (out / "erdos-7001" / "Witness.lean")
        .read_text(encoding="utf-8")
        .endswith("theorem witness : ∃ (n : ℕ), True := ⟨default, trivial⟩\n")
    )
    assert (
        (out / "erdos-7009" / "Witness.lean")
        .read_text(encoding="utf-8")
        .endswith("theorem witness : ∃ (S : Finset ℕ), True := ⟨default, trivial⟩\n")
    )
    # F14-T19: a helper-library name is ported mechanically, whether used bare, inside a type
    # ascription or written out with its namespace; the report names the port.
    for key in (7012, 7013, 7014):
        assert f"`erdos:{key}` → `erdos-{key}/` (port: CombinatoricsAP CombinatoricsBase)" in report
    assert (
        "`erdos:7011`: the open statement is a variant (erdos_7011.variants.generalisation)"
        in report
    )
    record = yaml.safe_load((out / "erdos-7009" / "record.yaml").read_text(encoding="utf-8"))
    assert record["title"].startswith("Erdős problem 7009, part i: ")
    assert sorted(p.name for p in out.iterdir() if p.is_dir()) == [
        "erdos-7001",
        "erdos-7002",
        "erdos-7003",
        "erdos-7006",
        "erdos-7009",
        "erdos-7012",
        "erdos-7013",
        "erdos-7014",
        "erdos-7017",
        "erdos-7021",
        "erdos-7022",
        "erdos-7025",
        "erdos-7026",
        "seven-conjecture",
        "upstream",
    ]
    # F14-T18: a non-Erdős target is titled by its file's heading, not the docstring's first
    # sentence (which opens with context: "Suppose $A, B ⊆ ...", "For a graph $G$, we define ...").
    record = yaml.safe_load((out / "seven-conjecture" / "record.yaml").read_text(encoding="utf-8"))
    assert record["title"] == "The Seven Conjecture"
    assert record["informal"] == "Suppose $n$ is a number. Is it seven?"
    seven = (out / "seven-conjecture" / "Statement.lean").read_text(encoding="utf-8")
    assert "/-! The Seven Conjecture — imported from" in seven
    # F14-T19: a prose line of the module doc that begins with "open" is not an `open` command
    # (found on the live probe: "open; [Kat16, Cor. 4.9] gives …" reached a statement).
    assert "open;" not in seven and "open problems" not in seven
    # The bound `S` and the dotted Mathlib member `card` in erdos_7009 are not helper uses.
    theorem = (out / "erdos-7009" / "Statement.lean").read_text(encoding="utf-8")
    assert "∀ S : Finset ℕ, S.card ≤ S.card + 1 := by" in theorem
    # F14-T19: the helper user and the file-local user are drafted with their ports.
    assert "`erdos:7002` → `erdos-7002/` (port: CombinatoricsAP CombinatoricsBase)" in report
    assert "`erdos:7003` → `erdos-7003/` (port: Local)" in report
    assert "`erdos:7004`: value-typed" in report
    assert "`erdos:7005`: binders before the colon carry a hypothesis" in report
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
        "--key erdos:7001" in script and "--key erdos:7006" in script and "erdos:7004" not in script
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


# --- F14-T18: wave two drafts every chosen row, with the curator's hand files where needed --------


def write_overrides(tmp_path: Path) -> Path:
    """The curator's hand files, one directory per target id: a `Witness.lean` where the driver
    cannot write the witness, and `defs/*.lean` ports where the statement uses a name the
    registry's helper library or the file itself defines."""
    overrides = tmp_path / "overrides"
    (overrides / "erdos-7005").mkdir(parents=True)
    (overrides / "erdos-7005" / "Witness.lean").write_text(
        "/-! By hand. -/\n\ntheorem witness : ∃ n : ℕ, 0 < n := ⟨1, Nat.one_pos⟩\n",
        encoding="utf-8",
    )
    (overrides / "erdos-7016").mkdir()
    (overrides / "erdos-7016" / "Witness.lean").write_text(
        "theorem witness : ∃ A : Set ℕ, A.Infinite := ⟨Set.univ, Set.infinite_univ⟩\n",
        encoding="utf-8",
    )
    (overrides / "erdos-7003" / "defs").mkdir(parents=True)
    (overrides / "erdos-7003" / "defs" / "Good.lean").write_text(
        f"{HEADER}import Mathlib\n\n/-! Ported from 7003.lean. -/\n\n"
        "def Good (n : ℕ) : Prop := n = n\n",
        encoding="utf-8",
    )
    (overrides / "erdos-7005" / "hazards.yaml").write_text(
        "- checker: off-by-one-range\n  location: 0 < n\n  justification: positive, as stated\n",
        encoding="utf-8",
    )
    (overrides / "erdos-7002" / "defs").mkdir(parents=True)
    (overrides / "erdos-7002" / "defs" / "AP.lean").write_text(
        f"{HEADER}import Mathlib\n\nnamespace Set\ndef IsAPOfLength (s : Set ℕ) (k : ℕ) : Prop := "
        "True\nend Set\n",
        encoding="utf-8",
    )
    return overrides


def test_hand_files_lift_the_witness_and_definition_refusals(tmp_path: Path) -> None:
    """With `--overrides`, a row the driver refused for its witness is drafted with the curator's
    `Witness.lean` verbatim, and a row refused for a helper or file-local name is drafted with the
    ported `defs/`, its statement importing them and `import.sh` passing them; the report says
    which drafts used hand files; a row with no hand file is refused as before."""
    overrides = write_overrides(tmp_path)
    out, _result, _doc = run_wave(tmp_path, "--overrides", str(overrides))
    report = (out / "REPORT.md").read_text(encoding="utf-8")
    assert "Drafted 16, refused 9." in report
    # Binders before the colon stay before the colon; the witness is the curator's.
    statement = (out / "erdos-7005" / "Statement.lean").read_text(encoding="utf-8")
    assert "theorem Opn.erdos_7005 (n : ℕ) (h : 0 < n) :\n    n ≤ n + 1 := by\n  sorry" in statement
    parsed = layout.parse_statement(statement)
    assert isinstance(parsed, layout.Statement) and parsed.decl_name == "Opn.erdos_7005"
    witness = (out / "erdos-7005" / "Witness.lean").read_text(encoding="utf-8")
    assert witness == (overrides / "erdos-7005" / "Witness.lean").read_text(encoding="utf-8")
    assert (
        (out / "erdos-7016" / "Witness.lean")
        .read_text(encoding="utf-8")
        .startswith("theorem witness : ∃ A : Set ℕ, A.Infinite")
    )
    # A ported definition: the statement imports it after Mathlib, the port is copied verbatim,
    # and the import passes --defs.
    statement = (out / "erdos-7003" / "Statement.lean").read_text(encoding="utf-8")
    assert "import Mathlib\nimport Defs.Good\n" in statement
    assert (out / "erdos-7003" / "defs" / "Good.lean").read_text(encoding="utf-8") == (
        overrides / "erdos-7003" / "defs" / "Good.lean"
    ).read_text(encoding="utf-8")
    assert "import Defs.AP\n" in (out / "erdos-7002" / "Statement.lean").read_text(encoding="utf-8")
    script = (out / "import.sh").read_text(encoding="utf-8")
    assert "--target erdos-7003 " in script and '--defs "$HERE/erdos-7003/defs"' in script
    # F14-T19: the hand ports for 7002 and 7003, and the driver's own for 7012, 7013, 7014.
    assert "--target erdos-7001 " in script and script.count("--defs") == 6
    assert "`erdos:7003` → `erdos-7003/` (hand: defs Good)" in report
    # The curator's port wins over the mechanical one: no `Local.lean` beside `Good.lean`.
    assert sorted(p.name for p in (out / "erdos-7003" / "defs").iterdir()) == ["Good.lean"]
    assert "`erdos:7005` → `erdos-7005/` (hand: Witness.lean; hazards.yaml)" in report
    # The curator's step-6 acknowledgements travel with the draft and reach the import (F02-R4).
    assert (out / "erdos-7005" / "hazards.yaml").read_text(encoding="utf-8") == (
        overrides / "erdos-7005" / "hazards.yaml"
    ).read_text(encoding="utf-8")
    assert (
        "--target erdos-7005 " in script and '--hazards "$HERE/erdos-7005/hazards.yaml"' in script
    )
    assert script.count("--hazards") == 1
    # Still refused: the value-typed row, and the row whose leading binders carry hypotheses and
    # whose curator wrote no witness.
    assert "`erdos:7004`: value-typed" in report
    assert "`erdos:7015`: leading ∀ binders carry hypotheses" in report


def test_a_hand_drafted_row_imports_with_its_defs_and_classifies_as_an_intake(
    tmp_path: Path,
) -> None:
    overrides = write_overrides(tmp_path)
    out, _result, doc = run_wave(tmp_path, "--overrides", str(overrides))
    root = copy_graph(tmp_path / "graph-parent", publish=True)
    target_id = "erdos-7003"
    directory = out / target_id
    rel = "FormalConjectures/ErdosProblems/7003.lean"
    imported = import_fc(
        root,
        target_id=target_id,
        source=out / "upstream" / rel,
        rel_path=rel,
        commit=PIN,
        base=yaml.safe_load((directory / "record.yaml").read_text(encoding="utf-8")),
        witness=(directory / "Witness.lean").read_text(encoding="utf-8"),
        statement=(directory / "Statement.lean").read_text(encoding="utf-8"),
        defs_dir=directory / "defs",
        acknowledged_hazards=yaml.safe_load(
            (out / "erdos-7005" / "hazards.yaml").read_text(encoding="utf-8")
        ),
        evidence_catalog=doc,
        evidence_key="erdos:7003",
        network_commit=NETWORK,
    )
    assert imported.evidence
    target = root / "targets" / target_id
    assert (target / "defs" / "Good.lean").is_file()
    meta = yaml.safe_load((target / "nodes" / target_id / "META.yaml").read_text(encoding="utf-8"))
    assert meta["acknowledged_hazards"][0]["checker"] == "off-by-one-range"
    changes = [
        Change("A", p.relative_to(root).as_posix())
        for p in sorted(target.rglob("*"))
        if p.is_file()
    ]
    c = modes.classify(changes, author="curator", curators=CURATORS)
    assert c.mode == "intake", c.as_dict()
    assert modes.check(root, c) == []


def test_a_named_key_is_drafted_whatever_its_score(tmp_path: Path) -> None:
    """The owner's ruling (2026-11-21): wave two loads every open statement regardless of grade,
    so a row named with `--key` is drafted below `--min-score`; a closed row is still not."""
    out, _result, _doc = run_wave(tmp_path, "--key", "erdos:7007", "--key", "erdos:7008")
    report = (out / "REPORT.md").read_text(encoding="utf-8")
    assert "Drafted 1, refused 0." in report
    assert "the rows named with --key: erdos:7007, erdos:7008" in report
    assert "scoring 5 or more" not in report
    assert (out / "erdos-7007").is_dir() and not (out / "erdos-7008").exists()
    record = yaml.safe_load((out / "erdos-7007" / "record.yaml").read_text(encoding="utf-8"))
    assert "Catalog score 4 (B)" in record["prior_art"]["summary"]


def test_the_record_carries_the_classification_its_ams_classes_give(
    wave: tuple[Path, dict[str, Any], dict[str, Any]],
) -> None:
    """F25-R4's block from the registry's AMS classes: every class as an MSC 2020 range, the
    arXiv categories they map to (at most two), and the graph's domain tag per class."""
    out, _result, _doc = wave
    record = yaml.safe_load((out / "erdos-7022" / "record.yaml").read_text(encoding="utf-8"))
    schemas.validate(record, intake.SCHEMA)
    assert record["classification"] == {
        "arxiv": ["math.NT", "math.CA"],
        "msc2020": ["11-xx", "33-xx"],
    }
    assert record["domains"] == ["number-theory", "special-functions"]
    assert intake.check_classification(record) == []
    one = yaml.safe_load((out / "erdos-7001" / "record.yaml").read_text(encoding="utf-8"))
    assert one["classification"] == {"arxiv": ["math.NT"], "msc2020": ["11-xx"]}


@pytest.mark.parametrize(
    ("prop", "closed"),
    [
        ("∀ᶠ n in Filter.atTop, n ≤ n + 1", None),
        ("∀ᶠ (N : ℕ) in Filter.atTop, ∀ᵉ (A ⊆ Finset.Icc 1 N), A.card ≤ N", None),
    ],
)
def test_eventually_is_not_a_binder(prop: str, closed: None) -> None:
    """`∀ᶠ x in l, P x` is `Filter.Eventually`, a proposition with no leading binder: step 7
    expects `True`, and the driver neither closes nor refuses it (Green's problem 58)."""
    tool = load_tool()
    assert tool.leading_binders(prop) is closed
    assert tool.shape_refusal(prop) is None
    assert tool.witness_for(prop) == tool.WITNESS


# --- the witness the driver writes follows step 7's closure rule ---------------------------------


@pytest.mark.parametrize(
    ("prop", "closed"),
    [
        ("Irrational (Real.sqrt 2)", None),
        ("∃ n : ℕ, n = 7006", None),
        ("∀ n : ℕ, n ≤ n + 1", ("(n : ℕ)", 1)),
        ("∀ n m : ℕ, n ≤ m", ("(n m : ℕ)", 2)),
        ("∀ (a b : ℕ) (S : Finset ℕ), a ≤ b", ("(a b : ℕ) (S : Finset ℕ)", 3)),
        ("∀ n : ℕ, ∀ S : Finset ℕ, n ∈ S ∨ n ∉ S", ("(n : ℕ) (S : Finset ℕ)", 2)),
    ],
)
def test_data_binders_close_into_the_witness(prop: str, closed: tuple[str, int] | None) -> None:
    """Step 7 expects ``∃ x…, True`` for leading data binders and ``True`` for none; the driver
    writes exactly that, inhabited by ``default``, and refuses nothing it can close."""
    tool = load_tool()
    assert tool.leading_binders(prop) == closed
    assert tool.shape_refusal(prop) is None
    witness = tool.witness_for(prop)
    if closed is None:
        assert witness == tool.WITNESS
    else:
        binders, names = closed
        terms = ", ".join(["default"] * names + ["trivial"])
        assert witness.endswith(f"theorem witness : ∃ {binders}, True := ⟨{terms}⟩\n")


@pytest.mark.parametrize(
    "prop",
    ["∀ {n : ℕ}, n = n", "∀ ⦃n : ℕ⦄, n = n", "∀ [Fintype α], True", "∀ n, n = n"],
)
def test_binders_the_driver_cannot_close_are_refused_by_name(prop: str) -> None:
    """An implicit, strict-implicit, instance or untyped leading binder is hand work: the
    driver names the refusal rather than drafting a witness the gate would refuse."""
    tool = load_tool()
    assert tool.leading_binders(prop) is None
    refusal = tool.shape_refusal(prop)
    assert refusal is not None and refusal.startswith("leading ∀ binders the driver cannot close")


def test_hypotheses_still_win_over_closure() -> None:
    """A bounded binder or an implication is the hypotheses rule's, as before (F14-T15)."""
    tool = load_tool()
    for prop in ("∀ n > 1, n = n", "∀ n : ℕ, 0 < n → n = n"):
        assert tool.leading_binders(prop) is None
        refusal = tool.shape_refusal(prop)
        assert refusal is not None and refusal.startswith("leading ∀ binders carry hypotheses")


# --- F14-T19: the driver ports definitions itself, and closes plain binders before the colon ------


REGISTRY_FILE_WITH_EVERYTHING = (
    f"{HEADER}module\n\npublic import FormalConjecturesUtil\n"
    "public meta import Mathlib.Data.List.Defs\n\n"
    "@[expose] public section\n\n"
    "/-!\n# A problem\n-/\n\nopen Filter\n\npublic meta section\n\ndef scratch : ℕ := 0\n\nend\n\n"
    "namespace Problem\n\n"
    "/-- A definition the statement uses. -/\n"
    "noncomputable def weight (n : ℕ) : ℝ :=\n  n\n\n"
    "public abbrev Good (n : ℕ) : Prop := 1 < n\n\n"
    "@[expose] instance : Inhabited (Fin 1) := ⟨0⟩\n\n"
    "/-- info: 0 -/\n#guard_msgs in\n#eval weight 0\n\n#check weight\n\n"
    '@[optimization_constant "6a"]\nnoncomputable def C6a : ℝ := 0\n\n'
    "@[AMS 11, simp] def d : ℕ := 1\n\n"
    "variable (k : ℕ)\n\n"
    "/-- A test, which goes. -/\n@[category test, AMS 11]\n"
    "theorem weight_zero : weight 0 = 0 := by\n  simp [weight]\n\n"
    "set_option linter.style.formal_proof_palomar false in\nopen Nat in\n"
    "@[category research open,\n  AMS 11]\n"
    "theorem problem : ∀ n, Good n → 0 < weight n := by\n"
    "  sorry\n\n"
    "/-- A lemma under a multi-line attribute. -/\n@[category high_school,\n  AMS 11]\n"
    "lemma helper : True := by\n  trivial\n\nend Problem\n\nend\n"
)


def test_a_port_keeps_the_definitions_and_drops_the_theorems_and_the_module_syntax() -> None:
    """`port_body` is the mechanical port of a registry file: every definition, instance,
    `variable` and scope line stays as written, every theorem and lemma goes with its docstring,
    its attributes and an `open ... in` prefix, and the module syntax (`module`, `public import`,
    the exposed public section and its closing `end`, `public` and `@[expose]`) is stripped so the
    text is an ordinary Lean file the gate elaborates under `import Mathlib`."""
    tool = load_tool()
    body, imports = tool.port_body(REGISTRY_FILE_WITH_EVERYTHING)
    assert imports == ["FormalConjecturesUtil", "Mathlib.Data.List.Defs"]
    # A linter option the registry defines goes, with its `in`; `meta` is module syntax.
    assert "set_option" not in body and "meta" not in body
    # A `#guard_msgs` test or a `#eval` is a command for the registry's own CI; its expected
    # text changes with the pretty-printer (found on the live probe) and it declares nothing.
    assert "#guard_msgs" not in body and "#eval" not in body and "#check" not in body
    assert "info: 0" not in body
    # An attribute the registry's own util library defines does not exist under Mathlib alone
    # (found on the live probe: `@[optimization_constant "6a"]`); the rest of the list stays.
    assert "optimization_constant" not in body and "AMS" not in body
    assert "noncomputable def C6a : ℝ := 0\n" in body and "@[simp] def d : ℕ := 1\n" in body
    # The exposed public section stays as a plain section, so its closing `end` still matches;
    # the meta section stays as a plain section with its own `end`.
    assert body.count("section\n") == 2 and body.count("\nend\n") == 2
    assert "def scratch : ℕ := 0\n" in body
    assert "theorem" not in body and "lemma" not in body and "sorry" not in body
    assert "@[category" not in body and "AMS 11" not in body and "open Nat in" not in body
    assert "A test, which goes." not in body and "A lemma under" not in body
    assert "noncomputable def weight (n : ℕ) : ℝ :=\n  n\n" in body
    assert "/-- A definition the statement uses. -/\n" in body
    assert "abbrev Good (n : ℕ) : Prop := 1 < n\n" in body and "public" not in body
    assert "instance : Inhabited (Fin 1) := ⟨0⟩\n" in body and "expose" not in body
    assert "variable (k : ℕ)\n" in body and "open Filter\n" in body
    assert "namespace Problem\n" in body and "end Problem\n" in body
    assert "module" not in body
    assert HEADER.split("\n")[1] not in body  # the header is the caller's to write


def test_an_exposed_noncomputable_section_keeps_its_noncomputable() -> None:
    """`@[expose] public noncomputable section` covers every definition under it; the port keeps
    the section and the modifier (found on the live probe as a surviving `public`)."""
    tool = load_tool()
    body, _imports = tool.port_body(
        "module\n\n@[expose] public noncomputable section\n\ndef f : ℝ := 0\n\nend\n"
    )
    assert body == "noncomputable section\n\ndef f : ℝ := 0\n\nend\n"


def test_an_attribute_list_loses_expose_and_keeps_the_rest() -> None:
    tool = load_tool()
    body, _imports = tool.port_body(
        "module\n\n@[expose] public section\n\n@[expose, simp] def f : ℕ := 0\n"
        "@[simp, expose]\ndef g : ℕ := 1\n"
    )
    assert "@[simp] def f : ℕ := 0\n" in body and "@[simp]\ndef g : ℕ := 1\n" in body


def test_a_file_local_definition_is_ported_mechanically(
    wave: tuple[Path, dict[str, Any], dict[str, Any]],
) -> None:
    """A row refused for a file-local name is drafted with `defs/Local.lean`, the registry file's
    definitions ported mechanically (its theorems and module syntax gone), the statement importing
    it after Mathlib and opening the namespace the theorem was stated in, and `import.sh` passing
    the port; the report says so."""
    out, _result, _doc = wave
    port = (out / "erdos-7003" / "defs" / "Local.lean").read_text(encoding="utf-8")
    header = intake.copyright_header(FILES[7003])
    assert header is not None and port.startswith(header)
    assert "\nimport Mathlib\n" in port and "FormalConjecturesUtil" not in port
    assert "Ported mechanically from `FormalConjectures/ErdosProblems/7003.lean`" in port
    assert "namespace Erdos7003\n" in port and "end Erdos7003\n" in port
    assert "def Good (n : ℕ) : Prop := n = n\n" in port
    assert "theorem" not in port and "sorry" not in port and "@[category" not in port
    assert "\nmodule\n" not in port and "public" not in port and "@[expose]" not in port
    statement = (out / "erdos-7003" / "Statement.lean").read_text(encoding="utf-8")
    assert "import Mathlib\nimport Defs.Local\n" in statement
    assert "open scoped Pointwise\nopen Erdos7003\n" in statement
    assert "∀ n : ℕ, Good n := by" in statement
    parsed = layout.parse_statement(statement)
    assert isinstance(parsed, layout.Statement) and parsed.decl_name == "Opn.erdos_7003"
    script = (out / "import.sh").read_text(encoding="utf-8")
    assert "--target erdos-7003 " in script and '--defs "$HERE/erdos-7003/defs"' in script


def test_a_helper_library_module_is_ported_with_what_it_imports(
    wave: tuple[Path, dict[str, Any], dict[str, Any]],
) -> None:
    """A row using a helper-library name is drafted with the library module that declares it
    ported verbatim under `defs/`, named by its path inside the library, its Mathlib imports
    collapsed into `import Mathlib` and its library imports ported too and imported as `Defs.*`."""
    out, _result, _doc = wave
    defs = out / "erdos-7002" / "defs"
    assert sorted(p.name for p in defs.iterdir()) == [
        "CombinatoricsAP.lean",
        "CombinatoricsBase.lean",
    ]
    ap = (defs / "CombinatoricsAP.lean").read_text(encoding="utf-8")
    assert ap.startswith(HEADER.rstrip("\n") + "\n")
    assert "\nimport Mathlib\nimport Defs.CombinatoricsBase\n" in ap
    assert "Mathlib.Order.Basic" not in ap and "public import" not in ap and "module\n" not in ap
    assert "Ported mechanically from `FormalConjecturesForMathlib/Combinatorics/AP.lean`" in ap
    assert "namespace Set\ndef IsAPOfLength (s : Set ℕ) (k : ℕ) : Prop := True\nend Set\n" in ap
    assert "@[simp] def hyperRamsey (n : ℕ) : ℕ := n\n" in ap
    assert "theorem card : True := trivial" in ap  # a library theorem stays: it is its module's
    base = (defs / "CombinatoricsBase.lean").read_text(encoding="utf-8")
    assert "def Combinatorics.base : ℕ := 0\n" in base and "import Defs." not in base
    # A library module the gate's toolchain carries (Batteries) is kept as written; Mathlib's
    # own modules collapse into `import Mathlib`.
    assert "\nimport Mathlib\nimport Batteries.Util.ProofWanted\n" in base
    statement = (out / "erdos-7002" / "Statement.lean").read_text(encoding="utf-8")
    assert (
        "import Mathlib\nimport Defs.CombinatoricsAP\nimport Defs.CombinatoricsBase\n" in statement
    )
    assert "S.IsAPOfLength 3 := by" in statement
    # A statement using both a file-local and a helper name imports both ports (7013 is a
    # helper-only row: no `Local.lean`).
    assert sorted(p.name for p in (out / "erdos-7013" / "defs").iterdir()) == [
        "CombinatoricsAP.lean",
        "CombinatoricsBase.lean",
    ]


def test_plain_binders_before_the_colon_close_into_the_witness(
    wave: tuple[Path, dict[str, Any], dict[str, Any]],
) -> None:
    """Binders before the colon are the same binders to step 7 as a leading ∀: data binders
    close over `True`, a hypothesis binder is still the curator's (F14-T18's refusal, narrowed)."""
    out, _result, _doc = wave
    statement = (out / "erdos-7025" / "Statement.lean").read_text(encoding="utf-8")
    assert "theorem Opn.erdos_7025 (n : ℕ) :\n    n ≤ n + 1 := by\n  sorry" in statement
    assert (
        (out / "erdos-7025" / "Witness.lean")
        .read_text(encoding="utf-8")
        .endswith("theorem witness : ∃ (n : ℕ), True := ⟨default, trivial⟩\n")
    )
    report = (out / "REPORT.md").read_text(encoding="utf-8")
    assert "`erdos:7005`: binders before the colon carry a hypothesis" in report
    assert not (out / "erdos-7005").exists()


def test_a_mechanically_ported_row_imports_with_its_defs_and_classifies_as_an_intake(
    wave: tuple[Path, dict[str, Any], dict[str, Any]], tmp_path: Path
) -> None:
    out, _result, doc = wave
    root = copy_graph(tmp_path / "graph-parent", publish=True)
    for n, ports in (
        (7003, ["Local.lean"]),
        (7002, ["CombinatoricsAP.lean", "CombinatoricsBase.lean"]),
    ):
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
            defs_dir=directory / "defs",
            evidence_catalog=doc,
            evidence_key=f"erdos:{n}",
            network_commit=NETWORK,
        )
        assert imported.evidence, target_id
        target = root / "targets" / target_id
        assert sorted(p.name for p in (target / "defs").iterdir()) == ports
        changes = [
            Change("A", p.relative_to(root).as_posix())
            for p in sorted(target.rglob("*"))
            if p.is_file()
        ]
        c = modes.classify(changes, author="curator", curators=CURATORS)
        assert c.mode == "intake", (target_id, c.as_dict())
        assert modes.check(root, c) == [], target_id


def test_a_subscript_in_the_declaration_name_becomes_a_plain_letter_in_the_id() -> None:
    """`moment_is_equiv₃` and `…ₖ` were refused by the id grammar on the live catalog (F14-T19)."""
    tool = load_tool()
    row = {"kind": "fc", "key": "fc:x", "decl": "Moments.moment_is_equiv₃"}
    assert tool.target_id_for(row) == "moment-is-equiv3"
    assert tool.target_id_for({**row, "decl": "moment_is_equivₖ"}) == "moment-is-equivk"


def test_a_library_notation_is_followed_to_its_module(
    wave: tuple[Path, dict[str, Any], dict[str, Any]],
) -> None:
    """`ℝ²` is a notation the helper library declares (Geometry/2d.lean, scoped), not a name the
    token scan sees; the port follows notation literals too (found on the live probe:
    "unexpected token '²'")."""
    out, _result, _doc = wave
    report = (out / "REPORT.md").read_text(encoding="utf-8")
    assert "`erdos:7026` → `erdos-7026/` (port: GeometryPlane)" in report
    port = (out / "erdos-7026" / "defs" / "GeometryPlane.lean").read_text(encoding="utf-8")
    assert 'namespace Plane\nscoped notation "ℝ²" => Fin 2\nend Plane\n' in port
    statement = (out / "erdos-7026" / "Statement.lean").read_text(encoding="utf-8")
    assert "import Mathlib\nimport Defs.GeometryPlane\n" in statement
    assert "open Plane\n" in statement


def test_a_definition_resting_on_sorry_refuses_the_row(
    wave: tuple[Path, dict[str, Any], dict[str, Any]],
) -> None:
    """A registry file may define `erdos_n.answer : T := sorry` and state the conjecture about
    it: an answer the registry leaves open is a question, not a conjecture (F11-Q24), and a `sorry`
    in `defs/` would fail admission anyway."""
    out, _result, _doc = wave
    report = (out / "REPORT.md").read_text(encoding="utf-8")
    assert (
        "`erdos:7027`: the file's definitions rest on `sorry` "
        "(an answer the registry leaves open): "
        "erdos_7027.answer" in report
    )
    assert not (out / "erdos-7027").exists()
