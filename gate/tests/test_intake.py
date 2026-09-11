"""F11: curated intake (T1; R7; AC8).

The selection record is prose the curator writes, so what a test can hold is its *completeness*:
that it names the chosen result, answers each of R7's six criteria with evidence, and rejects two
alternatives with reasons. Those are the parts a reader of the record needs and the parts a
hurried session would drop, so they are the parts pinned here (F11-AC8).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SELECTION = REPO / "engineering" / "evidence" / "F11" / "selection.md"
ANNEX = Path(__file__).resolve().parent / "fixtures" / "onramp" / "annex.md"

#: R7's criteria, each as the slug of its `###` heading under `## Criteria`. One heading per
#: criterion, so a criterion that was never answered is a missing key rather than a thin
#: paragraph nobody notices.
R7_CRITERIA: tuple[str, ...] = (
    "elementary-in-an-included-domain",
    "objects-defined-in-the-graphs-own-defs",
    "statable-in-under-40-lines",
    "at-most-three-definitions",
    "decomposable-into-three-to-six-lemmas",
    "mathlib-still-pinned",
)
MIN_REJECTED = 2  # R7: "two rejected alternatives and why"
MIN_LEMMAS, MAX_LEMMAS = 3, 6  # R7's band, counted as rows of the lemma-structure table


def sections(text: str, level: int) -> dict[str, str]:
    """Headings of exactly ``level`` hashes, mapped to the body under each."""
    pattern = re.compile(rf"^{'#' * level} +(?P<title>.+?)\s*$", re.M)
    found = list(pattern.finditer(text))
    out: dict[str, str] = {}
    for i, m in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(text)
        out[m.group("title").strip()] = text[m.end() : end]
    return out


def subsections(body: str) -> dict[str, str]:
    return sections(body, 3)


@pytest.fixture(scope="module")
def record() -> str:
    assert SELECTION.is_file(), f"the selection record R7 requires is missing: {SELECTION}"
    return SELECTION.read_text(encoding="utf-8")


def test_selection_record_complete(record: str) -> None:
    """AC8: the record names the chosen result, each R7 criterion with evidence, and two
    rejected alternatives."""
    top = sections(record, 2)
    wanted = ("Chosen", "Definitions", "Lemma structure", "Criteria", "Rejected alternatives")
    for heading in wanted:
        assert heading in top, f"the selection record has no '## {heading}' section"

    chosen = top["Chosen"]
    assert re.search(r"^-\s+\*\*theorem:\*\*\s+\S", chosen, re.M), "no chosen theorem is named"
    assert re.search(r"^-\s+\*\*root statement:\*\*\s+\S", chosen, re.M), "no root statement"

    criteria = subsections(top["Criteria"])
    missing = [c for c in R7_CRITERIA if c not in criteria]
    assert not missing, f"R7 criteria with no heading in the record: {', '.join(missing)}"
    unanswered = [c for c in R7_CRITERIA if not re.search(r"^evidence:\s*\S", criteria[c], re.M)]
    assert not unanswered, f"R7 criteria with a heading but no evidence: {', '.join(unanswered)}"

    rejected = subsections(top["Rejected alternatives"])
    assert len(rejected) >= MIN_REJECTED, (
        f"R7 wants two rejected alternatives; the record has {len(rejected)}"
    )
    silent = [name for name, body in rejected.items() if not re.search(r"why rejected:", body)]
    assert not silent, f"rejected alternatives with no reason: {', '.join(silent)}"


def test_selection_lemma_structure_is_in_r7s_band(record: str) -> None:
    """AC8, R7: three to six lemmas. Counted from the record rather than asserted in prose, so a
    later edit to the table cannot quietly leave the band."""
    table = sections(record, 2)["Lemma structure"]
    rows = [
        line
        for line in table.splitlines()
        if line.strip().startswith("|") and not re.match(r"^\s*\|[\s|:-]+\|\s*$", line)
    ]
    nodes = len(rows) - 1  # the header row
    assert MIN_LEMMAS <= nodes <= MAX_LEMMAS, (
        f"R7 asks for three to six lemmas; the record's table has {nodes} nodes"
    )
    assert re.search(r"\(root\)", table), "the lemma table does not mark which node is the root"


def test_selection_names_the_annex_the_skeleton_will_cite(record: str) -> None:
    """R8: the skeleton submitted in T4 cites an annex holding the paper's argument, so T1 has
    to leave one behind and the record has to say where it is (D-31)."""
    assert ANNEX.is_file(), f"the annex text R8's skeleton cites is missing: {ANNEX}"
    rel = ANNEX.relative_to(REPO).as_posix()
    assert rel in record, f"the selection record does not point at the annex at {rel}"
    text = ANNEX.read_text(encoding="utf-8")
    assert "D-31" in text, "the annex does not say what it is (untrusted input, D-31)"
