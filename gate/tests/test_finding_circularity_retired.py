"""F08-T42 (D-12, D-16, D-25 v3.43): the circularity claim and its label are retired.

The owner's ruling of 2026-10-15. A ``circular-decomposition`` claim's exhibit proved that a proof
of a hole is a proof of an ancestor. That holds of every hole by construction: a merged assembly
proves its parent from its holes, so every hole of a one-hole decomposition, and the last open hole
of any decomposition once its siblings are proved, meets it. A test every hole can pass separates
nothing, so the label marked only the holes where someone had filed, and agents spent sessions
writing exhibits for it that proved no mathematics.

What remains is the mechanical rule: a hole definitionally equal to an ancestor is refused at the
gate (``offload-restates-ancestor``, unchanged and tested in
``test_finding_hole_restates_ancestor``). So, here:

- the products drop the field: ``graph/v10``, ``frontier/v6`` and ``context/v8`` carry neither
  ``circular`` nor ``circular_below``, and the older versions stay as they were (D-34);
- a merged claim of the retired class changes no status, cause, frontier entry or claimability
  anywhere on its path, and stays in the record as history — ``defect_claims`` still lists it, as
  it lists every claim filed against the node (F08-T36);
- a new claim of the class, or an ``ancestor`` on any claim, is refused ``defect-class-retired``
  by the classifier and by the exhibit step, which no longer judges an implication;
- the codes that only the retired check emitted are gone from the registry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import samples
import yaml
from fakes import FakeToolchain
from harness import TARGET, copy_graph
from test_postmerge import ASSEMBLY, HOLES, PSEUDONYM
from test_products import attest

from opn_gate import codes, config, exhibits, layout, modes, postmerge, products, schemas
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext

RETIRED = "defect-class-retired"
RENDERED = "5" * 40
NOW = "2026-10-15T12:00:00Z"

HOLE = "and-reassoc"
ANCESTOR = "and-swap-reassoc"  # the fixture's root; it depends on the hole
ONE_HOLE_CLAIM = f"targets/{TARGET}/nodes/{HOLE}/defects/20261015T120000Z-alice.yaml"
#: ``hole → ancestor``, the implication the retired class asked for (v3.23).
EXHIBIT = (
    "theorem circular :\n"
    "    (∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r)) →\n"
    "    ∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p) :=\n"
    "  fun _ _ _ _ h => ⟨h.2, h.1.2, h.1.1⟩\n"
)

# erdos-69's live shape: the root decomposed three levels deep, every sibling on the way proved,
# a claim on the deepest hole naming the root — v3.22's path rule labelled MID and LOW.
ROOT = "and-swap-reassoc"
MID = f"{ROOT}--h2"
LOW = f"{MID}--h1"
DEEP = f"{LOW}--h2"
SIBLINGS = (f"{ROOT}--h1", f"{MID}--h2", f"{LOW}--h1")
PATH_CLAIM = f"targets/{TARGET}/nodes/{DEEP}/defects/20260924T123647Z-alice.yaml"

RETIRED_FIELDS = {"circular", "circular_below"}


def claim_doc(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "defect-claim/v3",
        "stmt_ref": HOLE,
        "class": "circular-decomposition",
        "ancestor": ANCESTOR,
        "line": 1,
        "exhibit": EXHIBIT,
        "contributor": "alice",
        "date": "2026-10-15",
    }
    doc.update(overrides)
    return {k: v for k, v in doc.items() if v is not None}


def file_claim(root: Path, rel: str = ONE_HOLE_CLAIM, **overrides: Any) -> str:
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


def exhibit_codes(root: Path, rel: str, fake: FakeToolchain) -> list[str]:
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


def generate(root: Path) -> products.Products:
    return products.generate(root, rendered_from=RENDERED, commit_time=NOW)


def docs(prod: products.Products) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """``graph.json``, ``frontier.json`` and every ``CONTEXT.json`` of the fixture's target."""
    gdoc = json.loads(prod.files[Path("targets") / TARGET / "graph.json"])
    fdoc = json.loads(prod.files[Path("frontier.json")])
    bundles = [json.loads(data) for rel, data in prod.files.items() if rel.name == "CONTEXT.json"]
    return gdoc, fdoc, bundles


def facts(prod: products.Products) -> dict[str, tuple[Any, ...]]:
    """What a node *is* on the record: graph row status and cause, frontier entry and its
    claimability and needs. A retired claim must move none of it."""
    gdoc, fdoc, _ = docs(prod)
    entries = {e["node_id"]: e for e in fdoc["entries"]}
    return {
        n["node_id"]: (
            n["status"],
            n["cause"],
            n["node_id"] in entries,
            entries.get(n["node_id"], {}).get("claimable"),
            entries.get(n["node_id"], {}).get("needs"),
        )
        for n in gdoc["nodes"]
    }


def nodes_dir(root: Path) -> Path:
    return root / "targets" / TARGET / "nodes"


def prove(root: Path, node_id: str, n: int) -> None:
    node = nodes_dir(root) / node_id
    text = (node / "Statement.lean").read_text(encoding="utf-8")
    (node / "Proof.lean").write_text(text.replace("sorry", "exact trivial"), encoding="utf-8")
    attest(root, node_id, n=n)


def chain(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path, publish=True)
    (nodes_dir(root) / ROOT / "Proof.lean").unlink()  # the root is open
    attest(root, "tutorial-and-swap", n=1)
    attest(root, "and-reassoc", n=2)
    for i, parent in enumerate((ROOT, MID, LOW)):
        postmerge.apply_partial(
            nodes_dir(root) / parent,
            HOLES,
            partial_text=ASSEMBLY,
            pseudonym=PSEUDONYM,
            stamp=f"2026091{i}T121314Z",
        )
    for n, sibling in enumerate(SIBLINGS, start=3):
        prove(root, sibling, n)
    status = root / "targets" / TARGET / "status"
    status.mkdir()
    (status / "2026-09-10-1.yaml").write_text(
        yaml.safe_dump(samples.target_status(root=ROOT)), encoding="utf-8"
    )
    return root


# --- the products drop the field ------------------------------------------------------------------


def test_the_products_are_the_next_versions_without_the_field(tmp_path: Path) -> None:
    root = chain(tmp_path)
    file_claim(root, PATH_CLAIM, stmt_ref=DEEP, ancestor=ROOT)
    gdoc, fdoc, bundles = docs(generate(root))
    assert (gdoc["schema"], fdoc["schema"]) == ("graph/v14", "frontier/v8")
    assert {b["schema"] for b in bundles} == {"context/v10"}
    for doc in (gdoc, fdoc, *bundles):
        assert schemas.violations(doc, doc["schema"]) == [], doc["schema"]
    for row in (*gdoc["nodes"], *fdoc["entries"], *bundles):
        assert not RETIRED_FIELDS & set(row), row["node_id"]


def test_the_new_schemas_publish_no_circularity_field() -> None:
    for schema_id in ("graph/v14", "frontier/v8", "context/v10"):
        text = json.dumps(schemas.load_schema(schema_id)["properties"])
        assert '"circular"' not in text and '"circular_below"' not in text, schema_id


# --- a merged claim of the retired class is history, nothing more ---------------------------------


def test_a_merged_claim_on_a_path_moves_no_fact(tmp_path: Path) -> None:
    """The live erdos-69 shape: under v3.22 to v3.41 the claim labelled DEEP, LOW and MID and named
    itself on the root's ``circular_below``. Now every node's status, cause, frontier membership,
    claimability and needs are what they are without the claim."""
    root = chain(tmp_path)
    before = facts(generate(root))
    file_claim(root, PATH_CLAIM, stmt_ref=DEEP, ancestor=ROOT)
    assert facts(generate(root)) == before


def test_a_merged_claim_stays_listed_as_history(tmp_path: Path) -> None:
    """Derive, never rewrite: the file stays under the hole's ``defects/``, and the list of claims
    filed against the node (F08-T36) still names it with its class."""
    root = copy_graph(tmp_path, publish=True)
    file_claim(root)
    gdoc, _, _ = docs(generate(root))
    [row] = [n for n in gdoc["nodes"] if n["node_id"] == HOLE]
    listed = [(c["file"], c["class"], c["state"]) for c in row["defect_claims"]]
    assert ("defects/20261015T120000Z-alice.yaml", "circular-decomposition", "standing") in listed


# --- a new claim of the class is refused ----------------------------------------------------------


def test_a_new_circularity_claim_is_refused_as_retired(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    rel = file_claim(root)
    assert check_codes(root, rel) == [RETIRED]


def test_an_ancestor_on_any_claim_is_refused_as_retired(tmp_path: Path) -> None:
    """``ancestor`` belonged to the retired class alone; on any other class it claims something
    nobody checks."""
    root = copy_graph(tmp_path)
    other: dict[str, Any] = {"class": "missing-hypothesis"}
    rel = file_claim(root, **other)
    assert check_codes(root, rel) == [RETIRED]


def test_an_ordinary_claim_is_still_accepted(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    plain: dict[str, Any] = {"class": "missing-hypothesis", "ancestor": None}
    rel = file_claim(root, **plain)
    assert check_codes(root, rel) == []


def test_the_exhibit_step_judges_no_implication(tmp_path: Path) -> None:
    """The exhibit step refuses the class too, and asks the toolchain nothing about it."""
    root = copy_graph(tmp_path)
    rel = file_claim(root)
    fake = FakeToolchain()
    assert exhibit_codes(root, rel, fake) == [RETIRED]
    assert not [c for c in fake.calls if c.startswith("relation")]


# --- the registry ---------------------------------------------------------------------------------


def test_the_retired_codes_are_gone_and_the_new_one_is_registered() -> None:
    known = set(codes.CATALOG)
    assert RETIRED in known
    gone = {
        "circular-ancestor",
        "circular-axiom",
        "circular-direction",
        "circular-elaboration",
        "circular-exhibit",
        "circular-sorry",
        "node-circular",
    }
    assert not gone & known


# --- F28's closer has no claim link ---------------------------------------------------------------


def test_the_closer_takes_no_link_from_a_claim() -> None:
    """F28 (v3.41) closed an ancestor through a merged claim's exhibit once the claimed hole was
    proved. v3.42 dropped that link (F28-Q12) and v3.43 the class: an older graph's ``circular``
    rows join nothing, and a proved hole closes what it was cut from only through a route."""
    from opn_gate import closing  # noqa: PLC0415 — the one test that reads it

    graph_doc = {
        "schema": "graph/v9",
        "target_id": "t",
        "root": "p",
        "nodes": [
            {
                "node_id": "p",
                "status": "ready",
                "deps": [],
                "origin": "authored",
                "decompositions": [],
            },
            {
                "node_id": "q",
                "status": "proved",
                "deps": [],
                "origin": "authored",
                "decompositions": [],
                "circular": [{"ancestor": "p", "claim": "q/defects/x.yaml"}],
            },
        ],
    }
    assert closing.links(graph_doc)["p"] == []
    assert closing.closable(graph_doc) == ()
