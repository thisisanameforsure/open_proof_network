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
from typing import Any, Protocol

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
    """What step 1 pins: a toolchain name and the Lean commit it resolves to — and, for a graph
    that pins Mathlib (D-7; F11-R6), the library search path of that checkout's built oleans,
    which every ``lean`` and metaprogram invocation is handed after the build directory and
    before the toolchain's own lib. The path is where *this* host keeps the checkout and is
    never recorded; ``mathlib_sha`` is what the attestation carries (D-5)."""

    name: str
    version: str
    githash: str
    libdir: Path
    mathlib_sha: str | None = None
    library_path: tuple[Path, ...] = ()

    @property
    def toolchain_hash(self) -> str:
        """sha256 over name and commit — platform-independent, so identical on every runner."""
        return hashlib.sha256(f"{self.name}\n{self.githash}\n".encode()).hexdigest()

    def search_path(self, *before: Path) -> list[Path]:
        """``LEAN_PATH`` in the gate's order: the caller's build directories, then Mathlib's
        packages when pinned, then the toolchain's lib — the one place the order is decided."""
        return [*before, *self.library_path, self.libdir]


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


@dataclass(frozen=True)
class WitnessRequest:
    """Inputs of ``opn-witness-type`` (F01-R3)."""

    statement: Path
    statement_module: str
    decl: str
    witness: Path | None = None
    witness_module: str | None = None

    def args(self) -> list[str]:
        out = [
            "--statement",
            str(self.statement.resolve()),
            "--module",
            self.statement_module,
            "--decl",
            self.decl,
        ]
        if self.witness is not None and self.witness_module is not None:
            out += [
                "--witness",
                str(self.witness.resolve()),
                "--witness-module",
                self.witness_module,
            ]
        return out


@dataclass(frozen=True)
class UsedConstantsRequest:
    """Inputs of ``opn-used-constants`` (F01-R4)."""

    file: Path
    module: str
    decl: str

    def args(self) -> list[str]:
        return ["--file", str(self.file.resolve()), "--module", self.module, "--decl", self.decl]


@dataclass(frozen=True)
class ArtifactRequest:
    """Inputs of ``opn-artifact-type`` (F07-R4, R5): the statement, and the artifact beside it."""

    statement: Path
    statement_module: str
    decl: str
    artifact: Path
    artifact_module: str
    artifact_decl: str
    kind: str  # proof | counterexample | vacuity | partial | reduction

    def args(self) -> list[str]:
        return [
            "--statement",
            str(self.statement.resolve()),
            "--module",
            self.statement_module,
            "--decl",
            self.decl,
            "--artifact",
            str(self.artifact.resolve()),
            "--artifact-module",
            self.artifact_module,
            "--artifact-decl",
            self.artifact_decl,
            "--kind",
            self.kind,
        ]


@dataclass(frozen=True)
class RelationRequest:
    """Inputs of ``opn-relation-type`` (D-30; F08-R4): a variant, its target's root, the claim."""

    variant: Path
    variant_module: str
    variant_decl: str
    root: Path
    root_module: str
    root_decl: str
    label: str  # resolves | partial | related
    relation: Path | None = None
    relation_module: str | None = None
    relation_decl: str = "relation"

    def args(self) -> list[str]:
        out = [
            "--variant",
            str(self.variant.resolve()),
            "--variant-module",
            self.variant_module,
            "--variant-decl",
            self.variant_decl,
            "--root",
            str(self.root.resolve()),
            "--root-module",
            self.root_module,
            "--root-decl",
            self.root_decl,
            "--label",
            self.label,
        ]
        if self.relation is not None and self.relation_module is not None:
            out += [
                "--relation",
                str(self.relation.resolve()),
                "--relation-module",
                self.relation_module,
                "--relation-decl",
                self.relation_decl,
            ]
        return out


@dataclass(frozen=True)
class HazardsRequest:
    """Inputs of ``opn-hazards`` (F02-R1, R3): the statement and exactly the checkers to run."""

    statement: Path
    module: str
    decl: str
    checkers: tuple[str, ...]

    def args(self) -> list[str]:
        return [
            "--statement",
            str(self.statement.resolve()),
            "--module",
            self.module,
            "--decl",
            self.decl,
            "--checkers",
            ",".join(self.checkers),
        ]


@dataclass(frozen=True)
class MetaprogramResult:
    """What a gate metaprogram (F01-R1) returned: parsed JSON on success, raw output otherwise."""

    ok: bool
    doc: dict[str, Any] = field(default_factory=dict)
    exit_code: int = 0
    output: str = ""  # first 8 KiB of stdout+stderr when the contract was not honoured (R9)

    @property
    def error(self) -> str | None:
        err = self.doc.get("error")
        return str(err) if err is not None else None

    @property
    def messages(self) -> tuple[Message, ...]:
        raw = self.doc.get("messages") or []
        return tuple(
            Message(
                file="",
                line=int(m.get("line", 0)),
                column=int(m.get("column", 0)),
                severity=str(m.get("severity", "error")),
                text=str(m.get("text", "")),
            )
            for m in raw
            if isinstance(m, dict)
        )


METAPROGRAM_OUTPUT_CAP = 8192

#: The executables the Lake package builds (F01-R1, F02-R1, F07-R4).
METAPROGRAMS: tuple[str, ...] = (
    "opn-witness-type",
    "opn-used-constants",
    "opn-hazards",
    "opn-artifact-type",
    "opn-relation-type",
)


def parse_metaprogram_output(exit_code: int, stdout: str, stderr: str) -> MetaprogramResult:
    """R1/R9: the last stdout line must be one JSON object; anything else is a failure."""
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    doc: Any = None
    if lines:
        try:
            doc = json.loads(lines[-1])
        except json.JSONDecodeError:
            doc = None
    if not isinstance(doc, dict) or "ok" not in doc:
        capped = (stdout + stderr)[:METAPROGRAM_OUTPUT_CAP]
        return MetaprogramResult(ok=False, exit_code=exit_code, output=capped)
    return MetaprogramResult(ok=bool(doc["ok"]) and exit_code == 0, doc=doc, exit_code=exit_code)


class Toolchain(Protocol):
    """Everything the gate steps need from Lean, in order of use."""

    def resolve(
        self, toolchain: str, *, install: bool = False, mathlib_sha: str | None = None
    ) -> ResolvedToolchain:
        """Step 1: make ``toolchain`` available and report what it is — and, when the graph pins
        Mathlib, find the checkout and its built oleans (F11-R6)."""

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
        """Compile ``source`` as module ``module``; the olean lands at ``out_dir/<module path>``.

        ``root`` is the directory the module path is relative to (default: the source's own
        directory); Lean derives the module name for private declarations from it.
        """

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

    def witness_type(
        self,
        tc: ResolvedToolchain,
        req: WitnessRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        """Step 7: ``opn-witness-type`` — the expected witness type, and the witness against it."""

    def used_constants(
        self,
        tc: ResolvedToolchain,
        req: UsedConstantsRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        """Step 8: ``opn-used-constants`` — the proof's dependency footprint with module origins."""

    def hazards(
        self,
        tc: ResolvedToolchain,
        req: HazardsRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        """Step 6: ``opn-hazards`` — the named checkers' findings over the statement."""

    def artifact_type(
        self,
        tc: ResolvedToolchain,
        req: ArtifactRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        """F07: ``opn-artifact-type`` — what the artifact declares, and its holes if it has any."""

    def relation_type(
        self,
        tc: ResolvedToolchain,
        req: RelationRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        """F08: ``opn-relation-type`` — the implication a labeled variant claims (D-30)."""


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


#: What ``gate/scripts/install-mathlib.sh`` (and the image) leave beside the checkout so the pin
#: can be verified without git: the commit the checkout is at.
MATHLIB_STAMP = "MATHLIB_SHA"
INSTALL_MATHLIB_SCRIPT = "gate/scripts/install-mathlib.sh"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def mathlib_library_path(home: Path, sha: str, toolchain: str) -> tuple[Path, ...]:
    """The built library directories of the Mathlib checkout pinned at ``sha`` (F11-R6; D-7):
    Mathlib's own and each of its packages', in a fixed order, or ``ToolchainMissingError``
    naming the install script.

    Three things are checked, because each has been the bug somewhere: the stamp says the
    checkout is at the pinned commit (a checkout at another commit elaborates a different
    Mathlib); its ``lean-toolchain`` is the graph's pin (Mathlib oleans are specific to the Lean
    that built them); and the oleans exist (a clone without ``lake exe cache get`` is a
    two-hour build waiting to time out inside the sandbox).
    """
    if not _SHA_RE.match(sha):
        msg = f"mathlib_sha {sha!r} is not a 40-hex commit"
        raise ToolchainMissingError(msg)
    checkout = home / sha
    hint = f"run {INSTALL_MATHLIB_SCRIPT} {sha} (OPN_MATHLIB_HOME={home})"
    stamp = checkout / MATHLIB_STAMP
    if not stamp.is_file():
        msg = f"no Mathlib checkout for {sha} under {home}; {hint}"
        raise ToolchainMissingError(msg)
    stamped = stamp.read_text(encoding="utf-8").strip()
    if stamped != sha:
        msg = f"the Mathlib checkout under {checkout} is stamped {stamped!r}, not {sha}; {hint}"
        raise ToolchainMissingError(msg)
    pin_file = checkout / "lean-toolchain"
    pinned = pin_file.read_text(encoding="utf-8").strip() if pin_file.is_file() else ""
    if pinned != toolchain:
        msg = (
            f"Mathlib {sha[:12]} pins {pinned or 'no toolchain'}, but the graph pins {toolchain}; "
            "a graph pins the Mathlib built by its own toolchain (D-7)"
        )
        raise ToolchainMissingError(msg)
    lib = Path(".lake") / "build" / "lib" / "lean"
    own = checkout / lib
    if not own.is_dir():
        msg = f"Mathlib {sha[:12]} has no built oleans at {own}; {hint}"
        raise ToolchainMissingError(msg)
    # Every package that has oleans. One that has none (``Cli``, a build-time dependency of
    # Mathlib's own cache tool) is not on the search path because nothing imports it.
    packages = checkout / ".lake" / "packages"
    extra = (
        [pkg / lib for pkg in sorted(packages.iterdir()) if (pkg / lib).is_dir()]
        if packages.is_dir()
        else []
    )
    return (own, *extra)


def module_output_path(module: str, suffix: str) -> Path:
    """``Nodes.«a-b».Proof`` -> ``Nodes/a-b/Proof<suffix>``; bare ``Proof`` -> ``Proof<suffix>``."""
    parts: list[str] = []
    current = ""
    quoted = False
    for ch in module:
        if ch == "«":
            quoted = True
        elif ch == "»":
            quoted = False
        elif ch == "." and not quoted:
            parts.append(current)
            current = ""
            continue
        else:
            current += ch
    parts.append(current)
    return Path(*parts[:-1], parts[-1] + suffix)


def _join_search_path(search_path: Sequence[Path]) -> str:
    return ":".join(str(p.resolve()) for p in search_path)


class LocalToolchain:
    """The real seam: shells out to elan-managed binaries. Used by pregate.sh, CI and reproduce."""

    def __init__(
        self,
        elan: Path,
        lean_pkg_bin: Path = config.DEFAULT_LEAN_PKG_BIN,
        mathlib_home: Path = config.DEFAULT_MATHLIB_HOME,
    ) -> None:
        self.elan = elan
        self.lean_pkg_bin = lean_pkg_bin
        self.mathlib_home = mathlib_home

    @classmethod
    def from_settings(cls, settings: config.Settings) -> LocalToolchain:
        return cls(
            find_elan(path_env=None, elan_home=settings.elan_home),
            settings.lean_pkg_bin,
            settings.mathlib_home,
        )

    def metaprogram(self, name: str) -> Path:
        """Path of a built metaprogram; ``ToolchainMissingError`` if the package is unbuilt."""
        path = self.lean_pkg_bin / name
        if not path.is_file():
            msg = (
                f"metaprogram {name} not found at {path}; build the Lake package with "
                f"`elan run <toolchain> lake build` in gate/lean (or set OPN_LEAN_PKG_BIN)"
            )
            raise ToolchainMissingError(msg)
        return path

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

    def resolve(
        self, toolchain: str, *, install: bool = False, mathlib_sha: str | None = None
    ) -> ResolvedToolchain:
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
        library_path: tuple[Path, ...] = ()
        if mathlib_sha is not None:
            library_path = mathlib_library_path(self.mathlib_home, mathlib_sha, toolchain)
        return ResolvedToolchain(
            name=toolchain,
            version=m.group(1),
            githash=githash.stdout.strip(),
            libdir=Path(libdir.stdout.strip()),
            mathlib_sha=mathlib_sha,
            library_path=library_path,
        )

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
        out_dir = out_dir.resolve()
        source = source.resolve()
        cwd = (root or source.parent).resolve()
        olean = out_dir / module_output_path(module, ".olean")
        ilean = out_dir / module_output_path(module, ".ilean")
        olean.parent.mkdir(parents=True, exist_ok=True)
        proc = self._run(
            tc.name,
            ["lean", "--json", "-o", str(olean), "-i", str(ilean), str(source.relative_to(cwd))],
            cwd=cwd,
            lean_path=tc.search_path(out_dir),
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
            lean_path=tc.search_path(*search_path),
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
            lean_path=tc.search_path(*search_path),
            timeout_s=timeout_s,
        )
        output = proc.stdout + proc.stderr
        axioms = parse_axioms(proc.stdout, decl)
        if proc.returncode != 0 or axioms is None:
            return AxiomResult(ok=False, output=output)
        return AxiomResult(ok=True, axioms=axioms, output=output)

    def ensure_metaprograms(self, tc: ResolvedToolchain) -> None:
        """Build the Lake package once if its executables are missing (pregate on a fresh clone)."""
        if all((self.lean_pkg_bin / n).is_file() for n in METAPROGRAMS):
            return
        pkg = self.lean_pkg_bin.parents[2] if len(self.lean_pkg_bin.parents) > 2 else None
        if pkg is None or not (pkg / "lakefile.lean").is_file():
            return
        proc = self._exec([str(self.elan), "run", tc.name, "lake", "build"], cwd=pkg, timeout_s=900)
        if proc.returncode != 0:
            msg = f"lake build of {pkg} failed: {(proc.stdout + proc.stderr)[-2000:]}"
            raise ToolchainError(msg)

    def _metaprogram_run(
        self,
        tc: ResolvedToolchain,
        name: str,
        args: Sequence[str],
        search_path: Sequence[Path],
        timeout_s: float | None,
    ) -> MetaprogramResult:
        self.ensure_metaprograms(tc)
        binary = self.metaprogram(name)
        sysroot = tc.libdir.parent.parent
        proc = self._exec(
            [str(self.elan), "run", tc.name, str(binary), *args],
            extra_env={
                "LEAN_PATH": _join_search_path(tc.search_path(*search_path)),
                "LEAN_SYSROOT": str(sysroot),
            },
            timeout_s=timeout_s,
        )
        return parse_metaprogram_output(proc.returncode, proc.stdout, proc.stderr)

    def witness_type(
        self,
        tc: ResolvedToolchain,
        req: WitnessRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        return self._metaprogram_run(tc, "opn-witness-type", req.args(), search_path, timeout_s)

    def used_constants(
        self,
        tc: ResolvedToolchain,
        req: UsedConstantsRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        return self._metaprogram_run(tc, "opn-used-constants", req.args(), search_path, timeout_s)

    def hazards(
        self,
        tc: ResolvedToolchain,
        req: HazardsRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        return self._metaprogram_run(tc, "opn-hazards", req.args(), search_path, timeout_s)

    def artifact_type(
        self,
        tc: ResolvedToolchain,
        req: ArtifactRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        return self._metaprogram_run(tc, "opn-artifact-type", req.args(), search_path, timeout_s)

    def relation_type(
        self,
        tc: ResolvedToolchain,
        req: RelationRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        return self._metaprogram_run(tc, "opn-relation-type", req.args(), search_path, timeout_s)


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
