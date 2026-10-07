"""What the site renders: a graph checkout at a commit plus F03's products (F04-T1; R1, R13).

Everything here is loaded once, validated at the boundary (products against their schemas,
node files by the gate's own layout rules) and handed to the renderer as plain data. A product
that fails validation is a ``SiteError``: the generator writes nothing (R13, C7). No string from
the graph is trusted here — escaping is the renderer's job, and it escapes everything.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from opn_gate import (
    evidence,
    explainers,
    glosses,
    intake,
    layout,
    paths,
    records,
    schemas,
    sections,
    signed,
    watch,
)
from opn_gate import graph as graphmod
from opn_gate import writeup as writeupmod

#: The product schema versions this generator can render. A consumer parses by version and old
#: snapshots keep rendering (D-34), so this is a set per product, not a pin: `targets-index/v2`
#: and `graph/v2` add F07-R8's two statuses, which the site shows without needing to know them.
PRODUCT_SCHEMAS: dict[str, tuple[str, ...]] = {
    "frontier.json": ("frontier/v1", "frontier/v2", "frontier/v3", "frontier/v4"),  # v4: F03-T16
    "info.json": ("info/v1", "info/v2"),  # v2: F05-T25
    "targets/index.json": (
        "targets-index/v1",
        "targets-index/v2",
        "targets-index/v3",
        "targets-index/v4",
        "targets-index/v5",  # F14: evidence, step 9 basis, formalizations
        "targets-index/v6",  # F15: policy, stewards, digestion, calibration
        "targets-index/v7",  # F07-T24: step9 may be `calibration`
    ),
    "graph.json": ("graph/v1", "graph/v2", "graph/v3", "graph/v4", "graph/v5"),  # v5: F08-T36
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
    licence: str | None = None  # F18-R10: annex/v1 records one


#: F18-T3 (R10): the front-matter keys each field is read from. Explainers write ``author`` and
#: ``model``; ``annex/v1`` writes ``contributor`` and ``model_and_tooling`` (and a licence), and
#: until 2026-10-03 every annex on the site read "author not recorded".
PROSE_KEYS: dict[str, tuple[str, ...]] = {
    "author": ("author", "contributor"),
    "model": ("model", "model_and_tooling"),
    "date": ("date",),
    "licence": ("licence",),
}
#: YAML's spellings of nothing: ``model_and_tooling: null`` is no model, not one called "null".
_YAML_NULLS = frozenset({"", "null", "~", "Null", "NULL"})


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
    #: F19-T8: the file's text and hash, for its outline's Lean lines on the reading view.
    file: LeanFile | None = None


@dataclass(frozen=True)
class SignatureView:
    """One valid explainer signature (F15-R8): who vouched, when, for which explainer."""

    signer: str
    date: str
    explainer: str
    path: str


@dataclass(frozen=True)
class WordsSection:
    """F21-R11: one section of a gloss or explainer version as the site prints it — its key (the
    gate's, from ``opn_gate.sections``), its heading and the outline steps it names (an explainer's
    level-2 section; ``None`` and none for a gloss or an unanchored explainer), its words, and the
    gate's normalised text of the section, which is what a pending edit is diffed against."""

    key: str
    heading: str | None
    steps: tuple[str, ...]
    text: str
    canonical: str


@dataclass(frozen=True)
class VersionView:
    """F20-R9, R13, R14: one version of a gloss or explainer chain, as ``glosses.json`` lists it,
    with its prose read from the tree and its signatures re-verified at render (F15's seam): only
    a valid signature is a claim, so the site never takes the product's word for one."""

    hash: str
    path: str  # relative to the graph root
    schema: str | None  # gloss/v1, explainer/v1, or None for an explainer filed before F20
    supersedes: str | None
    author: str | None
    drafter: dict[str, Any] | None
    date: str | None
    withdrawn: bool
    #: A gloss's: whether it describes its file as the checkout holds it (F20-R3); None for an
    #: explainer.
    describes_current: bool | None
    signers: tuple[tuple[str, str, str], ...]  # (signer, date, file), valid signatures only
    body: str  # the prose after the front matter
    #: An ``explainer/v1``'s sections, each with the outline steps it names (F20-Q2).
    sections: tuple[explainers.Section, ...] = ()
    #: F21-R6: the model and tooling a contributor says drafted this version (``gloss/v2``,
    #: ``explainer/v2``); contributor text, escaped and demarcated wherever shown (C9).
    drafted_with: str | None = None
    #: F21-R13: each valid signature's signer and the section keys it approves (``None``: every
    #: section of the version, a v1 signature), re-verified at render like ``signers``.
    approvals: tuple[tuple[str, frozenset[str] | None], ...] = ()
    #: F21-R11: the version's sections, keyed as the gate keys them.
    parts: tuple[WordsSection, ...] = ()

    def part(self, key: str) -> WordsSection | None:
        return next((p for p in self.parts if p.key == key), None)

    def verified_by(self, key: str) -> list[str]:
        """The signers whose valid signature approves this version's section ``key``."""
        found = [s for s, keys in self.approvals if keys is None or key in keys]
        return list(dict.fromkeys(found))

    @property
    def model(self) -> str | None:
        """The model a draft names (D-23), or ``None`` for a person's version."""
        return str(self.drafter["model"]) if self.drafter and self.drafter.get("model") else None


@dataclass(frozen=True)
class Placed:
    """F21-R14: one section a chain shows, or one awaiting review — its key, the version its words
    come from, and its state (drafted, written, verified; pending for one awaiting review)."""

    key: str
    version: str
    state: str


@dataclass(frozen=True)
class ChainView:
    versions: tuple[VersionView, ...]
    current: str | None  # the latest version not withdrawn (D-3 v3.30), or None
    #: F21-R14 (``glosses/v2``): the chain is read section by section — ``shown`` is what it
    #: shows, ``pending`` what awaits review. False for a ``glosses/v1`` product, which the site
    #: renders as whole versions, as before.
    sectioned: bool = False
    shown: tuple[Placed, ...] = ()
    pending: tuple[Placed, ...] = ()

    @property
    def current_version(self) -> VersionView | None:
        return next((v for v in self.versions if v.hash == self.current), None)

    def version(self, digest: str) -> VersionView | None:
        return next((v for v in self.versions if v.hash == digest), None)

    def shown_version(self, key: str) -> VersionView | None:
        """The version whose words the chain shows for section ``key`` (``glosses/v2``)."""
        placed = next((p for p in self.shown if p.key == key), None)
        return self.version(placed.version) if placed is not None else None

    def words(self) -> VersionView | None:
        """The version a gloss chain shows: under ``glosses/v2`` the one its ``whole`` section
        comes from — never an edit awaiting review (F21-R11) — and under v1 the current one."""
        return self.shown_version(sections.WHOLE) if self.sectioned else self.current_version


@dataclass(frozen=True)
class SubjectView:
    """One Lean file or merged proof artifact with the chains filed on it (``glosses/v1`` or
    ``glosses/v2``)."""

    kind: str  # statement, witness, relation, definition; proof, alternate, partial, absent
    record: str  # gloss or explainer
    node: str | None
    module: str | None
    file: str | None  # relative to the target directory
    lean_hash: str | None
    chains: tuple[ChainView, ...]

    def describing(self) -> list[VersionView]:
        """R13: each chain's current version that describes the file as it stands, in record
        order (F20-Q4) — what the site prints beside the Lean."""
        found = [c.words() for c in self.chains]
        return [v for v in found if v is not None and v.describes_current is not False]


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
    #: F08-T17: the merged circularity claim (graph-root relative) that ``graph.json``'s cause
    #: ``circular`` rests on, read by the gate's own reader so the two cannot name different files.
    circular_claim: str | None = None
    #: F08-T20 (D-12 v3.22): the merged circularity claims whose ancestor is this node
    #: (graph-root relative). The node stays open; its page names them.
    circular_below: tuple[str, ...] = ()
    #: F20-T8 (R13): a variant's ``Relation.lean``, shown with its gloss.
    relation: LeanFile | None = None

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

    @property
    def open_claims(self) -> list[dict[str, Any]]:
        """F08-T36 (D-16 v3.28): the defect claims against the node that stand, oldest first, as
        ``graph/v5`` lists them; none on an older graph, which did not list them."""
        raw = self.graph_entry.get("defect_claims")
        if not isinstance(raw, list):
            return []
        return [dict(c) for c in raw if isinstance(c, dict) and c.get("state") == "standing"]


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
    #: F19-R1, T7: the target's ``outline/v1`` products, keyed by the artifact hash they outline.
    outlines: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: F20-T8 (R13, R14): every subject ``glosses.json`` lists, in its order; empty when the
    #: products predate F20 (every slot then shows the cue).
    subjects: tuple[SubjectView, ...] = ()
    #: F20-T8 (R13): each definition module under ``defs/``, shown with its gloss.
    definitions: tuple[LeanFile, ...] = ()
    #: F21-T7 (R9): the subjects that lack words, by ``glosses.needed`` over the committed
    #: ``glosses.json`` and ``target.yaml`` (the rows ``list_words_needed`` serves); ``None``
    #: when the product is absent or unreadable, so the page claims no count it cannot know.
    words_needed: tuple[dict[str, Any], ...] | None = None
    #: F23-R14: login -> how its steward was admitted (``_steward_admissions``).
    admissions: dict[str, str] = field(default_factory=dict)

    @property
    def root(self) -> str:
        return str(self.graph["root"])

    def gloss_subject(
        self, kind: str, *, node: str | None = None, module: str | None = None
    ) -> SubjectView | None:
        """The gloss subject of one file: a node's statement, witness or relation, or a module."""
        return next(
            (
                s
                for s in self.subjects
                if s.record == "gloss" and s.kind == kind and s.node == node and s.module == module
            ),
            None,
        )

    def explainer_subjects(self, node: str) -> list[SubjectView]:
        """The node's merged proof artifacts that carry an explainer chain, in product order."""
        return [s for s in self.subjects if s.record == "explainer" and s.node == node and s.chains]

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

    @property
    def steward_rule_enforced(self) -> bool:
        """F15-R3, F04-T27: whether the graph's ``policy.json`` enforces the steward rule, as the
        index publishes it; ``False`` when the index predates the policy block (not enforced)."""
        policy = self.index.get("policy") or {}
        rule = policy.get("steward_rule") or {} if isinstance(policy, dict) else {}
        return bool(rule.get("enforced", False)) if isinstance(rule, dict) else False


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


#: F21-T7: the ``glosses.json`` versions ``glosses.needed`` reads (the live graph holds v1 until
#: its re-pin).
WORDS_GLOSSES_SCHEMAS = frozenset({"glosses/v1", "glosses/v2"})


def _load_words_needed(target_dir: Path, root: str) -> tuple[dict[str, Any], ...] | None:
    """F21-R9: the target's subjects without words, computed as the MCP's
    ``list_words_needed`` computes them (F21-Q6): ``glosses.needed`` over the committed
    product and the curated words of ``target.yaml``. A product that is absent, of another
    version or invalid is warned about and gives ``None``: no count rather than a false zero."""
    path = target_dir / GLOSSES_FILE
    if not path.is_file():
        return None
    try:
        doc = schemas.load_json(path)
        if doc.get("schema") not in WORDS_GLOSSES_SCHEMAS or doc.get("target") != target_dir.name:
            log.warning("%s: no words count from %s", path, doc.get("schema"))
            return None
        schemas.validate(doc, str(doc["schema"]))
    except schemas.SchemaError as exc:
        log.warning("%s: no words count, it does not validate: %s", path, exc)
        return None
    curated = glosses.curated_words(_load_record(target_dir))
    return tuple(glosses.needed(doc, root=root, curated=curated))


def _load_drift(target_dir: Path) -> tuple[watch.DriftRecord, ...]:
    """The watcher's records (F12-R11, R12), for the diff excerpt and the citation the target
    page shows escaped (R14); a malformed one is a ``SiteError`` like any invalid graph file."""
    try:
        return tuple(watch.load_drift(target_dir))
    except schemas.SchemaError as exc:
        msg = f"targets/{target_dir.name}/drift does not validate: {exc}"
        raise SiteError(msg) from exc


def parse_prose(path: Path, root: Path) -> Prose:
    """A text file with optional YAML-style front matter naming author, model, date and licence
    (``PROSE_KEYS``: an explainer's names and an annex's)."""
    text = path.read_text(encoding="utf-8")
    raw: dict[str, str] = {}
    m = _FRONT_MATTER_RE.match(text)
    if m:
        for line in m.group("head").splitlines():
            key, sep, value = line.partition(":")
            if sep:
                raw[key.strip()] = value.strip().strip("\"'")
        text = m.group("body")
    meta = {
        field: next((raw[k] for k in keys if raw.get(k, "") not in _YAML_NULLS), None)
        for field, keys in PROSE_KEYS.items()
    }
    return Prose(
        path=path.relative_to(root).as_posix(),
        text=text,
        author=meta["author"],
        model=meta["model"],
        date=meta["date"],
        licence=meta["licence"],
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
        digest = schemas.content_hash(f.read_bytes())
        found = by_hash.get(digest)
        views.append(
            AlternateView(
                path=f.relative_to(root).as_posix(),
                merge_commit=str(found["merge_commit"]) if found else None,
                submitter=str(found["submitter"]) if found and found.get("submitter") else None,
                file=_lean_file(root, f, attested_hash=digest if found else None),
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
        relation=_lean_file(root, node_dir / paths.RELATION_FILE),
        partials=_partials_for(root, node_dir),
        superseded_by=str(successor) if successor else None,
        superseded_cause=str(why) if why else None,
        superseded_record=replaced.path.relative_to(root).as_posix() if replaced else None,
        supersedes=str(predecessor) if predecessor else None,
        circular_claim=(
            (node_dir / claim).relative_to(root).as_posix()
            if (claim := records.circular_claim(node_dir))
            else None
        ),
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


#: F23-R14: what a v1 steward record says of how its steward came in — a curator merged it, and
#: the record does not say which.
ADMITTED_BY_CURATOR = "curator"
_STEWARD_FILE_RE = re.compile(r"^(?P<n>[1-9][0-9]*)\.ya?ml$")


def _steward_admissions(target_dir: Path) -> dict[str, str]:
    """F23-R14 (D-32 v3.33): for each login, how the commit it is active under was admitted —
    ``self``, a curator's login, or ``curator`` for a ``steward/v1`` record — read from the
    latest ``commit`` record with that login. Who is *active* is the index's (the gate's rule,
    signatures checked); this only labels them, so an unreadable record is skipped, never
    raised on, and a login with no record found gets no label."""
    directory = target_dir / "stewards"
    if not directory.is_dir():
        return {}
    numbered = []
    for p in directory.iterdir():
        m = _STEWARD_FILE_RE.match(p.name)
        if m and p.is_file():
            numbered.append((int(m.group("n")), p))
    found: dict[str, str] = {}
    for _n, path in sorted(numbered):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(doc, dict) or doc.get("action") != "commit":
            continue
        login = str(doc.get("login") or "")
        if doc.get("schema") == "steward/v2":
            admitted = str(doc.get("admitted_by") or "")
            if admitted:
                found[login] = admitted
        elif doc.get("schema") == "steward/v1":
            found[login] = ADMITTED_BY_CURATOR
    return found


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


#: F19-R1: where a target's outlines live, and the one schema version this generator renders.
OUTLINES_DIR = "outlines"
OUTLINE_SCHEMA = "outline/v1"


def _load_outlines(target_dir: Path) -> dict[str, dict[str, Any]]:
    """F19-T7: the target's ``outline/v1`` products, keyed by the artifact hash each outlines.

    An outline is a display aid over a proof the page already shows, so one that does not read —
    malformed, another version, filed under a name that is not its artifact's hash, or naming
    another target — is skipped with a warning naming the file, and the page shows the proof as
    it did before outlines existed (C7; the 2026-09-17 rule that one product's defect does not
    decide whether the graph has a site). Which bytes an outline may stand beside is the
    renderer's check: it shows one only over the very artifact it names.
    """
    directory = target_dir / OUTLINES_DIR
    if not directory.is_dir():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(p for p in directory.iterdir() if p.suffix == ".json"):
        try:
            doc = schemas.load_json(path)
        except schemas.SchemaError as exc:
            log.warning("outline %s skipped: it does not validate: %s", path.name, exc)
            continue
        problem = (
            f"it is {doc.get('schema')}, and this generator renders {OUTLINE_SCHEMA}"
            if doc.get("schema") != OUTLINE_SCHEMA
            else "its file name is not its artifact's hash"
            if doc["artifact"]["hash"] != path.stem
            else f"it names target {doc['target']}"
            if doc["target"] != target_dir.name
            else None
        )
        if problem is not None:
            log.warning("outline %s skipped: %s", path.name, problem)
            continue
        out[path.stem] = dict(doc)
    return out


#: F20-R9: the gloss and explainer chains per subject, and the versions this generator renders:
#: v1 as whole versions (the live graph until its re-pin), v2 section by section (F21-R14).
GLOSSES_FILE = "glosses.json"
GLOSSES_SCHEMAS: tuple[str, ...] = ("glosses/v1", "glosses/v2")
#: A signer, the signature's date, its file, and the section keys it approves (None: all).
_Sig = tuple[str, str, str, frozenset[str] | None]


def _load_glosses(target_dir: Path) -> tuple[SubjectView, ...]:
    """F20-T8: the target's ``glosses.json``, each version's prose read from the tree and each
    signature verified at render through the gate's own seam (as F15's explainer signatures are).

    The product is new with F20, so a graph rendered by an older gate has none: that is said in
    a warning and every slot shows its cue. One that does not read is skipped the same way — a
    display aid's defect never decides whether the graph has a site (C7; the 2026-09-17 rule).
    Whether a gloss describes its file is re-derived from the checkout, so the page states what
    the tree holds even when the products lag it."""
    path = target_dir / GLOSSES_FILE
    if not path.is_file():
        log.warning("%s has no %s; every gloss slot shows its cue", target_dir.name, GLOSSES_FILE)
        return ()
    try:
        doc = schemas.load_json(path)
    except schemas.SchemaError as exc:
        log.warning("%s skipped: it does not validate: %s", path, exc)
        return ()
    if doc.get("schema") not in GLOSSES_SCHEMAS or doc.get("target") != target_dir.name:
        log.warning("%s skipped: it is %s for %s", path, doc.get("schema"), doc.get("target"))
        return ()
    signer = signed.default_signer()
    gloss_sigs: dict[str, list[_Sig]] = {}
    explainer_sigs: dict[str, list[_Sig]] = {}
    root = target_dir.parents[1]
    parents = {target_dir, *(p for p in (target_dir / "nodes").glob("*") if p.is_dir())}
    try:
        for parent in sorted(parents):
            for digest, found in glosses.valid_signatures(parent, signer).items():
                gloss_sigs.setdefault(digest, []).extend(
                    (s.signer, s.date, s.path.relative_to(root).as_posix(), _keys(s.sections))
                    for s in found
                )
            if parent != target_dir:
                for sig in explainers.valid(parent, signer):
                    explainer_sigs.setdefault(sig.explainer, []).append(
                        (
                            sig.signer,
                            sig.date,
                            sig.path.relative_to(root).as_posix(),
                            _keys(sig.sections),
                        )
                    )
    except schemas.SchemaError as exc:
        msg = f"targets/{target_dir.name}: a gloss or explainer signature does not validate: {exc}"
        raise SiteError(msg) from exc
    out: list[SubjectView] = []
    for s in doc["subjects"]:
        file = target_dir / s["file"] if s.get("file") else None
        now = (
            schemas.content_hash(file.read_bytes()) if file is not None and file.is_file() else None
        )
        sigs = gloss_sigs if s["record"] == "gloss" else explainer_sigs
        sectioned = doc["schema"] != "glosses/v1"
        chains = tuple(
            ChainView(
                versions=tuple(
                    _version(target_dir, v, now=now, record=s["record"], sigs=sigs)
                    for v in c["versions"]
                ),
                current=c["current"],
                sectioned=sectioned,
                shown=tuple(_placed(p) for p in c.get("shown", ())),
                pending=tuple(_placed(p) for p in c.get("pending", ())),
            )
            for c in s["chains"]
        )
        out.append(
            SubjectView(
                kind=str(s["kind"]),
                record=str(s["record"]),
                node=s["node"],
                module=s["module"],
                file=s["file"],
                lean_hash=s["lean_hash"],
                chains=chains,
            )
        )
    return tuple(out)


def _keys(named: list[str] | None) -> frozenset[str] | None:
    return None if named is None else frozenset(named)


def _placed(p: dict[str, Any]) -> Placed:
    return Placed(key=str(p["key"]), version=str(p["version"]), state=str(p["state"]))


def _parts(
    record: str, text: str, body: str, found: tuple[explainers.Section, ...]
) -> tuple[WordsSection, ...]:
    """F21-R11: a version's sections, keyed by the gate's own reading (``sections.parts_of_text``,
    ``sections.key_of``) so the site's keys are the product's. An explainer whose sections name
    no step is one ``overview`` of its whole body, as the gate reads it; a section key carried
    twice (refused at the gate today) is shown once, its words joined, as the gate joins them."""
    canonical = {
        p.key: p.text for p in sections.keyed(sections.parts_of_text(text, gloss=record == "gloss"))
    }
    if record == "gloss" or not any(sec.steps for sec in found):
        key = sections.WHOLE if record == "gloss" else sections.OVERVIEW
        return (WordsSection(key, None, (), body, canonical.get(key, "")),)
    out: dict[str, WordsSection] = {}
    for sec in found:
        key = sections.key_of(sec.steps)
        if key in out:
            prior = out[key]
            out[key] = replace(prior, text=f"{prior.text}\n\n{sec.text}")
            continue
        out[key] = WordsSection(key, sec.heading, sec.steps, sec.text, canonical.get(key, ""))
    return tuple(out.values())


def _version(
    target_dir: Path,
    v: dict[str, Any],
    *,
    now: str | None,
    record: str,
    sigs: dict[str, list[_Sig]],
) -> VersionView:
    """One version as the product lists it, its words read from the tree. ``now`` is the hash of
    the subject's file as the checkout holds it, from which a gloss's ``describes_current`` is
    re-derived."""
    root = target_dir.parents[1]
    path = target_dir / str(v["path"])
    text = ""
    try:
        text = path.read_text(encoding="utf-8")
        _doc, body = glosses.split_front_matter(text)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        log.warning("%s does not read; shown without its words: %s", path, exc)
        body = ""
    found: tuple[explainers.Section, ...] = ()
    # F21-R6: an explainer/v2 is sectioned as a v1 is.
    if record == "explainer" and v["schema"] in explainers.RECORD_SCHEMAS:
        try:
            found = tuple(explainers.sections(body))
        except ValueError:
            found = ()
    signatures = sigs.get(str(v["hash"]), [])
    describes = v["describes_current"]
    if record == "gloss" and now is not None and v.get("lean_hash"):
        describes = v["lean_hash"] == now
    return VersionView(
        hash=str(v["hash"]),
        path=path.relative_to(root).as_posix(),
        schema=v["schema"],
        supersedes=v["supersedes"],
        author=v["author"],
        drafter=dict(v["drafter"]) if v["drafter"] else None,
        date=v["date"],
        withdrawn=bool(v["withdrawn"]),
        describes_current=describes,
        signers=tuple((s, d, p) for s, d, p, _k in signatures),
        body=body,
        sections=found,
        drafted_with=str(v["drafted_with"]) if v.get("drafted_with") else None,
        approvals=tuple((s, k) for s, _d, _p, k in signatures),
        parts=_parts(record, text, body, found),
    )


def _load_definitions(root: Path, target_dir: Path) -> tuple[LeanFile, ...]:
    """F20-T8 (R13): each definition module under ``defs/``, by path, as the products list them."""
    defs = target_dir / glosses.DEFS_DIR
    if not defs.is_dir():
        return ()
    found = (_lean_file(root, p) for p in sorted(defs.rglob("*.lean")) if p.is_file())
    return tuple(f for f in found if f is not None)


def _with_circular_paths(
    root: Path, target_id: str, graph: dict[str, Any], nodes: dict[str, NodeView]
) -> dict[str, NodeView]:
    """F08-T20 (D-12 v3.22): which claim each circular node on a path rests on, and which claims
    circle back to each ancestor — the gate's own ``graph.circular_marks`` over ``graph.json``'s
    deps, origins and statuses and the claim files in the tree, so the site cannot reach a
    different set of nodes than the products did. A path node's claim sits under the hole, not
    under the node, which is why the node's own ``defects/`` cannot name it."""
    nodes_dir = layout.graph_nodes_dir(root, target_id)
    rows = {str(e["node_id"]): e for e in graph["nodes"]}
    deps = {n: [str(d) for d in e["deps"]] for n, e in rows.items()}
    holes = {
        n: [d for d in ds if d in rows and graphmod.is_hole_of(n, d, str(rows[d].get("origin")))]
        for n, ds in deps.items()
    }
    claims = {
        n: found
        for n in rows
        if (found := graphmod.resolved_circular_claims(nodes_dir, nodes_dir / n))
    }
    statuses = {n: str(e["status"]) for n, e in rows.items()}
    on_path, below = graphmod.circular_marks(holes, deps, claims, statuses)
    prefix = nodes_dir.relative_to(root).as_posix()
    out = dict(nodes)
    for node_id, nv in nodes.items():
        view = nv
        if view.circular_claim is None and node_id in on_path:
            view = replace(view, circular_claim=f"{prefix}/{on_path[node_id]}")
        if node_id in below:
            view = replace(view, circular_below=tuple(f"{prefix}/{r}" for r in below[node_id]))
        out[node_id] = view
    return out


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
        nodes = _with_circular_paths(root, target_id, graph, nodes)
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
            admissions=_steward_admissions(target_dir),
            outlines=_load_outlines(target_dir),
            subjects=_load_glosses(target_dir),
            definitions=_load_definitions(root, target_dir),
            words_needed=_load_words_needed(target_dir, str(graph["root"])),
        )
    return site
