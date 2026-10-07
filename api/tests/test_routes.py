"""F05-T1 / AC18: the routes table against D-35's plain-path list (R1)."""

from __future__ import annotations

import html
import re
from pathlib import Path

from api_fakes import Harness

from opn_api import routes
from opn_api.app import resolve

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "docs" / "architecture_decisions.html"


def d35_rows() -> set[str]:
    """Every ``METHOD /path`` D-35's plain-path table names, verbatim (``<id>`` kept)."""
    text = DECISIONS.read_text(encoding="utf-8")
    start = text.index('id="d-35"')
    end = text.index('id="d-36"')
    found = re.findall(r"<code>((?:GET|POST|DELETE) /[^<]+)</code>", text[start:end])
    return {html.unescape(f) for f in found}


def d35_text() -> str:
    """D-35's section as plain text, for the rows whose plain path is a pull request rather
    than an endpoint — the three append tools share one such row (F07)."""
    text = DECISIONS.read_text(encoding="utf-8")
    section = text[text.index('id="d-35"') : text.index('id="d-36"')]
    return html.unescape(re.sub(r"<[^>]+>", "", section))


def test_routes_match_d35() -> None:
    """AC18: every write route has a D-35 row, and every row a shipped feature owns has a route."""
    rows = d35_rows()
    owned = routes.D35_OWNED_BY_F05 | routes.D35_OWNED_BY_F06 | {routes.D35_POST_SUBMISSIONS}
    owned |= routes.D35_OWNED_BY_F13  # F13-T3: D-35 v3.14's check_lean row
    owned |= routes.D35_OWNED_BY_F20  # F20-T6: D-35 v3.30's submit_gloss, withdraw_gloss row
    owned |= routes.D35_OWNED_BY_F23  # F23: D-35 v3.33's web session, stewards, approvals row
    assert rows >= owned, rows
    # The append row names no endpoint: D-35's plain path for the three append tools is the
    # pull request itself, quoted here verbatim so a reworded decision fails this test.
    assert routes.D35_APPEND_PR in d35_text()
    write_rows = {r.d35 for r in routes.ROUTES if r.write}
    assert None not in write_rows  # every write route names its D-35 row
    assert write_rows == routes.D35_OWNED_BY_F05 | {routes.D35_POST_PRECHECK} | (
        routes.D35_OWNED_BY_F07
        | routes.D35_OWNED_BY_F08
        | routes.D35_OWNED_BY_F13
        | routes.D35_OWNED_BY_F20
        | (routes.D35_OWNED_BY_F23 - {routes.D35_GET_SESSION})  # GET /session is a read
    )
    assert routes.D35_PROPOSAL_PR in d35_text()  # F08's rows, verbatim like the append row
    assert routes.D35_CLAIM_PR in d35_text()
    pr_rows = {routes.D35_APPEND_PR, routes.D35_PROPOSAL_PR, routes.D35_CLAIM_PR}
    for r in routes.ROUTES:
        assert r.d35 is None or r.d35 in rows or r.d35 in pr_rows, r
        assert r.feature in ("F05", "F06", "F07", "F08", "F13", "F20", "F23"), r


def test_web_sign_in_falls_under_the_token_row() -> None:
    """F23-T3: ``POST /auth/web/accept`` finishes a GitHub sign-in under the D-19 identity rules,
    as ``GET /auth/github/start`` and the callback do, so it is D-35's token row; the v3.33 row
    names the session's own routes, and sign-in is not among them."""
    accept = {r.label: r for r in routes.ROUTES}["POST /auth/web/accept"]
    assert accept.d35 == routes.D35_POST_TOKENS and not accept.authenticated


def test_f07_routes_are_authenticated_writes() -> None:
    """F07-R1, R11: every submission and append route needs a token and names its D-35 row.
    F07-T16 added F07's two reads, which are neither: open, like ``/frontier.json``, and with
    no D-35 row, since D-28 lists reads as mirrors rather than endpoints of their own. F07-T70
    added a third with no D-35 row, ``GET /submissions/mine``, which needs the caller's token
    because what it reads is the caller's own, as ``GET /claims/mine`` does."""
    f07_reads = {r.label: r for r in routes.ROUTES if r.feature == "F07" and not r.write}
    assert set(f07_reads) == {
        "GET /submissions.json",
        "GET /submissions/mine",
        "GET /submissions/{submission_id}",
    }
    for spec in f07_reads.values():
        mine = spec.label == "GET /submissions/mine"
        assert spec.authenticated == mine and spec.d35 is None, spec
    f07 = {r.label: r for r in routes.ROUTES if r.feature == "F07" and r.write}
    assert set(f07) == {
        "POST /submissions",
        "POST /postmortems",
        "POST /annexes",
        "POST /approach-records",
        "DELETE /submissions/{submission_id}",  # F07-T43 (ruling D5)
    }
    for spec in f07.values():
        assert spec.write and spec.authenticated, spec
    assert f07["POST /submissions"].d35 == routes.D35_POST_SUBMISSIONS
    appends = ("POST /postmortems", "POST /annexes", "POST /approach-records")
    assert {f07[p].d35 for p in appends} == {routes.D35_APPEND_PR}
    assert f07["DELETE /submissions/{submission_id}"].d35 == routes.D35_DELETE_SUBMISSION


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
