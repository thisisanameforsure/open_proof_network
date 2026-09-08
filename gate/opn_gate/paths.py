"""D-4 step 2: permitted paths, statement hash, proof-is-statement (F00-R2, R3, R19).

The submission is a set of changes against the graph. Before any build, every change must be one
of: create or modify the claimed node's ``Proof.lean``; add a file under its ``attempts/`` or
``annex/``. Anything else — another node, ``Statement.lean``, ``META.yaml``, ``defs/``, a rewrite
of an existing attempt — is rejected naming the path. The claimed node is an input, never
inferred from the diff: a diff that touches two nodes is a rejection, not a subgraph.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from opn_gate.diagnostic import Diagnostic
from opn_gate.layout import Statement

Status = Literal["A", "M", "D", "R"]


@dataclass(frozen=True)
class Change:
    status: Status
    path: str  # relative to the graph root, POSIX separators
    old_path: str | None = None


@dataclass(frozen=True)
class Claim:
    target_id: str
    node_id: str

    @property
    def node_prefix(self) -> str:
        return f"targets/{self.target_id}/nodes/{self.node_id}/"


APPEND_ONLY_DIRS: tuple[str, ...] = ("attempts/", "annex/")


def check_paths(changes: Iterable[Change], claim: Claim) -> list[Diagnostic]:
    """R2: every offending change, or ``[]`` when the diff is a permitted submission."""
    found: list[Diagnostic] = []
    for c in changes:
        for p in (c.path, c.old_path):
            if p is None:
                continue
            problem = _offence(c.status, p, claim)
            if problem:
                found.append(Diagnostic("path-forbidden", problem, {"path": p, "status": c.status}))
    return found


def _offence(status: Status, path: str, claim: Claim) -> str | None:
    if not path.startswith(claim.node_prefix):
        return f"{path} is outside the claimed node {claim.node_prefix}"
    rest = path[len(claim.node_prefix) :]
    if rest == "Proof.lean":
        return None if status in ("A", "M") else f"{path}: Proof.lean may not be {_verb(status)}"
    for d in APPEND_ONLY_DIRS:
        if rest.startswith(d):
            if "/" in rest[len(d) :] and not rest.startswith("attempts/precheck/"):
                return f"{path}: nested directories are not allowed under {d}"
            if status != "A":
                return f"{path}: {d} is append-only; a file there may not be {_verb(status)}"
            return None
    return f"{path} is not Proof.lean or an append under attempts/ or annex/"


def _verb(status: Status) -> str:
    return {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}[status]


def check_statement_hash(statement: Statement, meta: dict[str, object]) -> Diagnostic | None:
    """R3: Statement.lean recomputed against META's pin, both hashes in the diagnostic."""
    expected = str(meta.get("statement-hash"))
    actual = statement.statement_hash
    if actual != expected:
        return Diagnostic(
            "statement-hash",
            "Statement.lean hash differs from META.yaml statement-hash",
            {"meta": expected, "computed": actual},
        )
    return None


def check_proof_is_statement(statement: Statement, proof_text: str) -> Diagnostic | None:
    """R19: Proof.lean is Statement.lean with only the sorry body replaced."""
    prefix = statement.prefix
    if not proof_text.startswith(prefix):
        line = _first_divergent_line(prefix, proof_text)
        return Diagnostic(
            "proof-not-statement",
            f"Proof.lean diverges from Statement.lean at line {line} (header or signature)",
            {"line": line, "expected": _line(prefix, line), "got": _line(proof_text, line)},
        )
    suffix = statement.suffix.rstrip()
    body_and_suffix = proof_text[len(prefix) :].rstrip()
    if suffix and not body_and_suffix.endswith(suffix):
        line = proof_text.count("\n") + 1
        return Diagnostic(
            "proof-not-statement",
            f"Proof.lean does not end with Statement.lean's trailing text (near line {line})",
            {"line": line, "expected": suffix.strip().splitlines()[-1]},
        )
    body = body_and_suffix[: len(body_and_suffix) - len(suffix)] if suffix else body_and_suffix
    if not body.strip():
        return Diagnostic("proof-empty", "Proof.lean has no body after `:=`")
    return None


def _first_divergent_line(expected: str, got: str) -> int:
    exp_lines = expected.splitlines()
    got_lines = got.splitlines()
    for i, e in enumerate(exp_lines):
        g = got_lines[i] if i < len(got_lines) else ""
        is_last = i == len(exp_lines) - 1
        if (g != e) if not is_last else (not g.startswith(e)):
            return i + 1
    return len(exp_lines)


def _line(text: str, n: int) -> str:
    lines = text.splitlines()
    return lines[n - 1] if 0 < n <= len(lines) else ""


# --- producing a change list -------------------------------------------------------------------


def changes_from_name_status(text: str) -> list[Change]:
    """Parse ``git diff --name-status`` output (tab-separated; renames carry two paths)."""
    out: list[Change] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        code = parts[0][0]
        if code == "R" and len(parts) >= 3:
            out.append(Change("R", parts[2], parts[1]))
        elif code in ("A", "M", "D"):
            out.append(Change(code, parts[1]))  # type: ignore[arg-type]
        else:  # copies, type changes, unmerged: treat as a modification of the named path
            out.append(Change("M", parts[-1]))
    return out


def changes_from_git(repo: Path, base: str, head: str = "HEAD") -> list[Change]:
    proc = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-status", "--no-renames", f"{base}...{head}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return changes_from_name_status(proc.stdout)


def changes_from_worktree(repo: Path, base: str = "HEAD") -> list[Change]:
    """Working tree (tracked and untracked) against ``base`` — what pregate.sh checks locally."""
    subprocess.run(["git", "-C", str(repo), "add", "-N", "--all"], check=True)
    proc = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-status", "--no-renames", base],
        capture_output=True,
        text=True,
        check=True,
    )
    return changes_from_name_status(proc.stdout)


def changes_from_trees(base: Path, head: Path) -> list[Change]:
    """Compare two directory trees (tests and reproduce.sh); paths relative to each root."""

    def files(root: Path) -> dict[str, bytes]:
        return {
            p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*")
            if p.is_file() and ".git" not in p.parts
        }

    before, after = files(base), files(head)
    out: list[Change] = []
    for path in sorted(set(before) | set(after)):
        if path not in before:
            out.append(Change("A", path))
        elif path not in after:
            out.append(Change("D", path))
        elif before[path] != after[path]:
            out.append(Change("M", path))
    return out
