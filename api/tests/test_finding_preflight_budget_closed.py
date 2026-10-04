"""F13-T28 (audit 2026-10-04; the owner's ruling amending F13-Q22): a pre-flight fails closed
when the caller's check budget is spent.

Until now every pre-flight caught the budget's 429 and answered ``unavailable``, so the pull
request opened anyway: a caller whose hourly checks were spent could still open as many
proposals, witnesses and exhibit-carrying appends as the write limit allowed, each one a queue
slot and a full gate run, with none of them checked first. The owner reversed that: a spent
budget is the caller's to wait out, and the route answers 429 with ``Retry-After`` before any
branch or pull request exists and before the checker is asked. The checks a route needs are
reserved together up front, so a proposal never spends half its pre-flights and then stops.

What did not change: a checker that cannot answer (an outage, an error, no hosted environment)
still lets the pull request open with ``unavailable`` — that is the network's failure, not the
caller's, and the gate decides (D-4 v3.14).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
import samples
import test_finding_hazards_preflight as hazards
from api_fakes import AXLE_OKAY, Harness, make_harness
from mcp_client import TARGET
from test_finding_exhibit_preflight import EXHIBIT, claim, revision
from test_finding_witness_preflight import MATCH, PIN, RIGHT, harness, speculative, token, variant
from test_finding_witness_route_preflight import propose, with_hole

from opn_api.axle import AxleError
from opn_gate import schemas


def spent(h: Harness) -> Harness:
    """The caller's one check this hour, spent on ``POST /check``."""
    first = h.client.post(
        "/check", json={"target_id": TARGET, "content": RIGHT}, headers=h.auth(token(h))
    )
    assert first.status_code == 200, first.text
    assert len(h.axle.calls) == 1
    return h


def budget_one(*replies: Any) -> Harness:
    return harness(*replies, env={"OPN_API_CHECKS_PER_HOUR": "1"})


ROUTES: dict[str, Callable[[Harness], Any]] = {
    "speculative": lambda h: speculative(h, RIGHT),
    "variant": lambda h: variant(h, RIGHT),
    "witness": lambda h: propose(with_hole(h), RIGHT),
    "defect-claim": claim,
    "revision-request": lambda h: revision(h, EXHIBIT),
}


@pytest.mark.parametrize("route", sorted(ROUTES))
def test_a_spent_check_budget_refuses_before_anything_opens(route: str) -> None:
    h = spent(budget_one(MATCH, MATCH, MATCH))
    r = ROUTES[route](h)
    assert r.status_code == 429, r.text
    assert r.json()["error"] == "rate-limited"
    assert int(r.headers["retry-after"]) > 0
    # A branch exists only as a push to it (``FakeGitHost.push_files``): none, and no PR.
    assert h.githost.pushes == [] and h.githost.pulls == [], "no branch, no pull request"
    assert len(h.axle.calls) == 1, "the checker was not asked"
    assert len(h.store.checks) == 1  # only the /check that spent the budget is logged


@pytest.mark.parametrize("route", sorted(ROUTES))
def test_a_checker_that_fails_still_lets_the_pull_request_open(route: str) -> None:
    """The network's failure, not the caller's: unchanged by the ruling."""
    down = AxleError("AXLE check returned 502", status=502)
    h = harness(down, down, down)
    r = ROUTES[route](h)
    assert r.status_code == 201, r.text
    words = {k: v for k, v in r.json().items() if k.endswith("_preflight")}
    assert "unavailable" in words.values(), words
    assert len(h.githost.pulls) == 1


def test_a_reservation_that_does_not_fit_spends_nothing() -> None:
    """A speculative node on a target with hazard checkers needs two checks (step 6's and step
    7's pre-flights). With one left it is refused whole — before, one pre-flight ran and the other
    said ``unavailable`` — and the one left is still there for the caller's next check."""
    fake = hazards.RoutingAxle(
        replies=[hazards.WITNESS_MATCH, AXLE_OKAY], hazards=[hazards.found()]
    )
    h = make_harness({"OPN_API_CHECKS_PER_HOUR": "1"}, axle=fake)
    h.githost.files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(mathlib_sha=PIN, hazard_checkers=hazards.CHECKERS)
    )
    h.context.files.clear()
    r = hazards.speculative(h)
    assert r.status_code == 429, r.text
    assert h.axle.calls == []
    assert h.githost.pushes == [] and h.githost.pulls == []
    again = h.client.post(
        "/check", json={"target_id": TARGET, "content": RIGHT}, headers=h.auth(token(h))
    )
    assert again.status_code == 200, again.text
