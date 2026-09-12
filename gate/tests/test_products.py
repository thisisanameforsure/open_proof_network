"""F03: graph derivation (T2; R1-R3, R8; AC1-AC6, AC8) and the products (T3, T4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import harness
import pytest
import samples
import yaml
from harness import GRAPH, TARGET, copy_graph

from opn_gate import fidelity, graph, intake, layout, schemas
from opn_gate.diagnostic import Diagnostic
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


@pytest.mark.xfail(
    strict=True,
    reason="F03-Q7 / F07-Q18: a merged partial's attestation is indistinguishable from a "
    "proof's, so the assembly's parent is derived `proved` and its target `resolved`. Live on "
    "the graph since 2026-09-12: openproofnetwork.org shows euclid-primes as resolved, 1 proved "
    "4 blocked, with no Proof.lean anywhere under the root. Held, not fixed: which of the two "
    "rules settles it — a node is proved only when it has a recognised artifact file, or the "
    "attestation records the artifact kind and proof_for ignores a partial — is the owner's "
    "call, and it changes what the network asserts about a proof.",
)
def test_a_merged_partial_does_not_prove_its_parent(tmp_path: Path) -> None:
    """A partial reduces a statement to its holes; it does not settle it (D-12 #5, D-29).

    The assembly is filed under ``attempts/`` and never as ``Proof.lean`` (F07-R4, F11-Q28), yet
    the post-merge job signs a passing attestation against the parent's statement hash for a
    partial exactly as for a proof, and ``status_of`` reads any passing attestation as a proof
    because ``artifact_of`` answers ``None`` for a node with no proof file and the caller
    defaults that to ``"proof"``. Every fixture node is in that same state — none has a
    ``Proof.lean`` — which is why the whole suite agreed.
    """
    root = copy_graph(tmp_path)
    node = nodes_dir(root) / ROOT_NODE
    (node / "attempts").mkdir(exist_ok=True)
    (node / "attempts" / "20260912T000000Z-anon-partial.lean").write_text(
        "-- the assembly of a merged partial\n", encoding="utf-8"
    )
    attest(root, ROOT_NODE)
    assert not (node / "Proof.lean").exists()
    assert graph.load_target(root, TARGET).statuses[ROOT_NODE] != "proved"


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
        "targets/propositional/nodes/and-reassoc/CONTEXT.json",  # F10-R3
        "targets/propositional/nodes/and-swap-reassoc/CONTEXT.json",
        "targets/propositional/nodes/tutorial-and-swap/CONTEXT.json",
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
    assert info["protocol_version"] == "3.12"
    assert info["schemas"]["attestation"] == [1, 2, 3, 4] and info["schemas"]["meta"] == [
        1,
        2,
        3,
        4,
    ]
    assert info["schemas"]["defect-claim"] == [1, 2] and info["schemas"]["revision-request"] == [
        1,
        2,
    ]
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
        "targets/propositional/nodes/and-reassoc/CONTEXT.json",  # F10-R3
        "targets/propositional/nodes/and-reassoc/META.yaml",  # ready -> speculative (R2)
        "targets/propositional/nodes/and-swap-reassoc/CONTEXT.json",
        "targets/propositional/nodes/tutorial-and-swap/CONTEXT.json",
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
        yaml.safe_dump(samples.target_status(status="dormant", fidelity="screened-and-signed")),
        encoding="utf-8",
    )
    prod = generate(root)
    idx = loads(prod, "targets/index.json")["targets"][0]
    assert idx["status"] == "dormant" and idx["claimable"] is True
    assert idx["fidelity"] == "screened-and-signed"
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


# --- T4: golden products -------------------------------------------------------------------------

GOLDEN = Path(__file__).resolve().parent / "golden" / "products"
STATES = ("unproved", "interior-proved", "curated")


def build_state(tmp_path: Path, state: str) -> Path:
    """The fixture graph in one of three states, with every timestamp and hash fixed."""
    root = copy_graph(tmp_path)
    if state == "unproved":
        return root
    attest(root, "tutorial-and-swap", n=1)
    if state == "interior-proved":
        attest(root, "and-reassoc", n=2, trust_base="compiler")
        return root
    # curated: one interior node proved, the other speculative with attempts and an annex, and a
    # curator declaration that makes the target claimable and screened-and-signed.
    node_status_record(root, "and-reassoc", "speculative")
    att = nodes_dir(root) / "and-reassoc" / "attempts"
    (att / "2026-09-01-a.yaml").write_text(
        yaml.safe_dump(samples.postmortem(node="and-reassoc", route_class="case-split")),
        encoding="utf-8",
    )
    (att / "2026-09-02-b.yaml").write_text(
        yaml.safe_dump(
            samples.postmortem(
                node="and-reassoc",
                route_class="induction",
                outcome="exhausted",
                failure_class="missing-library",
            )
        ),
        encoding="utf-8",
    )
    (att / "2026-09-03-c.yaml").write_text("outcome: [oops\n", encoding="utf-8")
    (nodes_dir(root) / "and-reassoc" / "annex" / "sketch.md").write_text("informal\n")
    st = root / "targets" / TARGET / "status"
    st.mkdir()
    (st / "2026-09-05-1.yaml").write_text(
        yaml.safe_dump(samples.target_status(fidelity="screened-and-signed", date="2026-09-05")),
        encoding="utf-8",
    )
    return root


def write_goldens(base: Path = GOLDEN) -> None:
    """Regenerate the golden files (see golden/products/README.md); review the diff by eye."""
    import tempfile  # noqa: PLC0415

    for state in STATES:
        with tempfile.TemporaryDirectory() as tmp:
            prod = generate(build_state(Path(tmp), state))
            for rel, data in prod.files.items():
                target = base / state / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)


@pytest.mark.parametrize("state", STATES)
def test_golden(tmp_path: Path, state: str) -> None:
    """AC11: the generated products equal the checked-in golden files, byte for byte."""
    prod = generate(build_state(tmp_path, state))
    expected = sorted(p.relative_to(GOLDEN / state) for p in (GOLDEN / state).rglob("*.json"))
    assert sorted(prod.files) == expected, "the set of products changed; regenerate the goldens"
    for rel, data in prod.files.items():
        golden = (GOLDEN / state / rel).read_bytes()
        assert data == golden, f"{state}/{rel} differs from the golden file"


# --- F07-T4 / AC10: what a merged counterexample and a merged vacuity make of a node (R8) --------


def refute(root: Path, node_id: str, suffix: str) -> None:
    """Rewrite a node's Proof.lean as the artifact ``suffix`` names, as a merge would leave it."""
    node_dir = nodes_dir(root) / node_id
    statement = layout.parse_statement((node_dir / "Statement.lean").read_text())
    assert not isinstance(statement, Diagnostic)
    decl = statement.decl_name + suffix
    (node_dir / "Proof.lean").write_text(
        f"import Nodes.«{node_id}».Context\n\ntheorem {decl} : True := trivial\n", encoding="utf-8"
    )


def test_refuted_and_defective_statuses(tmp_path: Path) -> None:
    """AC10: a merged counterexample refutes the node and its dependents carry dep-refuted; a
    merged vacuity certificate makes it defective."""
    root = copy_graph(tmp_path)
    refute(root, "tutorial-and-swap", "_refuted")
    attest(root, "tutorial-and-swap", n=1)
    attest(root, "and-reassoc", n=2)

    tg = graph.load_target(root, TARGET)
    assert tg.statuses["tutorial-and-swap"] == "refuted"
    assert tg.statuses["and-reassoc"] == "proved"
    # The root depends on both, so a refuted dependency blocks it — and says why.
    assert tg.statuses["and-swap-reassoc"] == "blocked"
    causes = graph.derive_causes(tg.nodes, tg.statuses)
    assert causes["and-swap-reassoc"] == graph.CAUSE_DEP_REFUTED
    assert causes["and-reassoc"] is None

    doc = products.graph_doc(tg, "5" * 40)
    assert schemas.violations(doc, products.GRAPH_SCHEMA) == []
    by_id = {n["node_id"]: n for n in doc["nodes"]}
    assert by_id["tutorial-and-swap"]["status"] == "refuted"
    assert by_id["tutorial-and-swap"]["proof_commit"] == MERGE  # the artifact merged (D-12)
    assert by_id["and-swap-reassoc"]["cause"] == graph.CAUSE_DEP_REFUTED
    assert by_id["and-reassoc"]["cause"] is None

    # A vacuity certificate is the other resolution, and it is not a refutation.
    other = copy_graph(tmp_path / "b")
    refute(other, "tutorial-and-swap", "_vacuous")
    attest(other, "tutorial-and-swap", n=1)
    tg2 = graph.load_target(other, TARGET)
    assert tg2.statuses["tutorial-and-swap"] == "defective"
    causes2 = graph.derive_causes(tg2.nodes, tg2.statuses)
    assert causes2["and-swap-reassoc"] is None  # blocked, but not by a refutation


def test_resolved_nodes_leave_the_frontier(tmp_path: Path) -> None:
    """R5, R8: the frontier is what is still worth attacking, so a refuted node is not on it."""
    root = copy_graph(tmp_path)
    refute(root, "tutorial-and-swap", "_refuted")
    attest(root, "tutorial-and-swap", n=1)
    tg = graph.load_target(root, TARGET)
    node = tg.nodes["tutorial-and-swap"]
    assert not products.in_frontier(tg.statuses["tutorial-and-swap"], node)
    assert products.in_frontier("ready", node)


def test_node_counts_carry_the_new_statuses(tmp_path: Path) -> None:
    """R8: targets-index/v2 counts them, so the counts still sum to the node total."""
    root = copy_graph(tmp_path)
    refute(root, "tutorial-and-swap", "_refuted")
    attest(root, "tutorial-and-swap", n=1)
    tg = graph.load_target(root, TARGET)
    doc = products.index_doc([tg], "5" * 40)
    assert schemas.violations(doc, products.INDEX_SCHEMA) == []
    counts = doc["targets"][0]["node_counts"]
    assert counts["refuted"] == 1
    assert sum(counts.values()) == len(tg.nodes)


# --- R3, C7: every defective input is named, and nothing is written ------------------------------

from fakes import FakeToolchain, metaprogram_garbage  # noqa: E402

from opn_gate import records  # noqa: E402
from opn_gate.toolchain import ElabResult  # noqa: E402


def assert_nothing_generated(root: Path) -> None:
    assert not (root / "frontier.json").exists()
    assert not (root / "info.json").exists()
    assert not (root / "targets" / "index.json").exists()
    assert not (root / "targets" / TARGET / "graph.json").exists()


def test_malformed_attestation_is_a_graph_defect(tmp_path: Path) -> None:
    """A committed attestation that does not parse or validate stops generation naming the file;
    it is never skipped, because skipping it would silently un-prove a node."""
    root = copy_graph(tmp_path)
    att = root / "attestations"
    att.mkdir()
    (att / "000001.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(GraphError, match=r"attestation .*000001\.json is malformed"):
        generate(root)
    assert_nothing_generated(root)

    attest(root, "tutorial-and-swap", n=1)
    doc = json.loads((att / "000001.json").read_text())
    doc["verdict"] = "maybe"
    (att / "000001.json").write_bytes(schemas.canonical_json(doc))
    with pytest.raises(GraphError, match="malformed"):
        generate(root)
    assert_nothing_generated(root)


def test_malformed_meta_names_the_node(tmp_path: Path) -> None:
    """A node whose META does not parse, or names another id, is refused by name (R3)."""
    root = copy_graph(tmp_path)
    meta = nodes_dir(root) / "and-reassoc" / "META.yaml"
    meta.write_text("id: [unterminated\n", encoding="utf-8")
    with pytest.raises(GraphError, match="node and-reassoc"):
        generate(root)
    assert_nothing_generated(root)

    other = copy_graph(tmp_path / "b")
    meta = nodes_dir(other) / "and-reassoc" / "META.yaml"
    meta.write_text(meta.read_text().replace("id: and-reassoc", "id: tutorial-and-swap"))
    with pytest.raises(GraphError, match=r"node and-reassoc: .*differs from directory"):
        generate(other)


def test_missing_status_is_refused_by_the_meta_writer(tmp_path: Path) -> None:
    """R2: the bot rewrites only the status line; a META with none to rewrite is a defect, not a
    file the bot appends to."""
    root = copy_graph(tmp_path)
    meta = nodes_dir(root) / "and-reassoc" / "META.yaml"
    meta.write_text(meta.read_text().replace("status: ready\n", ""), encoding="utf-8")
    with pytest.raises(GraphError, match="no status line"):
        graph.write_meta_status(meta.parent, "proved")


def test_target_without_nodes_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    for node in nodes_dir(root).iterdir():
        import shutil  # noqa: PLC0415

        shutil.rmtree(node)
    with pytest.raises(GraphError, match="has no nodes"):
        generate(root)
    assert_nothing_generated(root)


def test_stray_target_directory_stops_generation(tmp_path: Path) -> None:
    """A directory under targets/ that is not a target (no gate-spec.json) is a defect of the
    whole graph, and the good target's products are not written either (R3, C7)."""
    root = copy_graph(tmp_path)
    (root / "targets" / "stray").mkdir()
    with pytest.raises(schemas.SchemaError, match=r"gate-spec\.json"):
        generate(root)
    assert_nothing_generated(root)
    assert products.target_ids(root) == [TARGET, "stray"]


def test_invalid_committed_claims_are_dropped_with_a_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """F05-Q3, C7: a claims.json that does not validate never blocks a merge; the frontier
    carries no claims and the log says why."""
    import logging  # noqa: PLC0415

    root = copy_graph(tmp_path)
    (root / "claims.json").write_text('{"schema": "claims/v1"}', encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        assert products.load_claims(root) == {}
        prod = generate(root)
    assert "claims.json does not validate" in caplog.text
    assert all(
        e["claims"] == {"active": [], "history_count": 0}
        for e in loads(prod, "frontier.json")["entries"]
    )
    (root / "claims.json").write_text("not json", encoding="utf-8")
    assert products.load_claims(root) == {}


def test_statement_scan_failures_are_graph_errors(tmp_path: Path) -> None:
    """R6 through the seam: a Context that does not elaborate, or a metaprogram that returns no
    verdict, names the node rather than tagging it with nothing."""
    root = copy_graph(tmp_path)
    tg = graph.load_target(root, TARGET)
    node = tg.nodes["and-reassoc"]
    from fakes import FAKE_RESOLVED  # noqa: PLC0415

    broken = FakeToolchain(elab=ElabResult(ok=False))
    with pytest.raises(GraphError, match="Context does not elaborate; cannot tag and-reassoc"):
        products.scan_statement(broken, FAKE_RESOLVED, node, tmp_path / "w1")

    garbage = FakeToolchain(constants=metaprogram_garbage(output="boom"))
    with pytest.raises(GraphError, match="opn-used-constants failed on and-reassoc: boom"):
        products.scan_statement(garbage, FAKE_RESOLVED, node, tmp_path / "w2")


def test_tag_cache_ignores_a_file_that_is_not_an_object(tmp_path: Path) -> None:
    """A bot-owned cache that is not a mapping is treated as empty: the scan runs again rather
    than trusting a shape it cannot read."""
    path = tmp_path / ".tags-cache.json"
    path.write_text("[1, 2]", encoding="utf-8")
    cache = products.TagCache(path)
    assert cache.entries == {}
    root = copy_graph(tmp_path)
    node = graph.load_target(root, TARGET).nodes["and-reassoc"]
    scans: list[str] = []

    def scanner(n: graph.NodeFacts) -> list[str]:
        scans.append(n.node_id)
        return ["Order", "Algebra"]

    assert cache.tags(node, scanner) == ["Algebra", "Order"]
    assert cache.tags(node, scanner) == ["Algebra", "Order"]
    assert scans == ["and-reassoc"] and cache.dirty


def test_find_root_edge_cases_with_revisions(tmp_path: Path) -> None:
    """F08-Q16: superseded sinks and revisions of interior nodes are set aside — but when nothing
    is left, or two candidates remain, the root is still ambiguous rather than guessed."""
    root = copy_graph(tmp_path)
    tg = graph.load_target(root, TARGET)

    def facts(base: str, **kw: object) -> graph.NodeFacts:
        from dataclasses import replace  # noqa: PLC0415

        return replace(tg.nodes[base], **kw)  # type: ignore[arg-type]

    superseded = records.StatusRecord("superseded", "c", "2026-09-10", Path("x"), {})
    # Two revisions of two different sinks, both un-depended-on: two candidates remain.
    two = {
        "a": facts("and-reassoc", node_id="a", deps=()),
        "a-v2": facts("and-reassoc", node_id="a-v2", deps=(), supersedes="a"),
        "b": facts("tutorial-and-swap", node_id="b", deps=()),
        "b-v2": facts("tutorial-and-swap", node_id="b-v2", deps=(), supersedes="b"),
    }
    with pytest.raises(GraphError, match="ambiguous: 2 nodes"):
        graph.find_root(two, None)
    # Every sink superseded and nothing revising it: zero candidates, still ambiguous.
    none = {
        "a": facts("and-reassoc", node_id="a", deps=(), override=superseded),
        "b": facts("tutorial-and-swap", node_id="b", deps=(), override=superseded),
    }
    with pytest.raises(GraphError, match="ambiguous: 0 nodes"):
        graph.find_root(none, None)
    # A superseded root and its revision: the revision is the root.
    revised = {
        "a": facts("and-reassoc", node_id="a", deps=(), override=superseded),
        "a-v2": facts("and-reassoc", node_id="a-v2", deps=(), supersedes="a"),
    }
    assert graph.find_root(revised, None) == "a-v2"


# --- F11-T2: fidelity signatures, dormancy and claimability in the products (R3, R4) ------------


F11_TARGET = "euclid-primes"
F11_DEFS = {"Primes.lean": "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p\n"}


def claimable_target(tmp_path: Path, *, defs: dict[str, str] | None = None) -> Path:
    """A curated target that satisfies every one of R4's three conditions."""
    root = copy_graph(tmp_path)
    harness.take_in(root, defs=defs)
    target = root / "targets" / F11_TARGET
    fidelity.attest(
        target,
        "root",
        "screened-and-signed",
        attestor="reviewer",
        date="2026-09-12",
        evidence="read the Lean against the English",
    )
    for name in defs or {}:
        fidelity.attest(
            target,
            Path(name).stem,
            "screened-and-signed",
            attestor="reviewer",
            date="2026-09-12",
            evidence="read the definition against the English",
        )
    intake.post(
        root,
        F11_TARGET,
        venue="erdosproblems.com",
        url="https://example.org/p",
        date="2026-09-12T00:00:00Z",
    )
    intake.activate(root, F11_TARGET, author="curator", date="2026-09-12T00:00:00Z")
    return root


def f11_row(root: Path, prod: products.Products | None = None) -> dict[str, Any]:
    products_ = prod if prod is not None else generate(root)
    rows = loads(products_, "targets/index.json")["targets"]
    return next(r for r in rows if r["target_id"] == F11_TARGET)


def declare(root: Path, status: str, date: str = "2026-09-13") -> None:
    directory = root / "targets" / F11_TARGET / "status"
    directory.mkdir(exist_ok=True)
    (directory / f"{date}-curator.yaml").write_text(
        yaml.safe_dump(
            {
                "schema": "target-status/v2",
                "status": status,
                "cause": "for the test",
                "author": "curator",
                "date": date,
            }
        ),
        encoding="utf-8",
    )


def test_signature_count(tmp_path: Path) -> None:
    """AC13: two certificates by different attestors give a signature count of 2 and both names
    in targets-index/v3, and the untouched v1 schema still validates a v1 document."""
    root = copy_graph(tmp_path)
    harness.take_in(root)
    target = root / "targets" / F11_TARGET
    for who, date in (("reviewer", "2026-09-12"), ("auditor", "2026-09-13")):
        fidelity.attest(
            target,
            "root",
            "screened-and-signed",
            attestor=who,
            date=date,
            evidence=f"{who} read it",
        )
    row = f11_row(root)
    subject = next(s for s in row["subjects"] if s["subject"] == "root")
    assert subject["signature_count"] == 2
    assert subject["signers"] == ["reviewer", "auditor"]
    assert row["fidelity"] == "screened-and-signed"

    # D-34: v1 was not edited, so a v1 consumer still validates a v1 document.
    old = json.loads((GOLDEN / "unproved" / "targets" / "index.json").read_bytes())
    old["schema"] = "targets-index/v1"
    for entry in old["targets"]:
        for key in ("track", "subjects", "posting", "not_claimable", "attempts", "drift"):
            entry.pop(key, None)
        for key in ("refuted", "defective"):
            entry["node_counts"].pop(key, None)
    assert schemas.violations(old, "targets-index/v1") == []


def test_dormant_target_stays_claimable(tmp_path: Path) -> None:
    """AC15, R4, D-33: a dormancy declaration refuses no claim — every ready node stays
    claimable and the frontier carries `dormant` as a fact. `resolved` and `known-result` do
    close claiming, and the reason names the status."""
    root = claimable_target(tmp_path)
    declare(root, "dormant")
    prod = generate(root)
    row = f11_row(root, prod)
    assert row["status"] == "dormant" and row["claimable"] is True and row["not_claimable"] == []
    entries = [e for e in loads(prod, "frontier.json")["entries"] if e["target_id"] == F11_TARGET]
    assert entries, "the curated target has nothing on the frontier"
    assert all(e["claimable"] and e["dormant"] for e in entries)
    # The tutorial graph's own entries are not dormant: the fact is per target, not per graph.
    others = [e for e in loads(prod, "frontier.json")["entries"] if e["target_id"] == TARGET]
    assert all(e["dormant"] is False for e in others)

    for closing in ("resolved", "known-result"):
        declare(root, closing, date="2026-09-14")
        row = f11_row(root)
        assert row["claimable"] is False, closing
        assert row["not_claimable"] == [f"status-{closing}"], closing
        (root / "targets" / F11_TARGET / "status" / "2026-09-14-curator.yaml").unlink()


def test_the_target_grade_is_its_weakest_subject_in_the_index(tmp_path: Path) -> None:
    """R3 through to the product: an uncertified definition holds the whole target down, and
    the index says so rather than publishing the root's grade alone."""
    root = claimable_target(tmp_path)
    target = root / "targets" / F11_TARGET
    (target / "defs" / "Later.lean").write_text("def Opn.Later : Nat := 1\n", encoding="utf-8")
    row = f11_row(root)
    assert row["fidelity"] == "mechanical-only"
    assert row["claimable"] is False
    assert "grade-below-screened-and-signed" in row["not_claimable"]
    assert {s["subject"] for s in row["subjects"]} == {"root", "Later"}


# --- F12-T6: the QA pass, the attempts, the drift flag and a related variant's signature --------


def related_variant(root: Path, node_id: str = "variant-related") -> Path:
    """A `related` variant of the propositional root: no Relation.lean, no implication proved."""
    from opn_gate import scaffold  # noqa: PLC0415

    proposal = scaffold.Proposal(
        node_id=node_id,
        target_id=TARGET,
        statement="theorem OpnProp.related_one : ∀ p : Prop, p → p := by\n  sorry\n",
        witness="theorem witness : True := trivial\n",
        author="proposer",
        origin="variant",
        relation="related",
        date="2026-09-12T00:00:00Z",
    )
    scaffold.validate(proposal)
    written = scaffold.write(nodes_dir(root), proposal)
    # A related variant has no dependents, so the DAG has two sinks and the root must be declared
    # (F08-Q19; the live graph's first variant taught the same, engineering/CLAUDE.md log).
    status = root / "targets" / TARGET / "status"
    status.mkdir(exist_ok=True)
    (status / "2026-09-12-curator.yaml").write_text(
        yaml.safe_dump(samples.target_status(root=ROOT_NODE)), encoding="utf-8"
    )
    return written


def test_related_variant_needs_signature(tmp_path: Path) -> None:
    """F12-AC10, R13 (D-30 v3.12): with no relevance signature a related variant is not marked
    pertinent; with one it is, and the signer is named; a resolves or partial variant and an
    authored node carry null. The proposer may not sign their own, and a signature is written
    once."""
    from opn_gate import qa  # noqa: PLC0415

    root = copy_graph(tmp_path)
    related_variant(root)
    prod = generate(root)
    rows = {
        n["node_id"]: n
        for n in json.loads(prod.files[Path(f"targets/{TARGET}/graph.json")])["nodes"]
    }
    assert rows["variant-related"]["relevance"] == {
        "pertinent": False,
        "signer": None,
        "date": None,
    }
    assert rows["tutorial-and-swap"]["relevance"] is None

    with pytest.raises(qa.QaError, match="non-author"):
        qa.sign_relevance(
            root,
            TARGET,
            "variant-related",
            text="mine",
            signer="proposer",
            date="2026-09-12T00:00:00Z",
        )
    with pytest.raises(qa.QaError, match="only a variant labelled"):
        qa.sign_relevance(
            root, TARGET, "tutorial-and-swap", text="x", signer="mike", date="2026-09-12T00:00:00Z"
        )
    qa.sign_relevance(
        root,
        TARGET,
        "variant-related",
        text="A nearby case of the root's swap.",
        signer="mike",
        date="2026-09-12T00:00:00Z",
    )
    with pytest.raises(qa.QaError, match="written once"):
        qa.sign_relevance(
            root,
            TARGET,
            "variant-related",
            text="again",
            signer="mike",
            date="2026-09-13T00:00:00Z",
        )
    prod = generate(root)
    doc = json.loads(prod.files[Path(f"targets/{TARGET}/graph.json")])
    assert doc["schema"] == "graph/v3"
    row = next(n for n in doc["nodes"] if n["node_id"] == "variant-related")
    assert row["relevance"] == {"pertinent": True, "signer": "mike", "date": "2026-09-12"}
    # The layout tolerates the file, and the gate knows whose it is.
    assert layout.validate_node(nodes_dir(root) / "variant-related") == []


def test_index_carries_the_qa_state_attempts_and_drift(tmp_path: Path) -> None:
    """F12-R14: per subject the pass state per check; per target the counted attempts and the
    drift flag; a target with no QA record shows every check unrun and the pass incomplete."""
    from opn_gate import qa, watch  # noqa: PLC0415

    root = copy_graph(tmp_path)
    harness.take_in(root)
    target = root / "targets" / F11_TARGET
    row = f11_row(root)
    subject = next(s for s in row["subjects"] if s["subject"] == "root")
    assert subject["qa"]["complete"] is False and subject["qa"]["checks"]["compile"] is None
    assert row["attempts"] == {"counted": 0, "recorded": 0} and row["drift"] is None

    rows = [
        qa.row(
            c,
            "pass",
            tool="t",
            tool_version="0",
            timestamp="2026-09-12T00:00:00Z",
            model="m" if qa.KIND_OF[c] == "brief" else None,
        )
        for c in qa.FLOOR_ROOT
    ]
    qa.write(target, "root", rows, date="2026-09-12T00:00:00Z", produced_by="t")
    qa.record_attempt(
        target, venue="sweep", system="Aristotle", date="2026-09-01", url="https://example.org/a"
    )
    qa.record_attempt(
        target,
        venue="sweep",
        system="Nexus",
        date="2026-09-02",
        url="https://example.org/b",
        statement_hash="0" * 64,
    )
    watch.write_drift(
        target,
        watch.DriftRecord(
            kind="upstream-edit",
            state="flagged",
            statement_hash=qa.subject_hash(target, "root"),
            date="2026-09-12T04:00:00Z",
            author="opn-watcher",
            upstream={
                "repo": "o/r",
                "path": "P.lean",
                "pinned_commit": "a" * 40,
                "head_commit": "b" * 40,
            },
            diff="--- a\n+++ b\n",
        ),
    )
    row = f11_row(root)
    subject = next(s for s in row["subjects"] if s["subject"] == "root")
    assert subject["qa"]["complete"] is True and subject["qa"]["checks"]["brief"] == "pass"
    assert subject["qa"]["checks"]["equivalence"] is None
    assert row["attempts"] == {"counted": 1, "recorded": 2}
    assert row["drift"]["kind"] == "upstream-edit" and row["drift"]["frozen"] is True
    assert row["claimable"] is False and "upstream-drift" in row["not_claimable"]
    assert (
        schemas.violations(
            json.loads(generate(root).files[Path("targets/index.json")]), "targets-index/v4"
        )
        == []
    )
