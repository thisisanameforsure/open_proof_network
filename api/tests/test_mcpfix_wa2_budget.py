"""mcpfix WA2 item 7: every read operation's default answer fits an agent's context.

A graph the size of the live one (450 targets, 606 frontier entries, one target with 69 of them,
every target with a glosses product of four subjects lacking words, erdos-1094's routes as the
products published them) and a node with 50 attempts and 30 long dependencies. Each read
operation called with no more than the arguments it requires answers under ``BUDGET``
characters of compact JSON, the form its text block takes (F09-T18), and the operations that
take ``full: true`` answer their plain path exactly with it (D-28).

``get_node`` is the one exception the owner's ruling makes: omitted, ``include`` answers
everything, as before (item 5); its compact form is ``include: []``, which is what is held to
the budget here.

Not held here: reads whose size grows with something other than the graph, which this fixture
leaves empty — ``list_submissions`` and ``get_my_submissions`` (the open pull requests),
``list_my_claims`` and ``get_check`` (one caller's records), ``get_submission`` and
``get_precheck`` (one record each).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from mcp_client import NODE, TARGET, McpClient
from mcpfix_wa2_fixture import TARGETS, compact, seed_large, target_id
from test_mcpfix_wa2_node_reviews import seed_big_node

from opn_api.mcp import reads

BUDGET = 25_000
ROUTES = Path(__file__).resolve().parents[2] / "gate" / "tests" / "fixtures" / "routes"
BIG = "erdos-1094"
SUBJECTS = 4


def glosses_doc(target: str) -> dict[str, Any]:
    """A ``glosses/v3`` product whose four subjects all lack words: the root's statement and
    three definition modules, as a bulk-loaded target's are."""
    subjects: list[dict[str, Any]] = [
        {
            "kind": "statement",
            "record": "gloss",
            "node": target,
            "module": None,
            "file": f"nodes/{target}/Statement.lean",
            "lean_hash": "a" * 64,
            "chains": [],
        }
    ] + [
        {
            "kind": "definition",
            "record": "gloss",
            "node": None,
            "module": f"Defs/Module{k}.lean",
            "file": f"defs/Defs/Module{k}.lean",
            "lean_hash": "b" * 64,
            "chains": [],
        }
        for k in range(SUBJECTS - 1)
    ]
    return {
        "schema": "glosses/v3",
        "target": target,
        "rendered_from": "5" * 40,
        "subjects": subjects,
    }


@pytest.fixture
def big(harness: Harness) -> Harness:
    return seed_big(harness)


def seed_big(harness: Harness) -> Harness:
    """The large graph and the large node, in the fake host."""
    seed_big_node(harness)
    seed_large(harness)
    files = harness.githost.files
    for i in range(TARGETS):
        t = target_id(i)
        files[f"targets/{t}/glosses.json"] = json.dumps(glosses_doc(t)).encode()
        files[f"targets/{t}/target.yaml"] = b"schema: target/v1\n"
        files[f"targets/{t}/graph.json"] = json.dumps(
            {
                "schema": "graph/v1",
                "target_id": t,
                "root": t,
                "rendered_from": "5" * 40,
                "nodes": [],
            }
        ).encode()
    graph = json.loads((ROUTES / f"{BIG}.json").read_text("utf-8"))["graph"]
    files[f"targets/{BIG}/graph.json"] = json.dumps(graph).encode()
    index = json.loads(files["targets/index.json"])
    for extra in (TARGET, BIG):  # the node's target and the routes' target, listed too
        row = dict(
            index["targets"][0], target_id=extra, root=graph["root"] if extra == BIG else NODE
        )
        index["targets"].append(row)
    files["targets/index.json"] = json.dumps(index).encode()
    harness.context.files.clear()
    harness.context.listings.clear()
    return harness


#: Each read operation held to the budget, with the arguments its default call takes.
DEFAULTS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("server_info", {}),
    ("list_targets", {}),
    ("get_target", {"target_id": TARGET}),
    ("list_frontier", {}),
    ("get_node", {"node_id": NODE, "include": []}),
    ("get_defs", {"target_id": TARGET}),
    ("get_gate_spec", {"target_id": TARGET}),
    ("get_dco", {}),
    ("list_routes", {}),
    ("get_hosted_checkers", {}),
    ("list_error_codes", {}),
    ("list_words_needed", {}),
    ("list_registrations", {}),
    ("list_review_questions", {}),
    ("list_open_pairs", {}),
    ("list_sufficient_sets", {"target_id": BIG}),
)
#: The reads this file does not hold, and why (the module docstring says more).
NOT_HELD = {
    "get_schema": "one schema file, named by the caller",
    "list_submissions": "the open pull requests",
    "get_my_submissions": "the caller's own",
    "list_my_claims": "the caller's own",
    "get_check": "one record",
    "get_submission": "one record",
    "get_precheck": "one record",
    "get_review": "one target's review",
}


def test_every_read_operation_is_held_or_named(harness: Harness) -> None:
    reads_ = {t.name for t in reads.TOOLS}
    assert reads_ == {name for name, _ in DEFAULTS} | set(NOT_HELD)


def test_every_default_answer_fits_the_budget(big: Harness) -> None:
    client = McpClient(big)
    sizes = {name: len(compact(client.ok(name, args))) for name, args in DEFAULTS}
    over = {name: size for name, size in sizes.items() if size >= BUDGET}
    assert not over, sizes


def test_the_full_forms_are_the_plain_paths(big: Harness) -> None:
    client = McpClient(big)
    assert client.ok("list_frontier", {"full": True}) == big.client.get("/frontier.json").json()
    assert client.ok("list_targets", {"full": True}) == json.loads(
        big.githost.files["targets/index.json"]
    )
    assert client.ok("list_error_codes", {"full": True}) == big.client.get("/errors.json").json()
    assert (
        client.ok("get_hosted_checkers", {"full": True})
        == big.client.get("/hosted-checkers.json").json()
    )


def test_words_needed_pages_cover_every_row_once(big: Harness) -> None:
    client = McpClient(big)
    first = client.ok("list_words_needed", {"limit": 200})
    rows, cursor = list(first["subjects"]), first["next"]
    while cursor is not None:
        more = client.ok("list_words_needed", {"limit": 200, "cursor": cursor})
        rows += more["subjects"]
        cursor = more["next"]
    assert len(rows) == first["count"] == TARGETS * SUBJECTS
    assert len({(r["target"], r["file"]) for r in rows}) == len(rows)


def test_hosted_checkers_by_default_count_the_targets(big: Harness) -> None:
    client = McpClient(big)
    full = client.ok("get_hosted_checkers", {"full": True})
    out = client.ok("get_hosted_checkers", {})
    assert "targets" not in out and out["target_count"] == len(full["targets"])
    some = next(iter(full["targets"]))
    one = client.ok("get_hosted_checkers", {"target_id": some})
    assert one["targets"] == {some: full["targets"][some]}
    assert client.failed("get_hosted_checkers", {"target_id": "no-such"})["error"] == "not-found"
