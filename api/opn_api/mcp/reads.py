"""The read tools (F09-R5, R6, R10; D-25, D-28, D-31).

A tool that maps to a graph file fetches it at ``main`` through the ``GitHost`` seam, cached
and revalidated by ETag exactly as ``frontier.committed`` does, and returns the parsed content
unchanged; a tool that maps to a service route calls that route in process and returns its
body. ``list_frontier`` reads the overlay (``GET /frontier.json``, D-35) and filters it by
equality or containment on named fields, in the file's order, with no ranking (D-25).
``get_node`` serves the node's committed ``CONTEXT.json`` — the bundle the post-merge job
renders with every contributor free-text value wrapped as untrusted data (F10-R3, R4) — plus
the raw files, annexes and explainers; a graph that has no bundle yet gets the same document
derived from its files through the same generator (F10-Q7). A source that does not answer is
an error result naming it, never a partial bundle (R10, C7).

Reads go to ``main`` only (Q4).
"""

from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING, Any

import yaml

from opn_api import frontier, precheck
from opn_api.app import ApiError, CachedFile
from opn_api.githost import GitHostError
from opn_api.mcp import demarcate, results
from opn_api.mcp.calls import ID_PARAM, Call, Source, Tool, error, params
from opn_gate import context, schemas

if TYPE_CHECKING:
    from opn_api.app import Context

ATTEMPT_SUFFIXES = (".yaml", ".yml")
PROSE_SUFFIX = ".md"
LEAN_SUFFIX = ".lean"
NODE_FILES: tuple[tuple[str, bool], ...] = (  # (file, required): the raw files (F10-R4)
    ("Statement.lean", True),
    ("Context.lean", True),
    ("Witness.lean", False),
    ("Proof.lean", False),
)
#: The frontier version whose entry fields the filters are drawn from. The newest known
#: one: its field set is a superset of the older versions', and a filter naming a field
#: an older document does not carry simply matches nothing (F11-R4).
FRONTIER_SCHEMA = "frontier/v2"
SCHEMA_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*/v[1-9][0-9]*$")
FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<yaml>.*?)\r?\n---[ \t]*\r?\n", re.S)


# --- reading the graph at main (R5) --------------------------------------------------------------


def committed(ctx: Context, path: str, *, optional: bool = False) -> bytes | None:
    """A file at ``main`` through the seam, reused for ``frontier_max_stale_s`` and then
    revalidated by ETag — ``frontier.committed``'s rule, with one addition: a file the graph
    does not have answers ``None`` when ``optional`` and a not-found error otherwise, instead
    of being mistaken for an outage."""
    cached = ctx.files.setdefault(path, CachedFile(path))
    now = time.monotonic()
    if cached.body is not None and now - cached.fetched_at < ctx.settings.frontier_max_stale_s:
        return cached.body
    try:
        got = ctx.githost.fetch_raw(
            ctx.settings.graph_repo, ctx.settings.graph_branch, path, etag=cached.etag
        )
    except GitHostError as exc:
        if cached.body is not None:
            return cached.body  # the last good copy, as the frontier route serves it (C7)
        raise error(
            "graph-unreachable", f"cannot read {path} from the graph: {exc}", "graph"
        ) from exc
    if got.status == 200 and got.body is not None:
        cached.body, cached.etag, cached.fetched_at = got.body, got.etag, now
        return got.body
    if got.status == 304 and cached.body is not None:
        cached.fetched_at = now
        return cached.body
    if got.status == 404:
        ctx.files.pop(path, None)
        if optional:
            return None
        raise error("not-found", f"the graph has no {path} at main", "graph")
    raise error("graph-unreachable", f"the graph answered {got.status} for {path}", "graph")


def listing(ctx: Context, path: str) -> list[str]:
    """The files under a directory at ``main``; an absent directory is an empty listing."""
    try:
        names = ctx.githost.list_dir(ctx.settings.graph_repo, ctx.settings.graph_branch, path)
    except GitHostError as exc:
        raise error(
            "graph-unreachable", f"cannot list {path} in the graph: {exc}", "graph"
        ) from exc
    return [n for n in (names or []) if n != ".gitkeep"]


def document(ctx: Context, path: str) -> dict[str, Any]:
    raw = committed(ctx, path)
    assert raw is not None
    return parse(raw, path)


# PyYAML ships no stubs (pyproject), so the base class is Any to mypy.
class _PlainLoader(yaml.SafeLoader):  # type: ignore[misc]
    """YAML with timestamps left as the strings the file holds: a record is served as JSON,
    which has no date type, and the gate validates dates as patterned strings (D-34)."""


_PlainLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def parse(raw: bytes, path: str) -> dict[str, Any]:
    """JSON or YAML, one object; the adapter never reinterprets what it cannot parse."""
    try:
        doc = (
            yaml.load(raw.decode("utf-8"), Loader=_PlainLoader)  # noqa: S506 — a SafeLoader subclass
            if not path.endswith(".json")
            else json.loads(raw)
        )
    except (UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
        raise error(
            "unparseable", f"{path} is not a record: {type(exc).__name__}", "graph"
        ) from exc
    if not isinstance(doc, dict):
        raise error("unparseable", f"{path} does not hold one record object", "graph")
    return doc


def text(raw: bytes, path: str) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise error("unparseable", f"{path} is not UTF-8", "graph") from exc


def check_id(value: Any, what: str) -> str:
    if not isinstance(value, str) or not re.match(ID_PARAM["pattern"], value):
        raise error("arguments-invalid", f"{what} must match {ID_PARAM['pattern']}", "adapter")
    return value


def service_answer(answer: Any, path: str) -> dict[str, Any]:
    """The body of a service route, or an error result naming the service (R10)."""
    if answer.refused or not isinstance(answer.body, dict):
        body = answer.body if isinstance(answer.body, dict) else {}
        raise error(
            str(body.get("error") or "service-error"),
            str(body.get("message") or f"{path} answered {answer.status}"),
            "service",
            status=answer.status,
        )
    doc: dict[str, Any] = answer.body
    return doc


def from_api_error(exc: ApiError) -> Exception:
    """An ``ApiError`` raised by an api helper the tool reused, as a tool failure."""
    source: Source = (
        "graph"
        if exc.code in ("graph-unreachable", "graph-unrendered", "node-unknown")
        else "service"
    )
    return error(exc.code, exc.message, source, status=exc.status if source == "service" else None)


# --- the tools -----------------------------------------------------------------------------------


async def server_info(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    return service_answer(await call.endpoint("GET", "/info.json"), "/info.json")


async def list_targets(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    return document(call.ctx, "targets/index.json")


async def get_target(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    target_id = check_id(args.get("target_id"), "target_id")
    graph = document(call.ctx, f"targets/{target_id}/graph.json")
    approaches = []
    for name in listing(call.ctx, f"targets/{target_id}/approaches"):
        if not name.endswith(ATTEMPT_SUFFIXES):
            continue
        path = f"targets/{target_id}/approaches/{name}"
        approaches.append(
            {"path": path, "record": demarcate.record(document(call.ctx, path), path)}
        )
    return {
        "target_id": target_id,
        "graph": graph,
        "approaches": approaches,
        "untrusted_note": demarcate.UNTRUSTED_NOTE,
    }


def _entry_fields() -> dict[str, Any]:
    props: dict[str, Any] = schemas.load_schema(FRONTIER_SCHEMA)["properties"]["entries"]["items"][
        "properties"
    ]
    return props


def _resolve(entry: dict[str, Any], field: str) -> tuple[bool, Any]:
    node: Any = entry
    for step in field.split("."):
        if not isinstance(node, dict) or step not in node:
            return False, None
        node = node[step]
    return True, node


def _known_field(field: str) -> bool:
    props = _entry_fields()
    steps = field.split(".")
    node: Any = {"properties": props}
    for step in steps:
        inner = node.get("properties", {}) if isinstance(node, dict) else {}
        if step not in inner:
            return False
        node = inner[step]
    return True


def matches(entry: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Equality on a scalar field, containment on a list field; nothing else (D-25)."""
    for field, wanted in filters.items():
        found, value = _resolve(entry, field)
        if not found:
            return False
        if isinstance(value, list):
            if wanted not in value:
                return False
        elif value != wanted:
            return False
    return True


async def list_frontier(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    filters = args.get("filters") or {}
    if not isinstance(filters, dict):
        raise error("arguments-invalid", "filters must be an object of field: value", "adapter")
    unknown = sorted(f for f in filters if not _known_field(f))
    if unknown:
        raise error(
            "filter-unknown",
            f"no such frontier field: {', '.join(unknown)}; the fields are "
            + ", ".join(sorted(_entry_fields())),
            "adapter",
        )
    doc = service_answer(await call.endpoint("GET", "/frontier.json"), "/frontier.json")
    entries = [e for e in doc.get("entries", []) if matches(e, filters)]
    return {**doc, "entries": entries}


def _prose(ctx: Context, directory: str) -> list[dict[str, Any]]:
    out = []
    for name in listing(ctx, directory):
        if not name.endswith(PROSE_SUFFIX):
            continue
        path = f"{directory}/{name}"
        raw = committed(ctx, path)
        assert raw is not None
        body = text(raw, path)
        front: dict[str, Any] = {}
        m = FRONT_MATTER_RE.match(body)
        if m is not None:
            front = demarcate.record(parse(m.group("yaml").encode(), path), path)
            body = body[m.end() :]
        out.append({"path": path, "front": front, "text": demarcate.wrap(body, path)})
    return out


class HostReader:
    """``context.Reader`` over the graph's host at ``main`` (F10-R4, Q7): the same generator the
    post-merge job runs over a checkout, so a derived bundle equals the committed one."""

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def read(self, path: str) -> bytes | None:
        return committed(self.ctx, path, optional=True)

    def listdir(self, path: str) -> list[str]:
        return listing(self.ctx, path)


def node_context(ctx: Context, target_id: str, node_id: str) -> tuple[dict[str, Any], str]:
    """The node's ``CONTEXT.json`` as committed, or the same document derived from the files at
    ``main`` when the graph carries none yet (a graph rendered before F10's pin). The second
    value says which (``file`` or ``derived``)."""
    path = context.context_path(target_id, node_id)
    raw = committed(ctx, path, optional=True)
    if raw is not None:
        try:
            return schemas.validate(parse(raw, path), context.SCHEMA), "file"
        except schemas.SchemaError as exc:
            raise error("context-invalid", f"{path} does not validate: {exc}", "graph") from exc
    states = context.graph_states({"nodes": precheck.graph_doc(ctx).get(target_id, [])})
    rendered = frontier.committed_frontier(ctx).get("rendered_from")
    try:
        doc = context.build(
            HostReader(ctx),
            target_id,
            node_id,
            states=states,
            rendered_from=str(rendered) if isinstance(rendered, str) else None,
        )
    except context.ContextError as exc:
        raise error("context-underivable", f"{node_id}: {exc}", "graph") from exc
    return doc, "derived"


async def get_node(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    node_id = check_id(args.get("node_id"), "node_id")
    try:
        facts = precheck.node_facts(call.ctx, node_id)
        bundle, source = node_context(call.ctx, str(facts["target_id"]), node_id)
    except ApiError as exc:
        raise from_api_error(exc) from exc
    target_id = str(facts["target_id"])
    node_dir = f"targets/{target_id}/nodes/{node_id}"
    files: dict[str, str | None] = {}
    for name, required in NODE_FILES:
        raw = committed(call.ctx, f"{node_dir}/{name}", optional=not required)
        files[name] = text(raw, name) if raw is not None else None
    overlay = service_answer(await call.endpoint("GET", "/frontier.json"), "/frontier.json")
    entry = next((e for e in overlay.get("entries", []) if e.get("node_id") == node_id), None)
    return {
        "node_id": node_id,
        "target_id": target_id,
        "context": bundle,
        "context_source": source,
        "files": files,
        "claims": dict(entry["claims"]) if entry is not None else None,
        "annexes": _prose(call.ctx, f"{node_dir}/annex"),
        "explainers": _prose(call.ctx, f"{node_dir}/explainer"),
        "untrusted_note": demarcate.UNTRUSTED_NOTE,
    }


async def get_defs(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    target_id = check_id(args.get("target_id"), "target_id")
    committed(call.ctx, f"targets/{target_id}/graph.json")  # the target exists, or not-found
    directory = f"targets/{target_id}/defs"
    defs, certificates = [], []
    for name in listing(call.ctx, directory):
        path = f"{directory}/{name}"
        raw = committed(call.ctx, path)
        assert raw is not None
        if name.endswith(LEAN_SUFFIX):
            defs.append(
                {"path": path, "sha256": schemas.content_hash(raw), "content": text(raw, path)}
            )
        elif name.endswith((*ATTEMPT_SUFFIXES, ".json")):
            certificates.append({"path": path, "record": parse(raw, path)})
    return {"target_id": target_id, "defs": defs, "certificates": certificates}


async def get_gate_spec(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    target_id = check_id(args.get("target_id"), "target_id")
    return document(call.ctx, f"targets/{target_id}/gate-spec.json")


async def get_submission(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    submission_id = args.get("submission_id")
    if not isinstance(submission_id, str) or not re.match(r"^[A-Za-z0-9-]+$", submission_id):
        raise error("arguments-invalid", "submission_id names an attestation file", "adapter")
    return document(call.ctx, f"attestations/{submission_id}.json")


async def get_schema(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    name = args.get("name")
    if not isinstance(name, str):
        raise error("arguments-invalid", "name is required", "adapter")
    tool = results.tool_of(name)
    if tool is not None:
        try:
            return results.load(tool)
        except KeyError as exc:
            raise error("not-found", f"no adapter schema {name}", "adapter") from exc
    if not SCHEMA_NAME_RE.match(name):
        raise error(
            "arguments-invalid",
            "name is <schema>/v<n> (as a record's schema field spells it) or mcp/<tool>/v1",
            "adapter",
        )
    return document(call.ctx, f"schemas/{name}.json")


async def get_precheck(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    job_id = args.get("job_id")
    if not isinstance(job_id, str) or not re.match(r"^[0-9A-Z]{26}$", job_id):
        raise error("arguments-invalid", "job_id is the id precheck_submission returned", "adapter")
    return service_answer(await call.endpoint("GET", f"/precheck/{job_id}"), "/precheck/<id>")


TOOLS: tuple[Tool, ...] = (
    Tool(
        "server_info",
        "Protocol version, gate-spec hashes, schema index and the rate-limit policy in force.",
        params({}),
        server_info,
    ),
    Tool(
        "list_targets",
        "Every graph: id, root statement hash, fidelity, status and pinned Mathlib SHA.",
        params({}),
        list_targets,
    ),
    Tool(
        "get_target",
        "A target's graph structure and node statuses, with its approach records.",
        params({"target_id": ID_PARAM}, ("target_id",)),
        get_target,
    ),
    Tool(
        "list_frontier",
        "The open nodes with D-25's observed facts and live claim status. `filters` is an "
        "object of frontier field to value (dotted for nested, e.g. `tags.library`): equality "
        "on a scalar field, containment on a list field; results keep the file's order and "
        "carry no ranking.",
        params({"filters": {"type": "object"}}),
        list_frontier,
    ),
    Tool(
        "get_node",
        "A node's context bundle (nodes/<id>/CONTEXT.json: statement, deps' signatures, witness, "
        "status, gate-spec reference, attempt log, annex hashes) plus the raw Lean files, live "
        "claim status, annexes and explainers.",
        params({"node_id": ID_PARAM}, ("node_id",)),
        get_node,
    ),
    Tool(
        "get_defs",
        "A target's shared-definition tier with content hashes.",
        params({"target_id": ID_PARAM}, ("target_id",)),
        get_defs,
    ),
    Tool(
        "get_gate_spec",
        "A target's pinned toolchain, Mathlib SHA, axiom allowlist, hazard checkers, network "
        "commit and precheck-attestation policy.",
        params({"target_id": ID_PARAM}, ("target_id",)),
        get_gate_spec,
    ),
    Tool(
        "get_submission",
        "A gate run's signed attestation: the record a merged submission earned.",
        params({"submission_id": {"type": "string"}}, ("submission_id",)),
        get_submission,
    ),
    Tool(
        "get_schema",
        "A JSON Schema by name: a protocol record's (`postmortem/v1`, `defect-claim/v1`, ...) "
        "or a tool result's (`mcp/<tool>/v1`).",
        params({"name": {"type": "string"}}, ("name",)),
        get_schema,
    ),
    Tool(
        "get_precheck",
        "A precheck job's state, diagnostics and signed attestation; poll after "
        "precheck_submission until the state is done or error.",
        params({"job_id": {"type": "string"}}, ("job_id",)),
        get_precheck,
    ),
)
