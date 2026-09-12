"""F08-T5: the curator's commands (R9, R10, R11, R12; AC13, AC14, AC15, AC16).

Each command writes what a curator pull request carries and decides nothing the products do not
re-derive from the files. So each test runs the command on a copy of the fixture graph, reads the
files it wrote, and — where the criterion says "products reflect it" — regenerates the products
over the result.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import samples
import yaml
from fakes import FakeToolchain
from harness import GRAPH, TARGET, copy_graph

from opn_gate import cli, config, curator, layout, products, records, scaffold, schemas
from opn_gate import graph as graphmod
from opn_gate.paths import Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import ElabResult

ROOT = "and-swap-reassoc"
INTERIOR = "and-reassoc"
TUTORIAL = "tutorial-and-swap"
AUTHOR = "thisisanameforsure"
DATE = "2026-09-10T12:13:14Z"
NOW = datetime(2026, 9, 10, 12, 13, 14, tzinfo=UTC)
NEW_STATEMENT = (
    "import Nodes.«and-reassoc-v2».Context\n\n"
    "/-! Revised: the hypothesis the original lacked (D-8). -/\n\n"
    "theorem OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by\n  sorry\n"
)


def nodes_dir(root: Path) -> Path:
    return layout.graph_nodes_dir(root, TARGET)


def add_dependent(root: Path, node_id: str, dep: str) -> None:
    """Make ``node_id`` depend on ``dep`` (META only: the tests need the edge, not the Lean)."""
    meta_path = nodes_dir(root) / node_id / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["deps"] = [*meta["deps"], dep]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False))


def write_request(root: Path, node_id: str) -> Path:
    path = nodes_dir(root) / node_id / "revisions" / "20260910T000000-alice.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = samples.revision_request(node=node_id, contributor="alice")
    path.write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")
    return path


def latest_status(root: Path, node_id: str) -> records.StatusRecord:
    record = records.load_node_status(nodes_dir(root) / node_id)
    assert record is not None, node_id
    return record


# --- AC13: revise --------------------------------------------------------------------------------


def test_revise_flow(tmp_path: Path) -> None:
    """AC13: N-v2 exists with supersedes N, N is superseded, D1 and D2 are stale with the
    revision as cause, and the products reflect all of it."""
    root = copy_graph(tmp_path)
    add_dependent(root, TUTORIAL, INTERIOR)  # D2; the root is D1 already
    request = write_request(root, INTERIOR)

    revision = curator.revise(
        root, TARGET, INTERIOR, NEW_STATEMENT, request, author=AUTHOR, date=DATE
    )
    assert revision.new_id == f"{INTERIOR}-v2"
    assert set(revision.dependents) == {ROOT, TUTORIAL}
    assert (
        revision.request
        == f"targets/{TARGET}/nodes/{INTERIOR}/revisions/20260910T000000-alice.yaml"
    )

    new_dir = nodes_dir(root) / revision.new_id
    assert layout.validate_node(new_dir) == []
    meta = yaml.safe_load((new_dir / "META.yaml").read_text())
    assert meta["schema"] == "meta/v4"
    assert meta["supersedes"] == INTERIOR
    assert meta["id"] == revision.new_id
    assert schemas.violations(meta) == []
    # The witness and the deps are the old node's, for the curator to adjust (R9).
    assert (new_dir / "Witness.lean").read_text() == (
        nodes_dir(root) / INTERIOR / "Witness.lean"
    ).read_text()
    assert (
        meta["deps"]
        == yaml.safe_load((nodes_dir(root) / INTERIOR / "META.yaml").read_text())["deps"]
    )
    assert (new_dir / "Statement.lean").read_text() == NEW_STATEMENT
    # The old statement is untouched (D-3, D-8).
    assert (nodes_dir(root) / INTERIOR / "Statement.lean").read_text() == (
        GRAPH / "targets" / TARGET / "nodes" / INTERIOR / "Statement.lean"
    ).read_text()

    superseded = latest_status(root, INTERIOR)
    assert superseded.status == "superseded"
    assert superseded.doc["reference"] == revision.new_id
    assert revision.request in superseded.doc["cause"]
    for dependent in (ROOT, TUTORIAL):
        stale = latest_status(root, dependent)
        assert stale.status == "stale"
        assert stale.doc["reference"] == INTERIOR
        assert revision.new_id in stale.doc["cause"] and "D-18" in stale.doc["cause"]
    assert all((root / w).is_file() for w in revision.written)

    # Products reflect it: statuses derived from the records, the revision in the frontier, and
    # the root still the root although the revision is a second sink (F08-Q16).
    prod = products.generate(root, rendered_from=None, commit_time="2026-09-10T12:13:14Z")
    tg = prod.targets[0]
    assert tg.root == ROOT
    assert tg.statuses[INTERIOR] == "superseded"
    assert tg.statuses[ROOT] == "stale" and tg.statuses[TUTORIAL] == "stale"
    assert tg.statuses[revision.new_id] == "ready"
    frontier = json.loads(prod.files[Path("frontier.json")])
    assert [e["node_id"] for e in frontier["entries"]] == [revision.new_id]

    # A second revision is v3, and a request for another node is refused.
    request_again = write_request(root, revision.new_id)
    again = curator.revise(
        root,
        TARGET,
        revision.new_id,
        NEW_STATEMENT.replace("-v2", "-v3"),
        request_again,
        author=AUTHOR,
        date="2026-09-11T00:00:00Z",
    )
    assert again.new_id == f"{INTERIOR}-v3"
    with pytest.raises(curator.CuratorError, match="not 'and-swap-reassoc'"):
        curator.revise(root, TARGET, ROOT, NEW_STATEMENT, request, author=AUTHOR, date=DATE)


def test_revising_the_root_makes_the_revision_the_root(tmp_path: Path) -> None:
    """D-8 on the root itself: the old root is superseded and the new one is the sink left."""
    root = copy_graph(tmp_path)
    request = write_request(root, ROOT)
    statement = (
        f"import Nodes.«{ROOT}-v2».Context\n\n"
        "theorem OpnProp.and_swap_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p) := by\n"
        "  sorry\n"
    )
    revision = curator.revise(root, TARGET, ROOT, statement, request, author=AUTHOR, date=DATE)
    tg = graphmod.load_target(root, TARGET)
    assert tg.root == revision.new_id
    assert tg.statuses[ROOT] == "superseded"


# --- AC14: consolidate -------------------------------------------------------------------------


def test_consolidate_requires_equality(tmp_path: Path) -> None:
    """AC14: different, non-defeq statements are refused; equal hashes give drop a superseded
    record naming keep; defeq statements are accepted through the toolchain."""
    root = copy_graph(tmp_path)
    not_defeq = FakeToolchain(elab=ElabResult(ok=False))
    with pytest.raises(curator.CuratorError, match="not the same statement"):
        curator.consolidate(
            root,
            TARGET,
            ROOT,
            INTERIOR,
            author=AUTHOR,
            date=DATE,
            defeq=defeq_with(root, not_defeq),
        )
    with pytest.raises(curator.CuratorError, match="no toolchain"):
        curator.consolidate(root, TARGET, ROOT, INTERIOR, author=AUTHOR, date=DATE)
    with pytest.raises(curator.CuratorError, match="two different nodes"):
        curator.consolidate(root, TARGET, ROOT, ROOT, author=AUTHOR, date=DATE)
    assert not (nodes_dir(root) / INTERIOR / "status").exists()

    # A byte-identical statement under another id is the duplicate D-29 consolidates.
    duplicate = nodes_dir(root) / "and-reassoc-again"
    duplicate.mkdir()
    for name in ("Statement.lean", "Witness.lean", "Context.lean"):
        (duplicate / name).write_text(
            (nodes_dir(root) / INTERIOR / name)
            .read_text()
            .replace("«and-reassoc»", "«and-reassoc-again»")
        )
    meta = yaml.safe_load((nodes_dir(root) / INTERIOR / "META.yaml").read_text())
    meta["id"] = "and-reassoc-again"
    (duplicate / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False))
    for d in layout.REQUIRED_DIRS:
        (duplicate / d).mkdir()
        (duplicate / d / layout.KEEP_FILE).write_text("")
    kept = layout.load_node(nodes_dir(root) / INTERIOR, TARGET)
    dropped = layout.load_node(duplicate, TARGET)
    assert isinstance(kept, layout.Node) and isinstance(dropped, layout.Node)
    if kept.statement.statement_hash != dropped.statement.statement_hash:
        # The import line names the module, so the bytes differ: that is the defeq path.
        record = curator.consolidate(
            root,
            TARGET,
            INTERIOR,
            "and-reassoc-again",
            author=AUTHOR,
            date=DATE,
            defeq=defeq_with(root, FakeToolchain()),
        )
        how = "definitionally equal"
    else:
        record = curator.consolidate(
            root, TARGET, INTERIOR, "and-reassoc-again", author=AUTHOR, date=DATE
        )
        how = "identical"
    doc = yaml.safe_load(record.read_text())
    assert doc["status"] == "superseded" and doc["reference"] == INTERIOR
    assert how in doc["cause"] and "D-29" in doc["cause"]
    assert schemas.violations(doc, "node-status/v1") == []
    assert (
        record
        == nodes_dir(root) / "and-reassoc-again" / "status" / f"{curator.stamp(DATE)}-{AUTHOR}.yaml"
    )
    assert graphmod.load_target(root, TARGET).statuses["and-reassoc-again"] == "superseded"


def defeq_with(root: Path, toolchain: FakeToolchain) -> curator.Defeq:
    spec_path = layout.gate_spec_path(root, TARGET)
    ctx = RunContext(
        graph_root=root,
        claim=Claim(TARGET, ROOT),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=root.parent / "work",
        toolchain=toolchain,
        settings=config.load({}),
    )
    return lambda kept, dropped: curator.statements_defeq(ctx, kept, dropped)


def test_defeq_probe_is_the_dropped_statement_proved_by_the_kept_one(tmp_path: Path) -> None:
    """R10's "elaborate to definitionally equal types", asked without a new metaprogram: the
    probe is drop's Statement.lean with its sorry replaced by keep's theorem, importing it."""
    root = copy_graph(tmp_path)
    kept = layout.load_node(nodes_dir(root) / ROOT, TARGET)
    dropped = layout.load_node(nodes_dir(root) / INTERIOR, TARGET)
    assert isinstance(kept, layout.Node) and isinstance(dropped, layout.Node)
    assert defeq_with(root, FakeToolchain())(kept, dropped) is True
    probe = (root.parent / "work" / "src" / "Nodes" / INTERIOR / "Consolidate.lean").read_text()
    assert probe.startswith(f"import Nodes.«{ROOT}».Statement\n")
    assert f"theorem {curator.PROBE_NAME}" in probe  # not a redeclaration of what it imports
    assert (
        dropped.statement.decl_name.split(".")[-1] not in probe.split("theorem", 1)[1].split(":")[0]
    )
    assert f":= {kept.statement.decl_name}" in probe.replace(":=\n", ":= ").replace("  ", " ") or (
        kept.statement.decl_name in probe
    )
    assert "sorry" not in probe.split(":=")[-1]


# --- AC15: dormancy ------------------------------------------------------------------------------


def test_dormancy_condition(tmp_path: Path) -> None:
    """AC15: a merge 10 days ago with N = 90 is refused citing D-33 (a); no merge in 100 days
    yields a record naming the series values, K and N."""
    root = copy_graph(tmp_path)
    recent = NOW - timedelta(days=10)
    with pytest.raises(curator.CuratorError, match=r"D-33 \(a\)") as refused:
        curator.declare_status(
            root,
            TARGET,
            TARGET,
            "dormant",
            "the network has moved on",
            author=AUTHOR,
            date=DATE,
            now=NOW,
            last_merge=recent,
            k=3,
            n_days=90,
        )
    assert "10 days ago" in str(refused.value) and "N=90" in str(refused.value)
    assert not (root / "targets" / TARGET / "status").exists()

    quiet = NOW - timedelta(days=100)
    record = curator.declare_status(
        root,
        TARGET,
        TARGET,
        "dormant",
        "the network has moved on",
        author=AUTHOR,
        date=DATE,
        now=NOW,
        last_merge=quiet,
        k=3,
        n_days=90,
    )
    doc = yaml.safe_load(record.read_text())
    # F11-R12: new declarations are written at v2, whose fidelity enum carries D-9
    # v3.12's renamed rung; v1 records already in a graph stay valid (D-34).
    assert doc["schema"] == "target-status/v2" and doc["status"] == "dormant"
    assert schemas.violations(doc, "target-status/v2") == []
    cause = doc["cause"]
    assert cause.startswith("the network has moved on\n")
    assert "D-25 series" in cause and "K=3" in cause and "N=90 days" in cause
    assert "zero-attempt fraction" in cause and "2026-06-02" in cause  # the last merge, named
    assert "ready nodes" in cause
    # F03 consumes it: the target is dormant in the products.
    tg = graphmod.load_target(root, TARGET)
    assert tg.declaration is not None and tg.declaration.status == "dormant"
    assert products.target_facts(tg).status == "dormant"

    # Condition (a)'s other arm: every ready node carries at least K attempts.
    root2 = copy_graph(tmp_path / "attempted")
    tg2 = graphmod.load_target(root2, TARGET)
    for node_id, status in tg2.statuses.items():
        if status == "ready":
            att = nodes_dir(root2) / node_id / "attempts"
            for i in range(3):
                (att / f"2026-09-0{i + 1}-x.yaml").write_text(
                    yaml.safe_dump(samples.postmortem(node=node_id)), encoding="utf-8"
                )
    record = curator.declare_status(
        root2,
        TARGET,
        TARGET,
        "dormant",
        "every ready node is well attempted",
        author=AUTHOR,
        date=DATE,
        now=NOW,
        last_merge=recent,
        k=3,
        n_days=90,
    )
    assert "zero-attempt fraction 0.00" in yaml.safe_load(record.read_text())["cause"]

    # `active` needs no evidence (D-33: reversal is mechanical anyway), and a node is abandoned.
    active = curator.declare_status(
        root,
        TARGET,
        TARGET,
        "active",
        "a merge landed",
        author=AUTHOR,
        date="2026-09-11T00:00:00Z",
        now=NOW,
    )
    assert yaml.safe_load(active.read_text())["status"] == "active"
    abandoned = curator.declare_status(
        root, TARGET, INTERIOR, "abandoned", "dead branch (D-14)", author=AUTHOR, date=DATE, now=NOW
    )
    assert yaml.safe_load(abandoned.read_text())["status"] == "abandoned"
    assert graphmod.load_target(root, TARGET).statuses[INTERIOR] == "abandoned"
    with pytest.raises(curator.CuratorError, match="target status"):
        curator.declare_status(
            root, TARGET, INTERIOR, "dormant", "x", author=AUTHOR, date=DATE, now=NOW
        )
    with pytest.raises(curator.CuratorError, match="node status"):
        curator.declare_status(
            root, TARGET, TARGET, "abandoned", "x", author=AUTHOR, date=DATE, now=NOW
        )
    with pytest.raises(curator.CuratorError, match="cause"):
        curator.declare_status(
            root, TARGET, TARGET, "active", "  ", author=AUTHOR, date=DATE, now=NOW
        )


# --- AC16: missing-library -----------------------------------------------------------------------


def test_missing_library_report(tmp_path: Path) -> None:
    """AC16: four postmortems naming one lemma modulo whitespace and case count as four; the
    report lists it with threshold 3 and creates nothing."""
    root = copy_graph(tmp_path)
    spellings = [
        "uniform bound on partial sums",
        "Uniform  bound on partial sums",
        "UNIFORM BOUND ON PARTIAL SUMS ",
        "uniform bound\ton partial sums",
    ]
    for i, lemma in enumerate(spellings):
        node = INTERIOR if i % 2 else ROOT
        att = nodes_dir(root) / node / "attempts"
        doc = samples.postmortem(
            node=node,
            outcome="blocked",
            failure_class="missing-library",
            artifacts={"missing_lemmas": [lemma, "a rarer lemma"] if i == 0 else [lemma]},
        )
        (att / f"2026-09-0{i + 1}-x.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    # A non-missing-library postmortem naming the lemma does not count; nor does a bad file.
    (nodes_dir(root) / ROOT / "attempts" / "2026-09-09-y.yaml").write_text(
        yaml.safe_dump(
            samples.postmortem(
                node=ROOT,
                failure_class="route-dead-ends",
                artifacts={"missing_lemmas": [spellings[0]]},
            )
        ),
        encoding="utf-8",
    )
    (nodes_dir(root) / ROOT / "attempts" / "2026-09-09-z.yaml").write_text("outcome: [oops\n")

    before = sorted(p.as_posix() for p in root.rglob("*"))
    report = curator.missing_library_report(root, TARGET, threshold=3)
    assert len(report) == 1
    found = report[0].as_dict()
    assert found["lemma"] == "uniform bound on partial sums"
    assert found["count"] == 4
    assert sorted(found["as_written"]) == sorted(spellings)
    assert found["nodes"] == [INTERIOR, ROOT]
    assert sorted(p.as_posix() for p in root.rglob("*")) == before  # nothing created (F08-Q3)
    assert [m.key for m in curator.missing_library_report(root, TARGET, threshold=1)] == [
        "uniform bound on partial sums",
        "a rarer lemma",
    ]
    assert [m.key for m in curator.missing_library_report(root, TARGET, threshold=2)] == [
        "uniform bound on partial sums",
    ]


# --- the commands, through the entry point --------------------------------------------------------


def git_env(tmp_path: Path) -> dict[str, str]:
    return {
        "GIT_AUTHOR_NAME": "curator",
        "GIT_AUTHOR_EMAIL": "c@x",
        "GIT_COMMITTER_NAME": "curator",
        "GIT_COMMITTER_EMAIL": "c@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }


def test_commands_write_and_branch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """R9-R12 as commands: each prints what it wrote, `--branch` commits it on a branch for the
    curator's pull request, a refusal exits 1 with the reason and writes nothing."""
    root = copy_graph(tmp_path)
    env = git_env(tmp_path)
    # `--branch` commits with the identity the environment carries, because the gate does not
    # fabricate one (F08-Q17). A hosted runner has none in ~/.gitconfig, so put it here.
    for name in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
    ):
        monkeypatch.setenv(name, env[name])

    def git(*args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(root), *args], check=True, env=env, capture_output=True, text=True
        )
        return proc.stdout

    request = write_request(root, INTERIOR)  # a merged revision request (F08-R6)
    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")
    statement = tmp_path / "Statement.lean"
    statement.write_text(NEW_STATEMENT)
    code = cli.main(
        [
            "revise",
            "--graph",
            str(root),
            "--author",
            AUTHOR,
            "--date",
            DATE,
            "--branch",
            "curator/revise",
            INTERIOR,
            "--statement",
            str(statement),
            "--request",
            str(request),
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["ok"] and out["revision"] == f"{INTERIOR}-v2"
    assert out["branch"] == "curator/revise" and "gh pr create" in out["next"]
    assert git("rev-parse", "--abbrev-ref", "HEAD").strip() == "curator/revise"
    assert git("status", "--porcelain").strip() == ""  # everything written was committed
    committed = git("show", "--name-only", "--format=", "HEAD").split()
    assert f"targets/{TARGET}/nodes/{INTERIOR}-v2/META.yaml" in committed
    assert any(p.startswith(f"targets/{TARGET}/nodes/{ROOT}/status/") for p in committed)

    code = cli.main(
        [
            "status",
            "--graph",
            str(root),
            "--author",
            AUTHOR,
            "--date",
            DATE,
            TARGET,
            "dormant",
            "--cause",
            "quiet",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 1 and out["ok"] is False and "D-33 (a)" in out["refused"]  # seeded seconds ago
    assert not (root / "targets" / TARGET / "status").exists()

    code = cli.main(["missing-library", "--graph", str(root), "--threshold", "1"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["lemmas"] == [] and out["created"] == []

    code = cli.main(
        [
            "consolidate",
            "--graph",
            str(root),
            "--author",
            AUTHOR,
            "--date",
            DATE,
            "--no-toolchain",
            ROOT,
            INTERIOR,
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 1 and "no toolchain" in out["refused"]


# --- every refusal, and what it leaves behind (R9-R12; C7: nothing) ---------------------------

from scripted import ScriptedToolchain  # noqa: E402


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_revise_refuses_a_node_that_is_not_one(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    request = write_request(root, INTERIOR)
    before = tree(root)
    with pytest.raises(curator.CuratorError, match="ghost is not a node of propositional"):
        curator.revise(root, TARGET, "ghost", NEW_STATEMENT, request, author=AUTHOR, date=DATE)
    assert tree(root) == before

    meta = nodes_dir(root) / INTERIOR / "META.yaml"
    meta.write_text(meta.read_text().replace("id: and-reassoc", "id: other"))
    request = write_request(root, INTERIOR)
    before = tree(root)
    with pytest.raises(curator.CuratorError, match="not a valid node: META id"):
        curator.revise(root, TARGET, INTERIOR, NEW_STATEMENT, request, author=AUTHOR, date=DATE)
    assert tree(root) == before


def test_revise_refuses_a_malformed_request_before_writing(tmp_path: Path) -> None:
    """R9 revises on a merged revision request; a file that is not one is a boundary failure."""
    root = copy_graph(tmp_path)
    request = write_request(root, INTERIOR)
    request.write_text(
        yaml.safe_dump(samples.revision_request(node=INTERIOR, defect_class="weaker")),
        encoding="utf-8",
    )
    before = tree(root)
    with pytest.raises(schemas.SchemaError):
        curator.revise(root, TARGET, INTERIOR, NEW_STATEMENT, request, author=AUTHOR, date=DATE)
    assert tree(root) == before
    with pytest.raises(schemas.SchemaError):
        curator.revise(
            root, TARGET, INTERIOR, NEW_STATEMENT, root / "nowhere.yaml", author=AUTHOR, date=DATE
        )
    assert tree(root) == before


def test_revise_refuses_a_statement_that_is_not_a_statement(tmp_path: Path) -> None:
    """The revision is scaffolded like any node: a proof, or two theorems, is not a statement,
    and the refusal comes before the old node's status record is written."""
    root = copy_graph(tmp_path)
    request = write_request(root, INTERIOR)
    before = tree(root)
    with pytest.raises(scaffold.ScaffoldError, match="single sorry-bodied theorem"):
        curator.revise(
            root,
            TARGET,
            INTERIOR,
            NEW_STATEMENT.replace("by\n  sorry", "fun p q r h => ⟨h.1.1, h.1.2, h.2⟩"),
            request,
            author=AUTHOR,
            date=DATE,
        )
    assert tree(root) == before
    assert not (nodes_dir(root) / f"{INTERIOR}-v2").exists()


def test_revise_refused_at_the_status_record_leaves_no_directory(tmp_path: Path) -> None:
    """C7, F08-Q18: every record's path is checked free before the directory is scaffolded, so
    a superseded record whose name is taken (same author, same second) refuses with nothing on
    disk — not with <node>-v<n>/ already written."""
    root = copy_graph(tmp_path)
    request = write_request(root, INTERIOR)
    curator.revise(root, TARGET, INTERIOR, NEW_STATEMENT, request, author=AUTHOR, date=DATE)
    before = tree(root)
    with pytest.raises(curator.CuratorError, match="append-only"):
        curator.revise(
            root,
            TARGET,
            INTERIOR,
            NEW_STATEMENT.replace("-v2", "-v3"),
            request,
            author=AUTHOR,
            date=DATE,
        )
    assert tree(root) == before


def test_version_ids() -> None:
    """Q16: the unversioned node is v1; the next free version is one past the highest taken."""
    assert curator.base_id("and-reassoc-v2") == "and-reassoc"
    assert curator.base_id("and-reassoc") == "and-reassoc"
    assert curator.base_id("and-reassoc-var") == "and-reassoc-var"  # not a version
    assert curator.version_of("and-reassoc-v7") == 7
    assert curator.version_of("and-reassoc") == 1
    assert curator.version_of("and-reassoc-v0") == 1  # v0 is not a version the grammar has


def test_next_version_skips_every_taken_version(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    for taken in ("and-reassoc-v2", "and-reassoc-v7", "and-reassoc-vx"):
        (nodes_dir(root) / taken).mkdir()
    assert curator.next_version_id(nodes_dir(root), INTERIOR) == "and-reassoc-v8"
    assert curator.next_version_id(nodes_dir(root), "and-reassoc-v2") == "and-reassoc-v8"
    assert curator.next_version_id(nodes_dir(root), ROOT) == f"{ROOT}-v2"


def test_consolidate_refuses_unknown_nodes(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    before = tree(root)
    with pytest.raises(curator.CuratorError, match="ghost is not a node"):
        curator.consolidate(root, TARGET, "ghost", INTERIOR, author=AUTHOR, date=DATE)
    with pytest.raises(curator.CuratorError, match="ghost is not a node"):
        curator.consolidate(root, TARGET, INTERIOR, "ghost", author=AUTHOR, date=DATE)
    assert tree(root) == before


def test_consolidate_treats_a_toolchain_that_cannot_answer_as_not_defeq(tmp_path: Path) -> None:
    """A missing toolchain, or one that exceeds the cap, proves no equality; the refusal names
    the reason and nothing is written."""
    root = copy_graph(tmp_path)
    before = tree(root)
    for toolchain in (
        FakeToolchain(missing=True),
        ScriptedToolchain(timeout_modules={f"Nodes.«{ROOT}».Context"}),
        ScriptedToolchain(timeout_modules={f"Nodes.«{ROOT}».Statement"}),
        ScriptedToolchain(timeout_modules={f"Nodes.«{INTERIOR}».Consolidate"}),
    ):
        with pytest.raises(curator.CuratorError, match="do not elaborate to definitionally"):
            curator.consolidate(
                root,
                TARGET,
                ROOT,
                INTERIOR,
                author=AUTHOR,
                date=DATE,
                defeq=defeq_with(root, toolchain),
            )
    assert tree(root) == before


def test_consolidate_refuses_to_record_twice(tmp_path: Path) -> None:
    """Status records are append-only: the same consolidation in the same second by the same
    curator is a collision, and the first record stands."""
    root = copy_graph(tmp_path)
    duplicate = nodes_dir(root) / "and-reassoc-again"
    shutil.copytree(nodes_dir(root) / INTERIOR, duplicate)
    for name in ("Statement.lean", "Witness.lean", "Context.lean"):
        text = (duplicate / name).read_text().replace("«and-reassoc»", "«and-reassoc-again»")
        (duplicate / name).write_text(text)
    meta = yaml.safe_load((duplicate / "META.yaml").read_text())
    meta["id"] = "and-reassoc-again"
    (duplicate / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False))
    first = curator.consolidate(
        root,
        TARGET,
        INTERIOR,
        "and-reassoc-again",
        author=AUTHOR,
        date=DATE,
        defeq=defeq_with(root, FakeToolchain()),
    )
    written = first.read_bytes()
    with pytest.raises(curator.CuratorError, match="append-only"):
        curator.consolidate(
            root,
            TARGET,
            INTERIOR,
            "and-reassoc-again",
            author=AUTHOR,
            date=DATE,
            defeq=defeq_with(root, FakeToolchain()),
        )
    assert first.read_bytes() == written


def test_status_refuses_an_unknown_node_and_a_duplicate_record(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    with pytest.raises(curator.CuratorError, match="ghost is not a node"):
        curator.declare_status(
            root, TARGET, "ghost", "abandoned", "dead", author=AUTHOR, date=DATE, now=NOW
        )
    first = curator.declare_status(
        root, TARGET, INTERIOR, "abandoned", "dead branch", author=AUTHOR, date=DATE, now=NOW
    )
    written = first.read_bytes()
    with pytest.raises(curator.CuratorError, match="append-only"):
        curator.declare_status(
            root, TARGET, INTERIOR, "abandoned", "dead again", author=AUTHOR, date=DATE, now=NOW
        )
    assert first.read_bytes() == written
    assert len(list((nodes_dir(root) / INTERIOR / "status").iterdir())) == 1
    # Another author, or another second, is another record — and the latest wins.
    curator.declare_status(
        root,
        TARGET,
        INTERIOR,
        "abandoned",
        "still dead",
        author="other",
        date="2026-09-10T12:13:15Z",
        now=NOW,
    )
    assert latest_status(root, INTERIOR).author == "other"


def test_status_refuses_a_status_neither_side_has(tmp_path: Path) -> None:
    """Only D-14's abandoned for a node; only D-33's dormant and active for a target."""
    root = copy_graph(tmp_path)
    for status in ("resurrected", "stale", "superseded", "proved"):
        with pytest.raises(curator.CuratorError, match="a node may be marked abandoned"):
            curator.declare_status(
                root, TARGET, INTERIOR, status, "x", author=AUTHOR, date=DATE, now=NOW
            )
        with pytest.raises(curator.CuratorError, match="a target may be declared dormant, active"):
            curator.declare_status(
                root, TARGET, TARGET, status, "x", author=AUTHOR, date=DATE, now=NOW
            )
    assert not (nodes_dir(root) / INTERIOR / "status").exists()
    assert not (root / "targets" / TARGET / "status").exists()


def test_dormancy_boundaries(tmp_path: Path) -> None:
    """D-33 (a): a merge exactly N days ago still counts as recent; a second older does not;
    a target that never merged is quiet by definition and the record says so."""
    root = copy_graph(tmp_path)

    def declare(last_merge: datetime | None, date: str) -> Path:
        return curator.declare_status(
            root,
            TARGET,
            TARGET,
            "dormant",
            "quiet",
            author=AUTHOR,
            date=date,
            now=NOW,
            last_merge=last_merge,
            k=3,
            n_days=90,
        )

    with pytest.raises(curator.CuratorError, match=r"D-33 \(a\)") as refused:
        declare(NOW - timedelta(days=90), DATE)
    assert "merged 90 days ago" in str(refused.value)
    assert not (root / "targets" / TARGET / "status").exists()

    record = declare(NOW - timedelta(days=90, seconds=1), DATE)
    assert "2026-06-12" in yaml.safe_load(record.read_text())["cause"]

    never = declare(None, "2026-09-11T00:00:00Z")
    assert "last progress artifact merged never" in yaml.safe_load(never.read_text())["cause"]


def test_dormancy_on_a_defective_graph_is_a_graph_error(tmp_path: Path) -> None:
    """The series is computed from the derived statuses, so a graph F03 refuses is refused here
    too, and no record is written over it."""
    root = copy_graph(tmp_path)
    meta_path = nodes_dir(root) / INTERIOR / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["deps"] = [ROOT]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False))
    with pytest.raises(graphmod.GraphError, match="cycle"):
        curator.declare_status(
            root, TARGET, TARGET, "dormant", "quiet", author=AUTHOR, date=DATE, now=NOW
        )
    assert not (root / "targets" / TARGET / "status").exists()


def test_missing_library_ignores_what_names_no_lemma(tmp_path: Path) -> None:
    """A missing-library postmortem with no artifacts, an empty list, or blank strings names
    nothing; a threshold above every count reports nothing; nothing is ever created."""
    root = copy_graph(tmp_path)
    att = nodes_dir(root) / INTERIOR / "attempts"
    shapes = [
        samples.postmortem(node=INTERIOR, failure_class="missing-library", artifacts={}),
        samples.postmortem(
            node=INTERIOR, failure_class="missing-library", artifacts={"missing_lemmas": []}
        ),
        samples.postmortem(
            node=INTERIOR,
            failure_class="missing-library",
            artifacts={"missing_lemmas": ["   ", "\t\n"]},
        ),
        samples.postmortem(
            node=INTERIOR, failure_class="missing-library", artifacts={"missing_lemmas": ["real"]}
        ),
    ]
    for i, doc in enumerate(shapes):
        if doc.get("artifacts") == {}:
            del doc["artifacts"]
        (att / f"2026-09-0{i + 1}-x.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    before = sorted(p.as_posix() for p in root.rglob("*"))
    assert [m.as_dict() for m in curator.missing_library_report(root, TARGET, threshold=1)] == [
        {"lemma": "real", "count": 1, "as_written": ["real"], "nodes": [INTERIOR]}
    ]
    assert curator.missing_library_report(root, TARGET, threshold=2) == []
    assert sorted(p.as_posix() for p in root.rglob("*")) == before
