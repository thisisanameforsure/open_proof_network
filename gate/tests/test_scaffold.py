"""F08-T1: what the node scaffold refuses to build (R3, R4, R9; D-3, D-8, D-30; F08-Q6, Q14, Q16).

Every refusal here is raised before a byte is written (C7), and each one is a proposal that could
not be a node: an id outside the grammar, a statement that is not a statement, a claim without
its proof, or a directory that already exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import GRAPH, TARGET, copy_graph

from opn_gate import layout, scaffold
from opn_gate.scaffold import Proposal, ScaffoldError

NODES = GRAPH / "targets" / TARGET / "nodes"
AUTHOR = "thisisanameforsure"
STATEMENT = "theorem OpnProp.t : True := by\n  sorry\n"
WITNESS = "theorem witness : True := trivial\n"
RELATION = "theorem relation : True := trivial\n"


def proposal(**overrides: object) -> Proposal:
    args: dict[str, object] = {
        "node_id": "spec-00000000",
        "target_id": TARGET,
        "statement": STATEMENT,
        "witness": WITNESS,
        "author": AUTHOR,
    }
    args.update(overrides)
    return Proposal(**args)  # type: ignore[arg-type]


# --- ids (F08 §6, Q16) ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "node_id",
    ["Upper-case", "-leading-hyphen", "under_score", "a" * 65, "spaced id", ""],
)
def test_a_slug_outside_the_grammar_is_refused(node_id: str) -> None:
    with pytest.raises(ScaffoldError, match="must match"):
        scaffold.check_slug(node_id)


def test_the_version_suffix_is_reserved_for_a_curator(tmp_path: Path) -> None:
    """Q16: a proposal may not end in -v<n>; a revision must — and the scaffold refuses both
    mismatches before writing anything."""
    with pytest.raises(ScaffoldError, match="curator's revision"):
        scaffold.files(NODES, proposal(node_id="and-reassoc-v2"))
    with pytest.raises(ScaffoldError, match="ends in -v<n>"):
        scaffold.files(
            NODES, proposal(node_id="and-reassoc-again", extra_meta={"supersedes": "and-reassoc"})
        )
    assert not (tmp_path / "and-reassoc-v2").exists()
    # The bare grammar accepts the suffix only when told it is a revision.
    assert scaffold.check_slug("and-reassoc-v2", versioned=True) == "and-reassoc-v2"
    assert scaffold.check_slug("and-reassoc") == "and-reassoc"


def test_the_target_id_is_checked_too() -> None:
    with pytest.raises(ScaffoldError, match="must match"):
        scaffold.files(NODES, proposal(target_id="Propositional"))


# --- the statement and the witness (D-3, D-4 step 7) ---------------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        "theorem a : True := by\n  sorry\ntheorem b : True := by\n  sorry\n",  # two theorems
        "theorem a : True := trivial\n",  # a proof, not a statement
        "-- nothing declared\n",
        "theorem a : True := by\n  sorry\nexample : True := by\n  sorry\n",  # two sorry bodies
    ],
)
def test_a_statement_that_is_not_one_sorry_bodied_theorem_is_refused(statement: str) -> None:
    with pytest.raises(ScaffoldError, match="single sorry-bodied theorem"):
        scaffold.validate(proposal(statement=statement))


@pytest.mark.parametrize("witness", ["", "   \n\t"])
def test_a_blank_witness_is_refused(witness: str) -> None:
    with pytest.raises(ScaffoldError, match=r"Witness\.lean"):
        scaffold.validate(proposal(witness=witness))


# --- D-30's labels and the relation proof (Q6, Q14) ----------------------------------------------


def test_an_unknown_relation_label_is_refused() -> None:
    with pytest.raises(ScaffoldError, match="relation must be one of"):
        scaffold.validate(proposal(origin="variant", relation="stronger"))


def test_a_related_variant_may_not_carry_a_proof() -> None:
    """Q14 (iv): `related` claims no implication, so a proof would prove nothing it claims."""
    with pytest.raises(ScaffoldError, match="claims no implication"):
        scaffold.validate(proposal(origin="variant", relation="related", relation_proof=RELATION))
    with pytest.raises(ScaffoldError, match="claims no implication"):
        scaffold.validate(proposal(origin="variant", relation=None, relation_proof=RELATION))


def test_a_relation_proof_on_a_non_variant_is_refused() -> None:
    """D-3: Relation.lean is a variant's file."""
    with pytest.raises(ScaffoldError, match="variants only"):
        scaffold.validate(proposal(origin="authored", relation_proof=RELATION))


def test_a_proof_labelled_for_another_claim_is_refused() -> None:
    """Q14 (iv): the file carries its own label; a conflicting one is refused, not relabelled."""
    with pytest.raises(ScaffoldError, match="says `-- relation: partial`"):
        scaffold.with_relation_label("-- relation: partial\n" + RELATION, "resolves")
    assert (
        scaffold.with_relation_label(RELATION, "resolves") == "-- relation: resolves\n" + RELATION
    )
    same = "-- relation: resolves\n" + RELATION
    assert scaffold.with_relation_label(same, "resolves") == same


# --- Context.lean needs every dep (F01-R6) -------------------------------------------------------


def test_a_dep_that_is_not_a_node_is_refused() -> None:
    with pytest.raises(ScaffoldError, match="'ghost' is not a node"):
        scaffold.context_for(NODES, ("and-reassoc", "ghost"))
    with pytest.raises(ScaffoldError, match="'ghost' is not a node"):
        scaffold.context_from(("ghost",), {"and-reassoc": STATEMENT})
    with pytest.raises(ScaffoldError, match="'ghost' is not a node"):
        scaffold.files(None, proposal(deps=("ghost",)), dep_statements={})


def test_a_scaffold_needs_a_source_for_the_deps() -> None:
    with pytest.raises(ScaffoldError, match="either a nodes directory"):
        scaffold.files(None, proposal())


# --- never into an existing directory (D-3, D-8) -------------------------------------------------


def test_write_never_touches_an_existing_node(tmp_path: Path) -> None:
    """A proposal that lands on an existing id is a revision wearing a proposal's clothes."""
    root = copy_graph(tmp_path)
    nodes = layout.graph_nodes_dir(root, TARGET)
    before = {p: p.read_bytes() for p in (nodes / "and-reassoc").rglob("*") if p.is_file()}
    with pytest.raises(ScaffoldError, match="already exists"):
        scaffold.write(nodes, proposal(node_id="and-reassoc"))
    assert {p: p.read_bytes() for p in (nodes / "and-reassoc").rglob("*") if p.is_file()} == before


def test_a_refused_proposal_writes_nothing(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    nodes = layout.graph_nodes_dir(root, TARGET)
    with pytest.raises(ScaffoldError):
        scaffold.write(nodes, proposal(node_id="spec-bad", witness=""))
    assert not (nodes / "spec-bad").exists()


# --- what the id and the META say ----------------------------------------------------------------


def test_speculative_id_is_derived_from_the_statement() -> None:
    """R3: the same crux proposed twice collides by name rather than entering twice."""
    assert scaffold.speculative_id(STATEMENT) == scaffold.speculative_id(STATEMENT)
    assert scaffold.speculative_id(STATEMENT) != scaffold.speculative_id(STATEMENT + "\n")
    assert scaffold.speculative_id(STATEMENT).startswith("spec-")
    assert scaffold.speculative_id(STATEMENT, "variant").startswith("variant-")
    scaffold.check_slug(scaffold.speculative_id(STATEMENT))


def test_meta_schema_is_the_oldest_that_fits() -> None:
    """A node that needs neither skeleton-hole nor supersedes keeps meta/v2, so committed
    nodes never churn; each newer field selects the version that carries it."""
    assert scaffold.meta_for(proposal(), "a" * 64)["schema"] == "meta/v2"
    hole = proposal(node_id="and-reassoc--h1", origin="skeleton-hole")
    assert scaffold.meta_for(hole, "a" * 64)["schema"] == "meta/v3"
    revision = proposal(node_id="and-reassoc-v2", extra_meta={"supersedes": "and-reassoc"})
    meta = scaffold.meta_for(revision, "a" * 64)
    assert meta["schema"] == "meta/v4" and meta["supersedes"] == "and-reassoc"
