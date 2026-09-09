"""F04-T3: the link checker (R10, R13; AC5, AC12)."""

from __future__ import annotations

from pathlib import Path

import fixture
import pytest

from opn_site import links, model, render

REPO = "https://github.com/example/graph"


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("links"))
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def test_internal_links_resolve(rendered: dict[str, str]) -> None:
    """AC5: every internal href resolves; the only external hrefs are graph file links and the
    copied document's cited sources."""
    foreign = frozenset({"docs/architecture-decisions.html", "docs/decisions.css"})
    assert links.check(rendered, repo_url=REPO, foreign=foreign) == []
    broken = dict(rendered, **{"index.html": rendered["index.html"] + '<a href="/nowhere/">x</a>'})
    problems = links.check(broken, repo_url=REPO, foreign=foreign)
    assert problems == ["index.html: internal link /nowhere/ does not resolve"]
    external = dict(
        rendered, **{"index.html": rendered["index.html"] + '<a href="https://evil.example/">x</a>'}
    )
    assert links.check(external, repo_url=REPO, foreign=foreign) == [
        "index.html: external link https://evil.example/"
    ]


def test_no_external_resources(rendered: dict[str, str]) -> None:
    """AC12: tags balance on every generated page and no resource is off-origin."""
    foreign = frozenset({"docs/architecture-decisions.html"})
    for rel, html in rendered.items():
        if rel.endswith(".html") and rel not in foreign:
            assert links.check({rel: html, **rendered}, repo_url=REPO, foreign=foreign) == []
    offsite = dict(
        rendered,
        **{
            "index.html": rendered["index.html"]
            + '<script src="https://cdn.example/x.js"></script>'
        },
    )
    assert "index.html: off-origin resource https://cdn.example/x.js" in links.check(
        offsite, repo_url=REPO, foreign=foreign
    )
    unbalanced = dict(rendered, **{"index.html": rendered["index.html"] + "</div>"})
    assert "index.html: unbalanced </div>" in links.check(
        unbalanced, repo_url=REPO, foreign=foreign
    )


def test_generator_refuses_broken_links(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R13 through the generator: a page that links nowhere is a build failure."""
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    original = render.Renderer.home

    def broken_home(self: render.Renderer) -> str:
        return original(self).replace("</main>", '<a href="/missing/">x</a></main>')

    monkeypatch.setattr(render.Renderer, "home", broken_home)
    with pytest.raises(model.SiteError, match="/missing/"):
        render.render_site(site, repo_url=REPO)


def test_resolve() -> None:
    assert links.resolve("/") == "index.html"
    assert links.resolve("/targets/") == "targets/index.html"
    assert links.resolve("/site.css") == "site.css"
    assert links.resolve("https://x/") is None and links.resolve("relative") is None
