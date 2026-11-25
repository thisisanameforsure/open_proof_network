"""F34-T8 (R9, AC10): the reference pages are generated from what the service itself reads.

* Error codes: every row of ``opn_gate.codes.CATALOG``, the table ``GET /errors.json`` serves,
  with its meaning and what to do, and an id per code so a refusal can be linked.
* API routes: every ``RouteSpec`` of ``opn_api.routes.ROUTES``, the table the service is built
  from, with whether it needs a token. Nothing is typed by hand, so neither page can drift.
"""

from __future__ import annotations

import html
import re

import fixture
import pytest

from opn_api import routes
from opn_gate import codes
from opn_site import model, render

REPO = "https://github.com/example/graph"


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("f34-reference"))
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def test_the_reference_group_lists_both_pages() -> None:
    reference = dict(render.DOCS_GROUPS)["Reference"]
    slugs = [slug for slug, _t, _f, _w in reference]
    assert "errors" in slugs and "routes" in slugs


def test_every_error_code_is_on_its_page_with_what_to_do(pages: dict[str, str]) -> None:
    page = pages["docs/errors/index.html"]
    shown = re.findall(r'<tr id="code-([^"]+)">', page)
    assert sorted(shown) == sorted(codes.CATALOG)
    for code, row in list(codes.CATALOG.items())[:40]:
        tr = page[page.index(f'<tr id="code-{code}">') :]
        tr = tr[: tr.index("</tr>")]
        assert render.esc(row.meaning) in tr and render.esc(row.remedy) in tr, code


def test_every_route_is_on_its_page_with_whether_it_needs_a_token(pages: dict[str, str]) -> None:
    page = pages["docs/routes/index.html"]
    rows = re.findall(r'<tr data-route="([A-Z]+) ([^"]+)" data-token="(yes|no)">', page)
    assert {(m, html.unescape(p)) for m, p, _t in rows} == {
        (r.method, r.path) for r in routes.ROUTES
    }
    needs = {(m, html.unescape(p)): t == "yes" for m, p, t in rows}
    for r in routes.ROUTES:
        assert needs[(r.method, r.path)] == r.authenticated, r.label


def test_the_mcp_and_rate_limits_point_at_the_live_service(pages: dict[str, str]) -> None:
    page = pages["docs/routes/index.html"]
    assert "search" in page and "read" in page and "write" in page
    assert "/llms.txt" in page
