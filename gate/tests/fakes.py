"""Fakes for the gate's seams (conventions §1, §2).

``FakeToolchain`` returns the structured records the seam defines; it never imitates Lean's
stdout, so the fast tier cannot drift silently — drift is caught by the real tier.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from opn_gate.toolchain import (
    AxiomResult,
    ElabResult,
    MetaprogramResult,
    ReplayResult,
    ResolvedToolchain,
    ToolchainMissingError,
    UsedConstantsRequest,
    WitnessRequest,
    module_output_path,
)

FAKE_RESOLVED = ResolvedToolchain(
    name="leanprover/lean4:v4.33.1",
    version="4.33.1",
    githash="819816b2e0a3bf405af45ae5c7af2491d8f5bee6",
    libdir=Path("/fake/elan/lib/lean"),
)


def witness_result(
    *,
    expected: str,
    witness: str | None,
    defeq: bool | None = None,
    axioms: tuple[str, ...] = (),
) -> MetaprogramResult:
    """A structured ``opn-witness-type`` result, as the real seam would parse it."""
    return MetaprogramResult(
        ok=True,
        doc={
            "ok": True,
            "expected": expected,
            "witness": witness,
            "defeq": (witness == expected) if defeq is None else defeq,
            "witness_axioms": list(axioms),
        },
    )


def used_constants_result(
    constants: list[tuple[str, str | None]], *, axioms: tuple[str, ...] = ()
) -> MetaprogramResult:
    """A structured ``opn-used-constants`` result: (name, module-or-None-for-submission) pairs."""
    return MetaprogramResult(
        ok=True,
        doc={
            "ok": True,
            "constants": [{"name": n, "module": m} for n, m in constants],
            "axioms": list(axioms),
        },
    )


LIBRARY_CONSTANTS: list[tuple[str, str | None]] = [
    ("And", "Init.Prelude"),
    ("And.intro", "Init.Prelude"),
    ("And.left", "Init.Prelude"),
    ("And.right", "Init.Prelude"),
]


def metaprogram_garbage(
    exit_code: int = 1, output: str = "Segmentation fault\n"
) -> MetaprogramResult:
    """R9: a metaprogram that exited non-zero with no JSON."""
    return MetaprogramResult(ok=False, exit_code=exit_code, output=output)


@dataclass
class FakeToolchain:
    """Scriptable seam. Each result is returned as configured; every call is recorded."""

    resolved: ResolvedToolchain = FAKE_RESOLVED
    elab: ElabResult = field(default_factory=lambda: ElabResult(ok=True))
    replay: ReplayResult = field(default_factory=lambda: ReplayResult(ok=True))
    axiom_result: AxiomResult = field(default_factory=lambda: AxiomResult(ok=True))
    witness: MetaprogramResult = field(
        default_factory=lambda: witness_result(expected="∃ p q, p ∧ q", witness="∃ p q, p ∧ q")
    )
    constants: MetaprogramResult = field(
        default_factory=lambda: used_constants_result(LIBRARY_CONSTANTS)
    )
    missing: bool = False
    raise_on: str | None = None  # name of the method that should raise an unexpected error
    calls: list[str] = field(default_factory=list)

    def _maybe_raise(self, name: str) -> None:
        if self.raise_on == name:
            msg = f"fake toolchain blew up in {name}"
            raise RuntimeError(msg)

    def resolve(self, toolchain: str, *, install: bool = False) -> ResolvedToolchain:
        self.calls.append(f"resolve:{toolchain}:install={install}")
        self._maybe_raise("resolve")
        if self.missing:
            msg = f"toolchain {toolchain} is not installed (fake)"
            raise ToolchainMissingError(msg)
        return self.resolved

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
        self.calls.append(f"elaborate:{module}")
        self._maybe_raise("elaborate")
        if self.elab.ok:
            olean = out_dir / module_output_path(module, ".olean")
            olean.parent.mkdir(parents=True, exist_ok=True)
            olean.write_bytes(b"fake olean")
        return self.elab

    def kernel_replay(
        self,
        tc: ResolvedToolchain,
        module: str,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> ReplayResult:
        self.calls.append(f"kernel_replay:{module}")
        self._maybe_raise("kernel_replay")
        return self.replay

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
        self.calls.append(f"axioms:{module}:{decl}")
        self._maybe_raise("axioms")
        return self.axiom_result

    def witness_type(
        self,
        tc: ResolvedToolchain,
        req: WitnessRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        self.calls.append(f"witness_type:{req.decl}:{req.witness is not None}")
        self._maybe_raise("witness_type")
        return self.witness

    def used_constants(
        self,
        tc: ResolvedToolchain,
        req: UsedConstantsRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        self.calls.append(f"used_constants:{req.decl}")
        self._maybe_raise("used_constants")
        return self.constants
