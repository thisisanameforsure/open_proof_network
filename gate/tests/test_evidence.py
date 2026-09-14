"""F14-T4: the statement-evidence record (R3, R4; AC3).

A curated target's root carries what the catalog knows about its statement, pinned to the
statement's hash, and the external attempts the catalog names go to the F12-R10 ledger. The gate
refuses a record that does not speak for the root as it stands, and every refusal writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from harness import copy_graph
from test_intake import import_fc, index_row

from opn_gate import cli, evidence, intake, modes, qa, schemas
from opn_gate.paths import Change

TARGET = "fc-42"
UPSTREAM = "FormalConjectures/ErdosProblems/42.lean"
NETWORK = "1" * 40
CURATORS = modes.Curators((("curator", "curator"),))


def catalog_doc() -> dict[str, Any]:
    """A two-row catalog in the build's shape: one scored row for the fixture's upstream file,
    one row the build did not score."""
    return {
        "schema": evidence.CATALOG_SCHEMA,
        "fc_commit": "b" * 40,
        "nexus_published": "2026-05-13",
        "rows": [
            {
                "key": "erdos:42",
                "kind": "erdos",
                "file": UPSTREAM,
                "decl": "erdos_42",
                "score": 6,
                "letter": "A",
                "reasons": [
                    "+2 attempted by AlphaProof Nexus (Feb 2026), not solved",
                    "+2 Bloom selected it for FrontierMath Erdős",
                    "+1 no misformalization issue ever filed",
                    "+1 Lean statement public for 180+ days",
                ],
                "history": {"first": "2025-04-26", "last": "2026-07-16", "n": 13},
                "issues": [],
                "local_defs": [],
                "hazards": [],
                "site_status": "OPEN",
                "mathlib_definition": None,
                "nexus_attempted": ["erdos_42", "erdos_42.variants.weak"],
            },
            {
                "key": "erdos:43",
                "kind": "erdos",
                "file": "FormalConjectures/ErdosProblems/43.lean",
                "decl": None,
                "score": None,
                "letter": "n/a",
                "reasons": ["site status is PROVED (LEAN), not a seed candidate"],
                "history": None,
                "issues": [],
                "local_defs": [],
                "hazards": [],
                "site_status": "PROVED (LEAN)",
                "mathlib_definition": None,
                "nexus_attempted": [],
            },
        ],
    }


@pytest.fixture
def graph(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path, publish=True)
    import_fc(root)
    return root


def target_of(graph: Path) -> Path:
    return graph / "targets" / TARGET


def add(graph: Path, key: str = "erdos:42", **kw: Any) -> tuple[Path, ...]:
    return evidence.add(
        target_of(graph),
        kw.pop("catalog", catalog_doc()),
        key,
        network_commit=NETWORK,
        recorded_by="curator",
        date="2026-09-14T10:00:00Z",
        upstream_path=kw.pop("upstream_path", UPSTREAM),
        **kw,
    )


# --- AC3: the record from a catalog row --------------------------------------------------------


def test_record_from_catalog_row(graph: Path) -> None:
    target = target_of(graph)
    written = add(graph)
    assert [p.name for p in written] == ["attempts.yaml", "root-1.yaml"]

    record = schemas.load_yaml(target / "evidence" / "root-1.yaml", evidence.SCHEMA)
    root_hash = qa.subject_hash(target, "root")
    assert record["statement_hash"] == root_hash
    assert record["catalog"]["key"] == "erdos:42" and record["catalog"]["score"] == 6
    assert record["catalog"]["letter"] == "A" and record["catalog"]["network_commit"] == NETWORK
    assert record["registry_history"] == {
        "first": "2025-04-26",
        "last": "2026-07-16",
        "commits": 13,
    }
    assert record["external_attempts_recorded"] == 2

    ledger = qa.attempts_state(target, root_hash)
    assert ledger.m == 2
    assert {e.url.rsplit("#", 1)[1] for e in ledger.counted} == {
        "erdos_42",
        "erdos_42.variants.weak",
    }
    assert all(e.date == "2026-05-13" and e.system == "AlphaProof Nexus" for e in ledger.counted)

    current = evidence.current(target)
    assert current is not None and current.score == 6
    assert current.reference() == f"evidence:evidence/root-1.yaml@{root_hash}:6"

    row = index_row(graph, TARGET)
    assert row["statement_evidence"] == {
        "file": "evidence/root-1.yaml",
        "key": "erdos:42",
        "score": 6,
        "letter": "A",
        "catalog_commit": NETWORK,
        "statement_hash": root_hash,
        "current": True,
        "misformalization_open": 0,
    }
    assert row["attempts"] == {"counted": 2, "recorded": 2}


def test_a_second_record_does_not_repeat_the_attempts(graph: Path) -> None:
    """R4: the attempts are on the ledger once; a later record is the next file."""
    add(graph)
    written = add(graph)
    assert [p.name for p in written] == ["root-2.yaml"]
    assert qa.attempts_state(target_of(graph)).m == 2
    assert [r.name for r in evidence.load(target_of(graph))] == ["root-1.yaml", "root-2.yaml"]


def test_refusals_write_nothing(graph: Path) -> None:
    """R4, C7: an unknown key, an unscored row, a row for another file and a malformed network
    commit are each refused before the ledger or the evidence directory exists."""
    target = target_of(graph)
    with pytest.raises(evidence.EvidenceError, match="holds no row"):
        add(graph, "erdos:9999")
    with pytest.raises(evidence.EvidenceError, match="not scored"):
        add(graph, "erdos:43")
    with pytest.raises(evidence.EvidenceError, match="was imported from"):
        add(graph, upstream_path="FormalConjectures/ErdosProblems/41.lean")
    with pytest.raises(schemas.SchemaError):
        evidence.add(
            target,
            catalog_doc(),
            "erdos:42",
            network_commit="not-a-commit",
            recorded_by="curator",
            date="2026-09-14",
        )
    assert not (target / "evidence").exists()
    assert not qa.attempts_path(target).exists()


def test_a_record_for_another_statement_counts_for_nothing(graph: Path) -> None:
    """R3: pinned to another hash, a record is not current, and the index says so."""
    target = target_of(graph)
    row = evidence.catalog_row(catalog_doc(), "erdos:42")
    stale = evidence.doc_from_row(
        catalog_doc(),
        row,
        statement_hash="0" * 64,
        network_commit=NETWORK,
        recorded_by="curator",
        date="2026-09-14",
        attempts_recorded=0,
    )
    evidence.write(target, stale)
    assert evidence.current(target) is None
    summary = index_row(graph, TARGET)["statement_evidence"]
    assert summary is not None and summary["current"] is False


def test_an_invalid_record_on_disk_raises(graph: Path) -> None:
    """C7: a broken record is not silently no record — it decides whether a person reviews."""
    target = target_of(graph)
    (target / "evidence").mkdir()
    (target / "evidence" / "root-1.yaml").write_text("schema: statement-evidence/v1\n")
    with pytest.raises(schemas.SchemaError):
        evidence.load(target)


# --- R4: the import carries its evidence ---------------------------------------------------------


def test_import_with_evidence(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    result = import_fc(
        root, evidence_catalog=catalog_doc(), evidence_key="erdos:42", network_commit=NETWORK
    )
    assert result.evidence == (
        f"targets/{TARGET}/attempts.yaml",
        f"targets/{TARGET}/evidence/root-1.yaml",
    )
    assert result.as_dict()["evidence"] == list(result.evidence)
    assert evidence.current(target_of(root)) is not None


def test_an_import_with_the_wrong_row_writes_nothing(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    wrong = catalog_doc()
    wrong["rows"][0]["file"] = "FormalConjectures/ErdosProblems/41.lean"
    with pytest.raises(intake.IntakeError, match="catalog row for"):
        import_fc(root, evidence_catalog=wrong, evidence_key="erdos:42", network_commit=NETWORK)
    with pytest.raises(intake.IntakeError, match="both the catalog and the row key"):
        import_fc(root, evidence_catalog=catalog_doc(), network_commit=NETWORK)
    with pytest.raises(intake.IntakeError, match="network commit"):
        import_fc(root, evidence_catalog=catalog_doc(), evidence_key="erdos:42")
    assert not target_of(root).exists()


# --- the gate: an evidence pull request, and an intake that carries one ----------------------


def test_an_evidence_pull_request_is_a_curator_act(graph: Path) -> None:
    add(graph)
    changes = [
        Change("A", f"targets/{TARGET}/evidence/root-1.yaml"),
        Change("A", f"targets/{TARGET}/attempts.yaml"),
    ]
    c = modes.classify(changes, author="curator", curators=CURATORS)
    assert c.mode == "curator", c.as_dict()
    assert modes.check(graph, c) == []


def test_a_stale_evidence_record_is_refused_at_the_gate(graph: Path) -> None:
    target = target_of(graph)
    row = evidence.catalog_row(catalog_doc(), "erdos:42")
    evidence.write(
        target,
        evidence.doc_from_row(
            catalog_doc(),
            row,
            statement_hash="0" * 64,
            network_commit=NETWORK,
            recorded_by="curator",
            date="2026-09-14",
            attempts_recorded=0,
        ),
    )
    c = modes.classify(
        [Change("A", f"targets/{TARGET}/evidence/root-1.yaml")], author="curator", curators=CURATORS
    )
    assert [d.code for d in modes.check(graph, c)] == ["evidence-stale"]


def test_an_evidence_record_by_a_non_curator_is_refused(graph: Path) -> None:
    add(graph)
    c = modes.classify(
        [Change("A", f"targets/{TARGET}/evidence/root-1.yaml")],
        author="stranger",
        curators=CURATORS,
    )
    assert c.mode is None and c.problems, c.as_dict()


def test_an_intake_may_carry_its_evidence(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    import_fc(root, evidence_catalog=catalog_doc(), evidence_key="erdos:42", network_commit=NETWORK)
    target = target_of(root)
    changes = [
        Change("A", p.relative_to(root).as_posix())
        for p in sorted(target.rglob("*"))
        if p.is_file()
    ]
    c = modes.classify(changes, author="curator", curators=CURATORS)
    assert c.mode == "intake", c.as_dict()
    roles = {loc.role for loc in c.located}
    assert {"statement-evidence", "attempts-ledger"} <= roles


# --- the command ---------------------------------------------------------------------------------


def test_evidence_add_command(
    graph: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog_doc()), encoding="utf-8")
    common = [
        "--graph",
        str(graph),
        "--catalog",
        str(path),
        "--network-commit",
        NETWORK,
        "--author",
        "curator",
    ]
    code = cli.main(
        ["evidence", "add", TARGET, "--key", "erdos:42", *common, "--date", "2026-09-14T10:00:00Z"]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_PASS and out["ok"] is True, out
    assert out["written"] == [
        f"targets/{TARGET}/attempts.yaml",
        f"targets/{TARGET}/evidence/root-1.yaml",
    ]

    code = cli.main(["evidence", "add", TARGET, "--key", "erdos:9999", *common])
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_FAIL and out["ok"] is False and "holds no row" in json.dumps(out), out

    code = cli.main(["evidence", "add", "propositional", "--key", "erdos:42", *common])
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_FAIL and "curated target" in json.dumps(out), out
