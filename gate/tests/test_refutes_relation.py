"""F08-T45 (D-30 v3.46): a ``refutes`` variant on the record reaches the products as it is.

The label lives in ``Relation.lean``'s ``-- relation:`` line (F03's convention). ``graph.json``
and ``frontier.json`` publish it verbatim, so a reader enumerating a target's sides
(``routes.REFUTES``) and the site's drawing read one word from one place.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import samples
import yaml
from harness import TARGET, copy_graph
from test_products import ROOT_NODE, generate, loads, nodes_dir

from opn_gate import graph, products, schemas

PROPOSALS = Path(__file__).resolve().parent / "fixtures" / "proposals"
REFUTES = "variant-refutes"


def with_refuting_variant(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path, publish=True)
    shutil.copytree(PROPOSALS / REFUTES, nodes_dir(root) / REFUTES)
    # F08-Q19: a variant has no dependents, so the root is declared, as the live record does.
    status = root / "targets" / TARGET / "status"
    status.mkdir(exist_ok=True)
    (status / "2026-10-21-curator.yaml").write_text(
        yaml.safe_dump(samples.target_status(root=ROOT_NODE, author="curator")),
        encoding="utf-8",
    )
    return root


def test_relation_of_reads_refutes(tmp_path: Path) -> None:
    node_dir = with_refuting_variant(tmp_path) / "targets" / TARGET / "nodes" / REFUTES
    assert graph.relation_of(node_dir, "variant") == "refutes"
    assert graph.relation_label("-- relation: refutes\n", "variant") == "refutes"
    # Not a variant: no label, whatever the file says (D-3).
    assert graph.relation_label("-- relation: refutes\n", "authored") is None


def test_graph_and_frontier_publish_refutes_verbatim(tmp_path: Path) -> None:
    """The node's ``graph.json`` row and its frontier entry carry ``relation: "refutes"``, and
    both documents validate against the published schemas (graph/v14, frontier/v8)."""
    root = with_refuting_variant(tmp_path)
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[REFUTES].relation == "refutes"
    doc = schemas.validate(products.graph_doc(tg, None), products.GRAPH_SCHEMA)
    [row] = [n for n in doc["nodes"] if n["node_id"] == REFUTES]
    assert row["relation"] == "refutes"
    assert row["origin"] == "variant"
    assert row["relevance"] is None  # F12-R13: relevance is a related variant's alone
    prod = generate(root)  # every product validated against its published schema
    [entry] = [e for e in loads(prod, "frontier.json")["entries"] if e["node_id"] == REFUTES]
    assert entry["relation"] == "refutes"
    [published] = [
        n for n in loads(prod, f"targets/{TARGET}/graph.json")["nodes"] if n["node_id"] == REFUTES
    ]
    assert published["relation"] == "refutes"
