"""F34-T13 (R21; D-19 v3.51 (i)): a curator's operator record names an operator and the ledger
identities that are theirs.

``operators/<operator>/<timestamp>-<curator>.yaml``, appended by a listed curator. The newest
record for an operator is the one read, so a later record corrects an earlier one and a record with
no identities releases them (the owner's ruling, 2026-11-25: "newest record wins"); no ledger entry
is changed; an identity belongs to at most one operator, and is never its own operator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import TARGET, copy_graph

from opn_gate import ledger, modes, paths, schemas
from opn_gate.modes import Curators
from opn_gate.paths import Change

DATE = "2026-09-16T12:00:00Z"
OPERATOR = "thisisanameforsure"
RECORD = f"operators/{OPERATOR}/20261125T120000Z-founder.yaml"
CURATORS = Curators((("founder", "founder-login"), ("second", "second-login")))


def operator_record(**kw: object) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "operator/v1",
        "operator": OPERATOR,
        "identities": ["agent-a", "agent-b"],
        "reason": "the owner ran every agent of the September and October runs (F34-Q11)",
        "author": "founder",
        "date": "2026-11-25",
    }
    doc.update(kw)
    return doc


def on_ledger(root: Path, *identities: str) -> None:
    for identity in identities:
        entry = ledger.proof_entry(
            identity=identity,
            target=TARGET,
            node="and-reassoc",
            artifact_type="proof",
            artifact="Proof.lean",
            merge_commit="1" * 40,
            date=DATE,
        )
        assert entry is not None
        ledger.record(root, identity, entry)


def write(root: Path, rel: str, doc: dict[str, Any]) -> str:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return rel


def check_codes(root: Path, rel: str) -> list[str]:
    classification = modes.classify([Change("A", rel)], author="founder-login", curators=CURATORS)
    assert classification.mode == "curator", classification.problems
    return [d.code for d in modes.check(root, classification)]


# --- the record is a curator's -------------------------------------------------------------------


def test_an_operator_record_is_a_curator_record() -> None:
    located = paths.locate(RECORD)
    assert located is not None and located.role == "operator-record"
    assert located.target_id == paths.GRAPH_SCOPE
    classification = modes.classify(
        [Change("A", RECORD)], author="founder-login", curators=CURATORS
    )
    assert classification.mode == "curator", classification.problems


def test_an_operator_record_by_anyone_else_is_refused() -> None:
    classification = modes.classify([Change("A", RECORD)], author="agent-a", curators=CURATORS)
    assert [d.code for d in classification.problems] == ["curator-unlisted"]


@pytest.mark.parametrize(
    "rel",
    [
        "operators/thisisanameforsure.yaml",  # no directory for the operator
        "operators/thisisanameforsure/sub/x.yaml",  # nested
        "operators/not a name/20261125T120000Z-founder.yaml",
    ],
)
def test_a_path_that_is_not_an_operator_record_is_nobodys(rel: str) -> None:
    assert paths.locate(rel) is None


def test_the_schema_is_published() -> None:
    assert schemas.violations(operator_record(), "operator/v1") == []
    assert schemas.violations(operator_record(identities=[]), "operator/v1") == []


# --- the checks ---------------------------------------------------------------------------------


def test_a_record_of_identities_on_the_ledger_passes(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    on_ledger(root, "agent-a", "agent-b")
    assert check_codes(root, write(root, RECORD, operator_record())) == []


def test_the_directory_names_the_operator(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    on_ledger(root, "agent-a", "agent-b")
    rel = write(root, "operators/someone-else/20261125T120000Z-founder.yaml", operator_record())
    assert check_codes(root, rel) == ["operator-record-dir-mismatch"]


def test_an_identity_not_on_the_ledger_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    on_ledger(root, "agent-a")
    assert check_codes(root, write(root, RECORD, operator_record())) == [
        "operator-identity-unknown"
    ]


def test_an_operator_is_not_its_own_identity(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    on_ledger(root, "agent-a", OPERATOR)
    rel = write(root, RECORD, operator_record(identities=["agent-a", OPERATOR]))
    assert check_codes(root, rel) == ["operator-identity-is-operator"]


def test_an_identity_held_by_another_operator_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    on_ledger(root, "agent-a", "agent-b")
    write(
        root,
        "operators/carol/20261120T120000Z-founder.yaml",
        operator_record(operator="carol", identities=["agent-b"]),
    )
    assert check_codes(root, write(root, RECORD, operator_record())) == ["operator-identity-held"]


def test_a_malformed_record_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    on_ledger(root, "agent-a", "agent-b")
    doc = {k: v for k, v in operator_record().items() if k != "reason"}
    assert check_codes(root, write(root, RECORD, doc)) == ["record-invalid"]


# --- reading them: the newest record per operator wins ----------------------------------------


def test_the_newest_record_for_an_operator_is_the_one_read(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    on_ledger(root, "agent-a", "agent-b", "agent-c")
    write(root, f"operators/{OPERATOR}/20261101T120000Z-founder.yaml", operator_record())
    write(
        root,
        f"operators/{OPERATOR}/20261125T120000Z-founder.yaml",
        operator_record(identities=["agent-a", "agent-c"]),
    )
    assert ledger.operators(root) == {"agent-a": OPERATOR, "agent-c": OPERATOR}


def test_a_record_with_no_identities_releases_them(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    on_ledger(root, "agent-a", "agent-b")
    write(root, f"operators/{OPERATOR}/20261101T120000Z-founder.yaml", operator_record())
    write(
        root,
        f"operators/{OPERATOR}/20261125T120000Z-founder.yaml",
        operator_record(identities=[]),
    )
    assert ledger.operators(root) == {}


def test_a_released_identity_may_be_named_again(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    on_ledger(root, "agent-a", "agent-b")
    write(
        root,
        "operators/carol/20261101T120000Z-founder.yaml",
        operator_record(operator="carol", identities=["agent-b"]),
    )
    write(
        root,
        "operators/carol/20261110T120000Z-founder.yaml",
        operator_record(operator="carol", identities=[]),
    )
    assert check_codes(root, write(root, RECORD, operator_record())) == []


def test_a_graph_without_operator_records_reads_none(tmp_path: Path) -> None:
    assert ledger.operators(copy_graph(tmp_path)) == {}
