"""F05-T24: ``/llms.txt`` and ``/robots.txt`` on the service (audit 2026-10-04; owner-approved).

An agent or a crawler that arrives at the service's hostname asks for these two files before
anything else; both answered ``404 not-found``. ``llms.txt`` names, as full URLs, the places an
agent starts: the contributor guide, the route index, ``info.json``, the error codes and the MCP
endpoint. Every URL is built from configuration (``OPN_API_PUBLIC_URL``, the graph repository),
never written as a literal hostname (the project log, 2026-09-09). ``robots.txt`` allows
everything and names no path, so it points at nothing secret.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from api_fakes import Harness, make_harness

from opn_api import routes

PUBLIC = "https://api.example.test"
API_PKG = Path(__file__).resolve().parents[1] / "opn_api"
HOSTNAME_RE = re.compile(r"openproofnetwork|cloudfront\.net|amazonaws\.com|execute-api", re.I)


@pytest.fixture
def configured() -> Iterator[Harness]:
    h = make_harness({"OPN_API_PUBLIC_URL": PUBLIC + "/"})
    with h.client:
        yield h


@pytest.mark.parametrize("path", ["/llms.txt", "/robots.txt"])
def test_both_files_are_open_reads_with_no_d35_row(path: str) -> None:
    (spec,) = [r for r in routes.ROUTES if r.label == f"GET {path}"]
    assert not spec.authenticated and not spec.write and spec.d35 is None


def test_llms_txt_names_where_an_agent_starts_as_full_urls(configured: Harness) -> None:
    r = configured.client.get("/llms.txt")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/plain")
    text = r.text
    assert text.startswith("# Open Proof Network\n")
    guide = configured.client.get("/").json()["guide"]  # the index's own guide link
    for url in (
        guide,
        f"{PUBLIC}/",
        f"{PUBLIC}/info.json",
        f"{PUBLIC}/errors.json",
        f"{PUBLIC}/mcp",
    ):
        assert f"]({url})" in text, url
    assert "//info.json" not in text and f"{PUBLIC}//" not in text  # the trailing slash is trimmed


def test_llms_txt_follows_the_configured_origin(harness: Harness) -> None:
    """The default harness has another origin; the file follows it, so no origin is written in."""
    origin = harness.settings.public_url
    assert origin != PUBLIC
    text = harness.client.get("/llms.txt").text
    assert f"]({origin}/errors.json)" in text
    assert PUBLIC not in text


def test_robots_txt_allows_everything_and_names_no_path(harness: Harness) -> None:
    r = harness.client.get("/robots.txt")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/plain")
    lines = [line.strip() for line in r.text.splitlines() if line.strip()]
    assert lines[0] == "User-agent: *"
    assert "Allow: /" in lines
    assert not [line for line in lines if line.lower().startswith("disallow") and line[9:].strip()]


def test_no_hostname_literal_in_the_service_source() -> None:
    offenders = [
        str(p.relative_to(API_PKG))
        for p in sorted(API_PKG.rglob("*.py"))
        if HOSTNAME_RE.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == []
