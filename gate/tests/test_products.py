"""F03: graph derivation (T2; R1-R3, R8; AC1-AC6, AC8) and the products (T3, T4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


# --- T3: the products ----------------------------------------------------------------------------

from opn_gate import cli, products  # noqa: E402

NOW = "2026-09-09T12:00:00Z"
RENDERED = "5" * 40


def generate(
    root: Path, *, commit_time: str = NOW, previous_frontier: dict[str, Any] | None = None
) -> products.Products:
    return products.generate(
        root, rendered_from=RENDERED, commit_time=commit_time, previous_frontier=previous_frontier
    )


def loads(prod: products.Products, rel: str) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(prod.files[Path(rel)])
    return doc


def frontier_ids(prod: products.Products) -> list[str]:
    doc = loads(prod, "frontier.json")
    return [str(e["node_id"]) for e in doc["entries"]]


def test_products_of_the_fixture(tmp_path: Path) -> None:
    """R4, R5, R9, R10 on the pristine fixture: two ready interior nodes, a blocked root."""
    root = copy_graph(tmp_path)
    prod = generate(root)
    assert sorted(p.as_posix() for p in prod.files) == [
        "frontier.json",
        "info.json",
        "targets/index.json",
        "targets/propositional/graph.json",
    ]
    g = loads(prod, "targets/propositional/graph.json")
    assert g["root"] == ROOT_NODE and g["rendered_from"] == RENDERED
    assert [(n["node_id"], n["status"]) for n in g["nodes"]] == [
        ("and-reassoc", "ready"),
        ("and-swap-reassoc", "blocked"),
        ("tutorial-and-swap", "ready"),
    ]
    assert frontier_ids(prod) == ["and-reassoc", "tutorial-and-swap"]
    entry = loads(prod, "frontier.json")["entries"][0]
    assert entry["ready_since"] == NOW and entry["tags"] == {"deps": [], "library": []}
    assert entry["claims"] == {"active": [], "history_count": 0}
    assert entry["claimable"] is False  # no declaration; the root is not the tutorial (Q4, Q5)
    idx = loads(prod, "targets/index.json")["targets"][0]
    assert idx["status"] == "listed" and idx["claimable"] is False
    assert idx["fidelity"] == "mechanical-only" and idx["mathlib_sha"] is None
    assert idx["node_counts"]["ready"] == 2 and idx["node_counts"]["blocked"] == 1
    info = loads(prod, "info.json")
    assert info["protocol_version"] == "3.11"
    assert info["schemas"]["attestation"] == [1, 2, 3] and info["schemas"]["meta"] == [1, 2]
    assert info["targets"]["propositional"]["network_commit"] == "0" * 40
    assert prod.meta_status[Path("targets/propositional/nodes/and-reassoc")] == "ready"


def test_curator_status_removes_from_frontier(tmp_path: Path) -> None:
    """AC4, second half: an abandoned node is absent from the frontier."""
    root = copy_graph(tmp_path)
    node_status_record(root, "and-reassoc", "abandoned")
    assert frontier_ids(generate(root)) == ["tutorial-and-swap"]


def test_proved_nodes_carry_trust_base_and_commit(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    attest(root, "tutorial-and-swap", n=1)
    attest(root, "and-reassoc", n=2, trust_base="compiler")
    prod = generate(root)
    g = loads(prod, "targets/propositional/graph.json")
    by_id = {n["node_id"]: n for n in g["nodes"]}
    assert by_id["and-reassoc"]["trust_base"] == "compiler"
    assert by_id["tutorial-and-swap"]["trust_base"] == "kernel"
    assert by_id["and-reassoc"]["proof_commit"] == MERGE
    assert by_id["and-swap-reassoc"]["trust_base"] is None
    assert frontier_ids(prod) == [ROOT_NODE]
    counts = loads(prod, "targets/index.json")["targets"][0]["node_counts"]
    assert counts["proved"] == 2 and counts["ready"] == 1


def test_cycle_writes_no_product(tmp_path: Path) -> None:
    """AC5: the generator raises before any file exists."""
    root = copy_graph(tmp_path)
    set_deps(root, "and-reassoc", [ROOT_NODE])
    with pytest.raises(GraphError, match="cycle"):
        generate(root)
    assert not (root / "frontier.json").exists()
    assert not (root / "targets" / TARGET / "graph.json").exists()


def test_attempt_aggregation(tmp_path: Path) -> None:
    """AC7: three postmortems and one invalid file on a frontier node."""
    root = copy_graph(tmp_path)
    att = nodes_dir(root) / "and-reassoc" / "attempts"
    docs = [
        samples.postmortem(node="and-reassoc", route_class="induction"),
        samples.postmortem(node="and-reassoc", route_class="case-split", failure_class=None),
        samples.postmortem(
            node="and-reassoc",
            route_class="induction",
            outcome="exhausted",
            failure_class="timeout-blowup",
        ),
    ]
    for i, doc in enumerate(docs):
        if doc.get("failure_class") is None:
            del doc["failure_class"]
        (att / f"2026-09-0{i + 1}-x.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    (att / "2026-09-04-y.yaml").write_text("route: [unterminated\n", encoding="utf-8")
    entry = loads(generate(root), "frontier.json")["entries"][0]
    assert entry["node_id"] == "and-reassoc"
    assert entry["attempts"] == 4
    assert entry["refuted_route_classes"] == ["case-split", "induction"]
    assert entry["failure_class_histogram"] == {
        "invalid": 1,
        "route-dead-ends": 1,
        "timeout-blowup": 1,
    }


def test_ready_since_from_previous_frontier(tmp_path: Path) -> None:
    """AC8 with files: the committed frontier.json feeds the carry-forward."""
    root = copy_graph(tmp_path)
    first = generate(root, commit_time="2026-09-01T00:00:00Z")
    first.write(root)
    attest(root, "and-reassoc", n=1)
    attest(root, "tutorial-and-swap", n=2)
    second = generate(root)  # reads root/frontier.json
    entries = loads(second, "frontier.json")["entries"]
    assert [(e["node_id"], e["ready_since"]) for e in entries] == [(ROOT_NODE, NOW)]
    # Explicitly: a still-ready node keeps its stamp.
    kept = "2026-08-01T00:00:00Z"
    third = generate(
        root, previous_frontier={"entries": [{"node_id": ROOT_NODE, "ready_since": kept}]}
    )
    assert loads(third, "frontier.json")["entries"][0]["ready_since"] == kept


def test_deterministic_and_valid(tmp_path: Path) -> None:
    """AC9: two generations are byte-identical and every product validates."""
    root = copy_graph(tmp_path)
    attest(root, "tutorial-and-swap", n=1)
    node_status_record(root, "and-reassoc", "speculative")
    a = generate(root)
    b = generate(root)
    assert a.files == b.files
    for rel, data in a.files.items():
        assert data.endswith(b"\n") and b"\r" not in data, rel
        assert schemas.violations(json.loads(data)) == [], rel
    written = a.write(root)
    assert sorted(p.as_posix() for p in written) == [
        "frontier.json",
        "info.json",
        "targets/index.json",
        "targets/propositional/graph.json",
        "targets/propositional/nodes/and-reassoc/META.yaml",  # ready -> speculative (R2)
        "targets/propositional/nodes/tutorial-and-swap/META.yaml",  # ready -> proved
    ]
    assert a.write(root) == []  # idempotent: nothing changes on a second write
    meta = yaml.safe_load((nodes_dir(root) / "tutorial-and-swap" / "META.yaml").read_text())
    assert meta["status"] == "proved"
    assert frontier_ids(a) == ["and-reassoc"]  # speculative stays in the frontier (R5)
    entry = loads(a, "frontier.json")["entries"][0]
    assert entry["ready_since"] is None


def test_target_declaration_drives_index(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    st = root / "targets" / TARGET / "status"
    st.mkdir()
    (st / "2026-09-09-1.yaml").write_text(
        yaml.safe_dump(samples.target_status(status="dormant", fidelity="back-translated")),
        encoding="utf-8",
    )
    prod = generate(root)
    idx = loads(prod, "targets/index.json")["targets"][0]
    assert idx["status"] == "dormant" and idx["claimable"] is True
    assert idx["fidelity"] == "back-translated"
    assert all(e["claimable"] for e in loads(prod, "frontier.json")["entries"])
    attest(root, "tutorial-and-swap", n=1)
    attest(root, "and-reassoc", n=2)
    attest(root, ROOT_NODE, n=3)
    idx = loads(generate(root), "targets/index.json")["targets"][0]
    assert idx["status"] == "resolved"  # a proved root beats any declaration


def test_library_tags_from_modules() -> None:
    """R6: top-level Mathlib namespaces, sorted, deduplicated; nothing from Init or nodes."""
    assert products.library_tags_from_modules(
        [
            "Mathlib.Order.Basic",
            "Init.Prelude",
            None,
            "Mathlib.Analysis.Calculus",
            "Mathlib.Order.Lattice",
            "Nodes.«a».Context",
            "Mathlib",
        ]
    ) == ["Analysis", "Order"]


def test_products_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI writes into a git checkout and refuses a defective graph without writing."""
    import subprocess  # noqa: PLC0415

    root = copy_graph(tmp_path)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "GIT_COMMITTER_DATE": "2026-09-09T10:11:12+00:00",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }
    for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "seed"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True, env=env)
    assert cli.main(["products", "--graph", str(root)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] and "frontier.json" in out["written"]
    frontier = json.loads((root / "frontier.json").read_text())
    assert frontier["entries"][0]["ready_since"] == "2026-09-09T10:11:12Z"
    assert frontier["rendered_from"] == out["rendered_from"]
    set_deps(root, "and-reassoc", ["ghost"])
    assert cli.main(["products", "--graph", str(root), "--out", str(tmp_path / "o")]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and "ghost" in out["error"]
    assert not (tmp_path / "o").exists()
