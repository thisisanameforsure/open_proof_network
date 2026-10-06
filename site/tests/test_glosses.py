"""F20-T8 (R13; AC2's site half, AC11): wherever the site prints Lean, the current gloss of that
file beside it, or the recruiting cue.

The Lean the site prints that takes a gloss is a statement (the node page, the problem page's
selected-statement card, the reading view), a witness and a relation (the node page) and a
definition module (the problem page). Each such block is followed by one gloss slot naming its
file: every chain's current version that describes the file as it stands, each under a fixed text
label and a provenance line (machine-drafted by a model, written by a person, read against the Lean
by a signer), or the cue that invites the first one. A gloss of since-changed text is shown only in
the slot's history, labelled so. A root shows its curated informal statement first, and any gloss
of it after, labelled unverified (Q11). The Problems page's rows carry each statement gloss's first
sentence, and a node page lists its dependencies with theirs.
"""

from __future__ import annotations

import re
from html import escape

import gloss_fixture as gf
import pytest
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"
#: The Lean blocks that take a gloss, by the class the site gives each one's ``<pre>``.
GLOSSED_PRE = re.compile(r'<pre class="lean (statement|witness|relation|definition)\b[^"]*">')
SLOT = re.compile(r'<div class="gloss-slot" data-gloss-slot="([^"]+)">')


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = gf.glossed_tree(tmp_path_factory.mktemp("glosses"))
    return render.render_site(model.load_site(root, gf.COMMIT), repo_url=REPO)


def node_page(pages: dict[str, str], node: str, target: str = TARGET) -> str:
    return pages[f"nodes/{target}/{node}/index.html"]


def slot_after(page: str, start: int) -> tuple[str, str]:
    """The gloss slot that follows the Lean block opening at ``start``: its file and its HTML up
    to the end of the slot (the slot holds no nested ``gloss-slot``)."""
    end = page.index("</pre>", start)
    m = SLOT.search(page, end)
    assert m is not None, f"no gloss slot after the Lean block at {start}"
    between = page[end + len("</pre>") : m.start()]
    # Only the block's own closing tags and its caption may sit between the Lean and its slot;
    # F22-T18 (P): a statement's caption is the one line saying what its ``sorry`` is.
    assert re.fullmatch(r'\s*(</figure>)?\s*(<p class="sorry-note">.*?</p>)?\s*', between), between[
        :200
    ]
    close = page.find('<div class="gloss-slot"', m.end())
    return m.group(1), page[m.start() : close if close != -1 else len(page)]


def slot_of(page: str, file: str) -> str:
    m = re.search(rf'<div class="gloss-slot" data-gloss-slot="{re.escape(file)}">', page)
    assert m is not None, f"no slot for {file}"
    rest = page[m.start() :]
    nxt = rest.find('<div class="gloss-slot"', 1)
    return rest[: nxt if nxt != -1 else len(rest)]


def current_part(slot: str) -> str:
    """A slot without its history: what it shows as describing the file now."""
    cut = slot.find('<details class="history"')
    return slot if cut == -1 else slot[:cut]


def math(text: str) -> str:
    """The prose renderer's output for text with ``$…$``: escaped, the math in a ``.math`` span."""
    return re.sub(r"\$([^$]+)\$", r'<span class="math">$\1$</span>', escape(text, quote=True))


def test_every_lean_block_has_its_gloss_or_the_cue(pages: dict[str, str]) -> None:
    """AC11: every statement, witness, relation and definition block on every page is followed by
    its gloss slot, which holds the current gloss or the cue; the root shows its curated informal
    statement first; the frontier row shows a first sentence."""
    seen: dict[str, set[str]] = {}
    for rel, page in pages.items():
        if not rel.endswith(".html"):
            continue
        for m in GLOSSED_PRE.finditer(page):
            file, slot = slot_after(page, m.start())
            seen.setdefault(m.group(1), set()).add(rel)
            assert (
                'data-block="gloss"' in slot
                or "No gloss yet" in slot
                or 'data-block="informal"' in slot
            ), (rel, file)
    # Every kind is printed somewhere: statements on node pages, panels and the reading view, a
    # witness and a relation on node pages, a definition module on the problem page.
    assert seen.keys() == {"statement", "witness", "relation", "definition"}, seen.keys()
    problem = pages[f"problems/{TARGET}/index.html"]
    assert seen["definition"] == {f"problems/{TARGET}/index.html"}
    assert any("/proofs/" in rel for rel in seen["statement"])

    # The tutorial's statement: the revision is current (written, then signed), the second chain
    # follows in record order, and the draft it superseded is history only.
    tutorial = node_page(pages, gf.TUTORIAL)
    now = current_part(slot_of(tutorial, f"{TARGET}/nodes/{gf.TUTORIAL}/Statement.lean"))
    assert math(gf.TUTORIAL_REVISED) in now
    assert "written by alice" in now and f"read against the Lean by {gf.CURATOR}" in now
    assert now.index(math(gf.TUTORIAL_REVISED)) < now.index(escape(gf.TUTORIAL_SECOND_CHAIN))
    assert escape(gf.TUTORIAL_DRAFT) not in now
    assert escape(gf.TUTORIAL_DRAFT) in slot_of(
        tutorial, f"{TARGET}/nodes/{gf.TUTORIAL}/Statement.lean"
    )
    for label in re.findall(r'data-provenance="gloss"><strong>([^<]+)</strong>', now):
        assert label == render.PROVENANCE["gloss"]

    # A file with no gloss carries the cue; the relation's draft names its model.
    assert "No gloss yet" in slot_of(
        node_page(pages, gf.MIDDLE), f"{TARGET}/nodes/{gf.MIDDLE}/Statement.lean"
    )
    variant = slot_of(node_page(pages, gf.VARIANT), f"{TARGET}/nodes/{gf.VARIANT}/Relation.lean")
    assert escape(gf.RELATION_GLOSS) in variant
    assert f"machine-drafted by {gf.DRAFTER['model']}" in variant

    # The definition module is printed on its problem page with its gloss.
    defs = slot_of(problem, f"{TARGET}/defs/{gf.MODULE}")
    assert escape(gf.DEFINITION_GLOSS) in defs and "written by carol" in defs
    assert "Opn.fact" in problem

    # The curated root: its informal statement of record first, the steward's gloss after it,
    # labelled unverified — on its node page and in its selected-statement card.
    for page in (
        node_page(pages, gf.CURATED_ROOT, gf.CURATED),
        pages[f"problems/{gf.CURATED}/index.html"],
    ):
        root_slot = slot_of(page, f"{gf.CURATED}/nodes/{gf.CURATED_ROOT}/Statement.lean")
        informal = root_slot.index('data-block="informal"')
        root_gloss = root_slot.index(escape(gf.ROOT_GLOSS))
        assert informal < root_gloss
        assert "unverified" in root_slot[informal:root_gloss].lower()
        # The record's informal text is rendered as every page renders it (F04-T13: escaped, the
        # whole sentence one ``.math`` span the math renderer reads back).
        assert escape(gf.INFORMAL) in root_slot[:root_gloss]

    # The reading view's slots are the real glosses now, not F19's placeholder.
    reading = next(page for rel, page in pages.items() if f"problems/{TARGET}/proofs/" in rel)
    assert math(gf.TUTORIAL_REVISED) in slot_of(
        reading, f"{TARGET}/nodes/{gf.TUTORIAL}/Statement.lean"
    )

    # The frontier row carries the gloss's first sentence and only that.
    row = re.search(
        rf'<div class="stmt"[^>]*>(?:(?!<div class="stmt").)*?{gf.TUTORIAL}.*?</div>',
        pages["problems/index.html"],
        re.S,
    )
    assert row is not None
    first = math(
        "For any two propositions $p$ and $q$, if both hold then both hold in the other order."
    )
    assert first in row.group(0) and "Nothing else is assumed" not in row.group(0)

    # A node page lists its dependencies with their words: the root depends on the tutorial.
    deps = node_page(pages, gf.ROOT)
    listed = deps[deps.index('class="deps"') :]
    assert first in listed[: listed.index("</ul>")]


def test_earlier_text_gloss_only_in_history(pages: dict[str, str]) -> None:
    """AC2 (site half): the hole's witness was glossed as a stub and then filled. The gloss is
    shown only in the slot's history, labelled as describing an earlier version of the file, and
    the slot invites a gloss of the witness as it stands."""
    page = node_page(pages, gf.HOLE)
    slot = slot_of(page, f"{TARGET}/nodes/{gf.HOLE}/Witness.lean")
    now = current_part(slot)
    assert escape(gf.WITNESS_OF_STUB) not in now
    assert "No gloss yet" in now
    history = slot[len(now) :]
    assert history.startswith('<details class="history"')
    words = history.index(escape(gf.WITNESS_OF_STUB))
    item = history.rfind('<li class="version"', 0, words)
    assert "describes an earlier version of this file" in history[item : words + 400]
    # Nowhere else on the page does the stale gloss appear as current words.
    assert page.count(escape(gf.WITNESS_OF_STUB)) == 1


def test_drafted_with_is_shown(pages: dict[str, str]) -> None:
    """F21-AC6 (R7): a version naming ``drafted_with`` says "written by <author>, drafted with
    <model>" in its provenance line — the gloss block's demarcated label (C9) — with the
    contributor's words escaped and never raw; a legacy drafter-block draft keeps
    "machine-drafted by <model>"."""
    page = node_page(pages, gf.HOLE)
    now = current_part(slot_of(page, f"{TARGET}/nodes/{gf.HOLE}/Statement.lean"))
    assert escape(gf.HOLE_STATEMENT_GLOSS) in now
    line = f"written by dana, drafted with {escape(gf.DRAFTED_WITH)}"
    label = re.search(r'<p class="block-label" data-provenance="gloss">(.*?)</p>', now, re.S)
    assert label is not None
    assert line in label.group(1), label.group(1)
    for page_html in pages.values():
        assert gf.DRAFTED_WITH not in page_html  # escaped wherever it is shown
    variant = slot_of(node_page(pages, gf.VARIANT), f"{TARGET}/nodes/{gf.VARIANT}/Relation.lean")
    assert f"machine-drafted by {gf.DRAFTER['model']}" in variant
