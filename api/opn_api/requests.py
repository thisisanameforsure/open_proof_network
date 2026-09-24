"""Revision requests and defect claims (F08-R6, R7; D-8, D-16, D-35).

Both are appends: a record that claims nothing a kernel could check lands under the node (or the
target's ``defs/``) through a pull request the gate merges on its schema and, for a defect claim,
D-16's mechanical pre-triage — which this module applies first, so a malformed claim bounces
here with the rule named and never reaches the graph. The gate repeats the same check in CI
(D-35), because the service is not the trust base and a hand-opened pull request gets the same
answer.

Neither record changes a statement. A revision request is evidence a curator may act on by
versioning the node (D-8); a defect claim is evidence an adjudicator weighs (D-17, Stage 1).
Exhibits are Lean files, stored verbatim, elaborated only in the gate's sandbox (C9).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import appends, claims, duplicates, precheck, proposals
from opn_api import clock as clockmod
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_api.githost import GitHostError
from opn_gate import graph as graphmod
from opn_gate import records, schemas

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

log = logging.getLogger(__name__)

REVISION_SCHEMA = "revision-request/v1"
DEFECT_SCHEMA = "defect-claim/v1"
#: D-16's taxonomy, verbatim; the schema carries the same list, and this is the one the 400 names.
DEFECT_CLASSES: tuple[str, ...] = (
    "missing-hypothesis",
    "junk-value",
    "vacuity",
    "quantifier-scope",
    "wrong-domain",
    "definition-mismatch",
    "strength-drift",
    "other-with-exhibit",
)
DEFS_PREFIX = "defs/"
#: F08-T17: the class that says a node is no easier than a node above it, filed at v3 with the
#: ancestor it names; every other class is still filed at v1.
CIRCULAR_CLASS = records.CIRCULAR_CLASS
CIRCULAR_SCHEMA = "defect-claim/v3"
#: A defect claim's classes: D-16's taxonomy and the circularity class. A revision request
#: (``revision-request/v1``) takes the taxonomy alone.
DEFECT_CLAIM_CLASSES: tuple[str, ...] = (*DEFECT_CLASSES, CIRCULAR_CLASS)


def check_class(raw: Any, field: str, classes: tuple[str, ...] = DEFECT_CLASSES) -> str:
    """D-16 (1): a claim names a defect class from the taxonomy or it bounces."""
    if raw not in classes:
        raise ApiError(
            400,
            "defect-class",
            f"{field} must be one of {', '.join(classes)} (D-16's taxonomy; "
            "a claim that names no class bounces)",
        )
    return str(raw)


def exhibit_text(fields: dict[str, Any], *, required: bool) -> str | None:
    text = proposals.lean_text(fields, "exhibit", required=required)
    if text is not None and not text.strip():
        raise ApiError(400, "exhibit-missing", "exhibit is required and must be a Lean file")
    return text


def fetch_optional(ctx: Context, path: str) -> bytes | None:
    """A committed file, or ``None`` when the graph has no such file; unreachable is a 503."""
    try:
        got = ctx.githost.fetch_raw(
            ctx.settings.graph_repo, ctx.settings.graph_branch, path, etag=None
        )
    except GitHostError as exc:
        raise ApiError(503, "graph-unreachable", f"cannot read {path} from the graph") from exc
    if got.status == 404 or got.body is None:
        return None
    return got.body


# --- POST /revision-requests (D-8) ---------------------------------------------------------------


def check_text_cap(text: str) -> None:
    """F07-R14's rule: the cap is the schema's, named without echoing the text."""
    evidence = schemas.load_schema(REVISION_SCHEMA)["properties"]["evidence"]
    cap = int(evidence["properties"]["text"]["maxLength"])
    if len(text) > cap:
        raise ApiError(
            400, "field-too-long", f"evidence.text is {len(text)} characters; the cap is {cap}"
        )


def as_evidence(raw: Any) -> dict[str, Any]:
    """``{text, exhibit?}``: the text is capped by the schema, the exhibit is a Lean file."""
    if isinstance(raw, str):
        raw = {"text": raw}
    if not isinstance(raw, dict):
        raise ApiError(400, "evidence-invalid", "evidence must be {text, exhibit?}")
    text = raw.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ApiError(400, "evidence-invalid", "evidence.text is required")
    out: dict[str, Any] = {"text": text}
    exhibit = exhibit_text(raw, required=False)
    if exhibit is not None:
        out["exhibit"] = exhibit
    return out


#: F05-T8: the fields ``POST /revision-requests`` reads; any other top-level key is refused.
REVISION_FIELDS: tuple[str, ...] = ("node_id", "defect_class", "evidence")


async def post_revision_requests(ctx: Context, request: Request) -> Response:
    """R6: a claim that a statement is defective, with evidence, for a curator to act on."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, REVISION_FIELDS)
    node_id, target_id = appends.node_target(ctx, fields)
    doc: dict[str, Any] = {
        "schema": REVISION_SCHEMA,
        "node": node_id,
        "contributor": identity.pseudonym,
        "defect_class": check_class(fields.get("defect_class"), "defect_class"),
        "evidence": as_evidence(fields.get("evidence")),
        "date": clockmod.render(ctx.clock.now())[:10],
    }
    check_text_cap(doc["evidence"]["text"])
    appends.validated(doc, REVISION_SCHEMA)
    path = appends.node_dir(target_id, node_id) + (
        f"revisions/{appends.record_name(ctx, identity)}.yaml"
    )
    return JSONResponse(
        appends.append_pr(
            ctx,
            identity,
            path=path,
            content=yaml.safe_dump(doc, sort_keys=True, allow_unicode=True),
            subject=f"revision request: {node_id}",
            what="revision request",
            kind="revision-request",
            target_id=target_id,
            node_id=node_id,
        ),
        status_code=201,
    )


# --- POST /defect-claims (D-16) -------------------------------------------------------------------


def resolve_ref(ctx: Context, raw: Any) -> tuple[str, str, str, dict[str, Any] | None]:
    """(target_id, stmt_ref as recorded, referenced path, the node's facts): a node id, or
    ``<target>/defs/<file>``, which has no facts. F08-T18: the facts are kept, since they say
    whether the node is already circular."""
    if not isinstance(raw, str) or not raw:
        raise ApiError(400, "stmt-ref-missing", "stmt_ref is required")
    target_id, sep, rest = raw.partition("/")
    if sep and rest.startswith(DEFS_PREFIX):
        appends.known_target(ctx, target_id)
        return target_id, rest, f"targets/{target_id}/{rest}", None
    if sep:
        raise ApiError(
            400, "stmt-ref-invalid", "stmt_ref is a node id, or <target>/defs/<file>.lean"
        )
    facts = precheck.node_facts(ctx, raw)
    target_id = str(facts["target_id"])
    return target_id, raw, f"targets/{target_id}/nodes/{raw}/Statement.lean", facts


def merged_claims_of(
    ctx: Context, target_id: str, node_id: str, defect_class: str
) -> tuple[str, ...]:
    """The paths of the node's merged defect claims of ``defect_class`` on ``main``. Only a
    message reads them, so a host that cannot answer gives none and the message names the
    directory instead (C7)."""
    folder = appends.node_dir(target_id, node_id) + "defects"
    try:
        names = ctx.githost.list_dir(ctx.settings.graph_repo, ctx.settings.graph_branch, folder)
        found = []
        for name in names or ():
            if not name.endswith(".yaml"):
                continue
            body = fetch_optional(ctx, f"{folder}/{name}")
            doc = yaml.safe_load(body) if body is not None else None
            if isinstance(doc, dict) and doc.get("class") == defect_class:
                found.append(f"{folder}/{name}")
    except Exception as exc:  # any host or parse failure: the refusal stands without the paths
        log.warning("%s: merged defect claims not listed: %s", node_id, type(exc).__name__)
        return ()
    return tuple(found)


def known_state(
    ctx: Context, defect_class: str, stmt_ref: str, facts: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """F08-T18 (ruling D2): a defect claim of a class already merged on the node is refused, and
    one of a class already open is named. The products record one class's merge — a merged
    circularity claim is the node's ``cause: circular`` (F08-T17) — so that is the refusal; the
    open ones are the service's own records, each carrying its class. Answers ``also_open``."""
    if facts is None:  # a definitions file: no node, no cause, no node-scoped records
        return []
    if defect_class == CIRCULAR_CLASS and facts.get("cause") == graphmod.CAUSE_CIRCULAR:
        target_id = str(facts["target_id"])
        raise claims.circular(
            stmt_ref,
            facts,
            lead=f"{stmt_ref} already has a merged circularity claim, and a second adds nothing",
            merged=merged_claims_of(ctx, target_id, stmt_ref, defect_class),
        )
    return [
        {"pr_number": found.pr_number, "pseudonym": found.pseudonym}
        for found in duplicates.open_rivals(ctx, stmt_ref, frozenset({"defect-claim"}))
        if found.defect_class == defect_class
    ]


def check_line(ctx: Context, raw: Any, path: str) -> int:
    """D-16 (1): the claim points at a specific, existing line of the referenced file."""
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        raise ApiError(400, "defect-line", "line must be a positive integer (D-16)")
    body = fetch_optional(ctx, path)
    if body is None:
        raise ApiError(404, "stmt-ref-unknown", f"{path} is not a file of this graph")
    count = len(body.decode("utf-8", errors="replace").splitlines())
    if raw > count:
        raise ApiError(
            400, "defect-line", f"line {raw} is beyond {path}, which has {count} lines (D-16)"
        )
    return raw


def ancestors_in(graph: list[dict[str, Any]], node_id: str) -> set[str]:
    """Every node of the target that depends on ``node_id`` transitively, from the committed
    ``graph.json`` rows, whose ``deps`` are already each dep read through its revisions (F08-T10)
    — the relation ``graph.ancestors`` reads from the tree, where the gate checks it again."""
    edges = {str(n["node_id"]): [str(d) for d in n.get("deps") or []] for n in graph}
    found: set[str] = set()
    todo = [node_id]
    while todo:
        below = todo.pop()
        for candidate, deps in edges.items():
            if below in deps and candidate not in found and candidate != node_id:
                found.add(candidate)
                todo.append(candidate)
    return found


def check_ancestor(
    ctx: Context, raw: Any, *, defect_class: str, target_id: str, stmt_ref: str
) -> str | None:
    """F08-T17: a ``circular-decomposition`` claim names a node above the one it sits under, and
    no other claim names one. The exhibit's type is the gate's to check, in the sandbox (C9)."""
    if defect_class != CIRCULAR_CLASS:
        if raw is None:
            return None
        raise ApiError(
            400,
            "circular-ancestor",
            f"ancestor belongs to a {CIRCULAR_CLASS} claim; a {defect_class} claim names none",
        )
    if stmt_ref.startswith(DEFS_PREFIX):
        raise ApiError(
            400, "circular-ancestor", f"a {CIRCULAR_CLASS} claim is about a node, not a defs/ file"
        )
    if not isinstance(raw, str) or not raw:
        raise ApiError(
            400,
            "circular-ancestor",
            f"a {CIRCULAR_CLASS} claim names `ancestor`: a node that depends on {stmt_ref}; the "
            f"exhibit proves `<ancestor's statement> → <{stmt_ref}'s statement>`",
        )
    above = ancestors_in(precheck.graph_doc(ctx).get(target_id, []), stmt_ref)
    if raw not in above:
        raise ApiError(
            400,
            "circular-ancestor",
            f"{raw} does not depend on {stmt_ref}, even through revisions; name one of: "
            f"{', '.join(sorted(above)) or 'none (nothing depends on this node)'}",
            details={"ancestors": sorted(above)},
        )
    return raw


#: F05-T8: the fields ``POST /defect-claims`` reads; any other top-level key is refused.
DEFECT_FIELDS: tuple[str, ...] = ("stmt_ref", "class", "line", "exhibit", "ancestor")


async def post_defect_claims(ctx: Context, request: Request) -> Response:
    """R7: D-16's pre-triage, then an append the gate re-checks the same way."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, DEFECT_FIELDS)
    defect_class = check_class(fields.get("class"), "class", DEFECT_CLAIM_CLASSES)
    target_id, stmt_ref, referenced, facts = resolve_ref(ctx, fields.get("stmt_ref"))
    line = check_line(ctx, fields.get("line"), referenced)
    exhibit = exhibit_text(fields, required=True)
    ancestor = check_ancestor(
        ctx,
        fields.get("ancestor"),
        defect_class=defect_class,
        target_id=target_id,
        stmt_ref=stmt_ref,
    )
    schema_id = DEFECT_SCHEMA if ancestor is None else CIRCULAR_SCHEMA
    doc: dict[str, Any] = {
        "schema": schema_id,
        "stmt_ref": stmt_ref,
        "class": defect_class,
        "line": line,
        "exhibit": exhibit,
        "contributor": identity.pseudonym,
        "date": clockmod.render(ctx.clock.now())[:10],
    }
    if ancestor is not None:
        doc["ancestor"] = ancestor
    appends.validated(doc, schema_id)
    also_open = known_state(ctx, defect_class, stmt_ref, facts)
    name = appends.record_name(ctx, identity)
    if stmt_ref.startswith(DEFS_PREFIX):
        path = f"targets/{target_id}/{DEFS_PREFIX}defects/{name}.yaml"
    else:
        path = appends.node_dir(target_id, stmt_ref) + f"defects/{name}.yaml"
    body = appends.append_pr(
        ctx,
        identity,
        path=path,
        content=yaml.safe_dump(doc, sort_keys=True, allow_unicode=True),
        subject=f"defect claim: {stmt_ref}",
        what="defect claim",
        kind="defect-claim",
        target_id=target_id,
        node_id=None if stmt_ref.startswith(DEFS_PREFIX) else stmt_ref,
        defect_class=defect_class,
    )
    if also_open:
        body["also_open"] = also_open
    return JSONResponse(body, status_code=201)
