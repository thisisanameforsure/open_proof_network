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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from opn_gate import paths, records, schemas, signed
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Located
from opn_gate.signer import Signer

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
    schema: str | None  # gloss/v1, explainer/v1, or None for an explainer filed before F20
    lean_hash: str | None = None  # a gloss's: the text it describes


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
        schema=SCHEMA,
        lean_hash=str(subject["lean_hash"]),
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
        if doc is None or doc.get("schema") != SCHEMA or schemas.violations(doc, SCHEMA):
            log.warning("%s does not validate as %s and is passed over", path, SCHEMA)
            continue
        out.append(gloss_version(path, doc))
    return out


def head_problems(  # noqa: PLR0913 — the version, its siblings and the host's facts
    path: str,
    version: Version,
    siblings: list[Version],
    withdrawn: frozenset[str],
    *,
    signed_versions: frozenset[str],
    author: str | None,
    may_supersede_signed: Callable[[str | None], bool],
) -> list[Diagnostic]:
    """R6: a version that supersedes another names the current head of a chain of its own
    subject (``record-not-head``, naming the head), and supersedes a validly signed version only
    in a pull request an active steward or a listed curator opened (``signed-supersede``)."""
    named = version.supersedes
    if named is None:
        return []
    same = [v for v in siblings if v.hash != version.hash and v.subject == version.subject]
    found = chains(same, withdrawn)
    chain = chain_of(found, named)
    head = chain.current if chain is not None else None
    if chain is None or head is None or head.hash != named:
        heads = (
            [c.current.hash for c in found if c.current is not None]
            if chain is None
            else [head.hash]
            if head is not None
            else []
        )
        why = (
            "it is not a version of the same subject"
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
    if named in signed_versions and not may_supersede_signed(author):
        return [
            Diagnostic(
                "signed-supersede",
                f"{path} supersedes {named}, which a steward or curator has signed; only an "
                f"active steward of the target or a listed curator supersedes a signed version, "
                f"and this pull request was opened by {author or 'an unknown login'}. Start a "
                "chain of your own instead (F20-R6)",
                {"path": path, "supersedes": named, "author": author},
            )
        ]
    return []


# --- gloss signatures (F20-R8) ------------------------------------------------------------------

SIGNATURE_SCHEMA = "gloss-signature/v1"
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

    def as_dict(self) -> dict[str, Any]:
        return {"signer": self.signer, "date": self.date}


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
            doc = schemas.load_yaml(path, SIGNATURE_SCHEMA)
        except schemas.SchemaError as exc:
            log.warning("%s counts for nothing: %s", path, exc)
            continue
        out.append(Signature(str(doc["gloss"]), str(doc["signer"]), str(doc["date"]), path, doc))
    return out


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
) -> Path:
    """R8: write one gloss signature with the signer's own key, or refuse by name with nothing
    written when the gloss is not there (C7). ``parent_dir`` is the node directory, or the target
    directory for a definition module's gloss."""
    if not _HASH_RE.match(gloss):
        msg = f"{gloss!r} is not a gloss hash (64 lowercase hex characters, D-3)"
        raise GlossError(msg)
    if gloss not in gloss_hashes(parent_dir):
        msg = f"no gloss {gloss[:12]}… is under {parent_dir.name}/{GLOSS_DIR}/; nothing to sign"
        raise GlossError(msg)
    doc = {
        "schema": SIGNATURE_SCHEMA,
        "target": target_id,
        "node": node_id,
        "gloss": gloss,
        "affirmation": AFFIRMATION,
        "signer": signer_login,
        "date": date[:10],
    }
    doc = schemas.validate(signed.sign(doc, key_path, signer), SIGNATURE_SCHEMA)
    path = next_signature_path(parent_dir, gloss)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    log.info("gloss: %s signed %s under %s", signer_login, gloss[:12], parent_dir.name)
    return path
