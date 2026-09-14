"""Second formalizations of a target's conjecture (F14-R7, R8; D-9 layer 4).

A formalization is another Lean statement of the same conjecture — a Mathlib-native restatement,
a registry's own file, a curator's independent attempt — kept under
``targets/<id>/formalizations/<name>/`` as its ``Statement.lean`` beside a ``formalization/v1``
record. It lives outside ``nodes/`` on purpose: it is evidence about the root, never a node, never
on the frontier, never claimable. Its weight comes from ``opn-gate qa equivalence``: both
implications between the root and it, proved and replayed, recorded on the root's QA record with
``against`` naming it (``qa/v2``). A failure is inconclusive and never negative evidence (F12-Q3).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate import layout, schemas
from opn_gate.diagnostic import Diagnostic

SCHEMA = "formalization/v1"
FORMALIZATIONS_DIR = "formalizations"
RECORD_FILE = "formalization.yaml"
STATEMENT_FILE = "Statement.lean"


class FormalizationError(ValueError):
    """A formalization on disk is not one the gate would have merged."""


@dataclass(frozen=True)
class Formalization:
    name: str
    path: Path
    doc: dict[str, Any]
    statement: layout.Statement

    @property
    def statement_hash(self) -> str:
        return self.statement.statement_hash


def formalizations_dir(target_dir: Path) -> Path:
    return target_dir / FORMALIZATIONS_DIR


def names(target_dir: Path) -> list[str]:
    directory = formalizations_dir(target_dir)
    if not directory.is_dir():
        return []
    return sorted(p.name for p in directory.iterdir() if p.is_dir())


def problems(target_dir: Path, name: str) -> list[Diagnostic]:
    """F14-R7: everything wrong with one formalization directory, or ``[]``.

    The record validates and names its own directory; the name is not a node id (a formalization is
    never a node); the statement is F00-R19's one sorry-bodied theorem, declares what the record
    says, hashes to what the record says, and imports only library modules or ``Defs.*``."""
    rel = f"{FORMALIZATIONS_DIR}/{name}"
    directory = formalizations_dir(target_dir) / name
    record, statement = directory / RECORD_FILE, directory / STATEMENT_FILE
    for path in (record, statement):
        if not path.is_file():
            return [
                Diagnostic(
                    "formalization-incomplete",
                    f"{rel}: a formalization is its {RECORD_FILE} and its {STATEMENT_FILE} "
                    f"together; {path.name} is missing (F14-R7)",
                    {"formalization": name, "missing": path.name},
                )
            ]
    try:
        doc = schemas.load_yaml(record, SCHEMA)
    except schemas.SchemaError as exc:
        return [
            Diagnostic("record-invalid", f"{rel}/{RECORD_FILE}: {exc}", {"formalization": name})
        ]
    found: list[Diagnostic] = []
    if doc["name"] != name:
        found.append(
            Diagnostic(
                "formalization-name",
                f"{rel}: the record names {doc['name']!r}, and its directory is {name!r}",
                {"formalization": name, "record": doc["name"]},
            )
        )
    if (layout.graph_nodes_dir(target_dir.parents[1], target_dir.name) / name).exists():
        found.append(
            Diagnostic(
                "formalization-name",
                f"{rel}: {name!r} is a node of {target_dir.name}; a formalization is never a node "
                "(F14-R7)",
                {"formalization": name},
            )
        )
    text = statement.read_text(encoding="utf-8")
    parsed = layout.parse_statement(text)
    if isinstance(parsed, Diagnostic):
        found.append(
            Diagnostic(
                "formalization-shape",
                f"{rel}/{STATEMENT_FILE}: {parsed.message}",
                {"formalization": name},
            )
        )
        return found
    if parsed.statement_hash != doc["statement_hash"]:
        found.append(
            Diagnostic(
                "formalization-hash",
                f"{rel}: {STATEMENT_FILE} hashes to {parsed.statement_hash}, and the record says "
                f"{doc['statement_hash']}",
                {"formalization": name, "computed": parsed.statement_hash},
            )
        )
    if parsed.decl_name != doc["declaration"]:
        found.append(
            Diagnostic(
                "formalization-declaration",
                f"{rel}: {STATEMENT_FILE} declares {parsed.decl_name!r}, and the record says "
                f"{doc['declaration']!r}",
                {"formalization": name, "declared": parsed.decl_name},
            )
        )
    for module in layout.imports_of(text):
        kind, _ = layout.module_origin(module)
        if kind not in ("library", "defs"):
            found.append(
                Diagnostic(
                    "import-forbidden",
                    f"{rel}/{STATEMENT_FILE} imports {module}; a formalization imports library "
                    "modules and Defs.* only",
                    {"formalization": name, "module": module},
                )
            )
    return found


def get(target_dir: Path, name: str) -> Formalization | None:
    """The formalization ``name``, or ``None`` when there is no such directory; one that exists
    and is not sound raises, because an equivalence against it would be evidence about nothing."""
    directory = formalizations_dir(target_dir) / name
    if not directory.is_dir():
        return None
    found = problems(target_dir, name)
    if found:
        raise FormalizationError("; ".join(d.message for d in found))
    doc = schemas.load_yaml(directory / RECORD_FILE, SCHEMA)
    parsed = layout.parse_statement((directory / STATEMENT_FILE).read_text(encoding="utf-8"))
    assert not isinstance(parsed, Diagnostic)  # problems() just parsed it
    return Formalization(name=name, path=directory, doc=doc, statement=parsed)


def load(target_dir: Path) -> list[Formalization]:
    out = [get(target_dir, name) for name in names(target_dir)]
    return [f for f in out if f is not None]


def summary(target_dir: Path) -> list[dict[str, Any]]:
    """F14-R9: each formalization with the latest equivalence verdict recorded against it as it
    stands (the root's QA rows whose ``against`` names it and its hash), or ``None`` where none has
    run, and that row's exhibit."""
    from opn_gate import fidelity, qa  # noqa: PLC0415 — qa reads this module for equivalence

    records = qa.load(target_dir).get(fidelity.ROOT_SUBJECT, [])
    out: list[dict[str, Any]] = []
    for formalization in load(target_dir):
        latest = None
        for record in records:
            for row in record.checks:
                against = row.against or {}
                if (
                    row.check == "equivalence"
                    and against.get("kind") == "formalization"
                    and against.get("ref") == formalization.name
                    and against.get("statement_hash") == formalization.statement_hash
                ):
                    latest = row
        out.append(
            {
                "name": formalization.name,
                "statement_hash": formalization.statement_hash,
                "equivalence": latest.verdict if latest is not None else None,
                "exhibit": latest.exhibit if latest is not None else None,
            }
        )
    return out
