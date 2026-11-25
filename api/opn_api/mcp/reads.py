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
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

import yaml

from opn_api import duplicates, frontier, pending, precheck, requests, reviews, session
from opn_api import glosses as glossroutes
from opn_api.app import ApiError, CachedDir, CachedFile, CachedTree
from opn_api.githost import GitHostError
from opn_api.mcp import auth as mcpauth
from opn_api.mcp import demarcate, results
from opn_api.mcp.calls import ID_PARAM, Call, Source, Tool, ToolError, error, params
from opn_gate import (
    closing,
    codes,
    context,
    explainers,
    glosses,
    layout,
    products,
    routes,
    schemas,
)

if TYPE_CHECKING:
    from opn_api.app import Context

log = logging.getLogger(__name__)

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
FRONTIER_SCHEMA = "frontier/v8"  # F08-T44 (D-30 v3.46): v7's fields, relation may be refutes
#: The ``CONTEXT.json`` versions get_node serves: the gate module's own set, plus the version the
#: v3.38 re-pin first renders (F10-T49), so the service accepts it whichever side of that
#: re-pin it is deployed on (the deploy-window lesson of 2026-09-11). F08-T42: ``context/v8``.
CONTEXT_SCHEMAS: tuple[str, ...] = tuple(
    dict.fromkeys(
        (*context.ACCEPTED, "context/v6", "context/v7", "context/v8", "context/v9", "context/v10")
    )
)
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
            ctx.settings.graph_repo, ctx.head or ctx.settings.graph_branch, path, etag=cached.etag
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
    dirs = _tree(ctx, ref, now)
    if dirs is not None:
        return _names(dirs.get(path.strip("/")))
    hold = pending.budget_hold(ctx)
    if hold is not None:
        if cached is not None:
            return _names(cached.names)
        raise error("host-budget-exhausted", hold, "graph")
    try:
        names = ctx.githost.list_dir(ctx.settings.graph_repo, ref, path)
    except GitHostError as exc:
        raise error(
            "graph-unreachable", f"cannot list {path} in the graph: {exc}", "graph"
        ) from exc
    if len(ctx.listings) >= pending.MAX_REMEMBERED:
        ctx.listings.clear()
    ctx.listings[path] = CachedDir(ref, names, now)
    return _names(names)


def _tree(ctx: Context, ref: str, now: float) -> dict[str, list[str]] | None:
    """F14-T33: the graph's files by directory at ``ref``, from one recursive tree read kept
    for the head as a listing is; ``None`` when the tree cannot serve, so the caller lists the
    one directory. A walk over every target (``GET /session``'s roles) is then one host call,
    where one Contents call per directory outgrew the gateway's window at 443 targets. A tree
    the host truncated, a held budget or a failed read all fall back to the directory walk."""
    kept = ctx.tree
    if (
        kept is not None
        and kept.ref == ref
        and (ctx.head is not None or now - kept.fetched_at < ctx.settings.frontier_max_stale_s)
    ):
        return kept.dirs
    if pending.budget_hold(ctx) is not None:
        return None
    try:
        dirs = ctx.githost.list_tree(ctx.settings.graph_repo, ref)
    except GitHostError as exc:
        log.warning("the graph's tree at %s could not be read, listing by directory: %s", ref, exc)
        return None
    ctx.tree = CachedTree(ref, dirs, now)
    return dirs


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


# --- mcpfix WA2 (testers 2026-11-25, qa-ea B3): compact answers, in pages ---------------------

#: A page's position: the ``next`` of the answer before. An offset into the list as the record
#: orders it, written as a string so that a client treats it as a token and never computes one.
CURSOR_PARAM: dict[str, Any] = {
    "type": "string",
    "pattern": "^(0|[1-9][0-9]{0,8})$",
    "description": "The last answer's `next`.",
}
FULL_PARAM: dict[str, Any] = {"type": "boolean", "description": "The plain path's whole body."}


def limit_param(default: int, maximum: int, what: str) -> dict[str, Any]:
    return {
        "type": "integer",
        "minimum": 1,
        "maximum": maximum,
        "description": f"{what.capitalize()} per page (default {default}).",
    }


def page(
    rows: list[Any], args: dict[str, Any], *, default: int
) -> tuple[list[Any], dict[str, Any]]:
    """One page of ``rows`` and what says where it sits: ``count`` (every row there is),
    ``limit``, ``cursor`` (where this page starts, null for the first) and ``next`` (the cursor
    of the page after, null on the last). The input schema has bounded ``limit`` and shaped
    ``cursor`` already; a cursor past the end is an empty last page."""
    limit = int(args.get("limit") or default)
    cursor = args.get("cursor")
    start = int(cursor) if isinstance(cursor, str) and cursor else 0
    end = start + limit
    return rows[start:end], {
        "count": len(rows),
        "limit": limit,
        "cursor": cursor if cursor else None,
        "next": str(end) if end < len(rows) else None,
    }


def known_target(ctx: Context, target_id: str) -> None:
    """``not-found`` for a target the index at main does not list (item 8: one code for one
    condition, whichever read meets it)."""
    try:
        listed = session.target_ids(ctx)
    except ApiError as exc:
        raise from_api_error(exc) from exc
    if target_id not in listed:
        raise error("not-found", f"no target {target_id} in targets/index.json at main", "graph")


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


#: mcpfix WA2: a target's row in list_targets' default answer, ``targets-index``'s own field names.
#: The index carries no title; ``root`` names the target's root statement.
TARGET_SUMMARY: tuple[str, ...] = (
    "target_id",
    "root",
    "status",
    "track",
    "claimable",
    "node_counts",
)
#: The index's newest row schema, whose fields ``fields`` may name.
INDEX_SCHEMA = "targets-index/v11"
TARGETS_LIMIT = (50, 200)


def _index_fields() -> list[str]:
    props: dict[str, Any] = schemas.load_schema(INDEX_SCHEMA)["properties"]["targets"]["items"][
        "properties"
    ]
    return sorted(props)


async def list_targets(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """``targets/index.json``. mcpfix WA2 (the owner's ruling, 2026-11-25): by default a page of
    summary rows (``TARGET_SUMMARY``); ``target_id`` answers that target's row with every field,
    ``fields`` names the fields a row carries beside its id, and ``full: true`` answers the
    committed index exactly, the plain path (D-28)."""
    ctx = call.ctx
    path = "targets/index.json"
    index = document(ctx, path)
    if args.get("full"):
        if any(args.get(k) is not None for k in ("target_id", "fields", "limit", "cursor")):
            raise error(
                "arguments-invalid",
                "full answers the whole index; it takes nothing else",
                "adapter",
            )
        return index
    fields = args.get("fields")
    if fields is not None:
        unknown = sorted(f for f in fields if f not in _index_fields())
        if unknown:
            raise error(
                "filter-unknown",
                f"no such target field: {', '.join(unknown)}; the fields are "
                + ", ".join(_index_fields()),
                "adapter",
            )
    rows = [r for r in index.get("targets") or [] if isinstance(r, dict)]
    target_id = args.get("target_id")
    if target_id is not None:
        target_id = check_id(target_id, "target_id")
        rows = [r for r in rows if r.get("target_id") == target_id]
        if not rows:
            raise error("not-found", f"no target {target_id} in {path} at main", "graph")
    if fields is not None:
        keep = ["target_id", *(f for f in fields if f != "target_id")]
    elif target_id is not None:
        keep = None  # one target: every field it has
    else:
        keep = list(TARGET_SUMMARY)
    chunk, where = page(rows, args, default=TARGETS_LIMIT[0])
    return {
        "read_at": ctx.head or ctx.settings.graph_branch,
        "index_schema": str(index.get("schema")),
        "rendered_from": index.get("rendered_from"),
        **where,
        "fields": keep,
        "targets": [r if keep is None else {k: r[k] for k in keep if k in r} for r in chunk],
    }


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
    # F25-R15 (D-3 v3.37): the target's registrations, as graph/v7 publishes them; a graph.json
    # rendered before v7 carries none, and the answer says so with an empty list.
    registrations = graph.get("registrations")
    return {
        "target_id": target_id,
        "graph": graph,
        "approaches": approaches,
        "registrations": registrations if isinstance(registrations, list) else [],
        "untrusted_note": demarcate.UNTRUSTED_NOTE,
    }


async def list_registrations(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """F25-R15 (D-3, D-10 v3.37): every registration the products derive per target, read from
    ``targets/index.json``'s rows (``targets-index/v10``'s ``registrations``), in the index's
    order: nothing is ranked (D-25) and nothing is recorded. An index rendered before v10 carries
    the field on no row, so it lists none. Every value is an identifier, an enum or a url the
    products built from validated records, so nothing is demarcated."""
    ctx = call.ctx
    target_id = args.get("target_id")
    if target_id is not None:
        target_id = check_id(target_id, "target_id")
    index_path = "targets/index.json"
    index = document(ctx, index_path)
    entries = [e for e in index.get("targets") or [] if isinstance(e, dict)]
    if target_id is not None:
        entries = [e for e in entries if e.get("target_id") == target_id]
        if not entries:
            raise error("not-found", f"no target {target_id} in {index_path} at main", "graph")
    found: list[dict[str, Any]] = []
    for entry in entries:
        rows = entry.get("registrations")
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict):
                found.append({"target_id": str(entry.get("target_id")), **row})
    return {
        "read_at": ctx.head or ctx.settings.graph_branch,
        "target_id": target_id,
        "count": len(found),
        "registrations": found,
    }


# --- F26-T10 (D-9, D-28 v3.39): the formalization review ---------------------------------------

#: F26-T19: the instance a refutation template is asked at.
REFUTE_N = {
    "type": "integer",
    "minimum": 0,
    "description": "An instance: refutation templates at n.",
}


async def get_review(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """``GET /reviews/<id>``, body for body, with the caller's bearer forwarded when the
    request carried one: the route applies the blind rule to it (F26-R3, AC12), so an anonymous
    caller and a bearer with no candidate on the record see no candidate's Lean, and a
    candidate's author sees every one. The read is open — the review is public — which is why
    the tool is declared ``anyone`` and reads the verified bearer itself rather than requiring
    one (a read tool is never ``endpoint``, ``calls.Tool``). The words, cases, questions and
    answers are contributor text, so the answer carries the untrusted note."""
    target_id = check_id(args.get("target_id"), "target_id")
    n = refutation_n(args)
    with_bearer = Call(call.ctx, call.http, token=mcpauth.bearer(), calls=call.calls)
    query = "" if n is None else f"?n={n}"
    try:
        doc = service_answer(
            await with_bearer.endpoint("GET", f"/reviews/{target_id}{query}"), "/reviews/<id>"
        )
    except ToolError as exc:
        # mcpfix WA2 (item 8): the route says target-unknown; every other read says not-found,
        # so the adapter answers that code for the same condition (qa-ea B5).
        if exc.doc.get("error") == "target-unknown":
            exc.doc["error"] = "not-found"
        raise
    return {**doc, "untrusted_note": demarcate.UNTRUSTED_NOTE}


def refutation_n(args: dict[str, Any]) -> int | None:
    """F26-T19: the instance a refutation template is asked at, or ``None``."""
    n = args.get("n")
    if n is not None and (isinstance(n, bool) or not isinstance(n, int) or n < 0):
        raise error("arguments-invalid", "n is a natural number", "adapter")
    return n


def _review_targets(ctx: Context, target_id: str | None) -> list[str]:
    """The targets to read: the one named (``not-found`` when the index lacks it), else every
    target the index lists, in its order."""
    try:
        listed = session.target_ids(ctx)
    except ApiError as exc:
        raise from_api_error(exc) from exc
    if target_id is None:
        return listed
    if target_id not in listed:
        raise error("not-found", f"no target {target_id} in targets/index.json at main", "graph")
    return [target_id]


async def list_review_questions(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """The questions no answer names, per target, read from ``targets/<id>/review/questions/``
    and ``answers/`` at ``main`` (F26-R7); in the records' order, ranked by nothing. A question
    is contributor-facing text written by the gate's job from exhibits; the answer carries the
    untrusted note all the same, since a send-back's question is a signer's words."""
    ctx = call.ctx
    target_id = args.get("target_id")
    if target_id is not None:
        target_id = check_id(target_id, "target_id")
    found: list[dict[str, Any]] = []
    try:
        targets = _review_targets(ctx, target_id)
        if target_id is None:
            # mcpfix WA2 (item 6, qa-ea U1): only the targets that have a review, their records
            # read in parallel, instead of 445 review.yaml reads in series past the Lambda's 29 s
            targets = reviewed_targets(ctx, targets)
            frontier.prefetch(ctx, review_record_paths(ctx, targets))
        for target in targets:
            found.extend(reviews.waiting_questions(ctx, target))
    except ApiError as exc:
        raise from_api_error(exc) from exc
    chunk, where = page(found, args, default=QUESTIONS_LIMIT[0])
    return {
        "read_at": ctx.head or ctx.settings.graph_branch,
        "target_id": target_id,
        **where,
        "questions": chunk,
        "untrusted_note": demarcate.UNTRUSTED_NOTE,
    }


#: mcpfix WA2: list_review_questions' page, default and most.
QUESTIONS_LIMIT = (50, 200)
#: The review records list_review_questions reads beside ``review.yaml``.
QUESTION_DIRS = ("questions", "answers")


def reviewed_targets(ctx: Context, targets: list[str]) -> list[str]:
    """The ``targets`` that hold a ``review/review.yaml`` at main, in their order. Read from the
    tree the service keeps for the head (F14-T33), which costs nothing once read; when the tree
    cannot serve, each target is asked in parallel (``frontier.PREFETCH_WORKERS``), an absent
    file answering ``None`` and an unreadable one an error, never a silent absence (C7)."""
    frontier.pin_head(ctx)
    dirs = _tree(ctx, ctx.head or ctx.settings.graph_branch, time.monotonic())
    if dirs is not None:
        return [t for t in targets if "review.yaml" in (dirs.get(reviews.review_dir(t)) or [])]
    frontier.generation(ctx)  # settled once, before the threads (frontier.prefetch's rule)

    def has_review(target: str) -> bool:
        return (
            committed(ctx, f"{reviews.review_dir(target)}/review.yaml", optional=True) is not None
        )

    with ThreadPoolExecutor(max_workers=frontier.PREFETCH_WORKERS) as pool:
        present = list(pool.map(has_review, targets))
    return [t for t, yes in zip(targets, present, strict=True) if yes]


def review_record_paths(ctx: Context, targets: list[str]) -> list[str]:
    """Every file ``waiting_questions`` will read for ``targets``, for one parallel prefetch."""
    paths: list[str] = []
    for t in targets:
        base = reviews.review_dir(t)
        paths.append(f"{base}/review.yaml")
        for sub in QUESTION_DIRS:
            paths += [f"{base}/{sub}/{name}" for name in listing(ctx, f"{base}/{sub}")]
    return paths


async def list_open_pairs(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """Each open pair direction with its last attempt, read from ``targets/<id>/review/pairs/``
    at ``main`` (F26-R8); a proof or refutation of one is a ``pair-proof`` artifact through
    ``submit_proof``. In the records' order, ranked by nothing (D-25; F26-Q6: not a frontier
    entry). Every value is an id, an enum or the gate's own attempt record."""
    ctx = call.ctx
    target_id = args.get("target_id")
    if target_id is not None:
        target_id = check_id(target_id, "target_id")
    n = refutation_n(args)
    caller = mcpauth.caller_pseudonym(ctx)
    found: list[dict[str, Any]] = []
    try:
        targets = _review_targets(ctx, target_id)
        if target_id is None:  # mcpfix WA2: as list_review_questions reads them (qa-ea U1)
            targets = reviewed_targets(ctx, targets)
        for target in targets:
            found.extend(reviews.open_directions(ctx, target, caller, n))
    except ApiError as exc:
        raise from_api_error(exc) from exc
    return {
        "read_at": ctx.head or ctx.settings.graph_branch,
        "target_id": target_id,
        "count": len(found),
        "pairs": found,
    }


async def list_sufficient_sets(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """F27-R9 (D-25, D-28 v3.40): a target's routes and sufficient sets, derived from its
    ``graph.json`` at main and the frontier the service serves by ``opn_gate.routes.read``, the
    function the site renders from (F27-Q1). The finest cuts by default; ``cut: any`` adds the
    coarser ones up to the service's cap (``routes_max_sets``). In the record's order, ranked by
    nothing (D-25). F09-T76 (D-25 v3.46): each set says which way it ``settles`` the root and
    the selector forks on the ``side`` when both exist (result schema v4). Every value is an
    id, a count, an enum or a frontier timestamp, so nothing is demarcated."""
    ctx = call.ctx
    target_id = check_id(args.get("target_id"), "target_id")
    cut = args.get("cut", "finest")
    if cut not in routes.CUTS:
        raise error("arguments-invalid", f"cut must be one of {', '.join(routes.CUTS)}", "adapter")
    # F27-T9 (R13): stop at a proved statement (the default) or follow what its proof rests on
    at_proved = args.get("at_proved", "stop")
    if at_proved not in routes.AT_PROVED:
        raise error(
            "arguments-invalid",
            f"at_proved must be one of {', '.join(routes.AT_PROVED)}",
            "adapter",
        )
    graph = document(ctx, f"targets/{target_id}/graph.json")
    served = service_answer(await call.endpoint("GET", "/frontier.json"), "/frontier.json")
    found = routes.read(
        graph,
        served.get("entries") or [],
        cut=cut,
        max_sets=ctx.settings.routes_max_sets,
        at_proved=at_proved,
    )
    # F28-T4 (R12, v3.41): the nodes whose proof exists in parts, read from the same graph; a
    # closable node is still open until its closing proof merges.
    closable = [c.as_dict() for c in closing.closable(graph)]
    doc = found.as_dict()
    every = doc["sets"]
    set_id = args.get("set_id")
    if set_id is not None:
        every = [s for s in every if s["id"] == set_id]
        if not every:
            raise error(
                "not-found",
                f"no set {set_id} among {target_id}'s {cut} sufficient sets at main",
                "graph",
            )
    # mcpfix WA2 (item 3): the sets in pages, enumerated in full first so that a page and its
    # count are of one enumeration; truncated says some set was left out of this answer.
    chunk, where = page(every, args, default=SETS_LIMIT[0])
    detail = args.get("detail", "compact")
    out: dict[str, Any] = {
        "read_at": ctx.head or ctx.settings.graph_branch,
        **doc,
        **where,
        "set_id": set_id,
        "truncated": found.truncated or where["next"] is not None or where["cursor"] is not None,
        "capped": found.truncated,
        "sets": chunk if detail == "full" else [compact_set(s) for s in chunk],
        "routes": [
            r if detail == "full" else compact_route(r)
            for r in page_routes(doc["routes"], doc["sets"], chunk)
        ],
        "detail": detail,
        "closable": closable,
    }
    if args.get("include_selector"):
        # F29-R8 (D-25 v3.44): the selector tree over every set, built from them alone (R6)
        out["selector"] = routes.selector_tree(found).as_dict()
    return out


#: mcpfix WA2: list_sufficient_sets' page of sets, default and most.
SETS_LIMIT = (5, 200)
#: mcpfix (lead, 2026-11-25): how much of each set and route row the answer carries.
DETAIL = ("compact", "full")
COMPACT_SUMMARY = ("holes", "proved", "open", "dead", "unresolved")


def compact_set(sufficient: dict[str, Any]) -> dict[str, Any]:
    """A set without ``statements``, which is its ``proved`` and its ``open`` together."""
    return {k: v for k, v in sufficient.items() if k != "statements"}


def compact_route(route: dict[str, Any]) -> dict[str, Any]:
    """A route row with what a reader needs to choose a set: no approach text, and each hole only
    its node and status (erdos-1094's default answer was 98,730 characters, 52,872 of them route
    rows repeating every hole's label, attempts and refuted classes)."""
    return {
        "id": route["id"],
        "node": route["node"],
        "live": route["live"],
        "resolved": route["resolved"],
        "holes": [{"node": h["node"], "status": h["status"]} for h in route["holes"]],
        "summary": {k: route["summary"][k] for k in COMPACT_SUMMARY},
    }


def page_routes(
    every_route: list[dict[str, Any]],
    every_set: list[dict[str, Any]],
    chunk: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """The routes a page answers: those its sets use, and those no set uses at all (a dead or
    unresolved decomposition, which no page would otherwise show, so a stall still shows), in
    the enumeration's order."""

    def used(sets: list[dict[str, Any]]) -> set[str]:
        return {r for s in sets for r in (*s["routes"], *s["proof_routes"])}

    anywhere, here = used(every_set), used(chunk)
    return [r for r in every_route if r["id"] in here or r["id"] not in anywhere]


def _entry_fields() -> dict[str, Any]:
    props: dict[str, Any] = schemas.load_schema(FRONTIER_SCHEMA)["properties"]["entries"]["items"][
        "properties"
    ]
    return props


def filters_param() -> dict[str, Any]:
    """F09-T21 (Q20): the filters parameter, its fields named from the frontier schema the
    filters are checked against, so the description cannot drift from what is accepted."""
    fields = ", ".join(f"`{f}`" for f in sorted(_entry_fields()))
    return {
        "type": "object",
        "description": "Field: value pairs, all of which an entry must match: equality on a "
        "scalar field, containment on a list field, a dotted path into an object field "
        f"(`tags.library`). The fields: {fields}.",
    }


def _resolve(entry: dict[str, Any], field: str) -> tuple[bool, Any]:
    node: Any = entry
    for step in field.split("."):
        if not isinstance(node, dict) or step not in node:
            return False, None
        node = node[step]
    return True, node


def _properties_of(node: Any) -> dict[str, Any]:
    """A schema node's object properties, read through a ``oneOf``/``anyOf`` as well (F09-T24:
    ``literature`` and ``literature_proposed`` are nullable objects, and a dotted path into one
    is a path into its object branch; on an entry where it is null the filter matches nothing)."""
    if not isinstance(node, dict):
        return {}
    out: dict[str, Any] = dict(node.get("properties", {}))
    for branch in [*node.get("oneOf", []), *node.get("anyOf", [])]:
        out.update(_properties_of(branch))
    return out


def _known_field(field: str) -> bool:
    props = _entry_fields()
    steps = field.split(".")
    node: Any = {"properties": props}
    for step in steps:
        inner = _properties_of(node)
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
    target_id = args.get("target_id")
    if target_id is not None:
        target_id = check_id(target_id, "target_id")
    doc = service_answer(await call.endpoint("GET", "/frontier.json"), "/frontier.json")
    entries = [e for e in doc.get("entries", []) if matches(e, filters)]
    if target_id is not None:
        if not any(e.get("target_id") == target_id for e in doc.get("entries", [])):
            known_target(call.ctx, target_id)  # a target with no open work is no error
        entries = [e for e in entries if e.get("target_id") == target_id]
    if args.get("full"):
        if args.get("limit") is not None or args.get("cursor") is not None:
            raise error("arguments-invalid", "full answers every entry; it is not paged", "adapter")
        return {**doc, "entries": entries}
    if target_id is not None:
        chunk, where = page(entries, args, default=FRONTIER_LIMIT[0])
        return {
            "rendered_from": doc.get("rendered_from"),
            "target_id": target_id,
            **where,
            "entries": chunk,
        }
    chunk, where = page(frontier_targets(call.ctx, entries), args, default=FRONTIER_LIMIT[0])
    return {"rendered_from": doc.get("rendered_from"), **where, "targets": chunk}


#: mcpfix WA2: list_frontier's page size, default and most.
FRONTIER_LIMIT = (50, 200)


def frontier_targets(ctx: Context, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per target that has an entry: its root, track and status from the index at main,
    how many of its entries there are (``open``) and how many are claimable; in the index's
    order, a target the index does not list yet (a product lag) after them in the frontier's.
    Ranked by nothing (D-25)."""
    counts: dict[str, list[int]] = {}
    for e in entries:
        tally = counts.setdefault(str(e.get("target_id")), [0, 0])
        tally[0] += 1
        tally[1] += 1 if e.get("claimable") is True else 0
    index = document(ctx, "targets/index.json")
    listed = {str(r.get("target_id")): r for r in index.get("targets") or [] if isinstance(r, dict)}
    order = [t for t in listed if t in counts] + [t for t in counts if t not in listed]
    return [
        {
            "target_id": t,
            "root": listed.get(t, {}).get("root"),
            "track": listed.get(t, {}).get("track"),
            "status": listed.get(t, {}).get("status"),
            "open": counts[t][0],
            "claimable": counts[t][1],
        }
        for t in order
    ]


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
        if declared not in CONTEXT_SCHEMAS:
            raise error(
                "context-invalid",
                f"{path} declares {declared!r}; expected one of {', '.join(CONTEXT_SCHEMAS)}",
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
    reach a proof through the node's own ``Context``, and so does a proved lemma's (D-12
    v3.38: a node another branch's hole restated, listed in ``lemmas``, which a direct proof may
    name as it names a hole's); a statement written since 2026-09-20
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
#: Every glosses product version the live graph may carry: the current one and every older one
#: still committed until each target is re-rendered. Named explicitly, never derived from the
#: current constant: deriving it dropped v2 the day v3 shipped and broke get_node live (2026-10-18).
GLOSSES_SCHEMAS: frozenset[str] = frozenset({"glosses/v1", "glosses/v2", "glosses/v3"})


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


#: The prose sections of a node's bundle a caller may leave out (F09-T19, Q18), in answer order.
PROSE_SECTIONS: tuple[str, ...] = (
    "annexes",
    "explainers",
    "outlines",
    "gloss_chains",
    "explainer_chains",
)
#: mcpfix WA2 (item 5): the context's own bulk a caller may leave out too — the attempt records
#: and each dependency's (and lemma's) statement. Every section is answered when ``include`` is
#: omitted; named ones only when it is given.
CONTEXT_SECTIONS: tuple[str, ...] = ("attempts", "deps")
INCLUDE_SECTIONS: tuple[str, ...] = (*PROSE_SECTIONS, *CONTEXT_SECTIONS)
#: The context's Lean text that ``files`` carries byte for byte: answered once when ``include``
#: leaves any section out.
CONTEXT_LEAN: tuple[tuple[str, str], ...] = (
    ("statement", "Statement.lean"),
    ("witness", "Witness.lean"),
)


def narrowed_context(
    bundle: dict[str, Any], wanted: set[str], files: dict[str, str | None]
) -> dict[str, Any]:
    """The context with what the caller left out taken out, and ``omitted`` naming each part
    taken (mcpfix WA2, item 5): the attempt records (the counts, histogram and refuted classes
    stay), each dependency's and lemma's ``signature`` (the ids, statuses and hashes stay; the
    top-level ``lemmas`` keep theirs), and the statement's and witness's text where ``files``
    holds the same bytes. No longer a ``context/v<n>`` document: ``omitted`` says so."""
    out = dict(bundle)
    omitted: list[str] = []
    attempts = out.get("attempts")
    if "attempts" not in wanted and isinstance(attempts, dict) and "records" in attempts:
        out["attempts"] = {k: v for k, v in attempts.items() if k != "records"}
        omitted.append("attempts.records")
    if "deps" not in wanted:
        for key in ("deps", "lemmas"):
            rows = out.get(key)
            if isinstance(rows, list) and any(
                isinstance(r, dict) and "signature" in r for r in rows
            ):
                out[key] = [
                    {k: v for k, v in r.items() if k != "signature"} if isinstance(r, dict) else r
                    for r in rows
                ]
                omitted.append(f"{key}[].signature")
    for key, name in CONTEXT_LEAN:
        part = out.get(key)
        if (
            isinstance(part, dict)
            and part.get("text") is not None
            and part["text"] == files.get(name)
        ):
            out[key] = {**part, "text": None}
            omitted.append(f"{key}.text")
    if omitted:
        out["omitted"] = omitted
    return out


#: The sections read from the node's chains of words, and so answered with ``chains_source``.
CHAIN_SECTIONS = frozenset({"outlines", "gloss_chains", "explainer_chains"})


def node_labels(ctx: Context, target_id: str, node_id: str) -> dict[str, Any]:
    """F29-R8: ``label``, ``label_source`` and ``claim`` from the node's ``graph.json`` row
    (graph/v12, F29-R3). On an older product, or a row without them: the id, ``id``, null.
    Read from the product, never from ``CONTEXT.json`` (its two builders must agree, F10-Q7)."""
    graph = document(ctx, f"targets/{target_id}/graph.json")
    row = next(
        (
            n
            for n in graph.get("nodes") or []
            if isinstance(n, dict) and n.get("node_id") == node_id
        ),
        {},
    )
    label = row.get("label")
    source = row.get("label_source")
    claim = row.get("claim")
    if not isinstance(label, str) or not label or source not in LABEL_SOURCES:
        label, source = node_id, "id"
    return {
        "label": label,
        "label_source": source,
        "claim": claim if isinstance(claim, str) and claim else None,
    }


#: graph/v12's ``label_source`` values (D-25 v3.44).
LABEL_SOURCES: frozenset[str] = frozenset({"gloss", "hole", "target", "id"})

#: The fields of a ``target_proofs`` entry that name the proof in ``in_closure`` (F22-T9).
PROOF_KEYS: tuple[str, ...] = ("node_id", "kind", "path", "artifact_hash")


def node_structure(ctx: Context, target_id: str, node_id: str) -> dict[str, Any]:
    """F22-T9 (request H, Q3): ``proposed_for``, the node's row's pointer (F18-R8), and
    ``in_closure``, each of the target's proofs (``target_proofs``, F18-R1) whose closure holds
    the node, in the record's order. Read from ``graph.json`` like the labels (F10-Q7); a product
    older than either field answers null and []."""
    graph = document(ctx, f"targets/{target_id}/graph.json")
    row = next(
        (
            n
            for n in graph.get("nodes") or []
            if isinstance(n, dict) and n.get("node_id") == node_id
        ),
        {},
    )
    pointer = row.get("proposed_for")
    proofs = graph.get("target_proofs")
    in_closure = [
        {key: p[key] for key in PROOF_KEYS}
        for p in (proofs if isinstance(proofs, list) else [])
        if isinstance(p, dict) and node_id in (p.get("closure") or [])
    ]
    return {
        "proposed_for": pointer if isinstance(pointer, str) and pointer else None,
        "in_closure": in_closure,
    }


async def get_node(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    node_id = check_id(args.get("node_id"), "node_id")
    # T19: every prose section unless the caller names the ones it wants (the owner's ruling:
    # full by default). The input schema has already refused an unknown name.
    wanted = set(INCLUDE_SECTIONS if args.get("include") is None else args["include"])
    narrowed = wanted != set(INCLUDE_SECTIONS)  # naming every section is the omitted answer
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
    bundle = frontier.read_at(call.ctx, bundle)  # F05-T30: the commit its files were read at
    lemmas = list(bundle.get("lemmas") or [])  # whole at the top level, whatever is narrowed
    if narrowed:
        bundle = narrowed_context(bundle, wanted, files)
    out: dict[str, Any] = {
        "node_id": node_id,
        "target_id": target_id,
        # F29-R8 (D-3, D-25 v3.44): the node's label, where it came from and its claim, as
        # graph.json carries them (R3); a product rendered before v3.44 has none, and the
        # answer falls back as the generator would with nothing on the record: the id.
        **node_labels(call.ctx, target_id, node_id),
        # F22-T9: what it was proposed for and which of the target's proofs rest on it.
        **node_structure(call.ctx, target_id, node_id),
        "context": bundle,
        "context_source": source,
        "closing": closing_route(node_id, files.get("Statement.lean")),
        "files": files,
        "claims": dict(entry["claims"]) if entry is not None else None,
        # F09-T72 (D-12 v3.38): the lemmas the bundle lists — nodes under other branches a
        # merged partial of this node restated as holes, usable once proved — lifted beside
        # the bundle so an agent reads what a proof may draw on without knowing the version;
        # a bundle older than context/v6 has no key and the answer says none.
        "lemmas": lemmas,
    }
    # A section not asked for is not read from the host either (T19).
    if "annexes" in wanted:
        out["annexes"] = _prose(call.ctx, f"{node_dir}/annex")
    if "explainers" in wanted:
        out["explainers"] = _prose(call.ctx, f"{node_dir}/explainer")
    if wanted & CHAIN_SECTIONS:
        # F20-R11: the outlines an explainer's sections name steps of, and every chain of words
        # on the node's Lean files and merged proofs, from the product or derived (F10-Q7).
        subjects, chains_source = node_chains(call.ctx, target_id, node_id)
        if "outlines" in wanted:
            out["outlines"] = node_outlines(call.ctx, target_id, subjects)
        if "gloss_chains" in wanted:
            out["gloss_chains"] = [s for s in subjects if s["record"] == "gloss"]
        if "explainer_chains" in wanted:
            out["explainer_chains"] = [s for s in subjects if s["record"] == "explainer"]
        out["chains_source"] = chains_source
    # F09-T7: the pull requests already open on this node, as GET /submissions.json lists them.
    out["submissions"] = {
        "open": [s for s in pending.get("open", []) if s.get("node_id") == node_id]
    }
    out["untrusted_note"] = demarcate.UNTRUSTED_NOTE
    return out


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
    """``GET /submissions.json`` body for body (F09-T7; D-28's notation note of 2026-09-14), its
    filters as the route's (F22-T8): ``target_id``, ``node_id`` and ``kind``."""
    names = {"target_id": "target", "node_id": "node", "kind": "kind"}
    if args.get("target_id") is not None:
        # mcpfix WA2 (item 8, qa-ea B4): the route filters by any string, so an unknown target
        # answered "nothing open"; the adapter names it not-found as every other read does.
        known_target(call.ctx, check_id(args["target_id"], "target_id"))
    query = {names[k]: str(v) for k, v in args.items() if k in names and v is not None}
    path = "/submissions.json" + (f"?{urlencode(query)}" if query else "")
    return service_answer(await call.endpoint("GET", path), "/submissions.json")


async def get_schema(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    name = args.get("name")
    if not isinstance(name, str):
        raise error("arguments-invalid", "name is required", "adapter")
    tool = results.tool_of(name)
    if tool is not None:
        try:
            return results.load(tool, results.version_named(name))
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
    (F13-R11; D-28 notation note 2026-09-20). mcpfix WA2: the per-target map is one row per
    target (53k characters live, 2026-11-25), so by default the answer carries the pins, the
    core environment and ``target_count``; ``target_id`` adds that target's row; ``full: true``
    is the route's body exactly."""
    path = "/hosted-checkers.json"
    doc = service_answer(await call.endpoint("GET", path), path)
    if args.get("full"):
        if args.get("target_id") is not None:
            raise error("arguments-invalid", "full answers every target already", "adapter")
        return doc
    listed = doc.get("targets")
    every: dict[str, Any] = listed if isinstance(listed, dict) else {}
    out = {k: v for k, v in doc.items() if k != "targets"}
    out["target_count"] = len(every)
    target_id = args.get("target_id")
    if target_id is not None:
        target_id = check_id(target_id, "target_id")
        if target_id not in every:
            known_target(call.ctx, target_id)
            raise error(
                "not-found",
                f"{target_id} has no row in {path}; check_lean cannot serve it",
                "service",
            )
        out["targets"] = {target_id: every[target_id]}
    return out


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
PREFIX_PARAM: dict[str, Any] = {
    "type": "string",
    "pattern": "^[a-z0-9_-]{0,64}$",
    "description": "Only the codes that start with this.",
}


#: mcpfix WA2: list_error_codes' page of codes, default and most. The whole catalog's codes and
#: meanings are 72k characters (526 codes, 2026-11-25), so even the one-line form is paged.
CODES_LIMIT = (100, 600)


async def list_error_codes(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """``GET /errors.json`` (F13-T29); ``prefix`` is passed through as the route's own query
    parameter. mcpfix WA2 (the owner's ruling, 2026-11-25): by default each code with its
    meaning only, in pages; ``code`` answers one code's whole row, read from the route with the
    code as its prefix (an unknown code is ``not-found``, naming the close ones); ``full: true``
    answers the route's body exactly, the plain path (D-28)."""
    path = "/errors.json"
    code = args.get("code")
    prefix = code if code is not None else args.get("prefix")
    query = f"?{urlencode({'prefix': prefix})}" if prefix else ""
    doc = service_answer(await call.endpoint("GET", path + query), path)
    if code is not None:
        rows = [r for r in doc.get("codes") or [] if r.get("code") == code]
        if not rows:
            close = codes.close_matches(code)
            raise error(
                "not-found",
                f"no error code {code}"
                + (f"; the close ones: {', '.join(close)}" if close else "")
                + "; list_error_codes with a prefix lists codes",
                "adapter",
            )
        return {**doc, "count": len(rows), "codes": rows}
    if args.get("full"):
        if args.get("limit") is not None or args.get("cursor") is not None:
            raise error("arguments-invalid", "full answers every code; it is not paged", "adapter")
        return doc
    rows = [{"code": r["code"], "meaning": r["meaning"]} for r in doc.get("codes") or []]
    chunk, where = page(rows, args, default=CODES_LIMIT[0])
    return {"prefix": doc.get("prefix"), **where, "codes": chunk}


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
GLOSSES_VERSIONS = frozenset({"glosses/v1", "glosses/v2", "glosses/v3"})


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
    # mcpfix WA2: two files a target, read in parallel first (443 targets read in series is
    # the shape that outran the Lambda's window, qa-ea U1)
    frontier.prefetch(
        ctx,
        [
            f"targets/{e.get('target_id')}/{name}"
            for e in entries
            for name in (products.GLOSSES_FILE, "target.yaml")
        ],
    )
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
    # mcpfix WA2: in pages; the review state and node status are read for the page's rows only
    # after the order is fixed, so superseded rows still come last across every page.
    subjects = _review_and_status_order(ctx, subjects)
    chunk, where = page(subjects, args, default=WORDS_LIMIT[0])
    return {
        "read_at": ctx.head or ctx.settings.graph_branch,
        "target_id": target_id,
        "kind": kind,
        **where,
        "subjects": _review_and_status(ctx, chunk),
        "unread": unread,
    }


#: mcpfix WA2: list_words_needed's page, default and most.
WORDS_LIMIT = (50, 200)


def _review_and_status_order(ctx: Context, subjects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The subjects in the order ``_review_and_status`` answers them — superseded nodes last,
    the record's order otherwise — computed before the page is cut."""
    statuses: dict[str, dict[str, str]] = {}
    for row in subjects:
        target = str(row["target"])
        if target not in statuses:
            statuses[target] = _node_statuses(ctx, target)

    def superseded(row: dict[str, Any]) -> bool:
        node = row.get("node")
        return node is not None and statuses[str(row["target"])].get(str(node)) == "superseded"

    return sorted(subjects, key=superseded)


TOOLS: tuple[Tool, ...] = (
    Tool(
        "server_info",
        "Protocol version, gate-spec hashes, schema index and the rate-limit policy in force.",
        params({}),
        server_info,
    ),
    Tool(
        "list_targets",
        "The graphs, in pages: by default each target's id, root, status, track, claimable and "
        "node_counts. `target_id` answers one target with every field (fidelity, mathlib_sha, "
        "stewards, review, ...); `fields` names the fields each row carries beside its id; "
        "`next` is the `cursor` of the page after. `full: true` is targets/index.json exactly "
        "(large). Plain path: targets/index.json.",
        params(
            {
                "target_id": {**ID_PARAM, "description": "Only this target, with every field."},
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                    "description": "The index fields each row carries beside target_id.",
                },
                "limit": limit_param(*TARGETS_LIMIT, "targets"),
                "cursor": CURSOR_PARAM,
                "full": FULL_PARAM,
            }
        ),
        list_targets,
    ),
    Tool(  # F25-R15: `registrations` rides beside the graph, as graph/v7 publishes them
        "get_target",
        "A target's graph structure and node statuses, with its approach records.",
        params({"target_id": ID_PARAM}, ("target_id",)),
        get_target,
    ),
    Tool(
        "list_frontier",
        "The open work, in pages. By default one row per target with open nodes: target_id, "
        "root, track, status, `open` (its entries) and `claimable` (how many may be claimed). "
        "`target_id` answers that target's open nodes (holes included) with D-25's observed "
        "facts and live claim status. `filters` is an object of frontier field to value "
        "(dotted for nested, e.g. `tags.library`): equality on a scalar field, containment on a "
        "list field, applied to the entries. `next` is the `cursor` of the page after. The "
        "file's order, no ranking. An entry's `literature` is its confirmed status (with "
        "`disputes`, or null) and `literature_proposed` the one awaiting a steward. "
        "`full: true` is GET /frontier.json exactly (large).",
        params(
            {
                "target_id": {**ID_PARAM, "description": "Only this target's open nodes."},
                "filters": filters_param(),
                "limit": limit_param(*FRONTIER_LIMIT, "rows"),
                "cursor": CURSOR_PARAM,
                "full": FULL_PARAM,
            }
        ),
        list_frontier,
        keywords=("open problem", "work", "find", "start", "claimable"),
    ),
    Tool(
        "get_node",
        "A node's context bundle (nodes/<id>/CONTEXT.json: statement, deps' signatures, witness, "
        "status, gate-spec reference, attempt log, annex hashes, `literature` and "
        "`literature_proposed` with each record's summary and references inlined and, on a "
        "confirmed status, `disputes`) plus the raw Lean files, live "
        "claim status, `lemmas` (results from other branches this node may use once proved), "
        "its `label` (the statement's short name, with `label_source`: gloss, hole, target or "
        "id) and `claim` (the statement in notation from its gloss, or null), "
        "annexes, explainers and the submissions open on it. `include` names the sections to "
        "answer (all of them when omitted): the prose ones, `attempts` (the context's attempt "
        "records) and `deps` (each dependency's and lemma's statement in the context); "
        "`include: []` answers the Lean files, the context without those (its `omitted` names "
        "what was left out), the claims, lemmas, label and open submissions.",
        params(
            {
                "node_id": ID_PARAM,
                "include": {
                    "type": "array",
                    "items": {"enum": list(INCLUDE_SECTIONS)},
                    "uniqueItems": True,
                    "description": "The sections to answer; every one when omitted, none with [].",
                },
            },
            ("node_id",),
        ),
        get_node,
        keywords=("else", "working", "others", "statement"),
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
        keywords=("pinned", "mathlib", "version", "toolchain"),
    ),
    Tool(
        "get_submission",
        (
            "A submission or proposal by its ULID or pull-request number (padded or "
            "not): the record, the pull request's live state "
            "and, once merged, the attestation it earned or why there is none. "
            "`pull_request.waiting_on` names the one thing it waits for (gate, "
            "step9-review, branch-update, merge, products, or gate-failed, when "
            "`gate_verdict` carries the gate's own diagnostic). `state` is open, merged "
            "or closed. While open, `queue` gives "
            "its `position` (from 1) `of` how many in its target's lane of the merge "
            "actor, and the pull requests `ahead`; a position is an upper bound on the "
            "merges ahead. For a partial, `holes[].became` is the node each hole became once "
            "the products record it: a new child, or a lemma for a hole that restated a node "
            'under another branch. The guide\'s "Precheck and submit" says more.'
        ),
        params({"submission_id": {"type": "string"}}, ("submission_id",)),
        get_submission,
        keywords=("status", "pull request", "pr", "merged", "queue position"),
    ),
    Tool(
        "list_submissions",
        "Every pull request the service opened on the graph that no live read has yet found "
        "merged or closed: id, kind, node, target, pull-request number and URL, pseudonym, in "
        "the merge actor's order. Each entry's `queue` gives its `position` `of` how many in its "
        "own target's lane (the actor runs one lane per target in parallel) and "
        "the `waiting_on` the service last read for it (null: not read, ask get_submission); "
        "the top-level `queue.order` is the queue's pull-request numbers across every lane. "
        "get_submission gives one with its checks and reviews; get_node lists a node's own. "
        "`target_id`, `node_id` and `kind` filter by equality; `kind: words` keeps glosses and "
        "explainers (F22-T8).",
        params(
            {
                "target_id": ID_PARAM,
                "node_id": ID_PARAM,
                "kind": {
                    "type": "string",
                    "description": "words (a gloss or explainer), or one submission kind",
                },
            }
        ),
        list_submissions,
    ),
    Tool(
        "get_schema",
        "A JSON Schema by name: a protocol record's (`postmortem/v1`, `defect-claim/v1`, ...) "
        "or a tool result's (`mcp/<tool>/v1`). A defect claim is written as "
        f"`{requests.DEFECT_SCHEMA}`.",
        params(
            {
                "name": {
                    "type": "string",
                    "description": "A record schema as a record's `schema` field spells it, "
                    "<name>/v<n>, or a tool's result schema, mcp/<tool>/v1.",
                }
            },
            ("name",),
        ),
        get_schema,
    ),
    Tool(
        "get_precheck",
        "A precheck job's state, diagnostics and signed attestation; poll after "
        "precheck_submission until the state is done or error. A pass that carries "
        "`carried_witnesses` did not check the witness files its `unchecked` lists (the "
        "target's pinned gate predates carried witnesses): it is a pass of the skeleton alone; "
        "`carried_proofs` says the same of proof files.",
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
        "Mathlib-free target, with `target_count`; `target_id` adds that target's row (its "
        "mathlib_sha and environment); `full: true` is GET /hosted-checkers.json exactly, "
        "every target's row. Plain path: GET /hosted-checkers.json.",
        params(
            {
                "target_id": {**ID_PARAM, "description": "Also this target's row."},
                "full": FULL_PARAM,
            }
        ),
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
        keywords=("show", "claims", "held"),
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
        keywords=("status", "pull request", "pr", "mine"),
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
        "verdict's diagnostic `code` up here: `code` answers that code's whole row (where, "
        "step, meaning, remedy). Without it, each code and its meaning in pages (`next` is the "
        "`cursor` of the page after); `full: true` is GET /errors.json exactly. Plain path: "
        "GET /errors.json.",
        params(
            {
                "code": {
                    "type": "string",
                    "pattern": "^[a-z0-9_-]{1,64}$",
                    "description": "One code, exactly: its whole row.",
                },
                "prefix": PREFIX_PARAM,
                "limit": limit_param(*CODES_LIMIT, "codes"),
                "cursor": CURSOR_PARAM,
                "full": FULL_PARAM,
            }
        ),
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
        "nothing. A target whose files could not be read is named under `unread`. In pages "
        "(`count` is every row, `next` the `cursor` of the page after). Plain path: "
        "targets/<id>/glosses.json and targets/<id>/target.yaml.",
        params(
            {
                "target_id": {**ID_PARAM, "description": "Only this target's files."},
                "kind": {
                    "type": "string",
                    "description": "Only this kind: statement, witness, relation, definition, "
                    "proof, alternate or partial.",
                },
                "limit": limit_param(*WORDS_LIMIT, "rows"),
                "cursor": CURSOR_PARAM,
            }
        ),
        list_words_needed,
        keywords=("gloss", "words", "need", "missing", "lean files"),
    ),
    # F25-T4: D-28's read table, v3.37.
    Tool(
        "list_registrations",
        "Every registration of a target in a public registry (Palomar), as the products derive "
        "it from the target's registration records: registry, registry_id, version, status "
        "(submitted, registered, revision_required, rejected) and url, with the target_id, in the "
        "index's order and ranked by nothing. `target_id` keeps one target (not-found when the "
        "index has no such target). Read from targets/index.json at main's head; an index "
        "rendered before the field existed lists none. Plain path: targets/index.json.",
        params({"target_id": {**ID_PARAM, "description": "Only this target's registrations."}}),
        list_registrations,
    ),
    # F26-T10: D-28's read table, v3.39 — the formalization review.
    Tool(
        "get_review",
        "A target's formalization review as the record holds it: the words, cases and "
        "concepts, the candidates (author, method, models, origin, the read_others claim), "
        "tests, questions (each `waiting` or not), answers, pairs and open directions, "
        "exhibits, signatures, and the derived `state`. The blind rule (D-9 v3.39): with no "
        "token, or one whose identity authored no candidate on the record, every candidate's "
        "`lean` is null with `lean_withheld: blind`; once your candidate is merged, every Lean "
        "is shown, and each open pair's `template`. 404 review-unknown if none. Read at "
        "main's head.",
        params({"target_id": ID_PARAM, "n": REFUTE_N}, ("target_id",)),
        get_review,
    ),
    Tool(
        "list_review_questions",
        "The questions waiting on a review — those no answer record names — each in words "
        "with its id, what raised it (`raised_by`: a disagreement, concept, mutant, shape or a "
        "signer's send-back, with the record), who is asked (`asked_to`: intent) and its "
        "target_id; in the records' order, ranked by nothing. `target_id` keeps one target "
        "(not-found when the index has no such target); without it, every target's. Read from "
        "targets/<id>/review/questions/ and answers/ at main's head; in pages (`count` is every "
        "question, `next` the `cursor` of the page after). Plain path: "
        "targets/<id>/review/questions/.",
        params(
            {
                "target_id": {**ID_PARAM, "description": "Only this target's questions."},
                "limit": limit_param(*QUESTIONS_LIMIT, "questions"),
                "cursor": CURSOR_PARAM,
            }
        ),
        list_review_questions,
    ),
    Tool(
        "list_open_pairs",
        "The pair directions a review leaves open: each with its two candidates `a` and `b`, "
        "the `direction` (forward: a implies b; backward: b implies a), the last `attempt` "
        "recorded (who, tool, budget_s) or null, its target_id, and `submit_as: pair-proof` — "
        "a proof or refutation of one goes through submit_proof with artifact_type pair-proof "
        "and is credited (F26-R8), with its `template` to fill (helper and proof regions "
        "only) under the blind rule (`template_withheld: blind` until you author a candidate "
        "there); `n` adds the `refutation` template. Latest record per pair, in record order, "
        "ranked by nothing; not a frontier entry. Plain path: targets/<id>/review/pairs/.",
        params(
            {
                "target_id": {**ID_PARAM, "description": "Only this target's open pairs."},
                "n": REFUTE_N,
            }
        ),
        list_open_pairs,
    ),
    Tool(  # F27-T2: D-28's read table, v3.40
        "list_sufficient_sets",
        "A target as an AND-OR graph (D-25 v3.40). `routes`: each merged decomposition "
        "(id `<node>@<k>`), all of whose holes are needed, with its `approach`, each hole's "
        "`label`, status, attempts and refuted route classes, and a `summary` (counts, "
        "`oldest_open_since`). `sets`: statements whose proofs, with the closing proofs of "
        "their `assemblies`, would settle the root, each with its counts and `settles` "
        "(`proves`, or `refutes` for a refutes variant, D-30 v3.46); proving sets first, in "
        "pages (`count`, `next`; `truncated` when any is left out); `routes` holds those the "
        "page's sets use or no set uses; `set_id` answers one set. `include_selector`: the "
        "tree of route choices over the sets, forking first on `side`. `cut: any` adds the "
        "coarser cuts up to a cap (`capped`). `at_proved: follow` also lists what each proved "
        "statement's proof rests on (`proof_routes`). Record order, never ranked. Plain path: "
        "targets/<id>/graph.json + GET /frontier.json.",
        params(
            {
                "target_id": ID_PARAM,
                "cut": {
                    "type": "string",
                    "enum": list(routes.CUTS),
                    "description": "finest (default): every node with a live route expanded; "
                    "any: the coarser cuts too.",
                },
                "at_proved": {
                    "type": "string",
                    "enum": list(routes.AT_PROVED),
                    "description": "stop (default): a proved statement ends the set; follow: "
                    "what its proof rests on is listed beneath it too.",
                },
                "set_id": {
                    "type": "string",
                    "pattern": "^s-[0-9a-f]+$",
                    "description": "Only this set, by its id.",
                },
                "limit": limit_param(*SETS_LIMIT, "sets"),
                "cursor": CURSOR_PARAM,
                "include_selector": {
                    "type": "boolean",
                    "description": "Also answer the selector tree over every set.",
                },
                "detail": {
                    "enum": list(DETAIL),
                    "description": "compact (default): a set without `statements` (its proved "
                    "and open), a route its id, node, live, resolved, holes' node and status and "
                    "counts; full: every fact.",
                },
            },
            ("target_id",),
        ),
        list_sufficient_sets,
        keywords=("prove", "root", "nodes", "settle"),
    ),
)
