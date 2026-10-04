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

**Contributed modules (F02-T12).** Step 7's witness and admission's relation proof are
contributor files no earlier step compiled. Each is compiled in a call of its own
(``compile_contributed``), whose only writable directory is a scratch area holding a copy of the
statements' trusted build, under a header the gate writes (``with_header``: the imports the file
may have, read through the statement's own). Only its olean is taken from there, by name, into
``contributed/``, which is never on a ``LEAN_PATH``: the judging program reads it at its path as
data and adds its constants through the kernel, executing nothing of it.

Without the sandbox (``pregate.sh`` on a contributor's own machine) ``confined`` hands back the
same seam: the contributor's code runs on their own machine there, and nothing it does there
decides a merge (D-4: only the gate's run in the sandbox does).
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from opn_gate import defs, layout
from opn_gate.diagnostic import Diagnostic
from opn_gate.toolchain import ElabResult, ResolvedToolchain, Toolchain, module_output_path

#: Beside the work directory, never inside it: ``<work>.judge``.
SUFFIX = ".judge"
STATEMENT_DIR = "meaning"
MODULES_DIR = "modules"
AXIOMS_DIR = "axioms"
#: F02-T12: a contributed module's olean, taken by name from the call that compiled it; read by
#: path as data, never on a ``LEAN_PATH``.
CONTRIBUTED_DIR = "contributed"
#: F02-T12: where a contributed file is compiled, beside the trusted build it is compiled against.
COMPILE_DIR = "compile"
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


def statement_olean(build: Path, node_id: str) -> Path:
    """Where a statement build puts the node's ``Statement`` olean."""
    return build / module_output_path(layout.node_module(node_id, "Statement"), ".olean")


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


# --- F02-T12: statements built from the record, and contributed files compiled apart ------------


def area(workdir: Path, name: str) -> Path:
    """A fresh directory ``<work>.judge/<name>`` for one judgment, made without touching the
    judging directory's other contents (step 4's, when it ran)."""
    path = root_for(workdir) / name
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def build_statements(  # noqa: PLR0913 — one argument per fact the build needs
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    target_dir: Path,
    nodes: Sequence[tuple[str, Path, Path]],
    root: Path,
    *,
    timeout_s: float | None,
) -> Diagnostic | None:
    """The target's definitions, then each node's ``Context.lean`` and ``Statement.lean`` (as
    ``(node id, context, statement)``, read from the files given, which the gate copied from the
    graph or wrote itself), compiled into ``root/build`` by calls that can write only under
    ``root``. The first failure is the answer, coded ``elaboration-failed`` with the module and
    node in its details."""
    seam = confined(toolchain, read_write=[root])
    problem = defs.compile_all(seam, tc, target_dir, root, timeout_s=timeout_s)
    if problem is not None:
        return problem
    src, build = root / "src", root / "build"
    for node_id, context, statement in nodes:
        dest = src / layout.NODES_PREFIX / node_id
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(context, dest / "Context.lean")
        shutil.copyfile(statement, dest / "Statement.lean")
    for node_id, _context, _statement in nodes:
        for stem in ("Context", "Statement"):
            module = layout.node_module(node_id, stem)
            elab = seam.elaborate(
                tc,
                src / layout.NODES_PREFIX / node_id / f"{stem}.lean",
                module,
                build,
                root=src,
                timeout_s=timeout_s,
            )
            if not elab.ok:
                return Diagnostic(
                    "elaboration-failed",
                    f"{module} does not elaborate from the node's own files",
                    {
                        "module": module,
                        "node": node_id,
                        "messages": [m.as_dict() for m in elab.errors or elab.messages],
                        "stderr": elab.stderr,
                    },
                )
    return None


def node_statement(  # noqa: PLR0913 — one argument per fact the build needs
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    target_dir: Path,
    node: layout.Node,
    judge: Judge,
    *,
    timeout_s: float | None,
) -> Diagnostic | None:
    """The node's statement built in ``judge.statement`` from its own files in the graph, once
    per run: a later caller finds the olean there and builds nothing."""
    build = judge.statement / "build"
    if statement_olean(build, node.node_id).is_file():
        return None
    return build_statements(
        toolchain,
        tc,
        target_dir,
        [(node.node_id, node.path / "Context.lean", node.path / "Statement.lean")],
        judge.statement,
        timeout_s=timeout_s,
    )


#: One line of a file's header: an import (``public``/``meta`` modifiers allowed), a blank line or
#: a line comment. A block comment is passed over whole.
_HEADER_IMPORT_RE = re.compile(r"^\s*(?:public\s+)?(?:meta\s+)?import\s+(?P<module>\S+)\s*$")


def _header_lines(text: str) -> list[tuple[int, str | None]]:
    """The header's lines by index, each with the module it imports (``None`` for a blank line or
    a comment); the header ends at the first line that is neither."""
    out: list[tuple[int, str | None]] = []
    in_block = 0
    for index, line in enumerate(text.split("\n")):
        stripped = line.strip()
        if in_block or stripped.startswith("/-"):
            in_block += stripped.count("/-") - stripped.count("-/")
            in_block = max(in_block, 0)
            out.append((index, None))
            continue
        if not stripped or stripped.startswith("--"):
            out.append((index, None))
            continue
        m = _HEADER_IMPORT_RE.match(line)
        if m is None:
            break
        out.append((index, m.group("module")))
    return out


def header_imports(text: str) -> list[str]:
    """The modules a file's header imports, in order, once each."""
    seen: list[str] = []
    for _index, module in _header_lines(text):
        if module is not None and module not in seen:
            seen.append(module)
    return seen


def with_header(text: str, imports: Sequence[str]) -> str:
    """``text`` with its header's import lines blanked and ``imports`` put first on its first line,
    so every later line keeps its number and the file is compiled under exactly the imports the
    gate chose (F02-T12): a witness under its statement's module, a relation proof under the
    statements' imports."""
    lines = text.split("\n")
    for index, module in _header_lines(text):
        if module is not None:
            lines[index] = ""
    prefix = "".join(f"import {m} " for m in imports)
    return prefix + "\n".join(lines)


def compile_contributed(  # noqa: PLR0913 — one argument per fact the compile needs
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    *,
    text: str,
    module: str,
    trusted_build: Path,
    where: Path,
    timeout_s: float | None,
) -> tuple[ElabResult, Path | None]:
    """Compile a contributor's file as ``module`` in a call whose only writable directory is
    ``where/compile``, holding a copy of ``trusted_build`` (the one place its imports can resolve
    besides the toolchain and Mathlib). Contributor code may run in this call and write anything
    there; what is taken from it is the module's own olean, a regular file copied by name into
    ``where/contributed``. Answers the compile's result and that olean's path (``None`` when the
    compile failed or left none)."""
    work = where / COMPILE_DIR
    if work.exists():
        shutil.rmtree(work)
    build = work / "build"
    if trusted_build.is_dir():
        shutil.copytree(trusted_build, build, symlinks=False)
    build.mkdir(parents=True, exist_ok=True)
    rel = module_output_path(module, ".lean")
    source = work / "src" / rel
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(text, encoding="utf-8")
    seam = confined(toolchain, read_write=[work])
    elab = seam.elaborate(tc, source, module, build, root=work / "src", timeout_s=timeout_s)
    if not elab.ok:
        return elab, None
    dest = where / CONTRIBUTED_DIR / module_output_path(module, ".olean")
    if not _copy_regular(build / module_output_path(module, ".olean"), dest):
        return ElabResult(ok=False, messages=elab.messages, stderr=elab.stderr), None
    return elab, dest
