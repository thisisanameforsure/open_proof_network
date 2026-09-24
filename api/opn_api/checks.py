"""``POST /check`` — the fast, non-authoritative Lean check (F13-R3 to R10; D-4 v3.14, D-28, D-35).

The service resolves the target's pinned Mathlib to a hosted environment through
``gate/hosted-checkers.yaml``, lints the text for the ways a checker's pass still fails the gate,
inlines the target's ``Defs`` modules the checker cannot import, and forwards the text to AXLE
through the ``Axle`` seam. The answer is AXLE's body verbatim beside the lint and
``authoritative: false`` (bar one warning on a gate-generated name, listed in
``dropped_warnings``, F13-T18): it never becomes an attestation and nothing reads it back (D-1).

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
from opn_gate import hosted, layout, scaffold, schemas

if TYPE_CHECKING:
    from opn_api.app import Context

log = logging.getLogger("opn_api.checks")

SERVICE = hosted.SERVICE
FIELDS = frozenset({"target_id", "node_id", "content", "mode", "statement", "deps"})
MODES = ("check", "verify", "witness", "hazards")
#: F13-T14: the modes that read the node's own statement, so cannot do without a node.
NODE_MODES = ("verify", "witness", "hazards")
#: F13-T16, T20: the modes that may read a statement that is not a node yet, sent as its text.
STATEMENT_MODES = ("witness", "hazards")
#: The prefix of the one info line the witness program logs; what follows it is JSON.
WITNESS_TAG = "OPN-WITNESS"
#: Step 7's own metaprogram (F01-R3), shipped beside the schemas as ``hosted-checkers.yaml`` is.
#: Read, never restated: the preview and the gate cannot disagree about a type they compute with
#: one file.
WITNESS_SOURCE = schemas.SCHEMAS_DIR.parent / "lean" / "OpnGate" / "WitnessType.lean"
#: F13-T20: the prefix of the one info line the hazard program logs; what follows it is JSON.
HAZARDS_TAG = "OPN-HAZARDS"
#: Step 6's checkers (F02-R1, R2) and the executable that names them, shipped beside the schemas
#: as ``WitnessType.lean`` is. Read, never restated: the checker files are inlined as they are, and
#: the registry is ``HazardsMain.lean``'s own.
LEAN_DIR = schemas.SCHEMAS_DIR.parent / "lean"
HAZARDS_MAIN = LEAN_DIR / "OpnGate" / "HazardsMain.lean"
HAZARDS_PREFIX = "OpnGate.Hazards"
REGISTRY_RE = re.compile(r"^def registry : Array Checker :=\s*(?P<list>#\[[^\]]*\])", re.M)
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
#: How the inlined Context of a statement that is not a node yet is labelled (F13-T16).
PROPOSED_CONTEXT = "Context (generated from the declared deps)"
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
    #: F13-T16: in witness mode, a statement that is not a node yet — its text, as a proposal
    #: would carry it — and the deps that proposal would declare (unchecked until the graph is).
    statement: str | None = None
    deps: Any = None


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
    statement = proposed_statement_field(ctx, fields, mode, node_id)
    if mode in NODE_MODES and node_id is None and statement is None:
        msg = f"{mode} reads a node's statement: node_id is required" + (
            ", or the statement's text as statement (F13-T16)" if mode in STATEMENT_MODES else ""
        )
        raise api_error(400, "node-id-required", msg)
    content = fields.get("content")
    if mode == "hazards":
        # F13-T20: the checkers read a statement; there is nothing else for content to be.
        if content not in (None, ""):
            msg = "mode hazards reads the statement (node_id or statement); send no content"
            raise api_error(400, "content-not-used", msg)
        content = ""
    if mode == "witness" and content is None:
        content = ""  # F13-T14: no witness yet; the answer is the expected type alone
    if not isinstance(content, str) or (mode not in STATEMENT_MODES and not content.strip()):
        raise api_error(400, "content-missing", "content must be the Lean text to check")
    size = len(content.encode("utf-8"))
    if size > ctx.settings.check_max_bytes:
        raise too_large(ctx, "content", size)
    return CheckRequest(target_id, node_id, content, mode, statement, fields.get("deps"))


def too_large(ctx: Context, what: str, size: int) -> Exception:
    """F13-T19: the size refusal says what to do, since a text this long rarely fits the gate
    either (testers 2026-09-24: a 657 kB case tree). Splitting it into lemmas is refused, and a
    ``set_option`` inside the proof does not raise Lean's heartbeat budget."""
    limit = ctx.settings.check_max_bytes
    return api_error(
        413,
        "content-too-large",
        f"{what} is {size} bytes; the limit is {limit}. A proof this long rarely fits the gate "
        "either: Lean's heartbeat budget (maxHeartbeats, 200000 by default) counts per "
        "declaration, a set_option inside the proof does not lift it, and a proof may declare "
        "nothing but the statement's theorem, so helper lemmas are refused (F00-R19). Make the "
        "proof cheaper (one `have` per case with `exact` at the leaves, named lemmas instead of "
        "search tactics), or decompose the node with a skeleton",
        details={"bytes": size, "limit_bytes": limit},
    )


def proposed_statement_field(
    ctx: Context, fields: dict[str, Any], mode: str, node_id: str | None
) -> str | None:
    """F13-T16: ``statement`` and ``deps``, which let witness mode (and hazards mode, F13-T20) read
    a statement that is not a node yet (a variant's or a crux's, before its proposal merges). Only
    there: a node's statement is its own, and the other modes check content against nothing or
    against a node."""
    statement, deps = fields.get("statement"), fields.get("deps")
    if statement is None:
        if deps is not None:
            msg = "deps are the dependencies a statement's proposal would declare; send statement"
            raise api_error(400, "deps-without-statement", msg)
        return None
    if mode not in STATEMENT_MODES:
        msg = (
            "statement is read in modes witness and hazards only; "
            "check a statement's text as content"
        )
        raise api_error(400, "statement-not-used", msg)
    if node_id is not None:
        msg = "a node's statement is its own: send node_id or statement, not both"
        raise api_error(400, "statement-with-node", msg)
    if not isinstance(statement, str):
        raise api_error(400, "statement-invalid", "statement must be the text of a Lean file")
    size = len(statement.encode("utf-8"))
    if size > ctx.settings.check_max_bytes:
        raise too_large(ctx, "statement", size)
    parsed = layout.parse_statement(statement)
    if not isinstance(parsed, layout.Statement):
        raise api_error(400, "statement-invalid", parsed.message)
    return statement


def without_node_imports(text: str) -> str:
    """A proposed statement without its ``import Nodes.…`` lines: the only one a statement may
    carry is its own Context, which the network generates and inlines itself (F13-T16), and the
    checker has no such module to import."""
    return "".join(
        line
        for line in text.splitlines(keepends=True)
        if not (line.startswith("import ") and layout.module_origin(line.split()[1])[0] == "node")
    )


def proposed_context(ctx: Context, target_id: str, raw_deps: Any) -> str | None:
    """The ``Context.lean`` a proposal declaring ``raw_deps`` would carry, built the way the
    proposal routes build it (``scaffold.context_from`` over the deps' committed statements), or
    ``None`` when it declares none."""
    from opn_api import proposals  # noqa: PLC0415 — proposals imports this module

    deps, statements = proposals.dep_statements(ctx, target_id, raw_deps)
    return scaffold.context_from(deps, statements) if deps else None


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


def own_context_module(node_id: str | None, *texts: str) -> str | None:
    """The node's own ``Context`` module, when one of the texts imports it (F13-T12). Only its
    own: a node may import no other node's module (F00's import rule), and the fast check does
    not widen that by fetching a sibling's."""
    if node_id is None:
        return None
    own = layout.node_module(node_id, "Context")
    return own if any(layout.imports_own_context(node_id, text) for text in texts) else None


def inline_defs(  # noqa: PLR0913 — the node's Context may be given rather than fetched
    ctx: Context,
    target_id: str,
    statement: layout.Statement | None,
    content: str,
    node_id: str | None = None,
    *,
    context: str | None = None,
) -> list[tuple[str, str]]:
    """R5: the statement's ``Defs`` modules, then the content's own (F13-T11: a proposer's
    statement is not a node yet, so its header is the only thing that names them), and everything
    they import, dependencies first, as (module, source without its import lines). A module the
    content names and the target does not have is refused by name rather than forwarded to fail
    as an unknown identifier.

    ``context`` is the node's own ``Context.lean`` when it is not on the graph yet (F13-T16: a
    proposal's, generated from the deps it declares); it is inlined in place of a fetched one."""
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports the routes that import this

    named = defs_modules(statement.text) if statement is not None else []
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()

    def visit(module: str, trail: tuple[str, ...]) -> None:
        if module in seen:
            return
        if module in trail:
            msg = f"the definitions import each other: {' -> '.join((*trail, module))}"
            raise api_error(409, "defs-cycle", msg)
        stem = module.partition(".")[2]
        try:
            raw = frontier.committed(ctx, f"targets/{target_id}/defs/{stem}.lean")
        except ApiError as exc:
            if module in named or trail:
                raise  # the graph's own module: an outage, not the caller's mistake
            msg = f"{target_id} has no {module} (defs/{stem}.lean could not be read)"
            raise api_error(400, "defs-unknown", msg) from exc
        source = raw.decode("utf-8")
        for dep in defs_modules(source):
            visit(dep, (*trail, module))
        seen.add(module)
        ordered.append((module, IMPORT_LINE_RE.sub("", source).strip("\n")))

    for module in (*named, *defs_modules(content)):
        visit(module, ())
    # F13-T12: the node's own Context, last, after the Defs it imports. It is where a declared
    # dependency's theorem lives (and, after a skeleton merges, a node's holes), so without it a
    # proof that uses one reads "Unknown identifier" on a checker that would otherwise pass it.
    own = own_context_module(node_id, content, statement.text if statement is not None else "")
    source: str | None = None
    if context is not None:
        own = layout.node_module(node_id, "Context") if node_id else PROPOSED_CONTEXT
        source = context
    elif own is not None and node_id is not None:
        raw = frontier.committed(ctx, f"targets/{target_id}/nodes/{node_id}/Context.lean")
        source = raw.decode("utf-8")
    if own is not None and source is not None:
        for dep in defs_modules(source):
            visit(dep, (own,))
        ordered.append((own, IMPORT_LINE_RE.sub("", source).strip("\n")))
    return ordered


def forwarded_text(content: str, defs: list[tuple[str, str]]) -> str:
    """The content with its ``import Defs.*`` lines removed and the definitions' sources placed
    after its remaining header, where a module's own declarations would begin."""
    if not defs:
        return content
    inlined = {module for module, _ in defs}
    lines = [
        line
        for line in content.splitlines(keepends=True)
        if not (
            line.startswith("import ")
            and (layout.module_origin(line.split()[1])[0] == "defs" or line.split()[1] in inlined)
        )
    ]
    last_import = max((i for i, line in enumerate(lines) if line.startswith("import ")), default=-1)
    block = "".join(
        f"\n-- inlined by the network from {module} (F13-R5)\n{src}\n" for module, src in defs
    )
    return "".join(lines[: last_import + 1]) + block + "\n" + "".join(lines[last_import + 1 :])


# --- the lint ------------------------------------------------------------------------------------


def lint(
    content: str, statement: layout.Statement | None, node_id: str | None = None
) -> list[dict[str, Any]]:
    """R4: where the gate would refuse what the checker accepts. Warnings only."""
    warnings: list[dict[str, Any]] = []
    if statement is not None:
        expected, got = layout.imports_of(statement.text), layout.imports_of(content)
        # F00-T10: the one header the gate takes besides the statement's own — its imports with
        # the node's own Context placed where ``layout.with_own_context`` puts it.
        allowed = (
            layout.imports_of(layout.with_own_context(statement.text, node_id))
            if node_id is not None
            else expected
        )
        if got not in (expected, allowed):
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


#: Mathlib's style linter for a ``__`` in a declaration's name (F13-T18), and the name it quotes.
NAME_CHECK = "linter.style.nameCheck"
NAME_CHECK_RE = re.compile(r"The declaration '(?P<name>[^']+)' contains '__'")


def without_generated_name_warning(
    body: dict[str, Any], statement: layout.Statement | None, node_id: str | None
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """F13-T18 (D6): the checker's body with Mathlib's naming-linter warning dropped when, and
    only when, the name it flags is the node's own gate-generated declaration: its id with ``-``
    made ``_``, declared by its statement, as ``postmerge.child_statement`` writes every hole. A
    contributor cannot rename that theorem, so the warning was noise on every check of a hole.
    Every other warning passes through verbatim. A copy: the body the log reads is the
    checker's (R9)."""
    if node_id is None or statement is None:
        return body, []
    generated = node_id.replace("-", "_")
    if statement.decl_name != generated:
        return body, []
    messages = body.get("lean_messages")
    warnings = messages.get("warnings") if isinstance(messages, dict) else None
    if not isinstance(warnings, list):
        return body, []
    kept: list[Any] = []
    dropped: list[dict[str, str]] = []
    for w in warnings:
        m = NAME_CHECK_RE.search(w) if isinstance(w, str) and NAME_CHECK in w else None
        if m is not None and m.group("name") == generated:
            dropped.append({"linter": NAME_CHECK, "declaration": generated})
        else:
            kept.append(w)
    if not dropped:
        return body, []
    assert isinstance(messages, dict)
    return {**body, "lean_messages": {**messages, "warnings": kept}}, dropped


def superseded_warning(ctx: Context, node_id: str | None) -> list[dict[str, Any]]:
    """T15: a check against a node that has been replaced says so and names the replacement, as
    a claim on it does (F05-T11). A warning, not a refusal: checking a superseded statement is
    how a defect in it is shown. A graph that cannot say is no reason to fail a check (C7)."""
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports the routes that import this

    if node_id is None:
        return []
    try:
        facts = precheck.node_facts(ctx, node_id)
        if facts.get("status") != "superseded":
            return []
        replacement = precheck.standing(ctx, node_id, facts)["replacement"]
    except ApiError:
        return []
    successor = f" by {replacement}; work continues there" if replacement else ""
    return [
        {
            "code": "node-superseded",
            "message": f"{node_id} has been superseded{successor} (D-8). Nothing can be "
            "submitted against it; its statement is kept for its history",
            "replacement": replacement,
        }
    ]


# --- the witness preview (F13-T14) ---------------------------------------------------------------


def witness_program(decl_name: str, has_witness: bool) -> str:
    """The gate's ``WitnessType.lean`` and the few lines that ask it one question: the type step
    7 will hold a witness of ``decl_name`` to, the given witness's type, and whether they are the
    same. Printed under the options the hole writer prints under (F07-R19, T30), so the text can
    be pasted back as a witness's type."""
    try:
        source = WITNESS_SOURCE.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"the witness metaprogram is not in this package: {WITNESS_SOURCE.name}"
        raise api_error(503, "witness-program-unreadable", msg) from exc
    body = IMPORT_LINE_RE.sub("", source).strip("\n")
    given = (
        "  let w ← getConstInfo `witness\n"
        "  let same ← withReducible (isDefEq expected w.type) <||> isDefEq expected w.type\n"
        "  let given := Json.str (← pp w.type)\n"
        "  let verdict := Json.bool same\n"
        if has_witness
        else "  let given := Json.null\n  let verdict := Json.null\n"
    )
    return (
        "\n-- the network's witness preview (F13-T14): gate/lean/OpnGate/WitnessType.lean\n"
        f"{body}\n\n"
        "open Lean Meta in\n"
        "run_meta do\n"
        f"  let s ← getConstInfo `{decl_name}\n"
        "  let expected ← OpnGate.expectedWitnessType s.type\n"
        "  let pp (e : Expr) : MetaM String :=\n"
        "    withOptions (fun o => ((o.setBool `pp.coercions.types true).setBool\n"
        "        `pp.numericTypes true).setBool `pp.funBinderTypes true) do\n"
        "      return toString (← ppExpr e)\n"
        f"{given}"
        "  let wanted ← pp expected\n"
        '  let answer := Json.mkObj [("expected", Json.str wanted), ("given", given), '
        '("matches", verdict)]\n'
        f'  logInfo m!"{WITNESS_TAG} {{Json.compress answer}}"\n'
    )


def witness_text(formal: str, content: str, decl_name: str) -> str:
    """What the checker is sent in witness mode: the node's statement under its own header (the
    definitions already inlined), ``import Lean`` for the metaprogram, the witness without its
    import lines, then the program."""
    lines = formal.splitlines(keepends=True)
    imports = [i for i, line in enumerate(lines) if line.startswith("import ")]
    at = imports[-1] + 1 if imports else 0
    header = "" if "Lean" in layout.imports_of(formal) else "import Lean\n"
    witness = IMPORT_LINE_RE.sub("", content).strip()
    return (
        "".join(lines[:at])
        + header
        + "".join(lines[at:])
        + (f"\n{witness}\n" if witness else "")
        + witness_program(decl_name, bool(witness))
    )


def witness_verdict(body: dict[str, Any]) -> dict[str, Any] | None:
    """The program's one line, read back out of the checker's info messages; ``None`` when it
    never ran (the witness or the statement did not elaborate). The checker's text is untrusted
    data: only the three keys are read, each held to its type."""
    messages = body.get("lean_messages")
    infos = messages.get("infos") if isinstance(messages, dict) else None
    for info in infos if isinstance(infos, list) else ():
        _, tag, rest = str(info).partition(WITNESS_TAG + " ")
        if not tag:
            continue
        try:
            doc = json.loads(rest.strip())
        except ValueError:
            continue
        if isinstance(doc, dict) and isinstance(doc.get("expected"), str):
            given, same = doc.get("given"), doc.get("matches")
            return {
                "expected": doc["expected"],
                "given": given if isinstance(given, str) else None,
                "matches": same if isinstance(same, bool) else None,
            }
    return None


# --- the hazard checkers (F13-T20) ---------------------------------------------------------------


def _lean_source(module: str) -> str:
    return (LEAN_DIR / (module.replace(".", "/") + ".lean")).read_text(encoding="utf-8")


def hazard_sources() -> tuple[list[tuple[str, str]], str]:
    """Step 6's checker files as ``opn-hazards`` is built from them, dependencies first, each
    without its import lines (they import only ``Lean``, F02), and ``HazardsMain.lean``'s
    registry of checkers, as its text. Walked from ``HazardsMain.lean``'s own imports, so a
    checker added to the gate is inlined here without an edit."""
    try:
        main = HAZARDS_MAIN.read_text(encoding="utf-8")
        ordered: list[tuple[str, str]] = []
        seen: set[str] = set()

        def visit(module: str) -> None:
            if module in seen:
                return
            seen.add(module)
            source = _lean_source(module)
            for dep in layout.imports_of(source):
                if dep == HAZARDS_PREFIX or dep.startswith(HAZARDS_PREFIX + "."):
                    visit(dep)
            ordered.append((module, IMPORT_LINE_RE.sub("", source).strip("\n")))

        for module in layout.imports_of(main):
            if module == HAZARDS_PREFIX or module.startswith(HAZARDS_PREFIX + "."):
                visit(module)
    except OSError as exc:
        msg = f"the hazard checkers are not in this package: {exc.filename}"
        raise api_error(503, "hazards-program-unreadable", msg) from exc
    registry = REGISTRY_RE.search(main)
    if registry is None or not ordered:
        msg = f"{HAZARDS_MAIN.name} names no registry of checkers"
        raise api_error(503, "hazards-program-unreadable", msg)
    return ordered, registry.group("list")


def hazards_program(decl_name: str, checkers: list[str]) -> str:
    """The gate's checkers and the few lines that ask them one question: the findings of exactly
    ``checkers``, in that order, over ``decl_name``'s type, printed as ``opn-hazards`` prints
    them. Each file sits in a ``section`` so its ``open`` lines end with it, and the question
    runs under the context ``opn-hazards`` gives it (no open namespaces, no options), because a
    finding's location is pretty-printed and is what an acknowledgment must match (F02-Q4)."""
    sources, registry = hazard_sources()
    block = "".join(
        f"\nsection\n-- inlined by the network from {module} (F13-T20)\n{src}\nend\n"
        for module, src in sources
    )
    ids = "[" + ", ".join(json.dumps(c) for c in checkers) + "]"
    return (
        "\n-- the network's hazard pre-screen (F13-T20): gate/lean/OpnGate/Hazards*.lean\n"
        f"{block}\n"
        "namespace OpnGate.Hazards\n"
        "-- HazardsMain.lean's registry, inlined by the network\n"
        f"def networkRegistry : Array Checker :=\n  {registry}\n"
        "end OpnGate.Hazards\n\n"
        "run_meta do\n"
        f"  let s ← Lean.getConstInfo `{decl_name}\n"
        f"  let ids : List String := {ids}\n"
        "  let selected := ids.toArray.filterMap fun id =>\n"
        "    OpnGate.Hazards.networkRegistry.find? (·.id == id)\n"
        "  let (findings, capped) ← withTheReader Lean.Core.Context\n"
        "      (fun c => { c with openDecls := [], currNamespace := Lean.Name.anonymous,\n"
        "                         options := Lean.Options.empty })\n"
        "      (OpnGate.Hazards.run selected s.type)\n"
        "  let answer := Lean.Json.mkObj [\n"
        '    ("checkers", Lean.toJson (selected.map (·.id))),\n'
        '    ("findings", Lean.toJson findings), ("capped", Lean.Json.bool capped)]\n'
        f'  Lean.logInfo (Lean.MessageData.ofFormat (Std.Format.text ("{HAZARDS_TAG} " ++ '
        "answer.compress)))\n"
    )


def hazards_text(formal: str, decl_name: str, checkers: list[str]) -> str:
    """What the checker is sent in hazards mode: the statement under its own header (the
    definitions already inlined), ``import Lean`` for the checkers, then the program."""
    lines = formal.splitlines(keepends=True)
    imports = [i for i, line in enumerate(lines) if line.startswith("import ")]
    at = imports[-1] + 1 if imports else 0
    header = "" if "Lean" in layout.imports_of(formal) else "import Lean\n"
    return "".join(lines[:at]) + header + "".join(lines[at:]) + hazards_program(decl_name, checkers)


def hazards_verdict(body: dict[str, Any]) -> dict[str, Any] | None:
    """The program's one line, read back out of the checker's info messages, in the shape
    ``opn-hazards`` prints (``checkers``, ``findings`` of ``{checker, location, message}``,
    ``capped``); ``None`` when it never ran (the statement did not elaborate). Untrusted text:
    only those keys are read, each held to its type."""
    messages = body.get("lean_messages")
    infos = messages.get("infos") if isinstance(messages, dict) else None
    for info in infos if isinstance(infos, list) else ():
        _, tag, rest = str(info).partition(HAZARDS_TAG + " ")
        if not tag:
            continue
        try:
            doc = json.loads(rest.strip())
        except ValueError:
            continue
        if not isinstance(doc, dict):
            continue
        raw, ids = doc.get("findings"), doc.get("checkers")
        if not isinstance(raw, list) or not isinstance(ids, list):
            continue
        findings = [
            {k: f[k] for k in ("checker", "location", "message")}
            for f in raw
            if isinstance(f, dict)
            and all(isinstance(f.get(k), str) for k in ("checker", "location", "message"))
        ]
        return {
            "checkers": [c for c in ids if isinstance(c, str)],
            "findings": findings,
            "capped": doc.get("capped") is True,
        }
    return None


def target_checkers(ctx: Context, target_id: str) -> list[str]:
    """The hazard checkers the target's ``gate-spec.json`` names, which step 6 runs; one this
    gate does not ship is the gate owner's configuration error, refused by the gate's own words
    (``steps.hazards.check_config``, F02-R3)."""
    from opn_gate.steps import hazards as gate_hazards  # noqa: PLC0415 — only this path needs it

    spec = json.loads(frontier.committed(ctx, f"targets/{target_id}/gate-spec.json"))
    problem = gate_hazards.check_config(spec)
    if problem is not None:
        raise api_error(409, problem.code, problem.message, details=problem.details)
    return [str(c) for c in spec.get("hazard_checkers") or []]


# --- the checker ---------------------------------------------------------------------------------

_SLOTS_LOCK = threading.Lock()
#: How long a check waits for a free slot (R8). Its own short budget, not the checker's: the
#: function lives 29 s, and a caller held for the checker's whole budget had none left (T13).
SLOT_WAIT_S = 2.0
#: F13-T16: the checker's budget when a proposal is pre-flighted. Shorter than a check's own
#: (``check_timeout_s``), because the same function must still open the pull request after it.
PREFLIGHT_TIMEOUT_S = 12
#: What the pull request's own calls (a branch, a commit, the pull request) are allowed after the
#: pre-flight, within the function's timeout.
PREFLIGHT_PR_HEADROOM_S = 8
#: The hosted checker's word for its own budget running out, in a 200 body (probed 2026-09-21).
LEAN_TIMEOUT = "LeanTimeout"


def timed_out(ctx: Context, request_id: str | None) -> Exception:
    """F13-T13: the one answer for a check that ran out of time, whether the checker said so or
    the transport did. Named, with the budget, so a contributor learns what does not fit instead
    of reading a gateway's 500."""
    budget = ctx.settings.check_timeout_s
    return api_error(
        504,
        "check-timeout",
        f"the check did not finish within the fast check's {budget} s budget. Search tactics such "
        "as exact?, apply? and rw? rarely fit it: find the lemma another way and name it. The "
        "precheck (POST /precheck) has the gate's full budget",
        details={"budget_s": budget, "axle_request_id": request_id},
    )


def slots(ctx: Context) -> threading.BoundedSemaphore:
    """This application's in-flight cap (R8, Q8), created on first use and kept on its Context.

    Not in a table keyed by ``id(ctx)``: CPython reuses a collected object's address, so a new
    application could inherit an old one's semaphore with another cap — which is how the first
    version failed once in a full suite run and never alone (evidence task-4.txt)."""
    with _SLOTS_LOCK:
        if ctx.check_slots is None:
            ctx.check_slots = threading.BoundedSemaphore(ctx.settings.check_concurrency)
        return ctx.check_slots


def call_checker(  # noqa: PLR0913 — the request, and how long it may take
    ctx: Context,
    req: CheckRequest,
    text: str,
    environment: str,
    formal: str | None,
    *,
    timeout_s: float | None = None,
) -> AxleAnswer:
    """``formal`` is the node's statement as the checker must compile it: with the definitions
    inlined exactly as they are into ``text`` (F13-T11), and ``None`` outside verify. The budget
    is the check's own unless the caller sets a shorter one (the pre-flight, F13-T16)."""
    budget = ctx.settings.check_timeout_s if timeout_s is None else timeout_s
    gate = slots(ctx)
    if not gate.acquire(timeout=min(SLOT_WAIT_S, ctx.settings.check_timeout_s)):
        msg = f"{ctx.settings.check_concurrency} checks are already in flight; retry shortly"
        raise api_error(503, "checker-busy", msg, headers={"Retry-After": "5"})
    try:
        if req.mode == "verify":
            assert formal is not None  # parse_body refuses verify without a node
            return ctx.axle.verify_proof(
                text,
                formal_statement=formal,
                environment=environment,
                timeout_s=budget,
            )
        return ctx.axle.check(text, environment=environment, timeout_s=budget)
    finally:
        gate.release()


# --- the log -------------------------------------------------------------------------------------


def verdict(body: dict[str, Any]) -> bool | None:
    """F13-T10: the checker's ``okay`` as the caller and the call log both read it — true, false,
    or ``None`` when the body carries no boolean verdict. AXLE answers a statement that does not
    compile with ``user_error`` and no ``okay`` at all, which is a third answer, not a false."""
    okay = body.get("okay")
    return okay if isinstance(okay, bool) else None


def error_count(body: dict[str, Any]) -> int | None:
    """Lean's errors plus the tool's, when the body has the shape AXLE answers with."""
    total, seen = 0, False
    for key in ("lean_messages", "tool_messages"):
        block = body.get(key)
        if isinstance(block, dict) and isinstance(block.get("errors"), list):
            total += len(block["errors"])
            seen = True
    return total if seen else None


def checker_errors(body: dict[str, Any]) -> list[str]:
    """F13-T17: Lean's error messages, then the tool's, as the checker gave them (untrusted text,
    passed back to the caller who sent it)."""
    out: list[str] = []
    for key in ("lean_messages", "tool_messages"):
        block = body.get(key)
        errors = block.get("errors") if isinstance(block, dict) else None
        out += [str(e) for e in errors] if isinstance(errors, list) else []
    return out


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
        okay=verdict(body),
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


# --- the pre-flight on a proposal (F13-T16) ------------------------------------------------------

#: What a proposal's 201 says of its pre-flight: the checker found the witness's type is the one
#: step 7 wants and the text compiles (F13-T17); it answered without a verdict (the statement or
#: the witness did not elaborate there); or it could not be asked (no environment, down, out of
#: time, busy, budget spent).
PREFLIGHT_MATCHED = "matched"
PREFLIGHT_INCONCLUSIVE = "inconclusive"
PREFLIGHT_UNAVAILABLE = "unavailable"


async def preflight_witness(
    ctx: Context, identity_id: str, target_id: str, node_id: str, files: dict[str, str]
) -> str:
    """Witness mode over exactly the files a proposal is about to push, before its pull request
    exists: the statement as written (own-Context import included), its generated Context
    inlined, and the witness. Two refusals: a mismatch (422 ``witness-type-mismatch`` with both
    types), and a witness of the right type that does not compile (422 ``witness-fails`` with the
    checker's errors, F13-T17); anything else is an outcome word and the proposal proceeds,
    because the hosted checker is a courtesy and step 7 is the authority (D-4 v3.14). Charged to
    the identity's check budget and logged as a check, like every call to the checker (R8, R9)."""
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports the routes that import this

    prefix = f"targets/{target_id}/nodes/{node_id}/"
    parsed = layout.parse_statement(files.get(prefix + "Statement.lean", ""))
    witness = files.get(prefix + "Witness.lean", "")
    if not isinstance(parsed, layout.Statement) or not witness.strip():
        return PREFLIGHT_UNAVAILABLE  # the scaffold refuses both before this is reached
    try:
        ratelimit.check_check(ctx, identity_id)
    except ApiError:
        return PREFLIGHT_UNAVAILABLE  # a spent check budget skips the courtesy, never the route
    req = CheckRequest(target_id, node_id, witness, "witness")
    caller = Caller("identity", identity_id)
    started = time.monotonic()
    environment: str | None = None
    try:
        _, entry = hosted_for(ctx, target_id)
        if entry is None or entry.environment is None:
            raise api_error(422, "no-hosted-environment", f"{target_id} has no hosted checker")
        environment = entry.environment
        context = files.get(prefix + "Context.lean")
        defs = inline_defs(ctx, target_id, parsed, witness, node_id, context=context)
        text = witness_text(forwarded_text(parsed.text, defs), witness, parsed.decl_name)
        budget = min(PREFLIGHT_TIMEOUT_S, ctx.settings.check_timeout_s)
        answer = await asyncio.to_thread(
            call_checker, ctx, req, text, environment, None, timeout_s=budget
        )
        if answer.body.get("error_type") == LEAN_TIMEOUT:
            raise timed_out(ctx, answer.request_id)
    except (ApiError, AxleError) as exc:
        code = exc.code if isinstance(exc, ApiError) else "upstream-unavailable"
        status = exc.status if isinstance(exc, AxleError) else None
        write_log(
            ctx,
            req,
            caller,
            outcome=code,
            started=started,
            environment=environment,
            upstream_status=status,
        )
        log.info("preflight %s for %s: %s", PREFLIGHT_UNAVAILABLE, node_id, code)
        return PREFLIGHT_UNAVAILABLE
    log_id = write_log(
        ctx, req, caller, outcome=ANSWERED, started=started, environment=environment, answer=answer
    )
    found = witness_verdict(answer.body)
    if found is None or found["matches"] is None:
        return PREFLIGHT_INCONCLUSIVE
    if found["matches"]:
        # F13-T17 (D1): a declaration whose proof fails keeps its stated type, so ``matches``
        # alone passed PR #195's witness, whose ``decide`` proved the statement false. It is
        # matched only when the checker's verdict is true too; a body with no verdict at all
        # (``user_error``) said nothing about the witness.
        okay = verdict(answer.body)
        if okay is None:
            return PREFLIGHT_INCONCLUSIVE
        if okay:
            return PREFLIGHT_MATCHED
        raise api_error(
            422,
            "witness-fails",
            "the witness has the type step 7 wants but does not compile: the checker reported "
            "errors in the statement and witness it was sent (D-4 step 7), so nothing was "
            f"opened. Checked on the hosted fast checker ({environment}); not authoritative, "
            "but step 7 elaborates the same text",
            details={"errors": checker_errors(answer.body), "log_id": log_id},
        )
    raise api_error(
        422,
        "witness-type-mismatch",
        "the witness's type is not the one step 7 holds a witness of this statement to "
        "(D-4 step 7), so nothing was opened: give the witness the type in `expected`. Checked "
        f"on the hosted fast checker ({environment}); not authoritative, but step 7 computes the "
        "type with the same metaprogram",
        details={"expected": found["expected"], "given": found["given"], "log_id": log_id},
    )


#: What a proposal's 201 says of its hazard pre-flight (F13-T20): the target's checkers ran and
#: every finding is acknowledged (or the target names none); the program did not run (the
#: statement did not elaborate there); or the checker could not be asked.
PREFLIGHT_CLEAR = "clear"


async def preflight_hazards(  # noqa: PLR0911 — one return per outcome word
    ctx: Context, identity_id: str, target_id: str, node_id: str, files: dict[str, str]
) -> str:
    """F13-T20 (D8): step 6 over exactly the statement a proposal is about to push, before its
    pull request exists, on the hosted checker: the target's checkers, the gate's own matching
    of each finding against the ``acknowledged_hazards`` in the ``META.yaml`` being pushed
    (``steps.hazards.evaluate``), and the gate's own refusal, 422 ``hazard-unacknowledged`` with
    ``findings``, ``acknowledged`` and ``checkers`` as step 6 prints them. Anything else is an
    outcome word and the proposal proceeds: step 6 is the authority. Charged and logged as a
    check (R8, R9)."""
    import yaml  # noqa: PLC0415 — only this path reads a META.yaml

    from opn_api.app import ApiError  # noqa: PLC0415 — app imports the routes that import this
    from opn_gate.steps import hazards as gate_hazards  # noqa: PLC0415

    prefix = f"targets/{target_id}/nodes/{node_id}/"
    parsed = layout.parse_statement(files.get(prefix + "Statement.lean", ""))
    if not isinstance(parsed, layout.Statement):
        return PREFLIGHT_UNAVAILABLE  # the scaffold refuses it before this is reached
    try:
        checkers = target_checkers(ctx, target_id)
    except ApiError:
        return PREFLIGHT_UNAVAILABLE  # the gate owner's configuration, or the graph unread
    if not checkers:
        return PREFLIGHT_CLEAR  # step 6 runs nothing on this target; nothing to spend
    try:
        ratelimit.check_check(ctx, identity_id)
    except ApiError:
        return PREFLIGHT_UNAVAILABLE  # a spent check budget skips the courtesy, never the route
    req = CheckRequest(target_id, node_id, parsed.text, "hazards")
    caller = Caller("identity", identity_id)
    started = time.monotonic()
    environment: str | None = None
    try:
        _, entry = hosted_for(ctx, target_id)
        if entry is None or entry.environment is None:
            raise api_error(422, "no-hosted-environment", f"{target_id} has no hosted checker")
        environment = entry.environment
        context = files.get(prefix + "Context.lean")
        defs = inline_defs(ctx, target_id, parsed, "", node_id, context=context)
        text = hazards_text(forwarded_text(parsed.text, defs), parsed.decl_name, checkers)
        budget = min(PREFLIGHT_TIMEOUT_S, ctx.settings.check_timeout_s)
        answer = await asyncio.to_thread(
            call_checker, ctx, req, text, environment, None, timeout_s=budget
        )
        if answer.body.get("error_type") == LEAN_TIMEOUT:
            raise timed_out(ctx, answer.request_id)
    except (ApiError, AxleError) as exc:
        code = exc.code if isinstance(exc, ApiError) else "upstream-unavailable"
        status = exc.status if isinstance(exc, AxleError) else None
        write_log(
            ctx,
            req,
            caller,
            outcome=code,
            started=started,
            environment=environment,
            upstream_status=status,
        )
        log.info("hazards preflight %s for %s: %s", PREFLIGHT_UNAVAILABLE, node_id, code)
        return PREFLIGHT_UNAVAILABLE
    log_id = write_log(
        ctx, req, caller, outcome=ANSWERED, started=started, environment=environment, answer=answer
    )
    found = hazards_verdict(answer.body)
    if found is None:
        return PREFLIGHT_INCONCLUSIVE
    try:
        meta = yaml.safe_load(files.get(prefix + "META.yaml", "")) or {}
    except yaml.YAMLError:
        meta = {}
    acks = gate_hazards.acknowledgments_from(meta if isinstance(meta, dict) else {})
    ev = gate_hazards.evaluate(gate_hazards.findings_from(found), acks)
    if not ev.unacknowledged:
        return PREFLIGHT_CLEAR
    first = ev.unacknowledged[0]
    raise api_error(
        422,
        "hazard-unacknowledged",
        f"{len(ev.unacknowledged)} unacknowledged hazard finding(s); first: {first.checker} at "
        f"{first.location}: {first.message}. Nothing was opened: acknowledge each in "
        "acknowledged_hazards with its checker, its location exactly as printed and a "
        "justification (F02-R4), or change the statement. Checked with step 6's own checkers "
        f"on the hosted fast checker ({environment}); not authoritative, step 6 decides",
        details={
            "findings": [f.as_dict() for f in ev.unacknowledged],
            "acknowledged": [a.as_dict() for a in ev.used],
            "checkers": checkers,
            "log_id": log_id,
        },
    )


async def preflight_proposal(
    ctx: Context, identity_id: str, target_id: str, node_id: str, files: dict[str, str]
) -> dict[str, str]:
    """F13-T20: both pre-flights, side by side, so the two fit in the one budget the function has
    before it opens the pull request (F13-T16). A hazard refusal is raised before a witness
    refusal: the statement is what the witness is of."""
    hazards, witness = await asyncio.gather(
        preflight_hazards(ctx, identity_id, target_id, node_id, files),
        preflight_witness(ctx, identity_id, target_id, node_id, files),
        return_exceptions=True,
    )
    for outcome in (hazards, witness):
        if isinstance(outcome, BaseException):
            raise outcome
    assert isinstance(hazards, str) and isinstance(witness, str)
    return {"hazards_preflight": hazards, "witness_preflight": witness}


# --- the pre-flight on an exhibit (F13-T22) ------------------------------------------------------

#: What a defect claim's or revision request's receipt says of its exhibit (F13-T22): the checker
#: compiled it; it answered without a verdict or with no Lean error to name; it could not be
#: asked; or the exhibit was not sent, because what the gate checks of it is not a compile the
#: service can reproduce (a circularity claim's relation, a module only the gate's staging holds).
PREFLIGHT_ELABORATES = "elaborates"
PREFLIGHT_SKIPPED = "skipped"
#: The node modules an exhibit may import, as the gate stages them (``exhibits.stage_node``).
EXHIBIT_NODE_MODULES = ("Statement", "Context")


def exhibit_imports(exhibit: str, node_id: str | None) -> tuple[list[str], set[str]] | None:
    """The exhibit's library imports and which of its own node's modules it imports, or ``None``
    when it names a module the checker could only be given by the gate's staging — another
    node's, or one that is neither a library, the target's ``Defs`` nor its own node's."""
    library: list[str] = []
    own: set[str] = set()
    for module in layout.imports_of(exhibit):
        origin, of_node = layout.module_origin(module)
        stem = module.rsplit(".", 1)[-1]
        if origin == "library":
            library.append(module)
        elif origin == "node":
            if node_id is None or of_node != node_id or stem not in EXHIBIT_NODE_MODULES:
                return None
            own.add(stem)
        elif origin != "defs":
            return None
    return library, own


def exhibit_check_text(
    ctx: Context,
    target_id: str,
    node_id: str | None,
    exhibit: str,
    found: tuple[list[str], set[str]],
) -> str:
    """The exhibit as the gate elaborates it, in one file: the node's committed ``Defs`` and
    Context, then its committed statement when the exhibit imports it, inlined in place of the
    imports the checker cannot resolve, under the union of their library imports. ``found`` is
    ``exhibit_imports``' answer."""
    library, own = found
    statement: layout.Statement | None = None
    headers = [exhibit]
    if "Statement" in own:
        assert node_id is not None
        raw = frontier.committed(ctx, f"targets/{target_id}/nodes/{node_id}/Statement.lean")
        parsed = layout.parse_statement(raw.decode("utf-8"))
        if not isinstance(parsed, layout.Statement):
            msg = f"{node_id}'s Statement.lean has no single sorry-bodied theorem"
            raise api_error(409, "statement-unparsable", msg)
        statement = parsed
        headers.append(parsed.text)
    defs = inline_defs(ctx, target_id, statement, exhibit, node_id if own else None)
    for module, _ in defs:
        origin, _node = layout.module_origin(module)
        if origin == "defs":
            path = f"targets/{target_id}/defs/{module.partition('.')[2]}.lean"
        else:
            assert node_id is not None
            path = f"targets/{target_id}/nodes/{node_id}/Context.lean"
        headers.append(frontier.committed(ctx, path).decode("utf-8"))
    if statement is not None:
        assert node_id is not None
        body = IMPORT_LINE_RE.sub("", statement.text).strip("\n")
        defs.append((layout.node_module(node_id, "Statement"), body))
    imports = [
        m
        for text in headers
        for m in layout.imports_of(text)
        if layout.module_origin(m)[0] == "library"
    ]
    header = "".join(f"import {m}\n" for m in dict.fromkeys([*library, *imports]))
    return forwarded_text(header + IMPORT_LINE_RE.sub("", exhibit), defs)


def lean_errors(body: dict[str, Any]) -> list[str]:
    """Lean's own error messages, and not the tool's: an exhibit is refused only on what the
    elaborator said, since that is what the gate's elaboration would say too."""
    block = body.get("lean_messages")
    errors = block.get("errors") if isinstance(block, dict) else None
    return [str(e) for e in errors] if isinstance(errors, list) else []


async def preflight_exhibit(  # noqa: PLR0913 — the caller, the node, the text, and its class
    ctx: Context,
    identity_id: str,
    target_id: str,
    node_id: str | None,
    exhibit: str,
    *,
    relational: bool = False,
) -> str:
    """F13-T22: the gate's exhibit check (``opn-gate exhibits``: the exhibit elaborates, against
    the node it is about) on the hosted checker, before the append's pull request exists. One
    refusal, 422 ``exhibit-elaboration`` with Lean's ``errors``, when the checker answers that the
    text does not compile and names why; anything else is an outcome word and the append opens,
    because the gate's sandbox is the authority (C9, D-4 v3.14). ``relational`` is a circularity
    claim, whose exhibit the gate also holds to an implication by a program the checker is not
    sent, so it is skipped rather than half-checked. Charged and logged as a check (R8, R9)."""
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports the routes that import this

    found = None if relational else exhibit_imports(exhibit, node_id)
    if found is None:
        return PREFLIGHT_SKIPPED
    try:
        ratelimit.check_check(ctx, identity_id)
    except ApiError:
        return PREFLIGHT_UNAVAILABLE  # a spent check budget skips the courtesy, never the route
    req = CheckRequest(target_id, node_id, exhibit, "check")
    caller = Caller("identity", identity_id)
    started = time.monotonic()
    environment: str | None = None
    try:
        _, entry = hosted_for(ctx, target_id)
        if entry is None or entry.environment is None:
            raise api_error(422, "no-hosted-environment", f"{target_id} has no hosted checker")
        environment = entry.environment
        text = exhibit_check_text(ctx, target_id, node_id, exhibit, found)
        budget = min(PREFLIGHT_TIMEOUT_S, ctx.settings.check_timeout_s)
        answer = await asyncio.to_thread(
            call_checker, ctx, req, text, environment, None, timeout_s=budget
        )
        if answer.body.get("error_type") == LEAN_TIMEOUT:
            raise timed_out(ctx, answer.request_id)
    except (ApiError, AxleError) as exc:
        code = exc.code if isinstance(exc, ApiError) else "upstream-unavailable"
        status = exc.status if isinstance(exc, AxleError) else None
        write_log(
            ctx,
            req,
            caller,
            outcome=code,
            started=started,
            environment=environment,
            upstream_status=status,
        )
        log.info("exhibit preflight %s for %s: %s", PREFLIGHT_UNAVAILABLE, target_id, code)
        return PREFLIGHT_UNAVAILABLE
    log_id = write_log(
        ctx, req, caller, outcome=ANSWERED, started=started, environment=environment, answer=answer
    )
    okay = verdict(answer.body)
    if okay is True:
        return PREFLIGHT_ELABORATES
    errors = lean_errors(answer.body)
    if okay is None or not errors:
        return PREFLIGHT_INCONCLUSIVE
    raise api_error(
        422,
        "exhibit-elaboration",
        "the exhibit does not elaborate: the checker reported Lean errors in it (F08-R6, R7), so "
        "nothing was opened. An exhibit is Lean the gate elaborates against the node it is about, "
        "not prose. Checked on the hosted fast checker "
        f"({environment}) with the node's statement, Context and definitions inlined where the "
        "exhibit imports them; not authoritative, but the gate elaborates the same text",
        details={"errors": errors, "log_id": log_id},
    )


# --- the routes ----------------------------------------------------------------------------------


def statement_mode_text(
    ctx: Context, req: CheckRequest, statement: layout.Statement, formal: str
) -> str:
    """The text sent in a mode that reads the statement: the witness program (F13-T14) or the
    hazard checkers (F13-T20), after ``formal``, the statement with its definitions inlined."""
    if req.mode == "hazards":
        return hazards_text(formal, statement.decl_name, target_checkers(ctx, req.target_id))
    # The caller's own text, not the forwarded one: the definitions and the Context are already
    # in ``formal``, and inlined into an empty witness they read as one.
    return witness_text(formal, req.content, statement.decl_name)


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
        context: str | None = None
        if req.statement is not None:
            # F13-T16: a statement that is not a node yet, with the Context its proposal would
            # carry. parse_body has already held it to one sorry-bodied theorem.
            parsed = layout.parse_statement(without_node_imports(req.statement))
            statement = parsed if isinstance(parsed, layout.Statement) else None
            context = proposed_context(ctx, req.target_id, req.deps)
        else:
            statement = statement_of(ctx, req.target_id, req.node_id) if req.node_id else None
        if req.mode in NODE_MODES and statement is None:
            msg = f"{req.node_id}'s Statement.lean has no single sorry-bodied theorem to verify"
            raise api_error(409, "statement-unparsable", msg)
        defs = inline_defs(ctx, req.target_id, statement, req.content, req.node_id, context=context)
        text = forwarded_text(req.content, defs)
        # F13-T14: a witness is not a proof. It declares ``witness`` and its header is its own,
        # so the gate-gap lints (R4), which are about proofs, say nothing true of it.
        warnings = [] if req.mode in STATEMENT_MODES else lint(req.content, statement, req.node_id)
        warnings += superseded_warning(ctx, req.node_id)
        if req.mode == "verify" and req.node_id is not None:
            own = layout.node_module(req.node_id, "Context")
            # T15: only a Context that declares something restates anything. Every statement
            # imports its own Context since F08-T13, so an empty one ("dependencies: none")
            # set the warning off on every node, where it said nothing true.
            if any(
                module == own and DECLARATION_RE.search(layout.strip_comments(source))
                for module, source in defs
            ):
                # F13-T12: a Context restates each dependency with a sorry body (the gate builds
                # against the real proofs instead), and a verifier refuses any proof that leans on
                # one, so its "no" here says nothing about the contributor's proof.
                warnings.append(
                    {
                        "code": "context-restated",
                        "message": "this node's Context restates its dependencies with sorry "
                        "bodies, so verify reports a proof that uses one as incomplete whatever "
                        "its merit; use mode check for it, and the precheck for the verdict",
                    }
                )
        try:
            formal = forwarded_text(statement.text, defs) if statement is not None else None
            if req.mode in STATEMENT_MODES:
                assert statement is not None and formal is not None  # NODE_MODES, above
                text = statement_mode_text(ctx, req, statement, formal)
            answer = await asyncio.to_thread(call_checker, ctx, req, text, environment, formal)
            if answer.body.get("error_type") == LEAN_TIMEOUT:
                raise timed_out(ctx, answer.request_id)
        except AxleError as exc:
            if exc.timed_out:
                raise timed_out(ctx, None) from exc
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
    user_error = answer.body.get("user_error")
    shown, dropped = without_generated_name_warning(answer.body, statement, req.node_id)
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
            # T10: the two facts a caller reads first, lifted beside the verbatim body, so a
            # body with no ``okay`` (a statement that does not compile) is still an answer.
            "okay": verdict(answer.body),
            "user_error": user_error if isinstance(user_error, str) else None,
            "result": shown,
            # F13-T18: what was left out of ``result`` and why; the log keeps the checker's own.
            "dropped_warnings": dropped,
            "log_id": log_id,
            **({"witness": witness_verdict(answer.body)} if req.mode == "witness" else {}),
            # F13-T20: step 6's findings as opn-hazards prints them, ready to acknowledge.
            **({"hazards": hazards_verdict(answer.body)} if req.mode == "hazards" else {}),
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
