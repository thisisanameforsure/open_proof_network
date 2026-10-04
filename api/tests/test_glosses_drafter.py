"""F20-T10: a draft through ``POST /glosses`` (R2, R10, R18; Q6).

The drafter is a named identity holding a contributor token (F20-Q6). What makes its version a
*draft* is two fields of the record — no ``author``, and a ``drafter`` block naming it, the model
and version that wrote the text, and the graph commit its input was read at (D-23, R18) — and the
service must write them only for that identity. Before T10 the route had no drafter field, so a
draft would have landed with ``opn-drafter`` as a human ``author``.

The rule asserted here: the identity whose pseudonym is the configured ``OPN_API_DRAFTER_PSEUDONYM``
files with ``author: null`` and the ``drafter`` block taken from the request (its ``name`` the
identity's own pseudonym), and must send one; any other identity sending a ``drafter`` block is
refused by name, before anything opens; and with no drafter configured nobody is one. The shape
that lands passes the gate as the merge will run it, opened by the service's login.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from test_glosses_route import (
    NODE_DIR,
    landed,
    make_keys,
    make_tree,
    nothing_opened,
    post,
    serve,
    statement_gloss,
)

from opn_api.githost import GitHubUser
from opn_gate import glosses

DRAFTER = "opn-drafter"
COMMIT = "c" * 40
BLOCK = {
    "model": "claude-opus-5",
    "model_version": "claude-opus-5-20261001",
    "input_commit": COMMIT,
}


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


def harness(tree: Path, env: dict[str, str]) -> Iterator[Harness]:
    h = make_harness(env)
    h.githost.users["code_drafter"] = GitHubUser("opn-drafter-bot", 1009, "2026-10-01T00:00:00Z")
    serve(h, tree)
    with h.client:
        yield h


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from harness(tree, {"OPN_API_DRAFTER_PSEUDONYM": DRAFTER})


@pytest.fixture
def unconfigured(tree: Path) -> Iterator[Harness]:
    yield from harness(tree, {})


def drafted(**block: Any) -> dict[str, Any]:
    return statement_gloss() | {"drafter": {**BLOCK, **block}}


def test_the_drafter_files_a_draft_with_no_author(h: Harness, tree: Path, tmp_path: Path) -> None:
    """The record lands with ``author: null`` and the drafter block, named for the identity
    itself; the gate passes the landed shape, opened by the service."""
    token = h.token_for("code_drafter", DRAFTER)
    r = post(h, token, drafted())
    assert r.status_code == 201, r.text
    [(path, content)] = h.githost.pushes[-1].files.items()
    assert path.startswith(f"{NODE_DIR}/gloss/")
    doc, _ = glosses.split_front_matter(content)
    assert doc is not None
    assert doc["author"] is None
    assert doc["drafter"] == {"name": DRAFTER, **BLOCK}
    assert landed(h, tree, tmp_path) == []


def test_the_drafter_may_name_itself_but_no_one_else(h: Harness) -> None:
    token = h.token_for("code_drafter", DRAFTER)
    r = post(h, token, drafted(name=DRAFTER))
    assert r.status_code == 201, r.text
    r = post(h, token, drafted(name="someone-else"))
    assert r.status_code == 400 and r.json()["error"] == "drafter-invalid", r.text


def test_another_identity_sending_a_drafter_block_is_refused(h: Harness) -> None:
    r = post(h, h.token_for("code_bob", "bob"), drafted())
    assert r.status_code == 403, r.text
    assert r.json()["error"] == "drafter-unauthorized"
    nothing_opened(h)


def test_no_identity_is_the_drafter_until_one_is_configured(unconfigured: Harness) -> None:
    token = unconfigured.token_for("code_drafter", DRAFTER)
    r = post(unconfigured, token, drafted())
    assert r.status_code == 403, r.text
    assert r.json()["error"] == "drafter-unauthorized"
    nothing_opened(unconfigured)


def test_the_drafter_must_say_what_wrote_the_text(h: Harness) -> None:
    """A draft without its block would land as a human version authored ``opn-drafter``; one with
    a malformed block (no model, a short commit, a key the schema does not know) is refused."""
    token = h.token_for("code_drafter", DRAFTER)
    for body in (
        statement_gloss(),
        statement_gloss() | {"drafter": "claude"},
        statement_gloss() | {"drafter": {"model_version": "x", "input_commit": COMMIT}},
        drafted(input_commit="abc123"),
        drafted(prompt="opn-drafter-prompts/1"),
    ):
        r = post(h, token, body)
        assert r.status_code == 400, (body, r.text)
        assert r.json()["error"] == "drafter-invalid", (body, r.text)
    nothing_opened(h)


def test_a_person_files_as_before(h: Harness, tree: Path, tmp_path: Path) -> None:
    """Unchanged for everyone else: the author is the token's pseudonym, no drafter."""
    r = post(h, h.token_for("code_bob", "bob"), statement_gloss())
    assert r.status_code == 201, r.text
    [(_, content)] = h.githost.pushes[-1].files.items()
    doc, _ = glosses.split_front_matter(content)
    assert doc is not None and doc["author"] == "bob" and doc["drafter"] is None
    assert landed(h, tree, tmp_path) == []
