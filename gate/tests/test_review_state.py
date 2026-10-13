"""F26-T2 / AC2: the review's state is derived from its records alone (F26-R1, R7, R17;
D-9 v3.39; F08-T10's principle) — surviving candidates are those no exhibit discards and the
format rule does not return, clusters are the components of both-directions-proved pairs over
the survivors, the signers are the latest accept per role, and the state names what is under
way. The same records in any order give the same state, and each rule is shown load-bearing by
a mutant that drops it (the F11-T7 pattern: a monkeypatch in memory, no file touched).

Every record the builder writes validates against its schema, so the scenarios are real records.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from opn_gate import review, schemas
from opn_gate.paths import REVIEW_DIR

T = "propositional"
DAY = "2026-10-12"
SIG = "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n"
TOOL = {"toolchain": "leanprover/lean4:v4.33.1", "mathlib_sha": None, "run": "local"}

# candidate ids: one person's and two models'
A, B, C = "c-aaaaaaaa", "c-bbbbbbbb", "c-cccccccc"


def exhibit_id(kind: str, candidate: str, result: str, test: str | None = None) -> str:
    """An exhibit's id from what it says, as the job names them (``e-<8 hex>``), so the same
    exhibit written in any order is the same record."""
    digest = hashlib.sha256(f"{kind}:{candidate}:{result}:{test}".encode()).hexdigest()
    return f"e-{digest[:8]}"


def _dump(path: Path, doc: dict[str, Any], name: str) -> None:
    assert schemas.violations(doc, name) == [], (name, schemas.violations(doc, name))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".json":
        path.write_text(json.dumps(doc, indent=1))
    else:
        path.write_text(yaml.safe_dump(doc, sort_keys=False))


class Review:
    """Writes one review's records under ``<target_dir>/review/``, each schema-checked."""

    def __init__(self, target_dir: Path, *, role: str = "network", identity: str = "network"):
        self.dir = target_dir
        self.base = target_dir / REVIEW_DIR
        _dump(
            self.base / "review.yaml",
            {
                "schema": "review/v1",
                "target": T,
                "opened_by": {"identity": identity, "role": role},
                "date": DAY,
                "words": "For all p q, p and q implies q and p.",
                "cases": [],
                "concepts": ["And"],
                "source": {"kind": "existing", "ref": "tutorial-and-swap"},
                "tracking": None,
                "supersedes": None,
            },
            "review/v1",
        )

    def candidate(
        self, cid: str, author: str, method: str = "agent", *, compiled: bool = True
    ) -> None:
        """A candidate on record; ``compiled`` also records the job's passing compile, which is
        what stage 3 needs before a candidate can survive (F26-T14: a candidate the job has not
        compiled is pending)."""
        if compiled:
            self.exhibit("compile", cid, "pass")
        _dump(
            self.base / "candidates" / f"{cid}.yaml",
            {
                "schema": "candidate/v1",
                "target": T,
                "id": cid,
                "author": author,
                "method": method,
                "models": [] if method == "manual" else ["claude-opus-5.5"],
                "read_others": False,
                "origin": "submitted",
                "source": None,
                "lean_file": f"{cid}.lean",
                "statement_hash": "0" * 64,
                "date": DAY,
            },
            "candidate/v1",
        )

    def exhibit(self, kind: str, candidate: str, result: str, test: str | None = None) -> str:
        eid = exhibit_id(kind, candidate, result, test)
        _dump(
            self.base / "exhibits" / f"{eid}.json",
            {
                "schema": "exhibit/v1",
                "target": T,
                "id": eid,
                "kind": kind,
                "candidate": candidate,
                "test": test,
                "result": result,
                "detail": f"{kind} {result}",
                "lean_file": None if result in ("returned", "error") else f"{eid}.lean",
                "date": DAY,
                **TOOL,
            },
            "exhibit/v1",
        )
        return eid

    def pair(self, a: str, b: str, forward: str = "open", backward: str = "open") -> None:
        """``forward`` is a implies b, ``backward`` b implies a (pair/v1); a is the smaller id."""
        a, b, forward, backward = (a, b, forward, backward) if a < b else (b, a, backward, forward)

        def direction(state: str) -> dict[str, Any]:
            if state == "open":
                return {
                    "state": state,
                    "exhibit": None,
                    "attempt": {"who": "gate", "tool": "grind", "budget_s": 20},
                }
            return {"state": state, "exhibit": self.exhibit("pair", a, state, b), "attempt": None}

        _dump(
            self.base / "pairs" / f"{a}--{b}.yaml",
            {
                "schema": "pair/v1",
                "target": T,
                "a": a,
                "b": b,
                "forward": direction(forward),
                "backward": direction(backward),
                "date": DAY,
            },
            "pair/v1",
        )

    def question(self, qid: str) -> None:
        _dump(
            self.base / "questions" / f"{qid}.yaml",
            {
                "schema": "review-question/v1",
                "target": T,
                "id": qid,
                "question": "Suppose 5 were the only prime. Would the conjecture hold at n = 2?",
                "raised_by": {"kind": "mutant", "ref": "e-deadbeef"},
                "asked_to": "intent",
                "date": DAY,
            },
            "review-question/v1",
        )

    def answer(self, qid: str, login: str = "alice") -> None:
        aid = f"a-{qid[2:]}"
        _dump(
            self.base / "answers" / f"{aid}.yaml",
            {
                "schema": "review-answer/v1",
                "target": T,
                "id": aid,
                "question": qid,
                "answer": "No.",
                "cites": None,
                "date": DAY,
                "login": login,
                "via": "approval-key",
                "key": "ssh-ed25519 AAAA",
                "signature": SIG,
            },
            "review-answer/v1",
        )

    def signature(
        self,
        role: str,
        decision: str,
        login: str,
        *,
        cluster: str | None = A,
        question: str | None = None,
        date: str = DAY,
        n: int = 1,
    ) -> None:
        _dump(
            self.base / "signatures" / f"{role}-{date}-{n}.yaml",
            {
                "schema": "review-signature/v1",
                "target": T,
                "role": role,
                "decision": decision,
                "cluster": None if decision == "send-back" else cluster,
                "question": question,
                "date": date,
                "login": login,
                "via": "approval-key",
                "key": "ssh-ed25519 AAAA",
                "signature": SIG,
            },
            "review-signature/v1",
        )


def fate(d: Path) -> dict[str, tuple[str, str | None]]:
    return {c["id"]: (c["status"], c["exhibit"]) for c in review.derive(d)["candidates"]}


def clusters(d: Path) -> list[list[str]]:
    return sorted(sorted(c) for c in review.derive(d)["clusters"])


# --- AC2, as the spec words it -----------------------------------------------------------


def ac2_records(d: Path, *, reverse: bool = False) -> Review:
    """Three candidates (one person's, two models'), two exhibits discarding one, a signature;
    plus one pair and one question so that the clusters and the waiting count mean something."""
    r = Review(d)
    steps: list[Callable[[], Any]] = [
        lambda: r.candidate(A, "alice", "manual"),
        lambda: r.candidate(B, "bob"),
        lambda: r.candidate(C, "carol"),
        lambda: r.exhibit("compile", B, "pass"),
        lambda: r.exhibit("screen", C, "fail"),
        lambda: r.exhibit("intent-test", C, "fail", test="t-89abcdef"),
        lambda: r.pair(A, B, "proved", "proved"),
        lambda: r.question("q-1"),
        lambda: r.signature("independent", "accept", "dave"),
    ]
    for step in reversed(steps) if reverse else steps:
        step()
    return r


def test_ac2_the_state_names_the_survivors_the_discard_and_the_grade(tmp_path: Path) -> None:
    ac2_records(tmp_path)
    full = review.derive(tmp_path)
    assert fate(tmp_path) == {
        A: ("surviving", None),
        B: ("surviving", None),
        # the first exhibit (by id) that discarded it
        C: (
            "discarded",
            min(
                exhibit_id("screen", C, "fail"), exhibit_id("intent-test", C, "fail", "t-89abcdef")
            ),
        ),
    }
    assert clusters(tmp_path) == [[A, B]]
    assert full["questions_waiting"] == ["q-1"]
    assert full["signers"] == {"intent": None, "independent": "dave"}
    assert full["grade_cap"] is None  # alice's candidate is a person's and survives
    # the opening is the network's, nobody has answered or signed as intent: Q5's state
    assert full["state"] == "needs-intent-signer"
    doc = review.state_of(tmp_path)
    assert doc == {
        "state": "needs-intent-signer",
        "candidates": 3,
        "surviving": 2,
        "clusters": 1,
        "questions_waiting": 1,
        "open_pairs": 0,
        "grade_cap": None,
        "signers": {"intent": None, "independent": "dave"},
        "tracking": None,
    }
    assert schemas.violations(doc, "graph/v9") != []  # a field, not a document
    # the grade: the review is not complete, so nothing above the floor is earned
    assert review.grade_of(tmp_path, "mechanical-only") == "mechanical-only"


def test_ac2_the_same_records_in_another_order_give_the_same_state(tmp_path: Path) -> None:
    ac2_records(tmp_path / "forward")
    ac2_records(tmp_path / "reverse", reverse=True)
    assert review.derive(tmp_path / "forward") == review.derive(tmp_path / "reverse")
    assert review.state_of(tmp_path / "forward") == review.state_of(tmp_path / "reverse")
    assert review.derive(tmp_path / "forward")["state"] == "needs-intent-signer"


def test_ac2_an_answer_completes_the_review_and_earns_the_second_rung(tmp_path: Path) -> None:
    r = ac2_records(tmp_path)
    r.answer("q-1")
    assert review.state_of(tmp_path)["state"] == "complete"
    assert review.grade_of(tmp_path, "mechanical-only") == "screened-and-signed"


# --- scenarios: one rule each, also driven by the mutants ----------------------------------


def scenario_a_pass_exhibit_discards_nothing(d: Path) -> None:
    r = Review(d)
    r.candidate(A, "alice", "manual")
    r.exhibit("compile", A, "pass")
    r.exhibit("screen", A, "pass")
    r.exhibit("intent-test", A, "pass", test="t-89abcdef")
    assert fate(d) == {A: ("surviving", None)}


def scenario_each_discarding_kind_discards(d: Path) -> None:
    r = Review(d)
    for cid, kind in ((A, "compile"), (B, "screen"), (C, "intent-test")):
        r.candidate(cid, "alice")
        r.exhibit(kind, cid, "fail", test="t-89abcdef" if kind == "intent-test" else None)
    assert {k: v[0] for k, v in fate(d).items()} == {A: "discarded", B: "discarded", C: "discarded"}


def scenario_an_error_exhibit_decides_nothing(d: Path) -> None:
    r = Review(d)
    r.candidate(A, "alice")
    r.exhibit("compile", A, "error")
    r.exhibit("screen", A, "error")
    assert fate(d) == {A: ("surviving", None)}


def scenario_a_pair_or_mutant_exhibit_never_discards(d: Path) -> None:
    """A mutant's failed test is about the mutant; a pair exhibit is about a direction."""
    r = Review(d)
    r.candidate(A, "alice")
    r.exhibit("mutant", A, "fail", test="t-89abcdef")
    r.exhibit("pair", A, "refuted", test=B)
    assert fate(d) == {A: ("surviving", None)}


def scenario_a_returned_candidate_is_neither_surviving_nor_discarded(d: Path) -> None:
    r = Review(d)
    r.candidate(A, "alice", "manual")
    r.candidate(B, "bob")
    r.exhibit("format", B, "returned")
    assert fate(d) == {A: ("surviving", None), B: ("returned", exhibit_id("format", B, "returned"))}
    assert clusters(d) == [[A]]
    assert review.state_of(d)["surviving"] == 1


def scenario_one_proved_direction_is_not_a_cluster(d: Path) -> None:
    r = Review(d)
    r.candidate(A, "alice")
    r.candidate(B, "bob")
    r.pair(A, B, "proved", "refuted")
    assert clusters(d) == [[A], [B]]
    r.pair(B, C, "proved", "open")
    r.candidate(C, "carol")
    assert clusters(d) == [[A], [B], [C]]


def scenario_equivalence_is_transitive(d: Path) -> None:
    """A proved equal to B and B to C, no pair between A and C: one cluster."""
    r = Review(d)
    for cid in (A, B, C):
        r.candidate(cid, "alice")
    r.pair(A, B, "proved", "proved")
    r.pair(B, C, "proved", "proved")
    assert clusters(d) == [[A, B, C]]
    assert review.state_of(d)["clusters"] == 1


def scenario_a_discarded_candidate_is_in_no_cluster(d: Path) -> None:
    r = Review(d)
    for cid in (A, B, C):
        r.candidate(cid, "alice")
    r.pair(A, C, "proved", "proved")
    r.exhibit("screen", C, "fail")
    assert clusters(d) == [[A], [B]]
    assert review.state_of(d)["clusters"] == 2


def scenario_complete_needs_no_question_waiting(d: Path) -> None:
    r = Review(d, role="proposer", identity="alice")
    r.candidate(A, "alice", "manual")
    assert review.state_of(d)["state"] == "complete"
    r.question("q-1")
    assert review.state_of(d)["state"] == "open"
    r.answer("q-1")
    assert review.state_of(d)["state"] == "complete"


def scenario_complete_needs_exactly_one_cluster(d: Path) -> None:
    r = Review(d, role="proposer", identity="alice")
    r.candidate(A, "alice", "manual")
    r.candidate(B, "bob")
    assert review.state_of(d)["state"] == "open"
    r.pair(A, B, "proved", "proved")
    assert review.state_of(d)["state"] == "complete"


def scenario_no_survivor_is_not_complete(d: Path) -> None:
    r = Review(d, role="proposer", identity="alice")
    r.candidate(A, "alice", "manual")
    r.exhibit("compile", A, "fail")
    assert review.state_of(d)["state"] == "open"


def scenario_needs_intent_signer_only_for_the_network_opening(d: Path) -> None:
    r = Review(d, role="proposer", identity="alice")
    r.candidate(A, "alice", "manual")
    r.question("q-1")
    assert review.state_of(d)["state"] == "open"


def scenario_an_answer_shows_someone_can_answer(d: Path) -> None:
    r = Review(d)
    r.candidate(A, "alice", "manual")
    r.question("q-1")
    r.question("q-2")
    assert review.state_of(d)["state"] == "needs-intent-signer"
    r.answer("q-1")
    assert review.state_of(d)["state"] == "open"


def scenario_an_intent_send_back_shows_someone_can_answer(d: Path) -> None:
    r = Review(d)
    r.candidate(A, "alice", "manual")
    r.question("q-1")
    r.signature("intent", "send-back", "alice", question="q-1")
    assert review.state_of(d)["state"] == "open"
    assert review.state_of(d)["signers"]["intent"] is None


def scenario_the_latest_signature_per_role_decides(d: Path) -> None:
    r = Review(d)
    r.candidate(A, "alice", "manual")
    r.signature("intent", "accept", "alice", date="2026-10-12")
    assert review.state_of(d)["signers"]["intent"] == "alice"
    r.signature("intent", "send-back", "alice", question="q-1", date="2026-10-13")
    assert review.state_of(d)["signers"]["intent"] is None
    r.signature("intent", "accept", "alice", date="2026-10-13", n=2)
    assert review.state_of(d)["signers"]["intent"] == "alice"


def scenario_a_signature_fills_its_own_role(d: Path) -> None:
    r = Review(d)
    r.candidate(A, "alice", "manual")
    r.signature("independent", "accept", "dave")
    assert review.state_of(d)["signers"] == {"intent": None, "independent": "dave"}


def scenario_the_cap_reads_the_surviving_cluster(d: Path) -> None:
    """A person's candidate that was discarded lifts no cap; one that survives does."""
    r = Review(d)
    r.candidate(A, "alice", "manual")
    r.candidate(B, "bob")
    r.exhibit("screen", A, "fail")
    assert review.state_of(d)["grade_cap"] == "screened-and-signed"
    r.candidate(C, "carol", "manual")
    r.pair(B, C, "proved", "proved")
    assert review.state_of(d)["grade_cap"] is None


def scenario_the_cap_reads_the_largest_cluster(d: Path) -> None:
    r = Review(d)
    r.candidate(A, "alice", "manual")
    r.candidate(B, "bob")
    r.candidate(C, "carol")
    r.pair(B, C, "proved", "proved")
    assert review.state_of(d)["grade_cap"] == "screened-and-signed"


def scenario_open_pairs_and_context_still_work(d: Path) -> None:
    r = Review(d)
    r.candidate(A, "alice", "manual")
    r.candidate(B, "bob")
    r.pair(A, B, "proved", "open")
    r.question("q-1")
    assert review.open_pairs(d) == [{"a": A, "b": B, "direction": "backward"}]
    assert review.state_of(d)["open_pairs"] == 1
    ctx = review.for_context(d)
    assert ctx is not None and ctx["state"] == "needs-intent-signer"
    assert [q["id"] for q in ctx["questions_waiting"]] == ["q-1"]


def scenario_a_candidate_the_job_has_not_compiled_is_pending(d: Path) -> None:
    """F26-T14 (2026-10-13): the 27 background reviews opened on the live graph derived
    ``complete`` with their one candidate surviving before the job had run, so review.yml found
    no open review and never ran. Stage 3 is the job's: no passing compile, no survivor."""
    r = Review(d)
    r.candidate(A, "network", compiled=False)
    assert fate(d) == {A: ("pending", None)}
    state = review.state_of(d)
    assert (state["state"], state["surviving"], state["clusters"]) == ("open", 0, 0)


def scenario_a_compile_error_leaves_the_candidate_pending(d: Path) -> None:
    """An ``error`` decides nothing: the candidate is neither discarded nor through stage 3."""
    r = Review(d)
    r.candidate(A, "alice", compiled=False)
    r.exhibit("compile", A, "error")
    assert fate(d) == {A: ("pending", None)}
    assert review.state_of(d)["state"] == "open"


def scenario_a_discard_needs_no_compile_pass(d: Path) -> None:
    r = Review(d)
    r.candidate(A, "alice", compiled=False)
    eid = r.exhibit("compile", A, "fail")
    assert fate(d) == {A: ("discarded", eid)}


SCENARIOS: dict[str, Callable[[Path], None]] = {
    k[len("scenario_") :]: v for k, v in dict(globals()).items() if k.startswith("scenario_")
}


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario(tmp_path: Path, name: str) -> None:
    SCENARIOS[name](tmp_path)


# --- the mutants: each rule is load-bearing ------------------------------------------------


def _mutant_any_exhibit_discards(ex: dict[str, Any]) -> bool:
    return ex.get("kind") in review.DISCARDING_KINDS


def _mutant_error_discards(ex: dict[str, Any]) -> bool:
    return ex.get("kind") in review.DISCARDING_KINDS and ex.get("result") in ("fail", "error")


def _mutant_any_kind_discards(ex: dict[str, Any]) -> bool:
    return ex.get("result") == "fail"


def _mutant_format_discards(ex: dict[str, Any]) -> bool:
    return ex.get("result") in ("fail", "returned")


def _mutant_nothing_is_returned(ex: dict[str, Any]) -> bool:
    return False


def _mutant_one_direction_is_enough(pair: dict[str, Any]) -> bool:
    return any(
        isinstance(pair.get(d), dict) and pair[d].get("state") == "proved"
        for d in ("forward", "backward")
    )


def _mutant_no_transitivity(ids: set[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    out: list[list[str]] = []
    for cid in sorted(ids):
        members = {cid} | {b for a, b in edges if a == cid} | {a for a, b in edges if b == cid}
        members &= ids
        if sorted(members) not in out:
            out.append(sorted(members))
    return out


def _mutant_complete_ignores_questions(
    head: dict[str, Any], n_clusters: int, waiting: int, can_answer: bool
) -> str:
    if n_clusters == 1:
        return review.COMPLETE
    if waiting and not can_answer and head.get("opened_by", {}).get("role") == "network":
        return review.NEEDS_INTENT
    return review.OPEN


def _mutant_complete_with_any_cluster(
    head: dict[str, Any], n_clusters: int, waiting: int, can_answer: bool
) -> str:
    if n_clusters >= 1 and not waiting:
        return review.COMPLETE
    if waiting and not can_answer and head.get("opened_by", {}).get("role") == "network":
        return review.NEEDS_INTENT
    return review.OPEN


def _mutant_needs_signer_ignores_role(
    head: dict[str, Any], n_clusters: int, waiting: int, can_answer: bool
) -> str:
    if n_clusters == 1 and not waiting:
        return review.COMPLETE
    if waiting and not can_answer:
        return review.NEEDS_INTENT
    return review.OPEN


def _mutant_needs_signer_ignores_who_can_answer(
    head: dict[str, Any], n_clusters: int, waiting: int, can_answer: bool
) -> str:
    if n_clusters == 1 and not waiting:
        return review.COMPLETE
    if waiting and head.get("opened_by", {}).get("role") == "network":
        return review.NEEDS_INTENT
    return review.OPEN


def _mutant_first_signature_wins(sigs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for s in sigs:
        out.setdefault(str(s.get("role")), s)
    return out


def _mutant_any_accept_counts(sigs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for s in sigs:
        if s.get("decision") == "accept":
            out[str(s.get("role"))] = s
    return out


_real_latest_signatures = review.latest_signatures  # bound before any mutant replaces it


def _mutant_role_blind_signers(sigs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest = _real_latest_signatures(sigs)
    if len(latest) == 1:
        (only,) = latest.values()
        return {"intent": only, "independent": only}
    return latest


def _mutant_never_capped(members: list[dict[str, Any]]) -> str | None:
    return None


def _mutant_always_capped(members: list[dict[str, Any]]) -> str | None:
    return review.CAP


def _mutant_no_compile_needed(ex: dict[str, Any]) -> bool:
    return True


def _mutant_any_compile_exhibit_counts(ex: dict[str, Any]) -> bool:
    return ex.get("kind") == "compile"


@pytest.mark.parametrize(
    ("where", "attr", "mutant"),
    [
        (review, "discards", _mutant_any_exhibit_discards),
        (review, "discards", _mutant_error_discards),
        (review, "discards", _mutant_any_kind_discards),
        (review, "discards", _mutant_format_discards),
        (review, "returns", _mutant_nothing_is_returned),
        (review, "equivalent", _mutant_one_direction_is_enough),
        (review, "components", _mutant_no_transitivity),
        (review, "state_rule", _mutant_complete_ignores_questions),
        (review, "state_rule", _mutant_complete_with_any_cluster),
        (review, "state_rule", _mutant_needs_signer_ignores_role),
        (review, "state_rule", _mutant_needs_signer_ignores_who_can_answer),
        (review, "latest_signatures", _mutant_first_signature_wins),
        (review, "latest_signatures", _mutant_any_accept_counts),
        (review, "latest_signatures", _mutant_role_blind_signers),
        (review, "cap_rule", _mutant_never_capped),
        (review, "cap_rule", _mutant_always_capped),
        (review, "compiled", _mutant_no_compile_needed),
        (review, "compiled", _mutant_any_compile_exhibit_counts),
    ],
    ids=[
        "any-exhibit-discards",
        "error-discards",
        "any-kind-discards",
        "format-discards",
        "nothing-is-returned",
        "one-direction-is-enough",
        "no-transitivity",
        "complete-ignores-questions",
        "complete-with-any-cluster",
        "needs-signer-ignores-role",
        "needs-signer-ignores-who-can-answer",
        "first-signature-wins",
        "any-accept-counts",
        "role-blind-signers",
        "never-capped",
        "always-capped",
        "no-compile-needed",
        "any-compile-exhibit-counts",
    ],
)
def test_each_rule_is_necessary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, where: Any, attr: str, mutant: Any
) -> None:
    monkeypatch.setattr(where, attr, mutant)
    failures = 0
    for i, (name, scenario) in enumerate(sorted(SCENARIOS.items())):
        d = tmp_path / f"{i}-{name}"
        d.mkdir()
        try:
            scenario(d)
        except AssertionError:
            failures += 1
    assert failures >= 1, "the mutant passed every scenario: a rule is untested"
