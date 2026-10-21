"""F28-T8 (D-12 v3.42): a node proved by closure, from the tree to the page.

The fixture's ``and-reassoc`` loses its ``Proof.lean`` and gains a closure record joining it with
the proved tutorial node. The products derive it proved and publish the closure (``graph/v10``);
its page says it is proved by closure, links the input and the record, and invents no proof file.
Take the input's proof away and the node is open again: nothing was written that says otherwise.
"""

from __future__ import annotations

import json
from pathlib import Path

import fixture
from harness import TARGET

from opn_gate import closure, products, schemas
from opn_site import model, render

REPO = "https://github.com/example/graph"
NODE = "and-reassoc"
INPUT = "tutorial-and-swap"


def closed(tmp_path: Path, *, input_proved: bool = True) -> Path:
    root = fixture.curated(tmp_path)
    nodes = fixture.nodes_dir(root)
    (nodes / NODE / "Proof.lean").unlink()
    (nodes / NODE / "attempts").mkdir(exist_ok=True)
    (nodes / NODE / "attempts" / "a-partial.lean").write_text("-- assembly\n", encoding="utf-8")
    record = closure.build(
        target_id=TARGET, node_id=NODE,
        statement_hash=schemas.content_hash((nodes / NODE / "Statement.lean").read_bytes()),
        link=closure.Link("route", f"{NODE}@1", (INPUT,)),
        source_path="attempts/a-partial.lean", source_text=None, source_hash="b" * 64,
        axioms=["propext"], graph_commit=fixture.MERGE, network_commit=None,
        lean_toolchain="leanprover/lean4:v4.33.1", mathlib_sha=None, timestamp=fixture.NOW,
    )  # fmt: skip
    closure.write(nodes / NODE, record)
    if not input_proved:
        (nodes / INPUT / "Proof.lean").unlink()
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    return root


def row(root: Path, node_id: str) -> dict[str, object]:
    doc = json.loads((root / "targets" / TARGET / "graph.json").read_text("utf-8"))
    # F28-T8 wrote v10; F08-T42 v11; F29-T1 v12; F08-T43 v13; F08-T44 v14
    assert doc["schema"] == "graph/v14"
    return next(n for n in doc["nodes"] if n["node_id"] == node_id)


def node_page(root: Path, node_id: str) -> str:
    pages = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    [page] = [p for k, p in pages.items() if k.endswith(f"/{node_id}/index.html")]
    return page


def test_the_products_publish_the_node_proved_by_its_closure(tmp_path: Path) -> None:
    got = row(closed(tmp_path), NODE)
    assert got["status"] == "proved"
    assert got["closure"] == {
        "kind": "route", "id": f"{NODE}@1", "inputs": [INPUT], "record": f"{NODE}/closure.json"
    }  # fmt: skip
    assert got["proofs"] == []


def test_its_page_says_proved_by_closure_and_invents_no_proof_file(tmp_path: Path) -> None:
    page = node_page(closed(tmp_path), NODE)
    assert "Proved by closure" in page
    assert f"{INPUT}" in page and "closure.json" in page
    assert "No proof merged yet" not in page


def test_without_the_input_s_proof_the_node_is_open_again(tmp_path: Path) -> None:
    got = row(closed(tmp_path, input_proved=False), NODE)
    assert got["status"] != "proved"
    assert got["closure"] is not None  # the record stands; it simply proves nothing now
