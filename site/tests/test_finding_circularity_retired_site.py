"""F04-T53 (D-12, D-16, D-25 v3.43): nothing on the site marks circularity.

A ``circular-decomposition`` claim's exhibit proved *a proof of the hole is a proof of an
ancestor*, which every hole's merged assembly already proves, so the label separated nothing; and
the owner read its word, "proves an ancestor", as if the node had already proved it (2026-10-15).
Decisions v3.43 retire the claim and its label: the gate's refusal of a hole definitionally equal
to an ancestor is the whole rule. The products drop the field (``graph/v11``, ``frontier/v6``,
F08-T42), and the site draws, keys and says nothing of it — no key entry, no mark on the pill, no
chip on the row, no note on the page, no routes note, no ``data-circular``. An older snapshot
(``graph/v6``-``v9``) still carrying ``circular`` rows renders the same way: the field is ignored.
A merged claim of the class stays on the record as history, listed among the node's defect
claims (F08-T36) like any other.

The tests T37, T26 and T20 wrote for the label (``test_finding_circular_label``,
``test_finding_circular_key``, ``test_finding_circular_path_note``) are retired with it; their two
guards that are still true — every state a node can take is keyed, and every mark the drawing can
make is keyed (F18-AC5) — are restated at the end of this file without the label.
"""

from __future__ import annotations

import dataclasses
import inspect
import re
from pathlib import Path

import fixture
import pytest
import yaml
from harness import TARGET

from opn_gate import graph as gate_graph
from opn_gate import products
from opn_site import dag, model, one_view, render

REPO = "https://github.com/example/graph"
HOLE = fixture.HOLE
ANCESTOR = "and-swap-reassoc"
CLAIM_FILE = "20260923T120000Z-alice.yaml"
CLAIM_REF = f"{HOLE}/defects/{CLAIM_FILE}"  # relative to the target's nodes/
CLAIM = f"targets/{TARGET}/nodes/{CLAIM_REF}"
CLASS = "circular-decomposition"
CSS = (Path(render.__file__).resolve().parent / "static" / "site.css").read_text(encoding="utf-8")

#: Every page a circularity mark ever reached: the hole's and the ancestor's pages, the problem
#: page (graph, panels, routes), the listing's rows, and the Docs glossary.
PAGES = (
    f"nodes/{TARGET}/{HOLE}/index.html",
    f"nodes/{TARGET}/{ANCESTOR}/index.html",
    f"problems/{TARGET}/index.html",
    "problems/index.html",
    "docs/index.html",
)


def file_claim(root: Path) -> None:
    """A merged ``circular-decomposition`` claim on the hole, as the service filed the class
    (``defect-claim/v3``) before v3.43 retired it."""
    doc = {
        "schema": "defect-claim/v3",
        "stmt_ref": HOLE,
        "class": CLASS,
        "ancestor": ANCESTOR,
        "line": 1,
        "exhibit": "theorem circular : True → True := id\n",
        "contributor": "alice",
        "date": "2026-09-23",
    }
    path = root / CLAIM
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")


def claimed_tree(tmp_path: Path) -> Path:
    """The revised-hole fixture with the claim filed and the products rendered by today's gate
    (``graph/v10``, ``frontier/v6``)."""
    root = fixture.build_with_revised_hole(tmp_path)
    file_claim(root)
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    return root


def render_tree(root: Path) -> dict[str, str]:
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


@pytest.fixture(scope="module")
def current(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return render_tree(claimed_tree(tmp_path_factory.mktemp("retired-current")))


@pytest.fixture(scope="module")
def older(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """The same tree with its products lowered to ``graph/v9`` / ``frontier/v5``, the hole's
    row (and the frontier's entry) carrying the label the v3.35 gate wrote."""
    root = claimed_tree(tmp_path_factory.mktemp("retired-older"))
    fixture.publish_circular_snapshot(root, {HOLE: [{"ancestor": ANCESTOR, "claim": CLAIM_REF}]})
    return render_tree(root)


def marks(html: str) -> list[str]:
    """Every circularity mark the site ever drew, found in a page. The claim's class name is
    the record's word, not a mark, and is taken out first."""
    text = html.replace(CLASS, "")
    found = [
        needle
        for needle in (
            "proves an ancestor",
            "circular-mark",
            "circular-label",
            "circular-note",
            "data-circular",
            "dot-circular",
            'class="proves"',
            "labelled circular",
            "circularity claim",
            "A proof of this statement is a proof of",
        )
        if needle in text
    ]
    if re.search(r"circular", text, re.I):
        found.append("the word circular")
    for svg in re.findall(r"<svg.*?</svg>", html, re.S):
        if "⇒" in svg:
            found.append("⇒ in a drawing")
    return found


# --- the products' versions ---------------------------------------------------------------------


def test_the_site_accepts_the_versions_the_gate_writes() -> None:
    accepted = model.PRODUCT_SCHEMAS
    assert products.GRAPH_SCHEMA == "graph/v14"  # F08-T44 (v3.46): relation refutes
    assert products.FRONTIER_SCHEMA == "frontier/v8"
    assert products.GRAPH_SCHEMA in accepted["graph.json"]
    assert products.FRONTIER_SCHEMA in accepted["frontier.json"]
    # D-34: every older snapshot still renders.
    assert all(f"graph/v{n}" in accepted["graph.json"] for n in range(1, 10))
    assert all(f"frontier/v{n}" in accepted["frontier.json"] for n in range(1, 6))


# --- no mark, on any page, from either version --------------------------------------------------


@pytest.mark.parametrize("rel", PAGES)
def test_no_page_marks_circularity(current: dict[str, str], rel: str) -> None:
    assert marks(current[rel]) == [], rel


@pytest.mark.parametrize("rel", PAGES)
def test_an_older_snapshots_circular_rows_draw_nothing(older: dict[str, str], rel: str) -> None:
    """A ``graph/v9`` row carrying ``circular`` draws nothing of it."""
    assert marks(older[rel]) == [], rel


@pytest.mark.parametrize("rel", PAGES)
def test_an_older_snapshot_renders_as_the_current_one(
    current: dict[str, str], older: dict[str, str], rel: str
) -> None:
    """The field is ignored: the page is the current one's, byte for byte."""
    assert older[rel] == current[rel], rel


def test_the_model_carries_no_label(tmp_path: Path) -> None:
    root = claimed_tree(tmp_path)
    fixture.publish_circular_snapshot(root, {HOLE: [{"ancestor": ANCESTOR, "claim": CLAIM_REF}]})
    nv = model.load_site(root, fixture.COMMIT).targets[TARGET].nodes[HOLE]
    assert nv.graph_entry["circular"], "guard: the older row does carry the field"
    fields = {f.name for f in dataclasses.fields(model.NodeView)}
    assert not {"circular", "circular_below"} & fields
    assert not hasattr(model, "CircularLabel")


def test_the_key_and_the_glossary_name_no_label() -> None:
    assert "circular" not in render.GLOSSARY_BY_KEY
    assert not hasattr(render, "CIRCULAR_LABEL_WORD")
    assert not hasattr(dag, "circular_mark")
    assert "labelled" not in inspect.signature(dag.svg).parameters
    for selector in (".dot-circular", ".circular-mark", ".circular-label", ".circular-note"):
        assert selector not in CSS, selector
    assert ".stmt .proves" not in CSS


def test_the_routes_table_says_nothing_of_an_older_row() -> None:
    def row(node_id: str, deps: list[str], **extra: object) -> dict[str, object]:
        holes = [{"name": f"h{i + 1}", "node": d} for i, d in enumerate(deps)]
        return {
            "node_id": node_id,
            "status": "ready",
            "deps": deps,
            "origin": "skeleton-hole" if "--" in node_id else "authored",
            "relation": None,
            "decompositions": [
                {
                    "partial": "attempts/20261010T000000Z-a-partial.lean",
                    "annex": None,
                    "holes": holes,
                }
            ]
            if deps
            else [],
            **extra,
        }

    doc = {
        "schema": "graph/v9",
        "target_id": "t",
        "root": "t",
        "nodes": [
            row("t", ["t--h1"], circular=[]),
            row("t--h1", [], circular=[{"ancestor": "t", "claim": "t--h1/defects/x.yaml"}]),
        ],
    }
    picture = one_view.drawing(doc, [], href={}, prefix="t")
    html = picture.svg + picture.selector + picture.table
    assert "circular" not in html.lower(), html


# --- history, not a label -----------------------------------------------------------------------


def test_the_claim_is_still_listed_among_the_defect_claims(current: dict[str, str]) -> None:
    page = current[f"nodes/{TARGET}/{HOLE}/index.html"]
    section = page.split('class="defect-claims"', 1)
    assert len(section) == 2, "the hole's page lists no defect claim"
    listed = section[1].split("</div>", 1)[0]
    assert f"<code>{CLASS}</code>" in listed
    assert f"{REPO}/blob/{fixture.COMMIT}/{CLAIM}" in listed


def test_a_retired_class_claim_is_history_not_an_open_claim(current: dict[str, str]) -> None:
    """D-12 v3.43: a merged claim of the retired class says nothing about the statement, so the
    page lists it as history and never as a claim open against the statement."""
    page = current[f"nodes/{TARGET}/{HOLE}/index.html"]
    listed = page.split('class="defect-claims"', 1)[1].split("</div>", 1)[0]
    assert "open against this statement" not in listed
    assert "claim open" not in listed
    assert "retired" in listed and "history" in listed


# --- the guards T26 and F18 wrote that are still true, without the label ------------------------


def test_every_state_a_node_can_take_has_a_key_entry(tmp_path: Path) -> None:
    """Every word ``node_state`` returns, from any status with any cause the gate derives and
    the retired cause ``circular`` an older snapshot may carry (``graph/v3``-``v5`` take any
    cause word; D-34), has a glossary card and a place in the key."""
    root = fixture.build(tmp_path)
    nv = model.load_site(root, fixture.COMMIT).targets[TARGET].nodes[ANCESTOR]
    causes = [
        v for k, v in vars(gate_graph).items() if k.startswith("CAUSE_") and isinstance(v, str)
    ]
    missing = []
    for status in render.STATUS_WORDS:
        for cause in (None, *causes, render.RETIRED_CIRCULAR_CAUSE):
            entry = {**nv.graph_entry, "status": status, "cause": cause}
            state = render.Renderer.node_state(dataclasses.replace(nv, graph_entry=entry))
            keyed = state in (*render.DOTTED_KEYS, *render.LEGEND_EXTRA)
            if state not in render.GLOSSARY_BY_KEY or not keyed:
                missing.append((status, cause, state))
    assert not missing, missing


def test_the_retired_cause_changes_no_state() -> None:
    mark = render.Renderer.status_mark("ready", cause="circular")
    assert "open" in mark and "circular" not in mark, mark
    assert render.status_words("blocked", "circular") == render.STATUS_WORDS["blocked"]
    assert "circular" not in render.CAUSE_WORDS


def test_every_output_class_has_a_key_entry() -> None:
    """F18-AC5, restated by F30-T2: every mark the merged drawing can put on a pill or a line
    has a glossary card, a swatch in the stylesheet, and a place in the key."""
    source = (
        inspect.getsource(one_view._pill_markup)
        + inspect.getsource(one_view._junction_markup)
        + inspect.getsource(one_view._dag_svg)
        + inspect.getsource(dag.outline_mark)
        + inspect.getsource(dag.lines)
    )
    drawn = {
        '"edge"': "depends-on",
        "edge use": "use",
        "edge proposed": "proposed-for",
        "edge lemma": "lemma",
        "outline_mark": "outline",
        "and-mark": "route-and",
        "or-mark": "route-or",
        "dead-cross": "route-dead",
        '"asm"': "closable",
    }
    for cls, key in drawn.items():
        assert cls in source, f"the drawing no longer draws {cls}; update this guard"
        assert key in render.GLOSSARY_BY_KEY, key
        assert f".dot-{key}" in CSS, key
    keys_source = (
        inspect.getsource(render.Renderer.proof_legend)
        + inspect.getsource(render.Renderer.graph_legend)
        + " ".join(f'"{k}"' for k in render.ROUTE_MARK_KEYS)
    )
    for key in drawn.values():
        assert f'"{key}"' in keys_source, key
