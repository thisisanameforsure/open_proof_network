"""F29-T9: ``POST /glosses`` takes a gloss of a merged partial (its route's approach words).

A merged partial is immutable and most live routes declared no ``-- approach:`` line, so the
problem page's selector says "route 1 of <label>" for them forever (F29-R4). The correction path
labels and claims already have is the gloss; this one is a ``gloss/v3`` of kind ``partial`` whose
subject names the partial's path under the node. The service validates that path by its grammar
before anything is read, so it can never leave the node; refuses a label on it (a label names a
statement); and ``submit_gloss`` forwards it body for body.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from mcp_client import McpClient
from test_glosses_route import (
    NODE,
    NODE_DIR,
    landed,
    make_h,
    make_keys,
    make_tree,
    nothing_opened,
    post,
)

from opn_api.mcp import results
from opn_gate import glosses, schemas

PARTIAL = "attempts/20260920T000000Z-alice-partial.lean"
WORDS = "Split at the conjunction and bound each half. Then recombine."


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    """The route test's tree with one merged partial under the node."""
    root = make_tree(tmp_path, keys)
    file = root / NODE_DIR / PARTIAL
    file.parent.mkdir(exist_ok=True)
    file.write_text("theorem x : True := by\n  sorry\n", encoding="utf-8")
    return root


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from make_h(tree)


def partial_gloss(**over: Any) -> dict[str, Any]:
    return {
        "subject": {"kind": "partial", "node_id": NODE, "module": PARTIAL},
        "text": WORDS + "\n",
        "licence": "CC-BY-4.0",
        **over,
    }


def test_a_partial_gloss_lands_as_gloss_v3_and_passes_the_preflight(
    h: Harness, tree: Path, tmp_path: Path
) -> None:
    token = h.token_for("code_bob", "bob")
    r = post(h, token, partial_gloss())
    assert r.status_code == 201, r.text
    [(path, content)] = h.githost.pushes[-1].files.items()
    assert path == f"{NODE_DIR}/gloss/{r.json()['hash']}.md"
    doc, body = glosses.split_front_matter(content)
    assert doc is not None and doc["schema"] == "gloss/v3"
    assert schemas.violations(doc, "gloss/v3") == []
    assert doc["subject"] == {
        "kind": "partial",
        "node": NODE,
        "module": PARTIAL,
        "lean_hash": schemas.content_hash((tree / NODE_DIR / PARTIAL).read_bytes()),
    }
    assert doc["label"] is None and doc["author"] == "bob"
    assert body.startswith(WORDS)
    assert r.json()["record"] == "gloss" and r.json()["lean_hash"] == doc["subject"]["lean_hash"]
    assert landed(h, tree, tmp_path) == []


@pytest.mark.parametrize(
    "module",
    [
        None,
        "Proof.lean",
        "attempts/../Proof.lean",
        "attempts/x-alternate.lean",
        "../x-partial.lean",
    ],
)
def test_a_module_that_is_not_a_partial_path_under_attempts_is_subject_invalid(
    h: Harness, module: str | None
) -> None:
    token = h.token_for("code_bob", "bob")
    body = partial_gloss()
    if module is None:
        del body["subject"]["module"]
    else:
        body["subject"]["module"] = module
    r = post(h, token, body)
    assert r.status_code == 400 and r.json()["error"] == "subject-invalid", r.text
    nothing_opened(h)


def test_a_partial_whose_path_is_not_in_the_tree_is_subject_unknown(h: Harness) -> None:
    token = h.token_for("code_bob", "bob")
    body = partial_gloss()
    body["subject"]["module"] = "attempts/20260101T000000Z-nobody-partial.lean"
    r = post(h, token, body)
    assert r.status_code == 400 and r.json()["error"] == "gloss-subject-unknown", r.text
    nothing_opened(h)


def test_a_label_on_a_partial_gloss_is_refused(h: Harness) -> None:
    token = h.token_for("code_bob", "bob")
    r = post(h, token, partial_gloss(label="Density route"))
    assert r.status_code == 400 and r.json()["error"] == "label-invalid", r.text
    nothing_opened(h)


def test_submit_gloss_forwards_a_partial_subject(h: Harness) -> None:
    token = h.token_for("code_bob", "bob")
    client = McpClient(h)
    listed = {t.name: t for t in client.list_tools()}
    kinds = listed["submit_gloss"].inputSchema["properties"]["subject"]["properties"]["kind"]
    assert "partial" in kinds["enum"]
    out = client.ok("submit_gloss", partial_gloss(), token=token)
    assert out["status"] == 201, out
    assert results.violations("submit_gloss", out) == []
    [(path, _)] = h.githost.pushes[-1].files.items()
    assert path == out["body"]["path"] == f"{NODE_DIR}/gloss/{out['body']['hash']}.md"
