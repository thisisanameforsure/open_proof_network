"""A target's definitions in the build (F11-R2, R7; D-6, D-7; F01-Q2).

``targets/<id>/defs/*.lean`` are the objects a target's statements are stated over — the on-ramp
graph's ``Divides``, ``IsPrime`` and ``fact`` — and every node file may ``import Defs.<Name>``
(F01-Q2's module contract). Until F11 no graph had any, so nothing staged them: a node importing
one would have failed step 4 with "unknown module". This module is that staging, used by every
place the gate compiles a node's Context: the pipeline's build (``steps.replay``), admission's
statement check (``steps.hazards.StatementStep``), the tag scan, the exhibits, the curator's
consolidation probe, intake's own definition check and the olean cache build.

Order matters: a definition may import another (``IsPrime`` imports ``Divides``), so the files
are sorted by their ``import Defs.*`` lines, a cycle is a refusal, and a file whose name is not a
Lean identifier is refused before it can become a module nobody can import.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from opn_gate import layout
from opn_gate.diagnostic import Diagnostic
from opn_gate.toolchain import ResolvedToolchain, Toolchain

DEFS_DIR = "defs"
#: A definition file's stem must be a plain Lean identifier: it becomes the module ``Defs.<stem>``.
_STEM_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*$")


@dataclass(frozen=True)
class Definition:
    module: str  # ``Defs.<stem>``
    source: Path  # the file in the target's ``defs/``
    staged: Path  # the copy under ``<src>/Defs/``


def target_defs_dir(target_dir: Path) -> Path:
    return target_dir / DEFS_DIR


def order(target_dir: Path) -> list[Definition] | Diagnostic:
    """The target's definitions in build order (imports first), or why they cannot be built.

    ``staged`` paths are relative to a source root the caller supplies through ``stage``; here
    they are the source paths, so the order can be computed without writing anything.
    """
    defs_dir = target_defs_dir(target_dir)
    if not defs_dir.is_dir():
        return []
    files = sorted(p for p in defs_dir.iterdir() if p.is_file() and p.suffix == ".lean")
    stems: dict[str, Path] = {}
    for path in files:
        if not _STEM_RE.match(path.stem):
            return Diagnostic(
                "defs-name",
                f"defs/{path.name} is not a Lean module name; a definition file is named "
                f"<Identifier>.lean and becomes Defs.<Identifier>",
                {"file": path.name},
            )
        stems[path.stem] = path
    deps: dict[str, list[str]] = {}
    for stem, path in stems.items():
        wanted: list[str] = []
        for module in layout.imports_of(path.read_text(encoding="utf-8")):
            kind, _ = layout.module_origin(module)
            if kind == "defs":
                target = module.partition(".")[2]
                if target not in stems:
                    return Diagnostic(
                        "defs-import",
                        f"defs/{path.name} imports {module}, which is not a definition of "
                        "this target",
                        {"file": path.name, "module": module},
                    )
                wanted.append(target)
            elif kind != "library":
                return Diagnostic(
                    "defs-import",
                    f"defs/{path.name} imports {module}; a definition imports library modules "
                    "and other definitions only (F01-Q2)",
                    {"file": path.name, "module": module},
                )
        deps[stem] = wanted
    ordered: list[str] = []
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(stem: str, chain: tuple[str, ...]) -> Diagnostic | None:
        if state.get(stem) == 2:
            return None
        if state.get(stem) == 1:
            return Diagnostic(
                "defs-cycle",
                "definition import cycle: " + " -> ".join((*chain, stem)),
                {"cycle": [*chain, stem]},
            )
        state[stem] = 1
        for dep in deps[stem]:
            problem = visit(dep, (*chain, stem))
            if problem is not None:
                return problem
        state[stem] = 2
        ordered.append(stem)
        return None

    for stem in sorted(stems):
        problem = visit(stem, ())
        if problem is not None:
            return problem
    return [
        Definition(f"{layout.DEFS_PREFIX}.{stem}", stems[stem], stems[stem]) for stem in ordered
    ]


def stage(target_dir: Path, src: Path) -> list[Definition] | Diagnostic:
    """Copy the definitions under ``<src>/Defs/`` in build order."""
    ordered = order(target_dir)
    if isinstance(ordered, Diagnostic):
        return ordered
    dest = src / layout.DEFS_PREFIX
    staged: list[Definition] = []
    for d in ordered:
        dest.mkdir(parents=True, exist_ok=True)
        copy = dest / d.source.name
        shutil.copy(d.source, copy)
        staged.append(Definition(d.module, d.source, copy))
    return staged


def compile_all(  # noqa: PLR0913 — one argument per fact the build needs
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    target_dir: Path,
    workdir: Path,
    *,
    timeout_s: float | None = None,
    skip_built: bool = True,
) -> Diagnostic | None:
    """Stage and elaborate every definition into ``<workdir>/build``, in order; the first failure
    is the answer. Idempotent: a module whose olean is already in the build directory is not
    recompiled, so the callers that share a work directory pay once."""
    from opn_gate.toolchain import module_output_path  # noqa: PLC0415 — avoid an import cycle

    src = workdir / "src"
    build = workdir / "build"
    staged = stage(target_dir, src)
    if isinstance(staged, Diagnostic):
        return staged
    build.mkdir(parents=True, exist_ok=True)
    for d in staged:
        if skip_built and (build / module_output_path(d.module, ".olean")).is_file():
            continue
        try:
            elab = toolchain.elaborate(tc, d.staged, d.module, build, root=src, timeout_s=timeout_s)
        except subprocess.TimeoutExpired:
            return Diagnostic(
                "timeout", f"compiling {d.module} exceeded the wall-clock cap", {"module": d.module}
            )
        if not elab.ok:
            return Diagnostic(
                "defs-elaboration",
                f"{d.module} (defs/{d.source.name}) does not elaborate",
                {
                    "module": d.module,
                    "file": d.source.name,
                    "messages": [m.as_dict() for m in elab.errors or elab.messages],
                },
            )
    return None
