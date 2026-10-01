"""F13-T20 / F02-T9 (CI run 36819988510): the composed hazards program inlines each checker file
with its import lines removed and supplies ``import Lean`` alone, so a checker may import nothing
but ``Lean`` and the gate's own ``OpnGate.Hazards`` modules. ``auto-implicit`` imported
``OpnGate.Frontend`` for ``elabFile``; the inlined text then failed on an unknown identifier and
took every hosted hazards check down with it, ``nat-sub`` alone included. The re-elaboration a
file-level checker needs is a seam on its ``Statement`` (``reelaborate``), which ``opn-hazards``
fills with ``elabFile`` and the composed program fills with the statement's own text."""

from __future__ import annotations

from pathlib import Path

from opn_api import checks
from opn_gate import layout

LEAN = Path(checks.HAZARDS_MAIN).parent
ALLOWED_PREFIX = checks.HAZARDS_PREFIX


def inlined_files() -> list[Path]:
    return [LEAN / "Hazards.lean", *sorted((LEAN / "Hazards").glob("*.lean"))]


def test_every_inlined_checker_imports_only_lean_and_the_hazards_modules() -> None:
    offending: dict[str, list[str]] = {}
    for path in inlined_files():
        bad = [
            m
            for m in layout.imports_of(path.read_text("utf-8"))
            if m not in ("Lean", ALLOWED_PREFIX) and not m.startswith(ALLOWED_PREFIX + ".")
        ]
        if bad:
            offending[path.name] = bad
    assert not offending, f"inlined by the network with its imports stripped: {offending}"


def test_the_composed_program_supplies_the_reelaboration_seam() -> None:
    """The program builds the ``Statement`` the file-level checkers read: the statement's own
    text (imports removed, under a probe namespace so nothing it declares collides with the
    declarations already elaborated) re-elaborated on the current environment under the options
    the checker asks for."""
    statement = 'import Lean\n\ntheorem Opn.t (s : String) : Or (s = "a\\\\b") True := by sorry\n'
    text = checks.hazards_text(statement, "Opn.t", ["auto-implicit"], statement=statement)
    assert "reelaborate := fun opts =>" in text
    assert "Lean.Elab.IO.processCommands" in text
    assert "namespace OpnAutoImplicitProbe" in text
    # The probe carries the statement without its header, as one Lean string literal.
    assert "import Lean" not in text.split("networkProbe")[1].split("\n")[0]
    assert (
        '\\"a\\\\\\\\b\\"' in text
    )  # the statement's own quotes and backslashes, escaped once more
    # Every selected checker's file-level hook runs before the subterm walk.
    assert "if let some check := c.source then" in text
    assert "OpnGate.Hazards.run selected s.type extra" in text


def test_the_probe_is_the_statement_not_the_inlined_definitions() -> None:
    """A definition inlined from the target's ``defs/`` is already elaborated; re-elaborating
    its copy under ``autoImplicit := false`` could report an identifier the gate never looks at.
    The probe is the statement's own text when the caller gives it."""
    defs = "\n-- inlined by the network from Defs.X (F13-R5)\ndef Opn.X (n) : Nat := n\n"
    statement = "import Lean\nimport Defs.X\n\ntheorem Opn.t : Opn.X 1 = 1 := rfl\n"
    formal = "import Lean\n" + defs + "\ntheorem Opn.t : Opn.X 1 = 1 := rfl\n"
    text = checks.hazards_text(formal, "Opn.t", ["auto-implicit"], statement=statement)
    probe = text.split("networkProbe")[1].split("\n")[0]
    assert "def Opn.X" not in probe
    assert "theorem Opn.t : Opn.X 1 = 1 := rfl" in probe
    assert "import Defs.X" not in probe
