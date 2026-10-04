"""The judging workspace (F02-T10): where step 4 and step 5 decide that an artifact proves its
statement, apart from everything the contributor's code could reach.

The step-3 sandbox runs every process in a fresh container, so no judging *process* is one a
contributor's code ran in. What it shared until T10 was the work directory: every call was handed
it writable, copied in and copied back, and the call that compiles a ``Proof.lean`` runs the
contributor's code (``#eval``, ``run_cmd``, a macro, an ``initialize`` in a module it imports),
which may write any file under it. The calls that judged the artifact then read from it.

So the verdict now rests on a directory of its own beside the work directory
(``<work>.judge``), made fresh for each run and never handed to a call that compiles
contributor code:

* ``meaning/``: the statement's own build, from the admitted files only (the target's
  definitions, the node's ``Context.lean`` of signatures, its ``Statement.lean``), copied from
  the graph by the gate and compiled by calls that can write only here;
* ``modules/``: the one input taken from the work directory, the contributor's compiled graph
  modules (each staged node's ``Context`` and ``Proof`` olean, by name, regular files only),
  beside the definitions' oleans from ``meaning/``, never the work directory's. Nothing else
  the work directory holds is copied: an olean named ``Init.*`` or ``Mathlib.*`` would shadow
  the real one on ``LEAN_PATH`` and, on a Mathlib pin, is never replayed.

The judging calls (the meaning comparison, the kernel replay, the axioms query) mount these
read-only and nothing writable. A contributor module copied here may still be anything at all,
which is why each is replayed through the kernel and the artifact's declaration is compared with
the statement's type (F08-T28) before anything is believed of it.

Without the sandbox (``pregate.sh`` on a contributor's own machine) ``confined`` hands back the
same seam: the contributor's code runs on their own machine there, and nothing it does there
decides a merge (D-4: only the gate's run in the sandbox does).
"""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from opn_gate import defs, layout
from opn_gate.diagnostic import Diagnostic
from opn_gate.toolchain import ResolvedToolchain, Toolchain, module_output_path

#: Beside the work directory, never inside it: ``<work>.judge``.
SUFFIX = ".judge"
STATEMENT_DIR = "meaning"
MODULES_DIR = "modules"
AXIOMS_DIR = "axioms"
#: ``ctx.data`` key: the ``Judge`` step 4 prepared, which step 5 reads.
KEY = "judge"
#: The stems step 4 compiles for each staged node, and so the oleans taken from its build.
NODE_STEMS: tuple[str, ...] = ("Context", "Proof")


@dataclass(frozen=True)
class Judge:
    root: Path

    @property
    def statement(self) -> Path:
        """The statement's own build: ``src/`` and ``build/`` as ``defs.compile_all`` lays out."""
        return self.root / STATEMENT_DIR

    @property
    def modules(self) -> Path:
        """The compiled modules the judging calls read: the only ``LEAN_PATH`` entry of theirs."""
        return self.root / MODULES_DIR

    @property
    def axioms(self) -> Path:
        return self.root / AXIOMS_DIR


def root_for(workdir: Path) -> Path:
    return workdir.parent / f"{workdir.name}{SUFFIX}"


def fresh(workdir: Path) -> Judge:
    """An empty judging directory for this run: whatever an earlier run left there is gone."""
    root = root_for(workdir)
    if root.is_symlink() or root.is_file():
        root.unlink()
    elif root.exists():
        shutil.rmtree(root)
    for sub in (STATEMENT_DIR, MODULES_DIR, AXIOMS_DIR):
        (root / sub).mkdir(parents=True)
    return Judge(root)


def confined(
    toolchain: Toolchain, *, read_only: Sequence[Path] = (), read_write: Sequence[Path] = ()
) -> Toolchain:
    """The seam with exactly these directories mounted, when it mounts any (the step-3 sandbox's
    ``scoped``); any other seam as it is."""
    scoped = getattr(toolchain, "scoped", None)
    if not callable(scoped):
        return toolchain
    result: Toolchain = scoped(read_only=read_only, read_write=read_write)
    return result


def build_definitions(
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    target_dir: Path,
    judge: Judge,
    *,
    timeout_s: float | None,
) -> Diagnostic | None:
    """The target's definitions compiled from the graph into the statement's own build, by calls
    that can write only there."""
    seam = confined(toolchain, read_write=[judge.statement])
    return defs.compile_all(seam, tc, target_dir, judge.statement, timeout_s=timeout_s)


def collect_modules(judge: Judge, build: Path, order: Sequence[str]) -> list[str]:
    """Copy each staged node's compiled ``Context`` and ``Proof`` from the work directory's
    ``build`` into ``modules/``, and the definitions' oleans from the statement's own build.
    Answers the modules copied, by name. A file that is missing or is not a regular file is not
    copied, and the judging calls then fail to find the module: they fail closed."""
    copied: list[str] = []
    for node_id in order:
        for stem in NODE_STEMS:
            module = layout.node_module(node_id, stem)
            rel = module_output_path(module, ".olean")
            if _copy_regular(build / rel, judge.modules / rel):
                copied.append(module)
    trusted = judge.statement / "build"
    base = trusted / layout.DEFS_PREFIX
    if base.is_dir():
        for olean in sorted(base.rglob("*.olean")):
            rel = olean.relative_to(trusted)
            if _copy_regular(olean, judge.modules / rel):
                copied.append(".".join(rel.with_suffix("").parts))
    return copied


def _copy_regular(source: Path, dest: Path) -> bool:
    if source.is_symlink() or not source.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest, follow_symlinks=False)
    return True
