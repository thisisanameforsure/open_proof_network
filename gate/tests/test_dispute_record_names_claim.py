"""F08-T38 (D-18 v3.28): the gate refuses a ``disputed`` record that names no standing claim.

D-18 v3.28: a dispute is accepted for adjudication when a listed curator records ``disputed`` on
the node, naming the defect claim it accepts. F08-T35 made the curator's ``status`` command write
such a record only with a ``reference`` naming a valid, standing defect claim on that node
(``curator.accepted_claim``). But curator mode admitted any schema-valid ``node-status/v1``
record, so a hand-written ``disputed`` with no ``reference`` — or one naming a missing,
withdrawn or foreign claim — passed the gate, took the node off the frontier, and could never lift
when a claim was withdrawn (``graph.disputed_is_void`` needs the reference, F08-T32). The mode
now holds the record to the command's own rule, through the same function. ``abandoned`` (D-14)
takes no claim and is unaffected.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import TARGET, copy_graph

from opn_gate import codes, curator, modes
from opn_gate.modes import Curators
from opn_gate.paths import Change

NODE = "and-reassoc"
OTHER = "tutorial-and-swap"
NODES = f"targets/{TARGET}/nodes"
CLAIM_NAME = "20261003T120000Z-alice.yaml"
STATUS = f"{NODES}/{NODE}/status/20261004T120000Z-founder.yaml"
CURATORS = Curators((("founder", "founder-login"), ("second", "second-login")))
CODE = "dispute-claim-unnamed"


def write_yaml(root: Path, rel: str, doc: dict[str, Any]) -> str:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return rel


def file_claim(root: Path, node_id: str = NODE) -> str:
    doc = samples.defect_claim(stmt_ref=node_id, **{"class": "wrong-domain"})
    write_yaml(root, f"{NODES}/{node_id}/defects/{CLAIM_NAME}", doc)
    return f"defects/{CLAIM_NAME}"


def withdraw_claim(root: Path) -> None:
    write_yaml(
        root,
        f"{NODES}/{NODE}/withdrawals/20261004T110000Z-founder.yaml",
        {
            "schema": "withdrawal/v1",
            "withdraws": f"defects/{CLAIM_NAME}",
            "reason": "filed against the wrong reading",
            "author": "founder",
            "date": "2026-10-04",
        },
    )


def status_doc(status: str = "disputed", **extra: str) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "node-status/v1",
        "status": status,
        "cause": "a ground (i) dispute accepted for adjudication",
        "author": "founder",
        "date": "2026-10-04",
    }
    doc.update(extra)
    return doc


def gate_codes(root: Path, rel: str = STATUS) -> list[str]:
    """Classify a pull request adding ``rel`` by a listed curator, then run the checks."""
    classification = modes.classify([Change("A", rel)], author="founder-login", curators=CURATORS)
    assert classification.mode == "curator", classification.problems
    return [d.code for d in modes.check(root, classification)]


def test_a_disputed_record_naming_no_claim_is_refused(tmp_path: Path) -> None:
    """The red case: a hand-written ``disputed`` with no ``reference`` passed the gate."""
    root = copy_graph(tmp_path)
    file_claim(root)
    write_yaml(root, STATUS, status_doc())
    assert gate_codes(root) == [CODE]


@pytest.mark.parametrize(
    "reference",
    [
        f"defects/{CLAIM_NAME}",
        f"{NODES}/{NODE}/defects/{CLAIM_NAME}",  # the graph-root form the derivation also reads
    ],
)
def test_a_disputed_record_naming_a_standing_claim_on_its_node_passes(
    tmp_path: Path, reference: str
) -> None:
    root = copy_graph(tmp_path)
    file_claim(root)
    write_yaml(root, STATUS, status_doc(reference=reference))
    assert gate_codes(root) == []


@pytest.mark.parametrize(
    "reference",
    [
        "defects/20260101T000000Z-nobody.yaml",  # not on the record
        "dispute-42",  # a free dispute id, not a claim
        f"targets/other-target/nodes/{NODE}/defects/{CLAIM_NAME}",  # another target
        f"{NODES}/{OTHER}/defects/{CLAIM_NAME}",  # another node's claim
    ],
)
def test_a_disputed_record_naming_no_claim_of_its_node_is_refused(
    tmp_path: Path, reference: str
) -> None:
    root = copy_graph(tmp_path)
    file_claim(root)
    file_claim(root, OTHER)
    write_yaml(root, STATUS, status_doc(reference=reference))
    assert gate_codes(root) == [CODE]


def test_a_disputed_record_naming_a_withdrawn_claim_is_refused(tmp_path: Path) -> None:
    """It would be void as it merged (F08-T32)."""
    root = copy_graph(tmp_path)
    file_claim(root)
    withdraw_claim(root)
    write_yaml(root, STATUS, status_doc(reference=f"defects/{CLAIM_NAME}"))
    assert gate_codes(root) == [CODE]


def test_an_abandoned_record_is_unaffected(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    write_yaml(root, STATUS, status_doc("abandoned"))
    assert gate_codes(root) == []


def test_the_curator_commands_own_record_passes_the_gate(tmp_path: Path) -> None:
    """The writer and the gate hold one rule: what ``curator status ... disputed`` writes, the
    curator mode admits."""
    root = copy_graph(tmp_path)
    file_claim(root)
    written = curator.declare_status(
        root,
        TARGET,
        NODE,
        "disputed",
        "ground (i) accepted",
        author="founder",
        date="2026-10-04T12:00:00Z",
        now=datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC),
        reference=f"defects/{CLAIM_NAME}",
    )
    assert gate_codes(root, written.relative_to(root).as_posix()) == []


def test_the_code_has_its_catalog_row() -> None:
    row = codes.CATALOG[CODE]
    assert row.source == "gate" and "D-18" in row.meaning
