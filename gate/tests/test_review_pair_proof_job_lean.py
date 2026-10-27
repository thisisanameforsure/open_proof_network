"""F26-T18 under the real toolchain (lean tier, make verify-lean): a merged contributed proof
becomes a proved direction and its exhibit, a contributed proof the kernel refuses leaves its
direction open with the record named, and a second run writes nothing.

Core Lean only: the first prototype's Legendre candidates, the faithful reading (``human-ref``)
and the closed interval (``alt-closed``). The job's own two-layer matching proves the first
implies the second, so to make that direction claimable work the test puts on record a pair
whose both directions the job left open at this budget, the state a stronger pair has on a real
target. The contributed proof is the contract's (``test_pair_proof_contract``): a helper relating
the two ``Prime`` predicates, then the existential repacked with ``Nat.le_of_lt``. The other
direction is false (it is refuted at n = 1, supposing 1 were the only prime), and the record
filed for it does not elaborate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from review_support import DATE, make_graph, prototype_lean, tree

from opn_gate import pair_proofs, review, review_job, review_lean, review_pairs
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

TARGET = "legendre"
BUDGET = 120
AUTHOR = "t1027-j"


def ns(cid: str) -> str:
    return review_lean.ns(cid, "p")


def run_real(
    graph: Path, real: LocalToolchain, pinned: ResolvedToolchain, work: Path
) -> dict[str, Any]:
    spec = json.loads((graph / "targets" / TARGET / "gate-spec.json").read_text())
    runner = review_lean.Runner(real, pinned, work, budget_s=BUDGET, jobs=4)
    settings = review_job.Settings(date=DATE, budget_s=BUDGET, jobs=4)
    return review_job.review_run(graph, TARGET, runner, spec, settings)


def put_record(  # noqa: PLR0917 — one argument per field the test varies
    graph: Path,
    a: str,
    b: str,
    direction: pair_proofs.Direction,
    helpers: str,
    proof: str,
    date: str,
) -> str:
    base = graph / "targets" / TARGET / "review"

    def cand(cid: str) -> review_lean.Cand:
        c = review_lean.prepare(cid, (base / "candidates" / f"{cid}.lean").read_text(), ["prime"])
        assert isinstance(c, review_lean.Cand)
        return c

    def hash_of(cid: str) -> str:
        return str(
            yaml.safe_load((base / "candidates" / f"{cid}.yaml").read_text())["statement_hash"]
        )

    tmpl = pair_proofs.template(cand(a), cand(b), direction)
    lean = tmpl.replace(pair_proofs.HELPERS_END, helpers + pair_proofs.HELPERS_END).replace(
        pair_proofs.PLACEHOLDER, proof
    )
    doc = {
        "schema": "pair-proof/v1",
        "target": TARGET,
        "a": a,
        "b": b,
        "direction": direction,
        "kind": "proof",
        "case": None,
        "statement_hashes": {"a": hash_of(a), "b": hash_of(b)},
        "lean": lean,
        "author": AUTHOR,
        "models": ["claude-opus-5-5"],
        "date": date,
    }
    stamp = date.replace("-", "").replace(":", "")
    name = pair_proofs.record_name(a, b, direction, stamp, AUTHOR)
    (base / pair_proofs.DIR).mkdir(parents=True, exist_ok=True)
    (base / pair_proofs.DIR / name).write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    )
    return name.removesuffix(".yaml")


def test_a_merged_contributed_proof_under_the_real_toolchain(
    real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path, tmp_path: Path
) -> None:
    del lean_pkg  # built: the metaprograms the shared verdict asks (replay, meaning, axioms)
    graph, ids = make_graph(
        tmp_path,
        candidates={
            "faithful": prototype_lean("legendre", "human-ref"),
            "weaker": prototype_lean("legendre", "alt-closed"),
        },
        people=("faithful",),
    )
    f, w = ids["faithful"], ids["weaker"]
    a, b = sorted([f, w])
    true_way: pair_proofs.Direction = "forward" if (a, b) == (f, w) else "backward"
    false_way: pair_proofs.Direction = "backward" if true_way == "forward" else "forward"
    base = graph / "targets" / TARGET / "review"
    # the job left both directions open at this budget (a pair record on record)
    still_open = {
        "state": "open",
        "exhibit": None,
        "attempt": {"who": "gate", "tool": review_pairs.TOOL, "budget_s": BUDGET},
    }
    (base / "pairs").mkdir(parents=True)
    (base / "pairs" / f"{a}--{b}.yaml").write_text(
        yaml.safe_dump(
            {
                "schema": "pair/v1",
                "target": TARGET,
                "a": a,
                "b": b,
                "forward": still_open,
                "backward": still_open,
                "date": DATE,
            },
            sort_keys=False,
        )
    )
    helper = f"private theorem same (p : Nat) : {ns(f)}.Prime p → {ns(w)}.Prime p := id\n"
    good = put_record(
        graph,
        a,
        b,
        true_way,
        helper,
        "  intro hn\n  obtain ⟨p, h1, h2, h3⟩ := h hn\n"
        "  exact ⟨p, Nat.le_of_lt h1, Nat.le_of_lt h2, same p h3⟩\n",
        "2026-10-27T01:00:00Z",
    )
    bad = put_record(graph, a, b, false_way, "", "  exact h\n", "2026-10-27T02:00:00Z")

    summary = run_real(graph, real_toolchain, pinned, tmp_path / "work")
    assert summary["candidates"] == {f: review.SURVIVING, w: review.SURVIVING}, summary
    (p,) = review.latest_pairs(base)
    settled, refused = p[true_way], p[false_way]
    assert settled["state"] == "proved" and settled["attempt"] is None, (p, summary["notes"])
    exhibit = json.loads((base / "exhibits" / f"{settled['exhibit']}.json").read_text())
    assert (exhibit["kind"], exhibit["candidate"], exhibit["test"], exhibit["result"]) == (
        "pair",
        f,
        w,
        "proved",
    )
    assert good in exhibit["detail"] and AUTHOR in exhibit["detail"]
    lean = (base / "exhibits" / exhibit["lean_file"]).read_text()
    record = yaml.safe_load((base / pair_proofs.DIR / f"{good}.yaml").read_text())
    assert lean == record["lean"]
    # the false direction's record does not elaborate: open, the record named, no exhibit
    assert refused["state"] == "open" and refused["exhibit"] is None, p
    assert refused["attempt"]["who"] == AUTHOR and bad in refused["attempt"]["tool"], refused
    assert "pair-proof-elaboration" in refused["attempt"]["tool"]
    assert any(bad in n for n in summary["notes"]), summary["notes"]
    # the exhibit's Lean elaborates alone, in a fresh directory, and its guarded copy does not
    runner = review_lean.Runner(real_toolchain, pinned, tmp_path / "again", budget_s=BUDGET)
    assert runner.check(lean).ok
    first = review_lean.prepare(f, prototype_lean("legendre", "human-ref"), ["prime"])
    assert isinstance(first, review_lean.Cand)
    assert not runner.check(pair_proofs.guarded(lean, first)).ok

    before = tree(graph)
    assert run_real(graph, real_toolchain, pinned, tmp_path / "work2")["written"] == []
    assert tree(graph) == before
