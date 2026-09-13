"""F12-T8 (finding D3): the gate re-runs what a QA record claims passed with no file to show.

A clean screen and a compile leave no exhibit (F12-Q15), so a typed record and a run one read the
same. Mike's decision of 2026-09-13: when a pull request adds a QA record, the gate re-runs, in
its sandbox toolchain on the statement as it stands at head, every compile and soundness screen
the record says passed without an exhibit, and refuses the pull request naming each row the
re-run does not also pass. Rows with exhibits stay R15's; brief and back-translation rows ask a
model the gate job must not hold a key for (C8), so they are not re-run and the report says so.

Everything here runs through the fake seam (conventions §2); the lean tier runs the same re-run on
the real toolchain (``test_qa_rerun_lean.py``).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from fakes import FakeToolchain
from harness import copy_graph, take_in
from scripted import ScriptedToolchain

from opn_gate import cli, config, layout, modes, qa, qa_rerun, schemas
from opn_gate.paths import Change

TARGET_ID = "euclid-primes"
ROOT_NODE = "and-reassoc"  # the fixture node take_in copies in as euclid-primes' root
CURATOR = "curator"
WHEN = "2026-09-13T10:00:00Z"
DEFS = {"Primes.lean": "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p\n"}
STATEMENT_MODULE = f"Nodes.«{ROOT_NODE}».Statement"
DEFINITION_MODULE = f"{layout.DEFS_PREFIX}.Primes"
SCREEN_MODULES = {
    "screen-statement": f"{qa.SCREEN_NAMESPACE}.ScreenStatement",
    "screen-negation": f"{qa.SCREEN_NAMESPACE}.ScreenNegation",
    "screen-false": f"{qa.SCREEN_NAMESPACE}.ScreenFalse",
}
NOTHING_PROVES = set(SCREEN_MODULES.values())
CLAIMED = ("compile", *qa.SCREENS)


@pytest.fixture
def graph(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path)
    take_in(root, TARGET_ID, defs=DEFS)
    return root


def target_of(graph: Path) -> Path:
    return graph / "targets" / TARGET_ID


def hand_row(check: str, verdict: str = "pass", **overrides: Any) -> dict[str, Any]:
    """A row the way a curator would type it: ``tool: hand``, no exhibit; a brief names a model
    so the reader's coherence rules (F12-Q18) are not what refuses it."""
    brief = qa.KIND_OF[check] == "brief"  # type: ignore[index]
    doc: dict[str, Any] = {
        "check": check,
        "kind": qa.KIND_OF[check],  # type: ignore[index]
        "tool": "hand",
        "tool_version": "hand",
        "model": "m" if brief else None,
        "model_version": "1" if brief else None,
        "verdict": verdict,
        "exhibit": None,
        "exhibit_sha256": None,
        "timestamp": WHEN,
    }
    doc.update(overrides)
    return doc


def floor(subject: str = "root") -> list[dict[str, Any]]:
    return [hand_row(c) for c in qa.floor_for(subject)]


def write_record(
    graph: Path, rows: list[dict[str, Any]], *, subject: str = "root", **pins: Any
) -> str:
    """A schema-valid record committed by hand; answers its path relative to the graph root."""
    target = target_of(graph)
    spec = qa.spec_of(target)
    doc = {
        "schema": qa.SCHEMA,
        "subject": subject,
        "statement_hash": qa.subject_hash(target, subject),
        "lean_toolchain": spec["lean_toolchain"],
        "mathlib_sha": spec.get("mathlib_sha"),
        "date": WHEN,
        "produced_by": "hand",
        "checks": rows,
    }
    doc.update(pins)
    schemas.validate(doc, qa.SCHEMA)
    path = qa.record_path(target, subject)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path.relative_to(graph).as_posix()


class Seamed:
    """The re-run the command wires, over the fake seam: a head copy under ``tmp``, one work
    directory, and a count of how often the gate asked."""

    def __init__(self, graph: Path, tmp: Path, toolchain: Any) -> None:
        self.graph, self.tmp, self.toolchain = graph, tmp, toolchain
        self.asked: list[tuple[str, str]] = []

    def __call__(self, target_id: str, subject: str) -> list[qa.Row]:
        self.asked.append((target_id, subject))
        copy = qa_rerun.head_copy(self.graph, self.tmp / "head")
        ctx = qa_rerun.context(copy, target_id, self.toolchain, self.tmp / "work", config.load({}))
        return qa_rerun.rerun_subject(
            ctx, subject, date=WHEN, attempt_budget_s=60.0, subject_budget_s=300.0
        )


def proves(check: str) -> ScriptedToolchain:
    """A seam on which exactly one screen's attempt proves."""
    return ScriptedToolchain(failing_modules=NOTHING_PROVES - {SCREEN_MODULES[check]})


def clean() -> ScriptedToolchain:
    return ScriptedToolchain(failing_modules=set(NOTHING_PROVES))


def tree(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


# --- what the classifier reports -----------------------------------------------------------------


def test_a_qa_record_pull_request_asks_for_the_rerun(graph: Path) -> None:
    """The classifier's located paths carry the record, and ``records_in`` names it; an append
    that is not a QA record asks for nothing."""
    rel = write_record(graph, floor())
    listed = modes.Curators(((CURATOR, CURATOR),))
    curated = modes.classify([Change("A", rel)], author=CURATOR, curators=listed)
    assert curated.mode == "curator" and qa_rerun.records_in(curated.located) == [rel]

    postmortem = f"targets/{TARGET_ID}/nodes/{ROOT_NODE}/attempts/2026-09-13-alice.yaml"
    appended = modes.classify([Change("A", postmortem)])
    assert appended.mode == "append" and qa_rerun.records_in(appended.located) == []


# --- a record the re-run agrees with is accepted --------------------------------------------------


def test_a_typed_record_whose_passes_the_rerun_reproduces_is_accepted(
    graph: Path, tmp_path: Path
) -> None:
    """The rule checks what a record *claims*, not who typed it: every compile and screen pass
    is re-run once and agrees; the brief rows are named as not re-run, with the reason."""
    rel = write_record(graph, floor())
    rerun = Seamed(graph, tmp_path, clean())
    report = qa_rerun.verify(graph, [rel], rerun)
    assert report.ok, report.problems
    assert [c.check for c in report.checked] == list(CLAIMED)
    assert all(c.agrees and c.rerun for c in report.checked)
    assert [(n.check, n.reason) for n in report.not_rerun] == [
        ("brief", qa_rerun.REASON_MODEL),
        ("backtranslation", qa_rerun.REASON_MODEL),
    ]
    assert rerun.asked == [(TARGET_ID, "root")]


def test_a_record_qa_screen_wrote_is_accepted(graph: Path, tmp_path: Path) -> None:
    """The honest path is unchanged: the record ``qa screen`` itself writes re-runs clean."""
    target = target_of(graph)
    ctx = qa_rerun.context(graph, TARGET_ID, clean(), tmp_path / "curator-work", config.load({}))
    run = qa.screen(ctx, "root", date=WHEN, attempt_budget_s=60.0, subject_budget_s=300.0)
    assert run.clean and run.record is not None
    report = qa_rerun.verify(graph, [run.record], Seamed(graph, tmp_path, clean()))
    assert report.ok and len(report.checked) == len(CLAIMED)
    assert qa.pass_state(target, "root").missing == ("brief", "backtranslation")


# --- a pass the re-run does not reproduce is refused, naming the row ------------------------------


@pytest.mark.parametrize("check", sorted(SCREEN_MODULES))
def test_a_typed_pass_the_rerun_refutes_is_refused_naming_the_row(
    graph: Path, tmp_path: Path, check: str
) -> None:
    """D3: every floor row typed ``pass``; the re-run proves this screen's attempt (the negation,
    False from the hypotheses, or the statement itself), so that row — and only that row — is
    refused, with the record, the check and what the re-run said."""
    rel = write_record(graph, floor())
    report = qa_rerun.verify(graph, [rel], Seamed(graph, tmp_path, proves(check)))
    assert not report.ok
    assert [(d.code, d.details["check"]) for d in report.problems] == [
        (qa_rerun.CODE_DISAGREES, check)
    ]
    problem = report.problems[0]
    assert problem.details["record"] == rel and problem.details["rerun"] == ["fail"]
    assert rel in problem.message and check in problem.message
    assert "recorded pass" in problem.message


def test_a_declared_consequence_that_proves_is_a_disagreement(graph: Path, tmp_path: Path) -> None:
    """A consequence lemma at head is part of the statement's screens: a typed consequence pass
    is refused when the lemma derives."""
    directory = qa.qa_dir(target_of(graph)) / qa.CONSEQUENCES_DIR
    directory.mkdir(parents=True)
    (directory / "Absurd.lean").write_text(
        "theorem OpnQa.C.absurd : ∀ p : Prop, p := by\n  sorry\n", encoding="utf-8"
    )
    rel = write_record(graph, floor())
    report = qa_rerun.verify(graph, [rel], Seamed(graph, tmp_path, clean()))
    assert [d.details["check"] for d in report.problems] == ["screen-consequence"]


def test_a_compile_the_rerun_cannot_reproduce_refuses_every_claimed_row(
    graph: Path, tmp_path: Path
) -> None:
    """Layer 1 fails at head: the compile disagrees, and every screen, now inconclusive, does
    too — one named problem per claimed row."""
    rel = write_record(graph, floor())
    toolchain = ScriptedToolchain(failing_modules={STATEMENT_MODULE, *NOTHING_PROVES})
    report = qa_rerun.verify(graph, [rel], Seamed(graph, tmp_path, toolchain))
    assert [d.details["check"] for d in report.problems] == list(CLAIMED)
    rerun = {d.details["check"]: d.details["rerun"] for d in report.problems}
    assert rerun["compile"] == ["fail"]
    assert all(rerun[s] == ["inconclusive"] for s in qa.SCREENS)


def test_an_inconclusive_rerun_is_refused_never_a_clean_pass(graph: Path, tmp_path: Path) -> None:
    """C7: a re-run that times out is not a pass, so the recorded pass it cannot reproduce is
    refused, naming the timeout."""
    rel = write_record(graph, floor())
    slow = ScriptedToolchain(
        failing_modules=set(NOTHING_PROVES),
        timeout_modules={SCREEN_MODULES["screen-negation"]},
    )
    report = qa_rerun.verify(graph, [rel], Seamed(graph, tmp_path, slow))
    assert [d.details["check"] for d in report.problems] == ["screen-negation"]
    assert report.problems[0].details["rerun"] == ["inconclusive"]
    assert qa.NOTE_TIMEOUT in report.problems[0].message


def test_an_erroring_rerun_is_refused(graph: Path, tmp_path: Path) -> None:
    """C7: the toolchain raises — every claimed row is refused, none passes by default."""
    rel = write_record(graph, floor())
    report = qa_rerun.verify(
        graph, [rel], Seamed(graph, tmp_path, FakeToolchain(raise_on="elaborate"))
    )
    assert [d.details["check"] for d in report.problems] == list(CLAIMED)
    assert all(d.details["rerun"] == ["inconclusive"] for d in report.problems)


def test_a_check_the_rerun_never_ran_is_a_disagreement(graph: Path) -> None:
    """A re-run that returns no row for a claimed check has not reproduced it."""
    rel = write_record(graph, [hand_row("screen-false")])
    report = qa_rerun.verify(graph, [rel], lambda _t, _s: [])
    assert [(d.code, d.details["rerun"]) for d in report.problems] == [
        (qa_rerun.CODE_DISAGREES, [])
    ]
    assert "did not run" in report.problems[0].message


# --- what is not re-run, and says why ----------------------------------------------------------


def never(_target: str, _subject: str) -> list[qa.Row]:
    raise AssertionError("the gate started a re-run it had no pass to check")


def test_rows_with_exhibits_and_rows_without_a_pass_are_not_rerun(graph: Path) -> None:
    """R15 covers a row that names a file; a row that records no pass claims nothing. A record
    of only those starts no toolchain and refuses nothing."""
    target = target_of(graph)
    finding_text = "theorem OpnQa.screen_false : True := trivial\n"
    finding, digest = qa.store_exhibit(target, "root-screen-false-1.lean", finding_text)
    pair, pair_digest = qa.store_exhibit(
        target, "root-equivalence-1.lean", "theorem OpnQa.equiv_forward : True := trivial\n"
    )
    rel = write_record(
        graph,
        [
            hand_row("screen-false", "fail", exhibit=finding, exhibit_sha256=digest),
            hand_row("equivalence", exhibit=pair, exhibit_sha256=pair_digest),
            hand_row("compile", "inconclusive"),
            hand_row("screen-negation", "fail"),
        ],
    )
    report = qa_rerun.verify(graph, [rel], never)
    assert report.ok and report.checked == []
    assert [(n.check, n.reason) for n in report.not_rerun] == [
        ("screen-false", qa_rerun.REASON_EXHIBIT),
        ("equivalence", qa_rerun.REASON_EXHIBIT),
        ("compile", qa_rerun.REASON_NOTHING_CLAIMED),
        ("screen-negation", qa_rerun.REASON_NOTHING_CLAIMED),
    ]


def test_an_equivalence_pass_with_no_file_is_not_rerun_and_says_why(graph: Path) -> None:
    rel = write_record(graph, [hand_row("equivalence")])
    report = qa_rerun.verify(graph, [rel], never)
    assert report.ok and [n.reason for n in report.not_rerun] == [qa_rerun.REASON_EQUIVALENCE]


def test_brief_rows_are_not_rerun_and_the_reason_is_the_missing_key(graph: Path) -> None:
    """C8: the brief and the back-translation ask a model; the gate job holds no key, so they
    are named as not re-run — with or without a file — and nothing starts."""
    target = target_of(graph)
    briefs = qa.qa_dir(target) / qa.BRIEFS_DIR
    briefs.mkdir(parents=True)
    (briefs / "root-brief-1.md").write_text("# brief\n", encoding="utf-8")
    rel_brief = qa.relative(target, briefs / "root-brief-1.md")
    rel = write_record(
        graph,
        [
            hand_row(
                "brief",
                exhibit=rel_brief,
                exhibit_sha256=schemas.content_hash(b"# brief\n"),
            ),
            hand_row("backtranslation"),
        ],
    )
    report = qa_rerun.verify(graph, [rel], never)
    assert report.ok and report.checked == []
    assert [(n.check, n.reason) for n in report.not_rerun] == [
        ("brief", qa_rerun.REASON_MODEL),
        ("backtranslation", qa_rerun.REASON_MODEL),
    ]
    assert "C8" in qa_rerun.REASON_MODEL and "model key" in qa_rerun.REASON_MODEL


# --- definitions, staleness, and the tree ------------------------------------------------------


def test_a_definitions_compile_pass_is_rerun(graph: Path, tmp_path: Path) -> None:
    """A definition's floor is compile, brief and back-translation (F12-Q10): its compile pass
    is re-run by building the definitions through the seam; a screen row on a definition is
    outside its floor and named as such."""
    rows = [*floor("Primes"), hand_row("screen-negation")]
    rel = write_record(graph, rows, subject="Primes")
    good = qa_rerun.verify(graph, [rel], Seamed(graph, tmp_path / "a", clean()))
    assert good.ok and [c.check for c in good.checked] == ["compile"]
    assert (
        "screen-negation",
        qa_rerun.REASON_DEFINITION_SCREEN,
    ) in [(n.check, n.reason) for n in good.not_rerun]

    broken = ScriptedToolchain(failing_modules={DEFINITION_MODULE})
    bad = qa_rerun.verify(graph, [rel], Seamed(graph, tmp_path / "b", broken))
    assert [
        (d.details["subject"], d.details["check"], d.details["rerun"]) for d in bad.problems
    ] == [("Primes", "compile", ["fail"])]


def test_a_definition_compile_that_errors_is_refused(graph: Path, tmp_path: Path) -> None:
    rel = write_record(graph, floor("Primes"), subject="Primes")
    report = qa_rerun.verify(
        graph, [rel], Seamed(graph, tmp_path, FakeToolchain(raise_on="elaborate"))
    )
    assert [d.details["rerun"] for d in report.problems] == [["inconclusive"]]


def test_a_record_for_another_pin_or_statement_is_unverifiable(graph: Path) -> None:
    """R5: a record pinned elsewhere cannot be checked against head, so it is refused as that —
    and no toolchain starts for it."""
    other_pin = write_record(graph, floor(), mathlib_sha="b" * 40)
    other_statement = write_record(graph, floor(), statement_hash="c" * 64)
    report = qa_rerun.verify(graph, [other_pin, other_statement], never)
    assert [(d.code, d.details["record"]) for d in report.problems] == [
        (qa_rerun.CODE_UNVERIFIABLE, other_pin),
        (qa_rerun.CODE_UNVERIFIABLE, other_statement),
    ]


def test_a_path_that_is_not_a_record_in_the_tree_is_unverifiable(graph: Path) -> None:
    missing = f"targets/{TARGET_ID}/qa/root-9.yaml"
    elsewhere = "curators.json"
    report = qa_rerun.verify(graph, [missing, elsewhere], never)
    assert [d.code for d in report.problems] == [qa_rerun.CODE_UNVERIFIABLE] * 2


def test_the_rerun_is_asked_once_per_subject(graph: Path, tmp_path: Path) -> None:
    first = write_record(graph, floor())
    second = write_record(graph, [hand_row("screen-false")])
    rerun = Seamed(graph, tmp_path, clean())
    report = qa_rerun.verify(graph, [first, second], rerun)
    assert report.ok and rerun.asked == [(TARGET_ID, "root")]
    assert len(report.checked) == len(CLAIMED) + 1


def test_the_rerun_writes_nothing_into_the_checkout(graph: Path, tmp_path: Path) -> None:
    """A finding makes ``qa screen`` write a record, an exhibit and a claim: all of it lands in
    the head copy, and the checkout the gate is checking is byte-for-byte what it was."""
    rel = write_record(graph, floor())
    before = tree(graph)
    report = qa_rerun.verify(graph, [rel], Seamed(graph, tmp_path, proves("screen-false")))
    assert not report.ok
    assert tree(graph) == before
    copy = tmp_path / "head" / "targets" / TARGET_ID
    assert (copy / "qa" / "exhibits" / "root-screen-false-1.lean").is_file()
    assert any((copy / "nodes" / ROOT_NODE / "defects").iterdir())


def test_the_report_is_json(graph: Path, tmp_path: Path) -> None:
    rel = write_record(graph, floor())
    report = qa_rerun.verify(graph, [rel], Seamed(graph, tmp_path, proves("screen-negation")))
    doc = json.loads(json.dumps(report.as_dict()))
    assert doc["ok"] is False and doc["records"] == [rel]
    assert {c["check"]: c["agrees"] for c in doc["checked"]}["screen-negation"] is False


# --- through the command, the way the graph's workflow runs it -----------------------------------


class Repo:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.env = {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@x",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@x",
            "PATH": "/usr/bin:/bin",
            "HOME": str(root.parent),
        }

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            env=self.env,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)


@pytest.fixture
def repo(graph: Path) -> Repo:
    (graph / "curators.json").write_text(
        json.dumps({"identities": [{"pseudonym": CURATOR, "github_login": CURATOR}]})
    )
    r = Repo(graph)
    r.git("init", "-q")
    r.commit(f"intake: list {TARGET_ID}")
    return r


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, Any], str]:
    capsys.readouterr()
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, (json.loads(captured.out) if captured.out.strip() else {}), captured.err


def test_classify_asks_the_workflow_for_the_rerun(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """The workflow's switch: ``needs_qa_rerun`` and the records, read with a default so a pin
    that predates them skips the step (F08-Q8's shape)."""
    rel = write_record(repo.root, floor())
    repo.commit("qa: typed")
    code, out, _err = run(
        capsys, "classify", "--graph", str(repo.root), "--base", "HEAD~1", "--author", CURATOR
    )
    assert code == cli.EXIT_PASS and out["mode"] == "curator"
    assert out["needs_qa_rerun"] is True and out["qa_records"] == [rel]
    assert out["needs_gate"] is False and out["needs_exhibits"] is False


def test_qa_rerun_runs_in_the_sandbox_refuses_a_forgery_and_accepts_a_true_record(
    repo: Repo, tmp_path: Path, seam: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """C9: the seam is the step-3 image, the head copy's root read-only and the work directory
    read-write; a pass the re-run refutes is exit 1 naming the row on stderr and in
    ``qa-rerun.json``; the checkout is left clean; the same record on a seam where nothing proves
    is exit 0."""
    rel = write_record(repo.root, floor())
    repo.commit("qa: typed")
    out_dir = tmp_path / "o1"
    seam.fake = proves("screen-negation")
    argv = ["qa-rerun", "--graph", str(repo.root), "--base", "HEAD~1", "--sandbox", "--date", WHEN]
    code, out, err = run(capsys, *argv, "--out", str(out_dir))
    assert code == cli.EXIT_FAIL and out["ok"] is False and out["sandboxed"] is True
    assert [(p["code"], p["details"]["check"]) for p in out["problems"]] == [
        (qa_rerun.CODE_DISAGREES, "screen-negation")
    ]
    assert f"{qa_rerun.CODE_DISAGREES}: {rel}" in err
    assert json.loads((out_dir / "qa-rerun.json").read_text()) == out
    head_root = out_dir / "head" / "targets" / TARGET_ID / "nodes" / ROOT_NODE
    assert seam.made == [
        {
            "image": seam.made[0]["image"],
            "caps": seam.made[0]["caps"],
            "read_only": [head_root.resolve()],
            "read_write": [(out_dir / "work").resolve()],
        }
    ]
    assert ":install=False" in seam.fake.calls[0]  # never installs in the sandbox
    assert repo.git("status", "--porcelain") == ""

    seam.fake = clean()
    code, out, err = run(capsys, *argv, "--out", str(tmp_path / "o2"))
    assert code == cli.EXIT_PASS and out["ok"] is True and err == ""
    assert [c["check"] for c in out["checked"]] == list(CLAIMED)


def test_qa_rerun_starts_no_sandbox_when_nothing_needs_it(
    repo: Repo, tmp_path: Path, seam: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Q15's shape: a record of briefs alone has nothing to re-run, so no image is built."""
    write_record(repo.root, [hand_row("brief"), hand_row("backtranslation")])
    repo.commit("qa: briefs")
    code, out, _err = run(
        capsys,
        "qa-rerun",
        "--graph",
        str(repo.root),
        "--base",
        "HEAD~1",
        "--sandbox",
        "--out",
        str(tmp_path / "o"),
    )
    assert code == cli.EXIT_PASS and out["checked"] == [] and len(out["not_rerun"]) == 2
    assert seam.made == [] and seam.docker_verbs() == []


def test_qa_rerun_refuses_a_diff_that_adds_no_record(
    repo: Repo, tmp_path: Path, seam: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo.root / "README.md").write_text("maintenance\n", encoding="utf-8")
    repo.commit("docs")
    code, out, err = run(
        capsys, "qa-rerun", "--graph", str(repo.root), "--base", "HEAD~1", "--sandbox"
    )
    assert code == cli.EXIT_ERROR and out == {} and "adds no QA record" in err
    assert seam.made == []


def test_qa_rerun_without_the_sandbox_uses_the_local_toolchain(
    repo: Repo, tmp_path: Path, seam: Any, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:  # fmt: skip
    from opn_gate import toolchain  # noqa: PLC0415

    write_record(repo.root, floor())
    repo.commit("qa: typed")
    local = clean()
    monkeypatch.setattr(
        toolchain.LocalToolchain, "from_settings", classmethod(lambda _c, _s: local)
    )
    code, out, _err = run(
        capsys,
        "qa-rerun",
        "--graph",
        str(repo.root),
        "--base",
        "HEAD~1",
        "--install",
        "--out",
        str(tmp_path / "o"),
    )
    assert code == cli.EXIT_PASS and out["sandboxed"] is False and seam.made == []
    assert ":install=True" in local.calls[0]
