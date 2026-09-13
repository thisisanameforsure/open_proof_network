"""Findings D and E (2026-09-13): two reports from an end-to-end run, each judged against the
decisions and the specs, with the current behaviour captured.

D — a hand-typed ``qa/root-1.yaml`` satisfies the signature gate (F12-R9).
E — ``opn-gate status <target> active`` on a curated target skips activation's refusal (F11-R5).

Each test asserts the behaviour the governing text asks for. The two reader defects were fixed
in F12-T7 (Q18); D3 was closed in F12-T8 where Mike's decision of 2026-09-13 put the rule (the
gate re-runs the screens on the pull request); E was closed in F11-T10. Tests marked **PIN**
capture behaviour judged intended.
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in
from scripted import ScriptedToolchain

from opn_gate import cli, fidelity, intake, modes, products, qa, qa_rerun, schemas
from opn_gate.paths import Change

TARGET_ID = "euclid-primes"
WHEN = "2026-09-12T10:00:00Z"
LATER = "2026-09-13T00:00:00Z"
CURATOR = "thisisanameforsure"


@pytest.fixture
def graph(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path)
    take_in(root)
    return root


def target_of(graph: Path) -> Path:
    return graph / "targets" / TARGET_ID


def hand_row(check: str, **overrides: Any) -> dict[str, Any]:
    """A row the way the end-to-end run typed it: ``tool: hand``, no exhibit, no model."""
    doc: dict[str, Any] = {
        "check": check,
        "kind": qa.KIND_OF[check],  # type: ignore[index]
        "tool": "hand",
        "tool_version": "hand",
        "model": None,
        "model_version": None,
        "verdict": "pass",
        "exhibit": None,
        "exhibit_sha256": None,
        "timestamp": WHEN,
    }
    doc.update(overrides)
    return doc


def write_hand_record(target: Path, rows: list[dict[str, Any]]) -> Path:
    """Commit a hand-typed record that satisfies ``qa/v1`` — the schema is the only check CI
    applies to a ``qa-record`` (``modes._check_schema``)."""
    spec = qa.spec_of(target)
    doc = {
        "schema": qa.SCHEMA,
        "subject": "root",
        "statement_hash": qa.subject_hash(target, "root"),
        "lean_toolchain": spec["lean_toolchain"],
        "mathlib_sha": spec.get("mathlib_sha"),
        "date": WHEN,
        "produced_by": "hand",
        "checks": rows,
    }
    schemas.validate(doc, qa.SCHEMA)  # setup guard: the forgery is schema-valid
    path = qa.record_path(target, "root")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def run_cli(*argv: str) -> tuple[int, dict[str, Any]]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(list(argv))
    text = out.getvalue().strip()
    return code, (json.loads(text) if text else {})


def index_row(graph: Path) -> dict[str, Any]:
    prod = products.generate(graph, rendered_from="5" * 40, commit_time="2026-09-11T00:00:00Z")
    files = {p.as_posix(): json.loads(data) for p, data in prod.files.items()}
    rows = files["targets/index.json"]["targets"]
    return next(r for r in rows if r["target_id"] == TARGET_ID)


# =================================================================================================
# D — the QA record behind a signature
# =================================================================================================


def test_d_reader_holds_a_row_to_the_writers_coherence_rules(graph: Path) -> None:
    """**Fixed in F12-T7.** A ``brief`` or ``backtranslation`` row that passes with no model
    is refused by the writer (``qa.row``: "a brief row records the model that produced it (R6,
    R7)"; "a brief that names no model is a brief nobody ran"), but ``qa.load``/``pass_state``
    read rows through ``Row.from_dict`` and apply none of ``row()``'s rules. The module says "the
    writer is the first reader"; the reader must not be laxer than the writer, or every rule
    the writer enforces is optional for a record committed by hand.

    Expected: the two model-less brief rows do not count, so the pass is incomplete."""
    target = target_of(graph)
    with pytest.raises(qa.QaError, match="records the model"):  # guard: the writer refuses it
        qa.row("brief", "pass", tool="hand", tool_version="hand", timestamp=WHEN)
    write_hand_record(target, [hand_row(c) for c in qa.FLOOR_ROOT])

    state = qa.pass_state(target, "root")
    assert not state.complete, "a model-less brief row counted toward a complete pass"
    assert {"brief", "backtranslation"} <= set(state.missing)


def test_d_a_rows_kind_is_its_checks_not_what_the_record_claims(tmp_path: Path) -> None:
    """**Fixed in F12-T7.** F12-R2: "record every check as exactly one of two kinds and
    permit only ``kind: exhibit`` to be cited as evidence for a fidelity grade; a ``kind: brief``
    result shall never raise a grade on its own" (D-9 v3.12: "Only the first kind may be cited
    as evidence for a grade"). ``qa.KIND_OF`` fixes ``brief`` as a brief, and ``qa.row`` derives
    the kind from the check — but ``qa/v1`` lets any check carry either kind and the reader
    trusts the record's ``kind``. A brief typed as ``kind: exhibit`` lands in
    ``PassState.exhibits`` and ``certificate_citations`` cites it as an exhibit.

    Expected: the mislabelled brief is not cited as an exhibit."""
    graph = copy_graph(tmp_path)
    take_in(graph)
    target = target_of(graph)
    briefs = qa.qa_dir(target) / qa.BRIEFS_DIR
    briefs.mkdir(parents=True)
    (briefs / "root-brief-1.md").write_text("# brief\n", encoding="utf-8")
    rel = qa.relative(target, briefs / "root-brief-1.md")
    rows = [hand_row(c, model="m", model_version="1") for c in qa.FLOOR_ROOT if c != "brief"]
    rows.append(
        hand_row(
            "brief",
            kind="exhibit",
            model="m",
            model_version="1",
            exhibit=rel,
            exhibit_sha256=schemas.content_hash(b"# brief\n"),
        )
    )
    write_hand_record(target, rows)

    state = qa.pass_state(target, "root")
    exhibits, _files = qa.certificate_citations(state)
    assert [e["kind"] for e in exhibits if e["kind"] in ("brief", "backtranslation")] == [], (
        "a brief was cited as a kernel exhibit (R2)"
    )


def test_d_a_hand_typed_pass_is_refused_by_the_gate_on_its_pull_request(
    graph: Path, tmp_path: Path, seam: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """**Fixed in F12-T8, at the pull request — where Mike's decision of 2026-09-13 put it.**

    The report, end to end: every floor row ``verdict: pass``, ``exhibit: null``,
    ``tool: hand`` (brief rows given a model name, so the two defects above are not the cause),
    and ``opn-gate fidelity euclid-primes root screened-and-signed --by reviewer`` exits 0 and
    writes the certificate.

    For refusal: F12 §2 "I want one command per check and a record I cannot forge by hand, so a
    grade is a summary of evidence rather than an opinion I typed"; D-9 v3.12 "each layer
    producing an artifact rather than an opinion" and screened-and-signed is "the mechanizable
    pass above completed with its exhibits recorded"; F12-Q8 names "a hand-committed row" as
    "the forgery the user story rules out". Against: F12-R15 closes the forgery only for rows
    that name a file, and F12-Q15 makes a clean screen a row with ``exhibit: null``.

    **Why the test moved.** This test used to assert that the local ``fidelity`` command refuse
    the typed record. The owner's rule is that CI re-runs the screens on the pull request that
    adds a QA record, and refuses it where a re-run disagrees. The local command runs where the
    curator runs it, so any check there is again the curator's own word; the pull request is
    the one way a record reaches the graph (D-35), and the gate job re-runs the screens inside
    the step-3 sandbox with no secret (C8, C9). So the test drives the path a typed record takes
    to the graph — ``classify`` asks for the re-run, ``qa-rerun --sandbox`` runs it — and asserts
    the refusal names the row the re-run refutes. The local command is deliberately unchanged:
    a record that never merged grades nothing on the graph. The rule verifies what a record
    *claims*, not who typed it, so a typed record whose passes the re-run reproduces is accepted
    (``test_qa_rerun.py``); brief rows are not re-run, because they ask a model (C8)."""
    target = target_of(graph)
    (graph / "curators.json").write_text(
        json.dumps({"identities": [{"pseudonym": CURATOR, "github_login": CURATOR}]})
    )
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t"}
    env |= {"GIT_COMMITTER_EMAIL": "t@x", "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(graph), *args], check=True, env=env, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "intake")
    rows = [
        hand_row(c, **({"model": "m", "model_version": "1"} if qa.KIND_OF[c] == "brief" else {}))
        for c in qa.FLOOR_ROOT
    ]
    rel = write_hand_record(target, rows).relative_to(graph).as_posix()
    git("add", "-A")
    git("commit", "-q", "-m", "qa: typed by hand")

    code, out = run_cli("classify", "--graph", str(graph), "--base", "HEAD~1", "--author", CURATOR)
    assert code == cli.EXIT_PASS and out["mode"] == "curator"
    assert out["needs_qa_rerun"] is True and out["qa_records"] == [rel]

    # The statement's negation proves at head: the typed "screen-negation: pass" is false.
    seam.fake = ScriptedToolchain(
        failing_modules={f"{qa.SCREEN_NAMESPACE}.{s}" for s in ("ScreenStatement", "ScreenFalse")}
    )
    code, out = run_cli(
        "qa-rerun", "--graph", str(graph), "--base", "HEAD~1", "--sandbox", "--date", WHEN,
        "--out", str(tmp_path / "rerun"),
    )  # fmt: skip
    assert code == cli.EXIT_FAIL, f"the gate accepted a typed pass its re-run refutes: {out}"
    assert [(p["code"], p["details"]["check"]) for p in out["problems"]] == [
        (qa_rerun.CODE_DISAGREES, "screen-negation")
    ]
    assert {n["check"]: n["reason"] for n in out["not_rerun"]} == {
        "brief": qa_rerun.REASON_MODEL,
        "backtranslation": qa_rerun.REASON_MODEL,
    }
    assert git("status", "--porcelain") == "", "the re-run wrote into the checkout"


def test_d_pin_ci_classifies_a_qa_record_as_curator_and_asks_for_the_rerun(graph: Path) -> None:
    """**PIN — intended as built.** What the classifier does with ``targets/<id>/qa/`` in a pull
    request: ``qa-record`` is a curator role (``paths.CURATOR_ROLES``; F12-Q12 "The QA record is
    a curator's act (a grade rests on it, R9), so ``qa-record`` and ``qa-file`` are curator
    roles"), so a stranger's record is ``curator-unlisted``; a listed curator's is ``curator``
    mode, reviewed by the other listed curators (F08-R8), and ``modes.check`` validates it
    against ``qa/v1``. Since F12-T8 (finding D3) the classifier also names the record for the
    re-run (``qa_rerun.records_in``, reported as ``needs_qa_rerun``), which is where a typed pass
    is refused — not in ``modes.check``, which runs before any sandbox."""
    target = target_of(graph)
    path = write_hand_record(target, [hand_row(c) for c in qa.FLOOR_ROOT])
    rel = path.relative_to(graph).as_posix()
    listed = modes.Curators((("mike", CURATOR), ("second", "second-curator")))

    stranger = modes.classify([Change("A", rel)], author="stranger", curators=listed)
    assert stranger.mode is None and stranger.problems[0].code == "curator-unlisted"

    curated = modes.classify([Change("A", rel)], author=CURATOR, curators=listed)
    assert curated.mode == "curator", curated.problems
    assert curated.reviewers == ("second-curator",)
    assert modes.check(graph, curated) == []
    assert qa_rerun.records_in(curated.located) == [rel]


def test_d_pin_an_exhibit_row_is_trusted_by_content(graph: Path) -> None:
    """**PIN — intended, and working.** F12-R15: the reader "shall refuse a row whose exhibit
    file is missing, whose hash differs from the recorded one, or whose file contains ``sorry``
    ... and shall not count that row". A hand row naming an exhibit that is not in the tree does
    not count — the forgery R15 addresses is closed; D's gap is the rows with no file."""
    target = target_of(graph)
    rows = [hand_row(c, model="m", model_version="1") for c in qa.FLOOR_ROOT]
    rows.append(
        hand_row(
            "equivalence",
            exhibit=f"targets/{TARGET_ID}/qa/exhibits/root-equivalence-1.lean",
            exhibit_sha256="0" * 64,
        )
    )
    write_hand_record(target, rows)
    state = qa.pass_state(target, "root")
    assert [d.code for d in state.refused] == [qa.CODE_MISSING]
    assert state.exhibits == ()


# =================================================================================================
# E — `opn-gate status <target> active` on a curated target
# =================================================================================================


def test_e_status_active_on_a_curated_target_refuses_what_activation_refuses(graph: Path) -> None:
    """**Held (strict xfail) — spec conflict; Mike decided 2026-09-13 for this reading: refuse
    unless claimable.**

    F08-R11 (2026-09-10, before curated targets existed): "``opn-gate status <node-or-target>
    <abandoned|dormant|active> --cause <text>`` writing the corresponding record" — only dormancy
    is evidence-gated (F08-Q17: "an active declaration needs no evidence").
    F11-R5 (later, for targets with ``target.yaml``): "``opn-gate intake activate <target>``
    flipping status to ``active`` ... activation shall refuse while ``claimable`` would remain
    false, naming the missing condition." F11-R4 derives ``claimable`` from status, grade and
    posting. D-33 defines ``listed`` as "root published, not yet claimable — D-6/D-9", and gives
    ``active`` no curator path except as the reversal of dormancy ("the next merged progress
    artifact flips the status back to active mechanically"). ``intake.py`` calls the refusal
    "the whole point of deriving claimability rather than declaring it".

    Today, on a listed, unposted, mechanical-only curated target, ``intake activate`` refuses but
    ``status active`` exits 0, and the index publishes ``status: active, claimable: false`` — a
    state D-33's vocabulary has no name for, and R5's refusal bypassed by a second command.

    Reading tested: on a curated target, ``status active`` is held to R5 — refused (exit 1),
    naming the missing grade and posting, nothing written. Pre-F11 targets keep F08-R11
    unchanged (``test_cli_curator.py::test_status_command_declares_a_target_active_and_branches_it``
    runs on ``propositional``, which has no ``target.yaml``)."""
    target = target_of(graph)
    with pytest.raises(intake.IntakeError, match="posted upstream"):  # guard: R5 refuses
        intake.activate(graph, TARGET_ID, author="curator", date=LATER)
    before = sorted(p.name for p in (target / "status").iterdir())

    code, out = run_cli(
        "status",
        TARGET_ID,
        "active",
        "--cause",
        "x",
        "--graph",
        str(graph),
        "--target",
        TARGET_ID,
        "--author",
        "curator",
        "--date",
        LATER,
    )
    row = index_row(graph)
    assert code == cli.EXIT_FAIL, (
        f"status active bypassed F11-R5: exit {code}, {out}; index now "
        f"status={row['status']} claimable={row['claimable']}"
    )
    assert "D-10" in json.dumps(out) and "D-9" in json.dumps(out)
    assert sorted(p.name for p in (target / "status").iterdir()) == before
    assert row["status"] == "listed"


def test_e_pin_a_dormant_curated_target_may_be_declared_active_again(graph: Path) -> None:
    """**PIN — intended (D-33 reversal).** D-33: dormancy "changes nothing else ... every node
    stays claimable", and it is "reversible"; F08-R11 gives the curator ``status active`` for
    that. On a curated target that was activated through R5 and then declared dormant, a
    curator's ``active`` declaration succeeds and the target stays claimable — which also holds
    under the reading of E's failing test, since R5's conditions are already met."""
    target = target_of(graph)
    fidelity.attest(
        target, "root", "screened-and-signed", attestor="reviewer", date=WHEN[:10], evidence="read"
    )
    intake.post(graph, TARGET_ID, venue="v", url="https://example.org/p", date=WHEN)
    intake.activate(graph, TARGET_ID, author="curator", date="2026-09-12T11:00:00Z")
    common = ["--graph", str(graph), "--target", TARGET_ID, "--author", "curator"]
    code, out = run_cli(
        "status",
        TARGET_ID,
        "dormant",
        "--cause",
        "quiet",
        *common,
        "--date",
        "2026-09-12T12:00:00Z",
    )
    assert code == cli.EXIT_PASS, out
    assert index_row(graph)["status"] == "dormant" and index_row(graph)["claimable"] is True

    code, out = run_cli("status", TARGET_ID, "active", "--cause", "back", *common, "--date", LATER)
    assert code == cli.EXIT_PASS, out
    row = index_row(graph)
    assert row["status"] == "active" and row["claimable"] is True
