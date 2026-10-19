"""F10-T50 (D-25 v3.45): the bundle inlines each literature record's summary and references.

``context/v9``'s ``literature`` and ``literature_proposed`` carry the record's ``summary`` and
``references`` beside the fact the graph published, read through the ``Reader`` seam so the
gate's builder (``DiskReader``) and the service's host reader produce the same bytes (F10-Q7).
A record that is missing or does not read leaves the fact as published with a fixed one-line
fallback, and the bundle still validates; the schema's own caps (2000 characters of summary,
20 references) are applied so an oversize record can never make a bundle invalid.

Size budget (§6, ``context.MAX_BYTES`` = 256 KiB): two inlined records are at most about
56 KB at the caps, so the caps are the schema's and the budget is untouched.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_literature import ALICE, RENDERED, TARGET, Graph
from test_literature import keys as keys  # noqa: PLC0414 — the module-scoped key fixture

from opn_gate import context, schemas

PROPOSAL = "literature/20261008T100000Z-bob-prover.yaml"


@pytest.fixture
def graph(tmp_path: Path, keys: dict[str, Path]) -> Graph:
    return Graph(tmp_path, keys)


class BytesReader:
    """A ``Reader`` over a mapping of graph-relative paths, the shape a host reader serves."""

    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    def read(self, path: str) -> bytes | None:
        return self.files.get(path)

    def listdir(self, path: str) -> list[str]:
        prefix = path.rstrip("/") + "/"
        names = (p[len(prefix) :] for p in self.files if p.startswith(prefix))
        return sorted(n for n in names if "/" not in n)


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }


def states_of(graph: Graph) -> dict[str, context.NodeState]:
    prod = graph.render()
    return context.graph_states(json.loads(prod.files[Path("targets") / TARGET / "graph.json"]))


def build(graph: Graph, reader: Any, states: dict[str, context.NodeState]) -> dict[str, Any]:
    return context.build(reader, TARGET, graph.node, states=states, rendered_from=RENDERED)


def record_doc(graph: Graph, rel: str) -> dict[str, Any]:
    return dict(yaml.safe_load((graph.node_dir / rel).read_text(encoding="utf-8")))


# --- the record's words reach the bundle ---------------------------------------------------------


def test_a_proposal_is_inlined_with_the_record_summary_and_references(graph: Graph) -> None:
    graph.proposal()
    prod = graph.render()
    inlined = graph.bundle(prod)["literature_proposed"]
    record = record_doc(graph, PROPOSAL)
    assert inlined["summary"] == record["summary"]
    assert inlined["references"] == record["references"]
    assert graph.bundle(prod)["literature"] is None
    assert schemas.violations(graph.bundle(prod), context.SCHEMA) == []


def test_a_confirmation_is_inlined_with_the_record_it_rests_on(graph: Graph) -> None:
    """Confirming a proposal publishes the proposal's words; stating the status publishes the
    confirmation's own."""
    graph.proposal(summary="Bob's words.")
    graph.signed_by(ALICE, confirms=PROPOSAL, summary="Alice agrees.")
    prod = graph.render()
    inlined = graph.bundle(prod)["literature"]
    assert inlined["record"] == PROPOSAL
    assert inlined["summary"] == "Bob's words."
    assert inlined["references"] == record_doc(graph, PROPOSAL)["references"]
    assert graph.bundle(prod)["literature_proposed"] is None
    assert schemas.violations(graph.bundle(prod), context.SCHEMA) == []


def test_a_steward_stating_the_status_is_inlined_with_her_own_words(graph: Graph) -> None:
    change = graph.signed_by(ALICE, status="open", summary="Nothing is published.")
    own = Path(change.path).name
    inlined = graph.bundle(graph.render())["literature"]
    assert inlined["record"] == f"literature/{own}"
    assert inlined["summary"] == "Nothing is published."
    assert inlined["references"] == record_doc(graph, f"literature/{own}")["references"]


# --- a record that cannot be read ----------------------------------------------------------------


def published_fact(record: str) -> dict[str, Any]:
    return {"status": "known", "record": record, "contributor": "bob-prover"}


def test_a_missing_record_yields_the_fallback_and_the_bundle_validates(graph: Graph) -> None:
    states = states_of(graph)
    state = states[graph.node]
    states[graph.node] = context.NodeState(
        **{**state.__dict__, "literature_proposed": published_fact("literature/gone.yaml")}
    )
    doc = build(graph, context.DiskReader(graph.root), states)
    inlined = doc["literature_proposed"]
    assert inlined["summary"] == context.UNREADABLE_SUMMARY
    assert inlined["references"] == [context.UNREADABLE_REFERENCE]
    assert {k: v for k, v in inlined.items() if k not in ("summary", "references")} == (
        published_fact("literature/gone.yaml")
    )
    assert schemas.violations(doc, context.SCHEMA) == []


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"\xff\xfe: [", id="not-utf8"),
        pytest.param(b"- [unclosed\n", id="not-yaml"),
        pytest.param(b"schema: other/v1\nsummary: x\nreferences: []\n", id="not-literature"),
        pytest.param(b"schema: literature/v2\nsummary: ''\nreferences: []\n", id="no-summary"),
    ],
)
def test_an_unreadable_record_yields_the_fallback(graph: Graph, content: bytes) -> None:
    change = graph.proposal()
    (graph.root / change.path).write_bytes(content)
    states = states_of(graph)
    states[graph.node] = context.NodeState(
        **{**states[graph.node].__dict__, "literature_proposed": published_fact(PROPOSAL)}
    )
    doc = build(graph, context.DiskReader(graph.root), states)
    assert doc["literature_proposed"]["summary"] == context.UNREADABLE_SUMMARY
    assert doc["literature_proposed"]["references"] == [context.UNREADABLE_REFERENCE]
    assert schemas.violations(doc, context.SCHEMA) == []


# --- both builders agree (F10-Q7) ----------------------------------------------------------------


def test_the_bundle_is_byte_identical_through_disk_and_a_reader_serving_the_same_bytes(
    graph: Graph,
) -> None:
    graph.proposal(summary="Bob's words.")
    graph.signed_by(ALICE, status="open", disputes=PROPOSAL, summary="Alice disagrees.")
    states = states_of(graph)
    from_disk = build(graph, context.DiskReader(graph.root), states)
    from_bytes = build(graph, BytesReader(snapshot(graph.root)), states)
    assert schemas.canonical_json(from_disk) == schemas.canonical_json(from_bytes)
    assert from_disk["literature"]["summary"] == "Alice disagrees."
    assert from_disk["literature"]["disputes"]["record"] == PROPOSAL
    assert from_disk["literature_proposed"] is None


# --- the schema's caps ---------------------------------------------------------------------------


def test_an_oversize_record_is_cut_to_the_schema_caps(graph: Graph) -> None:
    """A record the products accepted cannot be oversize (``literature.load`` validates), but the
    reader is the host's and the cap is the bundle's own guard: 2000 characters, 20 references,
    300 of title, applied before the bundle is validated."""
    change = graph.proposal()
    doc = record_doc(graph, PROPOSAL)
    doc["summary"] = "s" * 2500
    doc["references"] = [
        {"title": f"ref {i} " + "t" * 400, "url": None, "note": None} for i in range(25)
    ]
    files = snapshot(graph.root)
    files[change.path] = yaml.safe_dump(doc, sort_keys=False).encode("utf-8")
    states = states_of(graph)
    states[graph.node] = context.NodeState(
        **{**states[graph.node].__dict__, "literature_proposed": published_fact(PROPOSAL)}
    )
    bundle = build(graph, BytesReader(files), states)
    inlined = bundle["literature_proposed"]
    assert len(inlined["summary"]) == context.SUMMARY_MAX_CHARS == 2000
    assert len(inlined["references"]) == context.REFERENCES_MAX == 20
    assert all(len(r["title"]) == context.TITLE_MAX_CHARS == 300 for r in inlined["references"])
    assert schemas.violations(bundle, context.SCHEMA) == []


def test_two_records_at_the_caps_stay_inside_the_size_budget() -> None:
    """§6: the caps are the schema's, and two inlined records at the caps are far under the
    256 KiB bundle budget, so inlining never costs an attempt record."""
    at_cap = {
        "summary": "s" * context.SUMMARY_MAX_CHARS,
        "references": [
            {
                "title": "t" * context.TITLE_MAX_CHARS,
                "url": "https://" + "u" * 492,
                "note": "n" * 500,
            }
        ]
        * context.REFERENCES_MAX,
    }
    assert len(schemas.canonical_json({"a": at_cap, "b": at_cap})) < context.MAX_BYTES // 4
