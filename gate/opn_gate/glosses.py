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

The module also holds what glosses and explainers share (R6 to R9): versions and their linear
chains, whose current version is the latest not withdrawn; gloss signatures
(``gloss-signature/v1``), which change no status, grade or digestion state; and the coverage
report (R20) over every Lean file and merged proof artifact of a graph.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from opn_gate import paths, records, schemas, sections, signed
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Located
from opn_gate.signer import Signer

log = logging.getLogger(__name__)

SCHEMA = "gloss/v1"
#: Every gloss record version the gate reads, each validated against its own ``schema`` (D-34):
#: v2 adds ``drafted_with`` (F21-R6; D-3 v3.31, D-23).
SCHEMAS: frozenset[str] = frozenset({"gloss/v1", "gloss/v2"})
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
    """The gloss's front matter, validated against the version it declares (``gloss/v1`` or
    ``gloss/v2``) with exactly one of author and drafter set; or the reason it is not a gloss, as
    ``gloss-invalid``."""
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
    if doc.get("schema") not in SCHEMAS:
        return _invalid(
            located,
            f"the front matter declares {doc.get('schema')!r}, not one of "
            f"{', '.join(sorted(SCHEMAS))}",
        )
    violations = schemas.violations(doc, str(doc["schema"]))
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


# --- versions and chains (F20-R6, R7, R9; D-3 v3.30) --------------------------------------------
#
# A gloss supersedes the head of its chain, never an earlier version; an explainer does the same
# on its proof (F20-Q3). The gate holds new versions to that, so on disk a chain is linear except
# where a version was withdrawn: a withdrawn version is absent from its chain, so the version
# before it is the head again and may be superseded a second time. ``chains`` linearises that
# tree without a clock — of two versions superseding one, the one filed while the other's whole
# branch was withdrawn comes after it — and the current version is the last not withdrawn.

#: A subject's identity: ``(kind, node, module)`` for a gloss, ``("proof", node, proof hash)``
#: for an explainer.
Subject = tuple[str, str | None, str | None]


@dataclass(frozen=True)
class Version:
    """One gloss or explainer file, as its chain reads it."""

    hash: str
    path: Path
    subject: Subject
    supersedes: str | None
    author: str | None
    drafter: dict[str, Any] | None
    date: str | None
    schema: str | None  # gloss/v1 or v2, explainer/v1 or v2, or None for one filed before F20
    lean_hash: str | None = None  # a gloss's: the text it describes
    #: F21-R6 (D-23): the model a contributor's agent drafted with, in their words; ``None`` for
    #: a person's own writing and for every v1 record.
    drafted_with: str | None = None

    @property
    def by_model(self) -> bool:
        """F21-R11: whether a model wrote this version's words — it names one in ``drafted_with``,
        or it is one of F20's drafts (a ``drafter`` block)."""
        return self.drafted_with is not None or self.drafter is not None


@dataclass(frozen=True)
class Chain:
    versions: tuple[Version, ...]
    withdrawn: frozenset[str]

    @property
    def current(self) -> Version | None:
        """The latest version not withdrawn (D-3 v3.30), or ``None`` when all are."""
        live = [v for v in self.versions if v.hash not in self.withdrawn]
        return live[-1] if live else None

    @property
    def hashes(self) -> frozenset[str]:
        return frozenset(v.hash for v in self.versions)


def chains(versions: list[Version], withdrawn: frozenset[str]) -> list[Chain]:
    """The chains of one subject's versions, in record order: by the date the first version
    states, then its hash — an order for listing, which ranks nothing (D-25) and decides no
    head. A version superseding something not of this subject starts a chain of its own."""
    by_hash = {v.hash: v for v in versions}
    children: dict[str, list[Version]] = {}
    roots: list[Version] = []
    for v in versions:
        if v.supersedes is not None and v.supersedes in by_hash and v.supersedes != v.hash:
            children.setdefault(v.supersedes, []).append(v)
        else:
            roots.append(v)

    def live(v: Version, seen: frozenset[str]) -> bool:
        if v.hash in seen:
            return False
        return v.hash not in withdrawn or any(
            live(c, seen | {v.hash}) for c in children.get(v.hash, [])
        )

    def walk(v: Version, seen: set[str]) -> list[Version]:
        if v.hash in seen:
            return []
        seen.add(v.hash)
        kids = children.get(v.hash, [])
        dead = sorted((c for c in kids if not live(c, frozenset())), key=lambda c: c.hash)
        alive = sorted((c for c in kids if live(c, frozenset())), key=lambda c: c.hash)
        out = [v]
        for c in [*dead, *alive]:
            out.extend(walk(c, seen))
        return out

    seen: set[str] = set()
    out = [
        Chain(tuple(walk(r, seen)), withdrawn)
        for r in sorted(roots, key=lambda r: (r.date or "", r.hash))
    ]
    # Anything a cycle kept from every root (impossible for content-hashed files, but read
    # defensively: one bad pair must not hide a version) is listed as a chain of its own.
    out.extend(Chain((v,), withdrawn) for v in versions if v.hash not in seen)
    return out


def chain_of(found: list[Chain], digest: str) -> Chain | None:
    return next((c for c in found if digest in c.hashes), None)


def withdrawn_versions(parent_dir: Path, directory: str) -> frozenset[str]:
    """The hashes of the ``<directory>/<hash>.md`` files a merged withdrawal under
    ``parent_dir/withdrawals/`` names (R7): read as absent by every reader, still in the tree."""
    names = records.withdrawn_names(parent_dir, directory)
    return frozenset(name[: -len(".md")] for name in names if name.endswith(".md"))


def gloss_version(path: Path, doc: dict[str, Any]) -> Version:
    subject = doc["subject"]
    return Version(
        hash=path.stem,
        path=path,
        subject=(str(subject["kind"]), subject["node"], subject["module"]),
        supersedes=doc["supersedes"],
        author=doc["author"],
        drafter=doc["drafter"],
        date=str(doc["date"]),
        schema=str(doc["schema"]),
        lean_hash=str(subject["lean_hash"]),
        drafted_with=doc.get("drafted_with"),
    )


def load_versions(parent_dir: Path) -> list[Version]:
    """Every gloss under ``parent_dir/gloss/`` whose front matter validates, by file name. One
    that does not is logged and passed over: the gate refused it at merge, and one bad file must
    never decide what the products say (2026-09-17)."""
    directory = parent_dir / GLOSS_DIR
    if not directory.is_dir():
        return []
    out: list[Version] = []
    for path in sorted(p for p in directory.iterdir() if p.is_file() and p.suffix == ".md"):
        if not _HASH_RE.match(path.stem):
            continue
        try:
            doc, _ = split_front_matter(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            log.warning("%s is not a gloss and is passed over: %s", path, exc)
            continue
        schema = doc.get("schema") if doc is not None else None
        if doc is None or schema not in SCHEMAS or schemas.violations(doc, str(schema)):
            log.warning("%s does not validate as a gloss record and is passed over", path)
            continue
        out.append(gloss_version(path, doc))
    return out


def head_problems(
    path: str,
    version: Version,
    siblings: list[Version],
    withdrawn: frozenset[str],
) -> list[Diagnostic]:
    """R6: a version that supersedes another names the current head of a chain of its own
    subject (``record-not-head``, naming the head). Anyone may supersede a signed version: F20's
    rule that only a steward or curator might (``signed-supersede``) is withdrawn (F21-R13; D-3
    v3.31), and a person's change to verified words is pending until a steward or curator signs
    it (``opn_gate.sections``)."""
    named = version.supersedes
    if named is None:
        return []
    same = [v for v in siblings if v.hash != version.hash and v.subject == version.subject]
    found = chains(same, withdrawn)
    chain = chain_of(found, named)
    head = chain.current if chain is not None else None
    if chain is not None and head is not None and head.hash == named:
        return []
    heads = (
        [c.current.hash for c in found if c.current is not None]
        if chain is None
        else [head.hash]
        if head is not None
        else []
    )
    why = (
        "no merged version of the same subject has that hash (a version still in an open pull "
        "request cannot be superseded until it merges)"
        if chain is None
        else "it has been withdrawn"
        if named in withdrawn
        else "it has already been superseded"
    )
    return [
        Diagnostic(
            "record-not-head",
            f"{path} supersedes {named}, and {why}; a version supersedes the current head of "
            f"its chain ({', '.join(heads) or 'none'}) or starts a chain of its own "
            "(F20-R6, D-3 v3.30)",
            {
                "path": path,
                "supersedes": named,
                "head": heads[0] if len(heads) == 1 else None,
                "heads": heads,
            },
        )
    ]


# --- gloss signatures (F20-R8) ------------------------------------------------------------------

SIGNATURE_SCHEMA = "gloss-signature/v1"
#: v2 adds ``sections``: the section keys the signature approves (F21-R13; D-3 v3.31).
SIGNATURE_SCHEMA_V2 = "gloss-signature/v2"
SIGNATURE_SCHEMAS: frozenset[str] = frozenset({SIGNATURE_SCHEMA, SIGNATURE_SCHEMA_V2})
SIGNED_DIR = "signed"
AFFIRMATION = "I have read this against the Lean it names, and it says what the Lean says."
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_SIGNATURE_RE = re.compile(r"^(?P<hash>[0-9a-f]{64})-(?P<n>[1-9][0-9]*)\.ya?ml$")


@dataclass(frozen=True)
class Signature:
    gloss: str
    signer: str
    date: str
    path: Path
    doc: dict[str, Any]

    @property
    def sections(self) -> list[str] | None:
        """The section keys this signature approves; ``None`` for every section (a v1 signature,
        or a v2 one naming none) (F21-R13)."""
        named = self.doc.get("sections")
        return [str(k) for k in named] if isinstance(named, list) else None

    def as_dict(self) -> dict[str, Any]:
        return {"signer": self.signer, "date": self.date, "sections": self.sections}


def signed_dir(parent_dir: Path) -> Path:
    return parent_dir / GLOSS_DIR / SIGNED_DIR


def gloss_hashes(parent_dir: Path) -> frozenset[str]:
    directory = parent_dir / GLOSS_DIR
    if not directory.is_dir():
        return frozenset()
    return frozenset(
        p.stem
        for p in directory.iterdir()
        if p.is_file() and p.suffix == ".md" and _HASH_RE.match(p.stem)
    )


def signature_problems(
    path: str, doc: dict[str, Any], parent_dir: Path, signer: Signer
) -> list[Diagnostic]:
    """R8: why a gloss signature is not valid, by name; empty when it is — the gloss is in the
    tree, the sentence is the fixed one, the signature verifies under the record's own key and
    the file is named for the gloss it signs. Who signed is the caller's question."""
    found: list[Diagnostic] = []
    details = {"path": path, "signer": doc.get("signer")}
    gloss = str(doc.get("gloss"))
    if gloss not in gloss_hashes(parent_dir):
        found.append(
            Diagnostic(
                "gloss-absent",
                f"{path} signs gloss {gloss[:12]}…, which is not under {GLOSS_DIR}/ beside it",
                details,
            )
        )
    if doc.get("affirmation") != AFFIRMATION:
        found.append(
            Diagnostic(
                "affirmation-differs",
                f"{path}: the sentence is not the fixed one (F20-R8)",
                details,
            )
        )
    if not signed.verifies(doc, signer):
        found.append(
            Diagnostic(
                "signature-invalid",
                f"{path}: the signature does not verify under the record's key",
                details,
            )
        )
    unknown = [k for k in doc.get("sections") or [] if k != sections.WHOLE]
    if unknown:
        found.append(
            Diagnostic(
                "signature-section-unknown",
                f"{path} approves section {', '.join(map(str, unknown))}, which gloss "
                f"{gloss[:12]}… does not have: a gloss is one section, {sections.WHOLE} "
                "(F21-R11, R13)",
                {**details, "sections": unknown, "known": [sections.WHOLE]},
            )
        )
    m = _SIGNATURE_RE.match(PurePosixPath(path).name)
    if m is None or m.group("hash") != gloss:
        found.append(
            Diagnostic(
                "signature-name",
                f"{path}: a gloss signature is gloss/signed/<hash>-<n>.yaml, named for the gloss "
                "it signs (F20-R8)",
                details,
            )
        )
    return found


def load_signatures(parent_dir: Path) -> list[Signature]:
    """Every gloss signature under ``parent_dir/gloss/signed/`` that validates, by file name;
    one that does not is logged and passed over (it counts for nothing)."""
    directory = signed_dir(parent_dir)
    if not directory.is_dir():
        return []
    out: list[Signature] = []
    for path in sorted(p for p in directory.iterdir() if p.is_file()):
        try:
            doc = load_signature_doc(path, SIGNATURE_SCHEMAS)
        except schemas.SchemaError as exc:
            log.warning("%s counts for nothing: %s", path, exc)
            continue
        out.append(Signature(str(doc["gloss"]), str(doc["signer"]), str(doc["date"]), path, doc))
    return out


def load_signature_doc(path: Path, accepted: frozenset[str]) -> dict[str, Any]:
    """A signature file validated against the version it declares, which must be one of
    ``accepted`` (D-34: several versions live at once); ``SchemaError`` otherwise."""
    doc = schemas.load_yaml(path)
    if doc.get("schema") not in accepted:
        msg = f"{path} declares {doc.get('schema')!r}, not one of {', '.join(sorted(accepted))}"
        raise schemas.SchemaError(msg)
    return doc


def valid_signatures(parent_dir: Path, signer: Signer) -> dict[str, list[Signature]]:
    """The signatures that count, by the gloss they sign (R8). A signature changes no status,
    grade or digestion state (F20-Q12): only the glosses product reads this."""
    out: dict[str, list[Signature]] = {}
    for sig in load_signatures(parent_dir):
        problems = signature_problems(str(sig.path), sig.doc, parent_dir, signer)
        if problems:
            log.warning("%s counts for nothing: %s", sig.path, problems[0].message)
            continue
        out.setdefault(sig.gloss, []).append(sig)
    return out


def next_signature_path(parent_dir: Path, gloss: str) -> Path:
    directory = signed_dir(parent_dir)
    taken = {
        int(m.group("n"))
        for p in (directory.iterdir() if directory.is_dir() else ())
        if (m := _SIGNATURE_RE.match(p.name)) is not None and m.group("hash") == gloss
    }
    return directory / f"{gloss}-{max(taken, default=0) + 1}.yaml"


def sign(  # noqa: PLR0913 — one argument per fact the record carries
    parent_dir: Path,
    gloss: str,
    *,
    target_id: str,
    node_id: str | None,
    signer_login: str,
    date: str,
    key_path: Path,
    signer: Signer,
    approves: list[str] | None = None,
) -> Path:
    """R8: write one gloss signature with the signer's own key, or refuse by name with nothing
    written when the gloss is not there (C7). ``parent_dir`` is the node directory, or the target
    directory for a definition module's gloss. ``approves`` names the sections approved
    (``gloss-signature/v2``, F21-R13); ``None`` writes a v1 signature, which approves all."""
    if not _HASH_RE.match(gloss):
        msg = f"{gloss!r} is not a gloss hash (64 lowercase hex characters, D-3)"
        raise GlossError(msg)
    if gloss not in gloss_hashes(parent_dir):
        msg = f"no gloss {gloss[:12]}… is under {parent_dir.name}/{GLOSS_DIR}/; nothing to sign"
        raise GlossError(msg)
    if approves is not None and set(approves) - {sections.WHOLE}:
        msg = f"a gloss is one section, {sections.WHOLE}; nothing to sign by {approves}"
        raise GlossError(msg)
    doc: dict[str, Any] = {
        "schema": SIGNATURE_SCHEMA if approves is None else SIGNATURE_SCHEMA_V2,
        "target": target_id,
        "node": node_id,
        "gloss": gloss,
        "affirmation": AFFIRMATION,
        "signer": signer_login,
        "date": date[:10],
    }
    if approves is not None:
        doc["sections"] = list(dict.fromkeys(approves))
    doc = schemas.validate(signed.sign(doc, key_path, signer), str(doc["schema"]))
    path = next_signature_path(parent_dir, gloss)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    log.info("gloss: %s signed %s under %s", signer_login, gloss[:12], parent_dir.name)
    return path


# --- coverage (F20-R20) -------------------------------------------------------------------------


#: Why a subject is not covered (R20), as the report names it.
NO_GLOSS = "no-gloss"
EARLIER_TEXT = "describes-earlier-text"
ALL_WITHDRAWN = "all-withdrawn"
NO_EXPLAINER = "no-explainer"
ROOT_WITHOUT_INFORMAL = "root-without-informal"
RESTATES_UNCOVERED = "restates-uncovered"
CONTEXT_FILE = "Context.lean"


def coverage(graph_root: Path) -> dict[str, Any]:
    """R20: every Lean file and merged proof artifact of every target, with the gloss or
    explainer that covers it or the reason none does, and whether the whole is complete.

    A statement, witness, relation or definition module is covered by a chain whose current
    version describes the file as it stands; a gloss of since-changed text covers nothing. A
    merged proof artifact is covered by an explainer chain with a current version. A root's
    statement is covered by its curated informal statement (or, where the source may not be
    reproduced, its paraphrase; F11-R10), and a ``Context.lean`` by the statements it restates —
    the node's dependencies, read through any revision — each said per file, never left out.
    A target that does not load is listed under ``problems`` and makes the report incomplete."""
    from opn_gate import graph as graphmod  # noqa: PLC0415 — graph reads records, as this does

    rows: list[dict[str, Any]] = []
    problems: list[dict[str, str]] = []
    targets = graph_root / "targets"
    for target_dir in sorted(p for p in targets.iterdir() if (p / "nodes").is_dir()):
        try:
            tg = graphmod.load_target(graph_root, target_dir.name)
        except (ValueError, OSError) as exc:  # GraphError, SchemaError: a graph defect, named
            problems.append({"target": target_dir.name, "error": str(exc)})
            continue
        rows.extend(_target_rows(graph_root, tg))
    covered = sum(1 for r in rows if r["covered"])
    return {
        "complete": not problems and covered == len(rows),
        "counts": {"subjects": len(rows), "covered": covered},
        "problems": problems,
        "subjects": rows,
    }


def _row(graph_root: Path, target_id: str, file: Path, kind: str, **where: Any) -> dict[str, Any]:
    return {
        "target": target_id,
        "file": file.relative_to(graph_root).as_posix(),
        "kind": kind,
        "node": where.get("node"),
        "module": where.get("module"),
        "covered": False,
        "by": None,
        "reason": None,
    }


def _target_rows(graph_root: Path, tg: Any) -> list[dict[str, Any]]:
    """One target's rows: node by node, each node's Lean files, its Context and its merged
    proof artifacts; then the definition modules."""
    words = _curated_words(tg.path)
    per_node = {n: _lean_rows(graph_root, tg, n, words) for n in tg.order}
    statements = {n: r for n, rs in per_node.items() for r in rs if r["kind"] == "statement"}
    result: list[dict[str, Any]] = []
    for node_id in tg.order:
        node_dir: Path = tg.nodes[node_id].path
        result.extend(per_node[node_id])
        context = node_dir / CONTEXT_FILE
        if context.is_file():
            r = _row(graph_root, tg.target_id, context, "context", node=node_id)
            restates = list(tg.nodes[node_id].deps)
            r["by"] = {"restates": restates}
            if all(statements.get(d, {}).get("covered") for d in restates):
                r["covered"] = True
            else:
                r["reason"] = RESTATES_UNCOVERED
            result.append(r)
        result.extend(_artifact_rows(graph_root, tg.target_id, node_dir))
    result.extend(_definition_rows(graph_root, tg.target_id, tg.path))
    return result


def _lean_rows(graph_root: Path, tg: Any, node_id: str, words: str | None) -> list[dict[str, Any]]:
    """A node's statement, witness and relation, each covered by a gloss of its text as it
    stands — the root's statement by the target's curated words instead."""
    node_dir: Path = tg.nodes[node_id].path
    versions = load_versions(node_dir)
    withdrawn = withdrawn_versions(node_dir, GLOSS_DIR)
    out: list[dict[str, Any]] = []
    for kind, name in KIND_FILES.items():
        file = node_dir / name
        if not file.is_file():
            continue
        r = _row(graph_root, tg.target_id, file, kind, node=node_id)
        same = [v for v in versions if v.subject == (kind, node_id, None)]
        _cover_by_gloss(r, file, same, withdrawn)
        if kind == "statement" and node_id == tg.root and not r["covered"]:
            if words is not None:
                r.update(covered=True, by={words: "target.yaml"}, reason=None)
            elif r["reason"] == NO_GLOSS:
                r["reason"] = ROOT_WITHOUT_INFORMAL
        out.append(r)
    return out


def _artifact_rows(graph_root: Path, target_id: str, node_dir: Path) -> list[dict[str, Any]]:
    """A node's merged proof artifacts, each covered by an explainer chain with a current
    version on it."""
    from opn_gate import explainers  # noqa: PLC0415 — explainers imports this module

    withdrawn = withdrawn_versions(node_dir, explainers.EXPLAINER_DIR)
    everything = explainers.versions(node_dir)
    out: list[dict[str, Any]] = []
    for digest, rel in explainers.merged_artifacts(node_dir).items():
        kind = (
            "proof"
            if rel == "Proof.lean"
            else "alternate"
            if rel.endswith(paths.ALTERNATE_SUFFIX)
            else "partial"
        )
        r = _row(graph_root, target_id, node_dir / rel, kind, node=node_dir.name)
        found = chains([v for v in everything if v.subject[2] == digest], withdrawn)
        current = [c.current for c in found if c.current is not None]
        if current:
            r.update(covered=True, by={"explainer": current[0].hash})
        else:
            r["reason"] = ALL_WITHDRAWN if found else NO_EXPLAINER
        out.append(r)
    return out


def _definition_rows(graph_root: Path, target_id: str, target_dir: Path) -> list[dict[str, Any]]:
    defs_dir = target_dir / DEFS_DIR
    if not defs_dir.is_dir():
        return []
    versions = load_versions(target_dir)
    withdrawn = withdrawn_versions(target_dir, GLOSS_DIR)
    out: list[dict[str, Any]] = []
    for file in sorted(p for p in defs_dir.rglob("*.lean") if p.is_file()):
        module = file.relative_to(defs_dir).as_posix()
        r = _row(graph_root, target_id, file, DEFINITION, module=module)
        same = [v for v in versions if v.subject == (DEFINITION, None, module)]
        _cover_by_gloss(r, file, same, withdrawn)
        out.append(r)
    return out


def _cover_by_gloss(
    row: dict[str, Any], file: Path, versions: list[Version], withdrawn: frozenset[str]
) -> None:
    """Covered when a chain's current version describes the file as it stands."""
    found = chains(versions, withdrawn)
    current = [c.current for c in found if c.current is not None]
    text = schemas.content_hash(file.read_bytes())
    describing = [v for v in current if v.lean_hash == text]
    if describing:
        row.update(covered=True, by={"gloss": describing[0].hash})
    elif current:
        row["reason"] = EARLIER_TEXT
    elif found:
        row["reason"] = ALL_WITHDRAWN
    else:
        row["reason"] = NO_GLOSS


def _curated_words(target_dir: Path) -> str | None:
    """``informal`` or ``paraphrase``: which curated words of record ``target.yaml`` holds for
    the root (D-6, D-9; F11-R10), or ``None`` without a record or words."""
    path = target_dir / "target.yaml"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        log.warning("%s does not read; the root has no curated words here: %s", path, exc)
        return None
    return curated_words(doc)


def curated_words(record: Any) -> str | None:
    """Which curated words a parsed ``target.yaml`` holds for the root: ``informal``, else
    ``paraphrase`` (D-6, D-9; F11-R10), else ``None``. Pure, so a reader of the committed file
    (the service, the site) decides as ``coverage`` does."""
    if not isinstance(record, dict):
        return None
    for field in ("informal", "paraphrase"):
        if isinstance(record.get(field), str) and record[field].strip():
            return field
    return None


# --- words needed (F21-R8, R9; Q6) ---------------------------------------------------------------

#: The proof artifacts an explainer describes; each has an outline at
#: ``targets/<id>/outlines/<artifact-hash>.json`` (F19).
ARTIFACT_KINDS = frozenset({"proof", "alternate", "partial"})


def needed(doc: dict[str, Any], *, root: str | None, curated: str | None) -> list[dict[str, Any]]:
    """F21-R8: the subjects of one target's ``glosses.json`` (``glosses/v1`` or ``v2``) that lack
    words, in the product's order, ranked by nothing (D-25): each with its target, file (from
    the graph root), kind, node, module, the reason ``coverage`` gives and, for a proof
    artifact, the path of its outline. ``root`` is the target's root node and ``curated`` what
    ``curated_words`` says of its ``target.yaml``. ``Context.lean`` takes no words of its own,
    so it is not a subject here (Q6).

    The rules are ``coverage``'s, read off the product: a Lean file is covered by a chain whose
    current version describes the file as the product hashed it; a merged artifact by an
    explainer chain with a current version; the root's statement, failing a gloss, by curated
    words. A subject the tree does not hold (a gloss naming a missing file, an explainer of an
    ``absent`` artifact) has no file to write words for and is not listed."""
    target = str(doc["target"])
    base = f"targets/{target}"
    out: list[dict[str, Any]] = []
    for subject in doc["subjects"]:
        kind, file, lean_hash = subject["kind"], subject["file"], subject["lean_hash"]
        if file is None or lean_hash is None or kind == "absent":
            continue
        chains_ = subject["chains"]
        current = [c["current"] for c in chains_ if c["current"] is not None]
        if subject["record"] == "explainer":
            if current:
                continue
            reason = ALL_WITHDRAWN if chains_ else NO_EXPLAINER
        else:
            hashes = {v["hash"]: v["lean_hash"] for c in chains_ for v in c["versions"]}
            if any(hashes.get(h) == lean_hash for h in current):
                continue
            reason = EARLIER_TEXT if current else ALL_WITHDRAWN if chains_ else NO_GLOSS
            if kind == "statement" and subject["node"] == root and root is not None:
                if curated is not None:
                    continue
                if reason == NO_GLOSS:
                    reason = ROOT_WITHOUT_INFORMAL
        out.append(
            {
                "target": target,
                "file": f"{base}/{file}",
                "kind": kind,
                "node": subject["node"],
                "module": subject["module"],
                "reason": reason,
                "outline": f"{base}/outlines/{lean_hash}.json" if kind in ARTIFACT_KINDS else None,
            }
        )
    return out
