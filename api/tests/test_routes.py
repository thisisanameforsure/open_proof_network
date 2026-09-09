"""F05-T1 / AC18: the routes table against D-35's plain-path list (R1)."""

from __future__ import annotations

import html
import re
from pathlib import Path

from api_fakes import Harness

from opn_api import routes
from opn_api.app import resolve

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "docs" / "architecture_decisions_v_3_11.html"


def d35_rows() -> set[str]:
    """Every ``METHOD /path`` D-35's plain-path table names, verbatim (``<id>`` kept)."""
    text = DECISIONS.read_text(encoding="utf-8")
    start = text.index('id="d-35"')
    end = text.index('id="d-36"')
    found = re.findall(r"<code>((?:GET|POST|DELETE) /[^<]+)</code>", text[start:end])
    return {html.unescape(f) for f in found}


def test_routes_match_d35() -> None:
    """AC18: every write route has a D-35 row, and every row a shipped feature owns has a route."""
    rows = d35_rows()
    owned = routes.D35_OWNED_BY_F05 | routes.D35_OWNED_BY_F06
    assert rows >= owned, rows
    write_rows = {r.d35 for r in routes.ROUTES if r.write}
    assert None not in write_rows  # every write route names its D-35 row
    assert write_rows == routes.D35_OWNED_BY_F05 | {routes.D35_POST_PRECHECK}
    for r in routes.ROUTES:
        assert r.d35 is None or r.d35 in rows, r
        assert r.feature in ("F05", "F06"), r


def test_precheck_routes_match_d35() -> None:
    """F06-AC13: both precheck routes map to D-35's precheck_submission row."""
    rows = d35_rows()
    assert rows >= routes.D35_OWNED_BY_F06, rows
    precheck = {r.label: r for r in routes.ROUTES if r.feature == "F06"}
    assert precheck["POST /precheck"].d35 == routes.D35_POST_PRECHECK
    assert precheck["GET /precheck/{job_id}"].d35 == routes.D35_GET_PRECHECK
    # The POST is the write; the GET is the polling read D-28 pairs with it.
    assert precheck["POST /precheck"].write
    assert not precheck["GET /precheck/{job_id}"].write
    # R2/Q2: the route table does not demand a bearer, because the tutorial node is open.
    assert not precheck["POST /precheck"].authenticated


def test_every_handler_resolves() -> None:
    seen = set()
    for r in routes.ROUTES:
        assert callable(resolve(r.handler)), r.handler
        assert (r.method, r.path) not in seen
        seen.add((r.method, r.path))
    assert all(r.authenticated for r in routes.ROUTES if r.write and r.path.startswith("/claims"))


def test_read_routes_ignore_bearer(harness: Harness) -> None:
    """R5: a bearer on a read route is ignored, even a bad one."""
    r = harness.client.get("/dco.json", headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 200
    assert r.json()["version"]
