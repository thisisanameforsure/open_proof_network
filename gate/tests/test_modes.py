"""F07-T1: PR modes, append-mode checks, the annex hash rule, explainers (R3, R9, R10).
F08-T2: the proposal and curator modes (F08-R2, R5, R8).

Covers F07-AC3 (the classification matrix), AC11 (append mode runs schema checks and nothing
else), AC12 (an annex is named for its content) and AC13 (an explainer needs a merged proof); and
F08-AC6 (a proposal is exactly one new node directory), AC7 (a hole's witness is completed in
place, once) and AC12 (a curator record needs a listed author).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from fakes import FakeToolchain
from harness import copy_graph

from opn_gate import (
    admit,
    cli,
    config,
    exhibits,
    modes,
    paths,
    postmerge,
    sandbox,
    schemas,
    toolchain,
)
from opn_gate import graph as graphmod
from opn_gate.paths import Change, Claim
from opn_gate.steps import artifact as art
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import ElabResult

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GRAPH = FIXTURES / "graphs" / "propositional"
PROPOSALS = FIXTURES / "proposals"
T = "targets/propositional"
N = f"{T}/nodes/tutorial-and-swap"
UNPROVED = "and-swap-reassoc"  # the root: blocked in the pristine fixture, so it has no Proof.lean
CURATOR = "thisisanameforsure"
OTHER_CURATOR = "second-curator"


def added(*p: str) -> list[Change]:
    return [Change("A", path) for path in p]


def mode_of(*p: str) -> str | None:
    return modes.classify(added(*p)).mode


def curators(*logins: str) -> modes.Curators:
    return modes.Curators(tuple((f"{login}-pseudonym", login) for login in logins))


def write_curators(graph: Path, *logins: str) -> None:
    doc = {
        "identities": [
            {"pseudonym": f"{login}-pseudonym", "github_login": login} for login in logins
        ]
    }
    (graph / modes.CURATORS_FILE).write_text(json.dumps(doc, indent=2) + "\n")


def place_proposal(graph: Path, case: str, node_id: str | None = None) -> list[Change]:
    """Copy a proposal fixture into the graph as a PR would add it; return its changes."""
    node_id = node_id or case
    dest = graph / T / "nodes" / node_id
    shutil.copytree(PROPOSALS / case, dest)
    if node_id != case:  # META's id must be the directory's (F00-R1)
        meta_path = dest / "META.yaml"
        meta_path.write_text(meta_path.read_text().replace(f"id: {case}", f"id: {node_id}"))
    return [
        Change("A", p.relative_to(graph).as_posix()) for p in sorted(dest.rglob("*")) if p.is_file()
    ]


def base_from(pristine: Path) -> modes.BaseReader:
    """A base reader over a directory tree: what a path held before the change."""

    def read(path: str) -> bytes | None:
        p = pristine / path
        return p.read_bytes() if p.is_file() else None

    return read


@pytest.fixture
def graph(tmp_path: Path) -> Path:
    """A writable copy of the propositional fixture; tests add the files a PR would."""
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    return root


def write(graph: Path, path: str, data: bytes | str) -> Change:
    dest = graph / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data.encode() if isinstance(data, str) else data)
    return Change("A", path)


def problems(graph: Path, *changes: Change) -> list[str]:
    classification = modes.classify(changes)
    found = [d.code for d in classification.problems]
    if classification.ok:
        found += [d.code for d in modes.check(graph, classification)]
    return found


# --- AC3: the classification matrix ------------------------------------------------------------


@pytest.mark.parametrize(
    ("paths_touched", "mode"),
    [
        ((f"{N}/Proof.lean",), "proof"),
        ((f"{N}/Proof.lean", f"{N}/attempts/2026-09-10-alice.yaml"), "proof"),
        ((f"{N}/Proof.lean", f"{N}/waivers/native_decide.yaml"), "proof"),
        ((f"{N}/Proof.lean", f"{N}/annex/{'a' * 64}.md"), "proof"),
        ((f"{N}/attempts/2026-09-10-alice-partial.lean",), "partial"),
        (
            (f"{N}/attempts/2026-09-10-alice-partial.lean", f"{N}/attempts/2026-09-10-alice.yaml"),
            "partial",
        ),
        ((f"{N}/attempts/2026-09-10-alice.yaml",), "append"),
        ((f"{N}/attempts/precheck/01m23sfd.json",), "append"),
        ((f"{N}/annex/{'a' * 64}.md",), "append"),
        ((f"{T}/approaches/2026-09-10-alice.yaml",), "append"),
        (
            (f"{N}/attempts/2026-09-10-alice.yaml", f"{T}/approaches/2026-09-10-alice.yaml"),
            "append",
        ),
        ((f"{N}/explainer/{'b' * 64}.md",), "explainer"),
    ],
)
def test_classification_matrix(paths_touched: tuple[str, ...], mode: str) -> None:
    """AC3: each path pattern lands in its mode, and appends ride with a proof or a partial."""
    assert mode_of(*paths_touched) == mode


def test_classification_rejects_mixtures_and_forbidden_paths() -> None:
    """AC3: a PR mixing Proof.lean with an explainer is rejected; so is anything with no mode."""
    mixed = modes.classify(added(f"{N}/Proof.lean", f"{N}/explainer/{'b' * 64}.md"))
    assert mixed.mode is None
    assert [d.code for d in mixed.problems] == ["mode-mixed"]
    assert "explainer" in mixed.problems[0].message

    both_artifacts = modes.classify(
        added(f"{N}/Proof.lean", f"{N}/attempts/2026-09-10-alice-partial.lean")
    )
    assert both_artifacts.mode is None

    for path in (
        f"{T}/defs/Helper.lean",
        f"{T}/gate-spec.json",
        ".github/workflows/evil.yml",
        "curators.json",  # the role file is the founder's, never a submission's (F08 §7)
        f"{N}/attempts/precheck/nested/deep.json",
        f"{N}/annex/notes.txt",
        f"{N}/explainer/why.rst",
        f"{N}/status/nested/record.yaml",
    ):
        rejected = modes.classify(added(path))
        assert rejected.mode is None, path
        assert [d.code for d in rejected.problems] == ["path-forbidden"], path

    # A node's definition is added once and never edited (D-3, D-8): a modification is forbidden
    # at the path, before any mode is considered.
    for path in (
        f"{N}/Statement.lean",
        f"{N}/META.yaml",
        f"{N}/Context.lean",
        f"{N}/Relation.lean",
    ):
        rejected = modes.classify([Change("M", path)])
        assert rejected.mode is None, path
        assert [d.code for d in rejected.problems] == ["path-forbidden"], path


def test_classification_scoping_and_change_status() -> None:
    """One target, one node, and nothing modified or deleted but Proof.lean and its waiver."""
    other = f"{T}/nodes/and-reassoc/attempts/2026-09-10-alice.yaml"
    two_nodes = modes.classify(added(f"{N}/attempts/2026-09-10-alice.yaml", other))
    assert [d.code for d in two_nodes.problems] == ["mode-multi-node"]

    two_targets = modes.classify(added(f"{N}/Proof.lean", "targets/other/nodes/n/Proof.lean"))
    assert [d.code for d in two_targets.problems] == ["mode-multi-target"]

    assert modes.classify([Change("M", f"{N}/Proof.lean")]).mode == "proof"
    for change in (
        Change("D", f"{N}/Proof.lean"),
        Change("M", f"{N}/attempts/2026-09-10-alice.yaml"),
        Change("D", f"{N}/annex/{'a' * 64}.md"),
        Change("R", f"{N}/Proof.lean", f"{N}/Old.lean"),
    ):
        assert modes.classify([change]).mode is None, change

    assert modes.classify([]).problems[0].code == "mode-empty"


def test_only_proof_and_partial_build() -> None:
    """R9, R10: an append or an explainer never starts a sandbox and never waits for a review;
    a proposal (F08-R2) is admitted in the sandbox and reviewed by nobody (D-29)."""
    for mode_paths, builds in (
        ((f"{N}/Proof.lean",), True),
        ((f"{N}/attempts/2026-09-10-alice-partial.lean",), True),
        ((f"{N}/attempts/2026-09-10-alice.yaml",), False),
        ((f"{N}/explainer/{'b' * 64}.md",), False),
    ):
        classification = modes.classify(added(*mode_paths))
        assert classification.needs_gate is builds
        assert classification.needs_review is builds
        assert classification.needs_admission is False

    proposal = modes.classify(
        added(
            *(
                f"{T}/nodes/new/{f}"
                for f in ("META.yaml", "Statement.lean", "Witness.lean", "Context.lean")
            )
        )
    )
    assert proposal.mode == "proposal"
    assert proposal.needs_gate is False
    assert proposal.needs_admission is True
    assert proposal.admit == "new"
    assert proposal.needs_review is False


# --- AC11: append mode is path and schema checks, and nothing else ------------------------------


def test_append_mode_schema_only(graph: Path) -> None:
    """AC11: a valid postmortem passes on schema alone; a bad enum fails naming the field."""
    good = write(
        graph,
        f"{N}/attempts/2026-09-10-alice.yaml",
        yaml.safe_dump(samples.postmortem(), sort_keys=True),
    )
    classification = modes.classify([good])
    assert classification.mode == "append"
    assert modes.check(graph, classification) == []

    bad = write(
        graph,
        f"{N}/attempts/2026-09-10-bob.yaml",
        yaml.safe_dump(samples.postmortem(outcome="gave-up"), sort_keys=True),
    )
    found = modes.check(graph, modes.classify([bad]))
    assert [d.code for d in found] == ["append-invalid"]
    assert "outcome" in found[0].message


def test_append_mode_checks_every_record_kind(graph: Path) -> None:
    """R9: each append validates against its own schema — approach records and precheck records
    included, since they are the two the service does not write for a node."""
    ok = [
        write(
            graph,
            f"{T}/approaches/2026-09-10-alice.yaml",
            yaml.safe_dump(samples.approach_record(), sort_keys=True),
        ),
        write(
            graph,
            f"{N}/attempts/precheck/01m23sfd.json",
            schemas.canonical_json(samples.precheck_record()),
        ),
    ]
    assert problems(graph, *ok) == []

    bad_approach = write(
        graph,
        f"{T}/approaches/2026-09-10-bob.yaml",
        yaml.safe_dump(samples.approach_record(outcome="ran-out"), sort_keys=True),
    )
    assert problems(graph, bad_approach) == ["append-invalid"]

    long_route = write(
        graph,
        f"{T}/approaches/2026-09-10-carol.yaml",
        yaml.safe_dump(samples.approach_record(route="x" * 501), sort_keys=True),
    )
    assert problems(graph, long_route) == ["append-invalid"]

    passing_precheck = write(
        graph,
        f"{N}/attempts/precheck/01m23sfe.json",
        schemas.canonical_json(samples.precheck_record(verdict="pass")),
    )
    assert problems(graph, passing_precheck) == ["append-invalid"]

    unparseable = write(graph, f"{N}/attempts/2026-09-10-dan.yaml", "route: [unclosed\n")
    assert problems(graph, unparseable) == ["append-invalid"]


# --- AC12: an annex is named for its content ----------------------------------------------------


def test_annex_name_is_hash(graph: Path) -> None:
    """AC12: the file name is the SHA-256 of the file, so a citation is mechanical (D-31)."""
    data = samples.annex_file()
    digest = schemas.content_hash(data)
    assert problems(graph, write(graph, f"{N}/annex/{digest}.md", data)) == []

    misnamed = write(graph, f"{N}/annex/{'0' * 64}.md", data)
    found = modes.check(graph, modes.classify([misnamed]))
    assert [d.code for d in found] == ["content-hash-name"]
    assert found[0].details["expected"] == f"{digest}.md"

    edited = samples.annex_file(body="a different argument\n")
    assert problems(graph, write(graph, f"{N}/annex/{digest}.md", edited)) == ["content-hash-name"]


def test_annex_front_matter_and_cap(graph: Path) -> None:
    """R9, D-23: an annex declares its node, contributor and licence, and stays under the cap."""
    no_licence = samples.annex_front_matter()
    del no_licence["licence"]
    head = yaml.safe_dump(no_licence, sort_keys=True)
    unlicensed = f"---\n{head}---\nprose\n".encode()
    assert problems(
        graph, write(graph, f"{N}/annex/{schemas.content_hash(unlicensed)}.md", unlicensed)
    ) == ["append-invalid"]

    bare = b"just prose, no front matter\n"
    assert problems(graph, write(graph, f"{N}/annex/{schemas.content_hash(bare)}.md", bare)) == [
        "append-invalid"
    ]

    body = "x" * (paths.ANNEX_MAX_BYTES + 1)
    huge = samples.annex_file(body=body)
    assert problems(graph, write(graph, f"{N}/annex/{schemas.content_hash(huge)}.md", huge)) == [
        "annex-too-large"
    ]


# --- AC13: explainers ---------------------------------------------------------------------------


def test_explainer_mode(graph: Path) -> None:
    """AC13: an explainer on an unproved node is a misfiled annex; on a proved one it passes
    with no Lean build."""
    data = b"# Why the swap works\n\nBoth conjuncts are already in hand.\n"
    digest = schemas.content_hash(data)

    proved = write(graph, f"{N}/explainer/{digest}.md", data)
    classification = modes.classify([proved])
    assert classification.mode == "explainer"
    assert classification.needs_gate is False
    assert modes.check(graph, classification) == []

    # The fixture ships every node with a proof, so take one away: an unproved node is exactly a
    # node directory with no Proof.lean, which is the only file a proof ever merges (D-3).
    (graph / T / "nodes" / UNPROVED / "Proof.lean").unlink()
    unproved_path = f"{T}/nodes/{UNPROVED}/explainer/{digest}.md"
    found = modes.check(graph, modes.classify([write(graph, unproved_path, data)]))
    assert [d.code for d in found] == ["explainer-unproved"]
    assert "annex" in found[0].message

    misnamed = write(graph, f"{N}/explainer/{'c' * 64}.md", data)
    assert [d.code for d in modes.check(graph, modes.classify([misnamed]))] == ["content-hash-name"]


# --- the schemas T1 adds ------------------------------------------------------------------------


def test_new_schemas_accept_their_samples() -> None:
    for doc in (
        samples.annex_front_matter(),
        samples.approach_record(),
        samples.precheck_record(),
        samples.submission_meta(),
    ):
        schemas.validate(doc)


@pytest.mark.parametrize(
    ("sample", "bad"),
    [
        ("annex_front_matter", {"licence": "MIT"}),
        ("annex_front_matter", {"node": "Bad Id"}),
        ("annex_front_matter", {"extra": 1}),
        ("approach_record", {"outcome": "vibes"}),
        ("approach_record", {"route": ""}),
        ("approach_record", {"pinned_mathlib_sha": "short"}),
        ("approach_record", {"detail": "no such field"}),
        ("precheck_record", {"verdict": "fail"}),
        ("precheck_record", {"first_failing_step": 0}),
        ("precheck_record", {"transcript": "never"}),
        ("submission_meta", {"artifact_type": "sketch"}),
        ("submission_meta", {"identity": {"pseudonym": "a", "proof_kind": "vibes"}}),
        ("submission_meta", {"tooling": {"model": None, "harness": None}}),
        ("submission_meta", {"submission_id": "lowercase"}),
    ],
)
def test_new_schemas_reject(sample: str, bad: dict[str, object]) -> None:
    doc = getattr(samples, sample)(**bad)
    assert schemas.violations(doc)


# --- the command the workflow runs --------------------------------------------------------------


def test_classify_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The entry point gate.yml calls: a mode, whether it needs the sandbox, and every problem.

    Proved against a real diff, because the workflow hands it two commits and not a change list.
    """
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")

    record = yaml.safe_dump(samples.postmortem(), sort_keys=True)
    (root / N / "attempts" / "2026-09-10-alice.yaml").write_text(record)
    git("add", "-A")
    git("commit", "-q", "-m", "postmortem")
    assert cli.main(["classify", "--graph", str(root), "--base", "HEAD~1"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {
        "mode": "append",
        "target": "propositional",
        "node": "tutorial-and-swap",
        "needs_gate": False,
        "needs_admission": False,
        "admit": None,
        "needs_review": False,
        "reviewers": None,
        "review_waived": None,
        "problems": [],
        "ok": True,
        "exhibits": [],
        "needs_exhibits": False,
    }

    (root / N / "attempts" / "2026-09-10-bob.yaml").write_text(
        yaml.safe_dump(samples.postmortem(route_class="vibes"), sort_keys=True)
    )
    git("add", "-A")
    git("commit", "-q", "-m", "bad postmortem")
    assert cli.main(["classify", "--graph", str(root), "--base", "HEAD~1"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert [p["code"] for p in out["problems"]] == ["append-invalid"]

    (root / T / "defs" / "Sneak.lean").write_text("-- not a submission path\n")
    git("add", "-A")
    git("commit", "-q", "-m", "sneak")
    assert cli.main(["classify", "--graph", str(root), "--base", "HEAD~1"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["mode"] is None
    assert [p["code"] for p in out["problems"]] == ["path-forbidden"]


def test_classify_command_curator_and_completion(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """F08-R5, R8 through the entry point: the author reaches the classifier by flag or by
    ``OPN_PR_AUTHOR`` (F08-Q8), curators.json is read from the checkout, and a witness
    completion's precondition is read from the base commit with git."""
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)

    def classify(*extra: str) -> dict[str, Any]:
        code = cli.main(["classify", "--graph", str(root), "--base", "HEAD~1", *extra])
        out: dict[str, Any] = json.loads(capsys.readouterr().out)
        assert (code == 0) is out["ok"]
        return out

    write_curators(root, CURATOR)
    child = make_hole(root)
    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "seed: a curator, and a hole with an empty slot")

    record = root / T / "nodes" / "tutorial-and-swap" / "status" / "20260910T000000-c.yaml"
    record.parent.mkdir()
    record.write_text(yaml.safe_dump(samples.node_status(), sort_keys=True))
    git("add", "-A")
    git("commit", "-q", "-m", "a status record")
    out = classify("--author", CURATOR)
    assert out["mode"] == "curator"
    assert out["needs_review"] is False
    assert out["review_waived"] == "single-curator"
    out = classify("--author", "stranger")
    assert out["mode"] is None
    assert [p["code"] for p in out["problems"]] == ["curator-unlisted"]
    out = classify()  # no author known at all
    assert [p["code"] for p in out["problems"]] == ["curator-unlisted"]
    monkeypatch.setenv("OPN_PR_AUTHOR", CURATOR)
    assert classify()["mode"] == "curator"
    monkeypatch.delenv("OPN_PR_AUTHOR")

    witness = root / T / "nodes" / child / "Witness.lean"
    witness.write_text("theorem witness : True := trivial\n")
    git("add", "-A")
    git("commit", "-q", "-m", "fill the slot")
    out = classify()
    assert out["mode"] == "proposal"
    assert out["admit"] == child
    assert out["needs_admission"] is True
    assert out["problems"] == []

    witness.write_text("theorem witness : True := ⟨⟩\n")
    git("add", "-A")
    git("commit", "-q", "-m", "replace a real witness")
    out = classify()
    assert [p["code"] for p in out["problems"]] == ["witness-filled"]


def test_admit_sandbox_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """F08-R2, C9: ``admit --sandbox`` runs admission through the step-3 image with the gate's
    mounts — the node read-only, the work directory read-write — and never a local toolchain.
    The docker tier drives the real container (test_admit_docker.py)."""
    graph = copy_graph(tmp_path)
    place_proposal(graph, "good")
    node_dir = graph / T / "nodes" / "good"
    seen: dict[str, Any] = {}

    def fake_run(ctx: Any) -> Any:
        seen["toolchain"] = ctx.toolchain
        seen["workdir"] = ctx.workdir
        return admit.Admission(admitted=True, checks=())

    monkeypatch.setattr(admit, "run", fake_run)
    monkeypatch.setattr(cli, "ensure_image", lambda *_a, **_k: "opn-gate:test")
    out = tmp_path / "out"
    code = cli.main(["admit", str(node_dir), "--sandbox", "--out", str(out)])
    assert code == 0
    tc = seen["toolchain"]
    assert isinstance(tc, sandbox.SandboxToolchain)
    assert tc.image == "opn-gate:test"
    assert tc.read_only == [node_dir.resolve()]
    assert tc.read_write == [seen["workdir"].resolve()]
    summary = json.loads((out / "admission.json").read_text())
    assert summary["verdict"] == "pass"
    assert summary["sandboxed"] is True
    assert summary["node"] == "good"

    # Without the flag the local toolchain is used, as pregate does (F08-R1).
    monkeypatch.setattr(
        toolchain.LocalToolchain, "from_settings", classmethod(lambda _c, _s: "local")
    )
    assert cli.main(["admit", str(node_dir), "--out", str(tmp_path / "out2")]) == 0
    assert seen["toolchain"] == "local"
    assert config.load({"OPN_PR_AUTHOR": ""}).pr_author is None


# --- F08-T4: revision requests and defect claims are appends, and their exhibits build ----------


def exhibit_context(graph: Path, *, elab_ok: bool) -> RunContext:
    spec_path = graph / T / "gate-spec.json"
    return RunContext(
        graph_root=graph,
        claim=Claim("propositional", "tutorial-and-swap"),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=graph.parent / "work",
        toolchain=FakeToolchain(elab=ElabResult(ok=elab_ok)),
        settings=config.load({}),
    )


def test_revision_exhibit_elaborates(graph: Path) -> None:
    """F08-AC11: a revision request whose exhibit fails to elaborate fails the append gate
    naming the exhibit; one that elaborates passes; one with no exhibit needs no build."""
    record = write(
        graph,
        f"{N}/revisions/20260910T000000-alice.yaml",
        yaml.safe_dump(samples.revision_request(), sort_keys=True),
    )
    classification = modes.classify([record])
    assert classification.mode == "append"
    assert classification.needs_gate is False
    assert modes.check(graph, classification) == []
    carrying = modes.exhibits(graph, classification)
    assert [loc.path for loc in carrying] == [record.path]

    assert exhibits.run(exhibit_context(graph, elab_ok=True), carrying) == []
    found = exhibits.run(exhibit_context(graph, elab_ok=False), carrying)
    assert [d.code for d in found] == ["exhibit-elaboration"]
    assert found[0].details["path"] == record.path
    assert "tutorial-and-swap" in found[0].details["module"]

    no_exhibit = samples.revision_request()
    del no_exhibit["evidence"]["exhibit"]
    plain = write(
        graph,
        f"{N}/revisions/20260910T000001-alice.yaml",
        yaml.safe_dump(no_exhibit, sort_keys=True),
    )
    assert modes.exhibits(graph, modes.classify([plain])) == []
    assert modes.check(graph, modes.classify([plain])) == []

    bad = write(
        graph,
        f"{N}/revisions/20260910T000002-alice.yaml",
        yaml.safe_dump(samples.revision_request(defect_class="weaker"), sort_keys=True),
    )
    assert problems(graph, bad) == ["append-invalid"]


def test_defect_claim_pretriage_in_the_gate(graph: Path) -> None:
    """F08-R7, D-35: the gate repeats D-16's pre-triage on the landed record — the line must be
    a line of the referenced file, and the reference must be the statement the record sits under."""
    good = write(
        graph,
        f"{N}/defects/20260910T000000-alice.yaml",
        yaml.safe_dump(samples.defect_claim(), sort_keys=True),
    )
    classification = modes.classify([good])
    assert classification.mode == "append"
    assert modes.check(graph, classification) == []
    assert len(modes.exhibits(graph, classification)) == 1

    beyond = write(
        graph,
        f"{N}/defects/20260910T000001-alice.yaml",
        yaml.safe_dump(samples.defect_claim(line=99), sort_keys=True),
    )
    found = modes.check(graph, modes.classify([beyond]))
    assert [d.code for d in found] == ["defect-line"]
    assert found[0].details["lines"] == 4

    elsewhere = write(
        graph,
        f"{N}/defects/20260910T000002-alice.yaml",
        yaml.safe_dump(samples.defect_claim(stmt_ref="and-reassoc"), sort_keys=True),
    )
    assert problems(graph, elsewhere) == ["defect-ref"]

    typo = write(
        graph,
        f"{N}/defects/20260910T000003-alice.yaml",
        yaml.safe_dump(samples.defect_claim(**{"class": "typo"}), sort_keys=True),
    )
    assert problems(graph, typo) == ["record-invalid"]

    # A defs/ claim sits under defs/defects/ and names the defs file, which must exist.
    (graph / T / "defs" / "Helper.lean").write_text("def helper : Nat := 0\n")
    defs_claim = write(
        graph,
        f"{T}/defs/defects/20260910T000000-alice.yaml",
        yaml.safe_dump(samples.defect_claim(stmt_ref="defs/Helper.lean", line=1), sort_keys=True),
    )
    assert problems(graph, defs_claim) == []
    ghost = write(
        graph,
        f"{T}/defs/defects/20260910T000001-alice.yaml",
        yaml.safe_dump(samples.defect_claim(stmt_ref="defs/Ghost.lean", line=1), sort_keys=True),
    )
    assert problems(graph, ghost) == ["defect-ref"]
    # An exhibit about a defs file elaborates as a bare module (F08-Q15).
    carrying = modes.exhibits(graph, modes.classify([defs_claim]))
    assert exhibits.run(exhibit_context(graph, elab_ok=True), carrying) == []


def test_locate_is_the_whole_grammar() -> None:
    """Every role in the mode table comes from one path, and nothing else has a role."""
    roles = {
        f"{N}/Proof.lean": "proof",
        f"{N}/waivers/native_decide.yaml": "waiver",
        f"{N}/attempts/x-partial.lean": "partial",
        f"{N}/attempts/x.yaml": "postmortem",
        f"{N}/attempts/x.yml": "postmortem",
        f"{N}/attempts/precheck/x.json": "precheck-record",
        f"{N}/annex/{'a' * 64}.md": "annex",
        f"{N}/explainer/{'a' * 64}.md": "explainer",
        f"{T}/approaches/x.yaml": "approach-record",
        f"{N}/META.yaml": "node",
        f"{N}/Statement.lean": "node",
        f"{N}/Context.lean": "node",
        f"{N}/Witness.lean": "witness",
        f"{N}/Relation.lean": "relation",
        f"{N}/attempts/.gitkeep": "keep",
        f"{N}/annex/.gitkeep": "keep",
        f"{N}/explainer/.gitkeep": "keep",
        f"{N}/status/20260910T000000-curator.yaml": "node-status",
        f"{T}/status/2026-09-10-dormant.yaml": "target-status",
        f"{N}/revisions/20260910T000000-alice.yaml": "revision-request",
        f"{N}/defects/20260910T000000-alice.yaml": "defect-claim",
        f"{T}/defs/defects/20260910T000000-alice.yaml": "defect-claim",
    }
    target_scoped = {"approach-record", "target-status"}
    for path, role in roles.items():
        located = paths.locate(path)
        assert located is not None and located.role == role, path
        assert located.target_id == "propositional"
        expected_node = None if role in target_scoped or "/defs/" in path else "tutorial-and-swap"
        assert located.node_id == expected_node, path
    for path in (
        "README.md",
        "targets/Bad Target/nodes/n/Proof.lean",
        f"{T}/approaches/nested/x.yaml",
        f"{N}/attempts/",
        f"{N}/waivers/.gitkeep",
        f"{N}/status/.gitkeep",
        f"{N}/notes.md",
        f"{T}/status/nested/x.yaml",
        f"{T}/defs/Helper.lean",
        f"{T}/defs/defects/nested/x.yaml",
        f"{N}/revisions/x.lean",
        f"{T}/nodes/and-swap@2/Statement.lean",
        f"{T}/nodes/and-swap@v0/Statement.lean",
    ):
        assert paths.locate(path) is None, path

    # F08 §6, D-8: a revision is `<id>@v<n>`, and only that spelling is a version.
    versioned = paths.locate(f"{T}/nodes/and-swap-reassoc@v2/Statement.lean")
    assert versioned is not None and versioned.node_id == "and-swap-reassoc@v2"
    assert paths.is_versioned("and-swap-reassoc@v2")
    assert not paths.is_versioned("and-swap-reassoc")


# --- F08-AC6: a proposal is exactly one new node directory ----------------------------------------


def test_proposal_mode_exactly_one_dir(graph: Path) -> None:
    """F08-AC6: one new node directory is a proposal; anything else alongside it is rejected at
    step 2 — an edit to another node, a second directory, or a file outside the graph's grammar."""
    changes = place_proposal(graph, "good")
    assert {c.status for c in changes} == {"A"}
    classification = modes.classify(changes)
    assert classification.mode == "proposal"
    assert classification.admit == "good"
    assert classification.node_id == "good"
    assert classification.needs_admission is True
    assert classification.needs_review is False
    assert modes.check(graph, classification) == []

    # ... plus another node's file, modified or added: rejected before any sandbox (R2).
    other_proof = Change("M", f"{N}/Proof.lean")
    rejected = modes.classify([*changes, other_proof])
    assert rejected.mode is None
    assert [d.code for d in rejected.problems] == ["mode-multi-node"]

    other_append = Change("A", f"{N}/attempts/2026-09-10-alice.yaml")
    rejected = modes.classify([*changes, other_append])
    assert rejected.mode is None
    assert [d.code for d in rejected.problems] == ["mode-multi-node"]

    # Two new directories are two proposals (D-29 admits nodes one at a time).
    second = place_proposal(graph, "good", "good-two")
    rejected = modes.classify([*changes, *second])
    assert [d.code for d in rejected.problems] == ["mode-multi-node"]

    # A proposal that carries a proof, or an append, is not a proposal.
    for extra in (f"{T}/nodes/good/Proof.lean", f"{T}/nodes/good/attempts/2026-09-10-alice.yaml"):
        rejected = modes.classify([*changes, Change("A", extra)])
        assert rejected.mode is None, extra
        assert [d.code for d in rejected.problems] == ["mode-mixed"], extra

    # A proposal touching a file outside targets/ is a path violation, whatever else it adds.
    rejected = modes.classify([*changes, Change("A", "curators.json")])
    assert [d.code for d in rejected.problems] == ["path-forbidden"]


def test_proposal_must_be_a_whole_node(graph: Path) -> None:
    """R2, D-3: a proposal adds the four required files; a partial directory is refused by name."""
    changes = place_proposal(graph, "good")
    without_context = [c for c in changes if not c.path.endswith("Context.lean")]
    classification = modes.classify(without_context)
    assert classification.mode == "proposal"  # the shape is a proposal's; the content is short
    found = modes.check(graph, classification)
    assert [d.code for d in found] == ["proposal-incomplete"]
    assert found[0].details["missing"] == ["Context.lean"]

    # A lone Statement.lean on an existing node is the same refusal, not a silent edit.
    lone = modes.classify(added(f"{N}/Statement.lean"))
    assert lone.mode == "proposal"
    assert [d.code for d in modes.check(graph, lone)] == ["proposal-incomplete"]


def test_proposal_status_record_may_only_be_speculative(graph: Path) -> None:
    """F08-Q2, D-14: the scaffold marks a crux `speculative` with a status record inside the new
    directory; any other status there is a curator's judgment and is refused."""
    changes = place_proposal(graph, "good")
    record = f"{T}/nodes/good/status/20260910T000000-alice.yaml"
    speculative = samples.node_status(
        status="speculative", cause="proposed as a crux (D-14 mechanism 2)", author="alice"
    )
    changes.append(write(graph, record, yaml.safe_dump(speculative, sort_keys=True)))
    classification = modes.classify(changes)
    assert classification.mode == "proposal"
    assert modes.check(graph, classification) == []

    (graph / record).write_text(
        yaml.safe_dump(samples.node_status(status="abandoned", author="alice"), sort_keys=True)
    )
    found = modes.check(graph, modes.classify(changes))
    assert [d.code for d in found] == ["proposal-status"]

    (graph / record).write_text(yaml.safe_dump({"schema": "node-status/v1"}, sort_keys=True))
    found = modes.check(graph, modes.classify(changes))
    assert found and all(d.code == "record-invalid" for d in found)


# --- F08-AC7: a hole's witness is completed in place, once --------------------------------------

HOLES = (
    art.Hole(
        name="right",
        type="r",
        closed_type="∀ (p q r : Prop), (p ∧ q) ∧ r → r",
        defeq_goal=False,
    ),
)
ASSEMBLY = (
    "theorem OpnProp.and_swap_reassoc : True := by\n  have right : True := sorry\n  exact right\n"
)


def make_hole(graph: Path) -> str:
    """A compiler-derived child with an unfilled witness slot, as a merged partial leaves it."""
    parent = graph / T / "nodes" / UNPROVED
    result = postmerge.apply_partial(
        parent, HOLES, partial_text=ASSEMBLY, pseudonym="alice", stamp="20260910T121314Z"
    )
    return result.children[0]


def test_witness_completion(tmp_path: Path) -> None:
    """F08-AC7: adding only Witness.lean to a hole with an unfilled slot is a proposal whose
    admission makes the node ready; the same file on a node that already has a witness is
    rejected, because a witness is immutable once real (D-3)."""
    base = copy_graph(tmp_path / "base")
    child = make_hole(base)
    head = copy_graph(tmp_path / "head")
    make_hole(head)
    witness_path = f"{T}/nodes/{child}/Witness.lean"
    assert graphmod.witness_is_stub(base / T / "nodes" / child)

    (head / witness_path).write_text("theorem witness : True := trivial\n")
    change = Change("M", witness_path)
    classification = modes.classify([change])
    assert classification.mode == "proposal"
    assert classification.admit == child
    assert classification.needs_admission is True
    assert classification.needs_review is False
    assert modes.check(head, classification, base=base_from(base)) == []

    # After the merge the node is ready: F03 derives that from the tree, not from a record.
    facts = graphmod.load_nodes(head, "propositional", [])
    assert facts[child].witness_stub is False
    assert graphmod.derive_statuses(facts)[child] == "ready"

    # The precondition is a fact about the base; without it the check refuses rather than guesses.
    found = modes.check(head, classification, base=None)
    assert [d.code for d in found] == ["witness-completion-unverified"]

    # A hole whose slot was already filled is a ready node, and its witness is never replaced.
    (base / witness_path).write_text("theorem witness : True := ⟨⟩\n")
    found = modes.check(head, classification, base=base_from(base))
    assert [d.code for d in found] == ["witness-filled"]

    # Only a hole has a slot to fill: an authored node's witness was real from admission on
    # (D-29, F07-Q3), so a Witness.lean on the ready tutorial node is not a completion.
    ready = f"{N}/Witness.lean"
    (head / ready).write_text(
        "theorem witness : ∃ p q : Prop, p ∧ q := ⟨True, True, ⟨trivial, trivial⟩⟩\n"
    )
    found = modes.check(head, modes.classify([Change("M", ready)]), base=base_from(base))
    assert [d.code for d in found] == ["witness-not-a-hole"]

    # A Witness.lean for a directory with no META.yaml belongs to nothing.
    orphan = f"{T}/nodes/nobody/Witness.lean"
    (head / T / "nodes" / "nobody").mkdir()
    (head / orphan).write_text("theorem witness : True := trivial\n")
    found = modes.check(head, modes.classify([Change("A", orphan)]), base=base_from(base))
    assert [d.code for d in found] == ["proposal-incomplete"]


# --- F08-AC12: a curator record needs a listed author ------------------------------------------


def test_curator_mode_requires_listing(graph: Path) -> None:
    """F08-AC12: a status record by a listed login is mode curator; by anyone else, rejected."""
    record = write(
        graph,
        f"{N}/status/20260910T000000-curator.yaml",
        yaml.safe_dump(samples.node_status(), sort_keys=True),
    )
    listed = modes.classify([record], author=CURATOR, curators=curators(CURATOR))
    assert listed.mode == "curator"
    assert listed.node_id == "tutorial-and-swap"
    assert listed.needs_gate is False
    assert listed.needs_admission is False
    assert modes.check(graph, listed) == []

    for author, curator_list in (
        ("stranger", curators(CURATOR)),
        (None, curators(CURATOR)),
        (CURATOR, modes.Curators()),  # no curators.json at all
    ):
        rejected = modes.classify([record], author=author, curators=curator_list)
        assert rejected.mode is None, (author, curator_list)
        assert [d.code for d in rejected.problems] == ["curator-unlisted"], author
        assert rejected.problems[0].details["author"] == author

    # A target-level declaration (D-33) is a curator's record too.
    dormancy = write(
        graph,
        f"{T}/status/2026-09-10-dormant.yaml",
        yaml.safe_dump(
            samples.target_status(status="dormant", cause="series: ..."), sort_keys=True
        ),
    )
    assert modes.classify([dormancy], author=CURATOR, curators=curators(CURATOR)).mode == "curator"
    assert modes.classify([dormancy]).problems[0].code == "curator-unlisted"

    # The record still has to be a record.
    bad = write(
        graph,
        f"{N}/status/20260910T000001-curator.yaml",
        yaml.safe_dump(samples.node_status(status="vibes"), sort_keys=True),
    )
    found = modes.check(graph, modes.classify([bad], author=CURATOR, curators=curators(CURATOR)))
    assert [d.code for d in found] == ["record-invalid"]


def test_curator_review_is_a_second_listed_identity_or_waived() -> None:
    """F08-R8, D-21, D-22: a curator PR needs an approval from a *different* listed identity;
    while the founder is the only curator that is waived, and the waiver is on the record."""
    record = added(f"{N}/status/20260910T000000-curator.yaml")
    alone = modes.classify(record, author=CURATOR, curators=curators(CURATOR))
    assert alone.mode == "curator"
    assert alone.reviewers == ()
    assert alone.needs_review is False
    assert alone.review_waived == modes.WAIVER_SINGLE_CURATOR
    assert alone.as_dict()["review_waived"] == "single-curator"

    two = modes.classify(record, author=CURATOR, curators=curators(CURATOR, OTHER_CURATOR))
    assert two.reviewers == (OTHER_CURATOR,)
    assert two.needs_review is True
    assert two.review_waived is None
    assert two.as_dict()["reviewers"] == [OTHER_CURATOR]

    # A proof's reviewer is any non-author (D-4): the field stays open.
    assert modes.classify(added(f"{N}/Proof.lean")).reviewers is None


def test_curator_mode_scope(graph: Path) -> None:
    """R8, D-8: a revision touches several nodes in one PR — a versioned node plus records on the
    old node and its dependents — while a plain new node stays a proposal like anyone else's."""
    listed = curators(CURATOR)
    versioned = place_proposal(graph, "good", "good@v2")
    superseded = Change("A", f"{T}/nodes/{UNPROVED}/status/20260910T000000-curator.yaml")
    stale = Change("A", f"{T}/nodes/and-reassoc/status/20260910T000000-curator.yaml")
    revision = modes.classify([*versioned, superseded, stale], author=CURATOR, curators=listed)
    assert revision.mode == "curator"
    assert revision.admit == "good@v2"
    assert revision.needs_admission is True
    assert revision.node_id == "good@v2"

    # A versioned node alone is still a curator's act, never a proposal.
    assert modes.classify(versioned).problems[0].code == "curator-unlisted"
    assert modes.classify(versioned, author=CURATOR, curators=listed).mode == "curator"

    # A plain new node in a curator PR is a proposal in the wrong pull request (D-29, F08-Q3).
    plain = place_proposal(graph, "good", "good-plain")
    mixed = modes.classify([*plain, superseded], author=CURATOR, curators=listed)
    assert mixed.mode is None
    assert [d.code for d in mixed.problems] == ["mode-mixed"]
    assert "good-plain" in mixed.problems[0].message

    # A status record with a proof, or across two targets, is rejected like any mixture.
    with_proof = modes.classify(
        [superseded, Change("M", f"{N}/Proof.lean")], author=CURATOR, curators=listed
    )
    assert [d.code for d in with_proof.problems] == ["mode-mixed"]
    two_targets = modes.classify(
        [superseded, Change("A", "targets/other/status/2026-09-10-x.yaml")],
        author=CURATOR,
        curators=listed,
    )
    assert [d.code for d in two_targets.problems] == ["mode-multi-target"]


def test_load_curators(graph: Path) -> None:
    """R8: the role file, validated at the boundary; absent means no curators."""
    assert modes.load_curators(graph) == modes.Curators()
    write_curators(graph, CURATOR, OTHER_CURATOR)
    loaded = modes.load_curators(graph)
    assert loaded.logins == {CURATOR, OTHER_CURATOR}
    assert loaded.pseudonym_of(CURATOR) == f"{CURATOR}-pseudonym"
    assert loaded.pseudonym_of("nobody") is None

    for bad in ('{"identities": "x"}', '{"identities": [{"pseudonym": "a"}]}', "[]", "{not json"):
        (graph / modes.CURATORS_FILE).write_text(bad)
        with pytest.raises(modes.CuratorsError):
            modes.load_curators(graph)
