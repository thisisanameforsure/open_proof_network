"""F22-T28 (2026-11-19 run, B9): an explainer whose outline is not rendered yet waits, it is not
wrong.

The outline of a merged proof artifact is written by its own job after the post-merge job has
pushed (F19-T4), and the service reads it at main's head through its own cache window. In that
gap ``POST /glosses`` (dry run included) refused an anchored explainer with
``explainer-step-unknown`` "...has no outline", which reads as permanent: three agents in the
run took it so. When the subject is a merged artifact of the node and the service has no outline
of it, a section that names steps answers ``409 products-pending`` with ``Retry-After``; once the
outline is there, a step it lacks is ``explainer-step-unknown`` as before, and an explainer that
names no step never waits.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from test_explainer_schema import step
from test_glosses_route import (
    explainer_body,
    make_h,
    make_keys,
    make_tree,
    nothing_opened,
    post,
    proof_hash,
    serve,
    write_outline,
)

ANCHORED = "## The idea\nRegroup.\n\n## The bound {steps: s1}\nIt holds.\n"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from make_h(tree)


@pytest.mark.parametrize("dry_run", [False, True])
def test_an_anchored_explainer_of_a_merged_proof_without_its_outline_is_products_pending(
    h: Harness, tree: Path, dry_run: bool
) -> None:
    body: dict[str, Any] = explainer_body(proof_hash(tree), ANCHORED)
    if dry_run:
        body["dry_run"] = True
    r = post(h, h.token_for("code_bob", "bob"), body)
    assert r.status_code == 409, r.text
    doc = r.json()
    assert doc["error"] == "products-pending", doc
    assert int(r.headers["retry-after"]) > 0
    assert doc["details"]["proof"] == proof_hash(tree)
    assert doc["details"]["outline"].endswith(f"outlines/{proof_hash(tree)}.json")
    nothing_opened(h)


def test_once_the_outline_is_there_a_wrong_step_is_still_step_unknown(
    h: Harness, tree: Path
) -> None:
    write_outline(tree, [step("s2")])
    serve(h, tree)
    r = post(h, h.token_for("code_bob", "bob"), explainer_body(proof_hash(tree), ANCHORED))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "explainer-step-unknown"
    nothing_opened(h)


def test_an_explainer_naming_no_step_never_waits_for_the_outline(h: Harness, tree: Path) -> None:
    r = post(h, h.token_for("code_bob", "bob"), explainer_body(proof_hash(tree)))
    assert r.status_code == 201, r.text


def test_an_artifact_that_is_not_merged_is_still_proof_unknown(h: Harness) -> None:
    r = post(h, h.token_for("code_bob", "bob"), explainer_body("b" * 64, ANCHORED))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "explainer-proof-unknown"
