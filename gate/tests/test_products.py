"""F03: graph derivation (T2; R1-R3, R8; AC1-AC6, AC8) and the products (T3, T4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import samples
import yaml
from harness import GRAPH, TARGET, copy_graph

from opn_gate import graph, schemas
from opn_gate.graph import GraphError

ROOT_NODE = "and-swap-reassoc"
INTERIOR = ("and-reassoc", "tutorial-and-swap")
MERGE = "4" * 40


def nodes_dir(root: Path) -> Path:
    return root / "targets" / TARGET / "nodes"


def statement_hash(root: Path, node_id: str) -> str:
    return schemas.content_hash((nodes_dir(root) / node_id / "Statement.lean").read_bytes())


def attest(
    root: Path, node_id: str, *, merge_commit: str | None = MERGE, n: int = 1, **kw: object
) -> None:
    """Drop a passing attestation for ``node_id`` into ``attestations/``."""
    doc = samples.attestation(
        node_id=node_id,
        statement_hash=statement_hash(root, node_id),
        merge_commit=merge_commit,
        graph_commit="1" * 40,
        runner="hosted",
        **kw,
    )
    att = root / "attestations"
    att.mkdir(exist_ok=True)
    (att / f"{n:06d}.json").write_bytes(schemas.canonical_json(doc))


def set_deps(root: Path, node_id: str, deps: list[str]) -> None:
    meta = nodes_dir(root) / node_id / "META.yaml"
    doc = yaml.safe_load(meta.read_text())
    doc["deps"] = deps
    meta.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def node_status_record(root: Path, node_id: str, status: str) -> None:
    st = nodes_dir(root) / node_id / "status"
    st.mkdir()
    (st / "2026-09-09-1.yaml").write_text(
        yaml.safe_dump(samples.node_status(status=status)), encoding="utf-8"
    )


# --- T2: status model --------------------------------------------------------------------------


def test_status_ready_blocked(tmp_path: Path) -> None:
    """AC1: no attestations — the interior nodes are ready, the root is blocked."""
    root = copy_graph(tmp_path)
    tg = graph.load_target(root, TARGET)
    assert tg.statuses == {
        "and-reassoc": "ready",
        "and-swap-reassoc": "blocked",
        "tutorial-and-swap": "ready",
    }
    assert tg.root == ROOT_NODE
    assert tg.nodes[ROOT_NODE].deps == ("tutorial-and-swap", "and-reassoc")
    assert all(n.proof is None for n in tg.nodes.values())


def test_status_proved_unblocks(tmp_path: Path) -> None:
    """AC2: merged passing attestations for both interior nodes make the root ready."""
    root = copy_graph(tmp_path)
    attest(root, "tutorial-and-swap", n=1)
    attest(root, "and-reassoc", n=2, trust_base="compiler")
    tg = graph.load_target(root, TARGET)
    assert tg.statuses == {
        "and-reassoc": "proved",
        "and-swap-reassoc": "ready",
        "tutorial-and-swap": "proved",
    }
    assert tg.nodes["and-reassoc"].proof == graph.Proof(MERGE, "compiler", "000002.json")
    assert tg.nodes["tutorial-and-swap"].proof == graph.Proof(MERGE, "kernel", "000001.json")


def test_unmerged_pass_does_not_prove(tmp_path: Path) -> None:
    """AC3: a pass without a merge commit is a precheck, not a proof; a stale hash neither."""
    root = copy_graph(tmp_path)
    attest(root, "tutorial-and-swap", merge_commit=None, n=1)
    attest(root, "and-reassoc", n=2)
    tg = graph.load_target(root, TARGET)
    assert tg.statuses["tutorial-and-swap"] == "ready"
    assert tg.statuses["and-reassoc"] == "proved"
    assert tg.statuses[ROOT_NODE] == "blocked"
    # An attestation for an older statement text does not count either.
    att = root / "attestations" / "000002.json"
    doc = json.loads(att.read_text())
    doc["statement_hash"] = "0" * 64
    att.write_bytes(schemas.canonical_json(doc))
    assert graph.load_target(root, TARGET).statuses["and-reassoc"] == "ready"
    # And a failing merged one does not.
    attest(root, "and-reassoc", n=3, verdict="fail", first_failing_step=5)
    assert graph.load_target(root, TARGET).statuses["and-reassoc"] == "ready"


def test_curator_status_precedence(tmp_path: Path) -> None:
    """AC4: a curator record overrides the derived status."""
    root = copy_graph(tmp_path)
    node_status_record(root, "and-reassoc", "abandoned")
    tg = graph.load_target(root, TARGET)
    assert tg.statuses["and-reassoc"] == "abandoned"
    assert tg.statuses[ROOT_NODE] == "blocked"  # an abandoned dep is not proved
    attest(root, "and-reassoc", n=1)  # even a merged proof does not override the record
    assert graph.load_target(root, TARGET).statuses["and-reassoc"] == "abandoned"


def test_cycle_fails_writes_nothing(tmp_path: Path) -> None:
    """AC5 (derivation half): a cycle is named; T3 checks that no product is written."""
    root = copy_graph(tmp_path)
    set_deps(root, "and-reassoc", [ROOT_NODE])
    with pytest.raises(GraphError, match="cycle: and-reassoc -> and-swap-reassoc -> and-reassoc"):
        graph.load_target(root, TARGET)


def test_missing_dep_fails(tmp_path: Path) -> None:
    """AC6."""
    root = copy_graph(tmp_path)
    set_deps(root, "and-reassoc", ["ghost"])
    with pytest.raises(GraphError, match="ghost"):
        graph.load_target(root, TARGET)


def test_root_declared_or_unique(tmp_path: Path) -> None:
    """Q5: two sinks need a declaration; a declaration must name a node."""
    root = copy_graph(tmp_path)
    set_deps(root, ROOT_NODE, ["and-reassoc"])  # now tutorial-and-swap is a second sink
    with pytest.raises(GraphError, match="ambiguous"):
        graph.load_target(root, TARGET)
    st = root / "targets" / TARGET / "status"
    st.mkdir()
    (st / "2026-09-09-1.yaml").write_text(
        yaml.safe_dump(samples.target_status(root=ROOT_NODE)), encoding="utf-8"
    )
    tg = graph.load_target(root, TARGET)
    assert tg.root == ROOT_NODE and tg.declaration is not None
    (st / "2026-09-09-1.yaml").write_text(
        yaml.safe_dump(samples.target_status(root="nobody")), encoding="utf-8"
    )
    with pytest.raises(GraphError, match="nobody"):
        graph.load_target(root, TARGET)


def test_ready_since_carry_forward() -> None:
    """AC8 at the map level: a still-ready node keeps T; a newly ready one gets the commit time."""
    previous = {"and-reassoc": "2026-09-01T00:00:00Z", "tutorial-and-swap": "2026-09-01T00:00:00Z"}
    statuses = {"and-reassoc": "ready", "and-swap-reassoc": "ready", "tutorial-and-swap": "proved"}
    now = "2026-09-09T12:00:00Z"
    assert graph.ready_since_map(previous, statuses, now) == {
        "and-reassoc": "2026-09-01T00:00:00Z",
        "and-swap-reassoc": now,
        "tutorial-and-swap": None,
    }
    frontier = {
        "schema": "frontier/v1",
        "entries": [samples.frontier_entry(node_id="a", ready_since="T")],
    }
    assert graph.previous_ready_since(frontier) == {"a": "T"}
    assert graph.previous_ready_since(None) == {}


def test_write_meta_status_touches_only_the_status_line(tmp_path: Path) -> None:
    """R2, Q1."""
    root = copy_graph(tmp_path)
    meta = nodes_dir(root) / "and-reassoc" / "META.yaml"
    before = meta.read_text()
    assert graph.write_meta_status(meta.parent, "proved") is True
    after = meta.read_text()
    assert after.replace("status: proved", "status: ready") == before
    assert graph.write_meta_status(meta.parent, "proved") is False
    with pytest.raises(ValueError, match="not a node status"):
        graph.write_meta_status(meta.parent, "done")
    assert schemas.violations(yaml.safe_load(after)) == []
    assert GRAPH.is_dir()  # the pristine fixture is never touched


def test_commit_timestamp_is_git_committer_time(tmp_path: Path) -> None:
    """Q2."""
    import subprocess  # noqa: PLC0415

    root = copy_graph(tmp_path)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "GIT_COMMITTER_DATE": "2026-09-09T10:11:12+02:00",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }
    for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "seed"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True, env=env)
    assert graph.commit_timestamp(root, "HEAD") == "2026-09-09T08:11:12Z"
