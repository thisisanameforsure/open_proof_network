"""The conformance verifier (F25-R13): a registered Palomar entry re-checked with the network's
own tools.

Ground truth the registry accepted: the entry's repository at its recorded commit is cloned, its
Challenge and Solution hashes are held to the registry's record, it is built at its own toolchain
and judged by ``lake comparator`` with the toolchain's kernels, and then the network's own
checkers — ``opn-axioms`` and ``opn-statement-meaning``, built at that same toolchain — judge the
same theorems. A disagreement is a defect in the network's tools, not in the entry, and the job
fails on it. Processes run through :class:`palomar_port.Runner`; the network's checkers through a
seam (``Checkers``) so the plan of a verification is testable without a toolchain.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import palomar
from opn_gate.palomar_port import Ran, Runner

REPO_URL = "https://github.com/{repository}"
LEAN_PKG_NAME = "opn-lean"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Conformance:
    entry_id: str
    repository: str
    commit: str
    toolchain: str
    ok: bool = True
    checks: list[Check] = field(default_factory=list)
    comparator_exit: int | None = None
    our_axioms: dict[str, list[str]] = field(default_factory=dict)

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append(Check(name, ok, detail[-3000:]))
        self.ok = self.ok and ok

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "opn-conformance/v1",
            "entry_id": self.entry_id,
            "repository": self.repository,
            "commit": self.commit,
            "toolchain": self.toolchain,
            "ok": self.ok,
            "comparator_exit": self.comparator_exit,
            "our_axioms": self.our_axioms,
            "checks": [asdict(c) for c in self.checks],
        }


#: What the network's checkers answer for one theorem: its axioms, and whether the Solution's
#: declaration has the Challenge's type (``opn-statement-meaning``'s ``matches``).
Checkers = Callable[[Path, str, str, str, str], tuple[list[str] | None, bool | None, str]]


def project_dir(repo: Path, pin: dict[str, Any]) -> Path:
    return repo / pin["project_path"] if pin.get("project_path") else repo


def module_olean(project: Path, module: str) -> Path:
    """Lake's build layout: ``.lake/build/lib/lean/<Module/Path>.olean``."""
    return (
        project
        / ".lake"
        / "build"
        / "lib"
        / "lean"
        / Path(*module.split(".")).with_suffix(".olean")
    )


def search_path(project: Path) -> list[Path]:
    """The project's built oleans and every dependency's, as Lake lays them out."""
    out = [project / ".lake" / "build" / "lib" / "lean"]
    packages = project / ".lake" / "packages"
    if packages.is_dir():
        out.extend(
            sorted(p / ".lake" / "build" / "lib" / "lean" for p in packages.iterdir() if p.is_dir())
        )
    return out


def hashes_match(project: Path, pin: dict[str, Any], repo: Path) -> list[tuple[str, bool, str]]:
    out: list[tuple[str, bool, str]] = []
    for key, path_key in (
        ("challenge_sha256", "challenge_path"),
        ("solution_sha256", "solution_path"),
    ):
        path = repo / pin[path_key]
        have = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        out.append(
            (
                path_key,
                have == pin[key],
                f"{pin[path_key]}: {have[:12]} vs the record's {pin[key][:12]}",
            )
        )
    return out


def toolchain_of(project: Path, repo: Path, pin: dict[str, Any]) -> str:
    for candidate in (project / "lean-toolchain", repo / "lean-toolchain"):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8").strip()
    return str(pin["lean_toolchain"])


def clone(
    pin: dict[str, Any], work: Path, runner: Runner, *, timeout_s: float
) -> tuple[Path, list[Ran]]:
    """The repository at exactly the recorded commit: init, fetch that one commit, check it out
    (a branch may move; the commit is what the registry judged)."""
    repo = work / "repo"
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)
    url = REPO_URL.format(repository=pin["repository"])
    ran = [
        runner.run(["git", "init", "-q"], cwd=repo, timeout_s=timeout_s),
        runner.run(["git", "remote", "add", "origin", url], cwd=repo, timeout_s=timeout_s),
        runner.run(
            ["git", "fetch", "-q", "--depth", "1", "origin", pin["commit"]],
            cwd=repo,
            timeout_s=timeout_s,
        ),
        runner.run(["git", "checkout", "-q", "FETCH_HEAD"], cwd=repo, timeout_s=timeout_s),
    ]
    return repo, ran


def verify(  # noqa: PLR0913 — one argument per seam
    pin: dict[str, Any],
    *,
    work: Path,
    runner: Runner,
    prefix_for: Callable[[str], Path],
    checkers: Checkers | None,
    timeout_s: float = 3600,
) -> Conformance:
    """One registered entry through every check; ``prefix_for(toolchain)`` is the toolchain's
    install prefix (its ``bin/`` holds the kernels), ``checkers`` the network's own, ``None`` when
    they cannot be built (recorded as not attempted, which counts against the verdict)."""
    result = Conformance(pin["id"], pin["repository"], pin["commit"], str(pin["lean_toolchain"]))
    # absolute: lake runs with cwd=project and reads the config path as given (the first corpus
    # run passed a path relative to the tool's cwd and Comparator could not read it, 2026-10-11)
    work = work.resolve()
    repo, ran = clone(pin, work, runner, timeout_s=timeout_s)
    if any(r.exit_code != 0 for r in ran):
        result.record("clone", False, "\n".join(r.output[-500:] for r in ran if r.exit_code != 0))
        return result
    result.record("clone", True, pin["commit"])
    project = project_dir(repo, pin)
    for name, ok, detail in hashes_match(project, pin, repo):
        result.record(f"hash {name}", ok, detail)
    if not result.ok:
        return result
    tc = toolchain_of(project, repo, pin)
    result.toolchain = tc
    result.record(
        "toolchain", tc == str(pin["lean_toolchain"]), f"{tc} (record: {pin['lean_toolchain']})"
    )
    steps = [("cache", ["lake", "exe", "cache", "get"]), ("build", ["lake", "build"])]
    for name, argv in steps:
        r = runner.run(argv, cwd=project, timeout_s=timeout_s)
        result.record(name, r.exit_code == 0, r.output)
        if r.exit_code != 0:
            return result
    config_rel = Path(pin["comparator_config_path"])
    if pin.get("project_path"):
        config_rel = config_rel.relative_to(pin["project_path"])
    config = _kernels_config(project, config_rel, prefix_for(tc))
    r = runner.run(
        ["lake", "comparator", "--config", str(config)], cwd=project, timeout_s=timeout_s
    )
    result.comparator_exit = r.exit_code
    result.record("comparator", r.exit_code == 0, r.output)
    comparator = palomar.read_comparator((project / config_rel).read_text(encoding="utf-8"))
    if checkers is None:
        result.record(
            "network-checkers",
            False,
            "not attempted: the network's checkers could not be built at this toolchain",
        )
        return result
    challenge_olean = module_olean(project, comparator.challenge_module)
    for decl in comparator.theorem_names:
        axioms, matches, detail = checkers(
            project, tc, comparator.solution_module, decl, str(challenge_olean)
        )
        if axioms is None:
            result.record(f"opn-axioms {decl}", False, detail)
        else:
            result.our_axioms[decl] = sorted(axioms)
            extra = sorted(set(axioms) - set(comparator.permitted_axioms))
            result.record(
                f"opn-axioms {decl}",
                not extra,
                f"{sorted(axioms)}; outside the permitted list: {extra}",
            )
        if matches is None:
            result.record(f"opn-statement-meaning {decl}", False, detail)
        else:
            result.record(f"opn-statement-meaning {decl}", matches, detail)
    return result


def _kernels_config(project: Path, config_rel: Path, prefix: Path) -> Path:
    doc = json.loads((project / config_rel).read_text(encoding="utf-8"))
    doc.pop("enable_nanoda", None)
    doc.pop("external_kernels", None)
    doc["external_kernels"] = {
        "nanoda": [str(prefix / "bin" / "nanoda_bin")],
        "con-ron": [str(prefix / "bin" / "con-ron")],
    }
    out = project / ".opn-verify" / "comparator.generated.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return out


# --- the network's checkers at a foreign toolchain -------------------------------------------


def build_checkers(
    lean_pkg_src: Path, work: Path, toolchain: str, runner: Runner, *, timeout_s: float = 1800
) -> Path | None:
    """Copy the gate's Lake package (without its build) beside the work and build it at
    ``toolchain``; the built ``bin/`` or ``None`` with the failure in the log file beside it."""
    dest = work / LEAN_PKG_NAME
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(lean_pkg_src, dest, ignore=shutil.ignore_patterns(".lake"), symlinks=False)
    (dest / "lean-toolchain").write_text(toolchain + "\n", encoding="utf-8")
    r = runner.run(["lake", "build"], cwd=dest, timeout_s=timeout_s)
    (work / f"{LEAN_PKG_NAME}-build.txt").write_text(r.output, encoding="utf-8")
    if r.exit_code != 0:
        return None
    return dest / ".lake" / "build" / "bin"


def pins_drift(host_fetch: Callable[[str], bytes], pins: dict[str, Any]) -> list[dict[str, str]]:
    """F25-Q12: the registry's pins re-probed — the toolchain minimum and the formalization
    schema by sha256 — against ``gate/palomar/PINS.json``; one row per difference."""
    out: list[dict[str, str]] = []
    for name, entry in (
        ("toolchains", pins["toolchains"]),
        ("formalization_schema", pins["formalization_schema"]),
    ):
        raw = host_fetch(entry["source"])
        have = hashlib.sha256(raw).hexdigest()
        if have != entry["sha256"]:
            detail = ""
            if name == "toolchains":
                m = re.search(r'"minimum"\s*:\s*"([^"]+)"', raw.decode("utf-8", errors="replace"))
                detail = f"minimum now {m.group(1)}" if m else ""
            out.append({"pin": name, "pinned": entry["sha256"], "live": have, "detail": detail})
    return out
