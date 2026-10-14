"""F26-T5: the review job's filter stage, agreement tests and idempotence (R4, R5, R6, R13; AC3).

Fast tier: every file the job elaborates goes through ``Toolchain.elaborate`` and is decided by
``ReviewFake`` from the file's header and a Python model of each candidate (``review_support``).
The AC3 fixture is a core-Lean target whose root is in words (Legendre's conjecture, the first
prototype's: a conjecture with decidable small cases) and three candidates, the prototype's own
files: faithful (``human-ref``), the concept written inline (``alt-inline``) and the domain
hypothesis dropped (``bad-zero``). The spec's AC3 names "the propositional fixture's root"; that
root is a tautology about propositions, so the statement screen discards every faithful
formalization of it and it has no case to probe (proposed as an F26 Q entry).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from fakes import FAKE_RESOLVED
from review_support import (
    DATE,
    Model,
    ReviewFake,
    add_test_record,
    legendre,
    make_graph,
    prototype_lean,
    tree,
)

from opn_gate import cli, review, review_job, review_lean, schemas, toolchain

TARGET = "legendre"


def run_job(graph: Path, fake: ReviewFake, tmp: Path, **kw: Any) -> dict[str, Any]:
    spec = json.loads((graph / "targets" / TARGET / "gate-spec.json").read_text())
    runner = review_lean.Runner(fake, FAKE_RESOLVED, tmp / "work", budget_s=5, jobs=1)
    settings = review_job.Settings(date=DATE, budget_s=5, jobs=1, **kw)
    return review_job.review_run(graph, TARGET, runner, spec, settings)


def exhibits(graph: Path) -> list[dict[str, Any]]:
    folder = graph / "targets" / TARGET / "review" / "exhibits"
    return [json.loads(p.read_text()) for p in sorted(folder.glob("*.json"))]


def assert_records_valid_and_lean_accepted(graph: Path, fake: ReviewFake) -> None:
    """Every record the job wrote validates; every Lean file it wrote is a text the toolchain
    accepted in that run (the 2026-09-17 lesson)."""
    base = graph / "targets" / TARGET / "review"
    for p in sorted((base / "exhibits").glob("*.json")):
        schemas.validate(json.loads(p.read_text()), "exhibit/v1")
    for sub, sid in (
        ("tests", "intent-test/v1"),
        ("questions", "review-question/v1"),
        ("pairs", "pair/v1"),
    ):
        for p in sorted((base / sub).glob("*.yaml")) if (base / sub).is_dir() else []:
            schemas.validate(yaml.safe_load(p.read_text()), sid)
    for sub in ("exhibits", "tests"):
        for p in sorted((base / sub).glob("*.lean")) if (base / sub).is_dir() else []:
            assert p.read_text() in fake.accepted, p.name


@pytest.fixture
def ac3(tmp_path: Path) -> tuple[Path, dict[str, str], ReviewFake]:
    graph, ids = make_graph(
        tmp_path,
        candidates={
            "faithful": prototype_lean("legendre", "human-ref"),
            "inline": prototype_lean("legendre", "alt-inline"),
            "dropped": prototype_lean("legendre", "bad-zero"),
        },
        people=("faithful",),
    )
    fake = ReviewFake(
        models={
            ids["faithful"]: Model(legendre()),
            ids["inline"]: Model(legendre(), prime=None),
            ids["dropped"]: Model(legendre(lo=0)),
        }
    )
    return graph, ids, fake


def test_ac3_returned_discarded_surviving(
    ac3: tuple[Path, dict[str, str], ReviewFake], tmp_path: Path
) -> None:
    graph, ids, fake = ac3
    summary = run_job(graph, fake, tmp_path)
    assert summary["ok"], summary
    status = summary["candidates"]
    assert status[ids["inline"]] == review.RETURNED
    assert status[ids["dropped"]] == review.DISCARDED
    assert status[ids["faithful"]] == review.SURVIVING
    found = exhibits(graph)
    returned = [e for e in found if e["candidate"] == ids["inline"]]
    assert [(e["kind"], e["result"]) for e in returned] == [("format", "returned")]
    assert "`prime`" in returned[0]["detail"]
    dropped = [e for e in found if e["candidate"] == ids["dropped"] and review.discards(e)]
    assert len(dropped) == 1 and dropped[0]["kind"] in ("screen", "intent-test")
    # the discard's Lean is the kernel's: the counterexample at n = 0
    lean = (
        graph / "targets" / TARGET / "review" / "exhibits" / dropped[0]["lean_file"]
    ).read_text()
    assert "absurd (h 0)" in lean
    faithful = {(e["kind"], e["result"]) for e in found if e["candidate"] == ids["faithful"]}
    assert ("compile", "pass") in faithful
    assert not any(r == "fail" for _, r in faithful)
    # the page's derivation reads the same fates from the records the job wrote
    derived = review.derive(graph / "targets" / TARGET)
    assert {c["id"]: c["status"] for c in derived["candidates"]} == status
    assert_records_valid_and_lean_accepted(graph, fake)


def test_ac3_a_second_run_writes_nothing(
    ac3: tuple[Path, dict[str, str], ReviewFake], tmp_path: Path
) -> None:
    graph, _ids, fake = ac3
    first = run_job(graph, fake, tmp_path)
    assert first["written"]
    before = tree(graph)
    second = run_job(graph, fake, tmp_path)
    assert second["written"] == []
    assert tree(graph) == before
    assert second["candidates"] == first["candidates"]


def test_exhibit_ids_are_a_function_of_the_question_not_the_run(
    ac3: tuple[Path, dict[str, str], ReviewFake], tmp_path: Path
) -> None:
    """R13: another run id or another day asks the same questions and writes nothing new; a
    moved pin asks under another toolchain and gets new ids (R6's re-run)."""
    graph, _ids, fake = ac3
    run_job(graph, fake, tmp_path)
    again = run_job(graph, fake, tmp_path, run_id="12345")
    assert again["written"] == []
    a = review_job.exhibit_id("compile", "c-00000000", None, "compile", "lean:v1", None)
    b = review_job.exhibit_id("compile", "c-00000000", None, "compile", "lean:v2", None)
    assert a != b


def test_a_returned_candidate_is_never_compiled(
    ac3: tuple[Path, dict[str, str], ReviewFake], tmp_path: Path
) -> None:
    graph, ids, fake = ac3
    run_job(graph, fake, tmp_path)
    heads = [review_lean.header_of(t) or {} for t in fake.texts]
    assert not [h for h in heads if h.get("cand") == ids["inline"]]


def test_compile_failure_discards_with_no_lean(tmp_path: Path) -> None:
    graph, ids = make_graph(tmp_path, candidates={"broken": prototype_lean("legendre", "agent-b")})
    fake = ReviewFake(models={ids["broken"]: Model(legendre(), compiles=False)})
    summary = run_job(graph, fake, tmp_path)
    assert summary["candidates"][ids["broken"]] == review.DISCARDED
    (e,) = exhibits(graph)
    assert (e["kind"], e["result"], e["lean_file"]) == ("compile", "fail", None)


@pytest.mark.parametrize(("flag", "screen"), [("provable", "statement"), ("vacuous", "false")])
def test_a_screen_that_fires_discards(tmp_path: Path, flag: str, screen: str) -> None:
    graph, ids = make_graph(tmp_path, candidates={"c": prototype_lean("legendre", "human-ref")})
    model = Model(legendre(), provable=flag == "provable", vacuous=flag == "vacuous")
    fake = ReviewFake(models={ids["c"]: model})
    summary = run_job(graph, fake, tmp_path)
    assert summary["candidates"][ids["c"]] == review.DISCARDED
    fired = [e for e in exhibits(graph) if review.discards(e)]
    assert [(e["kind"], e["detail"].split(":")[0]) for e in fired] == [("screen", screen)]
    assert fired[0]["lean_file"] is not None


def test_a_test_on_record_discards_the_candidate_it_fails(tmp_path: Path) -> None:
    graph, ids = make_graph(
        tmp_path,
        candidates={
            "faithful": prototype_lean("legendre", "human-ref"),
            "closed": prototype_lean("legendre", "alt-closed"),
        },
    )
    case = review_lean.Case("witness", 1, (1,), "prime")
    tid = add_test_record(graph, TARGET, case, False, "citation", "the words: strictly between")
    fake = ReviewFake(
        models={ids["faithful"]: Model(legendre()), ids["closed"]: Model(legendre(closed=True))}
    )
    summary = run_job(graph, fake, tmp_path)
    assert summary["candidates"] == {
        ids["closed"]: review.DISCARDED,
        ids["faithful"]: review.SURVIVING,
    }
    (fail,) = [e for e in exhibits(graph) if review.discards(e)]
    assert (fail["kind"], fail["test"], fail["candidate"]) == ("intent-test", tid, ids["closed"])
    lean = (graph / "targets" / TARGET / "review" / "exhibits" / fail["lean_file"]).read_text()
    assert review_lean.case_of(lean) == case


def test_agreement_tests_are_written_where_every_survivor_agrees(tmp_path: Path) -> None:
    """R6: the job's degenerate and boundary cases, expected values from the survivors'
    agreement (the weakest source), each run against every survivor."""
    graph, ids = make_graph(
        tmp_path,
        candidates={
            "faithful": prototype_lean("legendre", "human-ref"),
            "mul": prototype_lean("legendre", "alt-mul"),
        },
        people=("faithful",),
    )
    a, b = ids["faithful"], ids["mul"]
    fake = ReviewFake(models={a: Model(legendre()), b: Model(legendre())}, implies={(a, b), (b, a)})
    summary = run_job(graph, fake, tmp_path)
    base = graph / "targets" / TARGET / "review"
    tests = [yaml.safe_load(p.read_text()) for p in sorted((base / "tests").glob("*.yaml"))]
    assert len(tests) == review_job.AGREEMENT_N * 2 + review_job.CONCEPT_N
    assert {t["expected"]["source"] for t in tests} == {"agreement"}
    assert {t["expected"]["ref"] for t in tests} == {"agreement:2"}
    by_case = {(t["probe"], t["case"]): t["expected"]["value"] for t in tests}
    assert by_case[("covers", "n = 0: does the conjecture say anything about it?")] is False
    assert by_case[("concept", "is 1 prime, in the sense the conjecture means?")] is False
    passes = [e for e in exhibits(graph) if e["kind"] == "intent-test"]
    assert len(passes) == 2 * len(tests) and {e["result"] for e in passes} == {"pass"}
    assert summary["clusters"] == [sorted([a, b])]
    assert_records_valid_and_lean_accepted(graph, fake)


def test_one_survivor_writes_no_agreement_test(
    ac3: tuple[Path, dict[str, str], ReviewFake], tmp_path: Path
) -> None:
    graph, _ids, fake = ac3
    summary = run_job(graph, fake, tmp_path)
    assert summary["tests_written"] == []


def test_small_cases_do_not_apply_is_recorded(tmp_path: Path) -> None:
    """R6: a claim with no computable small case says so in its compile exhibit's detail."""
    lean = (
        "def IsPrime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0\n\n"
        "theorem opn_infinite : ∀ N : Nat, ∃ p, N < p ∧ IsPrime p := by\n  sorry\n"
    )
    graph, ids = make_graph(tmp_path, candidates={"closed": lean})
    fake = ReviewFake(models={ids["closed"]: Model(lambda n, p: True)})
    run_job(graph, fake, tmp_path)
    compiled = [e for e in exhibits(graph) if e["kind"] == "compile"]
    assert compiled and compiled[0]["result"] == "pass"
    assert "small cases do not apply" in compiled[0]["detail"]


def test_the_cli_runs_the_job(
    ac3: tuple[Path, dict[str, str], ReviewFake],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    graph, ids, fake = ac3
    monkeypatch.setattr(toolchain.LocalToolchain, "from_settings", classmethod(lambda cls, s: fake))
    code = cli.main(["review", "run", "--graph", str(graph), "--target", TARGET, "--date", DATE])
    out = json.loads(capsys.readouterr().out)
    assert code == 0, out
    assert out["candidates"][ids["faithful"]] == review.SURVIVING
    assert out["written"]


# --- the statement screen asks about open conjectures only (F26-Q20; the owner's ruling) -------
# 2026-10-14: in the pinned image the tutorial's background review discarded its root at the
# statement screen ("the claim was proved for every n within the bounded budget"). That screen
# catches an open conjecture formalized too weakly; on a root already proved it reports a fact,
# not a defect. The owner's ruling: it runs only where the root is an open conjecture.


def _existing(graph: Path, track: str | None) -> None:
    """Make the review a background one on an existing target, with ``track`` in its record
    (None: no record, as the tutorial has none)."""
    tdir = graph / "targets" / TARGET
    head = yaml.safe_load((tdir / "review" / "review.yaml").read_text())
    head["opened_by"] = {"identity": "network", "role": "network"}
    head["source"] = {"kind": "existing", "ref": TARGET}
    (tdir / "review" / "review.yaml").write_text(yaml.safe_dump(head, sort_keys=False))
    if track is not None:
        (tdir / "target.yaml").write_text(yaml.safe_dump({"track": track}))


@pytest.mark.parametrize("track", ["formalization", None])
def test_a_root_off_the_open_track_is_not_discarded_for_being_provable(
    tmp_path: Path, track: str | None
) -> None:
    graph, ids = make_graph(tmp_path, candidates={"c": prototype_lean("legendre", "human-ref")})
    _existing(graph, track)
    fake = ReviewFake(models={ids["c"]: Model(legendre(), provable=True)})
    summary = run_job(graph, fake, tmp_path)
    assert summary["candidates"][ids["c"]] == review.SURVIVING
    kinds = [(e["kind"], e["detail"].split(":")[0]) for e in exhibits(graph)]
    assert ("screen", "statement") not in kinds
    assert ("screen", "negation") in kinds and ("screen", "false") in kinds


def test_an_open_track_root_is_still_discarded_for_being_provable(tmp_path: Path) -> None:
    graph, ids = make_graph(tmp_path, candidates={"c": prototype_lean("legendre", "human-ref")})
    _existing(graph, "open")
    fake = ReviewFake(models={ids["c"]: Model(legendre(), provable=True)})
    assert run_job(graph, fake, tmp_path)["candidates"][ids["c"]] == review.DISCARDED


def test_a_root_off_the_open_track_still_meets_the_false_screen(tmp_path: Path) -> None:
    graph, ids = make_graph(tmp_path, candidates={"c": prototype_lean("legendre", "human-ref")})
    _existing(graph, "formalization")
    fake = ReviewFake(models={ids["c"]: Model(legendre(), vacuous=True)})
    assert run_job(graph, fake, tmp_path)["candidates"][ids["c"]] == review.DISCARDED


# --- a candidate's graph imports are built for it (F26-Q21) ------------------------------------
# 2026-10-14, the first full live run: euclid-primes' root imports the graph's own definitions
# and its node's Context, and the job compiled it with neither on the search path. It recorded
# "does not elaborate at the pin: unknown module prefix 'Defs'" and discarded a statement the gate
# admits every day. The job now builds the graph modules its candidates import, once, before any
# check; a module it cannot build stops the job with nothing written, never a discard.

LOCAL_HEAD = "import Defs.Small\nimport Nodes.«legendre».Context\n"


def _graph_modules(graph: Path, *, context: str | None = "import Defs.Small\n") -> None:
    tdir = graph / "targets" / TARGET
    (tdir / "defs").mkdir(parents=True, exist_ok=True)
    (tdir / "defs" / "Small.lean").write_text("def Opn.small (n : Nat) : Prop := n < 3\n")
    if context is not None:
        node = tdir / "nodes" / TARGET
        node.mkdir(parents=True, exist_ok=True)
        (node / "Context.lean").write_text(
            context + "theorem Opn.h : ∀ n, Opn.small n → n < 4 := by\n  sorry\n"
        )


def test_a_candidate_importing_the_graphs_modules_compiles(tmp_path: Path) -> None:
    lean = LOCAL_HEAD + prototype_lean("legendre", "human-ref")
    graph, ids = make_graph(tmp_path, candidates={"c": lean})
    _graph_modules(graph)
    fake = ReviewFake(models={ids["c"]: Model(legendre())}, resolve_imports=True)
    summary = run_job(graph, fake, tmp_path)
    assert summary["ok"] is True
    assert summary["candidates"][ids["c"]] == review.SURVIVING
    compiled = [e for e in exhibits(graph) if e["kind"] == "compile"]
    assert [e["result"] for e in compiled] == ["pass"]


def test_a_graph_import_with_no_file_stops_the_job_and_writes_nothing(tmp_path: Path) -> None:
    lean = "import Defs.Missing\n" + prototype_lean("legendre", "human-ref")
    graph, ids = make_graph(tmp_path, candidates={"c": lean})
    before = tree(graph)
    fake = ReviewFake(models={ids["c"]: Model(legendre())}, resolve_imports=True)
    summary = run_job(graph, fake, tmp_path)
    assert summary["ok"] is False and "Defs.Missing" in summary["error"]
    assert tree(graph) == before


def test_a_graph_module_that_does_not_build_stops_the_job_and_writes_nothing(
    tmp_path: Path,
) -> None:
    lean = LOCAL_HEAD + prototype_lean("legendre", "human-ref")
    graph, ids = make_graph(tmp_path, candidates={"c": lean})
    _graph_modules(graph)
    before = tree(graph)
    fake = ReviewFake(
        models={ids["c"]: Model(legendre())},
        resolve_imports=True,
        broken_modules={"Nodes.«legendre».Context"},
    )
    summary = run_job(graph, fake, tmp_path)
    assert summary["ok"] is False and "Nodes.«legendre».Context" in summary["error"]
    assert tree(graph) == before
