"""Write-up records (F15-R6, R7; D-32, D-33 v3.17).

``targets/<id>/writeup/<n>.yaml`` records that a paper or a state-of-the-problem note about the
target exists — its kind, title, URL and date — signed with the signer's own key over the
canonical body (``opn_gate.signed``). A valid ``paper`` record is what makes a resolved target
``written-up``. Who may sign one — an active steward of the target or a listed curator — is the
gate's rule at merge (``modes``); here a record is valid when it verifies. The note's text is
still ``targets/<id>/note.md``: the record points at where the write-up lives, it does not hold it.
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

SCHEMA = "writeup/v1"
DIR = "writeup"
PAPER = "paper"
NOTE = "note"
KINDS: tuple[str, ...] = (PAPER, NOTE)
_FILE_RE = re.compile(r"^(?P<n>[1-9][0-9]*)\.ya?ml$")


class WriteupError(ValueError):
    """The record cannot be written as asked. Nothing is written."""


@dataclass(frozen=True)
class Writeup:
    n: int
    kind: str
    title: str
    url: str
    date: str
    signer: str
    key: str
    path: Path
    doc: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "url": self.url,
            "date": self.date,
            "signer": self.signer,
        }


def writeup_dir(target_dir: Path) -> Path:
    return target_dir / DIR


def record_of(doc: dict[str, Any], path: Path, n: int) -> Writeup:
    return Writeup(
        n=n,
        kind=str(doc["kind"]),
        title=str(doc["title"]),
        url=str(doc["url"]),
        date=str(doc["date"]),
        signer=str(doc["signer"]),
        key=str(doc["key"]),
        path=path,
        doc=doc,
    )


def load(target_dir: Path) -> list[Writeup]:
    """Every write-up record, in file order; a file that is not one, or does not validate, is a
    graph defect and raises."""
    directory = writeup_dir(target_dir)
    if not directory.is_dir():
        return []
    out: list[Writeup] = []
    for path in sorted(p for p in directory.iterdir() if p.is_file()):
        m = _FILE_RE.match(path.name)
        if m is None:
            msg = f"{path}: a write-up record is writeup/<n>.yaml (F15-R6)"
            raise schemas.SchemaError(msg)
        out.append(record_of(schemas.load_yaml(path, SCHEMA), path, int(m.group("n"))))
    out.sort(key=lambda r: r.n)
    return out


def valid(target_dir: Path, signer: Signer) -> list[Writeup]:
    out: list[Writeup] = []
    for record in load(target_dir):
        if not signed.verifies(record.doc, signer):
            log.warning("%s counts for nothing: the signature does not verify", record.path)
            continue
        out.append(record)
    return out


def has_paper(target_dir: Path, signer: Signer) -> bool:
    """R7: whether a valid ``paper`` record exists — the ``written-up`` condition."""
    return any(r.kind == PAPER for r in valid(target_dir, signer))


def next_path(target_dir: Path) -> Path:
    directory = writeup_dir(target_dir)
    taken = {
        int(m.group("n"))
        for p in (directory.iterdir() if directory.is_dir() else ())
        if (m := _FILE_RE.match(p.name)) is not None
    }
    return directory / f"{max(taken, default=0) + 1}.yaml"


def write(  # noqa: PLR0913 — one argument per fact the record carries
    target_dir: Path,
    *,
    kind: str,
    title: str,
    url: str,
    date: str,
    signer_login: str,
    key_path: Path,
    signer: Signer,
) -> Path:
    """R6: write and sign one record with the signer's own key, or refuse with nothing written."""
    if kind not in KINDS:
        msg = f"a write-up is a {PAPER} or a {NOTE}, not {kind!r}"
        raise WriteupError(msg)
    if not url.startswith("https://"):
        msg = "the write-up's URL is an https URL"
        raise WriteupError(msg)
    if not title.strip():
        msg = "the write-up's title is empty"
        raise WriteupError(msg)
    doc = {
        "schema": SCHEMA,
        "target": target_dir.name,
        "kind": kind,
        "title": title,
        "url": url,
        "date": date[:10],
        "signer": signer_login,
    }
    doc = schemas.validate(signed.sign(doc, key_path, signer), SCHEMA)
    path = next_path(target_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    log.info("writeup: %s recorded a %s on %s", signer_login, kind, target_dir.name)
    return path


def read_record(path: Path) -> Writeup:
    m = _FILE_RE.match(path.name)
    return record_of(schemas.load_yaml(path, SCHEMA), path, int(m.group("n")) if m else 0)
