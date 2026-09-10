"""A fake toolchain that fails or times out on demand, per module or per method.

``FakeToolchain`` answers every elaboration the same way, which cannot separate "the node's
Context compiles but its Statement does not" from "nothing compiles" — and several gate branches
exist only for that difference. This subclass scripts the difference, and the wall-clock cap's
``TimeoutExpired``, which the base fake never raises.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from fakes import FakeToolchain

from opn_gate.toolchain import (
    ArtifactRequest,
    AxiomResult,
    ElabResult,
    MetaprogramResult,
    RelationRequest,
    ResolvedToolchain,
)


def _timeout(what: str) -> subprocess.TimeoutExpired:
    return subprocess.TimeoutExpired(cmd=what, timeout=1.0)


@dataclass
class ScriptedToolchain(FakeToolchain):
    """``failing_modules`` do not elaborate; ``timeout_modules`` exceed the cap; ``timeout_on``
    names methods (``axioms``, ``artifact_type``, ``relation_type``) that exceed it."""

    failing_modules: set[str] = field(default_factory=set)
    timeout_modules: set[str] = field(default_factory=set)
    timeout_on: set[str] = field(default_factory=set)

    def elaborate(
        self,
        tc: ResolvedToolchain,
        source: Path,
        module: str,
        out_dir: Path,
        *,
        root: Path | None = None,
        timeout_s: float | None = None,
    ) -> ElabResult:
        if module in self.timeout_modules:
            self.calls.append(f"elaborate:{module}")
            raise _timeout(module)
        if module in self.failing_modules:
            self.calls.append(f"elaborate:{module}")
            return ElabResult(ok=False)
        return super().elaborate(tc, source, module, out_dir, root=root, timeout_s=timeout_s)

    def axioms(
        self,
        tc: ResolvedToolchain,
        module: str,
        decl: str,
        search_path: Sequence[Path],
        scratch: Path,
        *,
        timeout_s: float | None = None,
    ) -> AxiomResult:
        if "axioms" in self.timeout_on:
            raise _timeout("axioms")
        return super().axioms(tc, module, decl, search_path, scratch, timeout_s=timeout_s)

    def artifact_type(
        self,
        tc: ResolvedToolchain,
        req: ArtifactRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        if "artifact_type" in self.timeout_on:
            raise _timeout("opn-artifact-type")
        return super().artifact_type(tc, req, search_path, timeout_s=timeout_s)

    def relation_type(
        self,
        tc: ResolvedToolchain,
        req: RelationRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        if "relation_type" in self.timeout_on:
            raise _timeout("opn-relation-type")
        return super().relation_type(tc, req, search_path, timeout_s=timeout_s)
