"""F07-T50 (R23, AC44, Q57; D-29 v3.24): a partial carries its holes' witnesses.

The finding (testers 2026-10-01, B2): every level of a skeleton chain cost two passes through
the merge queue. A hole was born with an empty witness slot, so a separate witness pull request
had to merge and render before anything could be prechecked against the hole: #348 merged at
16:00:32, its witness #349 rendered at 16:21:34, with the queue empty; in round 2 the same step
ran from 12:51 to 14:30. The precheck already printed each hole's expected witness type, and the
witness was usually the parent's with a line changed.

The owner's ruling, 2026-10-01: "Okay, on letting a partial carry its hole's witnesses."

So a partial may add, beside its assembly ``attempts/<name>.lean``, files
``attempts/<name>.<n>.witness``, each the ``Witness.lean`` one hole's node is to be born with,
naming the hole on ``-- hole: <name>``. Step 2 refuses a malformed one by name; step 7 holds each
to the node witness's own check against the statement the post-merge job will write; and that job
writes what its run checked. A hole with nothing carried is created as before, and a partial that
carries nothing produces what it produced before, byte for byte.

Over the fake seam; the real elaboration is ``test_finding_partial_carries_witnesses_lean.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from fakes import FakeToolchain, artifact_result, witness_result
from harness import TARGET, copy_graph, node_dir
from test_cli_sandboxed import NODES, Seam, git_repo, run
from test_partial import ROOT, assembly_for, partial_context
from test_postmerge import ASSEMBLY, HOLES, PARENT, PSEUDONYM, STAMP, hole, snapshot

from opn_gate import carried, cli, graph, judging, modes, paths, pipeline, postmerge, schemas
from opn_gate.paths import Change
from opn_gate.steps.artifact import ARTIFACT_KEY, PARTIAL_KEY
from opn_gate.toolchain import MetaprogramResult, ResolvedToolchain, WitnessRequest

STAMP_FILE = "20260912T120000Z-someone-partial.lean"
STEM = "20260912T120000Z-someone-partial"
#: The two holes of ``test_partial``'s assembly, closed, as the extractor would report them.
CLOSED = {
    "right": "∀ (p q r : Prop), (p ∧ q) ∧ r → r",
    "left": "∀ (p q r : Prop), (p ∧ q) ∧ r → q ∧ p",
}
EXPECTED = "∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), (p ∧ q) ∧ r"
NODE_WITNESS = witness_result(expected="∃ p q r, (p ∧ q) ∧ r", witness="∃ p q r, (p ∧ q) ∧ r")
GOOD = witness_result(expected=EXPECTED, witness=EXPECTED)
WRONG = witness_result(expected=EXPECTED, witness="True")


def witness_text(
    hole_name: str, body: str = "⟨True, True, True, ⟨trivial, trivial⟩, trivial⟩"
) -> str:
    return f"-- hole: {hole_name}\n\ntheorem witness : {EXPECTED} :=\n  {body}\n"


def holes_report(**extra: dict[str, Any]) -> MetaprogramResult:
    report = artifact_result(holes=[(n, c, False) for n, c in CLOSED.items()])
    for doc in report.doc["holes"]:
        doc["expected_witness"] = EXPECTED
        doc.update(extra.get(doc["name"], {}))
    return report


@dataclass
class PerHole(FakeToolchain):
    """The fake seam, answering step 7 by the declaration asked about: the node's own witness
    as ``witness`` says, a staged child's as ``by_decl`` says (default: it is a witness)."""

    by_decl: dict[str, MetaprogramResult] = field(default_factory=dict)
    #: What each staged child looked like when step 7 asked: statement and witness text.
    seen: dict[str, tuple[str, str]] = field(default_factory=dict)
    search_paths: dict[str, list[Path]] = field(default_factory=dict)

    def witness_type(
        self,
        tc: ResolvedToolchain,
        req: WitnessRequest,
        search_path: Any,
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        answer = super().witness_type(tc, req, search_path, timeout_s=timeout_s)
        if "__h" not in req.decl:
            return answer
        assert req.witness is not None
        self.seen[req.decl] = (
            req.statement.read_text(encoding="utf-8"),
            req.witness.read_text(encoding="utf-8"),
        )
        self.search_paths[req.decl] = list(search_path)
        return self.by_decl.get(req.decl, GOOD)


def carrying(  # type: ignore[no-untyped-def]
    tmp_path: Path,
    files: dict[str, str],
    *,
    fake: PerHole | None = None,
    report: MetaprogramResult | None = None,
):
    """``test_partial``'s submission plus ``files`` (name under attempts/ -> text) in the diff."""
    fake = fake or PerHole(witness=NODE_WITNESS)
    fake.artifact = report or holes_report()
    ctx, stamp = partial_context(tmp_path, toolchain=fake)
    assert stamp == STAMP_FILE
    for name, text in files.items():
        (node_dir(ctx) / "attempts" / name).write_text(text, encoding="utf-8")
        ctx.changes.append(Change("A", f"targets/{TARGET}/nodes/{ROOT}/attempts/{name}"))
    return ctx, fake


BOTH = {f"{STEM}.1.witness": witness_text("right"), f"{STEM}.2.witness": witness_text("left")}


# --- the grammar (paths, mode) -------------------------------------------------------------------


def test_a_carried_witness_has_a_role_and_rides_in_partial_mode() -> None:
    """R23: ``attempts/<name>.<n>.witness`` is a path a partial may add, and nothing else may."""
    prefix = f"targets/{TARGET}/nodes/{ROOT}/attempts/"
    where = paths.locate(prefix + f"{STEM}.1.witness")
    assert where is not None and where.role == "hole-witness" and where.node_id == ROOT
    assert "hole-witness" not in paths.MODIFIABLE_ROLES and "hole-witness" not in paths.APPEND_ROLES
    both = [Change("A", prefix + STAMP_FILE), Change("A", prefix + f"{STEM}.1.witness")]
    assert modes.classify(both).mode == "partial"
    with_annex = [*both, Change("A", f"targets/{TARGET}/nodes/{ROOT}/annex/{'a' * 64}.md")]
    assert modes.classify(with_annex).mode == "partial"
    alone = modes.classify(both[1:])
    assert alone.mode is None and alone.problems[0].code == "mode-mixed"
    beside_a_proof = modes.classify(
        [Change("A", f"targets/{TARGET}/nodes/{ROOT}/Proof.lean"), both[1]]
    )
    assert beside_a_proof.mode is None
    modified = modes.classify([both[0], Change("M", both[1].path)])
    assert modified.mode is None and modified.problems[0].code == "path-forbidden"


def test_the_readers_of_assemblies_do_not_see_a_carried_witness(tmp_path: Path) -> None:
    """Q57 (2): the suffix is not ``.lean``, so every reader of ``attempts/*.lean`` reads what it
    read — here the gate's own two: the attempt count and step 2's choice of the assembly."""
    from opn_gate import records  # noqa: PLC0415

    ctx, _ = carrying(tmp_path, BOTH)
    plain, _ = partial_context(tmp_path / "plain")
    assert records.load_attempts(node_dir(ctx)) == records.load_attempts(node_dir(plain))
    ctx.changes = None  # a bare tree: the newest assembly, never a witness file
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert ctx.data[PARTIAL_KEY]["path"] == f"attempts/{STAMP_FILE}"
    assert [w["hole"] for w in ctx.data[carried.DATA_KEY]] == ["right", "left"]


# --- step 2: what is refused before any Lean ----------------------------------------------------


@pytest.mark.parametrize(
    ("files", "code"),
    [
        ({f"{STEM}.1.witness": "theorem witness : True := trivial\n"}, "hole-witness-unnamed"),
        (
            {
                f"{STEM}.1.witness": witness_text("right"),
                f"{STEM}.2.witness": witness_text("right"),
            },
            "hole-witness-duplicate",
        ),
        ({f"{STEM}.1.witness": witness_text("right", "by sorry")}, "hole-witness-sorry"),
        ({"other-partial.1.witness": witness_text("right")}, "hole-witness-unattached"),
        ({f"{STEM}.01.witness": witness_text("right")}, "hole-witness-unattached"),
        ({f"{STEM}.witness": witness_text("right")}, "hole-witness-unattached"),
    ],
)
def test_a_malformed_carried_witness_is_refused_at_step_2(
    tmp_path: Path, files: dict[str, str], code: str
) -> None:
    ctx, fake = carrying(tmp_path, files)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == code
    assert verdict.diagnostic.details["path"].startswith("attempts/")
    assert not any(c.startswith(("elaborate", "witness_type")) for c in fake.calls)


def test_a_witness_file_beside_a_proof_is_refused(tmp_path: Path) -> None:
    """R23: a carried witness belongs to a partial. On a node whose submission is its Proof.lean
    the file is refused by name at step 2, which is what a precheck (it never classifies) sees."""
    from harness import make_context  # noqa: PLC0415

    ctx = make_context(tmp_path)
    name = f"{STEM}.1.witness"
    attempts = node_dir(ctx) / "attempts"
    attempts.mkdir(exist_ok=True)
    (attempts / name).write_text(witness_text("right"), encoding="utf-8")
    assert ctx.changes is not None
    ctx.changes.append(Change("A", ctx.claim.node_prefix + f"attempts/{name}"))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "hole-witness-without-partial"
    assert verdict.diagnostic.details["paths"] == [f"attempts/{name}"]


# --- step 7: the same check, once per carried witness -------------------------------------------


def test_every_carried_witness_is_held_to_step_7_and_recorded(tmp_path: Path) -> None:
    """AC44: steps 1 to 8 pass; step 7 asks once for the node and once per carried witness,
    against the statement the post-merge job will write, staged under the work directory with
    the carried text as its Witness.lean; the pass names each witness with its hash."""
    ctx, fake = carrying(tmp_path, BOTH)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert [r.decl for r in fake.witness_requests] == [
        "OpnProp.and_swap_reassoc",
        "and_swap_reassoc__h1",
        "and_swap_reassoc__h2",
    ]
    holes = [art_hole(h) for h in ctx.data[ARTIFACT_KEY]["holes"]]
    for req, (name, text), h, child in zip(
        fake.witness_requests[1:], BOTH.items(), holes, (f"{ROOT}--h1", f"{ROOT}--h2"), strict=True
    ):
        staged = ctx.workdir / "holes" / "src" / "Nodes" / child
        assert req.statement == staged / "Statement.lean" and req.witness == staged / "Witness.lean"
        assert req.statement_module == f"Nodes.«{child}».Statement"
        proposal = postmerge.child_proposal(node_dir(ctx), child, h, author="x", origin="x")
        # F07-T75: staged as the child is born, without its `-- hole:` line.
        assert fake.seen[req.decl] == (proposal.statement, carried.as_witness(text))
        assert CLOSED[h.name] in proposal.statement
        # The child's own Context is compiled beside it. F02-T12: the program reads the child's
        # statement as the gate built it from those files in the judging directory, and nothing
        # under the work directory is on its path.
        assert fake.search_paths[req.decl] == [
            judging.root_for(ctx.workdir) / f"witness-{child}" / "meaning" / "build"
        ]
        assert f"elaborate:Nodes.«{child}».Context" in fake.calls
        assert name.endswith(".witness")
    step7 = next(s for s in verdict.steps if s.step == 7)
    assert step7.diagnostic is not None and step7.diagnostic.code == "hole-witnesses"
    recorded = step7.diagnostic.details["witnesses"]
    assert recorded == [
        carried.Carried("right", f"attempts/{STEM}.1.witness", BOTH[f"{STEM}.1.witness"]).as_dict(),
        carried.Carried("left", f"attempts/{STEM}.2.witness", BOTH[f"{STEM}.2.witness"]).as_dict(),
    ]
    assert [w["hole"] for w in ctx.data[carried.DATA_KEY]] == ["right", "left"]
    assert verdict.as_dict()["steps"][5]["diagnostic"]["details"]["witnesses"] == recorded
    # Nothing was built into the node's own build directory for the children (step 4's replay
    # and the olean cache read it).
    assert not (ctx.build_dir / "Nodes" / f"{ROOT}--h1").exists()


def art_hole(doc: dict[str, Any]) -> Any:
    from opn_gate.steps.artifact import Hole  # noqa: PLC0415

    return Hole.of(doc)


def test_a_carried_witness_is_narrowed_as_the_node_will_be(tmp_path: Path) -> None:
    """F07-T44 with R23: the extractor's ``proved_binders`` for the hole are what step 7 is asked
    with, exactly as it will be asked of the node once its META records them."""
    report = holes_report(left={"proved_binders": [4, 5]})
    ctx, fake = carrying(tmp_path, BOTH, report=report)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    by_decl = {r.decl: r for r in fake.witness_requests}
    assert by_decl["and_swap_reassoc__h1"].proved == ()
    assert by_decl["and_swap_reassoc__h2"].proved == (4, 5)
    assert "--proved" in by_decl["and_swap_reassoc__h2"].args()


@pytest.mark.parametrize(
    ("answer", "code"),
    [
        (WRONG, "witness-type-mismatch"),
        (witness_result(expected=EXPECTED, witness=EXPECTED, axioms=("sorryAx",)), "witness-sorry"),
        (witness_result(expected=EXPECTED, witness=EXPECTED, axioms=("Foo.ax",)), "witness-axiom"),
        (
            MetaprogramResult(ok=False, doc={"ok": False, "error": "witness does not elaborate"}),
            "witness-elaboration",
        ),
        (
            MetaprogramResult(ok=False, exit_code=139, output="Segmentation fault"),
            "metaprogram-failed",
        ),
    ],
)
def test_a_carried_witness_that_fails_refuses_the_partial(
    tmp_path: Path, answer: MetaprogramResult, code: str
) -> None:
    """AC44: the whole partial fails at step 7 with step 7's own code, naming the hole and the
    file; nothing is recorded for the post-merge job to write."""
    fake = PerHole(witness=NODE_WITNESS, by_decl={"and_swap_reassoc__h2": answer})
    ctx, _ = carrying(tmp_path, BOTH, fake=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 7, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == code
    assert verdict.diagnostic.details["hole"] == "left"
    assert verdict.diagnostic.details["path"] == f"attempts/{STEM}.2.witness"
    assert verdict.diagnostic.message.startswith("hole left (")
    assert carried.DATA_KEY not in ctx.data
    # The node's own step-7 record is the node's, whatever a carried witness did.
    assert ctx.data["witness"]["expected"] == "∃ p q r, (p ∧ q) ∧ r"


def test_a_witness_for_a_hole_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    ctx, fake = carrying(tmp_path, {f"{STEM}.1.witness": witness_text("middle")})
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 7
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "hole-witness-unknown"
    assert verdict.diagnostic.details == {
        "hole": "middle",
        "path": f"attempts/{STEM}.1.witness",
        "holes": ["right", "left"],
    }
    assert len(fake.witness_requests) == 1  # the node's; no child was asked about


def test_a_name_two_holes_share_is_refused(tmp_path: Path) -> None:
    report = artifact_result(holes=[("h", CLOSED["right"], False), ("h", CLOSED["left"], False)])
    ctx, _ = carrying(tmp_path, {f"{STEM}.1.witness": witness_text("h")}, report=report)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 7
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "hole-witness-ambiguous"
    assert verdict.diagnostic.details["hole"] == "h"


def test_the_nodes_own_witness_is_judged_first(tmp_path: Path) -> None:
    """A partial on a node whose own witness fails is refused on that, as it always was, before
    any carried witness is looked at."""
    fake = PerHole(witness=witness_result(expected="∃ p q r, (p ∧ q) ∧ r", witness="True"))
    ctx, _ = carrying(tmp_path, BOTH, fake=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 7
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "witness-type-mismatch"
    assert "hole" not in verdict.diagnostic.details
    assert len(fake.witness_requests) == 1


# --- the old shape, byte for byte --------------------------------------------------------------


def test_a_partial_that_carries_nothing_is_what_it_was(tmp_path: Path) -> None:
    """R23's last sentence. The verdict of ``test_partial``'s submission, the record step 2
    leaves, the one witness request and the writer's output for it are pinned as they were
    before this task (run against the code before it: green)."""
    fake = PerHole(witness=NODE_WITNESS)
    fake.artifact = artifact_result(holes=[(n, c, False) for n, c in CLOSED.items()])
    ctx, _ = partial_context(tmp_path, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None
    assert sorted(ctx.data[PARTIAL_KEY]) == ["file", "path"]
    assert carried.DATA_KEY not in ctx.data
    assert [
        (s["step"], s["result"], (s["diagnostic"] or {}).get("code"))
        for s in verdict.as_dict()["steps"]
    ] == [
        (1, "pass", None),
        (2, "pass", "partial-submission"),
        (4, "pass", "artifact-partial"),
        (5, "pass", None),
        (6, "pass", None),
        (7, "pass", None),
        (8, "pass", None),
    ]
    assert len(fake.witness_requests) == 1 and not (ctx.workdir / "holes").exists()


def test_the_writer_without_witnesses_writes_the_slots_it_wrote(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    parent = root / "targets" / TARGET / "nodes" / PARENT
    merged = postmerge.apply_partial(
        parent, HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP
    )
    assert merged.as_dict() == {
        "children": [f"{PARENT}--h1", f"{PARENT}--h2"],
        "attempt": f"attempts/{STAMP}-{PSEUDONYM}-partial.lean",
        "origin": "compiler-derived",
        "annex": None,
        "holes": [
            {"name": "right", "child": f"{PARENT}--h1", "reused_node": None},
            {"name": "left", "child": f"{PARENT}--h2", "reused_node": None},
        ],
    }
    for child in merged.children:
        node = parent.parent / child
        statement = (node / "Statement.lean").read_text(encoding="utf-8")
        assert (node / "Witness.lean").read_text(encoding="utf-8") == postmerge.witness_slot(
            None, statement
        )
        assert graph.witness_is_stub(node)
    same = copy_graph(tmp_path / "again")
    again = same / "targets" / TARGET / "nodes" / PARENT
    postmerge.apply_partial(
        again, HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP, witnesses={}
    )
    assert snapshot(again) == snapshot(parent)


# --- the post-merge writer ----------------------------------------------------------------------


def decomposed(tmp_path: Path, witnesses: dict[str, str]) -> tuple[Path, postmerge.PartialMerge]:
    """The fixture with the root unproved and one partial applied, carrying ``witnesses``."""
    from test_products import attest  # noqa: PLC0415

    root = copy_graph(tmp_path, publish=True)
    parent = root / "targets" / TARGET / "nodes" / PARENT
    (parent / "Proof.lean").unlink()
    attest(root, "tutorial-and-swap", n=1)
    attest(root, "and-reassoc", n=2)
    merged = postmerge.apply_partial(
        parent,
        HOLES,
        partial_text=ASSEMBLY,
        pseudonym=PSEUDONYM,
        stamp=STAMP,
        witnesses=witnesses,
    )
    return root, merged


W_RIGHT, W_LEFT = witness_text("right"), witness_text("left", "⟨True, True, True, by simp⟩")


def test_children_are_born_with_the_carried_witnesses_and_ready(tmp_path: Path) -> None:
    """AC44: every hole carried — both children hold the carried text byte for byte, neither is
    a stub, and the derivation says ``ready`` with no cause, where a slot says ``blocked`` /
    ``witness-missing``."""
    root, merged = decomposed(tmp_path, {"right": W_RIGHT, "left": W_LEFT})
    nodes = root / "targets" / TARGET / "nodes"
    h1, h2 = merged.children
    # F07-T75: the carried text byte for byte, less its `-- hole:` line.
    assert (nodes / h1 / "Witness.lean").read_text(encoding="utf-8") == carried.as_witness(W_RIGHT)
    assert (nodes / h2 / "Witness.lean").read_text(encoding="utf-8") == carried.as_witness(W_LEFT)
    assert not graph.witness_is_stub(nodes / h1) and not graph.witness_is_stub(nodes / h2)
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[h1] == "ready" and tg.statuses[h2] == "ready"
    causes = graph.derive_causes(tg.nodes, tg.statuses)
    assert causes[h1] is None and causes[h2] is None
    assert merged.as_dict()["witnessed"] == [h1, h2]
    # Everything else about a child is what it is without a witness: statement, META, Context.
    plain_root, plain = decomposed(tmp_path / "plain", {})
    for child in merged.children:
        for name in ("Statement.lean", "META.yaml", "Context.lean"):
            ours = (nodes / child / name).read_bytes()
            assert ours == (plain_root / "targets" / TARGET / "nodes" / child / name).read_bytes()
    assert "witnessed" not in plain.as_dict()


def test_only_the_holes_that_carried_one_are_ready(tmp_path: Path) -> None:
    """AC44, mixed: the hole with a carried witness is ready; the other is the slot, blocked."""
    root, merged = decomposed(tmp_path, {"left": W_LEFT})
    nodes = root / "targets" / TARGET / "nodes"
    h1, h2 = merged.children
    assert graph.witness_is_stub(nodes / h1)
    assert (nodes / h2 / "Witness.lean").read_text(encoding="utf-8") == carried.as_witness(W_LEFT)
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[h1] == "blocked" and tg.statuses[h2] == "ready"
    assert graph.derive_causes(tg.nodes, tg.statuses)[h1] == graph.CAUSE_WITNESS_MISSING
    assert merged.as_dict()["witnessed"] == [h2]


def test_the_writer_run_twice_writes_nothing_the_second_time(tmp_path: Path) -> None:
    """AC44: a re-run of the post-merge job finds its children by their text (R22) and touches
    none of them, carried witnesses or not; even handed different text, it writes nothing."""
    root = copy_graph(tmp_path)
    parent = root / "targets" / TARGET / "nodes" / PARENT
    rel = f"attempts/{STAMP}-{PSEUDONYM}-partial.lean"
    (parent / "attempts").mkdir(exist_ok=True)
    (parent / rel).write_text(ASSEMBLY, encoding="utf-8")
    kwargs: dict[str, Any] = {
        "partial_text": ASSEMBLY,
        "pseudonym": PSEUDONYM,
        "stamp": STAMP,
        "assembly_path": rel,
    }
    first = postmerge.apply_partial(parent, HOLES, witnesses={"right": W_RIGHT}, **kwargs)
    after_first = snapshot(parent)
    second = postmerge.apply_partial(parent, HOLES, witnesses={"right": W_RIGHT}, **kwargs)
    assert second.children == () and "witnessed" not in second.as_dict()
    assert [h["reused_node"] for h in second.holes] == list(first.children)
    assert snapshot(parent) == after_first
    third = postmerge.apply_partial(
        parent, HOLES, witnesses={"right": W_LEFT, "left": W_LEFT}, **kwargs
    )
    assert third.children == () and snapshot(parent) == after_first


def test_a_hole_that_is_an_existing_node_is_not_touched(tmp_path: Path) -> None:
    """R23: a later route restating an earlier hole carries a witness for it; the node exists,
    so nothing of it is written (its witness goes in as a proposal, F08-R5). The new hole beside
    it is born with its own."""
    root, first = decomposed(tmp_path, {})
    nodes = root / "targets" / TARGET / "nodes"
    slot = (nodes / first.children[0] / "Witness.lean").read_bytes()
    third = hole("third", "∀ (p q r : Prop), (p ∧ q) ∧ r → p", local="p")
    second = postmerge.apply_partial(
        nodes / PARENT,
        (HOLES[0], third),
        partial_text=ASSEMBLY,
        pseudonym="carol",
        stamp="20260911T000000Z",
        witnesses={"right": W_RIGHT, "third": witness_text("third")},
    )
    assert second.children == (f"{PARENT}--h4",)
    assert (nodes / first.children[0] / "Witness.lean").read_bytes() == slot
    born = (nodes / f"{PARENT}--h4" / "Witness.lean").read_text()
    assert born == carried.as_witness(witness_text("third"))
    assert second.as_dict()["witnessed"] == [f"{PARENT}--h4"]


# --- the post-merge command: only what its own run checked is written -------------------------


def merged_with_witnesses(tmp_path: Path, files: dict[str, str]) -> Path:
    """A repo whose HEAD adds one assembly and ``files`` to the unproved root."""
    root, git, _base = git_repo(tmp_path)
    node = root / NODES / ROOT
    (node / "Proof.lean").unlink(missing_ok=True)
    git("add", "-A")
    git("commit", "-q", "-m", "the root, unproved")
    statement = (node / "Statement.lean").read_text(encoding="utf-8")
    head, _, _ = statement.partition(":= by\n  sorry")
    (node / "attempts").mkdir(exist_ok=True)
    (node / "attempts" / STAMP_FILE).write_text(head + ":= by\n" + BODY, encoding="utf-8")
    for name, text in files.items():
        (node / "attempts" / name).write_text(text, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "partial: and-swap-reassoc")
    return root


BODY = """  intro p q r h
  have right : r := sorry
  have left : q ∧ p := sorry
  exact ⟨right, left⟩
"""


def postmerge_argv(root: Path, out: Path) -> list[str]:
    return [
        "postmerge", "--graph", str(root), "--commit", "HEAD", "--pr", "9", "--target", TARGET,
        "--node", ROOT, "--review-kind", "pr-approval", "--reviewer", "rev", "--out", str(out),
        "--apply-partial", "--author", "login",
    ]  # fmt: skip


def test_the_post_merge_command_writes_the_witnesses_its_run_checked(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root = merged_with_witnesses(tmp_path, {f"{STEM}.1.witness": witness_text("left")})
    seam.fake = PerHole(witness=NODE_WITNESS, artifact=holes_report())
    code, out, err = run(capsys, *postmerge_argv(root, tmp_path / "o"))
    assert code == cli.EXIT_PASS, err
    assert out["partial"]["children"] == [f"{ROOT}--h1", f"{ROOT}--h2"]
    assert out["partial"]["witnessed"] == [f"{ROOT}--h2"]
    nodes = root / NODES
    born = (nodes / f"{ROOT}--h2" / "Witness.lean").read_text()
    assert born == carried.as_witness(witness_text("left"))
    assert graph.witness_is_stub(nodes / f"{ROOT}--h1")
    # The carried file stays where it was submitted: the record of what was carried (D-3).
    assert (nodes / ROOT / "attempts" / f"{STEM}.1.witness").read_text() == witness_text("left")
    meta = yaml.safe_load((nodes / f"{ROOT}--h2" / "META.yaml").read_text())
    assert meta["provenance"]["author"] == "login"


def test_the_post_merge_command_writes_nothing_when_a_carried_witness_fails(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """The backstop for a merge that should not have happened: the re-derived verdict fails at
    step 7, nothing is attested and no child is written."""
    root = merged_with_witnesses(tmp_path, {f"{STEM}.1.witness": witness_text("left")})
    seam.fake = PerHole(
        witness=NODE_WITNESS, artifact=holes_report(), by_decl={"and_swap_reassoc__h2": WRONG}
    )
    code, out, _err = run(capsys, *postmerge_argv(root, tmp_path / "o"))
    assert code == cli.EXIT_FAIL
    assert out["first_failing_step"] == 7 and out["diagnostic"]["code"] == "witness-type-mismatch"
    assert out["diagnostic"]["details"]["hole"] == "left"
    assert not (root / NODES / f"{ROOT}--h1").exists()
    assert not (root / NODES / f"{ROOT}--h2").exists()


def test_the_assembly_text_is_the_one_test_partial_builds(tmp_path: Path) -> None:
    """The two fixtures above stand on ``test_partial``'s assembly; keep them the same text."""
    ctx, _ = partial_context(tmp_path)
    assert assembly_for(ctx).endswith(BODY)


# --- F07-T53: what is hashed and written is the file's bytes --------------------------------------


def test_a_carried_witness_is_hashed_and_written_as_its_bytes(tmp_path: Path) -> None:
    """The service binds a submission to its precheck by the hash of the bundle's text
    (``hole-witness-unchecked``), and D-29 v3.24 says a hole is created with the witness that was
    checked. Python's text mode folds ``\\r\\n`` into ``\\n`` on reading, so a witness with
    Windows line ends was hashed by the gate as a text nobody sent: the service then refused the
    submission in words about an old pin, and the child would have been written with other
    bytes than the file on record. The gate reads a carried witness as its bytes."""
    text = witness_text("right").replace("\n", "\r\n")
    name = f"{STEM}.1.witness"
    ctx, _fake = carrying(tmp_path, {})
    (node_dir(ctx) / "attempts" / name).write_bytes(text.encode("utf-8"))
    ctx.changes.append(Change("A", f"targets/{TARGET}/nodes/{ROOT}/attempts/{name}"))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    (checked,) = ctx.data[carried.DATA_KEY]
    assert checked["sha256"] == schemas.content_hash(text.encode("utf-8"))
    staged = ctx.workdir / "holes" / "src" / "Nodes" / f"{ROOT}--h1" / "Witness.lean"
    assert staged.read_bytes() == carried.as_witness(text).encode("utf-8")  # F07-T75
    held = replace(verdict, data=ctx.data)
    assert cli.checked_witnesses(held, node_dir(ctx)) == {"right": text}
    nodes = node_dir(ctx).parent
    postmerge.apply_partial(
        node_dir(ctx),
        [art_hole(h) for h in ctx.data[ARTIFACT_KEY]["holes"]],
        partial_text=(node_dir(ctx) / "attempts" / STAMP_FILE).read_text(encoding="utf-8"),
        pseudonym=PSEUDONYM,
        stamp=STAMP,
        assembly_path=f"attempts/{STAMP_FILE}",
        witnesses={"right": text},
    )
    born = (nodes / f"{ROOT}--h1" / "Witness.lean").read_bytes()
    assert born == carried.as_witness(text).encode("utf-8")
