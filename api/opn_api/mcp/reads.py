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
from urllib.parse import urlencode

import yaml

from opn_api import duplicates, frontier, pending, precheck, requests
from opn_api import glosses as glossroutes
from opn_api.app import ApiError, CachedDir, CachedFile
from opn_api.githost import GitHostError
from opn_api.mcp import demarcate, results
from opn_api.mcp.calls import ID_PARAM, Call, Source, Tool, ToolError, error, params
from opn_gate import context, explainers, glosses, layout, products, schemas

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
FRONTIER_SCHEMA = "frontier/v4"  # F03-T16: `needs`, `status`, `cause` are filterable
SCHEMA_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*/v[1-9][0-9]*$")
FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<yaml>.*?)\r?\n---[ \t]*\r?\n", re.S)


# --- reading the graph at main (R5) --------------------------------------------------------------


def committed(ctx: Context, path: str, *, optional: bool = False) -> bytes | None:
    """A file at ``main`` through the seam, reused for ``frontier_max_stale_s`` and then
    revalidated by ETag — ``frontier.committed``'s rule, with one addition: a file the graph
    does not have answers ``None`` when ``optional`` and a not-found error otherwise, instead
    of being mistaken for an outage. It follows the same freshness generation first, so a
    moved ``info.json`` makes this copy revalidate too (F05-T10)."""
    frontier.generation(ctx)
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
    """The files under a directory at ``main``; an absent directory is an empty listing.

    F07-T68: a listing is a Contents-API call as the App, so it is read once per head of
    ``main`` (``frontier.pin_head``; once per ``frontier_max_stale_s`` when the head is not
    known) and kept. While the App's budget is held at the reserve it is not read at all: the
    last listing of the path is served, and with none the call is a ``host-budget-exhausted``
    error naming the reset, as the other held reads say it."""
    frontier.pin_head(ctx)
    ref = ctx.head or ctx.settings.graph_branch
    cached = ctx.listings.get(path)
    now = time.monotonic()
    if (
        cached is not None
        and cached.ref == ref
        and (ctx.head is not None or now - cached.fetched_at < ctx.settings.frontier_max_stale_s)
    ):
        return _names(cached.names)
    hold = pending.budget_hold(ctx)
    if hold is not None:
        if cached is not None:
            return _names(cached.names)
        raise error("host-budget-exhausted", hold, "graph")
    try:
        names = ctx.githost.list_dir(ctx.settings.graph_repo, ctx.settings.graph_branch, path)
    except GitHostError as exc:
        raise error(
            "graph-unreachable", f"cannot list {path} in the graph: {exc}", "graph"
        ) from exc
    if len(ctx.listings) >= pending.MAX_REMEMBERED:
        ctx.listings.clear()
    ctx.listings[path] = CachedDir(ref, names, now)
    return _names(names)


def _names(names: list[str] | None) -> list[str]:
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
        # F08-T22: a committed bundle is validated against the version it names, within the
        # versions the bundle's module accepts — a graph rendered before the re-pin that first
        # writes ``context/v2`` still carries v1, and the service deploys before that re-pin.
        doc = parse(raw, path)
        declared = str(doc.get("schema"))
        if declared not in context.ACCEPTED:
            raise error(
                "context-invalid",
                f"{path} declares {declared!r}; expected one of {', '.join(context.ACCEPTED)}",
                "graph",
            )
        try:
            return schemas.validate(doc, declared), "file"
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


def closing_route(node_id: str, statement: str | None) -> dict[str, Any]:
    """How this node is closed through its holes and dependencies (F00-T10). Their theorems
    reach a proof through the node's own ``Context``; a statement written since 2026-09-20
    imports it, and a proof of an older one adds the line itself, which is the one import step 2
    allows. Two agents learned that a root could not be assembled from its holes at minute 37,
    by experiment; now it can, and the node says how. One function decides
    (``layout.imports_own_context``), so the site's line and this one cannot disagree."""
    in_statement = statement is not None and layout.imports_own_context(node_id, statement)
    return {
        "through_holes": True,
        "context_import": "statement" if in_statement else "proof",
        "import_line": f"import {layout.node_module(node_id, 'Context')}",
    }


#: The ``glosses.json`` versions get_node reads (F21-R6): v1 until a graph's re-pin renders v2,
#: which adds sections, shown and pending words and ``drafted_with``; the gate writes v2.
GLOSSES_SCHEMAS: frozenset[str] = frozenset({"glosses/v1", products.GLOSSES_SCHEMA})


def node_chains(ctx: Context, target_id: str, node_id: str) -> tuple[list[dict[str, Any]], str]:
    """F20-R11: the node's ``glosses/v1`` or ``glosses/v2`` subjects — each Lean file with the
    gloss chains filed on it, each merged proof artifact with its explainer chains — from the
    committed ``targets/<id>/glosses.json``, or derived from the node's files at ``main`` by the
    gate's own function while the graph carries none (F10-Q7; ``derived``). Every version gains
    its prose, as demarcated untrusted data (D-28)."""
    path = f"targets/{target_id}/{products.GLOSSES_FILE}"
    raw = committed(ctx, path, optional=True)
    if raw is not None:
        doc = parse(raw, path)
        try:
            # F21-R6: the committed product is validated against the version it declares, v1 or
            # v2 — the live graph holds glosses/v1 until the re-pin renders v2 (D-34).
            declared = doc.get("schema")
            if declared not in GLOSSES_SCHEMAS:
                msg = f"declares {declared!r}, not one of {', '.join(sorted(GLOSSES_SCHEMAS))}"
                raise schemas.SchemaError(msg)
            schemas.validate(doc, str(declared))
        except schemas.SchemaError as exc:
            raise error("glosses-invalid", f"{path} does not validate: {exc}", "graph") from exc
        subjects = [s for s in doc["subjects"] if s.get("node") == node_id]
        source = "file"
    else:
        try:
            subjects = glossroutes.node_glosses(
                ctx, target_id, node_id, lambda directory: listing(ctx, directory)
            )
        except ApiError as exc:
            raise from_api_error(exc) from exc
        source = "derived"
    for subject in subjects:
        for chain in subject["chains"]:
            for version in chain["versions"]:
                where = f"targets/{target_id}/{version['path']}"
                found = committed(ctx, where, optional=True)
                body = None
                if found is not None:
                    _front, body = glosses.split_front_matter(text(found, where))
                version["text"] = demarcate.wrap(body, where) if body is not None else None
                if isinstance(version.get("drafted_with"), str):
                    # F21-R7, C9: the contributor's own words on the model they used
                    version["drafted_with"] = demarcate.wrap(
                        version["drafted_with"], f"{where}#drafted_with"
                    )
    return subjects, source


def node_outlines(
    ctx: Context, target_id: str, subjects: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """F20-R11: F19's committed outline of each of the node's merged proof artifacts, or
    ``None`` beside an artifact not yet outlined — the step ids an explainer's sections name."""
    out = []
    for subject in subjects:
        if subject["record"] != "explainer" or subject["kind"] == "absent":
            continue
        digest = subject["lean_hash"]
        path = f"targets/{target_id}/{explainers.OUTLINES_DIR}/{digest}.json"
        raw = committed(ctx, path, optional=True)
        out.append(
            {
                "proof": digest,
                "file": subject["file"],
                "path": path,
                "outline": parse(raw, path) if raw is not None else None,
            }
        )
    return out


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
    pending = service_answer(await call.endpoint("GET", "/submissions.json"), "/submissions.json")
    claims = dict(entry["claims"]) if entry is not None else None
    if claims is not None:
        # Owner, 2026-09-14: get_node returns the latest node, so the bundle's committed claims
        # snapshot is replaced by the live overlay and the two blocks can never disagree.
        bundle = {**bundle, "claims": dict(claims)}
    subjects, chains_source = node_chains(call.ctx, target_id, node_id)
    return {
        "node_id": node_id,
        "target_id": target_id,
        "context": bundle,
        "context_source": source,
        "closing": closing_route(node_id, files.get("Statement.lean")),
        "files": files,
        "claims": dict(entry["claims"]) if entry is not None else None,
        "annexes": _prose(call.ctx, f"{node_dir}/annex"),
        "explainers": _prose(call.ctx, f"{node_dir}/explainer"),
        # F20-R11: the outlines an explainer's sections name steps of, and every chain of words
        # on the node's Lean files and merged proofs, from the product or derived (F10-Q7).
        "outlines": node_outlines(call.ctx, target_id, subjects),
        "gloss_chains": [s for s in subjects if s["record"] == "gloss"],
        "explainer_chains": [s for s in subjects if s["record"] == "explainer"],
        "chains_source": chains_source,
        # F09-T7: the pull requests already open on this node, as GET /submissions.json lists them.
        "submissions": {
            "open": [s for s in pending.get("open", []) if s.get("node_id") == node_id]
        },
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
    """``GET /submissions/{id}``, body for body (F09-T7): the record, the pull request's live
    state and the attestation once there is one."""
    submission_id = args.get("submission_id")
    if not isinstance(submission_id, str) or not re.match(r"^[A-Za-z0-9-]+$", submission_id):
        raise error(
            "arguments-invalid",
            "submission_id is the ULID a submission returned or its pull-request number",
            "adapter",
        )
    return service_answer(
        await call.endpoint("GET", f"/submissions/{submission_id}"), "/submissions/<id>"
    )


async def list_submissions(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """``GET /submissions.json`` body for body (F09-T7; D-28's notation note of 2026-09-14)."""
    return service_answer(await call.endpoint("GET", "/submissions.json"), "/submissions.json")


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


async def get_dco(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """``GET /dco.json``: the DCO text and the version ``get_token`` must name (D-23, R4).

    The one value the bootstrap needs that no other read publishes — ``info.json`` is the graph's
    product and carries no dco key, and ``get_schema`` serves schemas, not documents. Without
    this tool an MCP-only client cannot mint a token and is read-only for ever, which is the
    bijection rule failing in the direction nothing checked (found live 2026-09-16; D-28 notation
    note of the same day).
    """
    return service_answer(await call.endpoint("GET", "/dco.json"), "/dco.json")


async def list_routes(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """``GET /``: the service's own route index (F05-T12), so an MCP-only agent can see the plain
    path behind each tool (D-28 notation note 2026-09-20)."""
    return service_answer(await call.endpoint("GET", "/"), "/")


async def get_hosted_checkers(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """``GET /hosted-checkers.json``: which targets ``check_lean`` can serve, and how exactly
    (F13-R11; D-28 notation note 2026-09-20)."""
    path = "/hosted-checkers.json"
    return service_answer(await call.endpoint("GET", path), path)


async def list_my_claims(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """``GET /claims/mine``, body for body (F05-T14, ruling D3(b)): the caller's own active
    claims with their ids. The one read that needs a bearer, because what it reads is the
    caller's; the server refuses it without one before the route is reached."""
    return service_answer(await call.endpoint("GET", "/claims/mine"), "/claims/mine")


async def get_my_submissions(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """``GET /submissions/mine``, body for body (F07-T70, F09-T17): the caller's own open
    submissions with their place in the queue, and the most recently finished. A read that needs
    a bearer, as ``list_my_claims``: what it reads is the caller's own."""
    return service_answer(await call.endpoint("GET", "/submissions/mine"), "/submissions/mine")


async def get_check(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """``GET /checks/{id}``, body for body (F09-T17): the caller's own record of one fast check
    (F13-R10). The route answers ``404 check-unknown`` for anyone else's, which passes through."""
    check_id = args.get("check_id")
    if not isinstance(check_id, str) or not re.match(r"^[0-9A-Z]{26}$", check_id):
        raise error("arguments-invalid", "check_id is the log_id check_lean returned", "adapter")
    return service_answer(await call.endpoint("GET", f"/checks/{check_id}"), "/checks/<id>")


# --- F09-T15 (audit 2026-10-04, owner-approved): the error-code catalog -------------------------

#: A code prefix as the catalog spells codes: lower case, digits, ``-`` and ``_`` (F13-T29).
PREFIX_PARAM: dict[str, Any] = {"type": "string", "pattern": "^[a-z0-9_-]{0,64}$"}


async def list_error_codes(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """``GET /errors.json``, body for body (F13-T29): every error code with what it means and
    what to do; ``prefix`` is passed through as the route's own query parameter."""
    path = "/errors.json"
    prefix = args.get("prefix")
    query = f"?{urlencode({'prefix': prefix})}" if prefix else ""
    return service_answer(await call.endpoint("GET", path + query), path)


# --- F21-T7 (R8; D-28 notation note of 2026-10-05): the files that lack words --------------------

#: The kinds a subject lacking words can be: ``glosses/v2``'s subject kinds, ``absent`` aside
#: (an explainer of an artifact the tree does not hold has no file to write words for).
WORD_KINDS: tuple[str, ...] = (
    "statement",
    "witness",
    "relation",
    "definition",
    "proof",
    "alternate",
    "partial",
)


#: The products ``glosses.needed`` reads: the live graph holds v1 until its re-pin (F21-R6).
GLOSSES_VERSIONS = frozenset({"glosses/v1", "glosses/v2"})


class _UnreadError(Exception):
    """One target's file that could not be read, listed under ``unread`` (never an empty
    answer: a target without its product has not been shown to need nothing)."""

    def __init__(self, path: str, code: str, message: str) -> None:
        super().__init__(message)
        self.path, self.code, self.message = path, code, message


def _at_head(ctx: Context, path: str) -> dict[str, Any]:
    """A committed record at main's head (``frontier.committed``, F05-T13). ``reads.committed``
    reads the branch path instead, which the host's CDN caches for minutes; this tool does not
    inherit that gap."""
    try:
        return parse(frontier.committed(ctx, path), path)
    except ApiError as exc:
        raise _UnreadError(path, exc.code, exc.message) from exc
    except ToolError as exc:  # unparseable
        raise _UnreadError(path, str(exc.doc["error"]), str(exc.doc["message"])) from exc


def _target_words(ctx: Context, entry: dict[str, Any]) -> list[dict[str, Any]]:
    """One target's subjects lacking words, from its committed ``glosses.json`` and
    ``target.yaml`` by the gate's own rule."""
    target_id = str(entry["target_id"])
    path = f"targets/{target_id}/{products.GLOSSES_FILE}"
    doc = _at_head(ctx, path)
    if doc.get("schema") not in GLOSSES_VERSIONS or doc.get("target") != target_id:
        raise _UnreadError(
            path,
            "glosses-invalid",
            f"{path} is {doc.get('schema')!r} for {doc.get('target')!r}; this service reads "
            + ", ".join(sorted(GLOSSES_VERSIONS)),
        )
    try:
        schemas.validate(doc, str(doc["schema"]))
    except schemas.SchemaError as exc:
        raise _UnreadError(path, "glosses-invalid", f"{path} does not validate: {exc}") from exc
    curated = None
    # targets-index: ``track`` is null exactly for a target with no target.yaml (F11). An
    # older index without the field says nothing, so the record is read.
    if "track" not in entry or entry["track"] is not None:
        curated = glosses.curated_words(_at_head(ctx, f"targets/{target_id}/target.yaml"))
    root = entry.get("root")
    return glosses.needed(doc, root=str(root) if root else None, curated=curated)


def _node_statuses(ctx: Context, target_id: str) -> dict[str, str]:
    """F22-T7: each node's status in the target's committed ``graph.json`` at main's head; none
    when it cannot be read (the rows still answer, with ``node_status`` null)."""
    try:
        doc = _at_head(ctx, f"targets/{target_id}/graph.json")
    except _UnreadError:
        return {}
    return {
        str(n["node_id"]): str(n["status"])
        for n in doc.get("nodes") or []
        if isinstance(n, dict) and "node_id" in n and "status" in n
    }


def _subject_key(row: dict[str, Any]) -> str:
    """The row's subject as the one-writer rule keys it (``duplicates.words_key``): a merged
    artifact by its hash (the outline's name), a Lean file by its path under the target."""
    target = str(row["target"])
    if row.get("outline"):
        return duplicates.words_key(target, str(row["outline"]).rsplit("/", 1)[-1][: -len(".json")])
    return duplicates.words_key(target, str(row["file"]).removeprefix(f"targets/{target}/"))


def _review_and_status(ctx: Context, subjects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """F22-T7 (testers 2026-10-06, request D, P3-13): each row's ``in_review`` — the open words
    pull request, still able to merge, writing its subject (``{pr_number, author}``), or null —
    and ``node_status`` from the target's ``graph.json`` (null for a definition module); rows of
    superseded nodes last, the record's order otherwise kept (nothing is ranked, D-25)."""
    writing = duplicates.in_review(ctx, {_subject_key(r) for r in subjects}) if subjects else {}
    statuses: dict[str, dict[str, str]] = {}
    for row in subjects:
        target = str(row["target"])
        if target not in statuses:
            statuses[target] = _node_statuses(ctx, target)
        found = writing.get(_subject_key(row))
        row["in_review"] = (
            {"pr_number": found.pr_number, "author": found.pseudonym} if found is not None else None
        )
        node = row.get("node")
        row["node_status"] = statuses[target].get(str(node)) if node is not None else None
    return sorted(subjects, key=lambda r: r["node_status"] == "superseded")


async def list_words_needed(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """Every Lean file and merged proof that still lacks words (F21-R8), computed from the
    committed products by ``glosses.needed`` (Q6), in the index's target order and each
    product's subject order: equality filters only, nothing ranked (D-25), nothing recorded.

    Every value served is an identifier, a path the gate's layout admits or a reason code, so
    there is no contributor prose to demarcate (D-28's untrusted-data rule wraps prose)."""
    ctx = call.ctx
    target_id = args.get("target_id")
    if target_id is not None:
        target_id = check_id(target_id, "target_id")
    kind = args.get("kind")
    if kind is not None and kind not in WORD_KINDS:
        raise error(
            "filter-unknown",
            f"no such kind: {kind!r}; the kinds are {', '.join(WORD_KINDS)}",
            "adapter",
        )
    index_path = "targets/index.json"
    try:
        index = _at_head(ctx, index_path)
    except _UnreadError as exc:
        raise error(exc.code, exc.message, "graph") from exc
    entries = [e for e in index.get("targets") or [] if isinstance(e, dict)]
    if target_id is not None:
        entries = [e for e in entries if e.get("target_id") == target_id]
        if not entries:
            raise error("not-found", f"no target {target_id} in {index_path} at main", "graph")
    subjects: list[dict[str, Any]] = []
    unread: list[dict[str, str]] = []
    for entry in entries:
        try:
            rows = _target_words(ctx, entry)
        except _UnreadError as exc:
            unread.append(
                {
                    "target": str(entry.get("target_id")),
                    "path": exc.path,
                    "error": exc.code,
                    "message": exc.message,
                }
            )
            continue
        subjects.extend(r for r in rows if kind is None or r["kind"] == kind)
    subjects = _review_and_status(ctx, subjects)
    return {
        "read_at": ctx.head or ctx.settings.graph_branch,
        "target_id": target_id,
        "kind": kind,
        "count": len(subjects),
        "subjects": subjects,
        "unread": unread,
    }


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
        "claim status, annexes, explainers and the submissions open on it.",
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
        "A submission or proposal by its ULID, or by pull-request number (padded or not): the "
        "record, the pull request's live state and, once merged, the attestation it earned or "
        "why there is none. `pull_request.waiting_on` names the one thing it waits for (gate, "
        "step9-review, branch-update, merge, products, or gate-failed), and when that is "
        "gate-failed, `gate_verdict` carries the gate's own diagnostic: why it was refused. "
        "`state` at the top is open, merged or closed. While it is open, `queue` says where it "
        "stands in its own lane of the merge actor's order: the actor runs one lane per target "
        "in parallel, so `position` (from 1) `of` how many, and `ahead`, count only the pull "
        "requests on the same target and any the service cannot place in one target, each with "
        "its number, the service's record of it and the `waiting_on` the service last read for "
        "it (null: not read). Within a lane the order is pull-request number, oldest first; the "
        "actor merges the first green one and passes over a red or conflicting one, so a "
        "position is an upper bound on the merges ahead. "
        "`submission.closed` is the host's own merge or close time, and "
        "`submission.artifact_type` repeats `kind` for a proof, counterexample, vacuity, "
        "reduction or partial (null for any other record).",
        params({"submission_id": {"type": "string"}}, ("submission_id",)),
        get_submission,
    ),
    Tool(
        "list_submissions",
        "Every pull request the service opened on the graph that no live read has yet found "
        "merged or closed: id, kind, node, target, pull-request number and URL, pseudonym, in "
        "the merge actor's order. Each entry's `queue` gives its `position` `of` how many in its "
        "own target's lane (the actor runs one lane per target in parallel) and "
        "the `waiting_on` the service last read for it (null: not read, ask get_submission); "
        "the top-level `queue.order` is the queue's pull-request numbers across every lane. "
        "get_submission gives one with its checks and reviews; get_node lists a node's own.",
        params({}),
        list_submissions,
    ),
    Tool(
        "get_schema",
        "A JSON Schema by name: a protocol record's (`postmortem/v1`, `defect-claim/v1`, ...) "
        "or a tool result's (`mcp/<tool>/v1`). A defect claim of class "
        f"`{requests.CIRCULAR_CLASS}` is written as `{requests.CIRCULAR_SCHEMA}`, every other "
        f"class as `{requests.DEFECT_SCHEMA}`.",
        params({"name": {"type": "string"}}, ("name",)),
        get_schema,
    ),
    Tool(
        "get_precheck",
        "A precheck job's state, diagnostics and signed attestation; poll after "
        "precheck_submission until the state is done or error. A pass that carries "
        "`carried_witnesses` did not check the witness files its `unchecked` lists (the "
        "target's pinned gate predates carried witnesses): it is a pass of the skeleton alone.",
        params({"job_id": {"type": "string"}}, ("job_id",)),
        get_precheck,
    ),
    Tool(
        "get_dco",
        "The Developer Certificate of Origin and the version a write token must accept: "
        "get_token refuses any other version, and nothing else publishes it. Plain path: "
        "GET /dco.json.",
        params({}),
        get_dco,
    ),
    Tool(
        "list_routes",
        "The service's own index: every plain HTTP route with its method, whether it needs a "
        "bearer and what it is for, beside the guide's and this adapter's addresses. Every tool "
        "here has a plain path in it. Plain path: GET /.",
        params({}),
        list_routes,
    ),
    Tool(
        "get_hosted_checkers",
        "Which targets check_lean can serve: each pinned Mathlib commit mapped to the hosted "
        "checker's environment, whether that match is exact, and the environment for a "
        "Mathlib-free target. Plain path: GET /hosted-checkers.json.",
        params({}),
        get_hosted_checkers,
    ),
    Tool(
        "list_my_claims",
        "Your own active claims with their ids (what release_claim takes), oldest first, each "
        "with `others`: who else holds that node. Needs your token, since the list is yours; "
        "the public claims registry names pseudonyms and expiry times only. "
        "Plain path: GET /claims/mine.",
        params({}),
        list_my_claims,
        access="bearer",
    ),
    Tool(
        "get_my_submissions",
        "Your own submissions, by your token: `open`, each as list_submissions gives it (the "
        "record and its `queue` place in its own target's lane), and `recent`, the most "
        "recently merged or closed, newest first, each with `state` (merged or closed). Finds a "
        "pull request again after its receipt was lost; get_submission gives one in full. "
        "Plain path: GET /submissions/mine.",
        params({}),
        get_my_submissions,
        access="bearer",
    ),
    Tool(
        "get_check",
        "Your own record of one check_lean call, by the `log_id` it returned: target, node, "
        "mode, environment, the content's hash and size (never the text), the outcome, `okay`, "
        "the error count and the lint codes. Only the identity that made the call can read it; "
        "anyone else's answers not-found. Plain path: GET /checks/{check_id}.",
        params({"check_id": {"type": "string"}}, ("check_id",)),
        get_check,
        access="bearer",
    ),
    # F09-T15: D-28's read table, notation note of 2026-10-04.
    Tool(
        "list_error_codes",
        "Every error code the gate and the service emit: where it is met (gate, api or both), "
        "the D-4 step that emits it, what it means and what to do about it. `prefix` keeps the "
        "codes that start with it (`witness-`, `relation-`). Look a refusal's `error` or a "
        "verdict's diagnostic `code` up here. Plain path: GET /errors.json.",
        params({"prefix": PREFIX_PARAM}),
        list_error_codes,
    ),
    # F21-T7: D-28's read table, notation note of 2026-10-05.
    Tool(
        "list_words_needed",
        "Every Lean file and merged proof that still lacks words (a gloss for a statement, "
        "witness, relation or definition; an explainer for a proof, alternate or partial), with "
        "its target, file, kind, node, the reason none covers it and, for a proof, the path of "
        "its outline, `in_review` (the open pull request already writing it, {pr_number, "
        "author}, or null) and `node_status` (superseded nodes come last: skip them). "
        "`target_id` keeps one target; `kind` keeps one kind. Read from each "
        "target's glosses.json and target.yaml at main's head; in the record's order, ranked by "
        "nothing. A target whose files could not be read is named under `unread`. Plain path: "
        "targets/<id>/glosses.json and targets/<id>/target.yaml.",
        params({"target_id": ID_PARAM, "kind": {"type": "string"}}),
        list_words_needed,
    ),
)
