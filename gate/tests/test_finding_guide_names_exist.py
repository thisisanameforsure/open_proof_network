"""F07-T71 (audit 2026-10-04): every route, tool and error code the guide names exists in the code,
and the guide says what the service and the merge queue now do.

The guide is read by agents that act on its names, so a stale name costs a refused call (log,
2026-09-20: a route named from memory, ``GET /nodes/<id>``, did not exist). The names are taken
from the guide's backticked spans outside its fenced blocks, whose commands the walkthrough runs
(``test_walkthrough.py``), and held to the code itself:

* a span ``GET /path`` (any method) is a route of ``opn_api.routes.ROUTES``, and a bare ``/path``
  span is the path of one, with ``<id>`` and ``{name}`` read alike and a query string dropped;
* a tool named after "MCP" or in the appendix's first column is a tool of the MCP server, and
  every tool the server declares has an appendix row;
* a span ``409 code`` is a code of ``opn_gate.codes.CATALOG``, the catalog ``GET /errors.json``
  serves; any other kebab-case span is a catalog code or a string literal of the gate, the
  service or a schema (an enum value, a lint code, a ``waiting_on`` word), so a renamed value
  cannot linger in the guide.

The second half holds the audit's new behaviour to the sentences that describe it, each tied to
the constant or schema that implements it.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

from opn_api import config, pending, racers, routes, withdraw
from opn_api.mcp import server
from opn_gate import codes

ROOT = Path(__file__).resolve().parents[2]
GUIDE = (ROOT / "gate" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
PROSE = re.sub(r"^```.*?^```[ \t]*$", "", GUIDE, flags=re.DOTALL | re.MULTILINE)
SPANS = re.findall(r"`([^`\n]+)`", PROSE)
FLAT = re.sub(r"\s+", " ", GUIDE)
APPENDIX = "## Appendix: the MCP tools"

_ROUTE = re.compile(r"(GET|POST|DELETE|PUT|PATCH) (/\S*)")
_BARE_PATH = re.compile(r"/[A-Za-z0-9_./{}<>-]*")
_STATUS_CODE = re.compile(r"(\d{3}) ([a-z][a-z0-9-]*)")
_KEBAB = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)+")


def norm(path: str) -> str:
    return re.sub(r"\{[^}]*\}|<[^>]*>", "{}", path.split("?", maxsplit=1)[0])


def served() -> set[tuple[str, str]]:
    return {(r.method, norm(r.path)) for r in routes.ROUTES}


def appendix_tools() -> set[str]:
    section = GUIDE[GUIDE.index(APPENDIX) :]
    names: set[str] = set()
    for line in section.splitlines():
        if line.startswith("| `"):
            first = line.strip().strip("|").split("|")[0]
            names |= {t.split("(")[0].strip() for t in re.findall(r"`([^`]+)`", first)}
    return names


def named_tools() -> set[str]:
    return set(re.findall(r"MCP `([a-z_]+)", PROSE)) | appendix_tools()


def source_literals() -> str:
    parts = [
        p.read_text(encoding="utf-8")
        for package in (ROOT / "gate" / "opn_gate", ROOT / "api" / "opn_api")
        for p in package.rglob("*.py")
    ]
    parts += [p.read_text(encoding="utf-8") for p in (ROOT / "gate" / "schemas").rglob("*.json")]
    return "\n".join(parts)


def schema(name: str) -> dict[str, object]:
    doc: dict[str, object] = json.loads(
        (ROOT / "gate" / "schemas" / f"{name}.json").read_text(encoding="utf-8")
    )
    return doc


def section(heading: str) -> str:
    start = GUIDE.index(heading)
    end = GUIDE.find("\n## ", start + 1)
    return re.sub(r"\s+", " ", GUIDE[start : end if end >= 0 else len(GUIDE)])


# --- names held to the code -----------------------------------------------------------------------


def test_every_route_the_guide_names_is_served() -> None:
    known = served()
    paths = {p for _, p in known} | {server.MCP_PATH}
    stale: list[str] = []
    for span in SPANS:
        text = span.replace("$OPN_API", "")
        route = _ROUTE.fullmatch(text)
        if route is not None:
            if (route.group(1), norm(route.group(2))) not in known:
                stale.append(span)
        elif _BARE_PATH.fullmatch(text) and norm(text) not in paths:
            stale.append(span)
    assert not stale, f"routes the guide names that the service does not serve: {sorted(stale)}"


def test_every_tool_the_guide_names_is_a_tool() -> None:
    stale = named_tools() - set(server.BY_NAME)
    assert not stale, f"tools the guide names that the MCP server lacks: {sorted(stale)}"


def test_the_appendix_has_a_row_for_every_tool() -> None:
    missing = set(server.BY_NAME) - appendix_tools()
    assert not missing, f"MCP tools with no appendix row: {sorted(missing)}"


def test_every_status_and_code_the_guide_names_is_in_the_catalog() -> None:
    named = {m.group(2) for s in SPANS if (m := _STATUS_CODE.fullmatch(s))}
    assert named, "the guide names no refusal as `NNN code`"
    stale = named - set(codes.CATALOG)
    assert not stale, f"error codes the guide names that GET /errors.json lacks: {sorted(stale)}"


def test_every_other_kebab_name_exists_in_the_code() -> None:
    literals = source_literals()

    def exists(name: str) -> bool:
        if name in codes.CATALOG or f'"{name}"' in literals:
            return True
        # targets/index.json's reasons spell a D-33 status as f"status-{status}" (intake.py)
        return name.startswith("status-") and f'"{name.removeprefix("status-")}"' in literals

    stale = sorted({s for s in SPANS if _KEBAB.fullmatch(s) and not exists(s)})
    assert not stale, f"names the guide uses that no code or schema carries: {stale}"


# --- what the service and the queue now do --------------------------------------------------------


def test_the_queue_is_one_lane_per_target() -> None:
    """F07-T56, T69: the actor runs a lane per target and a position counts its own lane."""
    assert "across every target" not in FLAT
    assert "the open pull requests the actor takes, and `ahead`" not in FLAT
    assert "counted in the pull request's own lane" in pending.QUEUE_ORDER
    assert "`position` (1 is first) `of` the open pull requests in your own lane" in FLAT
    assert "Nothing waits for a post-merge job" in FLAT
    assert "wait for its gate commit" not in FLAT


def test_the_open_pull_request_caps_are_the_services() -> None:
    per, total = config.DEFAULT_OPEN_PRS_PER_IDENTITY, config.DEFAULT_OPEN_PRS_GLOBAL
    assert f"at most {per} pull requests open under one pseudonym" in FLAT
    assert f"{total} across the graph" in FLAT
    assert "`429 open-pull-requests-cap`" in FLAT
    assert "`503 queue-full`" in FLAT
    assert "`open_pull_requests_per_identity`" in FLAT and "`open_pull_requests_global`" in FLAT
    policy = config.Settings().rate_limit_policy()
    assert {"open_pull_requests_per_identity", "open_pull_requests_global"} <= set(policy)


def test_a_precheck_backs_one_pull_request() -> None:
    assert "`409 precheck-used`" in FLAT
    assert "precheck-used" in codes.CATALOG


def test_a_spent_check_budget_refuses_the_pre_flight() -> None:
    """F13-T28: a pre-flight whose check cannot be paid for refuses; an unavailable checker
    still lets the pull request open."""
    assert "the pre-flight is refused `429 rate-limited`" in FLAT
    assert "rate-limited" in codes.CATALOG


def test_the_error_catalog_and_the_wayfinding_routes() -> None:
    labels = {r.label for r in routes.ROUTES}
    assert {"GET /errors.json", "GET /llms.txt"} <= labels
    assert "\n## Error codes\n" in GUIDE
    errors = section("## Error codes")
    assert "`GET /errors.json`" in errors and "`list_error_codes`" in errors
    assert "`?prefix=" in errors
    assert "`GET $OPN_API/llms.txt`" in FLAT
    info = schema("info/v2")["properties"]
    assert isinstance(info, dict) and {"guide_url", "errors_url"} <= set(info)
    assert "`guide_url`" in FLAT and "`errors_url`" in FLAT


def test_the_frontier_says_status_cause_and_needs() -> None:
    """F03-T16: frontier/v4; a hole that needs a witness is listed and not claimable. F03-T18:
    frontier/v5 keeps the three and adds the circular label and the literature status."""
    entry = schema("frontier/v5")["properties"]["entries"]["items"]["properties"]  # type: ignore[index]
    assert {"status", "cause", "needs", "circular", "literature"} <= set(entry)
    assert set(entry["needs"]["oneOf"][1]["enum"]) == {"proof", "witness", "dependencies"}
    claiming = section("## Claiming a node")
    assert "The frontier publishes no status" not in claiming
    assert "and a claim on it answers `201`" not in claiming
    for word in ("`status`", "`cause`", "`needs`", "`needs: witness`", "`claimable: false`"):
        assert word in claiming, word
    assert "`details.pending`" in claiming


def test_an_agents_own_submissions_and_checks() -> None:
    labels = {r.label for r in routes.ROUTES}
    assert {"GET /submissions/mine", "GET /checks/{check_id}"} <= labels
    assert "`GET /submissions/mine`" in FLAT and "`get_my_submissions`" in FLAT
    assert "`get_check`" in FLAT and "`log_id`" in FLAT
    for key in ("open", "recent"):
        assert f'"{key}": ' in inspect.getsource(pending.mine), key
    assert pending.MAX_RECENT_MINE == 20
    assert "the twenty most recently merged or closed" in FLAT


def test_check_mode_reads_the_texts_own_sorry() -> None:
    """F13-T30: mode check answers ``okay: false`` on a text with its own sorry or admit."""
    assert "`okay` is `false` in `check` mode too when your own text carries `sorry`" in FLAT


def test_withdrawal_and_racer_moves_comment_first() -> None:
    """F07-T64: both say why on the pull request before acting."""
    for module in (withdraw, racers):
        assert "comment_on_pull_request(" in inspect.getsource(module), module.__name__
    assert "leaves a comment on the pull request" in FLAT
    assert "says so in a comment on your pull request" in FLAT
