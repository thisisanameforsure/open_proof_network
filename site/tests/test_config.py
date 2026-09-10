"""F04 configuration (C6; Q5, Q8): the repository URL is config and nothing in the generator
knows its own hostname. The project log's rule: never write a hostname into a template or a
page."""

from __future__ import annotations

import re
from pathlib import Path

import fixture

from opn_site import config, model, render

SITE_PKG = Path(__file__).resolve().parents[1] / "opn_site"
HOSTNAME_RE = re.compile(r"openproofnetwork|cloudfront\.net|amazonaws\.com", re.I)


def test_repo_url_comes_from_the_environment_only() -> None:
    """One documented variable, a documented default, and nothing else read."""
    assert config.load({}).graph_repo_url == config.DEFAULT_GRAPH_REPO_URL
    custom = config.load({"OPN_SITE_GRAPH_REPO_URL": "https://git.example/g"})
    assert custom.graph_repo_url == "https://git.example/g"
    unrelated = config.load({"GRAPH_REPO_URL": "https://git.example/other"})
    assert unrelated.graph_repo_url == config.DEFAULT_GRAPH_REPO_URL


def test_trailing_slash_on_repo_url_does_not_double_up_in_links(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    page = render.Renderer(site, repo_url="https://git.example/g///", decisions_doc=None).home()
    assert f'href="https://git.example/g/tree/{fixture.COMMIT}"' in page
    assert "g///" not in page and "g//" not in page


def test_no_hostname_literal_in_generator_source_templates_or_static_files() -> None:
    """A static check over every file the generator ships: no site hostname anywhere."""
    offenders = [
        str(p.relative_to(SITE_PKG))
        for p in sorted(SITE_PKG.rglob("*"))
        if p.is_file()
        and p.suffix in {".py", ".html", ".css", ".js"}
        and HOSTNAME_RE.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_only_the_config_module_reads_the_environment() -> None:
    """Conventions §1: nothing but the config module touches ``os.environ``."""
    readers = [
        str(p.relative_to(SITE_PKG))
        for p in sorted(SITE_PKG.rglob("*.py"))
        if p.name != "config.py"
        and re.search(r"os\.environ|os\.getenv|environ\[", p.read_text(encoding="utf-8"))
    ]
    assert readers == []


def test_rendered_pages_carry_no_hostname(tmp_path: Path) -> None:
    """The generated output names the graph repository (config) and nothing about where the
    site itself is served, so the same output can be served from any origin."""
    root = fixture.build(tmp_path)
    files = render.render_site(model.load_site(root, fixture.COMMIT), repo_url="https://x/y")
    for rel, content in files.items():
        if rel != "docs/architecture-decisions.html":  # a verbatim copy of the protocol doc
            assert not HOSTNAME_RE.search(content), rel
