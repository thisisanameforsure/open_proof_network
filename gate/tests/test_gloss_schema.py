"""F20-T2 / AC1: a gloss of every kind of Lean file (R1, R3; D-3 v3.30).

A gloss is prose saying what one Lean file says — a statement, a witness, a relation or a
definition module — naming the SHA-256 of the exact text it describes. It is accepted on a node of
any status, by the path check alone, in the explainer family of modes: nothing is built and no
proof is asked for. A gloss whose ``lean_hash`` is not the file as the tree holds it is refused
``gloss-subject-mismatch``, naming the current hash.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in

from opn_gate import modes, schemas
from opn_gate.paths import Change

TARGET = "euclid-primes"
ROOT = "and-reassoc"  # take_in's root
OPEN = "open-node"  # a node with no proof at all
HOLE = "and-reassoc--h1"
VARIANT = "and-reassoc-variant"
MODULE = "Primes.lean"
DEFS = {MODULE: "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p\n"}
STUB_WITNESS = "theorem witness : True := sorry -- the slot a proposer fills\n"
RELATION = "-- relation: resolves\ntheorem relation : True := trivial\n"


def nodes(root: Path) -> Path:
    return root / "targets" / TARGET / "nodes"


@pytest.fixture
def graph(tmp_path: Path) -> Path:
    """A curated target with a definition module, its root, an open node with no proof, a hole
    with a stub witness and a variant with a relation."""
    root = copy_graph(tmp_path)
    take_in(root, TARGET, defs=DEFS)
    for name, extra in ((OPEN, None), (HOLE, STUB_WITNESS), (VARIANT, None)):
        shutil.copytree(nodes(root) / ROOT, nodes(root) / name)
        (nodes(root) / name / "Proof.lean").unlink(missing_ok=True)
        if extra is not None:
            (nodes(root) / name / "Witness.lean").write_text(extra, encoding="utf-8")
    (nodes(root) / VARIANT / "Relation.lean").write_text(RELATION, encoding="utf-8")
    return root


def lean_hash(path: Path) -> str:
    return str(schemas.content_hash(path.read_bytes()))


def gloss_text(
    *,
    kind: str,
    node: str | None,
    module: str | None,
    lean: str,
    author: str | None = "alice",
    drafter: dict[str, Any] | None = None,
    supersedes: str | None = None,
    body: str = "The statement says that every conjunction can be reassociated.\n",
    **overrides: Any,
) -> str:
    doc: dict[str, Any] = {
        "schema": "gloss/v1",
        "target": TARGET,
        "subject": {"kind": kind, "node": node, "module": module, "lean_hash": lean},
        "supersedes": supersedes,
        "author": author,
        "drafter": drafter,
        "date": "2026-10-04",
        "licence": "CC-BY-4.0",
        **overrides,
    }
    front = str(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    return "---\n" + front + "---\n" + body


def file_gloss(root: Path, text: str, *, node: str | None) -> Change:
    """Write the gloss where a pull request would add it, named by its own hash."""
    digest = schemas.content_hash(text.encode("utf-8"))
    parent = nodes(root) / node if node is not None else root / "targets" / TARGET
    (parent / "gloss").mkdir(parents=True, exist_ok=True)
    (parent / "gloss" / f"{digest}.md").write_text(text, encoding="utf-8")
    return Change("A", (parent / "gloss" / f"{digest}.md").relative_to(root).as_posix())


def verdict(root: Path, change: Change) -> tuple[str | None, list[str], modes.Classification]:
    classification = modes.classify([change], author="anyone")
    if not classification.ok:
        return None, [d.code for d in classification.problems], classification
    return classification.mode, [d.code for d in modes.check(root, classification)], classification


def node_gloss(root: Path, kind: str, node: str, filename: str, **kw: Any) -> Change:
    kw.setdefault("lean", lean_hash(nodes(root) / node / filename))
    return file_gloss(root, gloss_text(kind=kind, node=node, module=None, **kw), node=node)


def test_every_lean_file_kind_takes_a_gloss(graph: Path) -> None:
    """AC1: glosses of an open node's statement, a hole's witness, a variant's relation and a
    definition module, each with the right ``lean_hash``, pass in a mode that builds nothing and
    asks for no review; one with a stale hash is refused ``gloss-subject-mismatch`` naming the
    current hash; and the open node has no proof, which is not asked for."""
    root = graph
    assert not (nodes(root) / OPEN / "Proof.lean").exists()
    changes = [
        node_gloss(root, "statement", OPEN, "Statement.lean"),
        node_gloss(root, "witness", HOLE, "Witness.lean"),
        node_gloss(root, "relation", VARIANT, "Relation.lean"),
    ]
    defs_file = root / "targets" / TARGET / "defs" / MODULE
    changes.append(
        file_gloss(
            root,
            gloss_text(kind="definition", node=None, module=MODULE, lean=lean_hash(defs_file)),
            node=None,
        )
    )
    for change in changes:
        mode, codes, classification = verdict(root, change)
        assert mode == "explainer", (change.path, codes)
        assert codes == [], (change.path, codes)
        assert not classification.needs_gate and not classification.needs_review
        assert not classification.needs_admission

    stale = node_gloss(root, "statement", OPEN, "Statement.lean", lean="0" * 64)
    mode, codes, _ = verdict(root, stale)
    assert mode == "explainer" and codes == ["gloss-subject-mismatch"]
    classification = modes.classify([stale], author="anyone")
    [problem] = modes.check(root, classification)
    current = lean_hash(nodes(root) / OPEN / "Statement.lean")
    assert problem.details["current"] == current
    assert current in problem.message


def test_a_gloss_and_its_node_may_ride_one_pull_request_only_with_its_own_family(
    graph: Path,
) -> None:
    """A gloss with a proof is two kinds of pull request: the mode family refuses the mixture."""
    root = graph
    gloss = node_gloss(root, "statement", OPEN, "Statement.lean")
    proof = Change("A", f"targets/{TARGET}/nodes/{OPEN}/Proof.lean")
    classification = modes.classify([gloss, proof], author="anyone")
    assert classification.mode is None
    assert [d.code for d in classification.problems] == ["mode-mixed"]


@pytest.mark.parametrize(
    ("author", "drafter"),
    [
        (None, None),
        (
            "alice",
            {"name": "opn-drafter", "model": "m", "model_version": "1", "input_commit": "a" * 40},
        ),
    ],
)
def test_exactly_one_of_author_and_drafter(
    graph: Path, author: str | None, drafter: dict[str, Any] | None
) -> None:
    """R1: a gloss is a person's or a draft, never both and never neither."""
    change = node_gloss(graph, "statement", OPEN, "Statement.lean", author=author, drafter=drafter)
    assert verdict(graph, change)[1] == ["gloss-invalid"]


def test_a_draft_passes(graph: Path) -> None:
    drafter = {"name": "opn-drafter", "model": "m", "model_version": "1", "input_commit": "a" * 40}
    change = node_gloss(graph, "witness", HOLE, "Witness.lean", author=None, drafter=drafter)
    assert verdict(graph, change)[1] == []


def test_a_gloss_without_front_matter_or_with_a_bad_schema_is_refused(graph: Path) -> None:
    bare = file_gloss(graph, "Just prose, no front matter.\n", node=OPEN)
    assert verdict(graph, bare)[1] == ["gloss-invalid"]
    lean = lean_hash(nodes(graph) / OPEN / "Statement.lean")
    extra = file_gloss(
        graph,
        gloss_text(kind="statement", node=OPEN, module=None, lean=lean, extra_field=1),
        node=OPEN,
    )
    assert verdict(graph, extra)[1] == ["gloss-invalid"]


def test_a_gloss_names_the_node_and_target_it_sits_under(graph: Path) -> None:
    """A gloss under one node naming another, or a definition gloss filed under a node, or a
    node's gloss filed under the target, is refused: the subject is where the file is."""
    root = graph
    lean = lean_hash(nodes(root) / ROOT / "Statement.lean")
    elsewhere = file_gloss(
        root, gloss_text(kind="statement", node=ROOT, module=None, lean=lean), node=OPEN
    )
    assert verdict(root, elsewhere)[1] == ["gloss-invalid"]
    wrong_target = file_gloss(
        root,
        gloss_text(kind="statement", node=OPEN, module=None, lean=lean, target="other"),
        node=OPEN,
    )
    assert verdict(root, wrong_target)[1] == ["gloss-invalid"]
    defs_file = root / "targets" / TARGET / "defs" / MODULE
    definition_under_node = file_gloss(
        root,
        gloss_text(kind="definition", node=None, module=MODULE, lean=lean_hash(defs_file)),
        node=OPEN,
    )
    assert verdict(root, definition_under_node)[1] == ["gloss-invalid"]
    statement_under_target = file_gloss(
        root, gloss_text(kind="statement", node=OPEN, module=None, lean=lean), node=None
    )
    assert verdict(root, statement_under_target)[1] == ["gloss-invalid"]


def test_a_gloss_of_a_file_that_is_not_there_is_refused(graph: Path) -> None:
    """A relation gloss on a node with no Relation.lean, and a module that is not in defs/."""
    root = graph
    absent = file_gloss(
        root, gloss_text(kind="relation", node=OPEN, module=None, lean="1" * 64), node=OPEN
    )
    assert verdict(root, absent)[1] == ["gloss-subject-unknown"]
    module = file_gloss(
        root,
        gloss_text(kind="definition", node=None, module="Nope.lean", lean="1" * 64),
        node=None,
    )
    assert verdict(root, module)[1] == ["gloss-subject-unknown"]


def test_a_gloss_is_named_for_its_content_and_is_append_only(graph: Path) -> None:
    root = graph
    change = node_gloss(root, "statement", OPEN, "Statement.lean")
    misnamed = Change("A", change.path.rsplit("/", 1)[0] + "/" + "a" * 64 + ".md")
    shutil.copy(root / change.path, root / misnamed.path)
    assert verdict(root, misnamed)[1] == ["content-hash-name"]
    for status in ("M", "D"):
        classification = modes.classify([Change(status, change.path)], author="anyone")
        assert classification.mode is None
        assert [d.code for d in classification.problems] == ["path-forbidden"]
