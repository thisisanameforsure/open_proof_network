"""F26-T2 / AC8: the ladder earned under the review (F26-R9, R11; D-9 v3.39's table) — the
grade is exactly the table's in every order the table allows, a target with no person-written
candidate in the surviving cluster caps at ``screened-and-signed`` with the cap shown, no grade a
target already holds is lowered, and a ``split`` by the intent signer names each cluster not
chosen as a D-30 variant with the label the pairs already prove. Each ladder rule is shown
load-bearing by a mutant (the pattern of ``test_review_state.py``).

The ladder is climbed in order (F24-Q7's rule): ``author-attested`` and above need the second
rung's non-author signature first, and the cap holds every rung above ``screened-and-signed``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from test_review_state import A, B, C, Review

from opn_gate import fidelity, review

M, S, AA, EA, P = fidelity.GRADES


def complete(d: Path, *, person: bool = True, role: str = "proposer") -> Review:
    """One surviving cluster, no question: the automated stages are done. Alice wrote the
    person's candidate (when there is one), bob the model's; dave wrote none."""
    r = Review(d, role=role, identity="alice" if role == "proposer" else "network")
    r.candidate(A, "alice", "manual" if person else "agent")
    r.candidate(B, "bob")
    r.pair(A, B, "proved", "proved")
    return r


# --- AC8: the table, in every order it allows ----------------------------------------------

Signing = list[tuple[str, str]]  # (role, login), appended in this order
TABLE: list[tuple[str, Signing, str]] = [
    ("nothing-signed", [], M),
    ("independent-only", [("independent", "dave")], S),
    ("intent-only-non-author", [("intent", "erin")], AA),
    ("intent-then-independent", [("intent", "erin"), ("independent", "dave")], EA),
    ("independent-then-intent", [("independent", "dave"), ("intent", "erin")], EA),
    ("intent-author-then-independent", [("intent", "alice"), ("independent", "dave")], EA),
]


@pytest.mark.parametrize(("name", "signing", "expected"), TABLE, ids=[t[0] for t in TABLE])
def test_ac8_the_grade_is_the_tables(
    tmp_path: Path, name: str, signing: Signing, expected: str
) -> None:
    r = complete(tmp_path)
    for n, (role, login) in enumerate(signing, start=1):
        r.signature(role, "accept", login, n=n)
    assert review.grade_of(tmp_path, M) == expected
    assert review.state_of(tmp_path)["state"] == "complete"
    assert review.state_of(tmp_path)["grade_cap"] is None


CAPPED: list[tuple[str, Signing]] = [
    ("capped-independent-only", [("independent", "dave")]),
    ("capped-intent-only", [("intent", "erin")]),
    ("capped-both", [("intent", "erin"), ("independent", "dave")]),
]


@pytest.mark.parametrize(("name", "signing"), CAPPED, ids=[t[0] for t in CAPPED])
def test_ac8_no_person_written_candidate_caps_at_the_second_rung(
    tmp_path: Path, name: str, signing: Signing
) -> None:
    r = complete(tmp_path, person=False)
    for n, (role, login) in enumerate(signing, start=1):
        r.signature(role, "accept", login, n=n)
    assert review.state_of(tmp_path)["grade_cap"] == S
    assert review.grade_of(tmp_path, M) == S


def test_ac8_the_cap_is_shown_before_anyone_signs(tmp_path: Path) -> None:
    complete(tmp_path, person=False)
    assert review.state_of(tmp_path)["grade_cap"] == S
    assert review.grade_of(tmp_path, M) == M


@pytest.mark.parametrize("held", fidelity.GRADES, ids=fidelity.GRADES)
def test_ac8_no_grade_held_today_is_lowered(tmp_path: Path, held: str) -> None:
    # no review at all: the grade is whatever the target holds
    assert review.grade_of(tmp_path / "none", held) == held
    # a review under way that has earned nothing
    r = Review(tmp_path / "open")
    r.candidate(A, "alice")
    r.question("q-1")
    assert review.state_of(tmp_path / "open")["state"] == "needs-intent-signer"
    assert review.grade_of(tmp_path / "open", held) == held
    # a review that has earned less than the target holds
    complete(tmp_path / "second").signature("independent", "accept", "dave")
    assert review.grade_of(tmp_path / "second", held) == max(held, S, key=fidelity.rank)


def test_the_top_rung_is_never_derived_here(tmp_path: Path) -> None:
    r = complete(tmp_path)
    r.signature("intent", "accept", "erin")
    r.signature("independent", "accept", "dave", n=2)
    assert review.grade_of(tmp_path, M) == EA
    assert review.grade_of(tmp_path, P) == P


def test_an_unknown_held_grade_is_refused(tmp_path: Path) -> None:
    with pytest.raises(fidelity.FidelityError):
        review.grade_of(tmp_path, "gold")


# --- scenarios: one ladder rule each, also driven by the mutants ----------------------------


def scenario_the_second_rung_needs_a_non_author(d: Path) -> None:
    """Alice wrote the surviving person's candidate; her signature alone earns nothing above
    the floor (D-9: above mechanical-only the attestor is not the author)."""
    complete(d).signature("intent", "accept", "alice")
    assert review.grade_of(d, M) == M
    assert review.state_of(d)["signers"]["intent"] == "alice"


def scenario_the_author_of_a_discarded_candidate_is_no_author(d: Path) -> None:
    r = complete(d)
    r.candidate(C, "dave")
    r.exhibit("screen", C, "fail")
    r.signature("independent", "accept", "dave")
    assert review.grade_of(d, M) == S


def scenario_the_second_rung_needs_a_complete_review(d: Path) -> None:
    r = complete(d)
    r.question("q-1")
    r.signature("independent", "accept", "dave")
    assert review.grade_of(d, M) == M
    r.answer("q-1")
    assert review.grade_of(d, M) == S


def scenario_the_third_rung_is_the_intent_signers(d: Path) -> None:
    r = complete(d)
    r.signature("independent", "accept", "dave")
    assert review.grade_of(d, M) == S
    r.signature("intent", "accept", "erin")
    assert review.grade_of(d, M) == EA


def scenario_the_fourth_rung_needs_both_roles(d: Path) -> None:
    r = complete(d)
    r.signature("intent", "accept", "erin")
    assert review.grade_of(d, M) == AA


def scenario_the_fourth_rung_needs_a_persons_candidate(d: Path) -> None:
    r = complete(d, person=False)
    r.signature("intent", "accept", "erin")
    r.signature("independent", "accept", "dave")
    assert review.grade_of(d, M) == S


def scenario_the_cap_holds_the_third_rung_too(d: Path) -> None:
    complete(d, person=False).signature("intent", "accept", "erin")
    assert review.grade_of(d, M) == S


def scenario_a_send_back_withdraws_the_signature(d: Path) -> None:
    r = complete(d)
    r.signature("intent", "accept", "erin")
    r.signature("independent", "accept", "dave", n=2)
    assert review.grade_of(d, M) == EA
    r.signature("intent", "send-back", "erin", question="q-1", date="2026-10-13")
    r.question("q-1")
    assert review.grade_of(d, M) == M
    assert review.grade_of(d, EA) == EA  # held grades are never lowered


def scenario_the_held_grade_is_kept(d: Path) -> None:
    r = complete(d)
    r.signature("independent", "accept", "dave")
    assert review.grade_of(d, EA) == EA
    assert review.grade_of(d / "none", AA) == AA


# --- R11: a split names the clusters not chosen as variants --------------------------------


def two_readings(d: Path, *, forward: str = "open", backward: str = "open") -> Review:
    """Two clusters: {A, B} and {C}; ``forward`` is A implies C, ``backward`` C implies A."""
    r = Review(d, role="proposer", identity="alice")
    r.candidate(A, "alice", "manual")
    r.candidate(B, "bob")
    r.candidate(C, "carol")
    r.pair(A, B, "proved", "proved")
    r.pair(A, C, forward, backward)
    return r


def scenario_no_split_no_variants(d: Path) -> None:
    r = two_readings(d)
    assert review.split_variants(d) == []
    r.signature("intent", "accept", "alice", cluster=A)
    assert review.split_variants(d) == []
    r.signature("independent", "split", "dave", cluster=A, n=2)  # not the intent signer's
    assert review.split_variants(d) == []


def scenario_a_split_names_the_other_cluster_as_related(d: Path) -> None:
    two_readings(d).signature("intent", "split", "alice", cluster=A)
    assert review.split_variants(d) == [
        {"representative": C, "members": [C], "relation": "related"}
    ]


def scenario_a_variant_that_implies_the_root_resolves(d: Path) -> None:
    """C implies A is proved: proving C resolves the chosen reading (D-30)."""
    two_readings(d, backward="proved").signature("intent", "split", "alice", cluster=A)
    assert review.split_variants(d) == [
        {"representative": C, "members": [C], "relation": "resolves"}
    ]


def scenario_a_variant_the_root_implies_is_partial(d: Path) -> None:
    """A implies C is proved and C implies A is refuted: C is at most as strong (D-30)."""
    two_readings(d, forward="proved", backward="refuted").signature(
        "intent", "split", "alice", cluster=A
    )
    assert review.split_variants(d) == [
        {"representative": C, "members": [C], "relation": "partial"}
    ]


def scenario_the_chosen_cluster_may_be_named_by_any_member(d: Path) -> None:
    two_readings(d, backward="proved").signature("intent", "split", "alice", cluster=B)
    assert review.split_variants(d) == [
        {"representative": C, "members": [C], "relation": "resolves"}
    ]


def scenario_a_proved_direction_from_any_member_counts(d: Path) -> None:
    """The pair proving C implies B is as good as one proving C implies A: B and A are one."""
    r = two_readings(d)
    r.pair(B, C, "open", "proved")
    r.signature("intent", "split", "alice", cluster=A)
    assert review.split_variants(d) == [
        {"representative": C, "members": [C], "relation": "resolves"}
    ]


def scenario_the_latest_intent_signature_decides_the_split(d: Path) -> None:
    r = two_readings(d)
    r.signature("intent", "split", "alice", cluster=A, date="2026-10-12")
    r.signature("intent", "accept", "alice", cluster=A, date="2026-10-13")
    assert review.split_variants(d) == []


SCENARIOS: dict[str, Callable[[Path], None]] = {
    k[len("scenario_") :]: v for k, v in dict(globals()).items() if k.startswith("scenario_")
}


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario(tmp_path: Path, name: str) -> None:
    SCENARIOS[name](tmp_path)


# --- the mutants: each ladder rule is load-bearing ------------------------------------------

# bound before any mutant replaces them, so a mutant that drops one rule keeps the others
_real_earned = review.earned
_real_relation = review.relation
_real_latest_signatures = review.latest_signatures


def _mutant_any_signer_is_independent(
    state: str, signers: dict[str, str | None], authors: set[str], cap: str | None
) -> str:
    return _real_earned(state, signers, set(), cap)


def _mutant_ignores_the_state(
    state: str, signers: dict[str, str | None], authors: set[str], cap: str | None
) -> str:
    return _real_earned(review.COMPLETE, signers, authors, cap)


def _mutant_either_role_attests(
    state: str, signers: dict[str, str | None], authors: set[str], cap: str | None
) -> str:
    both = {"intent": signers["intent"] or signers["independent"], "independent": None}
    return _real_earned(state, both, authors, cap)


def _mutant_cap_only_holds_the_top(
    state: str, signers: dict[str, str | None], authors: set[str], cap: str | None
) -> str:
    grade = _real_earned(state, signers, authors, None)
    return S if cap and grade == EA else grade


def _mutant_ignores_the_cap(
    state: str, signers: dict[str, str | None], authors: set[str], cap: str | None
) -> str:
    return _real_earned(state, signers, authors, None)


def _mutant_lowers_the_held_grade(target_dir: Path, existing_grade: str) -> str:
    fidelity.rank(existing_grade)
    full = review.derive(target_dir)
    if review.opening(target_dir) is None:
        return existing_grade
    return review.earned(
        full["state"], full["signers"], review.surviving_authors(full), full["grade_cap"]
    )


def _mutant_relation_swapped(chosen: set[str], other: set[str], pairs: Any) -> str:
    return _real_relation(other, chosen, pairs)


def _mutant_always_related(chosen: set[str], other: set[str], pairs: Any) -> str:
    return "related"


def _mutant_any_role_may_split(sigs: list[dict[str, Any]]) -> dict[str, Any] | None:
    latest = _real_latest_signatures(sigs)
    for s in latest.values():
        if s.get("decision") == "split":
            return s
    return None


@pytest.mark.parametrize(
    ("where", "attr", "mutant"),
    [
        (review, "earned", _mutant_any_signer_is_independent),
        (review, "earned", _mutant_ignores_the_state),
        (review, "earned", _mutant_either_role_attests),
        (review, "earned", _mutant_cap_only_holds_the_top),
        (review, "earned", _mutant_ignores_the_cap),
        (review, "grade_of", _mutant_lowers_the_held_grade),
        (review, "relation", _mutant_relation_swapped),
        (review, "relation", _mutant_always_related),
        (review, "the_split", _mutant_any_role_may_split),
    ],
    ids=[
        "any-signer-is-independent",
        "ignores-the-state",
        "either-role-attests",
        "cap-only-holds-the-top",
        "ignores-the-cap",
        "lowers-the-held-grade",
        "relation-swapped",
        "always-related",
        "any-role-may-split",
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
