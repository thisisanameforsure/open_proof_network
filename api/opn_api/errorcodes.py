"""``GET /errors.json`` (F05-T23; F13-T29): every error code, what it means and what to do.

The catalog is ``opn_gate.codes``, held to the source of the gate and the service by a test, so
this route serves a table that cannot lag the code it describes. Network documentation, open
like ``/dco.json`` and ``/hosted-checkers.json``, with no D-35 row: it records nothing and changes
nothing. ``?prefix=`` keeps the codes that start with it, which is what ``list_error_codes``
passes through.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_gate import codes

if TYPE_CHECKING:
    from opn_api.app import Context

#: The catalog changes only with a deploy, so a client and a CDN may keep it for a while.
CACHE_CONTROL = "public, max-age=3600"


async def get_errors(ctx: Context, request: Request) -> Response:
    prefix = request.query_params.get("prefix") or None
    return JSONResponse(codes.document(prefix), headers={"Cache-Control": CACHE_CONTROL})
