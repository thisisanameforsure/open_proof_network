"""F08-T10: a revision reaches the statements that depend on it (R15, AC21; Q22; D-8 v3.18).

Found live 2026-09-18 by an outside contributor working ``erdos-69--h2-v2--h1-v2``, and worse
than reported. ``opn-gate revise`` marks the old node ``superseded`` and its dependents ``stale``
and stops (F08-R9 said "for the curator to adjust"; nothing could). So the parent of a revised
hole could never close, for four independent reasons: its ``META.yaml`` deps still named the
superseded child, which has no proof and never will (``dep-unproved``); its ``Context.lean``
carried the old child's signature (``context-signature-mismatch``); its ``stale`` record outranks
a proof for ever, ``node-status/v1`` having no value that clears one; and no pull request in any
mode may touch either file. D-8 and D-18 both said dependents are "re-derived"; no code did.

The owner's ruling (2026-09-18), against his four principles — published state is actual state,
fully trackable, easily reversed, hard to tamper with: **derive, never rewrite.** ``META.yaml``
stays as written. Wherever deps are read, a superseded dep is read as the node at the end of its
revision chain; ``Context.lean``, a generated file, is regenerated to match, in both directions.
``stale`` lifts on the gate's evidence, never on a record or a date. Reverting the one revision
commit restores every dependent exactly, which the last test here holds byte for byte.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

import pytest
import samples
import yaml
from harness import TARGET, copy_graph
from test_finding_b_revise_v2 import AUTHOR, DATE, NEW_STATEMENT, v1_request_doc, write_doc

from opn_gate import context, curator, graph, layout, postmerge, products, schemas
from opn_gate.steps import deps as depstep
from opn_gate.steps import stage as staging

ROOT = "and-swap-reassoc"
DEP = "and-reassoc"
DEP_V2 = DEP + "-v2"
DEP_V3 = DEP + "-v3"
OTHER = "tutorial-and-swap"
COMMIT_TIME = "2026-09-19T12:00:00Z"
V3_STATEMENT = NEW_STATEMENT.replace("«and-reassoc-v2»", "«and-reassoc-v3»")
#: A revision whose *signature* differs, as a real correction's does (the live ones changed a
#: domain): the borrowed ``NEW_STATEMENT`` restates the original's type under a new comment, so
#: a dependent's context would still match it and nothing would need regenerating.
CHANGED_STATEMENT = NEW_STATEMENT.replace(
    "(p ∧ q) ∧ r → p ∧ (q ∧ r)", "p → (p ∧ q) ∧ r → p ∧ (q ∧ r)"
)


def nodes_dir(root: Path) -> Path:
    return layout.graph_nodes_dir(root, TARGET)


def statement_hash(root: Path, node_id: str) -> str:
    return schemas.content_hash((nodes_dir(root) / node_id / "Statement.lean").read_bytes())


def attest(root: Path, node_id: str, n: int, *, graph_commit: str = "1" * 40) -> None:
    doc = samples.attestation(
        node_id=node_id,
        statement_hash=statement_hash(root, node_id),
        merge_commit="4" * 40,
        graph_commit=graph_commit,
        runner="hosted",
    )
    att = root / "attestations"
    att.mkdir(exist_ok=True)
    (att / f"{n:06d}.json").write_bytes(schemas.canonical_json(doc))


def prove(root: Path, node_id: str, n: int, *, graph_commit: str = "1" * 40) -> None:
    """A merged proof of ``node_id``: the statement with its body replaced, and its attestation."""
    node = nodes_dir(root) / node_id
    statement = (node / "Statement.lean").read_text(encoding="utf-8")
    (node / "Proof.lean").write_text(statement.replace("sorry", "trivial"), encoding="utf-8")
    attest(root, node_id, n, graph_commit=graph_commit)


def unprove(root: Path, node_id: str) -> None:
    (nodes_dir(root) / node_id / "Proof.lean").unlink()


def revise(root: Path, node_id: str = DEP, statement: str = NEW_STATEMENT) -> curator.Revision:
    request = write_doc(root, node_id, v1_request_doc(node_id))
    return curator.revise(root, TARGET, node_id, statement, request, author=AUTHOR, date=DATE)


def base(tmp_path: Path, *, root_proved: bool = False) -> Path:
    """The fixture with both deps proved, and the root proved or (the live shape) not."""
    root = copy_graph(tmp_path, publish=True)
    attest(root, DEP, 1)
    attest(root, OTHER, 2)
    if root_proved:
        attest(root, ROOT, 3)
    else:
        unprove(root, ROOT)
    return root


def statuses(root: Path) -> dict[str, str]:
    return graph.load_target(root, TARGET).statuses


def git(root: Path, *args: str) -> str:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.org",
           "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", "HOME": str(root)}  # fmt: skip
    done = subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True, env=env
    )
    return done.stdout.strip()


def commit_all(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


# -- deps are read through the revision, and nothing on disk is rewritten -------------------------


def test_a_dependent_reads_its_dep_through_the_revision(tmp_path: Path) -> None:
    root = base(tmp_path)
    meta_before = (nodes_dir(root) / ROOT / "META.yaml").read_bytes()
    assert statuses(root)[ROOT] == "ready", "guard: both deps proved, the root open"
    revise(root)

    tg = graph.load_target(root, TARGET)
    assert tg.nodes[ROOT].deps == (OTHER, DEP_V2)
    assert tg.nodes[ROOT].declared_deps == (OTHER, DEP)
    assert (nodes_dir(root) / ROOT / "META.yaml").read_bytes() == meta_before
    assert tg.statuses[DEP] == "superseded"


def test_the_parent_of_a_revised_dep_waits_on_the_revision_not_on_a_stale_mark(
    tmp_path: Path,
) -> None:
    """The live ``erdos-69`` shape: the parent has no proof, so there is nothing to be stale."""
    root = base(tmp_path)
    revise(root)
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[ROOT] == "blocked"
    assert graph.blocked_because(tg.nodes[ROOT], lambda n: tg.statuses[n]) == (True, None)


def test_proving_the_revision_opens_the_parent(tmp_path: Path) -> None:
    """What could never happen: work on the corrected hole closes nothing. Now it opens it."""
    root = base(tmp_path)
    revise(root)
    prove(root, DEP_V2, 9)
    assert statuses(root)[ROOT] == "ready"


def test_a_chain_of_revisions_is_followed_to_its_end(tmp_path: Path) -> None:
    root = base(tmp_path)
    revise(root)
    revise(root, DEP_V2, V3_STATEMENT)
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[ROOT].deps == (OTHER, DEP_V3)
    assert graph.current_id(nodes_dir(root), DEP) == DEP_V3


def test_revising_a_revision_finds_the_dependents_of_the_original(tmp_path: Path) -> None:
    """``dependents_of`` reads deps the same way, or a second revision would miss the parent."""
    root = base(tmp_path, root_proved=True)
    revise(root)
    assert ROOT in curator.dependents_of(nodes_dir(root), DEP_V2)


# -- the guard: a revision is followed only when its own record names what it supersedes -----------


def test_a_successor_that_names_another_node_is_not_followed(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = base(tmp_path)
    revise(root)
    meta_path = nodes_dir(root) / DEP_V2 / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta["supersedes"] = OTHER  # the record on DEP says DEP_V2 replaced it; DEP_V2 disagrees
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="opn_gate.graph"):
        assert graph.current_id(nodes_dir(root), DEP) == DEP
    assert DEP_V2 in caplog.text and "supersedes" in caplog.text
    assert graph.load_target(root, TARGET).nodes[ROOT].deps == (OTHER, DEP)


def test_a_successor_that_is_no_node_or_a_loop_is_not_followed(tmp_path: Path) -> None:
    root = base(tmp_path)
    doc = curator.node_status_doc(
        "superseded", "superseded by a node that does not exist", author=AUTHOR, date=DATE,
        reference="no-such-node",
    )  # fmt: skip
    curator.write_record(nodes_dir(root) / DEP, doc, author=AUTHOR, date=DATE)
    assert graph.current_id(nodes_dir(root), DEP) == DEP
    loop = curator.node_status_doc(
        "superseded", "superseded by itself", author=AUTHOR, date="2026-09-11T00:00:00Z",
        reference=DEP,
    )  # fmt: skip
    curator.write_record(nodes_dir(root) / DEP, loop, author=AUTHOR, date="2026-09-11T00:00:00Z")
    assert graph.current_id(nodes_dir(root), DEP) == DEP
    assert products.generate(root, rendered_from=None, commit_time=COMMIT_TIME).files


# -- every reader agrees --------------------------------------------------------------------------


def test_the_published_graph_carries_the_effective_deps(tmp_path: Path) -> None:
    root = base(tmp_path)
    revise(root)
    built = products.generate(root, rendered_from=None, commit_time=COMMIT_TIME)
    doc = json.loads(built.files[Path(f"targets/{TARGET}/graph.json")])
    rows = {n["node_id"]: n for n in doc["nodes"]}
    assert rows[ROOT]["deps"] == [OTHER, DEP_V2]
    assert rows[ROOT]["status"] == "blocked" and rows[DEP]["status"] == "superseded"


def test_context_json_names_the_effective_deps_and_keeps_the_record(tmp_path: Path) -> None:
    """Both builders of ``CONTEXT.json`` (the gate over a tree, the service over the host) take
    their states from ``graph.json``, so its effective deps are what each of them reports; the
    recorded deps stay readable in ``meta``."""
    root = base(tmp_path)
    revise(root)
    built = products.generate(root, rendered_from=None, commit_time=COMMIT_TIME)
    graph_doc = json.loads(built.files[Path(f"targets/{TARGET}/graph.json")])
    states = context.graph_states(graph_doc)
    doc = context.build(context.DiskReader(root), TARGET, ROOT, states=states, rendered_from=None)
    assert [d["node_id"] for d in doc["deps"]] == [OTHER, DEP_V2]
    assert doc["deps"][1]["status"] == "ready"  # the revision: authored, unproved, open


def test_staging_a_parent_stages_the_revision(tmp_path: Path) -> None:
    root = base(tmp_path)
    revise(root)
    prove(root, DEP_V2, 9)
    (nodes_dir(root) / ROOT / "Proof.lean").write_text("-- a proof\n", encoding="utf-8")
    node = layout.load_node(nodes_dir(root) / ROOT, TARGET)
    assert isinstance(node, layout.Node)
    staged = staging.stage(node, tmp_path / "work")
    assert staged.problems == ()
    assert DEP_V2 in staged.order and DEP not in staged.order
    generated = (tmp_path / "work" / "src" / "Nodes" / ROOT / "Context.lean").read_text()
    assert f"«{DEP_V2}»" in generated and f"«{DEP}»" not in generated


def test_the_context_pass_regenerates_a_dependents_context_and_is_idempotent(
    tmp_path: Path,
) -> None:
    root = base(tmp_path)
    revise(root, statement=CHANGED_STATEMENT)
    node = layout.load_node(nodes_dir(root) / ROOT, TARGET)
    assert isinstance(node, layout.Node)
    declared = list(graph.effective_deps(nodes_dir(root), node.meta.get("deps")))
    stale_context = depstep.check_context(node, declared)
    assert stale_context is not None and stale_context.diagnostic is not None
    assert stale_context.diagnostic.code == "context-signature-mismatch", "guard: the defect"

    changed = postmerge.refresh_contexts(nodes_dir(root))
    assert [p.parent.name for p in changed] == [ROOT]
    assert depstep.check_context(node, declared) is None
    assert postmerge.refresh_contexts(nodes_dir(root)) == []


# -- stale lifts on evidence, never on a record or a date ------------------------------------------


def test_revise_marks_a_proved_dependent_stale_and_an_unproved_one_not(tmp_path: Path) -> None:
    proved = base(tmp_path / "a", root_proved=True)
    assert ROOT in revise(proved).dependents and statuses(proved)[ROOT] == "stale"
    unproved = base(tmp_path / "b")
    revise(unproved)
    assert not (nodes_dir(unproved) / ROOT / "status").exists()


def test_a_stale_record_on_a_node_with_no_proof_marks_nothing(tmp_path: Path) -> None:
    """The seven live parents already carry one: it must stop deciding their status."""
    root = base(tmp_path)
    revise(root)
    doc = curator.node_status_doc(
        "stale", f"depends on {DEP}, superseded by {DEP_V2}", author=AUTHOR, date=DATE,
        reference=DEP,
    )  # fmt: skip
    curator.write_record(nodes_dir(root) / ROOT, doc, author=AUTHOR, date=DATE)
    assert statuses(root)[ROOT] == "blocked"
    prove(root, DEP_V2, 9)
    assert statuses(root)[ROOT] == "ready"


def test_stale_on_a_proved_node_lifts_only_on_a_run_that_included_the_revision(
    tmp_path: Path,
) -> None:
    root = base(tmp_path, root_proved=True)
    git(root, "init", "-q", "-b", "main")
    before = commit_all(root, "base")
    revise(root)
    prove(root, DEP_V2, 9)
    marked = commit_all(root, "the revision, marking the root stale")
    assert statuses(root)[ROOT] == "stale", "no evidence yet: the old attestation predates it"

    attest(root, ROOT, 10, graph_commit=before)  # a run from before the revision proves nothing
    assert statuses(root)[ROOT] == "stale"
    attest(root, ROOT, 11, graph_commit="9" * 40)  # a commit the graph has never seen
    assert statuses(root)[ROOT] == "stale"
    attest(root, ROOT, 12, graph_commit=marked)  # the re-run D-18 asks for
    assert statuses(root)[ROOT] == "proved"


def test_without_a_history_to_ask_stale_stays(tmp_path: Path) -> None:
    """No git, no evidence: the conservative answer, and what every non-git fixture gets."""
    root = base(tmp_path, root_proved=True)
    revise(root)
    attest(root, ROOT, 12, graph_commit="1" * 40)
    assert statuses(root)[ROOT] == "stale"


def test_a_backdated_record_lifts_nothing(tmp_path: Path) -> None:
    """Why the rule is ancestry: a status record's date is whatever its author typed."""
    root = base(tmp_path, root_proved=True)
    git(root, "init", "-q", "-b", "main")
    commit_all(root, "base")
    request = write_doc(root, DEP, v1_request_doc(DEP))
    curator.revise(
        root, TARGET, DEP, NEW_STATEMENT, request, author=AUTHOR, date="1999-01-01T00:00:00Z"
    )
    commit_all(root, "a revision dated in the last century")
    assert statuses(root)[ROOT] == "stale"


# -- reversal is a property, not a hope ------------------------------------------------------------


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git/" not in p.as_posix() and not p.as_posix().endswith("/.git")
    }


def test_reverting_the_revision_restores_every_dependent_byte_for_byte(tmp_path: Path) -> None:
    """The property, on the tree the graph actually has: every ``Context.lean`` there was
    written by the generator (intake, the scaffold, the post-merge job), so what the pass writes
    back after a revert is the very bytes that were there."""
    root = base(tmp_path, root_proved=True)
    postmerge.regenerate_context(nodes_dir(root) / ROOT, nodes_dir(root))  # as the graph's are
    git(root, "init", "-q", "-b", "main")
    commit_all(root, "base")
    tree_before, statuses_before = snapshot(root), statuses(root)
    deps_before = {n: f.deps for n, f in graph.load_target(root, TARGET).nodes.items()}

    revise(root, statement=CHANGED_STATEMENT)
    revision = commit_all(root, "curator: revise and-reassoc")
    postmerge.refresh_contexts(nodes_dir(root))
    commit_all(root, "gate: regenerate contexts")
    assert statuses(root) != statuses_before, "guard: the revision changed something"

    git(root, "revert", "--no-edit", revision)
    postmerge.refresh_contexts(nodes_dir(root))  # the same pure pass, run by the same job
    assert snapshot(root) == tree_before
    assert statuses(root) == statuses_before
    assert {n: f.deps for n, f in graph.load_target(root, TARGET).nodes.items()} == deps_before


def test_a_hand_seeded_context_comes_back_equivalent_not_identical(tmp_path: Path) -> None:
    """The fixture's own root context was typed by hand, under a different comment. After a
    revert the pass regenerates it: step 8 passes against the original dep again, and the bytes
    are the generator's. Said here so nobody reads "byte for byte" as covering a file the
    generator never wrote."""
    root = base(tmp_path, root_proved=True)
    seeded = (nodes_dir(root) / ROOT / "Context.lean").read_bytes()
    git(root, "init", "-q", "-b", "main")
    commit_all(root, "base")
    revise(root, statement=CHANGED_STATEMENT)
    revision = commit_all(root, "curator: revise and-reassoc")
    postmerge.refresh_contexts(nodes_dir(root))
    commit_all(root, "gate: regenerate contexts")
    git(root, "revert", "--no-edit", revision)
    postmerge.refresh_contexts(nodes_dir(root))

    node = layout.load_node(nodes_dir(root) / ROOT, TARGET)
    assert isinstance(node, layout.Node)
    assert depstep.check_context(node, [OTHER, DEP]) is None
    assert (nodes_dir(root) / ROOT / "Context.lean").read_bytes() != seeded
