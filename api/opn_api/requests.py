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

from opn_api import appends, precheck, proposals
from opn_api import clock as clockmod
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_api.githost import GitHostError
from opn_gate import schemas

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


def check_class(raw: Any, field: str) -> str:
    """D-16 (1): a claim names a defect class from the taxonomy or it bounces."""
    if raw not in DEFECT_CLASSES:
        raise ApiError(
            400,
            "defect-class",
            f"{field} must be one of {', '.join(DEFECT_CLASSES)} (D-16's taxonomy; "
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


async def post_revision_requests(ctx: Context, request: Request) -> Response:
    """R6: a claim that a statement is defective, with evidence, for a curator to act on."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request)
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
        ),
        status_code=201,
    )


# --- POST /defect-claims (D-16) -------------------------------------------------------------------


def resolve_ref(ctx: Context, raw: Any) -> tuple[str, str, str]:
    """(target_id, stmt_ref as recorded, referenced path): a node id, or
    ``<target>/defs/<file>``."""
    if not isinstance(raw, str) or not raw:
        raise ApiError(400, "stmt-ref-missing", "stmt_ref is required")
    target_id, sep, rest = raw.partition("/")
    if sep and rest.startswith(DEFS_PREFIX):
        appends.known_target(ctx, target_id)
        return target_id, rest, f"targets/{target_id}/{rest}"
    if sep:
        raise ApiError(
            400, "stmt-ref-invalid", "stmt_ref is a node id, or <target>/defs/<file>.lean"
        )
    facts = precheck.node_facts(ctx, raw)
    target_id = str(facts["target_id"])
    return target_id, raw, f"targets/{target_id}/nodes/{raw}/Statement.lean"


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


async def post_defect_claims(ctx: Context, request: Request) -> Response:
    """R7: D-16's pre-triage, then an append the gate re-checks the same way."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request)
    defect_class = check_class(fields.get("class"), "class")
    target_id, stmt_ref, referenced = resolve_ref(ctx, fields.get("stmt_ref"))
    line = check_line(ctx, fields.get("line"), referenced)
    exhibit = exhibit_text(fields, required=True)
    doc: dict[str, Any] = {
        "schema": DEFECT_SCHEMA,
        "stmt_ref": stmt_ref,
        "class": defect_class,
        "line": line,
        "exhibit": exhibit,
        "contributor": identity.pseudonym,
        "date": clockmod.render(ctx.clock.now())[:10],
    }
    appends.validated(doc, DEFECT_SCHEMA)
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
    )
    return JSONResponse(body, status_code=201)
