"""The witnesses a partial carries for its holes (F07-R23; D-29 v3.24).

A hole used to be born with an empty witness slot, and a second pull request had to merge and
render before anything could be prechecked against it: two passes through the queue for each
level of a skeleton chain, for a witness that is usually the parent's with a line changed. So a
partial may carry them. Beside its one assembly ``attempts/<name>.lean`` it adds files

    attempts/<name>.<n>.witness        n = 1, 2, …

each the text of the ``Witness.lean`` one hole's node is to be born with, naming that hole on a
line ``-- hole: <name>`` — the ``have`` name the precheck lists, as a skeleton names its annex
on ``-- annex:``. The node's id does not exist before the merge and a position moves when the
skeleton is edited, so the name is the one stable handle; ``<n>`` only keeps the files apart.

The suffix is deliberately not ``.lean``: every reader that takes ``attempts/*.lean`` for an
assembly (the attempt count, the site's list, the service's fingerprints) goes on reading
exactly what it read.

This module is the grammar and nothing else, pure over text, so step 2 and the service refuse
the same things in the same words (D-4: one codebase). The check itself is step 7's
(``opn_gate.steps.witness``) and the writing is the post-merge job's (``opn_gate.postmerge``).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate import layout, schemas
from opn_gate.diagnostic import Diagnostic

#: The suffix of a carried witness; the path role is ``hole-witness`` (``opn_gate.paths``).
SUFFIX = ".witness"
ATTEMPTS = "attempts/"
ASSEMBLY_SUFFIX = ".lean"
#: ``ctx.data`` key: what step 7 checked, which the post-merge job writes and nothing else.
DATA_KEY = "hole_witnesses"
#: The key under step 2's partial record: the carried files as read, before any check of Lean.
PARTIAL_WITNESSES_KEY = "witnesses"

_HOLE_LINE_RE = re.compile(r"^\s*--\s*hole:\s*(?P<name>\S+)\s*$", re.M)
_NUMBER_RE = re.compile(r"^[1-9][0-9]*$")


@dataclass(frozen=True)
class Carried:
    """One carried witness: the hole it names, where it is under the node, and its text."""

    hole: str
    path: str  # relative to the node directory: ``attempts/<name>.<n>.witness``
    text: str

    @property
    def sha256(self) -> str:
        return schemas.content_hash(self.text.encode("utf-8"))

    def as_dict(self) -> dict[str, Any]:
        return {"hole": self.hole, "path": self.path, "sha256": self.sha256}


def read_file(path: Path) -> str:
    """A carried witness as its bytes say, decoded and nothing more. Text mode folds ``\\r\\n``
    into ``\\n``, and the hash of the folded text is not the hash of the file the service bound
    the submission to, nor the text the hole's node is to be born with (F07-T53)."""
    return path.read_bytes().decode("utf-8")


def is_carried(name: str) -> bool:
    """Whether a file name under ``attempts/`` is a carried witness, by its suffix alone."""
    return name.endswith(SUFFIX) and name != SUFFIX


def file_name(assembly_name: str, n: int) -> str:
    """``<assembly name without .lean>.<n>.witness``: the name the ``n``-th carried witness of
    the assembly ``assembly_name`` takes."""
    return f"{_stem(assembly_name)}.{n}{SUFFIX}"


def _stem(assembly_name: str) -> str:
    if assembly_name.endswith(ASSEMBLY_SUFFIX):
        return assembly_name[: -len(ASSEMBLY_SUFFIX)]
    return assembly_name


def number_of(assembly_name: str, name: str) -> int | None:
    """The ``<n>`` of a witness file attached to this assembly, or ``None`` when the name is
    not ``<assembly name without .lean>.<n>.witness``."""
    prefix = _stem(assembly_name) + "."
    if not (name.startswith(prefix) and name.endswith(SUFFIX)):
        return None
    middle = name[len(prefix) : -len(SUFFIX)]
    return int(middle) if _NUMBER_RE.match(middle) else None


def hole_named(text: str) -> str | None:
    """The hole a carried witness names: the value of its first ``-- hole: <name>`` line."""
    m = _HOLE_LINE_RE.search(text)
    return m.group("name") if m else None


def attached_to(assembly_rel: str, names: Mapping[str, str]) -> dict[str, str]:
    """Of ``names`` (path under the node -> text), the carried witnesses attached to the
    assembly at ``assembly_rel`` — what a bare tree, which has no diff, takes as the
    submission's own."""
    assembly_name = assembly_rel[len(ATTEMPTS) :]
    return {
        path: text
        for path, text in names.items()
        if path.startswith(ATTEMPTS) and number_of(assembly_name, path[len(ATTEMPTS) :]) is not None
    }


def read(assembly_rel: str, files: Mapping[str, str]) -> tuple[list[Carried], Diagnostic | None]:
    """The carried witnesses of the assembly at ``assembly_rel``, in the order of their numbers,
    or the first reason one of ``files`` (path under the node -> text) is not one (R23).

    Everything here is decided from names and text; whether a witness names a hole the assembly
    has, and whether it is a witness of it, is step 7's, which has the extractor's report.
    """
    assembly_name = assembly_rel[len(ATTEMPTS) :]
    numbered: list[tuple[int, Carried]] = []
    seen: dict[str, str] = {}
    for path in sorted(files):
        text = files[path]
        n = number_of(assembly_name, path[len(ATTEMPTS) :]) if path.startswith(ATTEMPTS) else None
        if n is None:
            return [], Diagnostic(
                "hole-witness-unattached",
                f"{path} is not attached to the assembly {assembly_rel}: a carried witness is "
                f"named {ATTEMPTS}{file_name(assembly_name, 1)}, …{file_name(assembly_name, 2)}, "
                "and so on (F07-R23)",
                {"path": path, "assembly": assembly_rel},
            )
        hole = hole_named(text)
        if hole is None:
            return [], Diagnostic(
                "hole-witness-unnamed",
                f"{path} names no hole: a carried witness says which hole it is for on a line "
                "`-- hole: <name>`, the name the precheck lists for that hole (F07-R23)",
                {"path": path},
            )
        if hole in seen:
            return [], Diagnostic(
                "hole-witness-duplicate",
                f"{path} and {seen[hole]} both name the hole {hole}; a hole takes one witness",
                {"path": path, "other": seen[hole], "hole": hole},
            )
        if layout.mentions_sorry(text):
            return [], Diagnostic(
                "hole-witness-sorry",
                f"{path} uses `sorry`: a carried witness is a finished one. Leave the file out "
                f"and the hole {hole} is created with its slot, as before (F07-R23)",
                {"path": path, "hole": hole},
            )
        seen[hole] = path
        numbered.append((n, Carried(hole=hole, path=path, text=text)))
    return [c for _, c in sorted(numbered, key=lambda pair: pair[0])], None


def without_partial(paths: list[str]) -> Diagnostic:
    """R23: a witness file in a submission that is not a partial."""
    return Diagnostic(
        "hole-witness-without-partial",
        "a carried witness belongs to a partial's assembly, and this submission has none: "
        + ", ".join(paths)
        + ". The witness of an existing hole goes in as its Witness.lean (F08-R5)",
        {"paths": paths},
    )
