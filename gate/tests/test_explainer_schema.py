"""F20-T3, T5 / AC3, AC4: explainer/v1 and its anchors (R2, R4, R5; D-3 v3.30).

An explainer may now carry front matter (``explainer/v1``) naming the merged proof artifact it
describes — the node's ``Proof.lean``, an alternate or a merged partial assembly — and its
sections may name the outline steps (F19's ``outline/v1``) they describe, at the end of a level-2
heading: ``## The bound {steps: s3 s4.1}`` (F20-Q2). The gate checks the names against the
committed outline, reading files and running no Lean: a proof that is not a merged artifact of
the node is ``explainer-proof-unknown``, and a step absent from its outline, or any step where
the proof has no outline, is ``explainer-step-unknown``. An explainer filed before F20 carries no
such front matter and stays valid, unanchored. A backticked Lean name in a section that none of
its steps' constants mention is the warning ``explainer-name-unanchored`` — never a refusal.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in

from opn_gate import config, explainers, modes, schemas
from opn_gate.paths import Change

TARGET = "euclid-primes"
NODE = "and-reassoc"  # take_in's root, carrying the fixture's Proof.lean
OPEN = "open-node"  # no Proof.lean; a merged partial assembly under attempts/
ALTERNATE = "attempts/2026-10-01T00-00-00Z-bob-alternate.lean"
PARTIAL = "attempts/2026-10-01T00-00-00Z-carol.lean"
LEGACY = (
    "---\nauthor: someone\nmodel: claude-fable-5-1\ndate: 2026-09-16\n---\n"
    "Reassociate the conjunction: both halves are already in hand.\n"
)


def nodes(root: Path) -> Path:
    return root / "targets" / TARGET / "nodes"


def text_of(text: str) -> dict[str, Any]:
    return {"text": text, "printed": "reliable", "truncated": False}


def step(
    step_id: str,
    *,
    mathlib: tuple[str, ...] = (),
    defs: tuple[str, ...] = (),
    children: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    return {
        "id": step_id,
        "kind": "have",
        "name": step_id,
        "claim": text_of("True"),
        "goal": None,
        "span": {"start_line": 1, "end_line": 2},
        "uses": {
            "nodes": [],
            "defs": list(defs),
            "mathlib": [{"name": n, "doc": None, "tags": []} for n in mathlib],
        },
        "closed_by": {"kind": "automation", "tactics": ["simp"]},
        "child_node": None,
        "children": list(children),
    }


def write_outline(root: Path, node: str, rel: str, steps: list[dict[str, Any]]) -> str:
    """The outline product F19 commits for one merged artifact, at its hash."""
    artifact = nodes(root) / node / rel
    digest = schemas.content_hash(artifact.read_bytes())
    doc = {
        "schema": "outline/v1",
        "target": TARGET,
        "node": node,
        "artifact": {"path": rel, "hash": digest, "kind": "proof"},
        "gate": "9" * 40,
        "steps": steps,
    }
    assert schemas.violations(doc, "outline/v1") == []
    out = root / "targets" / TARGET / "outlines" / f"{digest}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(schemas.canonical_json(doc))
    return digest


@pytest.fixture
def graph(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """A proved node with an outline of its Proof.lean and an alternate without one, and an open
    node with a merged partial assembly. Returns the root and the artifact hashes by name.

    The child step is ``s2.c1``, not ``s2.1``: ``outline/v1``'s id pattern requires each dotted
    component to open with a letter, though its own description gives ``s3.1`` (reported with
    F20-T3). The anchor check compares ids as strings, whatever their shape."""
    root = copy_graph(tmp_path)
    take_in(root, TARGET)
    node = nodes(root) / NODE
    (node / ALTERNATE).write_text(
        (node / "Proof.lean").read_text(encoding="utf-8") + "\n-- another way\n", encoding="utf-8"
    )
    shutil.copytree(node, nodes(root) / OPEN)
    (nodes(root) / OPEN / "Proof.lean").unlink()
    (nodes(root) / OPEN / ALTERNATE).unlink()
    (nodes(root) / OPEN / PARTIAL).write_text("-- a partial assembly\n", encoding="utf-8")
    proof = write_outline(
        root,
        NODE,
        "Proof.lean",
        [
            step("s1"),
            step("s2", mathlib=("Nat.Prime.two_le",), children=(step("s2.c1", defs=("Opn.f",)),)),
        ],
    )
    partial = write_outline(root, OPEN, PARTIAL, [step("h1")])
    alternate = schemas.content_hash((node / ALTERNATE).read_bytes())
    return root, {"proof": proof, "alternate": alternate, "partial": partial}


def explainer_text(
    proof: str,
    body: str,
    *,
    node: str = NODE,
    author: str | None = "alice",
    drafter: dict[str, Any] | None = None,
    supersedes: str | None = None,
    **overrides: Any,
) -> str:
    doc: dict[str, Any] = {
        "schema": "explainer/v1",
        "target": TARGET,
        "node": node,
        "proof": proof,
        "supersedes": supersedes,
        "author": author,
        "drafter": drafter,
        "date": "2026-10-04",
        "licence": "CC-BY-4.0",
        **overrides,
    }
    front = str(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    return "---\n" + front + "---\n" + body


def file_explainer(root: Path, text: str, node: str = NODE) -> Change:
    digest = schemas.content_hash(text.encode("utf-8"))
    directory = nodes(root) / node / "explainer"
    directory.mkdir(exist_ok=True)
    (directory / f"{digest}.md").write_text(text, encoding="utf-8")
    return Change("A", (directory / f"{digest}.md").relative_to(root).as_posix())


def check(root: Path, change: Change) -> list[str]:
    classification = modes.classify([change], author="anyone")
    assert classification.mode == "explainer", classification.as_dict()
    return [d.code for d in modes.check(root, classification)]


def warnings(root: Path, change: Change) -> list[Any]:
    classification = modes.classify([change], author="anyone")
    return modes.warnings(root, classification)


ANCHORED = (
    "## The idea\nReassociate.\n\n"
    "## The first half {steps: s1}\nIt is trivial.\n\n"
    "## The second half {steps: s2 s2.c1}\nUses `Nat.Prime.two_le`.\n"
)


def test_anchors_are_checked_against_the_outline(graph: tuple[Path, dict[str, str]]) -> None:
    """AC3: explainers naming a merged proof with known steps, an unknown step, an unknown proof,
    and steps on a proof with no outline, and an explainer filed before F20: pass,
    explainer-step-unknown, explainer-proof-unknown, explainer-step-unknown, pass."""
    root, h = graph
    known = file_explainer(root, explainer_text(h["proof"], ANCHORED))
    unknown_step = file_explainer(
        root, explainer_text(h["proof"], "## Intro\nx\n\n## Then {steps: s1 s9}\ny\n")
    )
    unknown_proof = file_explainer(root, explainer_text("f" * 64, "## Intro\nx\n"))
    no_outline = file_explainer(
        root, explainer_text(h["alternate"], "## Intro\nx\n\n## Then {steps: s1}\ny\n")
    )
    legacy = file_explainer(root, LEGACY)
    assert check(root, known) == []
    assert check(root, unknown_step) == ["explainer-step-unknown"]
    assert check(root, unknown_proof) == ["explainer-proof-unknown"]
    assert check(root, no_outline) == ["explainer-step-unknown"]
    assert check(root, legacy) == []


def test_an_alternate_without_anchors_and_a_partial_assembly_take_explainers(
    graph: tuple[Path, dict[str, str]],
) -> None:
    """R2: an alternate is a merged artifact, unanchored text on it passes; a merged partial
    assembly takes an explainer though its node has no Proof.lean (F20 §3)."""
    root, h = graph
    assert check(root, file_explainer(root, explainer_text(h["alternate"], "## Intro\nx\n"))) == []
    partial = file_explainer(
        root,
        explainer_text(h["partial"], "## Intro\nx\n\n## The hole {steps: h1}\ny\n", node=OPEN),
        node=OPEN,
    )
    assert check(root, partial) == []
    # The node's own artifacts only: the proof of another node is unknown here.
    elsewhere = file_explainer(root, explainer_text(h["proof"], "## Intro\nx\n", node=OPEN), OPEN)
    assert check(root, elsewhere) == ["explainer-proof-unknown"]
    # A legacy explainer on a node with no Proof.lean is still an annex misfiled (D-3).
    assert check(root, file_explainer(root, LEGACY, OPEN)) == ["explainer-unproved"]


@pytest.mark.parametrize(
    "body",
    [
        "Text before any section.\n\n## Intro\nx\n",  # sections under level-2 headings (R2)
        "",  # no section at all
        "# A level-one heading\nx\n",
    ],
)
def test_the_body_is_sections(graph: tuple[Path, dict[str, str]], body: str) -> None:
    root, h = graph
    assert check(root, file_explainer(root, explainer_text(h["proof"], body))) == [
        "explainer-invalid"
    ]


def test_front_matter_is_held_to_the_schema(graph: tuple[Path, dict[str, str]]) -> None:
    """Exactly one of author and drafter; the node and target are where the file sits; an
    unknown schema id is refused rather than read as a pre-F20 explainer. Restated by F21-R2:
    an added draft is refused ``draft-not-accepted`` even when the service opens it, and a merged
    one still reads as a version."""
    root, h = graph
    neither = file_explainer(root, explainer_text(h["proof"], "## I\nx\n", author=None))
    assert check(root, neither) == ["explainer-invalid"]
    elsewhere = file_explainer(root, explainer_text(h["proof"], "## I\nx\n", target="other"))
    assert check(root, elsewhere) == ["explainer-invalid"]
    other_node = file_explainer(root, explainer_text(h["proof"], "## I\nx\n", node=OPEN))
    assert check(root, other_node) == ["explainer-invalid"]
    wrong_schema = file_explainer(root, "---\nschema: explainer/v9\n---\n## I\nx\n")
    assert check(root, wrong_schema) == ["explainer-invalid"]
    drafter = {"name": "opn-drafter", "model": "m", "model_version": "1", "input_commit": "a" * 40}
    draft = file_explainer(root, explainer_text(h["proof"], ANCHORED, author=None, drafter=drafter))
    # No new drafts (F21-R2, ``test_no_new_drafts``): the service's own pull request is refused.
    service = modes.classify([draft], author=config.DEFAULT_SERVICE_LOGIN, graph_root=root)
    assert [d.code for d in modes.check(root, service)] == ["draft-not-accepted"]
    # Merged, the same draft validates and is read as a version.
    stem = draft.path.rsplit("/", 1)[-1].removesuffix(".md")
    [merged] = [
        v for v in explainers.versions(root / draft.path.rsplit("/", 2)[0]) if v.hash == stem
    ]
    assert merged.drafter == drafter and merged.author is None


def test_unanchored_name_warns_and_passes(graph: tuple[Path, dict[str, str]]) -> None:
    """AC4: a section citing ``Nat.Prime.two_le`` where its steps use it, and one where they do
    not: no warning and one ``explainer-name-unanchored`` warning, and both pass."""
    root, h = graph
    used = file_explainer(root, explainer_text(h["proof"], ANCHORED))
    unused = file_explainer(
        root,
        explainer_text(h["proof"], "## Intro\nx\n\n## First {steps: s1}\nBy `Nat.Prime.two_le`.\n"),
    )
    assert check(root, used) == [] and check(root, unused) == []
    assert warnings(root, used) == []
    [warning] = warnings(root, unused)
    assert warning.code == "explainer-name-unanchored"
    assert warning.details["name"] == "Nat.Prime.two_le"
    assert warning.details["steps"] == ["s1"]


def test_the_name_warning_reads_names_not_code(graph: tuple[Path, dict[str, str]]) -> None:
    """A step's descendants count as its own; a name occurring inside a used constant counts; an
    expression in backticks is not a name, nor is an unqualified one (a bound variable reads the
    same as a lemma's last component, so only a qualified name is held to the outline); an
    unanchored section is never warned about."""
    root, h = graph
    body = (
        "## Intro\nWe use `Foo.bar` here, unanchored.\n\n"
        "## Second {steps: s2}\n`Opn.f`, `two_le`, `Prime.two_le`, `n + 1`, `x` and "
        "`Nat.Prime.one_lt`.\n"
    )
    change = file_explainer(root, explainer_text(h["proof"], body))
    assert check(root, change) == []
    assert [w.details["name"] for w in warnings(root, change)] == ["Nat.Prime.one_lt"]
    assert json.dumps([w.as_dict() for w in warnings(root, change)])  # plain data


def bound(
    step_id: str,
    name: str | None,
    *,
    hypotheses: tuple[str, ...] = (),
    children: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    """A step binding ``name`` and leaving a goal with ``hypotheses``, as the extractor writes an
    ``obtain`` or a ``case`` (F19-Q4)."""
    out = step(step_id, children=children)
    out["name"] = name
    if hypotheses:
        out["goal"] = {
            "target": text_of("False"),
            "hypotheses": [{"name": h, "type": text_of("True")} for h in hypotheses],
        }
    return out


def test_names_the_outline_binds_do_not_warn(graph: tuple[Path, dict[str, str]]) -> None:
    """F22-T12 (testers 2026-10-06, #396, #429, #430): a backticked dotted name is held to the
    steps' constants only when it could be a library constant. Not warned: any step id of the
    outline (``tail_coeff.hNdeg``, a sub-step id the guide tells writers to cite, and
    ``aside.inner``, outside the section's steps); a name whose first component is a name an
    anchored step, or one of its sub-steps, binds, or a hypothesis its goal lists (``r.num``,
    ``hroot.hs``); a file name (``Context.lean``). Still warned: ``Finset.prod``, which no step's
    constants contain, and ``hidden.val``, a field of a local bound only by a step the section
    does not anchor."""
    root, _ = graph
    proof = write_outline(
        root,
        NODE,
        "Proof.lean",
        [
            bound("tail_coeff", "tail_coeff", children=(bound("tail_coeff.hNdeg", "hNdeg"),)),
            bound("s2", None, hypotheses=("hroot",)),
            bound("s3", "r"),
            bound("aside", "aside", children=(bound("aside.inner", "inner"),)),
            bound("s5", "hidden"),
        ],
    )
    body = (
        "## Intro\nThe outline.\n\n"
        "## The tail {steps: tail_coeff s2 s3}\n"
        "`tail_coeff.hNdeg` bounds the degree; `hroot.hs` and `r.num` are fields; see "
        "`Context.lean`; `aside.inner` is elsewhere; `Finset.prod` multiplies; `hidden.val` "
        "is bound elsewhere.\n"
    )
    change = file_explainer(root, explainer_text(proof, body))
    assert check(root, change) == []
    assert [w.details["name"] for w in warnings(root, change)] == ["Finset.prod", "hidden.val"]
