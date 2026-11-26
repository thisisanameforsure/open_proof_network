"""mcpfix WB2 item 4 (testers 2026-11-25, qa-ea): ``GET /submissions.json`` took any ``kind`` and
any ``target`` and answered an empty list for both, so a typo read as "nothing open".

``kind`` is now one of the service's submission kinds (``pending.SUBMISSION_KINDS``, one union of
the sets the modules kept apart) or ``words``; anything else is ``400 filter-unknown`` naming the
kinds. A ``target`` that ``targets/index.json`` does not list is ``404 not-found``, as the list
tools answer for one.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from api_fakes import Harness
from test_finding_submissions_filters import numbers, opened
from test_glosses_route import make_h, make_keys, make_tree

from opn_api import duplicates, pending, store, submissions

API = Path(__file__).resolve().parents[1] / "opn_api"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def h(tmp_path: Path, keys: dict[str, Path]) -> Iterator[Harness]:
    yield from make_h(make_tree(tmp_path, keys))


def test_an_unknown_kind_is_refused_naming_the_kinds(h: Harness) -> None:
    r = h.client.get("/submissions.json?kind=nonsense")
    assert r.status_code == 400, r.text
    body = r.json()
    assert body["error"] == "filter-unknown"
    assert "annex" in body["message"] and "gloss" in body["message"], body["message"]
    assert "words" in body["details"]["accepted_kinds"]


def test_an_unknown_target_is_not_found(h: Harness) -> None:
    r = h.client.get("/submissions.json?target=elsewhere")
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "not-found"


def test_every_known_kind_and_target_still_filter(h: Harness) -> None:
    prs = opened(h)
    for kind in pending.SUBMISSION_KINDS:
        r = h.client.get(f"/submissions.json?kind={kind}")
        assert r.status_code == 200, (kind, r.text)
    assert numbers(h, "?kind=annex") == [prs["annex"]]
    assert numbers(h, "?target=propositional") == sorted(prs.values())


def test_the_union_holds_every_scattered_set() -> None:
    union = set(pending.SUBMISSION_KINDS)
    for part in (
        duplicates.WORDS_KINDS,
        duplicates.PROOF_KINDS,
        duplicates.APPEND_KINDS,
        pending.ATTESTING_KINDS,
        store.PROPOSAL_KINDS,
        pending.WORDS_KINDS_ON_NODE,
        pending.WORDS_KINDS_ON_TARGET,
        submissions.ARTIFACT_TYPES,
    ):
        assert set(part) <= union, set(part) - union


def test_the_union_holds_every_kind_a_route_records() -> None:
    """Every ``kind="..."`` a route passes and every ``KIND* = "..."`` constant in the service."""
    found: set[str] = set()
    pattern = re.compile(r'(?:\bkind="([a-z-]+)"|^KIND[A-Z_]* = "([a-z-]+)")', re.MULTILINE)
    for path in API.glob("*.py"):
        for m in pattern.finditer(path.read_text()):
            found.add(m.group(1) or m.group(2))
    assert found, "the scan found nothing: the pattern is wrong"
    assert found <= set(pending.SUBMISSION_KINDS), found - set(pending.SUBMISSION_KINDS)
