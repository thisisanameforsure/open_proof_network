"""Declared uses: what a proof may draw on beyond its statement's own header (F08-R16 to R18;
D-3, D-4 v3.24).

A node's statement is immutable, and until this module a proof's header had to be the
statement's exactly (F00-R19, with F00-T10's one line). So nothing beneath a root stated over
Mathlib alone could name a definition admitted to the target later (F11-T13), and no node could
name a proved node it did not already depend on: a gate-written hole has ``deps: []`` and its
parent's header, and an authored node's deps are fixed when it is created.

**The declaration is the artifact's own header.** A proof, a partial's assembly or an alternate
may carry *use lines*: ``import`` lines placed directly after the statement's last import (after
the node's own ``Context`` line, where F00-T10 added one), each naming

* ``Defs.<Name>``: a definition module of the same target, on the tree; or
* ``Nodes.«<id>».Proof``: the merged proof of another node of the same target (F08-T24).

Nothing else changes in the file: with its use lines removed it is the statement with the
``sorry`` replaced, as before, so ``Statement.lean``, its hash and ``META.yaml`` are untouched.
The declaration lands in the tree inside the artifact, under the artifact's hash, with no
sidecar and no new path, and Lean itself enforces half of it: a name whose module is not
imported is not there to be used.

What makes it sound is split across the steps that already own each question:

* step 2 (``check``): each line names something that exists and may be used;
* step 4 (``steps.meaning``): the larger environment did not change what the statement says;
* step 8 (``steps.deps``): the lines agree with what the kernel term uses.

A gate that predates this module refuses every such header as ``proof-not-statement``, so
nothing here is live on a graph before its re-pin (D-35).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate import layout
from opn_gate.diagnostic import Diagnostic

#: ``ctx.data`` key: the uses step 2 read off the artifact, as ``Uses.as_dict`` gives them.
USES_KEY = "uses"

_DEFS_USE = rf"{layout.DEFS_PREFIX}\.[A-Za-z_][A-Za-z0-9_']*"
#: One use line, without its newline: the module it names.
USE_LINE_RE = re.compile(rf"import[ \t]+(?P<module>{_DEFS_USE})[ \t]*")


@dataclass(frozen=True)
class Uses:
    """The use lines of one artifact, in the order written."""

    modules: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.modules)

    @property
    def defs(self) -> tuple[str, ...]:
        """The ``Defs.<Name>`` modules declared."""
        return tuple(m for m in self.modules if layout.module_origin(m)[0] == "defs")

    def as_dict(self) -> dict[str, Any]:
        return {"modules": list(self.modules), "defs": list(self.defs)}


def _imports_end(text: str) -> int:
    """The offset just past ``text``'s last ``import`` line; 0 when it has none."""
    end = 0
    offset = 0
    for line in text.splitlines(keepends=True):
        offset += len(line)
        if line.startswith("import "):
            end = offset
    return end


def split(prefix: str, text: str, node_id: str | None) -> tuple[str, Uses]:
    """``text`` with its use lines removed, and the uses they declare.

    ``prefix`` is the statement's text up to its ``:=`` (``layout.Statement.prefix``). The use
    lines are the run of lines directly after the statement's last import, or after the node's
    own ``Context`` line where the artifact adds it (F00-T10), each matching ``USE_LINE_RE``.
    They are taken out only when what remains begins with the header the gate already takes;
    any other text comes back unchanged with no uses, so step 2's own diagnostic stands.
    """
    bases = [prefix]
    if node_id is not None:
        allowed = layout.with_own_context(prefix, node_id)
        if allowed != prefix:
            bases.append(allowed)
    for base in bases:
        at = _imports_end(base)
        if not text.startswith(base[:at]):
            continue
        modules: list[str] = []
        pos = at
        while True:
            end = text.find("\n", pos)
            if end == -1:
                break
            line = USE_LINE_RE.fullmatch(text[pos:end])
            if line is None:
                break
            modules.append(line.group("module"))
            pos = end + 1
        rest = base[:at] + text[pos:]
        if modules and rest.startswith(base):
            return rest, Uses(tuple(modules))
    return text, Uses()


def declared(statement: layout.Statement, text: str, node_id: str | None) -> Uses:
    """The uses an artifact of ``statement`` declares (``split``'s second half)."""
    return split(statement.prefix, text, node_id)[1]


def defs_file(target_dir: Path, module: str) -> Path:
    """Where ``Defs.<Name>`` lives in a target: ``defs/<Name>.lean``."""
    return target_dir / "defs" / f"{module.partition('.')[2]}.lean"


def check(node: layout.Node, uses: Uses) -> Diagnostic | None:
    """Step 2's rules for a declared use, read from the tree (R16): the first one broken.

    * ``use-duplicate``: a line repeats another, or a module the statement already imports;
    * ``use-unknown-defs``: ``Defs.<Name>`` is not a definition of this target on the tree. A
      submission cannot add one (``defs/`` is no submission path, D-3), so what is on the tree is
      what a curator's pull request admitted (F11-R15).
    """
    target_dir = node.path.parent.parent
    seen = set(layout.imports_of(node.statement.text))
    for module in uses.modules:
        if module in seen:
            return Diagnostic(
                "use-duplicate",
                f"the header imports {module} twice: a use line names a module once, and never "
                "one the statement already imports",
                {"module": module},
            )
        seen.add(module)
    for module in uses.defs:
        if not defs_file(target_dir, module).is_file():
            return Diagnostic(
                "use-unknown-defs",
                f"{module} is not a definition of {node.target_id}: a proof may use a module "
                f"under targets/{node.target_id}/defs/ that is already on the graph (D-3), and "
                "a definition is added by a curator's pull request (F11-R15)",
                {"module": module},
            )
    return None
