"""F29-T9: a gloss may describe a merged partial, and the route's approach reads it.

A route's ``approach`` (``graph.json`` ``decompositions[].approach``, F29-R4) was read from the
partial's own ``-- approach:`` line, else its leading comment, else its annex's first sentence.
A merged partial is immutable, and on the live graph 21 of 34 routes have none of these, so the
selector says "route 1 of h_small_n" for them forever. Labels and claims have a correction path
already, the superseding statement gloss (D-3 v3.44); a route's approach takes the same one: a
``gloss/v3`` record of kind ``partial`` on the partial's path under the node, whose current
version's first sentence is the approach when the partial declared none.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from harness import TARGET, copy_graph
from test_decompositions import HOLE_IDS, PARTIAL, add_hole, decompositions, merged_partial
from test_products import ROOT_NODE, nodes_dir

from opn_gate import glosses, labels, modes, paths, products, schemas
from opn_gate import graph as graphmod
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner

BARE = "theorem x : True := by\n  sorry\n"  # no comment, no annex, no declared line
GLOSS_WORDS = "Bound the density of the set first. Then the rest follows by counting."
SECOND_WORDS = "Count the small cases directly! The large ones reduce to the first route."


def bare_partial(root: Path, n: int = 7, path: str = PARTIAL) -> None:
    """A merged partial carrying nothing a route's approach could be read from."""
    merged_partial(root, n, ["hden"], path=path, annex=None)
    (nodes_dir(root) / ROOT_NODE / path).write_text(BARE, encoding="utf-8")


def partial_doc(root: Path, module: str = PARTIAL, **over: Any) -> dict[str, Any]:
    file = nodes_dir(root) / ROOT_NODE / module
    return {
        "schema": "gloss/v3",
        "target": TARGET,
        "subject": {
            "kind": "partial",
            "node": ROOT_NODE,
            "module": module,
            "lean_hash": schemas.content_hash(file.read_bytes() if file.is_file() else b""),
        },
        "supersedes": None,
        "author": "carol",
        "drafter": None,
        "date": "2026-10-17",
        "licence": "CC-BY-4.0",
        **over,
    }


def put_gloss(root: Path, doc: dict[str, Any], body: str) -> tuple[str, str]:
    """The record under the node's ``gloss/``; ``(hash, graph path)``."""
    text = "---\n" + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True) + "---\n" + body
    digest = schemas.content_hash(text.encode("utf-8"))
    directory = nodes_dir(root) / ROOT_NODE / "gloss"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{digest}.md").write_text(text, encoding="utf-8")
    return digest, f"targets/{TARGET}/nodes/{ROOT_NODE}/gloss/{digest}.md"


def gate_codes(root: Path, path: str) -> list[str]:
    """What the gate says of the record as a submission, the way an append merges."""
    classification = modes.classify([Change("A", path)], author="carol", graph_root=root)
    assert classification.ok, classification.as_dict()
    return [d.code for d in modes.check(root, classification)]


# --- the record ----------------------------------------------------------------------------------


def test_a_partial_gloss_validates_and_the_gate_accepts_it_on_its_node(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    bare_partial(root)
    doc = partial_doc(root)
    assert schemas.violations(doc, "gloss/v3") == []
    _, path = put_gloss(root, doc, GLOSS_WORDS + "\n")
    located = paths.locate(path)
    assert located is not None
    assert glosses.check_gloss(root, located) == []
    assert gate_codes(root, path) == []


def test_a_partial_gloss_of_a_path_not_in_the_tree_is_subject_unknown(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    bare_partial(root)
    other = "attempts/20260101T000000Z-nobody-partial.lean"
    _, path = put_gloss(root, partial_doc(root, module=other), GLOSS_WORDS + "\n")
    located = paths.locate(path)
    assert located is not None
    [problem] = glosses.check_gloss(root, located)
    assert problem.code == "gloss-subject-unknown"
    assert problem.details["file"] == f"targets/{TARGET}/nodes/{ROOT_NODE}/{other}"


def test_a_partial_gloss_whose_module_is_not_under_attempts_is_invalid(tmp_path: Path) -> None:
    """The path is checked before anything is read: a partial's module is its ``attempts/``
    file, ending ``-partial.lean``, and never leaves the node."""
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    bare_partial(root)
    for module in ("Proof.lean", "attempts/x-alternate.lean", "attempts/../Proof.lean"):
        doc = partial_doc(root, module=module)
        doc["subject"]["lean_hash"] = "0" * 64
        if schemas.violations(doc, "gloss/v3"):
            continue  # the schema's pattern refuses it before the gate reads it
        _, path = put_gloss(root, doc, GLOSS_WORDS + "\n")
        located = paths.locate(path)
        assert located is not None
        [problem] = glosses.check_gloss(root, located)
        assert problem.code == "gloss-invalid", module
    assert (
        glosses.subject_file(
            root / "targets" / TARGET,
            {"kind": "partial", "node": ROOT_NODE, "module": "attempts/../Proof.lean"},
        )
        is None
    )


# --- the approach ------------------------------------------------------------------------------


def test_the_approach_reads_the_declared_line_then_the_gloss_then_the_comment_then_the_annex() -> (
    None
):
    declared = "theorem x : True := by\n  -- approach: Declared here\n  -- a comment\n  sorry\n"
    commented = "theorem x : True := by\n  -- A leading comment.\n  sorry\n"
    annex = "The annex opens like this. And goes on."
    assert labels.approach_of(declared, gloss=GLOSS_WORDS, annex=annex) == "Declared here"
    assert (
        labels.approach_of(commented, gloss=GLOSS_WORDS, annex=annex)
        == "Bound the density of the set first."
    )
    assert labels.approach_of(commented, gloss=None, annex=annex) == "A leading comment."
    assert labels.approach_of(BARE, gloss=None, annex=annex) == "The annex opens like this."
    assert labels.approach_of(BARE) is None
    assert labels.approach_of(BARE, gloss="x" * 400) == "x" * 299 + "…"


def test_decompositions_read_the_approach_from_the_partial_gloss(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    bare_partial(root)
    [before] = decompositions(root)
    assert before["approach"] is None
    put_gloss(root, partial_doc(root), GLOSS_WORDS + "\n")
    [after] = decompositions(root)
    assert after["approach"] == "Bound the density of the set first."
    assert after["partial"] == PARTIAL


def test_a_superseding_version_replaces_the_approach(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    bare_partial(root)
    first, _ = put_gloss(root, partial_doc(root), GLOSS_WORDS + "\n")
    put_gloss(
        root,
        partial_doc(root, supersedes=first, date="2026-10-18", author="dana"),
        SECOND_WORDS + "\n",
    )
    [d] = decompositions(root)
    assert d["approach"] == "Count the small cases directly!"


def test_glosses_json_lists_the_partial_as_a_gloss_subject_with_its_chain(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    bare_partial(root)
    digest, _ = put_gloss(root, partial_doc(root), GLOSS_WORDS + "\n")
    tg = graphmod.load_target(root, TARGET)
    doc = schemas.validate(
        products.glosses_doc(tg, None, signer=SshKeygenSigner()), products.GLOSSES_SCHEMA
    )
    rows = [s for s in doc["subjects"] if s["kind"] == "partial" and s["node"] == ROOT_NODE]
    assert [(s["record"], s["module"], s["file"]) for s in rows] == [
        ("explainer", None, f"nodes/{ROOT_NODE}/{PARTIAL}"),
        ("gloss", PARTIAL, f"nodes/{ROOT_NODE}/{PARTIAL}"),
    ]
    explainer_row, gloss_row = rows
    assert explainer_row["chains"] == []
    [chain] = gloss_row["chains"]
    assert chain["current"] == digest
    assert [v["hash"] for v in chain["versions"]] == [digest]
    assert chain["versions"][0]["describes_current"] is True
    assert gloss_row["lean_hash"] == explainer_row["lean_hash"]


def test_coverage_says_whether_a_merged_partial_has_approach_words(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    bare_partial(root)

    def partial_row() -> dict[str, Any]:
        report = glosses.coverage(root)
        [row] = [r for r in report["subjects"] if r["kind"] == "partial"]
        return dict(row)

    row = partial_row()
    assert row["approach_words"] is False
    assert row["covered"] is False and row["reason"] == glosses.NO_EXPLAINER
    put_gloss(root, partial_doc(root), GLOSS_WORDS + "\n")
    row = partial_row()
    assert row["approach_words"] is True
    assert row["covered"] is False, "approach words do not cover the artifact; an explainer does"
    assert glosses.coverage(root)["complete"] is False


# --- testers 2026-10-27 (D's F-D7): an explainer's text filed as a gloss --------------------------


def test_step_anchored_text_filed_as_a_gloss_is_warned_not_refused(tmp_path: Path) -> None:
    """A gloss of kind ``partial`` whose text carries ``{steps: …}`` headings was accepted as a
    one-section gloss with no warning: the anchors only mean something in an explainer, so the
    writer had filed an explainer under the wrong record and nothing said so. The gate warns
    (F20-R5: never a refusal), naming the record an explainer is."""
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    bare_partial(root)
    _, anchored = put_gloss(
        root, partial_doc(root), "## The bound {steps: s1}\nBound the density first.\n"
    )
    classification = modes.classify([Change("A", anchored)], author="carol", graph_root=root)
    assert classification.ok, classification.as_dict()
    assert modes.check(root, classification) == []
    found = modes.warnings(root, classification)
    assert [w.code for w in found] == ["gloss-step-anchors"]
    assert "explainer" in found[0].message


def test_a_plain_gloss_is_not_warned(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    bare_partial(root)
    _, plain = put_gloss(root, partial_doc(root), GLOSS_WORDS + "\n")
    classification = modes.classify([Change("A", plain)], author="carol", graph_root=root)
    assert modes.warnings(root, classification) == []
