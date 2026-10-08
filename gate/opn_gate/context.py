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

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

from opn_gate import demarcate, layout, paths, schemas
from opn_gate import graph as graphmod
from opn_gate import records as recordsmod
from opn_gate.diagnostic import Diagnostic
from opn_gate.graph import GraphError

log = logging.getLogger(__name__)

#: The version the bundle is written at. F08-T22 (D-12 v3.23): ``context/v2`` adds
#: ``circular_below``; v1 is unchanged (D-34) and a graph rendered before the re-pin still
#: carries it, which is why a reader accepts every version in ``ACCEPTED``.
#: F08-T36 (D-16 v3.28): ``context/v3`` adds ``defect_claims``, the list ``graph.json`` carries.
#: F22-T13: ``context/v4`` gives each ``deps[]`` entry the dep's ``cause`` (testers 2026-10-06).
#: F10-T19 (D-12 v3.35, D-25 v3.35): ``context/v5`` carries ``circular``, ``literature`` and
#: ``literature_proposed`` as ``graph/v6`` does, beside v4's ``circular_below``.
SCHEMA = "context/v5"
ACCEPTED: tuple[str, ...] = ("context/v1", "context/v2", "context/v3", "context/v4", "context/v5")
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
    #: F08-T10: the node's deps as ``graph.json`` publishes them — read through any revision
    #: (D-8 v3.18). ``None`` when the states did not come from a graph document that has them.
    deps: tuple[str, ...] | None = None
    #: F08-T22: the node's origin as ``graph.json`` publishes it, which is how a dep is known to
    #: be one of its parent's holes (``graph.is_hole_of``) for ``circular_below``.
    origin: str | None = None
    #: F08-T39 (D-12 v3.35): the node's ``circular`` label as ``graph/v6`` publishes it, each
    #: ``{ancestor, claim}``; ``None`` when the document predates v6, in which case the builder
    #: derives it from the tree (``_circular``) as the gate would.
    circular: tuple[dict[str, str], ...] | None = None
    #: D-25 v3.35: the literature status ``graph/v6`` publishes (F08-T40), repeated, never
    #: re-derived here: a signed record is verified by the gate's own signer, which a host reader
    #: has no business repeating (F10-Q7). ``None`` when the document carries none or predates v6.
    literature: dict[str, Any] | None = None
    literature_proposed: dict[str, Any] | None = None


def graph_states(doc: Mapping[str, Any]) -> dict[str, NodeState]:
    """The states a ``graph.json`` document (``graph/v2`` on) records, keyed by node id."""
    return {
        str(n["node_id"]): NodeState(
            status=str(n["status"]),
            cause=_optional(n.get("cause")),
            proof_commit=_optional(n.get("proof_commit")),
            trust_base=_optional(n.get("trust_base")),
            deps=(tuple(str(d) for d in n["deps"]) if isinstance(n.get("deps"), list) else None),
            origin=_optional(n.get("origin")),
            circular=_labels(n.get("circular")),
            literature=_mapping(n.get("literature")),
            literature_proposed=_mapping(n.get("literature_proposed")),
        )
        for n in doc.get("nodes", [])
        if isinstance(n, dict)
    }


def _labels(value: Any) -> tuple[dict[str, str], ...] | None:
    """``graph/v6``'s ``circular`` list as the state carries it; ``None`` for an older document."""
    if not isinstance(value, list):
        return None
    return tuple(
        {"ancestor": str(item["ancestor"]), "claim": str(item["claim"])}
        for item in value
        if isinstance(item, dict)
    )


def _mapping(value: Any) -> dict[str, Any] | None:
    return dict(value) if isinstance(value, dict) else None


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
    reader: Reader,
    target_id: str,
    meta: Mapping[str, Any],
    states: Mapping[str, NodeState],
    effective: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """The deps a prover builds against. F08-T10: ``effective`` is the node's deps as the graph
    product has them, read through any revision; ``meta`` keeps the record as it was written."""
    out = []
    raw_deps = meta.get("deps")
    recorded = [str(d) for d in raw_deps] if isinstance(raw_deps, list) else []
    for dep in recorded if effective is None else list(effective):
        path = f"{node_path(target_id, dep)}/Statement.lean"
        raw = _must(reader, path)
        if dep not in states:
            msg = f"dep {dep!r} has no derived status; the graph products do not know it"
            raise ContextError(msg)
        out.append(
            {
                "node_id": dep,
                "status": states[dep].status,
                # F22-T13: the reason beside the status, as graph.json records it; never
                # re-derived here. (A circular route is a label on the dep's own row since
                # D-12 v3.35, F08-T39, not a cause.)
                "cause": states[dep].cause,
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
    named: list[str] = []  # partials a valid record names: one attempt with it (F03-T7)
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
        partial = (doc.get("artifacts") or {}).get("partial_proof")
        if isinstance(partial, str):
            named.append(partial)
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
        "count": recordsmod.count_attempts(len(yaml_names), lean_names, named),
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


def _circular_marks(
    reader: Reader, target_id: str, states: Mapping[str, NodeState]
) -> tuple[dict[str, str], dict[str, tuple[str, ...]], dict[str, list[tuple[str, str]]]]:
    """The gate's own ``graph.circular_marks`` over what ``graph.json`` already says (deps,
    origins, statuses) and each node's merged circularity claims, every ancestor read through
    its revision chain: the same claims the site's ancestor note lists (F08-T20), by the same
    rule, so the two cannot disagree. Returns ``(on_path, below, claims)``.

    The claims come from the document itself where it carries them (``graph/v6``'s ``circular``:
    a node's *own* claims are the entries named under it, F08-T39), and from the tree for an older
    document, under the nodes ``cause: circular`` marked (F08-T22) — a claim spoke only while its
    hole was open, which is what that mark said, so a host reader lists ``defects/`` under those
    nodes alone and never the whole target. Nothing is read from a toolchain, so the service
    derives the same bytes over the host (F10-Q7).
    """
    statuses = {n: s.status for n, s in states.items()}
    deps = {n: tuple(s.deps or ()) for n, s in states.items()}
    holes = {
        n: tuple(d for d in ds if d in states and graphmod.is_hole_of(n, d, states[d].origin or ""))
        for n, ds in deps.items()
    }
    claims: dict[str, list[tuple[str, str]]] = {}
    for hole, state in states.items():
        if state.circular is not None:
            own = [
                (label["claim"][len(hole) + 1 :], label["ancestor"])
                for label in state.circular
                if label["claim"].startswith(f"{hole}/")
            ]
        elif state.cause == graphmod.CAUSE_CIRCULAR:
            found = _circular_claims(reader, target_id, hole)
            own = [(ref, _current_id(reader, target_id, states, a)) for ref, a in found]
        else:
            own = []
        if own:
            claims[hole] = own
    on_path, below = graphmod.circular_marks(holes, deps, claims, statuses)
    return on_path, below, claims


def _circular_below(
    reader: Reader, target_id: str, node_id: str, states: Mapping[str, NodeState]
) -> list[dict[str, str]]:
    """F08-T22 (D-12 v3.23): the merged circularity claims that circle back to this node — each
    hole beneath it shown to imply this statement, with the claim that shows it — so an agent
    reading the bundle sees which routes beneath it were tried (``_circular_marks``)."""
    _on_path, below, _claims = _circular_marks(reader, target_id, states)
    return [
        {"node_id": named.partition("/")[0], "claim": f"{node_path(target_id, named)}"}
        for named in below.get(node_id, ())
    ]


def _circular(
    reader: Reader, target_id: str, node_id: str, states: Mapping[str, NodeState]
) -> list[dict[str, str]]:
    """F10-T19 (D-12 v3.35): the node's ``circular`` label as ``graph/v6`` carries it, repeated
    from the document when it has one; derived as ``graph.NodeFacts.circular`` derives it — the
    node's own claims, then the claim a circular path assigns it — for a document rendered by an
    older pin, so the bundle the service derives through the deploy window is the one the new
    gate writes (2026-09-11)."""
    state = states[node_id]
    if state.circular is not None:
        return [dict(label) for label in state.circular]
    on_path, _below, claims = _circular_marks(reader, target_id, states)
    labels = [
        {"ancestor": ancestor, "claim": f"{node_id}/{ref}"}
        for ref, ancestor in claims.get(node_id, ())
        if ancestor
    ]
    if node_id in on_path:
        named = on_path[node_id]
        hole, _, ref = named.partition("/")
        ancestor = next(a for r, a in claims[hole] if r == ref)
        if all(label["claim"] != named for label in labels):
            labels.append({"ancestor": ancestor, "claim": named})
    return labels


def withdrawn_names(reader: Reader, target_id: str, node_id: str, directory: str) -> frozenset[str]:
    """``records.withdrawn_names`` through a reader (F08-T33): the file names under
    ``<node>/<directory>/`` a merged ``withdrawal/v1`` or ``v2`` record names. The same rule — a
    withdrawal that does not validate is logged and passed over, so the record it names stands;
    no date is compared — so the bundle the service derives over the host reads a withdrawn
    record as absent exactly where the gate's products do (F10-Q7)."""
    withdrawals = f"{node_path(target_id, node_id)}/{recordsmod.WITHDRAWALS_DIR}"
    prefix = f"{directory}/"
    named: set[str] = set()
    for name in sorted(reader.listdir(withdrawals)):
        if not name.endswith(YAML_SUFFIXES):
            continue
        path = f"{withdrawals}/{name}"
        raw = reader.read(path)
        if raw is None:
            continue
        try:
            doc = _yaml(raw, path, None)  # against the version it declares (D-34; F20-R7)
            if doc.get("schema") not in recordsmod.WITHDRAWAL_SCHEMAS:
                msg = f"{path} declares {doc.get('schema')!r}, not a withdrawal"
                raise schemas.SchemaError(msg)
        except (schemas.SchemaError, ContextError) as exc:
            log.warning("%s: a withdrawal that does not validate is passed over: %s", path, exc)
            continue
        withdraws = str(doc["withdraws"])
        if withdraws.startswith(prefix):
            named.add(withdraws[len(prefix) :])
    return frozenset(named)


def defect_claims(
    reader: Reader, target_id: str, node_id: str, *, status: str
) -> list[dict[str, Any]]:
    """F08-T36 (D-16 v3.28): every defect claim filed against the node, oldest first, as
    ``{file, class, state, accepted}`` — ``graph.json``'s row and ``CONTEXT.json`` carry this one
    list, built through a reader so the service derives the same bytes over the host (F10-Q7).

    ``state`` is ``withdrawn`` when a merged withdrawal names the claim (F08-T31), else
    ``standing``: every claim is shown, withdrawn ones too. ``accepted`` is true for the claim
    the node's standing ``disputed`` record names (D-18 v3.28, F08-T35); ``status`` is the node's
    derived status, so a record that F08-T32 has voided accepts nothing. A file that does not
    validate is logged and passed over, as ``records.defect_claims`` passes it over: the gate
    refused it at merge, and one bad file must never decide whether the graph has products."""
    directory = f"{node_path(target_id, node_id)}/{recordsmod.DEFECTS_DIR}"
    names = [n for n in sorted(reader.listdir(directory)) if n.endswith(YAML_SUFFIXES)]
    if not names:
        return []
    accepted_schemas = paths.SCHEMAS_FOR_ROLE["defect-claim"]
    gone = withdrawn_names(reader, target_id, node_id, recordsmod.DEFECTS_DIR)
    accepted = _accepted_claim(reader, target_id, node_id) if status == "disputed" else None
    out: list[dict[str, Any]] = []
    for name in names:
        path = f"{directory}/{name}"
        raw = reader.read(path)
        if raw is None:
            continue
        try:
            doc = _yaml(raw, path, None)
        except (schemas.SchemaError, ContextError) as exc:
            log.warning("%s: a defect claim that does not read is passed over: %s", path, exc)
            continue
        schema_id = str(doc.get("schema"))
        if schema_id not in accepted_schemas or schemas.violations(doc, schema_id):
            log.warning("%s: a defect claim that does not validate is passed over", path)
            continue
        rel = f"{recordsmod.DEFECTS_DIR}/{name}"
        out.append(
            {
                "file": rel,
                "class": str(doc["class"]),
                "state": "withdrawn" if name in gone else "standing",
                "accepted": rel == accepted and name not in gone,
            }
        )
    return out


def _accepted_claim(reader: Reader, target_id: str, node_id: str) -> str | None:
    """The claim the node's standing ``disputed`` record names, as ``defects/<file>``; ``None``
    when the latest standing record is not ``disputed`` or names no claim on this node."""
    record = _latest_status(reader, target_id, node_id)
    if record is None or record.status != "disputed":
        return None
    m = graphmod.CLAIM_REF_RE.match(str(record.doc.get("reference") or ""))
    if m is None:
        return None
    named = (m.group("target"), m.group("node"))
    if named not in ((None, None), (target_id, node_id)):
        return None
    return f"{recordsmod.DEFECTS_DIR}/{m.group('name')}"


def _latest_status(reader: Reader, target_id: str, node_id: str) -> recordsmod.StatusRecord | None:
    """``records.load_node_status`` through a reader: the latest status record not withdrawn."""
    status_dir = f"{node_path(target_id, node_id)}/status"
    gone = withdrawn_names(reader, target_id, node_id, "status")  # F08-T33
    docs = []
    for name in sorted(reader.listdir(status_dir)):
        if not name.endswith(YAML_SUFFIXES) or name in gone:
            continue
        path = f"{status_dir}/{name}"
        docs.append((Path(path), _yaml(_must(reader, path), path, None)))
    return recordsmod.latest_status(docs, recordsmod.NODE_STATUS_SCHEMAS)


def _circular_claims(reader: Reader, target_id: str, hole: str) -> list[tuple[str, str]]:
    """``records.circular_claims`` through a reader: every valid ``circular-decomposition`` claim
    under the node, oldest first, as ``(defects/<file>, ancestor as named)``; a file that does
    not read as one is logged and passed over, as the products pass it over (2026-09-17). A
    claim a curator has withdrawn is absent, as it is to ``records`` (F08-T31, F08-T33)."""
    directory = f"{node_path(target_id, hole)}/{recordsmod.DEFECTS_DIR}"
    accepted = paths.SCHEMAS_FOR_ROLE["defect-claim"]
    gone = withdrawn_names(reader, target_id, hole, recordsmod.DEFECTS_DIR)
    found: list[tuple[str, str]] = []
    for name in sorted(reader.listdir(directory)):
        if not name.endswith(YAML_SUFFIXES) or name in gone:
            continue
        path = f"{directory}/{name}"
        raw = reader.read(path)
        if raw is None:
            continue
        try:
            doc = _yaml(raw, path, None)
        except (schemas.SchemaError, ContextError) as exc:
            log.warning("%s: a defect claim that does not read is passed over: %s", path, exc)
            continue
        if doc.get("class") != recordsmod.CIRCULAR_CLASS:
            continue
        schema_id = str(doc.get("schema"))
        if schema_id not in accepted or schemas.violations(doc, schema_id):
            log.warning("%s: a circularity claim that does not validate is passed over", path)
            continue
        found.append((f"{recordsmod.DEFECTS_DIR}/{name}", str(doc.get("ancestor") or "")))
    return found


def _current_id(
    reader: Reader, target_id: str, states: Mapping[str, NodeState], node_id: str
) -> str:
    """``graph.current_id`` through a reader (F08-T10's chain, F08-T22): the node ``node_id`` has
    become, following each ``superseded`` record's reference while the step is sound. A withdrawn
    status record is absent, as ``records.load_node_status`` reads it (F08-T31, F08-T33)."""

    def successor_of(current: str) -> str | None:
        record = _latest_status(reader, target_id, current)
        if record is None or record.status != "superseded":
            return None
        return str(record.doc.get("reference") or "") or None

    def supersedes_of(current: str) -> str | None:
        raw = reader.read(f"{node_path(target_id, current)}/META.yaml")
        if raw is None:
            return None
        try:
            meta = _yaml(raw, "META.yaml", None)
        except (schemas.SchemaError, ContextError):
            return None
        named = meta.get("supersedes")
        return str(named) if named else None

    return graphmod.follow_revisions(
        node_id,
        successor_of=successor_of,
        is_node=lambda n: n in states,
        supersedes_of=supersedes_of,
    )


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
        "deps": _deps(reader, target_id, meta, states, states[node_id].deps),
        "meta": _meta(reader, node_dir, meta, meta_path),
        "gate_spec": _gate_spec(reader, target_id),
        "claims": _claims(reader, node_id),
        "attempts": _attempts(reader, node_dir),
        "annexes": _annexes(reader, node_dir),
        "explainer_present": _explainer_present(reader, node_dir),
        "untrusted_note": demarcate.UNTRUSTED_NOTE,
        "circular_below": _circular_below(reader, target_id, node_id, states),
        "defect_claims": defect_claims(reader, target_id, node_id, status=state.status),
        # F10-T19 (D-12 v3.35, D-25 v3.35): graph/v6's three fields, repeated.
        "circular": _circular(reader, target_id, node_id, states),
        "literature": state.literature,
        "literature_proposed": state.literature_proposed,
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
