"""D-4 step 2: permitted paths, statement hash, proof-is-statement (F00-R2, R3, R19).

The submission is a set of changes against the graph. Before any build, every change must be one
of: create or modify the claimed node's ``Proof.lean``; add a file under its ``attempts/`` or
``annex/``; add or update ``waivers/native_decide.yaml`` when the proof uses ``native_decide``
(F02-R8). Anything else — another node, ``Statement.lean``, ``META.yaml``, ``defs/``, a rewrite
of an existing attempt — is rejected naming the path. The claimed node is an input, never
inferred from the diff: a diff that touches two nodes is a rejection, not a subgraph.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from opn_gate import schemas
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
WAIVER_PATH = "waivers/native_decide.yaml"  # F02-R8: permitted only when the proof needs it


def mentions_native_decide(proof_text: str) -> bool:
    """The textual half of F02-R8's gate on ``waivers/``: step 2 lets the waiver path through
    only when Proof.lean names ``native_decide`` at all; step 5 decides on the real axioms."""
    return "native_decide" in proof_text


def check_paths(
    changes: Iterable[Change], claim: Claim, *, waiver_allowed: bool = False
) -> list[Diagnostic]:
    """R2: every offending change, or ``[]`` when the diff is a permitted submission."""
    found: list[Diagnostic] = []
    for c in changes:
        for p in (c.path, c.old_path):
            if p is None:
                continue
            problem = _offence(c.status, p, claim, waiver_allowed=waiver_allowed)
            if problem:
                found.append(Diagnostic("path-forbidden", problem, {"path": p, "status": c.status}))
    return found


def _offence(  # noqa: PLR0911 — one return per rule
    status: Status, path: str, claim: Claim, *, waiver_allowed: bool
) -> str | None:
    if not path.startswith(claim.node_prefix):
        return f"{path} is outside the claimed node {claim.node_prefix}"
    rest = path[len(claim.node_prefix) :]
    if rest == "Proof.lean":
        return None if status in ("A", "M") else f"{path}: Proof.lean may not be {_verb(status)}"
    if rest == WAIVER_PATH:
        if not waiver_allowed:
            return f"{path}: {WAIVER_PATH} is permitted only when Proof.lean uses native_decide"
        return None if status in ("A", "M") else f"{path}: the waiver may not be {_verb(status)}"
    for d in APPEND_ONLY_DIRS:
        if rest.startswith(d):
            if "/" in rest[len(d) :] and not rest.startswith("attempts/precheck/"):
                return f"{path}: nested directories are not allowed under {d}"
            if status != "A":
                return f"{path}: {d} is append-only; a file there may not be {_verb(status)}"
            return None
    return (
        f"{path} is not Proof.lean, the native_decide waiver, or an append under attempts/ or "
        "annex/"
    )


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


# --- what a path is (F07-R3, R9, R10; F08-R2, R5, R8) --------------------------------------------
#
# Every path a submission may touch has exactly one role. ``locate`` is the whole grammar in one
# place, so the modes (``opn_gate.modes``) classify a diff by asking what each path is rather than
# by matching prefixes of their own.

Role = Literal[
    "proof",  # the node's Proof.lean (D-3): a proof, counterexample or vacuity certificate
    "waiver",  # waivers/native_decide.yaml (F02-R8)
    "partial",  # a .lean assembly under attempts/ (D-12 #5): the node stays open
    "postmortem",  # attempts/<ts>-<contributor>.yaml (D-13)
    "precheck-record",  # attempts/precheck/<name>.json (D-34)
    "annex",  # annex/<hash>.md (D-31)
    "explainer",  # explainer/<hash>.md (D-3, D-36)
    "approach-record",  # targets/<id>/approaches/<name>.yaml (D-14 mechanism 3)
    "node",  # META.yaml, Statement.lean, Context.lean: the node's definition, added once (D-3)
    "witness",  # Witness.lean: added with the node, or filled in on a hole's slot (F08-R5)
    "relation",  # Relation.lean: a variant's D-30 label and proof, added with the node
    "keep",  # <dir>/.gitkeep: D-3's required empty directories, added with the node
    "node-status",  # nodes/<id>/status/<name>.yaml: a curator record (F03-Q3, F08-R8)
    "target-status",  # targets/<id>/status/<name>.yaml: a curator declaration (D-33)
    "revision-request",  # nodes/<id>/revisions/<name>.yaml (D-8, F08-R6)
    "defect-claim",  # nodes/<id>/defects/ or targets/<id>/defs/defects/<name>.yaml (D-16, F08-R7)
]

#: Roles that claim nothing and merge on schema and path checks alone (F07-R9).
APPEND_ROLES: tuple[Role, ...] = (
    "postmortem",
    "precheck-record",
    "annex",
    "approach-record",
    "revision-request",
    "defect-claim",
)

#: Appends that may carry a Lean exhibit, which the gate elaborates in the sandbox (F08-R6, R7).
EXHIBIT_ROLES: tuple[Role, ...] = ("revision-request", "defect-claim")

#: The files a new node directory is made of (F08-R2): a proposal adds these and nothing else.
NODE_ROLES: tuple[Role, ...] = ("node", "witness", "relation", "keep")

#: The records only a listed curator may add (F08-R8; D-8, D-29, D-33).
CURATOR_ROLES: tuple[Role, ...] = ("node-status", "target-status")

#: Roles that may be modified as well as added: a proof is resubmittable, a waiver follows it, and
#: a hole's witness slot is filled in place (F08-R5) — everything else is append-only.
MODIFIABLE_ROLES: tuple[Role, ...] = ("proof", "waiver", "witness")

#: The schema each record validates against; an annex validates its YAML front matter.
SCHEMA_FOR_ROLE: dict[Role, str] = {
    "postmortem": "postmortem/v1",
    "precheck-record": "precheck-record/v1",
    "annex": "annex/v1",
    "approach-record": "approach-record/v1",
    "node-status": "node-status/v1",
    "target-status": "target-status/v1",
    "revision-request": "revision-request/v1",
    "defect-claim": "defect-claim/v1",
}

#: Roles whose file name is the SHA-256 of the file (D-31 annexes; D-3 explainers).
CONTENT_HASHED_ROLES: tuple[Role, ...] = ("annex", "explainer")

ANNEX_MAX_BYTES = 64 * 1024  # F07 §6
YAML_SUFFIXES: tuple[str, ...] = (".yaml", ".yml")
KEEP_FILE = ".gitkeep"
NODE_DEFINITION_FILES: tuple[str, ...] = ("META.yaml", "Statement.lean", "Context.lean")
WITNESS_FILE = "Witness.lean"
RELATION_FILE = "Relation.lean"
KEEP_DIRS: tuple[str, ...] = ("attempts", "annex", "explainer")

#: The node directories that hold flat YAML records, and the role of a record there.
RECORD_DIRS: dict[str, Role] = {
    "status/": "node-status",
    "revisions/": "revision-request",
    "defects/": "defect-claim",
}

_NODE_PATH_RE = re.compile(r"^targets/(?P<target>[^/]+)/nodes/(?P<node>[^/]+)/(?P<rest>.+)$")
_TARGET_PATH_RE = re.compile(r"^targets/(?P<target>[^/]+)/(?P<rest>.+)$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
#: D-8's revision of ``<slug>`` is ``<slug>-v<n>`` (F08-Q16: the document writes ``@v<n>``, and the
#: version rides inside the id's own alphabet so no id pattern changes). The suffix is reserved:
#: a proposal may not end in one, and only a curator adds a directory that does.
_NODE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VERSION_RE = re.compile(r"^(?P<base>[a-z0-9][a-z0-9-]*?)-v(?P<n>[1-9][0-9]*)$")


def is_versioned(node_id: str) -> bool:
    """Whether ``node_id`` is a D-8 revision (``<slug>-v<n>``), which only a curator may add."""
    return VERSION_RE.match(node_id) is not None


@dataclass(frozen=True)
class Located:
    """A path that is part of some submission, and what it is."""

    role: Role
    path: str
    target_id: str
    node_id: str | None  # None for the target-scoped approach record


def locate(path: str) -> Located | None:
    """The role of ``path``, or ``None`` when no mode may touch it (F07-R3's rejection)."""
    node_match = _NODE_PATH_RE.match(path)
    if node_match is not None:
        target, node = node_match.group("target"), node_match.group("node")
        if not (_ID_RE.match(target) and _NODE_ID_RE.match(node)):
            return None
        role = _node_role(node_match.group("rest"))
        return None if role is None else Located(role, path, target, node)
    target_match = _TARGET_PATH_RE.match(path)
    if target_match is not None and _ID_RE.match(target_match.group("target")):
        rest = target_match.group("rest")
        head, _, name = rest.partition("/")
        if head == "approaches" and _is_flat(name, YAML_SUFFIXES):
            return Located("approach-record", path, target_match.group("target"), None)
        if head == "status" and _is_flat(name, YAML_SUFFIXES):
            return Located("target-status", path, target_match.group("target"), None)
        if head == "defs" and name.startswith("defects/") and _is_flat(name[8:], YAML_SUFFIXES):
            return Located("defect-claim", path, target_match.group("target"), None)
    return None


def _node_role(rest: str) -> Role | None:  # noqa: PLR0911, PLR0912 — one branch per D-3 entry
    if rest == "Proof.lean":
        return "proof"
    if rest == WAIVER_PATH:
        return "waiver"
    if rest in NODE_DEFINITION_FILES:
        return "node"
    if rest == WITNESS_FILE:
        return "witness"
    if rest == RELATION_FILE:
        return "relation"
    if any(rest == f"{d}/{KEEP_FILE}" for d in KEEP_DIRS):
        return "keep"
    for directory, role in RECORD_DIRS.items():
        if rest.startswith(directory):
            return role if _is_flat(rest[len(directory) :], YAML_SUFFIXES) else None
    if rest.startswith("attempts/precheck/"):
        name = rest[len("attempts/precheck/") :]
        return "precheck-record" if _is_flat(name, (".json",)) else None
    if rest.startswith("attempts/"):
        name = rest[len("attempts/") :]
        if _is_flat(name, (".lean",)):
            return "partial"
        return "postmortem" if _is_flat(name, YAML_SUFFIXES) else None
    if rest.startswith("annex/"):
        return "annex" if _is_flat(rest[len("annex/") :], (".md",)) else None
    if rest.startswith("explainer/"):
        return "explainer" if _is_flat(rest[len("explainer/") :], (".md",)) else None
    return None


def _is_flat(name: str, suffixes: tuple[str, ...]) -> bool:
    """A file directly in the directory, with one of these suffixes — never a nested tree."""
    return "/" not in name and name != "" and PurePosixPath(name).suffix in suffixes


def check_content_hash_name(located: Located, data: bytes) -> Diagnostic | None:
    """R9: an annex is named for its own content, so a citation is mechanical (D-31) and a
    correction is a new file rather than an edit — which is also D-3's rule for explainers."""
    stem = PurePosixPath(located.path).stem
    digest = schemas.content_hash(data)
    if stem == digest:
        return None
    return Diagnostic(
        "content-hash-name",
        f"{located.path}: a {located.role} is named for the SHA-256 of its content",
        {"path": located.path, "expected": f"{digest}.md", "role": located.role},
    )


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
