"""mcpfix WA1 (testers 2026-11-25, qa-ea B1/B2, qa-eb L5/L9/L11, t883 2/11, t257 7, t257b 1):
search's brief entries carry the arguments and a real plain path, the ranking puts the operation
a tester asked for first, and an unknown name suggests the close ones."""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import Harness
from mcp_client import LEGACY_PATH, McpClient

from opn_api.mcp import bijection, surface
from opn_api.mcp.server import TITLES, TOOLS


def ranked(query: str, limit: int = 8) -> list[str]:
    doc = surface.search(TOOLS, TITLES, {"query": query, "limit": limit})
    return [o["name"] for o in doc["operations"]]


# --- item 1: brief entries --------------------------------------------------------------------


def test_brief_listing_carries_args_count_and_real_paths() -> None:
    doc = surface.search(TOOLS, TITLES, {})
    assert doc["count"] == len(TOOLS) == len(doc["operations"])
    by_name = {t.name: t for t in TOOLS}
    for op in doc["operations"]:
        tool = by_name[op["name"]]
        schema = tool.input_schema
        props = list(schema.get("properties", {}))
        required = list(schema.get("required", []))
        assert op["args"] == {
            "required": required,
            "optional": [p for p in props if p not in required],
        }, op["name"]
        assert op["plain"] == list(bijection.BY_TOOL[op["name"]].plain), op["name"]


def test_brief_plain_is_never_prose() -> None:
    """Every brief ``plain`` entry is a route label or a graph pattern, never a sentence."""
    doc = surface.search(TOOLS, TITLES, {})
    for op in doc["operations"]:
        for p in op["plain"]:
            assert bijection.ROUTE_LABEL_RE.match(p) or bijection.GRAPH_PATTERN_RE.match(p), (
                op["name"],
                p,
            )


def test_get_submission_names_the_attestation_file_by_pr_number() -> None:
    plain = bijection.BY_TOOL["get_submission"].plain
    assert "attestations/<pr_number>.json" in plain
    assert bijection.GRAPH_PATTERN_RE.match("attestations/<pr_number>.json")


# --- item 2: ranking (golden) -----------------------------------------------------------------

#: query -> (acceptable operations, within the top n)
GOLDEN: tuple[tuple[str, frozenset[str], int], ...] = (
    (
        "check the status of my pull request",
        frozenset({"get_submission", "get_my_submissions"}),
        3,
    ),
    ("what Lean files need a gloss", frozenset({"list_words_needed"}), 1),
    ("find an open problem to work on", frozenset({"list_frontier"}), 1),
    ("what is the pinned Mathlib version", frozenset({"get_gate_spec"}), 1),
    ("who else is working on this node", frozenset({"get_node"}), 2),
    ("which nodes would prove the root", frozenset({"list_sufficient_sets"}), 1),
    (
        "submit a decomposition into lemmas / holes",
        frozenset({"precheck_submission", "submit_proof"}),
        2,
    ),
    (
        "submit a skeleton proof with holes",
        frozenset({"precheck_submission", "submit_proof"}),
        2,
    ),
    ("dry run", frozenset({"submit_gloss"}), 1),
    # Kept first (they ranked right before the change).
    ("what does this error code mean", frozenset({"list_error_codes"}), 1),
    ("follow my submission", frozenset({"get_submission"}), 1),
    ("read a node's statement", frozenset({"get_node"}), 1),
    ("list the targets", frozenset({"list_targets"}), 1),
    ("show my claims", frozenset({"list_my_claims"}), 1),
    ("poll a precheck job", frozenset({"get_precheck"}), 1),
    ("shared definitions for a target", frozenset({"get_defs"}), 1),
    ("get the DCO text", frozenset({"get_dco"}), 1),
    ("merge queue position", frozenset({"list_submissions", "get_submission"}), 1),
    ("claim a node", frozenset({"claim_node"}), 1),
    ("submit a proof", frozenset({"submit_proof"}), 1),
)


@pytest.mark.parametrize(("query", "wanted", "within"), GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden_ranking(query: str, wanted: frozenset[str], within: int) -> None:
    top = ranked(query)
    assert wanted & set(top[:within]), top[:5]


def test_who_else_is_working_ranks_no_write_first() -> None:
    top = ranked("who else is working on this node")
    first = {t.name: t for t in TOOLS}[top[0]]
    assert not first.write, top[:5]


def test_stemmer_strips_a_plural_s_only() -> None:
    assert surface.words("status gloss claims nodes") == {"status", "gloss", "claim", "node"}


def test_keywords_and_parameters_count_toward_the_score() -> None:
    [tool] = [t for t in TOOLS if t.name == "submit_gloss"]
    assert surface.score(tool, TITLES["submit_gloss"], "dry_run") > 0
    assert hasattr(tool, "keywords")


# --- item 3: did you mean ----------------------------------------------------------------------


def test_unknown_operation_suggests_close_names(harness: Harness) -> None:
    client = McpClient(harness, raw=True)
    doc = client.failed("read", {"operation": "get_nodes", "arguments": {}})
    assert doc["error"] == "operation-unknown"
    assert "did you mean get_node?" in doc["message"]
    doc = client.failed("search", {"operations": ["get_nodes"]})
    assert "did you mean get_node?" in doc["message"]


def test_unknown_operation_without_a_close_name_still_names_search() -> None:
    message = surface.unknown_operation("zzzzqqq").doc["message"]
    assert "did you mean" not in message
    assert "search" in message


def test_legacy_tool_unknown_suggests_and_points_to_the_list(harness: Harness) -> None:
    legacy = McpClient(harness, path=LEGACY_PATH, raw=True)
    doc: dict[str, Any] = legacy.failed("get_nodes", {})
    assert doc["error"] == "tool-unknown"
    assert "did you mean get_node?" in doc["message"]
    assert "tools/list" in doc["message"]
    assert str(len(TOOLS)) in doc["message"]
