"""mcpfix WA2 items 5 and 6 (testers 2026-11-25): ``get_node``'s bulk can be left out, and
``list_review_questions`` over every target reads only the targets that have a review.

Item 5 (t257b report, item 4): ``get_node {include: []}`` answered 91,002 characters on
``spec-a70fcca4--h4--h1--h1--h1`` and the client refused it. ``include: []`` was documented as
"the Lean, the context, ..." and the context still carried the attempt records and every
dependency's statement, and the statement's and witness's Lean a second time beside ``files``.
``include`` gains ``attempts`` and ``deps``; omitted, the answer is today's.

Item 6 (qa-ea U1): ``list_review_questions {}`` once answered HTTP 500 after 30 s, the Lambda's
limit: it read ``review/review.yaml`` for each of 445 targets in series, and a target with no
review answered 404 every time, because a 404 is not cached. The tree read the service already
keeps for the head says which targets have a review, so the others are never asked; the rest are
read in parallel, and the answer is paged.
"""

from __future__ import annotations

import json
from typing import Any

import yaml
from api_fakes import Harness
from mcp_client import NODE, TARGET, McpClient, seed_node
from mcpfix_wa2_fixture import compact, seed_large, target_id
from test_reviews_routes import question

BUDGET = 25_000
DEPS = 30
DEP_STATEMENT = (
    "/-- A dependency, stated at length. -/\ntheorem dep_{i} : "
    + " ∧ ".join(f"(∀ n : Nat, n + {k} = {k} + n)" for k in range(30))
    + " := by\n  sorry\n"
)


def seed_big_node(harness: Harness) -> None:
    """The fixture node with 50 attempts carrying long details and 30 proved dependencies, each
    a long statement: the shapes that made the live answer large."""
    seed_node(harness, attempts=50, detail="x" * 3000)
    path = f"targets/{TARGET}/graph.json"
    graph = json.loads(harness.githost.files[path])
    deps = [f"dep-{i}" for i in range(DEPS)]
    for row in graph["nodes"]:
        if row["node_id"] == NODE:
            row["deps"] = deps
    for i, dep in enumerate(deps):
        graph["nodes"].append({**graph["nodes"][0], "node_id": dep, "status": "proved", "deps": []})
        harness.githost.files[f"targets/{TARGET}/nodes/{dep}/Statement.lean"] = (
            DEP_STATEMENT.format(i=i).encode()
        )
    harness.githost.files[path] = json.dumps(graph).encode()
    harness.context.files.clear()
    harness.context.listings.clear()


def test_get_node_without_include_is_todays_answer(harness: Harness) -> None:
    seed_big_node(harness)
    out = McpClient(harness).ok("get_node", {"node_id": NODE})
    assert out["context"]["attempts"]["records"]
    assert len(out["context"]["deps"]) == DEPS
    assert all("signature" in d for d in out["context"]["deps"])
    assert "omitted" not in out["context"]


def test_get_node_include_empty_leaves_the_bulk_out(harness: Harness) -> None:
    seed_big_node(harness)
    client = McpClient(harness)
    before = compact(client.ok("get_node", {"node_id": NODE}))
    out = client.ok("get_node", {"node_id": NODE, "include": []})
    after = compact(out)
    assert len(after) < BUDGET, (len(before), len(after))
    context = out["context"]
    assert "records" not in context["attempts"] and context["attempts"]["count"] == 50
    assert [d["node_id"] for d in context["deps"]] == [f"dep-{i}" for i in range(DEPS)]
    assert all("signature" not in d for d in context["deps"])
    # the Lean is answered once, in files
    assert out["files"]["Statement.lean"] and context["statement"]["text"] is None
    assert set(context["omitted"]) >= {"attempts.records", "deps[].signature"}


def test_get_node_include_names_attempts_and_deps(harness: Harness) -> None:
    seed_big_node(harness)
    out = McpClient(harness).ok("get_node", {"node_id": NODE, "include": ["attempts", "deps"]})
    assert out["context"]["attempts"]["records"]
    assert all("signature" in d for d in out["context"]["deps"])
    assert "annexes" not in out and "explainers" not in out


# --- item 6: list_review_questions over every target --------------------------------------------

REVIEWED = (3, 17, 401)


def seed_reviews(harness: Harness) -> None:
    seed_large(harness)
    for i in REVIEWED:
        base = f"targets/{target_id(i)}/review"
        files = harness.githost.files
        files[f"{base}/review.yaml"] = b"schema: review/v1\nrole: proposer\n"
        for n in (1, 2):
            files[f"{base}/questions/q-{n}.yaml"] = yaml.safe_dump(
                question(n, target=target_id(i))
            ).encode()
    harness.context.files.clear()
    harness.context.listings.clear()


def review_heads(harness: Harness) -> list[str]:
    return [p for p, _ in harness.githost.fetches if p.endswith("/review/review.yaml")]


def test_questions_over_every_target_read_only_the_reviewed_ones(harness: Harness) -> None:
    seed_reviews(harness)
    client = McpClient(harness)
    out = client.ok("list_review_questions", {})
    assert out["count"] == 2 * len(REVIEWED)
    assert [q["target_id"] for q in out["questions"]] == [
        target_id(i) for i in REVIEWED for _ in (1, 2)
    ]
    heads = review_heads(harness)
    assert sorted(set(heads)) == sorted(
        f"targets/{target_id(i)}/review/review.yaml" for i in REVIEWED
    )
    harness.githost.fetches.clear()
    client.ok("list_review_questions", {})
    assert review_heads(harness) == []  # nothing asked again within the window


def test_questions_are_paged(harness: Harness) -> None:
    seed_reviews(harness)
    client = McpClient(harness)
    first: dict[str, Any] = client.ok("list_review_questions", {"limit": 4})
    assert len(first["questions"]) == 4 and first["next"] == "4" and first["count"] == 6
    rest = client.ok("list_review_questions", {"limit": 4, "cursor": first["next"]})
    assert len(rest["questions"]) == 2 and rest["next"] is None


def test_questions_without_the_tree_still_answer_every_reviewed_target(harness: Harness) -> None:
    """A tree the host truncated: each target's review.yaml is asked (in parallel), and the
    answer is the same."""
    seed_reviews(harness)
    harness.githost.tree_truncated = True
    out = McpClient(harness).ok("list_review_questions", {})
    assert out["count"] == 2 * len(REVIEWED)
    assert len(set(review_heads(harness))) == 450


def test_open_pairs_over_every_target_read_only_the_reviewed_ones(harness: Harness) -> None:
    """list_open_pairs walked the same 445 review.yaml reads in series; it reads as
    list_review_questions does now."""
    seed_reviews(harness)
    assert McpClient(harness).ok("list_open_pairs", {})["count"] == 0
    assert len(set(review_heads(harness))) == len(REVIEWED)
