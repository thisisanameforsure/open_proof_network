"""``GET /`` (F05-T12, Q13): what this service offers, read off the routes table itself.

A caller who arrives at the hostname with nothing else gets every route, whether it needs a
bearer and what it is for, plus the two places the rest is written down: the contributor guide
in the graph repository and the MCP endpoint. Network configuration, open like ``/dco.json``;
``info.json`` stays the graph's product (``info/v1`` is closed, D-34).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import routes
from opn_api.mcp import server as mcpmod

if TYPE_CHECKING:
    from opn_api.app import Context


async def get_index(ctx: Context, request: Request) -> Response:
    settings = ctx.settings
    return JSONResponse(
        {
            "service": "Open Proof Network service",
            "authoritative_for": "nothing: the graph repository is the record (D-35)",
            "guide": f"https://github.com/{settings.graph_repo}/blob/{settings.graph_branch}"
            "/AGENTS.md",
            "mcp": mcpmod.MCP_PATH,
            "routes": [
                {
                    "method": spec.method,
                    "path": spec.path,
                    "auth": "bearer" if spec.authenticated else "none",
                    "purpose": routes.PURPOSES[spec.label],
                }
                for spec in routes.ROUTES
            ],
        }
    )
