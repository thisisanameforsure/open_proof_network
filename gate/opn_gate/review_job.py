"""The formalization review's job: stages 3, 4 and 6 from a target's records (F26-R4, R6, R7,
R8, R13; D-9 v3.39).

``opn-gate review run --graph <checkout> --target <id>`` reads ``targets/<id>/review/`` and writes
into the checkout, under that directory only, the records the automated stages produce: exhibits
(``exhibits/<id>.json`` beside the Lean the kernel checked), intent tests (``tests/``), questions
(``questions/``) and pair records (``pairs/``). It writes nothing else and never edits a file: a
record already on disk is left as it is (D-3), and the review's state is derived from the set by
``review.derive`` (F08-T10's principle). Like ``review open`` it commits nothing; the caller
(the post-merge job, ``review.yml``, F26-T8) commits what was written as one bot commit.

One run, in order:

1. **Answers into tests** (T7, ``review_questions.answers_to_tests``): every answer record whose
   question names a case becomes an intent test with ``expected.source: answer``.
2. **Filter** (T5, ``filter_candidate``), for each candidate not already returned or discarded:
   the format rule (``review_format.returned_reason``: a ``format`` exhibit, *returned*, never
   discarded); the compile at the pin (a ``compile`` exhibit; ``fail`` discards); the screens —
   prove it, prove its negation, prove ``False`` from its hypotheses — each a bounded attempt (a
   ``screen`` exhibit; ``fail`` means the screen *fired*, which discards); then every intent test
   on record under its probe (an ``intent-test`` exhibit; ``fail`` discards). The first ``fail``
   ends the candidate's filter.
3. **Agreement tests** (T5, ``agreement_tests``): the small, degenerate and boundary cases the job
   proposes mechanically from the concepts (``AGREEMENT_N``, ``CONCEPT_N``: no model is called and
   none supplies a value, R6) are computed for every surviving candidate; where two or more
   survivors all agree and no test is on record for the case, a test is written with
   ``expected.source: agreement`` and run against each survivor. Where they disagree no test is
   written: the case becomes a question at step 5.
4. **Pairs** (T6, ``review_pairs.run_pairs``) between surviving candidates.
5. **Questions** (T7, ``review_questions.raise_questions``) from every refuted direction and every
   concept value two survivors disagree on, phrased as the hypothesis.
6. **Mutation** (T7, ``review_mutants.mutate``) of the surviving cluster's representative, when
   exactly one cluster survives.

**Idempotent** (R13). An exhibit's id is a function of what was asked — its kind, the candidate,
the test, the case or screen, the toolchain and the Mathlib pin — never of the answer or the run,
so a second run on the same records computes the same ids, finds them on disk, reuses their
results instead of re-running Lean, and writes nothing. A test's id is a function of its case,
expected value and source; a question is not raised twice for one case (or, for a mutant with no
case, twice for one exhibit); a pair record is written only when its directions changed. Moving
the pin gives new exhibit ids, so the tests re-run (R6). Every Lean file written was elaborated in
this run, and is exactly the text that elaborated (the 2026-09-17 lesson).

**Exhibit results** (``exhibit/v1``), as this job writes them:

- ``compile``: ``pass`` (the Lean that elaborated) or ``fail`` (no Lean: it did not elaborate; the
  first error is the detail); a candidate whose small cases cannot be computed says so in the
  ``pass`` detail ("small cases do not apply: …", R6).
- ``screen``: ``fail`` when the screen fired (the proof is the Lean), ``pass`` when the bounded
  attempt found nothing (no Lean: nothing was proved), ``error`` on a timeout.
- ``intent-test``: ``pass`` with the kernel's proof of the expected value, ``fail`` with its proof
  of the opposite, ``error`` when the kernel decides neither (decides nothing).
- ``pair``: ``proved``, ``refuted`` (an instance) or ``open`` (the degenerate guard's proof, which
  shows the conclusion holds without the hypothesis); ``test`` names the other candidate.
- ``mutant`` (F26-R8; the meaning is this module's, since ``exhibit/v1`` is pinned): ``candidate``
  is the representative the mutant was made from and ``detail`` names the mutation. ``fail`` means
  **the tests caught it** — an intent test on record fails on the mutant, and the Lean is the
  kernel's proof of that; ``pass`` means **it survived** every test and becomes a question of kind
  ``mutant`` (the Lean, when there is one, is the instance where it and the representative
  differ); ``proved`` means it was proved equivalent to the representative both ways (not a change
  of meaning; no question); ``error`` means it does not elaborate (no Lean).
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from opn_gate import review, review_format, review_lean, schemas
from opn_gate.paths import REVIEW_DIR
from opn_gate.review_lean import Cand, Case, Checked, Runner

log = logging.getLogger(__name__)

#: The degenerate and boundary cases the job proposes for every review (R6): holds and covers at
#: n = 0..3, and each concept's value at 0, 1 and 2. Chosen mechanically, the same for every
#: review; the expected value only ever comes from agreement, an answer or a citation.
AGREEMENT_N = 4
CONCEPT_N = 3
#: An agreement needs at least this many survivors: one candidate agreeing with itself is no
#: evidence of anything.
AGREEMENT_MIN = 2
#: Who the job writes as a test's author (``intent-test/v1``).
GATE = "gate"


@dataclass
class TestRec:
    id: str
    record: dict[str, Any]
    case: Case | None
    expected: bool | None


@dataclass
class Job:
    """One run's records, in memory, and what it will write."""

    graph: Path
    target: str
    head: dict[str, Any]
    concepts: list[str]
    toolchain_name: str
    mathlib_sha: str | None
    run_id: str
    date: str
    runner: Runner
    sources: dict[str, str] = field(default_factory=dict)  # candidate id -> Lean
    records: dict[str, dict[str, Any]] = field(default_factory=dict)  # candidate id -> yaml
    cands: dict[str, Cand] = field(default_factory=dict)
    tests: dict[str, TestRec] = field(default_factory=dict)
    questions: list[dict[str, Any]] = field(default_factory=list)
    answers: list[dict[str, Any]] = field(default_factory=list)
    exhibits: dict[str, dict[str, Any]] = field(default_factory=dict)
    exhibit_lean: dict[str, str] = field(default_factory=dict)
    pairs: list[dict[str, Any]] = field(default_factory=list)
    tables: dict[str, dict[str, list[bool]]] = field(default_factory=dict)
    status: dict[str, str] = field(default_factory=dict)  # candidate id -> surviving/…
    out: dict[str, bytes] = field(default_factory=dict)  # path under review/ -> bytes
    notes: list[str] = field(default_factory=list)
    raised: list[str] = field(default_factory=list)
    tests_written: list[str] = field(default_factory=list)
    mutants: dict[str, Any] = field(default_factory=dict)

    @property
    def base(self) -> Path:
        return self.graph / "targets" / self.target / REVIEW_DIR


# --- reading the records -----------------------------------------------------------------------


def _yaml_docs(folder: Path) -> list[tuple[Path, dict[str, Any]]]:
    out: list[tuple[Path, dict[str, Any]]] = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.iterdir()):
        if path.suffix not in (".yaml", ".yml"):
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(doc, dict):
            out.append((path, doc))
    return out


def _load(job: Job) -> None:
    base = job.base
    for path, doc in _yaml_docs(base / "candidates"):
        cid = str(doc.get("id"))
        lean = path.with_name(str(doc.get("lean_file") or f"{cid}.lean"))
        if not lean.is_file():
            job.notes.append(f"candidate {cid}: its Lean file is missing; not checked")
            continue
        job.records[cid] = doc
        job.sources[cid] = lean.read_text(encoding="utf-8")
    for path, doc in _yaml_docs(base / "tests"):
        tid = str(doc.get("id"))
        lean = path.with_name(str(doc.get("lean_file") or f"{tid}.lean"))
        case = review_lean.case_of(lean.read_text(encoding="utf-8")) if lean.is_file() else None
        exp = (doc.get("expected") or {}).get("value")
        expected = exp if isinstance(exp, bool) else None
        if case is None or expected is None:
            job.notes.append(
                f"test {tid}: its Lean carries no case the job can read, or its expected value "
                "is not true/false; not run"
            )
        job.tests[tid] = TestRec(tid, doc, case, expected)
    job.questions = [doc for _, doc in _yaml_docs(base / "questions")]
    job.answers = [doc for _, doc in _yaml_docs(base / "answers")]
    job.pairs = [doc for _, doc in _yaml_docs(base / "pairs")]
    folder = base / "exhibits"
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(doc, dict) and isinstance(doc.get("id"), str):
                job.exhibits[doc["id"]] = doc
                lean = path.with_suffix(".lean")
                if lean.is_file():
                    job.exhibit_lean[doc["id"]] = lean.read_text(encoding="utf-8")


# --- exhibits and tests as records -------------------------------------------------------------


def exhibit_id(  # noqa: PLR0913, PLR0917 — one argument per fact the id is a function of
    kind: str, candidate: str, test: str | None, key: str, toolchain: str, mathlib: str | None
) -> str:
    """``e-<8 hex>`` of what was asked, never of the answer: a second run asks the same and
    finds the same id (R13); a moved pin asks under another toolchain and gets a new one (R6)."""
    text = "\n".join([kind, candidate, test or "", key, toolchain, mathlib or ""])
    return "e-" + hashlib.sha256(text.encode()).hexdigest()[:8]


def find_exhibit(
    job: Job, kind: str, candidate: str, test: str | None, key: str
) -> dict[str, Any] | None:
    return job.exhibits.get(
        exhibit_id(kind, candidate, test, key, job.toolchain_name, job.mathlib_sha)
    )


def add_exhibit(  # noqa: PLR0913, PLR0917 — one argument per field of the record
    job: Job,
    kind: str,
    candidate: str,
    test: str | None,
    key: str,
    result: str,
    detail: str,
    lean: str | None,
) -> dict[str, Any]:
    """Record an exhibit (or return the one already on record for the same question)."""
    eid = exhibit_id(kind, candidate, test, key, job.toolchain_name, job.mathlib_sha)
    if eid in job.exhibits:
        return job.exhibits[eid]
    doc: dict[str, Any] = {
        "schema": "exhibit/v1",
        "target": job.target,
        "id": eid,
        "kind": kind,
        "candidate": candidate,
        "test": test,
        "result": result,
        "detail": (" ".join(detail.split()) or result)[:2000],
        "lean_file": f"{eid}.lean" if lean is not None else None,
        "toolchain": job.toolchain_name,
        "mathlib_sha": job.mathlib_sha,
        "run": job.run_id,
        "date": job.date,
    }
    schemas.validate(doc, "exhibit/v1")
    job.exhibits[eid] = doc
    job.out[f"exhibits/{eid}.json"] = schemas.canonical_json(doc)
    if lean is not None:
        job.exhibit_lean[eid] = lean
        job.out[f"exhibits/{eid}.lean"] = lean.encode("utf-8")
    return doc


def test_id(case: Case, expected: bool, source: str, ref: str) -> str:
    text = "\n".join([case.token(), str(expected).lower(), source, ref])
    return "t-" + hashlib.sha256(text.encode()).hexdigest()[:8]


def tests_by_case(job: Job) -> dict[str, list[TestRec]]:
    out: dict[str, list[TestRec]] = {}
    for t in job.tests.values():
        if t.case is not None:
            out.setdefault(t.case.token(), []).append(t)
    return out


def add_test(job: Job, case: Case, expected: bool, source: str, ref: str) -> TestRec | None:
    """Write an intent test (its record and its Lean, the Lean elaborated first) unless one with
    the same id is on record; ``None`` when its Lean does not elaborate (nothing is written)."""
    tid = test_id(case, expected, source, ref)
    if tid in job.tests:
        return job.tests[tid]
    text = review_lean.test_text(tid, case, expected, source, ref)
    checked = job.runner.check(text)
    if not checked.ok:
        job.notes.append(f"test {tid}: its own Lean did not elaborate ({checked.first_error})")
        return None
    doc = {
        "schema": "intent-test/v1",
        "target": job.target,
        "id": tid,
        "case": case.words(),
        "probe": case.probe,
        "concept": case.concept,
        "expected": {"value": expected, "source": source, "ref": ref},
        "author": GATE,
        "lean_file": f"{tid}.lean",
        "date": job.date,
    }
    schemas.validate(doc, "intent-test/v1")
    job.out[f"tests/{tid}.yaml"] = _yaml_bytes(doc)
    job.out[f"tests/{tid}.lean"] = text.encode("utf-8")
    rec = TestRec(tid, doc, case, expected)
    job.tests[tid] = rec
    job.tests_written.append(tid)
    return rec


def _yaml_bytes(doc: dict[str, Any]) -> bytes:
    text: str = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    return text.encode("utf-8")


# --- one candidate's filter (stage 3) ----------------------------------------------------------


def probe_value(case: Case, expected: bool) -> bool:
    """The truth of the claim *under the probe* that an expected answer means: for ``covers`` the
    expectation is "the conjecture says something at n", which holds exactly when the claim with
    every concept made empty fails there; for every other probe it is the value itself."""
    return not expected if case.probe == "covers" else expected


def run_test(job: Job, c: Cand, test: TestRec) -> str:
    """One intent test against one candidate: ``pass``, ``fail`` or ``error`` (an exhibit)."""
    found = find_exhibit(job, "intent-test", c.id, test.id, "intent-test")
    if found is not None:
        return str(found["result"])
    case, expected = test.case, test.expected
    if case is None or expected is None:
        return "error"
    why = applies(c, case)
    if why is not None:
        add_exhibit(job, "intent-test", c.id, test.id, "intent-test", "error", why, None)
        return "error"
    value = probe_value(case, expected)
    text = review_lean.decide_text(c, case, value)
    if job.runner.check(text).ok:
        add_exhibit(
            job,
            "intent-test",
            c.id,
            test.id,
            "intent-test",
            "pass",
            f"{case.words()} — agrees with the expected {_yes(expected)} ({_source(test)})",
            text,
        )
        return "pass"
    opposite = review_lean.decide_text(c, case, not value)
    checked = job.runner.check(opposite)
    if checked.ok:
        add_exhibit(
            job,
            "intent-test",
            c.id,
            test.id,
            "intent-test",
            "fail",
            f"{case.words()} — the expected answer is {_yes(expected)} ({_source(test)}); "
            "the kernel shows this candidate says the opposite",
            opposite,
        )
        return "fail"
    add_exhibit(
        job,
        "intent-test",
        c.id,
        test.id,
        "intent-test",
        "error",
        f"{case.words()} — the kernel decided neither way: {checked.first_error[:300]}",
        None,
    )
    return "error"


def applies(c: Cand, case: Case) -> str | None:
    """Why a case cannot be asked of a candidate, or ``None``."""
    if not c.indexed:
        return c.why_no_cases or "small cases do not apply"
    if case.probe == "concept" and case.concept not in c.predicates:
        return f"the candidate has no predicate on one natural number for `{case.concept}`"
    if case.probe == "witness" and case.concept not in c.predicates:
        return f"the candidate has no predicate on one natural number for `{case.concept}`"
    if case.probe == "covers" and not c.predicates:
        return "the candidate names no concept predicate the covers probe can empty"
    return None


def _yes(value: bool) -> str:
    return "yes" if value else "no"


def _source(test: TestRec) -> str:
    exp = test.record.get("expected") or {}
    return f"{exp.get('source')}: {exp.get('ref')}"


def survey(job: Job, c: Cand) -> dict[str, list[bool]]:
    """The candidate's tables (a search for cases, never evidence): every row, else without the
    witness rows, else holds alone; empty when nothing computes."""
    if c.id in job.tables:
        return job.tables[c.id]
    tables: dict[str, list[bool]] = {}
    if c.indexed:
        for witness in (True, False):
            rows = review_lean.survey_rows(c, witness=witness)
            checked = job.runner.check(review_lean.survey_text(c, rows))
            if checked.ok:
                tables = review_lean.parse_tables(list(checked.messages))
                break
        else:
            rows = review_lean.survey_rows(c, witness=False)[:1]
            checked = job.runner.check(review_lean.survey_text(c, rows))
            if checked.ok:
                tables = review_lean.parse_tables(list(checked.messages))
    job.tables[c.id] = tables
    return tables


def _fate(job: Job, cid: str) -> str | None:
    """``returned`` or ``discarded`` when an exhibit on record already decided the candidate."""
    mine = [e for e in job.exhibits.values() if e.get("candidate") == cid]
    if any(review.returns(e) for e in mine):
        return review.RETURNED
    if any(review.discards(e) for e in mine):
        return review.DISCARDED
    return None


def filter_candidate(job: Job, cid: str) -> str:  # noqa: PLR0911 — one return per stage
    """Stage 3 for one candidate (R4, R5): its fate after this run."""
    fate = _fate(job, cid)
    if fate is not None:
        return fate
    source = job.sources[cid]
    reason = review_format.returned_reason(source, job.concepts)
    if reason is not None:
        doc = review_format.format_exhibit(
            cid,
            reason,
            target=job.target,
            toolchain=job.toolchain_name,
            mathlib_sha=job.mathlib_sha,
            run=job.run_id,
            date=job.date,
        )
        if doc["id"] not in job.exhibits:
            job.exhibits[str(doc["id"])] = dict(doc)
            job.out[f"exhibits/{doc['id']}.json"] = schemas.canonical_json(dict(doc))
        return review.RETURNED
    prepared = review_lean.prepare(cid, source, job.concepts)
    if isinstance(prepared, str):
        add_exhibit(job, "compile", cid, None, "compile", "error", prepared, None)
        return review.SURVIVING
    c = prepared
    job.cands[cid] = c
    if _compile(job, c) != "pass":
        return review.DISCARDED if _fate(job, cid) == review.DISCARDED else review.SURVIVING
    tables = survey(job, c)
    for which in ("statement", "negation", "false"):
        if _screen(job, c, which, tables) == "fail":
            return review.DISCARDED
    for tid in sorted(job.tests):
        if run_test(job, c, job.tests[tid]) == "fail":
            return review.DISCARDED
    return review.SURVIVING


def _compile(job: Job, c: Cand) -> str:
    found = find_exhibit(job, "compile", c.id, None, "compile")
    if found is not None:
        return str(found["result"])
    text = review_lean.compile_text(c)
    checked = job.runner.check(text, allowed_sorry=1 if c.theorem_shape else 0)
    if checked.error is not None:
        add_exhibit(job, "compile", c.id, None, "compile", "error", checked.error, None)
        return "error"
    if not checked.ok:
        detail = f"does not elaborate at the pin: {checked.first_error[:400]}"
        add_exhibit(job, "compile", c.id, None, "compile", "fail", detail, None)
        return "fail"
    notes = ["elaborates at the pin"]
    if c.why_no_cases:
        notes.append(c.why_no_cases)
    elif c.indexed and not survey(job, c):
        notes.append("small cases do not apply: the claim is not decidable at a given n")
    if c.not_probed:
        notes.append(
            "no predicate on one natural number for "
            + ", ".join(f"`{x}`" for x in c.not_probed)
            + ", so the covers and witness probes do not reach it"
        )
    add_exhibit(job, "compile", c.id, None, "compile", "pass", "; ".join(notes), text)
    return "pass"


def _screen(job: Job, c: Cand, which: str, tables: dict[str, list[bool]]) -> str:
    key = f"screen:{which}"
    found = find_exhibit(job, "screen", c.id, None, key)
    if found is not None:
        return str(found["result"])
    text: str | None
    if which == "negation":
        holds = tables.get("holds")
        k = next((n for n, v in enumerate(holds or []) if not v), None)
        text = review_lean.negation_text(c, k)
        if text is None:
            what = (
                f"no counterexample among n ≤ {review_lean.TABLE_N}"
                if c.indexed
                else (c.why_no_cases or "nothing to try")
            )
            add_exhibit(job, "screen", c.id, None, key, "pass", f"negation: {what}", None)
            return "pass"
    else:
        text = review_lean.screen_texts(c)[which]
        if text is None:
            add_exhibit(job, "screen", c.id, None, key, "pass", f"{which}: {c.why_no_cases}", None)
            return "pass"
    checked: Checked = job.runner.check(text)
    label = {
        "statement": "the claim was proved for every n",
        "negation": "the claim's negation was proved",
        "false": "False was proved from the claim's hypotheses (they are contradictory)",
    }[which]
    if checked.ok:
        add_exhibit(
            job,
            "screen",
            c.id,
            None,
            key,
            "fail",
            f"{which}: {label} within the bounded budget, so the candidate is not the open "
            "conjecture as stated",
            text,
        )
        return "fail"
    if checked.error is not None:
        add_exhibit(job, "screen", c.id, None, key, "error", f"{which}: {checked.error}", None)
        return "error"
    add_exhibit(
        job, "screen", c.id, None, key, "pass", f"{which}: nothing proved within the budget", None
    )
    return "pass"


# --- agreement tests (R6) ----------------------------------------------------------------------


def agreement_cases(concepts: list[str]) -> list[Case]:
    cases = [Case("holds", n) for n in range(AGREEMENT_N)]
    cases += [Case("covers", n) for n in range(AGREEMENT_N)]
    cases += [Case("concept", x, None, k) for k in concepts for x in range(CONCEPT_N)]
    return cases


def table_value(tables: dict[str, list[bool]], case: Case) -> bool | None:
    """A case's expected-answer value from a candidate's tables (``covers`` read as "says
    something"), or ``None`` when the table does not reach it."""
    if case.probe == "concept":
        row = tables.get(f"concept:{case.concept}")
    elif case.probe == "witness":
        row = None
        for i, s in enumerate(review_lean.witness_sets()):
            if s == case.set:
                row = tables.get(f"witness:{case.concept}:{i}")
    else:
        row = tables.get(case.probe)
    if row is None or case.n >= len(row):
        return None
    return (not row[case.n]) if case.probe == "covers" else row[case.n]


def agreement_tests(job: Job, survivors: list[str]) -> None:
    """Write a test for every proposed case on which two or more survivors agree and no test is
    on record; run it against each survivor. Disagreements write nothing here (stage 5)."""
    indexed = [job.cands[c] for c in survivors if c in job.cands and job.cands[c].indexed]
    if len(indexed) < AGREEMENT_MIN or len(indexed) != len(survivors):
        return
    on_record = tests_by_case(job)
    for case in agreement_cases(job.concepts):
        if case.token() in on_record:
            continue
        if any(applies(c, case) is not None for c in indexed):
            continue
        values = {table_value(survey(job, c), case) for c in indexed}
        if len(values) != 1 or None in values:
            continue
        expected = values.pop()
        assert expected is not None
        rec = add_test(job, case, expected, "agreement", f"agreement:{len(indexed)}")
        if rec is None:
            continue
        for c in indexed:
            run_test(job, c, rec)


# --- the run -----------------------------------------------------------------------------------


@dataclass
class Settings:
    """What a run is told: where it ran, the day, the budget per attempt and the parallelism."""

    run_id: str = "local"
    date: str = ""
    budget_s: float = 60.0
    jobs: int = 4
    mutant_cap: int = 200


def open_job(
    graph: Path, target_id: str, runner: Runner, spec: dict[str, Any], settings: Settings
) -> Job | str:
    target_dir = graph / "targets" / target_id
    head = review.opening(target_dir)
    if head is None:
        return f"targets/{target_id} has no review (review/review.yaml)"
    concepts = [str(x) for x in head.get("concepts") or []]
    job = Job(
        graph=graph,
        target=target_id,
        head=head,
        concepts=concepts,
        toolchain_name=str(spec["lean_toolchain"]),
        mathlib_sha=spec.get("mathlib_sha"),
        run_id=settings.run_id,
        date=settings.date,
        runner=runner,
    )
    _load(job)
    return job


def run(job: Job, settings: Settings) -> dict[str, Any]:
    """Stages 3, 4 and 6 over the job's records; returns the summary (nothing written yet)."""
    from opn_gate import review_mutants, review_pairs, review_questions  # noqa: PLC0415

    review_questions.answers_to_tests(job)
    for cid in sorted(job.sources):
        job.status[cid] = filter_candidate(job, cid)
    answer_tests_everywhere(job)
    survivors = [c for c in sorted(job.status) if job.status[c] == review.SURVIVING]
    agreement_tests(job, survivors)
    for cid in survivors:  # an agreement test a survivor failed (the kernel against the table)
        if _fate(job, cid) == review.DISCARDED:
            job.status[cid] = review.DISCARDED
    survivors = [c for c in sorted(job.status) if job.status[c] == review.SURVIVING]
    pair_docs = review_pairs.run_pairs(job, survivors)
    review_questions.raise_questions(job, survivors, pair_docs)
    clusters = review.components(
        set(survivors),
        [(str(p["a"]), str(p["b"])) for p in pair_docs if review.equivalent(p)],
    )
    if len(clusters) == 1 and clusters[0]:
        rep = representative(job, clusters[0])
        if rep is not None:
            job.mutants = review_mutants.mutate(job, job.cands[rep], cap=settings.mutant_cap)
    elif len(clusters) > 1:
        job.notes.append(f"{len(clusters)} clusters survive; mutation waits for one (R8)")
    return {
        "target": job.target,
        "candidates": dict(sorted(job.status.items())),
        "clusters": clusters,
        "tests_written": job.tests_written,
        "questions_raised": job.raised,
        "mutants": job.mutants,
        "elaborations": job.runner.count,
        "notes": job.notes,
    }


def prepared(job: Job, cid: str) -> Cand | None:
    """The candidate's shape, prepared once (``None`` for one the job cannot read)."""
    if cid not in job.cands:
        got = review_lean.prepare(cid, job.sources[cid], job.concepts)
        if isinstance(got, str):
            return None
        job.cands[cid] = got
    return job.cands[cid]


def answer_tests_everywhere(job: Job) -> None:
    """An ``answer`` test re-runs against every candidate that compiled, the discarded ones too
    (F26-AC7): the signers see how the answer splits all of them, not only the survivors."""
    for tid in sorted(job.tests):
        t = job.tests[tid]
        if (t.record.get("expected") or {}).get("source") != "answer":
            continue
        for cid in sorted(job.sources):
            compiled = find_exhibit(job, "compile", cid, None, "compile")
            if compiled is None or compiled.get("result") != "pass":
                continue
            c = prepared(job, cid)
            if c is not None:
                run_test(job, c, t)


def representative(job: Job, cluster: list[str]) -> str | None:
    """The cluster's representative: a person's candidate when one is in it (the smallest id),
    else the smallest id; ``None`` when it was not prepared (nothing to mutate)."""
    people = [c for c in cluster if review.is_person(job.records.get(c, {}))]
    pick = sorted(people or cluster)[0]
    return pick if pick in job.cands else None


def write(job: Job) -> list[str]:
    """Write what the run produced under ``review/``; a file already on disk is never touched
    (append-only, D-3). Returns the paths written, from the graph root."""
    written: list[str] = []
    for rel in sorted(job.out):
        path = job.base / rel
        data = job.out[rel]
        if path.exists():
            if path.read_bytes() != data:
                job.notes.append(f"{rel}: on record with other content; left as it is")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        written.append(path.relative_to(job.graph).as_posix())
    return written


def review_run(
    graph: Path, target_id: str, runner: Runner, spec: dict[str, Any], settings: Settings
) -> dict[str, Any]:
    """Open, run and write; the summary names every path written (empty on a second run)."""
    job = open_job(graph, target_id, runner, spec, settings)
    if isinstance(job, str):
        return {"target": target_id, "ok": False, "error": job, "written": []}
    summary = run(job, settings)
    summary["written"] = write(job)
    summary["ok"] = True
    return summary
