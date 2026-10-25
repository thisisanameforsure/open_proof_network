"""F31-T2 (R1, AC1): the shelving record at the gate — an append whose signer is a steward of
the target or a curator, refused on the root, on a used statement and for a route that is not
the node's; F31-T5 (R5, AC5): work on a shelved statement refused pre-merge, ``node-shelved``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from harness import TARGET
from shelving_support import ALICE, ROOT, SERVICE, SIGNER, STRANGER, A, T, Tree, make_keys
from test_modes import CURATOR

from opn_gate import modes, paths, signed

PARTIAL = "attempts/20261023T000000Z-t1023-f1-partial.lean"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory.mktemp("shelving-keys"))


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Tree:
    return Tree(tmp_path, keys)


# --- the role ---------------------------------------------------------------------------------


def test_the_role_is_registered_as_an_append(tree: Tree) -> None:
    change = tree.shelve(ALICE, A)
    located = paths.locate(change.path)
    assert located is not None
    assert located.role == "shelving" and located.node_id == A
    assert "shelving" in paths.APPEND_ROLES
    assert paths.SCHEMAS_FOR_ROLE["shelving"] == ("shelving/v1",)
    classification = tree.classify(change)
    assert classification.ok and classification.mode == "append", classification.as_dict()


def test_a_stewards_approval_key_record_opened_by_the_service_passes(tree: Tree) -> None:
    """AC1: the live shape — the service signs with the approval key for a signed-in steward."""
    change = tree.shelve(ALICE, A)
    assert tree.codes(change) == []
    found = modes.check_as_service(
        tree.root, change.path, (tree.root / change.path).read_bytes(), service_login=SERVICE
    )
    assert [d.code for d in found] == []


def test_a_curators_own_ssh_record_passes_when_the_curator_opened_it(tree: Tree) -> None:
    change = tree.signed_by(CURATOR, A)
    assert tree.codes(change, opened_by=CURATOR) == []


def test_a_stewards_ssh_record_under_her_steward_key_passes_from_the_service(tree: Tree) -> None:
    assert tree.codes(tree.signed_by(ALICE, A)) == []


def test_a_proved_statement_may_be_shelved(tree: Tree) -> None:
    """Rule 2: proved statements can be shelved; nothing uses this one."""
    tree.prove(A)
    assert tree.codes(tree.shelve(ALICE, A)) == []


def test_an_unshelve_and_a_route_retirement_pass_the_same_rules(tree: Tree) -> None:
    tree.partial(A, ["h1"], path=PARTIAL)
    assert tree.codes(tree.shelve(ALICE, A, action="unshelved")) == []
    assert tree.codes(tree.shelve(ALICE, A, scope="route", route=PARTIAL)) == []


# --- refusals ---------------------------------------------------------------------------------


def test_a_signer_who_is_neither_steward_nor_curator_is_refused(tree: Tree) -> None:
    assert tree.codes(tree.shelve(STRANGER, A)) == ["shelving-signer-unlisted"]


def test_a_tampered_record_is_refused(tree: Tree) -> None:
    change = tree.shelve(ALICE, A)
    path = tree.root / change.path
    doc = yaml.safe_load(path.read_text())
    doc["cause"] = "another cause under the same signature"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    assert tree.codes(change) == ["shelving-signature"]


def test_an_approval_key_record_under_another_key_is_refused(tree: Tree) -> None:
    change = tree.signed_by(ALICE, A, key=STRANGER, via=signed.VIA_APPROVAL_KEY)
    assert tree.codes(change) == ["shelving-signature"]


def test_an_ssh_record_under_a_key_that_is_not_the_signers_needs_the_signer_to_open_it(
    tree: Tree,
) -> None:
    change = tree.signed_by(ALICE, A, key=STRANGER)
    assert tree.codes(change) == ["signer-not-opener"]
    assert tree.codes(change, opened_by=ALICE) == []


def test_an_unsigned_record_does_not_validate(tree: Tree) -> None:
    """The schema makes every record signed (``key`` and ``signature`` are strings), so an
    unsigned one is refused at the schema, before any signature rule."""
    change = tree.write(tree.document(A))
    assert set(tree.codes(change)) == {"record-invalid"}  # one per missing field


def test_a_record_filed_under_another_node_is_refused(tree: Tree) -> None:
    doc = tree.document(T)
    doc = signed.sign(doc, tree.keys[ALICE], SIGNER)
    name = "20261024T100000Z-alice-steward.yaml"
    path = tree.node_dir(A) / "shelving" / name
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    change = paths.Change("A", path.relative_to(tree.root).as_posix())
    assert tree.codes(change) == ["shelving-node"]


ROOT_HOLE = f"{ROOT}--h9"
ROOT_ROUTE = "attempts/20261025T000000Z-root-partial.lean"


def test_a_record_on_the_root_is_refused(tree: Tree) -> None:
    """``scope: node`` on the root; a retirement of one of the root's routes is another matter
    (``test_a_route_record_on_the_root_passes``)."""
    assert tree.codes(tree.shelve(ALICE, ROOT)) == ["node-root"]


def test_a_route_record_on_the_root_passes(tree: Tree) -> None:
    """F31-Q18 (the owner's first live act, 2026-10-25, refused ``node-root``): a retirement
    names a decomposition of the node it sits on and never shelves that node, so the root's
    routes are retired like any other's."""
    tree.hole(ROOT_HOLE, "hr", parent=ROOT)
    tree.partial(ROOT, ["hr"], path=ROOT_ROUTE)
    assert tree.codes(tree.shelve(ALICE, ROOT, scope="route", route=ROOT_ROUTE)) == []


def test_a_record_on_a_statement_a_merged_proof_uses_is_refused(tree: Tree) -> None:
    """Rule 3: ``A`` is named in the root's proof footprint, so it may not be shelved; ``T``,
    proved but used by nothing, may."""
    tree.prove(A)
    tree.prove(T)
    tree.prove(ROOT, used=[A])
    assert tree.codes(tree.shelve(ALICE, A)) == ["node-used"]
    assert tree.codes(tree.shelve(ALICE, T)) == []


def test_a_route_that_is_not_the_nodes_is_refused(tree: Tree) -> None:
    change = tree.shelve(ALICE, A, scope="route", route=PARTIAL)
    assert tree.codes(change) == ["shelving-route-unknown"]


def test_a_second_shelved_record_on_a_shelved_node_is_an_append(tree: Tree) -> None:
    """Append-only, latest wins: the gate has no idempotence rule (the service does)."""
    tree.shelve(ALICE, A, date="2026-10-23T10:00:00Z")
    assert tree.codes(tree.shelve(CURATOR, A)) == []


def test_the_target_id_is_the_records(tree: Tree) -> None:
    change = tree.shelve(ALICE, A)
    assert change.path.startswith(f"targets/{TARGET}/nodes/{A}/shelving/")


# --- F31-T5 (R5, AC5): work on a shelved statement is refused before any sandbox ---------------

H1 = f"{A}--h1"
H2 = f"{A}--h2"
ROUTE1 = "attempts/20261020T000000Z-alice-partial.lean"


@pytest.fixture
def decomposed(tree: Tree) -> Tree:
    """``A`` decomposed into ``A--h1`` and ``A--h2``, then shelved: both holes inherit it."""
    tree.hole(H1, "h1", parent=A)
    tree.hole(H2, "h2", parent=A)
    tree.partial(A, ["h1", "h2"], path=ROUTE1)
    tree.shelve(ALICE, A)
    return tree


def rel(tree: Tree, node_id: str, name: str) -> str:
    return (tree.node_dir(node_id) / name).relative_to(tree.root).as_posix()


def test_a_witness_for_an_inherited_shelved_hole_is_refused(decomposed: Tree) -> None:
    """The hole's own slot is still a stub at the base; the completion would pass, and the
    shelving the hole inherits from ``A`` refuses it with the cause."""
    tree = decomposed
    path = rel(tree, H1, "Witness.lean")

    def base(rel_path: str) -> bytes | None:
        if rel_path == path:
            return b"theorem witness : True := sorry\n"
        return tree.base(rel_path)

    mode, codes = tree.check([paths.Change("M", path)], base=base)
    assert mode == "proposal"
    assert codes == ["node-shelved"]


def test_a_proof_a_partial_and_an_alternate_on_a_shelved_node_are_refused(
    decomposed: Tree,
) -> None:
    tree = decomposed
    (tree.node_dir(H1) / "Proof.lean").write_text("theorem x : True := trivial\n")
    assert tree.check([paths.Change("A", rel(tree, H1, "Proof.lean"))]) == (
        "proof",
        ["node-shelved"],
    )
    partial = rel(tree, H2, "attempts/20261024T000000Z-bob-partial.lean")
    (tree.root / partial).write_text("theorem x : True := by\n  sorry\n")
    assert tree.check([paths.Change("A", partial)]) == ("partial", ["node-shelved"])
    tree.prove(H2)  # an alternate needs a proved node; the shelving still refuses it
    alternate = rel(tree, H2, "attempts/20261024T000000Z-bob-alternate.lean")
    (tree.root / alternate).write_text("theorem x : True := ⟨⟩\n")
    mode, codes = tree.check([paths.Change("A", alternate)])
    assert mode == "alternate" and "node-shelved" in codes


def test_the_refusal_carries_the_cause_and_the_record(decomposed: Tree) -> None:
    tree = decomposed
    (tree.node_dir(H1) / "Proof.lean").write_text("theorem x : True := trivial\n")
    classification = modes.classify(
        [paths.Change("A", rel(tree, H1, "Proof.lean"))], author=SERVICE, graph_root=tree.root
    )
    (found,) = modes.check(tree.root, classification, base=tree.base)
    assert found.code == "node-shelved"
    assert found.details["shelved"]["via"] == A
    assert found.details["shelved"]["cause"] == "This branch does not serve the root."
    assert "This branch does not serve the root." in found.message


def test_a_proof_on_an_unshelved_sibling_passes(tree: Tree) -> None:
    """``A--h2`` carries its own ``unshelved`` record under a shelved ``A``."""
    tree.hole(H1, "h1", parent=A)
    tree.hole(H2, "h2", parent=A)
    tree.partial(A, ["h1", "h2"], path=ROUTE1)
    tree.shelve(ALICE, A)
    tree.shelve(ALICE, H2, action="unshelved")
    (tree.node_dir(H2) / "Proof.lean").write_text("theorem x : True := trivial\n")
    assert tree.check([paths.Change("A", rel(tree, H2, "Proof.lean"))]) == ("proof", [])
    (tree.node_dir(H1) / "Proof.lean").write_text("theorem x : True := trivial\n")
    assert tree.check([paths.Change("A", rel(tree, H1, "Proof.lean"))]) == (
        "proof",
        ["node-shelved"],
    )


def test_a_pull_requests_own_unshelve_does_not_lift_the_refusal(decomposed: Tree) -> None:
    """The refusal is judged on the parent tree: an ``unshelved`` record arriving beside the
    proof is not yet on the record (F31-Q8), so the proof is still refused."""
    tree = decomposed
    unshelve = tree.shelve(ALICE, H1, action="unshelved")
    (tree.node_dir(H1) / "Proof.lean").write_text("theorem x : True := trivial\n")
    mode, codes = tree.check([paths.Change("A", rel(tree, H1, "Proof.lean")), unshelve])
    assert mode == "proof" and codes == ["node-shelved"]


def test_a_proposed_for_pointer_at_a_shelved_node_is_refused(decomposed: Tree) -> None:
    """A proposal that attaches to a shelved statement (its ``proposed-for`` record names it)."""
    tree = decomposed
    pointer = tree.node_dir(T) / "proposed-for" / "20261024T120000Z-thisisanameforsure.yaml"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(
        yaml.safe_dump(
            {"schema": "proposed-for/v1", "for": H1, "author": CURATOR, "date": "2026-10-24"},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    change = paths.Change("A", pointer.relative_to(tree.root).as_posix())
    mode, codes = tree.check([change], opened_by=CURATOR)
    assert mode == "proposed-for" and codes == ["node-shelved"]
