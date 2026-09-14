"""``POST /check`` — the fast, non-authoritative Lean check (F13-R3 to R8; D-4 v3.14, D-28, D-35).

The service resolves the target's pinned Mathlib to a hosted environment through
``gate/hosted-checkers.yaml``, lints the text for the ways a checker's pass still fails the gate,
inlines the target's ``Defs`` modules the checker cannot import, and forwards the text to AXLE
through the ``Axle`` seam. The answer is AXLE's body verbatim beside the lint and
``authoritative: false``: it never becomes an attestation and nothing reads it back (D-1).

Order of refusals, cheapest first (C7): the body's shape, then the caller's limit, then the
graph (target, node, pin), then the checker. A refusal from the checker itself is
``upstream-unavailable`` naming its status; the network never retries on the caller's behalf.

The concurrency cap is per process (F13-Q8): on Lambda each container serves one request at a
time, so there the effective cap is the function's own concurrency, and this semaphore bounds
the local runner and any multi-threaded host.
"""

from __future__ import annotations

import asyncio
import json
import re
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import auth, frontier, identity, precheck, ratelimit
from opn_api.axle import AxleAnswer, AxleError
from opn_gate import layout, schemas

if TYPE_CHECKING:
    from opn_api.app import Context

#: The mapping sits beside the gate's schemas in the repository (``gate/``) and at the package
#: root on Lambda, where the deploy copies both (F13-T4) — the rule ``opn_gate.schemas`` uses.
MAPPING_PATH = schemas.SCHEMAS_DIR.parent / "hosted-checkers.yaml"
MAPPING_SCHEMA = "hosted-checkers/v1"
SERVICE = "axle"
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


@dataclass(frozen=True)
class Hosted:
    """One pin's entry in ``hosted-checkers.yaml`` (F13-R2)."""

    mathlib_tag: str
    environment: str | None
    exact: bool
    note: str | None


def api_error(status: int, code: str, message: str, **kwargs: Any) -> Exception:
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports the routes that import this

    return ApiError(status, code, message, **kwargs)


@lru_cache(maxsize=4)
def load_mapping(path: Path = MAPPING_PATH) -> dict[str, Hosted]:
    """The pin -> environment mapping, read once per process. A missing or malformed file is a
    503 naming it: a package without the mapping must not look like a pin with no checker."""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise api_error(503, "hosted-checkers-unreadable", f"{path.name}: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != MAPPING_SCHEMA:
        msg = f"{path.name} is not {MAPPING_SCHEMA}"
        raise api_error(503, "hosted-checkers-unreadable", msg)
    if doc.get("service") != SERVICE:
        msg = f"{path.name} names service {doc.get('service')!r}; only {SERVICE!r} is known (Q5)"
        raise api_error(503, "hosted-checkers-unreadable", msg)
    out: dict[str, Hosted] = {}
    for sha, entry in (doc.get("pins") or {}).items():
        out[str(sha)] = Hosted(
            mathlib_tag=str(entry.get("mathlib_tag")),
            environment=entry.get("environment"),
            exact=bool(entry.get("exact")),
            note=entry.get("note"),
        )
    return out


# --- the body ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckRequest:
    target_id: str
    node_id: str | None
    content: str
    mode: str


def parse_body(ctx: Context, fields: dict[str, Any]) -> CheckRequest:
    unknown = sorted(set(fields) - FIELDS)
    if unknown:
        allowed = ", ".join(sorted(FIELDS))
        msg = f"unknown field(s): {', '.join(unknown)}; POST /check takes {allowed}"
        raise api_error(400, "unknown-field", msg)
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


def charge(ctx: Context, request: Request) -> str | None:
    """R8: a presented token is authenticated and charged per identity; otherwise the source
    address is charged. Answers the identity id, or ``None`` for an anonymous caller."""
    if auth.bearer(request) is not None:
        who = auth.authenticate(ctx, request)
        ratelimit.check_check(ctx, who.id)
        return who.id
    ratelimit.check_anonymous_check(ctx, ratelimit.client_address(request))
    return None


# --- the graph -----------------------------------------------------------------------------------


def hosted_for(ctx: Context, target_id: str) -> tuple[str | None, Hosted | None]:
    """The target's pinned Mathlib and its mapping entry (``None`` when the pin has none)."""
    if target_id not in precheck.graph_doc(ctx):
        raise api_error(404, "target-unknown", f"{target_id} is not a target of this graph")
    spec = json.loads(frontier.committed(ctx, f"targets/{target_id}/gate-spec.json"))
    sha = spec.get("mathlib_sha")
    return sha, load_mapping().get(sha) if isinstance(sha, str) else None


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

_SLOTS: dict[int, threading.BoundedSemaphore] = {}
_SLOTS_LOCK = threading.Lock()


def slots(ctx: Context) -> threading.BoundedSemaphore:
    """This application's in-flight cap (R8, Q8), created on first use."""
    with _SLOTS_LOCK:
        cap = ctx.settings.check_concurrency
        return _SLOTS.setdefault(id(ctx), threading.BoundedSemaphore(cap))


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


async def post_check(ctx: Context, request: Request) -> Response:
    fields, _ = await identity.body_fields(request)
    req = parse_body(ctx, fields)
    charge(ctx, request)
    sha, hosted = hosted_for(ctx, req.target_id)
    if hosted is None or hosted.environment is None:
        msg = (
            f"{req.target_id} pins Mathlib {sha}, which no hosted checker serves"
            if sha
            else f"{req.target_id} is a Mathlib-free graph; the hosted checker serves Mathlib pins"
        )
        raise api_error(422, "no-hosted-environment", msg, details={"mathlib_sha": sha})
    statement = statement_of(ctx, req.target_id, req.node_id) if req.node_id else None
    if req.mode == "verify" and statement is None:
        msg = f"{req.node_id}'s Statement.lean has no single sorry-bodied theorem to verify against"
        raise api_error(409, "statement-unparsable", msg)
    defs = inline_defs(ctx, req.target_id, statement) if statement is not None else []
    text = forwarded_text(req.content, defs)
    try:
        answer = await asyncio.to_thread(
            call_checker, ctx, req, text, hosted.environment, statement
        )
    except AxleError as exc:
        raise api_error(
            502, "upstream-unavailable", str(exc), details={"upstream_status": exc.status}
        ) from exc
    return JSONResponse(
        {
            "authoritative": False,
            "service": SERVICE,
            "environment": hosted.environment,
            "exact": hosted.exact,
            "note": hosted.note,
            "mode": req.mode,
            "lint": lint(req.content, statement),
            "inlined_defs": [module for module, _ in defs],
            "result": answer.body,
            "log_id": None,
        }
    )
