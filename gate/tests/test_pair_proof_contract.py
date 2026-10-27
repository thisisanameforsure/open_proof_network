"""F26-T16 (R8): the pair-proof contract — the record, its role and mode, its credit line, and the
template every layer judges a settlement against (``opn_gate.pair_proofs``).

The lean-tier half (a filled template elaborates, its guarded copy does not) is in
``test_pair_proof_lean.py``; this file asserts the text."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from opn_gate import ledger, modes, pair_proofs, paths, review_lean, schemas
from opn_gate.diagnostic import Diagnostic

Pair = tuple[review_lean.Cand, review_lean.Cand]

FIX = Path(__file__).parent / "fixtures" / "review" / "legendre"
A, B = "c-aaaaaaaa", "c-bbbbbbbb"

ERDOS = Path(__file__).parent / "fixtures" / "review" / "erdos-849"
ROOT_849 = (ERDOS / "c-ae9bea28.lean").read_text(encoding="utf-8")
PAIRS_849 = (ERDOS / "c-fb339e85.lean").read_text(encoding="utf-8")

HELPER = "private theorem same (p : Nat) : C_c_aaaaaaaa_p.Prime p → C_c_bbbbbbbb_p.Prime p := id\n"
PROOF = (
    "  intro hn\n  obtain ⟨p, h1, h2, h3⟩ := h hn\n"
    "  exact ⟨p, Nat.le_of_lt h1, Nat.le_of_lt h2, same p h3⟩\n"
)


def cand(cid: str, name: str) -> review_lean.Cand:
    c = review_lean.prepare(cid, (FIX / f"{name}.lean").read_text(encoding="utf-8"), ["prime"])
    assert isinstance(c, review_lean.Cand)
    return c


@pytest.fixture
def pair() -> Pair:
    return cand(A, "human-ref"), cand(B, "alt-closed")


def fill(tmpl: str, helpers: str = HELPER, proof: str = PROOF) -> str:
    return tmpl.replace(pair_proofs.HELPERS_END, helpers + pair_proofs.HELPERS_END).replace(
        pair_proofs.PLACEHOLDER, proof
    )


# --- the template ------------------------------------------------------------------------------


def test_forward_proof_template_states_the_direction_and_opens_with_the_gates_intro(
    pair: Pair,
) -> None:
    a, b = pair
    t = pair_proofs.template(a, b, "forward")
    assert t.startswith(review_lean.HEADER)
    assert review_lean.header_of(t) == {
        "op": "pair-proof",
        "a": A,
        "b": B,
        "direction": "forward",
        "kind": "proof",
        "case": None,
    }
    assert "namespace C_c_aaaaaaaa_p" in t and "namespace C_c_bbbbbbbb_p" in t
    assert (
        "theorem opnDirection : ∀ n, C_c_aaaaaaaa_p.claim n → C_c_bbbbbbbb_p.claim n := by\n"
        "  intro n h\n"
    ) in t
    assert f"set_option maxHeartbeats {pair_proofs.MAX_HEARTBEATS} in\n" in t
    assert t.endswith(pair_proofs.PROOF_BEGINS + "\n" + pair_proofs.PLACEHOLDER)


def test_backward_swaps_the_claims_and_keeps_the_pairs_order_in_the_header(pair: Pair) -> None:
    a, b = pair
    t = pair_proofs.template(a, b, "backward")
    assert "∀ n, C_c_bbbbbbbb_p.claim n → C_c_aaaaaaaa_p.claim n" in t
    head = review_lean.header_of(t)
    assert head is not None and (head["a"], head["b"], head["direction"]) == (A, B, "backward")
    assert t.index("namespace C_c_bbbbbbbb_p") < t.index("namespace C_c_aaaaaaaa_p")


def test_the_template_is_its_own_unfilled_split(pair: Pair) -> None:
    t = pair_proofs.template(pair[0], pair[1], "forward")
    got = pair_proofs.split(t, t)
    assert isinstance(got, pair_proofs.Filled)
    assert (got.helpers, got.proof) == ("", pair_proofs.PLACEHOLDER)


def test_closed_claims_get_a_closed_goal_erdos_849() -> None:
    a = review_lean.prepare("c-ae9bea28", ROOT_849, [])
    b = review_lean.prepare("c-fb339e85", PAIRS_849, [])
    assert isinstance(a, review_lean.Cand) and isinstance(b, review_lean.Cand)
    assert (a.shape, b.shape) == ("closed", "closed")
    t = pair_proofs.template(a, b, "forward")
    assert "theorem opnDirection : C_c_ae9bea28_p.opnClaim → C_c_fb339e85_p.opnClaim := by\n" in t
    assert "\n  intro h\n  " + pair_proofs.PROOF_BEGINS in t
    assert t.count("import Mathlib") == 1


def test_refutation_template_is_the_jobs_instance_at_n(pair: Pair) -> None:
    a, b = pair
    t = pair_proofs.template(a, b, "backward", "refutation", 3)
    assert "theorem opnInstance : C_c_bbbbbbbb_p.claim 3 ∧ ¬ C_c_aaaaaaaa_p.claim 3 := by\n" in t
    assert review_lean.case_of(t) == review_lean.Case("holds", 3)
    assert "intro" not in t.split("opnInstance", 1)[1].split(pair_proofs.PROOF_BEGINS)[0]


@pytest.mark.parametrize(
    ("kind", "n", "why"),
    [
        ("proof", 2, "no instance"),
        ("refutation", None, "names its instance"),
        ("refutation", -1, "names its instance"),
        ("refutation", True, "names its instance"),
    ],
)
def test_template_refuses_a_kind_its_arguments_do_not_fit(
    pair: Pair, kind: str, n: object, why: str
) -> None:
    with pytest.raises(ValueError, match=why):
        pair_proofs.template(pair[0], pair[1], "forward", kind, n)  # type: ignore[arg-type]


def test_a_closed_direction_cannot_be_refuted() -> None:
    a = review_lean.prepare("c-ae9bea28", ROOT_849, [])
    b = review_lean.prepare("c-fb339e85", PAIRS_849, [])
    assert isinstance(a, review_lean.Cand) and isinstance(b, review_lean.Cand)
    with pytest.raises(ValueError, match="only indexed claims"):
        pair_proofs.template(a, b, "forward", "refutation", 1)


def test_claims_of_different_shapes_take_no_template(pair: Pair) -> None:
    closed = review_lean.prepare("c-ae9bea28", ROOT_849, [])
    assert isinstance(closed, review_lean.Cand)
    with pytest.raises(ValueError, match="shapes differ"):
        pair_proofs.template(pair[0], closed, "forward")


# --- filling it --------------------------------------------------------------------------------


def test_split_cuts_the_two_regions_and_numbers_their_lines(pair: Pair) -> None:
    t = pair_proofs.template(pair[0], pair[1], "forward")
    filled = fill(t)
    got = pair_proofs.split(filled, t)
    assert isinstance(got, pair_proofs.Filled)
    assert (got.helpers, got.proof) == (HELPER, PROOF)
    lines = filled.split("\n")
    assert lines[got.helpers_line - 1] == HELPER.rstrip("\n")
    assert lines[got.proof_line - 1] == PROOF.split("\n", 1)[0]
    assert pair_proofs.problems(got) == []


@pytest.mark.parametrize(
    "edit",
    [
        # the statement the contributor never writes
        lambda t: t.replace("→ C_c_bbbbbbbb_p.claim n", "→ True"),
        # a candidate's body
        lambda t: t.replace("Prime p", "True", 1),
        # the header
        lambda t: t.replace('"direction": "forward"', '"direction": "backward"'),
        # the heartbeat cap
        lambda t: t.replace("1000000", "9000000"),
        # the gate's intro (the guard's anchor)
        lambda t: t.replace("  intro n h\n", "  intro n _h\n"),
        # an import
        lambda t: "import Mathlib\n" + t,
    ],
)
def test_split_refuses_a_byte_the_gate_wrote(pair: Pair, edit: Callable[[str], str]) -> None:
    t = pair_proofs.template(pair[0], pair[1], "forward")
    got = pair_proofs.split(edit(fill(t)), t)
    assert isinstance(got, Diagnostic)
    assert got.code == "pair-proof-template-mismatch"
    assert got.details["line"] >= 1


def test_split_names_the_line_that_differs(pair: Pair) -> None:
    t = pair_proofs.template(pair[0], pair[1], "forward")
    bad = fill(t).replace("→ C_c_bbbbbbbb_p.claim n", "→ True")
    got = pair_proofs.split(bad, t)
    assert isinstance(got, Diagnostic)
    assert "opnDirection" in got.details["got"]


@pytest.mark.parametrize(
    ("helpers", "token"),
    [
        ("theorem same (p : Nat) : True := trivial\n", "theorem"),
        ("axiom cheat : False\n", "axiom"),
        ("set_option maxHeartbeats 0 in\nprivate theorem x : True := trivial\n", "set_option"),
        ("private theorem x : True := sorry\n", "sorry"),
        ("#eval 1\n", "#eval"),
        ("open Nat\n", "open"),
    ],
)
def test_helpers_are_held_to_the_helper_rule(pair: Pair, helpers: str, token: str) -> None:
    t = pair_proofs.template(pair[0], pair[1], "forward")
    got = pair_proofs.split(fill(t, helpers=helpers), t)
    assert isinstance(got, pair_proofs.Filled)
    found = pair_proofs.problems(got)
    assert [d.code for d in found] == ["pair-proof-forbidden"]
    assert found[0].details["token"] == token


@pytest.mark.parametrize("word", ["sorry", "admit", "native_decide", "set_option"])
def test_the_proof_region_may_not_hold_a_forbidden_word(pair: Pair, word: str) -> None:
    t = pair_proofs.template(pair[0], pair[1], "forward")
    got = pair_proofs.split(fill(t, proof=f"  intro hn\n  {word}\n"), t)
    assert isinstance(got, pair_proofs.Filled)
    found = pair_proofs.problems(got)
    assert [(d.code, d.details["token"]) for d in found] == [("pair-proof-forbidden", word)]


def test_a_forbidden_word_in_a_comment_or_a_name_is_not_one(pair: Pair) -> None:
    t = pair_proofs.template(pair[0], pair[1], "forward")
    proof = "  -- no sorry here\n  have sorryless := 1\n  exact Nat.le_refl 0 |>.elim\n"
    got = pair_proofs.split(fill(t, proof=proof), t)
    assert isinstance(got, pair_proofs.Filled)
    assert pair_proofs.problems(got) == []


def test_a_line_at_column_zero_would_start_a_command(pair: Pair) -> None:
    t = pair_proofs.template(pair[0], pair[1], "forward")
    got = pair_proofs.split(fill(t, proof="  intro hn\naxiom cheat : False\n"), t)
    assert isinstance(got, pair_proofs.Filled)
    found = pair_proofs.problems(got)
    assert [d.code for d in found] == ["pair-proof-forbidden"]
    assert "column 0" in found[0].message
    assert found[0].details["line"] == got.proof_line + 1


def test_an_empty_proof_region_is_refused(pair: Pair) -> None:
    t = pair_proofs.template(pair[0], pair[1], "forward")
    got = pair_proofs.split(fill(t, proof="\n"), t)
    assert isinstance(got, pair_proofs.Filled)
    assert [d.message for d in pair_proofs.problems(got)] == ["the proof region is empty"]


# --- the guard ---------------------------------------------------------------------------------


def test_guarded_clears_the_hypothesis_right_after_the_gates_intro(pair: Pair) -> None:
    a, b = pair
    filled = fill(pair_proofs.template(a, b, "forward"))
    g = pair_proofs.guarded(filled, a)
    assert "\n  intro n h; clear h\n  " + pair_proofs.PROOF_BEGINS + "\n" in g
    assert g.replace("; clear h", "") == filled


def test_guarded_refuses_a_text_with_no_single_gate_intro(pair: Pair) -> None:
    a, b = pair
    with pytest.raises(ValueError):
        pair_proofs.guarded(pair_proofs.template(a, b, "backward", "refutation", 1), a)


# --- the record, the role, the mode, the line ----------------------------------------------------


def record() -> dict[str, object]:
    return {
        "schema": "pair-proof/v1",
        "target": "erdos-849",
        "a": "c-ae9bea28",
        "b": "c-fb339e85",
        "direction": "forward",
        "kind": "proof",
        "case": None,
        "statement_hashes": {"a": "a" * 64, "b": "b" * 64},
        "lean": "-- opn-review: {}\n",
        "author": "t1026e-c",
        "models": ["claude-opus-5-5"],
        "date": "2026-10-27T01:00:00Z",
    }


def test_the_record_validates_and_a_refutation_carries_its_case() -> None:
    schemas.validate(record(), "pair-proof/v1")
    doc = record() | {
        "kind": "refutation",
        "case": {"probe": "holds", "n": 3, "set": None, "concept": None},
    }
    schemas.validate(doc, "pair-proof/v1")


@pytest.mark.parametrize(
    "change",
    [
        {"direction": "both"},
        {"kind": "disproof"},
        {"case": {"probe": "covers", "n": 3, "set": None, "concept": None}},
        {"statement_hashes": {"a": "a" * 64}},
        {"date": "2026-10-27"},
        {"lean": ""},
        {"extra": 1},
    ],
)
def test_the_record_refuses_what_it_does_not_name(change: dict[str, object]) -> None:
    with pytest.raises(schemas.SchemaError):
        schemas.validate(record() | change, "pair-proof/v1")


def test_the_file_locates_as_a_pair_proof_and_classifies_as_its_own_mode() -> None:
    name = pair_proofs.record_name(
        "c-ae9bea28", "c-fb339e85", "forward", "20261027T010000Z", "t1026e-c"
    )
    assert name == "c-ae9bea28--c-fb339e85--forward--20261027T010000Z-t1026e-c.yaml"
    loc = paths.locate(f"targets/erdos-849/review/{pair_proofs.DIR}/{name}")
    assert loc is not None and loc.role == "pair-proof"
    assert paths.SCHEMAS_FOR_ROLE["pair-proof"] == ("pair-proof/v1",)
    assert modes.RECORD_MODES["pair-proof"] == "pair-proof"
    assert "pair-proof" in modes.REVIEW_RECORD_ROLES  # a merge re-runs the job
    assert "pair-proof" not in modes.REVIEW_JOB_ROLES  # a contributor's, not the job's
    assert paths.locate(f"targets/erdos-849/review/{pair_proofs.DIR}/x.lean") is None


def test_a_merged_pair_proof_earns_the_review_line() -> None:
    assert ledger.MERGE_LINES["pair-proof"] == "review"
