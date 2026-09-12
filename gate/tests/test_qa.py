"""F12: the statement-QA record and pass (T1: R1, R2, R5, R15; AC1, AC3, AC4, AC21-AC23).

The record is what a fidelity grade rests on, so what is tested here is every way it could be
made to say more than was checked: a brief standing in for a screen, a stale record standing in
for a fresh one, an exhibit that is not there, not the same, or not a proof. Each is a named
refusal on both the writer and the reader, and none of them writes anything.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest
import yaml
from fakes import FakeModelClient, FakeToolchain, used_constants_result
from harness import copy_graph, take_in
from scripted import ScriptedToolchain

from opn_gate import config, fidelity, intake, layout, modes, qa, schemas
from opn_gate.paths import Change, Claim
from opn_gate.qa import QaError
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import ElabResult, Message

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


# =================================================================================================
# T2: the soundness screens (R3, R4; AC2, AC3, AC16, AC17, AC18)
# =================================================================================================


ROOT_NODE = "and-reassoc"  # the fixture node ``take_in`` copies in as euclid-primes' root
STATEMENT_MODULE = f"Nodes.«{ROOT_NODE}».Statement"
SCREEN_MODULES = {
    check: f"{qa.SCREEN_NAMESPACE}.{stem}"
    for check, stem in (
        ("screen-statement", "ScreenStatement"),
        ("screen-negation", "ScreenNegation"),
        ("screen-false", "ScreenFalse"),
    )
}
NOTHING_PROVES = set(SCREEN_MODULES.values())


def screen_context(target: Path, toolchain: Any) -> RunContext:
    graph_root = target.parents[1]
    spec_path = target / "gate-spec.json"
    return RunContext(
        graph_root=graph_root,
        claim=Claim(target.name, ROOT_NODE),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=graph_root.parent / "work",
        toolchain=toolchain,
        settings=config.load({}),
    )


def run_screen(target: Path, toolchain: Any, **kw: Any) -> qa.ScreenRun:
    kw.setdefault("attempt_budget_s", 60.0)
    kw.setdefault("subject_budget_s", 300.0)
    return qa.screen(screen_context(target, toolchain), "root", date=WHEN, **kw)


def verdicts(run: qa.ScreenRun) -> dict[str, str]:
    return {r.check: r.verdict for r in run.rows}


# --- the shapes the attempts are built from (R3, Q11) -------------------------------------------


@pytest.mark.parametrize(
    ("text", "binders", "prop", "false_form"),
    [
        (
            "theorem T.a : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by\n  sorry\n",
            "",
            "∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r)",
            "∀ p q r : Prop, (p ∧ q) ∧ r → False",
        ),
        (
            "theorem T.b (n : Nat) {m : Nat} [inst : Inhabited Nat] : n < m → m ≠ 0 := sorry\n",
            "(n : Nat) {m : Nat} [inst : Inhabited Nat]",
            "n < m → m ≠ 0",
            "n < m → False",
        ),
        (
            "theorem T.c : ∀ n : Nat, ∃ p : Nat, n < p ∧ Opn.IsPrime p := by\n  sorry\n",
            "",
            "∀ n : Nat, ∃ p : Nat, n < p ∧ Opn.IsPrime p",
            "∀ n : Nat, False",
        ),
        (
            "theorem T.d : (∀ x : Nat, x = x) → True := by sorry\n",
            "",
            "(∀ x : Nat, x = x) → True",
            "(∀ x : Nat, x = x) → False",
        ),
        ("namespace Opn\ntheorem e : True := by\n  sorry\nend Opn\n", "", "True", "False"),
    ],
)
def test_signature_shapes(text: str, binders: str, prop: str, false_form: str) -> None:
    """R3: the statement as a goal, its negation, and its conclusion replaced by False — only
    the last top-level arrow is the conclusion's; a hypothesis inside brackets is left alone."""
    statement = layout.parse_statement(text)
    assert isinstance(statement, layout.Statement)
    sig = qa.signature_of(statement)
    assert isinstance(sig, qa.Signature)
    assert (sig.binders, sig.prop, sig.false_form) == (binders, prop, false_form)
    assert sig.negation == f"¬ ({sig.closed})"
    if binders:
        assert sig.closed == f"∀ {binders}, {prop}"


def test_an_unreadable_signature_is_inconclusive_not_a_pass(target: Path) -> None:
    """Q11, C7: a shape the rewriter cannot read leaves every screen inconclusive, named."""
    node = target / "nodes" / ROOT_NODE
    text = "theorem OpnProp.and_reassoc (p : Prop := by\n  sorry\n"  # a binder that never closes
    (node / "Statement.lean").write_text(text, encoding="utf-8")
    meta = yaml.safe_load((node / "META.yaml").read_text())
    meta["statement-hash"] = schemas.content_hash(text.encode())
    (node / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    run = run_screen(target, FakeToolchain())
    assert verdicts(run)["compile"] == "pass"
    assert all(verdicts(run)[c] == "inconclusive" for c in qa.SCREENS)
    assert run.problems[0].code == "statement-shape" and not run.clean


def test_scratch_source_names_the_subject_as_hypothesis_or_goal_never_sorry() -> None:
    """R3: the subject is a goal or an explicit hypothesis; no scratch file uses sorry, and a
    Mathlib pin adds the Mathlib-only tactics."""
    sig = qa.Signature("(n : Nat)", "0 < n → n ≠ 0")
    plan = qa.attempts_for(sig, [])
    assert isinstance(plan, list)
    assert [a.check for a in plan] == ["screen-statement", "screen-negation", "screen-false"]
    for attempt in plan:
        source = qa.scratch_source(attempt, imports=["Defs.X"], mathlib=False)
        assert not layout.mentions_sorry(source)
        assert source.startswith("import Defs.X\n")
        assert "aesop" not in source
    consequence = layout.parse_statement("theorem C.one : ∀ n : Nat, n = n := by\n  sorry\n")
    assert isinstance(consequence, layout.Statement)
    with_c = qa.attempts_for(sig, [("One", consequence)])
    assert isinstance(with_c, list) and with_c[-1].check == "screen-consequence"
    source = qa.scratch_source(with_c[-1], imports=[], mathlib=True)
    assert "(opn_subject : ∀ (n : Nat), 0 < n → n ≠ 0)" in source
    assert ": ∀ n : Nat, n = n := by" in source and "aesop" in source


# --- AC2, AC3: a positive screen is a finding with an exhibit and an unrouted claim ---------------


def test_false_screen_files_unrouted_claim(target: Path) -> None:
    """AC2: contradictory hypotheses — the False screen proves, an exhibit is written, the run
    is not clean (the command exits non-zero), and a defect-claim/v2 claim of class
    screen-finding is opened, carrying the exhibit."""
    proves_false = ScriptedToolchain(
        failing_modules=NOTHING_PROVES - {SCREEN_MODULES["screen-false"]}
    )
    run = run_screen(target, proves_false)
    assert verdicts(run) == {
        "compile": "pass",
        "screen-consequence": "pass",
        "screen-statement": "pass",
        "screen-negation": "pass",
        "screen-false": "fail",
    }
    assert not run.clean and [r.check for r in run.findings] == ["screen-false"]
    exhibit = run.exhibits[0]
    assert exhibit == f"targets/{target.name}/qa/exhibits/root-screen-false-1.lean"
    graph_root = target.parents[1]
    assert (graph_root / exhibit).is_file()
    assert f"kernel_replay:{SCREEN_MODULES['screen-false']}" in proves_false.calls
    assert f"axioms:{SCREEN_MODULES['screen-false']}:OpnQa.screen_false" in proves_false.calls

    claim_path = graph_root / run.claims[0]
    assert claim_path.parent == target / "nodes" / ROOT_NODE / "defects"
    claim = schemas.load_yaml(claim_path, "defect-claim/v2")
    assert claim["class"] == "screen-finding" and claim["qa_exhibit"] == exhibit
    assert claim["exhibit"] == (graph_root / exhibit).read_text(encoding="utf-8")
    assert claim["line"] == 1 and claim["stmt_ref"] == ROOT_NODE
    # The record row cites the exhibit by content and the pass state sees the finding.
    state = qa.pass_state(target, "root", routed=qa.routed_by_claims(target))
    assert [f.exhibit for f in state.unrouted] == [exhibit] and state.refused == ()


def test_finding_is_unrouted_until_a_curator_routes_it(target: Path) -> None:
    """AC3: the claim names both readings and asserts neither; routing is a later claim that
    names it, after which the finding no longer holds the grade — and the gate's pre-triage
    accepts both claims."""
    run = run_screen(
        target, ScriptedToolchain(failing_modules=NOTHING_PROVES - {SCREEN_MODULES["screen-false"]})
    )
    graph_root = target.parents[1]
    claim_rel = run.claims[0]
    claim = yaml.safe_load((graph_root / claim_rel).read_text(encoding="utf-8"))
    assert claim["readings"] == ["misformalization", "refutation"]
    assert claim["routes"] is None
    assert "reading" not in claim and claim["class"] == "screen-finding"
    assert "misformalization" in claim["note"] and "refuted" in claim["note"]
    assert not qa.pass_state(target, "root", routed=qa.routed_by_claims(target)).routed_findings

    node = layout.load_node(target / "nodes" / ROOT_NODE, target.name)
    assert isinstance(node, layout.Node)
    with pytest.raises(QaError, match="not a screen-finding claim"):
        qa.route_finding(
            target,
            node,
            "nope.yaml",
            reading="refutation",
            defect_class="vacuity",
            contributor="curator",
            date="2026-09-13T00:00:00Z",
        )
    routed = qa.route_finding(
        target,
        node,
        Path(claim_rel).name,
        reading="misformalization",
        defect_class="vacuity",
        contributor="curator",
        date="2026-09-13T00:00:00Z",
        note="the hypotheses cannot hold",
    )
    state = qa.pass_state(target, "root", routed=qa.routed_by_claims(target))
    assert state.unrouted == () and state.routed_findings == (state.findings[0],)
    # Routed, but the screen still has to pass fresh: the finding is a fact about the statement.
    assert "screen-false" in state.missing and state.checks["screen-false"] == "fail"

    # The gate's own pre-triage (D-16, D-35) accepts the screen's claim and the routing claim.
    changes = [Change("A", claim_rel), Change("A", routed), Change("A", run.record or "")]
    for change in changes[:2]:
        appended = modes.classify([change])
        assert appended.mode == "append", change
        assert modes.check(graph_root, appended) == [], change


def test_a_routing_claim_must_name_a_real_finding(target: Path) -> None:
    """R4 in the gate: a claim that routes a file which is not a screen-finding bounces."""
    run = run_screen(
        target, ScriptedToolchain(failing_modules=NOTHING_PROVES - {SCREEN_MODULES["screen-false"]})
    )
    graph_root = target.parents[1]
    bad = dict(yaml.safe_load((graph_root / run.claims[0]).read_text()))
    bad["routes"] = {"claim": "ghost.yaml", "reading": "refutation"}
    bad["class"] = "vacuity"
    bad["qa_exhibit"] = None
    rel = f"targets/{target.name}/nodes/{ROOT_NODE}/defects/20260913T000000-curator.yaml"
    (graph_root / rel).write_text(yaml.safe_dump(bad), encoding="utf-8")
    found = modes.check(graph_root, modes.classify([Change("A", rel)]))
    assert [d.code for d in found] == ["defect-route"]


def test_a_clean_run_writes_a_record_and_nothing_else(target: Path) -> None:
    """R3: three clean screens, a compile and a vacuous consequence pass; no exhibit, no claim,
    and the pass state lacks only the two brief rows."""
    run = run_screen(target, ScriptedToolchain(failing_modules=NOTHING_PROVES))
    assert run.clean and run.exhibits == [] and run.claims == []
    assert run.record == f"targets/{target.name}/qa/root-1.yaml"
    state = qa.pass_state(target, "root")
    assert state.missing == ("brief", "backtranslation")
    consequence = next(r for r in run.rows if r.check == "screen-consequence")
    assert consequence.note == qa.NOTE_NO_CONSEQUENCES


def test_a_declared_consequence_is_attempted_under_the_subject(target: Path) -> None:
    """R3: each ``qa/consequences/<Name>.lean`` becomes an attempt with the statement as an
    explicit hypothesis; a consequence that proves is a finding like any other."""
    directory = qa.qa_dir(target) / qa.CONSEQUENCES_DIR
    directory.mkdir(parents=True)
    (directory / "Absurd.lean").write_text(
        "theorem OpnQa.C.absurd : ∀ p : Prop, p := by\n  sorry\n", encoding="utf-8"
    )
    proves = ScriptedToolchain(failing_modules=NOTHING_PROVES)  # the consequence module proves
    run = run_screen(target, proves)
    row = next(r for r in run.rows if r.check == "screen-consequence")
    assert row.verdict == "fail" and row.note is not None and "consequence Absurd" in row.note
    assert "elaborate:OpnQa.ScreenConsequenceAbsurd" in proves.calls
    source = (target.parents[1] / run.exhibits[0]).read_text(encoding="utf-8")
    assert "(opn_subject : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r))" in source
    assert not run.clean


def test_a_definition_is_refused_by_the_screens(target: Path) -> None:
    """Q10: a definition has nothing to negate; the refusal names what its pass is."""
    with pytest.raises(QaError, match="nothing to negate"):
        qa.screen(
            screen_context(target, FakeToolchain()),
            "Primes",
            date=WHEN,
            attempt_budget_s=1,
            subject_budget_s=1,
        )


# --- AC16, AC17, AC18: timeouts, budgets and errors are inconclusive, never a pass ----------------


def test_timeout_is_inconclusive_not_pass(target: Path) -> None:
    """AC16: one attempt times out — its row is inconclusive, carries the budget it ran under,
    writes no exhibit, and the pass is not complete."""
    slow = ScriptedToolchain(
        failing_modules=NOTHING_PROVES - {SCREEN_MODULES["screen-negation"]},
        timeout_modules={SCREEN_MODULES["screen-negation"]},
    )
    run = run_screen(target, slow, attempt_budget_s=7.0)
    row = next(r for r in run.rows if r.check == "screen-negation")
    assert row.verdict == "inconclusive" and row.exhibit is None
    assert row.budget_s == 7.0 and row.note == qa.NOTE_TIMEOUT
    assert run.exhibits == [] and not run.clean
    assert qa.pass_state(target, "root").missing == ("screen-negation", "brief", "backtranslation")


def test_subject_budget_marks_remaining_checks_inconclusive(target: Path) -> None:
    """AC17: the clock passes the per-subject budget after the second attempt; every remaining
    row exists, inconclusive, with the budget-exhausted note — none is missing."""
    ticks = iter([0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 400.0, 401.0, 402.0, 403.0, 404.0])

    def fake_clock() -> float:
        return next(ticks)

    run = run_screen(
        target,
        ScriptedToolchain(failing_modules=NOTHING_PROVES),
        subject_budget_s=300.0,
        clock=fake_clock,
    )
    assert [r.check for r in run.rows] == [
        "compile",
        "screen-consequence",
        "screen-statement",
        "screen-negation",
        "screen-false",
    ]
    by_check = {r.check: r for r in run.rows}
    assert by_check["screen-statement"].verdict == "pass"
    assert by_check["screen-negation"].verdict == "pass"
    assert by_check["screen-false"].verdict == "inconclusive"
    assert by_check["screen-false"].note == qa.NOTE_BUDGET
    assert not run.clean


def test_erroring_screen_is_inconclusive_and_visible(
    target: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """AC18: the toolchain raises — the row is inconclusive, the error is logged, and the run is
    not a clean pass."""
    with caplog.at_level(logging.ERROR, logger="opn_gate.qa"):
        run = run_screen(target, FakeToolchain(raise_on="elaborate"))
    assert all(r.verdict == "inconclusive" for r in run.rows)
    assert not run.clean
    assert any(
        "blew up" in rec.getMessage() or "failed" in rec.getMessage() for rec in caplog.records
    )
    compile_row = run.rows[0]
    assert compile_row.check == "compile" and "RuntimeError" in (compile_row.note or "")
    assert run.record is not None, "a run that errored still leaves its record"


def test_an_elaborated_proof_the_kernel_refuses_is_inconclusive(target: Path) -> None:
    """R3: a success is a finding only once leanchecker and the axiom check agree; anything
    less is recorded inconclusive with the diagnostic, and no exhibit is stored."""
    from opn_gate.toolchain import AxiomResult, ReplayResult  # noqa: PLC0415

    proves = ScriptedToolchain(failing_modules=NOTHING_PROVES - {SCREEN_MODULES["screen-false"]})
    proves.replay = ReplayResult(ok=False, output="kernel: declaration has metavariables")
    run = run_screen(target, proves)
    row = next(r for r in run.rows if r.check == "screen-false")
    assert row.verdict == "inconclusive" and "kernel-replay-failed" in (row.note or "")
    assert run.exhibits == [] and run.claims == []

    proves.replay = ReplayResult(ok=True)
    proves.axiom_result = AxiomResult(ok=True, axioms=frozenset({"sorryAx"}))
    run = run_screen(target, proves)
    row = next(r for r in run.rows if r.check == "screen-false")
    assert row.verdict == "inconclusive" and "axiom-not-allowed" in (row.note or "")
    assert run.exhibits == []


def test_a_statement_that_does_not_compile_stops_at_layer_one(target: Path) -> None:
    """R3: layer 1 fails — the compile row says so and every screen is inconclusive."""
    run = run_screen(target, ScriptedToolchain(failing_modules={STATEMENT_MODULE}))
    assert verdicts(run)["compile"] == "fail"
    assert all(verdicts(run)[c] == "inconclusive" for c in qa.SCREENS)
    assert not run.clean and run.record is not None


# --- the command (R3): sandboxed like admission, non-zero on anything short of a clean pass -------


def test_qa_screen_command_runs_in_the_sandbox_and_routes(
    tmp_path: Path, seam: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """``qa screen --sandbox`` puts the seam in the step-3 image with the root read-only and the
    work directory read-write, exits 1 on a finding and 0 on a clean pass; ``qa route`` appends
    the curator's claim."""
    from opn_gate import cli  # noqa: PLC0415

    root = copy_graph(tmp_path)
    take_in(root, defs=DEFS)
    target = root / "targets" / "euclid-primes"
    seam.fake = ScriptedToolchain(failing_modules=NOTHING_PROVES - {SCREEN_MODULES["screen-false"]})
    out = tmp_path / "out"
    argv = [
        "qa",
        "screen",
        "euclid-primes",
        "root",
        "--graph",
        str(root),
        "--sandbox",
        "--out",
        str(out),
        "--date",
        WHEN,
    ]
    code = cli.main(argv)
    captured = capsys.readouterr()
    doc = json.loads(captured.out)
    assert code == cli.EXIT_FAIL and doc["ok"] is False and doc["findings"] == ["screen-false"]
    assert "findings: screen-false" in captured.err
    assert seam.made[0]["read_only"] == [(target / "nodes" / ROOT_NODE).resolve()]
    assert seam.made[0]["read_write"] == [(out / "work").resolve()]
    assert (root / doc["record"]).is_file() and (root / doc["claims"][0]).is_file()

    claim = Path(doc["claims"][0]).name
    code = cli.main(
        [
            "qa",
            "route",
            "euclid-primes",
            "root",
            claim,
            "--graph",
            str(root),
            "--reading",
            "refutation",
            "--class",
            "other-with-exhibit",
            "--by",
            "mike",
            "--date",
            "2026-09-13T00:00:00Z",
        ]
    )
    routed = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_PASS and routed["routed"] == claim
    assert qa.pass_state(target, "root", routed=qa.routed_by_claims(target)).unrouted == ()

    # A clean pass exits 0.
    seam.fake = ScriptedToolchain(failing_modules=NOTHING_PROVES)
    code = cli.main([*argv[:-2], "--date", "2026-09-14T00:00:00Z", "--out", str(tmp_path / "out2")])
    doc = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_PASS and doc["ok"] is True and doc["record"].endswith("root-2.yaml")

    # A definition subject is a refusal (Q10), reported the curator way.
    code = cli.main(
        [
            "qa",
            "screen",
            "euclid-primes",
            "Primes",
            "--graph",
            str(root),
            "--sandbox",
            "--out",
            str(tmp_path / "out3"),
        ]
    )
    refused = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_FAIL and "nothing to negate" in refused["refused"]


# =================================================================================================
# T3: the brief, the back-translation and the equivalence (R6, R7, R8; AC5, AC6, AC15, AC19)
# =================================================================================================

CONSTANTS = [
    ("Opn.IsPrime", "Defs.Primes"),
    ("And", "Init.Prelude"),
    ("Nat.lt", "Init.Prelude"),
]
SIGNATURE = "OpnProp.and_reassoc : ∀ (p q r : Prop), (p ∧ q) ∧ r → p ∧ q ∧ r"
DEFINITIONS = {
    "Opn.IsPrime": "def Opn.IsPrime : Nat → Prop :=\nfun p => 2 ≤ p",
    "And": "structure And (a b : Prop) : Prop\nnumber of parameters: 2",
    "Nat.lt": "def Nat.lt : Nat → Nat → Prop :=\nfun n m => Nat.le (n + 1) m",
}


def brief_toolchain() -> FakeToolchain:
    """A fake whose `#check` and `#print` answers sit on the lines the scratch file puts them:
    one import, a blank line, `#check` on line 3, one `#print` per constant from line 4."""
    messages = [Message("Brief.lean", 3, 0, "info", SIGNATURE)]
    messages += [
        Message("Brief.lean", 4 + i, 0, "info", DEFINITIONS[name])
        for i, (name, _) in enumerate(CONSTANTS)
    ]
    return FakeToolchain(
        constants=used_constants_result([*CONSTANTS, ("OpnProp.and_reassoc", None)]),
        elab=ElabResult(ok=True, messages=tuple(messages)),
    )


def test_brief_lists_every_referenced_constant(target: Path) -> None:
    """AC15, R6: each constant exactly once with its definition as printed under the pin, the
    structural signature, the model's judgement labelled as one, and a `brief` row with the
    model and version filled — a judgement, not evidence."""
    model = FakeModelClient(answer="Nothing to flag; `Opn.IsPrime` is used as a predicate.")
    run = qa.brief(
        screen_context(target, brief_toolchain()), "root", model=model, date=WHEN, timeout_s=60
    )
    assert run.ok and run.row.kind == "brief" and run.row.verdict == "pass"
    assert (run.row.model, run.row.model_version) == ("fake-model", "fake-model-2026-09-12")
    assert run.row.exhibit == f"targets/{target.name}/qa/briefs/root-brief-1.md"
    text = (target.parents[1] / run.row.exhibit).read_text(encoding="utf-8")
    for name, module in CONSTANTS:
        assert text.count(f"### `{name}`") == 1, name
        assert module in text and DEFINITIONS[name] in text
    assert "### `OpnProp.and_reassoc`" not in text, "the subject is not its own constant"
    assert SIGNATURE in text
    assert text.index(qa.JUDGEMENT_HEADING) > text.index("## Referenced constants")
    assert model.answer in text
    # The model saw the grounded facts, and only after the kernel produced them.
    system, prompt = model.prompts[0]
    assert system == qa.BRIEF_SYSTEM and SIGNATURE in prompt and DEFINITIONS["And"] in prompt
    # R2: a brief alone raises nothing.
    assert "brief" not in qa.pass_state(target, "root").missing
    assert not qa.pass_state(target, "root").complete


def test_model_outage_is_inconclusive(target: Path) -> None:
    """AC19, C7: the model raises or answers non-2xx — the row is inconclusive and no brief
    file claiming success exists."""
    for failure in ("the model provider answered 503", "the model declined (bio)"):
        model = FakeModelClient(fail=failure)
        run = qa.brief(
            screen_context(target, brief_toolchain()), "root", model=model, date=WHEN, timeout_s=60
        )
        assert not run.ok and run.row.verdict == "inconclusive"
        assert run.row.exhibit is None and failure in (run.row.note or "")
        assert run.row.model == "fake-model"
    assert not (qa.qa_dir(target) / qa.BRIEFS_DIR).exists()
    assert qa.pass_state(target, "root").checks["brief"] == "inconclusive"


def test_a_brief_whose_grounding_fails_is_inconclusive(target: Path) -> None:
    """R6, C7: no constants could be read — the row says so and the model is never asked."""
    from fakes import metaprogram_garbage  # noqa: PLC0415

    model = FakeModelClient()
    run = qa.brief(
        screen_context(target, FakeToolchain(constants=metaprogram_garbage())),
        "root",
        model=model,
        date=WHEN,
        timeout_s=60,
    )
    assert run.row.verdict == "inconclusive" and "used-constants" in (run.row.note or "")
    assert model.prompts == []


def test_a_definition_gets_its_own_brief(target: Path) -> None:
    """Q10: a definition is a subject; its constants come from `opn-used-constants` over the
    definition file, and the brief names its declaration."""
    fake = brief_toolchain()
    run = qa.brief(
        screen_context(target, fake), "Primes", model=FakeModelClient(), date=WHEN, timeout_s=60
    )
    assert run.ok
    assert any(c.startswith("used_constants:Opn.IsPrime") for c in fake.calls)
    assert "Declaration: `Opn.IsPrime`" in (target.parents[1] / run.row.exhibit).read_text()  # type: ignore[operator]


def test_backtranslate_independence(target: Path) -> None:
    """AC5, R7: provenance naming an AI formalizer refuses a model of the same family before
    any call; provenance naming none proceeds, records `formalizer: unknown`, and withholds the
    informal source from the model."""
    record = intake.load_doc(target)
    assert record is not None
    record["provenance"]["author"] = "Claude Opus 4.5 (auto-formalized)"
    intake.write_doc(target, record)
    same_family = FakeModelClient(model="claude-opus-5")
    with pytest.raises(QaError, match="family") as refusal:
        qa.backtranslate(target, "root", model=same_family, date=WHEN)
    assert "claude" in str(refusal.value) and same_family.prompts == []
    other_family = FakeModelClient(model="gemini-3-pro", answer="For all propositions...")
    run = qa.backtranslate(target, "root", model=other_family, date=WHEN)
    assert run.ok and (run.row.note or "") == "formalizer: claude"

    record["provenance"]["author"] = "author"
    intake.write_doc(target, record)
    model = FakeModelClient(model="claude-opus-5", answer="For every three propositions...")
    run = qa.backtranslate(target, "root", model=model, date=WHEN)
    assert run.ok and run.row.note == "formalizer: unknown"
    assert run.row.exhibit == f"targets/{target.name}/qa/backtranslation/root-backtranslation-2.md"
    text = (target.parents[1] / run.row.exhibit).read_text(encoding="utf-8")
    assert "Formalizer per provenance: unknown" in text
    assert model.answer in text and record["informal"] in text, "the comparison sits beside it"
    system, prompt = model.prompts[0]
    assert system == qa.BACKTRANSLATION_SYSTEM
    assert "theorem OpnProp.and_reassoc" in prompt and "defs/Primes.lean" in prompt
    assert record["informal"] not in prompt and record["title"] not in prompt, "withheld (R7)"


def test_backtranslate_outage_is_inconclusive(target: Path) -> None:
    run = qa.backtranslate(target, "root", model=FakeModelClient(fail="answered 502"), date=WHEN)
    assert run.row.verdict == "inconclusive" and run.row.exhibit is None
    assert not (qa.qa_dir(target) / qa.BACKTRANSLATION_DIR).exists()


def equivalence_context(tmp_path: Path, toolchain: Any) -> tuple[Path, RunContext]:
    """The propositional fixture: its root and `and-reassoc` as the other formalization."""
    root = copy_graph(tmp_path)
    target = root / "targets" / "propositional"
    spec_path = target / "gate-spec.json"
    ctx = RunContext(
        graph_root=root,
        claim=Claim("propositional", "and-swap-reassoc"),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=tmp_path / "work",
        toolchain=toolchain,
        settings=config.load({}),
    )
    return target, ctx


def test_equivalence_failure_is_inconclusive(tmp_path: Path) -> None:
    """AC6, R8, Q3: one implication proves and the other does not — the row is inconclusive,
    no exhibit is written, and nothing negative is recorded."""
    target, ctx = equivalence_context(
        tmp_path, ScriptedToolchain(failing_modules={"OpnQa.EquivBackward"})
    )
    run = qa.equivalence(ctx, "and-reassoc", date=WHEN, attempt_budget_s=30)
    assert run.row.verdict == "inconclusive" and run.row.exhibit is None
    assert "not negative evidence" in (run.row.note or "")
    assert not (qa.exhibits_dir(target)).exists()
    state = qa.pass_state(target, "root")
    assert state.checks["equivalence"] == "inconclusive"
    assert "equivalence" not in state.floor


def test_a_proved_pair_is_an_exhibit(tmp_path: Path) -> None:
    """R8: both implications prove and replay — the pair is one kernel-checked exhibit."""
    fake = ScriptedToolchain()
    target, ctx = equivalence_context(tmp_path, fake)
    run = qa.equivalence(ctx, "and-reassoc", date=WHEN, attempt_budget_s=30)
    assert run.ok and run.row.kind == "exhibit"
    assert run.row.exhibit == "targets/propositional/qa/exhibits/root-equivalence-1.lean"
    source = (target.parents[1] / run.row.exhibit).read_text(encoding="utf-8")
    assert "theorem OpnQa.equiv_forward" in source and "theorem OpnQa.equiv_backward" in source
    assert "(opn_subject : ∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p))" in source
    assert "kernel_replay:OpnQa.Equivalence" in fake.calls
    assert qa.pass_state(target, "root").checks["equivalence"] == "pass"


def test_equivalence_needs_a_real_other_node(tmp_path: Path) -> None:
    _, ctx = equivalence_context(tmp_path, ScriptedToolchain())
    with pytest.raises(QaError, match="not a node"):
        qa.equivalence(ctx, "ghost", date=WHEN, attempt_budget_s=30)


def test_qa_brief_and_backtranslate_commands(
    tmp_path: Path, seam: Any, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The three commands through the CLI: no key is a usage error before any work (C8); with
    the seam faked, `brief` runs sandboxed and `backtranslate` needs no toolchain at all."""
    from opn_gate import cli  # noqa: PLC0415

    root = copy_graph(tmp_path)
    take_in(root, defs=DEFS)
    argv = [
        "qa",
        "brief",
        "euclid-primes",
        "root",
        "--graph",
        str(root),
        "--sandbox",
        "--out",
        str(tmp_path / "out"),
        "--date",
        WHEN,
    ]
    monkeypatch.delenv("OPN_MODEL_API_KEY", raising=False)
    assert cli.main(argv) == cli.EXIT_ERROR
    assert "OPN_MODEL_API_KEY" in capsys.readouterr().err

    model = FakeModelClient(answer="Fine.")
    monkeypatch.setattr(cli, "_model_client", lambda _settings: model)
    seam.fake = brief_toolchain()
    assert cli.main(argv) == cli.EXIT_PASS
    doc = json.loads(capsys.readouterr().out)
    assert doc["ok"] is True and doc["check"]["check"] == "brief"
    assert seam.made[0]["read_only"] == [
        (root / "targets/euclid-primes/nodes" / ROOT_NODE).resolve()
    ]

    code = cli.main(
        ["qa", "backtranslate", "euclid-primes", "Primes", "--graph", str(root), "--date", WHEN]
    )
    doc = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_PASS and doc["check"]["check"] == "backtranslation"
    assert doc["written"] == [
        "targets/euclid-primes/qa/Primes-1.yaml",
        "targets/euclid-primes/qa/backtranslation/Primes-backtranslation-1.md",
    ]
    assert (
        cli.main(
            [
                "qa",
                "equivalence",
                "euclid-primes",
                "Primes",
                "other",
                "--graph",
                str(root),
                "--sandbox",
            ]
        )
        == cli.EXIT_ERROR
    )
