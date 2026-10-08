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
#: v2 (F24-R5; D-32 v3.34): one act in a write-up's life, from its record to its acceptance.
SCHEMA_V2 = "writeup/v2"
SCHEMAS: frozenset[str] = frozenset({SCHEMA, SCHEMA_V2})
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
    return [record_of(a.doc, a.path, a.n) for a in load_any(target_dir) if a.is_record]


def valid(target_dir: Path, signer: Signer) -> list[Writeup]:
    out: list[Writeup] = []
    for record in load(target_dir):
        if not signed.verifies(record.doc, signer):
            log.warning("%s counts for nothing: the signature does not verify", record.path)
            continue
        out.append(record)
    return out


def has_paper(target_dir: Path, signer: Signer, *, curators: frozenset[str] = frozenset()) -> bool:
    """R7: whether a paper exists at ``steward-signed`` or above — the ``written-up`` condition
    (F15-R7; F24-R5: anyone may now record a write-up, and only a steward's or curator's signature
    makes it the problem's)."""
    graph_root = target_dir.parent.parent
    found = views(graph_root, target_dir.name, today=None, signer=signer, curators=curators)
    floor = STAGES.index(STEWARD_SIGNED)
    return any(
        v.kind == PAPER and v.stage != WITHDRAWN and STAGES.index(v.stage) >= floor for v in found
    )


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


# --- F24-R5, R7: a write-up's life, its stage and the official one (D-32 v3.34) -------------------

RECORD = "record"
AUTHOR_SIGN = "author-sign"
ARXIV = "arxiv"
SUBMITTED = "submitted"
ACCEPTED = "accepted"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
JOURNAL_ACTS: frozenset[str] = frozenset({SUBMITTED, ACCEPTED, REJECTED})
DRAFTED = "drafted"
WRITTEN = "written"
STEWARD_SIGNED = "steward-signed"
PANEL_VERIFIED = "panel-verified"
RELEASED = "released"
ON_ARXIV = "on-arxiv"
#: The ladder, lowest first; ``withdrawn`` sits outside it and is final.
STAGES: tuple[str, ...] = (
    DRAFTED, WRITTEN, STEWARD_SIGNED, PANEL_VERIFIED, RELEASED, ON_ARXIV, SUBMITTED, ACCEPTED,
    WITHDRAWN,
)  # fmt: skip


@dataclass(frozen=True)
class Act:
    """One write-up record of either version; a ``writeup/v1`` reads as a ``record`` whose only
    author is its signer."""

    n: int
    action: str
    signer: str
    date: str
    path: Path
    doc: dict[str, Any]
    writeup: int | None = None
    kind: str | None = None
    title: str | None = None
    url: str | None = None
    authors: tuple[str, ...] = ()
    model: str | None = None
    arxiv: str | None = None
    journal: str | None = None
    doi: str | None = None

    @property
    def is_record(self) -> bool:
        return self.action == RECORD


def act_of(doc: dict[str, Any], path: Path, n: int) -> Act:
    if doc["schema"] == SCHEMA:
        return Act(
            n=n, action=RECORD, signer=str(doc["signer"]), date=str(doc["date"]), path=path,
            doc=doc, kind=str(doc["kind"]), title=str(doc["title"]), url=str(doc["url"]),
            authors=(str(doc["signer"]),),
        )  # fmt: skip
    return Act(
        n=n,
        action=str(doc["action"]),
        signer=str(doc["signer"]),
        date=str(doc["date"]),
        path=path,
        doc=doc,
        writeup=int(doc["writeup"]) if "writeup" in doc else None,
        kind=doc.get("kind"),
        title=doc.get("title"),
        url=doc.get("url"),
        authors=tuple(str(a) for a in doc.get("authors", ())),
        model=doc.get("model"),
        arxiv=doc.get("arxiv"),
        journal=doc.get("journal"),
        doi=doc.get("doi"),
    )


def load_doc(path: Path) -> dict[str, Any]:
    """A write-up record validated against the version it declares (v1 or v2, D-34)."""
    doc = schemas.load_yaml(path)
    declared = doc.get("schema") if isinstance(doc, dict) else None
    if declared not in SCHEMAS:
        msg = f"{path} declares {declared!r}, not one of {', '.join(sorted(SCHEMAS))}"
        raise schemas.SchemaError(msg)
    return schemas.validate(doc, str(declared))


def load_any(target_dir: Path) -> list[Act]:
    """Every write-up record of either version, in file order. A file under ``writeup/`` that is
    not a numbered record, or does not validate, is a graph defect and raises."""
    directory = writeup_dir(target_dir)
    if not directory.is_dir():
        return []
    out: list[Act] = []
    for path in sorted(p for p in directory.iterdir() if p.is_file()):
        m = _FILE_RE.match(path.name)
        if m is None:
            msg = f"{path}: a write-up record is writeup/<n>.yaml (F15-R6)"
            raise schemas.SchemaError(msg)
        out.append(act_of(load_doc(path), path, int(m.group("n"))))
    out.sort(key=lambda a: a.n)
    return out


@dataclass(frozen=True)
class View:
    """A write-up with its derived stage (``targets-index/v9``'s ``writeups.items``)."""

    n: int
    kind: str
    title: str
    url: str
    stage: str
    model: str | None
    authors: tuple[str, ...]
    signed: tuple[str, ...]
    coauthors: tuple[str, ...]
    arxiv: str | None
    journal: str | None
    doi: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "kind": self.kind,
            "title": self.title,
            "url": self.url,
            "stage": self.stage,
            "model": self.model,
            "authors": list(self.authors),
            "signed": list(self.signed),
            "coauthors": list(self.coauthors),
            "arxiv": self.arxiv,
            "journal": self.journal,
            "doi": self.doi,
        }


def _stage(  # noqa: PLR0913 — the record, what follows it, and who may sign for the problem
    record: Act,
    following: list[Act],
    signed_by: tuple[str, ...],
    *,
    stewards: frozenset[str],
    curators: frozenset[str],
    verified: bool,
) -> tuple[str, str | None, str | None, str | None]:
    """(stage, arxiv, journal, doi) of one write-up."""
    if any(a.action == WITHDRAWN for a in following):
        arxiv = next((a.arxiv for a in reversed(following) if a.action == ARXIV), None)
        return WITHDRAWN, arxiv, None, None
    arxiv = next((a.arxiv for a in reversed(following) if a.action == ARXIV), None)
    latest = next((a for a in reversed(following) if a.action in JOURNAL_ACTS), None)
    journal, doi = (
        (latest.journal, latest.doi) if latest and latest.action != REJECTED else (None, None)
    )
    # The ladder is climbed in order: each rung needs the one below it, so an unreviewed note
    # cannot outrank a verified paper by having one author who signs it.
    stage = DRAFTED if record.model else WRITTEN
    deciders = stewards | curators
    # A writeup/v1 record was admitted only from a steward or a curator (F15-R6), so it is
    # steward-signed by the rule it merged under, whoever its signer is now.
    legacy = record.doc.get("schema") == SCHEMA
    if (
        not legacy
        and record.signer not in deciders
        and not any(a.action == AUTHOR_SIGN and a.signer in deciders for a in following)
    ):
        return stage, arxiv, journal, doi
    stage = STEWARD_SIGNED
    if not verified:
        return stage, arxiv, journal, doi
    stage = PANEL_VERIFIED
    if not set(record.authors) <= set(signed_by):
        return stage, arxiv, journal, doi
    reached = [RELEASED]
    if arxiv is not None:
        reached.append(ON_ARXIV)
    if journal is not None and latest is not None:
        reached.append(latest.action)
    return max(reached, key=STAGES.index), arxiv, journal, doi


def views(
    graph_root: Path,
    target_id: str,
    *,
    today: Any,
    signer: Signer,
    curators: frozenset[str] = frozenset(),
) -> list[View]:
    """Every write-up of the target with its stage on ``today`` (a ``datetime.date``; ``None``
    reads the motions as of today's date), in record order (F24-R5, R7).

    An act counts only when its signature verifies and, after the record, when its signer is a
    listed author; a second signature by the same author changes nothing."""
    import datetime as dt  # noqa: PLC0415

    from opn_gate import panel, steward  # noqa: PLC0415 — both read this module

    target_dir = graph_root / "targets" / target_id
    acts = [a for a in load_any(target_dir) if signed.verifies(a.doc, signer)]
    if not acts:
        return []
    on = today if today is not None else dt.datetime.now(dt.UTC).date()
    stewards = frozenset(s.login for s in steward.active(target_dir, signer))
    verified_writeups = {
        int(t.subject["writeup"])
        for t in panel.tallies(graph_root, target_id, today=on, signer=signer, curators=curators)
        if t.kind == panel.VERIFY_WRITEUP and t.state == panel.PASSED
    }
    words = panel.words_signers(target_dir)
    out: list[View] = []
    for record in (a for a in acts if a.is_record):
        following = [
            a for a in acts
            if not a.is_record and a.writeup == record.n and a.signer in record.authors
        ]  # fmt: skip
        signed_by = tuple(
            dict.fromkeys(
                [record.signer] * (record.signer in record.authors)
                + [a.signer for a in following if a.action == AUTHOR_SIGN]
            )
        )
        stage, arxiv, journal, doi = _stage(
            record, following, signed_by, stewards=stewards, curators=curators,
            verified=record.n in verified_writeups,
        )  # fmt: skip
        coauthors = tuple(sorted(stewards & (set(signed_by) | words)))
        out.append(
            View(
                n=record.n,
                kind=str(record.kind),
                title=str(record.title),
                url=str(record.url),
                stage=stage,
                model=record.model,
                authors=record.authors,
                signed=signed_by,
                coauthors=coauthors,
                arxiv=arxiv,
                journal=journal,
                doi=doi,
            )
        )
    return out


def official(found: list[View]) -> int | None:
    """The write-up the page shows: the highest stage, then the newest; never a withdrawn one."""
    live = [v for v in found if v.stage != WITHDRAWN]
    if not live:
        return None
    return max(live, key=lambda v: (STAGES.index(v.stage), v.n)).n
