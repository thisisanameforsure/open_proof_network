"""F07-T85 (bug B11, agent run 2026-11-19): a ``duplicate-submission`` says what matched and names
the pull request.

An agent's explainer was refused "an identical explainer for this node was submitted in the last 2
minutes", with no ``details.pr_number``, when the open pull request (#1512) was another author's
different text on the same subject. The guide says the refusal names the pull request.

The words came from the slot guard (``duplicates.take``), which every request holds for two
minutes so that two arriving together cannot both open (F07-T35). It holds two kinds of slot: the
content's fingerprint (identical text) and, for a gloss or an explainer, its subject (one writer
at a time, F21-R5) or its chain head (F22-T1). The message said "identical" for all of them, and
named nobody, though the rival's record usually exists already. Here it is a subject slot held by
a pull request whose gate has failed: the one-writer rule sets that one aside (``blocks``), so
the request reached the slot, which was still within its window.

The refusal now says which slot matched (``details.matched``: ``text``, ``subject``,
``chain-head`` or ``slot``) and names the open pull request that holds it, when the service has
its record (``pr_number``, ``pr_url``, ``submission_id``).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from test_glosses_one_writer import GATE_FAILED, explainer, gloss, tokens
from test_glosses_route import make_h, make_keys, make_tree, post, proof_hash


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from make_h(tree)


def slot_refusal(r: Any) -> dict[str, Any]:
    assert r.status_code == 409, r.text
    body: dict[str, Any] = r.json()
    assert body["error"] == "duplicate-submission"
    assert int(r.headers["Retry-After"]) > 0
    return body


def test_a_different_explainer_on_the_same_subject_is_not_called_identical(
    h: Harness, tree: Path
) -> None:
    bob, dave = tokens(h)
    proof = proof_hash(tree)
    first = post(h, bob, explainer(proof, "Regroup the conjuncts."))
    assert first.status_code == 201, first.text
    h.githost.set_pull_request_state(first.json()["pr_number"], runs=GATE_FAILED)
    body = slot_refusal(post(h, dave, explainer(proof, "Take the conjuncts apart.")))
    assert "identical" not in body["message"]
    assert "same subject" in body["message"]
    assert body["details"]["matched"] == "subject"
    assert body["details"]["pr_number"] == first.json()["pr_number"]
    assert body["details"]["pr_url"] == first.json()["pr_url"]
    assert f"#{first.json()['pr_number']}" in body["message"]


def test_identical_text_is_still_called_identical_and_names_the_pull_request(h: Harness) -> None:
    """The same gloss twice inside the window, the first's gate failed: the content slot."""
    bob, _ = tokens(h)
    first = post(h, bob, gloss("Conjunction reassociates, read left to right."))
    assert first.status_code == 201, first.text
    h.githost.set_pull_request_state(first.json()["pr_number"], runs=GATE_FAILED)
    body = slot_refusal(post(h, bob, gloss("Conjunction reassociates, read left to right.")))
    assert "identical" in body["message"]
    assert body["details"]["matched"] == "text"
    assert body["details"]["pr_number"] == first.json()["pr_number"]
