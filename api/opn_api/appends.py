"""The append routes (F07-R9, R11, R14; D-13, D-14, D-31, D-34).

``POST /postmortems``, ``POST /annexes`` and ``POST /approach-records`` put a record into the
graph through a pull request the gate merges on schema and path checks alone, because none of
them claims anything a kernel could check (F07-Q4). One rule holds all three: the caller supplies
the content, the service supplies the identity, and the file lands at the path its decision
fixes — ``attempts/`` for a postmortem (D-13), ``annex/<hash>.md`` for an annex (D-31),
``targets/<id>/approaches/`` for an approach record (D-14).

Free text is capped and stored verbatim (R14): the caps come from the schema itself, so there is
one number per field and it is the one the gate enforces. Nothing here interpolates contributor
text into a command, a template or a query — it is written to a file and served, later, as
demarcated untrusted data (D-28, C9).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import clock as clockmod
from opn_api import frontier, precheck, submissions
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_gate import schemas

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

log = logging.getLogger(__name__)

POSTMORTEM_SCHEMA = "postmortem/v1"
ANNEX_SCHEMA = "annex/v1"
APPROACH_SCHEMA = "approach-record/v1"
ANNEX_MAX_BYTES = 64 * 1024  # F07 §6
DEFAULT_LICENCE = "CC-BY-4.0"
LICENCES: tuple[str, ...] = ("CC-BY-4.0", "CDLA-Permissive-2.0", "Apache-2.0")
FILE_TIMESTAMP = "%Y%m%dT%H%M%SZ"  # sorts lexically, and is a legal file name everywhere


def stamp(ctx: Context) -> str:
    return ctx.clock.now().strftime(FILE_TIMESTAMP)


def record_name(ctx: Context, identity: Identity) -> str:
    """D-13's ``<timestamp>-<contributor>``. Two records in one second by one identity collide;
    the gate's append-only rule then rejects the second as a modification, which is a visible
    refusal rather than a silent overwrite (C7)."""
    return f"{stamp(ctx)}-{identity.pseudonym}"


def check_caps(doc: dict[str, Any], schema_id: str) -> None:
    """R14, AC19: every capped string field, against the cap its own schema publishes.

    The cap is checked here rather than left to validation so the refusal can name the field and
    the number without echoing the text back — a 5,000-character detail must not travel twice.
    """
    properties = schemas.load_schema(schema_id).get("properties", {})
    for field, spec in properties.items():
        cap = spec.get("maxLength") if isinstance(spec, dict) else None
        value = doc.get(field)
        if isinstance(cap, int) and isinstance(value, str) and len(value) > cap:
            raise ApiError(
                400,
                "field-too-long",
                f"{field} is {len(value)} characters; the cap is {cap}",
            )


def validated(doc: dict[str, Any], schema_id: str) -> dict[str, Any]:
    """The record, or a 400 naming the first field that does not satisfy its schema."""
    check_caps(doc, schema_id)
    problems = schemas.violations(doc, schema_id)
    if problems:
        first = problems[0]
        raise ApiError(400, "record-invalid", f"{first.path}: {first.message}")
    return doc


def as_mapping(raw: Any, field: str) -> dict[str, Any]:
    """The record the caller sent, as an object — JSON already, or a YAML document."""
    if isinstance(raw, str):
        try:
            raw = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise ApiError(400, f"{field}-invalid", f"{field} is not parseable YAML") from exc
    if not isinstance(raw, dict):
        raise ApiError(400, f"{field}-invalid", f"{field} must be an object or a YAML document")
    return dict(raw)


def node_target(ctx: Context, fields: dict[str, Any]) -> tuple[str, str]:
    node_id = fields.get("node_id")
    if not isinstance(node_id, str) or not node_id:
        raise ApiError(400, "node-id-missing", "node_id is required")
    facts = precheck.node_facts(ctx, node_id)
    return node_id, str(facts["target_id"])


def node_dir(target_id: str, node_id: str) -> str:
    return f"targets/{target_id}/nodes/{node_id}/"


def append_pr(  # noqa: PLR0913 — one pull request, described
    ctx: Context, identity: Identity, *, path: str, content: str, subject: str, what: str
) -> dict[str, Any]:
    """One appended file, one branch, one pull request (R11, R2)."""
    append_id = identitymod.new_ulid(ctx.clock.now())
    pr = submissions.open_pr(
        ctx,
        identity,
        branch=submissions.APPEND_BRANCH_PREFIX + append_id,
        files={path: content},
        subject=subject,
        title=subject,
        body=(
            f"A {what} appended through the Open Proof Network service by "
            f"`{identity.pseudonym}`. It claims nothing: the gate checks its path and its "
            f"schema (F07-R9).\n\n`{path}`\n"
        ),
    )
    log.info("%s %s opened %s for %s", what, append_id, pr.url, identity.id)
    return {"id": append_id, "path": path, "pr_url": pr.url, "pr_number": pr.number}


# --- POST /postmortems (D-13) ---------------------------------------------------------------------


async def post_postmortems(ctx: Context, request: Request) -> Response:
    """R11: a typed failed attempt, contributed under the caller's identity (AC15)."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request)
    node_id, target_id = node_target(ctx, fields)
    doc = as_mapping(fields.get("yaml"), "yaml")
    doc["schema"] = POSTMORTEM_SCHEMA
    doc["node"] = node_id
    doc["contributor"] = identity.pseudonym  # AC15: the caller, whatever the record said
    validated(doc, POSTMORTEM_SCHEMA)
    path = node_dir(target_id, node_id) + f"attempts/{record_name(ctx, identity)}.yaml"
    content = yaml.safe_dump(doc, sort_keys=True, allow_unicode=True)
    return JSONResponse(
        append_pr(
            ctx,
            identity,
            path=path,
            content=content,
            subject=f"postmortem: {node_id}",
            what="postmortem",
        ),
        status_code=201,
    )


# --- POST /annexes (D-31) -------------------------------------------------------------------------


def check_licence(raw: Any) -> str:
    """D-23's amendment: annex prose is licensed by its author at submission, or not accepted."""
    if raw is None:
        return DEFAULT_LICENCE
    if raw not in LICENCES:
        raise ApiError(400, "licence-invalid", f"licence must be one of {', '.join(LICENCES)}")
    return str(raw)


def annex_file(doc: dict[str, Any], text: str) -> str:
    """The file as it lands: YAML front matter, then the prose exactly as it was sent (R14)."""
    head = yaml.safe_dump(doc, sort_keys=True, allow_unicode=True)
    body = text if text.endswith("\n") else text + "\n"
    return f"---\n{head}---\n{body}"


async def post_annexes(ctx: Context, request: Request) -> Response:
    """R11, AC14: the hash a skeleton must cite is the file's, and it is the file's name too."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request)
    node_id, target_id = node_target(ctx, fields)
    text = fields.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ApiError(400, "text-missing", "text is required")
    if len(text.encode()) > ANNEX_MAX_BYTES:
        raise ApiError(
            400,
            "field-too-long",
            f"the annex is {len(text.encode())} bytes; the cap is {ANNEX_MAX_BYTES}",
        )
    front = {
        "schema": ANNEX_SCHEMA,
        "node": node_id,
        "contributor": identity.pseudonym,
        "licence": check_licence(fields.get("licence")),
        "date": clockmod.render(ctx.clock.now()),
        "model_and_tooling": _declared(fields.get("model_and_tooling")),
    }
    validated(front, ANNEX_SCHEMA)
    content = annex_file(front, text)
    digest = schemas.content_hash(content.encode())
    path = node_dir(target_id, node_id) + f"annex/{digest}.md"
    body = append_pr(
        ctx,
        identity,
        path=path,
        content=content,
        subject=f"annex: {node_id}",
        what="annex",
    )
    body["hash"] = digest  # what a skeleton cites (D-31)
    return JSONResponse(body, status_code=201)


def _declared(raw: Any) -> str | None:
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        raise ApiError(400, "tooling-invalid", "model_and_tooling must be a string")
    return raw


# --- POST /approach-records (D-14) ----------------------------------------------------------------


def known_target(ctx: Context, target_id: Any) -> str:
    if not isinstance(target_id, str) or not target_id:
        raise ApiError(400, "target-id-missing", "target_id is required")
    index = json.loads(frontier.committed(ctx, "targets/index.json"))
    if not any(t.get("target_id") == target_id for t in index.get("targets", [])):
        raise ApiError(404, "target-unknown", f"{target_id} is not a target of this graph")
    return target_id


async def post_approach_records(ctx: Context, request: Request) -> Response:
    """R11: a strategy-level verdict for a route that never reached a statement (D-14)."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request)
    target_id = known_target(ctx, fields.get("target_id"))
    doc = as_mapping(fields.get("record"), "record")
    doc["schema"] = APPROACH_SCHEMA
    doc["target"] = target_id
    doc["contributor"] = identity.pseudonym
    doc.setdefault("date", clockmod.render(ctx.clock.now()))
    doc.setdefault("pinned_mathlib_sha", None)
    doc.setdefault("model_and_tooling", None)
    validated(doc, APPROACH_SCHEMA)
    path = f"targets/{target_id}/approaches/{record_name(ctx, identity)}.yaml"
    return JSONResponse(
        append_pr(
            ctx,
            identity,
            path=path,
            content=yaml.safe_dump(doc, sort_keys=True, allow_unicode=True),
            subject=f"approach record: {target_id}",
            what="approach record",
        ),
        status_code=201,
    )
