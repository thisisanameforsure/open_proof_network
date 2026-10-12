"""The formalization review's questions, and answers into tests (F26-R6, R7; D-9 v3.39; the
amendment draft §2, §9 point 5).

**Questions.** Each refuted direction between two surviving candidates is a proved disagreement:
a case where one candidate's claim holds and the other's fails, checked by the kernel. It becomes
a question to the intent signer (``review-question/v1``, kind ``disagreement``), and each concept
value two survivors' predicates disagree on becomes one of kind ``concept`` ("Is 1 prime, in the
sense the conjecture means?"). A surviving mutant raises one of kind ``mutant``
(``review_mutants``). The question is in mathematics, never Lean, and phrased as the hypothesis the
probe tests ("Suppose 5 were the only prime. Would the conjecture be satisfied at n = 2?"): the
prototype's "would a prime at 5 count?" invited the opposite answer (§9 point 5). Its
``raised_by.ref`` is the exhibit that raised it, whose Lean carries the case in its header
(``review_lean.case_of``). No case is asked twice: not when a test is on record for it, not when a
question about it exists (answered or not). Questions are numbered ``q-<n>`` after the highest on
record.

**Answers into tests.** An answer record (``review-answer/v1``) names its question; the job reads
the case from the question's exhibit and the value from the answer's words, which begin with *yes*
or *no* (the question is a yes/no question by construction), and writes an intent test with
``expected.source: answer`` and ``expected.ref`` the answer's id. The question is then closed by
the answer itself (``review.questions_waiting``); the test runs against every candidate in the same
run, and a candidate it fails is discarded. An answer whose words begin with neither, or whose
question names no case (a mutant question with no differing case), writes no test, and the run's
notes say so. No model reads an answer; the parse is the first word.
"""

from __future__ import annotations

import re
from typing import Any

from opn_gate import review_lean, schemas
from opn_gate.review_job import Job, _yaml_bytes, add_test, tests_by_case
from opn_gate.review_lean import Case

_YES = {"yes", "y", "true"}
_NO = {"no", "n", "false"}
_QID_RE = re.compile(r"^q-(\d+)$")


def yes_no(answer: str) -> bool | None:
    """The value an answer's words give: ``True`` for an answer that begins *yes*, ``False`` for
    *no*, else ``None``."""
    m = re.match(r"\s*([A-Za-z]+)", answer)
    if not m:
        return None
    word = m.group(1).lower()
    if word in _YES:
        return True
    if word in _NO:
        return False
    return None


def case_of_question(job: Job, question: dict[str, Any]) -> Case | None:
    raised = question.get("raised_by") or {}
    ref = str(raised.get("ref") or "")
    lean = job.exhibit_lean.get(ref)
    return review_lean.case_of(lean) if lean is not None else None


def answers_to_tests(job: Job) -> None:
    """Every answer whose question names a case becomes an ``answer`` test (R7)."""
    by_id = {str(q.get("id")): q for q in job.questions}
    for answer in sorted(job.answers, key=lambda a: str(a.get("id"))):
        aid = str(answer.get("id"))
        question = by_id.get(str(answer.get("question")))
        if question is None:
            job.notes.append(f"answer {aid}: its question is not on record; no test")
            continue
        case = case_of_question(job, question)
        if case is None:
            job.notes.append(
                f"answer {aid}: question {question.get('id')} names no case the job can test; "
                "no test (the signers read the answer)"
            )
            continue
        value = yes_no(str(answer.get("answer") or ""))
        if value is None:
            job.notes.append(f"answer {aid}: its words begin with neither yes nor no; no test")
            continue
        add_test(job, case, value, "answer", aid)


def _next_number(job: Job) -> int:
    nums = [int(m.group(1)) for q in job.questions if (m := _QID_RE.match(str(q.get("id"))))]
    return max(nums, default=0) + 1


def asked_cases(job: Job) -> set[str]:
    """The case tokens already settled or already asked: every test's case, and every question's
    (through its exhibit)."""
    out = set(tests_by_case(job))
    for q in job.questions:
        case = case_of_question(job, q)
        if case is not None:
            out.add(case.token())
    return out


def add_question(job: Job, text: str, kind: str, ref: str, case: Case | None) -> str | None:
    """Queue one question unless its case (or, with no case, its exhibit) was asked before."""
    if case is not None:
        if case.token() in asked_cases(job):
            return None
    elif any((q.get("raised_by") or {}).get("ref") == ref for q in job.questions):
        return None
    qid = f"q-{_next_number(job)}"
    doc = {
        "schema": "review-question/v1",
        "target": job.target,
        "id": qid,
        "question": text,
        "raised_by": {"kind": kind, "ref": ref},
        "asked_to": "intent",
        "date": job.date,
    }
    schemas.validate(doc, "review-question/v1")
    job.questions.append(doc)
    job.out[f"questions/{qid}.yaml"] = _yaml_bytes(doc)
    job.raised.append(qid)
    return qid


def raise_questions(job: Job, survivors: list[str], pair_docs: list[dict[str, Any]]) -> None:
    """A question for every refuted direction between survivors and every concept value their
    predicates disagree on (R7)."""
    from opn_gate import review_pairs  # noqa: PLC0415 — the pairs module imports this one's peer

    alive = set(survivors)
    for p in pair_docs:
        if str(p.get("a")) not in alive or str(p.get("b")) not in alive:
            continue
        for direction in ("forward", "backward"):
            d = p.get(direction) or {}
            if d.get("state") != "refuted" or not d.get("exhibit"):
                continue
            ref = str(d["exhibit"])
            case = review_lean.case_of(job.exhibit_lean.get(ref, ""))
            if case is None:
                continue
            add_question(job, case.question(), "disagreement", ref, case)
    ids = [c for c in sorted(survivors) if c in job.cands]
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            ca, cb = job.cands[a], job.cands[b]
            for concept in sorted(set(ca.predicates) & set(cb.predicates)):
                for x, y in ((ca, cb), (cb, ca)):
                    found = review_pairs.concept_instance(job, x, y, concept)
                    if found is None:
                        continue
                    lean = job.exhibit_lean.get(str(found["id"]), "")
                    case = review_lean.case_of(lean)
                    if case is not None:
                        add_question(job, case.question(), "concept", str(found["id"]), case)
