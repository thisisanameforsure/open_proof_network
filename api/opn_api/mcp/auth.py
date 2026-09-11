"""Bearer verification for the MCP surface (F09-R2; D-28).

The SDK's ``TokenVerifier`` protocol is implemented over F05's token store: the same salted
hash and the same lookup ``opn_api.auth.authenticate`` makes, minus the 401 — a missing or
unknown token leaves the request anonymous, because D-28's read tools are unauthenticated and
must keep working. The SDK's bearer backend puts the verified token in a context variable;
a write tool reads it back through ``bearer`` and, finding none, answers the SDK's own
unauthorized body (``UNAUTHORIZED``) without touching its endpoint.

The SDK's ``AuthSettings`` wrapper is deliberately not used: it gates the whole transport,
``tools/list`` included, which is the opposite of R2 (Q3). The raw token lives in memory for
one request, forwarded in-process to the endpoint that needs it, and is never logged (C8).
"""

from __future__ import annotations

import hmac
from typing import TYPE_CHECKING, Any

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken

from opn_api import auth

if TYPE_CHECKING:
    from opn_api.app import Context

#: The body the SDK's ``RequireAuthMiddleware`` sends for a request without a valid bearer,
#: reproduced verbatim so a client sees one unauthorized shape on both paths (R2).
UNAUTHORIZED: dict[str, Any] = {
    "error": "invalid_token",
    "error_description": "Authentication required",
}
UNAUTHORIZED_STATUS = 401
WRITE_SCOPE = "write"


class StoreTokenVerifier:
    """``TokenVerifier`` over the F05 store: a token resolves to its identity or to nothing."""

    def __init__(self, ctx: Context) -> None:
        self._ctx = ctx

    async def verify_token(self, token: str) -> AccessToken | None:
        ctx = self._ctx
        if ctx.missing or not token:
            return None
        digest = auth.token_hash(ctx.settings.token_secret or "", token)
        record = ctx.store.get_token(digest)
        if record is None or not hmac.compare_digest(record.token_hash, digest) or record.revoked:
            return None
        identity = ctx.store.get_identity(record.identity_id)
        if identity is None:
            return None
        return AccessToken(
            token=token, client_id=identity.id, scopes=[WRITE_SCOPE], subject=identity.id
        )


def bearer() -> str | None:
    """The verified bearer of the current MCP request, or ``None`` for an anonymous caller."""
    access = get_access_token()
    return access.token if access is not None else None
