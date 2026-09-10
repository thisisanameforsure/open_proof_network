"""Building a node directory from a statement and a witness (F08-R3, R4, R5, R9).

Every node in the graph has the same shape (D-3), and every way a node enters it — a speculative
crux (D-14), a labeled variant (D-30), a compiler-derived hole (D-29), a curator's revision
(D-8) — differs only in what goes into that shape. So there is one builder, and the callers
differ in their arguments rather than in their file writing.

Two things it will not do. It never writes into an existing node directory, because a node's
statement is immutable (D-3, D-8) and a proposal that touched one would be a revision wearing a
proposal's clothes. And it decides nothing: a scaffolded directory is a *candidate*, and whether
it may enter the graph is admission's answer (``opn_gate.admit``), which runs on the files this
produced exactly as it would on hand-written ones.

``Context.lean`` is generated rather than accepted, because F01-R6 requires each declared dep's
signature there to hash-equal that dep's own ``Statement.lean`` — a property that is free when
the file is derived from the deps and fragile when it is typed by hand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from opn_gate import layout, schemas

META_SCHEMA = "meta/v2"
NODE_STATUS_SCHEMA = "node-status/v1"
RELATION_FILE = "Relation.lean"
RELATION_DECL = "relation"
#: D-30's labels. Above ``related`` the label is a claim, and needs ``Relation.lean``.
RELATION_LABELS: tuple[str, ...] = ("related", "partial", "resolves")
LABELS_NEEDING_PROOF: tuple[str, ...] = ("partial", "resolves")
Origin = Literal["authored", "compiler-derived", "variant"]

#: What a fresh node's META says before the products regenerate it (F03 owns ``status``).
SCAFFOLD_STATUS = "ready"

_IMPORT_LINE = re.compile(r"^import\s+\S+\s*$", re.M)
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MAX_SLUG = 64  # F08 §6


class ScaffoldError(ValueError):
    """The inputs do not describe a node that could exist. Raised before anything is written."""


@dataclass(frozen=True)
class Proposal:
    """What someone is proposing: the files, and the little that is not a file."""

    node_id: str
    target_id: str
    statement: str
    witness: str
    author: str
    deps: tuple[str, ...] = ()
    origin: Origin = "authored"
    relation: str | None = None  # D-30 label, variants only
    relation_proof: str | None = None
    speculative: bool = False  # F08-Q2: recorded as a status record, not a META field
    date: str | None = None
    model: str | None = None
    extra_meta: dict[str, Any] = field(default_factory=dict)

    @property
    def is_variant(self) -> bool:
        return self.origin == "variant"


def check_slug(node_id: str) -> str:
    if not _SLUG_RE.match(node_id) or len(node_id) > MAX_SLUG:
        msg = f"node id {node_id!r} must match ^[a-z0-9][a-z0-9-]*$ and be at most {MAX_SLUG} chars"
        raise ScaffoldError(msg)
    return node_id


def speculative_id(statement: str, prefix: str = "spec") -> str:
    """``spec-<hash8>`` (F08-R3): derived from the statement, so the same crux proposed twice
    collides by name rather than entering the graph twice."""
    return f"{prefix}-{schemas.content_hash(statement.encode('utf-8'))[:8]}"


def strip_imports(text: str) -> str:
    return _IMPORT_LINE.sub("", text).strip("\n")


def imports_of(texts: list[str]) -> list[str]:
    """The imports a generated ``Context.lean`` may carry: library modules and ``Defs.*`` only.

    A dep's ``Statement.lean`` imports that dep's own ``Context``, which this file must not
    (D-3 restricts Context's imports, F00's layout check enforces it) and does not need — the
    signatures it carries have ``sorry`` bodies and depend on nothing.
    """
    seen: list[str] = []
    for text in texts:
        for module in layout.imports_of(text):
            kind, _ = layout.module_origin(module)
            if kind in ("library", "defs") and module not in seen:
                seen.append(module)
    return seen


def context_for(nodes_dir: Path, deps: tuple[str, ...]) -> str:
    """``Context.lean``: each declared dep's statement, verbatim, under the union of imports.

    Verbatim is the point — F01-R6 compares the signature here with the dep's own
    ``Statement.lean``, and anything but a copy risks differing by a space.
    """
    if not deps:
        return "/-! Declared dependencies (D-4 step 8): none. -/\n"
    texts: list[str] = []
    for dep in deps:
        statement = nodes_dir / dep / "Statement.lean"
        if not statement.is_file():
            msg = f"declared dep {dep!r} is not a node of this target"
            raise ScaffoldError(msg)
        texts.append(statement.read_text(encoding="utf-8"))
    header = "/-! Declared dependencies (D-4 step 8): " + ", ".join(f"`{d}`" for d in deps) + ". -/"
    parts = [header, *(f"\n{strip_imports(t)}\n" for t in texts)]
    lines = [f"import {m}" for m in imports_of(texts)]
    if lines:
        parts.insert(0, "\n".join(lines) + "\n")
    return "\n".join(parts).rstrip("\n") + "\n"


def meta_for(proposal: Proposal, statement_hash: str) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": META_SCHEMA,
        "id": proposal.node_id,
        "status": SCAFFOLD_STATUS,
        "deps": list(proposal.deps),
        "statement-hash": statement_hash,
        "origin": proposal.origin,
        "provenance": {
            "author": proposal.author,
            "model": proposal.model,
            "source": None,
        },
        "tutorial": False,
    }
    if proposal.date:
        doc["provenance"]["date"] = day(proposal.date)  # META records the day, not the second
    doc.update(proposal.extra_meta)
    return doc


def day(timestamp: str) -> str:
    """The date part of an ISO timestamp; the record schemas take a day, not a second."""
    return timestamp[:10]


def status_record(proposal: Proposal) -> dict[str, Any]:
    """F08-Q2: ``speculative`` is a status record, because F03's derived statuses are the tree's
    and D-14 describes a crux as an authored statement. D-3 gained a fourth ``origin`` in v3.12,
    but it is ``skeleton-hole``, so this call is unchanged."""
    return {
        "schema": NODE_STATUS_SCHEMA,
        "status": "speculative",
        "cause": f"proposed as a crux statement by {proposal.author} (D-14 mechanism 2)",
        "author": proposal.author,
        "date": day(proposal.date or "") or "1970-01-01",
    }


def validate(proposal: Proposal) -> None:
    """Everything that can be refused before a byte is written (C7)."""
    check_slug(proposal.node_id)
    check_slug(proposal.target_id)
    parsed = layout.parse_statement(proposal.statement)
    if not isinstance(parsed, layout.Statement):
        msg = f"the statement is not a single sorry-bodied theorem: {parsed.message}"
        raise ScaffoldError(msg)
    if not proposal.witness.strip():
        msg = "a proposed node needs a Witness.lean (D-4 step 7)"
        raise ScaffoldError(msg)
    if proposal.relation is not None and proposal.relation not in RELATION_LABELS:
        msg = f"relation must be one of {', '.join(RELATION_LABELS)} (D-30)"
        raise ScaffoldError(msg)
    claims = proposal.is_variant and proposal.relation in LABELS_NEEDING_PROOF
    if claims and not (proposal.relation_proof or "").strip():
        msg = (
            f"a variant labeled {proposal.relation!r} claims an implication, so it needs a "
            "relation proof (D-30)"
        )
        raise ScaffoldError(msg)
    if proposal.relation_proof and not proposal.is_variant:
        msg = "Relation.lean belongs to variants only (D-3)"
        raise ScaffoldError(msg)


def files(nodes_dir: Path, proposal: Proposal) -> dict[str, str]:
    """The node directory as a mapping of relative path to content — what a PR would add.

    Returned rather than written so the service can put the same bytes in a branch (F07-R2)
    without ever having the graph checked out.
    """
    validate(proposal)
    parsed = layout.parse_statement(proposal.statement)
    assert isinstance(parsed, layout.Statement)
    out: dict[str, str] = {
        "Statement.lean": proposal.statement,
        "Witness.lean": proposal.witness,
        "Context.lean": context_for(nodes_dir, proposal.deps),
        "META.yaml": _yaml(meta_for(proposal, parsed.statement_hash)),
    }
    for keep in layout.REQUIRED_DIRS:
        out[f"{keep}/{layout.KEEP_FILE}"] = ""
    if proposal.is_variant and proposal.relation_proof:
        out[RELATION_FILE] = proposal.relation_proof
    if proposal.speculative:
        stamp = (proposal.date or "1970-01-01T00:00:00Z").replace(":", "").replace("-", "")
        out[f"status/{stamp[:15]}-{proposal.author}.yaml"] = _yaml(status_record(proposal))
    return out


def write(nodes_dir: Path, proposal: Proposal) -> Path:
    """Write the node directory under ``nodes_dir``; refuse to touch one that already exists."""
    node_dir = nodes_dir / proposal.node_id
    if node_dir.exists():
        msg = f"{proposal.node_id} already exists; a statement is never edited in place (D-3, D-8)"
        raise ScaffoldError(msg)
    for rel, content in files(nodes_dir, proposal).items():
        dest = node_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    return node_dir


def _yaml(doc: dict[str, Any]) -> str:
    import yaml  # noqa: PLC0415 — only the writing path needs it

    return str(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
