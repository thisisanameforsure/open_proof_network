"""F28-T3 finding (2026-10-15): a proof with use lines *and* a helper block was refused at step 2.

v3.25 lets a proof declare uses (import lines directly after the statement's imports) and F00-T11
lets it declare private helpers directly before the statement's theorem. Each was tested alone;
together, ``layout.split_uses`` took the use lines out only when what remained began with the
whole statement prefix, which a helper block interrupts, so the uses stayed in the text and step 2
answered ``proof-not-statement`` at the use line. Found composing a closing proof through a
circularity claim, which needs both (the exhibit as a helper, the claimed hole's proof as a use);
a contributor's proof that uses another node and declares a helper met the same refusal.
"""

from __future__ import annotations

from opn_gate import layout, paths

STATEMENT = (
    "import Mathlib\nimport Nodes.«a».Context\n\nopen scoped Nat\n\n"
    "/-- The node. -/\ntheorem a_thm : 1 + 1 = 2 := by\n  sorry\n"
)
USE = "import Nodes.«b».Proof\n"
HELPER = "private theorem two : 1 + 1 = 2 := rfl\n\n"


def parts() -> tuple[layout.Statement, str, str]:
    st = layout.parse_statement(STATEMENT)
    assert isinstance(st, layout.Statement)
    at = st.prefix.index("\n\nopen") + 1
    start = layout.declaration_start(st.prefix)
    return st, st.prefix[:at], st.prefix[at:start]


def test_a_proof_with_a_use_and_a_helper_is_the_statement() -> None:
    st, imports, middle = parts()
    text = imports + USE + middle + HELPER + st.prefix[len(imports) + len(middle) :] + " two\n"
    assert paths.check_proof_is_statement(st, text, node_id="a") is None


def test_the_use_is_read_beside_a_helper() -> None:
    """The one reading of a use (step 2's and staging's) sees it with a helper block present."""
    st, imports, middle = parts()
    text = imports + USE + middle + HELPER + st.prefix[len(imports) + len(middle) :] + " two\n"
    assert layout.split_uses(st.prefix, text, "a")[1] == ("Nodes.«b».Proof",)


def test_each_alone_still_passes_and_the_helper_rules_still_hold() -> None:
    """Uses alone and helpers alone pass as before; beside a use, a block step 2 forbids is
    still refused by the helper rule, and a changed theorem still diverges."""
    st, imports, middle = parts()
    decl = st.prefix[len(imports) + len(middle) :]
    assert paths.check_proof_is_statement(st, imports + USE + middle + decl + " two\n") is None
    assert paths.check_proof_is_statement(st, imports + middle + HELPER + decl + " two\n") is None
    opened = imports + USE + middle + "open Real\n\n" + decl + " two\n"
    got = paths.check_proof_is_statement(st, opened, node_id="a")
    assert got is not None and got.code == "helper-forbidden"
    changed = imports + USE + middle + HELPER + decl.replace("1 + 1", "2 + 0") + " two\n"
    got = paths.check_proof_is_statement(st, changed, node_id="a")
    assert got is not None and got.code == "proof-not-statement"
