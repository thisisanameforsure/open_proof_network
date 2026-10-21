"""Closure records (F28-T8; decisions v3.42): a node proved by construction.

A node whose merged decomposition has every hole proved is proved: the assembly the gate checked,
the children it wrote as exactly the gaps, and the children's proofs are the whole proof. The
post-merge job joins them at the level of terms (``opn-close``), the kernel accepts the node's
theorem, and the job writes this record beside the node as ``closure.json``, signed with the gate
key in the one step that holds it. A ``resolves`` variant's relation joins the same way,
with the composed proof text kept in the record.

Nothing here is a status. ``graph.derive_statuses`` reads the record and derives *proved* while
every input of its link is proved, so a reverted input re-opens the node on the next render and
no record is ever rewritten (D-18 v3.18, the owner's four principles). A root needs, in addition,
the statement vouching step 9 already accepts (a certificate, catalog evidence, a completed
formalization review), since that is the moment a conjecture would read settled.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate import schemas

SCHEMA = "closure/v2"  # F08-T44 (D-12 v3.46): ``verdict``, proved or refuted
#: Every version a record on the graph may carry; v1 records (before v3.46) are read as proved.
ACCEPTED: tuple[str, ...] = ("closure/v1", "closure/v2")
#: D-12 v3.42 / v3.46: what the join accepted.
VERDICT_PROVED = "proved"
VERDICT_REFUTED = "refuted"
FILE = "closure.json"


@dataclass(frozen=True)
class Link:
    """What the record joined: ``kind`` (route or variant; the claim link retired, F28-Q11),
    its id, its inputs."""

    kind: str
    id: str
    inputs: tuple[str, ...]


def path_for(node_dir: Path) -> Path:
    """Where a node's closure record lives."""
    return node_dir / FILE


def load(node_dir: Path) -> dict[str, Any] | None:
    """The node's closure record, validated, or ``None`` when it has none."""
    path = path_for(node_dir)
    if not path.is_file():
        return None
    doc = schemas.load_json(path)
    declared = doc.get("schema") if isinstance(doc, dict) else None
    if declared not in ACCEPTED:
        msg = f"{path}: schema {declared!r} is not a closure record this gate reads"
        raise schemas.SchemaError(msg)
    return schemas.validate(doc, str(declared))


def verdict_of(record: Mapping[str, Any]) -> str:
    """What the record says the join accepted: its ``verdict``, or proved for a v1 record."""
    return str(record.get("verdict") or VERDICT_PROVED)


def link_of(record: Mapping[str, Any]) -> Link:
    raw = record["link"]
    return Link(str(raw["kind"]), str(raw["id"]), tuple(str(i) for i in raw["inputs"]))


def build(  # noqa: PLR0913 — one argument per fact the record carries
    *,
    target_id: str,
    node_id: str,
    statement_hash: str,
    link: Link,
    source_path: str | None,
    source_text: str | None,
    source_hash: str,
    axioms: list[str],
    graph_commit: str,
    network_commit: str | None,
    lean_toolchain: str,
    mathlib_sha: str | None,
    timestamp: str,
    verdict: str = VERDICT_PROVED,
) -> dict[str, Any]:
    """An unsigned record (signature kind ``none``), validated; the post-merge job signs it.
    ``verdict`` is what the join accepted: the node's theorem, or (v3.46) its negation through a
    refutes variant."""
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "target_id": target_id,
        "node_id": node_id,
        "statement_hash": statement_hash,
        "verdict": verdict,
        "link": {"kind": link.kind, "id": link.id, "inputs": list(link.inputs)},
        "source": {"path": source_path, "hash": source_hash, "text": source_text},
        "axioms": sorted(axioms),
        "graph_commit": graph_commit,
        "network_commit": network_commit,
        "lean_toolchain": lean_toolchain,
        "mathlib_sha": mathlib_sha,
        "signature": {"kind": "none", "key_id": None, "value": None, "timestamp": timestamp},
    }
    return schemas.validate(doc, SCHEMA)


def write(node_dir: Path, record: dict[str, Any]) -> Path:
    path = path_for(node_dir)
    path.write_bytes(schemas.canonical_json(schemas.validate(record, SCHEMA)) + b"\n")
    return path
