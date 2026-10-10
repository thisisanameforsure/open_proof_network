"""F25-T1 / AC1 (F25-R1, R3 to R7; D-3, D-10, D-23 v3.37): the eight schemas accept the examples
their own descriptions cite and refuse their counter-examples.

Each schema is held to its own text: an enum value, a pattern or an example a description names
must validate (the F19 lesson, where a schema's id pattern refused its own description's example).
"""

from __future__ import annotations

import copy
from typing import Any

import jsonschema
import pytest
import samples

from opn_gate import schemas


def refused(doc: Any, schema: str) -> list[str]:
    return [v.path for v in schemas.violations(doc, schema)]


# --- submission-meta/v2 and the automation block (R1) ---------------------------------------


def test_v1_block_still_validates_and_v2_adds_automation() -> None:
    assert schemas.violations(samples.submission_meta(), "submission-meta/v1") == []
    assert schemas.violations(samples.submission_meta_v2(), "submission-meta/v2") == []
    without = samples.submission_meta(schema="submission-meta/v2")
    assert schemas.violations(without, "submission-meta/v2") == []  # optional in the schema


@pytest.mark.parametrize("method", ["manual", "copilot", "agent", "autonomous", "other"])
def test_every_method_the_description_names_validates(method: str) -> None:
    doc = samples.submission_meta_v2(automation=samples.automation(method=method))
    assert schemas.violations(doc, "submission-meta/v2") == []


def test_automation_examples_from_the_descriptions() -> None:
    full = samples.automation(
        tool_setup="Claude Code with the network's MCP server",
        wall_time="about 40 minutes",
        tokens={"input": 1_200_000, "output": 85_000},
        hardware="one laptop; hosted models",
        spend="subscription",
    )
    doc = samples.submission_meta_v2(automation=full)
    assert schemas.violations(doc, "submission-meta/v2") == []


@pytest.mark.parametrize(
    "bad",
    [
        {"method": "robot"},
        {"models": []},
        {"models": ["x" * 201]},
        {"framework": ""},
        {"tokens": {"input": -1, "output": 0}},
        {"tokens": {"input": 1}},
        {"tokens": {"input": 1.5, "output": 2}},
        {"spend_usd": "12"},  # Palomar's field name is not ours
    ],
)
def test_automation_counter_examples(bad: dict[str, Any]) -> None:
    doc = samples.submission_meta_v2(automation={**samples.automation(), **bad})
    assert refused(doc, "submission-meta/v2")


@pytest.mark.parametrize("missing", ["method", "models", "framework"])
def test_the_required_trio(missing: str) -> None:
    block = samples.automation()
    del block[missing]
    assert refused(samples.submission_meta_v2(automation=block), "submission-meta/v2")


# --- attestation/v7 and ledger/v2 (R3) -------------------------------------------------------


def test_attestation_v7_carries_automation_or_null() -> None:
    assert schemas.violations(samples.attestation(), "attestation/v7") == []
    declared = samples.attestation(automation=samples.automation())
    assert schemas.violations(declared, "attestation/v7") == []
    doc = samples.attestation()
    del doc["automation"]
    assert refused(doc, "attestation/v7")
    assert refused(samples.attestation(automation={"method": "agent"}), "attestation/v7")


def ledger_doc(**entry: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "line": "proof",
        "target": "euclid-primes",
        "node": "infinitude-of-primes",
        "artifact": "Proof.lean",
        "merge_commit": "a" * 40,
        "date": "2026-10-12T10:00:00Z",
        "tooling": "claude-fable-5-1 Claude Code",
        "status": "active",
        "automation": None,
    }
    row.update(entry)
    return {"schema": "ledger/v2", "identity": "someone", "entries": [row]}


def test_ledger_v2_entries_carry_automation_or_null() -> None:
    assert schemas.violations(ledger_doc(), "ledger/v2") == []
    assert schemas.violations(ledger_doc(automation=samples.automation()), "ledger/v2") == []
    doc = ledger_doc()
    del doc["entries"][0]["automation"]
    assert refused(doc, "ledger/v2")


# --- target/v3 (R4) --------------------------------------------------------------------------


def test_target_v3_classification_examples() -> None:
    base = samples.target_record(schema="target/v3")
    assert schemas.violations(base, "target/v3") == []  # optional
    for arxiv, msc in [
        (["math.CO"], ["05C35"]),
        (["math.NT", "math.CO"], ["11B13", "05D10", "11-xx"]),
        (["cs.LO"], ["03B35"]),
    ]:
        cls = {"arxiv": arxiv, "msc2020": msc}
        doc = samples.target_record(schema="target/v3", classification=cls)
        assert schemas.violations(doc, "target/v3") == [], (arxiv, msc)


@pytest.mark.parametrize(
    "bad",
    [
        {"arxiv": [], "msc2020": ["05C35"]},
        {"arxiv": ["math.CO", "math.NT", "math.PR"], "msc2020": ["05C35"]},
        {"arxiv": ["math"], "msc2020": ["05C35"]},
        {"arxiv": ["math.CO"], "msc2020": []},
        {"arxiv": ["math.CO"], "msc2020": ["5C35"]},
        {"arxiv": ["math.CO"], "msc2020": ["05C35"] * 2},
        {"arxiv": ["math.CO"]},
    ],
)
def test_target_v3_classification_counter_examples(bad: dict[str, Any]) -> None:
    assert refused(samples.target_record(schema="target/v3", classification=bad), "target/v3")


# --- registration/v1 (R5) --------------------------------------------------------------------


def test_registration_examples() -> None:
    assert schemas.violations(samples.registration(), "registration/v1") == []
    pending = samples.registration(
        registry_id=None, version=None, status="submitted", url=None,
        challenge_sha256=None, solution_sha256=None, note="awaiting review",
    )  # fmt: skip
    assert schemas.violations(pending, "registration/v1") == []
    for status in ("submitted", "registered", "revision_required", "rejected", "withdrawn"):
        assert schemas.violations(samples.registration(status=status), "registration/v1") == []


@pytest.mark.parametrize(
    "bad",
    [
        {"registry": "arxiv"},
        {"registry_id": "PALOMAR-2026-10-12-3"},
        {"version": 0},
        {"wrapper": {"repository": "no-owner", "commit": "a" * 40}},
        {"wrapper": {"repository": "o/r", "commit": "abc"}},
        {"graph_commit": "A" * 40},
        {"proof": {"node": "infinitude-of-primes", "attestation": "38"}},
        {"status": "pending"},
        {"submitted_by": "-leading-hyphen"},
        {"date": "2026-10-12T00:00:00Z"},
        {"url": "http://palomar-registry.org/x"},
        {"challenge_sha256": "c" * 63},
        {"note": ""},
        {"extra": 1},
    ],
)
def test_registration_counter_examples(bad: dict[str, Any]) -> None:
    assert refused(samples.registration(**bad), "registration/v1")


# --- display-name/v1 (R6) --------------------------------------------------------------------


def test_display_name_examples() -> None:
    assert schemas.violations(samples.display_name(), "display-name/v1") == []
    assert schemas.violations(samples.display_name(name=None, link=None), "display-name/v1") == []
    assert schemas.violations(samples.display_name(via="ssh"), "display-name/v1") == []


@pytest.mark.parametrize(
    "bad",
    [
        {"pseudonym": "has space"},
        {"name": ""},
        {"name": "x" * 201},
        {"link": "http://example.org"},
        {"via": "none"},
        {"key": "not a key"},
        {"signature": None},
        {"extra": 1},
    ],
)
def test_display_name_counter_examples(bad: dict[str, Any]) -> None:
    assert refused(samples.display_name(**bad), "display-name/v1")


# --- targets-index/v10 and graph/v7 (R7) -----------------------------------------------------


def _row_template() -> dict[str, Any]:
    schema = schemas.load_schema("targets-index/v10")
    return schema["properties"]["targets"]["items"]  # type: ignore[no-any-return]


def test_the_products_require_registrations() -> None:
    assert "registrations" in _row_template()["required"]
    graph = schemas.load_schema("graph/v7")
    assert "registrations" in graph["required"]
    summary = {
        "registry": "palomar",
        "registry_id": None,
        "version": None,
        "status": "submitted",
        "url": None,
    }
    for schema in ("targets-index/v10", "graph/v7"):
        node = schemas.load_schema(schema)
        prop = (
            node["properties"]["targets"]["items"]["properties"]["registrations"]
            if schema.startswith("targets-index")
            else node["properties"]["registrations"]
        )
        validator = jsonschema.Draft202012Validator(prop)
        assert list(validator.iter_errors([summary])) == []
        assert list(validator.iter_errors([{**summary, "status": "withdrawn"}]))  # never published
        assert list(validator.iter_errors([{**summary, "extra": 1}]))


def test_every_new_schema_is_pinned_and_hashes_hold() -> None:
    assert schemas.verify_pins() == []
    for name in (
        "submission-meta/v2", "attestation/v7", "ledger/v2", "target/v3",
        "registration/v1", "display-name/v1", "targets-index/v10", "graph/v7",
    ):  # fmt: skip
        assert name in schemas.known_schemas()
        doc = copy.deepcopy(schemas.load_schema(name))
        assert doc["title"] == name and doc["$id"].endswith(f"/{name}.json")
