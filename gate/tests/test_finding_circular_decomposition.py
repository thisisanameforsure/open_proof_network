"""Finding: a decomposition can be circular up to proof, and nothing could say so.

Found live 2026-09-23 by the nine testers on the calibration targets. Two merged skeletons had
produced holes that are no easier than what they were meant to reduce: on ``erdos-1050`` the
grandchild hole ``erdos-1050--h1-v2--h1`` states the root again after a reindexing identity (the
sum over n ≥ 0 of 1/(2^(n+1) - 3) differs from the sum of 1/(2^(n+3) - 3) by its first two
terms, -1 and +1), and on ``erdos-69`` the hole ``erdos-69--h2-v2--h1-v2--h4`` is equivalent to
the target. Both were published claimable, so the frontier invited provers to attack the open
problem again under another name, and a D-16 defect claim could not record the fact: no class
said "circular", a claim could not name the statement it circles back to, and the gate only
checked that an exhibit *elaborates*, never what it proves.

No program decides "equivalent up to proof". The owner's ruling (2026-09-23): anyone may file a
claim whose Lean exhibit proves ``Ancestor → Hole`` — the hole is no easier than a statement it
was meant to reduce; the gate elaborates the exhibit in the sandbox and checks its type is that
implication, with the ancestor a transitive dependent of the hole (read through revisions); once
merged, the hole leaves the frontier with the reason ``circular`` and the site labels it. No
record is rewritten: the claim file is the fact the products derive from (derive, never
rewrite, F08-T10).

The shape: ``defect-claim/v3`` adds the class ``circular-decomposition`` and the field
``ancestor``; the classifier checks the ancestor, ``exhibits.run`` asks ``opn-relation-type``
(label ``resolves``, the ancestor as the variant and the hole as the root) whether the exhibit's
one theorem is that implication, and ``graph.load_target`` reads the merged claim into
``NodeFacts.circular``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from fakes import FakeToolchain, relation_result
from harness import TARGET, copy_graph

from opn_gate import config, exhibits, graph, layout, modes, paths, products, schemas
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import AxiomResult

HOLE = "and-reassoc"
ANCESTOR = "and-swap-reassoc"  # the root; it depends on the hole
SIBLING = "tutorial-and-swap"  # a node beside the hole, not above it
CLAIM = f"targets/{TARGET}/nodes/{HOLE}/defects/20260923T120000Z-alice.yaml"
EXHIBIT = (
    "theorem circular :\n"
    "    (∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p)) →\n"
    "    ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) :=\n"
    "  fun _ _ _ _ h => ⟨h.1.1, h.1.2, h.2⟩\n"
)
RENDERED = "5" * 40
NOW = "2026-09-23T12:00:00Z"


def claim_doc(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "defect-claim/v3",
        "stmt_ref": HOLE,
        "class": "circular-decomposition",
        "ancestor": ANCESTOR,
        "line": 1,
        "exhibit": EXHIBIT,
        "contributor": "alice",
        "date": "2026-09-23",
    }
    doc.update(overrides)
    return {k: v for k, v in doc.items() if v is not None}


def file_claim(root: Path, rel: str = CLAIM, **overrides: Any) -> str:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(
        yaml.safe_dump(claim_doc(**overrides), sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    return rel


def check_codes(root: Path, rel: str) -> list[str]:
    classification = modes.classify([Change("A", rel)])
    assert classification.mode == "append", classification
    return [d.code for d in modes.check(root, classification)]


def run_exhibits(root: Path, rel: str, fake: FakeToolchain) -> list[str]:
    classification = modes.classify([Change("A", rel)])
    spec_path = layout.gate_spec_path(root, TARGET)
    ctx = RunContext(
        graph_root=root,
        claim=Claim(TARGET, classification.node_id or ""),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=root.parent / "work",
        toolchain=fake,
        settings=config.load({}),
    )
    return [d.code for d in exhibits.run(ctx, modes.exhibits(root, classification))]


# --- the claim can be expressed, and the classifier checks the ancestor ---------------------------


def test_a_circularity_claim_is_an_append_the_gate_accepts(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    rel = file_claim(root)
    located = paths.locate(rel)
    assert located is not None and located.role == "defect-claim"
    assert schemas.violations(claim_doc(), "defect-claim/v3") == []
    assert check_codes(root, rel) == []


@pytest.mark.parametrize(
    ("overrides", "why"),
    [
        ({"ancestor": SIBLING}, "a sibling is not above the hole"),
        ({"ancestor": HOLE}, "a node is not its own ancestor"),
        ({"ancestor": "ghost"}, "not a node of the target"),
    ],
)
def test_the_ancestor_must_be_a_transitive_dependent(
    tmp_path: Path, overrides: dict[str, Any], why: str
) -> None:
    root = copy_graph(tmp_path)
    assert check_codes(root, file_claim(root, **overrides)) == ["circular-ancestor"], why


def test_a_circularity_claim_names_its_ancestor(tmp_path: Path) -> None:
    """Without an ancestor there is no implication to check: the schema refuses it."""
    doc = claim_doc()
    del doc["ancestor"]
    assert schemas.violations(doc, "defect-claim/v3") != []


def test_an_ancestor_on_any_other_class_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    rel = file_claim(root, **{"class": "junk-value"})
    assert check_codes(root, rel) == ["circular-ancestor"]


def test_the_ancestor_is_read_through_revisions(tmp_path: Path) -> None:
    """D-8: the root's META still names the superseded child; the claim is on its revision."""
    root = copy_graph(tmp_path)
    nodes = root / "targets" / TARGET / "nodes"
    revised = nodes / f"{HOLE}-v2"
    revised.mkdir()
    for name in ("Statement.lean", "Context.lean", "Witness.lean"):
        (revised / name).write_bytes((nodes / HOLE / name).read_bytes())
    meta = yaml.safe_load((nodes / HOLE / "META.yaml").read_text())
    meta.update({"id": f"{HOLE}-v2", "schema": "meta/v4", "supersedes": HOLE})
    (revised / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    status = nodes / HOLE / "status"
    status.mkdir()
    (status / "2026-09-23-1.yaml").write_text(
        yaml.safe_dump(samples.node_status(status="superseded", reference=f"{HOLE}-v2")),
        encoding="utf-8",
    )
    rel = f"targets/{TARGET}/nodes/{HOLE}-v2/defects/20260923T120000Z-alice.yaml"
    assert check_codes(root, file_claim(root, rel, stmt_ref=f"{HOLE}-v2")) == []


# --- the sandbox checks what the exhibit proves -------------------------------------------------


def test_the_exhibit_is_checked_as_ancestor_implies_hole(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    fake = FakeToolchain()
    assert run_exhibits(root, file_claim(root), fake) == []
    # The ancestor is the variant and the hole the root: ``resolves`` is variant → root.
    assert "relation_type:resolves:OpnProp.and_swap_reassoc" in fake.calls


def test_the_reverse_implication_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    fake = FakeToolchain(relation=relation_result(expected="A → H", declared="H → A"))
    assert run_exhibits(root, file_claim(root), fake) == ["circular-direction"]


def test_an_exhibit_resting_on_sorry_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    fake = FakeToolchain(relation=relation_result(axioms=("sorryAx",)))
    assert run_exhibits(root, file_claim(root), fake) == ["circular-sorry"]


def test_an_exhibit_with_no_theorem_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    rel = file_claim(root, exhibit="example : True := trivial\n")
    assert run_exhibits(root, rel, FakeToolchain()) == ["circular-exhibit"]


def test_other_claims_still_only_elaborate(tmp_path: Path) -> None:
    """Guard: a D-16 claim of any other class asks nothing of the relation program."""
    root = copy_graph(tmp_path)
    rel = file_claim(root, ancestor=None, **{"class": "junk-value", "schema": "defect-claim/v1"})
    fake = FakeToolchain(axiom_result=AxiomResult(ok=True))
    assert run_exhibits(root, rel, fake) == []
    assert not any(c.startswith("relation_type") for c in fake.calls)


# --- once merged, the hole leaves the frontier and graph.json says why ----------------------------


def generate(root: Path) -> products.Products:
    return products.generate(root, rendered_from=RENDERED, commit_time=NOW)


def frontier_ids(prod: products.Products) -> list[str]:
    doc = json.loads(prod.files[Path("frontier.json")])
    return [str(e["node_id"]) for e in doc["entries"]]


def graph_row(prod: products.Products, node_id: str) -> dict[str, Any]:
    doc = json.loads(prod.files[Path("targets") / TARGET / "graph.json"])
    rows: list[dict[str, Any]] = [n for n in doc["nodes"] if n["node_id"] == node_id]
    return rows[0]


def test_a_merged_circularity_claim_takes_the_hole_off_the_frontier(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    assert HOLE in frontier_ids(generate(root)), "guard: the hole is work before the claim"
    file_claim(root)
    prod = generate(root)
    assert HOLE not in frontier_ids(prod)
    row = graph_row(prod, HOLE)
    assert row["status"] == "ready"  # nothing about the statement changed (D-3)
    assert row["cause"] == "circular"
    assert graph.load_target(root, TARGET).nodes[HOLE].circular == CLAIM.split(f"{HOLE}/")[1]


def test_no_record_is_rewritten(tmp_path: Path) -> None:
    """Derive, never rewrite: the products are all that change, and removing the claim (one
    commit's revert) restores them byte for byte."""
    root = copy_graph(tmp_path, publish=True)
    before = generate(root).files
    meta = (root / "targets" / TARGET / "nodes" / HOLE / "META.yaml").read_bytes()
    rel = file_claim(root)
    generate(root)
    assert (root / "targets" / TARGET / "nodes" / HOLE / "META.yaml").read_bytes() == meta
    (root / rel).unlink()
    assert generate(root).files == before


def test_a_claim_of_another_class_leaves_the_hole_on_the_frontier(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    file_claim(root, ancestor=None, **{"class": "junk-value", "schema": "defect-claim/v1"})
    prod = generate(root)
    assert HOLE in frontier_ids(prod)
    assert graph_row(prod, HOLE)["cause"] is None
