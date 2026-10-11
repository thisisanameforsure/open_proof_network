"""F21-T8 (R10; D-3, D-19, D-25 v3.31): the guide offers "write the words for a statement" as an
entry task beside the tutorial proof, and says what F21 changed about words.

The commands themselves run in the walkthrough (``test_walkthrough.py``); these tests hold the
prose to the rules: where the entry task is pointed to, what it tells an agent to call, the section
states, the lock, approval by section and the credit rule, and that the refusal table names the
codes F21 added and none it removed.
"""

from __future__ import annotations

import re
from pathlib import Path

from opn_api.mcp import server
from opn_gate import codes

ROOT = Path(__file__).resolve().parents[2]
GUIDE = (ROOT / "gate" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
FLAT = re.sub(r"\s+", " ", GUIDE)
SECTION = "## Glosses, explainers and outlines"
ENTRY = "### Entry task: write the words for a statement"


def words_section() -> str:
    start = GUIDE.index(SECTION)
    return GUIDE[start : GUIDE.index("\n## ", start + 1)]


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def test_the_entry_task_is_pointed_to_beside_the_tutorial() -> None:
    """A short pointer before the tutorial proof, the steps in the words section."""
    pointer = GUIDE.index("**Two ways in.**")
    assert pointer < GUIDE.index("## The tutorial node")
    near = flat(GUIDE[pointer : GUIDE.index("## The tutorial node")])
    for needle in ("`list_words_needed`", "`submit_gloss`", "`drafted_with`", ENTRY[4:]):
        assert needle in near, needle
    assert words_section().index(ENTRY) < words_section().index("### Reading an outline")


def test_the_entry_task_finds_reads_writes_and_submits() -> None:
    section = words_section()
    entry = flat(section[section.index(ENTRY) : section.index("### Reading an outline")])
    order = ("`list_words_needed(", "`get_node`", "`POST /glosses`", "`drafted_with`")
    at = 0
    for needle in order:
        found = entry.find(needle, at)
        assert found >= 0, f"{needle} is not after {entry[:at][-80:]!r}"
        at = found
    assert '"name":"list_words_needed"' in entry  # the runnable call, through the MCP endpoint
    assert '"drafted_with":' in entry  # the runnable submission discloses its model
    assert "`409 duplicate-submission`" in entry and "one writer per file" in entry.lower()
    assert {"list_words_needed", "submit_gloss", "get_node"} <= set(server.BY_NAME)


def test_the_states_the_lock_and_the_review_are_said() -> None:
    section = flat(words_section())
    for needle in (
        "**drafted**",
        "**written**",
        "**verified**",
        "**pending**",
        "`409 locked-by-a-person`",
        "awaiting review",
        "words you wrote yourself that no one has verified",
        "`author-not-opener`",
        "--sections whole",
        "`opn-gate explainer sign` takes `--sections`",
    ):
        assert needle in section, needle
    # F20-R6's bar on superseding a signed version is withdrawn (F21-R13)
    assert "may be superseded only" not in section
    assert "Anyone may supersede any version" in section


def test_the_credit_rule_is_said() -> None:
    section = flat(words_section())
    credit = section[section.index("**Credit.**") :]
    for needle in (
        "one write-up entry crediting the author",
        "a second signature adds nothing",
        "A draft (a version with no author) earns nothing",
        "a signature on your own version earns nothing",
        "the signer is never credited",
        "An unsigned version earns nothing",
    ):
        assert needle in credit, needle


def test_the_refusal_table_names_f21s_codes_and_not_the_removed_ones() -> None:
    table = words_section().split("What to do about each refusal:", 1)[1]
    rows = set(re.findall(r"^\| `([a-z-]+)`", table, re.M))
    added = {
        "duplicate-submission",
        "locked-by-a-person",
        "draft-not-accepted",
        "author-not-opener",
        "tooling-invalid",
        "section-duplicate",
        "signature-section-unknown",
    }
    assert added <= rows, added - rows
    assert rows <= set(codes.CATALOG), rows - set(codes.CATALOG)
    removed = ("signed-supersede", "drafter-unauthorized", "drafter-not-service", "drafter-invalid")
    for code in removed:
        assert code not in codes.CATALOG
        assert code not in GUIDE, code


def test_the_seven_drafts_are_history() -> None:
    section = flat(words_section())
    assert "The network drafts no words" in section
    assert "2026-10-05" in section and "machine-drafted by" in section
    assert "`draft-not-accepted`" in section
