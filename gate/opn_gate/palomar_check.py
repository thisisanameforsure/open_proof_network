"""The export's local check at the graph's pin (F25-R11): Stage A's proof that the wrapper is
the record.

Over the gate's own toolchain seam and nothing else — no Lake, no network: every module of the
exported project elaborates in build order, each is replayed through the kernel, the Solution's
theorem rests on the allowed axioms only, and ``opn-statement-meaning`` says by the kernel that
the Solution's declaration has the Challenge's type. Every answer is written to
``local-check.json``; the caller exits non-zero on any failure.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import palomar, toolchain
from opn_gate.toolchain import MeaningRequest, ResolvedToolchain, Toolchain

REPORT = "local-check.json"
BUILD_DIR = ".opn-check/build"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Report:
    ok: bool
    toolchain: str
    checks: list[Check] = field(default_factory=list)
    axioms: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "opn-local-check/v1",
            "ok": self.ok,
            "toolchain": self.toolchain,
            "modules": self.modules,
            "axioms": self.axioms,
            "checks": [asdict(c) for c in self.checks],
        }


def module_of(rel: str) -> str:
    """``OpnX/Nodes/a_b.lean`` → ``OpnX.Nodes.a_b``; ``Challenge.lean`` → ``Challenge``."""
    return rel.removesuffix(".lean").replace("/", ".")


def development_modules(project: Path, package: str) -> list[str]:
    """The project's Lean files in build order: definitions, nodes (as the library root lists
    them, dependencies first), the library root, then Solution; Challenge is checked apart."""
    root = project / f"{package}.lean"
    listed = [
        line.removeprefix("public import ").strip()
        for line in root.read_text(encoding="utf-8").splitlines()
        if line.startswith("public import ")
    ]
    return [*listed, package, "Solution"]


def local_check(  # noqa: PLR0912, PLR0913, PLR0915 — one check per clause of F25-R11
    tc_seam: Toolchain,
    tc: ResolvedToolchain,
    project: Path,
    *,
    package: str,
    decl: str,
    allowlist: list[str],
    timeout_s: float | None = None,
) -> Report:
    build = project / BUILD_DIR
    build.mkdir(parents=True, exist_ok=True)
    report = Report(ok=True, toolchain=tc.name)
    modules = development_modules(project, package)
    report.modules = [*modules, "Challenge"]
    search = tc.search_path(build)

    def fail(name: str, detail: str) -> None:
        report.ok = False
        report.checks.append(Check(name, False, detail))

    # 1. elaboration, in build order, then the Challenge on its own
    for module in report.modules:
        source = project / (module.replace(".", "/") + ".lean")
        result = tc_seam.elaborate(tc, source, module, build, root=project, timeout_s=timeout_s)
        if result.ok:
            report.checks.append(Check(f"elaborate {module}", True))
        else:
            fail(
                f"elaborate {module}",
                "; ".join(f"{m.file}:{m.line}:{m.column}: {m.text}" for m in result.errors)
                or result.stderr[-2000:],
            )
    if not report.ok:
        _write(project, report)
        return report
    # 2. kernel replay: fresh over Solution on a core-only project; per module when Mathlib is
    #    pinned (F02-T7's shape, so one process never holds every module's environment)
    if tc.mathlib_sha is None:
        replay = tc_seam.kernel_replay(tc, ["Solution"], search, fresh=True, timeout_s=timeout_s)
        report.checks.append(
            Check("replay Solution (fresh)", replay.ok, "" if replay.ok else replay.output[-2000:])
        )
        report.ok = report.ok and replay.ok
    else:
        for module in modules:
            replay = tc_seam.kernel_replay(tc, [module], search, fresh=False, timeout_s=timeout_s)
            report.checks.append(
                Check(f"replay {module}", replay.ok, "" if replay.ok else replay.output[-2000:])
            )
            report.ok = report.ok and replay.ok
    # 3. axioms of the Solution's theorem
    axioms = tc_seam.axioms(
        tc, "Solution", decl, search, project / ".opn-check", timeout_s=timeout_s
    )
    if not axioms.ok:
        fail("axioms", axioms.output[-2000:])
    else:
        report.axioms = sorted(axioms.axioms)
        extra = sorted(a for a in axioms.axioms if a not in set(allowlist))
        native = [a for a in axioms.axioms if toolchain.is_native_decide_axiom(a)]
        if extra or native:
            fail("axioms", f"outside the allowlist: {extra}; compiler-trusting: {native}")
        else:
            report.checks.append(Check("axioms", True, ", ".join(report.axioms)))
    # 4. the Solution's declaration has the Challenge's type, by the kernel
    req = MeaningRequest(
        statement_olean=build / "Challenge.olean",
        decl=decl,
        artifact_module="Solution",
        artifact_decl=decl,
    )
    meaning = tc_seam.statement_meaning(tc, req, search, timeout_s=timeout_s)
    if not meaning.ok or not meaning.doc.get("matches"):
        fail(
            "statement-meaning",
            meaning.error or meaning.output[-2000:] or json.dumps(meaning.doc)[:2000],
        )
    else:
        report.checks.append(
            Check(
                "statement-meaning",
                True,
                "identical" if meaning.doc.get("identical") else "definitionally equal",
            )
        )
    # 5. the export record's hashes are the files'
    record_path = project / "opn-export.json"
    if record_path.is_file():
        record = json.loads(record_path.read_text(encoding="utf-8"))
        wrong = [
            rel
            for rel, digest in record.get("hashes_out", {}).items()
            if palomar.measure(b"") is not None and _sha(project / rel) != digest
        ]
        if wrong:
            fail("record-hashes", f"files changed since the export: {wrong}")
        else:
            report.checks.append(
                Check("record-hashes", True, f"{len(record.get('hashes_out', {}))} files")
            )
    _write(project, report)
    return report


def _sha(path: Path) -> str:
    import hashlib  # noqa: PLC0415

    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _write(project: Path, report: Report) -> None:
    (project / REPORT).write_text(json.dumps(report.as_dict(), indent=2) + "\n", encoding="utf-8")
