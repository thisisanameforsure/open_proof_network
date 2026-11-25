"""mcpfix WB1 item 3 (testers 2026-11-25, qa-eb L4): a Lean position names a line of the
caller's own text.

The checker reports positions in the text it compiled, and that is not the caller's: AXLE puts
``import Mathlib`` and a blank line in place of the text's header (probed 2026-11-25: imports,
blank lines and ``--`` comments before the first command are removed), and the network inlines
the target's definitions and the node's Context after the imports. So a broken three-line proof
reported ``-:5:9`` and a one-line exhibit ``-:3:23``. Every position in ``lean_messages`` and
``tool_messages`` is now mapped back: through the checker's own echo to the text sent, and
through the composition to the caller's line. A position inside an inlined module names the
import line that pulled it in, with a note naming the module and its own line; one in the
statement (witness mode) is labelled ``statement``. ``echo: true`` returns the positions as the
checker gave them, beside the echo they refer to.
"""

from __future__ import annotations

from typing import Any

from api_fakes import AXLE_OKAY, AxleCall, FakeAxle, make_harness
from mcp_client import NODE, TARGET
from test_checks import harness_with, post, seed
from test_finding_exhibit_preflight import claim
from test_finding_witness_preflight import harness as dep_harness

from opn_api import checks


def axle_echo(sent: str) -> str:
    """What AXLE echoes for ``sent``: its header (imports, blank lines and ``--`` comments before
    the first command) replaced by ``import Mathlib`` and a blank line."""
    lines = sent.splitlines(keepends=True)
    k = 0
    while k < len(lines) and (not lines[k].strip() or lines[k].startswith(("import ", "--"))):
        k += 1
    return "import Mathlib\n\n" + "".join(lines[k:]) + "\n"


def line_of(text: str, marker: str) -> int:
    return text[: text.index(marker)].count("\n") + 1


def failing_at(*markers: str, kind: str = "error", col: int = 2) -> Any:
    """A reply that echoes like AXLE and reports a ``kind`` message at each marker's line."""

    def reply(call: AxleCall) -> dict[str, Any]:
        echo = axle_echo(call.content)
        messages = [
            f"-:{line_of(echo, m)}:{col}-{line_of(echo, m)}:{col + 3}: {kind}: about {m}\n"
            for m in markers
        ]
        infos = [f"-:{line_of(echo, markers[0])}:{col}: info: unsolved goals at error"]
        return {
            **AXLE_OKAY,
            "okay": False,
            "content": echo,
            "lean_messages": {"errors": messages, "warnings": [], "infos": []},
            "tool_messages": {"errors": [], "warnings": [], "infos": infos},
        }

    return reply


def test_a_broken_three_line_proof_reports_its_own_line() -> None:
    """qa-eb L4's call: the error on line 3 of the caller's proof read ``-:5:9``."""
    h = harness_with()
    seed(h)
    proof = "theorem t (h : True ∧ True) : True := by\n  have := h.1\n  exact h.2 BROKEN\n"
    h.axle.replies = [failing_at("BROKEN", col=9)]
    r = post(h, {"target_id": TARGET, "content": proof})
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    assert result["lean_messages"]["errors"] == ["-:3:9-3:12: error: about BROKEN\n"]
    assert result["tool_messages"]["infos"] == ["-:3:9: info: unsolved goals at error"]


def test_with_echo_the_positions_are_the_checkers() -> None:
    h = harness_with()
    seed(h)
    proof = "theorem t : True := by\n  exact BROKEN\n"
    h.axle.replies = [failing_at("BROKEN")]
    r = post(h, {"target_id": TARGET, "content": proof, "echo": True})
    assert r.json()["result"]["lean_messages"]["errors"] == ["-:4:2-4:5: error: about BROKEN\n"]


DEFS_A = "/- a definition -/\ndef Opn.a : Nat := 1\ndef Opn.bad : Nat := BADDEF\n"
CONTENT = "import Mathlib\nimport Defs.A\n\ntheorem t : Opn.a = 1 := by\n  exact BROKEN\n"


def test_a_position_in_inlined_text_names_the_import_that_pulled_it_in() -> None:
    h = harness_with()
    seed(h, defs={"A": "import Mathlib\n" + DEFS_A})
    h.axle.replies = [failing_at("BROKEN", "BADDEF")]
    r = post(h, {"target_id": TARGET, "content": CONTENT})
    assert r.status_code == 200, r.text
    errors = r.json()["result"]["lean_messages"]["errors"]
    assert errors[0] == "-:5:2-5:5: error: about BROKEN\n"
    # BADDEF is on line 3 of Defs.A's text as inlined (its import line blanked): it is reported
    # at the import line that pulled the module in, with a note naming where it really is
    assert errors[1].startswith("-:2:0: error: about BADDEF\n")
    assert "Defs.A" in errors[1] and "line 3" in errors[1]


def test_witness_mode_reports_the_witness_and_the_statement_apart() -> None:
    witness = "import Mathlib\n\ntheorem witness : True := WBROKEN\n"
    h = make_harness(axle=FakeAxle(replies=[failing_at("WBROKEN", "sorry")]))
    seed(h)
    r = post(h, {"target_id": TARGET, "node_id": NODE, "mode": "witness", "content": witness})
    assert r.status_code == 200, r.text
    errors = r.json()["result"]["lean_messages"]["errors"]
    assert errors[0] == "-:3:2-3:5: error: about WBROKEN\n"
    statement_line = line_of(
        h.githost.files[f"targets/{TARGET}/nodes/{NODE}/Statement.lean"].decode(), "sorry"
    )
    assert errors[1].startswith(f"statement:{statement_line}:2-")


EXHIBIT_LINE = "theorem exhibit_vacuous : OpnProp.and_swap_dep = BROKEN := rfl\n"


def test_a_defect_claims_exhibit_error_is_on_the_exhibits_own_line() -> None:
    """qa-eb L4: a one-line exhibit's error read ``-:3:23``."""
    exhibit = f"import Nodes.«and-reassoc».Context\n\n{EXHIBIT_LINE}"
    h = dep_harness(failing_at("BROKEN", col=23))
    r = claim(h, exhibit=exhibit)
    assert r.status_code == 422, r.text
    assert r.json()["details"]["errors"] == ["-:3:23-3:26: error: about BROKEN\n"]


def test_relocate_leaves_an_unpositioned_message_alone() -> None:
    composed = checks.plain("theorem t : True := trivial\n")
    assert checks.relocate("no position here", composed, 0) == "no position here"
