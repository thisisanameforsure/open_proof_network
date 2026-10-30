"""F32-T6 (R8; F03-Q7; D-12 v3.49): the products read a born-proved hole as proved through its
own record, and through nothing else.

A partial that carried a proof merges as two records with one ``merge_commit``: the partial's
(``node_id`` the parent, ``carried_by: null``) and the hole's (``node_id`` the hole, its own
statement hash, ``artifact_hash`` its composed ``Proof.lean``, ``carried_by`` pointing back).
Every reader finds a proof through an attestation naming its node (F32-Q1), so the hole is
proved, off the frontier and a proved input of its parent's decomposition exactly as a hole
proved by its own pull request is. F03-Q7 still holds: a record with no ``Proof.lean`` in the
tree proves nothing; and the partial's record, which shares the merge commit, is never the
hole's proof.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from harness import TARGET
from test_cli_sandboxed import NODES, Seam
from test_finding_carried_proof_postmerge import H1, H2, recorded
from test_partial import ROOT

from opn_gate import graph, postmerge, products, routes, schemas


def _graph_json(root: Path) -> dict[str, dict[str, object]]:
    doc = json.loads((root / "targets" / TARGET / "graph.json").read_text(encoding="utf-8"))
    return {str(n["node_id"]): n for n in doc["nodes"]}


def test_the_hole_reads_proved_through_its_own_record(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, merge, _bot = recorded(tmp_path, seam, capsys)
    tg = graph.load_target(root, TARGET)
    hole = tg.nodes[H1]
    assert hole.proof is not None
    assert hole.proof.attestation == postmerge.hole_attestation_path(root, 9, H1).name
    assert hole.proof.merge_commit == merge
    assert hole.artifact == "proof"
    assert tg.statuses[H1] == "proved" and tg.statuses[H2] == "ready"
    (record,) = hole.proofs
    assert (record.kind, record.path, record.attestation) == (
        "proof",
        "Proof.lean",
        f"000009.{H1}.json",
    )
    assert record.artifact_hash == schemas.content_hash(
        (root / NODES / H1 / "Proof.lean").read_bytes()
    )
    assert record.used == ()  # its step 8's footprint: nothing of the graph (F32-Q4)
    assert hole.partials == ()  # the hole's run is a proof run, not a partial
    rows = _graph_json(root)
    assert rows[H1]["status"] == "proved" and rows[H1]["proof_commit"] == merge


def test_the_hole_is_off_the_frontier_and_a_proved_input_of_its_route(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _merge, _bot = recorded(tmp_path, seam, capsys)
    frontier = json.loads((root / "frontier.json").read_text(encoding="utf-8"))
    listed = {e["node_id"] for e in frontier["entries"] if e["target_id"] == TARGET}
    assert H1 not in listed and H2 in listed
    doc = json.loads((root / "targets" / TARGET / "graph.json").read_text(encoding="utf-8"))
    (route,) = [r for r in routes.read(doc, frontier["entries"]).routes if r.node == ROOT]
    assert {h.node: h.status for h in route.holes} == {H1: "proved", H2: "ready"}
    assert (route.summary.proved, route.summary.open) == (1, 1)


def test_a_hole_record_without_its_proof_file_proves_nothing(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """F03-Q7: the attestation alone is not enough; the artifact must be in the tree."""
    root, _merge, _bot = recorded(tmp_path, seam, capsys)
    (root / NODES / H1 / "Proof.lean").unlink()
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[H1].artifact is None and tg.nodes[H1].proofs == ()
    assert tg.statuses[H1] == "ready"
    assert products.in_frontier("ready", tg.nodes[H1], lambda n: tg.statuses[n])


def test_the_partials_record_is_never_the_holes_proof(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """With the hole's own record gone, the partial's — same merge commit, a pass, the parent's
    node — is not read as the hole's proof, though ``Proof.lean`` is there; and the parent is
    not proved by it either (its record is a partial's, and the parent has no Proof.lean)."""
    root, _merge, _bot = recorded(tmp_path, seam, capsys)
    postmerge.hole_attestation_path(root, 9, H1).unlink()
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[H1].proof is None and tg.statuses[H1] != "proved"
    assert tg.nodes[ROOT].proof is not None  # the partial's record, kept for its parent
    assert tg.nodes[ROOT].artifact is None and tg.statuses[ROOT] == "blocked"
    (partial,) = tg.nodes[ROOT].partials
    assert partial.attestation == "000009.json"


def test_the_holes_record_does_not_stand_for_the_partial(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """And the other way round: the parent's partial is found through the partial's record
    only, whichever way the two file names sort (F32-Q7)."""
    root, _merge, _bot = recorded(tmp_path, seam, capsys)
    tg = graph.load_target(root, TARGET)
    (partial,) = tg.nodes[ROOT].partials
    assert partial.attestation == "000009.json" and partial.holes == ("right", "left")
    (decomposition,) = products.decompositions_of(tg, ROOT)
    assert decomposition["holes"] == [
        {"name": "right", "node": H1},
        {"name": "left", "node": H2},
    ]
