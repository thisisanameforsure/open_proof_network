"""mcpfix WB1 item 1 (testers 2026-11-25, t883 item 3): an inlined module's open scopes are
closed after it.

A ``Defs`` file may open a ``section`` or a ``namespace`` and never close it: in its own file the
scope ends at the end of the file. ``forwarded_text`` pastes modules one after another into one
file, so on erdos-883 every module after ``CombinatoricsSimpleGraphColoringVertex`` (which opens
``section`` and ``namespace SimpleGraph``) and the caller's own theorem landed inside
``SimpleGraph``, under its ``variable`` binders, and the check failed with 48 failed
declarations. Each inlined module is now followed by the ``end`` lines that close what it left
open, innermost first, as it opened them.
"""

from __future__ import annotations

import re
from pathlib import Path

import samples
from api_fakes import make_harness
from mcp_client import NODE, NODE_DIR, TARGET, seed_node

from opn_api import checks
from opn_gate import schemas

FIXTURES = Path(__file__).parent / "fixtures" / "erdos-883-defs"
PIN = "0df444a360eaa60ab8c11dca51a86af692955474"

UNBALANCED = (
    "/- a module that leaves three scopes open:\n"
    "namespace NotAScope\n"
    "end NotAScope -/\n"
    "section\n"
    "namespace Foo.Bar\n"
    "def x : Nat := 1\n"
    "-- end Foo.Bar   (a comment is not a command)\n"
    'def s : String := "end Foo"\n'
    "open Nat in\n"
    "def y : Nat := x\n"
    "noncomputable section Baz\n"
    "def z : Nat := 2\n"
)
BALANCED = "namespace Q\ndef w : Nat := 3\nend Q\nsection\nend\nmutual\nend\n"
CONTENT = "import Mathlib\nimport Defs.A\nimport Defs.B\n\ntheorem t : True := trivial\n"


def test_unbalanced_module_is_closed_before_the_next() -> None:
    defs = [("Defs.A", UNBALANCED.strip("\n")), ("Defs.B", BALANCED.strip("\n"))]
    text = checks.forwarded_text(CONTENT, defs)
    expected = (
        "import Mathlib\n"
        "\n-- inlined by the network from Defs.A (F13-R5)\n"
        + UNBALANCED
        + "end Baz\nend Foo.Bar\nend\n"
        + "\n-- inlined by the network from Defs.B (F13-R5)\n"
        + BALANCED
        + "\n"
        + "\ntheorem t : True := trivial\n"
    )
    assert text == expected


def test_closers_follow_dotted_and_partial_ends() -> None:
    """``namespace A.B`` closed by ``end B`` leaves ``A`` open; it is closed by its own name."""
    src = "namespace A.B\ndef p : Nat := 0\nend B\nsection S\nnamespace C"
    assert checks.scope_closers(src) == "end C\nend S\nend A\n"
    assert checks.scope_closers("namespace A.B\ndef p : Nat := 0") == "end A.B\n"
    assert checks.scope_closers(BALANCED) == ""
    # the attribute and visibility forms Lean accepts before a section
    assert checks.scope_closers("@[expose] public section\ndef q : Nat := 0") == "end\n"


def scopes_open(text: str) -> list[str]:
    """An independent count of the scopes open at the end of ``text``: block and line comments
    and strings removed, then ``namespace``/``section``/``end`` lines replayed."""
    text = re.sub(r"/-.*?-/", "", text, flags=re.S)
    text = re.sub(r'"[^"\n]*"', '""', text)
    text = re.sub(r"--[^\n]*", "", text)
    stack: list[str] = []
    for line in text.splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] == "noncomputable" and words[1:2] == ["section"]:
            words = words[1:]
        if words[0] == "namespace":
            stack += words[1].split(".")
        elif words[0] == "section":
            stack += words[1].split(".") if len(words) > 1 else [""]
        elif words[0] == "end":
            for _ in words[1].split(".") if len(words) > 1 else [""]:
                stack.pop()
    return stack


def test_erdos_883_defs_leave_no_scope_open_before_the_callers_theorem() -> None:
    """The live case, end to end through the route: the nine defs files of erdos-883 inlined for
    a check with the node, and the caller's own theorem starts at the top level."""
    h = make_harness()
    seed_node(h)
    files = h.githost.files
    files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(mathlib_sha=PIN)
    )
    statement = (FIXTURES / "Statement.lean").read_text(encoding="utf-8")
    files[NODE_DIR + "Statement.lean"] = statement.encode()
    for path in FIXTURES.glob("*.lean"):
        if path.name != "Statement.lean":
            files[f"targets/{TARGET}/defs/{path.name}"] = path.read_bytes()
    h.context.files.clear()

    content = (
        "import Mathlib\nimport Defs.CombinatoricsSimpleGraphColoringVertex\n\n"
        "theorem my_gcd_lemma (a : Nat) : Nat.gcd a a = a := Nat.gcd_self a\n"
    )
    r = h.client.post("/check", json={"node_id": NODE, "content": content})
    assert r.status_code == 200, r.text
    assert "Defs.CombinatoricsSimpleGraphColoringVertex" in r.json()["inlined_defs"]
    sent = h.axle.calls[-1].content
    vertex = sent.index(
        "-- inlined by the network from Defs.CombinatoricsSimpleGraphColoringVertex"
    )
    after = sent[vertex:].split("\n-- inlined by the network from ", 2)[1:]
    # the next inlined module (or the caller's text) begins only after the Vertex closers
    assert "end SimpleGraph\nend\n" in sent[vertex:]
    head = sent[: sent.index("theorem my_gcd_lemma")]
    assert scopes_open(head) == [], scopes_open(head)
    assert after  # the Vertex file is followed by more inlined text or the caller's
    # every module the statement imports was inlined, and none left a scope open after it
    for module in r.json()["inlined_defs"]:
        start = sent.index(f"-- inlined by the network from {module} (F13-R5)")
        end_of_block = sent.find("\n-- inlined by the network from ", start + 1)
        end_of_block = end_of_block if end_of_block != -1 else len(sent)
        assert scopes_open(sent[start:end_of_block]) == [], module
