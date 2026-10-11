"""Stage B of the export: the port to the registry's toolchain (F25-R12; D-10 v3.37).

An exported wrapper is byte-faithful to the graph at the graph's pin (Lean 4.33.1). Palomar
requires a newer toolchain, so the wrapper is *ported*: its pins rewritten, Mathlib resolved at
the registry's revision, built, and judged by ``lake comparator`` with the toolchain's bundled
kernels, as the registry's own template script does. The Challenge is frozen through the port —
its bytes may not move — and only proof bodies may be repaired by the person or agent doing the
port. The definition of done is the registry's preflight (``palomar-preflight.yml``), whose
mechanical report this module reads; "a local build or standalone Comparator run does not
count" is the registry's own rule.

Everything that runs a process goes through :class:`Runner`, with a fake for tests; the
classification of a failed build and the parsing of a preflight report are pure.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from opn_gate import palomar
from opn_gate.diagnostic import Diagnostic

PORT_REPORT = "port-report.json"
EXPORT_RECORD = "opn-export.json"
#: How a failed port is read, in the order the regexes are tried; the first match names it.
FAILURE_KINDS: tuple[tuple[str, str], ...] = (
    ("renamed-or-removed", r"unknown (?:identifier|constant|namespace) '?[^'\n]+'?"),
    (
        "type-mismatch",
        r"type mismatch|has type|but is expected to have type|application type mismatch",
    ),
    ("decide-failed", r"failed to reduce to true/false|`decide` failed|maximum recursion depth"),
    (
        "tactic-failed",
        r"(?:tactic|Tactic) `?[A-Za-z_]+`? failed|unsolved goals|linarith failed|omega could not",
    ),
    ("deprecated", r"has been deprecated|is deprecated"),
    ("timeout", r"deterministic timeout|\(deterministic\) timeout|maxHeartbeats"),
)
_DIAG_RE = re.compile(
    r"^(?:error|warning): (?P<file>[^:\n]+\.lean):(?P<line>\d+):(?P<col>\d+): (?P<text>.*)$", re.M
)
_BUILD_FAIL_RE = re.compile(r"^✖ \[\d+/\d+\] Building (?P<module>\S+)", re.M)


class PortError(Exception):
    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(f"{diagnostic.code}: {diagnostic.message}")
        self.diagnostic = diagnostic


# --- the runner seam -------------------------------------------------------------------------


@dataclass(frozen=True)
class Ran:
    argv: tuple[str, ...]
    exit_code: int
    output: str


class Runner(Protocol):
    def run(self, argv: list[str], *, cwd: Path, timeout_s: float) -> Ran: ...


class SubprocessRunner:
    def run(self, argv: list[str], *, cwd: Path, timeout_s: float) -> Ran:
        try:
            proc = subprocess.run(
                argv, cwd=cwd, capture_output=True, text=True, timeout=timeout_s, check=False
            )
        except subprocess.TimeoutExpired as exc:
            return Ran(tuple(argv), 124, f"timed out after {timeout_s:g}s: {exc}")
        return Ran(tuple(argv), proc.returncode, (proc.stdout or "") + (proc.stderr or ""))


class ElanRunner:
    """``elan run <toolchain> <argv>``: the registry's toolchain for every step, whatever the
    directory's own ``lean-toolchain`` says (the first probe run learned that lesson)."""

    def __init__(self, elan: Path, toolchain_name: str) -> None:
        self.elan = elan
        self.toolchain_name = toolchain_name

    def run(self, argv: list[str], *, cwd: Path, timeout_s: float) -> Ran:
        return SubprocessRunner().run(
            [str(self.elan), "run", self.toolchain_name, *argv], cwd=cwd, timeout_s=timeout_s
        )


@dataclass
class FakeRunner:
    """Scripted answers by the argv's first two words (``lake build``), in order of asking."""

    answers: dict[str, list[Ran]] = field(default_factory=dict)
    calls: list[tuple[tuple[str, ...], Path]] = field(default_factory=list)

    def run(self, argv: list[str], *, cwd: Path, timeout_s: float) -> Ran:
        self.calls.append((tuple(argv), cwd))
        key = " ".join(argv[:2])
        queue = self.answers.get(key) or self.answers.get(argv[0]) or []
        if queue:
            return queue.pop(0)
        return Ran(tuple(argv), 0, "")


# --- the pins ----------------------------------------------------------------------------------


def challenge_frozen(project: Path) -> None:
    """F25-R12: the Challenge's bytes are what the export wrote, or the port refuses."""
    record_path = project / EXPORT_RECORD
    if not record_path.is_file():
        raise PortError(
            Diagnostic(
                "port-record-missing", f"{project} carries no {EXPORT_RECORD}; port an export"
            )
        )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    want = record.get("hashes_out", {}).get("Challenge.lean")
    have = hashlib.sha256((project / "Challenge.lean").read_bytes()).hexdigest()
    if want != have:
        raise PortError(
            Diagnostic(
                "port-challenge-changed",
                "Challenge.lean is not the file the export wrote; only proof bodies may change "
                "in a port",
                {"expected": want, "found": have},
            )
        )


def rewrite_pins(project: Path, *, toolchain: str, mathlib_rev: str) -> dict[str, str]:
    """``lean-toolchain`` and the lakefile's Mathlib ``rev`` at the registry's values; the old
    values returned for the report."""
    minimum = palomar.toolchain_minimum()
    if _version_tuple(toolchain) < _version_tuple("leanprover/lean4:" + minimum):
        raise PortError(
            Diagnostic(
                "port-toolchain-below-minimum",
                f"{toolchain} is below the registry's minimum {minimum}",
                {"minimum": minimum},
            )
        )
    tc_path = project / "lean-toolchain"
    old_tc = tc_path.read_text(encoding="utf-8").strip()
    tc_path.write_text(toolchain + "\n", encoding="utf-8")
    lakefile = project / "lakefile.toml"
    text = lakefile.read_text(encoding="utf-8")
    m = re.search(r'^rev = "(?P<rev>[^"]+)"$', text, re.M)
    old_rev = m.group("rev") if m else ""
    if m:
        text = text[: m.start()] + f'rev = "{mathlib_rev}"' + text[m.end() :]
    else:
        text += (
            '\n[[require]]\nname = "mathlib"\nscope = "leanprover-community"\n'
            f'rev = "{mathlib_rev}"\n'
        )
    lakefile.write_text(text, encoding="utf-8")
    return {"toolchain_was": old_tc, "mathlib_was": old_rev}


def _version_tuple(toolchain: str) -> tuple[int, ...]:
    m = re.search(r"v(\d+)\.(\d+)\.(\d+)(?:-rc(\d+))?", toolchain)
    if not m:
        return (0,)
    major, minor, patch, rc = m.groups()
    return (int(major), int(minor), int(patch), int(rc) if rc else 10**6)


# --- failures --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Failure:
    module: str | None
    kind: str
    file: str
    line: int
    text: str


def classify(output: str) -> list[Failure]:
    """Each error line of a ``lake build`` output as a failure with a kind (F25-R12); warnings
    are kept only when they are deprecations, because those are what a later toolchain refuses
    next."""
    out: list[Failure] = []
    modules: list[str] = _BUILD_FAIL_RE.findall(output)
    for m in _DIAG_RE.finditer(output):
        text = m.group("text")
        is_error = m.group(0).startswith("error:")
        kind = next((k for k, pat in FAILURE_KINDS if re.search(pat, text)), "other")
        if not is_error and kind != "deprecated":
            continue
        out.append(
            Failure(
                # the file names the module; the failed-build line only when the file does not
                module=_module_of(m.group("file")) or (modules[0] if len(modules) == 1 else None),
                kind=kind,
                file=m.group("file"),
                line=int(m.group("line")),
                text=text.strip(),
            )
        )
    return out


def _module_of(file: str) -> str | None:
    rel = file.replace("\\", "/")
    rel = rel.split("/.lake/", 1)[0]
    if rel.endswith(".lean"):
        return rel.removesuffix(".lean").strip("./").replace("/", ".")
    return None


# --- the registry's preflight report ---------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    owner: str
    explanation: str
    next_action: str
    retryable: bool
    location: str | None


@dataclass(frozen=True)
class Preflight:
    status: str
    phase: str
    passed: bool
    findings: tuple[Finding, ...]


def preflight_report(doc: dict[str, Any]) -> Preflight:
    """Palomar's mechanical report (PalomarSubmission's ``diagnostics-v1`` rows): the status,
    the phase, and each finding with its owner, explanation and next action. Read loosely —
    the shape is the registry's and may move — and nothing but ``status == "pass"`` is read as a
    pass."""
    status = str(doc.get("status") or doc.get("result") or "unknown")
    phase = str(doc.get("phase") or "")
    rows: list[Finding] = []
    raw = doc.get("diagnostics") or doc.get("findings") or []
    if isinstance(raw, dict):
        raw = raw.get("items") or []
    for row in raw if isinstance(raw, list) else []:
        if not isinstance(row, dict):
            continue
        loc = row.get("location")
        rows.append(
            Finding(
                owner=str(row.get("owner") or ""),
                explanation=str(row.get("explanation") or row.get("message") or ""),
                next_action=str(
                    row.get("next_action") or row.get("nextAction") or row.get("remedy") or ""
                ),
                retryable=bool(
                    row.get("retryable") or row.get("retryability") in ("retryable", True)
                ),
                location=json.dumps(loc, sort_keys=True)
                if isinstance(loc, dict)
                else (str(loc) if loc else None),
            )
        )
    return Preflight(status=status, phase=phase, passed=status == "pass", findings=tuple(rows))


# --- the port ----------------------------------------------------------------------------------


@dataclass
class PortReport:
    toolchain: str
    mathlib_rev: str
    pins_were: dict[str, str]
    steps: list[dict[str, Any]] = field(default_factory=list)
    failures: list[Failure] = field(default_factory=list)
    ok: bool = False
    #: Q34: each proof body a repairs directory replaced, with the hash the export wrote and the
    #: hash built — so a reader of the wrapper can tell the export's text from the port's.
    repairs: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "opn-port-report/v1",
            "ok": self.ok,
            "toolchain": self.toolchain,
            "mathlib_rev": self.mathlib_rev,
            "pins_were": self.pins_were,
            "repairs": self.repairs,
            "steps": self.steps,
            "failures": [asdict(f) for f in self.failures],
        }


#: A repair's optional sidecar: the sha256 of the exported file it was written against.
REPAIR_SIDECAR = ".before.sha256"


def apply_repairs(project: Path, repairs: Path) -> list[dict[str, str]]:
    """Q34: copy each file under ``repairs`` over the same path in ``project``. Every refusal is
    raised before any file is written: ``Challenge.lean`` is frozen (``port-repair-forbidden``), a
    path the export did not write cannot be added (``port-repair-unknown``), and a repair whose
    sidecar names another export's hash is stale (``port-repair-stale``) — a whole-file repair
    made against an older export would otherwise put that export's text back silently."""
    record = json.loads((project / EXPORT_RECORD).read_text(encoding="utf-8"))
    wrote: dict[str, str] = record.get("hashes_out", {})
    planned: list[tuple[str, Path]] = []
    for path in sorted(p for p in repairs.rglob("*") if p.is_file()):
        rel = path.relative_to(repairs).as_posix()
        if rel.endswith(REPAIR_SIDECAR):
            continue
        if rel == "Challenge.lean":
            raise PortError(
                Diagnostic("port-repair-forbidden", "Challenge.lean is frozen through a port")
            )
        if rel not in wrote:
            raise PortError(
                Diagnostic(
                    "port-repair-unknown",
                    f"{rel}: the export did not write this file; a port cannot add one",
                )
            )
        have = hashlib.sha256((project / rel).read_bytes()).hexdigest()
        sidecar = Path(str(path) + REPAIR_SIDECAR)
        if sidecar.is_file():
            want = sidecar.read_text(encoding="utf-8").strip()
            if want != have:
                raise PortError(
                    Diagnostic(
                        "port-repair-stale",
                        f"{rel}: the repair was written against another export's file",
                        {"sidecar": want, "found": have},
                    )
                )
        planned.append((rel, path))
    applied: list[dict[str, str]] = []
    for rel, path in planned:
        before = hashlib.sha256((project / rel).read_bytes()).hexdigest()
        data = path.read_bytes()
        (project / rel).write_bytes(data)
        applied.append(
            {"path": rel, "sha256_before": before, "sha256_after": hashlib.sha256(data).hexdigest()}
        )
    return applied


def comparator_config_with_kernels(project: Path, prefix: Path) -> Path:
    """The template script's rule: the submitted ``comparator.json`` with the toolchain's
    bundled kernels added as ``external_kernels`` (an object, kernel name to argv; probe run 2),
    written beside it and never committed."""
    doc = json.loads((project / "comparator.json").read_text(encoding="utf-8"))
    if "external_kernels" in doc:
        raise PortError(
            Diagnostic(
                "port-comparator-kernels",
                "comparator.json names external_kernels; the registry refuses that key",
            )
        )
    doc.pop("enable_nanoda", None)
    doc["external_kernels"] = {
        "nanoda": [str(prefix / "bin" / "nanoda_bin")],
        "con-ron": [str(prefix / "bin" / "con-ron")],
    }
    out = project / ".opn-port" / "comparator.generated.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return out


def port(  # noqa: PLR0913 — one argument per thing the port is told
    project: Path,
    *,
    toolchain: str,
    mathlib_rev: str,
    runner: Runner,
    prefix: Path,
    timeout_s: float = 3600,
    skip_update: bool = False,
    repairs: Path | None = None,
) -> PortReport:
    """Rewrite the pins, resolve Mathlib, fetch its cache, build, judge. Each step's exit and
    tail are kept; the first failing step ends the port and its errors are classified. With
    ``repairs``, proof bodies are replaced first (``apply_repairs``, Q34); the Challenge check
    runs after, so a repair can never move it."""
    challenge_frozen(project)
    applied = apply_repairs(project, repairs) if repairs is not None else []
    challenge_frozen(project)
    were = rewrite_pins(project, toolchain=toolchain, mathlib_rev=mathlib_rev)
    report = PortReport(toolchain, mathlib_rev, were, repairs=applied)
    steps: list[tuple[str, list[str]]] = []
    if not skip_update:
        steps.append(("update", ["lake", "update", "mathlib"]))
    steps.append(("cache", ["lake", "exe", "cache", "get"]))
    steps.append(("build", ["lake", "build"]))
    config = comparator_config_with_kernels(project, prefix)
    steps.append(("comparator", ["lake", "comparator", "--config", str(config)]))
    for name, argv in steps:
        ran = runner.run(argv, cwd=project, timeout_s=timeout_s)
        # the build's whole output is what a repair is read from; the other steps' tails suffice
        keep = 200_000 if name == "build" else 4000
        report.steps.append(
            {"step": name, "argv": list(argv), "exit": ran.exit_code, "tail": ran.output[-keep:]}
        )
        if ran.exit_code != 0:
            if name == "build":
                report.failures = classify(ran.output)
            break
    else:
        report.ok = True
    (project / PORT_REPORT).write_text(
        json.dumps(report.as_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return report
