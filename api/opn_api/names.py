"""``POST /me/name``: a contributor's display name, for their own pseudonym and no other (F25-R6,
R15; D-3, D-19, D-35 v3.37).

A bearer — any identity, since the pseudonym is the identity (D-19) — records the name it chooses
to be shown by where the network names its contributors outside itself (a registration's authors,
D-19 v3.37), with an optional link, or withdraws it with a null name. The service writes
``names/<pseudonym>.yaml`` (``display-name/v1``) for the bearer's pseudonym — there is no field to
name another — signs it with the network's approval key over the canonical body the gate verifies
(``stewards.sign_record``, as every approval-key record is signed), and opens it on an ``append/``
branch the merge actor takes as it is. One file per pseudonym: a later record replaces it, which
the gate allows for this role alone, and the history is the trail (F25-Q6).

One writer at a time per pseudonym (the F22 rule for a chain's head): while a pull request of the
bearer's that writes the file is open and may merge, a second is refused ``409
display-name-in-review`` naming it, and nothing opens. A display name is a one-way publication
(F25 §7): the guide warns before the call, and nothing on the site reads it in this version.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import appends, duplicates, ratelimit, stewards, submissions
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_gate import names
from opn_gate import paths as gatepaths

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

SCHEMA = names.SCHEMA
KIND = "display-name"
#: F05-T8: what ``POST /me/name`` reads; any other top-level key — a pseudonym above all — is
#: refused.
FIELDS: tuple[str, ...] = ("name", "link")
NAME_MAX = 200  # display-name/v1's cap
LINK_MAX = 500  # display-name/v1's cap
ERROR_IN_REVIEW = "display-name-in-review"


def bad(message: str, field: str) -> ApiError:
    return ApiError(400, "arguments-invalid", message, details={"field": field})


def checked(fields: dict[str, Any]) -> tuple[str | None, str | None]:
    """(name, link): the name a string of 1 to 200 characters or null (a withdrawal, which takes
    no link); the link null or an https:// URL of at most 500 characters."""
    if "name" not in fields:
        raise bad("name is required: the display name, or null to withdraw it", "name")
    name = fields["name"]
    if name is not None and (not isinstance(name, str) or not name.strip() or len(name) > NAME_MAX):
        raise bad(f"name is null or the display name, 1 to {NAME_MAX} characters", "name")
    link = fields.get("link")
    if link is not None and (
        not isinstance(link, str) or not link.startswith("https://") or len(link) > LINK_MAX
    ):
        raise bad(f"link is null or an https:// URL of at most {LINK_MAX} characters", "link")
    if name is None and link is not None:
        raise bad("a withdrawal (name null) carries no link", "link")
    return name, link


def in_review(ctx: Context, pseudonym: str) -> None:
    """One writer per pseudonym: the bearer's own open pull request writing the file, if one
    still stands (``duplicates.blocks``), refuses a second with its number."""
    for found in ctx.store.list_open_submissions():
        if found.kind != KIND or found.pseudonym != pseudonym:
            continue
        if duplicates.blocks(ctx, found):
            raise ApiError(
                409,
                ERROR_IN_REVIEW,
                f"pull request #{found.pr_number} already writes names/{pseudonym}.yaml and may "
                "still merge; one writer at a time per pseudonym (D-3 v3.37)",
                details={
                    "pr_number": found.pr_number,
                    "pr_url": found.pr_url,
                    "submission_id": found.id,
                },
            )


def render(doc: dict[str, Any]) -> str:
    return str(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))


async def post_me_name(ctx: Context, request: Request) -> Response:
    """R15: one display-name record for the bearer's pseudonym, signed with the approval key, in
    its own pull request."""
    held: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, FIELDS)
    name, link = checked(fields)
    private, public = stewards.approval_key(ctx)
    ratelimit.enforce(
        ctx,
        KIND,
        held.pseudonym.casefold(),
        limit=ctx.settings.stewards_per_day,
        seconds=ratelimit.DAY_S,
    )
    in_review(ctx, held.pseudonym)
    doc = stewards.sign_record(
        {
            "schema": SCHEMA,
            "pseudonym": held.pseudonym,
            "name": name,
            "link": link,
            "date": ctx.clock.now().strftime("%Y-%m-%d"),
            "via": stewards.VIA,
        },
        private,
        public,
    )
    appends.validated(doc, SCHEMA)
    path = f"{names.DIR}/{held.pseudonym}.yaml"
    body = appends.append_pr(
        ctx,
        held,
        path=path,
        content=render(doc),
        subject=f"display name: {held.pseudonym}",
        what="display name",
        kind=KIND,
        target_id=gatepaths.GRAPH_SCOPE,  # a graph-root file, scoped as the gate scopes it
        node_id=None,
        written=f"{held.pseudonym} {name} {link}",
        hold_name=False,  # one fixed path per pseudonym: ``in_review`` is the one-writer rule
    )
    return JSONResponse(stewards.receipt(body, submissions.APPEND_BRANCH_PREFIX), status_code=201)
