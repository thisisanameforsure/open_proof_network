"""F08-T36 (D-16 v3.28): every defect claim is shown.

D-16 v3.28: "The products list every defect claim filed against a node, with its class and
whether it stands or has been withdrawn (D-18 v3.27). A claim blocks nothing by being filed: what
blocks is a curator accepting it for adjudication (D-18 v3.28)."

Before this task a defect claim reached the products only if its class was
``circular-decomposition`` (F08-T17, T20). A ``wrong-domain`` claim — the class the 2026-09-17
mis-generated holes drew — sat in the tree and no product, no ``CONTEXT.json`` and no page said
it was there, so an agent reading ``get_node`` would prove a statement someone had already shown
to be wrong. ``graph.json`` (the next graph version) now lists, per node, every claim with its
file, class and state, and whether a curator's ``disputed`` record accepts it; ``CONTEXT.json``
carries the same list, through the reader both of its builders share (F10-Q7).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import samples
import yaml
from harness import TARGET, copy_graph

from opn_gate import context, curator, products, records, schemas

NODE = "and-reassoc"
OTHER = "tutorial-and-swap"
STANDING = "20261003T120000Z-alice.yaml"
WITHDRAWN = "20261002T120000Z-bob.yaml"
BROKEN = "20261001T120000Z-carol.yaml"
RENDERED = "5" * 40
DATE = "2026-10-04T12:00:00Z"
NOW = datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC)


def node_dir(root: Path, node_id: str = NODE) -> Path:
    return root / "targets" / TARGET / "nodes" / node_id


def write(root: Path, rel: str, doc: dict[str, Any]) -> None:
    path = root / "targets" / TARGET / "nodes" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def claimed(tmp_path: Path) -> Path:
    """The fixture graph with three claims on ``and-reassoc``: a standing ``wrong-domain`` claim,
    a ``junk-value`` claim a curator has withdrawn, and a file that does not validate."""
    root = copy_graph(tmp_path, publish=True)
    standing = samples.defect_claim(stmt_ref=NODE, **{"class": "wrong-domain"})
    write(root, f"{NODE}/defects/{STANDING}", standing)
    write(root, f"{NODE}/defects/{WITHDRAWN}", samples.defect_claim(stmt_ref=NODE))
    write(root, f"{NODE}/defects/{BROKEN}", {"schema": "defect-claim/v1", "class": "junk-value"})
    write(
        root,
        f"{NODE}/withdrawals/20261004T110000Z-founder.yaml",
        {
            "schema": "withdrawal/v1",
            "withdraws": f"defects/{WITHDRAWN}",
            "reason": "the junk value is never reached",
            "author": "founder",
            "date": "2026-10-04",
        },
    )
    return root


EXPECTED = [
    {
        "file": f"defects/{WITHDRAWN}",
        "class": "junk-value",
        "state": "withdrawn",
        "accepted": False,
    },
    {
        "file": f"defects/{STANDING}",
        "class": "wrong-domain",
        "state": "standing",
        "accepted": False,
    },
]


def generate(root: Path) -> products.Products:
    return products.generate(root, rendered_from=RENDERED, commit_time=DATE)


def graph_row(prod: products.Products, node_id: str = NODE) -> dict[str, Any]:
    doc = json.loads(prod.files[Path(f"targets/{TARGET}/graph.json")])
    (row,) = [n for n in doc["nodes"] if n["node_id"] == node_id]
    return dict(row)


def bundle(prod: products.Products, node_id: str = NODE) -> dict[str, Any]:
    return dict(json.loads(prod.files[Path(context.context_path(TARGET, node_id))]))


def test_graph_json_lists_every_claim_with_its_class_and_state(tmp_path: Path) -> None:
    prod = generate(claimed(tmp_path))
    doc = json.loads(prod.files[Path(f"targets/{TARGET}/graph.json")])
    assert doc["schema"] == products.GRAPH_SCHEMA
    assert schemas.violations(doc, products.GRAPH_SCHEMA) == []
    assert graph_row(prod).get("defect_claims", []) == EXPECTED
    assert graph_row(prod, OTHER).get("defect_claims") == []


def test_a_filed_claim_blocks_nothing(tmp_path: Path) -> None:
    """D-16 v3.28: the node keeps its status and its place on the frontier."""
    prod = generate(claimed(tmp_path))
    plain = generate(copy_graph(tmp_path / "plain", publish=True))
    assert graph_row(prod)["status"] == graph_row(plain)["status"]
    assert prod.files[Path("frontier.json")] == plain.files[Path("frontier.json")]


def test_the_context_bundle_carries_the_same_list(tmp_path: Path) -> None:
    prod = generate(claimed(tmp_path))
    doc = bundle(prod)
    assert doc["schema"] == context.SCHEMA
    assert schemas.violations(doc, context.SCHEMA) == []
    assert doc.get("defect_claims", []) == EXPECTED
    assert bundle(prod, OTHER).get("defect_claims") == []


def test_a_claim_a_curator_accepts_is_marked_accepted(tmp_path: Path) -> None:
    """D-18 v3.28: the ``disputed`` record names the claim it accepts (F08-T35)."""
    root = claimed(tmp_path)
    curator.declare_status(
        root,
        TARGET,
        NODE,
        "disputed",
        "ground (i) accepted",
        author="founder",
        date=DATE,
        now=NOW,
        reference=f"defects/{STANDING}",
    )
    prod = generate(root)
    row = graph_row(prod)
    assert row["status"] == "disputed"
    accepted = {c["file"]: c["accepted"] for c in row["defect_claims"]}
    assert accepted == {f"defects/{WITHDRAWN}": False, f"defects/{STANDING}": True}
    assert bundle(prod)["defect_claims"] == row["defect_claims"]


def test_the_disk_reader_and_the_records_reader_agree(tmp_path: Path) -> None:
    """Two readers of one directory (the curator's check and the products): the same claims."""
    root = claimed(tmp_path)
    from_records = [c.as_dict() for c in records.defect_claims(node_dir(root))]
    from_context = context.defect_claims(context.DiskReader(root), TARGET, NODE, status="ready")
    assert [{k: v for k, v in c.items() if k != "accepted"} for c in from_context] == from_records
