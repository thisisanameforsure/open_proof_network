"""F26-T5, T6 under the real toolchain (AC3 and AC4; lean tier, make verify-lean).

The fast tier decides each file through a fake that reads its header; this elaborates the same
files with the pinned Lean. Core only, so the laptop runs it: the first prototype's Legendre
candidates, copied under ``fixtures/review/``.

AC4: the faithful reading and a rewording (``alt-mul``: ``0 < n``, products for squares) are
proved equivalent both ways by the two-layer matching; the closed interval (``alt-closed``,
weaker as a formula, equivalent only because squares are never prime) is proved one way and
refuted the other at a named case — n = 1, supposing 1 were the only prime. Every exhibit the job
wrote, and every test, re-elaborates on its own in a fresh directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from review_support import DATE, make_graph, prototype_lean, tree

from opn_gate import review, review_job, review_lean
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

TARGET = "legendre"


def run_real(
    graph: Path, real: LocalToolchain, pinned: ResolvedToolchain, work: Path
) -> dict[str, Any]:
    spec = json.loads((graph / "targets" / TARGET / "gate-spec.json").read_text())
    runner = review_lean.Runner(real, pinned, work, budget_s=120, jobs=4)
    settings = review_job.Settings(date=DATE, budget_s=120, jobs=4)
    return review_job.review_run(graph, TARGET, runner, spec, settings)


def reelaborate_everything(
    graph: Path, real: LocalToolchain, pinned: ResolvedToolchain, work: Path
) -> int:
    """Every Lean file under review/exhibits and review/tests, elaborated alone: the count."""
    base = graph / "targets" / TARGET / "review"
    files = sorted((base / "exhibits").glob("*.lean")) + sorted((base / "tests").glob("*.lean"))
    runner = review_lean.Runner(real, pinned, work, budget_s=120, jobs=4)
    results = runner.many([p.read_text(encoding="utf-8") for p in files])
    bad = [p.name for p, r in zip(files, results, strict=True) if not r.ok]
    assert bad == [], bad
    return len(files)


def pair(graph: Path, a: str, b: str) -> dict[str, Any]:
    folder = graph / "targets" / TARGET / "review" / "pairs"
    for p in folder.glob("*.yaml"):
        doc = yaml.safe_load(p.read_text())
        if {doc["a"], doc["b"]} == {a, b}:
            return dict(doc)
    raise AssertionError(f"no pair {a} {b}")


def way(doc: dict[str, Any], a: str, b: str) -> dict[str, Any]:
    found: dict[str, Any] = doc["forward"] if (doc["a"], doc["b"]) == (a, b) else doc["backward"]
    return found


def test_ac3_under_the_real_toolchain(
    real_toolchain: LocalToolchain, pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    graph, ids = make_graph(
        tmp_path,
        candidates={
            "faithful": prototype_lean("legendre", "human-ref"),
            "inline": prototype_lean("legendre", "alt-inline"),
            "dropped": prototype_lean("legendre", "bad-zero"),
        },
        people=("faithful",),
    )
    summary = run_real(graph, real_toolchain, pinned, tmp_path / "work")
    assert summary["candidates"] == {
        ids["dropped"]: review.DISCARDED,
        ids["faithful"]: review.SURVIVING,
        ids["inline"]: review.RETURNED,
    }, summary
    assert reelaborate_everything(graph, real_toolchain, pinned, tmp_path / "again") > 0
    before = tree(graph)
    assert run_real(graph, real_toolchain, pinned, tmp_path / "work2")["written"] == []
    assert tree(graph) == before


def test_ac4_pairs_proved_and_refuted_at_a_named_case(
    real_toolchain: LocalToolchain, pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    graph, ids = make_graph(
        tmp_path,
        candidates={
            "faithful": prototype_lean("legendre", "human-ref"),
            "rewording": prototype_lean("legendre", "alt-mul"),
            "weaker": prototype_lean("legendre", "alt-closed"),
        },
        people=("faithful",),
    )
    f, r, w = ids["faithful"], ids["rewording"], ids["weaker"]
    summary = run_real(graph, real_toolchain, pinned, tmp_path / "work")
    assert summary["candidates"] == dict.fromkeys(sorted([f, r, w]), review.SURVIVING), summary
    fr = pair(graph, f, r)
    assert way(fr, f, r)["state"] == "proved", fr
    assert way(fr, r, f)["state"] == "proved", fr
    fw = pair(graph, f, w)
    assert way(fw, f, w)["state"] == "proved", fw
    back = way(fw, w, f)
    assert back["state"] == "refuted", fw
    exhibit = json.loads(
        (graph / "targets" / TARGET / "review" / "exhibits" / f"{back['exhibit']}.json").read_text()
    )
    assert "n = 1, supposing 1 were the only prime" in exhibit["detail"], exhibit
    assert sorted(summary["clusters"]) == sorted([sorted([f, r]), [w]]), summary
    # the disagreement is a question, phrased as the hypothesis
    qs = [
        yaml.safe_load(p.read_text())
        for p in sorted((graph / "targets" / TARGET / "review" / "questions").glob("*.yaml"))
    ]
    assert "Suppose 1 were the only prime. Would the conjecture be satisfied at n = 1?" in [
        q["question"] for q in qs
    ]
    n = reelaborate_everything(graph, real_toolchain, pinned, tmp_path / "again")
    assert n > 0
    before = tree(graph)
    assert run_real(graph, real_toolchain, pinned, tmp_path / "work2")["written"] == []
    assert tree(graph) == before
