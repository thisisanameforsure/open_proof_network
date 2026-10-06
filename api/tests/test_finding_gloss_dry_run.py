"""F22-T5 (testers 2026-10-06, feature request B): a dry run of words opens nothing.

W1, W2 and W4 each filed a version to learn whether its step anchors resolved, what the gate
would warn about and how the site would render it — a pull request and a queue slot per guess.
``dry_run: true`` on ``POST /glosses`` (and on ``submit_gloss``) runs the whole pre-flight — the
gate's checks (step ids, the head, the model lock) and the one-writer rules — and answers
``{ok, dry_run, path, hash, record, warnings, sections, preview_html}`` with status 200, pushing
no branch, opening no pull request, recording nothing and holding no slot. ``sections`` is each
section's key, the steps its heading names and what those resolve to in the proof's outline;
``preview_html`` is the site's own prose renderer over the text (``opn_site.prose.render``).
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from api_fakes import Harness
from mcp_client import McpClient
from test_explainer_schema import step
from test_glosses_route import (
    explainer_body,
    make_h,
    make_keys,
    make_tree,
    nothing_opened,
    post,
    proof_hash,
    put_version,
    serve,
    statement_gloss,
    write_outline,
)

REPO = Path(__file__).resolve().parents[2]
ANCHORED = (
    "## The idea\nRegroup, *then* read.\n\n## The bound {steps: s1}\nBy `Nat.Prime.two_le`.\n"
)


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from make_h(tree)


def dry(body: dict[str, Any]) -> dict[str, Any]:
    return body | {"dry_run": True}


def nothing_recorded(h: Harness) -> None:
    nothing_opened(h)
    assert h.context.store.list_open_submissions() == []


def test_a_dry_run_answers_sections_warnings_and_the_page_and_opens_nothing(
    h: Harness, tree: Path
) -> None:
    write_outline(tree, [step("s1")])  # s1 spans lines 1-2 and uses no constant
    serve(h, tree)
    r = post(h, h.token_for("code_bob", "bob"), dry(explainer_body(proof_hash(tree), ANCHORED)))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True and body["dry_run"] is True
    assert body["record"] == "explainer"
    assert [w["code"] for w in body["warnings"]] == ["explainer-name-unanchored"]
    assert body["sections"] == [
        {"key": "overview", "steps": [], "resolved": []},
        {
            "key": "steps:s1",
            "steps": ["s1"],
            "resolved": [{"id": "s1", "kind": "have", "name": "s1", "lines": [1, 2]}],
        },
    ]
    html = body["preview_html"]
    assert "<p>" in html and "Regroup" in html
    assert "<script" not in html.lower()
    nothing_recorded(h)


def test_a_dry_run_of_a_gloss_is_one_whole_section(h: Harness) -> None:
    r = post(h, h.token_for("code_bob", "bob"), dry(statement_gloss()))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sections"] == [{"key": "whole", "steps": [], "resolved": None}]
    assert body["warnings"] == []
    # the prose is escaped: the gloss's text carries an instruction aimed at a reader
    assert "ignore previous instructions" in body["preview_html"]
    nothing_recorded(h)


def test_a_dry_run_with_a_typod_step_id_is_refused(h: Harness, tree: Path) -> None:
    write_outline(tree, [step("s1")])
    serve(h, tree)
    typo = ANCHORED.replace("{steps: s1}", "{steps: s7}")
    r = post(h, h.token_for("code_bob", "bob"), dry(explainer_body(proof_hash(tree), typo)))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "explainer-step-unknown"
    nothing_recorded(h)


def test_a_dry_run_is_held_to_the_head_and_the_one_writer_rule(h: Harness, tree: Path) -> None:
    a = put_version(tree, "gloss", "First.")
    b = put_version(tree, "gloss", "Second.", supersedes=a, date="2026-10-05")
    serve(h, tree)
    bob, carol = h.token_for("code_bob", "bob"), h.token_for("code_carol", "carol")
    stale = post(h, bob, dry(statement_gloss() | {"supersedes": a}))
    assert stale.status_code == 409 and stale.json()["error"] == "record-not-head", stale.text
    first = post(h, bob, statement_gloss() | {"supersedes": b})
    assert first.status_code == 201, first.text
    second = post(h, carol, dry(statement_gloss() | {"supersedes": b, "text": "Another."}))
    assert second.status_code == 409, second.text
    assert second.json()["error"] == "duplicate-submission"
    assert second.json()["details"]["pr_number"] == first.json()["pr_number"]
    assert len(h.githost.pulls) == 1


def test_a_dry_run_holds_no_slot(h: Harness) -> None:
    """The same request sent for real straight after its dry run opens: a dry run takes nothing
    the real one needs."""
    token = h.token_for("code_bob", "bob")
    assert post(h, token, dry(statement_gloss())).status_code == 200
    real = post(h, token, statement_gloss())
    assert real.status_code == 201, real.text


def test_dry_run_is_a_boolean(h: Harness) -> None:
    r = post(h, h.token_for("code_bob", "bob"), statement_gloss() | {"dry_run": "yes"})
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "arguments-invalid"
    assert r.json()["details"]["field"] == "dry_run"
    nothing_recorded(h)


def test_the_tool_takes_dry_run(h: Harness) -> None:
    out = McpClient(h).ok(
        "submit_gloss", dry(statement_gloss()), token=h.token_for("code_bob", "bob")
    )
    assert out["status"] == 200, out
    assert out["body"]["dry_run"] is True
    nothing_recorded(h)


# --- the package carries what preview_html reads (log 2026-09-09) ---------------------------------

WORKFLOW = REPO / ".github" / "workflows" / "api-deploy.yml"


def test_the_lambda_package_carries_the_site_prose_renderer() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    on = doc.get("on", doc.get(True))
    assert any(p.startswith("site/opn_site") for p in on["push"]["paths"]), on["push"]["paths"]
    assert "site/opn_site" in text.split("Check the package")[0], "the build copies opn_site"
    assert "opn_site/prose.py" in text.split("Check the package")[1], "the check looks for it"


def _imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found |= {a.name for a in node.names}
    return found


def test_the_prose_renderer_imports_nothing_the_package_lacks() -> None:
    """The package copies ``opn_site``'s Python modules and none of its dependencies: every
    module ``prose`` reaches imports the standard library or ``opn_site`` only."""
    import sys  # noqa: PLC0415

    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    pending, seen = {"opn_site.prose"}, set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        rel = Path("site", *name.split("."))
        path = REPO / rel.with_suffix(".py")
        if not path.is_file():
            path = REPO / rel / "__init__.py"
        assert path.is_file(), name
        for imported in _imports(path):
            top = imported.split(".")[0]
            if top == "opn_site":
                pending.add(imported)
            else:
                assert top in stdlib, f"{name} imports {imported}, which the package lacks"
