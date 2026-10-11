"""F22-T10 (testers 2026-10-06, request L, service half): one spelling of a model's name.

R1 counted three spellings of one model across one target's ``drafted_with`` values, two of
them differing only in spacing (a doubled space, a trailing newline). The service writes the
value with its whitespace normalised — each run of whitespace one space, none at either end —
and nothing else changed: the words are the contributor's (D-23), so ``Claude Opus`` is never
rewritten to ``claude-opus``. The tool's parameter description prescribes the one format,
``<model name> (<model id>)``.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from api_fakes import Harness
from mcp_client import McpClient
from test_glosses_route import make_h, make_keys, make_tree, post, statement_gloss

from opn_gate import glosses


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def h(tmp_path: Path, keys: dict[str, Path]) -> Iterator[Harness]:
    yield from make_h(make_tree(tmp_path, keys))


def landed_drafted_with(h: Harness) -> object:
    doc, _ = glosses.split_front_matter(next(iter(h.githost.pushes[-1].files.values())))
    assert doc is not None
    return doc["drafted_with"]


def test_whitespace_is_normalised_and_nothing_else(h: Harness) -> None:
    sent = "  Claude Opus 5.5\t (claude-opus-5-5)\n"
    r = post(h, h.token_for("code_bob", "bob"), statement_gloss() | {"drafted_with": sent})
    assert r.status_code == 201, r.text
    assert landed_drafted_with(h) == "Claude Opus 5.5 (claude-opus-5-5)"


def test_only_whitespace_is_no_model(h: Harness) -> None:
    r = post(h, h.token_for("code_bob", "bob"), statement_gloss() | {"drafted_with": " \n "})
    assert r.status_code == 201, r.text
    assert landed_drafted_with(h) is None


def test_the_tool_prescribes_one_format(h: Harness) -> None:
    [tool] = [t for t in McpClient(h).list_tools() if t.name == "submit_gloss"]
    described = tool.inputSchema["properties"]["drafted_with"]["description"]
    assert "<model name> (<model id>)" in described, described
