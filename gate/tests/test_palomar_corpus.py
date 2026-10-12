"""F25-T6 / AC11 (F25-R13's fast half): seven entries Palomar has registered, read with the
network's readers and written back with its writers.

Ground truth the registry accepted: a document here that fails to read, or that does not survive
the writer, is a defect in the network's Palomar code, not in the entry. Each fixture directory
under ``gate/tests/fixtures/palomar/<id>/`` holds the entry's Challenge, comparator config,
metadata, lakefile, toolchain and licence at the commit the registry recorded (``NOTICE`` says
how), and ``gate/palomar/corpus.json`` pins what the registry said of each.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from opn_gate import intake, palomar

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "palomar"
CORPUS = {c["id"]: c for c in palomar.corpus()}
IDS = sorted(CORPUS)


def fixture(entry_id: str, name: str) -> Path:
    return FIXTURES / entry_id / name


def test_the_corpus_is_the_fixture_set() -> None:
    assert sorted(p.name for p in FIXTURES.iterdir() if p.is_dir()) == IDS
    assert len(IDS) == 7
    assert (FIXTURES / "NOTICE").is_file()


@pytest.mark.parametrize("entry_id", IDS)
def test_the_entry_record_reads(entry_id: str) -> None:
    doc = palomar.read_entry(
        json.loads(fixture(entry_id, "entry.json").read_text(encoding="utf-8"))
    )
    pin = CORPUS[entry_id]
    assert doc["id"] == entry_id and doc["version"] == pin["version"]
    assert doc["source"]["repository"] == pin["repository"]
    assert doc["source"]["commit"] == pin["commit"]
    assert doc["status"] == "registered"
    assert set(doc["formalization"]["permitted_axioms"]) <= set(palomar.pins()["permitted_axioms"])


@pytest.mark.parametrize("entry_id", IDS)
def test_the_challenge_hash_and_size_are_the_registrys(entry_id: str) -> None:
    """The registry recorded the Challenge's sha256 and its line and byte counts; the fixture is
    that file, and the network's measure agrees with the registry's."""
    raw = fixture(entry_id, "Challenge.lean").read_bytes()
    pin = CORPUS[entry_id]
    assert hashlib.sha256(raw).hexdigest() == pin["challenge_sha256"]
    m = palomar.measure(raw)
    assert (m.lines, m.bytes) == (pin["challenge_lines"], pin["challenge_bytes"]), entry_id
    assert palomar.challenge_problems(raw) == []


#: A registered entry today's v0.4 schema refuses: its authors are {name, orcid} objects where
#: the schema now wants strings. The registry accepted it on 2026-09-05, so its schema moved
#: under a registered entry; the network's reader stays strict to the schema as vendored.
KNOWN_SCHEMA_DRIFT: dict[str, str] = {"PALOMAR-2026-09-05-000007": "authors"}


@pytest.mark.parametrize("entry_id", IDS)
def test_the_metadata_reads_and_round_trips(entry_id: str) -> None:
    text = fixture(entry_id, "formalization.yaml").read_text(encoding="utf-8")
    if entry_id in KNOWN_SCHEMA_DRIFT:
        with pytest.raises(palomar.PalomarDocumentError, match=KNOWN_SCHEMA_DRIFT[entry_id]):
            palomar.read_formalization(text)
        return
    doc = palomar.read_formalization(text)
    assert doc.version == palomar.FORMALIZATION_VERSION
    assert doc.authors, "every registered entry names at least one author"
    assert doc.review_status
    assert all(m.get("method") in palomar.METHODS for m in doc.automation_methods)
    again = palomar.read_formalization(palomar.write_formalization(doc))
    assert again.sections == doc.sections  # modulo key order, which yaml.safe_load drops
    assert yaml.safe_load(palomar.write_formalization(doc)) == yaml.safe_load(text)


@pytest.mark.parametrize("entry_id", IDS)
def test_the_comparator_config_reads_and_names_the_registered_theorems(entry_id: str) -> None:
    doc = palomar.read_comparator(fixture(entry_id, "comparator.json").read_text(encoding="utf-8"))
    pin = CORPUS[entry_id]
    assert list(doc.theorem_names) == pin["theorem_names"]
    assert list(doc.definition_names) == pin["definition_names"]
    assert set(doc.permitted_axioms) <= set(palomar.pins()["permitted_axioms"])
    assert json.loads(palomar.write_comparator(doc)) == {
        **json.loads(palomar.write_comparator(doc))
    }
    again = palomar.read_comparator(palomar.write_comparator(doc))
    assert again == doc


@pytest.mark.parametrize("entry_id", IDS)
def test_every_vendored_licence_is_on_the_allowlist(entry_id: str) -> None:
    pin = CORPUS[entry_id]
    assert pin["licence"] in intake.LICENCE_ALLOWLIST
    text = fixture(entry_id, "LICENSE").read_text(encoding="utf-8", errors="replace")
    expected = {"Apache-2.0": "Apache License", "MIT": "MIT License"}[pin["licence"]]
    assert expected in text


@pytest.mark.parametrize("entry_id", IDS)
def test_the_toolchain_pin_and_lakefile_agree(entry_id: str) -> None:
    pin = CORPUS[entry_id]
    toolchain = fixture(entry_id, "lean-toolchain").read_text(encoding="utf-8").strip()
    assert toolchain == pin["lean_toolchain"]
    lakefile = fixture(entry_id, "lakefile.toml").read_text(encoding="utf-8")
    assert "mathlib" in lakefile


def test_the_corpus_spans_the_shapes_the_export_must_handle() -> None:
    """What makes seven the right seven: at least one of each shape the export writes or the
    verifier meets."""
    rows: list[dict[str, Any]] = list(CORPUS.values())
    assert any(r["project_path"] for r in rows), "a nested project (source.project_path)"
    assert any(not r["kernels"] for r in rows), "an entry verified before the two kernels"
    assert any(r["definition_names"] for r in rows), "definition names in the comparator config"
    assert any(r["licence"] == "MIT" for r in rows), "a licence other than Apache-2.0"
    assert any(r["lean_toolchain"] < "leanprover/lean4:v4.35" for r in rows), "an older toolchain"
    assert any(len(r["theorem_names"]) > 10 for r in rows), "many theorems"
    assert all(r["mathlib_revision"] for r in rows), (
        "every entry pins Mathlib in project_dependencies"
    )
    challenge_modules = {
        palomar.read_comparator(fixture(r["id"], "comparator.json").read_text()).challenge_module
        for r in rows
    }
    assert challenge_modules > {"Challenge"}, "a non-default challenge module name"


def first_command(text: str) -> str:
    """The first Lean command after block and line comments."""
    stripped = re.sub(r"/-.*?-/", "", text, flags=re.S)
    return next(
        (
            ln.strip()
            for ln in stripped.splitlines()
            if ln.strip() and not ln.strip().startswith("--")
        ),
        "",
    )


def test_registered_challenges_use_the_module_system_since_october() -> None:
    """What the corpus says about the rule: every entry registered from 2026-10-02 begins with
    ``module``; two September entries do not. The export's transform (T7) writes ``module``, the
    shape today's submissions take; ``corpus.json`` records each entry's answer."""
    for entry_id in IDS:
        pin = CORPUS[entry_id]
        uses = (
            first_command(fixture(entry_id, "Challenge.lean").read_text(encoding="utf-8"))
            == "module"
        )
        assert uses == pin["module_system"], entry_id
        if pin["registered_at"] >= "2026-10-02":
            assert uses, entry_id
    assert sum(1 for i in IDS if CORPUS[i]["module_system"]) == 5


def test_the_pins_name_what_the_registry_publishes() -> None:
    pins = palomar.pins()
    assert palomar.toolchain_minimum() == pins["toolchains"]["minimum"] == "v4.35.0-rc2"
    assert (
        hashlib.sha256(palomar.FORMALIZATION_SCHEMA_FILE.read_bytes()).hexdigest()
        == pins["formalization_schema"]["sha256"]
    )
    assert (
        hashlib.sha256(palomar.TOOLCHAINS_FILE.read_bytes()).hexdigest()
        == pins["toolchains"]["sha256"]
    )
    assert "Apache License" in palomar.licence_text() and "Version 2.0" in palomar.licence_text()
    assert pins["challenge_caps"] == {
        "lines": 1000,
        "bytes": 102400,
        "preferred_lines": 300,
        "preferred_bytes": 32768,
    }


def test_the_writer_refuses_what_the_schema_refuses() -> None:
    bad = palomar.Formalization({"version": "v0.4", "project": {"name": "x"}})
    with pytest.raises(palomar.PalomarDocumentError, match="authors"):
        palomar.write_formalization(bad)
    with pytest.raises(palomar.PalomarDocumentError):
        palomar.read_formalization("- not\n- a mapping\n")
    with pytest.raises(palomar.PalomarDocumentError, match="theorem_names"):
        palomar.read_comparator(
            '{"challenge_module": "C", "solution_module": "S", "permitted_axioms": []}'
        )


def test_caps_count_physical_lines() -> None:
    assert palomar.measure(b"a\nb\n") == palomar.Measure(2, 4)
    assert palomar.measure(b"a\nb") == palomar.Measure(2, 3)
    assert palomar.measure(b"") == palomar.Measure(0, 0)
    assert palomar.challenge_problems(b"x\n" * 1001) == [
        "Challenge.lean has 1001 lines; the cap is 1000"
    ]
    assert palomar.challenge_problems(b"x" * 102401 + b"\n")[0].startswith(
        "Challenge.lean is 102402 bytes"
    )
    assert palomar.file_problems(b"x\n" * 10001, "Big.lean") == [
        "Big.lean has 10001 lines; the cap is 10000"
    ]
