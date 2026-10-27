"""F26-T18: a later pair record supersedes an earlier one, on reload and in ``review.derive``.

The job writes a pair's first record as ``<a>--<b>.yaml`` and every later one as
``<a>--<b>--<date>-<k>.yaml`` with ``k`` from 2. By file name the later ones sort *before* the
first (``-`` < ``.``) and ``-10`` before ``-2``, and a same-date tie used to be broken by file
order, so on reload the older record won. A contributor's settled direction (R8) makes a second
record on the same day the ordinary case (erdos-849's pair record is dated 2026-10-26). The rule
now: a record's place is its ``date``, then its generation ``k`` read from the name (1 for the
first), then its name; the last in that order is in force. Every published name stays readable
(D-34), and nothing is renamed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from fakes import FAKE_RESOLVED
from review_support import Model, ReviewFake, legendre, make_graph, prototype_lean

from opn_gate import review, review_job, review_lean, review_pairs

TARGET = "legendre"
DAY = "2026-10-26"


def direction(state: str) -> dict[str, Any]:
    if state == "open":
        return {
            "state": "open",
            "exhibit": None,
            "attempt": {"who": "gate", "tool": review_pairs.TOOL, "budget_s": 5},
        }
    return {"state": state, "exhibit": "e-00000000", "attempt": None}


def pair_doc(a: str, b: str, forward: str, backward: str, date: str = DAY) -> dict[str, Any]:
    return {
        "schema": "pair/v1",
        "target": TARGET,
        "a": a,
        "b": b,
        "forward": direction(forward),
        "backward": direction(backward),
        "date": date,
    }


def setup(tmp_path: Path) -> tuple[Path, str, str]:
    graph, ids = make_graph(
        tmp_path,
        candidates={
            "faithful": prototype_lean("legendre", "human-ref"),
            "other": prototype_lean("legendre", "alt-mul"),
        },
    )
    a, b = sorted(ids.values())
    return graph, a, b


def put(graph: Path, name: str, doc: dict[str, Any]) -> None:
    folder = graph / "targets" / TARGET / "review" / "pairs"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def base(graph: Path) -> Path:
    return graph / "targets" / TARGET / "review"


def compiled(graph: Path, *cids: str) -> None:
    """A passing compile exhibit for each candidate, so ``derive`` counts it as surviving."""
    folder = base(graph) / "exhibits"
    folder.mkdir(parents=True, exist_ok=True)
    for cid in cids:
        doc = {
            "schema": "exhibit/v1",
            "target": TARGET,
            "id": f"e-{cid[2:]}",
            "kind": "compile",
            "candidate": cid,
            "test": None,
            "result": "pass",
            "detail": "elaborates at the pin",
            "lean_file": None,
            "toolchain": "leanprover/lean4:v4.33.1",
            "mathlib_sha": None,
            "run": "local",
            "date": DAY,
        }
        (folder / f"e-{cid[2:]}.json").write_text(json.dumps(doc), encoding="utf-8")


def job_of(graph: Path, tmp_path: Path) -> review_job.Job:
    spec = json.loads((graph / "targets" / TARGET / "gate-spec.json").read_text())
    runner = review_lean.Runner(ReviewFake(), FAKE_RESOLVED, tmp_path / "work", budget_s=5, jobs=1)
    job = review_job.open_job(graph, TARGET, runner, spec, review_job.Settings(date=DAY))
    assert isinstance(job, review_job.Job), job
    return job


# --- the red cases ------------------------------------------------------------------------------


def test_a_second_record_on_the_same_day_supersedes_the_first_in_derive(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    compiled(graph, a, b)
    put(graph, f"{a}--{b}.yaml", pair_doc(a, b, "open", "open"))
    put(graph, f"{a}--{b}--{DAY}-2.yaml", pair_doc(a, b, "proved", "proved"))
    (p,) = review.latest_pairs(base(graph))
    assert p["forward"]["state"] == "proved"
    assert review.derive(graph / "targets" / TARGET)["clusters"] == [[a, b]]
    assert review.open_pairs(graph / "targets" / TARGET) == []


def test_generation_ten_supersedes_generation_two(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    put(graph, f"{a}--{b}.yaml", pair_doc(a, b, "open", "open"))
    put(graph, f"{a}--{b}--{DAY}-2.yaml", pair_doc(a, b, "open", "refuted"))
    put(graph, f"{a}--{b}--{DAY}-10.yaml", pair_doc(a, b, "proved", "refuted"))
    (p,) = review.latest_pairs(base(graph))
    assert (p["forward"]["state"], p["backward"]["state"]) == ("proved", "refuted")


def test_the_job_reloads_the_newer_record(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    put(graph, f"{a}--{b}.yaml", pair_doc(a, b, "open", "open"))
    put(graph, f"{a}--{b}--{DAY}-2.yaml", pair_doc(a, b, "proved", "open"))
    job = job_of(graph, tmp_path)
    held = review_pairs.latest(job, a, b)
    assert held is not None and held["forward"]["state"] == "proved"


# --- the rule's other edges ---------------------------------------------------------------------


def test_a_later_date_wins_whatever_the_generation(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    put(graph, f"{a}--{b}--2026-10-01-9.yaml", pair_doc(a, b, "open", "open", "2026-10-01"))
    put(graph, f"{a}--{b}--2026-10-02-2.yaml", pair_doc(a, b, "proved", "open", "2026-10-02"))
    (p,) = review.latest_pairs(base(graph))
    assert p["date"] == "2026-10-02"


def test_one_record_is_its_own_latest_and_pairs_are_kept_apart(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    put(graph, f"{a}--{b}.yaml", pair_doc(a, b, "open", "open"))
    put(graph, f"{a}--c-ffffffff.yaml", pair_doc(a, "c-ffffffff", "proved", "open"))
    got = review.latest_pairs(base(graph))
    assert [(p["a"], p["b"]) for p in got] == [(a, b), (a, "c-ffffffff")]


def test_latest_of_takes_names_in_any_order() -> None:
    """The service reads the records through the host, not the disk: the pure half."""
    a, b = "c-aaaaaaaa", "c-bbbbbbbb"
    named = [
        (f"{a}--{b}--{DAY}-10.yaml", pair_doc(a, b, "proved", "proved")),
        (f"{a}--{b}.yaml", pair_doc(a, b, "open", "open")),
        (f"{a}--{b}--{DAY}-2.yaml", pair_doc(a, b, "open", "proved")),
    ]
    for order in (named, named[::-1], [named[1], named[0], named[2]]):
        (p,) = review.latest_of(order)
        assert p["forward"]["state"] == "proved" and p["backward"]["state"] == "proved"
    assert [p["forward"]["state"] for p in review.in_order(named)] == ["open", "open", "proved"]


def test_a_name_the_rule_cannot_read_counts_as_a_first_record() -> None:
    """A hand-named record (none exists on any graph) is generation 1: beside the job's first
    record on the same day, the name decides, and a numbered one supersedes both."""
    a, b = "c-aaaaaaaa", "c-bbbbbbbb"
    named = [
        (f"{a}--{b}--extra.yaml", pair_doc(a, b, "refuted", "open")),
        (f"{a}--{b}.yaml", pair_doc(a, b, "open", "open")),
    ]
    assert [p["forward"]["state"] for p in review.in_order(named)] == ["refuted", "open"]
    named.append((f"{a}--{b}--{DAY}-2.yaml", pair_doc(a, b, "proved", "open")))
    (p,) = review.latest_of(named)
    assert p["forward"]["state"] == "proved"


def test_the_job_writes_a_second_record_the_rule_reads_as_newer(tmp_path: Path) -> None:
    """End to end in the fast tier: a pair on record as open, then the bounded tactics prove it
    (a moved budget re-attempts it); the job writes ``--<date>-2`` and every reader then sees the
    proved record, not the first."""
    graph, a, b = setup(tmp_path)
    old = pair_doc(a, b, "open", "open")
    for d in ("forward", "backward"):
        old[d]["attempt"]["budget_s"] = 1  # another budget: the job attempts again
    put(graph, f"{a}--{b}.yaml", old)
    fake = ReviewFake(models={a: Model(legendre()), b: Model(legendre())}, implies={(a, b), (b, a)})
    spec = json.loads((graph / "targets" / TARGET / "gate-spec.json").read_text())
    runner = review_lean.Runner(fake, FAKE_RESOLVED, tmp_path / "work", budget_s=5, jobs=1)
    settings = review_job.Settings(date=DAY, budget_s=5, jobs=1)
    summary = review_job.review_run(graph, TARGET, runner, spec, settings)
    assert f"targets/{TARGET}/review/pairs/{a}--{b}--{DAY}-2.yaml" in summary["written"]
    (p,) = review.latest_pairs(base(graph))
    assert review.equivalent(p)
    assert review.derive(graph / "targets" / TARGET)["clusters"] == [[a, b]]
    # and a second run reads it back as in force: nothing more is written
    runner = review_lean.Runner(fake, FAKE_RESOLVED, tmp_path / "work2", budget_s=5, jobs=1)
    assert review_job.review_run(graph, TARGET, runner, spec, settings)["written"] == []
