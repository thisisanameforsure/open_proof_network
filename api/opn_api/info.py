"""``GET /info.json`` (F05-R6; D-28 ``server_info``): the committed ``info.json`` with the
rate-limit policy in force filled in, validated against ``info/v1``."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import frontier
from opn_gate import schemas

if TYPE_CHECKING:
    from opn_api.app import Context

INFO_PATH = "info.json"
INFO_SCHEMA = "info/v1"


async def get_info(ctx: Context, request: Request) -> Response:
    doc = json.loads(frontier.committed(ctx, INFO_PATH))
    doc["rate_limit_policy"] = ctx.settings.rate_limit_policy()
    return JSONResponse(schemas.validate(doc, INFO_SCHEMA))
