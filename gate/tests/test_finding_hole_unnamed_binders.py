"""Finding hole-unnamed-binders (testers 2026-11-24, Reed's conjecture): two prechecks failed
step 4 ``hole-unnamed`` ("3 sorry(s) are not bound by a `have`") although every hole was written
``have … := by sorry``, the guide's own form. Each hole's type opened with ``{V}`` and ``[…]``
binders, so Lean elaborated the ``sorry`` under their lambdas and the extractor found it unbound;
``:= no_implicit_lambda% sorry`` was the cure, and neither the message, the hint nor the guide
said so. The tester found it by guessing. Also from that run, the guide's two gaps that cost
refused requests: where the tutorial precheck's nonce is (only the ``202`` answer carries it),
and what a definition gloss's ``module`` is (a file name under ``defs/``, extension included)."""

from __future__ import annotations

from pathlib import Path

from opn_gate import codes

GUIDE = Path(__file__).resolve().parents[1] / "agents" / "AGENTS.md"
ARTIFACT = Path(__file__).resolve().parents[1] / "opn_gate" / "steps" / "artifact.py"


def test_the_hint_names_the_cure() -> None:
    assert "no_implicit_lambda% sorry" in codes.CATALOG["hole-unnamed"].remedy


def test_the_step_4_message_names_the_cause_and_the_cure() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    start = text.index('"hole-unnamed",')
    message = text[start : text.index('{"unnamed"', start)]
    assert "implicit or instance binders" in message
    assert "no_implicit_lambda% sorry" in message


def test_the_guide_says_how_to_write_such_a_hole() -> None:
    assert "no_implicit_lambda% sorry" in GUIDE.read_text(encoding="utf-8")


def test_the_guide_says_where_the_nonce_is() -> None:
    assert "`GET /precheck/<job>`, the poll,\nnever repeats it" in GUIDE.read_text(encoding="utf-8")


def test_the_guide_gives_a_definition_subject_literally() -> None:
    assert '"module":\n"Local.lean"}' in GUIDE.read_text(encoding="utf-8")
