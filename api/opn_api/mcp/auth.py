"""Bearer verification for the MCP surface (F09-R2; D-28).

The SDK's ``TokenVerifier`` protocol is implemented over F05's token store: the same salted
hash and the same lookup ``opn_api.auth.authenticate`` makes, minus the 401 — a missing or
unknown token leaves the request anonymous, because D-28's read tools are unauthenticated and
must keep working. The SDK's bearer backend puts the verified token in a context variable;
the server reads it back through ``bearer`` and, finding none for a tool that needs one, answers
``UNAUTHORIZED`` without touching the endpoint.

The SDK's ``AuthSettings`` wrapper is deliberately not used: it gates the whole transport,
``tools/list`` included, which is the opposite of R2 (Q3). The raw token lives in memory for
one request, forwarded in-process to the endpoint that needs it, and is never logged (C8).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken

from opn_api import auth, precheck
from opn_api.app import ApiError

if TYPE_CHECKING:
    from opn_api.app import Context

log = logging.getLogger(__name__)

#: How the tutorial node is named when the graph cannot be read to name it.
TUTORIAL_UNNAMED = "the tutorial node (the node whose `tutorial` is true in get_target's graph)"


def tutorial_phrase(ctx: Context) -> str:
    """The tutorial node by name, ``<target>/<node>``, from the committed graphs at the time of
    asking (tester finding 2026-09-27: "the tutorial node" was never named, and list_frontier
    leaves it out because it is proved). Never a constant; an unreadable graph gives the generic
    words rather than failing the answer that carries them (C7)."""
    try:
        names = precheck.tutorial_nodes(ctx)
    except ApiError as exc:
        log.warning("tutorial node not named: %s", exc.message)
        return TUTORIAL_UNNAMED
    if not names:
        return TUTORIAL_UNNAMED
    return "the tutorial node " + ", ".join(f"`{n}`" for n in names)


def unauthorized_body(tutorial: str) -> dict[str, Any]:
    """The refusal body of a tool that needs a bearer and has none: the HTTP route's own shape
    and ``error`` (``opn_api.auth.authenticate``), so a client sees one unauthorized answer on
    both paths, with a message naming the way to a token that stays inside the MCP (F09-T6,
    D-19) and the node that way starts on."""
    return {
        "error": "unauthenticated",
        "message": (
            "this tool needs `Authorization: Bearer <token>`. To mint one without leaving the "
            f"MCP: run precheck_submission on {tutorial} with no token, poll get_precheck until "
            "it passes, then call get_token with proof {kind: tutorial, job_id, nonce}"
        ),
    }


def unauthorized(ctx: Context) -> dict[str, Any]:
    return unauthorized_body(tutorial_phrase(ctx))


#: The refusal in the words used when the tutorial node cannot be named.
UNAUTHORIZED: dict[str, Any] = unauthorized_body(TUTORIAL_UNNAMED)
UNAUTHORIZED_STATUS = 401
WRITE_SCOPE = "write"
#: The refusal a lapsed token earns at its endpoint (F05-T27, T29), and the verifier's mark for one.
EXPIRED = "token-expired"


class StoreTokenVerifier:
    """``TokenVerifier`` over the F05 store: a token resolves to its identity or to nothing."""

    def __init__(self, ctx: Context) -> None:
        self._ctx = ctx

    async def verify_token(self, token: str) -> AccessToken | None:
        """The F05 resolution (``opn_api.auth.resolve``): an unknown, revoked or renewed token is
        no token. A *lapsed* one (D-19 v3.29, F05-T29) is let through with no scope, so a tool
        forwards it and its endpoint answers ``401 token-expired`` with the way to recover,
        rather than the server answering "unauthenticated" as if it had never been a token at
        all. Nothing is granted by letting it through: every endpoint resolves the
        bearer again and refuses it."""
        ctx = self._ctx
        if ctx.missing or not token:
            return None
        try:
            _, identity = auth.resolve(ctx, token)
        except ApiError as refusal:
            if refusal.code != EXPIRED:
                return None
            return AccessToken(token=token, client_id=EXPIRED, scopes=[])
        return AccessToken(
            token=token, client_id=identity.id, scopes=[WRITE_SCOPE], subject=identity.id
        )


def bearer() -> str | None:
    """The verified bearer of the current MCP request, or ``None`` for an anonymous caller."""
    access = get_access_token()
    return access.token if access is not None else None
