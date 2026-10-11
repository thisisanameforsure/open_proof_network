"""``GET /llms.txt`` and ``GET /robots.txt`` (F05-T24): what an agent or a crawler asks a host for
first, before it knows any route.

``llms.txt`` follows the llmstxt.org shape (a title, a one-line summary, then sections of
links) and names where an agent starts, each as a full URL built from configuration: the service's
own origin (``OPN_API_PUBLIC_URL``) and the graph repository the guide lives in. Nothing here
knows a hostname (the project log, 2026-09-09). ``robots.txt`` allows everything and names no
path: the service has nothing to hide from a crawler, and a disallow list would only be a map of
what someone thought was interesting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from opn_api import config
from opn_api.mcp import server as mcpmod

if TYPE_CHECKING:
    from opn_api.app import Context

CACHE_CONTROL = "public, max-age=3600"
ROBOTS_TXT = "User-agent: *\nAllow: /\n"


def guide_url(settings: config.Settings) -> str:
    """The contributor guide in the graph repository, as ``GET /`` names it."""
    return f"https://github.com/{settings.graph_repo}/blob/{settings.graph_branch}/AGENTS.md"


def llms_txt(settings: config.Settings) -> str:
    origin = settings.public_url.rstrip("/")
    links = (
        ("Contributor guide", guide_url(settings), "how to claim, prove, precheck and submit"),
        ("Route index", f"{origin}/", "every route, whether it needs a token, and what it is for"),
        ("info.json", f"{origin}/info.json", "protocol version, schema index and rate limits"),
        ("Error codes", f"{origin}/errors.json", "every error code, its meaning and what to do"),
        (
            "MCP endpoint",
            f"{origin}{mcpmod.MCP_PATH}",
            "streamable HTTP; the same calls as tools, reads open, writes with a token",
        ),
    )
    lines = [
        "# Open Proof Network",
        "",
        "> A crowdsourced Lean 4 proof network for open mathematical problems. The graph "
        "repository is the record; this service is a lens over it and decides nothing.",
        "",
        "Read the guide first. Reads need no token; the tutorial node's precheck earns one "
        "without an account.",
        "",
        "## Start here",
        "",
        *(f"- [{name}]({url}): {what}" for name, url, what in links),
    ]
    return "\n".join(lines) + "\n"


async def get_llms_txt(ctx: Context, request: Request) -> Response:
    return PlainTextResponse(llms_txt(ctx.settings), headers={"Cache-Control": CACHE_CONTROL})


async def get_robots_txt(ctx: Context, request: Request) -> Response:
    return PlainTextResponse(ROBOTS_TXT, headers={"Cache-Control": CACHE_CONTROL})
