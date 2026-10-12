"""F16-T6 / AC6: the Docs page lists every connector, alphabetically, with its snippets filled
from the build's service URL, and says "not yet verified" for any entry no level-2 run has
passed — never a version it has not earned (F16-R10).
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import fixture
import pytest

from opn_gate import clients
from opn_site import model, render

API = "https://api.test.invalid"
REPO = "https://github.com/example/graph"


@pytest.fixture(scope="module")
def docs(tmp_path_factory: pytest.TempPathFactory) -> str:
    root = fixture.build(tmp_path_factory.mktemp("site"))
    site = model.load_site(root, fixture.COMMIT)
    return render.render_site(site, repo_url=REPO, api_url=API)["docs/index.html"]


def test_listed(docs: str) -> None:
    registry = clients.load()
    names = [e.name for e in registry.entries]
    positions = [docs.index(f"<h3>{render.esc(name)} ") for name in names]
    by_position = [name for _, name in sorted(zip(positions, names, strict=True))]
    assert by_position == sorted(names, key=str.lower), "listed alphabetically, never ranked"
    for entry in registry.entries:
        assert f'id="connector-{entry.id}"' in docs
        for r in clients.render(registry, entry, f"{API}/mcp"):
            assert render.esc(r.text.rstrip()) in docs, (entry.id, r.title)
    assert 'href="#connectors"' in docs


def test_only_the_configured_host(docs: str) -> None:
    section = docs[docs.index('id="connectors"') : docs.index('id="agents"')]
    hosts = set(re.findall(r"https?://([^/\s\"'<]+)", section))
    assert hosts <= {"api.test.invalid"}, hosts


def test_unverified_says_so(docs: str) -> None:
    for entry in clients.load().entries:
        card = docs[docs.index(f'id="connector-{entry.id}"') :]
        card = card[: card.index("</section>")]
        if entry.verified is None:
            assert "Not yet verified" in card and "Tested with" not in card, entry.id


def test_verified_shows_version_and_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A passing level-2 run is the only thing that puts a version on the page."""
    registry = clients.load()
    verified = clients.Verified("2.3.4", "2026-09-25", "engineering/evidence/F16/level2.txt")
    entries = tuple(
        dataclasses.replace(e, verified=verified) if e.id == "codex-cli" else e
        for e in registry.entries
    )
    monkeypatch.setattr(clients, "load", lambda *_a: dataclasses.replace(registry, entries=entries))
    root = fixture.build(tmp_path)
    page = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO, api_url=API)
    card = page["docs/index.html"]
    card = card[card.index('id="connector-codex-cli"') :]
    card = card[: card.index("</section>")]
    assert "Tested with 2.3.4 on 2026-09-25." in card
    assert "Not yet verified" not in card


def test_without_a_service_url_names_the_variable(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    page = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    section = page["docs/index.html"]
    section = section[section.index('id="connectors"') : section.index('id="agents"')]
    assert "$OPN_API/mcp" in section
    assert "https://" not in section
