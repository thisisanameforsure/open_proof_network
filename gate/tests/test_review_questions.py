"""F26-T7: questions from disagreements and mutants; answers into tests (R6, R7, R8; AC7).

Fast tier, the toolchain seam's fake (``review_support.ReviewFake``). The disagreement is the first
prototype's: Legendre's conjecture read faithfully and read as asking for two primes (``bad-two``,
strength drift). Every small case agrees; only the witness probe tells them apart, at n = 1 with 2
the only prime, which is the question the prototype's proposer was asked.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from review_support import (
    Model,
    ReviewFake,
    add_answer,
    add_test_record,
    candidate_id,
    legendre,
    make_graph,
    prototype_lean,
    tree,
)
from test_review_job import TARGET, exhibits, run_job

from opn_gate import review, review_job, review_lean, review_questions

WITNESS_2 = review_lean.Case("witness", 1, (2,), "prime")


def questions(graph: Path) -> list[dict[str, Any]]:
    folder = graph / "targets" / TARGET / "review" / "questions"
    return [yaml.safe_load(p.read_text()) for p in sorted(folder.glob("*.yaml"))]


def recorded_tests(graph: Path) -> list[dict[str, Any]]:
    folder = graph / "targets" / TARGET / "review" / "tests"
    return [yaml.safe_load(p.read_text()) for p in sorted(folder.glob("*.yaml"))]


def drift(tmp_path: Path) -> tuple[Path, dict[str, str], ReviewFake]:
    graph, ids = make_graph(
        tmp_path,
        candidates={
            "faithful": prototype_lean("legendre", "human-ref"),
            "two": prototype_lean("legendre", "bad-two"),
        },
        people=("faithful",),
    )
    a, b = ids["faithful"], ids["two"]
    fake = ReviewFake(
        models={a: Model(legendre()), b: Model(legendre(two=True))},
        implies={(b, a)},  # asking for two primes implies asking for one
    )
    return graph, ids, fake


def test_a_disagreement_writes_no_test_and_one_question(tmp_path: Path) -> None:
    graph, ids, fake = drift(tmp_path)
    summary = run_job(graph, fake, tmp_path)
    assert summary["candidates"] == {
        ids["faithful"]: review.SURVIVING,
        ids["two"]: review.SURVIVING,
    }
    (q,) = questions(graph)
    assert q["id"] == "q-1" and q["raised_by"]["kind"] == "disagreement"
    assert q["question"] == (
        "Suppose 2 were the only prime. Would the conjecture be satisfied at n = 1?"
    )
    # its ref is the kernel's instance of the disagreement, and the instance carries the case
    ref = q["raised_by"]["ref"]
    lean = (graph / "targets" / TARGET / "review" / "exhibits" / f"{ref}.lean").read_text()
    assert review_lean.case_of(lean) == WITNESS_2
    # no test was written for the case they disagree on (only the cases they agree on)
    written = [t for t in recorded_tests(graph) if t["probe"] == "witness"]
    assert written == []
    assert review.questions_waiting(graph / "targets" / TARGET)[0]["id"] == "q-1"


def test_ac7_an_answer_becomes_a_test_and_the_next_run_discards(tmp_path: Path) -> None:
    graph, ids, fake = drift(tmp_path)
    run_job(graph, fake, tmp_path)
    add_answer(graph, TARGET, "q-1", "Yes: with 2 the only prime, 2 lies strictly between 1 and 4.")
    second = run_job(graph, fake, tmp_path)
    answered = [t for t in recorded_tests(graph) if t["expected"]["source"] == "answer"]
    assert len(answered) == 1
    t = answered[0]
    assert (t["probe"], t["concept"], t["expected"]["value"], t["expected"]["ref"]) == (
        "witness",
        "prime",
        True,
        "a-1",
    )
    assert t["author"] == "gate"
    # it re-ran against every candidate: the drift fails it and is discarded, the faithful passes
    runs = {e["candidate"]: e["result"] for e in exhibits(graph) if e["test"] == t["id"]}
    assert runs == {ids["faithful"]: "pass", ids["two"]: "fail"}
    assert second["candidates"][ids["two"]] == review.DISCARDED
    assert second["candidates"][ids["faithful"]] == review.SURVIVING
    # the question is closed, and no new question was raised about the same case
    assert review.questions_waiting(graph / "targets" / TARGET) == []
    assert [q["id"] for q in questions(graph)] == ["q-1"]
    derived = review.derive(graph / "targets" / TARGET)
    assert {c["id"]: c["status"] for c in derived["candidates"]} == second["candidates"]
    before = tree(graph)
    third = run_job(graph, fake, tmp_path)
    assert third["written"] == [] and tree(graph) == before


def test_an_answer_test_reruns_against_a_candidate_already_discarded(tmp_path: Path) -> None:
    """AC7's "re-runs against every candidate": a candidate discarded earlier is still run."""
    graph, ids, fake = drift(tmp_path)
    extra = prototype_lean("legendre", "bad-zero")
    cid = candidate_id(extra)
    base = graph / "targets" / TARGET / "review" / "candidates"
    doc = yaml.safe_load((base / f"{ids['two']}.yaml").read_text())
    doc.update(id=cid, lean_file=f"{cid}.lean", author="zero")
    (base / f"{cid}.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
    (base / f"{cid}.lean").write_text(extra)
    fake.models[cid] = Model(legendre(lo=0))
    run_job(graph, fake, tmp_path)
    add_answer(graph, TARGET, "q-1", "yes")
    run_job(graph, fake, tmp_path)
    (t,) = [t for t in recorded_tests(graph) if t["expected"]["source"] == "answer"]
    ran = {e["candidate"] for e in exhibits(graph) if e["test"] == t["id"]}
    assert cid in ran


def test_an_answer_that_is_neither_yes_nor_no_writes_no_test(tmp_path: Path) -> None:
    graph, _ids, fake = drift(tmp_path)
    run_job(graph, fake, tmp_path)
    add_answer(graph, TARGET, "q-1", "It depends on what you mean by between.")
    summary = run_job(graph, fake, tmp_path)
    assert [t for t in recorded_tests(graph) if t["expected"]["source"] == "answer"] == []
    assert any("neither yes nor no" in n for n in summary["notes"])


def test_yes_no() -> None:
    assert review_questions.yes_no("Yes.") is True
    assert review_questions.yes_no("  no — 1 is not prime") is False
    assert review_questions.yes_no("Nope") is None
    assert review_questions.yes_no("") is None


def test_a_concept_disagreement_is_a_concept_question(tmp_path: Path) -> None:
    graph, ids = make_graph(
        tmp_path,
        target=TARGET,
        candidates={
            "faithful": prototype_lean("legendre", "human-ref"),
            "mul": prototype_lean("legendre", "alt-mul"),
        },
    )
    a, b = ids["faithful"], ids["mul"]
    fake = ReviewFake(
        models={
            a: Model(legendre()),
            b: Model(
                legendre(), prime=lambda p: p == 1 or (p >= 2 and all(p % d for d in range(2, p)))
            ),
        },
        implies={(a, b), (b, a)},
    )
    run_job(graph, fake, tmp_path)
    found = [q for q in questions(graph) if q["raised_by"]["kind"] == "concept"]
    assert [q["question"] for q in found] == ["Is 1 prime, in the sense the conjecture means?"]


def test_a_mutant_every_test_passes_becomes_a_question(tmp_path: Path) -> None:
    """R8: a mutant that survives the tests and differs from the representative at a case raises
    that case; one the tests catch is a ``fail`` exhibit and asks nothing."""
    graph, ids = make_graph(
        tmp_path,
        candidates={"faithful": prototype_lean("legendre", "human-ref")},
        people=("faithful",),
    )
    a = ids["faithful"]
    add_test_record(
        graph, TARGET, review_lean.Case("covers", 0), False, "citation", "0 is not positive"
    )
    found, _ = __import__("opn_gate.review_mutants", fromlist=["mutants"]).mutants(
        review_lean.prepare(a, prototype_lean("legendre", "human-ref"), ["prime"]), ["prime"]
    )
    closed = next(i for i, m in enumerate(found) if m.label.startswith("< → ≤"))
    dropped = next(i for i, m in enumerate(found) if m.cls == "hypothesis")
    fake = ReviewFake(
        models={a: Model(legendre())},
        mutant_models={closed: Model(legendre(closed=True)), dropped: Model(legendre(lo=0))},
    )
    summary = run_job(graph, fake, tmp_path)
    m = summary["mutants"]
    by_index = {r["label"]: r["result"] for r in m["results"]}
    assert by_index[found[closed].label] == "pass"
    assert by_index[found[dropped].label] == "fail"
    assert m["caught"] == 1 and m["survived"] == 1
    assert m["not_elaborating"] == m["total"] - 2
    (q,) = [q for q in questions(graph) if q["raised_by"]["kind"] == "mutant"]
    assert q["question"].startswith("Suppose ")
    lean = graph / "targets" / TARGET / "review" / "exhibits" / f"{q['raised_by']['ref']}.lean"
    assert review_lean.case_of(lean.read_text()) is not None
    # the mutation's exhibits are on record and a second run asks nothing again
    assert run_job(graph, fake, tmp_path)["written"] == []


def test_the_mutant_cap_is_recorded(tmp_path: Path) -> None:
    graph, ids = make_graph(
        tmp_path, candidates={"faithful": prototype_lean("legendre", "human-ref")}
    )
    fake = ReviewFake(models={ids["faithful"]: Model(legendre())})
    summary = run_job(graph, fake, tmp_path, mutant_cap=3)
    assert summary["mutants"]["capped"] is True
    assert summary["mutants"]["total"] == 3


def test_question_numbers_follow_the_record(tmp_path: Path) -> None:
    graph, _ids, fake = drift(tmp_path)
    qdir = graph / "targets" / TARGET / "review" / "questions"
    qdir.mkdir(parents=True)
    (qdir / "q-7.yaml").write_text(
        yaml.safe_dump(
            {
                "schema": "review-question/v1",
                "target": TARGET,
                "id": "q-7",
                "question": "Is the conjecture about every n?",
                "raised_by": {"kind": "signer", "ref": "signatures/intent-2026-10-12-1"},
                "asked_to": "intent",
                "date": "2026-10-12",
            }
        )
    )
    summary = run_job(graph, fake, tmp_path)
    assert summary["questions_raised"] == ["q-8"]
    assert json.dumps(summary)  # serialisable
    assert review_job.GATE == "gate"
