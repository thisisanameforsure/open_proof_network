"""F00-T3: schemas v1, validation, pinned hashes (R9, R10; AC15, AC16)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import samples

from opn_gate import schemas
from opn_gate.schemas import SchemaError


def test_known_schemas_are_the_published_set() -> None:
    assert schemas.known_schemas() == (
        "annex/v1",
        "approach-record/v1",
        "attestation/v1",
        "attestation/v2",
        "attestation/v3",
        "attestation/v4",
        "claims/v1",
        "defect-claim/v1",
        "fidelity/v1",
        "frontier/v1",
        "frontier/v2",
        "gate-spec/v1",
        "graph/v1",
        "graph/v2",
        "info/v1",
        "ledger/v1",
        "meta/v1",
        "meta/v2",
        "meta/v3",
        "meta/v4",
        "node-status/v1",
        "postmortem/v1",
        "precheck-record/v1",
        "revision-request/v1",
        "submission-meta/v1",
        "target-status/v1",
        "target-status/v2",
        "target/v1",
        "targets-index/v1",
        "targets-index/v2",
        "targets-index/v3",
        "waiver/v1",
    )


# --- F03-T1: record and product schemas -------------------------------------------------------


def test_record_samples_validate() -> None:
    schemas.validate(samples.postmortem())
    schemas.validate(samples.node_status())
    schemas.validate(samples.target_status())
    schemas.validate(
        {"schema": "frontier/v1", "rendered_from": None, "entries": [samples.frontier_entry()]}
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"outcome": "gave-up"},
        {"route_class": "vibes"},
        {"failure_class": "unlucky"},
        {"node": "Bad Id"},
        {"route": ""},
        {"artifacts": {"transcript": "x"}},
        {"artifacts": {"annex": "short"}},
        {"extra": 1},
    ],
)
def test_postmortem_rejects(bad: dict[str, object]) -> None:
    """D-13 verbatim: outcome mandatory, enums closed, no transcript field."""
    assert schemas.violations(samples.postmortem(**bad))


def test_postmortem_outcome_is_mandatory() -> None:
    doc = samples.postmortem()
    del doc["outcome"]
    assert schemas.violations(doc)
    minimal = {k: doc[k] for k in ("schema", "node", "contributor", "route", "route_class")}
    minimal["outcome"] = "blocked"
    assert schemas.violations(minimal) == []


@pytest.mark.parametrize(
    "bad",
    [
        {"status": "ready"},  # derived statuses are never recorded (F03-R1)
        {"status": "proved"},
        {"cause": ""},
        {"date": "2026-9-9"},
        {"extra": 1},
    ],
)
def test_node_status_rejects(bad: dict[str, object]) -> None:
    assert schemas.violations(samples.node_status(**bad))


@pytest.mark.parametrize(
    "bad",
    [
        {"status": "open"},
        {"fidelity": "gold"},
        {"claimable": "yes"},
        {"root": "Not An Id"},
        {"extra": 1},
    ],
)
def test_target_status_rejects(bad: dict[str, object]) -> None:
    assert schemas.violations(samples.target_status(**bad))


def test_frontier_entry_exact_fields() -> None:
    """F03-AC10: exactly the R5 fields — nothing added, nothing missing."""
    entry = samples.frontier_entry()
    assert set(entry) == {
        "node_id",
        "target_id",
        "statement_hash",
        "relation",
        "origin",
        "tags",
        "attempts",
        "refuted_route_classes",
        "failure_class_histogram",
        "ready_since",
        "claims",
        "annex_present",
        "bounty",
        "claimable",
        "tutorial",
    }

    def frontier(e: dict[str, object]) -> dict[str, object]:
        return {"schema": "frontier/v1", "rendered_from": None, "entries": [e]}

    assert schemas.violations(frontier(entry)) == []
    assert schemas.violations(frontier(samples.frontier_entry(difficulty=3)))  # no score (D-25)
    for key in entry:
        without = dict(entry)
        del without[key]
        assert schemas.violations(frontier(without)), key
    assert schemas.violations(frontier(samples.frontier_entry(tags={"deps": []})))
    assert schemas.violations(
        frontier(samples.frontier_entry(failure_class_histogram={"unlucky": 1}))
    )
    assert schemas.violations(frontier(samples.frontier_entry(refuted_route_classes=["vibes"])))
    assert (
        schemas.violations(
            frontier(
                samples.frontier_entry(
                    failure_class_histogram={"timeout-blowup": 1, "invalid": 1},
                    refuted_route_classes=["case-split", "induction"],
                    ready_since=None,
                )
            )
        )
        == []
    )


def test_graph_index_info_samples() -> None:
    node: dict[str, object] = {
        "node_id": "and-reassoc",
        "status": "proved",
        "deps": [],
        "origin": "authored",
        "statement_hash": "a" * 64,
        "relation": None,
        "tutorial": False,
        "trust_base": "kernel",
        "proof_commit": "1" * 40,
    }
    graph = {
        "schema": "graph/v1",
        "target_id": "propositional",
        "root": "and-swap-reassoc",
        "rendered_from": None,
        "nodes": [node],
    }
    assert schemas.violations(graph) == []
    assert schemas.violations(dict(graph, nodes=[dict(node, status="unknown")]))
    assert schemas.violations(dict(graph, nodes=[dict(node, score=1)]))
    counts = dict.fromkeys(
        (
            "ready",
            "blocked",
            "proved",
            "speculative",
            "superseded",
            "stale",
            "disputed",
            "abandoned",
        ),
        0,
    )
    target: dict[str, object] = {
        "target_id": "propositional",
        "root": "and-swap-reassoc",
        "root_statement_hash": "a" * 64,
        "fidelity": "mechanical-only",
        "status": "active",
        "mathlib_sha": None,
        "node_counts": counts,
        "claimable": True,
    }
    index: dict[str, object] = {
        "schema": "targets-index/v1",
        "rendered_from": "2" * 40,
        "targets": [target],
    }
    assert schemas.violations(index) == []
    partial = dict(index, targets=[dict(target, node_counts={"ready": 1})])
    assert schemas.violations(partial)
    info = {
        "schema": "info/v1",
        "protocol_version": "3.11",
        "schemas": {"attestation": [1, 2, 3], "meta": [1, 2]},
        "targets": {"propositional": {"gate_spec_hash": "c" * 64, "network_commit": "3" * 40}},
        "rate_limit_policy": None,
        "rendered_from": None,
    }
    assert schemas.violations(info) == []
    assert schemas.violations(dict(info, protocol_version="v3"))


def test_waiver_schema() -> None:
    """F02-R8: waiver/v1 needs kind, justification and author; nothing else."""
    schemas.validate(samples.waiver())
    undated = samples.waiver()
    del undated["date"]
    schemas.validate(undated)  # date is optional
    for bad in (
        {"justification": ""},
        {"author": ""},
        {"kind": "sorry"},
        {"extra": 1},
        {"date": "yesterday"},
    ):
        assert schemas.violations(samples.waiver(**bad)), bad


def test_attestation_v3_trust_base() -> None:
    """F02-R9: trust_base is kernel or compiler, optional; older records stay readable."""
    schemas.validate(samples.attestation(trust_base="compiler"))
    doc = samples.attestation()
    del doc["trust_base"]
    schemas.validate(doc)
    assert schemas.violations(samples.attestation(trust_base="hardware"))
    older = samples.attestation(schema="attestation/v2")
    for gone in ("trust_base", "submitter", "model_and_tooling"):
        older.pop(gone, None)
    schemas.validate(older)  # a v2 record still validates as v2
    assert schemas.violations(samples.attestation(schema="attestation/v2"))  # v2 has no v3/v4 keys


def test_meta_v1_still_valid() -> None:
    """F02-AC5, R6: meta/v1 validates unchanged; meta/v2 accepts acknowledgments."""
    schemas.validate(samples.meta())
    ack = {"checker": "nat-sub", "location": "n - 1", "justification": "intended"}
    schemas.validate(samples.meta(schema="meta/v2"))
    schemas.validate(samples.meta(schema="meta/v2", acknowledged_hazards=[ack]))
    assert schemas.violations(samples.meta(acknowledged_hazards=[ack]))  # v1 has no such key


@pytest.mark.parametrize(
    "acks",
    [
        [{"checker": "nat-sub", "location": "n - 1", "justification": ""}],
        [{"checker": "nat-sub", "location": "", "justification": "x"}],
        [{"checker": "Nat Sub", "location": "n - 1", "justification": "x"}],
        [{"checker": "nat-sub", "location": "n - 1", "justification": "x", "extra": 1}],
        [{"checker": "nat-sub", "location": "n - 1"}],
        [
            {"checker": "nat-sub", "location": "n - 1", "justification": "x"},
            {"checker": "nat-sub", "location": "n - 1", "justification": "x"},
        ],
    ],
)
def test_meta_v2_rejects_bad_acknowledgments(acks: list[dict[str, object]]) -> None:
    assert schemas.violations(samples.meta(schema="meta/v2", acknowledged_hazards=acks))


def test_meta_v3_reaches_the_skeleton_hole_origin() -> None:
    """D-3 v3.12: the fourth origin D-25 always published becomes settable. Only v3 takes it,
    and v3 still carries everything v2 did, so the older versions stay readable and narrower."""
    schemas.validate(samples.meta(schema="meta/v3", origin="skeleton-hole"))
    assert schemas.violations(samples.meta(schema="meta/v2", origin="skeleton-hole"))
    assert schemas.violations(samples.meta(origin="skeleton-hole"))  # v1

    for origin in ("authored", "compiler-derived", "variant"):
        schemas.validate(samples.meta(schema="meta/v3", origin=origin))
    assert schemas.violations(samples.meta(schema="meta/v3", origin="invented"))

    ack = {"checker": "nat-sub", "location": "n - 1", "justification": "intended"}
    schemas.validate(samples.meta(schema="meta/v3", acknowledged_hazards=[ack]))


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

    (copy / "meta" / "v99.json").write_text("{}")
    assert any(
        "meta/v99.json is not pinned" in p for p in schemas.verify_pins(copy, copy / "HASHES")
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
        {"review": {"kind": "pr-approval", "reviewer": "r"}},
        {"review": {"kind": "manager", "reviewer": None, "reference": None}},
        {"reviewer": "v1-field-on-v2"},
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


@pytest.mark.parametrize(
    "schema_id",
    ["meta/v0", "Meta/v1", "meta", "meta/1", "meta/v1/x", "meta/v01", "/v1", "meta/v1 "],
)
def test_malformed_schema_ids_are_refused_before_any_file_is_touched(schema_id: str) -> None:
    """R9: the id grammar is `<name>/v<n>`; anything else never reaches the filesystem."""
    with pytest.raises(SchemaError, match="malformed schema id"):
        schemas.schema_path(schema_id)
    assert [v.path for v in schemas.violations({"schema": schema_id})] == ["$.schema"]


def test_non_string_schema_field_is_one_violation() -> None:
    for doc in ({"schema": 1}, {"schema": None}, {"schema": ["meta/v1"]}):
        found = schemas.violations(doc)
        assert [v.path for v in found] == ["$.schema"], doc
        assert "missing or non-string" in found[0].message


def test_load_yaml_refuses_non_objects_and_broken_yaml(tmp_path: Path) -> None:
    listy = tmp_path / "list.yaml"
    listy.write_text("- a\n- b\n")
    with pytest.raises(SchemaError, match="must be an object"):
        schemas.load_yaml(listy)
    broken = tmp_path / "broken.yaml"
    broken.write_text("schema: meta/v1\nid: [unclosed\n")
    with pytest.raises(SchemaError, match="cannot read YAML"):
        schemas.load_yaml(broken)
    empty = tmp_path / "empty.yaml"
    empty.write_text("")
    with pytest.raises(SchemaError, match="must be an object"):
        schemas.load_yaml(empty)
    with pytest.raises(SchemaError, match="cannot read YAML"):
        schemas.load_yaml(tmp_path / "missing.yaml")
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{not json")
    with pytest.raises(SchemaError, match="cannot read JSON"):
        schemas.load_json(bad_json)


def test_pins_catch_a_removed_schema_and_skip_comments(tmp_path: Path) -> None:
    """R10, D-34: a published schema that disappears from disk is a pin failure too; the HASHES
    file may carry comments and blank lines."""
    copy = tmp_path / "schemas"
    shutil.copytree(schemas.SCHEMAS_DIR, copy)
    (copy / "meta" / "v1.json").unlink()
    problems = schemas.verify_pins(copy, copy / "HASHES")
    assert problems == ["pinned schema meta/v1.json is missing on disk"]

    pins = copy / "HASHES"
    pins.write_text("# comment\n\n" + pins.read_text())
    assert schemas.read_pins(pins) == schemas.read_pins(schemas.HASHES_FILE)
    assert schemas.verify_pins(copy, pins) == problems


@pytest.mark.parametrize(
    "bad",
    [
        {"lean_toolchain": "v4.33.1"},
        {"lean_toolchain": "leanprover/lean4"},
        {"network_commit": "0" * 39},
        {"network_commit": "G" * 40},
        {"hazard_checkers": ["NatSub"]},
        {"hazard_checkers": ["nat-sub", "nat-sub"]},
        {"olean_cache_url": "http://insecure.example"},
        {"precheck_max_age_s": 0},
        {"step3_caps": {"cpu": 1, "memory_mib": 0, "wallclock_s": 1}},
        {"step3_caps": {"cpu": 1, "memory_mib": 1, "wallclock_s": 1.5}},
        {"step3_caps": {"cpu": 1, "memory_mib": 1}},
        {"gate_owner": ""},
        {"axiom_allowlist": [""]},
        {"schema": "gate-spec/v2"},
    ],
)
def test_gate_spec_field_boundaries(bad: dict[str, object]) -> None:
    """F00-Q2, C6: every pinned value has a shape; a zero cap or a plain-http cache is refused."""
    assert schemas.violations(samples.gate_spec(**bad)), bad


def test_gate_spec_required_keys() -> None:
    for key in samples.gate_spec():
        doc = samples.gate_spec()
        del doc[key]
        assert schemas.violations(doc), key


@pytest.mark.parametrize(
    "bad",
    [
        {"id": "Tutorial"},
        {"id": "-leading-dash"},
        {"status": "Ready"},
        {"deps": "tutorial-and-swap"},
        {"deps": ["Bad Id"]},
        {"provenance": {"author": ""}},
        {"provenance": {"author": "a", "date": "8 Sep 2026"}},
        {"provenance": {"author": "a", "model": ""}},
        {"tutorial": 1},
        {"schema": "meta/v0"},
    ],
)
def test_meta_field_boundaries(bad: dict[str, object]) -> None:
    assert schemas.violations(samples.meta(**bad)), bad


def test_waiver_justification_is_capped() -> None:
    """F02-R8, D-28: contributor free text is short by schema."""
    assert schemas.violations(samples.waiver(justification="x" * 2001))
    assert schemas.violations(samples.waiver(justification="x" * 2000)) == []
    for key in ("kind", "justification", "author"):
        doc = samples.waiver()
        del doc[key]
        assert schemas.violations(doc), key


def test_canonical_json_is_stable() -> None:
    a = schemas.canonical_json({"b": 1, "a": [1, 2]})
    b = schemas.canonical_json({"a": [1, 2], "b": 1})
    assert a == b
    assert a.endswith(b"\n")
    assert schemas.content_hash(a) == schemas.content_hash(b)
