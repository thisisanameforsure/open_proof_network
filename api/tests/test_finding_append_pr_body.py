"""F22-T3 (testers 2026-10-06, P3-16): an append's pull-request body reads as English and says
what the gate checks for that kind.

W1 read "A explainer appended through the Open Proof Network service ... It claims nothing: the
gate checks its path and its schema" on an explainer, whose gate checks far more than that (the
proof it describes, its chain head, its sections against the outline, the lock on words a person
wrote). The article now follows the kind, and the sentence names the checks the kind gets.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from api_fakes import TUTORIAL_NODE, Harness
from test_glosses_route import (
    explainer_body,
    make_h,
    make_keys,
    make_tree,
    post,
    statement_gloss,
)

from opn_gate import schemas

TARGET = "propositional"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def h(tmp_path: Path, keys: dict[str, Path]) -> Iterator[Harness]:
    yield from make_h(make_tree(tmp_path, keys))


def body_of(h: Harness) -> str:
    return h.githost.pulls[-1].body


def test_an_explainer_body_reads_an_explainer_and_names_its_checks(h: Harness) -> None:
    r = post(h, h.token_for("code_bob", "bob"), explainer_body(_proof(h)))
    assert r.status_code == 201, r.text
    body = body_of(h)
    assert body.startswith("An explainer appended"), body
    assert "A explainer" not in body
    assert "its path and its schema (F07-R9)" not in body, "an explainer gets more checks"
    for check in ("proof", "head", "outline"):
        assert check in body, (check, body)


def test_a_gloss_body_names_its_checks(h: Harness) -> None:
    r = post(h, h.token_for("code_bob", "bob"), statement_gloss())
    assert r.status_code == 201, r.text
    body = body_of(h)
    assert body.startswith("A gloss appended"), body
    assert "Lean file" in body and "head" in body, body


def test_an_annex_and_an_approach_record_take_an(h: Harness) -> None:
    token = h.token_for("code_alice", "alice")
    annex = h.client.post(
        "/annexes",
        json={"node_id": TUTORIAL_NODE, "text": "Symmetry.\n", "licence": "CC-BY-4.0"},
        headers=h.auth(token),
    )
    assert annex.status_code == 201, annex.text
    assert body_of(h).startswith("An annex appended"), body_of(h)
    assert "its path and its schema" in body_of(h)
    record = {"route": "normalise both sides and compare", "outcome": "exhausted"}
    approach = h.client.post(
        "/approach-records",
        json={"target_id": TARGET, "record": record},
        headers=h.auth(token),
    )
    assert approach.status_code == 201, approach.text
    assert body_of(h).startswith("An approach record appended"), body_of(h)


def _proof(h: Harness) -> str:
    raw = h.githost.files[f"targets/{TARGET}/nodes/and-reassoc/Proof.lean"]
    return schemas.content_hash(raw)
