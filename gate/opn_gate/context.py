"""The per-node context bundle, ``nodes/<id>/CONTEXT.json`` (F10-T2; R3, R4; D-27, D-28, D-31).

One document an agent reads by clone or by tool: the statement and its hash, the declared
dependencies with their signatures, the witness, the derived status, the gate-spec reference,
the claim snapshot, the attempt log as typed records with every free-text field demarcated and
``detail`` capped, annex hashes with sizes, and whether an explainer exists. It is a rendering
of the node's own files plus the facts the products already derive — nothing evidentiary lives
here (F10-Q2) — so it is regenerated on every merge and byte-identical for one tree.

``build`` reads through a ``Reader`` rather than a directory so the same generator serves two
callers: the post-merge job over the checkout (``DiskReader``) and the api over the host, which
derives the identical document for a graph that has none committed yet (F10-Q7).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

from opn_gate import demarcate, layout, schemas
from opn_gate import graph as graphmod
from opn_gate.diagnostic import Diagnostic
from opn_gate.graph import GraphError

SCHEMA = "context/v1"
FILE = layout.CONTEXT_FILE
CLAIMS_FILE = "claims.json"
CLAIMS_SCHEMA = "claims/v1"
POSTMORTEM_SCHEMA = "postmortem/v1"
DETAIL_MAX_CHARS = 500  # R3: no detail longer than this reaches a bundle
DETAIL_FIELD = "detail"
RECORD_LIMIT = 50  # §6: the newest records
MAX_BYTES = 256 * 1024  # §6
ELLIPSIS = "…"
KEEP_FILE = ".gitkeep"
YAML_SUFFIXES: tuple[str, ...] = (".yaml", ".yml")
LEAN_SUFFIX = ".lean"
PROSE_SUFFIX = ".md"
INVALID = "invalid"


class ContextError(GraphError):
    """The node's files do not render to a bundle; nothing is written (C7)."""


class Reader(Protocol):
    """Where the node's files come from: a checkout, or the graph's host at ``main``."""

    def read(self, path: str) -> bytes | None:
        """The bytes at a graph-relative path, or ``None`` when there is no such file."""

    def listdir(self, path: str) -> list[str]:
        """The names of the files directly under a directory; ``[]`` when it does not exist."""


class DiskReader:
    def __init__(self, root: Path) -> None:
        self.root = root

    def read(self, path: str) -> bytes | None:
        target = self.root / path
        return target.read_bytes() if target.is_file() else None

    def listdir(self, path: str) -> list[str]:
        directory = self.root / path
        if not directory.is_dir():
            return []
        return sorted(p.name for p in directory.iterdir() if p.is_file())


@dataclass(frozen=True)
class NodeState:
    """What the products derived for a node (F03); the bundle repeats it rather than re-deriving."""

    status: str
    cause: str | None
    proof_commit: str | None
    trust_base: str | None


def graph_states(doc: Mapping[str, Any]) -> dict[str, NodeState]:
    """The states a ``graph.json`` document (``graph/v2``) records, keyed by node id."""
    return {
        str(n["node_id"]): NodeState(
            status=str(n["status"]),
            cause=_optional(n.get("cause")),
            proof_commit=_optional(n.get("proof_commit")),
            trust_base=_optional(n.get("trust_base")),
        )
        for n in doc.get("nodes", [])
        if isinstance(n, dict)
    }


def _optional(value: object) -> str | None:
    return str(value) if isinstance(value, str) and value else None


def node_path(target_id: str, node_id: str) -> str:
    return f"targets/{target_id}/nodes/{node_id}"


def context_path(target_id: str, node_id: str) -> str:
    return f"{node_path(target_id, node_id)}/{FILE}"


# --- the pieces ----------------------------------------------------------------------------------


def _text(raw: bytes, path: str) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        msg = f"{path} is not UTF-8"
        raise ContextError(msg) from exc


def _must(reader: Reader, path: str) -> bytes:
    raw = reader.read(path)
    if raw is None:
        msg = f"{path} is missing"
        raise ContextError(msg)
    return raw


def _yaml(raw: bytes, path: str, schema_id: str | None) -> dict[str, Any]:
    try:
        doc: object = yaml.safe_load(_text(raw, path))
    except yaml.YAMLError as exc:
        msg = f"{path} is not YAML: {exc}"
        raise schemas.SchemaError(msg) from exc
    return schemas.validate(doc, schema_id)


def _statement(reader: Reader, node_dir: str) -> dict[str, Any]:
    path = f"{node_dir}/Statement.lean"
    raw = _must(reader, path)
    parsed = layout.parse_statement(_text(raw, path))
    if isinstance(parsed, Diagnostic):
        msg = f"{path}: {parsed.message}"
        raise ContextError(msg)
    return {"decl": parsed.decl_name, "hash": schemas.content_hash(raw), "text": parsed.text}


def _witness(reader: Reader, node_dir: str) -> dict[str, Any]:
    path = f"{node_dir}/Witness.lean"
    raw = reader.read(path)
    text = _text(raw, path) if raw is not None else None
    return {"text": text, "stub": text is None or layout.mentions_sorry(text)}


def _proof(reader: Reader, node_dir: str, statement_decl: str, state: NodeState) -> dict[str, Any]:
    from opn_gate.steps import artifact  # noqa: PLC0415 — steps.base would otherwise cycle

    path = f"{node_dir}/Proof.lean"
    raw = reader.read(path)
    kind: str | None = None
    if raw is not None:
        declared = layout.parse_declaration(_text(raw, path), "Proof.lean")
        if not isinstance(declared, Diagnostic):
            kind = artifact.kind_of(statement_decl, declared)
    resolved = state.status in graphmod.RESOLVED_STATUSES and raw is not None
    return {
        "present": raw is not None,
        "artifact": kind,
        "commit": state.proof_commit if resolved else None,
        "trust_base": state.trust_base if resolved else None,
    }


def _deps(
    reader: Reader, target_id: str, meta: Mapping[str, Any], states: Mapping[str, NodeState]
) -> list[dict[str, Any]]:
    out = []
    raw_deps = meta.get("deps")
    for dep in [str(d) for d in raw_deps] if isinstance(raw_deps, list) else []:
        path = f"{node_path(target_id, dep)}/Statement.lean"
        raw = _must(reader, path)
        if dep not in states:
            msg = f"dep {dep!r} has no derived status; the graph products do not know it"
            raise ContextError(msg)
        out.append(
            {
                "node_id": dep,
                "status": states[dep].status,
                "statement_hash": schemas.content_hash(raw),
                "signature": _text(raw, path),
            }
        )
    return out


def _meta(reader: Reader, node_dir: str, meta: Mapping[str, Any], meta_path: str) -> dict[str, Any]:
    origin = str(meta.get("origin", "authored"))
    relation_raw = reader.read(f"{node_dir}/Relation.lean")
    relation_text = _text(relation_raw, "Relation.lean") if relation_raw is not None else None
    wrapped = demarcate.record(dict(meta), meta_path)
    acknowledged = wrapped.get("acknowledged_hazards")
    return {
        "origin": origin,
        "tutorial": bool(meta.get("tutorial", False)),
        "relation": graphmod.relation_label(relation_text, origin),
        "provenance": dict(meta.get("provenance") or {}),
        "supersedes": _optional(meta.get("supersedes")),
        "acknowledged_hazards": list(acknowledged) if isinstance(acknowledged, list) else [],
    }


def _gate_spec(reader: Reader, target_id: str) -> dict[str, Any]:
    path = f"targets/{target_id}/gate-spec.json"
    raw = _must(reader, path)
    try:
        spec = schemas.validate(__import__("json").loads(raw), "gate-spec/v1")
    except (ValueError, schemas.SchemaError) as exc:
        msg = f"{path} does not validate: {exc}"
        raise ContextError(msg) from exc
    return {
        "path": path,
        "hash": schemas.content_hash(raw),
        "network_commit": spec["network_commit"],
        "lean_toolchain": spec["lean_toolchain"],
        "mathlib_sha": spec["mathlib_sha"],
    }


def _claims(reader: Reader, node_id: str) -> dict[str, Any]:
    """The committed snapshot's entry for the node; empty when there is none or it is defective
    (operational, never evidentiary — the same rule the frontier applies, F05-R10)."""
    empty: dict[str, Any] = {"active": [], "history_count": 0}
    raw = reader.read(CLAIMS_FILE)
    if raw is None:
        return empty
    try:
        doc = schemas.validate(__import__("json").loads(raw), CLAIMS_SCHEMA)
    except (ValueError, schemas.SchemaError):
        return empty
    entry = (doc.get("nodes") or {}).get(node_id)
    if not isinstance(entry, dict):
        return empty
    return {
        "active": [dict(c) for c in entry.get("active", []) if isinstance(c, dict)],
        "history_count": int(entry.get("history_count", 0)),
    }


def shorten_detail(record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """R3: the ``detail`` field cut to the cap, the cut named. The text is wrapped later, so the
    cap applies to what an agent will read."""
    detail = record.get(DETAIL_FIELD)
    if not isinstance(detail, str) or len(detail) <= DETAIL_MAX_CHARS:
        return record, []
    out = dict(record)
    out[DETAIL_FIELD] = detail[: DETAIL_MAX_CHARS - len(ELLIPSIS)] + ELLIPSIS
    return out, [DETAIL_FIELD]


def _attempts(reader: Reader, node_dir: str) -> dict[str, Any]:
    directory = f"{node_dir}/attempts"
    names = [n for n in reader.listdir(directory) if n != KEEP_FILE]
    yaml_names = sorted(n for n in names if n.endswith(YAML_SUFFIXES))
    lean_names = sorted(n for n in names if n.endswith(LEAN_SUFFIX))
    refuted: set[str] = set()
    histogram: dict[str, int] = {}
    parsed: list[tuple[str, dict[str, Any] | None]] = []
    for name in yaml_names:
        path = f"{directory}/{name}"
        raw = _must(reader, path)
        doc: dict[str, Any] | None
        try:
            doc = _yaml(raw, path, POSTMORTEM_SCHEMA)
        except schemas.SchemaError:
            histogram[INVALID] = histogram.get(INVALID, 0) + 1
            parsed.append((path, None))
            continue
        if doc.get("outcome") == "refuted-route":
            refuted.add(str(doc["route_class"]))
        failure_class = doc.get("failure_class")
        if failure_class is not None:
            histogram[str(failure_class)] = histogram.get(str(failure_class), 0) + 1
        parsed.append((path, doc))
    truncated = len(parsed) > RECORD_LIMIT
    kept = parsed[-RECORD_LIMIT:] if truncated else parsed  # names sort by timestamp (F07-R11)
    records: list[dict[str, Any]] = []
    for path, doc in kept:
        if doc is None:
            records.append({"path": path, "invalid": True})
            continue
        shortened, cut = shorten_detail(doc)
        entry: dict[str, Any] = {"path": path, "record": demarcate.record(shortened, path)}
        if cut:
            entry["shortened"] = cut
        records.append(entry)
    assemblies = []
    for name in lean_names:
        path = f"{directory}/{name}"
        raw = _must(reader, path)
        assemblies.append({"path": path, "hash": schemas.content_hash(raw), "bytes": len(raw)})
    return {
        "count": len(yaml_names),
        "refuted_route_classes": sorted(refuted),
        "failure_class_histogram": dict(sorted(histogram.items())),
        "records": records,
        "truncated": truncated,
        "assemblies": assemblies,
    }


def _annexes(reader: Reader, node_dir: str) -> list[dict[str, Any]]:
    directory = f"{node_dir}/annex"
    out = []
    for name in sorted(reader.listdir(directory)):
        if not name.endswith(PROSE_SUFFIX):
            continue
        path = f"{directory}/{name}"
        raw = _must(reader, path)
        out.append({"path": path, "hash": schemas.content_hash(raw), "bytes": len(raw)})
    return out


def _explainer_present(reader: Reader, node_dir: str) -> bool:
    return any(n.endswith(PROSE_SUFFIX) for n in reader.listdir(f"{node_dir}/explainer"))


# --- the document --------------------------------------------------------------------------------


def build(
    reader: Reader,
    target_id: str,
    node_id: str,
    *,
    states: Mapping[str, NodeState],
    rendered_from: str | None,
) -> dict[str, Any]:
    """The validated bundle for one node, within the size budget (§6).

    Deterministic in the files and the states: no clock, no host, keys sorted by the canonical
    serialization, so two runs over one tree are byte-identical (AC3).
    """
    if node_id not in states:
        msg = f"{node_id} has no derived status; the graph products do not know it"
        raise ContextError(msg)
    state = states[node_id]
    node_dir = node_path(target_id, node_id)
    meta_path = f"{node_dir}/META.yaml"
    try:
        meta = _yaml(_must(reader, meta_path), meta_path, None)
    except schemas.SchemaError as exc:
        msg = f"{meta_path} does not validate: {exc}"
        raise ContextError(msg) from exc
    if meta.get("schema") not in layout.META_SCHEMAS:
        msg = f"{meta_path}: schema {meta.get('schema')!r} is not accepted"
        raise ContextError(msg)
    statement = _statement(reader, node_dir)
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "node_id": node_id,
        "target_id": target_id,
        "rendered_from": rendered_from,
        "status": state.status,
        "cause": state.cause,
        "statement": statement,
        "witness": _witness(reader, node_dir),
        "proof": _proof(reader, node_dir, statement["decl"], state),
        "deps": _deps(reader, target_id, meta, states),
        "meta": _meta(reader, node_dir, meta, meta_path),
        "gate_spec": _gate_spec(reader, target_id),
        "claims": _claims(reader, node_id),
        "attempts": _attempts(reader, node_dir),
        "annexes": _annexes(reader, node_dir),
        "explainer_present": _explainer_present(reader, node_dir),
        "untrusted_note": demarcate.UNTRUSTED_NOTE,
    }
    fit(doc)
    return schemas.validate(doc, SCHEMA)


def fit(doc: dict[str, Any]) -> None:
    """§6: under the byte cap, dropping the oldest attempt records first and saying so. A node
    whose files alone exceed the cap cannot be bundled, and that is an error, not a silent cut."""
    attempts = doc["attempts"]
    while len(schemas.canonical_json(doc)) > MAX_BYTES and attempts["records"]:
        attempts["records"] = attempts["records"][1:]
        attempts["truncated"] = True
    if len(schemas.canonical_json(doc)) > MAX_BYTES:
        msg = f"{doc['node_id']}: the bundle exceeds {MAX_BYTES} bytes with no attempt records"
        raise ContextError(msg)


def render(
    reader: Reader,
    target_id: str,
    node_id: str,
    *,
    states: Mapping[str, NodeState],
    rendered_from: str | None,
) -> bytes:
    """The bundle as the bytes the file holds."""
    return schemas.canonical_json(
        build(reader, target_id, node_id, states=states, rendered_from=rendered_from)
    )
