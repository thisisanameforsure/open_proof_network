"""The ``Toolchain`` seam: the one module that talks to elan, lean and leanchecker.

Conventions §1 names this seam; §2 requires that its fake returns structured results and never
imitates Lean's stdout. Everything the gate learns from the toolchain therefore crosses this
boundary as one of the small records below.

Kernel replay uses ``leanchecker --fresh``: lean4checker was merged into the Lean toolchain at
v4.28.0 and ships under that name (F00-Q10), so no separate checker is installed.

Run ``python -m opn_gate.toolchain --require`` to check that elan is reachable; it exits 1 with a
diagnostic naming the install script otherwise (F00-R16).
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from opn_gate import config

INSTALL_SCRIPT = "gate/scripts/install-toolchain.sh"

#: Axiom names that mean the proof leaned on the compiler instead of the kernel (D-4).
NATIVE_DECIDE_MARKERS: tuple[str, ...] = ("native_decide", "Lean.ofReduceBool")

_AXIOMS_RE = re.compile(r"^'(?P<decl>[^']+)' depends on axioms: \[(?P<axioms>[^\]]*)\]\s*$", re.M)
_NO_AXIOMS_RE = re.compile(r"^'(?P<decl>[^']+)' does not depend on any axioms\s*$", re.M)


class ToolchainMissingError(RuntimeError):
    """elan or the pinned toolchain is not available on this machine."""


class ToolchainError(RuntimeError):
    """The toolchain ran but its output could not be interpreted."""


@dataclass(frozen=True)
class ResolvedToolchain:
    """What step 1 pins: a toolchain name and the Lean commit it resolves to."""

    name: str
    version: str
    githash: str
    libdir: Path

    @property
    def toolchain_hash(self) -> str:
        """sha256 over name and commit — platform-independent, so identical on every runner."""
        return hashlib.sha256(f"{self.name}\n{self.githash}\n".encode()).hexdigest()


@dataclass(frozen=True)
class Message:
    """One diagnostic from ``lean --json``."""

    file: str
    line: int
    column: int
    severity: str
    text: str

    def as_dict(self) -> dict[str, object]:
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "text": self.text,
        }


@dataclass(frozen=True)
class ElabResult:
    ok: bool
    messages: tuple[Message, ...] = ()
    stderr: str = ""

    @property
    def errors(self) -> tuple[Message, ...]:
        return tuple(m for m in self.messages if m.severity == "error")


@dataclass(frozen=True)
class ReplayResult:
    ok: bool
    output: str = ""


@dataclass(frozen=True)
class AxiomResult:
    ok: bool
    axioms: frozenset[str] = field(default_factory=frozenset)
    output: str = ""


class Toolchain(Protocol):
    """Everything the gate steps need from Lean, in order of use."""

    def resolve(self, toolchain: str, *, install: bool = False) -> ResolvedToolchain:
        """Step 1: make ``toolchain`` available and report what it is."""

    def elaborate(
        self,
        tc: ResolvedToolchain,
        source: Path,
        module: str,
        out_dir: Path,
        *,
        timeout_s: float | None = None,
    ) -> ElabResult:
        """Compile ``source`` as module ``module`` into ``out_dir/<module>.olean``."""

    def kernel_replay(
        self,
        tc: ResolvedToolchain,
        module: str,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> ReplayResult:
        """Step 4: ``leanchecker --fresh module`` over ``search_path``."""

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
        """Step 5: the axioms ``decl`` (defined in ``module``) depends on."""


# --- helpers shared by the real implementation and its tests --------------------------------


def is_native_decide_axiom(name: str) -> bool:
    return any(marker in name for marker in NATIVE_DECIDE_MARKERS)


def parse_axioms(output: str, decl: str) -> frozenset[str] | None:
    """Read ``#print axioms`` output for ``decl``; ``None`` if it is not there."""
    for m in _AXIOMS_RE.finditer(output):
        if m.group("decl") == decl:
            raw = m.group("axioms").strip()
            return frozenset(a.strip() for a in raw.split(",") if a.strip())
    for m in _NO_AXIOMS_RE.finditer(output):
        if m.group("decl") == decl:
            return frozenset()
    return None


def parse_json_messages(stdout: str) -> tuple[Message, ...]:
    """Parse ``lean --json`` output: one JSON object per line; other lines are ignored."""
    out: list[Message] = []
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        pos = obj.get("pos") or {}
        out.append(
            Message(
                file=str(obj.get("fileName", "")),
                line=int(pos.get("line", 0)),
                column=int(pos.get("column", 0)),
                severity=str(obj.get("severity", "error")),
                text=str(obj.get("data", "")),
            )
        )
    return tuple(out)


def find_elan(*, path_env: str | None, elan_home: Path) -> Path:
    """Locate the elan binary on ``path_env`` or under ``elan_home``; raise if neither has it."""
    found = shutil.which("elan", path=path_env) if path_env is not None else shutil.which("elan")
    if found:
        return Path(found)
    candidate = elan_home / "bin" / "elan"
    if candidate.is_file():
        return candidate
    msg = (
        f"elan not found on PATH or at {candidate}. The pinned Lean toolchain is installed by "
        f"{INSTALL_SCRIPT} (it never edits your shell config; set OPN_ELAN_HOME if elan lives "
        "elsewhere)."
    )
    raise ToolchainMissingError(msg)


def _join_search_path(search_path: Sequence[Path]) -> str:
    return ":".join(str(p.resolve()) for p in search_path)


class LocalToolchain:
    """The real seam: shells out to elan-managed binaries. Used by pregate.sh, CI and reproduce."""

    def __init__(self, elan: Path) -> None:
        self.elan = elan

    @classmethod
    def from_settings(cls, settings: config.Settings) -> LocalToolchain:
        return cls(find_elan(path_env=None, elan_home=settings.elan_home))

    # -- process plumbing ---------------------------------------------------------------------

    def _exec(
        self,
        cmd: Sequence[str],
        *,
        cwd: Path | None = None,
        extra_env: dict[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """The one place a process is started. The sandbox seam overrides this alone."""
        return subprocess.run(
            list(cmd),
            cwd=cwd,
            env=_env_with(extra_env),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )

    def _elan(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return self._exec([str(self.elan), *args])

    def _run(
        self,
        tc_name: str,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        lean_path: Sequence[Path] | None = None,
        timeout_s: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        extra_env = None
        if lean_path is not None:
            extra_env = {"LEAN_PATH": _join_search_path(lean_path)}
        return self._exec(
            [str(self.elan), "run", tc_name, *args],
            cwd=cwd,
            extra_env=extra_env,
            timeout_s=timeout_s,
        )

    # -- the seam -----------------------------------------------------------------------------

    def resolve(self, toolchain: str, *, install: bool = False) -> ResolvedToolchain:
        listed = self._elan(["toolchain", "list"])
        installed = {line.split()[0] for line in listed.stdout.splitlines() if line.strip()}
        if toolchain not in installed:
            if not install:
                msg = (
                    f"toolchain {toolchain} is not installed under elan "
                    f"({self.elan}); run {INSTALL_SCRIPT} {toolchain}"
                )
                raise ToolchainMissingError(msg)
            done = self._elan(["toolchain", "install", toolchain])
            if done.returncode != 0:
                msg = f"elan toolchain install {toolchain} failed: {done.stderr.strip()}"
                raise ToolchainMissingError(msg)
        version = self._run(toolchain, ["lean", "--version"])
        githash = self._run(toolchain, ["lean", "--githash"])
        libdir = self._run(toolchain, ["lean", "--print-libdir"])
        for proc in (version, githash, libdir):
            if proc.returncode != 0:
                msg = f"lean under {toolchain} failed: {proc.stderr.strip()}"
                raise ToolchainError(msg)
        m = re.search(r"version (\S+),", version.stdout)
        if not m:
            msg = f"could not parse lean --version output: {version.stdout!r}"
            raise ToolchainError(msg)
        return ResolvedToolchain(
            name=toolchain,
            version=m.group(1),
            githash=githash.stdout.strip(),
            libdir=Path(libdir.stdout.strip()),
        )

    def elaborate(
        self,
        tc: ResolvedToolchain,
        source: Path,
        module: str,
        out_dir: Path,
        *,
        timeout_s: float | None = None,
    ) -> ElabResult:
        out_dir = out_dir.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        olean = out_dir / f"{module}.olean"
        ilean = out_dir / f"{module}.ilean"
        proc = self._run(
            tc.name,
            ["lean", "--json", "-o", str(olean), "-i", str(ilean), source.name],
            cwd=source.resolve().parent,
            lean_path=[out_dir, tc.libdir],
            timeout_s=timeout_s,
        )
        messages = parse_json_messages(proc.stdout)
        ok = proc.returncode == 0 and olean.is_file()
        return ElabResult(ok=ok, messages=messages, stderr=proc.stderr)

    def kernel_replay(
        self,
        tc: ResolvedToolchain,
        module: str,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> ReplayResult:
        proc = self._run(
            tc.name,
            ["leanchecker", "--fresh", module],
            lean_path=[*search_path, tc.libdir],
            timeout_s=timeout_s,
        )
        return ReplayResult(ok=proc.returncode == 0, output=proc.stdout + proc.stderr)

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
        scratch = scratch.resolve()
        scratch.mkdir(parents=True, exist_ok=True)
        probe = scratch / "OpnAxioms.lean"
        probe.write_text(f"import {module}\n#print axioms {decl}\n", encoding="utf-8")
        proc = self._run(
            tc.name,
            ["lean", probe.name],
            cwd=scratch,
            lean_path=[*search_path, tc.libdir],
            timeout_s=timeout_s,
        )
        output = proc.stdout + proc.stderr
        axioms = parse_axioms(proc.stdout, decl)
        if proc.returncode != 0 or axioms is None:
            return AxiomResult(ok=False, output=output)
        return AxiomResult(ok=True, axioms=axioms, output=output)


def _env_with(extra: dict[str, str] | None) -> dict[str, str] | None:
    """The child's environment: the inherited one plus ``extra`` (read via config only, R17)."""
    if not extra:
        return None
    return config.child_environment(extra)


def main(argv: Sequence[str] | None = None) -> int:
    """``python -m opn_gate.toolchain --require``: exit 0 if elan is reachable, else 1."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ["--require"]:
        sys.stderr.write("usage: python -m opn_gate.toolchain --require\n")
        return 2
    settings = config.load()
    try:
        elan = find_elan(path_env=None, elan_home=settings.elan_home)
    except ToolchainMissingError as exc:
        sys.stderr.write(f"verify-lean: {exc}\n")
        return 1
    sys.stdout.write(f"verify-lean: elan at {elan}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
