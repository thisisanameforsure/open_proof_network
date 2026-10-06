"""F22-T4 (testers 2026-10-06, feature request A): the gate's warnings reach the writer.

The gate tells an explainer's pull request what it warns about without refusing it
(``modes.warnings``: today ``explainer-name-unanchored``), and until now only the Actions log
said so: W1, W3 and W4 never saw theirs. The pre-flight computes them over the same scratch tree
it judges, and they go back in the 201 answer (``warnings``, each ``{code, message, details}``),
through the MCP tool body for body, and into the pull request's body.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from api_fakes import Harness
from mcp_client import McpClient
from test_explainer_schema import step
from test_glosses_route import (
    explainer_body,
    make_h,
    make_keys,
    make_tree,
    post,
    proof_hash,
    serve,
    statement_gloss,
    write_outline,
)

UNANCHORED = "explainer-name-unanchored"
CITING = "## The idea\nRegroup.\n\n## The bound {steps: s1}\nBy `Nat.Prime.two_le` it holds.\n"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from make_h(tree)


def test_an_explainer_citing_an_unused_name_is_told_so(h: Harness, tree: Path) -> None:
    write_outline(tree, [step("s1")])  # s1 uses no constant at all
    serve(h, tree)
    r = post(h, h.token_for("code_bob", "bob"), explainer_body(proof_hash(tree), CITING))
    assert r.status_code == 201, r.text
    body = r.json()
    assert "warnings" in body, body
    [warning] = body["warnings"]
    assert warning["code"] == UNANCHORED
    assert warning["details"]["name"] == "Nat.Prime.two_le"
    pr_body = h.githost.pulls[-1].body
    assert UNANCHORED in pr_body and "Nat.Prime.two_le" in pr_body, pr_body


def test_words_with_nothing_to_warn_about_answer_an_empty_list(h: Harness) -> None:
    r = post(h, h.token_for("code_bob", "bob"), statement_gloss())
    assert r.status_code == 201, r.text
    assert r.json().get("warnings") == [], r.json()
    assert "warn" not in h.githost.pulls[-1].body.lower()


def test_the_tool_carries_the_warnings(h: Harness, tree: Path) -> None:
    write_outline(tree, [step("s1")])
    serve(h, tree)
    args = explainer_body(proof_hash(tree), CITING)
    out = McpClient(h).ok("submit_gloss", args, token=h.token_for("code_bob", "bob"))
    assert out["status"] == 201, out
    assert [w["code"] for w in out["body"].get("warnings", ["missing"])] == [UNANCHORED]
