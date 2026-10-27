"""F26-T17 (R8): the gate before the merge for a pull request that adds a pair-proof record.

Classification (``modes.classify``) and the checks before any sandbox (``modes.check``): one
record per pull request, append-only, the record valid and named for itself, bound to an open
direction between two surviving candidates whose statement hashes it carries, not settled already
by an earlier record, by its own author, and its Lean the direction's template with its regions
filled. Then the classification asks for the sandbox (``needs_pair_proof``), and ``opn-gate
pair-proofs`` runs the verdict (``pair_proof_check``) for the record; through a fake here, and in
the step-3 sandbox in the docker tier."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Literal

import pytest
import yaml
from review_support import make_graph, prototype_lean
from test_pair_proof_check import STANDARD, PairFake

from opn_gate import cli, codes, config, modes, pair_proofs, review_lean, toolchain
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change

TARGET = "legendre"
SERVICE = "opn-service[bot]"
AUTHOR = "t1027-g"
STAMP_DATE = "2026-10-27T01:00:00Z"
STAMP = "20261027T010000Z"
HELPER = "private theorem same (p : Nat) : {a}.Prime p → {b}.Prime p := id\n"
PROOF = (
    "  intro hn\n  obtain ⟨p, h1, h2, h3⟩ := h hn\n"
    "  exact ⟨p, Nat.le_of_lt h1, Nat.le_of_lt h2, same p h3⟩\n"
)


# --- a graph as the job leaves it ----------------------------------------------------------------


def survive(graph: Path, cid: str) -> None:
    """The job's compile exhibit for ``cid``, result pass: the candidate survives stage 3."""
    folder = graph / "targets" / TARGET / "review" / "exhibits"
    folder.mkdir(parents=True, exist_ok=True)
    eid = "e-" + hashlib.sha256(f"compile:{cid}".encode()).hexdigest()[:8]
    doc = {
        "schema": "exhibit/v1",
        "target": TARGET,
        "id": eid,
        "kind": "compile",
        "candidate": cid,
        "test": None,
        "result": "pass",
        "detail": "compiles",
        "lean_file": None,
        "toolchain": "leanprover/lean4:v4.33.1",
        "mathlib_sha": None,
        "run": "run-1",
        "date": "2026-10-12",
    }
    (folder / f"{eid}.json").write_text(json.dumps(doc), encoding="utf-8")


def discard(graph: Path, cid: str) -> None:
    folder = graph / "targets" / TARGET / "review" / "exhibits"
    eid = "e-" + hashlib.sha256(f"screen:{cid}".encode()).hexdigest()[:8]
    doc = {
        "schema": "exhibit/v1",
        "target": TARGET,
        "id": eid,
        "kind": "screen",
        "candidate": cid,
        "test": None,
        "result": "fail",
        "detail": "the negation screen fired",
        "lean_file": None,
        "toolchain": "leanprover/lean4:v4.33.1",
        "mathlib_sha": None,
        "run": "run-1",
        "date": "2026-10-12",
    }
    (folder / f"{eid}.json").write_text(json.dumps(doc), encoding="utf-8")


def open_way() -> dict[str, Any]:
    return {
        "state": "open",
        "exhibit": None,
        "attempt": {"who": "gate", "tool": "gate: two-layer matching", "budget_s": 60},
    }


def proved_way() -> dict[str, Any]:
    return {"state": "proved", "exhibit": "e-00000001", "attempt": None}


def write_pair(
    graph: Path,
    a: str,
    b: str,
    forward: dict[str, Any],
    backward: dict[str, Any],
    *,
    date: str = "2026-10-12",
    name: str | None = None,
) -> None:
    folder = graph / "targets" / TARGET / "review" / "pairs"
    folder.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": "pair/v1",
        "target": TARGET,
        "a": a,
        "b": b,
        "forward": forward,
        "backward": backward,
        "date": date,
    }
    (folder / (name or f"{a}--{b}.yaml")).write_text(yaml.safe_dump(doc, sort_keys=False))


class World:
    """Two surviving Legendre candidates with an open forward direction, as the job leaves them."""

    def __init__(self, tmp: Path, second: str = "alt-closed", header: str = "") -> None:
        self.graph, ids = make_graph(
            tmp,
            candidates={
                "faithful": header + prototype_lean("legendre", "human-ref"),
                "other": prototype_lean("legendre", second),
                "third": prototype_lean("legendre", "bad-two"),
            },
        )
        self.ids = ids
        x, y = sorted([ids["faithful"], ids["other"]])
        self.a, self.b = x, y
        for cid in ids.values():
            survive(self.graph, cid)
        write_pair(self.graph, self.a, self.b, open_way(), open_way())
        self.base = self.graph / "targets" / TARGET / "review"

    def cand(self, cid: str) -> review_lean.Cand:
        lean = (self.base / "candidates" / f"{cid}.lean").read_text(encoding="utf-8")
        c = review_lean.prepare(cid, lean, ["prime"])
        assert isinstance(c, review_lean.Cand)
        return c

    def statement_hash(self, cid: str) -> str:
        doc = yaml.safe_load((self.base / "candidates" / f"{cid}.yaml").read_text())
        return str(doc["statement_hash"])

    @property
    def direction(self) -> pair_proofs.Direction:
        """The direction from the faithful reading into the other, which ``PROOF`` proves."""
        return "forward" if self.a == self.ids["faithful"] else "backward"

    def filled(self, direction: pair_proofs.Direction | None = None) -> str:
        direction = direction or self.direction
        a, b = self.cand(self.a), self.cand(self.b)
        tmpl = pair_proofs.template(a, b, direction)
        first, second = pair_proofs.ordered(a, b, direction)
        helper = HELPER.format(a=review_lean.ns(first.id, "p"), b=review_lean.ns(second.id, "p"))
        return tmpl.replace(pair_proofs.HELPERS_END, helper + pair_proofs.HELPERS_END).replace(
            pair_proofs.PLACEHOLDER, PROOF
        )

    def record(self, **change: Any) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "schema": "pair-proof/v1",
            "target": TARGET,
            "a": self.a,
            "b": self.b,
            "direction": change.get("direction", self.direction),
            "kind": "proof",
            "case": None,
            "statement_hashes": {
                "a": self.statement_hash(self.a),
                "b": self.statement_hash(self.b),
            },
            "lean": self.filled(change.get("direction", self.direction)),
            "author": AUTHOR,
            "models": ["claude-opus-5-5"],
            "date": STAMP_DATE,
        }
        doc.update(change)
        return doc

    def path_for(self, doc: dict[str, Any]) -> str:
        stamp = str(doc["date"]).replace("-", "").replace(":", "")
        name = pair_proofs.record_name(
            str(doc["a"]), str(doc["b"]), doc["direction"], stamp, str(doc["author"])
        )
        return f"targets/{TARGET}/review/{pair_proofs.DIR}/{name}"

    def put(self, doc: dict[str, Any], path: str | None = None) -> str:
        rel = path or self.path_for(doc)
        dest = self.graph / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return rel

    def gate(
        self, rel: str, *, opener: str = SERVICE, status: Literal["A", "M", "D"] = "A"
    ) -> tuple[modes.Classification, list[Diagnostic]]:
        cls = modes.classify(
            [Change(status, rel)],
            author=opener,
            graph_root=self.graph,
            service_login=SERVICE,
        )
        found = list(cls.problems)
        if cls.ok:
            found.extend(modes.check(self.graph, cls))
        return cls, found


def codes_of(found: list[Diagnostic]) -> list[str]:
    return [d.code for d in found]


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


# --- the happy path ------------------------------------------------------------------------------


def test_a_service_opened_pair_proof_classifies_as_its_mode_and_passes(world: World) -> None:
    rel = world.put(world.record())
    cls, found = world.gate(rel)
    assert cls.mode == "pair-proof"
    assert found == [], [d.as_dict() for d in found]


def test_a_hand_opened_pair_proof_by_its_author_passes(world: World) -> None:
    rel = world.put(world.record())
    _cls, found = world.gate(rel, opener=AUTHOR)
    assert found == [], [d.as_dict() for d in found]


def test_a_refutation_at_an_instance_passes(tmp_path: Path) -> None:
    w = World(tmp_path, second="bad-zero")
    a, b = w.cand(w.a), w.cand(w.b)
    # faithful holds at 0 and bad-zero fails: refute faithful -> bad-zero
    direction = w.direction
    tmpl = pair_proofs.template(a, b, direction, "refutation", 0)
    lean = tmpl.replace(pair_proofs.PLACEHOLDER, "  decide\n")
    doc = w.record(
        kind="refutation",
        case={"probe": "holds", "n": 0, "set": None, "concept": None},
        lean=lean,
    )
    _cls, found = w.gate(w.put(doc))
    assert found == [], [d.as_dict() for d in found]


# --- one direction per pull request, append-only -------------------------------------------------


def test_two_pair_proofs_in_one_pull_request_are_refused(world: World) -> None:
    one = world.put(world.record())
    two = world.put(world.record(date="2026-10-27T01:00:01Z"))
    cls = modes.classify(
        [Change("A", one), Change("A", two)],
        author=SERVICE,
        graph_root=world.graph,
        service_login=SERVICE,
    )
    assert codes_of(list(cls.problems)) == ["pair-proof-multiple"]
    assert not cls.ok


@pytest.mark.parametrize("status", ["M", "D"])
def test_a_merged_pair_proof_is_never_modified_or_deleted(
    world: World, status: Literal["M", "D"]
) -> None:
    rel = world.put(world.record())
    cls, found = world.gate(rel, status=status)
    assert not cls.ok
    assert codes_of(found) == ["path-forbidden"]


def test_a_pair_proof_with_another_review_record_is_a_mixture(world: World) -> None:
    rel = world.put(world.record())
    cand = f"targets/{TARGET}/review/candidates/c-12345678.yaml"
    cls = modes.classify(
        [Change("A", rel), Change("A", cand)],
        author=SERVICE,
        graph_root=world.graph,
        service_login=SERVICE,
    )
    assert codes_of(list(cls.problems)) == ["mode-mixed"]


# --- the record ----------------------------------------------------------------------------------


def test_a_record_that_does_not_validate_is_refused(world: World) -> None:
    doc = world.record()
    doc["kind"] = "disproof"
    _cls, found = world.gate(world.put(doc, world.path_for(world.record())))
    assert codes_of(found) == ["record-invalid"]


def test_a_record_for_another_target_is_refused(world: World) -> None:
    doc = world.record(target="erdos-1")
    rel = world.put(doc, world.path_for(world.record()))
    _cls, found = world.gate(rel)
    assert codes_of(found) == ["review-target-mismatch"]


@pytest.mark.parametrize(
    "name",
    [
        "{a}--{b}--{d}--20261027T010001Z-{au}.yaml",  # another stamp
        "{a}--{b}--{d}--{s}-someone-else.yaml",  # another author
        "{a}--{b}--{o}--{s}-{au}.yaml",  # the other direction
        "{b}--{a}--{d}--{s}-{au}.yaml",  # the pair the wrong way round
        "{a}--{b}--{d}--{s}-{au}-2.yaml",  # anything else
    ],
)
def test_a_record_named_for_anything_but_itself_is_refused(world: World, name: str) -> None:
    doc = world.record()
    other = "backward" if doc["direction"] == "forward" else "forward"
    fname = name.format(a=world.a, b=world.b, d=doc["direction"], o=other, s=STAMP, au=AUTHOR)
    rel = world.put(doc, f"targets/{TARGET}/review/{pair_proofs.DIR}/{fname}")
    _cls, found = world.gate(rel)
    assert codes_of(found) == ["pair-proof-name"]


def test_a_record_whose_pair_is_not_in_order_is_refused(world: World) -> None:
    doc = world.record(a=world.b, b=world.a)
    _cls, found = world.gate(world.put(doc))
    assert codes_of(found) == ["pair-proof-name"]
    assert "lexically" in found[0].message


# --- who it is for -------------------------------------------------------------------------------


def test_a_hand_opened_record_naming_someone_else_is_refused(world: World) -> None:
    rel = world.put(world.record())
    _cls, found = world.gate(rel, opener="mallory")
    assert codes_of(found) == ["pair-proof-not-author"]
    assert found[0].details["opened_by"] == ["mallory"]


def test_a_hand_opened_record_by_a_curator_login_acts_for_their_pseudonym(world: World) -> None:
    (world.graph / "curators.json").write_text(
        json.dumps({"identities": [{"pseudonym": AUTHOR, "github_login": "curator-login"}]})
    )
    rel = world.put(world.record())
    _cls, found = world.gate(rel, opener="curator-login")
    assert found == [], [d.as_dict() for d in found]


# --- the base tree: the review, the candidates, the pair ------------------------------------------


def test_a_target_with_no_review_takes_no_pair_proof(world: World) -> None:
    rel = world.put(world.record())
    (world.base / "review.yaml").unlink()
    _cls, found = world.gate(rel)
    assert codes_of(found) == ["pair-proof-no-review"]


def test_a_candidate_the_review_does_not_hold_is_refused(world: World) -> None:
    doc = world.record(b="c-ffffffff")
    _cls, found = world.gate(world.put(doc))
    assert codes_of(found) == ["pair-candidate-unknown"]
    assert found[0].details["candidate"] == "c-ffffffff"


def test_a_statement_hash_that_is_not_the_candidates_is_refused(world: World) -> None:
    doc = world.record()
    doc["statement_hashes"] = {"a": doc["statement_hashes"]["a"], "b": "0" * 64}
    _cls, found = world.gate(world.put(doc))
    assert codes_of(found) == ["pair-candidate-mismatch"]
    assert found[0].details["candidate"] == world.b


def test_a_discarded_candidate_takes_no_pair_proof(world: World) -> None:
    discard(world.graph, world.b)
    _cls, found = world.gate(world.put(world.record()))
    assert codes_of(found) == ["pair-candidate-not-surviving"]
    assert found[0].details["status"] == "discarded"


def test_a_pending_candidate_takes_no_pair_proof(world: World) -> None:
    for p in (world.base / "exhibits").glob("*.json"):
        if json.loads(p.read_text())["candidate"] == world.a:
            p.unlink()
    _cls, found = world.gate(world.put(world.record()))
    assert codes_of(found) == ["pair-candidate-not-surviving"]
    assert found[0].details["status"] == "pending"


def test_a_pair_the_job_has_not_compared_is_not_open(world: World) -> None:
    for p in (world.base / "pairs").glob("*.yaml"):
        p.unlink()
    _cls, found = world.gate(world.put(world.record()))
    assert codes_of(found) == ["pair-not-open"]


@pytest.mark.parametrize("state", ["proved", "refuted"])
def test_a_settled_direction_is_not_open(world: World, state: str) -> None:
    settled = {"state": state, "exhibit": "e-00000001", "attempt": None}
    d = world.direction
    write_pair(
        world.graph,
        world.a,
        world.b,
        settled if d == "forward" else open_way(),
        settled if d == "backward" else open_way(),
    )
    _cls, found = world.gate(world.put(world.record()))
    assert codes_of(found) == ["pair-not-open"]
    assert found[0].details["state"] == state


def test_the_latest_pair_record_is_the_one_read(world: World) -> None:
    """``review._pairs``: a later record for the same pair supersedes; here the job proved the
    direction after the first record left it open."""
    d = world.direction
    write_pair(
        world.graph,
        world.a,
        world.b,
        proved_way() if d == "forward" else open_way(),
        proved_way() if d == "backward" else open_way(),
        date="2026-10-20",
        name=f"{world.a}--{world.b}--2026-10-20-2.yaml",
    )
    _cls, found = world.gate(world.put(world.record()))
    assert codes_of(found) == ["pair-not-open"]


def test_a_later_open_record_reopens_nothing_it_did_not_say(world: World) -> None:
    """The other way round: an earlier proved record superseded by a later open one is open."""
    d = world.direction
    write_pair(
        world.graph,
        world.a,
        world.b,
        proved_way() if d == "forward" else open_way(),
        proved_way() if d == "backward" else open_way(),
        date="2026-10-01",
        name=f"{world.a}--{world.b}--2026-10-01-0.yaml",
    )
    _cls, found = world.gate(world.put(world.record()))
    assert found == []


def test_a_direction_an_earlier_merged_record_settled_is_refused(world: World) -> None:
    world.put(world.record(date="2026-10-26T09:00:00Z"))  # merged before this one
    rel = world.put(world.record())
    _cls, found = world.gate(rel)
    assert codes_of(found) == ["pair-proof-settled"]
    assert found[0].details["earlier"].endswith("20261026T090000Z-t1027-g.yaml")


def test_an_earlier_record_of_the_other_direction_settles_nothing_here(world: World) -> None:
    other = "backward" if world.direction == "forward" else "forward"
    world.put(world.record(direction=other, date="2026-10-26T09:00:00Z"))
    _cls, found = world.gate(world.put(world.record()))
    assert found == [], [d.as_dict() for d in found]


# --- the Lean against the template ----------------------------------------------------------------


def test_lean_that_differs_from_the_template_is_refused(world: World) -> None:
    doc = world.record()
    doc["lean"] = doc["lean"].replace(
        "set_option maxHeartbeats 1000000", "set_option maxHeartbeats 0"
    )
    _cls, found = world.gate(world.put(doc))
    assert codes_of(found) == ["pair-proof-template-mismatch"]


def test_lean_for_the_other_direction_is_refused(world: World) -> None:
    other: pair_proofs.Direction = "backward" if world.direction == "forward" else "forward"
    doc = world.record()
    doc["lean"] = world.filled(other)
    _cls, found = world.gate(world.put(doc))
    assert codes_of(found) == ["pair-proof-template-mismatch"]


def test_a_forbidden_region_is_refused(world: World) -> None:
    doc = world.record()
    doc["lean"] = doc["lean"].replace(PROOF, "  intro hn\n  sorry\n")
    _cls, found = world.gate(world.put(doc))
    assert codes_of(found) == ["pair-proof-forbidden"]


@pytest.mark.parametrize(
    ("kind", "case", "why"),
    [
        ("proof", {"probe": "holds", "n": 3, "set": None, "concept": None}, "no instance"),
        ("refutation", None, "names its instance"),
    ],
)
def test_a_kind_and_case_that_do_not_fit_are_refused(
    world: World, kind: str, case: dict[str, Any] | None, why: str
) -> None:
    _cls, found = world.gate(world.put(world.record(kind=kind, case=case)))
    assert codes_of(found) == ["pair-proof-kind"]
    assert why in found[0].message


def test_a_closed_direction_cannot_be_refuted(tmp_path: Path) -> None:
    """erdos-849's closed claims: a refutation names an instance, and only indexed claims have
    one (``pair_proofs.refutable``)."""
    root = Path(__file__).parent / "fixtures" / "review" / "erdos-849"
    graph, ids = make_graph(
        tmp_path,
        concepts=(),
        candidates={
            "root": (root / "c-ae9bea28.lean").read_text(encoding="utf-8"),
            "pairs": (root / "c-fb339e85.lean").read_text(encoding="utf-8"),
        },
    )
    a, b = sorted(ids.values())
    for cid in ids.values():
        survive(graph, cid)
    write_pair(graph, a, b, open_way(), open_way())
    w = World.__new__(World)
    w.graph, w.ids, w.a, w.b = graph, ids, a, b
    w.base = graph / "targets" / TARGET / "review"
    doc = {
        "schema": "pair-proof/v1",
        "target": TARGET,
        "a": a,
        "b": b,
        "direction": "forward",
        "kind": "refutation",
        "case": {"probe": "holds", "n": 1, "set": None, "concept": None},
        "statement_hashes": {"a": w.statement_hash(a), "b": w.statement_hash(b)},
        "lean": "-- opn-review: {}\n",
        "author": AUTHOR,
        "models": [],
        "date": STAMP_DATE,
    }
    _cls, found = w.gate(w.put(doc))
    assert codes_of(found) == ["pair-proof-kind"]
    assert "only indexed claims" in found[0].message


# --- every code is registered ------------------------------------------------------------------


def test_every_refusal_this_mode_names_is_in_the_catalog() -> None:
    for code in (
        "pair-proof-multiple",
        "pair-proof-name",
        "pair-proof-not-author",
        "pair-proof-no-review",
        "pair-candidate-unknown",
        "pair-candidate-mismatch",
        "pair-candidate-not-surviving",
        "pair-not-open",
        "pair-proof-settled",
        "pair-proof-kind",
    ):
        # the service raises the same refusal before a pull request opens (F26-T19): "both"
        assert codes.CATALOG[code].source in ("gate", "both"), code


# --- the workflow's switch and the sandboxed command ---------------------------------------------


class Repo:
    """The world's graph as a git checkout: the base commit, then the pull request's."""

    def __init__(self, world: World) -> None:
        self.world = world
        self.root = world.graph
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.org")
        self.git("config", "user.name", "t")
        self.commit("base")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            text=True,
            env=config.child_environment(drop=config.GIT_REPO_VARIABLES),
        ).stdout.strip()

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, Any], str]:
    capsys.readouterr()
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, (json.loads(captured.out) if captured.out.strip() else {}), captured.err


@pytest.fixture
def repo(world: World) -> Repo:
    return Repo(world)


def test_classify_asks_the_workflow_for_the_sandbox(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """``needs_pair_proof`` and the record, read by the workflow with a default so a pin that
    predates them skips the step (F08-Q8's shape)."""
    rel = repo.world.put(repo.world.record())
    repo.commit("pair proof")
    code, out, err = run(
        capsys, "classify", "--graph", str(repo.root), "--base", "HEAD~1", "--author", AUTHOR
    )
    assert code == cli.EXIT_PASS, err
    assert out["mode"] == "pair-proof" and out["ok"] is True
    assert out["needs_pair_proof"] is True and out["pair_proofs"] == [rel]
    assert out["needs_gate"] is False and out["needs_exhibits"] is False
    assert out["needs_review"] is False  # the gate's check is the review; no step 9


def test_classify_asks_no_sandbox_of_any_other_diff(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    add_answer_like = repo.world.base / "candidates" / "c-0000000a.yaml"
    add_answer_like.write_text("schema: candidate/v1\n")
    repo.commit("a bad candidate")
    _code, out, _err = run(
        capsys, "classify", "--graph", str(repo.root), "--base", "HEAD~1", "--author", AUTHOR
    )
    assert out["needs_pair_proof"] is False and out["pair_proofs"] == []


def test_a_refused_record_asks_for_no_sandbox(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    repo.world.put(
        repo.world.record(author="someone-else"), repo.world.path_for(repo.world.record())
    )
    repo.commit("pair proof")
    code, out, _err = run(
        capsys, "classify", "--graph", str(repo.root), "--base", "HEAD~1", "--author", AUTHOR
    )
    assert code == cli.EXIT_FAIL
    assert out["needs_pair_proof"] is False


def fake_toolchain(monkeypatch: pytest.MonkeyPatch, fake: Any) -> None:
    monkeypatch.setattr(toolchain.LocalToolchain, "from_settings", classmethod(lambda _c, _s: fake))


def test_the_command_runs_the_verdict_for_the_record_and_prints_it(
    repo: Repo,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    rel = repo.world.put(repo.world.record())
    repo.commit("pair proof")
    fake = PairFake(axiom_result=STANDARD)
    fake_toolchain(monkeypatch, fake)
    out_dir = tmp_path / "out"
    code, out, err = run(
        capsys,
        "pair-proofs",
        "--graph",
        str(repo.root),
        "--base",
        "HEAD~1",
        "--out",
        str(out_dir),
    )
    assert code == cli.EXIT_PASS, err
    assert out["ok"] is True and out["record"] == rel and out["sandboxed"] is False
    assert out["verdict"]["ok"] is True
    assert out["verdict"]["axioms"] == sorted(STANDARD.axioms)
    assert json.loads((out_dir / "pair-proofs.json").read_text()) == out
    assert "elaborate:filled" in fake.calls and "elaborate:guard" in fake.calls


def test_the_command_fails_naming_the_verdicts_refusal(
    repo: Repo,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo.world.put(repo.world.record())
    repo.commit("pair proof")
    fake_toolchain(monkeypatch, PairFake(axiom_result=STANDARD, guard_ok=True))
    code, out, err = run(
        capsys,
        "pair-proofs",
        "--graph",
        str(repo.root),
        "--base",
        "HEAD~1",
        "--out",
        str(tmp_path / "out"),
    )
    assert code == cli.EXIT_FAIL
    assert out["ok"] is False
    assert [p["code"] for p in out["problems"]] == ["pair-proof-degenerate"]
    assert "pair-proof-degenerate" in err


def test_the_command_re_reads_the_tree_and_refuses_an_inadmissible_record(
    repo: Repo,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The command judges the Lean of a record the tree takes; a record the tree does not take
    is refused before any toolchain runs, whatever the classify step said."""
    discard(repo.world.graph, repo.world.b)
    repo.commit("the job discards b")  # the tree's own state, before the pull request
    repo.world.put(repo.world.record())
    repo.commit("pair proof")
    fake = PairFake(axiom_result=STANDARD)
    fake_toolchain(monkeypatch, fake)
    code, out, _err = run(
        capsys,
        "pair-proofs",
        "--graph",
        str(repo.root),
        "--base",
        "HEAD~1",
        "--out",
        str(tmp_path / "out"),
    )
    assert code == cli.EXIT_FAIL
    assert [p["code"] for p in out["problems"]] == ["pair-candidate-not-surviving"]
    assert [c for c in fake.calls if c.startswith("elaborate")] == []


def test_the_command_belongs_to_the_pair_proof_mode_alone(
    repo: Repo, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    (repo.world.base / "candidates" / "c-0000000a.yaml").write_text("schema: candidate/v1\n")
    repo.commit("a candidate")
    code, _out, err = run(
        capsys,
        "pair-proofs",
        "--graph",
        str(repo.root),
        "--base",
        "HEAD~1",
        "--out",
        str(tmp_path / "out"),
    )
    assert code == cli.EXIT_ERROR
    assert "pair-proof" in err


def test_the_command_builds_the_graph_modules_the_candidates_import(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """F26-Q21 and the 2026-10-14 lesson (a root importing ``Defs`` was published as discarded):
    a candidate that imports a graph module is judged with that module built from the graph and
    on every call's search path."""
    w = World(tmp_path, header="import Defs.Extra\n")
    defs = w.graph / "targets" / TARGET / "defs"
    defs.mkdir()
    (defs / "Extra.lean").write_text("def Defs.extra : Nat := 1\n", encoding="utf-8")
    r = Repo(w)
    w.put(w.record())
    r.commit("pair proof")
    fake = PairFake(axiom_result=STANDARD)
    fake_toolchain(monkeypatch, fake)
    code, out, err = run(
        capsys,
        "pair-proofs",
        "--graph",
        str(r.root),
        "--base",
        "HEAD~1",
        "--out",
        str(tmp_path / "out"),
    )
    assert code == cli.EXIT_PASS, (out, err)
    assert any(t == "def Defs.extra : Nat := 1\n" for t in fake.texts)  # built from the graph
    judged = [ro for what, ro, _rw in fake.mounts if what in ("replay", "axioms", "meaning")]
    assert judged and all(
        any(p.name == "build" and p.parent.name == "graph" for p in ro) for ro in judged
    )


@pytest.mark.docker
def test_the_command_in_the_step_3_sandbox(
    repo: Repo, capsys: pytest.CaptureFixture[str], sandbox_image: str, tmp_path: Path
) -> None:
    """The workflow's own invocation, ``--sandbox``: the real Lean in the step-3 image."""
    repo.world.put(repo.world.record())
    repo.commit("pair proof")
    code, out, err = run(
        capsys,
        "pair-proofs",
        "--graph",
        str(repo.root),
        "--base",
        "HEAD~1",
        "--sandbox",
        "--image",
        sandbox_image,
        "--out",
        str(tmp_path / "out"),
    )
    assert code == cli.EXIT_PASS, (out, err)
    assert out["sandboxed"] is True and out["verdict"]["ok"] is True


@pytest.mark.lean
def test_the_command_with_the_real_toolchain(
    repo: Repo, capsys: pytest.CaptureFixture[str], lean_pkg: Path, tmp_path: Path
) -> None:
    """End to end at Lean 4.33.1 without the sandbox (the laptop's tier): the record the
    classify step admitted, rebuilt from the tree, judged by the real verdict."""
    del lean_pkg  # built: the metaprograms the verdict asks
    rel = repo.world.put(repo.world.record())
    repo.commit("pair proof")
    code, out, err = run(
        capsys, "classify", "--graph", str(repo.root), "--base", "HEAD~1", "--author", AUTHOR
    )
    assert code == cli.EXIT_PASS and out["needs_pair_proof"] is True, err
    code, out, err = run(
        capsys,
        "pair-proofs",
        "--graph",
        str(repo.root),
        "--base",
        "HEAD~1",
        "--out",
        str(tmp_path / "out"),
    )
    assert code == cli.EXIT_PASS, (out, err)
    assert out["record"] == rel and out["verdict"]["ok"] is True
