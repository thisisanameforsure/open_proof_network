"""F29-T2 / AC9 (R7; D-12 v3.44, D-3 v3.44): the hole writer files each child's gloss.

When the post-merge job writes a hole's child from a partial that declares its words, it files
beside the child a ``gloss/v3`` statement gloss of the child's ``Statement.lean``: the hole's
label, a body opening with the claim as a display followed by the block's prose, the partial's
author, the partial's licence and the submission's declared model. The gate's own gloss check
accepts what the job wrote; the products then read the child's label from the gloss. A partial
without declarations (an older pin) files none, and a hole that became an existing node (an edge
or a lemma) gets no gloss from this merge.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml
from harness import TARGET, copy_graph
from test_postmerge import HOLES, PARENT, PSEUDONYM, STAMP
from test_products import attest

from opn_gate import glosses, labels, postmerge, products, schemas
from opn_gate import graph as graphmod
from opn_gate.paths import Located

DEP_A = "tutorial-and-swap"
DEP_B = "and-reassoc"
H1 = f"{PARENT}--h1"
H2 = f"{PARENT}--h2"
MODEL = "claude-fable-5-1 through the MCP"

LABELLED = """/-! A partial proof of the root (D-12 #5). -/

theorem OpnProp.and_swap_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p) := by
  -- approach: peel r off the outer conjunction, then swap the inner one
  -- licence: CC-BY-4.0
  intro p q r h
  -- label: the outer conjunct
  -- claim: $r$
  -- The right half of the hypothesis, taken directly.
  have right : r := sorry
  -- label: the inner swap
  -- claim: $$q \\land p$$
  have left : q ∧ p := sorry
  exact ⟨right, left⟩
"""

UNLABELLED = """/-! A partial proof of the root (D-12 #5). -/

theorem OpnProp.and_swap_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p) := by
  intro p q r h
  have right : r := sorry
  have left : q ∧ p := sorry
  exact ⟨right, left⟩
"""


def decomposed(tmp_path: Path, text: str, **kwargs: Any) -> tuple[Path, postmerge.PartialMerge]:
    root = copy_graph(tmp_path, publish=True)
    parent = root / "targets" / TARGET / "nodes" / PARENT
    (parent / "Proof.lean").unlink()
    attest(root, DEP_A, n=1)
    attest(root, DEP_B, n=2)
    merged = postmerge.apply_partial(
        parent, HOLES, partial_text=text, pseudonym=PSEUDONYM, stamp=STAMP, **kwargs
    )
    return root, merged


def gloss_files(root: Path, child: str) -> list[Path]:
    directory = root / "targets" / TARGET / "nodes" / child / "gloss"
    return sorted(directory.iterdir()) if directory.is_dir() else []


def located(root: Path, path: Path) -> Located:
    rel = path.relative_to(root).as_posix()
    return Located("gloss", rel, TARGET, path.parents[1].name)


def test_each_created_child_carries_one_gloss_the_gate_accepts(tmp_path: Path) -> None:
    root, merged = decomposed(tmp_path, LABELLED, model=MODEL)
    assert merged.children == (H1, H2)
    expected = {H1: ("the outer conjunct", "r"), H2: ("the inner swap", "q \\land p")}
    for child, (label, claim) in expected.items():
        files = gloss_files(root, child)
        assert len(files) == 1, child
        text = files[0].read_text(encoding="utf-8")
        doc, body = glosses.split_front_matter(text)
        assert doc is not None
        assert schemas.violations(doc, "gloss/v3") == []
        assert doc["schema"] == "gloss/v3" and doc["label"] == label
        assert doc["target"] == TARGET and doc["supersedes"] is None
        assert doc["author"] == PSEUDONYM and doc["drafter"] is None
        assert doc["date"] == "2026-09-10" and doc["licence"] == "CC-BY-4.0"
        assert doc["drafted_with"] == MODEL
        statement = root / "targets" / TARGET / "nodes" / child / "Statement.lean"
        assert doc["subject"] == {
            "kind": "statement",
            "node": child,
            "module": None,
            "lean_hash": schemas.content_hash(statement.read_bytes()),
        }
        assert body.startswith(f"$${claim}$$\n")
        assert body.endswith("\n")
        assert labels.claim_of(body) == claim
        # Named for its own bytes, and the gate's own check (R1, R3) accepts it as filed.
        assert files[0].stem == schemas.content_hash(text.encode("utf-8"))
        assert glosses.check_gloss(root, located(root, files[0])) == []
    h1_body = glosses.split_front_matter(gloss_files(root, H1)[0].read_text())[1]
    assert h1_body == "$$r$$\n\nThe right half of the hypothesis, taken directly.\n"
    h2_body = glosses.split_front_matter(gloss_files(root, H2)[0].read_text())[1]
    assert h2_body == "$$q \\land p$$\n"


def test_the_written_paths_are_on_the_merge_record(tmp_path: Path) -> None:
    root, merged = decomposed(tmp_path, LABELLED)
    nodes = root / "targets" / TARGET / "nodes"
    assert len(merged.glosses) == 2
    assert [str(p) for p in merged.glosses] == [
        (nodes / child / "gloss" / f.name).relative_to(nodes.parent).as_posix()
        for child in (H1, H2)
        for f in gloss_files(root, child)
    ]
    assert merged.as_dict()["glosses"] == list(merged.glosses)
    # Without a model the record says so, and the file validates all the same.
    doc, _ = glosses.split_front_matter(gloss_files(root, H1)[0].read_text(encoding="utf-8"))
    assert doc is not None and doc["drafted_with"] is None


def test_the_products_read_the_label_from_the_gloss(tmp_path: Path) -> None:
    root, _ = decomposed(tmp_path, LABELLED)
    tg = graphmod.load_target(root, TARGET)
    doc = products.graph_doc(tg, "5" * 40)
    assert schemas.violations(doc, products.GRAPH_SCHEMA) == []
    by_id = {n["node_id"]: n for n in doc["nodes"]}
    assert by_id[H1]["label"] == "the outer conjunct"
    assert by_id[H1]["label_source"] == "gloss"
    assert by_id[H1]["claim"] == "r"
    assert by_id[H2]["label"] == "the inner swap"
    assert by_id[H2]["claim"] == "q \\land p"


def test_a_partial_without_declarations_files_none(tmp_path: Path) -> None:
    root, merged = decomposed(tmp_path, UNLABELLED)
    assert merged.children == (H1, H2)
    assert gloss_files(root, H1) == [] and gloss_files(root, H2) == []
    assert merged.glosses == ()
    assert "glosses" not in merged.as_dict()
    tg = graphmod.load_target(root, TARGET)
    by_id = {n["node_id"]: n for n in products.graph_doc(tg, "5" * 40)["nodes"]}
    assert (by_id[H1]["label"], by_id[H1]["label_source"]) == ("right", "hole")


def test_a_partial_with_a_licence_the_network_does_not_accept_files_none(tmp_path: Path) -> None:
    """Step 4 refuses such a partial (AC8); under an older pin it merges, and the writer files no
    words under a licence the record does not accept rather than choosing one (F05-T17)."""
    root, merged = decomposed(tmp_path, LABELLED.replace("CC-BY-4.0", "WTFPL"))
    assert gloss_files(root, H1) == [] and merged.glosses == ()


def test_a_hole_that_became_an_existing_node_gets_no_gloss(tmp_path: Path) -> None:
    """A hole the extractor matched to a sibling is that node (an edge or a lemma, F07-T7,
    T77): this merge writes nothing under it, words included."""
    root = copy_graph(tmp_path, publish=True)
    parent = root / "targets" / TARGET / "nodes" / PARENT
    (parent / "Proof.lean").unlink()
    attest(root, DEP_A, n=1)
    attest(root, DEP_B, n=2)
    holes = (replace(HOLES[0], defeq_sibling=DEP_B), HOLES[1])
    merged = postmerge.apply_partial(
        parent, holes, partial_text=LABELLED, pseudonym=PSEUDONYM, stamp=STAMP
    )
    assert merged.children == (H2,)
    assert gloss_files(root, DEP_B) == []
    assert len(merged.glosses) == 1 and merged.glosses[0].startswith(f"nodes/{H2}/gloss/")
    doc, _ = glosses.split_front_matter(gloss_files(root, H2)[0].read_text(encoding="utf-8"))
    assert doc is not None and doc["label"] == "the inner swap"


def test_the_yaml_style_is_the_services(tmp_path: Path) -> None:
    """A job-written gloss and a service-written one look alike: sorted keys, unicode kept."""
    root, _ = decomposed(tmp_path, LABELLED)
    text = gloss_files(root, H1)[0].read_text(encoding="utf-8")
    head = text.split("---\n")[1]
    doc = yaml.safe_load(head)
    assert head == yaml.safe_dump(doc, sort_keys=True, allow_unicode=True)
