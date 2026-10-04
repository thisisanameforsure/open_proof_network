"""Glosses: prose saying what one Lean file says (F20-R1, R3; D-3 v3.30).

Every Lean file on the graph that is not a proof — a node's ``Statement.lean``, ``Witness.lean``
and ``Relation.lean``, and each definition module under ``targets/<id>/defs/`` — may carry a
*gloss*: Markdown whose YAML front matter (``gloss/v1``) names the target, the subject (its kind,
its node or module, and ``lean_hash``, the SHA-256 of the exact Lean text it describes), the
version it supersedes, its author or the drafter that wrote it, the date and the licence. A
node's glosses live at ``nodes/<id>/gloss/<hash>.md`` and a definition module's at
``targets/<id>/gloss/<hash>.md``, each named for its own content like an explainer (D-3), so a
correction is a new file and never an edit.

A gloss asserts nothing a kernel could check, so it is accepted on a node of *any* status by the
path and file checks alone — no Lean is run (R1). What the gate does check is that it describes
the file as the tree holds it at merge (R3): a ``lean_hash`` that is not the subject's current
hash is refused ``gloss-subject-mismatch``, naming the current one. When the file later changes
(a hole's witness filled, say), the gloss stays in the tree and is read as describing an earlier
version (``describes_current``). Nothing here reads the prose for truth (D-3).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from opn_gate import paths, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Located

log = logging.getLogger(__name__)

SCHEMA = "gloss/v1"
GLOSS_DIR = "gloss"
#: The Lean file a node-level gloss of each kind describes (R1).
KIND_FILES: dict[str, str] = {
    "statement": paths.NODE_DEFINITION_FILES[1],  # Statement.lean
    "witness": paths.WITNESS_FILE,
    "relation": paths.RELATION_FILE,
}
DEFINITION = "definition"
DEFS_DIR = "defs"
_FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<yaml>.*?)\r?\n---[ \t]*\r?\n?", re.S)


class GlossError(ValueError):
    """A gloss command cannot do what was asked. Nothing is written."""


def split_front_matter(text: str) -> tuple[dict[str, Any] | None, str]:
    """``(front matter, body)``; ``(None, text)`` when the file opens with no front matter.
    Front matter that does not parse to a mapping raises ``ValueError`` naming why."""
    m = _FRONT_MATTER_RE.match(text)
    if m is None:
        return None, text
    try:
        doc = yaml.safe_load(m.group("yaml"))
    except yaml.YAMLError as exc:
        msg = f"the front matter is not parseable YAML: {exc.__class__.__name__}"
        raise ValueError(msg) from exc
    if not isinstance(doc, dict):
        msg = "the front matter must be one mapping"
        raise ValueError(msg)
    return doc, text[m.end() :]


def target_dir_of(graph_root: Path, target_id: str) -> Path:
    return graph_root / "targets" / target_id


def subject_file(target_dir: Path, subject: dict[str, Any]) -> Path | None:
    """The Lean file a gloss's subject names, under its target, or ``None`` when the subject's
    kind and location do not fit together (a definition with a node, a statement with none)."""
    kind = subject.get("kind")
    node = subject.get("node")
    module = subject.get("module")
    if kind == DEFINITION:
        if node is not None or not isinstance(module, str):
            return None
        return target_dir / DEFS_DIR / module
    if kind in KIND_FILES and isinstance(node, str) and module is None:
        return target_dir / "nodes" / node / KIND_FILES[str(kind)]
    return None


def _invalid(located: Located, why: str, **details: Any) -> Diagnostic:
    return Diagnostic(
        "gloss-invalid",
        f"{located.path}: {why} (F20-R1; gloss/v1)",
        {"path": located.path, **details},
    )


def document(located: Located, data: bytes) -> dict[str, Any] | Diagnostic:  # noqa: PLR0911
    """The gloss's front matter, validated against ``gloss/v1`` with exactly one of author and
    drafter set; or the reason it is not a gloss, as ``gloss-invalid``."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return _invalid(located, "the file is not valid UTF-8")
    try:
        doc, _body = split_front_matter(text)
    except ValueError as exc:
        return _invalid(located, str(exc))
    if doc is None:
        return _invalid(
            located,
            "a gloss opens with YAML front matter naming its target, its subject and the hash of "
            "the Lean it describes",
        )
    if doc.get("schema") != SCHEMA:
        return _invalid(located, f"the front matter declares {doc.get('schema')!r}, not {SCHEMA}")
    violations = schemas.violations(doc, SCHEMA)
    if violations:
        v = violations[0]
        return _invalid(located, f"{v.path}: {v.message}", field=v.path)
    if (doc["author"] is None) == (doc["drafter"] is None):
        return _invalid(
            located,
            "exactly one of author and drafter is set: a person's version names its author, a "
            "draft names its drafter and no author (D-23)",
        )
    return doc


def check_gloss(graph_root: Path, located: Located) -> list[Diagnostic]:  # noqa: PLR0911
    """R1, R3: a gloss is named for its content, validates, describes a Lean file of the node or
    target it is filed under, and names that file's text as the tree holds it now. Runs no Lean.
    Whether it may supersede what it names is ``check_supersedes``'s question."""
    try:
        data = (graph_root / located.path).read_bytes()
    except OSError as exc:
        return [
            Diagnostic(
                "append-unreadable",
                f"{located.path} cannot be read from the checkout: {exc.strerror}",
                {"path": located.path},
            )
        ]
    naming = paths.check_content_hash_name(located, data)
    if naming is not None:
        return [naming]
    doc = document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]
    subject: dict[str, Any] = doc["subject"]
    if doc["target"] != located.target_id:
        return [
            _invalid(
                located,
                f"it glosses a file of {doc['target']} and sits under {located.target_id}",
            )
        ]
    if located.node_id is None and subject["kind"] != DEFINITION:
        return [
            _invalid(
                located,
                f"a {subject['kind']} gloss sits under its node, nodes/<id>/{GLOSS_DIR}/; "
                f"targets/<id>/{GLOSS_DIR}/ holds the glosses of definition modules",
            )
        ]
    if located.node_id is not None and subject["node"] != located.node_id:
        return [
            _invalid(
                located,
                f"it glosses {subject['kind']} of {subject['node']!r} and sits under "
                f"{located.node_id}",
            )
        ]
    target_dir = target_dir_of(graph_root, located.target_id)
    file = subject_file(target_dir, subject)
    if file is None:
        return [
            _invalid(
                located,
                "a statement, witness or relation names its node and no module; a definition "
                "names its module and no node",
            )
        ]
    if not file.is_file():
        rel = file.relative_to(graph_root).as_posix()
        return [
            Diagnostic(
                "gloss-subject-unknown",
                f"{located.path} glosses {rel}, which is not in the tree (F20-R1)",
                {"path": located.path, "file": rel},
            )
        ]
    current = schemas.content_hash(file.read_bytes())
    if subject["lean_hash"] != current:
        rel = file.relative_to(graph_root).as_posix()
        return [
            Diagnostic(
                "gloss-subject-mismatch",
                f"{located.path} describes {rel} at {subject['lean_hash']}, and the file as it "
                f"stands hashes to {current}: gloss the text that is there (F20-R3)",
                {
                    "path": located.path,
                    "file": rel,
                    "lean_hash": subject["lean_hash"],
                    "current": current,
                },
            )
        ]
    return []
