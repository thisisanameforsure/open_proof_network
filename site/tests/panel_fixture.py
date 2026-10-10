"""F24-T6 / AC10: a ``targets-index/v9`` written by hand over the stewards fixture.

The gate's own products are F24-T4's; this module lifts the fixture's v8 index to v9 so the
site's panel and write-up sections can be built and checked independently of that task. The
document validates against ``gate/schemas/targets-index/v9.json`` (the test asserts it): the
stewarded target carries a lapsed steward, an open invitation, a passed verification with an
uncounted voter and a failed threshold motion, and three write-ups at different stages, one
withdrawn. Every free-text field carries markup, so the escaping tests cover the new fields.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fixture import STEWARD_LOGIN, STEWARDED_TARGET, build_with_stewards

__all__ = ["STEWARDED_TARGET", "STEWARD_LOGIN", "build", "lift"]

from opn_gate import schemas

LAPSED_LOGIN = "old-hand"
SECOND_MEMBER = "bob-steward"
INVITEE = "newcomer"
PROVER = "prover-x"
NOTE = "the <script>alert(1)</script> analytic half"
TITLE = "A proof of <b>the lemma</b>"
JOURNAL = "Annals & <i>Mathematics</i>"
ARXIV = "2610.01234v2"
DOI = "10.1234/abc.5"
CURATOR = "curator-one"

PANEL_SETTINGS: dict[str, Any] = {
    "vote_threshold": {
        "value": {"numerator": 2, "denominator": 3},
        "since": "2026-10-08",
        "reason": "The owner's ruling: a significant share must agree.",
    },
    "vote_window_days": {"value": 14, "since": None, "reason": None},
    "vote_minimum": {"value": 2, "since": None, "reason": None},
    "vote_minimum_from": {"value": 3, "since": None, "reason": None},
    "steward_cap": {"value": 5, "since": None, "reason": None},
    "steward_lapse_days": {"value": 180, "since": None, "reason": None},
}

MOTIONS: list[dict[str, Any]] = [
    {
        "n": 1,
        "kind": "invite",
        "subject": {"login": INVITEE, "note": NOTE},
        "opened_by": STEWARD_LOGIN,
        "opened": "2026-10-05",
        "closes": "2026-10-19",
        "state": "open",
        "yes": 1,
        "no": 0,
        "uncounted": [],
    },
    {
        "n": 2,
        "kind": "verify-writeup",
        "subject": {"writeup": 1},
        "opened_by": SECOND_MEMBER,
        "opened": "2026-09-20",
        "closes": "2026-10-04",
        "state": "passed",
        "yes": 2,
        "no": 0,
        "uncounted": [PROVER],
    },
    {
        "n": 3,
        "kind": "authorship-threshold",
        "subject": {"threshold": 0.1},
        "opened_by": STEWARD_LOGIN,
        "opened": "2026-09-21",
        "closes": "2026-10-05",
        "state": "failed",
        "yes": 1,
        "no": 1,
        "uncounted": [],
    },
]


def writeup(n: int, stage: str, **kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "n": n,
        "kind": "paper",
        "title": f"Write-up {n}",
        "url": f"https://example.org/writeups/{n}.pdf",
        "stage": stage,
        "model": None,
        "authors": [STEWARD_LOGIN],
        "signed": [STEWARD_LOGIN],
        "coauthors": [],
        "arxiv": None,
        "journal": None,
        "doi": None,
    }
    return {**base, **kw}


WRITEUPS: dict[str, Any] = {
    "official": 1,
    "items": [
        writeup(
            1,
            "accepted",
            title=TITLE,
            authors=[STEWARD_LOGIN, SECOND_MEMBER],
            signed=[STEWARD_LOGIN, SECOND_MEMBER],
            coauthors=[STEWARD_LOGIN, SECOND_MEMBER],
            arxiv=ARXIV,
            journal=JOURNAL,
            doi=DOI,
        ),
        writeup(
            2,
            "drafted",
            kind="note",
            model="claude-fable-5-1",
            authors=[SECOND_MEMBER, STEWARD_LOGIN],
            signed=[SECOND_MEMBER],
        ),
        writeup(3, "withdrawn"),
    ],
}


def lift(index: dict[str, Any]) -> dict[str, Any]:
    """The fixture's v8 index as v9: the panel settings, each steward's last act, and per
    target its panel and write-ups (empty but for the stewarded target)."""
    out: dict[str, Any] = json.loads(json.dumps(index))
    out["schema"] = "targets-index/v10"  # F25-T1: v9 plus registrations
    out["policy"]["panel"] = PANEL_SETTINGS
    for row in out["targets"]:
        for s in row["stewards"]:
            s["last_act"] = "2026-10-05"
            s["lapsed"] = False
        row["panel"] = {"members": [s["login"] for s in row["stewards"]], "motions": []}
        row["writeups"] = {"official": None, "items": []}
        row["registrations"] = []
        if row["target_id"] != STEWARDED_TARGET:
            continue
        first = dict(row["stewards"][0])
        row["stewards"].append(
            {**first, "login": SECOND_MEMBER, "name": "Bob Steward", "link": None,
             "since": "2026-09-18", "admitted_by": "motion:7", "via": "approval-key"}
        )  # fmt: skip
        row["stewards"].append(
            {**first, "login": LAPSED_LOGIN, "name": "Old Hand", "link": None,
             "since": "2026-01-02", "admitted_by": "self", "via": "approval-key",
             "last_act": "2026-01-03", "lapsed": True}
        )  # fmt: skip
        row["panel"] = {"members": [STEWARD_LOGIN, SECOND_MEMBER], "motions": MOTIONS}
        row["writeups"] = WRITEUPS
    return out


def build(tmp_path: Path) -> Path:
    """The stewards fixture with its index lifted to v9, validated against the schema."""
    root = build_with_stewards(tmp_path)
    path = root / "targets" / "index.json"
    doc = lift(json.loads(path.read_text(encoding="utf-8")))
    schemas.validate(doc, "targets-index/v10")
    path.write_bytes(schemas.canonical_json(doc))
    return root
