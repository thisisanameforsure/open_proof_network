"""F03-T14 (audit 2026-10-04): a closed root is not claimable work.

``targets/index.json`` published ``claimable: true, not_claimable: []`` for two kinds of target
whose root takes no more work:

(a) a target that predates F11 (no ``target.yaml``) whose root is proved: its status is
    ``resolved``, but ``target_facts`` answered with the declaration's flag (or the root's
    ``tutorial`` bit) and never looked at the status — the live ``tutorial`` target;
(b) a target whose root is refuted, defective or abandoned: only ``proved`` makes a target
    ``resolved``, so its status stays open (``listed``, ``active``, ...) and the claimability
    rule, which reads only the status, said yes.

The rule: such a target is ``claimable: false`` with a reason — ``status-resolved`` for (a),
``root-<status>`` for (b). F03-T17 (decisions v3.28, D-33 as written: "resolved (root closed by a
root-level D-12 artifact ...)") then moved the status word for two of (b)'s three: a root refuted by
a merged counterexample or defective by a merged vacuity certificate resolves its target, so the
reason is ``status-resolved`` there too; only an abandoned root (a curator's record, not a D-12
artifact) keeps ``root-abandoned`` and its target's status. The frontier does not move either: like
``status-resolved`` (F03-Q15, D-33 v3.20), a closed root is a fact about the root, so the nodes
beneath it keep the claimability they had (``products.open_beneath``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import harness
import pytest
import samples
import yaml
from harness import TARGET, copy_graph

from opn_gate import graph, intake, layout, products, schemas
from opn_gate.diagnostic import Diagnostic

ROOT_NODE = "and-swap-reassoc"
CURATED = "euclid-primes"
MERGE = "4" * 40
RENDERED = "5" * 40
NOW = "2026-09-09T12:00:00Z"


def nodes_dir(root: Path, target: str = TARGET) -> Path:
    return root / "targets" / target / "nodes"


def attest(root: Path, node_id: str, n: int, target: str = TARGET) -> None:
    statement = (nodes_dir(root, target) / node_id / "Statement.lean").read_bytes()
    doc = samples.attestation(
        node_id=node_id,
        statement_hash=schemas.content_hash(statement),
        merge_commit=MERGE,
        graph_commit="1" * 40,
        runner="hosted",
    )
    (root / "attestations").mkdir(exist_ok=True)
    (root / "attestations" / f"{n:06d}.json").write_bytes(schemas.canonical_json(doc))


def settle(root: Path, node_id: str, suffix: str, n: int, target: str = TARGET) -> None:
    """Merge the artifact ``suffix`` names (D-12) on ``node_id``: ``_refuted`` or ``_vacuous``."""
    node_dir = nodes_dir(root, target) / node_id
    statement = layout.parse_statement((node_dir / "Statement.lean").read_text())
    assert not isinstance(statement, Diagnostic)
    (node_dir / "Proof.lean").write_text(
        f"import Nodes.«{node_id}».Context\n\n"
        f"theorem {statement.decl_name}{suffix} : True := trivial\n",
        encoding="utf-8",
    )
    attest(root, node_id, n, target)


def abandon(root: Path, node_id: str, target: str = TARGET) -> None:
    st = nodes_dir(root, target) / node_id / "status"
    st.mkdir(exist_ok=True)
    (st / "2026-09-09-1.yaml").write_text(
        yaml.safe_dump(samples.node_status(status="abandoned")), encoding="utf-8"
    )


def declare_active(root: Path) -> None:
    """A pre-F11 target declaration that makes the fixture target claimable (F03-Q4)."""
    st = root / "targets" / TARGET / "status"
    st.mkdir(exist_ok=True)
    (st / "2026-09-09-1.yaml").write_text(
        yaml.safe_dump(samples.target_status(status="active")), encoding="utf-8"
    )


def generate(root: Path) -> products.Products:
    return products.generate(root, rendered_from=RENDERED, commit_time=NOW)


def index_row(prod: products.Products, target: str = TARGET) -> dict[str, Any]:
    rows = json.loads(prod.files[Path("targets/index.json")])["targets"]
    (row,) = [r for r in rows if r["target_id"] == target]
    return dict(row)


def frontier(prod: products.Products, target: str = TARGET) -> dict[str, bool]:
    entries = json.loads(prod.files[Path("frontier.json")])["entries"]
    return {str(e["node_id"]): bool(e["claimable"]) for e in entries if e["target_id"] == target}


def test_a_legacy_tutorial_target_with_a_proved_root_is_not_claimable(tmp_path: Path) -> None:
    """(a), the live ``tutorial`` target's shape: no ``target.yaml``, no declaration, the root a
    tutorial node, every node proved. Its status is ``resolved``; it was published claimable."""
    root = copy_graph(tmp_path, publish=True)
    meta = nodes_dir(root) / ROOT_NODE / "META.yaml"
    doc = yaml.safe_load(meta.read_text())
    doc["tutorial"] = True
    meta.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    attest(root, "tutorial-and-swap", 1)
    attest(root, "and-reassoc", 2)
    attest(root, ROOT_NODE, 3)
    assert graph.load_target(root, TARGET).statuses[ROOT_NODE] == "proved"
    row = index_row(generate(root))
    assert row["status"] == "resolved"
    assert row["claimable"] is False
    assert row["not_claimable"] == ["status-resolved"]


def test_a_legacy_declared_target_with_a_proved_root_is_not_claimable(tmp_path: Path) -> None:
    """(a) through a declaration's ``claimable: true``: a proved root beats any declaration for
    the status already (``test_target_declaration_drives_index``); now for claimability too."""
    root = copy_graph(tmp_path, publish=True)
    declare_active(root)
    assert index_row(generate(root))["claimable"] is True  # open until the root closes
    attest(root, "tutorial-and-swap", 1)
    attest(root, "and-reassoc", 2)
    attest(root, ROOT_NODE, 3)
    row = index_row(generate(root))
    assert row["status"] == "resolved"
    assert (row["claimable"], row["not_claimable"]) == (False, ["status-resolved"])


@pytest.mark.parametrize("closing", ["refuted", "defective", "abandoned"])
def test_a_legacy_target_with_a_closed_root_is_not_claimable(tmp_path: Path, closing: str) -> None:
    """(b) on a pre-F11 target declared claimable: the root refuted (a merged counterexample),
    defective (a merged vacuity certificate) or abandoned (a curator's record). The status word
    stays what the declaration says; the reason names the root's status. F03-T17 (D-33, v3.28):
    a refuted or defective root is a root-level D-12 artifact and resolves the target, so those two
    read ``resolved`` with ``status-resolved``; an abandoned root keeps the declared status."""
    root = copy_graph(tmp_path, publish=True)
    declare_active(root)
    attest(root, "tutorial-and-swap", 1)
    attest(root, "and-reassoc", 2)
    if closing == "abandoned":
        abandon(root, ROOT_NODE)
    else:
        settle(root, ROOT_NODE, "_refuted" if closing == "refuted" else "_vacuous", 3)
    assert graph.load_target(root, TARGET).statuses[ROOT_NODE] == closing
    row = index_row(generate(root))
    assert row["claimable"] is False
    if closing == "abandoned":
        assert row["status"] == "active"  # a curator's record is not a D-12 artifact
        assert row["not_claimable"] == ["root-abandoned"]
    else:
        assert row["status"] == "resolved"  # F03-T17: D-33 as written
        assert row["not_claimable"] == ["status-resolved"]


@pytest.mark.parametrize("closing", ["refuted", "defective", "abandoned"])
def test_a_curated_target_with_a_closed_root_is_not_claimable(tmp_path: Path, closing: str) -> None:
    """(b) on a curated target that meets every F11-R4 condition: the claimability rule read only
    the status, which a closed root other than ``proved`` left ``active``. F03-T17: a refuted or
    defective root now resolves the target (D-33 v3.28); an abandoned one leaves it ``active``."""
    root = copy_graph(tmp_path, publish=True)
    harness.take_in(root, CURATED)
    intake.activate(root, CURATED, author="curator", date="2026-09-12T00:00:00Z")
    assert index_row(generate(root), CURATED)["claimable"] is True
    root_id = graph.load_target(root, CURATED).root
    if closing == "abandoned":
        abandon(root, root_id, CURATED)
    else:
        suffix = "_refuted" if closing == "refuted" else "_vacuous"
        settle(root, root_id, suffix, 9, CURATED)
    assert graph.load_target(root, CURATED).statuses[root_id] == closing
    row = index_row(generate(root), CURATED)
    assert row["claimable"] is False
    if closing == "abandoned":
        assert row["status"] == "active"
        assert row["not_claimable"] == ["root-abandoned"]
    else:
        assert row["status"] == "resolved"
        assert row["not_claimable"] == ["status-resolved"]


def test_the_frontier_beneath_a_closed_root_does_not_move(tmp_path: Path) -> None:
    """A closed root is a fact about the root (F03-Q15): the ready nodes beneath a refuted root of
    a target declared claimable keep the claimability they had before the fix."""
    root = copy_graph(tmp_path, publish=True)
    declare_active(root)
    settle(root, ROOT_NODE, "_refuted", 3)
    prod = generate(root)
    assert index_row(prod)["claimable"] is False
    assert frontier(prod) == {"and-reassoc": True, "tutorial-and-swap": True}
    assert products.open_beneath(("root-refuted",)) is True
    assert products.open_beneath(("root-abandoned", "upstream-drift")) is False


def test_the_reasons_read_in_words() -> None:
    """The Targets page and the claims route explain every reason (``intake.explain``)."""
    for closing in ("refuted", "defective", "abandoned"):
        words = intake.explain(f"root-{closing}")
        assert words != f"root-{closing}" and closing in words, words


@pytest.mark.parametrize(
    ("closing", "suffix"), [("refuted", "_refuted"), ("defective", "_vacuous")]
)
def test_a_listed_target_whose_root_is_settled_by_a_d12_artifact_is_resolved(
    tmp_path: Path, closing: str, suffix: str
) -> None:
    """F03-T17 (D-33 as written, decisions v3.28): ``resolved`` is "root closed by a root-level
    D-12 artifact", and a counterexample or a vacuity certificate is one as much as a proof. A
    curated target, listed and never activated, read ``listed`` with a merged counterexample on
    its root; it reads ``resolved``, carries the digestion state every resolved target carries
    (D-33 v3.17), and refuses claims at the root with ``status-resolved`` alone."""
    root = copy_graph(tmp_path, publish=True)
    harness.take_in(root, CURATED)
    assert index_row(generate(root), CURATED)["status"] == "listed"
    root_id = graph.load_target(root, CURATED).root
    settle(root, root_id, suffix, 9, CURATED)
    assert graph.load_target(root, CURATED).statuses[root_id] == closing
    row = index_row(generate(root), CURATED)
    assert row["status"] == "resolved"
    assert (row["claimable"], row["not_claimable"]) == (False, ["status-resolved"])
    assert row["digestion"]["state"] == "undigested"


def test_an_abandoned_root_does_not_resolve_its_target(tmp_path: Path) -> None:
    """F03-T17's edge: ``abandoned`` is a curator's record (D-14), not a D-12 artifact, so the
    target stays ``listed`` and the root's own reason says why nothing is claimable there."""
    root = copy_graph(tmp_path, publish=True)
    harness.take_in(root, CURATED)
    abandon(root, graph.load_target(root, CURATED).root, CURATED)
    row = index_row(generate(root), CURATED)
    assert row["status"] == "listed"
    assert row["not_claimable"] == ["root-abandoned"]
    assert row["digestion"]["state"] is None
