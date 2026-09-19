"""What the site renders: a graph checkout at a commit plus F03's products (F04-T1; R1, R13).

Everything here is loaded once, validated at the boundary (products against their schemas,
node files by the gate's own layout rules) and handed to the renderer as plain data. A product
that fails validation is a ``SiteError``: the generator writes nothing (R13, C7). No string from
the graph is trusted here — escaping is the renderer's job, and it escapes everything.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from opn_gate import evidence, explainers, intake, layout, paths, records, schemas, signed, watch
from opn_gate import graph as graphmod
from opn_gate import writeup as writeupmod

#: The product schema versions this generator can render. A consumer parses by version and old
#: snapshots keep rendering (D-34), so this is a set per product, not a pin: `targets-index/v2`
#: and `graph/v2` add F07-R8's two statuses, which the site shows without needing to know them.
PRODUCT_SCHEMAS: dict[str, tuple[str, ...]] = {
    "frontier.json": ("frontier/v1", "frontier/v2", "frontier/v3"),
    "info.json": ("info/v1",),
    "targets/index.json": (
        "targets-index/v1",
        "targets-index/v2",
        "targets-index/v3",
        "targets-index/v4",
        "targets-index/v5",  # F14: evidence, step 9 basis, formalizations
        "targets-index/v6",  # F15: policy, stewards, digestion, calibration
    ),
    "graph.json": ("graph/v1", "graph/v2", "graph/v3"),
}
log = logging.getLogger(__name__)
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
class LeanFile:
    """One Lean artifact from the checkout, shown on the site rather than only linked (R14).

    ``attested_hash`` is the ``artifact_hash`` of the attestation naming this file, when one
    does. Only ``Proof.lean`` has one: nothing in the protocol hashes a witness or a partial, so
    those carry ``None`` and the page says what *was* checked instead of claiming a match.
    """

    path: str  # relative to the graph root
    text: str
    content_hash: str  # sha256 of the bytes in the checkout
    attested_hash: str | None = None

    @property
    def verified(self) -> bool:
        """The bytes on the page are the bytes the gate attested."""
        return self.attested_hash is not None and self.attested_hash == self.content_hash

    @property
    def mismatched(self) -> bool:
        """An attestation names a hash for this file and the checkout's bytes are not it.

        Told apart from "no hash anywhere", because they are different facts: a witness has no
        hash by design, while a proof whose hash disagrees is a defect. The renderer withholds
        the text in this case and says why — one node's defect must not decide whether the
        whole graph has a site (the rule the products learned on 2026-09-17).
        """
        return self.attested_hash is not None and self.attested_hash != self.content_hash


@dataclass(frozen=True)
class PartialView:
    """One ``attempts/*.lean`` partial assembly (D-3, D-12 #5) and the postmortem naming it.

    A partial is contributor text no attestation covers, so it renders untrusted (R4). The
    record is optional: the live graph carries partials that no ``postmortem/v1`` file names,
    and ``records.count_attempts`` already counts those as attempts in their own right.
    """

    file: LeanFile
    contributor: str | None = None
    route: str | None = None
    route_class: str | None = None
    outcome: str | None = None
    failure_class: str | None = None
    record_path: str | None = None


@dataclass(frozen=True)
class AlternateView:
    """One alternate proof (D-25 v3.13): its file, and what its attestation records."""

    path: str
    merge_commit: str | None  # None only when no attestation names the file's hash
    submitter: str | None


@dataclass(frozen=True)
class SignatureView:
    """One valid explainer signature (F15-R8): who vouched, when, for which explainer."""

    signer: str
    date: str
    explainer: str
    path: str


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
    #: D-25 v3.13: later proofs of this node, in the order their files are stamped.
    alternates: tuple[AlternateView, ...] = ()
    #: F15-R10: the valid signatures on the node's explainers — verified at render, since only
    #: a valid one is a comprehension claim (D-3 v3.17).
    signatures: tuple[SignatureView, ...] = ()
    #: F04-T15 (R14): the mathematics itself, so the site shows it rather than sending a reader
    #: to the record host. The proof is present only when its bytes are the attested ones; the
    #: witness is whatever the gate checked at step 7, open when its slot is unfilled.
    proof: LeanFile | None = None
    witness: LeanFile | None = None
    witness_open: bool = False
    partials: tuple[PartialView, ...] = ()
    #: F04-T18 (Q20): both ends of a D-8 revision, read from where the curator's command wrote
    #: them — the old node's ``superseded`` status record (``reference`` names the successor,
    #: ``cause`` is the curator's sentence naming the request and its defect class) and the
    #: successor's ``META.yaml``. The page had said one word, "superseded".
    superseded_by: str | None = None
    superseded_cause: str | None = None
    superseded_record: str | None = None
    supersedes: str | None = None

    @property
    def status(self) -> str:
        return str(self.graph_entry["status"])

    @property
    def deps(self) -> list[str]:
        return [str(d) for d in self.graph_entry["deps"]]

    @property
    def cause(self) -> str | None:
        """Why a blocked node is blocked (``graph/v2`` on; absent before, read as ``None``)."""
        cause = self.graph_entry.get("cause")
        return None if cause is None else str(cause)


@dataclass(frozen=True)
class TargetView:
    target_id: str
    graph: dict[str, Any]
    index_entry: dict[str, Any]
    spec: dict[str, Any]
    nodes: dict[str, NodeView]
    approaches: tuple[str, ...]  # file names under approaches/ (D-14; records are F08's)
    note: str | None  # the D-32 note, when targets/<id>/note.md exists
    record: dict[str, Any] | None = None  # targets/<id>/target.yaml (F11-R1), when curated
    drift: tuple[watch.DriftRecord, ...] = ()  # targets/<id>/drift/*.yaml (F12-R11, R12)
    #: F14-R10: the root's newest statement-evidence record, for the reasons behind its score.
    evidence: dict[str, Any] | None = None
    #: F15-R10: the valid write-up records — a paper or a note, with where it lives (R6).
    writeups: tuple[dict[str, Any], ...] = ()

    @property
    def root(self) -> str:
        return str(self.graph["root"])

    @property
    def stewards(self) -> list[dict[str, Any]]:
        """The active stewards the index publishes (``targets-index/v6``); none before it."""
        raw = self.index_entry.get("stewards")
        return [dict(s) for s in raw] if isinstance(raw, list) else []

    @property
    def digestion(self) -> dict[str, Any] | None:
        """The digestion state and its counts (v6), or ``None`` on an older index."""
        raw = self.index_entry.get("digestion")
        return dict(raw) if isinstance(raw, dict) else None

    @property
    def calibration(self) -> bool:
        return bool(self.index_entry.get("calibration", False))


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


def _load_record(target_dir: Path) -> dict[str, Any] | None:
    """The curator's ``target.yaml`` (F11-R1), or ``None`` for a target that predates F11.

    A malformed one is a ``SiteError`` like any other invalid graph file: the Targets page says
    why a target is not claimable and under whose licence its source is quoted, and rendering
    that from a record nobody validated is how a page states something the graph does not.
    """
    try:
        return intake.load_doc(target_dir)
    except schemas.SchemaError as exc:
        msg = f"targets/{target_dir.name}/{intake.TARGET_FILE} does not validate: {exc}"
        raise SiteError(msg) from exc


def _load_drift(target_dir: Path) -> tuple[watch.DriftRecord, ...]:
    """The watcher's records (F12-R11, R12), for the diff excerpt and the citation the target
    page shows escaped (R14); a malformed one is a ``SiteError`` like any invalid graph file."""
    try:
        return tuple(watch.load_drift(target_dir))
    except schemas.SchemaError as exc:
        msg = f"targets/{target_dir.name}/drift does not validate: {exc}"
        raise SiteError(msg) from exc


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


def _alternates_for(
    root: Path, node_dir: Path, node_id: str, statement_hash: str
) -> tuple[AlternateView, ...]:
    """R7, R15: each ``attempts/*-alternate.lean`` with the merged attestation whose
    ``artifact_hash`` is that file's — how an alternate is told from the node's own proof."""
    attempts = node_dir / "attempts"
    if not attempts.is_dir():
        return ()
    files = sorted(p for p in attempts.glob(f"*{paths.ALTERNATE_SUFFIX}") if p.is_file())
    if not files:
        return ()
    by_hash: dict[str, dict[str, Any]] = {}
    att_dir = root / "attestations"
    for path in (
        sorted(p for p in att_dir.iterdir() if p.suffix == ".json") if att_dir.is_dir() else ()
    ):
        try:
            doc = schemas.load_json(path)
        except schemas.SchemaError as exc:
            msg = f"attestation {path.relative_to(root).as_posix()} does not validate: {exc}"
            raise SiteError(msg) from exc
        digest = doc.get("artifact_hash")
        if (
            isinstance(digest, str)
            and doc.get("node_id") == node_id
            and doc.get("statement_hash") == statement_hash
            and doc.get("merge_commit")
        ):
            by_hash.setdefault(digest, doc)
    views: list[AlternateView] = []
    for f in files:
        found = by_hash.get(schemas.content_hash(f.read_bytes()))
        views.append(
            AlternateView(
                path=f.relative_to(root).as_posix(),
                merge_commit=str(found["merge_commit"]) if found else None,
                submitter=str(found["submitter"]) if found and found.get("submitter") else None,
            )
        )
    return tuple(views)


def _lean_file(root: Path, path: Path, *, attested_hash: str | None = None) -> LeanFile | None:
    """A Lean artifact's text and the hash of its bytes, or ``None`` when it is not here.

    A file that is not UTF-8 is a ``SiteError`` like any other unrenderable graph file: the page
    would otherwise show replacement characters where the mathematics is (R13, C7).
    """
    if not path.is_file():
        return None
    rel = path.relative_to(root).as_posix()
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        msg = f"{rel} is not valid UTF-8, so its text cannot be rendered: {exc}"
        raise SiteError(msg) from exc
    return LeanFile(
        path=rel, text=text, content_hash=schemas.content_hash(data), attested_hash=attested_hash
    )


def _partials_for(root: Path, node_dir: Path) -> tuple[PartialView, ...]:
    """Every partial assembly under ``attempts/``, with the record naming it when one does.

    An alternate is a proof, not an attempt (D-25 v3.13), and has its own view. A postmortem
    that does not validate is skipped rather than refused: ``records.load_attempts`` already
    counts it as invalid and the page says so, and one contributor's malformed yaml must not
    take down every page on the site.
    """
    attempts = node_dir / "attempts"
    if not attempts.is_dir():
        return ()
    named: dict[str, tuple[dict[str, Any], str]] = {}
    for path in sorted(p for p in attempts.iterdir() if p.suffix in records.ATTEMPT_SUFFIXES):
        try:
            doc = schemas.load_yaml(path, records.POSTMORTEM_SCHEMA)
        except schemas.SchemaError:
            continue
        partial = (doc.get("artifacts") or {}).get("partial_proof")
        if isinstance(partial, str):
            named[PurePosixPath(partial).name] = (doc, path.relative_to(root).as_posix())
    views: list[PartialView] = []
    for path in sorted(attempts.glob("*.lean")):
        if path.name.endswith(paths.ALTERNATE_SUFFIX):
            continue
        lean = _lean_file(root, path)
        if lean is None:  # pragma: no cover — glob yields only files
            continue
        doc, record_path = named.get(path.name, ({}, ""))

        def field(key: str, doc: dict[str, Any] = doc) -> str | None:
            value = doc.get(key)
            return str(value) if value else None

        views.append(
            PartialView(
                file=lean,
                contributor=field("contributor"),
                route=field("route"),
                route_class=field("route_class"),
                outcome=field("outcome"),
                failure_class=field("failure_class"),
                record_path=record_path or None,
            )
        )
    return tuple(views)


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
    # R14: the proof is shown, not just linked, so the bytes on the page must be the bytes the
    # gate attested. A difference is carried, not raised: the renderer withholds that one
    # proof's text and says why, and every other page still renders (Q17, Mike 2026-09-18).
    raw_hash = attestation.get("artifact_hash") if attestation else None
    attested = str(raw_hash) if raw_hash else None
    proof_file = _lean_file(root, proof, attested_hash=attested)
    if proof_file is not None and proof_file.mismatched:
        log.warning(
            "%s: Proof.lean is not the file attestation %s covers (attested %s, found %s); "
            "its text is withheld from the page",
            node_id,
            att_path,
            attested,
            proof_file.content_hash,
        )
    explainer_files = _prose_files(node_dir / "explainer", root)
    override = records.load_node_status(node_dir)
    replaced = override if override is not None and override.status == "superseded" else None
    successor = replaced.doc.get("reference") if replaced is not None else None
    why = replaced.doc.get("cause") if replaced is not None else None
    predecessor = loaded.meta.get("supersedes")
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
        explainer=explainer_files[0] if explainer_files else None,
        annexes=_prose_files(node_dir / "annex", root),
        acknowledgments=acks,
        tutorial=bool(entry.get("tutorial")),
        alternates=_alternates_for(root, node_dir, node_id, loaded.statement.statement_hash),
        signatures=_signatures_for(root, node_dir),
        proof=proof_file,
        witness=_lean_file(root, node_dir / paths.WITNESS_FILE),
        witness_open=graphmod.witness_is_stub(node_dir),
        partials=_partials_for(root, node_dir),
        superseded_by=str(successor) if successor else None,
        superseded_cause=str(why) if why else None,
        superseded_record=replaced.path.relative_to(root).as_posix() if replaced else None,
        supersedes=str(predecessor) if predecessor else None,
    )


def _signatures_for(root: Path, node_dir: Path) -> tuple[SignatureView, ...]:
    """F15-R10: the node's valid explainer signatures, verified through the gate's own seam
    (ssh-keygen, which the site build has where the gate has it). A signature file that does not
    read is a ``SiteError`` like any other invalid graph file."""
    try:
        valid = explainers.valid(node_dir, signed.default_signer())
    except schemas.SchemaError as exc:
        msg = f"{node_dir.name}: an explainer signature does not validate: {exc}"
        raise SiteError(msg) from exc
    return tuple(
        SignatureView(
            signer=sig.signer,
            date=sig.date,
            explainer=sig.explainer,
            path=sig.path.relative_to(root).as_posix(),
        )
        for sig in valid
    )


def _writeups_for(target_dir: Path) -> tuple[dict[str, Any], ...]:
    """F15-R10: the target's valid write-up records (R6), verified through the gate's seam."""
    try:
        valid = writeupmod.valid(target_dir, signed.default_signer())
    except schemas.SchemaError as exc:
        msg = f"targets/{target_dir.name}: a write-up record does not validate: {exc}"
        raise SiteError(msg) from exc
    return tuple(record.as_dict() for record in valid)


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


def _load_evidence(target_dir: Path) -> dict[str, Any] | None:
    """F14-R10: the root's newest statement-evidence record, whose reasons the index does not
    carry. A record that does not read is unrenderable, like any other graph defect (R13)."""
    try:
        record = evidence.newest(target_dir)
    except (ValueError, OSError) as exc:  # SchemaError, EvidenceError
        msg = f"target {target_dir.name}: an evidence record does not read: {exc}"
        raise SiteError(msg) from exc
    return record.doc if record is not None else None


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
            record=_load_record(target_dir),
            drift=_load_drift(target_dir),
            evidence=_load_evidence(target_dir),
            writeups=_writeups_for(target_dir),
        )
    return site
