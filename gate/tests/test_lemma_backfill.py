"""F08-T41 (D-12 v3.38): ``opn-gate lemmas-backfill`` writes the lemma edges of merges made
before the rule.

The live record has a merged partial whose hole restated a node under another branch and whose
parent carries no edge for it (erdos-1094, graph #479). The same steps that judged the partial
(1, 2 and 4) are run again and the edge the writer records today is written: ``META.yaml``'s
``lemmas`` and the regenerated ``Context.lean``. Fast tier over the fake toolchain, which answers
the extraction with the restatement it is told; a Mathlib target runs this in the sandbox.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import samples
import yaml
from fakes import FakeToolchain, artifact_result
from harness import TARGET, declared
from test_finding_lemma_edge import (
    X_SIGNATURE,
    X_TYPE,
    X,
    context_of,
    meta_of,
    nodes_dir,
    with_cross_branch_node,
)
from test_finding_parent_stays_open import H1
from test_postmerge import PARENT
from test_products import MERGE, statement_hash

from opn_gate import cli, config, layout, lemma_backfill, schemas
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext

ROOT_TYPE = "∀ (p q r : Prop), (p ∧ q) ∧ r → r ∧ q ∧ p"
OLD_PARTIAL = "attempts/20261009T120000Z-carol-partial.lean"


def old_merge(root: Path, *, n: int = 3, holes: list[str] | None = None) -> None:
    """A partial merged under a pin before v3.38: the assembly under ``attempts/`` (the
    statement's header with a hole), its passing attestation naming the file and the hole, and
    no edge on the parent for what the hole restated."""
    parent = nodes_dir(root) / PARENT
    head, _, _ = (parent / "Statement.lean").read_text("utf-8").partition(":= by\n  sorry")
    body = (
        f"  intro p q r h\n  have borrowed : {X_TYPE} := sorry\n"
        "  exact ⟨h.2, borrowed p q r h, h.1.1⟩\n"
    )
    # F29-R5: a partial on the record declares its words; the fixture's does too (step 4).
    (parent / OLD_PARTIAL).write_text(head + ":= by\n" + declared(body), encoding="utf-8")
    steps = [
        {"step": 1, "name": "toolchain", "result": "pass", "diagnostic": None},
        {
            "step": 2,
            "name": "paths",
            "result": "pass",
            "diagnostic": {
                "code": "partial-submission",
                "message": f"a partial proof: {OLD_PARTIAL} (D-12 #5)",
                "details": {"path": OLD_PARTIAL},
            },
        },
        {
            "step": 4,
            "name": "kernel-replay",
            "result": "pass",
            "diagnostic": {
                "code": "artifact-partial",
                "message": "partial",
                "details": {"holes": holes or ["borrowed"], "kind": "partial"},
            },
        },
    ]
    doc = samples.attestation(
        node_id=PARENT,
        statement_hash=statement_hash(root, PARENT),
        merge_commit=MERGE,
        artifact_hash=None,
        steps=steps,
    )
    (root / "attestations" / f"{n:06d}.json").write_bytes(schemas.canonical_json(doc))


def reporting(sibling: str | None) -> FakeToolchain:
    """The extractor's answer for the old partial: ``borrowed`` restates ``sibling``."""
    report = artifact_result(
        decl="OpnProp.and_swap_reassoc",
        expected=ROOT_TYPE,
        holes=[("borrowed", X_TYPE, False)],
    )
    report.doc["holes"][0]["defeq_sibling"] = sibling
    return FakeToolchain(artifact=report)


class Factory:
    """One copied tree per run, as the CLI exports one per partial; remembers each run."""

    def __init__(self, tree: Path, toolchain: FakeToolchain) -> None:
        self.tree, self.toolchain = tree, toolchain
        self.runs: list[RunContext] = []

    def __call__(self, node_id: str, out: Path) -> RunContext:
        run_tree = out / "tree"
        shutil.copytree(self.tree, run_tree)
        spec_path = layout.gate_spec_path(run_tree, TARGET)
        ctx = RunContext(
            graph_root=run_tree,
            claim=Claim(TARGET, node_id),
            spec=schemas.load_json(spec_path, "gate-spec/v1"),
            gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
            changes=None,
            workdir=out / "work",
            toolchain=self.toolchain,
            settings=config.load({}),
        )
        self.runs.append(ctx)
        return ctx


def test_the_backfill_writes_the_missing_edge_and_is_idempotent(tmp_path: Path) -> None:
    root = with_cross_branch_node(tmp_path / "g")
    old_merge(root)
    assert "lemmas" not in meta_of(root), "guard: the pre-v3.38 record"
    factory = Factory(root, reporting(X))
    report = lemma_backfill.backfill(root, TARGET, factory, tmp_path / "w")
    assert report.as_dict() == {
        "written": [{"node": PARENT, "hole": "borrowed", "lemma": X}],
        "unchanged": [],
        "failed": [],
    }
    assert meta_of(root)["lemmas"] == [{"hole": "borrowed", "node": X}]
    assert meta_of(root)["schema"] == "meta/v6"
    assert X_SIGNATURE in context_of(root)
    # Each run read the partial as the submission it was, over a tree of its own.
    [*_, run] = factory.runs
    assert run.changes == [Change("A", f"targets/{TARGET}/nodes/{PARENT}/{OLD_PARTIAL}")]
    assert run.graph_root != root
    # Again: nothing new, nothing rewritten.
    before = (nodes_dir(root) / PARENT / "META.yaml").read_bytes()
    again = lemma_backfill.backfill(root, TARGET, Factory(root, reporting(X)), tmp_path / "w2")
    assert again.as_dict() == {
        "written": [],
        "unchanged": [{"node": PARENT, "hole": "borrowed", "lemma": X}],
        "failed": [],
    }
    assert (nodes_dir(root) / PARENT / "META.yaml").read_bytes() == before


def test_a_hole_that_restated_the_parents_own_hole_is_recorded_as_restated(
    tmp_path: Path,
) -> None:
    """An own hole child is an edge already on the record (R22): not a lemma. Since F07-T78 the
    backfill records which own hole it is (``restated``, ``meta/v7``), keyed by the partial, so
    a route merged before the rule (erdos-68 #1154) stops reading as no node; run twice, the
    second run writes nothing. The Context is untouched: no signature is added."""
    root = with_cross_branch_node(tmp_path / "g")
    old_merge(root)
    context_before = context_of(root)
    report = lemma_backfill.backfill(root, TARGET, Factory(root, reporting(H1)), tmp_path / "w")
    assert report.as_dict() == {
        "written": [],
        "unchanged": [],
        "failed": [],
        "restated": [{"node": PARENT, "partial": OLD_PARTIAL, "hole": "borrowed", "own": H1}],
    }
    assert "lemmas" not in meta_of(root)
    assert meta_of(root)["restated"] == [{"partial": OLD_PARTIAL, "hole": "borrowed", "node": H1}]
    assert meta_of(root)["schema"] == "meta/v7"
    assert context_of(root) == context_before
    again = lemma_backfill.backfill(root, TARGET, Factory(root, reporting(H1)), tmp_path / "w2")
    assert again.as_dict() == {"written": [], "unchanged": [], "failed": []}


def test_the_node_s_first_partial_restates_nothing(tmp_path: Path) -> None:
    """F07-T78: a hole of the first partial on a node that names one of the node's own holes is
    that partial's own child, which it wrote; nothing is recorded (``follows_a_partial``)."""
    root = with_cross_branch_node(tmp_path / "g")
    for earlier in (nodes_dir(root) / PARENT / "attempts").glob("*-partial.lean"):
        earlier.unlink()
    old_merge(root)
    before = meta_of(root)
    report = lemma_backfill.backfill(root, TARGET, Factory(root, reporting(H1)), tmp_path / "w")
    assert report.as_dict() == {"written": [], "unchanged": [], "failed": []}
    assert meta_of(root) == before


def test_a_hole_that_restated_nothing_writes_nothing(tmp_path: Path) -> None:
    root = with_cross_branch_node(tmp_path / "g")
    old_merge(root)
    report = lemma_backfill.backfill(root, TARGET, Factory(root, reporting(None)), tmp_path / "w")
    assert report.as_dict() == {"written": [], "unchanged": [], "failed": []}


def test_a_partial_the_steps_no_longer_pass_is_reported_and_writes_nothing(tmp_path: Path) -> None:
    """C7: a failed re-extraction (here the fake's artifact does not elaborate) names the step
    and the code, and the record is untouched."""
    root = with_cross_branch_node(tmp_path / "g")
    old_merge(root)
    fake = reporting(X)
    fake.artifact = artifact_result(
        decl="OpnProp.and_swap_reassoc", expected=ROOT_TYPE, holes=[("borrowed", X_TYPE, True)]
    )  # a hole equal to the goal: step 4 refuses the partial (D-12's offload rule)
    report = lemma_backfill.backfill(root, TARGET, Factory(root, fake), tmp_path / "w")
    assert [f.as_dict() for f in report.failed] == [
        {"node": PARENT, "partial": OLD_PARTIAL, "failure": "step 4: offload-restated-goal"}
    ]
    assert report.written == [] and "lemmas" not in meta_of(root)


def test_a_restated_name_that_is_not_a_node_is_reported_not_written(tmp_path: Path) -> None:
    root = with_cross_branch_node(tmp_path / "g")
    old_merge(root)
    report = lemma_backfill.backfill(
        root, TARGET, Factory(root, reporting("no-such-node")), tmp_path / "w"
    )
    assert report.written == [] and len(report.failed) == 1
    assert "not another node" in report.failed[0].failure
    assert "lemmas" not in meta_of(root)


# --- the command ------------------------------------------------------------------------------


def git(root: Path, *args: str) -> str:
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.org",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.org",
        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        "HOME": str(root),
    }
    done = subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True, env=env
    )
    return done.stdout.strip()


def test_the_command_runs_over_the_checkout_and_prints_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``opn-gate lemmas-backfill --graph <checkout> --target <id>``: the record is read from
    and written into the checkout, each run is made by the sandbox seam (faked here), and the
    report is one JSON line. Exit 0 with nothing failed."""
    root = with_cross_branch_node(tmp_path / "g")
    old_merge(root)
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "the record before v3.38")
    factory = Factory(root, reporting(X))
    seen: list[tuple[str, str]] = []

    def fake_sandboxed_context(graph: Path, commit: str, out: Path, **kw: object) -> RunContext:
        seen.append((str(kw["target"]), str(kw["node"])))
        assert graph == root.resolve() and commit == git(root, "rev-parse", "HEAD")
        return factory(str(kw["node"]), out)

    monkeypatch.setattr(cli, "_sandboxed_context", fake_sandboxed_context)
    code = cli.main(
        ["lemmas-backfill", "--graph", str(root), "--target", TARGET, "--out", str(tmp_path / "o")]
    )
    assert code == 0
    doc = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert doc["target"] == TARGET and doc["commit"] == git(root, "rev-parse", "HEAD")
    assert doc["written"] == [{"node": PARENT, "hole": "borrowed", "lemma": X}]
    assert doc["unchanged"] == [] and doc["failed"] == []
    assert seen == [(TARGET, PARENT)]
    assert meta_of(root)["lemmas"] == [{"hole": "borrowed", "node": X}]
    assert [line.strip() for line in git(root, "status", "--porcelain").splitlines()] == [
        f"M targets/{TARGET}/nodes/{PARENT}/Context.lean",
        f"M targets/{TARGET}/nodes/{PARENT}/META.yaml",
    ]


def test_the_parser_knows_the_command() -> None:
    args = cli.build_parser().parse_args(["lemmas-backfill", "--graph", "g", "--target", "t"])
    assert args.command == "lemmas-backfill" and args.target == "t"
    assert args.image is None and args.no_build is False and args.out is None


def test_a_meta_the_backfill_writes_validates(tmp_path: Path) -> None:
    root = with_cross_branch_node(tmp_path / "g")
    old_merge(root)
    lemma_backfill.backfill(root, TARGET, Factory(root, reporting(X)), tmp_path / "w")
    meta = yaml.safe_load((nodes_dir(root) / PARENT / "META.yaml").read_text("utf-8"))
    schemas.validate(meta, "meta/v6")
