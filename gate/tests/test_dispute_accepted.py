"""F08-T35 (D-18 v3.28): a curator accepts a dispute by a ``disputed`` record naming the claim.

D-18 says a node is flagged ``disputed`` "when a dispute on grounds (i) or (ii) is accepted for
adjudication", and v3.28 says how: "a listed curator records disputed on the node, naming the
defect claim it accepts. The node then leaves the frontier and new claims on it are refused,
until the record or the claim is withdrawn (v3.27) or the dispute ends in a revision (D-8)."

Before this task the curator's ``status`` command wrote ``abandoned`` alone (``NODE_STATUSES``),
so the only way to accept a dispute was a hand-written record, which nothing required to name a
claim; and a record that names none can never lift when its claim is withdrawn
(``graph.disputed_is_void``, F08-T32). The command now writes ``disputed`` only with a
``reference`` naming a defect claim on that node that is on the record and not withdrawn.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import TARGET, copy_graph

from opn_gate import cli, curator, graph, products, schemas

NODE = "and-reassoc"
OTHER = "tutorial-and-swap"
ROOT = "and-swap-reassoc"
AUTHOR = "founder"
DATE = "2026-10-04T12:00:00Z"
NOW = datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC)
CLAIM_NAME = "20261003T120000Z-alice.yaml"
RENDERED = "5" * 40


def node_dir(root: Path, node_id: str = NODE) -> Path:
    return root / "targets" / TARGET / "nodes" / node_id


def file_claim(root: Path, node_id: str = NODE, name: str = CLAIM_NAME) -> str:
    doc = samples.defect_claim(stmt_ref=node_id, **{"class": "wrong-domain"})
    path = node_dir(root, node_id) / "defects" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return f"defects/{name}"


def withdraw(root: Path, node_id: str, withdraws: str) -> None:
    path = node_dir(root, node_id) / "withdrawals" / "20261004T110000Z-founder.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": "withdrawal/v1",
        "withdraws": withdraws,
        "reason": "filed against the wrong reading",
        "author": AUTHOR,
        "date": "2026-10-04",
    }
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def declare(root: Path, node_id: str = NODE, reference: str | None = None) -> Path:
    return curator.declare_status(
        root,
        TARGET,
        node_id,
        "disputed",
        "ground (i) accepted for adjudication: the statement is over the wrong domain",
        author=AUTHOR,
        date=DATE,
        now=NOW,
        reference=reference,
    )


def frontier(root: Path) -> list[str]:
    prod = products.generate(root, rendered_from=RENDERED, commit_time=DATE)
    doc: dict[str, Any] = json.loads(prod.files[Path("frontier.json")])
    return [str(e["node_id"]) for e in doc["entries"]]


def test_a_curator_accepts_a_dispute_naming_the_claim(tmp_path: Path) -> None:
    """The record is ``node-status/v1`` with the claim as its ``reference``; the derived status
    is ``disputed`` and the node leaves the frontier (where a claim is ``node-not-open``)."""
    root = copy_graph(tmp_path, publish=True)
    assert NODE in frontier(root)
    ref = file_claim(root)
    written = declare(root, reference=ref)
    doc = yaml.safe_load(written.read_text(encoding="utf-8"))
    assert schemas.violations(doc, "node-status/v1") == []
    assert (doc["status"], doc["reference"], doc["author"]) == ("disputed", ref, AUTHOR)
    assert graph.load_target(root, TARGET).statuses[NODE] == "disputed"
    assert NODE not in frontier(root)


def test_the_claim_may_be_named_by_its_path_from_the_graph_root(tmp_path: Path) -> None:
    """The form ``graph.dispute_withdrawn`` already reads; the record carries ``defects/<file>``."""
    root = copy_graph(tmp_path, publish=True)
    ref = file_claim(root)
    written = declare(root, reference=f"targets/{TARGET}/nodes/{NODE}/{ref}")
    assert yaml.safe_load(written.read_text(encoding="utf-8"))["reference"] == ref


def test_a_dispute_without_a_claim_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    file_claim(root)
    with pytest.raises(curator.CuratorError, match="names the defect claim"):
        declare(root, reference=None)
    assert not (node_dir(root) / "status").exists()


@pytest.mark.parametrize(
    "reference",
    [
        "defects/20261003T120000Z-nobody.yaml",  # no such file
        "dispute-17",  # a free id names no claim
        f"targets/{TARGET}/nodes/{OTHER}/defects/{CLAIM_NAME}",  # a claim on another node
        f"targets/elsewhere/nodes/{NODE}/defects/{CLAIM_NAME}",  # another target
    ],
)
def test_a_dispute_naming_no_claim_on_the_node_is_refused(tmp_path: Path, reference: str) -> None:
    root = copy_graph(tmp_path, publish=True)
    file_claim(root)
    file_claim(root, OTHER)
    with pytest.raises(curator.CuratorError, match="defect claim"):
        declare(root, reference=reference)
    assert not (node_dir(root) / "status").exists()


def test_a_dispute_naming_a_withdrawn_claim_is_refused(tmp_path: Path) -> None:
    """A withdrawn claim is absent (F08-T31): a dispute resting on it would be void at once."""
    root = copy_graph(tmp_path, publish=True)
    ref = file_claim(root)
    withdraw(root, NODE, ref)
    with pytest.raises(curator.CuratorError, match="withdrawn"):
        declare(root, reference=ref)


def test_a_reference_on_an_abandonment_is_refused(tmp_path: Path) -> None:
    """``reference`` names the accepted claim of a dispute; ``abandoned`` takes none (D-14)."""
    root = copy_graph(tmp_path, publish=True)
    ref = file_claim(root)
    with pytest.raises(curator.CuratorError, match="takes none"):
        curator.declare_status(
            root,
            TARGET,
            NODE,
            "abandoned",
            "dead",
            author=AUTHOR,
            date=DATE,
            now=NOW,
            reference=ref,
        )


def test_the_dispute_lifts_when_its_claim_is_withdrawn(tmp_path: Path) -> None:
    """The record the command writes is one F08-T32's ``disputed_is_void`` can lift."""
    root = copy_graph(tmp_path, publish=True)
    ref = file_claim(root)
    declare(root, reference=ref)
    withdraw(root, NODE, ref)
    assert graph.load_target(root, TARGET).statuses[NODE] == "ready"
    assert NODE in frontier(root)


def test_a_disputed_variant_leaves_the_frontier(tmp_path: Path) -> None:
    """D-18 v3.28: "the node then leaves the frontier" — a variant too. F03-Q12 had kept a
    stale or disputed variant listed and reserved the question; v3.28 answers it for disputed."""
    tg = graph.load_target(copy_graph(tmp_path), TARGET)
    variant = replace(tg.nodes[ROOT], origin="variant")
    status_of = lambda n: tg.statuses.get(n, "ready")  # noqa: E731
    assert not products.in_frontier("disputed", variant, status_of)
    assert products.in_frontier("stale", variant, status_of)


def test_the_status_command_writes_a_dispute(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Through the entry point: ``status <node> disputed --reference defects/<file>``."""
    root = copy_graph(tmp_path, publish=True)
    ref = file_claim(root)
    code = cli.main(
        [
            "status",
            "--graph",
            str(root),
            "--target",
            TARGET,
            "--author",
            AUTHOR,
            "--date",
            DATE,
            NODE,
            "disputed",
            "--cause",
            "ground (i) accepted",
            "--reference",
            ref,
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_PASS, out
    assert out["status"] == "disputed" and len(out["written"]) == 1
    doc = yaml.safe_load((root / out["written"][0]).read_text(encoding="utf-8"))
    assert doc["reference"] == ref
