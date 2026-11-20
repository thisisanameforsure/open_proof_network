"""F22-T29 (2026-11-19 run, B10): an explainer of a merged partial is named the way
``list_words_needed`` names it.

The words-needed row of a merged partial says ``kind: partial`` with the artifact's hash as
``lean_hash``. Two agents sent that back: ``{kind: partial, proof: <hash>}`` was refused
``subject-invalid`` "names the merged partial by its path", the path was refused too, and
``{kind: partial, module: <path>}`` with an explainer's text was silently filed as a *gloss* of
the partial (its route's approach words). Only ``{kind: proof, node_id, proof: <hash>}`` worked.

Now a subject with a ``proof`` is an explainer whatever artifact kind the row gave it (``proof``,
``alternate`` or ``partial``); a gloss whose text names outline steps — which only an explainer
reads — is refused rather than filed as a gloss, naming the explainer subject to send; and every
``subject-invalid`` says the shape it accepts.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from api_fakes import Harness
from test_glosses_route import (
    NODE,
    NODE_DIR,
    make_h,
    make_keys,
    make_tree,
    nothing_opened,
    post,
    proof_hash,
)

from opn_gate import schemas

PARTIAL = "attempts/20260920T000000Z-alice-partial.lean"
ALTERNATE = "attempts/20260921T000000Z-alice-alternate.lean"
EXPLAINER = "## The idea\nSplit at the conjunction, then recombine.\n"
ANCHORED = EXPLAINER + "\n## The split {steps: s1}\nEach half on its own.\n"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    """The route test's tree with one merged partial and one merged alternate under the node."""
    root = make_tree(tmp_path, keys)
    attempts = root / NODE_DIR / "attempts"
    attempts.mkdir(exist_ok=True)
    (attempts / PARTIAL.split("/")[1]).write_text(
        "theorem x : True := by\n  sorry\n", encoding="utf-8"
    )
    (attempts / ALTERNATE.split("/")[1]).write_text(
        "theorem y : True := trivial\n", encoding="utf-8"
    )
    return root


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from make_h(tree)


def artifact_hash(tree: Path, rel: str) -> str:
    return schemas.content_hash((tree / NODE_DIR / rel).read_bytes())


def request(subject: dict[str, Any], text: str = EXPLAINER, **over: Any) -> dict[str, Any]:
    return {"subject": {"node_id": NODE, **subject}, "text": text, "licence": "CC-BY-4.0", **over}


def landed_front(h: Harness) -> tuple[str, dict[str, Any]]:
    [(path, content)] = h.githost.pushes[-1].files.items()
    return path, yaml.safe_load(content.split("---\n")[1])


@pytest.mark.parametrize(("kind", "rel"), [("partial", PARTIAL), ("alternate", ALTERNATE)])
def test_the_row_s_kind_with_its_hash_files_an_explainer(
    h: Harness, tree: Path, kind: str, rel: str
) -> None:
    digest = artifact_hash(tree, rel)
    r = post(h, h.token_for("code_bob", "bob"), request({"kind": kind, "proof": digest}))
    assert r.status_code == 201, r.text
    assert r.json()["record"] == "explainer"
    path, front = landed_front(h)
    assert path.startswith(f"{NODE_DIR}/explainer/")
    assert front["schema"] == "explainer/v2"
    assert front["proof"] == digest


def test_a_dry_run_of_the_row_s_kind_is_an_explainer(h: Harness, tree: Path) -> None:
    digest = artifact_hash(tree, PARTIAL)
    body = request({"kind": "partial", "proof": digest}, dry_run=True)
    r = post(h, h.token_for("code_bob", "bob"), body)
    assert r.status_code == 200, r.text
    assert r.json()["record"] == "explainer"
    assert r.json()["sections"][0]["key"] == "overview"
    nothing_opened(h)


def test_an_explainer_s_text_sent_as_a_partial_gloss_is_refused_not_reinterpreted(
    h: Harness, tree: Path
) -> None:
    r = post(
        h, h.token_for("code_bob", "bob"), request({"kind": "partial", "module": PARTIAL}, ANCHORED)
    )
    assert r.status_code == 400, r.text
    doc = r.json()
    assert doc["error"] == "subject-invalid"
    # the refusal names the subject that files these words as the partial's explainer
    assert doc["details"]["explainer_subject"] == {
        "kind": "partial",
        "node_id": NODE,
        "proof": artifact_hash(tree, PARTIAL),
    }
    assert "explainer" in doc["message"]
    nothing_opened(h)


def test_a_statement_gloss_whose_text_names_steps_is_refused(h: Harness, tree: Path) -> None:
    r = post(h, h.token_for("code_bob", "bob"), request({"kind": "statement"}, ANCHORED))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "subject-invalid"
    assert r.json()["details"]["explainer_subject"] is None  # a statement is no artifact
    nothing_opened(h)


def test_a_partial_gloss_without_anchors_is_still_the_route_s_words(h: Harness) -> None:
    """F29-T9 stands: approach words about a route are a gloss of the partial."""
    r = post(h, h.token_for("code_bob", "bob"), request({"kind": "partial", "module": PARTIAL}))
    assert r.status_code == 201, r.text
    assert r.json()["record"] == "gloss"


@pytest.mark.parametrize(
    "proof",
    [PARTIAL, f"{NODE_DIR}/{PARTIAL}", "not-a-hash"],
)
def test_a_proof_that_is_not_a_hash_says_the_shape_and_where_the_hash_is(
    h: Harness, proof: str
) -> None:
    r = post(h, h.token_for("code_bob", "bob"), request({"kind": "partial", "proof": proof}))
    assert r.status_code == 400, r.text
    doc = r.json()
    assert doc["error"] == "subject-invalid"
    assert "{kind, node_id, proof}" in doc["message"]
    assert "lean_hash" in doc["message"]
    nothing_opened(h)


def test_a_partial_named_by_neither_module_nor_proof_says_both_shapes(h: Harness) -> None:
    r = post(h, h.token_for("code_bob", "bob"), request({"kind": "partial"}))
    assert r.status_code == 400, r.text
    message = r.json()["message"]
    assert r.json()["error"] == "subject-invalid"
    assert "module" in message and "proof" in message and "explainer" in message


def test_module_and_proof_together_are_refused(h: Harness, tree: Path) -> None:
    subject = {"kind": "partial", "module": PARTIAL, "proof": artifact_hash(tree, PARTIAL)}
    r = post(h, h.token_for("code_bob", "bob"), request(subject))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "subject-invalid"


def test_the_proof_kind_is_unchanged(h: Harness, tree: Path) -> None:
    r = post(
        h, h.token_for("code_bob", "bob"), request({"kind": "proof", "proof": proof_hash(tree)})
    )
    assert r.status_code == 201, r.text
    assert r.json()["record"] == "explainer"
