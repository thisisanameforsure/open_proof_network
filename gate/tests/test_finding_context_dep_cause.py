"""F22-T13: a dependency in ``CONTEXT.json`` carries its cause (testers 2026-10-06, P3-12).

Found by R1 on erdos-1050: ``get_node`` listed h1-v2's circular dependency as plain ``ready`` in
``context.deps``, while the dependency's own ``get_node`` said ``cause: circular``. The bundle
copied each dep's ``status`` from the derived states and dropped the ``cause`` beside it, so an
agent choosing what to build against could not see that a dependency's route had been shown
circular. ``context/v4`` gives each ``deps[]`` entry the ``cause`` ``graph.json`` records for that
node (``null`` when it has none). Both builders go through ``context.build`` and
``graph_states``, which already read ``cause`` (F10-Q7), so the service derives the same bytes.

Restated for D-12 v3.35 (F08-T39): a circularity claim is no longer a cause at all, so the dep
entry's ``cause`` is the hole's own mechanical one (``witness-missing`` for an unwitnessed hole)
and the claim is read from the dependency's own row and bundle as its ``circular`` label. What this
file still pins is the rule: every dep entry repeats ``graph.json``'s cause, whatever it is.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness import TARGET
from test_finding_circular_decomposition import generate
from test_finding_circular_path import DEEP, LOW, claimed

from opn_gate import context, products, schemas


def bundle(prod: products.Products, node_id: str) -> dict[str, Any]:
    return dict(json.loads(prod.files[Path(context.context_path(TARGET, node_id))]))


def graph_rows(prod: products.Products) -> dict[str, dict[str, Any]]:
    doc = json.loads(prod.files[Path(f"targets/{TARGET}/graph.json")])
    return {str(n["node_id"]): n for n in doc["nodes"]}


def test_a_dependency_under_a_claim_carries_its_own_cause_and_label(tmp_path: Path) -> None:
    """D-12 v3.35: the dep entry's ``cause`` is graph.json's — the hole's unfilled slot, never
    ``circular`` — and the claim is the dependency's ``circular`` label in its own bundle."""
    prod = generate(claimed(tmp_path))
    rows = graph_rows(prod)
    assert rows[DEEP]["cause"] == "witness-missing"  # the fact the products derive
    assert rows[DEEP]["circular"] != []  # the claim, as a label
    doc = bundle(prod, LOW)
    assert schemas.violations(doc, doc["schema"]) == []
    [dep] = [d for d in doc["deps"] if d["node_id"] == DEEP]
    assert dep.get("cause", "<absent>") == "witness-missing", dep
    assert bundle(prod, DEEP)["circular"] == rows[DEEP]["circular"]


def test_every_dependency_carries_the_cause_graph_json_records(tmp_path: Path) -> None:
    """Every dep of every bundle, ``null`` included: the bundle repeats the products, it never
    re-derives (``context.NodeState``)."""
    prod = generate(claimed(tmp_path))
    rows = graph_rows(prod)
    seen = 0
    for node_id in rows:
        path = Path(context.context_path(TARGET, node_id))
        if path not in prod.files:
            continue
        doc = bundle(prod, node_id)
        assert doc["schema"] == context.SCHEMA
        for dep in doc["deps"]:
            assert dep.get("cause", "<absent>") == rows[dep["node_id"]].get("cause"), (node_id, dep)
            seen += 1
    assert seen > 0
