"""Finding 2 (2026-09-13, the live MCP contribution; 2026-09-12 finding 5 re-found): the graph
publishes 4 of the 27 schema families ``info.json`` advertises, so ``get_schema`` answers
not-found for most of the names the index lists.

``info.json``'s schema index is F03-R10's "name → versions". The adapter's ``get_schema`` reads
``schemas/<name>/v<n>.json`` from the graph (``api/opn_api/mcp/reads.py``: the plain path is the
same file, the bijection), and D-34 says a published schema is versioned and never edited. Today
``products.generate`` builds the index from the network's registry (``schemas.known_schemas()``)
and never asks whether the graph carries the files, so the index advertises what the graph does
not hold; the fixture graphs carry no ``schemas/`` at all and every products test passes.

Each test asserts the behaviour F03-T6 lands: ``generate`` refuses a graph whose ``schemas/`` lacks
an advertised family, naming ``schema-unpublished`` and the family as ``<name>/v<n>``; and a new
``opn_gate.schemas.publish(graph_root)`` seeds a graph so that the index and the files agree, with
a ``HASHES`` pin per file. Held as strict xfails until the task lands (conventions §2); the helper
is looked up with ``getattr`` so a missing name is a failed test, never a collection error.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from harness import copy_graph

from opn_gate import graph as graphmod
from opn_gate import products, schemas

RENDERED_FROM = "5" * 40
COMMIT_TIME = "2026-09-13T00:00:00Z"
#: What the live graph holds at origin/main on 2026-09-13 (``git ls-tree origin/main schemas/``).
LIVE_GRAPH_HOLDS = ("attestation/v1", "attestation/v2", "gate-spec/v1", "meta/v1")
FAMILY_RE = re.compile(r"[a-z][a-z0-9-]*/v[1-9][0-9]*")
FINDING = "finding 2 (F03-R10, D-34; 2026-09-12 finding 5): "
FIX = "; fix: F03-T6 (Mike, 2026-09-13)"


def generate(root: Path) -> products.Products:
    return products.generate(root, rendered_from=RENDERED_FROM, commit_time=COMMIT_TIME)


def advertised(prod: products.Products) -> dict[str, list[int]]:
    """The schema index info.json carries (F03-R10)."""
    info = json.loads(prod.files[Path("info.json")])
    index: dict[str, list[int]] = info["schemas"]
    return index


def publish_by_hand(root: Path, schema_ids: tuple[str, ...]) -> None:
    """Copy the named registry files into the graph at the path get_schema reads."""
    for schema_id in schema_ids:
        source = schemas.schema_path(schema_id)
        assert source.is_file(), schema_id  # setup guard: the registry holds it
        dest = root / "schemas" / f"{schema_id}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source.read_bytes())


def families_named(message: str) -> set[str]:
    """Every ``<name>/v<n>`` a refusal names, whole tokens only (``meta/v1`` is a substring of
    ``submission-meta/v1``, so a plain ``in`` check would lie)."""
    return set(FAMILY_RE.findall(message))


@pytest.mark.xfail(
    strict=True,
    reason=FINDING
    + "products.generate builds info.json's schema index from the network registry and never "
    + "checks the graph's schemas/ holds the files, so a graph publishing none passes"
    + FIX,
)
def test_generate_refuses_a_graph_that_publishes_none_of_the_schemas_it_advertises(
    tmp_path: Path,
) -> None:
    """A graph with no ``schemas/`` directory advertises 27 families it cannot serve; the
    products refuse it and the refusal names the problem and at least one family."""
    root = copy_graph(tmp_path)
    assert not (root / "schemas").exists()  # setup guard: the fixture publishes nothing
    with pytest.raises(graphmod.GraphError, match="schema-unpublished") as excinfo:
        generate(root)
    named = families_named(str(excinfo.value))
    assert named & set(schemas.known_schemas()), str(excinfo.value)


@pytest.mark.xfail(
    strict=True,
    reason=FINDING
    + "products.generate accepts the live graph's shape (4 of 27 families published) and "
    + "advertises all 27, so get_schema answers not-found for the 23 the index lists"
    + FIX,
)
def test_the_refusal_names_the_families_the_graph_lacks_and_not_the_ones_it_holds(
    tmp_path: Path,
) -> None:
    """The live shape: four files under ``schemas/``. The refusal names a family the graph
    lacks (``annex/v1``) and none of the four it holds."""
    root = copy_graph(tmp_path)
    publish_by_hand(root, LIVE_GRAPH_HOLDS)
    with pytest.raises(graphmod.GraphError, match="schema-unpublished") as excinfo:
        generate(root)
    named = families_named(str(excinfo.value))
    assert "annex/v1" in named, str(excinfo.value)
    assert named.isdisjoint(LIVE_GRAPH_HOLDS), str(excinfo.value)


@pytest.mark.xfail(
    strict=True,
    reason=FINDING
    + "opn_gate.schemas has no publish(graph_root) helper, so nothing seeds a graph's schemas/ "
    + "from the registry and no fixture or re-pin can make the index and the files agree"
    + FIX,
)
def test_publish_seeds_every_advertised_family_with_a_pin_and_generate_passes(
    tmp_path: Path,
) -> None:
    """``schemas.publish(graph_root)`` copies every registry family to
    ``schemas/<name>/v<n>.json`` — the path ``get_schema`` reads for ``<name>/v<n>`` — byte for
    byte (D-34), writes one ``HASHES`` line per file that ``verify_pins`` accepts, is idempotent
    (adds versions, never edits), and leaves a graph whose ``info.json`` index equals what is on
    disk, so ``generate`` passes."""
    root = copy_graph(tmp_path)
    publish = getattr(schemas, "publish", None)
    assert publish is not None, "opn_gate.schemas.publish(graph_root) does not exist"
    publish(root)

    graph_schemas = root / "schemas"
    for schema_id in schemas.known_schemas():
        copy = graph_schemas / f"{schema_id}.json"
        assert copy.is_file(), f"{schema_id} is advertised and not published at {copy}"
        assert copy.read_bytes() == schemas.schema_path(schema_id).read_bytes(), schema_id
    hashes = graph_schemas / "HASHES"
    assert hashes.is_file(), "publish wrote no HASHES"
    assert schemas.read_pins(hashes) == schemas.compute_hashes(graph_schemas)
    assert schemas.verify_pins(graph_schemas, hashes) == []

    before = {p: p.read_bytes() for p in graph_schemas.rglob("*") if p.is_file()}
    publish(root)  # D-34: a second publish edits nothing
    assert {p: p.read_bytes() for p in graph_schemas.rglob("*") if p.is_file()} == before

    on_disk: dict[str, list[int]] = {}
    for path in sorted(graph_schemas.glob("*/v*.json")):
        on_disk.setdefault(path.parent.name, []).append(int(path.stem[1:]))
    prod = generate(root)
    assert advertised(prod) == {name: sorted(versions) for name, versions in on_disk.items()}
