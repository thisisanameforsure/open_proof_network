"""F12: the statement-QA record and pass (T1: R1, R2, R5, R15; AC1, AC3, AC4, AC21-AC23).

The record is what a fidelity grade rests on, so what is tested here is every way it could be
made to say more than was checked: a brief standing in for a screen, a stale record standing in
for a fresh one, an exhibit that is not there, not the same, or not a proof. Each is a named
refusal on both the writer and the reader, and none of them writes anything.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in

from opn_gate import fidelity, qa, schemas
from opn_gate.qa import QaError

DEFS = {"Primes.lean": "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p\n"}
WHEN = "2026-09-12T10:00:00Z"
TOOL = "opn-gate qa"
VERSION = "0.0.0"


@pytest.fixture
def target(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path)
    take_in(root, defs=DEFS)
    return root / "targets" / "euclid-primes"


def a_row(check: qa.Check, verdict: qa.Verdict = "pass", **kw: Any) -> qa.Row:
    if qa.KIND_OF[check] == "brief" and verdict == "pass":
        kw.setdefault("model", "fake-model")
        kw.setdefault("model_version", "1")
    return qa.row(check, verdict, tool=TOOL, tool_version=VERSION, timestamp=WHEN, **kw)


def floor_rows(subject: str = "root") -> list[qa.Row]:
    return [a_row(check) for check in qa.floor_for(subject)]


def write(target: Path, rows: list[qa.Row], subject: str = "root", **kw: Any) -> Path:
    return qa.write(target, subject, rows, date=WHEN, produced_by=TOOL, **kw)


def a_finding(target: Path, text: str = "theorem OpnQa.screen_false : True := trivial\n") -> qa.Row:
    """A positive screen-false with its exhibit stored the way the screen stores one."""
    path, digest = qa.store_exhibit(target, qa.exhibit_name("root", "screen-false", target), text)
    return a_row("screen-false", "fail", exhibit=path, exhibit_sha256=digest)


# --- R1, R2: the record and its two kinds --------------------------------------------------------


def test_every_check_has_exactly_one_kind() -> None:
    """R2: layers 1, 2 and 4 are exhibits, layer 3 is a brief; nothing is both or neither."""
    assert set(qa.KIND_OF) == set(qa.CHECKS)
    assert {c for c, k in qa.KIND_OF.items() if k == "brief"} == {"brief", "backtranslation"}
    for check in qa.CHECKS:
        assert a_row(check, "inconclusive").kind == qa.KIND_OF[check]


def test_row_coherence_rules() -> None:
    """The rules the schema cannot state: a finding carries its exhibit, a clean screen carries
    none, a path comes with its hash, and a brief names the model that produced it."""
    with pytest.raises(QaError, match="finding carries its exhibit"):
        a_row("screen-negation", "fail")
    with pytest.raises(QaError, match="found nothing produced nothing"):
        a_row("screen-negation", "pass", exhibit="x.lean", exhibit_sha256="a" * 64)
    with pytest.raises(QaError, match="go together"):
        a_row("equivalence", "pass", exhibit="x.lean")
    with pytest.raises(QaError, match="records the model"):
        qa.row("brief", "pass", tool=TOOL, tool_version=VERSION, timestamp=WHEN)
    with pytest.raises(QaError, match="unknown check"):
        qa.row("vibes", "pass", tool=TOOL, tool_version=VERSION, timestamp=WHEN)  # type: ignore[arg-type]


def test_record_is_written_once_per_run_and_read_back(target: Path) -> None:
    """R1: one file per run, append-only, validating against qa/v1 and pinned to the subject's
    hash and the graph's toolchain and Mathlib."""
    first = write(target, [a_row("compile")])
    second = write(target, floor_rows())
    assert (first.name, second.name) == ("root-1.yaml", "root-2.yaml")
    doc = yaml.safe_load(first.read_text(encoding="utf-8"))
    schemas.validate(doc, qa.SCHEMA)
    assert doc["statement_hash"] == qa.subject_hash(target, "root")
    assert doc["mathlib_sha"] == "a" * 40 and doc["lean_toolchain"] == "leanprover/lean4:v4.33.1"

    loaded = qa.load(target)["root"]
    assert [r.name for r in loaded] == ["root-1.yaml", "root-2.yaml"]
    assert [row.check for row in loaded[1].checks] == list(qa.FLOOR_ROOT)


def test_a_definition_is_a_subject_with_a_smaller_floor(target: Path) -> None:
    """A definition has nothing to negate: its pass is compile, brief and back-translation (Q10),
    and its hash is the file's own."""
    assert qa.subject_hash(target, "Primes") == schemas.content_hash(
        (target / "defs" / "Primes.lean").read_bytes()
    )
    write(target, floor_rows("Primes"), subject="Primes")
    assert qa.require_complete(target, "Primes").complete
    with pytest.raises(QaError, match="not a QA subject"):
        write(target, [a_row("compile")], subject="Nonexistent")


def test_a_broken_record_stops_the_reader_rather_than_being_skipped(target: Path) -> None:
    """C7: like a fidelity certificate (F11-R3) and unlike an attempt record, a QA record gates a
    grade — so a malformed one raises instead of quietly counting for nothing."""
    (qa.qa_dir(target)).mkdir(parents=True, exist_ok=True)
    (qa.qa_dir(target) / "root-7.yaml").write_text("checks: [oops\n", encoding="utf-8")
    with pytest.raises(schemas.SchemaError, match=r"root-7\.yaml"):
        qa.load(target)


# --- AC1: a brief alone raises nothing -----------------------------------------------------------


def test_brief_alone_cannot_raise(target: Path) -> None:
    """AC1, R2, R9: a record with a passing brief and back-translation and no exhibits is not a
    complete pass; the refusal names the compile and every screen still missing."""
    write(target, [a_row("brief"), a_row("backtranslation")])
    state = qa.pass_state(target, "root")
    assert state.checks["brief"] == "pass" and not state.complete
    assert state.missing == ("compile", *qa.SCREENS)
    with pytest.raises(QaError) as refusal:
        qa.require_complete(target, "root")
    assert refusal.value.code == "pass-incomplete"
    for screen in qa.SCREENS:
        assert screen in str(refusal.value), screen
    assert fidelity.SIGNED_FROM in str(refusal.value)


def test_a_complete_pass_is_every_floor_check_passed(target: Path) -> None:
    """R9: the floor is compile, the four screens, the brief and the back-translation;
    equivalence is a bonus layer and its absence holds nothing back (Q3)."""
    write(target, floor_rows())
    state = qa.require_complete(target, "root")
    assert state.complete and state.checks["equivalence"] is None
    assert state.as_dict()["missing"] == [] and state.as_dict()["complete"] is True


def test_an_inconclusive_check_is_not_a_pass(target: Path) -> None:
    """C7: a timed-out or errored screen leaves the floor unmet, exactly as if it had not run."""
    rows = [a_row(c, "inconclusive" if c == "screen-false" else "pass") for c in qa.FLOOR_ROOT]
    write(target, rows)
    state = qa.pass_state(target, "root")
    assert state.missing == ("screen-false",)
    assert not state.complete


def test_the_latest_run_of_a_check_wins(target: Path) -> None:
    """A re-run supersedes an earlier run of the same check, in record order then row order."""
    write(target, [a_row("compile", "inconclusive")])
    write(target, [a_row("compile", "pass")])
    assert qa.pass_state(target, "root").checks["compile"] == "pass"


# --- R5, AC4: staleness is derived from the pins ------------------------------------------------


def test_pin_move_stales_record(target: Path) -> None:
    """AC4: a complete pass counts for nothing once the graph's Mathlib pin moves; the grade
    gate refuses until the screens re-run, and the record itself is untouched."""
    path = write(target, floor_rows())
    assert qa.require_complete(target, "root").complete
    before = path.read_bytes()

    spec = qa.spec_of(target)
    spec["mathlib_sha"] = "b" * 40
    (target / "gate-spec.json").write_bytes(schemas.canonical_json(spec))

    state = qa.pass_state(target, "root")
    assert state.stale and state.fresh_records == 0 and state.stale_records == 1
    assert state.missing == qa.FLOOR_ROOT, "a stale record was counted"
    with pytest.raises(QaError, match="stale") as refusal:
        qa.require_complete(target, "root")
    assert "pin moved" in str(refusal.value) or "pin" in str(refusal.value)
    assert path.read_bytes() == before, "staleness must be derived, never written (Q9)"

    # Re-running the pass under the new pin makes it fresh again.
    write(target, floor_rows())
    assert qa.require_complete(target, "root").complete


def test_statement_change_stales_record(target: Path) -> None:
    """R5: a definition that changes is a different subject; every record for it is stale."""
    write(target, floor_rows("Primes"), subject="Primes")
    (target / "defs" / "Primes.lean").write_text(
        "def Opn.IsPrime (p : Nat) : Prop := 3 ≤ p\n", encoding="utf-8"
    )
    state = qa.pass_state(target, "Primes")
    assert state.stale and not state.complete


def test_a_record_under_another_toolchain_is_stale(target: Path) -> None:
    write(target, floor_rows())
    spec = qa.spec_of(target)
    spec["lean_toolchain"] = "leanprover/lean4:v4.34.0"
    assert qa.pass_state(target, "root", spec=spec).stale


# --- R4, AC3: a finding is routed by a person, never cleared by a re-run -------------------------


def test_finding_is_unrouted(target: Path) -> None:
    """AC3 (the record's half): a positive screen is a finding that holds the grade until a
    person routes it; the record asserts neither reading. T2 files the claim that names both."""
    finding = a_finding(target)
    write(target, [*(a_row(c) for c in qa.FLOOR_ROOT if c != "screen-false"), finding])
    state = qa.pass_state(target, "root")
    assert state.checks["screen-false"] == "fail"
    assert [f.check for f in state.unrouted] == ["screen-false"]
    assert not state.complete and state.missing == ("screen-false",)
    with pytest.raises(QaError, match="routing"):
        qa.require_complete(target, "root")
    # Nothing in the row says which reading it is.
    doc = yaml.safe_load(qa.load(target)["root"][0].path.read_text())  # type: ignore[union-attr]
    row = next(r for r in doc["checks"] if r["check"] == "screen-false")
    assert "reading" not in row and "class" not in row


def test_a_routed_finding_still_needs_a_clean_screen(target: Path) -> None:
    """R4, R9: routing takes the finding off the curator's queue; it does not make the screen
    pass. The floor is met only when a fresh run of the screen finds nothing."""
    finding = a_finding(target)
    write(target, [*(a_row(c) for c in qa.FLOOR_ROOT if c != "screen-false"), finding])
    state = qa.pass_state(target, "root", routed=lambda f: True)
    assert state.unrouted == () and state.missing == ("screen-false",)


def test_a_finding_is_not_cleared_by_a_later_pass(target: Path) -> None:
    """A clean re-run of a screen after a finding means the budget or the library moved, not
    that the kernel-checked exhibit stopped being one: the finding stays until it is routed."""
    finding = a_finding(target)
    write(target, [finding])
    write(target, [a_row("screen-false", "pass")])
    state = qa.pass_state(target, "root")
    assert state.checks["screen-false"] == "pass"
    assert [f.exhibit for f in state.unrouted] == [finding.exhibit]
    assert not state.complete


# --- R15, AC21-AC23: an exhibit is trusted by content ------------------------------------------


def test_missing_exhibit_is_refused(target: Path) -> None:
    """AC21: with the file deleted, the reader refuses the row with `exhibit-missing`, does not
    count it, and the grade gate names it; a writer citing the same path refuses too."""
    finding = a_finding(target)
    write(target, [finding])
    assert finding.exhibit is not None
    (qa.graph_root_of(target) / finding.exhibit).unlink()

    state = qa.pass_state(target, "root")
    assert [d.code for d in state.refused] == [qa.CODE_MISSING]
    assert state.checks["screen-false"] is None and state.findings == ()
    with pytest.raises(QaError) as refusal:
        qa.require_complete(target, "root")
    assert qa.CODE_MISSING in str(refusal.value)

    with pytest.raises(QaError) as written:
        write(target, [finding])
    assert written.value.code == qa.CODE_MISSING
    assert not (qa.qa_dir(target) / "root-2.yaml").exists(), "a refusal wrote a record"


def test_exhibit_hash_mismatch_is_refused(target: Path) -> None:
    """AC22: one altered byte and the row is refused with `exhibit-hash-mismatch` by both."""
    finding = a_finding(target)
    write(target, [finding])
    assert finding.exhibit is not None
    path = qa.graph_root_of(target) / finding.exhibit
    path.write_bytes(path.read_bytes().replace(b"trivial", b"trivial "))

    state = qa.pass_state(target, "root")
    assert [d.code for d in state.refused] == [qa.CODE_HASH]
    assert state.refused[0].details["recorded"] == finding.exhibit_sha256
    assert state.findings == ()
    with pytest.raises(QaError) as written:
        write(target, [finding])
    assert written.value.code == qa.CODE_HASH


def test_exhibit_containing_sorry_is_refused(target: Path) -> None:
    """AC23: the store never takes a `sorry`; and a hand-committed exhibit with `sorry` and a
    matching hash is refused by the writer and the reader with `exhibit-sorry`."""
    with pytest.raises(QaError) as stored:
        qa.store_exhibit(target, "root-screen-false-9.lean", "theorem t : False := sorry\n")
    assert stored.value.code == qa.CODE_SORRY
    assert not (qa.exhibits_dir(target) / "root-screen-false-9.lean").exists()

    forged = qa.exhibits_dir(target) / "root-screen-false-1.lean"
    forged.parent.mkdir(parents=True, exist_ok=True)
    text = b"theorem OpnQa.screen_false : False := by\n  sorry\n"
    forged.write_bytes(text)
    row = a_row(
        "screen-false",
        "fail",
        exhibit=qa.relative(target, forged),
        exhibit_sha256=schemas.content_hash(text),
    )
    with pytest.raises(QaError) as written:
        write(target, [row])
    assert written.value.code == qa.CODE_SORRY

    # Hand-written record, matching hash: the reader still refuses it.
    doc = qa.Record(
        "root",
        qa.subject_hash(target, "root"),
        "leanprover/lean4:v4.33.1",
        "a" * 40,
        WHEN,
        TOOL,
        (row,),
    ).as_dict()
    qa.qa_dir(target).mkdir(parents=True, exist_ok=True)
    (qa.qa_dir(target) / "root-1.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    state = qa.pass_state(target, "root")
    assert [d.code for d in state.refused] == [qa.CODE_SORRY] and state.findings == ()


def test_a_comment_naming_sorry_is_not_a_sorry(target: Path) -> None:
    """The token rule of F08-Q18: the word in a comment does not refuse a real exhibit."""
    finding = a_finding(target, "-- no sorry here\ntheorem OpnQa.screen_false : True := trivial\n")
    write(target, [finding])
    assert qa.pass_state(target, "root").refused == ()


def test_the_exhibit_store_is_append_only(target: Path) -> None:
    qa.store_exhibit(target, "root-screen-false-1.lean", "theorem a : True := trivial\n")
    with pytest.raises(QaError, match="append-only"):
        qa.store_exhibit(target, "root-screen-false-1.lean", "theorem b : True := trivial\n")
    assert qa.exhibit_name("root", "screen-false", target) == "root-screen-false-2.lean"


def test_a_brief_file_is_not_evidence_and_is_not_integrity_checked(target: Path) -> None:
    """R15 reaches exhibit rows: a brief's text file is a judgement, so its absence refuses
    nothing — and its presence counts toward no exhibit list."""
    briefs = qa.qa_dir(target) / "briefs"
    briefs.mkdir(parents=True)
    (briefs / "root-brief-1.md").write_text("constants: none\n", encoding="utf-8")
    row = a_row(
        "brief", exhibit=qa.relative(target, briefs / "root-brief-1.md"), exhibit_sha256="0" * 64
    )
    write(target, [row])
    (briefs / "root-brief-1.md").unlink()
    state = qa.pass_state(target, "root")
    assert (
        state.refused == ()
        and state.exhibits == ()
        and [r.check for r in state.briefs] == ["brief"]
    )
