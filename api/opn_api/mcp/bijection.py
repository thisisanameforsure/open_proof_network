"""The bijection table (F09-R4; D-28, D-35): every tool and its plain path.

A read tool maps to a graph file pattern at ``main`` (``<id>`` placeholders, a trailing slash
for a directory) or to a service route; a write tool maps to exactly one F05-F08 route. The
suite (``test_mcp_surface.py::test_bijection_table_complete``) checks that every declared tool
has a row and that every route named here exists in F05's routes table, so a tool without a
plain path cannot ship — D-28's "no MCP-only capability" made checkable.

``d28`` quotes the decision's own equivalent column, verbatim, so a reworded decision fails
the test that reads it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Kind = Literal["read", "write"]

#: A graph path pattern: path segments, ``<placeholder>`` segments, a trailing ``/`` for a
#: directory listing. Anything else in ``plain`` must be a route label (``METHOD /path``).
GRAPH_PATTERN_RE = re.compile(r"^(?:[A-Za-z0-9_.-]+|<[a-z_]+>)(?:/(?:[A-Za-z0-9_.<>-]+))*/?$")
ROUTE_LABEL_RE = re.compile(r"^(GET|POST|DELETE) /")


@dataclass(frozen=True)
class Row:
    tool: str
    kind: Kind
    plain: tuple[str, ...]  # one or two entries: graph patterns at main, or route labels
    d28: str  # the "git / HTTP equivalent" cell of D-28's table, verbatim

    @property
    def routes(self) -> tuple[str, ...]:
        return tuple(p for p in self.plain if ROUTE_LABEL_RE.match(p))

    @property
    def graph_paths(self) -> tuple[str, ...]:
        return tuple(p for p in self.plain if not ROUTE_LABEL_RE.match(p))


TABLE: tuple[Row, ...] = (
    # --- reads (D-28's read table) ------------------------------------------------------------
    Row("server_info", "read", ("GET /info.json",), "GET /info.json (repo-served static)"),
    Row("list_targets", "read", ("targets/index.json",), "targets/index.json"),
    Row(
        "get_target",
        "read",
        ("targets/<id>/graph.json", "targets/<id>/approaches/"),
        "targets/<id>/graph.json + targets/<id>/approaches/",
    ),
    Row(
        "list_frontier",
        "read",
        ("GET /frontier.json",),
        "frontier.json, regenerated on every merge",
    ),
    Row(
        "get_node",
        "read",
        ("targets/<target>/nodes/<id>/", "GET /frontier.json"),
        "raw files under nodes/<id>/",
    ),
    Row("get_defs", "read", ("targets/<id>/defs/",), "targets/<id>/defs/"),
    Row("get_gate_spec", "read", ("targets/<id>/gate-spec.json",), "gate-spec.json per graph"),
    Row("get_submission", "read", ("attestations/<id>.json",), "attestations/<id>.json"),
    Row("get_schema", "read", ("schemas/<name>.json",), "schemas/<name>.json"),
    Row("get_precheck", "read", ("GET /precheck/{job_id}",), "GET /precheck/<id>"),
    # --- writes (D-35's plain-path table) -----------------------------------------------------
    Row("claim_node", "write", ("POST /claims",), "POST /claims"),
    Row("release_claim", "write", ("DELETE /claims/{claim_id}",), "DELETE /claims/<id>"),
    Row("precheck_submission", "write", ("POST /precheck",), "POST /precheck with the bundle"),
    Row("submit_proof", "write", ("POST /submissions",), "POST /submissions opens that PR"),
    Row(
        "submit_postmortem",
        "write",
        ("POST /postmortems",),
        "a PR appending the schema-checked file under the node or target",
    ),
    Row(
        "submit_informal_annex",
        "write",
        ("POST /annexes",),
        "a PR appending the schema-checked file under the node or target",
    ),
    Row(
        "submit_approach_record",
        "write",
        ("POST /approach-records",),
        "a PR appending the schema-checked file under the node or target",
    ),
    Row(
        "file_defect_claim",
        "write",
        ("POST /defect-claims",),
        "a PR appending the schema-checked record to the target",
    ),
    Row(
        "file_revision_request",
        "write",
        ("POST /revision-requests",),
        "a PR appending the schema-checked record to the target",
    ),
    Row(
        "propose_speculative_node",
        "write",
        ("POST /proposals/speculative",),
        "a PR creating the node directory with origin set",
    ),
    Row(
        "propose_variant",
        "write",
        ("POST /proposals/variant",),
        "a PR creating the node directory with origin set",
    ),
)

BY_TOOL: dict[str, Row] = {row.tool: row for row in TABLE}


def problems(tools: set[str], route_labels: set[str]) -> list[str]:
    """Every way the table could fail R4: a declared tool without a row, a row without a tool,
    a write with anything but one route, a route not in F05's table, a malformed pattern."""
    out: list[str] = []
    out.extend(f"tool {t} has no bijection row" for t in sorted(tools - set(BY_TOOL)))
    out.extend(f"row {t} names no declared tool" for t in sorted(set(BY_TOOL) - tools))
    for row in TABLE:
        if not 1 <= len(row.plain) <= 2:
            out.append(f"{row.tool}: {len(row.plain)} plain paths, not one or two")
        if row.kind == "write" and (len(row.plain) != 1 or not row.routes):
            out.append(f"{row.tool}: a write tool maps to exactly one route")
        for route in row.routes:
            if route not in route_labels:
                out.append(f"{row.tool}: route {route!r} is not in the routes table")
        for pattern in row.graph_paths:
            if not GRAPH_PATTERN_RE.match(pattern):
                out.append(f"{row.tool}: {pattern!r} is neither a route nor a graph pattern")
    return out
