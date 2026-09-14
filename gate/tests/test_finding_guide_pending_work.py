"""Finding guide-pending-work (the 2026-09-13 Euclid tester): the guide leaves out what a
contributor has to discover by trial.

``gate/agents/AGENTS.md`` never says that a merged skeleton's holes are the submitter's own work
to witness and prove, one pull request and one non-author approval each, merged one at a time,
with the parent finalized only after them; it names the attestation ``attestations/<pull request
number>.json`` when the file is zero-padded to six digits; it gives no way to watch a submission
that has not merged (``GET /submissions/<id>``, ``get_submission`` with review and check state,
``list_submissions``); and its claiming section never says why a node is not claimable
(``not_claimable`` in ``targets/index.json``, the ``node-not-claimable`` refusal).

Docs are tests (F10-Q3): each test slices one section of the guide by its heading and reads its
prose (fenced blocks excluded where a code comment could satisfy the wording) against a few
equivalent phrasings, so the fix is the guide's own edit.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "gate" / "agents" / "AGENTS.md"


def _load_walkthrough() -> ModuleType:
    """``gate/tools/walkthrough.py`` is a script, not a package member; its heading and block
    parsers are the ones the guide's executed blocks already go through."""
    path = ROOT / "gate" / "tools" / "walkthrough.py"
    spec = importlib.util.spec_from_file_location("walkthrough", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def section(prefix: str) -> str:
    """The level-2 section whose heading starts with ``prefix``, subsections included."""
    walkthrough = _load_walkthrough()
    markdown = GUIDE.read_text(encoding="utf-8")
    titles = [h for h in walkthrough.headings(markdown) if h.startswith(prefix)]
    assert titles, f"no heading starting {prefix!r}: {walkthrough.headings(markdown)}"
    start = markdown.index(f"\n## {prefix}")
    end = markdown.find("\n## ", start + 1)
    return markdown[start : end if end >= 0 else len(markdown)]


def prose(text: str) -> str:
    """``text`` without its fenced blocks, so a comment inside a code block does not count."""
    kept: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.rstrip().startswith("```"):
            inside = not inside
            continue
        if not inside:
            kept.append(line)
    return "\n".join(kept)


def paragraphs(text: str) -> list[str]:
    return [" ".join(p.split()) for p in re.split(r"\n\s*\n", text) if p.strip()]


def says(text: str, *patterns: str) -> bool:
    """Whether any of the equivalent phrasings appears (case-insensitive, whitespace-folded)."""
    folded = " ".join(text.split())
    return any(re.search(p, folded, re.IGNORECASE) for p in patterns)


# --- Skeletonization ----------------------------------------------------------------------------


def test_the_skeleton_section_says_the_holes_are_yours_to_witness_and_prove() -> None:
    text = prose(section("Skeletonization"))
    assert says(text, r"\bwitness"), "the skeleton section never mentions a hole's witness"
    assert says(
        text,
        r"\bholes? (are|is|become|becomes) (yours|your own|your work|for you)",
        r"\byour (own )?holes\b",
        r"\byou (then |now |still )?(must |need to |have to )?(witness|prove)\b[^.]*\bholes?\b",
        r"\b(witness|prove) (and prove |and witness )?(each|every|the) holes?\b",
    ), "the skeleton section does not say the holes are the submitter's to witness and prove"


def test_the_skeleton_section_says_one_pull_request_and_one_approval_per_hole() -> None:
    text = prose(section("Skeletonization"))
    assert says(
        text,
        r"\b(one|a|its own|a separate|separate) pull requests? (for |per )?(each|every|per)\b",
        r"\bpull requests? per hole\b",
        r"\b(each|every) (hole|witness|proof)\b[^.]*\b(its own|one|a separate) pull request\b",
        r"\bone pull request each\b",
    ), "the skeleton section does not say each hole is its own pull request"
    assert says(text, r"\bnon-author\b"), "no non-author review is mentioned"
    assert says(
        text,
        r"\b(each|every)\b[^.]*\bapprov",
        r"\bapprov\w*\b[^.]*\b(each|every|per)\b",
        r"\ban approv\w+ each\b",
    ), "the skeleton section does not say each pull request needs its own approval"


def test_the_skeleton_section_says_merge_one_at_a_time_and_the_parent_last() -> None:
    text = prose(section("Skeletonization"))
    assert says(
        text,
        r"\bone at a time\b",
        r"\bone after (the )?other\b",
        r"\bone after another\b",
        r"\bsequential",
        r"\bin turn\b",
        r"\bafter the previous\b",
        r"\bstrict up-to-date\b",
    ), "the skeleton section does not say the hole pull requests merge one at a time"
    assert says(text, r"\bparent\b"), "the skeleton section never mentions the parent node"
    assert says(
        text,
        r"\bonly (then|once|after|when)\b",
        r"\bonce (all|every|each)\b[^.]*\bholes?\b",
        r"\b(after|until) (all|every|each)\b[^.]*\bholes?\b",
        r"\bholes?\b[^.]*\b(have|has) (all )?(merged|been proved|been witnessed)\b[^.]*\bparent\b",
    ), "the skeleton section does not say the parent is finalized only after its holes"


# --- Precheck and submit ------------------------------------------------------------------------


def test_precheck_and_submit_names_the_zero_padded_attestation() -> None:
    text = section("Precheck and submit")
    assert "attestations/<pull request number>.json" not in text, (
        "the guide still names the unpadded `attestations/<pull request number>.json`"
    )
    assert says(text, r"zero-pad", r"\bpadded\b", r"\bsix digits\b", r"\bsix-digit\b", "%06d"), (
        "the section does not say the attestation id is zero-padded"
    )
    assert re.search(r"attestations/\d{6}\.json", text), (
        "the section gives no six-digit example such as attestations/000033.json"
    )


def test_precheck_and_submit_says_how_to_watch_a_pending_submission() -> None:
    """``GET /submissions/<id>`` (or ``get_submission``) documented in the same paragraph as the
    pull request's review and check state — what an open submission is waiting on."""
    text = prose(section("Precheck and submit"))
    route = (r"GET /submissions/", r"/submissions/[<{$]", r"\bget_submission\b")
    documented = [
        p
        for p in paragraphs(text)
        if says(p, *route) and says(p, r"\breview") and says(p, r"\bchecks?\b", r"\bruns?\b")
    ]
    assert documented, (
        "no paragraph documents GET /submissions/<id> or get_submission with review and check state"
    )


def test_the_appendix_lists_list_submissions() -> None:
    text = section("Appendix: the MCP tools")
    assert "`list_submissions" in text, "the MCP appendix has no list_submissions row"


# --- Claiming a node ----------------------------------------------------------------------------


def test_the_claiming_section_says_why_a_node_is_not_claimable() -> None:
    text = section("Claiming a node")
    missing = [
        needle
        for needle in ("not_claimable", "targets/index.json", "node-not-claimable")
        if needle not in text
    ]
    assert missing == [], f"the claiming section does not mention {missing}"
