"""F04-T26 (Q28), restated for D-12 v3.35 (F04-T37): the circularity label is drawn, keyed and
defined as a label, never as a state.

The finding (2026-09-24, the erdos-1050 MCP tester): the problem page called a hole "circular"
and the key did not say what that meant; T26 made ``circular`` a state with its own dotted red
ring. Decisions v3.35 retire the state: a merged ``circular-decomposition`` claim labels the hole
(*a proof of this statement is a proof of <ancestor>*) and the hole keeps its status and its
claimability. So the pill wears its status, a labelled pill carries a small mark, the key names
the mark whenever a statement in the graph carries the label (Q16: a key names every mark the
drawing can show), the glossary defines it as a fact, and the Docs state map lists states only.
"""

from __future__ import annotations

import dataclasses
import inspect
import re
from pathlib import Path
from typing import Any

import fixture

from opn_gate import graph as gate_graph
from opn_site import dag, model, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"
ROOT = "and-swap-reassoc"
DEP = "and-reassoc"
CLAIM_REF = f"{DEP}/defects/20260924T120000Z-alice.yaml"
CSS = (Path(render.__file__).resolve().parent / "static" / "site.css").read_text(encoding="utf-8")
LABEL_WORD = "proves an ancestor"


def site_and_target(tmp_path: Path) -> tuple[Any, Any]:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    return site, site.targets[TARGET]


def labelled_page(tmp_path: Path, node_id: str = DEP) -> str:
    """The fixture's problem page with one node carrying a circularity label (``graph/v6``)."""
    root = fixture.build(tmp_path)
    fixture.publish_v335(root, circular={node_id: [{"ancestor": ROOT, "claim": CLAIM_REF}]})
    site = model.load_site(root, fixture.COMMIT)
    r = render.Renderer(site, repo_url=REPO, decisions_doc=None)
    return r.target(site.targets[TARGET])


def legend_words(html: str) -> list[str]:
    m = re.search(r'<div class="dag-legend">(.*?)</div>', html, re.S)
    assert m is not None, "the problem page has no graph key"
    return re.findall(
        r'<span class="dot dot-[a-z-]+"></span>([a-z ]+)<span class="term-card"', m.group(1)
    )


def gate_causes() -> list[str]:
    return [v for k, v in vars(gate_graph).items() if k.startswith("CAUSE_") and isinstance(v, str)]


def test_every_state_a_node_can_take_has_a_key_entry(tmp_path: Path) -> None:
    """Every word ``node_state`` can return, from any status the gate publishes with any cause it
    derives (the retired ``circular`` included, D-34), has a glossary card and a place in the
    key: the guard the status-only test missed."""
    _site, tv = site_and_target(tmp_path)
    nv = tv.nodes[ROOT]
    missing = []
    for status in render.STATUS_WORDS:
        for cause in (None, *gate_causes(), "circular"):
            entry = {**nv.graph_entry, "status": status, "cause": cause}
            state = render.Renderer.node_state(dataclasses.replace(nv, graph_entry=entry))
            keyed = state in (*render.DOTTED_KEYS, *render.LEGEND_EXTRA)
            if state not in render.GLOSSARY_BY_KEY or not keyed:
                missing.append((status, cause, state))
    assert not missing, missing


def test_circular_is_not_a_state(tmp_path: Path) -> None:
    """The key's status entries and the Docs state map list states; the label is not one."""
    assert "circular" not in render.LEGEND_EXTRA
    assert "circular" not in render.STATE_MAP_STATEMENT_KEYS
    _site, tv = site_and_target(tmp_path)
    nv = tv.nodes[DEP]
    entry = {**nv.graph_entry, "status": "ready", "cause": None, "circular": [{"ancestor": ROOT}]}
    assert render.Renderer.node_state(dataclasses.replace(nv, graph_entry=entry)) == "open"


def test_the_label_is_named_in_the_key_when_a_statement_carries_it(tmp_path: Path) -> None:
    """(c) Q16: a key names every mark the drawing can show; the mark appears in the key exactly
    when some statement of this problem carries the label."""
    assert LABEL_WORD in legend_words(labelled_page(tmp_path / "labelled"))
    _site, tv = site_and_target(tmp_path / "plain")
    r = render.Renderer(_site, repo_url=REPO, decisions_doc=None)
    assert LABEL_WORD not in legend_words(r.target(tv))
    assert "circular" not in legend_words(r.target(tv))


def test_a_labelled_statement_is_drawn_with_its_status_and_the_mark(tmp_path: Path) -> None:
    """The pill wears its own status (here the fixture's proved dependency, filled accent) and
    carries the label's mark; nothing on the drawing calls it circular."""
    html = labelled_page(tmp_path)
    pill = re.search(
        rf'<g class="node status-([a-z-]+)"[^>]*data-node="{DEP}"[^>]*>(.*?)</g></a>', html, re.S
    )
    assert pill is not None
    assert pill.group(1) == "proved", "the status is the row's, untouched by the label"
    assert '<g class="circular-mark"' in pill.group(2)
    assert "status-circular" not in html


def test_the_stylesheet_gives_the_label_its_mark() -> None:
    for selector in (".dot-circular", ".dag .circular-mark", ".circular-label", ".stmt .proves"):
        assert selector in CSS, selector


def test_the_glossary_says_the_label_is_a_fact_not_a_removal() -> None:
    word, meaning, proto = render.GLOSSARY_BY_KEY["circular"]
    assert word == LABEL_WORD
    assert "a proof of" in meaning.lower() and "ancestor" in meaning
    assert "not accepting work" not in meaning.lower()
    assert "no progress" not in meaning.lower()
    assert "D-12 v3.35" in proto


def test_every_output_class_has_a_key_entry() -> None:
    """F18-AC5: the guard over *outputs*, not inputs (2026-09-24). Every mark the proof drawing
    can put on a pill or a line (``dag.svg``'s classes, the picker's, the label's) has a glossary
    card, a swatch in the stylesheet, and a place in the key."""
    source = (
        inspect.getsource(dag.proof_attrs)
        + inspect.getsource(dag.svg)
        + inspect.getsource(dag.outline_mark)
        + inspect.getsource(dag.circular_mark)  # F04-T37: the label's mark
        + inspect.getsource(dag.lines)  # F04-T33: the line kinds
    )
    drawn = {
        '"edge"': "depends-on",  # F04-T33
        "on-proof": "on-proof",
        "off-proof": "not-needed",
        "edge use": "use",
        "edge proposed": "proposed-for",
        "outline-mark": "outline",
        "circular-mark": "circular",
    }
    for cls, key in drawn.items():
        assert cls in source, f"dag no longer draws {cls}; update this guard"
        assert key in render.GLOSSARY_BY_KEY, key
        assert f".dot-{key}" in CSS, key
    keys_source = inspect.getsource(render.Renderer.proof_legend) + inspect.getsource(
        render.Renderer.graph_legend
    )
    for key in (
        "depends-on",
        "on-proof",
        "not-needed",
        "use",
        "unmeasured",
        "proposed-for",
        "outline",
        "circular",
    ):
        assert f'"{key}"' in keys_source, key
        assert key in render.GLOSSARY_BY_KEY and f".dot-{key}" in CSS, key
