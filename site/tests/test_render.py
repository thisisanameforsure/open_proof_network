"""F04-T1: the renderer core (R1-R6, R13; AC1, AC4, AC6-AC8, AC11)."""

from __future__ import annotations

import json
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import ClassVar

import fixture
import pytest

from opn_gate import schemas
from opn_site import cli, model, render

GOLDEN = Path(__file__).resolve().parent / "golden"
REPO = "https://github.com/example/graph"
COPIED_DOC = "docs/architecture-decisions.html"  # a verbatim copy of a network file (R9, Q4)
PAGES = (
    "index.html",
    "targets/index.html",
    "targets/propositional/index.html",
    "nodes/propositional/and-reassoc/index.html",
    "nodes/propositional/and-swap-reassoc/index.html",
    "nodes/propositional/tutorial-and-swap/index.html",
)


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("site"))
    site = model.load_site(root, fixture.COMMIT)
    return render.render_site(site, repo_url=REPO)


def write_goldens(base: Path = GOLDEN) -> None:
    """Regenerate the golden pages (review the diff by eye before committing)."""
    import tempfile  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        root = fixture.build(Path(tmp))
        files = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
        for rel in (*PAGES, *T2_PAGES):
            target = base / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(files[rel], encoding="utf-8")


def test_golden_pages(rendered: dict[str, str]) -> None:
    """AC1 (T1's four page types): the rendering equals the checked-in golden HTML."""
    assert set(PAGES) <= set(rendered)
    for rel in PAGES:
        assert rendered[rel] == (GOLDEN / rel).read_text(encoding="utf-8"), rel


def test_commit_and_file_links(rendered: dict[str, str]) -> None:
    """AC4, R2: every page names the commit; every rendered file links at that commit."""
    for rel, html in rendered.items():
        if not rel.endswith(".html") or rel == COPIED_DOC:
            continue
        assert fixture.COMMIT[:12] in html, rel
        assert f"{REPO}/tree/{fixture.COMMIT}" in html, rel
    node = rendered["nodes/propositional/tutorial-and-swap/index.html"]
    assert (
        f"{REPO}/blob/{fixture.COMMIT}/targets/propositional/nodes/tutorial-and-swap/Statement.lean"
        in node
    )
    assert (
        f"{REPO}/blob/{fixture.MERGE}/targets/propositional/nodes/tutorial-and-swap/Proof.lean"
        in node
    )
    assert f"{REPO}/blob/{fixture.COMMIT}/attestations/000001.json" in node
    target = rendered["targets/propositional/index.html"]
    assert f"{REPO}/blob/{fixture.COMMIT}/targets/propositional/graph.json" in target


def test_node_page_states(rendered: dict[str, str]) -> None:
    """AC6: a proved node shows verdict, steps, reviewer and the proof link; an unproved one
    says so and links no proof."""
    proved = rendered["nodes/propositional/tutorial-and-swap/index.html"]
    assert "Verdict <strong>pass</strong>" in proved
    assert "reviewer-one" in proved
    assert "<td>kernel-replay</td>" in proved and 'class="result-pass"' in proved
    assert "Proof merged in commit" in proved and "/Proof.lean" in proved
    unproved = rendered["nodes/propositional/and-swap-reassoc/index.html"]
    assert "No proof merged yet." in unproved
    assert "/Proof.lean" not in unproved
    assert "No attestation" in unproved
    assert "1 recorded" not in unproved and "2 recorded" in unproved  # attempts incl. invalid
    assert "invalid 1" in unproved and "case-split" in unproved


def test_compiler_trust_flag(rendered: dict[str, str]) -> None:
    """AC7."""
    flagged = rendered["nodes/propositional/and-reassoc/index.html"]
    assert "trust base is the compiler" in flagged
    assert (
        "trust base is the compiler"
        not in rendered["nodes/propositional/tutorial-and-swap/index.html"]
    )


def test_no_explainer_cue(rendered: dict[str, str]) -> None:
    """AC8: the slot is never blank."""
    assert "No explainer yet." in rendered["nodes/propositional/and-reassoc/index.html"]
    with_one = rendered["nodes/propositional/tutorial-and-swap/index.html"]
    assert "No explainer yet." not in with_one
    assert "Unverified: explainer, by thisisanameforsure, drafted with claude-fable-5-1" in with_one


def test_target_page_has_dag_and_nodes(rendered: dict[str, str]) -> None:
    target = rendered["targets/propositional/index.html"]
    assert '<svg class="dag"' in target
    assert target.count('<g class="node status-') == 3
    assert "No approach records yet" in target and "No state-of-the-problem note yet" in target


def test_home_counts(rendered: dict[str, str]) -> None:
    home = rendered["index.html"]
    assert '<td class="n">1</td><td><a href="/targets/">targets</a>' in home
    assert '<td class="n">2</td><td><a href="/targets/">nodes proved</a>' in home
    assert '<td class="n">1</td><td><a href="/frontier/">nodes on the frontier</a>' in home


class _Balance(HTMLParser):
    VOID: ClassVar[set[str]] = {"meta", "link", "br", "hr", "img", "input"}

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.problems: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1] != tag:
            self.problems.append(f"unexpected </{tag}> (open: {self.stack[-3:]})")
        else:
            self.stack.pop()


def test_pages_are_well_formed(rendered: dict[str, str]) -> None:
    for rel, html in rendered.items():
        if rel.endswith(".html") and rel != COPIED_DOC:  # the copied doc is not our markup
            p = _Balance()
            p.feed(html)
            assert not p.problems and not p.stack, (rel, p.problems, p.stack)


def test_invalid_product_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC11, R13."""
    root = fixture.build(tmp_path)
    frontier = root / "frontier.json"
    doc = json.loads(frontier.read_text())
    doc["entries"][0]["difficulty"] = 3
    frontier.write_text(json.dumps(doc))
    out = tmp_path / "out"
    assert (
        cli.main(["render", "--graph", str(root), "--commit", fixture.COMMIT, "--out", str(out)])
        == 1
    )
    assert not out.exists()
    assert "frontier.json does not validate" in json.loads(capsys.readouterr().out)["error"]


def test_render_command_writes_everything(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = fixture.build(tmp_path)
    out = tmp_path / "out"
    assert (
        cli.main(["render", "--graph", str(root), "--commit", fixture.COMMIT, "--out", str(out)])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["ok"] is True
    for rel in PAGES:
        assert (out / rel).is_file(), rel
    assert (out / "site.css").is_file()


# --- T2: frontier, contributors, docs ---------------------------------------------------------

T2_PAGES = ("frontier/index.html", "contributors/index.html", "docs/index.html")


def test_frontier_table(rendered: dict[str, str]) -> None:
    """AC9: one row per frontier entry, one column per F03-R5 field, a same-origin script."""
    page = rendered["frontier/index.html"]
    assert page.count("<th>") == 15
    assert page.count("<tr>") == 1 + 1  # header + the one frontier entry (the ready root)
    assert 'href="/nodes/propositional/and-swap-reassoc/"' in page
    assert '<script src="/frontier.js"></script>' in page
    assert "https://" not in page.split("<main>")[1].split("</main>")[0].replace(REPO, "")
    assert "frontier.js" in rendered and "querySelector" in rendered["frontier.js"]
    assert "deps: and-reassoc, tutorial-and-swap; library: none" in page


def test_contributors_empty_state(rendered: dict[str, str]) -> None:
    """R8: no ledger files yet, and the page says so."""
    assert "No ledger files exist yet" in rendered["contributors/index.html"]


def test_docs_bundle(rendered: dict[str, str]) -> None:
    """R9, R10: the decisions doc is copied with no external link, inline style or script."""
    docs = rendered["docs/index.html"]
    assert 'href="/docs/architecture-decisions.html"' in docs
    assert "no AGENTS.md yet" in docs and "No license text" in docs and "No sign-off" in docs
    assert "No human-funnel documentation yet" not in docs  # F10-T5 delivered it
    copied = rendered["docs/architecture-decisions.html"]
    assert "fonts.googleapis.com" not in copied
    assert "<script" not in copied and "<style" not in copied
    assert '<link rel="stylesheet" href="/docs/decisions.css">' in copied
    assert "D-36" in copied and rendered["docs/decisions.css"].strip()


# F10-R9: each document and the decision it implements, named in its own text (AC9).
FUNNEL_DOCS: dict[str, tuple[str, tuple[str, ...]]] = {
    "docs/review-checklist.html": ("Statement review checklist", ("D-15", "D-16", "D-11")),
    "docs/revision-request.html": ("Requesting a revision", ("D-8",)),
    "docs/defect-claim.html": ("Filing a defect claim", ("D-16", "D-15")),
    "docs/curator-intake.html": ("Curator intake checklist", ("D-6", "D-9", "D-10")),
}
DEFECT_CLASSES = (
    "missing-hypothesis",
    "junk-value",
    "vacuity",
    "quantifier-scope",
    "wrong-domain",
    "definition-mismatch",
    "strength-drift",
    "other-with-exhibit",
)


def test_human_funnel_docs(rendered: dict[str, str]) -> None:
    """F10-AC9: the four human-funnel documents are rendered, linked from the Docs page, and
    each names the decisions it implements; the checklist covers every class of the taxonomy
    (F08-Q4) with a worked example, and nothing in a page is unescaped markup from the source."""
    docs = rendered["docs/index.html"]
    for rel, (title, decisions) in FUNNEL_DOCS.items():
        assert f'href="/{rel}"' in docs and title in docs, rel
        page = rendered[rel]
        assert f"<h1>{title}</h1>" in page
        for decision in decisions:
            assert decision in page, (rel, decision)
        assert "<script" not in page and "<style" not in page
    checklist = rendered["docs/review-checklist.html"]
    for defect_class in DEFECT_CLASSES:
        assert f"<h3>{defect_class}</h3>" in checklist, defect_class
    assert checklist.count("<pre><code>") >= len(DEFECT_CLASSES) - 1  # a worked example each
    assert "<ol><li>" in checklist and "<ul><li>" in checklist
    assert "&lt;" in rendered["docs/revision-request.html"]  # the record's angle brackets, escaped


def test_render_document_shapes() -> None:
    """The site-document renderer: headings, both list kinds with continuations, inline code
    and strong, fences, and escaping throughout."""
    from opn_site import prose  # noqa: PLC0415

    html = prose.render_document(
        "# T <b>\n\nA `x<y` **b**.\n\n- one\n  more\n- two\n\n1. a\n2. b\n\n```\n<raw>\n```\n"
    )
    assert html == (
        "<h1>T &lt;b&gt;</h1>\n"
        "<p>A <code>x&lt;y</code> <strong>b</strong>.</p>\n"
        "<ul><li>one more</li><li>two</li></ul>\n"
        "<ol><li>a</li><li>b</li></ol>\n"
        "<pre><code>&lt;raw&gt;</code></pre>"
    )
    assert prose.render_document("- a\nb\n") == "<ul><li>a</li></ul>\n<p>b</p>"


def test_t2_golden_pages(rendered: dict[str, str]) -> None:
    for rel in T2_PAGES:
        assert rendered[rel] == (GOLDEN / rel).read_text(encoding="utf-8"), rel


# --- F07-T5: the contributors page reads the ledger's entries (R8; D-19) -------------------------


def test_contributors_lists_ledger_entries(tmp_path_factory: pytest.TempPathFactory) -> None:
    """The page shows one row per contribution, linked to the artifact that earned it, and a
    revoked entry stays listed as revoked (D-18). No totals: significance is retrospective."""
    root = fixture.build(tmp_path_factory.mktemp("ledger-site"))
    doc = {
        "schema": "ledger/v1",
        "identity": "alice",
        "entries": [
            {
                "line": "proof",
                "target": "propositional",
                "node": "and-reassoc",
                "artifact": "Proof.lean",
                "merge_commit": "1" * 40,
                "date": "2026-09-10T12:00:00Z",
                "tooling": "claude-opus-5",
                "status": "active",
            },
            {
                "line": "attempts",
                "target": "propositional",
                "node": "and-reassoc",
                "artifact": "attempts/2026-09-10-alice.yaml",
                "merge_commit": "1" * 40,
                "date": "2026-09-10T12:00:00Z",
                "tooling": "undeclared",
                "route_class": "induction",
                "status": "revoked",
            },
        ],
    }
    (root / "ledger").mkdir(parents=True, exist_ok=True)
    (root / "ledger" / "alice.json").write_bytes(schemas.canonical_json(doc))

    pages = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    page = pages["contributors/index.html"]
    assert "No ledger files exist yet" not in page
    assert ">alice</h2>" in page
    assert "proof" in page and "attempts" in page
    assert "claude-opus-5" in page
    assert "revoked" in page  # D-18: kept and labelled, never removed
    assert "Proof.lean" in page


# --- F11-AC9: a listed target's page says why it cannot be claimed (R10) ------------------------


@pytest.fixture(scope="module")
def listed_pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build_with_listed_target(tmp_path_factory.mktemp("listed"))
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def test_listed_target_reasons(listed_pages: dict[str, str]) -> None:
    """AC9, R10: the Targets page carries the not-claimable reasons, the source link, the
    attribution and licence, and the QA summary — and does not reproduce the informal statement
    of a source that states no licence."""
    page = listed_pages["targets/index.html"]

    assert "Not claimable, because:" in page
    for reason in (
        "D-33 status is listed",
        "fidelity grade is below screened-and-signed",
        "not been posted upstream",
    ):
        assert reason in page, reason

    assert fixture.UNLICENSED["url"] in page, "the source is not linked"
    assert escape(fixture.UNLICENSED["attribution"]) in page, "the attribution is missing"
    assert "licence none-stated" in page
    assert escape(fixture.QA_SUMMARY) in page, "the QA summary is missing"

    # R10: the paraphrase stands in, and the source's own wording is nowhere on any page —
    # because intake refused to put it in the graph at all.
    assert escape(fixture.PARAPHRASE) in page
    assert "the network's own paraphrase" in page
    assert all(fixture.UNLICENSED_WORDING not in html for html in listed_pages.values())


def test_a_claimable_target_states_no_reasons(listed_pages: dict[str, str]) -> None:
    """The block is a fact about this target, not boilerplate: it appears once, for the listed
    target, and the propositional target's own card does not claim reasons it does not have."""
    page = listed_pages["targets/index.html"]
    assert page.count("Not claimable, because:") == 1
    assert "Fidelity by subject:" in page and "root mechanical-only" in page
