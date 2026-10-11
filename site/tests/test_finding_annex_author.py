"""F18-T3 (R10; AC10): an annex says who wrote it.

Found 2026-10-03 while planning F18: every annex on the live site read "author not recorded".
``annex/v1`` records ``contributor``, ``model_and_tooling`` and ``licence`` (the service writes
them, ``gate/schemas/annex/v1.json``), and the site's front-matter reader knew only ``author``,
``model`` and ``date`` — the explainer's names. The front matter below is a live annex's,
erdos-1050--h1-v2's f593a93a…, byte for byte except the body.
"""

from __future__ import annotations

from pathlib import Path

import fixture
import pytest
from harness import TARGET

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
NODE = "and-reassoc"
LIVE = (
    "---\n"
    "contributor: h0924-1050-http\n"
    "date: '2026-09-24T12:35:46Z'\n"
    "licence: CC-BY-4.0\n"
    "model_and_tooling: null\n"
    f"node: {NODE}\n"
    "schema: annex/v1\n"
    "---\n"
    "# Explicit q-Padé approximants\n\nNumerical evidence, not a proof.\n"
)
DRAFTED = LIVE.replace(
    "model_and_tooling: null", "model_and_tooling: Claude Opus 5.5 via Claude Code"
)


@pytest.fixture(scope="module")
def page(tmp_path_factory: pytest.TempPathFactory) -> str:
    root = fixture.curated(tmp_path_factory.mktemp("annex-author"))
    annex = root / "targets" / TARGET / "nodes" / NODE / "annex"
    (annex / ("1" * 64 + ".md")).write_text(LIVE, encoding="utf-8")
    (annex / ("2" * 64 + ".md")).write_text(DRAFTED, encoding="utf-8")
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    site = model.load_site(root, fixture.COMMIT)
    return render.render_site(site, repo_url=REPO)[f"nodes/{TARGET}/{NODE}/index.html"]


def annex_labels(page: str) -> list[str]:
    return [
        line for line in page.split('<p class="label">')[1:] if line.startswith("Untrusted: annex")
    ]


def test_the_contributor_and_licence_are_shown(page: str) -> None:
    labels = annex_labels(page)
    assert len(labels) == 2, labels
    assert all("author not recorded" not in label for label in labels), labels
    assert all("by h0924-1050-http" in label for label in labels), labels
    assert all("CC-BY-4.0" in label for label in labels), labels


def test_a_recorded_model_is_shown_and_a_null_one_is_not(page: str) -> None:
    first, second = annex_labels(page)
    assert "drafted with" not in first  # model_and_tooling: null is not a model called "null"
    assert "drafted with Claude Opus 5.5 via Claude Code" in second


def test_the_reader_keeps_the_explainer_names(tmp_path: Path) -> None:
    """Explainers write ``author``/``model``/``date``; those keep working."""
    f = tmp_path / "e.md"
    f.write_text("---\nauthor: alice\nmodel: none\ndate: 2026-09-01\n---\nbody\n", encoding="utf-8")
    p = model.parse_prose(f, tmp_path)
    assert (p.author, p.model, p.date) == ("alice", "none", "2026-09-01")
