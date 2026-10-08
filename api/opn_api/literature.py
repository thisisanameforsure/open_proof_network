"""The literature routes (D-3, D-25, D-32 v3.35; F05-T29, F23-T12).

``POST /literature`` lets any contributor say what the literature says of a statement — ``open``,
``known`` or ``elementary``, with the references that support it and a summary — as an unsigned
``literature/v1`` record attributed to the token's identity (D-23) and opened on the node's
``literature/<ts>-<contributor>.yaml`` through the append machinery (one target per pull request,
the same-second rule, the duplicate rule). It is a proposal: the pull request names the target's
active stewards as the people whose confirmation it awaits, and says a curator may confirm too.
That is the amendment's notification — the record is on the graph the moment it merges, and the
person it waits for sees it next time they sign in.

``POST /literature/confirm`` is the signed half (F23-T12): an active steward of the node's target
or a listed curator — signed in on the site, or a bearer whose identity is a GitHub login —
confirms a proposal by naming it in ``confirms``, or states the status themselves (``confirms``
null). The service writes the record as that login and signs it with the network's approval key
over the canonical body the gate verifies, exactly as ``POST /stewards`` and ``POST /approvals``
do; whether the signer's role holds is the gate's to check at the merge.

A literature status is a fact about the literature, never about difficulty (D-25): it earns
nothing, changes no status, blocks nothing and ranks nothing. Nothing here interpolates the
contributor's text into anything but the file it is written to (C9).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import appends, pending, ratelimit, session, stewards, submissions
from opn_api import clock as clockmod
from opn_api import identity as identitymod
from opn_api.app import ApiError

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

SCHEMA = "literature/v1"
DIR = "literature"
STATUSES: tuple[str, ...] = ("open", "known", "elementary")
REFERENCE_FIELDS: frozenset[str] = frozenset({"title", "url", "note"})
MAX_REFERENCES = 20  # literature/v1's cap, named here so the refusal can say it
#: F05-T8: what ``POST /literature`` reads; any other top-level key is refused.
FIELDS: tuple[str, ...] = ("node_id", "status", "references", "summary", "model_and_tooling")
#: A record named relative to the node, as ``confirms`` and the products name one.
RECORD_RE = re.compile(r"^literature/[^/]+\.ya?ml$")


def bad(message: str, field: str) -> ApiError:
    return ApiError(400, "arguments-invalid", message, details={"field": field})


# --- the shared shape ----------------------------------------------------------------------------


def checked_status(raw: Any) -> str:
    if raw not in STATUSES:
        raise bad(
            "status is one of " + ", ".join(STATUSES) + ": what the literature says of the "
            "statement (D-25 v3.35), never how hard it is",
            "status",
        )
    return str(raw)


def checked_references(raw: Any) -> list[dict[str, Any]]:
    """The references as the schema shapes them: one to twenty objects, each a ``title`` with
    ``url`` (null or ``https://``) and ``note`` (null or a sentence). The caps on each string are
    the schema's and are checked with the record (``appends.validated``)."""
    if not isinstance(raw, list) or not raw:
        raise bad(
            "references is a non-empty list of {title, url, note}: what supports the status, "
            "even for open (where the problem is listed)",
            "references",
        )
    if len(raw) > MAX_REFERENCES:
        raise bad(f"references holds at most {MAX_REFERENCES} entries", "references")
    out: list[dict[str, Any]] = []
    for i, ref in enumerate(raw):
        where = f"references[{i}]"
        if not isinstance(ref, dict) or not set(ref) <= REFERENCE_FIELDS:
            raise bad(f"{where} is an object with title, url and note", where)
        title = ref.get("title")
        if not isinstance(title, str) or not title.strip():
            raise bad(f"{where}.title is required: a non-empty string", f"{where}.title")
        url = ref.get("url")
        if url is not None and (not isinstance(url, str) or not url.startswith("https://")):
            raise bad(f"{where}.url is null or an https:// URL", f"{where}.url")
        note = ref.get("note")
        if note is not None and not isinstance(note, str):
            raise bad(f"{where}.note is null or a sentence", f"{where}.note")
        out.append({"title": title, "url": url, "note": note})
    return out


def checked_summary(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise bad("summary is required: what is known, in your words", "summary")
    return raw


def record_body(fields: dict[str, Any]) -> dict[str, Any]:
    """The fields the caller chose — status, references, summary — checked; also what the
    duplicate rule compares (F07-T35), before the service adds who and when."""
    return {
        "status": checked_status(fields.get("status")),
        "references": checked_references(fields.get("references")),
        "summary": checked_summary(fields.get("summary")),
    }


def record_path(target_id: str, node_id: str, stamp: str, contributor: str) -> str:
    return appends.node_dir(target_id, node_id) + f"{DIR}/{stamp}-{contributor}.yaml"


def render(doc: dict[str, Any]) -> str:
    """The file as it lands: the schema's field order, so a reader meets the status first."""
    return str(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))


def awaiting(ctx: Context, target_id: str) -> str:
    """The notification (v3.35): the target's active stewards by login, or that it has none;
    a curator may confirm either way."""
    logins = session.active_stewards(session.steward_records(ctx, target_id))
    if logins:
        names = ", ".join(f"`{login}`" for login in logins)
        who = (
            f"awaiting confirmation by {names} (the stewards of `{target_id}`); a curator may "
            "confirm it too"
        )
    else:
        who = f"`{target_id}` has no steward, so only a curator can confirm it"
    return (
        f"\nThis is a proposal: {who}, by a signed record of their own (D-25 v3.35). Until then "
        "the products show it as proposed.\n"
    )


# --- POST /literature ----------------------------------------------------------------------------


async def post_literature(ctx: Context, request: Request) -> Response:
    """F05-T29: an unsigned proposal, attributed to the caller, in its own pull request."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, FIELDS)
    node_id, target_id = appends.node_target(ctx, fields)
    chosen = record_body(fields)
    written = appends.written_record(chosen)
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "node": node_id,
        "contributor": identity.pseudonym,
        "date": clockmod.render(ctx.clock.now()),
        **chosen,
        "model_and_tooling": appends.declared(fields.get("model_and_tooling")),
        "confirms": None,
        "via": None,
        "key": None,
        "signature": None,
    }
    appends.validated(doc, SCHEMA)
    path = record_path(target_id, node_id, appends.stamp(ctx), identity.pseudonym)
    return JSONResponse(
        appends.append_pr(
            ctx,
            identity,
            path=path,
            content=render(doc),
            subject=f"literature: {node_id}",
            what="literature record",
            kind="literature",
            target_id=target_id,
            node_id=node_id,
            written=written,
            extra_body=awaiting(ctx, target_id),
        ),
        status_code=201,
    )


# --- POST /literature/confirm --------------------------------------------------------------------


#: F05-T8: what ``POST /literature/confirm`` reads; any other top-level key is refused.
CONFIRM_FIELDS: tuple[str, ...] = ("node_id", "record", "status", "references", "summary")
KIND_CONFIRMATION = "literature-confirmation"


def may_confirm(ctx: Context, target_id: str, login: str) -> None:
    """D-25, D-32 v3.35: an active steward of the target or a listed curator; anyone else is
    403, and nothing opens."""
    if session.is_curator(ctx, login) or session.is_steward(ctx, target_id, login):
        return
    raise ApiError(
        403,
        "not-steward-or-curator",
        f"{login} is neither an active steward of {target_id} nor a listed curator; only they "
        "may confirm a literature status (D-25, D-32 v3.35)",
    )


def checked_record(ctx: Context, target_id: str, node_id: str, raw: Any) -> str | None:
    """``record`` as ``confirms`` will carry it: null, or ``literature/<file>`` that is on the
    node at the commit the service reads (404 ``not-found`` naming the path otherwise) and is a
    literature record (400 otherwise)."""
    if raw is None:
        return None
    if not isinstance(raw, str) or not RECORD_RE.match(raw) or ".." in raw:
        raise bad(
            "record is null (you state the status yourself) or the proposal you confirm, "
            "relative to the node: literature/<timestamp>-<contributor>.yaml",
            "record",
        )
    path = appends.node_dir(target_id, node_id) + raw
    found = pending.optional_committed(ctx, path)
    if found is None:
        raise ApiError(
            404,
            "not-found",
            f"{node_id} has no merged literature record {raw}; a confirmation names a proposal "
            "that is on the graph, or null to state the status yourself",
            details={"path": path},
        )
    try:
        doc = yaml.safe_load(found)
    except yaml.YAMLError:
        doc = None
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise bad(f"{raw} is not a {SCHEMA} record; a confirmation names a proposal", "record")
    return raw


async def post_confirm(ctx: Context, request: Request) -> Response:
    """F23-T12: one signed confirmation, by the approval key, in its own pull request. The
    signer is the session's or the bearer's GitHub login (``stewards.github_login``), the key is
    read where ``POST /stewards`` reads it, and the body is signed as every approval-key record
    is (``stewards.sign_record``)."""
    held: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, CONFIRM_FIELDS)
    login = stewards.github_login(held)
    node_id, target_id = appends.node_target(ctx, fields)
    chosen = record_body(fields)
    private, public = stewards.approval_key(ctx)
    ratelimit.enforce(
        ctx,
        "literature-confirm",
        login.casefold(),
        limit=ctx.settings.approvals_per_hour,
        seconds=ratelimit.HOUR_S,
    )
    may_confirm(ctx, target_id, login)
    confirms = checked_record(ctx, target_id, node_id, fields.get("record"))
    doc = stewards.sign_record(
        {
            "schema": SCHEMA,
            "node": node_id,
            "contributor": login,
            "date": clockmod.render(ctx.clock.now()),
            **chosen,
            "model_and_tooling": None,
            "confirms": confirms,
            "via": stewards.VIA,
        },
        private,
        public,
    )
    appends.validated(doc, SCHEMA)
    path = record_path(target_id, node_id, appends.stamp(ctx), login)
    body = appends.append_pr(
        ctx,
        held,
        path=path,
        content=render(doc),
        subject=f"literature: {node_id} confirmed by {login}",
        what="literature confirmation",
        kind=KIND_CONFIRMATION,
        target_id=target_id,
        node_id=node_id,
        written=f"{node_id} {confirms} {chosen['status']} {login}",
    )
    return JSONResponse(stewards.receipt(body, submissions.APPEND_BRANCH_PREFIX), status_code=201)
