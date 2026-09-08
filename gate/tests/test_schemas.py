"""F00-T3: schemas v1, validation, pinned hashes (R9, R10; AC15, AC16)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import samples

from opn_gate import schemas
from opn_gate.schemas import SchemaError


def test_known_schemas_are_the_three_v1() -> None:
    assert schemas.known_schemas() == ("attestation/v1", "gate-spec/v1", "meta/v1")


def test_samples_validate() -> None:
    schemas.validate(samples.gate_spec())
    schemas.validate(samples.meta())
    schemas.validate(samples.attestation())


def test_schema_hashes_pinned(tmp_path: Path) -> None:
    """AC15: every schema matches its pin; a modified copy fails."""
    assert schemas.verify_pins() == []

    copy = tmp_path / "schemas"
    shutil.copytree(schemas.SCHEMAS_DIR, copy)
    edited = copy / "meta" / "v1.json"
    doc = json.loads(edited.read_text())
    doc["description"] = "edited"
    edited.write_text(json.dumps(doc))
    problems = schemas.verify_pins(copy, copy / "HASHES")
    assert len(problems) == 1
    assert "meta/v1.json was edited" in problems[0]

    (copy / "meta" / "v2.json").write_text("{}")
    assert any(
        "meta/v2.json is not pinned" in p for p in schemas.verify_pins(copy, copy / "HASHES")
    )


def test_unknown_schema_refused() -> None:
    """AC16."""
    with pytest.raises(SchemaError, match="unknown schema"):
        schemas.validate(samples.meta(schema="meta/v9"))
    with pytest.raises(SchemaError, match="malformed schema id"):
        schemas.load_schema("../etc/passwd")
    with pytest.raises(SchemaError, match="missing or non-string"):
        schemas.validate({"id": "x"})
    with pytest.raises(SchemaError, match="must be an object"):
        schemas.validate(["not", "an", "object"])


@pytest.mark.parametrize(
    "bad",
    [
        {"graph_id": "Has Caps"},
        {"mathlib_sha": "short"},
        {"axiom_allowlist": ["propext", "propext"]},
        {"step3_caps": {"cpu": 0, "memory_mib": 1, "wallclock_s": 1}},
        {"accepted_precheck_signatures": []},
        {"accepted_precheck_signatures": ["ssh"]},
        {"extra_key": 1},
    ],
)
def test_gate_spec_rejects(bad: dict[str, object]) -> None:
    assert schemas.violations(samples.gate_spec(**bad))


@pytest.mark.parametrize(
    "bad",
    [
        {"origin": "invented"},
        {"statement-hash": "abc"},
        {"tutorial": "yes"},
        {"provenance": {}},
        {"deps": ["a", "a"]},
    ],
)
def test_meta_rejects(bad: dict[str, object]) -> None:
    assert schemas.violations(samples.meta(**bad))


@pytest.mark.parametrize(
    "bad",
    [
        {"verdict": "maybe"},
        {"runner": "cloud"},
        {"first_failing_step": 10},
        {"signature": {"kind": "gate", "key_id": None, "value": None}},
        {"signature": {"kind": "gate", "key_id": None, "value": None, "timestamp": "yesterday"}},
        {"steps": [{"step": 1, "name": "toolchain", "result": "ok", "diagnostic": None}]},
        {"diagnostic": {"message": "no code"}},
        {"precheck_attestation": {"hash": None}},
    ],
)
def test_attestation_rejects(bad: dict[str, object]) -> None:
    assert schemas.violations(samples.attestation(**bad))


def test_violation_paths_are_named() -> None:
    found = schemas.violations(samples.attestation(steps=[{"step": 1}]))
    assert any(v.path.startswith("$['steps'][0]") for v in found)


def test_load_yaml_and_json(tmp_path: Path) -> None:
    y = tmp_path / "META.yaml"
    y.write_text(
        "schema: meta/v1\nid: n1\nstatus: ready\ndeps: []\n"
        f"statement-hash: {'e' * 64}\norigin: authored\n"
        "provenance:\n  author: someone\ntutorial: false\n"
    )
    assert schemas.load_yaml(y)["id"] == "n1"
    j = tmp_path / "gate-spec.json"
    j.write_bytes(schemas.canonical_json(samples.gate_spec()))
    assert schemas.load_json(j, "gate-spec/v1")["graph_id"] == "propositional"
    with pytest.raises(SchemaError, match="cannot read"):
        schemas.load_json(tmp_path / "missing.json")
    with pytest.raises(SchemaError, match="does not satisfy"):
        schemas.load_yaml(y, "gate-spec/v1")


def test_canonical_json_is_stable() -> None:
    a = schemas.canonical_json({"b": 1, "a": [1, 2]})
    b = schemas.canonical_json({"a": [1, 2], "b": 1})
    assert a == b
    assert a.endswith(b"\n")
    assert schemas.content_hash(a) == schemas.content_hash(b)
