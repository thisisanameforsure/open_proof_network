"""Precheck bundles (F06-R1): what a submitter may send, checked before any job exists.

A bundle is a mapping of path to UTF-8 content, the paths being relative to the graph root
exactly as a pull request's diff would name them. Validation reuses the gate's own step-2 path
check (``opn_gate.paths``), so the service can never accept something the authoritative gate
would reject on paths — one rule, one implementation (D-4: three invocations, one codebase).

Nothing here touches the network or the store; ``validate`` is a pure function of the bundle,
the claim and the node's files, which is what makes the rejections cheap to test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opn_gate import paths as gate_paths
from opn_gate.paths import Change, Claim

MAX_BUNDLE_BYTES = 512 * 1024  # F06 §6; the whole bundle, not per file
MAX_PATH_LENGTH = 255
PROOF_FILE = "Proof.lean"


@dataclass(frozen=True)
class Rejection:
    """The first violation, in the shape the route turns into a 400 body."""

    code: str
    message: str
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": self.message, **self.details}


@dataclass(frozen=True)
class Bundle:
    """A validated bundle: the files, their total size and their content hash."""

    files: dict[str, str]
    size: int
    digest: str

    @property
    def proof_text(self) -> str:
        """The proof the bundle carries, or empty when it only appends records."""
        for path, content in self.files.items():
            if path.endswith("/" + PROOF_FILE):
                return content
        return ""


def parse(raw: Any) -> tuple[dict[str, str], Rejection | None]:
    """Coerce the request's ``bundle`` field, rejecting anything that is not path -> text."""
    if not isinstance(raw, dict) or not raw:
        return {}, Rejection(
            "bundle-invalid", "bundle must be a non-empty object of path to file content", {}
        )
    files: dict[str, str] = {}
    for path, content in raw.items():
        if not isinstance(path, str) or not isinstance(content, str):
            return {}, Rejection(
                "bundle-invalid",
                "every bundle entry must be a string path with string content",
                {"path": str(path)[:MAX_PATH_LENGTH]},
            )
        files[path] = content
    return files, None


def _shape_problem(path: str) -> str | None:
    """Path shapes the gate's check never sees, because git would not produce them."""
    if len(path) > MAX_PATH_LENGTH:
        return f"path is longer than {MAX_PATH_LENGTH} characters"
    if path != path.strip() or not path:
        return "path is empty or padded with whitespace"
    if path.startswith("/") or path.endswith("/"):
        return "path must be relative to the graph root and name a file"
    if "\\" in path:
        return "path must use forward slashes"
    parts = path.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return "path must not contain empty, . or .. segments"
    return None


def size_of(files: dict[str, str]) -> int:
    return sum(len(path.encode()) + len(content.encode()) for path, content in files.items())


def digest_of(files: dict[str, str]) -> str:
    """A stable hash of the bundle's content, recorded on the job (R3)."""
    import hashlib  # noqa: PLC0415 — one caller

    h = hashlib.sha256()
    for path in sorted(files):
        h.update(path.encode())
        h.update(b"\0")
        h.update(files[path].encode())
        h.update(b"\0")
    return h.hexdigest()


def validate(
    raw: Any, claim: Claim, *, existing: frozenset[str] = frozenset()
) -> tuple[Bundle | None, Rejection | None]:
    """R1: the bundle, or the first violation.

    ``existing`` names the paths the node already has at ``main``, which decides whether a file
    is an addition or a modification — the distinction the gate's append-only rule turns on.
    """
    files, rejection = parse(raw)
    if rejection is not None:
        return None, rejection

    for path in sorted(files):
        problem = _shape_problem(path)
        if problem is not None:
            return None, Rejection("path-invalid", problem, {"path": path[:MAX_PATH_LENGTH]})

    size = size_of(files)
    if size > MAX_BUNDLE_BYTES:
        return None, Rejection(
            "bundle-too-large",
            f"the bundle is {size} bytes; the limit is {MAX_BUNDLE_BYTES}",
            {"size": size, "limit": MAX_BUNDLE_BYTES},
        )

    # The gate decides what is permitted; the service only reports what it says (R1).
    changes = [Change("M" if path in existing else "A", path) for path in sorted(files)]
    proof_text = next(
        (c for p, c in sorted(files.items()) if p.endswith("/" + PROOF_FILE)),
        "",
    )
    waiver_allowed = gate_paths.mentions_native_decide(proof_text)
    problems = gate_paths.check_paths(changes, claim, waiver_allowed=waiver_allowed)
    if problems:
        first = problems[0]
        return None, Rejection("path-forbidden", first.message, dict(first.details))

    return Bundle(files=files, size=size, digest=digest_of(files)), None
