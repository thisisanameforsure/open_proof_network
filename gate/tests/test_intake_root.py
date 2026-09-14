"""F11-T7: a target is taken in with its root declared, and no later declaration drops it
(R14; AC17, AC18; F08-Q19, F03-Q5; the findings register's §1).

The products read a target's root from its latest status record alone. Without a declaration they
infer the root as the DAG's unique sink, and a D-30 variant or a D-14 crux has no dependents, so
the first of either to merge gives the DAG two sinks and the products stop: silently, because the
site goes on serving the last render. That happened on the tutorial graph, and every live target
was one proposal away from it until graph pull requests #25-#30 declared the six roots by hand.

These tests hold the three writers of a target record to one rule: ``intake new`` (and
``import-fc``, which runs through it) declares the root it scaffolds; ``intake activate`` and
``opn-gate status`` carry forward the root the latest record names, and invent none where none was
declared. Every test that adds a variant writes no status record of its own, because that
hand-written record is exactly the follow-up this task retires.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import TARGET, copy_graph, take_in
from test_intake import LATER, generate, import_fc, index_row

from opn_gate import cli, curator, fidelity, intake, layout, records, scaffold, schemas
from opn_gate import graph as graphmod

NEW = "euclid-primes"
ROOT = "and-reassoc"  # take_in reuses this fixture node as the new target's root
FIXTURE_ROOT = "and-swap-reassoc"  # the pre-F11 fixture target's inferred root
NOW = datetime(2026, 9, 20, tzinfo=UTC)


def latest(root: Path, target_id: str = NEW) -> dict[str, Any]:
    record = records.load_target_status(root / "targets" / target_id)
    assert record is not None, f"{target_id} has no status record"
    return record.doc


def add_related_variant(root: Path, target_id: str = NEW, node_id: str = "variant-related") -> None:
    """A D-30 ``related`` variant: a node with no dependents, and no status record beside it."""
    proposal = scaffold.Proposal(
        node_id=node_id,
        target_id=target_id,
        statement="theorem OpnProp.related_one : ∀ p : Prop, p → p := by\n  sorry\n",
        witness="theorem witness : True := trivial\n",
        author="proposer",
        origin="variant",
        relation="related",
        date="2026-09-12T00:00:00Z",
    )
    scaffold.validate(proposal)
    scaffold.write(layout.graph_nodes_dir(root, target_id), proposal)


def hand_record_without_root(root: Path, target_id: str = NEW, date: str = "2026-09-12") -> None:
    """A later declaration written by hand that omits the root — the pre-R14 shape."""
    status = root / "targets" / target_id / "status"
    status.mkdir(exist_ok=True)
    (status / f"{date.replace('-', '')}T000000Z-someone.yaml").write_text(
        yaml.safe_dump(samples.target_status(status="listed", date=date)), encoding="utf-8"
    )


def ready_to_activate(root: Path) -> None:
    """The two facts activation requires (AC5): a non-author's signature and a posting."""
    fidelity.attest(
        root / "targets" / NEW,
        "root",
        "screened-and-signed",
        attestor="reviewer",
        date="2026-09-11",
        evidence="read the Lean against the English",
    )
    intake.post(root, NEW, venue="erdosproblems.com", url="https://example.org/posting", date=LATER)


# --- R14: intake declares the root it scaffolds (AC17) -------------------------------------------


def test_intake_new_declares_the_root_it_scaffolds(tmp_path: Path) -> None:
    """R14: the listed record names the scaffolded root and validates, and the three places the
    fact appears — the record, what intake reports, what the products publish — agree."""
    root = copy_graph(tmp_path, publish=True)
    result = take_in(root)
    doc = latest(root)
    assert doc["status"] == "listed"
    assert doc["root"] == ROOT == result.root
    assert schemas.violations(doc, "target-status/v2") == []
    assert index_row(root, NEW)["root"] == ROOT


def test_a_new_targets_first_variant_keeps_the_products_rendering(tmp_path: Path) -> None:
    """AC17, the findings register's §1 replayed: a related variant lands on a freshly listed
    target with no curator follow-up, and the products still render, naming the declared root.
    The control shows the test can see the failure: a later record that drops the root puts the
    products back where every live target stood before graph PRs #25-#30."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    add_related_variant(root)
    target = graphmod.load_target(root, NEW)
    assert target.root == ROOT and "variant-related" in target.nodes
    assert index_row(root, NEW)["root"] == ROOT

    hand_record_without_root(root)
    with pytest.raises(graphmod.GraphError, match="root is ambiguous"):
        generate(root)


def test_an_imported_target_declares_itself_as_root(tmp_path: Path) -> None:
    """R9 runs through R2, so the live Erdős shape — one node whose id is the target's — is
    covered by the same rule, and its first variant renders too."""
    root = copy_graph(tmp_path, publish=True)
    result = import_fc(root)
    assert latest(root, "fc-42")["root"] == "fc-42" == result.intake.root
    add_related_variant(root, "fc-42")
    assert graphmod.load_target(root, "fc-42").root == "fc-42"
    assert index_row(root, "fc-42")["root"] == "fc-42"


def test_the_cli_prints_the_root_the_record_declares(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """R14 through the entry point the curator actually runs: ``intake new`` reports the root,
    and the record it wrote names the same one. The record's Mathlib pin is not the fixture
    target's, so no target can supply its image and the curator passes ``--spec`` (F11-R6)."""
    root = copy_graph(tmp_path, publish=True)
    record = tmp_path / "target.yaml"
    record.write_text(yaml.safe_dump(samples.target_record(id=NEW)), encoding="utf-8")
    code = cli.main(
        [
            "intake",
            "new",
            NEW,
            "--graph",
            str(root),
            "--from",
            str(record),
            "--spec",
            str(root / "targets" / TARGET / "gate-spec.json"),
            "--root",
            str(root / "targets" / TARGET / "nodes" / ROOT),
            "--author",
            "curator",
            "--date",
            "2026-09-11T00:00:00Z",
            "--no-toolchain",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_PASS and out["root"] == ROOT
    status_files = [p for p in out["written"] if p.startswith(f"targets/{NEW}/status/")]
    assert len(status_files) == 1
    assert yaml.safe_load((root / status_files[0]).read_text(encoding="utf-8"))["root"] == ROOT


# --- R14: later declarations carry it forward (AC18) --------------------------------------------


def test_later_declarations_carry_the_root_forward(tmp_path: Path) -> None:
    """AC18 over the life a target actually has: listed, activated, dormant, active again. Every
    record in the directory names the root, not only the last, and the products still render
    once a variant has landed."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    ready_to_activate(root)
    intake.activate(root, NEW, author="curator", date="2026-09-12T00:00:00Z")
    curator.declare_status(
        root, NEW, NEW, "dormant", "quiet", author="curator", date="2026-09-13T00:00:00Z", now=NOW
    )
    curator.declare_status(
        root,
        NEW,
        NEW,
        "active",
        "work resumes",
        author="curator",
        date="2026-09-14T00:00:00Z",
        now=NOW,
    )
    status_dir = root / "targets" / NEW / "status"
    docs = [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(status_dir.iterdir())]
    assert [d["status"] for d in docs] == ["listed", "active", "dormant", "active"]
    assert all(d["root"] == ROOT for d in docs)
    assert all(schemas.violations(d, "target-status/v2") == [] for d in docs)

    add_related_variant(root)
    row = index_row(root, NEW)
    assert row["root"] == ROOT and row["status"] == "active" and row["claimable"] is True


@pytest.mark.parametrize("status", ["active", "dormant"])
def test_a_curator_declaration_carries_the_root_forward(tmp_path: Path, status: str) -> None:
    """AC18, one declaration at a time, straight after intake. An ``active`` declaration on a
    curated target needs it claimable first (F11-R5; finding E)."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    if status == "active":
        ready_to_activate(root)
    curator.declare_status(
        root, NEW, NEW, status, "a curator's call", author="curator", date=LATER, now=NOW
    )
    doc = latest(root)
    assert doc["status"] == status and doc["root"] == ROOT
    add_related_variant(root)
    assert index_row(root, NEW)["root"] == ROOT


def test_the_status_command_carries_the_root_forward(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC18 through ``opn-gate status``, on a graph with two targets so ``--target`` is needed,
    and a target claimable enough to be declared active (F11-R5; finding E)."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    ready_to_activate(root)
    code = cli.main(
        [
            "status",
            "--graph",
            str(root),
            "--target",
            NEW,
            "--author",
            "curator",
            "--date",
            "2026-09-12T00:00:00Z",
            NEW,
            "active",
            "--cause",
            "a merge landed",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_PASS
    (written,) = out["written"]
    assert yaml.safe_load((root / written).read_text(encoding="utf-8"))["root"] == ROOT


def test_a_target_that_never_declared_a_root_gets_none(tmp_path: Path) -> None:
    """R14 carries forward; it does not invent. The fixture's pre-F11 target has one sink and no
    declaration, a curator's record on it stays root-less, and F03's inference still speaks."""
    root = copy_graph(tmp_path, publish=True)
    curator.declare_status(
        root, TARGET, TARGET, "active", "a merge landed", author="curator", date=LATER, now=NOW
    )
    assert "root" not in latest(root, TARGET)
    assert graphmod.load_target(root, TARGET).root == FIXTURE_ROOT


def revise_root(root: Path, node_id: str, new_id: str) -> Any:
    """D-8 on the declared root: ``node_id`` superseded by ``new_id``, through the curator's
    own command (F08-R9), with a revision request on file as it requires."""
    request = (
        layout.graph_nodes_dir(root, NEW) / node_id / "revisions" / "20260913T000000-alice.yaml"
    )
    request.parent.mkdir(parents=True, exist_ok=True)
    request.write_text(
        yaml.safe_dump(samples.revision_request(node=node_id, contributor="alice"), sort_keys=True),
        encoding="utf-8",
    )
    statement = (
        f"import Nodes.«{new_id}».Context\n\n"
        "theorem OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by\n  sorry\n"
    )
    return curator.revise(
        root, NEW, node_id, statement, request, author="curator", date="2026-09-13T00:00:00Z"
    )


def test_a_revised_declared_root_is_followed_to_its_revision(tmp_path: Path) -> None:
    """Q29: a declaration names the node that was the root when it was written, and D-8 revises
    a node without rewriting the target's record. Before R14 an undeclared target found the
    revision as the one sink left (F08-R9); declaring the root at intake must not turn that into
    a superseded node published as the root. A variant is present, so inference alone cannot
    rescue the answer: it has to come from following the declaration."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    add_related_variant(root)
    revision = revise_root(root, ROOT, f"{ROOT}-v2")
    target = graphmod.load_target(root, NEW)
    assert target.statuses[ROOT] == "superseded"
    assert target.root == revision.new_id == f"{ROOT}-v2"
    assert index_row(root, NEW)["root"] == f"{ROOT}-v2"


def test_a_twice_revised_declared_root_is_followed_to_the_end(tmp_path: Path) -> None:
    """Q29: the chain is followed to its end, not one step."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    add_related_variant(root)
    first = revise_root(root, ROOT, f"{ROOT}-v2")
    second = revise_root(root, first.new_id, f"{ROOT}-v3")
    assert graphmod.load_target(root, NEW).root == second.new_id == f"{ROOT}-v3"


def test_a_consolidated_declared_root_is_followed_to_the_node_kept(tmp_path: Path) -> None:
    """Q29, D-29's other way to supersede: the root consolidated into a byte-identical duplicate
    names the kept node as its successor, and the declaration follows it."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    nodes = layout.graph_nodes_dir(root, NEW)
    shutil.copytree(nodes / ROOT, nodes / "and-reassoc-again")
    meta_path = nodes / "and-reassoc-again" / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    if "id" in meta:
        meta["id"] = "and-reassoc-again"
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    curator.consolidate(
        root, NEW, "and-reassoc-again", ROOT, author="curator", date="2026-09-13T00:00:00Z"
    )
    target = graphmod.load_target(root, NEW)
    assert target.statuses[ROOT] == "superseded"
    assert target.root == "and-reassoc-again"


def supersede_by_hand(root: Path, node_id: str, successor: str, date: str) -> None:
    node = layout.graph_nodes_dir(root, NEW) / node_id
    doc = curator.node_status_doc(
        "superseded", "a hand-written record", author="curator", date=date, reference=successor
    )
    curator.write_record(node, doc, author="curator", date=date)


def test_a_superseded_root_with_no_successor_is_a_loud_refusal(tmp_path: Path) -> None:
    """C7: a successor that never became a node is refused by name, never published as root."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    supersede_by_hand(root, ROOT, "ghost", "2026-09-13T00:00:00Z")
    with pytest.raises(graphmod.GraphError, match="successor 'ghost' is not a node"):
        graphmod.load_target(root, NEW)


def test_a_supersession_loop_is_a_loud_refusal(tmp_path: Path) -> None:
    """C7: a chain that comes back to itself is refused, not followed forever."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    revision = revise_root(root, ROOT, f"{ROOT}-v2")
    supersede_by_hand(root, revision.new_id, ROOT, "2026-09-14T00:00:00Z")
    with pytest.raises(graphmod.GraphError, match="loop"):
        graphmod.load_target(root, NEW)


def test_the_carried_root_is_the_one_the_products_read(tmp_path: Path) -> None:
    """The writers mirror the reader (F03-Q5: the latest record wins). A later hand record that
    drops the root has undeclared it as far as the products are concerned, so the next tool
    record does not resurrect an older one behind the curator's back (Q29)."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    hand_record_without_root(root)
    curator.declare_status(
        root, NEW, NEW, "dormant", "x", author="curator", date="2026-09-13T00:00:00Z", now=NOW
    )
    assert "root" not in latest(root)
