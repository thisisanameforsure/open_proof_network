"""F10-T14: the guide says what shipped for the 2026-09-24 testers' findings.

Six outside agents worked the calibration targets for an hour on 2026-09-24. What they found was
fixed in the service and the site (F05-T14, F05-T15, F07-T39 to T43, F08-T18, F08-T19, F09-T13,
F13-T17 to T20, F04-T26, F06-T9), and the guide had to follow, because an agent reads the guide and
not the code: it said AXLE "runs none of the hazard checkers", that only a merged proposal waits on
``products``, and nothing about the check's size limit, the heartbeat cap, circular nodes still
reading ``ready``, or the new routes. Where a sentence states a number or a word the code defines,
the test reads the code's value, so the two cannot drift apart again (log, 2026-09-11: docs are
tests).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from opn_api import checks, config, pending, routes

ROOT = Path(__file__).resolve().parents[2]
GUIDE = (ROOT / "gate" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
FLAT = re.sub(r"\s+", " ", GUIDE)
GRAPH = ROOT.parent / "open_proof_network_graph"

GONE = {
    "AXLE runs no hazard checker": "runs none of the hazard checkers",
    "only a merged proposal waits on products": "or, for a merged proposal, `products`",
}

PRESENT = {
    "the witness that does not compile is refused": "`422 witness-fails`",
    "a witness passes only when both hold": "`okay` and `witness.matches` both hold",
    "the hazard pre-flight refuses": "`422 hazard-unacknowledged`",
    "the hazards mode": '`"mode": "hazards"`',
    "a held theorem name is refused": "`409 declaration-clash`",
    "the heartbeat cap and its remedy": "200000 heartbeats",
    "set_option before the theorem is refused": "`proof-not-statement`",
    "the dropped naming warning": "`dropped_warnings`",
    "claiming twice returns the same claim": "returns the same claim",
    "the receipt's other holders": "`others`",
    "the caller's own claims": "`GET /claims/mine`",
    "products for annexes and witnesses": "`products` for a merged proposal, annex or witness",
    "jobs is always present": "each run's `jobs` is `[]`",
    "a proposal's statement": "`proposed_statement`",
    "withdrawing a pull request": "`DELETE /submissions/<id>`",
    "rivals in a proof's receipt": "`rivals`",
    "a proof on a proved node becomes an alternate": '`becomes: "alternate"`',
    "a second circularity claim is refused": "`circular-decomposition` claim on a node already",
    "an open claim of the same class is named": "`also_open`",
    "circular is a cause, not a status": "read `cause`, not `status`",
    "the service's rendered_from": "service's `rendered_from` is the commit it read the tree at",
    "the tutorial node without a clone": "`targets/tutorial/nodes/tutorial-and-swap/`",
    "the MCP list_my_claims row": "| `list_my_claims` | `GET /claims/mine`",
    "the MCP withdraw_submission row": (
        "| `withdraw_submission(submission_id)` | `DELETE /submissions/<id>`"
    ),
}


@pytest.mark.parametrize("what", sorted(GONE))
def test_a_sentence_the_network_contradicts_is_gone(what: str) -> None:
    assert GONE[what] not in FLAT, what


@pytest.mark.parametrize("what", sorted(PRESENT))
def test_the_guide_says(what: str) -> None:
    assert PRESENT[what] in FLAT, what


def test_the_size_limit_is_the_services() -> None:
    assert config.DEFAULT_CHECK_MAX_BYTES == 200_000
    assert "at most 200 kB (`413 content-too-large`" in FLAT


def test_the_time_budget_is_the_services() -> None:
    assert f"The budget is {config.DEFAULT_CHECK_TIMEOUT_S} seconds" in FLAT


def test_the_proposed_statement_cap_is_the_services() -> None:
    assert pending.PROPOSED_STATEMENT_MAX_BYTES == 16 * 1024
    assert "up to 16 kB" in FLAT


def test_every_witness_pre_flight_word_is_the_services() -> None:
    for word in (
        checks.PREFLIGHT_MATCHED,
        checks.PREFLIGHT_INCONCLUSIVE,
        checks.PREFLIGHT_UNAVAILABLE,
    ):
        assert f"`{word}`" in FLAT, word


def test_every_hazard_pre_flight_word_is_the_services() -> None:
    words = (checks.PREFLIGHT_CLEAR, checks.PREFLIGHT_INCONCLUSIVE, checks.PREFLIGHT_UNAVAILABLE)
    assert "`hazards_preflight` says " + ", ".join(f"`{w}`" for w in words[:2]) in FLAT


def test_the_new_routes_the_guide_names_exist() -> None:
    served = {(r.method, r.path) for r in routes.ROUTES}
    assert ("GET", "/claims/mine") in served
    assert ("DELETE", "/submissions/{submission_id}") in served


@pytest.mark.skipif(not (GRAPH / ".git").exists(), reason="the graph repo is not checked out")
def test_the_tutorial_path_the_guide_names_is_the_graphs() -> None:
    meta = GRAPH / "targets" / "tutorial" / "nodes" / "tutorial-and-swap" / "META.yaml"
    assert meta.is_file()
