"""mcpfix WB1 item 6 (testers 2026-11-25, t257b item 3): check_lean says which ``okay`` a
skeleton should aim for. The same sorry'd skeleton read ``okay: false`` in verify and, in check,
``okay: false`` beside ``result.okay: true``, and nothing said which one a skeleton is held to."""

from __future__ import annotations

from opn_api.mcp import writes


def test_check_lean_says_what_a_skeleton_aims_for() -> None:
    (tool,) = [t for t in writes.TOOLS if t.name == "check_lean"]
    text = tool.description
    assert "skeleton" in text
    assert "`result.okay: true` in check" in text
    assert "sorry-present" in text
    assert "verify reports sorry as failure" in text
    assert "lines of your text" in text  # mcpfix WB1 item 3: positions are the caller's
