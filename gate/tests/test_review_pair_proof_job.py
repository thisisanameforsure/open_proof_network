"""F26-T18 (R8, R13): the review job consumes a merged pair-proof record.

After a contributor's settlement of an open direction merges, the job (which the merge re-runs,
``postmerge.review_targets``) re-checks the record's Lean with its own runner — the direction's
template, the region rules, the file elaborates, and for a proof the guarded copy does not — and
on a pass writes the ``pair`` exhibit and the direction's new state. It trusts nothing the gate
said before the merge: a record that fails the re-check leaves the direction open, the attempt
naming the record and why. Fast tier: ``ReviewFake`` decides a filled template by the markers in
its proof region (``review_support.ReviewFake._pair_proof``); the lean tier is
``test_review_pair_proof_job_lean.py``.

The pair is Legendre's faithful reading and a rewording (``alt-mul``): the fake's bounded tactics
prove neither direction, so the job leaves both open — claimable work.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from fakes import FAKE_RESOLVED
from review_support import DATE, Model, ReviewFake, legendre, make_graph, prototype_lean, tree

from opn_gate import pair_proofs, postmerge, review, review_job, review_lean, review_pairs
from opn_gate.paths import Change

TARGET = "legendre"
AUTHOR = "t1027-j"
STAMP_DATE = "2026-10-27T01:00:00Z"
PROOF = "  -- the contributor's tactics\n  exact h\n"


# --- the graph and the records ---------------------------------------------------------------


def setup(tmp_path: Path, other: str = "alt-mul") -> tuple[Path, str, str]:
    """The two candidates, ``a`` the lexically smaller id as ``pair/v1`` names it."""
    graph, ids = make_graph(
        tmp_path,
        candidates={
            "faithful": prototype_lean("legendre", "human-ref"),
            "other": prototype_lean("legendre", other),
        },
    )
    a, b = sorted(ids.values())
    return graph, a, b


def base(graph: Path) -> Path:
    return graph / "targets" / TARGET / "review"


def cand(graph: Path, cid: str) -> review_lean.Cand:
    c = review_lean.prepare(
        cid, (base(graph) / "candidates" / f"{cid}.lean").read_text(), ["prime"]
    )
    assert isinstance(c, review_lean.Cand)
    return c


def statement_hash(graph: Path, cid: str) -> str:
    doc = yaml.safe_load((base(graph) / "candidates" / f"{cid}.yaml").read_text())
    return str(doc["statement_hash"])


def fill(tmpl: str, proof: str = PROOF, helpers: str = "") -> str:
    return tmpl.replace(pair_proofs.HELPERS_END, helpers + pair_proofs.HELPERS_END).replace(
        pair_proofs.PLACEHOLDER, proof
    )


def put_record(
    graph: Path,
    a: str,
    b: str,
    direction: pair_proofs.Direction = "forward",
    *,
    kind: pair_proofs.Kind = "proof",
    n: int | None = None,
    proof: str = PROOF,
    lean: str | None = None,
    author: str = AUTHOR,
    date: str = STAMP_DATE,
    hashes: dict[str, str] | None = None,
    case: dict[str, Any] | str | None = "auto",
) -> str:
    """A merged pair-proof record built the way the service builds one; returns its file stem."""
    if lean is None:
        lean = fill(pair_proofs.template(cand(graph, a), cand(graph, b), direction, kind, n), proof)
    if case == "auto":
        case = None if n is None else review_lean.Case("holds", n).key()
    doc = {
        "schema": "pair-proof/v1",
        "target": TARGET,
        "a": a,
        "b": b,
        "direction": direction,
        "kind": kind,
        "case": case,
        "statement_hashes": hashes
        or {"a": statement_hash(graph, a), "b": statement_hash(graph, b)},
        "lean": lean,
        "author": author,
        "models": ["claude-opus-5-5"],
        "date": date,
    }
    stamp = date.replace("-", "").replace(":", "")
    name = pair_proofs.record_name(a, b, direction, stamp, author)
    folder = base(graph) / pair_proofs.DIR
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    return name.removesuffix(".yaml")


def fake_for(a: str, b: str) -> ReviewFake:
    return ReviewFake(models={a: Model(legendre()), b: Model(legendre())})


def run(graph: Path, fake: ReviewFake, work: Path) -> dict[str, Any]:
    spec = json.loads((graph / "targets" / TARGET / "gate-spec.json").read_text())
    runner = review_lean.Runner(fake, FAKE_RESOLVED, work, budget_s=5, jobs=1)
    settings = review_job.Settings(date=DATE, budget_s=5, jobs=1)
    return review_job.review_run(graph, TARGET, runner, spec, settings)


def in_force(graph: Path, a: str, b: str) -> dict[str, Any]:
    (p,) = [p for p in review.latest_pairs(base(graph)) if (p["a"], p["b"]) == (a, b)]
    return p


def exhibit(graph: Path, eid: str) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads((base(graph) / "exhibits" / f"{eid}.json").read_text())
    return doc


def pair_proof_texts(fake: ReviewFake, start: int = 0) -> list[str]:
    return [t for t in fake.texts[start:] if '"op": "pair-proof"' in t.split("\n", 1)[0]]


def record_lean(graph: Path, stem: str) -> str:
    doc = yaml.safe_load((base(graph) / pair_proofs.DIR / f"{stem}.yaml").read_text())
    return str(doc["lean"])


# --- a proof that passes ---------------------------------------------------------------------


def test_a_merged_proof_becomes_a_proved_direction_and_its_exhibit(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    stem = put_record(graph, a, b, "forward")
    fake = fake_for(a, b)
    summary = run(graph, fake, tmp_path / "work")
    p = in_force(graph, a, b)
    fwd = p["forward"]
    assert fwd["state"] == "proved" and fwd["attempt"] is None, fwd
    e = exhibit(graph, fwd["exhibit"])
    spec = json.loads((graph / "targets" / TARGET / "gate-spec.json").read_text())
    assert e["id"] == review_job.exhibit_id(
        "pair", a, b, f"contributed:{stem}", spec["lean_toolchain"], spec.get("mathlib_sha")
    )
    assert (e["kind"], e["candidate"], e["test"], e["result"]) == ("pair", a, b, "proved")
    assert AUTHOR in e["detail"] and "implies" in e["detail"] and stem in e["detail"]
    lean = (base(graph) / "exhibits" / e["lean_file"]).read_text()
    assert lean == record_lean(graph, stem)
    # the record's Lean and its guarded copy were both elaborated by the job
    texts = pair_proof_texts(fake)
    assert lean in texts and pair_proofs.guarded(lean, cand(graph, a)) in texts
    assert lean in fake.accepted
    # the other direction is the job's own: still open, still claimable
    assert p["backward"]["state"] == "open"
    assert review.open_pairs(graph / "targets" / TARGET) == [
        {"a": a, "b": b, "direction": "backward"}
    ]
    assert f"targets/{TARGET}/review/exhibits/{e['id']}.lean" in summary["written"]


def test_a_backward_proof_names_the_directions_first_candidate(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    put_record(graph, a, b, "backward")
    fake = fake_for(a, b)
    run(graph, fake, tmp_path / "work")
    p = in_force(graph, a, b)
    assert p["forward"]["state"] == "open"
    back = p["backward"]
    assert back["state"] == "proved"
    e = exhibit(graph, back["exhibit"])
    assert (e["candidate"], e["test"]) == (b, a)
    # the guard cleared the hypothesis of the direction's first claim, b's
    texts = pair_proof_texts(fake)
    lean = (base(graph) / "exhibits" / e["lean_file"]).read_text()
    assert pair_proofs.guarded(lean, cand(graph, b)) in texts


def test_both_directions_contributed_make_one_cluster(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    put_record(graph, a, b, "forward")
    put_record(graph, a, b, "backward")
    summary = run(graph, fake_for(a, b), tmp_path / "work")
    assert review.equivalent(in_force(graph, a, b))
    assert summary["clusters"] == [[a, b]]
    assert review.derive(graph / "targets" / TARGET)["clusters"] == [[a, b]]


def test_an_open_direction_on_record_takes_the_record(tmp_path: Path) -> None:
    """The ordinary order: the job left the direction open (its own attempt at this budget, which
    alone would stand), then the record merged; the job writes a second pair record, the
    supersession rule reads it as in force, and a third run writes nothing."""
    graph, a, b = setup(tmp_path)
    fake = fake_for(a, b)
    run(graph, fake, tmp_path / "w1")
    first = in_force(graph, a, b)
    assert first["forward"]["state"] == "open"
    assert first["forward"]["attempt"]["who"] == "gate"
    put_record(graph, a, b, "forward")
    summary = run(graph, fake, tmp_path / "w2")
    assert f"targets/{TARGET}/review/pairs/{a}--{b}--{DATE}-2.yaml" in summary["written"]
    p = in_force(graph, a, b)
    assert p["forward"]["state"] == "proved"
    assert p["backward"] == first["backward"]
    before = tree(graph)
    assert run(graph, fake, tmp_path / "w3")["written"] == []
    assert tree(graph) == before


def test_a_second_run_writes_nothing_and_rechecks_nothing(tmp_path: Path) -> None:
    """R13, after ``test_pairs_are_not_attempted_again``: the settled direction stands, so the
    record's Lean is not elaborated again."""
    graph, a, b = setup(tmp_path)
    put_record(graph, a, b, "forward")
    fake = fake_for(a, b)
    run(graph, fake, tmp_path / "w1")
    before, n = tree(graph), len(fake.texts)
    assert run(graph, fake, tmp_path / "w2")["written"] == []
    assert tree(graph) == before
    assert pair_proof_texts(fake, n) == []


# --- a refutation ------------------------------------------------------------------------------


def test_a_merged_refutation_is_refuted_and_raises_its_question(tmp_path: Path) -> None:
    """The exhibit's Lean carries the template's ``-- opn-review:`` header with its case, so
    ``review_questions.raise_questions`` asks it of the intent signer like the job's own. The
    instance is past the agreement cases (n < 4): a case a test is already on record for is not
    asked again, the job's own refutations included."""
    graph, a, b = setup(tmp_path)
    stem = put_record(graph, a, b, "backward", kind="refutation", n=7, proof="  decide\n")
    summary = run(graph, fake_for(a, b), tmp_path / "work")
    back = in_force(graph, a, b)["backward"]
    assert back["state"] == "refuted" and back["attempt"] is None
    e = exhibit(graph, back["exhibit"])
    assert (e["kind"], e["candidate"], e["test"], e["result"]) == ("pair", b, a, "refuted")
    assert "n = 7" in e["detail"] and AUTHOR in e["detail"] and stem in e["detail"]
    lean = (base(graph) / "exhibits" / e["lean_file"]).read_text()
    assert review_lean.case_of(lean) == review_lean.Case("holds", 7)
    questions = [yaml.safe_load(p.read_text()) for p in (base(graph) / "questions").glob("*.yaml")]
    (q,) = [q for q in questions if q["raised_by"]["ref"] == e["id"]]
    assert q["raised_by"]["kind"] == "disagreement"
    assert q["question"] == review_lean.Case("holds", 7).question()
    assert q["id"] in summary["questions_raised"]


def test_a_refutation_is_not_guarded(tmp_path: Path) -> None:
    """A refutation has no hypothesis: it is elaborated once, and no guarded copy exists."""
    graph, a, b = setup(tmp_path)
    put_record(graph, a, b, "forward", kind="refutation", n=2, proof="  decide\n")
    fake = fake_for(a, b)
    run(graph, fake, tmp_path / "work")
    assert in_force(graph, a, b)["forward"]["state"] == "refuted"
    assert [t for t in pair_proof_texts(fake) if "; clear h" in t] == []


# --- a re-check that fails: the direction stays open, the attempt says why ----------------------


def failed(graph: Path, a: str, b: str, direction: str = "forward") -> dict[str, Any]:
    d = in_force(graph, a, b)[direction]
    assert d["state"] == "open" and d["exhibit"] is None, d
    attempt: dict[str, Any] = d["attempt"]
    return attempt


def no_contributed_exhibit(graph: Path) -> None:
    folder = base(graph) / "exhibits"
    found = [
        e
        for e in (json.loads(p.read_text()) for p in folder.glob("*.json"))
        if AUTHOR in e["detail"]
    ]
    assert found == []


def test_a_proof_the_kernel_refuses_leaves_the_direction_open(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    stem = put_record(graph, a, b, proof="  -- fake: refused\n  exact h\n")
    fake = fake_for(a, b)
    run(graph, fake, tmp_path / "w1")
    att = failed(graph, a, b)
    assert att["who"] == AUTHOR
    assert stem in att["tool"] and "does not elaborate" in att["tool"]
    assert att["budget_s"] == 5
    no_contributed_exhibit(graph)
    # and the failure is stable: a second run writes nothing
    before = tree(graph)
    assert run(graph, fake, tmp_path / "w2")["written"] == []
    assert tree(graph) == before


def test_a_proof_with_a_sorry_warning_is_refused(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    put_record(graph, a, b, proof="  -- fake: sorry\n  exact h\n")
    run(graph, fake_for(a, b), tmp_path / "work")
    assert "does not elaborate" in failed(graph, a, b)["tool"]


def test_a_degenerate_proof_is_refused_by_the_guard(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    stem = put_record(graph, a, b, proof="  -- fake: degenerate\n  exact h\n")
    run(graph, fake_for(a, b), tmp_path / "work")
    att = failed(graph, a, b)
    assert stem in att["tool"] and "degenerate guard" in att["tool"]
    no_contributed_exhibit(graph)


def test_a_file_off_its_template_is_refused_before_any_lean(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    tmpl = pair_proofs.template(cand(graph, a), cand(graph, b), "forward")
    bad = fill(tmpl).replace(f"C_{b.replace('-', '_')}_p.claim n :=", "True :=")
    assert bad != fill(tmpl)
    stem = put_record(graph, a, b, lean=bad)
    fake = fake_for(a, b)
    run(graph, fake, tmp_path / "work")
    att = failed(graph, a, b)
    assert stem in att["tool"] and "template" in att["tool"]
    assert bad not in fake.texts


def test_a_forbidden_region_is_refused_before_any_lean(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    stem = put_record(graph, a, b, proof="  exact h\naxiom cheat : False\n")
    fake = fake_for(a, b)
    run(graph, fake, tmp_path / "work")
    att = failed(graph, a, b)
    assert stem in att["tool"] and "column 0" in att["tool"]
    assert pair_proof_texts(fake) == []


def test_a_kind_its_case_does_not_fit_is_refused(tmp_path: Path) -> None:
    """``pair-proof/v1`` lets a proof carry a case; the template refuses it (a proof takes no
    instance), and so does the job."""
    graph, a, b = setup(tmp_path)
    tmpl = pair_proofs.template(cand(graph, a), cand(graph, b), "forward")
    stem = put_record(graph, a, b, lean=fill(tmpl), case=review_lean.Case("holds", 2).key())
    run(graph, fake_for(a, b), tmp_path / "work")
    att = failed(graph, a, b)
    assert stem in att["tool"] and "no instance" in att["tool"]


def test_a_record_for_another_direction_is_its_own(tmp_path: Path) -> None:
    """A record filed as ``backward`` whose Lean is the forward template is off its template."""
    graph, a, b = setup(tmp_path)
    forward = fill(pair_proofs.template(cand(graph, a), cand(graph, b), "forward"))
    stem = put_record(graph, a, b, "backward", lean=forward)
    run(graph, fake_for(a, b), tmp_path / "work")
    assert stem in failed(graph, a, b, "backward")["tool"]
    assert in_force(graph, a, b)["forward"]["attempt"]["who"] == "gate"


# --- which records the job reads ---------------------------------------------------------------


def test_a_record_whose_hashes_no_longer_match_is_ignored_with_a_note(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    stem = put_record(graph, a, b, hashes={"a": "0" * 64, "b": statement_hash(graph, b)})
    fake = fake_for(a, b)
    summary = run(graph, fake, tmp_path / "work")
    fwd = in_force(graph, a, b)["forward"]
    assert fwd["state"] == "open" and fwd["attempt"]["who"] == "gate"
    assert pair_proof_texts(fake) == []
    assert any(stem in n and "statement hash" in n for n in summary["notes"]), summary["notes"]


def test_of_several_passing_records_the_first_by_date_then_name_settles(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    late = put_record(graph, a, b, author="t-late", date="2026-10-27T03:00:00Z")
    early = put_record(graph, a, b, author="t-early", date="2026-10-27T02:00:00Z")
    tie = put_record(graph, a, b, author="t-a-tie", date="2026-10-27T03:00:00Z")
    summary = run(graph, fake_for(a, b), tmp_path / "work")
    e = exhibit(graph, in_force(graph, a, b)["forward"]["exhibit"])
    assert early in e["detail"] and "t-early" in e["detail"]
    assert any(late in n and "already settled" in n for n in summary["notes"])
    assert any(tie in n and "already settled" in n for n in summary["notes"])


def test_a_failing_first_record_does_not_block_a_passing_later_one(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    bad = put_record(
        graph, a, b, author="t-bad", date="2026-10-27T01:00:00Z", proof="  -- fake: refused\n"
    )
    good = put_record(graph, a, b, author="t-good", date="2026-10-27T02:00:00Z")
    summary = run(graph, fake_for(a, b), tmp_path / "work")
    e = exhibit(graph, in_force(graph, a, b)["forward"]["exhibit"])
    assert good in e["detail"]
    assert any(bad in n and "does not elaborate" in n for n in summary["notes"])


def test_a_record_for_a_settled_direction_is_not_rechecked(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    put_record(graph, a, b, "forward")
    fake = fake_for(a, b)
    run(graph, fake, tmp_path / "w1")
    later = put_record(graph, a, b, "forward", author="t-second", date="2026-10-28T00:00:00Z")
    n = len(fake.texts)
    summary = run(graph, fake, tmp_path / "w2")
    assert summary["written"] == []
    assert pair_proof_texts(fake, n) == []
    assert any(later in n and "already settled" in n for n in summary["notes"])


def test_a_record_off_the_surviving_pairs_is_not_read(tmp_path: Path) -> None:
    """Only a direction between two surviving candidates takes a record: here ``b`` is discarded
    (its statement screen fires), so the job compares no pair and the record is noted unread."""
    graph, a, b = setup(tmp_path)
    stem = put_record(graph, a, b, "forward")
    fake = ReviewFake(models={a: Model(legendre()), b: Model(legendre(), provable=True)})
    summary = run(graph, fake, tmp_path / "work")
    assert review.latest_pairs(base(graph)) == []
    assert pair_proof_texts(fake) == []
    assert any(stem in n and "surviving" in n for n in summary["notes"]), summary["notes"]


def test_a_malformed_record_is_noted_and_not_read(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    folder = base(graph) / pair_proofs.DIR
    folder.mkdir(parents=True)
    (folder / f"{a}--{b}--forward--20261027T010000Z-x.yaml").write_text(
        yaml.safe_dump({"schema": "pair-proof/v1", "a": a})
    )
    summary = run(graph, fake_for(a, b), tmp_path / "work")
    assert in_force(graph, a, b)["forward"]["attempt"]["who"] == "gate"
    assert any("not a pair-proof/v1 record" in n for n in summary["notes"])


def test_the_job_writes_nothing_under_pair_proofs(tmp_path: Path) -> None:
    """The record is the contributor's; the job only reads it (R13: it writes exhibits, tests,
    questions and pairs)."""
    graph, a, b = setup(tmp_path)
    put_record(graph, a, b, "forward")
    summary = run(graph, fake_for(a, b), tmp_path / "work")
    assert not [p for p in summary["written"] if f"/{pair_proofs.DIR}/" in p]


def test_a_merged_pair_proof_re_runs_the_review_job() -> None:
    """``postmerge.review_targets`` names the target of a merged pair-proof record, so the job
    that consumes it runs after the merge; a deletion re-runs nothing."""
    name = pair_proofs.record_name(
        "c-aaaaaaaa", "c-bbbbbbbb", "forward", "20261027T010000Z", AUTHOR
    )
    path = f"targets/{TARGET}/review/{pair_proofs.DIR}/{name}"
    assert postmerge.review_targets([Change("A", path)]) == [TARGET]
    assert postmerge.review_targets([Change("D", path)]) == []


def test_contributed_answers_none_when_no_record_speaks(tmp_path: Path) -> None:
    graph, a, b = setup(tmp_path)
    spec = json.loads((graph / "targets" / TARGET / "gate-spec.json").read_text())
    runner = review_lean.Runner(fake_for(a, b), FAKE_RESOLVED, tmp_path / "w", budget_s=5, jobs=1)
    job = review_job.open_job(graph, TARGET, runner, spec, review_job.Settings(date=DATE))
    assert isinstance(job, review_job.Job)
    assert review_pairs.contributed(job, cand(graph, a), cand(graph, b), "forward", 5) is None
