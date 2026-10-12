"""F10-T49 (D-12 v3.38): ``CONTEXT.json`` (``context/v6``) carries the node's lemmas.

Each lemma rides beside ``deps`` with the same shape plus the hole's name: the lemma node's
``Statement.lean`` verbatim (the signature the proof may use once it is proved), its hash, and
the status and cause ``graph.json`` derived for it — never re-derived here, so the gate's
``DiskReader`` and the service's ``HostReader`` build one document (F10-Q7).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET, copy_graph
from test_finding_graph_lemmas import (
    LEMMA,
    LEMMA_HOLE,
    OTHER_BRANCH,
    revise,
    with_lemma,
    write_lemmas,
    write_node_under,
)
from test_products import ROOT_NODE, nodes_dir

from opn_gate import context, products, schemas

COMMIT = "6" * 40


def generated(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    built = products.generate(root, rendered_from=COMMIT, commit_time="2026-10-10T12:00:00Z")
    gdoc = json.loads(built.files[Path("targets") / TARGET / "graph.json"])
    cdoc = json.loads(built.files[Path(context.context_path(TARGET, ROOT_NODE))])
    return gdoc, cdoc


def test_the_bundle_is_v6_and_carries_the_lemma_with_its_signature(tmp_path: Path) -> None:
    root = with_lemma(tmp_path)
    gdoc, doc = generated(root)
    assert doc["schema"] == "context/v7" == context.SCHEMA  # v6 when written; F26-T1 added review
    assert schemas.violations(doc, "context/v7") == []
    [lemma] = doc["lemmas"]
    statement = (nodes_dir(root) / LEMMA / "Statement.lean").read_bytes()
    [row] = [n for n in gdoc["nodes"] if n["node_id"] == LEMMA]
    assert lemma == {
        "node_id": LEMMA,
        "hole": LEMMA_HOLE,
        "status": row["status"],
        "cause": row["cause"],
        "statement_hash": schemas.content_hash(statement),
        "signature": statement.decode("utf-8"),
    }
    # A lemma is not a dep (D-3 keeps a declared dependency blocking).
    assert LEMMA not in [d["node_id"] for d in doc["deps"]]


def test_a_node_without_lemmas_carries_an_empty_list(tmp_path: Path) -> None:
    _, doc = generated(copy_graph(tmp_path, publish=True))
    assert doc["lemmas"] == [] and doc["schema"] == "context/v7"
    assert "context/v6" in context.ACCEPTED and "context/v5" in context.ACCEPTED


def test_a_revised_lemma_is_carried_as_its_revision(tmp_path: Path) -> None:
    root = with_lemma(tmp_path)
    new = revise(root, LEMMA)
    _, doc = generated(root)
    assert [x["node_id"] for x in doc["lemmas"]] == [new]


def test_the_derived_document_equals_the_committed_one(tmp_path: Path) -> None:
    """F10-Q7 / AC4: one builder, two readers — what the gate wrote and what a reader builds
    from the same tree and the same graph rows are the same document."""
    root = with_lemma(tmp_path)
    gdoc, committed = generated(root)
    derived = context.build(
        context.DiskReader(root),
        TARGET,
        ROOT_NODE,
        states=context.graph_states(gdoc),
        rendered_from=COMMIT,
    )
    assert derived == committed


def test_graph_rows_without_lemmas_fall_back_to_the_record(tmp_path: Path) -> None:
    """A reader given graph rows from before v7 (no ``lemmas`` key) still builds the list from
    ``META.yaml``, read through revisions, so the service's document does not depend on which
    side of the re-pin its graph rows came from."""
    root = with_lemma(tmp_path)
    new = revise(root, LEMMA)
    gdoc, committed = generated(root)
    for row in gdoc["nodes"]:
        del row["lemmas"]
    states = context.graph_states(gdoc)
    assert states[ROOT_NODE].lemmas is None
    derived = context.build(
        context.DiskReader(root), TARGET, ROOT_NODE, states=states, rendered_from=COMMIT
    )
    assert [x["node_id"] for x in derived["lemmas"]] == [new]
    assert derived == committed


def test_a_lemma_the_states_do_not_know_is_an_error(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    write_node_under(root, LEMMA, LEMMA_HOLE, OTHER_BRANCH)
    write_lemmas(root, ROOT_NODE, [{"hole": LEMMA_HOLE, "node": LEMMA}])
    gdoc, _ = generated(root)
    gdoc["nodes"] = [n for n in gdoc["nodes"] if n["node_id"] != LEMMA]
    with pytest.raises(context.ContextError, match="no derived status"):
        context.build(
            context.DiskReader(root),
            TARGET,
            ROOT_NODE,
            states=context.graph_states(gdoc),
            rendered_from=COMMIT,
        )
