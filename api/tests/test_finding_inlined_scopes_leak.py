# ruff: noqa: RUF001, RUF002 — the fixtures are Lean source, with its double-struck letters
"""Finding inlined-scopes-leak (curator D, 2026-11-25): the fast check failed a variant statement
for green-75 with errors inside the network's own definitions (`Function expected at ι` in
FieldTheoryMilnorKTheory), while the same statement passed with its imports in another order.

mcpfix WB1 (``scope_closers``) closes every scope an inlined module leaves open, which is the
case that failed: the mechanical port's unclosed ``section`` kept ColoringVertex's
``variable {V α ι : Type*}`` in scope over the next module. What closing scopes cannot reach is a
scoped command written outside every scope: a module's top-level ``variable`` or ``open`` ends
with its own file, and pasted into one text it stays in force over every later module and the
caller's statement. Two live modules have one (Data/Set/Interval's ``variable {β : Type*}
[Preorder β]``, Clique's ``open Finset``; scanned over every defs/ file on the graph). Each
inlined module now sits in a section of its own, after its closers, so nothing it puts in scope
reaches what follows it, whatever the order.
"""

from __future__ import annotations

import re

from opn_api import checks

TOP_LEVEL = """\
variable {β : Type*} [Preorder β]
open Finset

def lt₂ (a b : β) : Prop := a < b
"""

AFTER = """\
section
def uses_beta : ℕ := 1
end
"""

CONTENT = "import Mathlib\nimport Defs.A\nimport Defs.B\n\ntheorem t : True := trivial\n"

_OPEN = re.compile(r"^\s*(?:noncomputable\s+)?(?:section|namespace|mutual)\b[ \t]*(\S*)")
_END = re.compile(r"^\s*end\b[ \t]*(\S*)")


def depth_before(text: str, marker: str) -> int:
    """How many scopes are open at the first line containing ``marker`` (a dotted name counts
    one scope a component, as Lean counts them)."""
    depth = 0
    for line in text.splitlines():
        if marker in line:
            return depth
        opened, ended = _OPEN.match(line), _END.match(line)
        if opened:
            depth += max(1, len([c for c in opened.group(1).split(".") if c]))
        elif ended:
            depth -= max(1, len([c for c in ended.group(1).split(".") if c]))
    msg = f"{marker!r} not found"
    raise AssertionError(msg)


def scope_of(text: str, marker: str) -> list[str]:
    """The ``variable`` and ``open`` lines in force at ``marker``: those written in a scope that
    is still open there (a top-level one is in force to the end of the text)."""
    frames: list[list[str]] = [[]]
    for line in text.splitlines():
        if marker in line:
            return [cmd for frame in frames for cmd in frame]
        opened, ended = _OPEN.match(line), _END.match(line)
        if opened:
            frames.extend([] for _ in range(max(1, len(opened.group(1).split(".")))))
        elif ended and len(frames) > 1:
            for _ in range(max(1, len([c for c in ended.group(1).split(".") if c]))):
                if len(frames) > 1:
                    frames.pop()
        elif re.match(r"^\s*(variable|open)\b", line):
            frames[-1].append(line.strip())
    msg = f"{marker!r} not found"
    raise AssertionError(msg)


def test_a_top_level_variable_or_open_does_not_reach_the_next_module() -> None:
    text = checks.forwarded_text(CONTENT, [("Defs.A", TOP_LEVEL), ("Defs.B", AFTER)])
    assert scope_of(text, "def uses_beta") == []
    assert scope_of(text, "theorem t") == []


def test_every_inlined_module_is_closed_before_the_statement() -> None:
    text = checks.forwarded_text(CONTENT, [("Defs.A", TOP_LEVEL), ("Defs.B", AFTER)])
    assert depth_before(text, "theorem t") == 0
