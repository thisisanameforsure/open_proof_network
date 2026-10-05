"""F21-AC4 (R5, Q4, Q5; D-3 v3.31): one writer per file.

Writing the words for a file is a few minutes' work, and two people writing them at once costs one
of them those minutes plus a gate round for a version nobody will keep. So ``POST /glosses``
refuses a *new chain* (no ``supersedes``) on a subject for which an open pull request that can
still merge already adds a version: ``409 duplicate-submission``, naming that pull request, with
no branch pushed. A pull request whose gate failed, or that conflicts, blocks nothing; another
file is another subject; and a request that supersedes is not subject to this rule (the gate's
own head rule settles a race between two of those, F20-Q3).

The subject rides in the submission's fingerprints as ``words:<target>:<file-or-proof-hash>``
(Q5): a gloss's Lean file relative to its target, an explainer's proof hash.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from test_glosses_route import (
    NODE,
    TARGET,
    make_h,
    make_keys,
    make_tree,
    post,
    proof_hash,
    put_version,
    serve,
)

from opn_gate import schemas

GATE_FAILED = [{"name": "gate", "status": "completed", "conclusion": "failure", "url": "r"}]
OTHER_NODE = "tutorial-and-swap"  # listed in the api fixture's products


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from make_h(tree)


def gloss(text: str, *, kind: str = "statement", node: str = NODE, **extra: Any) -> dict[str, Any]:
    return {
        "subject": {"kind": kind, "node_id": node},
        "text": text,
        "licence": "CC-BY-4.0",
        **extra,
    }


def explainer(proof: str, text: str, *, node: str = NODE) -> dict[str, Any]:
    return {
        "subject": {"kind": "proof", "node_id": node, "proof": proof},
        "text": f"## The idea\n{text}\n",
        "licence": "CC-BY-4.0",
    }


def tokens(h: Harness) -> tuple[str, str]:
    return h.token_for("code_bob", "bob"), h.token_for("code_carol", "carol")


def refused_naming(h: Harness, r: Any, first: Any, pushes: int) -> None:
    assert r.status_code == 409, r.text
    body = r.json()
    assert body["error"] == "duplicate-submission"
    assert body["details"]["pr_number"] == first.json()["pr_number"]
    assert len(h.githost.pushes) == pushes, "no branch may be pushed for a refused request"


# --- glosses, keyed by the Lean file --------------------------------------------------------------


def test_a_second_writer_of_the_same_file_is_refused_naming_the_first(h: Harness) -> None:
    bob, dave = tokens(h)
    first = post(h, bob, gloss("Conjunction reassociates, read left to right."))
    assert first.status_code == 201, first.text
    pushes = len(h.githost.pushes)
    second = post(h, dave, gloss("Grouping the conjuncts either way gives the same claim."))
    refused_naming(h, second, first, pushes)


def test_after_the_first_writers_gate_failed_a_new_chain_passes(h: Harness) -> None:
    bob, dave = tokens(h)
    first = post(h, bob, gloss("Conjunction reassociates, read left to right."))
    assert first.status_code == 201, first.text
    h.githost.set_pull_request_state(first.json()["pr_number"], runs=GATE_FAILED)
    h.clock.advance(minutes=5)
    second = post(h, dave, gloss("Grouping the conjuncts either way gives the same claim."))
    assert second.status_code == 201, second.text


def test_another_file_is_another_writer(h: Harness) -> None:
    """The node's witness is another file than its statement, and another node's statement is
    another file again."""
    bob, dave = tokens(h)
    first = post(h, bob, gloss("Conjunction reassociates, read left to right."))
    assert first.status_code == 201, first.text
    witness = post(h, dave, gloss("The witness exhibits three true propositions.", kind="witness"))
    assert witness.status_code == 201, witness.text
    other = post(h, dave, gloss("Swapping and regrouping conjuncts.", node=OTHER_NODE))
    assert other.status_code == 201, other.text


def test_a_superseding_request_is_not_refused_by_this_rule(h: Harness, tree: Path) -> None:
    head = put_version(tree, "gloss", "Merged words.")
    serve(h, tree)
    bob, dave = tokens(h)
    first = post(h, bob, gloss("Bob's correction of the merged words.", supersedes=head))
    assert first.status_code == 201, first.text
    second = post(h, dave, gloss("Carol's correction of the merged words.", supersedes=head))
    assert second.status_code == 201, second.text


def test_an_open_superseding_version_blocks_a_new_chain_on_its_file(h: Harness, tree: Path) -> None:
    """R5 counts any open pull request that adds a version of the subject, a superseding one
    included: the rule is about who is writing the file now, not about chains."""
    head = put_version(tree, "gloss", "Merged words.")
    serve(h, tree)
    bob, dave = tokens(h)
    first = post(h, bob, gloss("Bob's correction of the merged words.", supersedes=head))
    assert first.status_code == 201, first.text
    pushes = len(h.githost.pushes)
    second = post(h, dave, gloss("Carol starts a chain of his own."))
    refused_naming(h, second, first, pushes)


# --- explainers, keyed by the proof hash ----------------------------------------------------------


def test_explainers_of_one_proof_have_one_writer(h: Harness, tree: Path) -> None:
    bob, dave = tokens(h)
    proof = proof_hash(tree)
    first = post(h, bob, explainer(proof, "Regroup the conjuncts."))
    assert first.status_code == 201, first.text
    pushes = len(h.githost.pushes)
    second = post(h, dave, explainer(proof, "Take the conjuncts apart and put them back."))
    refused_naming(h, second, first, pushes)

    h.githost.set_pull_request_state(first.json()["pr_number"], runs=GATE_FAILED)
    h.context.pulls.clear()  # the refusal above read the state; the service's cache ages out
    h.clock.advance(minutes=5)
    again = post(h, dave, explainer(proof, "Take the conjuncts apart and put them back."))
    assert again.status_code == 201, again.text


def test_an_explainer_of_another_proof_passes(h: Harness, tree: Path) -> None:
    bob, dave = tokens(h)
    first = post(h, bob, explainer(proof_hash(tree), "Regroup the conjuncts."))
    assert first.status_code == 201, first.text
    other_proof = (tree / "targets" / TARGET / "nodes" / OTHER_NODE / "Proof.lean").read_bytes()
    other = post(
        h,
        dave,
        explainer(schemas.content_hash(other_proof), "Swap, then regroup.", node=OTHER_NODE),
    )
    assert other.status_code == 201, other.text
