"""F26-T19 (R8; D-9, D-28, D-35 v3.39): an open pair direction is work, submitted directly.

``POST /submissions`` (and the MCP ``submit_proof``) takes ``artifact_type: pair-proof`` with a
``pair`` and the filled ``lean``: no node, no bundle, no precheck. Before any pull request opens,
each refusal by name (F13-T21's rule): the review, both candidates surviving at main's sha, the
direction open on the pair record in force, nothing pending or merged for it; the gate's template
(``opn_gate.pair_proofs``), byte for byte outside the two regions; the region rules; then the hosted
pre-flight (the owner's rule, 2026-09-24): the file elaborates, its axioms are the standard three
(read from a nonce-tagged line the service appends, since the checker's check mode names no axioms
— measured on the live service, 2026-10-27), and for a proof the guarded copy does not elaborate. A
checker that cannot answer is an advisory word and the record still opens: the gate's sandbox is
the authority (the ``preflight_exhibit`` precedent).

The fixture is the core-Lean Legendre pair of the gate's review fixtures, seeded under the
propositional target as merged review records, both candidates compiled (so surviving).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from api_fakes import AXLE_OKAY, AxleCall, FakeAxle, Harness, make_harness
from mcp_client import McpClient
from test_glosses_route import TARGET, make_keys, make_tree
from test_glosses_route import serve as serve_tree
from test_reviews_routes import candidate, nothing_opened, opening, put
from test_web_session import ENV

from opn_api.axle import AxleError
from opn_gate import pair_proofs, review_lean, schemas
from opn_gate import review as gate_review

FIX = Path(__file__).resolve().parents[2] / "gate" / "tests" / "fixtures" / "review" / "legendre"
REVIEW_DIR = f"targets/{TARGET}/review"
CONCEPTS = ["prime"]
#: The stronger reading (p strictly inside the interval) and the weaker one (endpoints allowed).
STRICT = (FIX / "human-ref.lean").read_text(encoding="utf-8")
LOOSE = (FIX / "alt-closed.lean").read_text(encoding="utf-8")
#: A closed claim: the review cannot compare it with an indexed one (``pair_proofs.provable``).
CLOSED = (
    "def Prime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0\n"
    "def claim : Prop := ∃ p, Prime p\n"
)
AUTOMATION = {"method": "agent", "models": ["claude-opus-5-5"], "framework": "Claude Code"}
TAG_RE = re.compile(r"OPN-PAIR-PROOF-[0-9a-f]{32}")


def cid(lean: str) -> str:
    return "c-" + hashlib.sha256(lean.encode("utf-8")).hexdigest()[:8]


S, L, C = cid(STRICT), cid(LOOSE), cid(CLOSED)
A, B = sorted((S, L))
#: The provable direction, strict implies loose, as pair/v1 names it.
PROVABLE: pair_proofs.Direction = "forward" if (A, B) == (S, L) else "backward"
OTHER: pair_proofs.Direction = "backward" if PROVABLE == "forward" else "forward"


def cand(c: str, lean: str) -> review_lean.Cand:
    got = review_lean.prepare(c, lean, CONCEPTS)
    assert isinstance(got, review_lean.Cand)
    return got


def template(direction: str = PROVABLE, kind: str = "proof", n: int | None = None) -> str:
    return pair_proofs.template(cand(A, LEANS[A]), cand(B, LEANS[B]), direction, kind, n)  # type: ignore[arg-type]


LEANS = {S: STRICT, L: LOOSE, C: CLOSED}
HELPER = (
    f"private theorem same (p : Nat) : {review_lean.ns(S, 'p')}.Prime p → "
    f"{review_lean.ns(L, 'p')}.Prime p := id\n"
)
PROOF = (
    "  intro hn\n  obtain ⟨p, h1, h2, h3⟩ := h hn\n"
    "  exact ⟨p, Nat.le_of_lt h1, Nat.le_of_lt h2, same p h3⟩\n"
)


def fill(tmpl: str, helpers: str = HELPER, proof: str = PROOF) -> str:
    return tmpl.replace(pair_proofs.HELPERS_END, helpers + pair_proofs.HELPERS_END).replace(
        pair_proofs.PLACEHOLDER, proof
    )


FILLED = fill(template())


# --- the checker's answers -----------------------------------------------------------------------


def answered(axioms: list[str] | None = None, *, okay: bool | None = True) -> Callable[..., Any]:
    """A check that elaborated, printing the service's tagged axiom line with the nonce the
    request carried (the program's own line; a contributor cannot know the nonce)."""

    def reply(call: AxleCall) -> dict[str, Any]:
        infos = []
        tag = TAG_RE.search(call.content)
        if tag is not None and axioms is not None:
            infos.append(f"-:300:0: info: {tag.group(0)} {json.dumps(axioms)}")
        body = {**AXLE_OKAY, "lean_messages": {"errors": [], "warnings": [], "infos": infos}}
        if okay is None:
            body = {k: v for k, v in body.items() if k != "okay"} | {"user_error": "no verdict"}
        else:
            body["okay"] = okay
        return body

    return reply


def fails(*errors: str) -> dict[str, Any]:
    return {
        **AXLE_OKAY,
        "okay": False,
        "failed_declarations": ["opnDirection"],
        "lean_messages": {"errors": list(errors), "warnings": [], "infos": []},
    }


GUARD_FAILS = fails("-:125:36-125:37: error(lean.unknownIdentifier): Unknown identifier `h`")


# --- the record ----------------------------------------------------------------------------------


def exhibit(c: str, result: str = "pass", kind: str = "compile") -> dict[str, Any]:
    return {"id": f"e-{kind}-{c}", "candidate": c, "kind": kind, "result": result}


def pair(**over: Any) -> dict[str, Any]:
    open_ = {
        "state": "open",
        "exhibit": None,
        "attempt": {"who": "gate", "tool": "t", "budget_s": 20},
    }
    return {
        "schema": "pair/v1",
        "target": TARGET,
        "a": A,
        "b": B,
        "forward": dict(open_),
        "backward": dict(open_),
        "date": "2026-09-05",
    } | over


def seed(
    tree: Path,
    *,
    cands: tuple[str, ...] = (S, L),
    compiled: tuple[str, ...] | None = None,
    pairs: list[tuple[str, dict[str, Any]]] | None = None,
    exhibits: list[dict[str, Any]] = (),  # type: ignore[assignment]
) -> None:
    put(tree, "review.yaml", opening(concepts=CONCEPTS))
    for c in cands:
        put(tree, f"candidates/{c}.yaml", candidate(LEANS[c], f"author-{c}"))
        put(tree, f"candidates/{c}.lean", LEANS[c])
    for c in cands if compiled is None else compiled:
        doc = exhibit(c)
        path = tree / REVIEW_DIR / "exhibits" / f"{doc['id']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc), encoding="utf-8")
    for doc in exhibits:
        path = tree / REVIEW_DIR / "exhibits" / f"{doc['id']}.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
    for name, doc in pairs if pairs is not None else [(f"{A}--{B}.yaml", pair())]:
        put(tree, f"pairs/{name}", doc)


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


@pytest.fixture
def axle() -> FakeAxle:
    return FakeAxle()


@pytest.fixture
def h(tree: Path, axle: FakeAxle) -> Iterator[Harness]:
    harness = make_harness(ENV, axle=axle)
    seed(tree)
    serve_tree(harness, tree)
    with harness.client:
        yield harness


def token(h: Harness) -> str:
    if not hasattr(h, "alice"):
        h.alice = h.token_for("code_alice", "alice-agent")  # type: ignore[attr-defined]
    return str(h.alice)  # type: ignore[attr-defined]


def body(**over: Any) -> dict[str, Any]:
    p = {"target": TARGET, "a": A, "b": B, "direction": PROVABLE, "kind": "proof"}
    return {
        "artifact_type": "pair-proof",
        "pair": p | over.pop("pair", {}),
        "lean": FILLED,
        "automation": AUTOMATION,
    } | over


def submit(h: Harness, doc: dict[str, Any] | None = None) -> Any:
    return h.client.post("/submissions", json=doc or body(), headers=h.auth(token(h)))


def reseed(h: Harness, tree: Path, **kw: Any) -> None:
    import shutil  # noqa: PLC0415

    shutil.rmtree(tree / REVIEW_DIR, ignore_errors=True)
    for path in [p for p in h.githost.files if p.startswith(REVIEW_DIR + "/")]:
        del h.githost.files[path]
    seed(tree, **kw)
    serve_tree(h, tree)


def refused(r: Any, status: int, code: str, h: Harness) -> dict[str, Any]:
    assert r.status_code == status, r.text
    doc: dict[str, Any] = r.json()
    assert doc["error"] == code, doc
    nothing_opened(h)
    return doc


# --- the happy path ------------------------------------------------------------------------------


def test_a_proof_lands_as_one_record_in_one_pull_request_on_an_append_branch(
    h: Harness, axle: FakeAxle
) -> None:
    axle.replies = [answered(["propext"]), GUARD_FAILS]
    r = submit(h)
    assert r.status_code == 201, r.text
    out = r.json()
    assert len(h.githost.pulls) == 1 and len(h.githost.pushes) == 1
    (push,) = h.githost.pushes
    assert list(push.files) == [out["path"]], "exactly one file: the record"
    assert out["path"].startswith(f"{REVIEW_DIR}/{pair_proofs.DIR}/{A}--{B}--{PROVABLE}--")
    assert out["path"].endswith("-alice-agent.yaml")
    assert out["branch"].startswith("append/"), "the merge actor takes append/"
    doc = yaml.safe_load(push.files[out["path"]])
    schemas.validate(doc, "pair-proof/v1")
    assert isinstance(pair_proofs.split(doc["lean"], template()), pair_proofs.Filled)
    assert doc["lean"] == FILLED
    assert (doc["a"], doc["b"], doc["direction"], doc["kind"], doc["case"]) == (
        A,
        B,
        PROVABLE,
        "proof",
        None,
    )
    assert doc["author"] == "alice-agent"
    assert doc["models"] == AUTOMATION["models"]
    assert doc["statement_hashes"] == {
        "a": hashlib.sha256(LEANS[A].encode()).hexdigest(),
        "b": hashlib.sha256(LEANS[B].encode()).hexdigest(),
    }
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", doc["date"])
    stamp = doc["date"].replace("-", "").replace(":", "")
    assert out["path"].endswith(pair_proofs.record_name(A, B, PROVABLE, stamp, "alice-agent")), (
        "the gate's own record name"
    )
    assert out["pair_proof_preflight"] == "passed"
    assert (out["artifact_type"], out["target_id"]) == ("pair-proof", TARGET)
    # two checks: the file with the axiom program, then the guarded copy
    first, second = axle.calls
    assert first.content.count(FILLED.split("\n", 1)[1]) == 1 and TAG_RE.search(first.content)
    assert "intro hn" in second.content and "; clear h\n" in second.content
    watched = h.client.get(f"/submissions/{out['pr_number']}")
    assert watched.status_code == 200 and watched.json()["submission"]["kind"] == "pair-proof"


def test_the_author_is_the_tokens_never_the_requests(h: Harness, axle: FakeAxle) -> None:
    axle.replies = [answered([]), GUARD_FAILS]
    r = submit(h, body(author="someone-else"))
    refused(r, 400, "unknown-field", h)
    r = submit(h, body(pair={"author": "someone-else"}))
    refused(r, 400, "arguments-invalid", h)
    assert submit(h).status_code == 201
    doc = yaml.safe_load(next(iter(h.githost.pushes[-1].files.values())))
    assert doc["author"] == "alice-agent"


def test_a_refutation_is_an_instance_checked_once_with_no_guard(h: Harness, axle: FakeAxle) -> None:
    lean = fill(template(OTHER, "refutation", 3), helpers="", proof="  decide\n")
    axle.replies = [answered([])]
    r = submit(h, body(pair={"direction": OTHER, "kind": "refutation", "n": 3}, lean=lean))
    assert r.status_code == 201, r.text
    assert len(axle.calls) == 1, "a refutation has no hypothesis and no guard"
    assert "collectAxioms `opnInstance" in axle.calls[0].content
    doc = yaml.safe_load(next(iter(h.githost.pushes[-1].files.values())))
    assert doc["case"] == {"probe": "holds", "n": 3, "set": None, "concept": None}
    assert doc["kind"] == "refutation" and doc["direction"] == OTHER


# --- the pre-flight's answers --------------------------------------------------------------------


def test_a_checker_that_cannot_answer_still_opens_with_an_advisory_word(
    h: Harness, axle: FakeAxle
) -> None:
    axle.replies = [AxleError("down", status=502)]
    r = submit(h)
    assert r.status_code == 201, r.text
    assert r.json()["pair_proof_preflight"] == "unavailable"
    assert len(axle.calls) == 1, "nothing to guard when the first answer never came"


@pytest.mark.parametrize(
    "first",
    [answered([], okay=None), answered(None)],  # no verdict; elaborated with no tagged line
    ids=["no-verdict", "no-axiom-line"],
)
def test_no_verdict_or_no_axiom_line_is_inconclusive(
    h: Harness, axle: FakeAxle, first: Callable[..., Any]
) -> None:
    axle.replies = [first, GUARD_FAILS]
    r = submit(h)
    assert r.status_code == 201, r.text
    assert r.json()["pair_proof_preflight"] == "inconclusive"


def test_a_guard_with_no_verdict_is_inconclusive(h: Harness, axle: FakeAxle) -> None:
    axle.replies = [answered([]), answered([], okay=None)]
    r = submit(h)
    assert r.status_code == 201 and r.json()["pair_proof_preflight"] == "inconclusive"


def test_an_axiom_line_without_the_nonce_is_not_read(h: Harness, axle: FakeAxle) -> None:
    """A contributor's own logInfo of the tag cannot vouch: the nonce is the service's."""

    def forged(call: AxleCall) -> dict[str, Any]:
        info = "-:30:0: info: OPN-PAIR-PROOF-" + "0" * 32 + " []"
        return {**AXLE_OKAY, "lean_messages": {"errors": [], "warnings": [], "infos": [info]}}

    axle.replies = [forged, GUARD_FAILS]
    r = submit(h)
    assert r.status_code == 201 and r.json()["pair_proof_preflight"] == "inconclusive"


def test_a_file_that_does_not_elaborate_is_refused(h: Harness, axle: FakeAxle) -> None:
    err = "-:40:2-40:9: error: type mismatch"
    axle.replies = [fails(err)]
    doc = refused(submit(h), 422, "pair-proof-elaboration", h)
    assert doc["details"]["errors"] == [err]
    assert len(axle.calls) == 1


@pytest.mark.parametrize(
    ("axioms", "code"),
    [
        (["propext", "sorryAx"], "pair-proof-sorry"),
        (["propext", "opnInstance._native.native_decide.ax_1_1"], "pair-proof-axiom"),
    ],
)
def test_axioms_beyond_the_standard_three_are_refused(
    h: Harness, axle: FakeAxle, axioms: list[str], code: str
) -> None:
    axle.replies = [answered(axioms), GUARD_FAILS]
    doc = refused(submit(h), 422, code, h)
    assert axioms[-1] in json.dumps(doc["details"])


def test_a_proof_that_never_uses_its_hypothesis_is_refused_by_the_guard(
    h: Harness, axle: FakeAxle
) -> None:
    axle.replies = [answered([]), answered([])]
    refused(submit(h), 422, "pair-proof-degenerate", h)
    assert len(axle.calls) == 2


# --- the record's refusals -----------------------------------------------------------------------


def test_a_target_with_no_review_is_404(h: Harness, tree: Path) -> None:
    import shutil  # noqa: PLC0415

    shutil.rmtree(tree / REVIEW_DIR)
    for path in [p for p in h.githost.files if p.startswith(REVIEW_DIR + "/")]:
        del h.githost.files[path]
    serve_tree(h, tree)
    refused(submit(h), 404, "review-unknown", h)


def test_a_candidate_not_on_the_record_is_404(h: Harness, tree: Path) -> None:
    reseed(h, tree, cands=(A,), pairs=[])
    refused(submit(h), 404, "candidate-unknown", h)


@pytest.mark.parametrize("fate", ["discarded", "pending"])
def test_a_candidate_that_is_not_surviving_is_refused(h: Harness, tree: Path, fate: str) -> None:
    if fate == "pending":
        reseed(h, tree, compiled=(A,))
    else:
        reseed(h, tree, exhibits=[exhibit(B, "fail", "screen")])
    doc = refused(submit(h), 409, "pair-candidate-not-surviving", h)
    assert doc["details"]["candidate"] == B


def test_a_pair_the_job_has_not_compared_is_404(h: Harness, tree: Path) -> None:
    reseed(h, tree, pairs=[])
    refused(submit(h), 404, "pair-unknown", h)


def test_a_settled_direction_is_refused(h: Harness, tree: Path) -> None:
    proved = {"state": "proved", "exhibit": "e-x", "attempt": None}
    reseed(h, tree, pairs=[(f"{A}--{B}.yaml", pair(**{PROVABLE: proved}))])
    refused(submit(h), 409, "pair-not-open", h)


def test_the_pair_record_in_force_decides_supersession(
    h: Harness, tree: Path, axle: FakeAxle
) -> None:
    proved = {"state": "proved", "exhibit": "e-x", "attempt": None}
    older = pair(**{PROVABLE: proved}, date="2026-09-04")
    newer = pair(date="2026-09-06")
    reseed(h, tree, pairs=[(f"{A}--{B}.yaml", older), (f"{A}--{B}--2026-09-06-2.yaml", newer)])
    axle.replies = [answered([]), GUARD_FAILS]
    assert submit(h).status_code == 201, "the newer record holds the direction open"
    flipped = [
        (f"{A}--{B}.yaml", newer | {"date": "2026-09-04"}),
        ("z.yaml", older | {"date": "2026-09-06"}),
    ]
    reseed(h, tree, pairs=flipped)
    r = submit(h, body())
    assert r.status_code == 409 and r.json()["error"] == "pair-not-open", r.text


def test_a_merged_record_waiting_for_the_job_settles_the_direction(h: Harness, tree: Path) -> None:
    rec: dict[str, Any] = {
        "schema": "pair-proof/v1",
        "target": TARGET,
        "a": A,
        "b": B,
        "direction": PROVABLE,
        "kind": "proof",
        "case": None,
        "statement_hashes": {"a": "0" * 64, "b": "1" * 64},
        "lean": FILLED,
        "author": "bob",
        "models": [],
        "date": "2026-09-08T10:00:00Z",
    }
    name = pair_proofs.record_name(A, B, PROVABLE, "20260908T100000Z", "bob")
    put(tree, f"{pair_proofs.DIR}/{name}", rec)
    serve_tree(h, tree)
    doc = refused(submit(h), 409, "pair-proof-settled", h)
    assert name in json.dumps(doc["details"])


def merged_record(tree: Path, when: str = "20260908T100000Z") -> str:
    """A merged pair-proof record for the provable direction; its file name."""
    stamp = f"{when[:4]}-{when[4:6]}-{when[6:8]}T{when[9:11]}:{when[11:13]}:{when[13:15]}Z"
    rec: dict[str, Any] = {
        "schema": "pair-proof/v1",
        "target": TARGET,
        "a": A,
        "b": B,
        "direction": PROVABLE,
        "kind": "proof",
        "case": None,
        "statement_hashes": {"a": "0" * 64, "b": "1" * 64},
        "lean": FILLED,
        "author": "bob",
        "models": [],
        "date": stamp,
    }
    name = pair_proofs.record_name(A, B, PROVABLE, when, "bob")
    put(tree, f"{pair_proofs.DIR}/{name}", rec)
    return name


def judgment(name: str, result: str) -> dict[str, Any]:
    """The review job's judgment of a merged record (F26-T18): a ``pair`` exhibit whose detail
    ends ``(pair-proof <stem>)``, ``open`` with the refusal when its re-check refused it."""
    stem = name.removesuffix(".yaml")
    detail = (
        f"{gate_review.REFUSED} pair-proof-degenerate (pair-proof {stem})"
        if result == "open"
        else f"{A} implies {B} (pair-proof {stem})"
    )
    return {
        "schema": "exhibit/v1",
        "id": "e-0000beef",
        "kind": "pair",
        "result": result,
        "detail": detail,
        "candidate": A,
        "test": B,
    }


def test_a_merged_record_the_job_refused_settles_nothing(
    h: Harness, tree: Path, axle: FakeAxle
) -> None:
    """F26-T21: a record the job's re-check refused left its direction open, so it must not
    block a new submission (otherwise the direction is locked for ever)."""
    name = merged_record(tree)
    reseed(h, tree, exhibits=[judgment(name, "open")])
    merged_record(tree)
    serve_tree(h, tree)
    axle.replies = [answered([]), GUARD_FAILS]
    r = submit(h)
    assert r.status_code == 201, r.text


def test_a_merged_record_the_job_accepted_settles_the_direction(h: Harness, tree: Path) -> None:
    name = merged_record(tree)
    reseed(h, tree, exhibits=[judgment(name, "proved")])
    merged_record(tree)
    serve_tree(h, tree)
    refused(submit(h), 409, "pair-proof-settled", h)


def test_a_same_day_later_pair_record_is_the_one_in_force(
    h: Harness, tree: Path, axle: FakeAxle
) -> None:
    """The job writes a later record for the same pair on the same day as
    ``<a>--<b>--<date>-<k>.yaml``, which sorts before ``<a>--<b>.yaml``: the gate's rule
    (``review.latest_of``, T18) ranks by date, then the generation in the name, so the later
    record, which reopens the direction here, is in force."""
    proved = {"state": "proved", "exhibit": "e-x", "attempt": None}
    first = pair(**{PROVABLE: proved}, date="2026-09-05")
    later = pair(date="2026-09-05")
    reseed(h, tree, pairs=[(f"{A}--{B}.yaml", first), (f"{A}--{B}--2026-09-05-2.yaml", later)])
    axle.replies = [answered([]), GUARD_FAILS]
    r = submit(h)
    assert r.status_code == 201, r.text


def test_a_second_submission_while_one_is_pending_is_refused(h: Harness, axle: FakeAxle) -> None:
    axle.replies = [answered([]), GUARD_FAILS]
    first = submit(h)
    assert first.status_code == 201
    pulls, pushes = len(h.githost.pulls), len(h.githost.pushes)
    r = submit(h)
    assert r.status_code == 409 and r.json()["error"] == "pair-proof-pending", r.text
    assert r.json()["details"]["pr_number"] == first.json()["pr_number"]
    assert (len(h.githost.pulls), len(h.githost.pushes)) == (pulls, pushes)


def test_a_kind_the_direction_cannot_take_is_refused(h: Harness, tree: Path) -> None:
    lo, hi = sorted((S, C))
    reseed(h, tree, cands=(S, L, C), pairs=[(f"{lo}--{hi}.yaml", pair(a=lo, b=hi))])
    doc = refused(submit(h, body(pair={"a": lo, "b": hi})), 422, "pair-proof-no-template", h)
    assert "shape" in doc["message"]
    doc = refused(
        submit(h, body(pair={"a": lo, "b": hi, "kind": "refutation", "n": 2})),
        422,
        "pair-proof-no-template",
        h,
    )
    assert "indexed" in doc["message"]


def test_a_file_off_its_template_is_refused_with_the_line(h: Harness) -> None:
    lean = FILLED.replace("theorem opnDirection :", "theorem opnDirection' :")
    doc = refused(submit(h, body(lean=lean)), 422, "pair-proof-template-mismatch", h)
    assert doc["details"]["line"] >= 1


@pytest.mark.parametrize(
    ("helpers", "proof"),
    [(HELPER, "  sorry\n"), ("axiom cheat : False\n", PROOF), (HELPER, "")],
)
def test_the_region_rules_are_refused(h: Harness, helpers: str, proof: str) -> None:
    refused(submit(h, body(lean=fill(template(), helpers, proof))), 422, "pair-proof-forbidden", h)


def test_ten_a_day_per_pseudonym_and_target(h: Harness, axle: FakeAxle) -> None:
    for _ in range(10):
        axle.replies = [fails("-:1:0: error: x")]
        assert submit(h).json()["error"] == "pair-proof-elaboration"
    r = submit(h)
    assert r.status_code == 429 and r.json()["error"] == "rate-limited"
    nothing_opened(h)


@pytest.mark.parametrize(
    ("over", "field"),
    [
        ({"pair": None}, "pair"),
        ({"pair": {"direction": "sideways"}}, "pair.direction"),
        ({"pair": {"kind": "disproof"}}, "pair.kind"),
        ({"pair": {"a": B, "b": A}}, "pair.a"),
        ({"pair": {"n": 3}}, "pair.n"),
        ({"pair": {"kind": "refutation"}}, "pair.n"),
        ({"pair": {"kind": "refutation", "n": -1}}, "pair.n"),
        ({"lean": ""}, "lean"),
        ({"node_id": "and-reassoc"}, "node_id"),
        ({"bundle": {}}, "bundle"),
        ({"precheck_job_id": "x"}, "precheck_job_id"),
        ({"tooling": {}}, "tooling"),
    ],
)
def test_bad_arguments_are_refused_by_field(h: Harness, over: dict[str, Any], field: str) -> None:
    doc = body()
    if "pair" in over and isinstance(over["pair"], dict):
        doc["pair"] = doc["pair"] | over.pop("pair")
    doc |= over
    out = refused(submit(h, doc), 400, "arguments-invalid", h)
    assert out["details"]["field"] == field


def test_the_disclosure_is_required(h: Harness) -> None:
    doc = body()
    del doc["automation"]
    refused(submit(h, doc), 400, "automation-missing", h)


def test_a_node_artifact_does_not_take_a_pair(h: Harness) -> None:
    r = h.client.post(
        "/submissions",
        json={
            "artifact_type": "proof",
            "node_id": "and-reassoc",
            "pair": {},
            "automation": AUTOMATION,
        },
        headers=h.auth(token(h)),
    )
    refused(r, 400, "arguments-invalid", h)


def test_a_pair_proof_needs_a_token(h: Harness) -> None:
    r = h.client.post("/submissions", json=body())
    assert r.status_code == 401


# --- the precheck says where a pair proof goes ---------------------------------------------------


def test_a_pair_proof_is_not_prechecked(h: Harness) -> None:
    r = h.client.post(
        "/precheck",
        json={"node_id": "and-reassoc", "bundle": {}, "artifact_type": "pair-proof"},
        headers=h.auth(token(h)),
    )
    doc = refused(r, 400, "pair-proof-not-prechecked", h)
    assert "submit_proof" in doc["message"]


def test_precheck_submission_passes_the_refusal_through(h: Harness) -> None:
    out = McpClient(h).failed(
        "precheck_submission",
        {"node_id": "and-reassoc", "bundle": {}, "artifact_type": "pair-proof"},
        token=token(h),
    )
    assert out["status"] == 400 and out["body"]["error"] == "pair-proof-not-prechecked"


# --- submit_proof --------------------------------------------------------------------------------


def test_submit_proof_takes_a_pair_proof_with_no_node_and_no_precheck(
    h: Harness, axle: FakeAxle
) -> None:
    axle.replies = [answered([]), GUARD_FAILS]
    args = {k: v for k, v in body().items()}
    out = McpClient(h).ok("submit_proof", args, token=token(h))
    assert out["status"] == 201, out
    assert out["body"]["path"].startswith(f"{REVIEW_DIR}/{pair_proofs.DIR}/")


def test_submit_proof_passes_a_pair_refusal_through(h: Harness, axle: FakeAxle) -> None:
    axle.replies = [answered([]), answered([])]
    out = McpClient(h).failed("submit_proof", body(), token=token(h))
    assert out["status"] == 422 and out["body"]["error"] == "pair-proof-degenerate"
    nothing_opened(h)


def test_submit_proof_refuses_a_precheck_reference_on_a_pair_proof(h: Harness) -> None:
    out = McpClient(h).failed("submit_proof", body(precheck_job_id="j"), token=token(h))
    assert out["status"] == 400 and out["body"]["error"] == "arguments-invalid"
    assert out["body"]["details"]["field"] == "precheck_job_id", "the route names the field"
    nothing_opened(h)


# --- the listings: supersession and the template -------------------------------------------------


def superseding(tree: Path, h: Harness) -> None:
    proved = {"state": "proved", "exhibit": "e-x", "attempt": None}
    reseed(
        h,
        tree,
        pairs=[
            (f"{A}--{B}.yaml", pair(date="2026-09-04")),
            (f"{A}--{B}--2026-09-06-2.yaml", pair(**{PROVABLE: proved}, date="2026-09-06")),
        ],
    )


def test_list_open_pairs_applies_supersession(h: Harness, tree: Path) -> None:
    superseding(tree, h)
    out = McpClient(h).ok("list_open_pairs", {"target_id": TARGET})
    assert [(r["a"], r["b"], r["direction"]) for r in out["pairs"]] == [(A, B, OTHER)]


def test_get_review_lists_only_the_pair_record_in_force(h: Harness, tree: Path) -> None:
    superseding(tree, h)
    doc = h.client.get(f"/reviews/{TARGET}").json()
    assert len(doc["pairs"]) == 1 and doc["pairs"][0]["date"] == "2026-09-06"
    assert [(r["a"], r["direction"]) for r in doc["open_pairs"]] == [(A, OTHER)]


def author_token(h: Harness) -> str:
    """A bearer whose pseudonym authored a candidate on the record (the blind rule is lifted)."""
    if not hasattr(h, "author"):
        h.author = h.token_for("code_bob", f"author-{A}")  # type: ignore[attr-defined]
    return str(h.author)  # type: ignore[attr-defined]


def test_an_open_direction_carries_its_template_to_a_candidates_author(h: Harness) -> None:
    out = McpClient(h).ok("list_open_pairs", {"target_id": TARGET}, token=author_token(h))
    rows = {r["direction"]: r for r in out["pairs"]}
    assert rows[PROVABLE]["template"] == template(PROVABLE)
    assert rows[PROVABLE]["template_withheld"] is None
    refute = rows[PROVABLE]["refutation"]
    assert refute["available"] is True and "`n`" in refute["note"] and refute["template"] is None
    review = h.client.get(f"/reviews/{TARGET}", headers=h.auth(author_token(h))).json()
    assert {r["direction"]: r["template"] for r in review["open_pairs"]}[OTHER] == template(OTHER)


def test_n_returns_the_refutation_template(h: Harness) -> None:
    out = McpClient(h).ok("list_open_pairs", {"target_id": TARGET, "n": 4}, token=author_token(h))
    rows = {r["direction"]: r for r in out["pairs"]}
    assert rows[OTHER]["refutation"]["template"] == template(OTHER, "refutation", 4)
    review = h.client.get(f"/reviews/{TARGET}?n=4", headers=h.auth(author_token(h))).json()
    got = {r["direction"]: r["refutation"]["template"] for r in review["open_pairs"]}
    assert got[OTHER] == template(OTHER, "refutation", 4)


def test_the_template_is_withheld_under_the_blind_rule(h: Harness) -> None:
    """R3: the template is both candidates' Lean, so a caller with no candidate on the record is
    shown none of it, as get_review withholds the candidates' Lean."""
    for out in (
        McpClient(h).ok("list_open_pairs", {"target_id": TARGET}),
        McpClient(h).ok("list_open_pairs", {"target_id": TARGET}, token=token(h)),
        h.client.get(f"/reviews/{TARGET}").json()
        | {"pairs": h.client.get(f"/reviews/{TARGET}").json()["open_pairs"]},
    ):
        for row in out["pairs"]:
            assert row["template"] is None and row["template_withheld"] == "blind"
            assert row["refutation"]["template"] is None


def test_a_bad_n_is_refused(h: Harness) -> None:
    out = McpClient(h).failed("list_open_pairs", {"target_id": TARGET, "n": -2})
    assert out["error"] == "arguments-invalid"
    assert h.client.get(f"/reviews/{TARGET}?n=x").status_code == 400
