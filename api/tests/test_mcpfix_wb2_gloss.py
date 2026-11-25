"""mcpfix WB2 item 5 (testers 2026-11-25, qa-eb B1 and L10): what POST /glosses took silently.

* ``drafted_with: "   "`` was normalised to nothing and read as "no model": a field sent with no
  words in it is a mistake to name, ``400 tooling-invalid``, on a dry run as on a real one.
  ``""`` and null stay "no model", as ``appends.declared`` has always read them.
* The ``<model name> (<model id>)`` shape is NOT enforced: measured on the live graph on
  2026-11-25, 289 of 792 merged non-null ``drafted_with`` values do not have it
  (engineering/evidence/mcpfix/wb2-5-drafted-with-measure.txt), so the description changes instead.
* A statement, witness or relation gloss whose text carries no LaTeX at all (no ``$``, ``\\(``
  or ``\\[``) answers a ``gloss-no-latex`` warning, never a refusal, on a dry run and a real one.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from test_glosses_route import make_h, make_keys, make_tree, post, statement_gloss


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def h(tmp_path: Path, keys: dict[str, Path]) -> Iterator[Harness]:
    yield from make_h(make_tree(tmp_path, keys))


def codes(doc: dict[str, Any]) -> list[str]:
    return [w["code"] for w in doc.get("warnings") or []]


@pytest.mark.parametrize("dry", [True, False])
@pytest.mark.parametrize("value", ["   ", "\t\n"])
def test_whitespace_only_drafted_with_is_tooling_invalid(h: Harness, dry: bool, value: str) -> None:
    bob = h.token_for("code_bob", "bob")
    r = post(h, bob, {**statement_gloss(), "drafted_with": value, "dry_run": dry})
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "tooling-invalid"
    assert "drafted_with" in r.json()["message"]
    assert h.githost.pulls == []


@pytest.mark.parametrize("value", [None, ""])
def test_null_or_empty_drafted_with_is_still_no_model(h: Harness, value: str | None) -> None:
    bob = h.token_for("code_bob", "bob")
    r = post(h, bob, {**statement_gloss(), "drafted_with": value, "dry_run": True})
    assert r.status_code == 200, r.text


def test_a_free_form_drafted_with_is_still_taken(h: Harness) -> None:
    """Not enforced: a third of the live record does not have the ``name (id)`` shape."""
    bob = h.token_for("code_bob", "bob")
    r = post(h, bob, {**statement_gloss(), "drafted_with": "some model", "dry_run": True})
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("dry", [True, False])
def test_a_statement_gloss_with_no_latex_is_warned(h: Harness, dry: bool) -> None:
    bob = h.token_for("code_bob", "bob")
    body = {**statement_gloss(), "dry_run": dry}
    assert "$" not in body["text"]
    r = post(h, bob, body)
    assert r.status_code == (200 if dry else 201), r.text
    assert "gloss-no-latex" in codes(r.json()), r.json()


@pytest.mark.parametrize("math", ["$p \\land q$", "\\(p\\)", "\\[p\\]"])
def test_a_statement_gloss_with_latex_is_not_warned(h: Harness, math: str) -> None:
    bob = h.token_for("code_bob", "bob")
    body = statement_gloss()
    body["text"] = f"{math} Associativity of conjunction, read left to right."
    r = post(h, bob, {**body, "dry_run": True})
    assert r.status_code == 200, r.text
    assert "gloss-no-latex" not in codes(r.json()), r.json()


def test_the_warning_is_catalogued() -> None:
    from opn_gate import codes as catalog  # noqa: PLC0415

    assert "gloss-no-latex" in catalog.CATALOG
