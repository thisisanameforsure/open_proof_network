"""F04-T30: ``/llms.txt`` and ``/robots.txt`` on the site (audit 2026-10-04; owner-approved).

The site's root had neither file. ``llms.txt`` names where an agent starts: the guide (the Docs
page, and the graph's AGENTS.md at the rendered commit) and the service's route index,
``info.json``, error codes and MCP endpoint, as full URLs from configuration — the service's
origin is ``OPN_SITE_API_URL``, which has no default, so with it unset the file says so and names
no service URL (C7). ``robots.txt`` allows everything and names no path.
"""

from __future__ import annotations

from pathlib import Path

import fixture
import pytest

from opn_api import routes
from opn_api.mcp import server as mcpmod
from opn_site import model, render

REPO = "https://git.example/graph"
API = "https://api.example.test"


def site(tmp_path: Path) -> model.Site:
    return model.load_site(fixture.build(tmp_path), fixture.COMMIT)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> model.Site:
    return site(tmp_path_factory.mktemp("llms"))


def test_llms_txt_names_the_guide_and_the_service_as_full_urls(built: model.Site) -> None:
    files = render.render_site(built, repo_url=REPO, api_url=API + "/")
    text = files["llms.txt"]
    assert text.startswith("# Open Proof Network\n")
    for url in (
        f"{REPO}/blob/{fixture.COMMIT}/AGENTS.md",
        f"{API}/",
        f"{API}/info.json",
        f"{API}/errors.json",
        f"{API}/mcp",
    ):
        assert f"]({url})" in text, url
    assert "](/docs/" in text  # the site's own Docs page, which renders the same guide
    assert f"{API}//" not in text


def test_llms_txt_without_a_service_names_no_service_url(built: model.Site) -> None:
    text = render.render_site(built, repo_url=REPO)["llms.txt"]
    assert f"{REPO}/blob/{fixture.COMMIT}/AGENTS.md" in text
    assert "not configured" in text
    assert "info.json" not in text and "errors.json" not in text and "/mcp" not in text


def test_robots_txt_allows_everything_and_names_no_path(built: model.Site) -> None:
    lines = [
        line.strip()
        for line in render.render_site(built, repo_url=REPO)["robots.txt"].splitlines()
        if line.strip()
    ]
    assert lines[0] == "User-agent: *"
    assert "Allow: /" in lines
    assert not [line for line in lines if line.lower().startswith("disallow") and line[9:].strip()]


def test_the_service_paths_are_the_services_own() -> None:
    """The site names service paths without importing the service; this holds them equal."""
    labels = {r.label for r in routes.ROUTES}
    for path in (render.INFO_PATH, render.ERRORS_PATH, "/"):
        assert f"GET {path}" in labels, path
    assert render.MCP_PATH == mcpmod.MCP_PATH


def test_both_files_are_written_to_the_site_root(built: model.Site, tmp_path: Path) -> None:
    files = render.render_site(built, repo_url=REPO, api_url=API)
    written = {p.relative_to(tmp_path).as_posix() for p in render.write(files, tmp_path)}
    assert {"llms.txt", "robots.txt"} <= written
