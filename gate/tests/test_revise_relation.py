"""F08-T46 (D-8 v3.46): a revision may carry a relation, and keeps its routes by derivation.

A proposed crux (D-14 v3.26) with a merged partial becomes a ``refutes`` variant (D-30 v3.46)
through ``opn-gate revise --relation refutes --relation-proof <file>`` with its statement
unchanged. Nothing is copied or rewritten: a revision whose statement is the superseded node's
(the same text, the one line naming its own Context aside) reads that node's merged partials
and hole children as its own — in ``NodeFacts``, in ``blocked_because`` (so the revision is not
blocked on holes it never waits on), in ``graph.json``'s ``decompositions`` and so in the
routes — and a revision with a changed statement inherits none of it, as before.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from harness import TARGET, copy_graph
from test_curator import AUTHOR, DATE, INTERIOR, ROOT, attest_proved, write_request
from test_decompositions import ANNEX, HOLE_IDS, PARTIAL, add_hole, merged_partial
from test_products import generate, loads, nodes_dir

from opn_gate import cli, curator, layout, products, routes, scaffold, schemas
from opn_gate import graph as graphmod

TUTORIAL = "tutorial-and-swap"
REFUTES_PROOF = (
    "theorem relation :\n"
    "    (∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r)) →\n"
    "    ¬(∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p)) := by\n"
    "  sorry\n"
)


def same_statement(root: Path, node_id: str, new_id: str) -> str:
    """The node's statement with only its own Context import renamed: what ``revise`` is
    handed when the statement is unchanged (D-8 v3.46)."""
    text = (nodes_dir(root) / node_id / "Statement.lean").read_text(encoding="utf-8")
    own = f"import {layout.node_module(node_id, 'Context')}"
    # A statement merged before F08-T13 may carry no own-Context import; it is then byte for
    # byte the same text.
    return text.replace(own, f"import {layout.node_module(new_id, 'Context')}")


def decomposed_root(tmp_path: Path) -> Path:
    """The fixture root, its two deps proved, with a merged partial that made two holes."""
    root = copy_graph(tmp_path, publish=True)
    # The live crux has no Proof.lean: with the fixture's in place, the partial's passing
    # attestation would be read as the root's proof (F03-Q7 reads both together).
    (nodes_dir(root) / ROOT / "Proof.lean").unlink()
    attest_proved(root, TUTORIAL, 1)
    attest_proved(root, INTERIOR, 2)
    add_hole(root, HOLE_IDS[0], "hden")
    add_hole(root, HOLE_IDS[1], "hrem")
    merged_partial(root, 7, ["hden", "hrem"])
    tg = graphmod.load_target(root, TARGET)
    assert tg.statuses[ROOT] == "ready", tg.statuses
    assert tg.nodes[ROOT].holes == HOLE_IDS
    return root


def row_of(root: Path, node_id: str) -> dict[str, object]:
    tg = graphmod.load_target(root, TARGET)
    doc = schemas.validate(products.graph_doc(tg, None), products.GRAPH_SCHEMA)
    [row] = [n for n in doc["nodes"] if n["node_id"] == node_id]
    return dict(row)


# --- revise --relation ---------------------------------------------------------------------------


def test_a_revision_may_carry_a_relation_and_its_proof(tmp_path: Path) -> None:
    """D-8 v3.46: with ``relation`` and its proof, the revision is scaffolded a variant with
    that Relation.lean, the label line written by the scaffold (F08-Q6)."""
    root = copy_graph(tmp_path)
    request = write_request(root, INTERIOR)
    revision = curator.revise(
        root,
        TARGET,
        INTERIOR,
        same_statement(root, INTERIOR, f"{INTERIOR}-v2"),
        request,
        author=AUTHOR,
        date=DATE,
        relation="refutes",
        relation_proof=REFUTES_PROOF,
    )
    new_dir = nodes_dir(root) / revision.new_id
    assert layout.validate_node(new_dir) == []
    meta = yaml.safe_load((new_dir / "META.yaml").read_text())
    assert meta["origin"] == "variant"
    assert meta["supersedes"] == INTERIOR
    relation = (new_dir / scaffold.RELATION_FILE).read_text(encoding="utf-8")
    assert relation == scaffold.with_relation_label(REFUTES_PROOF, "refutes")
    assert graphmod.relation_of(new_dir, "variant") == "refutes"
    assert f"targets/{TARGET}/nodes/{revision.new_id}/Relation.lean" in revision.written
    # The old node is untouched beyond its status record (D-3, D-8).
    assert not (nodes_dir(root) / INTERIOR / scaffold.RELATION_FILE).exists()


def test_a_label_that_claims_something_needs_its_proof(tmp_path: Path) -> None:
    """A label above ``related`` without a file is refused by name, and nothing is written."""
    root = copy_graph(tmp_path)
    request = write_request(root, INTERIOR)
    before = sorted(p.as_posix() for p in root.rglob("*"))
    with pytest.raises(curator.CuratorError, match="relation proof"):
        curator.revise(
            root,
            TARGET,
            INTERIOR,
            same_statement(root, INTERIOR, f"{INTERIOR}-v2"),
            request,
            author=AUTHOR,
            date=DATE,
            relation="refutes",
        )
    assert sorted(p.as_posix() for p in root.rglob("*")) == before
    with pytest.raises(curator.CuratorError, match="relation"):
        curator.revise(
            root,
            TARGET,
            INTERIOR,
            same_statement(root, INTERIOR, f"{INTERIOR}-v2"),
            request,
            author=AUTHOR,
            date=DATE,
            relation="sideways",
            relation_proof=REFUTES_PROOF,
        )
    assert sorted(p.as_posix() for p in root.rglob("*")) == before


def test_related_needs_no_proof_and_no_relation_is_as_today(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    request = write_request(root, INTERIOR)
    revision = curator.revise(
        root,
        TARGET,
        INTERIOR,
        same_statement(root, INTERIOR, f"{INTERIOR}-v2"),
        request,
        author=AUTHOR,
        date=DATE,
        relation="related",
    )
    new_dir = nodes_dir(root) / revision.new_id
    assert yaml.safe_load((new_dir / "META.yaml").read_text())["origin"] == "variant"
    assert not (new_dir / scaffold.RELATION_FILE).exists()

    plain = curator.revise(
        root,
        TARGET,
        revision.new_id,
        same_statement(root, revision.new_id, f"{INTERIOR}-v3"),
        write_request(root, revision.new_id),
        author=AUTHOR,
        date="2026-10-21T00:00:02Z",  # a second stale record on the root needs its own second
    )
    plain_dir = nodes_dir(root) / plain.new_id
    # Without the flags, as today: the origin and the relation are the old node's.
    assert yaml.safe_load((plain_dir / "META.yaml").read_text())["origin"] == "variant"
    assert not (plain_dir / scaffold.RELATION_FILE).exists()


def test_the_command_takes_the_relation_flags(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_graph(tmp_path)
    request = write_request(root, INTERIOR)
    statement = tmp_path / "Statement.lean"
    statement.write_text(same_statement(root, INTERIOR, f"{INTERIOR}-v2"), encoding="utf-8")
    proof = tmp_path / "Relation.lean"
    proof.write_text(REFUTES_PROOF, encoding="utf-8")
    code = cli.main(
        [
            "revise",
            "--graph",
            str(root),
            "--author",
            AUTHOR,
            "--date",
            DATE,
            INTERIOR,
            "--statement",
            str(statement),
            "--request",
            str(request),
            "--relation",
            "refutes",
            "--relation-proof",
            str(proof),
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["ok"], out
    assert graphmod.relation_of(nodes_dir(root) / out["revision"], "variant") == "refutes"

    code = cli.main(
        [
            "revise",
            "--graph",
            str(root),
            "--author",
            AUTHOR,
            "--date",
            "2026-10-21T00:00:01Z",
            out["revision"],
            "--statement",
            str(statement),
            "--request",
            str(write_request(root, out["revision"])),
            "--relation",
            "refutes",
        ]
    )
    refused = json.loads(capsys.readouterr().out)
    assert code == 1 and not refused["ok"] and "relation proof" in refused["refused"], refused


# --- routes inherited by derivation (D-8 v3.46) -------------------------------------------------


def test_a_same_statement_revision_reads_the_old_nodes_partials_and_holes(
    tmp_path: Path,
) -> None:
    """The revision's row carries the superseded node's decompositions with the holes resolved,
    its status is ``ready`` (not blocked on four deps), and the holes are its children."""
    root = decomposed_root(tmp_path)
    request = write_request(root, ROOT)
    revision = curator.revise(
        root,
        TARGET,
        ROOT,
        same_statement(root, ROOT, f"{ROOT}-v2"),
        request,
        author=AUTHOR,
        date=DATE,
    )
    new_id = revision.new_id
    tg = graphmod.load_target(root, TARGET)
    node = tg.nodes[new_id]
    assert node.holes == HOLE_IDS
    assert [p.path for p in node.partials] == [PARTIAL]
    assert tg.statuses[new_id] == "ready", tg.statuses
    assert tg.statuses[ROOT] == "superseded"
    blocked, cause = graphmod.blocked_because(node, lambda n: tg.statuses[n])
    assert (blocked, cause) == (False, None)
    for hole in HOLE_IDS:
        assert graphmod.is_hole_child(nodes_dir(root), new_id, hole)

    row = row_of(root, new_id)
    assert row["status"] == "ready"
    assert row["decompositions"] == [
        {
            "partial": PARTIAL,
            "annex": ANNEX,
            "holes": [{"name": "hden", "node": HOLE_IDS[0]}, {"name": "hrem", "node": HOLE_IDS[1]}],
            "approach": "an outline",
        }
    ]
    # The old node's row is what it was: nothing rewritten (D-3, D-8).
    assert row_of(root, ROOT)["decompositions"] == row["decompositions"]


def test_the_routes_list_one_route_for_the_revision(tmp_path: Path) -> None:
    root = decomposed_root(tmp_path)
    revision = curator.revise(
        root,
        TARGET,
        ROOT,
        same_statement(root, ROOT, f"{ROOT}-v2"),
        write_request(root, ROOT),
        author=AUTHOR,
        date=DATE,
    )
    prod = generate(root)
    doc = loads(prod, f"targets/{TARGET}/graph.json")
    entries = loads(prod, "frontier.json")["entries"]
    found = routes.read(doc, entries)
    mine = [r for r in found.routes if r.node == revision.new_id]
    assert len(mine) == 1, [r.id for r in found.routes]
    assert mine[0].partial == PARTIAL
    assert [h.node for h in mine[0].holes] == list(HOLE_IDS)


def test_a_changed_statement_inherits_nothing(tmp_path: Path) -> None:
    root = decomposed_root(tmp_path)
    changed = same_statement(root, ROOT, f"{ROOT}-v2").replace("r ∧ (q ∧ p)", "(q ∧ p) ∧ r")
    revision = curator.revise(
        root, TARGET, ROOT, changed, write_request(root, ROOT), author=AUTHOR, date=DATE
    )
    tg = graphmod.load_target(root, TARGET)
    node = tg.nodes[revision.new_id]
    assert node.holes == () and node.partials == ()
    assert tg.statuses[revision.new_id] == "blocked"  # the copied deps are deps, not holes
    assert row_of(root, revision.new_id)["decompositions"] == []
    assert not graphmod.is_hole_child(nodes_dir(root), revision.new_id, HOLE_IDS[0])


def test_inheritance_follows_the_supersedes_chain(tmp_path: Path) -> None:
    """A revision of a revision, each with the statement unchanged, reads the first node's."""
    root = decomposed_root(tmp_path)
    v2 = curator.revise(
        root,
        TARGET,
        ROOT,
        same_statement(root, ROOT, f"{ROOT}-v2"),
        write_request(root, ROOT),
        author=AUTHOR,
        date=DATE,
    )
    v3 = curator.revise(
        root,
        TARGET,
        v2.new_id,
        same_statement(root, v2.new_id, f"{ROOT}-v3"),
        write_request(root, v2.new_id),
        author=AUTHOR,
        date="2026-10-21T00:00:02Z",
    )
    tg = graphmod.load_target(root, TARGET)
    assert tg.nodes[v3.new_id].holes == HOLE_IDS
    assert [p.path for p in tg.nodes[v3.new_id].partials] == [PARTIAL]
    assert tg.statuses[v3.new_id] == "ready"
    assert graphmod.is_hole_child(nodes_dir(root), v3.new_id, HOLE_IDS[1])


# --- acknowledged hazards (F08-T47) --------------------------------------------------------------

ACK = {
    "checker": "div-zero",
    "location": "1 / (2 ^ ↑n - 1)",
    "justification": "Real division; the junk value at n = 0 does not change the statement.",
}


def _acknowledge(root: Path, node_id: str) -> None:
    meta_path = nodes_dir(root) / node_id / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta["acknowledged_hazards"] = [ACK]
    if meta.get("schema") == "meta/v1":  # the fixture predates the field (meta/v2, F02-R6)
        meta["schema"] = "meta/v2"
    meta_path.write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), "utf-8")


def test_a_same_statement_revision_carries_the_acknowledged_hazards(tmp_path: Path) -> None:
    """F08-T47 (found live, graph PR #801): the revision of spec-a70fcca4 restated the same
    proposition and admission refused it ``hazard-unacknowledged`` for the very division the
    superseded node had acknowledged, because ``revise`` copied deps, origin, relation and
    witness but not the acknowledgements. The same statement carries the same reading."""
    root = copy_graph(tmp_path)
    _acknowledge(root, INTERIOR)
    revision = curator.revise(
        root,
        TARGET,
        INTERIOR,
        same_statement(root, INTERIOR, f"{INTERIOR}-v2"),
        write_request(root, INTERIOR),
        author=AUTHOR,
        date=DATE,
        relation="refutes",
        relation_proof=REFUTES_PROOF,
    )
    new_dir = nodes_dir(root) / revision.new_id
    meta = yaml.safe_load((new_dir / "META.yaml").read_text(encoding="utf-8"))
    assert meta.get("acknowledged_hazards") == [ACK]
    assert layout.validate_node(new_dir) == []


def test_a_changed_statement_carries_no_acknowledgement(tmp_path: Path) -> None:
    """An acknowledgement names a location in a statement; a changed statement is read anew,
    so its hazards are acknowledged by whoever proposes it, never inherited."""
    root = decomposed_root(tmp_path)
    _acknowledge(root, ROOT)
    changed = same_statement(root, ROOT, f"{ROOT}-v2").replace("r ∧ (q ∧ p)", "(q ∧ p) ∧ r")
    revision = curator.revise(
        root, TARGET, ROOT, changed, write_request(root, ROOT), author=AUTHOR, date=DATE
    )
    meta = yaml.safe_load(
        (nodes_dir(root) / revision.new_id / "META.yaml").read_text(encoding="utf-8")
    )
    assert "acknowledged_hazards" not in meta
