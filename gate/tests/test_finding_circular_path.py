"""F08-T20 (D-12 v3.22): one circularity claim takes a whole established path off the frontier.

Found live 2026-09-24 on ``erdos-69``: the deepest hole ``erdos-69--h2-v2--h1-v2--h4`` was shown
equivalent to the root, and the frontier went on offering the two holes between them — each one
the root restated once its proved siblings are granted, since the root implies the deep hole, and
the deep hole with the proved holes beside it implies each node back up the chain. Testers had to
file a claim per node (three on the live record) to take the chain off, one pull request each.

The rule (decisions v3.22, D-12 "No cycles"): a merged ``circular-decomposition`` claim on a hole
H with ancestor A takes off the frontier every open node strictly between A and H on a path of
hole edges, provided every *other* entry of every node's ``deps`` on that path is proved. A node
whose siblings are not all proved stays on until they are. A itself stays open and claimable, and
its page names the claim. Derive, never rewrite: every consequence comes from the claim file and
the proved holes, so reverting the claim restores every product byte for byte.

The fixture mirrors erdos-69's live shape: the root decomposed into two holes, the second
decomposed again, and again, the circular claim sitting on the deepest hole and every sibling on
the way proved.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import samples
import yaml
from harness import TARGET, copy_graph
from test_finding_circular_decomposition import file_claim, frontier_ids, generate, graph_row
from test_postmerge import ASSEMBLY, HOLES, PSEUDONYM
from test_products import attest

from opn_gate import graph, modes, postmerge, products
from opn_gate.paths import Change

ROOT = "and-swap-reassoc"  # A: the ancestor, the target's root
MID = f"{ROOT}--h2"  # n1
LOW = f"{MID}--h1"  # n2
DEEP = f"{LOW}--h2"  # H: the hole the claim sits under
SIBLINGS = (f"{ROOT}--h1", f"{MID}--h2", f"{LOW}--h1")  # one per edge on the path
PATH = (MID, LOW)  # strictly between A and H
CLAIM_FILE = "20260924T123647Z-alice.yaml"
CLAIM = f"targets/{TARGET}/nodes/{DEEP}/defects/{CLAIM_FILE}"
CLAIM_REF = f"{DEEP}/defects/{CLAIM_FILE}"


def nodes_dir(root: Path) -> Path:
    return root / "targets" / TARGET / "nodes"


def prove(root: Path, node_id: str, n: int) -> None:
    """A Proof.lean that keeps the statement's name (a proof, F07-R4) and its attestation."""
    node = nodes_dir(root) / node_id
    text = (node / "Statement.lean").read_text(encoding="utf-8")
    (node / "Proof.lean").write_text(text.replace("sorry", "exact trivial"), encoding="utf-8")
    attest(root, node_id, n=n)


def chain(tmp_path: Path, *, unproved: tuple[str, ...] = ()) -> Path:
    """The root decomposed three levels deep, erdos-69's live shape: ROOT → MID → LOW → DEEP by
    hole edges, each written by the post-merge job's own writer, and every sibling on the way
    proved except those named in ``unproved``."""
    root = copy_graph(tmp_path, publish=True)
    (nodes_dir(root) / ROOT / "Proof.lean").unlink()  # the root is open
    attest(root, "tutorial-and-swap", n=1)
    attest(root, "and-reassoc", n=2)
    for i, parent in enumerate((ROOT, MID, LOW)):
        postmerge.apply_partial(
            nodes_dir(root) / parent,
            HOLES,
            partial_text=ASSEMBLY,
            pseudonym=PSEUDONYM,
            stamp=f"2026091{i}T121314Z",
        )
    for n, sibling in enumerate(SIBLINGS, start=3):
        if sibling not in unproved:
            prove(root, sibling, n)
    status = root / "targets" / TARGET / "status"  # an active, claimable target, root declared
    status.mkdir()
    (status / "2026-09-10-1.yaml").write_text(
        yaml.safe_dump(samples.target_status(root=ROOT)), encoding="utf-8"
    )
    return root


def claimed(tmp_path: Path, **kw: tuple[str, ...]) -> Path:
    root = chain(tmp_path, **kw)
    file_claim(root, CLAIM, stmt_ref=DEEP, ancestor=ROOT)
    return root


def frontier_row(prod: products.Products, node_id: str) -> dict[str, object]:
    doc = json.loads(prod.files[Path("frontier.json")])
    rows = [e for e in doc["entries"] if e["node_id"] == node_id]
    assert len(rows) == 1, f"{node_id} is not on the frontier"
    return dict(rows[0])


def test_guard_the_chain_is_work_before_any_claim(tmp_path: Path) -> None:
    root = chain(tmp_path)
    tg = graph.load_target(root, TARGET)
    assert tg.root == ROOT
    assert tg.nodes[ROOT].holes == (f"{ROOT}--h1", MID)
    assert tg.nodes[MID].holes == (f"{MID}--h1", f"{MID}--h2")
    assert all(tg.statuses[s] == "proved" for s in SIBLINGS)
    prod = generate(root)
    assert {ROOT, *PATH, DEEP} <= set(frontier_ids(prod))
    assert all(frontier_row(prod, n)["claimable"] is True for n in (ROOT, *PATH, DEEP))


# --- one claim, the whole path -----------------------------------------------------------------


def test_one_claim_on_the_deepest_hole_takes_the_whole_chain_off(tmp_path: Path) -> None:
    root = chain(tmp_path)
    before = graph.load_target(root, TARGET).statuses
    file_claim(root, CLAIM, stmt_ref=DEEP, ancestor=ROOT)
    prod = generate(root)
    on = frontier_ids(prod)
    for node_id in (*PATH, DEEP):
        assert node_id not in on, node_id
        row = graph_row(prod, node_id)
        assert row["cause"] == "circular", node_id
        assert row["status"] == before[node_id], "the status is untouched (D-3)"
    tg = graph.load_target(root, TARGET)
    assert tg.statuses == before
    for node_id in PATH:
        assert tg.nodes[node_id].circular == CLAIM_REF, "a path node names the claim it rests on"
    assert tg.nodes[DEEP].circular == f"defects/{CLAIM_FILE}"  # its own, as F08-T17 wrote it
    for sibling in SIBLINGS:
        assert graph_row(prod, sibling)["status"] == "proved"
        assert graph_row(prod, sibling).get("cause") is None


def test_a_nearer_ancestor_takes_only_the_nodes_below_it(tmp_path: Path) -> None:
    """The ancestor bounds the path: a claim naming MID takes LOW off and leaves MID on."""
    root = chain(tmp_path)
    file_claim(root, CLAIM, stmt_ref=DEEP, ancestor=MID)
    on = frontier_ids(generate(root))
    assert LOW not in on and DEEP not in on
    assert MID in on and ROOT in on


@pytest.mark.parametrize("sibling", SIBLINGS)
def test_a_node_whose_sibling_is_unproved_stays_on(tmp_path: Path, sibling: str) -> None:
    """The implication back up the chain needs every sibling proved: one unproved sibling on any
    edge breaks the only path, so both nodes between stay work. The claimed hole leaves alone."""
    root = claimed(tmp_path, unproved=(sibling,))
    prod = generate(root)
    on = frontier_ids(prod)
    assert DEEP not in on
    for node_id in PATH:
        assert node_id in on, (node_id, sibling)
        assert graph_row(prod, node_id).get("cause") != "circular"


def test_it_leaves_once_the_sibling_is_proved_with_no_new_record(tmp_path: Path) -> None:
    sibling = f"{MID}--h2"
    root = claimed(tmp_path, unproved=(sibling,))
    assert set(PATH) <= set(frontier_ids(generate(root)))
    prove(root, sibling, 9)  # a proof and its attestation: nothing names the claim
    on = frontier_ids(generate(root))
    assert not set(PATH) & set(on)


def test_a_declared_dep_on_the_path_must_be_proved_too(tmp_path: Path) -> None:
    """Conservative: ROOT's declared deps are "other entries" of its deps like its holes. With
    one of them unproved, ROOT → MID is no edge of the path, so nothing between is taken."""
    root = claimed(tmp_path)
    (root / "attestations" / "000002.json").unlink()  # and-reassoc no longer proved
    tg = graph.load_target(root, TARGET)
    assert tg.statuses["and-reassoc"] == "ready"
    assert all(tg.nodes[n].circular is None for n in PATH)


# --- the ancestor ------------------------------------------------------------------------------


def test_the_ancestor_stays_claimable_and_carries_the_note(tmp_path: Path) -> None:
    root = claimed(tmp_path)
    prod = generate(root)
    row = frontier_row(prod, ROOT)
    assert row["claimable"] is True
    assert graph_row(prod, ROOT).get("cause") is None
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[ROOT] == "ready"
    assert tg.nodes[ROOT].circular is None
    assert tg.nodes[ROOT].circular_below == (CLAIM_REF,)
    assert all(tg.nodes[n].circular_below == () for n in (*PATH, DEEP))


def test_the_ancestor_is_read_through_its_revision_chain(tmp_path: Path) -> None:
    """A claim naming a node that has since been replaced names its successor (F08-T10's reading,
    the one the gate's ancestor check takes): OLD is superseded by MID, and the claim says OLD."""
    root = chain(tmp_path)
    old = nodes_dir(root) / "old-mid"  # any statement will do: only the record is read
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
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[MID].circular_below == (CLAIM_REF,)
    assert tg.nodes["old-mid"].circular_below == ()
    assert tg.nodes[LOW].circular == CLAIM_REF and tg.nodes[MID].circular is None


# --- derive, never rewrite ---------------------------------------------------------------------


def test_reverting_the_claim_restores_every_product_byte_for_byte(tmp_path: Path) -> None:
    root = chain(tmp_path)
    before = generate(root).files
    meta = {n: (nodes_dir(root) / n / "META.yaml").read_bytes() for n in (ROOT, *PATH, DEEP)}
    rel = file_claim(root, CLAIM, stmt_ref=DEEP, ancestor=ROOT)
    assert generate(root).files != before
    assert {n: (nodes_dir(root) / n / "META.yaml").read_bytes() for n in meta} == meta
    (root / rel).unlink()
    assert generate(root).files == before


# --- a proof of a path node is still a proof ---------------------------------------------------


@pytest.mark.parametrize("node_id", PATH)
def test_a_proof_of_a_path_node_is_still_accepted(tmp_path: Path, node_id: str) -> None:
    root = claimed(tmp_path)
    rel = f"targets/{TARGET}/nodes/{node_id}/Proof.lean"
    prove(root, node_id, 9)
    classification = modes.classify([Change("A", rel)])
    assert classification.node_id == node_id
    assert [d.code for d in modes.check(root, classification)] == []
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[node_id] == "proved"
    assert not graph.is_circular(tg.nodes[node_id], tg.statuses[node_id])
    assert graph_row(generate(root), node_id).get("cause") is None
