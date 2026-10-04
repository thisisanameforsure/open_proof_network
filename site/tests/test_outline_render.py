"""F19-T7 (R9, R11, R13; AC10, AC3's page half, AC13's page half): the outline on a node page.

A merged proof's ``outline/v1`` product (``targets/<id>/outlines/<artifact-hash>.json``) renders
above its source as a tree of native ``<details>``: each step its claim and the goal it leaves,
each Mathlib constant its docstring sentence as a tooltip a keyboard reaches and its Stacks or
Kerodon tag as text, a step closed by automation folded and labelled "routine: <tactics>", a step
whose printing did not read back shown as its Lean lines only, and every step one click from its
Lean lines in the attested file. With no outline, the proof section is exactly what it was.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import fixture
import pytest
import site_outlines as so
from harness import TARGET, copy_graph

from opn_gate import products, schemas
from opn_site import model, render

REPO = "https://github.com/example/graph"
TUTORIAL = "tutorial-and-swap"
PAGE = f"nodes/{TARGET}/{TUTORIAL}/index.html"


def tutorial_tree(tmp_path: Path) -> tuple[Path, str]:
    """The fixture graph with the tutorial's proof rewritten to ``TUTORIAL_PROOF`` and attested;
    returns the root and the proof's sha256 (its ``artifact_hash``)."""
    root = copy_graph(tmp_path, publish=True)
    proof = fixture.nodes_dir(root) / TUTORIAL / "Proof.lean"
    proof.write_text(so.TUTORIAL_PROOF, encoding="utf-8")
    fixture.attest(root, TUTORIAL, 1)
    return root, schemas.content_hash(proof.read_bytes())


def render_pages(root: Path) -> dict[str, str]:
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def element(page: str, marker: str, tag: str = "li") -> str:
    """The whole ``<tag …marker…>…</tag>`` element, nested ones included."""
    assert marker in page, f"{marker} is not on the page"
    start = page.index(marker)
    start = page.rindex(f"<{tag}", 0, start)
    depth, at = 0, start
    pattern = re.compile(rf"<{tag}\b|</{tag}>")
    for m in pattern.finditer(page, start):
        depth += 1 if m.group(0) != f"</{tag}>" else -1
        if depth == 0:
            at = m.end()
            break
    return page[start:at]


def details_tag(li: str) -> str:
    m = re.search(r"<details\b[^>]*>", li)
    assert m is not None, li[:200]
    return m.group(0)


@pytest.fixture(scope="module")
def page(tmp_path_factory: pytest.TempPathFactory) -> str:
    root, digest = tutorial_tree(tmp_path_factory.mktemp("outline"))
    so.write(root, so.document(TUTORIAL, "Proof.lean", digest, so.tutorial_steps()))
    return render_pages(root)[PAGE]


def test_the_outline_is_a_tree_of_details_above_the_source(page: str) -> None:
    outline = element(page, 'class="proof-outline"', "section")
    assert page.index('class="proof-outline"') < page.index('<figure class="artifact"')
    for step_id in ("hq", "hq.s1", "hp", "s3"):
        assert "<details" in element(outline, f'data-step="{step_id}"')
    # Nested: the obtain is a child of hq, not a sibling.
    assert 'data-step="hq.s1"' in element(outline, 'data-step="hq"')
    assert 'data-step="hq.s1"' not in element(outline, 'data-step="hp"')


def test_each_step_shows_its_claim_and_the_goal_it_leaves(page: str) -> None:
    hq = element(page, 'data-step="hq"')
    summary = re.search(r"<summary>(.*?)</summary>", hq, re.S)
    assert summary is not None and "<code" in summary.group(1) and "q</code>" in summary.group(1)
    assert "q ∧ p" in hq and "hq : q" in hq


def test_the_automation_step_is_folded_and_labelled_with_its_tactics(page: str) -> None:
    hp = element(page, 'data-step="hp"')
    assert " open" not in details_tag(hp)
    assert "routine: simp" in hp
    assert " open" in details_tag(element(page, 'data-step="hq"'))


def test_a_mathlib_constant_carries_its_docstring_as_a_tooltip_and_its_tag_as_text(
    page: str,
) -> None:
    hp = element(page, 'data-step="hp"')
    m = re.search(r'<span class="term const"[^>]*tabindex="0"[^>]*>(.*?)</span></span>', hp, re.S)
    assert m is not None, "the constant is not a focusable term"
    assert "And.left" in m.group(1)
    assert 'role="tooltip"' in m.group(0)
    assert "Extract the left conjunct from a conjunction, &lt;b&gt;escaped&lt;/b&gt;." in m.group(0)
    assert f"Stacks {so.STACKS_TAG}" in hp
    assert "stacks.math" not in page and "kerodon.net" not in page  # Q6: text, not a link


def test_expanding_a_step_reaches_its_lean_lines(page: str) -> None:
    hq = element(page, 'data-step="hq"')
    lines = "\n".join(so.TUTORIAL_PROOF.splitlines()[4:7])
    assert f'<pre class="lean">{render.esc(lines)}</pre>' in hq
    assert re.search(
        r"/blob/4{40}/targets/propositional/nodes/tutorial-and-swap/Proof\.lean#L5-L7", hq
    )


def test_unreliable_step_shows_lean_only(page: str) -> None:
    """AC3's page half (F19-R3): a step whose printed claim did not read back is its lines."""
    s3 = element(page, 'data-step="s3"')
    assert render.esc(so.UNRELIABLE_TEXT) not in s3 and so.UNRELIABLE_TEXT not in s3
    assert "show q ∧ p" in s3 and "exact ⟨hq, hp⟩" in s3
    assert "printed form did not read back" in s3


def test_the_outline_says_what_checked_it(page: str) -> None:
    outline = element(page, 'class="proof-outline"', "section")
    label = re.search(r'<p class="block-label" data-provenance="kernel">(.*?)</p>', outline, re.S)
    assert label is not None
    assert "Checked by the kernel" in label.group(1) and "4" * 12 in label.group(1)


def test_without_an_outline_the_proof_section_is_unchanged(tmp_path: Path) -> None:
    root, digest = tutorial_tree(tmp_path / "a")
    bare = render_pages(root)[PAGE]
    so.write(root, so.document(TUTORIAL, "Proof.lean", digest, so.tutorial_steps()))
    outlined = render_pages(root)[PAGE]
    figure = re.compile(r'<figure class="artifact"[^>]*>.*?Proof\.lean.*?</figure>', re.S)
    assert "proof-outline" not in bare
    assert figure.findall(bare) == figure.findall(outlined) != []


def test_an_outline_of_other_bytes_is_not_shown(tmp_path: Path) -> None:
    root, _ = tutorial_tree(tmp_path)
    so.write(root, so.document(TUTORIAL, "Proof.lean", "e" * 64, so.tutorial_steps()))
    assert "proof-outline" not in render_pages(root)[PAGE]


def test_an_outline_that_does_not_validate_is_skipped_and_named(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """C7, the 2026-09-17 rule: one bad product does not take the site down."""
    root, digest = tutorial_tree(tmp_path)
    path = so.write(root, so.document(TUTORIAL, "Proof.lean", digest, so.tutorial_steps()))
    path.write_text('{"schema": "outline/v1"}\n', encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        page = render_pages(root)[PAGE]
    assert "proof-outline" not in page
    assert path.name in caplog.text


def test_a_term_proof_says_it_is_a_single_term(tmp_path: Path) -> None:
    root, digest = tutorial_tree(tmp_path)
    term = so.step(
        "s1", "term", (3, 10), claim=so.text("∀ p q : Prop, p ∧ q → q ∧ p"), closed_by=("term", [])
    )
    so.write(root, so.document(TUTORIAL, "Proof.lean", digest, [term]))
    assert "The proof is a single term" in render_pages(root)[PAGE]


def test_a_hole_step_of_a_partial_links_its_child_node(tmp_path: Path) -> None:
    """AC13's page half: a partial assembly's sorry step names the node it became."""
    root = fixture.curated(tmp_path)
    partial = (
        fixture.nodes_dir(root) / "and-swap-reassoc" / "attempts" / "2026-09-01-a-partial.lean"
    )
    hole = so.step(
        "s1",
        "hole",
        (3, 3),
        claim=so.text("q ∧ p"),
        closed_by=("hole", []),
        child_node="and-reassoc",
    )
    so.write(
        root,
        so.document(
            "and-swap-reassoc",
            "attempts/2026-09-01-a-partial.lean",
            schemas.content_hash(partial.read_bytes()),
            [hole],
            kind="partial",
        ),
    )
    page = render_pages(root)[f"nodes/{TARGET}/and-swap-reassoc/index.html"]
    step = element(page, 'data-step="s1"')
    assert f'href="/nodes/{TARGET}/and-reassoc/"' in step
    label = re.search(
        r'data-provenance="([a-z]+)"', element(page, 'class="proof-outline"', "section")
    )
    assert label is not None and label.group(1) == "untrusted"  # no attestation covers a partial
