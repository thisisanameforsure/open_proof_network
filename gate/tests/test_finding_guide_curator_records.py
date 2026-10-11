"""F07-T72 (audit 2026-10-04): the guide tells a curator how to withdraw a record and correct a
ledger line.

F08-T31 and F07-T66 built two curator records (D-18, D-19 v3.27) and the guide named neither, so
an agent acting as curator had no way to learn the path, what the record names or what it does.
Each sentence is held to the code that implements it: the path the guide gives is the role
``paths.locate`` assigns, the schema it names is the one that role accepts, the fields it lists
are the schema's own, and the refusal codes are catalog codes.
"""

from __future__ import annotations

import re
from pathlib import Path

from opn_gate import codes, paths, schemas

ROOT = Path(__file__).resolve().parents[2]
GUIDE = (ROOT / "gate" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
FLAT = re.sub(r"\s+", " ", GUIDE)

WITHDRAWAL = "targets/<id>/nodes/<node>/withdrawals/<stamp>-<curator>.yaml"
CORRECTION = "targets/<id>/credit-corrections/<stamp>-<curator>.yaml"


def concrete(path: str) -> str:
    return (
        path.replace("<id>", "erdos-69")
        .replace("<node>", "erdos-69--h1")
        .replace("<stamp>", "20261004T120000Z")
        .replace("<curator>", "founder")
    )


def paragraph(heading: str) -> str:
    """From the bold heading to the next bold paragraph or section heading."""
    start = FLAT.index(heading)
    ends = [i for i in (FLAT.find(m, start + 1) for m in (" **", " ## ")) if i != -1]
    return FLAT[start : min(ends)]


def test_the_guide_tells_a_curator_how_to_withdraw_a_record() -> None:
    text = paragraph("**For curators: withdrawing a record")
    assert f"`{WITHDRAWAL}`" in text
    located = paths.locate(concrete(WITHDRAWAL))
    assert located is not None and located.role == "withdrawal"
    assert "`withdrawal/v1`" in text
    # The version the paragraph teaches is one the gate accepts; F20-R7 added v2 for gloss and
    # explainer versions, which the guide's revision section covers (F20-T12).
    assert "withdrawal/v1" in paths.SCHEMAS_FOR_ROLE["withdrawal"]
    for field in schemas.load_schema("withdrawal/v1")["required"]:
        if field != "schema":
            assert f"`{field}`" in text, field
    assert "`status/<file>`" in text and "`defects/<file>`" in text
    assert "`withdrawal-unknown-record`" in text
    assert "withdrawal-unknown-record" in codes.CATALOG
    assert "stays in the tree" in text and "absent" in text


def test_the_guide_tells_a_curator_how_to_correct_a_ledger_line() -> None:
    text = paragraph("**For curators: correcting a ledger line")
    assert f"`{CORRECTION}`" in text
    located = paths.locate(concrete(CORRECTION))
    assert located is not None and located.role == "credit-correction"
    assert "`credit-correction/v1`" in text
    required = set(schemas.load_schema("credit-correction/v1")["required"])
    for field in required - {"schema", "author", "date"}:
        assert f"`{field}`" in text, field
    for code in ("credit-correction-unknown-entry", "credit-correction-same-identity"):
        assert f"`{code}`" in text and code in codes.CATALOG, code
    assert "`revoked`" in text and "never deletes" in text
