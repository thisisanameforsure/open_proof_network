"""mcpfix (lead, 2026-11-25; t883 item 10): list_words_needed leaves out a subject whose words
merged and wait for the post-merge render.

The tester's witness gloss merged at 22:51Z and list_words_needed still listed the file as
`no-gloss` at 22:58Z, inviting a second writer. WB2's ``frontier.pending_words`` names such
subjects; the adapter drops them, and they come back only if the render shows them still lacking
words."""

# ruff: noqa: F811 — the imported fixture `h` is the parameter every test names
from __future__ import annotations

from api_fakes import TUTORIAL_NODE, Harness
from mcp_client import McpClient
from test_mcp_words_needed import h, rendered, tree  # noqa: F401 — the rendered two-target graph
from test_mcpfix_wb2_pending_render import MERGE, RENDERED, TARGET, gloss_record

FILE = f"targets/{TARGET}/nodes/{TUTORIAL_NODE}/Statement.lean"


def listed(h: Harness) -> list[str]:
    out = McpClient(h).ok("list_words_needed", {"target_id": TARGET, "limit": 200})
    return [str(r["file"]) for r in out["subjects"]]


def test_a_merged_gloss_awaiting_render_is_not_listed(h: Harness) -> None:
    assert FILE in listed(h)
    gloss_record(h, 12, f"nodes/{TUTORIAL_NODE}/Statement.lean")
    h.githost.ancestry[(MERGE, RENDERED)] = False
    assert FILE not in listed(h)


def test_once_rendered_the_products_decide_again(h: Harness) -> None:
    gloss_record(h, 12, f"nodes/{TUTORIAL_NODE}/Statement.lean")
    h.githost.ancestry[(MERGE, RENDERED)] = True
    assert FILE in listed(h)  # the fixture's products still lack it, so it is listed
