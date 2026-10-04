"""``GET /info.json`` (F05-R6; D-28 ``server_info``): the committed ``info.json`` with what only
the service knows filled in — the rate-limit policy in force, and from ``info/v2`` (F05-T25) where
the contributor guide and the error-code catalog are — validated against the version the document
declares, constrained to the set below."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import frontier
from opn_gate import schemas

if TYPE_CHECKING:
    from opn_api.app import Context

INFO_PATH = "info.json"
#: The info versions this service will serve. The live graph publishes ``info/v1`` until its
#: re-pin, so what is pinned is the set (D-34), as it is for the frontier.
INFO_SCHEMAS: tuple[str, ...] = ("info/v1", "info/v2")
#: The versions that carry ``guide_url`` and ``errors_url`` (F05-T25).
URL_SCHEMAS: tuple[str, ...] = ("info/v2",)
#: The error-code catalog's route on this service (F13-T29, F05-T23).
ERRORS_PATH = "/errors.json"


def validate_info(doc: dict[str, Any]) -> dict[str, Any]:
    declared = str(doc.get("schema"))
    if declared not in INFO_SCHEMAS:
        msg = f"info.json declares {declared!r}; this service serves {', '.join(INFO_SCHEMAS)}"
        raise schemas.SchemaError(msg)
    return schemas.validate(doc, declared)


async def get_info(ctx: Context, request: Request) -> Response:
    doc = json.loads(frontier.committed(ctx, INFO_PATH))
    doc["rate_limit_policy"] = ctx.settings.rate_limit_policy()
    if doc.get("schema") in URL_SCHEMAS:
        # Configuration, never a literal hostname: the guide's URL and this service's origin.
        doc["guide_url"] = ctx.settings.guide_url
        doc["errors_url"] = ctx.settings.public_url + ERRORS_PATH
    return JSONResponse(validate_info(doc))
