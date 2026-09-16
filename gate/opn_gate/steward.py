"""Steward records and the active set (F15-R1, R2; D-32 v3.17, D-6 v3.17, D-22 v3.17).

A steward is the D-32 writer appointed at listing: a real-identity mathematician who commits, by
a signed record, to understand and write up whatever the network produces on a target. The
records live at ``targets/<id>/stewards/<n>.yaml``, append-only, each signed with the steward's
own SSH key over its canonical body (``opn_gate.signed``). A target's **active stewards** are the
logins whose latest counting record is a ``commit``.

What counts is decided here and nowhere else. A record counts for nothing when its signature does
not verify under its own key, when its sentence is not the fixed one for its action, or when a
``step-down`` is signed with a key other than the one its login committed with — so a stranger
cannot step a steward down, and a steward cannot commit under one key and later disown the record
under another. Such a record is *flagged* rather than raised on: it merged, it stays, and the
gate refuses a new one by name before it merges (``problems``, F15-T3). A record that does not
validate against its schema is a graph defect and raises, like a fidelity certificate.

The steward has no power here: nothing in this module pauses, reserves or closes anything. The
one thing the active set decides is claimability under the policy switch (F15-R4), and that is
``intake.claimability``'s to apply.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from opn_gate import schemas, signed
from opn_gate.signer import Signer

log = logging.getLogger(__name__)

SCHEMA = "steward/v1"
DIR = "stewards"
SUFFIX = ".yaml"
Action = Literal["commit", "step-down"]
COMMIT: Action = "commit"
STEP_DOWN: Action = "step-down"
#: The fixed sentences, verbatim (R1). A record with any other text counts for nothing.
COMMITMENT = (
    "I commit to make best efforts to understand and write up whatever the network produces on "
    "this problem, and to sign the explainer of the proof that closes it."
)
STEP_DOWN_SENTENCE = "I step down as a steward of this problem."
SENTENCE_FOR: dict[str, str] = {COMMIT: COMMITMENT, STEP_DOWN: STEP_DOWN_SENTENCE}
#: GitHub's login grammar: alphanumerics and single hyphens, at most 39 characters, never a
#: leading or trailing hyphen. Validated before a login enters any message or page (F15 §7).
LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}$")
_FILE_RE = re.compile(r"^(?P<n>[1-9][0-9]*)\.ya?ml$")


class StewardError(ValueError):
    """The record cannot be written as asked. Nothing is written."""


@dataclass(frozen=True)
class Record:
    """One steward record on disk, as written; whether it counts is ``Checked``'s."""

    n: int
    action: str
    login: str
    name: str
    link: str
    commitment: str
    date: str
    key: str
    path: Path
    doc: dict[str, Any]


@dataclass(frozen=True)
class Checked:
    """A record with the verdict on it: ``problems`` is empty exactly when it counts."""

    record: Record
    problems: tuple[str, ...] = ()

    @property
    def counts(self) -> bool:
        return not self.problems


@dataclass(frozen=True)
class Steward:
    """An active steward, in the shape ``targets/index.json`` publishes (F15-R9)."""

    login: str
    name: str
    link: str
    since: str

    def as_dict(self) -> dict[str, Any]:
        return {"login": self.login, "name": self.name, "link": self.link, "since": self.since}


# --- reading -------------------------------------------------------------------------------------


def stewards_dir(target_dir: Path) -> Path:
    return target_dir / DIR


def record_of(doc: dict[str, Any], path: Path, n: int) -> Record:
    return Record(
        n=n,
        action=str(doc["action"]),
        login=str(doc["login"]),
        name=str(doc["name"]),
        link=str(doc["link"]),
        commitment=str(doc["commitment"]),
        date=str(doc["date"]),
        key=str(doc["key"]),
        path=path,
        doc=doc,
    )


def load(target_dir: Path) -> list[Record]:
    """Every steward record, in file order (``<n>.yaml`` by ``n``). A file under ``stewards/``
    that is not a numbered record, or one that does not validate, is a graph defect and raises."""
    directory = stewards_dir(target_dir)
    if not directory.is_dir():
        return []
    out: list[Record] = []
    for path in sorted(p for p in directory.iterdir() if p.is_file()):
        m = _FILE_RE.match(path.name)
        if m is None:
            msg = f"{path}: a steward record is stewards/<n>.yaml (F15-R1)"
            raise schemas.SchemaError(msg)
        doc = schemas.load_yaml(path, SCHEMA)
        out.append(record_of(doc, path, int(m.group("n"))))
    out.sort(key=lambda r: r.n)
    return out


def problems_of(record: Record, signer: Signer, *, commit_key: str | None) -> tuple[str, ...]:
    """Why ``record`` counts for nothing, by name (R1), given the key the login is active under
    (``commit_key``; ``None`` when they are not). Empty when it counts."""
    problems: list[str] = []
    if not LOGIN_RE.match(record.login):
        problems.append(f"steward-login: {record.login!r} is not a GitHub login")
    if record.commitment != SENTENCE_FOR.get(record.action):
        problems.append(
            f"steward-sentence: the {record.action} sentence is not the fixed one (F15-R1)"
        )
    if not signed.verifies(record.doc, signer):
        problems.append("steward-signature: the signature does not verify under the record's key")
    if record.action == STEP_DOWN:
        if commit_key is None:
            problems.append(
                f"steward-not-active: {record.login} has no counting commit to step down from"
            )
        elif record.key != commit_key:
            problems.append(
                f"steward-key: the step-down is signed under a key other than the one "
                f"{record.login} committed with (F15-R1)"
            )
    return tuple(problems)


def check(records: list[Record], signer: Signer) -> list[Checked]:
    """Every record with its verdict, in order — each judged against the counting records
    before it, so a step-down is checked against the commit it undoes."""
    active_key: dict[str, str] = {}
    out: list[Checked] = []
    for record in records:
        problems = problems_of(record, signer, commit_key=active_key.get(record.login))
        checked = Checked(record, problems)
        out.append(checked)
        if not checked.counts:
            continue
        if record.action == COMMIT:
            active_key[record.login] = record.key
        else:
            active_key.pop(record.login, None)
    return out


def active(target_dir: Path, signer: Signer) -> list[Steward]:
    """R1: the logins whose latest counting record is a commit, in the order they became active,
    each ``since`` the commit that made them so (a re-commit while active keeps the date)."""
    current: dict[str, Steward] = {}
    for checked in check(load(target_dir), signer):
        if not checked.counts:
            log.warning(
                "%s counts for nothing: %s", checked.record.path, "; ".join(checked.problems)
            )
            continue
        r = checked.record
        if r.action == COMMIT:
            if r.login not in current:
                current[r.login] = Steward(r.login, r.name, r.link, r.date)
        else:
            current.pop(r.login, None)
    return list(current.values())


def active_logins(target_dir: Path, signer: Signer) -> tuple[str, ...]:
    return tuple(s.login for s in active(target_dir, signer))


def commit_key_of(target_dir: Path, login: str, signer: Signer) -> str | None:
    """The key ``login`` is active under, or ``None`` when they are not active."""
    key: str | None = None
    for checked in check(load(target_dir), signer):
        if not checked.counts or checked.record.login != login:
            continue
        key = checked.record.key if checked.record.action == COMMIT else None
    return key


# --- writing (F15-R2: the steward's own key, through the seam) ----------------------------------


def next_path(target_dir: Path) -> Path:
    """``stewards/<n>.yaml`` for the next free ``n`` — append-only, never a rewrite."""
    directory = stewards_dir(target_dir)
    taken = {
        int(m.group("n"))
        for p in (directory.iterdir() if directory.is_dir() else ())
        if (m := _FILE_RE.match(p.name)) is not None
    }
    n = max(taken, default=0) + 1
    return directory / f"{n}{SUFFIX}"


def document(  # noqa: PLR0913 — one argument per fact the record carries
    *,
    target_id: str,
    action: str,
    login: str,
    name: str,
    link: str,
    date: str,
) -> dict[str, Any]:
    """The unsigned record, refused before signing when its inputs are not what R1 asks."""
    if action not in SENTENCE_FOR:
        msg = f"a steward record is a {COMMIT} or a {STEP_DOWN}, not {action!r}"
        raise StewardError(msg)
    if not LOGIN_RE.match(login):
        msg = f"{login!r} is not a GitHub login (F15-R1: the login grammar)"
        raise StewardError(msg)
    if not link.startswith("https://"):
        msg = "the identity link is an https URL to an institutional page or an ORCID record"
        raise StewardError(msg)
    if not name.strip():
        msg = "the steward's display name is empty"
        raise StewardError(msg)
    return {
        "schema": SCHEMA,
        "target": target_id,
        "action": action,
        "login": login,
        "name": name,
        "link": link,
        "commitment": SENTENCE_FOR[action],
        "date": date[:10],
    }


def write(  # noqa: PLR0913 — one argument per fact the record carries
    target_dir: Path,
    *,
    action: str,
    login: str,
    name: str,
    link: str,
    date: str,
    key_path: Path,
    signer: Signer,
) -> Path:
    """R2: write and sign one record with the contributor's own key, or refuse by name with
    nothing written (C7). A step-down is refused unless ``login`` is active under this very key —
    the record would otherwise merge and count for nothing."""
    if not target_dir.is_dir():
        msg = f"no such target directory: {target_dir}"
        raise StewardError(msg)
    doc = document(
        target_id=target_dir.name, action=action, login=login, name=name, link=link, date=date
    )
    doc = signed.sign(doc, key_path, signer)
    if action == STEP_DOWN:
        current = commit_key_of(target_dir, login, signer)
        if current is None:
            msg = (
                f"{login} is not an active steward of {target_dir.name}; nothing to step down from"
            )
            raise StewardError(msg)
        if current != doc["key"]:
            msg = (
                f"the step-down key is not the key {login} committed with; a step-down is signed "
                "with the same key as the commitment (F15-R1)"
            )
            raise StewardError(msg)
    schemas.validate(doc, SCHEMA)
    path = next_path(target_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    log.info("steward: %s %s on %s", login, action, target_dir.name)
    return path


def read_record(path: Path) -> Record:
    """One record file, validated — for ``steward check`` and the gate's per-file checks."""
    m = _FILE_RE.match(path.name)
    n = int(m.group("n")) if m else 0
    return record_of(schemas.load_yaml(path, SCHEMA), path, n)
