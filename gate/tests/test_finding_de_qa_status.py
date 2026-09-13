"""Findings D and E (2026-09-13): two reports from an end-to-end run, each judged against the
decisions and the specs, with the current behaviour captured.

D — a hand-typed ``qa/root-1.yaml`` satisfies the signature gate (F12-R9).
E — ``opn-gate status <target> active`` on a curated target skips activation's refusal (F11-R5).

Each test asserts the behaviour the governing text asks for. The two reader defects were fixed
in F12-T7 (Q18); D3 and E are held as strict expected failures naming Mike's decision of
2026-09-13 and the fix it calls for. Tests marked **PIN** capture behaviour judged intended.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in

from opn_gate import cli, fidelity, intake, modes, products, qa, schemas
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


@pytest.mark.xfail(
    strict=True,
    reason="finding D3 (D-9 v3.12, F12 user story): a hand-typed clean pass raises a grade; fix: CI re-runs the screens on a QA pull request (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_d_a_hand_typed_pass_does_not_raise_a_grade_through_the_command(graph: Path) -> None:
    """**Held (strict xfail): a spec gap; Mike chose CI re-running the screens.**

    The report, end to end: every floor row ``verdict: pass``, ``exhibit: null``,
    ``tool: hand`` (brief rows given a model name, so the two defects above are not the cause),
    and ``opn-gate fidelity euclid-primes root screened-and-signed --by reviewer`` exits 0 and
    writes the certificate.

    For refusal: F12 §2 "I want one command per check and a record I cannot forge by hand, so a
    grade is a summary of evidence rather than an opinion I typed"; D-9 v3.12 "each layer
    producing an artifact rather than an opinion" and screened-and-signed is "the mechanizable
    pass above completed with its exhibits recorded"; F12-Q8 names "a hand-committed row" as
    "the forgery the user story rules out".

    Against: F12-R15 closes the forgery only for rows that name a file, and qa/v1 and F12-Q15
    make a clean screen or a compile a row with ``exhibit: null`` ("clean screens leave no
    file"), so no requirement says how a clean pass is told apart from a typed one. F11-R13's
    "the D-9 v3.12 pass run by hand" does not license it: that pass is "evidence in this repo"
    (network), for targets that stay mechanical-only (F11-Q5), not a ``qa/v1`` record.

    The reading tested: a floor row counts only when a gate command produced it. The weakest
    fix that turns this green (``tool`` must be the gate's own command name) is still typeable;
    the real options are the owner's — see the report."""
    target = target_of(graph)
    rows = [
        hand_row(c, **({"model": "m", "model_version": "1"} if qa.KIND_OF[c] == "brief" else {}))
        for c in qa.FLOOR_ROOT
    ]
    write_hand_record(target, rows)
    evidence = graph.parent / "evidence.txt"
    evidence.write_text("compared the English with the Lean", encoding="utf-8")

    code, out = run_cli(
        "fidelity",
        TARGET_ID,
        "root",
        "screened-and-signed",
        "--graph",
        str(graph),
        "--by",
        "reviewer",
        "--evidence",
        str(evidence),
        "--date",
        WHEN,
    )
    assert code == cli.EXIT_FAIL, f"a hand-typed QA pass raised the grade: {out}"
    assert fidelity.subject_grades(target)[0].grade == "mechanical-only"


def test_d_pin_ci_checks_a_qa_record_by_schema_and_curator_only(graph: Path) -> None:
    """**PIN — intended as built.** What the classifier does with ``targets/<id>/qa/`` in a pull
    request: ``qa-record`` is a curator role (``paths.CURATOR_ROLES``; F12-Q12 "The QA record is
    a curator's act (a grade rests on it, R9), so ``qa-record`` and ``qa-file`` are curator
    roles"), so a stranger's record is ``curator-unlisted``; a listed curator's is ``curator``
    mode, reviewed by the other listed curators (F08-R8), and ``modes.check`` validates it
    against ``qa/v1`` and nothing more — no pin, row-coherence or tool check runs in CI, and no
    screen is re-run. The hand record below is accepted. If the owner decides CI must verify a
    QA record (finding D), this pin is the test to change."""
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
