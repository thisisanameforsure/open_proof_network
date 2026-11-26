"""mcpfix (the owner, 2026-11-26): the Docs say what the MCP is now — three tools, ``search``,
``read`` and ``write``, over the service's operations (D-28 v3.50) — and say it where a reader
meets each route, not in one paragraph of the Quick start.

Held three ways, so the pages cannot drift from the server again:

* every operation a page names as ``<code>read</code> with <code>X</code>`` (or ``write``) is an
  operation the server declares, of that kind;
* every route a page shows that has an operation is paired with it on the same page;
* the Connect page's worked calls are valid calls: each validates against its tool's schema and
  its ``arguments`` against the operation's own.
"""

from __future__ import annotations

import html
import json
import re

import fixture
import jsonschema
import pytest
from docs_pages import docs_page, docs_rels

from opn_api.mcp import bijection, surface
from opn_api.mcp.server import TOOLS
from opn_site import model, render

API = "https://api.test.invalid"
REPO = "https://github.com/example/graph"

BY_NAME = {t.name: t for t in TOOLS}
NAMED_RE = re.compile(r"<code>(read|write)</code>\s+with\s+<code>([a-z_]+)</code>")
#: A route a page shows: ``POST $OPN_API/claims``, ``GET $OPN_API/precheck/<id>``, or a curl.
SHOWN_RE = re.compile(
    r"(?:\b(GET|POST|DELETE)\s+\"?\$OPN_API|curl(?:\s+-X\s+(POST|DELETE))?[^\n\"]*\"\$OPN_API)"
    r"(/(?:<[a-z_-]+>|[^\s\"'<),])*)"
)


def normal(path: str) -> str:
    """A path with every placeholder (``<id>``, ``{job_id}``) as ``{}``, no query, no slash."""
    path = re.sub(r"<[^>]*>|\{[^}]*\}|…", "{}", path.split("?", maxsplit=1)[0]).rstrip("/.")
    return path or "/"


#: Each route label the bijection pairs with operations, normalised, to those operations: one
#: route may stand behind several (``GET /frontier.json``), and naming any one covers it.
OPERATIONS_OF: dict[tuple[str, str], set[str]] = {}
for _row in bijection.TABLE:
    for _label in _row.routes:
        _method, _path = _label.split(" ", 1)
        OPERATIONS_OF.setdefault((_method, normal(_path)), set()).add(_row.tool)


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("site"))
    site = model.load_site(root, fixture.COMMIT)
    return render.render_site(site, repo_url=REPO, api_url=API)


def text(page: str) -> str:
    """The page's main column as text, tags kept, entities decoded."""
    main = page[page.index('<article class="docs-main">') : page.index('<nav class="prevnext"')]
    return html.unescape(main)


def test_every_named_operation_exists_with_its_kind(pages: dict[str, str]) -> None:
    named = 0
    for rel in docs_rels():
        for kind, name in NAMED_RE.findall(text(pages[rel])):
            named += 1
            assert name in BY_NAME, (rel, name)
            assert ("write" if BY_NAME[name].write else "read") == kind, (rel, name, kind)
    assert named >= 10, named  # the step pages name their operations, not one paragraph


def test_every_shown_route_names_its_operation(pages: dict[str, str]) -> None:
    missing = []
    for rel in docs_rels():
        if rel == "docs/connect/index.html":
            continue
        body = text(pages[rel])
        named = {name for _k, name in NAMED_RE.findall(body)}
        for m in SHOWN_RE.finditer(body):
            method = m.group(1) or m.group(2) or ("POST" if "--data" in m.group(0) else "GET")
            operations = OPERATIONS_OF.get((method, normal(m.group(3))), set())
            if operations and not operations & named:
                missing.append((rel, f"{method} {m.group(3)}", sorted(operations)))
    assert not missing, missing


def connect_section(pages: dict[str, str]) -> str:
    body = text(docs_page(pages, "connect"))
    return body[body.index('id="tools"') : body.index('id="harnesses"')]


def test_connect_says_what_the_server_offers(pages: dict[str, str]) -> None:
    section = connect_section(pages)
    for tool in surface.NAMES:
        assert f"<code>{tool}</code>" in section, tool
    assert "?surface=v1" in section  # the named tools, for a client built against them
    allow = section[section.index('id="permissions"') :]
    assert "<code>search</code>" in allow and "<code>read</code>" in allow
    assert "<code>write</code>" in allow


def test_connect_examples_are_valid_calls(pages: dict[str, str]) -> None:
    section = connect_section(pages)
    blocks = "\n".join(re.findall(r"<pre[^>]*><code>(.*?)</code></pre>", section, flags=re.S))
    calls = re.findall(r"^(search|read|write) (\{.*\})$", blocks, flags=re.M)
    assert {tool for tool, _ in calls} == set(surface.NAMES), calls
    for tool, raw in calls:
        call = json.loads(raw)
        schema = surface.SEARCH_SCHEMA if tool == "search" else surface.call_schema(tool)
        jsonschema.validate(call, schema)
        if tool != "search":
            operation = BY_NAME[call["operation"]]
            assert ("write" if operation.write else "read") == tool, call
            jsonschema.validate(call["arguments"], operation.input_schema)


def test_no_page_speaks_of_read_or_write_tools(pages: dict[str, str]) -> None:
    """There are no "read tools" or "write tools" any more: one tool of each, over operations."""
    for rel in docs_rels():
        body = re.sub(r"<[^>]+>", "", text(pages[rel]))
        assert not re.search(r"\b(read|write) tools\b", body, flags=re.I), rel


def test_the_landing_page_points_an_agent_at_the_mcp(pages: dict[str, str]) -> None:
    body = text(docs_page(pages, ""))
    card = body[body.index("Agent operators") :]
    card = card[: card.index("</section>")]
    assert 'href="/docs/connect/"' in card and "MCP" in card
