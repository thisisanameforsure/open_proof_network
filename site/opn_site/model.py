"""What the site renders: a graph checkout at a commit plus F03's products (F04-T1; R1, R13).

Everything here is loaded once, validated at the boundary (products against their schemas,
node files by the gate's own layout rules) and handed to the renderer as plain data. A product
that fails validation is a ``SiteError``: the generator writes nothing (R13, C7). No string from
the graph is trusted here — escaping is the renderer's job, and it escapes everything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import layout, records, schemas

#: The product schema versions this generator can render. A consumer parses by version and old
#: snapshots keep rendering (D-34), so this is a set per product, not a pin: `targets-index/v2`
#: and `graph/v2` add F07-R8's two statuses, which the site shows without needing to know them.
PRODUCT_SCHEMAS: dict[str, tuple[str, ...]] = {
    "frontier.json": ("frontier/v1",),
    "info.json": ("info/v1",),
    "targets/index.json": ("targets-index/v1", "targets-index/v2"),
    "graph.json": ("graph/v1", "graph/v2"),
}
KEEP_FILE = ".gitkeep"
_FRONT_MATTER_RE = re.compile(r"\A---\n(?P<head>.*?)\n---\n(?P<body>.*)\Z", re.S)


class SiteError(ValueError):
    """The checkout or its products cannot be rendered faithfully."""


@dataclass(frozen=True)
class Prose:
    """A piece of contributor text with what the record says about its author (R4)."""

    path: str  # relative to the graph root
    text: str
    author: str | None = None
    model: str | None = None
    date: str | None = None


@dataclass(frozen=True)
class NodeView:
    target_id: str
    node_id: str
    graph_entry: dict[str, Any]  # the node's row in graph.json
    statement: str
    statement_path: str
    proof_path: str | None  # present when Proof.lean exists in the checkout
    attestation: dict[str, Any] | None  # the proving attestation, when proved
    attestation_path: str | None
    attempts: records.AttemptSummary
    explainer: Prose | None
    annexes: tuple[Prose, ...]
    acknowledgments: tuple[dict[str, str], ...]
    tutorial: bool

    @property
    def status(self) -> str:
        return str(self.graph_entry["status"])

    @property
    def deps(self) -> list[str]:
        return [str(d) for d in self.graph_entry["deps"]]


@dataclass(frozen=True)
class TargetView:
    target_id: str
    graph: dict[str, Any]
    index_entry: dict[str, Any]
    spec: dict[str, Any]
    nodes: dict[str, NodeView]
    approaches: tuple[str, ...]  # file names under approaches/ (D-14; records are F08's)
    note: str | None  # the D-32 note, when targets/<id>/note.md exists

    @property
    def root(self) -> str:
        return str(self.graph["root"])


@dataclass(frozen=True)
class Site:
    root: Path
    commit: str
    info: dict[str, Any]
    frontier: dict[str, Any]
    index: dict[str, Any]
    targets: dict[str, TargetView] = field(default_factory=dict)

    @property
    def nodes(self) -> list[NodeView]:
        return [n for t in self.targets.values() for n in t.nodes.values()]


def _load_product(root: Path, rel: str, accepted: tuple[str, ...]) -> dict[str, Any]:
    """Load a product and validate it against the version it declares, if that is one we render."""
    path = root / rel
    if not path.is_file():
        msg = f"product {rel} is missing; run `opn-gate products` first (F03)"
        raise SiteError(msg)
    try:
        declared = schemas.load_json(path)
    except schemas.SchemaError as exc:
        msg = f"product {rel} does not validate: {exc}"
        raise SiteError(msg) from exc
    schema_id = str(declared.get("schema"))
    if schema_id not in accepted:
        msg = (
            f"product {rel} is {schema_id}, which this generator does not render; "
            f"it renders {', '.join(accepted)}"
        )
        raise SiteError(msg)
    return declared


def parse_prose(path: Path, root: Path) -> Prose:
    """A text file with optional YAML-style front matter naming author, model and date."""
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    m = _FRONT_MATTER_RE.match(text)
    if m:
        for line in m.group("head").splitlines():
            key, sep, value = line.partition(":")
            if sep and key.strip() in ("author", "model", "date"):
                meta[key.strip()] = value.strip().strip("\"'")
        text = m.group("body")
    return Prose(
        path=path.relative_to(root).as_posix(),
        text=text,
        author=meta.get("author"),
        model=meta.get("model"),
        date=meta.get("date"),
    )


def _prose_files(directory: Path, root: Path) -> tuple[Prose, ...]:
    if not directory.is_dir():
        return ()
    return tuple(
        parse_prose(p, root)
        for p in sorted(directory.iterdir())
        if p.is_file() and p.name != KEEP_FILE
    )


def _attestation_for(
    root: Path, node_id: str, statement_hash: str, proof_commit: str | None
) -> tuple[dict[str, Any] | None, str | None]:
    att_dir = root / "attestations"
    if proof_commit is None or not att_dir.is_dir():
        return None, None
    for path in sorted(p for p in att_dir.iterdir() if p.suffix == ".json"):
        rel = path.relative_to(root).as_posix()
        try:
            doc = schemas.load_json(path)  # by its own schema field: four versions are live
        except schemas.SchemaError as exc:
            msg = f"attestation {rel} does not validate: {exc}"
            raise SiteError(msg) from exc
        if not str(doc["schema"]).startswith("attestation/"):
            msg = f"attestation {rel} declares {doc['schema']!r}, not an attestation schema"
            raise SiteError(msg)
        if (
            doc.get("node_id") == node_id
            and doc.get("statement_hash") == statement_hash
            and doc.get("merge_commit") == proof_commit
        ):
            return doc, path.relative_to(root).as_posix()
    return None, None


def load_node(root: Path, target_id: str, entry: dict[str, Any]) -> NodeView:
    node_id = str(entry["node_id"])
    node_dir = layout.graph_nodes_dir(root, target_id) / node_id
    loaded = layout.load_node(node_dir, target_id)
    if isinstance(loaded, list):
        msg = f"node {node_id}: " + "; ".join(d.message for d in loaded)
        raise SiteError(msg)
    if loaded.statement.statement_hash != entry["statement_hash"]:
        msg = f"node {node_id}: graph.json is stale (statement hash differs from the checkout)"
        raise SiteError(msg)
    proof = node_dir / "Proof.lean"
    attestation, att_path = _attestation_for(
        root, node_id, loaded.statement.statement_hash, entry.get("proof_commit")
    )
    explainers = _prose_files(node_dir / "explainer", root)
    raw_acks = loaded.meta.get("acknowledged_hazards")
    acks = tuple(
        {str(k): str(v) for k, v in a.items()}
        for a in (raw_acks if isinstance(raw_acks, list) else [])
        if isinstance(a, dict)
    )
    return NodeView(
        target_id=target_id,
        node_id=node_id,
        graph_entry=entry,
        statement=loaded.statement.text,
        statement_path=(node_dir / "Statement.lean").relative_to(root).as_posix(),
        proof_path=proof.relative_to(root).as_posix() if proof.is_file() else None,
        attestation=attestation,
        attestation_path=att_path,
        attempts=records.load_attempts(node_dir),
        explainer=explainers[0] if explainers else None,
        annexes=_prose_files(node_dir / "annex", root),
        acknowledgments=acks,
        tutorial=bool(entry.get("tutorial")),
    )


def _check_graph_rows(target_id: str, graph: dict[str, Any]) -> None:
    """What the schema does not say about ``graph.json``: at least one node, ids unique, and
    the root among them. Each is a refusal, since the renderer indexes nodes by id and renders
    the root's statement (R13, C7)."""
    ids = [str(e["node_id"]) for e in graph["nodes"]]
    if not ids:
        msg = f"target {target_id}: graph.json lists no nodes, so there is no root to render"
        raise SiteError(msg)
    seen: set[str] = set()
    for node_id in ids:
        if node_id in seen:
            msg = f"target {target_id}: graph.json lists node {node_id!r} more than once"
            raise SiteError(msg)
        seen.add(node_id)
    root_id = str(graph["root"])
    if root_id not in seen:
        msg = f"target {target_id}: graph.json root {root_id!r} is not one of its nodes"
        raise SiteError(msg)


def load_site(root: Path, commit: str) -> Site:
    """Load a checkout and its products; raise ``SiteError`` on anything unrenderable."""
    root = root.resolve()
    info = _load_product(root, "info.json", PRODUCT_SCHEMAS["info.json"])
    frontier = _load_product(root, "frontier.json", PRODUCT_SCHEMAS["frontier.json"])
    index = _load_product(root, "targets/index.json", PRODUCT_SCHEMAS["targets/index.json"])
    site = Site(root=root, commit=commit, info=info, frontier=frontier, index=index)
    for index_entry in index["targets"]:
        target_id = str(index_entry["target_id"])
        target_dir = root / "targets" / target_id
        graph = _load_product(
            root, f"targets/{target_id}/graph.json", PRODUCT_SCHEMAS["graph.json"]
        )
        spec = schemas.load_json(layout.gate_spec_path(root, target_id), "gate-spec/v1")
        _check_graph_rows(target_id, graph)
        nodes = {str(e["node_id"]): load_node(root, target_id, e) for e in graph["nodes"]}
        approaches_dir = target_dir / "approaches"
        approaches = (
            tuple(
                p.name
                for p in sorted(approaches_dir.iterdir())
                if approaches_dir.is_dir() and p.is_file() and p.name != KEEP_FILE
            )
            if approaches_dir.is_dir()
            else ()
        )
        note_path = target_dir / "note.md"
        site.targets[target_id] = TargetView(
            target_id=target_id,
            graph=graph,
            index_entry=index_entry,
            spec=spec,
            nodes=nodes,
            approaches=approaches,
            note=note_path.read_text(encoding="utf-8") if note_path.is_file() else None,
        )
    return site
