"""F05-T12: ``GET /`` lists the service's routes (F05-Q13).

An outside contributor, 2026-09-18, arrived at the service's hostname from a link on the site
and asked it what it offers: ``/`` and ``/openapi.json`` both answered ``404 not-found``. The
only index of routes was ``routes.ROUTES``, in process. ``info.json`` cannot carry one: it is the
graph's product, ``info/v1`` is closed and hash-pinned (D-34), and F13 met the same wall and
gave ``/hosted-checkers.json`` its own route (F13-Q12), which is the precedent here.

The index is served from the routes table itself, so a route cannot be added without appearing
in it, and a test refuses a route with no sentence saying what it is for.
"""

from __future__ import annotations

from api_fakes import Harness

from opn_api import routes

INDEX = "GET /"


def test_the_index_is_an_open_read_with_no_d35_row() -> None:
    (spec,) = [r for r in routes.ROUTES if r.label == INDEX]
    assert not spec.authenticated and not spec.write and spec.d35 is None


def test_every_route_says_what_it_is_for() -> None:
    labels = {r.label for r in routes.ROUTES}
    assert set(routes.PURPOSES) == labels
    for label, purpose in routes.PURPOSES.items():
        assert len(purpose) > 20 and purpose.endswith("."), label


def test_the_index_lists_exactly_the_routes_table(harness: Harness) -> None:
    r = harness.client.get("/")
    assert r.status_code == 200, r.text
    doc = r.json()
    listed = [(e["method"], e["path"]) for e in doc["routes"]]
    assert listed == [(s.method, s.path) for s in routes.ROUTES]
    by_label = {f"{e['method']} {e['path']}": e for e in doc["routes"]}
    assert by_label["POST /claims"]["auth"] == "bearer"
    assert by_label["POST /check"]["auth"] == "none"
    assert by_label["GET /frontier.json"]["purpose"] == routes.PURPOSES["GET /frontier.json"]
    assert set(by_label[INDEX]) == {"method", "path", "auth", "purpose"}


def test_the_index_points_at_the_guide_and_the_mcp_endpoint(harness: Harness) -> None:
    doc = harness.client.get("/").json()
    repo, branch = harness.context.settings.graph_repo, harness.context.settings.graph_branch
    assert doc["guide"] == f"https://github.com/{repo}/blob/{branch}/AGENTS.md"
    assert doc["mcp"] == "/mcp"
    assert doc["authoritative_for"] == "nothing: the graph repository is the record (D-35)"


def test_an_unknown_path_is_still_not_found(harness: Harness) -> None:
    assert harness.client.get("/openapi.json").status_code == 404
