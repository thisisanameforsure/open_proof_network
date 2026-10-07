"""Explainer signatures (F15-R8; D-3 v3.17, D-33 v3.17).

An explainer is prose about a merged proof, content-hashed and labelled unverified (D-3). A
signature on one is a *comprehension claim*: a real-identity contributor affirming one sentence,
"I can explain this proof without the tool that produced it". It claims nothing about the
mathematics, changes no verdict and earns nothing at merge; the one thing it does is count toward
a resolved target's digestion state (``products.digestion``), and only a valid one counts.

Signatures live at ``nodes/<id>/explainer/signed/<hash>-<n>.yaml``, one file per signature,
named for the explainer they sign, and are signed with the signer's own key over the canonical
body (``opn_gate.signed``). Valid means: the explainer file is present, the sentence is the fixed
one, and the signature verifies under the record's key. Who may sign — an active steward of the
target or a listed curator at Stage 0 (F15-Q4) — is the gate's rule at merge (``modes``), not
re-derived here: once merged, a signature's signer was checked.

Since F20 (D-3 v3.30) an explainer may be an ``explainer/v1`` record: front matter naming the
merged proof artifact it describes, and level-2 sections that may name that artifact's outline
steps (``## The bound {steps: s3 s4.1}``, F20-Q2). ``check_record`` holds one to both; an
explainer filed before F20 stays valid and unanchored.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from opn_gate import glosses, schemas, signed
from opn_gate import sections as sectionsmod
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Located
from opn_gate.signer import Signer

log = logging.getLogger(__name__)

SCHEMA = "explainer-signature/v1"
#: v2 adds ``sections``: the section keys the signature approves (F21-R13; D-3 v3.31).
SCHEMA_V2 = "explainer-signature/v2"
#: v3 adds ``via`` (F23-R10, R11; D-3 v3.33): read exactly as v2 everywhere.
SCHEMA_V3 = "explainer-signature/v3"
SCHEMAS: frozenset[str] = frozenset({SCHEMA, SCHEMA_V2, SCHEMA_V3})
EXPLAINER_DIR = "explainer"
SIGNED_DIR = "signed"
#: A cited name ending so is a file of the graph, never a constant (F22-T12).
LEAN_FILE_SUFFIX = ".lean"
AFFIRMATION = "I can explain this proof without the tool that produced it."
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_FILE_RE = re.compile(r"^(?P<hash>[0-9a-f]{64})-(?P<n>[1-9][0-9]*)\.ya?ml$")


class ExplainerError(ValueError):
    """The signature cannot be written as asked. Nothing is written."""


@dataclass(frozen=True)
class Signature:
    explainer: str  # the explainer's hash, its file name under explainer/
    signer: str
    date: str
    key: str
    path: Path
    doc: dict[str, Any]
    n: int = 0

    @property
    def sections(self) -> list[str] | None:
        """The section keys this signature approves; ``None`` for every section of the version
        (a v1 signature) (F21-R13)."""
        named = self.doc.get("sections")
        return [str(k) for k in named] if isinstance(named, list) else None

    def as_dict(self) -> dict[str, Any]:
        return {"explainer": self.explainer, "signer": self.signer, "date": self.date}


def signed_dir(node_dir: Path) -> Path:
    return node_dir / EXPLAINER_DIR / SIGNED_DIR


def explainer_hashes(node_dir: Path) -> frozenset[str]:
    """The hashes of the explainers on the node: the stems of ``explainer/*.md``."""
    directory = node_dir / EXPLAINER_DIR
    if not directory.is_dir():
        return frozenset()
    return frozenset(
        p.stem
        for p in directory.iterdir()
        if p.is_file() and p.suffix == ".md" and _HASH_RE.match(p.stem)
    )


def signature_of(doc: dict[str, Any], path: Path, n: int = 0) -> Signature:
    return Signature(
        explainer=str(doc["explainer"]),
        signer=str(doc["signer"]),
        date=str(doc["date"]),
        key=str(doc["key"]),
        path=path,
        doc=doc,
        n=n,
    )


def load(node_dir: Path) -> list[Signature]:
    """Every signature file on the node, validated, in file order. A file under ``signed/`` that
    is not a signature, or one that does not validate, is a graph defect and raises."""
    directory = signed_dir(node_dir)
    if not directory.is_dir():
        return []
    out: list[Signature] = []
    for path in sorted(p for p in directory.iterdir() if p.is_file()):
        m = _FILE_RE.match(path.name)
        if m is None:
            msg = f"{path}: an explainer signature is explainer/signed/<hash>-<n>.yaml (F15-R8)"
            raise schemas.SchemaError(msg)
        doc = glosses.load_signature_doc(path, SCHEMAS)
        out.append(signature_of(doc, path, int(m.group("n"))))
    return out


def problems_of(sig: Signature, node_dir: Path, signer: Signer) -> tuple[str, ...]:
    """Why the signature is not valid, by name (R8); empty when it is."""
    problems: list[str] = []
    if sig.explainer not in explainer_hashes(node_dir):
        problems.append(
            f"explainer-absent: no explainer {sig.explainer[:12]}… is on {node_dir.name}"
        )
    elif sig.sections is not None:
        known = section_keys(node_dir / EXPLAINER_DIR / f"{sig.explainer}.md")
        unknown = [k for k in sig.sections if k not in known]
        if unknown:
            problems.append(
                f"signature-section-unknown: explainer {sig.explainer[:12]}… has no section "
                f"{', '.join(unknown)}; its sections are {', '.join(known) or 'none'} "
                "(F21-R11, R13)"
            )
    if sig.doc.get("affirmation") != AFFIRMATION:
        problems.append("affirmation-differs: the sentence is not the fixed one (F15-R8)")
    if not signed.verifies(sig.doc, signer):
        problems.append("signature-invalid: the signature does not verify under the record's key")
    stem_hash = _FILE_RE.match(sig.path.name)
    if stem_hash is not None and stem_hash.group("hash") != sig.explainer:
        problems.append("signature-name: the file is named for a different explainer than it signs")
    return tuple(problems)


def valid(node_dir: Path, signer: Signer) -> list[Signature]:
    """The signatures that count: explainer present, sentence fixed, signature verifying."""
    out: list[Signature] = []
    for sig in load(node_dir):
        problems = problems_of(sig, node_dir, signer)
        if problems:
            log.warning("%s counts for nothing: %s", sig.path, "; ".join(problems))
            continue
        out.append(sig)
    return out


# --- writing (``opn-gate explainer sign``) ------------------------------------------------------


def next_path(node_dir: Path, explainer_hash: str) -> Path:
    directory = signed_dir(node_dir)
    taken = {
        int(m.group("n"))
        for p in (directory.iterdir() if directory.is_dir() else ())
        if (m := _FILE_RE.match(p.name)) is not None and m.group("hash") == explainer_hash
    }
    return directory / f"{explainer_hash}-{max(taken, default=0) + 1}.yaml"


def sign(  # noqa: PLR0913 — one argument per fact the record carries
    node_dir: Path,
    explainer_hash: str,
    *,
    target_id: str,
    signer_login: str,
    date: str,
    key_path: Path,
    signer: Signer,
    approves: list[str] | None = None,
) -> Path:
    """R8: write one signature with the signer's own key, refusing by name with nothing written
    when the explainer is not on the node (C7). ``approves`` names the sections approved
    (``explainer-signature/v2``, F21-R13), each one the explainer has; ``None`` writes a v1
    signature, which approves every section."""
    if not _HASH_RE.match(explainer_hash):
        msg = f"{explainer_hash!r} is not an explainer hash (64 lowercase hex characters, D-3)"
        raise ExplainerError(msg)
    if explainer_hash not in explainer_hashes(node_dir):
        msg = f"no explainer {explainer_hash[:12]}… is on {node_dir.name}; nothing to sign"
        raise ExplainerError(msg)
    if approves is not None:
        known = section_keys(node_dir / EXPLAINER_DIR / f"{explainer_hash}.md")
        unknown = [k for k in approves if k not in known]
        if unknown:
            msg = (
                f"explainer {explainer_hash[:12]}… has no section {', '.join(unknown)}; its "
                f"sections are {', '.join(known) or 'none'}"
            )
            raise ExplainerError(msg)
    doc: dict[str, Any] = {
        "schema": SCHEMA if approves is None else SCHEMA_V2,
        "target": target_id,
        "node": node_dir.name,
        "explainer": explainer_hash,
        "affirmation": AFFIRMATION,
        "signer": signer_login,
        "date": date[:10],
    }
    if approves is not None:
        doc["sections"] = list(dict.fromkeys(approves))
    doc = schemas.validate(signed.sign(doc, key_path, signer), str(doc["schema"]))
    path = next_path(node_dir, explainer_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    log.info("explainer: %s signed %s on %s", signer_login, explainer_hash[:12], node_dir.name)
    return path


def signature_document_v3(  # noqa: PLR0913 — one argument per fact the record carries
    *,
    target_id: str,
    node_id: str,
    explainer_hash: str,
    signer_login: str,
    date: str,
    sections: list[str] | None,
    via: str = signed.VIA_APPROVAL_KEY,
) -> dict[str, Any]:
    """F23-R10: the unsigned ``explainer-signature/v3`` record, which the service signs with the
    approval key (``signed.body`` is what the signature is over, with ``key`` set first).
    ``sections`` ``None`` approves every section."""
    doc: dict[str, Any] = {
        "schema": SCHEMA_V3,
        "target": target_id,
        "node": node_id,
        "explainer": explainer_hash,
        "affirmation": AFFIRMATION,
        "signer": signer_login,
        "date": date[:10],
        signed.VIA_FIELD: via,
    }
    if sections is not None:
        doc["sections"] = list(dict.fromkeys(sections))
    return doc


def read_signature(path: Path) -> Signature:
    m = _FILE_RE.match(path.name)
    doc = glosses.load_signature_doc(path, SCHEMAS)
    return signature_of(doc, path, int(m.group("n")) if m else 0)


# --- explainer/v1: the proof described and the steps each section names (F20-R2, R4) ------------
#
# An explainer filed before F20 opens with free front matter (``author``, ``model``, ``date``) or
# none, and stays valid and unanchored. One whose front matter declares a ``schema`` is a record
# and is held to it: only ``explainer/v1`` is accepted.

RECORD_SCHEMA = "explainer/v1"
#: Every explainer record version the gate reads, each validated against its own ``schema``
#: (D-34): v2 adds ``drafted_with`` (F21-R6; D-3 v3.31, D-23).
RECORD_SCHEMAS: frozenset[str] = frozenset({"explainer/v1", "explainer/v2"})
OUTLINES_DIR = "outlines"
OUTLINE_SCHEMA = "outline/v1"
#: F20-Q2: a section names steps at the end of its level-2 heading, ``{steps: s3 s4.1}``.
_ANCHOR_RE = re.compile(r"\s*\{steps:(?P<ids>[^{}]*)\}\s*$")
_HEADING_RE = re.compile(r"^## (?P<heading>.*)$")
#: A qualified Lean name in backticks: the cited names R5's warning reads (F20-T5).
_CITED_RE = re.compile(r"`(?P<name>[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)+)`")


@dataclass(frozen=True)
class Section:
    heading: str
    steps: tuple[str, ...]
    text: str


def parse_record(text: str) -> tuple[dict[str, Any] | None, str]:
    """``(front matter, body)`` when the explainer declares a schema, ``(None, text)`` for an
    explainer filed before F20 (no front matter, or front matter without ``schema``). Raises
    ``ValueError`` for front matter that does not parse."""
    doc, body = glosses.split_front_matter(text)
    if doc is None or "schema" not in doc:
        return None, text
    return doc, body


def sections(body: str) -> list[Section]:
    """R2: the body's level-2 sections, each with the steps its heading names. Raises
    ``ValueError`` when the body is not sections: text before the first heading, or none."""
    out: list[Section] = []
    heading: str | None = None
    lines: list[str] = []
    for line in body.splitlines():
        m = _HEADING_RE.match(line)
        if m is None:
            if heading is None and line.strip():
                msg = "an explainer's body is sections under level-2 headings (## ...)"
                raise ValueError(msg)
            lines.append(line)
            continue
        if heading is not None:
            out.append(_section(heading, lines))
        heading, lines = m.group("heading"), []
    if heading is None:
        msg = "an explainer's body has at least one section under a level-2 heading (## ...)"
        raise ValueError(msg)
    out.append(_section(heading, lines))
    return out


def _section(heading: str, lines: list[str]) -> Section:
    m = _ANCHOR_RE.search(heading)
    steps: tuple[str, ...] = ()
    if m is not None:
        steps = tuple(s for s in re.split(r"[\s,]+", m.group("ids")) if s)
        heading = heading[: m.start()]
    return Section(heading.strip(), steps, "\n".join(lines))


def merged_artifacts(node_dir: Path) -> dict[str, str]:
    """The node's merged proof artifacts by content hash, each as its path relative to the node:
    ``Proof.lean``, the alternates and the partial assemblies under ``attempts/`` (D-3, D-25,
    D-12 #5). An explainer PR cannot add one (it would be another mode), so what is in the tree
    at its merge commit merged before it."""
    found: dict[str, str] = {}
    proof = node_dir / "Proof.lean"
    if proof.is_file():
        found[schemas.content_hash(proof.read_bytes())] = "Proof.lean"
    attempts = node_dir / "attempts"
    if attempts.is_dir():
        for path in sorted(p for p in attempts.iterdir() if p.is_file() and p.suffix == ".lean"):
            found.setdefault(schemas.content_hash(path.read_bytes()), f"attempts/{path.name}")
    return found


def outline_of(target_dir: Path, artifact_hash: str) -> dict[str, Any] | None:
    """F19's committed outline of one artifact, ``targets/<id>/outlines/<hash>.json``, or
    ``None`` when there is none. One that does not validate is logged and read as absent: a
    product the gate cannot read names no step (C7)."""
    path = target_dir / OUTLINES_DIR / f"{artifact_hash}.json"
    if not path.is_file():
        return None
    try:
        doc = schemas.load_json(path, OUTLINE_SCHEMA)
    except schemas.SchemaError as exc:
        log.warning("%s does not validate and names no step: %s", path, exc)
        return None
    return doc


def outline_steps(outline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every step of an outline by id, children included."""
    out: dict[str, dict[str, Any]] = {}
    stack = list(outline.get("steps") or [])
    while stack:
        step = stack.pop()
        out[str(step["id"])] = step
        stack.extend(step.get("children") or [])
    return out


def _invalid(located: Located, why: str) -> Diagnostic:
    return Diagnostic(
        "explainer-invalid",
        f"{located.path}: {why} (F20-R2; explainer/v1)",
        {"path": located.path},
    )


def record(  # noqa: PLR0911 — one return per rule
    located: Located, data: bytes
) -> tuple[dict[str, Any] | None, list[Section]] | Diagnostic:
    """The explainer's ``explainer/v1`` front matter and sections, ``(None, [])`` for one filed
    before F20, or ``explainer-invalid`` naming why it is neither."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return _invalid(located, "the file is not valid UTF-8")
    try:
        doc, body = parse_record(text)
    except ValueError as exc:
        return _invalid(located, str(exc))
    if doc is None:
        return None, []
    if doc.get("schema") not in RECORD_SCHEMAS:
        return _invalid(located, f"the front matter declares {doc.get('schema')!r}")
    violations = schemas.violations(doc, str(doc["schema"]))
    if violations:
        return _invalid(located, f"{violations[0].path}: {violations[0].message}")
    if (doc["author"] is None) == (doc["drafter"] is None):
        return _invalid(located, "exactly one of author and drafter is set (D-23)")
    if doc["target"] != located.target_id or doc["node"] != located.node_id:
        return _invalid(
            located,
            f"it explains a proof of {doc['target']}/{doc['node']} and sits under "
            f"{located.target_id}/{located.node_id}",
        )
    try:
        return doc, sections(body)
    except ValueError as exc:
        return _invalid(located, str(exc))


def check_record(  # noqa: PLR0911 — one return per rule
    graph_root: Path, located: Located, data: bytes
) -> list[Diagnostic] | None:
    """R2, R4: an ``explainer/v1`` file's checks, or ``None`` for an explainer filed before F20
    (the caller keeps D-3's rule for those). Reads files; runs no Lean."""
    parsed = record(located, data)
    if isinstance(parsed, Diagnostic):
        return [parsed]
    doc, found = parsed
    if doc is None:
        return None
    doubled = sectionsmod.duplicates(sectionsmod.explainer_parts("", found))
    if doubled:
        return [
            Diagnostic(
                "section-duplicate",
                f"{located.path}: two sections have the key {', '.join(doubled)}; a section is "
                "known by the steps it names, so each set of steps (and the unanchored overview) "
                "has one section (F21-R11, Q8)",
                {"path": located.path, "keys": doubled},
            )
        ]
    target_dir = graph_root / "targets" / located.target_id
    node_dir = target_dir / "nodes" / str(located.node_id)
    proof = str(doc["proof"])
    artifacts = merged_artifacts(node_dir)
    if proof not in artifacts:
        return [
            Diagnostic(
                "explainer-proof-unknown",
                f"{located.path} explains {proof}, which is not a merged proof artifact of "
                f"{located.node_id} (its Proof.lean, an alternate or a merged partial assembly); "
                f"the node's are: {', '.join(f'{p} {h}' for h, p in artifacts.items()) or 'none'}",
                {"path": located.path, "proof": proof, "artifacts": dict(artifacts)},
            )
        ]
    named = [s for section in found for s in section.steps]
    if not named:
        return []
    outline = outline_of(target_dir, proof)
    known = outline_steps(outline) if outline is not None else {}
    unknown = [s for s in named if s not in known]
    if not unknown:
        return []
    why = (
        f"absent from the outline of {artifacts[proof]}"
        if outline is not None
        else f"named on {artifacts[proof]}, which has no outline to name steps of"
    )
    return [
        Diagnostic(
            "explainer-step-unknown",
            f"{located.path}: step {', '.join(unknown)} is {why} (F20-R4); a section names steps "
            f"of {OUTLINES_DIR}/{proof}.json, or none",
            {"path": located.path, "steps": unknown, "outline": outline is not None},
        )
    ]


def is_record(data: bytes) -> bool:
    """Whether an explainer file declares a schema (``explainer/v1``) rather than being one filed
    before F20; a file that cannot be read as text counts as a record, so it meets the checks."""
    try:
        doc, _ = parse_record(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return True
    return doc is not None


# --- versions, chains and digestion (F20-R6, R7, R9; D-33 v3.30) ---------------------------------


def first_proof(node_dir: Path) -> str | None:
    """The hash of the node's ``Proof.lean``, its first proof (D-33 v3.30), or ``None``."""
    proof = node_dir / "Proof.lean"
    return schemas.content_hash(proof.read_bytes()) if proof.is_file() else None


def versions(node_dir: Path) -> list[glosses.Version]:
    """Every explainer on the node as a version of a chain, by file name. An ``explainer/v1``
    record is a version of the proof it names; one filed before F20 names no proof and is read as
    a one-version chain on the node's ``Proof.lean`` — what D-3 v3.17 said an explainer was about
    — so a signed one keeps counting and a record may supersede it. A record that does not
    validate is logged and passed over: the gate refused it at merge (C7)."""
    directory = node_dir / EXPLAINER_DIR
    if not directory.is_dir():
        return []
    first = first_proof(node_dir)
    out: list[glosses.Version] = []
    for path in sorted(p for p in directory.iterdir() if p.is_file() and p.suffix == ".md"):
        if not _HASH_RE.match(path.stem):
            continue
        try:
            text = path.read_text(encoding="utf-8")
            doc, _ = parse_record(text)
            loose = glosses.split_front_matter(text)[0] if doc is None else None
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            log.warning("%s is not an explainer and is passed over: %s", path, exc)
            continue
        if doc is None:
            fm = loose or {}
            author = fm.get("author") if isinstance(fm.get("author"), str) else None
            date = str(fm["date"]) if fm.get("date") is not None else None
            subject: glosses.Subject = ("proof", node_dir.name, first)
            out.append(glosses.Version(path.stem, path, subject, None, author, None, date, None))
            continue
        schema = doc.get("schema")
        if schema not in RECORD_SCHEMAS or schemas.violations(doc, str(schema)):
            log.warning("%s does not validate as an explainer record and is passed over", path)
            continue
        out.append(
            glosses.Version(
                hash=path.stem,
                path=path,
                subject=("proof", node_dir.name, str(doc["proof"])),
                supersedes=doc["supersedes"],
                author=doc["author"],
                drafter=doc["drafter"],
                date=str(doc["date"]),
                schema=str(schema),
                drafted_with=doc.get("drafted_with"),
            )
        )
    return out


def chains_on(node_dir: Path, proof: str | None) -> list[glosses.Chain]:
    """The explainer chains on one of the node's proofs (R9)."""
    withdrawn = glosses.withdrawn_versions(node_dir, EXPLAINER_DIR)
    on = [v for v in versions(node_dir) if v.subject[2] == proof]
    return glosses.chains(on, withdrawn)


def explained(node_dir: Path, signer: Signer) -> bool:
    """D-33 v3.31 (F21-R15): the node counts as explained while every section an explainer chain
    on its first proof shows is verified — signed by a steward or curator, by a signature naming
    that section or by one naming none (v1). A person's later edit of a verified section is
    pending and leaves the verified words shown; a section shown as drafted or written does not
    count, and a gloss signature counts for nothing here (F20-Q12)."""
    first = first_proof(node_dir)
    if first is None:
        return False
    approvals = approvals_of(valid(node_dir, signer))
    withdrawn = glosses.withdrawn_versions(node_dir, EXPLAINER_DIR)
    return any(
        sectionsmod.of_chain(chain, approvals, withdrawn).all_verified()
        for chain in chains_on(node_dir, first)
    )


def approvals_of(sigs: list[Signature]) -> dict[str, list[frozenset[str] | None]]:
    """What each explainer version's valid signatures approve: the keys a v2 signature names, or
    ``None`` (every section) for a v1 one (F21-R13)."""
    out: dict[str, list[frozenset[str] | None]] = {}
    for sig in sigs:
        out.setdefault(sig.explainer, []).append(
            None if sig.sections is None else frozenset(sig.sections)
        )
    return out


def section_keys(path: Path) -> list[str]:
    """The section keys of the explainer file at ``path``, in order; empty when it cannot be
    read (F21-R11)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return list(dict.fromkeys(p.key for p in sectionsmod.parts_of_text(text, gloss=False)))


def name_warnings(graph_root: Path, located: Located) -> list[Diagnostic]:
    """R5 (F20-T5): ``explainer-name-unanchored`` for each qualified Lean name in backticks in an
    anchored section that occurs in none of the constants its steps (and their sub-steps) use, by
    the outline. A warning, never a refusal: untested as a detector, so it informs. Names occur
    in a constant as a run of its dotted components (``Prime.two_le`` in ``Nat.Prime.two_le``).
    A name that cannot be a constant is not held to them (F22-T12, ``_not_a_constant``)."""
    try:
        data = (graph_root / located.path).read_bytes()
    except OSError:
        return []
    parsed = record(located, data)
    if isinstance(parsed, Diagnostic) or parsed[0] is None:
        return []
    doc, found = parsed
    assert doc is not None
    outline = outline_of(graph_root / "targets" / located.target_id, str(doc["proof"]))
    if outline is None:
        return []
    steps = outline_steps(outline)
    out: list[Diagnostic] = []
    for section in found:
        if not section.steps or any(s not in steps for s in section.steps):
            continue
        constants = _constants(steps[s] for s in section.steps)
        locals_ = _locals(steps[s] for s in section.steps)
        seen: set[str] = set()
        for m in _CITED_RE.finditer(section.text):
            name = m.group("name")
            if name in seen or any(_occurs(name, c) for c in constants):
                continue
            if _not_a_constant(name, steps, locals_):
                continue
            seen.add(name)
            out.append(
                Diagnostic(
                    "explainer-name-unanchored",
                    f"{located.path}: the section {section.heading!r} cites `{name}`, which none "
                    f"of the constants its steps ({', '.join(section.steps)}) use contains; check "
                    "that the prose describes the Lean it names (F20-R5)",
                    {"path": located.path, "name": name, "steps": list(section.steps)},
                )
            )
    return out


def _constants(steps: Any) -> set[str]:
    out: set[str] = set()
    stack = list(steps)
    while stack:
        step = stack.pop()
        uses = step.get("uses") or {}
        out.update(str(d) for d in uses.get("defs") or [])
        out.update(str(m["name"]) for m in uses.get("mathlib") or [])
        stack.extend(step.get("children") or [])
    return out


def _locals(steps: Any) -> set[str]:
    """The names the steps, and their sub-steps, bind or list as hypotheses their goals
    introduce: locals of the proof, whose fields a writer may cite (``r.num``, ``hroot.hs``)."""
    out: set[str] = set()
    stack = list(steps)
    while stack:
        step = stack.pop()
        if step.get("name"):
            out.add(str(step["name"]))
        goal = step.get("goal") or {}
        out.update(str(h["name"]) for h in goal.get("hypotheses") or [])
        stack.extend(step.get("children") or [])
    return out


def _not_a_constant(name: str, steps: Mapping[str, Any], locals_: set[str]) -> bool:
    """F22-T12 (testers 2026-10-06): a cited name that cannot be a library constant, so is not
    held to the steps' constants: a step id of the outline (a sub-step id is what the guide tells
    writers to cite), a field of a local the section's steps bind (its first component), or a
    file name (``Context.lean``)."""
    return name in steps or name.split(".", 1)[0] in locals_ or name.endswith(LEAN_FILE_SUFFIX)


def _occurs(name: str, constant: str) -> bool:
    parts, whole = name.split("."), constant.split(".")
    return any(whole[i : i + len(parts)] == parts for i in range(len(whole) - len(parts) + 1))
