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


# --- the checker against hostile hrefs and resources (R10, R13) ----------------------------------


@pytest.mark.parametrize(
    "href",
    [
        "javascript:alert(1)",
        "JAVASCRIPT:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "//evil.example/x",
        "relative/page/",
        "mailto:x@example",
    ],
)
def test_active_or_off_origin_hrefs_are_reported(rendered: dict[str, str], href: str) -> None:
    """Every scheme, protocol-relative and relative href is a problem: only same-origin absolute
    paths and links under the configured repository URL are allowed."""
    foreign = frozenset({"docs/architecture-decisions.html"})
    page = rendered["index.html"] + f'<a href="{href}">x</a>'
    problems = links.check({**rendered, "index.html": page}, repo_url=REPO, foreign=foreign)
    assert problems == [f"index.html: external link {href}"]


@pytest.mark.parametrize(
    "href",
    ["https://github.com/example/graph-evil/x", "https://github.com/example/graph.evil.example/"],
)
def test_repo_url_prefix_match_is_exact_to_the_configured_string(href: str) -> None:
    """A URL that merely starts with the repository URL's text is external."""
    assert links.check({"index.html": f'<a href="{href}">x</a>'}, repo_url=REPO) == [
        f"index.html: external link {href}"
    ]


@pytest.mark.parametrize(
    ("tag", "attr"),
    [("img", "src"), ("iframe", "src"), ("source", "src"), ("link", "href")],
)
def test_every_resource_kind_must_be_same_origin_and_present(tag: str, attr: str) -> None:
    files = {"index.html": f'<{tag} {attr}="https://cdn.example/x">', "site.css": ""}
    problems = links.check(files, repo_url=REPO)
    assert "index.html: off-origin resource https://cdn.example/x" in problems
    files["index.html"] = f'<{tag} {attr}="/missing.css">'
    problems = links.check(files, repo_url=REPO)
    assert "index.html: resource /missing.css does not resolve" in problems


def test_data_uri_resource_is_off_origin() -> None:
    files = {"index.html": '<img src="data:image/svg+xml,<svg onload=alert(1)>">'}
    assert links.check(files, repo_url=REPO) == [
        "index.html: off-origin resource data:image/svg+xml,<svg onload=alert(1)>"
    ]


def test_traversal_and_encoded_paths_do_not_resolve() -> None:
    """An internal href must name a generated file literally; `..` and percent-encoding are not
    normalised into a match."""
    files = {"index.html": "", "targets/index.html": ""}
    assert links.resolve("/targets/../index.html") == "targets/../index.html"
    assert links.resolve("/%74argets/") == "%74argets/index.html"
    for href in ("/targets/../index.html", "/%74argets/", "/Targets/"):
        page = f'<a href="{href}">x</a>'
        assert links.check({**files, "index.html": page}, repo_url=REPO) == [
            f"index.html: internal link {href} does not resolve"
        ]


def test_query_and_fragment_are_ignored_when_resolving() -> None:
    assert links.resolve("/targets/?filter=x#row-3") == "targets/index.html"
    assert links.resolve("#top") is None
    files = {"index.html": '<a href="#top">x</a><a href="/?x=1">y</a>'}
    assert links.check(files, repo_url=REPO) == []


def test_unclosed_tag_and_stray_close_are_both_reported() -> None:
    files = {"index.html": "<div><p>open", "site.css": ""}
    assert links.check(files, repo_url=REPO) == ["index.html: unclosed p"]
    files["index.html"] = "<p>x</p></p>"
    assert links.check(files, repo_url=REPO) == ["index.html: unbalanced </p>"]


def test_foreign_pages_skip_balance_but_never_resource_checks() -> None:
    """The copied decisions document may link anywhere, but it still may not load a resource
    from another origin (R10: the CSP would block it and the page would silently break)."""
    files = {
        "docs/x.html": '<a href="https://cited.example/">c</a></div>'
        '<script src="https://cdn.example/x.js"></script>'
    }
    problems = links.check(files, repo_url=REPO, foreign=frozenset({"docs/x.html"}))
    assert problems == ["docs/x.html: off-origin resource https://cdn.example/x.js"]


def test_non_html_files_are_not_scanned() -> None:
    files = {"site.css": 'a { background: url("https://cdn.example/x.png") }'}
    assert links.check(files, repo_url=REPO) == []
