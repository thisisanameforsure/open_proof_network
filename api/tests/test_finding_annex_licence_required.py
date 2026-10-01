"""F05-T17 (bugs.md item 6, 2026-09-30): ``POST /annexes`` with no ``licence`` was accepted and
silently recorded as ``CC-BY-4.0``.

D-23's amendment says annex prose is licensed by its author at submission or not accepted;
``check_licence`` turned an absent field into the default, so a contributor who never chose a
licence had one chosen for them and the record said they did. The rule: a missing (or null)
``licence`` is refused ``400 licence-required`` naming the accepted values, nothing opens, and a
value outside the list is still ``licence-invalid``. The MCP tool's declared input schema requires
the field too, so an agent learns it from ``tools/list`` before calling; the adapter refuses the
call the way it refuses every missing required argument (F09-T10), and nothing is forwarded. The
guide's own annex example carries a licence, and a test holds it to that.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from api_fakes import TUTORIAL_NODE, Harness
from mcp_client import McpClient

from opn_api.appends import LICENCES
from opn_api.mcp.server import BY_NAME

GUIDE = Path(__file__).resolve().parents[2] / "gate" / "agents" / "AGENTS.md"
TEXT = "An informal argument: a conjunction is symmetric.\n"


def post(h: Harness, token: str, body: dict[str, Any]) -> Any:
    return h.client.post("/annexes", json=body, headers=h.auth(token))


def test_a_missing_licence_is_refused_and_nothing_opens(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = post(harness, token, {"node_id": TUTORIAL_NODE, "text": TEXT})
    assert r.status_code == 400, r.text
    doc = r.json()
    assert doc["error"] == "licence-required"
    for licence in LICENCES:
        assert licence in doc["message"], doc["message"]
    assert doc["details"] == {"accepted": list(LICENCES)}
    assert harness.githost.pushes == [] and harness.githost.pulls == []
    assert harness.store.list_open_submissions() == []


def test_a_null_licence_is_a_missing_one(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = post(harness, token, {"node_id": TUTORIAL_NODE, "text": TEXT, "licence": None})
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "licence-required"
    assert harness.githost.pushes == []


def test_a_licence_outside_the_list_is_still_invalid(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = post(harness, token, {"node_id": TUTORIAL_NODE, "text": TEXT, "licence": "MIT"})
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "licence-invalid"
    assert harness.githost.pushes == []


def test_the_licence_the_author_chose_is_what_the_record_says(harness: Harness) -> None:
    """Each accepted value lands in the front matter as given: no default stands in."""
    token = harness.token_for("code_alice", "alice")
    for n, licence in enumerate(LICENCES):
        r = post(
            harness, token, {"node_id": TUTORIAL_NODE, "text": f"{TEXT}{n}\n", "licence": licence}
        )
        assert r.status_code == 201, r.text
        _path, content = next(iter(harness.githost.pushes[-1].files.items()))
        front = yaml.safe_load(content.split("---\n")[1])
        assert front["licence"] == licence


def test_the_mcp_tool_requires_the_licence_and_forwards_nothing_without_it(
    harness: Harness,
) -> None:
    tool = BY_NAME["submit_informal_annex"]
    assert "licence" in tool.input_schema["required"], tool.input_schema["required"]
    assert tool.input_schema["properties"]["licence"]["enum"] == list(LICENCES)
    token = harness.token_for("code_alice", "alice")
    client = McpClient(harness)
    doc = client.failed(
        "submit_informal_annex", {"node_id": TUTORIAL_NODE, "text": TEXT}, token=token
    )
    assert "licence" in doc["message"], doc
    assert harness.githost.pushes == []
    opened = client.ok(
        "submit_informal_annex",
        {"node_id": TUTORIAL_NODE, "text": TEXT, "licence": "Apache-2.0"},
        token=token,
    )
    assert opened["body"]["pr_number"] == 1
    _path, content = next(iter(harness.githost.pushes[-1].files.items()))
    assert "licence: Apache-2.0" in content


def test_the_guide_example_carries_a_licence() -> None:
    """The guide is tested documentation: its ``/annexes`` request is built in one block, and
    that block names a licence from the list, so a contributor who pastes it is not refused."""
    text = GUIDE.read_text()
    start = text.index("annex-request.json")
    block = text[start : text.index("```", start)]
    assert any(f'"licence": "{licence}"' in block for licence in LICENCES), block
