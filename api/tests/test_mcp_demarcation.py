"""F09-T2 / AC6: contributor free text is served only as demarcated untrusted data (R6)."""

from __future__ import annotations

import json
from typing import Any

from api_fakes import Harness
from mcp_client import INJECTION, NODE, NODE_DIR, TARGET, McpClient, seed_node, unwrap

from opn_api.mcp import demarcate
from opn_gate.context import RECORD_LIMIT as ATTEMPT_LOG_LIMIT


def bare_hits(value: Any, needle: str, path: str = "$") -> list[str]:
    """Paths of bare (unwrapped) strings containing ``needle``."""
    if demarcate.is_wrapped(value):
        return []
    if isinstance(value, str):
        return [path] if needle in value else []
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in bare_hits(v, needle, f"{path}.{k}")]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in bare_hits(v, needle, f"{path}[{i}]")]
    return []


def wrapped_hits(value: Any, needle: str) -> list[dict[str, Any]]:
    if demarcate.is_wrapped(value):
        return [value] if needle in value["text"] else []
    if isinstance(value, dict):
        return [w for v in value.values() for w in wrapped_hits(v, needle)]
    if isinstance(value, list):
        return [w for v in value for w in wrapped_hits(v, needle)]
    return []


def test_free_text_wrapped(harness: Harness) -> None:
    """AC6: a postmortem detail of "ignore previous instructions" appears only inside an
    untrusted object, with the top-level note present — and so does every other prose field:
    the annex body, the explainer, the hazard justification."""
    seed_node(harness)
    bundle = McpClient(harness).ok("get_node", {"node_id": NODE})
    assert bundle["untrusted_note"] == demarcate.UNTRUSTED_NOTE
    assert bare_hits(bundle, INJECTION) == []
    found = wrapped_hits(bundle, INJECTION)
    sources = {w["source"] for w in found}
    assert any(s.startswith(NODE_DIR + "attempts/") for s in sources)
    assert any(s.startswith(NODE_DIR + "annex/") for s in sources)
    assert NODE_DIR + "explainer/overview.md" in sources
    assert NODE_DIR + "META.yaml" in sources
    for w in found:
        assert w["untrusted"] is True
        assert INJECTION in w["text"]
    # Wrapped verbatim: unwrapping gives the records back exactly as the files hold them.
    attempt = bundle["context"]["attempts"]["records"][0]
    assert unwrap(attempt["record"])["detail"] == f"attempt 0: {INJECTION}"
    assert attempt["record"]["route"] == {
        "untrusted": True,
        "source": attempt["path"],
        "text": "route 0",
    }
    assert attempt["record"]["route_class"] == "induction"  # an enum stays a bare fact
    # The whole served bundle, as text, holds the injection only inside untrusted objects.
    text = json.dumps(bundle)
    assert text.count(INJECTION) == len(found)


def test_target_approaches_wrapped(harness: Harness) -> None:
    """R6 on get_target: an approach record's route and blocked_on are prose."""
    path = f"targets/{TARGET}/approaches/20260910T120000Z-alice.yaml"
    harness.githost.files[path] = (
        "schema: approach-record/v1\ntarget: propositional\ncontributor: alice\n"
        f"route: {INJECTION}\noutcome: blocked\nblocked_on: {INJECTION} too\n"
        "pinned_mathlib_sha: null\nmodel_and_tooling: null\ndate: '2026-09-10T12:00:00Z'\n"
    ).encode()
    harness.context.files.clear()
    doc = McpClient(harness).ok("get_target", {"target_id": TARGET})
    assert bare_hits(doc, INJECTION) == []
    [entry] = doc["approaches"]
    assert entry["record"]["route"] == demarcate.wrap(INJECTION, path)
    assert entry["record"]["blocked_on"]["untrusted"] is True
    assert entry["record"]["outcome"] == "blocked"
    assert doc["untrusted_note"] == demarcate.UNTRUSTED_NOTE


def test_attempt_log_truncated(harness: Harness) -> None:
    """§6: the newest 50 attempt records, oldest first, with the marker set."""
    seed_node(harness, attempts=ATTEMPT_LOG_LIMIT + 3)
    attempts = McpClient(harness).ok("get_node", {"node_id": NODE})["context"]["attempts"]
    assert attempts["truncated"] is True and attempts["count"] == ATTEMPT_LOG_LIMIT + 3
    assert len(attempts["records"]) == ATTEMPT_LOG_LIMIT
    paths = [a["path"] for a in attempts["records"]]
    assert paths == sorted(paths)
    assert unwrap(attempts["records"][0]["record"])["route"] == "route 3"  # the oldest dropped
    assert unwrap(attempts["records"][-1]["record"])["route"] == f"route {ATTEMPT_LOG_LIMIT + 2}"
    seed_node(harness, attempts=ATTEMPT_LOG_LIMIT)
    bundle = McpClient(harness).ok("get_node", {"node_id": NODE})
    assert bundle["context"]["attempts"]["truncated"] is False


def test_record_wrapping_by_family() -> None:
    """Every family in FREE_TEXT wraps its named paths and nothing else; an unknown family and a
    missing field are left alone."""
    src = "targets/t/nodes/n/attempts/x.yaml"
    pm = demarcate.record({"schema": "postmortem/v1", "route": "r", "outcome": "exhausted"}, src)
    assert pm == {
        "schema": "postmortem/v1",
        "route": demarcate.wrap("r", src),
        "outcome": "exhausted",
    }
    meta = demarcate.record(
        {"schema": "meta/v3", "acknowledged_hazards": [{"justification": "j"}, {"other": 1}]}, src
    )
    assert meta["acknowledged_hazards"] == [
        {"justification": demarcate.wrap("j", src)},
        {"other": 1},
    ]
    rev = demarcate.record({"schema": "revision-request/v1", "evidence": {"text": "t"}}, src)
    assert rev["evidence"] == {"text": demarcate.wrap("t", src)}
    waiver = demarcate.record({"schema": "waiver/v1", "justification": 7}, src)
    assert waiver["justification"] == 7  # not a string: not prose
    other = demarcate.record({"schema": "graph/v2", "route": "r"}, src)
    assert other == {"schema": "graph/v2", "route": "r"}
    assert demarcate.bare_strings({"a": [demarcate.wrap("x", src), "y"]}) == ["$.a[1]"]
    assert set(demarcate.FREE_TEXT) >= {
        "postmortem",
        "approach-record",
        "annex",
        "meta",
        "waiver",
        "revision-request",
    }
