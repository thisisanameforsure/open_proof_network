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
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from opn_gate import schemas, signed
from opn_gate.signer import Signer

log = logging.getLogger(__name__)

SCHEMA = "explainer-signature/v1"
EXPLAINER_DIR = "explainer"
SIGNED_DIR = "signed"
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
        doc = schemas.load_yaml(path, SCHEMA)
        out.append(signature_of(doc, path, int(m.group("n"))))
    return out


def problems_of(sig: Signature, node_dir: Path, signer: Signer) -> tuple[str, ...]:
    """Why the signature is not valid, by name (R8); empty when it is."""
    problems: list[str] = []
    if sig.explainer not in explainer_hashes(node_dir):
        problems.append(
            f"explainer-absent: no explainer {sig.explainer[:12]}… is on {node_dir.name}"
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
) -> Path:
    """R8: write one signature with the signer's own key, refusing by name with nothing written
    when the explainer is not on the node (C7)."""
    if not _HASH_RE.match(explainer_hash):
        msg = f"{explainer_hash!r} is not an explainer hash (64 lowercase hex characters, D-3)"
        raise ExplainerError(msg)
    if explainer_hash not in explainer_hashes(node_dir):
        msg = f"no explainer {explainer_hash[:12]}… is on {node_dir.name}; nothing to sign"
        raise ExplainerError(msg)
    doc = {
        "schema": SCHEMA,
        "target": target_id,
        "node": node_dir.name,
        "explainer": explainer_hash,
        "affirmation": AFFIRMATION,
        "signer": signer_login,
        "date": date[:10],
    }
    doc = schemas.validate(signed.sign(doc, key_path, signer), SCHEMA)
    path = next_path(node_dir, explainer_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    log.info("explainer: %s signed %s on %s", signer_login, explainer_hash[:12], node_dir.name)
    return path


def read_signature(path: Path) -> Signature:
    m = _FILE_RE.match(path.name)
    return signature_of(schemas.load_yaml(path, SCHEMA), path, int(m.group("n")) if m else 0)
