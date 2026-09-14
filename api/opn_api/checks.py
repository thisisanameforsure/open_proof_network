"""``POST /check`` — the fast, non-authoritative Lean check (F13-R3 to R10; D-4 v3.14, D-28, D-35).

The service resolves the target's pinned Mathlib to a hosted environment through
``gate/hosted-checkers.yaml``, lints the text for the ways a checker's pass still fails the gate,
inlines the target's ``Defs`` modules the checker cannot import, and forwards the text to AXLE
through the ``Axle`` seam. The answer is AXLE's body verbatim beside the lint and
``authoritative: false``: it never becomes an attestation and nothing reads it back (D-1).

Order of refusals, cheapest first (C7): the body's shape, then the caller's limit, then the
graph (target, node, pin), then the checker. A refusal from the checker itself is
``upstream-unavailable`` naming its status; the network never retries on the caller's behalf.

Every call that passes the body and the limit is logged (R9, Q11): one ``check-log`` record in
the operational store and one structured log line, carrying the content's hash and size and
never its text (C9 v2, Q3). A refusal before that point — a malformed body, a bad token, a spent
limit — is in the access log only, so a flood of bad requests cannot fill the store. A log write
that fails is itself logged and never fails the check (C7).

The concurrency cap is per process (F13-Q8): on Lambda each container serves one request at a
time, so there the effective cap is the function's own concurrency, and this semaphore bounds
the local runner and any multi-threaded host.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import threading
import time
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import auth, frontier, identity, precheck, ratelimit
from opn_api import clock as clockmod
from opn_api.axle import AxleAnswer, AxleError
from opn_api.store import CheckLog
from opn_gate import hosted, layout

if TYPE_CHECKING:
    from opn_api.app import Context

log = logging.getLogger("opn_api.checks")

SERVICE = hosted.SERVICE
FIELDS = frozenset({"target_id", "node_id", "content", "mode"})
MODES = ("check", "verify")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
#: A top-level declaration, after comments are blanked: optional attributes and modifiers, the
#: keyword, and the written name (empty for ``example`` and anonymous instances).
DECLARATION_RE = re.compile(
    r"^(?:@\[[^\]\n]*\]\s*)*(?:(?:private|protected|noncomputable|partial|unsafe)\s+)*"
    r"(?P<kind>theorem|lemma|def|abbrev|instance|axiom|structure|inductive|class|opaque|example)"
    r"\b[ \t]*(?P<name>[^\s:({\[]*)",
    re.M,
)
IMPORT_LINE_RE = re.compile(r"^import\s+\S+[ \t]*$", re.M)
ANSWERED = "answered"


def api_error(status: int, code: str, message: str, **kwargs: Any) -> Exception:
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports the routes that import this

    return ApiError(status, code, message, **kwargs)


def mapping(ctx: Context | None = None) -> hosted.HostedMapping:
    """The shared mapping (``opn_gate.hosted``), or a 503 naming the file: a package without it
    must not look like a pin with no checker (F13-T4)."""
    try:
        return hosted.load()
    except hosted.MappingError as exc:
        raise api_error(503, "hosted-checkers-unreadable", str(exc)) from exc


# --- the body and the caller ---------------------------------------------------------------------


@dataclass(frozen=True)
class CheckRequest:
    target_id: str
    node_id: str | None
    content: str
    mode: str


@dataclass(frozen=True)
class Caller:
    """Who the log names (R9): an identity id, or a keyed hash of the source address (Q4)."""

    kind: str  # "identity" or "address"
    id: str


def parse_body(ctx: Context, fields: dict[str, Any]) -> CheckRequest:
    # A key outside FIELDS was already refused by identity.body_fields (F05-T8, Q10).
    target_id = fields.get("target_id")
    if not isinstance(target_id, str) or not ID_RE.match(target_id):
        raise api_error(400, "target-id-invalid", "target_id must match ^[a-z0-9][a-z0-9-]*$")
    node_id = fields.get("node_id")
    if node_id is not None and (not isinstance(node_id, str) or not ID_RE.match(node_id)):
        raise api_error(400, "node-id-invalid", "node_id must match ^[a-z0-9][a-z0-9-]*$")
    mode = fields.get("mode", "check")
    if mode not in MODES:
        raise api_error(400, "mode-invalid", f"mode must be one of {', '.join(MODES)}")
    if mode == "verify" and node_id is None:
        msg = "verify compares against a node's statement: node_id is required"
        raise api_error(400, "node-id-required", msg)
    content = fields.get("content")
    if not isinstance(content, str) or not content.strip():
        raise api_error(400, "content-missing", "content must be the Lean text to check")
    size = len(content.encode("utf-8"))
    if size > ctx.settings.check_max_bytes:
        msg = f"content is {size} bytes; the limit is {ctx.settings.check_max_bytes}"
        raise api_error(413, "content-too-large", msg)
    return CheckRequest(target_id, node_id, content, mode)


def charge(ctx: Context, request: Request) -> Caller:
    """R8: a presented token is authenticated and charged per identity; otherwise the source
    address is charged, and the log names it only by a keyed hash (Q4)."""
    if auth.bearer(request) is not None:
        who = auth.authenticate(ctx, request)
        request.state.identity_id = who.id  # the access log line names it, as on other routes
        ratelimit.check_check(ctx, who.id)
        return Caller("identity", who.id)
    address = ratelimit.client_address(request)
    ratelimit.check_anonymous_check(ctx, address)
    return Caller("address", auth.token_hash(ctx.settings.token_secret or "", "address:" + address))


# --- the graph -----------------------------------------------------------------------------------


def hosted_for(ctx: Context, target_id: str) -> tuple[str | None, hosted.Hosted | None]:
    """The target's pinned Mathlib and its mapping entry (``None`` when the pin has none)."""
    if target_id not in precheck.graph_doc(ctx):
        raise api_error(404, "target-unknown", f"{target_id} is not a target of this graph")
    spec = json.loads(frontier.committed(ctx, f"targets/{target_id}/gate-spec.json"))
    sha = spec.get("mathlib_sha")
    return sha, hosted.lookup(mapping(), sha if isinstance(sha, str) else None)


def statement_of(ctx: Context, target_id: str, node_id: str) -> layout.Statement | None:
    facts = precheck.node_facts(ctx, node_id)
    if facts["target_id"] != target_id:
        msg = f"{node_id} belongs to {facts['target_id']}, not {target_id}"
        raise api_error(400, "node-target-mismatch", msg)
    raw = frontier.committed(ctx, f"targets/{target_id}/nodes/{node_id}/Statement.lean")
    parsed = layout.parse_statement(raw.decode("utf-8"))
    return parsed if isinstance(parsed, layout.Statement) else None


def defs_modules(text: str) -> list[str]:
    return [m for m in layout.imports_of(text) if layout.module_origin(m)[0] == "defs"]


def inline_defs(ctx: Context, target_id: str, statement: layout.Statement) -> list[tuple[str, str]]:
    """R5: the statement's ``Defs`` modules and everything they import, dependencies first, as
    (module, source without its import lines)."""
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()

    def visit(module: str, trail: tuple[str, ...]) -> None:
        if module in seen:
            return
        if module in trail:
            msg = f"the definitions import each other: {' -> '.join((*trail, module))}"
            raise api_error(409, "defs-cycle", msg)
        stem = module.partition(".")[2]
        source = frontier.committed(ctx, f"targets/{target_id}/defs/{stem}.lean").decode("utf-8")
        for dep in defs_modules(source):
            visit(dep, (*trail, module))
        seen.add(module)
        ordered.append((module, IMPORT_LINE_RE.sub("", source).strip("\n")))

    for module in defs_modules(statement.text):
        visit(module, ())
    return ordered


def forwarded_text(content: str, defs: list[tuple[str, str]]) -> str:
    """The content with its ``import Defs.*`` lines removed and the definitions' sources placed
    after its remaining header, where a module's own declarations would begin."""
    if not defs:
        return content
    lines = [
        line
        for line in content.splitlines(keepends=True)
        if not (line.startswith("import ") and layout.module_origin(line.split()[1])[0] == "defs")
    ]
    last_import = max((i for i, line in enumerate(lines) if line.startswith("import ")), default=-1)
    block = "".join(
        f"\n-- inlined by the network from {module} (F13-R5)\n{src}\n" for module, src in defs
    )
    return "".join(lines[: last_import + 1]) + block + "\n" + "".join(lines[last_import + 1 :])


# --- the lint ------------------------------------------------------------------------------------


def lint(content: str, statement: layout.Statement | None) -> list[dict[str, Any]]:
    """R4: where the gate would refuse what the checker accepts. Warnings only."""
    warnings: list[dict[str, Any]] = []
    if statement is not None:
        expected, got = layout.imports_of(statement.text), layout.imports_of(content)
        if expected != got:
            warnings.append(
                {
                    "code": "imports-differ",
                    "message": "the gate requires the statement's imports exactly (F00-R19); "
                    "the checker substitutes its own header and would not notice",
                    "expected": expected,
                    "got": got,
                }
            )
        written = _written_name(statement.text)
        extra = [
            f"{m.group('kind')} {m.group('name')}".strip()
            for m in DECLARATION_RE.finditer(layout.strip_comments(content))
            if not (m.group("kind") in ("theorem", "lemma") and m.group("name") == written)
        ]
        if extra:
            warnings.append(
                {
                    "code": "helper-declarations",
                    "message": "a proof is the statement with its sorry replaced (F00-R19); "
                    "move helpers inside the proof as `have`, or submit a skeleton",
                    "declarations": extra,
                }
            )
    if layout.mentions_sorry(content):
        warnings.append(
            {
                "code": "sorry-present",
                "message": "the text still uses sorry; a proof with sorry fails the axiom step, "
                "and a skeleton is submitted as a partial",
            }
        )
    return warnings


def _written_name(statement_text: str) -> str | None:
    for m in DECLARATION_RE.finditer(layout.strip_comments(statement_text)):
        if m.group("kind") in ("theorem", "lemma"):
            return m.group("name")
    return None


# --- the checker ---------------------------------------------------------------------------------

_SLOTS_LOCK = threading.Lock()


def slots(ctx: Context) -> threading.BoundedSemaphore:
    """This application's in-flight cap (R8, Q8), created on first use and kept on its Context.

    Not in a table keyed by ``id(ctx)``: CPython reuses a collected object's address, so a new
    application could inherit an old one's semaphore with another cap — which is how the first
    version failed once in a full suite run and never alone (evidence task-4.txt)."""
    with _SLOTS_LOCK:
        if ctx.check_slots is None:
            ctx.check_slots = threading.BoundedSemaphore(ctx.settings.check_concurrency)
        return ctx.check_slots


def call_checker(
    ctx: Context, req: CheckRequest, text: str, environment: str, statement: layout.Statement | None
) -> AxleAnswer:
    gate = slots(ctx)
    if not gate.acquire(timeout=ctx.settings.check_timeout_s):
        msg = f"{ctx.settings.check_concurrency} checks are already in flight; retry shortly"
        raise api_error(503, "checker-busy", msg, headers={"Retry-After": "5"})
    try:
        if req.mode == "verify":
            assert statement is not None  # parse_body refuses verify without a node
            return ctx.axle.verify_proof(
                text,
                formal_statement=statement.text,
                environment=environment,
                timeout_s=ctx.settings.check_timeout_s,
            )
        return ctx.axle.check(text, environment=environment, timeout_s=ctx.settings.check_timeout_s)
    finally:
        gate.release()


# --- the log -------------------------------------------------------------------------------------


def error_count(body: dict[str, Any]) -> int | None:
    """Lean's errors plus the tool's, when the body has the shape AXLE answers with."""
    total, seen = 0, False
    for key in ("lean_messages", "tool_messages"):
        block = body.get(key)
        if isinstance(block, dict) and isinstance(block.get("errors"), list):
            total += len(block["errors"])
            seen = True
    return total if seen else None


def write_log(  # noqa: PLR0913 — one argument per fact the record keeps
    ctx: Context,
    req: CheckRequest,
    caller: Caller,
    *,
    outcome: str,
    started: float,
    environment: str | None = None,
    lint_codes: list[str] | None = None,
    answer: AxleAnswer | None = None,
    upstream_status: int | None = None,
) -> str | None:
    """R9: one record and one log line; the record's id, or ``None`` when the store refused it."""
    now = ctx.clock.now()
    body = answer.body if answer is not None else {}
    okay = body.get("okay")
    record = CheckLog(
        id=identity.new_ulid(now),
        created=clockmod.render(now),
        caller_kind=caller.kind,
        caller=caller.id,
        target_id=req.target_id,
        node_id=req.node_id,
        mode=req.mode,
        environment=environment,
        content_sha256=hashlib.sha256(req.content.encode("utf-8")).hexdigest(),
        content_bytes=len(req.content.encode("utf-8")),
        outcome=outcome,
        okay=okay if isinstance(okay, bool) else None,
        error_count=error_count(body) if answer is not None else None,
        lint=list(lint_codes or []),
        axle_request_id=answer.request_id if answer is not None else None,
        upstream_status=upstream_status,
        latency_ms=int((time.monotonic() - started) * 1000),
    )
    log.info(
        "check id=%s caller=%s:%s target=%s node=%s mode=%s env=%s outcome=%s okay=%s errors=%s "
        "bytes=%d ms=%d",
        record.id,
        record.caller_kind,
        record.caller[:12],
        record.target_id,
        record.node_id or "-",
        record.mode,
        record.environment or "-",
        record.outcome,
        record.okay,
        record.error_count,
        record.content_bytes,
        record.latency_ms,
    )
    try:
        ctx.store.put_check(record)
    except Exception as exc:  # C7: a lost log line never costs the caller a check
        log.error("check id=%s was not stored: %s", record.id, type(exc).__name__)
        return None
    return record.id


# --- the routes ----------------------------------------------------------------------------------


async def post_check(ctx: Context, request: Request) -> Response:
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports the routes that import this

    fields, _ = await identity.body_fields(request, FIELDS)
    req = parse_body(ctx, fields)
    caller = charge(ctx, request)
    started = time.monotonic()
    environment: str | None = None
    try:
        sha, hosted = hosted_for(ctx, req.target_id)
        if hosted is None or hosted.environment is None:
            msg = (
                f"{req.target_id} pins Mathlib {sha}, which no hosted checker serves"
                if sha
                else f"{req.target_id} is Mathlib-free; the hosted checker serves Mathlib pins"
            )
            raise api_error(422, "no-hosted-environment", msg, details={"mathlib_sha": sha})
        environment = hosted.environment
        statement = statement_of(ctx, req.target_id, req.node_id) if req.node_id else None
        if req.mode == "verify" and statement is None:
            msg = f"{req.node_id}'s Statement.lean has no single sorry-bodied theorem to verify"
            raise api_error(409, "statement-unparsable", msg)
        defs = inline_defs(ctx, req.target_id, statement) if statement is not None else []
        text = forwarded_text(req.content, defs)
        warnings = lint(req.content, statement)
        try:
            answer = await asyncio.to_thread(call_checker, ctx, req, text, environment, statement)
        except AxleError as exc:
            raise api_error(
                502, "upstream-unavailable", str(exc), details={"upstream_status": exc.status}
            ) from exc
    except ApiError as refusal:
        upstream = (refusal.details or {}).get("upstream_status")
        log_id = write_log(
            ctx,
            req,
            caller,
            outcome=refusal.code,
            started=started,
            environment=environment,
            upstream_status=upstream if isinstance(upstream, int) else None,
        )
        refusal.details = {**(refusal.details or {}), "log_id": log_id}
        raise
    log_id = write_log(
        ctx,
        req,
        caller,
        outcome=ANSWERED,
        started=started,
        environment=environment,
        lint_codes=[w["code"] for w in warnings],
        answer=answer,
    )
    return JSONResponse(
        {
            "authoritative": False,
            "service": SERVICE,
            "environment": hosted.environment,
            "exact": hosted.exact,
            "note": hosted.note,
            "mode": req.mode,
            "lint": warnings,
            "inlined_defs": [module for module, _ in defs],
            "result": answer.body,
            "log_id": log_id,
        }
    )


async def get_check(ctx: Context, request: Request) -> Response:
    """R10: a record is readable by the identity that made the call and by nobody else; an
    anonymous call's record names no identity, so no token reads it."""
    record = ctx.store.get_check(str(request.path_params["check_id"]))
    who = str(request.state.identity_id)
    if record is None or record.caller_kind != "identity" or record.caller != who:
        raise api_error(404, "check-unknown", "no such check for this identity")
    return JSONResponse(asdict(record))


async def get_hosted_checkers(ctx: Context, request: Request) -> Response:
    """R11 (Q12): the mapping as data, and each listed target's pin and environment, so an agent
    learns before its first check which targets have a hosted checker and how exact it is. A read
    of network configuration, not of the graph; ``info.json`` stays the graph's product."""
    known = mapping()
    targets: dict[str, dict[str, Any]] = {}
    for entry in precheck.index_doc(ctx).get("targets", []):
        sha = entry.get("mathlib_sha")
        found = hosted.lookup(known, sha if isinstance(sha, str) else None)
        targets[str(entry["target_id"])] = {
            "mathlib_sha": sha,
            "environment": found.environment if found is not None else None,
            "exact": found.exact if found is not None else None,
        }
    return JSONResponse(
        {
            "schema": hosted.MAPPING_SCHEMA,
            "service": SERVICE,
            "endpoint": "POST /check",
            "authoritative": False,
            "pins": {sha: asdict(entry) for sha, entry in sorted(known.pins.items())},
            "core": asdict(known.core) if known.core is not None else None,
            "targets": dict(sorted(targets.items())),
        }
    )
