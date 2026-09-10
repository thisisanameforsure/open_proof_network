"""What kind of pull request this is, and what that kind may touch (F07-R3, R9, R10).

Until F07 every pull request the gate saw was a proof of one node. D-12's other artifacts, D-13's
postmortems, D-31's annexes, D-14's approach records and D-3's explainers all reach the graph the
same way — a pull request — and they need different checks: a proof runs the Lean pipeline, an
append asserts nothing a kernel could check and merges on its schema, an explainer is prose about
an object that already merged.

So the diff is classified into exactly one mode before anything else runs:

===============  ==========================================================================
``proof``        the node's ``Proof.lean``, plus appends — the D-4 pipeline (D-12 #1, #2, #3)
``partial``      a ``.lean`` assembly under ``attempts/``, plus appends (D-12 #4, #5)
``append``       only new postmortems, precheck records, annexes or approach records
``explainer``    only new files under ``explainer/`` (D-3), on a node that already has a proof
===============  ==========================================================================

A diff that fits none of them is rejected at step 2, naming the paths — never guessed at. F08 adds
the ``proposal`` and ``curator`` modes; until it does, a pull request that proposes a node or
files a curator record is one of those rejections.

Modes are decided from the diff alone. Whether the *submitter* called it a counterexample or a
reduction is in the ``opn-submission`` block (``submission-meta/v1``, F07-R2), and the artifact
checks that consume it are F07-T2's; classification never reads it, because the block is not
evidentiary and the paths are.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from opn_gate import paths, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change, Located, Role

Mode = Literal["proof", "partial", "append", "explainer"]

#: The modes that run the Lean pipeline; the other two never build anything (R9, R10).
BUILDING_MODES: tuple[Mode, ...] = ("proof", "partial")

_FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<yaml>.*?)\r?\n---[ \t]*\r?\n", re.S)


@dataclass(frozen=True)
class Classification:
    """What the diff is. ``mode`` is ``None`` exactly when ``problems`` says why it is nothing."""

    mode: Mode | None
    target_id: str | None
    node_id: str | None
    located: tuple[Located, ...] = ()
    problems: tuple[Diagnostic, ...] = ()

    @property
    def ok(self) -> bool:
        return self.mode is not None

    @property
    def needs_gate(self) -> bool:
        """Whether the sandboxed pipeline runs. Appends and explainers assert nothing (R9, R10)."""
        return self.mode in BUILDING_MODES

    @property
    def needs_review(self) -> bool:
        """Step 9 is a review of a *statement's* claim; an append makes none (F07-Q4)."""
        return self.mode in BUILDING_MODES

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "target": self.target_id,
            "node": self.node_id,
            "needs_gate": self.needs_gate,
            "needs_review": self.needs_review,
            "problems": [d.as_dict() for d in self.problems],
        }


def classify(changes: Iterable[Change]) -> Classification:
    """R3: the diff's one mode, or the reasons it is not a submission at all."""
    changes = list(changes)
    if not changes:
        return _rejected([Diagnostic("mode-empty", "the pull request changes no file")])

    located: list[Located] = []
    problems: list[Diagnostic] = []
    for change in changes:
        problems.extend(_locate_change(change, located))
    if problems:
        return _rejected(problems)

    scoping = _scope(located)
    if isinstance(scoping, list):
        return _rejected(scoping)
    target_id, node_id = scoping

    roles = {loc.role for loc in located}
    mode = _mode_for(roles)
    if mode is None:
        return Classification(
            None,
            target_id,
            node_id,
            tuple(located),
            (
                Diagnostic(
                    "mode-mixed",
                    "this pull request mixes kinds of change that belong in separate ones: "
                    + ", ".join(sorted(roles)),
                    {"roles": sorted(roles)},
                ),
            ),
        )
    return Classification(mode, target_id, node_id, tuple(located))


def _locate_change(change: Change, located: list[Located]) -> list[Diagnostic]:
    """Place one change, or say why it is outside every mode. Appends to ``located`` on success."""
    if change.old_path is not None:
        return [
            Diagnostic(
                "path-forbidden",
                f"{change.old_path} -> {change.path}: nothing in the graph is renamed",
                {"path": change.old_path, "status": change.status},
            )
        ]
    where = paths.locate(change.path)
    if where is None:
        return [
            Diagnostic(
                "path-forbidden",
                f"{change.path} is not a path any submission may touch",
                {"path": change.path, "status": change.status},
            )
        ]
    allowed: tuple[str, ...] = ("A", "M") if where.role in ("proof", "waiver") else ("A",)
    if change.status not in allowed:
        return [
            Diagnostic(
                "path-forbidden",
                f"{change.path}: a {where.role} may not be {_verb(change.status)}",
                {"path": change.path, "status": change.status, "role": where.role},
            )
        ]
    located.append(where)
    return []


def _scope(located: Sequence[Located]) -> tuple[str, str | None] | list[Diagnostic]:
    """One target, at most one node (D-2, D-3): a diff over two nodes is a rejection, not a
    subgraph. An approach record is target-scoped and rides with whatever node the rest name."""
    targets = sorted({loc.target_id for loc in located})
    if len(targets) > 1:
        return [
            Diagnostic(
                "mode-multi-target",
                f"a submission touches one target; this one touches {', '.join(targets)}",
                {"targets": targets},
            )
        ]
    nodes = sorted({loc.node_id for loc in located if loc.node_id is not None})
    if len(nodes) > 1:
        return [
            Diagnostic(
                "mode-multi-node",
                f"a submission touches one node (D-2, D-3); this one touches {', '.join(nodes)}",
                {"nodes": nodes},
            )
        ]
    return targets[0], nodes[0] if nodes else None


def _mode_for(roles: set[Role]) -> Mode | None:
    appendish = set(paths.APPEND_ROLES)
    if "proof" in roles or "waiver" in roles:
        return "proof" if roles <= ({"proof", "waiver"} | appendish) else None
    if "partial" in roles:
        return "partial" if roles <= ({"partial"} | appendish) else None
    if "explainer" in roles:
        return "explainer" if roles == {"explainer"} else None
    return "append"


def _rejected(problems: list[Diagnostic]) -> Classification:
    return Classification(None, None, None, (), tuple(problems))


def _verb(status: str) -> str:
    return {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}[status]


# --- the checks the non-building modes run instead of a build ----------------------------------


def check(graph_root: Path, classification: Classification) -> list[Diagnostic]:
    """R9, R10: everything an ``append`` or ``explainer`` pull request is checked for.

    Content rules that belong to a file rather than to a mode — an annex is named for its own
    content, a postmortem validates against its schema — are applied to those files wherever they
    appear, so a proof that carries an append is held to the same rules.
    """
    problems: list[Diagnostic] = []
    for located in classification.located:
        if located.role in paths.APPEND_ROLES:
            problems.extend(check_append_file(graph_root, located))
        elif located.role == "explainer":
            problems.extend(check_explainer_file(graph_root, located, classification))
    return problems


def check_append_file(graph_root: Path, located: Located) -> list[Diagnostic]:
    """One appended record: name, size and schema. An append claims nothing, so this is all."""
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    problems: list[Diagnostic] = []
    if located.role in paths.CONTENT_HASHED_ROLES:
        naming = paths.check_content_hash_name(located, data)
        if naming is not None:
            problems.append(naming)
    if located.role == "annex" and len(data) > paths.ANNEX_MAX_BYTES:
        problems.append(
            Diagnostic(
                "annex-too-large",
                f"{located.path}: {len(data)} bytes; an annex is capped at "
                f"{paths.ANNEX_MAX_BYTES} bytes",
                {"path": located.path, "bytes": len(data), "cap": paths.ANNEX_MAX_BYTES},
            )
        )
    problems.extend(_check_schema(located, data))
    return problems


def check_explainer_file(
    graph_root: Path, located: Located, classification: Classification
) -> list[Diagnostic]:
    """R10: an explainer is prose about a merged proof; on an unproved node it is a misfiled
    annex (D-3), and it is named for its content like one, because a correction is a new entry."""
    if located.node_id is not None and not _has_proof(graph_root, located):
        return [
            Diagnostic(
                "explainer-unproved",
                f"{located.node_id} has no merged proof, so this text is an annex misfiled as an "
                "explainer: submit it under annex/ (D-3, D-31)",
                {"path": located.path, "node": located.node_id},
            )
        ]
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    naming = paths.check_content_hash_name(located, data)
    return [naming] if naming is not None else []


def _has_proof(graph_root: Path, located: Located) -> bool:
    """A node has a merged proof exactly when ``Proof.lean`` is in the tree: it is the one file a
    submission may create and it only ever arrives by a merge (D-3)."""
    assert located.node_id is not None
    proof = graph_root / "targets" / located.target_id / "nodes" / located.node_id / "Proof.lean"
    return proof.is_file()


def _read(graph_root: Path, located: Located) -> bytes | Diagnostic:
    path = graph_root / located.path
    try:
        return path.read_bytes()
    except OSError as exc:
        return Diagnostic(
            "append-unreadable",
            f"{located.path} cannot be read from the checkout: {exc.strerror}",
            {"path": located.path},
        )


def _check_schema(located: Located, data: bytes) -> list[Diagnostic]:
    schema_id = paths.SCHEMA_FOR_ROLE.get(located.role)
    if schema_id is None:
        return []
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]
    violations = schemas.violations(doc, schema_id)
    return [
        Diagnostic(
            "append-invalid",
            f"{located.path} does not satisfy {schema_id}: {v.path}: {v.message}",
            {"path": located.path, "schema": schema_id, "field": v.path},
        )
        for v in violations[:5]
    ]


def _document(located: Located, data: bytes) -> dict[str, Any] | Diagnostic:
    """The record inside an appended file: the file itself for YAML and JSON records, the YAML
    front matter for an annex, whose body is prose the gate never reads (D-31)."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return Diagnostic(
            "append-invalid",
            f"{located.path} is not valid UTF-8",
            {"path": located.path},
        )
    if located.role == "annex":
        m = _FRONT_MATTER_RE.match(text)
        if m is None:
            return Diagnostic(
                "append-invalid",
                f"{located.path} has no YAML front matter; an annex declares its node, its "
                "contributor and the licence its author releases the prose under (D-23, D-31)",
                {"path": located.path},
            )
        text = m.group("yaml")
    try:
        doc = yaml.safe_load(text)  # a superset of JSON, so it reads both records
    except yaml.YAMLError as exc:
        return Diagnostic(
            "append-invalid",
            f"{located.path} is not parseable: {exc.__class__.__name__}",
            {"path": located.path},
        )
    if not isinstance(doc, dict):
        return Diagnostic(
            "append-invalid",
            f"{located.path} must hold one record object",
            {"path": located.path},
        )
    return doc
