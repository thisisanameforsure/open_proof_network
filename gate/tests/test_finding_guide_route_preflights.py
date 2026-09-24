"""F13-T21, T22: the guide and the MCP tools say what the witness and exhibit pre-flights refuse.

The route that fills a hole's witness slot pre-flights the witness before it opens a pull request
(``proposals.post_witness``, ``checks.preflight_witness``), so the guide's step "Witness it" and
the ``propose_witness`` tool description name the two refusals and the receipt's outcome words.
Defect claims and revision requests compile their exhibit first (``checks.preflight_exhibit``),
so the guide's ``defects/`` row and both MCP tools name that refusal. Each word is read from the
code that emits it, so the sentence and the constant cannot drift apart (log, 2026-09-11: docs
are tests).
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

from opn_api import checks, proposals, requests, routes
from opn_api.mcp import writes

ROOT = Path(__file__).resolve().parents[2]
GUIDE = (ROOT / "gate" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
FLAT = re.sub(r"\s+", " ", GUIDE)
WORDS = (checks.PREFLIGHT_MATCHED, checks.PREFLIGHT_INCONCLUSIVE, checks.PREFLIGHT_UNAVAILABLE)
REFUSALS = ("witness-type-mismatch", "witness-fails")


def witness_step() -> str:
    """The guide's "Witness it." step, up to the next numbered step."""
    start = FLAT.index("1. **Witness it.**")
    return FLAT[start : FLAT.index("2. **Prove it.**", start)]


def test_the_route_is_the_services() -> None:
    assert any(
        r.method == "POST" and r.path == "/proposals/witness" and r.handler.endswith("post_witness")
        for r in routes.ROUTES
    )


def test_the_refusals_are_the_pre_flights_own() -> None:
    source = inspect.getsource(checks.preflight_witness)
    for code in REFUSALS:
        assert f'"{code}"' in source, code
    assert "checks.preflight_witness" in inspect.getsource(proposals.post_witness)


def test_the_witness_step_names_both_refusals_and_the_receipt() -> None:
    step = witness_step()
    for code in REFUSALS:
        assert f"`422 {code}`" in step, code
    assert "`witness_preflight`" in step
    for word in WORDS:
        assert f"`{word}`" in step, word


def test_the_check_paragraph_says_the_witness_route_runs_it_too() -> None:
    assert "`POST /proposals/witness` runs it against the hole's statement" in FLAT


def test_a_sorry_witness_is_refused_on_every_proposal_route() -> None:
    assert '"witness-invalid"' in inspect.getsource(proposals.check_witness_filled)
    for caller in (proposals.node_files, proposals.post_witness):
        assert "check_witness_filled(" in inspect.getsource(caller), caller.__name__
    assert "`sorry` in its code `400 witness-invalid` on every proposal route" in FLAT


def test_the_hazard_pre_flight_is_said_of_the_proposal_routes_only() -> None:
    """The witness route pushes a Witness.lean alone; step 6 over a hole's derived statement
    records its findings and does not refuse (F07-Q19), so there is nothing to pre-flight."""
    assert "The same routes run the target's hazard checkers" not in FLAT
    assert "The two proposal routes run the target's hazard checkers" in FLAT


def test_the_mcp_tool_says_the_same() -> None:
    (tool,) = [t for t in writes.TOOLS if t.name == "propose_witness"]
    text = re.sub(r"\s+", " ", tool.description)
    for code in REFUSALS:
        assert f"422 {code}" in text, code
    assert "`witness_preflight`" in text
    for word in WORDS:
        assert word in text, word


# --- F13-T22: the exhibit pre-flight on defect claims and revision requests ----------------------

EXHIBIT_WORDS = (
    checks.PREFLIGHT_ELABORATES,
    checks.PREFLIGHT_INCONCLUSIVE,
    checks.PREFLIGHT_UNAVAILABLE,
    checks.PREFLIGHT_SKIPPED,
)


def test_the_exhibit_refusal_is_the_pre_flights_own() -> None:
    assert '"exhibit-elaboration"' in inspect.getsource(checks.preflight_exhibit)
    for handler in (requests.post_defect_claims, requests.post_revision_requests):
        assert "checks.preflight_exhibit" in inspect.getsource(handler), handler.__name__


def test_the_guide_row_for_defects_names_the_refusal_and_the_receipt() -> None:
    row = next(line for line in GUIDE.splitlines() if line.startswith("| `revisions/`, `defects/`"))
    assert "`422 exhibit-elaboration`" in row
    assert "`exhibit_preflight`" in row
    for word in EXHIBIT_WORDS:
        assert f"`{word}`" in row, word


def test_the_mcp_defect_tools_say_the_same() -> None:
    by_name = {t.name: re.sub(r"\s+", " ", t.description) for t in writes.TOOLS}
    for name in ("file_defect_claim", "file_revision_request"):
        assert "422 exhibit-elaboration" in by_name[name], name
        assert "`exhibit_preflight`" in by_name[name], name
    for word in EXHIBIT_WORDS:
        assert word in by_name["file_defect_claim"], word
