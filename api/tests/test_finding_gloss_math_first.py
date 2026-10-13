"""F20-T16 (Q21): the gloss contract is math first.

Expert readers of erdos-1094 asked for a gloss to state what the Lean says the way a
mathematician would write it, and only then the prose. The guidance now says, in every place an
agent or a person meets it: a gloss opens with the statement in standard mathematical notation
in LaTeX (``$$…$$`` or ``$…$``), mirroring the Lean exactly, every hypothesis and quantifier;
then at most a few short lines on the Lean conventions that change its meaning (floor division,
``Nat.minFac`` at 0 and 1, truncated subtraction, ``%``, guards such as ``0 < k``); then any prose,
last. Guidance only: no schema, no gate rule (Q21). The worked example in the guide is checked
with ``glosses.opens_with_math``, the same function the audit tool uses.
"""

from __future__ import annotations

import re
from pathlib import Path

from opn_api.mcp import server
from opn_api.mcp.server import BY_NAME
from opn_gate import cli, glosses

REPO = Path(__file__).resolve().parents[2]
GUIDE = REPO / "gate" / "agents" / "AGENTS.md"
DOCS = REPO / "site" / "opn_site" / "templates" / "docs.html"
#: The words every copy of the rule carries.
RULE_WORDS = ("LaTeX", "Lean convention")


def flat(text: str) -> str:
    return " ".join(text.split())


def entry_task() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index("### Entry task: write the words for a statement")
    return text[start : text.index("### Reading an outline", start)]


def test_the_guides_write_step_puts_the_math_first() -> None:
    task = entry_task()
    step = flat(task[task.index("3. **Write the words.**") : task.index("4. **Submit it**")])
    for word in (*RULE_WORDS, "opens with", "every hypothesis", "quantifier", "prose"):
        assert word in step, (word, step)
    assert step.index("LaTeX") < step.index("Lean convention") < step.rindex("prose"), step


def test_the_guides_worked_example_opens_with_math() -> None:
    task = entry_task()
    example = task[task.index("4. **Submit it**") :]
    m = re.search(r"^text = (.*?)\nprint\(", example, re.M | re.S)
    assert m is not None
    text = eval(m.group(1))  # noqa: S307 — a string literal from the repository's own guide
    assert glosses.opens_with_math(text), text


def test_the_mcp_tool_says_it() -> None:
    tool = BY_NAME["submit_gloss"]
    desc = flat(tool.description or "")
    assert "LaTeX" in desc, desc
    text_param = flat(tool.input_schema["properties"]["text"]["description"])
    for word in RULE_WORDS:
        assert word in text_param, (word, text_param)


def test_the_handshake_says_it() -> None:
    words = flat(server.instructions("the tutorial"))
    assert "submit_gloss" in words and "LaTeX" in words, words


def test_the_docs_page_says_it() -> None:
    words = flat(re.sub(r"<[^>]+>", " ", DOCS.read_text(encoding="utf-8")))
    start = words.index("The words.")
    para = words[start : start + 1200]
    for word in ("LaTeX", "Lean convention"):
        assert word in para, (word, para)


def test_a_new_gloss_file_starts_from_the_rule() -> None:
    """``opn-gate gloss revise``'s placeholder body states the order the guide asks for."""
    body = flat(cli._NEW_GLOSS_BODY)
    for word in RULE_WORDS:
        assert word in body, body
