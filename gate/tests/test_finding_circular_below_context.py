"""F08-T22: the ancestor's ``CONTEXT.json`` names the circular routes below it (``context/v2``).

Found 2026-09-29 with tester 69-C's B3 (F08-T21): the site's ancestor page had named each merged
circularity claim that circles back to it since F08-T20, but the product an agent reads — the
node's bundle, served by MCP ``get_node`` and read by the precheck — said nothing, so an agent
choosing a route could not see which decompositions beneath the node had already been tried and
shown circular. The owner: other agents should be shown "beware, this path is circular".

``context/v2`` adds ``circular_below``: for every merged ``circular-decomposition`` claim whose
ancestor is this node (read through the ancestor's revision chain, F08-T10), the hole it sits
under and the claim file, while the hole is open — the same claims ``graph.circular_marks``
reports to the site, so the two cannot disagree. Derived from the claim files and ``graph.json``
through the bundle's ``Reader``, so the service's toolchain-free builder over the host produces
the same bytes as the post-merge job's over the checkout (F10-Q7); ``context/v1`` is unchanged
(D-34) and a graph rendered before the re-pin still serves it.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import samples
import yaml
from harness import TARGET
from test_finding_circular_decomposition import file_claim, generate
from test_finding_circular_path import (
    CLAIM,
    DEEP,
    MID,
    PATH,
    ROOT,
    chain,
    claimed,
    nodes_dir,
    prove,
)

from opn_gate import context, products, schemas

SCHEMA = "context/v2"


def bundle(prod: products.Products, node_id: str) -> dict[str, Any]:
    return dict(json.loads(prod.files[Path(context.context_path(TARGET, node_id))]))


def test_the_ancestors_bundle_names_the_claim_and_the_hole(tmp_path: Path) -> None:
    root = claimed(tmp_path)
    prod = generate(root)
    doc = bundle(prod, ROOT)
    assert doc["schema"] == SCHEMA
    assert schemas.violations(doc, SCHEMA) == []
    assert doc["circular_below"] == [{"node_id": DEEP, "claim": CLAIM}]
    for node_id in (*PATH, DEEP):
        assert bundle(prod, node_id)["circular_below"] == [], node_id


def test_the_bundle_follows_the_ancestors_revision_chain(tmp_path: Path) -> None:
    """A claim naming a node since replaced names its successor (F08-T10's reading, the one the
    gate's ancestor check took): OLD is superseded by MID, and the claim says OLD."""
    root = chain(tmp_path)
    old = nodes_dir(root) / "old-mid"
    shutil.copytree(nodes_dir(root) / "and-reassoc", old)
    (old / "Proof.lean").unlink()
    meta = yaml.safe_load((old / "META.yaml").read_text(encoding="utf-8"))
    meta.update({"id": "old-mid"})
    (old / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    (old / "status").mkdir()
    (old / "status" / "2026-09-24-1.yaml").write_text(
        yaml.safe_dump(samples.node_status(status="superseded", reference=MID)), encoding="utf-8"
    )
    file_claim(root, CLAIM, stmt_ref=DEEP, ancestor="old-mid")
    prod = generate(root)
    assert bundle(prod, MID)["circular_below"] == [{"node_id": DEEP, "claim": CLAIM}]
    assert bundle(prod, "old-mid")["circular_below"] == []
    assert bundle(prod, ROOT)["circular_below"] == []


def test_a_claim_speaks_only_while_its_hole_is_open(tmp_path: Path) -> None:
    """A proof of the hole is still a proof (D-16), and once it is proved the route is no longer
    a route to warn about: the bundle agrees with the site and the frontier (``circular_marks``)."""
    root = claimed(tmp_path)
    assert bundle(generate(root), ROOT)["circular_below"] != []
    prove(root, DEEP, 9)
    assert bundle(generate(root), ROOT)["circular_below"] == []


def test_the_reader_sees_what_the_tree_holds(tmp_path: Path) -> None:
    """The service derives the bundle through a host reader with ``read`` and ``listdir`` only
    (F10-Q7): the same function over a reader that forgets it is a directory must give the
    same bytes, claims included."""
    root = claimed(tmp_path)
    prod = generate(root)
    gdoc = json.loads(prod.files[Path("targets") / TARGET / "graph.json"])
    states = context.graph_states(gdoc)

    class HostLike:
        def read(self, path: str) -> bytes | None:
            target = root / path
            return target.read_bytes() if target.is_file() else None

        def listdir(self, path: str) -> list[str]:
            directory = root / path
            if not directory.is_dir():
                return []
            return sorted(p.name for p in directory.iterdir() if p.is_file())

    rendered = str(gdoc["rendered_from"])
    for node_id in (ROOT, MID, DEEP):
        derived = context.render(HostLike(), TARGET, node_id, states=states, rendered_from=rendered)
        assert derived == prod.files[Path(context.context_path(TARGET, node_id))], node_id
