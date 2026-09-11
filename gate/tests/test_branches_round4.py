"""Round four of failing-case coverage: the last unexercised lines in the gate, one failing case
each, named by what it proves (session note 2026-09-10-test-coverage-review.md for rounds one to
three).

Two lines are left alone on purpose, because the code before them makes them unreachable:
``steps/paths_step.py:37`` (``layout.load_node`` already refuses a statement-hash mismatch, so the
second check never sees one), ``modes.py:435`` (``_check_schema`` returns ``_document``'s
diagnostic, so a record that passed the schema always parses again) — both noted here rather
than forced.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from fakes import FAKE_RESOLVED, FakeToolchain
from harness import GRAPH, TARGET, TUTORIAL, copy_graph, make_context

from opn_gate import admit, cli, layout, ledger, modes, paths, sandbox, scaffold, submission
from opn_gate import toolchain as toolchainmod
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change, Located
from opn_gate.steps.deps import statement_signature
from opn_gate.steps.hazards import Acknowledgment, Finding, evaluate

T = f"targets/{TARGET}"
N = f"{T}/nodes/{TUTORIAL}"
CURATOR = "thisisanameforsure"
ROOT = "and-swap-reassoc"
INTERIOR = "and-reassoc"
DATE = "2026-09-10T12:13:14Z"
STAMP = "20260910T121314Z"
RELATION = "theorem relation : True := trivial\n"


def added(*p: str) -> list[Change]:
    return [Change("A", path) for path in p]


def curators(*logins: str) -> modes.Curators:
    return modes.Curators(tuple((f"{login}-pseudonym", login) for login in logins))


def codes(problems: list[Diagnostic]) -> list[str]:
    return [d.code for d in problems]


# --- modes: a file the diff names that the checkout cannot read (F07-R9, R10; F08-R8) -----------


def test_a_status_record_the_checkout_cannot_read_is_reported_not_raised(tmp_path: Path) -> None:
    """A curator record in the diff but absent from the tree is ``append-unreadable`` with the
    OS's reason, rather than an exception out of the check (conventions §5)."""
    root = copy_graph(tmp_path)
    path = f"{N}/status/20260910T000000-c.yaml"
    classification = modes.classify(added(path), author=CURATOR, curators=curators(CURATOR))
    assert classification.mode == "curator"
    problems = modes.check(root, classification)
    assert codes(problems) == ["append-unreadable"]
    assert problems[0].details == {"path": path}
    assert "No such file" in problems[0].message


def test_an_append_the_checkout_cannot_read_is_reported_not_raised(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    path = f"{N}/annex/{'a' * 64}.md"
    classification = modes.classify(added(path))
    assert classification.mode == "append"
    problems = modes.check(root, classification)
    assert codes(problems) == ["append-unreadable"] and problems[0].details["path"] == path


def test_an_explainer_the_checkout_cannot_read_is_reported_after_the_proof_check(
    tmp_path: Path,
) -> None:
    """R10: the proved node passes the merged-proof rule, so the unreadable file is the finding."""
    root = copy_graph(tmp_path)
    path = f"{N}/explainer/{'b' * 64}.md"
    classification = modes.classify(added(path))
    assert classification.mode == "explainer"
    problems = modes.check(root, classification)
    assert codes(problems) == ["append-unreadable"]


def test_an_unreadable_exhibit_record_is_not_scheduled_for_the_sandbox(tmp_path: Path) -> None:
    """F08-R7: a defect claim that ``check`` already reported unreadable carries no exhibit to
    elaborate — the sandbox is never spent on a file that is not there."""
    root = copy_graph(tmp_path)
    classification = modes.classify(added(f"{N}/defects/20260910T000000-alice.yaml"))
    assert classification.mode == "append"
    assert modes.exhibits(root, classification) == []


# --- modes: a defect claim that is not one record (D-16, F08-R7) --------------------------------


def test_a_defect_claim_that_is_a_yaml_list_is_refused_before_its_reference_is_read(
    tmp_path: Path,
) -> None:
    """The file parses, but not as one record object: ``append-invalid`` from the pre-triage,
    and the schema check never runs on a document that is not a mapping."""
    root = copy_graph(tmp_path)
    path = f"{N}/defects/20260910T000000-alice.yaml"
    (root / path).parent.mkdir()
    (root / path).write_text("- stmt_ref: tutorial-and-swap\n- line: 3\n", encoding="utf-8")
    problems = modes.check(root, modes.classify(added(path)))
    assert codes(problems) == ["append-invalid"]
    assert "one record object" in problems[0].message


def test_a_defs_defect_claim_must_reference_a_defs_file(tmp_path: Path) -> None:
    """F08-R7: under ``defs/defects/`` the reference names a ``defs/`` file; a node id there is
    a claim filed in the wrong place, and ``referenced_file`` says so with ``None``."""
    located = Located("defect-claim", f"{T}/defs/defects/20260910T000000-alice.yaml", TARGET, None)
    assert modes.referenced_file(located, TUTORIAL) is None
    assert modes.referenced_file(located, "defs/Basic.lean") == f"{T}/defs/Basic.lean"

    root = copy_graph(tmp_path)
    (root / located.path).parent.mkdir(parents=True)
    (root / located.path).write_text(
        yaml.safe_dump(samples.defect_claim(stmt_ref=TUTORIAL), sort_keys=True), encoding="utf-8"
    )
    problems = modes.check(root, modes.classify(added(located.path)))
    assert codes(problems) == ["defect-ref"]
    assert "defs/defects/ names a defs/ file" in problems[0].message


def test_only_the_two_exhibit_roles_carry_an_exhibit() -> None:
    """F08-R6, R7: an ``exhibit`` field on any other record is prose, never Lean to elaborate."""
    assert modes.exhibit_of("annex", {"exhibit": "example : True := trivial"}) is None
    assert modes.exhibit_of("postmortem", {"evidence": {"exhibit": "x"}}) is None
    assert modes.exhibit_of("defect-claim", {"exhibit": "   "}) is None


def test_a_role_without_a_published_schema_has_nothing_to_validate() -> None:
    """``_check_schema`` is the one place a role's schema is looked up; an explainer has none
    (D-3: prose named for its content), so the answer is no problems, not a lookup error. No
    public check reaches this arm today — every append and curator role is in the table — so the
    guard is driven directly."""
    located = Located("explainer", f"{N}/explainer/{'c' * 64}.md", TARGET, TUTORIAL)
    assert modes._check_schema(located, b"not even yaml: [") == []


# --- cli: classify with a curators.json that is not JSON (F08-R8) -------------------------------


def test_classify_with_a_malformed_curators_file_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The role list is the founder's file, checked at the boundary: unreadable JSON is exit 2
    naming the file, never a classification that silently has no curators."""
    root = copy_graph(tmp_path)
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

    (root / modes.CURATORS_FILE).write_text("{not json\n")
    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")
    record = root / N / "status" / "20260910T000000-c.yaml"
    record.parent.mkdir()
    record.write_text(yaml.safe_dump(samples.node_status(), sort_keys=True))
    git("add", "-A")
    git("commit", "-q", "-m", "a status record")

    code = cli.main(["classify", "--graph", str(root), "--base", "HEAD~1", "--author", CURATOR])
    captured = capsys.readouterr()
    assert code == cli.EXIT_ERROR and captured.out == ""
    assert modes.CURATORS_FILE in captured.err and "not readable JSON" in captured.err


# --- cli: consolidate's toolchain choice (F08-R10; C9) -------------------------------------------


def curator_args(root: Path, *rest: str) -> list[str]:
    return ["--graph", str(root), "--author", CURATOR, "--date", DATE, *rest]


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, Any], str]:
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    out: dict[str, Any] = json.loads(captured.out) if captured.out.strip() else {}
    return code, out, captured.err


def test_consolidate_sandbox_mounts_only_the_work_directory_and_takes_the_image_it_is_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--sandbox``: the probe runs in the step-3 image with the work directory as the one
    read-write mount (C9); ``--image`` names the tag, and without it the image is ensured from
    the gate-spec's pin."""
    made: list[dict[str, Any]] = []
    fake = FakeToolchain()

    def make_sandbox(image: str, caps: sandbox.Caps, **mounts: Any) -> FakeToolchain:
        made.append({"image": image, "caps": caps, **mounts})
        return fake

    ensured: list[tuple[str, bool]] = []

    def ensure_image(spec: dict[str, Any], *, build: bool) -> str:
        ensured.append((str(spec["lean_toolchain"]), build))
        return f"ensured:{spec['lean_toolchain']}"

    monkeypatch.setattr(sandbox, "SandboxToolchain", make_sandbox)
    monkeypatch.setattr(cli, "ensure_image", ensure_image)

    root = copy_graph(tmp_path)
    out_dir = tmp_path / "o1"
    code, out, err = run(
        capsys,
        "consolidate",
        *curator_args(root, "--out", str(out_dir), "--sandbox", "--image", "given:tag"),
        ROOT,
        INTERIOR,
    )
    assert code == cli.EXIT_PASS and err == "", err
    written = f"{T}/nodes/{INTERIOR}/status/{STAMP}-{CURATOR}.yaml"
    assert out == {"ok": True, "keep": ROOT, "drop": INTERIOR, "written": [written]}
    assert made[-1]["image"] == "given:tag" and ensured == []
    assert made[-1]["read_write"] == [out_dir.resolve() / "work"]
    assert "read_only" not in made[-1]
    assert any(c.startswith("elaborate:") and "Consolidate" in c for c in fake.calls)

    (root / written).unlink()
    pin = str(json.loads((root / T / "gate-spec.json").read_text())["lean_toolchain"])
    code, out, err = run(
        capsys,
        "consolidate",
        *curator_args(root, "--out", str(tmp_path / "o2"), "--sandbox", "--no-build"),
        ROOT,
        INTERIOR,
    )
    assert code == cli.EXIT_PASS and out["ok"] is True
    assert ensured == [(pin, False)] and made[-1]["image"] == f"ensured:{pin}"


def test_consolidate_without_a_local_toolchain_is_a_usage_error_that_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without ``--no-toolchain`` or ``--sandbox`` the probe needs elan; when it is missing the
    answer is exit 2 with the install hint, and no superseded record lands."""

    def missing(_cls: object, _settings: object) -> FakeToolchain:
        raise toolchainmod.ToolchainMissingError(
            f"elan not found; run {toolchainmod.INSTALL_SCRIPT}"
        )

    monkeypatch.setattr(toolchainmod.LocalToolchain, "from_settings", classmethod(missing))
    root = copy_graph(tmp_path)
    before = sorted(p.as_posix() for p in root.rglob("*.yaml"))
    code, out, err = run(
        capsys, "consolidate", *curator_args(root, "--out", str(tmp_path / "o")), ROOT, INTERIOR
    )
    assert code == cli.EXIT_ERROR and out == {} and toolchainmod.INSTALL_SCRIPT in err
    assert sorted(p.as_posix() for p in root.rglob("*.yaml")) == before


# --- paths, deps, submission: the shape fallbacks (F00-R19, F01, F07-R13) -----------------------


def test_a_crlf_statement_against_an_lf_proof_is_reported_at_the_last_line() -> None:
    """R19 is byte-exact, so a Statement.lean with CRLF endings never prefixes an LF Proof.lean;
    no line differs as text, and the divergence is reported at the prefix's last line rather
    than at a line that does not exist."""
    statement = layout.parse_statement("theorem OpnProp.t :\r\n  True := by\r\n  sorry\r\n")
    assert isinstance(statement, layout.Statement)
    d = paths.check_proof_is_statement(statement, "theorem OpnProp.t :\n  True := by\n  trivial\n")
    assert d is not None and d.code == "proof-not-statement"
    assert d.details["line"] == 2
    assert d.details == {"line": 2, "expected": "  True :=", "got": "  True := by"}


def test_a_statement_prefix_without_a_theorem_keyword_signs_as_its_whole_text() -> None:
    """F01: the signature is the ``theorem … :=`` span; a prefix the pattern does not match falls
    back to the whole prefix minus its ``:=``, normalised, rather than an empty signature."""
    st = layout.Statement("t", "", prefix="/-- doc -/\nexample : True :=", suffix="")
    assert statement_signature(st) == "/-- doc -/ example : True"


def test_a_submission_block_that_is_not_json_is_the_same_as_no_block() -> None:
    """R13, C7: a malformed disclosure block declares nothing the gate checks, so it is ignored
    rather than failing a proof over formatting."""
    body = f"```json\n{submission.MARKER}\n{{not json\n```"
    assert submission.extract(body) is None
    assert submission.extract("A hand-opened pull request with no block at all.") is None
    assert submission.model_and_tooling(submission.extract(body)) == submission.UNDECLARED


# --- admit: staging a root that has no Context.lean of its own (F08-R1) -------------------------


def test_stage_context_copies_only_the_files_the_root_has(tmp_path: Path) -> None:
    """The relation check stages the root's Statement and Context; a root directory missing one
    of them stages the other alone and asks the toolchain to compile what is there."""
    fake = FakeToolchain()
    ctx = make_context(tmp_path, toolchain=fake)
    root_dir = tmp_path / "root-node"
    root_dir.mkdir()
    (root_dir / "Statement.lean").write_text("theorem r : True := by\n  sorry\n")
    result = admit.stage_context(ctx, FAKE_RESOLVED, "root-node", root_dir)
    assert result is None
    staged = ctx.workdir / "src" / "Nodes" / "root-node"
    assert sorted(p.name for p in staged.iterdir()) == ["Statement.lean"]
    assert any(c.startswith("elaborate:") for c in fake.calls)


# --- ledger, hazards, scaffold --------------------------------------------------------------------


def test_an_identity_whose_ledger_has_no_entries_is_not_a_contributor(tmp_path: Path) -> None:
    """D-36: a written but empty ledger file earns no row on the contributors page."""
    ledger.write(tmp_path, ledger.load(tmp_path, "carol"))
    assert ledger.ledger_path(tmp_path, "carol").is_file()
    entry = ledger.Entry("proof", TARGET, TUTORIAL, "Proof.lean", "a" * 40, DATE)
    ledger.record(tmp_path, "alice", entry)
    assert sorted(ledger.contributions(tmp_path)) == ["alice"]


def test_one_acknowledgment_covers_every_finding_at_its_location_and_is_used_once() -> None:
    """R4: two findings from the same checker at the same location are both acknowledged by
    the one entry, which is counted as used once, not twice."""
    f1 = Finding("nat-sub", "n - 1", "m1")
    f2 = Finding("nat-sub", "n - 1", "m2")
    ack = Acknowledgment("nat-sub", "n - 1", "why")
    ev = evaluate([f1, f2], [ack])
    assert ev.unacknowledged == () and ev.used == (ack,) and ev.unused == ()


def test_a_variant_with_a_relation_proof_scaffolds_a_labelled_relation_file(tmp_path: Path) -> None:
    """D-30: through ``files`` (the service's path, F07-R2) a ``resolves`` variant's proof lands
    as ``Relation.lean`` under its label; an authored proposal has no such file."""
    nodes = GRAPH / T / "nodes"
    variant = scaffold.Proposal(
        node_id="variant-00000000",
        target_id=TARGET,
        statement="theorem OpnProp.t : True := by\n  sorry\n",
        witness="theorem witness : True := trivial\n",
        author=CURATOR,
        origin="variant",
        relation="resolves",
        relation_proof=RELATION,
    )
    out = scaffold.files(nodes, variant)
    assert out[scaffold.RELATION_FILE] == f"-- relation: resolves\n{RELATION}"
    plain = scaffold.files(
        nodes,
        scaffold.Proposal(
            node_id="spec-00000000",
            target_id=TARGET,
            statement=variant.statement,
            witness=variant.witness,
            author=CURATOR,
        ),
    )
    assert scaffold.RELATION_FILE not in plain
